#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
views.py — THE THREE VIEWS: one memory per pixel, seen by three eyes, each blind to the pin it looks along.

Jonathan (Sep 7): "each eye has the pin aligned with it invisible, and the other three make up what that pixel is to
that perspective. The side eye sees the directional pins, the border and the normal pins, and stores its memory as
that set. The front eye sees the flat and diagonal pins and keeps those: the diagonal and the coordinates on the
back — which pixel is for what, and the context. The full memory is all of them combined."

    SIDE_X looks along the rows (from the left face): sees the VERTICAL pins — up and down borders, the trail's vertical
           legs, the walls above and below.  Blind to the horizontal pins and to the diagonals.
    SIDE_Y looks along the columns (from the bottom face): sees the HORIZONTAL pins.  Blind to the vertical ones.
    CORNER the two side eyes together — what stands, seen from the diagonal (Sep 7: what was first called the side eye).
    FRONT  looks straight at the screen: sees what LIES FLAT — bent, broken, dragged — and the diagonals foreshortened,
           each foot with its back-wall coordinate and condition, and which thing the pixel belongs to and what kind
           of magnet it has.  Memory: the relations, the rings, the magnets, the paths.  Blind to what stands.
    EYES   look down each pin: see only whether it held — the water on the cell, the meter's pins on the band, the
           diagonal pins' counts.  Memory: the verification.  Blind to geometry and to context.

    Views.build(...)  composes the three from the layers; .at(y, x) is one pixel's memory; .summary() says what each
    eye sees and what only the union sees (a door: a wall to the side eye, a diagonal to the front eye).
