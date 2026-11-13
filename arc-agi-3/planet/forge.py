#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forge.py — the FORGE, stitched from the colony's sandbox-runner (D:\\shovelcat-colony) into the
planet's sleep: the first organ by which the planet improves ITSELF, gated by measurement.

The colony's law (sandbox-runner/src/forge.ts, engine.ts), ported faithfully:
  - a CANDIDATE upgrade is run against REFERENCE JOBS pulled from production history
    ("fight like you train" — SEVEN_BODY.md),
  - a DECISION POLICY promotes / holds / rejects on measured pass-rate and quality,
  - decisions write back to the registry, and review failures feed the RING as forge specs.
Notably the colony's Runner was still a stub ("will be replaced with real tool invocation").
This file is that replacement — the forge's first real runner:

  candidate   = a witness CONFIGURATION (instruction tail + wake depths; witness.TAILS)
  reference   = real recorded footage: clip_*.npz from the world's dashcam
  runner      = replay the witness over a clip's frames with the candidate config (fresh thread,
                same frames for every candidate — a fair race on identical history)
  quality     = the antenna feed rate (predictions later fed by what actually arrived)
  decision    = challenger PROMOTES over the champion only if it wins on a majority of the same
                jobs AND by a real margin on the mean; near-champion holds; else rejects
  registry    = forge/champion.json — the config the LIVE witness plays with (witness.py reads it)
  ledger      = forge/ledger.jsonl — every bout, both scores, the verdict
  ring        = forge/ring.json — when a world's LIVE antenna rate falls well below the forged
                rate, a review-failure entry is written; the next forge run challenges that world
                first (the phi_close ring: work failures become self-improvement specs)

Usage:  python forge.py --root D:\\planet\\ocean\\<world>          (one bout per sleep)
        python forge.py --root ... --dry                           (stub runner, plumbing test)
"""
from __future__ import annotations
import argparse, base64, glob, json, os, sys, time
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

import witness as W

MODEL = "gemma3:4b"
LOOKS = 8                  # frames replayed per reference job (every Nth frame of the clip)
CLIPS = 2                  # reference jobs per bout
MARGIN = 0.05              # the mean must improve by this much — no promotion on noise
FDIR = os.path.join(HERE, "forge")

CANDIDATES: List[Dict] = [           # the challenger pool, tried in order across sleeps
    {"id": "base-8", "tail": "base", "line_keep": 8, "far_keep": 8},
    {"id": "delta-8", "tail": "delta", "line_keep": 8, "far_keep": 8},
    {"id": "naming-8", "tail": "naming", "line_keep": 8, "far_keep": 8},
    {"id": "base-4", "tail": "base", "line_keep": 4, "far_keep": 4},
    {"id": "naming-12", "tail": "naming", "line_keep": 12, "far_keep": 8},
    {"id": "delta-12", "tail": "delta", "line_keep": 12, "far_keep": 8},
    # hue-as-context (Jonathan, Sep 2: "probably more useful for context stuff — a colorized
    # old photo is still the same thing but makes it more real"): one SCENE COLOR line
    # computed from the frame, prepended to the prompt. Color situates; it adds no objects.
    {"id": "hue-8", "tail": "base", "line_keep": 8, "far_keep": 8, "hue": True},
    {"id": "hue-delta-8", "tail": "delta", "line_keep": 8, "far_keep": 8, "hue": True},
]


def _hue_line(b64: str) -> str:
    """The colorized-photo line: which part of the circle this frame lives in."""
    try:
        import base64 as _b64, io
        import numpy as np
        from PIL import Image
        import hue as H
        img = np.asarray(Image.open(io.BytesIO(_b64.b64decode(b64))).convert("RGB"))[::6, ::6]
        h, s, v = H._rgb_to_hsv(img)
        mask = (s > 0.25) & (v > 0.15)
        if mask.sum() < 40:
            return "SCENE COLOR: gray, almost no color.\n"
        hist = np.bincount((h[mask] * 12).astype(int) % 12, minlength=12)
        top = hist.argsort()[::-1][:2]
        return f"SCENE COLOR: mostly {H.SEGS[top[0]]} and {H.SEGS[top[1]]}.\n"
    except Exception:
        return ""


def _load(p, default):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default


def _save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: json.dump(obj, f, indent=1, ensure_ascii=False)


# ------------------------------------------------------------------------- the runner
def replay(frames_b64: List[str], cfg: Dict, world: str, truths: str, ask_image) -> Dict:
    """Run one candidate over one reference job: a fresh thread walks the recorded frames.
    Returns the antenna verdict for that walk. Identical frames for every candidate = fair race."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        w = W.Witness(td, world, cfg=cfg)
        for b64 in frames_b64:
            p = w.prompt(truths)
            if cfg.get("hue"):
                p = _hue_line(b64) + p          # color situates the same scene (context, not detail)
            out = ask_image(p, b64)
            if out: w.absorb(out)
        fed, broken = w.antenna.get("fed", 0), w.antenna.get("broken", 0)
        n = fed + broken
        return {"fed": fed, "broken": broken, "rate": (fed / n) if n else 0.0,
                "lines": len(w.lines), "scored": n}


