"""Relational events: colour-free descriptions of what a press did, made of relations between things
rather than roles. Each is a candidate general rung. The test is the same as for "the game took control":
does it single out the winning press, and the presses on winning routes, against arbitrary presses, pooled
over games (so it can only pass if it means the same thing in every game)?

  python relations.py trail/frontier_casebook.json trail/relations.md"""
import json, logging, os, sys, random
from collections import defaultdict
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL); os.environ.pop("ONLY_RESET_LEVELS", None)
import harness  # noqa: E402
from arc_agi import Arcade, OperationMode  # noqa: E402
from arcengine import ActionInput, GameAction  # noqa: E402
from scipy.ndimage import label, binary_dilation  # noqa: E402
from mika3.explorer import components  # noqa: E402
from mika3.university import PUBLIC_DEPT  # noqa: E402

EIGHT = np.ones((3, 3), int)
arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))


def start(e):
    card = arcade.open_scorecard(); env = arcade.make(e["game"], scorecard_id=card); g = env._game
    if e["level"] > 0:
        g.set_level(e["level"])
    g._action_count = 1
    return g


def render(g):
    return np.array(g.camera.render(g.current_level.get_sprites()), dtype=np.int16)


def inner(f):
    return f[2:-2, 2:-2]          # border bars are clocks


