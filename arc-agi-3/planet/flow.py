#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
flow.py — THE MOTION MAP: the derivative of the screen with respect to each button.

Jonathan (Sep 3): "part of the map should have a direction to where we think it'll go — the derivative — walls
have movement 0, the budget drains every turn so that pattern should appear; press up and see what parts move
and predict where they go next; each pixel gets a coloured arrow; the controls sit in the foreground and each
button pokes pins into the pixels it controls; the surprises pile up behind the screen."

For every recorded press (frame, action, next frame) the motion of each changed pixel is measured: where its
colour went (the displace search from induce.py, then per-piece block matching), or that it vanished /
appeared (no motion, a colour event). Aggregated per (button, colour of the pixel): the mode vector and how
often the pixel obeyed it. That table IS the pins — which pixels a button controls and where it sends them.
The register (budget bar) is a front that moves a fixed number of cells per press; it gets its own arrow.
The surprise layer counts, per pixel, the presses where the pixel did not do what its pins said.

Output: D:\planet\eye\flow_<game>.png — the level's first frame with arrows per button, the controller with
pins to the pixels it moves, the register's drift, and the surprise layer; plus flow_<game>.json (the table).

Usage:  python flow.py sp80             python flow.py sp80,ls20,tr87        python flow.py ls20 --view side|front|eyes
        THE THREE VIEWS (Jonathan, Sep 7): --view side draws what stands (the fence: trail, walls, openings), --view front
        what lies flat and the diagonal feet with their back-wall marks, --view eyes the water, the meter and the pins'
        counts; without --view, everything.
"""
from __future__ import annotations
import json, os, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import induce
VIEW = "all"

OUT = r"D:\planet\eye"
PAL = [(0, 0, 0), (0, 116, 217), (255, 65, 54), (46, 204, 64), (255, 220, 0), (170, 170, 170), (240, 18, 190), (255, 133, 27),
       (127, 219, 255), (135, 12, 37), (255, 255, 255), (64, 64, 64), (160, 80, 0), (120, 200, 120), (200, 120, 200), (80, 160, 200)]
ACT_COL = {1: (80, 200, 255), 2: (255, 120, 60), 3: (255, 230, 80), 4: (150, 255, 120), 5: (240, 120, 255), 6: (255, 255, 255)}
ACT_NAME = {1: "1 up", 2: "2 down", 3: "3 left", 4: "4 right", 5: "5 act", 6: "6 click"}
R = 8                                    # pixels per cell


def press_flow(f0, f1, mask, bg):
    """per-cell motion for one press: flow (H,W,2) where a cell's colour went, moved mask, vanished, appeared"""
    H, W = f0.shape; flow = np.zeros((H, W, 2), np.int16); moved = np.zeros((H, W), bool)
    D = (f0 != f1) & mask
    explained = np.zeros((H, W), bool)
    r = induce.explain_shift(f0, f1, mask, bg)
    if r is not None:
        d, S, fill, t = r
        core = S & (f0 != fill) & (f0 != bg)              # the mover proper, not the uniform floor swept along with it
        if not core.any(): core = S
        flow[core] = d; moved |= core; explained |= S | induce.shifted(S, *d, fill=False)
    rest = D & ~explained
    vals, counts = np.unique(f0, return_counts=True)
    floor = set(int(v) for v, c in zip(vals, counts) if c > 900)      # floor and walls never move; only pieces do
    if rest.any():                              # pieces the one-shift story missed: match each by its own colour
        lab, n = ndimage.label(rest & ~np.isin(f0, sorted(floor)))
        for i in range(1, n + 1):
            O = (lab == i)
            ys, xs = np.where(O); col = f0[O]
            best = None
            for dy in range(-8, 9):
                for dx in range(-8, 9):
                    if dy == 0 and dx == 0: continue
                    ny, nx = ys + dy, xs + dx
                    if ny.min() < 0 or nx.min() < 0 or ny.max() >= H or nx.max() >= W: continue
                    if np.array_equal(f1[ny, nx], col) and not np.array_equal(f0[ny, nx], col):
                        n_ = abs(dy) + abs(dx)
                        if best is None or n_ < best[0]: best = (n_, dy, dx)
            if best: flow[O] = (best[1], best[2]); moved |= O
    vanished = D & ~moved & (f0 != bg) & (f1 == bg)
    appeared = D & ~moved & (f1 != bg) & (f0 == bg)
    return flow, moved, vanished, appeared, D


