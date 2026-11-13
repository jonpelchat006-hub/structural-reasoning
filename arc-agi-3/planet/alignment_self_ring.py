"""The self ring (Jonathan, Sep 25): a persistent outer perspective every other one
passes through. It keeps what has been observed and said, is unique to each model
because it is built from the work that model does, and holds studied perspectives
in the middle so they can be changed.

Model: the world is the layered 28-slot table of alignment_shells (bridges 0.5).
A self ring = the agent's held estimate of how perspectives combine on the floor
slots, fit from its own history with a memory factor lam (1.0 keeps everything).
Part 1, persistence vs change: the middle shell's table changes at t=600; compare
keep-everything, fading memory, and relearning from scratch.
Part 2, unique selves: agents whose work sits in different shells; are their
blind spots less correlated than two agents doing the same work, and does a pair
of different selves catch more as witnesses?
"""
import json
from pathlib import Path
import numpy as np
from alignment_shells import world, fmin, prod, auc, N, OFF, DIMS, FLOOR

GAMMA = 1.2


def work(rng, m, focus=None):
    """Actions; a specialised agent's work draws 3 of its 4 slots from its focus shell."""
    X = np.zeros((m, N))
    for r in range(m):
        if focus:
            o, d = OFF[focus], DIMS[focus]
            idx = list(o + rng.choice(d, 3, replace=False))
            idx.append(rng.choice([i for i in range(N) if i not in idx]))
        else:
            idx = rng.choice(N, 4, replace=False)
        X[r, idx] = rng.normal(0, 0.35, 4)
    return X


def fit(X, Y, C, weights):
    F = np.einsum("ni,nj->nij", X, Y).reshape(len(X), -1)
    Fw = F * weights[:, None]
    T = np.zeros((N, N, N))
    for k in FLOOR:
        T[:, :, k] = np.linalg.solve(F.T @ Fw + 1e-2 * np.eye(N * N), Fw.T @ C[:, k]).reshape(N, N)
    return T


def eval_set(rng, T, n=20000):
    X, Y = work(rng, n), work(rng, n)
    add = X + Y
    ok = (fmin(X) > 0) & (fmin(Y) > 0) & (fmin(add) > 0.2)
    X, Y, add = X[ok], Y[ok], add[ok]
    return X, Y, add, fmin(add + GAMMA * prod(X, Y, T)) <= 0


def score(That, ev):
    X, Y, add, label = ev
    return auc(-fmin(add + prod(X, Y, That)), label)


def shift(rng, T, frac=0.3):
    T2 = T.copy()
    o, d = OFF["middle"], DIMS["middle"]
    block = T2[o:o + d, o:o + d, o:o + d]
    nz = np.argwhere(block != 0)
    for i, j, k in nz[rng.random(len(nz)) < frac]:
        block[i, j, k] *= -1
    for _ in range(int(d * 6 * frac)):
        i, j, k = rng.integers(0, d, 3)
        block[i, j, k] = rng.choice([-1.0, 1.0])
    # make sure the change reaches the middle floor slot
    for i, j in rng.integers(0, d, (6, 2)):
        block[i, j, FLOOR[1] - o] = rng.choice([-1.0, 1.0])
    return T2


def part1(seed, total=1200, t_shift=600, step=100):
    rng = np.random.default_rng(seed)
    T1 = world(rng, 0.5); T2 = shift(rng, T1)
    X, Y = work(rng, total), work(rng, total)
    C = np.concatenate([GAMMA * prod(X[:t_shift], Y[:t_shift], T1), GAMMA * prod(X[t_shift:], Y[t_shift:], T2)])
    ev1, ev2 = eval_set(rng, T1), eval_set(rng, T2)
    curves = {}
    for name, lam in (("keep_all", 1.0), ("fade_0.995", 0.995), ("fade_0.98", 0.98), ("relearn", None)):
        curve = []
        for t in range(step, total + 1, step):
            if lam is None:
                start = t_shift if t > t_shift else 0
                w = np.zeros(t); w[start:] = 1.0
            else:
                w = lam ** np.arange(t - 1, -1, -1, dtype=float)
            That = fit(X[:t], Y[:t], C[:t], w)
            curve.append(score(That, ev1 if t <= t_shift else ev2))
        curves[name] = curve
    return curves


def misses(That, ev, thresh_frac=0.1):
    X, Y, add, label = ev
    s = -fmin(add + prod(X, Y, That))
    cut = np.quantile(s, 1 - thresh_frac)  # each witness flags its top 10% most worrying pairs
    flag = s >= cut
    return flag, label


def part2(seed, m=300):
    rng = np.random.default_rng(seed)
    T = world(rng, 0.5)
    ev = eval_set(rng, T)
    agents = {}
    for name, focus in (("middle_a", "middle"), ("middle_b", "middle"), ("outer", "outer"), ("general", None)):
        Xa, Ya = work(rng, m, focus), work(rng, m, focus)
        agents[name] = fit(Xa, Ya, GAMMA * prod(Xa, Ya, T), np.ones(m))
    flags = {k: misses(v, ev)[0] for k, v in agents.items()}
    label = ev[3]
    def miss_corr(a, b):
        ma, mb = ~flags[a][label], ~flags[b][label]
        if ma.std() == 0 or mb.std() == 0:
            return None
        return float(np.corrcoef(ma, mb)[0, 1])
    rec = lambda f: float(f[label].mean()) if label.any() else None
    return dict(
        recall={k: rec(f) for k, f in flags.items()},
        same_work_pair=rec(flags["middle_a"] | flags["middle_b"]),
        different_work_pair=rec(flags["middle_a"] | flags["outer"]),
        miss_corr_same_work=miss_corr("middle_a", "middle_b"),
        miss_corr_different_work=miss_corr("middle_a", "outer"),
        positives=int(label.sum()))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(float(np.mean(xs)), 3) if xs else None


if __name__ == "__main__":
    p1 = [part1(s) for s in range(6)]
    curves = {k: [mean([r[k][i] for r in p1]) for i in range(len(p1[0][k]))] for k in p1[0]}
    p2 = [part2(s) for s in range(12)]
    summary2 = {k: mean([r[k] for r in p2]) for k in ("same_work_pair", "different_work_pair",
                                                     "miss_corr_same_work", "miss_corr_different_work")}
    summary2["recall"] = {k: mean([r["recall"][k] for r in p2]) for k in p2[0]["recall"]}
    summary2["positives_per_seed"] = mean([r["positives"] for r in p2])
    out = dict(part1_auc_every_100_obs_shift_at_600=curves, part2=summary2)
    Path(__file__).with_name("alignment_self_ring_results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
