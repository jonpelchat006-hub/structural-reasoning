"""Does a known winning event single out the winning press? Lift = P(win press matches an earlier win
event) / P(an ordinary route press matches one). Three granularities: fine, mid (colours, no sizes or
counts), coarse (colour-free roles)."""
import json, sys, ast, numpy as np
from collections import defaultdict
rows = json.load(open(sys.argv[1]))
keys = [k for k, r in rows.items() if r["replay_won"] and r["fine"]]

def mid(sig):
    act, target, effs, won = ast.literal_eval(sig)
    tcol = target[0] if target else None
    eff = tuple(sorted({(e[0], e[1], e[2]) for e in effs}))
    return (act, tcol, eff)

def coarse(sig):
    t = ast.literal_eval(sig); return t[:4]

def fine(sig):
    t = ast.literal_eval(sig); return t[:3]

out = ["| granularity | employer pool | levels | winning press matches an earlier win | ordinary press matches an earlier win | lift |", "|---|---|---|---|---|---|"]
for name, fn, src in (("fine", fine, "fine"), ("mid (colours, no sizes)", mid, "fine"), ("coarse (roles only)", coarse, "coarse")):
    for pool_name in ("same game, earlier levels", "same department, other games", "other departments"):
        w_hits, o_hits, n = [], [], 0
        for k in keys:
            r = rows[k]
            if pool_name.startswith("same game"):
                pool = [j for j in keys if rows[j]["game"] == r["game"] and rows[j]["level"] < r["level"]]
            elif pool_name.startswith("same department"):
                pool = [j for j in keys if rows[j]["game"] != r["game"] and rows[j]["dept"] == r["dept"]]
            else:
                pool = [j for j in keys if rows[j]["dept"] != r["dept"]]
            if not pool:
                continue
            n += 1
            wins = {fn(rows[j][src][-1]) for j in pool}
            evs = [fn(s) for s in r[src]]
            w_hits.append(evs[-1] in wins)
            o_hits += [e in wins for e in evs[:-1]]
        pw = np.mean(w_hits) if w_hits else 0; po = np.mean(o_hits) if o_hits else 0
        out.append(f"| {name} | {pool_name} | {n} | {pw:.0%} | {po:.0%} | {pw / po if po else float('inf'):.1f}x |")
print("\n".join(out))
