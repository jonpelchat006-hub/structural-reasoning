#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
species.py — the INNATE species, as streaming learners (frame rate, no replay).

Each species predicts the next frame from the current one and the action, learns
online from what actually happened, and knows nothing about any game. They are the
inner shell: laws, not knowledge. All operate on a small integer grid (H x W, values
0..K-1) — the coarse "box of pixels" the player sees, never the raw screen.

  CAMERA  — the world scrolls: estimate the global shift between frames (phase
            correlation on the luminance-ish grid) and compensate. In a scrolling
            game the background moves; without this every species sees a lie.
  MOVER   — per action, the displacement of the one object the hand drives, and
            which colours it is made of. Only the connected object that changed on
            the previous step moves (camera-compensated).
  COUNTER — per (action, colour), a register: a run of one colour that loses (or
            gains) a fixed number of pixels from one end per action.
  STATIC  — the flat surface: next = current (camera-compensated). Always on.

SurpriseMonitor composes them: prediction = static -> counter -> mover, then
measures per-region surprise (unexplained pixels) — the food, the gaze-stealer,
and the charge that becomes lightning.
"""
from __future__ import annotations
import math
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import ndimage


# ============================================================================
# CAMERA — global shift
# ============================================================================
class Camera:
    """Global (dy, dx) between consecutive frames by phase correlation, limited to
    |shift| <= max_shift. Returns (0,0) when the correlation peak is weak (no scroll)."""
    def __init__(self, max_shift: int = 12, min_peak: float = 0.15):
        self.max_shift, self.min_peak = max_shift, min_peak
        self.last = (0, 0); self.history: List[Tuple[int, int]] = []

    def estimate(self, prev: np.ndarray, cur: np.ndarray) -> Tuple[int, int]:
        a = prev.astype(float); b = cur.astype(float)
        a -= a.mean(); b -= b.mean()
        if a.std() < 1e-6 or b.std() < 1e-6:
            self.last = (0, 0); return self.last
        F = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
        F /= (np.abs(F) + 1e-9)
        corr = np.fft.ifft2(F).real
        H, W = corr.shape
        # restrict to allowed shifts
        best, bv = (0, 0), -1.0
        for dy in range(-self.max_shift, self.max_shift + 1):
            for dx in range(-self.max_shift, self.max_shift + 1):
                v = corr[dy % H, dx % W]
                if v > bv: bv, best = v, (dy, dx)
        peak = bv / (np.abs(corr).max() + 1e-9)
        # corr peak at (dy,dx) means cur is prev shifted by -(dy,dx) → world moved by (dy,dx) on screen
        self.last = (-best[0], -best[1]) if peak >= self.min_peak else (0, 0)
        self.history.append(self.last)
        return self.last

    @staticmethod
    def shift(frame: np.ndarray, dy: int, dx: int, fill: int = -1) -> np.ndarray:
        """Move the content of `frame` by (dy, dx); vacated cells = fill (-1 = unknown)."""
        out = np.full_like(frame, fill)
        H, W = frame.shape
        ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
        xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
        out[yd, xd] = frame[ys, xs]
        return out


# ============================================================================
# MOVER — the hand's object
# ============================================================================
class Mover:
    def __init__(self, max_shift: int = 8, max_obj: int = 400):
        self.S = [(dy, dx) for dy in range(-max_shift, max_shift + 1) for dx in range(-max_shift, max_shift + 1)]
        self.votes: Dict[str, np.ndarray] = defaultdict(lambda: np.zeros(len(self.S)))
        self.mobile: Dict[str, Counter] = defaultdict(Counter)
        self.max_obj = max_obj
        self.obj_mask: Optional[np.ndarray] = None       # where the driven object was last seen
        self.obj_pos: Optional[Tuple[float, float]] = None

    def displacement(self, action: str) -> Tuple[int, int]:
        """The hand's effect is what DEPENDS on the action: fog, wind and parallax drift the same way
        whatever key is pressed, so their votes appear under every action and cancel; the body's
        votes appear only under the action that moved it."""
        v = self.votes.get(action)
        if v is None or v.sum() <= 0: return (0, 0)
        others = [w / w.sum() for a, w in self.votes.items() if a != action and w.sum() > 0]
        contrast = v / v.sum() - (np.mean(others, axis=0) if others else 0.0)
        k = int(np.argmax(contrast))
        return self.S[k] if contrast[k] > 0.05 else (0, 0)

    def mobile_colors(self, action: Optional[str] = None) -> set:
        """Colours that move under this action — those seen moving at least half as often as
        the most-moved colour (background restorations vote once or twice; the object every step)."""
        def pick(cnt):
            if not cnt: return set()
            top = max(cnt.values())
            return {c for c, n in cnt.items() if n >= max(2, 0.5 * top)} if top >= 2 else set(cnt)
        if action is not None:
            return pick(self.mobile[action])
        out = set()
        for cnt in self.mobile.values(): out |= pick(cnt)
        return out

    def predict(self, prev_comp: np.ndarray, cur: np.ndarray, action: str) -> np.ndarray:
        """prev_comp = previous frame already camera-compensated into cur's coordinates."""
        dy, dx = self.displacement(action)
        mob = self.mobile_colors(action)
        pred = cur.copy()
        self.obj_pos = None                               # a detection is per frame; the Body persists
        if not mob or (dy == 0 and dx == 0): return pred
        changed = (cur != prev_comp) & (prev_comp >= 0) & np.isin(cur, list(mob))
        if not changed.any(): return pred
        lab, n = ndimage.label(np.isin(cur, list(mob)))
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)) if n else []
        ids = [k for k in set(np.unique(lab[changed])) - {0} if 2 <= sizes[k - 1] <= self.max_obj]
        if not ids: return pred
        obj = np.isin(lab, ids)
        ys, xs = np.where(obj)
        self.obj_mask = obj; self.obj_pos = (float(ys.mean()), float(xs.mean()))
        bg = prev_comp[ys, xs]
        pred[ys, xs] = np.where((bg >= 0) & ~np.isin(bg, list(mob)), bg, _halo_color(cur, ys, xs, avoid=mob))
        ny, nx = ys + dy, xs + dx
        ok = (ny >= 0) & (ny < cur.shape[0]) & (nx >= 0) & (nx < cur.shape[1])
        pred[ny[ok], nx[ok]] = cur[ys[ok], xs[ok]]
        return pred

    def observe(self, prev_comp: np.ndarray, cur: np.ndarray, action: str) -> None:
        """A colour is MOBILE for this action if the pixels of it that vanished are a shifted
        copy of the pixels of it that appeared (match >= 0.6). Only such colours vote, and
        their vote is the match count at the shift that aligns them."""
        valid = prev_comp >= 0
        changed = (cur != prev_comp) & valid
        if not changed.any() or changed.sum() > 0.4 * cur.size: return
        colors = set(np.unique(cur[changed]).tolist()) & set(np.unique(prev_comp[changed]).tolist())
        v = self.votes[action]
        for c in colors:
            c = int(c)                       # a common colour may still carry a small driven object (a black boy on black)
            gone = changed & (prev_comp == c) & (cur != c)
            came = changed & (cur == c) & (prev_comp != c)
            ng, nc = int(gone.sum()), int(came.sum())
            if ng < 2 or nc < 2: continue
            # the object = the component(s) of colour c that lost pixels, and the one(s) that gained;
            # displacement = centroid shift (right even when the object overlaps its old place)
            labp, npc = ndimage.label(prev_comp == c); labc, ncc = ndimage.label(cur == c)
            sizes_p = ndimage.sum(np.ones_like(labp), labp, range(1, npc + 1)) if npc else []
            sizes_c = ndimage.sum(np.ones_like(labc), labc, range(1, ncc + 1)) if ncc else []
            # per COMPONENT (a tiny boy must not be drowned by the fog's boundary of the same colour)
            cur_comps = []
            for k in set(np.unique(labc[came])) - {0}:
                if 2 <= sizes_c[k - 1] <= self.max_obj:
                    yy, xx = np.where(labc == k); cur_comps.append((k, sizes_c[k - 1], yy.mean(), xx.mean()))
            for k in set(np.unique(labp[gone])) - {0}:
                sp = sizes_p[k - 1]
                if sp < 2 or sp > self.max_obj: continue
                py, px = np.where(labp == k); pcy, pcx = py.mean(), px.mean()
                best = None
                for kc, sc, ccy, ccx in cur_comps:
                    if max(sp, sc) > 1.6 * min(sp, sc): continue
                    dy, dx = int(round(ccy - pcy)), int(round(ccx - pcx))
                    if (dy, dx) == (0, 0) or (dy, dx) not in self.S: continue
                    d = abs(dy) + abs(dx)
                    if best is None or d < best[0]: best = (d, dy, dx, sc)
                if best is None: continue
                _, dy, dx, sc = best
                self.mobile[action][c] += 1
                v[self.S.index((dy, dx))] += min(sp, sc)


