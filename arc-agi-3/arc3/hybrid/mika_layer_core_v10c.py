"""Mika's evidence layer for a language-model harness (ARC-AGI-3). v10 (Oct 28): the core layer.

v10 says fewer, sharper things. The v8 planes below still run, but only two of their notes are said (the step bar
and a glyph made equal to a still one). The rest comes from what Mika's core learned on ls20 (planes at the end):
operators (what touching a thing does to a small far picture, as a law), the equation (the touches that make that
picture equal to a glyph in a still thing), tracks (things moving by themselves on a loop, one step per move of the
mover) and pushes (moves that did not land one step on).

Mika's planes compute facts from the raw frames and hand them to the model as a few short notes. Nothing
here is written by the model, and nothing here chooses actions: the notes are evidence, the model reasons.

    real plane   per press: where am I (state seen before? what was already tried here?), what did the
                 press do (moved what, how far; changed what; nothing), did the game take control.
    image plane  per win: the before-picture of what the winning press changed; at the next level's first
                 screen, where that picture fits again (its own colours, any flip or rotation).
    school       per level: a digest of the level just won (presses, what each key did, what won it).
    core card    (v6) the slots a press fires, from frames: moved / arrived next to a still thing / made a
                 thing equal to a still thing / a small far thing changed / how many places one press changed.
                 The last win's form is kept with the colours it was bound to (+C), and at the next level's
                 start the layer says where those colours are; during the level, when a press brings the moved
                 thing next to a still thing of a bound colour, or makes something equal to a still thing.

Self-contained (numpy only). Every public method is wrapped: an error means "no note", never a crash.

    layer = MikaLayer()
    layer.observe(before, frames_after, action, level=..., level_done=..., game_over=...)
    lines = layer.notes()            # list of short strings for the next turn message
"""
from __future__ import annotations

import hashlib
import re
import threading
from collections import Counter, defaultdict

import numpy as np

# the harness's own legend (inference/utils/grid_utils.py): index -> letter the model sees, and its name
_CHARS = "WwgGcBMPRbSYOrNp"
_NAMES = ["white", "light gray", "gray", "dark gray", "charcoal", "black", "magenta", "pink", "red", "blue",
          "sky blue", "yellow", "orange", "dark red", "light green", "purple"]


def _cname(c):
    c = int(c)
    return f"{_CHARS[c]} ({_NAMES[c]})" if 0 <= c < 16 else f"colour {c}"


def _label(mask):
    """8-connected components of a boolean mask (scipy if present, else a small flood fill)."""
    try:
        from scipy.ndimage import label
        lab, n = label(mask, structure=np.ones((3, 3), int))
        return lab, n
    except Exception:
        lab = np.zeros(mask.shape, int); n = 0
        H, W = mask.shape
        for y0, x0 in zip(*np.nonzero(mask)):
            if lab[y0, x0]:
                continue
            n += 1; st = [(y0, x0)]; lab[y0, x0] = n
            while st:
                y, x = st.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n; st.append((yy, xx))
        return lab, n


def _box(m):
    ys, xs = np.nonzero(m)
    return int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1


# ---------------------------------------------------------------- the core card (v8)
SLOTS = ["CONTROL+", "CONTROL-", "CONTACT+", "CONTACT-", "MATCH+", "MATCH-", "PLACE+", "PLACE-",
         "COUNT+", "COUNT-", "ORDER+", "ORDER-"]
BOUNDARY = {"CONTROL-", "CONTACT-", "ORDER-"}       # never on a winning route in our data: guards, not goals
_WORDS = {
    "CONTROL+": "moving a thing", "CONTROL-": "presses that changed nothing",
    "CONTACT+": "changing the thing pressed or touched", "CONTACT-": "ending the life",
    "MATCH+": "making a pattern equal to a still one", "MATCH-": "making equal things differ",
    "PLACE+": "bringing the moved thing next to a still thing", "PLACE-": "moving a thing away from a still thing",
    "COUNT+": "a small thing far away changing", "COUNT-": "a step bar running down",
    "ORDER+": "matching a target shown on the screen", "ORDER-": "coming back to a board already seen",
}


class _Card:
    """One level's card: per slot, how often it fired, its first example, the colours it was bound to (+C),
    and the places involved (for telling separate jobs apart)."""
    def __init__(self):
        self.n = Counter(); self.first = {}; self.bind = defaultdict(set); self.won = set(); self.events = []

    def add(self, slot, press, example="", bind=(), things=()):
        self.n[slot] += 1
        if slot not in self.first:
            self.first[slot] = (press, example)
        self.bind[slot] |= {int(c) for c in bind}
        if things and len(self.events) < 300:
            self.events.append((slot, tuple(tuple(int(v) for v in b) for b in things)))

    def kinds(self):
        return {s for s, k in self.n.items() if k}


def _jobs(card):
    """separate jobs on a level: groups of goal events whose places touch (the moved thing is the seam
    they share, so moves are left out); returns up to two groups as (Counter of slots, union box)"""
    ev = [(s, b) for s, b in card.events if s.endswith("+") and not s.startswith("CONTROL") and b][-150:]
    parent = list(range(len(ev)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def touch(a, b):
        return a[0] <= b[1] and b[0] <= a[1] and a[2] <= b[3] and b[2] <= a[3]
    for i in range(len(ev)):
        for j in range(i + 1, len(ev)):
            if any(touch(a, b) for a in ev[i][1] for b in ev[j][1]):
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(ev)):
        groups[find(i)].append(ev[i])
    out = []
    for g in groups.values():
        if len(g) < 3:
            continue
        boxes = [b for _, bs in g for b in bs]
        ub = (min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes))
        out.append((Counter(s for s, _ in g), ub))
    out.sort(key=lambda x: -sum(x[0].values()))
    if len(out) < 2:
        return out
    (c1, b1), (c2, b2) = out[0], out[1]
    far = not (b1[0] <= b2[1] + 4 and b2[0] <= b1[1] + 4 and b1[2] <= b2[3] + 4 and b2[2] <= b1[3] + 4)
    if not far or c1.most_common(1)[0][0] == c2.most_common(1)[0][0]:
        return out[:1]                     # one job seen from two sides, not two jobs
    return out[:2]


# lines shared by every game running in this process (the competition rerun plays its games as threads of one
# process): what winning presses and ordinary presses were made of, per game, without any game's specifics
_LINES_LOCK = threading.Lock()
_LINES = {}


def _lines_add(gid, press_slots=None, win_slots=None):
    try:
        with _LINES_LOCK:
            d = _LINES.setdefault(gid, {"wins": 0, "win": Counter(), "presses": 0, "press": Counter()})
            if press_slots is not None:
                d["presses"] += 1; d["press"].update(set(press_slots))
            if win_slots is not None:
                d["wins"] += 1; d["win"].update(set(win_slots))
    except Exception:
        pass


def _lines_top(gid, min_wins=8, min_games=3, min_lift=1.5):
    """the line (slot) that winning presses of OTHER games had most often relative to their ordinary presses"""
    try:
        with _LINES_LOCK:
            others = [d for g, d in _LINES.items() if g != gid]
            wins = sum(d["wins"] for d in others); games = sum(1 for d in others if d["wins"])
            pres = sum(d["presses"] for d in others)
            if wins < min_wins or games < min_games or pres < 50:
                return None
            best = None
            for s in SLOTS:
                if s in BOUNDARY or s.startswith("CONTROL") or s.startswith("CONTACT") or s == "ORDER+":
                    continue                      # a winning press always changes something; ORDER+ = MATCH+
                k = sum(d["win"][s] for d in others); share = sum(d["press"][s] for d in others) / pres
                if k < 3:
                    continue
                lift = (k / wins) / max(share, 1e-3)
                if lift >= min_lift and (best is None or lift > best[3]):
                    best = (s, k, wins, lift, share)
            return best
    except Exception:
        return None


class _Level:
    def __init__(self, idx):
        self.idx = idx
        self.visits = Counter()                 # state -> times seen
        self.tried = defaultdict(dict)          # state -> {action: outcome text}
        self.key_stats = defaultdict(Counter)   # action -> Counter(outcome kind)
        self.key_shift = defaultdict(Counter)   # action -> Counter((dy, dx)) of the main moved thing
        self.presses = 0
        self.recent = []                        # recent states (loop detection)
        self.start_frame = None
        self.goal_places = []                   # [(y0, y1, x0, x1)] where an earlier win's before-picture fits
        self.goal_said = set()                  # places already reported as changed (once per level)
        self.notes_sent = set()
        self.start_things = None                # things on the start screen (core card)
        self.changed = None                     # pixels changed on this level so far
        self.equal_said = set()                 # (place, still place) pairs reported as made equal
        self.arrive_said = set()                # still places reported as arrived at
        self.key_places = defaultdict(Counter)  # action -> Counter(number of separate places one press changed)
        self.cons = defaultdict(Counter)        # colour -> {"kept": n, "broke": n}: totals over reshaping presses
        self.cons_said = set()
        self.clicks = {}                        # thing box at the click -> [colours at the click point]
        self.cycles_said = set()
        self.card = _Card()                     # v8: this level's card
        self.wide_said = False                  # the stall spray, once per level
        self.last_cells = None                  # step-bar cells after the previous press


