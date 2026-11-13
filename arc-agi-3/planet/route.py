#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
route.py — THE ROUTE WITH REFILL POINTS: every ring is a goal, and the order of the goals is what the bar allows.

Jonathan (Sep 6): "there are 2 refill points in that game. It's not the route, it's recognizing a 2nd point is
the same and adding another goal." Sixteen runs of ls20 level 2 chose the rings one at a time as detours and were
one or two moves short every life. Here the whole life is planned as a sequence of stops: the walk to the source,
its touches, the target — and each standing ring inserted wherever it makes the budget close.

    plan(...) -> (stops, total_moves) or None
      stops: [("ring", ring), ("touch", i), ("ring", ring), ("box", target)]

Costs are the planner's own paths on imagined frames (the operators walked forward), so the walk from a ring to
the source is measured on the frame the body would see there. A touch from adjacency costs one move; a second
touch from the source itself costs two (out and in again); a refused press costs nothing (measured on ls20).
A ring refills the bar to full on the move that lands on it, so that leg may spend the whole bar.
"""
from __future__ import annotations
import hashlib
import itertools
import numpy as np

def _walk(ops, f, path):
    q = f
    for a in path:
        r = ops.predict(q, a)
        if r is None: break
        q = r
    return q


def plan(ops, f, vkey, body_of, contact_tests, plan_to, rings, touch_cells, touches, box_cells, bar, bar_full, margin=1, log=None):
    """rings: [{"id", "cells"}] standing; touch_cells: the source; touches: touches still needed; box_cells: the
    target (None if not matched yet — then the box leg is the far ring's worth of slack, not a stop); bar: moves
    left now; bar_full: moves in a full bar. Returns the cheapest feasible (stops, total) or None."""
    # Memoize only within this planning call. Operators and fence rules may
    # change between calls even when the frame/cells are identical.
    cache = {}
    legs_seen = []; lifted = []

    def leg(frame, cells, kind):
        """moves from `frame` to a step that lands on `cells` (adjacency), and the frame there"""
        k = (vkey(frame), hashlib.md5(cells.tobytes()).hexdigest()[:10], kind)
        if k in cache: return cache[k]
        adj, _ = contact_tests(ops, cells)
        if kind == "enter":
            goal = lambda q, c_=cells: (lambda b_: b_ is not None and (b_ & c_).any())(body_of(ops, q))
        else:
            goal = adj
        p = plan_to(ops, frame, goal, vkey, depth=40, max_states=3000)     # the live state space is wider than the offline one: the planner's own limits
        res = None if p is None else (len(p), _walk(ops, frame, p))
        if res is not None: cache[k] = res                            # a failure is not remembered: the operators may be stronger next time
        return res

    def bump_frame(frame, cells):
        """the frame after the body steps ONTO the cells from adjacency (the touch itself)"""
        b = body_of(ops, frame)
        if b is None: return frame
        for a_, op_ in ops.ops.items():
            if hasattr(op_, "d") and op_.d is not None and hasattr(op_, "locate"):
                dy, dx = op_.d
                H, W = b.shape; moved = np.zeros_like(b)
                ys, xs = np.where(b); ys2, xs2 = ys + dy, xs + dx
                ok = (ys2 >= 0) & (ys2 < H) & (xs2 >= 0) & (xs2 < W); moved[ys2[ok], xs2[ok]] = True
                if (moved & cells).any():
                    q = ops.predict(frame, a_)
                    if q is not None and not np.array_equal(q, frame): return q
        return frame

    best = None
    slots = list(range(0, touches + 1))
    ring_lists = [[]]
    for r in range(1, len(rings) + 1):
        for combo in itertools.permutations(rings, r):
            for pos in itertools.product(slots, repeat=r):
                if list(pos) != sorted(pos): continue
                ring_lists.append(list(zip(combo, pos)))
    for placement in ring_lists:
        at = {}
        for ring, pos in placement: at.setdefault(pos, []).append(ring)
        frame = f; left = float(bar); total = 0; stops = []; ok = True; on_source = False; legs_ = []
        def take_rings(pos):
            nonlocal frame, left, total, ok, on_source
            for ring in at.get(pos, []):
                l = leg(frame, ring["cells"], "enter")            # PRICED FROM WHERE THE BODY STANDS (Jonathan, Sep 6): on the source after a touch
                if l is None or l[0] > left: ok = False; return
                total += l[0]; frame = l[1]; left = float(bar_full); on_source = False
                stops.append(("ring", ring)); legs_.append(f"ring {ring['id']} {l[0]}")
        take_rings(0)
        if not ok: continue
        if touches > 0:
            l = leg(frame, touch_cells, "adjacent")
            if l is None or l[0] > left - margin: continue
            total += l[0]; left -= l[0]; frame = l[1]; legs_.append(f"walk {l[0]}")
            for i in range(1, touches + 1):
                cost = 2 if on_source else 1
                if cost > left - margin: ok = False; break
                total += cost; left -= cost; legs_.append(f"touch {cost}")
                if not on_source: frame = bump_frame(frame, touch_cells)     # the body is ON the source now
                on_source = True; stops.append(("touch", i))
                take_rings(i)
                if not ok: break
                if at.get(i) and i < touches:
                    l = leg(frame, touch_cells, "adjacent")            # back from the ring to the source's side
                    if l is None or l[0] > left - margin: ok = False; break
                    total += l[0]; left -= l[0]; frame = l[1]; on_source = False; legs_.append(f"back {l[0]}")
        if not ok: continue
        if box_cells is not None:
            l = leg(frame, box_cells, "adjacent")
            if l is None or l[0] + 1 > left - margin: continue
            total += l[0] + 1; left -= l[0] + 1; stops.append(("box", None)); legs_.append(f"box {l[0] + 1}")
        if best is None or total < best[1]: best = (stops, total, left, legs_)
    if log and best is None:
        base = [f"walk {(lambda l: 'none' if l is None else l[0])(leg(f, touch_cells, 'adjacent'))}"] if touches > 0 else []
        base += [f"ring {r_['id']} {(lambda l: 'none' if l is None else l[0])(leg(f, r_['cells'], 'enter'))}" for r_ in rings]
        if box_cells is not None: base.append(f"box {(lambda l: 'none' if l is None else l[0])(leg(f, box_cells, 'adjacent'))}")
        log(f"  route: no order closes from here (bar {bar:.0f}, full {bar_full:.0f}, {touches} touches); legs from here: " + ", ".join(base) + (f"; {len(lifted)} legs only the fence forbade" if lifted else ""))
    if log and best: log("  route: " + " -> ".join(s[0] + ("" if s[1] is None or s[0] == "touch" else " " + s[1]["id"]) + (str(s[1]) if s[0] == "touch" else "") for s in best[0]) + f" ({best[1]} moves, {best[2]:.0f} left; legs " + ", ".join(best[3]) + (f"; {len(lifted)} legs priced with the fence lifted" if lifted else "") + ")")
    return best[:3] if best else None
