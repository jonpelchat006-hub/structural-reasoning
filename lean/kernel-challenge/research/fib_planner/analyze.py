#!/usr/bin/env python3
"""Read a pricing pass and report, per bit length, the cheapest plans against v7's plan."""
import json, sys
from collections import defaultdict
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl

rows = []
for f in sys.argv[1:]:
    rows += json.load(open(f))
by = defaultdict(list)
for r in rows:
    if r["ir"]: by[r["L"]].append(r)
tot_v7 = tot_best = 0
for L in sorted(by):
    rs = sorted(by[L], key=lambda r: r["ir"])
    v7 = [r for r in rs if r["plan"] == pl.V7[L].name()]
    v7ir = v7[0]["ir"] if v7 else None
    print(f"L={L} (n={rs[0]['n']}): v7 {pl.V7[L].name()} = {v7ir:,}" if v7ir else f"L={L}: v7 not measured")
    for r in rs[:6]:
        d = f"{r['ir'] - v7ir:+,}" if v7ir else ""
        print(f"   {r['plan']:24s} {r['ir']:>10,}  {d}")
    if v7ir: tot_v7 += v7ir; tot_best += rs[0]["ir"]
print(f"sum over L: v7 {tot_v7:,}  best {tot_best:,}  ({tot_best - tot_v7:+,}, {100 * (tot_best - tot_v7) / tot_v7:+.2f}%)")
