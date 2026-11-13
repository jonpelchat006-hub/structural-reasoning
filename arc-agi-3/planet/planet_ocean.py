#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
planet_ocean.py — the SURFACE OCEAN as a neurofungus substrate.

The food is unexplained pixels. A replay (frames F[t], actions A[t]) is a
64x64 surface cut into 8x8 regions (the tiles). Under each region a COLUMN
can be dug one level at a time; each level is a predictor of the region's
next tile with a wider key than the level above it, falling back to the
level above when its key was never seen:

  L0 (the flat surface, free) : tile(t+1) = tile(t)
  L1 action memory            : (action, tile)                       -> next tile
  L2 neighborhood memory      : (action, tile, 4 neighbour tiles)    -> next tile
  L3 context memory           : (action, tile, neighbours, level, bar bucket) -> next tile

Scoring is PREQUENTIAL (online): frame t+1 is predicted only from memory
built on frames <= t, so memorizing a frame you have already seen earns
nothing — only structure that RECURS is food. Score = pixels explained over
the flat surface (E0 - E). target_score = E0 (everything explained).

A commitment is (region, level). Realize = dig that level and keep it only
if the region's error strictly drops (else 'no_gain'). Spores = a few random
extra digs on the best state. Anastomosis = union of two dig-sets.

