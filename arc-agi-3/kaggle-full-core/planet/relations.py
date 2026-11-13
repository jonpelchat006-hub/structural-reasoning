#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relations.py — THE RELATION LAYER: lines from one object to another, learned from state edges.

Jonathan (Sep 5): the keyhole's line runs to the HUD glyph across the screen; the box accepts the key only
when the glyph matches. So: an object whose touch changes a region elsewhere OWNS a line to that region
(source -> region); an object whose inner pattern that region can be made to equal is the TARGET the line
points at (region -> target); and the plan is "touch the source until the region matches, then go to the
target". June's relations.ts measured count / position / size / shape invariants across pairs; this is the
same measurement over presses: what a touch changes, and what it can be made to equal.

  region(A)     the union box of everything that changed, away from the body and the register, on the
                presses that touched A with effect 'state'
  pattern(box)  the rarest colour's mask inside the box, cropped, shrunk while its blocks are uniform (the
                chain's shrink), a small binary shape
  cycle(A)      the patterns the region showed after each touch of A — the states the source can reach
  target(A)     an object whose inner pattern equals one of those states (up to D4): the thing the region
                is FOR. matched_now = the region's pattern equals the target's pattern exactly (no rotation)
"""
from __future__ import annotations
import numpy as np
import qtube_fit
from scipy import ndimage


def shrink(m):
    m = m.astype(int)
    ys, xs = np.where(m)
    if not len(ys): return m
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    for s in (3, 2):
        if m.size and m.shape[0] % s == 0 and m.shape[1] % s == 0:
            t = m.reshape(m.shape[0] // s, s, m.shape[1] // s, s).mean(axis=(1, 3))
            if ((t == 0) | (t == 1)).all(): return t.astype(int)
    return m


def pattern(f, box, floor, exclude=(), colour=None):
    """the rarest colour's shape inside a box (frame edges of the box excluded), as a small binary array; with
    `colour` given, that colour's shape (THE RELATION'S COLOUR, Sep 5: on ls20 level 1 the key's 9s were the rarer
    colour inside the HUD region, on level 2 the 5 gaps were, and the region read as the box's negative)"""
    y0, y1, x0, x1 = box
    inner = f[y0:y1 + 1, x0:x1 + 1]
    if colour is not None:
        m = inner == colour
        return (shrink(m), int(colour)) if m.any() else (None, None)
    vals, counts = np.unique(inner, return_counts=True)
    cands = [(c, int(v)) for v, c in zip(vals, counts) if int(v) not in floor and int(v) not in exclude]
    if not cands: return None, None
    cands.sort()
    col = cands[0][1]
    return shrink(inner == col), col


def d4_equal(a, b):
    if a is None or b is None: return None
    for t in range(8):
        g = np.rot90(a, t % 4)
        if t >= 4: g = np.fliplr(g)
        if g.shape == b.shape and np.array_equal(g, b): return t
    return None


def regions(edges, level_hist, body_of, amb, ops):
    """source object -> the union box of what its 'state' touches changed (away from body and register)"""
    out = {}
    by_press = {}
    for e in edges:
        if e.get("effect") == "state" and e.get("press") is not None: by_press.setdefault(e["press"], []).append(e["object"])
    for i, (f0, f1, a, x, y) in enumerate(level_hist):
        if i not in by_press: continue
        D = (f0 != f1) & ~amb
        b0 = body_of(ops, f0); b1 = body_of(ops, f1)
        if b0 is not None: D &= ~b0
        if b1 is not None: D &= ~b1
        if not D.any(): continue
        ys, xs = np.where(D); box = (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))
        for src in by_press[i]:
            r = out.get(src)
            out[src] = box if r is None else (min(r[0], box[0]), max(r[1], box[1]), min(r[2], box[2]), max(r[3], box[3]))
    return out


def cycle(level_hist, edges, src, box, floor, colour=None):
    """the region's patterns after each touch of the source, in order"""
    presses = sorted(e["press"] for e in edges if e.get("object") == src and e.get("effect") == "state" and e.get("press") is not None)
    seen = []
    for i in presses:
        if i >= len(level_hist): continue
        p, _ = pattern(level_hist[i][1], box, floor, colour=colour)
        if p is not None and not any(np.array_equal(p, q) for q in seen): seen.append(p)
    return seen


