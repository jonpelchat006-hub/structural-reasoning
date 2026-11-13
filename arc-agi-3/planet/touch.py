#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
touch.py — THE TOUCH GRAPH: body, objects, and what happens when they meet.

Jonathan (Sep 3): the body is the object connected to the controls; a goal has something pointing at it that
is not just a wall pointing at a wall; nothing may be called useless for good.

  BODY     the object with the most control bonds, weighted by bond (induce.Operators): the colours the gated
           displace operators move. tr87-style chains (a selector that chooses what up/down act on) show up as
           a second body colour set from the cycle operators' anchor.
  OBJECTS  connected components of the non-floor colours in the level's first frame, minus the body and the
           register (floor = any colour covering > 900 cells).
  EDGES    one per press, from the button through the body to the object it met, typed by what happened:
             refusal  the body did not move and its destination overlapped the object      (a wall, for now)
             pass     the body moved onto/over the object and nothing else changed          (floor-like)
             state    something persistent changed elsewhere (a ring vanished, the key recoloured, the bar jumped)
             level    the level counter rose
           A button with no body operator (ACTION5, clicks) points at the objects next to the body (or under the click).
  LABELS   per object, a bond per type (start 0.1; +35% of the gap on that type; x0.6 on any other type), so a
           "wall" stays a wall only while refusals keep coming; one state edge breaks it.

Check 1: does the body rank pick the right thing across the games with gated operators?
Check 2: in sp80 and ls20, do the objects that mattered end up with a state/level edge while walls have only refusals?

