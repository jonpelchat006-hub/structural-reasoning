"""Per-department route prior: for each department, fit the press order on its TRAINING games only
(each training game gets weights fitted without itself; 'all' = every training game of the department,
used on exam games and hidden games). Exam games' routes are never read."""
import json, sys, collections
import numpy as np
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT, TRAIN, EXAM
import importlib.util
spec = importlib.util.spec_from_file_location("tp", "train_prior.py")
src = open("train_prior.py").read()
fit = None; evaluate = None
ns = {}
exec(src[src.index("def fit("):src.index("prior = {}")], {"np": np, "FEAT_NAMES": __import__("mika3.explorer2", fromlist=["FEAT_NAMES"]).FEAT_NAMES}, ns)
fit, evaluate = ns["fit"], ns["evaluate"]
res = json.load(open(sys.argv[1]))
groups = collections.defaultdict(list); seen = set()
for r in res:
    g = r["game"][:4]
    if g not in TRAIN:
        continue
    for d in (r.get("route_data") or []):
        X = np.array(d["feats"], dtype=float); key = (g, d["level"], X.shape, d["chosen"], X.tobytes())
        if key in seen: continue
        seen.add(key); groups[g].append((X, d["chosen"]))
out = {}
for dept in ("click", "keys", "mixed"):
    games = [g for g in TRAIN if PUBLIC_DEPT[g] == dept and groups.get(g)]
    out[dept] = {}
    for g in games:
        tr = [x for h in games if h != g for x in groups[h]]
        if not tr: continue
        w = fit(tr); out[dept][g] = w.round(4).tolist()
        ll, base, t1, rk = evaluate(w, groups[g])
        print(f"{dept:5s} {g}: states {len(groups[g]):4d} loglik {ll:6.2f} (uniform {base:6.2f}) rank {rk:.2f}")
    allg = [x for h in games for x in groups[h]]
    if allg:
        out[dept]["all"] = fit(allg).round(4).tolist()
    print(dept, "training games with routes:", games)
json.dump(out, open(sys.argv[2], "w"))