# ============================================================================
# COUNTER — registers
# ============================================================================
class CounterSpecies:
    def __init__(self, max_delta: int = 8):
        self.hist: Dict[Tuple[str, int], List[Tuple[int, str]]] = defaultdict(list)
        self.reg_next: Dict[int, List[Tuple[int, int]]] = {}
        self.max_delta = max_delta

    def laws(self) -> Dict[Tuple[str, int], Tuple[int, str]]:
        out = {}
        for (a, c), h in self.hist.items():
            if len(h) >= 2:
                out[(a, c)] = (int(np.median([d for d, _ in h])), Counter(e for _, e in h).most_common(1)[0][0])
        return out

    def predict(self, cur: np.ndarray, action: str) -> np.ndarray:
        pred = cur.copy()
        for (a, c), (delta, end) in self.laws().items():
            if a != action or delta >= 0: continue
            lab, n = ndimage.label(cur == c)
            if n == 0: continue
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            big = 1 + int(np.argmax(sizes))
            if c in self.reg_next:
                ids = [int(lab[y, x]) for y, x in self.reg_next[c] if 0 <= y < lab.shape[0] and 0 <= x < lab.shape[1] and lab[y, x] > 0]
                if ids: big = Counter(ids).most_common(1)[0][0]
            ys, xs = np.where(lab == big)
            order = np.argsort(xs, kind="stable") if end in ("L", "R") else np.argsort(ys, kind="stable")
            if end in ("R", "B"): order = order[::-1]
            take = order[:min(-delta, len(order))]
            oy, ox = {"L": (0, -1), "R": (0, 1), "T": (-1, 0), "B": (1, 0)}[end]
            H, W = cur.shape
            ny = np.clip(ys.min() + oy if end == "T" else (ys.max() + oy if end == "B" else ys[take]), 0, H - 1)
            nx = np.clip(xs.min() + ox if end == "L" else (xs.max() + ox if end == "R" else xs[take]), 0, W - 1)
            fill = cur[ny, nx]
            fill = np.where(fill == c, _halo_color(cur, ys[take], xs[take], exclude=int(c)), fill)
            pred[ys[take], xs[take]] = fill
        return pred

    def observe(self, prev_comp: np.ndarray, cur: np.ndarray, action: str) -> None:
        valid = prev_comp >= 0
        for c in np.unique(prev_comp[valid]):
            c = int(c)
            d = int((cur == c).sum() - ((prev_comp == c) & valid).sum())
            if d == 0 or abs(d) > self.max_delta: continue
            lost = (prev_comp == c) & (cur != c) & valid
            ys, xs = np.where(lost)
            if len(ys) == 0: continue
            lab0, _ = ndimage.label(prev_comp == c)
            comp = np.isin(lab0, np.unique(lab0[lost])) & (lab0 > 0)
            ay, ax = np.where(comp)
            cx, cy = xs.mean(), ys.mean(); mx, my = ax.mean(), ay.mean()
            end = ("R" if cx > mx else "L") if abs(cx - mx) >= abs(cy - my) else ("B" if cy > my else "T")
            self.hist[(action, c)].append((d, end))
            iy, ix = {"L": (0, 1), "R": (0, -1), "T": (1, 0), "B": (-1, 0)}[end]
            inside = [(int(y + iy * k), int(x + ix * k)) for y, x in zip(ys, xs) for k in (1, 2, 3)]
            self.reg_next[c] = [(y, x) for y, x in inside
                                if 0 <= y < cur.shape[0] and 0 <= x < cur.shape[1] and cur[y, x] == c]


