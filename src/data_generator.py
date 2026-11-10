"""All identities, transactions and parameters are fictional; no market calibration."""
import numpy as np
import pandas as pd
from .config import PARAMS, GENRES, CHANNELS


def generate(seed=42, n=None, discount_strength=1., seasonality=True, params=None):
    p = dict(PARAMS, **(params or {}))
    n = p['n_lines'] if n is None else n
    rng = np.random.default_rng(seed)
    k = p['n_books']
    catalog = pd.DataFrame({
        'ma_sach': [f'BK{i+1:04}' for i in range(k)],
        'ten_sach': [f'Sách mô phỏng {i+1:03}' for i in range(k)],
        'the_loai': np.repeat(GENRES, k // len(GENRES)),
        'tac_gia': [f'Tác giả giả lập {i:02}' for i in rng.integers(1,41,k)],
        'nha_xuat_ban': [f'NXB giả lập {i:02}' for i in rng.integers(1,9,k)],
        'nam_xuat_ban': rng.integers(p['catalog_year_min'],p['catalog_year_max']+1,k),
        'gia_goc': np.clip(np.round(rng.lognormal(np.log(p['price_median']),p['price_log_sd'],k)/1000)*1000,p['price_min'],p['price_max']).astype(int),
        'diem_danh_gia': np.round(1+4*rng.beta(p['rating_beta_a'],p['rating_beta_b'],k),1),
    })
    genres = rng.choice(len(GENRES),n,p=p['genre_weights'])
    book_idx = genres*(k//len(GENRES))+rng.integers(0,k//len(GENRES),n)
    truth = catalog.iloc[book_idx].reset_index(drop=True).copy()
    dates = pd.date_range(p['start'],p['end'])
    truth['ngay_ban'] = rng.choice(dates,n)
    truth['kenh_ban'] = rng.choice(CHANNELS,n,p=p['channel_weights'])
    truth['ma_dong'] = [f'L{i+1:06}' for i in range(n)]
    # One simulated single-title order per line; this restriction is explicit.
    truth['ma_don'] = [f'O{i+1:06}' for i in range(n)]
    online = truth.kenh_ban.isin(CHANNELS[:3])
    truth['giam_gia_niem_yet'] = np.where(online, rng.choice([0,5,10,15,20,25,30,35,40],n), rng.choice([0,5,10,15,20],n))
    truth['gia_ban'] = (np.round(truth.gia_goc*(1-truth.giam_gia_niem_yet/100)/1000)*1000).astype(int)
    month = truth.ngay_ban.dt.month
    seasonal = np.where(month.isin([11,12]),p['season_peak'],np.where(month.isin([8,9]),p['season_shoulder'],1.0)) if seasonality else np.ones(n)
    lam = p['lam_base']*seasonal*np.maximum(.5,1.8-truth.gia_ban/p['lam_price_scale'])*(1+discount_strength*truth.giam_gia_niem_yet/30)
    truth['so_luong'] = 1+rng.poisson(lam)
    # Valid, rare bulk orders demonstrate that an outlier is not necessarily an error.
    bulk_rng = np.random.default_rng(seed+77)
    bulk = bulk_rng.choice(n,p['n_bulk'],replace=False)
    truth.loc[bulk,'so_luong'] = bulk_rng.integers(p['bulk_qty_min'],p['bulk_qty_max']+1,len(bulk))
    truth['ngay_ban'] = truth.ngay_ban.dt.strftime('%Y-%m-%d')
    return catalog, truth


def corrupt(truth, seed=42, missing_rate=None, params=None):
    p = dict(PARAMS, **(params or {}))
    missing_rate = p['missing_rate'] if missing_rate is None else missing_rate
    rng = np.random.default_rng(seed+10000)
    raw = truth.copy()
    events = []
    def log(idx,col,kind):
        for i in idx:
            events.append({'ma_dong':str(truth.loc[i,'ma_dong']),'cot':col,'loai_loi':kind,'gia_tri_chuan':str(truth.loc[i,col])})
    for col in ['tac_gia','nha_xuat_ban','nam_xuat_ban','diem_danh_gia']:
        idx = rng.choice(len(raw),round(len(raw)*missing_rate),replace=False)
        raw.loc[idx,col] = np.nan
        log(idx,col,'missing')
    idx = rng.choice(len(raw),p['n_format_genre'],replace=False)
    raw.loc[idx,'the_loai'] = raw.loc[idx,'the_loai'].map(lambda s:'  '+s.upper()+'  ')
    log(idx,'the_loai','format')
    raw['gia_ban'] = raw.gia_ban.astype(object)
    idx = rng.choice(len(raw),p['n_currency_format'],replace=False)
    raw.loc[idx,'gia_ban'] = raw.loc[idx,'gia_ban'].map(lambda x:f'{x:,} VNĐ')
    log(idx,'gia_ban','currency_format')
    idx = rng.choice(len(raw),p['n_invalid_price'],replace=False)
    raw.loc[idx,'gia_ban'] = -50000
    log(idx,'gia_ban','invalid_price')
    bad_qty = rng.choice(len(raw),p['n_invalid_qty'],replace=False)
    raw.loc[bad_qty[:8],'so_luong'] = p['invalid_qty_high']
    raw.loc[bad_qty[8:],'so_luong'] = p['invalid_qty_low']
    log(bad_qty,'so_luong','invalid_qty')
    exact = raw.iloc[rng.choice(len(raw),p['n_dup_exact'],replace=False)].copy()
    formatted = raw.iloc[rng.choice(len(raw),p['n_dup_format'],replace=False)].copy()
    formatted['the_loai'] = formatted.the_loai.str.lower().str.strip()
    good = np.setdiff1d(np.arange(len(raw)),bad_qty)
    conflicts = rng.choice(good,p['n_conflicts'],replace=False)
    contradictory = raw.iloc[conflicts].copy()
    contradictory['so_luong'] += 1
    log(conflicts,'so_luong','duplicate_conflict')
    for block,kind in [(exact,'duplicate_exact'),(formatted,'duplicate_format')]:
        for _,r in block.iterrows():
            events.append({'ma_dong':r.ma_dong,'cot':'*','loai_loi':kind,'gia_tri_chuan':''})
    raw = pd.concat([raw,exact,formatted,contradictory],ignore_index=True).sample(frac=1,random_state=seed).reset_index(drop=True)
    raw.insert(0,'raw_row_id',[f'R{i+1:06}' for i in range(len(raw))])
    return raw, pd.DataFrame(events)
