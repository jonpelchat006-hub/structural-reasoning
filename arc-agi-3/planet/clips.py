#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clips.py — SHORT-TERM VISUAL MEMORY: the eye keeps the last few seconds as real footage, and
the sleep breaks it down into the ocean.

Jonathan: "have it record small videos which then get broken down into the ocean and the rings
and geo files — all that raw data is what we're compacting down." The player keeps a rolling
buffer of raw frames (a dashcam); when a real surprise fires, or at every rest, the buffer is
sealed as a CLIP in <world>/clips/. Clips are the rawest sediment (L7-imagination in the
network's terms). In the SLEEP this module digests each new clip:

  raw clip (a tube: time × face)
    → three moments (begin / middle / end) shown TOGETHER to the seeing model → one grounded
      description of what happened across them (motion has a direction; a still can't say)
    → per-frame change magnitudes → the clip's own .geo loop (segments = how hard the picture
      moved, threshold bubbles at the spikes, the description on the text track)
    → a row in clips/ledger.jsonl the chatbot can retrieve ("what did you watch?")

The compaction ledger is explicit: raw bytes in, description+loop bytes kept, ratio recorded —
the same sediment law as everywhere else.

Usage:  python clips.py --root D:\\planet\\ocean\\<world>     (the spore chains this in the sleep)
"""
from __future__ import annotations
import argparse, base64, glob, json, os, sys, time
from typing import Dict, List, Optional
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import lower
import geo

MODEL = "gemma3:4b"
PER_RUN = 6                    # clips digested per sleep (oldest first; the rest wait)

PROMPT = ("These are three moments from a few seconds of screen footage: beginning, middle, end, in order. "
          "In two short sentences: what is happening ACROSS them — what moved, appeared, or changed, and in "
          "which direction? Only what is visible; if text or equations are on screen, quote the key words.")


def digest_clip(path: str, model: str) -> Optional[Dict]:
    try:
        z = np.load(path, allow_pickle=True)
        jpegs: List[bytes] = [bytes(b) for b in z["J"]]
        times = z["T"].tolist(); actions = [str(a) for a in z["A"]]
    except Exception:
        return None
    if len(jpegs) < 3: return None
    trio = [jpegs[0], jpegs[len(jpegs) // 2], jpegs[-1]]
    prompt = PROMPT
    try:                # the earned truths are what's behind each pixel — hand them to the eye as priors
        from storyteller import truths_line
        tl = truths_line(os.path.dirname(os.path.dirname(path)))
        if tl: prompt = f"(What this world is known to do: {tl}.)\n{PROMPT}"
    except Exception: pass
    desc = lower._ask_image(model, prompt, [base64.b64encode(b).decode() for b in trio],
                            timeout=150.0, num_predict=120)
    desc = (desc or "").strip()
    # per-frame change magnitudes (decoded small): the clip's pulse
    try:
        from PIL import Image
        import io
        small = []
        for b in jpegs:
            im = Image.open(io.BytesIO(b)).convert("L")
            im = im.resize((80, max(1, int(im.height * 80 / im.width))))
            small.append(np.asarray(im, dtype=np.float32))
        mags = [0.0] + [float(np.abs(a - b).mean()) for a, b in zip(small, small[1:])]
    except Exception:
        mags = [0.0] * len(jpegs)
    thresh = (np.mean(mags) + 2 * np.std(mags)) if len(mags) > 3 else 1e9
    body_path = [{"t": max(0.01, times[i] - times[i - 1]) if i else 0.25, "dx": round(m, 2), "dy": 0.0, "jump": 0.0}
                 for i, m in enumerate(mags)]
    events = [(["surprise.big"] if m > thresh else []) for m in mags]
    raw_bytes = sum(len(b) for b in jpegs)
    world = os.path.basename(os.path.dirname(os.path.dirname(path)))
    cont = geo.life_container("clip", 0, body_path, events, desc, {"actions": actions[:60]}, path, "", "watched",
                              {"drive": float(sum(1 for e in events if e)), "W": 0, "H": 0,
                               "raw_bytes": raw_bytes, "clip": os.path.basename(path)})
    cont["manifest"]["name"] = f"clip-{world}-{os.path.basename(path)[5:-4]}"
    cont["manifest"]["tags"] = ["planet", world, "clip"]
    gpath = path.replace(".npz", ".geo")
    geo.write_geo(gpath, cont, dormant=True)
    kept = len(desc.encode()) + os.path.getsize(gpath)
    return {"clip": os.path.basename(path), "world": world, "t": os.path.getmtime(path),
            "frames": len(jpegs), "seconds": round(times[-1] - times[0], 1) if len(times) > 1 else 0,
            "description": desc, "spikes": int(sum(1 for e in events if e)),
            "raw_bytes": raw_bytes, "kept_bytes": kept, "sediment_ratio": round(kept / max(1, raw_bytes), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    cdir = os.path.join(a.root, "clips")
    if not os.path.isdir(cdir): print("no clips folder in", a.root); return
    ledger = os.path.join(cdir, "ledger.jsonl")
    done = set()
    try:
        with open(ledger, "r", encoding="utf-8") as f:
            done = {json.loads(l)["clip"] for l in f if l.strip()}
    except Exception: pass
    models = lower.available([a.model])
    if not models: print("vision model not available:", a.model); return
    todo = [p for p in sorted(glob.glob(os.path.join(cdir, "clip_*.npz"))) if os.path.basename(p) not in done]
    n = 0
    for p in todo[:PER_RUN]:
        row = digest_clip(p, models[0])
        if row is None: continue
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        n += 1
        print(f"  {row['clip']}: {row['seconds']}s, {row['spikes']} spikes, sediment {row['sediment_ratio']} — {row['description'][:110]}")
    print(f"digested {n} clips ({len(todo) - n} waiting)")


if __name__ == "__main__":
    main()
