#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lesson.py — the BELL COUPLING and the FLOWER OF LIFE on the void line: targeted teaching.

Jonathan (Aug 31): "what if that's how we make the flower of life around the void line too? One
tunnel would have to be fixed to a void point — that's where it would want to end. Then the
expert tunnel would just have to have that point somewhere inside, and could point somewhere
deeper too. Bending the tunnel happens when one tunnel pushes against the other — it would be
like a bell. How deep it goes would be like a song that teaches a lot or just hits hard. The
novice void point would already have lines connecting it, so we use one of those lines that
lead back to novice territory as the axis to build the flower on. Then we can use that line to
attach more instruments and make more of a band."

Made concrete, every piece:

  VOID POINT — a rule the novice measurably failed to recover. Mika's teach-back answers are
      stored in the story jsons; re-scoring them per-invariant (the scorer already reports
      recovered per rule) yields the exact missed rules. A void point is not a metaphor: it is
      {world, story n, rule key} with a failing score attached.
  THE NOVICE TUNNEL fixed to it — her next pass is aimed to END exactly there: she is asked
      for that one rule, nothing else.
  THE EXPERT TUNNEL containing it, pointing deeper — the lesson embeds the missed rule INSIDE
      deeper context: the rule plus its neighboring rules from the same story, depth 1-3.
      Depth 1 hits hard (the rule nearly alone, a strike); depth 3 teaches a lot (the rule
      wrapped in its neighbors, a long ring). That is the BELL, and it sounds like one:
      music._bell renders the lesson with inharmonic bell partials — depth sets strike
      hardness and ring length.
  THE AXIS — the void point already has lines connecting it: its story, its world's core, the
      atoms leading back into novice territory. The WORLD is the line that leads home, so the
      world is the axis, and the flower is built around it.
  THE FLOWER — flower of life geometry taken literally: six circles around one. Each lesson
      attempt lays ONE PETAL on that void point's flower at k x 60 degrees; six petals close a
      ring and the next ring begins. A petal records whether the re-teach RECOVERED the rule
      (closed=True) — the flower around a void point is the visible record of the void being
      filled by teaching, petal by petal.
  THE BAND — more instruments attach along the same axis: the world's forge bouts already play
      drum/chord/flute there, duets play violin, lessons play bell. flower --status lists each
      axis's band: which instruments have actually played on that line.

