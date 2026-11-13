"""Download public game environments once; never perform online gameplay.

Uses an anonymous key internally, never prints it. Existing caches are inspected
only, not refreshed in place. Use a new root for another game-version snapshot.
"""
import argparse
import json
import logging
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    environments = root / "environments"
    cached = list(environments.rglob("metadata.json"))
    if cached:
        print(json.dumps({"status": "existing_cache_unchanged", "games": len(cached), "path": str(environments)}))
        return
    os.environ.update(OPERATION_MODE="normal", PYTHON_DOTENV_DISABLED="1")
    for name in ("ARC_API_KEY", "ARC_BASE_URL", "ENVIRONMENTS_DIR", "RECORDINGS_DIR"):
        os.environ.pop(name, None)
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade, OperationMode
    from arc_agi.local_wrapper import LocalEnvironmentWrapper
    from evaluation_batch import atomic_json
    arc = Arcade(operation_mode=OperationMode.NORMAL, environments_dir=str(environments),
                 recordings_dir=str(root / "bootstrap"))
    if arc.operation_mode != OperationMode.NORMAL: raise RuntimeError("download/local mode not honored")
    games = sorted(e.game_id for e in arc.get_environments())
    results = []
    try:
        for game in games:
            env = arc.make(game)
            ok = isinstance(env, LocalEnvironmentWrapper) and env.observation_space is not None
            results.append({"game": game, "downloaded": ok})
            print(f"{'cached' if ok else 'FAILED'} {game}", flush=True)
    finally:
        arc.close_scorecard()
    complete = bool(results) and all(r["downloaded"] for r in results)
    atomic_json(root / "download_manifest.json", {"status": "complete" if complete else "failed", "games": results})
    if not complete: raise SystemExit("Some games were unavailable; partial cache was retained, not scored.")


if __name__ == "__main__": main()
