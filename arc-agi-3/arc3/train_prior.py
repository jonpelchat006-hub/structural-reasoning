"""The look-back across games: learn which candidate presses lie on the shortest won routes.

Conditional logit: at each state on a won route, P(press j) = softmax_j(w . x_j), fit by gradient
descent with L2. Leave-one-game-out: for each public game G, weights fit on the other 24 games are
what the agent uses on G (so the bench measures transfer to unseen games); "all" is fit on every game
and is what goes to the hidden set.

  python3 train_prior.py runs/d_feats.json prior.json"""
import json, sys, collections
import numpy as np

sys.path.insert(0, "."); sys.path.insert(0, "fw")
from mika3.explorer2 import FEAT_NAMES

res = json.load(open(sys.argv[1]))
groups = collections.defaultdict(list)          # game -> list of (X, chosen)
seen = set()
for r in res:
    g = r["game"][:4]
    for d in (r.get("route_data") or []):
        X = np.array(d["feats"], dtype=float)
        key = (g, d["level"], X.shape, d["chosen"], X.tobytes())
        if key in seen:                         # the same state on the same route across seeds: once
            continue
        seen.add(key)
        groups[g].append((X, d["chosen"]))
print({g: len(v) for g, v in sorted(groups.items())}, "states")


def fit(data, lam=0.05, iters=400, lr=0.5):
    D = len(FEAT_NAMES)
    w = np.zeros(D)
    for it in range(iters):
        grad = lam * w
        for X, c in data:
            z = X @ w; z -= z.max(); p = np.exp(z); p /= p.sum()
            grad += (X.T @ p - X[c]) / len(data)
        w -= lr * grad
    return w


def evaluate(w, data):
    ll, top1, rank, base = 0.0, 0, 0.0, 0.0
    for X, c in data:
        z = X @ w; z -= z.max(); p = np.exp(z); p /= p.sum()
        ll += np.log(p[c] + 1e-12); base += np.log(1.0 / len(p))
        top1 += int(np.argmax(p) == c)
        rank += (p > p[c]).sum() / max(1, len(p) - 1)
    n = max(1, len(data))
    return ll / n, base / n, top1 / n, rank / n


prior = {}
rows = []
for g in sorted(groups):
    train = [x for h, v in groups.items() if h != g for x in v]
    w = fit(train)
    prior[g] = w.round(4).tolist()
    ll, base, t1, rk = evaluate(w, groups[g])
    rows.append((g, len(groups[g]), ll, base, t1, rk))
    print(f"{g}: held-out states {len(groups[g]):4d}  loglik {ll:6.2f} (uniform {base:6.2f})  top1 {t1:.2f}  mean rank frac {rk:.2f}")
allw = fit([x for v in groups.values() for x in v])
prior["all"] = allw.round(4).tolist()
n = sum(r[1] for r in rows)
print("held-out mean loglik %.3f vs uniform %.3f; top1 %.3f; rank %.3f" % (
    sum(r[2] * r[1] for r in rows) / n, sum(r[3] * r[1] for r in rows) / n, sum(r[4] * r[1] for r in rows) / n, sum(r[5] * r[1] for r in rows) / n))
print("weights (all):", {k: round(v, 2) for k, v in zip(FEAT_NAMES, allw)})
# games with no won route still get the all-games weights
json.dump(prior, open(sys.argv[2], "w"))
