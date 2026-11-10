import numpy as np
import pandas as pd
from .config import PARAMS, MARKETPLACE_CHANNELS, DIGITAL_CHANNELS
from .data_cleaner import features,clean
from .data_generator import generate,corrupt,ERROR_FAMILIES

# Correlation and ratio outputs are written at this precision. BLAS builds differ around the
# 16th significant digit, so an unrounded value makes the committed JSON impossible to
# reproduce byte-for-byte on another machine (and breaks exact comparisons in the notebook).
DECIMALS = 6


def _r(x):
    return round(float(x), DECIMALS)


def summarize(d):
    def group(c):
        t=d.groupby(c,dropna=False).agg(doanh_thu=('doanh_thu','sum'),so_luong=('so_luong','sum'),so_dong=('ma_dong','size')).reset_index()
        t['ty_trong']=t.doanh_thu/d.doanh_thu.sum()*100
        return t.sort_values('doanh_thu',ascending=False)
    tables={k:group(c) for k,c in [('genre','the_loai'),('channel','kenh_ban'),('segment','phan_khuc_gia'),('month','thang_nam'),('year','nam_ban'),('publisher','nha_xuat_ban'),('author','tac_gia')]}
    books=d.groupby(['ma_sach','ten_sach'],dropna=False).agg(doanh_thu=('doanh_thu','sum'),so_luong=('so_luong','sum'),so_dong=('ma_dong','size'),diem_danh_gia=('diem_danh_gia','first')).reset_index()
    tables['books']=books.sort_values('doanh_thu',ascending=False)
    tables['discount']=d.groupby('nhom_giam_gia',dropna=False).agg(n=('ma_dong','size'),median_qty=('so_luong','median'),mean_qty=('so_luong','mean'),total_revenue=('doanh_thu','sum')).reset_index()
    numeric=['gia_goc','gia_ban','giam_gia_thuc_te','so_luong','doanh_thu','diem_danh_gia']
    tables['correlation']=d[numeric].corr()
    tables['describe']=d[numeric].describe().T.reset_index(names='bien')
    years=d.groupby('nam_ban').doanh_thu.sum()
    metrics={'lines':len(d),'books':int(d.ma_sach.nunique()),'orders':int(d.ma_don.nunique()),'revenue':int(d.doanh_thu.sum()),'quantity':int(d.so_luong.sum()),'average_unit_price':_r(d.doanh_thu.sum()/d.so_luong.sum()),'yoy_pct':_r((years.loc[2025]/years.loc[2024]-1)*100),'rating_qty_r':_r(d.diem_danh_gia.corr(d.so_luong)),'rating_book_qty_r':_r(books.diem_danh_gia.corr(books.so_luong)),'discount_qty_r':_r(d.giam_gia_thuc_te.corr(d.so_luong)),'rating_known':int(d.diem_danh_gia.notna().sum()),'good_rating_pct':_r(d.loc[d.diem_danh_gia.notna(),'diem_danh_gia'].ge(4).mean()*100),'iqr_flags':int(d.co_ngoai_lai_iqr.sum())}
    return tables,metrics


def evaluate(truth,cleaned,raw,events):
    t=features(truth).set_index('ma_dong'); c=cleaned.set_index('ma_dong')
    cols=['gia_ban','so_luong','doanh_thu','diem_danh_gia','nam_xuat_ban','tac_gia','nha_xuat_ban','the_loai']
    matches=[]
    for col in cols:
        a=c[col]; b=t.loc[c.index,col]
        equal=np.isclose(a,b,equal_nan=True) if pd.api.types.is_numeric_dtype(a) else a.fillna('<NA>').eq(b.fillna('<NA>'))
        matches.append({'cot':col,'so_khop':int(np.sum(equal)),'so_so_sanh':len(c),'ty_le_khop':float(np.mean(equal))})
    # Precision and recall are measured against every row that carries an injected defect, not
    # only the two families the old rule happened to target. Restricting the denominator to
    # invalid_qty + duplicate_conflict is what made the aggregate figure read 100%/100%: it
    # excluded every defect the rule could not see.
    intended=set(events.loc[events.ho_loi.notna(),'ma_dong'])
    removed=set(t.index)-set(c.index)
    return pd.DataFrame(matches), {'truth_revenue':int(t.doanh_thu.sum()),'clean_revenue':int(c.doanh_thu.sum()),'relative_revenue_error_pct':_r(100*(c.doanh_thu.sum()/t.doanh_thu.sum()-1)),'retained_pct':_r(len(c)/len(t)*100),'quarantine_precision':_r(len(removed&intended)/len(removed) if removed else 1.),'quarantine_recall':_r(len(removed&intended)/len(intended) if intended else 1.),'retained_revenue_error':int(c.doanh_thu.sum()-t.loc[c.index].doanh_thu.sum()),'unresolved_missing':int(c[cols].isna().sum().sum())}


