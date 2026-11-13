"""The sideways plane: events instead of screens, and the first employer survey.

An event is one press described in kinds of things, not pixels:
  (action class, what was clicked, what changed: moved / recoloured / appeared / vanished, by which
   colours, near the actor or elsewhere, and whether the level ended).
Two granularities:
  fine   = with colours (colours are stable inside a game, so levels of one game can share these);
  coarse = colour-free roles ("the clicked thing changed its own colour", "the mover moved",
           "something away from the actor changed") - what could carry between games.

Survey (employer feedback): replay every winning route in the casebook from its level start (the engine
is deterministic), turn it into events, and ask, for each level, whether the skills its winning route
uses - and the event that wins it - were already known from (a) the previous levels of the same game,
(b) other games of the same department, (c) other departments.

  python events.py trail/frontier_casebook.json trail/events.json"""
import json, logging, os, sys
from collections import Counter, defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL)
os.environ.pop("ONLY_RESET_LEVELS", None)
import harness  # noqa: E402
from scipy.ndimage import label  # noqa: E402

EIGHT = np.ones((3, 3), int)


def size_bucket(n):
    return 0 if n <= 2 else 1 if n <= 9 else 2 if n <= 36 else 3 if n <= 144 else 4 if n <= 600 else 5


def comp_at(f, x, y):
    """the same-colour region under a click"""
    c = f[y, x]
    lab, _ = label(f == c)
    m = lab == lab[y, x]
    return int(c), int(m.sum()), m


def describe(f0, f1, a, xy, won):
    """one press -> (fine, coarse) event signatures"""
    D = f0 != f1
    D[:2, :] = False; D[-2:, :] = False; D[:, :2] = False; D[:, -2:] = False     # border bars are clocks
    act = "click" if a == 6 else ("A5" if a == 5 else ("undo" if a == 7 else "move"))
    target = None; tmask = None
    if a == 6 and xy is not None:
        c, n, tmask = comp_at(f0, int(xy[0]), int(xy[1]))
        target = (c, size_bucket(n))
    effects_f, effects_c = [], []
    if D.any():
        lab, n = label(D, structure=EIGHT)
        for i in range(1, n + 1):
            m = lab == i
            before = tuple(sorted(set(f0[m].tolist()))); after = tuple(sorted(set(f1[m].tolist())))
            sb = size_bucket(int(m.sum()))
            on_target = bool(tmask is not None and (m & tmask).any())
            if set(before) == set(after):
                kind = "moved"            # same colours, rearranged: something moved through here
            elif len(before) == 1 and len(after) == 1:
                kind = "recoloured"
            else:
                kind = "changed"
            effects_f.append((kind, before, after, sb, on_target))
            effects_c.append((kind, sb >= 3, on_target))
    eff_f = tuple(sorted(set(effects_f)))[:6]
    eff_c = tuple(sorted(set(effects_c)))
    fine = (act, target, eff_f, won)
    coarse = (act, "self" if any(e[2] for e in effects_c) else ("other" if effects_c else "none"),
              tuple(sorted({e[0] for e in effects_c})), len(effects_c) > 1, won)
    return fine, coarse


def replay(entry):
    from arc_agi import Arcade, OperationMode
    from arcengine import ActionInput, GameAction
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))
    card = arcade.open_scorecard()
    env = arcade.make(entry["game"], scorecard_id=card)
    g = env._game
    if entry["level"] > 0:
        g.set_level(entry["level"])
    g._action_count = 1
    f = np.array(g.camera.render(g.current_level.get_sprites()))
    evs = []; won = False
    for a, xy, kind in entry["route"]:
        data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
        r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
        f1 = np.array(r.frame[-1]) if r.frame else f
        won = r.levels_completed > 0 or str(r.state).endswith("WIN")
        if won and r.levels_completed > 0 and not str(r.state).endswith("WIN") and len(r.frame) > 1:
            # the last frame is already the next level; the press's own effect is the frame before it
            fe = np.array(r.frame[-2])
        else:
            fe = f1
        evs.append(describe(f, fe, a, xy, won))
        f = f1
        if won:
            break
    return evs, won


def main(book_path, out_path):
    from mika3.university import PUBLIC_DEPT
    book = json.load(open(book_path))
    rows = {}
    ok = 0
    for key, e in sorted(book.items(), key=lambda kv: (kv[0].split(":")[0], int(kv[0].split(":")[1]))):
        try:
            evs, won = replay(e)
        except Exception as ex:
            evs, won = [], False
        ok += won
        rows[key] = dict(game=key.split(":")[0], level=int(key.split(":")[1]), dept=PUBLIC_DEPT[key.split(":")[0]],
                         replay_won=won, fine=[repr(x[0]) for x in evs], coarse=[repr(x[1]) for x in evs])
    print(f"replayed {len(rows)} winning routes; {ok} reproduce the win from the level start")

    # ---- the survey
    keys = [k for k in rows if rows[k]["replay_won"] and rows[k]["fine"]]
    def skills(k, which):          # the distinct events a route uses (without the winning flag)
        return {s.rsplit(",", 1)[0] for s in rows[k][which]}
    def win_ev(k, which):
        return rows[k][which][-1].rsplit(",", 1)[0]
    lines = ["# The first employer survey: do skills carry sideways?", "",
             f"{len(keys)} winning routes replayed to the win (of {len(rows)} inside levels), turned into events.", "",
             "For each level: the share of its winning route's distinct skills already seen, and whether its winning event was already seen, in",
             "(a) earlier levels of the same game, (b) other games of the same department, (c) other departments.", ""]
    for which in ("fine", "coarse"):
        stats = defaultdict(list)
        for k in keys:
            g, lv, dept = rows[k]["game"], rows[k]["level"], rows[k]["dept"]
            S = skills(k, which); W = win_ev(k, which)
            pools = {
                "a: earlier levels, same game": [j for j in keys if rows[j]["game"] == g and rows[j]["level"] < lv],
                "b: other games, same department": [j for j in keys if rows[j]["game"] != g and rows[j]["dept"] == dept],
                "c: other departments": [j for j in keys if rows[j]["dept"] != dept],
            }
            for name, pool in pools.items():
                if not pool:
                    continue
                known = set().union(*(skills(j, which) for j in pool))
                wins = {win_ev(j, which) for j in pool}
                stats[name].append((len(S & known) / max(1, len(S)), W in known, W in wins))
        lines += [f"## {which} events", "", "| employer pool | levels with a pool | skills already known | winning event already seen as a skill | winning event = an earlier winning event |", "|---|---|---|---|---|"]
        for name in ("a: earlier levels, same game", "b: other games, same department", "c: other departments"):
            v = stats.get(name, [])
            if not v:
                lines.append(f"| {name} | 0 | | | |"); continue
            lines.append(f"| {name} | {len(v)} | {np.mean([x[0] for x in v]):.0%} | {np.mean([x[1] for x in v]):.0%} | {np.mean([x[2] for x in v]):.0%} |")
        lines.append("")
    # the vocabulary
    for which in ("coarse",):
        c = Counter(s.rsplit(",", 1)[0] for k in keys for s in set(rows[k][which]))
        lines += ["Most common coarse skills (in how many winning routes):", ""]
        lines += [f"- {n}x  {s}" for s, n in c.most_common(10)]
        wc = Counter(win_ev(k, which) for k in keys)
        lines += ["", "Most common winning events (coarse):", ""] + [f"- {n}x  {s}" for s, n in wc.most_common(8)]
    json.dump(rows, open(out_path, "w"), indent=0)
    open(out_path.replace(".json", ".md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
