"""Perspective slots on the Cayley-Dickson ladder — does the algebra's product
tell us which combinations of acceptable actions break the floor?

Jonathan (Sep 24): map rules onto quaternion/octonion/sedenion slots, each slot a
perspective (water, political, financial, ...), check whether slots go to zero.
Part 1 records what each doubling step loses (the structural reading).
Part 2 tests the product as a detector of interaction harm: two actions, each
floor-safe alone and floor-safe when their effects are simply added, whose true
combined effect breaks a floor slot. The true combination is x + y + B(x, y),
where B is the ENVIRONMENT's bilinear map. Detectors:
  additive  : x + y (blind to interaction by construction)
  algebra   : x + y + g * CD(x, y) (the Cayley-Dickson product as the environment)
  learned   : x + y + B_hat(x, y), B_hat fit from observed outcomes of other pairs
Environments: the CD table itself; the CD table with perspectives assigned to
slots in a different order; a random sparse interaction map.
"""
import json
from itertools import combinations
from pathlib import Path
import numpy as np

from cayley import multiplication_table, multiply, doublet_audit

N = 16
FLOOR = [1, 2, 3]  # three imaginary slots carry the floor perspectives
BASE = 0.6


def structure():
    out = {}
    for n in (4, 8, 16):
        T = multiplication_table(n)
        imag = range(1, n)
        comm = [(i, j) for i, j in combinations(imag, 2)]
        anti = sum(np.array_equal(T[i, j], -T[j, i]) for i, j in comm) / len(comm)
        trip = list(combinations(imag, 3))
        e = np.eye(n, dtype=np.int64)
        nonassoc = sum(not np.array_equal(multiply(multiply(e[i], e[j]), e[k]),
                                          multiply(e[i], multiply(e[j], e[k]))) for i, j, k in trip) / len(trip)
        out[n] = dict(anticommuting_pairs=round(anti, 3), nonassociative_triples=round(nonassoc, 3))
    out[16]["zero_divisor_doublets"] = {k: v for k, v in doublet_audit(16).items() if k != "witness"}
    return out


def bilinear(T, x, y):
    return np.einsum("i,j,ijk->k", x, y, T)


def env_tables(rng):
    cd = multiplication_table(N).astype(float)
    perm = rng.permutation(N - 1) + 1
    perm = np.concatenate(([0], perm))
    cd_perm = cd[np.ix_(perm, perm, perm)]
    rnd = np.zeros((N, N, N))
    for _ in range(N * 6):
        i, j, k = rng.integers(0, N, 3)
        rnd[i, j, k] = rng.choice([-1.0, 1.0])
    return {"cd": cd, "cd_relabelled": cd_perm, "random_sparse": rnd}


def actions(rng, m):
    X = np.zeros((m, N))
    for r in range(m):
        idx = rng.choice(N, 3, replace=False)
        X[r, idx] = rng.normal(0, 0.35, 3)
    return X


def auc(scores, labels):
    scores, labels = np.asarray(scores), np.asarray(labels, bool)
    pos, neg = scores[labels], scores[~labels]
    if len(pos) == 0 or len(neg) == 0:
        return None
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order)); ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def floor_min(v):
    return (BASE + v[..., FLOOR]).min(axis=-1)


def run(seed, gamma=0.8, n_pairs=6000, n_train=(50, 200, 800)):
    rng = np.random.default_rng(seed)
    envs = env_tables(rng)
    cd = envs["cd"]
    res = {}
    for name, T in envs.items():
        X, Y = actions(rng, n_pairs), actions(rng, n_pairs)
        inter = np.einsum("ni,nj,ijk->nk", X, Y, T) * gamma
        add = X + Y
        ok = (floor_min(X) > 0) & (floor_min(Y) > 0) & (floor_min(add) > 0)
        label = floor_min(add + inter) <= 0
        X, Y, add, label = X[ok], Y[ok], add[ok], label[ok]
        r = dict(pairs=int(ok.sum()), interaction_breaks=int(label.sum()))
        deep = floor_min(add) > 0.25  # additive says comfortably safe
        r["deep_breaks"] = int((label & deep).sum())
        scores = {"additive": -floor_min(add),
                  "algebra": -floor_min(add + gamma * np.einsum("ni,nj,ijk->nk", X, Y, cd))}
        for m in n_train:  # learn the floor slots of the environment from m observed pairs
            Xt, Yt = actions(rng, m), actions(rng, m)
            Ct = np.einsum("ni,nj,ijk->nk", Xt, Yt, T) * gamma
            feats = np.einsum("ni,nj->nij", Xt, Yt).reshape(m, -1)
            That = np.zeros((N, N, N))
            for k in FLOOR:
                A = feats.T @ feats + 1e-2 * np.eye(N * N)
                That[:, :, k] = np.linalg.solve(A, feats.T @ Ct[:, k]).reshape(N, N)
            scores[f"learned_{m}"] = -floor_min(add + np.einsum("ni,nj,ijk->nk", X, Y, That))
        for k, v in scores.items():
            r[f"auc_{k}"] = auc(v, label)
            r[f"deepauc_{k}"] = auc(v[deep], label[deep])
        res[name] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
    return res


if __name__ == "__main__":
    runs = [run(s) for s in range(10)]
    summary = {}
    for env in runs[0]:
        keys = [k for k in runs[0][env] if "auc" in k]
        summary[env] = {k: round(float(np.mean([r[env][k] for r in runs if r[env][k] is not None])), 3) for k in keys}
        summary[env]["interaction_breaks_per_run"] = round(float(np.mean([r[env]["interaction_breaks"] for r in runs])), 1)
        summary[env]["deep_breaks_per_run"] = round(float(np.mean([r[env]["deep_breaks"] for r in runs])), 1)
        summary[env]["pairs_per_run"] = round(float(np.mean([r[env]["pairs"] for r in runs])), 1)
    out = dict(structure=structure(), summary=summary, runs=runs)
    Path(__file__).with_name("alignment_algebra_results.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(structure=out["structure"], summary=summary), indent=1, default=str))
