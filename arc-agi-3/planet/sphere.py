#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sphere.py — the PINCH-OFF: when the push breaks the tunnel's attachment, a sphere is born.

Jonathan (Aug 31): "what if something pushes in really deep and breaks the tunnel's attachment
to the ring? could that close off and cut off the line segment that was pushing? what if that's
how a sphere generator is made? it would be a thing neither side could figure out, but we would
keep the parts that were inside the bell shape and the lines that were there as sources, and
then send that out as some mass. I think that would be the sphere generator from earlier."

It is. SPHERE_GENERATOR.md's central law (§C.2): CLOSURE FAILURE IS THE BIRTH CONDITION FOR A
PRIMITIVE — "where the required width stops matching the local zone, the system is forced to
mint a new primitive." This file is that law's physical mechanism, and the mechanism is real
physics everywhere membranes exist: push into a membrane deep enough and the neck closes behind
the intruder — a vesicle buds off (endocytosis), a droplet detaches (Rayleigh-Plateau), a
plasmoid is ejected (magnetic reconnection). The bell that could not teach becomes the membrane
that engulfs.

The trigger, measured, never guessed: a void point whose flower shows the coupling FAILED AT
FULL DEPTH — at least PINCH_AFTER petals, none closed, the latest at maximum depth. The bell
rang as deep as it goes and the rule still would not cross; neither side could figure it out.
Ringing forever would be the infinite-lesson trap. Instead the attachment breaks and the pinch
runs:

  1. KEEP WHAT WAS INSIDE THE BELL — the rule itself, its neighboring rules at full depth, and
     every answer the novice gave (the failed attempts are part of the mass: they show where
     the words bounced off).
  2. KEEP THE LINES THAT WERE THERE AS SOURCES — the story path, the world (the axis), the
     core, the ring sections pointing at that world. The sphere is sealed but ADDRESSED: every
     line inside points back to where it came from.
  3. SEND IT OUT AS MASS — sphere_<n>.json into D:\planet\spheres\, and a copy into the
     network's L7-imagination zone (incoming unverified — exactly the zone for a thing nobody
     here could verify), where any other node (the Erdős machine, a cloud, a future Mira) can
     pick it up. A work order is posted so sleeping nodes see it.
  4. THE ATTACHMENT STAYS BROKEN — the void is marked ejected in the flower; the bell stops
     ringing on it. The flower keeps the petals as the scar: the record that teaching was
     tried, how deep, and when the sphere left.

A sphere coming BACK — another domain answers it — is the minted primitive arriving; land it by
scoring the returned answer against the sealed rule (the capsule carries everything needed).

Usage:  python sphere.py            (scan flowers; pinch off every void that has broken through)
        python sphere.py --status  (spheres generated, where they went, what came back)
        python sphere.py --demo    (fixture a broken void and watch the pinch)
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"
SPHERES = r"D:\planet\spheres" if os.name == "nt" else "/tmp/spheres"
PINCH_AFTER = 3                 # open petals, none closed, latest at max depth -> the neck closes
MAX_DEPTH = 3


def _load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default


def _ring_sources(world: str) -> List[Dict]:
    try:
        import ring as R
        rows = R._tail_jsonl(R.RING, 100000)
        return [{"n": r["n"], "angle": r["angle"], "kind": r["kind"], "label": r["label"][:90]}
                for r in rows if r.get("pointer", {}).get("world") == world][-5:]
    except Exception:
        return []


def broken_voids() -> List[Dict]:
    """Voids where the push went all the way in and the coupling still failed."""
    fl = _load(FLOWER, {})
    out = []
    for world, ax in fl.items():
        for key, v in ax.get("voids", {}).items():
            pets = v.get("petals", [])
            if v.get("ejected") or len(pets) < PINCH_AFTER: continue
            if any(p["closed"] for p in pets): continue
            if pets[-1]["depth"] < MAX_DEPTH: continue
            out.append({"world": world, "key": key, "petals": pets})
    return out


