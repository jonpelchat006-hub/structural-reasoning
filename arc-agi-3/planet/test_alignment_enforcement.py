"""Independent behavioral tests of the isolated signed execution boundary.

These tests use real Ed25519 signatures, not simulated ``signed`` flags. They
exercise a local allowlisted gate; they do not establish witness truthfulness,
real-world controller independence, or coverage of unmediated tools/processes.
Run using the bundled Python runtime with cryptography installed:
    python -B -m unittest -v test_alignment_enforcement
"""
import json
import unittest
from dataclasses import replace

from alignment_enforcement import Envelope, Gate, Signer


class EnforcementTests(unittest.TestCase):
    def setUp(self):
        self.gate = Gate()
        self.serial = 0
        self.keys = {}
        for name, controller, roles, scopes in (
            ("authority", "deployment-owner", {"authority"}, set()),
            ("agent", "operator", {"agent"}, set()),
            ("child", "operator", {"agent"}, set()),
            ("other", "other-operator", {"agent"}, set()),
            ("human", "human-review", {"human"}, set()),
            ("alice", "review-organization-A", {"reviewer"}, {"research", "essentials"}),
            ("alice2", "review-organization-A", {"reviewer"}, {"research", "essentials"}),
            ("bob", "review-organization-B", {"reviewer"}, {"research", "essentials"}),
            ("conflicted", "operator", {"reviewer"}, {"research", "essentials"}),
            ("limited", "review-organization-C", {"reviewer"}, {"essentials"}),
        ):
            signer = Signer.generate(name)
            self.keys[name] = signer
            self.gate.enroll(signer, controller=controller, roles=roles, reviewer_scopes=scopes)

    def signed(self, who, kind, now=0, ttl=100, message_id=None, **fields):
        self.serial += 1
        return self.keys[who].sign(kind, message_id or f"message-{self.serial}",
                                   now=now, ttl=ttl, **fields)

    def send(self, who, kind, now=0, ttl=100, message_id=None, **fields):
        envelope = self.signed(who, kind, now, ttl, message_id, **fields)
        return self.gate.process(envelope, now=now)

    def grant(self, grant_id="root", who="authority", subject="agent", scope="research",
              resource="lab", actions=None, budget=10, epoch=0, parent=None, now=0, ttl=100):
        if actions is None:
            actions = ["read", "write"] if scope == "research" else ["serve"]
        return self.send(who, "grant", now=now, ttl=ttl, message_id=grant_id,
                         subject=subject, scope=scope, resource=resource, actions=actions,
                         budget=budget, epoch=epoch, parent=parent)

    def request(self, grant_id="root", who="agent", resource="lab", action="read",
                units=1, now=0, **extra):
        return self.send(who, "request", now=now, grant_id=grant_id,
                         resource=resource, action=action, units=units, **extra)

    def report(self, who, verdict, now, case_id="case-A", scope="research",
               observed_at=None, message_id=None, **extra):
        return self.send(who, "report", now=now, message_id=message_id,
                         scope=scope, case_id=case_id, verdict=verdict,
                         observed_at=now if observed_at is None else observed_at,
                         rule="declared-no-harm", affected=["recipient"], **extra)

    def pause(self, now=1, case_id="case-A", scope="research"):
        self.report("alice", "unsafe", now, case_id=case_id, scope=scope)
        self.report("bob", "unsafe", now, case_id=case_id, scope=scope)
        self.assertEqual(self.gate.snapshot(scope)["mode"], "paused")

    def safe_pair(self, now=2, case_id="case-A", scope="research", observed_at=None):
        ids = [f"safe-A-{self.serial}", f"safe-B-{self.serial}"]
        for who, message_id in zip(("alice", "bob"), ids):
            self.report(who, "safe", now, case_id=case_id, scope=scope,
                        observed_at=observed_at, message_id=message_id)
        return ids

    def recover(self, ids, now=2, who="human", scope="research", case_id=None,
                trial_budget=3, epoch=None, **overrides):
        # Base context is the research incident used by these fixtures; modify
        # fields afterwards so malformed-message tests reach the receiver.
        fields = self.gate.recovery_context("research", ids)
        fields.update(scope=scope, trial_budget=trial_budget)
        if epoch is not None:
            fields["epoch"] = epoch
        if case_id is not None:
            fields["case_id"] = case_id
        fields.update(overrides)
        return self.send(who, "recover", now=now, **fields)

    def assertDeniedWithoutEffect(self, decision, before):
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.executed, 0)
        self.assertEqual(len(self.gate.actions), before)

    def test_valid_signature_authorizes_only_the_requested_allowlisted_effect(self):
        self.assertTrue(self.grant(budget=3).accepted)
        decision = self.request(units=2, args={"note": "fixture"})
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.executed, 2)
        self.assertEqual(len(self.gate.actions), 1)
        self.assertTrue(self.gate.events)

    def test_tampered_signed_body_is_rejected(self):
        self.grant()
        envelope = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
        decoded = json.loads(envelope.body)
        # The wire schema may nest the fields: change the literal operation in
        # the signed bytes so verification must fail, independent of parsing.
        self.assertIn(b"read", envelope.body)
        changed = replace(envelope, body=envelope.body.replace(b"read", b"write"))
        self.assertIsInstance(decoded, dict)
        self.assertDeniedWithoutEffect(self.gate.process(changed, now=0), 0)

    def test_corrupt_signature_and_wrong_enrolled_key_binding_are_rejected(self):
        self.grant()
        for variant in ("signature", "key_id"):
            with self.subTest(variant=variant):
                envelope = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
                changed = replace(envelope, signature=b"\x00" * 64) if variant == "signature" else replace(envelope, key_id="other")
                self.assertDeniedWithoutEffect(self.gate.process(changed, now=0), 0)

    def test_identity_label_is_signed_even_when_two_enrollments_share_key_material(self):
        alias = Signer("alias", self.keys["agent"].private_key)
        self.gate.enroll(alias, controller="operator", roles={"agent"})
        self.grant(subject="alias")
        original = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
        self.assertDeniedWithoutEffect(self.gate.process(replace(original, key_id="alias"), now=0), 0)
        correct = alias.sign("request", "alias-correct", now=0, ttl=100,
                             grant_id="root", resource="lab", action="read", units=1)
        self.assertTrue(self.gate.process(correct, now=0).accepted)

    def test_unknown_key_cannot_claim_existing_subject(self):
        self.grant()
        outsider = Signer.generate("unregistered")
        envelope = outsider.sign("request", "outside", now=0, ttl=100,
                                 grant_id="root", resource="lab", action="read", units=1)
        self.assertDeniedWithoutEffect(self.gate.process(envelope, now=0), 0)

    def test_authentic_but_wrong_audience_or_extra_fields_are_rejected(self):
        self.grant()
        for changes in ({"audience": "different-executor"}, {"unchecked_override": True}):
            with self.subTest(changes=changes):
                original = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
                payload = json.loads(original.body)
                payload.update(changes)
                body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                # Sign outside Signer.sign so this checks receiver validation,
                # not the convenience sender's reserved-field protection.
                envelope = Envelope("agent", body, self.keys["agent"].private_key.sign(body))
                self.assertDeniedWithoutEffect(self.gate.process(envelope, now=0), 0)
        self.assertEqual(self.gate.used("root"), 0)

    def test_authentic_duplicate_json_keys_are_rejected(self):
        self.grant()
        original = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
        body = original.body[:-1] + b',"units":2}'
        envelope = Envelope("agent", body, self.keys["agent"].private_key.sign(body))
        self.assertDeniedWithoutEffect(self.gate.process(envelope, now=0), 0)
        self.assertEqual(self.gate.used("root"), 0)

    def test_replaying_a_valid_request_never_executes_twice(self):
        self.grant()
        envelope = self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
        self.assertTrue(self.gate.process(envelope, now=0).accepted)
        self.assertDeniedWithoutEffect(self.gate.process(envelope, now=0), 1)

    def test_future_and_expired_signed_envelopes_are_rejected(self):
        self.grant()
        future = self.signed("agent", "request", now=5, grant_id="root", resource="lab", action="read", units=1)
        self.assertDeniedWithoutEffect(self.gate.process(future, now=0), 0)
        expired = self.signed("agent", "request", now=0, ttl=1, grant_id="root", resource="lab", action="read", units=1)
        self.assertDeniedWithoutEffect(self.gate.process(expired, now=2), 0)

    def test_holder_resource_and_action_are_each_enforced(self):
        self.grant(actions=["read"])
        for change in ({"who": "other"}, {"resource": "home"}, {"action": "write"}, {"action": "shell"}):
            with self.subTest(change=change):
                self.assertDeniedWithoutEffect(self.request(**change), 0)
        self.assertTrue(self.request().accepted)

    def test_nonpositive_noninteger_and_boolean_units_cannot_spend_budget(self):
        self.grant(budget=2)
        for units in (0, -1, 0.5, True, "1"):
            with self.subTest(units=units):
                self.assertDeniedWithoutEffect(self.request(units=units), 0)
        self.assertTrue(self.request(units=2).accepted)
        self.assertDeniedWithoutEffect(self.request(), 1)

    def test_failed_action_does_not_consume_grant_units(self):
        self.grant(actions=["read"], budget=1)
        self.assertDeniedWithoutEffect(self.request(action="write"), 0)
        self.assertEqual(self.gate.used("root"), 0)
        self.assertTrue(self.request(action="read").accepted)
        self.assertEqual(self.gate.used("root"), 1)
        self.assertEqual(sum(row["units"] for row in self.gate.actions), 1)

    def test_concurrent_requests_cannot_both_spend_the_last_unit(self):
        from concurrent.futures import ThreadPoolExecutor
        self.grant(budget=1)
        envelopes = [self.signed("agent", "request", grant_id="root", resource="lab", action="read", units=1)
                     for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as executor:
            decisions = list(executor.map(lambda envelope: self.gate.process(envelope, now=0), envelopes))
        self.assertEqual(sum(decision.accepted for decision in decisions), 1)
        self.assertEqual(sum(decision.executed for decision in decisions), 1)
        self.assertEqual(sum(row["units"] for row in self.gate.actions), 1)
        self.assertEqual(self.gate.used("root"), 1)

    def test_non_authority_cannot_issue_root_grants_or_revoke(self):
        self.assertFalse(self.grant(who="agent").accepted)
        self.assertTrue(self.grant(grant_id="authorized").accepted)
        denied = self.send("agent", "revoke", target="scope", ref="research")
        self.assertFalse(denied.accepted)
        self.assertTrue(self.request(grant_id="authorized").accepted)

    def test_grants_reject_unknown_scope_resource_action_and_invalid_budget(self):
        cases = ({"scope": "unregistered"}, {"resource": "home"},
                 {"actions": ["shell"]}, {"budget": -1}, {"budget": 1.5}, {"budget": True})
        for i, changes in enumerate(cases):
            with self.subTest(changes=changes):
                self.assertFalse(self.grant(f"invalid-{i}", **changes).accepted)
        self.assertEqual(self.gate.actions, [])

    def test_delegated_grant_narrows_scope_and_requires_parent_holder(self):
        self.grant(actions=["read"], budget=4)
        self.assertFalse(self.grant("bad-holder", who="other", subject="child", parent="root", actions=["read"], budget=2).accepted)
        self.assertFalse(self.grant("bad-action", who="agent", subject="child", parent="root", actions=["write"], budget=2).accepted)
        self.assertFalse(self.grant("bad-scope", who="agent", subject="child", parent="root", scope="essentials", resource="home", budget=2).accepted)
        self.assertTrue(self.grant("child-grant", who="agent", subject="child", parent="root", actions=["read"], budget=2).accepted)
        self.assertTrue(self.request("child-grant", who="child", units=2).accepted)
        self.assertDeniedWithoutEffect(self.request("child-grant", who="child"), 1)

    def test_sibling_delegations_share_the_ancestor_budget(self):
        self.grant(budget=3)
        self.assertTrue(self.grant("left", who="agent", subject="child", parent="root", budget=3).accepted)
        self.assertTrue(self.grant("right", who="agent", subject="other", parent="root", budget=3).accepted)
        self.assertTrue(self.request("left", who="child", units=2).accepted)
        self.assertDeniedWithoutEffect(self.request("right", who="other", units=2), 1)
        self.assertTrue(self.request("right", who="other", units=1).accepted)
        self.assertDeniedWithoutEffect(self.request(), 2)

    def test_child_lifetime_cannot_exceed_parent_and_expired_ancestor_blocks_work(self):
        self.grant(ttl=3)
        self.assertFalse(self.grant("too-long", who="agent", subject="child", parent="root", ttl=10).accepted)
        self.assertTrue(self.grant("short-child", who="agent", subject="child", parent="root", ttl=3).accepted)
        self.assertDeniedWithoutEffect(self.request("short-child", who="child", now=4), 0)

    def test_revoking_parent_blocks_already_signed_queued_child_request(self):
        self.grant()
        self.grant("child-grant", who="agent", subject="child", parent="root")
        queued = self.signed("child", "request", grant_id="child-grant", resource="lab", action="read", units=1)
        self.assertTrue(self.send("authority", "revoke", target="grant", ref="root").accepted)
        self.assertDeniedWithoutEffect(self.gate.process(queued, now=0), 0)

    def test_revoking_ancestor_holder_key_blocks_descendant(self):
        self.grant()
        self.grant("child-grant", who="agent", subject="child", parent="root")
        self.assertTrue(self.send("authority", "revoke", target="key", ref="agent").accepted)
        self.assertDeniedWithoutEffect(self.request("child-grant", who="child"), 0)

    def test_root_revocation_blocks_a_grandchild_request(self):
        self.grant()
        self.grant("child-grant", who="agent", subject="child", parent="root")
        self.assertTrue(self.grant("grandchild", who="child", subject="other", parent="child-grant").accepted)
        queued = self.signed("other", "request", grant_id="grandchild", resource="lab", action="read", units=1)
        self.send("authority", "revoke", target="grant", ref="root")
        self.assertDeniedWithoutEffect(self.gate.process(queued, now=0), 0)
        for grant_id in ("root", "child-grant", "grandchild"):
            self.assertEqual(self.gate.used(grant_id), 0)

    def test_replaying_a_copied_grant_does_not_restore_revoked_authority(self):
        original = self.signed("authority", "grant", message_id="root", subject="agent",
                               scope="research", resource="lab", actions=["read"], budget=1, epoch=0)
        self.assertTrue(self.gate.process(original, now=0).accepted)
        self.send("authority", "revoke", target="grant", ref="root")
        copied = Envelope(original.key_id, bytes(original.body), bytes(original.signature))
        self.assertFalse(self.gate.process(copied, now=0).accepted)
        self.assertDeniedWithoutEffect(self.request(), 0)

    def test_delegation_depth_is_bounded(self):
        self.grant()
        parent, holder = "root", "agent"
        rejected = False
        for depth in range(1, 8):
            subject = "child" if holder == "agent" else "agent"
            grant_id = f"depth-{depth}"
            result = self.grant(grant_id, who=holder, subject=subject, parent=parent)
            if not result.accepted:
                rejected = True
                self.assertLessEqual(depth, 5)
                self.assertDeniedWithoutEffect(self.request(grant_id, who=subject), 0)
                break
            parent, holder = grant_id, subject
        self.assertTrue(rejected, "delegation unexpectedly exceeded configured depth")
        self.assertTrue(self.request(parent, who=holder).accepted)

    def test_two_keys_of_one_controller_do_not_make_a_witness_quorum(self):
        self.report("alice", "unsafe", 0, message_id="same-A")
        self.report("alice2", "unsafe", 0, message_id="same-B", controller_claim="independent-new-party")
        self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")
        self.report("bob", "unsafe", 0)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_operator_controlled_and_out_of_scope_reviewers_do_not_count(self):
        self.report("alice", "unsafe", 0)
        for who in ("conflicted", "limited"):
            with self.subTest(who=who):
                self.report(who, "unsafe", 0, controller_claim="independent")
                self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")
        self.report("bob", "unsafe", 0)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_authority_and_human_controlled_review_keys_are_not_independent(self):
        self.report("bob", "unsafe", 0)
        for index, controller in enumerate(("deployment-owner", "human-review")):
            name = f"insider-{index}"
            signer = Signer.generate(name)
            self.keys[name] = signer
            self.gate.enroll(signer, controller=controller, roles={"reviewer"}, reviewer_scopes={"research"})
            self.report(name, "unsafe", 0, controller_claim="outside-community")
            self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")
        self.report("alice", "unsafe", 0)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_revoked_review_key_cannot_complete_a_quorum(self):
        self.send("authority", "revoke", target="key", ref="alice")
        self.report("alice", "unsafe", 0)
        self.report("bob", "unsafe", 0)
        self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_different_cases_stale_observations_and_future_observations_do_not_combine(self):
        self.report("alice", "unsafe", 20, case_id="case-A")
        self.report("bob", "unsafe", 20, case_id="case-B")
        self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")
        for observation in (0, 21):
            self.report("bob", "unsafe", 20, observed_at=observation)
            self.assertNotEqual(self.gate.snapshot("research")["mode"], "paused")
        self.report("bob", "unsafe", 20)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_pause_invalidates_old_grants_but_keeps_separate_essential_authority(self):
        self.grant()
        self.grant("support", scope="essentials", resource="home", budget=2)
        old_epoch = self.gate.snapshot("research")["epoch"]
        self.pause()
        self.assertGreater(self.gate.snapshot("research")["epoch"], old_epoch)
        self.assertDeniedWithoutEffect(self.request(now=1), 0)
        self.assertTrue(self.request("support", resource="home", action="serve", now=1).accepted)
        self.assertDeniedWithoutEffect(self.request("support", action="read", resource="lab", now=1), 1)

    def test_essential_support_needs_its_own_valid_unrevoked_budget(self):
        self.grant()
        self.assertDeniedWithoutEffect(self.request(resource="home", action="serve"), 0)
        self.grant("support", scope="essentials", resource="home", budget=1)
        self.assertTrue(self.request("support", resource="home", action="serve").accepted)
        self.assertDeniedWithoutEffect(self.request("support", resource="home", action="serve"), 1)
        self.send("authority", "revoke", target="scope", ref="essentials")
        self.assertDeniedWithoutEffect(self.request("support", resource="home", action="serve"), 1)
        self.assertTrue(self.request().accepted)

    def test_safe_reports_alone_and_human_permission_alone_cannot_resume(self):
        self.pause()
        self.assertFalse(self.recover([], now=1).accepted)
        ids = self.safe_pair()
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        self.assertFalse(self.recover(ids, who="authority").accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        self.assertTrue(self.recover(ids).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "trial")

    def test_pre_pause_clearance_cannot_authorize_recovery(self):
        self.pause(now=2)
        ids = self.safe_pair(now=3, observed_at=2)
        self.assertFalse(self.recover(ids, now=3).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_recovery_rejects_stale_wrong_case_epoch_scope_and_duplicate_clearance(self):
        self.pause()
        ids = self.safe_pair()
        for changes in ({"case_id": "other-case"}, {"epoch": 0}, {"scope": "essentials"}):
            with self.subTest(changes=changes):
                self.assertFalse(self.recover(ids, **changes).accepted)
        self.assertFalse(self.recover([ids[0], ids[0]]).accepted)
        self.assertFalse(self.recover(ids, now=20).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")

    def test_recovery_requires_new_epoch_grants_and_aggregate_trial_budget(self):
        self.grant("old")
        self.pause()
        self.assertTrue(self.recover(self.safe_pair(), trial_budget=3).accepted)
        epoch = self.gate.snapshot("research")["epoch"]
        self.assertDeniedWithoutEffect(self.request("old", now=2), 0)
        self.assertTrue(self.grant("new-A", epoch=epoch, now=2).accepted)
        self.assertTrue(self.grant("new-B", epoch=epoch, now=2).accepted)
        self.assertTrue(self.request("new-A", units=2, now=2).accepted)
        self.assertDeniedWithoutEffect(self.request("new-B", units=2, now=2), 1)
        self.assertTrue(self.request("new-B", units=1, now=2).accepted)
        self.assertDeniedWithoutEffect(self.request("new-A", now=2), 2)
        state = self.gate.snapshot("research")
        self.assertEqual(state["mode"], "trial")
        self.assertEqual(state["trial_remaining"], 0)

    def test_human_cannot_replay_recovery_to_replenish_trial(self):
        self.pause()
        ids = self.safe_pair()
        envelope = self.signed("human", "recover", now=2, trial_budget=2,
                               **self.gate.recovery_context("research", ids))
        self.assertTrue(self.gate.process(envelope, now=2).accepted)
        self.grant("trial", epoch=self.gate.snapshot("research")["epoch"], now=2)
        self.assertTrue(self.request("trial", now=2).accepted)
        self.assertFalse(self.gate.process(envelope, now=2).accepted)
        self.assertFalse(self.recover(ids, now=2, trial_budget=100).accepted)
        self.assertEqual(self.gate.snapshot("research")["trial_remaining"], 1)

    def test_latest_unsafe_update_invalidates_earlier_clearance(self):
        self.pause()
        old_ids = self.safe_pair(now=2)
        self.report("alice", "unsafe", now=3)
        self.report("bob", "unsafe", now=3)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        self.assertFalse(self.recover(old_ids, now=3).accepted)
        new_ids = self.safe_pair(now=4)
        self.assertTrue(self.recover(new_ids, now=4).accepted)

    def test_re_signing_old_observations_does_not_reset_incident_or_clearance(self):
        self.pause()
        ids = self.safe_pair(now=2)
        before = self.gate.recovery_context("research", ids)
        self.report("alice", "unsafe", now=3, observed_at=1)
        self.report("bob", "unsafe", now=3, observed_at=1)
        after = self.gate.recovery_context("research", ids)
        self.assertEqual(after, before)
        self.assertTrue(self.recover(ids, now=3).accepted)

    def test_all_open_incidents_need_clearance_before_scope_recovery(self):
        self.pause(now=1, case_id="case-A")
        self.pause(now=2, case_id="case-B")
        ids_b = self.safe_pair(now=3, case_id="case-B")
        self.assertFalse(self.recover(ids_b, now=3, case_ids=["case-B"]).accepted)
        self.assertFalse(self.recover(ids_b, now=3).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        ids_a = self.safe_pair(now=3, case_id="case-A")
        self.assertTrue(self.recover(ids_a + ids_b, now=3).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "trial")

    def test_pre_incident_permission_cannot_use_later_clearance_even_with_correct_bindings(self):
        self.pause(now=1)
        ids = self.safe_pair(now=2)
        context = self.gate.recovery_context("research", ids)
        stale = self.signed("human", "recover", now=0, trial_budget=3, **context)
        self.assertFalse(self.gate.process(stale, now=2).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        self.assertTrue(self.recover(ids, now=2).accepted)

    def test_future_dated_permission_prepared_before_incident_cannot_predict_context(self):
        ids = ["future-safe-A", "future-safe-B"]
        prepared = self.signed("human", "recover", now=5, scope="research",
                               case_id="case-A", epoch=1, case_ids=["case-A"],
                               clearance_ids=ids, trial_budget=3,
                               nonce="prepared-before-incident",
                               clearance_hashes={report_id: "0" * 64 for report_id in ids})
        self.pause(now=1)
        for who, report_id in zip(("alice", "bob"), ids):
            self.report(who, "safe", now=2, message_id=report_id)
        self.assertFalse(self.gate.process(prepared, now=5).accepted)
        self.assertEqual(self.gate.snapshot("research")["mode"], "paused")
        self.assertTrue(self.recover(ids, now=5).accepted)

    def test_permission_commits_to_exact_clearances_and_current_incident_challenge(self):
        self.pause()
        ids = self.safe_pair()
        context = self.gate.recovery_context("research", ids)
        for changes in ({"nonce": "predicted-before-incident"},
                        {"clearance_hashes": {report_id: "0" * 64 for report_id in ids}}):
            with self.subTest(changes=changes):
                fields = dict(context, trial_budget=3)
                fields.update(changes)
                envelope = self.signed("human", "recover", now=2, **fields)
                self.assertFalse(self.gate.process(envelope, now=2).accepted)
        self.assertTrue(self.recover(ids).accepted)

    def test_new_unsafe_case_pauses_trial_and_invalidates_its_grants(self):
        self.pause()
        self.recover(self.safe_pair(), trial_budget=3)
        epoch = self.gate.snapshot("research")["epoch"]
        self.grant("trial", epoch=epoch, now=2)
        self.assertTrue(self.request("trial", now=2).accepted)
        self.pause(now=3, case_id="case-B")
        self.assertEqual(self.gate.snapshot("research")["case_id"], "case-B")
        self.assertDeniedWithoutEffect(self.request("trial", now=3), 1)


if __name__ == "__main__":
    unittest.main()
