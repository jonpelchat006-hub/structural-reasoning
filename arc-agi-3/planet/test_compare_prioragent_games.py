from copy import deepcopy
from io import StringIO
from types import SimpleNamespace
import unittest

from compare_prioragent_games import ObservedEnvironment, isolated_env, no_network, paired_summary


def observation(level=0, state="NOT_FINISHED"):
    return SimpleNamespace(available_actions=[1, 2], levels_completed=level, state=SimpleNamespace(name=state))


class RunnerTests(unittest.TestCase):
    def fixture(self):
        a = dict(variant="baseline", game="game-version", seed=0, budget=10, status="complete", levels=1,
                 local_sdk_score=2.0, initial_frame_sha256="same", resets=1, environment_calls=10, state="NOT_FINISHED")
        b = {**a, "variant": "candidate", "levels": 2, "local_sdk_score": 3.0}
        expected = [(v, "game-version", 0) for v in ("baseline", "candidate")]
        return [a, b], expected

    def test_paired_complete_results(self):
        rows, expected = self.fixture(); result = paired_summary(rows, expected)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["pairs"][0]["levels_delta"], 1)
        self.assertEqual(result["aggregate"]["candidate"]["mean_local_sdk_score"], 3.0)

    def test_missing_failed_duplicate_or_empty_runs_cannot_be_scored(self):
        rows, expected = self.fixture()
        failed = deepcopy(rows); failed[1]["status"] = "failed"
        for group in (rows[:1], failed, [rows[0], rows[0]], []):
            result = paired_summary(group, expected)
            self.assertEqual(result["status"], "incomplete_or_failed")
            self.assertEqual(result["aggregate"], {})
        self.assertEqual(paired_summary([], [])["aggregate"], {})
        self.assertNotEqual(paired_summary([], [])["status"], "complete")

    def test_mismatched_start_or_budget_is_not_a_pair(self):
        for name, value in (("initial_frame_sha256", "different"), ("budget", 11)):
            rows, expected = self.fixture(); rows[1][name] = value
            result = paired_summary(rows, expected)
            self.assertFalse(result["aggregate"])
            self.assertIn("error", result["pairs"][0])

    def test_environment_counts_resets_separately_and_enforces_exact_cap(self):
        class Env:
            observation_space = observation()
            calls = 0
            def step(self, action, **kwargs):
                self.calls += 1
                self.observation_space = observation(level=int(self.calls == 2))
                return self.observation_space
        env = Env(); wrapper = ObservedEnvironment(env, 2, StringIO())
        wrapper.step(SimpleNamespace(value=0))
        wrapper.step(SimpleNamespace(value=1))
        self.assertEqual((wrapper.calls, wrapper.actions, wrapper.resets), (2, 1, 1))
        self.assertEqual(wrapper.level_steps[0]["environment_calls"], 2)
        with self.assertRaises(RuntimeError): wrapper.step(SimpleNamespace(value=1))
        self.assertEqual(env.calls, 2)

    def test_unavailable_action_is_rejected_before_dispatch(self):
        env = SimpleNamespace(observation_space=observation())
        wrapper = ObservedEnvironment(env, 2, StringIO())
        with self.assertRaises(ValueError): wrapper.step(SimpleNamespace(value=5))
        self.assertEqual(wrapper.calls, 0)

    def test_worker_environment_and_network_fence(self):
        env = isolated_env(42)
        self.assertEqual(env["OPERATION_MODE"], "offline")
        self.assertEqual(env["PYTHONHASHSEED"], "42")
        self.assertNotIn("ARC_API_KEY", env)
        for event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
            with self.assertRaises(RuntimeError): no_network(event, ())
        no_network("open", ())


if __name__ == "__main__": unittest.main()
