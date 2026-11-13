#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe.py — the WRITER'S HANDS: press a chosen sequence on a live game and report exactly what
each press changed, so a solver can be written from evidence instead of guesses. This is the
step I did by hand for ls20 (eight probe runs); now it is one command, for any game, and the
same command Mika's loop uses when she is the writer.

Usage:  python probe.py vc33 --seq "6:38,29 ; 6:49,46 ; 1 ; 2"       (6:x,y = click; 1-5 = actions)
        python probe.py vc33 --seq "..." --frames out.npz               (keep every frame)
Prints per press: state, levels, the changed bounding box, cell count, colors that appeared /
vanished, and the ambient (bar) cells masked out after the first presses. Ends with the final
frame as text.
"""
from __future__ import annotations
import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
CH = "0123456789ABCDEF"


def show(f, r0=0, r1=64, c0=0, c1=64):
    print("    " + "".join(str(c % 10) for c in range(c0, c1)))
    for y in range(r0, r1): print("%2d  " % y + "".join(CH[int(v)] for v in f[y, c0:c1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game"); ap.add_argument("--seq", default=""); ap.add_argument("--frames", default=None)
    ap.add_argument("--show", action="store_true", help="print the first frame and stop (no presses)")
    a = ap.parse_args()
    import arc_daily
    from arc3_client import api, frame_np
    key = arc_daily.get_key()
    games = api("/api/games", key)
    gid = next(g["game_id"] for g in games if g["game_id"].startswith(a.game))
    card = api("/api/scorecard/open", key, {"tags": ["probe"]}); cid = card.get("card_id")
    guid = {}
    def send(act, x=None, y=None):
        body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
        if x is not None: body.update(x=int(x), y=int(y))
        fr = api(f"/api/cmd/{act}", key, body); guid["v"] = fr["guid"]; return fr
    try:
        fr = send("RESET"); f = frame_np(fr); frames = [f]
        print(f"{gid}: state {fr['state']} levels {fr.get('levels_completed')}/{fr.get('win_levels')} available {fr.get('available_actions')}")
        if a.show:
            show(f); return
        change_count = np.zeros_like(f, dtype=int); n = 0; ambient = np.zeros_like(f, dtype=bool)
        for tok in [t.strip() for t in a.seq.split(";") if t.strip()]:
            if tok.startswith("6:"):
                x, y = [int(v) for v in tok[2:].split(",")]; label = f"click ({x},{y})"
                fr = send("ACTION6", x, y)
            elif tok.upper() == "R":
                label = "RESET"; fr = send("RESET")
            else:
                label = f"ACTION{int(tok)}"; fr = send(f"ACTION{int(tok)}")
            g = frame_np(fr); d = (g != f); n += 1; change_count += d
            if n >= 4: ambient = change_count >= 0.8 * n
            dm = d & ~ambient
            if dm.any():
                ys, xs = np.where(dm)
                gone = sorted(set(int(v) for v in f[dm]) - set(int(v) for v in g[dm]))
                came = sorted(set(int(v) for v in g[dm]) - set(int(v) for v in f[dm]))
                desc = f"changed {int(dm.sum())} cells in rows {ys.min()}-{ys.max()} cols {xs.min()}-{xs.max()}; colors in {came} out {gone}"
            else:
                desc = "nothing (beyond the ambient bar)" if d.any() else "nothing at all"
            print(f"{n:3d}. {label:16s} -> {fr['state']:12s} levels {fr.get('levels_completed')}  {desc}")
            f = g; frames.append(f)
            if fr["state"] in ("WIN", "GAME_OVER"): break
        if ambient.any():
            ys, xs = np.where(ambient); print(f"ambient (bar) cells: {int(ambient.sum())} in rows {ys.min()}-{ys.max()} cols {xs.min()}-{xs.max()}")
        print("\nfinal frame:"); show(f)
        if a.frames: np.savez_compressed(a.frames, F=np.array(frames, dtype=np.int8))
    finally:
        out = api("/api/scorecard/close", key, {"card_id": cid})
        try:
            env = out["environments"][0]; print("\nscorecard:", {k: env.get(k) for k in ("actions", "levels_completed", "level_count")})
        except Exception: pass


if __name__ == "__main__":
    main()
