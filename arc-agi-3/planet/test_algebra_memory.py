"""Offline checks: python -B -m unittest test_algebra_memory -v."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import cayley
import cube_memory
import quat
from algebra_audit import audit_view, neighbor_audit
from views import Views


class AlgebraTests(unittest.TestCase):
    def test_matches_existing_convention(self):
        rng = np.random.default_rng(7)
        for _ in range(12):
            a, b = rng.normal(size=(2, 4))
            np.testing.assert_allclose(cayley.multiply(a, b), quat.qmul(a, b), atol=1e-12)
            a, b = rng.normal(size=(2, 8))
            expected = np.concatenate(quat.omul((a[:4], a[4:]), (b[:4], b[4:])))
            np.testing.assert_allclose(cayley.multiply(a, b), expected, atol=1e-12)

    def test_identity_conjugate_and_embedding(self):
        for n in (1, 2, 4, 8, 16, 32):
            a = np.arange(n, dtype=np.int64) - 3
            one = np.eye(n, dtype=np.int64)[0]
            np.testing.assert_array_equal(cayley.multiply(a, one), a)
            np.testing.assert_array_equal(cayley.multiply(one, a), a)
            np.testing.assert_array_equal(cayley.multiply(a, cayley.conjugate(a)), one * (a @ a))
            if n > 1:
                half = np.arange(n // 2, dtype=np.int64)
                lifted = np.concatenate((half, np.zeros(n // 2, dtype=np.int64)))
                np.testing.assert_array_equal(cayley.multiply(lifted, lifted)[:n // 2], cayley.multiply(half, half))

    def test_historical_doublet_counts(self):
        self.assertEqual(cayley.doublet_audit(4)["ordered_zero_pairs"], 0)
        self.assertEqual(cayley.doublet_audit(8)["ordered_zero_pairs"], 0)
        audit = cayley.doublet_audit(16)
        self.assertEqual(audit["ordered_zero_pairs"], 84)
        self.assertEqual(audit["participating_left_doublets"], 42)
        self.assertEqual(audit["partners_per_participant"], [2])

    def test_void_certificate_is_not_empty_operands(self):
        w = cayley.doublet_audit(16)["witness"]
        self.assertTrue(w["zero_divisor_witness"])
        self.assertGreater(w["left_norm"] * w["right_norm"], 0)
        self.assertEqual(w["product_norm"], 0)
        empty = cayley.product_certificate(np.zeros(16), w["right"])
        self.assertFalse(empty["zero_divisor_witness"])
        self.assertIsNone(empty["relative_residual"])

    def test_annihilator_directions_really_annihilate(self):
        a = cayley.doublet_audit(16)["witness"]["left"]
        for side in ("left", "right"):
            kernel = cayley.annihilator_basis(a, side)
            self.assertGreater(kernel["nullity"], 0)
            for b in kernel["directions"]:
                self.assertAlmostEqual(np.linalg.norm(b), 1)
                p = cayley.multiply(a, b) if side == "right" else cayley.multiply(b, a)
                self.assertLess(np.linalg.norm(p), 1e-10)
        self.assertEqual(cayley.annihilator_basis([1, 2, 3, 4, 5, 6, 7, 8])["nullity"], 0)

    def test_invalid_operands(self):
        for a, b in (([1, 2, 3], [1, 2, 3]), ([1, 2], [1]), ([[1, 2]], [[1, 2]])):
            with self.assertRaises(ValueError): cayley.multiply(a, b)
        with self.assertRaises(ValueError): cayley.annihilator_basis(np.zeros(16))


class CubeTests(unittest.TestCase):
    def test_keeps_silence_and_direction_distinctions(self):
        side = {(0, 0): {"borders": {"up": 1, "down": -1}}}
        eyes = {(0, 0): {"pins": [{"fired_with": 1}]},
                (0, 1): {"pins": [{"fired_with": 1, "silent_with": 100}]}}
        field = cube_memory.pack((1, 2), side, {}, eyes)
        np.testing.assert_array_equal(field[0, 0, :4], [1, -1, 0, 0])
        self.assertEqual(field[0, 1, 6], 100)
        self.assertFalse(np.array_equal(field[0, 0], field[0, 1]))
        audit = cube_memory.collision_audit(np.zeros((1, 2, 4)), field)
        self.assertEqual(audit["legacy_signatures_hiding_distinctions"], 1)
        self.assertEqual(audit["pixels_in_ambiguous_signatures"], 2)

    def test_evidence_requires_both_conditions(self):
        first = cube_memory.evidence({"fired_with": 1})
        self.assertIsNone(first["contrast"])
        self.assertTrue(first["needs_negative_test"])
        bad = cube_memory.evidence({"fired_with": 1, "silent_with": 100, "silent_without": 2})
        self.assertAlmostEqual(bad["p_fire_with"], 1 / 101)
        self.assertTrue(bad["contradicted"])

    def test_neighbor_zero_uses_both_nonzero_operands(self):
        w = cayley.doublet_audit(16)["witness"]
        field = np.array([[w["left"], w["right"]]], dtype=float)
        report = neighbor_audit(field)
        self.assertEqual(report["near_zero_products"], 1)
        self.assertTrue(report["witness"]["numerical_zero_product"])
        self.assertFalse(report["witness"]["zero_divisor_witness"])
        field[0, 1] = 0
        self.assertEqual(neighbor_audit(field)["nonzero_neighbor_pairs"], 0)

    def test_live_views_save_and_offline_audit(self):
        view = Views((2, 2)).build(water=np.array([[1., 0.], [0., 2.]]))
        self.assertEqual(view.s.shape, (2, 2, 16))
        self.assertIn("summary_collisions", view.collapse())
        with tempfile.TemporaryDirectory(prefix="planet-algebra-test-") as root:
            path = Path(root) / "views.json"
            view.save(str(path))
            saved = json.loads(path.read_text())
            self.assertEqual(saved["algebra_memory"]["schema"], cube_memory.SCHEMA)
            np.testing.assert_array_equal(np.load(path.with_name("views_s.npy")), view.s)
            report = audit_view(path)
            self.assertEqual(report["summary_collisions"]["pixels"], 4)


if __name__ == "__main__":
    unittest.main()