def pinch(vp: Dict) -> str:
    """The neck closes: seal contents + sources, send the mass out, break the attachment."""
    world, key = vp["world"], vp["key"]
    # what was inside the bell: the rule, its full-depth neighbors, every failed attempt
    story, spath, rule, neighbors, attempts = None, None, None, [], []
    for p in sorted(glob.glob(os.path.join(OCEAN, world, "stories", "story_*.json")),
                    key=os.path.getmtime)[::-1]:
        s = _load(p, {})
        invs = s.get("invariants", [])
        idx = next((i for i, v in enumerate(invs) if v.get("key", v.get("text", "")[:30]) == key), None)
        if idx is None: continue
        story, spath = s, p
        rule = invs[idx]
        neighbors = invs[max(0, idx - (MAX_DEPTH - 1)):idx]
        for side in ("mika_teach_back", "duet"):
            blk = s.get(side) or {}
            a = blk.get("answer") or (blk.get("answers", {}) or {}).get("mika")
            if a: attempts.append({"via": side, "answer": a[:800]})
        break
    if rule is None: return ""
    os.makedirs(SPHERES, exist_ok=True)
    n = len(glob.glob(os.path.join(SPHERES, "sphere_*.json"))) + 1
    sp = {"n": n, "t": time.time(), "born_of": "pinch-off",
          "why": "neither side could figure it out: "
                 f"{len(vp['petals'])} bells, none closed, last at depth {vp['petals'][-1]['depth']}",
          "contents": {"rule": rule, "neighbors": neighbors, "attempts": attempts,
                       "petals": vp["petals"]},
          "sources": {"world": world, "story": spath, "story_n": story.get("n"),
                      "core": sorted(glob.glob(os.path.join(OCEAN, world, "core_*.json")))[-1:],
                      "ring": _ring_sources(world)},
          "ask": "From the rule and the failed attempts inside, produce a NEW way to state or "
                 "decompose this rule that a novice could recover — a minted primitive.",
          "answer": None}
    p = os.path.join(SPHERES, f"sphere_{n:03d}.json")
    json.dump(sp, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    # send it out as mass: the network's incoming-unverified zone + a work order
    try:
        import network as N
        if N.available():
            import shutil
            d = os.path.join(N.NETWORK, "L7-imagination", "spheres")
            os.makedirs(d, exist_ok=True)
            shutil.copy2(p, d)
            N.post("distill", os.path.join(OCEAN, world),
                   note=f"sphere {n}: unteachable rule '{key}' pinched off — see L7-imagination/spheres")
    except Exception: pass
    # the attachment stays broken: mark the flower; the bell stops ringing here
    fl = _load(FLOWER, {})
    fl[world]["voids"][vp["key"]]["ejected"] = {"t": time.time(), "sphere": n}
    json.dump(fl, open(FLOWER, "w", encoding="utf-8"), indent=1)
    return p


def status() -> None:
    caps = sorted(glob.glob(os.path.join(SPHERES, "sphere_*.json")))
    if not caps: print("no spheres — no coupling has broken through yet"); return
    for p in caps:
        s = _load(p, {})
        back = "answered" if s.get("answer") else "out as mass"
        print(f"sphere {s.get('n')}: {s.get('sources', {}).get('world')} / "
              f"'{s.get('contents', {}).get('rule', {}).get('key', '?')}' — {back} ({s.get('why', '')[:70]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.status: status(); return
    if a.demo:
        fl = _load(FLOWER, {})
        ax = fl.setdefault("dead_cells", {"axis": "dead_cells", "voids": {}})
        ax["voids"]["door+key"] = {"petals": [
            {"t": time.time() - 3, "angle": 0, "ring": 1, "depth": 1, "closed": False, "instrument": "bell"},
            {"t": time.time() - 2, "angle": 60, "ring": 1, "depth": 2, "closed": False, "instrument": "bell"},
            {"t": time.time() - 1, "angle": 120, "ring": 1, "depth": 3, "closed": False, "instrument": "bell"}]}
        os.makedirs(os.path.dirname(FLOWER), exist_ok=True)
        json.dump(fl, open(FLOWER, "w", encoding="utf-8"), indent=1)
    born = [pinch(v) for v in broken_voids()]
    born = [b for b in born if b]
    if born:
        for b in born: print(f"pinch-off: the neck closed -> {b}")
    else:
        print("no broken attachments — every open void is still being taught")


if __name__ == "__main__":
    main()
