"""Conservative one-step experiment controller for already-reached test sites.

Requires a central, target-specific observer and a current, bound condition.
No navigation, delayed effects, relation/ring matching, or click actions yet.
The send callback is injected; this module never contacts an API on its own.
"""
from copy import deepcopy
import hashlib
import math
import numpy as np

from diagonal import _reads


class ExperimentBlocked(ValueError):
    pass


class ExperimentExecutor:
    def __init__(self):
        self._attempted = set()

    def run(self, proposal, question, frame, *, expected_version, current_version,
            current_scope, available_actions, remaining_actions, at_foot, observer,
            send, body_pos=None, reserve=1):
        """Return one observation delta, or explicit uncertainty after dispatch.

        `observer` comes from the central world model, NEVER from a helper reply.
        `send(action)` returns {frame: 2-D array, scope: game/level, action: int}.
        A transport error consumes the attempt; uncertain actions are not retried.
        """
        if current_scope != question["scope"] or str(current_version) != str(expected_version):
            raise ExperimentBlocked("stale scope or frame version")
        if question["status"] != "open" or proposal["question_id"] != question["id"] or proposal["pin_id"] != question["pin_id"]:
            raise ExperimentBlocked("wrong or closed question")
        if (proposal.get("status") != "needs_execution_validation" or proposal.get("evidence_status") != "unverified_proposal"
                or proposal.get("blockers") or question.get("blockers")):
            raise ExperimentBlocked("unresolved proposal prerequisites")
        if not at_foot:
            raise ExperimentBlocked("test site has not been reached")
        if (remaining_actions is None or not math.isfinite(remaining_actions) or reserve < 0
                or not math.isfinite(reserve) or remaining_actions < 1 + reserve):
            raise ExperimentBlocked("unknown or insufficient action budget")
        pin = question["pin"]
        condition = pin.get("condition")
        if (not condition or condition.get("kind") != "back_pattern" or proposal["condition"] != condition
                or type(question["condition_present"]) is not bool
                or proposal["condition_present"] is not question["condition_present"]
                or proposal["expected_effect"] != pin["effect"]):
            raise ExperimentBlocked("unsupported or changed condition/effect")
        before = np.array(frame, copy=True)
        if before.ndim != 2 or not np.issubdtype(before.dtype, np.integer) or np.any((before < 0) | (before > 15)):
            raise ExperimentBlocked("invalid game frame")
        present = _reads(before, condition, body_pos)
        if present is None or present != question["condition_present"]:
            raise ExperimentBlocked("required condition is not observed here")
        controls = proposal["candidate_controls"]
        if (not controls or any(type(a) is not int or a not in pin["front"] for a in controls)
                or len(set(controls)) != len(controls)):
            raise ExperimentBlocked("unbound controls")
        candidates = [a for a in controls if a in available_actions and 1 <= a <= 5]
        if not candidates:
            raise ExperimentBlocked("no available supported action")
        if not observer or observer.get("target") != pin["effect"]["target"]:
            raise ExperimentBlocked("central target observer missing")
        observer = deepcopy(observer)
        box = observer.get("box", [])
        if len(box) != 4 or any(type(v) is not int for v in box):
            raise ExperimentBlocked("invalid observer coordinates")
        y0, y1, x0, x1 = box
        if not (0 <= y0 <= y1 < before.shape[0] and 0 <= x0 <= x1 < before.shape[1]):
            raise ExperimentBlocked("observer is outside the frame")
        if observer.get("kind") != "pattern_appeared":
            raise ExperimentBlocked("only an instantaneous target-pattern observer is supported")
        pattern = np.asarray(observer.get("pattern"))
        if pattern.shape != (y1 - y0 + 1, x1 - x0 + 1):
            raise ExperimentBlocked("observer pattern shape mismatch")
        if np.array_equal(before[y0:y1 + 1, x0:x1 + 1], pattern):
            raise ExperimentBlocked("target effect is already present")
        key = (question["id"], str(current_version), hashlib.sha256(before.tobytes()).hexdigest())
        if key in self._attempted:
            raise ExperimentBlocked("this question/state already dispatched an experiment")
        self._attempted.add(key)  # consume BEFORE sending; failures may be ambiguous
        action = candidates[0]
        base = {"question_id": question["id"], "pin_id": question["pin_id"], "scope": current_scope,
                "before_version": str(current_version), "action": action, "condition_present": present,
                "observer": observer, "evidence_delta": None, "causal_confirmation": False}
        try:
            response = send(action)
            after = np.asarray(response["frame"])
            if (response.get("scope") != current_scope or type(response.get("action")) is not int
                    or response["action"] != action or after.shape != before.shape
                    or not np.issubdtype(after.dtype, np.integer) or np.any((after < 0) | (after > 15))):
                return {**base, "status": "inconclusive", "reason": "response action, scope, or frame changed unexpectedly"}
            fired = bool(np.array_equal(after[y0:y1 + 1, x0:x1 + 1], pattern))
            field = ("fired" if fired else "silent") + ("_with" if present else "_without")
            return {**base, "status": "observed", "target_pattern_appeared": fired,
                    "after_digest": hashlib.sha256(after.tobytes()).hexdigest(), "evidence_delta": {field: 1}}
        except Exception as e:
            return {**base, "status": "uncertain", "reason": f"{type(e).__name__}: {e}"}
