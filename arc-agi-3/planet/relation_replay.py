"""Recorded-frame matcher audit, NOT a counterfactual game or score evaluation.

The caller supplies the source, HUD region and target identified in a failure
log. Previous-level HUD masks reconstruct the carried structural prior. No
actions are sent, and no claim is made about outcomes of a different action.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import relations
import touch
from evaluation_batch import atomic_json


def audit(base, level, region, source, target, prior_colour):
    with np.load(str(base) + ".npz", allow_pickle=False) as data:
        frames = data["F"]
    with open(str(base) + ".jsonl", encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if len(frames) != len(rows) + 1:
        raise ValueError("one before/after frame per record required")
    # Only same-level transitions; exclude resets and cross-level boundary frames.
    before_levels = [0] + [row["levels"] for row in rows[:-1]]
    indices = [i for i, row in enumerate(rows) if before_levels[i] == row["levels"] == level and 1 <= row["a"] <= 7]
    previous = [i for i, row in enumerate(rows) if before_levels[i] == row["levels"] == level - 1 and 1 <= row["a"] <= 7]
    if not indices or not previous:
        raise ValueError("current and previous level recordings required")
    states = []
    for i in previous:
        mask, _ = relations.pattern(frames[i], region, set(), colour=prior_colour)
        if mask is not None and not any(np.array_equal(mask, s) for s in states):
            states.append(mask)
    objects = touch.objects_of(frames[indices[0]], set(), [], np.zeros_like(frames[0], bool))
    dst = next(o for o in objects if o["id"] == target)
    prior = {"region": region, "colour": prior_colour, "states": states,
             "src_colour": int(source.split("@")[0]), "target_colours": {dst["colour"]}}
    carried = next(r for r in relations.carry([prior], frames[indices[0]], objects, set())
                   if r["src"] == source and any(t["id"] == target for t in r["targets"]))
    carried = {**carried, "targets": [t for t in carried["targets"] if t["id"] == target]}
    old = {**carried, "colour": prior_colour}
    y0, y1, x0, x1 = region
    seen, examples = set(), []
    old_matches = new_matches = matching_rotations = changes = 0
    for i in indices:
        f, g = frames[i], frames[i + 1]
        roi = f[y0:y1 + 1, x0:x1 + 1]
        seen.add(roi.tobytes())
        changed = not np.array_equal(roi, g[y0:y1 + 1, x0:x1 + 1])
        before = bool(relations.matched(f, old, set()))
        after = bool(relations.matched(f, carried, set()))
        old_matches += before; new_matches += after; changes += changed
        if after and changed:
            matching_rotations += 1
            examples.append({"press": rows[i]["n"], "action": rows[i]["a"], "why": rows[i].get("why"),
                             "old_match": before, "rebound_match": after})
    return {"kind": "recorded_matcher_diagnostic_not_game_score", "recording": str(base),
            "completed_levels": level, "region": region, "source": source, "target": target,
            "previous_colour": prior_colour, "rebound_colour": carried["colour"],
            "prior_states": len(states), "actions": len(indices), "distinct_region_states": len(seen),
            "region_changes": changes, "old_matching_frames": old_matches,
            "rebound_matching_frames": new_matches, "rotations_away_from_match": matching_rotations,
            "examples": examples, "limitation": "Matcher-only replay; alternative routes, action savings and level wins remain untested."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("--level", type=int, required=True, help="levels already completed")
    parser.add_argument("--region", type=int, nargs=4, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--prior-colour", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.base, args.level, args.region, args.source, args.target, args.prior_colour)
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2))
