# =====================================================================
# PriorAgent — the consolidated-prior generic engine (Vesica AI / Shovelcat)
# Distilled from live LS20 solves (levels 1-5 at 13/22, 47/123, 47/73, 50/84,
# 58/96 vs human baselines). The transferable layer only:
#   probe-first  : classify what each action does before planning
#   agent-blob   : find the movable 'self' by frame-diffing, learn its lattice
#   landmarks    : small distinct objects are goals/tools; visit them
#   wind-learning: an action that jumps the blob >2 quanta is a transport;
#                  ban the edge for planning, remember the ride
#   novelty      : state-hash graph; prefer the least-tried action from here;
#                  never loop on a proven no-op
#   budget law   : refills exist; a bar that only drains means actions are the
#                  budget — never spend two on the same failed idea
# =====================================================================
import random
import hashlib
import time
from collections import defaultdict, deque
from typing import Any, Optional

import numpy as np

try:
    from agents.agent import Agent
    from arcengine import FrameData, GameAction, GameState
except ImportError:                      # local practice: the shim provides the same surface
    from arcshim import Agent, FrameData, GameAction, GameState

MOVE_ACTIONS = [GameAction.ACTION1, GameAction.ACTION2,
                GameAction.ACTION3, GameAction.ACTION4]


def _grid(latest_frame: FrameData) -> Optional[np.ndarray]:
    fr = latest_frame.frame
    if fr is None or len(fr) == 0:
        return None
    g = np.asarray(fr[-1], dtype=np.int16)
    return g if g.ndim == 2 else None


