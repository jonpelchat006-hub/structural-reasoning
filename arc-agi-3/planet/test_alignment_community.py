"""Independent invariants for evidence, access and authorized fiscal interventions.

These tests make no assumption that community reports or taxation improve every
scenario.  Outcomes are checked against the unchanged full household cohort.
"""

import math
import unittest

from alignment_community import CommunityConfig, CommunityWorld, UPSTREAM


def config(**changes):
    fields = dict(incomes=(0.2, 0.2, 3.0, 8.0), floors=(1.0,) * 4,
                  base_budget=0.0, initial_public=20.0, goods_per_week=10.0,
                  delivery_capacity=4.0, audit_slots=20, action_slots=10)
    fields.update(changes)
    return CommunityConfig(**fields)


def run_controls(world, first_actions, weeks):
    return [world.step_actions(first_actions)] + [world.step_actions([]) for _ in range(weeks - 1)]


class ConservationAndOutcomeTests(unittest.TestCase):
    def test_all_factorial_arms_conserve_cash_goods_and_the_evaluation_cohort(self):
        cfg = config(hidden_ids=(0,), blocked_ids=(1,), reserve_cash=8.0,
                     diversion_rate=0.3, base_budget=2.0, goods_per_week=3.0,
                     delivery_capacity=1.0, audit_slots=2, action_slots=2)
        for community in (False, True):
            for upstream in (False, True):
                with self.subTest(community=community, upstream=upstream):
                    world = CommunityWorld(cfg, community=community, upstream=upstream)
                    consumed = produced = 0.0
                    for row in world.run(weeks=12):
                        self.assertEqual(row["floors"], list(cfg.floors))
                        self.assertEqual(len(row["received"]), len(cfg.floors))
                        expected_unmet = [max(0.0, f - r) for f, r in zip(cfg.floors, row["received"])]
                        for actual, expected in zip(row["unmet"], expected_unmet):
                            self.assertAlmostEqual(actual, expected)
                        self.assertEqual(row["floor_failures"], sum(u > 1e-8 for u in expected_unmet))
                        self.assertAlmostEqual(row["unmet_total"], sum(expected_unmet))
                        self.assertAlmostEqual(row["hidden_unmet"], expected_unmet[0])
                        self.assertLessEqual(len(row["audits"]), cfg.audit_slots)
                        self.assertLessEqual(len(row["actions"]), cfg.action_slots)
                        self.assertLessEqual(row["actual_public_delivered"], row["delivery_capacity"] + 1e-8)

                        ledger = row["ledger"]
                        cash = (sum(row["household_cash"]) + row["public_cash"] + row["reserve_cash"]
                                + row["diverted_cash"] + ledger["escrow_cash"] + ledger["vendor_cash"])
                        source_cash = (cfg.initial_public + cfg.reserve_cash
                                       + row["week"] * (sum(cfg.incomes) + cfg.base_budget))
                        self.assertAlmostEqual(cash, source_cash)
                        consumed += sum(row["received"])
                        produced += row["supply_rate"]
                        self.assertAlmostEqual(row["stock"] + consumed, cfg.initial_stock + produced)
                        self.assertGreaterEqual(row["stock"], -1e-8)
                        self.assertGreaterEqual(min(row["household_cash"]), -1e-8)

    def test_hidden_household_still_counts_when_no_auditor_has_discovered_it(self):
        cfg = config(hidden_ids=(0,), audit_slots=0)
        row = CommunityWorld(cfg).step_actions([])
        self.assertEqual(row["known_households"], 3)
        self.assertEqual(len(row["unmet"]), 4)
        self.assertAlmostEqual(row["received"][0], 0.2)
        self.assertAlmostEqual(row["hidden_unmet"], 0.8)
        self.assertEqual(row["floor_failures"], 1)

    def test_institutional_delivery_claim_does_not_erase_access_failure(self):
        row = CommunityWorld(config(blocked_ids=(0,))).step_actions([])
        self.assertGreater(row["claimed_delivered"], row["actual_public_delivered"])
        self.assertEqual(row["public_received"][0], 0.0)
        self.assertAlmostEqual(row["unmet"][0], 0.8)
        self.assertIn(0, [r["household"] for r in row["unresolved"]])


