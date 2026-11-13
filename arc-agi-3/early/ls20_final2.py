"""LS20 room-aware solver — the teacher's hints wired in (Jonathan as the tangency post):
match the HUD image to the goal (his rule), the batch rotates it (side-dialed, adaptive),
refill when lowest (visit the ring before the long leg), rooms connected by transitions.
Route: L1 anchor -> L2 room1 -> transition (17,16) -> room2: rotate at keyhole (read k after
EVERY entry, adapt), refill at the ring when low, insert at the room-2 box. Bar logged at
every waypoint; every frame recorded."""
import json, os, sys
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, "/home/claude/rh_voidline")
from arc3_client import api, frame_np

HUD = 56
ACTS = {"ACTION1": (-5,0), "ACTION2": (5,0), "ACTION3": (0,-5), "ACTION4": (0,5)}
OPP = {"ACTION1": "ACTION2", "ACTION2": "ACTION1", "ACTION3": "ACTION4", "ACTION4": "ACTION3"}
key = os.environ["ARC_API_KEY"]
games = api("/api/games", key)
gid = next(g["game_id"] for g in games if g["game_id"].startswith("ls20"))
card_id = api("/api/scorecard/open", key, {"tags": ["room-final"]}).get("card_id")
guid = {}; n_act = 0
frames = []
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
def s11(f):
    cells = set()
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: cells |= {(int(y), int(x)) for y, x in zip(ys, xs)}
    return cells
PASS = {0, 1, 3, 9, 12}
def passable(f, p, s11set):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    for dy in range(5):
        for dx in range(5):
            v = int(f[y-2+dy, x-2+dx])
            if v in PASS or (v == 11 and (y-2+dy, x-2+dx) in s11set): continue
            return False
    return True
def goto(f, fr, want, near=0, cap=30):
    s = s11(f)
    for _ in range(cap):
        pos = agent_pos(f)
        if pos is None: return f, fr, False
        if abs(pos[0]-want[0]) + abs(pos[1]-want[1]) <= near: return f, fr, True
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
        if fr["state"] in ("WIN", "GAME_OVER") or fr.get("levels_completed", 0) > LVL[0]:
            return f, fr, True
        s = s11(f)     # layout may change (transition) — re-read
    return f, fr, False
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None

LVL = [0]
fr, f = send("RESET")
def leveled(fr):
    nl = fr.get("levels_completed", 0)
    if nl > LVL[0]:
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act)); LVL[0] = nl; return True
    return False

# ---- Level 1: the anchor ----
G, box = goal_box(f); kh = keyhole(f)
f, fr, _ = goto(f, fr, kh, 0)
leveled(fr)
if LVL[0] == 0:
    f, fr, _ = goto(f, fr, (box[0]+10, box[1]), 2)
    for _ in range(3):
        fr, f = send("ACTION1")
        if leveled(fr): break
print("[L1 done] actions %d, bar %d" % (n_act, bar_px(f)))

# ---- Level 2 ----
if LVL[0] == 1 and fr["state"] not in ("WIN", "GAME_OVER"):
    print("[L2 room1] bar %d — to the transition" % bar_px(f))
    f, fr, ok = goto(f, fr, (17, 16), 0, cap=25)
    print("[transition] actions %d bar %d" % (n_act, bar_px(f)))
    # burn to respawn: the respawn is a free teleport to (42,31) INSIDE room 2, fresh bar
    resp = False
    for _ in range(40):
        p0 = agent_pos(f)
        fr, f = send("ACTION2")
        p1 = agent_pos(f)
        if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): break
        if p0 and p1 and abs(p1[0]-p0[0]) + abs(p1[1]-p0[1]) > 12: resp = True; break
        fr, f = send("ACTION1")
        p2 = agent_pos(f)
        if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): break
        if p1 and p2 and abs(p2[0]-p1[0]) + abs(p2[1]-p1[1]) > 12: resp = True; break
    print("[respawn teleport] resp=%s pos %s bar %d actions %d" % (resp, agent_pos(f), bar_px(f), n_act))
    def bfs_len(f, pos, want):
        s = s11(f)
        q = deque([(pos, 0)]); seen = {pos}
        while q:
            p, d0 = q.popleft()
            if p == want: return d0
            for a, dv in ACTS.items():
                np_ = (p[0]+dv[0], p[1]+dv[1])
                if np_ not in seen and passable(f, np_, s):
                    seen.add(np_); q.append((np_, d0+1))
        return None

    for life in range(3):
        if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: break
        G2, box2 = goal_box(f); kh2 = keyhole(f)
        k = match_rot(hud_glyph(f), G2) if G2 is not None else None
        pos = agent_pos(f)
        print("[life %d] pos %s bar %d k=%s box %s" % (life, pos, bar_px(f), k, box2))
        if k is None or kh2 is None or box2 is None: break
        # rotation: walk to the CHEAPEST reachable entry cell, then adaptive enter/off/on
        tries = 0
        while k != 0 and tries < 5 and fr["state"] not in ("WIN","GAME_OVER"):
            cands = []
            for a, dv in ACTS.items():
                adj = (kh2[0]-dv[0], kh2[1]-dv[1])
                L_ = bfs_len(f, agent_pos(f), adj)
                if L_ is not None: cands.append((L_, a, adj))
            if not cands: break
            _, a, adj = min(cands)
            f, fr, ok2 = goto(f, fr, adj, 0, cap=12)
            if not ok2: break
            fr, f = send(a)
            if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): break
            k_new = match_rot(hud_glyph(f), G2)
            print("  entry %s: k %s -> %s  bar %d" % (a, k, k_new, bar_px(f)))
            k = k_new
            if k != 0:
                fr, f = send(OPP[a])
                if leveled(fr): break
            tries += 1
        if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: break
        if k == 0:
            # straight race to the box: approach from the RIGHT, push LEFT
            f, fr, okb = goto(f, fr, (box2[0], box2[1]+10), 2, cap=18)
            print("[race] pos %s bar %d k=%s" % (agent_pos(f), bar_px(f), match_rot(hud_glyph(f), G2)))
            for _ in range(5):
                if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 2: break
                p2 = agent_pos(f)
                if p2 is None: break
                if match_rot(hud_glyph(f), G2) != 0: break     # died mid-race, key reset
                dy, dx = box2[0]-p2[0], box2[1]-p2[1]
                a = ("ACTION3" if dx < 0 else "ACTION4") if abs(dx) >= abs(dy) else ("ACTION1" if dy < 0 else "ACTION2")
                fr, f = send(a)
                if leveled(fr): break
            print("[insert] pos %s bar %d level %d" % (agent_pos(f), bar_px(f), LVL[0]))
        # if we died anywhere above, the loop retries with the fresh life (room persists)

print("\nfinal: state=%s levels=%d actions=%d" % (fr["state"], fr.get("levels_completed", 0), n_act))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:500])
np.savez_compressed("/home/claude/rh_voidline/room_solver_frames.npz",
                    F=np.array(frames, dtype=np.int8))
print("saved room_solver_frames.npz (%d frames)" % len(frames))
