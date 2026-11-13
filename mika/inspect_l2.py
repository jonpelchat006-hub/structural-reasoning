"""What does Mika carry between lives, and what happens on level 2? (read-only summary of her journals)"""
import json
from collections import Counter
for game in ["sp80", "ls20"]:
    j = json.load(open(rf"D:\planet\mika\{game}.json", encoding="utf-8"))
    print(f"\n===== {game}: {len(j['lives'])} lives, routes {{level: presses}} = { {int(k) + 1: v['len'] for k, v in j.get('routes', {}).items()} }")
    print("keys kept in journal:", list(j.keys()))
    print("facts:", len(j.get("facts", [])), "| questions:", len(j.get("questions", [])), "| picks per level:", {k: len(v) for k, v in j.get("picks", {}).items()},
          "| things remembered:", len(j.get("things", {})))
    seen = Counter(); new_per_life = []
    for n, l in enumerate(j["lives"], 1):
        ex = [e for e in l.get("experiments", []) if e.get("level") == 1]
        keys = [str(e.get("goal") or e.get("id") or e.get("what")) for e in ex]
        new = sum(1 for k in set(keys) if seen[k] == 0)
        for k in keys: seen[k] += 1
        res = Counter(str(e.get("result") or e.get("outcome"))[:20] for e in ex)
        lp = l.get("level_presses")
        refl = l.get("reflection") or {}
        print(f" life {n:2d} {l['date']}: levels {l['levels']}, presses {l['presses']}, deaths {l['deaths']}, resets {l['voluntary_resets']}, "
              f"level presses {lp}, L2 experiments {len(ex)} ({new} never tried before), results {dict(res.most_common(4))}, "
              f"mind moves {len(l.get('mind_moves', []))}, reflection {'yes' if refl.get('what_happened') else 'no'} {('(' + refl.get('model', '') + ')') if refl else ''}")
    print(" distinct L2 experiments over all lives:", len(seen), "| tried 3+ times:", sum(1 for v in seen.values() if v >= 3))
    if j["lives"] and j["lives"][-1].get("experiments"):
        print(" example experiment record:", json.dumps(j["lives"][-1]["experiments"][-1])[:300])
