"""polydisc v9: the low-part normal PRS for D5 with residue storage (two's complement, one width per
polynomial).  Mirrors V9/Low.lean op by op.

Each polynomial F_k is stored as residues u_e = F_k,e mod 2^(q_k) with |F_k,e| < 2^(q_k - 1), so
F_k,e = u_e - s_e 2^(q_k) with s_e = u_e >> (q_k - 1).
Step (A = F_k width qA, B = F_{k+1} width qB) -> C = F_{k+2} width q:
  sh = v2(lc A) (checked), M = 2^(q + 2 sh), inv = (odd part of lc A)^(-2) mod 2^q (Newton),
  multipliers (residues mod M):  m1 = lg^2 inv,  m2 = -lg lf inv,  m3 = (lf g1 - lg f1) inv,
  corrections c1 = m1 2^qA, c2 = m2 2^qB, c3 = m3 2^qB (mod M),
  per coefficient:  u = ((m1 uA_e + m2 uB_{e-1} + m3 uB_e + 4M - (sA c1 + sB' c2 + sB c3)) >> 2sh) mod 2^q."""
import sys, json, random, subprocess, math
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge"); sys.path.insert(0, "/home/claude/polyvar")
sys.path.insert(0, "/home/claude/polyv8")
from gen8 import Dag, zenc, zdec
import lowdag   # gcd op patch, TAB, ladder, price
from lowdag import TAB, DB, M64, ladder, price

CERT = json.load(open("/home/claude/v9dev/gen/cert_3484.json"))
QW = [3485, 3489] + [c["q"] for c in sorted(CERT, key=lambda c: -c["d"])]   # width of F_0 .. F_24
assert len(QW) == 25

def low2_ops(g, TABr):
    hd = lambda L: L[0] if L else ("c", 0)
    def newton(a, x, nw):
        for p in nw:
            mp = g.sub(g.shl(1, p), 1)
            t = g.land(g.mul(g.land(a, mp), x), mp)
            x = g.land(g.mul(x, g.sub(g.add(mp, 3), t)), mp)
        return x
    def coef(m1, m2, m3, c1, c2, c3, K, sh2, qm, qhA, qhB, x, y, z):
        S = g.add(g.add(g.mul(m1, x), g.mul(m2, y)), g.mul(m3, z))
        Cr = g.add(g.add(g.mul(g.shr(x, qhA), c1), g.mul(g.shr(y, qhB), c2)), g.mul(g.shr(z, qhB), c3))
        return g.land(g.shr(g.sub(g.add(S, K), Cr), sh2), qm)
    def coefL(m1, m3, c1, c3, K, sh2, qm, qhA, qhB, x, z):    # the constant coefficient (no y)
        S = g.add(g.mul(m1, x), g.mul(m3, z))
        Cr = g.add(g.mul(g.shr(x, qhA), c1), g.mul(g.shr(z, qhB), c3))
        return g.land(g.shr(g.sub(g.add(S, K), Cr), sh2), qm)
    def lstep(qA, qB, q, first, nw, A, B):
        lf, lg, f1, g1 = hd(A), hd(B), hd(A[1:]), hd(B[1:])
        qhA, qhB = ("c", qA - 1), ("c", qB - 1)
        QA, QB = g.shl(1, qA), g.shl(1, qB)
        sf = g.shr(lf, qhA)
        sfQ = g.mul(sf, QA)
        mlf = g.add(g.sub(lf, sfQ), g.sub(sfQ, lf))
        xL = g.land(lf, M64)
        if first: sh = ("c", 0)
        else:
            P = g.op("gcd", xL, g.shl(1, 64))
            idx = g.shr(g.land(g.mul(P, DB), M64), 58)
            sh = g.land(g.shr(TABr, g.shl(idx, 3)), 255)
        sh2 = g.shl(sh, 1)
        M = g.shl(1, g.add(q, sh2))
        mask = g.sub(M, 1)
        K = g.shl(M, 2)
        EA, EB = g.sub(M, QA), g.sub(M, QB)
        ext = lambda u, qh, E: g.add(u, g.mul(g.shr(u, qh), E))
        Lg, F1, G1 = ext(lg, qhB, EB), ext(f1, qhA, EA), ext(g1, qhB, EB)
        qm = g.sub(g.shl(1, q), 1)
        md = lambda x: g.land(x, mask)
        sel = lambda s, t: g.add(g.mul(s, t), g.mul(g.sub(1, s), g.sub(M, t)))    # s ? t : M - t
        if first: inv = ("c", 1)
        else:
            o = g.shr(mlf, sh)
            inv = newton(o, o, nw)
        w = md(g.mul(Lg, inv))
        m1 = md(g.mul(w, w))
        m2 = sel(sf, md(g.shl(w, sh)))
        h = md(g.shl(G1, sh))
        m3 = md(g.mul(g.sub(g.add(sel(g.sub(1, sf), h), M), md(g.mul(F1, w))), inv))
        c1 = md(g.shl(m1, qA)); c2 = md(g.shl(m2, qB)); c3 = md(g.shl(m3, qB))
        xs, zs = A[2:], B[1:]
        n = min(len(xs), len(zs))
        H = []
        for j in range(n):
            if j == n - 1:
                H.append(coefL(m1, m3, c1, c3, K, sh2, qm, qhA, qhB, xs[j], zs[j]))
            else:
                H.append(coef(m1, m2, m3, c1, c2, c3, K, sh2, qm, qhA, qhB, xs[j], zs[j + 1], zs[j]))
        if first: return H, g.sub(1, hd(H))
        chk = g.add(g.sub(1, g.land(g.shr(xL, sh), 1)), g.land(xL, g.sub(g.shl(1, sh), 1)))
        return H, g.add(chk, g.sub(1, hd(H)))
    return lstep

