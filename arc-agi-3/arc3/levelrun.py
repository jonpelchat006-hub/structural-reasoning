"""Level-start runs: put a student straight into level k of a public game (the engine's set_level),
count her presses until the level is won, and score it as the official card would score that level:
min((human/presses)^2 * 100, 115).

Two uses:
  frontier  the top Mika walks the trail: every level of every game, cold, with a big budget. Every
            level she wins comes in with the shortest route in her own map (the look-back).
  exam      professors are graded on the levels inside the school (won at least once on the
            frontier), cold (blank mind) or warm (carrying what the previous level's frontier route
            teaches: kinds on the route, goal colour, its run structure, the route itself) - exactly
            what she would carry had she won level k-1 herself.

  python levelrun.py frontier SPEC --budget 12000 --seeds 2 --workers 12 --out frontier.json
  python levelrun.py exam SPEC --casebook casebook.json --budget 3000 --seeds 4 --mode warm --out exam_x.json"""
import argparse, ast, json, logging, os, sys, time
import numpy as np
from collections import Counter
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "fw")]
logging.disable(logging.CRITICAL)
os.environ.pop("ONLY_RESET_LEVELS", None)
import harness  # noqa: E402


def _kind(s):
    if s is None or s == "None":
        return None
    try:
        return ast.literal_eval(s) if isinstance(s, str) else tuple(s)
    except Exception:
        return None


def play_level(job):
    spec, game, level, budget, seed, warm = job
    from arc_agi import Arcade, OperationMode
    from arcengine import FrameData, GameState
    t0 = time.time()
    cls = harness.load_class(spec)
    cls.MAX_ACTIONS = budget + 10
    cls.SEED = seed
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))
    card = arcade.open_scorecard()
    env = arcade.make(game, scorecard_id=card)
    g = env._game
    base = env.environment_info.baseline_actions or []
    nlev = len(base)
    if level > 0:
        g.set_level(level)
    g._action_count = 1          # so that her first RESET restarts this level, not the game
    frame = g.camera.render(g.current_level.get_sprites())
    latest = FrameData(game_id=game, frame=[frame.tolist()], state=GameState.NOT_FINISHED, levels_completed=0,
                       win_levels=g._win_score, available_actions=list(g._available_actions))
    agent = cls(card_id=card, game_id=game, agent_name="lvl", ROOT_URL="", record=False, arc_env=env)
    m = agent.mind
    # departments and knobs first (as the student class would at its first frame), then the warm lessons
    if hasattr(agent, "dept") and agent.dept is None:
        from mika3.university import department, apply_knobs, knobs_for
        agent.dept = department(latest.available_actions)
        apply_knobs(agent, knobs_for(agent.plan()), agent.dept, game)
    if warm:
        m.lesson_kinds = Counter({_kind(k): v for k, v in warm.get("kinds", {}).items() if _kind(k) is not None})
        m.goal_colours = set(warm.get("goal") or [])
        route = [(a, None if xy is None else tuple(xy), _kind(kd)) for a, xy, kd in warm.get("route", [])]
        m.last_route = route
        if getattr(m, "MOMENTUM_ADAPT", 0) and route:
            runs = 1 + sum(1 for x, y in zip(route, route[1:]) if (x[0], x[2]) != (y[0], y[2]))
            m.mean_run = len(route) / runs
            m.momentum_now = m.MOMENTUM_ADAPT if m.mean_run >= 2.5 else 0.0
        if getattr(m, "REPLAY", False) and route:
            m.replay = list(route)
        if warm.get("win_templates"):
            m.win_templates = [[np.array(T, dtype=np.int16) for T in warm["win_templates"]]]
        if warm.get("win_moment"):
            m.win_moments = {warm["win_moment"]}
        we = warm.get("win_event")
        if we:
            m.win_event = dict(act=we["act"], col=we["col"], eff={(k, tuple(b), tuple(a)) for k, b, a in we["eff"]})
        # open the level now, so her first look does not treat it as a fresh game and drop the replay
        from mika3.explorer2 import Level
        m.level = Level(0); m.levels_done = 0
    frames = [latest]
    solved, presses, err = False, 0, None
    try:
        for _ in range(budget):
            act = agent.choose_action(frames, latest)
            fr = agent.take_action(act)
            presses += 1
            if fr is None:
                continue
            frames.append(fr); latest = fr
            if len(frames) > 4:
                frames = frames[-4:]
            if fr.levels_completed > 0 or fr.state == GameState.WIN:
                solved = True
                break
        if solved:
            try:
                m.act(latest)    # let her look back over the level she just won
            except Exception:
                pass
    except Exception:
        import traceback; err = traceback.format_exc()[-400:]
    b = base[level] if level < nlev else None
    score = min(115.0, (b / presses) ** 2 * 100) if solved and b else 0.0
    win = None
    if solved and getattr(m, "wins", None):
        w = m.wins[-1]
        win = dict(spent=presses, shortest=w["shortest"], route=w.get("route"),
                   kinds={str(k): v for k, v in (w.get("kinds") or {}).items()}, goal=w.get("goal"), mean_run=w.get("mean_run"))
    return dict(game=game, level=level, n_levels=nlev, seed=seed, solved=solved, presses=presses, baseline=b,
                score=round(score, 3), win=win, seconds=round(time.time() - t0, 1), error=err, warm=bool(warm),
                rungs=dict(getattr(m, "goal_log", {}) or {}))


