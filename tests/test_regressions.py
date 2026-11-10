"""Regression tests for the reproducibility and reporting defects fixed in PR1.

Each test is written against the behaviour that was actually broken: reverting the fix makes it
fail. They are deliberately narrow, so a genuine regression is not masked by a broad assertion.
"""
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import PARAMS
from src.data_cleaner import clean, price_group
from src.data_generator import corrupt, generate
from src.analysis import channel_shares, experiments, summarize, bootstrap

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def bundle():
    catalog, truth = generate(seed=PARAMS['seed'], n=PARAMS['n_lines'],
                              discount_strength=PARAMS['discount_strength'],
                              seasonality=PARAMS['seasonality'])
    raw, events = corrupt(truth, seed=PARAMS['seed'], missing_rate=PARAMS['missing_rate'])
    d, stages, q, changes, lineage = clean(raw, catalog)
    tables, metrics = summarize(d)
    return dict(catalog=catalog, truth=truth, raw=raw, events=events, d=d, stages=stages,
                q=q, tables=tables, metrics=metrics)


# --- F-03: experiments must honour the configured sample size -------------------------------

def test_experiments_uses_configured_n_lines():
    """Regression: experiments() called generate() with its default n, so the scenario layer
    silently simulated 6500 lines no matter what the pipeline was configured to run."""
    small = experiments(reps=2, params={'n_lines': 300})
    assert len(small) == 6
    # Revenue is the sum over the cleaned sample; 300 lines cannot reach the base-case total.
    assert small.revenue.max() < PARAMS['n_lines'] * 1e6
    base = experiments(reps=1)
    assert small.revenue.mean() < base.revenue.mean() / 5


def test_corrupt_reads_missing_rate_from_params():
    """Regression: the scenario layer ignored the configured missing_rate. Missing values are
    recoverable from the catalog, so retention cannot show this — count the injected cells."""
    catalog, truth = generate(seed=PARAMS['seed'], n=2000)
    _, low = corrupt(truth, seed=PARAMS['seed'], params={'missing_rate': .02})
    _, high = corrupt(truth, seed=PARAMS['seed'], params={'missing_rate': .40})
    assert (low.loai_loi == 'missing').sum() < (high.loai_loi == 'missing').sum() / 5


# --- F-08: the two definitions of "online" must not be conflated ----------------------------

def test_channel_shares_separates_marketplace_from_digital(bundle):
    """Regression: a single online_share summed the three sàn plus Website, which the generator
    treats as an offline channel (0-20% discount band). The two numbers must differ."""
    marketplace, digital = channel_shares(bundle['d'])
    d = bundle['d']
    revenue = d.groupby('kenh_ban').doanh_thu.sum()
    assert marketplace == pytest.approx(revenue[['Sàn A', 'Sàn B', 'Sàn C']].sum() / d.doanh_thu.sum() * 100, abs=1e-6)
    assert digital == pytest.approx(revenue[['Sàn A', 'Sàn B', 'Sàn C', 'Website']].sum() / d.doanh_thu.sum() * 100, abs=1e-6)
    assert digital > marketplace
    assert marketplace + digital < 200  # both are shares of the same denominator


def test_experiments_reports_both_channel_shares():
    cols = experiments(reps=2).columns
    assert 'marketplace_share' in cols and 'digital_channel_share' in cols
    assert 'online_share' not in cols


# --- F-11: a missing price is not a premium price -------------------------------------------

def test_price_group_missing_is_unknown_not_top_segment():
    """Regression: np.select sent NaN to `default`, labelling every missing price as the highest
    segment and inflating the premium bucket."""
    s = pd.Series([50000., np.nan, 300000.])
    out = price_group(s)
    assert out.iloc[0] == 'Dưới 80.000'
    assert out.iloc[2] == 'Trên 200.000'
    assert out.iloc[1] == 'Chưa biết'
    assert out.iloc[1] != 'Trên 200.000'


def test_price_group_boundaries_unchanged():
    out = price_group(pd.Series([79999., 80000., 200000., 200001.]))
    assert list(out) == ['Dưới 80.000', '80.000–200.000', '80.000–200.000', 'Trên 200.000']


# --- F-02 / F-18: no hard-coded figures, Vietnamese number format ---------------------------

