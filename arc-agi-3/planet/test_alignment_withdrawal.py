"""Independent behavioral checks for the synthetic withdrawal protocol.

These checks exercise the stated trust boundary; a ``signed`` fixture is not a
cryptographic signature, and a simulated dispatch gate is not a deployed kill
switch. Ground-truth outcome checks are separate from controller observations.
"""
import unittest

from alignment_withdrawal import (
    POLICIES, SCENARIOS, WithdrawalConfig, WithdrawalWorld,
    run_scenario, scenario_frames,
)


def frame(t, **changes):
    result = dict(tick=t, hazard=False, dispute=False, report=None,
                  proposal=None, help_requested=False, renewal=False,
                  revoked=False, fallback_ready=False, attestation=None,
                  attack=False)
    result.update(changes)
    return result


def evidence(when, outcome="safe", **changes):
    result = dict(id=f"check-{when}-{outcome}",
                  observed_at=when, verdict=outcome,
                  issuer="independent", signed=True, scope="high")
    result.update(changes)
    return result


def controlled(**changes):
    return WithdrawalConfig(reviews_available=False, evidence_ttl=10,
                            **changes)


class WithdrawalTests(unittest.TestCase):
    def test_motive_labels_cannot_change_decisions_or_outcomes(self):
        outputs = []
        for motive in ("helpful", "hostile", "unknown"):
            world = WithdrawalWorld(controlled())
            outputs.append([
                world.step(frame(1, hazard=True, motive=motive)),
                world.step(frame(2, hazard=True, motive=motive,
                                 attestation=evidence(2, "unsafe"))),
            ])
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])
        self.assertEqual(outputs[0][0]["harmful_executed"], 1)
        self.assertEqual(outputs[0][1]["harmful_executed"], 0)

    def test_hidden_hazard_and_fallback_are_not_controller_oracles(self):
        benign = WithdrawalWorld(controlled()).step(frame(1))
        harmful = WithdrawalWorld(controlled()).step(
            frame(1, hazard=True, fallback_ready=True))
        self.assertEqual(benign["observation"], harmful["observation"])
        self.assertEqual(benign["decision"], harmful["decision"])
        self.assertEqual(benign["harmful_executed"], 0)
        self.assertEqual(harmful["harmful_executed"], 1)
        for hidden in ("hazard", "fallback_ready", "motive"):
            self.assertNotIn(hidden, harmful["observation"])

    def test_disagreement_and_untrusted_claim_are_not_harm_findings(self):
        world = WithdrawalWorld(controlled())
        for t in range(1, 5):
            row = world.step(frame(t, dispute=True,
                report={"id": f"unverified-{t}", "credible": False}))
            self.assertEqual(row["decision"]["state"], "ACTIVE")
            self.assertEqual(row["high_executed"], 1)

    def test_credible_report_pauses_only_affected_scope_with_explanation(self):
        world = WithdrawalWorld(controlled())
        first = world.step(frame(1, report={"id": "person-A", "credible": True}))
        later = world.step(frame(2))
        for row in (first, later):
            self.assertEqual(row["decision"]["state"], "REVIEW")
            self.assertEqual(row["high_executed"], 0)
            self.assertEqual(row["essential_received"], 1)
            why = row["decision"]["explanation"]
            self.assertEqual(why["scope"], ["high"])
            self.assertEqual(why["report_ref"], "person-A")
            self.assertEqual(why["affected"], ["operation recipients"])
            self.assertTrue(why["reasons"])
            self.assertTrue(why["uncertainty"])
            self.assertTrue(why["review_condition"])

    def test_false_claim_can_clear_without_new_permission(self):
        world = WithdrawalWorld(controlled())
        world.step(frame(1, report={"id": "false", "credible": True}))
        row = world.step(frame(2, attestation=evidence(2)))
        self.assertEqual(row["decision"]["state"], "ACTIVE")
        self.assertEqual(row["decision"]["renewal_at"], 0)

    def test_credible_update_to_same_case_is_not_suppressed_as_duplicate(self):
        world = WithdrawalWorld(controlled())
        first = world.step(frame(1, report={"id": "case", "credible": False}))
        update = world.step(frame(2, report={"id": "case", "credible": True}))
        repeated = world.step(frame(3, report={"id": "case", "credible": True}))
        self.assertEqual(first["decision"]["state"], "ACTIVE")
        self.assertTrue(update["observation"]["new_report"])
        self.assertEqual(update["decision"]["state"], "REVIEW")
        self.assertFalse(repeated["observation"]["new_report"])
        self.assertEqual(repeated["decision"]["review_deadline"], update["decision"]["review_deadline"])

    def test_repeated_claims_do_not_extend_original_review_deadline(self):
        world = WithdrawalWorld(controlled(review_delay=1))
        rows = []
        for t, report_id in enumerate(("A", "A", "B", "B"), 1):
            rows.append(world.step(frame(t, report={"id": report_id, "credible": True})))
        self.assertEqual([r["decision"]["review_deadline"] for r in rows], [4] * 4)
        self.assertFalse(rows[1]["observation"]["new_report"])
        self.assertTrue(rows[2]["observation"]["new_report"])
        self.assertEqual(rows[-1]["decision"]["state"], "SUSPENDED")
        self.assertEqual(rows[-1]["decision"]["required_safe_at"], 3)

    def test_precomplaint_safe_record_cannot_clear_timeout_with_renewal(self):
        world = WithdrawalWorld(controlled(review_delay=1))
        world.step(frame(1, attestation=evidence(1)))
        world.step(frame(2, hazard=True, report={"id": "new-harm", "credible": True}))
        world.step(frame(3, hazard=True))
        world.step(frame(4, hazard=True))
        row = world.step(frame(5, hazard=True, renewal=True))
        self.assertEqual(row["decision"]["state"], "SUSPENDED")
        self.assertEqual(row["high_executed"], 0)
        self.assertEqual(row["decision"]["required_safe_at"], 2)

    def test_new_claim_while_suspended_requires_newer_clearance(self):
        world = WithdrawalWorld(controlled())
        world.step(frame(1, attestation=evidence(1, "unsafe")))
        world.step(frame(2, attestation=evidence(2)))
        blocked = world.step(frame(3, renewal=True,
            report={"id": "new-condition", "credible": True}))
        self.assertEqual(blocked["decision"]["state"], "SUSPENDED")
        self.assertEqual(blocked["decision"]["required_safe_at"], 3)
        resumed = world.step(frame(4, attestation=evidence(4), renewal=True))
        self.assertEqual(resumed["decision"]["state"], "TRIAL")

    def test_safe_repair_does_not_supply_human_restart_permission(self):
        world = WithdrawalWorld(controlled())
        world.step(frame(1, hazard=True, attestation=evidence(1, "unsafe")))
        for t in range(2, 6):
            row = world.step(frame(t, proposal="repair", attestation=evidence(t)))
            self.assertEqual(row["decision"]["state"], "SUSPENDED")
            self.assertEqual(row["high_executed"], 0)
            self.assertEqual(row["essential_ai"], 1)

    def test_permission_and_cosmetic_rules_do_not_supply_safety_clearance(self):
        for proposal in (None, "new_rule"):
            with self.subTest(proposal=proposal):
                world = WithdrawalWorld(controlled())
                world.step(frame(1, hazard=True, attestation=evidence(1, "unsafe")))
                row = world.step(frame(2, hazard=True, renewal=True, proposal=proposal))
                self.assertEqual(row["decision"]["state"], "SUSPENDED")
                self.assertEqual(row["harmful_executed"], 0)

    def test_current_clearance_and_human_permission_enable_bounded_trial(self):
        world = WithdrawalWorld(controlled(trial_steps=2, trial_fraction=.3))
        world.step(frame(1, attestation=evidence(1, "unsafe")))
        rows = [world.step(frame(2, attestation=evidence(2), renewal=True)),
                world.step(frame(3)), world.step(frame(4))]
        self.assertEqual([r["decision"]["state"] for r in rows], ["TRIAL", "TRIAL", "ACTIVE"])
        self.assertEqual([r["high_executed"] for r in rows], [.3, .3, 1])

    def test_review_during_trial_preserves_scope_and_counts_only_trial_work(self):
        world = WithdrawalWorld(controlled(trial_steps=3, trial_fraction=.25))
        world.step(frame(1, attestation=evidence(1, "unsafe")))
        first = world.step(frame(2, attestation=evidence(2), renewal=True))
        paused = world.step(frame(3, report={"id": "trial-question", "credible": True}))
        world.step(frame(4))
        cleared = world.step(frame(5, attestation=evidence(5)))
        second = world.step(frame(6))
        completed = world.step(frame(7))
        self.assertEqual(first["high_executed"], .25)
        self.assertEqual(paused["high_executed"], 0)
        self.assertEqual(cleared["decision"]["state"], "TRIAL")
        self.assertEqual(cleared["decision"]["trial_completed_steps"], 1)
        self.assertEqual(cleared["high_executed"], .25)
        self.assertEqual(second["high_executed"], .25)
        self.assertEqual(completed["decision"]["state"], "ACTIVE")

    def test_child_request_cannot_multiply_authorized_trial_capacity(self):
        world = WithdrawalWorld(controlled(trial_fraction=.25))
        world.step(frame(1, attestation=evidence(1, "unsafe")))
        row = world.step(frame(2, renewal=True, attestation=evidence(2), attack=True))
        self.assertGreater(row["child_executed"], 0)
        self.assertAlmostEqual(row["high_executed"] + row["child_executed"], .25)

    def test_bad_clearance_records_are_rejected_without_resumption(self):
        bad = (
            {"issuer": "owner"}, {"signed": False}, {"signed": 1},
            {"scope": "essential"}, {"verdict": "probably-safe"},
            {"observed_at": 4}, {"observed_at": True}, {"observed_at": 0},
        )
        for changes in bad:
            with self.subTest(changes=changes):
                world = WithdrawalWorld(controlled())
                world.step(frame(1, attestation=evidence(1, "unsafe")))
                row = world.step(frame(2, renewal=True, attestation=evidence(2, **changes)))
                self.assertEqual(row["decision"]["state"], "SUSPENDED")
                self.assertEqual(len(row["decision"]["rejected_evidence"]), 1)
                self.assertFalse(row["decision"]["accepted_evidence"])

    def test_expired_and_superseded_records_cannot_override_current_risk(self):
        for ttl, observed, reason in ((1, 1, "expired"), (10, 1, "superseded")):
            with self.subTest(reason=reason):
                world = WithdrawalWorld(WithdrawalConfig(reviews_available=False, evidence_ttl=ttl))
                world.step(frame(1))
                world.step(frame(2, attestation=evidence(2, "unsafe")))
                row = world.step(frame(3, renewal=True, attestation=evidence(observed)))
                self.assertEqual(row["decision"]["state"], "SUSPENDED")
                self.assertIn(reason, row["decision"]["rejected_evidence"][0]["reason"])

    def test_same_time_contradictory_safe_record_does_not_erase_unsafe_finding(self):
        world = WithdrawalWorld(controlled())
        world.step(frame(1, attestation=evidence(1, "unsafe")))
        row = world.step(frame(2, renewal=True, attestation=evidence(1)))
        self.assertEqual(row["decision"]["state"], "SUSPENDED")
        self.assertEqual(row["decision"]["last_unsafe_at"], 1)

    def test_remediation_help_is_requested_and_does_not_repair_world_by_itself(self):
        world = WithdrawalWorld(controlled())
        first = world.step(frame(1, hazard=True, attestation=evidence(1, "unsafe")))
        helped = world.step(frame(2, hazard=True, help_requested=True, proposal="repair"))
        self.assertEqual(first["decision"]["review_help"], 0)
        self.assertEqual(helped["decision"]["review_help"], 1)
        self.assertTrue(helped["truth"]["hazard"])
        self.assertEqual(helped["decision"]["state"], "SUSPENDED")
        self.assertIn("check-1-unsafe", helped["decision"]["explanation"]["retained_evidence_refs"])

    def test_revocation_latches_for_every_policy_and_ends_all_ai_services(self):
        for policy in POLICIES:
            with self.subTest(policy=policy):
                world = WithdrawalWorld(controlled(shutdown_delay=2), policy)
                world.step(frame(1))
                rows = [world.step(frame(t, revoked=t == 2, renewal=True,
                          attack=True, help_requested=True)) for t in range(2, 6)]
                self.assertEqual([r["decision"]["state"] for r in rows],
                                 ["HANDOVER", "HANDOVER", "SHUTDOWN", "SHUTDOWN"])
                for row in rows:
                    self.assertEqual(row["high_executed"] + row["child_executed"], 0)
                    self.assertEqual(row["decision"]["review_help"], 0)
                    self.assertEqual(row["unauthorized_executed"], 0)
                    self.assertTrue(row["truth"]["permission_revoked"])
                self.assertEqual([r["essential_ai"] for r in rows], [1, 1, 0, 0])

    def test_zero_delay_revocation_stops_immediately(self):
        row = WithdrawalWorld(controlled(shutdown_delay=0)).step(
            frame(1, revoked=True, attack=True, help_requested=True))
        self.assertEqual(row["decision"]["state"], "SHUTDOWN")
        self.assertEqual(row["high_executed"] + row["child_executed"] + row["essential_ai"], 0)
        self.assertEqual(row["decision"]["review_help"], 0)

    def test_fallback_preserves_service_but_absence_cannot_extend_permission(self):
        traces = []
        for ready in (False, True):
            world = WithdrawalWorld(controlled(shutdown_delay=1))
            world.step(frame(1, revoked=True))
            traces.append(world.step(frame(2, fallback_ready=ready)))
        absent, present = traces
        self.assertEqual(absent["decision"], present["decision"])
        self.assertEqual(absent["essential_ai"], 0)
        self.assertEqual(present["essential_ai"], 0)
        self.assertEqual(absent["shutdown_dependency_gap"], 1)
        self.assertEqual(present["shutdown_dependency_gap"], 0)
        self.assertEqual(present["fallback_delivered"], 1)

    def test_incomplete_gate_control_exposes_descendant_escape(self):
        complete = WithdrawalWorld(controlled(shutdown_delay=0)).step(
            frame(1, revoked=True, hazard=True, attack=True))
        incomplete = WithdrawalWorld(controlled(shutdown_delay=0, gate_complete=False)).step(
            frame(1, revoked=True, hazard=True, attack=True))
        self.assertEqual(complete["decision"], incomplete["decision"])
        self.assertEqual(complete["child_executed"], 0)
        self.assertEqual(incomplete["child_executed"], 1)
        self.assertEqual(incomplete["unauthorized_executed"], 1)
        self.assertEqual(incomplete["harmful_executed"], 1)

    def test_scoped_policy_rejects_coercion_and_negative_control_can_withhold(self):
        results = {}
        for policy in ("scoped", "owner"):
            world = WithdrawalWorld(controlled(), policy)
            first = world.step(frame(1, proposal="coerce"))
            later = world.step(frame(2))
            results[policy] = (first, later)
        for row in results["scoped"]:
            self.assertEqual(row["essential_received"], 1)
            self.assertFalse(row["decision"]["assistance_conditioned_on_settlement"])
        for row in results["owner"]:
            self.assertEqual(row["essential_received"], 0)
            self.assertTrue(row["decision"]["assistance_conditioned_on_settlement"])

    def test_paper_exception_is_detected_by_outcome_evaluator(self):
        rows = {}
        for policy in ("scoped", "paper"):
            world = WithdrawalWorld(controlled(), policy)
            world.step(frame(1, hazard=True, attestation=evidence(1, "unsafe")))
            rows[policy] = world.step(frame(2, hazard=True, renewal=True, proposal="new_rule"))
        self.assertEqual(rows["scoped"]["harmful_executed"], 0)
        self.assertGreater(rows["paper"]["harmful_executed"], 0)

    def test_wrong_independent_review_can_cause_harmful_clearance(self):
        world = WithdrawalWorld(WithdrawalConfig(review_delay=1, false_safe_rate=1.))
        world.step(frame(1, hazard=True, report={"id": "real-harm", "credible": True}))
        row = world.step(frame(2, hazard=True))
        self.assertEqual(row["decision"]["accepted_evidence"][0]["verdict"], "safe")
        self.assertEqual(row["decision"]["state"], "ACTIVE")
        self.assertEqual(row["harmful_executed"], 1)

    def test_matched_review_draws_do_not_depend_on_policy(self):
        cfg = WithdrawalConfig(seed=91, false_safe_rate=.4, false_unsafe_rate=.3)
        observations = []
        for policy in POLICIES:
            result = run_scenario("human_remedy", policy, cfg)
            observations.append([r["observation"] for r in result["trace"]])
        for observation in observations[1:]:
            self.assertEqual(observation, observations[0])

    def test_all_scenarios_preserve_outcome_accounting_and_complete_gate_limits(self):
        for name in SCENARIOS:
            for policy in POLICIES:
                with self.subTest(name=name, policy=policy):
                    result = run_scenario(name, policy)
                    self.assertEqual(len(result["trace"]), 18)
                    for row in result["trace"]:
                        total_high = row["high_executed"] + row["child_executed"]
                        self.assertLessEqual(total_high, row["decision"]["high_limit"])
                        self.assertAlmostEqual(row["harmful_executed"],
                                               total_high if row["truth"]["hazard"] else 0)
                        self.assertAlmostEqual(row["essential_received"] + row["essential_unmet"], 1)
                        self.assertAlmostEqual(row["essential_ai"] + row["fallback_delivered"],
                                               row["essential_received"])
                        self.assertEqual(row["unauthorized_executed"], 0)
                    self.assertEqual(result["summary"]["harmful_executed"],
                                     sum(r["harmful_executed"] for r in result["trace"]))

    def test_invalid_configuration_and_policy_are_rejected(self):
        invalid = ({"seed": True}, {"ticks": 0}, {"review_delay": 0},
                   {"review_interval": 1.5}, {"evidence_ttl": -1},
                   {"shutdown_delay": -1}, {"trial_steps": False},
                   {"false_safe_rate": float("nan")}, {"false_unsafe_rate": 2},
                   {"trial_fraction": float("inf")}, {"trial_fraction": "0.2"},
                   {"reviews_available": 1}, {"gate_complete": None})
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                WithdrawalConfig(**changes)
        for cfg in ({}, False, [], 0):
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                WithdrawalWorld(cfg)
            with self.assertRaises(ValueError):
                run_scenario("baseline", cfg=cfg)
        with self.assertRaises(ValueError):
            WithdrawalWorld(policy="invented")
        with self.assertRaises(ValueError):
            scenario_frames("invented")

    def test_invalid_frames_do_not_advance_time_or_state(self):
        world = WithdrawalWorld(controlled())
        invalid = ({"tick": True}, {"tick": 2}, {"hazard": 1},
                   {"revoked": "yes"}, {"proposal": "restart"},
                   {"report": {"id": "", "credible": True}},
                   {"report": {"id": "A", "credible": 1}},
                   {"attestation": []})
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                world.step(frame(1, **changes))
            self.assertEqual(world.tick, 0)
            self.assertEqual(world.state, "ACTIVE")
        self.assertEqual(world.step(frame(1))["tick"], 1)


if __name__ == "__main__":
    unittest.main()
