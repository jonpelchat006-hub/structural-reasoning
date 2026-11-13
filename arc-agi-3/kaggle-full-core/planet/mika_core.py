#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mika_core.py - HER INNER CORE BUILDS EQUATIONS; THE NOTES ARE THE OUTER SHELL (Oct 27 2026).

Jonathan, Oct 27:
  "towards our center we should be seeing equations and formulas that get pieced together for the answers. so its like
   one of our nodes can supply variables like x and y, then another supplies z, and another can do exponents, and the
   nodes that get activated build equations for the problem."
  "the notes are the outer shell products ... the llm layer takes that image or scene she sees and translates down to a
   note that would float around the outer shell. and then the notes in the outer shell would be what float into her
   perspective and can light up the paths she sees"
  "if she finds a note and its green, and it says this worked and this didnt, instead of just trying what the note says
   she should try to figure out what was missing from it"

What runs here, in her terms:

  NODES (pieces)   the KEY node reads the variable the level is about: the glyph in the HUD region her relation memory
                   names (a colour and a shape). The TARGET node reads the glyph inside a box on the board. Every thing
                   whose touch changed the key is an OPERATOR node: R (turns the shape a quarter, clockwise, k times),
                   C (recolours a -> b), F (mirrors). A thing touched n times is that operator to the power n.
  THE EQUATION     the nodes that light up on a level assemble   op1^n1 . op2^n2 ... (key) = target   and she solves it for
                   the powers (a small search over her known operators: the shortest product that reaches the target).
  THE PLAN         the solution, ordered so the body's own skills finish it: the recolour first, then the body's relation
                   loop (touch the rotator until the shapes match, then walk into the box). She re-solves from the frame
                   on every decision, so a reset or a half-done plan needs no bookkeeping.
  NOTES            what she sends out to the outer shell: English text (a template now; the LLM's job later) PLUS the path
                   (the equation and its pieces) PLUS the seven colours it fills (pool.py's meanings) PLUS its pool: the
                   colours still missing. A note that floats back in lights its path directly; its missing colours are
                   what she explores before she trusts it (the note is not gospel).

  Operators are learned from her own presses: after every press (play.py -> mind.see) she compares the key glyph with
  the one before and gives the change to the thing being touched (the experiment's thing, the relation's source, or the
  thing the body is standing on). They are kept in her journal by the thing's COLOUR, as the body carries relations, so
  a rotator on level 1 is a rotator on level 3. At the start of a life she also reads her last life's saved frames.

Usage:  python mika_core.py ls20 --presses 400              (her core on; the shell off unless --shell is given)
        python mika_core.py --learn ls20                    (read the last saved life only, print what she learned)
        python mika_core.py --notes ls20                    (print her notes)
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
import numpy as np
import qtube_fit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import mika_mind as mm
import mika_think as mt

EYE = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"
CORE = os.path.join(mm.HOME, "core")
SEVEN = ["RED", "ORANGE", "YELLOW", "GREEN", "CYAN", "BLUE", "VIOLET"]     # pool.py's colours, in its order
MEANING = {"RED": "what blocks or failed", "ORANGE": "how many (the powers)", "YELLOW": "what each touch changes",
           "GREEN": "the variables (key and target)", "CYAN": "the equals (what must match what)",
           "BLUE": "the order", "VIOLET": "what she does not know yet"}
MAXDEPTH = 12                                       # states are deduped; level 5 needs 7 (S^2 R^2 C^3)


def _now(): return time.strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================================ pieces
def shrink(m):
    """crop to the mask, then undo a uniform 3x or 2x scale (relations.shrink, kept here so the core stands alone)"""
    m = np.asarray(m).astype(int)
    ys, xs = np.where(m)
    if not len(ys): return m
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    for s_ in (3, 2):
        if m.size and m.shape[0] % s_ == 0 and m.shape[1] % s_ == 0:
            t = m.reshape(m.shape[0] // s_, s_, m.shape[1] // s_, s_).mean(axis=(1, 3))
            if ((t == 0) | (t == 1)).all(): return t.astype(int)
    return m


def _ring_colour(f, y0, y1, x0, x1):
    """the background around a region: the most common colour on the one-cell ring outside it"""
    H, W = f.shape
    ring = []
    for x in range(max(0, x0 - 1), min(W, x1 + 2)):
        if y0 - 1 >= 0: ring.append(int(f[y0 - 1, x]))
        if y1 + 1 < H: ring.append(int(f[y1 + 1, x]))
    for y in range(max(0, y0 - 1), min(H, y1 + 2)):
        if x0 - 1 >= 0: ring.append(int(f[y, x0 - 1]))
        if x1 + 1 < W: ring.append(int(f[y, x1 + 1]))
    return int(np.bincount(ring).argmax()) if ring else None


def read_glyph(f, region):
    """KEY NODE: (colour, shape) of the one-colour glyph in the region (y0, y1, x0, x1), or None"""
    f = np.asarray(f)
    y0, y1, x0, x1 = [int(v) for v in region]
    inner = f[y0:y1 + 1, x0:x1 + 1]
    bg = _ring_colour(f, y0, y1, x0, x1)
    cols = [int(v) for v in np.unique(inner) if int(v) != bg]
    if len(cols) != 1: return None
    return (cols[0], shrink(inner == cols[0]))


def read_box_glyph(f, box, own_colour):
    """TARGET NODE: (colour, shape) of the glyph inside a box thing (box = [y0, x0, y1, x1] as her things keep it)"""
    f = np.asarray(f)
    y0, x0, y1, x1 = [int(v) for v in box]
    inner = f[y0:y1 + 1, x0:x1 + 1]
    cols = [int(v) for v in np.unique(inner) if int(v) != int(own_colour)]
    if len(cols) != 1: return None
    sh = shrink(inner == cols[0])
    if sh.size < 4 or sh.size == inner.size: return None
    return (cols[0], sh)


def same(a, b):
    return a is not None and b is not None and a[0] == b[0] and a[1].shape == b[1].shape and np.array_equal(a[1], b[1])


def shape_text(sh):
    return " / ".join("".join("#" if v else "." for v in row) for row in sh)


# ============================================================================================ operators
def state_text(g):
    return f"{int(g[0])}|{shape_text(g[1])}"


def shape_from(text):
    return np.array([[1 if ch == "#" else 0 for ch in row] for row in text.split(" / ")], int)


def parse_state(text):
    c, sh = text.split("|", 1)
    return (int(c), None if sh == "*" else shape_from(sh))


def _eq(a, b):
    return a is not None and b is not None and a.shape == b.shape and np.array_equal(a, b)


def transform(a, b):
    """what one touch did to the key, kept as the pair of states (a, b) in text; None when nothing changed"""
    if a is None or b is None or same(a, b): return None
    return (state_text(a), state_text(b))


def fit(trans):
    """THE NODE'S LAW, induced from every change it was seen to make: the simplest rule all of them obey.
    ('R', k) every change a k-quarter clockwise turn; ('F',) a mirror; ('C', {colour: colour}) recolours that keep the
    shape; ('S', {shape: shape}) shape changes that keep the colour (run 20, level 4: the colour-0 thing changes the
    key's SHAPE, where level 3's colour-0 thing turned it); ('M', {state: state}) anything else, as a map."""
    pairs = []
    for t in trans:
        if isinstance(t, dict) and t.get("op"): return tuple(t["op"]) if t["op"][0] != "C" else ("C", dict(t["op"][1]))
        a, b = parse_state(t[0]), parse_state(t[1]); pairs.append((a, b))
    if not pairs: return None
    for k in (1, 2, 3):
        if all(ca == cb and sa is not None and _eq(np.rot90(sa, -k), sb) for (ca, sa), (cb, sb) in pairs): return ("R", k)
    if all(ca == cb and sa is not None and _eq(np.fliplr(sa), sb) for (ca, sa), (cb, sb) in pairs): return ("F",)
    if all(ca != cb and (sa is None or sb is None or _eq(sa, sb)) for (ca, sa), (cb, sb) in pairs):
        return ("C", {str(ca): int(cb) for (ca, sa), (cb, sb) in pairs})
    if all(ca == cb and sa is not None and sb is not None for (ca, sa), (cb, sb) in pairs):
        return ("S", {shape_text(sa): shape_text(sb) for (ca, sa), (cb, sb) in pairs})
    return ("M", {f"{ca}|{shape_text(sa)}": f"{cb}|{shape_text(sb)}" for (ca, sa), (cb, sb) in pairs if sa is not None and sb is not None})


def apply(op, g):
    """one touch of an operator on a glyph; None when the operator's effect on this glyph is unknown (a VIOLET piece:
    the node has not been seen to act on this state yet)"""
    if op is None: return None
    c, sh = g
    k = op[0]
    if k == "R": return (c, np.rot90(sh, -op[1]))
    if k == "F": return (c, np.fliplr(sh))
    if k == "C":
        m = op[1] if isinstance(op[1], dict) else {str(op[1]): op[2]}
        return (int(m[str(c)]), sh) if str(c) in m else None
    if k == "S":
        t = op[1].get(shape_text(sh))
        return (c, shape_from(t)) if t else None
    if k == "M":
        t = op[1].get(state_text(g))
        return parse_state(t) if t else None
    if k == "RC": return (op[3], np.rot90(sh, -op[1])) if c == op[2] else None
    return None


def op_text(op):
    if op is None: return "?"
    if op[0] == "R": return f"turn {op[1] * 90} degrees clockwise"
    if op[0] == "C" and isinstance(op[1], dict): return "recolour " + ", ".join(f"{a} -> {b}" for a, b in op[1].items())
    if op[0] == "C": return f"recolour {op[1]} -> {op[2]}"
    if op[0] == "F": return "mirror"
    if op[0] == "S": return "reshape " + ", ".join(f"[{a}] -> [{b}]" for a, b in op[1].items())
    if op[0] == "M": return "change " + ", ".join(f"{a} -> {b}" for a, b in op[1].items())
    if op[0] == "RC": return f"turn {op[1] * 90} and recolour {op[2]} -> {op[3]}"
    return str(op)


def op_symbol(op, src):
    return {"R": "R", "C": "C", "F": "F", "S": "S", "M": "M", "RC": "RC"}.get(op[0], "?") + f"[{src}]"


def solve(start, target, ops, max_depth=MAXDEPTH):
    """THE EQUATION: the shortest product of known operators taking start to target. ops = {source: op}. Returns the
    touch sequence [source, ...] (empty when start already equals target) or None."""
    if start is None or target is None: return None
    if same(start, target): return []
    key = lambda g: (g[0], g[1].shape, g[1].tobytes())
    seen = {key(start)}; frontier = [(start, [])]
    for _ in range(max_depth):
        nxt = []
        for g, path in frontier:
            for src, op in ops.items():
                h = apply(op, g)
                if h is None: continue
                if same(h, target): return path + [src]
                kh = key(h)
                if kh in seen: continue
                seen.add(kh); nxt.append((h, path + [src]))
        frontier = nxt
        if not frontier: break
    return None


def frontier(start, ops, max_depth=8, skip=frozenset()):
    """THE EDGE OF WHAT SHE KNOWS: the shortest product of known operators taking the key to a state on which some node's
    effect is not known yet, and that node. Returns (touches, node) or None. (Run 30: after the first box every node's
    effect on the key in hand was known, none led to the second box, and her hands stopped.)"""
    if start is None: return None
    key = lambda g: (g[0], g[1].shape, g[1].tobytes())
    seen = {key(start)}; frontier_ = [(start, [])]
    for _ in range(max_depth):
        nxt = []
        for g, path in frontier_:
            unknown = [src for src, op in ops.items() if apply(op, g) is None and (state_text(g), src) not in skip]
            if unknown and path: return path, unknown[0]
            for src, op in ops.items():
                h = apply(op, g)
                if h is None: continue
                kh = key(h)
                if kh in seen: continue
                seen.add(kh); nxt.append((h, path + [src]))
        frontier_ = nxt
        if not frontier_: break
    return None


def powers(seq):
    out = {}
    for s_ in seq: out[s_] = out.get(s_, 0) + 1
    return out


def equation_text(seq, ops):
    pw = powers(seq)
    terms = [f"{op_symbol(ops[s_], s_)}^{n}" for s_, n in pw.items()]
    return (" . ".join(terms) or "1") + " (key) = target"


# ============================================================================================ attribution
def touched_thing(bp, things):
    """the thing the body's block lies on (run 16: a used ring is gone from the board, so 'its colour is gone' named the
    ring for a rotator's turn; the body's own block is the evidence of what it stands on)"""
    if bp is None: return None
    here = block_cells(bp); best, n_best = None, 10 ** 9
    for tid, t in things.items():
        if tid.startswith(("open@", "chg", "place", "wall")) or not t.get("box"): continue
        n = int(t.get("n") or 0)
        if n < 1 or n > 30: continue
        if box_cells(t["box"]) & here and n < n_best: best, n_best = tid, n
    return best


def covered_thing(f, things):
    """the thing the body is standing on: the non-opening thing whose own colour is gone from most of its cells"""
    bp = body_pos(f)
    if bp is not None: return touched_thing(bp, things)
    best, frac_best = None, 1.0
    for tid, t in things.items():
        if tid.startswith(("open@", "chg", "place", "wall")) or t.get("box") is None or t.get("colour") is None: continue
        n = int(t.get("n") or 0)
        if n < 1 or n > 30: continue                          # small things are touched; big ones are walls and HUDs
        y0, x0, y1, x1 = t["box"]
        vis = int((np.asarray(f)[y0:y1 + 1, x0:x1 + 1] == int(t["colour"])).sum())
        frac = vis / n
        if frac < 0.5 and frac < frac_best: best, frac_best = tid, frac
    return best


def colour_of(tid):
    try: return int(str(tid).split("@")[0])
    except Exception: return None


def _adjacent(b, kb):
    return all(abs(kb[i] - b[i]) <= 2 for i in range(4))


class NodeBook:
    """HER NODES (Jonathan, Oct 27: 'if one is reached by 2 nodes separately they could end up having the same color but
    then belong to different jobs'). A node is a thing's colour ON ONE LEVEL: L<level>:c<colour>, holding every change it
    was seen to make to the key; its law is fit() over them (WHITE: one node, its own colours). A law shared by the same
    colour on two or more levels, agreeing, is GOLD and is offered on a new level as the core's hypothesis; a single
    node from another level is only a hint. A hypothesis is checked by the first touch: a contradiction makes this
    level's own node."""
    def __init__(s, store, legacy=None):
        s.d = store
        if legacy and not s.d:                          # the colour-keyed book of the morning, carried over as nodes:
            P = np.array([[1, 1, 0], [1, 0, 0], [0, 0, 0]])   # its laws become the changes they stand for (a recolour map
            for c, e in legacy.items():                        # as colour pairs, a turn as a turned test shape), so later
                op = e.get("op") or []                         # sightings add to them instead of replacing them
                tr = []
                if op and op[0] == "C":
                    m = op[1] if isinstance(op[1], dict) else {str(op[1]): op[2]}
                    tr = [[f"{a}|*", f"{b}|*"] for a, b in m.items()]
                elif op and op[0] == "R":
                    tr = [[f"0|{shape_text(P)}", f"0|{shape_text(np.rot90(P, -int(op[1])))}"]]
                if not tr: continue
                for lv in e.get("levels", []):
                    s.d[f"L{int(lv)}:c{int(c)}"] = {"level": int(lv), "colour": int(c), "trans": [list(x) for x in tr],
                                                    "seen": int(e.get("seen", 1)), "ids": list(e.get("ids", [])), "migrated": True}

        # run 21: a node of the afternoon was keyed by its colour on a level, and level 4 has two different things of
        # colour 12 (a part of the changer, and the body's own start square that a reset was blamed on). A node is
        # one thing on one level; a key that held one thing's sightings is re-keyed to that thing.
        for k in [k for k in list(s.d) if re.fullmatch(r"L\d+:c\d+", k)]:
            e = s.d[k]
            if e.get("migrated") or len(e.get("ids") or []) != 1: continue
            nk = s.key(e["level"], e["ids"][0])
            if nk not in s.d: s.d[nk] = dict(e, tid=e["ids"][0])
            del s.d[k]

    @staticmethod
    def key(lvl, tid): return f"L{int(lvl)}:{tid}"

    def node(s, lvl, tid):
        """the thing's own node on the level; a node carried over from the colour book (levels 1-3, 'migrated') stands
        for every thing of its colour on its level"""
        e = s.d.get(s.key(lvl, tid))
        if e is None and colour_of(tid) is not None:
            e = s.d.get(f"L{int(lvl)}:c{int(colour_of(tid))}")
            if e is not None and not e.get("migrated"): e = None
        return e

    def observe(s, tid, lvl, a, b):
        c = colour_of(tid); t = transform(a, b)
        if c is None or t is None: return None
        k = s.key(lvl, tid); e = s.node(lvl, tid)
        if e is None: e = s.d[k] = {"level": int(lvl), "colour": int(c), "tid": tid, "trans": [], "seen": 0, "ids": []}
        before = fit(e["trans"]) if e["trans"] else None
        if list(t) not in e["trans"]: e["trans"] = (e["trans"] + [list(t)])[-40:]
        e["seen"] += 1
        if tid not in e["ids"]: e["ids"] = (e["ids"] + [tid])[-8:]
        after = fit(e["trans"])
        if before is None: return "new"
        return "again" if (before[0] == after[0] and before == after) else ("grew" if before[0] == after[0] else "relearned")

    def white(s, lvl, tid):
        e = s.node(lvl, tid)
        return fit(e["trans"]) if e and e["trans"] else None

    def gold(s, c, but=None):
        """the law of a colour held by two or more nodes elsewhere, agreeing (Jonathan: 'gold notes would be when
        multiple nodes are involved and white is a single node')"""
        laws = []
        for k, e in s.d.items():
            if e.get("colour") != int(c) or e.get("level") == but or not e.get("trans"): continue
            laws.append((e["level"], fit(e["trans"])))
        if len(laws) < 2: return None
        kinds = {op[0] for _, op in laws if op}
        if len(kinds) != 1: return None
        kind = kinds.pop()
        if kind == "R" and len({op[1] for _, op in laws}) == 1: return laws[0][1]
        if kind == "F": return ("F",)
        if kind == "C":
            m = {}
            for _, op in laws:
                for a_, b_ in op[1].items():
                    if a_ in m and m[a_] != b_: return None
                    m[a_] = b_
            return ("C", m)
        return None

    def hint(s, c, but=None):
        for k, e in sorted(s.d.items(), key=lambda kv: (-len(kv[1].get("trans", [])), -kv[1].get("seen", 0))):
            if e.get("colour") == int(c) and e.get("level") != but and e.get("trans"): return fit(e["trans"]), e["level"]
        return None, None

    def _hint_src(s, c, lvl):
        h, hl = s.hint(c, but=lvl)
        return h, (f"hint from level {hl + 1}" if h else None)

    def op_for(s, tid, lvl):
        """(op, where it came from): this level's own node, else the gold law, else a hint from another level"""
        c = colour_of(tid)
        if c is None: return None, None
        w = s.white(lvl, tid)
        if w: return w, "white"
        lf = getattr(s, "look_law", None)               # a metal note whose nodes look like this thing (Oct 27 evening)
        if lf is not None:
            try:
                r_ = lf(lvl, tid)
                if r_: return r_
            except Exception: pass
        g = s.gold(c, but=lvl)
        if g: return g, "gold"
        h, hl = s.hint(c, but=lvl)
        if h: return h, f"hint from level {hl + 1}"
        return None, None

    def parts(s, things, lvl):
        """every thing on the level with the operator it carries (its own node's, or the node of a thing within 2
        cells: a changer the body sees as two colours side by side is one node with one job)"""
        out = {}
        known = {}
        for tid in things:
            if tid.startswith(("open@", "chg", "place", "wall")): continue
            op, _ = s.op_for(tid, lvl)
            if op: known[tid] = op
        for tid, t in things.items():
            if tid.startswith(("open@", "chg", "place", "wall")): continue
            if tid in known: out[tid] = known[tid]; continue
            b = t.get("box")
            if not b or t.get("moving"): continue
            for kid, op in known.items():
                kb = things.get(kid, {}).get("box")
                if kb and not things.get(kid, {}).get("moving") and _adjacent(b, kb): out[tid] = op; break
        return out

    def for_level(s, things, lvl):
        """the operator nodes lit on a level, one per physical thing (adjacent parts merged: their own changes pooled
        and the law fitted again), with where each came from"""
        groups = []
        for tid, t in things.items():
            if tid.startswith(("open@", "chg", "place", "wall")) or not t.get("box"): continue
            op, src = s.op_for(tid, lvl)
            if not op: continue
            g = None if t.get("moving") else next((g for g in groups if not any(things[m].get("moving") for m in g)
                                                   and any(_adjacent(t["box"], things[m]["box"]) for m in g)), None)
            if g is None: groups.append([tid])
            else: g.append(tid)
        ops, srcs = {}, {}
        for g in groups:
            rep = g[0]
            local = []
            for m in g:
                e = s.node(lvl, m)
                if e and e.get("trans"): local += [x for x in e["trans"] if not isinstance(x, dict) and x not in local]
            if local:
                ops[rep] = fit(local); srcs[rep] = "white"
                # a hypothesis her first touches agreed with keeps its other colours (ls20 level 4: one touch showed
                # 14 -> 8, level 3's changer said 14 -> 8 too and knew 8 -> 12 -> 9; dropping that made her probe)
                best = None
                for m in g:
                    ll_ = None
                    lf_ = getattr(s, "look_law", None)          # the nodes that look like it (run 28: level 6's reshaper
                    if lf_ is not None:                         # turned ##./.##/#.# into .#./.#./### as level 4's did)
                        try: ll_ = lf_(lvl, m)
                        except Exception: ll_ = None
                    for cand, where in ([ll_] if ll_ else []) + [(s.gold(colour_of(m), but=lvl), "gold"), s._hint_src(colour_of(m), lvl)]:
                        merged = _agrees(ops[rep], cand)
                        if merged is not None and (best is None or _size(merged) > _size(best[0])): best = (merged, where, m)
                if best is not None and _size(best[0]) > _size(ops[rep]):
                    ops[rep] = best[0]; srcs[rep] = f"white, agrees with {best[1]}" + (f" via {best[2]}" if best[2] != rep else "")
            else:
                cands = []
                for m in g:
                    op, src = s.op_for(m, lvl)
                    if not op: continue
                    rank = 0 if src == "white" else 1 if src == "gold" else 2
                    size = len(op[1]) if op[0] in ("C", "S", "M") and isinstance(op[1], dict) else 1
                    cands.append((rank, -size, m, op, src))
                if cands:
                    cands.sort(key=lambda x: (x[0], x[1]))
                    _, _, m, op, src = cands[0]
                    ops[rep] = op; srcs[rep] = src + (f" via {m}" if m != rep else "")
        return ops, srcs


def _size(op):
    return len(op[1]) if op and op[0] in ("C", "S", "M") and isinstance(op[1], dict) else 1


def _agrees(local, cand):
    """the hypothesis with the local sightings folded in, when every local change is one the hypothesis predicts;
    None when they disagree (then the local node stands alone)"""
    if not local or not cand or local[0] != cand[0]: return None
    if local[0] in ("C", "S", "M"):
        if not (isinstance(local[1], dict) and isinstance(cand[1], dict)): return None
        for a_, b_ in local[1].items():
            if a_ in cand[1] and cand[1][a_] != b_: return None
        if not any(a_ in cand[1] for a_ in local[1]): return None     # nothing in common: no evidence either way
        return (local[0], {**cand[1], **local[1]})
    return cand if tuple(local) == tuple(cand) else None


# ============================================================================================ metal notes (tints)
# Jonathan, Oct 27 evening: "what if its more like getting a metallic color and gold is just the floor? ... what if each
# node left a tint in the gold? ... there would be a limit to it, like the dimensions only go so high. so depending on
# which nodes were involved in the note it could come out like copper or some other metal."
#
# A METAL NOTE is a law that two or more nodes agree on (gold is that floor). Every node that holds it leaves its tint,
# read from what the node is. The tint has three dimensions, and no more:
#   colour    the nodes are of different colours                 -> silver   (the law crosses colours)
#   look      the nodes look different (shape and colours together) -> copper (the law crosses kinds of thing)
#   coverage  some nodes showed only part of the law            -> bronze   (the law is still being worked)
# Each dimension has two depths (light, deep). The note's metal is gold, tinted by its strongest dimension.
GOLD_RGB = (212, 175, 55)
TINT_RGB = {"colour": (200, 200, 205), "look": (184, 115, 51), "coverage": (150, 120, 70)}
TINT_NAME = {"colour": ("electrum", "silver"), "look": ("rose gold", "copper"), "coverage": ("brass", "bronze")}
LOOK_HEX = "0123456789abcdef"


def ground_of(f):
    """the floor colour: the commonest colour that is not a wall"""
    v, c = np.unique(np.asarray(f), return_counts=True)
    cand = [(int(n), int(x)) for x, n in zip(v, c) if int(x) not in WALLS]
    return max(cand)[1] if cand else None


def look_of(f, box, ground=None):
    """WHAT A THING LOOKS LIKE: the patch of non-floor, non-wall cells joined to it (its other colours included),
    cropped, as text ('.0./100/.1.' is ls20's rotator: colour 0 with two colour-1 marks). None for big things."""
    f = np.asarray(f); H, W = f.shape
    g = {int(ground)} if ground is not None else {ground_of(f)}
    g |= set(WALLS)
    y0, x0, y1, x1 = [int(v) for v in box]
    seed = [(y, x) for y in range(max(0, y0), min(H, y1 + 1)) for x in range(max(0, x0), min(W, x1 + 1)) if int(f[y, x]) not in g]
    if not seed: return None
    comp = set(seed); st = list(seed)
    while st:
        y, x = st.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q in comp or not (0 <= q[0] < H and 0 <= q[1] < W): continue
                if q[0] < y0 - 3 or q[0] > y1 + 3 or q[1] < x0 - 3 or q[1] > x1 + 3: continue
                if int(f[q]) in g: continue
                comp.add(q); st.append(q)
    if len(comp) > 40: return None
    ys = [c[0] for c in comp]; xs = [c[1] for c in comp]
    rows = []
    for y in range(min(ys), max(ys) + 1):
        rows.append("".join(LOOK_HEX[int(f[y, x])] if (y, x) in comp else "." for x in range(min(xs), max(xs) + 1)))
    return "/".join(rows)


def look_d4(a):
    """the look in all eight turns and mirrors (a thing turned on another level is the same kind of thing)"""
    if not a: return set()
    rows = a.split("/"); m = np.array([list(r) for r in rows])
    out = set()
    for t in range(8):
        g = np.rot90(m, t % 4)
        if t >= 4: g = np.fliplr(g)
        out.add("/".join("".join(r) for r in g))
    return out


def _law_size(op):
    return len(op[1]) if op and op[0] in ("C", "S", "M") and isinstance(op[1], dict) else 1


def _job(op):
    k = op[0] if op else None
    return {"C": "the key's colour", "R": "the key's shape", "F": "the key's shape", "S": "the key's shape",
            "M": "the key", "RC": "the key's colour", "spring": "the body", "refill": "the bar"}.get(k, "?")


def node_witnesses(j, key, e):
    """the things a node stands for, on its level, with their looks (a node carried over from the colour book lists
    things of other levels too; only its own level's count)"""
    lv = int(e["level"]); things = j.get("things", {}).get(str(lv), {}); looks = j.get("core_looks", {}).get(str(lv), {})
    ids = [e["tid"]] if e.get("tid") else [t for t in (e.get("ids") or []) if t in things]
    out = []
    for t in ids:
        out.append({"node": key, "level": lv, "tid": t, "colour": colour_of(t), "look": looks.get(t), "n": (things.get(t) or {}).get("n")})
    return out


def metal_notes(j, book, mbook=None, min_nodes=2):
    """every law two or more nodes agree on, with its witnesses, its tint and its metal (min_nodes=1 keeps the single
    nodes too, for matching a new thing by its look)"""
    nodes = [(k, e, fit(e["trans"])) for k, e in book.d.items() if e.get("trans")]
    nodes = [(k, e, op) for k, e, op in nodes if op]
    nodes.sort(key=lambda x: -_law_size(x[2]))
    groups = []                                           # [law, [node keys]]
    for k, e, op in nodes:
        for g in groups:
            m = _agrees(op, g[0]) if op[0] in ("C", "S", "M") else (g[0] if tuple(op) == tuple(g[0]) else None)
            if m is not None:
                g[0] = m; g[1].append((k, e, op)); break
        else:
            groups.append([op, [(k, e, op)]])
    out = []
    for law, members in groups:
        wit = []
        for k, e, op in members:
            for w in node_witnesses(j, k, e):
                w["coverage"] = round(_law_size(op) / max(1, _law_size(law)), 2)
                if not any(x["level"] == w["level"] and x["look"] == w["look"] and w["look"] for x in wit): wit.append(w)
        a_ = _alloy(law, wit, op_text(law)); a_["_op"] = law; out.append(a_)
    if min_nodes < 2: return [a for a in out if a["witnesses"]]
    if mbook is not None:                                 # the move law: a spring line on each level it held on
        for c, e in mbook.d.get("springs", {}).items():
            if e.get("seen", 0) < 2 or e.get("miss", 0) * 10 > e["seen"]: continue
            wit = [{"node": f"L{lv}:spring", "level": int(lv), "tid": f"{c}-line", "colour": int(c), "look": "line", "coverage": 1.0}
                   for lv in e.get("levels", [])]
            out.append(_alloy(("spring", int(c)), wit, f"a colour-{c} line along a face pushes the body away to the next wall (seen {e['seen']}x)"))
    rings = {}                                            # the refill: every ring that refilled the bar
    for life in j.get("lives", []):
        for x in life.get("experiments", []):
            if "level" in x and x.get("result") == "refill": rings.setdefault((int(x["level"]), str(x["id"])), 0)
    looks = j.get("core_looks", {})
    wit = [{"node": f"L{lv}:{t}", "level": lv, "tid": t, "colour": colour_of(t), "look": looks.get(str(lv), {}).get(t), "coverage": 1.0}
           for (lv, t) in sorted(rings)]
    if len({w["level"] for w in wit}) >= 2: out.append(_alloy(("refill",), wit, "walking into it fills the bar"))
    return [a for a in out if len(a["witnesses"]) >= 2]


def _alloy(law, wit, text):
    from collections import Counter
    def spread(vals):
        vals = [v for v in vals if v is not None]
        if len(vals) < 2: return 0.0
        top = Counter(vals).most_common(1)[0][1]
        return round(1.0 - top / len(vals), 2)
    looks = []
    for w in wit:                                         # looks that are turns or mirrors of each other count as one
        lk = w.get("look")
        if lk is None: looks.append(None); continue
        same = next((x for x in looks if x is not None and lk in look_d4(x)), None)
        looks.append(same or lk)
    tint = {"colour": spread([w.get("colour") for w in wit]), "look": spread(looks),
            "coverage": round(1.0 - sum(w.get("coverage", 1.0) for w in wit) / max(1, len(wit)), 2)}
    strong = [(v, d) for d, v in tint.items() if v >= 0.1]
    if not strong: metal = "gold"
    else:
        v, d = max(strong)
        metal = TINT_NAME[d][1 if v >= 0.4 else 0]
        rest = [d2 for v2, d2 in sorted(strong, reverse=True)[1:]]
        if rest: metal += " with " + " and ".join(TINT_NAME[d2][0] for d2 in rest)
    tot = min(0.6, 0.6 * sum(tint.values()))
    s_ = sum(tint.values()) or 1.0
    rgb = tuple(int(round(GOLD_RGB[i] * (1 - tot) + sum(TINT_RGB[d][i] * tot * tint[d] / s_ for d in tint))) for i in range(3))
    levels = sorted({w["level"] for w in wit})
    kinds = sorted({w["look"] for w in wit if w.get("look")})
    name = (law[0] if law else "?") + ":" + ",".join(f"L{w['level']}:{w['tid']}" for w in wit[:3])
    return {"id": name, "law": [law[0]] + [law[1] if len(law) > 1 else None], "law_text": text, "job": _job(law),
            "witnesses": wit, "tint": tint, "metal": metal, "rgb": list(rgb), "levels": [l + 1 for l in levels], "looks": kinds,
            "text": (f"{metal[0].upper() + metal[1:]} note: {text}. It acts on {_job(law)}; {len(wit)} nodes hold it, on levels "
                     f"{', '.join(str(l + 1) for l in levels)}" + (f"; they look like {', '.join(kinds)}" if kinds else "") +
                     (f". Tint: " + ", ".join(f"{d} {v}" for d, v in tint.items() if v) if any(tint.values()) else ". No tint: pure gold"))}


def learn_looks(j, lvl, f, body=None):
    """every thing's look on a level, read off the level's first frame (the body's own square left out)"""
    things = j.get("things", {}).get(str(int(lvl)), {}); store = j.setdefault("core_looks", {}).setdefault(str(int(lvl)), {})
    g = ground_of(f); here = block_cells(body) if body is not None else set(); n = 0
    for tid, t in things.items():
        if not isinstance(t, dict) or not t.get("box") or str(tid).startswith(("open@", "chg", "place", "wall")): continue
        if here and box_cells(t["box"]) & here: continue
        lk = look_of(f, t["box"], g)
        if lk and store.get(tid) != lk: store[tid] = lk; n += 1
    return n


# ============================================================================================ things that move (tracks)
# Jonathan, Oct 28: "for the moving things would she make a bigger static body where the moving thing goes and then
# switch the pixels in there on/off to follow the object?" The static body is the TRACK: every square the thing visits,
# in order, as one lap. The square that is on is the thing. Her saved level-6 frames say what switches it: every press
# that moves the body advances every moving thing one square; a press that goes nowhere moves nothing; a reset or a
# death puts them back to the lap's start. So the thing at tick t stands at lap[t mod P] (0 misses over 3 things and
# 4 resets in run 24). A touch is the body's square overlapping the thing after a moving press - every such press,
# including the ones where they move together.
def find_look(f, look):
    """every place (top-left) where a look appears exactly in the frame"""
    f = np.asarray(f); rows = look.split("/"); h, w = len(rows), len(rows[0]); H, W = f.shape
    if h > H or w > W: return []
    m = np.ones((H - h + 1, W - w + 1), bool)
    for dy, r in enumerate(rows):
        for dx, c in enumerate(r):
            if c != ".": m &= (f[dy:H - h + 1 + dy, dx:W - w + 1 + dx] == int(c, 16))
    ys, xs = np.where(m)
    return list(zip(ys.tolist(), xs.tolist()))


def look_cells_at(look, pos):
    rows = look.split("/")
    return {(pos[0] + dy, pos[1] + dx) for dy, r in enumerate(rows) for dx, c in enumerate(r) if c != "."}


def look_box_at(look, pos):
    rows = look.split("/")
    return [pos[0], pos[1], pos[0] + len(rows) - 1, pos[1] + len(rows[0]) - 1]


def learn_track(obs, max_p=24):
    """obs = {tick: (y, x)}: the shortest lap that every sighting agrees with, seen whole at least twice; None for a
    thing that stands still or has not been watched long enough"""
    if len({tuple(v) for v in obs.values()}) < 2: return None
    top = max(obs)
    for P in range(2, max_p + 1):
        if top + 1 < 2 * P: break
        lap = [None] * P; ok = True
        for t, v in obs.items():
            v = tuple(v)
            if lap[t % P] is None: lap[t % P] = v
            elif lap[t % P] != v: ok = False; break
        if ok and all(x is not None for x in lap): return [list(x) for x in lap]
    return None


def level_ticks(F, rec, ks, start):
    """the tick (body moves since the level began, back to 0 on a reset or a death) at each frame index in ks"""
    tick = 0; out = {ks[0]: 0}
    for k in ks[:-1]:
        p0, p1 = body_pos(F[k]), body_pos(F[k + 1])
        why = str(rec[k].get("why", ""))
        if why.startswith("reset") or (p1 is not None and p1 == start and p0 is not None and p0 != start
                                        and abs(p0[0] - p1[0]) + abs(p0[1] - p1[1]) > BODY):
            tick = 0
        elif p0 is not None and p1 is not None and p0 != p1: tick += 1
        out[k + 1] = tick
    return out


def learn_tracks_from_life(j, F, rec, log=print):
    """read the tracks of every thing that moved in a saved life, level by level"""
    by = {}
    for k in range(1, min(len(rec), len(F) - 1)):
        by.setdefault(int(rec[k - 1]["levels"]), []).append(k)
    out = []
    store = j.setdefault("core_tracks", {})
    for lv, ks in by.items():
        looks = j.get("core_looks", {}).get(str(lv), {})
        kinds = {}
        for tid, lk in looks.items():
            if lk and "/" in lk and lk not in ("bbb/b.b/bbb",): kinds.setdefault(lk, []).append(tid)
        if not kinds: continue
        ticks = level_ticks(F, rec, ks, body_pos(F[ks[0]]))
        for lk, tids in kinds.items():
            obs = {}
            for k in ks:
                h = find_look(F[k], lk)
                if len(h) == 1 and k in ticks: obs.setdefault(ticks[k], h[0])
            lap = learn_track(obs)
            if not lap: continue
            nodes = j.get("core_nodes", {})
            tid = max(tids, key=lambda t_: (nodes.get(f"L{lv}:{t_}", {}).get("seen", 0), [-ord(c) for c in t_]))
            old = store.get(str(lv), {}).get(lk, {})
            store.setdefault(str(lv), {})[lk] = {"lap": lap, "P": len(lap), "tid": old.get("tid") or tid}
            out.append((lv, lk, len(lap)))
    if out: log("  core: things that move, read from her last life: " +
                "; ".join(f"level {lv + 1} {lk} on a lap of {P}" for lv, lk, P in out))
    return out


def reach_timed(f, start, t0, goal_cells, avoid_cells, movers, goal_mover=None, max_steps=70, into_walls=False,
                blocked=frozenset(), springs=(), jumps=None):
    """THE MEETING: the shortest press path by place and tick. movers = {id: (look, lap)}; a mover stands at
    lap[t mod P] at tick t, and every press that moves the body is one tick. The goal is a static goal or the mover
    goal_mover (the body's square overlapping it after a press); every other mover is kept off."""
    import math
    from collections import deque
    f = np.asarray(f)
    L = 1
    for _, lap in movers.values(): L = L * len(lap) // math.gcd(L, len(lap))
    L = min(L, 48)
    def mc(mid, t):
        look, lap = movers[mid]; y, x = lap[t % len(lap)]
        return look_cells_at(look, (y, x))
    q = deque([(start, t0, [])]); seen = {(start, t0 % L)}
    while q:
        p, t, path = q.popleft()
        if len(path) >= max_steps: continue
        for a, (dy, dx) in MOVES.items():
            st = step_to(f, p, a, springs, jumps, blocked)
            t1 = t + 1
            if st is None:
                n = (p[0] + dy, p[1] + dx)              # a walled goal (the box) is entered by a plain step
                if into_walls and goal_mover is None and (p, a) not in blocked and _inside(f, n) and block_cells(n) & goal_cells and n != p:
                    if not any(block_cells(n) & mc(m_, t1) for m_ in movers): return path + [a]
                continue
            n, passed = st
            cells = block_cells(n)
            if any(cells & mc(m_, t1) for m_ in movers if m_ != goal_mover): continue
            if any(block_cells(c) & (goal_cells | avoid_cells) for c in passed[:-1]): continue
            if goal_mover is not None and cells & mc(goal_mover, t1): return path + [a]
            if goal_mover is None and cells & goal_cells and n != p: return path + [a]
            if (n, t1 % L) in seen or cells & avoid_cells: continue
            seen.add((n, t1 % L)); q.append((n, t1, path + [a]))
    return None


def align_rec(rec):
    """the saved life's records lined up with its frames: a death saves the death frame with its press and then the
    reset frame with no record of its own (run 25: every press after the death was read one frame late, and her move
    book took 55 of them for jumps). The reset gets a record here."""
    out = []
    for r in rec:
        out.append(r)
        if r.get("state") == "GAME_OVER":
            out.append({"n": r.get("n"), "a": 0, "x": -1, "y": -1, "levels": r.get("levels"), "state": "RESET", "why": "reset"})
    return out


def saved_life_sig(game):
    pz = os.path.join(EYE, f"play_{game}.npz")
    try: st = os.stat(pz); return f"{int(st.st_mtime)}:{st.st_size}"
    except Exception: return None


def learn_from_saved_life(game, j, log=print):
    """read the last life's saved frames (D:\\planet\\eye\\play_<game>.npz + .jsonl) and add every key change she can
    give to a touched thing. A life is read once (its signature is kept), and a life her core already watched press by
    press is marked read when it ends. Returns the list of what she learned."""
    pz, pj = os.path.join(EYE, f"play_{game}.npz"), os.path.join(EYE, f"play_{game}.jsonl")
    if not (os.path.exists(pz) and os.path.exists(pj)): return []
    sig = saved_life_sig(game)
    if j.get("core_book") != "nodes":                  # lives read by the colour book were read without reshapes (run 20's
        j["core_read"] = []; j["core_book"] = "nodes"   # level-4 touch was lost): the node book reads the last life again
    if sig is not None and sig in j.setdefault("core_read", []):
        if not j.get("core_looks"):                     # a life read before looks were kept: read only the looks
            try:
                F = np.load(pz)["F"]; rec = align_rec([json.loads(l) for l in open(pj, encoding="utf-8")]); seen_ = set()
                for k in range(1, min(len(rec), len(F) - 1)):
                    lv_ = int(rec[k - 1]["levels"])
                    if lv_ not in seen_: seen_.add(lv_); learn_looks(j, lv_, F[k], body_pos(F[k]))
                log(f"  core: read the looks of {sum(len(v) for v in j.get('core_looks', {}).values())} things from her last life's first frames")
            except Exception: pass
        if not j.get("core_tracks"):                    # a life read before tracks were kept: read only the tracks
            try:
                F = np.load(pz)["F"]; rec = align_rec([json.loads(l) for l in open(pj, encoding="utf-8")])
                learn_tracks_from_life(j, F, rec, log)
            except Exception as e_: log(f"  core: could not read the tracks ({str(e_)[:80]})")
        return []
    if sig is not None: j["core_read"] = (j["core_read"] + [sig])[-20:]
    F = np.load(pz)["F"]; rec = align_rec([json.loads(l) for l in open(pj, encoding="utf-8")])
    region = hud_region(j)
    if region is None: return []
    book = NodeBook(j.setdefault("core_nodes", {}), j.get("core_ops")); out = []
    moves = MoveBook(j.setdefault("core_moves", {})); springs0 = set(moves.springs()); mv = {}
    starts = {}; first_k = {}
    for k in range(1, min(len(rec), len(F) - 1)):
        lvl_before = int(rec[k - 1]["levels"]); lvl_after = int(rec[k]["levels"])
        if lvl_before not in starts: starts[lvl_before] = body_pos(F[k]); first_k[lvl_before] = k
        if lvl_after != lvl_before or str(rec[k].get("why", "")).startswith("reset"): continue
        try:                                              # how the body moved on this press
            a_ = rec[k].get("a"); p0, p1 = body_pos(F[k]), body_pos(F[k + 1])
            if isinstance(a_, int) and a_ in MOVES and p0 is not None and p1 is not None and not (p1 == starts.get(lvl_before) and p0 != p1):
                r_ = moves.learn(F[k], lvl_before, p0, a_, p1)
                if r_: mv[r_] = mv.get(r_, 0) + 1
        except Exception: pass
        a, b = read_glyph(F[k], region), read_glyph(F[k + 1], region)
        if transform(a, b) is None: continue
        bp = body_pos(F[k + 1])
        if bp is not None and bp == starts.get(lvl_before): continue          # a death: back at the start, the key with it
        things = j.get("things", {}).get(str(lvl_before), {})
        if starts.get(lvl_before) is not None:
            things = {k: v for k, v in things.items() if not (isinstance(v, dict) and v.get("box") and box_cells(v["box"]) <= block_cells(starts[lvl_before]))}
        tid = touched_thing(bp, things) if bp is not None else covered_thing(F[k + 1], things)
        if tid is None: continue
        r = book.observe(tid, lvl_before, a, b)
        out.append({"press": rec[k]["n"], "level": lvl_before, "thing": tid, "change": list(transform(a, b)), "book": r})
    for lv_, k_ in first_k.items():                      # what each thing looks like, from each level's first frame
        try: learn_looks(j, lv_, F[k_], body_pos(F[k_]))
        except Exception: pass
    try: learn_tracks_from_life(j, F, rec, log)          # and the laps of the things that move
    except Exception as e_: log(f"  core: could not read the tracks ({str(e_)[:80]})")
    if mv: log(f"  core: read her last life's moves - " + ", ".join(f"{v} {k}" for k, v in sorted(mv.items())) +
               (f"; the spring law now holds for colour(s) {sorted(set(moves.springs()) - springs0)}" if set(moves.springs()) - springs0 else ""))
    if out: log(f"  core: read her last life's frames - {len(out)} key change(s): " +
                "; ".join(f"level {o['level'] + 1} press {o['press']}: {o['thing']} {o['change'][0]} -> {o['change'][1]}" for o in out[:8]))
    return out


def hud_region(j):
    rels = j.get("relations") or []
    for r in reversed(rels):
        if r.get("region"): return tuple(int(v) for v in r["region"])
    return None


# ============================================================================================ the muscle
WALLS = {4, 5}                                         # yellow walls and grey boxes (the body never enters them)
MOVES = {1: (-5, 0), 2: (5, 0), 3: (0, -5), 4: (0, 5)}  # ACTION1-4, read off her saved life: up, down, left, right by 5
BODY = 5


def body_pos(f):
    """the body: a 5x5 block, two rows of one colour over three of another (ls20: 12 over 9). Top-left (row, col)."""
    f = np.asarray(f); H, W = f.shape
    for y in range(0, H - 4):
        for x in range(0, W - 4):
            top = f[y:y + 2, x:x + 5]; bot = f[y + 2:y + 5, x:x + 5]
            a, b = int(top[0, 0]), int(bot[0, 0])
            if a == b or a in WALLS or b in WALLS or a == 3 or b == 3: continue
            if (top == a).all() and (bot == b).all(): return (y, x)
    return None


def block_cells(p):
    y, x = p
    return {(y + i, x + j) for i in range(BODY) for j in range(BODY)}


def box_cells(box):
    y0, x0, y1, x1 = box
    return {(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


def _inside(f, p):
    y, x = p; H, W = f.shape
    return not (y < 0 or x < 0 or y + BODY > H or x + BODY > W)


def _open(f, p):
    y, x = p
    return _inside(f, p) and not np.isin(f[y:y + BODY, x:x + BODY], list(WALLS)).any()


def spring_push(f, n, colours):
    """THE SPRING (run 21, ls20 level 4): a thin line of one colour along one face of the square the body steps into
    pushes it straight away from that face. Returns the push (dy, dx), or None when no face (or more than one) has it."""
    y, x = n; H, W = f.shape; d = []
    for c in colours:
        c = int(c)
        if y - 1 >= 0 and (f[y - 1, x:x + BODY] == c).sum() >= 3: d.append((BODY, 0))
        if y + BODY < H and (f[y + BODY, x:x + BODY] == c).sum() >= 3: d.append((-BODY, 0))
        if x - 1 >= 0 and (f[y:y + BODY, x - 1] == c).sum() >= 3: d.append((0, BODY))
        if x + BODY < W and (f[y:y + BODY, x + BODY] == c).sum() >= 3: d.append((0, -BODY))
    return d[0] if len(d) == 1 else None


def face_colours(f, n):
    """the colours lying along a face of the square at n (three cells or more of one face)"""
    y, x = n; H, W = f.shape; out = set()
    faces = []
    if y - 1 >= 0: faces.append(f[y - 1, x:x + BODY])
    if y + BODY < H: faces.append(f[y + BODY, x:x + BODY])
    if x - 1 >= 0: faces.append(f[y:y + BODY, x - 1])
    if x + BODY < W: faces.append(f[y:y + BODY, x + BODY])
    for fc in faces:
        v, c = np.unique(fc, return_counts=True)
        out |= {int(a) for a, b in zip(v, c) if b >= 3}
    return out


def slide(f, n, d):
    """pushed by d from n: on, square by square, until the next square is a wall or the edge"""
    passed = [n]
    if d is None: return n, passed
    while _open(f, (n[0] + d[0], n[1] + d[1])):
        n = (n[0] + d[0], n[1] + d[1]); passed.append(n)
    return n, passed


def step_to(f, p, a, springs=(), jumps=None, blocked=frozenset()):
    """where one press takes the body, by what she has seen: (landing, squares passed) or None when it goes nowhere.
    A press she saw land somewhere is taken as seen; otherwise a plain step of 5, then the spring law if she trusts
    it for a colour on the new square's faces."""
    if (p, a) in blocked: return None
    if jumps and (p, a) in jumps:
        q = tuple(jumps[(p, a)])
        return None if q == p else (q, [q])
    dy, dx = MOVES[a]; n = (p[0] + dy, p[1] + dx)
    if not _open(f, n): return None
    return slide(f, n, spring_push(f, n, springs) if springs else None)


def reach(f, start, goal_cells, avoid_cells, max_steps=60, into_walls=False, blocked=frozenset(), springs=(), jumps=None):
    """the shortest press path for the body from start until its block covers a goal cell, never covering an avoid
    cell or a wall on the way (into_walls: the last press may go into a walled goal, as into the target box). A
    spring's slide may not cross a thing on its way (what it would do there is not known). Returns [action, ...] or None."""
    f = np.asarray(f)
    from collections import deque
    q = deque([(start, [])]); seen = {start}
    while q:
        p, path = q.popleft()
        if len(path) >= max_steps: continue
        for a, (dy, dx) in MOVES.items():
            st = step_to(f, p, a, springs, jumps, blocked)
            if st is None:
                n = (p[0] + dy, p[1] + dx)                  # a walled goal (the box) is entered by a plain step
                if into_walls and (p, a) not in blocked and _inside(f, n) and block_cells(n) & goal_cells and n != p: return path + [a]
                continue
            n, passed = st
            if any(block_cells(c) & (goal_cells | avoid_cells) for c in passed[:-1]): continue
            cells = block_cells(n)
            if cells & goal_cells and n != p: return path + [a]   # re-entering where she began counts
            if n in seen or cells & avoid_cells: continue
            seen.add(n); q.append((n, path + [a]))
    return None


def walk_end(p, path, f=None, springs=(), jumps=None, blocked=frozenset()):
    for a in path:
        st = step_to(np.asarray(f), p, a, springs, jumps, blocked) if f is not None else None
        if st is not None: p = st[0]
        else:
            dy, dx = MOVES[a]; p = (p[0] + dy, p[1] + dx)
    return p


class MoveBook:
    """HOW THE BODY MOVES, learned from her own presses (run 21). Three kinds of knowledge, white to gold:
      jumps    one square, one press, where it really landed (white: a single node, its own place)
      blocked  presses that went nowhere
      springs  the law 'a line of colour c along a face pushes away until a wall', counted per colour over every
               press that tests it; trusted when seen twice with misses under a tenth, gold when it held on two levels"""
    def __init__(s, store):
        s.d = store
        for k in ("springs", "jumps", "blocked"): s.d.setdefault(k, {})

    def springs(s):
        return [int(c) for c, e in s.d["springs"].items() if e.get("seen", 0) >= 2 and e.get("miss", 0) * 10 <= e["seen"]]

    def gold(s):
        return [int(c) for c in s.springs() if len(s.d["springs"][str(c)].get("levels", [])) >= 2]

    def jumps(s, lvl):
        return {((int(v[0]), int(v[1])), int(v[2])): (int(v[3]), int(v[4])) for v in s.d["jumps"].get(str(int(lvl)), [])}

    def blocked(s, lvl):
        return frozenset(((int(v[0]), int(v[1])), int(v[2])) for v in s.d["blocked"].get(str(int(lvl)), []))

    def learn(s, f, lvl, p, a, q):
        """one press seen: from p, action a, the body came to rest at q (f: the frame before the press)"""
        f = np.asarray(f); lvl = int(lvl); a = int(a)
        if a not in MOVES or p is None or q is None: return None
        n = (p[0] + MOVES[a][0], p[1] + MOVES[a][1])
        out = None
        if q == p:                                          # a press that went nowhere is never planned again from here
            if _inside(f, n) and (f[n[0]:n[0] + BODY, n[1]:n[1] + BODY] == 5).any():
                return None                                 # ...unless a box turned it away: that depends on the key
            b = s.d["blocked"].setdefault(str(lvl), [])     # (run 22: up into the wall from (5,14), 37 times)
            if [p[0], p[1], a] not in b: b.append([p[0], p[1], a]); s.d["blocked"][str(lvl)] = b[-300:]
            return "blocked"
        if q != n:
            jl = s.d["jumps"].setdefault(str(lvl), [])
            if not any(v[:3] == [p[0], p[1], a] for v in jl): jl.append([p[0], p[1], a, q[0], q[1]]); s.d["jumps"][str(lvl)] = jl[-300:]
            out = "jump"
        if _open(f, n):
            for c in face_colours(f, n):
                d = spring_push(f, n, [c])
                if d is None: continue
                pred, _ = slide(f, n, d)
                if pred == n: continue                     # pushed against a wall at once: the press tells nothing
                e = s.d["springs"].setdefault(str(c), {"seen": 0, "miss": 0, "levels": []})
                if pred == q:
                    e["seen"] += 1; out = f"spring {c}"
                    if lvl not in e["levels"]: e["levels"] = sorted(e["levels"] + [lvl])
                elif q == n: e["miss"] += 1
        return out


# ============================================================================================ notes (the outer shell)
def note_colours(note):
    """which of the seven colours a note fills (pool.py's meanings) and its pool: the ones still missing"""
    filled = {}
    if note.get("failed"): filled["RED"] = 1.0
    if note.get("powers"): filled["ORANGE"] = 1.0
    if note.get("ops"): filled["YELLOW"] = 1.0
    if note.get("key") and note.get("target"): filled["GREEN"] = 1.0
    if note.get("equation"): filled["CYAN"] = 1.0
    if note.get("order"): filled["BLUE"] = 1.0
    unknowns = note.get("unknowns") or []
    filled["VIOLET"] = 1.0 if not unknowns else round(1.0 / (1 + len(unknowns)), 2)
    pool = {c: round(1.0 - filled.get(c, 0.0), 2) for c in SEVEN if filled.get(c, 0.0) < 1.0}
    return filled, pool


def note_english(note):
    """the outer-shell text. A template for now; this is the LLM layer's job (translate the scene down to a note)."""
    if note.get("kind") == "solved":
        steps = "; ".join(f"touch {s_} {n} time{'s' if n != 1 else ''} ({op_text(note['ops'][s_])})" for s_, n in note["powers"].items())
        t = f"Level {note['level'] + 1}: the key ({note['key']}) must equal the target ({note['target']}). {steps}; then walk into {note['box']}."
    else:
        t = f"Level {note['level'] + 1}: the key ({note.get('key')}) and the target ({note.get('target')}) - no product of her operators reaches it."
    if note.get("outcome"): t += f" Outcome: {note['outcome']}."
    if note.get("unknowns"): t += " Still unknown: " + "; ".join(note["unknowns"]) + "."
    return t


# ============================================================================================ the mind
class CoreMind(mt.ThinkingMind):
    last = None                                        # the instance of this life (main() reads it after mm.live)

    def __init__(s, journal, log=print, mode="push"):
        super().__init__(journal, log=log, mode=mode)
        CoreMind.last = s
        s.book = NodeBook(s.j.setdefault("core_nodes", {}), s.j.get("core_ops"))
        s.mbook = MoveBook(s.j.setdefault("core_moves", {}))
        s.book.look_law = s._look_law
        s.tracks = s.j.setdefault("core_tracks", {})    # level -> look -> {lap, P, tid}: the things that move
        s.tick = {}; s.toff = {}; s.mobs = {}; s._prev_bp = None
        s.j.setdefault("notes", [])
        s.region = hud_region(s.j)
        s.prev = None; s.prev_lvl = None; s.last_frame = None; s.frame_lvl = None; s.muscle_n = {}; s.muscle_on = {}
        s.goals_seen = {}                              # level -> {id: thing}
        s.plans = {}                                   # level -> the current solution
        s.core_log = []
        s.lit = {}                                     # level -> the note that floated in and lit this level's path
        try: learn_from_saved_life(s.game, s.j, s.log)
        except Exception as e_: s.log(f"  core: could not read the last life ({str(e_)[:100]})")
        s.log(f"  core: operators she knows (by node): " +
              ("; ".join(f"level {v['level'] + 1} {v.get('tid') or 'colour ' + str(v['colour'])}: {op_text(fit(v['trans']))} (seen {v['seen']}x)" for k, v in sorted(s.book.d.items()) if v.get('trans')) or "none"))
        try: s._metals_out("her metal notes")
        except Exception as e_: s.log(f"  core: metal notes failed ({str(e_)[:100]})")
        sp_ = s.mbook.springs()
        if sp_:
            s.log(f"  core: how the body moves: a line of colour {', '.join(map(str, sp_))} along a face pushes it away to the next wall "
                  f"(seen {', '.join(str(s.mbook.d['springs'][str(c)]['seen']) for c in sp_)}x; "
                  f"{'gold - it held on levels ' + ', '.join(str(l + 1) for l in s.mbook.d['springs'][str(sp_[0])]['levels']) if s.mbook.gold() else 'white'})")

    # ------------------------------------------------------------------------------------- metal notes (tints)
    def _metals_out(s, why):
        ms = metal_notes(s.j, s.book, s.mbook)
        s.j["metal_notes"] = [{k: v for k, v in m.items() if not k.startswith("_")} for m in ms]
        s.log(f"  core: {why}: " + ("; ".join(f"{m['metal']} - {m['law_text'][:70]} ({len(m['witnesses'])} nodes, levels "
                                               f"{', '.join(map(str, m['levels']))})" for m in ms) or "none yet"))
        return ms

    def _metals1(s):
        """the single-node-or-more groups, cached until a node or a look changes"""
        sig = (tuple(sorted((k, e.get("seen", 0), len(e.get("trans", []))) for k, e in s.book.d.items())),
               sum(len(v) for v in s.j.get("core_looks", {}).values()))
        if getattr(s, "_m1_sig", None) != sig:
            s._m1_sig, s._m1 = sig, metal_notes(s.j, s.book, None, min_nodes=1)
        return s._m1

    def _look(s, lvl, tid):
        return s.j.get("core_looks", {}).get(str(int(lvl)), {}).get(tid)

    def _look_law(s, lvl, tid):
        """a law from nodes on other levels that LOOK like this thing (its shape and its colours together), before
        any law that only shares its colour (ls20 level 4: the colour-0 reshaper took the rotators' gold law)"""
        lk = s._look(lvl, tid)
        if not lk: return None
        best = None
        for m in s._metals1():
            if m.get("_op") is None or m["_op"][0] not in ("R", "F", "C", "S", "M"): continue
            hits = [w for w in m["witnesses"] if w["level"] != int(lvl) and w.get("look") and lk in look_d4(w["look"])]
            if hits and (best is None or len(hits) > best[0]): best = (len(hits), m, hits[0])
        if best is None: return None
        _, m, w = best
        return m["_op"], f"{m['metal'] if len(m['witnesses']) > 1 else 'a node'} - looks like {w['tid']} on level {w['level'] + 1}"

    def _off_tint(s, lvl, tid, op):
        """a law taken by colour, for a thing that looks like none of the nodes that hold it: (its look, theirs) or None"""
        lk = s._look(lvl, tid)
        if not lk: return None
        for m in s._metals1():
            if m.get("_op") is None or (_agrees(op, m["_op"]) is None and tuple(op) != tuple(m["_op"])): continue
            theirs = [w["look"] for w in m["witnesses"] if w["level"] != int(lvl) and w.get("look")]
            if theirs and not any(lk in look_d4(x) for x in theirs): return lk, sorted(set(theirs))
        return None

    def after_press(s, lvl, since, a, changed, surprise, nl, why):
        try: super().after_press(lvl, since, a, changed, surprise, nl, why)
        except Exception: pass
        try:                                             # the press and the frame before it, for see() to learn the move
            s._act = (int(a), s.last_frame, body_pos(s.last_frame) if s.last_frame is not None else None, int(lvl), int(since))
        except Exception: s._act = None

    # ------------------------------------------------------------------------------------- logging
    def _c(s, kind, **kw):
        s.core_log.append({"t": _now(), "kind": kind, **kw})
        try:
            os.makedirs(CORE, exist_ok=True)
            with open(os.path.join(CORE, f"{s.game}_core.jsonl"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"t": _now(), "kind": kind, **kw}, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    # ------------------------------------------------------------------------------------- the eye, every press
    def see(s, lvl, g, nl, exp_id, rel_src, why):
        lvl = int(lvl)
        s.last_frame, s.frame_lvl = np.asarray(g), (lvl if nl == lvl else int(nl))
        try: s._bar_learn(lvl, g)
        except Exception: pass
        if s.region is None: return
        now = read_glyph(g, s.region)
        bp = body_pos(g)
        act = getattr(s, "_act", None); s._act = None; s._last_forced = None
        try: s._clock(lvl, nl, bp, why, g, act)
        except Exception as e_: s.log(f"  core: the clock failed ({str(e_)[:80]})")
        fresh = act is not None and len(act) > 4 and act[4] <= 1
        if fresh:
            act = None                                   # the first press after a start, a reset or a death: the frame she
                                                         # saw last is the one before the reset (run 25), not this press's
        if nl != lvl and bp is not None:                 # the new level's first frame is its start (run 21 took the square
            s.start_pos = getattr(s, "start_pos", {})    # after the first press, and a reset was blamed on the body's own
            s.start_pos.setdefault(int(nl), bp)          # start square, '12@5,54')
            try: learn_looks(s.j, int(nl), g, bp)
            except Exception: pass
        if (act is not None and act[3] == lvl and nl == lvl and act[2] is not None and bp is not None and act[1] is not None
                and not str(why).startswith("reset") and not (bp == getattr(s, "start_pos", {}).get(lvl) and act[2] != bp)):
            try:
                r_ = s.mbook.learn(act[1], lvl, act[2], act[0], bp)
                if r_ and r_ != "blocked":
                    s._c("move", level=lvl, at=list(act[2]), a=act[0], to=list(bp), law=r_)
                    k_ = ("move", lvl, act[2], act[0])
                    if not s.muscle_on.get(k_):
                        s.muscle_on[k_] = True
                        s.log(f"  core: level {lvl + 1}: press {act[0]} from {act[2]} landed at {bp}, not one square on ({r_})")
            except Exception: pass
        if s.prev_lvl != lvl or nl != lvl or str(why).startswith("reset"):
            s.prev, s.prev_lvl = now, (lvl if nl == lvl else None)
            if s.prev_lvl is not None and lvl not in getattr(s, "start_pos", {}):
                s.start_pos = getattr(s, "start_pos", {}); s.start_pos[lvl] = bp
            if s.prev_lvl is not None:
                s.start_key = getattr(s, "start_key", {}); s.start_key.setdefault(lvl, now)
                c_ = getattr(s, "bar_colour", None)          # a full bar is what a fresh start shows (run 19 took 164 px off
                if c_ is not None:                           # the bottom band for 'full' and priced refills at 41 presses)
                    s.bar_full_px = int((np.asarray(g)[58:64] == c_).sum())
            if nl != lvl and lvl in s.plans: s._level_closed(lvl)
            return
        op = transform(s.prev, now)                      # the change, as (state before, state after)
        if not fresh and op is None and bp is not None and s.prev is not None and same(s.prev, now) and nl == lvl:
            try:                                         # a touch that changed nothing is something she knows as well
                ons_ = s._movers_on(lvl, bp)
                if len(ons_) == 1:
                    s.nochange = getattr(s, "nochange", {}); s.nochange.setdefault(lvl, set()).add((state_text(now), ons_[0]))
            except Exception: pass
        if fresh: op = None                              # play.py does not show her a reset frame: the key put back by a
                                                         # reset shows on the next press (run 27 gave it to '5@0,0')
        if op is not None and bp is not None and bp == getattr(s, "start_pos", {}).get(lvl):
            op = None                                  # a death: the body is back at the level's start and the key with it (run 12 gave that to a ring)
        if op is not None:
            things = dict(s.j.get("things", {}).get(str(lvl), {}))
            things.update(s.goals_seen.get(lvl, {}))
            sp0 = getattr(s, "start_pos", {}).get(lvl)       # the body as it stood at the start is not a thing (run 24: '9@52,24')
            if sp0 is not None:
                things = {k: v for k, v in things.items() if not (isinstance(v, dict) and v.get("box") and box_cells(v["box"]) <= block_cells(sp0))}
            ons = s._movers_on(lvl, bp)                      # a moving thing over the body (Oct 28: it is on its track now)
            things = s._sub_movers(lvl, things)
            who = ons[0] if len(ons) == 1 else None
            if len(ons) > 1: op = None                      # two at once (run 27: changer and rotator in one press): no one node's
            elif who is None: who = touched_thing(bp, things)  # what her block stands on (run 19: the body's stale experiment
            if who is None and op is not None:               # id, the changer, was given the rotator's turns)
                for cand in (exp_id, rel_src):
                    t_ = things.get(str(cand)) if cand else None
                    if cand and not str(cand).startswith("open@") and t_ and int(t_.get("n") or 99) <= 30: who = str(cand); break
            if who and op is not None:
                r = s.book.observe(who, lvl, s.prev, now)
                law = s.book.white(lvl, who)
                s._c("op", level=lvl, thing=who, change=list(op), law=op_text(law), book=r, why=why)
                if r != "again": s.log(f"  core: level {lvl + 1}: touching {who} took the key {op[0]} -> {op[1]}; its node now reads '{op_text(law)}' ({r})")
        if not same(now, s.prev) and lvl not in s.cleared:
            try: s._plan(lvl, g)                       # the key changed: she re-solves at once (run 9 waited for the next pick)
            except Exception as e_: s.log(f"  core: plan failed ({str(e_)[:120]})")
        s.prev = now

    # ------------------------------------------------------------------------------------- the equation
    def _target(s, lvl, f, things):
        """things: {id: {box [y0, x0, y1, x1], colour, n}}"""
        key = read_glyph(f, s.region) if s.region else None
        if key is None: return None, None, None
        best = None; best_off = 9.0; like = False
        ry0, ry1, rx0, rx1 = s.region
        for tid, d in things.items():
            if tid.startswith("open@"): continue
            if not d.get("box") or d.get("colour") is None or int(d.get("n") or 0) < 12: continue
            y0, x0, y1, x1 = d["box"]
            if not (y1 < ry0 or y0 > ry1 or x1 < rx0 or x0 > rx1): continue      # the HUD that holds the key is not a target
            t = read_box_glyph(f, d["box"], d["colour"])
            if t is None: continue
            # a target is a box whose glyph the key's shape can be turned into (the same shape up to turning/mirroring)
            like = any(np.rot90(key[1], k_).shape == t[1].shape and np.array_equal(np.rot90(key[1], k_), t[1]) for k_ in range(4)) or \
                   any(np.rot90(np.fliplr(key[1]), k_).shape == t[1].shape and np.array_equal(np.rot90(np.fliplr(key[1]), k_), t[1]) for k_ in range(4))
            if like: best = (tid, t); break
            if qtube_fit.on():                             # THE Q-TUBE (Nov 2): with no exact fit, aim at the box whose shape fits the key best up to a move
                try:
                    ft = qtube_fit.fit(key[1], t[1])
                    off = ft[2] if ft is not None else 9.0
                except Exception:
                    off = 9.0
                if best is None or off < best_off: best, best_off = (tid, t), off
                continue
            if best is None: best = (tid, t)            # level 4: the target's shape is one a reshape node must make
        if qtube_fit.on() and best is not None and best_off < 9.0 and not like:
            qtube_fit.note(f"no box fits the key exactly; the nearest is {best[0]}, {round(100 * best_off)}% of its cells off after the best move")
        return key, best[1] if best else None, best[0] if best else None

    def _things(s, lvl):
        """what she knows is on this level: her journal's things from earlier lives plus what the body offered this life.
        Things inside the HUD region are the key itself, never an operator (run 19 level 4 lit '14@55,3', the key's own
        glyph, as a recolour)"""
        t = {k: dict(v) for k, v in s.j.get("things", {}).get(str(lvl), {}).items() if isinstance(v, dict)}
        t.update(s.goals_seen.get(lvl, {}))
        if s.region is not None:
            ry0, ry1, rx0, rx1 = s.region
            t = {k: v for k, v in t.items() if not (v.get("box") and not (v["box"][2] < ry0 or v["box"][0] > ry1 or v["box"][3] < rx0 or v["box"][1] > rx1)
                                                    and int(v.get("n") or 0) <= 30)}
        sp = getattr(s, "start_pos", {}).get(lvl)
        if sp is not None:                               # the body as it stood at the start (run 21: '12@5,54')
            here = block_cells(sp)
            t = {k: v for k, v in t.items() if not (v.get("box") and box_cells(v["box"]) <= here)}
        return s._sub_movers(lvl, t)

    # ------------------------------------------------------------------------------------- things that move
    def _clock(s, lvl, nl, bp, why, g, act=None):
        """every press that moves the body is one tick of every moving thing; a reset or a death sets it back"""
        if nl != lvl:
            s.tick[int(nl)] = 0; s.toff[int(nl)] = {}; s._prev_bp = bp
            s._track_watch(int(nl), g); return
        pb = s._prev_bp; s._prev_bp = bp
        st = getattr(s, "start_pos", {}).get(lvl)
        if act is not None and len(act) > 4 and act[4] <= 1 and st is not None:
            # the level's first press since it began, a reset or a death (play.py counts 'since' from there): the
            # things stood at the lap's start, and so did the body
            s.tick[lvl] = 1 if (bp is not None and bp != st) else 0; s.toff[lvl] = {}
            s._track_watch(lvl, g); return
        if str(why).startswith("reset") or (bp is not None and pb is not None and bp == st and pb != st
                                            and abs(pb[0] - bp[0]) + abs(pb[1] - bp[1]) > BODY):
            s.tick[lvl] = 0; s.toff[lvl] = {}
        elif bp is not None and pb is not None and bp != pb:
            s.tick[lvl] = s.tick.get(lvl, 0) + 1
        s._track_watch(lvl, g)

    def _track_watch(s, lvl, g):
        """checks each known track against the frame (and keeps it in step), and watches looks that may move"""
        tick = s.tick.get(lvl, 0)
        tr = s.tracks.get(str(lvl), {})
        for lk, d in tr.items():
            h = find_look(g, lk)
            if len(h) != 1: continue
            lap = [tuple(x) for x in d["lap"]]; P = len(lap); off = s.toff.setdefault(lvl, {}).get(lk, 0)
            if lap[(tick + off) % P] == tuple(h[0]): continue
            cands = [d_ for d_ in range(P) if lap[(tick + d_) % P] == tuple(h[0])]
            if not cands: continue
            s.toff[lvl][lk] = min(cands, key=lambda d_: min((d_ - off) % P, (off - d_) % P))
            k_ = ("resync", lvl, lk)
            if not s.muscle_on.get(k_):
                s.muscle_on[k_] = True; s.log(f"  core: level {lvl + 1}: {lk} was not where her clock said - back in step")
        looks = s.j.get("core_looks", {}).get(str(lvl), {})
        kinds = {lk for lk in looks.values() if lk and "/" in lk and lk not in tr and lk != "bbb/b.b/bbb"}
        if not kinds: return
        ob = s.mobs.setdefault(lvl, {})
        for lk in kinds:
            h = find_look(g, lk)
            if len(h) == 1: ob.setdefault(lk, {}).setdefault(tick, h[0])
        if tick and tick % 8 == 0:
            for lk, obs in ob.items():
                if lk in tr: continue
                lap = learn_track(obs)
                if not lap: continue
                tids = [t_ for t_, l_ in looks.items() if l_ == lk]
                tid = max(tids, key=lambda t_: (s.book.d.get(f"L{lvl}:{t_}", {}).get("seen", 0), [-ord(c) for c in t_]))
                s.tracks.setdefault(str(lvl), {})[lk] = {"lap": lap, "P": len(lap), "tid": tid}
                s.log(f"  core: level {lvl + 1}: {tid} ({lk}) moves - a lap of {len(lap)} squares, one square per move of the body")

    def _mover_pos(s, lvl, lk, dt=0):
        d = s.tracks.get(str(lvl), {}).get(lk)
        if not d: return None
        lap = d["lap"]; P = len(lap)
        return tuple(lap[(s.tick.get(lvl, 0) + s.toff.get(lvl, {}).get(lk, 0) + dt) % P])

    def _movers_now(s, lvl):
        """{thing: (look, lap from now on)}: lap[0] is where it stands, lap[i] where it will be after i moves"""
        out = {}
        for lk, d in s.tracks.get(str(lvl), {}).items():
            P = len(d["lap"]); i0 = s.tick.get(lvl, 0) + s.toff.get(lvl, {}).get(lk, 0)
            out[d["tid"]] = (lk, [tuple(d["lap"][(i0 + i) % P]) for i in range(P)])
        return out

    def _sub_movers(s, lvl, t):
        """the things of a level with every moving thing replaced by one thing where it stands now"""
        tr = s.tracks.get(str(lvl), {})
        if not tr: return t
        looks = s.j.get("core_looks", {}).get(str(lvl), {})
        t = {k: v for k, v in t.items() if looks.get(k) not in tr}
        for lk, d in tr.items():
            pos = s._mover_pos(lvl, lk)
            t[d["tid"]] = {"id": d["tid"], "box": look_box_at(lk, pos), "n": len(look_cells_at(lk, pos)),
                           "colour": colour_of(d["tid"]), "moving": lk}
        return t

    def _movers_on(s, lvl, bp):
        if bp is None: return []
        here = block_cells(bp)
        return [d["tid"] for lk, d in s.tracks.get(str(lvl), {}).items() if here & look_cells_at(lk, s._mover_pos(lvl, lk))]

    def _plan(s, lvl, f, things=None):
        if s.region is None or lvl in s.cleared or (lvl in s.routes and lvl not in s.route_off): return None
        things = things if things is not None else s._things(lvl)
        key, target, box = s._target(lvl, f, things)
        if key is None or target is None: return None
        # the target box and what stands in it are the answer, never operators (run 23, level 5: the target glyph
        # '8@6,55' took the changer's colour-8 law, and the box itself was probed as a part of it)
        bb = (things.get(box) or {}).get("box")
        def _in_box(v):
            b = v.get("box")
            return bool(bb and b and b[0] >= bb[0] - 1 and b[1] >= bb[1] - 1 and b[2] <= bb[2] + 1 and b[3] <= bb[3] + 1)
        rings_ = set(s._rings(lvl, things, f))           # a refill is a refill (run 24 gave a ring the turn of a rotator passing by)
        boxlike = lambda k, v: colour_of(k) == 5 and int(v.get("n") or 0) >= 12 and v.get("box") and \
            v["box"][2] - v["box"][0] <= 12 and v["box"][3] - v["box"][1] <= 12          # another box (run 26 probed level 6's
        rects = [v["box"] for k, v in things.items() if boxlike(k, v)]                  # first box after it took the key, and
        in_any = lambda v: bool(v.get("box")) and any(v["box"][0] >= r[0] - 1 and v["box"][1] >= r[1] - 1 and   # its glyph)
                                                      v["box"][2] <= r[2] + 1 and v["box"][3] <= r[3] + 1 for r in rects)
        ops, srcs = s.book.for_level({k: v for k, v in things.items() if k != box and not _in_box(v) and k not in rings_
                                      and not boxlike(k, v) and not in_any(v)}, lvl)
        first = []                                       # laws taken by colour for things that look like none of their nodes
        for t_, op_ in ops.items():
            if str(srcs.get(t_, "white")).startswith("white") or "looks like" in str(srcs.get(t_)): continue
            ot = s._off_tint(lvl, t_, op_)
            if ot:
                srcs[t_] = f"{srcs[t_]}; off-tint: it looks like {ot[0]}, the law's nodes look like {', '.join(ot[1])}"
                first.append(t_)
        seq = solve(key, target, ops)
        plan = {"level": lvl, "key": key, "target": target, "box": box, "ops": ops, "srcs": srcs, "seq": seq, "t": _now(),
                "probe_first": first}
        # what she cannot yet predict: a lit node whose law says nothing about the key as it is now (a missing colour
        # to fill by touching it once - the note is not gospel)
        plan["probe"] = [t_ for t_, op_ in ops.items() if apply(op_, key) is None]
        plan["probe"] = [t_ for t_ in first if t_ in plan["probe"]] + [t_ for t_ in plan["probe"] if t_ not in first]
        if seq is None:
            # no product reaches the target: a law she carried in from elsewhere (gold or a hint) may not be this
            # node's job here (run 21: colour 0 turned on levels 1-3 and reshapes on level 4). Touch those once too.
            plan["probe"] += [t_ for t_ in ops if t_ not in plan["probe"] and not str(srcs.get(t_, "white")).startswith("white")]
            plan["probe"] = [t_ for t_ in plan["probe"] if t_ in first] + [t_ for t_ in plan["probe"] if t_ not in first]
        if seq is None:
            plan["equation"] = None
        else:
            plan["equation"] = equation_text(seq, ops)
            # THE ORDER (blue): recolours first, then the turns, because the body's relation loop walks into the box as
            # soon as the SHAPES match and the box only takes the key when the colour matches too
            colour_first = [x for x in seq if ops[x][0] in ("C", "RC")]
            plan["next"] = (colour_first or seq or [None])[0]
            plan["colour_ok"] = key[0] == target[0]
        old = s.plans.get(lvl)
        s.plans[lvl] = plan
        sk = getattr(s, "start_key", {}).get(lvl)
        if seq is not None and (sk is None or same(sk, key) or lvl not in getattr(s, "level_eq", {})):
            s.level_eq = getattr(s, "level_eq", {})          # the equation as solved from the level's start key: the note
            s.level_eq[lvl] = dict(plan)                     # carries this, not the last step's 'walk into the box'
        sig = (plan["equation"], key[0], shape_text(key[1]))
        if old is None or (old.get("equation"), old["key"][0], shape_text(old["key"][1])) != sig:
            if plan["equation"]:
                s.log(f"  core: level {lvl + 1}: key colour {key[0]} [{shape_text(key[1])}] -> target colour {target[0]} [{shape_text(target[1])}] in {box}; "
                      f"{plan['equation']}; next: {plan['next'] or 'walk into ' + box} | nodes: " +
                      ", ".join(f"{k_}={op_text(v_)} ({srcs.get(k_)})" for k_, v_ in ops.items()))
            else:
                s.log(f"  core: level {lvl + 1}: key colour {key[0]} [{shape_text(key[1])}] -> target colour {target[0]} [{shape_text(target[1])}] in {box}; "
                      f"no product of her operators reaches it ({', '.join(f'{k}={op_text(v)} ({srcs.get(k)})' for k, v in ops.items()) or 'none known here'})"
                      + (f"; she will probe {', '.join(plan['probe'])} to fill what is missing" if plan.get("probe") else ""))
            s._c("plan", level=lvl, key=[key[0], shape_text(key[1])], target=[target[0], shape_text(target[1])], box=box,
                 equation=plan["equation"], seq=seq, ops={k: list(v) for k, v in ops.items()})
            s._float_in(lvl, plan)
        return plan

    def _float_in(s, lvl, plan):
        """a note from an earlier life about this level floats into her view: does it light the same path?"""
        if lvl in s.lit: return
        mine = [n for n in s.j["notes"] if n.get("game") == s.game and n.get("level") == lvl and n.get("equation")]
        if not mine: return
        n = mine[-1]; s.lit[lvl] = n
        lights = n.get("equation") == plan.get("equation")
        s._c("float_in", level=lvl, note_equation=n.get("equation"), now_equation=plan.get("equation"), same_path=lights, pool=n.get("pool"))
        s.log(f"  core: level {lvl + 1}: a note from {n.get('t', '?')} floats in - {'it lights the same path' if lights else 'it lights a different path: ' + str(n.get('equation'))}"
              f"; its missing colours: {', '.join(n.get('pool', {}).keys()) or 'none (white)'}")

    # ------------------------------------------------------------------------------------- the body's hooks
    def order(s, goals, lvl, f):
        lvl = int(lvl)
        s.goals_seen.setdefault(lvl, {}).update({str(g["id"]): mm.describe(g, f) for g in goals})
        try: plan = s._plan(lvl, f)
        except Exception as e_:
            plan = None; s.log(f"  core: plan failed ({str(e_)[:120]})")
        new = super().order(goals, lvl, f)
        if not plan or plan.get("seq") is None: return new
        # KEEP OFF what would undo the work: a thing whose operator takes the key further from the target goes last
        parts = s.book.parts(s._things(lvl), lvl); need = len(plan["seq"]); away = []
        for g in new:
            op = parts.get(str(g["id"]))
            if not op: continue
            after = apply(op, plan["key"])
            if after is None:
                # its effect on this key is unknown; if it recolours and the colour is already right, it can only risk it
                if op[0] in ("C", "RC") and plan.get("colour_ok") and str(g["id"]) != plan.get("next"): away.append(g)
                continue
            rest = solve(after, plan["target"], plan["ops"])
            if (rest is None or len(rest) + 1 > need) and str(g["id"]) != plan.get("next"): away.append(g)
        if away:
            new = [g for g in new if g not in away] + away
            if not getattr(s, "_away_logged", {}).get((lvl, tuple(sorted(str(g["id"]) for g in away)), plan["key"][0])):
                s._away_logged = getattr(s, "_away_logged", {}); s._away_logged[(lvl, tuple(sorted(str(g["id"]) for g in away)), plan["key"][0])] = True
                s.log(f"  core: level {lvl + 1}: she keeps the body off {', '.join(str(g['id']) for g in away)} for now (it would undo the work)")
                s._c("keep_off", level=lvl, things=[str(g["id"]) for g in away])
        want = plan["next"] if plan["seq"] else plan["box"]
        if want is None: return new
        first = [g for g in new if str(g["id"]) == want]
        if not first:                                     # the thing's other part: a changer the body sees as two colours side by side
            wb = s._things(lvl).get(want, {}).get("box")
            if wb:
                for g in new:
                    gb = s.goals_seen.get(lvl, {}).get(str(g["id"]), {}).get("box")
                    if gb and not str(g["id"]).startswith("open@") and abs(gb[0] - wb[0]) <= 2 and abs(gb[1] - wb[1]) <= 2:
                        first = [g]; want = str(g["id"]); break
        if not first: return new
        out = first + [g for g in new if str(g["id"]) != want]
        if str(new[0]["id"]) != want:
            op_ = plan["ops"].get(want) or s.book.parts(s._things(lvl), lvl).get(want)
            s.log(f"  core: level {lvl + 1}: she sends the body to {want} ({'the box' if want == plan['box'] else (op_text(op_) if op_ else '?')})")
            s._c("send", level=lvl, to=want)
        return out

    def allow_relation(s, lvl, r, reset=False):
        lvl = int(lvl)
        # the loop is asked for before the body has offered her a single choice on the level: she looks at the frame
        # she saw last (her eye, every press) with the things her journal knows are here
        if getattr(s, "last_frame", None) is not None and s.frame_lvl == lvl:
            try: s._plan(lvl, s.last_frame)
            except Exception as e_: s.log(f"  core: plan failed ({str(e_)[:120]})")
        plan = s.plans.get(lvl)
        if plan and plan.get("seq") is not None:
            # the loop may run only on a TURNING source, and only once the colour is right (run 8: with the colour right
            # the body found a second loop, 'touch the changer until it matches', and its first touch took 9 back to 12)
            src = r.get("src") if isinstance(r, dict) else None
            src = src.get("id") if isinstance(src, dict) else src
            turners = {colour_of(t) for t, op in plan["ops"].items() if op[0] in ("R", "F")}
            if colour_of(src) not in turners:
                s._c("refuse", level=lvl, src=src)
                return False
            ok = bool(plan.get("colour_ok"))
            if not ok and not getattr(s, "_held", {}).get(lvl):
                s._held = getattr(s, "_held", {}); s._held[lvl] = True
                s.log(f"  core: level {lvl + 1}: she holds the body's relation loop until the key's colour is right (the loop only turns it)")
                s._c("hold", level=lvl)
            if ok and getattr(s, "_held", {}).get(lvl):
                s._held[lvl] = False
                s.log(f"  core: level {lvl + 1}: the colour is right - the body's loop may turn the key and walk it in")
                s._c("release", level=lvl)
            return ok
        return super().allow_relation(lvl, r, reset)

    def want_carried(s, lvl, rels=None):
        """play.py asks: offer the relation carried from the last level even though one was found on this level? Yes when
        her equation needs a turn (run 10: the body found 'touch the changer until...' and dropped the carried rotator,
        the one loop that can turn the key)"""
        plan = s.plans.get(int(lvl))
        return bool(plan and plan.get("seq") and any(plan["ops"][x][0] in ("R", "F") for x in plan["seq"]))

    def press(s, lvl, since):
        """HER OWN HANDS for an exact touch. The body's experiment pushes into a thing up to three times (the insert takes
        three) and a changer counts every entry: run 10 took the key 12 -> 9 -> 12 in four seconds. When her equation
        needs a recolour she walks the body there herself, enters once, and lets the body lead again."""
        r = super().press(lvl, since)
        if r is not None: return r
        try: return s._muscle(int(lvl))
        except Exception as e_:
            s.log(f"  core: her hands failed ({str(e_)[:120]})"); return None

    def sense(s, lvl, rem, margin, since):
        super().sense(lvl, rem, margin, since)
        try:                                           # a full bar is what the register reads at a fresh start (run 14
            if rem is not None and int(since) <= 1:    # took a one-off 42 as 'full' and planned routes the bar could not pay)
                s.bar_full = getattr(s, "bar_full", {}); s.bar_full[int(lvl)] = float(rem); s.bar_cap = float(rem)
            # what one press really costs in the register's units (run 15: the plan priced 1 a press, the bar fell ~2)
            pe, ps = getattr(s, "_pe", None), getattr(s, "_ps", None)
            if rem is not None and pe is not None and ps is not None and int(since) == ps + 1 and 0 < pe - float(rem) <= 6:
                s.drain = 0.7 * getattr(s, "drain", 1.0) + 0.3 * (pe - float(rem))
            s._pe, s._ps = (float(rem) if rem is not None else None), int(since)
        except Exception: pass

    def _groups(s, lvl, things):
        """every thing with an operator, its other parts merged in (a changer the body sees as two colours)"""
        parts = s.book.parts(things, lvl); groups = {}; rep_of = {}
        for tid in parts:
            b = things.get(tid, {}).get("box")
            if not b: continue
            rep = next((r for r in groups if all(abs(things[r]["box"][i] - b[i]) <= 2 for i in range(4))), tid)
            groups.setdefault(rep, set()).update(box_cells(b)); rep_of[tid] = rep
        return parts, groups, rep_of

    def bar_now(s, f):
        """the bar in presses, read off the frame: the refill things' colour in the bottom band, divided by what one press
        costs (run 18: the body's own budget estimate read 11 where the bar held 14, and 'no route fits' handed the
        level back to the body's resets). None until she knows the colour."""
        c = getattr(s, "bar_colour", None)
        if c is None: return None
        px = int((np.asarray(f)[58:64] == c).sum())
        d = getattr(s, "bar_drain", None) or 4.0
        return px / d

    def _bar_learn(s, lvl, g):
        if getattr(s, "bar_colour", None) is None:       # the refills' colour, from any level she has seen one refill on
            for (lv_, tid) in sorted(set(getattr(s, "refill_ids", set())) |
                                     {(lv_, t_) for lv_, d_ in s.results.items() for t_, r_ in d_.items() if "refill" in r_}):
                if colour_of(tid) is not None: s.bar_colour = int(colour_of(tid)); break
        c = getattr(s, "bar_colour", None)
        if c is None: return
        px = int((np.asarray(g)[58:64] == c).sum()); pp = getattr(s, "_bar_px", None)
        if pp is not None and 0 < pp - px <= 12 and getattr(s, "_bar_lvl", None) == lvl:
            # the drain is the level's own (ls20: 4 px a press on level 3, 2 on level 4); until this level shows a drop,
            # the last level's drain stands, which can only make her plan too careful, never too bold
            d_ = getattr(s, "_drops_lvl", {}); hist = d_.setdefault(lvl, []); hist.append(pp - px); d_[lvl] = hist[-30:]
            s._drops_lvl = d_
            s.bar_drain = float(sorted(d_[lvl])[len(d_[lvl]) // 2])
        if not getattr(s, "bar_full_px", 0): s.bar_full_px = px
        s._bar_px = px; s._bar_lvl = lvl

    def _ring_kinds(s, lvl):
        """(colour, size) of things that refilled the bar on OTHER levels, with the levels: a refill law that holds on
        two levels is gold (several nodes, one job), and a thing of that colour and size on a new level is a ring until
        its first touch says otherwise (ls20 level 4: neither ring had refilled yet, both look like levels 2-3's)"""
        kinds = {}
        seen = set(getattr(s, "refill_ids", set())) | {(lv_, t_) for lv_, d_ in s.results.items() for t_, r_ in d_.items() if "refill" in r_}
        for (lv_, tid) in seen:
            if int(lv_) == int(lvl) or colour_of(tid) is None: continue
            t = s.j.get("things", {}).get(str(lv_), {}).get(tid) or {}
            kinds.setdefault((int(colour_of(tid)), int(t.get("n") or 0)), set()).add(int(lv_))
        return kinds

    def _rings(s, lvl, things, f):
        """the refills still standing on the board (things that gave 'refill', their colour still showing; on a level
        where none has refilled yet, things of a refill's colour and size from other levels)"""
        out = {}
        kinds = s._ring_kinds(lvl)
        here = any("refill" in list(s.results.get(lvl, {}).get(t_, [])) + list(s.life_res.get(lvl, {}).get(t_, []))
                   or (lvl, t_) in getattr(s, "refill_ids", set()) for t_ in things)
        for tid, t in things.items():
            res = list(s.results.get(lvl, {}).get(tid, [])) + list(s.life_res.get(lvl, {}).get(tid, []))
            known = "refill" in res or (lvl, tid) in getattr(s, "refill_ids", set())
            like = (not here and colour_of(tid) is not None and (int(colour_of(tid)), int(t.get("n") or 0)) in kinds
                    and not str(tid).startswith("open"))
            if not known and not like: continue
            b = t.get("box"); c = colour_of(tid)            # the id keeps the thing's own colour; the journal's 'colour' is
            if not b or c is None: continue                  # whatever stood there when last described (a used ring reads 3)
            y0, x0, y1, x1 = b
            if (np.asarray(f)[y0:y1 + 1, x0:x1 + 1] == int(c)).sum() >= max(1, int(t.get("n") or 1) // 2): out[tid] = box_cells(b)
        return out

    def _best_route(s, lvl, f, pos, legs, groups, things, reserve=0):
        """THE ROUTE (blue + orange + red): the touches the equation asks for, in order, then the box, with the
        refills slotted in wherever the bar would run out. Every order of refills is priced; the shortest that never
        empties the bar wins. Returns (total, first leg, the stops) or None."""
        import itertools
        rings = s._rings(lvl, things, f)
        rem = s.bar_now(f)
        if rem is None: rem = getattr(s, "energy", None)
        cap = (getattr(s, "bar_full_px", 0) / (getattr(s, "bar_drain", None) or 4.0)) if getattr(s, "bar_full_px", 0) else (getattr(s, "bar_cap", None) or rem)
        s._last_rem, s._last_cap, s._last_rings = rem, cap, list(rings)
        allcells = set().union(*groups.values()) if groups else set()
        boxcells = set(); f_box = f
        # every box's grey is floor to the body (run 25's frames: it stood at (30,54), one row into level 6's first box);
        # only a box's middle is 'entering' it, and that is for the box she is going to, with the key right
        f = np.array(f, copy=True); mids = {}
        ry0, ry1, rx0, rx1 = s.region if s.region else (99, -1, 99, -1)
        for tid_, t_ in things.items():
            b_ = t_.get("box")
            if not b_ or colour_of(tid_) != 5 or int(t_.get("n") or 0) < 12 or b_[2] - b_[0] > 12 or b_[3] - b_[1] > 12: continue
            if not (b_[2] < ry0 or b_[0] > ry1 or b_[3] < rx0 or b_[1] > rx1): continue
            sub = f[b_[0]:b_[2] + 1, b_[1]:b_[3] + 1]; sub[sub == 5] = 3
            mids[tid_] = ((b_[0] + b_[2]) // 2, (b_[1] + b_[3]) // 2)
        if legs and legs[-1][0] == "box" and things.get(legs[-1][1], {}).get("box"):
            # the box is entered, not touched: the body has to stand over its middle (run 22 stood on its grey edge at
            # (5,14), read that as 'in the box', and pressed up into the wall 37 times). Its grey is floor to the body.
            y0, x0, y1, x1 = things[legs[-1][1]]["box"]
            boxcells = {((y0 + y1) // 2, (x0 + x1) // 2)}
            f_box = np.array(f, copy=True); sub = f_box[y0:y1 + 1, x0:x1 + 1]; sub[sub == 5] = 3
        other_mids = {c_ for t_, c_ in mids.items() if not (legs and legs[-1][0] == "box" and t_ == legs[-1][1])}
        allcells = allcells | other_mids
        cache = {}
        bl, sp_, jm = s.mbook.blocked(lvl), s.mbook.springs(), s.mbook.jumps(lvl)
        mv = s._movers_now(lvl)                         # the things that move: met by place and tick (Oct 28)
        still = (set().union(*[c for k_, c in groups.items() if k_ not in mv]) if groups else set()) | other_mids
        import math
        Lm = 1
        for _, lap_ in mv.values(): Lm = Lm * len(lap_) // math.gcd(Lm, len(lap_))
        def leg_path(p, t, kind, target):
            k = (p, t % Lm, kind, target)
            if k not in cache:
                ac, st_ = allcells | boxcells, still | boxcells        # the box's middle is for the last leg only
                if not mv:
                    if kind == "ring": cache[k] = reach(f, p, rings[target], ac, 70, blocked=bl, springs=sp_, jumps=jm)
                    elif kind == "box": cache[k] = reach(f_box, p, boxcells, allcells, 70, blocked=bl, springs=sp_, jumps=jm)
                    else: cache[k] = reach(f, p, groups[target], ac - groups[target], 70, blocked=bl, springs=sp_, jumps=jm)
                elif kind == "ring": cache[k] = reach_timed(f, p, t, rings[target], st_, mv, None, 70, blocked=bl, springs=sp_, jumps=jm)
                elif kind == "box": cache[k] = reach_timed(f_box, p, t, boxcells, still, mv, None, 70, blocked=bl, springs=sp_, jumps=jm)
                elif target in mv: cache[k] = reach_timed(f, p, t, set(), st_, mv, target, 70, blocked=bl, springs=sp_, jumps=jm)
                else: cache[k] = reach_timed(f, p, t, groups[target], st_ - groups[target], mv, None, 70, blocked=bl, springs=sp_, jumps=jm)
            return cache[k]
        ring_ids = list(rings)[:3]
        best = None
        for combo in itertools.product([None] + list(range(len(legs))), repeat=len(ring_ids)):
            seq = []
            for i, leg in enumerate(legs):
                seq += [("ring", r_) for r_, at in zip(ring_ids, combo) if at == i]
                seq.append(leg)
            p = pos; tk = 0; bar = rem if rem is not None else 999.0; total = 0; first = None; ok = True
            for kind, target in seq:
                path = leg_path(p, tk, kind, target)
                if path is None: ok = False; break
                if first is None: first = (kind, target, path)
                bar -= len(path); total += len(path)               # the register counts presses (84 px / 4 a press)
                # a ring refills on entry and the box ends the level: both may be reached on the last press of the bar
                # (the body's own detours do it: 'ring 11@51,40 is 1 away, budget 2' -> REFILL); a touch must leave one
                if bar < (0 if kind in ("box", "ring") else 1): ok = False; break
                p = walk_end(p, path, f, sp_, jm, bl); tk += len(path)
                if kind == "ring" and cap: bar = cap
            if ok and first and bar < reserve and seq[-1][0] != "ring": ok = False   # a probe (or a first box) keeps bar to go on
            if ok and first and (best is None or total < best[0]): best = (total, first, seq)
        return best

    def _muscle(s, lvl):
        """her hands walk the whole solution: each touch exactly once per entry (the exponent is the number of entries),
        refills where the bar needs them, the box last. Re-planned from the frame on every press."""
        plan = s.plans.get(lvl)
        if not plan or s.frame_lvl != lvl or s.last_frame is None: return None
        n = s.muscle_n.get(lvl, 0)
        if n >= 400: return None
        f = s.last_frame; pos = body_pos(f)
        if pos is None: return None
        things = s._things(lvl)
        if not things.get(plan["box"], {}).get("box"): return None
        bt_ = things[plan["box"]]
        cy_, cx_ = (bt_["box"][0] + bt_["box"][2]) // 2, (bt_["box"][1] + bt_["box"][3]) // 2
        mid_ = {(cy_ + dy_, cx_ + dx_) for dy_ in (-1, 0, 1) for dx_ in (-1, 0, 1)}
        if not (block_cells(pos) & mid_) and not np.isin(np.asarray(f)[cy_ - 1:cy_ + 2, cx_ - 1:cx_ + 2], [3, 5], invert=True).any():
            # the box shows no glyph any more: it took the key (ls20 level 6 has two boxes; run 24 kept walking in and
            # out of the first one after it had vanished, 12 presses, until the bar ran out). Solve again from the frame.
            old_box = plan["box"]
            try: s._plan(lvl, f)
            except Exception: return None
            plan = s.plans.get(lvl)
            if not plan or plan.get("box") == old_box: return None
            s.log(f"  core: level {lvl + 1}: {old_box} took the key - the next box is {plan['box']}")
            if not things.get(plan["box"], {}).get("box"): return None
        bb = things[plan["box"]]["box"]                 # the box and its glyph are the destination, not parts to avoid
        parts, groups, rep_of = s._groups(lvl, {k: v for k, v in things.items() if k != plan["box"] and not v.get("moving") and not (
            v.get("box") and v["box"][0] >= bb[0] - 1 and v["box"][1] >= bb[1] - 1 and v["box"][2] <= bb[2] + 1 and v["box"][3] <= bb[3] + 1)})
        for mid, (lk_, lap_) in s._movers_now(lvl).items():   # a moving thing is its own group, where it stands now
            groups[mid] = look_cells_at(lk_, lap_[0]); rep_of[mid] = mid
        if plan.get("seq") is None:
            # no product of what she knows reaches the target: touch the node whose effect on this key she has not
            # seen yet, once, and solve again with what it shows her (filling a missing colour before trusting)
            s.probed = getattr(s, "probed", set())
            here_ = block_cells(pos)
            for t in plan.get("probe") or []:                # standing in it is the touch: it is probed for this key
                r_ = rep_of.get(t, t)
                if r_ in groups and here_ & groups[r_]: s.probed.add((lvl, r_, state_text(plan["key"])))
            probes = [rep_of.get(t, t) for t in plan.get("probe") or [] if rep_of.get(t, t) in groups
                      and (lvl, rep_of.get(t, t), state_text(plan["key"])) not in s.probed]
            if not probes:
                fr_ = frontier(plan["key"], plan["ops"], skip=frozenset(getattr(s, "nochange", {}).get(lvl, set())))
                if not fr_: return None
                path_, node_ = fr_
                legs = [("touch", rep_of.get(t, t)) for t in path_ + [node_] if rep_of.get(t, t) in groups]
                if not legs: return None
                k_ = ("edge", lvl, state_text(plan["key"]), tuple(path_), node_)
                if not s.muscle_on.get(k_):
                    s.muscle_on[k_] = True
                    s.log(f"  core: level {lvl + 1}: nothing she knows reaches the target; she goes to the edge of what she knows - "
                          f"{' . '.join(path_)} then {node_}, whose effect on that key is not known yet")
            else:
                legs = [("touch", probes[0])]
            if probes and not s.muscle_on.get(("probe", lvl, probes[0], state_text(plan["key"]))):
                s.muscle_on[("probe", lvl, probes[0], state_text(plan["key"]))] = True
                s.log(f"  core: level {lvl + 1}: she probes {probes[0]} - what it does to key {state_text(plan['key'])} is not known yet")
        else:
            recol = [t for t in plan["seq"] if plan["ops"][t][0] in ("C", "RC")]
            turns = [t for t in plan["seq"] if plan["ops"][t][0] not in ("C", "RC")]
            order_ = recol + turns
            pf = [t for t in plan.get("probe_first") or [] if t in order_]
            if pf:                                       # an off-tint law is checked first: one touch, then she solves again
                order_.remove(pf[0]); order_ = [pf[0]] + order_
                k_ = ("tint", lvl, pf[0], state_text(plan["key"]))
                if not s.muscle_on.get(k_):
                    s.muscle_on[k_] = True
                    s.log(f"  core: level {lvl + 1}: {pf[0]} goes first - it does not look like the nodes its law came from")
            legs = [("touch", rep_of.get(t, t)) for t in order_ if rep_of.get(t, t) in groups] + [("box", plan["box"])]
        # a level with another box still showing: the bar should not be spent to the last press on this one (run 28:
        # the first box took the key with 2 presses left, and the reset that followed put it back)
        more = any(k_ != plan["box"] and colour_of(k_) == 5 and int(v_.get("n") or 0) >= 12 and v_.get("box")
                   and v_["box"][2] - v_["box"][0] <= 12 and v_["box"][3] - v_["box"][1] <= 12
                   and read_box_glyph(f, v_["box"], 5) is not None for k_, v_ in things.items())
        res_ = 10 if plan.get("seq") is None else (15 if more else 0)
        best = s._best_route(lvl, f, pos, legs, groups, things, reserve=res_)
        if best is None and res_:
            best = s._best_route(lvl, f, pos, legs, groups, things)
        if best is None:
            # no whole route fits, but a standing ring within the bar is still the only way on (run 17: she stopped one
            # press short of a ring and the body reset the level, 19 presses at a time)
            rings = s._rings(lvl, things, f); rem = s.bar_now(f)
            if rem is None: rem = getattr(s, "energy", None)
            allc = set().union(*groups.values()) if groups else set()
            near = None
            for rid, rc in rings.items():
                pth = reach(f, pos, rc, allc, 30, blocked=s.mbook.blocked(lvl), springs=s.mbook.springs(), jumps=s.mbook.jumps(lvl))
                if pth and (rem is None or len(pth) <= rem + 1) and (near is None or len(pth) < len(near[1])): near = (rid, pth)
            if near:
                s._c("hands", level=lvl, step="ring-rescue", to=near[0], a=near[1][0], left=len(near[1]))
                s.muscle_n[lvl] = n + 1
                return (near[1][0], -1, -1)
            # no safe route on this bar: if she is standing in a changer with the colour right, she still steps out
            here = block_cells(pos)
            if plan.get("colour_ok") and any(here & groups[rep_of.get(t, t)] for t in plan["ops"] if plan["ops"][t][0] in ("C", "RC") and rep_of.get(t, t) in groups):
                for a in (1, 3, 4, 2):
                    st = step_to(np.asarray(f), pos, a, s.mbook.springs(), s.mbook.jumps(lvl), s.mbook.blocked(lvl))
                    if st is None: continue
                    if any(block_cells(c_) & g_ for c_ in st[1] for g_ in groups.values()): continue
                    s._c("hands", level=lvl, step="out", a=a); s.muscle_n[lvl] = n + 1
                    return (a, -1, -1)
            s._c("hands", level=lvl, step="none", bar=getattr(s, "_last_rem", None), rings=getattr(s, "_last_rings", None), body=list(pos))
            if not s.muscle_on.get(("none", lvl)):
                s.muscle_on[("none", lvl)] = True
                s.log(f"  core: level {lvl + 1}: no route fits the bar from here ({getattr(s, 'energy', None)} left) - the body leads")
            return None
        total, (kind, target, path), seq = best
        sig = tuple(seq)
        if s.muscle_on.get(lvl) != sig:
            s.muscle_on[lvl] = sig
            s.log(f"  core: level {lvl + 1}: her own hands - {total} presses: " + " -> ".join(f"{k_}:{t_}" for k_, t_ in seq) +
                  f" (bar {getattr(s, 'energy', None)}, full {getattr(s, 'bar_cap', None)})")
            s._c("route", level=lvl, total=total, stops=[list(x) for x in seq], bar=getattr(s, "_last_rem", None),
                 full=getattr(s, "_last_cap", None), rings=getattr(s, "_last_rings", None), body=list(pos))
        s.muscle_n[lvl] = n + 1
        s._c("hands", level=lvl, step=kind, to=target, a=path[0], left=len(path), bar=getattr(s, "_last_rem", None), body=list(pos))
        if kind != "box" and len(path) > 1: s._last_forced = (pos, path[0], lvl)   # a move that should go somewhere
        return (path[0], -1, -1)

    def _maybe_think(s, goals, lvl, f):
        plan = s.plans.get(int(lvl))
        if plan and plan.get("seq") is not None: return          # her core knows what to do here; no shell call
        return super()._maybe_think(goals, lvl, f)

    # ------------------------------------------------------------------------------------- notes
    def _level_closed(s, lvl):
        plan = s.plans.get(lvl)
        if not plan or plan.get("_noted"): return
        plan["_noted"] = True
        whole = getattr(s, "level_eq", {}).get(lvl) or plan
        s._write_note(whole, outcome="held: the level cleared")

    def _write_note(s, plan, outcome):
        lvl = plan["level"]
        unknowns = []
        if not str(outcome).startswith("held"):         # run 24 wrote a white note for a level it never finished
            unknowns.append("whether the path holds: it was not walked to the end")
        used = set(plan.get("seq") or [])
        for src, op in plan["ops"].items():
            if src not in used: continue
            where = (plan.get("srcs") or {}).get(src, "white")
            if where != "white": unknowns.append(f"whether {src} on this level really does '{op_text(op)}' ({where}, not yet seen here)")
            if op[0] in ("C", "S", "M") and isinstance(op[1], dict) and len(op[1]) < 2:
                a_, b_ = next(iter(op[1].items()))
                unknowns.append(f"what a second touch of {src} does (only {a_} -> {b_} seen)")
            if op[0] == "RC": unknowns.append(f"what {src} does to colours other than {op[2]}")
        note = {"t": _now(), "game": s.game, "level": lvl, "kind": "solved" if plan.get("seq") is not None else "unsolved",
                "key": f"colour {plan['key'][0]} {shape_text(plan['key'][1])}", "target": f"colour {plan['target'][0]} {shape_text(plan['target'][1])}",
                "box": plan["box"], "equation": plan.get("equation"), "powers": powers(plan.get("seq") or []),
                "ops": {k: list(v) for k, v in plan["ops"].items()}, "nodes": dict(plan.get("srcs") or {}),
                "order": "recolour first, then turn, then the box",
                "failed": s._failed(lvl, plan["box"]), "outcome": outcome, "unknowns": unknowns,
                "path": {"region": list(s.region), "box": plan["box"], "ops": {k: list(v) for k, v in plan["ops"].items()}}}
        note["colours"], note["pool"] = note_colours(note)
        note["text"] = note_english(note)
        s.j["notes"] = (s.j["notes"] + [note])[-100:]
        s._c("note", note={k: v for k, v in note.items() if k != "path"})
        s.log(f"  core: note -> outer shell: {note['text']}")
        s.log(f"  core: the note fills {', '.join(note['colours'])}; its pool (what she should find out before trusting it): "
              f"{', '.join(f'{c} - {MEANING[c]}' for c in note['pool']) or 'none - white'}")

    def _failed(s, lvl, box):
        """RED, from her own record: what walking into the box gave when the key was not right"""
        past = list(s.results.get(lvl, {}).get(box, [])) + list(s.life_res.get(lvl, {}).get(box, []))
        cnt = {}
        for x in past:
            if x in mm.DEAD or x == "untestable": cnt[x] = cnt.get(x, 0) + 1
        return [f"walking into {box} gave '{k}' {v} time{'s' if v != 1 else ''}" for k, v in cnt.items()]

    def finish(s):
        """end of life: a plan that never closed its level still goes out as a note, with what failed"""
        try: s._metals_out("metal notes at the end of the life")
        except Exception as e_: s.log(f"  core: metal notes failed ({str(e_)[:100]})")
        for lvl, plan in s.plans.items():
            if plan.get("_noted") or lvl in s.cleared: continue
            if plan.get("seq") is None: s._write_note(plan, outcome="no product of her operators reaches the target")
            else: s._write_note(plan, outcome="not reached this life")
            plan["_noted"] = True


# ============================================================================================ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game", nargs="?", default="ls20")
    ap.add_argument("--lives", type=int, default=1)
    ap.add_argument("--presses", default="400")
    ap.add_argument("--shell", default="none", help="an Ollama model for imagination when her core has no plan, or 'none'")
    ap.add_argument("--no-reflect", action="store_true")
    ap.add_argument("--mode", default="push", choices=["push", "study"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--learn", action="store_true", help="only read the last saved life and print what she learns")
    ap.add_argument("--notes", action="store_true")
    a = ap.parse_args()
    if a.notes:
        j = mm.load_journal(a.game)
        for n in j.get("notes", [])[-10:]: print(f"[{n['t']}] {n['text']}\n    path: {n.get('equation')} | pool: {list(n.get('pool', {}))}")
        return
    if a.learn:
        j = mm.load_journal(a.game); j.setdefault("game", a.game)
        out = learn_from_saved_life(a.game, j)
        print(json.dumps(out, indent=1))
        for k, v in sorted(j.get("core_nodes", {}).items()): print(k, op_text(fit(v["trans"])), "seen", v["seen"])
        return
    os.makedirs(CORE, exist_ok=True)
    mt.ThinkingMind.shell = None if a.shell.lower() == "none" else a.shell
    mt.ThinkingMind.tlog_path = os.path.join(mt.THINK, f"{a.game}_{time.strftime('%Y%m%d_%H%M%S')}_core_{a.shell.replace(':', '-')}.jsonl")
    mm.MikaMind = CoreMind
    presses = 0 if str(a.presses).lower() == "auto" else int(a.presses)
    rows = mm.live(a.game, presses, a.lives, not a.no_reflect, None if mt.ThinkingMind.shell is None else mt.ThinkingMind.shell,
                   None, a.seed, mode=a.mode)
    # end of life: plans that did not close go out as notes too (the journal is saved again with them)
    m = CoreMind.last
    if m is not None:
        try:
            m.log = print                                       # the life log is closed by now (run 16)
            m.finish()
            j = mm.load_journal(a.game)
            j["notes"] = m.j.get("notes", []); j["core_nodes"] = m.j.get("core_nodes", {}); j["core_book"] = m.j.get("core_book")
            j["core_moves"] = m.j.get("core_moves", {})
            j["core_looks"] = m.j.get("core_looks", {}); j["metal_notes"] = m.j.get("metal_notes", [])
            sig = saved_life_sig(a.game)                        # this life was watched press by press: never read it twice
            j["core_read"] = (list(m.j.get("core_read", [])) + ([sig] if sig else []))[-20:]
            mm.save_journal(j)
        except Exception as e_:
            print(f"core: could not save the end-of-life notes ({str(e_)[:120]})")
    print(f"core log: {os.path.join(CORE, a.game + '_core.jsonl')}")


if __name__ == "__main__":
    main()
