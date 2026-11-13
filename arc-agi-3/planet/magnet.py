#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
magnet.py — THE CENTRE MAGNET: the hidden response of every thing, rebuilt from the pins that broke into it.

Jonathan (Sep 6): "the centre of that pixel wants a pin where the void line is; that centre has some magnet that is
supposed to be there but we don't know what it is and we have to recreate it from these pins. A goal we don't
have the key for needs a complex magnet, walls respond the same way to everything; the walls are the first thing
we meet, so at the start the goal is empty while the walls have pins already. When pins bounce off the inside of
the pixel they give hints: partially aligned means it shares some properties but is missing something else."

    Magnets.build(pairs, things, body_of, ops, band)   -> per thing: the response table
        table[thing][(control, side)] = {"pass": n, "refuse": n, "state": n, "level": n}
        closure[thing]   how much of (controls x sides) has an answer            walls close with a few pins
        contradiction[thing] = [(control, side, counts)]                          a goal without its key contradicts itself
    Magnets.key(thing, control, side, pairs)            -> the separating feature of a contradiction:
        the region of the frame whose pattern is constant in the passes and different in every refusal — the
        missing property the bounced pin points at (ls20: the HUD region from the box's door alone)
"""
from __future__ import annotations
import hashlib
import numpy as np
from scipy import ndimage

SIDES = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}


def _unit(d):
    dy, dx = int(np.sign(d[0])), int(np.sign(d[1]))
    return (dy, dx)


def _shift(m, dy, dx):
    H, W = m.shape; out = np.zeros_like(m)
    ys, xs = np.where(m); ys2, xs2 = ys + dy, xs + dx
    ok = (ys2 >= 0) & (ys2 < H) & (xs2 >= 0) & (xs2 < W); out[ys2[ok], xs2[ok]] = True
    return out


class Magnets:
    def __init__(self):
        self.table: dict = {}        # thing id -> {(control, side): {"pass","refuse","state","level"}}
        self.presses: dict = {}      # thing id -> {(control, side): {"pass": [press idx], "refuse": [...]}}
        self.things: dict = {}       # thing id -> cells
        self.controls: set = set()
        self.body_pos: dict = {}     # press index -> (y, x) of the body's top-left, for the search in body coordinates

    def build(self, pairs, things, body_of, ops, band=None, levels=None):
        """pairs: (f0, f1, a, x, y); things: [{"id", "cells"}]; the body's step ahead of each press names the things
        the pin went into, and what the game answered"""
        self.things = {t["id"]: t["cells"] for t in things}
        disp = {a: op for a, op in ops.ops.items() if hasattr(op, "d") and getattr(op, "d", None) is not None}
        for i, (f0, f1, a, x, y) in enumerate(pairs):
            op = disp.get(a)
            if op is None:
                if int(a) != 6: self._act(i, f0, f1, int(a), body_of, ops, band, levels)     # THE ACT BUTTON'S PINS
                continue
            self.controls.add(int(a))
            S0 = body_of(ops, f0); S1 = body_of(ops, f1)
            if S0 is None: continue
            self.body_pos[i] = tuple(int(v) for v in np.argwhere(S0).min(axis=0))
            dy, dx = op.d; q = max(abs(dy), abs(dx)); u = _unit(op.d)
            ahead = np.zeros_like(S0)
            for k in range(1, q + 1): ahead |= _shift(S0, u[0] * k, u[1] * k)
            ahead &= ~S0
            moved = S1 is not None and not np.array_equal(S0, S1)
            other = (f0 != f1)
            if band is not None: other &= ~band
            if S0 is not None: other &= ~S0
            if S1 is not None: other &= ~S1
            lvl_up = levels is not None and i + 1 < len(levels) and levels[i + 1] > levels[i]
            for tid, cells in self.things.items():
                if not (ahead & cells).any(): continue
                side = SIDES.get((-u[0], -u[1]), "?")                     # the side of the thing the body came from
                part = hashlib.md5((ahead & cells).tobytes()).hexdigest()[:6]   # WHICH PART of the thing the pin went into (a mouth is not its door)
                key = (int(a), side, part)
                row = self.table.setdefault(tid, {}).setdefault(key, {"pass": 0, "refuse": 0, "state": 0, "level": 0})
                rec = self.presses.setdefault(tid, {}).setdefault(key, {"pass": [], "refuse": [], "state": [], "level": []})
                if lvl_up: row["level"] += 1; rec["level"].append(i)
                elif moved and (S1 & cells).any(): row["pass"] += 1; rec["pass"].append(i)
                elif not moved and other.any(): row["state"] += 1; rec["state"].append(i)
                elif not moved: row["refuse"] += 1; rec["refuse"].append(i)
                # moved but not into it: the pin bent past (a ride, a slide) — no answer about this thing
        return self

    def _act(self, i, f0, f1, a, body_of, ops, band, levels):
        """THE ACT BUTTON (Jonathan, Sep 6): a button that moves nothing is a complex magnet from the start — we don't know
        what it does either. Its pin goes into every thing the body is lined up with (rows or columns overlapping) from
        the side the thing lies on, and into 'afar' when nothing is lined up; the answer is what changed: the thing
        itself ('hit'), something elsewhere ('state'), nothing ('refuse'), or the level."""
        self.controls.add(a)
        S0 = body_of(ops, f0)
        changed = (f0 != f1)
        if band is not None: changed &= ~band
        if S0 is not None: changed &= ~S0
        S1 = body_of(ops, f1)
        if S1 is not None: changed &= ~S1
        lvl_up = levels is not None and i + 1 < len(levels) and levels[i + 1] > levels[i]
        hit_any = False
        if S0 is not None:
            ys, xs = np.where(S0); by0, by1, bx0, bx1 = ys.min(), ys.max(), xs.min(), xs.max()
            self.body_pos[i] = (int(by0), int(bx0))
            cy, cx = ys.mean(), xs.mean()
            for tid, cells in self.things.items():
                tys, txs = np.where(cells)
                if len(tys) == 0: continue
                cols = not (txs.max() < bx0 or txs.min() > bx1); rows = not (tys.max() < by0 or tys.min() > by1)
                if not (cols or rows): continue
                if cols: side = "above" if tys.mean() < cy else "below"
                else: side = "left" if txs.mean() < cx else "right"
                span = (max(bx0, txs.min()), min(bx1, txs.max())) if cols else (max(by0, tys.min()), min(by1, tys.max()))
                key = (a, "lined up " + side, f"{span[0]}-{span[1]}")
                row = self.table.setdefault(tid, {}).setdefault(key, {"pass": 0, "refuse": 0, "state": 0, "level": 0})
                rec = self.presses.setdefault(tid, {}).setdefault(key, {"pass": [], "refuse": [], "state": [], "level": []})
                own_change = (f0 != f1) & cells
                if band is not None: own_change &= ~band
                if lvl_up: row["level"] += 1; rec["level"].append(i)
                elif own_change.any(): row["pass"] += 1; rec["pass"].append(i)               # the thing itself answered: the pin went in (even when the body is what it became — sp80's act hands control to the block)
                elif changed.any(): row["state"] += 1; rec["state"].append(i)
                else: row["refuse"] += 1; rec["refuse"].append(i)
                hit_any = True
        # the button's own magnet: what it does from wherever it was pressed (the body's own change counts here: a button
        # that turns the body into something else has acted)
        own = f"ACTION{a}"; self.things.setdefault(own, np.zeros_like(f0, bool))
        key = (a, "lined up" if hit_any else "afar", "-")
        row = self.table.setdefault(own, {}).setdefault(key, {"pass": 0, "refuse": 0, "state": 0, "level": 0})
        rec = self.presses.setdefault(own, {}).setdefault(key, {"pass": [], "refuse": [], "state": [], "level": []})
        any_change = (f0 != f1)
        if band is not None: any_change &= ~band
        if lvl_up: row["level"] += 1; rec["level"].append(i)
        elif any_change.any(): row["state"] += 1; rec["state"].append(i)
        else: row["refuse"] += 1; rec["refuse"].append(i)

    def closure(self, tid):
        rows = self.table.get(tid, {})
        if not self.controls: return 0.0
        return len(set((a, s) for (a, s, p) in rows)) / (len(self.controls) * 4)

    def kind(self, tid):
        """'wall': answers refuse and nothing else; 'door': the same pin passed and refused; 'open': passes only;
        'empty': nothing on it yet; 'state': its touches change something elsewhere; a button: 'complex' when its
        answer depends on where it was pressed, 'inert' when it never did anything, 'plain' when it always does the same"""
        rows = self.table.get(tid, {})
        if tid.startswith("ACTION"):
            if not rows: return "empty"
            answers = set(o for v in rows.values() for o in ("pass", "refuse", "state", "level") if v[o])
            if answers == {"refuse"}: return "inert"
            return "complex" if len(answers) >= 2 or len(rows) >= 2 else "plain"
        if not rows: return "empty"
        if any(v["level"] for v in rows.values()): return "goal"
        if any(sum(1 for o in ("pass", "refuse", "state", "level") if v[o]) >= 2 for v in rows.values()): return "door"   # the same pin, two answers
        if any(v["state"] for v in rows.values()): return "state"
        if all(v["refuse"] and not v["pass"] for v in rows.values()): return "wall"
        if all(v["pass"] and not v["refuse"] for v in rows.values()): return "open"
        return "mixed"

    def expecting(self):
        """the things where something complex is expected — a door, or nothing on it yet — where a complex button
        should be tried first, doors before empties"""
        order = {"door": 0, "empty": 1, "state": 2, "goal": 3, "open": 4, "mixed": 5, "wall": 6}
        return sorted((t for t in self.things if not t.startswith("ACTION")), key=lambda t: order.get(self.kind(t), 9))

    def contradictions(self):
        out = []
        for tid, rows in self.table.items():
            for (a, side, part), v in rows.items():
                if sum(1 for o in ("pass", "refuse", "state", "level") if v[o]) >= 2: out.append((tid, a, side, dict(v), part))
        return out

    def key(self, tid, a, side, pairs, exclude=None, min_cells=4, part=None, body=None):
        """THE MISSING PROPERTY: cells constant across the passes and different from that value in every refusal,
        away from the body, the band and the thing itself; returned as the largest such region with its pattern"""
        recs = self.presses.get(tid, {})
        rec = recs.get((a, side, part)) if part is not None else next((v for (aa, ss, pp), v in recs.items() if aa == a and ss == side and sum(1 for o in v if v[o]) >= 2), None)
        if not rec: return None
        # the open answer is the rarer, higher one (level > state > pass); the other answers are the closed ones
        order = [o for o in ("level", "state", "pass", "refuse") if rec[o]]
        if len(order) < 2: return None
        open_, closed_ = order[0], [i for o in order[1:] for i in rec[o]]
        opens_i, closes_i = rec[open_], closed_
        found = self._search([pairs[i][0] for i in opens_i], [pairs[i][0] for i in closes_i], tid, exclude, body, min_cells)
        if found is not None:
            box, best, pat = found
            return {"frame": "screen", "box": box, "cells": int(best.sum()), "pattern_when_open": pat.tolist(), "open": open_, "opens": len(opens_i), "closed": len(closes_i),
                    "shared": "the same colours from the same side", "missing": f"a region of {int(best.sum())} cells at rows {box[0]}-{box[1]} cols {box[2]}-{box[3]} that reads one way when the pin passes and another when it bounces"}
        # THE SEARCH IN BODY COORDINATES (Jonathan, Sep 6): a diagonal pin whose foot slides with the body — every frame is
        # shifted so the body sits at the origin, and the same test runs; the region comes back as an offset from the body
        if all(i in self.body_pos for i in opens_i + closes_i):
            H, W = pairs[0][0].shape
            def canvas(i):
                f = pairs[i][0]; y0, x0 = self.body_pos[i]; c = np.full((2 * H, 2 * W), -1, f.dtype)
                c[H - y0:H - y0 + H, W - x0:W - x0 + W] = f; return c
            # ONE OPEN AT A TIME (Sep 6): sp80's act swaps with a block below on one press and above on the next; no single
            # offset is constant across the opens, but each open alone names its region, and when the regions agree in
            # colour the key is that colour adjacent on any of the sides seen
            per = []
            for i in opens_i:
                f_ = self._search([canvas(i)], [canvas(j) for j in closes_i], None, None, None, min_cells)
                if f_ is None: continue
                box, best, pat = f_; rel = (box[0] - H, box[1] - H, box[2] - W, box[3] - W)
                vals = pat[pat >= 0]; col = int(np.bincount(vals).argmax()) if vals.size else -1
                per.append((rel, col, int(best.sum())))
            if per and len(opens_i) >= 2:
                cols = [c for _, c, _ in per]; col = max(set(cols), key=cols.count)
                sides = sorted(set(("below" if r[0] > 0 else "above" if r[1] < 0 else "beside") for r, c, _ in per if c == col))
                agree = sum(1 for c in cols if c == col)
                if agree == len(opens_i): return {"frame": "body", "box": per[0][0], "cells": per[0][2], "pattern_when_open": [[col]], "open": open_, "opens": len(opens_i), "closed": len(closes_i),
                        "sides": sides, "colour": col, "agree": agree, "shared": "the same colours from the same side",
                        "missing": f"a thing of colour {col} touching the body {' or '.join(sides)} ({agree} of {len(opens_i)} opens agree) — that is there when the pin passes and not when it bounces"}
            found = self._search([canvas(i) for i in opens_i], [canvas(i) for i in closes_i], None, None, None, min_cells)
            if found is not None:
                box, best, pat = found
                rel = (box[0] - H, box[1] - H, box[2] - W, box[3] - W)
                where = ("below" if rel[0] > 0 else "above" if rel[1] < 0 else "beside")
                return {"frame": "body", "box": rel, "cells": int(best.sum()), "pattern_when_open": pat.tolist(), "open": open_, "opens": len(opens_i), "closed": len(closes_i),
                        "shared": "the same colours from the same side",
                        "missing": f"a region of {int(best.sum())} cells {where} the body — rows {rel[0]:+d}..{rel[1]:+d}, cols {rel[2]:+d}..{rel[3]:+d} from the body's corner — that reads one way when the pin passes and another when it bounces"}
        return None

    def _search(self, opens, closes, tid, exclude, body, min_cells):
        P = np.stack(opens); R = np.stack(closes)
        const = (P == P[0]).all(axis=0)
        differs = (R != P[0]).all(axis=0)
        m = const & differs & (P[0] >= 0)
        if exclude is not None: m &= ~exclude
        if body is not None and tid is not None and not tid.startswith("ACTION"): m &= ~body     # a thing's key is not the body's own place; a button's may be exactly that
        if tid is not None: m &= ~self.things[tid]
        if not m.any(): return None
        lab, n = ndimage.label(m)
        valid = P[0] >= 0
        bgc = int(np.bincount(P[0][valid].ravel()).argmax())                      # the ground: the commonest colour in the open frames
        origin = (P[0].shape[0] // 2, P[0].shape[1] // 2) if tid is None else None   # body coordinates: the body sits at the centre
        best = None; best_key = None
        for i in range(1, n + 1):
            c = lab == i
            if c.sum() < min_cells: continue
            content = bool((P[0][c] != bgc).any())                                # a key is a thing, not a patch of empty floor
            ys, xs = np.where(c)
            dist = 0.0 if origin is None else float(min(abs(ys - origin[0]).min(), abs(xs - origin[1]).min()) + abs((ys.mean() - origin[0])) / 100)
            key = (0 if content else 1, dist, -int(c.sum()))
            if best is None or key < best_key: best, best_key = c, key
        if best is None: return None
        ys, xs = np.where(best)
        box = (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))
        return box, best, P[0][box[0]:box[1] + 1, box[2]:box[3] + 1]

    def summary(self, pairs=None, exclude=None, body=None):
        kinds = {}
        for tid in self.things: kinds.setdefault(self.kind(tid), []).append(tid)
        parts = [f"{k}: {len(v)}" for k, v in sorted(kinds.items())]
        line = "magnets: " + ", ".join(parts)
        cons = self.contradictions()
        if cons:
            bits = []
            for tid, a, side, v, part in cons[:3]:
                kk = self.key(tid, a, side, pairs, exclude, part=part, body=body) if pairs is not None else None
                ans = "/".join(f"{v[o]} {o}" for o in ("level", "state", "pass", "refuse") if v[o])
                bits.append(f"{tid} from {side} by ACTION{a} ({ans})" + ((f" -> the {kk['open']} needs " + (f"rows {kk['box'][0]}-{kk['box'][1]} cols {kk['box'][2]}-{kk['box'][3]} to read one way" if kk["frame"] == "screen" else (f"a thing of colour {kk['colour']} touching the body {' or '.join(kk['sides'])}" if kk.get("sides") else f"the cells rows {kk['box'][0]:+d}..{kk['box'][1]:+d} cols {kk['box'][2]:+d}..{kk['box'][3]:+d} from the body to read one way"))) if kk else " -> no separating region"))
            line += " | contradictions: " + "; ".join(bits)
        return line

    def stats(self, pairs=None, exclude=None, body=None):
        return {"things": len(self.things), "kinds": {tid: self.kind(tid) for tid in self.things},
                "closure": {tid: round(self.closure(tid), 2) for tid in self.things},
                "contradictions": [{"thing": tid, "control": a, "side": side, **v, "key": (self.key(tid, a, side, pairs, exclude, part=part, body=body) if pairs is not None else None)}
                                   for tid, a, side, v, part in self.contradictions()]}
