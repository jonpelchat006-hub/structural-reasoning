#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
meter.py — THE BUDGET METER AS PINS.

Jonathan (Sep 6): "that meter is one colour and changes to another surrounded by one other, so each turn when it
drains we would see how much and then we would be able to start predicting that each turn would drain it. Each
pixel in that bar would put those pins in that direction dragging the rest, but it wouldn't drag the surrounding
colour all the way, so that would be where it ends."

The band is the register's rows (the tick region play.py already finds). Inside it three colours: the bar, the
drained (what the bar turns into), and the surround (what the band is framed by). Every press the front moves;
the cells it uncovered lay their pins down pointing the way the front went (the drain direction), and the count
is the drain of that press. The pins drag the rest of the bar: the same drain next move, and the one after. The
surround is not dragged: where the bar's colour meets the surround at the start is THE END, and the moves left
are the pins still standing between the front and the end, divided by the drain. A refill is the front jumping
back the other way (a ride): the pins stand up again.

    observe(f0, f1, moved) -> {"drained": n, "refill": bool} | None
    left()                 -> moves left (None until the drain is known)
    summary()              -> one line for the log
"""
from __future__ import annotations
import numpy as np


class Meter:
    def __init__(self):
        self.band = None; self.bar = None; self.drained_col = None; self.direction = None   # direction: +1 front moves toward larger x, -1 smaller
        self.axis = None            # 1: the bar runs along x (columns), 0: along y
        self.drain_moves = []       # cells drained on presses where the body moved
        self.drain_still = []       # cells drained on refused presses
        self.pins = None            # per band column: 1 standing (bar), 0 laid (drained), -1 beyond (surround / never bar)
        self.end = None             # the coordinate where the bar met the surround at the start
        self.right = 0; self.wrong = 0; self.refills = 0
        self.predicted = None

    def fit(self, band, colour, f):
        """band: the register's rows/cols mask; colour: the bar colour; f: a frame to read the bar's extent from"""
        self.band = band; self.bar = int(colour)
        ys, xs = np.where(band)
        if len(ys) == 0: return self
        self.axis = 1 if (xs.max() - xs.min()) >= (ys.max() - ys.min()) else 0
        line = self._line(f)
        self.pins = np.where(line == self.bar, 1, -1).astype(np.int8)
        return self

    def _line(self, f):
        """the band collapsed to one line along its axis: the colour that fills each column (the bar's colour if any cell is)"""
        ys, xs = np.where(self.band)
        if self.axis == 1:
            cols = sorted(set(xs.tolist())); out = np.full(max(cols) + 1, -1, int)
            for x in cols:
                v = f[ys[xs == x], x]
                out[x] = self.bar if (v == self.bar).any() else int(np.bincount(v).argmax())
        else:
            rows = sorted(set(ys.tolist())); out = np.full(max(rows) + 1, -1, int)
            for y in rows:
                v = f[y, xs[ys == y]]
                out[y] = self.bar if (v == self.bar).any() else int(np.bincount(v).argmax())
        return out

    def stand(self, f):
        """a reset: the bar is back as the frame shows it; the pins stand accordingly"""
        if self.band is None: return
        line = self._line(f); self.pins = np.where(line == self.bar, 1, np.where(self.pins == -1, -1, 0)).astype(np.int8)

    def observe(self, f0, f1, moved):
        if self.band is None or self.pins is None: return None
        l0 = self._line(f0); l1 = self._line(f1)
        bar0 = np.where(l0 == self.bar)[0]; bar1 = np.where(l1 == self.bar)[0]
        if len(bar0) == 0 and len(bar1) == 0: return None
        n0, n1 = len(bar0), len(bar1)
        out = {"drained": 0, "refill": False}
        if n1 > n0 + 2:
            self.refills += 1; out["refill"] = True
            self.pins[bar1] = 1                                          # the pins stand up again
            return out
        if n1 < n0:
            gone = np.setdiff1d(bar0, bar1)
            out["drained"] = int(len(gone))
            if self.direction is None and len(gone):
                hi = gone.max()
                self.direction = +1 if (len(bar1) and bar1.min() > hi) else -1                  # the remaining bar lies beyond the vanished end: the front moves +1
            self.pins[gone] = 0                                          # laid down, pointing the way the front went
            if self.drained_col is None and len(gone): self.drained_col = int(l1[gone[0]])
            if self.end is None:
                # the end: where the standing bar meets the surround, on the side the front is moving toward
                std = np.where(self.pins == 1)[0]
                if len(std): self.end = int(std.max() if self.direction == +1 else std.min())
            (self.drain_moves if moved else self.drain_still).append(out["drained"])
        else:
            (self.drain_moves if moved else self.drain_still).append(0)
        if self.predicted is not None:
            if out["drained"] == self.predicted: self.right += 1
            else: self.wrong += 1
        return out

    def drain(self):
        if len(self.drain_moves) < 2: return None
        return float(np.median(self.drain_moves[-12:]))

    def still_free(self):
        """do refused presses leave the bar alone?"""
        if not self.drain_still: return None
        return float(np.mean([d == 0 for d in self.drain_still]))

    def predict(self, moved=True):
        d = self.drain()
        if d is None: return None
        if not moved and self.still_free() is not None and self.still_free() >= 0.8: self.predicted = 0
        else: self.predicted = int(round(d))
        return self.predicted

    def standing(self):
        return int((self.pins == 1).sum()) if self.pins is not None else 0

    def left(self):
        d = self.drain()
        if d is None or d <= 0 or self.pins is None: return None
        return self.standing() / d

    def summary(self):
        d = self.drain(); sf = self.still_free()
        if d is None: return "meter: the drain is not known yet"
        tot = self.right + self.wrong
        lf = self.left()
        left_s = f"{lf:.0f} moves left" if lf is not None else "moves left unknown"
        return (f"meter: bar colour {self.bar} drains {d:.0f} cells per move toward {'+' if self.direction == 1 else '-'}{'x' if self.axis == 1 else 'y'}"
                + (f", {sf:.0%} of refused presses drain nothing" if sf is not None else "")
                + f"; {self.standing()} pins standing, the end at {self.end}, {left_s}; the pins predicted the drain in {self.right}/{tot}"
                + (f"; {self.refills} refills (the pins stood up again)" if self.refills else ""))

    def stats(self):
        return {"bar": self.bar, "drain": self.drain(), "still_free": self.still_free(), "standing": self.standing(), "end": self.end,
                "left": self.left(), "right": self.right, "wrong": self.wrong, "refills": self.refills, "direction": self.direction}
