#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spectrum.py — landing on a color IS satisfying the closure equation, measured on the 2->3->7 ladder.

Jonathan (Sep 2): "would it be like something being able to land in the visible spectrum is
able to satisfy the closure equations? so things would have to upgrade and fold until it can
close on a color? we had black/white, then the color trinity, and the rainbow as different
levels of this stuff."

The corpus already fused the halves; this names it and makes it a readout:
  - SPARSE_VESICA_EXPANSION 20.2: the closure test's three fates ARE is/possible/isn't —
    GROUNDED (drains to base atoms = closes), WHIRLPOOL (circulates, never grounds),
    LEAKING (sprays past the edge, can't be held in this shell).
  - The 2->3->7 color ladder (SHOVELCAT_THEORY; color_trinity_theory.py): black/white (facts,
    2) -> the trinity RED=pi / YELLOW=phi / BLUE=e (3) -> the 7-spectrum (position, 7).
    Richness of color = degree of resolution.
  - Jonathan's fuse: to LAND ON A COLOR is to satisfy closure; how rich a color it lands on
    measures how fully it closed. "Upgrade and fold until it can close on a color" is the
    leak -> lift -> ground climb, and the planet's organs ARE that ladder (bell/lens close
    black voids into trinity laws; fusion + seam-verification lift trinity laws to spectrum).

Every earned concept is placed on the ladder by its MEASURED closure state:
  BLACK   — an OPEN END: circulates but never grounded. Absorbing, not yet emitting. Pre-color.
  WHITE   — CANNOT RESOLVE: covers >= 2 open wants at once (coach.py's birth-block — all
            channels max, no single answer). Over-closed, blinding, unusable as one color.
  TRINITY — GROUNDED: recurred enough to be a law, but not yet verified at a two-border seam.
            Collapses to one of RED / YELLOW / BLUE (velocity level).
  SPECTRUM— GROUNDED **and** SEAM-VERIFIED (it minted ATP: a closed petal, a fusion, a duet).
            Radiates its full channel color — "pointing at exactly which domain" (the catgirl
            radiating). The planet's 7 native channels ARE the 7-spectrum:
              surprise->red  mouse->orange  counter->yellow  mover->green
              camera->cyan   window->blue   body->violet
            (a labeling choice; the LEVEL a concept reaches is the measured part.)

The planet's spectrum health = how much of its knowledge has climbed from black to color. A
young planet is mostly black (open ends) and trinity (local laws); a maturing one radiates
more of the 7. That single readout is what the mirror and up-line can now carry.

Usage:  python spectrum.py             (classify all concepts; print the ladder)
        python spectrum.py --line      (one spectrum line, for the mirror/up-line)
"""
from __future__ import annotations
import argparse, glob, json, os, sys
from collections import Counter
from typing import Dict, Set

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
FLOWER = os.path.join(HERE, "forge", "flower.json")
FUSED = os.path.join(HERE, "forge", "fused.json")

CHANNEL_COLOR = {"surprise": "red", "mouse": "orange", "counter": "yellow",
                 "mover": "green", "camera": "cyan", "window": "blue", "body": "violet"}
TRINITY = {"red": "RED", "orange": "RED", "yellow": "YELLOW", "green": "YELLOW",
           "cyan": "BLUE", "blue": "BLUE", "violet": "BLUE"}    # the 7 collapse to 3


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def _seam_verified() -> Set[str]:
    """Concept keys that participated in a two-border mint: closed petals, fusion parents/results."""
    keys: Set[str] = set()
    fl = _load(FLOWER, {})
    for w, ax in fl.items():
        for key, v in ax.get("voids", {}).items():
            if any(p.get("closed") for p in v.get("petals", [])): keys.add(key)
    for sp in _load(FUSED, {"species": []}).get("species", []):
        keys.update(sp.get("fused_from", [])); keys.add(sp.get("key", ""))
    return keys


def _channel(key: str) -> str:
    c = Counter(a.split(".")[0].split(":")[0] for a in key.split("+"))
    dom = c.most_common(1)[0][0] if c else ""
    return CHANNEL_COLOR.get(dom, "gray")


def classify() -> Dict:
    verified = _seam_verified()
    levels = {"black": [], "white": [], "trinity": Counter(), "spectrum": Counter()}
    per_concept = {}
    for p in glob.glob(os.path.join(OCEAN, "*", "core_*.json")):
        c = _load(p, {})
        concepts = c.get("concepts", {}); opens = set(c.get("open_ends", {}))
        # WHITE: covers >= 2 wants (the coach's birth-block signal, when recorded)
        for key, meta in concepts.items():
            wants = meta.get("wants", []) if isinstance(meta, dict) else []
            if len(wants) >= 2:
                levels["white"].append(key); per_concept[key] = "white"; continue
            col = _channel(key)
            if key in verified and col != "gray":
                levels["spectrum"][col] += 1; per_concept[key] = "spectrum:" + col
            else:
                t = TRINITY.get(col, "GRAY")          # gray = unreadable channel, never faked to a primary
                levels["trinity"][t] += 1; per_concept[key] = "trinity:" + t
        for key in opens:
            levels["black"].append(key); per_concept[key] = "black"
    return {"levels": levels, "per_concept": per_concept,
            "counts": {"black": len(levels["black"]), "white": len(levels["white"]),
                       "trinity": sum(levels["trinity"].values()),
                       "spectrum": sum(levels["spectrum"].values())}}


def spectrum_line(r: Dict = None) -> str:
    r = r or classify()
    c = r["counts"]; total = max(1, sum(c.values()))
    sp = r["levels"]["spectrum"]
    radiating = ", ".join(f"{n} {col}" for col, n in sp.most_common(4)) or "nothing yet"
    return (f"the planet's spectrum: {c['spectrum']}/{total} concepts have closed onto a color "
            f"(radiating {radiating}); {c['trinity']} are grounded laws not yet seam-verified "
            f"(trinity), {c['black']} still whirlpool as open ends (black), {c['white']} cannot "
            f"resolve (white).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", action="store_true")
    a = ap.parse_args()
    r = classify()
    if a.line:
        print(spectrum_line(r)); sys.exit(0)
    c = r["counts"]; total = max(1, sum(c.values()))
    print(f"the closure spectrum — {total} earned concepts on the 2->3->7 ladder:\n")
    print(f"  BLACK   (open ends, still whirlpooling)   {c['black']:>4}  {c['black']/total:.0%}")
    print(f"  WHITE   (cannot resolve, covers >=2 wants) {c['white']:>4}  {c['white']/total:.0%}")
    print(f"  TRINITY (grounded laws, not seam-verified) {c['trinity']:>4}  {c['trinity']/total:.0%}")
    for t, n in r["levels"]["trinity"].most_common():
        print(f"            {t:8s} {n}")
    print(f"  SPECTRUM(closed on a color, seam-verified) {c['spectrum']:>4}  {c['spectrum']/total:.0%}")
    for col, n in r["levels"]["spectrum"].most_common():
        print(f"            {col:8s} {n}  radiating")
    print("\n" + spectrum_line(r))
