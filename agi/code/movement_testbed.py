#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
movement_testbed.py — do the recent Shovelcat ideas give a measurable edge on
                      MOVEMENT, against vanilla baselines? Two clean, self-
                      generating tasks with exact ground truth.

TEST 1 — Redundant-arm inverse kinematics (fine motor).
  Ideas under test:
    * trapdoor: forward FK is one-shot O(N); inverse IK must iterate.
    * the .14 reserve = the arm's NULL-SPACE (redundant DOF kept open) used for a
      secondary objective (stay off the joint limits) WITHOUT hurting the reach.
    * the jet = force-cancellation reaching (damped least squares).
  Baseline A: DLS reach only. Method B: DLS reach + null-space comfort (the reserve).
  Win condition for the idea: B reaches as well as A but with far fewer joint-limit
  saturations — i.e. keeping the reserve open is load-bearing, not decoration.

TEST 2 — Bidirectional pathfinding (coordination / spatial awareness).
  Ideas under test:
    * the double bounce = meet-in-the-middle search vs forward-only (node expansions).
    * the seam = the min-cut doorway; claim: the two frontiers MEET at the doorway.
    * experience = cache the doorway; reuse it to replan fast when the map changes.
  Baseline: forward BFS. Method: bidirectional BFS. Plus a doorway-cache replanning test.

