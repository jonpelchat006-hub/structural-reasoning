"""Mika's evidence layer for a language-model harness (ARC-AGI-3).

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
                    used = self.bar_full - cells
                    if used > 0:
                        rate = used / max(1, L.presses)
                        left = cells / rate if rate > 0 else None
                        if L.last_cells is not None and cells < L.last_cells:
                            L.card.add("COUNT-", L.presses, "step bar")
                        if left is not None and (cells <= 0.25 * self.bar_full or left <= 12):
                            band = 12 if left > 6 else (6 if left > 3 else 3)
                            if getattr(L, "bar_band", None) != band:
                                L.bar_band = band
                                self._pending.append(f"[Frame facts] Step bar: about {int(left)} presses left at this rate.")
                    L.last_cells = cells
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
            for line in self._pending:
                if line in seen or line in out:
                    continue
                out.append(line)
            send, keep = out[: self.max_lines], out[self.max_lines:]
            for line in send:
                seen.add(line)
            self._pending = keep[:6]                 # said on the next turn instead of lost
            return send
        except Exception:
            self._pending = []
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
