"""LS20 solver v4 — the anchor + delta structure (Part XXXVIII, Jonathan's level law):
levels keep the solved policy (match the key, protect it, insert at the goal) and add
deltas (new rotator patches on the path). New: PARITY PLANNING — if no rotator-free route
to the box exists, plan through them and pre-set the key so the crossings finish the match
(each rotator entry adds +1 to rot_needed mod 4, measured)."""
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
card_id = api("/api/scorecard/open", key, {"tags": ["ls20-direct-insert"]}).get("card_id")
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
def glyph_color(region, exclude):
    vals = region[~np.isin(region, list(exclude))]
    if not len(vals): return None
    u, c = np.unique(vals, return_counts=True)
    return int(u[np.argmax(c)])
def hud_glyph(f):
    box = f[54:64, 0:14]
    col = glyph_color(box, {3, 4, 5, 11, 8, 0})
    return (shrink(box == col) if col is not None else np.zeros((1,1), int)), col
def goal_box(f):
    lab, n = ndimage.label(f[:52] == 5)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) < 16: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        inner = f[y0+1:y1, x0+1:x1]
        col = glyph_color(inner, {5})
        if inner.size and col is not None and (inner == col).sum() >= 4:
            return (shrink(inner == col), col), (int((y0+y1)//2), int((x0+x1)//2))
    return None, None
def keyhole(f):
    m = np.isin(f[:52], [0, 1])
    if not m.any(): return None
    ys, xs = np.where(m)
    return (int(round(ys.mean())), int(round(xs.mean())))
def rot_candidates(f):
    out = []
    kh = keyhole(f)
    if kh: out.append(kh)
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30:
            out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return out
def small11(f):
    cells = set()
    lab, n = ndimage.label(f[:52] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: cells |= {(int(y), int(x)) for y, x in zip(ys, xs)}
    return cells
def agent_pos(f):
    lab, n = ndimage.label(np.isin(f[:HUD], [9, 12]))
    for i in range(1, n+1):
        yy, xx = np.where(lab == i)
        if (f[yy, xx] == 12).any(): return (int(round(yy.mean())), int(round(xx.mean())))
    return None
PASS = {0, 1, 3, 9, 12}
S11 = set()
def passable(f, p):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    w = f[y-2:y+3, x-2:x+3]
    for dy in range(5):
        for dx in range(5):
            v = int(w[dy, dx])
            if v in PASS: continue
            if v == 11 and (y-2+dy, x-2+dx) in S11: continue
            return False
    return True
def near_rot(p, rots, r=4):
    return any(abs(p[0]-q[0]) + abs(p[1]-q[1]) <= r for q in rots)
def bfs(f, pos, want, rots, protect, near=2):
    """path to within `near` of want; protect=True forbids rotator cells.
       returns (path, reached, crossings)"""
    q = deque([(pos, [], 0)]); seen = {pos}
    best = (pos, [], 0); bd = abs(pos[0]-want[0]) + abs(pos[1]-want[1])
    while q:
        p, pth, c = q.popleft()
        d = abs(p[0]-want[0]) + abs(p[1]-want[1])
        if d < bd: best, bd = (p, pth, c), d
        if d <= near: return pth, True, c
        for a, dv in ACTS.items():
            np_ = (p[0]+dv[0], p[1]+dv[1])
            if np_ in seen or not passable(f, np_): continue
            hit = near_rot(np_, rots)
            if protect and hit: continue
            seen.add(np_); q.append((np_, pth + [a], c + (1 if hit else 0)))
    return best[1], False, best[2]
def match_rot(H, G):
    for k_ in range(4):
        Hk = np.rot90(H, k_)
        if Hk.shape == G.shape and (Hk == G).all(): return k_
    return None

fr = send("RESET"); f = frame_np(fr)
lvl = fr.get("levels_completed", 0)
rotators = set()
dead_cands = set()
completions = []
lvl_seen = lvl
print("start: level", lvl, "of", fr.get("win_levels"))

def step(a):
    global f, fr, lvl, rotators, lvl_seen
    H0, c0 = hud_glyph(f)
    p_before = agent_pos(f)
    fr = send(a); f2 = frame_np(fr)
    nl = fr.get("levels_completed", 0)
    if nl > lvl or fr["state"] == "WIN":
        completions.append(dict(level=nl, actions=n_act))
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act))
        lvl = nl
        rotators = set(); dead_cands.clear()
        f = f2; return True, False
    H1, c1 = hud_glyph(f2)
    rot = (H1.shape != H0.shape) or not (H1 == H0).all() or (c1 != c0)
    rp = agent_pos(f2)
    respawn = p_before and rp and (abs(rp[0]-p_before[0]) + abs(rp[1]-p_before[1]) > 12)
    if rot and respawn:
        print("  (bar refill respawn — key reset, not a rotator)")
    elif rot and rp:
        rotators.add(rp)
    f = f2
    return False, rot

def chain_cost(f, pos, cand, box_c):
    q = deque([(pos, 0)]); seen = {pos}; d1 = None
    while q:
        p, d0 = q.popleft()
        if abs(p[0]-cand[0]) + abs(p[1]-cand[1]) <= 2: d1 = d0; break
        for _, dv in ACTS.items():
            np_ = (p[0]+dv[0], p[1]+dv[1])
            if np_ not in seen and passable(f, np_): seen.add(np_); q.append((np_, d0+1))
    if d1 is None: return None
    q = deque([(cand, 0)]); seen = {cand}
    while q:
        p, d0 = q.popleft()
        if abs(p[0]-box_c[0]) + abs(p[1]-box_c[1]) <= 12: return d1 + d0
        for _, dv in ACTS.items():
            np_ = (p[0]+dv[0], p[1]+dv[1])
            if np_ not in seen and passable(f, np_): seen.add(np_); q.append((np_, d0+1))
    return None

while n_act < 165 and fr["state"] not in ("WIN", "GAME_OVER"):
    S11.clear(); S11.update(small11(f))
    Hres = hud_glyph(f); Gres, box_c = goal_box(f)
    if Gres is None or agent_pos(f) is None:
        print("perception incomplete at action", n_act); break
    H, hcol = Hres; (G, gcol) = Gres[0], Gres[1]
    kh = keyhole(f); pos = agent_pos(f)
    if hcol != gcol:
        print(f"  COLOR mismatch: key color {hcol} vs goal {gcol} — a color batch is needed")
    k = match_rot(H, G)
    global_cands = [c for c in rot_candidates(f) if c not in dead_cands]
    rots = set(rotators) | set(global_cands)
    print(f"[{n_act}] L{lvl} rot_needed={k} pos={pos} cands={global_cands} dead={sorted(dead_cands)}")
    if k is None:
        print("  patterns unrelated — stopping"); break
    if k == 0:
        path_p, reach_p, _ = bfs(f, pos, box_c, rots, protect=True, near=12)
        path_use = path_p if reach_p else None
        if path_use is None:
            path_u, reach_u, c = bfs(f, pos, box_c, rots, protect=False, near=12)
            if reach_u and c > 0:
                e = (4 - (c % 4)) % 4
                print(f"  protected route can't reach; crossing {c} rotators -> pre-rotating {e}")
                tgt = kh or next(iter(rotators), None)
                for _ in range(e):
                    pw, ok_, _ = bfs(f, agent_pos(f), tgt, set(), protect=False, near=0)
                    for a in pw:
                        lv, rot = step(a)
                        if lv or rot or fr["state"] in ("WIN","GAME_OVER"): break
                    lv, _ = step("ACTION1")
                    if lv or fr["state"] in ("WIN","GAME_OVER"): break
                path_use, _, _ = bfs(f, agent_pos(f), box_c, rots, protect=False, near=12)
            else:
                path_use = path_p or path_u
        if not path_use:
            print("  matched but no progress possible — probing"); step("ACTION1"); continue
        broke = False
        for a in path_use:
            lv, rot = step(a)
            if lv or rot or fr["state"] in ("WIN", "GAME_OVER"): broke = True; break
        if not broke and fr["state"] not in ("WIN", "GAME_OVER"):
            for _ in range(3):
                p2 = agent_pos(f)
                if not p2: break
                dy, dx = box_c[0]-p2[0], box_c[1]-p2[1]
                if abs(dy) + abs(dx) <= 2: break
                push, dv = (("ACTION1", (-5,0)) if dy < 0 else ("ACTION2", (5,0))) if abs(dy) >= abs(dx)                            else (("ACTION3", (0,-5)) if dx < 0 else ("ACTION4", (0,5)))
                land = (p2[0]+dv[0], p2[1]+dv[1])
                if near_rot(land, rotators):
                    print("  push would hit a rotator — stopping push"); break
                lv, rot = step(push)
                if lv or rot or fr["state"] in ("WIN", "GAME_OVER"): break
        continue
    # k != 0: cheapest full chain; if NOTHING fits the attempt timer (~20 actions),
    # test the side-insertion hypothesis: push in unrotated and observe
    scored = [(chain_cost(f, pos, c, box_c), c) for c in global_cands]
    scored = [(cost, c) for cost, c in scored if cost is not None]
    if scored: print("  chain costs:", [(c, cost) for cost, c in sorted(scored)])
    if lvl >= 1 and (not scored or min(scored)[0] > 20):
        print("  no chain fits the attempt timer -> DIRECT INSERT test (side sets orientation?)")
        path_d, reach_d, _ = bfs(f, pos, box_c, set(), protect=False, near=12)
        for a in path_d:
            lv, rot = step(a)
            if lv or fr["state"] in ("WIN", "GAME_OVER"): break
        for _ in range(4):
            if fr["state"] in ("WIN", "GAME_OVER"): break
            p2 = agent_pos(f)
            if not p2: break
            dy, dx = box_c[0]-p2[0], box_c[1]-p2[1]
            if abs(dy) + abs(dx) <= 2: break
            push = ("ACTION1" if dy < 0 else "ACTION2") if abs(dy) >= abs(dx) else ("ACTION3" if dx < 0 else "ACTION4")
            lv, rot = step(push)
            if lv: break
        continue
    target = min(scored)[1] if scored else next(iter(rotators), None)
    if target is None:
        print("  no rotator known — probing"); step("ACTION1"); continue
    k_before = k
    pw, ok_, _ = bfs(f, pos, target, set(), protect=False, near=0)
    done = False
    for a in pw:
        done, _ = step(a)
        if done or fr["state"] in ("WIN", "GAME_OVER"): break
    if done or fr["state"] in ("WIN", "GAME_OVER"): continue
    cur_k = match_rot(hud_glyph(f)[0], G)
    if cur_k == k_before and agent_pos(f) and abs(agent_pos(f)[0]-target[0]) + abs(agent_pos(f)[1]-target[1]) <= 2:
        print("  candidate", target, "did not rotate — blacklisting")
        dead_cands.add(target)
        continue
    tries = 0
    while cur_k not in (0, None) and tries < 8 and fr["state"] not in ("WIN", "GAME_OVER"):
        for pair in [("ACTION1","ACTION2"), ("ACTION3","ACTION4"), ("ACTION2","ACTION1"), ("ACTION4","ACTION3")]:
            lv1, _ = step(pair[0])
            if lv1 or fr["state"] in ("WIN","GAME_OVER"): break
            lv2, rot2 = step(pair[1])
            if lv2 or fr["state"] in ("WIN","GAME_OVER") or rot2: break
        cur_k = match_rot(hud_glyph(f)[0], G)
        tries += 1

print("\nfinal: state=%s levels=%d actions=%d completions=%s" %
      (fr["state"], fr.get("levels_completed", 0), n_act, completions))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:700])
json.dump(dict(completions=completions, actions=n_act),
          open("/home/claude/rh_voidline/ls20_solver4_log.json","w"), indent=1)
