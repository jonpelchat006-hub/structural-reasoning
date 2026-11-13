from pathlib import Path
import tempfile
import unittest
import numpy as np
from arc3_preflight import inspect_recording, manifest


class PreflightTests(unittest.TestCase):
    def test_manifest_rejects_debug_arrays_and_excludes_play_recordings(self):
        with tempfile.TemporaryDirectory(prefix="planet-preflight-") as root:
            path = Path(root)
            data = dict(F=np.zeros((26, 64, 64), np.int8), A=np.ones(25, np.int8),
                        X=np.full(25, -1), Y=np.full(25, -1))
            np.savez(path / "game.npz", **data)
            np.savez(path / "fence_debug.npz", border=np.zeros(2))
            np.savez(path / "play_game.npz", F=data["F"])
            report = manifest(path)
            self.assertEqual((report["valid_count"], report["rejected_count"]), (1, 1))
            record = next(r for r in report["records"] if r["valid"])
            self.assertEqual((record["early"], record["late"]), (16, 9))
            self.assertEqual(len(record["sha256"]), 64)

    def test_bad_lengths_and_click_coordinates_rejected(self):
        with tempfile.TemporaryDirectory(prefix="planet-preflight-") as root:
            path = Path(root) / "game.npz"
            data = dict(F=np.zeros((26, 64, 64), np.int8), A=np.full(25, 6), X=np.full(25, -1), Y=np.ones(25, int))
            np.savez(path, **data)
            self.assertFalse(inspect_recording(path)["valid"])
            data.update(X=np.ones(25, int), F=np.zeros((25, 64, 64), np.int8))
            np.savez(path, **data)
            self.assertFalse(inspect_recording(path)["valid"])

    def test_missing_directory_fails_instead_of_reporting_zero_score(self):
        with tempfile.TemporaryDirectory(prefix="planet-preflight-") as root:
            with self.assertRaises(ValueError): manifest(Path(root) / "missing")


if __name__ == "__main__":
    unittest.main()
