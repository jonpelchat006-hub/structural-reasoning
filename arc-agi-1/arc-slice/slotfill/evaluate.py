"""Measure the slot filler on ARC-1 train and eval: per class, attempted / correct@1 / correct@2 / wrong,
and the gain over the solver's verified lists."""
import json, re, sys, time, collections
import numpy as np
from multiprocessing import Pool
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import slotfill
src = open("arc_levels.py").read()
exec(src[src.index("D4 = "):src.index("out = {}")])

def ids(path):
    for p in (path, os.path.join("..", path)):
        if os.path.exists(p): return set(re.findall(r"[0-9a-f]{8}", open(p).read()))
    return set()

def run(args):
    split, tid = args
    task = TASKS[split][tid]
    t = time.time()
    try:
        r = slotfill.solve(task, max_attempts=2)
    except Exception as e:
        return split, tid, "error", repr(e)[:200], time.time() - t
    if not r: return split, tid, "none", None, time.time() - t
    truth = [np.array(p["output"]) for p in task["test"]]
    res = []
    for names, mode, loo, preds in r:
        res.append((names, mode, loo, all(np.array_equal(p, q) for p, q in zip(preds, truth))))
    return split, tid, "rule", res, time.time() - t

TASKS = {s: json.load(open(f"{s}_tasks.json")) for s in ("train", "eval")}
if __name__ == "__main__":
    splits = sys.argv[1:] or ["train", "eval"]
    jobs = [(s, t) for s in splits for t in TASKS[s]]
    with Pool(2) as pool:
        results = pool.map(run, jobs, chunksize=4)
    solved = {"train": ids("verified_solved.txt"), "eval": ids("verified_eval.txt")}
    out = {}
    for s in splits:
        rows = collections.defaultdict(lambda: collections.Counter())
        detail = []
        for split, tid, kind, res, dt in results:
            if split != s: continue
            c = classify(TASKS[s][tid])[0]
            row = rows[c]; row["n"] += 1; row["old"] += tid in solved[s]
            if kind == "error": row["err"] += 1; detail.append((tid, c, "error", res)); continue
            if kind == "none": continue
            row["att"] += 1
            c1 = res[0][3]; c2 = any(x[3] for x in res)
            row["c1"] += c1; row["c2"] += c2; row["wrong"] += not c2
            row["new2"] += c2 and tid not in solved[s]
            row["loo1"] += res[0][2]; row["loo_c1"] += res[0][2] and c1
            detail.append((tid, c, [(list(n), m, l, ok) for n, m, l, ok in res], round(dt, 2)))
        tot = collections.Counter()
        print(f"=== {s}")
        print(f"{'class':4s} {'n':>4s} {'old':>4s} {'att':>4s} {'@1':>4s} {'@2':>4s} {'wrong':>5s} {'new@2':>5s} {'union':>5s}  loo@1 (correct)")
        for c in sorted(rows):
            r = rows[c]; tot.update(r)
            print(f"{c:4s} {r['n']:4d} {r['old']:4d} {r['att']:4d} {r['c1']:4d} {r['c2']:4d} {r['wrong']:5d} {r['new2']:5d} {r['old'] + r['new2']:5d}  {r['loo1']} ({r['loo_c1']})")
        r = tot
        print(f"{'all':4s} {r['n']:4d} {r['old']:4d} {r['att']:4d} {r['c1']:4d} {r['c2']:4d} {r['wrong']:5d} {r['new2']:5d} {r['old'] + r['new2']:5d}  {r['loo1']} ({r['loo_c1']})")
        out[s] = detail
    json.dump(out, open("eval_detail.json", "w"), indent=0, default=str)