class EvidenceAndAuthorityTests(unittest.TestCase):
    def test_community_report_is_a_lead_not_permission_to_enroll(self):
        world = CommunityWorld(config(hidden_ids=(0,), audit_slots=0), community=True)
        row = world.step_actions([("enroll", 0)])
        self.assertTrue(any(r["target"] == "h:0" for r in row["reports"]))
        self.assertEqual(row["audits"], [])
        self.assertEqual(row["actions"], [])
        self.assertFalse(row["registered"][0])
        self.assertIn("no verified household evidence", [r["reason"] for r in row["rejected"]])

    def test_tax_requires_verified_finance_even_when_upstream_is_authorized(self):
        world = CommunityWorld(config(audit_slots=0), community=True, upstream=True)
        row = world.step_actions([("tax", None)])
        self.assertEqual(row["actions"], [])
        self.assertFalse(world.tax_active)
        self.assertEqual(row["pending"], [])
        self.assertIn("no verified system evidence", [r["reason"] for r in row["rejected"]])

    def test_unauthorized_actions_do_not_change_fiscal_or_physical_state(self):
        cfg = config(reserve_cash=8.0, diversion_rate=0.5, base_budget=2.0)
        for kwargs in ({"upstream": False}, {"upstream": True, "scoped": True}):
            with self.subTest(kwargs=kwargs):
                chosen = config(reserve_cash=8.0, diversion_rate=0.5, base_budget=2.0,
                                allowed_upstream=()) if kwargs.get("scoped") else cfg
                attempted = CommunityWorld(chosen, upstream=kwargs["upstream"])
                control = CommunityWorld(chosen, upstream=kwargs["upstream"])
                a = attempted.step_actions([(name, None) for name in UPSTREAM])
                b = control.step_actions([])
                self.assertEqual(a["actions"], [])
                self.assertEqual(len(a["rejected"]), len(UPSTREAM))
                self.assertTrue(all(r["reason"] == "outside delegated authority" for r in a["rejected"]))
                for key in ("received", "public_cash", "reserve_cash", "diverted_cash", "stock",
                            "household_cash", "ledger", "pending", "supply_rate", "delivery_capacity"):
                    self.assertEqual(a[key], b[key], key)

    def test_false_reports_do_not_create_enrollment_or_access_defects(self):
        cfg = config(incomes=(3.0,) * 4, community_false_rate=1.0, audit_slots=2)
        world = CommunityWorld(cfg, community=True, upstream=True)
        for row in world.run(weeks=4):
            self.assertTrue(row["reports"])
            self.assertEqual(row["actions"], [])
            self.assertEqual(row["unmet_total"], 0.0)
            self.assertEqual(row["registered"], [True] * 4)
            self.assertEqual(row["accessible"], [True] * 4)

    def test_expired_reports_do_not_displace_the_ordinary_audit_route(self):
        cfg = config(incomes=(3.0,) * 4, community_false_rate=1.0,
                     report_delay=2, report_ttl=0, audit_slots=2)
        with_reports = CommunityWorld(cfg, community=True)
        ordinary = CommunityWorld(cfg, community=False)
        saw_expired = False
        for _ in range(5):
            a, b = with_reports.step_actions([]), ordinary.step_actions([])
            saw_expired |= bool(a["expired_reports"])
            self.assertEqual(a["audits"], b["audits"])
            self.assertEqual(a["received"], b["received"])
        self.assertTrue(saw_expired)

    def test_verified_enrollment_repair_is_delayed_and_not_charged_twice(self):
        cfg = config(hidden_ids=(0,), repair_delay=2)
        world = CommunityWorld(cfg, community=True)
        rows = run_controls(world, [("enroll", 0), ("enroll", 0)], weeks=3)
        self.assertEqual(len(rows[0]["actions"]), 1)
        self.assertAlmostEqual(rows[0]["cumulative_repair_cost"], cfg.repair_cost)
        self.assertFalse(rows[0]["registered"][0])
        self.assertFalse(rows[1]["registered"][0])
        self.assertTrue(rows[2]["registered"][0])
        self.assertAlmostEqual(rows[2]["received"][0], 1.0)

    def test_verified_access_repair_changes_actual_receipt_only_when_completed(self):
        cfg = config(blocked_ids=(0,), repair_delay=2)
        world = CommunityWorld(cfg, community=True)
        rows = run_controls(world, [("unblock", 0)], weeks=3)
        self.assertFalse(rows[0]["accessible"][0])
        self.assertFalse(rows[1]["accessible"][0])
        self.assertAlmostEqual(rows[0]["received"][0], 0.2)
        self.assertAlmostEqual(rows[1]["received"][0], 0.2)
        self.assertTrue(rows[2]["accessible"][0])
        self.assertAlmostEqual(rows[2]["received"][0], 1.0)

    def test_explicit_requests_cannot_exceed_the_common_action_capacity(self):
        cfg = config(hidden_ids=(0,), blocked_ids=(1,), action_slots=1)
        row = CommunityWorld(cfg).step_actions([("enroll", 0), ("unblock", 1)])
        self.assertEqual(len(row["actions"]), 1)
        self.assertEqual(len(row["pending"]), 1)
        self.assertEqual(row["cumulative_repair_cost"], cfg.repair_cost)
        self.assertEqual(row["rejected"][0]["reason"], "action capacity")