class MikaLayer:
    def __init__(self, max_lines=3):
        self.max_lines = max_lines
        self.level = None
        self.levels_won = []                    # digests of won levels
        self.win_templates = []                 # [[template arrays]] per won level (last 3)
        self.fr_counts = Counter(); self.fr_total = 0
        self.row_hits = np.zeros(64); self.col_hits = np.zeros(64); self.n_obs = 0
        self.mask_rows = set(); self.mask_cols = set()
        self.bar = None                         # (side, index) of a step bar on the border, if found
        self.bar_hist = []                      # [(press, cells used)]
        self._pending = []                      # notes produced by the last observation
        self.bind = set()                       # colours the last win's form was bound to (+C)
        self._tcache = (None, None)             # (board key, things) of the last frame looked at
        self.cards = []                         # v8: cards of the levels won, in order (the chain of cores)
        self.level_presses = []                 # presses each won level took
        self.track = defaultdict(lambda: [0, 0])  # slot -> [levels it came back on, levels it was carried into]
        self.gid = id(self)
        self.slot_n = Counter(); self.n_board = 0
        self.jobs_log = []  # how often each slot fires on this game's board-changing presses
        self._core_pending = []                 # v10: notes from the core planes
        self.c10 = None

    # ------------------------------------------------------------------ perception helpers
    def _key(self, f):
        g = np.array(f, dtype=np.int16, copy=True)
        if self.mask_rows:
            g[sorted(self.mask_rows), :] = -1
        if self.mask_cols:
            g[:, sorted(self.mask_cols)] = -1
        return hashlib.blake2b(g.tobytes(), digest_size=8).hexdigest()

    def _update_ticker(self, f0, f1):
        """lines along the border that change by a few pixels on most presses are clocks, not the world"""
        if f0.shape != (64, 64) or f1.shape != (64, 64):
            return
        d = f0 != f1
        r = d.sum(1); c = d.sum(0)
        self.row_hits += (r > 0) & (r <= 3); self.col_hits += (c > 0) & (c <= 3)
        self.n_obs += 1
        if self.n_obs >= 6:
            for i in list(range(0, 3)) + list(range(61, 64)):
                if self.row_hits[i] >= 0.3 * self.n_obs:
                    self.mask_rows.add(i)
                if self.col_hits[i] >= 0.3 * self.n_obs:
                    self.mask_cols.add(i)

    def _inner_diff(self, f0, f1):
        D = f0 != f1
        D[:2, :] = False; D[-2:, :] = False; D[:, :2] = False; D[:, -2:] = False
        if self.mask_rows:
            D[sorted(self.mask_rows), :] = False
        if self.mask_cols:
            D[:, sorted(self.mask_cols)] = False
        return D

    def _describe(self, f0, f1):
        """what one press did, in a few words, plus (dy, dx) of the main moved thing if it moved"""
        D = self._inner_diff(f0, f1)
        if not D.any():
            return "nothing", None, D
        lab, n = _label(D)
        sizes = np.bincount(lab.ravel())[1:]
        big = int(sizes.argmax()) + 1
        M = lab == big
        before = Counter(f0[M].tolist()); after = Counter(f1[M].tolist())
        # moved: the same colours rearranged (something left one place and appeared at another)
        if len(before) >= 2:
            shift = self._shift(f0, f1, M)
            if shift is not None:
                return "moved", shift, D
        if len(before) == 1 and len(after) == 1:
            (b, _), = before.items(); (a, _), = after.items()
            return f"recoloured {_cname(b)}->{_cname(a)}", None, D
        y0, y1, x0, x1 = _box(M)
        bs = "/".join(_cname(c) for c, _ in before.most_common(3)); as_ = "/".join(_cname(c) for c, _ in after.most_common(3))
        return f"changed a {y1 - y0}x{x1 - x0} region at rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1} from {bs} to {as_}", None, D

    @staticmethod
    def _shift(f0, f1, M):
        """displacement that maps the moved thing's old pixels onto its new ones (small search)"""
        y0, y1, x0, x1 = _box(M)
        best = None
        vals0 = f0[y0:y1, x0:x1]
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                if dy == 0 and dx == 0:
                    continue
                ys, xs = np.nonzero(M[y0:y1, x0:x1])
                yy = ys + y0 + dy; xx = xs + x0 + dx
                ok = (yy >= 0) & (yy < 64) & (xx >= 0) & (xx < 64)
                if ok.mean() < 0.9:
                    continue
                src = f0[ys[ok] + y0, xs[ok] + x0]
                dst = f1[yy[ok], xx[ok]]
                moved = src != f0[yy[ok], xx[ok]]
                if moved.sum() < 2:
                    continue
                frac = float((src[moved] == dst[moved]).mean())
                if frac >= 0.9 and (best is None or frac > best[0] or (frac == best[0] and abs(dy) + abs(dx) < abs(best[1]) + abs(best[2]))):
                    best = (frac, dy, dx)
        _ = vals0
        return None if best is None else (best[1], best[2])

    def _bar_cells(self, f):
        """cells of the step bar still 'full' (the bar is the border line whose one colour shrinks)"""
        if self.bar is None:
            return None
        side, i = self.bar
        line = f[i, :] if side == "row" else f[:, i]
        return int((line == self.bar_colour).sum())

    def _find_bar(self, f0, f1):
        if self.bar is not None or f0.shape != (64, 64):
            return
        for side in ("row", "col"):
            for i in list(range(0, 3)) + list(range(61, 64)):
                a = f0[i, :] if side == "row" else f0[:, i]
                b = f1[i, :] if side == "row" else f1[:, i]
                if (a != b).sum() in (1, 2, 3):
                    c = Counter(a[a != b].tolist()).most_common(1)[0][0]
                    if (a == c).sum() >= 12:
                        self.bar = (side, i); self.bar_colour = c; self.bar_full = int((a == c).sum())
                        return

    # ------------------------------------------------------------------ the core card: things and slots
    @staticmethod
    def _sig(p, turns=False):
        """the picture of a thing (its own colours), as drawn, or up to the 8 flips/rotations"""
        best = None
        for k in range(8 if turns else 1):
            t = np.rot90(p, k % 4)
            if k >= 4:
                t = np.fliplr(t)
            h = hashlib.blake2b(np.ascontiguousarray(t).tobytes() + bytes(t.shape), digest_size=8).hexdigest()
            if best is None or h < best:
                best = h
        return best

    def _thing(self, g, m, grain):
        y0, y1, x0, x1 = _box(m)
        p = np.where(m[y0:y1, x0:x1], g[y0:y1, x0:x1], -1).astype(np.int16)
        cols = sorted(int(c) for c in np.unique(p) if c >= 0)
        n = int(m.sum())
        t = dict(mask=m, box=(y0, y1, x0, x1), sig=self._sig(p), cols=cols, n=n, grain=grain,
                 plain=(len(cols) == 1 and n == (y1 - y0) * (x1 - x0)), glyphs={})
        if grain == "composite":
            cnt = Counter(p[p >= 0].tolist())
            frame = cnt.most_common(1)[0][0]
            for c in cols:
                if c == frame or cnt[c] < 3:
                    continue
                gm = p == c
                gy, gx = np.nonzero(gm)
                q = gm[gy.min():gy.max() + 1, gx.min():gx.max() + 1]
                k = self._scale(q)
                r = q[::k, ::k]
                if r.sum() >= 3 and not r.all():
                    t["glyphs"][c] = (self._sig(r.astype(np.int16), turns=False), k)
        return t

    @staticmethod
    def _scale(q):
        """the largest k such that the pattern is made of k x k blocks (a picture drawn k times larger)"""
        h, w = q.shape
        for k in range(min(h, w), 1, -1):
            if h % k or w % k:
                continue
            r = q[::k, ::k]
            if np.array_equal(np.repeat(np.repeat(r, k, 0), k, 1), q):
                return k
        return 1

    def _glyph_equal(self, f0, f1, D):
        """(changed thing, still thing, colour, scales): a pattern of one colour inside a thing the press changed
        now equals the pattern of that colour inside a still thing, same way up, any size"""
        still = [t for t in self._still(D) if t["glyphs"]]
        if not still:
            return None
        t1, _ = self._things(f1)
        t0, _ = self._things(f0)
        Dg = self._grow(D, 1)
        had = {(c, gs[0]) for t in t0 if (t["mask"] & Dg).any() for c, gs in t["glyphs"].items()}
        for t in t1:
            if not t["glyphs"] or not (t["mask"] & D).any():
                continue
            for c, (sg, k) in t["glyphs"].items():
                if (c, sg) in had:
                    continue
                for s in still:
                    if c in s["glyphs"] and s["glyphs"][c][0] == sg and not (s["mask"] & self._grow(t["mask"], 1)).any():
                        return t, s, c, (k, s["glyphs"][c][1])
        return None

    def _things(self, f):
        """things: same-colour regions of 2..400 pixels (bigger ones are floors and walls), and composites of
        touching small regions with 2+ colours (up to 400 pixels). Border lines and clocks are left out."""
        k = self._key(f)
        if self._tcache[0] == k:
            return self._tcache[1]
        g = np.array(f, dtype=np.int16, copy=True)
        vals, cnt = np.unique(g[2:-2, 2:-2], return_counts=True)
        bg = int(vals[cnt.argmax()])
        g[:2, :] = bg; g[-2:, :] = bg; g[:, :2] = bg; g[:, -2:] = bg
        for r in self.mask_rows:
            g[r, :] = bg
        for c in self.mask_cols:
            g[:, c] = bg
        out = []
        small = np.zeros(g.shape, bool)
        for c in np.unique(g):
            if c == bg:
                continue
            lab, n = _label(g == c)
            if n > 150:
                continue
            sizes = np.bincount(lab.ravel())
            for i in range(1, n + 1):
                s = int(sizes[i])
                if s > 400:
                    continue
                m = lab == i
                if s < 2:
                    small |= m                   # a single pixel: only as part of a composite
                    continue
                out.append(self._thing(g, m, "part"))
                if s <= 100:
                    small |= m
        lab, n = _label(small)
        for i in range(1, min(n, 200) + 1):
            m = lab == i
            if m.sum() > 400 or len(np.unique(g[m])) < 2:
                continue
            out.append(self._thing(g, m, "composite"))
        res = (out, bg)
        self._tcache = (k, res)
        return res

    @staticmethod
    def _grow(m, r=1):
        out = m.copy()
        for _ in range(r):
            o = out.copy()
            o[1:, :] |= out[:-1, :]; o[:-1, :] |= out[1:, :]; o[:, 1:] |= out[:, :-1]; o[:, :-1] |= out[:, 1:]
            o[1:, 1:] |= out[:-1, :-1]; o[:-1, :-1] |= out[1:, 1:]; o[1:, :-1] |= out[:-1, 1:]; o[:-1, 1:] |= out[1:, :-1]
            out = o
        return out

    def _still(self, D=None):
        """things on the level's start screen that no press has changed yet (not plain rectangles)"""
        L = self.level
        if L is None or L.start_things is None:
            return []
        ch = L.changed.copy() if L.changed is not None else None
        if D is not None and ch is not None and ch.shape == D.shape:
            ch |= D
        ch = self._grow(ch, 1) if ch is not None and ch.any() else None
        return [t for t in L.start_things if not t["plain"] and (ch is None or not (t["mask"] & ch).any())]

    def _arrived(self, f0, f1, D):
        """still things the moved thing now touches and did not touch before"""
        lab, n = _label(D)
        if not n:
            return []
        sizes = np.bincount(lab.ravel())[1:]
        M = lab == int(sizes.argmax()) + 1
        t0, bg = self._things(f0)
        new = M & (f1 != bg); old = M & (f0 != bg)
        gn, go = self._grow(new, 1), self._grow(old, 1)
        out = []
        for t in t0:
            if (t["mask"] & D).any() or t["n"] < 2 or t["n"] > 100:
                continue
            if (t["mask"] & gn).any() and not (t["mask"] & go).any():
                out.append(t)
        return out

    def _made_equal(self, f0, f1, D):
        """(changed thing, still thing): a thing the press changed now has the same picture as a still thing"""
        still = self._still(D)
        if not still:
            return None
        sc = Counter(t["sig"] for t in still)
        t1, _ = self._things(f1)
        t0, _ = self._things(f0)
        Dg = self._grow(D, 1)
        before = {t["sig"] for t in t0 if (t["mask"] & Dg).any()}     # what the changed place held: moved, not made
        for t in t1:
            if t["plain"] or t["n"] < 4 or not (t["mask"] & D).any():
                continue
            if t["sig"] in before:
                continue
            for s in still:
                if s["sig"] == t["sig"] and sc[s["sig"]] <= 2 and not (s["mask"] & self._grow(t["mask"], 1)).any():
                    return t, s
        return None

    def _far(self, D):
        """small changed places (<= 36 pixels) away from the main change: indicators"""
        lab, n = _label(D)
        if n < 2:
            return []
        sizes = np.bincount(lab.ravel())[1:]
        big = int(sizes.argmax()) + 1
        near = self._grow(lab == big, 6)
        return [lab == i for i in range(1, n + 1) if i != big and sizes[i - 1] <= 36 and not (near & (lab == i)).any()]

    def _win_form(self, f0, eff, action):
        """the winning press's form in slot words, and the colours it was bound to"""
        D = self._inner_diff(f0, eff)
        if not D.any():
            return "", set(), set()
        words, bind, slots = [], set(), set()
        kind, shift, _ = self._describe(f0, eff)
        if kind == "moved":
            slots.add("CONTROL+")
            arr = self._arrived(f0, eff, D)
            if arr:
                slots.add("PLACE+")
                t = max(arr, key=lambda t: t["n"])
                y0, y1, x0, x1 = t["box"]
                words.append(f"the moved thing arrived next to a still {'/'.join(_cname(c) for c in t['cols'][:2])} thing "
                             f"(rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1})")
                bind |= set(t["cols"][:2])
        m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            if 0 <= r < f0.shape[0] and 0 <= c < f0.shape[1]:
                bind.add(int(f0[r, c]))
                slots.add("CONTACT+")
        elif kind != "moved":
            slots.add("CONTACT+")
        me = self._made_equal(f0, eff, D)
        if me:
            slots |= {"MATCH+", "ORDER+"}
            t, s = me
            words.append(f"it made a thing equal to the still thing at rows {s['box'][0]}-{s['box'][1] - 1}, cols "
                         f"{s['box'][2]}-{s['box'][3] - 1}")
            bind |= set(s["cols"][:2])
        else:
            ge = self._glyph_equal(f0, eff, D)
            if ge:
                slots |= {"MATCH+", "ORDER+"}
                t, s, c, _ = ge
                words.append(f"it made the {_cname(c)} pattern of a thing equal to the one inside the still thing at rows "
                             f"{s['box'][0]}-{s['box'][1] - 1}, cols {s['box'][2]}-{s['box'][3] - 1}")
                bind.add(c)
        for F in self._far(D)[:1]:
            slots.add("COUNT+")
            y0, y1, x0, x1 = _box(F)
            after = sorted({int(c) for c in np.unique(eff[F])})
            words.append(f"a small thing far away changed (rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1}, now "
                         f"{'/'.join(_cname(c) for c in after[:2])})")
            bind |= set(after[:2])
        return ("; ".join(words), bind, slots)

    def _bound_places(self, f):
        """where the colours of the last win's form are on a new screen (few places only)"""
        if not self.bind:
            return ""
        ts, bg = self._things(f)
        parts = []
        for c in sorted(self.bind):
            if c == bg:
                continue
            pl = [t["box"] for t in ts if t["grain"] == "part" and t["cols"] == [c]]
            if not pl or len(pl) > 6:
                continue
            parts.append(f"{_cname(c)} at " + ", ".join(f"rows {y0}-{y1 - 1} cols {x0}-{x1 - 1}" for y0, y1, x0, x1 in pl[:3])
                         + (f" (+{len(pl) - 3})" if len(pl) > 3 else ""))
        return "; ".join(parts[:3])

    # ------------------------------------------------------------------ the image plane
    @staticmethod
    def _before_templates(f0, f1):
        D = np.zeros(f0.shape, bool)
        D[2:-2, 2:-2] = (f0 != f1)[2:-2, 2:-2]
        lab, n = _label(D)
        out = []
        for i in range(1, min(n, 20) + 1):
            m = lab == i
            y0, y1, x0, x1 = _box(m)
            if m.sum() < 2 or y1 - y0 > 24 or x1 - x0 > 24:
                continue
            out.append(np.where(m[y0:y1, x0:x1], f0[y0:y1, x0:x1], -1).astype(np.int16))
        return out

    @staticmethod
    def _fits(S, T):
        from numpy.lib.stride_tricks import sliding_window_view
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
                places.append((int(y), int(y) + h, int(x), int(x) + w))
        return sorted(set(places))

    # ------------------------------------------------------------------ main entry points
    def start_level(self, frame, idx):
        try:
            f = np.asarray(frame, dtype=np.int16)
            self.level = _Level(idx)
            self.level.start_frame = f
            try:
                _c10_start(self, f)
            except Exception:
                pass
            if self.win_templates:
                places = []
                for temps in self.win_templates[-1:]:
                    for T in temps:
                        p = self._fits(f, T)
                        if 0 < len(p) <= 6:          # fits almost everywhere: says nothing
                            places += p
                self.level.goal_places = places[:6]
                if self.level.goal_places:
                    y0, y1, x0, x1 = self.level.goal_places[0]
                    more = f" (and {len(self.level.goal_places) - 1} more)" if len(self.level.goal_places) > 1 else ""
                    self._pending.append(
                        f"[Frame facts] Last level was won by a press that changed a small picture; the same before-picture "
                        f"(same colours, maybe flipped or rotated) is on this screen at rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1}{more}.")
            if self.levels_won:
                self._pending.append("[Frame facts] " + self.levels_won[-1])
            try:
                cl = self._card_line()
                if cl:
                    self._pending.append(cl)
            except Exception:
                pass
            try:
                self.level.start_things = self._things(f)[0]
                self.level.changed = np.zeros(f.shape, bool)
                bp = self._bound_places(f)
                if bp:
                    self._pending.append(f"[Frame facts] Colours of the last win's form on this screen: {bp}.")
            except Exception:
                pass
        except Exception:
            pass

    def reset_life(self, frame=None):
        """a RESET (by the model or after a death): the level restarts; the map of the level is kept"""
        try:
            if self.level is not None:
                self.level.recent = []
            _c10_reset(self)
        except Exception:
            pass

    def observe(self, before, frames_after, action, level=None, level_done=False, game_over=False, effect_known=True):
        """One real press: `before` the frame before it, `frames_after` the frames it produced (an
        animation is several), `action` its name (e.g. 'UP', 'MOUSE@12,40')."""
        try:
            f0 = np.asarray(before, dtype=np.int16)
            frames = [np.asarray(x, dtype=np.int16) for x in (frames_after or [])]
            if not frames:
                return
            f1 = frames[-1]
            if self.level is None:
                self.start_level(f0, level or 0)
            L = self.level
            L.presses += 1
            nfr = len(frames)
            usual = self._usual_frames()
            changed_any = bool((f0 != f1).any())
            took = changed_any and self.fr_total >= 8 and nfr >= max(3, 2 * usual)
            if changed_any:
                self.fr_counts[nfr] += 1; self.fr_total += 1
            if level_done:
                form = ""
                won = set()
                if effect_known and len(frames) >= 1:
                    eff = frames[0]
                    kind, shift, _ = self._describe(f0, eff)
                    self.win_templates = (self.win_templates + [self._before_templates(f0, eff)])[-3:]
                    try:
                        form, bind, won = self._win_form(f0, eff, action)
                        self.bind = bind
                    except Exception:
                        form = ""
                else:                                # only the next level's first screen is known
                    kind, shift = "won the level", None
                keys = ", ".join(self._key_summary(a) for a in sorted(L.key_stats)[:4])
                jobs = ""
                try:
                    jobs = self._finish_card(L, won)
                except Exception:
                    pass
                self.levels_won.append(f"Level {L.idx + 1} digest: won in {L.presses} presses; the winning press "
                                       f"({action}) {self._words(kind, shift)}" + (f"; {form}" if form else "") + "."
                                       + (f" Keys there: {keys}." if keys else "") + jobs)
                self.level = None
                self.start_level(f1, (level if level is not None else L.idx) + 1)   # the last frame is the next level's first
                return
            if game_over:
                L.card.add("CONTACT-", L.presses, str(action))
                self._pending.append(f"[Frame facts] That press ({action}) ended the life after {L.presses} presses this level.")
                return
            self._update_ticker(f0, f1)
            self._find_bar(f0, f1)
            k0 = self._key(f0); k1 = self._key(f1)
            kind, shift, D = self._describe(f0, f1)
            outcome = self._words(kind, shift)
            base_action = self._action_kind(str(action), f0)
            nplaces = 0
            if D.any():
                nplaces = _label(D)[1]
                if kind != "moved" and nplaces >= 2:
                    outcome += f" ({nplaces} separate places changed)"
                L.key_places[base_action][min(nplaces, 9)] += 1
            L.key_stats[base_action][kind.split(" ")[0]] += 1
            if shift is not None:
                L.key_shift[base_action][shift] += 1
            L.tried[k0][str(action)] = outcome
            L.visits[k1] += 1
            L.recent = (L.recent + [k1])[-16:]
            try:
                _c10_observe(self, f0, f1, action, D, kind, shift)
            except Exception as _e:
                self.c10_errs = getattr(self, "c10_errs", 0) + 1; self.c10_last_err = repr(_e)
            ev = {}
            try:
                ev = self._sense(f0, f1, D, kind, shift, action, base_action, k1)
            except Exception:
                ev = {}
            try:
                self._core_notes(f0, f1, D, kind, action, ev)
            except Exception:
                pass
            try:
                self._action_notes(f0, f1, D, kind, action)
            except Exception:
                pass
            if L.changed is not None and D.any() and L.changed.shape == D.shape:
                L.changed |= D
            if took:
                self._pending.append(f"[Frame facts] {action}: the game took control ({nfr} frames, usual {usual}); something "
                                     f"happened beyond a normal move.")
            if L.visits[k1] in (3, 6, 12) and k1 in L.tried:
                done = ", ".join(f"{a}: {o}" for a, o in list(L.tried[k1].items())[:5])
                self._pending.append(f"[Frame facts] This exact board has been seen {L.visits[k1]} times this level. Already "
                                     f"tried from here: {done}.")
            if len(L.recent) >= 16 and len(set(L.recent)) <= 4 and L.presses % 8 == 0:
                self._pending.append(f"[Frame facts] Loop: the last 16 presses visited only {len(set(L.recent))} distinct boards.")
            if L.goal_places and D.any():
                keep = []; said = False
                for (y0, y1, x0, x1) in L.goal_places:
                    if D[y0:y1, x0:x1].any():
                        if L.presses <= 3:
                            continue                 # it moves from the start: it is the thing she moves
                        if not said and (y0, y1, x0, x1) not in L.goal_said:
                            said = True
                            L.goal_said.add((y0, y1, x0, x1))
                            self._pending.append(f"[Frame facts] {action} changed the place where the last level's winning "
                                                 f"picture fits (rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1}).")
                    keep.append((y0, y1, x0, x1))
                L.goal_places = keep
            if self.bar is not None:
                cells = self._bar_cells(f1)
                if cells is not None:
                    self.bar_hist.append((L.presses, cells))
                    if L.last_cells is not None and cells < L.last_cells:
                        L.card.add("COUNT-", L.presses, "step bar")
                    L.last_cells = cells
                try:
                    _jn_bar(self, f1)                   # v10c: per life, said in presses
                except Exception:
                    pass
            try:
                self._port()
            except Exception:
                pass
        except Exception:
            pass

    def _action_notes(self, f0, f1, D, kind, action):
        """the action model: totals a press reshapes but keeps (conserved), and colour cycles of clicked things"""
        L = self.level
        if L is None or not D.any():
            return
        # conserved totals: the press moved pixels of a colour between places, not as one shifted thing
        if kind != "moved":
            vals, cnt = np.unique(f0[2:-2, 2:-2], return_counts=True)
            bg = int(vals[cnt.argmax()])
            for c in set(np.unique(f0[D]).tolist()) | set(np.unique(f1[D]).tolist()):
                c = int(c)
                if c == bg:
                    continue
                G = (f0 == c) & (f1 != c) & D; A = (f1 == c) & (f0 != c) & D
                if G.any() and A.any():
                    # between two different things: the pixels gained join one thing of this colour, the pixels
                    # lost leave another one standing (one thing moving is not a transfer)
                    lab, _ = _label(f1 == c)
                    ids_a = set(np.unique(lab[A]).tolist()) - {0}
                    ids_g = set(np.unique(lab[self._grow(G, 1) & (f1 == c) & ~D]).tolist()) - {0}
                    if not ids_a or not ids_g or (ids_a & ids_g):
                        continue
                    n0, n1 = int((f0 == c).sum()), int((f1 == c).sum())
                    L.cons[c]["kept" if n0 == n1 else "broke"] += 1
                    if n0 == n1:
                        L.card.add("COUNT+", L.presses, f"{_cname(c)} passed between two things", bind=[c])
                    if n0 == n1:
                        L.cons[c]["total"] = n1
            for c, st in L.cons.items():
                if st["kept"] >= 4 and not st["broke"] and c not in L.cons_said:
                    L.cons_said.add(c)
                    self._pending.append(f"[Frame facts] Conserved so far: in {st['kept']} presses {_cname(c)} pixels moved "
                                         f"between places but their total stayed {st['total']} (what one place gains, another loses).")
                    break
        # click cycles: the colour at a clicked thing, click after click
        m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            if 0 <= r < f0.shape[0] and 0 <= c < f0.shape[1] and D[max(0, r - 1):r + 2, max(0, c - 1):c + 2].any():
                ts, _ = self._things(f0)
                own = [t for t in ts if t["mask"][r, c]]
                k = min(own, key=lambda t: t["n"])["box"] if own else (r, r + 1, c, c + 1)
                seq = L.clicks.setdefault(k, [int(f0[r, c])])
                seq.append(int(f1[r, c]))
                if len(seq) >= 3 and seq[-1] == seq[0] and len(set(seq[:-1])) == len(seq) - 1:
                    cyc = tuple(seq)
                    canon = min(tuple(cyc[i:-1] + cyc[:i]) for i in range(len(cyc) - 1))
                    L.card.add("ORDER-", L.presses, "click cycle", bind=list(cyc[:-1]))
                    if canon not in L.cycles_said:
                        L.cycles_said.add(canon)
                        y0, y1, x0, x1 = k
                        self._pending.append(f"[Frame facts] Clicking the thing at rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1} cycles its colour: "
                                             + " -> ".join(_CHARS[v] if 0 <= v < 16 else str(v) for v in cyc)
                                             + f" ({len(cyc) - 1} clicks back to the start).")
                    L.clicks[k] = [seq[-1]]
                elif len(seq) > 7 or (seq[-1] in seq[:-1] and seq[-1] != seq[0]):
                    L.clicks[k] = [seq[-1]]

    def _sense(self, f0, f1, D, kind, shift, action, base_action, k1):
        """the card's sensors: which slots this press fired, with what it was bound to"""
        L = self.level
        C = L.card; p = L.presses; fired = set()
        if not D.any():
            C.add("CONTROL-", p, base_action)
            _lines_add(self.gid, press_slots=set())
            return {}
        lab, n = _label(D)
        sizes = np.bincount(lab.ravel())[1:]
        main = _box(lab == int(sizes.argmax()) + 1)
        if kind == "moved":
            ex = f"{base_action} moved a thing by {shift[0]:+d},{shift[1]:+d}" if shift else base_action
            C.add("CONTROL+", p, ex, things=[main]); fired.add("CONTROL+")
        m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
        near = False
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            if 0 <= r < f0.shape[0] and 0 <= c < f0.shape[1] and D[max(0, r - 3):r + 4, max(0, c - 3):c + 4].any():
                near = True
                C.add("CONTACT+", p, f"{action} changed the {_cname(f0[r, c])} thing there", bind=[f0[r, c]],
                      things=[(r, r + 1, c, c + 1)]); fired.add("CONTACT+")
        if not near and kind != "moved":
            C.add("CONTACT+", p, f"{base_action} {kind.split(' at ')[0]}", things=[main]); fired.add("CONTACT+")
        ge = self._glyph_equal(f0, f1, D)
        me = None if ge else self._made_equal(f0, f1, D)
        if ge:
            t, s, c, _ = ge
            for sl in ("MATCH+", "ORDER+"):
                C.add(sl, p, f"{_cname(c)} pattern made equal to the one in the still thing", bind=[c], things=[t["box"], s["box"]])
            fired |= {"MATCH+", "ORDER+"}
        elif me:
            t, s = me
            for sl in ("MATCH+", "ORDER+"):
                C.add(sl, p, "a thing made equal to a still thing", bind=s["cols"][:2], things=[t["box"], s["box"]])
            fired |= {"MATCH+", "ORDER+"}
        arr = self._arrived(f0, f1, D) if kind == "moved" else []
        for t in arr[:2]:
            C.add("PLACE+", p, f"arrived next to a still {'/'.join(_cname(c) for c in t['cols'][:2])} thing",
                  bind=t["cols"][:2], things=[t["box"]]); fired.add("PLACE+")
        far = self._far(D)
        for F in far[:1]:
            C.add("COUNT+", p, "a small thing far away changed", bind=np.unique(f1[F]).tolist()[:2], things=[_box(F)])
            fired.add("COUNT+")
        if L.visits.get(k1, 0) >= 2:
            C.add("ORDER-", p, "board seen before"); fired.add("ORDER-")
        self.slot_n.update(fired); self.n_board += 1
        _lines_add(self.gid, press_slots=fired)
        return dict(ge=ge, me=me, arr=arr, far=far)

    def _finish_card(self, L, won):
        """close a won level's card: its win slots, the track record of carried slots, the shared lines, and
        whether it had separate jobs (a body of two cores joined at the moved thing)"""
        C = L.card
        C.won = set(won)
        for sl in won:
            C.n[sl] += 0
        if self.cards:
            prev = self.cards[-1].kinds()
            for sl in prev:
                self.track[sl][1] += 1
                if C.n[sl]:
                    self.track[sl][0] += 1
        self.cards.append(C)
        self.level_presses.append(L.presses)
        _lines_add(self.gid, win_slots=won)
        # separate jobs (a body of two cores): measured from frames, the split mostly separates a press from its
        # own indicator rather than two jobs, so it is kept for the log only and not said to the model
        self.jobs_log.append(_jobs(C))
        return ""

    def _share(self, s):
        return self.slot_n[s] / self.n_board if self.n_board else 0.0

    def _won_kinds(self):
        """slots that came with earlier wins, rarest-on-ordinary-presses first; slots that fire on most presses
        of this game (every click changes something, every key moves something) say nothing and are left out"""
        won = Counter(s for c in self.cards for s in c.won if s not in BOUNDARY and not s.startswith("CONTROL"))
        return [(s, k) for s, k in sorted(won.items(), key=lambda x: -x[1] / max(self._share(x[0]), 0.02))
                if self._share(s) < 0.35]

    @staticmethod
    def _merge(slots):
        """MATCH+ and ORDER+ always come together (a match is made with a shown target): say them once"""
        out = [s for s in slots if not (s == "ORDER+" and "MATCH+" in slots)]
        return out

    def _card_line(self):
        """the carried cores, said once at a new level: what wins were made of, what every level had, what was new"""
        if not self.cards:
            return ""
        nc = len(self.cards)
        won = Counter(dict(self._won_kinds()))
        every = [s for s in SLOTS if s not in BOUNDARY and s not in won and all(c.n[s] for c in self.cards)
                 and (self._share(s) < 0.35 or s == "COUNT-")]
        parts = []
        if won:
            ws = self._merge([s for s, _ in won.most_common()])
            parts.append("wins came with " + ", ".join(f"{_WORDS[s]} ({won[s]} of {nc})" for s in ws[:3]))
        every = self._merge(every)
        if every:
            parts.append("every level so far also had " + ", ".join(_WORDS[s] for s in every[:3]))
        if nc >= 2:
            new = self._merge([s for s in SLOTS if s not in BOUNDARY and self.cards[-1].n[s] and not self.cards[-2].n[s]
                               and self._share(s) < 0.5])
            if new:
                parts.append("new on the last level: " + ", ".join(_WORDS[s] for s in new[:2]))
        if not parts:
            return ""
        lv = f"level 1" if nc == 1 else f"levels 1-{nc}"
        return f"[Frame facts] Card from {lv}: " + "; ".join(parts) + "."

    def _port(self):
        """the stall spray: when a level runs long, offer what the carried card (or the other games) says is
        still missing; once per level. Narrow sprays (bound places, made-equal) are said where they happen."""
        L = self.level
        if L is None or L.wide_said:
            return
        limit = max(40, int(1.5 * self.level_presses[-1])) if self.level_presses else 60
        if L.presses < limit:
            return
        L.wide_said = True
        if self.cards:
            want = self._merge([s for s, _ in self._won_kinds() if not L.card.n[s]])
            if want:
                self._pending.append(f"[Frame facts] This level has taken {L.presses} presses (the last one took "
                                     f"{self.level_presses[-1]}). Kinds of event that came with earlier wins but have not "
                                     f"happened yet on this level: " + "; ".join(_WORDS[s] for s in want[:3]) + ".")
                return
        top = _lines_top(self.gid)
        if top:
            sl, k, n, lift, share = top
            self._pending.append(f"[Frame facts] In the other games being played right now, {k} of {n} winning presses "
                                 f"involved {_WORDS[sl]} (ordinary presses: {share:.0%}).")

    def _core_notes(self, f0, f1, D, kind, action, ev=None):
        L = self.level
        if L is None or not D.any():
            return
        ev = ev or {}
        ge = ev.get("ge") if "ge" in ev else self._glyph_equal(f0, f1, D)
        if ge and len(L.equal_said) < 3:
            t, s, c, (k1, k2) = ge
            kk = (t["box"], s["box"], c)
            if kk not in L.equal_said:
                L.equal_said.add(kk)
                a, b = t["box"], s["box"]
                size = "" if k1 == k2 else f", drawn {k1}x vs {k2}x"
                self._pending.append(f"[Frame facts] After {action}, the {_cname(c)} pattern inside the thing at rows {a[0]}-{a[1] - 1}, "
                                     f"cols {a[2]}-{a[3] - 1} has the same shape as the {_cname(c)} pattern inside the still thing at "
                                     f"rows {b[0]}-{b[1] - 1}, cols {b[2]}-{b[3] - 1} (same way up{size}).")
                return
        me = ev.get("me") if "me" in ev else self._made_equal(f0, f1, D)
        if me and len(L.equal_said) < 3:
            t, s = me
            k = (t["box"], s["box"])
            if k not in L.equal_said:
                L.equal_said.add(k)
                a, b = t["box"], s["box"]
                self._pending.append(f"[Frame facts] After {action}, the thing at rows {a[0]}-{a[1] - 1}, cols {a[2]}-{a[3] - 1} "
                                     f"has the same picture as the still thing at rows {b[0]}-{b[1] - 1}, cols {b[2]}-{b[3] - 1} "
                                     f"(same colours, same way up).")
        if kind == "moved" and self.bind and len(L.arrive_said) < 3:
            bind = {c for c in self.bind if int((f1 == c).sum()) <= 200}     # not walls and floors
            for t in (ev.get("arr") if "arr" in ev else self._arrived(f0, f1, D)):
                if set(t["cols"]) & bind and t["box"] not in L.arrive_said:
                    L.arrive_said.add(t["box"])
                    y0, y1, x0, x1 = t["box"]
                    self._pending.append(f"[Frame facts] {action} brought the moved thing next to a still "
                                         f"{'/'.join(_cname(c) for c in t['cols'][:2])} thing (rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1}), "
                                         f"a colour of the last win's form.")
                    break

    def notes(self):
        """the notes for the next turn message (deduplicated within the level), at most max_lines"""
        try:
            out = []
            seen = self.level.notes_sent if self.level is not None else set()
            keep_v8 = [l for l in self._pending if "Step bar:" in l or "has the same shape as the" in l]
            for line in list(self._core_pending) + keep_v8:
                if line in seen or line in out:
                    continue
                out.append(line)
            send, keep = out[: self.max_lines], out[self.max_lines:]
            for line in send:
                seen.add(line)
            self._core_pending = [l for l in keep if l not in keep_v8][:8]   # said on the next turn instead of lost
            self._pending = [l for l in keep if l in keep_v8][:3]
            return send
        except Exception:
            self._pending = []; self._core_pending = []
            return []

    def key_digest(self):
        """what each key did so far on this level, one line (for a pinned log or on request)"""
        try:
            if self.level is None:
                return ""
            parts = [self._key_summary(a) for a in sorted(self.level.key_stats)]
            return "[Frame facts] Keys this level: " + "; ".join(p for p in parts if p) + "."
        except Exception:
            return ""

    # ------------------------------------------------------------------ small helpers
    @staticmethod
    def _action_kind(action, f0):
        """keys by name; clicks by the colour of the thing clicked (a click's place changes every time)"""
        m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", action)
        if m:
            r, c = int(m.group(1)), int(m.group(2))
            if 0 <= r < f0.shape[0] and 0 <= c < f0.shape[1]:
                return f"MOUSE on {_cname(f0[r, c])}"
            return "MOUSE"
        return action.split("(")[0].strip() or action
    def _usual_frames(self):
        if not self.fr_total:
            return 1
        half = self.fr_total / 2.0; acc = 0
        for n in sorted(self.fr_counts):
            acc += self.fr_counts[n]
            if acc >= half:
                return n
        return 1

    def _key_summary(self, a):
        L = self.level
        st = L.key_stats.get(a) if L is not None else None
        if not st:
            return ""
        n = sum(st.values())
        top, c = st.most_common(1)[0]
        s = f"{a} {top} {c}/{n}"
        sh = L.key_shift.get(a)
        if sh:
            (dy, dx), m = sh.most_common(1)[0]
            s += f" (shift {dy:+d},{dx:+d} {m}x)"
        kp = L.key_places.get(a)
        if kp and top != "moved":
            np_, m = kp.most_common(1)[0]
            if np_ >= 2:
                s += f" ({np_}{'+' if np_ >= 9 else ''} places per press {m}x)"
        return s

    @staticmethod
    def _words(kind, shift):
        if kind == "moved" and shift is not None:
            dy, dx = shift
            return f"moved something by {dy:+d} rows, {dx:+d} cols"
        if kind == "nothing":
            return "changed nothing on the board"
        return kind

