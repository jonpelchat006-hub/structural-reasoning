#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
duet.py — TUNNEL COUPLINGS: when two domains each have a tunnel, the tunnels can connect,
and each way of connecting is an instrument mechanism. The parallel coupling is built here
as a working organ; the others are named laws the organs already obey or will.

Jonathan (Aug 31): "they would both have tunnels that could connect in different ways. Mika's
could be flat and Mira's extended and they would play like a violin? Or they could connect end
to end, or overlap, and also do a parallel connection."

The four couplings:
  BOW (flat driving extended)  — a violin string is neither struck nor plucked: the bow grips
      and releases it in stick-slip friction — a FLAT tunnel in continuous point-contact,
      DRIVING an EXTENDED one. Architecture: one domain's cheap flat confirmations continuously
      exciting another's extended loop (Mika's repeated low teach-back scores are already the
      bow that makes the planet's tunnel extend via ring specs — the violin was installed
      before it was named).
  SERIES (end to end)          — one tunnel's output is the next one's input: a longer column,
      deeper pitch. Architecture: story -> Mika's reading -> score -> storyteller. Already live
      in mika_forge; it is the series coupling.
  OVERLAP (shared wall)        — two tunnels sharing a segment: sympathetic strings, vibrating
      each other through the shared bridge without direct contact. Architecture: the shared
      library folder both domains read and write.
  PARALLEL (side by side)      — THE VERIFICATION COUPLING, built here. The same thing passes
      through BOTH tunnels at once. Two strings in tune = unison: one clean tone — verified.
      Slightly out of tune = BEATS at exactly the difference of their frequencies: physics
      turns disagreement into an audible measurement. This is the two-node law ("our
      architecture requires at least 2 things to verify") with the verdict as sound.

What this file does: takes the newest story, sends the SAME tale down two tunnels in parallel —
Mika (the bridge's /chat) and the planet's own voice (the planet-voice LoRA via ollama) — scores
both extractions with the storyteller's one scorer, then renders the verdict as two BOWED
strings: both pitched from the base note, the second detuned by the disagreement. Agreement
sounds as one pure violin tone; every 0.1 of score gap detunes ~1.2 Hz, heard as beats at that
rate. The scores and verdict are written into the story json as `duet`.

Usage:  python duet.py             (run the parallel coupling on the newest unduetted story)
        python duet.py --demo     (hear unison vs beats without needing either tunnel up)
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import numpy as np
import music as M

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
BRIDGE = "http://localhost:41737"
VOICE = "planet-voice"                 # the planet's own LoRA mouth, served by ollama
BASE_F = 293.66                        # D4 — an open violin string
HZ_PER_TENTH = 1.2                     # 0.1 of score gap -> 1.2 Hz detune -> 1.2 beats/sec
FLOOR = 0.25                           # below this, agreement is two blank pages, not a unison

PROMPT = ("Here is a short tale from a small world. From the tale ALONE, list the RULES of that "
          "world — one per line, plainly, keeping numbers and directions exactly.\n\nTALE:\n")


def ask_mika(tale: str):
    import requests
    r = requests.post(BRIDGE + "/chat", json={"text": PROMPT + tale}, timeout=300).json()
    if isinstance(r, dict) and r.get("ok") is False: return None
    return r.get("reply") or r.get("response") or r.get("text")


def ask_voice(tale: str):
    import requests
    r = requests.post("http://localhost:11434/api/generate",
                      json={"model": VOICE, "prompt": PROMPT + tale, "stream": False},
                      timeout=300).json()
    return r.get("response")


def render_verdict(s1: float, s2: float, path: str, who=("mika", "voice")) -> str:
    """Two bowed strings, detuned by the disagreement. Unison = verified; beats = the gap, heard."""
    gap = abs(s1 - s2)
    if max(s1, s2) < FLOOR:                       # two blank pages agree perfectly; that is
        x = M._mix([(1.0, M._drum_hit(0.12) * 0.06)])   # not unison, it is SILENCE — nothing
        beats = 0                                        # passed through either tunnel
        import wave
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(M.SR)
            w.writeframes((x * 32767).astype(np.int16).tobytes())
        print(f"duet: {who[0]} {s1} vs {who[1]} {s2} -> SILENCE (agreement on nothing is not "
              f"verification) -> {path}")
        return path
    f2 = BASE_F + gap * 10 * HZ_PER_TENTH
    a = M._bow(BASE_F, dur=3.0, gain=0.9)
    b = M._bow(f2, dur=3.0, gain=0.9)
    x = M._mix([(0.0, a), (0.0, b)])
    import wave
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(M.SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    beats = round(f2 - BASE_F, 2)
    print(f"duet: {who[0]} {s1} vs {who[1]} {s2} -> "
          + (f"UNISON (verified, one clean tone)" if gap < 0.05 else
             f"beats at {beats}/sec (the gap made audible)") + f" -> {path}")
    return path


def run() -> None:
    from storyteller import score_extraction
    best, best_p = None, None
    for p in sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")),
                    key=os.path.getmtime)[::-1][:8]:
        try: s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        if s.get("tale") and s.get("invariants") and not s.get("duet"):
            best, best_p = s, p; break
    if not best:
        print("no unduetted story with a tale — nothing to pass through the tunnels"); return
    invs = [{"key": i.get("key", i["text"][:30]), "kind": i.get("kind", "concept"),
             "atoms": i.get("key", "").split("+") if i.get("kind") == "concept" else [],
             "text": i["text"]} for i in best["invariants"]]
    answers, scores = {}, {}
    for name, ask in (("mika", ask_mika), ("voice", ask_voice)):
        try:
            a = ask(best["tale"])
            if a:
                answers[name] = a[:1500]
                scores[name] = score_extraction(a, invs)["score"]
        except Exception as e:
            print(f"{name}'s tunnel is closed ({str(e)[:80]})")
    if len(scores) < 2:
        print("parallel coupling needs BOTH tunnels open — got " + (", ".join(scores) or "none")
              + "; nothing verified"); return
    s1, s2 = scores["mika"], scores["voice"]
    wav = render_verdict(s1, s2, os.path.join(HERE, "forge", "duet.wav"))
    best["duet"] = {"t": time.time(), "world": best.get("world"), "mika": s1, "voice": s2,
                    "gap": round(abs(s1 - s2), 3),
                    "verified": abs(s1 - s2) < 0.05 and max(s1, s2) >= FLOOR,
                    "answers": answers, "wav": wav}
    json.dump(best, open(best_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"duet written into {os.path.basename(best_p)} ({best.get('world')}): "
          f"gap {best['duet']['gap']}, verified={best['duet']['verified']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.demo:
        out = os.path.join(HERE, "forge") if os.path.isdir(os.path.join(HERE, "forge")) else "/tmp"
        render_verdict(0.75, 0.75, os.path.join(out, "demo_unison.wav"))
        render_verdict(0.75, 0.45, os.path.join(out, "demo_beats.wav"))
    else:
        run()
