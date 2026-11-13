"""The board: rate every professor by how fresh students do in each department, choose one per
department from the TRAINING games only, then (and only then) open the practice final.

  python3 board.py uni/   ->  uni/report.md, mika3/curriculum.json

Board rules (v2) for a professor to replace "plain" in a department:
  1. lesson plans say how to explore, never what to press in a given game (true by construction:
     knob settings; the route prior is fitted without the game it is used on);
  2. better on average over the department's training games, seed for seed (paired), by at least 0.02;
  3. better on at least 7 of 8 seeds;
  4. keeps at least 70% of plain's score on every training game where plain already wins cheaply
     (score >= 1): the score is quadratic in efficiency, so cheap wins are what to protect.
Ties go to plain (the simplest plan).
v1 (avg > 0, 6/8 seeds) let noise through: its picks lost to plain on the practice final 8/8 seeds, and
graded by rotating finals (board_cv.py) it lost 0.023 on average; v2 lost nothing."""
import json, os, sys, collections, statistics as st
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT, TRAIN, EXAM, PROFESSORS

D = sys.argv[1] if len(sys.argv) > 1 else "uni"
runs = {}
for p in PROFESSORS:
    f = os.path.join(D, p.replace("-", "_") + ".json")
    if os.path.exists(f):
        runs[p] = json.load(open(f))
profs = [p for p in PROFESSORS if p in runs]
seeds = sorted({r.get("seed") or 0 for r in runs["plain"]})


def table(p):
    """score[game][seed], levels[game][seed], waste list"""
    sc = collections.defaultdict(dict); lv = collections.defaultdict(dict); waste = collections.defaultdict(list)
    for r in runs[p]:
        g = r["game"][:4]; s = r.get("seed") or 0
        sc[g][s] = r["score"]; lv[g][s] = r["levels"]
        for w in (r.get("wins") or []):
            waste[g].append((w["spent"], w["shortest"]))
    return sc, lv, waste


T = {p: table(p) for p in profs}


def dept_seed_scores(p, games):
    sc = T[p][0]
    return [st.mean(sc[g].get(s, 0.0) for g in games) for s in seeds]


lines = ["# Mika's university: the board's report", "",
         f"Practice final (held back, never used to choose): {', '.join(EXAM)}", "",
         "Ratings on the TRAINING games (mean over 8 seeds; seeds won against plain; levels per seed).", ""]
curriculum = {"default": "plain"}
for dept in ("click", "keys", "mixed"):
    games = [g for g in TRAIN if PUBLIC_DEPT[g] == dept]
    base = dept_seed_scores("plain", games)
    lines += [f"## {dept} ({len(games)} training games: {', '.join(games)})", "",
              "| professor | score | vs plain | seeds won | levels/seed | waste (spent/shortest) | cheap wins kept | verdict |",
              "|---|---|---|---|---|---|---|---|"]
    best, best_gain = "plain", 0.0
    for p in profs:
        ss = dept_seed_scores(p, games)
        diff = [a - b for a, b in zip(ss, base)]
        won = sum(d > 1e-9 for d in diff)
        lvl = st.mean(sum(T[p][1][g].get(s, 0) for g in games) for s in seeds)
        sp = sum(a for g in games for a, _ in T[p][2][g]); sh = sum(b for g in games for _, b in T[p][2][g])
        cheap = [g for g in games if st.mean(T["plain"][0][g].values()) >= 1.0]
        kept = all(st.mean(T[p][0][g].values()) >= 0.7 * st.mean(T["plain"][0][g].values()) for g in cheap)
        ok = p != "plain" and st.mean(diff) >= 0.02 and won >= 7 and kept
        verdict = "plain (reference)" if p == "plain" else ("passes" if ok else
                  "fails: " + ", ".join(x for x, c in (("gain below 0.02", st.mean(diff) < 0.02), (f"won {won}/8 seeds", won < 7), ("breaks a cheap win", not kept)) if c))
        lines.append(f"| {p} | {st.mean(ss):.3f} | {st.mean(diff):+.3f} | {won}/8 | {lvl:.1f} | "
                     f"{sp / max(1, sh):.0f}x | {'yes' if kept else 'no'} ({len(cheap)}) | {verdict} |")
        if ok and st.mean(diff) > best_gain:
            best, best_gain = p, st.mean(diff)
    curriculum[dept] = best
    lines += ["", f"**Board's choice for {dept}: {best}.** {PROFESSORS[best][0]}", ""]

# ---------------------------------------------------------------- the practice final, opened last
lines += ["## The practice final (opened after the choices above)", "",
          "| game | department | professor chosen | its score | plain's score | best professor here (for reference) |",
          "|---|---|---|---|---|---|"]
uni_seed = []; plain_seed = []
for s in seeds:
    uni_seed.append(st.mean(T[curriculum[PUBLIC_DEPT[g]]][0][g].get(s, 0.0) for g in EXAM))
    plain_seed.append(st.mean(T["plain"][0][g].get(s, 0.0) for g in EXAM))
for g in EXAM:
    d = PUBLIC_DEPT[g]; p = curriculum[d]
    bestp = max(profs, key=lambda q: st.mean(T[q][0][g].values()))
    lines.append(f"| {g} | {d} | {p} | {st.mean(T[p][0][g].values()):.2f} | {st.mean(T['plain'][0][g].values()):.2f} | "
                 f"{bestp} ({st.mean(T[bestp][0][g].values()):.2f}) |")
lines += ["", f"Practice final: university {st.mean(uni_seed):.3f} vs plain {st.mean(plain_seed):.3f}; "
          f"university better on {sum(a > b + 1e-9 for a, b in zip(uni_seed, plain_seed))}/8 seeds, worse on "
          f"{sum(a < b - 1e-9 for a, b in zip(uni_seed, plain_seed))}/8.", ""]
allg = sorted(PUBLIC_DEPT)
u_all = st.mean(st.mean(T[curriculum[PUBLIC_DEPT[g]]][0][g].get(s, 0.0) for g in allg) for s in seeds)
p_all = st.mean(st.mean(T["plain"][0][g].get(s, 0.0) for g in allg) for s in seeds)
lines += [f"All 25 games: university {u_all:.3f} vs plain {p_all:.3f}.", ""]
open(os.path.join(D, "report.md"), "w").write("\n".join(lines))
json.dump(curriculum, open("mika3/curriculum.json", "w"), indent=1)
print("\n".join(lines))
