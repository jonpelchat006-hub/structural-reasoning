"""polydisc v8 graphs: the packed normal PRS (D1: all 23 steps; D3: a packed prefix, then v7's
element steps), as natdag% programs over the 25 encoded coefficients x0..x24 (x25 = Prod.mk).
The tail mirrors v7's structured `run` operation by operation (so `rfl` can link them)."""
import sys, json
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge"); sys.path.insert(0, "/home/claude/polyvar")

class Dag:
    """hash-consed Nat expression graph with values"""
    def __init__(s, inputs):
        s.vals = []; s.lines = []; s.inputs = list(inputs); s.cost = []; s.memo = {}
    def val(s, r):
        k, i = r
        return s.vals[i] if k == "v" else s.inputs[i] if k == "x" else i
    def tok(s, r):
        k, i = r
        return f"v{i}" if k == "v" else f"x{i}" if k == "x" else str(i)
    def big(s, c):
        """a constant above 2^64 as a node when it is 2^k, 2^k − 1 or m·2^k (keeps the source small)"""
        if c < (1 << 64): return ("c", c)
        if c & (c - 1) == 0: return s.op("shl", ("c", 1), ("c", c.bit_length() - 1))
        if c & (c + 1) == 0: return s.op("sub", s.big(c + 1), ("c", 1))
        k = (c & -c).bit_length() - 1
        if k > 0 and (c >> k) < (1 << 64): return s.op("shl", ("c", c >> k), ("c", k))
        return ("c", c)
    def op(s, name, a, b):
        if isinstance(a, int): a = s.big(a)
        if isinstance(b, int): b = s.big(b)
        if a[0] == "c" and a[1] >= (1 << 64): a = s.big(a[1])
        if b[0] == "c" and b[1] >= (1 << 64): b = s.big(b[1])
        key = (name, a, b)
        if key in s.memo: return s.memo[key]
        x, y = s.val(a), s.val(b)
        v = {"add": lambda: x + y, "sub": lambda: max(x - y, 0), "mul": lambda: x * y,
             "div": lambda: x // y if y else 0, "mod": lambda: x % y if y else x,
             "land": lambda: x & y, "xor": lambda: x ^ y, "shl": lambda: x << y, "shr": lambda: x >> y}[name]()
        s.vals.append(v); s.lines.append(f"{name} {s.tok(a)} {s.tok(b)}")
        bx, by = max(x.bit_length(), 1), max(y.bit_length(), 1)
        if name in ("div", "mod"): s.cost.append((name, max(v.bit_length() if name == "div" else bx - by, 1), by))
        elif name in ("shl", "shr"): s.cost.append((name, bx, y))
        else: s.cost.append(({"add": "add", "sub": "sub", "mul": "mul"}.get(name, "and"), bx, by))
        r = ("v", len(s.vals) - 1); s.memo[key] = r
        return r
    def __getattr__(s, name):
        if name in ("add", "sub", "mul", "div", "mod", "land", "xor", "shl", "shr"):
            return lambda a, b: s.op(name, a, b)
        raise AttributeError(name)

