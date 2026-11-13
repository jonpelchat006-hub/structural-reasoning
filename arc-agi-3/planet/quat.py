#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
quat.py — THE QUATERNION MEMORY and its doubling.

Jonathan (Sep 7): "would the memory be stored using quaternions, where when we recall we choose a real axis eye to see
from and have the other three as imaginary terms? ... the octonion would be the quaternion from the starting pixel and
the rest of the imaginary terms would be the ones from the next pixel."

A pixel's memory is four numbers, one per eye:
    top     what held      (the pins' eyes and the water: +1 fired only with its condition, -1 fired without, 0 unseen)
    front   the context    (+1 a diagonal foot or a back-wall coordinate, +0.5 flat pins only, 0 nothing)
    side_x  the vertical   (the up/down borders: +1 bent, -1 broken, averaged; 0 unknown)
    side_y  the horizontal (the left/right borders, likewise)

RECALL from an eye puts that eye on the real axis and the other three on i, j, k — the same memory, a different
quaternion. A PATH is the product of its pixels' quaternions in order; the product is not commutative, which is what
the route taught (touch then ring is not ring then touch). The OCTONION of two neighbouring pixels is the Cayley–Dickson
pair (q_here, q_next): (a, b)(c, d) = (ac - d*b, da + bc*). Octonions are not associative: (pq)r != p(qr) along a path,
and the size of that failure — the associator — is where the path has a natural split, a basin boundary.
"""
from __future__ import annotations
import numpy as np

EYES = ["top", "front", "side_x", "side_y"]


def recall(q, eye):
    """q: (..., 4) in the order top, front, side_x, side_y; returns (..., 4) with `eye` as the real part"""
    i = EYES.index(eye)
    order = [i] + [j for j in range(4) if j != i]
    return np.asarray(q)[..., order]


def qmul(a, b):
    """Hamilton product of quaternions (w, x, y, z)"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def qconj(a):
    a = np.asarray(a, float); return np.array([a[0], -a[1], -a[2], -a[3]])


def qnorm(a): return float(np.sqrt(np.sum(np.asarray(a, float) ** 2)))


ONE = np.array([1.0, 0.0, 0.0, 0.0])


def lift(q):
    """a pixel enters a product as ONE plus its memory: nothing remembered is the identity, not zero (Sep 7: a single empty
    pixel on a path had annihilated the whole product)"""
    return ONE + np.asarray(q, float)


def path_product(qs):
    """the product of a path's pixels in order; (real part, norm, the product)"""
    p = ONE.copy()
    for q in qs: p = qmul(p, lift(q))
    return float(p[0]), qnorm(p), p


def omul(A, B):
    """Cayley–Dickson product of octonions as pairs of quaternions: (a, b)(c, d) = (ac - d* b, d a + b c*)"""
    a, b = A; c, d = B
    return (qmul(a, c) - qmul(qconj(d), b), qmul(d, a) + qmul(b, qconj(c)))


def onorm(A): return float(np.sqrt(qnorm(A[0]) ** 2 + qnorm(A[1]) ** 2))


def pairs_of(qs):
    """the octonions of a path: each pixel paired with the next (the last pairs with zero)"""
    zero = np.zeros(4)
    return [(lift(qs[i]), np.asarray(qs[i + 1], float) if i + 1 < len(qs) else zero) for i in range(len(qs))]


def associator(A, B, C):
    """|(AB)C - A(BC)|: zero for quaternions, not for octonions — where a path does not split freely"""
    L = omul(omul(A, B), C); R = omul(A, omul(B, C))
    return float(np.sqrt(qnorm(L[0] - R[0]) ** 2 + qnorm(L[1] - R[1]) ** 2))


def path_octonion(qs):
    """the path's octonion product left to right, its norm, and the largest associator along it (the basin boundary)"""
    os_ = pairs_of(qs)
    if not os_: return None
    P = os_[0]
    for O in os_[1:]: P = omul(P, O)
    worst = (0.0, None)
    for i in range(len(os_) - 2):
        a = associator(os_[i], os_[i + 1], os_[i + 2])
        if a > worst[0]: worst = (a, i + 1)
    return {"norm": onorm(P), "real": float(P[0][0]), "associator": worst[0], "split_at": worst[1]}


def qpow(q, n):
    """q multiplied by itself n times"""
    p = ONE.copy()
    for _ in range(int(n)): p = qmul(p, q)
    return p


def holonomy(q, n):
    """THE SAME TERM ROUND A BORDER (Jonathan, Sep 7): going round a uniform region's edge multiplies the same lifted term
    n times. For the direction part this is a rotation by n times its angle; it comes back to where it started when that
    is a whole turn. Returns (angle of one step, total angle mod 2pi, |growth| per step, closes: bool)."""
    u = lift(q); nrm = qnorm(u)
    if nrm == 0: return 0.0, 0.0, 0.0, True
    unit = u / nrm
    step = 2.0 * float(np.arccos(np.clip(unit[0], -1.0, 1.0)))             # a unit quaternion w = cos(theta/2)
    total = (step * n) % (2.0 * np.pi)
    closes = min(total, 2.0 * np.pi - total) < 1e-6 or step < 1e-9
    return step, total, nrm, closes


def collapse(q, tol=1e-6):
    """A UNIFORM REGION IS ONE TERM: connected pixels with the same memory collapse into one node — the term, the count of
    cells, the perimeter, and the holonomy round the edge. The body's 25 pixels become one quaternion; a wall piece too.
    Returns (terms, labels) with terms sorted by size."""
    from scipy import ndimage
    H, W, _ = q.shape
    key = np.round(q / tol).astype(np.int64)
    flat = key.reshape(H * W, 4)
    uniq, inv = np.unique(flat, axis=0, return_inverse=True)
    inv = inv.reshape(H, W)
    labels = np.zeros((H, W), np.int32); terms = []; nxt = 1
    for u in range(len(uniq)):
        m = inv == u
        lab, n = ndimage.label(m)
        for i in range(1, n + 1):
            c = lab == i
            cnt = int(c.sum())
            inner = ndimage.binary_erosion(c, border_value=0)
            perim = int((c & ~inner).sum())
            qq = q[c][0]
            step, total, growth, closes = holonomy(qq, max(perim, 1))
            labels[c] = nxt; nxt += 1
            terms.append({"id": nxt - 1, "cells": cnt, "perimeter": perim, "q": [round(float(v), 3) for v in qq], "step": round(step, 4),
                          "round_the_edge": round(total, 4), "growth": round(growth, 3), "closes": bool(closes), "empty": bool(np.all(qq == 0))})
    terms.sort(key=lambda t: -t["cells"])
    return terms, labels


def stitch(terms, labels, body):
    """THE STITCH (Jonathan, Sep 7): the body's parts are separate terms because its two colours carry different pins,
    but they keep a constant position relative to each other — the diagonal between them has nowhere to go — so they
    nest into one term. Two parts nest as the Cayley–Dickson pair (an octonion: the first part real, the second its
    imaginary half); more parts chain. Returns the nested term: its parts, the pair, its norm, and the whole's
    quaternion as the lifted product of the parts in reading order."""
    ids = [int(i) for i in np.unique(labels[body]) if i > 0]
    parts = [t for t in terms if t["id"] in ids]
    parts.sort(key=lambda t: -t["cells"])
    qs = [np.asarray(t["q"], float) for t in parts]
    if not qs: return None
    real, norm, whole = path_product(qs)
    pair = (lift(qs[0]), qs[1] if len(qs) > 1 else np.zeros(4))
    for q in qs[2:]: pair = omul(pair, (lift(q), np.zeros(4)))
    return {"parts": [{"id": t["id"], "cells": t["cells"], "q": t["q"]} for t in parts], "whole": [round(float(v), 3) for v in whole],
            "octonion_norm": round(onorm(pair), 3), "whole_norm": round(norm, 3), "one_term": len(qs) == 1}
