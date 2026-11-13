"""LS20 L2 — Jonathan's exact sequence (the teacher's full instruction):
refill #1 right away (the nook by spawn) -> rotate 3 times (down-entries, +1 each)
-> refill #2 just before the end (17,16 — it opens the endgame) -> insert at the box.
Pips = lives. Bar logged everywhere; nook entered by free blocked pushes if needed."""
import json, os, sys
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arc3_client import api, frame_np

HUD = 56
ACTS = {"ACTION1": (-5,0), "ACTION2": (5,0), "ACTION3": (0,-5), "ACTION4": (0,5)}
key = os.environ.get("ARC_API_KEY") or __import__("arc_daily").get_key()
games = api("/api/games", key)
gid = next(g["game_id"] for g in games if g["game_id"].startswith("ls20"))
card_id = api("/api/scorecard/open", key, {"tags": ["ls20-L1L2-planet"]}).get("card_id")
guid = {}; n_act = 0; frames = []; _trans = []; _lv = [0]
import atexit, time
HERE = os.path.dirname(os.path.abspath(__file__))
def _save():
    try:
        np.savez_compressed(os.path.join(HERE, "ls20_l1l2_frames.npz"), F=np.array(frames, dtype=np.int8))
        with open(os.path.join(HERE, "arc3_trans.jsonl"), "w", encoding="utf-8") as _f:
            for r in _trans: _f.write(json.dumps(r) + "\n")
    except Exception as e: print("save failed:", e)
atexit.register(_save)
def send(a):
    global n_act
    for attempt in range(5):          # the live API drops connections; a lost press must not lose the run
        try:
            fr = api(f"/api/cmd/{a}", key, {"game_id": gid, "card_id": card_id, "guid": guid.get("v")})
            break
        except Exception as e:
            print("  [net] %s (attempt %d)" % (str(e)[:80], attempt + 1)); time.sleep(2 + 2 * attempt)
    else:
        raise RuntimeError("live API unreachable after 5 attempts")
    guid["v"] = fr["guid"]
    if a != "RESET": n_act += 1
    f = frame_np(fr)
    try:
        st = fr["state"]; prev = frames[-1] if frames else None
        nl = fr.get("levels_completed", 0) or 0
        eff = ("win" if st == "WIN" else "game_over" if st == "GAME_OVER" else
               "score_up" if nl > _lv[0] else
               "changed" if (prev is None or not np.array_equal(f, prev)) else "nothing")
        _lv[0] = max(_lv[0], nl)
        _trans.append({"action": a, "effect": eff})
    except Exception: pass
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
def glyph_color(region, exclude):
    vals = region[~np.isin(region, list(exclude))]
    if not len(vals): return None
    u, c = np.unique(vals, return_counts=True)
    return int(u[np.argmax(c)])
def key_color(f):
    """the held key's glyph color (L3+ changes it; the color batch sets it to the goal's)"""
    return glyph_color(f[54:64, 0:14], {3, 4, 5, 11, 0})   # 8 is a real key color (renders 'blank' in L4's cycle)
def hud_glyph(f):
    col = key_color(f)
    return shrink(f[54:64, 0:14] == col) if col is not None else np.zeros((1, 1), int)
def _box_mask(f):
    m = (f == 5); m[:, :4] = False; m[52:, :12] = False; m[60:] = False
    return m
