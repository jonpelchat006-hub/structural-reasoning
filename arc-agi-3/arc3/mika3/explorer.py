"""Mika's ARC-AGI-3 body, v1: a graph explorer.

Each level is a graph of states (the frame with ticker lines masked) and actions. She tries what
she has never tried, walks the shortest known way to the nearest state that still has something
untried, keeps away from presses that ended a life, and plans inside the life budget once she has
seen it. Clicks are offered one per object (a same-colour connected region), most distinctive
first; what she learns about kinds of objects (which kinds ever change anything) carries from
state to state and from level to level.

Only the frames are used: no game-specific rules."""
from __future__ import annotations

import hashlib
import random
from collections import defaultdict, deque

import numpy as np

try:
    from scipy.ndimage import label as _label
except Exception:  # pragma: no cover
    _label = None

try:
    from agents.agent import Agent
    from arcengine import GameAction, GameState
except Exception:  # pragma: no cover
    from arcshim import Agent, GameAction, GameState  # type: ignore

RESET = 0
CLICK = 6


# ---------------------------------------------------------------- perception
def components(f: np.ndarray):
    """Same-colour 4-connected regions: list of (colour, size, (y, x) representative, bbox)."""
    out = []
    for c in np.unique(f):
        m = f == c
        if _label is not None:
            lab, n = _label(m)
            if n == 0:
                continue
            idx = np.arange(1, n + 1)
            ys, xs = np.nonzero(lab)
            ls = lab[ys, xs]
            order = np.argsort(ls, kind="stable")
            ys, xs, ls = ys[order], xs[order], ls[order]
            cuts = np.searchsorted(ls, idx)
            ends = np.append(cuts[1:], len(ls))
            for i in range(n):
                yy, xx = ys[cuts[i]:ends[i]], xs[cuts[i]:ends[i]]
                out.append(_comp(int(c), yy, xx))
        else:
            seen = np.zeros_like(m)
            for y0, x0 in zip(*np.nonzero(m)):
                if seen[y0, x0]:
                    continue
                q = [(y0, x0)]; seen[y0, x0] = True; pts = []
                while q:
                    y, x = q.pop(); pts.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < f.shape[0] and 0 <= xx < f.shape[1] and m[yy, xx] and not seen[yy, xx]:
                            seen[yy, xx] = True; q.append((yy, xx))
                yy = np.array([p[0] for p in pts]); xx = np.array([p[1] for p in pts])
                out.append(_comp(int(c), yy, xx))
    return out


def _comp(c, yy, xx):
    cy, cx = yy.mean(), xx.mean()
    k = int(np.argmin((yy - cy) ** 2 + (xx - cx) ** 2))
    return (c, int(len(yy)), (int(yy[k]), int(xx[k])), (int(yy.min()), int(xx.min()), int(yy.max()), int(xx.max())))


def size_bucket(n):
    return 0 if n <= 2 else 1 if n <= 9 else 2 if n <= 36 else 3 if n <= 144 else 4 if n <= 600 else 5


# ---------------------------------------------------------------- the mind
class Level:
    def __init__(self, idx):
        self.idx = idx
        self.nodes = {}            # key -> dict(frame, cands, tried:set, avail)
        self.edges = {}            # (key, act) -> next key | "DEATH"
        self.noop = set()          # (key, act) that changed nothing
        self.start = None
        self.deaths = defaultdict(int)
        self.death_steps = []      # steps since reset at each death
        self.budget = None