"""
from __future__ import annotations
import json
import numpy as np

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
NAMES = ["up", "down", "left", "right"]


class Views:
    def __init__(self, shape):
        self.shape = shape
        self.side = {}      # (y, x) -> what stands here, from the corner (both side eyes)
        self.side_x = {}    # (y, x) -> the vertical pins only (the left face)
        self.side_y = {}    # (y, x) -> the horizontal pins only (the bottom face)
        self.q = None       # (H, W, 4): the quaternion memory — top, front, side_x, side_y
        self.s = None       # (H, W, 16): separate directional evidence, for algebra experiments
        self.front = {}     # (y, x) -> what lies flat, the diagonal feet and back coordinates, the thing and its magnet
        self.eyes = {}      # (y, x) -> what held
        self.union_only = []

    # ---- the side eye: the fence
    def _side(self, fen):
        H, W = self.shape
        if fen is None: return
        mid_any = (fen.mid == 1).any(axis=0)
        opens = {}
        for y, x, k, n, walled, kind in fen.openings():
            dy, dx = DIRS[k]; opens.setdefault((y + dy, x + dx), []).append(NAMES[k])
        fallen = getattr(fen, "fallen", None)
        for y in range(H):
            for x in range(W):
                standing = [NAMES[k] for k in range(4) if fen.mid[k, y, x] == 0 and fen.border[k, y, x] == 0]
                trail = [NAMES[k] for k in range(4) if fen.mid[k, y, x] == 1]
                if not trail and (fallen is None or not fallen[y, x]) and (y, x) not in opens and not (fen.pred[:, y, x] != 0).any(): continue
                rec = {"standing": standing, "trail": trail,
                       "borders": {NAMES[k]: int(fen.border[k, y, x]) for k in range(4) if fen.border[k, y, x] != 0},
                       "wall": bool(fallen[y, x]) if fallen is not None else False,
                       "opening": opens.get((y, x)), "pull": [round(float(fen.pull[k, y, x]), 2) for k in range(4)]}
                self.side[(y, x)] = rec
                # THE TWO SIDE EYES (Jonathan, Sep 7): each blind to the axis it looks along
                vert = {k_: v_ for k_, v_ in rec["borders"].items() if k_ in ("up", "down")}; horz = {k_: v_ for k_, v_ in rec["borders"].items() if k_ in ("left", "right")}
                if vert or any(t_ in ("up", "down") for t_ in trail) or rec["wall"]:
                    self.side_x[(y, x)] = {"standing": [t_ for t_ in standing if t_ in ("up", "down")], "trail": [t_ for t_ in trail if t_ in ("up", "down")], "borders": vert, "wall": rec["wall"]}
                if horz or any(t_ in ("left", "right") for t_ in trail) or rec["wall"]:
                    self.side_y[(y, x)] = {"standing": [t_ for t_ in standing if t_ in ("left", "right")], "trail": [t_ for t_ in trail if t_ in ("left", "right")], "borders": horz, "wall": rec["wall"]}

    # ---- the front eye: the flat pins, the feet, the back wall, the things and their magnets
    def _front(self, fen, diag, mags, things):
        H, W = self.shape
        owner = {}
        for t in things or []:
            for y, x in np.argwhere(t["cells"]): owner[(int(y), int(x))] = t["id"]
        feet = {}; backs = {}
        for i, p in enumerate((diag.pins if diag is not None else [])):
            for y, x in np.argwhere(p["cells"]):
                feet.setdefault((int(y), int(x)), []).append({"pin": i, "to": p["back"]["frame"], "box": [int(v) for v in p["back"]["box"]], "effect": p["effect"]["target"], "source": p["source"]})
            b = p["back"]
            if b["frame"] == "screen":
                y0, y1, x0, x1 = b["box"]
                for y in range(max(0, y0), min(H, y1 + 1)):
                    for x in range(max(0, x0), min(W, x1 + 1)): backs.setdefault((y, x), []).append({"pin": i, "read_for": p["foot"], "effect": p["effect"]["target"]})
        for y in range(H):
            for x in range(W):
                flat = {}
                if fen is not None:
                    for k in range(4):
                        if fen.border[k, y, x] == 1: flat[NAMES[k]] = "bent"
                        elif fen.border[k, y, x] == -1: flat[NAMES[k]] = "broken"
                        elif getattr(fen, "dragged", None) is not None and fen.dragged[k, y, x]: flat[NAMES[k]] = "dragged"
                tid = owner.get((y, x))
                if not flat and (y, x) not in feet and (y, x) not in backs and tid is None: continue
                self.front[(y, x)] = {"flat": flat, "thing": tid, "magnet": (mags.kind(tid) if (mags is not None and tid in mags.things) else None),
                                      "feet": feet.get((y, x)), "back_of": backs.get((y, x))}

    # ---- the eyes: the water, the meter, the pins' counts
    def _eyes(self, water, met, diag, things):
        H, W = self.shape
        owner = {}
        for t in things or []:
            for y, x in np.argwhere(t["cells"]): owner[(int(y), int(x))] = t["id"]
        pin_eyes = {}
        for p in (diag.pins if diag is not None else []): pin_eyes.setdefault(p["foot"], []).append(p["eye"])
        band = getattr(met, "band", None)
        for y in range(H):
            for x in range(W):
                w = float(water[y, x]) if water is not None else 0.0
                tid = owner.get((y, x)); pe = pin_eyes.get(tid)
                onband = band is not None and band[y, x]
                if w <= 0 and not pe and not onband: continue
                rec = {"water": round(w, 1)}
                if pe: rec["pins"] = pe
                if onband and met is not None and met.pins is not None and met.axis == 1 and x < len(met.pins): rec["meter"] = {"pin": int(met.pins[x]), "predicted": met.right, "wrong": met.wrong}
                self.eyes[(y, x)] = rec

    def _quaternions(self, fen, water):
        """THE QUATERNION MEMORY: four numbers per pixel — top (what held), front (context), side_x (vertical), side_y (horizontal)"""
        H, W = self.shape; q = np.zeros((H, W, 4), np.float32)
        wmax = float(water.max()) if water is not None and water.max() > 0 else 1.0
        for (y, x), e in self.eyes.items():
            pe = e.get("pins")
            if pe:
                fw = sum(p["fired_with"] for p in pe); fo = sum(p["fired_without"] for p in pe)
                q[y, x, 0] = (fw - fo) / (fw + fo) if (fw + fo) else 0.0
            elif e.get("water", 0) > 0: q[y, x, 0] = -min(1.0, e["water"] / wmax)          # wet: the pins here did not hold
        for (y, x), f in self.front.items():
            q[y, x, 1] = 1.0 if (f.get("feet") or f.get("back_of")) else (0.5 if f.get("flat") else 0.0)
        if fen is not None:
            for k, sign_ in ((0, 0), (1, 0), (2, 1), (3, 1)):
                comp = 2 + sign_
                q[..., comp] += np.where(fen.border[k] == 1, 0.5, np.where(fen.border[k] == -1, -0.5, 0.0))
        self.q = q
        return q

    def collapse(self, body=None):
        """the uniform regions as single terms; the body as one term when its pixels agree"""
        from quat import collapse as _c
        if self.q is None: return None
        terms, labels = _c(self.q); self.terms = terms; self.labels = labels
        body_term = None
        if body is not None and body.any():
            ids = np.unique(labels[body]); body_term = {"one_term": len(ids) == 1, "terms": int(len(ids)), "cells": int(body.sum())}
            try:
                from quat import stitch as _st
                body_term["stitched"] = _st(terms, labels, body)          # THE STITCH: the parts that move together nest into one term
            except Exception: body_term["stitched"] = None
        nonempty = [t for t in terms if not t["empty"]]
        self.collapse_stats = {"pixels": int(self.q.shape[0] * self.q.shape[1]), "terms": len(terms), "nonempty_terms": len(nonempty),
                               "largest": terms[0]["cells"] if terms else 0, "closing": sum(1 for t in nonempty if t["closes"]), "body": body_term}
        if self.s is not None:
            from cube_memory import collision_audit
            self.collapse_stats["summary_collisions"] = collision_audit(self.q, self.s)
        return self.collapse_stats

    def recall(self, eye):
        """the same memory with `eye` on the real axis"""
        from quat import recall as _r
        return _r(self.q, eye) if self.q is not None else None

    def build(self, fen=None, diag=None, mags=None, things=None, water=None, met=None):
        self._side(fen); self._front(fen, diag, mags, things); self._eyes(water, met, diag, things); self._quaternions(fen, water)
        from cube_memory import pack
        self.s = pack(self.shape, self.side, self.front, self.eyes)
        # what only the union sees: a door — a wall (or a refusal) to the side eye and a diagonal foot to the front eye
        self.union_only = sorted({self.front[c]["thing"] for c in self.front if self.front[c].get("feet") and c in self.side and (self.side[c]["wall"] or any(v == -1 for v in self.side[c]["borders"].values()))} - {None})
        return self

    def at(self, y, x):
        return {"side": self.side.get((y, x)), "front": self.front.get((y, x)), "eyes": self.eyes.get((y, x))}

    def summary(self):
        walls = sum(1 for v in self.side.values() if v["wall"]); trail = sum(1 for v in self.side.values() if v["trail"]); opens = sum(1 for v in self.side.values() if v["opening"])
        feet = sum(1 for v in self.front.values() if v.get("feet")); backs = sum(1 for v in self.front.values() if v.get("back_of")); kinds = {}
        seen_ = set()
        for v in self.front.values():
            if v.get("magnet") and v.get("thing") not in seen_: seen_.add(v["thing"]); kinds[v["magnet"]] = kinds.get(v["magnet"], 0) + 1   # things, not cells
        wet = sum(1 for v in self.eyes.values() if v["water"] > 0); eyed = sum(1 for v in self.eyes.values() if v.get("pins"))
        sx = len(self.side_x); sy = len(self.side_y)
        return (f"views: side eyes see {sx} cells of vertical pins and {sy} of horizontal (the corner: {trail} trail cells, {walls} wall cells, {opens} openings), blind to the diagonals | front eye sees {feet} foot cells, "
                f"{backs} back-wall cells, things by magnet {kinds}, blind to what stands | eyes see {wet} wet cells, {eyed} cells under a pin's eye, blind to geometry"
                + (f" | only the union sees the doors: {self.union_only}" if self.union_only else " | only the union sees the doors: none yet"))

    def save(self, path):
        def enc(d): return {f"{y},{x}": v for (y, x), v in d.items()}
        def default(o):
            if isinstance(o, (np.integer,)): return int(o)
            if isinstance(o, (np.floating,)): return float(o)
            if isinstance(o, (np.bool_,)): return bool(o)
            if isinstance(o, np.ndarray): return o.tolist()
            return str(o)
        from cube_memory import SCHEMA, CHANNELS
        with open(path, "w", encoding="utf-8") as out:
            json.dump({"side": enc(self.side), "side_x": enc(self.side_x), "side_y": enc(self.side_y), "front": enc(self.front), "eyes": enc(self.eyes), "union_only": self.union_only,
                       "algebra_memory": {"schema": SCHEMA, "channels": CHANNELS, "status": "experimental coordinates; detailed records authoritative"}}, out, default=default)
        if self.q is not None: np.save(path.replace(".json", "_q.npy"), self.q)
        if self.s is not None: np.save(path.replace(".json", "_s.npy"), self.s)
