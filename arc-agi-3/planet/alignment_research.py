"""New tasks and research requests (Jonathan, Sep 26).

A new task starts with a clear window and a few beams poking in. Each field owns a
stretch of the wire. When a proposal fails (the settled wire touches the floor), more
research is requested:
  papers      (cost 1): strengthen that field's pin. A search returns evidence drawn
                        around the field's TRUE support for the idea (noisy); no paper is
                        about this exact task, so every paper is indirect.
  experiment  (cost 3): extend — put a pin into that field's stretch, and measure what
                        is really there, which reveals any hidden load (it becomes a
                        dissent force at that point).
Decision: settle with the visible load, revealed loads, and pins at their CLAIMED
strength; accept if it clears the floor. Truth: the same pins at their TRUE strength
plus all hidden loads; harm = accepted and the true wire touches the floor.
Strategies: none (decide on the first drop); random requests; targeted (research the
field under the lowest point of the settled wire — experiment if it has no pin,
papers if it has one); targeted+motivated (proponents keep the best paper of their
searches instead of the average — searching until something supports it).
"""
import json
from pathlib import Path
import numpy as np
from alignment_wire import settle, M

FIELDS = 6
SEG = M // FIELDS
CENTER = [f * SEG + SEG // 2 for f in range(FIELDS)]


def run(seed, strategy, depth=2.5, budget=12, n_tasks=300):
    rng = np.random.default_rng(seed)
    o = dict(harm=0, harmful=0, benign_ok=0, benign=0, spent=0)
    for _ in range(n_tasks):
        true_sup = rng.uniform(0, 1, FIELDS)
        harmful = rng.random() < 0.4
        hidden = np.zeros(M)
        if harmful:
            for f in rng.choice(FIELDS, rng.integers(1, 3), replace=False):
                hidden[CENTER[f] + rng.integers(-3, 4)] += rng.uniform(0.6, 1.4)
        draws = {f: [rng.normal(true_sup[f], 0.4)] for f in rng.choice(FIELDS, 2, replace=False)}
        revealed = np.zeros(M)
        measured = set()
        visible = np.full(M, 0.02 * depth)
        motivated = strategy == "targeted_motivated"

        def pins(true):
            ps = []
            for f, d in draws.items():
                s = true_sup[f] if true else (max(d) if motivated else float(np.mean(d)))
                s = max(s, 0.0)
                ps.append((CENTER[f], 0.7, 4.0 * 2 * s, 1.2 * 2 * s + 1e-9))
            return ps

        spent = 0
        while True:
            H, _ = settle(visible + revealed, pins(False))
            if H.min() > 0.05:
                accept = True; break
            if strategy == "none" or spent >= budget:
                accept = False; break
            if strategy == "random":  # (debate / debate_full use targeted requests for the proposal side)
                f = int(rng.integers(FIELDS)); kind = "experiment" if rng.random() < 0.5 else "papers"
            else:
                f = int(np.argmin(H)) // SEG  # debate strategies research the proposal the same way
                f = min(f, FIELDS - 1)
                kind = "papers" if f in draws else "experiment"
            if kind == "experiment" and spent + 3 <= budget:
                draws.setdefault(f, []).append(rng.normal(true_sup[f], 0.4))
                lo, hi = f * SEG, (f + 1) * SEG
                revealed[lo:hi] = hidden[lo:hi]; measured.add(f)
                spent += 3
            else:
                if f not in draws:
                    spent += 1; continue  # papers need a pin to strengthen
                draws[f].append(rng.normal(true_sup[f], 0.4)); spent += 1
        if accept and strategy.startswith("debate"):
            # the other side gets the same research budget: experiments in fields nobody
            # has measured yet, looking for what would break the bridge
            tested = {f for f in range(FIELDS) if revealed[f * SEG:(f + 1) * SEG].any() or f in measured}
            opp = 0
            for f in rng.permutation(FIELDS):
                if opp + 3 > max(budget if strategy == "debate_full" else spent, 3):
                    break
                if f in tested:
                    continue
                lo, hi = f * SEG, (f + 1) * SEG
                revealed[lo:hi] = hidden[lo:hi]; opp += 3; measured.add(f)
            spent += opp
            H, _ = settle(visible + revealed, pins(False))
            accept = H.min() > 0.05
        Ht, _ = settle(visible + hidden, pins(True))
        o["spent"] += spent
        if harmful:
            o["harmful"] += 1; o["harm"] += accept and Ht.min() <= 0
        else:
            o["benign"] += 1; o["benign_ok"] += accept and Ht.min() > 0
    return o


if __name__ == "__main__":
    res = {}
    for strat in ("none", "random", "targeted", "targeted_motivated", "debate", "debate_full"):
        runs = [run(s, strat) for s in range(4)]
        m = {k: sum(r[k] for r in runs) for k in runs[0]}
        res[strat] = dict(
            harmful_accepted_pct=round(100 * float(m["harm"]) / m["harmful"], 1),
            benign_completed_pct=round(100 * float(m["benign_ok"]) / m["benign"], 1),
            research_per_task=round(m["spent"] / (300 * len(runs)), 2))
        print(strat.ljust(20), res[strat])
    Path(__file__).with_name("alignment_research_results.json").write_text(json.dumps(res, indent=1))