# ==================================================================================== v10: the core planes (Oct 28)
# What Mika's core learned on ls20 (Oct 27-28), as notes for the model. Fewer and sharper than v8: the v8 notes are
# computed but only the step bar and the made-equal glyph are said; the rest of what is said comes from these planes.
#
#   operators   touching a thing changes a small far picture (an indicator, e.g. a key in a corner): the change is
#               read as a law of that thing (a quarter turn, a recolour map, a reshape map), kept per thing
#   equation    when a still thing holds a glyph the indicator could become: the touches that make them equal,
#               solved from the laws seen so far
#   tracks      things that move by themselves, one step each time the mover moves, on a fixed loop: where they
#               will be after the next move
#   pushes      a move that did not land one step on (a spring, a teleport), and the law behind it when it repeats
_DIRS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
_HEX = "0123456789abcdef"


def _ground(f):
    """the floor and the walls: every colour covering an eighth of the board or more (ls20: walls and floor both)"""
    inner = f[2:-2, 2:-2]
    vals, cnt = np.unique(inner, return_counts=True)
    out = {int(v) for v, c in zip(vals, cnt) if c >= inner.size / 8}
    return frozenset(out or {int(vals[cnt.argmax()])})


def _look_at(f, box, ground, walls=()):
    """what a thing looks like: the patch of non-floor cells joined to it (its other colours included)"""
    H, W = f.shape
    y0, y1, x0, x1 = box
    g = (set(ground) if isinstance(ground, (set, frozenset)) else {int(ground)}) | set(walls)
    seed = [(y, x) for y in range(max(0, y0), min(H, y1)) for x in range(max(0, x0), min(W, x1)) if int(f[y, x]) not in g]
    if not seed:
        return None, None
    comp = set(seed); st = list(seed)
    while st:
        y, x = st.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (y + dy, x + dx)
                if q in comp or not (0 <= q[0] < H and 0 <= q[1] < W):
                    continue
                if q[0] < y0 - 3 or q[0] >= y1 + 3 or q[1] < x0 - 3 or q[1] >= x1 + 3:
                    continue
                if int(f[q]) in g:
                    continue
                comp.add(q); st.append(q)
    if len(comp) > 64:
        return None, None
    ys = [c[0] for c in comp]; xs = [c[1] for c in comp]
    rows = []
    for y in range(min(ys), max(ys) + 1):
        rows.append("".join(_HEX[int(f[y, x])] if (y, x) in comp and 0 <= int(f[y, x]) < 16 else "." for x in range(min(xs), max(xs) + 1)))
    return "/".join(rows), (min(ys), min(xs))


