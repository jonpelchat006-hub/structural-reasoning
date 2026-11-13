"""Read observed ARC-3 recordings and locate a demonstrated object contact.

This helper reads frames, action records, and the existing observation extractors.
It never reads an environment's implementation, starts a game, or trains a model.
The HUD region is an explicit caller-supplied observational prior. Action meanings
and the reverse movement are inferred from recorded body displacements.

    core = load_observation_core(source_dir)
    frames, actions = load_demo(npz_path, jsonl_path, source_dir)
    contact = find_bootstrap(frames, actions, region, core=core)

``contact['prefix']`` contains normalized action dictionaries with ``a/x/y``;
``action_prefix`` is the same prefix as integer action IDs. Both include the
contact event. Glyphs are ``(colour, binary_numpy_mask)`` tuples.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


def load_observation_core(source_dir: str | Path) -> SimpleNamespace:
    """Load only four pure visual extractors from the downloaded planet core.

    Importing all of mika_core also imports its agent, journals, and model stack.
    Compiling this small, explicit set of existing pure functions avoids those
    side effects and does not require torch. WALLS is the extractor's own visual
    exclusion constant, rather than a new navigation rule.
    """
    source_path = Path(source_dir) / "mika_core.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    names = {"shrink", "_ring_colour", "read_glyph", "body_pos"}
    namespace: dict[str, Any] = {"np": np}
    functions = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "WALLS"
                   for target in node.targets):
                namespace["WALLS"] = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            functions.append(node)
    found = {node.name for node in functions}
    if found != names or "WALLS" not in namespace:
        raise ValueError(f"Missing documented visual extractors in {source_path}")
    selected = ast.Module(body=functions, type_ignores=[])
    exec(compile(selected, str(source_path), "exec"), namespace)
    return SimpleNamespace(
        **{name: namespace[name] for name in names},
        source_path=str(source_path.resolve()),
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )


def _reset_record(record: dict[str, Any]) -> bool:
    return (int(record.get("a", -1)) == 0
            or str(record.get("state", "")).upper() == "RESET"
            or str(record.get("why", "")).startswith("reset"))


def _align_records(records: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Old play recordings omitted the RESET record after a game-over frame."""
    if len(records) == count:
        return [dict(record) for record in records]
    expanded = []
    for index, record in enumerate(records):
        expanded.append(dict(record))
        if str(record.get("state", "")).upper() == "GAME_OVER":
            following = records[index + 1] if index + 1 < len(records) else None
            if following is None or not _reset_record(following):
                expanded.append({
                    "a": 0, "x": -1, "y": -1,
                    "n": record.get("n"), "levels": record.get("levels"),
                    "state": "RESET", "why": "reset",
                    "synthesized_reset": True,
                })
    if len(expanded) != count:
        raise ValueError(
            f"Cannot align {len(records)} records to {count} transitions; "
            f"inserting missing post-game-over resets gives {len(expanded)}"
        )
    return expanded


def _normalize_record(record: dict[str, Any], index: int) -> dict[str, Any]:
    result = dict(record)
    action = int(result["a"])
    if not 0 <= action <= 7:
        raise ValueError(f"Invalid action ID at transition {index}: {action}")
    result.update(a=action, x=int(result.get("x", -1)),
                  y=int(result.get("y", -1)), transition_index=index)
    if action == 6 and not (0 <= result["x"] < 64 and 0 <= result["y"] < 64):
        raise ValueError(f"Invalid click coordinates at transition {index}")
    if result.get("levels") is not None:
        result["levels"] = int(result["levels"])
    return result


