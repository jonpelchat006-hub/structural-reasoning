#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fence.py — THE FLOOR FLOW FIELD: middle pins, border pins, and the colour rule behind them.

Jonathan (Sep 5): "each pin on each pixel of floor lays down or gets split and laid down pointing in the directions
you are allowed to go; moving the body over it knocks it over; that starts making its own trail, and the hallway
would be connected to the goal because those flow lines developed. There's a fence on the pixel border too: when
we move onto the pixel it bends the middle pin, when we leave it bends the border pin, but when there's a wall
the border pin breaks. The middle pins reach to the border and the border pins reach to the next middle — a way
to double-verify where you can go. Against a bottom wall, moving left, right, up leaves those pins, but you can't
move down — so far away, with the same floor and wall colours, it won't bend that way either."

    mid[k, y, x]     the middle pin of cell (y,x) in direction k:  +1 laid (the body passed over this cell going k)
    border[k, y, x]  the fence between (y,x) and its neighbour in direction k:  +1 bent (crossed), -1 broken (refused)
    rule[(near colour, far colour, k)] = [passes, blocks]   the generalisation: the same colours far away answer the same
    pred[k, y, x]    what the fence says about a border nobody has touched: the rule applied to the level's ground

The chain mid -> border -> next mid is the trail. Where a mid pin is laid toward a border that is neither bent nor
broken, the chain stops: that is an OPENING, the end of a channel, where the next press should go.

