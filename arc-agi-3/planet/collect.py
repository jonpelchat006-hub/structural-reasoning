#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect.py — THE TOUCH: press every public ARC-AGI-3 game ~120 times and keep EVERY frame with
the press that made it, so a small eye can be trained on what a press changes. This is the data
the eye (eye.py) learns from; before it, the frames on disk were snapshots every 20 presses.

Policy is deliberately dumb (a fly's hand): for click games, click the small pieces first
(the clickables), then random cells; for action games, random among the available actions with
momentum (half the time repeat the last press, so movers travel). GAME_OVER -> RESET and keep
going; WIN -> next game. Every level change is kept in the log.

Usage:  python collect.py                    (all public games, 120 presses each -> D:\planet\eye\<game>.npz)
        python collect.py --games vc33,ft09 --presses 60
        python collect.py --summary
Each npz: F (n+1,64,64 int8 frames), A (n int: 0 RESET, 1-6), X, Y (n int, -1 when not a click),
L (n int levels after the press), S (n int: 0 not finished, 1 win, 2 game over).
"""
from __future__ import annotations
import argparse, glob, json, os, random, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"


def clickables(g, ambient=None, cap=40):
    from scipy import ndimage
    vals, counts = np.unique(g, return_counts=True)
    bg = set(int(v) for v, c in zip(vals, counts) if c > 900)
    out = []
    for v in vals:
        v = int(v)
        if v in bg: continue
        m = (g == v)
        if ambient is not None: m = m & ~ambient
        lab, n = ndimage.label(m)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if 1 <= len(ys) <= 200: out.append((len(ys), int(ys.mean()), int(xs.mean())))
    out.sort()
    seen, res = set(), []
    for n, y, x in out:
        k = (y // 3, x // 3)
        if k in seen: continue
        seen.add(k); res.append((x, y))
        if len(res) >= cap: break
    return res


def collect_game(gid, key, presses=120, log=print):
    from arc3_client import api, frame_np
    card = api("/api/scorecard/open", key, {"tags": ["eye-collect"]}); cid = card.get("card_id")
    guid = {}
    def send(act, x=None, y=None):
        body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
        if x is not None: body.update(x=int(x), y=int(y))
        last = None
        for t in range(4):
            try:
                fr = api(f"/api/cmd/{act}", key, body); guid["v"] = fr["guid"]; return fr
            except Exception as e:
                last = e; time.sleep(2 + 3 * t)
        raise last
    F, A, X, Y, L, S = [], [], [], [], [], []
    try:
        fr = send("RESET"); f = frame_np(fr); F.append(f)
        avail = [int(a) for a in (fr.get("available_actions") or [1, 2, 3, 4, 5, 6])]
        log(f"{gid}: levels {fr.get('win_levels')} available {avail}")
        change_count = np.zeros_like(f, dtype=int); n = 0; ambient = np.zeros_like(f, dtype=bool)
        queue = clickables(f) if 6 in avail else []
        random.shuffle(queue)
        last = None; resets = 0; changed = 0
        while n < presses:
            avail = [int(a) for a in (fr.get("available_actions") or avail) if 1 <= int(a) <= 6] or avail
            x = y = -1
            if 6 in avail and (len(avail) == 1 or random.random() < 0.7):
                act = 6
                if queue and random.random() < 0.75: x, y = queue.pop()
                else: x, y = random.randrange(64), random.randrange(64)
            else:
                acts = [a for a in avail if a != 6] or avail
                if last in acts and random.random() < 0.5: act = last
                else: act = random.choice(acts)
            fr = send("ACTION6", x, y) if act == 6 else send(f"ACTION{act}")
            g = frame_np(fr); d = (g != f); n += 1; change_count += d
            if n >= 4: ambient = change_count >= 0.8 * n
            if (d & ~ambient).any(): changed += 1
            F.append(g); A.append(act); X.append(x); Y.append(y); L.append(int(fr.get("levels_completed", 0) or 0))
            st = 1 if fr["state"] == "WIN" else 2 if fr["state"] == "GAME_OVER" else 0
            S.append(st); last = act; f = g
            if not queue and 6 in avail and n % 20 == 0: queue = clickables(f, ambient); random.shuffle(queue)
            if st == 1: log(f"  WIN at press {n}"); break
            if st == 2:
                resets += 1
                if resets > 10: break
                fr = send("RESET"); g = frame_np(fr)
                F.append(g); A.append(0); X.append(-1); Y.append(-1); L.append(int(fr.get("levels_completed", 0) or 0)); S.append(0)
                f = g; last = None; queue = clickables(f, ambient) if 6 in avail else []; random.shuffle(queue)
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, gid.split("-")[0] + ".npz")
        np.savez_compressed(path, F=np.array(F, dtype=np.int8), A=np.array(A, int), X=np.array(X, int), Y=np.array(Y, int),
                            L=np.array(L, int), S=np.array(S, int))
        row = {"game": gid, "presses": n, "changed": changed, "levels": int(max(L) if L else 0), "resets": resets,
               "available": avail, "path": path}
        log(f"  kept {len(F)} frames; {changed}/{n} presses changed something; levels {row['levels']}; resets {resets}")
        return row
    finally:
        try: api("/api/scorecard/close", key, {"card_id": cid})
        except Exception: pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default=None); ap.add_argument("--presses", type=int, default=120)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        for p in sorted(glob.glob(os.path.join(OUT, "*.npz"))):
            z = np.load(p); A = z["A"]; F = z["F"]
            ch = sum(1 for i in range(len(A)) if (F[i + 1] != F[i]).any())
            print(f"  {os.path.basename(p):12s} presses {len(A):4d} changed {ch:4d} levels {int(z['L'].max()) if len(z['L']) else 0}")
        return
    import arc_daily
    key = arc_daily.get_key()
    from arc3_client import api
    games = [g["game_id"] for g in api("/api/games", key)]
    if a.games:
        want = [w.strip() for w in a.games.split(",")]; games = [g for g in games if g.split("-")[0] in want]
    os.makedirs(OUT, exist_ok=True)
    logp = os.path.join(OUT, "collect.jsonl")
    for i, gid in enumerate(games):
        print(f"[{i + 1}/{len(games)}]", flush=True)
        try: row = collect_game(gid, key, a.presses)
        except Exception as e: row = {"game": gid, "error": str(e)[:200]}; print("  error", row["error"])
        with open(logp, "a", encoding="utf-8") as fh: fh.write(json.dumps(row) + "\n")
    print("done")


if __name__ == "__main__":
    main()
