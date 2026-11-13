#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arc_batch.py — THE PROXY EXAM: play EVERY public ARC-AGI-3 game once with the generic agent
(PriorAgent + the budget law + the wisdom hook — the thing the Kaggle attempt actually submits),
and score it the way the hidden set will: levels cleared over levels available.

The ls20 chain is a scripted solver for one public game; it does not travel to Kaggle's hidden
games. What travels is the generic agent. So before spending an attempt, measure the generic
agent on the 24 public games it has never played (Sep 3: only ls20 had ever been played live).
Every run's transitions are laid on the torus under the game's own name, so the feel-prior
grows across games at the same time.

Usage:  python arc_batch.py                 (all games except ls20; ~2-3 min each, detached is best)
        python arc_batch.py --games ft09,vc33
        python arc_batch.py --summary       (the last batch's table and the proxy score)
"""
from __future__ import annotations
import argparse, glob, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\arc_batch" if os.name == "nt" else "/tmp/arc_batch"


def run_one(gid: str, key: str, timeout: int = 1200) -> dict:
    env = dict(os.environ, ARC_API_KEY=key)
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, "arc3_client.py"), "--game", gid, "--key", key, "--prior"],
                       capture_output=True, text=True, timeout=timeout, env=env, cwd=HERE,
                       creationflags=(0x08000000 if os.name == "nt" else 0))
    out = (r.stdout or "") + (r.stderr or "")
    lv = re.findall(r"levels_completed[\"']?:\s*(\d+)", out)
    lc = re.findall(r"level_count[\"']?:\s*(\d+)", out)
    st = re.findall(r"live: state=(\w+)", out)
    steps = re.findall(r"steps=(\d+)", out)
    wisdom = len(re.findall(r"wisdom at press", out))
    row = {"game": gid, "levels": int(lv[-1]) if lv else None, "level_count": int(lc[-1]) if lc else None,
           "state": st[-1] if st else None, "steps": int(steps[-1]) if steps else None, "wisdom_calls": wisdom,
           "seconds": round(time.time() - t0), "tail": out.strip().splitlines()[-3:]}
    try:                                       # keep the transitions per game and lay them on the torus
        src = os.path.join(HERE, "arc3_trans.jsonl")
        if os.path.exists(src):
            dst = os.path.join(OUT, f"trans_{gid.split('-')[0]}.jsonl"); shutil.copy(src, dst)
            import torus; torus.lay(dst, gid.split("-")[0])
            import pool; pool.feed_run(dst)
    except Exception: pass
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default=None); ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.summary:
        files = sorted(glob.glob(os.path.join(OUT, "batch_*.jsonl")))
        if not files: print("no batch yet"); return
        rows = [json.loads(l) for l in open(files[-1], encoding="utf-8") if l.strip()]
        summary(rows, files[-1]); return
    import arc_daily
    key = arc_daily.get_key()
    if not key: print("no key"); return
    from arc3_client import api
    games = [g["game_id"] for g in api("/api/games", key)]
    if a.games: want = [w.strip() for w in a.games.split(",")]; games = [g for g in games if g.split("-")[0] in want]
    else: games = [g for g in games if not g.startswith("ls20")]      # ls20 is the chain's; the daily covers it
    path = os.path.join(OUT, f"batch_{time.strftime('%Y%m%d_%H%M')}.jsonl")
    rows = []
    for i, gid in enumerate(games):
        print(f"[{i + 1}/{len(games)}] {gid} ...", flush=True)
        try: row = run_one(gid, key)
        except Exception as e: row = {"game": gid, "error": str(e)[:200]}
        rows.append(row)
        with open(path, "a", encoding="utf-8") as f: f.write(json.dumps(row) + "\n")
        print(f"   levels {row.get('levels')}/{row.get('level_count')} state {row.get('state')} steps {row.get('steps')} ({row.get('seconds')}s)", flush=True)
    summary(rows, path)


def summary(rows, path):
    got = sum(r.get("levels") or 0 for r in rows); tot = sum(r.get("level_count") or 0 for r in rows)
    played = [r for r in rows if r.get("level_count")]
    print(f"\nproxy exam ({os.path.basename(path)}): {len(played)} games played, {got}/{tot} levels = "
          f"{(got / tot if tot else 0):.3f}; games with >= 1 level: {sum(1 for r in rows if (r.get('levels') or 0) >= 1)}")
    for r in sorted(rows, key=lambda r: -(r.get("levels") or 0)):
        print(f"  {r['game'][:14]:14s} {str(r.get('levels')):>4s}/{str(r.get('level_count')):<4s} {str(r.get('state')):12s} steps {str(r.get('steps')):>4s} wisdom x{r.get('wisdom_calls', 0)}" + (f"  ERROR {r['error'][:60]}" if r.get("error") else ""))


if __name__ == "__main__":
    main()