def targets(f, box, states, objects, floor, src_id, colour=None):
    """objects whose inner pattern equals one of the region's reachable states (up to D4); each with the D4
    index needed from the region's CURRENT pattern, and whether it matches now"""
    now, _ = pattern(f, box, floor, colour=colour)
    out = []; near = []
    for o in objects:
        if o["id"] == src_id or o["id"].startswith(("chg", "place", "wall")) or o["id"] == "bound": continue
        if o["cells"][box[0]:box[1] + 1, box[2]:box[3] + 1].any(): continue          # the HUD that holds the region is not its own target
        ys, xs = np.where(o["cells"])
        if len(ys) < 12: continue
        obox = (int(ys.min()) + 1, int(ys.max()) - 1, int(xs.min()) + 1, int(xs.max()) - 1)
        if obox[1] <= obox[0] or obox[3] <= obox[2]: continue
        pat, col = pattern(f, obox, floor, exclude={o["colour"]})
        if pat is None or pat.size < 4: continue
        reachable = [s for s in states + ([now] if now is not None else []) if d4_equal(s, pat) is not None]
        if not reachable:
            if qtube_fit.on(): near.append((o, pat))
            continue
        out.append({"id": o["id"], "object": o, "pattern": pat, "matched_now": bool(now is not None and now.shape == pat.shape and np.array_equal(now, pat)),
                    "rotation": d4_equal(now, pat) if now is not None else None})
    if not out and near:                     # THE Q-TUBE (Nov 2): nothing fits exactly; the nearest shape up to a move is aimed at
        try:
            best = None
            for o, pat in near:
                if int(pat.sum()) < 4: continue
                for st in states + ([now] if now is not None else []):
                    ft = qtube_fit.fit(st, pat)
                    if ft is not None and ft[2] <= qtube_fit.NEAR and (best is None or ft[1] < best[2][1]): best = (o, pat, ft)
            if best is not None:
                o, pat, ft = best
                as_is = [x for x in (qtube_fit.off_as_is(st, pat) for st in states + ([now] if now is not None else [])) if x is not None]
                lim = min(as_is) if as_is and min(as_is) <= qtube_fit.NEAR * max(int(pat.sum()), 1) else -1
                cur = qtube_fit.off_as_is(now, pat) if now is not None else None
                out.append({"id": o["id"], "object": o, "pattern": pat, "matched_now": bool(cur is not None and lim >= 0 and cur <= lim),
                            "rotation": None, "near": ft, "near_lim": lim})
                qtube_fit.note(f"the nearest fit for what {src_id} changes is {o['id']}: its shape is that one {qtube_fit.words(ft[0], ft[1])}")
        except Exception:
            pass
    return out


def find(f, edges, level_hist, objects, body_of, amb, ops, floor):
    """every relation on this level: source -> region -> targets"""
    rels = []
    regs = regions(edges, level_hist, body_of, amb, ops)
    for src, box in regs.items():
        if (box[1] - box[0] + 1) * (box[3] - box[2] + 1) > 400: continue      # a whole-screen change is a level, not a region
        # the region is read in every colour it holds; the colour whose states name a target is the relation's colour
        inner = f[box[0]:box[1] + 1, box[2]:box[3] + 1]
        cols = [int(v) for v in np.unique(inner) if int(v) not in floor]
        best = None
        for c in cols + [None]:                      # a named colour first; the rarest-colour reading only as the fallback
            states = cycle(level_hist, edges, src, box, floor, colour=c)
            tg = targets(f, box, states, objects, floor, src, colour=c)
            if best is None or (tg and not best[1]): best = (states, tg, c)
            if tg: break
        states, tg, c = best if best is not None else ([], [], None)
        rels.append({"src": src, "region": box, "states": len(states), "targets": tg, "state_patterns": states, "colour": c})
    return rels


def carried_colour(prior, f, floor):
    """Rebind an absent pigment only when one current mask fits a known shape.

    Structure may transfer between levels; a literal colour need not. Ambiguous
    alternatives remain unresolved, rather than selecting a convenient mask.
    """
    old = prior.get("colour")
    y0, y1, x0, x1 = prior["region"]
    present = set(int(v) for v in np.unique(f[y0:y1 + 1, x0:x1 + 1]))
    if old is None or old in present:
        return old
    candidates = []
    for colour in sorted(present - set(floor)):
        mask, _ = pattern(f, prior["region"], floor, colour=colour)
        if any(d4_equal(mask, known) is not None for known in prior["states"]):
            candidates.append(colour)
    return candidates[0] if len(candidates) == 1 else old


