"""A per-level attempt budget survives restarting the same relation hypothesis.

This is a loop guard, not a proof the relation is wrong. A materially changed
hypothesis or an already-matched target may be tried again.
"""
import hashlib
import json


def identity(rel):
    data = {k: rel.get(k) for k in ("src", "region", "colour", "raw_open", "state_patterns")}
    data["targets"] = [{"id": t["id"], "pattern": t.get("pattern")} for t in rel.get("targets", [])]
    raw = json.dumps(data, sort_keys=True, default=lambda v: v.tolist(), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


class RelationAttempts:
    def __init__(self, limit=8):
        if type(limit) is not int or limit < 1:
            raise ValueError("positive attempt limit required")
        self.limit, self.counts, self.stalls = limit, {}, {}

    def allowed(self, rel, *, matched=False):
        return matched or self.counts.get(identity(rel), 0) < self.limit

    def attempt(self, rel):
        key = identity(rel)
        if not self.allowed(rel):
            raise ValueError("relation attempt budget exhausted")
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] >= self.limit:
            self.stalls[key] = {"hypothesis_id": key, "source": rel["src"], "attempts": self.counts[key],
                                "question": "Repeated source-touch attempts have exhausted this hypothesis's budget. Is the target condition, source binding, or required additional object wrong?",
                                "status": "needs_new_evidence_or_hypothesis", "not_an_impossibility_proof": True}

    def snapshot(self):
        return {"limit": self.limit, "counts": self.counts.copy(),
                "stalls": [dict(v) for v in self.stalls.values()]}
