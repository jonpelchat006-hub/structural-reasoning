"""Cross-game look-back: what do the shortest winning routes in her own maps consist of?"""
import json, sys, collections, statistics as st
res = json.load(open(sys.argv[1]))
acts_avail = {}
fin = collections.Counter(); comp = collections.Counter(); n = 0
per_game = collections.defaultdict(list)
for r in res:
    for w in (r.get("wins") or []):
        route = w.get("route") or []
        if not route: continue
        n += 1
        per_game[(r["game"][:4], w["level"])].append(route)
        a = route[-1][0]; fin["click" if a == 6 else f"A{a}"] += 1
        for c in route: comp["click" if c[0] == 6 else f"A{c[0]}"] += 1
print("won levels with a route:", n)
print("final press:", fin.most_common())
print("all presses on routes:", comp.most_common())
for (g, l), rs in sorted(per_game.items()):
    r = min(rs, key=len)
    print(f"{g} L{l+1}: {len(rs)} wins, shortest route {len(r)}: " + " ".join(("c" + (r_[2] or "")) if r_[0] == 6 else f"A{r_[0]}" for r_ in r)[:160])
