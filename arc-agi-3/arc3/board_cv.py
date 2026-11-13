"""Grading the board itself (the level above the professors).

The board's job is to pick, per department, the professor whose students will do better on games
nobody has seen. So a set of board rules is graded the same way a professor is: by what happens on
held-out games. Five-fold rotation over the 25 public games (each fold: 2 click, 1 keys, 2 mixed
held out); in each fold the board picks from the other 20 games' ratings and its picks are scored
on the held-out 5; seed-paired against plain.

  python3 board_cv.py uni/"""
import json, os, sys, random, collections, statistics as st
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT, PROFESSORS

D = sys.argv[1] if len(sys.argv) > 1 else "uni"
runs = {p: json.load(open(os.path.join(D, p.replace("-", "_") + ".json"))) for p in PROFESSORS
        if os.path.exists(os.path.join(D, p.replace("-", "_") + ".json"))}
profs = list(runs)
seeds = sorted({r.get("seed") or 0 for r in runs["plain"]})
SC = {p: collections.defaultdict(dict) for p in profs}
for p in profs:
    for r in runs[p]:
        SC[p][r["game"][:4]][r.get("seed") or 0] = r["score"]


def folds(seed=7):
    rng = random.Random(seed)
    by = {d: sorted(g for g, x in PUBLIC_DEPT.items() if x == d) for d in ("click", "keys", "mixed")}
    for d in by: rng.shuffle(by[d])
    out = [[] for _ in range(5)]
    for d, games in by.items():
        for i, g in enumerate(games):
            out[i % 5].append(g)
    return out


def dept_seed(p, games):
    return [st.mean(SC[p][g].get(s, 0.0) for g in games) for s in seeds]


def rule_set(name):
    def pick(games):
        if name == "always plain":
            return "plain"
        base = dept_seed("plain", games)
        cheap = [g for g in games if st.mean(SC["plain"][g].values()) >= 1.0]
        best, bg = "plain", 0.0
        for p in profs:
            if p == "plain":
                continue
            ss = dept_seed(p, games); diff = [a - b for a, b in zip(ss, base)]
            m = st.mean(diff); won = sum(x > 1e-9 for x in diff)
            kept = all(st.mean(SC[p][g].values()) >= 0.7 * st.mean(SC["plain"][g].values()) for g in cheap)
            rel = m / max(1e-9, st.mean(base))
            ok = {"greedy (best average)": m > 0,
                  "board v1 (avg>0, 6/8 seeds, keep cheap wins)": m > 0 and won >= 6 and kept,
                  "strict (gain>=0.02 and 7/8 seeds, keep cheap wins)": m >= 0.02 and won >= 7 and kept,
                  "relative (gain>=10% and 7/8 seeds, keep cheap wins)": rel >= 0.10 and won >= 7 and kept}[name]
            if ok and m > bg:
                best, bg = p, m
        return best
    return pick


RULES = ["always plain", "greedy (best average)", "board v1 (avg>0, 6/8 seeds, keep cheap wins)",
         "strict (gain>=0.02 and 7/8 seeds, keep cheap wins)", "relative (gain>=10% and 7/8 seeds, keep cheap wins)"]
F = folds()
print("folds:", F)
lines = ["| board rules | held-out gain vs plain (mean over 5 folds x 8 seeds) | folds better / worse | picks per fold (click, keys, mixed) |", "|---|---|---|---|"]
for name in RULES:
    pick = rule_set(name)
    gains = []; better = worse = 0; picks = []
    for exam in F:
        train = [g for g in PUBLIC_DEPT if g not in exam]
        cur = {d: pick([g for g in train if PUBLIC_DEPT[g] == d]) for d in ("click", "keys", "mixed")}
        picks.append("/".join(cur[d] for d in ("click", "keys", "mixed")))
        u = [st.mean(SC[cur[PUBLIC_DEPT[g]]][g].get(s, 0.0) for g in exam) for s in seeds]
        b = [st.mean(SC["plain"][g].get(s, 0.0) for g in exam) for s in seeds]
        g = st.mean(a - c for a, c in zip(u, b)); gains.append(g)
        better += g > 1e-9; worse += g < -1e-9
    lines.append(f"| {name} | {st.mean(gains):+.3f} | {better} / {worse} | {'; '.join(picks)} |")
print("\n".join(lines))
open(os.path.join(D, "board_cv.md"), "w").write("\n".join(lines) + "\n")
