"""price each PRS step: low part vs v7's exact element step, on the exact chain of a D5 input"""
import sys, random
from lowdag import *
from gen8 import v7_ops
import reference_answers as ref, prs_model as pm
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
# exact chain
F, G = P, pm.deriv(P); chain = [F, G]; first = True
while len(G) > 1:
    dm = 1 if first else F[0] ** 2
    lf, lg = F[0], G[0]; c1 = lg * F[1] - lf * G[1]
    H = []
    for j in range(len(F) - 2):
        x = F[j + 2]; z = G[j + 1]; y = G[j + 2] if j + 2 < len(G) else 0
        e = lg * lg * x - lg * lf * y - c1 * z
        assert e % dm == 0; H.append(e // dm)
    chain.append(H); F, G, first = G, H, False
tl, tv = 0, 0
for k in range(23):
    F, G = chain[k], chain[k + 1]; d = 22 - k
    inp = [zenc(c) for c in F] + [zenc(c) for c in G] + [0, TAB]
    nf = len(F)
    Fr = [("x", i) for i in range(nf)]; Gr = [("x", nf + i) for i in range(len(G))]
    g1 = Dag(inp); lstep = low_ops(g1, ("x", len(inp) - 1))
    H, bad = lstep(QD[d], k == 0, ladder(QD[d]), Fr, Gr)
    assert [zdec(g1.val(h)) for h in H] == chain[k + 2] and g1.val(bad) == 0, k
    g2 = Dag(inp); run = v7_ops(g2)
    dm = ("c", 1) if k == 0 else g2.mul(g2.shr(Fr[0], 1), g2.shr(Fr[0], 1))
    # one v7 step = run(1, ...) with explicit dm: reimplement via run on k=1 needs dmOf(F); for k=0 dm=1
    if k == 0:
        r = None
    a = price(g1.cost, f"ps_l{k}")
    # v7 step: run(1, F, G, 0) uses dmOf(F) = lc^2; for the first step v7 uses dm = 1 (runAll)
    if k == 0:
        g2 = Dag(inp); runf = v7_ops(g2)
    out = runf if k == 0 else run
    res = out(1, Fr, Gr, ("c", 0))
    b = price(g2.cost, f"ps_v{k}")
    tl += a; tv += b
    print(f"step {k:2d} d={d:2d} q={QD[d]:6d} coefs={len(chain[k+2]):2d}  low {a/1e6:6.1f}M ({len(g1.lines)} nodes)  v7 {b/1e6:6.1f}M ({len(g2.lines)} nodes)", flush=True)
print(f"total low {tl/1e6:.1f}M  v7 {tv/1e6:.1f}M")
