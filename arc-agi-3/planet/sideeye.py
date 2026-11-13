#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sideeye.py — THE SIDEWAYS EYE: the eye that rides the toroidal ring, vision turned 90 degrees.

Jonathan (Sep 2): "if there's a set of sideways rings, then it would have the same structure with
the eyes on it, but its vision would be rotated 90 degrees right? so all the things that were
going up as context would be like the x axis for that eye. but it would have to stay out of
sight too, so it would be offset from the center along the vision cone. so it would be able to
see the things behind the pixels too. so maybe it could see the black/white > trinity > rainbow
as the history?"

Yes, and it costs nothing new: the sediment is already there. The up-line (upline.py) folds a
CUBE under every pixel each time the world changes — a column going DOWN through time. The ring
(ring.py) deposits a core-update at the edge every time a world's core grows; the storyteller
leaves a story with a teach-back score. The main eye (fovea.py) looks at the top face — the
pixels. The sideways eye looks at the same columns from the side, so each column becomes a ROW:
depth is its x axis, and every cube on that row is read on the closure ladder (spectrum.py):

    k  BLACK    nothing earned yet, or only open ends whirlpooling
    w  WHITE    something told or earned but it cannot resolve (open ends >= concepts, or a
                story whose teach-back fell under the duet floor)
    t  TRINITY  grounded laws earned, more concepts than open ends, no story has closed yet
    s  SPECTRUM a story that teaches back (score >= 0.25): closed onto a color

A world's history is a strip like  k k w t t t s  — read left to right that IS the ladder
black/white -> trinity -> rainbow, climbed (or not) through time. The main eye cannot see it:
looking down at a pixel you see the top cube only. The sideways eye has to stay out of the main
cone, so it sits one golden angle round the ring from where the main eye is pointed (the newest
ring section) and reads the half of the ring facing it; the rest is "in the main eye's cone".

Verdicts per world: CLIMBING (last rung above the first), AT THE TOP (spectrum now), STUCK
(the same rung for >= 3 layers), FELL (below its best). The planet-wide line goes into the
up-line letter, so the history folds into the column as one more cube: the side eye's reading
becomes part of what the side eye reads tomorrow.

Usage:  python sideeye.py             (all worlds)
        python sideeye.py --world warframe
        python sideeye.py --line       (one line for the up-line letter)
