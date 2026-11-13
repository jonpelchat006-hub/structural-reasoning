"""cayley.py - Cayley-Dickson doubling (reals -> complex -> quaternions -> octonions -> sedenions) and a check of where
the zero divisors appear. Convention: (a,b)(c,d) = (ac - d*b, da + bc*), (a,b)* = (a*, -b)."""
import itertools
import numpy as np


def conj(x):
    x = np.asarray(x, dtype=float)
    if len(x) == 1: return x.copy()
    h = len(x) // 2
    return np.concatenate([conj(x[:h]), -x[h:]])


def mul(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    if len(x) == 1: return x * y
    h = len(x) // 2
    a, b, c, d = x[:h], x[h:], y[:h], y[h:]
    return np.concatenate([mul(a, c) - mul(conj(d), b), mul(d, a) + mul(b, conj(c))])


def e(i, n):
    v = np.zeros(n); v[i] = 1.0; return v


def norm(x): return float(np.sqrt(np.dot(x, x)))


def zero_divisor_planes(n):
    """planes span(e_i, e_j) of imaginary units whose diagonals e_i +/- e_j zero-divide some other such diagonal"""
    planes = set(); pairs = 0
    imag = range(1, n)
    for (i, j), (k, l) in itertools.product(itertools.combinations(imag, 2), repeat=2):
        for s in (1, -1):
            for t in (1, -1):
                p = mul(e(i, n) + s * e(j, n), e(k, n) + t * e(l, n))
                if norm(p) < 1e-12:
                    planes.add((i, j)); pairs += 1
    return planes, pairs


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    for n, name in [(4, "quaternions"), (8, "octonions"), (16, "sedenions")]:
        planes, pairs = zero_divisor_planes(n)
        ratios = []
        for _ in range(2000):
            a, b = rng.normal(size=n), rng.normal(size=n)
            ratios.append(norm(mul(a, b)) / (norm(a) * norm(b)))
        print(f"{name:12s} dim {n:2d}: zero-divisor planes {len(planes):3d}, zero products found {pairs:4d}, "
              f"|ab|/(|a||b|) over random pairs: min {min(ratios):.3f} max {max(ratios):.3f}")
