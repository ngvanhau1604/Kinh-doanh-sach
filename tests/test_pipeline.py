import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
import pytest
from src.data_generator import generate,corrupt
from src.data_cleaner import clean,price_group,rating_group,parse_price
from src.config import PRICE_LABELS,RATING_LABELS,CAT_FIELDS
from src.analysis import evaluate,summarize

@pytest.fixture(scope='module')
def bundle():
    cat,t=generate();r,e=corrupt(t);d,s,q,c,l=clean(r,cat)
    return cat,t,r,e,d,s,q,c,l

def test_boundaries():
    assert price_group(pd.Series([79999,80000,200000,200001])).tolist()==[PRICE_LABELS[0],PRICE_LABELS[1],PRICE_LABELS[1],PRICE_LABELS[2]]
    assert rating_group(pd.Series([2.9,3.,4.,4.5,5.,np.nan])).tolist()==RATING_LABELS+[RATING_LABELS[-1],'Chưa biết']

@pytest.mark.parametrize('value,expected',[('120,000 VNĐ',120000),('120.000 VND',120000),('120000',120000),('-50000',-50000)])
def test_price_formats(value,expected):assert parse_price(value)==expected

def test_known_truth_recovery(bundle):
    """Recovery is now a measured quantity, not a perfect score.

    The old assertion required every retained field to match the truth exactly, which was only
    possible because every injected defect sat outside its legal domain. Families that produce a
    legal but wrong value (price reset, price swap, date swap, genre mislabel) survive cleaning by
    design, so a 100% match rate would mean the defect set had been made trivial again.
    """
    cat,t,r,e,d,s,q,c,l=bundle
    matches,v=evaluate(t,d,r,e)
    # Rows flagged as outside the catalog have no verifiable description by design, so the
    # exactness check applies to the rows whose description the catalog can confirm.
    verifiable=d.loc[~d.ma_sach_ngoai_danh_muc.astype(bool)]
    tv=t[t.ma_dong.isin(verifiable.ma_dong)]
    mv,_=evaluate(tv,verifiable,r,r.iloc[:0].assign(ho_loi=pd.Series(dtype=object)))
    exact={'diem_danh_gia','nam_xuat_ban','nha_xuat_ban'}
    for row in mv.itertuples():
        if row.cot in exact:
            assert row.ty_le_khop==1, f'{row.cot} should match the truth exactly'
    # Every other field must at least be overwhelmingly correct, and the shortfall must be
    # attributable to the undetectable families rather than to a broken rule.
    assert matches.ty_le_khop.min()>0.99
    assert v['quarantine_precision']==1
    assert 0<v['quarantine_recall']<1
    assert not d.ma_dong.duplicated().any()

def test_undetectable_families_are_reported_not_hidden(bundle):
    """The families a range check cannot see must show up as surviving errors, not as recall."""
    from src.analysis import error_family_performance
    cat,t,r,e,d,s,q,c,l=bundle
    fam=error_family_performance(t,d,r,e).set_index('ho_loi')
    for family in ['price_reset','genre_mislabel']:
        assert fam.loc[family,'phat_hien_duoc']=='no'
        assert fam.loc[family,'recall']==0
        assert fam.loc[family,'con_sai']>0
    for family in ['qty_negative','qty_fractional']:
        assert fam.loc[family,'recall']==1
        assert fam.loc[family,'con_sai']==0
    # A missing catalog record is detected by a flag, not by removal: the row's own price and
    # quantity are still valid, so its revenue must stay in the analysis.
    assert fam.loc['catalog_missing','recall']==1
    assert fam.loc['catalog_missing','n_cach_ly']==0
    assert fam.loc['catalog_missing','n_danh_dau']>0
    assert fam.attrs['aggregate']['recall']<1

def test_no_unaccounted_rows(bundle):
    cat,t,r,e,d,s,q,c,l=bundle
    assert len(l)==len(r)==l.raw_row_id.nunique()
    assert set(l.raw_row_id)==set(r.raw_row_id)
    assert len(d)+len(q)+l.trang_thai.eq('duplicate_collapsed').sum()==len(r)

def test_valid_bulk_sales_retained(bundle):
    _,t,_,e,d,*_=bundle
    invalid=set(e.loc[e.loai_loi.isin(['invalid_qty','duplicate_conflict']),'ma_dong'])
    good=t.loc[(t.so_luong>150)&~t.ma_dong.isin(invalid),'ma_dong']
    assert len(good)>0
    assert set(good).issubset(set(d.ma_dong))

def test_catalog_missing_does_not_invent_values(bundle):
    cat,t,r,e,*_=bundle
    empty=cat.iloc[:0]
    d,*_=clean(r,empty)
    assert d.diem_danh_gia.isna().any()
    assert d.tac_gia.eq('Không rõ tác giả').any()

def test_conflict_quarantines_both_variants(bundle):
    cat,t,*_=bundle
    r=t.iloc[:2].copy();r['raw_row_id']=['R1','R2']
    other=r.iloc[[0]].copy();other['raw_row_id']='R3';other['so_luong']+=1
    d,_,q,_,_=clean(pd.concat([r,other],ignore_index=True),cat)
    assert len(d)==1 and len(q)==2

@pytest.mark.parametrize('column,value',[('ngay_ban','not a date'),('gia_goc',0),('diem_danh_gia',6),('so_luong',2.5),('kenh_ban','unknown'),('nam_xuat_ban',2025)])
def test_invalid_inputs_are_quarantined(bundle,column,value):
    cat,t,*_=bundle
    r=t.iloc[:3].copy();r['raw_row_id']=['R1','R2','R3'];r[column]=r[column].astype(object);r.loc[r.index[0],column]=value
    d,_,q,_,_=clean(r,cat)
    assert 'R1' in q.raw_row_id.values

def test_determinism(bundle):
    cat,t,*_=bundle
    cat2,t2=generate()
    pd.testing.assert_frame_equal(cat,cat2);pd.testing.assert_frame_equal(t,t2)

def test_all_totals_reconcile(bundle):
    d=bundle[4];tables,m=summarize(d)
    for k in ['genre','channel','segment','month','year','publisher','author','books']:
        assert tables[k].doanh_thu.sum()==m['revenue']
        assert tables[k].so_luong.sum()==m['quantity']
    assert np.isclose(m['average_unit_price'],m['revenue']/m['quantity'])
