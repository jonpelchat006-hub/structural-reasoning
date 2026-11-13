#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chat.py — the planet's own CHATBOT: a lower-ocean model (Ollama, local) that can only speak
from what the planet has actually deposited — the cores (what the player learned), the
library (what the digester ate), the narrations (what the lives said) — plus a MAILBOX that
is the only way anything from the clouds gets in.

The grounding rule is the same as the narrator's: the model is handed the retrieved
sediment and told to answer only from it. When it cannot, it says so and writes a LETTER
to the clouds (mailbox/to_claude/<n>.md) — that is lightning: a bounded question with the
context that produced it. Answers dropped into mailbox/from_claude/ are rain: `--ingest`
moves them into the inbox, the digester eats them as documents, and they become library
sediment like anything else (untrusted until they recur / get used).

Usage:
  python chat.py --root D:\\planet\\ocean                # REPL over everything under the root
  python chat.py --root D:\\planet\\ocean --ask "what does the right key do in limbo?"
  python chat.py --root D:\\planet\\ocean --ingest        # eat the letters in mailbox/from_claude
  python chat.py --root D:\\planet\\ocean --status        # what the planet holds, in numbers
"""
from __future__ import annotations
import argparse, glob, json, math, os, re, shutil, sys, time
from collections import Counter
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, HERE)
import lower
from digester import atoms_of, STOP

DEFAULT_MODEL = "planet-voice"     # the planet's own weights (LoRA over qwen2.5:3b); gemma is the fallback
FALLBACK_MODEL = "gemma3:4b"


def load_json(p, default):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default


class Sediment:
    """Everything the planet has deposited, indexed for retrieval by atom overlap (tf-idf over atoms)."""
    def __init__(self, root: str):
        self.root = root
        self.library = load_json(os.path.join(root, "core_library.json"), {})
        self.cores = {os.path.basename(p)[5:-5]: load_json(p, {}) for p in glob.glob(os.path.join(root, "*", "core_*.json"))}
        self.docs: List[Dict] = []          # chunks: {"doc", "i", "text", "atoms"}
        for p in glob.glob(os.path.join(root, "library", "*.json")):
            d = load_json(p, {})
            for c in d.get("chunks", []):
                if c.get("text"): self.docs.append({"doc": d["doc"], "i": c["i"], "text": c["text"], "atoms": set(atoms_of(c["text"]))})
        for p in glob.glob(os.path.join(root, "*", "clips", "ledger.jsonl")):
            world = os.path.basename(os.path.dirname(os.path.dirname(p)))
            try:
                with open(p, encoding="utf-8") as f:
                    for l in f:
                        r = json.loads(l)
                        if r.get("description"):
                            t = f"[watched {world}, {time.strftime('%b %d %H:%M', time.localtime(r['t']))}] {r['description']}"
                            self.docs.append({"doc": f"clip:{world}", "i": r["clip"], "text": t, "atoms": set(atoms_of(t))})
            except Exception: pass
        for p in glob.glob(os.path.join(root, "*", "stories", "story_*.json")):
            s = load_json(p, {})
            if s.get("tale"):
                t = (f"[a story the planet told about {s.get('world')}, teach-back score "
                     f"{s.get('teach_back', {}).get('score')}] {s['tale']}")
                self.docs.append({"doc": f"story:{s.get('world')}", "i": s.get("n", 0), "text": t,
                                  "atoms": set(atoms_of(t))})
        for p in glob.glob(os.path.join(root, "*", "witness_*.txt")):
            world = os.path.basename(os.path.dirname(p))
            try:
                lines = open(p, encoding="utf-8").read().splitlines()[-200:]
            except Exception: continue
            for k in range(0, len(lines), 6):
                t = f"[watched {world}, the witness thread] " + "\n".join(lines[k:k + 6])
                self.docs.append({"doc": f"witness:{world}", "i": k, "text": t, "atoms": set(atoms_of(t))})
        self.narrations: List[Dict] = []    # narration lines as chunks too (a life's own words)
        for p in glob.glob(os.path.join(root, "*", "narration_*.txt")):
            world = os.path.basename(p)[10:-4]
            try:
                lines = open(p, encoding="utf-8").read().splitlines()[-400:]
            except Exception: continue
            for k in range(0, len(lines), 8):
                t = "\n".join(lines[k:k + 8])
                self.docs.append({"doc": f"life:{world}", "i": k, "text": t, "atoms": set(atoms_of(t))})
        df = Counter(a for d in self.docs for a in d["atoms"])
        n = max(1, len(self.docs))
        self.idf = {a: math.log(1 + n / c) for a, c in df.items()}

    def retrieve(self, q: str, k: int = 6) -> List[Dict]:
        qa = atoms_of(q)
        scored = []
        for d in self.docs:
            s = sum(self.idf.get(a, 0.0) for a in qa & d["atoms"])
            if s > 0: scored.append((s / math.sqrt(len(d["atoms"]) + 10), d))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:k]]

    def definitions(self, q: str, k: int = 6) -> List[Tuple[str, str]]:
        qa = {a for a in atoms_of(q) if "_" not in a}
        out = []
        for term, e in self.library.get("definitions", {}).items():
            words = set(term.split())
            if words & qa: out.append((term, e["sentences"][0]))
        return out[:k]

    def core_summary(self) -> str:
        parts = []
        for world, c in self.cores.items():
            laws = c.get("laws", {})
            mv = {k: v["value"] for k, v in laws.get("mover", {}).items() if v.get("evidence", 0) >= 1}
            h = c.get("history", [])[-3:]
            parts.append(f"world {world}: {c.get('lives', 0)} lives; keys→movement (dy,dx) {json.dumps(mv)}; "
                         f"concepts {list(c.get('concepts', {}))[:8]}; last lives {[(x.get('n_actions'), x.get('cause'), x.get('drive')) for x in h]}; "
                         f"lightning {json.dumps(c.get('lightning', {}).get('hot_regions', [])[:3])}")
        s = self.library.get("sediment", {})
        if s: parts.append(f"library: {s.get('docs')} documents, {s.get('definitions')} definitions, {s.get('terms')} terms")
        st = self.stats_summary()
        if st: parts.append("watched sessions (the stats organ read these off the screen):\n" + st)
        return "\n".join(parts) or "nothing deposited yet"

    def stats_summary(self) -> str:
        try:
            import stats as _st
        except Exception:
            return ""
        lines = []
        for p in glob.glob(os.path.join(self.root, "*", "stats", "sessions.json")):
            lines.extend(_st.summary(os.path.dirname(os.path.dirname(p))).splitlines())
        return "\n".join(lines[-10:])


def answer(model: str, sed: Sediment, q: str, history: List[Tuple[str, str]]) -> Tuple[str, bool]:
    chunks = sed.retrieve(q)
    defs = sed.definitions(q)
    ctx = "\n\n".join(f"[{c['doc']}#{c['i']}] {c['text']}" for c in chunks)
    dtx = "\n".join(f"- {t}: {s}" for t, s in defs)
    hist = "\n".join(f"Q: {a}\nA: {b}" for a, b in history[-3:])
    prompt = (
        "You are the inhabitant of a small learning system (a 'planet'). You may answer ONLY from the material "
        "below, which is what the system has actually learned or read. Quote the source tag in brackets when you "
        "use a passage. The 'watched sessions' lines under the player's learnings were read off the user's own screen "
        "while watching them play — they are known facts about the user's games: answer stats questions (KDA, gold, results) "
        "from them directly and confidently. Only if the material truly does not contain the answer, begin with exactly: I DON'T HAVE THAT YET, then one "
        "sentence on what would be needed. Answer DIRECTLY in at most five sentences — do not narrate your reasoning, "
        "do not restate the question or the rules, do not list what you reviewed; no invented facts.\n\n"
        f"== what the player has learned ==\n{sed.core_summary()}\n\n== definitions ==\n{dtx or '(none match)'}\n\n"
        f"== passages ==\n{ctx or '(none match)'}\n\n{hist}\nQ: {q}\nA:")
    out = lower._ask(model, prompt, timeout=180.0, num_predict=450)
    if out is None: return "(the lower ocean is not answering — is Ollama running?)", False
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
    return out, out.upper().lstrip("* ").startswith("I DON'T HAVE THAT")


def write_letter(root: str, q: str, a: str, sed: Sediment) -> str:
    box = os.path.join(root, "mailbox", "to_claude"); os.makedirs(box, exist_ok=True)
    n = len(glob.glob(os.path.join(box, "*.md"))) + 1
    p = os.path.join(box, f"letter_{n:03d}.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Letter {n} to the clouds\n\n*{time.strftime('%Y-%m-%d %H:%M')}*\n\n## The question I could not answer\n{q}\n\n"
                f"## What I said\n{a}\n\n## What I hold\n{sed.core_summary()}\n\n"
                "## Rules for the answer\nReply as a document in mailbox/from_claude/. It will be eaten as rain: "
                "untrusted until it recurs or is used. Definitions ('X is ...') are what the digester keeps best.\n")
    return p


def ingest(root: str) -> None:
    src = os.path.join(root, "mailbox", "from_claude"); inbox = os.path.join(root, "inbox")
    os.makedirs(src, exist_ok=True); os.makedirs(inbox, exist_ok=True)
    moved = 0
    for f in os.listdir(src):
        p = os.path.join(src, f)
        if os.path.isfile(p):
            shutil.move(p, os.path.join(inbox, "rain_" + f)); moved += 1
    print(f"{moved} letters moved to the inbox as rain")
    if moved:
        import subprocess
        subprocess.run([sys.executable, os.path.join(HERE, "digester.py"), "--root", root], check=False,
                       creationflags=(0x08000000 if os.name == "nt" else 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\planet\ocean")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ask", default=None)
    ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.ingest: ingest(a.root); return
    sed = Sediment(a.root)
    if a.status:
        print(sed.core_summary()); print(f"{len(sed.docs)} retrievable passages"); return
    models = lower.available([a.model, FALLBACK_MODEL])
    if not models: print("model not available in Ollama:", a.model); return
    hist: List[Tuple[str, str]] = []
    def one(q: str):
        out, missing = answer(models[0], sed, q, hist)
        print(out); hist.append((q, out))
        if missing:
            print("  -> letter written:", write_letter(a.root, q, out, sed))
    if a.ask: one(a.ask); return
    print("planet chat — ask about what it has learned/read; 'quit' to leave")
    while True:
        try: q = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not q or q.lower() in ("quit", "exit"): break
        one(q)


if __name__ == "__main__":
    main()
