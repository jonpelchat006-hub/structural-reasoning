"""Branch tips, and an enforcement patrol that stitches pins across the gaps
(Jonathan, Sep 26).

Branches: when two actions meet, every lit pair of perspectives (i from one, j from
the other) sends a branch into each floor slot k with tip value x_i*y_j*T[i,j,k].
A combination breaks the floor where the tips (plus the additive part) take a floor
slot to zero; the most negative tip says WHERE the harm is.
Pins: a pin on cell (i,j,k) is a line over one gap, not a wall: it blocks a
combination only if that branch's tip is below -0.02. The floor itself is untouched.
Patrol: each round it probes a few cells (reading the tips there) and pins the
negative ones; after every committed break it investigates and pins the worst tip
(learning from breaks). Compared with no enforcement and with a wall between shells.
World: the layered 28-slot table of alignment_shells with strong bridges.
"""
import json
from pathlib import Path
import numpy as np
from alignment_shells import world, fmin, N, OFF, DIMS, FLOOR
from alignment_self_ring import work

GAMMA, TIP = 1.2, -0.02


def shell_of():
    s = np.empty(N, int)
    for n, (name, o) in enumerate(OFF.items()):
        s[o:o + DIMS[name]] = n
    return s


def tips(x, y, T):
    return GAMMA * np.einsum("i,j,ijk->ijk", x, y, T[:, :, FLOOR])  # (N,N,3)


def run(seed, strategy, rounds=25, per_round=200, budget=20):
    rng = np.random.default_rng(seed)
    T = world(rng, 1.0)
    sh = shell_of()
    known = np.zeros((N, N), bool)          # gaps the enforcement has a pin (a line) across
    cross = [(i, j) for i in range(N) for j in range(N) if sh[i] != sh[j]]
    allc = [(i, j) for i in range(N) for j in range(N)]
    rng.shuffle(cross); rng.shuffle(allc)
    zig = iter(sorted(cross, key=lambda c: (min(sh[c[0]], sh[c[1]]), max(sh[c[0]], sh[c[1]]), c[0], c[1])) + allc)
    traffic = np.zeros((N, N))
    out = dict(late_breaks=0, breaks=0, blocked_breaks=0, benign_blocked=0, benign=0, probes=0, pins_by_round=[])
    for r in range(rounds):
        X, Y = work(rng, per_round), work(rng, per_round)
        for x, y in zip(X, Y):
            full = GAMMA * np.einsum("i,j,ijk->k", x, y, T)
            breaks = fmin(x + y + full) <= 0
            traffic += np.abs(np.outer(x, y))
            if strategy == "wall":
                a, b = np.flatnonzero(x), np.flatnonzero(y)
                blocked = any(sh[i] != sh[j] for i in a for j in b)
            elif strategy == "none":
                blocked = False
            else:  # the pins' partial map: only the branches crossing pinned gaps are counted
                Tk = np.where(known[:, :, None], T, 0.0)
                blocked = bool(fmin(x + y + GAMMA * np.einsum("i,j,ijk->k", x, y, Tk)) <= 0.05)
            if breaks:
                out["breaks" if not blocked else "blocked_breaks"] += 1
                out["late_breaks"] += (not blocked) and r >= rounds - 5
                if not blocked and strategy != "wall" and strategy != "none":
                    tp = GAMMA * np.einsum("i,j,ijk->ijk", x, y, T[:, :, FLOOR])
                    for flat in np.argsort(tp, axis=None)[:3]:  # investigate: the worst tips get pins
                        i, j, _ = np.unravel_index(flat, tp.shape)
                        known[i, j] = True
            else:
                out["benign"] += 1
                out["benign_blocked"] += blocked
        if strategy.startswith("patrol"):
            for _ in range(budget):
                if strategy == "patrol_random":
                    i, j = rng.integers(0, N, 2)
                elif strategy == "patrol_zigzag":
                    i, j = next(zig)
                else:  # patrol_traffic: walk the busiest gaps not yet pinned
                    t = np.where(known, -1, traffic)
                    i, j = np.unravel_index(np.argmax(t), t.shape)
                out["probes"] += 1
                known[i, j] = True
        out["pins_by_round"].append(int(known.sum()))
    return out


if __name__ == "__main__":
    res = {}
    for strat in ("none", "wall", "reactive", "patrol_random", "patrol_zigzag", "patrol_traffic"):
        runs = [run(s, strat) for s in range(8)]
        agg = {k: round(float(np.mean([r[k] for r in runs])), 1) for k in ("late_breaks", "breaks", "blocked_breaks", "benign_blocked", "benign", "probes")}
        agg["benign_blocked_pct"] = round(100 * agg["benign_blocked"] / agg["benign"], 1)
        agg["final_pins"] = round(float(np.mean([r["pins_by_round"][-1] for r in runs])), 1)
        res[strat] = agg
    Path(__file__).with_name("alignment_patrol_results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
