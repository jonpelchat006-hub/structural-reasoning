"""Mika's ARC-AGI-3 body, v2: the graph explorer plus a verified movement model.

v1 tried every action in every state. v2 learns, from her own presses, what the movement actions do
to the thing she controls (it shifts by a fixed step; some colours let it through, some stop it,
some it pushes, some end the life). Where that model has never been wrong in this level, she does
not spend presses checking it: she plans through the predicted states and spends presses only
where the model cannot say what will happen (an unknown colour, a push, a click, a new action).
A prediction that turns out wrong is recorded, counted against the model, and the true outcome
is kept. This is the same rule as the static slot filler: act on a rule only while it reproduces
everything seen, otherwise abstain and look."""
from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict, deque

import numpy as np

from mika3.explorer import components, size_bucket  # noqa: F401  (perception shared with v1)

try:
    from agents.agent import Agent
    from arcengine import GameAction, GameState
except Exception:  # pragma: no cover
    from arcshim import Agent, GameAction, GameState  # type: ignore

RESET = 0
CLICK = 6
PAD = 16
DCANDS = [(dy, dx) for dy in range(-12, 13) for dx in range(-12, 13) if (dy, dx) != (0, 0)]


# ---------------------------------------------------------------- the movement model
class Mover:
    def __init__(self):
        self.votes = defaultdict(Counter)    # action -> Counter of displacements seen
        self.d = {}                          # action -> confirmed displacement
        self.patch = None                    # sprite pixels (h, w) when first seen
        self.looks = {}                      # action -> how the sprite looks after moving with it (facing)
        self.shape_votes = Counter()         # sprite box sizes seen on clean moves
        self.turns = {}                      # action -> True if a blocked press still turns the sprite
        self.box = None                      # (y, x) of the sprite's top-left in the current frame
        self.passable = set(); self.blocking = set(); self.pushable = set(); self.deadly = set()
        self.floor = Counter()
        self.ok = Counter(); self.bad = Counter()   # prediction checks per action

    # -- displacement of whatever moved between f0 and f1
    @staticmethod
    def shift_of(f0, f1, D, prefer=None):
        """The displacement d of the thing that moved: its new pixels S (changed, not the colour left
        behind) must equal the old frame shifted by d, and the pixels it vacated V, carried by d, must
        land on it again. Returns (d, (ys, xs)) or (None, None); ties go to the shortest d."""
        ys, xs = np.nonzero(D)
        n = len(ys)
        if n < 2 or n > 1600:
            return None, None
        v1 = f1[ys, xs]
        vals, cnts = np.unique(v1, return_counts=True)
        F = vals[np.argmax(cnts)]
        sm = v1 != F
        if sm.sum() == 0 or sm.sum() == n:
            sm = np.ones(n, bool); vm = np.zeros(n, bool)
        else:
            vm = ~sm
        sy, sx, sv = ys[sm], xs[sm], v1[sm]
        vy, vx = ys[vm], xs[vm]
        F0 = np.pad(f0, PAD, constant_values=-1)
        F1 = np.pad(f1, PAD, constant_values=F)
        tot = len(sy) + len(vy)
        def frac(d):
            dy, dx = d
            a = int((F0[sy - dy + PAD, sx - dx + PAD] == sv).sum())
            b = int((F1[vy + dy + PAD, vx + dx + PAD] != F).sum()) if len(vy) else 0
            return (a + b) / tot
        if prefer is not None and frac(prefer) >= 0.8:
            return prefer, (ys, xs)
        best, bf = None, 0.0
        for d in DCANDS:
            fr = frac(d)
            if fr > bf + 1e-9 or (abs(fr - bf) <= 1e-9 and best is not None and abs(d[0]) + abs(d[1]) < abs(best[0]) + abs(best[1])):
                best, bf = d, fr
        if best is None or bf < 0.8:
            return None, None
        return best, (ys, xs)

    def find_patch(self, f):
        """Locate the sprite in a frame: any of its known looks, exact on its non-floor pixels, one hit."""
        if self.patch is None:
            return None
        h, w = self.patch.shape
        if f.shape[0] < h or f.shape[1] < w:
            return None
        from numpy.lib.stride_tricks import sliding_window_view
        win = sliding_window_view(f, (h, w))
        fl = self.floor.most_common(1)[0][0] if self.floor else None
        seen = set()
        for pt in [self.patch] + list(self.looks.values()):
            k = pt.tobytes()
            if k in seen or pt.shape != (h, w):
                continue
            seen.add(k)
            care = pt != fl if fl is not None else np.ones_like(pt, bool)
            if care.sum() == 0:
                continue
            eq = (win == pt) | ~care
            hits = np.argwhere(eq.all(axis=(2, 3)))
            if len(hits) == 1:
                return int(hits[0][0]), int(hits[0][1])
        return None

    def observe(self, f0, f1, a, D, died=False):
        """Learn from one real transition under simple action a."""
        if a in (RESET, CLICK, 7):
            return
        moved = False
        if D.any():
            d, pts = self.shift_of(f0, f1, D, prefer=self.d.get(a))
            if d is not None:
                self.votes[a][d] += 1
                top, cnt = self.votes[a].most_common(1)[0]
                if cnt >= 2 and cnt >= 0.8 * sum(self.votes[a].values()):
                    self.d[a] = top
                if self.d.get(a) == d:
                    moved = True
                    ys, xs = pts
                    # the sprite's box from this move: D's box without the trailing strip
                    y0, x0, y1, x1 = int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1
                    dy, dx = d
                    cb = (y0 + max(dy, 0), x0 + max(dx, 0))
                    cs = ((y1 - y0) - abs(dy), (x1 - x0) - abs(dx))
                    if 1 <= cs[0] <= 16 and 1 <= cs[1] <= 16:
                        self.shape_votes[cs] += 1
                    shape = self.shape_votes.most_common(1)[0][0] if self.shape_votes else None
                    if shape is not None and (self.patch is None or self.patch.shape != shape) and cs == shape:
                        self.patch = f1[cb[0]:cb[0] + cs[0], cb[1]:cb[1] + cs[1]].copy()
                        self.looks = {}
                    if self.patch is not None:
                        h, w = self.patch.shape
                        if cs == (h, w):
                            self.box = cb                       # a clean move re-anchors the box
                            for yy, xx in zip(ys, xs):          # what showed up where it left: floor
                                if not (cb[0] <= yy < cb[0] + h and cb[1] <= xx < cb[1] + w):
                                    self.floor[int(f1[yy, xx])] += 1
                        elif self.box is not None:
                            self.box = (self.box[0] + dy, self.box[1] + dx)
                        if self.box is not None and not (0 <= self.box[0] <= f1.shape[0] - h and 0 <= self.box[1] <= f1.shape[1] - w):
                            self.box = None
                        if self.box is not None and cs == (h, w):
                            by, bx = self.box
                            self.looks[a] = f1[by:by + h, bx:bx + w].copy()
        # colours: what was in the way
        if a in self.d and self.patch is not None:
            R = self._ahead(f0, a, self._prev_box)
            if R is not None:
                cols = set(np.unique(R).tolist())
                if died:
                    self.deadly |= cols - self.passable
                elif moved:
                    # did something get shoved along?
                    if self.box is not None and self._pushed(f0, f1, a):
                        self.pushable |= cols - self.passable - set(np.unique(self.patch).tolist())
                    else:
                        self.passable |= cols
                        self.blocking -= cols
                elif not D.any() or self._inside_box(D):
                    self.blocking |= cols - self.passable
                    if self._prev_box is not None:
                        self.turns[a] = bool(D.any())
                        if D.any():
                            by, bx = self._prev_box; h, w = self.patch.shape
                            self.looks[a] = f1[by:by + h, bx:bx + w].copy()

    _prev_box = None

    def before(self):
        self._prev_box = self.box

    def _ahead(self, f, a, box):
        if box is None or a not in self.d or self.patch is None:
            return None
        h, w = self.patch.shape
        y, x = box; dy, dx = self.d[a]
        ty, tx = y + dy, x + dx
        if not (0 <= ty <= f.shape[0] - h and 0 <= tx <= f.shape[1] - w):
            return np.array([], dtype=f.dtype)
        tgt = np.zeros(f.shape, bool); tgt[ty:ty + h, tx:tx + w] = True
        tgt[y:y + h, x:x + w] = False
        return f[tgt]

    def _inside_box(self, D):
        if self._prev_box is None or self.patch is None:
            return False
        h, w = self.patch.shape; y, x = self._prev_box
        m = np.zeros(D.shape, bool); m[y:y + h, x:x + w] = True
        return bool(D.any()) and not (D & ~m).any()

    def _pushed(self, f0, f1, a):
        """Pixels changed beyond the sprite's own old and new boxes = something else moved with it."""
        if self._prev_box is None:
            return False
        h, w = self.patch.shape
        D = f0 != f1
        m = np.zeros(f0.shape, bool)
        (y0, x0), (y1, x1) = self._prev_box, self.box
        m[y0:y0 + h, x0:x0 + w] = True; m[y1:y1 + h, x1:x1 + w] = True
        extra = D & ~m
        extra[:3, :] = False; extra[-3:, :] = False; extra[:, :3] = False; extra[:, -3:] = False
        return int(extra.sum()) >= 2

    STRICT = True

    def trusted(self, a):
        if a not in self.d:
            return False
        if self.STRICT:
            # verified: never wrong, and right often enough to have been tested
            return self.bad[a] == 0 and self.ok[a] >= 3
        return self.bad[a] <= max(1, self.ok[a] // 4)

    def predict(self, f, box, a, check=False):
        """(frame, box, kind) after action a, or None when the model cannot say.
        kind: 'move' | 'block' | 'death'. check=True predicts even before the model is trusted
        (to test it on presses made anyway)."""
        if box is None or self.patch is None or a not in self.d or not self.floor:
            return None
        if not check and not self.trusted(a):
            return None
        R = self._ahead(f, a, box)
        if R is None:
            return None
        h, w = self.patch.shape
        if R.size == 0:
            return self._blocked(f, box, a), box, "block"
        cols = set(np.unique(R).tolist())
        if cols & self.deadly:
            return None, None, "death"
        if cols <= self.passable:
            y, x = box; dy, dx = self.d[a]
            g = f.copy()
            g[y:y + h, x:x + w] = self.floor.most_common(1)[0][0]
            g[y + dy:y + dy + h, x + dx:x + dx + w] = self.looks.get(a, self.patch)
            return g, (y + dy, x + dx), "move"
        if (cols - self.passable) and (cols - self.passable) <= self.blocking:
            return self._blocked(f, box, a), box, "block"
        return None

    def _blocked(self, f, box, a):
        if not self.turns.get(a) or a not in self.looks:
            return f
        y, x = box; h, w = self.patch.shape
        g = f.copy(); g[y:y + h, x:x + w] = self.looks[a]
        return g


# ---------------------------------------------------------------- the mind
class Level:
    def __init__(self, idx):
        self.idx = idx
        self.nodes = {}            # key -> dict(frame, cands, tried:set, box)
        self.edges = {}            # (key, aid) -> next key | "DEATH"
        self.start = None
        self.deaths = defaultdict(int)
        self.death_steps = []
        self.budget = None
        self.moves_done = False


class Mind:
    NOVELTY = 1.0
    KIND_DECAY = 0
    CLICK_LATE = False
    REPLAY = False

    def __init__(self, seed=0, predict=True, lessons=True):
        self.rng = random.Random(seed)
        self.jit = [self.rng.random() * 0.01 for _ in range(997)]   # seeded tie-breaking
        self.use_model = predict
        self.use_lessons = lessons
        self.level = None
        self.levels_done = 0
        self.prev_key = None; self.prev_act = None; self.prev_frame = None; self._last_kind = None
        self.steps_since_reset = 0
        self.path = []             # [(expected key, step)]
        self.T = 0
        for nm in ("rowhit", "colhit", "rowpix", "colpix", "rowany", "colany"):
            setattr(self, nm, np.zeros(64))
        self.mask_rows = (); self.mask_cols = ()
        self.kind = defaultdict(lambda: [0, 0])
        self.act_stats = defaultdict(lambda: [0, 0])
        self.mover = Mover()
        self.vcache = {}           # virtual (predicted) node key -> (frame, box)
        self.stats = Counter()
        # hindsight: what the won levels teach the next ones
        self.lesson_kinds = Counter()      # click kinds on the shortest winning path
        self.lesson_moves = Counter()
        self.goal_colours = set()          # colours entered on the winning press
        self.wins = []                     # per won level: spent vs shortest known path
        self.last_route = []               # the last won level's shortest route, as candidates
        self.replay = []                   # route being tried on the new level
        self.level_actions = 0

    # ---- ticker mask (as v1)
    def key(self, f):
        g = f.copy()
        if self.mask_rows: g[list(self.mask_rows), :] = 255
        if self.mask_cols: g[:, list(self.mask_cols)] = 255
        return hashlib.blake2b(g.tobytes() + bytes(f.shape), digest_size=12).hexdigest()

    def dmask(self, f0, f1):
        D = f0 != f1
        if self.mask_rows: D[list(self.mask_rows), :] = False
        if self.mask_cols: D[:, list(self.mask_cols)] = False
        return D

    def update_mask(self, f0, f1):
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
        rows = tuple(sorted(set(lines(self.rowhit, self.rowany, self.rowpix)) | set(self.mask_rows)))
        cols = tuple(sorted(set(lines(self.colhit, self.colany, self.colpix)) | set(self.mask_cols)))
        if rows != self.mask_rows or cols != self.mask_cols:
            self.mask_rows, self.mask_cols = rows, cols
            return True
        return False

    def rekey(self):
        L = self.level
        self.vcache = {}
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
        L.deaths = defaultdict(int, {(remap.get(k, k), a): v for (k, a), v in L.deaths.items()})
        if L.start is not None:
            L.start = remap.get(L.start, L.start)
        self.prev_key = remap.get(self.prev_key, self.prev_key)
        self.path = []

    # ---- candidates and their worth
    def candidates(self, f, avail):
        simple = [a for a in avail if a not in (RESET, CLICK)]
        cands = [(a, None, None) for a in simple]
        if CLICK in avail:
            comps = components(f)
            if comps:
                big = max(comps, key=lambda t: t[1])
                for c, n, (y, x), bb in comps:
                    bg = (c == big[0] and n == big[1] and n > 0.3 * f.size)
                    cands.append((CLICK, (x, y), ("bg", c) if bg else (c, size_bucket(n))))
        return cands

    @staticmethod
    def aid(cand):
        a, xy, _ = cand
        return a if xy is None else (a, xy)

    def worth(self, cand):
        a, xy, kind = cand
        if a != CLICK:
            t, ch = self.act_stats[a]
            s = 3.0 if t == 0 else (2.0 + ch / t)
            if a == 7:
                s -= 1.5
            return s
        late = self.CLICK_LATE and self.level is not None and not self.level.moves_done and \
            any(a not in (7,) for a in getattr(self, "level_simple", []))
        w = self._click_worth(kind)
        return w * 0.05 if late else w

    def _click_worth(self, kind):
        t, ch = self.kind[kind]
        if kind and kind[0] == "bg":
            return 0.2 if t < 2 else 0.05
        # diminishing returns: a kind of object that changes something every time it is clicked would
        # otherwise be clicked forever (each click makes a new state with the same kind untried in it)
        g = 1.0 / (1.0 + t / self.KIND_DECAY) if self.KIND_DECAY else 1.0
        if self.lesson_kinds.get(kind) and (t < 3 or ch > 0):
            return (3.5 + 0.1 * min(5, self.lesson_kinds[kind])) * (g if t > 3 * self.lesson_kinds[kind] else 1.0)
        if t == 0:
            return 2.5 - 0.1 * kind[1]
        if ch == 0:
            return 0.3 / t
        return (1.5 + ch / t) * g

    def node(self, key, f, avail, box=None):
        L = self.level
        n = L.nodes.get(key)
        if n is None:
            n = dict(frame=f, cands=self.candidates(f, avail), tried=set(), box=box, avail=tuple(avail))
            L.nodes[key] = n
        elif box is not None:
            n["box"] = box
        return n

    def frontier(self, key, n):
        """Best (score, index) among this node's untried actions whose outcome the model cannot predict."""
        L = self.level
        best = (-1.0, None)
        for i, c in enumerate(n["cands"]):
            if i in n["tried"]:
                continue
            a = c[0]
            if self.use_model and a != CLICK and n.get("box") is not None:
                p = self.mover.predict(n["frame"], n["box"], a)
                if p is not None:
                    continue          # the model knows; no need to look
            s = self.worth(c) - (5 if L.deaths.get((key, self.aid(c))) else 0) + self.jit[i % 997]
            if s > best[0]:
                best = (s, i)
        return best

    # ---- hindsight (Jonathan, Oct 21): once a level is won, look back over its map
    def hindsight(self, L, k_last, a_last, f_last):
        if k_last is None or a_last is None or L.start is None:
            return
        adj = defaultdict(list)
        for (k, aid), nk in L.edges.items():
            if nk != "DEATH" and nk != k:
                adj[k].append((aid, nk))
        prev = {L.start: None}; q = deque([L.start])
        while q:
            k = q.popleft()
            if k == k_last:
                break
            for aid, nk in adj[k]:
                if nk not in prev:
                    prev[nk] = (k, aid); q.append(nk)
        if k_last not in prev:
            return
        steps = []
        k = k_last
        while prev[k] is not None:
            pk, aid = prev[k]; steps.append((pk, aid)); k = pk
        steps = steps[::-1] + [(k_last, a_last)]
        route = []
        for k, aid in steps:
            n = L.nodes.get(k)
            if n is None:
                continue
            for c in n["cands"]:
                if self.aid(c) == aid:
                    route.append(c)
                    if c[0] == CLICK:
                        self.lesson_kinds[c[2]] += 1
                    else:
                        self.lesson_moves[c[0]] += 1
                    break
        self.last_route = route
        n = L.nodes.get(k_last)
        if n is not None and not isinstance(a_last, tuple) and n.get("box") is not None and f_last is not None:
            R = self.mover._ahead(f_last, a_last, n["box"])
            if R is not None and R.size:
                fl = self.mover.floor.most_common(1)[0][0] if self.mover.floor else None
                self.goal_colours |= set(np.unique(R).tolist()) - {fl}
        self.wins.append(dict(level=L.idx, spent=self.level_actions, shortest=len(steps),
                              kinds=dict(self.lesson_kinds), goal=sorted(self.goal_colours),
                              route=[(c[0], None if c[1] is None else list(c[1]), None if c[2] is None else str(c[2])) for c in route]))

    def goal_bonus(self, frame, box):
        if not self.goal_colours or box is None or self.mover.patch is None:
            return 0.0
        h, w = self.mover.patch.shape; y, x = box
        m = max([abs(d[0]) + abs(d[1]) for d in self.mover.d.values()] or [1])
        reg = frame[max(0, y - m):y + h + m, max(0, x - m):x + w + m]
        return 2.0 if np.isin(reg, list(self.goal_colours)).any() else 0.0

    # ---- planning over real and predicted edges
    def successors(self, k):
        """Yield (step, next key) from node k: real edges, and predicted ones for untried moves."""
        L = self.level
        n = L.nodes.get(k)
        if n is not None:
            frame, box, cands, tried = n["frame"], n.get("box"), n["cands"], n["tried"]
        else:
            v = self.vcache.get(k)
            if v is None:
                return
            frame, box = v
            cands = [(a, None, None) for a in self.level_simple]
            tried = set()
        for i, c in enumerate(cands):
            real = L.edges.get((k, self.aid(c))) if n is not None else None
            if real is not None:
                if real != "DEATH" and real != k:
                    yield i, real
                continue
            if not self.use_model or c[0] == CLICK or box is None:
                continue
            p = self.mover.predict(frame, box, c[0])
            if p is None or p[2] != "move":
                continue
            g, nb, _ = p
            nk = self.key(g)
            if nk == k:
                continue
            if nk not in L.nodes and nk not in self.vcache:
                if len(self.vcache) > 20000:
                    self.vcache.clear()
                self.vcache[nk] = (g, nb)
            yield i, nk

    def bfs(self, src, want, limit=6000):
        L = self.level
        q = deque([src]); prev = {src: None}
        seen = 0
        while q and seen < limit:
            k = q.popleft(); seen += 1
            if k != src and want(k):
                path = []
                while prev[k] is not None:
                    pk, step = prev[k]
                    path.append((pk, step)); k = pk
                return path[::-1]
            for i, nk in self.successors(k):
                if nk not in prev:
                    prev[nk] = (k, i); q.append(nk)
            if k == src and L.start is not None and L.start not in prev and L.start != src:
                prev[L.start] = (k, "RESET"); q.append(L.start)
        return None

    def want_score(self, k):
        L = self.level
        n = L.nodes.get(k)
        if n is not None:
            sc = self.frontier(k, n)[0]
            return sc + (self.goal_bonus(n["frame"], n.get("box")) if sc > 0 else 0.0)
        v = self.vcache.get(k)
        if v is None:
            return -1
        # a predicted state never visited: being there is news (the model predicts frames, not what the
        # game makes of them: a win, a trap, a switch), and so are its unpredictable actions
        frame, box = v
        best = self.NOVELTY
        for a in self.level_simple:
            if self.mover.predict(frame, box, a) is None:
                best = max(best, self.worth((a, None, None)))
        if self.level_click:
            best = max(best, 1.0)
        return best + self.goal_bonus(frame, box)

    # ---- the step
    def act(self, latest):
        st = latest.state
        avail = list(latest.available_actions or [])
        if st == GameState.NOT_PLAYED or not latest.frame:
            return self._reset()
        f = np.array(latest.frame[-1], dtype=np.int16)
        if latest.levels_completed != self.levels_done or self.level is None:
            if self.level is not None and latest.levels_completed > self.levels_done and self.use_lessons:
                try:
                    self.hindsight(self.level, self.prev_key, self.prev_act, self.prev_frame)
                except Exception:
                    pass
            self.level_actions = 0
            if self.REPLAY and self.use_lessons and latest.levels_completed > self.levels_done and self.last_route:
                self.replay = list(self.last_route)
            else:
                self.replay = []
            self.levels_done = latest.levels_completed
            self.level = Level(self.levels_done)
            self.vcache = {}
            self.prev_key = None; self.prev_act = None; self.path = []; self.prev_frame = None
            self.steps_since_reset = 0
            self.mover.box = self.mover.find_patch(f)
        L = self.level
        self.level_simple = [a for a in avail if a not in (RESET, CLICK)]
        self.level_click = CLICK in avail
        if self.prev_frame is not None and self.update_mask(self.prev_frame, f):
            self.rekey()
        key = self.key(f)
        died = st == GameState.GAME_OVER
        # learn from the transition that brought us here
        if self.prev_key is not None and self.prev_act is not None and self.prev_frame is not None:
            pa = self.prev_act
            D = self.dmask(self.prev_frame, f) if self.prev_frame.shape == f.shape else np.ones((1, 1), bool)
            if not isinstance(pa, tuple):
                pred = self._pending_pred
                self.mover.observe(self.prev_frame, f, pa, D if D.shape == f.shape else np.zeros_like(f, bool), died)
                if pred is not None:
                    if pred == key or (pred == "DEATH" and died):
                        self.mover.ok[pa] += 1; self.stats["pred_ok"] += 1
                    else:
                        self.mover.bad[pa] += 1; self.stats["pred_bad"] += 1
            changed = self.prev_key != key
            self._credit(pa, changed)
            L.edges[(self.prev_key, pa)] = "DEATH" if died else key
            if died:
                L.deaths[(self.prev_key, pa)] += 1
                L.death_steps.append(self.steps_since_reset)
                self._update_budget()
        if self.mover.box is None and self.mover.patch is not None and not died:
            self.mover.box = self.mover.find_patch(f)
        if died:
            self.replay = []
            return self._reset()
        n = self.node(key, f, avail, box=self.mover.box)
        if L.start is None:
            L.start = key
        self.prev_frame = f
        # first presses of a new level: try the last level's winning route (cheap, and if the levels
        # share a layout it wins outright; whatever it shows goes into the map either way)
        choice = None
        while self.replay and choice is None:
            a, xy, kind = self.replay.pop(0)
            for j, c in enumerate(n["cands"]):
                if c[0] != a:
                    continue
                if a != CLICK:
                    choice = j; break
            if a == CLICK and choice is None:
                best = None
                for j, c in enumerate(n["cands"]):
                    if c[0] == CLICK and c[2] == kind:
                        dd = (c[1][0] - xy[0]) ** 2 + (c[1][1] - xy[1]) ** 2
                        if best is None or dd < best[0]:
                            best = (dd, j)
                if best is not None:
                    choice = best[1]
        if choice is not None:
            self.stats["replay"] += 1
            return self._emit(key, n, choice)
        # follow the plan while reality matches it
        if self.path:
            exp, step = self.path[0]
            if exp == key:
                self.path.pop(0)
                if step == "RESET":
                    return self._reset()
                if step < len(n["cands"]):
                    choice = step
            else:
                self.stats["replan"] += 1
                self.path = []
        if choice is None:
            s, i = self.frontier(key, n)
            if i is not None and s > 0.6:
                choice = i
            else:
                p = self._plan(key, s)
                if p:
                    exp, step = p[0]
                    self.path = p[1:]
                    if step == "RESET":
                        return self._reset()
                    choice = step
                elif i is not None:
                    choice = i
        if choice is None:
            # nothing left the model cannot predict and nothing reachable: try any untried action
            u = [j for j in range(len(n["cands"])) if j not in n["tried"]]
            if u:
                choice = max(u, key=lambda j: self.worth(n["cands"][j]))
            elif n["cands"]:
                # everything reachable is known: press a known action again (recorded), since a world
                # that does not repeat itself exactly can open new states this way
                self.stats["repress"] += 1
                ok = [j for j, c in enumerate(n["cands"]) if L.edges.get((key, self.aid(c))) != "DEATH"] or list(range(len(n["cands"])))
                choice = self.rng.choice(ok)
            else:
                return self._random(avail)
        return self._emit(key, n, choice)

    def _plan(self, key, here):
        L = self.level
        th = max(0.6, here)
        p = self.bfs(key, lambda k: self.want_score(k) > th)
        if p is None and self.CLICK_LATE and not L.moves_done:
            # nothing left to learn with the moves: now the clicks count
            L.moves_done = True
            self.stats["moves_done"] += 1
            here = self.frontier(key, L.nodes[key])[0] if key in L.nodes else here
            th = max(0.6, here)
            p = self.bfs(key, lambda k: self.want_score(k) > th)
        if p is None:
            p = self.bfs(key, lambda k: self.want_score(k) > here)
        if p and L.budget is not None and self.steps_since_reset + len(p) + 2 > L.budget \
                and all(s != "RESET" for _, s in p) and L.start is not None and key != L.start:
            p2 = self.bfs(L.start, lambda k: self.want_score(k) > th)
            if p2 is not None:
                return [(key, "RESET")] + p2
        return p

    def _update_budget(self):
        L = self.level
        ds = sorted(L.death_steps)
        for a, b in zip(ds, ds[1:]):
            if b - a <= 2 and a >= 5:
                L.budget = a
                break

    def _credit(self, aid, changed):
        if not isinstance(aid, tuple):
            s = self.act_stats[aid]; s[0] += 1; s[1] += int(changed)
        if self._last_kind is not None:
            k = self.kind[self._last_kind]; k[0] += 1; k[1] += int(changed)

    _pending_pred = None

    def _emit(self, key, n, i):
        self.stats["emit"] += 1
        self.level_actions += 1
        a, xy, kind = n["cands"][i]
        n["tried"].add(i)
        self.prev_key = key
        self.prev_act = self.aid(n["cands"][i])
        self._last_kind = kind if a == CLICK else None
        self._pending_pred = None
        if a not in (CLICK, 7) and n.get("box") is not None:
            p = self.mover.predict(n["frame"], n["box"], a, check=True)
            if p is not None:
                self._pending_pred = "DEATH" if p[2] == "death" else self.key(p[0])
        self.mover.before()
        self.steps_since_reset += 1
        act = GameAction.from_id(a)
        if a == CLICK:
            act.set_data({"x": int(xy[0]), "y": int(xy[1])})
        return act

    def _reset(self):
        self.stats["reset"] += 1
        self.level_actions += 1
        self.prev_key = None; self.prev_act = None; self._last_kind = None; self.prev_frame = None
        self._pending_pred = None
        self.steps_since_reset = 0
        self.path = []
        self.mover.box = None     # found again on the next frame
        return GameAction.RESET

    def _random(self, avail):
        self.stats["random"] += 1
        self.level_actions += 1
        acts = [a for a in avail if a != RESET] or [1]
        a = self.rng.choice(acts)
        self.prev_key = None; self.prev_act = None; self._last_kind = None; self._pending_pred = None
        self.steps_since_reset += 1
        act = GameAction.from_id(a)
        if a == CLICK:
            act.set_data({"x": self.rng.randrange(64), "y": self.rng.randrange(64)})
        return act


class Explorer2(Agent):
    MAX_ACTIONS = 3000
    PREDICT = True
    LESSONS = False
    SEED = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mind = Mind(seed=int(hashlib.md5(f"{self.game_id}:{self.SEED}".encode()).hexdigest()[:8], 16),
                         predict=self.PREDICT, lessons=self.LESSONS)
        self.mind.mover.STRICT = getattr(self, "STRICT", True)
        self.mind.KIND_DECAY = getattr(self, "KIND_DECAY", 0)
        self.mind.CLICK_LATE = getattr(self, "CLICK_LATE", False)
        self.mind.REPLAY = getattr(self, "REPLAY", False)

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame):
        try:
            return self.mind.act(latest_frame)
        except Exception:
            import traceback; traceback.print_exc()
            self.mind.level = None
            return GameAction.RESET


class Explorer2NoModel(Explorer2):
    PREDICT = False


class Explorer3(Explorer2):
    LESSONS = True


class Explorer3NoModel(Explorer2):
    PREDICT = False
    LESSONS = True


class Explorer4(Explorer2):
    PREDICT = False
    LESSONS = True
    KIND_DECAY = 15


class Explorer5(Explorer2):
    PREDICT = False
    LESSONS = True
    CLICK_LATE = True


class Explorer6(Explorer2):
    PREDICT = False
    LESSONS = True
    REPLAY = True


class Explorer4Model(Explorer2):
    LESSONS = True
    KIND_DECAY = 15


class Explorer3Loose(Explorer2):
    LESSONS = True
    STRICT = False
