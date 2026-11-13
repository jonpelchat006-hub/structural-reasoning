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
        try:
            return self._predict(f, box, a, check)
        except Exception:
            return None

    def _predict(self, f, box, a, check=False):
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
        if not self.turns.get(a) or a not in self.looks or self.looks[a].shape != self.patch.shape:
            return f
        y, x = box; h, w = self.patch.shape
        if not (0 <= y <= f.shape[0] - h and 0 <= x <= f.shape[1] - w):
            return f
        g = f.copy(); g[y:y + h, x:x + w] = self.looks[a]
        return g


# ---------------------------------------------------------------- candidate features (for the look-back prior)
FEAT_NAMES = (["bias", "click"] + [f"A{i}" for i in (1, 2, 3, 4, 5, 7)] + ["mixed"] +
              [f"sz{i}" for i in range(6)] + ["bg", "colfrac", "log_kind_n", "colour_unique", "border",
               "centre_dist", "aspect", "log_ncomp", "fill"])


def cand_feats_simple(a, nsimple, has_click):
    v = [1.0, 0.0] + [1.0 if a == i else 0.0 for i in (1, 2, 3, 4, 5, 7)] + [1.0 if has_click else 0.0]
    return v + [0.0] * (len(FEAT_NAMES) - len(v))


def cand_feats_click(c, n, yx, bb, bg, colfrac, kinds, ncol, ncomp, nsimple):
    y0, x0, y1, x1 = bb
    h, w = y1 - y0 + 1, x1 - x0 + 1
    sb = size_bucket(n)
    v = [1.0, 1.0] + [0.0] * 6 + [1.0 if nsimple else 0.0]
    v += [1.0 if sb == i else 0.0 for i in range(6)]
    v += [1.0 if bg else 0.0, colfrac.get(int(c), 0.0), float(np.log1p(kinds.get((c, sb), 1))),
          1.0 if ncol.get(c, 0) == 1 else 0.0, 1.0 if (y0 == 0 or x0 == 0 or y1 == 63 or x1 == 63) else 0.0,
          float(np.hypot(yx[0] - 31.5, yx[1] - 31.5) / 45.0), float(min(h, w) / max(h, w)),
          float(np.log1p(ncomp)), float(n / max(1, h * w))]
    return v


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
    RARE = 0.0
    _last_rare = 0.0
    CLOCK = False
    DUMP = False
    PRIOR = None
    PRIOR_W = 0.5
    MOMENTUM = 0.0
    MOMENTUM_ADAPT = 0.0
    momentum_now = 0.0
    mean_run = None
    NOVELTY = 1.0
    KIND_DECAY = 0
    CLICK_LATE = False
    REPLAY = False
    # goal rungs (Jonathan, Oct 22: describe a victory generally first, then by the game's own events)
    TAKEOVER = 0.0     # general rung: "the game took control" - one press, a longer animation than usual
    WINEVENT = 0.0     # specific rung: "what the last win did" - the winning press's effect, in this game
    REL_GATE = 0.0     # if set, a relation counts only while it follows fewer than this share of presses here
    rel_seen = 0
    PICK = False       # control: choose among near frontier states (bfs_pick) without any rung bonus
    RELATION = 0.0     # general rung from the relational survey: "something small changed far away" (an
                       # indicator) or "a colour vanished" - the two that held on route presses across games
    GOALSEARCH = 0.0   # image plane, forward: look for the before-picture of earlier wins in the new screen
    goal_mask = None
    goal_near = None
    WINIMAGE = 0.0     # image plane: the press looks like an earlier win of this game, up to limited turns
    _marks = {}

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
        self.pixmask = None; self.clock = {}; self.life = 0
        self.pxcount = np.zeros((64, 64))
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
        self.route_data = []               # look-back training data: candidates at route states
        self.replay = []                   # route being tried on the new level
        self.level_actions = 0
        # goal rungs
        self.fr_counts = Counter(); self.fr_total = 0      # animation lengths seen in this game
        self.kk_tries = Counter()                          # presses per kind (click kind or action)
        self.took_kind = Counter()                         # ... that made the game take control
        self.ev_kind = Counter()                           # ... whose effect repeated the last win's
        self.rel_kind = Counter()                          # ... that changed an indicator / ended a colour
        self.img_kind = Counter()                          # ... whose picture matched an earlier win's
        self.win_moments = set()                           # pictures of this game's winning presses
        self.win_templates = []                            # before-pictures of the changed regions of each win
        self.goal_kind = Counter()                         # kinds of press that touched a goal place
        self.mom_count = Counter(); self.mom_n = 0         # how often each picture follows a press here
        self.win_event = None                              # dict(act, col, eff:set) of the last win
        self.eff_count = Counter(); self.eff_n = 0         # how often each effect follows a press here
        self.goal_log = Counter()

    # ---- ticker mask (as v1)
    def key(self, f):
        g = f.copy()
        if self.mask_rows: g[list(self.mask_rows), :] = 255
        if self.mask_cols: g[:, list(self.mask_cols)] = 255
        if self.pixmask is not None and g.shape == self.pixmask.shape: g[self.pixmask] = 255
        return hashlib.blake2b(g.tobytes() + bytes(f.shape), digest_size=12).hexdigest()

    def dmask(self, f0, f1):
        D = f0 != f1
        if self.mask_rows: D[list(self.mask_rows), :] = False
        if self.mask_cols: D[:, list(self.mask_cols)] = False
        if self.pixmask is not None and D.shape == self.pixmask.shape: D[self.pixmask] = False
        return D

    # ---- clock pixels: a pixel that changes at the same press count in every life, whatever was
    # pressed, and never at any other count, is a clock (a timer or budget bar), not the world
    def clock_observe(self, f0, f1, step, aid, life):
        if f0 is None or f0.shape != f1.shape or f1.shape != (64, 64):
            return
        d = f0 != f1
        n = int(d.sum())
        if n == 0 or n > 400:
            return
        for idx in np.flatnonzero(d).tolist():
            rec = self.clock.get(idx)
            if rec is None:
                self.clock[idx] = rec = {}
            rec.setdefault(step, set()).add((life, str(aid)))

    def clock_update(self):
        new = []
        for idx, rec in self.clock.items():
            if len(rec) != 1:
                continue
            (step, ev), = rec.items()
            lives = {l for l, _ in ev}
            acts = {a for _, a in ev}
            if len(lives) >= 3 and len(acts) >= 2:
                new.append(idx)
        if not new:
            return False
        m = np.zeros(64 * 64, bool) if self.pixmask is None else self.pixmask.ravel().copy()
        before = int(m.sum())
        m[new] = True
        if int(m.sum()) == before:
            return False
        self.pixmask = m.reshape(64, 64)
        self.stats["clock_px"] = int(m.sum())
        return True

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
    def candidates(self, f, avail, feats_out=None):
        simple = [a for a in avail if a not in (RESET, CLICK)]
        cands = [(a, None, None) for a in simple]
        feats = [cand_feats_simple(a, len(simple), CLICK in avail) for a in simple]
        if CLICK in avail:
            comps = components(f)
            if comps:
                big = max(comps, key=lambda t: t[1])
                colfrac = {int(c): float((f == c).mean()) for c in np.unique(f)}
                kinds = Counter((c, size_bucket(n)) for c, n, _, _ in comps)
                ncol = Counter(c for c, _, _, _ in comps)
                for c, n, (y, x), bb in comps:
                    bg = (c == big[0] and n == big[1] and n > 0.3 * f.size)
                    kind = ("bg", c) if bg else (c, size_bucket(n))
                    cands.append((CLICK, (x, y), kind))
                    feats.append(cand_feats_click(c, n, (y, x), bb, bg, colfrac, kinds, ncol, len(comps), len(simple)))
        if feats_out is not None:
            feats_out.extend(feats)
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
            feats = []
            cands = self.candidates(f, avail, feats)
            n = dict(frame=f, cands=cands, tried=set(), box=box, avail=tuple(avail), feats=feats)
            if self.PRIOR is not None and feats:
                X = np.array(feats); z = X @ self.PRIOR
                z = z - z.max(); p = np.exp(z); p /= p.sum()
                n["prior"] = (p * len(p)).tolist()       # 1.0 = average candidate here
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
            if self.PRIOR is not None and "prior" in n:
                s += self.PRIOR_W * float(np.log(max(1e-3, n["prior"][i])))
            if self.TAKEOVER or self.WINEVENT or self.RELATION or self.WINIMAGE or self.GOALSEARCH:
                s += self.goal_rung_bonus(c)
            if self.momentum_now and key == self.cur_key and self.run is not None:
                ra, rxy, rkind = self.run
                if a == ra and (a != CLICK or c[2] == rkind):
                    # the look-back across games: winning routes are runs of the same press;
                    # keep pressing what just changed something until it stops
                    s += self.momentum_now + (0.5 if a == CLICK and c[1] == rxy else 0.0)
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
        if self.DUMP:
            for k, aid in steps:
                n = L.nodes.get(k)
                if n is None or not n.get("feats"):
                    continue
                ch = [j for j, c in enumerate(n["cands"]) if self.aid(c) == aid]
                if ch:
                    self.route_data.append(dict(level=L.idx, chosen=ch[0], feats=[[round(x, 4) for x in v] for v in n["feats"]]))
        # a lesson about how to learn: if the won route was made of long runs of one press, the next
        # level is explored by runs (keep pressing what just changed something); otherwise not
        if self.MOMENTUM_ADAPT and route:
            runs = 1 + sum(1 for x, y in zip(route, route[1:]) if (x[0], x[2]) != (y[0], y[2]))
            self.mean_run = len(route) / runs
            self.momentum_now = self.MOMENTUM_ADAPT if self.mean_run >= 2.5 else 0.0
        n = L.nodes.get(k_last)
        if n is not None and not isinstance(a_last, tuple) and n.get("box") is not None and f_last is not None:
            R = self.mover._ahead(f_last, a_last, n["box"])
            if R is not None and R.size:
                fl = self.mover.floor.most_common(1)[0][0] if self.mover.floor else None
                self.goal_colours |= set(np.unique(R).tolist()) - {fl}
        self.wins.append(dict(level=L.idx, spent=self.level_actions, shortest=len(steps),
                              kinds=dict(self.lesson_kinds), goal=sorted(self.goal_colours),
                              route=[(c[0], None if c[1] is None else list(c[1]), None if c[2] is None else str(c[2])) for c in route],
                              mean_run=self.mean_run, momentum_next=self.momentum_now))

    def goal_bonus(self, frame, box):
        if not self.goal_colours or box is None or self.mover.patch is None:
            return 0.0
        h, w = self.mover.patch.shape; y, x = box
        m = max([abs(d[0]) + abs(d[1]) for d in self.mover.d.values()] or [1])
        reg = frame[max(0, y - m):y + h + m, max(0, x - m):x + w + m]
        return 2.0 if np.isin(reg, list(self.goal_colours)).any() else 0.0

    # ---- goal rungs: a ladder of descriptions of "getting somewhere", general to specific
    @staticmethod
    def _kkey(cand):
        a, xy, kind = cand
        return ("c", kind) if a == CLICK else ("a", a)

    def _fr_median(self):
        half = self.fr_total / 2.0; acc = 0
        for n in sorted(self.fr_counts):
            acc += self.fr_counts[n]
            if acc >= half:
                return n
        return 1

    @staticmethod
    def effects(f0, f1, D):
        """What a press did, in kinds of things: the set of (kind, colours before, colours after) of each
        changed region, without sizes or places; regions that only moved are left out (moving is what
        presses usually do)."""
        if D is None or D.shape != f0.shape or not D.any() or D.sum() > 1500:
            return set()
        try:
            from scipy.ndimage import label as _lab
        except Exception:
            return set()
        D = D.copy(); D[:2, :] = False; D[-2:, :] = False; D[:, :2] = False; D[:, -2:] = False
        lab, n = _lab(D, structure=np.ones((3, 3), int))
        out = set()
        for i in range(1, min(n, 40) + 1):
            m = lab == i
            b = tuple(sorted(set(f0[m].tolist()))); a = tuple(sorted(set(f1[m].tolist())))
            if set(b) == set(a):
                continue
            out.add(("recoloured" if len(b) == 1 and len(a) == 1 else "changed", b, a))
        return out

    @staticmethod
    def moment_key(f0, f1):
        """The image plane: the main change of one press as a picture in standard form, using only limited
        turns - only the changed pixels (before and after), colours renumbered in order of appearance, the
        smallest of the 8 flips/rotations, cut out of its place on the screen. None if nothing changed."""
        try:
            from scipy.ndimage import label as _lab
        except Exception:
            return None
        g0 = np.asarray(f0, dtype=np.int16)[2:-2, 2:-2]; g1 = np.asarray(f1, dtype=np.int16)[2:-2, 2:-2]
        if g0.shape != g1.shape:
            return None
        D = g0 != g1
        if not D.any():
            return None
        lab, n = _lab(D, structure=np.ones((3, 3), int))
        sizes = np.bincount(lab.ravel())[1:]
        M = lab == int(sizes.argmax()) + 1
        ys, xs = np.nonzero(M)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        if y1 - y0 > 24 or x1 - x0 > 24:
            return f"big{(y1 - y0) // 8},{(x1 - x0) // 8}"
        m = M[y0:y1, x0:x1]
        B = np.where(m, g0[y0:y1, x0:x1], -1); A = np.where(m, g1[y0:y1, x0:x1], -1)
        best = None
        for k in range(8):
            b = np.rot90(B, k % 4); a = np.rot90(A, k % 4)
            if k >= 4:
                b = np.fliplr(b); a = np.fliplr(a)
            flat = np.concatenate([b.ravel(), a.ravel()])
            vals = flat[flat >= 0]
            lut = np.full(257, -1, dtype=np.int16)
            u, idx = np.unique(vals, return_index=True)
            lut[u[np.argsort(idx)].astype(int) + 1] = np.arange(len(u), dtype=np.int16)
            sig = lut[b.astype(int) + 1].tobytes() + lut[a.astype(int) + 1].tobytes() + bytes(str(b.shape), "ascii")
            if best is None or sig < best:
                best = sig
        return hashlib.blake2b(best, digest_size=10).hexdigest()

    @staticmethod
    def before_templates(f0, f1):
        """the changed regions of a winning press, cut from the frame before it (changed pixels only)"""
        from scipy.ndimage import label as _lab
        D = np.zeros(f0.shape, bool)
        D[2:-2, 2:-2] = (f0 != f1)[2:-2, 2:-2]
        lab, n = _lab(D, structure=np.ones((3, 3), int))
        out = []
        for i in range(1, min(n, 20) + 1):
            m = lab == i
            ys, xs = np.nonzero(m)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            if m.sum() < 2 or y1 - y0 > 24 or x1 - x0 > 24:
                continue
            out.append(np.where(m[y0:y1, x0:x1], f0[y0:y1, x0:x1], -1).astype(np.int16))
        return out

    def find_goal(self, f):
        """Where in this screen does the before-picture of an earlier win fit (its own colours, any of the 8
        flips/rotations)? Those places are where the win may happen again. A template that fits almost
        everywhere says nothing and is dropped."""
        from numpy.lib.stride_tricks import sliding_window_view
        S = np.asarray(f, dtype=np.int16)
        G = np.zeros(S.shape, bool)
        for temps in self.win_templates:
            for T in temps:
                places = []
                for k in range(8):
                    Tt = np.rot90(T, k % 4)
                    if k >= 4:
                        Tt = np.fliplr(Tt)
                    h, w = Tt.shape
                    if h > S.shape[0] or w > S.shape[1]:
                        continue
                    V = sliding_window_view(S, (h, w))
                    ok = np.ones(V.shape[:2], bool)
                    for c in np.unique(Tt):
                        if c < 0:
                            continue
                        ys, xs = np.nonzero(Tt == c)
                        ok &= (V[:, :, ys, xs] == c).all(axis=2)
                    for y, x in zip(*np.nonzero(ok)):
                        places.append((y, x, Tt))
                if not places or len(places) > 100:      # fits in over ~3% of all places: says nothing
                    continue
                for y, x, Tt in places:
                    h, w = Tt.shape
                    G[y:y + h, x:x + w] |= Tt >= 0
        if G.any():
            from scipy.ndimage import binary_dilation as _dil
            self.goal_mask = G
            self.goal_near = _dil(G, iterations=1)
            self.goal_log["goal_found"] += 1
        else:
            self.goal_mask = None; self.goal_near = None

    def set_win_event(self, f0, f1, cand):
        """The specific rung: remember what the winning press did (in this game's own colours)."""
        if f0 is None or f1 is None or cand is None or f0.shape != f1.shape:
            return
        a, xy, kind = cand
        col = int(f0[int(xy[1]), int(xy[0])]) if (a == CLICK and xy is not None) else None
        eff = {t for t in self.effects(f0, f1, self.dmask(f0, f1))
               if self.eff_count[t] < 0.3 * max(5, self.eff_n)}     # what only the win did, not every press
        self.win_event = dict(act=a, col=col, eff=eff)
        self.goal_log["win_events"] += 1

    def goal_rung_bonus(self, c):
        kk = self._kkey(c)
        t = self.kk_tries.get(kk, 0)
        s = 0.0
        if self.TAKEOVER and self.took_kind.get(kk):
            # kinds of press that made the game take control, by how often they do
            s += self.TAKEOVER * self.took_kind[kk] / max(1, t)
        if self.RELATION and self.rel_kind.get(kk):
            s += self.RELATION * self.rel_kind[kk] / max(1, t)
        if self.WINIMAGE and self.img_kind.get(kk):
            s += self.WINIMAGE * self.img_kind[kk] / max(1, t)
        if self.GOALSEARCH and self.goal_mask is not None:
            if self.goal_kind.get(kk):
                s += self.GOALSEARCH * self.goal_kind[kk] / max(1, t)
            if c[0] == CLICK and c[1] is not None and t == 0 and self.goal_near is not None \
                    and self.goal_near[int(c[1][1]), int(c[1][0])]:
                s += self.GOALSEARCH                    # a thing where the last win's before-picture fits
        if self.WINEVENT:
            if self.ev_kind.get(kk):
                s += self.WINEVENT * self.ev_kind[kk] / max(1, t)
            w = self.win_event
            if w and t == 0 and c[0] == w["act"] and c[0] == CLICK and c[2] and c[2][0] == w["col"]:
                s += 0.5 * self.WINEVENT          # a thing of the colour the last win was pressed on
        return s

    def observe_rungs(self, latest, f, D, died):
        """After each press inside a level: did the game take control? did the press repeat the last
        win's effect? Marks go on the kind of press and on the state it led to."""
        took = ev = img = False
        if self._last_cand is None:
            return
        kk = self._kkey(self._last_cand)
        self.kk_tries[kk] += 1
        if died:
            return
        if self.TAKEOVER:
            nfr = len(latest.frame or [])
            if self.fr_total >= 8 and nfr >= max(3, 2 * self._fr_median()):
                self.took_kind[kk] += 1; took = True; self.goal_log["took"] += 1
            self.fr_counts[nfr] += 1; self.fr_total += 1
        if self.WINEVENT and self.prev_frame is not None:
            eff = self.effects(self.prev_frame, f, D)
            # only effects that are not what presses here usually do single anything out (a clock or a
            # counter that changes on every press would match every press)
            hit = []
            if self.win_event and self.win_event["eff"]:
                hit = [t for t in eff & self.win_event["eff"] if self.eff_count[t] < 0.3 * max(5, self.eff_n)]
            self.eff_count.update(eff); self.eff_n += 1
            if hit:
                self.ev_kind[kk] += 1; ev = True; self.goal_log["winlike"] += 1
        rel = False
        self.eff_n_all = getattr(self, "eff_n_all", 0) + 1
        if self.RELATION and self.prev_frame is not None and D is not None and D.any():
            rel = self.relational(self.prev_frame, f, D)
            if rel and self.REL_GATE:
                # like "took control": only what is unusual for this game singles anything out
                usual = self.rel_seen >= self.REL_GATE * max(10, self.eff_n_all)
                self.rel_seen += 1
                rel = not usual
            if rel:
                self.rel_kind[kk] += 1; self.goal_log["rel"] += 1
        if self.WINIMAGE and self.prev_frame is not None:
            k = self.moment_key(self.prev_frame, f)
            if k is not None:
                if k in self.win_moments:
                    self.img_kind[kk] += 1; img = True; self.goal_log["winimg"] += 1
                self.mom_count[k] += 1; self.mom_n += 1
        goal = False
        if self.GOALSEARCH and self.goal_mask is not None and D is not None and D.shape == self.goal_mask.shape:
            if (D & self.goal_mask).any():
                self.goal_kind[kk] += 1; goal = True; self.goal_log["goal_touched"] += 1
        self._marks = dict(took=took, winlike=ev, rel=rel, winimg=img, goal=goal)

    @staticmethod
    def relational(f0, f1, D):
        """colour-free: a small change far from the main change (an indicator), or a colour that vanished"""
        try:
            from scipy.ndimage import label as _lab, binary_dilation as _dil
        except Exception:
            return False
        g0, g1 = f0[2:-2, 2:-2], f1[2:-2, 2:-2]
        if set(np.unique(g0).tolist()) - set(np.unique(g1).tolist()):
            return True
        DD = D[2:-2, 2:-2]
        if DD.sum() > 1500:
            return False
        lab, n = _lab(DD, structure=np.ones((3, 3), int))
        if n < 2:
            return False
        sizes = np.bincount(lab.ravel())[1:]
        big = int(sizes.argmax()) + 1
        near = _dil(lab == big, iterations=6)
        for i in range(1, min(n, 40) + 1):
            if i != big and sizes[i - 1] <= 36 and not (near & (lab == i)).any():
                return True
        return False

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

    def bfs_pick(self, src, th, extra=6, kmax=40, limit=6000):
        L = self.level
        q = deque([src]); prev = {src: None}; depth = {src: 0}
        seen = 0; cands = []; first = None
        while q and seen < limit:
            k = q.popleft(); seen += 1
            d = depth[k]
            if first is not None and d > first + extra:
                break
            if k != src:
                w = self.want_score(k)
                if w > th:
                    if first is None:
                        first = d
                    n = L.nodes.get(k)
                    bonus = 0.0
                    if n:
                        bonus = self.RARE * n.get("rare", 0.0) + self.TAKEOVER * n.get("took", 0.0) \
                            + self.WINEVENT * n.get("winlike", 0.0) + self.RELATION * n.get("rel", 0.0) \
                            + self.WINIMAGE * n.get("winimg", 0.0) + self.GOALSEARCH * n.get("goal", 0.0)
                    cands.append((w + bonus - 0.15 * d, k))
                    if len(cands) >= kmax:
                        break
            for i, nk in self.successors(k):
                if nk not in prev:
                    prev[nk] = (k, i); depth[nk] = d + 1; q.append(nk)
            if k == src and L.start is not None and L.start not in prev and L.start != src:
                prev[L.start] = (k, "RESET"); depth[L.start] = 1; q.append(L.start)
        if not cands:
            return None
        k = max(cands)[1]
        path = []
        while prev[k] is not None:
            pk, step = prev[k]
            path.append((pk, step)); k = pk
        return path[::-1]

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
            if self.GOALSEARCH and self.level is not None and latest.levels_completed > self.levels_done \
                    and self.prev_frame is not None and latest.frame:
                try:
                    T = self.before_templates(self.prev_frame, np.array(latest.frame[0], dtype=np.int16))
                    if T:
                        self.win_templates = (self.win_templates + [T])[-3:]
                        self.goal_log["win_templates"] += 1
                except Exception:
                    pass
            if self.WINIMAGE and self.level is not None and latest.levels_completed > self.levels_done \
                    and self.prev_frame is not None and latest.frame:
                try:   # the winning press's first frame (the level-end animation comes after it)
                    k = self.moment_key(self.prev_frame, np.array(latest.frame[0], dtype=np.int16))
                    if k is not None and self.mom_count[k] < 0.3 * max(10, self.mom_n):   # not what every press does
                        self.win_moments.add(k); self.goal_log["win_moments"] += 1
                except Exception:
                    pass
            if self.WINEVENT and self.level is not None and latest.levels_completed > self.levels_done \
                    and self.prev_frame is not None and len(latest.frame) >= 2:
                try:   # the press's own effect is the frame before the switch to the next level
                    self.set_win_event(self.prev_frame, np.array(latest.frame[-2], dtype=np.int16), self._last_cand)
                except Exception:
                    pass
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
            self.goal_mask = None; self.goal_near = None
            self.vcache = {}
            self.prev_key = None; self.prev_act = None; self.path = []; self.prev_frame = None
            self.steps_since_reset = 0
            self.mover.box = self.mover.find_patch(f)
        L = self.level
        self.level_simple = [a for a in avail if a not in (RESET, CLICK)]
        self.level_click = CLICK in avail
        if self.prev_frame is not None and self.update_mask(self.prev_frame, f):
            self.rekey()
        if self.CLOCK and self.prev_frame is not None and self.prev_act is not None:
            self.clock_observe(self.prev_frame, f, self.steps_since_reset, self.prev_act, self.life)
        key = self.key(f)
        died = st == GameState.GAME_OVER
        # learn from the transition that brought us here
        if self.prev_key is not None and self.prev_act is not None and self.prev_frame is not None:
            pa = self.prev_act
            D = self.dmask(self.prev_frame, f) if self.prev_frame.shape == f.shape else np.ones((1, 1), bool)
            if not isinstance(pa, tuple) and self.use_model:
                pred = self._pending_pred
                try:
                    self.mover.observe(self.prev_frame, f, pa, D if D.shape == f.shape else np.zeros_like(f, bool), died)
                except Exception:
                    self.stats["mover_error"] += 1
                if pred is not None:
                    if pred == key or (pred == "DEATH" and died):
                        self.mover.ok[pa] += 1; self.stats["pred_ok"] += 1
                    else:
                        self.mover.bad[pa] += 1; self.stats["pred_bad"] += 1
            changed = self.prev_key != key
            self._credit(pa, changed)
            if self.TAKEOVER or self.WINEVENT or self.RELATION or self.WINIMAGE or self.GOALSEARCH:
                try:
                    self.observe_rungs(latest, f, D if D.shape == f.shape else None, died)
                except Exception:
                    self.stats["rung_error"] += 1
            if self.RARE and D.shape == (64, 64):
                self._last_rare = float((1.0 / (1.0 + self.pxcount[D])).sum())
                self.pxcount[D] += 1
            L.edges[(self.prev_key, pa)] = "DEATH" if died else key
            if died:
                L.deaths[(self.prev_key, pa)] += 1
                L.death_steps.append(self.steps_since_reset)
                self._update_budget()
        # the run: the last press, if it changed something
        if self.prev_key is not None and self.prev_act is not None and not died:
            if self.prev_key != key and self._last_cand is not None:
                self.run = self._last_cand
            else:
                self.run = None
        self.cur_key = key
        if self.mover.box is None and self.mover.patch is not None and not died:
            self.mover.box = self.mover.find_patch(f)
        if died:
            self.replay = []
            return self._reset()
        fresh = key not in L.nodes
        n = self.node(key, f, avail, box=self.mover.box)
        if fresh and self.RARE:
            # how rare were the pixels that changed on the way in? (a HUD glyph that seldom changes
            # scores high; the avatar's usual footprint scores low)
            n["rare"] = min(3.0, self._last_rare / 5.0)
        self._last_rare = 0.0
        for nm, v in self._marks.items():
            if v:
                n[nm] = 1.0
        self._marks = {}
        if L.start is None:
            L.start = key
            if self.GOALSEARCH and self.win_templates:
                try:
                    self.find_goal(f)
                except Exception:
                    self.goal_mask = None; self.goal_near = None
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
        if self.RARE or self.TAKEOVER or self.WINEVENT or self.RELATION or self.WINIMAGE or self.GOALSEARCH or self.PICK:
            p = self.bfs_pick(key, th)
        else:
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
    _last_cand = None
    run = None
    cur_key = None

    def _emit(self, key, n, i):
        self.stats["emit"] += 1
        self.level_actions += 1
        a, xy, kind = n["cands"][i]
        self._last_cand = n["cands"][i]
        if self.TAKEOVER or self.WINEVENT or self.WINIMAGE or self.GOALSEARCH or self.RELATION:
            kk = self._kkey(n["cands"][i])
            why = [nm for nm, c in (("took", self.took_kind), ("winevent", self.ev_kind), ("winimg", self.img_kind), ("rel", self.rel_kind), ("goal", self.goal_kind)) if c.get(kk)]
            self.goal_log["cite_" + ("+".join(why) if why else "none")] += 1
        n["tried"].add(i)
        self.prev_key = key
        self.prev_act = self.aid(n["cands"][i])
        self._last_kind = kind if a == CLICK else None
        self._pending_pred = None
        if self.use_model and a not in (CLICK, 7) and n.get("box") is not None:
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
        self.life += 1
        if self.CLOCK and self.clock_update():
            self.rekey()
        self.run = None
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
        self.mind.MOMENTUM = getattr(self, "MOMENTUM", 0.0)
        self.mind.momentum_now = self.mind.MOMENTUM
        self.mind.MOMENTUM_ADAPT = getattr(self, "MOMENTUM_ADAPT", 0.0)
        self.mind.CLOCK = getattr(self, "CLOCK", False)
        self.mind.RARE = getattr(self, "RARE", 0.0)
        self.mind.TAKEOVER = getattr(self, "TAKEOVER", 0.0)
        self.mind.WINEVENT = getattr(self, "WINEVENT", 0.0)
        self.mind.RELATION = getattr(self, "RELATION", 0.0)
        self.mind.PICK = getattr(self, "PICK", False)
        self.mind.WINIMAGE = getattr(self, "WINIMAGE", 0.0)
        self.mind.GOALSEARCH = getattr(self, "GOALSEARCH", 0.0)
        self.mind.REL_GATE = getattr(self, "REL_GATE", 0.0)
        self.mind.DUMP = getattr(self, "DUMP", False)
        pr = getattr(self, "PRIOR", None)
        if isinstance(pr, dict):          # per-game leave-one-out weights, keyed by game prefix
            pr = pr.get(self.game_id[:4], pr.get("all"))
        self.mind.PRIOR = None if pr is None else np.array(pr, dtype=float)
        self.mind.PRIOR_W = getattr(self, "PRIOR_W", 0.5)

    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame):
        try:
            return self.mind.act(latest_frame)
        except Exception:
            # keep her map; forget only the press in flight, and make a harmless press
            m = self.mind
            m.stats["error"] += 1
            m.prev_key = None; m.prev_act = None; m.path = []; m.replay = []
            if m.stats["error"] <= 3:
                import traceback; traceback.print_exc()
            if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER) or not latest_frame.frame:
                return GameAction.RESET
            acts = [a for a in (latest_frame.available_actions or []) if a not in (0, 6)]
            if acts:
                return GameAction.from_id(m.rng.choice(acts))
            act = GameAction.ACTION6
            act.set_data({"x": m.rng.randrange(64), "y": m.rng.randrange(64)})
            return act


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


