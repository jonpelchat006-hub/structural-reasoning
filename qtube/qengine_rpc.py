"""JSONL worker for the public ARC-AGI-3 OFFLINE engine.

Run with arc3/venv/Scripts/python.exe. The first line is a ready observation;
subsequent requests are {"action": 0..7, "data": {}} or
{"command": "score" | "close"}. Only public observations cross this boundary.
The make() call performs the initial reset; it is not repeated or included in
actions_sent. Official action/reset accounting remains the engine's own.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import traceback
from typing import Any


DEFAULT_ENVIRONMENTS = Path(r"D:\planet\arc3\data\environment_files")


def observation(response: Any) -> dict[str, Any]:
    if response is None:
        raise RuntimeError("The offline engine returned no observation; state may have changed")
    frames = [frame.tolist() if hasattr(frame, "tolist") else frame for frame in response.frame]
    if not frames:
        raise RuntimeError("The offline engine returned no frames")
    for frame in frames:
        if len(frame) != 64 or any(len(row) != 64 for row in frame):
            raise RuntimeError("Expected 64x64 public observation frames")
    return {
        "frame": frames[-1],
        "frames": frames,
        "state": response.state.name,
        "levels_completed": int(response.levels_completed),
        "win_levels": int(response.win_levels),
        "available_actions": [int(action) for action in response.available_actions],
        "guid": str(response.guid or ""),
        "full_reset": bool(response.full_reset),
    }


def choose_game(arcade: Any, requested: str) -> str:
    # get_environments() in OFFLINE mode uses local metadata only. Do not use
    # titles, tags, baselines, game source, or internal engine/game objects.
    game_ids = sorted({env.game_id for env in arcade.get_environments()})
    if requested in game_ids:
        return requested
    matches = [game_id for game_id in game_ids if game_id.startswith(requested)]
    if not matches:
        raise ValueError(f"No locally installed game matches {requested!r}")
    if len({game_id.split("-", 1)[0] for game_id in matches}) > 1:
        raise ValueError(f"Game prefix {requested!r} is ambiguous: {', '.join(matches)}")
    return matches[-1]


def score_data(card: Any) -> dict[str, Any]:
    if card is None:
        raise RuntimeError("The official engine returned no scorecard")
    return card.model_dump(mode="json", exclude={"api_key"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, help="Installed game prefix or full ID")
    parser.add_argument("--environments-dir", type=Path, default=DEFAULT_ENVIRONMENTS)
    args = parser.parse_args()

    # Redirect before importing arc_agi: some package loggers capture sys.stdout
    # at import time. Protocol output alone retains the original stream.
    protocol_output = sys.stdout
    sys.stdout = sys.stderr

    def emit(message: dict[str, Any]) -> None:
        protocol_output.write(json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n")
        protocol_output.flush()

    def error(exc: Exception, phase: str, *, state_uncertain: bool = False) -> None:
        traceback.print_exc(file=sys.stderr)
        emit({
            "ok": False,
            "ready": False if phase == "initialize" else True,
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "phase": phase,
            "state_uncertain": state_uncertain,
        })

    # COMPETITION overrides even an explicit OFFLINE constructor in this SDK.
    # Change only this worker's environment, before constructing the arcade.
    os.environ["OPERATION_MODE"] = "offline"
    os.environ.pop("ONLY_RESET_LEVELS", None)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    logger = logging.getLogger("qtube.offline_engine")
    arcade = None
    card_id = None
    closed = False
    try:
        from arc_agi import Arcade, OperationMode
        from arcengine import GameAction

        directory = args.environments_dir.resolve()
        if not directory.is_dir():
            raise ValueError(f"Environment directory does not exist: {directory}")
        if not args.game.strip():
            raise ValueError("--game must be a nonempty prefix or full ID")
        arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(directory),
            logger=logger,
        )
        if arcade.operation_mode != OperationMode.OFFLINE:
            raise RuntimeError("Refusing to run outside OFFLINE mode")
        game_id = choose_game(arcade, args.game.strip())
        card_id = arcade.open_scorecard()
        env = arcade.make(game_id, scorecard_id=card_id, save_recording=False)
        if env is None:
            raise RuntimeError(f"Failed to make local game {game_id}")
        initial = observation(env.observation_space)
        actions_sent = 0
        # make()'s full reset opens a run with zero scored actions in this SDK.
        emit({
            "ok": True,
            "ready": True,
            "game_id": game_id,
            "initial_reset": True,
            "initial_reset_counted": False,
            "actions_sent": actions_sent,
            **initial,
        })
    except Exception as exc:
        error(exc, "initialize")
        if arcade is not None and card_id is not None:
            try:
                arcade.close_scorecard(card_id)
            except Exception:
                traceback.print_exc(file=sys.stderr)
        return 1

    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            phase = "request"
            state_uncertain = False
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("Each request must be a JSON object")
                command = request.get("command", request.get("cmd"))
                if command is not None:
                    if "action" in request:
                        raise ValueError("Specify a command or an action, not both")
                    if command not in ("score", "close"):
                        raise ValueError("Supported commands are 'score' and 'close'")
                    phase = command
                    if command == "close":
                        card = arcade.close_scorecard(card_id)
                        closed = True
                    else:
                        card = arcade.get_scorecard(card_id)
                    emit({
                        "ok": True,
                        "game_id": game_id,
                        "command": command,
                        "closed": closed,
                        "actions_sent": actions_sent,
                        "scorecard": score_data(card),
                    })
                    if closed:
                        break
                    continue
                action_id = request.get("action")
                if type(action_id) is not int or not 0 <= action_id <= 7:
                    raise ValueError("action must be an integer from 0 through 7")
                data = request.get("data", {})
                if not isinstance(data, dict):
                    raise ValueError("data must be a JSON object")
                action = GameAction.from_id(action_id)
                action.validate_data(data)
                phase = "step"
                state_uncertain = True
                actions_sent += 1
                result = observation(env.step(action, data=data))
                state_uncertain = False
                emit({"ok": True, "game_id": game_id, "actions_sent": actions_sent, **result})
            except Exception as exc:
                error(exc, phase, state_uncertain=state_uncertain)
                if closed:
                    return 1
    finally:
        # EOF and client disconnect release the in-memory scorecard. No extra
        # response is emitted on EOF, preserving one reply per request.
        if not closed:
            try:
                arcade.close_scorecard(card_id)
            except Exception:
                traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
