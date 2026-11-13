"""Offline tests; no game API, model provider, or GPU is needed."""
from copy import deepcopy
import json
import unittest

import numpy as np
import diagonal
from pin_questions import QuestionQueue


def sample(**counts):
    return {"front": [5], "foot": "switch", "back": {"frame": "screen", "box": [0, 0, 0, 0]},
            "effect": {"kind": "opens", "target": "door"}, "source": "magnet", "sides": None,
            "condition": {"kind": "back_pattern", "frame": "screen", "box": [0, 0, 0, 0], "reads": [[2]]},
            "eye": {"fired_with": 0, "fired_without": 0, "silent_with": 0, "silent_without": 0, **counts}}


def opened(report):
    return [q for q in report["questions"] if q["status"] == "open"]


class QuestionTests(unittest.TestCase):
    def test_one_success_asks_missing_negative_and_replication(self):
        qs = opened(QuestionQueue("game:L1").update([sample(fired_with=1)]))
        self.assertEqual({q["kind"] for q in qs}, {"missing_negative", "replicate_positive"})
        self.assertEqual(qs[0]["kind"], "missing_negative")
        self.assertIn("absent", qs[0]["question"])
        self.assertIsNone(qs[0]["evidence"]["contrast"])

    def test_snapshot_is_idempotent_and_does_not_change_input(self):
        pin = sample(fired_with=1)
        before = deepcopy(pin)
        queue = QuestionQueue("game:L1")
        first = queue.update([pin], 3)
        self.assertEqual(first, queue.update([pin], 3))
        self.assertEqual(pin, before)
        first["questions"][0]["pin"]["front"].append(99)
        self.assertNotIn(99, queue.snapshot()["questions"][0]["pin"]["front"])

    def test_real_new_evidence_answers_sampling_not_causality(self):
        queue = QuestionQueue("game:L1")
        qid = next(q["id"] for q in opened(queue.update([sample(fired_with=1)], 1)) if q["kind"] == "missing_negative")
        report = queue.update([sample(fired_with=1, silent_without=1)], 2)
        answered = next(q for q in report["questions"] if q["id"] == qid)
        self.assertEqual(answered["status"], "answered")
        self.assertIn("not causal confirmation", answered["answer"]["interpretation"])
        self.assertIn("replicate_negative", {q["kind"] for q in opened(report)})

    def test_counterexample_answers_test_and_opens_repair_question(self):
        queue = QuestionQueue("game:L1")
        queue.update([sample(fired_with=1)])
        report = queue.update([sample(fired_with=1, fired_without=1)])
        self.assertEqual(opened(report)[0]["kind"], "explain_contradiction")
        self.assertTrue(any(q["kind"] == "missing_negative" and q["status"] == "answered" for q in report["questions"]))
        report = queue.update([sample(fired_with=5, fired_without=1, silent_without=5)])
        self.assertEqual([q["kind"] for q in opened(report)], ["explain_contradiction"])

    def test_observation_quota_does_not_claim_proof(self):
        self.assertEqual(QuestionQueue("x").update([sample(fired_with=3, silent_without=3)])["open_count"], 0)

    def test_old_reports_are_explicitly_blocked(self):
        pin = sample(fired_with=1)
        del pin["condition"]
        pin["front"] = []
        q = opened(QuestionQueue("x").update([pin]))[0]
        self.assertIn("condition_specification_missing", q["blockers"])
        self.assertIn("control_to_pin_binding_unknown", q["blockers"])
        self.assertFalse(q["execution_ready"])

    def test_constant_ring_does_not_invent_negative_case(self):
        pin = sample(fired_with=3)
        pin["condition"] = {"kind": "constant", "value": True}
        q = opened(QuestionQueue("x").update([pin]))[0]
        self.assertIn("condition_is_always_true_in_current_model", q["blockers"])

    def test_changed_pattern_retires_old_hypothesis(self):
        queue = QuestionQueue("x")
        pin = sample(fired_with=1)
        first_ids = {q["id"] for q in opened(queue.update([pin]))}
        pin["condition"]["reads"] = [[3]]
        report = queue.update([pin])
        self.assertTrue(first_ids.isdisjoint({q["id"] for q in opened(report)}))
        self.assertTrue(all(q["status"] == "retired" for q in report["questions"] if q["id"] in first_ids))

    def test_count_reset_starts_new_epoch(self):
        queue = QuestionQueue("x")
        first = opened(queue.update([sample(fired_with=2)]))
        report = queue.update([sample(fired_with=1)])
        self.assertTrue({q["id"] for q in first}.isdisjoint({q["id"] for q in opened(report)}))
        self.assertTrue(any(q.get("retirement_reason") == "evidence_reset" for q in report["questions"]))

    def test_disappearance_and_return_gets_fresh_questions(self):
        queue = QuestionQueue("x")
        first = opened(queue.update([sample()]))
        self.assertEqual(queue.update([])["open_count"], 0)
        second = opened(queue.update([sample()]))
        self.assertEqual(len(second), 2)
        self.assertTrue({q["id"] for q in first}.isdisjoint({q["id"] for q in second}))

    def test_scope_separates_levels(self):
        a = opened(QuestionQueue("L1").update([sample()]))
        b = opened(QuestionQueue("L2").update([sample()]))
        self.assertTrue({q["id"] for q in a}.isdisjoint({q["id"] for q in b}))

    def test_prompt_contains_evidence_and_no_automatic_execution(self):
        report = QuestionQueue("x").update([sample(fired_with=1)])
        json.dumps(report, allow_nan=False)
        q = opened(report)[0]
        self.assertIn('"fired_with": 1', q["prompt"])
        self.assertIn("Your reply cannot mark a question answered", q["prompt"])
        self.assertEqual(q["transport"], "local_outbox_only")

    def test_invalid_counts_and_conflicting_duplicates(self):
        for value in (-1, 1.5, True):
            with self.assertRaises(ValueError): QuestionQueue("x").update([sample(fired_with=value)])
        with self.assertRaises(ValueError): QuestionQueue("x").update([sample(), sample(fired_with=1)])

    def test_diagonal_dump_retains_pattern_and_frozen_counts(self):
        pins = diagonal.Pins()
        pins.add([5], "switch", np.ones((1, 1), bool),
                 {"frame": "screen", "box": [0, 0, 0, 0], "reads": np.array([[2]])},
                 {"kind": "opens", "target": "door"}, source="magnet")
        saved = pins.dump()
        self.assertEqual(saved[0]["condition"]["reads"], [[2]])
        pins.pins[0]["eye"]["fired_with"] = 8
        self.assertEqual(saved[0]["eye"]["fired_with"], 0)
        self.assertEqual(QuestionQueue("x").update(saved)["open_count"], 2)

    def test_relation_dump_retains_matcher_context(self):
        pins = diagonal.Pins()
        rel = {"region": [0, 0, 0, 0], "targets": [{"id": "door", "pattern": np.array([[2]])}]}
        pins.add([], "switch", np.ones((1, 1), bool),
                 {"frame": "screen", "box": [0, 0, 0, 0], "reads": [[2]]},
                 {"kind": "opens", "target": "door"}, source="relation", rel=rel)
        saved = pins.dump(floor={0, 1})
        self.assertEqual(saved[0]["condition"]["floor"], [0, 1])
        self.assertEqual(saved[0]["condition"]["targets"][0]["pattern"], [[2]])
        self.assertNotIn("relation_floor_context_missing", opened(QuestionQueue("x").update(saved))[0]["blockers"])


if __name__ == "__main__":
    unittest.main()
