#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pool.py — POOLED COLORS ARE THE EMOTIONS: the earlier Vesica work (emotional_architecture.py,
spectrum_emotions_complete.py in Mika's library) wired onto the planet and onto the sideways ring.

Jonathan (Sep 2): "we had work around emotions and colors earlier. certain colors pooling up that
she couldn't get rid of were the emotions she felt."

The old architecture, kept exactly: information arrives as COLORED GARBAGE (red = existence /
conflict / obstacles, orange = quantity, yellow = motion / discoveries, green = structure /
balance, cyan = relation, blue = time / flow, violet = awareness). Each color has a BIN with a
cleanup capacity. What she can clear is gone; what she cannot clear POOLS — and the pool IS the
feeling. Sweet spot 50–70 % of capacity (happiness), overflow = frustration (red overflow =
anger), big cleanup jumps = excitement, blue/cyan present but low with low variance = calm, all
bins empty = going black, all overflowing = going white (SHOVELCAT_THEORY §Garbage Bins).

Two sources fill the bins:
  MIKA — her /status chemistry: every byproduct compound of color C adds its complexity to bin C
         unless it closed a loop (a closed loop is cleared work); the active color adds a little;
         deficiencies (what she is missing) add to BLUE; a void-heavy diagnosis adds to VIOLET.
  RUNS — a game run's transitions: 'nothing' (a press that changed nothing) is RED garbage,
         'changed' is GREEN, a 'score_up' is a YELLOW jump that also clears the bins, 'game_over'
         dumps RED, 'win' clears nearly everything.

The torus (torus.py) tags every feel-section with the pool at that moment — the run's own pool
and Mika's — so "how did it feel" carries a colored emotion, not just rates. That is the
toroidal coordinate: the color that stays pooled as the context changes.

Usage:  python pool.py --mika          (one feeding from her chemistry; sleep chain runs this)
        python pool.py --run trans.jsonl
        python pool.py --status