def goal_box(f):
    lab, n = ndimage.label(_box_mask(f))
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) < 16: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        inner = f[y0+1:y1, x0+1:x1]
        col = glyph_color(inner, {3, 4, 5, 11, 0})     # 8 is a real goal color (L5)
        if inner.size and col is not None and (inner == col).sum() >= 4:
            return shrink(inner == col), (int((y0+y1)//2), int((x0+x1)//2))
    return None, None
def goal_color(f):
    lab, n = ndimage.label(_box_mask(f))
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) < 16: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        return glyph_color(f[y0+1:y1, x0+1:x1], {3, 4, 5, 11, 0})
    return None
def keyhole(f):
    lab, n = ndimage.label(np.isin(f[:52], [0, 1]))
    best = None
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if (f[ys, xs] == 0).any() and len(ys) <= 30:
            best = (int(round(ys.mean())), int(round(xs.mean()))); break
    if best is None and n:
        ys, xs = np.where(lab > 0); best = (int(round(ys.mean())), int(round(xs.mean())))
    return best
def rings(f):
    out = []
    lab, n = ndimage.label(f[:HUD] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return out
def agent_pos(f):
    """the key block: a 2x5 bar of color 12 over 3x5 of color 9. The 12-bar alone identifies it
    (color stations carry stray 12s that fooled the old blob rule)"""
    lab, n = ndimage.label(f[:HUD] == 12)
    for i in range(1, n+1):
        yy, xx = np.where(lab == i)
        if len(yy) == 10 and yy.max() - yy.min() == 1 and xx.max() - xx.min() == 4:
            return (int(yy.min()) + 2, int(xx.min()) + 2)
    for i in range(1, n+1):                      # fallback: any 12 blob of agent size
        yy, xx = np.where(lab == i)
        if 6 <= len(yy) <= 25: return (int(yy.min()) + 2, int(xx.min()) + 2)
    return None
def bar_px(f): return int((f[56:] == 11).sum())
def s11set(f):
    cells = set()
    lab, n = ndimage.label(f[:HUD] == 11)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) <= 30: cells |= {(int(y), int(x)) for y, x in zip(ys, xs)}
    return cells
def fan_cells(f):
    """each color-1 strip (no 0 in its blob = not a keyhole) defends the 5x5 cell on its open side;
    entering that cell is a RIDE to the far wall. Never path through one by accident."""
    out = set()
    lab, n = ndimage.label(f[:HUD] == 1)
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if len(ys) < 3: continue
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        if y0 == y1:                                   # horizontal strip -> blows north or south
            xc = (x0 + x1) // 2
            if y0 + 1 < HUD and f[y0 + 1, xc] == 3: out.add((int(y0) + 3, int(xc)))
            if y0 - 1 >= 0 and f[y0 - 1, xc] == 3: out.add((int(y0) - 3, int(xc)))
        elif x0 == x1:                                 # vertical strip -> blows east or west
            yc = (y0 + y1) // 2
            if x0 + 1 < 64 and f[yc, x0 + 1] == 3: out.add((int(yc), int(x0) + 3))
            if x0 - 1 >= 0 and f[yc, x0 - 1] == 3: out.add((int(yc), int(x0) - 3))
    return out
PASS = {0, 1, 3, 9, 12}
def passable(f, p, s, fans=frozenset()):
    y, x = p
    if p in fans: return False
    if not (2 <= y < HUD-2 and 2 <= x < 62): return False
    for dy in range(5):
        for dx in range(5):
            v = int(f[y-2+dy, x-2+dx])
            if v in PASS or (v == 11 and (y-2+dy, x-2+dx) in s): continue
            return False
    return True
LVL = [0]; TARGET = [2]
def leveled(fr):
    nl = fr.get("levels_completed", 0)
    if nl > LVL[0]:
        print(">>> LEVEL %d COMPLETE at action %d" % (nl, n_act)); LVL[0] = nl; return True
    return False
def snap(f, p):
    """the standable lattice cell nearest a feature (the agent moves on a 5-px lattice)"""
    a = agent_pos(f)
    if a is None: return p
    def sn(v, av):
        d = (av - v) % 5
        return v + (d if d <= 2 else d - 5)
    return (sn(p[0], a[0]), sn(p[1], a[1]))
def _zeros(f):
    out = []
    lab, n = ndimage.label(np.isin(f[:HUD], [0, 1]))
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if (f[ys, xs] == 0).any() and len(ys) <= 30: out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return out
def goto(f, fr, want, near=0, cap=30):
    for _ in range(cap):
        pos = agent_pos(f)
        if pos is None: return f, fr, False
        if abs(pos[0]-want[0]) + abs(pos[1]-want[1]) <= near: return f, fr, True
        s = s11set(f); fans = fan_cells(f) | {snap(f, z) for z in _zeros(f)}; fans -= {tuple(want)}   # never wander into a fan cell or a keyhole
        q = deque([(pos, [])]); seen = {pos}; path = None
        while q:
            p, pth = q.popleft()
            if abs(p[0]-want[0]) + abs(p[1]-want[1]) <= near: path = pth; break
            for a, dv in ACTS.items():
                np_ = (p[0]+dv[0], p[1]+dv[1])
                if np_ not in seen and passable(f, np_, s, fans):
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
    b0 = bar_px(f); n0 = len(rings(f))
    def got(f):
        return bar_px(f) > b0 + 8 or len(rings(f)) < n0
    # SNAP the ring to the agent's 5-px lattice (parity!): the standable cell
    p = agent_pos(f)
    ry = ring[0] + ((p[0] - ring[0]) % 5 if (p[0] - ring[0]) % 5 <= 2 else (p[0] - ring[0]) % 5 - 5)
    rx = ring[1] + ((p[1] - ring[1]) % 5 if (p[1] - ring[1]) % 5 <= 2 else (p[1] - ring[1]) % 5 - 5)
    snapped = (ry, rx)
    f, fr, ok = goto(f, fr, snapped, 0, cap=12)
    if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= TARGET[0]: return f, fr, False
    if ok and got(f):
        print("  [REFILL collected at %s] bar %d -> %d" % (str(snapped), b0, bar_px(f)))
        return f, fr, True
    if ok:
        # stand on it a beat: step off and back on
        fr, f = send("ACTION3"); fr, f = send("ACTION4")
        if got(f):
            print("  [REFILL collected at %s] bar %d -> %d" % (str(snapped), b0, bar_px(f)))
            return f, fr, True
    cands = []
    for dy, dx in [(-5,0),(5,0),(0,-5),(0,5),(-10,0),(10,0),(0,-10),(0,10),
                   (5,5),(5,-5),(-5,5),(-5,-5)]:
        launch = (snapped[0]+dy, snapped[1]+dx)
        cands.append(launch)
    for launch in cands:
        f, fr, ok = goto(f, fr, launch, 0, cap=8)
        if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= TARGET[0]: return f, fr, False
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
            if got(f):
                print("  [REFILL collected at %s] bar %d -> %d" % (str(ring), b0, bar_px(f)))
                return f, fr, True
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
                if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= TARGET[0]: break
                fr, f = send("ACTION2")
                if leveled(fr): break
            print("[insert done] pos %s bar %d level %d" % (agent_pos(f), bar_px(f), LVL[0]))


def touch(f, fr, target, label, tries=2):
    """stations (color batch, shapers) are not standable: stand next to them and push in"""
    for launch in [(target[0]-5, target[1]), (target[0]+5, target[1]), (target[0], target[1]-5), (target[0], target[1]+5),
                   (target[0]-10, target[1]), (target[0]+10, target[1]), (target[0], target[1]-10), (target[0], target[1]+10)]:
        f, fr, ok = goto(f, fr, launch, 0, cap=16)
        if fr["state"] in ("WIN","GAME_OVER"): return f, fr, False
        if not ok: continue
        for _ in range(tries):
            p = agent_pos(f)
            if p is None: break
            dyy, dxx = target[0]-p[0], target[1]-p[1]
            a = ("ACTION1" if dyy < 0 else "ACTION2") if abs(dyy) >= abs(dxx) else ("ACTION3" if dxx < 0 else "ACTION4")
            kc0 = key_color(f)
            fr, f = send(a)
            if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): return f, fr, False
            print("  [%s] from %s pushed %s -> pos %s key color %s->%s" % (label, str(p), a, str(agent_pos(f)), kc0, key_color(f)))
            if key_color(f) != kc0: return f, fr, True
    return f, fr, False

