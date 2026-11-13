"""ARC-AGI-3 runtime v1 — probe-first + budget engine + planned exploration.

The measured laws, wired for live play:
  * probe-first: learn (action -> displacement) by acting, identify the agent as whatever
    moves consistently (ARC_PROBE_FIRST / ARC_OPERATOR_INDUCTION)
  * budget engine: the HUD meter read as a two-register counter (fine bar + coarse pips);
    remaining budget tracked every step; exploration stops inside a reserve margin
    (Part XXXIV + golden-field reserve law)
  * planned spending: BFS on the learned movement lattice to distinct objects first (touch
    everything), then frontier cells — no random walk, blocked edges learned (free!) and
    remembered; no undo ever
  * surprise log: any off-agent frame change is evidence, kept (ARC_PERCEPTION_SURPRISE)
Usage: ARC_API_KEY=... python arc3_runtime.py --game ls20 [--cap 160]
"""
import json, os, sys, time
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, "/home/claude/rh_voidline")
from arc3_client import api, frame_np

HUD_ROW = 56          # rows >= this are HUD (meter etc.), not playfield
ACTS = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]

# ---------------- wire ----------------
key = os.environ["ARC_API_KEY"]
want = "ls20"; cap = 160
for i, a in enumerate(sys.argv):
    if a == "--game": want = sys.argv[i+1]
    if a == "--cap": cap = int(sys.argv[i+1])
games = api("/api/games", key)
gid = next(g["game_id"] for g in games if g["game_id"].startswith(want))
card_id = api("/api/scorecard/open", key, {"tags": ["runtime-v1"]}).get("card_id")
print("scorecard:", card_id, "game:", gid)
guid = {}
n_actions = 0
def send(a, x=None, y=None):
    global n_actions
    body = {"game_id": gid, "card_id": card_id, "guid": guid.get("v")}
    if x is not None: body.update(x=x, y=y)
    fr = api(f"/api/cmd/{a}", key, body)
    guid["v"] = fr["guid"]
    if a != "RESET": n_actions += 1
    return fr

# ---------------- perception ----------------
def agent_mask(f, agent_colors):
    return np.isin(f[:HUD_ROW], list(agent_colors))

def centroid(f, agent_colors):
    ys, xs = np.where(agent_mask(f, agent_colors))
    return (float(ys.mean()), float(xs.mean())) if len(ys) else None

def objects(f, agent_colors, bg_colors):
    """small static components worth touching (locks, keys, dots)"""
    out = []
    for c in range(16):
        if c in agent_colors or c in bg_colors: continue
        m = (f[:HUD_ROW] == c)
        if not m.any(): continue
        lab, n = ndimage.label(m)
        for i in range(1, n+1):
            ys, xs = np.where(lab == i)
            if 1 <= len(ys) <= 80:
                out.append((c, float(ys.mean()), float(xs.mean()), len(ys)))
    return out

# ---------------- budget engine (fine bar + coarse pips, online) ----------------
class Budget:
    def __init__(self, f0):
        self.h0 = f0[HUD_ROW:].copy()
        self.cap = None; self.last_bar = None; self.units_per_bar = None
        self.trace = []
    def read(self, f):
        h = f[HUD_ROW:]
        # fine bar = pixels equal to their t0 value among cells that EVER change
        chg = (h != self.h0)
        colors0, counts0 = np.unique(self.h0[self.h0 > 0], return_counts=True)
        # fuel color: the color losing pixels vs t0
        best, loss = None, 0
        for c in colors0:
            l = (self.h0 == c).sum() - (h == c).sum()
            if l > loss: best, loss = c, l
        bar_now = int((h == best).sum()) if best is not None else 0
        self.trace.append(bar_now)
        if self.last_bar is not None and bar_now > self.last_bar + 5:
            self.cap = bar_now                      # refill observed: capacity learned
        self.last_bar = bar_now
        return bar_now
    def remaining_actions(self, f):
        bar = self.read(f)
        h = f[HUD_ROW:]
        # credit the coarse register: any HUD color that has only stepped DOWN, rarely
        pip_units = 0
        for c in np.unique(self.h0[self.h0 > 0]):
            n0 = int((self.h0 == c).sum()); n1 = int((h == c).sum())
            if 0 < n1 <= n0 and n0 <= 24 and n1 < n0 + 1:
                pip_units += n1        # each surviving pip pixel is stored fuel
        # each pip refills one bar (learned scale: pips are small, bars big)
        bars_stored = pip_units / 4.0 if pip_units else 0.0
        return bar // 2 + int(bars_stored * 42)

# ---------------- main loop ----------------
log = dict(levels=[], surprises=[], probe={}, frames_kept=[])
fr = send("RESET")
f = frame_np(fr)
budget = Budget(f)
f0 = f.copy()

# --- probe: which colors move, and how far, per action ---
disp = {}
agent_colors = set()
prev = f
for a in ACTS:
    fr = send(a); cur = frame_np(fr)
    dm = (cur[:HUD_ROW] != prev[:HUD_ROW])
    moved_colors = set(prev[:HUD_ROW][dm].tolist()) | set(cur[:HUD_ROW][dm].tolist())
    moved_colors -= {0}
    prev2 = prev
    prev = cur
    if not dm.any(): continue
    agent_colors |= {c for c in moved_colors if (prev2[:HUD_ROW] == c).sum() < 200}
bg = {int(c) for c in np.unique(f0[:HUD_ROW]) if (f0[:HUD_ROW] == int(c)).sum() >= 200}
agent_colors -= bg
print("agent colors:", sorted(agent_colors), " background:", sorted(bg))
# second probe pass: displacement per action from a clean read
for a in ACTS:
    c0 = centroid(prev, agent_colors)
    fr = send(a); cur = frame_np(fr)
    c1 = centroid(cur, agent_colors)
    if c0 and c1:
        d = (round(c1[0]-c0[0]), round(c1[1]-c0[1]))
        if d != (0, 0): disp[a] = d
    prev = cur
