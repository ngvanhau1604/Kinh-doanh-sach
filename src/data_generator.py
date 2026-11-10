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


# Injected defect families. Each is a distinct failure mode with its own detectability, and the
# point of separating them is that one aggregate precision/recall figure hides exactly that
# difference. `detectable` records what a value-domain rule can see, decided by construction:
#   yes    — the value leaves its legal domain, so a range check catches it
#   partly — some draws leave the domain and some stay inside it
#   no     — the value stays legal, so no rule that does not know the truth can catch it
# Counts are Poisson draws, so the number of defects per run is itself random. That is what makes
# `retained_pct` a random quantity with a real standard error instead of a design constant.
ERROR_FAMILIES = {
    'qty_scale':       dict(lam=6, col='so_luong', detectable='partly',
                            note='Số cuốn nhân 10^k; phần lớn vẫn nằm dưới ngưỡng rà soát.'),
    'qty_negative':    dict(lam=3, col='so_luong', detectable='yes',
                            note='Số cuốn âm; vi phạm miền giá trị.'),
    'qty_fractional':  dict(lam=3, col='so_luong', detectable='yes',
                            note='Số cuốn không nguyên; vi phạm miền giá trị.'),
    'price_reset':     dict(lam=6, col='gia_ban', detectable='no',
                            note='Giá bán đặt lại bằng giá gốc; mất chiết khấu nhưng giá vẫn hợp lệ.'),
    'price_swap':      dict(lam=6, col='gia_ban', detectable='partly',
                            note='Hoán vị giá bán giữa hai dòng; chỉ lộ khi giá vượt giá gốc.'),
    'date_swap':       dict(lam=7, col='ngay_ban', detectable='partly',
                            note='Đảo ngày/tháng khi biểu diễn được, còn lại lùi một năm.'),
    'genre_mislabel':  dict(lam=5, col='the_loai', detectable='no',
                            note='Thể loại hợp lệ nhưng sai; không thể phát hiện bằng miền giá trị.'),
    'catalog_missing': dict(lam=5, col='ma_sach', detectable='yes',
                            note='Mã sách không có trong danh mục; phát hiện bằng kiểm tra tham chiếu.'),
}


