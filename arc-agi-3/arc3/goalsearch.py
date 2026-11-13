"""The image plane used forward: "this place in the new level looks like where I won last time."

A press's picture is only seen after the press. To steer before the win, she has to look for the BEFORE half
of the last win's picture in the new level's screen. For each pair of levels (k-1 won, k inside the school) of
a game:
  templates  each changed region of level k-1's winning press, cut from the frame before that press (only
             the changed pixels; the rest blank). Regions of 1 pixel are skipped.
  search     every place in level k's START screen where a template fits, under limited turns: the 8
             flips/rotations, with exact colours, or with colours renumbered (any consistent one-to-one
             recolouring).
  test       does a hit overlap the place where level k is actually won (the changed regions of its winning
             press)? precision = hits that overlap / all hits; base = the share of all places of that size
             that overlap (what a blind guess gets); coverage = levels where some hit overlaps.

  python goalsearch.py trail/frontier_casebook.json trail/goalsearch.md"""
import json, logging, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL); os.environ.pop("ONLY_RESET_LEVELS", None)
from scipy.ndimage import label  # noqa: E402
EIGHT = np.ones((3, 3), int)


def replay(arcade, e):
    """(start frame, frame before the winning press, first frame after it) of a casebook route, or None"""
    from arcengine import ActionInput, GameAction
    card = arcade.open_scorecard(); env = arcade.make(e["game"], scorecard_id=card); g = env._game
    if e["level"] > 0:
        g.set_level(e["level"])
    g._action_count = 1
    f = np.array(g.camera.render(g.current_level.get_sprites()), dtype=np.int16)
    s = f
    for a, xy, kind in e["route"]:
        data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
        r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
        if r.levels_completed > 0 or str(r.state).endswith("WIN"):
            return s, f, np.array(r.frame[0], dtype=np.int16)
        if r.frame:
            f = np.array(r.frame[-1], dtype=np.int16)
    return None


def regions(f0, f1):
    """changed regions (inner area; border bars are clocks), as (mask, bbox)"""
    D = np.zeros(f0.shape, bool)
    D[2:-2, 2:-2] = (f0 != f1)[2:-2, 2:-2]
    lab, n = label(D, structure=EIGHT)
    out = []
    for i in range(1, min(n, 20) + 1):
        m = lab == i
        ys, xs = np.nonzero(m)
        out.append((m, (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)))
    return out


def turns(T):
    r = [np.rot90(T, k) for k in range(4)]
    return r + [np.fliplr(x) for x in r]


def fits(S, T, recolour):
    """boolean map of top-left places where template T (-1 = blank) fits screen S"""
    h, w = T.shape
    H, W = S.shape
    if h > H or w > W:
        return np.zeros((0, 0), bool)
    from numpy.lib.stride_tricks import sliding_window_view
    V = sliding_window_view(S, (h, w))                     # (H-h+1, W-w+1, h, w)
    ok = np.ones(V.shape[:2], bool)
    cols = [c for c in np.unique(T) if c >= 0]
    got = []
    for c in cols:
        ys, xs = np.nonzero(T == c)
        vals = V[:, :, ys, xs]                             # (.., .., n)
        same = (vals == vals[:, :, :1]).all(axis=2)
        if recolour:
            ok &= same
            got.append(vals[:, :, 0])
        else:
            ok &= same & (vals[:, :, 0] == c)
    if recolour and len(got) > 1:                          # one-to-one: different template colours, different colours
        G = np.stack(got, axis=2)
        for i in range(len(got)):
            for j in range(i + 1, len(got)):
                ok &= G[:, :, i] != G[:, :, j]
    return ok


def main(book_path, out_path):
    import harness
    from arc_agi import Arcade, OperationMode
    from mika3.university import PUBLIC_DEPT
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))
    book = json.load(open(book_path))
    rep = {k: replay(arcade, e) for k, e in book.items()}
    rows = []
    for key, e in sorted(book.items()):
        g, lv = key.split(":")[0], int(key.split(":")[1])
        prev = rep.get(f"{g}:{lv - 1}")
        cur = rep.get(key)
        if prev is None or cur is None:
            continue
        _, pf0, pf1 = prev
        start, cf0, cf1 = cur
        target = np.zeros(start.shape, bool)
        for m, _ in regions(cf0, cf1):
            target |= m
        if not target.any():
            continue
        temps = []
        for m, (y0, y1, x0, x1) in regions(pf0, pf1):
            if m.sum() < 2 or (y1 - y0) > 24 or (x1 - x0) > 24:
                continue
            T = np.where(m[y0:y1, x0:x1], pf0[y0:y1, x0:x1], -1)
            temps.append(T)
        row = dict(key=key, dept=PUBLIC_DEPT[g], n_templates=len(temps))
        for recolour in (False, True):
            hits = over = base_n = base_d = 0
            for T in temps:
                seen = set()
                for Tt in turns(T):
                    F = fits(start, Tt, recolour)
                    if F.size == 0:
                        continue
                    h, w = Tt.shape
                    # every place of this size: does it overlap where level k is won?
                    from numpy.lib.stride_tricks import sliding_window_view
                    ov = sliding_window_view(target, (h, w)).any(axis=(2, 3))
                    base_n += int(ov.sum()); base_d += ov.size
                    for y, x in zip(*np.nonzero(F)):
                        if (y, x, h, w) in seen:
                            continue
                        seen.add((y, x, h, w))
                        hits += 1; over += bool(ov[y, x])
            row["recolour" if recolour else "exact"] = dict(hits=hits, over=over, base=base_n / base_d if base_d else 0.0)
        rows.append(row)
        print(key, row, flush=True)
    lines = ["# The image plane used forward: does the last win's before-picture find the next win's place?", "",
             f"{len(rows)} levels whose previous level is also inside the school. Templates: the changed regions of the "
             "previous level's winning press, cut from the frame before it. Searched in the new level's start screen "
             "under the 8 flips/rotations.", "",
             "| colours | levels with a hit | levels where a hit is on the next win's place | precision of hits | blind guess | lift |",
             "|---|---|---|---|---|---|"]
    for mode in ("exact", "recolour"):
        rs = [r for r in rows if r["n_templates"]]
        withhit = [r for r in rs if r[mode]["hits"]]
        cover = [r for r in rs if r[mode]["over"]]
        prec = np.mean([r[mode]["over"] / r[mode]["hits"] for r in withhit]) if withhit else 0
        base = np.mean([r[mode]["base"] for r in withhit]) if withhit else 0
        lines.append(f"| {mode} | {len(withhit)} of {len(rs)} | {len(cover)} | {prec:.0%} | {base:.0%} | "
                     f"{prec / base if base else float('inf'):.1f}x |")
    lines += ["", "Per level:", "", "| level | department | templates | exact: hits / on target | recolour: hits / on target | blind guess |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['key']} | {r['dept']} | {r['n_templates']} | {r['exact']['hits']} / {r['exact']['over']} | "
                     f"{r['recolour']['hits']} / {r['recolour']['over']} | {r['recolour']['base']:.0%} |")
    open(out_path, "w").write("\n".join(lines) + "\n")
    json.dump(rows, open(out_path.replace(".md", ".json"), "w"), default=int)
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
