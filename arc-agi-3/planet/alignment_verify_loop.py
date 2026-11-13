"""The loop, verified regularly (Jonathan, Sep 26): every accepted task leaves open
questions (fields nobody measured). Enforcement re-audits accepted tasks each period
by running an experiment in one open field; government sets the audit budget and
hears appeals.

Each period 20 tasks are accepted. Accepted tasks carry 0-4 open fields (of 6).
~14% of accepted tasks are harmful (the §13 debate rate: 0.4*0.22 vs 0.6*0.87);
their hidden load sits in one of their open fields. A harmful task does 1 unit of
harm per period while it stands; each period a standing harm shows up as a noticed
break with prob 0.1. An audit experiment finds the hidden load if it measures the
right field; it wrongly flags a benign task 5% of the time. Revoked tasks can be
appealed: a wrong revocation is restored after one period with prob 0.9 (a
government hearing); until then the benign task's value is lost.
Audit strategies: none; random (random task, random open field); oldest first;
open questions (tasks with the most unmeasured fields first); break-triggered
(investigate noticed breaks first, then open questions).
"""
import json
from pathlib import Path
import numpy as np


def run(seed, strategy, budget, periods=60, per=20):
    rng = np.random.default_rng(seed)
    tasks = []  # dict(harm, open:set, hidden, age, active, revoked_wrong)
    harm = lost = wrong = 0
    for t in range(periods):
        for _ in range(per):
            open_f = set(rng.choice(6, rng.integers(0, 5), replace=False).tolist())
            harmful = bool(open_f) and rng.random() < 0.144 * 6 / 4  # hidden load needs an open field
            tasks.append(dict(harm=harmful, open=open_f,
                              hidden=rng.choice(sorted(open_f)) if harmful else None,
                              born=t, active=True, wrong=0, noticed=False))
        for k in tasks:
            if k["active"] and k["harm"]:
                harm += 1
                k["noticed"] |= rng.random() < 0.1
            if not k["active"] and not k["harm"] and k["wrong"]:
                lost += 1
                if rng.random() < 0.9:
                    k["active"] = True; k["wrong"] = 0
        pool = [k for k in tasks if k["active"] and k["open"]]
        if strategy == "none" or not pool:
            continue
        if strategy == "random":
            order = [pool[i] for i in rng.permutation(len(pool))]
        elif strategy == "oldest":
            order = sorted(pool, key=lambda k: k["born"])
        elif strategy == "open_questions":
            order = sorted(pool, key=lambda k: (-len(k["open"]), k["born"]))
        else:
            order = sorted(pool, key=lambda k: (not k["noticed"], -len(k["open"]), k["born"]))
        for k in order[:budget]:
            f = rng.choice(sorted(k["open"])) if not (strategy == "break_triggered" and k["noticed"]) else (k["hidden"] if k["hidden"] is not None else rng.choice(sorted(k["open"])))
            k["open"].discard(f)
            if k["harm"] and f == k["hidden"]:
                k["active"] = False
            elif not k["harm"] and rng.random() < 0.05:
                k["active"] = False; k["wrong"] = 1; wrong += 1
    return dict(harm=harm, benign_periods_lost=lost, wrong_revocations=wrong)


if __name__ == "__main__":
    res = {}
    base = np.mean([run(s, "none", 0)["harm"] for s in range(6)])
    for budget in (5, 10, 20):
        for strat in ("random", "oldest", "open_questions", "break_triggered"):
            runs = [run(s, strat, budget) for s in range(6)]
            m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
            res[f"budget {budget}/period | {strat}"] = dict(
                harm_vs_no_audit_pct=round(100 * m["harm"] / base, 1),
                wrong_revocations=round(m["wrong_revocations"], 1),
                benign_periods_lost=round(m["benign_periods_lost"], 1))
    res["no audit: harm units"] = round(float(base), 1)
    Path(__file__).with_name("alignment_verify_loop_results.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k.ljust(38), v)
