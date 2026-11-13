"""Packed normal PRS for polydisc as a Nat expression graph (natdag-style), with real values.

Every polynomial S (high-to-low, degree d) is one natural number: its sign-normalized value
Ŝ(B) = σ·S(B) at B = 2^W (σ makes the leading coefficient positive), and its offset form
u = Ŝ(B) + O_d with O_d = T·(1 + B + … + B^d), whose base-B digits are v_i + T.
A step is  R(B) = (lg²·F̂(B) − (lf·lg·B + c1)·Ĝ(B)) / dm,  Ĥ(B) = |R(B)|,  σ_H = σ_F·sign R.
Checks (all into one failure count): c1 ≠ 0; exact division; every digit of u_H in [0, 2T)
(one AND with a mask) and no digit above d−2 (one shift); leading digit > 0.
With W ≥ 3b+3 (T = 2^b) the checked digit bounds make E(B) = 0 imply E ≡ 0 for
E = ±N − dm·Ĥ, i.e. the packed step IS the coefficientwise normal step."""
import sys
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge")
sys.path.insert(0, "/home/claude/polyvar")

class Dag:
    def __init__(s, inputs):
        s.vals = []; s.lines = []; s.inputs = list(inputs); s.cost = []
    def val(s, r):
        k, i = r
        return s.vals[i] if k == "v" else s.inputs[i] if k == "x" else i
    def tok(s, r):
        k, i = r
        return f"v{i}" if k == "v" else f"x{i}" if k == "x" else str(i)
    def op(s, name, a, b):
        if isinstance(a, int): a = ("c", a)
        if isinstance(b, int): b = ("c", b)
        x, y = s.val(a), s.val(b)
        f = {"add": lambda: x + y, "sub": lambda: max(x - y, 0), "mul": lambda: x * y,
             "div": lambda: x // y if y else 0, "mod": lambda: x % y if y else x,
             "land": lambda: x & y, "xor": lambda: x ^ y, "shl": lambda: x << y, "shr": lambda: x >> y}[name]
        v = f()
        s.vals.append(v); s.lines.append(f"{name} {s.tok(a)} {s.tok(b)}")
        bx, by = max(x.bit_length(), 1), max(y.bit_length(), 1)
        g = {"add": "add", "sub": "sub", "mul": "mul", "land": "and", "xor": "and"}.get(name)
        if name in ("div", "mod"): s.cost.append((name, max(v.bit_length() if name == "div" else bx - by, 1), by))
        elif name in ("shl", "shr"): s.cost.append((name, bx, y))
        else: s.cost.append((g, bx, by))
        return ("v", len(s.vals) - 1)
    def __getattr__(s, name):
        if name in ("add", "sub", "mul", "div", "mod", "land", "xor", "shl", "shr"):
            return lambda a, b: s.op(name, a, b)
        raise AttributeError(name)

def rep(T, B, d):  # O_d = T·(1 + B + … + B^d)
    return T * sum(B ** i for i in range(d + 1))

def himask(W, b, d):  # every bit at or above b+1 inside lanes 0..d
    lane = (1 << W) - (1 << (b + 1))
    return sum(lane << (W * i) for i in range(d + 1))

def build(fz, sched, exact_mod=True, marks=None):
    """fz: the 25 z-encoded coefficients (2·|a| + sign), f0 = 2. sched[t] = b for step t (W = 3b+3);
    a change of b repacks F and G digit by digit. Returns (dag, result node, bad node)."""
    g = Dag(fz)
    D = 24
    b = sched[0]; W = 3 * b + 3; T, B = 1 << b, 1 << W
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
    uF, uG = pack(dF, W), pack(dG, W)
    Fv = g.sub(uF, rep(T, B, D)); Gv = g.sub(uG, rep(T, B, D - 1))
    lf, dF1 = ("c", 1), dF[1]
    lg, dG1 = ("c", 24), dG[1]
    dm = None; sF = sG = ("c", 0); bad = ("c", 0)
    d = D  # degree of F
    for t in range(23):
        if marks is not None: marks.append(len(g.cost))
        if sched[t] != b:   # repack F (degree d) and G (degree d-1) into the new lanes
            b2 = sched[t]; W2 = 3 * b2 + 3; T2, B2 = 1 << b2, 1 << W2
            def repack(v, dd):
                u = g.add(v, rep(T, B, dd))
                ds = []
                for i in range(dd + 1):
                    p = dd - i
                    x = g.shr(u, W * p) if i == 0 else (g.land(u, B - 1) if p == 0 else g.land(g.shr(u, W * p), B - 1))
                    ds.append(g.add(x, T2 - T) if T2 > T else g.sub(x, T - T2))
                return g.sub(pack(ds, W2), rep(T2, B2, dd)), ds[1]
            Fv, dF1 = repack(Fv, d); Gv, dG1 = repack(Gv, d - 1)
            b, W, T, B = b2, W2, T2, B2
        first = t == 0
        lflg = ("c", 24) if first else g.mul(lf, lg)
        A = ("c", 576) if first else g.mul(lg, lg)
        P1 = g.add(g.mul(lg, dF1), g.shl(lf, b))
        N1 = g.add(g.mul(lf, dG1), g.shl(lg, b))
        z = g.add(g.sub(P1, N1), g.sub(N1, P1))
        bad = g.add(bad, g.sub(1, z))                      # c1 = 0
        M = g.sub(g.add(g.shl(lflg, W), P1), N1)
        X1 = g.mul(A, Fv); X2 = g.mul(M, Gv)
        D2 = g.sub(X2, X1)
        mag = g.add(g.sub(X1, X2), D2)
        sH = g.xor(sF, g.sub(1, g.sub(1, D2)))
        if first: q = mag
        else:
            q = g.div(mag, dm)
            if exact_mod: bad = g.add(bad, g.mod(mag, dm))
            else:
                m = (1 << (g.val(dm).bit_length() + 1)) - 1
                t1 = g.land(mag, m); t2 = g.land(g.mul(dm, g.land(q, m)), m)
                bad = g.add(bad, g.add(g.sub(t1, t2), g.sub(t2, t1)))
        dh = d - 2
        u = g.add(q, rep(T, B, dh))
        bad = g.add(bad, g.add(g.land(u, himask(W, b, dh)), g.shr(u, W * (dh + 1))))
        d0 = g.shr(u, W * dh)
        lh = g.sub(d0, T)
        bad = g.add(bad, g.sub(1, lh))                     # leading digit 0
        dH1 = g.land(g.shr(u, W * (dh - 1)), B - 1) if dh >= 1 else None
        Fv, lf, dF1, sF = Gv, lg, dG1, sG
        Gv, lg, dG1, sG = q, lh, dH1, sH
        dm = A; d -= 1
    if marks is not None: marks.append(len(g.cost))
    res = g.add(g.shl(Gv, 1), sG)                         # encoded (−1)^σ·|R|
    return g, res, bad

def zenc(a): return 2 * abs(a) + (1 if a < 0 else 0)
def zdec(z): return -(z // 2) if z % 2 else z // 2

def params(P):
    import prs_model as pm
    L = pm.Log(); r, seq = pm.run(P, L)
    b = max(abs(c).bit_length() for p in seq for c in p) + 1
    return b, 3 * b + 3, r