def _halo_color(frame, ys, xs, exclude=None, avoid=()):
    H, W = frame.shape
    y0, y1 = max(0, ys.min() - 3), min(H, ys.max() + 4); x0, x1 = max(0, xs.min() - 3), min(W, xs.max() + 4)
    cnt = Counter(frame[y0:y1, x0:x1].ravel().tolist())
    if exclude is not None: cnt.pop(exclude, None)
    for c in (avoid or ()): cnt.pop(int(c), None)
    return cnt.most_common(1)[0][0] if cnt else 0



# ============================================================================
# BODY — object permanence: the driven thing persists when it cannot be seen
# ============================================================================
class Body:
    """Jonathan: 'you need a way to have the body persist even when you can't see it … just keep
    going right and walk past.' The body is a STATE, not a detection:
      * a detection is only ACCEPTED as the body if it moved the way the action said it would
        (the fog does not obey the hand; the boy does) — confirmed after `confirm_n` agreements;
      * when nothing is detected, the body is dead-reckoned: pos += displacement(action), then
        corrected by the camera shift; it stays alive `patience` frames → atom body.hidden;
      * a detection near the dead-reckoned position re-acquires it → body.reacquired;
      * where it vanished while the reckoning still had it on screen is an OCCLUDER — the seed of
        the foreground SHEET (something between the eye and the body)."""
    def __init__(self, confirm_n: int = 2, patience: int = 40, reacquire_radius: float = 12.0):
        self.pos: Optional[Tuple[float, float]] = None
        self.vel: Tuple[int, int] = (0, 0)
        self.confirmed = False; self.agree = 0; self.hidden_for = 0
        self.confirm_n, self.patience, self.radius = confirm_n, patience, reacquire_radius
        self.occluders: List[Tuple[float, float]] = []      # screen positions where it vanished (this life)

    def visible(self) -> bool:
        return self.pos is not None and self.hidden_for == 0

    def update(self, detection: Optional[Tuple[float, float]], expected: Tuple[int, int], cam: Tuple[int, int],
               H: int, W: int) -> Set[str]:
        ev: Set[str] = set()
        dy, dx = expected; cy, cx = cam
        if self.pos is not None:
            # dead reckoning in SCREEN coordinates: the body moves by the action, the screen drags by the camera
            self.pos = (self.pos[0] + dy + cy, self.pos[1] + dx + cx)
        if detection is not None:
            if self.pos is None:
                self.pos = detection; self.agree = 0
            else:
                d = abs(detection[0] - self.pos[0]) + abs(detection[1] - self.pos[1])
                if d <= self.radius:
                    if self.hidden_for > 0: ev.add("body.reacquired")
                    # a twitch is not a step: only a real displacement under the action counts as agreement
                    self.agree += 1 if abs(dy) + abs(dx) >= 2 else 0
                    self.pos = detection; self.hidden_for = 0
                    if not self.confirmed and self.agree >= self.confirm_n:
                        self.confirmed = True; ev.add("body.confirmed")
                elif not self.confirmed or self.hidden_for > self.patience // 2:
                    self.pos = detection; self.agree = 0; self.confirmed = False; self.hidden_for = 0
                else:
                    ev.add("body.impostor")        # something moved, but not where the body should be
                    self.hidden_for += 1
        else:
            if self.pos is not None:
                if self.hidden_for == 0: self.occluders.append(self.pos); ev.add("body.occluded")
                self.hidden_for += 1
                ev.add("body.hidden")
                if self.hidden_for > self.patience or not (0 <= self.pos[0] < H and 0 <= self.pos[1] < W):
                    self.pos = None; self.confirmed = False; self.hidden_for = 0; ev.add("body.lost")
        return ev