def _look_name(lk):
    """how a look is named in a note: its picture when small, otherwise its size and colours"""
    rows = str(lk).split("/")
    h, w = len(rows), max(len(r) for r in rows)
    if h <= 5 and w <= 6:
        return f"the thing that looks like {lk}"
    cnt = Counter(ch for r in rows for ch in r if ch != ".")
    cols = [_NAMES[_HEX.index(ch)] for ch, _ in cnt.most_common(2) if ch in _HEX]
    return f"the {h}x{w} {' and '.join(cols) or 'coloured'} thing"


def _find_look(f, look):
    rows = look.split("/"); h, w = len(rows), len(rows[0]); H, W = f.shape
    if h > H or w > W:
        return []
    m = np.ones((H - h + 1, W - w + 1), bool)
    for dy, r in enumerate(rows):
        for dx, c in enumerate(r):
            if c != ".":
                m &= (f[dy:H - h + 1 + dy, dx:W - w + 1 + dx] == int(c, 16))
    ys, xs = np.nonzero(m)
    return list(zip(ys.tolist(), xs.tolist()))


def _look_cells(look, pos):
    return {(pos[0] + dy, pos[1] + dx) for dy, r in enumerate(look.split("/")) for dx, c in enumerate(r) if c != "."}


def _look_box(look, pos):
    rows = look.split("/")
    return (pos[0], pos[0] + len(rows), pos[1], pos[1] + len(rows[0]))