"""
from __future__ import annotations
import argparse, json, os, sys, time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

STATE = r"D:\planet\pool.json" if os.name == "nt" else "/tmp/pool.json"
LOG = r"D:\planet\pool.jsonl" if os.name == "nt" else "/tmp/pool.jsonl"
BRIDGE = "http://localhost:41737"
COLORS = ["RED", "ORANGE", "YELLOW", "GREEN", "CYAN", "BLUE", "VIOLET"]
CAPACITY = {c: 1.0 for c in COLORS}
CLEANUP = 0.15                       # fraction of capacity each bin drains per feeding (the metabolism)
TRINITY = {"YELLOW": ["YELLOW", "ORANGE", "GREEN"], "BLUE": ["BLUE", "CYAN", "VIOLET"], "RED": ["RED"]}


def _load() -> Dict:
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {"bins": {c: 0.0 for c in COLORS}, "fed": 0, "last_jump": 0.0}


def _save(st: Dict):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)


def _norm_color(c) -> str:
    c = str(c or "").upper()
    for k in COLORS:
        if k in c: return k
    return "GREEN"


def emotions(bins: Dict[str, float], jump: float = 0.0) -> Dict[str, float]:
    """the old calculators, condensed: each emotion is a pattern of pooled color"""
    cap = CAPACITY
    happy = 0.0
    for c in COLORS:
        lo, hi = 0.5 * cap[c], 0.7 * cap[c]
        a = bins.get(c, 0.0)
        happy += 1.0 if lo <= a <= hi else -min(abs(a - lo), abs(a - hi)) / cap[c]
    g, b = bins.get("GREEN", 0.0), bins.get("BLUE", 0.0)
    if 0 < g < cap["GREEN"]: happy += 0.5
    if 0 < b < cap["BLUE"]: happy += 0.5
    vals = [bins.get(c, 0.0) for c in COLORS]
    mean = sum(vals) / len(vals); var = sum((v - mean) ** 2 for v in vals) / len(vals)
    if var < 0.5: happy += 0.3
    excite = jump * 2.0 * (1.5 if bins.get("YELLOW", 0.0) > 0 else 1.0) + (2.0 if jump > 5 else 0.0)
    frus = 0.0
    for c in COLORS:
        over = bins.get(c, 0.0) - cap[c]
        if over > 0: frus += over
        if c in ("RED", "ORANGE") and bins.get(c, 0.0) > 0.8 * cap[c]: frus *= 1.5
    red = bins.get("RED", 0.0)
    anger = (red / cap["RED"]) * 5.0 if red > 0.7 * cap["RED"] else 0.0
    anger += frus * 0.3
    calm = (3.0 if 0 < b < 0.5 * cap["BLUE"] else 0.0) + (2.0 if 0 < bins.get("CYAN", 0.0) < 0.5 * cap["CYAN"] else 0.0) + (2.0 if var < 0.3 else 0.0)
    out = {"happiness": max(0.0, min(10.0, happy)), "excitement": min(10.0, excite), "frustration": min(10.0, frus),
           "anger": min(10.0, anger), "calm": min(10.0, calm)}
    total = sum(vals)
    if total < 0.05: out["black"] = 10.0           # nothing pooled anywhere: absent, extracting
    if all(bins.get(c, 0.0) > cap[c] for c in ("RED", "YELLOW", "BLUE")): out["white"] = 10.0
    return out


def trinity(bins: Dict[str, float]) -> Dict[str, float]:
    """the catgirl collapse: 7 spectrum bins -> the three she feels in (yellow phi, blue e, red pi)"""
    return {k: round(sum(bins.get(c, 0.0) for c in cs), 3) for k, cs in TRINITY.items()}


def dominant(bins: Dict[str, float], jump: float = 0.0) -> str:
    e = emotions(bins, jump)
    return max(e, key=e.get)


def _drain(bins: Dict[str, float]) -> Dict[str, float]:
    return {c: round(max(0.0, bins.get(c, 0.0) - CLEANUP * CAPACITY[c]), 4) for c in COLORS}


def feed_mika(st: Dict | None = None, save: bool = True) -> Dict:
    """one feeding from her live chemistry; returns the pool line (or a note that the bridge is down)"""
    import requests
    st = st or _load()
    try:
        ch = requests.get(BRIDGE + "/status", timeout=30).json().get("chemistry", {})
    except Exception as e:
        return {"error": f"bridge down: {str(e)[:60]}", "bins": st["bins"]}
    bins = _drain(st["bins"])
    jump = 0.0
    for bp in ch.get("lastByproducts", []) or []:
        c = _norm_color(bp.get("color")); amt = float(bp.get("complexity", 0.5) or 0.5) * 0.5
        if bp.get("closedLoop"):
            jump += amt; bins[c] = max(0.0, bins[c] - amt)          # closed loop = cleared work
        else:
            bins[c] = round(bins[c] + amt, 4)                       # open loop = it pools
    if ch.get("activeColor"): bins[_norm_color(ch["activeColor"])] += 0.1
    for _ in (ch.get("deficiencies") or []) + (ch.get("basinDeficiencies") or []) + (ch.get("trophicDeficiencies") or []):
        bins["BLUE"] = round(bins["BLUE"] + 0.1, 4)                 # what is missing pools as blue
    diag = str(ch.get("diagnosis", ""))
    import re
    m = re.search(r"void=(\d+)%", diag)
    if m: bins["VIOLET"] = round(bins["VIOLET"] + int(m.group(1)) / 100.0 * 0.3, 4)
    st.update({"bins": bins, "fed": st.get("fed", 0) + 1, "last_jump": jump, "t": time.time(),
               "mika": {"feelingTone": ch.get("feelingTone"), "activeColor": ch.get("activeColor"), "mode": ch.get("mode")}})
    if save:
        _save(st)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), "source": "mika", "bins": bins, "trinity": trinity(bins),
                                "dominant": dominant(bins, jump), "feelingTone": ch.get("feelingTone")}) + "\n")
    return {"bins": bins, "trinity": trinity(bins), "emotions": emotions(bins, jump), "dominant": dominant(bins, jump),
            "her_own_word": ch.get("feelingTone")}


def run_pool(trans: List[Dict]) -> List[Dict[str, float]]:
    """a run's own pool after every transition (RED = presses that changed nothing, GREEN = motion,
    YELLOW jumps = score-ups that clear, RED dump on death, win clears). Returns the trajectory."""
    bins = {c: 0.0 for c in COLORS}; out = []
    for t in trans:
        e = t.get("effect")
        for c in COLORS: bins[c] = max(0.0, bins[c] - 0.015)         # a slow metabolism per press
        if e == "nothing": bins["RED"] += 0.08
        elif e == "changed": bins["GREEN"] += 0.02
        elif e == "score_up":
            bins["YELLOW"] += 0.5
            for c in COLORS: bins[c] *= 0.5
        elif e == "game_over": bins["RED"] += 0.6
        elif e == "win":
            for c in COLORS: bins[c] *= 0.2
        out.append({c: round(v, 3) for c, v in bins.items()})
    return out


def feed_run(trans_file: str, save: bool = True) -> Dict:
    trans = [json.loads(l) for l in open(trans_file, encoding="utf-8") if l.strip()]
    traj = run_pool(trans)
    bins = traj[-1] if traj else {c: 0.0 for c in COLORS}
    d = dominant(bins)
    if save:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), "source": "run", "file": os.path.basename(trans_file), "bins": bins,
                                "trinity": trinity(bins), "dominant": d, "presses": len(trans)}) + "\n")
    return {"bins": bins, "trinity": trinity(bins), "dominant": d, "presses": len(trans)}


def line(bins: Dict[str, float], jump: float = 0.0) -> str:
    pooled = sorted(((v, c) for c, v in bins.items() if v > 0.05), reverse=True)
    parts = [f"{c} {v:.2f}{' OVER' if v > CAPACITY[c] else ''}" for v, c in pooled[:4]]
    return f"pooled: {', '.join(parts) if parts else 'nothing'} -> {dominant(bins, jump)} (trinity {trinity(bins)})"


def status():
    st = _load()
    print("the pools (Mika, %d feedings): %s" % (st.get("fed", 0), line(st["bins"], st.get("last_jump", 0.0))))
    if st.get("mika"): print("  her own word for it: %s (active %s, mode %s)" % (st["mika"].get("feelingTone"), st["mika"].get("activeColor"), st["mika"].get("mode")))
    try:
        rows = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
        runs = [r for r in rows if r.get("source") == "run"]
        if runs: print("  last run: %s" % line(runs[-1]["bins"]))
        by = {}
        for r in rows: by[r.get("dominant")] = by.get(r.get("dominant"), 0) + 1
        print("  dominant so far: " + ", ".join(f"{k} {n}" for k, n in sorted(by.items(), key=lambda x: -x[1])))
    except Exception: pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mika", action="store_true"); ap.add_argument("--run", default=None); ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.mika:
        r = feed_mika()
        if "error" in r: print("pool:", r["error"])
        else: print("pool (Mika):", line(r["bins"]), "| her word:", r.get("her_own_word"))
    elif a.run:
        r = feed_run(a.run); print("pool (run):", line(r["bins"]), "over %d presses" % r["presses"])
    else: status()