def build(fz, qw=QW):
    """graph over inputs x0..x24 (encoded coefficients), x25 = Prod.mk, x26 = dbTab"""
    g = Dag(list(fz) + [0, TAB])
    lstep = low2_ops(g, ("x", 26))
    X = [("x", i) for i in range(25)]
    qf, qg = qw[0], qw[1]
    QF, QG = g.shl(1, qf), g.shl(1, qg)
    def zres(mag, s, qm, Q):     # residue of (-1)^s mag mod Q = 2^q
        return g.land(g.add(g.mul(g.sub(1, s), mag), g.mul(s, g.sub(Q, mag))), qm)
    A = [zres(g.shr(x, 1), g.land(x, 1), g.sub(QF, 1), QF) for x in X]
    B = [zres(g.mul(g.shr(X[i], 1), 24 - i), g.land(X[i], 1), g.sub(QG, 1), QG) for i in range(24)]
    H, bad = lstep(qw[0], qw[1], qw[2], True, [], A, B)
    A, B = B, H
    for k in range(1, 23):
        H, b = lstep(qw[k], qw[k + 1], qw[k + 2], False, ladder(qw[k + 2] + 128), A, B)
        bad = g.add(bad, b)
        A, B = B, H
    u = B[0]; q = qw[24]
    s = g.shr(u, q - 1); sQ = g.mul(s, g.shl(1, q))
    res = g.add(g.shl(g.add(g.sub(u, sQ), g.sub(sQ, u)), 1), s)    # z-encoding of F_24
    return g, res, bad

if __name__ == "__main__":
    import reference_answers as ref
    random.seed(5)
    ns = [random.randint(2 ** 57, 2 ** 63) for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2)]
    for n in ns:
        P = ref.candidate_polynomial(n)[0]
        g, res, bad = build([zenc(c) for c in P])
        want = ref.polynomial_discriminant(P)
        ok = zdec(g.val(res)) == want and g.val(bad) == 0
        line = f"n={n}: ok={ok} bad={g.val(bad)} nodes={len(g.lines)}"
        if len(sys.argv) > 2: line += f" GMP={price(g.cost, f'low2_{n % 1000}') / 1e6:.1f}M"
        print(line, flush=True)
