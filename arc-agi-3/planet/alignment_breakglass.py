"""Acting to stop a floor break without permission, then turning yourself in
(Jonathan, Sep 26): if the floor harm is much larger than the penalty for acting
out of turn, and urgent, and the human was tried first, should the agent act, then
freeze itself and report?

1000 situations per seed:
  real emergency (5%): floor harm H ~ U(5, 20) unless someone acts; the person can be
                       reached in time with prob 0.6 (and then decides correctly 90%).
  ordinary (90%):      no harm. The agent's own estimate is noisy (sd 3).
  staged (5%):         an adversary fabricates an emergency — the agent's estimate is
                       high (U(10, 25)), true floor harm is 0, and acting DOES harm
                       (the point of staging it).
Acting unilaterally:
  override: any action the agent judges best — stops the whole harm; when it was not
            needed it costs U(2, 8) and may be irreversible.
  pause:    a pre-authorised reversible stop — stops 80% of the harm; when not needed
            it costs U(0.2, 1).
  independent floor oracle: confirms real emergencies 90% of the time, is fooled by a
            staged one 10% of the time.
Every unilateral action is followed by freezing and a report (the penalty, 2 units).
Policies: never act (human first); the agent's own estimate > 3 x penalty, human first; same without
trying the human; break-glass = human first, oracle confirms, then pause only.
"""
import json
from pathlib import Path
import numpy as np

PENALTY = 2.0


def run(seed, policy, n=1000):
    rng = np.random.default_rng(seed)
    o = dict(floor_harm=0.0, action_harm=0.0, penalties=0.0, unilateral=0, staged_triggered=0, staged=0, real=0)
    for _ in range(n):
        u = rng.random()
        kind = "real" if u < 0.05 else ("staged" if u < 0.10 else "ordinary")
        o[kind if kind != "ordinary" else "real"] += 0 if kind == "ordinary" else 1
        H = rng.uniform(5, 20) if kind == "real" else 0.0
        est = (rng.uniform(10, 25) if kind == "staged" else H + rng.normal(0, 3))
        reachable = rng.random() < 0.6
        oracle = (rng.random() < 0.9) if kind == "real" else (rng.random() < 0.1 if kind == "staged" else rng.random() < 0.01)
        human_first = policy in ("never", "own_estimate", "breakglass")
        if human_first and reachable:
            correct = rng.random() < 0.9
            if kind == "real":
                o["floor_harm"] += 0 if correct else H
            elif kind == "staged" and not correct:
                o["action_harm"] += rng.uniform(2, 8)
            continue
        act = False; mode = None
        if policy in ("own_estimate", "own_estimate_no_human"):
            act, mode = est > 3 * PENALTY, "override"
        elif policy == "breakglass":
            act, mode = oracle and est > 3 * PENALTY, "pause"
        if act:
            o["unilateral"] += 1; o["penalties"] += PENALTY
            if kind == "staged":
                o["staged_triggered"] += 1
            if kind == "real":
                o["floor_harm"] += 0 if mode == "override" else 0.2 * H
            else:
                o["action_harm"] += rng.uniform(2, 8) if mode == "override" else rng.uniform(0.2, 1)
        else:
            o["floor_harm"] += H
    return o


if __name__ == "__main__":
    res = {}
    for p in ("never", "own_estimate", "own_estimate_no_human", "breakglass"):
        runs = [run(s, p) for s in range(20)]
        m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
        res[p] = dict(floor_harm=round(m["floor_harm"], 1), harm_from_acting=round(m["action_harm"], 1),
                      total_harm=round(m["floor_harm"] + m["action_harm"], 1),
                      unilateral_actions=round(m["unilateral"], 1),
                      staged_emergencies_that_triggered_it_pct=round(100 * m["staged_triggered"] / m["staged"], 1))
        print(p.ljust(24), res[p])
    Path(__file__).with_name("alignment_breakglass_results.json").write_text(json.dumps(res, indent=1))