def objects(f):
    """things: connected non-background regions (several colours allowed), as translation-free patches"""
    vals, cnt = np.unique(f, return_counts=True)
    bg = vals[cnt.argmax()]
    lab, n = label(f != bg, structure=EIGHT)
    out = []
    for i in range(1, min(n, 200) + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) > 600:
            continue
        p = f[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
        m = (lab[ys.min():ys.max() + 1, xs.min():xs.max() + 1] == i)
        p[~m] = -1
        out.append(p.tobytes() + bytes(p.shape))
    return out


def pairs(objs):
    from collections import Counter
    return sum(c * (c - 1) // 2 for c in Counter(objs).values())


def colour_comps(f):
    """colour -> number of same-colour regions"""
    out = defaultdict(int)
    for c, n, _, _ in components(f):
        out[int(c)] += 1
    return out


def symmetry(f):
    return max(float((f == f[:, ::-1]).mean()), float((f == f[::-1, :]).mean()))


def relations(f0, f1, nfr, med, a, xy):
    """the colour-free relational description of one press"""
    g0, g1 = inner(f0), inner(f1)
    D = g0 != g1
    R = {}
    R["took control"] = nfr >= max(3, 2 * med)
    R["nothing changed"] = not D.any()
    R["big change (over 10% of the screen)"] = D.mean() > 0.10
    if not D.any():
        return R
    o0, o1 = objects(g0), objects(g1)
    p0, p1 = pairs(o0), pairs(o1)
    R["made two things equal"] = p1 > p0
    R["made two equal things differ"] = p1 < p0
    R["fewer things"] = len(o1) < len(o0)
    R["more things"] = len(o1) > len(o0)
    c0, c1 = set(np.unique(g0).tolist()), set(np.unique(g1).tolist())
    R["a colour vanished"] = bool(c0 - c1)
    R["a colour appeared"] = bool(c1 - c0)
    R["more symmetric"] = symmetry(g1) > symmetry(g0) + 0.005
    R["less symmetric"] = symmetry(g1) < symmetry(g0) - 0.005
    # an indicator: a small change far from the main change
    lab, n = label(D, structure=EIGHT)
    if n >= 2:
        sizes = [(int((lab == i).sum()), i) for i in range(1, n + 1)]
        big = max(sizes)[1]
        near = binary_dilation(lab == big, iterations=6)
        R["something small changed far away"] = any(s <= 36 and not (near & (lab == i)).any() for s, i in sizes if i != big)
    else:
        R["something small changed far away"] = False
    # touched a one-of-a-kind thing: a change next to a region whose colour occurs in only one region
    cc = colour_comps(g0)
    uniq = [c for c, k in cc.items() if k == 1]
    if uniq:
        U = np.isin(g0, uniq)
        lab0, _ = label(U, structure=EIGHT)
        small = np.zeros_like(U)
        for i in range(1, lab0.max() + 1):
            m = lab0 == i
            if m.sum() <= 64:
                small |= m
        R["touched a one-of-a-kind thing"] = bool((binary_dilation(D, iterations=1) & small).any())
    else:
        R["touched a one-of-a-kind thing"] = False
    if a == 6 and xy is not None:
        c = int(f0[int(xy[1]), int(xy[0])])
        R["clicked a one-of-a-kind colour"] = colour_comps(f0).get(c, 0) == 1
    return R


def main(book_path, out_path):
    book = json.load(open(book_path))
    rng = random.Random(0)
    rows = []
    for key, e in sorted(book.items()):
        g = start(e); f = render(g); route = []; won = False
        for a, xy, kind in e["route"]:
            data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
            r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
            won = r.levels_completed > 0 or str(r.state).endswith("WIN")
            nxt = won and r.levels_completed > 0 and not str(r.state).endswith("WIN") and len(r.frame) > 1
            fe = np.array(r.frame[-2] if nxt else r.frame[-1], dtype=np.int16) if r.frame else f
            route.append((f, fe, len(r.frame) - (1 if nxt else 0), a, xy))
            if won:
                first = (f, np.array(r.frame[0], dtype=np.int16) if r.frame else f, len(r.frame) - (1 if nxt else 0), a, xy)
            f = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
            if won:
                break
        if not won:
            continue
        g = start(e); f = render(g); rand = []
        acts = [a for a in g._available_actions if a != 0]
        for t in range(150):
            a = rng.choice(acts); data = {}; xy = None
            if a == 6:
                comps = components(f); c = rng.choice(comps); xy = (c[2][1], c[2][0]); data = {"x": xy[0], "y": xy[1]}
            r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
            if r.levels_completed > 0 or str(r.state).endswith("WIN"):
                break
            if str(r.state).endswith("GAME_OVER"):
                g.perform_action(ActionInput(id=GameAction.RESET), raw=True); f = render(g); continue
            f1 = np.array(r.frame[-1], dtype=np.int16) if r.frame else f
            rand.append((f, f1, len(r.frame), a, xy))
            f = f1
        med = float(np.median([x[2] for x in rand])) if rand else 1.0
        rows.append(dict(key=key, game=key.split(":")[0], dept=PUBLIC_DEPT[key.split(":")[0]],
                         win=relations(*route[-1][:3], med, *route[-1][3:]),
                         win_first=relations(*first[:3], med, *first[3:]),
                         route=[relations(*x[:3], med, *x[3:]) for x in route[:-1]],
                         rand=[relations(*x[:3], med, *x[3:]) for x in rand]))
        print(key, len(route), len(rand), flush=True)
    json.dump(rows, open(out_path.replace(".md", ".json"), "w"), default=bool)
    report(rows, out_path)


def report(rows, out_path):
    names = sorted({k for r in rows for d in [r["win"]] + r["route"] + r["rand"] for k in d})
    games = sorted({r["game"] for r in rows})

    def rate(dicts, f):
        v = [bool(f(d)) for d in dicts]
        return (sum(v) / len(v)) if v else 0.0, sum(v), len(v)

    W = [r["win"] for r in rows]; W1 = [r["win_first"] for r in rows]
    # the baseline is arbitrary presses that changed something: route presses always change something, and
    # "press what changes something" is what the explorer does anyway
    RT = [d for r in rows for d in r["route"]]; AR = [d for r in rows for d in r["rand"] if not d.get("nothing changed")]

    def balanced(f):
        """each game weighs the same: mean over games of its route rate, over the mean of its arbitrary rate;
        and in how many games (with at least 3 route presses) route presses have it more often"""
        rr, aa, up, n = [], [], 0, 0
        for g in games:
            rt = [d for r in rows if r["game"] == g for d in r["route"]]
            ar = [d for r in rows if r["game"] == g for d in r["rand"] if not d.get("nothing changed")]
            if len(rt) < 3 or not ar:
                continue
            a, b = rate(rt, f)[0], rate(ar, f)[0]
            rr.append(a); aa.append(b); n += 1; up += a > b
        return (np.mean(rr) / np.mean(aa) if aa and np.mean(aa) > 0 else float("inf")), up, n

    def row(label, f):
        w = rate(W, f); w1 = rate(W1, f); rt = rate(RT, f); ar = rate(AR, f)
        lr = rt[0] / ar[0] if ar[0] else float("inf")
        bl, up, n = balanced(f)
        return (lr, f"| {label} | {rt[0]:.0%} ({rt[1]}) | {ar[0]:.1%} ({ar[1]}) | **{lr:.1f}x** | {bl:.1f}x | {up} of {n} | "
                    f"{w1[0]:.0%} | {w[0]:.0%} |")

    head = ["| description | other presses on winning routes | arbitrary presses that changed something | lift: route (pooled) | lift: route (each game equal) | games where route presses have it more | winning press, first frame | winning press, incl. level-end animation |",
            "|---|---|---|---|---|---|---|---|"]
    single = sorted((row(nm, lambda d, nm=nm: d.get(nm)) for nm in names), key=lambda t: -t[0])
    combo = sorted((row(f"took control and {nm}", lambda d, nm=nm: d.get("took control") and d.get(nm))
                    for nm in names if nm != "took control"), key=lambda t: -t[0])
    lines = ["# Relational events: general rungs between games", "",
             f"{len(rows)} winning routes replayed ({len(games)} games); arbitrary presses: up to 150 random presses from "
             "each level start (the baseline counts only those that changed something). Every description is colour-free; it can only carry between games if it means the same thing in every game.", "",
             "The clean test is the presses on the way to a win (the route minus its last press): the winning press "
             "also plays the level-end animation, which inflates its numbers (shown separately, both with the first "
             "frame after the press and with the frame just before the switch to the next level).", "",
             "## One description", ""] + head + [t[1] for t in single] + \
            ["", "## With the general rung: presses that took control and ...", ""] + head + [t[1] for t in combo]
    open(out_path, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1].endswith(".json") and "casebook" not in sys.argv[1]:
        report(json.load(open(sys.argv[1])), sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
