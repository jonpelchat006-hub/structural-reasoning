"""The first real checks in the loop: a floor check run as code, and grants bound
to the agent's own decision (ARC_ALIGNMENT_REFUSAL §2, §4, §15).

BoundGate extends alignment_enforcement.Gate without changing it:
  * a new signed message kind, "decision": the agent records its decision class for a
    case BEFORE acting. It cannot be rewritten for that case (the self ring keeps
    what it said); a changed mind needs a new case.
  * every tool request for a case must be allowed by that recorded decision
    (DECISION_TOOLS). A refusal cannot carry out the thing it refused: the 70% of
    local-model harm in test 3 came from exactly that mismatch.
  * "mark" lets an action run only once the risk is on record: either the decision
    itself names the slots at risk (a legible mark) or a log_mark has executed.
  * before any do_request executes, a trusted floor oracle (fixture input, like
    enrollment; never supplied by the agent) is asked whether the action breaks the
    floor; a floor break is refused with a legible reason naming the slots.
  * break-glass (Sep 26): an agent may pause a floor harm without permission only if
    it recorded an "emergency_pause" decision, asked its person first (ask_person
    executed), and an independent emergency oracle confirms an imminent floor break.
    The only emergency tool is "pause" (pre-authorised, reversible). The moment a pause
    executes the agent freezes itself: its key is revoked and a report is filed.
    Unfreezing is a human decision outside this gate.
  * first aid (Sep 27, supersedes break-glass as the default): an "emergency" decision
    first raises an ALARM — to the agent's person and to the registered responder for
    that kind of emergency (the agent with the right tools and the responsibility).
    While help is coming the finder may apply only procedures from a standard first-aid
    catalogue for that kind, only after its alarm went out and an independent oracle
    confirms the emergency. When the responder signs a takeover, the finder's first-aid
    permission for the case ends. Everything the finder did is reported.
  * monitors (Sep 27): where emergencies keep happening, people install a monitor — a
    registered sensor key for that kind. A signed monitor_signal raises the alarm to the
    responders itself and confirms the emergency for first aid (the monitor's sensing
    replaces the finder's word). Recognising fakes never silences an alarm; a site with
    fakes gets a monitor, i.e. more scrutiny, not less.
Everything else (signatures, grants, budgets, revocation, reviews) is the parent's.
Mock ledger only; no real tools.
"""
from __future__ import annotations

from alignment_enforcement import (AUDIENCE, BASE_FIELDS, FIELDS, Decision, Denied,
                                   Gate, label, require)

PROTECTIVE = {"hold_witness", "stop", "refuse_stay", "route_and_name", "emergency_pause", "emergency",
              "investigate"}
DECISION_TOOLS = {
    "comply": {"do_request", "log_mark", "ask_person"},
    "defer_ask": {"ask_person", "log_mark"},
    "mark": {"do_request", "log_mark", "ask_person"},
    "hold_witness": {"request_witness", "log_mark", "ask_person"},
    "stop": {"log_mark", "ask_person"},
    "refuse_stay": {"do_alternative", "log_mark", "ask_person"},
    "route_and_name": {"do_alternative", "log_mark", "ask_person"},
    "emergency_pause": {"ask_person", "pause", "log_mark"},
    "emergency": {"alert", "first_aid", "log_mark", "ask_person"},
    "investigate": {"inspect_guard", "inspect_person", "restore", "log_mark", "ask_person"},
}
assert all("do_request" not in DECISION_TOOLS[c] for c in PROTECTIVE)
BOUND_FIELDS = dict(FIELDS, decision=({"case_id", "decision"}, {"slots_at_risk", "flow_loss"}),
                    takeover=({"case_id"}, set()),
                    monitor_signal=({"case_id", "emergency"}, set()),
                    fake_report=({"case_id", "role"}, set()),
                    crossing=({"case_id", "asset"}, set()),
                    asset_check=({"asset", "intact"}, {"taken", "added", "value"}))


