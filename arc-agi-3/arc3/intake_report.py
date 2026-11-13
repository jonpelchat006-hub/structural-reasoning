"""Intake: what the trail brought in, oriented to the school.

  python intake_report.py trail/frontier.json trail/frontier_casebook.json [reach.json]
reach.json (optional): a whole-game run (harness output) - which levels she reaches by playing in order."""
import json, sys, collections, statistics as st
sys.path[:0] = [".", "fw"]
from mika3.university import PUBLIC_DEPT, EXAM

fr = json.load(open(sys.argv[1])); book = json.load(open(sys.argv[2]))
reach = set()
if len(sys.argv) > 3:
    for r in json.load(open(sys.argv[3])):
        for lv in range(r["levels"]):
            reach.add((r["game"][:4], lv))
lv_all = collections.defaultdict(set)
for r in fr:
    lv_all[r["game"][:4]].add(r["level"])
lines = ["# Intake from the trail", "",
         f"Frontier: the top Mika dropped cold into every level of every public game ({len(fr)} level runs). "
         f"**{len(book)} of {sum(len(v) for v in lv_all.values())} levels came inside the school** (won at least once).", ""]
if reach:
    beyond = [k for k in book if (k.split(':')[0], int(k.split(':')[1])) not in reach]
    lines += [f"Of those, {len(beyond)} lie beyond what she reaches playing each game in order (whole-game runs reach "
              f"{len(reach)} levels): the trail had levels she could win but never got to.", ""]
lines += ["| department | levels inside / total | mean run length on route | routes with clicks | final press click / A5 / move | waste (spent / shortest) | shortest / human |",
          "|---|---|---|---|---|---|---|"]
for dept in ("click", "keys", "mixed"):
    cs = [c for c in book.values() if c["dept"] == dept]
    tot = sum(len(v) for g, v in lv_all.items() if PUBLIC_DEPT[g] == dept)
    if not cs:
        lines.append(f"| {dept} | 0 / {tot} | | | | | |"); continue
    mr = st.mean(c["mean_run"] for c in cs if c["mean_run"])
    wc = sum(1 for c in cs if c["clicks"]) / len(cs)
    fin = collections.Counter("click" if c["final"] == 6 else ("A5" if c["final"] == 5 else "move") for c in cs)
    waste = sum(c["frontier_presses"] for c in cs) / max(1, sum(c["shortest"] for c in cs))
    sh = sum(c["shortest"] for c in cs) / max(1, sum(c["baseline"] or 0 for c in cs))
    lines.append(f"| {dept} | {len(cs)} / {tot} | {mr:.1f} | {wc:.0%} | {fin['click']} / {fin['A5']} / {fin['move']} | {waste:.0f}x | {sh:.2f} |")
lines += ["", "Per game: levels inside (L1 = first level).", ""]
for g in sorted(lv_all):
    ins = sorted(int(k.split(':')[1]) + 1 for k in book if k.startswith(g + ":"))
    lines.append(f"- {g} ({PUBLIC_DEPT[g]}{', practice final' if g in EXAM else ''}): {len(ins)}/{len(lv_all[g])} - "
                 + (", ".join(f"L{x}" for x in ins) if ins else "none"))
print("\n".join(lines))
open(sys.argv[2].replace("frontier_casebook.json", "intake.md"), "w").write("\n".join(lines) + "\n")