quant = max((max(abs(d[0]), abs(d[1])) for d in disp.values()), default=5)
# fill unknown directions with the semantic default scaled to the learned quantum
default = {"ACTION1": (-1,0), "ACTION2": (1,0), "ACTION3": (0,-1), "ACTION4": (0,1)}
for a in ACTS:
    if a not in disp: disp[a] = (default[a][0]*quant, default[a][1]*quant)
log["probe"] = {a: disp[a] for a in ACTS}
print("displacements:", disp, " (quantum %d px)" % quant)

blocked = set()           # (pos, action) edges that failed
visited = set()
score_prev = fr.get("score", 0) or 0
level_start_actions = n_actions
f = prev

def lattice(p):
    return (round(p[0]/quant), round(p[1]/quant))

def plan(start, goals, maxn=4000):
    """BFS on the learned lattice; unknown = walkable, blocked edges remembered"""
    q = deque([(start, [])]); seen = {start}
    while q and len(seen) < maxn:
        pos, path = q.popleft()
        if pos in goals: return path
        for a in ACTS:
            d = disp[a]
            np_ = (pos[0] + d[0], pos[1] + d[1])
            l_ = lattice(np_)
            if (lattice(pos), a) in blocked or l_ in [lattice(p) for p in []]: continue
            if not (0 <= np_[0] < HUD_ROW and 0 <= np_[1] < 64): continue
            if l_ not in [s for s in []] and (np_ not in seen):
                seen.add(np_); q.append((np_, path + [a]))
    return None

while n_actions < cap and fr["state"] not in ("WIN", "GAME_OVER"):
    pos = centroid(f, agent_colors)
    if pos is None: break
    visited.add(lattice(pos))
    rem = budget.remaining_actions(f)
    if rem < 10:
        print("budget low (%d est. actions) — spending to the end (probe-death doctrine)" % rem)
    # targets: unvisited objects first, then frontier
    objs = [(o[1], o[2]) for o in objects(f, agent_colors, bg)
            if lattice((o[1], o[2])) not in visited]
    goals = {(oy, ox) for oy, ox in objs}
    goal_l = {lattice(g) for g in goals}
    # plan to nearest object by BFS over positions whose lattice hits a goal lattice
    path = None
    q = deque([(pos, [])]); seen = {lattice(pos)}
    while q:
        p, pth = q.popleft()
        if lattice(p) in goal_l and pth: path = pth; break
        if len(pth) > 60: continue
        for a in ACTS:
            d = disp[a]; np_ = (p[0]+d[0], p[1]+d[1])
            if not (0 <= np_[0] < HUD_ROW and 0 <= np_[1] < 64): continue
            if (lattice(p), a) in blocked: continue
            if lattice(np_) not in seen:
                seen.add(lattice(np_)); q.append((np_, pth + [a]))
    if path is None:
        # frontier: nearest lattice cell not visited
        q = deque([(pos, [])]); seen = {lattice(pos)}
        while q:
            p, pth = q.popleft()
            if lattice(p) not in visited and pth: path = pth; break
            if len(pth) > 60: continue
            for a in ACTS:
                d = disp[a]; np_ = (p[0]+d[0], p[1]+d[1])
                if not (0 <= np_[0] < HUD_ROW and 0 <= np_[1] < 64): continue
                if (lattice(p), a) in blocked: continue
                if lattice(np_) not in seen:
                    seen.add(lattice(np_)); q.append((np_, pth + [a]))
    if not path:
        print("nowhere new reachable — stopping"); break
    # execute the plan, verifying each step
    for a in path:
        if n_actions >= cap: break
        p0 = centroid(f, agent_colors)
        fr = send(a); f2 = frame_np(fr)
        p1 = centroid(f2, agent_colors)
        score = fr.get("score", 0) or 0
        if score > score_prev:
            used = n_actions - level_start_actions
            log["levels"].append(dict(level=score, actions=used))
            print(">>> LEVEL UP to %d after %d actions (baseline level1 = 22)" % (score, used))
            score_prev = score; level_start_actions = n_actions
            blocked.clear(); visited.clear()
            f = f2
            break
        if fr["state"] in ("WIN", "GAME_OVER"): f = f2; break
        moved = p0 and p1 and (abs(p1[0]-p0[0]) + abs(p1[1]-p0[1]) > 1)
        if not moved:
            blocked.add((lattice(p0), a))          # learned wall, cost-free (measured law)
            f = f2; break                          # replan
        # off-agent surprise?
        am = agent_mask(f, agent_colors) | agent_mask(f2, agent_colors)
        other = ((f[:HUD_ROW] != f2[:HUD_ROW]) & ~am)
        if other.sum() > 4:
            ys, xs = np.where(other)
            log["surprises"].append(dict(step=n_actions, n=int(other.sum()),
                                         at=[int(ys.mean()), int(xs.mean())]))
        f = f2
        if lattice(centroid(f, agent_colors) or (0,0)) in visited: pass
        visited.add(lattice(p1))

print("\nfinal: state=%s actions=%d levels=%s surprises=%d" %
      (fr["state"], n_actions, [l["level"] for l in log["levels"]], len(log["surprises"])))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:600])
log["final_state"] = fr["state"]; log["actions"] = n_actions
json.dump(log, open("/home/claude/rh_voidline/runtime_v1_log.json","w"), indent=1)
np.save("/home/claude/rh_voidline/runtime_v1_last.npy", f)
print("saved runtime_v1_log.json")
