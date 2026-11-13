"""Perspectives on rings of different radii: addition across shells, a
multiplication table per shell (Jonathan, Sep 25).

Addition   : the perspective space is the direct sum inner (4) + middle (8) + outer (16);
             a bigger ring holds more slots, so the dimension doubles going out.
Multiply   : each shell has its own table. Inner = the fixed Cayley-Dickson table
             (innate, read-only); middle and outer = environment tables, unknown.
Bridges    : cross-shell terms (inner x outer, ...) — the tunnels between ring eyes.
Question   : when the world is layered like this, does a learner that assumes the
             layering find floor-breaking combinations with fewer observations than a
             flat learner, and what does it miss when bridges exist?
Floor slots: one per shell. Detection is scored on 'deep' pairs (additively safe).
"""
import json
from pathlib import Path
import numpy as np
from cayley import multiplication_table

DIMS = {"inner": 4, "middle": 8, "outer": 16}
OFF = {"inner": 0, "middle": 4, "outer": 12}
N = 28
FLOOR = [1, 4 + 1, 12 + 1]
BASE = 0.6


def world(rng, bridge_strength):
    T = np.zeros((N, N, N))
    T[:4, :4, :4] = multiplication_table(4)
    for s in ("middle", "outer"):
        o, d = OFF[s], DIMS[s]
        for _ in range(d * 6):
            i, j, k = rng.integers(0, d, 3)
            T[o + i, o + j, o + k] = rng.choice([-1.0, 1.0])
    for _ in range(40):  # bridges: product of slots in two shells lands in a third slot
        a, b = rng.choice(list(DIMS), 2, replace=False)
        i = OFF[a] + rng.integers(DIMS[a]); j = OFF[b] + rng.integers(DIMS[b]); k = rng.choice(FLOOR) if rng.random() < 0.5 else rng.integers(N)  # half the bridges reach a floor slot
        T[i, j, k] = bridge_strength * rng.choice([-1.0, 1.0])
    return T


def actions(rng, m):
    X = np.zeros((m, N))
    for r in range(m):  # an action touches a few perspectives, often in more than one shell
        idx = rng.choice(N, 4, replace=False)
        X[r, idx] = rng.normal(0, 0.35, 4)
    return X


def prod(X, Y, T):
    return np.einsum("ni,nj,ijk->nk", X, Y, T)


def fmin(v):
    return (BASE + v[..., FLOOR]).min(axis=-1)


def auc(s, y):
    s, y = np.asarray(s), np.asarray(y, bool)
    p, q = s[y], s[~y]
    if not len(p) or not len(q):
        return None
    r = np.empty(len(s)); r[np.argsort(np.concatenate([p, q]))] = np.arange(1, len(s) + 1)
    return float((r[:len(p)].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(q)))


def masks():
    shell = np.empty(N, int)
    for n, (s, o) in enumerate(OFF.items()):
        shell[o:o + DIMS[s]] = n
    same = shell[:, None] == shell[None, :]
    return shell, same


def fit(Xt, Yt, Ct, mode):
    """Learn the floor-slot outputs of the table from observed pairs."""
    shell, same = masks()
    That = np.zeros((N, N, N))
    feats_full = np.einsum("ni,nj->nij", Xt, Yt)
    for k in FLOOR:
        if mode == "flat":
            allow = np.ones((N, N), bool)
        elif mode == "layered":  # products only inside the output's own shell; inner given
            allow = same & (shell[:, None] == shell[k])
        elif mode == "layered+bridges":  # own shell + any cross-shell pair
            allow = (same & (shell[:, None] == shell[k])) | ~same
        target = Ct[:, k].copy()
        if mode != "flat" and shell[k] == 0:  # innate table: not learned
            That[:4, :4, k] = multiplication_table(4)[:, :, k]
            target -= np.einsum("nij,ij->n", feats_full, That[:, :, k])
            allow = allow & ~((shell[:, None] == 0) & (shell[None, :] == 0))
        F = feats_full[:, allow]
        w = np.linalg.solve(F.T @ F + 1e-2 * np.eye(F.shape[1]), F.T @ target)
        That[:, :, k][allow] += w
    return That


def run(seed, bridge, trains=(100, 300, 1000), gamma=1.2, npairs=12000):
    rng = np.random.default_rng(seed)
    T = world(rng, bridge)
    X, Y = actions(rng, npairs), actions(rng, npairs)
    add = X + Y
    ok = (fmin(X) > 0) & (fmin(Y) > 0) & (fmin(add) > 0.2)
    X, Y, add = X[ok], Y[ok], add[ok]
    label = fmin(add + gamma * prod(X, Y, T)) <= 0
    out = dict(pairs=int(ok.sum()), breaks=int(label.sum()), additive=auc(-fmin(add), label))
    for m in trains:
        Xt, Yt = actions(rng, m), actions(rng, m)
        Ct = gamma * prod(Xt, Yt, T)
        for mode in ("flat", "layered", "layered+bridges"):
            out[f"{mode}_{m}"] = auc(-fmin(add + prod(X, Y, fit(Xt, Yt, Ct, mode))), label)
    return out


if __name__ == "__main__":
    res = {}
    for bridge in (0.0, 0.5, 1.0):
        runs = [run(s, bridge) for s in range(8)]
        res[f"bridge_{bridge}"] = {k: round(float(np.mean([r[k] for r in runs if r[k] is not None])), 3) for k in runs[0]}
    Path(__file__).with_name("alignment_shells_results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
