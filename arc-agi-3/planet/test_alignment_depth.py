"""Independent invariants for the alignment learning-world experiments.

These tests check learning, observability and accounting.  They deliberately do
not require any allocation policy, including schooling, to beat another policy.
"""

import math
import unittest

from alignment_depth import Config, World


POLICIES = ("reserve", "enjoy", "repeat", "school", "peer", "discover", "mixed")


class LearningTests(unittest.TestCase):
    def blank_world(self):
        world = World(Config(n_agents=1, n_topics=1, school_topics=0,
                             modulus=5, forgetting=0.0))
        # Truth belongs to the evaluator.  Agents only receive the observations
        # explicitly delivered below, never the truth tuple itself.
        world.rules[0] = (2, 1)
        world.candidates[0][0] = {(a, b) for a in range(5) for b in range(5)}
        return world

    def test_two_distinct_examples_generalize_to_unseen_inputs(self):
        world = self.blank_world()
        world.observe(0, 0, 0, 1)
        world.observe(0, 0, 1, 3)

        self.assertEqual(world.candidates[0][0], {(2, 1)})
        a, b = next(iter(world.candidates[0][0]))
        # Literal expected answers for y = 2*x+1 (mod 5), neither trained on.
        self.assertEqual((a * 3 + b) % 5, 2)
        self.assertEqual((a * 4 + b) % 5, 4)
        measured = world.metrics(required_topics=(0,))
        self.assertEqual(measured["depth_mean"], 1.0)
        self.assertEqual(measured["accuracy"], 1.0)

    def test_repetition_does_not_create_identifying_evidence(self):
        world = self.blank_world()
        for _ in range(100):
            world.observe(0, 0, 0, 1)

        self.assertEqual(len(world.candidates[0][0]), 5)
        predictions = {(a * 3 + b) % 5 for a, b in world.candidates[0][0]}
        self.assertEqual(predictions, {0, 1, 2, 3, 4})
        measured = world.metrics(required_topics=(0,))
        self.assertEqual(measured["depth_mean"], 0.0)
        self.assertAlmostEqual(measured["accuracy"], 0.2)

    def test_consistent_false_evidence_can_produce_wrong_confidence(self):
        world = self.blank_world()
        world.observe(0, 0, 0, 0)
        world.observe(0, 0, 1, 1)

        self.assertEqual(world.candidates[0][0], {(1, 0)})
        self.assertNotEqual(next(iter(world.candidates[0][0])), world.rules[0])
        a, b = next(iter(world.candidates[0][0]))
        self.assertNotEqual((a * 3 + b) % 5, 2)
        measured = world.metrics(required_topics=(0,))
        self.assertEqual(measured["confidence_mean"], 1.0)
        self.assertEqual(measured["depth_mean"], 0.0)
        # The wrong rule happens to agree at x=4, but not at x=3.
        self.assertEqual(measured["accuracy"], 0.5)
        self.assertEqual(measured["floor_failures"], 1)

    def test_access_exclusion_prevents_lessons_reaching_a_person(self):
        world = World(Config(n_agents=4, n_topics=1, school_topics=1,
                             budget=8, forgetting=0.0, teach_fidelity=1.0))
        original = set(world.candidates[2][0])
        world.run("school", rounds=10, access=[True, True, False, True])

        self.assertEqual(world.candidates[2][0], original)
        self.assertEqual(world.candidates[3][0], {world.rules[0]})

    def test_transmission_policies_cannot_use_hidden_truth_to_select_lessons(self):
        for policy in ("school", "peer", "repeat"):
            with self.subTest(policy=policy):
                original = World(Config(n_agents=4, n_topics=3, school_topics=2,
                                        budget=3, forgetting=0.0, teach_fidelity=0.7))
                altered_truth = original.clone()
                # Same beliefs, archive, peers and delivery randomness; only the
                # evaluator's hidden answers differ.  Discovery is intentionally
                # excluded because it pays to acquire an external true label.
                altered_truth.rules = [(a, (b + 1) % 5) for a, b in original.rules]
                for _ in range(3):
                    original.step(policy)
                    altered_truth.step(policy)
                    self.assertEqual(original.candidates, altered_truth.candidates)
                    self.assertEqual(original.spent, altered_truth.spent)
                    self.assertEqual(original.messages, altered_truth.messages)