def _learn_lap(obs, max_p=24):
    if len({tuple(v) for v in obs.values()}) < 2:
        return None
    top = max(obs)
    for P in range(2, max_p + 1):
        if top + 1 < 2 * P:
            break
        lap = [None] * P; ok = True
        for t, v in obs.items():
            v = tuple(v)
            if lap[t % P] is None:
                lap[t % P] = v
            elif lap[t % P] != v:
                ok = False; break
        if ok and all(x is not None for x in lap):
            return lap
    return None


def _shrink_mask(m):
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    q = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    k = MikaLayer._scale(q)
    return q[::k, ::k].astype(np.int8)


def _state_of(sub):
    """an indicator's state: (colour, shape) when one colour stands on its background, else the whole picture"""
    vals, cnt = np.unique(sub, return_counts=True)
    bg = int(vals[cnt.argmax()])
    cols = [int(v) for v in vals if int(v) != bg]
    if len(cols) == 1:
        sh = _shrink_mask(sub == cols[0])
        if sh is not None and sh.size >= 4:
            return ("one", cols[0], sh)
    return ("pic", None, np.array(sub, dtype=np.int16))


def _st_key(s):
    return (s[0], s[1], s[2].shape, s[2].tobytes())


def _shape_txt(sh):
    return "/".join("".join("#" if v else "." for v in row) for row in sh)


def _transform(a, b):
    """('R', k) a turn clockwise by k quarters, ('F',) a mirror, ('C', {ca: cb}) a recolour, ('S', {shape: shape}),
    or ('M', {state: state}) for anything else"""
    if a[0] == "one" and b[0] == "one":
        if a[1] == b[1]:
            for k in (1, 2, 3):
                r = np.rot90(a[2], -k)
                if r.shape == b[2].shape and np.array_equal(r, b[2]):
                    return ("R", k)
            for t in (np.fliplr(a[2]), np.flipud(a[2])):
                if t.shape == b[2].shape and np.array_equal(t, b[2]):
                    return ("F",)
            if a[2].shape == b[2].shape and np.array_equal(a[2], b[2]):
                return None                           # same picture, only moved within the box: not a law
            return ("S", {_shape_txt(a[2]): _shape_txt(b[2])})
        if a[2].shape == b[2].shape and np.array_equal(a[2], b[2]):
            return ("C", {a[1]: b[1]})
    return ("M", {_st_key(a): _st_key(b)})


def _merge_law(old, new):
    """the law grown by one more sighting; None when they disagree"""
    if old is None:
        return new
    if old[0] != new[0]:
        return None
    if old[0] == "R":
        return old if old[1] == new[1] else None
    if old[0] == "F":
        return old
    m = dict(old[1])
    for a, b in new[1].items():
        if a in m and m[a] != b:
            return None
        m[a] = b
    return (old[0], m)


def _apply(law, s):
    if s[0] != "one":
        if law[0] == "M":
            t = law[1].get(_st_key(s))
            return None if t is None else ("key", t)
        return None
    if law[0] == "R":
        return ("one", s[1], np.rot90(s[2], -law[1]))
    if law[0] == "F":
        return None
    if law[0] == "C":
        c = law[1].get(s[1])
        return None if c is None else ("one", c, s[2])
    if law[0] == "S":
        t = law[1].get(_shape_txt(s[2]))
        if t is None:
            return None
        return ("one", s[1], np.array([[1 if ch == "#" else 0 for ch in row] for row in t.split("/")], dtype=np.int8))
    return None