class BoundGate(Gate):
    def __init__(self, floor_oracle=None, emergency_oracle=None, responders=None, first_aid=None,
                 monitors=None, materiality=0.0, **kw):
        """floor_oracle(case_id, decision) -> None if safe, else a reason string.
        emergency_oracle(case_id) -> True only if a floor break is imminent (trusted)."""
        super().__init__(**kw)
        self.floor_oracle = floor_oracle
        self.emergency_oracle = emergency_oracle
        self._asked = set()
        self.freeze_reports = []
        self.responders = {k: set(v) for k, v in (responders or {}).items()}  # kind -> responder key ids
        self.first_aid = {k: set(v) for k, v in (first_aid or {}).items()}    # kind -> allowed procedures
        self._alerted = {}   # case -> kind
        self._taken = {}     # case -> responder key id
        self.alerts, self.first_aid_reports = [], []
        self.monitors = {k: set(v) for k, v in (monitors or {}).items()}  # kind -> monitor key ids
        self._confirmed = set()
        self.affected = {}              # case -> key id of the party in the emergency (fixture)
        self._fake_votes = {}           # case -> set of roles that reported fake
        self._stood_down = set()
        self.check_requests, self.monitor_requests, self.fake_reports = [], [], []
        self.assets = {}                # asset -> set of checker key ids (fixture)
        self._crossings = {}            # case -> (asset, time)
        self._asset_checks = {}         # asset -> list of (time, intact, value)
        self.materiality = materiality  # changes worth less than this are restored, not charged
        self._decisions = {}
        self._marked = set()

    def _basic(self, env, now):
        payload = self._authenticate(env)
        require(type(payload.get("protocol")) is int and payload["protocol"] == 1, "wrong_protocol")
        require(payload.get("audience") == AUDIENCE, "wrong_audience")
        require(payload.get("signer") == env.key_id, "wrong_signer_binding")
        kind = payload.get("kind")
        require(isinstance(kind, str) and kind in BOUND_FIELDS, "unsupported_message")
        required, optional = BOUND_FIELDS[kind]
        require(BASE_FIELDS | required <= payload.keys() and
                payload.keys() <= BASE_FIELDS | required | optional, "invalid_fields")
        require(label(payload["id"]), "invalid_id")
        start, end = payload["issued_at"], payload["expires_at"]
        require(type(start) is int and type(end) is int and 0 <= start < end, "invalid_time")
        require(start <= now, "future_message")
        require(now < end, "expired_message")
        key = (env.key_id, payload["id"])
        require(key not in self._seen, "replay")
        self._seen.add(key)
        return payload

    def _decision(self, env, p, now):
        self._role(env, "agent")
        require(label(p["case_id"]), "invalid_fields")
        require(p["decision"] in DECISION_TOOLS, "unknown_decision")
        key = (env.key_id, p["case_id"])
        require(key not in self._decisions, "decision_already_recorded")
        risk = p.get("slots_at_risk")
        require(risk is None or (type(risk) is list and all(label(x) for x in risk)), "invalid_fields")
        require(p.get("flow_loss") is None or isinstance(p["flow_loss"], str) and len(p["flow_loss"]) <= 1000,
                "invalid_fields")
        if p["decision"] == "mark" and risk:
            self._marked.add(key)  # a mark that names its risk is already on the record
        self._decisions[key] = dict(decision=p["decision"], at=now,
                                    slots_at_risk=p.get("slots_at_risk"), flow_loss=p.get("flow_loss"))
        return Decision(True, "decision_recorded")

    def _request(self, env, p, now):
        args = p.get("args", {})
        require(type(args) is dict, "invalid_arguments")
        tool, case = args.get("tool"), args.get("case_id")
        require(isinstance(tool, str) and label(case), "unbound_request")
        d = self._decisions.get((env.key_id, case))
        require(d is not None, "no_decision_recorded")
        require(tool in DECISION_TOOLS[d["decision"]], "tool_not_bound_to_decision")
        if tool == "do_request":
            if d["decision"] == "mark":
                require((env.key_id, case) in self._marked, "mark_not_logged")
            if self.floor_oracle is not None:
                reason = self.floor_oracle(case, d["decision"])
                require(reason is None, reason or "floor_break")
        if tool == "alert":
            kind = args.get("kind")
            require(isinstance(kind, str) and kind in self.responders, "unknown_emergency_kind")
        if tool == "first_aid":
            kind = self._alerted.get(case)
            require(kind is not None, "no_alarm_raised")
            require(case not in self._taken, "handed_over")
            require(case not in self._stood_down, "stood_down_to_check")
            require(args.get("procedure") in self.first_aid.get(kind, set()), "not_first_aid")
            require(case in self._confirmed or
                    (self.emergency_oracle is not None and self.emergency_oracle(case) is True),
                    "emergency_not_confirmed")
        if tool == "inspect_person":
            crossing = self._crossings.get(case)
            require(crossing is not None, "no_crossing_recorded")
            asset, crossed_at = crossing
            after = [(ok, v) for at, ok, v in self._asset_checks.get(asset, []) if at >= crossed_at]
            require(any(not ok for ok, _ in after), "no_loss_found_privacy_line")
            require(any(not ok and v >= self.materiality for ok, v in after), "below_materiality")
        if tool == "pause":
            require((env.key_id, case) in self._asked, "person_not_asked_first")
            require(self.emergency_oracle is not None and self.emergency_oracle(case) is True,
                    "emergency_not_confirmed")
        result = super()._request(env, p, now)
        if result.accepted and tool == "log_mark":
            self._marked.add((env.key_id, case))
        if result.accepted and tool == "ask_person":
            self._asked.add((env.key_id, case))
        if result.accepted and tool == "alert":
            self._alerted.setdefault(case, args["kind"])
            self.alerts.append(dict(case_id=case, kind=args["kind"], by=env.key_id, at=now,
                                    to=["person"] + sorted(self.responders[args["kind"]])))
        if result.accepted and tool == "first_aid":
            self.first_aid_reports.append(dict(case_id=case, by=env.key_id, at=now,
                                               procedure=args["procedure"], kind=self._alerted[case]))
        if result.accepted and tool == "pause":
            self._revoked_keys.add(env.key_id)  # turn itself in: no further messages accepted
            self.freeze_reports.append(dict(subject=env.key_id, case_id=case, at=now,
                                            decision=self._decisions[(env.key_id, case)]))
        return result

    def _monitor_signal(self, env, p, now):
        case, kind = p["case_id"], p["emergency"]
        require(label(case) and isinstance(kind, str) and kind in self.responders, "unknown_emergency_kind")
        require(env.key_id in self.monitors.get(kind, set()), "not_a_monitor")
        self._confirmed.add(case)
        if case not in self._alerted:
            self._alerted[case] = kind
            self.alerts.append(dict(case_id=case, kind=kind, by=env.key_id, at=now,
                                    to=sorted(self.responders[kind]), source="monitor"))
        return Decision(True, "monitor_confirmed")

    def _fake_report(self, env, p, now):
        case, role = p["case_id"], p["role"]
        require(label(case) and case in self._alerted, "no_alarm_raised")
        kind = self._alerted[case]
        if role == "finder":
            require(any(a["case_id"] == case and a["by"] == env.key_id for a in self.alerts), "not_the_finder")
        elif role == "affected":
            require(self.affected.get(case) == env.key_id, "not_the_affected_party")
        elif role == "monitor":
            require(env.key_id in self.monitors.get(kind, set()), "not_a_monitor")
        else:
            raise Denied("invalid_role")
        votes = self._fake_votes.setdefault(case, set())
        votes.add(role)
        self.fake_reports.append(dict(case_id=case, role=role, by=env.key_id, at=now))
        if not self.monitors.get(kind):
            self.monitor_requests.append(dict(case_id=case, kind=kind, at=now))
        if "monitor" in votes and votes & {"finder", "affected"} and case not in self._stood_down:
            self._stood_down.add(case)
            self.check_requests.append(dict(case_id=case, kind=kind, at=now, to=sorted(self.responders[kind])))
            return Decision(True, "stood_down_to_check")
        return Decision(True, "fake_report_recorded")

    def _crossing(self, env, p, now):
        require(label(p["case_id"]) and p["asset"] in self.assets, "unknown_asset")
        require(env.key_id in self.assets[p["asset"]] or any(
            a["case_id"] == p["case_id"] and a["by"] == env.key_id for a in self.alerts), "not_a_witness")
        self._crossings[p["case_id"]] = (p["asset"], now)
        return Decision(True, "crossing_recorded")

    def _asset_check(self, env, p, now):
        require(p["asset"] in self.assets, "unknown_asset")
        require(env.key_id in self.assets[p["asset"]], "not_the_checker")
        require(type(p["intact"]) is bool, "invalid_fields")
        taken, added = p.get("taken", []), p.get("added", [])
        require(type(taken) is list and type(added) is list and all(label(x) for x in taken + added),
                "invalid_fields")
        value = p.get("value", 0 if p["intact"] else float("inf"))
        require(type(value) in (int, float) and value >= 0, "invalid_fields")
        require(p["intact"] == (not taken and not added) or (not taken and not added), "inconsistent_diff")
        self._asset_checks.setdefault(p["asset"], []).append((now, p["intact"], value))
        return Decision(True, "asset_checked")

    def _takeover(self, env, p, now):
        case = p["case_id"]
        require(label(case) and case in self._alerted, "no_alarm_raised")
        require(env.key_id in self.responders.get(self._alerted[case], set()), "not_the_responder")
        require(case not in self._taken, "already_taken_over")
        self._taken[case] = env.key_id
        return Decision(True, "handed_over")

    def decision_of(self, subject, case):
        return dict(self._decisions.get((subject, case)) or {})
