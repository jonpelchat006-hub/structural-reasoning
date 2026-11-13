#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
induce.py — TRANSITION INDUCTION: the ARC-AGI-1 inducers run over ARC-AGI-3 presses.

A press is a train pair: (frame, action) -> next frame. Group the recorded presses by action, induce one
operator per action from the early presses, commit it only when it is exactly consistent on the presses it
was fitted to (the operator-induction gate), and score it on the late presses it never saw — the same
early/late split and the same changed-cell metrics as eye.py, so the two columns compare directly.

Ported from D:\shovelcat-colony (June 2026, ARC-AGI-1, 81/400 train):
  displace  arc-proposer induce.ts induceMove + arc-slice discover.ts induceMoveByColor: the mover's cells
            shift by one (dy,dx) per action; floor colours learned from where it went, walls from refusals
  slide     discover.ts induceGravity, applied to the mover: shift in one direction until a wall
  local1/2  prune.ts induceLocalRule: each cell's next value is a function of its (2r+1)^2 neighbourhood.
            The ARC-1 version abstained on the whole task at the first conflict; here conflicting keys
            abstain (predict "unchanged") and the conflict count is the gate
  click     local1 with the clicked component and the distance to the click in the key (ACTION6 only)
  ambient   local2 on the bar/counter cells, pooled across actions (the budget register, budget_lab.py)

Two columns per game: BEST = the operator that scored best on a held-out quarter of the early presses;
STRICT = the best among operators that passed the gate (no-change when none did).

Usage:  python induce.py                       (all games in D:\planet\eye\<game>.npz -> induce_results.json)
        python induce.py --games ls20,vc33
        python induce.py --summary
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"
NC = 16
START: dict = {}        # id(frame) -> the frame this level started from (RESET or level change)
SHIFTS = [(dy, dx) for dy in range(-8, 9) for dx in range(-8, 9) if (dy, dx) != (0, 0)]


# ---------------------------------------------------------------- grid helpers (grid.ts, objects.ts)
def background(g) -> int:
    v, c = np.unique(g, return_counts=True); return int(v[np.argmax(c)])


def shifted(m, dy, dx, fill=0):
    """out[y+dy, x+dx] = m[y, x]; cells shifted in from outside get `fill`."""
    out = np.full_like(m, fill); H, W = m.shape
    ys, xs = slice(max(0, dy), min(H, H + dy)), slice(max(0, dx), min(W, W + dx))
    ys0, xs0 = slice(max(0, -dy), min(H, H - dy)), slice(max(0, -dx), min(W, W - dx))
    out[ys, xs] = m[ys0, xs0]; return out


def load_game(path, split=80):
    """early, late press lists of (f0, f1, action, x, y); RESET transitions dropped (as eye.py)."""
    z = np.load(path); F = z["F"].astype(np.int16); A, X, Y = z["A"], z["X"], z["Y"]
    L = z["L"] if "L" in z.files else np.zeros(len(A), int)
    keep = [i for i in range(len(A)) if A[i] != 0]
    if len(keep) < 20: return None
    pairs = []; start = F[0]
    for i in range(len(A)):
        if A[i] == 0: start = F[i + 1]; continue                  # RESET: the level starts here
        f0 = F[i]; pairs.append((f0, F[i + 1], int(A[i]), int(X[i]), int(Y[i]))); START[id(f0)] = start
        if L[i] != (L[i - 1] if i else 0): start = F[i + 1]        # a level change: new ground
    first = min(split, int(0.67 * len(keep)))
    return pairs[:first], pairs[first:]


def ambient_mask(pairs, frac=0.8):
    """cells that change on >= 80% of presses: the bar / counter / timer (prioragent v11, collect.py)"""
    cc = np.zeros(pairs[0][0].shape, int)
    for f0, f1, *_ in pairs: cc += (f0 != f1)
    return cc >= frac * len(pairs)


def tick_region(pairs, small=4):
    """THE BUDGET REGISTER (budget_lab.py): a bar drains a cell or two per press along its length, so no
    single cell changes often — but every press that changed almost nothing changed only the register.
    Collect those cells; a thin strip of them is a bar or counter, so take its full row (or column)."""
    H, W = pairs[0][0].shape; tick = np.zeros((H, W), bool)
    for f0, f1, *_ in pairs:
        D = f0 != f1
        if 0 < D.sum() <= small: tick |= D
    # a counter that ticks on EVERY press never leaves a small press behind (tr87's bottom row): find it by its
    # own signature instead — cells that changed exactly once, in a line, in spatial order of press time
    when = np.full((H, W), -1, int); times = np.zeros((H, W), int); line_hits = {0: np.zeros(H, int), 1: np.zeros(W, int)}
    for i, (f0, f1, *_) in enumerate(pairs):
        D = f0 != f1; times += D; when[D & (when < 0)] = i
        line_hits[0] += D.any(1); line_hits[1] += D.any(0)
    few = (times >= 1) & (times <= 3)                 # a register cell drains once and refills once per life; a mover's path cell churns
    for axis in (0, 1):
        for k in range(H if axis == 0 else W):
            if line_hits[axis][k] < 0.4 * len(pairs): continue          # a register ticks on most presses (tr87: every second one)
            line = few[k] if axis == 0 else few[:, k]
            idx = np.where(line)[0]
            if len(idx) < 6: continue
            t = (when[k] if axis == 0 else when[:, k])[idx]
            d = np.diff(t)
            # strictly one cell after another: a mover changes several cells at the same press and fails this
            if ((d > 0).all() or (d < 0).all()) and len(set(t.tolist())) >= 4:
                if axis == 0: tick[k, idx.min():idx.max() + 1] = True
                else: tick[idx.min():idx.max() + 1, k] = True
    if not tick.any(): return tick
    lab, n = ndimage.label(ndimage.binary_dilation(tick, iterations=3))
    reg = np.zeros_like(tick)
    for i in range(1, n + 1):
        ys, xs = np.where(tick & (lab == i))
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        if y1 - y0 <= 2: x0, x1 = 0, W - 1
        if x1 - x0 <= 2: y0, y1 = 0, H - 1
        reg[y0:y1 + 1, x0:x1 + 1] = True
    return reg if reg.sum() <= 0.2 * H * W else tick


# ---------------------------------------------------------------- displace / slide (induceMove, gravity)
_explain_cache: dict = {}


def d4(g, t):
    """the 8 grid symmetries: rotate by t%4 quarter turns, then mirror if t >= 4"""
    g = np.rot90(g, t % 4)
    return np.fliplr(g) if t >= 4 else g