def error_family_performance(truth,cleaned,raw,events):
    """Precision and recall per injected defect family.

    The single aggregate figure this project used to report was 100%/100%, and it was true by
    construction: every injected quantity error sat far outside the review threshold, so the
    quarantine rule was the exact inverse of the injection rule. Splitting by family shows which
    defects a value-domain rule can and cannot see, which is the finding the aggregate hid.

    Definitions, per family:
      n_cai      rows carrying that family label in the injected-error log
      n_cach_ly  rows of that family the pipeline quarantined outright
      n_danh_dau rows of that family the pipeline flagged without discarding (a missing catalog
                 record is flagged, because the transaction's own price and quantity are valid)
      recall     (n_cach_ly + n_danh_dau) / n_cai -- detected, by removal or by flag
      n_lot      rows of that family that survived into the cleaned data
      con_sai    rows of that family that survived AND still differ from the truth
    `con_sai` is the honest measure of harm: a row can be caught for an unrelated reason and still
    count as detected, but only a surviving wrong value corrupts the analysis. Detection and harm
    are reported separately rather than collapsed into one number.
    """
    t=features(truth).set_index('ma_dong')
    kept=set(cleaned.ma_dong)
    # A row flagged in place counts as detected even though it was not removed.
    if 'ma_sach_ngoai_danh_muc' in cleaned:
        flagged_ids=set(cleaned.loc[cleaned.ma_sach_ngoai_danh_muc.astype(bool),'ma_dong'])
    else:
        flagged_ids=set()
    fam=events[events.ho_loi.notna()].copy()
    # Duplicate families are about rows, not values; they are reported but excluded from the
    # value-level comparison because the duplicate row has no single "correct" value.
    value_families=[f for f in ERROR_FAMILIES if f in set(fam.ho_loi)]
    rows=[]
    for family in value_families:
        spec=ERROR_FAMILIES[family]
        ids=fam.loc[fam.ho_loi.eq(family),'ma_dong'].unique()
        if not len(ids):
            continue
        caught=[m for m in ids if m not in kept]
        survived=[m for m in ids if m in kept]
        flagged=[m for m in survived if m in flagged_ids]
        col=spec['col']
        wrong=0
        for m in survived:
            if m not in t.index: continue
            got=cleaned.loc[cleaned.ma_dong.eq(m),col]
            want=t.loc[m,col]
            if not len(got): continue
            g,w=got.iloc[0],want
            if col in ('so_luong','gia_ban'):
                if not np.isclose(float(g),float(w)):
                    wrong+=1
            elif str(g)!=str(w):
                wrong+=1
        detected=len(caught)+len(flagged)
        rows.append({'ho_loi':family,'n_cai':len(ids),'n_cach_ly':len(caught),
                     'n_danh_dau':len(flagged),'recall':_r(detected/len(ids)),
                     'n_lot':len(survived),'con_sai':wrong,
                     'ty_le_sot_sai':_r(wrong/len(ids)),'phat_hien_duoc':spec['detectable'],
                     'ghi_chu':spec['note']})
    out=pd.DataFrame(rows)
    # Aggregate over value families only, so the number is comparable with the per-family rows.
    total=out.n_cai.sum(); caught=out.n_cach_ly.sum(); flagged=out.n_danh_dau.sum()
    out.attrs['aggregate']={'n_cai':int(total),'n_cach_ly':int(caught),'n_danh_dau':int(flagged),
                            'recall':_r((caught+flagged)/total) if total else 1.,
                            'con_sai':int(out.con_sai.sum())}
    return out


