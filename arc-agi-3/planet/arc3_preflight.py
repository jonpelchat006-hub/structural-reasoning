"""Read-only recording manifest for offline transition evaluation, not RHAE.

This does not train, run a game, obtain credentials, or submit a scorecard.
Do not feed arbitrary debug NPZ files to induce.load_game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np


def inspect_recording(path):
    path = Path(path)
    result = {"path": str(path.resolve()), "valid": False}
    try:
        with np.load(path, allow_pickle=False) as z:
            missing = sorted({"F", "A", "X", "Y"} - set(z.files))
            if missing:
                return {**result, "reason": "missing transition arrays", "missing": missing}
            f, a, x, y = (z[k] for k in ("F", "A", "X", "Y"))
            if f.ndim != 3 or a.ndim != 1 or x.shape != a.shape or y.shape != a.shape or len(f) != len(a) + 1:
                return {**result, "reason": "expected F[T+1,H,W] and A/X/Y[T]"}
            if not all(np.issubdtype(v.dtype, np.integer) for v in (f, a, x, y)):
                return {**result, "reason": "integer arrays required"}
            if f.shape[1:] != (64, 64) or np.any((f < 0) | (f > 15)) or np.any((a < 0) | (a > 7)):
                return {**result, "reason": "invalid ARC-3 dimensions, colors, or action IDs"}
            click = a == 6
            if np.any((x[click] < 0) | (x[click] > 63) | (y[click] < 0) | (y[click] > 63)):
                return {**result, "reason": "invalid ACTION6 coordinates"}
            if "L" in z.files and z["L"].shape != a.shape:
                return {**result, "reason": "level array does not match actions"}
            count = int(np.count_nonzero(a))
            if count < 20:
                return {**result, "reason": "fewer than 20 non-reset transitions", "transitions": count}
            early = min(80, int(.67 * count))
            result.update(valid=True, transitions=count, early=early, late=count - early)
    except (OSError, ValueError, KeyError) as e:
        return {**result, "reason": f"{type(e).__name__}: {str(e)[:180]}"}
    result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def manifest(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("recording directory must exist")
    # Match the current induction glob to show exactly which candidates fail.
    records = [inspect_recording(p) for p in sorted(directory.glob("*.npz")) if not p.name.startswith("play_")]
    return {"scope": "offline transition-file validation, not leaderboard performance or leakage certification",
            "python": platform.python_version(), "numpy": np.__version__, "records": records,
            "valid_count": sum(r["valid"] for r in records), "rejected_count": sum(not r["valid"] for r in records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = manifest(args.directory)
    payload = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(payload + "\n")
        print(f"{report['valid_count']} valid recordings; {report['rejected_count']} rejected candidates")
        for r in report["records"]:
            if not r["valid"]: print(f"  {Path(r['path']).name}: {r['reason']}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
