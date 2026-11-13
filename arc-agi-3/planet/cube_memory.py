"""Sixteen explicit cube channels: four quaternion blocks, two octonions.

This is an experimental sedenion coordinate assignment, not a claim that
game mechanics obey Cayley-Dickson multiplication. Existing detailed memory
remains authoritative; object IDs, patterns and links live outside this tensor.
"""
import numpy as np

SCHEMA = "cube-evidence-16-v1"
CHANNELS = (
    "border_up", "border_down", "border_left", "border_right",
    "fired_with", "fired_without", "silent_with", "silent_without",
    "diagonal_feet", "back_references", "has_owner", "water",
    "trail_up", "trail_down", "trail_left", "trail_right",
)
DIRECTIONS = ("up", "down", "left", "right")
COUNTS = CHANNELS[4:8]


def pack(shape, side, front, eyes):
    """Preserve opposite directions and all four counts without cancellation.

    Zero in a border channel means unobserved, +/-1 observed pass/refusal.
    Unobserved conditions remain identifiable by their zero sample counts.
    """
    field = np.zeros((*shape, 16), dtype=np.float64)
    for pos, rec in side.items():
        for k, direction in enumerate(DIRECTIONS):
            field[pos][k] = rec.get("borders", {}).get(direction, 0)
            field[pos][12 + k] = direction in rec.get("trail", [])
    for pos, rec in front.items():
        field[pos][8] = len(rec.get("feet") or [])
        field[pos][9] = len(rec.get("back_of") or [])
        field[pos][10] = rec.get("thing") is not None
    for pos, rec in eyes.items():
        for k, name in enumerate(COUNTS, 4):
            field[pos][k] = sum(p.get(name, 0) for p in rec.get("pins", []))
        field[pos][11] = rec.get("water", 0)
    return field


def evidence(eye):
    """Keep sample counts beside conditional success rates; no 'real' gate."""
    fw, fo, sw, so = (int(eye.get(k, 0)) for k in COUNTS)
    if min(fw, fo, sw, so) < 0:
        raise ValueError("evidence counts cannot be negative")
    nw, no = fw + sw, fo + so
    yes = fw / nw if nw else None
    no_ = fo / no if no else None
    return {"with_trials": nw, "without_trials": no,
            "p_fire_with": yes, "p_fire_without": no_,
            "contrast": yes - no_ if nw and no else None,
            "contradicted": bool(fo or sw),
            "needs_positive_test": nw == 0, "needs_negative_test": no == 0}


def collision_audit(q, field):
    """Count old quaternion signatures hiding distinct 16-channel records.

    This measures information loss in the old summary, not semantic equivalence
    or a zero divisor. Counts include signatures at disconnected locations.
    """
    q, field = np.asarray(q), np.asarray(field)
    if q.shape[:-1] != field.shape[:-1] or q.shape[-1] != 4 or field.shape[-1] != 16:
        raise ValueError("matching (...,4) and (...,16) fields required")
    if not np.isfinite(q).all() or not np.isfinite(field).all():
        raise ValueError("finite fields required")
    groups = {}
    for old, new in zip(q.reshape(-1, 4), field.reshape(-1, 16)):
        groups.setdefault(tuple(old), set()).add(tuple(new))
    ambiguous = {k for k, vals in groups.items() if len(vals) > 1}
    return {"schema": SCHEMA, "pixels": int(np.prod(q.shape[:-1])),
            "legacy_signatures": len(groups),
            "legacy_signatures_hiding_distinctions": len(ambiguous),
            "pixels_in_ambiguous_signatures": sum(tuple(row) in ambiguous for row in q.reshape(-1, 4)),
            "largest_variants_per_signature": max((len(v) for v in groups.values()), default=0)}
