"""Regenerate figures/report from current source and existing experiment results.

Use only for presentation changes; run.py is required if simulation/cleaning changes.
"""
import sys,json,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_cleaner import clean
from src.analysis import summarize,evaluate
from src.visualizer import generate_all_charts
from src.dashboard_builder import build_dashboard
from src.report_builder import build_report
from run import manifest_files

raw=pd.read_csv(ROOT/'data/raw/book_sales_raw.csv');catalog=pd.read_csv(ROOT/'data/reference/catalog.csv')
d,stages,q,changes,lineage=clean(raw,catalog)
stored=pd.read_csv(ROOT/'data/processed/book_sales_clean.csv')
pd.testing.assert_frame_equal(d.astype('string'),stored.astype('string'))
t,m=summarize(d)
exp=pd.read_csv(ROOT/'results/sensitivity_runs.csv')
truth=pd.read_csv(ROOT/'data/reference/ground_truth.csv');errors=pd.read_csv(ROOT/'data/audit/injected_errors.csv')
matches,v=evaluate(truth,d,raw,errors)
# Exact dict equality here was the F-05 defect: a float that differs in the 16th digit (another
# BLAS build, another platform) aborted a presentation-only refresh. Compare with a tolerance
# and fail on any real difference.
published=json.loads((ROOT/'results/metrics.json').read_text(encoding='utf8'))['metrics']
assert published.keys()==m.keys(), f'Metric keys differ: {sorted(set(published)^set(m))}'
for k,val in m.items():
    old=published[k]
    if isinstance(val,float):
        assert abs(val-old)<=1e-9*max(1,abs(old)), f'{k}: {val} != {old}'
    else:
        assert val==old, f'{k}: {val} != {old}'
generate_all_charts(d,t,exp,ROOT/'charts');build_dashboard(d,ROOT/'charts/dashboard.html');build_report(ROOT,d,t,m,v,stages,exp,matches)
manifest=json.loads((ROOT/'results/manifest.json').read_text(encoding='utf8'))
manifest['files']=manifest_files(ROOT)
(ROOT/'results/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
print('Presentation regenerated; core data and metrics match pipeline.')
