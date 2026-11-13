import ast
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_orbital_notebook import BASELINE_SHA, DEPENDENCIES, build


class NotebookTests(unittest.TestCase):
    def test_packaging_sources_outputs_metadata_and_imports(self):
        root = Path(__file__).parent
        notebook = build(Path('C:/Users/GamerTech/Downloads/prioragent-arc-agi-3.ipynb'), root)
        source_cells = [c for c in notebook['cells'] if ''.join(c['source']).startswith('%%writefile')]
        self.assertEqual(len(source_cells), len(DEPENDENCIES)+1)
        hashes = notebook['metadata']['orbital_learning']['source_sha256']
        for cell in source_cells:
            first, source = ''.join(cell['source']).split('\n', 1)
            name = first.rsplit('/', 1)[-1]
            ast.parse(source)
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), hashes[name])
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                self.assertEqual(cell['outputs'], []); self.assertIsNone(cell['execution_count'])
        runner = ''.join(next(c for c in notebook['cells'] if c['id'] == 'run-competition-gateway')['source'])
        for name in DEPENDENCIES:
            self.assertIn(name, runner)
        self.assertIn('check=True', runner)
        self.assertIn("'checked_thread_runner.py', 'main.py'", runner)
        self.assertNotIn('!cd ', runner)
        self.assertFalse(notebook['metadata']['kaggle']['isInternetEnabled'])
        self.assertFalse(notebook['metadata']['orbital_learning']['archives_included'])
        self.assertEqual(notebook['metadata']['orbital_learning']['baseline_sha256'], BASELINE_SHA)

    def test_changed_baseline_refused(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'wrong.ipynb'; path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError): build(path, Path(__file__).parent)


if __name__ == '__main__': unittest.main()