def corrupt(truth, seed=42, missing_rate=None, params=None):
    p = dict(PARAMS, **(params or {}))
    missing_rate = p['missing_rate'] if missing_rate is None else missing_rate
    rng = np.random.default_rng(seed+10000)
    raw = truth.copy()
    events = []

    def log(idx, col, kind, family=None):
        for i in idx:
            events.append({'ma_dong': str(truth.loc[i, 'ma_dong']), 'cot': col, 'loai_loi': kind,
                           'ho_loi': family or kind, 'gia_tri_chuan': str(truth.loc[i, col])})

    n = len(raw)
    # Disjoint row blocks: each injected row carries exactly one family label, so per-family
    # recall is attributable. Overlapping injections would make the denominators ambiguous.
    order = rng.permutation(n)
    cursor = 0

    def block(count):
        nonlocal cursor
        count = int(min(max(count, 0), max(0, n - cursor)))
        idx = order[cursor:cursor + count]
        cursor += count
        return idx

    for col in ['tac_gia','nha_xuat_ban','nam_xuat_ban','diem_danh_gia']:
        idx = rng.choice(len(raw),round(len(raw)*missing_rate),replace=False)
        raw.loc[idx,col] = np.nan
        log(idx,col,'missing','missing')

    idx = rng.choice(len(raw),p['n_format_genre'],replace=False)
    raw.loc[idx,'the_loai'] = raw.loc[idx,'the_loai'].map(lambda s:'  '+s.upper()+'  ')
    log(idx,'the_loai','format','format')
    raw['gia_ban'] = raw.gia_ban.astype(object)
    idx = rng.choice(len(raw),p['n_currency_format'],replace=False)
    raw.loc[idx,'gia_ban'] = raw.loc[idx,'gia_ban'].map(lambda x:f'{x:,} VNĐ')
    log(idx,'gia_ban','currency_format','currency_format')
    idx = rng.choice(len(raw),p['n_invalid_price'],replace=False)
    raw.loc[idx,'gia_ban'] = -50000
    log(idx,'gia_ban','invalid_price','invalid_price')

    counts = {h: int(rng.poisson(spec['lam'])) for h, spec in ERROR_FAMILIES.items()}

    # Quantity families. A scale error is the interesting one: q*10 stays under the review
    # threshold for most books, so the rule cannot see it and the error survives into the
    # cleaned data. That is the defect the single 100% recall figure used to hide.
    idx = block(counts['qty_scale'])
    if len(idx):
        k = rng.integers(1, 4, len(idx))
        raw.loc[idx, 'so_luong'] = raw.loc[idx, 'so_luong'].to_numpy() * 10 ** k
        log(idx, 'so_luong', 'qty_scale', 'qty_scale')
    idx = block(counts['qty_negative'])
    if len(idx):
        raw.loc[idx, 'so_luong'] = -raw.loc[idx, 'so_luong'].to_numpy()
        log(idx, 'so_luong', 'qty_negative', 'qty_negative')
    idx = block(counts['qty_fractional'])
    if len(idx):
        # Cast first: assigning floats into an int64 column is a deprecated pandas pattern.
        raw['so_luong'] = raw.so_luong.astype(float)
        raw.loc[idx, 'so_luong'] = raw.loc[idx, 'so_luong'].to_numpy() + 0.5
        log(idx, 'so_luong', 'qty_fractional', 'qty_fractional')

    # Price families: both leave a legal price behind, so they are invisible to a range check.
    idx = block(counts['price_reset'])
    if len(idx):
        raw.loc[idx, 'gia_ban'] = raw.loc[idx, 'gia_goc'].to_numpy()
        log(idx, 'gia_ban', 'price_reset', 'price_reset')
    idx = block(counts['price_swap'])
    if len(idx) >= 2:
        # Only paired rows are actually swapped; an odd leftover row must not be logged as a
        # defect it never received, or the recall denominator counts a phantom.
        paired = idx[:len(idx) - len(idx) % 2]
        pairs = paired.reshape(-1, 2)
        a, b = pairs[:, 0], pairs[:, 1]
        va, vb = raw.loc[a, 'gia_ban'].to_numpy(), raw.loc[b, 'gia_ban'].to_numpy()
        raw.loc[a, 'gia_ban'] = vb
        raw.loc[b, 'gia_ban'] = va
        log(paired, 'gia_ban', 'price_swap', 'price_swap')

    # Date family: swapping day and month keeps the date inside the simulated period whenever
    # both components are <= 12, so the row passes every date check.
    idx = block(counts['date_swap'])
    if len(idx):
        dt = pd.to_datetime(raw.loc[idx, 'ngay_ban'])
        # A day/month transposition is only representable when the day is <= 12. Where it is not,
        # the realistic import error is a year shift, which does leave the simulated period — so
        # this family is partly detectable, and the split is reported rather than hidden.
        swappable = ((dt.dt.day <= 12) & (dt.dt.month <= 12)).to_numpy()
        swapped_idx, shifted_idx = idx[swappable], idx[~swappable]
        if len(swapped_idx):
            d2 = pd.to_datetime(raw.loc[swapped_idx, 'ngay_ban'])
            swapped = pd.to_datetime(dict(year=d2.dt.year, month=d2.dt.day, day=d2.dt.month))
            raw.loc[swapped_idx, 'ngay_ban'] = swapped.dt.strftime('%Y-%m-%d').to_numpy()
        if len(shifted_idx):
            d3 = pd.to_datetime(raw.loc[shifted_idx, 'ngay_ban'])
            raw.loc[shifted_idx, 'ngay_ban'] = (d3 - pd.DateOffset(years=1)).dt.strftime('%Y-%m-%d').to_numpy()
        log(idx, 'ngay_ban', 'date_swap', 'date_swap')

    # Genre family: a legal but wrong label. Kept, not quarantined — the cleaning pipeline has no
    # information that could identify it, and inventing a rule that reads the truth would be
    # exactly the defect this project is trying to avoid. Its effect is measured, not removed.
    idx = block(counts['genre_mislabel'])
    if len(idx):
        current = raw.loc[idx, 'the_loai'].to_numpy()
        choices = np.array(GENRES)
        replacement = []
        for g in current:
            options = choices[choices != g]
            replacement.append(options[rng.integers(0, len(options))])
        raw.loc[idx, 'the_loai'] = replacement
        log(idx, 'the_loai', 'genre_mislabel', 'genre_mislabel')

    # Catalog family: the key does not resolve, which a referential-integrity check can see.
    idx = block(counts['catalog_missing'])
    if len(idx):
        raw.loc[idx, 'ma_sach'] = 'BK9999'
        log(idx, 'ma_sach', 'catalog_missing', 'catalog_missing')

    exact = raw.iloc[rng.choice(len(raw),p['n_dup_exact'],replace=False)].copy()
    formatted = raw.iloc[rng.choice(len(raw),p['n_dup_format'],replace=False)].copy()
    formatted['the_loai'] = formatted.the_loai.str.lower().str.strip()
    bad_qty = raw.index[raw.so_luong.le(0) | raw.so_luong.mod(1).ne(0) | raw.so_luong.gt(p['max_qty_review'])].to_numpy()
    good = np.setdiff1d(np.arange(len(raw)),bad_qty)
    conflicts = rng.choice(good,p['n_conflicts'],replace=False)
    contradictory = raw.iloc[conflicts].copy()
    contradictory['so_luong'] += 1
    log(conflicts,'so_luong','duplicate_conflict','duplicate_conflict')
    for block_,kind in [(exact,'duplicate_exact'),(formatted,'duplicate_format')]:
        for _,r in block_.iterrows():
            events.append({'ma_dong':r.ma_dong,'cot':'*','loai_loi':kind,'ho_loi':kind,'gia_tri_chuan':''})
    raw = pd.concat([raw,exact,formatted,contradictory],ignore_index=True).sample(frac=1,random_state=seed).reset_index(drop=True)
    raw.insert(0,'raw_row_id',[f'R{i+1:06}' for i in range(len(raw))])
    return raw, pd.DataFrame(events)
