"""Offline algebra + cube audit. No API, model training, or live state writes.

python -B algebra_audit.py --views D:\\planet\\eye\\views_ls20_L1.json
An optional --output creates a NEW report; it never overwrites an existing file.
Saved views are reconstructed in memory; the recording and q array are untouched.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import cayley
import cube_memory


def neighbor_audit(field, tolerance=1e-12):
    """Test actual adjacent nonzero memory elements, not their differences.

    Unlifted, unit-normalized operands in cube-evidence-16-v1; tolerance and
    basis are explicit because a zero product depends on the coordinate map.
    """
    left = np.concatenate((field[:, :-1].reshape(-1, 16), field[:-1].reshape(-1, 16)))
    right = np.concatenate((field[:, 1:].reshape(-1, 16), field[1:].reshape(-1, 16)))
    nl, nr = np.linalg.norm(left, axis=1), np.linalg.norm(right, axis=1)
    keep = (nl > 0) & (nr > 0)
    a, b = left[keep] / nl[keep, None], right[keep] / nr[keep, None]
    result = {"schema": cube_memory.SCHEMA, "convention": "a*b, unlifted, unit-normalized; right and down neighbors",
              "nonzero_neighbor_pairs": len(a), "tolerance": tolerance, "near_zero_products": 0,
              "minimum_relative_residual": None, "witness": None}
    if len(a):
        products = np.einsum("pi,pj,ijk->pk", a, b, cayley.multiplication_table(16), optimize=True)
        residual = np.linalg.norm(products, axis=1)
        result["minimum_relative_residual"] = float(residual.min())
        result["near_zero_products"] = int(np.count_nonzero(residual <= tolerance))
        if result["near_zero_products"]:
            idx = int(np.argmin(residual))
            result["witness"] = cayley.product_certificate(left[keep][idx], right[keep][idx], tolerance)
    return result


def audit_view(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    q = np.load(path.with_name(path.stem + "_q.npy"), allow_pickle=False)
    if q.ndim != 3 or q.shape[-1] != 4:
        raise ValueError("a saved H x W x 4 quaternion field is required")
    def decode(name):
        return {tuple(map(int, pos.split(","))): rec for pos, rec in data.get(name, {}).items()}
    s = cube_memory.pack(q.shape[:2], decode("side"), decode("front"), decode("eyes"))
    return {"source": str(path.resolve()), "summary_collisions": cube_memory.collision_audit(q, s),
            "neighbor_products": neighbor_audit(s)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--views", nargs="*", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ladder = [cayley.doublet_audit(n) for n in (4, 8, 16)]
    witness = ladder[-1]["witness"]
    report = {"scope": "finite algebra checks and saved-memory diagnostics; no ARC solving claim",
              "ladder": ladder, "void_directions": cayley.annihilator_basis(witness["left"]),
              "views": [audit_view(p) for p in args.views]}
    payload = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        with args.output.open("x", encoding="utf-8") as out:
            out.write(payload + "\n")
        print(f"Report: {args.output.resolve()}")
    for row in ladder:
        print(f"dim {row['dimension']}: {row['ordered_zero_pairs']} ordered zero products; "
              f"{row['participating_left_doublets']} participating doublets")
    print(f"Witness right-annihilator dimension: {report['void_directions']['nullity']}")
    for row in report["views"]:
        c, n = row["summary_collisions"], row["neighbor_products"]
        print(f"{Path(row['source']).name}: {c['legacy_signatures_hiding_distinctions']} quaternion signatures hide distinctions; "
              f"{n['near_zero_products']}/{n['nonzero_neighbor_pairs']} adjacent nonzero pairs annihilate at tolerance {n['tolerance']}")
    if not args.output:
        print(payload)


if __name__ == "__main__":
    main()