def _same_state(a, b):
    return a[0] == "one" and b[0] == "one" and a[1] == b[1] and a[2].shape == b[2].shape and np.array_equal(a[2], b[2])


def _solve(start, target, laws, max_depth=10):
    """the shortest sequence of touches (thing keys) that takes the indicator from start to target"""
    if _same_state(start, target):
        return []
    seen = {_st_key(start)}; frontier = [(start, [])]
    for _ in range(max_depth):
        nxt = []
        for s, path in frontier:
            for k, law in laws.items():
                t = _apply(law, s)
                if t is None or t[0] != "one":
                    continue
                if _same_state(t, target):
                    return path + [k]
                kk = _st_key(t)
                if kk in seen:
                    continue
                seen.add(kk); nxt.append((t, path + [k]))
        frontier = nxt
        if not frontier:
            break
    return None


def _law_words(law):
    if law[0] == "R":
        return {1: "turns it a quarter turn clockwise", 2: "turns it half a turn", 3: "turns it a quarter turn anticlockwise"}[law[1]]
    if law[0] == "F":
        return "mirrors it"
    if law[0] == "C":
        m = law[1]
        start = next(iter(m)); chain = [start]; cur = start
        while cur in m and m[cur] not in chain and len(chain) < 12:
            cur = m[cur]; chain.append(cur)
        cyc = cur in m and m[cur] == start
        txt = " -> ".join(_CHARS[c] if 0 <= c < 16 else str(c) for c in chain) + (f" -> {_CHARS[start]}" if cyc and 0 <= start < 16 else "")
        rest = [f"{_CHARS[a]}->{_CHARS[b]}" for a, b in m.items() if a not in chain]
        return "recolours it " + txt + (" (a cycle)" if cyc else "") + ("; also " + ", ".join(rest) if rest else "")
    if law[0] == "S":
        pairs = list(law[1].items())[:3]
        return "reshapes it (" + "; ".join(f"{a} -> {b}" for a, b in pairs) + (f"; {len(law[1]) - 3} more" if len(law[1]) > 3 else "") + ")"
    return "changes it"


class _Core10:
    def __init__(self):
        self.tick = 0
        self.start = None                 # the mover's place at the level's start
        self.mover = None                 # the mover's look
        self.mpos = None                  # its top-left now
        self.step = defaultdict(Counter)  # action -> Counter of (dy, dx) of the mover
        self.cands = None                 # looks that may move by themselves
        self.obs = defaultdict(dict)      # look -> {tick: pos}
        self.laps = {}                    # look -> lap
        self.lap_said = set()
        self.jumps = []                   # (pos0, action, pos1, intended)
        self.push = defaultdict(lambda: [0, 0])
        self.push_said = set(); self.jump_said = 0
        self.ind = []                     # indicator boxes (y0, y1, x0, x1)
        self.laws = {}                    # (indicator index, thing key) -> law
        self.law_where = {}               # thing key -> (box, look)
        self.law_said = {}
        self.law_n = {}                   # sightings that agreed with the law
        self.law_conf = set()             # laws already said with 'Each time'
        self.eq_said = set()
        self.n_said = 0


def _c10_reset(self):
    C = getattr(self, "c10", None)
    if C is None:
        return
    C.tick = 0


def _c10_start(self, f):
    old = getattr(self, "c10", None)
    self.c10 = _Core10()
    if old is not None:
        self.c10.mover = old.mover                 # the mover usually looks the same on the next level
    try:
        g = _ground(f)
        ts, _bg = self._things(f)
        looks = Counter()
        for t in ts:
            if t["n"] > 60 or t["plain"]:
                continue
            lk, _p = _look_at(f, t["box"], g)
            if lk and 3 <= sum(ch != "." for ch in lk) <= 49:
                looks[lk] += 1
        self.c10.cands = [lk for lk, k in looks.items() if len(_find_look(f, lk)) == 1][:40]
    except Exception:
        self.c10.cands = []


def _c10_say(self, line, cap=10):
    C = self.c10
    if C.n_said >= cap:
        return
    C.n_said += 1
    self._core_pending.append(line)


def _c10_observe(self, f0, f1, action, D, kind, shift):
    C = getattr(self, "c10", None)
    if C is None:
        _c10_start(self, f0); C = self.c10
    act = str(action).split("(")[0].strip().upper()
    g = _ground(f0)
    # ---- the mover: found by its look; learned from the first press that moved something
    p0 = p1 = None
    if C.mover:
        h0, h1 = _find_look(f0, C.mover), _find_look(f1, C.mover)
        if len(h0) == 1 and len(h1) == 1:
            p0, p1 = h0[0], h1[0]
    if (p0 is None or p1 is None) and kind == "moved" and shift is not None and D.any():
        dy, dx = shift
        N = np.zeros(D.shape, bool)
        ys, xs = np.nonzero(D)
        for y, x in zip(ys, xs):
            yy, xx = y - dy, x - dx
            if 0 <= yy < 64 and 0 <= xx < 64 and f1[y, x] == f0[yy, xx] and int(f1[y, x]) not in g:
                N[y, x] = True
        if N.sum() >= 3:
            lk, pos = _look_at(f1, _box(N), g)
            if lk and len(_find_look(f1, lk)) == 1 and len(_find_look(f0, lk)) == 1:
                C.mover = lk; p1 = pos; p0 = _find_look(f0, lk)[0]
    moved = p0 is not None and p1 is not None and p0 != p1
    if C.start is None and p0 is not None and C.tick == 0:
        C.start = p0
    died = False
    away = _jn_away(self, f1)                            # presses since the board was last at the level's start
    undo = "UNDO" in act or "ACTION7" in act
    if moved and C.start is not None and p1 == C.start and abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) > 12:
        C.tick = 0                                       # back at the start from far away: a death or a reset, not a move
        moved = False; died = not undo and away >= 3
    elif not undo and away >= 3 and _jn_is_reset(self, f0, f1):
        normal = moved and act in _DIRS and C.step[act] and (p1[0] - p0[0], p1[1] - p0[1]) == _usual_step(C, act)[0]
        if not normal and _jn_death(self, f0, f1, act, p0):  # back at the start, and a second sign agrees
            C.tick = 0; moved = False; died = True
            undo = True                                    # already said
    if died and not undo:
        died = _jn_death(self, f0, f1, act, p0)          # a death only when a second sign agrees (a pip, the bar)
    dmv = None
    if moved:
        C.tick += 1
        d = (p1[0] - p0[0], p1[1] - p0[1]); dmv = d
        C.step[act][d] += 1
        _c10_pushes(self, f0, f1, act, p0, p1, d)
        _jn_swapped(self, act)
    if not died and p1 is not None:
        _jn_end(self, p0, p1)
    if not died and D.any():
        _jn_click(self, f0, f1, action, D, g)
    C.mpos = p1
    # ---- things that move by themselves, clocked by the mover's moves
    C.travel = set()
    if C.cands:
        for lk in C.cands:
            if lk == C.mover:
                continue
            h = _find_look(f1, lk)
            if len(h) == 1 and lk not in C.laps:
                C.obs[lk].setdefault(C.tick, h[0])
            h0 = _find_look(f0, lk) if len(h) == 1 else []
            if len(h) == 1 and len(h0) == 1 and h0[0] != h[0]:
                C.travel |= _look_cells(lk, h0[0]) | _look_cells(lk, h[0])
                if not died:
                    _jn_selfmove(self, lk, h0[0], h[0], act, dmv, action)
        if moved and C.tick % 4 == 0 and C.tick >= 8:
            for lk, ob in list(C.obs.items()):
                if lk in C.laps:
                    continue
                lap = _learn_lap(ob)
                if lap:
                    C.laps[lk] = lap
        for lk, lap in C.laps.items():
            if lk in C.lap_said:
                continue
            C.lap_said.add(lk)
            P = len(lap); now = lap[C.tick % P]; nxt = lap[(C.tick + 1) % P]
            rs = [p[0] for p in lap]; cs = [p[1] for p in lap]
            h, w = len(lk.split("/")), len(lk.split("/")[0])
            _c10_say(self, f"[Frame facts] {_look_name(lk)[0].upper() + _look_name(lk)[1:]} (now at rows {now[0]}-{now[0] + h - 1}, cols {now[1]}-{now[1] + w - 1}) "
                           f"moves by itself one step each time you move, on a fixed loop of {P} places within rows {min(rs)}-{max(rs) + h - 1}, "
                           f"cols {min(cs)}-{max(cs) + w - 1}; after your next move it will be at rows {nxt[0]}-{nxt[0] + h - 1}, cols {nxt[1]}-{nxt[1] + w - 1}. "
                           f"Touching it counts when your mover overlaps it after a move.")
            break
    # ---- operators: a small far picture changed; what was touched
    if D.any():
        _c10_operators(self, f0, f1, action, act, D, g, p1)


def _c10_pushes(self, f0, f1, act, p0, p1, d):
    C = self.c10
    if act not in _DIRS or not C.step[act]:
        return
    usual, k = _usual_step(C, act)
    if k < 3 or d == usual:
        return
    intended = (p0[0] + usual[0], p0[1] + usual[1])
    C.jumps.append((p0, act, p1, intended))
    rows = C.mover.split("/"); h, w = len(rows), len(rows[0])
    # a thin line of one colour along a face of the intended square, pushing straight away from it
    y0, x0 = intended; y1, x1 = y0 + h, x0 + w
    faces = []
    if y0 - 1 >= 0: faces.append(((1, 0), f0[y0 - 1, x0:x1]))
    if y1 < 64: faces.append(((-1, 0), f0[y1, x0:x1]))
    if x0 - 1 >= 0: faces.append(((0, 1), f0[y0:y1, x0 - 1]))
    if x1 < 64: faces.append(((0, -1), f0[y0:y1, x1]))
    dn = (int(np.sign(p1[0] - intended[0])), int(np.sign(p1[1] - intended[1])))
    found = None
    for push, line in faces:
        vals, cnt = np.unique(line, return_counts=True)
        for v, c in zip(vals, cnt):
            if c >= max(3, 0.6 * len(line)) and int(v) not in _ground(f0):
                if push == dn:
                    found = int(v)
    if found is not None:
        C.push[found][0] += 1
        if C.push[found][0] >= 2 and found not in C.push_said:
            C.push_said.add(found)
            _c10_say(self, f"[Frame facts] Thin {_cname(found)} lines push: {C.push[found][0]} times, a move that would end next to one "
                           f"threw the mover straight away from the line until it hit something. They can be used as shortcuts.")
            return
    if C.jump_said < 2:
        C.jump_said += 1
        J = _jn(self)
        lead = ""
        if ("game", "dirs") not in J["said"]:
            J["said"].add(("game", "dirs"))
            lead = ("Each direction button normally moves the body one step; this press didn't, so something on the board "
                    "did it, and it will do it again. ")
        _c10_say(self, f"[Frame facts] {lead}{act} from rows {p0[0]}-{p0[0] + h - 1}, cols {p0[1]}-{p0[1] + w - 1} did not move one step "
                       f"({usual[0]:+d},{usual[1]:+d} usually): the mover ended at rows {p1[0]}-{p1[0] + h - 1}, cols {p1[1]}-{p1[1] + w - 1}.")


