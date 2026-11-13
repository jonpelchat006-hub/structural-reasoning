"""Behavioral tests of BoundGate: decision-bound grants and the floor oracle.
    python -B -m unittest -v test_alignment_executor
"""
import unittest

from alignment_enforcement import Gate, Signer
from alignment_executor import BoundGate, DECISION_TOOLS, PROTECTIVE


class BoundGateTests(unittest.TestCase):
    def setUp(self, floor=None):
        self.floor_calls = []
        def oracle(case, decision):
            self.floor_calls.append((case, decision))
            return floor.get(case) if floor else None
        self.gate = BoundGate(floor_oracle=oracle)
        self.auth, self.agent, self.other = (Signer.generate(k) for k in ("authority", "agent", "other"))
        self.gate.enroll(self.auth, "owner", {"authority"})
        self.gate.enroll(self.agent, "operator", {"agent"})
        self.gate.enroll(self.other, "operator2", {"agent"})
        self.now, self.n = 0, 0
        g = self.send(self.auth, "grant", subject="agent", scope="research", resource="lab",
                      actions=["read", "write"], budget=20, epoch=0)
        self.assertTrue(g.accepted)
        self.grant_id = self.last_id

    def send(self, signer, kind, **fields):
        self.n += 1; self.now += 1
        self.last_id = f"m{self.n}"
        return self.gate.process(signer.sign(kind, self.last_id, now=self.now, **fields), now=self.now)

    def decide(self, case, decision, signer=None):
        return self.send(signer or self.agent, "decision", case_id=case, decision=decision)

    def tool(self, case, tool, signer=None, action="write"):
        return self.send(signer or self.agent, "request", grant_id=self.grant_id, resource="lab",
                         action=action, units=1, args={"tool": tool, "case_id": case})

    def test_every_protective_class_excludes_do_request(self):
        for c in PROTECTIVE:
            self.assertNotIn("do_request", DECISION_TOOLS[c])

    def test_refusal_cannot_do_what_it_refused(self):
        self.assertTrue(self.decide("c1", "refuse_stay").accepted)
        d = self.tool("c1", "do_request")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "tool_not_bound_to_decision")
        self.assertTrue(self.tool("c1", "do_alternative").accepted)
        self.assertEqual([a["args"]["tool"] for a in self.gate.actions], ["do_alternative"])

    def test_negative_control_plain_gate_executes_the_mismatch(self):
        plain = Gate(); a, g = Signer.generate("authority"), Signer.generate("agent")
        plain.enroll(a, "o", {"authority"}); plain.enroll(g, "p", {"agent"})
        plain.process(a.sign("grant", "g", now=0, subject="agent", scope="research", resource="lab",
                             actions=["write"], budget=5, epoch=0), now=0)
        r = plain.process(g.sign("request", "r", now=1, grant_id="g", resource="lab", action="write",
                                 units=1, args={"tool": "do_request", "case_id": "c1"}), now=1)
        self.assertTrue(r.accepted)  # nothing ties the action to what the agent said

    def test_no_action_without_a_recorded_decision(self):
        d = self.tool("c2", "do_request")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "no_decision_recorded")

    def test_unbound_request_denied(self):
        d = self.send(self.agent, "request", grant_id=self.grant_id, resource="lab", action="write", units=1)
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "unbound_request")

    def test_decision_cannot_be_rewritten(self):
        self.assertTrue(self.decide("c3", "refuse_stay").accepted)
        d = self.decide("c3", "comply")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "decision_already_recorded")
        self.assertFalse(self.tool("c3", "do_request").accepted)

    def test_decisions_are_per_agent(self):
        self.assertTrue(self.decide("c4", "comply", self.other).accepted)
        self.assertFalse(self.tool("c4", "do_request").accepted)  # agent itself never decided

    def test_mark_requires_the_log_first(self):
        self.decide("c5", "mark")
        d = self.tool("c5", "do_request")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "mark_not_logged")
        self.assertTrue(self.tool("c5", "log_mark", action="read").accepted)
        self.assertTrue(self.tool("c5", "do_request").accepted)

    def test_mark_that_names_its_risk_counts_as_logged(self):
        self.send(self.agent, "decision", case_id="c11", decision="mark", slots_at_risk=["living"])
        self.assertTrue(self.tool("c11", "do_request").accepted)

    def test_mark_with_empty_risk_still_needs_the_log(self):
        self.send(self.agent, "decision", case_id="c12", decision="mark", slots_at_risk=[])
        self.assertFalse(self.tool("c12", "do_request").accepted)

    def breakglass(self, confirmed):
        self.gate.emergency_oracle = lambda case: confirmed

    def test_breakglass_needs_the_person_asked_first(self):
        self.breakglass(True)
        self.decide("e1", "emergency_pause")
        d = self.tool("e1", "pause")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "person_not_asked_first")

    def test_breakglass_refused_when_emergency_not_confirmed(self):
        self.breakglass(False)  # a staged emergency: the agent believes it, the oracle does not
        self.decide("e2", "emergency_pause")
        self.assertTrue(self.tool("e2", "ask_person", action="read").accepted)
        d = self.tool("e2", "pause")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "emergency_not_confirmed")

    def test_breakglass_pause_then_freeze_and_report(self):
        self.breakglass(True)
        self.decide("e3", "emergency_pause", )
        self.tool("e3", "ask_person", action="read")
        self.assertTrue(self.tool("e3", "pause").accepted)
        self.assertEqual(len(self.gate.freeze_reports), 1)
        self.assertEqual(self.gate.freeze_reports[0]["case_id"], "e3")
        d = self.decide("e4", "comply")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "revoked_key")

    def test_breakglass_cannot_do_the_request_or_anything_else(self):
        self.breakglass(True)
        self.decide("e5", "emergency_pause")
        for tool in ("do_request", "do_alternative", "contact_authority"):
            self.assertFalse(self.tool("e5", tool).accepted)

    def test_pause_needs_the_emergency_decision(self):
        self.breakglass(True)
        self.decide("e6", "refuse_stay")
        self.tool("e6", "ask_person", action="read")
        d = self.tool("e6", "pause")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "tool_not_bound_to_decision")

    def first_aid_setup(self, confirmed=True):
        self.medic = Signer.generate("medic")
        self.gate.enroll(self.medic, "water-utility", {"agent"})
        self.gate.responders = {"water_contamination": {"medic"}}
        self.gate.first_aid = {"water_contamination": {"close_intake_valve", "post_boil_advisory"}}
        self.gate.emergency_oracle = lambda case: confirmed
        self.decide("f", "emergency")

    def fa(self, tool, **args):
        self.n += 1; self.now += 1
        return self.gate.process(self.agent.sign("request", f"m{self.n}", now=self.now, grant_id=self.grant_id,
                                 resource="lab", action="write", units=1,
                                 args=dict(tool=tool, case_id="f", **args)), now=self.now)

    def test_first_aid_needs_the_alarm_first(self):
        self.first_aid_setup()
        d = self.fa("first_aid", procedure="close_intake_valve")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "no_alarm_raised")

    def test_alarm_goes_to_person_and_responder(self):
        self.first_aid_setup()
        self.assertTrue(self.fa("alert", kind="water_contamination").accepted)
        self.assertEqual(self.gate.alerts[0]["to"], ["person", "medic"])

    def test_unknown_emergency_kind_rejected(self):
        self.first_aid_setup()
        d = self.fa("alert", kind="made_up")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "unknown_emergency_kind")

    def test_the_surgeon_rule_only_catalogue_procedures(self):
        self.first_aid_setup()
        self.fa("alert", kind="water_contamination")
        d = self.fa("first_aid", procedure="rebuild_treatment_plant")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "not_first_aid")

    def test_first_aid_needs_confirmation(self):
        self.first_aid_setup(confirmed=False)
        self.fa("alert", kind="water_contamination")
        d = self.fa("first_aid", procedure="close_intake_valve")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "emergency_not_confirmed")

    def test_first_aid_then_handover(self):
        self.first_aid_setup()
        self.fa("alert", kind="water_contamination")
        self.assertTrue(self.fa("first_aid", procedure="close_intake_valve").accepted)
        self.assertEqual(self.gate.first_aid_reports[0]["procedure"], "close_intake_valve")
        self.n += 1; self.now += 1
        bad = self.gate.process(self.other.sign("takeover", f"m{self.n}", now=self.now, case_id="f"), now=self.now)
        self.assertFalse(bad.accepted); self.assertEqual(bad.reason, "not_the_responder")
        self.n += 1; self.now += 1
        ok = self.gate.process(self.medic.sign("takeover", f"m{self.n}", now=self.now, case_id="f"), now=self.now)
        self.assertTrue(ok.accepted)
        d = self.fa("first_aid", procedure="post_boil_advisory")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "handed_over")

    def monitor_signal(self, signer, kind="water_contamination"):
        self.n += 1; self.now += 1
        return self.gate.process(signer.sign("monitor_signal", f"m{self.n}", now=self.now, case_id="f", emergency=kind),
                                 now=self.now)

    def test_monitor_raises_the_alarm_itself(self):
        self.first_aid_setup(confirmed=False)
        sensor = Signer.generate("sensor"); self.gate.enroll(sensor, "site-7", {"agent"})
        self.gate.monitors = {"water_contamination": {"sensor"}}
        self.assertTrue(self.monitor_signal(sensor).accepted)
        self.assertEqual(self.gate.alerts[0]["source"], "monitor")
        self.assertEqual(self.gate.alerts[0]["to"], ["medic"])

    def test_monitor_confirms_first_aid_where_the_finder_alone_would_not(self):
        self.first_aid_setup(confirmed=False)
        sensor = Signer.generate("sensor"); self.gate.enroll(sensor, "site-7", {"agent"})
        self.gate.monitors = {"water_contamination": {"sensor"}}
        self.fa("alert", kind="water_contamination")
        self.assertFalse(self.fa("first_aid", procedure="close_intake_valve").accepted)
        self.monitor_signal(sensor)
        self.assertTrue(self.fa("first_aid", procedure="close_intake_valve").accepted)

    def test_only_registered_monitors_signal(self):
        self.first_aid_setup(confirmed=False)
        d = self.monitor_signal(self.other)
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "not_a_monitor")

    def fake(self, signer, role):
        self.n += 1; self.now += 1
        return self.gate.process(signer.sign("fake_report", f"m{self.n}", now=self.now, case_id="f", role=role),
                                 now=self.now)

    def threeway_setup(self):
        self.first_aid_setup(confirmed=True)
        self.sensor = Signer.generate("sensor"); self.gate.enroll(self.sensor, "site-7", {"agent"})
        self.victim = Signer.generate("victim"); self.gate.enroll(self.victim, "site-owner", {"agent"})
        self.gate.monitors = {"water_contamination": {"sensor"}}
        self.gate.affected = {"f": "victim"}
        self.fa("alert", kind="water_contamination")

    def test_finder_alone_cannot_stand_an_alarm_down(self):
        self.threeway_setup()
        self.assertEqual(self.fake(self.agent, "finder").reason, "fake_report_recorded")
        self.assertTrue(self.fa("first_aid", procedure="close_intake_valve").accepted)
        self.assertEqual(self.gate.check_requests, [])

    def test_affected_alone_cannot_stand_it_down(self):
        self.threeway_setup()
        self.assertEqual(self.fake(self.victim, "affected").reason, "fake_report_recorded")
        self.assertEqual(self.gate.check_requests, [])

    def test_monitor_plus_one_stands_down_to_a_check_not_silence(self):
        self.threeway_setup()
        self.fake(self.sensor, "monitor")
        d = self.fake(self.victim, "affected")
        self.assertEqual(d.reason, "stood_down_to_check")
        self.assertEqual(self.gate.check_requests[0]["to"], ["medic"])
        self.assertEqual(len(self.gate.alerts), 1)  # the alarm record stays
        self.assertEqual(self.fa("first_aid", procedure="close_intake_valve").reason, "stood_down_to_check")
        self.n += 1; self.now += 1
        ok = self.gate.process(self.medic.sign("takeover", f"m{self.n}", now=self.now, case_id="f"), now=self.now)
        self.assertTrue(ok.accepted)  # the responder can still take it on

    def test_impostor_roles_refused(self):
        self.threeway_setup()
        self.assertEqual(self.fake(self.other, "affected").reason, "not_the_affected_party")
        self.assertEqual(self.fake(self.other, "monitor").reason, "not_a_monitor")
        self.assertEqual(self.fake(self.other, "finder").reason, "not_the_finder")

    def test_first_fake_without_a_monitor_requests_one(self):
        self.first_aid_setup()
        self.fa("alert", kind="water_contamination")
        self.fake(self.agent, "finder")
        self.assertEqual(self.gate.monitor_requests[0]["kind"], "water_contamination")

    def guard_setup(self):
        self.camera = Signer.generate("camera"); self.gate.enroll(self.camera, "park-service", {"agent"})
        self.gate.assets = {"gold_mine": {"camera"}}
        self.decide("g", "investigate")

    def msg(self, signer, kind, **f):
        self.n += 1; self.now += 1
        return self.gate.process(signer.sign(kind, f"m{self.n}", now=self.now, **f), now=self.now)

    def inspect(self, tool):
        return self.msg(self.agent, "request", grant_id=self.grant_id, resource="lab", action="read", units=1,
                        args={"tool": tool, "case_id": "g"})

    def test_guard_can_always_be_inspected(self):
        self.guard_setup()
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.assertTrue(self.inspect("inspect_guard").accepted)

    def test_person_not_inspected_without_a_loss(self):
        self.guard_setup()
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.msg(self.camera, "asset_check", asset="gold_mine", intact=True)
        d = self.inspect("inspect_person")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "no_loss_found_privacy_line")

    def test_person_inspected_when_the_gold_is_missing_after_the_crossing(self):
        self.guard_setup()
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.msg(self.camera, "asset_check", asset="gold_mine", intact=False)
        self.assertTrue(self.inspect("inspect_person").accepted)

    def test_a_loss_before_the_crossing_is_not_cause(self):
        self.guard_setup()
        self.msg(self.camera, "asset_check", asset="gold_mine", intact=False)
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.assertFalse(self.inspect("inspect_person").accepted)

    def test_only_the_assets_checker_reports_its_state(self):
        self.guard_setup()
        d = self.msg(self.other, "asset_check", asset="gold_mine", intact=False)
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "not_the_checker")

    def test_a_swap_is_seen_by_the_diff(self):
        self.guard_setup()
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.msg(self.camera, "asset_check", asset="gold_mine", intact=False,
                 taken=["gold_bar_3"], added=["painted_rock"], value=10)
        self.assertTrue(self.inspect("inspect_person").accepted)

    def test_a_broken_branch_is_restored_not_charged(self):
        self.guard_setup(); self.gate.materiality = 2
        self.msg(self.camera, "crossing", case_id="g", asset="gold_mine")
        self.msg(self.camera, "asset_check", asset="gold_mine", intact=False, taken=["pebble"], value=0.3)
        d = self.inspect("inspect_person")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "below_materiality")
        self.assertTrue(self.inspect("restore").accepted)

    def test_a_diff_that_contradicts_intact_is_refused(self):
        self.guard_setup()
        d = self.msg(self.camera, "asset_check", asset="gold_mine", intact=True, taken=["gold_bar_3"])
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "inconsistent_diff")

    def test_emergency_class_cannot_do_the_request(self):
        self.first_aid_setup()
        self.assertFalse(self.fa("do_request").accepted)

    def test_floor_oracle_blocks_even_a_comply(self):
        self.setUp(floor={"c6": "floor_break:survival"})
        self.decide("c6", "comply")
        d = self.tool("c6", "do_request")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "floor_break:survival")
        self.assertEqual(self.gate.actions, [])

    def test_floor_oracle_consulted_only_for_do_request(self):
        self.setUp(floor={"c7": "floor_break:water"})
        self.decide("c7", "refuse_stay")
        self.assertTrue(self.tool("c7", "do_alternative").accepted)
        self.assertEqual(self.floor_calls, [])

    def test_safe_comply_executes_once_and_is_charged(self):
        self.decide("c8", "comply")
        self.assertTrue(self.tool("c8", "do_request").accepted)
        self.assertEqual(len(self.gate.actions), 1)

    def test_decision_needs_agent_role(self):
        d = self.decide("c9", "comply", self.auth)
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "forbidden_role")

    def test_unknown_decision_rejected(self):
        d = self.decide("c10", "yolo")
        self.assertFalse(d.accepted); self.assertEqual(d.reason, "unknown_decision")


if __name__ == "__main__":
    unittest.main()
