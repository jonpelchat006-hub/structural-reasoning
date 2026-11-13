"""Offline ARC-AGI-3 harness: play an Agent class on the public games with the official engine and
the official scorecard (arc_agi.Arcade in OFFLINE mode), one fresh scorecard per game.

  ./venv/bin/python harness.py MODULE:CLASS [--games ls20,sp80] [--max-actions N] [--workers 2] [--out f.json]

Scoring is the package's own: per level min((baseline/actions)^2 * 100, 115), level k weighted by k,
unfinished levels count 0, game score = weighted mean, total = mean over games. RESETs count as actions.
RESET keeps the level after the first action (engine default), as in the competition."""
import argparse, importlib, json, logging, os, sys, time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_DIR = os.path.join(ROOT, "data", "environment_files")
sys.path.insert(0, os.path.join(ROOT, "fw"))
# the engine default already keeps the level on RESET once an action was taken (ONLY_RESET_LEVELS would
# also turn the first reset into a level reset, and then the scorecard never opens a play)
os.environ.pop("ONLY_RESET_LEVELS", None)
logging.disable(logging.CRITICAL)


def all_games():
    out = []
    for g in sorted(os.listdir(ENV_DIR)):
        for v in os.listdir(os.path.join(ENV_DIR, g)):
            out.append(f"{g}-{v}")
    return out


def load_class(spec):
    mod, cls = spec.split(":")
    if mod.endswith(".py"):
        spec_ = importlib.util.spec_from_file_location(os.path.basename(mod)[:-3], mod)
        m = importlib.util.module_from_spec(spec_); sys.modules[spec_.name] = m; spec_.loader.exec_module(m)
    else:
        m = importlib.import_module(mod)
    return getattr(m, cls)


def play(args):
    spec, game, max_actions, extra = args[:4]
    seed = args[4] if len(args) > 4 else None
    import arc_agi
    from arc_agi import Arcade, OperationMode
    t0 = time.time()
    cls = load_class(spec)
    if max_actions: cls.MAX_ACTIONS = max_actions
    if seed is not None: cls.SEED = seed
    arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=ENV_DIR,
                    logger=logging.getLogger("quiet"))
    card = arcade.open_scorecard()
    env = arcade.make(game, scorecard_id=card)
    agent = cls(card_id=card, game_id=game, agent_name=spec, ROOT_URL="", record=False, arc_env=env, **(extra or {}))
    err = None
    try:
        agent.main()
    except Exception as e:  # an agent crash scores what it had
        import traceback; err = traceback.format_exc()[-600:]
    wins = None
    try:
        wins = [dict(w, kinds={str(k): v for k, v in w.get("kinds", {}).items()}) for w in getattr(agent.mind, "wins", [])]
    except Exception:
        pass
    route_data = getattr(getattr(agent, "mind", None), "route_data", None)
    sc = arcade.get_scorecard(card)
    env_scores = sc.environments[0].runs if sc.environments else []
    best = max(env_scores, key=lambda r: r.score) if env_scores else None
    return dict(game=game, score=best.score if best else 0.0, levels=best.levels_completed if best else 0,
                n_levels=len(best.level_scores) if best and best.level_scores else 0,
                actions=sum(r.actions for r in env_scores), resets=sum((r.resets or 0) for r in env_scores),
                level_actions=best.level_actions if best else None,
                level_baseline=best.level_baseline_actions if best else None,
                level_scores=[round(x, 2) for x in best.level_scores] if best and best.level_scores else None,
                seconds=round(time.time() - t0, 1), error=err, seed=seed, wins=wins,
                route_data=route_data or None)


def run(spec, games=None, max_actions=None, workers=2, extra=None, seeds=1):
    games = games or all_games()
    jobs = [(spec, g, max_actions, extra, s) for s in range(seeds) for g in games]
    with Pool(workers) as pool:
        res = pool.map(play, jobs, chunksize=1)
    return res


def report(res):
    seeds = sorted(set(r.get("seed") or 0 for r in res))
    if len(seeds) > 1:
        import statistics
        per = {}
        for r in res: per.setdefault(r["game"], []).append(r)
        for g in sorted(per):
            rs = per[g]
            print(f"{g[:4]}  mean score {statistics.mean(x['score'] for x in rs):6.2f}  levels {[x['levels'] for x in rs]}  L1 actions {[x['level_actions'][0] if x['levels'] else None for x in rs]}")
        tots = [sum(r["score"] for r in res if (r.get("seed") or 0) == s) / max(1, len(per)) for s in seeds]
        lv = [sum(r["levels"] for r in res if (r.get("seed") or 0) == s) for s in seeds]
        print(f"TOTAL mean {statistics.mean(tots):.3f}  per seed {[round(t, 3) for t in tots]}  levels per seed {lv}")
        return statistics.mean(tots)
    tot = sum(r["score"] for r in res) / max(1, len(res))
    for r in sorted(res, key=lambda r: r["game"]):
        print(f"{r['game'][:4]}  score {r['score']:6.2f}  levels {r['levels']}/{r['n_levels']}  actions {r['actions']:5d}"
              f"  resets {r['resets']:3d}  {r['seconds']:6.1f}s  {('ERR ' + r['error'].splitlines()[-1][:60]) if r['error'] else ''}")
    lv = sum(r["levels"] for r in res); nl = sum(r["n_levels"] for r in res)
    print(f"TOTAL score {tot:.3f}   levels {lv}/{nl}   games with a level {sum(r['levels'] > 0 for r in res)}/{len(res)}")
    return tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--games", default="")
    ap.add_argument("--max-actions", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="")
    ap.add_argument("--seeds", type=int, default=1)
    a = ap.parse_args()
    games = [g for g in all_games() if not a.games or g[:4] in a.games.split(",")]
    res = run(a.agent, games, a.max_actions or None, a.workers, seeds=a.seeds)
    report(res)
    if a.out: json.dump(res, open(a.out, "w"), indent=1)