# ============================ L3 — the transfer level (ARC3_LIVE_PLAN, l3_final.py rebuilt) ======
def hop(f, fr, launch, act, label):
    """step to a launch cell, then one press into a transport (wind / shaft); report the landing"""
    f, fr, ok = goto(f, fr, launch, 0, cap=24)
    p0 = agent_pos(f); b0 = bar_px(f)
    fr, f = send(act)
    p1 = agent_pos(f)
    print("[%s] launch %s ok=%s -> landed %s (bar %d->%d)" % (label, str(p0), ok, str(p1), b0, bar_px(f)))
    return f, fr, p1

def keyhole_entries(f, fr, kh, G, want_k=0, max_entries=3):
    """down-entries at a keyhole: each = +1; read k after every entry"""
    kh = snap(f, kh)
    k = match_rot(hud_glyph(f), G)
    n = 0
    while k not in (0, None) and n < max_entries and fr["state"] not in ("WIN","GAME_OVER"):
        f, fr, ok = goto(f, fr, (kh[0]-5, kh[1]), 0, cap=14)
        if not ok: print("  cannot reach above the keyhole"); break
        fr, f = send("ACTION2")
        if leveled(fr) or fr["state"] in ("WIN","GAME_OVER"): break
        k = match_rot(hud_glyph(f), G); n += 1
        print("  [entry] k=%s bar %d actions %d" % (k, bar_px(f), n_act))
        if k != want_k:
            fr, f = send("ACTION1")
    return f, fr, k

