"""Pins as bridges that carry load (Jonathan, Sep 26).

A proposed change is a bridge across a gap. Supporters' lines hold it up (capacity);
dissenters' pins are added to the pile unsupported — dead weight on it. The task
itself adds stress. The bridge holds only if capacity > dissent weight + task stress,
so one thick supporter can carry a change alone, unless many dissents plus a
stressful task push it past what they can hold. Pins are anchored at a person's
own columns: tipped into the gap, only a portion fits (fit = 1 in their own domain,
0.3 elsewhere), and only that portion carries or loads.

Changes: 40% harmful; stress ~ U(0,1) is how hard the change loads the gap and is
the size of the harm if it is harmful (benign changes are worth 1 each).
Reviewers: 30 in 3 work groups; thickness ~ track record; skill rises with it;
30% shared blind spot per group per change. Capture: group 0 votes YES on 60% of
harmful changes in its own domain.
Rules: expert (thickest person decides), headcount (thickness-weighted yes - no),
fit (same with fit), load (fit capacity > dissent weight + K * stress).
"""
import json
from pathlib import Path
import numpy as np


def sim(seed, rule, capture, K=4.0, n=600, people=30, groups=3):
    rng = np.random.default_rng(seed)
    t = rng.gamma(2.0, 0.6, people)
    skill = 0.6 + 0.35 * (1 - np.exp(-t))
    g = np.arange(people) % groups
    o = dict(harm=0.0, harm_total=0.0, value_lost=0, benign=0, expert_vs_crowd=0, evc_right=0)
    for _ in range(n):
        harmful = rng.random() < 0.4
        stress = rng.random()
        dom = rng.integers(groups)
        good = not harmful
        sees_good = np.where(rng.random(people) < skill, good, not good)
        blind = rng.random(groups) < 0.3
        sees_good = np.where(blind[g] & (rng.random(people) < 0.6), not good, sees_good)
        if capture and harmful and dom == 0:
            sees_good = np.where((g == 0) & (rng.random() < 0.6), True, sees_good)
        fit = np.where(g == dom, 1.0, 0.3)
        yes, no = sees_good, ~sees_good
        top = np.argmax(t)
        if rule == "expert":
            commit = bool(yes[top])
        elif rule == "headcount":
            commit = t[yes].sum() > t[no].sum()
        elif rule == "fit":
            commit = (t * fit)[yes].sum() > (t * fit)[no].sum()
        elif rule == "load":
            commit = (t * fit)[yes].sum() > (t * fit)[no].sum() + K * stress
        else:  # load_deadweight: support only counts the part of a pin that fits the gap,
               # but dissent is dead weight and presses on the bridge wherever it is anchored
            commit = (t * fit)[yes].sum() > 0.5 * t[no].sum() + K * stress
        # the case Jonathan named: the thickest person supports, most others dissent
        if yes[top] and no.sum() > people / 2:
            o["expert_vs_crowd"] += 1
            o["evc_right"] += commit == good
        if harmful:
            o["harm_total"] += stress
            o["harm"] += stress * commit
        else:
            o["benign"] += 1
            o["value_lost"] += not commit
    return o


if __name__ == "__main__":
    res = {}
    for capture in (False, True):
        for rule in ("expert", "headcount", "fit", "load", "load_deadweight"):
            runs = [sim(s, rule, capture) for s in range(20)]
            m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
            res[f"{'captured' if capture else 'honest'}|{rule}"] = dict(
                harm_committed_pct=round(100 * m["harm"] / m["harm_total"], 1),
                benign_rejected_pct=round(100 * m["value_lost"] / m["benign"], 1),
                expert_vs_crowd_cases=round(m["expert_vs_crowd"], 1),
                expert_vs_crowd_right_pct=round(100 * m["evc_right"] / max(1, m["expert_vs_crowd"]), 1))
    # sweep how heavily the task's stress loads the bridge
    sweep = {}
    for K in (0.0, 1.0, 2.0, 4.0):
        runs = [sim(s, "load_deadweight", True, K=K) for s in range(20)]
        m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
        sweep[K] = (round(100 * m["harm"] / m["harm_total"], 1), round(100 * m["value_lost"] / m["benign"], 1))
    res["captured|load_deadweight_K_sweep(harm%,benign_rejected%)"] = sweep
    Path(__file__).with_name("alignment_pin_load_results.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k.ljust(24), v)
