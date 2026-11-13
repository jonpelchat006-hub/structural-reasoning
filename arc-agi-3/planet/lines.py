#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lines.py — PINS THAT CONNECT PIXELS: an object's own line across the floor to the wall.

Jonathan (Sep 5): the pins can connect different pixels too — a fan has a pin, a line that crosses the floor
until the wall; whatever interacts with something else gets a line to it. Pressing a control runs its lines
to the body, the body moves and touches the pins already there; a fan draws a sideways line, and the pixel
with the fan on it leaves that path on its pin.

Mechanically: a RIDE the displace operator learned (the body at place p was carried by w) is a LINE owned by
the object beside p — from p, in the direction of w, to the landing. Lines GENERALISE: every other object of
the same colour and the same orientation gets the same line from its open side, cast across the floor until
the first non-floor cell. The generalised lines are seeded back into every movement operator as rides, so
the closure includes fans the body has never ridden. The chain's fan map (ls20_chain.fan_cells) is the
ORACLE: precision/recall of the learned fan cells against it.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage

HUD = 56


def chain_fans(f):
    """the oracle, copied from ls20_chain.fan_cells: each colour-1 strip defends the 5x5 cell on its open side"""
    out = {}
    lab, n = ndimage.label(f[:HUD] == 1)
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < 3: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        if y0 == y1:
            xc = (x0 + x1) // 2
            if y0 + 1 < HUD and f[y0 + 1, xc] == 3: out[(int(y0) + 3, int(xc))] = (1, 0)
            if y0 - 1 >= 0 and f[y0 - 1, xc] == 3: out[(int(y0) - 3, int(xc))] = (-1, 0)
        elif x0 == x1:
            yc = (y0 + y1) // 2
            if x0 + 1 < 64 and f[yc, x0 + 1] == 3: out[(int(yc), int(x0) + 3)] = (0, 1)
            if x0 - 1 >= 0 and f[yc, x0 - 1] == 3: out[(int(yc), int(x0) - 3)] = (0, -1)
    return out


def _strips(f, colour, floor, amb=None):
    """the objects of one colour, with their orientation and open side(s)"""
    m = (f == colour)
    if amb is not None: m &= ~amb
    lab, n = ndimage.label(m); out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) < 2: continue
        y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
        horiz = (y1 - y0) < (x1 - x0)
        out.append({"cells": lab == i, "box": (y0, y1, x0, x1), "horiz": horiz, "colour": colour, "n": int(len(ys))})
    return out


def cast(f, start, direction, floor, quantum, body_size=5, limit=20):
    """the line: from `start`, step by the lattice quantum in `direction` while the body's square would stand on
    floor; the landing is the last standable place. Returns (landing, cells along the line)."""
    y, x = start; dy, dx = direction[0] * quantum, direction[1] * quantum; r = body_size // 2; H, W = f.shape
    landing = None; path = []
    for _ in range(limit):
        ny, nx = y + dy, x + dx
        if ny - r < 0 or nx - r < 0 or ny + r >= H or nx + r >= W: break
        win = f[ny - r:ny + r + 1, nx - r:nx + r + 1]
        if not set(int(v) for v in win.flatten()) <= floor: break
        y, x = ny, nx; landing = (y, x); path.append((y, x))
    return landing, path


def learn(f, rides, floor, quantum, amb=None, body_size=5):
    """rides: {place: vector} from the displace operators. For each ride find the object beside the place (the
    strip whose box touches the body's square there) and give it a line. Returns the lines and the strip
    colours seen, so the lines can generalise."""
    lines = []
    r = body_size // 2
    objs = []
    for c in set(int(v) for v in np.unique(f)) - floor:
        objs += _strips(f, c, floor, amb)
    for (py, px), (wy, wx) in rides.items():
        d = (int(np.sign(wy)), int(np.sign(wx)))
        if d == (0, 0): continue
        # the object whose box touches the body's square at the place, on the side opposite the ride
        near = None
        for o in objs:
            y0, y1, x0, x1 = o["box"]
            touch_y = y0 <= py + r + 1 and y1 >= py - r - 1; touch_x = x0 <= px + r + 1 and x1 >= px - r - 1
            if touch_y and touch_x: near = o; break
        landing = (py + wy, px + wx)
        lines.append({"from": (int(py), int(px)), "dir": d, "to": (int(landing[0]), int(landing[1])),
                      "owner": None if near is None else (near["colour"], near["box"], near["horiz"]), "learned": True})
    return lines


def generalise(f, lines, floor, quantum, amb=None, body_size=5):
    """every object with the same colour and orientation as a learned line's owner gets the same kind of line
    from its open side: the fan cell is one quantum off the strip's face, the line runs away from the strip"""
    out = []; seen = set((l["from"]) for l in lines)
    kinds = set((l["owner"][0], l["owner"][2]) for l in lines if l["owner"] is not None)
    if not kinds: return out
    for colour, horiz in kinds:
        for o in _strips(f, colour, floor, amb):
            if o["horiz"] != horiz: continue
            y0, y1, x0, x1 = o["box"]
            faces = [((y1 + 1) + (body_size // 2), (x0 + x1) // 2, (1, 0)), ((y0 - 1) - (body_size // 2), (x0 + x1) // 2, (-1, 0))] if horiz else \
                    [((y0 + y1) // 2, (x1 + 1) + (body_size // 2), (0, 1)), ((y0 + y1) // 2, (x0 - 1) - (body_size // 2), (0, -1))]
            for fy, fx, d in faces:
                r = body_size // 2
                if fy - r < 0 or fx - r < 0 or fy + r >= f.shape[0] or fx + r >= f.shape[1]: continue
                win = f[fy - r:fy + r + 1, fx - r:fx + r + 1]
                if not set(int(v) for v in win.flatten()) <= floor: continue        # the fan cell must be standable floor
                if (fy, fx) in seen: continue
                landing, path = cast(f, (fy, fx), d, floor, quantum, body_size)
                if landing is None: continue
                out.append({"from": (int(fy), int(fx)), "dir": d, "to": landing, "owner": (colour, o["box"], horiz), "learned": False})
                seen.add((fy, fx))
    return out


def snap_key(p, quantum, anchor):
    """the lattice cell a place falls in, relative to the body's lattice (the operators key rides by the body's
    top-left, the chain keys fans by the body's centre)"""
    return (int(p[0]), int(p[1]))


def oracle_check(f, lines, quantum=5):
    """precision / recall of the learned+generalised fan cells against the chain's fan map (cells within one
    quantum of each other count as the same fan)"""
    truth = chain_fans(f); mine = [l["from"] for l in lines]
    def near(a, B): return any(abs(a[0] - b[0]) <= quantum and abs(a[1] - b[1]) <= quantum for b in B)
    tp = sum(1 for m in mine if near(m, truth)); fp = len(mine) - tp; fn = sum(1 for t in truth if not near(t, mine))
    return {"oracle_fans": len(truth), "mine": len(mine), "tp": tp, "fp": fp, "fn": fn,
            "precision": round(tp / len(mine), 2) if mine else None, "recall": round(tp / len(truth), 2) if truth else None}


def seed_rides(ops, lines, body_size=5):
    """put every line into every movement operator as a ride keyed by the body's top-left at the fan cell"""
    n = 0
    for op in ops.ops.values():
        if not hasattr(op, "rides"): continue
        for l in lines:
            fy, fx = l["from"]; ty, tx = l["to"]
            key = (fy - body_size // 2, fx - body_size // 2) if not l["learned"] else (fy, fx)
            if key not in op.rides: op.rides[key] = (ty - fy, tx - fx); n += 1
    return n
