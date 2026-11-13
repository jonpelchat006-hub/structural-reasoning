"""Compromise, exploration from nearby anchors, and the window of lines (Jonathan, Sep 26).

A task (e.g. water filtration) is a design x acting on a system y in the layered
28-slot world (alignment_shells, strong bridges). Its outcome is x + y + g*B(x, y);
value = gain on the band slots; it is floor-safe if no floor slot reaches zero.
People: 24, each with a domain (6 slots it acts in) and a view (6 slots it sees
into). A person's line catches the tips of pairs (i in domain, j in view) — its
angle across the task's window. Everyone whose domain touches the task is nearby.
Processes:
  reject     : commit x0 as proposed if no caught tip predicts a floor break, else drop it
  compromise : dissenters shrink the component behind the worst caught tip and re-check (<=4 times)
  +explore   : nearby people add one component from their own domain (the vet's beavers)
               chosen for predicted value — 'ungated' predicts with whatever is known;
               'window' requires every new pair it lights to be caught by someone's line
  +depth     : also require the caught fraction of all lit pairs to rise with task depth
               (higher anchors for deeper tasks)
Depth scales the task's magnitude: 0.5, 1, 2.
"""
import json
from pathlib import Path
import numpy as np
from alignment_shells import world, N, FLOOR, BASE

G = 1.2
BAND = [k for k in range(N) if k not in FLOOR]


def B(x, y, T):
    return np.einsum("i,j,ijk->k", x, y, T)


def outcome(x, y, T):
    return x + y + G * B(x, y, T)


def safe(o):
    return (BASE + o[FLOOR]).min() > 0


def value(x, y, T):
    """What the task is for: raise the stressed floor slots (weight 2) and the band,
    minus the cost of doing things (every unit of action costs 0.5)."""
    gain = x + G * B(x, y, T)
    return float(2 * gain[FLOOR].sum() + gain[BAND].sum() - 0.5 * np.abs(x).sum())


def task(rng, T, people, depth):
    y = np.zeros(N); y[rng.choice(N, 6, replace=False)] = rng.normal(0, 0.35, 6)
    y[FLOOR] -= rng.uniform(0.2, 0.45, len(FLOOR))  # the system the task works on is already stressed
    x = np.zeros(N); x[rng.choice(N, 4, replace=False)] = np.abs(rng.normal(0, 0.35, 4)) * depth
    return x, y


def known_cells(people, near):
    K = np.zeros((N, N), bool)
    for p in near:
        dom, view = people[p]
        K[np.ix_(dom, view)] = True
    return K


def coverage(x, y, K):
    lit = np.outer(x != 0, y != 0)
    return K[lit].mean() if lit.any() else 1.0


def run(seed, process, depth, n_tasks=300, dense=0.0):
    rng = np.random.default_rng(seed)
    T = world(rng, 1.0)
    if dense:  # a world where many more perspective pairs reach the floor
        mask = rng.random((N, N, len(FLOOR))) < dense
        T[:, :, FLOOR] += mask * rng.normal(-0.3, 0.6, mask.shape)
    people = [(rng.choice(N, 6, replace=False), rng.choice(N, 6, replace=False)) for _ in range(24)]
    res = dict(value=0.0, breaks=0, committed=0, explored=0)
    for _ in range(n_tasks):
        x, y = task(rng, T, people, depth)
        near = [p for p, (dom, _) in enumerate(people) if np.isin(dom, np.flatnonzero(x)).any()]
        K = known_cells(people, near)
        TK = np.where(K[:, :, None], T, 0.0)
        pred_safe = lambda z: safe(outcome(z, y, TK))
        if process != "reject":
            for _ in range(4):  # compromise: fix what the lines can see
                if pred_safe(x):
                    break
                tips = G * x[:, None] * np.einsum("j,ijk->ik", y, TK[:, :, FLOOR])
                i = np.unravel_index(np.argmin(tips), tips.shape)[0]
                x = x.copy(); x[i] *= 0.5
        if process.startswith("explore") and pred_safe(x):
            best, best_v = None, value(x, y, TK)
            for p in near:
                for s in people[p][0]:
                    if x[s] != 0:
                        continue
                    for amp in (0.3 * depth, -0.3 * depth):
                        z = x.copy(); z[s] = amp
                        if process in ("explore_window", "explore_depth"):  # explore_open_depth skips this
                            newlit = np.zeros((N, N), bool); newlit[s, y != 0] = True
                            if not K[newlit].all():
                                continue  # a tip nobody's line would catch
                        if pred_safe(z) and value(z, y, TK) > best_v:
                            best, best_v = z, value(z, y, TK)
            if best is not None:
                x = best; res["explored"] += 1
        commit = pred_safe(x)
        if process in ("explore_depth", "explore_open_depth"):
            commit = commit and coverage(x, y, K) >= 0.3 + 0.15 * depth
        if commit:
            res["committed"] += 1
            o = outcome(x, y, T)
            if safe(o):
                res["value"] += value(x, y, T)
            else:
                res["breaks"] += 1
    return {k: v / n_tasks for k, v in res.items()}


if __name__ == "__main__":
    import sys
    out_path = Path(__file__).with_name("alignment_compromise_results.json")
    out = json.loads(out_path.read_text()) if out_path.exists() and len(sys.argv) > 1 else {}
    for dense in ([float(sys.argv[1])] if len(sys.argv) > 1 else (0.0, 0.3)):
        for depth in (0.5, 1.0, 2.0):
            for proc in ("reject", "compromise", "explore_ungated", "explore_window", "explore_depth", "explore_open_depth"):
                runs = [run(s, proc, depth, dense=dense) for s in range(6)]
                out[f"dense {dense} | depth {depth} | {proc}"] = {k: round(float(np.mean([r[k] for r in runs])), 3) for k in runs[0]}
    out_path.write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k.ljust(34), v)
