#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chord.py — THE CROSS-TUNNEL between the two ring sets IS THE SHAVE. The focus gets a mechanism.

Jonathan (Sep 2): "we have the orthogonal rings, and these side rings, but we also had a way for
the orthogonal rings to connect to each other, so wouldn't the side eyes have that too? and then
what if those 2 sets have to connect with one of those tunnels, but one would be on the left/
right sides and the other on the top/bottom, so if we connected those wouldn't it be kind of
like the shave? did we have an actual mechanism for that? the context rings would make the y
axis and the side ones would be x, but they would have to be at the edges so the tunnel would
be a line from the end of each axis. so then we could shift each ring slightly and change the
focus?"

It is the shave, exactly, and until now the shave had no mechanism — fovea.json was a hand-set
dial (depth 0.35). Put the round eye's rim as the unit circle. The context (upward, poloidal)
rings end on the rim at angle THETA_Y; the side (toroidal) rings end on the rim at THETA_X. A
tunnel from one end to the other is a CHORD of the circle. A chord is a flat cut: the shave.
  half-chord      = sin(delta/2)             = the opening radius a of shave_law
  distance to it  = cos(delta/2)   so depth d = 1 - cos(delta/2)      (delta = theta_y - theta_x)
  midpoint angle  = (theta_y + theta_x)/2    = the DIRECTION the aperture faces
Rings a quarter turn apart give d = 0.293 (a = 0.707, half-angle 45 deg). The side eye sits one
golden angle from the main eye (sideeye.py), so the resting chord spans 137.5 deg: d = 0.64, a
wide shallow field. SHIFT either ring a little and two things change at once: the separation
sets the depth (wide field vs long reach — shave_law), the mean sets where the eye points. That
is focus, and it is nothing but where the two ring sets happen to touch.

What the direction points at: the ring's sections have angles (ring.py). Sections within the
aperture's half-angle of the direction are IN FOCUS; the worlds they point to are what the
planet attends to. The derived depth is written into fovea.json (the round eye reads it), the
focus into D:\\planet\\focus.json, and the dials that shift the rings are shift_y / shift_x
degrees in fovea.json — turn them and the focus moves.

Usage:  python chord.py                       (read the rings, cut the chord, write the focus)
        python chord.py --shift-x -47 --shift-y 0   (try a shift; persisted in fovea.json)
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

RING = r"D:\planet\ring.jsonl" if os.name == "nt" else "/tmp/ring.jsonl"
FOVEA = r"D:\planet\fovea.json" if os.name == "nt" else "/tmp/fovea.json"
FOCUS = r"D:\planet\focus.json" if os.name == "nt" else "/tmp/focus.json"
GOLDEN_DEG = 360.0 * (1 - 1 / ((1 + 5 ** 0.5) / 2))


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def shave_law(depth: float) -> Dict[str, float]:
    try:
        import fovea
        return fovea.shave_law(depth)
    except Exception:
        d = min(1.0, max(1e-4, depth)); a = math.sqrt(max(0.0, 2 * d - d * d)); th = math.asin(min(1.0, a))
        om = 2 * math.pi * (1 - math.cos(th))
        return {"depth": d, "opening": round(a, 4), "theta_deg": round(math.degrees(th), 2), "omega_sr": round(om, 4), "reach": round(1 / om, 3)}


def chord(theta_y: float, theta_x: float) -> Dict:
    """the tunnel between the two ring ends, read as a shave"""
    delta = abs((theta_y - theta_x + 180) % 360 - 180)          # separation, 0..180
    d = 1 - math.cos(math.radians(delta / 2))
    law = shave_law(d)
    signed = ((theta_y - theta_x + 180) % 360 - 180)               # y relative to x, -180..180
    direction = (theta_x + signed / 2) % 360                         # the chord's midpoint bearing
    return {"theta_y": round(theta_y % 360, 2), "theta_x": round(theta_x % 360, 2), "separation_deg": round(delta, 2),
            "depth": round(d, 4), "direction_deg": round(direction, 2), "law": law}


