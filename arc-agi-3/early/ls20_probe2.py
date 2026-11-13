"""LS20 level-2 instrumented probe — measure everything, solve from the data.
Segments: (1) L1 anchor solve; (2) stand on ring2, read BAR + FIELD before/after;
(3) keyhole entries from two different sides, rotation delta per side;
(4) burn to respawn, diff the field across it (what persists?).
Every frame recorded to l2_probe_frames.npz."""
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
card_id = api("/api/scorecard/open", key, {"tags": ["l2-probe"]}).get("card_id")
guid = {}; n_act = 0
frames, marks = [], []
def send(a, mark=""):
    global n_act
    fr = api(f"/api/cmd/{a}", key, {"game_id": gid, "card_id": card_id, "guid": guid.get("v")})
    guid["v"] = fr["guid"]
    if a != "RESET": n_act += 1
    f = frame_np(fr)
    frames.append(f); marks.append("%d:%s:%s" % (n_act, a, mark))
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
def agent_pos(f):
    lab, n = ndimage.label(np.isin(f[:HUD], [9, 12]))
    for i in range(1, n+1):
        yy, xx = np.where(lab == i)
        if (f[yy, xx] == 12).any(): return (int(round(yy.mean())), int(round(xx.mean())))
    return None
def bar_px(f): return int((f[56:] == 11).sum())
S11 = set()
def refresh_s11(f):
    S11.clear()
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: S11.update({(int(y), int(x)) for y, x in zip(ys, xs)})
PASS = {0, 1, 3, 9, 12}
def passable(f, p):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    for dy in range(5):
        for dx in range(5):
            v = int(f[y-2+dy, x-2+dx])
            if v in PASS or (v == 11 and (y-2+dy, x-2+dx) in S11): continue
            return False
    return True
def goto(f, fr, want, near=0, cap=30, mark=""):
    for _ in range(cap):
        pos = agent_pos(f)
        if pos is None: return f, fr
        if abs(pos[0]-want[0]) + abs(pos[1]-want[1]) <= near: return f, fr
        q = deque([(pos, [])]); seen = {pos}; path = None
        while q:
            p, pth = q.popleft()
            if abs(p[0]-want[0]) + abs(p[1]-want[1]) <= near: path = pth; break
            for a, dv in ACTS.items():
                np_ = (p[0]+dv[0], p[1]+dv[1])
                if np_ not in seen and passable(f, np_):
                    seen.add(np_); q.append((np_, pth + [a]))
        if not path: return f, fr
        fr, f = send(path[0], mark)
        if fr["state"] in ("WIN", "GAME_OVER"): return f, fr
    return f, fr
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None

fr, f = send("RESET", "start")
refresh_s11(f)
# --- seg 1: L1 anchor ---
G, box = goal_box(f); kh = keyhole(f)
f, fr = goto(f, fr, kh, 0, mark="L1-key")
f, fr = goto(f, fr, (box[0]+10, box[1]), 2, mark="L1-box")
for _ in range(3):
    fr, f = send("ACTION1", "L1-insert")
    if fr.get("levels_completed", 0) >= 1: break
print("L1 done at", n_act, "level:", fr.get("levels_completed"))
refresh_s11(f)
G, box = goal_box(f); kh = keyhole(f)
ring2 = (17, 16)
print("L2: keyhole", kh, "box", box, "k =", match_rot(hud_glyph(f), G), "bar =", bar_px(f))

# --- seg 2: stand on ring2; bar + field before/after ---
f_before = f.copy(); b_before = bar_px(f)
f, fr = goto(f, fr, ring2, 0, mark="to-ring2")
b_on = bar_px(f)
field_diff = int((f[:52] != f_before[:52]).sum())
print("RING2: bar %d -> %d (delta %+d) | field pixels changed since before: %d"
      % (b_before, b_on, b_on - b_before, field_diff))
# step off and back on: re-usable?
fr, f = send("ACTION2", "ring-off"); fr, f = send("ACTION1", "ring-on")
print("  re-enter: bar =", bar_px(f))

# --- seg 3: keyhole entries from two sides ---
k0 = match_rot(hud_glyph(f), G)
f, fr = goto(f, fr, (kh[0], kh[1]-5), 0, cap=30, mark="left-of-key")
fr, f = send("ACTION4", "enter-from-left")
k1 = match_rot(hud_glyph(f), G)
fr, f = send("ACTION3", "exit-left")
f, fr = goto(f, fr, (kh[0]-5, kh[1]), 0, cap=10, mark="above-key")
fr, f = send("ACTION2", "enter-from-top")
k2 = match_rot(hud_glyph(f), G)
print("KEYHOLE sides: k %s -> after LEFT entry %s -> after TOP entry %s" % (k0, k1, k2))

# --- seg 4: burn to respawn; field persistence ---
f_pre = f.copy()
resp = False
for _ in range(30):
    p0 = agent_pos(f)
    fr, f = send("ACTION1", "burn"); fr2 = fr
    p1 = agent_pos(f)
    if p0 and p1 and abs(p1[0]-p0[0]) + abs(p1[1]-p0[1]) > 12: resp = True; break
    fr, f = send("ACTION2", "burn")
    p2 = agent_pos(f)
    if p1 and p2 and abs(p2[0]-p1[0]) + abs(p2[1]-p1[1]) > 12: resp = True; break
    if fr["state"] in ("WIN", "GAME_OVER"): break
if resp:
    pers = (f[:52] != f_pre[:52])
    # exclude agent areas
    am = np.isin(f[:52], [9, 12]) | np.isin(f_pre[:52], [9, 12])
    pers = pers & ~am
    ys, xs = np.where(pers)
    print("RESPAWN: %d non-agent field pixels differ from pre-respawn" % len(ys))
    if len(ys): print("  at rows", sorted(set(ys.tolist()))[:10])
    print("  k after respawn:", match_rot(hud_glyph(f), G), " bar:", bar_px(f))
print("\nfinal: state=%s levels=%s actions=%d" % (fr["state"], fr.get("levels_completed"), n_act))
api("/api/scorecard/close", key, {"card_id": card_id})
np.savez_compressed("/home/claude/rh_voidline/l2_probe_frames.npz",
                    F=np.array(frames, dtype=np.int8), marks=np.array(marks))
print("saved l2_probe_frames.npz (%d frames)" % len(frames))