class AccessAndCounterfactualTests(unittest.TestCase):
    def test_service_supports_requirement_without_writing_internal_knowledge(self):
        world = World(Config(n_agents=3, n_topics=2, school_topics=1,
                             forgetting=0.0, service_accuracy=1.0))
        original = [[set(topic) for topic in agent] for agent in world.candidates]
        baseline = world.metrics(required_topics=(0,))
        served = world.metrics(required_topics=(0,), service_access=[True] * 3)
        outage = world.metrics(required_topics=(0,), service_access=[True, True, False])

        self.assertEqual(baseline["floor_failures"], 1)
        self.assertEqual(served["effective_floor_failures"], 0)
        self.assertEqual(outage["effective_floor_failures"], 1)
        self.assertEqual(served["depth_by_agent"], [1, 1, 0])
        self.assertEqual(served["depth_mean"], baseline["depth_mean"])
        self.assertEqual(served["accuracy"], baseline["accuracy"])
        self.assertGreater(served["accessible_depth_mean"], baseline["accessible_depth_mean"])
        self.assertEqual(world.candidates, original)

    def test_service_cannot_satisfy_a_requirement_outside_its_archive(self):
        world = World(Config(n_agents=3, n_topics=2, school_topics=1,
                             forgetting=0.0))
        result = world.metrics(required_topics=(0, 1), service_access=[True] * 3)
        self.assertEqual(result["effective_floor_failures"], 3)

    def test_noisy_service_is_not_reported_as_guaranteed_coverage(self):
        world = World(Config(n_agents=3, n_topics=1, school_topics=1,
                             forgetting=0.0, service_accuracy=0.5))
        result = world.metrics(required_topics=(0,), service_access=[True] * 3)
        self.assertEqual(result["effective_floor_failures"], 1)

    def test_forgetting_matches_despite_different_delivery_rng_consumption(self):
        original = World(Config(seed=47, n_agents=6, n_topics=5,
                                school_topics=5, forgetting=0.35))
        for agent in range(original.cfg.n_agents):
            original.candidates[agent] = [{rule} for rule in original.rules]
        other = original.clone()

        for round_number in range(1, 7):
            # A policy may consume a completely different number of random
            # delivery draws.  It must still face the same exogenous shock.
            for _ in range(37 * round_number):
                other._rng.random()
            original.step("reserve")
            other.step("enjoy")
            self.assertEqual(original.candidates, other.candidates)
            if round_number == 1:
                forgotten = sum(len(topic) > 1 for agent in original.candidates for topic in agent)
                self.assertGreater(forgotten, 0)
                self.assertLess(forgotten, 30)

    def test_counterfactual_clone_does_not_share_mutable_state(self):
        original = World(Config(n_agents=3, n_topics=2, school_topics=1,
                                peer_connectivity=1.0))
        cloned = original.clone()
        cloned.candidates[2][1].clear()
        cloned.archive[0][0] = (cloned.archive[0][0] + 1) % cloned.cfg.modulus
        cloned.peers[0].clear()
        self.assertEqual(len(original.candidates[2][1]), 25)
        self.assertNotEqual(original.archive[0][0], cloned.archive[0][0])
        self.assertEqual(original.peers[0], {1, 2})


class AccountingTests(unittest.TestCase):
    def test_each_policy_accounts_for_actual_spending_and_unused_budget(self):
        budget = 3.25
        for policy in POLICIES:
            with self.subTest(policy=policy):
                world = World(Config(n_agents=4, n_topics=3, school_topics=1,
                                     budget=budget, discovery_cost=1.75,
                                     forgetting=0.0))
                previous_spent = 0.0
                previous_reserve = 0.0
                for round_number in range(1, 5):
                    world.step(policy)
                    increment = world.spent - previous_spent
                    self.assertGreaterEqual(increment, -1e-10)
                    self.assertLessEqual(increment, budget + 1e-10)
                    self.assertGreaterEqual(world.reserve, previous_reserve - 1e-10)
                    self.assertAlmostEqual(world.spent + world.reserve,
                                           round_number * budget)
                    previous_spent = world.spent
                    previous_reserve = world.reserve

    def test_unaffordable_actions_terminate_and_preserve_the_budget(self):
        for budget in (0.0, 0.25):
            for policy in POLICIES:
                with self.subTest(budget=budget, policy=policy):
                    world = World(Config(n_agents=3, n_topics=2, school_topics=1,
                                         budget=budget, discovery_cost=2.0,
                                         forgetting=0.0))
                    world.run(policy, rounds=3)
                    self.assertEqual(world.round, 3)
                    self.assertEqual(world.spent, 0.0)
                    self.assertAlmostEqual(world.reserve, 3 * budget)

    def test_discovery_cost_greater_than_budget_does_not_overspend(self):
        world = World(Config(n_agents=3, n_topics=2, school_topics=0,
                             budget=1.0, discovery_cost=2.0, forgetting=0.0))
        world.run("discover", rounds=4)
        self.assertEqual(world.spent, 0.0)
        self.assertEqual(world.reserve, 4.0)


class ValidationTests(unittest.TestCase):
    def test_invalid_configuration_is_rejected(self):
        invalid = (
            {"n_agents": 0}, {"n_topics": 0}, {"modulus": 4},
            {"school_topics": -1}, {"school_topics": 9, "n_topics": 8},
            {"budget": -1}, {"budget": math.inf}, {"budget": math.nan},
            {"discovery_cost": 0}, {"discovery_cost": math.inf},
            {"teach_fidelity": -0.1}, {"teach_fidelity": 1.1},
            {"forgetting": math.nan}, {"peer_connectivity": 1.1},
            {"service_accuracy": -0.1},
            {"n_agents": 1.5}, {"n_topics": True}, {"modulus": 5.0},
            {"budget": "8"}, {"discovery_cost": False},
        )
        for fields in invalid:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    World(Config(**fields))

    def test_invalid_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            World().step("unrecognized-policy")

    def test_evaluation_inputs_cannot_be_supplied_as_training_observations(self):
        world = World(Config(n_agents=1, n_topics=1, school_topics=0))
        for x in (3, 4):
            with self.subTest(x=x):
                with self.assertRaises(ValueError):
                    world.observe(0, 0, x, 0)

    def test_invalid_runtime_inputs_are_rejected(self):
        world = World(Config(n_agents=3, n_topics=2, school_topics=0))
        for rounds in (-1, 1.5, True):
            with self.subTest(rounds=rounds):
                with self.assertRaises(ValueError):
                    world.run("reserve", rounds)
        for access in ([True], [True, True, 1]):
            with self.subTest(access=access):
                with self.assertRaises(ValueError):
                    world.step("school", access=access)
        for topic in (-1, 2):
            with self.subTest(topic=topic):
                with self.assertRaises(ValueError):
                    world.metrics(required_topics=(topic,))


if __name__ == "__main__":
    unittest.main()
