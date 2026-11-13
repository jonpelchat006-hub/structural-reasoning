"""The core card: 12 slots = 6 rules x 2 sides, measured from frames only (what Mika's layer can see online).

  CONTROL  + moves         a same-colour thing turned up shifted (the press steered something)
           - blocked       a press that changed nothing on the board
  CONTACT  + makes/collects  a thing at the acting point changed colour, vanished or appeared (not the mover)
           - removes/kills the attempt ended (game over) or the level went back to its start picture
  MATCH    + match         the press made two things equal (same picture up to the 8 flips)
           - differ        the press made two equal things differ
  PLACE    + in/onto       the mover now touches a still thing it was not touching
           - out/apart     the mover stopped touching a still thing
  COUNT    + gather        something small changed far away (an indicator), or the last of a colour went
           - spend         the step bar / clock ticked (pixels that change on most presses of this level)
  ORDER    + target shown  the press made a thing equal to a thing that never changes on this level (a shown target)
           - undo/reverse  the board came back to a picture already seen on this level

For every level inside the school (36+ winning routes): replay the route; 150 random presses from the level
start as the arbitrary baseline (only those that changed something count; deaths reset the level).
Reports: which slots the winning press used (first frame after it, before the level-end animation); which the
route used; which the random exploration met (the boundaries); coverage (wins no + slot describes); slots that
always come together; lift of route presses over arbitrary presses per slot.

Also the matching-pair survey (the +C probe for a game with no notes): things on the level's START screen
that have a twin (exact / up to flips / up to flips and recolouring). Do route presses touch a twin more than
arbitrary presses that changed something?

  python coreslots.py trail/frontier_casebook.json trail/coreslots.md"""
import json, logging, os, sys, random, hashlib
from collections import defaultdict, Counter
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL); os.environ.pop("ONLY_RESET_LEVELS", None)
from relations import start, render  # noqa: E402
from arcengine import ActionInput, GameAction  # noqa: E402
from scipy.ndimage import label, binary_dilation  # noqa: E402
from mika3.explorer import components  # noqa: E402
from mika3.university import PUBLIC_DEPT  # noqa: E402

EIGHT = np.ones((3, 3), int)
LAST_BIND = {}
FOUR = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
SLOTS = ["CONTROL+", "CONTROL-", "CONTACT+", "CONTACT-", "MATCH+", "MATCH-", "PLACE+", "PLACE-",
         "COUNT+", "COUNT-", "ORDER+", "ORDER-"]
NAMES = {"CONTROL+": "moves", "CONTROL-": "blocked", "CONTACT+": "makes/collects", "CONTACT-": "removes/kills",
         "MATCH+": "match", "MATCH-": "differ", "PLACE+": "in/onto", "PLACE-": "out/apart",
         "COUNT+": "gather", "COUNT-": "spend", "ORDER+": "target shown", "ORDER-": "undo/reverse"}


def inner(f):
    return f[2:-2, 2:-2]


def d4(a):
    r = [a, np.rot90(a, 1), np.rot90(a, 2), np.rot90(a, 3)]
    return r + [np.fliplr(x) for x in r]


def renumber(a):
    flat = a.ravel()
    lut = {}
    out = np.full(a.shape, -1, dtype=np.int16)
    for i, v in enumerate(flat):
        if v >= 0 and v not in lut:
            lut[v] = len(lut)
    for v, k in lut.items():
        out[a == v] = k
    return out


def key(a):
    return hashlib.md5(a.astype(np.int16).tobytes() + bytes(a.shape)).hexdigest()[:12]


def _sig(f, m, y0, y1, x0, x1):
    p = f[y0:y1, x0:x1].astype(np.int16).copy()
    p[~m[y0:y1, x0:x1]] = -1
    return key(p), min(key(t) for t in d4(p)), min(key(renumber(t)) for t in d4(p))


