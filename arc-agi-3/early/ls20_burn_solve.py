"""LS20 level-2 burn-solve — Jonathan's fuel law as the solution:
"refill when it's lowest; get near the subgoal and burn the budget so the refill does more."
Hypothesis: the bar-empty respawn applies +1 rotation (observed k: 0->1 twice).
Plan: L1 anchor solve; L2: keyhole -> set k=3 (2 extra entries), BURN real moves to force
the respawn (k=3 +1 = 0, fresh full bar at spawn), then direct spawn->box->insert (18 <= 22).
Either way we MEASURE k after a controlled respawn (die at k=2: reset->1 vs +1->3)."""
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
card_id = api("/api/scorecard/open", key, {"tags": ["burn-solve"]}).get("card_id")
guid = {}; n_act = 0
def send(a):
    global n_act
    fr = api(f"/api/cmd/{a}", key, {"game_id": gid, "card_id": card_id, "guid": guid.get("v")})
    guid["v"] = fr["guid"]
    if a != "RESET": n_act += 1
    return fr
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
PASS = {0, 1, 3, 9, 12}
def passable(f, p):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    return bool(np.isin(f[y-2:y+3, x-2:x+3], list(PASS)).all())
def bfs_path(f, pos, want, near=2):
    q = deque([(pos, [])]); seen = {pos}
    best, bp = pos, []
    bd = abs(pos[0]-want[0]) + abs(pos[1]-want[1])
    while q:
        p, pth = q.popleft()
        d = abs(p[0]-want[0]) + abs(p[1]-want[1])
        if d < bd: best, bp, bd = p, pth, d
        if d <= near: return pth
        for a, dv in ACTS.items():
            np_ = (p[0]+dv[0], p[1]+dv[1])
            if np_ not in seen and passable(f, np_):
                seen.add(np_); q.append((np_, pth + [a]))
    return bp
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None

fr = send("RESET"); f = frame_np(fr)
lvl = 0
def step(a):
    global f, fr, lvl
    p0 = agent_pos(f)
    fr = send(a); f = frame_np(fr)
    nl = fr.get("levels_completed", 0)
    lev = nl > lvl or fr["state"] == "WIN"
    if lev:
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act)); lvl = nl
    p1 = agent_pos(f)
    resp = p0 and p1 and abs(p1[0]-p0[0]) + abs(p1[1]-p0[1]) > 12
    return lev, resp

# ---- level 1: the anchor ----
G, box = goal_box(f); kh = keyhole(f)
for a in bfs_path(f, agent_pos(f), kh, near=0):
    lv, _ = step(a)
    if lv: break
if lvl == 0:
    for a in bfs_path(f, agent_pos(f), box, near=12) + ["ACTION1"]*3:
        lv, _ = step(a)
        if lv: break
print("after L1: level", lvl, "actions", n_act)

# ---- level 2: burn-solve ----
if lvl == 1 and fr["state"] not in ("WIN", "GAME_OVER"):
    G, box = goal_box(f); kh = keyhole(f)
    print("L2: keyhole", kh, "box", box, "k =", match_rot(hud_glyph(f), G))
    # 1) go to keyhole (entry: k 1->2), then one off/on (k->3)
    for a in bfs_path(f, agent_pos(f), kh, near=0):
        lv, resp = step(a)
        if lv or resp or fr["state"] in ("WIN","GAME_OVER"): break
    print("  at keyhole: k =", match_rot(hud_glyph(f), G))
    step("ACTION1"); step("ACTION2")     # off and back on = +1
    k_now = match_rot(hud_glyph(f), G)
    print("  after off/on: k =", k_now, "(want 3)")
    # 2) BURN: shuttle real moves until the respawn fires
    resp = False
    burn = 0
    while not resp and burn < 30 and fr["state"] not in ("WIN", "GAME_OVER"):
        for a in ["ACTION1", "ACTION2"]:
            lv, resp = step(a); burn += 1
            if resp or lv or fr["state"] in ("WIN","GAME_OVER"): break
    k_after = match_rot(hud_glyph(f), G)
    print("  RESPAWN after %d burn moves: k = %s  (reset->1 vs +1-rule->0)" % (burn, k_after))
    # 3) if k == 0: the fresh full bar carries the direct insert
    if k_after == 0 and fr["state"] not in ("WIN", "GAME_OVER"):
        for a in bfs_path(f, agent_pos(f), box, near=12):
            lv, resp = step(a)
            if lv or resp or fr["state"] in ("WIN","GAME_OVER"): break
        for _ in range(4):
            if fr["state"] in ("WIN","GAME_OVER") or lvl >= 2: break
            p2 = agent_pos(f)
            dy, dx = box[0]-p2[0], box[1]-p2[1]
            if abs(dy)+abs(dx) <= 2: break
            push = ("ACTION1" if dy < 0 else "ACTION2") if abs(dy) >= abs(dx) else ("ACTION3" if dx < 0 else "ACTION4")
            lv, _ = step(push)
            if lv: break

print("\nfinal: state=%s levels=%d actions=%d" % (fr["state"], fr.get("levels_completed", 0), n_act))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:400])
