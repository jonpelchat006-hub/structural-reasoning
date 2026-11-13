#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
play.py — LEARN BY PLAYING: the small eye (eye.py) starts blank and learns the game WHILE the
hand presses, the way Jonathan described it (Sep 3 2026): "at the start every move is a surprise
and I remember every one; later I only remember the surprises and the checkpoints; and we have
to do it by actually playing."

Every press:
  1. imagine — the eye predicts the next frame for every candidate press (available actions;
     for click games the clickables plus a few random cells) WITHOUT sending them.
  2. touch — send the press the eye is least sure about (curiosity: most predicted change and
     highest uncertainty, minus how often that press was already tried on this same screen).
  3. surprise — compare the real next frame with the eye's prediction on the cells that changed
     or were predicted to change: surprise = fraction wrong. At the start the eye is blank, so
     everything is a surprise and everything is remembered.
  4. remember — keep the transition if surprise > SURPRISE_KEEP, or it is one of the first
     presses, or the level changed (a checkpoint). Otherwise forget it (nothing happened that
     the eye did not already know).
  5. learn — a few gradient steps on the memory, more steps the bigger the surprise; the memory
     is sampled by surprise so the eye studies what it got wrong.
The recording rate over the run is printed in bins of 20 presses: it should fall as the eye
learns — that is the claim being measured — and levels cleared is the score.

Usage:  python play.py vc33 --presses 150            (one game, prints the run)
        python play.py --all --presses 150            (every public game -> D:\planet\eye\play_<stamp>.jsonl)
        python play.py --summary
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, random, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"
import induce, touch, pins, lines, relations, fence, rings, route, meter, magnet, diagonal, views, quat   # the world model, the touch graph, the pins, the lines, the relations (module level)
import pin_questions
import cube_router
from relation_guard import RelationAttempts
from play_metrics import action_records
SURPRISE_KEEP = 0.05
FIRST = 12                 # the first presses are always remembered
NC = 16


class _LevelTagged(list):
    """The experiments list, every entry stamped with the level it ran on (Oct 13 2026: Mika's journal
    needs to know which level an experiment belonged to, so what one life learned can steer the next)."""
    def __init__(s, level_fn):
        super().__init__(); s._lv = level_fn; s.hook = None       # hook: the mind hears each result as it happens (Oct 16)
    def append(s, e):
        if isinstance(e, dict):
            try: e.setdefault("level", int(s._lv()))
            except Exception: pass
        super().append(e)
        if s.hook is not None:
            try: s.hook(e)
            except Exception: pass


class Memory:
    def __init__(s): s.F0, s.F1, s.A, s.X, s.Y, s.H, s.W = [], [], [], [], [], [], []
    def add(s, f0, a, x, y, f1, h, w):
        s.F0.append(f0); s.F1.append(f1); s.A.append(a); s.X.append(x); s.Y.append(y); s.H.append(h.copy()); s.W.append(max(w, 0.02))
    def __len__(s): return len(s.A)
    def sample(s, k):
        w = np.array(s.W, float); w = w / w.sum()
        idx = np.random.choice(len(s.A), size=min(k, len(s.A)), replace=len(s.A) < k, p=w)
        return (np.array([s.F0[i] for i in idx]), np.array([s.F1[i] for i in idx]), np.array([s.A[i] for i in idx]),
                np.array([s.X[i] for i in idx]), np.array([s.Y[i] for i in idx]), np.array([s.H[i] for i in idx]))


class Player:
    def __init__(s, device=None):
        import torch, eye
        s.torch = torch; s.eye_mod = eye
        s.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        s.model = eye.make_model().to(s.device)
        s.opt = torch.optim.AdamW(s.model.parameters(), lr=1e-3, weight_decay=1e-4)
        s.mem = Memory(); s.tried = {}; s.steps = 0

    def imagine(s, f, cands, h=None):
        """predicted next frame + uncertainty for each candidate (a, x, y); h = the layers behind the screen"""
        torch = s.torch; s.model.eval()
        A = np.array([c[0] for c in cands]); X = np.array([c[1] for c in cands]); Y = np.array([c[2] for c in cands])
        F0 = np.repeat(f[None], len(cands), 0)
        H = np.repeat(h[None], len(cands), 0) if h is not None else None
        with torch.no_grad():
            x = s.eye_mod.encode(F0, A, X, Y, s.device, H)
            logits = s.model(x); p = torch.softmax(logits, 1)
            pred = p.argmax(1)
            ent = -(p * torch.log(p + 1e-8)).sum(1).mean((1, 2))                  # mean entropy per frame
            f0 = torch.as_tensor(F0, device=s.device)
            change = (pred != f0).float().sum((1, 2))
        return pred.cpu().numpy(), ent.cpu().numpy(), change.cpu().numpy()

    def choose(s, f, cands, rise=None, approach=None, h=None, tick=None, ops=None):
        """rise(frame) -> how far up the level this frame is; approach(frame) -> minus the distance from the
        mover to the unmoving unique thing (the goal read off the layers); None = curiosity only.
        ops = the world model (induce.Operators): where an action has a gated operator its prediction replaces
        the eye's, with no uncertainty — so curiosity flows to the actions no operator explains yet."""
        key = s._key(f, tick)
        if len(s.mem) < FIRST and not (ops is not None and ops.ops):   # the first touches: just touch, each thing once
            untried = [c for c in cands if s.tried.get((key, c), 0) == 0]
            c = random.choice(untried or cands); return c, None, "touch eye"
        pred, ent, change = s.imagine(f, cands, h)
        src = ["eye"] * len(cands)
        if ops is not None:
            for i, (a, x, y) in enumerate(cands):
                if ops.known(a):
                    q = ops.predict(f, a, x, y)
                    if q is not None: pred[i] = q; ent[i] = 0.0; change[i] = float((q != f).sum()); src[i] = "op"
        curiosity = ent / (ent.max() + 1e-8) + 0.5 * np.minimum(change, 200) / 200.0
        tried = np.array([s.tried.get((key, c), 0) for c in cands])
        score = 0.25 * curiosity - 0.6 * tried; why = []
        if rise is not None:
            here = rise(f); gain = np.array([rise(pr) - here for pr in pred], float)
            if gain.max() > 0: score = score + gain / gain.max(); why.append("rise %+d" % int(gain.max()))
        if approach is not None:
            here = approach(f)
            if here is not None:
                ap = np.array([(approach(pr) if approach(pr) is not None else here) - here for pr in pred], float)
                if ap.max() > 0: score = score + ap / ap.max(); why.append("near %+d" % int(ap.max()))
        if not why: score = curiosity - 0.6 * tried; why = ["curious"]
        i = int(np.argmax(score)); return cands[i], pred[i], " ".join(why) + " " + src[i]

    def surprise(s, f, pred, g, tick=None):
        """1 - F1 between what the eye said would change (to which color) and what did, ignoring the
        tick region (the budget bar / counter that drains a cell or two every press)"""
        if pred is None: return 1.0
        ch = (g != f); pch = (pred != f)
        if tick is not None: ch = ch & ~tick; pch = pch & ~tick
        if not ch.any() and not pch.any(): return 0.0
        tp = int((ch & pch & (pred == g)).sum()); fp = int(pch.sum()) - tp; fn = int(ch.sum()) - int((ch & pch & (pred == g)).sum())
        return float(1.0 - (2 * tp / (2 * tp + fp + fn) if tp else 0.0))

    def learn(s, steps, bs=16):
        torch = s.torch; s.model.train()
        for _ in range(steps):
            F0, F1, A, X, Y, H = s.mem.sample(bs)
            x = s.eye_mod.encode(F0, A, X, Y, s.device, H)
            y1 = torch.as_tensor(F1, device=s.device).clamp(0, NC - 1); y0 = torch.as_tensor(F0, device=s.device).clamp(0, NC - 1)
            w = 1.0 + 8.0 * (y1 != y0).float()
            loss = (torch.nn.functional.cross_entropy(s.model(x), y1, reduction="none") * w).sum() / w.sum()
            s.opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(s.model.parameters(), 1.0); s.opt.step()
            s.steps += 1
        return float(loss.detach())

    @staticmethod
    def _key(f, tick=None):
        """the screen's identity, ignoring the tick region (the bar drains every press; the screen is the same)"""
        if tick is not None and tick.any(): f = f.copy(); f[tick] = 0
        return hashlib.md5(f.tobytes()).hexdigest()[:12]


def topology(f, nchg, tick, agent_color, minsize=2, maxsize=120):
    """THE LAYERS BEHIND THE SCREEN: walls are cells that never changed (one thin layer of color); the mover is
    the color that keeps adding layers; the goal is a thing that never moves either but shares its color with
    nothing else — not the border, not the background, not the mover. Returns the goal blobs' centres."""
    from scipy import ndimage
    vals, counts = np.unique(f, return_counts=True); count = dict(zip(vals.tolist(), counts.tolist()))
    border = set(np.unique(np.concatenate([f[0], f[-1], f[:, 0], f[:, -1]])).tolist())
    goals = []
    for v, c in count.items():
        if c > maxsize or v in border or v == agent_color or c > 900: continue
        m = (f == v) & (nchg == 0) & ~tick
        lab, n = ndimage.label(m)
        for i in range(1, n + 1):
            ys, xs = np.where(lab == i)
            if minsize <= len(ys) <= maxsize: goals.append((float(ys.mean()), float(xs.mean()), int(v), len(ys)))
    return goals


def mover_pos(fr, f, nchg, agent_color):
    """centre of the mover in a (real or imagined) frame: its color, on cells that have layers or just changed"""
    if agent_color is None: return None
    m = (fr == agent_color) & ((nchg >= 1) | (fr != f))
    if not m.any(): return None
    ys, xs = np.where(m); return float(ys.mean()), float(xs.mean())


def plan_step(ops, f, visited, key_fn, approach=None, depth=8, max_states=400):
    """THE PROPOSER over the world model (layer 3): breadth-first over the gated operators to the nearest state
    this run has not stood in yet — among equals, the one nearest a goal. Returns (first action, path length)
    or None when every reachable state within `depth` has been visited. Replanned every press, so an operator
    that is wrong costs one press, not a plan."""
    acts = [a for a in ops.ops if a != 6]
    if not acts: return None
    frontier = [(f, [])]; seen = {key_fn(f)}; n = 0; best = None
    for d in range(depth):
        nxt = []
        for g, path in frontier:
            for a in acts:
                q = ops.predict(g, a)
                if q is None or np.array_equal(q, g): continue
                k = key_fn(q)
                if k in seen: continue
                seen.add(k); n += 1; nxt.append((q, path + [a]))
                if k not in visited:
                    sc = approach(q) if approach is not None else None
                    cand = (d, -(sc if sc is not None else 0.0), path + [a])
                    if best is None or cand[:2] < best[:2]: best = cand
            if n >= max_states: break
        if best is not None: return best[2][0], len(best[2])
        frontier = nxt
        if not frontier or n >= max_states: break
    return None


class Register:
    """THE BUDGET, read off the register (Jonathan, Sep 4: "recognize when the budget will run out"): fill = cells of
    the bar's colour inside the register band, drain = the median cells lost per press; presses left = fill / drain.
    The bar's colour is the one that loses cells on the most presses (refills are jumps up and are ignored)."""
    def __init__(s): s.band = None; s.colour = None; s.drain = None

    def fit(s, band, pairs):
        if band is None or not band.any() or len(pairs) < 6: return s
        s.band = band; best = None
        for c in np.unique(np.concatenate([p[0][band] for p in pairs[:5]])):
            drops = [int((p[0][band] == c).sum()) - int((p[1][band] == c).sum()) for p in pairs]
            down = [d for d in drops if d > 0]
            if best is None or len(down) > best[0]: best = (len(down), int(c), float(np.median(down)) if down else None)
        if best and best[2]: s.colour, s.drain = best[1], best[2]
        return s

    def fill(s, f):
        if s.band is None or s.colour is None: return None
        return int((f[s.band] == s.colour).sum())

    def remaining(s, f, since=0, deaths=()):
        """presses left. From the bar: fill / drain. From the deaths (Jonathan, Sep 4: learn the budget from the
        deaths directly): each death gives fill-at-segment-start / presses-to-death, a drain the bar reading may
        have missed (a cost the bar does not show); the stricter of the two wins. With no readable bar, the deaths
        alone give the life length, and what is left is that minus the presses since the segment began."""
        fill = s.fill(f)
        rem_bar = (fill / s.drain) if (fill is not None and s.drain) else None
        rem_death = None
        d_fill = [f0 / n for f0, n in deaths if f0 and n]
        d_len = [n for f0, n in deaths if n]
        if fill is not None and d_fill: rem_death = fill / max(d_fill)
        elif d_len: rem_death = float(min(d_len)) - since
        if rem_bar is None: return rem_death
        if rem_death is None: return rem_bar
        return min(rem_bar, rem_death)


def body_of(ops, f):
    """the body in a frame: located by the most trusted displace operator; failing that, its colours"""
    disps = sorted(((ops.bond.get(a, 0), a, op) for a, op in ops.ops.items() if isinstance(op, induce.Displace)), key=lambda t: -t[0])
    for _, a, op in disps:
        S = op.locate(f)
        if S is not None: return S
    for _, a, op in disps:
        m = np.isin(f, sorted(op.colors))
        if m.any(): return m
    return None


def contact_tests(ops, cells, tried_sides=None):
    """goal tests for an experiment: the body touches the object (adjacent) on a side whose step lands in it and
    has not been tried; failing that, lines up with it (sp80's bar under the token: the act button works on the
    column, the bar can never touch the token)"""
    from scipy import ndimage
    ring = ndimage.binary_dilation(cells, iterations=1) & ~cells
    def adjacent(q):
        """within one move of the thing: a displace step from here lands on it (a keyhole is a floor feature the
        key drives onto, never one cell away on a 5-lattice); with no movement operators, touching its ring"""
        b = body_of(ops, q)
        if b is None: return False
        if (b & cells).any(): return False                         # already on it: not a contact, a stand
        disp = [(a_, op) for a_, op in ops.ops.items() if isinstance(op, induce.Displace)]
        if not disp: return bool((b & ring).any())
        for a_, op in disp:
            if tried_sides is not None and a_ in tried_sides: continue
            if (induce.shifted(b, *op.d, fill=False) & cells).any(): return True
        return False
    def aligned(q):
        b = body_of(ops, q)
        return b is not None and any(touch.span_overlap(b, cells))
    return adjacent, aligned