def channel_shares(d):
    """Revenue shares under the two definitions of 'online' that this project used to conflate.

    marketplace_share counts the three sàn only; digital_channel_share adds Website, which the
    generator treats as an offline channel (0–20% discount band, like Cửa hàng).
    """
    shares=d.groupby('kenh_ban').doanh_thu.sum()/d.doanh_thu.sum()*100
    return _r(shares.reindex(MARKETPLACE_CHANNELS).sum()), _r(shares.reindex(DIGITAL_CHANNELS).sum())


def null_band(metric='rating_book_qty_r', n_seeds=200, params=None):
    """Distribution of a correlation under the generator's own null.

    The generator draws `diem_danh_gia` at catalog level and never uses it in the rate that
    produces `so_luong`, so the population correlation is zero by construction. Any single-seed
    value is therefore a draw from this distribution, and reporting it without the band invites
    reading noise as a finding. Seed 42's value is placed against this band rather than assumed
    to be inside or outside it.
    """
    p=dict(PARAMS,**(params or {}))
    rows=[]
    for seed in range(n_seeds):
        catalog,truth=generate(seed=seed,n=p['n_lines'],discount_strength=p['discount_strength'],
                               seasonality=p['seasonality'],params=p)
        raw,events=corrupt(truth,seed=seed,missing_rate=p['missing_rate'],params=p)
        c,_,_,_,_=clean(raw,catalog,params=p)
        # Grouped exactly as `summarize` groups books, so the observed value and this band are on
        # the same unit. Grouping by `ma_sach` alone was wrong: rows whose key did not resolve
        # carry the placeholder BK9999, so six different books collapsed into one fake book with
        # their quantities summed. That mismatch also made the band incomparable with the
        # reported figure.
        books=c.groupby(['ma_sach','ten_sach']).agg(so_luong=('so_luong','sum'),
                                                    diem=('diem_danh_gia','first'))
        years=c.groupby('nam_ban').doanh_thu.sum()
        rows.append({'seed':seed,
                     'rating_book_qty_r':_r(books.diem.corr(books.so_luong)),
                     'rating_qty_r':_r(c.diem_danh_gia.corr(c.so_luong)),
                     'discount_qty_r':_r(c.giam_gia_thuc_te.corr(c.so_luong)),
                     'q4_share':_r(c.loc[pd.to_datetime(c.ngay_ban).dt.quarter.eq(4),'doanh_thu'].sum()/c.doanh_thu.sum()*100),
                     'yoy_pct':_r((years.loc[2025]/years.loc[2024]-1)*100)})
    return pd.DataFrame(rows)


def null_summary(null):
    """Mean, SD and 2.5/97.5 percentiles for each metric in the null distribution."""
    rows=[]
    for col in [c for c in null.columns if c!='seed']:
        s=null[col].dropna()
        rows.append({'metric':col,'n':len(s),'mean':_r(s.mean()),'sd':_r(s.std()),
                     'p025':_r(s.quantile(.025)),'p975':_r(s.quantile(.975)),
                     'min':_r(s.min()),'max':_r(s.max())})
    return pd.DataFrame(rows)


BOOT_METRICS=('revenue','average_unit_price','rating_qty_r','rating_book_qty_r',
              'discount_qty_r','q4_share','marketplace_share','digital_channel_share')


