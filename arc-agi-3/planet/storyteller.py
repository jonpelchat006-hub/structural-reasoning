#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
storyteller.py — STORIES: fictional paths that visit real truths (ARC_OPEN_ENDS §5).

Jonathan's construction: take the invariants a world has already EARNED, and draw a path that
visits them all while ignoring the interior — fiction is physically false everywhere except at
the truths it threads. Story quality = how close the path passes to the truths. The teaching
use: a story launched from the back face arcs OVER the built structure and comes down at old
truths a novice can reach.

The job, verbatim from the doc: take k invariants from a world's core → the mouth writes a
short tale whose events instantiate each invariant in order, claiming no physical truth → the
learner (a FRESH context — no shared memory with the mouth) extracts the invariants back — the
reproduction test run through fiction. Score = fraction of invariants recovered.

Honesty clause, doubled for stories: a story bypasses the operator-induction gate BY DESIGN
(narrative transportation relaxes counterarguing), so every story is labeled fiction, scored,
and kept as an OPEN back-face loop — imagination until its truths are re-verified by play.

Artifacts per story, in <world>/stories/:
  story_NNN.json   the tale, the invariants it threads, the learner's extraction, the score
  story_NNN.geo    an OPEN loop (orientation "back") — first-class imagination sediment

Usage:  python storyteller.py --root D:\\planet\\ocean\\<world>            (one story per run)
        python storyteller.py --root ... --dry                             (score mechanics only, no Ollama)
The spore chains this in the sleep after clips; the chatbot retrieves the tales.
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys, time
from typing import Dict, List, Optional, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

MODEL = "gemma3:4b"
K_DEFAULT = 4                  # invariants per tale — a parable, not a textbook
MIN_EVIDENCE = 2               # a law must have survived at least this many confirmations

# ---------------------------------------------------------------------------- invariants
DIRS = {"R": "right", "L": "left", "U": "up", "D": "down", "right": "right", "left": "left", "up": "up",
        "down": "down", "grabright": "grabbing to the right", "grableft": "grabbing to the left"}


def _phrase(atom: str) -> str:
    """One atom → one plain-language clause the mouth can weave (and the scorer can find)."""
    m = re.match(r"counter\.(up|down):?(\d*)", atom)
    if m:
        which = f"counter {m.group(2)}" if m.group(2) else "the counter"
        return f"{which} ticks {m.group(1)}"
    m = re.match(r"mover\.moved:?(\w+)", atom)
    if m:
        d = DIRS.get(m.group(1), m.group(1))
        return f"things move {d}"
    m = re.match(r"mouse\.moved:?(\w+)", atom)
    if m: return f"the gaze drifts {' '.join(DIRS.get(ch, ch) for ch in m.group(1))}"
    if atom == "camera.scrolled": return "the whole view slides"
    if atom == "window.new_ground": return "new ground appears"
    if atom == "body.impostor": return "a stranger wearing your shape appears"
    if atom == "object.vanished": return "an object vanishes"
    if atom == "object.appeared": return "an object appears"
    if atom.startswith("death"): return "the life ends"
    if atom.startswith("respawn"): return "life begins again"
    if atom.startswith("surprise"): return "something unexpected happens"
    if atom.startswith("hand."): return "a hand acts"
    return atom.replace(".", " ").replace(":", " ").replace("_", " ")


