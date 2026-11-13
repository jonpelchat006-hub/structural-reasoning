import sys, random
from lowdag2 import *
from gen8 import v7_ops
import reference_answers as ref, prs_model as pm
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]
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
for k, p in enumerate(chain): assert max(abs(c) for c in p) < 2 ** (QW[k] - 1), k
tl = tv = 0
for k in range(23):
    F, G = chain[k], chain[k + 1]
    res = lambda c, q: c % (1 << q)
    inp = [res(c, QW[k]) for c in F] + [res(c, QW[k + 1]) for c in G] + [0, TAB]
    nf = len(F); Fr = [("x", i) for i in range(nf)]; Gr = [("x", nf + i) for i in range(len(G))]
    g1 = Dag(inp); lstep = low2_ops(g1, ("x", len(inp) - 1))
    H, bad = lstep(QW[k], QW[k + 1], QW[k + 2], k == 0, [] if k == 0 else ladder(QW[k + 2] + 128), Fr, Gr)
    assert [g1.val(h) for h in H] == [res(c, QW[k + 2]) for c in chain[k + 2]] and g1.val(bad) == 0, k
    inp2 = [zenc(c) for c in F] + [zenc(c) for c in G]
    g2 = Dag(inp2); run = v7_ops(g2); run(1, Fr, Gr, ("c", 0))
    a, b = price(g1.cost, f"p2_l{k}"), price(g2.cost, f"p2_v{k}")
    tl += a; tv += b
    print(f"step {k:2d} q={QW[k+2]:6d} low {a/1e6:6.1f}M ({len(g1.lines)} nodes)  v7 {b/1e6:6.1f}M ({len(g2.lines)} nodes)", flush=True)
print(f"total low {tl/1e6:.1f}M  v7 {tv/1e6:.1f}M")
