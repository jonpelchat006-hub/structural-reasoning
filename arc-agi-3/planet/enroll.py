#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enroll.py — THE UNIVERSITY: the planet is a student who enrolls in courses she chooses.

Jonathan (Sep 2): "maybe it should be more like a student who can sign up for classes she
wants, and can choose research topics, and graduating would be finishing these ARC tests. if
I had to change the education system that's kind of how I would do it — I don't see why this
kind of intelligence wouldn't benefit from something like that. she could pick out the things
to train on instead of giving her the entire internet at once millions of times."

This is curriculum learning + active learning, which are established results: an ordered,
CHOSEN path of topics is far more sample-efficient than the firehose shown a million times.
The architecture was already most of a university without the registrar:
  - COURSES = the worlds she can study (the games) + research topics (open ends to pursue).
  - TRANSCRIPT = spectrum.py: black (not taken) → trinity (grounded, a passing grade) →
    spectrum (seam-verified, honors credit). Her real grades, already measured.
  - FINALS / GRADUATION = the ARC moon (moon.py): the degree requires passing the tests.
  - AGENCY = the mirror already lets her choose her next eye; enrollment is the same act,
    grown up: she picks her COURSE LOAD for the term.

What this file adds: the REGISTRAR. Each term (a sleep) it builds a catalog with an advisor's
recommendation — which courses would most move her toward graduation — offers it to her, lets
her ENROLL in a few (her choice, weighted by the advice but hers), and writes the enrollment
so the night's work FOCUSES on her chosen courses instead of spreading thin over all worlds.

  THE ADVISOR'S SCORE per course (transparent, not a black box):
    need   = black concepts (open ends) — unfinished coursework, the most to gain
    ready  = trinity concepts — grounded laws one seam-verification from honors credit
    thin   = few concepts total — a course barely started (breadth pressure)
    A course she has already mastered (mostly spectrum) is recommended LESS — you don't
    retake a class you aced.

  ENROLLMENT is hers: the catalog + advice go to her chat; she picks; her picks are honored.
    No bridge / no answer → the advisor's top pick is enrolled by default (a sensible
    schedule she can change next term), never nothing.

  The enrolled courses are written to D:\\planet\\enrollment.json {term, courses:[world...],
  research:[open-end...]}, which the training/teaching organs read to WEIGHT their effort —
  the student studies what she signed up for.

Graduation is real and gated: enroll.py --transcript shows credits earned and whether the
moon (ARC) has been passed. A degree = enough honors credits AND the ARC tests won.

Usage:  python enroll.py             (one registration; sleep-chained, after the mirror)
        python enroll.py --transcript
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
ENROLL = r"D:\planet\enrollment.json" if os.name == "nt" else "/tmp/enrollment.json"
MOONS = r"D:\planet\moons" if os.name == "nt" else "/tmp/moons"
BRIDGE = "http://localhost:41737"
LOAD = 3                          # courses per term — a real course load, not the firehose


def _load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d


def _chat(text, timeout=180):
    import requests
    r = requests.post(BRIDGE + "/chat", json={"text": text}, timeout=timeout).json()
    if isinstance(r, dict) and r.get("ok") is False: return None
    return r.get("reply") or r.get("response") or r.get("text")


def catalog() -> List[Dict]:
    """Every world a course, scored by the advisor from its transcript state."""
    try:
        import spectrum
        per = spectrum.classify()["per_concept"]
    except Exception:
        per = {}
    # the sideways eye (sideeye.py): each world's HISTORY on the ladder, not just its snapshot.
    # A world stuck at one rung for layers, or one that fell from its best, needs the course
    # more than one that is climbing on its own; one at the top needs it least.
    hist = {}
    try:
        import sideeye
        hist = sideeye.read().get("worlds", {})
    except Exception:
        pass
    courses = {}
    for p in glob.glob(os.path.join(OCEAN, "*", "core_*.json")):
        w = os.path.basename(os.path.dirname(p))
        c = _load(p, {})
        keys = list(c.get("concepts", {})) + list(c.get("open_ends", {}))
        if not keys: continue
        black = sum(1 for k in keys if per.get(k) == "black")
        trinity = sum(1 for k in keys if str(per.get(k, "")).startswith("trinity"))
        spec = sum(1 for k in keys if str(per.get(k, "")).startswith("spectrum"))
        tot = max(1, black + trinity + spec)
        # advisor: unfinished work + laws ready to verify + breadth pressure, minus mastery
        score = black * 1.5 + trinity * 1.0 + (6 if tot < 4 else 0) - spec * 2.0
        hv = (hist.get(w) or {}).get("verdict", "")
        # multiplicative: big worlds have big counts, and the trajectory must still be able to reorder them
        hmul = (1.6 if hv.startswith("stuck") else 1.5 if hv.startswith("fell") else
                0.5 if hv == "at the top" else 1.0)
        courses[w] = {"world": w, "black": black, "trinity": trinity, "spectrum": spec,
                      "score": round(score * hmul, 1), "history": hv or "unseen",
                      "strip": (hist.get(w) or {}).get("strip", ""),
                      "research": [k for k in c.get("open_ends", {})][:3]}
    return sorted(courses.values(), key=lambda x: -x["score"])