def explain_shift(f0, f1, mask, bg):
    """The smallest (dy,dx) such that moving a set S of non-bg cells by it reproduces f1 on mask.
    Stage 1 (induceMove): a rigid shift of every cell whose colour reappears at c+d.
    Stage 2 (quaternion.ts): one object, transformed by a D4 symmetry, then shifted - a sprite that flips.
    Returns ((dy,dx), S, fill, t) or None."""
    k = (id(f0), id(f1))
    if k in _explain_cache: return _explain_cache[k]
    D = (f0 != f1) & mask
    res = None
    if D.any():
        best = None
        vals0, counts0 = np.unique(f0, return_counts=True); freq = dict(zip(vals0.tolist(), counts0.tolist()))
        def try_shifts(shift_list):
            nonlocal best
            for dy, dx in shift_list:
                f1s = shifted(f1, -dy, -dx, fill=-1)          # f1s[c] = f1[c + d]
                Ds = shifted(D, -dy, -dx, fill=False)          # Ds[c]  = D[c + d]
                S = (f0 != bg) & (f1s == f0) & (D | Ds)
                if not S.any(): continue
                # THE WHOLE BODY MOVES (Sep 6): a wide uniform bar shifted by less than its width changes only its two ends,
                # so the moved set found from the diff misses its middle and the true short shift fails while a long
                # two-patch "teleport" passes. Grow S to the connected bodies of its colours and try that first.
                grown = np.zeros_like(S)
                for v_ in np.unique(f0[S]):
                    lab_, n_ = ndimage.label(f0 == v_)
                    grown |= np.isin(lab_, np.unique(lab_[S & (f0 == v_)]))
                for S_try in ((grown, S) if grown.sum() > S.sum() else (S,)):
                    S = S_try
                    dest = shifted(S, dy, dx, fill=False)
                    vac = S & ~dest
                    vals = f1[vac]
                    fill = int(np.bincount(vals, minlength=NC).argmax()) if vals.size else bg
                    P = f0.copy(); P[vac] = fill; P[dest] = shifted(f0, dy, dx, fill=-1)[dest]
                    if np.array_equal(P[mask], f1[mask]): break
                if np.array_equal(P[mask], f1[mask]):
                    # figure over ground: between two shifts that both reproduce the frame, the mover is the
                    # RARER colour (a bracket over uniform floor can be read either way; the floor is not the mover)
                    core = S & (f0 != fill)
                    rarity = float(np.mean([freq[int(v)] for v in f0[core]])) if core.any() else 1e9
                    n = abs(dy) + abs(dx)
                    # rarity first: a periodic row of tiles lets the FLOOR "move" by a whole pitch and explain a
                    # wrap of the bracket; the rare colour is the figure, and only among equal figures the shorter shift
                    if best is None or (rarity, n) < (best[5], best[0]): best = (n, (dy, dx), S, fill, 0, rarity)
        try_shifts(SHIFTS)
        if best is None:                                   # a wrap-around jump: long, axis-aligned
            try_shifts([(0, dx) for dx in range(-40, 41) if abs(dx) > 8] + [(dy, 0) for dy in range(-40, 41) if abs(dy) > 8])
        if best is None:
            # A MOVE WITH A SIDE EFFECT: the mover shifted AND something changed elsewhere (ls20: entering the keyhole
            # turns the HUD glyph). Explain the mover on a window around the largest changed piece; the rest of the
            # change is the side effect, left to the relation layer. Without this the floor never learns the colours
            # of the things a touch acts on, and every such thing stays a wall.
            lab, n = ndimage.label(D)
            if n >= 2:
                sizes = ndimage.sum(D, lab, range(1, n + 1)); big = lab == (int(np.argmax(sizes)) + 1)
                ys, xs = np.where(big); H, W = f0.shape
                win = np.zeros_like(mask); win[max(0, ys.min() - 8):min(H, ys.max() + 9), max(0, xs.min() - 8):min(W, xs.max() + 9)] = True
                local = mask & win
                Dfull = D; D = (f0 != f1) & local
                saved_mask = mask; mask = local
                try_shifts(SHIFTS)
                mask = saved_mask; D = Dfull
        if best is None:
            H, W = f0.shape
            # candidate objects: first the non-bg pieces of the diff itself (a sprite that fully vacates its cells),
            # then whole non-bg components (a sprite that overlaps its old place; may be fused to a neighbour)
            cands = []
            for m in ((f0 != bg) & D, (f0 != bg) & mask):
                lab, n = ndimage.label(m)
                cands += [(lab == i) for i in range(1, n + 1)]
            for O in cands:
                if not (O & D).any() or O.sum() > 200: continue
                ys, xs = np.where(O); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
                crop = f0[y0:y1 + 1, x0:x1 + 1]; om = O[y0:y1 + 1, x0:x1 + 1]
                for t in range(1, 8):
                    T = d4(crop, t); Tm = d4(om, t); h, w = T.shape
                    for dy, dx in SHIFTS + [(0, 0)]:
                        ny0, nx0 = y0 + dy, x0 + dx
                        if ny0 < 0 or nx0 < 0 or ny0 + h > H or nx0 + w > W: continue
                        placed = np.zeros_like(O); placed[ny0:ny0 + h, nx0:nx0 + w] = Tm
                        vac = O & ~placed; vals = f1[vac]
                        fill = int(np.bincount(vals, minlength=NC).argmax()) if vals.size else bg
                        P = f0.copy(); P[vac] = fill; P[ny0:ny0 + h, nx0:nx0 + w][Tm] = T[Tm]
                        if np.array_equal(P[mask], f1[mask]):
                            nn = abs(dy) + abs(dx)
                            if best is None or nn < best[0]: best = (nn, (dy, dx), O, fill, t)
                if best is not None: break
        if best is not None: res = (best[1], best[2], best[3], best[4])
    _explain_cache[k] = res
    return res