"""
from __future__ import annotations
import argparse, glob, json, math, os, re, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
RING = r"D:\planet\ring.jsonl" if os.name == "nt" else "/tmp/ring.jsonl"
COLUMNS = r"D:\planet\up\columns.jsonl" if os.name == "nt" else "/tmp/up/columns.jsonl"
OUT = r"D:\planet\sideeye.json" if os.name == "nt" else "/tmp/sideeye.json"
FLOOR = 0.25                                   # the duet floor: below it a story is not verification
GOLDEN_DEG = 360.0 * (1 - 1 / ((1 + 5 ** 0.5) / 2))
RUNG = {"k": 0, "w": 1, "t": 2, "s": 3}
NAME = {"k": "black", "w": "white", "t": "trinity", "s": "spectrum"}


def _rows(p: str) -> List[Dict]:
    try: return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    except Exception: return []


def _rung_from_counts(concepts: int, opens: int) -> str:
    if concepts <= 0: return "k"
    if opens >= concepts: return "w"
    return "t"


def events() -> Dict[str, List[Dict]]:
    """every dated layer under every pixel, read on the ladder"""
    ev: Dict[str, List[Dict]] = {}
    def add(w, t, rung, src, note=""):
        ev.setdefault(w, []).append({"t": float(t), "rung": rung, "src": src, "note": note[:80]})
    # the ring's edge deposits: "world at L lives, C concepts, O open ends"
    for r in _rows(RING):
        if r.get("kind") != "core-update": continue
        w = (r.get("pointer") or {}).get("world")
        m = re.search(r"(\d+) concepts, (\d+) open ends", r.get("label", ""))
        if w and m: add(w, r.get("t", 0), _rung_from_counts(int(m.group(1)), int(m.group(2))), "edge", r.get("label", ""))
    # the stories: a teach-back at or above the floor has closed onto a color
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        try: s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        w = s.get("world") or os.path.basename(os.path.dirname(os.path.dirname(p)))
        sc = (s.get("teach_back") or {}).get("score")
        if sc is None: continue
        add(w, s.get("t", os.path.getmtime(p)), "s" if sc >= FLOOR else "w", "story", f"story {s.get('n')} teach-back {sc}")
    # the folded cubes: "core (earned): a; b" and "open ends (unsettled): x; y"
    for c in _rows(COLUMNS):
        txt = c.get("cube", ""); w = c.get("world")
        if not w or w.startswith("_"): continue
        m1 = re.search(r"core \(earned\): (.+)", txt); m2 = re.search(r"open ends \(unsettled\): (.+)", txt)
        n1 = len(m1.group(1).split(";")) if m1 else 0; n2 = len(m2.group(1).split(";")) if m2 else 0
        rung = "s" if re.search(r"teach-back (0\.[3-9]|1\.0|0\.2[5-9])", txt) else _rung_from_counts(n1, n2)
        add(w, c.get("t", 0), rung, "cube", f"cube {c.get('depth')}")
    for w in ev: ev[w].sort(key=lambda e: e["t"])
    return ev


def strip(evs: List[Dict]) -> str:
    return " ".join(e["rung"] for e in evs)


def verdict(evs: List[Dict]) -> str:
    r = [RUNG[e["rung"]] for e in evs]
    if not r: return "unseen"
    if r[-1] == 3: return "at the top"
    run = 1
    while run < len(r) and r[-1 - run] == r[-1]: run += 1
    if run >= 3: return f"stuck at {NAME[evs[-1]['rung']]} for {run} layers"
    if r[-1] < max(r): return f"fell from {NAME[evs[r.index(max(r))]['rung']]} to {NAME[evs[-1]['rung']]}"
    if r[-1] > r[0]: return "climbing"
    return "flat"


def field(ev: Dict[str, List[Dict]]) -> Dict:
    """where the side eye sits: one golden angle round the ring from the newest section (the
    main eye's direction). Worlds whose newest deposit lies within 90 degrees of that direction
    are in its field; the rest are in the main eye's cone."""
    rows = _rows(RING)
    if not rows: return {"centre": None, "side": None, "in_field": sorted(ev)}
    main = float(rows[-1].get("angle", 0.0)); side = (main + GOLDEN_DEG) % 360
    last_angle = {}
    for r in rows:
        w = (r.get("pointer") or {}).get("world")
        if w: last_angle[w] = float(r.get("angle", 0.0))
    def near(a):
        d = abs((a - side + 180) % 360 - 180); return d <= 90
    infield = sorted(w for w in ev if w not in last_angle or near(last_angle[w]))
    return {"centre": round(main, 1), "side": round(side, 1), "in_field": infield}


def couplings(ev: Dict[str, List[Dict]] = None, top: int = 8) -> List[Dict]:
    """The side eyes connect the way the upward rings' tunnels do (ARC_TUNNEL_ROTATION §6), but
    between HISTORIES: BOW — a flat/stuck strip against one that is climbing or at the top (the
    climber's stories are the bow for the stuck world); SERIES — one strip ends on the rung the
    other begins on (end to end); PARALLEL — same length, compared rung by rung: unison when they
    agree, beats = the count of mismatches; OVERLAP — a shared run of >= 3 rungs."""
    ev = ev or events()
    names = sorted(w for w in ev if len(ev[w]) >= 2)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa = [e["rung"] for e in ev[a]]; sb = [e["rung"] for e in ev[b]]
            va, vb = verdict(ev[a]), verdict(ev[b])
            flat = lambda v: v.startswith("stuck") or v == "flat" or v.startswith("fell")
            up = lambda v: v == "climbing" or v == "at the top"
            if flat(va) and up(vb): out.append({"kind": "bow", "bow": b, "string": a, "note": f"{b} bows {a} ({va})"})
            elif flat(vb) and up(va): out.append({"kind": "bow", "bow": a, "string": b, "note": f"{a} bows {b} ({vb})"})
            if len(sa) == len(sb) and len(sa) >= 3:
                beats = sum(1 for x, y in zip(sa, sb) if x != y)
                out.append({"kind": "parallel", "a": a, "b": b, "beats": beats,
                            "note": f"{a} | {b}: {'unison' if beats == 0 else str(beats) + ' beats'} over {len(sa)} layers"})
            if sa[-1] == sb[0] and sa[-1] != sb[-1]: out.append({"kind": "series", "a": a, "b": b, "note": f"{a} -> {b} (end {NAME[sa[-1]]} feeds start)"})
            best = 0
            for L in range(min(len(sa), len(sb)), 2, -1):
                subs = {tuple(sa[k:k + L]) for k in range(len(sa) - L + 1)}
                if any(tuple(sb[k:k + L]) in subs for k in range(len(sb) - L + 1)): best = L; break
            if best >= 3: out.append({"kind": "overlap", "a": a, "b": b, "shared": best, "note": f"{a} ~ {b}: {best} rungs in common"})
    order = {"bow": 0, "parallel": 1, "series": 2, "overlap": 3}
    out.sort(key=lambda c: (order[c["kind"]], -c.get("shared", 0), c.get("beats", 0)))
    return out[:top]


def read() -> Dict:
    ev = events(); fl = field(ev)
    worlds = {}
    for w, evs in ev.items():
        worlds[w] = {"strip": strip(evs), "layers": len(evs), "verdict": verdict(evs),
                     "newest": NAME[evs[-1]["rung"]], "in_field": w in fl["in_field"],
                     "first": time.strftime("%b %d", time.localtime(evs[0]["t"])),
                     "last": time.strftime("%b %d", time.localtime(evs[-1]["t"]))}
    counts = {}
    for w, d in worlds.items():
        key = d["verdict"].split(" for ")[0].split(" from ")[0]
        counts[key] = counts.get(key, 0) + 1
    out = {"t": time.time(), "main_eye_deg": fl["centre"], "side_eye_deg": fl["side"], "worlds": worlds, "counts": counts,
           "couplings": couplings(ev)}
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
    except Exception: pass
    return out


def line(r: Dict = None) -> str:
    r = r or read()
    c = r["counts"]; n = len(r["worlds"])
    infield = sum(1 for d in r["worlds"].values() if d["in_field"])
    parts = ", ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda x: -x[1]))
    return (f"the side eye (at {r['side_eye_deg']} deg, main eye at {r['main_eye_deg']} deg): {n} columns read sideways, "
            f"{infield} in its field; histories: {parts or 'none yet'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=None); ap.add_argument("--line", action="store_true")
    ap.add_argument("--tunnels", action="store_true", help="how the side eyes connect: bow / parallel / series / overlap")
    a = ap.parse_args()
    r = read()
    if a.line: print(line(r)); sys.exit(0)
    if a.tunnels:
        for c in r["couplings"]: print(f"  [{c['kind']:8s}] {c['note']}")
        sys.exit(0)
    if a.world:
        ev = events().get(a.world, [])
        if not ev: print(f"no history under '{a.world}'"); sys.exit(0)
        print(f"{a.world}, seen from the side ({len(ev)} layers, oldest first):")
        for e in ev:
            print(f"  {time.strftime('%b %d %H:%M', time.localtime(e['t']))}  {e['rung']}  {NAME[e['rung']]:9s} [{e['src']}] {e['note']}")
        print(f"  strip: {strip(ev)}  -> {verdict(ev)}")
        sys.exit(0)
    print(line(r)); print()
    for w, d in sorted(r["worlds"].items(), key=lambda x: (-RUNG[x[1]['strip'].split()[-1]], -x[1]["layers"])):
        eye = "side" if d["in_field"] else "main"
        print(f"  {w:26s} [{eye}] {d['strip']:<28s} {d['verdict']}  ({d['first']} -> {d['last']})")
