"""The goal professors against plain and against their control (pick-only: the same choice of where to go
next, no rung), on every level inside the school, level-weighted as the official card weights them.

  python goal_report.py trail uni  -> trail/goal_report.md"""
import json, os, sys, collections, statistics as st
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT

T, U = sys.argv[1], sys.argv[2]
PROFS = ["pick-only", "took-control", "took-light", "win-event", "two-rungs", "far-change", "far-change-win", "far-rare", "three-rungs", "win-image", "took-image", "two-rungs-image", "goal-search", "two-rungs-search"]


def exam(mode, prof):
    f = os.path.join(T, f"exam_{mode}_{prof.replace('-', '_')}.json")
    if not os.path.exists(f):
        return None
    t = collections.defaultdict(dict)
    for r in json.load(open(f)):
        t[(r["game"][:4], r["level"])][r["seed"]] = r["score"]
    return t


def weighted(t, keys, seeds):
    W = sum(l + 1 for _, l in keys) or 1
    return [sum((l + 1) * t.get((g, l), {}).get(s, 0.0) for g, l in keys) / W for s in seeds]


lines = ["# Goal professors: graded against plain and against their control", "",
         "Control = **pick-only**: look a few steps further and go to the most promising unexplored place "
         "(every goal professor does this too); no rung. A rung earns its place only if it beats the control.", ""]
for mode in ("cold", "warm"):
    P = exam(mode, "plain"); C = exam(mode, "pick-only")
    seeds = sorted({s for v in P.values() for s in v})
    lines += [f"## {mode} level exams ({len(P)} inside levels, 4 seeds, level k weighs k)", "",
              "| professor | all | vs plain (seeds better) | vs control (seeds better) | click | keys | mixed |", "|---|---|---|---|---|---|---|"]
    keys_all = sorted(P)
    base = weighted(P, keys_all, seeds); ctl = weighted(C, keys_all, seeds)
    row = ["plain", f"{st.mean(base):.2f}", "", ""]
    for d in ("click", "keys", "mixed"):
        ks = [k for k in keys_all if PUBLIC_DEPT[k[0]] == d]
        row.append(f"{st.mean(weighted(P, ks, seeds)):.2f}")
    lines.append("| " + " | ".join(row) + " |")
    for p in PROFS:
        Q = exam(mode, p)
        if Q is None:
            continue
        q = weighted(Q, keys_all, seeds)
        dp = [a - b for a, b in zip(q, base)]; dc = [a - b for a, b in zip(q, ctl)]
        row = [p, f"{st.mean(q):.2f}", f"{st.mean(dp):+.2f} ({sum(x > 1e-9 for x in dp)}/{len(seeds)})",
               "" if p == "pick-only" else f"{st.mean(dc):+.2f} ({sum(x > 1e-9 for x in dc)}/{len(seeds)})"]
        for d in ("click", "keys", "mixed"):
            ks = [k for k in keys_all if PUBLIC_DEPT[k[0]] == d]
            a = weighted(Q, ks, seeds); b = weighted(P, ks, seeds); c = weighted(C, ks, seeds)
            row.append(f"{st.mean(a):.2f} ({st.mean(a) - st.mean(b):+.2f} / ctl {st.mean(a) - st.mean(c):+.2f})")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

# whole games
def game_tab(p):
    f = os.path.join(U, p.replace("-", "_") + ".json")
    if not os.path.exists(f):
        return None
    t = collections.defaultdict(dict)
    for r in json.load(open(f)):
        t[r.get("seed") or 0][r["game"][:4]] = r["score"]
    return t

P = game_tab("plain"); C = game_tab("pick-only")
if P:
    seeds = sorted(P)
    lines += ["## Whole games (25 public games, 8 seeds, 3,000 actions)", "",
              "| professor | mean | vs plain (seeds better) | vs control (seeds better) | games up / down by over 0.05 vs control |", "|---|---|---|---|---|"]
    m = lambda t, s: st.mean(t[s].values())
    lines.append(f"| plain | {st.mean(m(P, s) for s in seeds):.3f} | | | |")
    for p in PROFS:
        Q = game_tab(p)
        if Q is None:
            continue
        dp = [m(Q, s) - m(P, s) for s in seeds]
        dc = [m(Q, s) - m(C, s) for s in seeds] if C else None
        gd = {g: st.mean(Q[s][g] - (C or P)[s][g] for s in seeds) for g in P[seeds[0]]}
        up = ", ".join(f"{g} {v:+.2f}" for g, v in sorted(gd.items(), key=lambda x: -x[1]) if v > 0.05)
        dn = ", ".join(f"{g} {v:+.2f}" for g, v in sorted(gd.items(), key=lambda x: x[1]) if v < -0.05)
        lines.append(f"| {p} | {st.mean(m(Q, s) for s in seeds):.3f} | {st.mean(dp):+.3f} ({sum(x > 1e-9 for x in dp)}/8) | "
                     + ("" if (p == "pick-only" or not dc) else f"{st.mean(dc):+.3f} ({sum(x > 1e-9 for x in dc)}/8)")
                     + f" | up: {up or '-'}; down: {dn or '-'} |")
open(os.path.join(T, "goal_report.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
