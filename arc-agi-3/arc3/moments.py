"""The image plane: moments, and whether they carry between games under limited turns.

A moment is what one press did, kept as a picture: the before/after crop of the main change (the largest
connected changed region; border bars are clocks and are cut away). It is put into a standard form using
only limited turns:
  colours  renumbered in order of appearance (game A's 9 can be game B's 4);
  flips    the 8 flips/rotations of the grid (the smallest form is kept);
  shift    the crop itself (where on the screen it happened does not matter).
Three grains:
  context  the crop with one pixel of unchanged surroundings;
  change   only the changed pixels (before and after), the rest blank;
  shape    only the outline of the change, plus how many colours it had before and after.

Survey: for each game (leave-one-game-out), the library is the moments of the winning routes of the OTHER
games. Do this game's route presses match the library more often than its arbitrary presses that changed
something? With no turns, colours only, and colours + flips, to see whether the limited turns are what let
moments carry.

  python moments.py trail/frontier_casebook.json trail/moments.md"""
import json, logging, os, sys, random, hashlib
from collections import defaultdict, Counter
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL); os.environ.pop("ONLY_RESET_LEVELS", None)

EIGHT = np.ones((3, 3), int)
GRAINS = ("context", "change", "shape")
TURNS = ("none", "colours", "colours+flips")


def renumber(*arrs):
    """colours renumbered in order of first appearance across the arrays (row-major); -1 stays blank"""
    flat = np.concatenate([a.ravel() for a in arrs])
    vals = flat[flat >= 0]
    lut = np.full(257, -1, dtype=np.int16)          # index v + 1 (so that -1 maps to slot 0)
    if vals.size:
        u, idx = np.unique(vals, return_index=True)
        order = u[np.argsort(idx)]
        lut[order.astype(int) + 1] = np.arange(len(order), dtype=np.int16)
    return [lut[a.astype(int) + 1] for a in arrs]


def d4(a):
    r = [a, np.rot90(a, 1), np.rot90(a, 2), np.rot90(a, 3)]
    return r + [np.fliplr(x) for x in r]