class Mind:
    def __init__(self, seed=0, max_clicks=48):
        self.rng = random.Random(seed)
        self.jit = [self.rng.random() * 0.01 for _ in range(997)]
        self.max_clicks = max_clicks
        self.level = None
        self.levels_done = 0
        self.prev_key = None
        self.prev_act = None
        self.prev_frame = None
        self.steps_since_reset = 0
        self.path = []
        # ticker-line detection
        self.T = 0
        self.rowhit = np.zeros(64); self.colhit = np.zeros(64)
        self.rowpix = np.zeros(64); self.colpix = np.zeros(64)
        self.rowany = np.zeros(64); self.colany = np.zeros(64)
        self.mask_rows = (); self.mask_cols = ()
        # kinds of objects: (colour, size bucket) -> [tries, changes]
        self.kind = defaultdict(lambda: [0, 0])
        self.act_stats = defaultdict(lambda: [0, 0])   # simple action -> [tries, changes]
        self.log = []

    # ---- keys
    def key(self, f):
        g = f.copy()
        if self.mask_rows: g[list(self.mask_rows), :] = 255
        if self.mask_cols: g[:, list(self.mask_cols)] = 255
        return hashlib.blake2b(g.tobytes() + bytes(f.shape), digest_size=12).hexdigest()

    def update_mask(self, f0, f1):
        """Ticker lines (life/step counters): a row or column whose changes are small (1-3 px on the line)
        and keep coming whatever is pressed. On a border line (within 2 px of the edge, where these games
        keep their bars) 10% of transitions is enough; inside the picture it takes 85%."""
        if f0 is None or f0.shape != f1.shape or f1.shape != (64, 64):
            return False
        d = f0 != f1
        self.T += 1
        r = d.sum(1); c = d.sum(0)
        self.rowhit += (r > 0) & (r <= 3); self.colhit += (c > 0) & (c <= 3)
        self.rowpix += r; self.colpix += c
        self.rowany += r > 0; self.colany += c > 0
        if self.T < 8:
            return False
        def lines(hit, anyh, pix):
            out = []
            for i in range(64):
                if anyh[i] == 0 or pix[i] / anyh[i] > 3.0:
                    continue
                edge = i <= 2 or i >= 61
                if hit[i] >= (0.10 if edge else 0.97) * self.T and hit[i] >= 3 and (edge or pix[i] / anyh[i] <= 1.5):
                    out.append(i)
            return tuple(out)
        rows = lines(self.rowhit, self.rowany, self.rowpix)
        cols = lines(self.colhit, self.colany, self.colpix)
        rows = tuple(sorted(set(rows) | set(self.mask_rows))); cols = tuple(sorted(set(cols) | set(self.mask_cols)))
        if rows != self.mask_rows or cols != self.mask_cols:
            self.mask_rows, self.mask_cols = rows, cols
            return True
        return False

    def rekey(self):
        """The mask changed: rebuild the level's graph under the new keys."""
        L = self.level
        if L is None:
            return
        remap = {k: self.key(n["frame"]) for k, n in L.nodes.items()}
        nodes = {}
        for k, n in L.nodes.items():
            nk = remap[k]
            if nk in nodes:
                nodes[nk]["tried"] |= n["tried"]
            else:
                nodes[nk] = n
        L.nodes = nodes
        L.edges = {(remap.get(k, k), a): (remap.get(v, v) if v != "DEATH" else v) for (k, a), v in L.edges.items()}
        L.noop = {(remap.get(k, k), a) for k, a in L.noop}
        L.deaths = defaultdict(int, {(remap.get(k, k), a): v for (k, a), v in L.deaths.items()})
        if L.start is not None:
            L.start = remap.get(L.start, L.start)
        self.prev_key = remap.get(self.prev_key, self.prev_key)
        self.path = []

    # ---- candidates
    def candidates(self, f, avail):
        simple = [a for a in avail if a not in (RESET, CLICK)]
        cands = [(a, None, None) for a in simple]
        if CLICK in avail:
            comps = components(f)
            if comps:
                big = max(comps, key=lambda t: t[1])
                total = f.size
                for c, n, (y, x), bb in comps:
                    kind = (c, size_bucket(n))
                    bg = (c == big[0] and n == big[1] and n > 0.3 * total)
                    cands.append((CLICK, (x, y), kind if not bg else ("bg", c)))
        return cands

    def score_cand(self, cand):
        a, xy, kind = cand
        if a != CLICK:
            t, ch = self.act_stats[a]
            s = 3.0 if t == 0 else (2.0 + ch / t)
            if a == 7:
                s -= 1.5   # undo: navigation, rarely news
            return s
        t, ch = self.kind[kind]
        if isinstance(kind, tuple) and kind and kind[0] == "bg":
            return 0.2 if t < 2 else 0.05
        if t == 0:
            return 2.5 - 0.1 * kind[1]
        if ch == 0:
            return 0.3 / t
        return 1.5 + ch / t

    def node(self, key, f, avail):
        L = self.level
        n = L.nodes.get(key)
        if n is None:
            cands = self.candidates(f, avail)
            n = dict(frame=f, cands=cands, tried=set(), avail=tuple(avail))
            L.nodes[key] = n
        return n

    def untried(self, key):
        n = self.level.nodes[key]
        return [i for i in range(len(n["cands"])) if i not in n["tried"]]

    def best_untried(self, key):
        n = self.level.nodes[key]
        u = self.untried(key)
        if not u:
            return None, -1
        L = self.level
        sc = [(self.score_cand(n["cands"][i]) - (5 if L.deaths.get((key, self._aid(n["cands"][i]))) else 0) + self.jit[i % 997], i) for i in u]
        s, i = max(sc)
        return i, s

    @staticmethod
    def _aid(cand):
        a, xy, _ = cand
        return a if xy is None else (a, xy)

    # ---- planning
    def bfs(self, src, want, budget_left=None):
        """Shortest known path (list of cand indices / RESET) from src to a node satisfying want."""
        L = self.level
        q = deque([src]); prev = {src: None}
        while q:
            k = q.popleft()
            if k != src and want(k):
                path = []
                while prev[k] is not None:
                    pk, step = prev[k]
                    path.append(step); k = pk
                return path[::-1]
            n = L.nodes.get(k)
            if n is None:
                continue
            for i, c in enumerate(n["cands"]):
                nk = L.edges.get((k, self._aid(c)))
                if nk is None or nk == "DEATH" or nk == k or nk in prev:
                    continue
                prev[nk] = (k, i); q.append(nk)
            if L.start is not None and L.start not in prev and k == src:
                prev[L.start] = (k, "RESET"); q.append(L.start)
        return None

    # ---- the step
    def act(self, latest):
        st = latest.state
        avail = list(latest.available_actions or [])
        if st in (GameState.NOT_PLAYED,) or not latest.frame:
            self._record_death_if_any(st)
            return self._reset()
        f = np.array(latest.frame[-1], dtype=np.int16)
        if latest.levels_completed != self.levels_done or self.level is None:
            self.levels_done = latest.levels_completed
            self.level = Level(self.levels_done)
            self.prev_key = None; self.prev_act = None; self.path = []
            self.steps_since_reset = 0
            self.prev_frame = None
        L = self.level
        if self.prev_frame is not None and self.update_mask(self.prev_frame, f):
            self.rekey()
        key = self.key(f)
        n = self.node(key, f, avail)
        if L.start is None:
            L.start = key
        # record the transition that brought us here
        if self.prev_key is not None and self.prev_act is not None:
            pa = self.prev_act
            L.edges[(self.prev_key, pa)] = key
            changed = self.prev_key != key
            if not changed:
                L.noop.add((self.prev_key, pa))
            self._learn(pa, changed)
        if st == GameState.GAME_OVER:
            if self.prev_key is not None and self.prev_act is not None:
                L.edges[(self.prev_key, self.prev_act)] = "DEATH"
                L.deaths[(self.prev_key, self.prev_act)] += 1
                L.death_steps.append(self.steps_since_reset)
                self._update_budget()
            return self._reset()
        self.prev_frame = f
        # follow a planned path if it is still valid
        choice = None
        if self.path:
            step = self.path.pop(0)
            if step == "RESET":
                return self._reset()
            if isinstance(step, int) and step < len(n["cands"]):
                choice = step
            else:
                self.path = []
        if choice is None:
            i, s = self.best_untried(key)
            if i is not None and s > 0.6:
                choice = i
            else:
                p = self._plan(key, s)
                if p:
                    self.path = p
                    step = self.path.pop(0)
                    if step == "RESET":
                        return self._reset()
                    choice = step
                elif i is not None:
                    choice = i
        if choice is None:
            if n["cands"]:
                ok = [j for j, c in enumerate(n["cands"]) if L.edges.get((key, self._aid(c))) != "DEATH"] or list(range(len(n["cands"])))
                choice = self.rng.choice(ok)
            else:
                return self._random(avail, f)
        return self._emit(key, n, choice)

    def _plan(self, key, here_score):
        L = self.level
        def want(k):
            i, s = self.best_untried(k)
            return i is not None and s > max(0.6, here_score)
        p = self.bfs(key, want)
        if p is None:
            def want2(k):
                i, s = self.best_untried(k)
                return i is not None and s > here_score
            p = self.bfs(key, want2)
        if p and L.budget is not None and self.steps_since_reset + len(p) + 2 > L.budget and "RESET" not in p:
            # out of life budget on the way: start the life over and go from the start
            if L.start is not None and key != L.start:
                p2 = self.bfs(L.start, want) if L.start in L.nodes else None
                if p2 is not None:
                    return ["RESET"] + p2
        return p

    def _update_budget(self):
        L = self.level
        ds = sorted(L.death_steps)
        if len(ds) >= 2:
            # deaths at (nearly) the same press count after a reset: that count is the life budget
            for a, b in zip(ds, ds[1:]):
                if b - a <= 2 and a >= 5:
                    L.budget = a
                    break

    def _learn(self, aid, changed):
        if isinstance(aid, tuple):
            # click: credit the kind of object clicked
            n = None
        else:
            s = self.act_stats[aid]; s[0] += 1; s[1] += int(changed)
        if self._last_kind is not None:
            k = self.kind[self._last_kind]; k[0] += 1; k[1] += int(changed)

    _last_kind = None

    def _emit(self, key, n, i):
        L = self.level
        a, xy, kind = n["cands"][i]
        n["tried"].add(i)
        self.prev_key = key
        self.prev_act = self._aid(n["cands"][i])
        self._last_kind = kind if a == CLICK else None
        self.steps_since_reset += 1
        act = GameAction.from_id(a)
        if a == CLICK:
            act.set_data({"x": int(xy[0]), "y": int(xy[1])})
        return act

    def _reset(self):
        self.prev_key = None; self.prev_act = None; self._last_kind = None
        self.prev_frame = None
        self.steps_since_reset = 0
        self.path = []
        return GameAction.RESET

    def _record_death_if_any(self, st):
        pass

    def _random(self, avail, f):
        acts = [a for a in avail if a != RESET] or [1]
        a = self.rng.choice(acts)
        self.prev_key = None; self.prev_act = None; self._last_kind = None
        self.steps_since_reset += 1
        act = GameAction.from_id(a)
        if a == CLICK:
            act.set_data({"x": self.rng.randrange(64), "y": self.rng.randrange(64)})
        return act


class Explorer(Agent):
    MAX_ACTIONS = 3000
    SEED = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mind = Mind(seed=int(hashlib.md5(f"{self.game_id}:{self.SEED}".encode()).hexdigest()[:8], 16))

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame):
        try:
            return self.mind.act(latest_frame)
        except Exception:
            import traceback; traceback.print_exc()
            self.mind.level = None
            return GameAction.RESET