Usage:  python lesson.py            (one bell: pick the freshest void point, teach, re-ask, petal)
        python lesson.py --status  (the flowers and each axis's band)
        python lesson.py --demo    (whole loop against a stub novice; no bridge needed)
"""
from __future__ import annotations
import argparse, glob, json, math, os, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
FLOWER = os.path.join(HERE, "forge", "flower.json") if os.name == "nt" else "/tmp/flower.json"
BRIDGE = "http://localhost:41737"


def _load(p, default):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default


def _invs(story: Dict) -> List[Dict]:
    return [{"key": i.get("key", i["text"][:30]), "kind": i.get("kind", "concept"),
             "atoms": i.get("key", "").split("+") if i.get("kind") == "concept" else [],
             "text": i["text"]} for i in story.get("invariants", [])]


def void_points() -> List[Dict]:
    """Rules the novice measurably missed: re-score every stored teach-back per invariant."""
    from storyteller import score_extraction
    out = []
    for p in sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")),
                    key=os.path.getmtime)[::-1][:20]:
        s = _load(p, None)
        if not s: continue
        for side in ("mika_teach_back", "duet"):
            blk = s.get(side) or {}
            ans = blk.get("answer") or (blk.get("answers", {}) or {}).get("mika")
            if not ans: continue
            per = score_extraction(ans, _invs(s))["per_invariant"]
            for pi in per:
                if not pi["recovered"]:
                    out.append({"world": s.get("world"), "story": s.get("n"), "path": p,
                                "key": pi["key"], "via": side})
            break                                     # one recorded answer per story is enough
    return out


def compose(story: Dict, key: str, depth: int) -> Optional[str]:
    """The expert tunnel: the missed rule fixed at the END, wrapped in depth-1 neighbors."""
    invs = story.get("invariants", [])
    idx = next((i for i, v in enumerate(invs) if v.get("key", v["text"][:30]) == key), None)
    if idx is None: return None
    lo = max(0, idx - (depth - 1))
    context = invs[lo:idx + 1]                        # neighbors lead IN; the void point is the end
    lines = "\n".join(f"- {v['text']}" for v in context)
    return (f"A short lesson about the world '{story.get('world')}'. Read these true rules; the "
            f"LAST one is the one to hold onto:\n{lines}\n\n"
            f"Now, in your own words, state that last rule back — one line, keeping every "
            f"number and direction exactly.")


def petal(world: str, key: str, depth: int, closed: bool, instrument: str = "bell") -> Dict:
    fl = _load(FLOWER, {})
    ax = fl.setdefault(world, {"axis": world, "voids": {}})
    v = ax["voids"].setdefault(key, {"petals": []})
    k = len(v["petals"])
    v["petals"].append({"t": time.time(), "angle": (k * 60) % 360, "ring": k // 6 + 1,
                        "depth": depth, "closed": bool(closed), "instrument": instrument})
    os.makedirs(os.path.dirname(FLOWER), exist_ok=True)
    json.dump(fl, open(FLOWER, "w", encoding="utf-8"), indent=1)
    return v["petals"][-1]


def ring_bell(depth: int, closed: bool) -> str:
    import numpy as np, wave, music as M
    x = M._mix([(0.0, M._bell(depth=depth))]
               + ([(0.35, M._bell(freq=277.18, depth=depth) * 0.6)] if closed else []))
    p = os.path.join(HERE, "forge", "bell.wav") if os.name == "nt" else "/tmp/bell.wav"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with wave.open(p, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(M.SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return p


def teach(ask=None) -> None:
    """One bell: freshest void point, lesson at depth from history (miss again -> deeper), petal."""
    from storyteller import score_extraction
    vps = void_points()
    fl0 = _load(FLOWER, {})
    vps = [v for v in vps                                  # a pinched-off void's attachment is broken:
           if not fl0.get(v["world"], {}).get("voids", {}).get(v["key"], {}).get("ejected")]
    if not vps:
        print("no void points — every recorded teach-back recovered every rule"); return
    vp = vps[0]
    story = _load(vp["path"], {})
    fl = _load(FLOWER, {})
    prior = len(fl.get(vp["world"], {}).get("voids", {}).get(vp["key"], {}).get("petals", []))
    depth = min(3, 1 + prior)                          # missed before -> ring deeper this time
    try:                                               # the ZOOM (chord.py): a shallow chord cannot push deep —
        import math                                    # the bell is the chord bent, so its depth is capped by the shave
        fz = _load(r"D:\planet\focus.json" if os.name == "nt" else "/tmp/focus.json", {})
        if fz.get("depth") is not None:
            cap = max(1, min(3, int(math.ceil(3 * float(fz["depth"])))))
            if depth > cap: print(f"  (zoom caps the bell at depth {cap}; the chord is shallow)"); depth = cap
    except Exception: pass
    text = compose(story, vp["key"], depth)
    if not text: print("void point's story lost its rule"); return
    if ask is None:
        def ask(t):
            import requests
            r = requests.post(BRIDGE + "/chat", json={"text": t}, timeout=300).json()
            if isinstance(r, dict) and r.get("ok") is False: return None
            return r.get("reply") or r.get("response") or r.get("text")
    try:
        answer = ask(text)
    except Exception as e:
        print(f"the novice tunnel is closed ({str(e)[:80]}) — the bell waits"); return
    if not answer:
        print("no answer came back — the bell waits"); return
    inv = [v for v in _invs(story) if v["key"] == vp["key"]]
    closed = score_extraction(answer, inv)["per_invariant"][0]["recovered"]
    pt = petal(vp["world"], vp["key"], depth, closed)
    wav = ring_bell(depth, closed)
    print(f"bell: {vp['world']} / '{vp['key']}' at depth {depth} -> "
          f"{'CLOSED — the petal opens' if closed else 'still open — next lesson rings deeper'} "
          f"(petal {prior + 1}, ring {pt['ring']}, {pt['angle']} deg) -> {wav}")


def status() -> None:
    fl = _load(FLOWER, {})
    if not fl: print("no flowers yet — no lessons rung"); return
    # the band: every instrument that has actually played on each axis
    bands: Dict[str, set] = {}
    for row in _load_ledger():
        w = row.get("world")
        if w and row.get("sound"): bands.setdefault(w, set()).add(row["sound"]["instrument"])
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        s = _load(p, {})
        if s.get("duet"): bands.setdefault(s.get("world"), set()).add("violin")
    for w, ax in fl.items():
        for key, v in ax["voids"].items():
            n = len(v["petals"]); c = sum(1 for q in v["petals"] if q["closed"])
            bands.setdefault(w, set()).add("bell")
            print(f"{w} / '{key}': {n} petals ({c} closed), ring {(n - 1) // 6 + 1}")
        print(f"  the band on the {w} axis: {', '.join(sorted(bands.get(w, {'bell'})))}")


def _load_ledger():
    try:
        return [json.loads(l) for l in open(os.path.join(HERE, "forge", "ledger.jsonl"),
                                            encoding="utf-8").read().splitlines() if l.strip()]
    except Exception: return []


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    elif a.demo:
        # stub novice: misses until the lesson carries the rule text at depth >= 2
        state = {"n": 0}
        def stub(t):
            state["n"] += 1
            rules = [l[2:] for l in t.splitlines() if l.startswith("- ")]
            return rules[-1] if state["n"] >= 2 else "the boy walks left"
        teach(ask=stub); teach(ask=stub)
    else:
        teach()
