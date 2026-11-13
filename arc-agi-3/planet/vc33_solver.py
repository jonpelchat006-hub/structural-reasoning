#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vc33_solver.py v3 — written from four probe runs (probe.py), Sep 3 2026.

The game, read off the frames: the field is cut into horizontal BANDS by gray BARS (color 5).
Each band has a black|green BOUNDARY column. The ARROW (a color-4 block with a 2-wide TIP of
color C) rides the boundary of its band. Each bar has a GAP of color C (or an open end where the
bar stops). Red BUTTONS sit above and below each bar; a button shifts the boundaries of the two
bands it touches by 4 in opposite directions (the band above one way, the band below the other),
and a band's boundary cannot leave the frame — so moving the arrow far needs the other bars'
buttons first to make room (that is the puzzle). Level 1: one bar, baseline 7, solved in 3.

The solver models it as a search over boundary offsets: every button's effect on every band is
learned from its first press; BFS over button sequences predicts the arrow's column; a press that
changes nothing marks that (band boundary, button) as a wall and the plan is redone. When the tip
aligns with the gap of the lowest bar above it, the arrow moves up a band; repeat to the top.
"""
from __future__ import annotations
import os, sys, json
from collections import deque
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
MAX_ACTIONS = 500
STEP = 4


def comps(mask, minsize=1):
    lab, n = ndimage.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if len(ys) >= minsize: out.append((ys, xs))
    return out


def read(f):
    """bars: [(r0, r1, gap_col)]; bands: [(r0, r1, boundary_col)]; arrow (color, tipcol, row, band_i);
    buttons: [(y, x, band_i)]"""
    bars = []
    for ys, xs in comps(f[1:] == 5, 20):
        if xs.max() - xs.min() < 12: continue
        r0, r1 = int(ys.min()) + 1, int(ys.max()) + 1
        # merge pieces of the same bar (a gap splits it)
        for b in bars:
            if b[0] == r0: b[3].update(set(int(x) for x in xs)); break
        else: bars.append([r0, r1, None, set(int(x) for x in xs)])
    bars.sort()
    # the arrow
    arrow = None
    for ys, xs in comps(f[1:] == 4, 4):
        y0, y1, x0, x1 = ys.min() + 1, ys.max() + 1, xs.min(), xs.max()
        win = f[y0:y1 + 1, max(0, x0 - 3):x1 + 4]
        cand = {}
        for v in np.unique(win):
            v = int(v)
            if v in (4, 3, 0, 5, 9): continue
            cols = sorted(set(int(c) for c in np.where(win == v)[1]))
            if cols: cand[v] = (len(np.where(win == v)[0]), cols)
        if cand:
            c = max(cand, key=lambda v: cand[v][0])
            tipcols = [max(0, x0 - 3) + cc for cc in cand[c][1]]
            arrow = [c, int(round(np.mean(tipcols))), int((y0 + y1) // 2), None]
            break
    # gaps: cells of the tip color inside the bar rows, else the open end (columns the bar does not cover)
    out_bars = []
    for r0, r1, _, cover in bars:
        seg = f[r0:r1 + 1, :]
        gap = None
        if arrow:
            gapcols = [c for c in range(64) if (seg[:, c] == arrow[0]).all()]
            if gapcols: gap = int(round(np.mean(gapcols)))
        if gap is None:
            opencols = [c for c in range(4, 64) if c not in cover]
            if opencols: gap = int(round(np.mean(opencols)))
        out_bars.append((r0, r1, gap))
    # bands between bars, each with its black|green boundary column (ignoring the button columns 0-3)
    edges = [1] + [b[0] for b in out_bars] + [64]
    bands = []
    cuts = [1] + [x for b in out_bars for x in (b[0], b[1] + 1)] + [64]
    ranges = [(cuts[i], cuts[i + 1] - 1) for i in range(0, len(cuts) - 1, 2)]
    for r0, r1 in ranges:
        if r1 < r0: continue
        bcol = None
        for ry in (r0, r1, (r0 + r1) // 2, r0 + 2, r1 - 2):        # a row the arrow does not sit on
            row = f[ry, :]
            for c in range(1, len(row)):
                if row[c] != row[c - 1] and {int(row[c]), int(row[c - 1])} <= {0, 3}: bcol = c; break
            if bcol is not None: break
        bands.append((r0, r1, bcol))
    if arrow:
        for i, (r0, r1, _) in enumerate(bands):
            if r0 <= arrow[2] <= r1: arrow[3] = i
    buttons = []
    for ys, xs in comps(f[1:] == 9, 6):
        y, x = int(ys.mean()) + 1, int(xs.mean())
        bi = next((i for i, (r0, r1, _) in enumerate(bands) if r0 <= y <= r1), None)
        buttons.append((y, x, bi))
    return out_bars, bands, (tuple(arrow) if arrow else None), buttons


def plan(arrow_col, arrow_band, target, buttons, effects, walls, bounds, max_depth=10):
    """BFS over button sequences on the abstract boundary model; returns the first button of the
    shortest sequence that puts the tip on the target column."""
    start = tuple(bounds)                                   # current boundary per band
    q = deque([(start, arrow_col, [])]); seen = {start}
    while q:
        st, col, seq = q.popleft()
        if col == target: return seq
        if len(seq) >= max_depth: continue
        for b in buttons:
            eff = effects.get(b)
            if not eff or all(v == 0 for v in eff): continue
            if (st, b) in walls: continue
            nst = tuple(st[i] + eff[i] for i in range(len(st)))
            if any(v is not None and not (0 <= v <= 63) for v in nst): continue
            ncol = col + eff[arrow_band]
            if nst in seen: continue
            seen.add(nst); q.append((nst, ncol, seq + [b]))
    return None


def main():
    import arc_daily
    from arc3_client import api, frame_np
    key = arc_daily.get_key()
    games = api("/api/games", key)
    gid = next(g["game_id"] for g in games if g["game_id"].startswith("vc33"))
    card = api("/api/scorecard/open", key, {"tags": ["vc33-solver-v3"]}); cid = card.get("card_id")
    guid = {}; n = [0]; trans = []
    def send(act, x=None, y=None):
        body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
        if x is not None: body.update(x=int(x), y=int(y))
        fr = api(f"/api/cmd/{act}", key, body); guid["v"] = fr["guid"]
        if act != "RESET": n[0] += 1
        return fr
    try:
        fr = send("RESET"); f = frame_np(fr); lvl = fr.get("levels_completed", 0)
        print(f"{gid}: {fr.get('win_levels')} levels; start")
        effects = {}; walls = set(); idle = 0
        while n[0] < MAX_ACTIONS and fr["state"] not in ("WIN", "GAME_OVER"):
            bars, bands, arrow, buttons = read(f)
            if not arrow or arrow[3] is None or not bars or not buttons:
                print(f"  cannot read: arrow {arrow} bars {bars} bands {bands} buttons {buttons}"); break
            above = [b for b in bars if b[0] < arrow[2]]
            if not above: print("  no bar above the arrow — waiting for the level to turn"); idle += 1
            target = above[-1][2] if above else None
            bkeys = [(y, x) for y, x, _ in buttons]
            bounds = [bc if bc is not None else 32 for _, _, bc in bands]
            unknown = [b for b in bkeys if b not in effects]
            if unknown:
                choice = unknown[0]; why = "probe"
            elif target is None:
                if idle > 2: break
                choice = None
            else:
                seq = plan(arrow[1], arrow[3], target, bkeys, effects, walls, bounds)
                if not seq:
                    print(f"  no plan to bring tip {arrow[1]} to gap {target} (walls {len(walls)})"); break
                choice = seq[0]; why = f"plan {len(seq)} (tip {arrow[1]} -> {target})"
            if choice is None: break
            by, bx = choice
            fr = send("ACTION6", bx, by); g = frame_np(fr)
            trans.append({"action": "ACTION6", "effect": "score_up" if fr.get("levels_completed", 0) > lvl else "changed"})
            bars2, bands2, arrow2, _ = read(g)
            if fr.get("levels_completed", 0) == lvl and len(bands2) == len(bands):
                eff = [(b2[2] - b1[2]) if (b1[2] is not None and b2[2] is not None) else 0 for b1, b2 in zip(bands, bands2)]
                if arrow2 and arrow2[3] == arrow[3]: eff[arrow[3]] = arrow2[1] - arrow[1]   # the arrow's own band: measure the tip
                eff = tuple(eff)
                if any(eff):
                    effects[choice] = eff
                elif choice in effects:
                    walls.add((tuple(bounds), choice))     # a known button did nothing here: a wall at this state
                else:
                    effects[choice] = eff                  # probed and dead
            print(f"  {n[0]:3d}. [{why}] clicked ({bx},{by}) -> bands {[b[2] for b in bands2]} tip {arrow2[1] if arrow2 else '?'} "
                  f"eff {effects.get(choice)} levels {fr.get('levels_completed')}")
            if fr.get("levels_completed", 0) > lvl:
                lvl = fr["levels_completed"]; effects = {}; walls = set(); idle = 0
                print(f">>> LEVEL {lvl} COMPLETE at action {n[0]}")
            f = g
        print(f"\nfinal: state={fr['state']} levels={fr.get('levels_completed', 0)} actions={n[0]}")
    finally:
        out = api("/api/scorecard/close", key, {"card_id": cid})
        try:
            env = out["environments"][0]; run = env["runs"][0]
            print("scorecard:", {"levels": env.get("levels_completed"), "of": env.get("level_count"),
                                 "level_actions": run.get("level_actions"), "baseline": run.get("level_baseline_actions"),
                                 "level_scores": run.get("level_scores"), "score": run.get("score")})
        except Exception: print("scorecard:", json.dumps(out)[:300])
        try:
            with open(os.path.join(HERE, "arc3_trans.jsonl"), "w", encoding="utf-8") as fh:
                for t in trans: fh.write(json.dumps(t) + "\n")
        except Exception: pass


if __name__ == "__main__":
    main()