class Explorer7(Explorer2):
    PREDICT = False
    LESSONS = True
    MOMENTUM = 2.0


class Explorer7b(Explorer7):
    MOMENTUM = 0.8


class Explorer8(Explorer2):
    PREDICT = False
    LESSONS = True
    MOMENTUM_ADAPT = 2.0


class Explorer9(Explorer2):
    PREDICT = False
    LESSONS = True
    CLOCK = True


class Explorer9m(Explorer9):
    MOMENTUM_ADAPT = 2.0


class ExplorerDump(Explorer2):
    PREDICT = False
    LESSONS = True
    DUMP = True


class Explorer4Model(Explorer2):
    LESSONS = True
    KIND_DECAY = 15


class Explorer3Loose(Explorer2):
    LESSONS = True
    STRICT = False


def _load_prior(name="prior.json"):
    import json, os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    try:
        return json.load(open(p))
    except Exception:
        return None


class ExplorerPrior(Explorer2):
    """v3n + the look-back across games: a learned order for untried presses (leave-one-game-out
    weights on the public bench; the all-games weights elsewhere)."""
    PREDICT = False
    LESSONS = True
    PRIOR = _load_prior()
    PRIOR_W = 0.5


class ExplorerPrior1(ExplorerPrior):
    PRIOR_W = 1.0


class ExplorerPrior2(ExplorerPrior):
    PRIOR_W = 2.0
