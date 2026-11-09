import numpy as np
import pandas as pd
from .config import PARAMS, MARKETPLACE_CHANNELS, DIGITAL_CHANNELS
from .data_cleaner import features,clean
from .data_generator import generate,corrupt

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
    intended=set(events.loc[events.loai_loi.isin(['invalid_qty','duplicate_conflict']),'ma_dong'])
    removed=set(t.index)-set(c.index)
    return pd.DataFrame(matches), {'truth_revenue':int(t.doanh_thu.sum()),'clean_revenue':int(c.doanh_thu.sum()),'relative_revenue_error_pct':_r(100*(c.doanh_thu.sum()/t.doanh_thu.sum()-1)),'retained_pct':_r(len(c)/len(t)*100),'quarantine_precision':_r(len(removed&intended)/len(removed) if removed else 1.),'quarantine_recall':_r(len(removed&intended)/len(intended) if intended else 1.),'retained_revenue_error':int(c.doanh_thu.sum()-t.loc[c.index].doanh_thu.sum()),'unresolved_missing':int(c[cols].isna().sum().sum())}


def channel_shares(d):
    """Revenue shares under the two definitions of 'online' that this project used to conflate.

    marketplace_share counts the three sàn only; digital_channel_share adds Website, which the
    generator treats as an offline channel (0–20% discount band, like Cửa hàng).
    """
    shares=d.groupby('kenh_ban').doanh_thu.sum()/d.doanh_thu.sum()*100
    return _r(shares.reindex(MARKETPLACE_CHANNELS).sum()), _r(shares.reindex(DIGITAL_CHANNELS).sum())


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
            c,_,_,_,_=clean(raw,catalog)
            _,v=evaluate(t,c,raw,events)
            no_bulk=c[c.so_luong<=150]
            marketplace,digital=channel_shares(c)
            q4=c.loc[pd.to_datetime(c.ngay_ban).dt.quarter.eq(4),'doanh_thu'].sum()/c.doanh_thu.sum()*100
            rows.append({'seed':seed,'scenario':scenario,'revenue':int(c.doanh_thu.sum()),'marketplace_share':marketplace,'digital_channel_share':digital,'q4_share':_r(q4),'discount_qty_r':_r(c.giam_gia_thuc_te.corr(c.so_luong)),'discount_qty_r_without_bulk':_r(no_bulk.giam_gia_thuc_te.corr(no_bulk.so_luong)),'revenue_error_pct':v['relative_revenue_error_pct'],'retained_pct':v['retained_pct']})
    return pd.DataFrame(rows)


def missing_sensitivity(truth,seed=42):
    rows=[]; rng=np.random.default_rng(seed+20000)
    for rate in [.02,.10,.25]:
        masked=truth.copy(); idx=rng.choice(len(truth),round(len(truth)*rate),replace=False)
        masked.loc[idx,'diem_danh_gia']=np.nan
        means=masked.groupby('the_loai').diem_danh_gia.transform('mean')
        for method,filled in [('Giữ thiếu',masked.diem_danh_gia),('Trung bình thể loại',masked.diem_danh_gia.fillna(means))]:
            known=filled.notna(); error=(filled.loc[idx]-truth.loc[idx,'diem_danh_gia']).abs()
            rows.append({'missing_rate':rate,'method':method,'coverage':_r(known.mean()),'mae_imputed':_r(error.mean()) if error.notna().any() else None,'mean_rating':_r(filled.mean()),'rating_qty_r':_r(filled.corr(truth.so_luong))})
    return pd.DataFrame(rows)
