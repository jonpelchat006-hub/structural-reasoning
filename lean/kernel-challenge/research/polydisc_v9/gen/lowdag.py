"""polydisc v9: the low-part normal PRS for the D5 band, as a hash-consed Nat graph.

Mirrors the Lean structured run (V9/Low.lean) op by op:
  lstep q first nw F G  ->  (H, bad)   with H = F_{k+2} (z-encoded), all coefficients computed
  mod 2^q (q from the size certificate) and sign-lifted.
Per step: lf = lc F, sh = v2(lf) (gcd + de Bruijn lookup, checked), M = 2^(q + 2 sh),
the three multipliers reduced mod M, the odd part's square inverted mod 2^q (Newton).
Per coefficient: three magnitude products mod M, the signed sum, >> 2sh, x inverse, mod 2^q,
sign lift, z-encode."""
import sys, json, random, subprocess
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge"); sys.path.insert(0, "/home/claude/polyvar")
sys.path.insert(0, "/home/claude/polyv8")
from gen8 import Dag, zenc, zdec

M64 = (1 << 64) - 1
DB = 0x022fdd63cc95386d
def db_index(s): return ((DB << s) & M64) >> 58
assert len({db_index(s) for s in range(64)}) == 64
TAB = sum(s << (8 * db_index(s)) for s in range(64))

CERT = json.load(open("/home/claude/v9dev/gen/cert_3484.json"))
QD = {c["d"]: c["q"] for c in CERT}

def ladder(q, p0=3):
    out, p = [], p0
    while p < q:
        p = min(2 * p, q); out.append(p)
    return out

def low_ops(g, TABr):
    """the low-part step on graph g (TABr: the dbTab input)"""
    hd = lambda L: L[0] if L else ("c", 0)
    def zlin(a, b, c, d):   # v7's zlin: a*b - c*d on encoded integers (exact)
        zP = lambda T, N: g.sub(T, N)
        zD = lambda T, N: g.sub(N, zP(T, N))
        zMag = lambda T, N: g.add(g.sub(zP(T, N), N), zD(T, N))
        zSgn = lambda T, N: g.sub(1, g.sub(1, zD(T, N)))
        zq = lambda T, N, dm: g.add(g.shl(g.div(zMag(T, N), dm), 1), zSgn(T, N))
        pm = lambda a, b: g.mul(g.shr(a, 1), g.shr(b, 1))
        return zq(g.add(pm(a, b), pm(c, d)),
                  g.add(g.mul(g.land(g.xor(a, b), 1), pm(a, b)), g.mul(g.xor(g.land(g.xor(c, d), 1), 1), pm(c, d))), 1)
    def newton(a, x, nw):
        for p in nw:
            mp = g.sub(g.shl(1, p), 1)
            t = g.land(g.mul(g.land(a, mp), x), mp)
            x = g.land(g.mul(x, g.sub(g.add(mp, 3), t)), mp)
        return x
    def lc1(mA, mC, sC, m1, s1, mask, K, sh2, qm, qh, Q2, x, y, z):
        p1 = g.land(g.mul(mA, g.shr(x, 1)), mask)
        p2 = g.land(g.mul(mC, g.shr(y, 1)), mask)
        p3 = g.land(g.mul(m1, g.shr(z, 1)), mask)
        ng = g.add(g.add(g.mul(g.land(x, 1), p1), g.mul(g.xor(g.land(y, 1), sC), p2)), g.mul(g.xor(g.land(z, 1), s1), p3))
        r = g.sub(g.add(g.add(g.add(p1, p2), p3), K), g.shl(ng, 1))
        u = g.land(g.shr(r, sh2), qm)
        s = g.shr(u, qh)
        sQ = g.mul(s, Q2)
        return g.add(g.shl(g.add(g.sub(u, sQ), g.sub(sQ, u)), 1), s)
    def lstep(q, first, nw, F, G):
        lf, lg = hd(F), hd(G)
        mlf, mlg = g.shr(lf, 1), g.shr(lg, 1)
        xL = g.land(mlf, M64)
        if first: sh = ("c", 0)
        else:
            P = g.op("gcd", xL, g.shl(1, 64))
            idx = g.shr(g.land(g.mul(P, DB), M64), 58)
            sh = g.land(g.shr(TABr, g.shl(idx, 3)), 255)
        sh2 = g.shl(sh, 1)
        M = g.shl(1, g.add(q, sh2))
        mask = g.sub(M, 1)
        K = g.shl(M, 2)
        c1 = zlin(lg, hd(F[1:]), lf, hd(G[1:]))
        qm = g.sub(g.shl(1, q), 1)
        Q2 = g.shl(1, q)
        if first: inv = ("c", 1)
        else:
            o = g.shr(mlf, sh)
            a = g.land(g.mul(o, o), qm)
            inv = newton(a, a, nw)
        mA = g.land(g.mul(g.land(g.mul(mlg, mlg), mask), inv), mask)
        mC = g.land(g.mul(g.land(g.mul(mlg, mlf), mask), inv), mask)
        sC = g.xor(g.land(g.xor(lg, lf), 1), 1)
        m1 = g.land(g.mul(g.land(g.shr(c1, 1), mask), inv), mask)
        s1 = g.xor(g.land(c1, 1), 1)
        xs, zs = F[2:], G[1:]
        H = [lc1(mA, mC, sC, m1, s1, mask, K, sh2, qm, ("c", q - 1), Q2, xs[j], hd(zs[j + 1:]), zs[j])
             for j in range(min(len(xs), len(zs)))]
        if first: chk = ("c", 0)
        else: chk = g.add(g.sub(1, g.land(g.shr(xL, sh), 1)), g.land(xL, g.sub(g.shl(1, sh), 1)))
        return H, g.add(chk, g.sub(1, g.shr(hd(H), 1)))
    return lstep