Measurement 1 asks: with NO knowledge of the game, do the columns deepen at
the places the oracle solvers know were decisive (keyhole, rings, box, HUD
glyph, the agent's lattice), and does the surface elsewhere become GROUND
(fully predicted / exhausted)?
"""
from __future__ import annotations
import sys, json, hashlib, math
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

sys.path.insert(0, "/root/arc")
from neurofungus import Substrate, Fungus

TILE = 8
NR = 64 // TILE                      # 8x8 regions
LEVELS = (1, 2, 3, 4, 5)
MEMORY = (1, 2, 3)
SHIFT, COUNTER = 4, 5
SHIFTS = [(dy, dx) for dy in range(-8, 9) for dx in range(-8, 9)]


def tiles_of(frame: np.ndarray) -> np.ndarray:
    return frame.reshape(NR, TILE, NR, TILE).swapaxes(1, 2)   # (NR, NR, TILE, TILE)


class Replay:
    def __init__(self, F: np.ndarray, A: np.ndarray, L: np.ndarray):
        self.F = F.astype(np.int16); self.A = [str(a) for a in A]; self.L = L
        self.T = len(F)
        self.tiles = np.stack([tiles_of(f) for f in self.F])   # (T, NR, NR, 8, 8)
        # tile byte keys
        self.key = [[[self.tiles[t, i, j].tobytes() for j in range(NR)] for i in range(NR)] for t in range(self.T)]
        self.bar = [int((f[56:] == 11).sum()) // 8 for f in self.F]
        # flat-surface error per region per step (E0)
        self.e0 = np.zeros((self.T - 1, NR, NR), int)
        for t in range(self.T - 1):
            self.e0[t] = (self.tiles[t + 1] != self.tiles[t]).sum(axis=(2, 3))
        self._learn_online()

    def _learn_online(self):
        """Online (prequential) species, learned from steps < t only, predicting frame t+1
        from frame t. Both produce FULL-FRAME predictions (regions crop them).
        MOVER : per action a, displacement d_a (votes) + mobile colours; only the connected
                object that changed on the previous step is moved (the thing the hand drives).
        COUNTER: per (action, colour), the pixel-count delta and the end it is taken from
                (L/R/T/B); applied to the whole run of that colour in the frame (a register)."""
        from scipy import ndimage
        T, F = self.T, self.F
        self.mover_pred = np.stack([F[t].copy() for t in range(T)])
        self.counter_pred = np.stack([F[t].copy() for t in range(T)])
        votes = defaultdict(lambda: np.zeros(len(SHIFTS), float))
        mobile = defaultdict(Counter)
        chist = defaultdict(list)          # (a, c) -> [(delta, end)]
        reg_box = {}                       # c -> bbox of the run that last lost pixels
        for t in range(T - 1):
            a = self.A[t + 1]
            # ---- MOVER prediction for t+1 ----
            if votes[a].sum() > 0 and t > 0:
                dy, dx = SHIFTS[int(np.argmax(votes[a]))]
                mob = {c for c, n in mobile[a].items() if n >= 1}
                prev_changed = (F[t] != F[t - 1]) & np.isin(F[t], list(mob)) if mob else np.zeros_like(F[t], bool)
                if prev_changed.any() and (dy or dx):
                    lab, n = ndimage.label(np.isin(F[t], list(mob)))
                    ids = set(np.unique(lab[prev_changed])) - {0}
                    obj = np.isin(lab, list(ids))
                    ys, xs = np.where(obj)
                    if 0 < len(ys) <= 200:
                        pred = F[t].copy()
                        bg = F[t - 1]
                        pred[ys, xs] = np.where(bg[ys, xs] != F[t][ys, xs], bg[ys, xs],
                                                self._bg_color(F[t], ys, xs, exclude=None, avoid=mob))
                        ny, nx = ys + dy, xs + dx
                        ok = (ny >= 0) & (ny < 64) & (nx >= 0) & (nx < 64)
                        pred[ny[ok], nx[ok]] = F[t][ys[ok], xs[ok]]
                        self.mover_pred[t] = pred
            # ---- COUNTER prediction for t+1 ----
            pred = F[t].copy(); touched = False
            for (aa, c), h in chist.items():
                if aa != a or len(h) < 2: continue
                delta = int(np.median([d for d, _ in h])); end = Counter(e for _, e in h).most_common(1)[0][0]
                if delta >= 0: continue
                lab, n = ndimage.label(F[t] == c)
                if n == 0: continue
                sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
                big = 1 + int(np.argmax(sizes))
                if c in reg_box:                       # the register = the run the last loss ate INTO
                    ids = [int(lab[y, x]) for y, x in reg_box[c] if lab[y, x] > 0]
                    if ids: big = Counter(ids).most_common(1)[0][0]
                ys, xs = np.where(lab == big)
                order = np.argsort(xs, kind="stable") if end in ("L", "R") else np.argsort(ys, kind="stable")
                if end in ("R", "B"): order = order[::-1]
                take = order[:min(-delta, len(order))]
                oy, ox = {"L": (0, -1), "R": (0, 1), "T": (-1, 0), "B": (1, 0)}[end]
                # fill with what lies just OUTSIDE the run at that end (the colour the register reveals)
                ny, nx = np.clip(ys.min() + oy if end == "T" else (ys.max() + oy if end == "B" else ys[take]), 0, 63), \
                         np.clip(xs.min() + ox if end == "L" else (xs.max() + ox if end == "R" else xs[take]), 0, 63)
                fill = F[t][ny, nx]
                fill = np.where(fill == c, self._bg_color(F[t], ys[take], xs[take], exclude=int(c)), fill)
                pred[ys[take], xs[take]] = fill
                touched = True
            if touched: self.counter_pred[t] = pred
            # ---- learn from the real transition t -> t+1 ----
            ch = np.argwhere(F[t + 1] != F[t])
            if len(ch) and len(ch) < 400:
                old = F[t][ch[:, 0], ch[:, 1]]; new = F[t + 1][ch[:, 0], ch[:, 1]]
                freq = Counter(F[t].ravel().tolist())
                w = {int(c): 1.0 / math.sqrt(max(1, freq[int(c)])) for c in np.unique(np.concatenate([old, new]))}
                for c in np.unique(new):
                    if (old == c).any() and (new == c).any() and freq[int(c)] < 800: mobile[a][int(c)] += 1
                src = {(int(y), int(x)): int(F[t][y, x]) for y, x in ch}
                dst = {(int(y), int(x)): int(F[t + 1][y, x]) for y, x in ch}
                for k, (dy, dx) in enumerate(SHIFTS):
                    if dy == 0 and dx == 0: continue
                    votes[a][k] += sum(w[c] for (y, x), c in src.items()
                                       if c != dst.get((y, x), c) and dst.get((y + dy, x + dx)) == c)
                # counter: colours whose total count changed by a small amount at one end
                for c in np.unique(old):
                    c = int(c)
                    d = int((F[t + 1] == c).sum() - (F[t] == c).sum())
                    if d == 0 or abs(d) > 8: continue
                    lost = (F[t] == c) & (F[t + 1] != c)
                    ys, xs = np.where(lost)
                    if len(ys) == 0: continue
                    lab0, _ = ndimage.label(F[t] == c)
                    ay, ax = np.where(np.isin(lab0, np.unique(lab0[lost])) & (lab0 > 0))   # the run itself
                    cx, cy = xs.mean(), ys.mean(); mx, my = ax.mean(), ay.mean()
                    end = ("R" if cx > mx else "L") if abs(cx - mx) >= abs(cy - my) else ("B" if cy > my else "T")
                    chist[(a, c)].append((d, end))
                    iy, ix = {"L": (0, 1), "R": (0, -1), "T": (1, 0), "B": (-1, 0)}[end]
                    inside = [(int(y + iy * k), int(x + ix * k)) for y, x in zip(ys, xs) for k in (1, 2, 3)]
                    reg_box[c] = [(y, x) for y, x in inside if 0 <= y < 64 and 0 <= x < 64 and F[t + 1][y, x] == c]

    @staticmethod
    def _bg_color(frame, ys, xs, exclude=None, avoid=()):
        """Most common colour in a 3-px halo around the given pixels (excluding some colours)."""
        y0, y1 = max(0, ys.min() - 3), min(64, ys.max() + 4); x0, x1 = max(0, xs.min() - 3), min(64, xs.max() + 4)
        win = frame[y0:y1, x0:x1]
        cnt = Counter(win.ravel().tolist())
        if exclude is not None: cnt.pop(exclude, None)
        for c in (avoid or ()): cnt.pop(int(c), None)
        return cnt.most_common(1)[0][0] if cnt else 0

    def nbr_key(self, t, i, j) -> bytes:
        h = hashlib.blake2b(digest_size=8)
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ii, jj = i + di, j + dj
            h.update(self.key[t][ii][jj] if 0 <= ii < NR and 0 <= jj < NR else b"edge")
        return h.digest()


class OceanSubstrate(Substrate):
    """state = frozenset of (i, j, level) digs."""
    def __init__(self, replays: List[Replay], seed: int = 0):
        self.replays = replays
        self.rng = np.random.default_rng(seed)
        self.E0 = sum(r.e0.sum() for r in replays)
        self.target_score = float(self.E0)
        self._cache: Dict[frozenset, Tuple[float, np.ndarray, np.ndarray]] = {}

    # --- the predictor stack, evaluated online for ONE region ---
    def region_error(self, i: int, j: int, levels: Set[int]) -> Tuple[int, np.ndarray]:
        """Return (error pixels, per-step error) for region (i,j) with the given dig levels."""
        err_steps = []
        for rp in self.replays:
            mem = {lv: {} for lv in levels if lv in MEMORY}            # level -> key -> Counter(next tile bytes)
            for t in range(rp.T - 1):
                a = rp.A[t + 1]                       # action that produced frame t+1
                cur = rp.key[t][i][j]
                keys = {}
                if 1 in levels: keys[1] = (a, cur)
                if 2 in levels: keys[2] = (a, cur, rp.nbr_key(t, i, j))
                if 3 in levels: keys[3] = (a, cur, rp.nbr_key(t, i, j), int(rp.L[t]), rp.bar[t])
                pred = None
                for lv in (3, 2, 1):
                    if lv in keys and keys[lv] in mem[lv]:
                        pred = mem[lv][keys[lv]].most_common(1)[0][0]; break
                nxt = rp.key[t + 1][i][j]
                if pred is None:
                    base = rp.tiles[t, i, j]
                    st = rp.tiles[t, i, j]
                    if SHIFT in levels:
                        mv = rp.mover_pred[t, i*TILE:(i+1)*TILE, j*TILE:(j+1)*TILE]
                        base = np.where(mv != st, mv, base)
                    if COUNTER in levels:
                        ct = rp.counter_pred[t, i*TILE:(i+1)*TILE, j*TILE:(j+1)*TILE]
                        base = np.where(ct != st, ct, base)
                    e = int((base != rp.tiles[t + 1, i, j]).sum())
                else:
                    e = int((np.frombuffer(pred, dtype=np.int16) != np.frombuffer(nxt, dtype=np.int16)).sum())
                err_steps.append(e)
                for lv, k in keys.items():
                    mem[lv].setdefault(k, Counter())[nxt] += 1
        arr = np.array(err_steps, int)
        return int(arr.sum()), arr

    def evaluate(self, state: frozenset) -> Tuple[float, np.ndarray, np.ndarray]:
        if state in self._cache:
            return self._cache[state]
        levels = defaultdict(set)
        for (i, j, lv) in state:
            levels[(i, j)].add(lv)
        err = np.zeros((NR, NR), int)
        e0 = sum(r.e0.sum(axis=0) for r in self.replays)
        for i in range(NR):
            for j in range(NR):
                err[i, j] = self.region_error(i, j, levels[(i, j)])[0] if levels[(i, j)] else e0[i, j]
        score = float(self.E0 - err.sum())
        self._cache[state] = (score, err, e0)
        return self._cache[state]

    # --- Substrate interface ---
    def score(self, state) -> float: return self.evaluate(state)[0]
    def spine(self, state) -> Set: return set(state)

    def candidates(self, state, k, stations, rng) -> List[Tuple[int, int, int]]:
        _, err, _ = self.evaluate(state)
        have = defaultdict(set)
        for (i, j, lv) in state: have[(i, j)].add(lv)
        boost = Counter()
        for sp, smell in stations:
            for (i, j, lv) in sp: boost[(i, j)] += smell
        out = []
        for i in range(NR):
            for j in range(NR):
                if err[i, j] == 0: continue
                opts = []
                nm = min(set(MEMORY) - have[(i, j)], default=None)
                if nm is not None: opts.append(nm)
                for sp in (SHIFT, COUNTER):
                    if sp not in have[(i, j)]: opts.append(sp)
                for lv in opts:
                    pull = err[i, j] * (1.0 + 0.5 * boost[(i, j)]) * (1.0 + 0.3 * rng.random())
                    out.append((pull, (i, j, lv)))
        out.sort(reverse=True)
        return [c for _, c in out[:k]]

    def realize(self, state, commitment, rng):
        new = frozenset(state | {commitment})
        if self.score(new) > self.score(state):
            return new, "ok"
        return None, "no_gain"

    def sow(self, state, n, rng):
        out = []
        all_c = [(i, j, lv) for i in range(NR) for j in range(NR) for lv in LEVELS if (i, j, lv) not in state]
        for _ in range(n):
            m = int(rng.integers(2, 5))
            picks = [all_c[x] for x in rng.choice(len(all_c), size=min(m, len(all_c)), replace=False)]
            st = frozenset(state | set(picks))
            out.append((st, self.score(st)))
        return out

    def fuse(self, a, b, rng):
        return frozenset(a | b)


# ============================================================================
def load_replays(paths: List[str]) -> List[Replay]:
    out = []
    for p in paths:
        d = np.load(p, allow_pickle=False)
        if "A" in d.files:
            out.append(Replay(d["F"], d["A"], d["L"]))
        else:   # probe format: marks "n:ACTION:note"; level inferred from big frame changes
            A = np.array([str(m).split(":")[1] for m in d["marks"]])
            F = d["F"]; L = np.zeros(len(F), int)
            for t in range(1, len(F)):
                L[t] = L[t-1] + (1 if (F[t] != F[t-1])[:52].sum() > 900 else 0)
            out.append(Replay(F, A, L))
    return out


def depth_map(state) -> np.ndarray:
    dm = np.zeros((NR, NR), int)
    for (i, j, lv) in state: dm[i, j] = max(dm[i, j], lv)
    return dm


ORACLE = {  # what the LS20 oracle solvers used (row, col) — pixel coords
    "keyhole L1/L2 (47,51)": (47, 51), "ring nook (51,41)": (51, 41), "ring end (17,16)": (17, 16),
    "goal box L2 (42,16)": (42, 16), "HUD key glyph (58,6)": (58, 6), "fuel bar (60,32)": (60, 32),
    "spawn/agent (42,31)": (42, 31),
}


def run(paths, iters=400, seed=0, log=print):
    reps = load_replays(paths)
    sub = OceanSubstrate(reps, seed)
    fungus = Fungus(sub, frozenset(), seed=seed, max_children=4, max_depth=200, spores_every=8,
                    n_spores=4, anastomosis_min_overlap=0.15, require_authentic=False, log=lambda *a: None)
    best = fungus.run(iters)
    score, err, e0 = sub.evaluate(best.state)
    return sub, fungus, best, score, err, e0


if __name__ == "__main__":
    paths = sys.argv[1:] or ["/root/arc/replay_ls20_L1L2.npz", "/root/arc/replay_ls20_L2probe.npz"]
    sub, fungus, best, score, err, e0 = run(paths)
    dm = depth_map(best.state)
    print(f"flat-surface error E0 = {sub.E0} px ; explained = {score:.0f} ({100*score/sub.E0:.1f}%) ; "
          f"digs = {len(best.state)} ; nodes = {len(fungus.tree.nodes)} ; stations = {len(fungus.stations())} ; "
          f"spores {fungus.field.snapshot()}")
    print("\nDEPTH MAP (max level per 8x8 region; rows top->bottom):")
    for i in range(NR): print("  " + " ".join(str(dm[i, j]) if dm[i, j] else "." for j in range(NR)))
    print("\nRESIDUAL (unexplained px per region):")
    for i in range(NR): print("  " + " ".join(f"{err[i, j]:4d}" for j in range(NR)))
    print("\nFLAT SURFACE E0 per region:")
    for i in range(NR): print("  " + " ".join(f"{e0[i, j]:4d}" for j in range(NR)))
    print("\nORACLE SPOTS -> depth / residual / E0:")
    for name, (r, c) in ORACLE.items():
        i, j = r // TILE, c // TILE
        print(f"  {name:28s} region({i},{j}) depth={dm[i, j]} resid={err[i, j]} e0={e0[i, j]}")
    ground = int(((err == 0) & (e0 > 0)).sum()); never = int((e0 == 0).sum())
    print(f"\nGROUND: {ground} regions fully predicted (of {int((e0>0).sum())} that ever changed); "
          f"{never} regions never changed (bedrock)")
    np.savez_compressed("/root/arc/ocean_result.npz", depth=dm, resid=err, e0=e0,
                        state=np.array(sorted(best.state)), history=np.array(fungus.history))
