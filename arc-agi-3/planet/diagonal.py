#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
diagonal.py — THE DIAGONAL PINS: the pins that leave the screen into the logic space and come back down elsewhere.

Jonathan (Sep 6): "the controller is in front with longer pins going to each pixel; a diagonal pin goes in and out and
connects far-apart pixels, or is conditional; each pin has an eye that looks at it; the diagonal pins go to a back wall
— the context and logic domain, with coordinates — and the controller is the front wall; we would still see the end
of the diagonal pin in the pixel as a small arrow pointing at the pixels it affects; the angle it comes in at can enter
nearby pixels; we have to make a full path between the front and back walls."

A diagonal pin:
    front   the button(s) whose press drives it (the front wall)
    foot    the thing on the screen the pin stands in (its cells) — the small arrow is drawn here
    back    where it lands on the back wall: {"frame": "screen", "box": rows/cols} or {"frame": "body", "box": offset}
            and what it must read there ("reads": the pattern when the pin is live)
    effect  what happens when it fires: the target thing, the register (a refill), or the level
    width   how far the foot's angle reaches: the span of cells it is lined up with (the act button's reach)
    eye     the count that keeps it honest: fired with the condition, fired without it, silent with it, silent without

Made from what the other layers found — the relations (source -> region -> target), the rings (ring -> the bar), the
magnets' keys (a door -> its key; a button -> its key) — and given one eye each over the level's presses.
A PATH is complete for a button when a front pin (an operator or act pins) reaches a foot that has a diagonal pin.
"""
from __future__ import annotations
import numpy as np


def _centre(cells):
    ys, xs = np.where(cells)
    return (float(ys.mean()), float(xs.mean())) if len(ys) else (0.0, 0.0)


def _reads(f, back, body_pos=None):
    """does the frame read the pin's pattern at its back-wall coordinate? None when the coordinate is off the frame"""
    y0, y1, x0, x1 = back["box"]
    if back["frame"] == "body":
        if body_pos is None: return None
        y0 += body_pos[0]; y1 += body_pos[0]; x0 += body_pos[1]; x1 += body_pos[1]
    H, W = f.shape
    if y0 < 0 or x0 < 0 or y1 >= H or x1 >= W: return None
    pat = np.asarray(back["reads"])
    if pat.shape == (1, 1):                                   # a colour, anywhere in the box (the per-open key)
        return bool((f[y0:y1 + 1, x0:x1 + 1] == pat[0, 0]).any())
    sub = f[y0:y1 + 1, x0:x1 + 1]
    return bool(sub.shape == pat.shape and np.array_equal(sub, pat))