def things(f):
    """things on a screen, at two grains:
      parts      same-colour regions (4-connected), 2..400 pixels (bigger ones are floors and walls)
      composites groups of parts (each at most 100 pixels) that touch (8-connected), up to 400 pixels
    Each: mask, bbox, signatures exact / d4 (up to flips) / rc (up to flips and recolouring)."""
    vals, cnt = np.unique(f, return_counts=True)
    bg = vals[cnt.argmax()]
    out = []
    small = np.zeros(f.shape, bool)
    for c in vals:
        if c == bg:
            continue
        lab, n = label(f == c, structure=FOUR)
        if n > 150:
            continue
        sizes = np.bincount(lab.ravel())
        for i in range(1, n + 1):
            s = int(sizes[i])
            if s < 2 or s > 400:
                continue
            m = lab == i
            ys, xs = np.nonzero(m)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            ex, dd, rc = _sig(f, m, y0, y1, x0, x1)
            out.append(dict(mask=m, bbox=(y0, y1, x0, x1), exact=ex, d4=dd, rc=rc, n=s, grain="part"))
            if s <= 100:
                small |= m
    lab, n = label(small, structure=EIGHT)
    for i in range(1, min(n, 200) + 1):
        m = lab == i
        s = int(m.sum())
        if s > 400:
            continue
        ys, xs = np.nonzero(m)
        if len(set(f[m].tolist())) < 2:
            continue                      # a single part: already counted
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        ex, dd, rc = _sig(f, m, y0, y1, x0, x1)
        out.append(dict(mask=m, bbox=(y0, y1, x0, x1), exact=ex, d4=dd, rc=rc, n=s, grain="composite"))
    return out, bg