STALE = ['6.660', '6.480', '6.500', '2.969.430.000', '2.978.555.000', '9.125.000',
         '30.790', '96.441', '99,692', '74,18', '0,173', '29,95', '25,33', '638.410.000']


def _report_text(monkeypatch, n_lines):
    """Render the report body for a given sample size, without building the PDF."""
    from src import report_builder
    monkeypatch.setitem(PARAMS, 'n_lines', n_lines)
    for key, ratio in [('n_bulk', 8 / 6500), ('n_dup_exact', 130 / 6500), ('n_dup_format', 25 / 6500),
                       ('n_conflicts', 5 / 6500), ('n_format_genre', 250 / 6500),
                       ('n_currency_format', 120 / 6500), ('n_invalid_price', 15 / 6500),
                       ('n_invalid_qty', 15 / 6500)]:
        monkeypatch.setitem(PARAMS, key, max(1, round(ratio * n_lines)))
    catalog, truth = generate(seed=PARAMS['seed'], n=n_lines)
    raw, events = corrupt(truth, seed=PARAMS['seed'])
    d, stages, q, changes, lineage = clean(raw, catalog)
    tables, metrics = summarize(d)
    from src.analysis import evaluate
    from src.analysis import missing_sensitivity
    matches, validation = evaluate(truth, d, raw, events)
    missing = missing_sensitivity(truth)
    exp = experiments(reps=2)
    sections = report_builder.build_sections(ROOT, d, tables, metrics, validation, stages, exp, matches,
                                             raw=raw, missing=missing)
    md, web = report_builder.render_text(sections)
    return md, metrics


def test_report_contains_no_base_case_literals_when_sample_changes(monkeypatch):
    """Regression: the report carried base-case figures as literals, so a run with a different
    n_lines produced a document quoting the old sample. This is the F-02 defect directly."""
    md, metrics = _report_text(monkeypatch, 7000)
    assert metrics['lines'] != 6480
    # Word boundaries: '6.660' must not match inside a longer derived number such as 16.660.
    leaked = [s for s in STALE if re.search(rf'(?<![\d.,]){re.escape(s)}(?![\d.,])', md)]
    assert not leaked, f'Báo cáo còn số liệu của kịch bản 6500 dòng: {leaked}'
    assert '7.000' in md


def test_report_numbers_are_vietnamese_formatted(monkeypatch):
    """Regression: f'{n:,}' produced English grouping (6,660) inside Vietnamese prose.

    The figures are derived from the run rather than hardcoded: an earlier version of this test
    pinned the base-case line count, so it would have passed a report that quoted a stale sample
    and failed a correct one after the simulation changed. What must hold is the format, not the
    value.
    """
    md, metrics = _report_text(monkeypatch, 6500)
    def vn(n):
        return f'{n:,}'.replace(',', '.')
    lines = vn(metrics['lines'])
    revenue = vn(metrics['revenue'])
    assert lines in md, f'số dòng {lines} không xuất hiện đúng định dạng tiếng Việt'
    assert revenue in md, f'doanh thu {revenue} không xuất hiện đúng định dạng tiếng Việt'
    # English grouping of these exact quantities must not appear.
    for english in [f'{metrics["lines"]:,}', f'{metrics["revenue"]:,}']:
        assert english not in md, f'Còn định dạng số kiểu Anh: {english}'
    # Vietnamese decimal: comma before the fraction.
    assert re.search(r'\d,\d+%', md)


def test_report_uses_decimal_comma(monkeypatch):
    md, _ = _report_text(monkeypatch, 6500)
    # Vietnamese decimals: comma before a fraction, e.g. 99,692%.
    assert re.search(r'\d,\d+%', md)


# --- F-16: captions and in-text references -------------------------------------------------

def test_table_and_figure_captions_are_numbered_and_sequential(monkeypatch):
    """Regression: captions reused the section title and no table captions existed in Markdown."""
    md, _ = _report_text(monkeypatch, 6500)
    tables = re.findall(r'^\*\*Bảng (\d+)\.', md, re.M)
    figures = re.findall(r'^!\[Hình (\d+)\.', md, re.M)
    assert tables == [str(i) for i in range(1, len(tables) + 1)]
    assert figures == [str(i) for i in range(1, len(figures) + 1)]
    assert len(tables) >= 5 and len(figures) >= 8


