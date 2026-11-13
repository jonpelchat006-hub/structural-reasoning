"""The board, re-peeled with the levels that came in from the trail.

Professors are graded on every level inside the school (won at least once on the frontier), each
level weighted as the official card weights it (level k counts k), by fresh students dropped
straight into the level - warm (carrying what the previous level's route teaches) or cold.
Choices use the training games only; the rotating finals (5 folds) grade the board's rules.

  python level_board.py trail/   (reads trail/exam_<mode>_<prof>.json, trail/frontier_casebook.json)"""
import json, os, sys, glob, random, collections, statistics as st
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT, TRAIN, EXAM, PROFESSORS

D = sys.argv[1] if len(sys.argv) > 1 else "trail"
book = json.load(open(os.path.join(D, "frontier_casebook.json")))
R = {}   # (mode, prof) -> {(game, level): {seed: score}}
for f in glob.glob(os.path.join(D, "exam_*_*.json")):
    base = os.path.basename(f)[5:-5]
    mode, prof = base.split("_", 1)
    prof = prof.replace("_", "-")
    t = collections.defaultdict(dict)
    for r in json.load(open(f)):
        t[(r["game"][:4], r["level"])][r["seed"]] = r["score"]
    R[(mode, prof)] = t
modes = sorted({m for m, _ in R})
seeds = sorted({s for t in R.values() for v in t.values() for s in v})


def lv_weight(level):
    return level + 1


def dept_scores(mode, prof, games):
    """per seed: level-weighted mean score over the inside levels of these games (levels missing in a
    professor's exam count 0)"""
    t = R[(mode, prof)]
    keys = [k for k in R[(mode, "plain")] if k[0] in games]
    W = sum(lv_weight(l) for _, l in keys) or 1
    return [sum(lv_weight(l) * t.get((g, l), {}).get(s, 0.0) for g, l in keys) / W for s in seeds], keys


def choose(mode, games, rule):
    base, keys = dept_scores(mode, "plain", games)
    cheap = [k for k in keys if st.mean(R[(mode, "plain")][k].values()) >= 1.0]
    best, bg = "plain", 0.0
    rows = []
    for (m, p) in R:
        if m != mode or p == "plain":
            continue
        ss, _ = dept_scores(mode, p, games)
        diff = [a - b for a, b in zip(ss, base)]
        mg = st.mean(diff); won = sum(d > 1e-9 for d in diff)
        rel = mg / max(1e-9, st.mean(base))
        kept = all(st.mean(R[(mode, p)].get(k, {0: 0}).values()) >= 0.7 * st.mean(R[(mode, "plain")][k].values()) for k in cheap)
        ok = {"greedy": mg > 0,
              "strict": rel >= 0.10 and won == len(seeds) and kept}[rule]
        rows.append((p, st.mean(ss), mg, won, kept, ok))
        if ok and mg > bg:
            best, bg = p, mg
    return best, rows, st.mean(base)


lines = ["# The board, re-peeled with the trail", "",
         f"Inside the school: {len(book)} levels won on the frontier. Practice-final games held out: {', '.join(EXAM)}.", ""]
cur = {}
for mode in modes:
    lines += [f"## {mode} level exams", ""]
    for dept in ("click", "keys", "mixed"):
        games = [g for g in TRAIN if PUBLIC_DEPT[g] == dept]
        best, rows, b = choose(mode, games, "strict")
        cur[(mode, dept)] = best
        nk = len([k for k in R[(mode, "plain")] if k[0] in games])
        lines += [f"**{dept}** ({nk} inside levels on training games; plain {b:.2f})", "",
                  "| professor | weighted level score | vs plain | seeds won | keeps cheap wins | passes strict board |", "|---|---|---|---|---|---|"]
        for p, s_, mg, won, kept, ok in sorted(rows, key=lambda x: -x[2]):
            lines.append(f"| {p} | {s_:.2f} | {mg:+.2f} | {won}/{len(seeds)} | {'yes' if kept else 'no'} | {'yes' if ok else 'no'} |")
        lines += ["", f"Board's choice ({mode}, {dept}): **{best}**", ""]

# rotating finals: grade the rules on held-out games, level-weighted
def folds(seed=7):
    rng = random.Random(seed)
    by = {d: sorted(g for g, x in PUBLIC_DEPT.items() if x == d) for d in ("click", "keys", "mixed")}
    for d in by: rng.shuffle(by[d])
    out = [[] for _ in range(5)]
    for d, games in by.items():
        for i, g in enumerate(games):
            out[i % 5].append(g)
    return out


lines += ["## Grading the board on rotating finals (level-weighted, held-out games)", "",
          "| exams | rules | held-out gain vs plain | folds better / worse |", "|---|---|---|---|"]
for mode in modes:
    for rule in ("greedy", "strict"):
        gains = []; bt = wt = 0
        for exam in folds():
            train = [g for g in PUBLIC_DEPT if g not in exam]
            pick = {d: choose(mode, [g for g in train if PUBLIC_DEPT[g] == d], rule)[0] for d in ("click", "keys", "mixed")}
            keys = [k for k in R[(mode, "plain")] if k[0] in exam]
            if not keys:
                continue
            W = sum(lv_weight(l) for _, l in keys)
            u = [sum(lv_weight(l) * R[(mode, pick[PUBLIC_DEPT[g]])].get((g, l), {}).get(s, 0.0) for g, l in keys) / W for s in seeds]
            b = [sum(lv_weight(l) * R[(mode, "plain")][(g, l)].get(s, 0.0) for g, l in keys) / W for s in seeds]
            gg = st.mean(x - y for x, y in zip(u, b)); gains.append(gg); bt += gg > 1e-9; wt += gg < -1e-9
        lines.append(f"| {mode} | {rule} | {st.mean(gains):+.3f} | {bt} / {wt} |")

# the practice final under the strict board's warm choices
mode = "warm" if "warm" in modes else modes[0]
keys = [k for k in R[(mode, "plain")] if k[0] in EXAM]
if keys:
    W = sum(lv_weight(l) for _, l in keys)
    u = [sum(lv_weight(l) * R[(mode, cur[(mode, PUBLIC_DEPT[g])])].get((g, l), {}).get(s, 0.0) for g, l in keys) / W for s in seeds]
    b = [sum(lv_weight(l) * R[(mode, "plain")][(g, l)].get(s, 0.0) for g, l in keys) / W for s in seeds]
    lines += ["", f"Practice final ({mode}, {len(keys)} inside levels of {', '.join(EXAM)}): strict board's choices "
              f"{st.mean(u):.2f} vs plain {st.mean(b):.2f}."]
out = {d: cur.get(("warm", d), cur.get((modes[0], d), "plain")) for d in ("click", "keys", "mixed")}
out["default"] = "plain"
json.dump(out, open(os.path.join(D, "curriculum_levels.json"), "w"), indent=1)
open(os.path.join(D, "level_board.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("curriculum (warm):", out)