# ============================================================================
# SURPRISE MONITOR — the fast loop
# ============================================================================
class SurpriseMonitor:
    """Holds the species, predicts each frame, scores per-region surprise, learns.
    active = which species are switched on per region (the coach can bend this)."""
    def __init__(self, H: int, W: int, tile: int = 8, use_camera: bool = True):
        self.H, self.W, self.tile = H, W, tile
        self.NR, self.NC = H // tile, W // tile
        self.camera = Camera() if use_camera else None
        self.mover, self.counter, self.body = Mover(), CounterSpecies(), Body()
        self.prev: Optional[np.ndarray] = None
        self.pred: Optional[np.ndarray] = None
        self.last_action: Optional[str] = None
        self.surprise = np.zeros((self.NR, self.NC))          # decaying per-region charge
        self.e0_total = 0; self.err_total = 0; self.steps = 0
        self.cam_shift = (0, 0)
        self._follows = False; self._follow_votes = 0

    def regions(self, err: np.ndarray) -> np.ndarray:
        return err[:self.NR * self.tile, :self.NC * self.tile].reshape(self.NR, self.tile, self.NC, self.tile).sum(axis=(1, 3))

    def step(self, frame: np.ndarray, action: str) -> Dict:
        """Feed the frame that RESULTED from `action`. Returns surprise info for this step."""
        info = {"e0": 0, "err": 0, "region_err": np.zeros((self.NR, self.NC), int), "cam": (0, 0)}
        if self.prev is None:
            self.prev = frame; self.last_action = action; return info
        prev = self.prev
        if self.camera is not None:
            dy, dx = self.camera.estimate(prev % 8, frame % 8)          # scroll from the luminance lens only
            prev_comp = Camera.shift(prev, dy, dx) if (dy or dx) else prev
            self.cam_shift = (dy, dx)
        else:
            prev_comp = prev
        info["cam"] = self.cam_shift
        # ---- predict (from prev, before seeing frame): static -> counter -> mover
        # (prediction uses the compensated previous frame as the "current" of the species)
        base = prev_comp
        pc = self.counter.predict(np.where(base >= 0, base, 0), action)
        pp = getattr(self, "_prev_prev_comp", None)
        if pp is None: pp = base
        elif self.cam_shift != (0, 0): pp = Camera.shift(pp, *self.cam_shift)
        pm = self.mover.predict(pp, np.where(base >= 0, base, 0), action)
        pred = np.where(base >= 0, base, frame)          # unknown (scrolled-in) cells cost nothing
        pred = np.where(pc != np.where(base >= 0, base, 0), pc, pred)
        pred = np.where(pm != np.where(base >= 0, base, 0), pm, pred)
        valid = base >= 0
        e0 = ((frame != base) & valid).astype(int)
        err = ((frame != pred) & valid).astype(int)
        info["e0"], info["err"] = int(e0.sum()), int(err.sum())
        info["region_err"] = self.regions(err); info["region_e0"] = self.regions(e0)
        self.e0_total += info["e0"]; self.err_total += info["err"]; self.steps += 1
        # charge: decays, accumulates unexplained pixels
        self.surprise = 0.85 * self.surprise + info["region_err"]
        # ---- the body persists; the map should move WITH the body (the screen drags back as he goes)
        det = self.mover.obj_pos
        expected = self.mover.displacement(action)
        info["body"] = self.body.update(det, expected, self.cam_shift, self.H, self.W)
        if self.body.confirmed and expected != (0, 0):
            # expected scroll: the camera follows the body (drags the world back by the body's motion)
            exp_cam = (-expected[0], -expected[1]) if self._follows else (0, 0)
            drift = abs(self.cam_shift[0] - exp_cam[0]) + abs(self.cam_shift[1] - exp_cam[1])
            if self.cam_shift != (0, 0): self._follow_votes += 1 if abs(self.cam_shift[1] + expected[1]) <= 1 else -1
            self._follows = self._follow_votes > 2
            if self._follows and drift > 2: info["body"].add("camera.drift")
        # ---- learn
        self.mover.observe(np.where(valid, base, -1), frame, action)
        self.counter.observe(np.where(valid, base, -1), frame, action)
        self._prev_prev_comp = np.where(valid, base, -1)
        self.prev = frame; self.last_action = action; self.pred = pred
        return info

    def explained_fraction(self) -> float:
        return 1.0 - self.err_total / max(1, self.e0_total)

    def hottest_region(self, pressure: Optional[np.ndarray] = None) -> Tuple[int, int]:
        s = self.surprise * (1.0 + (pressure if pressure is not None else 0.0))
        i = int(np.argmax(s)); return divmod(i, self.NC)
