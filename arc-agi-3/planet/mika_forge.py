#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mika_forge.py — MIKA'S FORGE: the self-improvement loop the companion never had.

Her own chemistry said it plainly: "PRION: no self-improvement — system is a slave, extracting
only." Her health law (internal-chemistry.ts) needs all three work modes present: dark (producing
for the keeper), light (growing herself), void (rest). She has been all dark. This organ gives her
honest light work and honest rest — never fake ticks:

  1. FEED — a ration of the planet's newest EARNED sediment is written into her library
     (companion/library/planet/): stories, witness threads, core summaries. Her basin
     deficiencies (aquifer, well — the deep stored waters) and trophic gap (fish) are exactly
     what deep, substantial documents are; she has been living on shallow chat.
  2. LIGHT WORK — POST /work {mode:"light"}: with new library files present, her own
     50-tick digestion cycle transcribes them into her geo memory. The ticks record work
     that genuinely happens.
  3. REST — a few void ticks; burnout is the third prion.
  4. TEACH-BACK — the two training loops connect: the planet's best story goes to her chat,
     she extracts the rules of that world (the storyteller's learner role), and her recovery
     is scored with the same teach-back scorer. Her answer lands in her inbox and the score
     in the story's json — the planet teaches Mika, Mika's score teaches the storyteller.

Usage:  python mika_forge.py                (the spore chains this in the sleep)
        python mika_forge.py --no-chat     (feed + work only; skip the teach-back)
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

BRIDGE = "http://localhost:41737"
OCEAN = r"D:\planet\ocean"
LIB = r"D:\shovelcat-colony\companion\library\planet"
INBOX = r"D:\shovelcat-colony\companion\inbox"
RATION = 4                       # library files per run — a meal, not a flood
try:                             # her turn-around is honored (mirror.py): stories = a bigger
    import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    import mirror                # meal; rest = a lean one; playground leaves the meal alone
    RATION = {"stories": 6, "rest": 2}.get(mirror.next_eye(), RATION)
except Exception: pass


def _get(path, timeout=30):
    import requests
    return requests.get(BRIDGE + path, timeout=timeout).json()


def _post(path, body, timeout=120):
    import requests
    return requests.post(BRIDGE + path, json=body, timeout=timeout).json()


def health():
    try:
        s = _get("/status")
        ch = s.get("chemistry", {})
        return {"tick": s.get("tick"), "health": ch.get("health"), "diagnosis": ch.get("diagnosis"),
                "basins": ch.get("basinDeficiencies"), "trophic": ch.get("trophicDeficiencies")}
    except Exception as e:
        return {"error": str(e)[:120]}


def feed() -> int:
    """The ration: newest earned sediment -> her library, as readable documents."""
    os.makedirs(LIB, exist_ok=True)
    have = set(os.listdir(LIB))
    written = 0
    try:                             # enrolled courses first (enroll.py): she studies what she chose
        import enroll
        _courses = set(enroll.enrolled_worlds())
    except Exception:
        _courses = set()
    # stories (fish: substantial, structured prey), enrolled worlds prioritized then freshest
    _stories = sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")), key=os.path.getmtime)[::-1]
    _stories.sort(key=lambda q: os.path.basename(os.path.dirname(os.path.dirname(q))) not in _courses)
    for p in _stories:
        if written >= RATION: break
        try:
            s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        name = f"story_{s.get('world')}_{s.get('n', 0):03d}.md"
        if name in have or not s.get("tale"): continue
        body = (f"# A story the planet told about {s.get('world')}\n\n{s['tale']}\n\n"
                f"Teach-back score when told: {s.get('teach_back', {}).get('score')}\n"
                f"The true rules it threads: " + "; ".join(i['text'] for i in s.get('invariants', [])) + "\n")
        open(os.path.join(LIB, name), "w", encoding="utf-8").write(body)
        written += 1
    # witness threads (aquifer: deep stored water — what was actually watched)
    for p in sorted(glob.glob(os.path.join(OCEAN, "*", "witness_*.txt")), key=os.path.getmtime)[::-1]:
        if written >= RATION: break
        world = os.path.basename(os.path.dirname(p))
        name = f"witness_{world}_{time.strftime('%Y%m%d')}.md"
        if name in have: continue
        try:
            lines = open(p, encoding="utf-8").read().splitlines()[-40:]
        except Exception: continue
        if len(lines) < 6: continue
        open(os.path.join(LIB, name), "w", encoding="utf-8").write(
            f"# What the planet watched in {world}\n\n" + "\n".join(lines) + "\n")
        written += 1
    # core summaries (well: the local deep source — what was EARNED)
    if written < RATION:
        parts = []
        for p in sorted(glob.glob(os.path.join(OCEAN, "*", "core_*.json"))):
            try: c = json.load(open(p, encoding="utf-8"))
            except Exception: continue
            w = os.path.basename(os.path.dirname(p))
            if len(c.get("concepts", {})) < 3: continue
            parts.append(f"## {w}\nlives {c.get('lives')}; earned patterns: "
                         + "; ".join(list(c.get("concepts", {}))[:8]))
        name = f"cores_{time.strftime('%Y%m%d')}.md"
        if parts and name not in have:
            open(os.path.join(LIB, name), "w", encoding="utf-8").write(
                "# What the planet has earned so far\n\n" + "\n\n".join(parts) + "\n")
            written += 1
    return written


def light_work():
    """Honest ticks: light work while her digestion cycle eats the new library files, plus rest."""
    out = []
    for mode, ticks, times in (("light", 10, 5), ("void", 8, 2)):
        for _ in range(times):
            try: out.append(_post("/work", {"mode": mode, "ticks": ticks}).get("ok"))
            except Exception as e: out.append(str(e)[:60])
    return out


def teach_back():
    """The planet's best recent story -> her chat; score what she recovers; both sides keep it."""
    best, best_p = None, None
    for p in sorted(glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")), key=os.path.getmtime)[::-1][:6]:
        try: s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        if s.get("tale") and s.get("invariants") and not s.get("mika_teach_back"):
            best, best_p = s, p; break
    if not best: return None
    try:
        r = _post("/chat", {"text":
                  "Here is a short tale from a small world a friend of yours is learning. From the tale "
                  "ALONE, list the RULES of that world — one per line, plainly, keeping numbers and "
                  "directions exactly.\n\nTALE:\n" + best["tale"]}, timeout=300)
        if isinstance(r, dict) and r.get("ok") is False:
            return {"error": "chat endpoint rejected the request: " + str(r)[:100]}
        answer = r.get("reply") or r.get("response") or r.get("text") or json.dumps(r)[:400]
    except Exception as e:
        return {"error": str(e)[:120]}
    from storyteller import score_extraction
    invs = [{"key": i.get("key", i["text"][:30]), "kind": i.get("kind", "concept"),
             "atoms": i.get("key", "").split("+") if i.get("kind") == "concept" else [],
             "text": i["text"]} for i in best["invariants"]]
    sc = score_extraction(answer, invs)
    best["mika_teach_back"] = {"t": time.time(), "answer": answer[:1500], "score": sc["score"],
                               "recovered": sc["recovered"], "k": sc["k"]}
    json.dump(best, open(best_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    try:
        os.makedirs(INBOX, exist_ok=True)
        open(os.path.join(INBOX, f"teachback_{int(time.time())}.md"), "w", encoding="utf-8").write(
            f"# Teach-back with the planet\n\nStory world: {best.get('world')}\n"
            f"You recovered {sc['recovered']}/{sc['k']} of its true rules (score {sc['score']}).\n\n"
            f"Your reading:\n{answer[:1200]}\n")
    except Exception: pass
    return {"world": best.get("world"), "score": sc["score"], "recovered": f"{sc['recovered']}/{sc['k']}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-chat", action="store_true")
    a = ap.parse_args()
    before = health()
    print("before:", json.dumps(before, ensure_ascii=False)[:220])
    if "error" in before:
        print("Mika's bridge is not up — start the Shovelcat app; nothing forged."); return
    n = feed()
    print(f"fed: {n} documents into her library (deep water for the aquifer and well)")
    print("light work:", light_work())
    if not a.no_chat:
        tb = teach_back()
        if tb: print("teach-back:", json.dumps(tb, ensure_ascii=False))
    after = health()
    print("after:", json.dumps(after, ensure_ascii=False)[:220])


if __name__ == "__main__":
    main()