def route(f, fr, pts, label):
    """walk a list of lattice waypoints; stop on level/win/death"""
    for p in pts:
        f, fr, ok = goto(f, fr, p, 0, cap=8)
        if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= TARGET[0]: return f, fr, ok
        if not ok: print("  [%s] could not reach %s (at %s)" % (label, str(p), str(agent_pos(f)))); return f, fr, False
    return f, fr, True

if LVL[0] == 2 and fr["state"] not in ("WIN", "GAME_OVER"):
    TARGET[0] = 3
    G3, box3 = goal_box(f); kh3 = keyhole(f)
    print("[L3 start] bar %d pos %s rings %s keyhole %s box %s key color %s goal color %s k=%s"
          % (bar_px(f), agent_pos(f), rings(f), kh3, box3, key_color(f), goal_color(f), match_rot(hud_glyph(f), G3) if G3 is not None else None))
    np.save(os.path.join(HERE, "ls20_L3_start.npy"), f)
    # the map (read live Sep 2): spawn (47,11) at the foot of the west corridor x=11; a fan at the
    # corridor's top blows you east along row 7 to (7,36). The top-left room drains south down x=31
    # into the big room (rows 25-34), which drains south down x=31 to the lower room with the COLOR
    # BATCH (3x3 patch at (47,31)) and east/up x=56 to the top-right room with the KEYHOLE (12,51)
    # and the fan-shaft x=56 that drops you to (47,56), right above the goal box (52,56).
    # Fuel: 4 px per move, 84 px bar. ring1 (32,21) then batch then ring2 (17,36) then keyhole.
    f, fr, p = hop(f, fr, (12, 11), "ACTION1", "T1 wind")
    f, fr, got1 = collect_ring(f, fr, (32, 21)); print("[ring1] collected=%s bar %d actions %d" % (got1, bar_px(f), n_act))
    if key_color(f) != goal_color(f):
        f, fr, ok = route(f, fr, [(32, 31), (42, 31)], "to-batch")
        f, fr, ok = touch(f, fr, (47, 31), "batch", tries=2)
        print("[batch] flipped=%s pos %s bar %d key color %s (goal %s)" % (ok, agent_pos(f), bar_px(f), key_color(f), goal_color(f)))
    else: print("[batch] key already the goal color %s" % key_color(f))
    f, fr, ok = route(f, fr, [(32, 31), (17, 31)], "to-ring2")
    f, fr, got2 = collect_ring(f, fr, (17, 36)); print("[ring2] collected=%s bar %d actions %d" % (got2, bar_px(f), n_act))
    f, fr, ok = route(f, fr, [(27, 36), (27, 56), (17, 56), (17, 46), (7, 46), (7, 51)], "to-keyhole")   # never step on (7,56): that is the fan drop
    G3, box3 = goal_box(f); kh3 = keyhole(f) or (12, 51)
    print("[pre-keyhole] pos %s bar %d k=%s keyhole %s" % (agent_pos(f), bar_px(f), match_rot(hud_glyph(f), G3) if G3 is not None else None, kh3))
    if G3 is not None:
        f, fr, k = keyhole_entries(f, fr, kh3, G3, 0, 4)
    else: k = None
    print("[L3 keyhole] k=%s bar %d actions %d pos %s" % (k, bar_px(f), n_act, agent_pos(f)))
    if fr["state"] not in ("WIN","GAME_OVER") and LVL[0] == 2:
        # from inside the keyhole (12,51): east to (12,56), NORTH into the fan cell (7,56) -> dropped to (47,56); push down into the box
        f, fr, ok = route(f, fr, [(12, 56)], "to-shaft")
        f, fr, p = hop(f, fr, (12, 56), "ACTION1", "drop shaft")
        for _ in range(3):
            if fr["state"] in ("WIN","GAME_OVER") or LVL[0] >= 3: break
            fr, f = send("ACTION2"); leveled(fr)
        print("[L3 end] pos %s bar %d level %d actions %d" % (agent_pos(f), bar_px(f), LVL[0], n_act))