def load_demo(npz_path: str | Path, jsonl_path: str | Path | None,
              source_dir: str | Path) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Return frames[T+1,H,W] and records[T], including reset transitions.

    NPZ A/X/Y/L/S arrays, when present, are authoritative. F-only play files
    require their JSONL sidecar. source_dir is validated as an observation-core
    source, so callers cannot accidentally supply an environment implementation.
    """
    load_observation_core(source_dir)
    records = None
    with np.load(Path(npz_path), allow_pickle=False) as data:
        frames = data["F"].copy()
        if (frames.ndim != 3 or frames.shape[1:] != (64, 64)
                or len(frames) < 2 or not np.issubdtype(frames.dtype, np.integer)
                or np.any((frames < 0) | (frames > 15))):
            raise ValueError("Expected at least two integer 64x64 frames with colours 0..15")
        count = len(frames) - 1
        if "A" in data.files:
            actions = data["A"]
            if actions.shape != (count,) or not np.issubdtype(actions.dtype, np.integer):
                raise ValueError("Expected one integer action per frame transition")
            for name in ("X", "Y", "L", "S"):
                if name in data.files and data[name].shape != (count,):
                    raise ValueError(f"{name} does not align with frame transitions")
            records = []
            for index, action in enumerate(actions):
                record = {"a": int(action), "x": -1, "y": -1}
                for name, field in (("X", "x"), ("Y", "y"), ("L", "levels")):
                    if name in data.files:
                        record[field] = int(data[name][index])
                if "S" in data.files:
                    state = int(data["S"][index])
                    record["state"] = {0: "NOT_FINISHED", 1: "WIN", 2: "GAME_OVER"}.get(state, str(state))
                if int(action) == 0:
                    record["state"] = "RESET"
                records.append(record)
    if records is None:
        if jsonl_path is None:
            raise ValueError("An F-only recording requires its JSONL action sidecar")
        raw_records = [json.loads(line) for line in Path(jsonl_path).read_text(
            encoding="utf-8").splitlines() if line.strip()]
        records = _align_records(raw_records, count)
    normalized = [_normalize_record(record, index) for index, record in enumerate(records)]
    frames.flags.writeable = False
    return frames, normalized


def read_glyph(frame: np.ndarray, region, core: SimpleNamespace):
    """Read one glyph through the existing observation-only crop/shrink code."""
    values = tuple(int(value) for value in region)
    if len(values) != 4:
        raise ValueError("region must be (y0, y1, x0, x1), inclusive")
    y0, y1, x0, x1 = values
    height, width = np.asarray(frame).shape
    if not (0 <= y0 <= y1 < height and 0 <= x0 <= x1 < width):
        raise ValueError("region lies outside the observation frame")
    glyph = core.read_glyph(frame, values)
    if glyph is None or not np.asarray(glyph[1]).any():
        return None
    return int(glyph[0]), np.asarray(glyph[1], dtype=np.uint8).copy()


def _same_mask(left: np.ndarray, right: np.ndarray) -> bool:
    return left.shape == right.shape and bool(np.array_equal(left, right))


def _d4_matches(before: np.ndarray, after: np.ndarray, core) -> list[dict[str, int]]:
    """Post-hoc geometry diagnostic; these labels never select an action ID."""
    matches = []
    for reflected in (False, True):
        source = np.fliplr(before) if reflected else before
        for quarter_turns in range(4):
            transformed = core.shrink(np.rot90(source, quarter_turns))
            if _same_mask(transformed, after):
                matches.append({"reflection": int(reflected), "ccw_quarter_turns": quarter_turns})
    return matches


def find_bootstrap(frames: np.ndarray, actions: list[dict[str, Any]], region,
                   source_dir: str | Path | None = None, *,
                   core: SimpleNamespace | None = None) -> dict[str, Any] | None:
    """Find the first demonstrated pose change with an observed reverse move.

    Only the initial uninterrupted level segment is scanned. A boundary, death,
    reset, or terminal transition ends the scan. Reverse-action evidence must
    precede the contact and have exactly the negative incoming displacement.
    A replay client must still verify that stepping off and re-entering really
    has the predicted effect; a global inverse movement law is not assumed.
    """
    if len(frames) != len(actions) + 1:
        raise ValueError("Expected exactly one more frame than action records")
    if core is None:
        if source_dir is None:
            raise ValueError("Supply core or source_dir for the visual extractors")
        core = load_observation_core(source_dir)
    initial_level = actions[0].get("levels") if actions else None
    movement_evidence: dict[tuple[int, int], dict[str, Any]] = {}
    initial_body = core.body_pos(frames[0])
    for index, record in enumerate(actions):
        state = str(record.get("state", "")).upper()
        if (_reset_record(record) or state in {"GAME_OVER", "WIN"}
                or (initial_level is not None and record.get("levels") != initial_level)):
            break
        source_body = core.body_pos(frames[index])
        target_body = core.body_pos(frames[index + 1])
        before = read_glyph(frames[index], region, core)
        after = read_glyph(frames[index + 1], region, core)
        displacement = None
        if source_body is not None and target_body is not None:
            displacement = tuple(int(b - a) for a, b in zip(source_body, target_body))
        changed = (before is not None and after is not None
                   and before[0] == after[0] and not _same_mask(before[1], after[1]))
        if changed and displacement not in (None, (0, 0)):
            # A return to the observed initial body location can be an implicit
            # death; do not give that restored glyph to an object operator.
            returned_to_start = target_body == initial_body and target_body != source_body
            matches = _d4_matches(before[1], after[1], core)
            reverse = movement_evidence.get(tuple(-value for value in displacement))
            if matches and reverse is not None and not returned_to_start:
                prefix = [dict(item) for item in actions[:index + 1]]
                return {
                    "event_index": index,
                    "level": initial_level,
                    "prefix": prefix,
                    "action_prefix": [item["a"] for item in prefix],
                    "before_glyph": before,
                    "after_glyph": after,
                    "source_body": tuple(source_body),
                    "target_body": tuple(target_body),
                    "incoming_action": int(record["a"]),
                    "incoming_displacement": displacement,
                    "reverse_action": int(reverse["action"]),
                    "reverse_evidence": dict(reverse),
                    "exact_d4_matches": matches,
                    "condition": "demonstrated object contact, not a global action meaning",
                }
        if displacement not in (None, (0, 0)) and record["a"] != 6:
            movement_evidence.setdefault(displacement, {
                "transition_index": index,
                "action": int(record["a"]),
                "source_body": tuple(source_body),
                "target_body": tuple(target_body),
                "displacement": displacement,
            })
    return None


def _json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--jsonl", type=Path)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--region", type=int, nargs=4, required=True,
                        metavar=("Y0", "Y1", "X0", "X1"))
    args = parser.parse_args()
    core = load_observation_core(args.source_dir)
    frames, actions = load_demo(args.npz, args.jsonl, args.source_dir)
    contact = find_bootstrap(frames, actions, args.region, core=core)
    output = {
        "npz": str(args.npz.resolve()),
        "jsonl": str(args.jsonl.resolve()) if args.jsonl else None,
        "frames": list(frames.shape), "actions": len(actions),
        "source_path": core.source_path, "source_sha256": core.source_sha256,
        "explicit_region_prior": args.region, "bootstrap": contact,
    }
    print(json.dumps(output, default=_json_default, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