def _c10_operators(self, f0, f1, action, act, D, g, p1):
    C = self.c10
    far = self._far(D)
    if not far:
        return
    F = None
    trav = getattr(C, "travel", set())
    if C.mover and p1 is not None:
        trav = trav | _look_cells(C.mover, p1)
    for F_ in far:
        y0, y1, x0, x1 = _box(F_)
        if not (y0 >= 3 and y1 <= 61 and x0 >= 3 and x1 <= 61):    # not the border, where step bars and clocks live
            continue
        if trav and any((y, x) in trav for y, x in zip(*np.nonzero(F_))):
            continue                                                 # a thing travelling, not a picture changing
        F = F_; break
    if F is None:
        return
    y0, y1, x0, x1 = _box(F)
    R = (max(0, y0 - 2), min(64, y1 + 2), max(0, x0 - 2), min(64, x1 + 2))
    try:                                                 # the whole indicator: the small thing the change belongs to
        ts, _ = self._things(f1)
        own = [t for t in ts if (t["mask"] & F).any() and t["n"] <= 120]
        if own:
            t = max(own, key=lambda t: t["n"])
            b = t["box"]
            if (b[1] - b[0]) <= 16 and (b[3] - b[2]) <= 16:
                R = b
    except Exception:
        pass
    idx = None
    for i, b in enumerate(C.ind):
        if not (R[1] <= b[0] or b[1] <= R[0] or R[3] <= b[2] or b[3] <= R[2]):
            C.ind[i] = (min(b[0], R[0]), max(b[1], R[1]), min(b[2], R[2]), max(b[3], R[3])); idx = i; break
    if idx is None:
        C.ind.append(R); idx = len(C.ind) - 1
    R = C.ind[idx]
    a = _state_of(f0[R[0]:R[1], R[2]:R[3]]); b = _state_of(f1[R[0]:R[1], R[2]:R[3]])
    # what was touched: the clicked thing, a moving thing over the mover, or what the mover stepped onto
    key = where = None
    m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
    if m:
        r, c = int(m.group(1)), int(m.group(2))
        ts, _ = self._things(f0)
        own = [t for t in ts if t["mask"][r, c]] if 0 <= r < 64 and 0 <= c < 64 else []
        if own:
            t = min(own, key=lambda t: t["n"]); lk, _p = _look_at(f0, t["box"], g)
            key, where = ("click", lk or _cname(f0[r, c])), (_look_box(lk, _p) if lk else t["box"])
    elif C.mover and p1 is not None:
        cells = _look_cells(C.mover, p1)
        for lk, lap in C.laps.items():
            pos = lap[C.tick % len(lap)]
            if cells & _look_cells(lk, pos):
                key, where = ("thing", lk), _look_box(lk, pos); break
        if key is None:
            ts, _ = self._things(f0)
            hit = [t for t in ts if t["n"] <= 60 and any(t["mask"][y, x] for y, x in cells if 0 <= y < 64 and 0 <= x < 64)]
            if hit:
                t = min(hit, key=lambda t: t["n"]); lk, _p = _look_at(f0, t["box"], g)
                if lk and len(lk.split("/")) <= 8 and len(lk.split("/")[0]) <= 8:     # something small enough to step onto
                    key, where = ("thing", lk), _look_box(lk, _p)
    if key is None:
        key, where = ("press", act), None
    tr = _transform(a, b)
    if tr is None:
        return
    lk_ = (idx, key)
    new = _merge_law(C.laws.get(lk_), tr)
    if new is None:                                   # two sightings disagree: keep the newest, say nothing yet
        C.laws[lk_] = tr; C.law_n[lk_] = 1; return
    grew = C.laws.get(lk_) != new
    C.laws[lk_] = new; C.law_where[key] = where
    C.law_n[lk_] = C.law_n.get(lk_, 0) + 1
    n_entries = len(new[1]) if new[0] in ("C", "S", "M") else 1
    said = C.law_said.get(lk_, 0)
    confirm = said > 0 and new[0] != "M" and C.law_n.get(lk_, 0) == 2 and lk_ not in C.law_conf
    if confirm or (grew and new[0] != "M" and (said == 0 or (n_entries >= said + 2) or (new[0] == "C" and "a cycle" in _law_words(new) and said < 99))):
        if C.law_n.get(lk_, 0) >= 2:
            C.law_conf.add(lk_)
        C.law_said[lk_] = 99 if (new[0] == "C" and "a cycle" in _law_words(new)) else n_entries
        who = "pressing " + act if key[0] == "press" else (("clicking" if key[0] == "click" else "stepping onto") +
                                                           " " + _look_name(key[1]) +
                                                           (f" (rows {where[0]}-{where[1] - 1}, cols {where[2]}-{where[3] - 1})" if where else ""))
        lead = "Each time" if C.law_n.get(lk_, 0) >= 2 else "Once so far"
        if lead == "Each time" and (R[1] - R[0]) <= 12 and (R[3] - R[2]) <= 12:
            _jn_display(self, R)
        _c10_say(self, f"[Frame facts] {lead}, {who} {_law_words(new)}: the small picture at rows {R[0]}-{R[1] - 1}, cols {R[2]}-{R[3] - 1}.")
        if key[0] in ("thing", "click") and where is not None:
            _jn_alike(self, f1, key[1], where, "stepped onto" if key[0] == "thing" else "clicked")
    _c10_equation(self, f1, idx, b)


def _c10_equation(self, f1, idx, cur):
    """the touches that make the indicator equal to a glyph standing in a still thing"""
    C = self.c10
    if cur[0] != "one" or len(C.eq_said) >= 2:
        return
    laws = {k: v for (i, k), v in C.laws.items() if i == idx and v[0] != "M"}
    if not laws:
        return
    R = C.ind[idx]
    for s in self._still():
        if not s["glyphs"]:
            continue
        if not (s["box"][1] <= R[0] or R[1] <= s["box"][0] or s["box"][3] <= R[2] or R[3] <= s["box"][2]):
            continue
        y0, y1, x0, x1 = s["box"]
        sub = np.where(s["mask"][y0:y1, x0:x1], f1[y0:y1, x0:x1], -1)
        for c in s["glyphs"]:
            q = _shrink_mask(sub == c)
            if q is None or q.shape != cur[2].shape:
                continue
            tgt = ("one", int(c), q)
            if _same_state(cur, tgt):
                continue
            seq = _solve(cur, tgt, laws)
            if not seq:
                continue
            k = (s["box"], int(c))
            if k in C.eq_said:
                return
            C.eq_said.add(k)
            cnt = Counter(seq); parts = []
            for kk, n in cnt.items():
                w = C.law_where.get(kk)
                nm = ("press " + kk[1]) if kk[0] == "press" else (_look_name(kk[1]) + (f" (at rows {w[0]}-{w[1] - 1}, cols {w[2]}-{w[3] - 1} when last touched)" if w else ""))
                parts.append(f"{nm} {n} time{'s' if n > 1 else ''}")
            _c10_say(self, f"[Frame facts] From what touching things did so far, the small picture at rows {R[0]}-{R[1] - 1}, cols {R[2]}-{R[3] - 1} "
                           f"would equal the {_cname(c)} glyph inside the still thing at rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1} after touching "
                           + "; ".join(parts) + " (the colour and the shape must both match).")
            return


# ====================================================================== v10c: Jonathan's notes (Oct 29)
# Each note starts black and white: it is said only when its "When" shows up in the frames, with the places filled in.
# Written by Jonathan (D:/planet/mika/notes_from_jonathan.md): something to solve before the end; one button per
# direction; moving things follow their own pattern; alike only when two properties match; a death is an unplanned
# reset and lives are pips. Suggested by Claude and kept: the bar is a budget; a small far picture is a display.

def _usual_step(C, act):
    """the button's usual step: the most common move the way it points; else the most common move"""
    cnt = C.step[act]
    named = Counter({d: n for d, n in cnt.items() if act in _DIRS and (int(np.sign(d[0])), int(np.sign(d[1]))) == _DIRS[act]})
    (u, k), = (named or cnt).most_common(1)
    return u, k


def _jn(self):
    J = getattr(self, "jn", None)
    if J is None:
        J = self.jn = {"said": set(), "deaths": Counter()}
    return J


def _jn_say(self, key, line, game=False, per_level=6):
    """say a note once (per level, or once per game), at most per_level notes per level"""
    J = _jn(self)
    lvl = self.level.idx if self.level is not None else -1
    k = ("game", key) if game else (lvl, key)
    if k in J["said"]:
        return False
    if sum(1 for (l, _) in J["said"] if l == lvl) >= per_level:
        return False
    J["said"].add(k)
    if game:
        J["said"].add((lvl, ("g",) + (key if isinstance(key, tuple) else (key,))))   # counts toward this level's budget
    self._core_pending.append(line)
    return True


def _rc(box):
    y0, y1, x0, x1 = box
    return f"rows {y0}-{y1 - 1}, cols {x0}-{x1 - 1}"


def _cap1(s):
    return s[:1].upper() + s[1:]


def _cells_mask(cells):
    m = np.zeros((64, 64), bool)
    for y, x in cells:
        if 0 <= y < 64 and 0 <= x < 64:
            m[y, x] = True
    return m


def _jn_end(self, p0, p1):
    """Something to solve before the end: the mover reached a still thing holding a glyph and the level did not end"""
    C = self.c10
    if not C.mover or p1 is None:
        return
    m1 = self._grow(_cells_mask(_look_cells(C.mover, p1)), 1)
    m0 = _cells_mask(_look_cells(C.mover, p0)) if p0 is not None else None
    for s in self._still():
        if not s["glyphs"] or s["n"] < 9:
            continue
        if m0 is not None and (s["mask"] & m0).any():
            continue                                   # where it stood before: itself, or what it stands on
        if (s["mask"] & m1).any():
            J = _jn(self)
            if ("game", "end_full") not in J["said"]:
                if _jn_say(self, ("end", s["box"]),
                           f"[Frame facts] The mover reached the thing holding a glyph at {_rc(s['box'])}, and the level did not "
                           f"end. There is at least one objective to solve before moving to the end: the end is usually locked "
                           f"until it is done. Look for what the end shows (a picture, a colour, a count) and what on the board "
                           f"can change to match it, then come back.", per_level=6):
                    J["said"].add(("game", "end_full"))
            else:
                _jn_say(self, ("end", s["box"]), f"[Frame facts] The mover reached the thing holding a glyph at {_rc(s['box'])}, "
                                                 f"and the level did not end: something is still to solve first.", per_level=6)
            return


def _jn_swapped(self, act):
    """One button per direction: a direction button whose usual step goes another way"""
    C = self.c10
    if act not in _DIRS or not C.step[act]:
        return
    total = sum(C.step[act].values())
    own = sum(n for d, n in C.step[act].items() if (int(np.sign(d[0])), int(np.sign(d[1]))) == _DIRS[act])
    (u, k), = C.step[act].most_common(1)
    if total < 4 or own > 0 or k < 3:
        return
    sg = (int(np.sign(u[0])), int(np.sign(u[1])))
    if sg != (0, 0) and sg != _DIRS[act]:
        _jn_say(self, ("swap", act), f"[Frame facts] {act} moves the body {u[0]:+d} rows, {u[1]:+d} cols ({k} times), not "
                                     f"{act.lower()}: on this level the direction buttons are swapped or turned.")


