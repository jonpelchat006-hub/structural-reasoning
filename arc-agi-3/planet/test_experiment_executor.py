from copy import deepcopy
import unittest
import numpy as np
from cube_router import local_proposals
from experiment_executor import ExperimentExecutor, ExperimentBlocked
from pin_questions import QuestionQueue
from test_pin_questions import sample


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.queue = QuestionQueue("L1")
        self.pin = sample(fired_with=1)
        self.report = self.queue.update([self.pin])
        self.q = next(q for q in self.report["questions"] if q["kind"] == "missing_negative")
        self.proposal = local_proposals(self.report, "v1")["proposals"][self.q["id"]]
        self.before = np.zeros((3, 3), int)  # condition color 2 absent
        self.after = self.before.copy(); self.after[2, 2] = 5
        self.calls = []
        self.executor = ExperimentExecutor()
        self.args = dict(expected_version="v1", current_version="v1", current_scope="L1",
                         available_actions=[5], remaining_actions=3, at_foot=True,
                         observer={"target": "door", "kind": "pattern_appeared", "box": [2, 2, 2, 2], "pattern": [[5]]},
                         send=self.send)

    def send(self, action):
        self.calls.append(action)
        return {"frame": self.after, "action": action, "scope": "L1"}

    def run_test(self, **kw):
        return self.executor.run(self.proposal, self.q, self.before, **{**self.args, **kw})

    def test_question_to_cubes_to_action_to_counterexample(self):
        result = self.run_test()
        self.assertEqual(self.calls, [5])
        self.assertEqual(result["evidence_delta"], {"fired_without": 1})
        pin = deepcopy(self.pin)
        for name, count in result["evidence_delta"].items(): pin["eye"][name] += count
        report = self.queue.update([pin])
        self.assertEqual(next(q for q in report["questions"] if q["id"] == self.q["id"])["status"], "answered")
        self.assertTrue(any(q["kind"] == "explain_contradiction" and q["status"] == "open" for q in report["questions"]))
        self.assertFalse(result["causal_confirmation"])

    def test_silence_is_an_observation_not_a_guessed_success(self):
        self.after = self.before.copy()
        self.assertEqual(self.run_test()["evidence_delta"], {"silent_without": 1})

    def test_stale_wrong_scope_unreachable_and_low_budget_never_dispatch(self):
        for change in (dict(current_version="v2"), dict(current_scope="L2"), dict(at_foot=False),
                       dict(remaining_actions=1), dict(remaining_actions=None), dict(available_actions=[]), dict(observer=None)):
            with self.assertRaises(ExperimentBlocked): self.run_test(**change)
        self.assertEqual(self.calls, [])

    def test_condition_is_rechecked_on_current_pixels(self):
        self.before[0, 0] = 2
        with self.assertRaises(ExperimentBlocked): self.run_test()
        self.assertEqual(self.calls, [])

    def test_already_present_effect_is_not_credited(self):
        self.before[2, 2] = 5
        with self.assertRaises(ExperimentBlocked): self.run_test()

    def test_duplicate_dispatch_rejected(self):
        self.run_test()
        with self.assertRaises(ExperimentBlocked): self.run_test()
        self.assertEqual(self.calls, [5])

    def test_uncertain_transport_is_not_retried_or_scored(self):
        def timeout(a): self.calls.append(a); raise TimeoutError("no reply")
        result = self.run_test(send=timeout)
        self.assertEqual(result["status"], "uncertain")
        self.assertIsNone(result["evidence_delta"])
        with self.assertRaises(ExperimentBlocked): self.run_test()
        self.assertEqual(self.calls, [5])

    def test_level_change_is_inconclusive_for_this_observer(self):
        result = self.run_test(send=lambda a: {"frame": self.after, "scope": "L2", "action": a})
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["evidence_delta"])


if __name__ == "__main__":
    unittest.main()