def refresh_active(active, current, objects):
    """Refresh a running relation's matcher without spending/restoring trials.

    Only replace the same source/region/target binding. Observed relations take
    precedence over carried hypotheses; unrelated discoveries cannot hijack a
    pending experiment. Callers must discard a pending source plan on change.
    """
    from relation_guard import identity
    old = active["rel"]
    target = active["dst"]["id"]
    candidates = [r for r in current if r["src"] == old["src"]
                  and tuple(r["region"]) == tuple(old["region"])
                  and any(t["id"] == target for t in r.get("targets", []))]
    source = next((o for o in objects if o["id"] == old["src"]), None)
    if not candidates or source is None:
        return active, False
    latest = min(candidates, key=lambda r: bool(r.get("prior")))
    dst = next(t["object"] for t in latest["targets"] if t["id"] == target)
    changed = identity(old) != identity(latest)
    return {**active, "rel": latest, "src": source, "dst": dst}, changed


def carry(priors, f, objects, floor):
    """THE ROTATOR CARRIED OVER (Sep 5): a relation learned on the last level — the keyhole's colour, the HUD region,
    the patterns its touches cycled through — instantiated on this level by colour: every thing of the source's
    colour is a source, the same region is the region, the targets are whatever thing's inner pattern equals one
    of the remembered states. Nothing has been touched yet; the loop can start at once."""
    out = []
    for pr in priors:
        colour = carried_colour(pr, f, floor)
        for o in objects:
            if o["id"].startswith(("chg", "place", "wall")) or o["id"] == "bound" or o.get("colour") != pr["src_colour"]: continue
            tg = targets(f, pr["region"], pr["states"], objects, floor, o["id"], colour=colour)
            tg = [t for t in tg if t["object"].get("colour") in pr["target_colours"]] or tg
            if not tg: continue
            out.append({"src": o["id"], "region": pr["region"], "states": len(pr["states"]), "targets": tg, "state_patterns": list(pr["states"]),
                        "prior": True, "colour": colour, "prior_colour": pr.get("colour"),
                        "colour_rebound": colour != pr.get("colour")})
    return out


def touches_needed(f, rel, floor):
    """how many touches from the region's current state to the target's pattern, round the cycle the touches were
    seen to run (None when the current state or the target is not on the remembered cycle)"""
    now, _ = pattern(f, rel["region"], floor, colour=rel.get("colour"))
    pats = rel.get("state_patterns") or []
    if now is None or not pats or not rel.get("targets"): return None
    same = lambda p, q: p is not None and q is not None and p.shape == q.shape and np.array_equal(p, q)
    i_now = next((i for i, p in enumerate(pats) if same(p, now)), None)
    tgt = rel["targets"][0]["pattern"]
    i_tgt = next((i for i, p in enumerate(pats) if same(p, tgt)), None)
    if i_now is None or i_tgt is None: return None
    return (i_tgt - i_now) % len(pats)


def matched(f, rel, floor):
    if rel.get("raw_open") is not None:                                   # THE MAGNET'S KEY: the region reads one way when the door opens
        y0, y1, x0, x1 = rel["region"]; now_raw = f[y0:y1 + 1, x0:x1 + 1]
        ok = np.array_equal(now_raw, np.asarray(rel["raw_open"]))
        for t in rel["targets"]: t["matched_now"] = ok
        return [t for t in rel["targets"] if ok]
    now, _ = pattern(f, rel["region"], floor, colour=rel.get("colour"))
    for t in rel["targets"]:
        pat = t["pattern"]
        t["matched_now"] = bool(now is not None and now.shape == pat.shape and np.array_equal(now, pat))
        t["rotation"] = d4_equal(now, pat) if now is not None else None
        if not t["matched_now"] and t.get("near") is not None and now is not None and t.get("near_lim", -1) >= 0:
            try:                              # THE Q-TUBE: a near target takes the key when the region reads as near as it gets
                cur = qtube_fit.off_as_is(now, pat)
                t["matched_now"] = bool(cur is not None and cur <= t["near_lim"])
            except Exception:
                pass
    return [t for t in rel["targets"] if t["matched_now"]]
