#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ring.py — the OORT RING: the tail curls into a circle at the domain's edge.

Jonathan (Aug 30): "what if that tail leaving the memories ends up curling into a circle? each
deposit is a small section on that ring, and it expands by adding one section at a time — like
the Oort cloud. deposits near the edge of everything, old versions of code and stuff, things that
stick to the inside of your layer that point you to where in the core it came from."

So: an APPEND-ONLY ring of sections at the edge of the domain. Every deposit the planet makes —
a sleep commit (an old version of the code), a forge verdict, a story, a core update, a trained
adapter — becomes ONE section, and each section carries a POINTER back into the core (git hash,
file path, world). The ring is the index shell: persistent memory finally has a boundary you can
run your hand along and be pointed home from.

Placement is the spiral drive's own law: section n sits at angle n × 137.5° (the golden angle),
so the ring fills evenly as it expands one section at a time — sunflower packing; new sections
always land in the largest remaining gap, which is Jonathan's circle-on-the-grid void-filling
done automatically. The ring never rewrites: it only grows.

Usage:  python ring.py --scan            (harvest new deposits since last scan into sections)
        python ring.py --find "words"    (run your hand along the ring: matching sections + pointers)
        python ring.py --status
"""
from __future__ import annotations
import argparse, glob, json, math, os, re, subprocess, sys, time
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

RING = r"D:\planet\ring.jsonl" if os.name == "nt" else "/tmp/ring.jsonl"
STATE = RING.replace("ring.jsonl", "ring_state.json")
OCEAN = r"D:\planet\ocean" if os.name == "nt" else "/tmp/ocean"
GOLDEN_DEG = 360.0 * (1 - 1 / ((1 + 5 ** 0.5) / 2))          # ~137.5077


def _load_state() -> Dict:
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {"n": 0, "seen": {}}


def _append(sections: List[Dict], st: Dict) -> None:
    with open(RING, "a", encoding="utf-8") as f:
        for s in sections:
            s["n"] = st["n"]
            s["angle"] = round((st["n"] * GOLDEN_DEG) % 360.0, 2)
            st["n"] += 1
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)


def _atoms(s: str) -> List[str]:
    return sorted(set(re.findall(r"[a-z0-9_]{3,}", s.lower())))[:24]


def scan(code_dir: str = HERE) -> int:
    """Harvest every deposit made since the last scan into ring sections."""
    st = _load_state(); seen = st["seen"]; out = []
    # 1. sleep commits — the old versions of the code, exactly as he said
    try:
        r = subprocess.run(["git", "-C", code_dir, "log", "--format=%H|%ct|%s", "-40"],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            h, ct, msg = line.split("|", 2)
            if seen.get("git:" + h[:12]): continue
            seen["git:" + h[:12]] = 1
            out.append({"t": int(ct), "kind": "code-version", "label": msg[:110],
                        "pointer": {"git": h[:12], "dir": code_dir}, "atoms": _atoms(msg)})
    except Exception: pass
    # 2. forge verdicts
    for row in _tail_jsonl(os.path.join(code_dir, "forge", "ledger.jsonl"), 40):
        key = f"forge:{row.get('t')}"
        if seen.get(key): continue
        seen[key] = 1
        out.append({"t": row.get("t"), "kind": "forge-verdict",
                    "label": f"{row.get('challenger')} vs {row.get('champion')} -> {row.get('verdict')} ({row.get('world')})",
                    "pointer": {"path": os.path.join(code_dir, "forge", "ledger.jsonl"), "world": row.get("world")},
                    "atoms": _atoms(json.dumps([row.get("challenger"), row.get("champion"), row.get("world")]))})
    # 3. stories, cores, adapters, insights
    for p in glob.glob(os.path.join(OCEAN, "*", "stories", "story_*.json")):
        key = "story:" + p + str(int(os.path.getmtime(p)))
        if seen.get(key): continue
        seen[key] = 1
        try: s = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        out.append({"t": os.path.getmtime(p), "kind": "story",
                    "label": f"story {s.get('n')} of {s.get('world')} (teach-back {s.get('teach_back', {}).get('score')}"
                             + (f", mika {s.get('mika_teach_back', {}).get('score')}" if s.get('mika_teach_back') else "") + ")",
                    "pointer": {"path": p, "world": s.get("world")},
                    "atoms": _atoms(" ".join(i.get("text", "") for i in s.get("invariants", [])))})
    for p in glob.glob(os.path.join(OCEAN, "*", "core_*.json")):
        w = os.path.basename(os.path.dirname(p))
        try: c = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        key = f"core:{w}:{c.get('lives')}"
        if seen.get(key): continue
        seen[key] = 1
        out.append({"t": os.path.getmtime(p), "kind": "core-update",
                    "label": f"{w} at {c.get('lives')} lives, {len(c.get('concepts', {}))} concepts, "
                             f"{len(c.get('open_ends', {}))} open ends",
                    "pointer": {"path": p, "world": w},
                    "atoms": _atoms(" ".join(list(c.get("concepts", {}))[:12]))})
    ad = RING.replace("ring.jsonl", "lora/adapter") if os.name == "nt" else "/tmp/adapter"
    if os.path.isdir(os.path.dirname(ad)) and os.path.isdir(ad):
        key = "adapter:" + str(int(os.path.getmtime(ad)))
        if not seen.get(key):
            seen[key] = 1
            out.append({"t": os.path.getmtime(ad), "kind": "voice-weights",
                        "label": "planet-voice LoRA adapter (the mouth's own weights)",
                        "pointer": {"path": ad}, "atoms": ["lora", "adapter", "voice", "qwen"]})
    if len(seen) > 4000:                                     # the ledger of seen keys stays bounded
        st["seen"] = dict(list(seen.items())[-3000:])
    _append(out, st)
    return len(out)


def _tail_jsonl(p: str, k: int) -> List[Dict]:
    try:
        return [json.loads(l) for l in open(p, encoding="utf-8").read().splitlines()[-k:] if l.strip()]
    except Exception: return []


def find(q: str, k: int = 10, deep: bool = False) -> None:
    qa = set(_atoms(q))
    rows = _tail_jsonl(RING, 100000)
    if not deep:                     # absorbed members are represented by their compacts (--deep sees all)
        try:
            gone = set(json.load(open(RING.replace("ring.jsonl", "darkplanet.json"), encoding="utf-8"))["compacted"])
            rows = [r for r in rows if r["n"] not in gone]
        except Exception: pass
    scored = []
    for r in rows:
        s = len(qa & set(r.get("atoms", []))) + 2 * sum(1 for w in qa if w in r.get("label", "").lower())
        if s > 0: scored.append((s, r))
    scored.sort(key=lambda x: (-x[0], -x[1].get("t", 0)))
    for s, r in scored[:k]:
        print(f"  §{r['n']:>5} @ {r['angle']:6.2f}°  [{r['kind']:13s}] {r['label']}")
        print(f"         -> {json.dumps(r.get('pointer', {}), ensure_ascii=False)}")
    if not scored: print("  nothing on the ring matches — the core may still hold it (try voidsearch)")


def status() -> None:
    rows = _tail_jsonl(RING, 100000)
    kinds = {}
    for r in rows: kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"the ring holds {len(rows)} sections ({json.dumps(kinds)})")
    if rows: print(f"newest: §{rows[-1]['n']} @ {rows[-1]['angle']}° — {rows[-1]['label'][:90]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--find", default=None)
    ap.add_argument("--deep", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.scan: print(f"ring: {scan()} new sections laid (golden-angle placement)")
    if a.find: find(a.find, deep=a.deep)
    if a.status or not (a.scan or a.find): status()
