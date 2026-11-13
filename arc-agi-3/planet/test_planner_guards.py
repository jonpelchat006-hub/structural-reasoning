from copy import deepcopy
import unittest
import numpy as np
import route
from relation_guard import RelationAttempts
from play_metrics import action_records


class PlannerGuardTests(unittest.TestCase):
    def test_reset_entries_cannot_inflate_operator_press_counts(self):
        rows = [{"a": 1, "src": "op"}, {"a": 0, "src": "op"}, {"a": 2, "src": "eye"}]
        actual = action_records(rows)
        self.assertEqual(len(actual), 2)
        self.assertEqual(sum(r["src"] == "op" for r in actual), 1)

    def test_route_cost_recomputed_after_model_changes_with_identical_frame(self):
        class Ops:
            ops = {}
            cost = 1
            def predict(self, frame, action): return frame + 1
        ops = Ops()
        f = np.zeros((2, 2), int)
        cells = np.ones_like(f, bool)
        calls = []
        def plan_to(ops, frame, goal, vkey, **kwargs):
            calls.append(ops.cost)
            return [1] * ops.cost
        args = (ops, f, lambda a: a.tobytes(), lambda *a: cells,
                lambda *a: (lambda f: True, lambda f: True), plan_to, [], cells, 0, cells)
        first = route.plan(*args, bar=20, bar_full=20)
        ops.cost = 5
        second = route.plan(*args, bar=20, bar_full=20)
        self.assertEqual(first[1], 2)
        self.assertEqual(second[1], 6)
        self.assertEqual(calls, [1, 5])

    def fixture(self):
        return {"src": "0@11,51", "region": [55, 60, 3, 8], "colour": 3,
                "state_patterns": [np.array([[3]])],
                "targets": [{"id": "5@49,53", "pattern": np.array([[3, 3]])}]}

    def test_restart_does_not_restore_attempt_budget(self):
        guard = RelationAttempts()
        rel = self.fixture()
        for _ in range(8): guard.attempt(rel)
        rebuilt = deepcopy(rel)
        rebuilt["targets"][0].update(matched_now=False, rotation=2)
        self.assertFalse(guard.allowed(rebuilt))
        with self.assertRaises(ValueError): guard.attempt(rebuilt)
        self.assertEqual(guard.snapshot()["stalls"][0]["source"], "0@11,51")

    def test_new_hypothesis_matched_target_and_new_level_are_not_blocked(self):
        guard = RelationAttempts(limit=1)
        rel = self.fixture()
        guard.attempt(rel)
        self.assertTrue(guard.allowed(rel, matched=True))
        changed = deepcopy(rel)
        changed["targets"][0]["pattern"] = np.array([[3]])
        self.assertTrue(guard.allowed(changed))
        self.assertTrue(RelationAttempts(limit=1).allowed(rel))


if __name__ == "__main__":
    unittest.main()
