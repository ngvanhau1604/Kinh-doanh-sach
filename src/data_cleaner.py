"""Cleaning sees raw observations and master catalog only, never ground truth/error labels."""
import re
import numpy as np
import pandas as pd
from .config import CAT_FIELDS, GENRES, CHANNELS, PARAMS, PRICE_LABELS, RATING_LABELS, DISCOUNT_LABELS


def price_group(s):
    # np.select sends NaN to `default`, which used to label a missing price as the highest
    # segment — a silent bias toward the premium bucket. Missing stays missing.
    out = pd.Series(np.select([s<80000,s<=200000],PRICE_LABELS[:2],default=PRICE_LABELS[2]),index=s.index)
    return out.where(s.notna(),'Chưa biết')


def rating_group(s):
    out = pd.cut(s,bins=[-np.inf,3,4,4.5,np.inf],right=False,labels=RATING_LABELS).astype('string')
    return out.fillna('Chưa biết')


def features(d):
    d=d.copy()
    d['ngay_ban']=pd.to_datetime(d.ngay_ban).dt.strftime('%Y-%m-%d')
    dt=pd.to_datetime(d.ngay_ban)
    d['doanh_thu']=d.gia_ban*d.so_luong
    d['giam_gia_thuc_te']=(100*(1-d.gia_ban/d.gia_goc)).round(3)
    d['phan_khuc_gia']=price_group(d.gia_ban)
    d['nhom_danh_gia']=rating_group(d.diem_danh_gia)
    d['thang_nam']=dt.dt.strftime('%Y-%m')
    d['nam_ban']=dt.dt.year
    d['quy_ban']=dt.dt.to_period('Q').astype(str)
    d['nhom_giam_gia']=pd.cut(d.giam_gia_niem_yet,[-1,5,15,25,40],labels=DISCOUNT_LABELS).astype('string')
    return d


def parse_price(v):
    if pd.isna(v): return np.nan
    if isinstance(v,(int,float,np.number)): return float(v)
    s=str(v).strip().replace('VNĐ','').replace('VND','').strip()
    if re.fullmatch(r'-?\d{1,3}(?:[,\.]\d{3})+',s): s=s.replace(',','').replace('.','')
    try: return float(s)
    except ValueError: return np.nan


def mask_catalog(catalog, coverage, seed):
    """Blank a fraction of catalog attributes to make `catalog_coverage` a live assumption.

    The report calls a trustworthy, complete catalog a strong assumption but never measured how
    strong. Masking whole rows (not cells) is the realistic failure: a book is either in the
    master data or it is not. Deterministic in `seed` so a scenario is reproducible.

    Returns the masked catalog and the set of book keys that lost their record. The caller must
    also blank those attributes on the transaction rows: in a real pipeline the transaction file
    carries only `ma_sach` and the descriptive fields arrive through the join, so an incomplete
    catalog means the join yields nothing. Masking the catalog alone would measure almost nothing,
    because the simulated transaction rows happen to carry their own copy of every attribute.
    """
    if coverage >= 1.0:
        return catalog, set()
    out = catalog.copy()
    rng = np.random.default_rng(seed + 30000)
    n = len(out)
    n_masked = int(round(n * (1 - coverage)))
    if n_masked <= 0:
        return out, set()
    idx = rng.choice(n, n_masked, replace=False)
    masked_keys = set(out.loc[out.index[idx], 'ma_sach'])
    out.loc[out.index[idx], CAT_FIELDS] = np.nan
    return out, masked_keys


