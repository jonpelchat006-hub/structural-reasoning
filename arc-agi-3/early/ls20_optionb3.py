"""LS20 L2 — Jonathan's exact sequence (the teacher's full instruction):
refill #1 right away (the nook by spawn) -> rotate 3 times (down-entries, +1 each)
-> refill #2 just before the end (17,16 — it opens the endgame) -> insert at the box.
Pips = lives. Bar logged everywhere; nook entered by free blocked pushes if needed."""
import json, os, sys
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, "/home/claude/rh_voidline")
from arc3_client import api, frame_np

HUD = 56
ACTS = {"ACTION1": (-5,0), "ACTION2": (5,0), "ACTION3": (0,-5), "ACTION4": (0,5)}
key = os.environ["ARC_API_KEY"]
games = api("/api/games", key)
gid = next(g["game_id"] for g in games if g["game_id"].startswith("ls20"))
card_id = api("/api/scorecard/open", key, {"tags": ["option-b3"]}).get("card_id")
guid = {}; n_act = 0; frames = []
def send(a):
    global n_act
    fr = api(f"/api/cmd/{a}", key, {"game_id": gid, "card_id": card_id, "guid": guid.get("v")})
    guid["v"] = fr["guid"]
    if a != "RESET": n_act += 1
    f = frame_np(fr)
    frames.append(f)
    return fr, f
def crop(m):
    ys, xs = np.where(m)
    return m[ys.min():ys.max()+1, xs.min():xs.max()+1] if len(ys) else m
def shrink(m):
    m = crop(m)
    for s in (3, 2):
        if m.size and m.shape[0] % s == 0 and m.shape[1] % s == 0:
            t = m.reshape(m.shape[0]//s, s, m.shape[1]//s, s).mean(axis=(1,3))
            if ((t == 0) | (t == 1)).all(): return t.astype(int)
    return m.astype(int)
def hud_glyph(f): return shrink(f[54:64, 0:14] == 9)
def goal_box(f):
    lab, n = ndimage.label(f[:52] == 5)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) < 16: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        inner = f[y0+1:y1, x0+1:x1]
        if inner.size and (inner == 9).any():
            return shrink(inner == 9), (int((y0+y1)//2), int((x0+x1)//2))
    return None, None
def keyhole(f):
    m = np.isin(f[:52], [0, 1])
    if not m.any(): return None
    ys, xs = np.where(m)
    return (int(round(ys.mean())), int(round(xs.mean())))
def rings(f):
    out = []
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return out
def agent_pos(f):
    lab, n = ndimage.label(np.isin(f[:HUD], [9, 12]))
    for i in range(1, n+1):
        yy, xx = np.where(lab == i)
        if (f[yy, xx] == 12).any(): return (int(round(yy.mean())), int(round(xx.mean())))
    return None
def bar_px(f): return int((f[56:] == 11).sum())
def s11set(f):
    cells = set()
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: cells |= {(int(y), int(x)) for y, x in zip(ys, xs)}
    return cells
PASS = {0, 1, 3, 9, 12}
def passable(f, p, s):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    for dy in range(5):
        for dx in range(5):
            v = int(f[y-2+dy, x-2+dx])
            if v in PASS or (v == 11 and (y-2+dy, x-2+dx) in s): continue
            return False
    return True
LVL = [0]
def leveled(fr):
    nl = fr.get("levels_completed", 0)
    if nl > LVL[0]:
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act)); LVL[0] = nl; return True
    return False
def goto(f, fr, want, near=0, cap=30):
    for _ in range(cap):
        pos = agent_pos(f)
        if pos is None: return f, fr, False
        if abs(pos[0]-want[0]) + abs(pos[1]-want[1]) <= near: return f, fr, True
        s = s11set(f)
        q = deque([(pos, [])]); seen = {pos}; path = None
        while q:
            p, pth = q.popleft()
            if abs(p[0]-want[0]) + abs(p[1]-want[1]) <= near: path = pth; break
            for a, dv in ACTS.items():
                np_ = (p[0]+dv[0], p[1]+dv[1])
                if np_ not in seen and passable(f, np_, s):
                    seen.add(np_); q.append((np_, pth + [a]))
        if not path: return f, fr, False
        fr, f = send(path[0])
        if leveled(fr) or fr["state"] in ("WIN", "GAME_OVER"): return f, fr, True
    return f, fr, False
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None
def collect_ring(f, fr, ring):
    """storm the ring from every reachable launch point; blocked pushes are free;
       success = bar jump upward"""
    b0 = bar_px(f)
    # SNAP the ring to the agent's 5-px lattice (parity!): the standable cell
    p = agent_pos(f)
    ry = ring[0] + ((p[0] - ring[0]) % 5 if (p[0] - ring[0]) % 5 <= 2 else (p[0] - ring[0]) % 5 - 5)
    rx = ring[1] + ((p[1] - ring[1]) % 5 if (p[1] - ring[1]) % 5 <= 2 else (p[1] - ring[1]) % 5 - 5)
    snapped = (ry, rx)
    f, fr, ok = goto(f, fr, snapped, 0, cap=12)
    if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: return f, fr, False
    if ok and bar_px(f) > b0 + 8:
        print("  [REFILL collected at %s] bar %d -> %d" % (str(snapped), b0, bar_px(f)))
        return f, fr, True
    if ok:
        # stand on it a beat: step off and back on
        fr, f = send("ACTION3"); fr, f = send("ACTION4")
        if bar_px(f) > b0 + 8:
            print("  [REFILL collected at %s] bar %d -> %d" % (str(snapped), b0, bar_px(f)))
            return f, fr, True
    cands = []
    for dy, dx in [(-5,0),(5,0),(0,-5),(0,5),(-10,0),(10,0),(0,-10),(0,10),
                   (5,5),(5,-5),(-5,5),(-5,-5)]:
        launch = (snapped[0]+dy, snapped[1]+dx)
        cands.append(launch)
    for launch in cands:
        f, fr, ok = goto(f, fr, launch, 0, cap=8)
        if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: return f, fr, False
        if not ok: continue
        # push toward the ring center up to 3 times
        for _ in range(3):
            p = agent_pos(f)
            if p is None: break
            dyy, dxx = ring[0]-p[0], ring[1]-p[1]
            if abs(dyy) + abs(dxx) == 0: break
            a = ("ACTION1" if dyy < 0 else "ACTION2") if abs(dyy) >= abs(dxx) \
                else ("ACTION3" if dxx < 0 else "ACTION4")
            fr, f = send(a)
            if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): return f, fr, False
            if bar_px(f) > b0 + 8:
                print("  [REFILL collected at %s] bar %d -> %d" % (str(ring), b0, bar_px(f)))
                return f, fr, True
            b0 = min(b0, bar_px(f))
    return f, fr, False