def npairs(ts, sig):
    c = Counter(t[sig] for t in ts)
    return sum(k * (k - 1) // 2 for k in c.values())


def moved_comps(g0, g1, D):
    """same-colour components (4-connected, 2..300 px) touched by the change that turn up shifted (|d|<=16).
    Returns list of (mask_before, mask_after)."""
    out = []
    Dd = binary_dilation(D, iterations=1)
    vals = [int(c) for c in np.unique(g0[D])]
    for c in vals:
        l0, n0 = label(g0 == c, structure=FOUR)
        l1, n1 = label(g1 == c, structure=FOUR)
        if n0 > 80 or n1 > 80:
            continue
        after = []
        for j in range(1, n1 + 1):
            m1 = l1 == j
            if 2 <= m1.sum() <= 300 and (m1 & Dd).any():
                after.append(m1)
        for i in range(1, n0 + 1):
            m0 = l0 == i
            s = m0.sum()
            if not (2 <= s <= 300) or not (m0 & D).any():
                continue
            ys, xs = np.nonzero(m0)
            for m1 in after:
                if m1.sum() != s:
                    continue
                ys1, xs1 = np.nonzero(m1)
                dy, dx = ys1.min() - ys.min(), xs1.min() - xs.min()
                if (dy, dx) == (0, 0) or abs(dy) > 16 or abs(dx) > 16:
                    continue
                if np.array_equal(ys + dy, ys1) and np.array_equal(xs + dx, xs1):
                    out.append((m0, m1))
                    break
    return out


def slots_of(f0, f1, a, xy, state, start_pic, seen, clock, still_sigs):
    """the slots one press fired. f0/f1 full frames; seen = set of board keys this level; clock = bool mask
    (inner) of clock pixels; still_sigs = d4 signatures of things that never change on this level."""
    g0, g1 = inner(f0), inner(f1)
    S = set()
    B = {}
    LAST_BIND.clear()
    D = (g0 != g1)
    Dn = D & ~clock if clock is not None else D
    if str(state).endswith("GAME_OVER") or (start_pic is not None and np.array_equal(g1, start_pic) and D.any()):
        S.add("CONTACT-")
    if clock is not None and (D & clock).any():
        S.add("COUNT-")
    if not Dn.any():
        S.add("CONTROL-")
        return S, None
    bk = key(np.where(clock, 0, g1)) if clock is not None else key(g1)
    if bk in seen:
        S.add("ORDER-")
    mv = moved_comps(g0, g1, Dn)
    if mv:
        S.add("CONTROL+")
        B["CONTROL+"] = sorted({int(c) for m0, _ in mv for c in np.unique(g0[m0])})
    # acting point
    act = np.zeros(g0.shape, bool)
    if a == 6 and xy is not None:
        yy, xx = int(xy[1]) - 2, int(xy[0]) - 2
        if 0 <= yy < act.shape[0] and 0 <= xx < act.shape[1]:
            act[yy, xx] = True
    mover = np.zeros(g0.shape, bool)
    for m0, m1 in mv:
        act |= m0 | m1
        mover |= m0 | m1
    near = binary_dilation(act, iterations=2) if act.any() else np.zeros_like(act)
    # contact +: something at the acting point (not the mover) changed colour, vanished or appeared
    other = Dn & ~mover
    if near.any() and (other & near).any():
        S.add("CONTACT+")
        B["CONTACT+"] = sorted({int(c) for c in np.unique(g0[other & near])})
    elif a == 6 and xy is not None and Dn.any() and not mv:
        hit = Dn & binary_dilation(act, iterations=4)
        if hit.any():
            S.add("CONTACT+")
            B["CONTACT+"] = sorted({int(c) for c in np.unique(g0[hit])})
    # count +: a small change far from the acting point / main change, or the last of a colour went
    lab, n = label(Dn, structure=EIGHT)
    if n >= 1:
        sizes = [(int((lab == i).sum()), i) for i in range(1, n + 1)]
        if act.any():
            base = binary_dilation(act, iterations=6)
        else:
            base = binary_dilation(lab == max(sizes)[1], iterations=6)
        far = [i for s, i in sizes if s <= 36 and not (base & (lab == i)).any()]
        if far:
            S.add("COUNT+")
            F = np.isin(lab, far)
            B["COUNT+"] = sorted({int(c) for c in np.unique(g0[F])} | {int(c) for c in np.unique(g1[F])})
            B["COUNT+@"] = [int(v) for v in (np.nonzero(F)[0].min(), np.nonzero(F)[1].min())]
    c0, c1 = set(np.unique(g0).tolist()), set(np.unique(g1).tolist())
    if c0 - c1:
        S.add("COUNT+")
        B.setdefault("COUNT+", sorted(int(c) for c in (c0 - c1)))
    # match +/-: pairs of equal things (up to flips)
    t0, _ = things(g0)
    t1, _ = things(g1)
    p0, p1 = npairs(t0, "d4"), npairs(t1, "d4")
    if p1 > p0:
        S.add("MATCH+")
        cnt1 = Counter(t["d4"] for t in t1)
        B["MATCH+"] = sorted({int(c) for t in t1 if cnt1[t["d4"]] >= 2 and (t["mask"] & Dn).any() for c in np.unique(g1[t["mask"]])})
    if p1 < p0:
        S.add("MATCH-")
    # order +: a changed thing now equals a thing that never changes on this level (a shown target)
    if still_sigs:
        for t in t1:
            if (t["mask"] & Dn).any() and t["d4"] in still_sigs:
                # and it did not equal it before
                before = [u for u in t0 if (u["mask"] & t["mask"]).any()]
                if not any(u["d4"] == t["d4"] for u in before):
                    S.add("ORDER+")
                    B["ORDER+"] = sorted({int(c) for c in np.unique(g1[t["mask"]])})
                    break
    # place +/-: the mover touches a still thing it was not touching (or stopped touching one)
    if mv:
        still = np.zeros(g0.shape, bool)
        for t in t0:
            if not (t["mask"] & (D | mover)).any():
                still |= t["mask"]
        for m0, m1 in mv:
            b0 = binary_dilation(m0, iterations=1) & still
            b1 = binary_dilation(m1, iterations=1) & still
            lb, nb = label(still, structure=EIGHT)
            ids0 = set(np.unique(lb[b0]).tolist()) - {0}
            ids1 = set(np.unique(lb[b1]).tolist()) - {0}
            if ids1 - ids0:
                S.add("PLACE+")
                newm = np.isin(lb, list(ids1 - ids0))
                B.setdefault("PLACE+", [])
                B["PLACE+"] = sorted(set(B["PLACE+"]) | {int(c) for c in np.unique(g0[newm])})
            if ids0 - ids1:
                S.add("PLACE-")
    LAST_BIND.update(B)
    return S, bk


def press(g, a, xy):
    data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
    return g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)


