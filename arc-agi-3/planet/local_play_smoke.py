"""Exercise the real play loop against an injected local mock, never the API.

This is an integration smoke test, not an ARC benchmark or leaderboard score.
"""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from arc3_client import MockGame


class MockTransport:
    def __init__(self, seed=0):
        self.game, self.calls = MockGame(seed), []
        self.card_id = "local-smoke-" + uuid4().hex

    def __call__(self, path, key, body=None, method=None):
        self.calls.append(path)
        if path == "/api/scorecard/open": return {"card_id": self.card_id}
        if path == "/api/scorecard/close":
            return {"mode": "local-mock-not-official", "card_id": self.card_id,
                    "environment_actions": sum(p.startswith("/api/cmd/ACTION") for p in self.calls), "environments": []}
        if not path.startswith("/api/cmd/"): raise ValueError(f"unsupported mock endpoint: {path}")
        action = path.rsplit("/", 1)[-1]
        frame = self.game.frame() if action == "RESET" else self.game.act(action, body.get("x"), body.get("y"))
        return {**frame, "levels_completed": int(frame["state"] == "WIN"), "win_levels": 1,
                "available_actions": [1, 2, 3, 4]}


def run(output_dir, presses=16, seed=7, device="cpu"):
    import torch
    import play
    torch.set_num_threads(1)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    transport = MockTransport(seed)
    with (output_dir / "smoke.log").open("w", encoding="utf-8") as log:
        def record(line):
            log.write(line + "\n"); log.flush()
        result = play.play_game("mock-local", "", presses=presses, device=device, use_prior=False,
                                transport=transport, output_dir=output_dir, seed=seed, log=record)
    result["scope"] = "local mock integration only; not an ARC-AGI-3 score"
    result["transport_actions"] = sum(p.startswith("/api/cmd/ACTION") for p in transport.calls)
    from evaluation_batch import atomic_json
    atomic_json(output_dir / "smoke_result.json", result)
    print(json.dumps({k: result[k] for k in ("scope", "presses", "transport_actions", "levels", "seconds", "scorecard_file")}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--presses", type=int, default=16)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    if not 1 <= args.presses <= 100: parser.error("smoke presses must be between 1 and 100")
    run(args.output_dir, args.presses, args.seed, args.device)