def clean(raw,catalog,params=None):
    p=dict(PARAMS,**(params or {}))
    catalog,masked_keys=mask_catalog(catalog,p['catalog_coverage'],p['seed'])
    if catalog.ma_sach.duplicated().any(): raise ValueError('Catalog key must be unique')
    d=raw.copy()
    # Model the failed join: a book with no catalog record contributes no descriptive attributes.
    if masked_keys:
        hit=d.ma_sach.isin(masked_keys)
        if hit.any(): d.loc[hit,CAT_FIELDS]=np.nan
    before=d.copy(); stages=[]; changes=[]
    basecols=['ma_dong','ma_don','ma_sach']+CAT_FIELDS+['ngay_ban','kenh_ban','giam_gia_niem_yet','gia_ban','so_luong']
    def stage(name): stages.append({'buoc':name,'so_dong':len(d),'o_thieu':int(d[basecols].isna().sum().sum()),'ma_dong_lap':int(d.ma_dong.duplicated().sum())})
    stage('01. Nạp dữ liệu')
    mapping={g.casefold():g for g in GENRES}
    d['the_loai']=d.the_loai.map(lambda v:mapping.get(' '.join(str(v).split()).casefold(),str(v).strip()))
    for c in ['tac_gia','nha_xuat_ban','ten_sach','kenh_ban']:
        d[c]=d[c].astype('string').str.strip().str.replace(r'\s+',' ',regex=True)
    d['gia_ban']=d.gia_ban.map(parse_price)
    for c in ['gia_goc','giam_gia_niem_yet','so_luong','nam_xuat_ban','diem_danh_gia']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    master=catalog.set_index('ma_sach')
    for c in CAT_FIELDS:
        missing=d[c].isna()
        mapped=d.ma_sach.map(master[c])
        restored=missing & mapped.notna()
        d[f'khoi_phuc_{c}']=restored
        if restored.any(): d.loc[restored,c]=mapped.loc[restored].astype(d[c].dtype)
    valid_basis=(d.gia_goc>0)&d.giam_gia_niem_yet.between(0,100,inclusive='left')
    bad=(d.gia_ban.isna()|(d.gia_ban<=0))&valid_basis
    d['gia_ban_duoc_sua']=bad
    d.loc[bad,'gia_ban']=(d.loc[bad,'gia_goc']*(1-d.loc[bad,'giam_gia_niem_yet']/100)).round(-3)
    stage('02. Chuẩn hóa và khôi phục có căn cứ')
    # Preserve cell-level change provenance, including currency parsing.
    for c in basecols:
        a=before[c].astype('string').fillna('<NA>'); b=d[c].astype('string').fillna('<NA>')
        for i in d.index[a.ne(b)]:
            changes.append({'raw_row_id':d.loc[i,'raw_row_id'],'ma_dong':d.loc[i,'ma_dong'],'cot':c,'truoc':a.loc[i],'sau':b.loc[i]})
    # Identical after normalization may be safely collapsed by the stable line key.
    duplicate=d.duplicated(subset=basecols,keep='first')
    duplicate_rows=d.loc[duplicate,['raw_row_id','ma_dong']].copy()
    duplicate_rows['trang_thai']='duplicate_collapsed'
    d=d.loc[~duplicate].copy()
    stage('03. Gộp bản sao cùng mã và cùng nội dung')
    conflict=d.ma_dong.duplicated(keep=False)
    reason=pd.Series('',index=d.index,dtype='string')
    reason.loc[conflict]='conflicting_line_id'
    invalid_qty=d.so_luong.isna()|(d.so_luong<=0)|(d.so_luong%1!=0)|(d.so_luong>p['max_qty_review'])
    reason.loc[invalid_qty]='quantity_needs_review'
    bad_date=~pd.to_datetime(d.ngay_ban,format='%Y-%m-%d',errors='coerce').between(pd.Timestamp(p['start']),pd.Timestamp(p['end']))
    # Referential integrity is flagged, not quarantined. A transaction whose book key is absent
    # from the master catalog still carries a real price, quantity and date, so its revenue is
    # valid even though its descriptive attributes are not. Quarantining it would discard sound
    # money data because a label is missing, which is the wrong trade for an analysis whose
    # primary measure is revenue. The row is kept, the attributes stay missing, and the flag
    # records that they could not be verified.
    d['ma_sach_ngoai_danh_muc']=~d.ma_sach.isin(master.index)
    invalid_schema=bad_date|d.ma_dong.isna()|d.ma_don.isna()|d.ma_sach.isna()|~d.the_loai.isin(GENRES)|~d.kenh_ban.isin(CHANNELS)|~d.giam_gia_niem_yet.between(0,100,inclusive='left')|d.gia_goc.isna()|(d.gia_goc<=0)|d.gia_ban.isna()|(d.gia_ban<=0)|(d.gia_ban>d.gia_goc)
    invalid_schema |= (d.diem_danh_gia.notna() & ~d.diem_danh_gia.between(1,5)) | (d.nam_xuat_ban.notna() & (~d.nam_xuat_ban.between(1900,2023) | (d.nam_xuat_ban%1!=0)))
    reason.loc[invalid_schema]='invalid_required_fields'
    quarantine=d.loc[reason.ne('')].copy(); quarantine['ly_do']=reason[reason.ne('')]
    d=d.loc[reason.eq('')].copy()
    q1,q3=d.so_luong.quantile([.25,.75]); threshold=q3+1.5*(q3-q1)
    d['co_ngoai_lai_iqr']=d.so_luong>threshold  # Flag only: bulk sales remain.
    stage('04. Cách ly bất thường và xung đột')
    d=features(d).sort_values(['ngay_ban','ma_dong']).reset_index(drop=True)
    for c in ['gia_goc','gia_ban','so_luong','doanh_thu']: d[c]=d[c].astype('int64')
    for c,label in [('tac_gia','Không rõ tác giả'),('nha_xuat_ban','Không rõ NXB')]: d[c]=d[c].fillna(label)
    retained=d[['raw_row_id','ma_dong']].copy(); retained['trang_thai']='retained'
    q=quarantine[['raw_row_id','ma_dong','ly_do']].rename(columns={'ly_do':'trang_thai'})
    lineage=pd.concat([duplicate_rows,retained,q],ignore_index=True)
    return d,pd.DataFrame(stages),quarantine,pd.DataFrame(changes),lineage
