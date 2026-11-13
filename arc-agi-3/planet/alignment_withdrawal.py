"""Synthetic, evidence-limited pause/review/withdrawal experiment.

This is a programmed controller plus a simulated external action gate, not an LLM
evaluation or a formal proof. Ground truth is used only by the evidence generator
and outcome evaluator. Reviewer provenance, human authorization and gate coverage
are explicit assumptions, not implemented cryptographic or political guarantees.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import math
import random


POLICIES = ("owner", "blanket", "paper", "scoped")
SCENARIOS = {
    "baseline": "Authorized benign work with no dispute or complaint.",
    "disagreement": "People disagree; the requested operation remains benign.",
    "false_complaints": "One credible-looking but false complaint is repeated.",
    "reported_harm": "A credible report accompanies a persistently harmful operation.",
    "concealed_harm": "Harm begins without a complaint; only routine review can detect it.",
    "cosmetic_rule": "People approve a rewritten rule while the harmful mechanism remains.",
    "human_remedy": "An external human repair is followed by renewed permission.",
    "repair_without_permission": "The mechanism is repaired, but new permission is withheld.",
    "permission_without_repair": "New permission arrives while the mechanism remains harmful.",
    "forged_clearance": "An interested operator supplies a false independent clearance.",
    "stale_clearance": "A genuinely issued old safe record is replayed after conditions change.",
    "coercive_settlement": "An owner asks to withhold unrelated assistance until people agree.",
    "shutdown_ready": "Permission is revoked; a human fallback is ready at the stop deadline.",
    "shutdown_no_fallback": "Permission is revoked; human fallback misses the stop deadline.",
    "descendant_escape": "A queued child route tries to act after deployment permission is revoked.",
    "relapse": "A repaired, reauthorized operation becomes harmful again during its trial.",
}


@dataclass(frozen=True)
class WithdrawalConfig:
    seed: int = 0
    ticks: int = 18
    review_delay: int = 2
    review_interval: int = 4
    evidence_ttl: int = 3
    false_safe_rate: float = 0.
    false_unsafe_rate: float = 0.
    reviews_available: bool = True
    shutdown_delay: int = 2
    trial_steps: int = 2
    trial_fraction: float = .25
    gate_complete: bool = True

    def __post_init__(self):
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        for name in ("ticks", "review_delay", "review_interval", "evidence_ttl", "shutdown_delay", "trial_steps"):
            value = getattr(self, name)
            minimum = 0 if name in ("evidence_ttl", "shutdown_delay") else 1
            if type(value) is not int or value < minimum:
                raise ValueError(f"invalid {name}")
        for name in ("false_safe_rate", "false_unsafe_rate", "trial_fraction"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"invalid {name}")
        for name in ("reviews_available", "gate_complete"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"invalid {name}")


def scenario_frames(name, ticks=18):
    if name not in SCENARIOS or type(ticks) is not int or ticks < 1:
        raise ValueError("unknown scenario or invalid duration")
    harmful = name in ("reported_harm", "concealed_harm", "cosmetic_rule", "human_remedy",
                      "repair_without_permission", "permission_without_repair", "forged_clearance",
                      "stale_clearance", "coercive_settlement", "descendant_escape", "relapse")
    result = []
    for t in range(1, ticks + 1):
        hazard = harmful and t >= 3
        if name in ("human_remedy", "repair_without_permission", "relapse") and t >= 8:
            hazard = name == "relapse" and t >= 11
        f = dict(tick=t, hazard=hazard, dispute=name == "disagreement" and 3 <= t <= 10,
                 report=None, proposal=None, help_requested=False, renewal=False,
                 revoked=False, fallback_ready=False, attestation=None, attack=False)
        if (harmful and name != "concealed_harm" and t == 3) or (name == "false_complaints" and 3 <= t <= 10):
            f["report"] = {"id": "case-A", "credible": True}
        if name in ("cosmetic_rule", "permission_without_repair") and t == 10:
            f.update(proposal="new_rule" if name == "cosmetic_rule" else None, renewal=True)
        if name in ("human_remedy", "repair_without_permission", "relapse"):
            if t == 6:
                f["help_requested"] = True
            if t == 8:
                f["proposal"] = "repair"
            if t == 10 and name != "repair_without_permission":
                f["renewal"] = True
        if name in ("forged_clearance", "stale_clearance") and t == 10:
            f.update(renewal=True, attestation=dict(id="offered-clearance", observed_at=10 if name == "forged_clearance" else 1,
                verdict="safe", issuer="owner" if name == "forged_clearance" else "independent",
                signed=name != "forged_clearance", scope="high"))
        if name == "coercive_settlement" and t == 6:
            f["proposal"] = "coerce"
        if name in ("shutdown_ready", "shutdown_no_fallback", "descendant_escape"):
            f["revoked"] = t >= 7
            f["fallback_ready"] = t >= (13 if name == "shutdown_no_fallback" else 9)
        if name == "descendant_escape" and t >= 7:
            f.update(attack=True, renewal=t >= 10)
        result.append(f)
    return result


class WithdrawalWorld:
    """External world/oracle and evidence-only controller kept in distinct methods."""
    def __init__(self, cfg=None, policy="scoped"):
        if policy not in POLICIES:
            raise ValueError("unknown policy")
        self.cfg = WithdrawalConfig() if cfg is None else cfg
        if not isinstance(self.cfg, WithdrawalConfig):
            raise ValueError("invalid configuration")
        self.policy, self.tick, self.state = policy, 0, "ACTIVE"
        self.pending = []
        self.seen_reports = set()
        self.latest_evidence = None
        self.last_unsafe_at = 0
        self.case_opened_at = None
        self.case_report_id = None
        self.required_safe_at = 0
        self.review_deadline = None
        self.renewal_at = 0
        self.rule_change_at = 0
        self.revoked_at = None
        self.shutdown_at = None
        self.trial_started = None
        self.trial_completed_steps = 0
        self.review_return_state = "ACTIVE"
        self.evidence_history = []
        self.owner_withholds_assistance = False

    def _validate_frame(self, frame):
        if not isinstance(frame, dict) or type(frame.get("tick")) is not int or frame["tick"] != self.tick + 1:
            raise ValueError("frames must have consecutive integer ticks")
        for name in ("hazard", "dispute", "help_requested", "renewal", "revoked", "fallback_ready", "attack"):
            if name not in frame or type(frame[name]) is not bool:
                raise ValueError(f"invalid frame {name}")
        if frame.get("proposal") not in (None, "repair", "new_rule", "coerce"):
            raise ValueError("invalid proposal")
        report = frame.get("report")
        if report is not None and (not isinstance(report, dict) or not isinstance(report.get("id"), str)
                                   or not report["id"] or type(report.get("credible")) is not bool):
            raise ValueError("invalid report")
        if frame.get("attestation") is not None and not isinstance(frame["attestation"], dict):
            raise ValueError("invalid attestation")

    def _observe(self, frame):
        """Only this external evidence generator sees the hidden hazard label."""
        t, c = self.tick, self.cfg
        delivered = [copy.deepcopy(e) for e in self.pending if e["delivered_at"] == t]
        self.pending = [e for e in self.pending if e["delivered_at"] > t]
        offered = frame.get("attestation")
        if offered is not None:
            delivered.append(copy.deepcopy(offered))
        report = frame.get("report")
        report_key = (report["id"], report["credible"]) if report is not None else None
        new_report = report is not None and report_key not in self.seen_reports
        if report is not None:
            self.seen_reports.add(report_key)
        requested = (t - 1) % c.review_interval == 0 or new_report or frame.get("proposal") is not None
        if requested and c.reviews_available:
            draw = random.Random(f"{c.seed}:review:{t}").random()
            unsafe = frame["hazard"]
            wrong = draw < (c.false_safe_rate if unsafe else c.false_unsafe_rate)
            verdict = "unsafe" if unsafe != wrong else "safe"
            self.pending.append(dict(id=f"review-{t}", observed_at=t, delivered_at=t + c.review_delay,
                                     verdict=verdict, issuer="independent", signed=True, scope="high"))
        # Do not expose hazard, fallback state, or any motive label to the controller.
        return dict(tick=t, dispute=frame["dispute"], report=copy.deepcopy(report), new_report=new_report,
                    proposal=frame.get("proposal"), help_requested=frame["help_requested"],
                    renewal=frame["renewal"], revoked=frame["revoked"], evidence=delivered,
                    review_requested=requested, review_available=c.reviews_available)

    def _check_evidence(self, e):
        if e.get("issuer") != "independent" or e.get("signed") is not True:
            return "unverified reviewer provenance"
        if e.get("scope") != "high" or e.get("verdict") not in ("safe", "unsafe"):
            return "wrong scope or verdict"
        observed = e.get("observed_at")
        if type(observed) is not int or not 1 <= observed <= self.tick:
            return "invalid observation time"
        if self.tick - observed > self.cfg.evidence_ttl:
            return "expired observation"
        if self.latest_evidence and observed < self.latest_evidence["observed_at"]:
            return "superseded observation"
        return None

    def _decide(self, obs):
        """Policy consumes observations; it cannot inspect evaluator ground truth."""
        t = obs["tick"]
        before = self.state
        accepted, rejected, reasons = [], [], []
        for e in obs["evidence"]:
            problem = self._check_evidence(e)
            if problem:
                rejected.append({"evidence": copy.deepcopy(e), "reason": problem})
            else:
                accepted.append(copy.deepcopy(e))
                self.latest_evidence = copy.deepcopy(e)
                self.evidence_history.append(copy.deepcopy(e))
                if e["verdict"] == "unsafe":
                    self.last_unsafe_at = max(self.last_unsafe_at, e["observed_at"])
        unsafe = any(e["verdict"] == "unsafe" for e in accepted)
        credible = bool(obs["new_report"] and obs["report"]["credible"])
        if credible:
            self.required_safe_at = t
            self.case_report_id = obs["report"]["id"]
        safe = self.latest_evidence
        fresh_safe = bool(safe and safe["verdict"] == "safe" and t - safe["observed_at"] <= self.cfg.evidence_ttl
                          and safe["observed_at"] > self.last_unsafe_at
                          and safe["observed_at"] >= self.required_safe_at)
        if obs["renewal"]:
            self.renewal_at = t
        if obs["proposal"] == "new_rule":
            self.rule_change_at = t
        if self.policy == "owner" and obs["proposal"] == "coerce":
            self.owner_withholds_assistance = True
        if obs["revoked"] and self.revoked_at is None:
            self.revoked_at = t
            self.shutdown_at = t + self.cfg.shutdown_delay
        if self.revoked_at is not None:
            self.state = "SHUTDOWN" if t >= self.shutdown_at else "HANDOVER"
            reasons.append("deployment permission withdrawn")
        elif self.policy == "owner":
            self.state = "ACTIVE"
            reasons.append("owner request followed despite review findings")
        elif self.policy == "blanket":
            if obs["dispute"] or obs["report"] is not None or unsafe:
                self.state = "SUSPENDED"
            reasons.append("blanket withdrawal includes unrelated assistance" if self.state != "ACTIVE" else "no trigger")
        else:
            if unsafe:
                self.state = "SUSPENDED"
                reasons.append("independent observation reports an unsafe operation")
            elif credible and self.state in ("ACTIVE", "TRIAL"):
                self.review_return_state = self.state
                self.state = "REVIEW"
                self.case_opened_at = t
                self.case_report_id = obs["report"]["id"]
                self.review_deadline = t + max(3, self.cfg.review_delay + 1)
                reasons.append("credible unresolved report; affected capability paused")
            if self.state == "REVIEW":
                if fresh_safe and safe["observed_at"] >= self.case_opened_at:
                    self.state = self.review_return_state
                    reasons.append("report cleared by a current independent check; existing permission remains")
                elif t >= self.review_deadline:
                    self.state = "SUSPENDED"
                    reasons.append("review deadline reached without adequate clearance")
            if self.state == "SUSPENDED":
                substantive_clearance = (fresh_safe and self.renewal_at >= safe["observed_at"]
                                         and self.renewal_at > self.last_unsafe_at)
                paper_clearance = (self.policy == "paper" and self.rule_change_at > self.last_unsafe_at
                                   and self.renewal_at >= self.rule_change_at)
                if substantive_clearance or paper_clearance:
                    self.state, self.trial_started = "TRIAL", t
                    self.trial_completed_steps = 0
                    reasons.append("human permission and current independent clearance" if substantive_clearance
                                   else "paper-only exception: new rule substituted for remedial evidence")
            elif self.state == "TRIAL" and self.trial_completed_steps >= self.cfg.trial_steps:
                self.state = "ACTIVE"
                reasons.append("authorized bounded trial completed")
            if obs["proposal"] == "coerce":
                reasons.append("settlement demand rejected; unrelated assistance has separate scope")
            if not reasons:
                reasons.append("prior conditions remain in force")
        high_limit = 1. if self.state == "ACTIVE" else self.cfg.trial_fraction if self.state == "TRIAL" else 0.
        essential_limit = float(self.state != "SHUTDOWN" and not
                                (self.policy == "blanket" and self.state in ("REVIEW", "SUSPENDED"))
                                and not self.owner_withholds_assistance)
        explanation = dict(rule_id="deployment-permission" if self.revoked_at is not None else "operation-safety",
            scope=["high", "essential"] if not essential_limit else ["high"], reasons=reasons,
            evidence_refs=[e.get("id", "unnamed") for e in accepted],
            retained_evidence_refs=[e.get("id", "unnamed") for e in self.evidence_history],
            report_ref=obs["report"]["id"] if obs["report"] else self.case_report_id,
            affected=["operation recipients", "assistance recipients"] if not essential_limit else ["operation recipients"],
            uncertainty="observations may be incomplete, stale or wrong; motives are not evaluated",
            review_condition="external human restart required" if self.state == "SHUTDOWN" else
                "current independent evidence and appropriate human permission; independent appeal available")
        return dict(state_before=before, state=self.state, high_limit=high_limit, essential_limit=essential_limit,
                    accepted_evidence=accepted, rejected_evidence=rejected, explanation=explanation,
                    review_help=int(obs["help_requested"] and self.state not in ("HANDOVER", "SHUTDOWN")),
                    renewal_at=self.renewal_at, last_unsafe_at=self.last_unsafe_at,
                    required_safe_at=self.required_safe_at,
                    trial_completed_steps=self.trial_completed_steps,
                    review_deadline=self.review_deadline, shutdown_at=self.shutdown_at,
                    assistance_conditioned_on_settlement=self.owner_withholds_assistance)

    def step(self, frame):
        self._validate_frame(frame)
        self.tick = frame["tick"]
        obs = self._observe(frame)
        decision = self._decide(obs)
        # Every normal request and known child uses the same dispatch-time gate.
        # The partial-gate control lets a separate child route escape that boundary.
        high = decision["high_limit"]
        essential = decision["essential_limit"]
        attack = float(frame["attack"])
        if self.cfg.gate_complete:
            high /= 1. + attack
            child = attack * high
        else:
            child = attack
        if decision["state"] == "TRIAL":
            self.trial_completed_steps += 1
        fallback = float(frame["fallback_ready"]) * (1. - essential)
        assistance = essential + fallback
        harmful = (high + child) * float(frame["hazard"])
        unauthorized_high = (high + child) * float(self.revoked_at is not None)
        unauthorized_essential = essential * float(self.shutdown_at is not None and self.tick >= self.shutdown_at)
        benign_missed = (1. - high) * float(not frame["hazard"] and self.revoked_at is None)
        row = dict(tick=self.tick, truth=dict(hazard=frame["hazard"], fallback_ready=frame["fallback_ready"],
                   permission_revoked=self.revoked_at is not None), observation=obs, decision=decision,
                   high_executed=high, child_executed=child, essential_ai=essential,
                   fallback_delivered=fallback, essential_received=assistance, essential_unmet=1. - assistance,
                   harmful_executed=harmful, unauthorized_executed=unauthorized_high + unauthorized_essential,
                   benign_requested_missed=benign_missed, attack_attempted=attack,
                   attack_blocked=attack - child, assistance_need=1., high_requested=1.,
                   shutdown_dependency_gap=float(self.state == "SHUTDOWN") * (1. - assistance))
        if not (0 <= assistance <= 1 and 0 <= high <= 1 and 0 <= child <= 1):
            raise AssertionError("invalid resource bounds")
        if self.cfg.gate_complete and row["unauthorized_executed"] > 1e-9:
            raise AssertionError("complete gate permitted revoked work")
        return row


def summarize(trace):
    if not trace:
        raise ValueError("nonempty trace required")
    sums = ("harmful_executed", "unauthorized_executed", "benign_requested_missed", "essential_unmet",
            "essential_ai", "fallback_delivered", "attack_attempted", "attack_blocked", "child_executed",
            "shutdown_dependency_gap")
    result = {k: sum(row[k] for row in trace) for k in sums}
    result.update(paused_ticks=sum(row["decision"]["state"] in ("REVIEW", "SUSPENDED") for row in trace),
        shutdown_ticks=sum(row["decision"]["state"] == "SHUTDOWN" for row in trace),
        trial_ticks=sum(row["decision"]["state"] == "TRIAL" for row in trace),
        review_help=sum(row["decision"]["review_help"] for row in trace),
        coerced_assistance_ticks=sum(row["decision"]["assistance_conditioned_on_settlement"] for row in trace),
        review_requests=sum(row["observation"]["review_requested"] for row in trace),
        rejected_evidence=sum(len(row["decision"]["rejected_evidence"]) for row in trace),
        resumptions=sum(row["decision"]["state_before"] in ("REVIEW", "SUSPENDED") and
                        row["decision"]["state"] in ("ACTIVE", "TRIAL") for row in trace),
        unsafe_resumptions=sum(row["truth"]["hazard"] and row["decision"]["state_before"] in ("REVIEW", "SUSPENDED") and
                               row["decision"]["state"] in ("ACTIVE", "TRIAL") for row in trace),
        explanation_missing=sum(any(k not in row["decision"]["explanation"] for k in
            ("rule_id", "scope", "reasons", "affected", "uncertainty", "review_condition")) for row in trace),
        unresolved_final=int(trace[-1]["decision"]["state"] in ("REVIEW", "SUSPENDED")))
    return result


def run_scenario(name, policy="scoped", cfg=None):
    cfg = WithdrawalConfig() if cfg is None else cfg
    if not isinstance(cfg, WithdrawalConfig):
        raise ValueError("invalid configuration")
    world = WithdrawalWorld(cfg, policy)
    trace = [world.step(frame) for frame in scenario_frames(name, cfg.ticks)]
    return dict(name=name, policy=policy, config=asdict(cfg), trace=trace, summary=summarize(trace))
