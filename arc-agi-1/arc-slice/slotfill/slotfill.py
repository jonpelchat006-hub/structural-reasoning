"""Slot filler for ARC tasks whose outputs only fill background cells.

Propose, verify, fall back (the polydisc v9 pattern):
  * propose: a cell rule `output colour = T[key(cell)]`, where key is a tuple of local/global features of the
    input grid at that background cell, learned as a lookup table from every train pair;
  * verify: the table must be consistent (one answer per key), reproduce every train output exactly, and
    cover every background cell of the test input (no unseen key);
  * rank: rules that also pass leave-one-out re-induction first, then the smallest table;
  * fall back: if no rule passes, say nothing (the rest of the solver keeps the task).

Two key modes:
  raw      keys and answers are absolute colours;
  abstract keys are canonically relabelled (first occurrence order; background and border kept fixed) and the
           answer may be "the colour in key slot j" instead of an absolute colour, so a rule learned on one
           palette transfers to another.
"""
import json, collections, itertools, sys
import numpy as np

BORDER = -1          # outside the grid
NONE = -2            # feature not defined

def bg_of(g):
    return collections.Counter(g.ravel().tolist()).most_common(1)[0][0]

# ---------------------------------------------------------------- features (each: grid, bg -> HxW array of ints)
DIRS8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

def padded(g, k=1):
    return np.pad(g, k, constant_values=BORDER)

def f_nb(g, bg, dr, dc):
    p = padded(g, 2); H, W = g.shape
    return p[2 + dr:2 + dr + H, 2 + dc:2 + dc + W]

def ray_first(g, bg, dr, dc):
    """colour of the first non-background cell along a ray (BORDER if none)."""
    H, W = g.shape; out = np.full((H, W), BORDER)
    rs = range(H) if dr <= 0 else range(H - 1, -1, -1)
    cs = range(W) if dc <= 0 else range(W - 1, -1, -1)
    for r in rs:
        for c in cs:
            r2, c2 = r + dr, c + dc
            if 0 <= r2 < H and 0 <= c2 < W:
                out[r, c] = g[r2, c2] if g[r2, c2] != bg else out[r2, c2]
    return out

def ray_dist(g, bg, dr, dc):
    H, W = g.shape; out = np.full((H, W), 99)
    rs = range(H) if dr <= 0 else range(H - 1, -1, -1)
    cs = range(W) if dc <= 0 else range(W - 1, -1, -1)
    for r in rs:
        for c in cs:
            r2, c2 = r + dr, c + dc
            if 0 <= r2 < H and 0 <= c2 < W:
                out[r, c] = 1 if g[r2, c2] != bg else min(99, out[r2, c2] + 1)
    return out

def between(g, bg, axis):
    """colour if the first non-bg cells on both sides along the axis agree, else NONE."""
    dirs = {"h": [(0, -1), (0, 1)], "v": [(-1, 0), (1, 0)], "d": [(-1, -1), (1, 1)], "a": [(-1, 1), (1, -1)]}[axis]
    a, b = ray_first(g, bg, *dirs[0]), ray_first(g, bg, *dirs[1])
    return np.where((a == b) & (a != BORDER), a, NONE)

def enclosed(g, bg):
    """1 if the cell's 4-connected background region does not touch the border."""
    H, W = g.shape; lab = -np.ones((H, W), int); out = np.zeros((H, W), int); k = 0
    for r in range(H):
        for c in range(W):
            if g[r, c] != bg or lab[r, c] >= 0: continue
            stack = [(r, c)]; lab[r, c] = k; cells = []; touch = False
            while stack:
                y, x = stack.pop(); cells.append((y, x))
                if y in (0, H - 1) or x in (0, W - 1): touch = True
                for dy, dx in DIRS8[:4]:
                    y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W and g[y2, x2] == bg and lab[y2, x2] < 0:
                        lab[y2, x2] = k; stack.append((y2, x2))
            for y, x in cells: out[y, x] = 0 if touch else 1
            k += 1
    return out

def region_rim(g, bg):
    """the single colour bounding the cell's background region (NONE if several or touches the border)."""
    H, W = g.shape; lab = -np.ones((H, W), int); out = np.full((H, W), NONE)
    for r in range(H):
        for c in range(W):
            if g[r, c] != bg or lab[r, c] >= 0: continue
            stack = [(r, c)]; lab[r, c] = 1; cells = []; rim = set(); touch = False
            while stack:
                y, x = stack.pop(); cells.append((y, x))
                if y in (0, H - 1) or x in (0, W - 1): touch = True
                for dy, dx in DIRS8[:4]:
                    y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W:
                        if g[y2, x2] == bg:
                            if lab[y2, x2] < 0: lab[y2, x2] = 1; stack.append((y2, x2))
                        else: rim.add(int(g[y2, x2]))
            v = rim.pop() if (len(rim) == 1 and not touch) else NONE
            for y, x in cells: out[y, x] = v
    return out

