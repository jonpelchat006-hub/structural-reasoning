"""LS20 experiment v2 — map-based navigation (passable read from the frame itself),
exact parking on the keyhole and slots. Movement-only game (available_actions=[1,2,3,4]),
so the win is a PLACE: park the 5x5 key block exactly somewhere meaningful."""
import json, os, sys
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, "/home/claude/rh_voidline")
from arc3_client import api, frame_np

HUD = 56
ACTS = {"ACTION1": (-3,0), "ACTION2": (3,0), "ACTION3": (0,-3), "ACTION4": (0,3)}
key = os.environ["ARC_API_KEY"]
games = api("/api/games", key)
gid = next(g["game_id"] for g in games if g["game_id"].startswith("ls20"))
card_id = api("/api/scorecard/open", key, {"tags": ["exp-v2"]}).get("card_id")
guid = {}; n_act = 0
def send(a):
    global n_act
    fr = api(f"/api/cmd/{a}", key, {"game_id": gid, "card_id": card_id, "guid": guid.get("v")})
    guid["v"] = fr["guid"]
    if a != "RESET": n_act += 1
    return fr

fr = send("RESET"); f = frame_np(fr)
lvl0 = fr.get("levels_completed", 0)

def agent_pos(f):
    m = (f[:HUD] == 12)
    if not m.any(): return None
    ys, xs = np.where(np.isin(f[:HUD], [9, 12]))
    lab, n = ndimage.label(np.isin(f[:HUD], [9, 12]))
    for i in range(1, n+1):
        yy, xx = np.where(lab == i)
        if (f[yy, xx] == 12).any():
            return (int(round(yy.mean())), int(round(xx.mean())))
    return None

PASS = {0, 1, 3, 9, 12}
def passable(f, p):
    y, x = p
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    w = f[y-2:y+3, x-2:x+3]
    return bool(np.isin(w, list(PASS)).all())

def drive_exact(f, fr, target, maxsteps=50):
    """walk the 3px lattice to put the agent center exactly on target"""
    for _ in range(maxsteps):
        pos = agent_pos(f)
        if pos is None or pos == target: return f, fr, pos == target
        q = deque([(pos, [])]); seen = {pos}; path = None
        while q:
            p, pth = q.popleft()
            if p == target: path = pth; break
            for a, d in ACTS.items():
                np_ = (p[0]+d[0], p[1]+d[1])
                if np_ in seen or not passable(f, np_): continue
                seen.add(np_); q.append((np_, pth + [a]))
        if not path:
            # nearest reachable point to target
            best, bd = None, 1e9
            for p in seen:
                dd = abs(p[0]-target[0]) + abs(p[1]-target[1])
                if dd < bd: best, bd = p, dd
            if best == pos or best is None: return f, fr, False
            q = deque([(pos, [])]); seen2 = {pos}
            while q:
                p, pth = q.popleft()
                if p == best: path = pth; break
                for a, d in ACTS.items():
                    np_ = (p[0]+d[0], p[1]+d[1])
                    if np_ in seen2 or not passable(f, np_): continue
                    seen2.add(np_); q.append((np_, pth + [a]))
            if not path: return f, fr, False
        for a in path:
            fr = send(a); f = frame_np(fr)
            if fr.get("levels_completed", 0) > lvl0 or fr["state"] in ("WIN", "GAME_OVER"):
                return f, fr, True
    return f, fr, agent_pos(f) == target

def targets(f):
    out = []
    m = np.isin(f[:HUD], [0, 1])
    if m.any():
        ys, xs = np.where(m); out.append(("keyhole", (int(round(ys.mean())), int(round(xs.mean())))))
    lab, n = ndimage.label(f[:HUD] == 4)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 60 and 10 <= ys.mean() <= 54 and 4 <= xs.mean() <= 60:
            out.append((f"slot", (int(round(ys.mean())), int(round(xs.mean())))))
    return out

log = []
for name, t in targets(f):
    if n_act > 140 or fr["state"] in ("WIN", "GAME_OVER"): break
    print(f"-> exact-park on {name} {t}   [action {n_act}]")
    f, fr, ok = drive_exact(f, fr, t)
    lv = fr.get("levels_completed", 0)
    print(f"   parked={ok} pos={agent_pos(f)} levels={lv} state={fr['state']} actions={n_act}")
    log.append(dict(target=name, at=t, parked=bool(ok), levels=lv,
                    state=fr["state"], actions=n_act))
    if lv > lvl0:
        print(">>> LEVEL COMPLETED at action %d (baseline 22)" % n_act); break
    # dump 13x13 around agent for the record
    p = agent_pos(f)
    if p:
        w = f[max(0,p[0]-6):p[0]+7, max(0,p[1]-6):p[1]+7]
        log[-1]["window"] = ["".join("%x" % v for v in row) for row in w]

print("\nfinal:", fr["state"], "levels:", fr.get("levels_completed"), "actions:", n_act)
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:400])
json.dump(log, open("/home/claude/rh_voidline/exp2_ls20.json","w"), indent=1)
np.save("/home/claude/rh_voidline/exp2_last.npy", f)