def register_drift(pairs, amb):
    """the register front: mean shift of the boundary between the bar's colour and its background per press"""
    if not amb.any(): return None
    ys, xs = np.where(amb); band = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    shifts = []
    for f0, f1, *_ in pairs:
        a0, a1 = f0[band], f1[band]
        if np.array_equal(a0, a1): continue
        D = a0 != a1
        cy, cx = np.where(D)
        # the front is the changed cells' centroid; direction = along the band's long axis, sign from which side gained bg
        shifts.append((float(cy.mean()), float(cx.mean())))
    if len(shifts) < 3: return None
    s = np.array(shifts); horiz = (band[1].stop - band[1].start) >= (band[0].stop - band[0].start)
    seq = s[:, 1] if horiz else s[:, 0]
    dv = np.diff(seq); dv = dv[np.abs(dv) <= 6]
    step = float(np.median(dv)) if len(dv) else 0.0
    return {"band": [int(band[0].start), int(band[0].stop), int(band[1].start), int(band[1].stop)], "horizontal": bool(horiz),
            "cells_per_press": round(step, 2)}


def build(game):
    g = induce.load_game(os.path.join(OUT, f"{game}.npz"))
    if g is None: return None
    pairs = g[0] + g[1]
    amb = induce.ambient_mask(pairs) | induce.tick_region(pairs); mask = ~amb; bg = induce.background(pairs[0][0])
    H, W = pairs[0][0].shape
    pins: dict = {}                            # (action, colour) -> {vec: count}
    obey: dict = {}                            # (action, colour) -> [obeyed, total]
    surprise = np.zeros((H, W), np.int32); moved_ever = np.zeros((6 + 1, H, W), np.int32)
    flows = []
    for f0, f1, a, x, y in pairs:
        flow, moved, van, app, D = press_flow(f0, f1, mask, bg)
        flows.append((a, flow, moved, van, app, D))
        for c in np.unique(f0[moved]):
            m = moved & (f0 == c)
            for v, cnt in zip(*np.unique(flow[m].reshape(-1, 2), axis=0, return_counts=True)):
                pins.setdefault((a, int(c)), {})[(int(v[0]), int(v[1]))] = pins.setdefault((a, int(c)), {}).get((int(v[0]), int(v[1])), 0) + int(cnt)
        moved_ever[a] += moved
    # the pins: per (button, colour) the mode vector; then the surprise layer = presses where a pixel of that colour
    # under that button did NOT move by the mode vector (walls, refusals, cascades) or moved when its pins say still
    table = {}
    for (a, c), vs in pins.items():
        v, n = max(vs.items(), key=lambda kv: kv[1]); tot = sum(vs.values())
        table[(a, c)] = {"vec": list(v), "agree": round(n / tot, 3), "n": int(tot)}
    # THE BOND (Jonathan, Sep 3): attachment is two-sided. Every control wants to attach to every pixel and breaks
    # off where its claim fails; every pixel wants to stay independent and attaches only under repeated evidence.
    # Run the presses in order: a control's claim on a colour starts at a small prior, climbs fast when the colour
    # obeys (control side, eager), halves on a violation (the break), and decays a little on every press where the
    # control was used and the colour did nothing (the pixel side, drifting back to independence).
    bond = {}
    vals0, counts0 = np.unique(pairs[0][0], return_counts=True); floor0 = set(int(v) for v, c in zip(vals0, counts0) if c > 900)
    for (f0, f1, a, x, y), (aa, flow, moved, van, app, D) in zip(pairs, flows):
        for (bb, c), t in table.items():
            if bb != a or c in floor0: continue
            m = (f0 == c) & mask
            if not m.any(): continue
            b = bond.get((a, c), 0.1)
            obeyed = int((moved & m & (flow == t["vec"]).all(-1)).sum()); present = int(m.sum())
            violated = int((moved & m & ~(flow == t["vec"]).all(-1)).sum())
            if violated > 0.2 * present: b *= 0.5                     # the break
            elif obeyed > 0.5 * present: b += (1 - b) * 0.35           # the attach
            else: b *= 0.9                                            # nothing happened: drift toward independence
            bond[(a, c)] = b
    for k, t in table.items(): t["bond"] = round(bond.get(k, 0.0), 3)
    for f0, f1, a, x, y in pairs:
        flow, moved, van, app, D = press_flow(f0, f1, mask, bg)
        pred = np.zeros((H, W), bool); predv = np.zeros((H, W, 2), np.int16)
        vals, counts = np.unique(f0, return_counts=True); floor = set(int(v) for v, c in zip(vals, counts) if c > 900)
        for (aa, c), t in table.items():
            if aa == a and t["agree"] >= 0.5 and c not in floor:
                m = (f0 == c) & mask; pred |= m; predv[m] = t["vec"]
        wrong = (pred & ~moved) | (moved & ~pred) | (moved & pred & (flow != predv).any(-1))
        surprise += wrong & mask
    reg = register_drift(pairs, amb)
    out = {"game": game, "presses": len(pairs), "bg": bg, "register": reg,
           "pins": [{"action": a, "colour": c, **t} for (a, c), t in sorted(table.items())],
           "moved_cells_per_action": {int(a): int((moved_ever[a] > 0).sum()) for a in range(1, 7)}}
    json.dump(out, open(os.path.join(OUT, f"flow_{game}.json"), "w"), indent=1)
    return pairs, amb, bg, table, surprise, reg, moved_ever, out