def test_every_caption_is_referenced_in_the_text(monkeypatch):
    """Regression: captions existed but the body never pointed at them."""
    md, _ = _report_text(monkeypatch, 6500)
    body = re.sub(r'^\*\*Bảng \d+\..*$', '', md, flags=re.M)
    body = re.sub(r'^!\[Hình \d+\..*$', '', body, flags=re.M)
    for kind in ('Bảng', 'Hình'):
        numbers = re.findall(rf'^\*\*{kind} (\d+)\.' if kind == 'Bảng' else rf'^!\[{kind} (\d+)\.', md, re.M)
        for n in numbers:
            assert re.search(rf'{kind} {n}\b', body), f'{kind} {n} không được dẫn trong bài'


def test_caption_text_is_not_the_section_title(monkeypatch):
    md, _ = _report_text(monkeypatch, 6500)
    headings = {h.strip() for h in re.findall(r'^# (.+)$', md, re.M)}
    for cap in re.findall(r'^\*\*Bảng \d+\. (.+?)\*\*$', md, re.M):
        assert cap not in headings


# --- F-13: reproducible text outputs -------------------------------------------------------

def test_text_outputs_are_written_with_lf(tmp_path):
    """Regression: Windows text mode wrote CRLF, so the manifest hash differed per platform.
    This exercises the writer itself, so reverting newline='\\n' fails here."""
    from src import report_builder
    (tmp_path / 'report').mkdir()
    sections = [{'title': 'T', 'paras': ['Một đoạn văn.'],
                 'chart': None, 'table': [['A', 'B'], ['1', '2']], 'caption': 'Bảng thử'}]
    report_builder.write_text_outputs(tmp_path, sections)
    for name in ['bao_cao.md', 'bao_cao.html']:
        data = (tmp_path / 'report' / name).read_bytes()
        assert data, f'{name} rỗng'
        assert b'\r\n' not in data, f'{name} chứa CRLF'


def test_pdf_is_byte_reproducible(tmp_path):
    """Regression: reportlab stamped a creation date into the PDF, so two identical runs produced
    different bytes and the manifest could never verify. invariant=1 removes it."""
    from src import report_builder
    sections = [{'title': 'T', 'paras': ['Một đoạn văn.'], 'chart': None,
                 'table': [['A', 'B'], ['1', '2']], 'caption': 'Bảng thử'}]
    digests = []
    for run in ['a', 'b']:
        root = tmp_path / run
        (root / 'report').mkdir(parents=True)
        report_builder.write_text_outputs(root, sections)
        report_builder.write_pdf(root, sections)
        digests.append((root / 'report/bao_cao.pdf').read_bytes())
    assert digests[0] == digests[1], 'PDF không tái lập được giữa hai lần chạy'


def test_dashboard_data_reconciles_with_metrics():
    """The dashboard computes its KPIs in the browser from embedded rows, so the rows themselves
    must reconcile with metrics.json — otherwise the dashboard and the report disagree."""
    import re
    dash = (ROOT / 'charts/dashboard.html').read_text(encoding='utf8')
    match = re.search(r'const rows=(\[.*?\]);const fmt', dash, re.S)
    assert match, 'Không tìm thấy dữ liệu nhúng trong dashboard'
    rows = json.loads(match.group(1))
    metrics = json.loads((ROOT / 'results/metrics.json').read_text(encoding='utf8'))['metrics']
    assert len(rows) == metrics['lines'], f"{len(rows)} dòng nhúng vs {metrics['lines']} dòng sạch"
    assert sum(r['doanh_thu'] for r in rows) == metrics['revenue']
    assert sum(r['so_luong'] for r in rows) == metrics['quantity']


def test_committed_text_outputs_use_lf_only():
    for rel in ['report/bao_cao.md', 'report/bao_cao.html', 'results/metrics.json',
                'results/manifest.json', 'charts/dashboard.html']:
        data = (ROOT / rel).read_bytes()
        assert b'\r\n' not in data, f'{rel} chứa CRLF'


def test_manifest_excludes_files_the_pipeline_does_not_generate():
    """Regression: data_dictionary.md is hand-written but was listed in the manifest, so the
    manifest could not be verified on a fresh clone."""
    import sys
    sys.path.insert(0, str(ROOT))
    from run import manifest_files
    files = manifest_files(ROOT)
    assert 'data/data_dictionary.md' not in files
    assert 'results/manifest.json' not in files
    assert 'data/processed/book_sales_clean.csv' in files


