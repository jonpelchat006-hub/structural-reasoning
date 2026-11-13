#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rotation.py — the ROTATION EYE: the sheet turns, and the world is built from what passes across it.

A 3D game seen through the screen has six degrees of freedom, and they show up differently on
the sheet. Rotation (yaw, pitch — the mouse) moves EVERYTHING the same way, near and far alike,
so it looks exactly like Limbo's camera scroll; translation (the keys) moves near things more
than far ones (parallax). This eye is the rotation estimator: it is told by the mouse when to
look and how far to expect the sheet to slide, learns the gain (pixels per mouse count) from
what it actually sees, and stitches the frames into a PANORAMA — a ring of sheets around the
place where the body stands. When the ring closes (the frame matches where it started after a
long turn) the eye knows how many pixels one full turn is: the ring's circumference.

The layer sorter's first layer falls out for free: cells that never move while the sheet slides
are the HUD (crosshair, health, minimap). They are found, not hard-coded (the ARC row-55 lesson),
and they are excluded from both the correlation and the panorama.

Species interface: step(prev, cur, mouse=(dx, dy)) -> info {shift, predicted, peak, events};
save/load; summary().
"""
from __future__ import annotations
import json, os
from typing import Dict, Optional, Set, Tuple
import numpy as np

from species import Camera
from wall import Atlas, UNKNOWN


class RotationEye:
    def __init__(self, H: int, W: int, max_resid: int = 12):
        self.H, self.W = H, W
        self.max_resid = max_resid
        self.gain = {"x": 0.0, "y": 0.0}; self.evidence = {"x": 0, "y": 0}
        self.still = np.zeros((H, W), np.int32); self.moved = np.zeros((H, W), np.int32)
        self.pan = Atlas(H, W, pad=W)                     # the ring: world x = yaw in pixels, world y = pitch
        self.yaw = 0.0; self.pitch = 0.0; self.turn_width: Optional[float] = None
        self.n = 0; self.predicted_steps = 0; self.closures = 0

    # ---- the HUD layer: still while the sheet moves
    def hud_mask(self) -> np.ndarray:
        return (self.still > 5) & (self.still > 3 * self.moved)

    def _observe_layers(self, prev: np.ndarray, cur: np.ndarray, shift: Tuple[int, int]) -> None:
        if abs(shift[0]) + abs(shift[1]) < 3: return
        same = prev == cur
        self.still[same] += 1; self.moved[~same] += 1

    # ---- one look
    def step(self, prev: Optional[np.ndarray], cur: np.ndarray, mouse: Tuple[int, int]) -> Dict:
        ev: Set[str] = set(); self.n += 1
        info = {"shift": (0, 0), "predicted": (0, 0), "peak": 0.0, "events": ev, "used": "none"}
        if prev is None: self.pan.stitch(cur, *self.pan.pos); return info
        mdx, mdy = mouse
        hud = self.hud_mask()
        a = np.where(hud, 0, prev); b = np.where(hud, 0, cur)
        # predicted sheet motion from the mouse (world moves opposite to the turn): screen shift = -gain*mouse
        pdx = int(round(-self.gain["x"] * mdx)) if self.evidence["x"] >= 3 else 0
        pdy = int(round(-self.gain["y"] * mdy)) if self.evidence["y"] >= 3 else 0
        info["predicted"] = (pdy, pdx)
        # correlate the residual after applying the prediction (lets big turns exceed the ±12 search)
        pre = Camera.shift(a, pdy, pdx) if (pdy or pdx) else a
        # bootstrap: before the gain is known, a fast turn can exceed ±12 px — search wide (±40) until then
        wide = 40 if (self.evidence["x"] < 3 and abs(mdx) >= 6) or (self.evidence["y"] < 3 and abs(mdy) >= 6) else self.max_resid
        resid = self._estimate(pre, b, wide)
        peak = self._peak_quality(pre, b, resid)
        if peak >= 0.12:
            shift = (pdy + resid[0], pdx + resid[1]); info["used"] = "measured"
        elif pdy or pdx:
            shift = (pdy, pdx); info["used"] = "predicted"; self.predicted_steps += 1; ev.add("rotation.predicted")
        else:
            shift = (0, 0)
        info["shift"] = shift; info["peak"] = peak
        # learn the gain from measured turns
        if info["used"] == "measured":
            for axis, m, s in (("x", mdx, shift[1]), ("y", mdy, shift[0])):
                if abs(m) >= 6 and abs(s) >= 2 and np.sign(-s) == np.sign(m):
                    g = -s / m
                    if self.evidence[axis] == 0: self.gain[axis] = g
                    else: self.gain[axis] = 0.85 * self.gain[axis] + 0.15 * g
                    self.evidence[axis] += 1
                    if self.evidence[axis] == 3: ev.add(f"rotation.gain_learned:{axis}")
        self._observe_layers(prev, cur, shift)
        # the ring
        if shift != (0, 0):
            ev.add("rotation.yaw:" + ("R" if shift[1] < 0 else "L") if shift[1] else "rotation.pitch")
        self.yaw -= shift[1]; self.pitch -= shift[0]
        wy, wx = self.pan.pos
        wy, wx = wy - shift[0], wx - shift[1]
        if self.turn_width: wx = int(wx % self.turn_width)
        self.pan.pos = (int(wy), int(wx))
        if self.n % 5 == 0 and self.pan.realign(b) is not None: ev.add("rotation.realigned")
        self.pan.stitch(cur, *self.pan.pos, body_mask=hud)
        # closure: after more than two screens of turning, does the frame fit back where the ring began?
        if self.turn_width is None and abs(self.yaw) > 2.5 * self.W and self.n % 3 == 0:
            r = self.pan.recognise(b, min_peak=0.45)
            if r is not None and abs(r[1] - self.pan.pos[1]) > 1.5 * self.W:
                self.turn_width = float(abs(self.pan.pos[1] - r[1]))
                self.pan.pos = (self.pan.pos[0], int(r[1])); self.closures += 1
                ev.add("rotation.turn_closed")
        return info

    @staticmethod
    def _estimate(prev: np.ndarray, cur: np.ndarray, max_shift: int) -> Tuple[int, int]:
        """Phase correlation, vectorised over the allowed window (world shift on screen)."""
        a = prev.astype(float); b = cur.astype(float); a -= a.mean(); b -= b.mean()
        if a.std() < 1e-6 or b.std() < 1e-6: return (0, 0)
        F = np.fft.fft2(a) * np.conj(np.fft.fft2(b)); F /= (np.abs(F) + 1e-9)
        corr = np.fft.ifft2(F).real
        H, W = corr.shape; r = np.arange(-max_shift, max_shift + 1)
        win = corr[np.ix_(r % H, r % W)]
        k = np.unravel_index(int(np.argmax(win)), win.shape)
        return (-int(r[k[0]]), -int(r[k[1]]))

    def _peak_quality(self, a: np.ndarray, b: np.ndarray, shift: Tuple[int, int]) -> float:
        """How well does `a` moved by `shift` explain `b`? Fraction of cells that agree over the overlap."""
        moved = Camera.shift(a, shift[0], shift[1])
        ok = moved != -1
        if ok.sum() < 0.3 * a.size: return 0.0
        agree = float((moved[ok] == b[ok]).mean())
        base = float((a[ok] == b[ok]).mean())              # agreement with NO shift
        return max(0.0, agree - base) + (agree if agree > 0.6 else 0.0) * 0.2

    # ---- persistence / report
    def save(self, path_npz: str, path_json: str) -> None:
        self.pan.save(path_npz)
        np.savez_compressed(path_npz.replace(".npz", "_layers.npz"), still=self.still, moved=self.moved)
        with open(path_json, "w", encoding="utf-8") as f:
            json.dump({"gain": self.gain, "evidence": self.evidence, "turn_width": self.turn_width,
                       "closures": self.closures, "hud_cells": int(self.hud_mask().sum())}, f, indent=1)

    @classmethod
    def load(cls, H: int, W: int, path_npz: str, path_json: str) -> "RotationEye":
        r = cls(H, W)
        try:
            r.pan = Atlas.load(path_npz, H, W)
            d = np.load(path_npz.replace(".npz", "_layers.npz")); r.still, r.moved = d["still"], d["moved"]
            with open(path_json, "r", encoding="utf-8") as f: j = json.load(f)
            r.gain, r.evidence, r.turn_width, r.closures = j["gain"], j["evidence"], j.get("turn_width"), j.get("closures", 0)
        except Exception: pass
        return r

    def summary(self) -> str:
        c = self.pan.canvas; known = int((c != UNKNOWN).sum())
        return (f"rotation: gain x={self.gain['x']:.3f} ({self.evidence['x']}) y={self.gain['y']:.3f} ({self.evidence['y']}) px/count, "
                f"yaw {self.yaw:.0f}px, turn={None if self.turn_width is None else int(self.turn_width)}px, "
                f"ring {known} cells, HUD {int(self.hud_mask().sum())} cells, predicted-only {self.predicted_steps}")


if __name__ == "__main__":
    # synthetic: a ring of width 900 px, gain 0.5 px per mouse count, a HUD box that never moves
    rng = np.random.default_rng(1)
    H, W, ring = 96, 160, 900
    world = rng.integers(0, 6, (H, ring))
    world = np.repeat(np.repeat(world[::2, ::2], 2, 0), 2, 1)[:H, :ring]     # coarser texture, like a game
    eye = RotationEye(H, W); prev = None; x = 0.0
    def frame_at(x):
        xi = int(round(x)) % ring
        f = np.take(world, np.arange(xi, xi + W) % ring, axis=1).copy()
        f[80:90, 70:90] = 7                                                     # the HUD
        return f
    for t in range(400):
        m = int(rng.integers(-40, 41)) if t % 7 else 0
        x += 0.5 * m
        cur = frame_at(x)
        info = eye.step(prev, cur, (m, 0))
        prev = cur
        if info["events"] - {"rotation.yaw:L", "rotation.yaw:R", "rotation.realigned"}: print(t, sorted(info["events"]))
    print(eye.summary())
