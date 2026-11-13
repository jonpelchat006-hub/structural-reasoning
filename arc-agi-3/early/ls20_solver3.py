"""LS20 solver v2 — Jonathan's rule + match-protection + door detection + insertion.
Loop per level: read key (HUD) / goal (in-field box) / rotators; rotate by stepping
off+on the rotator ((4-k)%4 entries); once matched, NEVER cross a rotator again
(protected BFS); watch the field for door changes; drive into the goal box; repeat."""
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
card_id = api("/api/scorecard/open", key, {"tags": ["ls20-solver-v3"]}).get("card_id")
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
def bfs(f, pos, want, avoid=set(), near=1):
    q = deque([(pos, [])]); seen = {pos}
    best, bd, bpath = pos, abs(pos[0]-want[0])+abs(pos[1]-want[1]), []
    while q:
        p, pth = q.popleft()
        d = abs(p[0]-want[0]) + abs(p[1]-want[1])
        if d < bd: best, bd, bpath = p, d, pth
        if d <= near: return pth, True
        for a, dv in ACTS.items():
            np_ = (p[0]+dv[0], p[1]+dv[1])
            if np_ in seen or not passable(f, np_): continue
            if any(abs(np_[0]-r[0]) + abs(np_[1]-r[1]) <= 3 for r in avoid): continue
            seen.add(np_); q.append((np_, pth + [a]))
    return bpath, False
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None

fr = send("RESET"); f = frame_np(fr)
lvl = fr.get("levels_completed", 0)
rotators = set()
completions = []
print("start: level", lvl, "of", fr.get("win_levels"))

def step(a):
    """send one action; returns (leveled, rotated)"""
    global f, fr, lvl
    H0 = hud_glyph(f)
    p0 = agent_pos(f)
    fr = send(a); f2 = frame_np(fr)
    nl = fr.get("levels_completed", 0)
    if nl > lvl or fr["state"] == "WIN":
        completions.append(dict(level=nl, actions=n_act))
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act))
        lvl = nl; f = f2; return True, False
    H1 = hud_glyph(f2)
    rot = (H1.shape != H0.shape) or not (H1 == H0).all()
    if rot:
        rp = agent_pos(f2)
        if rp: rotators.add(rp)
    f = f2
    return False, rot

while n_act < 160 and fr["state"] not in ("WIN", "GAME_OVER"):
    H = hud_glyph(f); G, box_c = goal_box(f)
    kh = keyhole(f); pos = agent_pos(f)
    if G is None or pos is None:
        print("perception incomplete at action", n_act); break
    k = match_rot(H, G)
    rots = set(rotators) | ({kh} if kh else set())
    print(f"[{n_act}] rot_needed={k} pos={pos} keyhole={kh} rotators={sorted(rots)}")
    if k is None:
        print("  patterns unrelated — stopping"); break
    if k != 0:
        entries = (4 - k) % 4
        # go stand adjacent to a rotator, then step on/off
        target = kh or next(iter(rotators), None)
        if target is None: print("  no rotator known"); break
        path, ok = bfs(f, pos, target, near=1)
        done_lv = False
        for a in path:
            done_lv, _ = step(a)
            if done_lv or fr["state"] in ("WIN", "GAME_OVER"): break
        if done_lv or fr["state"] in ("WIN", "GAME_OVER"): continue
        # on the rotator now (entry counted as 1 rotation); do remaining off/on cycles
        cur_k = match_rot(hud_glyph(f), G)
        tries = 0
        while cur_k != 0 and tries < 8 and fr["state"] not in ("WIN", "GAME_OVER"):
            for pair in [("ACTION1","ACTION2"), ("ACTION3","ACTION4"), ("ACTION2","ACTION1"), ("ACTION4","ACTION3")]:
                lv1, _ = step(pair[0])
                if lv1 or fr["state"] in ("WIN","GAME_OVER"): break
                lv2, rot2 = step(pair[1])
                if lv2 or fr["state"] in ("WIN","GAME_OVER") or rot2: break
            cur_k = match_rot(hud_glyph(f), G)
            tries += 1
        continue
    # matched: protect the match; drive INTO the goal box (or as close as possible)
    print("  MATCHED — driving to insert at goal box", box_c, "avoiding rotators")
    path, reached = bfs(f, pos, box_c, avoid=rots, near=2)
    if not path:
        print("  no protected progress toward box; trying box-adjacent points")
        adj = [(box_c[0]+dy, box_c[1]+dx) for dy, dx in [(-6,0),(6,0),(0,-6),(0,6),(9,0)]]
        moved = False
        for t in adj:
            path, _ = bfs(f, pos, t, avoid=rots, near=1)
            if path: moved = True; break
        if not moved:
            print("  nothing reachable while protected — stopping"); break
    done_lv = False
    for a in path:
        done_lv, rot = step(a)
        if done_lv or rot or fr["state"] in ("WIN", "GAME_OVER"): break
    if done_lv or fr["state"] in ("WIN", "GAME_OVER"): continue
    # INSERT: push toward the box (its center relative to us tells the direction)
    pos2 = agent_pos(f)
    if pos2:
        dy, dx = box_c[0]-pos2[0], box_c[1]-pos2[1]
        push = ("ACTION1" if dy < 0 else "ACTION2") if abs(dy) >= abs(dx) else ("ACTION3" if dx < 0 else "ACTION4")
        print("  INSERT push", push, "from", pos2, "toward", box_c)
        for _ in range(3):
            done_lv, rot = step(push)
            if done_lv or rot or fr["state"] in ("WIN", "GAME_OVER"): break
        if done_lv: continue
        pos3 = agent_pos(f)
        if pos3 == pos2 and pos2 == pos:
            print("  fully stuck at", pos3, "— dumping and stopping")
            np.save("/home/claude/rh_voidline/ls20_stuck.npy", f)
            break

print("\nfinal: state=%s levels=%d actions=%d completions=%s" %
      (fr["state"], fr.get("levels_completed", 0), n_act, completions))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:500])
json.dump(dict(completions=completions, actions=n_act,
               rotators=[list(r) for r in rotators]),
          open("/home/claude/rh_voidline/ls20_solver2_log.json","w"), indent=1)
