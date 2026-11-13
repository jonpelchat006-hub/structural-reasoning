#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pins.py — THE PIN REGISTRY: an empty container for every control and every thing, asking "what is this?"

Jonathan (Sep 4): the pins are empty containers asking what is this. The orthogonal rings held context and
purpose (what things are for, seen from where); the sideways ring holds how it feels; the pins hold what
controls what and what is controlled by what — the real stuff on the normal axis. The pins are the
hypothesis about what everything is, so we always want something more than nothing for every control.
Lineage: SPARSE_VESICA §39b "an idle basis term is an empty slot awaiting its C"; §27 "actively move the
empty containers to an attractor"; FOLDING Part XXXIX, the rings as lenses.

Four rules:
  1. A pin exists for every control x thing from the level's first frame, state EMPTY; emptiness is counted.
  2. "Does nothing" may fill a pin only with a place attached — NOTHING HERE, never nothing. The pin keeps
     asking everywhere else.
  3. Attention goes to the emptiest control first.
  4. The fraction of pins with an answer is a shape statistic beside the closure's coverage.

Pin states, in order of how much they say: level > state > pass > refusal > nothing_here > empty.
A thing is a goal candidate when some pin on it says state or level; a thing with empty pins is a candidate
because it has not been asked; a thing whose pins all say refusal is a wall; nothing_here ranks between.
"""
from __future__ import annotations

ORDER = {"level": 5, "state": 4, "pass": 3, "refusal": 2, "nothing_here": 1, "empty": 0}


class Pins:
    def __init__(self):
        self.things: dict = {}            # thing id -> the touch graph's object dict (cells, colour, n, at)
        self.controls: list = []
        self.pins: dict = {}              # (control, thing) -> {"state", "places": set of place keys where it did nothing, "n": count}

    def open(self, controls, things):
        """rule 1: every control x thing, empty until told otherwise; things and controls may grow between sleeps"""
        self.controls = sorted(set(self.controls) | set(int(c) for c in controls))
        for o in things: self.things.setdefault(o["id"], o)
        for c in self.controls:
            for t in self.things:
                self.pins.setdefault((c, t), {"state": "empty", "places": set(), "n": 0})
        return self

    def fill(self, control, thing, effect, place=None):
        """rule 2: 'nothing' needs a place and never outranks an answer; any other effect fills by precedence"""
        c = int(control)
        if (c, thing) not in self.pins:
            if thing not in self.things or c not in self.controls: return
            self.pins[(c, thing)] = {"state": "empty", "places": set(), "n": 0}
        p = self.pins[(c, thing)]; p["n"] += 1
        if effect == "nothing":
            if place is not None: p["places"].add(place)
            if p["state"] == "empty": p["state"] = "nothing_here"
            return
        if ORDER.get(effect, 0) > ORDER[p["state"]]: p["state"] = effect

    def asked_here(self, control, thing, place) -> bool:
        p = self.pins.get((int(control), thing))
        return p is not None and (p["state"] not in ("empty", "nothing_here") or place in p["places"])

    def emptiness(self, control) -> float:
        """how much a control still has to answer: empty pins count 1, nothing-here pins 0.5"""
        ps = [p for (c, t), p in self.pins.items() if c == int(control)]
        if not ps: return 1.0
        return sum(1.0 if p["state"] == "empty" else 0.5 if p["state"] == "nothing_here" else 0.0 for p in ps) / len(ps)

    def emptiest(self, controls):
        """rule 3: the control whose pins are most empty, among those offered"""
        cs = [int(c) for c in controls if int(c) in self.controls] or [int(c) for c in controls]
        return max(cs, key=self.emptiness) if cs else None

    def stats(self) -> dict:
        n = len(self.pins); by = {}
        for p in self.pins.values(): by[p["state"]] = by.get(p["state"], 0) + 1
        answered = sum(v for k, v in by.items() if k not in ("empty", "nothing_here"))
        return {"pins": n, "empty": by.get("empty", 0), "nothing_here": by.get("nothing_here", 0), "answered": answered,
                "answered_frac": round(answered / n, 3) if n else None, "by": by}

    def candidates(self, exclude=()):
        """things ranked by what their pins say: level/state first (most answers first), then things with empty pins
        (most empty first), then nothing-here-only; walls (refusal only) and the excluded last / out"""
        rows = []
        for t, o in self.things.items():
            if t in exclude or t.startswith(("chg", "place", "wall")) or t == "bound": continue
            ps = [p for (c, tt), p in self.pins.items() if tt == t]
            if not ps: continue
            states = [p["state"] for p in ps]
            pointed = sum(1 for s in states if s in ("level", "state")); lvl = sum(1 for s in states if s == "level")
            empty = sum(1 for s in states if s == "empty"); nothing = sum(1 for s in states if s == "nothing_here")
            wall = all(s in ("refusal", "pass") for s in states) and any(s == "refusal" for s in states)
            if pointed: tier = 0
            elif empty: tier = 1
            elif nothing: tier = 2
            elif wall: tier = 4
            else: tier = 3
            rows.append((tier, -lvl, -pointed, -empty, o.get("n", 0), t))
        rows.sort()
        return [self.things[t] for *_, t in rows if _[0] < 4]

    def summary(self) -> str:
        s = self.stats()
        if not s["pins"]: return "no pins"
        return (f"{s['pins']} pins: {s['answered_frac']:.0%} answered, {s['empty']} empty, {s['nothing_here']} nothing-here"
                + " | emptiest control " + ", ".join(f"{c}:{self.emptiness(c):.0%}" for c in self.controls))
