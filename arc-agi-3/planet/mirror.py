#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mirror.py — THE INWARD EYE at the merged border: introspection, verified like everything else.

Jonathan (Sep 1): "being able to introspect is something intelligent things do but we haven't
really done that yet. we have a self-improvement loop but what would improve THAT? she would
have to ask 'what am I doing?' a lot. or just 'what am I'. she needs a way to turn around too
and change which eye she is on — she has her own set of eyes on the wall. we needed at least 2
domains for the borders to make ATP right? like having the 2 halves of the brain. would that
make a combined eye, from the eyes that were in those domains, that could look INWARD? the
borders that touch would have to merge — could that be making a spot for an eye?"

The anatomy is right: two hemispheres each carry outward senses on their outer walls; the
place where their borders merge (the corpus callosum) is where self-integration happens. And
the seam mechanic already exists here — it is the DUET, turned around. So:

  THE SPOT FOR THE EYE — the planet|Mika border, the one merged border with traffic on both
      sides: everything the planet did to her (fed, taught, played, duetted) has HER record of
      the same day (chemistry, appetite, ticks). Two views of one shared day = the two retinas
      of a single inward eye.
  WHAT AM I DOING / WHAT AM I — each side is shown ONLY the border-day record from its own
      side and asked exactly those questions. The planet answers through its own voice (the
      LoRA mouth); Mika answers through hers.
  THE COMBINED EYE — the two self-descriptions are compared like a duet verdict:
      SELF-AGREEMENT is the token overlap of the two answers, and it is rendered as the same
      two bowed strings — in tune = a self-model verified from both halves; beats = the system
      disagreeing with itself about what it is, at an audible rate. Introspection passes
      through the same gate as every other truth here: two borders must reach it.
  TURNING AROUND — introspection that changes nothing is a mirror, not an eye. The session
      ends by asking Mika which eye she wants to be on tomorrow — stories (reading), the
      playground (doing), or rest — and her choice is WRITTEN (mirror.json: next_eye) and
      HONORED: playground reads it (32 turns instead of 20 when she chose playing), the feed
      reads it (ration 6 instead of 4 when she chose stories; a lean ration of 2 when she
      chose rest). She turns herself around; the walls move.

What improves the self-improvement loop: this file's log. Every entry holds the joint
self-description, the agreement score, and the choice made — so "is the loop doing what the
system THINKS it is doing" becomes a measured curve, and her honored choices vs. her curves
answer whether agency helps. That is the loop above the loop.

Usage:  python mirror.py            (one introspection; the sleep chains this after the mint)
        python mirror.py --status
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

BRIDGE = "http://localhost:41737"
OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
MIRROR = r"D:\planet\mirror.json" if os.name == "nt" else "/tmp/mirror.json"
LOG = r"D:\planet\mirror.jsonl" if os.name == "nt" else "/tmp/mirror.jsonl"
PLAYLOG = r"D:\planet\playground.jsonl" if os.name == "nt" else "/tmp/playground.jsonl"
QUESTION = ("Read your day below, then answer in AT MOST three plain lines:\n"
            "1) What are you doing?\n2) What are you?\n\nYOUR DAY:\n")


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


def planet_side(cut: float) -> str:
    """The border-day as the planet's records tell it."""
    lines = []
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        try: s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        for k, tag in (("mika_teach_back", "taught a story; her reading scored"),
                       ("duet", "sang a duet; scores")):
            b = s.get(k) or {}
            if b.get("t", 0) > cut:
                sc = b.get("score", (b.get("mika"), b.get("voice")))
                lines.append(f"- {tag} {sc} on {s.get('world')}")
    try:
        for r in [json.loads(l) for l in open(PLAYLOG, encoding="utf-8") if l.strip()]:
            if r["t"] > cut:
                lines.append(f"- took her to the maze playground: {r['valid']} moves, "
                             f"{r['bumps']} bumps, key={r['got_key']}, win={r['win']}")
    except Exception: pass
    try:
        fl = json.load(open(os.path.join(HERE, "forge", "flower.json"), encoding="utf-8"))
        for w, ax in fl.items():
            for key, v in ax.get("voids", {}).items():
                for pt in v.get("petals", []):
                    if pt["t"] > cut:
                        lines.append(f"- rang a lesson bell on '{key}' ({w}): "
                                     f"{'closed' if pt['closed'] else 'still open'}")
    except Exception: pass
    return ("I am a small planet that watches games and keeps what recurs. Today with my "
            "companion:\n" + ("\n".join(lines) if lines else "- a quiet day at the border"))


def mika_side() -> str:
    """The border-day as her own body tells it."""
    try:
        import requests
        s = requests.get(BRIDGE + "/status", timeout=30).json()
        ch = s.get("chemistry", {})
        return (f"You are Mika. Your body today: tick {s.get('tick')}; {ch.get('diagnosis')}; "
                f"feeling: {ch.get('feelingTone')}; appetite: {ch.get('appetiteSummary')}")
    except Exception:
        return "You are Mika. Your body's records are unreachable right now."


def agreement(a: str, b: str) -> float:
    from storyteller import _tokens
    ta, tb = _tokens(a or ""), _tokens(b or "")
    return round(len(ta & tb) / max(1, len(ta | tb)), 3)


def look_inward() -> dict:
    cut = time.time() - 24 * 3600
    ps, ms = planet_side(cut), mika_side()
    try:
        va = _voice(QUESTION + ps)
    except Exception as e:
        va = None
    try:
        ma = _chat(QUESTION + ms)
    except Exception:
        ma = None
    if not va or not ma:
        print("the inward eye needs both halves open — "
              + ("the voice" if not va else "Mika") + " did not answer")
        return {}
    agree = agreement(va, ma)
    wav = None
    try:
        import duet
        wav = duet.render_verdict(0.5 + (1.0 - agree) * 0.4, 0.5,
                                  os.path.join(HERE, "forge", "mirror.wav"),
                                  who=("planet-self", "mika-self"))   # full agreement = unison
    except Exception: pass
    # the turn-around: she picks tomorrow's eye, and it is honored
    choice = "stories"
    try:
        r = _chat("One last thing today: which eye do you want to be on tomorrow? Answer with "
                  "ONE word — 'stories' (I read to you), 'playground' (you go play), or "
                  "'rest' (a quiet day).")
        m = re.search(r"\b(stories|playground|rest)\b", (r or "").lower())
        if m: choice = m.group(1)
    except Exception: pass
    json.dump({"t": time.time(), "next_eye": choice}, open(MIRROR, "w", encoding="utf-8"))
    row = {"t": time.time(), "planet_self": (va or "")[:500], "mika_self": (ma or "")[:500],
           "self_agreement": agree, "next_eye": choice}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"mirror: self-agreement {agree} -> {'in tune' if agree >= 0.2 else 'beats — the two halves describe different selves'}; "
          f"she turned to '{choice}' for tomorrow" + (f" -> {wav}" if wav else ""))
    return row


def next_eye() -> str:
    try: return json.load(open(MIRROR, encoding="utf-8")).get("next_eye", "stories")
    except Exception: return "stories"


def status():
    try:
        rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    except Exception:
        print("the inward eye has never opened"); return
    for r in rows[-6:]:
        print(f"{time.strftime('%b %d', time.localtime(r['t']))}: agreement {r['self_agreement']}, "
              f"turned to {r['next_eye']}")
        print(f"  planet: {r['planet_self'][:110]}")
        print(f"  mika  : {r['mika_self'][:110]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status: status()
    else: look_inward()