Directions k: 0 up (-1,0), 1 down (+1,0), 2 left (0,-1), 3 right (0,+1). The opposite of k is k ^ 1.
"""
from __future__ import annotations
import json
import numpy as np
from scipy.ndimage import label as ndimage_label

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
NAMES = ["up", "down", "left", "right"]


def unit_of(d):
    """the direction index and the step count of a displacement (dy, dx)"""
    dy, dx = int(d[0]), int(d[1])
    if dy == 0 and dx == 0: return None, 0
    if abs(dy) >= abs(dx): return (0 if dy < 0 else 1), abs(dy)
    return (2 if dx < 0 else 3), abs(dx)


def shifted(S, dy, dx):
    """S moved by (dy, dx), cells leaving the frame dropped"""
    H, W = S.shape; out = np.zeros_like(S)
    ys, xs = np.where(S); ys2, xs2 = ys + dy, xs + dx
    ok = (ys2 >= 0) & (ys2 < H) & (xs2 >= 0) & (xs2 < W)
    out[ys2[ok], xs2[ok]] = True
    return out


class Fence:
    def __init__(self, shape):
        H, W = shape
        self.shape = (H, W)
        self.mid = np.zeros((4, H, W), np.int8)
        self.border = np.zeros((4, H, W), np.int8)
        self.rule: dict = {}
        self.pred = np.zeros((4, H, W), np.int8)
        self.ground = None
        self.exempt = np.zeros((H, W), bool)             # cells another layer answers for (a relation's target): the fence never blocks them
        self.brushed = np.zeros((4, H, W), np.int8)       # THE SIDES (Jonathan, Sep 5): borders the body slid along without crossing — dragged down
        self.prior: dict = {}                             # THE PINS PERSIST (Jonathan, Sep 6): colour rules from earlier levels and runs, magnets until this level confirms them
        self.pull = np.zeros((4, H, W), np.float32)       # THE MAGNETS: how hard the broken pins pull each untouched border toward "wall"
        self.presses = 0; self.passes = 0; self.refusals = 0

    def exempt_cells(self, cells):
        """a relation says this thing opens when its region matches: the borders into it are not the fence's to
        block, whatever a bump before the match taught"""
        from scipy import ndimage
        self.exempt |= ndimage.binary_dilation(cells, iterations=1)

    # ---- colours at a border: the near side is what the body stands on (the floor it leaves behind), the far side what lies ahead
    @staticmethod
    def _colours(f0, S, fill, y, x, k):
        dy, dx = DIRS[k]; y2, x2 = y + dy, x + dx
        H, W = f0.shape
        if not (0 <= y2 < H and 0 <= x2 < W): return None
        near = int(fill) if S[y, x] else int(f0[y, x])
        far = int(fill) if S[y2, x2] else int(f0[y2, x2])
        return near, far

    def _teach(self, key, passed):
        r = self.rule.setdefault(key, [0, 0]); r[0 if passed else 1] += 1

    # ---- observation of one press
    def observe(self, f0, f1, S0, S1, fill, d_expected=None):
        """S0: the body before, S1: the body after (None when it could not be found); fill: the floor colour the body
        leaves behind; d_expected: the operator's step for this button (used when the body did not move: the
        direction it was refused in). Returns 'pass', 'refused' or None."""
        self.presses += 1
        if S0 is None: return None
        if S1 is not None and not np.array_equal(S0, S1) and S0.sum() == S1.sum():
            ys0, xs0 = np.where(S0); ys1, xs1 = np.where(S1)
            w = (int(ys1.min() - ys0.min()), int(xs1.min() - xs0.min()))
            if not np.array_equal(shifted(S0, *w), S1): return None      # not a rigid move (a transform, a respawn): no pins
            k, q = unit_of(w)
            if k is None or (w[0] and w[1]): return None                 # diagonal: no fence to speak of
            if d_expected is not None and tuple(w) != tuple(d_expected) and q > 2 * max(abs(d_expected[0]), abs(d_expected[1])):
                return None                                               # a respawn (the bar ran dry, the body reappeared at the start) is not a move: no pins, no rule
            self.passes += 1
            dy, dx = DIRS[k]
            swept = np.zeros_like(S0)
            for i in range(q + 1): swept |= shifted(S0, dy * i, dx * i)
            sides = [j for j in range(4) if j not in (k, k ^ 1)]
            for i in range(q + 1):
                layer = shifted(S0, dy * i, dx * i)
                self.mid[k][layer] = 1                                    # the middle pin bends the way the body went
                for j in sides:                                           # the body's flanks drag the side borders down as it slides past
                    jy, jx = DIRS[j]
                    beyond = shifted(layer, jy, jx) & ~swept              # the cell on the far side of that border, not part of the sweep
                    flank = shifted(beyond, -jy, -jx) & layer
                    self.brushed[j][flank & (self.border[j] == 0)] = 1
                if i < q:
                    for y, x in zip(*np.where(layer)):
                        self.border[k, y, x] = 1                          # the border bends when the body leaves the cell
                        y2, x2 = y + dy, x + dx
                        if 0 <= y2 < self.shape[0] and 0 <= x2 < self.shape[1]: self.border[k ^ 1, y2, x2] = 1
                        c = self._colours(f0, S0, fill, y, x, k)
                        if c is not None: self._teach((c[0], c[1], k), True)
            return "pass"
        if S1 is not None and np.array_equal(S0, S1) and d_expected is not None:
            k, q = unit_of(d_expected)
            if k is None: return None
            self.refusals += 1
            dy, dx = DIRS[k]
            # the wall is the first cell ahead (within the step) whose colour is not the floor the body walks on; failing
            # that, an unseen wall right at the leading edge. The border there breaks.
            lead = np.zeros_like(S0)                                      # the leading edge: body cells with no body cell ahead of them
            for y, x in zip(*np.where(S0)):
                y2, x2 = y + dy, x + dx
                if not (0 <= y2 < self.shape[0] and 0 <= x2 < self.shape[1]) or not S0[y2, x2]: lead[y, x] = True
            for y, x in zip(*np.where(lead)):
                wall_at = None
                for i in range(1, q + 1):
                    y2, x2 = y + dy * i, x + dx * i
                    if not (0 <= y2 < self.shape[0] and 0 <= x2 < self.shape[1]): wall_at = i - 1; break
                    if int(f0[y2, x2]) != int(fill) and not S0[y2, x2]: wall_at = i - 1; break
                unseen = wall_at is None
                if wall_at is None: wall_at = 0                          # every cell ahead looks like floor: an unseen wall at the edge
                by, bx = y + dy * wall_at, x + dx * wall_at
                self.border[k, by, bx] = -1
                y2, x2 = by + dy, bx + dx
                if 0 <= y2 < self.shape[0] and 0 <= x2 < self.shape[1]: self.border[k ^ 1, y2, x2] = -1
                c = self._colours(f0, S0, fill, by, bx, k)
                # an unseen wall is a place, not a law of colours (Sep 6: sp80's arena bound had taught "floor into floor
                # going down blocks" and the bar could not be planned downward anywhere)
                if c is not None and not unseen: self._teach((c[0], c[1], k), False)
            return "refused"
        return None

    # ---- the generalisation: the rule applied to the level's ground, the known borders on top
    def compile(self, ground):
        """ground: the level's start frame with the body's cells painted the floor colour. pred[k] holds, per border,
        +1 (the rule says pass), -1 (the rule says block), 0 (nobody knows); a border that was bent or broken keeps
        its own answer."""
        self.ground = ground
        H, W = self.shape
        self.pred[:] = 0
        for (near, far, k), (p, b) in self.rule.items():
            # a rule that was seen both ways (the keyhole: blocked until the region matched, then passed) is not the
            # fence's to answer — something else decides there; only one-sided evidence is laid down far away.
            # THE GAME ALWAYS WINS (Jonathan, Sep 6): the pins broken by real refusals displace the imagined bent ones —
            # when the refusals outweigh a stray pass five to one, the wall stands; the stray pass stays as a faint
            # hypothesis in `pull` until more refusals push it out
            if p and b and not (b >= 5 * max(1, p) or p >= 5 * max(1, b)): continue
            if p and b: p, b = (0, b) if b > p else (p, 0)
            dy, dx = DIRS[k]
            m = (ground == near)
            m2 = shifted((ground == far), -dy, -dx)                       # cells whose neighbour in direction k has colour `far`
            sel = m & m2
            self.pred[k][sel] = 1 if p > b else -1
        # THE MAGNETS (Jonathan, Sep 6): a broken pin pulls its likes. The same colours and direction: with it (1.0, a wall
        # for the planner). The same colours, another direction: dragged too, weakly (0.5) — the body probably won't go
        # into that wall from another side either. The same far colour, any near colour, any direction: faintly (0.25).
        # The rules carried from earlier levels and runs pull at 0.75 until one bump on this level confirms them.
        self.pull[:] = 0
        def one_sided(v_): return (v_[1] > 0 and v_[0] == 0) or (v_[1] >= 5 * max(1, v_[0]) and v_[1] >= 5)
        blockers = [(k_, 1.0) for k_, v_ in self.rule.items() if one_sided(v_)]
        # THE MERGE (Jonathan, Sep 6): when two or more near colours agree that a far colour blocks in a direction, the
        # pins align at the centre — the far colour blocks from any near colour, at 0.75 until each pair is seen
        agree = {}
        for (near, far, k), v_ in self.rule.items():
            if one_sided(v_): agree.setdefault((far, k), set()).add(near)
        merged = [((None, far, k), 0.75) for (far, k), nears in agree.items() if len(nears) >= 2]
        self.merged_rules = [(far, k) for (far, k), nears in agree.items() if len(nears) >= 2]
        blockers += [(k_, 0.75) for k_, v_ in self.prior.items() if v_[1] > 0 and v_[0] == 0 and k_ not in self.rule]
        for (near, far, k), w in blockers + merged:
            for kk in range(4):
                dy, dx = DIRS[kk]
                m2 = shifted((ground == far), -dy, -dx)
                same = ((ground == near) if near is not None else (ground != far)) & m2
                self.pull[kk] = np.maximum(self.pull[kk], (w if kk == k else w * 0.5) * same)
                self.pull[kk] = np.maximum(self.pull[kk], w * 0.25 * m2)
        known = self.border != 0
        self.pred[known] = self.border[known]
        for k, (dy, dx) in enumerate(DIRS):                                # a border into an exempt cell is never blocked
            into = shifted(self.exempt, -dy, -dx) | self.exempt
            self.pred[k][into & (self.pred[k] == -1)] = 0
        # a brushed border the rule calls a wall is a pin dragged down along the wall: laid, part of the map
        self.dragged = (self.brushed == 1) & (self.pred == -1)
        self.gfar = np.stack([self.far_colours(ground, k) for k in range(4)])    # what lay beyond each border when this was learned
        # THE FALLEN PINS (Jonathan, Sep 5): the pin that matched the bump breaks off and lies INSIDE the wall pixel,
        # disconnected from the floor; where fallen pins touch, the wall connects from the inside into pieces
        H, W = self.shape; self.fallen = np.zeros((H, W), bool)
        for k, (dy, dx) in enumerate(DIRS):
            src = (self.border[k] == -1) | ((self.pred[k] == -1) & (self.mid[k] == 1))   # bumped, or the trail's cell facing a predicted wall
            self.fallen |= shifted(src, dy, dx)
        self.fallen &= ~(self.mid == 1).any(axis=0)                                     # inside the wall, never on the trail
        lab, n = ndimage_label(self.fallen); self.wall_pieces = n
        return self

    @staticmethod
    def far_colours(F, k):
        """per cell, the colour of its neighbour in direction k (-1 beyond the frame)"""
        dy, dx = DIRS[k]; H, W = F.shape; out = np.full((H, W), -1, np.int16)
        ys = slice(max(0, -dy), H - max(0, dy)); xs = slice(max(0, -dx), W - max(0, dx))
        ys2 = slice(max(0, dy), H - max(0, -dy)); xs2 = slice(max(0, dx), W - max(0, -dx))
        out[ys, xs] = F[ys2, xs2]
        return out

    def circuit(self):
        """THE CIRCUIT: of the walked floor's borders (every cell with a middle pin, four borders each), the share that
        has an answer — bent, broken, dragged down along a wall, or predicted by the rule. 1.0 is a closed circuit:
        no open terminal left on the trail."""
        walked = (self.mid == 1).any(axis=0)
        if not walked.any(): return 0.0, 0
        answered = (self.border != 0) | (self.pred != 0) | (self.brushed == 1) & (self.pred == -1)
        tot = 4 * int(walked.sum()); got = int(answered[:, walked].sum())
        return got / tot, tot - got

    def blocks(self, f0, S, d, fill=None):
        """would the fence stop the body S moving by d? True when a border it must cross is broken or predicted broken."""
        k, q = unit_of(d)
        if k is None: return False
        dy, dx = DIRS[k]
        neg = (self.pred[k] == -1)
        if getattr(self, "gfar", None) is not None:                     # a border learned on one colour says nothing once that colour changed (a door, a state)
            neg = neg & (self.far_colours(f0, k) == self.gfar[k])
        for i in range(q):
            layer = shifted(S, dy * i, dx * i)
            if (neg & layer).any(): return True
        return False

    # ---- the trail and its ends
    def openings(self, ground=None):
        """cells with a middle pin laid toward a border that is neither bent nor broken and not predicted broken:
        where the chain mid -> border -> mid stops. Returns [(y, x, k, channel length)] longest channel first."""
        out = []
        H, W = self.shape
        ground = ground if ground is not None else self.ground
        for k in range(4):
            dy, dx = DIRS[k]
            cells = np.argwhere((self.mid[k] == 1) & (self.border[k] == 0) & (self.pred[k] != -1))
            for y, x in cells:
                y2, x2 = y + dy, x + dx
                if not (0 <= y2 < H and 0 <= x2 < W): continue
                # the channel behind it: how many middle pins in a row point this way
                n = 0; yy, xx = y, x
                while 0 <= yy < H and 0 <= xx < W and self.mid[k, yy, xx] == 1 and n < 64: n += 1; yy -= dy; xx -= dx
                # a far colour that blocks in some other direction is probably a wall here too: one bump verifies the rule
                # for this direction; a far colour never seen to block is open country and ranks first
                far = int(ground[y2, x2]) if ground is not None else -1
                walled = float(self.pull[k, y, x]) >= 0.5 or any(v[1] > 0 and v[0] == 0 and kk[1] == far for kk, v in self.rule.items())
                out.append((int(y), int(x), k, n, walled, "ahead"))
            # THE SIDE OPENINGS: a border the body slid along, not predicted a wall, onto a cell no pin was ever laid on —
            # a branch the trail passed without turning
            unwalked = ~(self.mid == 1).any(axis=0)
            sel = (self.brushed[k] == 1) & (self.border[k] == 0) & (self.pred[k] != -1) & shifted(unwalked, -dy, -dx)
            for y, x in np.argwhere(sel):
                y2, x2 = y + dy, x + dx
                far = int(ground[y2, x2]) if ground is not None else -1
                walled = float(self.pull[k, y, x]) >= 0.5 or any(v[1] > 0 and v[0] == 0 and kk[1] == far for kk, v in self.rule.items())
                # the channel that passes it: middle pins along the trail's own axis at this cell
                n = sum(1 for kk in range(4) if kk not in (k, k ^ 1) and self.mid[kk, y, x] == 1)
                out.append((int(y), int(x), k, n, walled, "side"))
        out.sort(key=lambda t: (t[4], t[5] != "ahead", -t[3]))
        return out

    def opening_objects(self, ground=None):
        """the openings as things for the experiment loop: the strip of cells beyond the border, grouped where they
        touch, each with the direction of the chain that reaches it and the length of that channel"""
        from scipy import ndimage
        H, W = self.shape; objs = []
        ops = self.openings(ground)
        for k in range(4):
            dy, dx = DIRS[k]
            for kind in ("ahead", "side"):
                m = np.zeros((H, W), bool); ln = {}
                for y, x, kk, n, walled, kd in ops:
                    if kk != k or kd != kind: continue
                    m[y + dy, x + dx] = True; ln[(y + dy, x + dx)] = (n, walled)
                if not m.any(): continue
                lab, nl = ndimage.label(m)
                for i in range(1, nl + 1):
                    cells = lab == i; ys, xs = np.where(cells)
                    n = max(ln[(int(y), int(x))][0] for y, x in zip(ys, xs)); walled = all(ln[(int(y), int(x))][1] for y, x in zip(ys, xs))
                    objs.append({"id": f"open@{int(ys.min())},{int(xs.min())} {NAMES[k]}" + (" side" if kind == "side" else ""), "cells": cells,
                                 "open": k, "len": n, "walled": walled, "kind": kind,
                                 "colour": int(ground[ys[0], xs[0]]) if ground is not None else -1})
        objs.sort(key=lambda o: (o["walled"], o["kind"] != "ahead", -o["len"]))
        return objs

    def stats(self):
        laid = int((self.mid == 1).sum()); bent = int((self.border == 1).sum()) // 2; broken = int((self.border == -1).sum())
        pb = int((self.pred == -1).sum()); pp = int((self.pred == 1).sum())
        rules = {f"{k[0]}>{k[1]} {NAMES[k[2]]}": v for k, v in self.rule.items()}
        ops = self.openings(); closed, open_terms = self.circuit()
        return {"laid": laid, "bent": bent, "broken": broken, "predicted_block": pb, "predicted_pass": pp,
                "brushed": int((self.brushed == 1).sum()), "dragged": int(getattr(self, "dragged", np.zeros(1, bool)).sum()),
                "rules": rules, "passes": self.passes, "refusals": self.refusals, "openings": len(ops),
                "openings_ahead": sum(1 for o in ops if o[5] == "ahead"), "openings_side": sum(1 for o in ops if o[5] == "side"),
                "circuit": round(closed, 3), "open_terminals": open_terms,
                "fallen": int(getattr(self, "fallen", np.zeros(1, bool)).sum()), "wall_pieces": int(getattr(self, "wall_pieces", 0)),
                "pulled_weakly": int(((self.pull >= 0.25) & (self.pull < 1.0) & (self.pred == 0)).sum()), "prior_rules": len(self.prior),
                "merged": [f"{far} {NAMES[k]}" for far, k in getattr(self, "merged_rules", [])],
                "corrected": [f"{a}>{b} {NAMES[k]}" for (a, b, k), v in self.rule.items() if v[0] and v[1] and (v[1] >= 5 * max(1, v[0]) or v[0] >= 5 * max(1, v[1]))]}

    def summary(self):
        s = self.stats()
        blocks = sorted((k for k, v in self.rule.items() if v[1] > 0 and v[0] == 0), key=lambda k: -self.rule[k][1])
        return (f"{s['laid']} pins laid, {s['bent']} borders bent, {s['broken']} broken, {s['dragged']} dragged down along walls; rule predicts "
                f"{s['predicted_block']} borders blocked far away" + (f" ({', '.join(f'{a}>{b} {NAMES[k]}' for a, b, k in blocks[:4])})" if blocks else "")
                + f"; circuit {s['circuit']:.0%} closed, {s['open_terminals']} open terminals; {s['openings_ahead']} openings ahead, {s['openings_side']} to the side"
                + f"; {s['fallen']} pins fallen inside the walls, {s['wall_pieces']} wall pieces connected; magnets pull {s['pulled_weakly']} more borders weakly"
                + (f"; {s['prior_rules']} rules carried in" if s['prior_rules'] else "")
                + (f"; merged: far colour {', '.join(s['merged'])} blocks from any near colour" if s['merged'] else "")
                + (f"; corrected by the game: {', '.join(s['corrected'])}" if s['corrected'] else ""))

    def save(self, path):
        np.savez_compressed(path, mid=self.mid, border=self.border, pred=self.pred, brushed=self.brushed,
                            dragged=getattr(self, "dragged", np.zeros_like(self.border, dtype=bool)),
                            fallen=getattr(self, "fallen", np.zeros(self.shape, bool)), pull=self.pull)
        json.dump({"rules": {f"{k[0]},{k[1]},{k[2]}": v for k, v in self.rule.items()}, "stats": self.stats()}, open(path + ".json", "w"), indent=1)

    def rules_merged(self):
        """this level's rules over the carried ones: what persists to the next level and the next run"""
        out = {k: list(v) for k, v in self.prior.items()}
        for k, v in self.rule.items():
            r = out.setdefault(k, [0, 0]); r[0] += v[0]; r[1] += v[1]
        return out


def save_rules(path, rules):
    json.dump({f"{k[0]},{k[1]},{k[2]}": v for k, v in rules.items()}, open(path, "w"), indent=1)


def load_rules(path):
    import os
    if not os.path.exists(path): return {}
    out = {}
    for k, v in json.load(open(path)).items():
        a, b, c = (int(t) for t in k.split(",")); out[(a, b, c)] = [int(v[0]), int(v[1])]
    return out


def ground_of(start, S, fill):
    """the level's ground: the start frame with the body painted the floor colour it walks on"""
    g = start.copy()
    if S is not None and fill is not None: g[S] = fill
    return g