def bootstrap(d, n_boot=2000, seed=42, metrics=BOOT_METRICS):
    """Percentile bootstrap intervals for the reported figures.

    Three things this is and is not, because conflating them is the easiest way to overclaim:

    * It IS an interval for the sampling variability of the statistic given the cleaned sample.
      Resampling rows answers "how much would this number move if the sample had come out
      slightly differently".
    * It is NOT a market confidence interval. The data are simulated, so there is no population
      to infer to. It says nothing about real book sales.
    * It is NOT the null band from `null_band`. That band asks whether a value could plausibly
      have arisen from the generator's own randomness across seeds; this one asks how precisely
      a single sample pins the value down. A value can sit inside one and outside the other, and
      the report keeps them in separate sections for exactly that reason.

    The resampling unit differs by metric, and that difference is the point. Line-level
    statistics resample transaction rows. `rating_book_qty_r` resamples whole books, because it
    is computed on one row per book: resampling lines would treat a book with 40 sales as 40
    independent observations and produce an interval that is far too narrow.
    """
    rng=np.random.default_rng(seed)
    d=d.reset_index(drop=True)
    # Same grouping as summarize: the placeholder key BK9999 marks rows whose book could not be
    # identified, so grouping on the key alone would merge several distinct books into one.
    books=(d.groupby(['ma_sach','ten_sach'])
             .agg(so_luong=('so_luong','sum'),diem=('diem_danh_gia','first'))
             .reset_index())
    shares=d.groupby('kenh_ban').doanh_thu.sum()/d.doanh_thu.sum()*100
    q4=d.assign(q=pd.to_datetime(d.ngay_ban).dt.quarter).groupby('q').doanh_thu.sum()
    n=len(d); nb=len(books)
    draws={m:[] for m in metrics}
    for _ in range(n_boot):
        s=d.iloc[rng.integers(0,n,n)]
        bs=books.iloc[rng.integers(0,nb,nb)]
        for m in metrics:
            if m=='revenue':
                draws[m].append(float(s.doanh_thu.sum()))
            elif m=='average_unit_price':
                draws[m].append(float(s.doanh_thu.sum()/s.so_luong.sum()))
            elif m=='rating_qty_r':
                draws[m].append(float(s.diem_danh_gia.corr(s.so_luong)))
            elif m=='rating_book_qty_r':
                draws[m].append(float(bs.diem.corr(bs.so_luong)))
            elif m=='discount_qty_r':
                draws[m].append(float(s.giam_gia_thuc_te.corr(s.so_luong)))
            elif m=='q4_share':
                q=pd.to_datetime(s.ngay_ban).dt.quarter
                draws[m].append(float(s.loc[q.eq(4),'doanh_thu'].sum()/s.doanh_thu.sum()*100))
            elif m=='marketplace_share':
                sh=s.groupby('kenh_ban').doanh_thu.sum()/s.doanh_thu.sum()*100
                draws[m].append(float(sh.reindex(MARKETPLACE_CHANNELS).sum()))
            elif m=='digital_channel_share':
                sh=s.groupby('kenh_ban').doanh_thu.sum()/s.doanh_thu.sum()*100
                draws[m].append(float(sh.reindex(DIGITAL_CHANNELS).sum()))
    point={'revenue':float(d.doanh_thu.sum()),
           'average_unit_price':float(d.doanh_thu.sum()/d.so_luong.sum()),
           'rating_qty_r':float(d.diem_danh_gia.corr(d.so_luong)),
           'rating_book_qty_r':float(books.diem.corr(books.so_luong)),
           'discount_qty_r':float(d.giam_gia_thuc_te.corr(d.so_luong)),
           'q4_share':float(q4.loc[4]/d.doanh_thu.sum()*100),
           'marketplace_share':float(shares.reindex(MARKETPLACE_CHANNELS).sum()),
           'digital_channel_share':float(shares.reindex(DIGITAL_CHANNELS).sum())}
    unit={'revenue':'dòng bán hàng','average_unit_price':'dòng bán hàng',
          'rating_qty_r':'dòng bán hàng','rating_book_qty_r':'đầu sách',
          'discount_qty_r':'dòng bán hàng','q4_share':'dòng bán hàng',
          'marketplace_share':'dòng bán hàng','digital_channel_share':'dòng bán hàng'}
    rows=[]
    for m in metrics:
        a=np.array([x for x in draws[m] if np.isfinite(x)])
        lo,hi=np.quantile(a,.025),np.quantile(a,.975)
        rows.append({'metric':m,'unit':unit[m],'n_boot':len(a),'point':_r(point[m]),
                     'boot_mean':_r(a.mean()),'boot_sd':_r(a.std(ddof=1)),
                     'ci_low':_r(lo),'ci_high':_r(hi),'ci_width':_r(hi-lo)})
    return pd.DataFrame(rows)