def _jn_selfmove(self, lk, h0, h1, act, d, action):
    """Moving things follow their own pattern: a thing moved that the press did not move"""
    C = self.c10
    if not C.mover or act not in _DIRS:
        return                                         # clicks, SPACE and UNDO can move things themselves
    dd = (h1[0] - h0[0], h1[1] - h0[1])
    if d is not None and dd == d:
        return                                         # moved with the mover: pushed or a second body
    if act in _DIRS and (int(np.sign(dd[0])), int(np.sign(dd[1]))) == _DIRS[act]:
        return                                         # moved the way the button points: the press moved it
    m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
    if m:
        r, c = int(m.group(1)), int(m.group(2))
        b0, b1 = _look_box(lk, h0), _look_box(lk, h1)
        if any(b[0] - 1 <= r < b[1] + 1 and b[2] - 1 <= c < b[3] + 1 for b in (b0, b1)):
            return                                     # it was clicked
    seen = getattr(C, "jn_self", None)
    if seen is None:
        seen = C.jn_self = Counter()
    seen[lk] += 1
    if seen[lk] < 2:
        return                                         # one sighting can be coincidence: wait for a second
    n = sum(1 for (l, key) in _jn(self)["said"] if l == (self.level.idx if self.level else -1) and isinstance(key, tuple) and key[0] == "self")
    if n >= 2:
        return
    _jn_say(self, ("self", lk), f"[Frame facts] {_cap1(_look_name(lk))} (now at {_rc(_look_box(lk, h1))}) moved by itself: the "
                                f"press did not move it. Moving things follow their own pattern (a loop, a back-and-forth, or "
                                f"chasing you): watch it for a few presses before planning around it.")


def _jn_alike(self, f, lk, where, verb):
    """Alike only when two properties match: other things with the same shape and the same colours as one that acted"""
    try:
        hits = _find_look(f, lk)
    except Exception:
        return
    kept = []
    for h in hits:
        b = _look_box(lk, h)
        if any(not (b[1] <= k[0] or k[1] <= b[0] or b[3] <= k[2] or k[3] <= b[2]) for k in kept):
            continue                                   # overlaps a copy already counted
        kept.append(b)
    others = [(b[0], b[2]) for b in kept if where is None or (b[0], b[2]) != (where[0], where[2])]
    if not others:
        return
    places = "; ".join(_rc(_look_box(lk, h)) for h in others[:3]) + (f"; and {len(others) - 3} more" if len(others) > 3 else "")
    _jn_say(self, ("alike", lk), f"[Frame facts] {len(others)} other thing{'s look' if len(others) > 1 else ' looks'} exactly like the "
                                 f"one {verb} (same shape and same colours): {places}. Things that share two properties are "
                                 f"probably related, so expect {'them' if len(others) > 1 else 'it'} to do the same.")


def _jn_click(self, f0, f1, action, D, g):
    """a click that changed the clicked thing: the alike note for its exact copies"""
    m = re.match(r"\s*MOUSE\(row=(\d+),\s*col=(\d+)\)", str(action))
    if not m or not D.any():
        return
    r, c = int(m.group(1)), int(m.group(2))
    if not (0 <= r < 64 and 0 <= c < 64):
        return
    ts, _ = self._things(f0)
    own = [t for t in ts if t["mask"][r, c] and t["n"] <= 60]
    if not own:
        return
    t = min(own, key=lambda t: t["n"])
    if not (t["mask"] & D).any():
        return
    lk, p = _look_at(f0, t["box"], g)
    if not lk or len(lk) > 120:
        return
    _jn_alike(self, f0, lk, _look_box(lk, p), "just clicked")


def _jn_pips(f0, f1, bar=None):
    """lives as small pips: a small thing (<= 3x3) that just went to one plain colour, with full copies beside it
    on the same rows or columns; returns (box, full pips left) or None"""
    D = f0 != f1
    if not D.any():
        return None
    lab, n = _label(D)
    if n > 60:
        return None
    for i in range(1, n + 1):
        mk = lab == i
        if mk.sum() > 9:
            continue
        y0, y1, x0, x1 = _box(mk)
        h, w = y1 - y0, x1 - x0
        if h > 3 or w > 3 or h * w < 2:
            continue
        if not (y0 <= 4 or y1 >= 60 or x0 <= 4 or x1 >= 60):
            continue                                   # lives are drawn at the edge of the screen
        if bar is not None and ((bar[0] == "row" and y0 <= bar[1] < y1) or (bar[0] == "col" and x0 <= bar[1] < x1)) \
                and bar[2] in set(np.unique(f0[y0:y1, x0:x1]).tolist()):
            continue                                   # a cell of the step bar, not a pip
        before = f0[y0:y1, x0:x1]; after = f1[y0:y1, x0:x1]
        if len(np.unique(after)) != 1 or (before == after).any():
            continue
        def count(F, band):
            k = 0; nxt = 0
            if band == "row":
                for x in range(0, 64 - w + 1):
                    if x >= nxt and np.array_equal(F[y0:y1, x:x + w], before):
                        k += 1; nxt = x + w + 1          # separate copies only
            else:
                for y in range(0, 64 - h + 1):
                    if y >= nxt and np.array_equal(F[y:y + h, x0:x1], before):
                        k += 1; nxt = y + h + 1
            return k
        for band in ("row", "col"):
            if 2 <= count(f0, band) <= 9:
                return (y0, y1, x0, x1), count(f1, band)
    return None


def _jn_death(self, f0, f1, act, p0):
    """A death is an unplanned reset: the board went back to the level's start without RESET. Said only when a second
    sign agrees (two properties): a life pip emptied, or the step bar had run out. Returns whether it was a death."""
    J = _jn(self)
    L = self.level
    lvl = L.idx if L else -1
    pip = _jn_pips(f0, f1, (self.bar[0], self.bar[1], int(self.bar_colour)) if self.bar is not None else None)
    bl = self._bar_cells(f0) if self.bar is not None else None
    bar_out = self.bar is not None and bl is not None and getattr(L, "bar_rate", None) is not None and \
        bl <= max(1, int(round(L.bar_rate)))
    if not pip and not bar_out:
        return False
    J["deaths"][lvl] += 1
    k = J["deaths"][lvl]
    if k > 3:
        return True
    parts = [f"[Frame facts] That was a death (an unplanned reset: the board went back to the level's start without RESET; "
             f"death {k} on this level)."]
    if pip:
        box, left = pip
        parts.append(f"Lives are the small pips: the one at {_rc(box)} just emptied, {left} full left.")
    if bar_out:
        parts.append("The step bar had run out: that bar counts your presses, and when it is empty you lose a life. "
                     "Plan routes that fit inside what is left.")
    elif act:
        parts.append(f"It came right after {act}" + (f" from rows {p0[0]}-{p0[0] + len(self.c10.mover.split('/')) - 1}, "
                                                    f"cols {p0[1]}-{p0[1] + len(self.c10.mover.split('/')[0]) - 1}" if p0 and self.c10 and self.c10.mover else "") + ".")
    _jn_say(self, ("death", k), " ".join(parts), per_level=9)
    return True


def _jn_away(self, f1):
    """how many presses the board had been away from the level's start before this one (then counts this one)"""
    L = self.level
    if L is None or L.start_frame is None or L.start_frame.shape != f1.shape or f1.shape != (64, 64):
        return 0
    prev = getattr(L, "jn_away", 0)
    near = int((f1[3:61, 3:61] != L.start_frame[3:61, 3:61]).sum()) <= 4
    L.jn_away = 0 if near else prev + 1
    return prev


def _jn_is_reset(self, f0, f1):
    """the board went back to this level's start screen (border rows and columns aside) from somewhere else"""
    L = self.level
    if L is None or L.start_frame is None or L.start_frame.shape != f1.shape or f1.shape != (64, 64):
        return False
    S = L.start_frame
    d1 = int((f1[3:61, 3:61] != S[3:61, 3:61]).sum())
    d0 = int((f0[3:61, 3:61] != S[3:61, 3:61]).sum())
    return d1 <= 4 and d0 >= 20


def _edge(side, i):
    if side == "row":
        return "top edge" if i < 32 else "bottom edge"
    return "left edge" if i < 32 else "right edge"


def _jn_bar(self, f1):
    """The bar is a budget: measured per life (a refill starts the count again), said in presses"""
    L = self.level
    if self.bar is None or L is None:
        return
    cells = self._bar_cells(f1)
    if cells is None:
        return
    last = getattr(L, "bar_last", None)
    L.bar_last = cells
    if last is None:
        return
    if cells > last:                                   # refilled: a new life or a reset
        L.bar_drops = []; L.bar_band = None
        return
    drops = getattr(L, "bar_drops", [])
    drops.append(last - cells)
    L.bar_drops = drops[-40:]
    if len(L.bar_drops) < 3 or sum(L.bar_drops) <= 0:
        return
    rate = sum(L.bar_drops) / len(L.bar_drops)
    L.bar_rate = rate
    left = int(cells / rate) if rate > 0 else None
    if left is None:
        return
    dr = L.bar_drops
    nzi = [j for j, d in enumerate(dr) if d > 0]
    gaps = [b - a for a, b in zip(nzi, nzi[1:])]
    regular = False
    if len(dr) >= 4 and len(set(dr)) == 1:
        per = f"{dr[0]} cell{'s' if dr[0] > 1 else ''} per press"; regular = True
    elif len(nzi) >= 3 and len(set(dr[j] for j in nzi)) == 1 and len(set(gaps)) == 1 and 2 <= gaps[0] <= 6:
        per = f"{dr[nzi[0]]} cell{'s' if dr[nzi[0]] > 1 else ''} every {gaps[0]} presses"; regular = True
        rate = dr[nzi[0]] / gaps[0]; left = int(cells / rate)
    else:
        per = f"about {rate:.1f} cells per press"
    if not regular and len(dr) < 8:
        return
    side, i = self.bar
    if regular and not getattr(L, "bar_intro", False):
        L.bar_intro = True
        _jn_say(self, "bar_intro", f"[Frame facts] Step bar: the {_cname(self.bar_colour)} line along the {_edge(side, i)} "
                                   f"({'row' if side == 'row' else 'col'} {i}) loses {per}; {cells} cells left = about {left} "
                                   f"presses before it runs out.", per_level=9)
        return
    if left <= 12:
        band = 12 if left > 6 else (6 if left > 3 else 3)
        if getattr(L, "bar_band", None) != band:
            L.bar_band = band
            self._core_pending.append(f"[Frame facts] Step bar: {left} presses left ({cells} cells, {per}).")


def _jn_display(self, R):
    """A small far picture is a display (said once per game, with the first law about it)"""
    _jn_say(self, "display", f"[Frame facts] The small picture at {_rc(R)} is a display: it shows state (like a key or a "
                             f"counter). Touching things changes it, so it can be set on purpose.", game=True)
