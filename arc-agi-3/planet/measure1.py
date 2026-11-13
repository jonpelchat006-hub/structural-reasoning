#!/usr/bin/env python3
"""measure1.py — MEASUREMENT 1: does a blank neurofungus, fed only unexplained pixels,
deepen its columns where the oracle solvers know the game's structure lives?
Runs: the fungus; a UNIFORM control (dig every level under every region); a RANDOM
control (same number of digs, placed at random, best of 20); a SHUFFLED control
(frames in random order — no dynamics to learn: the fungus should starve)."""
import sys, time
import numpy as np
sys.path.insert(0, "/root/arc")
import planet_ocean as po
from neurofungus import Fungus

PATHS = ["/root/arc/replay_ls20_L1L2.npz", "/root/arc/replay_ls20_L2probe.npz"]


def fungus_run(sub, iters, seed=0, cps=12):
    f = Fungus(sub, frozenset(), seed=seed, max_children=3, max_depth=400, spores_every=10, n_spores=4,
               anastomosis_min_overlap=0.15, require_authentic=False, inherit_exhausted=True)
    # candidates_per_step is a tree.expand arg; wrap step to pass it
    orig = f.tree.expand
    f.tree.expand = lambda leaf, rng, candidates_per_step=6, **kw: orig(leaf, rng, candidates_per_step=cps, **kw)
    best = f.run(iters)
    return f, best


def report(name, sub, state, extra=""):
    score, err, e0 = sub.evaluate(state)
    print(f"{name:10s} explained {score:6.0f}/{sub.E0} ({100*score/sub.E0:5.1f}%)  digs={len(state):3d} {extra}")
    return score, err, e0


if __name__ == "__main__":
    t0 = time.time()
    reps = po.load_replays(PATHS)
    sub = po.OceanSubstrate(reps)
    f, best = fungus_run(sub, iters=1500)
    sc, err, e0 = report("FUNGUS", sub, best.state,
                         f"nodes={len(f.tree.nodes)} stations={len(f.stations())} anastomoses={f.field.anastomosis_successes}")
    # UNIFORM: everything dug everywhere
    allstate = frozenset((i, j, lv) for i in range(po.NR) for j in range(po.NR) for lv in po.LEVELS)
    su, erru, _ = report("UNIFORM", sub, allstate)
    # RANDOM: same number of digs, best of 20 random placements
    rng = np.random.default_rng(1)
    cands = sorted(allstate)
    rs = []
    for k in range(20):
        pick = frozenset(cands[i] for i in rng.choice(len(cands), size=len(best.state), replace=False))
        rs.append(sub.score(pick))
    print(f"{'RANDOM':10s} explained best-of-20 {max(rs):6.0f} ({100*max(rs)/sub.E0:5.1f}%)  mean {np.mean(rs):6.0f} ({100*np.mean(rs)/sub.E0:5.1f}%)")
    # SHUFFLED: frames in random order (actions kept aligned to their frame) — no dynamics
    sreps = []
    for r in reps:
        perm = rng.permutation(r.T)
        sreps.append(po.Replay(r.F[perm], np.array(r.A)[perm], r.L[perm]))
    ssub = po.OceanSubstrate(sreps)
    fs, bests = fungus_run(ssub, iters=600)
    report("SHUFFLED", ssub, bests.state, f"(E0 shuffled = {ssub.E0})")

    dm = po.depth_map(best.state)
    print("\nFUNGUS depth map (regions, rows top->bottom; . = surface, 1-3 memory, 4 mover, 5 counter; max shown):")
    for i in range(po.NR):
        row = []
        for j in range(po.NR):
            lv = sorted(l for (a, b, l) in best.state if a == i and b == j)
            row.append("".join(str(x) for x in lv) if lv else ".")
        print("  " + " ".join(f"{c:>5s}" for c in row))
    print("\nexplained fraction per region (fungus):")
    for i in range(po.NR):
        print("  " + " ".join(f"{(1-err[i,j]/e0[i,j])*100:5.0f}" if e0[i, j] else "    -" for j in range(po.NR)))
    print("\noracle spots:")
    for name, (r, c) in po.ORACLE.items():
        i, j = r // po.TILE, c // po.TILE
        lv = sorted(l for (a, b, l) in best.state if a == i and b == j)
        print(f"  {name:28s} region({i},{j}) digs={lv} explained {100*(1-err[i,j]/max(1,e0[i,j])):5.1f}%  (uniform {100*(1-erru[i,j]/max(1,e0[i,j])):5.1f}%)")
    # where is the residual? top unexplained (t, region) events of the fungus state
    print("\nLIGHTNING CANDIDATES — the biggest unexplained single steps (replay, step, action, region, px):")
    events = []
    for ri, rp in enumerate(reps):
        levels = {}
        for (i, j, lv) in best.state: levels.setdefault((i, j), set()).add(lv)
        for (i, j), lv in levels.items():
            _, steps = sub.region_error(i, j, lv)
            # steps are concatenated over replays in order
            off = sum(r.T - 1 for r in reps[:ri])
            seg = steps[off:off + rp.T - 1]
            for t in np.argsort(seg)[::-1][:2]:
                if seg[t] > 30: events.append((int(seg[t]), ri, int(t), rp.A[t + 1], (i, j)))
    for e in sorted(events, reverse=True)[:12]:
        print(f"  {e[0]:4d} px  replay{e[1]} step {e[2]:3d} {e[3]:8s} region{e[4]}")
    print(f"\n[{time.time()-t0:.0f}s]")
    np.savez_compressed("/root/arc/measure1_result.npz", depth=dm, resid=err, e0=e0, resid_uniform=erru,
                        state=np.array(sorted(best.state)), history=np.array(f.history))