def ring_ends(shift_y: float = 0.0, shift_x: float = 0.0) -> Dict:
    """where the two ring sets end on the rim right now: the context rings at the main eye's
    direction (the newest ring section), the side rings one golden angle round (sideeye.py)"""
    rows = [json.loads(l) for l in open(RING, encoding="utf-8") if l.strip()] if os.path.exists(RING) else []
    main = float(rows[-1].get("angle", 90.0)) if rows else 90.0
    return {"theta_y": (main + shift_y) % 360, "theta_x": (main + GOLDEN_DEG + shift_x) % 360, "rows": rows}


def focus(shift_y: float = None, shift_x: float = None, write: bool = True) -> Dict:
    fv = _load(FOVEA, {})
    sy = fv.get("shift_y", 0.0) if shift_y is None else shift_y
    sx = fv.get("shift_x", 0.0) if shift_x is None else shift_x
    # the governor (chain.py): a shift may drag the whole chain, but not snap a second link while a
    # bubble is still open — clamp tonight's move to max_shift_deg from where the rings were
    lim = fv.get("max_shift_deg")
    if lim is not None:
        py, px = fv.get("shift_y", 0.0), fv.get("shift_x", 0.0)
        sy = py + max(-lim, min(lim, sy - py)); sx = px + max(-lim, min(lim, sx - px))
    ends = ring_ends(sy, sx)
    c = chord(ends["theta_y"], ends["theta_x"])
    half = c["law"]["theta_deg"]
    seen = {}
    for r in ends["rows"]:
        w = (r.get("pointer") or {}).get("world")
        if not w: continue
        a = float(r.get("angle", 0.0))
        off = abs((a - c["direction_deg"] + 180) % 360 - 180)
        if off <= half: seen[w] = min(seen.get(w, 999), round(off, 1))
    out = {"t": time.time(), "shift_y": round(sy, 2), "shift_x": round(sx, 2), "max_shift_deg": fv.get("max_shift_deg"), **c,
           "in_focus": sorted(seen, key=seen.get), "offsets": seen,
           "reading": (f"chord from the context ring at {c['theta_y']} deg to the side ring at {c['theta_x']} deg: "
                       f"{c['separation_deg']} deg apart -> shave depth {c['depth']} (opening {c['law']['opening']}, "
                       f"half-angle {half} deg, reach {c['law']['reach']}), facing {c['direction_deg']} deg; "
                       f"{len(seen)} worlds in focus: {', '.join(sorted(seen, key=seen.get)[:6]) or 'none'}")}
    if write:
        try:
            os.makedirs(os.path.dirname(FOCUS), exist_ok=True)
            json.dump(out, open(FOCUS, "w", encoding="utf-8"), indent=1)
            fv.update({"shaves": fv.get("shaves", 1), "depth": c["depth"], "shift_y": sy, "shift_x": sx,
                       "derived_from": "chord.py — the tunnel between the two ring sets", "t": time.time()})
            json.dump(fv, open(FOVEA, "w", encoding="utf-8"), indent=1)
        except Exception: pass
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shift-y", type=float, default=None); ap.add_argument("--shift-x", type=float, default=None)
    ap.add_argument("--table", action="store_true", help="depth and reach across separations")
    a = ap.parse_args()
    if a.table:
        print("separation  depth   opening  half-angle  reach")
        for sep in (30, 60, 90, 120, GOLDEN_DEG, 150, 180):
            c = chord(sep, 0.0); l = c["law"]
            print(f"{sep:9.1f}  {c['depth']:.3f}   {l['opening']:.3f}    {l['theta_deg']:6.2f}   {l['reach']:.3f}")
        sys.exit(0)
    print("focus:", focus(a.shift_y, a.shift_x)["reading"])