# ============================ L4 — fans, color station, shape stamp (probed live Sep 2) =============
# Rules learned: 2 px per press here (blocked presses cost too); a FAN CELL (the 5x5 in front of a
# color-1 strip) carries you to the far wall in one press, straight through other fan cells.
# Rides: (22,46)->S->(47,46); (42,46)->W->(42,36); (27,41)->N->(7,41); (27,46)->W->(27,36) (shelf);
# (37,11)->E->(37,26) (under the stamp pocket); (42,26)->W->(42,11).
def press(f, fr, a, label):
    p0 = agent_pos(f); b0 = bar_px(f); k0 = key_color(f)
    fr, f = send(a)
    p1 = agent_pos(f)
    ride = p1 is not None and p0 is not None and (abs(p1[0]-p0[0]) + abs(p1[1]-p0[1])) > 5
    print("  [%s] %s at %s -> %s%s bar %d->%d key %s->%s lvl %d" % (label, a, str(p0), str(p1), " RIDE" if ride else "", b0, bar_px(f), k0, key_color(f), fr.get("levels_completed", 0)))
    leveled(fr)
    return f, fr, p1

if LVL[0] == 3 and fr["state"] not in ("WIN", "GAME_OVER"):
    TARGET[0] = 4
    G4, box4 = goal_box(f); kh4 = snap(f, keyhole(f)) if keyhole(f) else None
    print("[L4 start] bar %d pos %s rings %s keyhole %s box %s key color %s goal color %s k=%s fans %s"
          % (bar_px(f), agent_pos(f), rings(f), kh4, box4, key_color(f), goal_color(f), match_rot(hud_glyph(f), G4) if G4 is not None else None, sorted(fan_cells(f))))
    np.save(os.path.join(HERE, "ls20_L4_start.npy"), f)
    alive = lambda: fr["state"] not in ("WIN", "GAME_OVER") and LVL[0] == 3
    # 1. T1 lane -> F1 ride south to (47,46)
    f, fr, ok = route(f, fr, [(7, 41), (22, 41)], "to-F1")
    if alive(): f, fr, p = press(f, fr, "ACTION4", "F1 ride S")
    # (the south ring (52,36) is walled off from (47,46) — rows 45-49 cols 39-43; not needed at 2 px/press)
    # 3. SE loop up the east column to (32,46), then north into F3 -> ride west onto the shelf (27,36)
    if alive(): f, fr, ok = route(f, fr, [(47, 56), (32, 56), (32, 46)], "SE-loop")
    if alive(): f, fr, p = press(f, fr, "ACTION1", "F3 ride W")
    # 4. the color station (32,36) below the shelf: each touch cycles the held color; stop at the goal's
    if alive() and agent_pos(f) == (27, 36):
        for i in range(5):
            if key_color(f) == goal_color(f) or not alive(): break
            f, fr, p = press(f, fr, "ACTION2", "station touch %d" % (i + 1))
            if alive() and p == (32, 36): f, fr, p = press(f, fr, "ACTION1", "station back up")
        print("[station] key color %s goal %s bar %d actions %d" % (key_color(f), goal_color(f), bar_px(f), n_act))
        # 5. F4: east into (27,41) -> ride north to (7,41)
        if alive(): f, fr, p = press(f, fr, "ACTION4", "F4 ride N")
    else:
        print("[station] not on the shelf (at %s) — skipping the color station" % str(agent_pos(f)))
    # 6. north ring, then the west side: (37,16) -> west into F6 -> ride east to (37,26) under the stamp
    if alive():
        f, fr, got = collect_ring(f, fr, (17, 21)); print("[ring N] collected=%s bar %d pos %s" % (got, bar_px(f), agent_pos(f)))
    if alive(): f, fr, ok = route(f, fr, [(22, 16), (37, 16)], "to-F6")
    if alive(): f, fr, p = press(f, fr, "ACTION3", "F6 ride E")
    # 7. the stamp pocket (32,26): one entry sets the key's shape to the goal's
    if alive() and agent_pos(f) == (37, 26):
        G4, box4 = goal_box(f)
        for i in range(3):
            f, fr, p = press(f, fr, "ACTION1", "stamp entry %d" % (i + 1))
            k = match_rot(hud_glyph(f), G4) if G4 is not None else None
            print("[stamp] k=%s key color %s bar %d" % (k, key_color(f), bar_px(f)))
            if alive() and p == (32, 26): f, fr, p = press(f, fr, "ACTION2", "stamp back down")
            if k == 0 or not alive(): break
        # 8. F7 west to (42,11), then up the west side to the top corridor and push west into the box's east face
        if alive(): f, fr, p = press(f, fr, "ACTION2", "F7 ride W")
    else:
        print("[stamp] not under the pocket (at %s)" % str(agent_pos(f)))
    if alive():
        G4, box4 = goal_box(f)
        f, fr, ok = route(f, fr, [(42, 16), (37, 16), (22, 16), (17, 21), (7, 26), (7, 21)], "to-box")
        print("[pre-insert] pos %s bar %d key %s goal %s k=%s" % (agent_pos(f), bar_px(f), key_color(f), goal_color(f), match_rot(hud_glyph(f), G4) if G4 is not None else None))
        for i in range(3):
            if not alive(): break
            f, fr, p = press(f, fr, "ACTION3", "insert W %d" % (i + 1))
    print("[L4 end] pos %s bar %d key %s level %d actions %d" % (agent_pos(f), bar_px(f), key_color(f), LVL[0], n_act))