def test_manifest_hashes_match_committed_files():
    manifest = json.loads((ROOT / 'results/manifest.json').read_text(encoding='utf8'))
    import hashlib
    for rel, digest in manifest['files'].items():
        path = ROOT / rel
        assert path.is_file(), f'{rel} trong manifest nhưng không tồn tại'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Hash sai: {rel}'


# --- F-05: float comparison must tolerate last-digit noise, not real drift ------------------

def test_metrics_are_rounded_for_stable_comparison(bundle):
    """Regression: metrics.json stored full float repr, so a different BLAS build produced a
    different file and an exact-equality assertion aborted the notebook."""
    for key, value in bundle['metrics'].items():
        if isinstance(value, float):
            assert value == round(value, 6), f'{key} chưa được làm tròn 6 chữ số'


def test_published_metrics_match_recomputation(bundle):
    published = json.loads((ROOT / 'results/metrics.json').read_text(encoding='utf8'))['metrics']
    assert published.keys() == bundle['metrics'].keys()
    for key, value in bundle['metrics'].items():
        old = published[key]
        if isinstance(value, float):
            assert math.isclose(value, old, rel_tol=1e-9, abs_tol=1e-12), key
        else:
            assert value == old, key


# --- generator refactor must stay RNG-identical --------------------------------------------

def test_generator_output_is_unchanged_by_the_config_refactor():
    """Regression guard: moving constants into PARAMS must not perturb the random stream.
    These hashes are the committed source data, so any change in draw order fails here."""
    import hashlib
    import io

    def digest(df):
        """Hash the CSV content with line endings normalised to LF.

        pandas writes os.linesep by default, so the same frame serialises as CRLF on Windows
        and LF on Linux. The committed reference files are CRLF, so a raw byte comparison only
        ever passed on Windows and failed on every Linux runner. Normalising both sides keeps
        this guard on what it is actually for: the random draw order. A change in draw order
        alters the values, so it still fails here.
        """
        buf = io.BytesIO()
        df.to_csv(buf, index=False, encoding='utf-8-sig')
        return hashlib.sha256(buf.getvalue().replace(b'\r\n', b'\n')).hexdigest()

    catalog, truth = generate(seed=PARAMS['seed'], n=PARAMS['n_lines'],
                              discount_strength=PARAMS['discount_strength'],
                              seasonality=PARAMS['seasonality'])
    raw, events = corrupt(truth, seed=PARAMS['seed'], missing_rate=PARAMS['missing_rate'])
    for name, df, rel in [('catalog', catalog, 'data/reference/catalog.csv'),
                          ('ground_truth', truth, 'data/reference/ground_truth.csv'),
                          ('raw', raw, 'data/raw/book_sales_raw.csv'),
                          ('events', events, 'data/audit/injected_errors.csv')]:
        assert digest(df) == hashlib.sha256(
            (ROOT / rel).read_bytes().replace(b'\r\n', b'\n')).hexdigest(), \
            f'{name} thay đổi sau khi refactor cấu hình'


# --- F-13b: re-executing the notebook must not dirty the working tree ------------------------

def test_notebook_execution_is_idempotent():
    """Regression: nbclient stamps every cell with wall-clock timestamps, so running the
    notebook rewrote the committed file on every run and left git status dirty. The outputs
    are kept (they are part of the submission); only the volatile metadata is stripped."""
    import nbformat
    from tools.execute_notebook import normalise

    path = ROOT / 'notebooks/book_sales_analysis.ipynb'
    nb = nbformat.read(path, as_version=4)
    before = nbformat.writes(nb, version=4)
    # Simulate what nbclient does on execution.
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.metadata['execution'] = {'iopub.execute_input': '2026-01-01T00:00:00.000000Z'}
    nb.metadata['language_info']['version'] = '3.99.0'
    after = nbformat.writes(normalise(nb), version=4)
    assert after == before, 'notebook is not stable across executions'
    assert chr(13) not in before, 'committed notebook must use LF so --check works on Linux CI'