def random_presses(e, rng, n=150):
    g = start(e); f = render(g); out = []
    acts = [a for a in g._available_actions if a != 0]
    for t in range(n):
        a = rng.choice(acts); xy = None
        if a == 6:
            comps = components(f); c = rng.choice(comps); xy = (c[2][1], c[2][0])
        r = press(g, a, xy)
        if r.levels_completed > 0 or str(r.state).endswith("WIN"):
            break
        f1 = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
        out.append((f, f1, a, xy, r.state))
        if str(r.state).endswith("GAME_OVER"):
            g.perform_action(ActionInput(id=GameAction.RESET), raw=True); f = render(g); continue
        f = f1
    return out


def level(key_, e, rng):
    # route
    g = start(e); f = render(g); s0 = f.copy(); route = []; won = False
    for a, xy, kind in e["route"]:
        r = press(g, a, xy)
        won = r.levels_completed > 0 or str(r.state).endswith("WIN")
        f1 = np.array(r.frame[0] if won else r.frame[-1], dtype=np.int16) if r.frame else f
        route.append((f, f1, a, xy, r.state))
        f = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
        if won:
            break
    if not won:
        return None
    rand = random_presses(e, rng)
    # clock: inner pixels that change on most presses that changed something (random + route)
    ch = [inner(x[0]) != inner(x[1]) for x in rand + route[:-1]]
    ch = [c for c in ch if c.any()]
    clock = np.zeros(inner(s0).shape, bool)
    if len(ch) >= 8:
        freq = np.mean(ch, axis=0)
        if (freq >= 0.6).sum() <= 200:
            clock |= freq >= 0.6
        # step bars: lines of the outer band (rows/cols 0-3 and 60-63 of the screen) that change by a few
        # pixels on at least 30% of presses (the changing pixel moves along the bar)
        H, W = clock.shape
        band = [i for i in range(H) if i < 2 or i >= H - 2]   # inner index; screen rows 2-3 and 60-61
        for i in band:
            hits = np.mean([(0 < c[i, :].sum() <= 3) for c in ch])
            if hits >= 0.3:
                clock[i, :] = True
            hits = np.mean([(0 < c[:, i].sum() <= 3) for c in ch])
            if hits >= 0.3:
                clock[:, i] = True
    # still things: things on the start screen that no route press changes
    t_start, _ = things(inner(s0))
    Dall = np.zeros(inner(s0).shape, bool)
    for x in route:
        Dall |= inner(x[0]) != inner(x[1])
    still_sigs = {t["d4"] for t in t_start if not (binary_dilation(t["mask"], iterations=1) & Dall).any()}
    start_pic = inner(s0)

    def run(seq):
        binds = []
        run.binds = binds
        seen = {key(np.where(clock, 0, start_pic))}
        out = []
        for f0, f1, a, xy, st in seq:
            S, bk = slots_of(f0, f1, a, xy, st, start_pic, seen, clock, still_sigs)
            if bk:
                seen.add(bk)
            out.append(sorted(S))
            binds.append(dict(LAST_BIND))
            if str(st).endswith("GAME_OVER"):
                seen = {key(np.where(clock, 0, start_pic))}
        return out

    rs = run(route); route_b = run.binds
    rd = run(rand); rand_b = run.binds
    changed = [bool((inner(x[0]) != inner(x[1])).any()) for x in rand]
    # matching-pair survey on the start screen
    surv = {}
    for sig in ("exact", "d4", "rc"):
        c = Counter(t[sig] for t in t_start)
        mem = np.zeros(start_pic.shape, bool)
        for t in t_start:
            if 2 <= c[t[sig]] <= 8:
                mem |= t["mask"]
        memd = binary_dilation(mem, iterations=1)
        def touch(x):
            D = inner(x[0]) != inner(x[1])
            return bool((D & memd).any())
        surv[sig] = dict(cover=float(mem.mean()), n_pairs=int(sum(1 for k in c.values() if 2 <= k <= 8)),
                         route=[touch(x) for x in route[:-1]], win=touch(route[-1]),
                         rand=[touch(x) for x, ch_ in zip(rand, changed) if ch_],
                         route_any=any(touch(x) for x in route))
    # odd one out: same shape (up to flips and recolouring) but no exact twin
    crc = Counter(t["rc"] for t in t_start); cd4 = Counter(t["d4"] for t in t_start)
    odd = np.zeros(start_pic.shape, bool)
    for t in t_start:
        if 2 <= crc[t["rc"]] <= 8 and cd4[t["d4"]] == 1:
            odd |= t["mask"]
    oddd = binary_dilation(odd, iterations=1)
    def touch_odd(x):
        return bool(((inner(x[0]) != inner(x[1])) & oddd).any())
    surv["odd"] = dict(cover=float(odd.mean()), n_pairs=int(odd.any()), route=[touch_odd(x) for x in route[:-1]],
                       win=touch_odd(route[-1]), rand=[touch_odd(x) for x, ch_ in zip(rand, changed) if ch_],
                       route_any=any(touch_odd(x) for x in route))
    g_ = key_.split(":")[0]
    return dict(key=key_, game=g_, dept=PUBLIC_DEPT[g_], n_route=len(route), win=rs[-1], route=rs[:-1],
                win_b=route_b[-1], route_b=route_b[:-1], rand_b=[b for b, c in zip(rand_b, changed) if c],
                rand=[s for s, c in zip(rd, changed)], rand_all=rd, clock=int(clock.sum()), survey=surv)