def render(game, pairs, amb, bg, table, surprise, reg, moved_ever, out):
    f = pairs[0][0]; H, W = f.shape
    panel = 120
    img = Image.new("RGB", (W * R + 340, H * R + panel), (18, 18, 22)); d = ImageDraw.Draw(img)
    # the screen, dimmed where surprise piled up behind it
    smax = max(1, int(surprise.max()))
    for y in range(H):
        for x in range(W):
            col = PAL[int(f[y, x]) % 16]
            s = surprise[y, x] / smax
            col = tuple(int(c * (1 - 0.6 * s) + 255 * 0.6 * s * (i == 0)) for i, c in enumerate(col))   # redden by surprise
            d.rectangle([x * R, y * R, x * R + R - 1, y * R + R - 1], fill=col)
    # THE WATER behind the screen (play.py's unexplained change) and THE ANTENNAS poking out of it
    try:
        wpath = os.path.join(OUT, f"water_{game}_L1.npy")            # the first level's water when a level was won, else the run's
        if not os.path.exists(wpath): wpath = os.path.join(OUT, f"water_{game}.npy")
        if os.path.exists(wpath) and VIEW in ("all", "eyes"):
            water = np.load(wpath); wmax = max(1.0, float(water.max()))
            for y in range(H):
                for x in range(W):
                    if water[y, x] > 0:
                        a_ = min(0.75, water[y, x] / wmax)
                        px = img.getpixel((x * R + R // 2, y * R + R // 2))
                        col = tuple(int(c * (1 - a_) + b * a_) for c, b in zip(px, (40, 90, 200)))
                        d.rectangle([x * R + 1, y * R + 1, x * R + R - 2, y * R + R - 2], fill=col)
            apath = os.path.join(OUT, f"antennas_{game}_L1.json")
            if not os.path.exists(apath): apath = os.path.join(OUT, f"antennas_{game}.json")
            if os.path.exists(apath):
                loaded = json.load(open(apath)); loaded = loaded.get("antennas", []) if isinstance(loaded, dict) else loaded
                for i, a_ in enumerate(loaded[:5]):
                    try:
                        cy_, cx_ = a_["id"].split("@")[1].split(","); cy_, cx_ = int(cy_), int(cx_)
                        tip = (cx_ * R + R // 2, max(4, cy_ * R - 14 - 4 * i))
                        d.polygon([tip, (tip[0] - 5, tip[1] + 14), (tip[0] + 5, tip[1] + 14)], fill=(255, 230, 80), outline=(60, 40, 0))
                        d.text((tip[0] + 8, tip[1]), f"{a_['id']} {a_['antenna']:.0f}", fill=(255, 230, 80))
                    except Exception: pass
    except Exception: pass
    # THE FENCE: middle pins laid along the trail, borders bent (faint) or broken (red), the rule's far-away
    # predictions (dark red), the openings (cyan) where the chain of pins stops
    try:
        fpath = next((q for q in (os.path.join(OUT, f"fence_{game}_L1.npz"), os.path.join(OUT, f"fence_{game}.npz")) if os.path.exists(q)), None)
        if fpath and VIEW in ("all", "side", "front"):
            z = np.load(fpath); mid, border, pred = z["mid"], z["border"], z["pred"]
            dragged = z["dragged"] if "dragged" in z.files else np.zeros_like(border, dtype=bool)
            brushed = z["brushed"] if "brushed" in z.files else np.zeros_like(border)
            fallen = z["fallen"] if "fallen" in z.files else np.zeros((H, W), bool)
            for y, x in (np.argwhere(fallen) if VIEW != "front" else []):                     # a pin lying inside the wall pixel (the side eye's)
                d.line([x * R + 2, y * R + R - 3, x * R + R - 3, y * R + 2], fill=(90, 90, 110), width=1)
            DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for k, (dy, dx) in enumerate(DIRS):
                if VIEW == "front": break                                                          # the front eye looks down the standing pins: invisible
                for y, x in np.argwhere(mid[k] == 1):
                    cx, cy = x * R + R / 2, y * R + R / 2
                    d.line([cx - dx * 2.5, cy - dy * 2.5, cx + dx * 2.5, cy + dy * 2.5], fill=(235, 235, 235), width=1)
                    d.ellipse([cx + dx * 2.5 - 1, cy + dy * 2.5 - 1, cx + dx * 2.5 + 1, cy + dy * 2.5 + 1], fill=(235, 235, 235))
            def edge(y, x, k):
                x0, y0, x1, y1 = x * R, y * R, x * R + R, y * R + R
                return {0: [x0, y0, x1, y0], 1: [x0, y1 - 1, x1, y1 - 1], 2: [x0, y0, x0, y1], 3: [x1 - 1, y0, x1 - 1, y1]}[k]
            for k in range(4):
                for y, x in np.argwhere((pred[k] == -1) & (border[k] == 0)): d.line(edge(y, x, k), fill=(120, 20, 20), width=1)
                for y, x in np.argwhere(border[k] == -1): d.line(edge(y, x, k), fill=(255, 40, 40), width=2)
                for y, x in np.argwhere(dragged[k]): d.line(edge(y, x, k), fill=(255, 140, 40), width=2)          # dragged down along a wall
                unwalked = ~(mid == 1).any(axis=0); dy, dx = DIRS[k]
                for y, x in np.argwhere((brushed[k] == 1) & (border[k] == 0) & (pred[k] != -1)):
                    y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W and unwalked[y2, x2]: d.rectangle([x2 * R + 3, y2 * R + 3, x2 * R + R - 4, y2 * R + R - 4], outline=(0, 230, 255), width=1)
                for y, x in (np.argwhere((mid[k] == 1) & (border[k] == 0) & (pred[k] != -1)) if VIEW != "front" else []):
                    dy, dx = DIRS[k]; y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W: d.rectangle([x2 * R + 2, y2 * R + 2, x2 * R + R - 3, y2 * R + R - 3], outline=(0, 230, 255), width=1)
            d.text((6, H * R - 26), "fence: white ticks = pins laid by the body, red = broken borders, orange = dragged down along a wall,", fill=(235, 235, 235))
            d.text((6, H * R - 14), "dark red = the rule far away, cyan = openings (ahead of the trail, and branches to its side)", fill=(235, 235, 235))
    except Exception as e:
        print("fence layer skipped:", e)
    # arrows: for each cell, every button whose pins reach its colour (agree >= 0.5)
    vals, counts = np.unique(f, return_counts=True); floor = set(int(v) for v, c in zip(vals, counts) if c > 900)
    for (a, c), t in table.items():
        if VIEW not in ("all", "side"): break                                   # the controller's pins stand: the side eye's
        if t.get("bond", 0) < 0.5 or c in floor: continue                # a pin draws only while its bond holds
        vy, vx = t["vec"]; L = max(1.0, (vy * vy + vx * vx) ** 0.5); uy, ux = vy / L, vx / L
        cells = np.argwhere((f == c) & ~amb)
        for y, x in cells:
            cx, cy = x * R + R / 2, y * R + R / 2
            off = (a - 1) * 1.2 - 3                      # fan the buttons' arrows apart a little
            x0, y0 = cx - ux * 3 + (-uy) * off, cy - uy * 3 + ux * off
            x1, y1 = cx + ux * 3 + (-uy) * off, cy + uy * 3 + ux * off
            d.line([x0, y0, x1, y1], fill=ACT_COL[a], width=1)
            d.ellipse([x1 - 1.2, y1 - 1.2, x1 + 1.2, y1 + 1.2], fill=ACT_COL[a])
    # THE DIAGONAL PINS' FEET: a small magenta arrow inside the foot pointing at the back-wall coordinate (or at the body's
    # side, for a pin that slides with the body), and a magenta corner mark where it lands
    try:
        dpath = next((q for q in (os.path.join(OUT, f"diagonal_{game}_L1.json"), os.path.join(OUT, f"diagonal_{game}.json")) if os.path.exists(q)), None)
        if dpath and VIEW in ("all", "front", "eyes"):
            dj = json.load(open(dpath))
            for p in dj.get("pins", []):
                fy, fx = p["foot_centre"]; b = p["back"]; box = b["box"]
                if b["frame"] == "screen": ty, tx = (box[0] + box[1]) / 2, (box[2] + box[3]) / 2
                else: ty, tx = fy + (box[0] + box[1]) / 2, fx + (box[2] + box[3]) / 2
                vy, vx = ty - fy, tx - fx; L = max(1.0, (vy * vy + vx * vx) ** 0.5); uy, ux = vy / L, vx / L
                cx, cy = fx * R + R / 2, fy * R + R / 2
                d.line([cx, cy, cx + ux * 9, cy + uy * 9], fill=(255, 60, 220), width=2)
                d.polygon([(cx + ux * 12, cy + uy * 12), (cx + ux * 6 - uy * 4, cy + uy * 6 + ux * 4), (cx + ux * 6 + uy * 4, cy + uy * 6 - ux * 4)], fill=(255, 60, 220))
                if b["frame"] == "screen":
                    x0_, y0_, x1_, y1_ = box[2] * R, box[0] * R, (box[3] + 1) * R - 1, (box[1] + 1) * R - 1
                    for (ax, ay, sx, sy) in ((x0_, y0_, 1, 1), (x1_, y0_, -1, 1), (x0_, y1_, 1, -1), (x1_, y1_, -1, -1)):
                        d.line([ax, ay, ax + sx * 5, ay], fill=(255, 60, 220), width=2); d.line([ax, ay, ax, ay + sy * 5], fill=(255, 60, 220), width=2)
                e = p["eye"]; d.text((cx + 12, cy - 6), f"{p['effect']['target']} {e['fired_with']}/{e['fired_without']}", fill=(255, 60, 220))
    except Exception as e:
        print("diagonal layer skipped:", e)
    # THE METER'S PINS: laid (drained) pointing the way the front went, standing (bar), the end where the surround begins
    try:
        mpath = next((q for q in (os.path.join(OUT, f"meter_{game}_L1.json"),) if os.path.exists(q)), None)
        if mpath and VIEW in ("all", "eyes"):
            mj = json.load(open(mpath))
            if mj.get("pins") and mj.get("band") and mj.get("axis") == 1:
                (y0m, x0m), (y1m, x1m) = mj["band"]; cy = (y0m + y1m + 1) / 2 * R; sgn = 1 if mj.get("direction") == 1 else -1
                for x, pnn in enumerate(mj["pins"]):
                    cx = x * R + R / 2
                    if pnn == 0: d.line([cx - sgn * 3, cy, cx + sgn * 3, cy], fill=(255, 200, 60), width=1); d.ellipse([cx + sgn * 3 - 1, cy - 1, cx + sgn * 3 + 1, cy + 1], fill=(255, 200, 60))
                    elif pnn == 1: d.line([cx, cy - 3, cx, cy + 3], fill=(255, 240, 160), width=1)
                if mj.get("end") is not None:
                    ex = (mj["end"] + (1 if sgn == 1 else 0)) * R; d.line([ex, y0m * R - 2, ex, (y1m + 1) * R + 2], fill=(255, 80, 80), width=2)
                    d.text((ex + 3, y0m * R - 12), "the end", fill=(255, 80, 80))
    except Exception as e:
        print("meter layer skipped:", e)
    # the register's drift
    if reg:
        y0, y1, x0, x1 = reg["band"]; step = reg["cells_per_press"]
        d.rectangle([x0 * R, y0 * R, x1 * R - 1, y1 * R - 1], outline=(255, 200, 60))
        cy = (y0 + y1) / 2 * R
        for x in range(x0, x1, 4):
            cx = x * R + R / 2; s = -1 if step < 0 else 1
            d.line([cx, cy, cx + s * 5, cy], fill=(255, 200, 60), width=2); d.ellipse([cx + s * 5 - 1.5, cy - 1.5, cx + s * 5 + 1.5, cy + 1.5], fill=(255, 200, 60))
        d.text((x0 * R + 4, (y1 * R + 2) if y1 * R + 14 < H * R else y0 * R - 12), f"register: front moves {step:+.1f} cells/press", fill=(255, 200, 60))
    # the controller in the foreground, pins into the pixels each button moves
    top = H * R + 10
    for i, a in enumerate(range(1, 7)):
        bx = 20 + i * 100; by = top + 30
        d.rounded_rectangle([bx, by, bx + 80, by + 44], radius=8, fill=(40, 40, 48), outline=ACT_COL[a], width=2)
        d.text((bx + 8, by + 6), ACT_NAME[a], fill=ACT_COL[a])
        n = out["moved_cells_per_action"].get(a, 0); d.text((bx + 8, by + 24), f"moves {n} px", fill=(200, 200, 200))
        m = moved_ever[a] > 0
        if m.any():
            lab, k = ndimage.label(m)
            for j in range(1, k + 1):
                ys, xs = np.where(lab == j)
                if len(ys) < 3: continue
                d.line([bx + 40, by, xs.mean() * R + R / 2, ys.mean() * R + R / 2], fill=ACT_COL[a] + (0,), width=1)
                d.ellipse([xs.mean() * R + R / 2 - 3, ys.mean() * R + R / 2 - 3, xs.mean() * R + R / 2 + 3, ys.mean() * R + R / 2 + 3], outline=ACT_COL[a])
    # legend: the pins table
    lx = W * R + 16; ly = 12
    d.text((lx, ly), f"{game}: pins (button -> colour: vector, obeyed, bond)", fill=(230, 230, 230)); ly += 18
    for (a, c), t in sorted(table.items(), key=lambda kv: -kv[1].get("bond", 0)):
        if t["n"] < 3: continue
        held = t.get("bond", 0) >= 0.5
        d.rectangle([lx, ly + 3, lx + 10, ly + 13], fill=PAL[c % 16])
        d.text((lx + 16, ly), f"{ACT_NAME[a]:8s} colour {c:2d}: ({t['vec'][0]:+d},{t['vec'][1]:+d})  {t['agree']:.0%} of {t['n']}  bond {t.get('bond', 0):.2f}{' held' if held else ' broken'}",
               fill=ACT_COL[a] if held else (120, 120, 130)); ly += 15
    ly += 8; d.text((lx, ly), f"surprise layer: max {smax} presses at one pixel (red)", fill=(255, 120, 120)); ly += 15
    d.text((lx, ly), f"{len(pairs)} presses recorded", fill=(160, 160, 160))
    p = os.path.join(OUT, f"flow_{game}{'' if VIEW == 'all' else '_' + VIEW}.png"); img.save(p); return p


if __name__ == "__main__":
    if "--view" in sys.argv:
        VIEW = sys.argv[sys.argv.index("--view") + 1]; sys.argv = [a for i, a in enumerate(sys.argv) if a != "--view" and (i == 0 or sys.argv[i - 1] != "--view")]
    games = (sys.argv[1] if len(sys.argv) > 1 else "sp80").split(",")
    for gname in games:
        b = build(gname)
        if b is None: print(gname, "no data"); continue
        p = render(gname, *b)
        out = b[-1]
        print(f"{gname}: {out['presses']} presses; register {out['register']}; pins:")
        for r in out["pins"]:
            if r["n"] >= 3: print(f"   {ACT_NAME[r['action']]:8s} colour {r['colour']:2d} -> ({r['vec'][0]:+d},{r['vec'][1]:+d}) obeyed {r['agree']:.0%} of {r['n']} px")
        print("   ->", p)
