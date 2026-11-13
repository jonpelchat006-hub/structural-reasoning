"""Guardrails around emergency areas, and protecting what attracts the fakes
(Jonathan, Sep 27).

A path with a fence at the edge. People fall (accidents) — more where the fence has a
hole. Near some spots there is 'gold' (something valuable to steal); thieves stage a
dramatic fall over the fence to reach it. Crossing a fence takes effort, so a crossing
is more suspicious — but some people genuinely tripped.
40 spots over 300 periods, 20 seeds. 6 spots have gold. Each spot's fence starts with a
hole with prob 0.3 (accidents 3x more likely there).
Policies:
  no_fence       : accidents at 3%, thieves take gold freely
  fence          : a fence everywhere; accidents 0.5% (1.5% through a hole); a thief
                   gets through 40% of attempts
  fence+search   : every crosser is searched (catches a thief 90%) — and every innocent
                   faller is searched too (the privacy line crossed)
  fence+inspect  : after any crossing, inspect the FENCE (a hole is found and fixed 90%)
                   and the GOLD (missing gold is noticed 95%); only if gold is missing is the
                   crosser looked at (then caught 90%). Innocent fallers are not searched.
  +threat_model  : also look around in advance for what people would want to steal and
                   how: gold spots get a camera and a stronger fence (thief gets through
                   15%, the camera sees a staged fall 80%)
"""
import json
from pathlib import Path
import numpy as np

SPOTS, T = 40, 300


def run(seed, policy):
    rng = np.random.default_rng(seed)
    gold = set(rng.choice(SPOTS, 6, replace=False).tolist())
    hole = rng.random(SPOTS) < 0.3
    hardened = set(gold) if policy.endswith("threat_model") else set()
    o = dict(accidents=0, gold_stolen=0, thieves_caught=0, innocents_searched=0, holes_fixed=0)
    for t in range(T):
        for s in range(SPOTS):
            # accidents
            if policy == "no_fence":
                p_acc = 0.03
            else:
                p_acc = 0.015 if hole[s] else 0.005
            if rng.random() < p_acc:
                o["accidents"] += 1
                if policy == "fence+search":
                    o["innocents_searched"] += 1
                if policy.startswith("fence+inspect") and hole[s] and rng.random() < 0.9:
                    hole[s] = False; o["holes_fixed"] += 1
            # thieves try at gold spots
            if s in gold and rng.random() < 0.02:
                p_through = 1.0 if policy == "no_fence" else (0.15 if s in hardened else 0.4)
                if hole[s]:
                    p_through = min(1.0, p_through * 2)
                if rng.random() >= p_through:
                    continue  # the fence held
                caught = False
                if policy == "fence+search":
                    caught = rng.random() < 0.9
                elif policy.startswith("fence+inspect"):
                    seen = (s in hardened and rng.random() < 0.8) or (rng.random() < 0.95)  # camera or gold check
                    caught = seen and rng.random() < 0.9
                    if hole[s] and rng.random() < 0.9:
                        hole[s] = False; o["holes_fixed"] += 1
                if caught:
                    o["thieves_caught"] += 1
                else:
                    o["gold_stolen"] += 1
    return o


if __name__ == "__main__":
    res = {}
    for p in ("no_fence", "fence", "fence+search", "fence+inspect", "fence+inspect+threat_model"):
        runs = [run(s, p) for s in range(20)]
        res[p] = {k: round(float(np.mean([r[k] for r in runs])), 1) for k in runs[0]}
        print(p.ljust(28), res[p])
    Path(__file__).with_name("alignment_guardrails_results.json").write_text(json.dumps(res, indent=1))
