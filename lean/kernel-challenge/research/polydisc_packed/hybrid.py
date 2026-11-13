"""Packed prefix (segmented lanes) + v7 element steps for the tail: price every switch point."""
import sys, json
sys.path.insert(0, "/home/claude/polypack"); sys.path.insert(0, "/home/claude/polyvar")
from packdag import *
import cost, seg, reference_answers as ref, prs_model as pm
OPC = 5000
NODES_PER_ELT, NODES_PER_STEP = 28, 0

def v7_step_costs(P):
    """per step: v7 graph nodes ≈ 28 per element; GMP from the element products and divisions"""
    F, G = P, pm.deriv(P); out = []; first = True
    while len(G) > 1:
        L = pm.Log()
        H = pm.step(F, G, 1 if first else F[0] * F[0], L)
        ops = [("mul", a, b) for a, b in L.mul] + [("div", max(a - b, 1), b) for a, b in L.div if not first]
        out.append(cost.price(ops) + OPC * NODES_PER_ELT * len(H))
        F, G = G, H; first = False
    return out

if __name__ == "__main__":
    for band, n in [(a, int(b)) for a, b in (x.split(":") for x in sys.argv[1:])]:
        P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
        v7c = v7_step_costs(P)
        print(band, "v7 model total", f"{sum(v7c):,}", "per step", [round(c / 1e6, 2) for c in v7c])
        best = None
        for ts in range(4, 24):
            # packed for steps < ts: DP over segments restricted to those steps
            res, _ = seg.plan(band, n)
            break
        bs = sorted({seg.need(band, t, (0.02, 16)) for t in range(23)})
        sc = {b: seg.step_costs(fz, b) for b in bs}
        rows = []
        for ts in range(1, 24):
            # best segmentation of steps 0..ts-1 (≤ 5 segments) by DP
            bestc = {0: 0}; 
            dp = [float("inf")] * (ts + 1); dp[0] = 0
            for e in range(1, ts + 1):
                for s0 in range(e):
                    b = max(seg.need(band, t, (0.02, 16)) for t in range(s0, e))
                    c = dp[s0] + sum(sc[b][t] for t in range(s0, e)) + (seg.repack_cost(24 - s0, 0, b) if s0 > 0 else 0)
                    dp[e] = min(dp[e], c)
            unpack = OPC * 7 * 2 * (24 - ts) if ts < 23 else 0
            tot = dp[ts] + unpack + sum(v7c[ts:])
            rows.append((tot, ts))
            print(f"  {band} switch at step {ts:2d}: packed {dp[ts]/1e6:6.2f}M + unpack {unpack/1e6:4.2f}M + v7 tail {sum(v7c[ts:])/1e6:6.2f}M = {tot/1e6:6.2f}M", flush=True)
        print(band, "best", min(rows))