def main(book_path, out_path):
    book = json.load(open(book_path))
    rng = random.Random(0)
    rows = []
    for k, e in sorted(book.items()):
        try:
            r = level(k, e, rng)
        except Exception as ex:
            import traceback; traceback.print_exc(); r = None
        if r:
            rows.append(r)
            print(k, "win:", r["win"], flush=True)
    json.dump(rows, open(out_path.replace(".md", ".json"), "w"))
    report(rows, out_path)


def report(rows, out_path):
    games = sorted({r["game"] for r in rows})
    L = [f"# The core card: 12 slots measured from frames", "",
         f"{len(rows)} winning routes replayed ({len(games)} games). Arbitrary presses: up to 150 random presses from "
         "each level start (the comparison counts only those that changed the board, not just the clock or step bar; deaths reset the level). The "
         "winning press is read on the first frame after it (before the level-end animation).", ""]
    # per level
    L += ["## Per level: the slots of the winning press, of the route, and of random exploration", "",
          "| level | dept | presses | winning press | route (share of presses) | met while exploring (share) |", "|---|---|---|---|---|---|"]
    for r in rows:
        rc = Counter(s for S in r["route"] for s in S); n = max(1, len(r["route"]))
        xc = Counter(s for S in r["rand_all"] for s in S); m = max(1, len(r["rand_all"]))
        L.append(f"| {r['key']} | {r['dept']} | {r['n_route']} | {' '.join(r['win']) or '(none)'} | "
                 + ", ".join(f"{s} {rc[s]/n:.0%}" for s in SLOTS if rc[s]) + " | "
                 + ", ".join(f"{s} {xc[s]/m:.0%}" for s in SLOTS if xc[s]) + " |")
    # coverage
    plus = [s for s in SLOTS if s.endswith("+")]
    unc = [r["key"] for r in rows if not (set(r["win"]) & set(plus))]
    L += ["", "## Coverage", "",
          f"Winning presses with no + slot: {len(unc)} of {len(rows)}" + (f" ({', '.join(unc)})" if unc else "") + ".", ""]
    L += ["| slot | winning presses with it | levels whose route uses it | levels whose exploration meets it | route presses | arbitrary presses that changed the board | lift pooled | lift, each game equal | games where route has it more |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in SLOTS:
        w = sum(s in r["win"] for r in rows)
        ru = sum(any(s in S for S in r["route"] + [r["win"]]) for r in rows)
        ex = sum(any(s in S for S in r["rand_all"]) for r in rows)
        rp = [s in S for r in rows for S in r["route"]]
        ap = [s in S for r in rows for S in r["rand"] if "CONTROL-" not in S]
        a_ = np.mean(ap) if ap else 0; b_ = np.mean(rp) if rp else 0
        # game-balanced
        per = []
        more = 0
        for g in games:
            rg = [s in S for r in rows if r["game"] == g for S in r["route"]]
            ag = [s in S for r in rows if r["game"] == g for S in r["rand"] if "CONTROL-" not in S]
            if rg and ag:
                per.append((np.mean(rg), np.mean(ag)))
                more += np.mean(rg) > np.mean(ag)
        bal = (np.mean([p[0] for p in per]) / np.mean([p[1] for p in per])) if per and np.mean([p[1] for p in per]) > 0 else float("inf")
        L.append(f"| {s} {NAMES[s]} | {w} | {ru} | {ex} | {b_:.0%} | {a_:.1%} | {b_ / a_ if a_ else float('inf'):.1f}x | {bal:.1f}x | {more} of {len(per)} |")
    L += ["", "Per game, share of route presses vs arbitrary board-changing presses (+ slots):", "",
          "| game | " + " | ".join(x for x in SLOTS if x.endswith("+")) + " |", "|---" * 7 + "|"]
    for g in games:
        cells = []
        for s in [x for x in SLOTS if x.endswith("+")]:
            rg = [s in S for r in rows if r["game"] == g for S in r["route"]]
            ag = [s in S for r in rows if r["game"] == g for S in r["rand"] if "CONTROL-" not in S]
            cells.append(f"{np.mean(rg):.0%} / {np.mean(ag):.0%}" if rg and ag else "-")
        L.append(f"| {g} | " + " | ".join(cells) + " |")
    # co-firing on winning presses
    pc = Counter()
    for r in rows:
        W = sorted(set(r["win"]))
        for i in range(len(W)):
            for j in range(i + 1, len(W)):
                pc[(W[i], W[j])] += 1
    L += ["", "Slots that come together on winning presses (pairs, count of levels): " +
          ", ".join(f"{a}&{b} {c}" for (a, b), c in pc.most_common(10)), ""]
    always = []
    for s in SLOTS:
        for t in SLOTS:
            if s < t:
                rs_ = [r for r in rows if s in r["win"] or t in r["win"]]
                if len(rs_) >= 3 and all(s in r["win"] and t in r["win"] for r in rs_):
                    always.append(f"{s}&{t} ({len(rs_)})")
    L.append("Pairs that always come together on winning presses (at least 3 levels): " + (", ".join(always) or "none") + ".")
    # survey
    L += ["", "## Matching-pair survey: things on the start screen with a twin", "",
          "Twins: things (connected non-background regions) that occur 2 to 8 times on the level's start screen. "
          "A press touches a twin if it changes a pixel on or next to one. 'odd' = same shape as another thing up to "
          "flips and recolouring, but no exact twin (the differ side).", "",
          "| twins | levels with any | screen covered (mean) | route presses touching | arbitrary presses touching | lift pooled | lift each game equal | winning press touches | routes that touch one at all |",
          "|---|---|---|---|---|---|---|---|---|"]
    for sig, nm in (("exact", "exact copies"), ("d4", "up to flips"), ("rc", "up to flips and recolouring"), ("odd", "odd one out")):
        rr = [r for r in rows if r["survey"][sig]["n_pairs"]]
        rp = [x for r in rr for x in r["survey"][sig]["route"]]
        ap = [x for r in rr for x in r["survey"][sig]["rand"]]
        per = []
        for g in games:
            rg = [x for r in rr if r["game"] == g for x in r["survey"][sig]["route"]]
            ag = [x for r in rr if r["game"] == g for x in r["survey"][sig]["rand"]]
            if rg and ag:
                per.append((np.mean(rg), np.mean(ag)))
        bal = (np.mean([p[0] for p in per]) / np.mean([p[1] for p in per])) if per and np.mean([p[1] for p in per]) > 0 else float("nan")
        b_ = np.mean(rp) if rp else 0; a_ = np.mean(ap) if ap else 0
        L.append(f"| {nm} | {len(rr)} of {len(rows)} | {np.mean([r['survey'][sig]['cover'] for r in rr]) if rr else 0:.0%} | "
                 f"{b_:.0%} | {a_:.0%} | {b_ / a_ if a_ else float('nan'):.1f}x | {bal:.1f}x | "
                 f"{sum(r['survey'][sig]['win'] for r in rr)} of {len(rr)} | {sum(r['survey'][sig]['route_any'] for r in rr)} of {len(rr)} |")
    open(out_path, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(json.load(open(sys.argv[2])), sys.argv[3])
    else:
        main(sys.argv[1], sys.argv[2])
