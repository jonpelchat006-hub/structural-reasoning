"""Independent mechanics checks for the synthetic support-portfolio experiment.

No test requires a policy to win.  The checks concern real retained learning,
timing, resource conservation, access to non-wage resources, and matched shocks.
"""

import math
import unittest

from alignment_support import SupportConfig, SupportWorld


POLICIES = ("education", "employment", "balanced", "bottleneck")


def funded_config(**changes):
    fields = dict(forgetting=0.0, initial_skills=0, initial_cash=10.0,
                  stipend=10.0, expenses=0.0, ai_unit_upkeep=0.0)
    fields.update(changes)
    return SupportConfig(**fields)


def knowledge(world):
    return [set(topic) for topic in world.learner.candidates[0]]


class LearningAndCapacityTests(unittest.TestCase):
    def test_rest_and_exercise_do_not_manufacture_knowledge(self):
        for action in ("rest", "exercise", "social", "spare"):
            with self.subTest(action=action):
                world = SupportWorld(funded_config())
                original = knowledge(world)
                world.step_actions([action])
                self.assertEqual(knowledge(world), original)

    def test_enjoyment_can_exist_with_no_learning_or_restorative_gain(self):
        world = SupportWorld(funded_config(exercise_recovery=0.0,
                                          attention_recovery=0.0,
                                          physical_recovery=0.0))
        original = knowledge(world)
        result = world.step_actions(["exercise"])
        self.assertGreater(result["enjoyment"], 0.0)
        self.assertEqual(knowledge(world), original)
        self.assertEqual(result["ledger"]["wages"], 0.0)
        self.assertLess(result["attention"], world.cfg.initial_attention)
        self.assertLess(result["physical"], world.cfg.initial_physical)

    def test_rest_is_available_for_enjoyment_without_recovery_need(self):
        world = SupportWorld(funded_config(initial_attention=8.0,
                                          initial_physical=8.0, rest_recovery=0.0))
        original = knowledge(world)
        result = world.step_actions(["rest"])
        self.assertEqual(result["actions"], ["rest"])
        self.assertGreater(result["enjoyment"], 0.0)
        self.assertEqual(result["attention"], 8.0)
        self.assertEqual(result["physical"], 8.0)
        self.assertEqual(knowledge(world), original)

    def test_exercise_recovery_arrives_next_week_without_creating_learning(self):
        world = SupportWorld(funded_config(initial_attention=4.0,
                                          attention_recovery=0.0,
                                          physical_recovery=0.0,
                                          exercise_recovery=1.5))
        original = knowledge(world)
        first = world.step_actions(["exercise"])
        second = world.step_actions(["spare"])
        self.assertAlmostEqual(first["attention"], 3.8)
        self.assertAlmostEqual(second["attention"], 5.3)
        self.assertEqual(knowledge(world), original)

    def test_one_example_per_human_block_cannot_identify_a_rule(self):
        world = SupportWorld(funded_config(human_example_cap=1, ai_capacity=12,
                                          teacher_examples=12))
        result = world.step_actions(["study"])
        self.assertIn("study", result["actions"])
        self.assertEqual(sum(len(c) == 1 for c in knowledge(world)), 0)
        self.assertEqual(sum(len(c) < 25 for c in knowledge(world)), 1)

    def test_teacher_limit_is_not_bypassed_by_larger_ai_capacity(self):
        world = SupportWorld(funded_config(human_example_cap=2, ai_capacity=12,
                                          teacher_examples=1))
        result = world.step_actions(["study"])
        self.assertLessEqual(result["teacher_used"], 1)
        self.assertEqual(sum(len(c) == 1 for c in knowledge(world)), 0)

    def test_study_social_gain_preserves_learning_and_costs_and_caps_support(self):
        for gain in (0.12, 2.0):
            with self.subTest(gain=gain):
                baseline = SupportWorld(funded_config(seed=47, study_social_gain=0.0))
                social_study = SupportWorld(funded_config(seed=47, study_social_gain=gain))
                a = baseline.step_actions(["study"])
                b = social_study.step_actions(["study"])
                self.assertEqual(a["actions"], ["study"])
                self.assertEqual(b["actions"], ["study"])
                self.assertAlmostEqual(b["social"], min(1.0, a["social"] + gain))
                self.assertGreater(b["social"], a["social"])
                self.assertEqual(knowledge(baseline), knowledge(social_study))
                for field in ("knowledge", "accuracy", "cumulative_messages", "teacher_used",
                              "ai_used", "attention", "physical", "free_time", "ledger"):
                    self.assertEqual(a[field], b[field], field)

    def test_infeasible_study_does_not_deliver_social_support(self):
        for limit in ({"teacher_examples": 0},
                      {"initial_attention": 0.0, "attention_recovery": 0.0}):
            with self.subTest(limit=limit):
                cfg = funded_config(study_social_gain=0.12, **limit)
                rejected = SupportWorld(cfg)
                control = SupportWorld(cfg)
                a = rejected.step_actions(["study"])
                b = control.step_actions(["spare"])
                self.assertEqual(a["actions"], [])
                self.assertEqual(a["rejected"], ["study"])
                self.assertEqual(a["social"], b["social"])
                self.assertEqual(knowledge(rejected), knowledge(control))
                self.assertEqual(a["teacher_used"], 0)
                self.assertEqual(a["cumulative_messages"], 0)

    def test_larger_curriculum_can_learn_a_required_topic_beyond_the_old_limit(self):
        world = SupportWorld(funded_config(n_topics=64, initial_skills=63,
                                          required_topics=(63,), teacher_examples=2,
                                          ai_capacity=1, human_example_cap=2))
        self.assertEqual(world.metrics()["knowledge"], 63.0)
        self.assertTrue(world.metrics()["ground_shortfall"])
        result = world.step_actions(["study"])
        self.assertEqual(result["knowledge"], 64.0)
        self.assertFalse(result["ground_shortfall"])
        self.assertEqual(result["accuracy"], 1.0)

    def test_additional_ai_cannot_force_more_than_human_uptake(self):
        small = SupportWorld(funded_config(ai_capacity=2, teacher_examples=12,
                                          human_example_cap=2))
        large = SupportWorld(funded_config(ai_capacity=12, teacher_examples=12,
                                          human_example_cap=2))
        a = small.step_actions(["study"])
        b = large.step_actions(["study"])
        self.assertEqual(knowledge(small), knowledge(large))
        self.assertLessEqual(a["teacher_used"], 2)
        self.assertLessEqual(b["teacher_used"], 2)

    def test_all_policies_respect_identical_time_and_teaching_limits(self):
        for policy in POLICIES:
            with self.subTest(policy=policy):
                cfg = funded_config(time_blocks=8, reserve_blocks=2,
                                    teacher_examples=3, ai_capacity=2)
                world = SupportWorld(cfg)
                for result in world.run(policy, weeks=4):
                    self.assertLessEqual(len(result["actions"]), 6)
                    self.assertGreaterEqual(result["free_time"], 2)
                    self.assertLessEqual(result["teacher_used"], 3)
                    self.assertLessEqual(result["ai_used"], 2)


