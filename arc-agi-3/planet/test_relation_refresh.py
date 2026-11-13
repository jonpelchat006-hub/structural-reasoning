from copy import deepcopy
import unittest
import numpy as np
import relations


class RelationRefreshTests(unittest.TestCase):
    def setUp(self):
        self.shape = np.array([[1, 0, 1], [1, 0, 0], [1, 1, 1]])
        self.frame = np.where(np.kron(self.shape, np.ones((2, 2), int)), 12, 5)
        self.prior = {"colour": 9, "region": [0, 5, 0, 5], "states": [self.shape]}

    def test_absent_colour_rebinds_unique_scaled_shape(self):
        self.assertEqual(relations.carried_colour(self.prior, self.frame, set()), 12)
        self.assertEqual(self.prior["colour"], 9)

    def test_present_colour_is_not_overridden_by_convenient_shape(self):
        frame = self.frame.copy(); frame[0, 0] = 9
        self.assertEqual(relations.carried_colour(self.prior, frame, set()), 9)

    def test_ambiguous_rebinding_remains_unresolved(self):
        frame = np.array([[12, 5], [5, 12]])
        prior = {"colour": 9, "region": [0, 1, 0, 1], "states": [frame == 12]}
        self.assertEqual(relations.carried_colour(prior, frame, set()), 9)

    def test_missing_match_and_floor_candidate_remain_unresolved(self):
        self.assertEqual(relations.carried_colour(self.prior, self.frame, {12}), 9)
        self.assertEqual(relations.carried_colour(self.prior, np.full((6, 6), 5), set()), 9)

    def fixture(self):
        src = {"id": "source", "cells": np.ones((6, 6), bool)}
        dst = {"id": "target", "cells": np.zeros((6, 6), bool)}
        old = {"src": "source", "region": [0, 5, 0, 5], "colour": 9,
               "state_patterns": [self.shape], "prior": True,
               "targets": [{"id": "target", "object": dst, "pattern": self.shape}]}
        active = {"src": src, "dst": dst, "rel": old, "tries": 4}
        fresh = deepcopy(old); fresh.update(colour=12, prior=False)
        return active, fresh, [src, dst]

    def test_active_matcher_refresh_recognizes_match_and_preserves_trials(self):
        active, fresh, objects = self.fixture()
        self.assertEqual(relations.matched(self.frame, active["rel"], set()), [])
        current, changed = relations.refresh_active(active, [active["rel"], fresh], objects)
        self.assertTrue(changed)
        self.assertEqual(current["tries"], 4)
        self.assertEqual(len(relations.matched(self.frame, current["rel"], set())), 1)
        self.assertEqual(active["rel"]["colour"], 9)

    def test_unrelated_source_region_or_target_cannot_replace_active(self):
        for change in (dict(src="other"), dict(region=[1, 5, 0, 5]), dict(targets=[])):
            active, fresh, objects = self.fixture(); fresh.update(change)
            current, changed = relations.refresh_active(active, [fresh], objects)
            self.assertIs(current, active)
            self.assertFalse(changed)

    def test_mutable_match_flags_do_not_invalidate_plan(self):
        active, fresh, objects = self.fixture()
        fresh["colour"] = 9
        fresh["targets"][0].update(matched_now=True, rotation=0)
        _, changed = relations.refresh_active(active, [fresh], objects)
        self.assertFalse(changed)


if __name__ == "__main__":
    unittest.main()