def region_size_rank(g, bg):
    """size of the cell's background region, capped (small holes vs big areas)."""
    H, W = g.shape; lab = -np.ones((H, W), int); out = np.zeros((H, W), int)
    for r in range(H):
        for c in range(W):
            if g[r, c] != bg or lab[r, c] >= 0: continue
            stack = [(r, c)]; lab[r, c] = 1; cells = []
            while stack:
                y, x = stack.pop(); cells.append((y, x))
                for dy, dx in DIRS8[:4]:
                    y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W and g[y2, x2] == bg and lab[y2, x2] < 0:
                        lab[y2, x2] = 1; stack.append((y2, x2))
            for y, x in cells: out[y, x] = min(len(cells), 9)
    return out

def region_geom(g, bg):
    """per background cell: region size, bbox height, bbox width, rectangle flag, touches border."""
    H, W = g.shape; lab = -np.ones((H, W), int)
    size, bh, bw, rect = (np.zeros((H, W), int) for _ in range(4))
    for r in range(H):
        for c in range(W):
            if g[r, c] != bg or lab[r, c] >= 0: continue
            stack = [(r, c)]; lab[r, c] = 1; cells = []
            while stack:
                y, x = stack.pop(); cells.append((y, x))
                for dy, dx in DIRS8[:4]:
                    y2, x2 = y + dy, x + dx
                    if 0 <= y2 < H and 0 <= x2 < W and g[y2, x2] == bg and lab[y2, x2] < 0:
                        lab[y2, x2] = 1; stack.append((y2, x2))
            ys = [y for y, _ in cells]; xs = [x for _, x in cells]
            h, w = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
            for y, x in cells:
                size[y, x], bh[y, x], bw[y, x], rect[y, x] = len(cells), h, w, int(h * w == len(cells))
    return size, bh, bw, rect

def sym_partner(g, bg, kind):
    f = {"h": lambda a: a[:, ::-1], "v": lambda a: a[::-1, :], "r2": lambda a: a[::-1, ::-1],
         "t": lambda a: a.T, "at": lambda a: a[::-1, ::-1].T}[kind]
    m = f(g)
    if m.shape != g.shape: return np.full(g.shape, NONE)
    return m

def period_fill(g, bg):
    """colour predicted by the smallest 2-D period consistent with all non-background cells."""
    H, W = g.shape
    for area in range(1, H * W + 1):
        for py in range(1, H + 1):
            if area % py: continue
            px = area // py
            if px > W: continue
            tile = {}
            ok = True
            for r in range(H):
                for c in range(W):
                    v = g[r, c]
                    if v == bg: continue
                    k = (r % py, c % px)
                    if tile.setdefault(k, v) != v: ok = False; break
                if not ok: break
            if ok and len(tile) == py * px and (py < H or px < W):
                out = np.empty((H, W), int)
                for r in range(H):
                    for c in range(W): out[r, c] = tile[(r % py, c % px)]
                return out
    return np.full((H, W), NONE)

def row_has(g, bg):
    """canonical code of the set of non-bg colours in the row and in the column."""
    H, W = g.shape
    rows = [tuple(sorted(set(g[r].tolist()) - {bg})) for r in range(H)]
    cols = [tuple(sorted(set(g[:, c].tolist()) - {bg})) for c in range(W)]
    return rows, cols

