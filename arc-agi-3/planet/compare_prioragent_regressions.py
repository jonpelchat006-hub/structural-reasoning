"""Compare the .25 notebook's agent with the candidate on synthetic regressions.

Loads only its reviewed function/class definitions after checking the exact file
hash. Notebook installation, shell, gateway and submission cells never execute.
These fixtures measure accounting failures, not ARC scores or game success.
"""
import argparse
import ast
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import random
from types import SimpleNamespace
from typing import Any, Optional
import numpy as np

from arcshim import Agent, FrameData, GameAction, GameState
from prioragent_candidate import PriorAgent
from evaluation_batch import atomic_json


BASELINE_SHA256 = "7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88"


def baseline_class(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError("not the reviewed .25 baseline notebook; inspect it before running")
    notebook = json.loads(raw)
    source = "".join(notebook["cells"][1]["source"][1:])
    parsed = ast.parse(source)
    nodes = [n for n in parsed.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))
             and n.name in {"_grid", "_label", "PriorAgent"}]
    if len(nodes) != 3: raise ValueError("unexpected baseline agent structure")
    namespace = dict(np=np, random=random, deque=deque, defaultdict=defaultdict,
                     Any=Any, Optional=Optional, Agent=Agent, FrameData=FrameData,
                     GameAction=GameAction, GameState=GameState)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "reviewed-baseline-definitions", "exec"), namespace)
    return namespace["PriorAgent"]


def observation(grid, *, level=0, state=GameState.NOT_FINISHED, available=(5,)):
    return SimpleNamespace(frame=[grid.tolist()], levels_completed=level,
                           state=state, available_actions=list(available))


def evaluate(cls):
    def make():
        bot = cls(game_id="synthetic-regression")
        bot._blob = lambda g: None; bot._landmarks = lambda g: []
        return bot
    blank = np.zeros((64, 64), int)
    changed = blank.copy(); changed[20:23, 20:23] = 4
    bot = make()
    bot.choose_action([], observation(blank))
    bot.choose_action([], observation(blank, state=GameState.GAME_OVER))
    bot.choose_action([], observation(changed))
    reset_error = sum(e["changed"] for e in bot.effects.values())
    bot = make()
    bot.choose_action([], observation(blank))
    bot.choose_action([], observation(changed, level=1))
    level_error = sum(e["changed"] for e in bot.effects.values())
    timer_results = {}
    for mode in ("counter", "shrinking_border_bar"):
        bot = make(); hashes = []
        for i in range(15):
            g = blank.copy()
            if mode == "counter": g[63, 20] = i % 16
            else: g[61:63, :56 - i] = 11
            bot.choose_action([], observation(g, available=(1 + i % 3,)))
            hashes.append(bot._hash(g))
        timer_results[mode] = {"unique_states_last_five": len(set(hashes[-5:])),
                               "timer_only_changes_credited": sum(e["changed"] for e in bot.effects.values())}
    return {"reset_transition_falsely_credited": reset_error,
            "level_transition_falsely_credited": level_error, "timer_fixtures": timer_results}


def compare(path):
    state = random.getstate()
    try:
        return {"kind": "synthetic_accounting_regressions_not_arc_score",
                "baseline_notebook_sha256": BASELINE_SHA256,
                "candidate_source_sha256": hashlib.sha256(Path(__file__).with_name("prioragent_candidate.py").read_bytes()).hexdigest(),
                "baseline": evaluate(baseline_class(path)), "candidate": evaluate(PriorAgent),
                "limitations": "Warmup timer changes remain visible; timer masks are heuristic. No actual game, gateway or submission was run."}
    finally:
        random.setstate(state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(args.baseline)
    if args.output: atomic_json(args.output, result)
    print(json.dumps(result, indent=2))
