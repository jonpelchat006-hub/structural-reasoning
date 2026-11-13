#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translation.py — the TRANSLATION EYE: keys move the body, parallax sorts the world into depth.

The second estimator on the sheet (rotation.py is the first). Rotation slides everything
equally; translation slides near things more than far things. So: on steps where a movement
key is held and the rotation shift is small, remove the rotation estimate, then measure each
region's own residual shift by local block matching. The running average of |residual| per
region is the DEPTH MAP — the "sheet with layers": still cells are the HUD (rotation.py owns
those), near-zero cells are far (skybox, distant geometry), large cells are near. The second
eye for depth is the previous frame: parallax over time, motion known because the key is known.

Cheap by design: 12x20 regions, ±4 search, only on translation steps — a few ms.
"""
from __future__ import annotations
import json, os
from typing import Dict, Optional, Tuple
import numpy as np

from species import Camera

MOVE_KEYS = {"left", "right", "jumpleft", "jumpright", "up", "jump"}


class TranslationEye:
    def __init__(self, H: int, W: int, tile: int = 8, search: int = 4):
        self.H, self.W, self.tile, self.search = H, W, tile, search
        self.h, self.w = H // tile, W // tile
        self.depth = np.zeros((self.h, self.w), np.float32)      # EMA of |parallax| per region
        self.n_obs = np.zeros((self.h, self.w), np.int32)
        self.steps = 0

    def step(self, prev: Optional[np.ndarray], cur: np.ndarray, action: str,
             rot_shift: Tuple[int, int], hud: Optional[np.ndarray] = None) -> Dict:
        """Call every look; it only works when a move key is held and rotation is quiet."""
        info = {"used": False, "near": 0}
        if prev is None or action not in MOVE_KEYS: return info
        if abs(rot_shift[0]) + abs(rot_shift[1]) > 3: return info      # rotation dominates this look
        a = prev if not (rot_shift[0] or rot_shift[1]) else Camera.shift(prev, rot_shift[0], rot_shift[1])
        if hud is not None:
            a = np.where(hud, -2, a); b = np.where(hud, -2, cur)
        else:
            b = cur
        self.steps += 1; info["used"] = True
        s, t = self.search, self.tile
        for i in range(self.h):
            for j in range(self.w):
                y, x = i * t, j * t
                if y - s < 0 or x - s < 0 or y + t + s > self.H or x + t + s > self.W:
                    ry0, rx0 = max(0, y - s), max(0, x - s)
                else:
                    ry0, rx0 = y - s, x - s
                block = a[y:y + t, x:x + t]
                if (block < 0).mean() > 0.5: continue                   # mostly HUD/unknown
                best, bmag = 1e9, 0.0
                for dy in range(-s, s + 1):
                    for dx in range(-s, s + 1):
                        yy, xx = y + dy, x + dx
                        if yy < 0 or xx < 0 or yy + t > self.H or xx + t > self.W: continue
                        diff = float((block != b[yy:yy + t, xx:xx + t]).mean())
                        if diff < best: best, bmag = diff, abs(dy) + abs(dx)
                if best < 0.4:                                          # the block was actually found again
                    self.n_obs[i, j] += 1
                    alpha = 1.0 / min(50, self.n_obs[i, j])
                    self.depth[i, j] = (1 - alpha) * self.depth[i, j] + alpha * bmag
        info["near"] = int((self.layers() == 2).sum())
        return info

    def layers(self) -> np.ndarray:
        """0 = far (no parallax), 1 = mid, 2 = near (strong parallax); -1 = unobserved."""
        out = np.full((self.h, self.w), -1, np.int8)
        seen = self.n_obs >= 5
        if not seen.any(): return out
        d = self.depth[seen]
        lo, hi = np.percentile(d, 40), np.percentile(d, 80)
        out[seen] = 1
        out[seen & (self.depth <= lo)] = 0
        out[seen & (self.depth >= hi) & (self.depth > 0.5)] = 2
        return out

    def save(self, path: str) -> None:
        np.savez_compressed(path, depth=self.depth, n=self.n_obs, steps=self.steps)

    @classmethod
    def load(cls, H: int, W: int, path: str) -> "TranslationEye":
        te = cls(H, W)
        try:
            d = np.load(path); te.depth, te.n_obs, te.steps = d["depth"], d["n"], int(d["steps"])
        except Exception: pass
        return te

    def summary(self) -> str:
        L = self.layers()
        return (f"depth: {int((L == 2).sum())} near, {int((L == 1).sum())} mid, {int((L == 0).sum())} far, "
                f"{int((L == -1).sum())} unseen regions ({self.steps} translation looks)")


if __name__ == "__main__":
    # synthetic parallax: near strip moves 3 px per step, far strip 0, mid 1
    rng = np.random.default_rng(0); H, W = 96, 160
    far = rng.integers(0, 6, (32, W + 400)); mid = rng.integers(0, 6, (32, W + 400)); near = rng.integers(0, 6, (32, W + 400))
    te = TranslationEye(H, W); prev = None
    for step in range(80):
        f = np.vstack([far[:, 0:W], mid[:, step:step + W], near[:, 3 * step:3 * step + W]]).astype(int)
        info = te.step(prev, f, "right", (0, 0)); prev = f
    L = te.layers()
    print(te.summary())
    print("rows (top=far):", [int(np.median(L[r])) for r in range(12)])
