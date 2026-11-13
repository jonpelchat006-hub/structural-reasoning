#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hue.py — where each world lives on the color circle (Jonathan's marker construction, measured).

The ladder (Sep 1): point (one red) -> line (wavelengths of red) -> square (+saturation) ->
cube (+brightness) -> a MARKER where the line hands over to the next color -> markers movable,
each segment its own cube -> going through the colors completes a CIRCLE. The markers here are
12 fixed 30-degree hue segments (movable later — learnable bin edges, like the Eye's luminance
EDGES). The planet's Eye is currently colorblind (luminance+edge only); this probe asks whether
color eyes would PAY: do the worlds occupy distinct segments of the circle?

Usage:  python hue.py            (newest clip per world -> hue histogram over the 12 markers)
"""
from __future__ import annotations
import glob, io, json, os, sys

import numpy as np

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
SEGS = ["red", "orange", "yellow", "chartreuse", "green", "spring",
        "cyan", "azure", "blue", "violet", "magenta", "rose"]      # 12 markers, 30 deg each


def _rgb_to_hsv(img: np.ndarray):
    """Vectorized RGB->HSV (h in [0,1), s,v in [0,1])."""
    a = img.astype(float) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-12
    h = np.zeros_like(mx)
    m = mx == r; h[m] = ((g - b)[m] / d[m]) % 6
    m = mx == g; h[m] = (b - r)[m] / d[m] + 2
    m = mx == b; h[m] = (r - g)[m] / d[m] + 4
    return h / 6.0, d / (mx + 1e-12), mx


def world_hues(wroot: str, frames: int = 4):
    clips = sorted(glob.glob(os.path.join(wroot, "clips", "clip_*.npz")))
    if not clips: return None
    try:
        from PIL import Image
    except Exception:
        return "no-PIL"
    z = np.load(clips[-1], allow_pickle=True)
    jpegs = [bytes(b) for b in z["J"]]
    step = max(1, len(jpegs) // frames)
    hist = np.zeros(12)
    n = 0
    for jb in jpegs[::step][:frames]:
        img = np.asarray(Image.open(io.BytesIO(jb)).convert("RGB"))[::4, ::4]
        h, s, v = _rgb_to_hsv(img)
        mask = (s > 0.25) & (v > 0.15)               # drop the gray world: UI, fog, shadow
        if mask.sum() < 50: continue
        hist += np.bincount((h[mask] * 12).astype(int) % 12, minlength=12)
        n += mask.sum()
    if n == 0: return "gray"
    return (hist / hist.sum()).round(3).tolist()


def main():
    out = {}
    for wroot in sorted(glob.glob(os.path.join(OCEAN, "*"))):
        if not os.path.isdir(os.path.join(wroot, "clips")): continue
        w = os.path.basename(wroot)
        r = world_hues(wroot)
        if r is None: continue
        out[w] = r
        if isinstance(r, list):
            top = sorted(range(12), key=lambda i: -r[i])[:3]
            print(f"{w:26s} " + "  ".join(f"{SEGS[i]}:{r[i]:.0%}" for i in top))
        else:
            print(f"{w:26s} {r}")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
