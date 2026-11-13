# Sort ARC tasks by the frame's levels and compare with what the solver already solves (read-only).
import json, os, re, collections
import numpy as np
ROOT = os.path.expanduser("~/mnt/arc-slice")
def ids(path):
    s = open(path).read()
    return set(re.findall(r"[0-9a-f]{8}", s))
D4 = [lambda g: g, lambda g: np.rot90(g, 1), lambda g: np.rot90(g, 2), lambda g: np.rot90(g, 3),
      lambda g: g[:, ::-1], lambda g: g[::-1, :], lambda g: g.T, lambda g: np.rot90(g, 2).T]
def stab(g): return sum(1 for f in D4 if f(g).shape == g.shape and np.array_equal(f(g), g))
def classify(task):
    P = [(np.array(p["input"]), np.array(p["output"])) for p in task["train"]]
    same = all(a.shape == b.shape for a, b in P)
    for f in D4[1:]:
        if all(f(a).shape == b.shape and np.array_equal(f(a), b) for a, b in P): return "A core move (turn/flip)"
    if all(stab(b) > stab(a) for a, b in P): return "B lands on a symmetric state"
    if same:
        kinds = set()
        for a, b in P:
            bg = collections.Counter(a.ravel().tolist()).most_common(1)[0][0]
            ch = a != b
            if not ch.any(): kinds.add("none"); continue
            if np.all(a[ch] == bg): kinds.add("fill")
            elif np.all(b[ch] == bg): kinds.add("erase")
            elif np.all((a[ch] != bg) & (b[ch] != bg)): kinds.add("recolor")
            else: kinds.add("mixed")
        kinds.discard("none")
        if kinds == {"fill"}: return "C fills empty slots only"
        if kinds <= {"recolor", "erase"}: return "D recolors or erases only"
        return "E same size, mixed changes"
    if all(b.size < a.size for a, b in P): return "F output smaller (reads out a part)"
    if all(b.size > a.size for a, b in P): return "G output larger (expands)"
    return "H size changes vary"
out = {}
for split, d, sol in [("train", "data", "verified_solved.txt"), ("eval", "data-eval", "verified_eval.txt")]:
    S = ids(os.path.join(ROOT, sol)); rows = collections.defaultdict(lambda: [0, 0])
    for fn in sorted(os.listdir(os.path.join(ROOT, d))):
        if not fn.endswith(".json"): continue
        t = json.load(open(os.path.join(ROOT, d, fn))); c = classify(t); tid = fn[:-5]
        rows[c][0] += 1; rows[c][1] += tid in S
    out[split] = {k: v for k, v in sorted(rows.items())}
    print(f"--- {split}: {sum(v[0] for v in rows.values())} tasks, {len(S)} solved ids listed")
    for k, (n, s) in sorted(rows.items()):
        print(f"  {k:40s} {n:4d} tasks, solved {s:3d} ({100*s/n:5.1f}%)")
json.dump(out, open(os.path.expanduser("~/atlas/arc_levels.json"), "w"), indent=1)
