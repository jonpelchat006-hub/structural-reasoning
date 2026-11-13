import sys, itertools, time
sys.path.insert(0, "/home/claude/polyv8"); sys.path.insert(0, "/home/claude/polypack")
from gen8 import *
import reference_answers as ref, cost
band, n = sys.argv[1], int(sys.argv[2])
P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P] + [0]
want = ref.compute_answer("polydisc", n)
best = []
t0 = time.time()
LB = int(sys.argv[5]) if len(sys.argv) > 5 else 99
srange = range(int(sys.argv[3]), int(sys.argv[4]) + 1)
for steps in srange:
    for k in range(0, 4):
        for cs in itertools.combinations(range(1, steps), k):
            cuts = [0] + list(cs)
            sched = schedule(band, cuts, steps)
            g, res, bad = build(fz, sched, steps, LB)
            assert zdec(g.val(res)) == want and g.val(bad) == 0
            est = cost.price(g.cost) + 5000 * len(g.lines)
            best.append((est, steps, cuts, len(g.lines)))
    best.sort(); print(steps, best[:1], f"{time.time()-t0:.0f}s", flush=True)
best.sort()
for r in best[:8]: print(r)