def moment_keys(f0, f1):
    """{(grain, turns): key} for one press, or None if nothing changed (border bars cut away)"""
    from scipy.ndimage import label
    g0 = np.asarray(f0, dtype=np.int16)[2:-2, 2:-2]; g1 = np.asarray(f1, dtype=np.int16)[2:-2, 2:-2]
    if g0.shape != g1.shape:
        return None
    D = g0 != g1
    if not D.any():
        return None
    lab, n = label(D, structure=EIGHT)
    sizes = np.bincount(lab.ravel())[1:]
    big = int(sizes.argmax()) + 1
    M = lab == big
    ys, xs = np.nonzero(M)
    out = {}
    for grain in GRAINS:
        pad = 1 if grain == "context" else 0
        y0, y1 = max(0, ys.min() - pad), min(g0.shape[0], ys.max() + 1 + pad)
        x0, x1 = max(0, xs.min() - pad), min(g0.shape[1], xs.max() + 1 + pad)
        if (y1 - y0) > 24 or (x1 - x0) > 24:
            # a big change: keep only its rough size; it is the same "kind" of picture at every turn
            k = ("big", (y1 - y0) // 8, (x1 - x0) // 8)
            for t in TURNS:
                out[(grain, t)] = str(k)
            continue
        B = g0[y0:y1, x0:x1].copy(); A = g1[y0:y1, x0:x1].copy(); m = M[y0:y1, x0:x1]
        if grain == "change":
            B[~m] = -1; A[~m] = -1
        if grain == "shape":
            nb = len(set(g0[M].tolist())); na = len(set(g1[M].tolist()))
            forms = {"none": [m.astype(np.int16)], "colours": [m.astype(np.int16)], "colours+flips": d4(m.astype(np.int16))}
            for t, fs in forms.items():
                out[(grain, t)] = min(f"{f.shape}{f.tobytes().hex()}" for f in fs) + f"|{nb},{na}"
            continue
        for t in TURNS:
            if t == "none":
                pairs = [(B, A)]
            elif t == "colours":
                pairs = [tuple(renumber(B, A))]
            else:
                pairs = [tuple(renumber(b, a)) for b, a in zip(d4(B), d4(A))]
            out[(grain, t)] = min(hashlib.blake2b(b.tobytes() + a.tobytes() + bytes(str(b.shape), "ascii"),
                                                  digest_size=10).hexdigest() for b, a in pairs)
    return out


def collect(book_path):
    import harness
    from arc_agi import Arcade, OperationMode
    from arcengine import ActionInput, GameAction
    from mika3.explorer import components
    from mika3.university import PUBLIC_DEPT
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))

    def start(e):
        card = arcade.open_scorecard(); env = arcade.make(e["game"], scorecard_id=card); g = env._game
        if e["level"] > 0:
            g.set_level(e["level"])
        g._action_count = 1
        return g

    def render(g):
        return np.array(g.camera.render(g.current_level.get_sprites()), dtype=np.int16)

    book = json.load(open(book_path))
    rng = random.Random(0)
    rows = []
    for key, e in sorted(book.items()):
        g = start(e); f = render(g); route = []; won = False; win = None
        for a, xy, kind in e["route"]:
            data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
            r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
            won = r.levels_completed > 0 or str(r.state).endswith("WIN")
            if won:
                # the winning press: its first frame (the level-end animation comes after)
                win = moment_keys(f, np.array(r.frame[0], dtype=np.int16)) if r.frame else None
                break
            f1 = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
            route.append(moment_keys(f, f1))
            f = f1
        if not won:
            continue
        g = start(e); f = render(g); rand = []
        acts = [a for a in g._available_actions if a != 0]
        for t in range(150):
            a = rng.choice(acts); data = {}
            if a == 6:
                comps = components(f); c = rng.choice(comps); data = {"x": c[2][1], "y": c[2][0]}
            r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
            if r.levels_completed > 0 or str(r.state).endswith("WIN"):
                break
            if str(r.state).endswith("GAME_OVER"):
                g.perform_action(ActionInput(id=GameAction.RESET), raw=True); f = render(g); continue
            f1 = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
            rand.append(moment_keys(f, f1))
            f = f1
        js = lambda d: None if d is None else {f"{gr}/{t}": v for (gr, t), v in d.items()}
        rows.append(dict(key=key, game=key.split(":")[0], level=int(key.split(":")[1]), dept=PUBLIC_DEPT[key.split(":")[0]],
                         route=[js(d) for d in route], win=js(win), rand=[js(d) for d in rand]))
        print(key, len(route), len(rand), flush=True)
    return rows


