"""
debate_experiment.py — does letting observers argue help, or does it dissipate them?

JONATHAN'S PROPOSAL
-------------------
"after the initial score comes in, couldn't we see why they disagree and choose the
one with the strongest point?"

THE PRE-REGISTERED PREDICTION (written before the run)
------------------------------------------------------
Debate is a DISSIPATION operation in this framework's terms. FOLDING_OUTER_SLOT
Part III: "if the models in the slot dissipate into each other you manufacture
agreement and lose the seam." Showing each observer the others' verdicts is exactly
that -- it converts independent readings into correlated ones.

FOLDING_OBSERVERS_AS_D measured the consequence: across six rosters,
corr(score, seam) = -0.91. Score and seam signal trade off almost perfectly.

    PREDICTION 1: DEBATE raises the score and LOWERS the seam signal.
                  It slides the roster toward the reinforcement end.
    PREDICTION 2: JUDGE (observers never see each other; a fresh arbiter reads all
                  three readings) raises the score WITHOUT collapsing the seam,
                  because the observers stay independent and the judge is a new D
                  rather than a channel between them.

If P1 holds, debate is the right move for a verdict product and the wrong move for
a seam map -- and the two must not share a pipeline.

THREE CONDITIONS, same 58 images, same 3 independent families (claude, gpt, grok):

    BASELINE  the cached independent readings                    (already measured)
    DEBATE    each observer re-scores after seeing the others'   (3 calls/image)
    JUDGE     observers untouched; an arbiter reads all three    (1 call/image)
"""

from __future__ import annotations

import json
import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import committee_experiment as ce

ROSTER = [("claude", 0), ("gpt", 0), ("grok", 0)]
CACHE = "debate_cache.json"
JUDGE_MODEL = "claude"          # a fresh D, not one of the debating observers
_dcache = {}
_lock = threading.Lock()


def _fmt(readings):
    out = []
    for i, r in enumerate(readings):
        out.append(f"Observer {chr(65+i)}: global={r['global']:.0f}, "
                   f"cells={[int(c) for c in r['cells']]}")
    return "\n".join(out)


DEBATE_PROMPT = """You already assessed this image on a 4x4 grid. Here is what the
whole panel returned, including you:

{panel}

You are Observer {me}. The panel does not agree.

Look at the image again with the disagreement in mind. Where another observer saw
something you did not, decide whether they were seeing a real defect or an artifact
of their own reading. Hold your position where you have concrete visual grounds;
revise where they have the stronger point.

Reply with STRICT JSON and nothing else:
{{"cells": [16 integers 0-100], "global": <integer 0-100>, "changed_because": "<one short sentence>"}}"""

JUDGE_PROMPT = """Three independent observers assessed this image on a 4x4 grid
(100 = certainly a real photograph, 0 = certainly AI-generated). They did not
confer, and they do not agree:

{panel}

You are the arbiter. You can see the image yourself. Do not average them. Decide
which observer's reading is best supported by what is actually visible, cell by
cell, and say what carried the decision.

Reply with STRICT JSON and nothing else:
{{"cells": [16 integers 0-100], "global": <integer 0-100>, "decided_by": "<one short sentence>"}}"""


def _call(model, path, prompt):
    saved = ce.PROMPT
    ce.PROMPT = prompt
    try:
        return ce.CALLERS[model](path, 0)
    finally:
        ce.PROMPT = saved


def get(path, kind, model, readings):
    key = f"{path}|{kind}|{model}"
    with _lock:
        if key in _dcache:
            return _dcache[key]
    out = None
    panel = _fmt(readings)
    for attempt in range(3):
        try:
            if kind == "debate":
                me = chr(65 + [m for m, _ in ROSTER].index(model))
                out = _call(model, path,
                            DEBATE_PROMPT.format(panel=panel, me=me))
            else:
                out = _call(JUDGE_MODEL, path, JUDGE_PROMPT.format(panel=panel))
            if out:
                break
        except Exception:
            pass
    with _lock:
        _dcache[key] = out
    return out


