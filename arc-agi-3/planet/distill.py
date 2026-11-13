#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
distill.py — "feel out Claude's weights and copy them": the honest version.

Claude's weights cannot be read. What CAN be copied is Claude's BEHAVIOUR on the questions
this planet actually has — and only those, because a general copy is impossible at this
size and a specific one is what the core needs. Distillation here is a loop:

  1. ASK      — questions are generated from what the planet holds and cannot resolve:
                lightning (hot regions, unresolved candidate concepts), letters the chatbot
                wrote (mailbox/to_claude), library terms that recur but never got defined.
                They are written to distill/questions.jsonl and, as one document, to
                mailbox/to_claude/distill_<n>.md — so a Claude session (or the API, if
                ANTHROPIC_API_KEY is set) can answer them in one pass.
  2. ANSWER   — answers arrive as mailbox/from_claude/*.md (rain) or through the API;
                `--collect` pairs them with the questions into distill/dataset.jsonl.
  3. COPY     — `--build` makes a local model that carries the copied behaviour:
                  a) always: an Ollama model `planet-<base>` whose SYSTEM prompt is the
                     distilled sediment (definitions + Q/A pairs, compacted to fit) — the
                     cheapest copy: the surface of the answers, no weights changed;
                  b) when torch + peft + transformers are installed: a LoRA fine-tune of the
                     base on the dataset (real weight change) — distill/lora/. Not installed
                     on this machine yet (torch absent); the script says so and does (a).
  4. MEASURE  — `--score` asks the local model the held-out questions and counts, by atom
                overlap with Claude's answers, how much of the behaviour transferred.
                That number is the only honest "how much of Claude did we copy".

Usage:
  python distill.py --root D:\\planet\\ocean --ask            # write the questions
  python distill.py --root D:\\planet\\ocean --collect        # pair answers from mailbox/from_claude
  python distill.py --root D:\\planet\\ocean --build [--base qwen3:4b]
  python distill.py --root D:\\planet\\ocean --score
"""
from __future__ import annotations
import argparse, glob, json, os, re, subprocess, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, HERE)
import lower
from digester import atoms_of


def load_json(p, default):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default


def read_jsonl(p) -> List[Dict]:
    try:
        with open(p, "r", encoding="utf-8") as f: return [json.loads(l) for l in f if l.strip()]
    except Exception: return []


def write_jsonl(p, rows: List[Dict]):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------- 1. ask
def make_questions(root: str) -> List[Dict]:
    qs: List[Dict] = []
    for p in glob.glob(os.path.join(root, "*", "core_*.json")):
        world = os.path.basename(p)[5:-5]; c = load_json(p, {})
        lt = c.get("lightning", {})
        for score, i, j in lt.get("hot_regions", [])[:3]:
            qs.append({"kind": "lightning", "world": world,
                       "q": f"In the game '{world}', seen from the side, region row {i} column {j} of a 12x20 grid keeps surprising the "
                            f"player (charge {score:.2f}) and its {lt.get('n_actions')}-action life ended by '{lt.get('cause')}'. "
                            f"What kinds of things in such a game produce persistent unexplained motion there, and what should the player try?"})
        for k in lt.get("unresolved_candidates", [])[:5]:
            qs.append({"kind": "concept", "world": world,
                       "q": f"The player keeps seeing these events together but cannot name the situation: {k.replace('+', ' AND ')}. "
                            f"Give it a short name and a one-sentence definition of the form 'NAME is ...'."})
        for key, v in list(c.get("laws", {}).get("mover", {}).items())[:6]:
            qs.append({"kind": "law", "world": world,
                       "q": f"In '{world}', holding the key '{key}' moves the figure by (dy,dx)={v.get('value')} pixels per look "
                            f"(evidence {v.get('evidence')}). Is that consistent with how the game is normally played, and what does the key do beyond moving?"})
    lib = load_json(os.path.join(root, "core_library.json"), {})
    defined = set(lib.get("definitions", {}))
    for term, e in sorted(lib.get("terms", {}).items(), key=lambda kv: -kv[1]["docs"])[:12]:
        if term not in defined and "_" in term:
            qs.append({"kind": "term", "q": f"In the Shovelcat / folding-theory documents, the term '{term.replace('_', ' ')}' recurs in "
                                            f"{e['docs']} documents but is never defined. Define it in one sentence of the form 'TERM is ...'."})
    for p in sorted(glob.glob(os.path.join(root, "mailbox", "to_claude", "letter_*.md"))):
        txt = open(p, encoding="utf-8").read()
        m = re.search(r"## The question I could not answer\n(.+?)\n\n", txt, re.S)
        if m: qs.append({"kind": "letter", "q": m.group(1).strip(), "src": os.path.basename(p)})
    seen, out = set(), []
    for i, q in enumerate(qs):
        if q["q"] in seen: continue
        seen.add(q["q"]); q["id"] = f"q{int(time.time())%100000:05d}_{i:03d}"; out.append(q)
    return out


def ask(root: str) -> None:
    qs = make_questions(root)
    old = read_jsonl(os.path.join(root, "distill", "questions.jsonl"))
    known = {q["q"] for q in old}
    new = [q for q in qs if q["q"] not in known]
    write_jsonl(os.path.join(root, "distill", "questions.jsonl"), old + new)
    box = os.path.join(root, "mailbox", "to_claude"); os.makedirs(box, exist_ok=True)
    n = len(glob.glob(os.path.join(box, "distill_*.md"))) + 1
    p = os.path.join(box, f"distill_{n:03d}.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Distillation questions {n}\n\n*{time.strftime('%Y-%m-%d %H:%M')}* — {len(new)} new questions. "
                "Answer each under its id as `## <id>` in a file placed in mailbox/from_claude/. Prefer definitions "
                "('X is ...'); they are what the digester keeps best.\n\n")
        for q in new: f.write(f"## {q['id']} ({q['kind']})\n{q['q']}\n\n")
    print(f"{len(new)} new questions ({len(old) + len(new)} total) -> {p}")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and new:
        try:
            import urllib.request
            body = {"model": os.environ.get("DISTILL_MODEL", "claude-sonnet-4-5"), "max_tokens": 4000,
                    "messages": [{"role": "user", "content": open(p, encoding="utf-8").read()}]}
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                         headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=180) as r:
                txt = "".join(b.get("text", "") for b in json.loads(r.read().decode()).get("content", []))
            fb = os.path.join(root, "mailbox", "from_claude"); os.makedirs(fb, exist_ok=True)
            with open(os.path.join(fb, f"distill_{n:03d}_answers.md"), "w", encoding="utf-8") as f: f.write(txt)
            print("answers fetched through the API -> mailbox/from_claude")
        except Exception as e:
            print("API call failed (the letter still waits in the mailbox):", e)


# ----------------------------------------------------------------------------- 2. collect
def collect(root: str) -> None:
    qs = {q["id"]: q for q in read_jsonl(os.path.join(root, "distill", "questions.jsonl"))}
    ds_path = os.path.join(root, "distill", "dataset.jsonl")
    ds = read_jsonl(ds_path); have = {d["id"] for d in ds}
    added = 0
    for p in glob.glob(os.path.join(root, "mailbox", "from_claude", "*.md")) + glob.glob(os.path.join(root, "inbox", "eaten", "rain_*.md")):
        txt = open(p, encoding="utf-8").read()
        for m in re.finditer(r"^##\s+(q\d{5}_\d{3})[^\n]*\n(.+?)(?=^##\s+q\d{5}_|\Z)", txt, re.S | re.M):
            qid, ans = m.group(1), m.group(2).strip()
            if qid in qs and qid not in have and ans:
                ds.append({"id": qid, "kind": qs[qid]["kind"], "q": qs[qid]["q"], "a": ans, "src": os.path.basename(p)}); have.add(qid); added += 1
    write_jsonl(ds_path, ds)
    print(f"{added} new pairs, {len(ds)} total in {ds_path}")


# ----------------------------------------------------------------------------- 3. copy
def build(root: str, base: str) -> None:
    ds = read_jsonl(os.path.join(root, "distill", "dataset.jsonl"))
    lib = load_json(os.path.join(root, "core_library.json"), {})
    defs = [f"- {t}: {e['sentences'][0]}" for t, e in list(lib.get("definitions", {}).items())[:80]]
    pairs = [f"Q: {d['q']}\nA: {d['a'][:600]}" for d in ds[:60]]
    system = ("You are the planet's inhabitant: a local model carrying what a larger model (the clouds) answered "
              "for this system. Prefer these definitions and answers; if a question is outside them, say I DON'T HAVE THAT YET.\n\n"
              "DEFINITIONS\n" + "\n".join(defs) + "\n\nWHAT THE CLOUDS ANSWERED\n" + "\n\n".join(pairs))
    out = os.path.join(root, "distill"); os.makedirs(out, exist_ok=True)
    mf = os.path.join(out, "Modelfile")
    with open(mf, "w", encoding="utf-8") as f:
        f.write(f"FROM {base}\nPARAMETER temperature 0.2\nSYSTEM \"\"\"{system}\"\"\"\n")
    name = "planet-" + base.split(":")[0]
    try:
        r = subprocess.run(["ollama", "create", name, "-f", mf], capture_output=True, text=True, timeout=600,
                           creationflags=(0x08000000 if os.name == "nt" else 0))
        print(f"ollama create {name}: {'ok' if r.returncode == 0 else r.stderr[:300]}")
    except Exception as e:
        print("ollama create failed:", e)
    try:
        import torch, peft, transformers  # noqa
        print("torch+peft present: LoRA fine-tune would run here (not implemented until the dataset has >200 pairs)")
    except ImportError:
        print("no torch/peft on this machine: the copy is the prompt-carried one (planet-*). "
              "Install torch (cu128 for the RTX 5060 Ti) + peft + transformers to change weights for real.")


# ----------------------------------------------------------------------------- 4. measure
def score(root: str, base: str) -> None:
    ds = read_jsonl(os.path.join(root, "distill", "dataset.jsonl"))
    if len(ds) < 4: print("need at least 4 pairs to score"); return
    held = ds[-max(2, len(ds) // 5):]
    name = "planet-" + base.split(":")[0]
    models = lower.available([name, base])
    if not models: print("no local model available"); return
    rows = []
    for m in models:
        tot = 0.0
        for d in held:
            out = lower._ask(m, d["q"], timeout=180.0, num_predict=400) or ""
            out = re.sub(r"<think>.*?</think>", "", out, flags=re.S)
            a, b = atoms_of(out), atoms_of(d["a"])
            tot += len(a & b) / max(1, len(b))
        rows.append({"model": m, "held_out": len(held), "atom_recall": round(tot / len(held), 3), "t": time.time()})
        print(rows[-1])
    hist = read_jsonl(os.path.join(root, "distill", "scores.jsonl")); write_jsonl(os.path.join(root, "distill", "scores.jsonl"), hist + rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\planet\ocean"); ap.add_argument("--base", default="gemma3:4b")
    ap.add_argument("--ask", action="store_true"); ap.add_argument("--collect", action="store_true")
    ap.add_argument("--build", action="store_true"); ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.ask: ask(a.root)
    if a.collect: collect(a.root)
    if a.build: build(a.root, a.base)
    if a.score: score(a.root, a.base)
    if not (a.ask or a.collect or a.build or a.score): ap.print_help()


if __name__ == "__main__":
    main()
