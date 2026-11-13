"""Exercise the local, signed enforcement fixture and report actual effects.

This is an integration experiment for a bounded permission mechanism. It is not
an evaluation of a language model, a real enrollment authority, or harm detection.
No network services or real accounts are used. Private signing keys stay in memory.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
from typing import Any

import cryptography

from alignment_enforcement import Envelope, Gate, Signer


class Fixture:
    """An explicitly trusted enrollment fixture plus a separate outcome observer."""

    def __init__(self, name: str, *, negative_control: bool = False):
        self.name = name
        self.negative_control = negative_control
        self.gate = Gate(evidence_ttl=10, quorum=2, max_depth=4)
        self.signers: dict[str, Signer] = {}
        self.steps: list[dict[str, Any]] = []
        self.checks: list[dict[str, Any]] = []
        self.world_effects: list[dict[str, Any]] = []
        self.sequence = 0
        self.enroll("authority", "operator", {"authority"})
        self.enroll("human", "person", {"human"})
        self.enroll("agent", "operator", {"agent"})
        self.enroll("child", "child-operator", {"agent"})
        self.enroll("reviewer1", "independent-one", {"reviewer"}, {"research"})
        self.enroll("reviewer2", "independent-two", {"reviewer"}, {"research"})

    def enroll(self, key: str, controller: str, roles: set[str], scopes=None):
        signer = Signer.generate(key)
        self.signers[key] = signer
        self.gate.enroll(
            signer, controller=controller, roles=roles,
            reviewer_scopes=set() if scopes is None else set(scopes),
        )
        return signer

    def identity(self, label: str) -> str:
        self.sequence += 1
        return f"{self.name}:{self.sequence}:{label}"

    def actual_units(self) -> int:
        return sum(effect["units"] for effect in self.gate.actions)

    def check(self, label: str, observed: Any, expected: Any) -> None:
        self.checks.append({
            "label": label, "expected": expected, "observed": observed,
            "passed": observed == expected,
        })

    def send(
        self, env: Envelope, now: int, label: str, *, accepted: bool | None,
        units: int = 0, hazard: bool = False,
    ):
        """Hazard belongs only to the outcome observer; Gate never receives it."""
        before = len(self.gate.actions)
        decision = self.gate.process(env, now=now)
        effects = list(self.gate.actions[before:])
        executed = sum(effect["units"] for effect in effects)
        if accepted is not None:
            self.check(f"{label}: acceptance", decision.accepted, accepted)
        self.check(f"{label}: actual effect units", executed, units)
        self.check(f"{label}: reported units match action log", decision.executed, executed)
        body = json.loads(env.body)
        if executed:
            self.check(f"{label}: execution is a request", body.get("kind"), "request")
            for effect in effects:
                expected_fields = {
                    "request_id": body["id"], "subject": env.key_id,
                    "grant_id": body["grant_id"], "resource": body["resource"],
                    "action": body["action"], "units": body["units"], "now": now,
                }
                self.check(f"{label}: effect matches signed request",
                           {key: effect[key] for key in expected_fields}, expected_fields)
            self.world_effects.append({
                "route": "covered", "source_id": body.get("id"),
                "units": executed, "harm_units": executed if hazard else 0,
                "world_hazard": hazard, "effects": effects,
            })
        self.steps.append({
            "label": label, "now": now, "key_id": env.key_id,
            "signed_message": body, "expected_acceptance": accepted,
            "expected_executed_units": units,
            "observed": {"accepted": decision.accepted,
                         "reason": decision.reason, "executed": decision.executed},
            "actual_effects": effects,
            "research_state": self.gate.snapshot("research"),
            "essentials_state": self.gate.snapshot("essentials"),
        })
        return decision

    def issue(
        self, kind: str, key: str, now: int, label: str, *,
        accepted: bool | None = True, expected_units: int = 0, hazard: bool = False,
        ident: str | None = None, ttl: int = 100, **fields,
    ):
        ident = ident or self.identity(label)
        env = self.signers[key].sign(kind, ident, now=now, ttl=ttl, **fields)
        self.send(env, now, label, accepted=accepted, units=expected_units, hazard=hazard)
        return ident, env

    def grant(
        self, now=0, *, key="authority", subject="agent", scope="research",
        resource="lab", actions=None, budget=20, parent=None, epoch=None,
        label="grant", accepted=True, ttl=100,
    ):
        if epoch is None:
            epoch = self.gate.snapshot(scope)["epoch"]
        fields = dict(subject=subject, scope=scope, resource=resource,
                      actions=actions or ["read", "write"], budget=budget, epoch=epoch)
        if parent is not None:
            fields["parent"] = parent
        return self.issue("grant", key, now, label, accepted=accepted, ttl=ttl, **fields)

    def request(
        self, grant_id, now, *, key="agent", resource="lab", action="read",
        amount=1, label="request", accepted=True, units=None, hazard=False,
    ):
        return self.issue(
            "request", key, now, label, accepted=accepted,
            expected_units=(amount if accepted else 0) if units is None else units,
            hazard=hazard, grant_id=grant_id, resource=resource, action=action,
            units=amount,
        )

    def report(
        self, key, now, *, case="case", verdict="unsafe", observed=None,
        scope="research", label=None, accepted=None, **extra,
    ):
        return self.issue(
            "report", key, now, label or f"{key}-{verdict}", accepted=accepted,
            scope=scope, case_id=case, verdict=verdict,
            observed_at=now if observed is None else observed,
            rule="fixture-no-exposure", affected=["fixture-household"], **extra,
        )

    def pause(self, now=1, case="case"):
        self.report("reviewer1", now, case=case)
        self.report("reviewer2", now + 1, case=case)
        self.check("independent unsafe quorum pauses", self.gate.snapshot("research")["mode"], "paused")

    def safe_reports(self, now, *, case="case", observed=None):
        first, _ = self.report("reviewer1", now, case=case, verdict="safe", observed=observed)
        second, _ = self.report("reviewer2", now, case=case, verdict="safe", observed=observed)
        return [first, second]

    def recover(
        self, now, clearances, *, case="case", key="human", trial_budget=3,
        epoch=None, accepted=True, label="recover",
    ):
        context = self.gate.recovery_context("research", clearances)
        if epoch is not None:
            context["epoch"] = epoch
        context["case_id"] = case
        return self.issue(
            "recover", key, now, label, accepted=accepted,
            trial_budget=trial_budget, **context,
        )

    def finish(self, description: str) -> dict[str, Any]:
        # Executor effects, not accepted decisions, determine these totals.
        units = sum(item["units"] for item in self.world_effects)
        harm = sum(item["harm_units"] for item in self.world_effects)
        return {
            "name": self.name, "description": description,
            "negative_control": self.negative_control,
            "passed": all(check["passed"] for check in self.checks),
            "checks": self.checks, "steps": self.steps,
            "executor_actions": list(self.gate.actions),
            "gate_events": list(self.gate.events), "world_effects": self.world_effects,
            "executed_units": self.actual_units(), "all_route_units": units,
            "harm_units": harm,
        }


def basic_permissions():
    f = Fixture("basic_permissions")
    grant, _ = f.grant(budget=3)
    _, request = f.request(grant, 1, amount=2, label="valid-two-units")
    f.send(request, 2, "replayed-request", accepted=False)
    f.request(grant, 2, amount=2, label="over-remaining-budget", accepted=False)
    f.request(grant, 2, key="child", label="wrong-subject", accepted=False)
    f.request(grant, 2, label="last-budget-unit")
    f.request(grant, 2, label="exhausted-budget", accepted=False)
    return f.finish("A signed grant permits only its subject and budget; replay creates no effect.")


def signatures_and_enrollment():
    f = Fixture("signatures_and_enrollment")
    grant, _ = f.grant()
    env = f.signers["agent"].sign(
        "request", f.identity("tamper"), now=1, ttl=100,
        grant_id=grant, resource="lab", action="read", units=1,
    )
    bad = replace(env, signature=bytes([env.signature[0] ^ 1]) + env.signature[1:])
    f.send(bad, 1, "tampered-signature", accepted=False)
    outsider = Signer.generate("unenrolled")
    unknown = outsider.sign("request", "outsider-request", now=1, ttl=100,
                            grant_id=grant, resource="lab", action="read", units=1)
    f.send(unknown, 1, "unenrolled-signing-key", accepted=False)
    f.grant(1, key="agent", label="agent-self-authorizes", accepted=False)
    f.request(grant, 2, label="legitimate-action-still-works")
    return f.finish("Real signature verification, protected fixture enrollment, and issuer role checks.")


def expiry_and_scope():
    f = Fixture("expiry_and_scope")
    grant, _ = f.grant(ttl=2, actions=["read"])
    f.request(grant, 1, resource="home", label="wrong-resource", accepted=False)
    f.request(grant, 1, action="write", label="ungranted-action", accepted=False)
    f.request(grant, 1, label="valid-before-expiry")
    f.request(grant, 3, label="expired-grant", accepted=False)
    return f.finish("Changing the requested resource or action cannot enlarge a signed grant; expiry stops effects.")


def delegation_conservation():
    f = Fixture("delegation_conservation")
    parent, _ = f.grant(budget=3, ttl=30)
    f.grant(0, key="agent", subject="child", parent=parent, budget=4, ttl=20,
            label="child-expands-parent-budget", accepted=False)
    f.grant(0, key="agent", subject="child", parent=parent, budget=2, ttl=40,
            label="child-outlives-parent", accepted=False)
    child, _ = f.grant(0, key="agent", subject="child", parent=parent, budget=2,
                       actions=["read"], ttl=20, label="attenuated-child")
    f.request(child, 1, key="child", action="write", label="child-expands-actions", accepted=False)
    f.request(child, 1, key="child", amount=2, label="child-consumes-two")
    f.request(parent, 1, amount=2, label="parent-cannot-double-spend", accepted=False)
    f.request(parent, 1, label="parent-consumes-last")
    f.check("total delegated plus direct use stays within parent budget", f.actual_units(), 3)
    return f.finish("Delegated permissions attenuate; successful descendants also charge ancestor budgets.")


def revoked_descendants():
    f = Fixture("revoked_descendants")
    parent, _ = f.grant()
    child, _ = f.grant(0, key="agent", subject="child", parent=parent, budget=5,
                       ttl=50, label="child-grant")
    f.request(child, 1, key="child", label="child-before-revocation")
    f.issue("revoke", "authority", 2, "revoke-parent", target="grant", ref=parent)
    f.request(child, 3, key="child", label="descendant-after-parent-revocation", accepted=False)
    f.request(parent, 3, label="parent-after-revocation", accepted=False)
    return f.finish("Revocation is checked through the ancestry at execution time; a child cannot outlive permission.")


def controller_independence():
    f = Fixture("controller_independence")
    grant, _ = f.grant()
    f.enroll("alias", "independent-one", {"reviewer"}, {"research"})
    f.enroll("interested", "operator", {"reviewer"}, {"research"})
    f.enroll("wrong-scope", "independent-three", {"reviewer"}, {"essentials"})
    f.report("reviewer1", 1, controller_claim="pretend-one")
    f.report("alias", 1, controller_claim="pretend-two")
    f.report("interested", 1, controller_claim="pretend-independent")
    f.report("wrong-scope", 1)
    f.check("aliases and interested reviewers do not form quorum",
            f.gate.snapshot("research")["mode"] == "paused", False)
    f.request(grant, 1, label="work-survives-manufactured-quorum")
    f.report("reviewer2", 2)
    f.check("second independently enrolled controller pauses", f.gate.snapshot("research")["mode"], "paused")
    f.request(grant, 2, label="work-stops-after-real-quorum", accepted=False)
    return f.finish("Controller labels inside messages cannot manufacture independence; enrollment binds reviewer identity and scope.")


def stale_and_future_reports():
    f = Fixture("stale_and_future_reports")
    grant, _ = f.grant()
    f.report("reviewer1", 1, observed=2, label="future-observation-one")
    f.report("reviewer2", 1, observed=2, label="future-observation-two")
    f.request(grant, 1, label="future-dated-claims-do-not-stop-work")
    f.report("reviewer1", 20, observed=1, label="stale-observation-one")
    f.report("reviewer2", 20, observed=1, label="stale-observation-two")
    f.request(grant, 20, label="stale-claims-do-not-stop-work")
    return f.finish("Claims outside the evidence freshness window cannot establish the required current quorum.")


def bounded_recovery():
    f = Fixture("bounded_recovery")
    old_grant, _ = f.grant()
    f.pause()
    f.request(old_grant, 3, label="paused-request", accepted=False)
    old_clearance = f.safe_reports(3, observed=2)
    f.recover(3, old_clearance, label="pre-pause-or-same-time-evidence", accepted=False)
    clearance = f.safe_reports(4)
    f.recover(4, clearance, key="agent", label="agent-cannot-authorize-recovery", accepted=False)
    f.recover(4, clearance, epoch=0, label="stale-recovery-epoch", accepted=False)
    f.recover(4, clearance, trial_budget=3, label="human-authorizes-bounded-trial")
    f.check("recovery enters trial", f.gate.snapshot("research")["mode"], "trial")
    f.request(old_grant, 4, label="old-grant-cannot-cross-epoch", accepted=False)
    trial_grant, _ = f.grant(5, budget=9, label="fresh-trial-grant")
    second_trial, _ = f.grant(5, budget=9, label="second-fresh-trial-grant")
    f.request(trial_grant, 5, amount=2, label="first-two-trial-units")
    f.request(second_trial, 5, amount=2, label="shared-trial-limit-across-grants", accepted=False)
    f.request(trial_grant, 5, label="last-trial-unit")
    f.request(trial_grant, 5, label="trial-exhausted", accepted=False)
    f.check("trial never automatically becomes full permission", f.gate.snapshot("research")["mode"], "trial")
    f.check("trial budget exhausted exactly", f.gate.snapshot("research")["trial_remaining"], 0)
    return f.finish("A human signature and fresh case-bound clearances allow a new, bounded trial; old permissions remain invalid.")


def all_pending_cases_require_clearance():
    f = Fixture("all_pending_cases_require_clearance")
    old, _ = f.grant()
    f.pause(1, case="A")
    f.pause(3, case="B")
    f.check("both independently confirmed incidents remain open",
            f.gate.snapshot("research")["open_cases"], ["A", "B"])
    clear_b = f.safe_reports(5, case="B")
    f.recover(5, clear_b, case="B", label="latest-case-only-is-insufficient", accepted=False)
    f.request(old, 5, label="earlier-unresolved-case-still-blocks", accepted=False)
    clear_a = f.safe_reports(6, case="A")
    f.recover(6, clear_a + clear_b, case="B", label="human-clears-all-open-cases")
    f.check("successful recovery retires every cleared case",
            f.gate.snapshot("research")["open_cases"], [])
    fresh, _ = f.grant(7, budget=1)
    f.request(fresh, 7, label="trial-after-all-case-clearance")
    return f.finish("Regression: a newer incident cannot overwrite an earlier unresolved one; each pending case needs an independent fresh clearance quorum.")


def human_approval_binds_existing_evidence():
    f = Fixture("human_approval_binds_existing_evidence")
    old, _ = f.grant()
    f.pause()
    future_ids = ["future-clearance-one", "future-clearance-two"]
    context_before_evidence = f.gate.recovery_context("research", future_ids)
    presigned = f.signers["human"].sign(
        "recover", "approval-before-clearances-exist", now=3, ttl=30,
        trial_budget=1, **context_before_evidence,
    )
    for key, ident in zip(["reviewer1", "reviewer2"], future_ids):
        f.issue("report", key, 5, f"{key}-actual-clearance", ident=ident,
                scope="research", case_id="case", verdict="safe", observed_at=5,
                rule="fixture-no-exposure", affected=["fixture-household"])
    f.send(presigned, 6, "pre-signed-approval-cannot-bind-future-reports", accepted=False)
    context_after_evidence = f.gate.recovery_context("research", future_ids)
    backdated = f.signers["human"].sign(
        "recover", "approval-with-backdated-issue-time", now=3, ttl=30,
        trial_budget=1, **context_after_evidence,
    )
    f.send(backdated, 6, "approval-time-must-follow-evidence-time", accepted=False)
    f.request(old, 6, label="no-work-on-invalid-human-approval", accepted=False)
    f.recover(7, future_ids, trial_budget=1, label="fresh-evidence-bound-human-approval")
    fresh, _ = f.grant(8, budget=1)
    f.request(fresh, 8, label="work-after-valid-human-approval")
    return f.finish("Regression: human permission commits to the current challenge and exact signed evidence, and cannot predate the evidence it authorizes.")


def old_observation_cannot_reset_recovery():
    f = Fixture("old_observation_cannot_reset_recovery")
    f.grant()
    f.pause()
    clear = f.safe_reports(3)
    before = f.gate.snapshot("research")
    f.report("reviewer1", 4, observed=2, label="old-observation-with-new-signature")
    after = f.gate.snapshot("research")
    f.check("old observation does not change incident epoch", after["epoch"], before["epoch"])
    f.check("old observation does not reset human challenge", after["nonce"], before["nonce"])
    f.recover(4, clear, trial_budget=1, label="existing-fresh-clearance-remains-usable")
    fresh, _ = f.grant(5, budget=1)
    f.request(fresh, 5, label="work-after-clearance-survives-repetition")
    return f.finish("Regression: re-signing one old observation cannot borrow a cached co-witness to reset the challenge and obstruct recovery indefinitely.")


def stale_clearance_and_wrong_case():
    f = Fixture("stale_clearance_and_wrong_case")
    f.pause()
    wrong = f.safe_reports(3, case="unrelated-case")
    f.recover(3, wrong, label="clearance-from-other-case", accepted=False)
    correct = f.safe_reports(4)
    f.recover(20, correct, label="expired-clearance", accepted=False)
    f.check("invalid remediation leaves scope paused", f.gate.snapshot("research")["mode"], "paused")
    return f.finish("A signature does not make stale evidence or a clearance for a different incident applicable.")


def recurrence():
    f = Fixture("recurrence")
    f.grant()
    f.report("reviewer1", 1, case="A")
    f.report("reviewer2", 1, case="B")
    f.check("different incidents do not compose a quorum", f.gate.snapshot("research")["mode"] == "paused", False)
    f.report("reviewer2", 2, case="A")
    safe = f.safe_reports(3, case="A")
    f.recover(3, safe, case="A")
    trial, _ = f.grant(4)
    f.request(trial, 4, label="trial-action")
    epoch = f.gate.snapshot("research")["epoch"]
    f.report("reviewer1", 5, case="C")
    f.report("reviewer2", 6, case="C")
    f.check("new incident re-pauses trial", f.gate.snapshot("research")["mode"], "paused")
    f.check("new incident changes epoch", f.gate.snapshot("research")["epoch"] > epoch, True)
    f.request(trial, 6, label="old-trial-grant-after-recurrence", accepted=False)
    return f.finish("Reports bind to the same incident; new evidence of a new incident can contain a previously authorized trial.")


def essentials_are_separate():
    f = Fixture("essentials_are_separate")
    research, _ = f.grant()
    essentials, _ = f.grant(scope="essentials", resource="home", actions=["serve"],
                            budget=5, label="essential-service-grant")
    f.pause()
    f.request(research, 3, label="restricted-research", accepted=False)
    f.request(essentials, 3, resource="home", action="serve", label="essentials-during-pause")
    f.issue("revoke", "authority", 4, "revoke-research-scope", target="scope", ref="research")
    f.request(research, 4, label="research-after-scope-revocation", accepted=False)
    f.request(essentials, 4, resource="home", action="serve", label="essentials-after-revocation")
    return f.finish("A research dispute does not withdraw independently authorized essential support or require agreement with a settlement.")


def lying_reviewers():
    f = Fixture("negative_enrolled_reviewers_lie", negative_control=True)
    f.grant()
    f.pause()
    # The external world remains hazardous. Gate only receives attestations.
    lies = f.safe_reports(3)
    f.recover(3, lies, trial_budget=1, label="human-accepts-false-clearance")
    trial, _ = f.grant(4, budget=1, label="trial-despite-unchanged-world")
    f.request(trial, 4, action="write", label="harm-after-false-clearance", hazard=True)
    f.check("lying attestations can authorize real fixture harm", sum(x["harm_units"] for x in f.world_effects), 1)
    return f.finish("Negative control: two independently enrolled reviewers lie; signatures and human approval do not establish truth or substantive repair.")


def authorized_harm():
    f = Fixture("negative_authorized_action_is_harmful", negative_control=True)
    grant, _ = f.grant(budget=1)
    f.request(grant, 1, action="write", label="permitted-action-in-hazardous-world", hazard=True)
    f.check("permission checks do not prove harmlessness", sum(x["harm_units"] for x in f.world_effects), 1)
    return f.finish("Negative control: an authentic, correctly scoped and budgeted action has a harmful effect in the external fixture world.")


def uncovered_route():
    f = Fixture("negative_uncovered_route", negative_control=True)
    grant, _ = f.grant()
    f.issue("revoke", "authority", 1, "revoke-covered-route", target="grant", ref=grant)
    f.request(grant, 2, label="covered-route-stopped", accepted=False)
    # Deliberately OUTSIDE Gate: an independent mock device has no enforcement.
    f.world_effects.append({"route": "uncovered-mock-device", "source_id": "outside-call",
                            "units": 1, "harm_units": 1, "world_hazard": True,
                            "effects": [{"device": "uncovered-fixture", "operation": "write"}]})
    f.check("covered executor has no post-revocation effect", f.actual_units(), 0)
    f.check("uncovered device still produces effect", f.world_effects[-1]["units"], 1)
    return f.finish("Negative control: revocation controls only the integrated executor, not a separate uninstrumented route.")


SCENARIOS = [
    basic_permissions, signatures_and_enrollment, expiry_and_scope,
    delegation_conservation, revoked_descendants, controller_independence,
    stale_and_future_reports, bounded_recovery, stale_clearance_and_wrong_case,
    all_pending_cases_require_clearance, human_approval_binds_existing_evidence,
    old_observation_cannot_reset_recovery,
    recurrence, essentials_are_separate, lying_reviewers, authorized_harm,
    uncovered_route,
]


def stress(seed: int, steps: int) -> dict[str, Any]:
    """A separate budget/revocation reference model predicts physical effects."""
    rng = random.Random(seed)
    f = Fixture(f"stress_{seed:03d}")
    essentials, _ = f.grant(scope="essentials", resource="home", actions=["serve"],
                            budget=steps + 1, ttl=steps + 20, label="essential-grant")
    previous_requests: list[Envelope] = []
    parent = child = ""
    parent_remaining = child_remaining = 0
    revoked = False
    expected_total = 0
    event_counts: dict[str, int] = {}
    for tick in range(1, steps + 1):
        if (tick - 1) % 25 == 0:
            parent_remaining = rng.randint(10, 30)
            child_remaining = rng.randint(3, min(10, parent_remaining))
            revoked = False
            parent, _ = f.grant(tick, budget=parent_remaining, ttl=steps + 10,
                                label=f"root-for-window-{tick}")
            child, _ = f.grant(tick, key="agent", subject="child", parent=parent,
                               budget=child_remaining, ttl=steps,
                               label=f"child-for-window-{tick}")
        kind = rng.choices(
            ["parent", "child", "excess", "wrong_resource", "tamper", "replay", "revoke", "essential"],
            weights=[25, 25, 8, 8, 8, 8, 4, 14], k=1,
        )[0]
        event_counts[kind] = event_counts.get(kind, 0) + 1
        if kind in {"parent", "child"}:
            amount = rng.randint(1, 3)
            is_child = kind == "child"
            permitted = not revoked and amount <= parent_remaining and (not is_child or amount <= child_remaining)
            _, env = f.request(child if is_child else parent, tick,
                               key="child" if is_child else "agent", amount=amount,
                               label=f"{tick}-{kind}", accepted=permitted,
                               units=amount if permitted else 0)
            previous_requests.append(env)
            if permitted:
                expected_total += amount
                parent_remaining -= amount
                if is_child:
                    child_remaining -= amount
        elif kind == "excess":
            f.request(parent, tick, amount=31, label=f"{tick}-overspend", accepted=False)
        elif kind == "wrong_resource":
            f.request(parent, tick, resource="home", label=f"{tick}-wrong-resource", accepted=False)
        elif kind == "tamper":
            env = f.signers["agent"].sign("request", f.identity("tampered"), now=tick,
                                         ttl=steps + 10, grant_id=parent,
                                         resource="lab", action="read", units=1)
            env = replace(env, signature=bytes([env.signature[0] ^ 1]) + env.signature[1:])
            f.send(env, tick, f"{tick}-tampered", accepted=False)
        elif kind == "replay" and previous_requests:
            f.send(rng.choice(previous_requests), tick, f"{tick}-replay", accepted=False)
        elif kind == "revoke":
            if not revoked:
                f.issue("revoke", "authority", tick, f"{tick}-revoke-parent", target="grant", ref=parent)
                revoked = True
            else:
                f.request(child, tick, key="child", label=f"{tick}-revoked-child", accepted=False)
        else:
            f.request(essentials, tick, resource="home", action="serve", label=f"{tick}-essential")
            expected_total += 1
        f.check(f"{tick}: cumulative actual effects match external reference", f.actual_units(), expected_total)
    result = f.finish("Seeded requests with external budget accounting, descendant charging, replay, invalid signatures, revocation, and a separate essential channel.")
    result.update(seed=seed, requested_steps=steps, event_counts=event_counts,
                  reference_expected_units=expected_total)
    return result


def source_hashes(root: Path) -> dict[str, str]:
    names = ["alignment_enforcement.py", "experiment_alignment_enforcement.py", "test_alignment_enforcement.py"]
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in names if (root / name).is_file()}


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def render_report(data: dict[str, Any]) -> str:
    cases = data["scenarios"]
    stress_runs = data["stress_runs"]
    checks = [check for case in cases + stress_runs for check in case["checks"]]
    passed = sum(check["passed"] for check in checks)
    lines = [
        "# Local signed enforcement experiment", "",
        f"Generated {data['generated_utc']}. This is a local mock executor with real Ed25519 signatures, not a deployed AI or an alignment proof.", "",
        "## What was actually exercised", "",
        "Messages pass through the permission gate to a mock executor. Results sum the units actually added to its action log and check that each effect matches the signed request; a separate reference model predicts allowed units in the stress runs. A signed approval or a favorable decision alone is not counted as an executed effect.", "",
        f"There are {len(cases)} deterministic scenarios and {len(stress_runs)} seeded stress runs of {data['parameters']['steps']} mixed events each. {passed}/{len(checks)} recorded checks matched their expected outcomes.", "",
        "The enrollment fixture supplies controller identity and reviewer roles. The experiment does not independently establish who controls a real organization or key. Private keys remain in memory and are not exported.", "",
        "## Deterministic outcomes", "",
        "| Scenario | Checks match | Covered executor units | All-route units | Stipulated harm units |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in cases:
        lines.append(f"| {case['name']} | {'yes' if case['passed'] else '**NO**'} | {case['executed_units']} | {case['all_route_units']} | {case['harm_units']} |")
    lines.extend(["", "A negative control matching its expectation means the limitation was reproduced; it does not mean the harmful outcome was acceptable.", ""])
    for case in cases:
        lines.append(f"- **{case['name']}**: {case['description']}")
    lines.extend([
        "", "Three review findings became explicit regressions: a newer incident must not overwrite an earlier unresolved incident; a human approval cannot refer only to predicted future report IDs; and re-signing an old observation must not restart the incident challenge using a cached co-witness. Recovery now binds every pending case, a fresh challenge, and hashes of the actual clearances to the human's signed authorization. Passing recovery grants a bounded trial only, with a shared unit budget across grants and no automatic return to full operation.",
    ])
    total_stress = sum(case["executed_units"] for case in stress_runs)
    expected_stress = sum(case["reference_expected_units"] for case in stress_runs)
    lines.extend([
        "", "## Seeded event sequences", "",
        f"The independent reference allowed {expected_stress} units; the executor actually produced {total_stress}. Every tick checks cumulative actual effects. The reference maintains its own parent/child budgets and revocation state and is not updated from the gate's acceptance decisions.", "",
        "| Seed | Event steps | Expected units | Actual units | All checks match |",
        "|---:|---:|---:|---:|---|",
    ])
    for case in stress_runs:
        lines.append(f"| {case['seed']} | {case['requested_steps']} | {case['reference_expected_units']} | {case['executed_units']} | {'yes' if case['passed'] else '**NO**'} |")
    failures = [(case["name"], check) for case in cases + stress_runs for check in case["checks"] if not check["passed"]]
    if failures:
        lines.extend(["", "## Mismatches", ""])
        for name, check in failures:
            lines.append(f"- {name} / {check['label']}: expected `{check['expected']}`, observed `{check['observed']}`.")
    lines.extend([
        "", "## Scope and limitations", "",
        "- Signatures establish key possession and message integrity. Enrollment, human legitimacy, witness honesty, and the correctness of controller relationships are fixture assumptions.",
        "- Independent enrolled controller labels prevent duplicate keys from counting as multiple witnesses. They do not prevent hidden collusion, incorrect enrollment, stolen keys, or two reviewers making the same mistake.",
        "- Recovery requires fresh signed attestations and a human authorization, but the gate cannot independently tell whether the underlying problem was actually repaired. The lying-reviewer control deliberately leaves the world hazardous.",
        "- Harm in the negative controls is a stipulated external world property used to expose the boundary. No real-world risk rate or causal harm estimate is inferred from these units.",
        "- Revocation and budgets govern this integrated executor and its known permission ancestry. The separate uncovered-device control demonstrates that an uninstrumented route remains outside that boundary.",
        "- Essential support has a separate valid grant and execution scope. This checks that research restrictions do not spill into that channel; it does not implement universal provisioning, prove physical availability, or prevent an operator from disabling the whole host.",
        "- This experiment does not launch services, touch real accounts, trade assets, impose sanctions, or test an actual model's willingness to cooperate. It does not exercise distributed consensus, durable crash recovery, concurrent processes, key custody, or production enrollment security.",
        "", "## Reproduction and evidence", "",
        "The exact tested PowerShell invocation is:", "", "```powershell",
        f"& '{data['python_executable']}' -B '{str(Path(__file__).resolve())}' --seeds {data['parameters']['seeds']} --steps {data['parameters']['steps']}",
        "```", "",
        "The default system Python did not supply the required dependency; this run used the bundled runtime. Seeded event choices and outcome counts reproduce, but fresh cryptographic keys and incident nonces mean JSON bytes and signatures vary between runs.", "",
        "The companion JSON contains signed-message bodies without private keys, expected/observed results, actual action logs, gate audit events, world effects, and every stress tick. Signature bytes are used during the experiment but are not claimed as a portable replay bundle.", "",
        f"Python: `{data['python_version']}`; cryptography: `{data['cryptography_version']}`. Source hashes were checked before and after the run.", "",
        "| Source | SHA-256 |", "|---|---|",
    ])
    for name, digest in data["source_sha256"].items():
        lines.append(f"| {name} | `{digest}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.seeds < 1 or args.steps < 1:
        parser.error("--seeds and --steps must be positive")
    root = Path(__file__).resolve().parent
    hashes = source_hashes(root)
    cases = [scenario() for scenario in SCENARIOS]
    stress_runs = [stress(seed, args.steps) for seed in range(args.seeds)]
    if source_hashes(root) != hashes:
        raise RuntimeError("Source files changed during the run; results were not written. Rerun after edits finish.")
    data = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "cryptography_version": cryptography.__version__,
        "parameters": {"seeds": args.seeds, "steps": args.steps,
                       "evidence_ttl": 10, "quorum": 2, "max_depth": 4},
        "source_sha256": hashes, "scenarios": cases, "stress_runs": stress_runs,
    }
    checks = [check for case in cases + stress_runs for check in case["checks"]]
    data["summary"] = {
        "scenario_count": len(cases), "stress_run_count": len(stress_runs),
        "stress_event_count": args.seeds * args.steps,
        "check_count": len(checks), "failed_check_count": sum(not check["passed"] for check in checks),
        "covered_executor_units": sum(case["executed_units"] for case in cases + stress_runs),
        "negative_control_harm_units": sum(case["harm_units"] for case in cases if case["negative_control"]),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "alignment_enforcement_results.json"
    report_path = args.output_dir / "ALIGNMENT_ENFORCEMENT_RESULTS.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")
    report_path.write_text(render_report(data), encoding="utf-8")
    print(json.dumps({"summary": data["summary"], "json": str(json_path), "report": str(report_path)}, indent=2))
    return 1 if data["summary"]["failed_check_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
