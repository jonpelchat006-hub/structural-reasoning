"""+C at the general rung: does the last win's form (its slots, with the colours they were bound to) carry
to the next level of the same game?  For consecutive levels (k-1 won, k inside the school):
  form      the + slots of level k-1's winning press, each with its binding (colours of the still thing
            arrived at, the thing touched, the far indicator, the matched thing ...)
  test      on level k: route presses vs arbitrary board-changing presses that have the slot AND share a
            bound colour; and the slot alone (no binding) for comparison. Winning press of k: has the bound form?
  python bindings.py trail/coreslots.json trail/bindings.md"""
import json, sys
import numpy as np
from collections import defaultdict

rows = {r["key"]: r for r in json.load(open(sys.argv[1]))}
PLUS = ["CONTROL+", "CONTACT+", "MATCH+", "PLACE+", "COUNT+", "ORDER+"]
res = defaultdict(lambda: dict(rb=[], ab=[], rs=[], as_=[], win_b=0, win_s=0, n=0, games=set()))
pairs = []
for k, r in rows.items():
    g, lv = k.split(":")[0], int(k.split(":")[1])
    p = rows.get(f"{g}:{lv - 1}")
    if not p:
        continue
    pairs.append(k)
    for s in PLUS:
        if s not in p["win"] or not p["win_b"].get(s):
            continue
        C = set(p["win_b"][s])
        R = res[s]; R["n"] += 1; R["games"].add(g)
        rp = list(zip(r["route"] + [r["win"]], r["route_b"] + [r["win_b"]]))
        ap = [(S, b) for S, b in zip(r["rand"], r["rand_b"]) if "CONTROL-" not in S]
        R["rb"] += [s in S and bool(C & set(b.get(s, []))) for S, b in rp]
        R["ab"] += [s in S and bool(C & set(b.get(s, []))) for S, b in ap]
        R["rs"] += [s in S for S, b in rp]
        R["as_"] += [s in S for S, b in ap]
        R["win_b"] += s in r["win"] and bool(C & set(r["win_b"].get(s, [])))
        R["win_s"] += s in r["win"]
L = ["# +C at the general rung: the last win's form, with its bindings, on the next level", "",
     f"{len(pairs)} levels whose previous level is also inside the school ({', '.join(sorted(pairs))}).", "",
     "| slot of the last winning press | level pairs (games) | route presses: slot + bound colour | arbitrary: slot + bound colour | lift (bound) | route: slot alone | arbitrary: slot alone | lift (slot alone) | next winning press has the bound form | has the slot |",
     "|---|---|---|---|---|---|---|---|---|---|"]
for s in PLUS:
    R = res.get(s)
    if not R or not R["n"]:
        continue
    f = lambda x: np.mean(x) if x else 0.0
    lb = f(R["rb"]) / f(R["ab"]) if f(R["ab"]) else float("inf")
    ls = f(R["rs"]) / f(R["as_"]) if f(R["as_"]) else float("inf")
    L.append(f"| {s} | {R['n']} ({len(R['games'])}) | {f(R['rb']):.0%} | {f(R['ab']):.1%} | {lb:.1f}x | {f(R['rs']):.0%} | {f(R['as_']):.1%} | {ls:.1f}x | {R['win_b']} of {R['n']} | {R['win_s']} of {R['n']} |")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("\n".join(L))
