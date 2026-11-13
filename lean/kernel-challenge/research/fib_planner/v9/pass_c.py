"""Pass C: can neighbouring chains merge (one test fewer)? Price the larger chain on the smaller inputs."""
import json, sys
sys.path.insert(0, "/home/claude/fibvar"); sys.set_int_max_str_digits(0)
import pass_a, planner3 as p3
P = p3.Plan3
# a plan's L only selects its point list here; the chain itself is valid for every n < 2^(t + P + r)
PTS = {15: [20749, 21083, 21210, 21877, 21965], 17: [82769, 82856, 83842, 83889, 88554, 91056, 128320, 130509]}
plans = [P(15, 8, 7, 7, "A", "m0", "sg"),     # = chain16's plan (16 = 8 + 7 + 1) priced on 15-bit inputs
         P(17, 8, 7, 6, "E", "m0", "sg")]     # chain17 itself, for the paired reference
plans_merge = [("m16on15", p3.Plan3(16, 8, 7, 7, "A", "m0", "sg"), 15), ("m18on17", p3.Plan3(18, 8, 7, 6, "E", "m0", "sg"), 17)]
import xbench
from planner import fib_pair
extra = p3.common_defs() + "\n" + "\n".join(p3.emit(p, f"pm{i}") for i, (_, p, _) in enumerate(plans_merge))
cases = [(f"{i}|{n}", f"pm{i} n", n, fib_pair(n)[0]) for i, (_, p, L) in enumerate(plans_merge) for n in PTS[L]]
res = xbench.run(cases, extra_defs=extra, workers=2)
out = {}
for k, w in res.items():
    i, n = k.split("|"); out.setdefault(plans_merge[int(i)][0], {})[int(n)] = w
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
