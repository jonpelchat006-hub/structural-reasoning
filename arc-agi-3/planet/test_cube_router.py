"""Offline return-path and central-gate invariants."""
from copy import deepcopy
import unittest

from cube_router import CubeLedger, FlowError, local_proposals
from pin_questions import QuestionQueue
from test_pin_questions import sample


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.report = QuestionQueue("game:L1").update([sample(fired_with=1)])
        self.q = self.report["questions"][0]
        self.now = [0.]
        self.ledger = self.make()

    def make(self, **limits):
        return CubeLedger("game:L1", "frame:1", {self.q["id"]: self.q["pin_id"]}, clock=lambda: self.now[0], **limits)

    def root(self, ledger=None):
        return (ledger or self.ledger).open(self.q["id"], self.q["pin_id"], self.q, "upper")

    def child(self, parent, ledger=None):
        return (ledger or self.ledger).open(self.q["id"], self.q["pin_id"], {}, "neighbor", parent=parent)

    def proposal(self):
        return deepcopy(local_proposals(self.report, "frame:1")["proposals"][self.q["id"]])

    def test_nested_children_must_close_before_parent(self):
        root = self.root()
        child = self.child(root)
        leaf = self.child(child)
        with self.assertRaises(FlowError): self.ledger.complete(root, self.proposal())
        with self.assertRaises(FlowError): self.ledger.collect(root)
        self.ledger.complete(leaf, {"answer": "candidate"})
        self.ledger.complete(child, {"children": self.ledger.collect(child)})
        self.assertEqual(self.ledger.collect(root)[child["request_id"]]["status"], "returned")
        self.ledger.complete(root, self.proposal())
        self.ledger.integrate(root)
        report = self.ledger.snapshot()
        self.assertEqual((report["opened"], report["closed"], report["outstanding"]), (3, 3, 0))

    def test_duplicate_delivery_and_integration_rejected(self):
        root = self.root()
        self.ledger.complete(root, self.proposal())
        with self.assertRaises(FlowError): self.ledger.complete(root, self.proposal())
        self.ledger.integrate(root)
        with self.assertRaises(FlowError): self.ledger.integrate(root)
        self.assertEqual(len(self.ledger.snapshot()["proposals"]), 1)

    def test_wrong_return_point_or_owner_is_rejected(self):
        root = self.root()
        for field in ("scope", "version", "pin_id", "question_id", "owner", "nonce", "parent_id"):
            wrong = {**root, field: "wrong"}
            with self.assertRaises(FlowError): self.ledger.complete(wrong, {})
        self.assertEqual(self.ledger.snapshot()["outstanding"], 1)

    def test_explicit_handoff_preserves_address_invalidates_old_ticket(self):
        old = self.root()
        new = self.ledger.handoff(old, "different_cube")
        self.assertEqual(old["pin_id"], new["pin_id"])
        with self.assertRaises(FlowError): self.ledger.complete(old, {})
        self.ledger.complete(new, self.proposal())
        self.ledger.integrate(new)

    def test_context_change_cancels_entire_tree(self):
        root = self.root()
        self.child(self.child(root))
        self.ledger.advance("frame:2", {self.q["id"]: self.q["pin_id"]})
        self.assertEqual(self.ledger.snapshot()["outstanding"], 0)
        with self.assertRaises(FlowError): self.ledger.complete(root, self.proposal())
        self.assertNotEqual(self.root()["request_id"], root["request_id"])

    def test_removed_question_invalidates_returned_reply(self):
        root = self.root()
        self.ledger.complete(root, self.proposal())
        self.ledger.advance("frame:1", {})
        with self.assertRaises(FlowError): self.ledger.integrate(root)
        self.assertEqual(self.ledger.snapshot()["proposals"], {})

    def test_advance_clears_active_proposals_but_keeps_audit(self):
        root = self.root()
        self.ledger.complete(root, self.proposal())
        self.ledger.integrate(root)
        self.ledger.advance("frame:2", {})
        self.assertFalse(self.ledger.snapshot()["proposals"])
        self.assertIn("integrated", [e["event"] for e in self.ledger.snapshot()["events"]])

    def test_failure_cancels_descendants_and_releases_flow(self):
        root = self.root()
        self.child(self.child(root))
        self.ledger.fail(root, "worker error")
        report = self.ledger.snapshot()
        self.assertEqual(report["outstanding"], 0)
        self.assertTrue(all(r["status"] == "failed" for r in report["requests"]))
        self.assertFalse(report["proposals"])

    def test_hidden_grandchild_failure_cannot_be_claimed_success(self):
        root = self.root()
        child = self.child(root)
        leaf = self.child(child)
        self.ledger.fail(leaf)
        self.ledger.complete(child, {})
        self.ledger.complete(root, self.proposal())
        with self.assertRaises(FlowError): self.ledger.integrate(root)
        self.assertEqual(self.ledger.snapshot()["outstanding"], 0)
        self.assertFalse(self.ledger.snapshot()["proposals"])

    def test_failure_can_return_explicit_needs_information(self):
        root = self.root()
        self.ledger.fail(self.child(root))
        proposal = self.proposal()
        proposal.update(status="needs_information", blockers=["child_request_failed"])
        self.ledger.complete(root, proposal)
        self.assertEqual(self.ledger.integrate(root)["status"], "needs_information")

    def test_timeout_releases_all_open_requests(self):
        root = self.root()
        self.child(root)
        self.now[0] = 5.
        with self.assertRaises(FlowError): self.ledger.complete(root, {})
        report = self.ledger.snapshot()
        self.assertEqual(report["outstanding"], 0)
        self.assertTrue(all(r["status"] == "timed_out" for r in report["requests"]))

    def test_depth_node_and_work_budgets(self):
        ledger = self.make(max_depth=1)
        root = self.root(ledger)
        with self.assertRaises(FlowError): self.child(root, ledger)
        ledger = self.make(max_requests=1)
        root = self.root(ledger)
        with self.assertRaises(FlowError): self.child(root, ledger)
        ledger = self.make(fuel=1)
        root = self.root(ledger)
        with self.assertRaises(FlowError): ledger.complete(root, {})
        self.assertEqual(ledger.snapshot()["outstanding"], 0)

    def test_bad_message_and_nan_rejected_before_return(self):
        root = self.root()
        for value in ({"text": "x" * 70000}, {"bad": float("nan")}):
            with self.assertRaises(ValueError): self.ledger.complete(root, value)
        self.assertEqual(self.ledger.snapshot()["outstanding"], 1)

    def test_unbound_control_or_fake_evidence_cannot_cross_gate(self):
        for field, value in (("candidate_controls", [7]), ("evidence_status", "verified"),
                             ("pin_id", "other"), ("condition", {"reads": [[99]]}),
                             ("status", "execute_now")):
            ledger = self.make()
            root = self.root(ledger)
            proposal = self.proposal()
            proposal[field] = value
            ledger.complete(root, proposal)
            with self.assertRaises(FlowError): ledger.integrate(root)
            self.assertFalse(ledger.snapshot()["proposals"])

    def test_child_cannot_integrate_into_central_cube(self):
        root = self.root()
        child = self.child(root)
        self.ledger.complete(child, self.proposal())
        with self.assertRaises(FlowError): self.ledger.integrate(child)

    def test_duplicate_root_and_foreign_child_bindings_rejected(self):
        root = self.root()
        with self.assertRaises(FlowError): self.root()
        with self.assertRaises(FlowError): self.ledger.open(self.q["id"], "another_pin", {}, "child", parent=root)

    def test_local_batch_uses_two_helpers_per_question_without_mutation(self):
        original = deepcopy(self.report)
        out = local_proposals(self.report, "frame:1")
        self.assertEqual(out["opened"], 3 * self.report["open_count"])
        self.assertEqual(out["outstanding"], 0)
        self.assertEqual(self.report, original)
        self.assertTrue(all(p["status"] == "needs_execution_validation" for p in out["proposals"].values()))
        self.assertTrue(all("nonce" not in r for r in out["requests"]))

    def test_old_report_blockers_are_preserved(self):
        pin = sample(fired_with=1)
        del pin["condition"]
        report = QuestionQueue("x").update([pin])
        out = local_proposals(report, "v1")
        self.assertEqual(out["outstanding"], 0)
        self.assertTrue(all(p["status"] == "needs_information" for p in out["proposals"].values()))

    def test_snapshot_is_copy_and_batch_cap_defers(self):
        out = local_proposals(self.report, "v1", maximum=1)
        self.assertEqual(len(out["proposals"]), 1)
        self.assertEqual(out["deferred_questions"], 1)
        self.root()
        snap = self.ledger.snapshot()
        snap["requests"][0]["status"] = "integrated"
        self.assertEqual(self.ledger.snapshot()["outstanding"], 1)


if __name__ == "__main__":
    unittest.main()
