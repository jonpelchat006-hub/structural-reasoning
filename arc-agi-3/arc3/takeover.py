"""A general rung: "the game took control" (one press, a long animation). Does it single out the winning
press, and the presses on winning routes, against arbitrary presses? Lift measured inside each game
relative to that game's own usual animation length, so it can carry between games."""
import json, logging, os, sys, random
import numpy as np
from collections import defaultdict
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL); os.environ.pop("ONLY_RESET_LEVELS", None)
import harness
from arc_agi import Arcade, OperationMode
from arcengine import ActionInput, GameAction
from mika3.explorer import components
from mika3.university import PUBLIC_DEPT
book = json.load(open(sys.argv[1]))
arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))

def start(e):
    card = arcade.open_scorecard(); env = arcade.make(e["game"], scorecard_id=card); g = env._game
    if e["level"] > 0: g.set_level(e["level"])
    g._action_count = 1
    return g

rows = []
rng = random.Random(0)
for key, e in sorted(book.items()):
    g = start(e); route_frames = []; won = False
    for a, xy, kind in e["route"]:
        data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
        r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
        won = r.levels_completed > 0 or str(r.state).endswith("WIN")
        n = len(r.frame) - (1 if (won and r.levels_completed > 0 and not str(r.state).endswith("WIN")) else 0)
        route_frames.append(n)
        if won: break
    if not won: continue
    # arbitrary presses from the level start
    g = start(e); rand_frames = []
    acts = [a for a in g._available_actions if a not in (0,)]
    for t in range(150):
        a = rng.choice(acts); data = {}
        if a == 6:
            f = np.array(g.camera.render(g.current_level.get_sprites()))
            comps = components(f); c = rng.choice(comps); data = {"x": c[2][1], "y": c[2][0]}
        r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
        if r.levels_completed > 0 or str(r.state).endswith("WIN"): break
        if str(r.state).endswith("GAME_OVER"):
            g.perform_action(ActionInput(id=GameAction.RESET), raw=True); continue
        rand_frames.append(len(r.frame))
    rows.append(dict(key=key, dept=PUBLIC_DEPT[key.split(":")[0]], route=route_frames, rand=rand_frames))

def lift_table(thresh_fn, label):
    out = []
    P = defaultdict(lambda: [0, 0])
    for r in rows:
        med = np.median(r["rand"]) if r["rand"] else 1
        th = thresh_fn(med)
        P["winning press"][0] += r["route"][-1] >= th; P["winning press"][1] += 1
        for n in r["route"][:-1]:
            P["other presses on the winning route"][0] += n >= th; P["other presses on the winning route"][1] += 1
        for n in r["rand"]:
            P["arbitrary presses"][0] += n >= th; P["arbitrary presses"][1] += 1
    base = P["arbitrary presses"][0] / max(1, P["arbitrary presses"][1])
    out.append(f"**{label}**")
    out.append("")
    out.append("| press | took control | lift vs arbitrary |")
    out.append("|---|---|---|")
    for k in ("winning press", "other presses on the winning route", "arbitrary presses"):
        p = P[k][0] / max(1, P[k][1])
        out.append(f"| {k} ({P[k][1]}) | {p:.0%} | {p / base if base else float('inf'):.1f}x |")
    return out

lines = [f"{len(rows)} winning routes replayed; arbitrary presses: 150 random presses from each level start.", ""]
lines += lift_table(lambda med: max(3, 2 * med), "took control = the press animated at least 3 frames and at least twice this game's usual")
lines += [""] + lift_table(lambda med: max(2, med + 1), "looser: longer than this game's usual by at least one frame")
print("\n".join(lines))
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