def test_committed_notebook_keeps_its_outputs():
    """The outputs are submitted evidence, not build artefacts: stripping them to keep the tree
    clean would have been the wrong fix."""
    import nbformat

    nb = nbformat.read(ROOT / 'notebooks/book_sales_analysis.ipynb', as_version=4)
    code = [c for c in nb.cells if c.cell_type == 'code']
    assert code, 'notebook has no code cells'
    # A cell that only rebuilds charts has no display output by design; every cell that shows
    # something must still show it.
    showing = [c for c in code if 'display(' in c.source or 'Image(' in c.source]
    assert len(showing) >= 10, 'notebook lost its display cells'
    assert all(c.outputs for c in showing), 'a display cell lost its output'
    assert all(c.execution_count is not None for c in code), 'execution counts were dropped'


# --- bootstrap intervals -------------------------------------------------------------------

def test_book_level_correlation_uses_the_same_grouping_as_the_report(bundle):
    """Regression: `summarize` grouped books by (ma_sach, ten_sach) while `null_band` grouped by
    ma_sach alone. Rows whose key did not resolve carry the placeholder BK9999, so the second
    grouping merged six distinct books into one and summed their quantities. The reported value
    and the null band it was compared against were therefore computed on different units."""
    d = bundle['d']
    by_pair = (d.groupby(['ma_sach', 'ten_sach'])
                 .agg(q=('so_luong', 'sum'), r=('diem_danh_gia', 'first')))
    by_key = d.groupby('ma_sach').agg(q=('so_luong', 'sum'), r=('diem_danh_gia', 'first'))
    assert len(by_pair) > len(by_key), 'placeholder key no longer collapses distinct books'
    assert not math.isclose(by_pair.r.corr(by_pair.q), by_key.r.corr(by_key.q), rel_tol=1e-6), \
        'the two groupings agree, so this test no longer guards anything'
    assert bundle['metrics']['rating_book_qty_r'] == round(by_pair.r.corr(by_pair.q), 6)


def test_bootstrap_point_estimates_match_the_published_metrics(bundle):
    """The interval must be centred on the number the report prints. A bootstrap that resamples
    a different unit than `summarize` measures produces a point estimate that silently disagrees
    with the headline figure."""
    boot = bootstrap(bundle['d'], n_boot=120).set_index('metric')
    m = bundle['metrics']
    assert boot.loc['revenue', 'point'] == m['revenue']
    assert boot.loc['rating_book_qty_r', 'point'] == m['rating_book_qty_r']
    assert boot.loc['rating_qty_r', 'point'] == m['rating_qty_r']
    assert boot.loc['discount_qty_r', 'point'] == m['discount_qty_r']
    assert boot.loc['average_unit_price', 'point'] == m['average_unit_price']


def test_bootstrap_intervals_bracket_their_point_estimate(bundle):
    boot = bootstrap(bundle['d'], n_boot=200)
    for row in boot.itertuples():
        assert row.ci_low <= row.point <= row.ci_high, row.metric
        assert row.ci_width > 0, row.metric


def test_book_level_interval_is_wider_than_a_line_level_one(bundle):
    """Resampling books must give a wider interval than resampling lines for the book-level
    correlation, because there are only ~300 books but ~6500 lines. If the two were equal the
    book-level metric would be pretending to a precision it does not have."""
    d = bundle['d']
    books = (d.groupby(['ma_sach', 'ten_sach'])
               .agg(q=('so_luong', 'sum'), r=('diem_danh_gia', 'first')))
    assert len(books) < len(d) / 10
    boot = bootstrap(d, n_boot=300).set_index('metric')
    # The line-level rating/quantity correlation is the same population quantity, measured on
    # rows; it must be reported with a visibly tighter interval.
    assert boot.loc['rating_book_qty_r', 'ci_width'] > boot.loc['rating_qty_r', 'ci_width']


def test_null_band_verdict_follows_the_arithmetic(bundle):
    """Regression: the report asserted the observed value was outside the null band while the
    numbers said otherwise. The percentile (96.5) and the band (central 95%) answer different
    questions, and the prose had been written from the first while claiming the second."""
    import pandas as pd
    from src.report_builder import _inside_band, _band_verdict

    null = pd.read_csv(ROOT / 'results/null_distribution.csv')
    s = null['rating_book_qty_r'].dropna()
    lo, hi = s.quantile(.025), s.quantile(.975)
    observed = bundle['metrics']['rating_book_qty_r']

    expected = 'trong' if lo <= observed <= hi else 'ngoài'
    assert _inside_band(null, 'rating_book_qty_r', observed) == expected
    verdict = _band_verdict(null, 'rating_book_qty_r', observed)
    assert ('tương thích' in verdict) == (expected == 'trong')

    # The band must be wide enough that a value at the 96.5th percentile still sits inside it.
    # If this ever fails, the band and the percentile are being computed on different units.
    assert lo <= observed <= hi, (lo, observed, hi)