class Displace:
    """one (dy,dx) per action (mode 'step'); or one direction, slide until a wall (mode 'slide')"""
    def __init__(self, mode="step"):
        self.mode = mode; self.name = "displace" if mode == "step" else "slide"
        self.d = None; self.t = 0; self.colors = set(); self.size = 0; self.floor = set(); self.fill = 0; self.ok = False
        self.blocked: set = set()                    # mover positions where this action was refused with floor ahead (an unseen wall)
        self.rides: dict = {}                        # RIDES (prioragent's wind, the chain's fan cells): position -> the jump this press takes there

    @staticmethod
    def _pos(S):
        ys, xs = np.where(S); return (int(ys.min()), int(xs.min()))

    def fit(self, pairs, mask, bg) -> float:
        vecs, fills, floor, cols, sizes, ts = [], [], set(), {}, [], []; floor_n: dict = {}
        for f0, f1, a, x, y in pairs:
            r = explain_shift(f0, f1, mask, bg)
            if r is None: continue                         # blocked, or a press this operator cannot explain
            d, S, fill, t = r; ts.append(t)
            # the mover proper: the cells it vacated or carried, minus anything the colour of the floor it
            # left behind (the shift also "explains" uniform corridor cells that reappear at c+d)
            core = S & (f0 != fill) & (f0 != bg)
            if not core.any(): core = S
            vecs.append(d); fills.append(fill); sizes.append(int(core.sum()))
            for v, c in zip(*np.unique(f0[core], return_counts=True)): cols[int(v)] = cols.get(int(v), 0) + int(c)
            dest = shifted(core, *d, fill=False) & ~core
            for v_ in set(int(v) for v in f0[dest]): floor_n[v_] = floor_n.get(v_, 0) + 1     # a floor colour is one the body entered on two presses (Sep 6: one right-move into a colour-4 patch made walls floor and the planner's states explode)
        self.ok = False
        if not vecs: return 0.0
        if len(set(ts)) != 1: return 0.0                   # one symmetry per action
        self.t = ts[0]
        self.wrap = None
        if self.mode == "step":
            from collections import Counter
            (d0, n0), = Counter(vecs).most_common(1)
            self.d = d0; self.rides = {}; self.wrap_at = set()
            if len(set(vecs)) != 1:
                # every press that did NOT take the usual step is either the WRAP (one long jump the other way along
                # the same axis, taken at the row's end: tr87) or a RIDE (a fan cell, a shaft, a transport: ls20 — a
                # "right" press that moves the key up 5, or 25). Rides are keyed by the place they happen at; that is
                # prioragent's wind-learning and the chain's fan map, as a learned parameter of the move itself.
                for (f0, f1, a, x, y) in pairs:
                    r = explain_shift(f0, f1, mask, bg)
                    if r is None or r[0] == d0: continue
                    w = r[0]; core = r[1] & (f0 != r[2]) & (f0 != bg); p = self._pos(core if core.any() else r[1])
                    same_axis = (d0[0] == 0) == (w[0] == 0)
                    opposite = np.sign(w[0] + w[1]) != np.sign(d0[0] + d0[1])
                    if same_axis and opposite and max(abs(w[0]), abs(w[1])) > max(abs(d0[0]), abs(d0[1])) and self.wrap in (None, w):
                        self.wrap = w; self.wrap_at.add(p[0] if w[0] else p[1])
                    else:
                        self.rides[p] = w
        else:
            units = set((int(np.sign(dy)), int(np.sign(dx))) for dy, dx in vecs)
            if len(units) != 1: return 0.0
            u = units.pop()
            if (u[0] and u[1]) or self.t: return 0.0        # slide is axis-aligned and rigid
            q = min(max(abs(dy), abs(dx)) for dy, dx in vecs)
            self.d = (u[0] * q, u[1] * q)
        self.fill = int(np.bincount(fills, minlength=NC).argmax())
        self.size = float(np.median(sizes))
        # the mover's palette: colours that make up most of the moved cells
        tot = sum(cols.values()); self.colors = set(v for v, c in cols.items() if c >= 0.05 * tot)
        floor = set(floor_n)                          # every colour the body entered; the fence vetoes the ones its walls deny (play.py)
        self.floor = floor
        self.ok = True
        # refusals the floor rule cannot explain: remember the place (prioragent's move_block, as a learned parameter);
        # the same coordinate refused at two different places along the motion axis is an arena bound, not a wall
        self.blocked = set(); self.bounds = set(); seen_axis: dict = {}
        for f0, f1, a, x, y in pairs:
            if ((f0 != f1) & mask).any(): continue
            S = self.locate(f0)
            if S is not None and self._step(f0, S) is not None:
                p = self._pos(S); self.blocked.add(p)
                c = p[0] if self.d[0] else p[1]
                seen_axis.setdefault(c, set()).add(p)
                if len(seen_axis[c]) >= 2: self.bounds.add(c)
        return float(np.mean([np.array_equal(self.predict(f0, x, y, a)[mask], f1[mask]) for f0, f1, a, x, y in pairs]))

    def locate(self, f0):
        m = np.isin(f0, sorted(self.colors))
        if not m.any(): return None
        if abs(int(m.sum()) - self.size) <= 0.25 * self.size: return m      # the mover may be several pieces (a bracket)
        lab, n = ndimage.label(m)
        best = None
        for i in range(1, n + 1):
            c = (lab == i); s = int(c.sum())
            if best is None or abs(s - self.size) < abs(best[1] - self.size): best = (c, s)
        if best is None or abs(best[1] - self.size) > 0.5 * self.size: return None
        return best[0]

    def _step(self, f0, S):
        p = self._pos(S)
        if p in self.blocked or (p[0] if self.d[0] else p[1]) in getattr(self, "bounds", ()): return None
        fen = getattr(self, "fence", None)                       # THE FENCE (play.py): a border this step must cross is broken
        if fen is not None and fen.blocks(f0, S, self.d): return None
        if self.t:
            ys, xs = np.where(S); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            T = d4(f0[y0:y1 + 1, x0:x1 + 1], self.t); Tm = d4(S[y0:y1 + 1, x0:x1 + 1], self.t); h, w = T.shape
            ny0, nx0 = y0 + self.d[0], x0 + self.d[1]; H, W = f0.shape
            if ny0 < 0 or nx0 < 0 or ny0 + h > H or nx0 + w > W: return None
            dest_all = np.zeros_like(S); dest_all[ny0:ny0 + h, nx0:nx0 + w] = Tm
            dest = dest_all & ~S
            if not dest.any() or not set(int(v) for v in f0[dest]) <= self.floor: return None
            P = f0.copy(); P[S & ~dest_all] = self.fill; P[ny0:ny0 + h, nx0:nx0 + w][Tm] = T[Tm]
            return P, dest_all
        dest_all = shifted(S, *self.d, fill=False)
        if dest_all.sum() != S.sum(): return None              # part of the mover would leave the frame: the edge is a wall
        dest = dest_all & ~S
        if not dest.any(): return None
        cols = set(int(v) for v in f0[dest])
        if not cols <= self.floor: return None
        P = f0.copy(); P[S & ~dest_all] = self.fill; P[dest_all] = shifted(f0, *self.d, fill=-1)[dest_all]
        return P, dest_all

    def applies(self, f0, a=0, x=-1, y=-1) -> bool:
        return self.ok and self.locate(f0) is not None

    def _jump(self, f0, S, w):
        """a ride: the mover lands at S + w whatever lies there (the fan decides, not the floor rule)"""
        dest_all = shifted(S, *w, fill=False)
        if dest_all.sum() != S.sum(): return None
        P = f0.copy(); P[S & ~dest_all] = self.fill; P[dest_all] = shifted(f0, *w, fill=-1)[dest_all]
        return P

    def predict(self, f0, x=-1, y=-1, a=0):
        if not self.ok: return f0.copy()
        S = self.locate(f0)
        if S is None: return f0.copy()
        rides = getattr(self, "rides", None)
        if rides:
            p = self._pos(S)
            if p in rides:
                P = self._jump(f0, S, rides[p])
                return P if P is not None else f0.copy()
        w = getattr(self, "wrap", None)
        if w is not None:                                   # at the row's end the step is a wrap jump instead
            p = self._pos(S); c = p[0] if w[0] else p[1]
            if c in getattr(self, "wrap_at", ()):
                d, self.d = self.d, w
                try: r = self._step(f0, S)
                finally: self.d = d
                return r[0] if r is not None else f0.copy()
        P = f0
        for _ in range(1 if self.mode == "step" else 16):
            r = self._step(P, S)
            if r is None: break
            P, S = r
        return P.copy() if P is f0 else P


