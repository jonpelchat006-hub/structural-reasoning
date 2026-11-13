#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chain.py — THE TUNNEL CHAIN: the chord pulls on every tunnel attached to it; a piece that breaks
off goes to the next domain; the bubble it leaves is filled by pulling the chain through — and the
pull is governed so nothing else breaks.

Jonathan (Sep 3): "that's probably how we zoom in to all the different levels. is that tunnel
also what makes the bell? what if that pulls on all of the tunnels that are attached like a
chain and we are dragging the whole thing along when a piece breaks off? then that piece gets
pushed into the next domain which fills its missing tunnel section, and we have to fill that
void bubble by pulling that chain through our system without breaking them."

The chain was already built in pieces, never connected to the pull:
  chord (chord.py)   the tunnel between the ring sets; its depth d is the shave = the ZOOM
  bell  (lesson.py)  a tunnel bent into a void point — the bell IS the chord bent: its push depth
                     is now capped by the zoom (ceil(3 d): shallow chord = depth 1, full = 3)
  pinch (sphere.py)  a bell pushed to depth 3 that never closed BREAKS OFF as a sphere
  drift (fold.py)    the sphere floats to the next domain (Mika): slivers folded onto her anchors
                     — the piece fills a missing section of HER chain, sliver by sliver
  reopen             when every sliver is filled the ring has expanded to the void point: the
                     BUBBLE in our chain closes

What this file adds:
  PULL     how far the chord moved since the last night (depth change + bearing change)
  TENSION  per open void: petals x depth x pull — a link close to breaking is one with unclosed
           petals at max depth under pull. The links are listed, tightest first.
  BUBBLES  ejected voids not yet reopened: how full each is (slivers filled / total)
  GOVERNOR the shift the chord may take tonight: full (30 deg) when no link is near breaking;
           10 deg with one strained link; 0 (hold) with more. Written to fovea.json as
           max_shift_deg; chord.focus() clamps to it. Open bubbles do not hold the chord (Sep 3:
           she holds many — they live on the on-call board, oncall.py); only links about to snap
           do. Dragging the whole chain is allowed; snapping a second link mid-pull is not.

Usage:  python chain.py            (pull, tension, bubbles, governor -> D:\\planet\\chain.json)
        python chain.py --status