def experiments(reps=50, params=None):
    """Paired-seed scenario runs. Every generator setting comes from `params`, so the scenario
    layer can never silently run a different sample size than the base pipeline."""
    p=dict(PARAMS,**(params or {}))
    rows=[]
    scenarios=[('Cơ sở',1.,True),('Không hệ số giảm giá',0.,True),('Không mùa vụ',1.,False)]
    # Paired seeds; results are conditional Monte Carlo summaries, not market intervals.
    for seed in range(100,100+reps):
        for scenario,strength,season in scenarios:
            catalog,t=generate(seed=seed,n=p['n_lines'],discount_strength=strength,seasonality=season,params=p)
            raw,events=corrupt(t,seed=seed,missing_rate=p['missing_rate'],params=p)
            c,_,_,_,_=clean(raw,catalog,params=p)
            _,v=evaluate(t,c,raw,events)
            no_bulk=c[c.so_luong<=150]
            marketplace,digital=channel_shares(c)
            q4=c.loc[pd.to_datetime(c.ngay_ban).dt.quarter.eq(4),'doanh_thu'].sum()/c.doanh_thu.sum()*100
            rows.append({'seed':seed,'scenario':scenario,'revenue':int(c.doanh_thu.sum()),'marketplace_share':marketplace,'digital_channel_share':digital,'q4_share':_r(q4),'discount_qty_r':_r(c.giam_gia_thuc_te.corr(c.so_luong)),'discount_qty_r_without_bulk':_r(no_bulk.giam_gia_thuc_te.corr(no_bulk.so_luong)),'revenue_error_pct':v['relative_revenue_error_pct'],'retained_pct':v['retained_pct']})
    return pd.DataFrame(rows)


def catalog_coverage_sensitivity(levels=(1.0,.95,.90,.75,.50), seed=42, params=None):
    """How much the 'trustworthy catalog' assumption actually carries.

    The report calls a complete catalog a strong assumption but never measured it. Masking whole
    catalog rows shows what breaks: revenue is computed from the transaction line, so it should
    survive; attribute completeness should not.
    """
    p=dict(PARAMS,**(params or {}))
    rows=[]
    for coverage in levels:
        q=dict(p,catalog_coverage=coverage)
        catalog,truth=generate(seed=seed,n=p['n_lines'],discount_strength=p['discount_strength'],
                               seasonality=p['seasonality'],params=p)
        raw,events=corrupt(truth,seed=seed,missing_rate=p['missing_rate'],params=p)
        c,_,quar,_,_=clean(raw,catalog,params=q)
        _,v=evaluate(truth,c,raw,events)
        unknown_key=quar.ly_do.eq('unknown_book_key').sum() if len(quar) else 0
        rows.append({'catalog_coverage':coverage,'lines':len(c),'revenue':int(c.doanh_thu.sum()),
                     'relative_revenue_error_pct':v['relative_revenue_error_pct'],
                     'retained_pct':v['retained_pct'],
                     'unknown_author_pct':_r(c.tac_gia.eq('Không rõ tác giả').mean()*100),
                     'unknown_publisher_pct':_r(c.nha_xuat_ban.eq('Không rõ NXB').mean()*100),
                     'rating_known_pct':_r(c.diem_danh_gia.notna().mean()*100),
                     'quarantined':len(quar),'quarantined_pct':_r(len(quar)/len(raw)*100),
                     'unknown_book_key':int(unknown_key)})
    return pd.DataFrame(rows)


