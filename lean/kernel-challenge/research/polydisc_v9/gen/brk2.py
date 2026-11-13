import sys, random, re
import lowdag
from lowdag import *
import reference_answers as ref
# tag ops by the function that created them
import inspect
orig = Dag.op
def op(s, name, a, b):
    key = (name, a, b)
    new = key not in s.memo
    r = orig(s, name, a, b)
    if new and name == "mul":
        fr = inspect.stack()[1:6]
        fn = next((f.function for f in fr if f.function in ("lc1", "newton", "zlin", "lstep", "build")), "?")
        if fn == "lc1":
            ln = next(f.code_context[0] for f in fr if f.function == "lc1")
            fn += ":" + ln.strip()[:2]
        s.roles = getattr(s, "roles", []) ; s.roles.append((fn, s.cost[-1]))
    return r
Dag.op = op
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
g, res, bad = build([zenc(c) for c in P])
from collections import defaultdict
groups = defaultdict(list)
for fn, c in g.roles: groups[fn].append(c)
for k, ops in sorted(groups.items()):
    v = price(ops, "r_" + re.sub(r"\W", "_", k))
    print(f"{k:12s} n={len(ops):6d}  GMP={v/1e6:7.1f}M")