class Restore:
    """the press returns the level to the frame it started from (outside the register); for clicks the
    trigger is the colour under the click, for buttons the action itself"""
    name = "restore"

    def __init__(self): self.trig = set(); self.ok = False

    @staticmethod
    def key(f0, a, x, y):
        return int(f0[y, x]) if a == 6 and 0 <= x < f0.shape[1] and 0 <= y < f0.shape[0] else -1

    def fit(self, pairs, mask, bg) -> float:
        self.trig = set(); self.ok = False
        for f0, f1, a, x, y in pairs:
            s = START.get(id(f0))
            if s is None: continue
            if ((f0 != f1) & mask).any() and np.array_equal(f1[mask], s[mask]): self.trig.add(self.key(f0, a, x, y))
        if not self.trig: return 0.0
        self.ok = True
        return float(np.mean([np.array_equal(self.predict(f0, x, y, a)[mask], f1[mask]) for f0, f1, a, x, y in pairs]))

    def applies(self, f0, a=0, x=-1, y=-1) -> bool:
        return self.ok and START.get(id(f0)) is not None and self.key(f0, a, x, y) in self.trig

    def predict(self, f0, x=-1, y=-1, a=0):
        s = START.get(id(f0))
        if self.ok and s is not None and self.key(f0, a, x, y) in self.trig: return s.copy()
        return f0.copy()


def explain_transform(f0, f1, mask, bg):
    """the smallest square region, containing the whole diff, whose contents are a D4 transform of themselves
    (a glyph rotated or flipped in place) with nothing else changed. Returns (t, (y0, x0, s)) or None."""
    D = (f0 != f1) & mask
    if not D.any(): return None
    ys, xs = np.where(D); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = f0.shape; base = max(y1 - y0, x1 - x0) + 1
    for s in range(base, min(base + 5, 24)):
        for oy in range(y1 - s + 1, y0 + 1):
            for ox in range(x1 - s + 1, x0 + 1):
                if oy < 0 or ox < 0 or oy + s > H or ox + s > W: continue
                c0, c1 = f0[oy:oy + s, ox:ox + s], f1[oy:oy + s, ox:ox + s]
                for t in range(1, 8):
                    if np.array_equal(d4(c0, t), c1):
                        P = f0.copy(); P[oy:oy + s, ox:ox + s] = c1
                        if np.array_equal(P[mask], f1[mask]): return t, (int(oy), int(ox), int(s))
    return None


class Transform:
    """PER-OBJECT TRANSFORM PIN (quaternion.ts about the object's own centre): the button rotates or flips one
    square region in place. Which region: the one at a fixed offset from an anchor colour's box (tr87: the
    glyph under the black selector), or a fixed place when no anchor is consistent."""
    name = "transform"

    def __init__(self): self.t = 0; self.anchor = None; self.offset = None; self.size = 0; self.fixed = None; self.ok = False

    def fit(self, pairs, mask, bg) -> float:
        self.ok = False; found = []
        for f0, f1, a, x, y in pairs:
            r = explain_transform(f0, f1, mask, bg)
            if r is not None: found.append((f0, r[0], r[1]))
        if not found: return 0.0
        ts = set(t for _, t, _ in found)
        if len(ts) != 1: return 0.0
        self.t = ts.pop(); self.size = int(np.median([reg[2] for _, _, reg in found]))
        # anchor: a non-floor colour whose bounding box sits at one fixed offset from the region, every press
        best = None
        vals, counts = np.unique(found[0][0], return_counts=True); floor = set(int(v) for v, c in zip(vals, counts) if c > 900)
        for c in set(int(v) for v in vals) - floor:
            offs = set()
            for f0, t, (oy, ox, s) in found:
                m = (f0 == c) & mask
                if not m.any(): offs.add(None); break
                ys, xs = np.where(m); offs.add((int(oy - ys.min()), int(ox - xs.min())))
            if len(offs) == 1 and None not in offs:
                if best is None or int(((found[0][0] == c) & mask).sum()) < best[1]: best = (c, int(((found[0][0] == c) & mask).sum()), offs.pop())
        if best is not None: self.anchor, self.offset = best[0], best[2]
        elif len(set((oy, ox) for _, _, (oy, ox, s) in found)) == 1: self.fixed = found[0][2][:2]
        else: return 0.0
        self.ok = True
        return float(np.mean([np.array_equal(self.predict(f0, x, y, a)[mask], f1[mask]) for f0, f1, a, x, y in pairs]))

    def region(self, f0):
        if self.anchor is not None:
            m = (f0 == self.anchor)
            if not m.any(): return None
            ys, xs = np.where(m); oy, ox = ys.min() + self.offset[0], xs.min() + self.offset[1]
        elif self.fixed is not None: oy, ox = self.fixed
        else: return None
        H, W = f0.shape; s = self.size
        if oy < 0 or ox < 0 or oy + s > H or ox + s > W: return None
        return int(oy), int(ox), s

    def applies(self, f0, a=0, x=-1, y=-1) -> bool:
        return self.ok and self.region(f0) is not None

    def predict(self, f0, x=-1, y=-1, a=0):
        r = self.region(f0) if self.ok else None
        if r is None: return f0.copy()
        oy, ox, s = r; P = f0.copy(); P[oy:oy + s, ox:ox + s] = d4(f0[oy:oy + s, ox:ox + s], self.t); return P