# ---------------- v7's structured run, mirrored op by op ----------------
def v7_ops(g):
    zP = lambda T, N: g.sub(T, N)
    zD = lambda T, N: g.sub(N, zP(T, N))
    zMag = lambda T, N: g.add(g.sub(zP(T, N), N), zD(T, N))
    zSgn = lambda T, N: g.sub(1, g.sub(1, zD(T, N)))
    zq = lambda T, N, dm: g.add(g.shl(g.div(zMag(T, N), dm), 1), zSgn(T, N))
    zr = lambda T, N, dm: g.sub(zMag(T, N), g.mul(g.div(zMag(T, N), dm), dm))
    pm = lambda a, b: g.mul(g.shr(a, 1), g.shr(b, 1))
    def zlin(a, b, c, d):
        return zq(g.add(pm(a, b), pm(c, d)),
                  g.add(g.mul(g.land(g.xor(a, b), 1), pm(a, b)), g.mul(g.xor(g.land(g.xor(c, d), 1), 1), pm(c, d))), 1)
    eT = lambda mA, mC, m1, x, y, z: g.add(g.add(g.mul(mA, g.shr(x, 1)), g.mul(mC, g.shr(y, 1))), g.mul(m1, g.shr(z, 1)))
    def eN(mA, mC, sC, m1, s1, x, y, z):
        return g.add(g.add(g.mul(g.land(x, 1), g.mul(mA, g.shr(x, 1))),
                           g.mul(g.xor(g.land(y, 1), sC), g.mul(mC, g.shr(y, 1)))),
                     g.mul(g.xor(g.land(z, 1), s1), g.mul(m1, g.shr(z, 1))))
    hd = lambda L: L[0] if L else ("c", 0)
    def coef(F, G):
        mA = g.mul(g.shr(hd(G), 1), g.shr(hd(G), 1)); mC = g.mul(g.shr(hd(G), 1), g.shr(hd(F), 1))
        sC = g.xor(g.land(g.xor(hd(G), hd(F)), 1), 1)
        c1 = zlin(hd(G), hd(F[1:]), hd(F), hd(G[1:]))
        return mA, mC, sC, g.shr(c1, 1), g.xor(g.land(c1, 1), 1), c1
    def stepQ(dm, F, G):
        mA, mC, sC, m1, s1, _ = coef(F, G)
        xs, zs = F[2:], G[1:]; out = []
        for j in range(min(len(xs), len(zs))):
            y = hd(zs[j + 1:])
            out.append(zq(eT(mA, mC, m1, xs[j], y, zs[j]), eN(mA, mC, sC, m1, s1, xs[j], y, zs[j]), dm))
        return out
    def fold(f, F, G):   # right fold  add(f(0), add(f(1), ... add(f(n-1), 0)))
        mA, mC, sC, m1, s1, _ = coef(F, G)
        xs, zs = F[2:], G[1:]; n = min(len(xs), len(zs))
        acc = ("c", 0)
        for j in range(n - 1, -1, -1):
            y = hd(zs[j + 1:])
            acc = g.add(f(eT(mA, mC, m1, xs[j], y, zs[j]), eN(mA, mC, sC, m1, s1, xs[j], y, zs[j])), acc)
        return acc
    def stepR(dm, F, G):
        sm = fold(lambda T, N: zMag(T, N), F, G)
        sq = fold(lambda T, N: g.div(zMag(T, N), dm), F, G)
        return g.sub(sm, g.mul(dm, sq))
    def stepBad(dm, F, G):
        c1 = coef(F, G)[5]
        return g.add(g.add(g.sub(1, g.shr(c1, 1)), stepR(dm, F, G)), g.sub(1, g.shr(hd(stepQ(dm, F, G)), 1)))
    dmOf = lambda F: g.mul(g.shr(hd(F), 1), g.shr(hd(F), 1))
    def run(k, F, G, bad):
        while k > 0:
            dm = dmOf(F)
            F, G, bad = G, stepQ(dm, F, G), g.add(bad, stepBad(dm, F, G))
            k -= 1
        return hd(G), bad
    return run

# ---------------- the packed steps ----------------
def lanes_R(g, W, L):
    """R = 1 + B + … + B^(L-1), built by doubling (B = 2^W)"""
    R, n = ("c", 1), 1
    while 2 * n <= L:
        R = g.add(R, g.shl(R, W * n)); n *= 2
    while n < L:
        R = g.add(R, g.shl(1, W * n)); n += 1
    return R

def packed(g, sched, steps, lowbits_from=99):
    """steps 0..steps-1 packed with b = sched[t] (W = 3b+3). Returns the state."""
    D = 24
    b = sched[0]; W = 3 * b + 3; T, B = 1 << b, 1 << W
    R = lanes_R(g, W, 25)
    Rd = lambda d: g.shr(R, W * (24 - d))          # 1 + … + B^d
    dF, dG = [], []
    for i in range(D + 1):
        if i == 0: dF.append(("c", 1 + T)); dG.append(("c", 24 + T)); continue
        x = ("x", i)
        h = g.shr(x, 1); e = g.land(x, 1)
        d_ = g.sub(g.add(h, T), g.mul(g.shl(h, 1), e))
        dF.append(d_)
        if i < D:
            dG.append(g.sub(g.mul(d_, D - i), (D - 1 - i) * T) if D - i > 1 else d_)
    def pack(ds, W):
        n = len(ds) - 1; u = ds[n]
        for i in range(n - 1, -1, -1):
            u = g.add(u, g.shl(ds[i], W * (n - i)))
        return u
    Fv = g.sub(pack(dF, W), g.shl(Rd(D), b)); Gv = g.sub(pack(dG, W), g.shl(Rd(D - 1), b))
    lf, dF1 = ("c", 1), dF[1]
    lg, dG1 = ("c", 24), dG[1]
    dm = None; sF = sG = ("c", 0); bad = ("c", 0)
    d = D
    bprev = b
    for t in range(steps):
        if sched[t] != b:
            b2 = sched[t]; W2 = 3 * b2 + 3; T2, B2 = 1 << b2, 1 << W2
            R2 = lanes_R(g, W2, 25)
            def repack(v, dd):
                u = g.add(v, g.shl(Rd(dd), b))
                ds = []
                for i in range(dd + 1):
                    p = dd - i
                    x = g.shr(u, W * p) if i == 0 else (g.land(u, B - 1) if p == 0 else g.land(g.shr(u, W * p), B - 1))
                    ds.append(g.add(x, T2 - T))
                return ds
            dsF, dsG = repack(Fv, d), repack(Gv, d - 1)
            b, W, T, B, R = b2, W2, T2, B2, R2
            Fv = g.sub(pack(dsF, W), g.shl(Rd(d), b)); dF1 = dsF[1]
            Gv = g.sub(pack(dsG, W), g.shl(Rd(d - 1), b)); dG1 = dsG[1]
        first = t == 0
        lflg = ("c", 24) if first else g.mul(lf, lg)
        A = ("c", 576) if first else g.mul(lg, lg)
        P1 = g.add(g.mul(lg, dF1), g.shl(lf, b))
        N1 = g.add(g.mul(lf, dG1), g.shl(lg, b))
        bad = g.add(bad, g.sub(1, g.add(g.sub(P1, N1), g.sub(N1, P1))))          # c1 = 0
        M = g.sub(g.add(g.shl(lflg, W), P1), N1)
        X1 = g.mul(A, Fv); X2 = g.mul(M, Gv)
        D2 = g.sub(X2, X1)
        mag = g.add(g.sub(X1, X2), D2)
        sH = g.xor(sF, g.sub(1, g.sub(1, D2)))
        if first: q = mag
        else:
            q = g.div(mag, dm)
            if t < lowbits_from:
                bad = g.add(bad, g.mod(mag, dm))
            else:    # mag − dm·q ∈ [0, dm) and dm < 2^k: zero iff it vanishes mod 2^k
                m = (1 << (2 * bprev)) - 1
                t1 = g.land(mag, m); t2 = g.land(g.mul(dm, g.land(q, m)), m)
                bad = g.add(bad, g.add(g.sub(t1, t2), g.sub(t2, t1)))
        dh = d - 2
        Rh = Rd(dh)
        u = g.add(q, g.shl(Rh, b))
        HM = g.sub(g.shl(Rh, W), g.shl(Rh, b + 1))
        bad = g.add(bad, g.add(g.land(u, HM), g.shr(u, W * (dh + 1))))
        lh = g.sub(g.shr(u, W * dh), T)
        bad = g.add(bad, g.sub(1, lh))                                          # leading digit 0
        dH1 = g.land(g.shr(u, W * (dh - 1)), B - 1) if dh >= 1 else None
        Fv, lf, dF1, sF = Gv, lg, dG1, sG
        Gv, lg, dG1, sG = q, lh, dH1, sH
        dm = A; d -= 1; bprev = b
    return dict(Fv=Fv, Gv=Gv, sF=sF, sG=sG, bad=bad, d=d, b=b, W=W, T=T, B=B, Rd=Rd)