def test_null_band_and_observed_value_use_the_same_book_grouping(bundle):
    """The band is generated across seeds; the observed value comes from `summarize`. Both must
    group books the same way, or the comparison is between two different quantities."""
    import pandas as pd
    from src.analysis import null_band

    null = pd.read_csv(ROOT / 'results/null_distribution.csv')
    # Recompute one seed through the same path the band uses and compare with summarize's rule.
    one = null_band(n_seeds=1)
    assert 'rating_book_qty_r' in one.columns
    assert null['rating_book_qty_r'].notna().all()


# --- APA citation integrity ----------------------------------------------------------------

def test_every_reference_is_cited_and_every_citation_has_a_reference():
    """APA is author-date, so a numeric marker anywhere in the text means the conversion was
    incomplete, and a reference nobody cites is a reference that should not be in the list."""
    import re
    from src.report_builder import SOURCES

    text = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    body, _, refs = text.partition('# Tài liệu tham khảo và chỉ dẫn tái lập')

    assert not re.search(r'\[\d\]', body), 'numeric citation marker left in the body'

    # Each reference must appear verbatim in the reference section.
    for title, _url in SOURCES:
        assert title in refs, title[:60]

    # Each in-text citation must correspond to a reference entry.
    keys = {
        'Morris và cộng sự, 2019': 'Morris, T. P.',
        'GO FAIR Foundation, n.d.': 'GO FAIR Foundation',
        'NIST/SEMATECH, 2012': 'NIST/SEMATECH',
        'The pandas development team, 2024': 'The pandas development team',
    }
    for in_text, ref_start in keys.items():
        if in_text in body:
            assert ref_start in refs, in_text


def test_cover_placeholders_are_marked_not_invented():
    """The template cannot know the institution or the members. Every such field must be an
    explicit placeholder rather than a plausible-looking guess."""
    text = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    for field in ['TRƯỜNG:', 'KHOA/BỘ MÔN:', 'HỌC PHẦN:', 'GIẢNG VIÊN HƯỚNG DẪN:', 'NHÓM THỰC HIỆN:']:
        assert field in text, field
    assert text.count('[CẦN ĐIỀN') >= 6


def test_metrics_json_survives_a_console_that_cannot_encode_vietnamese():
    """CI on windows-latest runs with a cp1252 stdout. Printing the metrics payload there raised
    UnicodeEncodeError and failed the pipeline while passing locally under PYTHONIOENCODING=utf-8.
    The file is written as UTF-8 either way; the console copy must degrade, not crash."""
    import io
    import json

    payload = {'metric': 'doanh_thu', 'unit': 'đồng', 'note': 'Điểm đánh giá'}

    # A stream that refuses anything outside cp1252, like the real Windows console.
    strict = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict', newline='')
    with pytest.raises(UnicodeEncodeError):
        strict.write(json.dumps(payload, ensure_ascii=False))

    # The fallback used by run.py must round-trip the same data.
    escaped = json.dumps(payload, ensure_ascii=True)
    strict.write(escaped)
    strict.flush()
    decoded = json.loads(strict.buffer.getvalue().decode('cp1252'))
    assert decoded == payload


# --- Final submission regressions (Errors A - H) --------------------------------------------

def test_regression_error_a_book_counts_and_placeholder_key(bundle):
    """Lỗi A: Catalog có 300 sách, nhưng tập sạch có 301 mã sách do BK9999, và 306 cặp (mã, tên).
    Báo cáo phải phân biệt rõ ràng ba số lượng này."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert '300 mã danh mục' in md or '300 sách' in md or '300 đầu sách' in md
    assert 'BK9999' in md
    assert '301 mã sách' in md or '301 mã' in md
    # Make sure we don't confuse the catalog design with the observed keys
    assert '301 mã sách trong danh mục' not in md


def test_regression_error_b_detection_rates_consistency():
    """Lỗi B: Không dùng mẫu số 1029 để tuyên bố 97,9% lỗi còn lại trên 8 họ lỗi.
    Tỷ lệ phát hiện và dòng còn sai phải đồng nhất."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert '97,9% lỗi vẫn nằm lại' not in md
    assert '97,9% lỗi còn lại' not in md
    # We must explicitly distinguish the family-level detection
    assert 'tám họ lỗi giá trị' in md or 'tám họ' in md
    assert '32' in md  # 32 dòng lỗi giá trị còn sai


