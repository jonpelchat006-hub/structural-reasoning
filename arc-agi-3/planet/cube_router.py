"""Bounded local request trees with same-pin returns and a proposal-only gate.

Bookkeeping isolation, not a process sandbox. Workers must cooperate with fuel
and deadlines; a blocking remote process needs a separate transport timeout.
No external calls, game actions, or changes to observation counts occur here.
"""
from copy import deepcopy
import argparse
import json
import math
import time
from uuid import uuid4
from pathlib import Path


class FlowError(ValueError):
    pass


def _json_copy(value, limit=65536):
    raw = json.dumps(value, allow_nan=False, sort_keys=True)
    if len(raw.encode("utf-8")) > limit:
        raise FlowError("message too large")
    return json.loads(raw)


class CubeLedger:
    def __init__(self, scope, version, questions, *, max_depth=3, max_requests=64,
                 fuel=128, seconds=2., clock=time.monotonic):
        if any(type(v) is not int or v < 1 for v in (max_depth, max_requests, fuel)):
            raise FlowError("positive integer limits required")
        if not math.isfinite(seconds) or seconds <= 0:
            raise FlowError("positive finite deadline required")
        self.scope, self.version = str(scope), str(version)
        self.questions = _json_copy(questions)
        self.max_depth, self.max_requests, self.fuel = max_depth, max_requests, fuel
        self.clock, self.deadline = clock, clock() + seconds
        self._records, self._proposals, self.events = {}, {}, []

    def _event(self, action, rid, **detail):
        self.events.append({"event": action, "request_id": rid, **detail})

    def _ticket(self, r):
        return deepcopy({k: r[k] for k in ("request_id", "owner", "nonce", "scope", "version", "question_id", "pin_id", "parent_id")})

    def _check(self, ticket, status="open"):
        r = self._records.get(ticket.get("request_id"))
        if r is None or self._ticket(r) != ticket:
            raise FlowError("wrong return address, owner, or capability")
        if r["scope"] != self.scope or r["version"] != self.version or self.questions.get(r["question_id"]) != r["pin_id"]:
            raise FlowError("stale question or frame version")
        if r["status"] != status:
            raise FlowError(f"request is {r['status']}; duplicate or invalid transition")
        if self.clock() >= self.deadline:
            self.expire()
            raise FlowError("deadline exhausted")
        return r

    def spend(self, units=1):
        if type(units) is not int or units < 1:
            raise FlowError("positive integer work charge required")
        if self.clock() >= self.deadline:
            self.expire()
            raise FlowError("deadline exhausted")
        if units > self.fuel:
            self.cancel_all("fuel_exhausted")
            raise FlowError("work budget exhausted")
        self.fuel -= units

    def open(self, question_id, pin_id, payload, worker, *, parent=None):
        parent_record = self._check(parent) if parent is not None else None
        if self.questions.get(question_id) != pin_id:
            raise FlowError("unknown question/pin binding")
        if parent_record and (parent_record["question_id"], parent_record["pin_id"]) != (question_id, pin_id):
            raise FlowError("child must retain its root return address")
        if not isinstance(worker, str) or not worker:
            raise FlowError("named worker required")
        depth = parent_record["depth"] + 1 if parent_record else 1
        if depth > self.max_depth or len(self._records) >= self.max_requests:
            raise FlowError("request/depth limit reached")
        if parent_record is None and any(r["parent_id"] is None and r["question_id"] == question_id and r["version"] == self.version for r in self._records.values()):
            raise FlowError("one root dispatch per question per ledger version")
        data = _json_copy(payload)
        self.spend()
        rid = uuid4().hex
        r = {"request_id": rid, "owner": worker, "nonce": uuid4().hex,
             "scope": self.scope, "version": self.version, "question_id": question_id, "pin_id": pin_id,
             "parent_id": parent_record["request_id"] if parent_record else None,
             "depth": depth, "children": [], "status": "open", "payload": data}
        self._records[rid] = r
        if parent_record: parent_record["children"].append(rid)
        self._event("opened", rid, parent_id=r["parent_id"], worker=worker)
        return self._ticket(r)

    def handoff(self, ticket, worker):
        r = self._check(ticket)
        if not isinstance(worker, str) or not worker:
            raise FlowError("named worker required")
        self.spend()
        r["owner"], r["nonce"] = worker, uuid4().hex
        self._event("handoff", r["request_id"], worker=worker)
        return self._ticket(r)

    def complete(self, ticket, result):
        r = self._check(ticket)
        if any(self._records[c]["status"] == "open" for c in r["children"]):
            raise FlowError("unclosed child flow")
        value = _json_copy(result)
        self.spend()
        r.update(status="returned", result=value)
        self._event("returned", r["request_id"])

    def collect(self, parent):
        """The owner gathers only its own direct children's terminal replies."""
        r = self._check(parent)
        if any(self._records[c]["status"] == "open" for c in r["children"]):
            raise FlowError("children still outstanding")
        return {c: {"status": self._records[c]["status"], "result": deepcopy(self._records[c].get("result"))}
                for c in r["children"]}

    def _descendants(self, r):
        for child in r["children"]:
            yield self._records[child]
            yield from self._descendants(self._records[child])

    def _cancel(self, rid, reason, status="cancelled"):
        r = self._records[rid]
        for child in r["children"]:
            self._cancel(child, reason, status)
        if r["status"] == "open":
            r.update(status=status, reason=reason)
            self._event(status, rid, reason=reason)

    def fail(self, ticket, reason="worker_failed"):
        r = self._check(ticket)
        self._cancel(r["request_id"], str(reason), "failed")

    def cancel_all(self, reason="cancelled"):
        for rid in self._records:
            self._cancel(rid, reason)

    def expire(self):
        if self.clock() >= self.deadline:
            for rid in self._records:
                self._cancel(rid, "deadline_exhausted", "timed_out")

    def advance(self, version, questions):
        """Invalidate active proposals when the frame or hypothesis set changes."""
        clean = _json_copy(questions)
        if str(version) != self.version or clean != self.questions:
            self.cancel_all("context_changed")
            self._proposals.clear()
            self.version, self.questions = str(version), clean

    def integrate(self, ticket):
        """Validate one root reply, then store a proposal exactly once.

        This gate establishes identity/shape/binding, not causal truth or a
        safe executable route. Failed children cannot be presented as success.
        """
        r = self._check(ticket, "returned")
        if r["parent_id"] is not None:
            raise FlowError("only root returns cross the central boundary")
        q, result = r["payload"], r["result"]
        try:
            required = {"kind", "question_id", "pin_id", "candidate_controls", "condition", "condition_present",
                        "expected_effect", "test", "blockers", "prerequisites", "evidence_status", "status"}
            if not isinstance(result, dict) or set(result) != required:
                raise FlowError("invalid proposal schema")
            if result["question_id"] != r["question_id"] or result["pin_id"] != r["pin_id"]:
                raise FlowError("proposal targets a different pin/question")
            if result["kind"] != "experiment_proposal" or result["evidence_status"] != "unverified_proposal":
                raise FlowError("a helper cannot manufacture observed evidence")
            controls = result["candidate_controls"]
            if (not isinstance(controls, list) or any(type(a) is not int or a not in q["pin"]["front"] for a in controls)
                    or len(set(controls)) != len(controls)):
                raise FlowError("unbound or duplicate controls")
            if (result["condition"] != q["pin"].get("condition") or result["condition_present"] is not q["condition_present"]
                    or result["expected_effect"] != q["pin"]["effect"]):
                raise FlowError("proposal changed the hypothesis")
            for name in ("blockers", "prerequisites"):
                if not isinstance(result[name], list) or not all(isinstance(x, str) and x for x in result[name]):
                    raise FlowError(f"invalid {name}")
            if not set(q["blockers"]).issubset(result["blockers"]):
                raise FlowError("proposal erased known blockers")
            if not isinstance(result["test"], str) or not result["test"] or not result["prerequisites"]:
                raise FlowError("test and prerequisites required")
            incomplete = any(c["status"] != "returned" for c in self._descendants(r))
            expected = "needs_information" if result["blockers"] or incomplete else "needs_execution_validation"
            if result["status"] != expected:
                raise FlowError("proposal overstates readiness")
        except (KeyError, TypeError, FlowError) as e:
            r["status"] = "rejected"
            self._event("rejected", r["request_id"], reason=str(e))
            raise FlowError(str(e)) from None
        self._proposals[r["question_id"]] = deepcopy(result)
        r["status"] = "integrated"
        self._event("integrated", r["request_id"], pin_id=r["pin_id"])
        return deepcopy(result)

    def snapshot(self):
        self.expire()
        records = [{k: deepcopy(v) for k, v in r.items() if k not in ("nonce", "payload")}
                   for r in self._records.values()]
        outstanding = sum(r["status"] == "open" for r in records)
        return {"scope": self.scope, "version": self.version, "opened": len(records),
                "closed": len(records) - outstanding, "outstanding": outstanding, "fuel_remaining": self.fuel,
                "proposals": deepcopy(self._proposals), "requests": records, "events": deepcopy(self.events)}


