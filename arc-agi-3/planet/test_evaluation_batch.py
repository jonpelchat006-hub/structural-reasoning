import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

import numpy as np
from evaluation_batch import run_batch, validate_completed, practice_verdict


class BatchTests(unittest.TestCase):
    def fixture(self, root, name="game"):
        np.savez(Path(root) / f"{name}.npz", F=np.zeros((26, 64, 64), np.int8),
                 A=np.ones(25, int), X=np.full(25, -1), Y=np.full(25, -1))

    def test_complete_batch_filters_debug_and_retains_identity(self):
        with tempfile.TemporaryDirectory(prefix="planet-eval-") as root:
            self.fixture(root)
            np.savez(Path(root) / "fence_debug.npz", border=np.ones(4))
            out = Path(root) / "report.json"
            report = run_batch(root, out, lambda name, path: {"test": name}, run_id="fresh")
            self.assertEqual(validate_completed(json.loads(out.read_text()), "fresh"), report)
            self.assertEqual(report["expected_games"], ["game"])
            self.assertEqual(len(report["rejected"]), 1)

    def test_failure_keeps_previous_complete_report_separate(self):
        with tempfile.TemporaryDirectory(prefix="planet-eval-") as root:
            self.fixture(root)
            out = Path(root) / "report.json"
            previous = run_batch(root, out, lambda n, p: {}, run_id="old")
            def broken(n, p): raise RuntimeError("broken operator")
            with self.assertRaises(RuntimeError): run_batch(root, out, broken, run_id="new")
            self.assertEqual(json.loads(out.read_text()), previous)
            progress = json.loads(out.with_name(out.name + ".progress.json").read_text())
            self.assertEqual(progress["status"], "failed")
            with self.assertRaises(ValueError): validate_completed(previous, "new")

    def test_selected_games_do_not_merge_previous_corpus(self):
        with tempfile.TemporaryDirectory(prefix="planet-eval-") as root:
            self.fixture(root, "a"); self.fixture(root, "b")
            out = Path(root) / "report.json"
            full = run_batch(root, out, lambda n, p: {})
            subset = run_batch(root, out, lambda n, p: {}, games=["a"])
            self.assertEqual(set(subset["games"]), {"a"})
            self.assertNotEqual(full["corpus_id"], subset["corpus_id"])
            with self.assertRaises(ValueError): run_batch(root, out, lambda n, p: {}, games=["missing"])

    def test_missing_result_is_failure(self):
        with tempfile.TemporaryDirectory(prefix="planet-eval-") as root:
            self.fixture(root)
            out = Path(root) / "report.json"
            with self.assertRaises(ValueError): run_batch(root, out, lambda n, p: None)
            self.assertFalse(out.exists())

    def test_changed_recording_is_not_silently_scored(self):
        with tempfile.TemporaryDirectory(prefix="planet-eval-") as root:
            self.fixture(root)
            def changes(n, p):
                np.savez(p, F=np.zeros((26, 64, 64), np.int8), A=np.full(25, 2), X=np.full(25, -1), Y=np.full(25, -1))
                return {}
            with self.assertRaises(ValueError): run_batch(root, Path(root) / "out.json", changes)

    def test_no_comparison_with_old_or_different_corpus(self):
        practice = {"agent": "induce.py", "status": "complete", "corpus_id": "A", "wins": 10}
        history = [{"practice": {**practice, "corpus_id": "B", "wins": 100}},
                   {"practice": {"agent": "induce.py", "wins": 100}}]
        self.assertEqual(practice_verdict(practice, history), (None, "first-baseline"))
        history.append({"practice": {**practice, "wins": 20}})
        self.assertEqual(practice_verdict(practice, history), (20, "REGRESSED"))
        self.assertEqual(practice_verdict({"status": "failed", "wins": None}, history), (None, "FAILED"))

    def test_incomplete_or_missing_games_rejected(self):
        with self.assertRaises(ValueError):
            validate_completed({"schema": "induction-batch-v2", "run_id": "x", "status": "complete",
                                "corpus_id": "y", "expected_games": ["a", "b"], "games": {"a": {}}}, "x")

    def daily_functions(self):
        # Avoid importing arc_daily: its oncall import selects persistent work.
        path = Path(__file__).with_name("arc_daily.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"_induction_practice", "run_practice"}]
        ns = {"subprocess": subprocess, "sys": sys, "os": __import__("os"), "json": json,
              "HERE": str(path.parent), "OUT_EYE": "not-read-on-failure"}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), ns)
        return ns

    def test_daily_nonzero_exit_is_failure_not_old_score_or_mock(self):
        ns = self.daily_functions()
        with patch.object(subprocess, "run", return_value=Mock(returncode=2, stderr="failed", stdout="")) as run:
            result = ns["run_practice"]()
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["wins"])
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
