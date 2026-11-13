"""Choose lane-width segments for the packed PRS by dynamic programming over the 23 steps."""
import sys, json
sys.path.insert(0, "/home/claude/polypack"); sys.path.insert(0, "/home/claude/polyvar")
from packdag import *
import cost, reference_answers as ref, prs_model as pm
SIZES = json.load(open("/home/claude/polypack/sizes.json"))
OPC = 5000

def need(band, t, margin):  # b covering polys t, t+1, t+2
    mx = SIZES[band]["max"]
    m = max(mx[t], mx[t + 1], mx[t + 2])
    return m + 1 + int(margin[0] * m) + margin[1]

def step_costs(fz, b):
    marks = []
    g, res, bad = build(fz, [b] * 23, True, marks)
    out = []
    for t in range(23):
        ops = g.cost[marks[t]:marks[t + 1]]
        out.append(cost.price(ops) + OPC * len(ops))
    return out

def repack_cost(d, b_old, b_new):
    W = 3 * b_new + 3
    ops = 0; lin = 0
    for dd in (d, d - 1):
        ops += 2 + 5 * (dd + 1)
        lin += (dd + 1) * (dd + 1) * W / 64 * 6     # adds/shifts on the growing packed number
    return int(ops * OPC + lin)

def plan(band, n, margin=(0.02, 16), max_segs=6):
    P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
    bs = sorted({need(band, t, margin) for t in range(23)})
    sc = {b: step_costs(fz, b) for b in bs}
    INF = float("inf")
    # best[e][k] = min cost of steps 0..e-1 with k segments, last segment ending at e
    best = {(0, 0): (0, None)}
    for e in range(1, 24):
        for s0 in range(e):
            b = max(need(band, t, margin) for t in range(s0, e))
            seg = sum(sc[b][t] for t in range(s0, e))
            for k in range(max_segs):
                if (s0, k) not in best: continue
                prev, _ = best[(s0, k)]
                bprev = None
                c = prev + seg + (repack_cost(24 - s0, 0, b) if s0 > 0 else 0)
                key = (e, k + 1)
                if key not in best or c < best[key][0]:
                    best[key] = (c, (s0, k, b))
    res = {}
    for k in range(1, max_segs + 1):
        if (23, k) not in best: continue
        c = best[(23, k)][0]; sched = [None] * 23; e, kk = 23, k
        while e > 0:
            _, (s0, kp, b) = best[(e, kk)]
            for t in range(s0, e): sched[t] = b
            e, kk = s0, kp
        res[k] = (c, sched)
    return res, fz

if __name__ == "__main__":
    for band, n in [("D1", 300000), ("D3", 1099511628553)]:
        res, fz = plan(band, n)
        for k, (c, sched) in res.items():
            g, r, bad = build(fz, sched, True)
            ok = zdec(g.val(r)) == ref.compute_answer("polydisc", n) and g.val(bad) == 0
            segs = sorted(set((sched.index(b), b) for b in sched))
            print(f"{band} segs={k}: model {c:,}  real {cost.price(g.cost) + OPC * len(g.lines):,} ops={len(g.lines)} ok={ok} {segs}", flush=True)