def nonbg_count8(g, bg):
    p = padded(g); H, W = g.shape; n = np.zeros((H, W), int)
    for dr, dc in DIRS8:
        s = p[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
        n += (s != bg) & (s != BORDER)
    return n

def nearest_colour(g, bg):
    """colour of the nearest non-bg cell (Chebyshev), NONE if tied between colours."""
    H, W = g.shape; pts = np.argwhere(g != bg); out = np.full((H, W), NONE)
    if len(pts) == 0: return out
    cols = g[pts[:, 0], pts[:, 1]]
    for r in range(H):
        for c in range(W):
            d = np.maximum(abs(pts[:, 0] - r), abs(pts[:, 1] - c)); m = d.min()
            cs = set(cols[d == m].tolist())
            out[r, c] = cs.pop() if len(cs) == 1 else NONE
    return out

# ---------------------------------------------------------------- feature registry
def build_features(g, bg):
    F = {}
    for i, (dr, dc) in enumerate(DIRS8):
        F[f"n{i}"] = f_nb(g, bg, dr, dc)
    for i, (dr, dc) in enumerate(DIRS8):
        F[f"ray{i}"] = ray_first(g, bg, dr, dc)
    for ax in "hvda":
        F[f"btw_{ax}"] = between(g, bg, ax)
    F["encl"] = enclosed(g, bg)
    F["rim"] = region_rim(g, bg)
    F["rsize"] = region_size_rank(g, bg)
    F["rsz"], F["rbh"], F["rbw"], F["rrect"] = region_geom(g, bg)
    for k in ["h", "v", "r2", "t", "at"]:
        F[f"sym_{k}"] = sym_partner(g, bg, k)
    F["period"] = period_fill(g, bg)
    F["cnt8"] = nonbg_count8(g, bg)
    F["near"] = nearest_colour(g, bg)
    H, W = g.shape
    rr, cc = np.indices((H, W))
    F["r2m"], F["c2m"] = rr % 2, cc % 2
    F["r3m"], F["c3m"] = rr % 3, cc % 3
    rows, cols = row_has(g, bg)
    code = {}
    F["rowset"] = np.array([[code.setdefault(rows[r], len(code)) for c in range(W)] for r in range(H)])
    F["colset"] = np.array([[code.setdefault(cols[c], len(code)) for c in range(W)] for r in range(H)])
    return F

COLOUR_FEATS = {f"n{i}" for i in range(8)} | {f"ray{i}" for i in range(8)} | {f"btw_{a}" for a in "hvda"} | \
    {"rim", "near", "period"} | {f"sym_{k}" for k in ["h", "v", "r2", "t", "at"]}

# feature groups tried as keys (each a tuple of feature names)
N4 = ("n0", "n1", "n2", "n3"); N8 = tuple(f"n{i}" for i in range(8))
R4 = ("ray0", "ray1", "ray2", "ray3"); R8 = tuple(f"ray{i}" for i in range(8))
BASE_GROUPS = [
    ("btw_h",), ("btw_v",), ("btw_h", "btw_v"), ("btw_d", "btw_a"), ("btw_h", "btw_v", "btw_d", "btw_a"),
    ("encl",), ("rim",), ("rim", "encl"), ("rsize",), ("rsize", "encl"), ("period",), ("near",),
    ("sym_h",), ("sym_v",), ("sym_r2",), ("sym_t",), ("sym_at",), ("sym_h", "sym_v"), ("sym_h", "sym_v", "sym_r2"),
    ("sym_t", "sym_at"), ("cnt8",), N4, N8, R4, R8, ("rowset",), ("colset",), ("rowset", "colset"),
    ("r2m", "c2m"), ("r3m", "c3m"),
    ("encl", "rsz"), ("encl", "rbh", "rbw"), ("encl", "rrect"), ("rim", "rsz"), ("rim", "rbh", "rbw"),
    ("encl", "rrect", "rbh", "rbw"),
]
def groups():
    G = list(BASE_GROUPS)
    small = [("btw_h",), ("btw_v",), ("encl",), ("rim",), ("near",), ("cnt8",), ("r2m",), ("c2m",), ("period",),
             ("rowset",), ("colset",), N4, R4, ("sym_h",), ("sym_v",), ("sym_r2",), ("sym_t",)]
    for a, b in itertools.combinations(small, 2):
        G.append(a + b)
    seen = set(); out = []
    for g in G:
        if g not in seen: seen.add(g); out.append(g)
    return out
GROUPS = groups()

# ---------------------------------------------------------------- learning
def keys_for(F, names, cells, bg, mode):
    """key tuples for the given cells; in abstract mode colours are relabelled by first occurrence."""
    cols = [F[n] for n in names]
    out = []
    for r, c in cells:
        v = tuple(int(a[r, c]) for a in cols)
        if mode == "raw":
            out.append((v, v))
        else:
            m = {bg: "B", BORDER: "E", NONE: "N"}; key = []
            for n, x in zip(names, v):
                if n in COLOUR_FEATS:
                    if x not in m: m[x] = len([k for k in m.values() if isinstance(k, int)])
                    key.append(m[x])
                else:
                    key.append(("v", x))
            out.append((tuple(key), v))
    return out

def explain(v, names, out_colour, bg, mode):
    """the set of explanations of an output colour given feature values v."""
    if mode == "raw": return {("abs", out_colour)}
    ex = set()
    if out_colour == bg: ex.add(("bg",))
    else: ex.add(("abs", out_colour))
    for j, (n, x) in enumerate(zip(names, v)):
        if n in COLOUR_FEATS and x == out_colour and x not in (BORDER, NONE): ex.add(("slot", j))
    return ex

def apply_ex(e, v, bg):
    if e[0] == "bg": return bg
    if e[0] == "abs": return e[1]
    return v[e[1]]

def pick(exs):
    """deterministic choice: background, then key slot (transfers), then absolute colour."""
    for kind in ("bg", "slot", "abs"):
        c = sorted(e for e in exs if e[0] == kind)
        if c: return c[0]
    return None

class Rule:
    def __init__(self, names, mode, table, dflt=False):
        self.names, self.mode, self.table, self.dflt = names, mode, table, dflt

def learn(pairs, names, mode, dflt=False):
    """pairs: list of (input, output, bg, features). Returns the rule or None if inconsistent."""
    table = {}
    for a, b, bg, F in pairs:
        cells = list(zip(*np.nonzero(a == bg)))
        for (key, v), (r, c) in zip(keys_for(F, names, cells, bg, mode), cells):
            ex = explain(v, names, int(b[r, c]), bg, mode)
            if key in table:
                table[key] &= ex
                if not table[key]: return None
            else:
                table[key] = set(ex)
    return Rule(names, mode, {k: pick(e) for k, e in table.items()}, dflt)

def predict(rule, a, bg, F):
    """None if some background cell has an unseen key (unless the rule defaults unseen keys to background)."""
    out = a.copy(); cells = list(zip(*np.nonzero(a == bg)))
    for (key, v), (r, c) in zip(keys_for(F, rule.names, cells, bg, rule.mode), cells):
        e = rule.table.get(key)
        if e is None:
            if rule.dflt: continue
            return None
        out[r, c] = apply_ex(e, v, bg)
    return out

def prep(task):
    P = []
    for p in task["train"]:
        a, b = np.array(p["input"]), np.array(p["output"])
        bg = bg_of(a); P.append((a, b, bg, build_features(a, bg)))
    T = []
    for p in task["test"]:
        a = np.array(p["input"]); bg = bg_of(a); T.append((a, bg, build_features(a, bg)))
    return P, T

def solve(task, max_attempts=2):
    """list (per test input) of up to max_attempts predicted grids, best first; [] if no rule passes."""
    P, T = prep(task)
    if not all(a.shape == b.shape for a, b, _, _ in P): return None
    cands = []
    for names in GROUPS:
        for mode in ("raw", "abstract"):
            for dflt in (False,):        # defaulting unseen keys to background added false positives
                rule = learn(P, names, mode, dflt)
                if rule is None: continue
                # verify: reproduce every train pair exactly
                if not all((pr := predict(rule, a, bg, F)) is not None and np.array_equal(pr, b) for a, b, bg, F in P):
                    continue
                preds = [predict(rule, a, bg, F) for a, bg, F in T]
                if any(p is None for p in preds): continue
                # leave-one-out re-induction (kernel-tier K2)
                loo = 0
                if len(P) >= 2:
                    for i in range(len(P)):
                        r2 = learn(P[:i] + P[i + 1:], names, mode, dflt)
                        a, b, bg, F = P[i]
                        if r2 is not None and (pr := predict(r2, a, bg, F)) is not None and np.array_equal(pr, b): loo += 1
                loo_ok = loo == len(P) and len(P) >= 2
                if dflt and not loo_ok: continue        # defaulting unseen keys needs the stronger check
                nontrivial = any(not np.array_equal(p, a) for p, (a, _, _) in zip(preds, T))
                cands.append((not loo_ok, dflt, -loo, len(rule.table), len(names), mode != "abstract",
                              names, mode, preds, nontrivial))
    if not cands: return []
    cands.sort(key=lambda x: x[:6])
    out = []; seen = []
    for c in cands:
        preds = c[8]
        if not c[9]: continue
        if any(all(np.array_equal(x, y) for x, y in zip(preds, s)) for s in seen): continue
        seen.append(preds); out.append((c[6], c[7] + ("+dflt" if c[1] else ""), c[0] is False, preds))
        if len(out) >= max_attempts: break
    return out

if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "train"
    tasks = json.load(open(f"{split}_tasks.json"))
    ids = sys.argv[2:] or list(tasks)
    for tid in ids:
        r = solve(tasks[tid])
        print(tid, r if r is None else [(n, m, l) for n, m, l, _ in r])