MISSING_MECHANISMS=('MCAR','MAR','MNAR')
MISSING_METHODS=('Giữ thiếu','Trung bình toàn cục','Trung bình thể loại','Trung vị thể loại')


def missing_sensitivity(truth, seed=42, rates=(.02,.10,.25), n_seeds=100, params=None):
    """Missing-data experiment across mechanism x rate x method.

    The previous version used one seed, one mechanism (MCAR) and omitted the global-mean baseline,
    so it could not support any claim about which imputation method is better. Three mechanisms
    are needed because they fail differently: MCAR is ignorable, MAR depends on an observed
    variable, and MNAR depends on the missing value itself, which no imputation can undo.
    """
    p=dict(PARAMS,**(params or {}))
    base=truth.copy()
    base['ngay_ban']=pd.to_datetime(base.ngay_ban)
    rows=[]
    for rate in rates:
        for mechanism in MISSING_MECHANISMS:
            for s in range(n_seeds):
                rng=np.random.default_rng(seed+40000+s)
                masked=base.copy()
                n=len(masked)
                if mechanism=='MCAR':
                    prob=np.full(n,rate)
                elif mechanism=='MAR':
                    # Higher-priced books are less likely to carry a rating: missingness depends
                    # on an observed variable, so conditioning on it can recover the mean.
                    price_rank=masked.gia_ban.rank(pct=True).to_numpy()
                    prob=rate*(0.2+1.6*price_rank)
                else:
                    # Low ratings are more likely to be missing: missingness depends on the value
                    # itself, so every imputation is biased toward the observed mean.
                    rating=masked.diem_danh_gia.to_numpy()
                    low=(5-rating)/4
                    prob=rate*(0.2+1.6*low)
                prob=np.clip(prob,0,1)
                hidden=rng.random(n)<prob
                masked.loc[hidden,'diem_danh_gia']=np.nan
                if not hidden.any():
                    continue
                global_mean=masked.diem_danh_gia.mean()
                global_median=masked.diem_danh_gia.median()
                genre_mean=masked.groupby('the_loai').diem_danh_gia.transform('mean')
                genre_median=masked.groupby('the_loai').diem_danh_gia.transform('median')
                fills={'Giữ thiếu':masked.diem_danh_gia,
                       'Trung bình toàn cục':masked.diem_danh_gia.fillna(global_mean),
                       'Trung bình thể loại':masked.diem_danh_gia.fillna(genre_mean),
                       'Trung vị thể loại':masked.diem_danh_gia.fillna(genre_median)}
                for method,filled in fills.items():
                    truth_hidden=base.loc[hidden,'diem_danh_gia']
                    if method=='Giữ thiếu':
                        mae=np.nan
                    else:
                        mae=float((filled.loc[hidden]-truth_hidden).abs().mean())
                    rows.append({'missing_rate':rate,'mechanism':mechanism,'method':method,'seed':s,
                                 'n_hidden':int(hidden.sum()),'mae_imputed':mae,
                                 'mean_rating':_r(filled.mean()),
                                 'rating_qty_r':_r(filled.corr(base.so_luong))})
    raw=pd.DataFrame(rows)
    agg=(raw.groupby(['mechanism','missing_rate','method'],sort=False)
            .agg(n_seeds=('seed','size'),mae_mean=('mae_imputed','mean'),mae_sd=('mae_imputed','std'),
                 mean_rating=('mean_rating','mean'),rating_qty_r=('rating_qty_r','mean'))
            .reset_index())
    agg['mae_mean']=agg.mae_mean.round(DECIMALS)
    agg['mae_sd']=agg.mae_sd.round(DECIMALS)
    agg['mcse_mean']=(agg.mae_sd/agg.n_seeds**.5).round(DECIMALS)
    agg['mean_rating']=agg.mean_rating.round(DECIMALS)
    agg['rating_qty_r']=agg.rating_qty_r.round(DECIMALS)
    return agg, raw