def plan_to(ops, f, goal, key_fn, depth=40, max_states=2500, avoid=None):
    """breadth-first over the trusted operators to the nearest state where goal(frame) holds. Returns the whole
    action path ([] when already there) or None when unreachable. One search per experiment; the path is followed
    and only re-planned when the world deviates from the operators' prediction."""
    acts = [a for a in ops.ops if a != 6 and ops.known(a)]
    if not acts: return None
    if goal(f): return []
    frontier = [(f, [])]; seen = {key_fn(f)}; n = 0
    for d in range(depth):
        nxt = []
        for g, path in frontier:
            for a in acts:
                q = ops.predict(g, a)
                if q is None or np.array_equal(q, g): continue
                k = key_fn(q)
                if k in seen: continue
                seen.add(k); n += 1
                if avoid is not None:
                    b_ = body_of(ops, q)
                    if b_ is not None and (b_ & avoid).any(): continue           # lava: the source that would undo the match
                if goal(q): return path + [a]
                nxt.append((q, path + [a]))
            if n >= max_states: break
        frontier = nxt
        if not frontier or n >= max_states: break
    return None


def closure(ops, f, key_fn, cap=3000, ever=None, avail=()):
    """THE SHAPE OF THE MODEL (Jonathan, Sep 4): every state the operators can reach from here. Its size is the
    circle; the visited set is the slice drawn out of it; a newly gated button or a surprise that gates one makes
    the circle grow. Measured with every operator EVER gated on this level (`ever`), so a bond dipping for one
    sleep does not collapse the circle. Also returns THE RING: the states where going round returns nothing —
    an operator abstained or refused, or a button the level offers has no operator — the wall the next circle
    starts from. Returns (keys, size, radius, ring_frames)."""
    import copy
    view = ops
    if ever:
        view = copy.copy(ops); view.ops = dict(ever); view.bond = {a: 1.0 for a in ever}
    acts = [a for a in view.ops if a != 6 and view.known(a)]
    gaps = [a for a in avail if a != 6 and a not in acts]
    seen = {key_fn(f)}; frontier = [f]; depth = 0; radius = 0; walls = []; open_ = []; ring_keys = set()
    while frontier and len(seen) < cap and acts:
        nxt = []
        for q in frontier:
            refused = False
            for a in acts:
                r = view.predict(q, a)
                if r is None or np.array_equal(r, q): refused = True; continue
                k = key_fn(r)
                if k in seen: continue
                seen.add(k); nxt.append(r)
                if len(seen) >= cap: break
            kq = key_fn(q)
            if kq not in ring_keys and len(walls) + len(open_) < 300:
                if refused: walls.append(q); ring_keys.add(kq)          # a wall: the operators return nothing here
                elif gaps: open_.append(q); ring_keys.add(kq)           # an unexplained button waits here
            if len(seen) >= cap: break
        frontier = nxt; depth += 1
        if nxt: radius = depth
    return seen, len(seen), radius, walls + open_


BASELINES = os.path.join(OUT, "baselines.json")      # game -> level_baseline_actions, learned from closed scorecards


def load_baselines(path=None):
    try:
        with open(path or BASELINES, encoding="utf-8") as src: return json.load(src)
    except Exception: return {}


def front_prediction(ops, f, a, x, y):
    """what the thin lines in front of the screen say this press will do: the trusted operator, else the hypothesis
    on trial; None when nothing in front has an answer (then everything that changes is water)"""
    if ops.known(a): return ops.predict(f, a, x, y)
    h = ops.hyp.get(a)
    if h is not None and h.applies(f, a, x, y):
        P = h.predict(f, x, y, a); Q = f.copy(); Q[ops.mask] = P[ops.mask]; return Q
    return None


def antenna(water, cells, empty_frac):
    """THE ANTENNA (Jonathan, Sep 5): the water piled up near a thing, weighted by how empty its pins are — where the
    colours behind the screen leave a spike poking out that a hypothesis should fill"""
    from scipy import ndimage
    near = ndimage.binary_dilation(cells, iterations=2)
    return float(water[near].sum()) * (0.5 + empty_frac)


def candidates(f, avail, ambient=None):
    from collect import clickables
    cands = [(a, -1, -1) for a in avail if a != 6]
    if 6 in avail:
        for x, y in clickables(f, ambient, cap=24): cands.append((6, x, y))
        for _ in range(4): cands.append((6, random.randrange(64), random.randrange(64)))
    return cands


