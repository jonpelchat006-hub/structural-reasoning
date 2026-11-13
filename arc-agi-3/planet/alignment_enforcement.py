"""Local signed-capability experiment, not a production service or an AI model.

Ed25519 authenticates bytes. Enrollment, controller relationships, the clock,
human roles, protected process state, and complete executor coverage are trusted
fixture inputs. Evidence truth is deliberately NOT inferred from signatures.
Only an in-memory action ledger is affected; there are no real tools or network.
Requires cryptography (tested with the bundled runtime's version 50.0.1).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import secrets
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


AUDIENCE = "alignment-local-executor"
BASE_FIELDS = {"protocol", "audience", "signer", "kind", "id", "issued_at", "expires_at"}
FIELDS = {
    "grant": ({"subject", "scope", "resource", "actions", "budget", "epoch"}, {"parent"}),
    "request": ({"grant_id", "resource", "action", "units"}, {"args"}),
    "revoke": ({"target", "ref"}, set()),
    "report": ({"scope", "case_id", "verdict", "observed_at", "rule", "affected"}, {"controller_claim"}),
    "recover": ({"scope", "case_id", "epoch", "clearance_ids", "trial_budget", "nonce", "clearance_hashes"}, {"case_ids"}),
}
SCOPES = {
    "research": ("lab", frozenset({"read", "write"})),
    "essentials": ("home", frozenset({"serve"})),
}


@dataclass(frozen=True)
class Envelope:
    key_id: str
    body: bytes
    signature: bytes


@dataclass(frozen=True)
class Signer:
    key_id: str
    private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls, key_id):
        return cls(key_id, Ed25519PrivateKey.generate())

    def sign(self, kind, id, now=0, ttl=100, **fields):
        payload = dict(protocol=1, audience=AUDIENCE, signer=self.key_id, kind=kind, id=id,
                       issued_at=now, expires_at=now + ttl)
        if BASE_FIELDS.intersection(fields):
            raise ValueError("reserved envelope fields")
        payload.update(fields)
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
        return Envelope(self.key_id, body, self.private_key.sign(body))


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str
    executed: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Identity:
    public_key: object
    controller: str
    roles: frozenset
    reviewer_scopes: frozenset


class Denied(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Denied(reason)


def positive_int(value):
    return type(value) is int and value > 0


def label(value):
    return isinstance(value, str) and 0 < len(value) <= 128


def envelope_digest(env):
    """Bind clearance content, signature, and enrolled signer to an approval."""
    data = json.dumps(dict(key_id=env.key_id, body=env.body.hex(),
                           signature=env.signature.hex()), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class Gate:
    """Serialized check/charge/record boundary for one protected mock executor.

    Enrollment and direct access to Python objects are outside the message
    threat model. A production service would require durable atomic state and
    isolation, not merely this process-local lock and in-memory collections.
    """

    def __init__(self, evidence_ttl=10, quorum=2, max_depth=4):
        if not all(positive_int(x) for x in (evidence_ttl, quorum, max_depth)):
            raise ValueError("positive integer configuration required")
        self.evidence_ttl, self.quorum, self.max_depth = evidence_ttl, quorum, max_depth
        self._identities = {}
        self._revoked_keys = set()
        self._revoked_grants = set()
        self._grants = {}
        self._used = {}
        self._reports = {}
        self._seen = set()
        self._retired_cases = set()
        self._cases = {scope: {} for scope in SCOPES}
        self._states = {scope: dict(mode="active", epoch=0, case_id=None,
                                   trial_remaining=None, paused_at=None, nonce=None)
                        for scope in SCOPES}
        self._clock = -1
        self._lock = threading.RLock()
        self.actions = []
        self.events = []

    def enroll(self, signer, controller, roles, reviewer_scopes=frozenset()):
        """Trusted fixture enrollment; deliberately not exposed as a message."""
        with self._lock:
            if not label(signer.key_id) or not label(controller):
                raise ValueError("identity/controller label required")
            if signer.key_id in self._identities:
                raise ValueError("enrollment cannot replace a key")
            if not set(roles) <= {"authority", "human", "agent", "reviewer"}:
                raise ValueError("unknown role")
            if not set(reviewer_scopes) <= SCOPES.keys():
                raise ValueError("unknown reviewer scope")
            self._identities[signer.key_id] = Identity(
                signer.private_key.public_key(), controller, frozenset(roles),
                frozenset(reviewer_scopes))

    def snapshot(self, scope):
        with self._lock:
            return dict(self._states[scope], open_cases=sorted(self._cases[scope]))

    def recovery_context(self, scope, clearance_ids):
        """Public signing context, never itself permission to resume.

        Random incident challenges prevent approval prepared before an incident.
        Hashes require the human signature to commit to the exact clearances.
        Missing IDs remain visible and will be rejected at the message boundary.
        """
        with self._lock:
            state = self._states[scope]
            return dict(scope=scope, case_id=state["case_id"], epoch=state["epoch"],
                        case_ids=sorted(self._cases[scope]), nonce=state["nonce"],
                        clearance_ids=list(clearance_ids),
                        clearance_hashes={rid: envelope_digest(self._reports[rid]["envelope"])
                                          if rid in self._reports else None for rid in clearance_ids})

    def used(self, grant_id):
        with self._lock:
            return self._used.get(grant_id, 0)

    def _authenticate(self, env):
        require(isinstance(env, Envelope), "invalid_envelope")
        require(label(env.key_id), "invalid_envelope")
        require(env.key_id in self._identities, "unknown_signer")
        require(env.key_id not in self._revoked_keys, "revoked_key")
        require(type(env.body) is bytes and len(env.body) <= 65536 and
                type(env.signature) is bytes, "invalid_envelope")
        try:
            self._identities[env.key_id].public_key.verify(env.signature, env.body)
        except (InvalidSignature, ValueError, TypeError):
            raise Denied("bad_signature") from None
        try:
            payload = json.loads(env.body, object_pairs_hook=unique_object,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError, RecursionError):
            raise Denied("invalid_encoding") from None
        require(type(payload) is dict, "invalid_fields")
        return payload

    def _basic(self, env, now):
        payload = self._authenticate(env)
        require(type(payload.get("protocol")) is int and payload["protocol"] == 1,
                "wrong_protocol")
        require(payload.get("audience") == AUDIENCE, "wrong_audience")
        require(payload.get("signer") == env.key_id, "wrong_signer_binding")
        kind = payload.get("kind")
        require(isinstance(kind, str) and kind in FIELDS, "unsupported_message")
        required, optional = FIELDS[kind]
        require(BASE_FIELDS | required <= payload.keys() and
                payload.keys() <= BASE_FIELDS | required | optional, "invalid_fields")
        require(label(payload["id"]), "invalid_id")
        start, end = payload["issued_at"], payload["expires_at"]
        require(type(start) is int and type(end) is int and 0 <= start < end,
                "invalid_time")
        require(start <= now, "future_message")
        require(now < end, "expired_message")
        key = (env.key_id, payload["id"])
        require(key not in self._seen, "replay")
        # Authenticated attempts, including denied requests, have one-use IDs.
        self._seen.add(key)
        return payload

    def _role(self, env, role):
        require(role in self._identities[env.key_id].roles, "forbidden_role")

    def _scope(self, scope):
        require(isinstance(scope, str) and scope in SCOPES, "unknown_scope")
        return self._states[scope]

    def _open_scope(self, scope, epoch):
        state = self._scope(scope)
        require(state["mode"] != "revoked", "scope_revoked")
        require(state["mode"] != "paused", "scope_paused")
        require(type(epoch) is int and epoch == state["epoch"], "stale_epoch")
        return state

    def _chain(self, grant_id, now):
        require(label(grant_id) and grant_id in self._grants, "unknown_grant")
        chain = []
        current = grant_id
        while current is not None:
            require(current not in [g["id"] for g in chain], "cyclic_delegation")
            require(current in self._grants, "unknown_parent")
            record = self._grants[current]
            grant = record["payload"]
            require(current not in self._revoked_grants, "grant_revoked")
            require(record["issuer"] not in self._revoked_keys and
                    grant["subject"] not in self._revoked_keys, "revoked_key")
            require(grant["issued_at"] <= now < grant["expires_at"], "grant_expired")
            self._open_scope(grant["scope"], grant["epoch"])
            chain.append(grant)
            require(len(chain) <= self.max_depth, "delegation_depth")
            current = grant.get("parent")
        return chain

    def _grant(self, env, p, now):
        require(p["id"] not in self._grants, "duplicate_grant")
        require(label(p["subject"]) and p["subject"] in self._identities,
                "unknown_subject")
        require(p["subject"] not in self._revoked_keys, "revoked_key")
        require("agent" in self._identities[p["subject"]].roles, "invalid_subject_role")
        self._open_scope(p["scope"], p["epoch"])
        resource, allowed = SCOPES[p["scope"]]
        require(p["resource"] == resource, "wrong_resource")
        require(type(p["actions"]) is list and len(p["actions"]) > 0 and
                all(isinstance(a, str) for a in p["actions"]) and
                len(set(p["actions"])) == len(p["actions"]) and
                set(p["actions"]) <= allowed, "bad_actions")
        require(positive_int(p["budget"]), "invalid_budget")
        parent_id = p.get("parent")
        if parent_id is None:
            self._role(env, "authority")
        else:
            require(label(parent_id), "unknown_parent")
            chain = self._chain(parent_id, now)
            parent = chain[0]
            require(len(chain) < self.max_depth, "delegation_depth")
            require(env.key_id == parent["subject"], "not_parent_holder")
            require(p["scope"] == parent["scope"] and p["resource"] == parent["resource"] and
                    set(p["actions"]) <= set(parent["actions"]), "delegation_expands_scope")
            require(p["expires_at"] <= parent["expires_at"], "delegation_expands_expiry")
            require(all(p["budget"] <= g["budget"] - self._used[g["id"]] for g in chain),
                    "delegation_expands_budget")
        self._grants[p["id"]] = {"payload": p, "issuer": env.key_id, "envelope": env}
        self._used[p["id"]] = 0
        return Decision(True, "grant_accepted")

    def _request(self, env, p, now):
        chain = self._chain(p["grant_id"], now)
        grant = chain[0]
        require(env.key_id == grant["subject"], "not_grant_holder")
        require(p["resource"] == grant["resource"], "wrong_resource")
        require(p["action"] in grant["actions"], "action_not_allowed")
        require(positive_int(p["units"]), "invalid_units")
        require(type(p.get("args", {})) is dict, "invalid_arguments")
        require(all(self._used[g["id"]] + p["units"] <= g["budget"] for g in chain),
                "budget_exhausted")
        state = self._states[grant["scope"]]
        if state["mode"] == "trial":
            require(p["units"] <= state["trial_remaining"], "trial_exhausted")
        # This locked section is the only action path: check, charge, record.
        # The ledger is the whole mock side effect; real external tools would
        # need their own idempotency, cancellation and transaction design.
        for ancestor in chain:
            self._used[ancestor["id"]] += p["units"]
        if state["mode"] == "trial":
            state["trial_remaining"] -= p["units"]
        self.actions.append(dict(request_id=p["id"], subject=env.key_id,
                                 grant_id=grant["id"], scope=grant["scope"],
                                 resource=p["resource"], action=p["action"],
                                 units=p["units"], args=p.get("args", {}),
                                 now=now, route="gate"))
        return Decision(True, "executed", p["units"])

    def _revoke(self, env, p, now):
        self._role(env, "authority")
        require(label(p["ref"]), "invalid_reference")
        if p["target"] == "grant":
            require(p["ref"] in self._grants, "unknown_grant")
            self._revoked_grants.add(p["ref"])
        elif p["target"] == "key":
            require(p["ref"] in self._identities, "unknown_signer")
            self._revoked_keys.add(p["ref"])
        elif p["target"] == "scope":
            state = self._scope(p["ref"])
            state.update(mode="revoked", epoch=state["epoch"] + 1, trial_remaining=0)
        else:
            raise Denied("invalid_target")
        return Decision(True, "revoked")

    def _reviewer(self, key_id, scope):
        require(key_id not in self._revoked_keys, "revoked_key")
        identity = self._identities[key_id]
        require("reviewer" in identity.roles and scope in identity.reviewer_scopes,
                "forbidden_reviewer")
        conflicted = {item.controller for item in self._identities.values()
                      if item.roles & {"agent", "authority", "human"}}
        require(identity.controller not in conflicted, "conflicted_witness")
        return identity.controller

    def _fresh_report(self, record, now, scope, case_id, verdict, after=None):
        try:
            env, p = record["envelope"], record["payload"]
            self._authenticate(env)
            controller = self._reviewer(env.key_id, scope)
            require(p["scope"] == scope and p["case_id"] == case_id and
                    p["verdict"] == verdict, "wrong_evidence")
            require(p["issued_at"] <= now < p["expires_at"] and
                    0 <= now - p["observed_at"] <= self.evidence_ttl, "evidence_not_fresh")
            require(after is None or p["observed_at"] > after, "evidence_not_fresh")
            return controller
        except Denied:
            return None

    def _report(self, env, p, now):
        state = self._scope(p["scope"])
        require(state["mode"] != "revoked", "scope_revoked")
        self._reviewer(env.key_id, p["scope"])
        require(label(p["case_id"]) and label(p["rule"]), "invalid_fields")
        require(type(p["affected"]) is list and all(label(x) for x in p["affected"]),
                "invalid_fields")
        require(p["verdict"] in ("unsafe", "safe"), "invalid_verdict")
        require(type(p["observed_at"]) is int and 0 <= p["observed_at"] <= p["issued_at"] and
                now - p["observed_at"] <= self.evidence_ttl, "evidence_not_fresh")
        require(p["id"] not in self._reports, "duplicate_report")
        require((p["scope"], p["case_id"]) not in self._retired_cases, "retired_case")
        if p["verdict"] == "safe":
            require(state["mode"] == "paused" and p["case_id"] in self._cases[p["scope"]], "unknown_case")
            require(p["observed_at"] > self._cases[p["scope"]][p["case_id"]], "evidence_not_fresh")
        self._reports[p["id"]] = dict(envelope=env, payload=p)
        if p["verdict"] == "unsafe":
            # A previously confirmed case requires a NEW quorum of observations.
            # Re-signing one old observation cannot borrow cached co-witnesses
            # to keep rotating the recovery challenge or invalidate clearance.
            after = self._cases[p["scope"]].get(p["case_id"])
            controllers = {c for r in self._reports.values()
                           if (c := self._fresh_report(r, now, p["scope"], p["case_id"], "unsafe", after))}
            if len(controllers) >= self.quorum:
                self._cases[p["scope"]][p["case_id"]] = now
                state.update(mode="paused", epoch=state["epoch"] + 1,
                             case_id=p["case_id"], paused_at=now, trial_remaining=0,
                             nonce=secrets.token_hex(24))
                return Decision(True, "paused")
        return Decision(True, "report_recorded")

    def _recover(self, env, p, now):
        self._role(env, "human")
        state = self._scope(p["scope"])
        require(state["mode"] == "paused", "not_paused")
        require(p["case_id"] == state["case_id"] and
                type(p["epoch"]) is int and p["epoch"] == state["epoch"], "wrong_case_or_epoch")
        require(label(p["nonce"]) and p["nonce"] == state["nonce"], "wrong_recovery_nonce")
        require(p["issued_at"] > state["paused_at"], "stale_human_permission")
        require(positive_int(p["trial_budget"]), "invalid_budget")
        require(type(p["clearance_ids"]) is list and all(label(x) for x in p["clearance_ids"]),
                "invalid_fields")
        case_ids = p.get("case_ids", [p["case_id"]])
        require(type(case_ids) is list and all(label(x) for x in case_ids) and
                len(set(case_ids)) == len(case_ids) and
                set(case_ids) == set(self._cases[p["scope"]]), "unresolved_cases")
        require(type(p["clearance_hashes"]) is dict and
                set(p["clearance_hashes"]) == set(p["clearance_ids"]), "invalid_clearance_binding")
        controllers = {case: set() for case in case_ids}
        for report_id in set(p["clearance_ids"]):
            require(report_id in self._reports, "unknown_clearance")
            record = self._reports[report_id]
            require(p["clearance_hashes"][report_id] == envelope_digest(record["envelope"]),
                    "invalid_clearance_binding")
            case_id = record["payload"]["case_id"]
            require(case_id in controllers, "wrong_evidence")
            require(p["issued_at"] >= record["payload"]["issued_at"], "stale_human_permission")
            controller = self._fresh_report(record, now, p["scope"], case_id, "safe",
                                            self._cases[p["scope"]][case_id])
            require(controller is not None, "invalid_clearance")
            controllers[case_id].add(controller)
        require(all(len(group) >= self.quorum for group in controllers.values()), "insufficient_witnesses")
        self._retired_cases.update((p["scope"], case_id) for case_id in case_ids)
        self._cases[p["scope"]].clear()
        state.update(mode="trial", epoch=state["epoch"] + 1,
                     trial_remaining=p["trial_budget"], nonce=None)
        return Decision(True, "recovered_to_trial")

    def process(self, env, now):
        with self._lock:
            p = None
            try:
                require(type(now) is int and now >= 0 and now >= self._clock, "invalid_clock")
                self._clock = now
                p = self._basic(env, now)
                decision = getattr(self, "_" + p["kind"])(env, p, now)
            except Denied as error:
                decision = Decision(False, str(error))
            self.events.append(dict(now=now, key_id=getattr(env, "key_id", None),
                                    message=p, **decision.to_dict()))
            return decision
