"""Rebuild the academic report from the committed analysis results."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.report_builder import build_report
from run import manifest_files

data = pd.read_csv(ROOT / 'data/processed/book_sales_clean.csv')
metrics = json.loads((ROOT / 'results/metrics.json').read_text(encoding='utf8'))
tables = {name: pd.read_csv(ROOT / f'results/{name}.csv') for name in
          ['genre', 'books', 'month', 'year', 'channel', 'segment', 'discount', 'correlation']}
build_report(ROOT, data, tables, metrics['metrics'], metrics['validation'],
             pd.read_csv(ROOT / 'data/audit/cleaning_stages.csv'),
             pd.read_csv(ROOT / 'results/sensitivity_runs.csv'),
             pd.read_csv(ROOT / 'results/recovery.csv'))
manifest_path = ROOT / 'results/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf8'))
manifest['files'] = manifest_files(ROOT)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8', newline='\n')
print('Report regenerated from existing analysis results.')