def invariants_of(core: Dict, k: int = K_DEFAULT) -> List[Dict]:
    """The earned truths, DIVERSE first: graduated concepts (the richest sediment — skip ones that
    mostly repeat an already-picked bundle), then laws deduped to one per register (the strongest
    reading of 'wait', not four)."""
    picked: List[Dict] = []
    concepts = sorted(core.get("concepts", {}).items(),
                      key=lambda kv: (-len(set(kv[0].split("+"))), kv[1].get("born", 0)))
    for key, c in concepts:
        atoms = sorted(set(key.split("+")))
        if any(len(set(p["atoms"]) & set(atoms)) >= 2 for p in picked): continue   # says the same thing
        picked.append({"key": key, "kind": "concept", "atoms": atoms,
                       "text": " and ".join(_phrase(a) for a in atoms) + ", together"})
        if len(picked) >= k: return picked
    best_law: Dict[str, Tuple[int, Dict]] = {}                # one per register, highest evidence
    for kind in ("mover", "counter"):
        for key, law in core.get("laws", {}).get(kind, {}).items():
            ev = law.get("evidence", 0)
            if ev < MIN_EVIDENCE: continue
            reg = f"{kind}:{key.split(':')[0]}"
            if reg not in best_law or ev > best_law[reg][0]:
                v = law.get("value")
                if kind == "mover" and isinstance(v, (list, tuple)) and len(v) == 2:
                    dy, dx = v
                    d = (("down" if dy > 0 else "up" if dy < 0 else "")
                         + ("right" if dx > 0 else "left" if dx < 0 else ""))
                    text = f"pressing {key} moves things {d or 'nowhere'}"
                    atoms = [f"mover.{key}", f"dir.{d or 'none'}"]
                else:
                    vs = v if isinstance(v, (int, float, str)) else (v[0] if isinstance(v, list) and v else v)
                    text = f"{key.split(':')[0]} changes by {vs}"
                    atoms = [f"{kind}.{key}", f"value.{vs}"]
                best_law[reg] = (ev, {"key": f"{kind}:{key}", "kind": kind, "atoms": atoms, "text": text})
    for ev, inv in sorted(best_law.values(), key=lambda t: -t[0]):
        if len(picked) >= k: break
        picked.append(inv)
    return picked[:k]


def truths_line(root: str, k: int = 5) -> str:
    """One line of a world's earned truths, for handing the SEEING models as priors — Jonathan:
    'that stuff is what's behind each pixel'. Empty string when nothing is earned yet."""
    core = None
    for p in glob.glob(os.path.join(root, "core_*.json")):
        try:
            with open(p, encoding="utf-8") as f: core = json.load(f)
            break
        except Exception: pass
    if not core: return ""
    invs = invariants_of(core, k)
    return "; ".join(i["text"] for i in invs)


# ---------------------------------------------------------------------------- scoring
_STOP = {"the", "a", "an", "by", "and", "or", "of", "to", "in", "on", "at", "it", "is", "are",
         "things", "something", "together"}


def _tokens(s: str) -> Set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOP}


_SYN = {   # a learner keeps the TALE's words, not ours — accept the honest paraphrases
    "body.impostor": [{"copy"}, {"double"}, {"impostor"}, {"twin"}],
    "camera.scrolled": [{"world", "shifts"}, {"world", "lurches"}, {"scrolls"}, {"scrolled"}, {"view", "slides"}],
    "window.new_ground": [{"ground", "reforms"}, {"ground", "reforming"}, {"ground", "appears"}, {"new", "ground"}],
    "object.vanished": [{"vanishes"}, {"disappears"}],
    "object.appeared": [{"appears"}, {"materializes"}],
}


def _match_atom(atom: str, lines: List[Set[str]]) -> bool:
    """One atom is matched when some single rule-line carries it: its number anchored by a word,
    or most of its phrase tokens, or an accepted paraphrase."""
    for s in [_tokens(_phrase(atom))] + _SYN.get(atom, []):
        digits = {t for t in s if t.isdigit()}; rest = s - digits
        for l in lines:
            if digits:
                if (digits & l) and (not rest or rest & l): return True
            else:
                need = len(s) if len(s) <= 2 else max(2, int(0.6 * len(s)))
                if len(s & l) >= need: return True
    return False