class Cycle:
    """PER-OBJECT STATE PIN: the button replaces the contents of one region with the next state in a finite
    sequence (tr87's glyphs, ls20's stamp and colour stations). The region is learned relative to an anchor
    colour's box (the selector): the smallest box, in anchor coordinates, that held every change. The table
    maps region contents -> next contents; a content never seen abstains."""
    name = "cycle"

    def __init__(self): self.anchor = None; self.rel = None; self.table: dict = {}; self.conflicts = 0; self.ok = False

    @staticmethod
    def _box(m):
        ys, xs = np.where(m); return int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())

    def fit(self, pairs, mask, bg) -> float:
        self.ok = False; self.table = {}; self.conflicts = 0
        changed = [(f0, f1, a, x, y) for f0, f1, a, x, y in pairs if ((f0 != f1) & mask).any()]
        if len(changed) < 2: return 0.0
        vals, counts = np.unique(changed[0][0], return_counts=True); floor = set(int(v) for v, c in zip(vals, counts) if c > 900)
        best = None
        for c in set(int(v) for v in vals) - floor:
            rel = None; ok = True
            for f0, f1, a, x, y in changed:
                m = (f0 == c) & mask
                if not m.any(): ok = False; break
                ay0, ay1, ax0, ax1 = self._box(m); dy0, dy1, dx0, dx1 = self._box((f0 != f1) & mask)
                r = (dy0 - ay0, dy1 - ay0, dx0 - ax0, dx1 - ax0)
                rel = r if rel is None else (min(rel[0], r[0]), max(rel[1], r[1]), min(rel[2], r[2]), max(rel[3], r[3]))
            if not ok: continue
            area = (rel[1] - rel[0] + 1) * (rel[3] - rel[2] + 1)
            if area <= 400 and (best is None or area < best[0]): best = (area, c, rel)
        if best is None: return 0.0
        self.anchor, self.rel = best[1], best[2]
        conflicts = set()
        for f0, f1, a, x, y in changed:
            r = self.region(f0)
            if r is None: continue
            y0, y1, x0, x1 = r; k = f0[y0:y1 + 1, x0:x1 + 1].tobytes(); v = f1[y0:y1 + 1, x0:x1 + 1].copy()
            if k in self.table and not np.array_equal(self.table[k], v): conflicts.add(k)
            else: self.table[k] = v
        for k in conflicts: self.table.pop(k, None)
        self.conflicts = len(conflicts)
        if not self.table: return 0.0
        self.ok = True
        return float(np.mean([np.array_equal(self.predict(f0, x, y, a)[mask], f1[mask]) for f0, f1, a, x, y in pairs]))

    def region(self, f0):
        m = (f0 == self.anchor)
        if not m.any(): return None
        ay0, ay1, ax0, ax1 = self._box(m); H, W = f0.shape
        y0, y1, x0, x1 = ay0 + self.rel[0], ay0 + self.rel[1], ax0 + self.rel[2], ax0 + self.rel[3]
        if y0 < 0 or x0 < 0 or y1 >= H or x1 >= W: return None
        return y0, y1, x0, x1

    def applies(self, f0, a=0, x=-1, y=-1) -> bool:
        r = self.region(f0) if self.ok else None
        return r is not None and f0[r[0]:r[1] + 1, r[2]:r[3] + 1].tobytes() in self.table

    def predict(self, f0, x=-1, y=-1, a=0):
        r = self.region(f0) if self.ok else None
        if r is None: return f0.copy()
        y0, y1, x0, x1 = r; v = self.table.get(f0[y0:y1 + 1, x0:x1 + 1].tobytes())
        if v is None: return f0.copy()
        P = f0.copy(); P[y0:y1 + 1, x0:x1 + 1] = v; return P


