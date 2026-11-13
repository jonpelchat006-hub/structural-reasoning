"""Frame-only enclosed-glyph candidates for an experimental ARC-3 goal.

No target coordinates, target colours, or game implementation are consulted.
Four-connected colour components supply enclosing boxes; contrasting pixels
must lie inside holes in that component. Shape agreement is a D4 compatibility
hypothesis, not evidence that the environment recognizes the box as its goal.

    candidates = detect_goal_candidates(frame, (colour, mask), hud_region=region)
    hypothesis = select_unambiguous(candidates)

Boxes use inclusive [y0, x0, y1, x1]. hud_region uses the existing extractor's
inclusive [y0, y1, x0, x1] convention. body_box, when supplied from observations,
uses the box convention. The default selector requires unchanged glyph colour
and exact pose compatibility, because a quaternion cannot recolour or reshape.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage


def _overlap(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _shrink(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Tight crop, then remove a directly observed uniform 3x or 2x scale."""
    mask = np.asarray(mask, dtype=np.uint8)
    ys, xs = np.where(mask)
    if not len(ys):
        return mask, 1
    mask = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    for scale in (3, 2):
        if all(length % scale == 0 for length in mask.shape):
            reduced = mask.reshape(mask.shape[0] // scale, scale,
                                   mask.shape[1] // scale, scale).mean(axis=(1, 3))
            if ((reduced == 0) | (reduced == 1)).all():
                return reduced.astype(np.uint8), scale
    return mask, 1


def _same_mask(a, b) -> bool:
    return a.shape == b.shape and bool(np.array_equal(a, b))


def _matching_turns(source, target) -> list[dict[str, int]]:
    matches = []
    for reflected in (False, True):
        value = np.fliplr(source) if reflected else source
        for turns in range(4):
            if _same_mask(np.rot90(value, turns), target):
                matches.append({"reflection": int(reflected), "ccw_quarter_turns": turns})
    return matches


def scan_goal_candidates(frame: np.ndarray, current_glyph, *, hud_region=None,
                         body_box=None) -> dict[str, Any]:
    """Return candidates plus component rejection diagnostics.

    A supplied HUD crop is excluded by overlap, including its surrounding panel.
    Complete monochrome rectangles and open floor/wall shapes fail enclosure.
    Components reaching the frame edge are treated as unbounded backgrounds.
    One-cell glyphs and tiny rings are excluded as visually trivial. This is an
    explicit perception restriction; detecting a target with such a glyph would
    require a different hypothesis class, as would a target on the frame edge.
    """
    frame = np.asarray(frame)
    if frame.ndim != 2 or not np.issubdtype(frame.dtype, np.integer):
        raise ValueError("Expected a two-dimensional integer observation frame")
    current_colour, current_mask = None, None
    if current_glyph is not None:
        current_colour, current_mask = current_glyph
        current_mask = np.asarray(current_mask, dtype=np.uint8)
        if current_mask.ndim != 2 or not current_mask.any():
            raise ValueError("Expected a nonempty binary current glyph mask")
        current_mask, _ = _shrink(current_mask)
    hud_box = None
    if hud_region is not None:
        y0, y1, x0, x1 = map(int, hud_region)
        hud_box = [y0, x0, y1, x1]
    candidates, rejected = [], Counter()
    component_count = 0
    for colour in np.unique(frame):
        labels, _ = ndimage.label(frame == colour)
        for label, slices in enumerate(ndimage.find_objects(labels), start=1):
            if slices is None:
                continue
            component_count += 1
            row, column = slices
            height, width = row.stop - row.start, column.stop - column.start
            if min(height, width) < 3:
                rejected["too_small_to_enclose_glyph"] += 1
                continue
            box = [int(row.start), int(column.start), int(row.stop - 1), int(column.stop - 1)]
            if (box[0] == 0 or box[1] == 0 or box[2] == frame.shape[0] - 1
                    or box[3] == frame.shape[1] - 1):
                # A canvas background around a filled floor patch is also a
                # topological enclosure. Require a bounded visible object.
                rejected["frame_edge_component"] += 1
                continue
            if hud_box is not None and _overlap(box, hud_box):
                rejected["hud_overlap"] += 1
                continue
            if body_box is not None and _overlap(box, body_box):
                rejected["body_overlap"] += 1
                continue
            tile = frame[slices]
            component = labels[slices] == label
            contrast = tile != colour
            if not contrast.any():
                rejected["no_contrasting_glyph"] += 1
                continue
            glyph_colours = np.unique(tile[contrast])
            if len(glyph_colours) != 1:
                rejected["multiple_contrasting_colours"] += 1
                continue
            holes = ndimage.binary_fill_holes(component) & ~component
            if not bool(holes[contrast].all()):
                rejected["contrast_not_enclosed"] += 1
                continue
            mask, scale = _shrink(contrast)
            if mask.size < 4 or int(mask.sum()) < 2:
                rejected["trivial_glyph"] += 1
                continue
            matches = _matching_turns(current_mask, mask) if current_mask is not None else []
            glyph_colour = int(glyph_colours[0])
            perimeter = np.concatenate((tile[0], tile[-1], tile[1:-1, 0], tile[1:-1, -1]))
            candidates.append({
                "box": box,
                "centre": [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2],
                "box_colour": int(colour),
                "glyph": (glyph_colour, mask),
                "shape_compatible": bool(matches) if current_mask is not None else None,
                "colour_matches": glyph_colour == int(current_colour) if current_colour is not None else None,
                "pose_matches": _same_mask(current_mask, mask) if current_mask is not None else None,
                "d4_matches": matches,
                "confirmed_goal": False,
                "evidence": {
                    "colour_component_encloses_all_contrasting_pixels": True,
                    "contrasting_colour_count": 1,
                    "component_pixels": int(component.sum()),
                    "glyph_pixels": int(contrast.sum()),
                    "glyph_cells": int(mask.sum()),
                    "observed_uniform_scale": scale,
                    "perimeter_fraction_box_colour": float((perimeter == colour).mean()),
                    "hud_overlap": False,
                    "body_overlap": False if body_box is not None else "not_supplied; enclosure rejects split-colour body blocks",
                    "interpretation": "visible enclosed glyph; D4 agreement is a compatibility hypothesis",
                },
            })
    candidates.sort(key=lambda item: tuple(item["box"]))
    return {"candidates": candidates, "rejected": dict(rejected),
            "components_scanned": component_count}


def detect_goal_candidates(frame: np.ndarray, current_glyph, *, hud_region=None,
                           body_box=None) -> list[dict[str, Any]]:
    """Return plausible visible boxes, including incompatible shape/colour cases."""
    return scan_goal_candidates(frame, current_glyph, hud_region=hud_region,
                                body_box=body_box)["candidates"]


def select_unambiguous(candidates, *, require_same_colour=True,
                       require_shape_compatible=True) -> dict[str, Any] | None:
    """Select exactly one qualifying hypothesis; never resolve ties by location."""
    eligible = [candidate for candidate in candidates
                if (not require_same_colour or candidate["colour_matches"])
                and (not require_shape_compatible or candidate["shape_compatible"])]
    return eligible[0] if len(eligible) == 1 else None


def discover_state_display(frames, body_pos=None) -> dict[str, Any]:
    """Distinguish a changing display from a constant compatible visible panel.

    The changing panel must retain its component box and border colour through
    every supplied frame, retain glyph colour, and show a nonidentity D4 change.
    At each change, a separate compatible panel must be observed on both sides
    with a constant glyph. This discovers a display *hypothesis* without a HUD
    location prior; it does not prove causality or goal semantics.

    body_pos may be an existing frame-to-body observer. A two-coordinate result
    excludes boxes containing that observed body anchor; a four-coordinate box
    excludes overlap. No movement meaning or body dimensions are inferred here.
    The result always includes region (None on abstention) and audit evidence.
    """
    frames = np.asarray(frames)
    if frames.ndim != 3 or len(frames) < 2:
        raise ValueError("Display discovery requires at least two consecutive frames")
    groups = {}
    for frame_index, frame in enumerate(frames):
        body = body_pos(frame) if callable(body_pos) else None
        for candidate in scan_goal_candidates(frame, None)["candidates"]:
            box = candidate["box"]
            if body is not None:
                if len(body) == 4 and _overlap(box, body):
                    continue
                if (len(body) == 2 and box[0] <= body[0] <= box[2]
                        and box[1] <= body[1] <= box[3]):
                    continue
            key = (tuple(box), candidate["box_colour"])
            group = groups.setdefault(key, {"box": box, "box_colour": candidate["box_colour"],
                                            "observations": {}})
            group["observations"][frame_index] = candidate["glyph"]

    constants, dynamics, panels = [], [], []
    for key, group in groups.items():
        observations = group["observations"]
        indexes = sorted(observations)
        first_colour, first_mask = observations[indexes[0]]
        stable_colour = all(observations[i][0] == first_colour for i in indexes)
        constant = stable_colour and all(_same_mask(observations[i][1], first_mask) for i in indexes)
        compatible = stable_colour and all(_matching_turns(first_mask, observations[i][1]) for i in indexes)
        changes = []
        for index in indexes:
            if index - 1 not in observations:
                continue
            before_colour, before = observations[index - 1]
            after_colour, after = observations[index]
            if before_colour == after_colour and not _same_mask(before, after):
                changes.append({"before_frame": index - 1, "after_frame": index,
                                "d4_matches": _matching_turns(before, after)})
        panel = {"box": group["box"], "box_colour": group["box_colour"],
                 "observed_frames": indexes, "glyph_colour": first_colour,
                 "first_glyph": first_mask.tolist(),
                 "stable_glyph_colour": stable_colour,
                 "constant_glyph": constant,
                 "all_glyphs_d4_compatible": bool(compatible),
                 "present_every_frame": len(indexes) == len(frames),
                 "changes": changes}
        panels.append(panel)
        item = (key, group, panel)
        if constant and len(indexes) >= 2:
            constants.append(item)
        if (len(indexes) == len(frames) and compatible and changes
                and all(change["d4_matches"] for change in changes)):
            dynamics.append(item)

    eligible = []
    for dynamic_key, dynamic_group, dynamic_panel in dynamics:
        dynamic_mask = next(iter(dynamic_group["observations"].values()))[1]
        witness_panels = []
        for constant_key, constant_group, constant_panel in constants:
            if constant_key == dynamic_key:
                continue
            constant_mask = next(iter(constant_group["observations"].values()))[1]
            if not _matching_turns(dynamic_mask, constant_mask):
                continue
            witnessed = [change for change in dynamic_panel["changes"]
                         if change["before_frame"] in constant_group["observations"]
                         and change["after_frame"] in constant_group["observations"]]
            if witnessed:
                witness_panels.append({"box": constant_panel["box"],
                                       "box_colour": constant_panel["box_colour"],
                                       "constant_glyph_colour": constant_panel["glyph_colour"],
                                       "witnessed_changes": witnessed})
        covered_changes = {(change["before_frame"], change["after_frame"])
                           for witness in witness_panels for change in witness["witnessed_changes"]}
        if all((change["before_frame"], change["after_frame"]) in covered_changes
               for change in dynamic_panel["changes"]):
            eligible.append({"panel": dynamic_panel, "constant_compatible_panels": witness_panels})
    result = {
        "region": None, "panel_box": None, "panel_colour": None,
        "frames_observed": len(frames), "eligible_display_count": len(eligible),
        "ambiguous": len(eligible) > 1, "panels": panels,
        "eligible_displays": eligible,
        "interpretation": "changing display hypothesis with constant compatible panel; unconfirmed semantics",
    }
    if len(eligible) == 1:
        panel = eligible[0]["panel"]
        y0, x0, y1, x1 = panel["box"]
        result.update(region=(y0 + 1, y1 - 1, x0 + 1, x1 - 1),
                      panel_box=panel["box"], panel_colour=panel["box_colour"],
                      evidence=eligible[0], status="selected")
    else:
        result["status"] = "ambiguous" if eligible else "insufficient_observed_change"
    return result


def _json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--actions", type=Path)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--region", type=int, nargs=4, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from qrecording import load_demo, load_observation_core
    core = load_observation_core(args.source_dir)
    with np.load(args.frames, allow_pickle=False) as data:
        if "A" in data.files and "L" not in data.files and args.actions is None:
            frames = data["F"].copy()
            frame_levels = ["fresh_run"] * len(frames)
        else:
            frames, actions = load_demo(args.frames, args.actions, args.source_dir)
            frame_levels = [actions[0].get("levels", "unknown")] + [row.get("levels", "unknown") for row in actions]
    by_level = defaultdict(lambda: {
        "frames": 0, "invalid_glyph_frames": 0,
        "candidate_counts": Counter(), "compatible_counts": Counter(),
        "pose_only_selectable_frames": 0, "rejected": Counter(),
        "first_example": None,
    })
    for frame_index, (frame, level) in enumerate(zip(frames, frame_levels)):
        entry = by_level[str(level)]
        entry["frames"] += 1
        glyph = core.read_glyph(frame, args.region)
        if glyph is None:
            entry["invalid_glyph_frames"] += 1
            continue
        body = core.body_pos(frame)
        # The existing observer recognizes a five-cell body block. This is a
        # supplied perception prior, not a target location or movement rule.
        body_box = [body[0], body[1], body[0] + 4, body[1] + 4] if body else None
        result = scan_goal_candidates(frame, glyph, hud_region=args.region, body_box=body_box)
        candidates = result["candidates"]
        entry["candidate_counts"][len(candidates)] += 1
        entry["compatible_counts"][sum(c["shape_compatible"] for c in candidates)] += 1
        entry["pose_only_selectable_frames"] += int(select_unambiguous(candidates) is not None)
        entry["rejected"].update(result["rejected"])
        if entry["first_example"] is None:
            entry["first_example"] = {
                "frame_index": frame_index, "current_glyph": glyph,
                "candidates": candidates,
            }
    result = {"frames_path": str(args.frames.resolve()), "region_prior": args.region,
              "scope": "observed enclosed-glyph hypotheses; no goal identity or environment success labels",
              "levels": dict(by_level)}
    text = json.dumps(result, default=_json_default, indent=2, allow_nan=False)
    if args.output:
        # Avoid overwriting another experiment's evidence.
        with args.output.open("x", encoding="utf-8") as output:
            output.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
