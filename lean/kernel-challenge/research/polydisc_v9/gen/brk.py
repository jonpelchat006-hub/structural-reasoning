import sys, random
from lowdag import *
import reference_answers as ref
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
g, res, bad = build([zenc(c) for c in P])
from collections import defaultdict
groups = defaultdict(list)
for line, c in zip(g.lines, g.cost):
    groups[line.split()[0]].append(c)
tot = 0
for k, ops in sorted(groups.items()):
    v = price(ops, "brk_" + k); tot += v
    print(f"{k:5s} n={len(ops):6d}  GMP={v/1e6:7.1f}M")
print("total", tot / 1e6)
# big multiplies by size class
muls = [c for line, c in zip(g.lines, g.cost) if line.startswith("mul") and min(c[1], c[2]) > 64]
print("big muls", len(muls))