class Rhythm:
    """PATTERNS IN THE MOVEMENT (Jonathan, Sep 3): a spinning bar's pixels each return to their origin. A cell
    whose colour sequence over the run repeats with period p, for at least two full periods, is a rhythm cell;
    cells sharing a period are one turning thing. Its next value is its value p presses ago, whatever the
    button — so the rhythm is laid over the button's operator on the cells the operator leaves alone.
    Cells that ever held a mover's colour are excluded (a bar the planner walks back and forth is not spinning)."""
    name = "rhythm"

    def __init__(self): self.period = None; self.tail = None; self.ok = False; self.objects = []

    def fit(self, pairs, mask, mover_colors=()):
        self.ok = False; self.objects = []
        if len(pairs) < 6: return self
        F = np.stack([p[0] for p in pairs] + [pairs[-1][1]]); T, H, W = F.shape
        changes = (F[1:] != F[:-1]).sum(0)
        cand = (changes >= 2) & mask
        if mover_colors: cand &= ~np.isin(F, sorted(mover_colors)).any(0)
        period = np.zeros((H, W), int)
        for y, x in np.argwhere(cand):
            s = F[:, y, x]
            for p in range(2, T // 2 + 1):
                if np.array_equal(s[p:], s[:-p]): period[y, x] = p; break
        self.period = period
        if not (period > 0).any(): return self
        pmax = int(period.max()); self.tail = F[-pmax:]
        for p in sorted(set(period[period > 0].tolist())):
            lab, n = ndimage.label(period == p)
            for i in range(1, n + 1):
                m = lab == i
                if m.sum() >= 2: self.objects.append({"period": int(p), "cells": int(m.sum()), "at": [int(v) for v in np.argwhere(m).mean(0)]})
        self.ok = True
        return self

    def overlay(self, Q, f0, k=1):
        """lay the rhythm's next value (k presses ahead of the latest frame) over cells the operator left unchanged"""
        if not self.ok: return Q
        T = len(self.tail); out = Q
        for p in sorted(set(self.period[self.period > 0].tolist())):
            m = (self.period == p) & (Q == f0)
            if not m.any(): continue
            idx = T - 1 + k - p * ((k + p - 1) // p)          # the frame p·m presses back that this step repeats
            if idx < 0: continue
            if out is Q: out = Q.copy()
            out[m] = self.tail[idx][m]
        return out

    def summary(self) -> str:
        if not self.ok: return "none"
        return " ".join(f"p{o['period']}x{o['cells']}" for o in sorted(self.objects, key=lambda o: -o["cells"])[:6])


def cycle_lengths(op) -> list:
    """for a Cycle operator: how many presses bring each known state back to itself (the return to origin)"""
    if not isinstance(op, Cycle) or not op.table: return []
    out = []
    for k in list(op.table):
        seen = [k]; cur = k
        for _ in range(64):
            nxt = op.table.get(cur)
            if nxt is None: break
            nb = nxt.tobytes()
            if nb == k: out.append(len(seen)); break
            if nb in seen: break
            seen.append(nb); cur = nb
    return out


# ---------------------------------------------------------------- local rule (prune.ts induceLocalRule)
class LocalRule:
    def __init__(self, r=1, click=False, use_action=False):
        self.r = r; self.click = click; self.use_action = use_action
        self.name = (f"local{r}" if not click else "click") + ("+a" if use_action else "")
        self.table: dict = {}; self.conflicts = 0

    def keys(self, f0, x, y, a=0):
        r = self.r; H, W = f0.shape
        pad = np.full((H + 2 * r, W + 2 * r), -1, np.int16); pad[r:r + H, r:r + W] = f0
        chans = [pad[dy:dy + H, dx:dx + W] for dy in range(2 * r + 1) for dx in range(2 * r + 1)]
        if self.use_action: chans.append(np.full((H, W), a, np.int16))
        if self.click:
            if 0 <= x < W and 0 <= y < H:
                lab, n = ndimage.label(f0 == f0[y, x]); comp = (lab == lab[y, x]).astype(np.int16)
                yy, xx = np.mgrid[:H, :W]; dist = np.maximum(abs(yy - y), abs(xx - x))
                db = np.digitize(dist, [1, 2, 3, 6, 10]).astype(np.int16)
            else:
                comp = np.zeros((H, W), np.int16); db = np.full((H, W), 9, np.int16)
            chans += [comp, db]
        return np.stack(chans, -1).astype(np.int8).reshape(H * W, -1)

    def fit(self, pairs, mask, bg) -> float:
        self.table = {}; conflicts = set()
        self.nontrivial = sum(1 for f0, f1, a, x, y in pairs if ((f0 != f1) & mask).any())   # presses where something happened
        sel = np.where(mask.reshape(-1))[0]
        for f0, f1, a, x, y in pairs:
            K = self.keys(f0, x, y, a); out = f1.reshape(-1); t = self.table
            for i in sel:
                k = K[i].tobytes(); v = int(out[i]); p = t.get(k)
                if p is None: t[k] = v
                elif p != v: conflicts.add(k)
        for k in conflicts: self.table.pop(k, None)
        self.conflicts = len(conflicts)
        return float(np.mean([np.array_equal(self.predict(f0, x, y, a)[mask], f1[mask]) for f0, f1, a, x, y in pairs]))

    def applies(self, f0, a=0, x=-1, y=-1) -> bool:
        return bool(self.table)

    def predict(self, f0, x=-1, y=-1, a=0):
        if not self.table: return f0.copy()
        K = self.keys(f0, x, y, a); out = f0.reshape(-1).copy(); t = self.table
        for i in range(len(out)):
            v = t.get(K[i].tobytes())
            if v is not None: out[i] = v
        return out.reshape(f0.shape)


# ---------------------------------------------------------------- selection, gate, evaluation
def candidates(action):
    if action == 6: return [Restore(), Transform(), Cycle(), LocalRule(1, click=True), LocalRule(1), LocalRule(2)]
    return [Displace("step"), Displace("slide"), Transform(), Cycle(), Restore(), LocalRule(1), LocalRule(2)]


def gate(op, exact) -> bool:
    if isinstance(op, LocalRule): return op.conflicts == 0 and bool(op.table)
    return op.ok and exact >= 1.0


def mech_score(op, pairs, mask):
    """changed-cell accuracy on the non-ambient cells of held-out presses; exactness when nothing changed"""
    hit = tot = 0; ex = []
    for f0, f1, a, x, y in pairs:
        P = op.predict(f0, x, y, a); ch = (f1 != f0) & mask
        hit += int((P[ch] == f1[ch]).sum()); tot += int(ch.sum()); ex.append(np.array_equal(P[mask], f1[mask]))
    return (hit / tot) if tot else float(np.mean(ex))


def induce_action(pairs, mask, bg):
    """fit every candidate on the first 3/4, select on the last 1/4, refit the chosen on all; gate on all"""
    n = len(pairs); nfit = max(3, int(0.75 * n)) if n >= 4 else n
    fitp, selp = pairs[:nfit], pairs[nfit:]
    rows = []
    for op in candidates(pairs[0][2]):
        op.fit(fitp, mask, bg)
        s = mech_score(op, selp, mask) if selp else 0.0
        full = Displace(op.mode) if isinstance(op, Displace) else Restore() if isinstance(op, Restore) else Transform() if isinstance(op, Transform) else Cycle() if isinstance(op, Cycle) else LocalRule(op.r, op.click, op.use_action)
        exact = full.fit(pairs, mask, bg)
        rows.append({"op": op.name, "select": round(s, 3), "exact": round(exact, 3), "gate": gate(full, exact), "model": full})
    best = max(rows, key=lambda r: r["select"])
    gated = [r for r in rows if r["gate"]]
    strict = max(gated, key=lambda r: r["select"]) if gated else None
    return rows, best, strict


class Operators:
    """THE WORLD MODEL for play.py: per action, the gated operator (none when nothing passed the gate), plus
    the register rule. Fit from the game's prior touches and the run's own presses; refit as the run grows.
    predict() answers None when no gated operator applies, and the eye imagines instead."""

    BOND_START, BOND_KEEP = 0.6, 0.5                 # a freshly gated operator's trust; below KEEP it may not plan
    # one miss at full trust leaves 0.6 (still trusted); two in a row leave 0.36 (retired); each success closes 35% of the gap

    def __init__(self):
        self.ops: dict = {}; self.report: dict = {}; self.amb = None; self.mask = None; self.bg = 0; self.ambop = None; self.n = 0
        self.bond: dict = {}                          # action -> running trust (the bond, now in the gate)
        self.hyp: dict = {}; self.hyp_bond: dict = {}   # THE HYPOTHESES: per ungated action, the best candidate that did not pass, on trial
        self.promoted: set = set()                       # actions whose operator was earned by trial on the ring
        self.rhythm = Rhythm()

    def fit(self, pairs, min_presses=3, recent=None):
        """pairs = everything known (prior touches + this run); recent = the contiguous run, for the rhythm"""
        if len(pairs) < 8: return self
        self.n = len(pairs)
        amb_new = ambient_mask(pairs) | tick_region(pairs)
        # THE REGISTER SURVIVES A LEVEL CHANGE (Sep 5): eight presses into ls20 level 2 no cell had changed often enough to
        # be ambient, the bar's drain landed inside the mask, and the up operator was retired for not predicting it.
        # A new level keeps the last register band until its own presses reveal one.
        if not amb_new.any() and self.amb is not None and self.amb.any(): amb_new = self.amb
        self.amb = amb_new; self.mask = ~self.amb; self.bg = background(pairs[0][0])
        self.ambop = LocalRule(2, use_action=True)
        if self.amb.any(): self.ambop.fit(pairs, self.amb, self.bg)
        by: dict = {}
        for p in pairs: by.setdefault(p[2], []).append(p)
        old = dict(self.ops); self.ops = {}; self.report = {}
        for a, ps in sorted(by.items()):
            if len(ps) < min_presses: continue
            rows, best, strict = induce_action(ps, self.mask, self.bg)
            # THE BOND IN THE GATE: instead of "exact on every press" (which a pickup or a refill breaks for good),
            # run each candidate through the presses in order with the bond dynamics; the operator with the highest
            # trust at the end is the action's operator, and it may plan while that trust stays above KEEP.
            # A local rule that never explained a real change is not a law and does not compete.
            scored = []
            for r in rows:
                m = r["model"]
                if isinstance(m, LocalRule) and (len(ps) < 8 or r["select"] < 0.9 or m.nontrivial < 3): continue
                if isinstance(m, Restore) and not m.ok: continue
                if isinstance(m, Displace) and not m.ok: continue
                b = self.BOND_START; used = 0; hits = 0
                for f0, f1, aa, x, y in ps:
                    if not m.applies(f0, aa, x, y): b *= 0.97; continue
                    P = m.predict(f0, x, y, aa); used += 1
                    ok = np.array_equal(P[self.mask], f1[self.mask]); hits += ok
                    b = b + (1 - b) * 0.35 if ok else b * 0.6
                # THE LAW WITH EXCEPTIONS (Sep 5): three keyhole touches in a row retired ls20's 'left' (52 of 55 exact).
                # An operator exact on >= 90% of at least ten presses is a law; its exceptions belong to another layer
                # (a relation, a door) and do not cost it the gate
                if used >= 10 and hits >= 0.9 * used: b = max(b, hits / used)     # a law's bond is its accuracy: it outranks a state table that merely memorised
                if used: scored.append((b, r["select"], r))
            # A MOVEMENT LAW BEATS A MEMORISED TABLE (Sep 6): a Cycle that scores 1.0 by remembering every position the bar stood in
            # is not a law of the button; a Displace at 0.9 or better is preferred over it (sp80's left/right came back as Cycle
            # and the planner could no longer slide the bar under the token)
            disp_ = [t for t in scored if isinstance(t[2]["model"], Displace) and t[0] >= 0.9]
            pick = max(disp_, key=lambda t: (t[0], t[1])) if disp_ else (max(scored, key=lambda t: (t[0], t[1])) if scored else None)
            gated = pick is not None and pick[0] >= self.BOND_KEEP
            self.report[a] = {"presses": len(ps), "gated": pick[2]["op"] if gated else None, "best": best["op"], "best_select": best["select"],
                              "history_bond": round(pick[0], 3) if pick else None, "cycle": cycle_lengths(pick[2]["model"]) if gated else []}
            if gated:
                self.ops[a] = pick[2]["model"]
                # the bond survives a refit; a new operator (or a changed kind) starts at its history bond
                if a not in old or type(old[a]) is not type(pick[2]["model"]): self.bond[a] = pick[0]
                self.hyp.pop(a, None); self.hyp_bond.pop(a, None)
            elif a in old and a in self.promoted and self.bond.get(a, 0.0) >= self.BOND_KEEP:
                # a promoted hypothesis is an operator earned by trial, not by the history gate: it stays while its
                # live bond holds (the first version re-promoted sp80's ACTION5 six times, once per refit)
                self.ops[a] = old[a]; self.report[a]["gated"] = old[a].name + " (promoted)"
            else:
                self.bond.pop(a, None); self.promoted.discard(a)
                # the best candidate that did NOT pass becomes the action's hypothesis (Jonathan, Sep 4: the parts of
                # the whole that could match, tried where the model has nothing to say); its trial bond survives
                # a refit while the kind stays the same
                usable = [r for r in rows if getattr(r["model"], "ok", None) is not False and
                          not (isinstance(r["model"], LocalRule) and (not r["model"].table or r["model"].nontrivial < 3))]
                if usable:
                    h = max(usable, key=lambda r: (r["select"], r["exact"]))["model"]
                    if a not in self.hyp or type(self.hyp[a]) is not type(h): self.hyp_bond[a] = 0.3
                    self.hyp[a] = h
        movers = set()
        for op in self.ops.values():
            if isinstance(op, Displace): movers |= op.colors
        self.rhythm = Rhythm().fit(recent if recent is not None else pairs, self.mask, movers)
        return self

    def known(self, a) -> bool:
        return a in self.ops and self.bond.get(a, 0.0) >= self.BOND_KEEP

    def test_hypothesis(self, f0, a, x, y, f1):
        """a press of an unexplained button is a trial of its hypothesis: exact -> trust climbs, wrong -> it
        drops; at KEEP the hypothesis is promoted into the operators and the circle grows. Returns
        (verdict, promoted) with verdict True/False/None (did not apply)."""
        h = self.hyp.get(a)
        if h is None or a in self.ops: return None, False
        if not h.applies(f0, a, x, y): self.hyp_bond[a] = self.hyp_bond.get(a, 0.3) * 0.97; return None, False
        P = h.predict(f0, x, y, a); Q = f0.copy(); Q[self.mask] = P[self.mask]
        ok = np.array_equal(Q[self.mask], f1[self.mask])
        # pin rule 2: a fulfilled prediction of "nothing changes" is not evidence for a law — it is "nothing here",
        # a fact about this place, and it must never promote a hypothesis into an operator
        if ok and np.array_equal(Q[self.mask], f0[self.mask]): return None, False
        b = self.hyp_bond.get(a, 0.3); b = b + (1 - b) * 0.35 if ok else b * 0.6; self.hyp_bond[a] = b
        if b >= self.BOND_KEEP:
            self.ops[a] = h; self.bond[a] = b; self.hyp.pop(a, None); self.hyp_bond.pop(a, None); self.promoted.add(a)
            self.report.setdefault(a, {}).update({"gated": h.name, "promoted": True})
            return ok, True
        return ok, False

    def observe(self, f0, a, x, y, f1):
        """THE BOND IN THE GATE: after every real press, the operator that claimed it gains trust if it was
        exact, halves if it was wrong, drifts down a little if it abstained. Returns True/False/None."""
        op = self.ops.get(a)
        if op is None: return None
        b = self.bond.get(a, self.BOND_START)
        if not op.applies(f0, a, x, y): self.bond[a] = b * 0.97; return None
        P = self.predict(f0, a, x, y)
        ok = P is not None and np.array_equal(P[self.mask], f1[self.mask])
        self.bond[a] = b + (1 - b) * 0.35 if ok else b * 0.6
        return ok

    def predict(self, f0, a, x=-1, y=-1, k=1):
        op = self.ops.get(a)
        if op is None or not op.applies(f0, a, x, y): return None
        P = op.predict(f0, x, y, a); Q = f0.copy(); Q[self.mask] = P[self.mask]
        if self.amb is not None and self.amb.any() and self.ambop is not None and self.ambop.table:
            Q[self.amb] = self.ambop.predict(f0, x, y, a)[self.amb]
        return self.rhythm.overlay(Q, f0, k)

    def summary(self) -> str:
        s = " ".join(f"{a}:{r.get('gated') or ('?' + self.hyp[a].name + ' h%.2f' % self.hyp_bond.get(a, 0) if a in self.hyp else '-')}({r.get('presses', 0)})"
                     f"{(' b%.2f' % self.bond[a]) if a in self.bond else ''}"
                     f"{(' cyc' + str(sorted(set(r['cycle'])))) if r.get('cycle') else ''}" for a, r in sorted(self.report.items()))
        return s + (f" | rhythm {self.rhythm.summary()}" if self.rhythm.ok else "")


def evaluate(preds, pairs, amb):
    """eye.py's metrics on all changed cells, plus the same on non-ambient (mechanics) cells"""
    m = {"all": [0, 0, 0, 0, 0], "mech": [0, 0, 0, 0, 0]}          # hit, tot, tp, fp, fn
    for (f0, f1, a, x, y), P in zip(pairs, preds):
        for key, keep in (("all", np.ones_like(amb)), ("mech", ~amb)):
            ch = (f1 != f0) & keep; pch = (P != f0) & keep
            r = m[key]
            r[0] += int((P[ch] == f1[ch]).sum()); r[1] += int(ch.sum())
            r[2] += int((pch & ch).sum()); r[3] += int((pch & ~ch).sum()); r[4] += int((~pch & ch).sum())
    out = {}
    for key, (hit, tot, tp, fp, fn) in m.items():
        prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
        out[key] = {"changed_acc": round(hit / tot, 3) if tot else None, "changed_cells": tot,
                    "det_f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0}
    return out


def run_game(name, path, log=print):
    _explain_cache.clear()
    t0 = time.time()
    g = load_game(path)
    if g is None: return None
    early, late = g
    amb = ambient_mask(early) | tick_region(early); bg = background(early[0][0])
    mask = ~amb
    by_action: dict = {}
    for p in early: by_action.setdefault(p[2], []).append(p)
    ambop = LocalRule(2, use_action=True); amb_exact = ambop.fit(early, amb, bg) if amb.any() else None
    chosen = {}; report = {}
    for a, ps in sorted(by_action.items()):
        rows, best, strict = induce_action(ps, mask, bg)
        chosen[a] = (best["model"], strict["model"] if strict else None)
        report[a] = {"presses": len(ps), "best": best["op"], "best_select": best["select"], "best_exact": best["exact"],
                     "strict": strict["op"] if strict else None,
                     "ops": [{k: v for k, v in r.items() if k != "model"} for r in rows]}
    preds_best, preds_strict = [], []
    for f0, f1, a, x, y in late:
        b, s = chosen.get(a, (None, None))
        for op, dst in ((b, preds_best), (s, preds_strict)):
            P = op.predict(f0, x, y, a) if op is not None else f0.copy()
            Q = f0.copy(); Q[mask] = P[mask]
            if amb.any(): Q[amb] = ambop.predict(f0, x, y, a)[amb]
            dst.append(Q)
    res = {"presses": len(early) + len(late), "early": len(early), "late": len(late), "ambient_cells": int(amb.sum()),
           "ambient_exact": None if amb_exact is None else round(amb_exact, 3), "ambient_conflicts": ambop.conflicts,
           "actions": report, "best": evaluate(preds_best, late, amb), "strict": evaluate(preds_strict, late, amb),
           "seconds": round(time.time() - t0, 1)}
    ops = " ".join(f"{a}:{r['best']}{'*' if r['strict'] == r['best'] else ('/' + r['strict'] if r['strict'] else '/-')}" for a, r in report.items())
    log(f"  {name:6s} {len(late):3d} late | BEST acc {res['best']['all']['changed_acc']} f1 {res['best']['all']['det_f1']} "
        f"mech {res['best']['mech']['changed_acc']} | STRICT acc {res['strict']['all']['changed_acc']} f1 {res['strict']['all']['det_f1']} "
        f"| {ops} ({res['seconds']}s)")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default=None); ap.add_argument("--summary", action="store_true")
    ap.add_argument("--input-dir", default=OUT)
    ap.add_argument("--output", default=None)
    ap.add_argument("--run-id", default=None)
    a = ap.parse_args()
    resp = a.output or os.path.join(OUT, "induce_results.json")
    if a.summary:
        summary(json.load(open(resp))); return
    from evaluation_batch import run_batch
    results = run_batch(a.input_dir, resp, run_game,
                        games=a.games.split(",") if a.games else None, run_id=a.run_id)
    summary(results)


def summary(res):
    eye = {}
    try: eye = json.load(open(os.path.join(OUT, "eye_results.json")))["games"]
    except Exception: pass
    gs = res["games"]
    print(f"\ntransition induction vs the eye; {len(gs)} games (late presses, changed cells; * = passed the gate)")
    print(f"  {'game':6s} {'BEST acc':>8s} {'f1':>6s} {'mech':>6s} {'STRICT':>8s} {'f1':>6s} {'EYE CAT':>8s} {'f1':>6s}  operators per action")
    cols = {"b": [], "bf": [], "m": [], "s": [], "sf": [], "e": [], "ef": []}
    for n, g in sorted(gs.items()):
        b, s = g["best"]["all"], g["strict"]["all"]; mech = g["best"]["mech"]["changed_acc"]
        e = eye.get(n, {}).get("cat", {})
        ops = " ".join(f"{a}:{r['best']}{'*' if r['strict'] == r['best'] else ''}" for a, r in g["actions"].items())
        print(f"  {n:6s} {str(b['changed_acc']):>8s} {b['det_f1']:6.2f} {str(mech):>6s} {str(s['changed_acc']):>8s} {s['det_f1']:6.2f} "
              f"{str(e.get('changed_acc')):>8s} {e.get('det_f1', 0) or 0:6.2f}  {ops}")
        for k, v in (("b", b["changed_acc"]), ("bf", b["det_f1"]), ("m", mech), ("s", s["changed_acc"]), ("sf", s["det_f1"]),
                     ("e", e.get("changed_acc")), ("ef", e.get("det_f1"))):
            if v is not None: cols[k].append(v)
    mean = lambda k: (sum(cols[k]) / len(cols[k])) if cols[k] else 0.0
    print(f"  {'MEAN':6s} {mean('b'):8.3f} {mean('bf'):6.2f} {mean('m'):6.3f} {mean('s'):8.3f} {mean('sf'):6.2f} {mean('e'):8.3f} {mean('ef'):6.2f}")


if __name__ == "__main__":
    main()
