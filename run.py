"""Run from any current directory: python path/to/run.py --replications 50."""
import argparse,json,hashlib,platform,sys
from pathlib import Path
import pandas as pd
from src.config import ROOT,PARAMS
from src.data_generator import generate,corrupt
from src.data_cleaner import clean
from src.analysis import summarize,evaluate,experiments,missing_sensitivity
from src.visualizer import generate_all_charts
from src.dashboard_builder import build_dashboard

# Hand-written documentation that lives under an output folder but is not produced by run.py.
# Listing it in the manifest made the manifest unverifiable on a fresh clone.
MANIFEST_EXCLUDE={'results/manifest.json','data/data_dictionary.md'}


def manifest_files(root):
    return {str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['data','results','charts','report'] for p in (root/folder).rglob('*')
            if p.is_file() and str(p.relative_to(root)).replace('\\','/') not in MANIFEST_EXCLUDE}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--replications',type=int,default=50);ap.add_argument('--out',type=Path,default=ROOT);ap.add_argument('--skip-presentation',action='store_true')
    ap.add_argument('--n-lines',type=int,default=None,help='Override PARAMS["n_lines"] (e.g. 7000) to check that no figure in the report is hard-coded.')
    a=ap.parse_args()
    if a.replications<2:ap.error('replications must be >=2 for Monte Carlo SE')
    if a.n_lines:
        # Scale the injected-defect budget with the sample. Leaving these at their 6500 defaults
        # would make a "different configuration" run silently reuse the base-case error counts.
        base=PARAMS['n_lines']
        scaled=['n_bulk','n_dup_exact','n_dup_format','n_conflicts','n_format_genre',
                'n_currency_format','n_invalid_price','n_invalid_qty']
        ratios={k:PARAMS[k]/base for k in scaled}
        PARAMS['n_lines']=a.n_lines
        for k in scaled: PARAMS[k]=max(1,round(ratios[k]*a.n_lines))
    root=a.out.resolve()
    for p in ['data/raw','data/reference','data/processed','data/audit','results','charts','report']: (root/p).mkdir(parents=True,exist_ok=True)
    def csv(d,p,index=False):d.to_csv(root/p,index=index,encoding='utf-8-sig')
    catalog,truth=generate(seed=PARAMS['seed'],n=PARAMS['n_lines'],discount_strength=PARAMS['discount_strength'],seasonality=PARAMS['seasonality'])
    raw,events=corrupt(truth,seed=PARAMS['seed'],missing_rate=PARAMS['missing_rate'])
    csv(catalog,'data/reference/catalog.csv');csv(truth,'data/reference/ground_truth.csv');csv(raw,'data/raw/book_sales_raw.csv');csv(events,'data/audit/injected_errors.csv')
    d,stages,q,changes,lineage=clean(raw,catalog)
    csv(d,'data/processed/book_sales_clean.csv');csv(stages,'data/audit/cleaning_stages.csv');csv(q,'data/audit/quarantine.csv');csv(changes,'data/audit/cell_changes.csv');csv(lineage,'data/audit/row_lineage.csv')
    tables,metrics=summarize(d);matches,validation=evaluate(truth,d,raw,events)
    csv(matches,'results/recovery.csv')
    missing=missing_sensitivity(truth);csv(missing,'results/missing_sensitivity.csv')
    for name,table in tables.items():csv(table,f'results/{name}.csv',index=name=='correlation')
    print('Running paired simulation scenarios...',flush=True)
    exp=experiments(a.replications);csv(exp,'results/sensitivity_runs.csv')
    summary=[]
    for scenario,g in exp.groupby('scenario',sort=False):
        for col in ['revenue','marketplace_share','digital_channel_share','q4_share','discount_qty_r','discount_qty_r_without_bulk','revenue_error_pct','retained_pct']:
            summary.append({'scenario':scenario,'metric':col,'R':len(g),'mean':float(g[col].mean()),'sd':float(g[col].std()),'mcse_mean':float(g[col].std()/len(g)**.5),'p025':float(g[col].quantile(.025)),'p975':float(g[col].quantile(.975))})
    csv(pd.DataFrame(summary),'results/sensitivity_summary.csv')
    allmetrics={'parameters':dict(PARAMS,replications=a.replications),'metrics':metrics,'validation':validation}
    (root/'results/metrics.json').write_text(json.dumps(allmetrics,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    if not a.skip_presentation:
        generate_all_charts(d,tables,exp,root/'charts');build_dashboard(d,root/'charts/dashboard.html')
        from src.report_builder import build_report
        build_report(root,d,tables,metrics,validation,stages,exp,matches,raw=raw,missing=missing)
    (root/'results/manifest.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'files':manifest_files(root)},ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    print(json.dumps(allmetrics,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
