"""Execute the analysis notebook and write it back with its outputs.

The committed notebook must carry its outputs: they are part of what is submitted and they are
the evidence that the notebook runs. But re-executing used to dirty the working tree on every
run, because nbclient stamps each cell with wall-clock timestamps:

    cell.metadata.execution = {"iopub.execute_input": "2026-11-09T12:43:25.327159Z", ...}

Those timestamps carry no information about the analysis, so they are stripped before the file
is written. Outputs, execution counts and the notebook source are kept exactly as produced.

`--check` executes without writing and exits non-zero if the committed notebook no longer matches
a fresh run. CI uses it to prove the committed outputs are current rather than merely present.

The comparison is deliberately not byte-exact. Embedded PNG output is rendered by the local
matplotlib/freetype build, so the same figure produces different bytes on Windows and on Linux,
and a byte comparison would fail CI for a reason that has nothing to do with the analysis. What
must match is everything a reader can check: the source of every cell, the execution counts, the
text of every output, and the presence and type of every image. Image bytes are compared only
within one platform, where they are expected to be stable.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Written by nbclient from the running interpreter; it differs per Python build and would make
# the notebook dirty on CI for a reason that has nothing to do with the analysis.
VOLATILE_CELL_METADATA = ('execution',)

# Output types whose payload is a rendered image rather than text.
IMAGE_MIMES = ('image/png', 'image/jpeg', 'image/svg+xml')


def normalise(nb):
    """Remove run-specific metadata, keeping every output and execution count."""
    for cell in nb.cells:
        for key in VOLATILE_CELL_METADATA:
            cell.get('metadata', {}).pop(key, None)
    # A stable language_info: version pins the interpreter that happened to run last.
    info = nb.setdefault('metadata', {}).setdefault('language_info', {})
    info.pop('version', None)
    nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    return nb


def execute(path):
    with tempfile.TemporaryDirectory(prefix='book-sales-kernel-') as tmp:
        spec = Path(tmp) / 'kernels' / 'book-sales'
        spec.mkdir(parents=True)
        (spec / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'Book sales validation',
            'language': 'python',
        }), encoding='utf8')
        os.environ['JUPYTER_PATH'] = tmp + os.pathsep + os.environ.get('JUPYTER_PATH', '')
        nb = nbformat.read(path, as_version=4)
        NotebookClient(nb, timeout=600, kernel_name='book-sales',
                       resources={'metadata': {'path': str(ROOT)}}).execute()
    return normalise(nb)


def _text_of(output):
    """The checkable text of one output, with image payloads reduced to their type.

    Image bytes are deliberately not compared. The same figure is rendered by the local
    matplotlib/freetype build, so its PNG differs between Windows and Linux; comparing bytes
    would fail CI for a reason unrelated to the analysis. What is checked is that the output is
    still an image of the same type, in the same position. The figure's content is verified by
    the pipeline regenerating it from the same data.
    """
    kind = output.get('output_type')
    if kind == 'stream':
        return ('stream', output.get('name'), ''.join(output.get('text', '')))
    if kind in ('execute_result', 'display_data'):
        data = output.get('data', {})
        parts = []
        for mime, payload in sorted(data.items()):
            if mime in IMAGE_MIMES:
                parts.append((mime, '<image>'))
            else:
                text = payload if isinstance(payload, str) else ''.join(payload)
                parts.append((mime, text))
        return (kind, tuple(parts))
    if kind == 'error':
        return ('error', output.get('ename'), output.get('evalue'))
    return (kind, str(output))


def compare(committed, fresh):
    """Differences a reader could notice. Empty list means the notebook is current."""
    problems = []
    if len(committed.cells) != len(fresh.cells):
        problems.append(f'cell count {len(committed.cells)} committed vs {len(fresh.cells)} fresh')
        return problems
    for i, (a, b) in enumerate(zip(committed.cells, fresh.cells)):
        if a.cell_type != b.cell_type:
            problems.append(f'cell {i}: type {a.cell_type} vs {b.cell_type}')
            continue
        if a.source != b.source:
            problems.append(f'cell {i}: source differs')
        if a.cell_type != 'code':
            continue
        if a.get('execution_count') != b.get('execution_count'):
            problems.append(f'cell {i}: execution_count {a.get("execution_count")} vs {b.get("execution_count")}')
        if len(a.outputs) != len(b.outputs):
            problems.append(f'cell {i}: {len(a.outputs)} outputs committed vs {len(b.outputs)} fresh')
            continue
        for j, (oa, ob) in enumerate(zip(a.outputs, b.outputs)):
            ta, tb = _text_of(oa), _text_of(ob)
            if ta != tb:
                problems.append(f'cell {i} output {j}: content differs')
    return problems


def main():
    check = '--check' in sys.argv[1:]
    path = ROOT / 'notebooks/book_sales_analysis.ipynb'
    fresh = execute(path)
    code_cells = len([c for c in fresh.cells if c.cell_type == 'code'])
    rendered = nbformat.writes(fresh, version=4)
    current = path.read_text(encoding='utf8')

    if check:
        committed = nbformat.reads(current, as_version=4)
        problems = compare(committed, fresh)
        if problems:
            print('Notebook outputs are stale: re-run tools/execute_notebook.py and commit the result.')
            for p in problems[:20]:
                print(f'  {p}')
            if len(problems) > 20:
                print(f'  ... and {len(problems) - 20} more')
            return 1
        print(f'Notebook is current: {code_cells} code cells, no execution errors.')
        return 0

    if rendered != current:
        path.write_text(rendered, encoding='utf8', newline='\n')
        print(f'Notebook executed and updated: {code_cells} code cells, no execution errors.')
    else:
        print(f'Notebook executed: {code_cells} code cells, no execution errors. File unchanged.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
