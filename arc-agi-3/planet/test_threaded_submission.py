"""Execute packaged modules with the real official Swarm, in an isolated process.

Only transport is a synthetic frame fixture; no hosted/hidden game is contacted.
This exercises imports, registry, construction, multiple worker threads, SQLite,
control receipts, journal replay data, and process-level exception propagation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from build_orbital_notebook import build


ROOT = Path(__file__).parent
FRAMEWORK = Path('D:/planet/arc_compare/framework')
OLD = Path('D:/planet/arc_compare/submission_orbital_20260909/prioragent-orbital.ipynb')

DRIVER = '''
import json, os, sqlite3
from types import SimpleNamespace
import numpy as np
from arcengine import GameState
from arc_agi import OperationMode
from agents import Swarm, PriorAgent
from agents import swarm as module

class Environment:
    def __init__(self, game):
        self.calls = 0
        self.observation_space = SimpleNamespace(game_id=game, frame=[np.zeros((8,8), dtype=np.int16)],
            state=GameState.NOT_FINISHED, levels_completed=0, win_levels=1, guid=game,
            full_reset=False, available_actions=[1,2,3,4])
    def step(self, action, **kwargs):
        self.calls += 1
        if os.environ.get('DIAGNOSTIC_FAIL') == 'yes':
            raise RuntimeError('deliberate SDK fixture failure')
        return self.observation_space

class Arcade:
    operation_mode = OperationMode.OFFLINE
    def open_scorecard(self, **kwargs): return 'fixture-card'
    def make(self, game, **kwargs): return Environment(game)
    def close_scorecard(self, *args): return None

module.Arcade = Arcade
PriorAgent.MAX_ACTIONS = 3
swarm = Swarm('prioragent', 'http://offline.invalid', ['fixture-a', 'fixture-b'])
swarm.main()
rows = []
for agent in swarm.agents:
    summary = getattr(agent, 'learning_summary', {})
    path = getattr(agent, '_archive_path', None)
    observations = []
    if path and summary:
        from orbital_archive import OrbitalArchive
        archive = OrbitalArchive(path)
        observations = archive.observations(agent._instance)
        archive.close()
    rows.append(dict(calls=agent.arc_env.calls, summary=summary,
                     receipts=sum('channel_exchange' in row for row in observations)))
print('DIAGNOSTIC=' + json.dumps(rows))
'''


@unittest.skipUnless(FRAMEWORK.exists(), 'official local framework required')
class ThreadedSubmissionTests(unittest.TestCase):
    def run_packaged(self, notebook, fail=False):
        with TemporaryDirectory(prefix='arc-packaged-thread-test-') as tmp:
            root = Path(tmp)
            (root/'agents'/'templates').mkdir(parents=True)
            for name in ('agent.py', 'swarm.py', 'recorder.py', 'tracing.py'):
                shutil.copy2(FRAMEWORK/'agents'/name, root/'agents'/name)
            shutil.copy2(FRAMEWORK/'agents'/'templates'/'random_agent.py', root/'agents'/'templates'/'random_agent.py')
            for cell in notebook['cells']:
                source = ''.join(cell.get('source', []))
                if source.startswith('%%writefile '):
                    first, body = source.split('\n', 1)
                    name = first.rsplit('/', 1)[-1]
                    path = root/'agents'/'templates'/name if name == 'my_agent.py' else root/name
                    path.write_text(body, encoding='utf-8')
            # Same explicit registry used by the generated notebook.
            (root/'agents'/'__init__.py').write_text(
                'from .agent import Agent, Playback\nfrom .swarm import Swarm\n'
                'from .templates.random_agent import Random\nfrom .templates.my_agent import PriorAgent\n'
                'AVAILABLE_AGENTS = {"random": Random, "prioragent": PriorAgent}\n', encoding='utf-8')
            (root/'driver.py').write_text(DRIVER, encoding='utf-8')
            shutil.copy2(ROOT/'checked_thread_runner.py', root/'checked_thread_runner.py')
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
                               MPLBACKEND='Agg', OPERATION_MODE='offline', RECORDINGS_DIR=str(root/'recordings'),
                               DIAGNOSTIC_FAIL='yes' if fail else 'no')
            for name in ('ARC_API_KEY', 'ARC_BASE_URL', 'AGENTOPS_API_KEY'):
                environment.pop(name, None)
            result = subprocess.run([sys.executable, '-B', 'checked_thread_runner.py', 'driver.py'],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=40)
            row = next((line for line in result.stdout.splitlines() if line.startswith('DIAGNOSTIC=')), None)
            return result, None if row is None else json.loads(row.split('=', 1)[1])

    def notebook(self):
        return build('C:/Users/GamerTech/Downloads/prioragent-arc-agi-3.ipynb', ROOT)

    def test_packaged_multigame_workers_play_and_persist_receipts(self):
        result, rows = self.run_packaged(self.notebook())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row['calls'], 4)
            self.assertEqual(row['summary']['observations'], 5)
            self.assertEqual(row['receipts'], 4)
            self.assertEqual(row['summary']['status'], 'complete')

    def test_sdk_thread_error_fails_process_and_never_fabricates_receipt(self):
        result, rows = self.run_packaged(self.notebook(), fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('deliberate SDK fixture failure', result.stderr)
        self.assertNotIn('SQLite objects created in a thread', result.stderr)
        self.assertEqual([row['receipts'] for row in rows], [0, 0])
        self.assertEqual([row['calls'] for row in rows], [1, 1])

    @unittest.skipUnless(OLD.exists(), 'archived original submission required')
    def test_old_submission_is_a_failing_regression_control(self):
        result, rows = self.run_packaged(json.loads(OLD.read_text(encoding='utf-8')))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SQLite objects created in a thread', result.stderr)
        self.assertEqual([row['calls'] for row in rows], [0, 0])


if __name__ == '__main__': unittest.main()