def report(rows, out_path):
    games = sorted({r["game"] for r in rows})
    lines = ["# The image plane: do moments carry between games under limited turns?", "",
             f"{len(rows)} winning routes replayed ({len(games)} games); arbitrary presses: up to 150 random presses "
             "from each level start, counting only those that changed something. A moment is the before/after crop of a "
             "press's main change.", "",
             "**Library** = the moments of the winning routes of the *other* games (a game never sees its own). "
             "**Match** = a press whose moment is in the library. **Route-like** = a moment seen more often (relative) on "
             "the other games' routes than on their arbitrary presses, by at least 2x.", ""]

    def presses(r, which):
        return [d for d in (r["route"] if which == "route" else r["rand"]) if d]

    for test in ("match", "route-like"):
        lines += [f"## {test}", "",
                  "| grain | turns | route presses | arbitrary presses | lift (pooled) | lift (games equal) | games where route presses match more | winning press (first frame) |",
                  "|---|---|---|---|---|---|---|---|"]
        for grain in GRAINS:
            for t in TURNS:
                k = f"{grain}/{t}"
                rr, aa, ww, per = [], [], [], []
                for g in games:
                    other = [r for r in rows if r["game"] != g]
                    lib_r = Counter(d[k] for r in other for d in presses(r, "route") + ([r["win"]] if r["win"] else []))
                    nr = sum(lib_r.values()) or 1
                    lib_a = Counter(d[k] for r in other for d in presses(r, "rand"))
                    na = sum(lib_a.values()) or 1
                    if test == "match":
                        ok = lambda key: key in lib_r
                    else:
                        ok = lambda key: key in lib_r and lib_r[key] / nr > 2 * lib_a.get(key, 0) / na
                    mine = [r for r in rows if r["game"] == g]
                    R = [ok(d[k]) for r in mine for d in presses(r, "route")]
                    A = [ok(d[k]) for r in mine for d in presses(r, "rand")]
                    W = [ok(r["win"][k]) for r in mine if r["win"]]
                    rr += R; aa += A; ww += W
                    if len(R) >= 3 and A:
                        per.append((np.mean(R), np.mean(A)))
                pr, pa = np.mean(rr), np.mean(aa)
                br, ba = np.mean([x for x, _ in per]), np.mean([y for _, y in per])
                up = sum(1 for x, y in per if x > y)
                lines.append(f"| {grain} | {t} | {pr:.0%} | {pa:.1%} | **{pr / pa if pa else float('inf'):.1f}x** | "
                             f"{br / ba if ba else float('inf'):.1f}x | {up} of {len(per)} | {np.mean(ww):.0%} |")
        lines.append("")
    # within the game: earlier levels' route moments (the specific rung, as images)
    lines += ["## Within a game: the library is this game's earlier levels", "",
              "| grain | turns | route presses | arbitrary presses | lift | levels |", "|---|---|---|---|---|---|"]
    for grain in GRAINS:
        for t in TURNS:
            k = f"{grain}/{t}"
            rr, aa, n = [], [], 0
            for r in rows:
                prev = [q for q in rows if q["game"] == r["game"] and q["level"] < r["level"]]
                if not prev:
                    continue
                lib = {d[k] for q in prev for d in presses(q, "route") + ([q["win"]] if q["win"] else [])}
                rr += [d[k] in lib for d in presses(r, "route")]; aa += [d[k] in lib for d in presses(r, "rand")]; n += 1
            pr, pa = np.mean(rr), np.mean(aa)
            lines.append(f"| {grain} | {t} | {pr:.0%} | {pa:.1%} | {pr / pa if pa else float('inf'):.1f}x | {n} |")
    # winning moments: does the winning press look like a win from elsewhere, more than ordinary presses do?
    for scope in ("other games", "earlier levels of the same game"):
        lines += ["", f"## Winning moments: the library is the winning presses of {scope}", "",
                  "| grain | turns | winning press | other route presses | arbitrary presses | lift: win vs arbitrary | lift: route vs arbitrary | levels |",
                  "|---|---|---|---|---|---|---|---|"]
        for grain in GRAINS:
            for t in TURNS:
                k = f"{grain}/{t}"
                ww, rr, aa, n = [], [], [], 0
                for r in rows:
                    if scope == "other games":
                        pool = [q for q in rows if q["game"] != r["game"]]
                    else:
                        pool = [q for q in rows if q["game"] == r["game"] and q["level"] < r["level"]]
                    lib = {q["win"][k] for q in pool if q["win"]}
                    if not lib or not r["win"]:
                        continue
                    n += 1
                    ww.append(r["win"][k] in lib)
                    rr += [d[k] in lib for d in presses(r, "route")]
                    aa += [d[k] in lib for d in presses(r, "rand")]
                pw, pr, pa = np.mean(ww), np.mean(rr), np.mean(aa)
                f = lambda x: f"{x / pa:.1f}x" if pa else ("inf" if x else "-")
                lines.append(f"| {grain} | {t} | {pw:.0%} | {pr:.1%} | {pa:.1%} | {f(pw)} | {f(pr)} | {n} |")
    open(out_path, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    if "casebook" in src:
        rows = collect(src)
        json.dump(rows, open(out.replace(".md", ".json"), "w"))
    else:
        rows = json.load(open(src))
    report(rows, out)