# ============================ L5 — stamp, color rides, the pendulum rotator, the elevator ===========
def zero_blobs(f):
    """every small 0/1 blob that contains a 0: the static keyhole(s) and any moving patch"""
    out = []
    lab, n = ndimage.label(np.isin(f[:HUD], [0, 1]))
    for i in range(1, n+1):
        ys, xs = np.where(lab == i)
        if (f[ys, xs] == 0).any() and len(ys) <= 30:
            out.append((int(round(ys.mean())), int(round(xs.mean()))))
    return out
def kk(f):
    G, _ = goal_box(f)
    return match_rot(hud_glyph(f), G) if G is not None else None

if LVL[0] == 4 and fr["state"] not in ("WIN", "GAME_OVER"):
    TARGET[0] = 5
    G5, box5 = goal_box(f)
    print("[L5 start] bar %d pos %s rings %s zeros %s box %s key color %s goal color %s k=%s fans %s"
          % (bar_px(f), agent_pos(f), rings(f), zero_blobs(f), box5, key_color(f), goal_color(f), kk(f), sorted(fan_cells(f))))
    np.save(os.path.join(HERE, "ls20_L5_start.npy"), f)
    alive = lambda: fr["state"] not in ("WIN", "GAME_OVER") and LVL[0] == 4
    # A. up the east side, ride west off (32,56), up to the NE landing (7,41)
    f, fr, ok = route(f, fr, [(37, 56)], "A1")
    if alive(): f, fr, p = press(f, fr, "ACTION1", "A ride W off (32,56)")
    if alive(): f, fr, ok = route(f, fr, [(22, 46), (17, 41), (7, 41)], "A2")
    # C. COLOR first (probed Sep 2: 12->9->14->8, three touches): ride south off (7,36) onto the shelf (27,36),
    #    touch the station (27,31), ride north off (27,41) back to (7,41). Ring (7,46) sits next to the landing.
    touched = 0
    while alive() and key_color(f) != goal_color(f) and touched < 4:
        if bar_px(f) <= 20 and (7, 46) in [snap(f, r) for r in rings(f)]:   # a cycle costs 16 px; the ring is 4 away
            f, fr, got = collect_ring(f, fr, (7, 46)); print("[ring NE] collected=%s bar %d" % (got, bar_px(f)))
            f, fr, ok = route(f, fr, [(7, 41)], "C-back")
        if agent_pos(f) != (7, 41): print("  [C] not at (7,41) (at %s)" % str(agent_pos(f))); break
        f, fr, p = press(f, fr, "ACTION3", "C ride S off (7,36)")
        if p != (27, 36): break
        f, fr, p = press(f, fr, "ACTION3", "C touch station")
        touched += 1
        if alive() and p == (27, 31): f, fr, p = press(f, fr, "ACTION4", "C back to shelf")
        if alive(): f, fr, p = press(f, fr, "ACTION4", "C ride N off (27,41)")
    print("[color] key color %s goal %s touches %d bar %d actions %d pos %s" % (key_color(f), goal_color(f), touched, bar_px(f), n_act, agent_pos(f)))
    if alive() and bar_px(f) <= 76 and (7, 46) in [snap(f, r) for r in rings(f)]:
        f, fr, got = collect_ring(f, fr, (7, 46)); print("[ring NE] collected=%s bar %d" % (got, bar_px(f)))
    # B. the SHAPE STAMP at (12,21), entered from below (17,21): each entry advances a 6-cycle of shapes;
    #    stop when the key's shape is the goal's (at any rotation). Refill at (12,11) when low.
    if alive(): f, fr, ok = route(f, fr, [(17, 41), (17, 21)], "B1")
    for i in range(7):
        if not alive() or kk(f) is not None: break
        if bar_px(f) <= 20 and (12, 11) in [snap(f, r) for r in rings(f)]:
            f, fr, ok = route(f, fr, [(12, 16)], "B-refill")
            f, fr, got = collect_ring(f, fr, (12, 11)); print("[ring W] collected=%s bar %d pos %s" % (got, bar_px(f), agent_pos(f)))
            f, fr, ok = route(f, fr, [(12, 16), (17, 16), (17, 21)], "B-back")
        if agent_pos(f) != (17, 21): print("  [B] not below the stamp (at %s)" % str(agent_pos(f))); break
        f, fr, p = press(f, fr, "ACTION1", "B stamp entry %d" % (i + 1))
        print("    shape %s k=%s" % (hud_glyph(f).tolist(), kk(f)))
        if alive() and kk(f) is None and p == (12, 21): f, fr, p = press(f, fr, "ACTION2", "B back below")
    print("[stamp] k=%s key color %s pos %s bar %d actions %d" % (kk(f), key_color(f), agent_pos(f), bar_px(f), n_act))
    if alive() and agent_pos(f) == (12, 21): f, fr, p = press(f, fr, "ACTION2", "B leave the stamp")
    if alive() and bar_px(f) <= 40 and (12, 11) in [snap(f, r) for r in rings(f)]:
        f, fr, ok = route(f, fr, [(17, 16), (12, 16)], "B-refill2")
        f, fr, got = collect_ring(f, fr, (12, 11)); print("[ring W] collected=%s bar %d pos %s" % (got, bar_px(f), agent_pos(f)))
        f, fr, ok = route(f, fr, [(12, 16), (17, 16), (17, 21)], "B-back2")
    # D. the ROTATOR lane (row 37, x 9..28) with the swinging patch; enter the west room by the ride off (27,21)
    if alive(): f, fr, ok = route(f, fr, [(17, 21), (22, 21)], "D1")
    if alive(): f, fr, p = press(f, fr, "ACTION2", "D ride W off (27,21)")
    if alive(): f, fr, ok = route(f, fr, [(32, 11)], "D2")
    print("[rotator] before: k=%s patch %s bar %d" % (kk(f), zero_blobs(f), bar_px(f)))
    want = 0
    # The patch is a keyhole that patrols x 16<->26 (16,21,26,21,16...), one step per agent MOVE (a
    # blocked press or ACTION5 freezes it). Probed Sep 2: crossing the lane at x=11 and waiting south of it
    # do nothing. Hypotheses: a rotation happens when agent and patch pass THROUGH each other (swap) or when
    # they land on the same cell (overlap). A small planner sets each up; live k tells which is real.
    LANE_Y, LANE_XS = 37, (11, 16, 21, 26)
    def patch_x(f):
        zs = [z for z in zero_blobs(f) if LANE_Y - 2 <= z[0] <= LANE_Y + 2]
        return snap(f, zs[0])[1] if zs else None
    def patch_next(px, pdir):
        nx = px + 5 * pdir
        if nx > 26: return 21, -1
        if nx < 16: return 21, 1
        return nx, pdir
    def lane_plan(ay, ax, px, pdir, event, max_depth=7):
        """shortest action list that produces `event` ('swap' or 'overlap') exactly once, with no other event"""
        from collections import deque as _dq
        start = (ay, ax, px, pdir)
        q = _dq([(start, [])]); seen = {start}
        while q:
            (y, x, p, d), acts = q.popleft()
            if len(acts) >= max_depth: continue
            for a, (dy, dx) in ACTS.items():
                ny, nx = y + dy, x + dx
                if ny == 32 and nx != 11: continue
                if ny == 37 and nx not in LANE_XS: continue
                if ny == 42 and not (11 <= nx <= 36): continue
                if ny == 47 and nx not in (16, 21, 26): continue
                if ny not in (32, 37, 42, 47): continue
                p2, d2 = patch_next(p, d)
                swap = (y == 37 and ny == 37 and nx == p and p2 == x)
                overlap = (ny == 37 and nx == p2)
                ev = "swap" if swap else "overlap" if overlap else None
                if ev == event: return acts + [a]
                if ev is not None: continue
                st = (ny, nx, p2, d2)
                if st not in seen: seen.add(st); q.append((st, acts + [a]))
        return None
    def patch_state(f):
        """(x, dir) of the patch now; when it is hidden under the agent (an overlap) it is AT the agent"""
        hist = [patch_x(g) for g in frames[-6:]]
        px = hist[-1]
        if px is None:
            a = agent_pos(f); px = a[1] if a else 21
        known = [h for h in hist[:-1] if h is not None]
        if px == 16: d = 1
        elif px == 26: d = -1
        elif known: d = 1 if px > known[-1] else -1 if px < known[-1] else 1
        else: d = 1
        return px, d
    def lane_run(f, fr, event, budget=8):
        """execute a planned event; report whether k changed"""
        px0, pdir = patch_state(f)
        pos = agent_pos(f)
        plan = lane_plan(pos[0], pos[1], px0, pdir, event)
        print("  [lane] agent %s patch %s dir %+d -> plan for %s: %s" % (str(pos), px0, pdir, event, plan))
        if not plan: return f, fr, False
        k0 = kk(f)
        for a in plan[:budget]:
            if not alive(): break
            f, fr, p = press(f, fr, a, "D %s" % event)
            print("    k=%s patch %s" % (kk(f), patch_x(f)))
        return f, fr, kk(f) != k0
    if alive() and kk(f) is not None:
        f, fr, got = collect_ring(f, fr, (47, 16)); print("[ring S] collected=%s bar %d pos %s" % (got, bar_px(f), agent_pos(f)))
        f, fr, ok = route(f, fr, [(42, 16)], "D-lane-entry")
        model = None
        for event in ("overlap", "swap"):          # Sep 2 live: OVERLAP rotates (+1), like a keyhole entry
            if not alive() or kk(f) == want: break
            f, fr, changed = lane_run(f, fr, event)
            if changed: model = event; break
        print("[rotator] model=%s k=%s pos %s bar %d" % (model, kk(f), agent_pos(f), bar_px(f)))
        tries = 0
        while alive() and model and kk(f) != want and tries < 4:
            f, fr, changed = lane_run(f, fr, model); tries += 1
        if alive() and agent_pos(f) and agent_pos(f)[0] == 37:
            f, fr, p = press(f, fr, "ACTION2", "D exit lane south")
    print("[rotator] after: k=%s pos %s bar %d actions %d" % (kk(f), agent_pos(f), bar_px(f), n_act))
    # E. south ring, the bottom corridor, the elevator cell (52,56): ride north up the chimney into the box
    if alive() and (47, 16) in [snap(f, r) for r in rings(f)]:
        f, fr, got = collect_ring(f, fr, (47, 16)); print("[ring S] collected=%s bar %d pos %s" % (got, bar_px(f), agent_pos(f)))
    if alive(): f, fr, ok = route(f, fr, [(52, 21), (52, 51)], "E1")
    if alive(): f, fr, p = press(f, fr, "ACTION4", "E elevator ride N")
    for i in range(3):
        if not alive(): break
        f, fr, p = press(f, fr, "ACTION1", "E insert N %d" % (i + 1))
    print("[L5 end] pos %s bar %d key %s k=%s level %d actions %d" % (agent_pos(f), bar_px(f), key_color(f), kk(f), LVL[0], n_act))
print("\nfinal: state=%s levels=%d actions=%d" % (fr["state"], fr.get("levels_completed", 0), n_act))
out = api("/api/scorecard/close", key, {"card_id": card_id})
print("scorecard:", json.dumps(out)[:400])
print("run held %d frames" % len(frames))

try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "arc3_trans.jsonl"), "w", encoding="utf-8") as _f:
        for r in _trans: _f.write(json.dumps(r) + "\n")
except Exception: pass
