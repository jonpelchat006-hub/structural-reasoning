import sys, random, re, inspect
from lowdag2 import *
import reference_answers as ref
orig = Dag.op
def op(s, name, a, b):
    key = (name, a, b); new = key not in s.memo
    r = orig(s, name, a, b)
    if new and name == "mul":
        fr = inspect.stack()[1:6]
        fn = next((f.function for f in fr if f.function in ("coef", "coefL", "newton", "lstep", "build", "zres", "<lambda>")), "?")
        f0 = next((f for f in fr if f.function == "lstep"), None)
        if fn in ("lstep", "<lambda>") and f0: fn += ":" + f0.code_context[0].strip()[:12]
        s.roles = getattr(s, "roles", []); s.roles.append((fn, s.cost[-1]))
    return r
Dag.op = op
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
g, res, bad = build([zenc(c) for c in P])
from collections import defaultdict
groups = defaultdict(list)
for fn, c in g.roles: groups[fn].append(c)
tot = 0
for k, ops in sorted(groups.items()):
    v = price(ops, "r3_" + re.sub(r"\W", "_", k)); tot += v
    print(f"{k:28s} n={len(ops):6d}  GMP={v/1e6:7.1f}M")
print(tot / 1e6)
