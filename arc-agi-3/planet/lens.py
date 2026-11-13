#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lens.py — THE ORTHOGONAL RINGS: putting yourself in other shoes, at measured distances.

Jonathan (Sep 1): "we can also put ourselves in others' shoes and see it from further away.
wouldn't the orthogonal rings be able to connect, and we can have eyes on that axis which
would be different kinds of reasoning. the eyes on those rings would be CENTERED ON A VOID
POINT on the normal plane when in use — that's where the tunnels start, inside that bell when
it breaks. on that ring it would ROTATE and explore branches — the tunnel gets broken down on
each ring, and we bridge each ring eye to eye with one tunnel per bridge. a close ring that
rotates would be like 'can you see it from another person's perspective', further out would
be someone who's in a different country, and out to how animals would see it."

The mirror (ARC_MIRROR) was the eye looking IN; this is the eye stepping OUT — and the
distance ordering is the real structure of perspective-taking: another person in the room,
then a stranger with a different life, then a different Umwelt entirely. Made mechanical:

  THE EYE CENTERS ON A VOID POINT — the lens only engages where teaching is STUCK: an open
      void the bell has struck at least twice without closing (and not yet pinched off).
      That is exactly "inside the bell when it breaks" — the window between bell and sphere.
  ONE TUNNEL PER BRIDGE — each attempt is one bridge, eye to eye: the planet's voice RETELLS
      the rule from the ring's perspective (the tunnel unraveled into that ring's branches),
      and Mika recovers the PLAIN rule from the retelling. Recovery is scored against the
      original invariant by the one scorer — the perspective must round-trip.
  ROTATION — a failed persona rotates to the next eye on the SAME ring. A full rotation
      that fails steps OUT one ring: the perspective gets more foreign only after the
      nearer ring is exhausted.
  THE RINGS (close -> far):
      ring 1, another person   : a rival player; the door itself; a patient teammate
      ring 2, another life     : a chef writing a recipe; a border guard; a sailor
      ring 3, another creature : a dog (smell and motion); a bee (light and direction);
                                 an octopus (touch and taste by arm)
  WHAT IT LEAVES — a closure lays a petal on the void's flower with instrument "lens-r<N>"
      and the persona recorded, so the flower shows WHICH DISTANCE finally landed the rule.
      Over time that is the empathy-distance curve: which voids need a neighbor's eyes, and
      which need a bee's.

Usage:  python lens.py             (one bridge on the most stubborn eligible void; sleep-chained)
        python lens.py --status
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import lesson as L                      # void points, flower, petal, _invs, _load
BRIDGE = "http://localhost:41737"
MIN_BELLS = 2                           # the lens engages only where the bell has failed twice

RINGS = [
    ("another person", ["a rival player who wants you to lose",
                        "the door itself, tired of being pushed",
                        "a patient teammate whispering during the game"]),
    ("another life",   ["a chef writing it as a recipe step",
                        "a border guard explaining a crossing rule",
                        "an old sailor telling it as a rule of the sea"]),
    ("another creature", ["a dog who knows the world by smell and motion",
                          "a bee who knows the world by light and direction",
                          "an octopus who tastes everything through its arms"]),
]


def _chat(text, timeout=240):
    import requests
    r = requests.post(BRIDGE + "/chat", json={"text": text}, timeout=timeout).json()
    if isinstance(r, dict) and r.get("ok") is False: return None
    return r.get("reply") or r.get("response") or r.get("text")


def _voice(text, timeout=240):
    import requests
    r = requests.post("http://localhost:11434/api/generate",
                      json={"model": "planet-voice", "prompt": text, "stream": False},
                      timeout=timeout).json()
    return r.get("response")


def _stuck_void() -> Optional[Dict]:
    """The eye's center: an open void, belled >= MIN_BELLS times, not ejected."""
    fl = L._load(L.FLOWER, {})
    vps = L.void_points()
    for vp in vps:
        v = fl.get(vp["world"], {}).get("voids", {}).get(vp["key"], {})
        pets = v.get("petals", [])
        if v.get("ejected") or not pets: continue
        if any(p["closed"] for p in pets): continue
        if len([p for p in pets if p.get("instrument", "bell") == "bell"]) >= MIN_BELLS:
            vp["lens_tried"] = len([p for p in pets if str(p.get("instrument", "")).startswith("lens")])
            return vp
    return None


def bridge_once(ask_voice=None, ask_mika=None) -> Optional[Dict]:
    from storyteller import score_extraction
    vp = _stuck_void()
    if vp is None:
        print("no stuck voids — every open void is still in the bell's hands"); return None
    story = L._load(vp["path"], {})
    inv = [v for v in L._invs(story) if v["key"] == vp["key"]]
    if not inv: print("the void's rule is gone from its story"); return None
    rule = inv[0]["text"]
    # rotation: which eye on which ring, from how many lens petals already laid
    k = vp["lens_tried"]
    ring_i = min(len(RINGS) - 1, k // 3)
    persona = RINGS[ring_i][1][k % 3]
    ring_name = RINGS[ring_i][0]
    ask_voice = ask_voice or _voice
    ask_mika = ask_mika or _chat
    try:
        retold = ask_voice(f"Retell this game rule in ONE short vivid line, strictly from the "
                           f"point of view of {persona}. Keep every number and direction "
                           f"exact, but use their voice and their senses.\nRULE: {rule}")
    except Exception as e:
        print(f"the voice eye is closed ({str(e)[:70]})"); return None
    if not retold: print("the retelling came back empty"); return None
    retold = retold.strip().splitlines()[0][:300]
    try:
        answer = ask_mika(f"Someone described a rule of a small world like this:\n\"{retold}\"\n"
                          f"Say the rule PLAINLY in one line — no character voice, keep every "
                          f"number and direction exactly.")
    except Exception as e:
        print(f"the novice eye is closed ({str(e)[:70]})"); return None
    closed = bool(answer) and score_extraction(answer, inv)["per_invariant"][0]["recovered"]
    pt = L.petal(vp["world"], vp["key"], depth=ring_i + 1, closed=closed,
                 instrument=f"lens-r{ring_i + 1}")
    row = {"t": time.time(), "world": vp["world"], "key": vp["key"], "ring": ring_i + 1,
           "ring_name": ring_name, "persona": persona, "retold": retold,
           "answer": (answer or "")[:300], "closed": closed}
    lp = L.FLOWER.replace("flower.json", "lens.jsonl")
    with open(lp, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"lens: '{vp['key'][:40]}' seen through {persona} (ring {ring_i + 1}, {ring_name}) -> "
          + ("CLOSED — that distance could see it "
             f"(petal {pt['angle']} deg)" if closed else "still open — the ring rotates"))
    return row


def status():
    lp = L.FLOWER.replace("flower.json", "lens.jsonl")
    try:
        rows = [json.loads(l) for l in open(lp, encoding="utf-8") if l.strip()]
    except Exception:
        print("the orthogonal rings have never turned"); return
    closed = [r for r in rows if r["closed"]]
    print(f"{len(rows)} bridges, {len(closed)} closures")
    for r in rows[-6:]:
        print(f"  ring {r['ring']} ({r['persona'][:34]}): '{r['key'][:34]}' -> "
              f"{'CLOSED' if r['closed'] else 'open'}")
    by_ring = {}
    for r in closed: by_ring[r["ring"]] = by_ring.get(r["ring"], 0) + 1
    if by_ring: print("  the empathy-distance curve so far:", by_ring)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else: bridge_once()