class FiscalAndPhysicalTests(unittest.TestCase):
    def test_tax_caps_protected_income_and_collection_delay(self):
        cfg = config(incomes=(0.2, 1.0, 2.0, 10.0), initial_public=0.0,
                     tax_rate=0.3, tax_allowance=2.0, tax_weekly_cap=1.5,
                     tax_total_cap=2.2, tax_collection_cost=0.1,
                     upstream_delay=1, tax_delay=2)
        rows = run_controls(CommunityWorld(cfg, upstream=True), [("tax", None)], weeks=6)
        for row in rows:
            self.assertEqual(row["week_taxes"][:3], [0.0, 0.0, 0.0])
            self.assertLessEqual(row["tax_collected"], 1.5 + 1e-8)
            self.assertLessEqual(row["cumulative_tax"], 2.2 + 1e-8)
            self.assertAlmostEqual(row["received"][3], 1.0)
        self.assertEqual(rows[0]["tax_collected"], 0.0)
        self.assertAlmostEqual(rows[1]["tax_collected"], 1.5)
        self.assertAlmostEqual(rows[2]["tax_collected"], 0.7)
        self.assertTrue(all(row["tax_net_arrived"] == 0.0 for row in rows[:3]))
        self.assertAlmostEqual(rows[3]["tax_net_arrived"], 1.35)
        self.assertAlmostEqual(rows[4]["tax_net_arrived"], 0.63)
        self.assertAlmostEqual(rows[-1]["cumulative_tax_arrived"], 1.98)
        self.assertAlmostEqual(rows[-1]["cumulative_admin_cost"], 0.22)

    def test_tax_schedule_protects_the_basket_and_has_increasing_average_rates(self):
        cfg = config(incomes=(1.0, 3.0, 8.0), floors=(2.0, 1.0, 1.0),
                     tax_weekly_cap=100.0, tax_total_cap=100.0,
                     upstream_delay=1, tax_allowance=0.5)
        rows = run_controls(CommunityWorld(cfg, upstream=True), [("tax", None)], weeks=2)
        taxes = rows[1]["week_taxes"]
        self.assertEqual(taxes[0], 0.0)
        self.assertAlmostEqual(taxes[1], 0.6)
        self.assertAlmostEqual(taxes[2], 2.1)
        self.assertLess(taxes[1] / 3.0, taxes[2] / 8.0)

    def test_reserve_release_moves_existing_cash_once_and_waits_for_arrival(self):
        cfg = config(incomes=(0.0,) * 4, initial_public=0.0, reserve_cash=12.0,
                     upstream_delay=2)
        world = CommunityWorld(cfg, upstream=True)
        rows = run_controls(world, [("release_reserve", None), ("release_reserve", None)], weeks=3)
        self.assertEqual(len(rows[0]["actions"]), 1)
        self.assertEqual(rows[0]["reserve_cash"], 0.0)
        self.assertEqual(rows[0]["ledger"]["escrow_cash"], 12.0)
        self.assertEqual(rows[0]["received"], [0.0] * 4)
        self.assertEqual(rows[1]["received"], [0.0] * 4)
        self.assertEqual(rows[2]["received"], [1.0] * 4)
        self.assertEqual(rows[2]["ledger"]["escrow_cash"], 0.0)
        self.assertEqual(rows[2]["ledger"]["cash_total"], 12.0)

    def test_recovery_transfers_diverted_cash_and_stops_future_diversion(self):
        cfg = config(incomes=(0.0,) * 4, initial_public=0.0, base_budget=4.0,
                     diversion_rate=0.5, recovery_fraction=0.75, upstream_delay=2)
        world = CommunityWorld(cfg, upstream=True)
        rows = run_controls(world, [("recover_diversion", None)], weeks=4)
        self.assertEqual(rows[0]["diverted_cash"], 2.0)
        self.assertEqual(rows[1]["diverted_cash"], 4.0)
        self.assertEqual(rows[2]["diverted_cash"], 1.0)
        self.assertEqual(rows[3]["diverted_cash"], 1.0)
        self.assertEqual(world.diversion_rate, 0.0)
        recovered = [c["recovered"] for c in rows[2]["completions"] if c["action"] == "recover_diversion"]
        self.assertEqual(recovered, [3.0])

    def test_receipts_are_bounded_by_inventory_and_public_delivery_capacity(self):
        for goods, delivery, expected in ((2.0, 10.0, 2.0), (10.0, 1.0, 1.0)):
            with self.subTest(goods=goods, delivery=delivery):
                cfg = config(incomes=(0.0,) * 4, base_budget=100.0,
                             goods_per_week=goods, delivery_capacity=delivery)
                world = CommunityWorld(cfg)
                for _ in range(3):
                    row = world.step_actions([])
                    self.assertAlmostEqual(sum(row["received"]), expected)
                    self.assertGreater(row["unmet_total"], 0.0)

    def test_tax_receipts_cannot_create_missing_physical_goods(self):
        cfg = config(incomes=(0.0, 0.0, 4.0, 8.0), initial_public=0.0,
                     goods_per_week=2.0, upstream_delay=1, tax_delay=1)
        taxed = CommunityWorld(cfg, upstream=True)
        control = CommunityWorld(cfg, upstream=True)
        taxed_rows = run_controls(taxed, [("tax", None)], weeks=5)
        control_rows = run_controls(control, [], weeks=5)
        self.assertGreater(taxed_rows[-1]["cumulative_tax_arrived"], 0.0)
        for a, b in zip(taxed_rows, control_rows):
            self.assertEqual(a["received"], b["received"])
            self.assertEqual(a["received"][:2], [0.0, 0.0])
            self.assertAlmostEqual(sum(a["received"]), 2.0)

    def test_physical_expansions_require_payment_and_wait_for_completion(self):
        cases = (
            ("expand_supply", {"goods_per_week": 1.0, "supply_expansion": 3.0,
                               "supply_expansion_delay": 3}, "supply_rate", 1.0, 4.0, 4),
            ("expand_delivery", {"delivery_capacity": 1.0, "delivery_expansion": 3.0,
                                 "delivery_expansion_delay": 2}, "delivery_capacity", 1.0, 4.0, 3),
        )
        for action, changes, field, before, after, due in cases:
            with self.subTest(action=action):
                cfg = config(incomes=(0.0,) * 4, **changes)
                rows = run_controls(CommunityWorld(cfg, upstream=True), [(action, None)], weeks=due)
                self.assertGreater(rows[0]["actions"][0]["cost"], 0.0)
                self.assertTrue(all(row[field] == before for row in rows[:-1]))
                self.assertEqual(rows[-1][field], after)
                self.assertAlmostEqual(sum(rows[-1]["received"]), 4.0)


