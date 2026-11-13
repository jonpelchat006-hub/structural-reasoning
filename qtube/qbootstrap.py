"""Bounded, demonstration-free acquisition of an observed contact transition.

This module consumes only the client's public frames and available actions.
It probes each initially available noncomplex action once, learns body motion
and the revealed floor colour, then approaches one small enclosed nonfloor
island as an unverified contact hypothesis. A changing display is discovered
from the resulting frames rather than supplied by coordinates.

The existing body observer and its five-cell footprint, four-connected visual
components, a maximum object area, and a short action budget are explicit priors.
No game source, saved demonstration, model training, or network client is used.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
from scipy import ndimage

from qnav import learn_motion, plan_to_box
from qrecording import read_glyph
from qscene import discover_state_display, scan_goal_candidates


class ActiveBootstrapError(RuntimeError):
    """An unsupported visual/navigation hypothesis requires abstention."""

    def __init__(self, message, **evidence):
        super().__init__(message)
        self.evidence = evidence


def _overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _same_mask(a, b):
    return a.shape == b.shape and bool(np.array_equal(a, b))


def contact_object_candidates(frame, body, motion, *, max_object_area=40):
    """Find small nonfloor islands topologically surrounded by observed floor.

    Size/shape do not establish an object's causal role. Visible enclosed panels,
    the body footprint, components reaching the frame edge, and large islands
    are excluded. All remaining islands are returned as hypotheses, not ranked
    by colour, coordinates, or a known operator shape.
    """
    frame = np.asarray(frame)
    size = int(motion["footprint"])
    if frame.ndim != 2 or body is None or size < 1 or max_object_area < 1:
        raise ValueError("Need a frame, observed body, positive footprint and object limit")
    floor = np.isin(frame, motion["floor_colours"])
    bounded_surface = ndimage.binary_fill_holes(floor)
    islands = bounded_surface & ~floor
    y, x = map(int, body)
    body_box = [y, x, y + size - 1, x + size - 1]
    labels, _ = ndimage.label(islands)
    visible_panels = scan_goal_candidates(frame, None)["candidates"]
    candidates, rejected = [], Counter()
    for label, slices in enumerate(ndimage.find_objects(labels), start=1):
        if slices is None:
            continue
        rows, columns = slices
        component = labels[slices] == label
        area = int(component.sum())
        box = [int(rows.start), int(columns.start), int(rows.stop - 1), int(columns.stop - 1)]
        if _overlap(box, body_box):
            rejected["body_overlap"] += 1
            continue
        if (box[0] == 0 or box[1] == 0 or box[2] == frame.shape[0] - 1
                or box[3] == frame.shape[1] - 1):
            rejected["frame_edge"] += 1
            continue
        if any(_overlap(box, panel["box"]) for panel in visible_panels):
            rejected["visible_enclosed_panel"] += 1
            continue
        if area > max_object_area:
            rejected["area_above_observation_prior"] += 1
            continue
        colours, counts = np.unique(frame[slices][component], return_counts=True)
        candidates.append({
            "box": box, "area": area,
            "colour_counts": {int(colour): int(count) for colour, count in zip(colours, counts)},
            "confirmed_contact_operator": False,
            "evidence": {
                "enclosed_by_observed_floor": True,
                "floor_colours": list(map(int, motion["floor_colours"])),
                "maximum_object_area_prior": int(max_object_area),
                "body_overlap": False, "visible_panel_overlap": False,
                "interpretation": "small unknown island; approach is an unverified contact probe",
            },
        })
    candidates.sort(key=lambda value: tuple(value["box"]))
    return {"candidates": candidates, "rejected": dict(rejected),
            "floor_colours": list(map(int, motion["floor_colours"])),
            "footprint": size, "maximum_object_area_prior": int(max_object_area)}


def _action_ids(client):
    return [int(action["a"] if isinstance(action, dict) else action) for action in client.actions]


def _audit(client, record):
    if callable(getattr(client, "write", None)):
        client.write(record)


def _is_d4_transition(before, after):
    return any(_same_mask(np.rot90(np.fliplr(before) if reflected else before, turns), after)
               for reflected in (False, True) for turns in range(4))


def active_bootstrap(client, core, *, max_actions=20, footprint=5,
                     max_object_area=40) -> dict[str, Any]:
    """Acquire one contact event from a fresh client's own observations.

    client supplies frames, actions, last, and step(action, phase=, prediction=).
    Predictions are descriptive probe/navigation hypotheses; the caller's step
    implementation must log them before its environment action. This helper
    returns the qrecording bootstrap schema plus motion and visual audit data.
    Unsupported or ambiguous evidence raises ActiveBootstrapError.
    """
    if len(client.actions) != 0 or len(client.frames) != 1:
        raise ValueError("Active bootstrap requires a fresh client with no prior actions")
    if max_actions < 1 or footprint < 1:
        raise ValueError("Action budget and body footprint must be positive")
    fixed_level = int(client.last["levels_completed"])
    if core.body_pos(client.frames[-1]) is None:
        raise ActiveBootstrapError("The initial frame has no supported body observation")
    object_scan = None
    motion = None
    probe_actions = sorted({int(action) for action in client.last.get("available_actions", [])
                            if 1 <= int(action) <= 5})
    if not probe_actions:
        raise ActiveBootstrapError("No available noncomplex action supports this bootstrap")

    def bounded_step(action, phase, prediction):
        if len(client.actions) >= max_actions:
            raise ActiveBootstrapError("Active bootstrap action budget exhausted", max_actions=max_actions)
        if int(action) not in [int(a) for a in client.last.get("available_actions", [])]:
            raise ActiveBootstrapError("An observed action is no longer available", action=int(action))
        frame = client.step(int(action), phase=phase, prediction=prediction)
        if (int(client.last["levels_completed"]) != fixed_level
                or client.last.get("state") != "NOT_FINISHED" or client.last.get("full_reset")):
            raise ActiveBootstrapError("Episode/level boundary invalidates active bootstrap",
                                       action=int(action), state=client.last.get("state"))
        if core.body_pos(frame) is None:
            raise ActiveBootstrapError("The new frame has no supported body observation", action=int(action))
        return frame

    def finish_if_display_changed():
        nonlocal motion
        if len(client.frames) < 2:
            return None
        discovery = discover_state_display(np.asarray(client.frames), body_pos=core.body_pos)
        region = discovery["region"]
        if region is None:
            return None
        before = read_glyph(client.frames[-2], region, core)
        after = read_glyph(client.frames[-1], region, core)
        if before is None or after is None:
            raise ActiveBootstrapError("Discovered display cannot be read at the contact")
        if _same_mask(before[1], after[1]) and before[0] == after[0]:
            return None
        if before[0] != after[0] or not _is_d4_transition(before[1], after[1]):
            raise ActiveBootstrapError("First display change is outside the pose-only bootstrap")
        motion = learn_motion(client.frames, _action_ids(client), core.body_pos, footprint=footprint)
        source = tuple(core.body_pos(client.frames[-2]))
        target = tuple(core.body_pos(client.frames[-1]))
        delta = tuple(int(b - a) for a, b in zip(source, target))
        incoming = _action_ids(client)[-1]
        if delta == (0, 0) or motion["moves"].get(incoming) != delta:
            raise ActiveBootstrapError("Changing display is not paired with a supported contact movement")
        reverse_evidence = next((entry for entry in motion["evidence"][:-1]
                                 if tuple(entry["delta"]) == tuple(-v for v in delta)), None)
        if reverse_evidence is None:
            raise ActiveBootstrapError("No earlier observed reverse displacement supports stepping off")
        reverse_action = int(reverse_evidence["action"])
        reverse = {
            "transition_index": int(reverse_evidence["transition"]),
            "action": reverse_action,
            "source_body": tuple(reverse_evidence["from"]),
            "target_body": tuple(reverse_evidence["to"]),
            "displacement": tuple(reverse_evidence["delta"]),
        }
        prefix = [{"a": action, "x": -1, "y": -1, "levels": fixed_level,
                   "transition_index": index} for index, action in enumerate(_action_ids(client))]
        result = {
            "event_index": len(client.actions) - 1, "level": fixed_level,
            "prefix": prefix, "action_prefix": _action_ids(client),
            "before_glyph": before, "after_glyph": after,
            "source_body": source, "target_body": target,
            "incoming_action": incoming, "incoming_displacement": delta,
            "reverse_action": reverse_action, "reverse_evidence": reverse,
            "region": tuple(region), "display_discovery": discovery,
            "object_candidates": object_scan,
            "motion": motion, "probe_actions": probe_actions,
            "condition": "active observed contact hypothesis; no saved demonstration",
            "observation_priors": {"body_footprint": footprint,
                                   "maximum_object_area": max_object_area,
                                   "maximum_bootstrap_actions": max_actions},
        }
        _audit(client, {"phase": "active_bootstrap_complete", "event_index": result["event_index"],
                        "region": list(region), "source_body": list(source), "target_body": list(target),
                        "incoming_action": incoming, "reverse_action": reverse_action,
                        "actions": len(client.actions)})
        return result

    # No direction is attached to these IDs. Each is exercised exactly once in
    # the current state, and later navigation uses only observed displacements.
    for action in probe_actions:
        bounded_step(action, "active_bootstrap:action_probe", {
            "kind": "unknown_noncomplex_action_probe", "action": action,
            "body_before": list(core.body_pos(client.frames[-1])),
        })
        found = finish_if_display_changed()
        if found is not None:
            return found
    motion = learn_motion(client.frames, _action_ids(client), core.body_pos, footprint=footprint)
    if not motion["moves"]:
        raise ActiveBootstrapError("Action probes produced no consistent nonzero movements")
    object_scan = contact_object_candidates(client.frames[-1], core.body_pos(client.frames[-1]),
                                             motion, max_object_area=max_object_area)
    _audit(client, {"phase": "active_bootstrap_hypotheses", "motion": motion,
                    "object_scan": object_scan})
    if len(object_scan["candidates"]) != 1:
        raise ActiveBootstrapError("Small enclosed contact-object hypothesis is not unique",
                                   object_scan=object_scan)
    candidate = object_scan["candidates"][0]
    remaining = max_actions - len(client.actions)
    path = plan_to_box(client.frames[-1], core.body_pos(client.frames[-1]), candidate["box"],
                       motion, max_steps=remaining)
    if path is None:
        raise ActiveBootstrapError("No supported bounded route reaches the contact-object hypothesis",
                                   object_candidate=candidate)
    for planned in path:
        before_body = core.body_pos(client.frames[-1])
        if tuple(before_body) != tuple(planned["from"]):
            raise ActiveBootstrapError("Current body position contradicts the proposed route")
        frame = bounded_step(planned["action"], "active_bootstrap:contact_approach", {
            "body_to": planned["to"], "target_probe": planned["target_probe"],
            "object_box": candidate["box"], "confirmed_operator": False,
        })
        if tuple(core.body_pos(frame)) != tuple(planned["to"]):
            raise ActiveBootstrapError("An approach step contradicts the learned motion hypothesis",
                                       planned=planned, observed_body=list(core.body_pos(frame)))
        found = finish_if_display_changed()
        if found is not None:
            return found
    raise ActiveBootstrapError("Reached the object hypothesis without an identifiable display pose change",
                               object_scan=object_scan, actions=len(client.actions))
