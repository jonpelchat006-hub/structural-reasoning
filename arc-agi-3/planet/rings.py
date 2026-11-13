#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
rings.py — THE RING RELATION: a thing the body enters that refills the register and is consumed.

ls20 level 2 (Sep 5): the body picked up the top-left ring twice in 370 presses and never reached the keyhole,
because every route to it was longer than the budget and the reset came first. The ring is a budget detour:
a thing of the register's own colour, standing on the floor, that the body drives onto; the bar refills by a
fixed gain and the ring is gone until the next reset.

    hypothesis(reg, f, amb)   before any refill was seen: things of the register's colour outside its band ARE rings
    learn(level_hist, reg, ...)  from the presses where the bar rose: the colour consumed, the gain, how often
    present(f, colour, amb)   the rings still standing in a frame
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage


def present(f, colour, amb, min_cells=4):
    """the rings of this colour standing in the frame (outside the register band)"""
    m = (f == colour)
    if amb is not None: m &= ~amb
    lab, n = ndimage.label(m); out = []
    for i in range(1, n + 1):
        cells = lab == i
        if cells.sum() < min_cells: continue
        ys, xs = np.where(cells)
        out.append({"id": f"{colour}@{int(ys.min())},{int(xs.min())}", "cells": cells, "colour": int(colour)})
    return out


def hypothesis(reg, f, amb):
    """the register's colour, standing on the floor, is a ring until shown otherwise"""
    if reg is None or reg.colour is None: return None
    if not present(f, reg.colour, amb): return None
    return {"colour": int(reg.colour), "gain": None, "confirmed": 0, "source": "hypothesis: the register's own colour"}


def learn(level_hist, reg, body_of, ops, amb, floor):
    """from the presses where the bar rose: which colour vanished under the body, and by how much the bar rose"""
    if reg is None or reg.colour is None: return None
    gains = {}; count = {}
    for f0, f1, a, x, y in level_hist:
        r0, r1 = reg.fill(f0), reg.fill(f1)
        if r0 is None or r1 is None or r1 <= r0: continue
        b1 = body_of(ops, f1)
        gone = (f0 != f1)
        if amb is not None: gone &= ~amb
        if b1 is not None: gone &= b1                                   # what the body now stands on
        cols = [int(c) for c in np.unique(f0[gone]) if int(c) not in floor]
        for c in cols:
            gains.setdefault(c, []).append(r1 - r0); count[c] = count.get(c, 0) + 1
    if not count: return None
    c = max(count, key=lambda k: count[k])
    return {"colour": c, "gain": float(np.median(gains[c])), "confirmed": count[c], "source": "learned from the refills"}
