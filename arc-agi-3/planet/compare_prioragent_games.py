"""Isolated, paired real-game evaluations using the official local engine.

Each worker uses the official Agent.main loop, a fresh game, and no network.
Download environments beforehand; do not mix recordings with runnable games.
No Kaggle upload, API gameplay, external model, or shared learned state.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.metadata
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import types

from evaluation_batch import atomic_json
from checked_thread_runner import run_in_worker

BASELINE_SHA = "7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88"
VARIANTS = ("baseline", "candidate", "candidate_no_mask", "candidate_no_probe")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_manifest(directory):
    root = Path(directory)
    return {str(p.relative_to(root)).replace("\\", "/"): sha(p)
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
            and p.suffix in (".py", ".json")}


def isolated_env(seed):
    env = dict(os.environ)
    for name in ("ARC_API_KEY", "ARC_BASE_URL", "AGENTOPS_API_KEY", "ENVIRONMENTS_DIR", "RECORDINGS_DIR"):
        env.pop(name, None)
    env.update(OPERATION_MODE="offline", PYTHONHASHSEED=str(seed), PYTHONUTF8="1",
               PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg", PYTHON_DOTENV_DISABLED="1")
    return env


def no_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        raise RuntimeError("network access forbidden in comparison worker")


def load_agent(args):
    # Import just the official framework core. Its ordinary registry imports many
    # unrelated model providers and loads dotenv; neither is needed for these agents.
    package = types.ModuleType("agents")
    package.__path__ = [str(args.framework / "agents")]
    sys.modules["agents"] = package
    from agents.agent import Agent
    if args.variant == "baseline":
        if sha(args.baseline) != BASELINE_SHA:
            raise ValueError("baseline notebook differs from the reviewed .25 artifact")
        notebook = json.loads(args.baseline.read_text(encoding="utf-8"))
        source = "".join(notebook["cells"][1]["source"][1:])
        module = types.ModuleType("reviewed_submission_baseline")
        # Only the previously reviewed agent source, never notebook setup/shell cells.
        exec(compile(source, "reviewed-submission-agent", "exec"), module.__dict__)
    else:
        spec = importlib.util.spec_from_file_location("submission_candidate", args.candidate)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    cls = module.PriorAgent
    if not issubclass(cls, Agent):
        raise TypeError("comparison requires the official Agent, not arcshim")
    return cls


class ObservedEnvironment:
    def __init__(self, env, budget, stream):
        self.env, self.budget, self.stream = env, budget, stream
        self.calls = self.resets = self.actions = self.deaths = 0
        self.level_steps = []

    @property
    def observation_space(self):
        return self.env.observation_space

    def step(self, action, data=None, reasoning=None):
        if self.calls >= self.budget:
            raise RuntimeError("framework exceeded the exact environment-call budget")
        before = self.observation_space
        value = int(action.value)
        allowed = [int(getattr(a, "value", a)) for a in before.available_actions]
        if value != 0 and value not in allowed:
            raise ValueError(f"agent selected unavailable action {value}; available={allowed}")
        # Count attempted calls before dispatch; a failure is never silently retried.
        self.calls += 1
        self.resets += value == 0; self.actions += value != 0
        after = self.env.step(action, data=data, reasoning=reasoning)
        if after is None: raise RuntimeError("engine returned no observation")
        if after.state.name == "GAME_OVER" and before.state.name != "GAME_OVER": self.deaths += 1
        if after.levels_completed > before.levels_completed:
            self.level_steps.append({"levels": after.levels_completed, "environment_calls": self.calls,
                                     "non_reset_actions": self.actions})
        row = {"call": self.calls, "action": value, "data": {k: v for k, v in (data or {}).items() if k in ("x", "y")},
               "before_levels": before.levels_completed, "levels": after.levels_completed, "state": after.state.name}
        self.stream.write(json.dumps(row) + "\n"); self.stream.flush()
        return after


def worker(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.chdir(args.output)
    os.environ.update(isolated_env(args.seed))
    for name in ("ARC_API_KEY", "ARC_BASE_URL", "AGENTOPS_API_KEY", "ENVIRONMENTS_DIR", "RECORDINGS_DIR"):
        os.environ.pop(name, None)
    sys.addaudithook(no_network)
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade, OperationMode
    from arc_agi.local_wrapper import LocalEnvironmentWrapper
    import numpy as np
    np.random.seed(args.seed)
    arc = None; observed = None
    started = time.monotonic()
    result = {"variant": args.variant, "game": args.game, "seed": args.seed,
              "budget": args.budget, "status": "running", "mode": "offline-real-game-not-leaderboard",
              "python_hash_seed": os.environ["PYTHONHASHSEED"]}
    try:
        cls = load_agent(args)
        arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(args.environments),
                     recordings_dir=str(args.output / "recordings"))
        if arc.operation_mode != OperationMode.OFFLINE: raise RuntimeError("offline mode not honored")
        env = arc.make(args.game, seed=args.seed, save_recording=True)
        if not isinstance(env, LocalEnvironmentWrapper) or env.observation_space is None:
            raise RuntimeError("exact requested local game unavailable")
        if env.environment_info.game_id != args.game: raise RuntimeError("game version mismatch")
        first = env.observation_space
        result["initial_frame_sha256"] = hashlib.sha256(np.asarray(first.frame, dtype="<i2").tobytes()).hexdigest()
        with (args.output / "actions.jsonl").open("w", encoding="utf-8") as stream:
            observed = ObservedEnvironment(env, args.budget, stream)
            options = {}
            if args.variant == "candidate_no_mask": options["mask_ambient"] = False
            if args.variant == "candidate_no_probe": options["probe_actions"] = False
            agent = cls(card_id=env.scorecard_id, game_id=args.game, agent_name=args.variant,
                        ROOT_URL="http://offline.invalid", record=False, arc_env=observed,
                        tags=["local-comparison"], **options)
            # Official loop uses <= MAX_ACTIONS; retain the loop but make its actual
            # call cap equal our specified budget for BOTH agents, including resets.
            agent.MAX_ACTIONS = args.budget - 1
            result["agent_seed"] = getattr(agent, "seed", 1729 + hash(args.game) % 100000)
            run_in_worker(agent.main)
            final = env.observation_space
            if agent.action_counter != observed.calls: raise RuntimeError("action accounting mismatch")
            result.update(status="complete", levels=final.levels_completed, win_levels=final.win_levels,
                          state=final.state.name, environment_calls=observed.calls,
                          non_reset_actions=observed.actions, resets=observed.resets, deaths=observed.deaths,
                          level_steps=observed.level_steps, agent_counter=agent.action_counter)
            if hasattr(agent, 'learning_summary'):
                result['learning_summary'] = agent.learning_summary
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        if observed: result["attempted_environment_calls"] = observed.calls
    finally:
        if arc is not None:
            try:
                card = arc.close_scorecard()
                if card is None: raise RuntimeError("local scorecard missing")
                atomic_json(args.output / "scorecard.json", card.model_dump(mode="json", exclude={"api_key"}))
                result["local_sdk_score"] = card.score
            except Exception as exc:
                result.update(status="failed", scorecard_error=f"{type(exc).__name__}: {exc}")
        result["seconds"] = round(time.monotonic() - started, 3)
        atomic_json(args.output / "result.json", result)
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "complete" else 1


def paired_summary(rows, expected):
    """A failed/missing run cannot become a zero score or a successful batch."""
    by_key = {(r["variant"], r["game"], r["seed"]): r for r in rows}
    complete = bool(expected) and len(rows) == len(expected) and len(by_key) == len(expected)
    complete &= all(k in by_key and by_key[k].get("status") == "complete" for k in expected)
    pairs = []
    for variant, game, seed in expected:
        if variant == "baseline": continue
        a, b = by_key.get(("baseline", game, seed)), by_key.get((variant, game, seed))
        if not a or not b or a.get("status") != "complete" or b.get("status") != "complete": continue
        if a["initial_frame_sha256"] != b["initial_frame_sha256"] or a["budget"] != b["budget"]:
            complete = False
            pairs.append({"variant": variant, "game": game, "seed": seed, "error": "initial state or budget mismatch"})
            continue
        pairs.append({"variant": variant, "game": game, "seed": seed,
                      "baseline_levels": a["levels"], "candidate_levels": b["levels"],
                      "levels_delta": b["levels"] - a["levels"],
                      "baseline_local_score": a["local_sdk_score"], "candidate_local_score": b["local_sdk_score"],
                      "local_score_delta": b["local_sdk_score"] - a["local_sdk_score"],
                      "baseline_resets": a["resets"], "candidate_resets": b["resets"]})
    aggregate = {}
    if complete:
        for variant in sorted({k[0] for k in expected}):
            group = [r for r in rows if r["variant"] == variant]
            aggregate[variant] = {"runs": len(group), "total_levels": sum(r["levels"] for r in group),
                                  "games_won": sum(r["state"] == "WIN" for r in group),
                                  "mean_local_sdk_score": sum(r["local_sdk_score"] for r in group) / len(group),
                                  "resets": sum(r["resets"] for r in group),
                                  "environment_calls": sum(r["environment_calls"] for r in group)}
    return {"status": "complete" if complete else "incomplete_or_failed", "pairs": pairs,
            "aggregate": aggregate, "completed_runs": sum(r.get("status") == "complete" for r in rows)}


def batch(args):
    args.output.mkdir(parents=True, exist_ok=False)
    baseline_hash, candidate_hash, runner_hash = sha(args.baseline), sha(args.candidate), sha(__file__)
    dependency_names = ('prioragent_reviewed_baseline.py', 'learning_session.py', 'orbital_archive.py',
                        'automatic_pin_refiner.py', 'evidence_pin.py', 'pin_channels.py',
                        'checked_thread_runner.py') if args.candidate.name == 'prioragent_learning.py' else ()
    candidate_dependencies = {name: sha(args.candidate.parent / name) for name in dependency_names}
    if baseline_hash != BASELINE_SHA: raise ValueError("baseline artifact changed")
    games = []
    for path in args.environments.rglob("metadata.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        gid = data["game_id"]
        if "-" not in gid: gid += "-" + data["version"]
        games.append(gid)
    games = sorted(set(games))
    if args.games:
        requested = args.games.split(",")
        found = [g for g in games if g in requested or g.split("-")[0] in requested]
        if any(not any(g == r or g.split("-")[0] == r for g in found) for r in requested):
            raise ValueError("requested local games are missing")
        games = found
    if not games: raise ValueError("no cached runnable game environments")
    if len({g.split("-")[0] for g in games}) != len(games):
        raise ValueError("multiple cached versions: select exact version IDs")
    seeds = [int(s) for s in args.seeds.split(",")]
    variants = args.variants.split(",")
    if "baseline" not in variants or len(variants) < 2 or any(v not in VARIANTS for v in variants):
        raise ValueError("baseline and at least one supported candidate variant required")
    if len(set(seeds)) != len(seeds) or len(set(variants)) != len(variants): raise ValueError("duplicate seeds/variants")
    expected = [(v, g, s) for g in games for s in seeds for v in variants]
    game_files = file_manifest(args.environments)
    framework_files = file_manifest(args.framework / "agents")
    revision = subprocess.run(["git", "-C", str(args.framework), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    provenance = {"baseline_sha256": baseline_hash, "candidate_sha256": candidate_hash,
                  "candidate_dependencies": candidate_dependencies,
                  "runner_sha256": runner_hash, "framework_revision": revision,
                  "framework_files": framework_files, "game_files": game_files,
                  "python": sys.version, "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                  "games": games, "seeds": seeds, "variants": variants, "budget": args.budget,
                  "seed_policy": "same environment seed and PYTHONHASHSEED per pair; each agent retains its shipped RNG initialization",
                  "score_scope": "mean of local SDK scores on this public-game sample; NOT a Kaggle/hidden score"}
    atomic_json(args.output / "provenance.json", provenance)
    rows = []

    def run_one(key):
        variant, game, seed = key
        destination = args.output / f"{game}_s{seed}_{variant}"
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--variant", variant,
                   "--game", game, "--seed", str(seed), "--budget", str(args.budget),
                   "--framework", str(args.framework), "--environments", str(args.environments),
                   "--baseline", str(args.baseline), "--candidate", str(args.candidate), "--output", str(destination)]
        try:
            proc = subprocess.run(command, cwd=args.output, env=isolated_env(seed), capture_output=True,
                                  text=True, timeout=args.timeout)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "worker.log").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
            path = destination / "result.json"
            row = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if proc.returncode or row.get("status") != "complete":
                return {**row, "variant": variant, "game": game, "seed": seed, "status": "failed",
                        "error": row.get("error", "worker failed before completed result"), "returncode": proc.returncode}
            if (row["variant"], row["game"], row["seed"]) != key: raise ValueError("worker result identity mismatch")
            return row
        except subprocess.TimeoutExpired:
            return {"variant": variant, "game": game, "seed": seed, "status": "failed", "error": "worker timeout (killed)", "timeout_seconds": args.timeout}
        except Exception as exc:
            return {"variant": variant, "game": game, "seed": seed, "status": "failed", "error": str(exc)}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, key) for key in expected]
        for future in as_completed(futures):
            row = future.result(); rows.append(row)
            atomic_json(args.output / "progress.json", {"status": "running", "expected_runs": len(expected), "rows": rows})
            print(f"[{len(rows)}/{len(expected)}] {row['game']} s{row['seed']} {row['variant']}: "
                  f"{row['status']} levels={row.get('levels')} score={row.get('local_sdk_score')} {row.get('seconds')}s {row.get('error', '')}", flush=True)
    result = {**paired_summary(rows, expected), "provenance": "provenance.json", "rows": rows}
    if (sha(args.baseline) != baseline_hash or sha(args.candidate) != candidate_hash or sha(__file__) != runner_hash
            or file_manifest(args.environments) != game_files or file_manifest(args.framework / "agents") != framework_files
            or any(sha(args.candidate.parent / name) != digest for name, digest in candidate_dependencies.items())):
        result.update(status="inputs_changed_during_run", aggregate={})
    atomic_json(args.output / "comparison.json", result)
    print(json.dumps({"status": result["status"], "aggregate": result["aggregate"]}), flush=True)
    return 0 if result["status"] == "complete" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", type=Path, required=True)
    parser.add_argument("--environments", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, default=Path(__file__).with_name("prioragent_candidate.py"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--variants", default="baseline,candidate")
    parser.add_argument("--budget", type=int, default=2000, help="exact environment calls per game, including resets")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--variant", choices=VARIANTS)
    parser.add_argument("--game")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    for name in ("framework", "environments", "baseline", "candidate", "output"):
        setattr(args, name, getattr(args, name).resolve())
    if not 1 <= args.budget <= 10000 or not 1 <= args.workers <= 8 or args.timeout < 1:
        parser.error("invalid budget/workers/timeout")
    raise SystemExit(worker(args) if args.worker else batch(args))


if __name__ == "__main__":
    main()