def reduce_(readings):
    ok = [r for r in readings if r]
    if not ok:
        return None
    c = np.array([r["cells"] for r in ok], float)
    return {"agreement": float(c.mean()),
            "disagreement": float(c.std(0).mean()) if len(ok) > 1 else 0.0,
            "n_obs": len(ok)}


def main():
    global _dcache
    if os.path.exists(CACHE):
        _dcache = json.load(open(CACHE))
        print(f"resumed {len(_dcache)}")
    ce._cache = json.load(open("committee_cache.json"))
    imgs = ce.images()

    base = {}
    for p, label, bucket in imgs:
        rs = [ce._cache.get(f"{p}|{m}|{r}") for m, r in ROSTER]
        if all(rs):
            base[p] = (rs, label, bucket)
    print(f"{len(base)} images with a complete independent panel\n")

    from concurrent.futures import ThreadPoolExecutor
    jobs = ([(p, "debate", m) for p in base for m, _ in ROSTER]
            + [(p, "judge", JUDGE_MODEL) for p in base])
    done = [0]

    def work(t):
        p, kind, m = t
        r = get(p, kind, m, base[p][0])
        with _lock:
            done[0] += 1
            if done[0] % 25 == 0:
                print(f"  {done[0]}/{len(jobs)}", flush=True)
                json.dump(_dcache, open(CACHE, "w"))
        return r

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, jobs))
    json.dump(_dcache, open(CACHE, "w"))

    rows = {"BASELINE independent": [], "DEBATE (observers confer)": [],
            "JUDGE (observers stay blind)": []}
    for p, (rs, label, bucket) in base.items():
        meta = {"label": label, "bucket": bucket}
        b = reduce_(rs)
        d = reduce_([get(p, "debate", m, rs) for m, _ in ROSTER])
        j = get(p, "judge", JUDGE_MODEL, rs)
        if b:
            rows["BASELINE independent"].append({**b, **meta})
        if d:
            rows["DEBATE (observers confer)"].append({**d, **meta})
        if j:
            # the judge is one reading; its seam is the panel it read
            rows["JUDGE (observers stay blind)"].append(
                {"agreement": float(np.mean(j["cells"])),
                 "disagreement": b["disagreement"] if b else 0.0, **meta})

    print(f"\n{'='*78}\nDOES ARGUING HELP?\n{'='*78}")
    print(f"{'condition':<32}{'score AUC':>11}{'seam |d|':>10}{'n':>5}")
    res = {}
    for k, v in rows.items():
        if len(v) < 20:
            continue
        a = ce.stratified(v, "agreement")[0]
        s = ce.stratified(v, "disagreement")[0]
        res[k] = (a, abs(s - 0.5))
        print(f"{k:<32}{a:>11.3f}{abs(s-0.5):>10.3f}{len(v):>5}")

    if "DEBATE (observers confer)" in res and "BASELINE independent" in res:
        b, d = res["BASELINE independent"], res["DEBATE (observers confer)"]
        print(f"\nPREDICTION 1 (debate: score UP, seam DOWN)")
        print(f"   score {b[0]:.3f} -> {d[0]:.3f} ({abs(d[0]-.5)-abs(b[0]-.5):+.3f})   "
              f"seam {b[1]:.3f} -> {d[1]:.3f} ({d[1]-b[1]:+.3f})")
        ok = (abs(d[0]-.5) >= abs(b[0]-.5)) and (d[1] < b[1])
        print(f"   -> {'CONFIRMED (dissipation)' if ok else 'NOT confirmed'}")
    if "JUDGE (observers stay blind)" in res:
        b, j = res["BASELINE independent"], res["JUDGE (observers stay blind)"]
        print(f"\nPREDICTION 2 (judge: score UP, seam preserved)")
        print(f"   score {b[0]:.3f} -> {j[0]:.3f} ({abs(j[0]-.5)-abs(b[0]-.5):+.3f})")

    json.dump({k: list(v) for k, v in res.items()},
              open("debate_results.json", "w"), indent=2)
    print("\nwrote debate_results.json")


if __name__ == "__main__":
    main()