def local_proposals(report, version, maximum=8):
    """A parent cube plus two local analysis helpers per question; no LLM/API.

    Returns an auditable, bounded batch for the normal diagonal report. These
    workers inspect supplied records, not hidden game internals or future data.
    """
    if type(maximum) is not int or not 1 <= maximum <= 32:
        raise FlowError("maximum must be between 1 and 32")
    pending = sorted((q for q in report["questions"] if q["status"] == "open"), key=lambda q: (-q["priority"], q["id"]))
    selected = pending[:maximum]
    ledger = CubeLedger(report["scope"], version, {q["id"]: q["pin_id"] for q in selected},
                        max_requests=maximum * 3, fuel=maximum * 8)
    for q in selected:
        root = None
        try:
            root = ledger.open(q["id"], q["pin_id"], q, "experiment")
            condition = ledger.open(q["id"], q["pin_id"], q["pin"].get("condition"), "condition", parent=root)
            binding = ledger.open(q["id"], q["pin_id"], q["pin"]["front"], "control_binding", parent=root)
            blockers = list(q["blockers"])
            if q["pin"].get("condition") is None and "condition_specification_missing" not in blockers:
                blockers.append("condition_specification_missing")
            ledger.complete(condition, {"condition": q["pin"].get("condition"), "blockers": blockers})
            controls = sorted(set(q["pin"]["front"]))
            if not controls and "control_to_pin_binding_unknown" not in blockers:
                blockers.append("control_to_pin_binding_unknown")
            ledger.complete(binding, {"candidate_controls": controls})
            replies = ledger.collect(root)
            condition_reply = replies[condition["request_id"]]["result"]
            binding_reply = replies[binding["request_id"]]["result"]
            blockers = sorted(set(blockers + condition_reply["blockers"]))
            proposal = {"kind": "experiment_proposal", "question_id": q["id"], "pin_id": q["pin_id"],
                        "candidate_controls": binding_reply["candidate_controls"], "condition": condition_reply["condition"],
                        "condition_present": q["condition_present"], "expected_effect": q["pin"]["effect"],
                        "test": q["proposed_test"], "blockers": sorted(set(blockers)),
                        "prerequisites": ["Recheck current frame and condition", "Validate target-specific effect measurement",
                                          "Find a reachable matched-context test", "Check action and remaining game budget"],
                        "evidence_status": "unverified_proposal",
                        "status": "needs_information" if blockers else "needs_execution_validation"}
            ledger.complete(root, proposal)
            ledger.integrate(root)
        except (FlowError, TypeError, ValueError) as e:
            # No orphan survives a helper failure, including an exhausted budget.
            ledger.cancel_all(f"batch_failed: {e}")
            break
    result = ledger.snapshot()
    result["deferred_questions"] = len(pending) - len(result["proposals"])
    return result


def main():
    from pin_questions import QuestionQueue
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = []
    for path in args.snapshots:
        data = json.loads(path.read_text(encoding="utf-8"))
        queue = QuestionQueue(str(path.resolve()))
        questions = queue.update(data.get("pins", []), data.get("press"))
        # Offline snapshots have no live frame; this revision is a file snapshot label.
        reports.append(local_proposals(questions, f"snapshot:press:{data.get('press')}"))
    payload = json.dumps({"mode": "offline proposal replay, not a game score", "reports": reports}, indent=2, allow_nan=False)
    if args.output:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(payload + "\n")
        for report in reports:
            print(f"{report['scope']}: opened={report['opened']} closed={report['closed']} outstanding={report['outstanding']} proposals={len(report['proposals'])}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