class Pins:
    def __init__(self): self.pins = []

    def add(self, front, foot_id, foot_cells, back, effect, width=None, source="", condition_sides=None, rel=None):
        self.pins.append({"front": sorted(int(a) for a in front), "foot": foot_id, "cells": foot_cells, "back": back, "effect": effect, "rel": rel,
                          "width": width, "source": source, "sides": condition_sides, "eye": {"fired_with": 0, "fired_without": 0, "silent_with": 0, "silent_without": 0}})

    def from_layers(self, rels, ring_rel, rings_standing, reg_band, mags, mag_stats, objects):
        """the relations, the rings and the magnets' keys, as pins"""
        obj = {o["id"]: o for o in objects}
        for r in rels or []:
            if not r.get("targets"): continue
            src = obj.get(r["src"])
            if src is None: continue
            reads = r.get("raw_open")
            if reads is None:
                t = r["targets"][0]; reads = t.get("pattern")
                if reads is not None: reads = np.asarray(reads).astype(int).tolist()
            self.add(front=[], foot_id=r["src"], foot_cells=src["cells"], back={"frame": "screen", "box": list(r["region"]), "reads": reads if reads is not None else [[-1]]},
                     effect={"kind": "opens", "target": r["targets"][0]["id"]}, source="relation", rel=r)
        if ring_rel and reg_band is not None:
            ys, xs = np.where(reg_band); box = [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())] if len(ys) else [0, 0, 0, 0]
            for ring in rings_standing or []:
                self.add(front=[], foot_id=ring["id"], foot_cells=ring["cells"], back={"frame": "screen", "box": box, "reads": [[-1]]},
                         effect={"kind": "refill", "target": "the register"}, source="ring")
        for c in (mag_stats or {}).get("contradictions", []):
            kk = c.get("key")
            if not kk: continue
            tid = c["thing"]; cells = mags.things.get(tid)
            if cells is None: continue
            back = {"frame": kk["frame"], "box": list(kk["box"]), "reads": kk["pattern_when_open"]}
            self.add(front=[c["control"]], foot_id=tid, foot_cells=cells, back=back,
                     effect={"kind": c.get("key", {}).get("open", "opens"), "target": tid}, width=c.get("side"), source="magnet", condition_sides=kk.get("sides"))
        return self

    def eyes(self, pairs, mags, band=None, floor=None, matched=None):
        """THE EYE on each pin: over the presses whose pin went into the place the effect lands (the target for a relation,
        the foot otherwise — the magnets' records), did the effect fire with the condition, without it, and did it stay
        silent with the condition? A relation's condition is its own match test; a ring's is always met."""
        for p in self.pins:
            where = p["effect"]["target"] if p["effect"]["target"] in mags.presses else p["foot"]
            recs = mags.presses.get(where, {})
            fired = set(); silent = set()
            for key, rec in recs.items():
                if p["front"] and int(key[0]) not in p["front"]: continue
                # a relation fires when its target OPENS (a pass or the level), not when something else changed nearby
                # a relation whose target is the goal fires on the level alone (a pass into the box's mouth is not the door opening)
                for o in (("level",) if p.get("rel") is not None else ("level", "state", "pass")): fired.update(rec.get(o, []))
                silent.update(rec.get("refuse", []))
            for i in fired | silent:
                if i >= len(pairs): continue
                if p["source"] == "ring": reads = True
                elif p.get("rel") is not None and matched is not None: reads = bool(matched(pairs[i][0], p["rel"], floor or set()))
                else: reads = _reads(pairs[i][0], p["back"], mags.body_pos.get(i))
                if reads is None: continue
                k = ("fired" if i in fired else "silent") + ("_with" if reads else "_without")
                p["eye"][k] += 1
        return self

    def paths(self, controls, front_known):
        """which buttons have a full path front wall -> foot -> back wall"""
        out = {}
        for a in sorted(controls):
            has_front = a in front_known
            feet = [p["foot"] for p in self.pins if not p["front"] or a in p["front"]]
            out[int(a)] = {"front": has_front, "diagonal": len(feet) > 0, "complete": has_front and len(feet) > 0}
        return out

    def summary(self, paths=None):
        if not self.pins: return "diagonal pins: none yet"
        bits = []
        for p in self.pins:
            e = p["eye"]; back = p["back"]
            where = (f"rows {back['box'][0]}-{back['box'][1]} cols {back['box'][2]}-{back['box'][3]}" if back["frame"] == "screen"
                     else (f"a {'/'.join(p['sides'])} neighbour" if p.get("sides") else f"the cells {back['box'][0]:+d}..{back['box'][1]:+d}, {back['box'][2]:+d}..{back['box'][3]:+d} from the body"))
            honest = "real" if e["fired_with"] and not e["fired_without"] and not e["silent_with"] else ("unproven" if not (e["fired_with"] + e["fired_without"]) else "leaky")
            bits.append(f"{p['foot']} -> {where} -> {p['effect']['target']} ({p['source']}; eye {e['fired_with']}/{e['fired_without']}/{e['silent_with']}/{e['silent_without']} {honest})")
        line = f"diagonal pins: {len(self.pins)} — " + "; ".join(bits)
        if paths:
            done = [a for a, v in paths.items() if v["complete"]]
            line += f" | paths front to back: {len(done)} of {len(paths)} buttons complete" + (f" ({done})" if done else "")
        return line

    def dump(self, floor=None):
        out = []
        for p in self.pins:
            cy, cx = _centre(p["cells"]); b = p["back"]
            if p["source"] == "ring":
                condition = {"kind": "constant", "value": True}
            elif p.get("rel") is not None:
                r = p["rel"]
                condition = {"kind": "relation_match", "region": [int(v) for v in r["region"]],
                             "raw_open": np.asarray(r["raw_open"]).tolist() if r.get("raw_open") is not None else None,
                             "colour": int(r["colour"]) if r.get("colour") is not None else None,
                             "floor": sorted(int(c) for c in floor) if floor is not None else None,
                             "targets": [{"id": t["id"], "pattern": np.asarray(t["pattern"]).tolist() if t.get("pattern") is not None else None} for t in r["targets"]]}
            else:
                condition = {"kind": "back_pattern", "frame": b["frame"], "box": [int(v) for v in b["box"]],
                             "reads": np.asarray(b["reads"]).tolist(), "matcher": "any_colour_for_1x1_else_exact"}
            observation = {"fired_events": ["level"] if p.get("rel") is not None else ["level", "state", "pass"],
                           "silent_events": ["refuse"], "note": "existing eye event proxies; check target-specific effect before a causal experiment"}
            out.append({"front": p["front"], "foot": p["foot"], "foot_centre": [cy, cx], "back": {"frame": b["frame"], "box": [int(v) for v in b["box"]]},
                        "effect": p["effect"], "source": p["source"], "sides": p.get("sides"), "eye": p["eye"].copy(), "condition": condition,
                        "effect_observation": observation})
        return out