def win_event_of(entry):
    """Replay a casebook route from its level start; return what the winning press did (the specific rung
    a student carries into the next level), or None if the route does not reproduce the win."""
    import numpy as np
    from arc_agi import Arcade, OperationMode
    from arcengine import ActionInput, GameAction
    from mika3.explorer2 import Mind
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=harness.ENV_DIR, logger=logging.getLogger("q"))
    card = arcade.open_scorecard()
    env = arcade.make(entry["game"], scorecard_id=card)
    g = env._game
    if entry["level"] > 0:
        g.set_level(entry["level"])
    g._action_count = 1
    f = np.array(g.camera.render(g.current_level.get_sprites()), dtype=np.int16)
    for a, xy, kind in entry["route"]:
        data = {"x": int(xy[0]), "y": int(xy[1])} if (a == 6 and xy is not None) else {}
        r = g.perform_action(ActionInput(id=GameAction.from_id(a), data=data), raw=True)
        won = r.levels_completed > 0 or str(r.state).endswith("WIN")
        if won:
            fe = np.array(r.frame[-2] if (len(r.frame) > 1 and not str(r.state).endswith("WIN")) else r.frame[-1], dtype=np.int16)
            col = int(f[int(xy[1]), int(xy[0])]) if (a == 6 and xy is not None) else None
            eff = Mind.effects(f, fe, f != fe)
            f0n = np.array(r.frame[0], dtype=np.int16) if r.frame else fe
            mom = Mind.moment_key(f, f0n)
            temps = [T.tolist() for T in Mind.before_templates(f, f0n)]
            return dict(act=a, col=col, eff=[[k, list(b), list(c)] for k, b, c in sorted(eff)], moment=mom, templates=temps)
        if r.frame:
            f = np.array(r.frame[-1], dtype=np.int16)
    return None


def n_levels(game):
    import json as _j
    g, v = game.split("-")
    return len(_j.load(open(os.path.join(harness.ENV_DIR, g, v, "metadata.json")))["baseline_actions"])


def casebook_from(frontier):
    """Intake: every level won on the frontier, oriented to the school (department, route anatomy)."""
    from mika3.university import PUBLIC_DEPT
    book = {}
    for r in frontier:
        if not r["solved"] or not r.get("win"):
            continue
        key = f"{r['game'][:4]}:{r['level']}"
        w = r["win"]
        route = w.get("route") or []
        runs = 1 + sum(1 for x, y in zip(route, route[1:]) if (x[0], x[2]) != (y[0], y[2])) if route else 0
        cur = book.get(key)
        cand = dict(game=r["game"], level=r["level"], dept=PUBLIC_DEPT.get(r["game"][:4]), baseline=r["baseline"],
                    frontier_presses=r["presses"], shortest=w["shortest"], route=route, kinds=w.get("kinds"),
                    goal=w.get("goal"), mean_run=(len(route) / runs) if runs else None,
                    clicks=sum(1 for c in route if c[0] == 6), final=route[-1][0] if route else None)
        if cur is None or cand["shortest"] < cur["shortest"]:
            book[key] = cand
    return book


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["frontier", "exam"])
    ap.add_argument("spec")
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--casebook", default="")
    ap.add_argument("--mode", default="cold", choices=["cold", "warm"])
    ap.add_argument("--games", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    games = [g for g in harness.all_games() if not a.games or g[:4] in a.games.split(",")]
    jobs = []
    if a.what == "frontier":
        for s in range(a.seeds):
            for g in games:
                for lv in range(n_levels(g)):
                    jobs.append((a.spec, g, lv, a.budget, 100 + s, None))
    else:
        book = json.load(open(a.casebook))
        wev = {}
        if a.mode == "warm":
            for key, c in book.items():
                try:
                    wev[key] = win_event_of(c)
                except Exception:
                    wev[key] = None
            print(f"win events: {sum(1 for v in wev.values() if v and v['eff'])} of {len(wev)} routes carry one")
        for s in range(a.seeds):
            for key, c in sorted(book.items()):
                if a.games and key[:4] not in a.games.split(","):
                    continue
                warm = None
                if a.mode == "warm" and c["level"] > 0:
                    prev = book.get(f"{key[:4]}:{c['level'] - 1}")
                    if prev is None:
                        continue          # warm exam needs the previous level inside the school
                    warm = dict(kinds=prev.get("kinds") or {}, goal=prev.get("goal"), route=prev.get("route") or [],
                                win_event=wev.get(f"{key[:4]}:{c['level'] - 1}"),
                                win_moment=(wev.get(f"{key[:4]}:{c['level'] - 1}") or {}).get("moment"),
                                win_templates=(wev.get(f"{key[:4]}:{c['level'] - 1}") or {}).get("templates"))
                jobs.append((a.spec, c["game"], c["level"], a.budget, s, warm))
    jobs.sort(key=lambda j: -j[3])
    t = time.time()
    with Pool(a.workers) as pool:
        res = pool.map(play_level, jobs, chunksize=1)
    json.dump(res, open(a.out, "w"))
    solved = sum(r["solved"] for r in res)
    print(f"{a.what}: {len(res)} level runs, {solved} won, mean level score {sum(r['score'] for r in res) / max(1, len(res)):.2f}, "
          f"{time.time() - t:.0f}s")
    if a.what == "frontier":
        book = casebook_from(res)
        json.dump(book, open(a.out.replace(".json", "_casebook.json"), "w"), indent=1)
        print(f"casebook: {len(book)} levels inside the school")