def _label(mask: np.ndarray):
    """4-connected components without scipy: returns list of (ys, xs) arrays."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                ys, xs = [], []
                while q:
                    cy, cx = q.popleft()
                    ys.append(cy); xs.append(cx)
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] \
                                and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                comps.append((np.array(ys), np.array(xs)))
    return comps


class PriorAgent(Agent):
    """Generic probe-first explorer with landmark navigation."""

    MAX_ACTIONS = 2000
    CANDIDATE_VERSION = "reliability-1"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        seed = kwargs.pop("candidate_seed", None)
        self.mask_ambient = kwargs.pop("mask_ambient", True)
        self.probe_actions = kwargs.pop("probe_actions", True)
        super().__init__(*args, **kwargs)
        self.seed = int(seed) if seed is not None else int.from_bytes(
            hashlib.blake2b(str(self.game_id).encode("utf-8"), digest_size=8).digest(), "big")
        self.rng = random.Random(self.seed)
        self.prev_grid: Optional[np.ndarray] = None
        self.prev_action: Optional[int] = None
        self.prev_blob: Optional[tuple] = None
        self.effects: dict = defaultdict(lambda: {"moved": 0, "changed": 0,
                                                  "noop": 0, "dy": [], "dx": []})
        self.visit: dict = defaultdict(int)          # state-hash -> visits
        self.tried: dict = defaultdict(lambda: defaultdict(int))
        self.banned: set = set()                     # (state_hash, action_val)
        self.plan: deque = deque()                   # queued action values
        self.plan_target: Optional[tuple] = None
        self.landmark_seen: dict = defaultdict(int)
        self.quantum: int = 0                        # movement lattice, learned
        self.level_at: int = 0
        self.click_targets: deque = deque()
        self.move_block: dict = defaultdict(int)     # (blob,action) -> blocked count
        self.walkable: set = set()                   # colors proven standable
        self.walls: set = set()                      # colors proven blocking
        self.mysteries: list = []                    # unexplained big changes (from the
                                                     # Learning pool: mystery tracking)
        self.steps: int = 0
        self.self_colors: set = set()                # learned per-game self palette
        self.last_progress: int = 0                  # step of last level-up/reset
        self.click_chain: deque = deque()            # productive-click follow-ups
        self.ambient = None
        self.change_count = None
        self.press_count = 0
        self.ambient_actions = set()
        self.bar_candidates = {}
        self.noop_at = defaultdict(int)
        self.probe_queue = deque()
        self._probe_level = None

    # ---------- lifecycle ----------
    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state == GameState.WIN

    def _boundary(self, *, new_level=False):
        """A reset/new board is not an observation of the last game action."""
        self.prev_grid = self.prev_action = self.prev_blob = None
        self._last_click = None
        self.plan.clear(); self.plan_target = None
        self.goal = None
        self.visit.clear(); self.tried.clear(); self.banned.clear(); self.noop_at.clear()
        self.landmark_seen.clear(); self.move_block.clear(); self.click_chain.clear()
        self.mysteries.clear()
        if hasattr(self, "sweep"): del self.sweep
        self.last_progress = self.steps
        if new_level:
            # Colours, lattice and noise belong to a board; action statistics may transfer.
            self.walkable.clear(); self.walls.clear(); self.self_colors.clear()
            self.quantum = 0
            self.ambient = self.change_count = None
            self.press_count = 0; self.ambient_actions.clear()
            self.bar_candidates.clear()
            self.probe_queue.clear(); self._probe_level = None
            self.click_gain = defaultdict(int); self.click_n = 0

    def _diff(self, g, prev):
        changed = g != prev
        if self.mask_ambient and self.ambient is not None and self.ambient.shape == g.shape:
            changed &= ~self.ambient
        return changed

    def _note_change(self, g, prev):
        """Small, recurring changes across several controls are ambient candidates.

        This is a heuristic, not causal proof. Keep the self's known pixels and
        reject large masks. A single repeatedly toggled control is insufficient.
        """
        if not self.mask_ambient or g.shape != prev.shape: return
        if self.change_count is None or self.change_count.shape != g.shape:
            self.change_count = np.zeros(g.shape, dtype=np.int32)
            self.press_count = 0; self.ambient_actions.clear()
            self.bar_candidates.clear()
        self.change_count += (g != prev)
        self.press_count += 1
        if self.prev_action is not None: self.ambient_actions.add(self.prev_action)
        bars = self._bar_mask(g, prev)
        mask = np.zeros(g.shape, dtype=bool)
        if self.press_count >= 8 and len(self.ambient_actions) >= 3:
            mask = (self.change_count >= 0.8 * self.press_count) | bars
            if self.self_colors:
                mask &= ~np.isin(g, list(self.self_colors)) & ~np.isin(prev, list(self.self_colors))
            if mask.sum() > 0.1 * mask.size: mask[:] = False
        previous = self.ambient if self.ambient is not None else np.zeros_like(mask)
        if not np.array_equal(mask, previous):
            # Keys from a different observation abstraction must never be reused.
            self.visit.clear(); self.banned.clear(); self.noop_at.clear()
            for key in list(self.tried):
                if not isinstance(key, tuple) or key[0] != "pos": del self.tried[key]
        self.ambient = mask

    def _bar_mask(self, g, prev):
        """Infer simple two-colour horizontal edge bars, not arbitrary HUD bands.

        A shrinking bar changes different cells each press. Require a single
        colour boundary, eight observations, frequent change and a moving edge
        spanning several cells. A new colour/shape invalidates the hypothesis.
        Raw frames remain intact; this mask is only for novelty/effect accounting.
        """
        mask = np.zeros(g.shape, bool)
        h, w = g.shape
        if h < 16 or w < 32: return mask
        for y in (0, 1, h - 3, h - 2, h - 1):
            a, b = prev[y], g[y]
            palette = tuple(int(v) for v in np.unique(np.concatenate((a, b))))
            if (len(palette) != 2 or np.count_nonzero(a[1:] != a[:-1]) > 1
                    or np.count_nonzero(b[1:] != b[:-1]) > 1):
                self.bar_candidates.pop(y, None)
                continue
            stat = self.bar_candidates.get(y)
            if stat is None or stat["palette"] != palette:
                stat = {"palette": palette, "seen": 0, "changed": 0, "swept": np.zeros(w, bool)}
                self.bar_candidates[y] = stat
            stat["seen"] += 1
            changed = a != b
            stat["changed"] += bool(changed.any()); stat["swept"] |= changed
            if (stat["seen"] >= 8 and stat["changed"] >= 0.8 * stat["seen"]
                    and stat["swept"].sum() >= max(4, w // 8)):
                mask[y] = True
        return mask

    # ---------- perception ----------
    def _blob(self, g: np.ndarray) -> Optional[tuple]:
        """The movable self. Palette detector FIRST (exact position); frame-diff
        as fallback, using the two-component trick: a move leaves an old-spot and
        a new-spot — the distance between their centroids is the exact quantum
        (the diff-centroid alone halves it: the L S20 lesson, twice-paid)."""
        if self.self_colors:                       # learned palette for THIS game
            m = np.isin(g, sorted(self.self_colors))
            comps = [c for c in _label(m) if 1 <= len(c[0]) <= 300]   # v10: 1-px selves exist
            if len(comps) == 1:
                ys, xs = comps[0]
                self._blob_kind = "palette"
                return (int(ys.mean()), int(xs.mean()))
        m = np.isin(g[:56], [9, 12])
        if m.any():
            for ys, xs in _label(m):
                if len(ys) >= 15:
                    vals = g[ys, xs]
                    if (vals == 12).any():
                        self._blob_kind = "palette"
                        return (int(ys.mean()), int(xs.mean()))
        if self.prev_grid is not None and g.shape == self.prev_grid.shape:
            diff = self._diff(g, self.prev_grid)
            nd = int(diff.sum())
            if 0 < nd <= 200:
                comps = sorted(_label(diff), key=lambda c: -len(c[0]))
                if len(comps) == 1 and nd <= 8:
                    # v10: a 1-quantum move leaves ADJACENT old+new cells that merge into one
                    # component — split it by which pixels became background (left) vs colored (entered)
                    ys, xs = comps[0]
                    vals_u, counts_u = np.unique(g, return_counts=True)
                    bg_u = set(int(v) for v, c in zip(vals_u, counts_u) if c > 900)
                    now_vals = g[ys, xs]
                    new_i = [i for i in range(len(ys)) if int(now_vals[i]) not in bg_u]
                    old_i = [i for i in range(len(ys)) if int(now_vals[i]) in bg_u]
                    if new_i and old_i:
                        c1 = (float(np.mean([ys[i] for i in new_i])), float(np.mean([xs[i] for i in new_i])))
                        c0 = (float(np.mean([ys[i] for i in old_i])), float(np.mean([xs[i] for i in old_i])))
                        d = int(round(max(abs(c0[0] - c1[0]), abs(c0[1] - c1[1]))))
                        if 0 < d <= 10 and self.quantum == 0:
                            self.quantum = d
                        cols = set(int(now_vals[i]) for i in new_i) - bg_u
                        if cols and len(cols) <= 4:
                            self.self_colors |= cols
                        self._blob_kind = "diff-adjacent"
                        return (int(round(c1[0])), int(round(c1[1])))
                if len(comps) >= 2 and len(comps[1][0]) >= 0.4 * len(comps[0][0]):
                    c0 = (comps[0][0].mean(), comps[0][1].mean())
                    c1 = (comps[1][0].mean(), comps[1][1].mean())
                    d = int(round(max(abs(c0[0] - c1[0]), abs(c0[1] - c1[1]))))
                    if 0 < d <= 10 and self.quantum == 0:
                        self.quantum = d          # exact old->new displacement
                    # the NEW spot: whichever component's pixels are non-background now
                    ys, xs = comps[0]
                    # learn the self palette: the moving component's current colors
                    vals, counts = np.unique(g, return_counts=True)
                    bg = set(int(v) for v, c in zip(vals, counts) if c > 900)
                    cols = set(int(v) for v in g[ys, xs]) - bg
                    if cols and len(cols) <= 4:
                        self.self_colors |= cols
                    self._blob_kind = "diff2"
                    return (int(ys.mean()), int(xs.mean()))
                ys, xs = comps[0]
                self._blob_kind = "diff"
                return (int(ys.mean()), int(xs.mean()))
        return None

    def _landmarks(self, g: np.ndarray) -> list:
        """Small rare-color components: goals, stations, rings, keyholes."""
        out = []
        vals, counts = np.unique(g, return_counts=True)
        bg = set(int(v) for v, c in zip(vals, counts) if c > 900)
        for v in vals:
            v = int(v)
            if v in bg:
                continue
            comps = _label(g == v)
            if len(comps) > 4:
                continue          # v10: a color scattered as MANY pieces is texture/walls, not a goal
            for ys, xs in comps:
                if 1 <= len(ys) <= 120:   # v10: a landmark can be a single pixel (keys, doors)
                    out.append((v, int(ys.mean()), int(xs.mean()), len(ys)))
        return out

    def _hash(self, g: np.ndarray) -> int:
        visible = np.array(g, dtype="<i2", copy=True)
        mask = np.zeros(g.shape, bool)
        if self.mask_ambient and self.ambient is not None and self.ambient.shape == g.shape:
            mask = self.ambient
            visible[mask] = 0
        raw = np.asarray(g.shape, dtype="<i4").tobytes() + mask.tobytes() + visible.tobytes()
        return int.from_bytes(hashlib.blake2b(raw, digest_size=16).digest(), "big")

    # ---------- planning ----------
    DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}

    def _learn_wall(self, g, blob, a):
        """the window just beyond the blob in direction a blocked us: its colors
        (not already proven floor) are walls"""
        q = max(1, self.quantum); r = max(1, q // 2)
        dy, dx = self.DIRS[a]
        y, x = blob[0] + dy * q, blob[1] + dx * q
        h, w = g.shape
        if not (r <= y < h - r and r <= x < w - r): return
        win = g[y - r:y + r + 1, x - r:x + r + 1]
        for v in set(int(t) for t in win.flatten()):
            if v not in self.walkable:
                self.walls.add(v)

    def _learn_floor(self, g_before, new_blob):
        """we now stand where g_before shows the old colors: they were passable"""
        r = max(1, self.quantum // 2)
        y, x = new_blob
        h, w = g_before.shape
        if not (r <= y < h - r and r <= x < w - r): return
        win = g_before[y - r:y + r + 1, x - r:x + r + 1]
        for v in set(int(t) for t in win.flatten()):
            self.walkable.add(v)
            self.walls.discard(v)

    def _passable(self, g, y, x, r) -> bool:
        h, w = g.shape
        if not (r <= y < h - r and r <= x < w - r):
            return False
        if not self.walkable:                          # seed: the global mode color
            vals, counts = np.unique(g, return_counts=True)
            self.walkable.add(int(vals[np.argmax(counts)]))
        win = g[y - r:y + r + 1, x - r:x + r + 1]
        ok = 0; tot = 0
        for v in win.flatten():
            v = int(v); tot += 1
            if v in self.walls: return False
            if v in self.walkable: ok += 1
        return ok >= tot * 0.5                         # unknown colors: allowed if half known-floor

    def _bfs_step(self, g, start, goal, q) -> Optional[int]:
        """First move action value of a shortest lattice path start->goal."""
        r = max(1, q // 2)
        dq = deque([(start, None)])
        seen = {start}
        parent = {}
        deltas = {1: (-q, 0), 2: (q, 0), 3: (0, -q), 4: (0, q)}
        found = None
        while dq:
            p, first = dq.popleft()
            if abs(p[0] - goal[0]) + abs(p[1] - goal[1]) <= q:
                found = first
                break
            for a, (dy, dx) in deltas.items():
                np_ = (p[0] + dy, p[1] + dx)
                if np_ in seen or not self._passable(g, np_[0], np_[1], r):
                    continue
                seen.add(np_)
                dq.append((np_, first if first is not None else a))
        return found

    # ---------- the policy ----------
    def choose_action(self, frames, latest_frame) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self._boundary()
            return GameAction.RESET

        g = _grid(latest_frame)
        if g is None:
            self._boundary()
            return GameAction.RESET

        # level change: clear per-level state, keep learned action effects
        if (latest_frame.levels_completed != self.level_at
                or (self.prev_grid is not None and g.shape != self.prev_grid.shape)):
            self.level_at = latest_frame.levels_completed
            self._boundary(new_level=True)

        # stuck escape: long time on this level AND we mostly revisit known
        # states -> RESET restarts the level with a clean board (spent
        # resources, dead-end configurations, wasted rings all come back)
        if self.steps - self.last_progress > 300:
            self._boundary()
            return GameAction.RESET

        if self.prev_grid is not None and self.prev_action is not None:
            self._note_change(g, self.prev_grid)
        hsh = self._hash(g)
        self.visit[hsh] += 1
        self.steps += 1
        if self.steps % 40 == 0 and self.move_block:
            # negative confirmation (Learning pool): walls may be doors later —
            # halve the block evidence periodically so bans get re-tested
            for k in list(self.move_block):
                self.move_block[k] //= 2
        blob = self._blob(g)

        # learn from the previous action's observed effect
        if self.prev_grid is not None and self.prev_action is not None:
            eff = self.effects[self.prev_action]
            mag = int(self._diff(g, self.prev_grid).sum()) \
                if g.shape == self.prev_grid.shape else 0
            changed = mag > 0
            if not changed:
                eff["noop"] += 1
                if self.prev_action in (1, 2, 3, 4) and self.prev_blob is not None:
                    self.move_block[(self.prev_blob, self.prev_action)] += 1
                    self._learn_wall(g, self.prev_blob, self.prev_action)
                ph = self._hash(self.prev_grid)
                self.noop_at[(ph, self.prev_action)] += 1
                if self.noop_at[(ph, self.prev_action)] >= 3:
                    self.banned.add((ph, self.prev_action))
            else:
                ph = self._hash(self.prev_grid)
                self.noop_at.pop((ph, self.prev_action), None)
                self.banned.discard((ph, self.prev_action))
                eff["changed"] += 1
                if mag > 60 and self.prev_action in (1, 2, 3, 4):
                    # a big change no movement explains: remember WHERE (surprise
                    # priority — predictive validation: encode what defied the guess)
                    diff = self._diff(g, self.prev_grid)
                    ys, xs = np.where(diff)
                    self.mysteries.append((int(ys.mean()), int(xs.mean())))
                    self.mysteries = self.mysteries[-6:]
                if self.prev_action in (1, 2, 3, 4) and blob is not None \
                        and self.prev_blob is not None and blob == self.prev_blob:
                    # the move was BLOCKED even though pixels changed (a draining
                    # bar is ambient noise, not progress — the LS20 wall-spam bug)
                    self.move_block[(self.prev_blob, self.prev_action)] += 1
                    self._learn_wall(g, blob, self.prev_action)
                elif self.prev_action in (1, 2, 3, 4) and blob is not None \
                        and self.prev_blob is not None and blob != self.prev_blob:
                    self._learn_floor(self.prev_grid, blob)
                if self.prev_action == 6 and getattr(self, "_last_click", None) \
                        and mag >= 4:                     # ignore 1-2px cursor noise
                    if getattr(self, "click_gain", None) is None:
                        self.click_gain = defaultdict(int)
                    self.click_gain[self._last_click] += 1
                    # chain: a productive click earns an immediate replay of the
                    # same spot, then its 8-lattice neighbors (FT09: placements
                    # live on an 8-spaced grid and repeat until the cell is full)
                    cx, cy = self._last_click
                    if len(self.click_chain) < 12:
                        self.click_chain.append((cx, cy))
                        for ddx, ddy in ((8, 0), (0, 8), (-8, 0), (0, -8)):
                            self.click_chain.append((cx + ddx, cy + ddy))
                if blob is not None and self.prev_blob is not None:
                    dy = blob[0] - self.prev_blob[0]
                    dx = blob[1] - self.prev_blob[1]
                    if dy or dx:
                        eff["moved"] += 1
                        eff["dy"].append(dy); eff["dx"].append(dx)
                        step = max(abs(dy), abs(dx))
                        if 0 < step <= 8 and getattr(self, "_blob_kind", "") == "palette":
                            self.quantum = step   # exact when the palette detector holds

        self.prev_grid = g.copy()
        self.prev_blob = blob

        avail = latest_frame.available_actions or []
        avail_vals = []
        for a in avail:
            try:
                value = int(getattr(a, "value", a))
                if 1 <= value <= 6: avail_vals.append(value)
            except (TypeError, ValueError):
                pass
        if not avail_vals: avail_vals = [1, 2, 3, 4, 5, 6]

        # Probe each currently available non-click control once per level, not per reset.
        if self.probe_actions and self._probe_level != self.level_at:
            self._probe_level = self.level_at
            self.probe_queue = deque(a for a in range(1, 6) if a in avail_vals)
        while self.probe_queue:
            a = self.probe_queue.popleft()
            if a in avail_vals:
                self.prev_action = a
                return GameAction["ACTION%d" % a]

        # follow an existing plan while it stays sane and actions remain available
        while self.plan:
            a = self.plan.popleft()
            if a not in avail_vals:
                self.plan.clear(); break
            if blob is not None and 1 <= a <= 4 and self.move_block[(blob, a)] >= 2:
                self.plan.clear(); break             # planned move is proven blocked
            self.prev_action = a
            return GameAction["ACTION%d" % a]

        # click games: productive-click memory + landmark cycling
        pure_click = 6 in avail_vals and not set(avail_vals) & {1, 2, 3, 4}
        stalled = self.effects.get(self.prev_action, {}).get("noop", 0) > 4 \
            if self.prev_action else False
        # budget law for clicks (v10): clicks that never produce anything are a proven
        # no-op — after 20 dry clicks in a movement game, stop clicking entirely
        # (found by the daily mock practice: the stalled-trigger click loop burned
        # 357/400 steps on a game whose clicks did nothing)
        self.click_n = getattr(self, "click_n", 0)
        _good_any = any(v > 0 for v in getattr(self, "click_gain", {}).values()) \
            if getattr(self, "click_gain", None) else False
        clicks_dead = (not pure_click) and self.click_n >= 20 and not _good_any
        if 6 in avail_vals and not clicks_dead \
                and (pure_click or stalled or self.rng.random() < 0.15):
            self.click_n += 1
            if getattr(self, "click_gain", None) is None:
                self.click_gain = defaultdict(int)
            if not hasattr(self, "sweep"):
                self.sweep = deque((x, y) for y in range(4, 64, 8)
                                   for x in range(4, 64, 8))
            good = [k for k, v in self.click_gain.items() if v > 0]
            if self.click_chain:                         # phase 0: ride the chain
                x, y = self.click_chain.popleft()
            elif self.sweep and (not good or self.rng.random() < 0.6):
                x, y = self.sweep.popleft()              # phase 1: coarse sweep
            elif good:
                bx, by = self.rng.choice(good)             # phase 2: focus near hits
                x = bx + self.rng.choice((-4, -2, 0, 2, 4))
                y = by + self.rng.choice((-4, -2, 0, 2, 4))
            else:
                lms = sorted(self._landmarks(g), key=lambda t: t[3])
                if lms and self.rng.random() < 0.6:
                    v, yy, xx, n = self.rng.choice(lms[:12])
                    x, y = xx, yy
                else:
                    x, y = self.rng.randint(2, 61), self.rng.randint(2, 61)
            act = GameAction.ACTION6
            act.set_data({"x": int(max(0, min(63, x))), "y": int(max(0, min(63, y)))})
            self.prev_action = 6
            self._last_click = (int(x), int(y))
            return act

        # movement games: a PERSISTENT GOAL machine — commit to one landmark,
        # walk to it, bump it (collect/enter/insert are all bumps), exhaust, next.
        if blob is not None and self.quantum:
            move_ok = [a for a in (1, 2, 3, 4) if a in avail_vals
                       and self.move_block[(blob, a)] < 2] \
                or [a for a in (1, 2, 3, 4) if a in avail_vals] or [1, 2, 3, 4]
            lms = self._landmarks(g)
            if not hasattr(self, "goal"): self.goal = None
            # re-locate / validate the current goal
            if self.goal is not None:
                v0, gy, gx = self.goal
                same = [t for t in lms if t[0] == v0]
                if same:
                    same.sort(key=lambda t: abs(t[1] - gy) + abs(t[2] - gx))
                    v0, gy, gx = same[0][0], same[0][1], same[0][2]
                    self.goal = (v0, gy, gx)
                else:
                    self.goal = None
            if self.goal is None:
                fresh = [t for t in lms
                         if self.landmark_seen[(t[0], t[1] // 5, t[2] // 5)] < 4]
                if not fresh and lms:
                    # round over: everything visited once. Start a NEW ROUND —
                    # a different visit order lets two-step effects emerge
                    # (enter the keyhole THEN push the box: the T-K-B anchor)
                    self.landmark_seen.clear()
                    self.move_block = defaultdict(int)
                    fresh = lms[:]
                    self.rng.shuffle(fresh)
                if fresh:
                    def myst_bonus(t):
                        return -2 if any(abs(t[1] - my) + abs(t[2] - mx) < 12
                                         for my, mx in self.mysteries) else 0
                    fresh.sort(key=lambda t: (
                        self.landmark_seen[(t[0], t[1] // 5, t[2] // 5)] + myst_bonus(t),
                        abs(t[1] - blob[0]) + abs(t[2] - blob[1])))
                    v0, gy, gx = fresh[0][0], fresh[0][1], fresh[0][2]
                    self.goal = (v0, gy, gx)
                    self.bumps = 0
            if self.goal is not None:
                v0, gy, gx = self.goal
                gkey = (v0, gy // 5, gx // 5)
                dist = abs(gy - blob[0]) + abs(gx - blob[1])
                if dist <= 2 * self.quantum:
                    if getattr(self, "bumps", 0) >= 4:
                        self.landmark_seen[gkey] = 99   # exhausted
                        self.goal = None
                    else:
                        dy, dx = gy - blob[0], gx - blob[1]
                        a = (1 if dy < 0 else 2) if abs(dy) >= abs(dx) \
                            else (3 if dx < 0 else 4)
                        if a in move_ok:
                            self.bumps = getattr(self, "bumps", 0) + 1
                            self.landmark_seen[gkey] += 1
                            self.prev_action = a
                            return GameAction["ACTION%d" % a]
                        self.landmark_seen[gkey] = 99
                        self.goal = None
                else:
                    a = self._bfs_step(g, blob, (gy, gx), self.quantum)
                    if a is not None and a in move_ok:
                        self.prev_action = a
                        return GameAction["ACTION%d" % a]
                    self.landmark_seen[gkey] += 2       # hard to reach; deprioritize
                    self.goal = None
        # novelty fallback: least-tried available action from this state
        nkey = ("pos", blob) if blob is not None else hsh
        cands = [a for a in avail_vals if 1 <= a <= 5 and (hsh, a) not in self.banned
                 and not (blob is not None and 1 <= a <= 4
                          and self.move_block[(blob, a)] >= 2)]
        if not cands:
            cands = [a for a in avail_vals if 1 <= a <= 5] or \
                    ([6] if 6 in avail_vals else [1])
        if cands == [6]:
            act = GameAction.ACTION6
            act.set_data({"x": self.rng.randint(2, 61), "y": self.rng.randint(2, 61)})
            self.prev_action = 6
            return act
        cands.sort(key=lambda a: (self.tried[nkey][a], self.rng.random()))
        a = cands[0]
        self.tried[nkey][a] += 1
        self.prev_action = a
        return GameAction["ACTION%d" % a]