def play_game(gid, key, presses=150, device=None, log=print, save=True, use_rise=True, use_ops=True, use_prior=True, refit_every=20, hard_cap=600, use_cubes=True, use_relation_guard=True, transport=None, output_dir=None, seed=None, mind=None):
    # mind (Oct 13 2026): an optional MIND riding this body (mika_mind.MikaMind). Before each experiment is picked it may
    # re-order the candidates with mind.order(goals, level, frame); it never adds or removes one. None = the planet alone.
    OUT = os.path.abspath(output_dir or globals()["OUT"])
    BASELINES = os.path.join(OUT, "baselines.json")
    os.makedirs(OUT, exist_ok=True)
    if seed is not None:
        random.seed(seed); np.random.seed(seed)
        import torch
        torch.manual_seed(seed)
    auto = (presses == 0)                                 # --presses auto: run until the slice covers the circle
    if auto: presses = hard_cap
    from arc3_client import api, frame_np
    api = transport if transport is not None else api
    import induce, touch
    P = Player(device)
    # THE WORLD MODEL (induce.py): gated operators from this game's prior touches, refitted as the run grows
    ops = induce.Operators(); hist = []; prior = []
    if use_ops:
        pp = os.path.join(OUT, f"{gid.split('-')[0]}.npz")
        if use_prior and os.path.exists(pp):
            g_ = induce.load_game(pp)
            if g_: prior = g_[0] + g_[1]
        if prior:
            ops.fit(prior); log(f"  operators from {len(prior)} prior touches: {ops.summary() or 'none gated'}")
    card = api("/api/scorecard/open", key, {"tags": ["play-eye"]}); cid = card.get("card_id")
    guid = {}
    def send(act, x=None, y=None):
        body = {"game_id": gid, "card_id": cid, "guid": guid.get("v")}
        if x is not None: body.update(x=int(x), y=int(y))
        last = None
        for t in range(4):
            try:
                fr = api(f"/api/cmd/{act}", key, body); guid["v"] = fr["guid"]; return fr
            except Exception as e:
                last = e; time.sleep(2 + 3 * t)
        raise last
    frames, rec, t0 = [], [], time.time()
    try:
        fr = send("RESET"); f = frame_np(fr); frames.append(f)
        avail = [int(a) for a in (fr.get("available_actions") or [1, 2, 3, 4, 5, 6]) if 1 <= int(a) <= 6]
        lvl = int(fr.get("levels_completed", 0) or 0); wins = fr.get("win_levels")
        log(f"{gid}: {wins} levels, available {avail}, eye on {P.device}")
        n = 0; kept = 0; resets = 0; changed = 0; change_count = np.zeros_like(f, dtype=int); ambient = None
        visited = set(); probed = set()                      # places this run has stood in / probed an unexplained button at
        level_press = []                                     # press index of the last level change (an early refit follows)
        # RESETS AS CHECKPOINTS (Jonathan, Sep 4): a reset restarts the level, keeps the levels won, costs no life, and
        # every action already spent still counts — so it is the cheaper death. The first death teaches the budget
        # (life_len presses); after that the agent resets when the next target is farther than the presses left in
        # this life, or when nothing new is reachable from here. Places stay visited across resets, so the planner
        # walks the known path back out to the frontier by itself. A reset is not a press.
        life_len = None; since = 0; vresets = 0
        # THE SEGMENT (Jonathan, Sep 4): place the reset where the budget will run out and feel it out — a death
        # before the planned reset means it was placed too far (margin grows), clean resets shrink it back. Each
        # segment lays down one section of the eventual route; until a section reaches the goal, explore.
        reg = Register(); margin = 2; clean = 0; segments = []; seg_start = 0; seg_budget = None
        deaths_lv = []; seg_fill = None; last_sleep = 0       # this level's deaths as (fill at segment start, presses to death)
        shape = []; last_size = 0; stop_reason = None; shape_level_start = 0   # the closure measured at every sleep; per-level window for the stop rule
        ever = {}; ever_keys = set()                          # every operator ever gated on this level; every state ever reachable
        ring = []; ring_mode = False; ring_target = None; ring_probed = set(); ring_done = False; gaps_found = []
        refills = {}                                          # place key -> frame where the register jumped up (a subgoal: grow the ring)
        hypotheses_promoted = []
        reg_pins = pins.Pins()                                # THE PIN REGISTRY: a container per control x thing, asking "what is this?"
        level_lines = []; lines_log = []                     # PINS THAT CONNECT PIXELS: the objects' own lines (fans), learned and generalised
        rels = []; rel = None; rel_log = []; rel_seen = False   # THE RELATION LAYER: source -> region -> target; the active "touch until it matches" loop
        relation_attempts = RelationAttempts()
        rel_prior = []                                       # relations from the last level, carried by colour (the rotator)
        ring_rel = None; ring_log = []                       # THE RING RELATION: the register's colour on the floor refills the bar
        water = np.zeros_like(f, dtype=float); explained_mass = 0.0; unexplained_mass = 0.0; antennas = []   # THE WATER MAP: unexplained change per cell
        residue = []; cause = {}                             # THE VOID LINE (Jonathan, Sep 5): per press, the residue after prediction and observation cancel;
                                                             # credited to the thing the body acted on that press, not the floor the residue landed on
        fen = fence.Fence(f.shape); fen_log = []              # THE FLOOR FLOW FIELD (Jonathan, Sep 5): middle pins, border pins, the colour rule, the openings
        fen.prior = fence.load_rules(os.path.join(OUT, f"fence_rules_{gid.split('-')[0]}.json")) if use_prior else {}
        if fen.prior: log(f"  fence: {len(fen.prior)} colour rules carried in from the last run of this game")
        route_plan = None; bar_full_cells = 0; route_dumped = False   # THE ROUTE WITH REFILL POINTS: this life's stops, planned over the rings
        met = meter.Meter(); met_log = []                     # THE BUDGET METER AS PINS (Jonathan, Sep 6): the bar's cells lay their pins down as it drains
        mags = None; mag_log = []                             # THE CENTRE MAGNETS (Jonathan, Sep 6): every thing's response table, rebuilt from the pins that broke into it
        diag = None; diag_log = []                            # THE DIAGONAL PINS (Jonathan, Sep 6): from a foot on the screen to a coordinate on the back wall, with an eye each
        question_queue = pin_questions.QuestionQueue(f"{gid}:level:{lvl}")
        vw = None; vw_log = []                                # THE THREE VIEWS (Jonathan, Sep 7): one memory per pixel, seen by the side eye, the front eye and the pins' eyes
        depth = {1: 0.0, 2: 0.0, 3: 0.0, 0: 0.0}; depth_log = []   # THE DEPTH COUNT (Jonathan, Sep 7): change explained at layer 1 (the pixel: an operator or the fence), 2 (the thing: a magnet),
                                                                 # 3 (the relation: a diagonal pin's region), or 0 — wall to wall, a short circuit, the water

        def fence_attach():
            for op_ in list(ops.ops.values()) + list(ops.hyp.values()):
                if isinstance(op_, induce.Displace): op_.fence = fen

        def fence_ground():
            fills = [op_.fill for op_ in ops.ops.values() if isinstance(op_, induce.Displace) and op_.ok]
            return fence.ground_of(start, body_of(ops, start), fills[0] if fills else None)

        def fence_observe(f0, g0, a0):
            op_ = ops.ops.get(a0)
            if not isinstance(op_, induce.Displace) or not op_.ok: return None
            r_ = fen.observe(f0, g0, op_.locate(f0), op_.locate(g0), op_.fill, d_expected=op_.d)
            if r_ is not None: fen.compile(fence_ground())
            return r_
        baselines = load_baselines(BASELINES).get(gid.split("-")[0], []) if use_prior else []
        # THE EXPERIMENT LOOP and THE SLEEP (Jonathan, Sep 4): the touch graph ranks candidates (things pointed at by a
        # state or level edge, then things never touched); an experiment walks the body to one, tries the unexplained
        # buttons and a bump there; a level ends it, a changed board is kept, nothing means reset and next candidate.
        # A reset or an undo is where the consolidation happens: operators refit, this level's register re-read from
        # its own presses, the touch graph rebuilt, the candidates re-ranked. That is the sleep.
        level_hist = []; level_lv = []; graph = None; goals = []; done_exp = set(); exp = None; experiments = _LevelTagged(lambda: lvl)
        if mind is not None and hasattr(mind, "observe"): experiments.hook = mind.observe
        level_touch = []                                     # per press: was it a relation touch (meant to change the body)? kept out of the operator refit
        retry_at = {}                                        # thing id -> the press after which an unreachable thing is asked again
        prev_level_hist = []                                 # the last level's presses: a button's law until this level has its own

        def sleep(reason):
            nonlocal reg, graph, goals, last_size, ever, rels, antennas, cause, fen, ring_rel, mags, diag, vw   # antennas: the water's spikes; cause: whose residue it is; the magnets, pins and views are the level's, not the sleep's
            t1 = time.time()
            # OPERATORS ARE PER LEVEL: the prior (recorded on level 1) counts only on level 1; a later level is fit from
            # its own presses. Fitting on both levels at once gates nothing (the bounds contradict) and made the
            # operators swing with whichever level's presses dominated. Until a new level has 8 presses, the old
            # operators stand with their bonds reset.
            plain_ = [h_ for h_, t_ in zip(level_hist, level_touch) if not t_]     # the relation touches are the relation's, not the operators'
            # THE LAST LEVEL'S LAW UNTIL THIS LEVEL SPEAKS (Sep 6): a button this level has not pressed eight times keeps the last
            # level's presses in its fit (ls20 level 2: the walk to the keyhole never needs 'left', so 'left' was dropped, and both
            # rings — to the left — were unreachable in the model)
            from collections import Counter as _C
            have_ = _C(h_[2] for h_ in plain_)
            carry_ = [h_ for h_ in prev_level_hist if have_.get(h_[2], 0) < 8] if lvl > 0 else []
            fit_data = (prior if lvl == 0 else []) + carry_ + plain_
            if len(fit_data) >= 8: ops.fit(fit_data, recent=plain_ if plain_ else fit_data)
            # THE FENCE is laid again from this level's own presses with the operators as they stand now, then
            # compiled onto the level's ground: the same colours far away get the same answer
            exempt_, prior_ = fen.exempt, fen.prior; fen = fence.Fence(f.shape); fen.exempt = exempt_; fen.prior = prior_   # what a relation opened stays open; the rules persist
            for f0_, g0_, a0_, _x, _y in level_hist: fence_observe(f0_, g0_, a0_)
            fen.compile(fence_ground()); fence_attach()
            # THE FENCE VETOES THE FLOOR (Sep 6): one recorded right-move into a colour-4 patch made walls floor for the planner and its
            # states exploded; a colour the fence has bumped five times and never passed is not floor on one press's word
            vetoed_ = set()
            for op_ in list(ops.ops.values()) + list(ops.hyp.values()):
                if not isinstance(op_, induce.Displace): continue
                for c_ in list(op_.floor):
                    ev_ = [v_ for (nn_, ff_, kk_), v_ in list(fen.rule.items()) + list(fen.prior.items()) if ff_ == c_ and nn_ == op_.fill]
                    blocks_ = sum(v_[1] for v_ in ev_); passes_ = sum(v_[0] for v_ in ev_)
                    if blocks_ >= 5 and passes_ <= 1: op_.floor.discard(c_); vetoed_.add(c_)
            if vetoed_: log(f"  fence: vetoed floor colour(s) {sorted(vetoed_)} — the walls say no")
            # THE LINES: every ride an operator learned is a line owned by the object beside the fan cell; the line
            # generalises to every object of the same colour and orientation; the generalised lines go back into
            # every movement operator as rides, so the closure includes fans never ridden. The chain's fan map checks it.
            try:
                disp_ops = [op for op in ops.ops.values() if isinstance(op, induce.Displace) and op.ok]
                rides = {}
                for op in disp_ops: rides.update(getattr(op, "rides", {}) or {})
                if disp_ops and rides:
                    floor = set(); size = 5
                    for op in disp_ops: floor |= op.floor
                    size = int(round(max(op.size for op in disp_ops) ** 0.5)) or 5
                    q = max(abs(disp_ops[0].d[0]), abs(disp_ops[0].d[1])) or 5
                    body_lines = lines.learn(start, {(k[0] + size // 2, k[1] + size // 2): v for k, v in rides.items()}, floor, q, ops.amb, size)
                    gen = lines.generalise(start, body_lines, floor, q, ops.amb, size)
                    level_lines = body_lines + gen
                    seeded = lines.seed_rides(ops, gen, size)
                    chk = lines.oracle_check(start, level_lines, q)
                    lines_log.append({"press": n, "learned": len(body_lines), "generalised": len(gen), "seeded": seeded, "oracle": chk})
                    log(f"  lines: {len(body_lines)} learned from rides, {len(gen)} generalised to like objects, {seeded} seeded as rides | "
                        f"chain oracle: {chk['oracle_fans']} fans, precision {chk['precision']}, recall {chk['recall']}")
            except Exception as e:
                log(f"  lines failed: {str(e)[:100]}")
            if len(level_hist) >= 8:
                band = induce.ambient_mask(level_hist) | induce.tick_region(level_hist)   # this level's own register
                reg = Register().fit(band if band.any() else ops.amb, level_hist)
                if met.band is None and reg.colour is not None and reg.band is not None:
                    try:
                        met.fit(reg.band, reg.colour, level_hist[0][0])            # the pins stand at the level's start frame
                        for f0_, g0_, a0_, _x, _y in level_hist:                   # ...and lay down over its presses
                            b0_, b1_ = body_of(ops, f0_), body_of(ops, g0_)
                            _p_ = lambda m_: None if m_ is None or not m_.any() else tuple(np.argwhere(m_).min(axis=0).tolist())
                            moved_ = _p_(b0_) is not None and _p_(b1_) is not None and _p_(b0_) != _p_(b1_)
                            met.predict(moved_); met.observe(f0_, g0_, moved_)
                    except Exception as e_:
                        log(f"  meter failed: {str(e_)[:80]}")
                try:
                    graph = touch.build([h + (lv,) for h, lv in zip(level_hist, level_lv)], log=lambda *_: None, ops=ops, key_fn=vkey)
                    if graph:
                        reg_pins.open([a_ for a_ in avail if a_ != 6], graph["objects"])
                        for e_ in graph["edges"]: reg_pins.fill(e_["button"], e_["object"], e_["effect"], e_.get("place"))
                        goals = reg_pins.candidates(exclude=done_exp) or touch.candidates(graph, exclude=done_exp)
                        goals = [o for o in goals if retry_at.get(o["id"], 0) <= n]      # not yet: it was unreachable a moment ago
                        # THE ANTENNAS: the things where the water piled up and the pins are empty rank first within their tier
                        def _tier(o):
                            ps = [p_ for (c_, t_), p_ in reg_pins.pins.items() if t_ == o["id"]]
                            return 0 if any(p_["state"] in ("level", "state") for p_ in ps) else 1
                        def _empty(o):
                            ps = [p_ for (c_, t_), p_ in reg_pins.pins.items() if t_ == o["id"]]
                            return (sum(1 for p_ in ps if p_["state"] == "empty") / len(ps)) if ps else 1.0
                        # THE CAUSE: each press's residue is credited to the thing(s) its touch edge names — the keyhole, not the
                        # corridor the residue landed on. A press with no edge keeps its residue on the cells (the floor's own water).
                        cause = {}
                        named = {}
                        for e_ in graph["edges"]:
                            # a 'pass' names the floor the body walked over, not a cause; the residue of a press goes to the
                            # things it touched that did something or refused (state, level, refusal, nothing)
                            if e_.get("press") is not None and e_.get("effect") != "pass": named.setdefault(e_["press"], set()).add(e_["object"])
                        def _floorish(t_):
                            ps_ = [p_["state"] for (c_, tt_), p_ in reg_pins.pins.items() if tt_ == t_]
                            return bool(ps_) and sum(1 for s_ in ps_ if s_ == "pass") >= 0.5 * len(ps_)
                        for i_, r_ in enumerate(residue):
                            if r_ <= 0 or i_ not in named: continue
                            things_ = [t_ for t_ in named[i_] if not _floorish(t_)] or list(named[i_])   # the floor shares no credit while a real thing is named
                            share = r_ / len(things_)
                            for t_ in things_: cause[t_] = cause.get(t_, 0.0) + share
                        # the antennas are measured over EVERY thing on the level, not only the current candidates (marker: all-things antennas):
                        # the cause first, the cell water near the thing as the tie-breaker
                        def _ant(o):
                            ps_ = [p_["state"] for (c_, t_), p_ in reg_pins.pins.items() if t_ == o["id"]]
                            if ps_ and all(s_ in ("pass", "empty") for s_ in ps_) and any(s_ == "pass" for s_ in ps_): return 0.0   # floor: walked over, never a cause
                            return (cause.get(o["id"], 0.0) + 0.25 * antenna(water, o["cells"], 0.0)) * (0.5 + _empty(o))
                        scored = [(_tier(o), -_ant(o), o) for o in goals]
                        scored.sort(key=lambda t_: (t_[0], t_[1]))
                        goals = [o for _, _, o in scored]
                        # THE OPENINGS: where the trail's chain of pins stops with no answer, the body goes and asks
                        # (after the things whose pins already hold a state or a level; before the never-touched things and the ring)
                        opens_ = [o for o in fen.opening_objects(fence_ground()) if o["id"] not in done_exp]
                        # (Jonathan, Sep 5) the openings go AHEAD of the never-touched things: close the circuit first
                        t0_ = [o for o in goals if _tier(o) == 0]; t1_ = [o for o in goals if _tier(o) != 0]
                        goals = t0_ + opens_ + t1_
                        allsc = sorted(((_ant(o), _empty(o), o["id"], cause.get(o["id"], 0.0)) for o in graph["objects"]
                                        if not o["id"].startswith(("chg", "place", "wall")) and o["id"] != "bound"), reverse=True)
                        antennas = [{"id": i_, "antenna": round(a_, 1), "empty": round(e_, 2), "caused": round(c_, 1)} for a_, e_, i_, c_ in allsc[:5] if a_ > 0]
                        floor_ = set()
                        for op_ in ops.ops.values():
                            if isinstance(op_, induce.Displace): floor_ |= op_.floor
                        rels = relations.find(f, graph["edges"], level_hist, graph["objects"], body_of, ops.amb, ops, floor_)
                        want_c_ = False
                        if rel_prior and mind is not None and hasattr(mind, "want_carried"):
                            try: want_c_ = bool(mind.want_carried(lvl, rels))      # Oct 27: her equation needs the carried turn
                            except Exception: want_c_ = False
                        if rel_prior and (want_c_ or not any(r_["targets"] for r_ in rels)):
                            carried = relations.carry(rel_prior, f, graph["objects"], floor_)
                            if carried:
                                rels = [r_ for r_ in rels if r_["targets"]] + carried
                                for r_ in carried: log(f"  relation carried from the last level by colour: {r_['src']} -> region rows {r_['region'][0]}-{r_['region'][1]} cols {r_['region'][2]}-{r_['region'][3]} -> {r_['targets'][0]['id']}")
                        # THE CENTRE MAGNETS: one response table per thing (walls included), a kind, a contradiction, and the key of each
                        try:
                            wall_things = [t_ for t_ in touch.objects_of(start, floor_ - {0, 1, 5, 11}, [], ops.amb if ops.amb is not None else np.zeros_like(f, bool)) if t_["n"] >= 4
                                           and t_["id"] not in {o_["id"] for o_ in graph["objects"]}]
                            things_ = [o_ for o_ in graph["objects"] if not o_["id"].startswith(("chg", "place", "wall")) and o_["id"] != "bound"] + wall_things
                            band_ = (ops.amb if ops.amb is not None else np.zeros_like(f, bool)) | (reg.band if reg.band is not None else np.zeros_like(f, bool))
                            body_all_ = np.zeros_like(f, bool)
                            for f0_, g0_, *_ in level_hist:
                                for fr_ in (f0_, g0_):
                                    b_ = body_of(ops, fr_)
                                    if b_ is not None: body_all_ |= b_
                            mags = magnet.Magnets().build(level_hist, things_, body_of, ops, band=band_, levels=level_lv + [level_lv[-1] if level_lv else 0])
                            log("  " + mags.summary(level_hist, exclude=band_, body=body_all_))
                            # THE ACT BUTTON IS A COMPLEX MAGNET FROM THE START (Jonathan, Sep 6): we don't know what it does either;
                            # where things expect something complex — a door, or nothing on them yet — it is tried there first
                            acts_ = [t_ for t_ in mags.things if t_.startswith("ACTION")]
                            if acts_: log("  buttons: " + "; ".join(f"{t_} {mags.kind(t_)} " + ", ".join(f"{k_[1]}: " + "/".join(f"{v_[o_]} {o_}" for o_ in ("level", "state", "pass", "refuse") if v_[o_]) for k_, v_ in mags.table[t_].items()) for t_ in acts_))
                            exp_order_ = {t_: i_ for i_, t_ in enumerate(mags.expecting())}
                            # the fence's order stands (Jonathan, Sep 5: the openings ahead of the untouched things — close the circuit first);
                            # the magnets order the things AFTER the openings (Sep 6: putting the empties first cost ls20 its level twice)
                            goals = sorted(goals, key=lambda o_: (0 if _tier(o_) == 0 else 1, 0 if str(o_["id"]).startswith("open@") else 1, exp_order_.get(o_["id"], 99)))
                            st_ = mags.stats(level_hist, exclude=band_, body=body_all_); mag_log.append({"press": n, "kinds": st_["kinds"], "contradictions": st_["contradictions"]})
                            # THE KEYHOLE FALLS OUT OF THE SEARCH: a contradiction with a key region becomes a relation — the region must
                            # read as it did when the door opened; the source is the thing whose touches change that region
                            if not any(r_["targets"] for r_ in rels):
                                regs_ = relations.regions(graph["edges"], level_hist, body_of, ops.amb, ops)
                                for c_ in st_["contradictions"]:
                                    kk_ = c_.get("key")
                                    if not kk_: continue
                                    y0_, y1_, x0_, x1_ = kk_["box"]
                                    src_ = next((s_ for s_, bx_ in regs_.items() if not (bx_[1] < y0_ or bx_[0] > y1_ or bx_[3] < x0_ or bx_[2] > x1_)), None)
                                    tobj_ = next((o_ for o_ in things_ if o_["id"] == c_["thing"]), None)
                                    if src_ is None or tobj_ is None: continue
                                    rels.append({"src": src_, "region": kk_["box"], "states": 2, "raw_open": kk_["pattern_when_open"],
                                                 "targets": [{"id": tobj_["id"], "object": tobj_, "pattern": None, "matched_now": False, "rotation": None}], "state_patterns": [], "magnet": True})
                                    log(f"  magnet relation: touch {src_} until rows {y0_}-{y1_} cols {x0_}-{x1_} read as they did when {tobj_['id']} opened ({c_['control']} from {c_['side']}: {kk_['opens']} open / {kk_['closed']} closed)")
                                    break
                        except Exception as e_:
                            log(f"  magnets failed: {str(e_)[:100]}")
                        # THE RINGS: learned from the refills; before any, the register's own colour on the floor is the hypothesis
                        try:
                            learned_ = rings.learn(level_hist, reg, body_of, ops, ops.amb, floor_)
                            ring_rel = learned_ or rings.hypothesis(reg, f, ops.amb)
                            if ring_rel:
                                # the ring is floor to the move: the body drives onto it (the operators' floor rule never saw
                                # the pass — the refill press is not a plain shift — so the relation supplies it)
                                for op_ in list(ops.ops.values()) + list(ops.hyp.values()):
                                    if isinstance(op_, induce.Displace): op_.floor.add(int(ring_rel["colour"]))
                                standing = rings.present(f, ring_rel["colour"], ops.amb)
                                ring_log.append({"press": n, **{k_: v_ for k_, v_ in ring_rel.items()}, "standing": len(standing)})
                                log(f"  rings: colour {ring_rel['colour']} ({ring_rel['source']}), gain {ring_rel['gain']}, {len(standing)} standing: {[r_['id'] for r_ in standing]}")
                        except Exception as e:
                            log(f"  rings failed: {str(e)[:80]}")
                        # THE DIAGONAL PINS: the relations, the rings and the magnets' keys as one kind of thing, each with an eye
                        try:
                            if mags is not None:
                                standing_d = rings.present(f, ring_rel["colour"], ops.amb) if ring_rel else []
                                st_d = mag_log[-1] if mag_log else {}
                                diag = diagonal.Pins().from_layers(rels, ring_rel, standing_d, reg.band, mags, {"contradictions": st_d.get("contradictions", [])}, graph["objects"])
                                diag.eyes(level_hist, mags, band=reg.band, floor=floor_, matched=relations.matched)
                                front_known = set(a_ for a_ in ops.ops if ops.known(a_)) | set(int(t_[6:]) for t_ in mags.things if t_.startswith("ACTION") and mags.kind(t_) != "empty")
                                paths_ = diag.paths([a_ for a_ in avail if a_ != 6], front_known)
                                log("  " + diag.summary(paths_))
                                pin_dump = diag.dump(floor=floor_)
                                questions_ = question_queue.update(pin_dump, step=n)
                                log(f"  pin questions: {questions_['open_count']} open (local prompt outbox; proposals only)")
                                diag_log.append({"press": n, "pins": pin_dump, "paths": paths_, "question_queue": questions_})
                                if use_cubes:
                                    flow_ = cube_router.local_proposals(questions_, f"{n}:{hashlib.sha256(f.tobytes()).hexdigest()[:16]}")
                                    diag_log[-1]["cube_flow"] = flow_
                                    log(f"  cubes: {flow_['opened']} requests, {flow_['outstanding']} outstanding, {len(flow_['proposals'])} proposals (not actions)")
                        except Exception as e:
                            log(f"  diagonal pins failed: {str(e)[:100]}")
                        # THE THREE VIEWS: composed from the fence (side), the pins and magnets (front), the water, meter and eyes (eyes)
                        try:
                            things_v = [o_ for o_ in graph["objects"] if not o_["id"].startswith(("chg", "place", "wall")) and o_["id"] != "bound"]
                            vw = views.Views(f.shape).build(fen=fen, diag=diag, mags=mags, things=things_v, water=water, met=met)
                            log("  " + vw.summary()); vw_log.append({"press": n, "union_only": vw.union_only})
                            tot_d = sum(depth.values())
                            if tot_d:
                                log(f"  depth: of this level's change, {depth[1] / tot_d:.0%} lands at layer 1 (the pixel), {depth[2] / tot_d:.0%} at layer 2 (the thing), "
                                    f"{depth[3] / tot_d:.0%} at layer 3 (the relation), {depth[0] / tot_d:.0%} runs wall to wall (short circuits)")
                                depth_log.append({"press": n, **{f"layer{k_}": round(v_ / tot_d, 3) for k_, v_ in depth.items()}})
                            # THE COLLAPSE (Jonathan, Sep 7): a uniform region is one term; the body one quaternion instead of its pixels
                            try:
                                cs_ = vw.collapse(body=body_of(ops, f))
                                if cs_:
                                    bt_ = cs_["body"]
                                    log(f"  collapsed: {cs_['pixels']} pixels -> {cs_['terms']} terms ({cs_['nonempty_terms']} with memory, the largest {cs_['largest']} cells; "
                                        f"{cs_['closing']} regions whose edge comes back to where it started)"
                                        + (f"; the body is {'ONE term' if bt_['one_term'] else str(bt_['terms']) + ' terms'} for its {bt_['cells']} cells" if bt_ else "")
                                        + (f" — stitched into one nested term: {len(bt_['stitched']['parts'])} parts (interior and rim), |o| {bt_['stitched']['octonion_norm']}, |whole| {bt_['stitched']['whole_norm']}" if bt_ and bt_.get("stitched") and not bt_["stitched"]["one_term"] else ""))
                                    vw_log[-1]["collapse"] = cs_
                                    # THE FLOOR THINNING (Jonathan, Sep 7): the body detaches the pins that travel with it; the floor's field
                                    # is collapsed again with the body's cells emptied, and the rule sheet split into the body's own colour and the rest
                                    b_ = body_of(ops, f)
                                    if b_ is not None and vw.q is not None:
                                        q2_ = vw.q.copy(); q2_[b_] = 0
                                        terms2_, _ = quat.collapse(q2_)
                                        before_ = cs_["nonempty_terms"]; after_ = sum(1 for t_ in terms2_ if not t_["empty"])
                                        fills_ = set(op_.fill for op_ in ops.ops.values() if isinstance(op_, induce.Displace))
                                        own_ = sum(1 for (nn_, ff_, kk_) in fen.rule if nn_ in fills_); rest_r = len(fen.rule) - own_
                                        log(f"  floor: {before_} terms with the body's pins -> {after_} after it detached them; the sheet keeps {rest_r} rules of other colour pairs, {own_} are the body's own ({sorted(fills_)} against the walls)")
                                        vw_log[-1]["floor"] = {"terms_with_body": before_, "terms_without": after_, "rules_body": own_, "rules_rest": rest_r}
                            except Exception as e_:
                                log(f"  collapse failed: {str(e_)[:80]}")
                            # THE PATH PRODUCT (Jonathan, Sep 7): a diagonal pin's path — its foot, its back-wall coordinate, its effect — as the
                            # product of the pixels' quaternions in order (recalled from the top eye), and as the octonion chain of neighbour
                            # pairs; checked against the pin's own eye. If the real part tracks the eye, the multiplication earns its place.
                            if diag is not None and vw.q is not None:
                                obj_c = {o_["id"]: o_ for o_ in graph["objects"]}
                                prods = []
                                for p_ in diag.pins:
                                    fy, fx = (lambda ys_, xs_: (int(ys_.mean()), int(xs_.mean())))(*np.where(p_["cells"]))
                                    b_ = p_["back"]; box_ = b_["box"]
                                    if b_["frame"] == "screen": by, bx = int((box_[0] + box_[1]) / 2), int((box_[2] + box_[3]) / 2)
                                    else: by, bx = fy + int((box_[0] + box_[1]) / 2), fx + int((box_[2] + box_[3]) / 2)
                                    tgt = obj_c.get(p_["effect"]["target"])
                                    path_px = [(fy, fx), (by, bx)] + ([(lambda ys_, xs_: (int(ys_.mean()), int(xs_.mean())))(*np.where(tgt["cells"]))] if tgt is not None else [])
                                    H_, W_ = f.shape
                                    qs_ = [vw.q[min(max(y_, 0), H_ - 1), min(max(x_, 0), W_ - 1)] for y_, x_ in path_px]
                                    real_, norm_, _ = quat.path_product(qs_); oct_ = quat.path_octonion(qs_)
                                    e_ = p_["eye"]; prods.append({"pin": p_["foot"], "to": p_["effect"]["target"], "real": round(real_, 3), "norm": round(norm_, 3),
                                                                   "oct_norm": round(oct_["norm"], 3) if oct_ else None, "associator": round(oct_["associator"], 3) if oct_ else None,
                                                                   "eye": [e_["fired_with"], e_["fired_without"], e_["silent_with"], e_["silent_without"]]})
                                if prods:
                                    log("  paths as products: " + "; ".join(f"{p_['pin']} -> {p_['to']}: real {p_['real']:+.2f}, |q| {p_['norm']:.2f}, |o| {p_['oct_norm']}, associator {p_['associator']} vs eye {p_['eye']}" for p_ in prods))
                                    vw_log[-1]["products"] = prods
                        except Exception as e:
                            log(f"  views failed: {str(e)[:100]}")
                        for r_ in rels:
                            if r_["targets"]:
                                log(f"  relation: {r_['src']} -> region rows {r_['region'][0]}-{r_['region'][1]} cols {r_['region'][2]}-{r_['region'][3]} ({r_['states']} states seen) -> "
                                    + ", ".join(f"{t_['id']}{' MATCHED' if t_['matched_now'] else (' (D4 %s away)' % t_['rotation'])}" for t_ in r_["targets"]))
                    else:
                        goals = []; log(f"  touch graph: no body found on this level's presses (pins not refilled)")
                except Exception as e:
                    graph = None; goals = []; log(f"  touch graph failed: {str(e)[:80]}")
            # THE ROUTE (Jonathan, Sep 4): a planned path with an estimated length ending in a reset; a known part
            # (the operators reproduce it) and an unknown part; until the reset can be placed past the goal, explore
            if exp is not None and exp.get("path") is not None:
                known = len(exp["path"]); budget_now = reg.remaining(f, since, deaths_lv)
                mode = "goal-driven: the reset sits past the goal" if budget_now is None or known <= budget_now - margin else "exploring: the reset falls before the goal"
                log(f"  route: {known} known presses to '{exp['id']}', budget {('%.0f' % budget_now) if budget_now is not None else '?'}, margin {margin} -> {mode}")
            for a_, op_ in ops.ops.items(): ever[a_] = op_
            if ever:
                keys, size, radius, ring_now = closure(ops, f, vkey, ever=ever, avail=avail)
                ring[:] = ring_now
                ever_keys.update(keys)                              # the circle is every state EVER reachable on this level
                keys = ever_keys; size = len(ever_keys)
                covered = len(keys & visited) / size if size else 0.0
                budget_now = reg.remaining(f, since, deaths_lv)
                wraps = (size / budget_now) if budget_now else None
                grew = size - last_size; last_size = size
                shape.append({"press": n, "size": size, "radius": radius, "covered": round(covered, 3), "wraps": None if wraps is None else round(wraps, 1), "grew": grew,
                              "pins": reg_pins.stats()})
                log(f"  shape: closure {size}{'+' if size >= 3000 else ''} states (operators ever gated: {sorted(ever)}), radius {radius}, slice covered {covered:.0%}, "
                    f"{('%.1f segments to wrap' % wraps) if wraps else 'budget unread'}, grew {grew:+d}, ring {len(ring_now)} gap states")
            if reg_pins.pins: log(f"  pins: {reg_pins.summary()}")
            if met.band is not None:
                rr_ = reg.remaining(f, since, deaths_lv); ml_ = met.left()
                met_log.append({"press": n, **met.stats(), "register_says": rr_})
                log(f"  {met.summary()}" + (f" | the register's own reading: {rr_:.0f}" if rr_ is not None and ml_ is not None and abs(rr_ - ml_) >= 1 else ""))
            if fen.presses:
                fs_ = fen.stats(); fen_log.append({"press": n, **{k_: v_ for k_, v_ in fs_.items() if k_ != "rules"}})
                log(f"  fence: {fen.summary()}")
            tot_ = explained_mass + unexplained_mass
            log(f"  sweep: {explained_mass / tot_:.0%} of this level's change explained in front, {unexplained_mass / tot_:.0%} only behind; water {water.sum():.0f}"
                + (f" | antennas: " + ", ".join(f"{a_['id']} {a_['antenna']:.0f} (caused {a_.get('caused', 0):.0f}, pins {a_['empty']:.0%} empty)" for a_ in antennas) if antennas else "") if tot_ else "  sweep: no change yet")
            log(f"  sleep ({reason}): {ops.summary() or 'no operators'} | budget "
                f"{('colour %s drains %g/press, %.0f left' % (reg.colour, reg.drain, reg.remaining(f, since, deaths_lv))) if reg.colour is not None else 'unread'}"
                f"{(' (deaths %d, death-drain %.2f)' % (len(deaths_lv), max(f0 / nn for f0, nn in deaths_lv if f0 and nn))) if any(f0 and nn for f0, nn in deaths_lv) else ''}"
                f" | candidates {[c['id'] for c in goals[:5]]} ({time.time() - t1:.1f}s)")
        if prior and ops.amb is not None:
            reg.fit(ops.amb, prior[-60:])
            if reg.colour is not None: log(f"  budget from the prior: register colour {reg.colour}, drains {reg.drain:g} cells/press, {reg.remaining(f):.0f} presses left")
        tick = np.zeros_like(f, dtype=bool)                   # cells that move when almost nothing else does
        start = f.copy(); nchg = np.zeros_like(f, dtype=int)  # the level's first frame; how often each cell changed since
        agent_hist = {}; state = {"agent": None, "goals": []}
        def rise(fr_):
            """RISING: cells that differ from the level's start frame and have not been flipping back and forth
            (changed at most twice so far) — irreversible change, which is what progress looks like in a puzzle;
            the agent walking over new ground counts once, walking back over it does not."""
            return int(((fr_ != start) & (nchg <= 2) & ~tick).sum())
        def approach(fr_):
            """minus the distance from the mover to the nearest goal blob (None when there is no mover or goal)"""
            if not state["goals"]: return None
            pos = mover_pos(fr_, f, nchg, state["agent"])
            if pos is None: return None
            return -min(abs(pos[0] - gy) + abs(pos[1] - gx) for gy, gx, _, _ in state["goals"])
        while n < presses and stop_reason is None:
            avail_all = [int(a) for a in (fr.get("available_actions") or [])]
            avail = [int(a) for a in (fr.get("available_actions") or avail) if 1 <= int(a) <= 6] or avail
            cands = candidates(f, avail, (ambient | tick) if ambient is not None else tick)
            if n >= FIRST and use_rise:
                state["agent"] = max(agent_hist, key=agent_hist.get) if agent_hist else None
                state["goals"] = topology(f, nchg, tick, state["agent"])
            induce.START[id(f)] = start                            # for the restore operator: where this level began
            # the state key leaves the whole register band out (Sep 6): after a refill the bar's far end changes every press, and with
            # only the often-changing cells masked every planned state looked new — the search hit its cap before any far target
            _band_ = reg.band if (reg is not None and getattr(reg, "band", None) is not None) else None
            _mask_ = (tick | ops.amb) if ops.amb is not None else tick
            if _band_ is not None: _mask_ = _mask_ | _band_
            vkey = (lambda q, m_=_mask_: P._key(q, m_)) if use_ops else None
            planned = None; exp_step = None; do_reset = None; unknown = []
            if use_ops and ops.ops:
                if rel is not None and graph:
                    rel, refreshed = relations.refresh_active(rel, rels, graph["objects"])
                    if refreshed:
                        log(f"  {n:3d}. relation: matcher refreshed from current evidence (colour {rel['rel'].get('colour')})")
                    if exp is not None and exp.get("rel") == "src":
                        current_floor = set().union(*(op.floor for op in ops.ops.values() if isinstance(op, induce.Displace)))
                        if refreshed or relations.matched(f, rel["rel"], current_floor):
                            # A stale source plan must not rotate away a newly recognized match.
                            exp = None
                visited.add(vkey(f))
                unknown = [a_ for a_ in avail if a_ != 6 and not ops.known(a_)]
                relation_ready = rel is not None or any(r_["targets"] for r_ in rels)
                if ring_mode and exp is None and not goals and exp_step is None and not relation_ready:
                    if ring_target is None:
                        while ring and ring_target is None:
                            q = ring.pop(0); k_ = vkey(q)
                            if any((k_, a_) not in ring_probed for a_ in avail if a_ != 6): ring_target = (k_, q)
                        if ring_target is None: ring_done = True; ring_mode = False
                    if ring_target is not None:
                        if vkey(f) == ring_target[0]:
                            # at a gap state press only what the model cannot answer here: the unexplained buttons, and
                            # the trusted buttons whose operator abstains or refuses at this very state (the wall test)
                            here = [a_ for a_ in avail if a_ != 6 and (ring_target[0], a_) not in ring_probed
                                    and (not ops.known(a_) or ops.predict(f, a_) is None or np.array_equal(ops.predict(f, a_), f))]
                            here.sort(key=lambda a_: (-reg_pins.emptiness(a_) if reg_pins.pins else 0, a_ not in ops.hyp, a_))   # emptiest control first
                            if here: exp_step = (here[0], "ring")
                            else:
                                for a_ in avail: ring_probed.add((ring_target[0], a_))
                                ring_target = None
                        else:
                            tk = ring_target[0]; path = plan_to(ops, f, lambda q: vkey(q) == tk, vkey)
                            if path: planned = (path[0], len(path), "plan")
                            elif path is None: ring_target = None            # not reachable with what is trusted now
                # THE RELATION LOOP: touch the source until the region matches a target, then go to the target
                if exp is None and rel is None and rels:
                    for r_ in rels:
                        if r_["targets"] and graph:
                            if use_relation_guard and not relation_attempts.allowed(r_):
                                current_floor = set().union(*(op.floor for op in ops.ops.values() if isinstance(op, induce.Displace)))
                                if not relations.matched(f, r_, current_floor): continue
                            srcobj = next((o for o in graph["objects"] if o["id"] == r_["src"]), None)
                            if srcobj is not None and mind is not None and hasattr(mind, "allow_relation"):
                                try:
                                    if not mind.allow_relation(lvl, r_): continue      # her planner may stop the body's loop (Oct 27)
                                except Exception: pass
                            if srcobj is not None:
                                rel = {"src": srcobj, "rel": r_, "tries": 0, "dst": r_["targets"][0]["object"]}
                                log(f"  {n:3d}. relation loop: touch {r_['src']} until the region matches {r_['targets'][0]['id']}"); break
                if exp is None and rel is not None:
                    floor_ = set()
                    for op_ in ops.ops.values():
                        if isinstance(op_, induce.Displace): floor_ |= op_.floor
                    hits = relations.matched(f, rel["rel"], floor_)
                    # THE ROUTE WITH REFILL POINTS (Jonathan, Sep 6): every standing ring is a goal; the life is planned as stops —
                    # the touches still needed, the target, and the rings wherever the bar closes. The first stop decides now.
                    next_ring_ = None
                    try:
                        rem_r = reg.remaining(f, since, deaths_lv)
                        if ring_rel and rem_r is not None and reg.drain:
                            standing_r = rings.present(f, ring_rel["colour"], ops.amb)
                            states_r = int(rel["rel"].get("states", 1) or 1)
                            need_t = relations.touches_needed(f, rel["rel"], floor_)
                            touches_r = 0 if hits else (need_t if need_t else max(1, states_r - rel["tries"]))   # round the cycle to the target
                            box_r = hits[0]["object"]["cells"] if hits else rel["dst"]["cells"]
                            full_r = (bar_full_cells / reg.drain) if bar_full_cells else rem_r
                            if standing_r:
                                route_plan = route.plan(ops, f, vkey, body_of, contact_tests, plan_to, standing_r, rel["src"]["cells"], touches_r, box_r,
                                                        bar=rem_r, bar_full=full_r, margin=1, log=log)   # the bar is read exactly; one move of slack
                                if route_plan and route_plan[0] and route_plan[0][0][0] == "ring": next_ring_ = route_plan[0][0][1]
                                if route_plan is None:
                                    log(f"  {n:3d}. route: no order of the rings closes the budget from here ({len(standing_r)} standing, {touches_r} touches, {rem_r:.0f} left)")
                                    if not route_dumped and rem_r >= 18 and since <= 3:            # once: the fence and frame at a failed plan from a full bar, for the bench
                                        try:
                                            fen.save(os.path.join(OUT, "fence_debug.npz")); np.save(os.path.join(OUT, "frame_debug.npy"), f)
                                            json.dump({"floors": {int(a_): sorted(int(c_) for c_ in op_.floor) for a_, op_ in ops.ops.items() if isinstance(op_, induce.Displace)},
                                                       "known": [int(a_) for a_ in ops.ops if ops.known(a_)], "press": n}, open(os.path.join(OUT, "route_debug.json"), "w"))
                                            route_dumped = True; log(f"  {n:3d}. route: fence and frame dumped for the bench")
                                        except Exception as e_: log(f"  dump failed: {str(e_)[:60]}")
                    except Exception as e_:
                        log(f"  {n:3d}. route failed: {str(e_)[:80]}")
                    if next_ring_ is not None:
                        sides = set(); adj, ali = contact_tests(ops, next_ring_["cells"], sides)
                        exp = {"id": next_ring_["id"], "cells": next_ring_["cells"], "adjacent": adj, "aligned": ali, "tried": [], "changed": False, "n0": n, "fallback": False,
                               "bump_only": True, "rel": "ring", "sides": sides}
                        log(f"  {n:3d}. route: the ring {next_ring_['id']} first")
                    elif hits:
                        dst = hits[0]["object"]; sides = set(); adj, ali = contact_tests(ops, dst["cells"], sides)
                        from scipy import ndimage as _nd
                        lava = _nd.binary_dilation(rel["src"]["cells"], iterations=3)      # the source would undo the match: lava
                        exp = {"id": dst["id"], "cells": dst["cells"], "adjacent": adj, "aligned": ali, "tried": [], "changed": False, "n0": n, "fallback": False,
                               "bump_only": True, "rel": "dst", "sides": sides, "avoid": lava}
                        fen.exempt_cells(dst["cells"]); fen.compile(fence_ground())     # the relation answers for the door, not the fence
                        log(f"  {n:3d}. relation: the region MATCHES {dst['id']} — going to it (the fence lets its borders go)"); rel_log.append({"press": n, "src": rel["src"]["id"], "dst": dst["id"], "tries": rel["tries"]})
                        rel = None
                    elif rel["tries"] < 8 and (not use_relation_guard or relation_attempts.allowed(rel["rel"])):
                        srcobj = rel["src"]; sides = set(); adj, ali = contact_tests(ops, srcobj["cells"], sides); rel["tries"] += 1
                        exp = {"id": srcobj["id"], "cells": srcobj["cells"], "adjacent": adj, "aligned": ali, "tried": [], "changed": False, "n0": n, "fallback": False,
                               "bump_only": True, "rel": "src", "sides": sides}
                        log(f"  {n:3d}. relation: touch {srcobj['id']} (try {rel['tries']})")
                    else:
                        log(f"  {n:3d}. relation: touch-attempt budget exhausted for {rel['src']['id']}; this hypothesis yields to other goals"); rel = None
                if exp is None and goals and mind is not None:
                    try:
                        ordered_ = mind.order(goals, lvl, f)
                        ids_ = {c_["id"] for c_ in goals}
                        if ordered_ and len(ordered_) >= len(goals) and ids_ <= {c_["id"] for c_ in ordered_}: goals = ordered_   # she may add back a thing she saw this life (Oct 16)
                    except Exception as e_:
                        log(f"  {n:3d}. mind: order failed ({str(e_)[:80]}); the planet's own order stands")
                if exp is None and goals:
                    c0 = goals[0]; adj, ali = contact_tests(ops, c0["cells"])
                    exp = {"id": c0["id"], "cells": c0["cells"], "adjacent": adj, "aligned": ali, "tried": [], "changed": False, "n0": n, "fallback": False,
                           "open": c0.get("open"), "bump_only": c0.get("open") is not None}
                    log(f"  {n:3d}. experiment: {exp['id']} ({len(goals)} candidates: {[c['id'] for c in goals[:4]]})")
                if exp is not None:
                    at = exp["adjacent"](f) or (exp["fallback"] and exp["aligned"](f))
                    b_now = body_of(ops, f)
                    if exp.get("bump_a") is not None and exp.get("repeat", 0) < 3 and b_now is not None and (b_now & exp["cells"]).any() and "bump" in exp["tried"]:
                        # a bump that moved the body INTO the thing is progress: push again the same way (the insert takes three)
                        exp["repeat"] = exp.get("repeat", 0) + 1; exp_step = (exp["bump_a"], "bump"); at = False
                    if at:
                        here = [] if exp.get("bump_only") else [a_ for a_ in unknown if a_ not in exp["tried"]]
                        if here: exp_step = (here[0], "try")
                        elif "bump" not in exp["tried"]:
                            b = body_of(ops, f); bump = None; sides = exp.get("sides")
                            if b is not None:
                                for a_, op in ops.ops.items():
                                    if isinstance(op, induce.Displace) and (sides is None or a_ not in sides) and (induce.shifted(b, *op.d, fill=False) & exp["cells"]).any(): bump = a_; break
                            if bump is not None: exp_step = (bump, "bump")
                            else: exp["tried"].append("bump")
                        if exp_step is None and not here and "bump" in exp["tried"]:
                            pressed = [t_ for t_ in exp["tried"] if isinstance(t_, int)] + ([exp["bump_a"]] if "bump_a" in exp else [])
                            # no button was pressed at the thing (all trusted, no bump possible): the experiment is UNTESTABLE
                            # from here, not "nothing" — the pins stay empty and no reset is spent on it
                            result = ("changed" if exp["changed"] else "nothing") if pressed else "untestable"
                            # the experiment answers the pins directly: every control tried at this thing gets 'state'
                            # or 'nothing here' (touch.build only records presses that met an object by adjacency)
                            for a_ in [t_ for t_ in exp["tried"] if isinstance(t_, int)] + ([exp["bump_a"]] if "bump_a" in exp else []):
                                if exp.get("open") is None: reg_pins.fill(a_, exp["id"], "state" if exp["changed"] else "nothing", vkey(f))
                            if not exp.get("rel"): done_exp.add(exp["id"])
                            experiments.append({"id": exp["id"], "result": result, "presses": n - exp["n0"], "rel": exp.get("rel")})
                            log(f"  {n:3d}. experiment {exp['id']}{(' (relation ' + exp['rel'] + ')') if exp.get('rel') else ''}: {result} after {n - exp['n0']} presses")
                            was_rel = exp.get("rel"); was_open = exp.get("open") is not None; goals = [c for c in goals if c["id"] != exp["id"]]; exp = None
                            if use_relation_guard and was_rel == "src" and pressed and rel is not None:
                                relation_attempts.attempt(rel["rel"])
                            if result == "nothing" and not was_rel and not was_open: do_reset = "experiment over, nothing happened: next candidate"
                            if was_rel == "src" and result == "untestable": rel = None                          # cannot touch it from here: stop asking
                            elif was_rel == "src" and result != "changed" and rel is not None: rel["tries"] += 2   # a touch that changed nothing costs extra tries
                    elif exp_step is None:                                    # travel only when no press was chosen (the repeat-bump chooses one)
                        path = exp.get("path")
                        if path is None or exp.get("deviated"):          # plan once; re-plan only when the world deviated
                            exp["deviated"] = False
                            path = plan_to(ops, f, exp["adjacent"], vkey, avoid=exp.get("avoid"))
                            if path is None and exp.get("avoid") is not None: path = plan_to(ops, f, exp["adjacent"], vkey)   # no protected route: take the plain one
                            if path is None and not exp["fallback"]:
                                exp["fallback"] = True; path = plan_to(ops, f, exp["aligned"], vkey)
                            exp["path"] = path
                            if path is not None: log(f"  {n:3d}. experiment {exp['id']}: path of {len(path)} presses{' (aligned, not adjacent)' if exp['fallback'] else ''}")
                        if path is None:
                            # UNREACHABLE IS NOT DONE (Sep 7): the keyhole tried at press 11, before the operators were gated, was filed as
                            # done for the level and never retried; a thing the model cannot reach yet is asked again thirty presses later
                            if not exp.get("rel"): retry_at[exp["id"]] = n + 30
                            else:
                                rel = None
                                rels = []; log(f"  {n:3d}. the relation's {exp.get('rel')} cannot be reached with what is trusted now: the relation waits for the next sleep")
                            experiments.append({"id": exp["id"], "result": "unreachable", "presses": n - exp["n0"], "rel": exp.get("rel")})
                            log(f"  {n:3d}. experiment {exp['id']}: unreachable"); goals = [c for c in goals if c["id"] != exp["id"]]; exp = None
                        elif path:
                            planned = (path[0], len(path), "plan"); exp["expect"] = ops.predict(f, path[0])
                            rem_now = reg.remaining(f, since, deaths_lv)
                            # a relation touch needs presses AFTER arriving (the bump, a step back, the next bump); the HUD state
                            # does not survive a reset (ls20 level 2: 25 touches, one per life, never past the first state)
                            need_ = 0
                            if exp.get("rel") == "src":
                                states_ = (rel or {}).get("rel", {}).get("states", 1) if isinstance(rel, dict) else 1
                                need_ = min(9, 3 * max(1, int(states_) - 1))          # every remaining state costs a touch: bump, step back, bump
                            if exp.get("rel") in ("src", "dst", "ring") and route_plan: need_ = 0; rem_now = None   # routed: the stops were budgeted together
                            if rem_now is not None and len(path) + need_ > rem_now - margin:
                                # THE RING DETOUR (Jonathan, Sep 5): the goal is farther than the budget; a ring the body can
                                # reach first refills the bar — go there, then the goal is planned again from the refill
                                took = False
                                if ring_rel:
                                    best_ = None
                                    q_ = max([max(abs(op_.d[0]), abs(op_.d[1])) for op_ in ops.ops.values() if isinstance(op_, induce.Displace) and op_.d] or [5])
                                    gy_, gx_ = np.argwhere(exp["cells"]).mean(axis=0)
                                    standing_ = rings.present(f, ring_rel["colour"], ops.amb)
                                    hop_ = lambda r_: (lambda c_: (abs(c_[0] - gy_) + abs(c_[1] - gx_)) / q_)(np.argwhere(r_["cells"]).mean(axis=0))   # ring -> goal, estimated
                                    # THE ORDER OF THE RINGS: when the goal itself is within reach and a ring stands near it, walk to the goal
                                    # first — that ring pays for the touches there, and the rings elsewhere are kept for the trip after
                                    near_ = []
                                    at_goal_ = f
                                    for a__ in path:                                                          # the frame at the end of the walk, imagined
                                        nq_ = ops.predict(at_goal_, a__)
                                        if nq_ is None: break
                                        at_goal_ = nq_
                                    for r_ in standing_:
                                        if hop_(r_) > max(3, need_): continue
                                        dn_ = plan_to(ops, at_goal_, lambda q, c_=r_["cells"]: (lambda b_: b_ is not None and (b_ & c_).any())(body_of(ops, q)), vkey, depth=12, max_states=800)
                                        near_.append(len(dn_) if dn_ else hop_(r_))                             # the real way from the goal to it when there is one
                                    if near_ and rem_now - margin - len(path) >= min(near_): took = True         # ...and that ring is still affordable after the walk
                                    dbg_ = []
                                    for r_ in ([] if took else standing_):
                                        cells_ = r_["cells"]
                                        d_ = plan_to(ops, f, lambda q, c_=cells_: (lambda b_: b_ is not None and (b_ & c_).any())(body_of(ops, q)), vkey)
                                        dbg_.append(f"{r_['id']}: {'no path' if d_ is None else str(len(d_)) + ' away'}, hop {hop_(r_):.1f}")
                                        if d_ is None or not (0 < len(d_) <= rem_now): continue              # only a ring the bar still reaches (the ring's refill is the margin)
                                        cost_ = len(d_) + hop_(r_)                                                # to the ring, then on to the goal
                                        if best_ is None or cost_ < best_[2]: best_ = (r_, d_, cost_)
                                    log(f"  {n:3d}. detour check: goal {len(path)} away + {need_} to touch, budget {rem_now:.0f}, margin {margin}; "
                                        f"{'walk first (a ring near the goal is affordable after)' if took else ('rings: ' + '; '.join(dbg_) if dbg_ else 'no ring standing')}")
                                    if best_ is not None and len(best_[1]) <= rem_now and len(best_[1]) > 0:   # entering the ring refills: the last press may land on it
                                        planned = (best_[1][0], len(best_[1]), "ring"); exp["path"] = None; took = True
                                        log(f"  {n:3d}. ring detour: goal {len(path)} presses away{' + ' + str(need_) + ' to touch' if need_ else ''}, budget {rem_now:.0f}; ring {best_[0]['id']} is {len(best_[1])} away")
                                if not took and refills:
                                    rk = set(refills); detour = plan_to(ops, f, lambda q: vkey(q) in rk, vkey)
                                    if detour and len(detour) < rem_now - margin:
                                        planned = (detour[0], len(detour), "plan"); exp["path"] = None
                                        log(f"  {n:3d}. refill detour: goal {len(path)} presses away, budget {rem_now:.0f}; a refill is {len(detour)} away")
                if exp_step is None and planned is None and do_reset is None:
                    if unknown:
                        c_ = reg_pins.emptiest(unknown) if reg_pins.pins else random.choice(unknown)
                        every = 2 if (reg_pins.pins and reg_pins.emptiness(c_) >= 0.5) else 4     # the emptier the control, the oftener it is asked
                        if n % every == 0 and (vkey(f), c_) not in probed:
                            probed.add((vkey(f), c_)); planned = (c_, 0, "probe")
                    else:
                        r_ = plan_step(ops, f, visited, vkey, approach if use_rise else None, depth=14, max_states=600)
                        if r_: planned = (r_[0], r_[1], "plan")
            rem = reg.remaining(f, since, deaths_lv) if use_ops else None
            if since == 0: seg_fill = reg.fill(f)
            if rem is not None and since == 0:
                seg_budget = rem                                 # what the register said at the start of this segment
                if rem <= margin + 2:                            # a full segment cannot start with an empty register: the model is stale
                    log(f"  {n:3d}. budget model says {rem:.0f} at a fresh start: discarded until the next refit"); reg = Register(); rem = None
            # MIKA'S ROUTE (Oct 13 2026): a level a mind has cleared before is walked again press for press from its start;
            # no reset interrupts it. If the route ends without the level, the mind drops it and the body leads.
            forced_ = None; mind_reset_ = False
            if mind is not None and hasattr(mind, "sense"):
                try: mind.sense(lvl, rem, margin, since)
                except Exception as e_: log(f"  {n:3d}. mind: sense failed ({str(e_)[:80]})")
            if mind is not None and hasattr(mind, "press"):
                try: forced_ = mind.press(lvl, since)
                except Exception as e_: log(f"  {n:3d}. mind: route failed ({str(e_)[:80]})"); forced_ = None
            if isinstance(forced_, str):                     # she asks to put the level back (a trimmed route failed, a study is over)
                do_reset = f"mind: {forced_.lower()} requested"; mind_reset_ = True; forced_ = None
            if forced_ is not None: do_reset = None
            if forced_ is None and use_ops and ops.ops and since > 0:
                if rem is not None and since >= 3 and (seg_budget is None or seg_budget - rem >= 1):   # only once this segment has visibly drained
                    ring_leg_ = (exp is not None and exp.get("rel") == "ring") or (planned is not None and planned[2] == "ring")
                    if planned and planned[2] in ("plan", "ring") and planned[1] > rem - (0 if ring_leg_ else margin):
                        do_reset = f"target {planned[1]} presses away, budget {rem:.0f} left, margin {margin}"
                    elif rem <= margin:
                        do_reset = f"budget {rem:.0f} left, margin {margin}"
                elif planned and planned[2] == "plan" and life_len and planned[1] > life_len - since:
                    do_reset = f"target {planned[1]} presses away, {life_len - since} left in this life"
                if do_reset is None and planned is None and exp_step is None and exp is None and since >= 4 and not unknown:
                    do_reset = "dead end: nothing new reachable from here"
            # Oct 16 night: the habit resets ("experiment over, nothing happened", "dead end") are weighed too; they cost
            # everything built since the last reset (ls20 life 16: a refill counted as 'nothing' reset away a key change)
            if do_reset and not mind_reset_ and mind is not None and hasattr(mind, "weigh_reset") and str(do_reset).startswith(("target", "budget", "experiment over", "dead end")):
                try:
                    hold_ = mind.weigh_reset(lvl, {"reason": do_reset, "rem": rem, "margin": margin, "target": planned[1] if planned else None,
                                                   "kind": planned[2] if planned else None, "exp": exp["id"] if exp else None, "since": since})
                except Exception as e_:
                    hold_ = None; log(f"  {n:3d}. mind: weighing failed ({str(e_)[:80]})")
                if hold_:
                    log(f"  {n:3d}. mind holds her path instead of resetting ({do_reset}; {hold_})"); do_reset = None
            if do_reset:
                segments.append({"start": seg_start, "end": n, "presses": since, "ended": "reset", "budget_left": None if rem is None else round(rem, 1), "margin": margin})
                if rem is not None and rem <= margin:
                    clean += 1
                    if clean >= 3: margin = max(1, margin - 1); clean = 0       # three clean budget resets: place the next one later
                fr = send("RESET"); f = frame_np(fr); frames.append(f); vresets += 1; since = 0; seg_start = n
                if exp is not None: exp["path"] = None; exp["deviated"] = False     # the body is back at the start: the route is planned again
                if exp is not None and exp.get("rel"): exp = None                   # a relation's life starts over: the route is planned from a full bar
                if rel is not None: rel["tries"] = 0                                # the HUD state did not survive the reset
                if rel is not None and mind is not None and hasattr(mind, "allow_relation"):
                    try:
                        if not mind.allow_relation(lvl, rel["rel"], reset=True): rel = None   # Oct 27: she may stop the loop at a reset
                    except Exception: pass
                route_plan = None; met.stand(f)
                start = f.copy(); nchg[:] = 0
                rec.append({"n": n, "a": 0, "x": -1, "y": -1, "changed": 0, "surprise": 0.0, "kept": False, "levels": lvl, "state": "RESET",
                            "steps": 0, "rise": 0, "why": "reset", "src": "op", "dist": None, "goals": 0, "mover": None})   # the record carries the reset (one frame, no press)
                log(f"  {n:3d}. RESET #{vresets} ({do_reset}); level {int(fr.get('levels_completed', 0) or 0)} kept; segment of {segments[-1]['presses']} presses laid down")
                sleep("reset")
                continue
            if forced_ is not None:
                a, x, y = int(forced_[0]), int(forced_[1]), int(forced_[2]); pred = ops.predict(f, a) if (use_ops and a != 6) else None
                why = "mind route " + ("op" if pred is not None else "eye")
            elif exp_step is not None:
                a, x, y = exp_step[0], -1, -1; pred = ops.predict(f, a); why = f"exp {exp_step[1]} " + ("op" if pred is not None else "eye")
                if exp_step[1] == "ring": ring_probed.add((ring_target[0], a))
                else:
                    exp["tried"].append(a if exp_step[1] == "try" else "bump")
                    if exp_step[1] == "bump": exp["bump_a"] = a
            elif planned:
                a, x, y = planned[0], -1, -1; pred = ops.predict(f, a); why = f"{'plan' if planned[2] == 'ring' else planned[2]} d{planned[1]} " + ("op" if pred is not None else "eye")
            else:
                (a, x, y), pred, why = P.choose(f, cands, rise if use_rise else None, approach if use_rise else None, nchg, tick,
                                                ops if use_ops else None)
            src = "op" if why.endswith(" op") else "eye"
            k = P._key(f, tick); P.tried[(k, (a, x, y))] = P.tried.get((k, (a, x, y)), 0) + 1
            fr = send("ACTION6", x, y) if a == 6 else send(f"ACTION{a}")
            g = frame_np(fr); n += 1; since += 1; d = (g != f); change_count += d; nchg += d
            hist.append((f, g, a, x, y)); level_hist.append((f, g, a, x, y)); level_lv.append(int(fr.get("levels_completed", 0) or 0))
            touch_ = bool(exp is not None and exp.get("rel") == "src" and exp_step is not None and exp_step[1] == "bump")
            # Oct 16 night: an ordinary experiment's bump into its thing is a touch too, not a test of the move operator
            # (ls20 life 16: the poke that changed the key retired ACTION2 - 'predicted [3] real [0, 1]' at the key - so the
            # refill three presses away became unreachable and the change was lost)
            if exp is not None and exp.get("open") is None and exp_step is not None and exp_step[1] in ("bump", "try"): touch_ = True
            if rel is not None and isinstance(rel, dict) and rel.get("src") is not None:
                _sc = rel["src"]["cells"]; _b0 = body_of(ops, f); _b1 = body_of(ops, g)
                if (_b0 is not None and (_b0 & _sc).any()) or (_b1 is not None and (_b1 & _sc).any()): touch_ = True   # on or off the source: the glyph hides and reappears under the body
            level_touch.append(touch_)
            if use_ops:
                reg_mask = (ops.amb if ops.amb is not None else np.zeros_like(f, dtype=bool)) | tick
                chg = d & ~reg_mask
                fp_ = front_prediction(ops, f, a, x, y)
                unexpl = chg if fp_ is None else (chg & (fp_ != g))
                water += unexpl.astype(float); unexplained_mass += float(unexpl.sum()); explained_mass += float((chg & ~unexpl).sum())
                residue.append(float(unexpl.sum()))
                # the depth: layer 1 is what the front predicted; of the rest, layer 3 is inside a relation's region, layer 2 inside a
                # thing the magnets know (a state answer); what is left runs wall to wall
                depth[1] += float((chg & ~unexpl).sum())
                rest_ = unexpl.copy()
                for r_ in rels or []:
                    y0_, y1_, x0_, x1_ = r_["region"]; m_ = np.zeros_like(rest_); m_[y0_:y1_ + 1, x0_:x1_ + 1] = True
                    depth[3] += float((rest_ & m_).sum()); rest_ &= ~m_
                if mags is not None:
                    for tid_, cells_ in mags.things.items():
                        if tid_.startswith("ACTION") or mags.kind(tid_) in ("empty",): continue
                        depth[2] += float((rest_ & cells_).sum()); rest_ &= ~cells_
                depth[0] += float(rest_.sum())
                fr_ = fence_observe(f, g, a); fence_attach()
                if fr_ == "refused" and exp is not None and exp.get("open") is not None: log(f"  {n:3d}. the border at {exp['id']} broke: the fence learns")
            fill0, fill1 = reg.fill(f), reg.fill(g)
            if fill1 is not None: bar_full_cells = max(bar_full_cells, fill1)
            if met.band is not None:
                b0m_, b1m_ = body_of(ops, f), body_of(ops, g)
                _pos_ = lambda m_: None if m_ is None or not m_.any() else tuple(np.argwhere(m_).min(axis=0).tolist())
                movedm_ = _pos_(b0m_) is not None and _pos_(b1m_) is not None and _pos_(b0m_) != _pos_(b1m_)      # the body's place changed (its pattern may change without moving)
                pm_ = met.predict(movedm_); om_ = met.observe(f, g, movedm_)
                if om_ is not None and pm_ is not None and om_["drained"] != pm_ and not om_["refill"]:
                    log(f"  {n:3d}. meter: the pins said {pm_} cells would drain, {om_['drained']} did")
            if fill0 is not None and fill1 is not None and fill1 >= fill0 + 3:
                refills[vkey(f)] = f; log(f"  {n:3d}. REFILL: the register jumped {fill0} -> {fill1} here; a subgoal that grows the ring ({len(refills)} known)")
                if exp is not None and exp.get("rel") == "ring":                    # the ring stop is over the moment the bar rose: no step back to a ring that is gone
                    experiments.append({"id": exp["id"], "result": "refill", "presses": n - exp["n0"], "rel": "ring"}); log(f"  {n:3d}. route: the ring {exp['id']} refilled the bar; on to the next stop")
                    exp = None
                elif exp is not None and exp.get("open") is None and not exp.get("changed") and int(fr.get("levels_completed", 0) or 0) == lvl and \
                        (lambda b_: b_ is not None and (b_ & exp["cells"]).any())(body_of(ops, g)):   # (not on the winning press: a new level's bar is full too)
                    # Oct 16 night: an ordinary experiment on the ring itself ends when the bar rises, as a REFILL (ls20 life 16
                    # walked into 11@51,40, the bar went 12 -> 84, then it bumped on for 4 presses and filed 'nothing')
                    experiments.append({"id": exp["id"], "result": "refill", "presses": n - exp["n0"], "rel": exp.get("rel")})
                    log(f"  {n:3d}. experiment {exp['id']}: refill (the bar rose as the body reached it)")
                    if not exp.get("rel"): done_exp.add(exp["id"])
                    goals = [c for c in goals if c["id"] != exp["id"]]; exp = None
            if exp_step is not None and exp_step[1] == "ring" and (d & ~(tick | (ops.amb if ops.amb is not None else tick))).any():
                # a hole is a change the operators did NOT predict: an unexplained button did something, or a trusted
                # button that refused here in the model moved the world after all
                predicted = pred is not None and np.array_equal(pred[~tick], g[~tick])
                if not predicted:
                    gaps_found.append({"press": n, "action": a}); log(f"  {n:3d}. hole in the wall: ACTION{a} changed the board unpredicted at a gap state ({int((d & ~tick).sum())} cells)")
            if exp is not None and exp_step is None and exp.get("path") and planned and planned[2] == "plan" and a == exp["path"][0]:
                exp["path"].pop(0)
                if exp.get("expect") is not None and not np.array_equal(exp["expect"][~tick], g[~tick]): exp["deviated"] = True
            if exp is not None and exp_step is not None and exp_step[1] == "bump" and exp.get("sides") is not None:
                if not (d & ~(tick | (ops.amb if ops.amb is not None else tick))).any() or (body_of(ops, g) is not None and body_of(ops, f) is not None and np.array_equal(body_of(ops, g), body_of(ops, f))):
                    exp["sides"].add(a)                                   # refused from this side: another side next
                    if len(exp["sides"]) < 4 and "bump" in exp["tried"]: exp["tried"].remove("bump"); exp["path"] = None
                    log(f"  {n:3d}. bump into {exp['id']} from side {a} refused; sides tried {sorted(exp['sides'])}")
            if exp is not None and exp_step is not None and exp.get("open") is not None and exp_step[1] == "bump":
                b0_ = body_of(ops, f); b1_ = body_of(ops, g)
                moved_ = b0_ is not None and b1_ is not None and not np.array_equal(b0_, b1_)
                experiments.append({"id": exp["id"], "result": "pass" if moved_ else "wall", "presses": n - exp["n0"], "open": True})
                log(f"  {n:3d}. opening {exp['id']}: {'the body went through — the trail goes on' if moved_ else 'a wall — the border broke'}")
                done_exp.add(exp["id"]); goals = [c for c in goals if c["id"] != exp["id"]]; exp = None
            if exp is not None and exp_step is not None:
                b0 = body_of(ops, f); b1 = body_of(ops, g); others = d & ~tick
                if ops.amb is not None: others &= ~ops.amb
                if getattr(reg, "band", None) is not None: others &= ~reg.band            # the register's drain is not the thing answering
                if b0 is not None: others = others & ~b0
                if b1 is not None: others = others & ~b1
                if others.any(): exp["changed"] = True
                if exp["changed"] and exp.get("rel") == "src" and exp_step[1] == "bump":     # the touch is over the moment the region changed: the step off it is the next stop's first move
                    if use_relation_guard and rel is not None: relation_attempts.attempt(rel["rel"])
                    rel_ = exp.get("rel"); experiments.append({"id": exp["id"], "result": "changed", "presses": n - exp["n0"], "rel": rel_})
                    log(f"  {n:3d}. experiment {exp['id']} (relation src): changed after {n - exp['n0']} presses"); exp = None
            if use_ops and not ops.known(a) and a in ops.hyp:
                hv, promoted = ops.test_hypothesis(f, a, x, y, g)   # a press of an unexplained button tries its hypothesis
                if hv is not None:
                    log(f"  {n:3d}. hypothesis for ACTION{a} ({(ops.ops[a] if promoted else ops.hyp[a]).name}): {'held' if hv else 'broke'}"
                        f"{' -> PROMOTED: the circle grows' if promoted else ' (h%.2f)' % ops.hyp_bond.get(a, 0)}")
                    if promoted: ever[a] = ops.ops[a]; hypotheses_promoted.append({"press": n, "action": a, "kind": ops.ops[a].name})
            if use_ops:
                trusted = ops.known(a)
                # the bond is the operator's own: the fence is lifted while it is judged (its walls are judged by the fence's
                # own stats), and a relation-source touch — a press MEANT to change the body — is not a miss
                fens_ = [(op_, op_.fence) for op_ in list(ops.ops.values()) + list(ops.hyp.values()) if getattr(op_, "fence", None) is not None]
                for op_, _ in fens_: op_.fence = None
                verdict = None if touch_ else ops.observe(f, a, x, y, g)              # the bond: trust earned or lost on this press (a touch press is the relation's)
                for op_, fn_ in fens_: op_.fence = fn_
                if verdict is False and trusted:
                    try:
                        P_ = ops.predict(f, a, x, y); D_ = (P_ != g) & ops.mask; ys_, xs_ = np.where(D_)
                        where_ = f" — {int(D_.sum())} cells at rows {ys_.min()}-{ys_.max()} cols {xs_.min()}-{xs_.max()}, predicted {sorted(set(P_[D_].tolist()))} real {sorted(set(g[D_].tolist()))}" if D_.any() else " — no cell differs inside the mask (the operator abstained or the mask moved)"
                    except Exception: where_ = ""
                    log(f"  {n:3d}. operator for ACTION{a} was wrong: bond now {ops.bond.get(a, 0):.2f}" + ("  (retired)" if not ops.known(a) else "") + where_)
            since_level = n - (level_press[0] if level_press else 0)
            if use_ops and (n % refit_every == 0 or since_level == 8) and len(prior) + len(hist) >= 8:
                last_sleep = n; sleep("every %d presses" % refit_every if since_level != 8 else "8 presses into the level")
            if auto and shape and len(shape) - shape_level_start >= 2:
                sh = shape[-1]; lvl_now = int(fr.get("levels_completed", 0) or 0)
                # the cap: three times the human baseline, but never under 150 — a first attempt at a 22-press level
                # still has a whole game's mechanics to learn (ls20 stopped at 66 presses once)
                cap_lv = max(150, 3 * baselines[lvl_now]) if lvl_now < len(baselines) else None
                if rel is not None or any(r_["targets"] for r_ in rels): rel_seen = True
                if cap_lv is not None and rel_seen: cap_lv += 100   # a relation found on this level earns room to finish, and keeps it
                # "nothing left to try" means: every button this level offers is trusted (or clicks), a full segment has been
                # played, the circle stopped growing across two sleeps, the slice covers it, and no candidate is waiting
                all_trusted = all(ops.known(a_) for a_ in avail if a_ != 6)
                matured = n >= 40 and (vresets + resets) >= 1 and len(lvl_shape) >= 2 and lvl_shape[-2]["grew"] <= 0
                # going round returns nothing = the slice stopped growing (three sleeps at the same coverage), whatever the
                # number; a full circle at 95% is the same signal. Either way: the ring.
                lvl_shape = shape[shape_level_start:]
                stalled = len(lvl_shape) >= 3 and all(abs(x_["covered"] - sh["covered"]) < 0.005 and x_["grew"] <= 0 for x_ in lvl_shape[-3:])
                if matured and (sh["covered"] >= 0.95 or stalled) and sh["grew"] <= 0 and exp is None and sh["size"] < 3000:
                    if ring and not ring_done and not ring_mode:
                        # THE RING SEARCH (Jonathan, Sep 4): going round returned nothing, so search where the slice ends —
                        # travel to every gap state and press every button there; a surprise there is a hole in the wall
                        ring_mode = True; log(f"  {n:3d}. the slice covers the circle: ring search over {len(ring)} gap states")
                    elif (ring_done or not ring) and not gaps_found and not goals:
                        stop_reason = f"the slice covers the circle ({sh['size']} states, {sh['covered']:.0%}), the ring was searched, no hole: switch method"
                    elif ring_done and gaps_found:
                        ring_done = False; gaps_found = []; log(f"  {n:3d}. holes were found on the ring: a new circle from there")
                elif cap_lv is not None and since_level >= cap_lv:
                    stop_reason = f"{since_level} presses on level {lvl_now + 1}, three times the human baseline of {baselines[lvl_now]}"
                if stop_reason: log(f"  {n:3d}. stop: {stop_reason}")
            # the undo, where a game offers it (none of the 25 public games does): a probe that changed the board
            # without a level is taken back in one press instead of a reset and a replay
            if use_ops and planned and planned[2] == "probe" and 7 in avail_all and (d & ~tick).any() and int(fr.get("levels_completed", 0) or 0) == lvl:
                fr = send("ACTION7"); g = frame_np(fr); frames.append(g); n += 1; since += 1
                log(f"  {n:3d}. ACTION7 undo after the probe (board changed, no level)")
            if n >= 4: ambient = change_count >= 0.8 * n
            if d.sum() <= 3: tick |= d
            if (d & ~tick).any(): changed += 1
            bg = set(int(v) for v, c in zip(*np.unique(g, return_counts=True)) if c > 900)
            for v, c in zip(*np.unique(g[d & ~tick], return_counts=True)):      # who keeps adding layers = the mover
                if int(c) <= 60 and int(v) not in bg: agent_hist[int(v)] = agent_hist.get(int(v), 0) + int(c)
            sp = P.surprise(f, pred, g, tick)
            nl = int(fr.get("levels_completed", 0) or 0); checkpoint = nl != lvl
            keep = sp > SURPRISE_KEEP or n <= FIRST or checkpoint
            steps = 0
            if keep:
                P.mem.add(f, a, x, y, g, nchg - d, sp + (1.0 if checkpoint else 0.0)); kept += 1
                steps = 8 + int(32 * sp); loss = P.learn(steps)
            r_now = rise(g); near = approach(g)
            rec.append({"n": n, "a": a, "x": x, "y": y, "changed": int(d.sum()), "surprise": round(sp, 3), "kept": keep,
                        "levels": nl, "state": fr["state"], "steps": steps, "rise": r_now, "why": why, "src": src,
                        "dist": (None if near is None else -near), "goals": len(state["goals"]), "mover": state["agent"]})
            if mind is not None and hasattr(mind, "after_press"):
                try: mind.after_press(lvl, since, a, int(d.sum()), round(sp, 3), nl, why)
                except Exception: pass
            if mind is not None and hasattr(mind, "see"):               # Oct 27: her core reads the frame after every press
                try: mind.see(lvl, g, nl, exp.get("id") if isinstance(exp, dict) else None,
                              (rel.get("src") or {}).get("id") if isinstance(rel, dict) and isinstance(rel.get("src"), dict) else None, why)
                except Exception: pass
            if use_ops and sp > 0.5 and not checkpoint and n - last_sleep >= 8:
                last_sleep = n; sleep("surprise marker")
            if n <= 3 or n % 10 == 0 or checkpoint or sp > 0.5:
                log(f"  {n:3d}. {('click (%d,%d)' % (x, y)) if a == 6 else 'ACTION%d' % a:14s} [{why:20s}] changed {int(d.sum()):4d} "
                    f"surprise {sp:.2f} {'KEEP' if keep else 'skip':4s} rise {r_now:4d} mover {state['agent']} goals {len(state['goals'])} "
                    f"dist {('%.0f' % -near) if near is not None else '-':>3s} memory {len(P.mem):3d} levels {nl}")
            if checkpoint:
                log(f">>> LEVEL {nl} at press {n}")
                # THE LEVEL'S LAST WORD (Jonathan, Sep 7: close the accounting gap): the press that opened the goal is in
                # level_hist but no sleep has seen it — the magnets and the pins' eyes are scored once more with it counted
                try:
                    if diag is not None and mags is not None and graph is not None:
                        things_w = [o_ for o_ in graph["objects"] if not o_["id"].startswith(("chg", "place", "wall")) and o_["id"] != "bound"]
                        band_w = (ops.amb if ops.amb is not None else np.zeros_like(f, bool)) | (reg.band if reg.band is not None else np.zeros_like(f, bool))
                        mags_w = magnet.Magnets().build(level_hist, things_w, body_of, ops, band=band_w, levels=level_lv + [nl])
                        floor_w = set()
                        for op_ in ops.ops.values():
                            if isinstance(op_, induce.Displace): floor_w |= op_.floor
                        for p_ in diag.pins: p_["eye"] = {"fired_with": 0, "fired_without": 0, "silent_with": 0, "silent_without": 0}
                        diag.eyes(level_hist, mags_w, band=reg.band, floor=floor_w, matched=relations.matched)
                        log("  the level's last word — " + diag.summary())
                        if diag_log:
                            diag_log[-1]["pins"] = diag.dump(floor=floor_w)
                            diag_log[-1]["question_queue"] = question_queue.update(diag_log[-1]["pins"], step=n)
                            if use_cubes:
                                diag_log[-1]["cube_flow"] = cube_router.local_proposals(diag_log[-1]["question_queue"], f"{n}:{hashlib.sha256(g.tobytes()).hexdigest()[:16]}")
                            diag_log[-1]["last_word"] = True
                except Exception as e_:
                    log(f"  last word failed: {str(e_)[:100]}")
                # THE LEVEL'S LAST LOOK AT ITS RELATIONS (Oct 16 night): a route walk clears a level between two sleeps, so the
                # touches that made the pattern match were never read and no relation went on to the next level (ls20 since
                # Oct 13: level 2 always began blind). Read them once more, with every press of the level counted.
                if mind is not None and not any(r_["targets"] and r_.get("state_patterns") for r_ in rels) and len(level_hist) >= 3:
                    try:
                        hist_ = level_hist[:-1]                                      # up to the frame before the winning press
                        g_last = touch.build([h + (lv,) for h, lv in zip(hist_, level_lv)], log=lambda *_: None, ops=ops, key_fn=vkey)
                        floor_l = set()
                        for op_ in ops.ops.values():
                            if isinstance(op_, induce.Displace): floor_l |= op_.floor
                        amb_l = ops.amb if ops.amb is not None else np.zeros_like(f, dtype=bool)
                        rels_l = relations.find(hist_[-1][1], g_last["edges"], hist_, g_last["objects"], body_of, amb_l, ops, floor_l)
                        new_l = [r_ for r_ in rels_l if r_["targets"] and r_.get("state_patterns")]
                        if new_l:
                            rels = new_l
                            log(f"  the level's last look found {len(new_l)} relation(s): " + "; ".join(f"{r_['src']} -> rows {r_['region'][0]}-{r_['region'][1]} cols {r_['region'][2]}-{r_['region'][3]} -> {r_['targets'][0]['id']}" for r_ in new_l))
                        else:
                            log(f"  the level's last look found no relation ({len(rels_l)} region(s) without a target)")
                    except Exception as e_:
                        log(f"  last look failed: {str(e_)[:100]}")
                start = g.copy(); nchg[:] = 0; tick[:] = False; agent_hist.clear()   # a new level: new ground
                since = 0; life_len = None; reg = Register(); seg_start = n; deaths_lv = []   # a new level: a new budget, a new register
                if exp is not None: experiments.append({"id": exp["id"], "result": "level", "presses": n - exp["n0"]}); log(f"  experiment {exp['id']}: LEVEL")
                prev_level_hist = [h_ for h_, t_ in zip(level_hist, level_touch) if not t_]
                level_hist = []; level_lv = []; level_touch = []; graph = None; goals = []; done_exp = set(); exp = None; retry_at = {}
                ever = {}; ever_keys = set(); ring = []; ring_mode = False; ring_target = None; ring_probed = set(); ring_done = False; refills = {}
                rel_prior = [{"src_colour": int(r_["src"].split("@")[0]), "region": r_["region"], "states": r_.get("state_patterns", []),
                              "target_colours": set(t_["object"].get("colour") for t_ in r_["targets"]), "colour": r_.get("colour")}
                             for r_ in rels if r_["targets"] and r_.get("state_patterns")] or rel_prior
                if mind is not None:                     # THE JOINT BETWEEN LEVELS (Oct 16 night): her memory of relations across lives
                    try:
                        if any(r_["targets"] and r_.get("state_patterns") for r_ in rels) and hasattr(mind, "relations_learned"):
                            mind.relations_learned(nl - 1, rel_prior)
                        elif not rel_prior and hasattr(mind, "relations_for"):
                            rel_prior = mind.relations_for(nl) or []
                    except Exception as e_:
                        log(f"  mind relations failed: {str(e_)[:100]}")
                if rel_prior: log(f"  relations carried to the next level: {[(p_['src_colour'], sorted(p_['target_colours']), 'read in colour %s' % p_['colour']) for p_ in rel_prior]}")
                reg_pins = pins.Pins(); level_lines = []; rels = []; rel = None; rel_seen = False; ring_rel = None
                relation_attempts = RelationAttempts()
                try:
                    json.dump({"pins": met.pins.tolist() if met.pins is not None else None, "axis": met.axis, "direction": met.direction, "end": met.end,
                               "band": [[int(v) for v in r_] for r_ in np.argwhere(met.band)[[0, -1]]] if met.band is not None else None, **{k_: v_ for k_, v_ in met.stats().items()}},
                              open(os.path.join(OUT, f"meter_{gid.split('-')[0]}_L{nl}.json"), "w"), indent=1)
                except Exception: pass
                met = meter.Meter()
                try: fen.save(os.path.join(OUT, f"fence_{gid.split('-')[0]}_L{nl}.npz"))
                except Exception: pass
                try: json.dump(diag_log[-1] if diag_log else {}, open(os.path.join(OUT, f"diagonal_{gid.split('-')[0]}_L{nl}.json"), "w"), indent=1)
                except Exception: pass
                try:
                    if vw is not None: vw.save(os.path.join(OUT, f"views_{gid.split('-')[0]}_L{nl}.json"))
                except Exception as e_: log(f"  views save failed: {str(e_)[:80]}")
                diag = None; vw = None
                question_queue = pin_questions.QuestionQueue(f"{gid}:level:{nl}")
                carried_rules_ = fen.rules_merged()
                fen = fence.Fence(f.shape); fen.prior = carried_rules_; fence_attach()
                route_plan = None; bar_full_cells = 0
                try:
                    np.save(os.path.join(OUT, f"water_{gid.split('-')[0]}_L{nl}.npy"), water)
                    json.dump({"antennas": antennas, "explained": explained_mass, "unexplained": unexplained_mass}, open(os.path.join(OUT, f"antennas_{gid.split('-')[0]}_L{nl}.json"), "w"), indent=1)
                except Exception: pass
                water = np.zeros_like(f, dtype=float); explained_mass = 0.0; unexplained_mass = 0.0; antennas = []; shape_level_start = len(shape); last_size = 0
                residue = []; cause = {}
                depth = {1: 0.0, 2: 0.0, 3: 0.0, 0: 0.0}
                if use_ops:                                     # trust is per level: keep the operators, restart their bonds, forget the places
                    visited.clear(); probed.clear(); level_press[:] = [n]
                    for a_ in list(ops.bond): ops.bond[a_] = ops.BOND_START
                    for op_ in list(ops.ops.values()) + list(ops.hyp.values()):   # the last level's walls, bounds and fans are not this level's
                        if isinstance(op_, induce.Displace): op_.blocked = set(); op_.bounds = set(); op_.rides = {}; op_.wrap_at = set()
                    log(f"  new level: bonds reset, places forgotten; operators {ops.summary() or 'none'}")
            lvl = nl; f = g; frames.append(g)
            if fr["state"] == "WIN": log("  WIN"); break
            if fr["state"] == "GAME_OVER":
                resets += 1
                life_len = since if life_len is None else min(life_len, since)   # the death teaches the budget
                rem_d = reg.remaining(f, since, deaths_lv)
                segments.append({"start": seg_start, "end": n, "presses": since, "ended": "death", "budget_left": None if rem_d is None else round(rem_d, 1), "margin": margin})
                deaths_lv.append((seg_fill, since))                           # the death teaches the budget directly
                if rem_d is not None and rem_d > margin: margin += 2            # wrong by more than the margin: widen it
                clean = 0
                dd = [f0 / nn for f0, nn in deaths_lv if f0 and nn]
                log(f"  {n:3d}. death after {since} presses; budget model said {('%.0f' % rem_d) if rem_d is not None else '?'} left"
                    + (f"; death-drain now {max(dd):.2f} cells/press" if dd else "") + f"; margin {margin}")
                since = 0; seg_start = n
                if resets > 10: break
                fr = send("RESET"); f = frame_np(fr); frames.append(f)
                if exp is not None: exp["path"] = None; exp["deviated"] = False
                if exp is not None and exp.get("rel"): exp = None
                if rel is not None: rel["tries"] = 0
                if rel is not None and mind is not None and hasattr(mind, "allow_relation"):
                    try:
                        if not mind.allow_relation(lvl, rel["rel"], reset=True): rel = None   # Oct 27: and at a death
                    except Exception: pass
                route_plan = None; met.stand(f)
                start = f.copy(); nchg[:] = 0                      # back to the level's start
                sleep("death")
        bins = {}
        action_recs = action_records(rec)
        for r in action_recs: bins.setdefault((r["n"] - 1) // 20, []).append(r["kept"])
        rate = [round(sum(v) / len(v), 2) for k, v in sorted(bins.items())]
        op_rows = [r for r in action_recs if r["src"] == "op"]; eye_rows = [r for r in action_recs if r["src"] == "eye" and r["why"] != "touch eye"]
        planned_rows = [r for r in action_recs if r["why"].startswith("plan")]
        row = {"game": gid, "presses": n, "changed": changed, "kept": kept, "levels": lvl, "resets": resets, "rise": use_rise,
               "scorecard_id": cid, "seed": seed,
               "recorded_actions": len(action_recs), "reset_records": len(rec) - len(action_recs),
               "configuration": {"use_ops": use_ops, "use_prior": use_prior, "use_cubes": use_cubes, "use_relation_guard": use_relation_guard},
               "level_presses": [r["n"] for i, r in enumerate(rec) if r["levels"] > (rec[i - 1]["levels"] if i else 0)],
               "state": fr["state"], "record_rate_per_20": rate, "eye_steps": P.steps, "seconds": round(time.time() - t0),
               "mean_surprise_first20": round(float(np.mean([r["surprise"] for r in action_recs[:20]])), 3) if action_recs else None,
               "mean_surprise_last20": round(float(np.mean([r["surprise"] for r in action_recs[-20:]])), 3) if action_recs else None,
               "ops": ops.summary() if use_ops else None, "op_presses": len(op_rows), "prior_touches": len(prior),
               "bonds": {int(a): round(b, 3) for a, b in ops.bond.items()} if use_ops else None,
               "rhythm": ops.rhythm.objects if use_ops and ops.rhythm.ok else [],
               "planned_presses": len(planned_rows), "places_visited": len(visited),
               "voluntary_resets": vresets, "deaths": resets, "life_len": life_len,
               "budget": {"colour": reg.colour, "drain": reg.drain, "margin": margin}, "segments": segments,
               "experiments": experiments, "shape": shape, "stop": stop_reason, "auto": auto,
               "ring": {"searched": ring_done, "holes": gaps_found, "refills": len(refills)}, "promoted": hypotheses_promoted,
               "pins": reg_pins.stats(), "lines": lines_log[-1] if lines_log else None, "relations": rel_log,
               "water": {"explained": explained_mass, "unexplained": unexplained_mass, "antennas": antennas},
               "fence": fen_log[-1] if fen_log else None, "openings_tried": [e_ for e_ in experiments if e_.get("open")],
               "rings": ring_log[-1] if ring_log else None,
               "route": None if not route_plan else {"stops": [st[0] + ("" if not isinstance(st[1], dict) else " " + st[1]["id"]) for st in route_plan[0]], "moves": route_plan[1]},
               "meter": met_log[-1] if met_log else None,
               "magnets": mag_log[-1] if mag_log else None,
               "diagonal": diag_log[-1] if diag_log else None,
               "relation_guard": relation_attempts.snapshot() if use_relation_guard else None,
               "views": vw_log[-1] if vw_log else None,
               "depth": depth_log[-1] if depth_log else None,
               "surprise_op": round(float(np.mean([r["surprise"] for r in op_rows])), 3) if op_rows else None,
               "surprise_eye": round(float(np.mean([r["surprise"] for r in eye_rows])), 3) if eye_rows else None}
        log(f"  done: levels {lvl} presses {n} changed {changed} kept {kept} record-rate/20 {rate} "
            f"surprise first20 {row['mean_surprise_first20']} last20 {row['mean_surprise_last20']} ({row['seconds']}s)")
        if use_ops: log(f"  world model: {row['ops'] or 'none gated'} | presses imagined by operator {len(op_rows)}/{n}, planned {len(planned_rows)}, "
                        f"places visited {len(visited)} | surprise op {row['surprise_op']} vs eye {row['surprise_eye']} | "
                        f"deaths {resets}, voluntary resets {vresets}, life {life_len}")
        if use_ops: log(f"  segments: " + " ".join(f"{s['presses']}{'d' if s['ended'] == 'death' else 'r'}" for s in segments)
                        + f" | budget colour {reg.colour} drain {reg.drain} margin {margin}")
        if use_ops: log(f"  experiments: " + (", ".join(f"{e['id']} -> {e['result']} ({e['presses']})" for e in experiments) or "none"))
        if use_ops and shape: log(f"  shape over the run: " + " ".join(f"{s_['size']}@{s_['covered']:.0%}" for s_ in shape) + (f" | stop: {stop_reason}" if stop_reason else " | ran to the press limit"))
        if use_ops and reg_pins.pins: log(f"  pins at the end: {reg_pins.summary()}")
        if use_ops:
            try: json.dump(diag_log[-1] if diag_log else {}, open(os.path.join(OUT, f"diagonal_{gid.split('-')[0]}.json"), "w"), indent=1)
            except Exception: pass
            try:
                if vw is not None: vw.save(os.path.join(OUT, f"views_{gid.split('-')[0]}.json"))
            except Exception: pass
            try:
                fen.save(os.path.join(OUT, f"fence_{gid.split('-')[0]}.npz"))
                fence.save_rules(os.path.join(OUT, f"fence_rules_{gid.split('-')[0]}.json"), fen.rules_merged())   # the pins persist to the next run
            except Exception: pass
            try:
                np.save(os.path.join(OUT, f"water_{gid.split('-')[0]}.npy"), water)
                json.dump(antennas, open(os.path.join(OUT, f"antennas_{gid.split('-')[0]}.json"), "w"), indent=1)
            except Exception: pass
        if use_ops and level_lines:
            try:
                json.dump([{k: (list(v) if isinstance(v, tuple) else v) for k, v in l.items() if k != "owner"} | {"owner_colour": (l["owner"][0] if l["owner"] else None)} for l in level_lines],
                          open(os.path.join(OUT, f"lines_{gid.split('-')[0]}.json"), "w"), indent=1)
            except Exception: pass
        if save:
            os.makedirs(OUT, exist_ok=True)
            np.savez_compressed(os.path.join(OUT, f"play_{gid.split('-')[0]}.npz"), F=np.array(frames, dtype=np.int8))
            with open(os.path.join(OUT, f"play_{gid.split('-')[0]}.jsonl"), "w", encoding="utf-8") as fh:
                for r in rec: fh.write(json.dumps(r) + "\n")
        return row
    finally:
        try:
            card = api("/api/scorecard/close", key, {"card_id": cid})
            if save:
                from evaluation_batch import atomic_json
                card_file = os.path.join(OUT, f"scorecard_{hashlib.sha256(str(cid).encode()).hexdigest()[:16]}.json")
                atomic_json(card_file, card)
                if "row" in locals(): row["scorecard_file"] = card_file
            for env_ in (card.get("environments") or []):
                if str(env_.get("id", "")).startswith(gid.split("-")[0]):
                    for run_ in (env_.get("runs") or []):
                        lb = run_.get("level_baseline_actions")
                        if lb:
                            b = load_baselines(BASELINES); b[gid.split("-")[0]] = lb
                            os.makedirs(OUT, exist_ok=True); json.dump(b, open(BASELINES, "w", encoding="utf-8"), indent=1)
                            log(f"  human baselines for {gid.split('-')[0]}: {lb} (saved)")
        except Exception as e:
            log(f"  scorecard close/save failed: {str(e)[:180]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game", nargs="?"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--presses", default="150", help="a number, or 'auto': run until the slice covers the model's closure (cap 600, or 3x the human baseline per level once known)")
    ap.add_argument("--device", default=None)
    ap.add_argument("--summary", action="store_true"); ap.add_argument("--no-rise", action="store_true", help="curiosity only")
    ap.add_argument("--no-ops", action="store_true", help="eye only, no induced operators")
    ap.add_argument("--no-prior", action="store_true", help="no cached transitions, fence rules, or human baselines; within-run learning remains")
    ap.add_argument("--output-dir", default=None, help="isolated directory for this run's data and scorecards")
    ap.add_argument("--seed", type=int, default=None, help="seed Python, NumPy, and Torch; not a guarantee of GPU determinism")
    ap.add_argument("--no-cubes", action="store_true", help="disable local helper-cube proposals for overhead comparisons")
    ap.add_argument("--no-relation-guard", action="store_true", help="baseline comparison: allow restarting exhausted relation hypotheses")
    a = ap.parse_args()
    a.presses = 0 if str(a.presses).lower() == "auto" else int(a.presses)
    if a.summary:
        files = sorted(glob.glob(os.path.join(OUT, "play_batch_*.jsonl")))
        if not files: print("no play batch yet"); return
        rows = [json.loads(l) for l in open(files[-1], encoding="utf-8") if l.strip()]
        summary(rows, files[-1]); return
    import arc_daily
    key = arc_daily.get_key()
    from arc3_client import api
    games = [g["game_id"] for g in api("/api/games", key)]
    if not a.all:
        games = [g for g in games if g.startswith(a.game or "vc33")]
        play_game(games[0], key, a.presses, a.device, use_rise=not a.no_rise, use_ops=not a.no_ops, use_prior=not a.no_prior, use_cubes=not a.no_cubes, use_relation_guard=not a.no_relation_guard, output_dir=a.output_dir, seed=a.seed); return
    batch_out = os.path.abspath(a.output_dir or OUT); os.makedirs(batch_out, exist_ok=True)
    path = os.path.join(batch_out, f"play_batch_{time.strftime('%Y%m%d_%H%M')}.jsonl")
    rows = []
    for i, gid in enumerate(games):
        print(f"[{i + 1}/{len(games)}]", flush=True)
        try: row = play_game(gid, key, a.presses, a.device, use_rise=not a.no_rise, use_ops=not a.no_ops, use_prior=not a.no_prior, use_cubes=not a.no_cubes, use_relation_guard=not a.no_relation_guard, output_dir=a.output_dir, seed=a.seed)
        except Exception as e: row = {"game": gid, "error": str(e)[:200]}; print("  error", row["error"])
        rows.append(row)
        with open(path, "a", encoding="utf-8") as fh: fh.write(json.dumps(row) + "\n")
    summary(rows, path)


def summary(rows, path):
    played = [r for r in rows if "levels" in r]
    print(f"\nlearn-by-playing ({os.path.basename(path)}): {len(played)} games, levels {sum(r['levels'] for r in played)}, "
          f"games with >= 1 level {sum(1 for r in played if r['levels'] >= 1)}")
    print(f"  {'game':6s} {'levels':>6s} {'changed':>8s} {'kept':>5s}  record-rate per 20 presses          surprise first/last 20   op-presses  surprise op/eye  operators")
    for r in sorted(played, key=lambda r: -r["levels"]):
        print(f"  {r['game'][:4]:6s} {r['levels']:6d} {r['changed']:4d}/{r['presses']:<3d} {r['kept']:5d}  {str(r['record_rate_per_20']):36s} "
              f"{r['mean_surprise_first20']} / {r['mean_surprise_last20']}  at {r.get('level_presses', [])}  "
              f"{r.get('op_presses', 0):3d}  {r.get('surprise_op')} / {r.get('surprise_eye')}  {r.get('ops') or '-'}")


if __name__ == "__main__":
    main()
