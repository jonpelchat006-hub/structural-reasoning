"""Cayley-Dickson ladder, in the convention used by quat.omul.

(a,b)(c,d) = (ac - conjugate(d)b, da + b conjugate(c)).
Coordinates are explicit: e0 is the identity. A zero product is an algebraic
certificate, not evidence that an ARC transition is impossible or understood.
See ALGEBRA_LINEAGE.md for the sphere-generator / orchard source trail.
"""
from functools import lru_cache
from itertools import combinations
import numpy as np


def _dimension(n):
    if n not in (1, 2, 4, 8, 16, 32):
        raise ValueError("dimension must be 1, 2, 4, 8, 16, or 32")


def conjugate(a):
    a = np.asarray(a)
    if a.ndim != 1:
        raise ValueError("one algebra element required")
    _dimension(len(a))
    out = -a.copy()
    out[0] = a[0]
    return out


def _recursive(a, b):
    if len(a) == 1:
        return a * b
    h = len(a) // 2
    x, y, z, w = a[:h], a[h:], b[:h], b[h:]
    return np.concatenate((_recursive(x, z) - _recursive(conjugate(w), y),
                           _recursive(w, x) + _recursive(y, conjugate(z))))


@lru_cache(maxsize=6)
def multiplication_table(n):
    """Exact signed basis products; read-only to protect cached conventions."""
    _dimension(n)
    basis = np.eye(n, dtype=np.int64)
    table = np.array([[_recursive(a, b) for b in basis] for a in basis])
    table.flags.writeable = False
    return table


def multiply(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.ndim != 1 or b.shape != a.shape:
        raise ValueError("operands must be equal-length vectors")
    return np.einsum("i,j,ijk->k", a, b, multiplication_table(len(a)))


def product_certificate(a, b, tolerance=1e-12):
    """Retain both operands when a product disappears; zero != empty inputs.

    Integer inputs use exact equality (within int64 range); floating inputs
    additionally report a scale-normalized residual. Never assume norm
    multiplicativity at dimension 16 or above.
    """
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    a, b = np.asarray(a), np.asarray(b)
    p = multiply(a, b)
    if not all(np.isfinite(v).all() for v in (a, b, p)):
        raise ValueError("finite coordinates required")
    na, nb, np_ = (float(np.linalg.norm(v.astype(float))) for v in (a, b, p))
    nonzero = na > 0 and nb > 0
    residual = np_ / na / nb if nonzero else None
    exact = bool(np.all(p == 0))
    integer = np.issubdtype(a.dtype, np.integer) and np.issubdtype(b.dtype, np.integer)
    return {"dimension": len(a), "left": a.tolist(), "right": b.tolist(),
            "product": p.tolist(), "left_norm": na, "right_norm": nb,
            "product_norm": np_, "relative_residual": residual,
            "nonzero_operands": nonzero, "exact_zero_product": exact,
            "zero_divisor_witness": nonzero and exact and integer,
            "numerical_zero_product": nonzero and exact and not integer,
            "near_annihilation": nonzero and not integer and not exact and residual <= tolerance}


def annihilator_basis(a, side="right", tolerance=1e-12):
    """Numerical directions b with a*b=0 (right) or b*a=0 (left).

    The kernel supplies candidate 'void lines' for this element, with residuals.
    It does not invent a map from these directions to game actions.
    """
    a = np.asarray(a, dtype=float)
    if a.ndim != 1 or not np.isfinite(a).all() or not np.any(a):
        raise ValueError("a finite nonzero algebra element is required")
    _dimension(len(a))
    if side not in ("right", "left") or not (0 < tolerance < 1):
        raise ValueError("side must be right/left and tolerance between 0 and 1")
    a = a / np.linalg.norm(a)
    basis = np.eye(len(a))
    mat = np.column_stack([multiply(a, b) if side == "right" else multiply(b, a) for b in basis])
    _, singular, vh = np.linalg.svd(mat)
    rank = int(np.count_nonzero(singular > tolerance * singular[0]))
    directions = vh[rank:]
    return {"side": side, "dimension": len(a), "nullity": len(directions),
            "directions": directions.tolist(),
            "residuals": [float(np.linalg.norm(mat @ b)) for b in directions]}


def doublet_audit(n):
    """Reproduce the old finite search: e_i+e_j, 1 <= i < j < n.

    Counts are ordered pairs from this family, not all zero divisors.
    """
    _dimension(n)
    if n > 16:
        raise ValueError("the historical doublet audit is bounded at 16")
    indices = list(combinations(range(1, n), 2))
    vectors = np.zeros((len(indices), n), dtype=np.int64)
    for row, (i, j) in enumerate(indices):
        vectors[row, i] = vectors[row, j] = 1
    products = np.einsum("ai,bj,ijk->abk", vectors, vectors, multiplication_table(n), optimize=True)
    hits = np.all(products == 0, axis=-1)
    pairs = np.argwhere(hits)
    witness = product_certificate(vectors[pairs[0, 0]], vectors[pairs[0, 1]]) if len(pairs) else None
    return {"dimension": n, "family": "positive imaginary basis doublets e_i+e_j, i<j",
            "doublets": len(indices), "ordered_zero_pairs": len(pairs),
            "participating_left_doublets": int(np.count_nonzero(hits.any(axis=1))),
            "partners_per_participant": sorted(set(hits.sum(axis=1)[hits.any(axis=1)].tolist())),
            "witness": witness}