Everything is numpy + stdlib, seeded, exact ground truth. A LOOK with clean numbers,
not a claim about AGI — the honest question is "does the framework construct beat the
vanilla baseline on a task where we know the right answer."
"""

import numpy as np
from collections import deque

RNG = np.random.default_rng(7)

# ============================================================================
# TEST 1 — Redundant-arm IK
# ============================================================================

def fk(theta, L):
    """Forward kinematics: joint angles -> (tip, joint_positions). One-shot, O(N)."""
    ang = np.cumsum(theta)
    pts = np.zeros((len(theta) + 1, 2))
    for i in range(len(theta)):
        pts[i + 1] = pts[i] + L[i] * np.array([np.cos(ang[i]), np.sin(ang[i])])
    return pts[-1], pts

def jacobian(theta, L):
    """2xN planar Jacobian d(tip)/d(theta)."""
    tip, pts = fk(theta, L)
    J = np.zeros((2, len(theta)))
    for i in range(len(theta)):
        d = tip - pts[i]                      # lever arm from joint i to tip
        J[:, i] = np.array([-d[1], d[0]])     # perpendicular = rotational velocity
    return J

def ik_solve(target, theta0, L, lim, use_reserve, lam=0.1, iters=200, tol=1e-3):
    """Damped-least-squares reach. If use_reserve, add null-space push toward joint
    center (the redundant reserve serving a secondary comfort objective)."""
    theta = theta0.copy()
    center = np.zeros_like(theta)             # comfortable posture = mid-range
    for _ in range(iters):
        tip, _ = fk(theta, L)
        e = target - tip
        if np.linalg.norm(e) < tol:
            break
        J = jacobian(theta, L)
        JJt = J @ J.T + (lam ** 2) * np.eye(2)
        Jpinv = J.T @ np.linalg.inv(JJt)      # damped pseudo-inverse
        dtheta = Jpinv @ e                     # the reach (the jet / force-cancel)
        if use_reserve:
            # secondary gradient: pull toward center, projected into the null space
            z = -0.15 * (theta - center)
            N = np.eye(len(theta)) - Jpinv @ J  # null-space projector (the reserve)
            dtheta = dtheta + N @ z
        theta = theta + dtheta
        theta = np.clip(theta, lim[0], lim[1])
    tip, _ = fk(theta, L)
    err = float(np.linalg.norm(target - tip))
    margin = float(np.min(np.minimum(theta - lim[0], lim[1] - theta)))  # nearest limit
    saturated = int(np.any(np.abs(theta - lim[0]) < 1e-3) or np.any(np.abs(theta - lim[1]) < 1e-3))
    return err, margin, saturated

def run_ik(N=5, trials=300):
    L = np.ones(N)
    lim = (-2.2, 2.2)
    reach = 0.6 * N            # ask for targets well inside the workspace
    res = {"A": [], "B": []}
    sat = {"A": 0, "B": 0}
    solved = {"A": 0, "B": 0}
    margins = {"A": [], "B": []}
    for _ in range(trials):
        ang = RNG.uniform(0, 2 * np.pi)
        r = RNG.uniform(0.3 * reach, reach)
        target = r * np.array([np.cos(ang), np.sin(ang)])
        theta0 = RNG.uniform(-0.5, 0.5, N)
        for key, use in (("A", False), ("B", True)):
            err, margin, s = ik_solve(target, theta0, L, lim, use_reserve=use)
            res[key].append(err); margins[key].append(margin)
            sat[key] += s
            solved[key] += int(err < 1e-2)
    print("=" * 70)
    print("  TEST 1 — Redundant-arm IK (N =", N, "links, 2-D target => 3 redundant DOF)")
    print("=" * 70)
    print("  the trapdoor: FK is one matrix pass; IK took up to 200 iterations to invert.")
    print(f"  {'method':34s}  reach%   med_err   joint-limit hits   mean nearest-limit")
    for key, name in (("A", "A: DLS reach only (baseline)"),
                      ("B", "B: DLS + null-space reserve")):
        rr = 100 * solved[key] / trials
        me = float(np.median(res[key]))
        print(f"  {name:34s}  {rr:5.1f}   {me:7.4f}   {sat[key]:3d}/{trials:<12d}  {np.mean(margins[key]):.3f}")
    print()
    print("  READ: if B reaches ~as well as A but with far fewer limit hits and a bigger")
    print("  nearest-limit margin, the open reserve (null space) is load-bearing.")
    return dict(solvedA=solved["A"], solvedB=solved["B"], satA=sat["A"], satB=sat["B"],
                trials=trials, marginA=float(np.mean(margins["A"])), marginB=float(np.mean(margins["B"])))

# ============================================================================
# TEST 2 — Bidirectional pathfinding
# ============================================================================

def neighbors(cell, grid):
    y, x = cell
    H, W = grid.shape
    for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny, nx = y+dy, x+dx
        if 0 <= ny < H and 0 <= nx < W and grid[ny, nx] == 0:
            yield (ny, nx)

def bfs_forward(grid, start, goal):
    """Vanilla forward BFS. Returns (found, expansions)."""
    seen = {start}; q = deque([start]); exp = 0
    while q:
        c = q.popleft(); exp += 1
        if c == goal:
            return True, exp
        for n in neighbors(c, grid):
            if n not in seen:
                seen.add(n); q.append(n)
    return False, exp

def bfs_bidirectional(grid, start, goal):
    """Meet-in-the-middle BFS. Returns (found, expansions, meeting_cell)."""
    if start == goal:
        return True, 0, start
    fseen = {start}; bseen = {goal}
    fq = deque([start]); bq = deque([goal]); exp = 0
    while fq and bq:
        # expand the smaller frontier (balanced growth)
        q, seen, other = (fq, fseen, bseen) if len(fq) <= len(bq) else (bq, bseen, fseen)
        for _ in range(len(q)):
            c = q.popleft(); exp += 1
            for n in neighbors(c, grid):
                if n in other:
                    return True, exp, n
                if n not in seen:
                    seen.add(n); q.append(n)
    return False, exp, None

def make_doorway_maze(H=41, W=41, gap_row=None):
    """Two rooms split by a vertical wall with a single 1-cell doorway = the min-cut."""
    grid = np.zeros((H, W), dtype=int)
    wallx = W // 2
    grid[:, wallx] = 1
    if gap_row is None:
        gap_row = RNG.integers(2, H - 2)
    grid[gap_row, wallx] = 0                 # the doorway
    # scatter light obstacles in both rooms (never on the doorway column)
    for _ in range((H * W) // 12):
        y, x = RNG.integers(0, H), RNG.integers(0, W)
        if x != wallx:
            grid[y, x] = 1
    start = (H // 2, 1); goal = (H // 2, W - 2)
    grid[start] = 0; grid[goal] = 0
    return grid, start, goal, (gap_row, wallx)

def run_paths(trials=200):
    print("=" * 70)
    print("  TEST 2 — Bidirectional pathfinding (meet-in-the-middle vs forward)")
    print("=" * 70)
    ratios = []; door_hits = []; door_dists = []
    both_found = 0
    for _ in range(trials):
        grid, start, goal, door = make_doorway_maze()
        f_found, f_exp = bfs_forward(grid, start, goal)
        b_found, b_exp, meet = bfs_bidirectional(grid, start, goal)
        if not (f_found and b_found):
            continue
        both_found += 1
        ratios.append(b_exp / max(1, f_exp))
        if meet is not None:
            d = abs(meet[0] - door[0]) + abs(meet[1] - door[1])
            door_dists.append(d)
            door_hits.append(int(d <= 2))
    print(f"  solved by both: {both_found}/{trials}")
    print(f"  expansions  bidirectional / forward : median {np.median(ratios):.2f}x"
          f"  (mean {np.mean(ratios):.2f}x)  — <1 means fewer nodes touched")
    print(f"  meeting point lands on the doorway (min-cut seam): "
          f"{100*np.mean(door_hits):.0f}%  within 2 cells; median dist {np.median(door_dists):.1f}")
    print()

    # --- experience: cache the doorway, reuse it to replan on a changed map ---
    print("  EXPERIENCE test — cache the doorway, replan when the map changes:")
    fresh_exp = []; cached_exp = []
    for _ in range(trials):
        grid, start, goal, door = make_doorway_maze()
        b_found, _, meet = bfs_bidirectional(grid, start, goal)
        if not b_found or meet is None:
            continue
        # change the map: reshuffle obstacles in the rooms, keep the SAME doorway
        grid2 = grid.copy()
        wallx = door[1]
        grid2[:, :] = 0; grid2[:, wallx] = 1; grid2[door[0], wallx] = 0
        for _ in range((grid.shape[0]*grid.shape[1])//12):
            y, x = RNG.integers(0, grid.shape[0]), RNG.integers(0, grid.shape[1])
            if x != wallx: grid2[y, x] = 1
        grid2[start] = 0; grid2[goal] = 0; grid2[door[0], wallx] = 0
        # fresh: full bidirectional again
        _, fx, _ = bfs_bidirectional(grid2, start, goal)
        # cached: route through the remembered doorway = two short bidirectional legs
        okA, xa, _ = bfs_bidirectional(grid2, start, door)
        okB, xb, _ = bfs_bidirectional(grid2, door, goal)
        if okA and okB:
            fresh_exp.append(fx); cached_exp.append(xa + xb)
    if fresh_exp:
        r = np.array(cached_exp) / np.maximum(1, np.array(fresh_exp))
        print(f"    replan via cached doorway vs fresh search: median {np.median(r):.2f}x expansions"
              f"  (n={len(fresh_exp)})")
    print()
    return dict(ratio_med=float(np.median(ratios)), door_hit=float(np.mean(door_hits)),
                cached_ratio=float(np.median(r)) if fresh_exp else None)

# ============================================================================
# TEST 3 — Dynamics: sustain a NON-EQUILIBRIUM pose over time (the statics->dynamics turn)
# ============================================================================

def run_hold(N=4, dt=0.004, T=2.2):
    """Hold an arm HORIZONTAL (higher energy) instead of letting it relax to HANGING
    (rest / lowest energy), paid out of the reserve budget — and TEAR when a perturbation
    drives a joint past its range (|theta| > tear). Movement = holding the band, bounded
    by the tear threshold. Per-joint pendulum model (coupling ignored — flagged)."""
    g = 9.8
    Gi = g * np.arange(N, 0, -1)              # gravity load per joint (base heaviest)
    Ii = np.arange(N, 0, -1).astype(float)    # inertia ~ outboard mass
    tear = 1.7                                # |theta| > tear  => the fiber tears
    Kp, Kd = 80.0, 16.0
    steps = int(T / dt)

    def sim(control, reserve, kick=0.0):
        th = np.zeros(N); w = np.zeros(N)     # start AT the target (horizontal)
        w[0] += kick                          # impulse to the base joint
        torn = False
        for _ in range(steps):
            tg = -Gi * np.cos(th)             # gravity pulls toward hanging (-pi/2)
            if control:
                tc = np.clip(Kp * (0.0 - th) - Kd * w, -(Gi + reserve), (Gi + reserve))
            else:
                tc = np.zeros(N)
            w = (w + dt * (tc + tg) / Ii) * 0.999
            th = th + dt * w
            if np.any(np.abs(th) > tear):
                torn = True; break
        return float(np.mean(np.sin(th))), float(np.mean(np.abs(th) < 0.3)), torn

    hA, tA, _ = sim(control=False, reserve=0.0)
    hB, tB, _ = sim(control=True,  reserve=8.0)
    print("=" * 70)
    print("  TEST 3 — DYNAMICS: hold a non-equilibrium pose (arm horizontal) over time")
    print("=" * 70)
    print(f"  {'controller':40s}  mean height   on-target")
    print(f"    (0.0 = held horizontal, -1.0 = collapsed to hanging)")
    print(f"  {'A: no budget (relaxes to rest)':40s}   {hA:+.2f}        {100*tA:.0f}%")
    print(f"  {'B: reserve budget holds the pose':40s}   {hB:+.2f}        {100*tB:.0f}%")
    print("  -> the rest-seeking arm FALLS to hanging; the reserve budget SUSTAINS the")
    print("     higher-energy pose. That is movement: not settling to the floor.")
    print()
    print("  reserve budget  ->  largest impulse absorbed before a joint TEARS (|theta|>1.7):")
    rows = []
    for reserve in (2.0, 6.0, 18.0):
        best = 0.0
        for kick in np.arange(0.5, 40.0, 0.5):
            _, _, torn = sim(control=True, reserve=reserve, kick=float(kick))
            if torn: break
            best = float(kick)
        rows.append((reserve, best))
        print(f"    reserve = {reserve:5.1f}   ->  max impulse held = {best:5.1f}")
    print("  -> bigger leftover budget = bigger perturbation sustained before tearing;")
    print("     the reserve IS 'how much movement/disturbance you can hold in range.'")
    print()
    return dict(hA=hA, hB=hB, tearA_ontarget=tA, tearB_ontarget=tB, tear_curve=rows)


# ============================================================================
# TEST 4 — Metabolic reserve: flow in/out, burst-then-fatigue, refill (the endurance law)
# ============================================================================

def run_metabolic(N=3, dt=0.005):
    """The reserve made DYNAMIC: a tank R0 that refills at supply s and drains at demand d.
    Prediction: d<=s -> sustainable forever; d>s -> hold for ~R0/(d-s) then the tank empties
    and the pose tears/collapses. Part A = the pure law; Part B = an embodied arm that
    actually falls at the predicted time; Part C = recover on a slow supply.
    NB: one GENERIC throughput/refill — the border-specific pore caps (per-material flux,
    the k/temperature axis, the pinned 0.627 saturation) are abstracted away (Jonathan's caveat)."""
    g = 9.8
    Gi = g * np.arange(N, 0, -1); Ii = np.arange(N, 0, -1).astype(float)
    tear = 1.7; Kp, Kd = 80.0, 16.0; R0 = 100.0

    print("=" * 70)
    print("  TEST 4 — Metabolic reserve: the endurance law (flow, burst, fatigue, refill)")
    print("=" * 70)

    # --- Part A: the pure endurance law ---
    print("  A. time-to-failure vs demand d, at supply s   (R0 = 100)")
    print(f"     {'s':>4} {'d':>4}   {'measured TTF':>14}   {'predicted R0/(d-s)':>18}")
    for s in (3.0, 6.0):
        for d in (1.0, 2.0, 4.0, 5.0, 8.0, 12.0):
            R = R0; t = 0.0
            while t < 2000:
                R = min(R0, R + (s - d) * dt)
                if R <= 0: break
                t += dt
            ttf = f"{t:8.1f}s" if R <= 0 else "  sustainable"
            pred = f"{R0/(d-s):8.1f}s" if d > s else "  infinite"
            print(f"     {s:4.0f} {d:4.0f}   {ttf:>14}   {pred:>18}")
    print("     -> below the supply line it holds forever; above it, fatigue = R0/(d-s).")
    print()

    # --- Part B: embodied arm — control authority gated by the reserve ---
    def sim_arm(d_hold, s, T=120.0):
        th = np.zeros(N); w = np.zeros(N); R = R0; t = 0.0; fail_t = None
        while t < T:
            tg = -Gi * np.cos(th)
            if R > 0:
                auth = 1.0
                R = R - max(0.0, d_hold - s) * dt
                if d_hold < s: R = min(R0, R + (s - d_hold) * dt)
            else:
                auth = min(1.0, s / d_hold)          # tank empty: throttled to the supply
            tmax = (Gi + 5.0) * auth
            tc = np.clip(Kp * (0.0 - th) - Kd * w, -tmax, tmax)
            w = (w + dt * (tc + tg) / Ii) * 0.999
            th = th + dt * w
            if fail_t is None and (np.any(np.abs(th) > tear) or np.mean(np.sin(th)) < -0.7):
                fail_t = t
            t += dt
        return fail_t

    print("  B. embodied arm holding horizontal, authority drawn from the reserve (s = 5):")
    print(f"     {'load (d_hold)':>14}   {'outcome':>26}   {'predicted fail':>16}")
    for d_hold in (3.0, 8.0, 15.0):
        ft = sim_arm(d_hold, s=5.0)
        out = f"{ft:6.1f}s  fatigued & fell" if ft is not None else "held (sustainable)"
        pred = f"{R0/(d_hold-5.0):6.1f}s" if d_hold > 5.0 else "  —"
        print(f"     {d_hold:14.0f}   {out:>26}   {pred:>16}")
    print("     -> light load (< supply) holds forever; heavy load fatigues and falls")
    print("        right around R0/(d-s), the tank running dry.")
    print()

    # --- Part C: recover on a slow supply ---
    R = 20.0; s = 6.0; d = 2.0; t = 0.0
    while R < R0 and t < 2000:
        R = min(R0, R + (s - d) * dt); t += dt
    print(f"  C. recover: reserve 20 -> 100 on a slow net supply (s-d = {s-d:.0f}): "
          f"{t:.1f}s measured vs {(R0-20)/(s-d):.1f}s predicted.")
    print("     -> 'do other work or wait' literally refills the tank at the net inflow rate.")
    print()
    return dict(law="R0/(d-s)")


if __name__ == "__main__":
    ik = run_ik()
    pth = run_paths()
    hold = run_hold()
    meta = run_metabolic()
    print("=" * 70)
    print("  VERDICT (honest)")
    print("=" * 70)
    print("  These are known-good techniques the framework *predicts* from its own geometry")
    print("  (null-space redundancy, bidirectional search, waypoint caching). The test is")
    print("  whether the framework's recent ideas map to a MEASURABLE edge on movement —")
    print("  and, unlike the detector, the ground truth here is exact so the numbers are clean.")