Usage:  python touch.py sp80              (collect recording)
        python touch.py sp80 --play       (the last play.py run, which has the planner's presses)
        python touch.py --all             (check 1 over every game)
"""
from __future__ import annotations
import argparse, glob, json, os, sys
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import induce

OUT = r"D:\planet\eye"
EFFECTS = ("refusal", "pass", "state", "level", "nothing")


def load_collect(game):
    z = np.load(os.path.join(OUT, f"{game}.npz")); F = z["F"].astype(np.int16); A, X, Y, L = z["A"], z["X"], z["Y"], z["L"]
    pairs = []
    for i in range(len(A)):
        if A[i] == 0: continue
        pairs.append((F[i], F[i + 1], int(A[i]), int(X[i]), int(Y[i]), int(L[i])))
    return pairs


def load_play(game):
    """the last play.py run: frames from play_<game>.npz, presses from play_<game>.jsonl, one extra frame after each GAME_OVER"""
    F = np.load(os.path.join(OUT, f"play_{game}.npz"))["F"].astype(np.int16)
    rec = [json.loads(l) for l in open(os.path.join(OUT, f"play_{game}.jsonl"), encoding="utf-8")]
    pairs = []; fi = 0
    for r in rec:
        if fi + 1 >= len(F): break
        if int(r["a"]) == 0: fi += 1; continue                        # a voluntary reset: one frame, no press
        pairs.append((F[fi], F[fi + 1], int(r["a"]), int(r["x"]), int(r["y"]), int(r["levels"]))); fi += 1
        if r["state"] == "GAME_OVER": fi += 1
    return pairs


def body_rank(pairs, ops=None):
    """the body: colours the gated displace operators move, ranked by (buttons, bond sum); cycle anchors as a chain"""
    if ops is None: ops = induce.Operators().fit([p[:5] for p in pairs], recent=[p[:5] for p in pairs])
    score: dict = {}; chain = set(); shifts = {}
    for a, op in ops.ops.items():
        b = ops.bond.get(a, 0)
        if isinstance(op, induce.Displace):
            for c in op.colors:
                s = score.setdefault(c, [0, 0.0]); s[0] += 1; s[1] += b
            shifts[a] = op.d
        elif isinstance(op, induce.Cycle) and op.anchor is not None:
            chain.add(op.anchor)
    if not score:                                    # no gated displace: rank colours by how many buttons ever shifted them
        acts: dict = {}
        for f0, f1, a, x, y, lv in pairs:
            r = induce.explain_shift(f0, f1, ops.mask if ops.mask is not None else np.ones_like(f0, bool), induce.background(f0))
            if r is None: continue
            core = r[1] & (f0 != r[2]) & (f0 != induce.background(f0))
            for c in set(int(v) for v in f0[core]):
                acts.setdefault(c, set()).add(a)
                s = score.setdefault(c, [0, 0.0]); s[1] += 0.05; s[0] = len(acts[c])
    ranked = sorted(score.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
    return ops, ranked, chain, shifts


def objects_of(f, floor, body_colors, amb):
    out = []
    for c in sorted(set(int(v) for v in np.unique(f)) - floor - set(body_colors)):
        lab, n = ndimage.label((f == c) & ~amb)
        for i in range(1, n + 1):
            m = lab == i
            if m.sum() < 2: continue
            ys, xs = np.where(m)
            out.append({"id": f"{c}@{ys.min()},{xs.min()}", "colour": c, "cells": m, "n": int(m.sum()), "at": (int(ys.mean()), int(xs.mean()))})
    return out


def locate_body(f, body_colors, op=None):
    """the body: the operator's own size-matched locator when there is one (tr87's two brackets by count, ls20's
    key by the piece nearest its size — the HUD draws a copy of the key in the key's colours); else all cells"""
    if op is not None:
        S = op.locate(f)
        if S is not None: return S
    m = np.isin(f, sorted(body_colors))
    return m if m.any() else None


def aligned(b0, objs):
    """objects the body points at: inside its row AND column band first (the tile under the selector), else either"""
    both = [o for o in objs if all(span_overlap(b0, o["cells"]))]
    return both or [o for o in objs if any(span_overlap(b0, o["cells"]))]


def span_overlap(a, b):
    """do two cell masks share rows or columns? (the bar under the token; the selector over a tile)"""
    ay, ax = np.where(a); by, bx = np.where(b)
    rows = not (ay.max() < by.min() or by.max() < ay.min()); cols = not (ax.max() < bx.min() or bx.max() < ax.min())
    return rows, cols


def candidates(g, exclude=()):
    """THE GOAL QUESTION as a list: objects with a state or level edge first (level, then state count), then the
    things never touched (smallest first — a key, a ring, a token), never walls, bounds, the register, or the body."""
    counts: dict = {}
    for e in g["edges"]: counts.setdefault(e["object"], {}).setdefault(e["effect"], 0); counts[e["object"]][e["effect"]] += 1
    objs = {o["id"]: o for o in g["objects"] if not o["id"].startswith(("chg", "place", "wall")) and o["id"] != "bound"}
    pointed = sorted(((c.get("level", 0), c.get("state", 0), oid) for oid, c in counts.items()
                      if oid in objs and (c.get("level", 0) or c.get("state", 0))), reverse=True)
    untouched = sorted(((o["n"], oid) for oid, o in objs.items() if oid not in counts and o["n"] <= 200))
    out = [objs[oid] for _, _, oid in pointed] + [objs[oid] for _, oid in untouched]
    return [o for o in out if o["id"] not in exclude]


def build(pairs, log=print, ops=None, key_fn=None):
    """key_fn(frame) -> a place key; when given, every edge carries the place it happened at (for the pins:
    'nothing' is only ever 'nothing here')"""
    if ops is None: induce._explain_cache.clear(); induce.START.clear()   # ids are reused across games in one process
    ops, ranked, chain, shifts = body_rank(pairs, ops)
    if not ranked: return None
    if ranked[0][1][0] < 2 and ranked[0][1][1] < 0.5: return None      # one weak button is a coincidence, not a body
    body_colors = set(c for c, s in ranked if s[0] >= max(2, ranked[0][1][0] - 1)) or {ranked[0][0]}
    pairs = [p if len(p) == 6 else (*p[:5], 0) for p in pairs]
    amb = ops.amb if ops.amb is not None else np.zeros_like(pairs[0][0], bool); mask = ~amb
    f_start = pairs[0][0]
    vals, counts = np.unique(f_start, return_counts=True); floor = set(int(v) for v, c in zip(vals, counts) if c > 900)
    objs = objects_of(f_start, floor, body_colors | chain, amb)
    edges = []; bonds = {o["id"]: {e: 0.1 for e in EFFECTS} for o in objs}
    def bump(oid, eff):
        b = bonds.setdefault(oid, {e: 0.1 for e in EFFECTS})
        for e in EFFECTS: b[e] = b[e] + (1 - b[e]) * 0.35 if e == eff else b[e] * 0.6
    prev_lv = pairs[0][5]
    disp = next((op for op in ops.ops.values() if isinstance(op, induce.Displace)), None)
    floor_of = disp.floor if disp is not None else set()
    for press_i, (f0, f1, a, x, y, lv) in enumerate(pairs):
        D = (f0 != f1) & mask
        b0 = locate_body(f0, body_colors, disp); b1 = locate_body(f1, body_colors, disp)
        moved = b0 is not None and b1 is not None and not np.array_equal(b0, b1)
        others = D.copy()
        if b0 is not None: others &= ~b0
        if b1 is not None: others &= ~b1
        d = shifts.get(a)
        if b0 is not None and d is not None: dest = induce.shifted(b0, *d, fill=False) & ~b0
        elif moved: dest = b1 & ~b0
        else: dest = None
        if lv > prev_lv: eff = "level"; dest = None      # the screen redraws on a level: the press points along the body's lines, not at "where the body went"
        elif others.any(): eff = "state"
        elif dest is not None and not moved and d is not None: eff = "refusal"
        elif moved: eff = "pass"
        else: eff = "nothing"
        prev_lv = lv
        if a == 6 and 0 <= x < 64 and 0 <= y < 64:
            touch = [o for o in objs if o["cells"][y, x]]
        elif dest is not None and dest.any():
            touch = [o for o in objs if (o["cells"] & dest).any()]
            if eff == "refusal":                     # the wall is whatever in the way is not floor to this body
                touch = [o for o in touch if o["colour"] not in floor_of]
                if not touch:
                    cols = set(int(v) for v in f0[dest]) - floor_of
                    for c in sorted(cols):           # a floor-class colour that blocks (ls20's yellow) is a wall node
                        oid = f"wall:{c}"
                        if oid not in bonds: objs.append({"id": oid, "colour": c, "cells": (f0 == c), "n": int((f0 == c).sum()), "at": (0, 0)})
                        touch.append(next(o for o in objs if o["id"] == oid))
        elif b0 is not None:
            near = ndimage.binary_dilation(b0, iterations=1) & ~b0
            touch = [o for o in objs if (o["cells"] & near).any()]
            if not touch: touch = aligned(b0, objs)   # a button pressed with nothing adjacent points along the body's lines
            if not touch and eff == "level":         # a level with nothing in reach: the place itself is the target
                ys, xs = np.where(b0); oid = f"place@{ys.min()},{xs.min()}"
                if oid not in bonds: objs.append({"id": oid, "colour": -1, "cells": b0.copy(), "n": int(b0.sum()), "at": (int(ys.mean()), int(xs.mean()))})
                touch = [next(o for o in objs if o["id"] == oid)]
        else: touch = []
        # a state change with nothing touched: the thing that changed is the target (the HUD glyph, the register jump).
        # A level change redraws the screen, so only aligned/adjacent objects are credited, never "what changed".
        if eff == "state" and not touch:
            lab, n = ndimage.label(others)
            for i in range(1, n + 1):
                m = lab == i; ys, xs = np.where(m)
                oid = f"chg{int(f0[m][0])}@{ys.min()},{xs.min()}"
                if oid not in bonds: objs.append({"id": oid, "colour": int(f0[m][0]), "cells": m, "n": int(m.sum()), "at": (int(ys.mean()), int(xs.mean()))})
                touch.append(next(o for o in objs if o["id"] == oid))
        place = key_fn(f0) if key_fn is not None else None
        for o in touch:
            edges.append({"button": a, "object": o["id"], "effect": eff, "place": place, "press": press_i}); bump(o["id"], eff)
        if not touch and eff == "refusal":           # refused by nothing visible: the arena bound
            edges.append({"button": a, "object": "bound", "effect": "refusal", "place": place, "press": press_i}); bump("bound", "refusal")
    return {"ops": ops, "ranked": ranked, "chain": chain, "body": body_colors, "objects": objs, "edges": edges, "bonds": bonds, "floor": floor}


def label(b):
    e = max(b, key=b.get); return e if b[e] >= 0.3 else "unknown"


def report(game, src, g, log=print):
    ops = g["ops"]
    log(f"=== {game} ({src}): {len(g['edges'])} edges")
    log(f"  body rank: " + "  ".join(f"colour {c}: {s[0]} buttons, bond sum {s[1]:.2f}" for c, s in g["ranked"][:4]) + (f"  | chain via {sorted(g['chain'])}" if g["chain"] else ""))
    log(f"  body = colours {sorted(g['body'])}; operators {ops.summary()}")
    counts: dict = {}
    for e in g["edges"]: counts.setdefault(e["object"], {}).setdefault(e["effect"], 0); counts[e["object"]][e["effect"]] += 1
    rows = []
    for oid, b in g["bonds"].items():
        c = counts.get(oid, {}); tot = sum(c.values())
        if tot == 0: continue
        rows.append((label(b), -tot, oid, c, b))
    order = {"level": 0, "state": 1, "pass": 2, "refusal": 3, "nothing": 4, "unknown": 5}
    rows.sort(key=lambda r: (order[r[0]], r[1]))
    log(f"  {'object':16s} {'label':8s} {'edges: refusal pass state level nothing':44s} bonds")
    for lab, negtot, oid, c, b in rows[:24]:
        log(f"  {oid:16s} {lab:8s} {c.get('refusal',0):8d} {c.get('pass',0):5d} {c.get('state',0):6d} {c.get('level',0):6d} {c.get('nothing',0):8d}      "
            + " ".join(f"{e[:3]} {b[e]:.2f}" for e in EFFECTS if b[e] >= 0.3))
    # THE GOAL QUESTION is existence, not majority: a wall only ever has refusals pointing at it; anything with a
    # state or level edge has been pointed at by something that was not a wall. Rank those, level first.
    cands = sorted(((c.get("level", 0), c.get("state", 0), oid) for oid, c in counts.items()
                    if (c.get("level", 0) or c.get("state", 0)) and not oid.startswith("chg")), reverse=True)
    walls = [oid for oid, c in counts.items() if c.get("refusal", 0) and not (c.get("level", 0) or c.get("state", 0) or c.get("pass", 0))]
    log("  goal candidates (level, state edges): " + (", ".join(f"{oid} ({l},{s})" for l, s, oid in cands[:8]) if cands else "none"))
    log("  walls (refusals only): " + (", ".join(walls) if walls else "none"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game", nargs="?"); ap.add_argument("--play", action="store_true"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        print(f"{'game':6s} {'body colours':14s} {'buttons/bonds':40s} chain")
        for p in sorted(glob.glob(os.path.join(OUT, "*.npz"))):
            game = os.path.basename(p)[:-4]
            if game.startswith("play_"): continue
            try: pairs = load_collect(game)
            except Exception as e: print(game, "error", e); continue
            if len(pairs) < 20: continue
            g = build(pairs)
            if g is None: print(f"{game:6s} {'-':14s} no operator moves anything"); continue
            print(f"{game:6s} {str(sorted(g['body'])):14s} {'  '.join(f'{c}:{s[0]}b/{s[1]:.1f}' for c, s in g['ranked'][:3]):40s} {sorted(g['chain']) if g['chain'] else ''}")
        return
    game = a.game or "sp80"
    pairs = load_play(game) if a.play else load_collect(game)
    g = build(pairs)
    if g is None: print("no body found"); return
    report(game, "play" if a.play else "collect", g)


if __name__ == "__main__":
    main()