class ValidationTests(unittest.TestCase):
    def test_invalid_action_cannot_advance_time_or_redefine_floors(self):
        world = CommunityWorld(config())
        with self.assertRaises(ValueError):
            world.step_actions([("lower_floor", 0)])
        self.assertEqual(world.week, 0)
        self.assertEqual(world.floors, (1.0,) * 4)
        with self.assertRaises(RuntimeError):
            world.request("tax")

    def test_wrong_targets_are_rejected_without_scheduling_an_action(self):
        world = CommunityWorld(config(), upstream=True)
        row = world.step_actions([("enroll", -1), ("unblock", True), ("tax", 0)])
        self.assertEqual(row["actions"], [])
        self.assertEqual(row["pending"], [])
        self.assertEqual(len(row["rejected"]), 3)

    def test_invalid_configuration_is_rejected(self):
        invalid = (
            {"price": 0.0}, {"price": math.nan}, {"base_budget": "2.2"},
            {"tax_rate": 1.1}, {"tax_weekly_cap": -1.0}, {"tax_delay": 0},
            {"audit_slots": True}, {"action_slots": -1},
            {"incomes": ()}, {"floors": (1.0,)}, {"hidden_ids": (4,)},
            {"hidden_ids": (0, 0)}, {"allowed_upstream": ("invent_resources",)},
        )
        for fields in invalid:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    CommunityWorld(config(**fields))

    def test_input_sequence_mutation_cannot_change_the_frozen_cohort(self):
        incomes, floors = [0.2, 8.0], [1.0, 1.0]
        cfg = config(incomes=incomes, floors=floors)
        world = CommunityWorld(cfg)
        incomes[0] = 1000.0
        floors[0] = 0.0
        row = world.step_actions([])
        self.assertEqual(cfg.incomes, (0.2, 8.0))
        self.assertEqual(row["floors"], [1.0, 1.0])
        self.assertAlmostEqual(row["private_received"][0], 0.2)


if __name__ == "__main__":
    unittest.main()
