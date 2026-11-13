"""Hindsight report over a multi-seed run: per won level, actions spent vs the shortest known path
(Jonathan's look-back), and what the winning path used."""
import json, sys, statistics as st, collections
res = json.load(open(sys.argv[1]))
rows = collections.defaultdict(list)
for r in res:
    for w in (r.get("wins") or []):
        rows[(r["game"][:4], w["level"])].append((w["spent"], w["shortest"], r["level_baseline"][w["level"]] if r.get("level_baseline") else None, w.get("kinds"), w.get("goal")))
tot_sp, tot_sh, tot_b = 0, 0, 0
print(f"{'game':5s}{'lvl':>4s} {'n':>2s} {'spent':>7s} {'shortest':>9s} {'human':>6s} {'waste':>6s}  path kinds")
for (g, l), v in sorted(rows.items()):
    sp = st.mean(x[0] for x in v); sh = st.mean(x[1] for x in v); b = v[0][2]
    tot_sp += sp; tot_sh += sh; tot_b += b or 0
    print(f"{g:5s}{l:4d} {len(v):2d} {sp:7.0f} {sh:9.1f} {b if b else -1:6d} {sp / max(1, sh):6.1f}  {v[0][3]}")
print(f"all won levels: spent {tot_sp:.0f}  shortest {tot_sh:.0f}  human {tot_b}  waste x{tot_sp / max(1, tot_sh):.1f}  shortest/human {tot_sh / max(1, tot_b):.2f}")