fr, f = send("RESET")
# --- L1 anchor ---
G, box = goal_box(f); kh = keyhole(f)
f, fr, _ = goto(f, fr, kh, 0)
if LVL[0] == 0:
    f, fr, _ = goto(f, fr, (box[0]+10, box[1]), 2)
    for _ in range(3):
        fr, f = send("ACTION1")
        if leveled(fr): break
print("[L1] actions %d bar %d" % (n_act, bar_px(f)))

# --- L2: Jonathan's Option B: 1 rotation -> refill1 (nook, low bar) -> 2 rotations
#     -> trek -> refill2 just before the end -> insert ---
if LVL[0] == 1 and fr["state"] not in ("WIN", "GAME_OVER"):
    G2, box2 = goal_box(f); kh2 = keyhole(f)
    rg = rings(f)
    print("[L2 start] bar %d rings %s keyhole %s box %s k=%s"
          % (bar_px(f), rg, kh2, box2, match_rot(hud_glyph(f), G2)))
    nook = min(rg, key=lambda r: abs(r[0]-47) + abs(r[1]-41))     # (51,41) by the keyhole
    endring = min(rg, key=lambda r: abs(r[0]-17) + abs(r[1]-16))  # (17,16) endgame ring
    # STEP 1: trek to above-keyhole, one down-entry
    f, fr, ok = goto(f, fr, (kh2[0]-5, kh2[1]), 0, cap=20)
    k = match_rot(hud_glyph(f), G2)
    fr, f = send("ACTION2")
    k = match_rot(hud_glyph(f), G2)
    print("[entry 1] k=%s bar %d actions %d" % (k, bar_px(f), n_act))
    # STEP 2: refill1 at the nook, NOW that the bar is low
    f, fr, got1 = collect_ring(f, fr, nook)
    print("[refill1] collected=%s bar %d actions %d" % (got1, bar_px(f), n_act))
    # STEP 3: two more down-entries
    entries = 0
    while k not in (0, None) and entries < 4 and fr["state"] not in ("WIN","GAME_OVER"):
        f, fr, ok = goto(f, fr, (kh2[0]-5, kh2[1]), 0, cap=12)
        if not ok: break
        fr, f = send("ACTION2")
        if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): break
        k = match_rot(hud_glyph(f), G2)
        print("[entry] k=%s bar %d" % (k, bar_px(f)))
        entries += 1
        if k != 0:
            fr, f = send("ACTION1")
            if leveled(fr): break
    print("[rotated] k=%s bar %d actions %d" % (k, bar_px(f), n_act))
    # STEP 4: trek to the endgame ring; collect just before empty
    if k == 0 and fr["state"] not in ("WIN","GAME_OVER") and LVL[0] == 1:
        f, fr, got2 = collect_ring(f, fr, endring)
        kchk = match_rot(hud_glyph(f), goal_box(f)[0])
        print("[refill2] collected=%s bar %d k=%s actions %d" % (got2, bar_px(f), kchk, n_act))
        # STEP 5: the end — box from above, push down
        G2, box2 = goal_box(f)
        if box2 and kchk == 0:
            f, fr, _ = goto(f, fr, (box2[0]-10, box2[1]), 2, cap=12)
            print("[pre-insert] pos %s bar %d" % (agent_pos(f), bar_px(f)))
            for _ in range(4):
                if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: break
                fr, f = send("ACTION2")
                if leveled(fr): break
            print("[insert done] pos %s bar %d level %d" % (agent_pos(f), bar_px(f), LVL[0]))

print("\nfinal: state=%s levels=%d actions=%d" % (fr["state"], fr.get("levels_completed", 0), n_act))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:400])
np.savez_compressed("/home/claude/rh_voidline/hint_frames.npz", F=np.array(frames, dtype=np.int8))
print("saved hint_frames.npz (%d frames)" % len(frames))
