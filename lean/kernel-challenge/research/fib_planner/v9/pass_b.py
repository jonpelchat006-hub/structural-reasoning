"""Pass B: the best planner3 plans per size at the v8 comparison points (paired with v8's chains)."""
import json, sys
sys.path.insert(0, "/home/claude/fibvar"); sys.set_int_max_str_digits(0)
import pass_a, planner3 as p3
P = p3.Plan3
PTS = {14: [5125, 5185, 5342, 5459, 5677, 8905, 8990, 9502, 9511, 9786],
       15: [20749, 21083, 21210, 21877, 21965], 16: [34966, 35606, 36079, 36657, 39667],
       17: [82769, 82856, 83842, 83889, 88554, 91056, 128320, 130509],
       18: [137686, 138153, 143049, 147248, 147709, 149931]}
plans = [P(14, 7, 7, 7, "C", "m0", "sg"), P(14, 8, 6, 6, "C", "m0", "sg"),
         P(15, 7, 7, 7, "A", "m0", "sg"), P(15, 8, 6, 6, "A", "m0", "sg"), P(15, 8, 7, 7, "C", "m0", "sg"),
         P(16, 8, 7, 7, "A", "m0", "sg"), P(16, 7, 8, 8, "A", "m0", "sg"),
         P(17, 7, 8, 8, "E", "m0", "sg"), P(17, 7, 7, 7, "E", "m0", "sg"), P(17, 8, 7, 6, "E", "m0", "sg"),
         P(18, 8, 7, 6, "E", "m0", "sg"), P(18, 8, 7, 7, "E", "m0", "sg"), P(18, 7, 8, 7, "E", "m0", "sg"),
         P(18, 7, 8, 8, "E", "m0", "sg")]
pass_a.PTS = PTS
pass_a.run(plans, sys.argv[1], batch=20)