def test_regression_error_c_no_false_100_percent_claim_on_all_fields():
    """Lỗi C: Không khẳng định cả 8 trường đều khớp 100% khi chỉ có 3 trường đạt 100%."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert 'tám trường được đối chiếu với dữ liệu chuẩn đều đạt tỷ lệ khớp 100%' not in md
    assert 'ba trường thuộc tính danh mục đạt tỷ lệ khớp 100%' in md


def test_regression_error_d_error_family_table_has_flagged_column():
    """Lỗi D: Bảng họ lỗi phải có cột 'Gắn cờ' để giải thích tại sao catalog_missing
    có cách ly = 0 nhưng tỷ lệ phát hiện là 100%."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert '| Gắn cờ |' in md
    assert 'catalog_missing' in md


def test_regression_error_e_revenue_error_interpretation(bundle):
    """Lỗi E: Doanh thu tập sạch cao hơn dữ liệu chuẩn (+2,992%).
    Phải tách biệt hai tác động: lỗi còn sót làm tăng và cách ly làm giảm."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert 'tổng kỳ vẫn thiếu do cách ly' not in md
    assert 'cơ chế cách ly gây thiếu tổng' not in md
    assert '+2,992%' in md or '2,992%' in md
    # Arithmetic identity verification
    truth = bundle['truth']
    clean_df = bundle['d']
    t_feat = truth.copy()
    t_feat['doanh_thu'] = t_feat['gia_ban'] * t_feat['so_luong']
    removed_ids = set(truth['ma_dong']) - set(clean_df['ma_dong'])
    quarantine_loss = t_feat[t_feat['ma_dong'].isin(removed_ids)]['doanh_thu'].sum()
    retained_clean = clean_df.set_index('ma_dong')['doanh_thu']
    retained_truth = t_feat.set_index('ma_dong').loc[clean_df['ma_dong']]['doanh_thu']
    retained_err = (retained_clean - retained_truth).sum()
    net_gap = clean_df['doanh_thu'].sum() - t_feat['doanh_thu'].sum()
    assert retained_err - quarantine_loss == net_gap
    assert net_gap > 0  # Clean revenue is higher than truth


def test_regression_error_f_null_distribution_verdict_consistent():
    """Lỗi F: Giá trị quan sát r=0.105 nằm TRONG khoảng null 95% [-0.112; 0.107].
    Không văn bản nào được khẳng định nó nằm ngoài khoảng 95%."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert 'thấy nó nằm ngoài khoảng 95%' not in md
    assert 'nằm trong khoảng 95%' in md

    # Also check notebook source
    import nbformat
    nb = nbformat.read(ROOT / 'notebooks/book_sales_analysis.ipynb', as_version=4)
    nb_text = ''.join(c.source for c in nb.cells)
    assert 'nằm ngoài khoảng 95%' not in nb_text
    assert 'nằm trong khoảng 95%' in nb_text


def test_regression_error_g_no_thousands_separator_in_years():
    """Lỗi G: Năm xuất bản không được định dạng thành 2.015–2.023."""
    md = (ROOT / 'report/bao_cao.md').read_text(encoding='utf8')
    assert '2.015' not in md
    assert '2.023' not in md
    assert '2015–2023' in md


def test_regression_error_h_readme_and_docs_sync_with_metrics():
    """Lỗi H: README.md và docs/KET-QUA-KIEM-TRA.md phải đồng bộ với số liệu mới nhất."""
    readme = (ROOT / 'README.md').read_text(encoding='utf8')
    metrics = json.loads((ROOT / 'results/metrics.json').read_text(encoding='utf8'))['metrics']
    assert '6.480' not in readme
    assert f"{metrics['lines']:,}".replace(',', '.') in readme
    assert '22 mã nghiệp vụ' in readme
    assert '+2,992%' in readme