def reference_jobs(wroot: str, k: int = CLIPS) -> List[Tuple[str, List[str]]]:
    """Real production history: the newest clips, every Nth frame, as b64 jpegs."""
    jobs = []
    for p in sorted(glob.glob(os.path.join(wroot, "clips", "clip_*.npz")))[-k:]:
        try:
            import numpy as np
            z = np.load(p, allow_pickle=True)
            jpegs = [bytes(b) for b in z["J"]]
            step = max(1, len(jpegs) // LOOKS)
            picks = jpegs[::step][:LOOKS]
            if len(picks) >= 4:
                jobs.append((os.path.basename(p), [base64.b64encode(b).decode() for b in picks]))
        except Exception: continue
    return jobs


# ------------------------------------------------------------------------- the decision (forge.ts law)
def decide(champ: List[Dict], chall: List[Dict]) -> Tuple[str, str]:
    """Promote / hold / reject — the ported ForgeDecisionPolicy, paired on identical jobs."""
    if not champ or not chall: return "hold", "no-reference-jobs"
    wins = sum(1 for a, b in zip(chall, champ) if a["rate"] > b["rate"])
    mc = sum(x["rate"] for x in chall) / len(chall)
    mh = sum(x["rate"] for x in champ) / len(champ)
    if wins * 2 > len(champ) and mc >= mh + MARGIN:
        return "promote", f"wins {wins}/{len(champ)}, mean {mc:.2f} vs {mh:.2f}"
    if mc >= mh - MARGIN:
        return "hold", f"near-champion: mean {mc:.2f} vs {mh:.2f}"
    return "reject", f"below-champion: mean {mc:.2f} vs {mh:.2f}"


# ------------------------------------------------------------------------- the tunnel's voice
def sound_of(rotation: str, chall_runs: List[Dict]) -> Dict:
    """Where music comes from (Jonathan, Aug 31): the tunnel at each posture is an INSTRUMENT,
    and what passes through plays it. A wall hit is a broken prediction; a clean pass is a fed one.
      flat, nothing hits      -> SILENCE: the tunnel lies along the ring, ends sealed — impermeable
      flat, something hits    -> DRUM: one strike at the midpoint touching the ring — the beat
      extended, many hits     -> CHORD: bouncing all the way down — every reference job a string
      extended, nothing hits  -> FLUTE: through at full length without touching — pure resonance
    The sound is a real diagnostic: silence = confirmed seal, drum = wake up and extend, chord =
    rich learning signal, flute = mastery at length."""
    hits = sum(r.get("broken", 0) for r in chall_runs)
    scored = sum(r.get("scored", 0) for r in chall_runs)
    notes = [round(r.get("rate", 0.0), 2) for r in chall_runs]   # each job a string; its rate its pitch
    if scored == 0:
        inst = "unplayed"                # nothing went through the tunnel — no instrument sounded
    elif rotation == "flat":
        inst = "silence" if hits == 0 else "drum"
    else:
        inst = "flute" if hits == 0 else "chord"
    return {"instrument": inst, "hits": hits, "scored": scored, "notes": notes}


# ------------------------------------------------------------------------- the ring (phi_close)
def review_live(wroot: str, world: str, champion: Dict) -> None:
    """The review side: compare the world's LIVE antenna rate to the forged rate; a big shortfall
    is a review failure — written to the ring so the next forge bout targets this world first."""
    t = _load(os.path.join(wroot, "thread.json"), {})
    a = t.get("antenna", {}); n = a.get("fed", 0) + a.get("broken", 0)
    if n < 10: return
    live = a.get("fed", 0) / n
    forged = champion.get("forged_rate")
    if forged and live < forged - 0.15:
        ring = _load(os.path.join(FDIR, "ring.json"), {"specs": []})
        ring["specs"] = [s for s in ring["specs"] if s.get("world") != world][-15:]
        ring["specs"].append({"world": world, "live_rate": round(live, 2), "forged_rate": forged,
                              "t": time.time(), "why": "live antenna well below forged"})
        _save(os.path.join(FDIR, "ring.json"), ring)


# ------------------------------------------------------------------------- one bout
def bout(wroot: str, model: str = MODEL, dry: bool = False,
         force_challenger: str = None, force_clips: int = None, force_looks: int = None) -> Optional[Dict]:
    world = os.path.basename(os.path.normpath(wroot))
    ledger_p = os.path.join(FDIR, "ledger.jsonl")
    champion = _load(os.path.join(FDIR, "champion.json"), {"id": "base-8", "tail": "base",
                                                          "line_keep": 8, "far_keep": 8})
    tried = set()
    try:
        with open(ledger_p, encoding="utf-8") as f:
            tried = {json.loads(l)["challenger"] for l in f if l.strip()}
    except Exception: pass
    pool = [c for c in CANDIDATES if c["id"] != champion.get("id") and c["id"] not in tried] \
        or [c for c in CANDIDATES if c["id"] != champion.get("id")]
    if not pool: print("no challengers"); return None
    challenger = pool[int(time.time()) % len(pool)] if len(pool) > 1 else pool[0]
    if force_challenger:
        challenger = next((c for c in CANDIDATES if c["id"] == force_challenger), challenger)

    if dry:
        import hashlib
        def ask_image(prompt, b64):        # the stub runner, colony-style: deterministic, end-to-end
            h = int(hashlib.sha1((b64[:64] + prompt[-40:]).encode()).hexdigest(), 16)
            fav = "delta" in prompt or "no change" in prompt
            return (f"OBS: thing-{h % 7} moves toward marker {h % 5} while thing-{(h + 1) % 7} waits.\n"
                    f"PREDICT: thing-{h % 7 if fav else (h + 3) % 7} moves toward marker {h % 5}.")
        truths = "test truths"
    else:
        import lower
        models = lower.available([model])
        if not models: print("vision model not available:", model); return None
        def ask_image(prompt, b64):
            return lower._ask_image(models[0], prompt, b64, timeout=90.0, num_predict=160)
        try:
            from storyteller import truths_line
            truths = truths_line(wroot)
        except Exception: truths = ""

    # TUNNEL ROTATION (Jonathan, Aug 30): the bout's length is the loop seen at an angle.
    # Flat = a point: nothing is wrong, one short confirmation pass. Fully extended: the ring
    # holds a review-failure spec for this world, or the champion has never been measured here —
    # the whole seven-body length comes into view: more reference jobs, deeper looks.
    ring = _load(os.path.join(FDIR, "ring.json"), {"specs": []})
    ring_spec = any(sp.get("world") == world for sp in ring.get("specs", []))
    unmeasured = champion.get("forged_rate") is None or champion.get("world") != world
    if ring_spec:
        # deep work costs: an extended bout is funded by 1 ATP (verified past wins pay for
        # tomorrow's deep attention). Cannot pay -> run at normal size, never block.
        funded = True
        try:
            import atp
            funded = atp.spend("extended-rotation", f"ring spec on {world}")
        except Exception: pass
        if funded:
            clips, looks = 4, 12      # fully extended: the tunnel at length
        else:
            clips, looks = CLIPS, LOOKS
            ring_spec = False         # unfunded: rotation recorded as normal
    elif unmeasured:
        clips, looks = CLIPS, LOOKS   # normal rotation
    else:
        clips, looks = 1, 6           # flat: the point — a cheap confirmation bounce
    if force_clips: clips = force_clips
    if force_looks: looks = force_looks
    global LOOKS_ACTIVE
    jobs = reference_jobs(wroot, k=clips)
    jobs = [(n, f[:looks]) for n, f in jobs]
    if not jobs: print(f"{world}: no clips to train against"); return None
    champ_runs, chall_runs = [], []
    for name, frames in jobs:
        champ_runs.append(replay(frames, champion, world, truths, ask_image))
        chall_runs.append(replay(frames, challenger, world, truths, ask_image))
    verdict, why = decide(champ_runs, chall_runs)
    import socket
    rotation = "extended" if ring_spec else "flat" if not unmeasured else "normal"
    sound = sound_of(rotation, chall_runs)
    row = {"t": time.time(), "node": socket.gethostname().lower(),
           "world": world, "champion": champion.get("id"),
           "challenger": challenger["id"], "jobs": [j[0] for j in jobs], "rotation": rotation,
           "champion_runs": champ_runs, "challenger_runs": chall_runs,
           "verdict": verdict, "why": why, "sound": sound}
    os.makedirs(FDIR, exist_ok=True)
    with open(ledger_p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if verdict == "promote":
        new = dict(challenger)
        new["forged_rate"] = round(sum(x["rate"] for x in chall_runs) / len(chall_runs), 3)
        new["promoted_at"] = time.time(); new["over"] = champion.get("id"); new["world"] = world
        _save(os.path.join(FDIR, "champion.json"), new)
    else:
        champion.setdefault("forged_rate", round(sum(x["rate"] for x in champ_runs) / max(1, len(champ_runs)), 3))
        _save(os.path.join(FDIR, "champion.json"), champion)
    review_live(wroot, world, _load(os.path.join(FDIR, "champion.json"), {}))
    print(f"forge {world}: {challenger['id']} vs {champion.get('id')} -> {verdict} ({why}); "
          f"the tunnel played {sound['instrument']} ({sound['hits']} wall hits in {sound['scored']})")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--challenger", default=None)
    ap.add_argument("--clips", type=int, default=None)
    ap.add_argument("--looks", type=int, default=None)
    a = ap.parse_args()
    bout(a.root, a.model, a.dry, a.challenger, a.clips, a.looks)


if __name__ == "__main__":
    main()