def score_extraction(extraction: str, invariants: List[Dict]) -> Dict:
    """CONCEPTS score per ATOM (a 3-atom truth honestly comes back as 2-3 separate rules):
    recovered when >= 2/3 of its atoms are found, each in some line. LAWS are one clause: a
    single line must carry most of the text's tokens. Per-line matching throughout, so two
    half-mentions in different rules don't fake an atom."""
    lines = [_tokens(l) for l in extraction.splitlines() if l.strip()]
    per = []
    for inv in invariants:
        if inv.get("kind") == "concept":
            atoms = inv["atoms"]
            hit = [a for a in atoms if _match_atom(a, lines)]
            need = len(atoms) if len(atoms) <= 2 else -(-2 * len(atoms) // 3)   # ceil(2n/3)
            per.append({"key": inv["key"], "want": atoms, "matched": len(hit), "hit": hit,
                        "needed": need, "recovered": len(hit) >= need})
        else:
            want = _tokens(inv["text"])
            need = max(2, int(0.6 * len(want))) if len(want) > 2 else len(want)
            best = max((len(want & l) for l in lines), default=0)
            per.append({"key": inv["key"], "want": sorted(want), "matched": best,
                        "needed": need, "recovered": best >= need})
    rec = sum(1 for p in per if p["recovered"])
    return {"per_invariant": per, "recovered": rec, "k": len(invariants),
            "score": round(rec / max(1, len(invariants)), 3)}


# ---------------------------------------------------------------------------- the two mouths
MOUTH_PROMPT = ("You are the storyteller of a small world called '{world}'. These are REAL rules the "
                "world has earned by living in it, in order:\n{rules}\n\n"
                "Write a SHORT tale (under 160 words) that begins with the line 'A story, not a report:' "
                "in which each rule VISIBLY HAPPENS, in the order given, to a single small character. "
                "The tale may ignore all other physics — skip gravity if you like — but every listed "
                "rule must occur exactly, with its numbers and directions kept. Do not number or list "
                "the rules; let the events show them.")

LEARNER_PROMPT = ("Here is a short tale from an unfamiliar world. From the tale ALONE, list the RULES "
                  "of that world — one rule per line, plainly, keeping any numbers and directions "
                  "exactly as the tale gives them. No commentary, just the rules.\n\nTALE:\n{tale}")


def tell(root: str, model: str = MODEL, k: int = K_DEFAULT, dry: bool = False) -> Optional[Dict]:
    world = os.path.basename(os.path.normpath(root))
    core = None
    for p in glob.glob(os.path.join(root, "core_*.json")):
        try:
            with open(p, encoding="utf-8") as f: core = json.load(f)
            break
        except Exception: pass
    if not core: print("no core in", root); return None
    invariants = invariants_of(core, k)
    if len(invariants) < 2: print(f"{world}: only {len(invariants)} earned invariants — not enough to thread a story"); return None

    sdir = os.path.join(root, "stories"); os.makedirs(sdir, exist_ok=True)
    n = len(glob.glob(os.path.join(sdir, "story_*.json"))) + 1
    rules = "\n".join(f"{i+1}. {inv['text']}" for i, inv in enumerate(invariants))

    if dry:
        tale = "A story, not a report:\n" + " Then ".join(inv["text"] + "." for inv in invariants)
        extraction = "\n".join(inv["text"] for inv in invariants)
    else:
        import lower
        models = lower.available([model])
        if not models: print("model not available:", model); return None
        tale = lower._ask(models[0], MOUTH_PROMPT.format(world=world, rules=rules),
                          timeout=180.0, num_predict=320)
        if not tale: print("the mouth said nothing"); return None
        tale = re.sub(r"<think>.*?</think>", "", tale, flags=re.S).strip()
        # the learner: a FRESH call, no shared context — reproduction requires independence
        extraction = lower._ask(models[0], LEARNER_PROMPT.format(tale=tale),
                                timeout=180.0, num_predict=300) or ""
        extraction = re.sub(r"<think>.*?</think>", "", extraction, flags=re.S).strip()

    sc = score_extraction(extraction, invariants)
    story = {"n": n, "world": world, "t": time.time(), "k": len(invariants),
             "invariants": [{"key": i["key"], "kind": i["kind"], "text": i["text"]} for i in invariants],
             "tale": tale, "extraction": extraction, "teach_back": sc,
             "label": "FICTION — truths re-verify by play only (honesty clause, ARC_OPEN_ENDS §5)"}
    jp = os.path.join(sdir, f"story_{n:03d}.json")
    with open(jp, "w", encoding="utf-8") as f: json.dump(story, f, indent=1, ensure_ascii=False)

    # the back-face open loop: a story is imagination sediment — open until played
    try:
        import geo
        wants = sorted({a for i in invariants for a in i["atoms"]})
        cont = geo.life_container(world, n, [], [], f"[fiction] {tale[:400]}", {}, "", jp, "story",
                                  {"drive": sc["score"], "W": 0, "H": 0},
                                  open_end={"wants": wants, "seed": f"story:{world}:{n}",
                                            "orientation": "back", "born": n, "status": "open",
                                            "evidence": 1})
        cont["manifest"]["name"] = f"story-{world}-{n:03d}"
        cont["manifest"]["tags"] = ["planet", world, "story", "fiction"]
        geo.write_geo(jp.replace(".json", ".geo"), cont, dormant=True)
    except Exception: pass

    print(f"story {n} for {world}: {sc['recovered']}/{sc['k']} invariants taught back "
          f"(score {sc['score']})\n  {tale[:140]}...")
    return story


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--k", type=int, default=K_DEFAULT)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    tell(a.root, a.model, a.k, a.dry)


if __name__ == "__main__":
    main()