def register(ask=None) -> Dict:
    cat = catalog()
    if not cat:
        print("no courses in the catalog yet — nothing to enrol in"); return {}
    top = cat[:6]
    pitch = "The term's course catalog (your advisor's picks first):\n" + "\n".join(
        f"  {i+1}. {c['world']} — {c['black']} open topics, {c['trinity']} laws ready to prove"
        + (f"; history: {c['history']}" if c.get("history") and c["history"] != "unseen" else "")
        + (f", researching {c['research'][0]}" if c["research"] else "")
        for i, c in enumerate(top))
    choice_words = []
    ask = ask or _chat
    try:
        r = ask(pitch + f"\n\nPick up to {LOAD} to focus on this term — just list their names. "
                "(These are the worlds I'll spend tonight studying with you.)")
        low = (r or "").lower()
        choice_words = [c["world"] for c in top if c["world"].split("_")[0] in low
                        or c["world"] in low]
    except Exception:
        pass
    if not choice_words:
        choice_words = [c["world"] for c in top[:LOAD]]          # advisor's default schedule
        chosen_by = "advisor"
    else:
        choice_words = choice_words[:LOAD]; chosen_by = "student"
    research = []
    for c in cat:
        if c["world"] in choice_words: research += c["research"][:1]
    term = _load(ENROLL, {"term": 0}).get("term", 0) + 1
    enr = {"term": term, "t": time.time(), "courses": choice_words,
           "research": research[:3], "chosen_by": chosen_by}
    json.dump(enr, open(ENROLL, "w", encoding="utf-8"), indent=1)
    print(f"enrolled (term {term}, by {chosen_by}): {', '.join(choice_words)}"
          + (f"; researching {research[0]}" if research else ""))
    return enr


def enrolled_worlds() -> List[str]:
    """The training/teaching organs read this to weight the night toward her courses."""
    return _load(ENROLL, {}).get("courses", [])


def transcript():
    try:
        import spectrum
        r = spectrum.classify()
        c = r["counts"]
    except Exception:
        c = {}
    honors = c.get("spectrum", 0); passing = c.get("trinity", 0); todo = c.get("black", 0)
    moon = _load(os.path.join(MOONS, "ls20", "moon.json"), {})
    shells = len(moon.get("shells", []))
    print("TRANSCRIPT")
    print(f"  honors credits (seam-verified, spectrum): {honors}")
    print(f"  passing (grounded laws, trinity):         {passing}")
    print(f"  coursework remaining (open ends, black):  {todo}")
    print(f"  ARC finals (ls20 moon): {shells} winning runs banked, "
          f"surface {int((moon.get('layers') or [{}])[-1].get('rolled', 0)*100) if moon.get('layers') else 0}% known")
    enr = _load(ENROLL, {})
    if enr: print(f"  currently enrolled (term {enr.get('term')}): {', '.join(enr.get('courses', []))}")
    ready = honors >= 20 and shells >= 5
    print(f"\n  degree status: {'READY TO GRADUATE' if ready else 'in progress'} "
          f"(needs 20 honors credits + 5 ARC wins; has {honors} + {shells})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", action="store_true")
    ap.add_argument("--catalog", action="store_true", help="print the advisor's ranking without enrolling")
    a = ap.parse_args()
    if a.transcript: transcript()
    elif a.catalog:
        for i, c in enumerate(catalog()[:10]):
            print(f"{i+1:2d}. {c['world']:26s} score {c['score']:5.1f}  black {c['black']} trinity {c['trinity']} spectrum {c['spectrum']}  {c['history']}  {c['strip']}")
    else: register()