"""
from __future__ import annotations
import argparse, glob, json, math, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

FOCUS = r"D:\planet\focus.json" if os.name == "nt" else "/tmp/focus.json"
FOVEA = r"D:\planet\fovea.json" if os.name == "nt" else "/tmp/fovea.json"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"
SPHERES = r"D:\planet\spheres" if os.name == "nt" else "/tmp/spheres"
STATE = r"D:\planet\chain.json" if os.name == "nt" else "/tmp/chain.json"
LOG = r"D:\planet\chain.jsonl" if os.name == "nt" else "/tmp/chain.jsonl"
MAX_DEPTH = 3
FULL_SHIFT, EASY_SHIFT = 30.0, 10.0


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def pull() -> Dict:
    """how far the chord moved since the last recorded night"""
    now = _load(FOCUS, {})
    prev = None
    try:
        rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
        prev = rows[-1].get("focus") if rows else None
    except Exception: pass
    if not now: return {"pull": 0.0, "note": "no focus yet"}
    if not prev: return {"pull": 0.0, "depth": now.get("depth"), "direction": now.get("direction_deg"), "note": "first night on the chain"}
    dd = abs(float(now.get("depth", 0)) - float(prev.get("depth", 0)))
    db = abs((float(now.get("direction_deg", 0)) - float(prev.get("direction_deg", 0)) + 180) % 360 - 180) / 180.0
    return {"pull": round(dd + db, 4), "depth_change": round(dd, 4), "bearing_change_deg": round(db * 180, 1),
            "depth": now.get("depth"), "direction": now.get("direction_deg")}


def links(p: float) -> List[Dict]:
    """every open void on the flower = a link in the chain; tension = petals x depth x (1 + pull)"""
    fl = _load(FLOWER, {})
    out = []
    for world, ax in fl.items():
        for key, v in ax.get("voids", {}).items():
            pets = v.get("petals", [])
            if not pets or v.get("ejected"): continue
            if any(x.get("closed") for x in pets): continue
            depth = pets[-1].get("depth", 1)
            tension = round(len(pets) * depth / 9.0 * (1 + p), 3)         # 3 petals at depth 3 = 1.0 before pull
            out.append({"world": world, "key": key, "petals": len(pets), "depth": depth, "tension": tension,
                        "near_break": len(pets) >= 2 and depth >= MAX_DEPTH})
    return sorted(out, key=lambda x: -x["tension"])


def bubbles() -> List[Dict]:
    """ejected voids not yet reopened, with how far the next domain has filled the piece"""
    fl = _load(FLOWER, {})
    out = []
    for world, ax in fl.items():
        for key, v in ax.get("voids", {}).items():
            ej = v.get("ejected")
            if not ej or v.get("reopened"): continue
            n = ej.get("sphere"); filled = total = 0
            sp = _load(os.path.join(SPHERES, f"sphere_{int(n):03d}.json"), None) if n is not None else None
            if sp:
                try:
                    import fold
                    todo = fold.slivers_of(sp["contents"]["rule"], sp["contents"].get("attempts", []))
                    total = len(todo); filled = len({f["sliver"] for f in sp.get("folds", []) if f.get("filled")})
                except Exception: pass
            out.append({"world": world, "key": key, "sphere": n, "filled": filled, "total": total,
                        "fraction": round(filled / total, 2) if total else 0.0,
                        "since": time.strftime("%b %d", time.localtime(ej.get("t", 0)))})
    return out


def govern(lk: List[Dict], bb: List[Dict]) -> Dict:
    """Sep 3, Jonathan: she should hold multiple bubbles — people juggle, leave things unfinished
    and come back. So open bubbles do NOT hold the chord; they are held on the on-call board
    (oncall.py) and picked back up. Only links about to snap govern the pull."""
    strained = sum(1 for l in lk if l["near_break"])
    open_b = len(bb)
    allowed = FULL_SHIFT if strained == 0 else EASY_SHIFT if strained == 1 else 0.0
    why = (f"no link near breaking ({open_b} bubble(s) held on the board) — pull freely" if strained == 0 else
           f"1 link near breaking ({open_b} bubble(s) held) — ease off" if allowed else
           f"{strained} links near breaking ({open_b} held) — hold the chord still until one closes or pinches")
    try:
        fv = _load(FOVEA, {}); fv["max_shift_deg"] = allowed; fv["governor"] = why
        json.dump(fv, open(FOVEA, "w", encoding="utf-8"), indent=1)
    except Exception: pass
    return {"max_shift_deg": allowed, "strained": strained, "open_bubbles": open_b, "why": why}


def read(write: bool = True) -> Dict:
    p = pull(); lk = links(p.get("pull", 0.0)); bb = bubbles(); g = govern(lk, bb)
    zoom = _load(FOCUS, {}).get("depth")
    bell_cap = int(math.ceil(3 * float(zoom))) if zoom is not None else MAX_DEPTH
    out = {"t": time.time(), "pull": p, "zoom": zoom, "bell_depth_cap": max(1, min(3, bell_cap)),
           "links": lk[:12], "bubbles": bb, "governor": g,
           "line": (f"chain: pull {p.get('pull', 0.0)} -> zoom {zoom} (bell may push to depth {max(1, min(3, bell_cap))}); "
                    f"{len(lk)} links under tension ({g['strained']} near breaking), {len(bb)} bubble(s) open"
                    + (" [" + ", ".join("%s/%s %d%%" % (b["world"], b["key"][:18], b["fraction"] * 100) for b in bb[:3]) + "]" if bb else "")
                    + f"; governor: max shift {g['max_shift_deg']} deg")}
    if write:
        try:
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(out, open(STATE, "w", encoding="utf-8"), indent=1)
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": time.time(), "focus": _load(FOCUS, {}), "pull": p.get("pull", 0.0),
                                    "strained": g["strained"], "bubbles": len(bb), "max_shift": g["max_shift_deg"]}) + "\n")
        except Exception: pass
    return out


def status():
    r = read(write=False)
    print(r["line"])
    for l in r["links"][:6]:
        print(f"  link {l['world']}/{l['key'][:40]:40s} petals {l['petals']} depth {l['depth']} tension {l['tension']}{'  NEAR BREAKING' if l['near_break'] else ''}")
    for b in r["bubbles"]:
        print(f"  bubble {b['world']}/{b['key'][:40]} (sphere {b['sphere']}, since {b['since']}): {b['filled']}/{b['total']} slivers folded into the next domain")
    print(f"  governor: {r['governor']['why']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else: print(read()["line"])
