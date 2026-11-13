"""Package reviewed-policy orbital learning for the user's existing Kaggle flow.

Does not upload or submit. Refuses existing outputs; removes stale cell outputs.
Never packages local game archives, environments, recordings or credentials.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path


BASELINE_SHA = '7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88'
DEPENDENCIES = ('prioragent_reviewed_baseline.py', 'orbital_archive.py', 'learning_session.py',
                'automatic_pin_refiner.py', 'evidence_pin.py', 'pin_channels.py', 'checked_thread_runner.py')


def runtime_ast(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
    return ast.dump(tree)


def build(baseline_path, source_directory):
    baseline_path, source_directory = Path(baseline_path), Path(source_directory)
    raw = baseline_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA:
        raise ValueError('review the changed baseline notebook before packaging')
    notebook = json.loads(raw)
    reviewed = ''.join(notebook['cells'][1]['source'][1:])
    sources = {name: (source_directory/name).read_text(encoding='utf-8') for name in DEPENDENCIES}
    if runtime_ast(reviewed) != runtime_ast(sources['prioragent_reviewed_baseline.py']):
        raise ValueError('frozen baseline executable syntax differs from reviewed notebook')
    sources['my_agent.py'] = (source_directory/'prioragent_learning.py').read_text(encoding='utf-8')
    for source in sources.values():
        ast.parse(source)
    hashes = {name: hashlib.sha256(source.encode('utf-8')).hexdigest() for name, source in sources.items()}

    def code(text, identifier):
        return dict(cell_type='code', id=identifier, execution_count=None, outputs=[], metadata={}, source=text.splitlines(True))

    cells = [dict(cell_type='markdown', id='orbital-notes', metadata={}, source=[
        '# PriorAgent — orbital learning experiment\n',
        'Offline-compatible archive, explicit boundaries, and observed movement planning.\n',
        'Local comparisons are not hidden leaderboard scores. No saved game evidence is bundled.\n'])]
    cells.append(code(''.join(notebook['cells'][0]['source']), 'install-wheels'))
    for name, source in sources.items():
        cells.append(code(f'%%writefile /kaggle/working/{name}\n'+source, name.replace('_', '-').replace('.', '-')))
    verify = ('import hashlib\nfrom pathlib import Path\n' + f'SOURCE_HASHES = {hashes!r}\n' +
              "for name, expected in SOURCE_HASHES.items():\n" +
              "    actual = hashlib.sha256((Path('/kaggle/working') / name).read_bytes()).hexdigest()\n" +
              "    assert actual == expected, f'Source mismatch: {name}'\n")
    cells.append(code(verify, 'verify-source-hashes'))
    runner = ''.join(notebook['cells'][2]['source'])
    marker = '    # Install our agent\n'
    if marker not in runner:
        raise ValueError('baseline gateway cell changed; review before packaging')
    copy_deps = ('    import shutil\n' + f'    for name in {DEPENDENCIES!r}:\n' +
                 "        shutil.copy2('/kaggle/working/' + name, '/kaggle/working/ARC-AGI-3-Agents/' + name)\n\n")
    runner = runner.replace(marker, copy_deps+marker, 1)
    run_marker = '    # Run the agent against every hidden game\n'
    if run_marker not in runner:
        raise ValueError('baseline launch marker changed; review before packaging')
    # A shell !command can exit nonzero while the notebook still succeeds.
    # Use a checked subprocess plus a worker-exception guard instead.
    runner = runner[:runner.index(run_marker)] + '''    # Run the agent against every hidden game; propagate worker failures.
    import subprocess
    import sys
    environment = dict(os.environ, MPLBACKEND='agg')
    subprocess.run([sys.executable, 'checked_thread_runner.py', 'main.py', '--agent', 'prioragent'],
                   cwd='/kaggle/working/ARC-AGI-3-Agents', env=environment, check=True)
'''
    cells.append(code(runner, 'run-competition-gateway'))
    cells.append(code(''.join(notebook['cells'][3]['source']), 'non-rerun-placeholder'))
    metadata = deepcopy(notebook['metadata'])
    metadata.pop('papermill', None)
    metadata['orbital_learning'] = dict(version='orbital-channels-2', baseline_sha256=BASELINE_SHA,
                                       source_sha256=hashes, archives_included=False)
    return dict(cells=cells, metadata=metadata, nbformat=4, nbformat_minor=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--source-directory', type=Path, default=Path(__file__).parent)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    packaged = build(args.baseline, args.source_directory)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(packaged, stream, indent=1, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output.resolve()), cells=len(packaged['cells']),
                         sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))