def build(fz, qd=QD, modes=None):
    """graph over inputs x0..x24 (encoded coefficients), x25 = Prod.mk, x26 = dbTab"""
    g = Dag(list(fz) + [0, TAB])
    lstep = low_ops(g, ("x", 26))
    hd = lambda L: L[0] if L else ("c", 0)
    X = [("x", i) for i in range(25)]
    # derivative (v7's gz): ((f >> 1) * k << 1) + (f & 1)
    G = [g.add(g.shl(g.mul(g.shr(X[i], 1), 24 - i), 1), g.land(X[i], 1)) for i in range(24)]
    F, Gc = X, G
    H, bad = lstep(qd[22], True, [], F, Gc)
    F, Gc = Gc, H
    for d in range(21, -1, -1):
        H, b = lstep(qd[d], False, ladder(qd[d]), F, Gc)
        bad = g.add(bad, b)
        F, Gc = Gc, H
    return g, hd(Gc), bad


def gcd_patch():
    """teach the Dag the gcd op"""
    import math
    orig = Dag.op
    def op(s, name, a, b):
        if name != "gcd": return orig(s, name, a, b)
        key = (name, a, b)
        if key in s.memo: return s.memo[key]
        v = math.gcd(s.val(a), s.val(b))
        s.vals.append(v); s.lines.append(f"gcd {s.tok(a)} {s.tok(b)}")
        s.cost.append(("and", 64, 64))
        r = ("v", len(s.vals) - 1); s.memo[key] = r
        return r
    Dag.op = op
gcd_patch()

def price(ops, tag):
    p = f"/tmp/ops_{tag}.txt"
    open(p, "w").write("".join(f"{o} {max(a, 1)} {max(b, 1)}\n" for o, a, b in ops))
    out = f"/tmp/cg_{tag}.out"
    subprocess.run(f"valgrind --tool=callgrind --collect-atstart=no --callgrind-out-file={out} /home/claude/gmpcost/gmpcost < {p}",
                   shell=True, capture_output=True)
    for l in open(out):
        if l.startswith("summary:"): return int(l.split()[1])

if __name__ == "__main__":
    import reference_answers as ref
    random.seed(5)
    ns = [random.randint(2 ** 57, 2 ** 63) for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2)]
    for n in ns:
        P = ref.candidate_polynomial(n)[0]
        fz = [zenc(c) for c in P]
        g, res, bad = build(fz)
        want = ref.polynomial_discriminant(P)
        got = zdec(g.val(res))
        ok = (got == want) and g.val(bad) == 0
        line = f"n={n}: ok={ok} bad={g.val(bad)} nodes={len(g.lines)}"
        if len(sys.argv) > 2:
            gm = price(g.cost, f"low{n % 1000}")
            line += f" GMP={gm / 1e6:.1f}M"
        print(line, flush=True)