class IncomeAndTimingTests(unittest.TestCase):
    def test_successful_application_does_not_pay_wages_until_later_work(self):
        world = SupportWorld(funded_config(job_chance=1.0, job_delay=2))
        first = world.step_actions(["search", "work"])
        second = world.step_actions(["work"])
        third = world.step_actions(["work"])
        self.assertIn("search", first["actions"])
        self.assertNotIn("work", first["actions"])
        self.assertNotIn("work", second["actions"])
        self.assertEqual(first["ledger"]["wages"], 0)
        self.assertEqual(second["ledger"]["wages"], 0)
        self.assertIn("work", third["actions"])
        self.assertGreater(third["ledger"]["wages"], 0)

    def test_transfers_can_cover_material_needs_without_employment(self):
        world = SupportWorld(funded_config(initial_cash=0.0, stipend=2.0,
                                          expenses=2.0, ai_capacity=0,
                                          initial_skills=2))
        result = world.step_actions(["spare"])
        self.assertFalse(result["job"])
        self.assertEqual(result["ledger"]["wages"], 0.0)
        self.assertEqual(result["cash"], 0.0)
        self.assertFalse(result["water_shortfall"])

    def test_matched_hiring_draws_do_not_depend_on_unrelated_action_order(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                cfg = funded_config(seed=seed, ai_capacity=0, job_chance=0.35,
                                    job_delay=1)
                direct = SupportWorld(cfg)
                reordered = SupportWorld(cfg)
                direct.step_actions(["search"])
                reordered.step_actions(["exercise", "search"])
                a = direct.step_actions(["spare"])["job_events"][0]
                b = reordered.step_actions(["spare"])["job_events"][0]
                self.assertEqual(a["probability"], b["probability"])
                self.assertEqual(a["success"], b["success"])

    def test_cash_ledger_counts_transfers_expenses_and_ai_cost(self):
        world = SupportWorld(funded_config(initial_cash=7.0, stipend=3.0,
                                          expenses=2.0, ai_capacity=4,
                                          ai_unit_upkeep=0.25))
        previous = 7.0
        for _ in range(3):
            result = world.step_actions(["spare"])
            ledger = result["ledger"]
            self.assertAlmostEqual(ledger["opening_cash"], previous)
            self.assertEqual(ledger["wages"], 0.0)
            self.assertEqual(ledger["stipend"], 3.0)
            self.assertEqual(ledger["expenses"], 2.0)
            self.assertEqual(ledger["ai_cost"], 1.0)
            expected = (ledger["opening_cash"] + ledger["stipend"] + ledger["wages"]
                        - ledger["expenses"] - ledger["ai_cost"])
            self.assertAlmostEqual(ledger["closing_cash"], expected)
            previous = ledger["closing_cash"]


class CounterfactualAndFloorTests(unittest.TestCase):
    def test_forgetting_matches_when_rest_choices_and_delivery_rng_differ(self):
        cfg = funded_config(seed=47, forgetting=0.3, initial_skills=8)
        a = SupportWorld(cfg)
        b = SupportWorld(cfg)
        original = knowledge(a)
        for week in range(1, 7):
            for _ in range(17 * week):
                b.learner._rng.random()
            a.step_actions(["spare"])
            b.step_actions(["exercise"])
            self.assertEqual(knowledge(a), knowledge(b))
        self.assertNotEqual(knowledge(a), original)

    def test_named_shortfalls_are_separate_from_knowledge_and_job_status(self):
        cfg = funded_config(initial_skills=2, initial_social=0.8,
                            initial_attention=6.0, initial_physical=6.0)
        flags = ("water_shortfall", "ground_shortfall", "air_shortfall",
                 "fire_shortfall", "void_shortfall")
        for field, value, expected in (("cash", -0.1, "water_shortfall"),
                                       ("social", 0.3, "air_shortfall"),
                                       ("attention", 1.0, "fire_shortfall"),
                                       ("physical", 0.5, "fire_shortfall")):
            with self.subTest(field=field):
                world = SupportWorld(cfg)
                self.assertTrue(world.metrics()["viable"])
                setattr(world, field, value)
                result = world.metrics()
                self.assertEqual([flag for flag in flags if result[flag]], [expected])
                self.assertEqual(result["knowledge"], 2.0)
                self.assertFalse(result["job"])

    def test_rejected_work_does_not_consume_time_or_pay_wages(self):
        world = SupportWorld(funded_config())
        result = world.step_actions(["work", "work"])
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["rejected"], ["work", "work"])
        self.assertEqual(result["free_time"], world.cfg.time_blocks)
        self.assertEqual(result["ledger"]["wages"], 0.0)


class ValidationTests(unittest.TestCase):
    def test_invalid_action_rejected_before_the_week_advances(self):
        world = SupportWorld(funded_config())
        with self.assertRaises(ValueError):
            world.step_actions(["study", "invent-free-money"])
        self.assertEqual(world.step_actions(["spare"])["week"], 1)

    def test_explicit_plan_cannot_spend_protected_time(self):
        world = SupportWorld(funded_config(time_blocks=8, reserve_blocks=2))
        with self.assertRaises(ValueError):
            world.step_actions(["spare"] * 7)
        self.assertEqual(world.step_actions(["spare"])["week"], 1)

    def test_invalid_configuration_rejected(self):
        invalid = (
            {"time_blocks": 0}, {"time_blocks": 2, "reserve_blocks": 3},
            {"job_delay": 0}, {"job_chance": -0.1}, {"job_chance": 1.1},
            {"forgetting": math.nan}, {"ai_unit_upkeep": -1.0},
            {"initial_cash": math.inf}, {"required_topics": (8,)},
            {"study_social_gain": -0.1}, {"study_social_gain": math.nan},
        )
        for fields in invalid:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    SupportWorld(funded_config(**fields))


if __name__ == "__main__":
    unittest.main()
