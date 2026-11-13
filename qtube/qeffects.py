"""Evidence-scoped discrete glyph effects, without game code or engine actions.

Glyph state is (colour, cropped binary mask). A rule is scoped by
(level, contact_id, context, guard); context and guard are opaque hashable keys,
not predicates. There is no global meaning for a marker colour or action ID.

Exact observed state transitions, colour mappings, and all compatible D4 laws
are kept separately. Non-D4 geometry remains an exact-state shape lookup.
Conflicts invalidate the affected prediction instead of selecting an arbitrary
rotation. An explicit new context creates a separate rule. Unseen shape changes
and ambiguous poses return unknown. Pose generalization is a hypothesis under
the supplied D4 prior, not a verified universal contact law.

The CLI audits recorded frames through qrecording's pure visual extractors.
Contact attribution uses the observed incoming body's destination footprint;
it is observational attribution, not intervention-confirmed causation. No game
implementation is read, no engine is started, and no model is trained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Hashable

import numpy as np


def _mask(mask) -> np.ndarray:
    value = np.asarray(mask)
    if value.ndim != 2 or not value.size or not np.isin(value, (0, 1)).all() or not value.any():
        raise ValueError("Expected a nonempty two-dimensional binary foreground mask.")
    rows, columns = np.where(value)
    result = value[rows.min():rows.max() + 1, columns.min():columns.max() + 1].astype(np.uint8).copy()
    result.flags.writeable = False
    return result


@dataclass(frozen=True, eq=False)
class GlyphState:
    colour: int
    mask: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "colour", int(self.colour))
        object.__setattr__(self, "mask", _mask(self.mask))

    @property
    def key(self):
        return self.colour, self.mask.shape, self.mask.tobytes()

    def to_dict(self):
        return {"colour": self.colour, "mask": self.mask.tolist()}


def as_state(state) -> GlyphState:
    if isinstance(state, GlyphState):
        return state
    if isinstance(state, dict):
        return GlyphState(state["colour"], state["mask"])
    return GlyphState(*state)


def same_state(left, right) -> bool:
    return as_state(left).key == as_state(right).key


def apply_d4(mask, turn: int) -> np.ndarray:
    """0..3: CCW quarter turns; 4..7: reflect x, then turn."""
    if not 0 <= turn < 8:
        raise ValueError("D4 turn must be an integer from 0 through 7.")
    source = np.fliplr(mask) if turn >= 4 else mask
    return _mask(np.rot90(source, turn % 4))


def matching_turns(before, after) -> set[int]:
    before, after = _mask(before), _mask(after)
    return {turn for turn in range(8)
            if apply_d4(before, turn).shape == after.shape
            and np.array_equal(apply_d4(before, turn), after)}


def classify_effect(before, after) -> dict:
    before, after = as_state(before), as_state(after)
    turns = matching_turns(before.mask, after.mask)
    same_geometry = before.mask.shape == after.mask.shape and np.array_equal(before.mask, after.mask)
    recolour = before.colour != after.colour
    geometry = "identity" if same_geometry else "pose" if turns else "shape_lookup"
    if geometry == "identity":
        kind = "recolor" if recolour else "identity"
    else:
        kind = ("joint_" if recolour else "") + geometry + ("_recolor" if recolour else "")
    return {"kind": kind, "geometry": geometry,
            "colour": "mapping" if recolour else "identity",
            "compatible_d4": sorted(turns)}


@dataclass(frozen=True)
class EffectScope:
    level: Hashable
    contact_id: Hashable
    context: Hashable | None = None
    guard: Hashable | None = None

    def __post_init__(self):
        if self.level is None or self.contact_id is None:
            raise ValueError("A level and explicit object/contact ID are required.")
        for value in (self.level, self.contact_id, self.context, self.guard):
            hash(value)

    def to_dict(self):
        return {"level": self.level, "contact_id": self.contact_id,
                "context": self.context, "guard": self.guard}


@dataclass
class EffectRule:
    scope: EffectScope
    pose_support: set[int] | None = None
    observations: int = 0
    counts: Counter = field(default_factory=Counter)
    colour_counts: dict[int, Counter] = field(default_factory=dict)
    transitions: dict[tuple, Counter] = field(default_factory=dict)
    states: dict[tuple, GlyphState] = field(default_factory=dict)
    invalidations: Counter = field(default_factory=Counter)
    events: list[dict] = field(default_factory=list)

    def observe(self, before, after, provenance=None) -> dict:
        before, after = as_state(before), as_state(after)
        effect = classify_effect(before, after)
        compatible = set(effect["compatible_d4"])
        invalidated = []
        if self.pose_support is None:
            self.pose_support = compatible
        else:
            removed = self.pose_support - compatible
            self.pose_support &= compatible
            for turn in sorted(removed):
                self.invalidations[f"pose:{turn}"] += 1
                invalidated.append(f"pose:{turn}")
        colours = self.colour_counts.setdefault(before.colour, Counter())
        if len(colours) == 1 and after.colour not in colours:
            self.invalidations[f"colour:{before.colour}"] += 1
            invalidated.append(f"colour:{before.colour}")
        outcomes = self.transitions.setdefault(before.key, Counter())
        if len(outcomes) == 1 and after.key not in outcomes:
            self.invalidations["exact_state"] += 1
            invalidated.append("exact_state")
        colours[after.colour] += 1
        outcomes[after.key] += 1
        self.states[before.key], self.states[after.key] = before, after
        self.observations += 1
        self.counts[effect["kind"]] += 1
        event = {**effect, "before": before.to_dict(), "after": after.to_dict(),
                 "support_after": sorted(self.pose_support),
                 "invalidated": invalidated, "provenance": provenance}
        self.events.append(event)
        return event

    def predict(self, state) -> dict:
        state = as_state(state)
        result = {"known": False, "status": "unknown", "next_state": None,
                  "candidates": [], "scope": self.scope.to_dict(),
                  "pose_support": sorted(self.pose_support or set()),
                  "observations": self.observations}
        outcomes = self.transitions.get(state.key)
        if outcomes:
            result["candidates"] = [
                {"state": self.states[key].to_dict(), "support": count}
                for key, count in outcomes.items()]
            if len(outcomes) != 1:
                return {**result, "reason": "conflicting_exact_state_observations"}
            target_key = next(iter(outcomes))
            target = self.states[target_key]
            return {**result, "known": True,
                    "status": "identity" if target.key == state.key else "supported",
                    "next_state": target.to_dict(), "basis": "exact_state_lookup",
                    "effect": classify_effect(state, target), "extrapolated": False}
        colours = self.colour_counts.get(state.colour)
        if not colours:
            return {**result, "reason": "unseen_input_colour"}
        if len(colours) != 1:
            return {**result, "reason": "conflicting_colour_mapping"}
        if not self.pose_support:
            return {**result, "reason": "no_supported_pose_for_unseen_state"}
        colour = next(iter(colours))
        possible = {}
        for turn in sorted(self.pose_support):
            target = GlyphState(colour, apply_d4(state.mask, turn))
            entry = possible.setdefault(target.key, {"state": target, "turns": []})
            entry["turns"].append(turn)
        result["candidates"] = [
            {"state": entry["state"].to_dict(), "turns": entry["turns"],
             "support": self.observations} for entry in possible.values()]
        if len(possible) != 1:
            return {**result, "reason": "compatible_poses_disagree"}
        target = next(iter(possible.values()))["state"]
        return {**result, "known": True,
                "status": "identity" if target.key == state.key else "supported",
                "next_state": target.to_dict(),
                "basis": "pose_consensus_and_observed_colour_mapping",
                "effect": classify_effect(state, target), "extrapolated": True}

    def summary(self) -> dict:
        return {"scope": self.scope.to_dict(), "observations": self.observations,
                "effect_counts": dict(self.counts),
                "pose_support": sorted(self.pose_support or set()),
                "colour_mappings": {str(source): dict(counts)
                                    for source, counts in self.colour_counts.items()},
                "exact_source_states": len(self.transitions),
                "conflicting_exact_source_states": sum(len(c) > 1 for c in self.transitions.values()),
                "invalidations": dict(self.invalidations)}


class EffectBook:
    def __init__(self):
        self.rules: dict[EffectScope, EffectRule] = {}
        self.unknown_observations = 0

    def observe(self, level, contact_id, before, after, *, context=None,
                guard=None, provenance=None) -> dict:
        scope = EffectScope(level, contact_id, context, guard)
        if before is None or after is None:
            self.unknown_observations += 1
            return {"status": "unknown", "reason": "missing_glyph_observation",
                    "scope": scope.to_dict()}
        rule = self.rules.setdefault(scope, EffectRule(scope))
        return rule.observe(before, after, provenance)

    def predict(self, level, contact_id, state, *, context=None, guard=None) -> dict:
        scope = EffectScope(level, contact_id, context, guard)
        if state is None:
            return {"known": False, "status": "unknown", "next_state": None,
                    "reason": "missing_glyph_observation", "scope": scope.to_dict()}
        rule = self.rules.get(scope)
        if rule is None:
            return {"known": False, "status": "unknown", "next_state": None,
                    "reason": "unobserved_scope", "scope": scope.to_dict()}
        return rule.predict(state)

    def summary(self) -> dict:
        return {"rules": [rule.summary() for rule in self.rules.values()],
                "unknown_observations": self.unknown_observations}


def extract_contact_effects(frames, actions, region, core) -> list[dict]:
    """Conservatively attribute changed glyphs to observed destination footprints.

    The supplied core's body extractor defines a 5x5 visible body. Level changes,
    terminal/reset transitions, missing bodies/glyphs, stationary bodies and
    returns to the level's starting body location are excluded. The footprint is
    an observational contact ID; marker colours are retained only as provenance.
    """
    from qrecording import read_glyph

    if len(frames) != len(actions) + 1:
        raise ValueError("Expected one more frame than action records.")
    glyphs = [read_glyph(frame, region, core) for frame in frames]
    bodies = [core.body_pos(frame) for frame in frames]
    events = []
    initial_body = bodies[0]
    for index, record in enumerate(actions):
        level = record.get("levels")
        previous_level = actions[index - 1].get("levels") if index else level
        terminal = str(record.get("state", "")).upper() in {"RESET", "GAME_OVER", "WIN"}
        if int(record.get("a", -1)) == 0 or terminal or level != previous_level:
            initial_body = bodies[index + 1]
            continue
        before, after = glyphs[index:index + 2]
        source, target = bodies[index:index + 2]
        if (level is None or before is None or after is None or source is None
                or target is None or source == target or same_state(before, after)):
            continue
        if target == initial_body:
            continue
        y, x = map(int, target)
        patch = np.asarray(frames[index])[y:y + 5, x:x + 5]
        if patch.shape != (5, 5):
            continue
        events.append({
            "event_index": index, "level": level,
            "contact_id": ("body_footprint", y, x),
            "before": as_state(before), "after": as_state(after),
            "provenance": {"event_index": index, "action": int(record["a"]),
                "source_body": tuple(map(int, source)), "target_body": (y, x),
                "incoming_displacement": tuple(int(b - a) for a, b in zip(source, target)),
                "visible_before_patch": patch.tolist(),
                "attribution": "observed destination body footprint; causation not independently verified"},
        })
    return events


def audit_recording(events: list[dict]) -> dict:
    """Replay evidence, then check aliases and explicit conservative abstentions."""
    book = EffectBook()
    rows = []
    for event in events:
        level, contact = event["level"], event["contact_id"]
        before_prediction = book.predict(level, contact, event["before"])
        update = book.observe(level, contact, event["before"], event["after"],
                              provenance=event["provenance"])
        after_prediction = book.predict(level, contact, event["before"])
        rows.append({"event_index": event["event_index"], "level": level,
                     "contact_id": contact, "classification": update,
                     "prediction_before_observation": before_prediction,
                     "prediction_after_observation": after_prediction})
        assert not after_prediction["known"] or same_state(
            after_prediction["next_state"], event["after"])
    recolours = [event for event in events
                 if classify_effect(event["before"], event["after"])["kind"] == "recolor"]
    reshapes = [event for event in events
                if classify_effect(event["before"], event["after"])["geometry"] == "shape_lookup"]
    poses = [event for event in events
             if classify_effect(event["before"], event["after"])["geometry"] == "pose"]
    checks = {}
    if recolours:
        event = recolours[0]
        conflict = EffectBook()
        conflict.observe(event["level"], event["contact_id"], event["before"], event["after"])
        update = conflict.observe(event["level"], event["contact_id"], event["before"], event["before"])
        prediction = conflict.predict(event["level"], event["contact_id"], event["before"])
        conflict.observe(event["level"], event["contact_id"], event["before"], event["before"],
                         context="explicit-new-context", guard="opaque-guard")
        isolated = conflict.predict(event["level"], event["contact_id"], event["before"],
                                    context="explicit-new-context", guard="opaque-guard")
        checks["synthetic_contradiction_and_context"] = {
            "base_is_unknown": not prediction["known"], "invalidated": update["invalidated"],
            "new_context_identity": isolated["status"] == "identity",
            "base_stays_unknown": not conflict.predict(
                event["level"], event["contact_id"], event["before"])["known"]}
        assert all(checks["synthetic_contradiction_and_context"][key] for key in
                   ("base_is_unknown", "new_context_identity", "base_stays_unknown"))
    if reshapes and poses:
        reshape, pose = reshapes[0], poses[0]
        pose_rule = book.rules[EffectScope(pose["level"], pose["contact_id"])]
        reshape_rule = book.rules[EffectScope(reshape["level"], reshape["contact_id"])]
        unseen = GlyphState(reshape["before"].colour, apply_d4(reshape["before"].mask, 1))
        checks["actual_marker_colour_aliases"] = {
            "pose_scope": pose_rule.summary(), "reshape_scope": reshape_rule.summary(),
            "both_visible_markers_contain_colour_0": all(
                0 in np.asarray(event["provenance"]["visible_before_patch"])
                for event in (pose, reshape)),
            "pose_support_retained": bool(pose_rule.pose_support),
            "reshape_has_no_d4_support": not reshape_rule.pose_support,
            "unseen_reshape_is_unknown": not reshape_rule.predict(unseen)["known"],
            "unobserved_contact_is_unknown": not book.predict(
                pose["level"], ("unseen-contact",), pose["before"])["known"],
        }
        if len(pose_rule.pose_support) > 1:
            probe = GlyphState(pose["before"].colour, reshape["before"].mask)
            ambiguity = pose_rule.predict(probe)
            checks["all_compatible_pose_aliases_preserved"] = {
                "support": sorted(pose_rule.pose_support),
                "prediction": ambiguity}
    alias_pair = next(((left, right) for left in events for right in events
                       if left["level"] == right["level"]
                       and left["contact_id"] != right["contact_id"]
                       and left["before"].colour == right["before"].colour
                       and left["after"].colour != right["after"].colour), None)
    if alias_pair:
        checks["actual_same_colour_different_contacts"] = [
            {"event_index": event["event_index"], "contact_id": event["contact_id"],
             "input_colour": event["before"].colour,
             "observed_output_colour": event["after"].colour,
             "prediction": book.predict(
                 event["level"], event["contact_id"], event["before"])}
            for event in alias_pair]
    if poses and reshapes:
        joint = EffectBook()
        examples = [("pose", poses[0]), ("shape", reshapes[0])]
        checks["synthetic_joint_changes"] = []
        for name, event in examples:
            after = GlyphState((event["before"].colour + 1) % 16, event["after"].mask)
            update = joint.observe("synthetic", name, event["before"], after)
            prediction = joint.predict("synthetic", name, event["before"])
            checks["synthetic_joint_changes"].append({"kind": update["kind"],
                                                       "known": prediction["known"]})
            assert update["kind"].startswith("joint_") and prediction["known"]
    supported_before = [row for row in rows if row["prediction_before_observation"]["known"]]
    return {"observed_effect_counts": dict(Counter(
                classify_effect(event["before"], event["after"])["kind"] for event in events)),
            "recorded_sequence_predictions": {
                "supported_before_observation": len(supported_before),
                "correct_supported_predictions": sum(same_state(
                    row["prediction_before_observation"]["next_state"], row["classification"]["after"])
                    for row in supported_before),
                "unknown_before_observation": len(rows) - len(supported_before)},
            "actual_recolor_event_indices": [event["event_index"] for event in recolours],
            "actual_shape_lookup_event_indices": [event["event_index"] for event in reshapes],
            "checks": checks, "summary": book.summary(), "events": rows}


def main():
    from qrecording import load_demo, load_observation_core

    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npz", type=Path, default=root / "eye/play_ls20.npz")
    parser.add_argument("--jsonl", type=Path, default=root / "eye/play_ls20.jsonl")
    parser.add_argument("--source-dir", type=Path,
                        default=root / "kaggle_push/out_gemma_26b_qtube_v1/planet")
    parser.add_argument("--region", type=int, nargs=4, default=(55, 60, 3, 8))
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("qeffects_results.json"))
    args = parser.parse_args()
    core = load_observation_core(args.source_dir)
    frames, actions = load_demo(args.npz, args.jsonl, args.source_dir)
    events = extract_contact_effects(frames, actions, args.region, core)
    result = {"npz": str(args.npz.resolve()), "jsonl": str(args.jsonl.resolve()),
              "observation_core_sha256": core.source_sha256,
              "region_prior": list(args.region), "training": False,
              "engine_actions": 0, "scope_policy": "level/contact/context/guard; never global colour",
              "limits": ["Destination-footprint contact attribution is observational, not verified causation.",
                         "Shape changes predict only exact observed source states.",
                         "D4 is supplied; pose consensus on unseen shapes remains an evidence-compatible hypothesis.",
                         "Identity is observed evidence, never an unknown-effect default.",
                         "Synthetic consistency checks are reported separately from actual recording evidence."],
              **audit_recording(events)}
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"events", "summary"}}, indent=2))
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