def unpack_true(g, st, which):
    """the true polynomial (z-encoded, high-to-low) from the packed state"""
    v, s, d = (st["Fv"], st["sF"], st["d"]) if which == "F" else (st["Gv"], st["sG"], st["d"] - 1)
    b, W, T, B = st["b"], st["W"], st["T"], st["B"]
    u = g.add(v, g.shl(st["Rd"](d), b))
    out = []
    for i in range(d + 1):
        p = d - i
        x = g.shr(u, W * p) if i == 0 else (g.land(u, B - 1) if p == 0 else g.land(g.shr(u, W * p), B - 1))
        a = g.sub(x, T); c = g.sub(T, x)
        out.append(g.add(g.shl(g.add(a, c), 1), g.xor(g.sub(1, g.sub(1, c)), s)))
    return out

def build(fz, sched, steps, lowbits_from=99):
    g = Dag(fz)
    st = packed(g, sched, steps, lowbits_from)
    if steps == 23:
        res = g.add(g.shl(st["Gv"], 1), st["sG"]); bad = st["bad"]
    else:
        F = unpack_true(g, st, "F"); G = unpack_true(g, st, "G")
        run = v7_ops(g)
        res, bad = run(23 - steps, F, G, st["bad"])
    return g, res, bad

def zenc(a): return 2 * abs(a) + (1 if a < 0 else 0)
def zdec(z): return -(z // 2) if z % 2 else z // 2

SIZES = json.load(open("/home/claude/polypack/sizes.json"))
def need(band, t, margin=(0.02, 16)):
    mx = SIZES[band]["max"]; m = max(mx[t], mx[t + 1], mx[t + 2])
    return m + 1 + int(margin[0] * m) + margin[1]
def schedule(band, cuts, steps):
    """cuts: segment start steps (first is 0); b of a segment covers all its steps"""
    sched = [None] * steps
    bounds = cuts + [steps]
    for a, e in zip(bounds, bounds[1:]):
        b = max(need(band, t) for t in range(a, e))
        for t in range(a, e): sched[t] = b
    return sched

if __name__ == "__main__":
    import reference_answers as ref
    sys.path.insert(0, "/home/claude/polypack"); import cost
    for band, n, cuts, steps in [("D1", 300000, [0, 14], 23), ("D3", 1099511628553, [0, 8, 11], 13),
                                 ("D3", 1099511628553, [0, 9, 14], 23)]:
        P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P] + [0]
        sched = schedule(band, cuts, steps)
        g, res, bad = build(fz, sched, steps)
        ok = zdec(g.val(res)) == ref.compute_answer("polydisc", n) and g.val(bad) == 0
        print(f"{band} n={n} cuts={cuts} steps={steps} b={sorted(set(sched))}: ok={ok} nodes={len(g.lines)} "
              f"est={cost.price(g.cost) + 5000 * len(g.lines):,}")
