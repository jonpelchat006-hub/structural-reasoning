#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fovea.py — the ROUND EYE and its SHAVES: what is actually seen is round; the square is the screen.

Jonathan (Aug 31): "shouldnt the screen we use inside be round but also be able to fit a square
inside it? the square screens are just because it's easier to make physical screens — what people
actually see is round. the shave off the eye gives it a focal point down that opening, like a
laser coming out. we can shave more than once — one cut for a normal eye, several for a fly's
eye with many sides, up to infinity for an all-seeing eye — even half the eye. and the angle of
the round-to-flat part determines how far it can see."

The geometry, taken literally on a unit sphere:
  - A SHAVE is a flat cut removing a spherical cap of depth d (0 < d <= 1; d=1 shaves half the
    eye). The flat face is a disc of radius a = sqrt(2d - d^2); the cone of sight through it has
    half-angle theta = arcsin(a).
  - REACH is concentration: one attention budget spread over the solid angle
    Omega = 2*pi*(1 - cos(theta)). reach = 1/Omega. A shallow shave is a narrow, far LASER
    (small Omega, huge reach); shaving half the eye sees the whole hemisphere at reach 1/(2*pi).
  - One shave = a normal eye (fovea dead center — "normal eyes focus in the center, so we have a
    round area we are looking at"). k shaves = a fly's eye: facet axes placed by the GOLDEN ANGLE
    (facet j at j x 137.5 deg — the ring's own packing law, so facets fill the view evenly as
    they are added one at a time, exactly like ring sections). Infinite shaves = the all-seeing
    limit: flat everywhere, every direction seen, zero concentration — the eye has become the
    screen again. The two ends meet: no shave sees nothing sharply, infinite shaves see
    everything unsharply; every real eye lives between.

On the planet's inner screen (the H x W symbol grid):
  - aperture(): the ROUND screen — the inscribed disc keeps its symbols, the four corners beyond
    the rim are set to the RIM symbol. The square still fits inside the round view the way he
    said: the largest square inside the disc is the central sqrt(2)/2 window, untouched.
  - facets(): the shaves — facet 0 bores down the center; facet j sits at radius 0.62*r along
    angle j x 137.5 deg. Each returns a crop whose SIDE comes from its depth (deep shave = wide
    flat = wide window) and whose REACH tags how concentrated that look is. The witness can be
    handed facet crops instead of (or beside) the whole frame; the forge can race facet configs
    like any candidate.

Opt-in and measurable, never assumed: the live Eye only rounds its screen if D:\\planet\\fovea.json
exists (e.g. {"shaves": 1, "depth": 0.35}). No file — nothing changes at play time.

Usage:  python fovea.py --demo          (show the law: depth -> angle -> reach table + a masked grid)
"""
from __future__ import annotations
import json, math, os
from typing import Dict, List, Optional, Tuple

import numpy as np

CONF = r"D:\planet\fovea.json" if os.name == "nt" else "/tmp/fovea.json"
GOLDEN_DEG = 360.0 * (1 - 1 / ((1 + 5 ** 0.5) / 2))
RIM = -1                        # the symbol beyond the round rim: not darkness — simply not seen


def shave_law(depth: float) -> Dict[str, float]:
    """depth of the flat cut -> opening radius, cone half-angle, solid angle, reach."""
    d = min(1.0, max(1e-4, depth))
    a = math.sqrt(max(0.0, 2 * d - d * d))          # radius of the flat disc
    theta = math.asin(min(1.0, a))                  # round-to-flat angle: how far it can see
    omega = 2 * math.pi * (1 - math.cos(theta))     # solid angle of the cone
    return {"depth": d, "opening": round(a, 4), "theta_deg": round(math.degrees(theta), 2),
            "omega_sr": round(omega, 4), "reach": round(1.0 / omega, 3)}


class Fovea:
    def __init__(self, shaves: int = 1, depth: float = 0.35):
        self.shaves = max(1, int(shaves))
        self.depth = float(depth)
        self.law = shave_law(self.depth)

    @classmethod
    def load(cls, path: str = CONF) -> Optional["Fovea"]:
        """The opt-in: a Fovea only exists if the dial file does."""
        try:
            c = json.load(open(path, encoding="utf-8"))
            return cls(c.get("shaves", 1), c.get("depth", 0.35))
        except Exception:
            return None

    # ---------------------------------------------------------------- the round screen
    def aperture(self, grid: np.ndarray) -> np.ndarray:
        """Round what is seen: keep the inscribed disc, RIM beyond it. The largest square that
        fits inside the disc (side r*sqrt(2)) is untouched — the square fits inside the round."""
        H, W = grid.shape
        cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
        r = min(H, W) / 2.0
        yy, xx = np.mgrid[0:H, 0:W]
        out = grid.copy()
        out[((yy - cy) ** 2 + (xx - cx) ** 2) > r * r] = RIM
        return out

    def apply(self, grid: Optional[np.ndarray]) -> Optional[np.ndarray]:
        return None if grid is None else self.aperture(grid)

    # ---------------------------------------------------------------- the shaves
    def facet_centers(self, H: int, W: int) -> List[Tuple[int, int, float]]:
        """(y, x, axis_deg) per shave. Facet 0 bores the center; the rest land by golden angle
        at 0.62*r — new facets always fill the largest gap left on the round, like ring sections."""
        cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
        r = min(H, W) / 2.0
        out = [(int(round(cy)), int(round(cx)), 0.0)]
        for j in range(1, self.shaves):
            ang = math.radians((j * GOLDEN_DEG) % 360.0)
            out.append((int(round(cy + 0.62 * r * math.sin(ang))),
                        int(round(cx + 0.62 * r * math.cos(ang))),
                        round(math.degrees(ang), 1)))
        return out

    def facets(self, grid: np.ndarray) -> List[Dict]:
        """Each shave's look: a crop down its opening. Deep shave = wide flat = wide window with
        low reach; shallow = a laser: a few pixels seen very hard."""
        H, W = grid.shape
        side = max(4, int(round(self.law["opening"] * min(H, W))))   # window side from the flat's radius
        half = side // 2
        looks = []
        for j, (y, x, ang) in enumerate(self.facet_centers(H, W)):
            y0, y1 = max(0, y - half), min(H, y + half)
            x0, x1 = max(0, x - half), min(W, x + half)
            looks.append({"facet": j, "axis_deg": ang, "center": (y, x),
                          "reach": self.law["reach"], "theta_deg": self.law["theta_deg"],
                          "crop": grid[y0:y1, x0:x1]})
        return looks

    def describe(self) -> str:
        kind = ("a normal eye" if self.shaves == 1 else
                f"a fly's eye with {self.shaves} facets" if self.shaves < 40 else
                f"nearly all-seeing ({self.shaves} facets)")
        return (f"{kind}: shave depth {self.depth} -> opening angle {self.law['theta_deg']} deg, "
                f"reach {self.law['reach']} (attention per steradian)")


def demo():
    print("the shave law — depth of the flat cut sets the angle, the angle sets the reach:")
    print(f"  {'depth':>6} {'theta':>8} {'omega(sr)':>10} {'reach':>8}")
    for d in (0.02, 0.1, 0.25, 0.5, 0.75, 1.0):
        L = shave_law(d)
        note = "  <- the laser" if d == 0.02 else "  <- half the eye: whole hemisphere, reach 1/2pi" if d == 1.0 else ""
        print(f"  {L['depth']:>6} {L['theta_deg']:>7}° {L['omega_sr']:>10} {L['reach']:>8}{note}")
    g = np.arange(16 * 24).reshape(16, 24) % 8
    f = Fovea(shaves=5, depth=0.35)
    a = f.aperture(g)
    rim = int((a == RIM).sum())
    print(f"\nround screen on a 16x24 grid: {rim} corner cells beyond the rim ({rim/g.size:.0%}) — "
          f"the inscribed square is untouched")
    print(f.describe())
    for lk in f.facets(g):
        print(f"  facet {lk['facet']} @ {lk['axis_deg']:>6}°  center {lk['center']}  "
              f"crop {lk['crop'].shape}  reach {lk['reach']}")


if __name__ == "__main__":
    demo()
