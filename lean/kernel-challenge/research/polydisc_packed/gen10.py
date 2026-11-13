"""polydisc v8 generator with every lane constant as a graph input ("c" variables).

Produces, per band: the natdag program `pkDagC` (inputs f0..f24, Prod.mk, c0..cM), the structured
right-hand side over the same variables (acts list, pinit call, optional v7 tail), the constant
definitions and the closed argument list used by `pkDag`. Mirrors lean/PackDefs.lean."""
import sys, json
sys.set_int_max_str_digits(0)
sys.path.insert(0, "/home/claude/lkc/evaluation/judge"); sys.path.insert(0, "/home/claude/polyvar")
sys.path.insert(0, "/home/claude/polyv8")
from gen8 import Dag, v7_ops, zenc, zdec, SIZES

def rep(W, L): return sum(1 << (W * i) for i in range(L))
def hmask(W, b, L): return sum(((1 << W) - (1 << (b + 1))) << (W * i) for i in range(L))

class G(Dag):
    """graph whose constants are named inputs"""
    def __init__(s, fz):
        super().__init__(list(fz) + [0])      # x0..x24 coefficients, x25 = Prod.mk
        s.cvars = []                          # (lean argument term, value)
        s.cidx = {}
    INLINE = False
    def var(s, key, value, arg):
        if s.INLINE:          # constants computed inside the graph (2^k, 2^k − 1, m·2^k; else literal)
            if key not in s.cidx:
                s.cidx[key] = s.mkconst(value); s.cvars.append((arg, value))
            return s.cidx[key]
        if key not in s.cidx:
            s.inputs.append(value); s.cidx[key] = ("x", len(s.inputs) - 1); s.cvars.append((arg, value))
        return s.cidx[key]
    def mkconst(s, c):
        if c < (1 << 64): return ("c", c)
        if c & (c - 1) == 0: return s.op("shl", ("c", 1), ("c", c.bit_length() - 1))
        if c & (c + 1) == 0: return s.op("sub", s.mkconst(c + 1), ("c", 1))
        k = (c & -c).bit_length() - 1
        if k > 0 and (c >> k) < (1 << 64): return s.op("shl", ("c", c >> k), ("c", k))
        # T·rep W 25 / hmask: build from rep by doubling when recognisable
        return ("c", c)
    def cname(s, r):   # lean name of a variable or node-free constant
        k, i = r
        if k == "x": return f"f{i}" if i < 25 else f"c{i - 26}"
        if k == "c": return str(i)
        raise ValueError("node in a constant position")

class Seg:
    def __init__(s, g, tag, W, b):
        s.g, s.W, s.b, s.tag = g, W, b, tag
        s.T = 1 << b
        if g.INLINE:
            R1 = ("c", 1); R2 = g.add(R1, g.shl(R1, W)); R4 = g.add(R2, g.shl(R2, 2 * W))
            R8 = g.add(R4, g.shl(R4, 4 * W)); R16 = g.add(R8, g.shl(R8, 8 * W))
            R25 = g.add(g.add(R16, g.shl(R8, 16 * W)), g.shl(1, 24 * W))
            s.KO = g.shl(R25, b); s.KH = g.sub(g.shl(R25, W), g.shl(R25, b + 1))
        else:
            s.KO = g.var(("KO", W, b), s.T * rep(W, 25), f"kO{tag}")
            s.KH = g.var(("KH", W, b), hmask(W, b, 25), f"kH{tag}")
        s.Tv = g.var(("T", b), s.T, f"kT{tag}")
        s.M = g.var(("M", W), (1 << W) - 1, f"kM{tag}")
        s.Q = g.var(("Q", b), (1 << (2 * b)) - 1, f"kQ{tag}")
    def sh(s, amount):    # a shift amount: a variable (numeral argument) when large
        if amount < 64: return ("c", amount)
        return s.g.var(("sh", amount), amount, str(amount))
    def O(s, L):  return s.g.shr(s.KO, s.sh(s.W * (25 - L)))
    def HM(s, L): return s.g.shr(s.KH, s.sh(s.W * (25 - L)))

def digsU(g, m, u, shs): return [g.land(g.shr(u, sh), m) for sh in shs]
def packL(g, ds, shs):
    if len(ds) == 1: return ds[0]
    return g.add(packL(g, ds[1:], shs[1:]), g.shl(ds[0], shs[0]))
def inDig(g, T, x): return g.sub(g.add(g.shr(x, 1), T), g.mul(g.shl(g.shr(x, 1), 1), g.land(x, 1)))
def derDigs(g, ds, ks, kTs):
    if len(ds) == 1: return [ds[0]]
    return [g.sub(g.mul(ds[0], ks[0]), kTs[0])] + derDigs(g, ds[1:], ks[1:], kTs[1:])

def pinit(g, S, xs, L):
    """L collects the Lean argument terms of the pinit call"""
    T = S.Tv
    l0 = g.var(("l0",), S.T + 1, str(S.T + 1)); g0 = g.var(("g0",), S.T + 24, str(S.T + 24))
    shF = [S.sh(S.W * k) for k in range(24, 0, -1)]; shG = [S.sh(S.W * k) for k in range(23, 0, -1)]
    ks = [("c", k + 1) for k in range(22, 0, -1)]
    kTs = [g.var(("kT", k), k * S.T, str(k * S.T)) for k in range(22, 0, -1)]
    O25, O24 = S.O(25), S.O(24)
    ds = [inDig(g, T, x) for x in xs]
    gs = derDigs(g, ds[:23], ks, kTs)
    fv = g.sub(packL(g, [l0] + ds, shF), O25); gv = g.sub(packL(g, [g0] + gs, shG), O24)
    L.update(T=T, l0=l0, g0=g0, shF=shF, shG=shG, ks=ks, kTs=kTs, O25=("shr", S.KO, S.sh(0)), O24=("shr", S.KO, S.sh(S.W)))
    return dict(fv=fv, lf=("c", 1), df1=ds[0], fs=("c", 0), gv=gv, lg=("c", 24), dg1=gs[0], gs=("c", 0),
                dm=("c", 1), bad=("c", 0))

def pstep(g, S, dh, first, lowb, s, A_):
    T, m, m2 = S.Tv, S.M, S.Q
    O, HM = S.O(dh + 1), S.HM(dh + 1)
    sb, sW, s1, s0, sm = S.sh(S.b), S.sh(S.W), S.sh(S.W * (dh + 1)), S.sh(S.W * dh), S.sh(S.W * max(dh - 1, 0))
    A_.append(("step", S, dh, first, lowb, (T, m, ("shr", S.KO, S.sh(S.W * (24 - dh))), ("shr", S.KH, S.sh(S.W * (24 - dh))), m2, sb, sW, s1, s0, sm)))
    P1 = g.add(g.mul(s["lg"], s["df1"]), g.shl(s["lf"], sb))
    N1 = g.add(g.mul(s["lf"], s["dg1"]), g.shl(s["lg"], sb))
    bad1 = g.add(s["bad"], g.sub(1, g.add(g.sub(P1, N1), g.sub(N1, P1))))
    A = g.mul(s["lg"], s["lg"])
    X1 = g.mul(A, s["fv"])
    X2 = g.mul(g.sub(g.add(g.shl(g.mul(s["lf"], s["lg"]), sW), P1), N1), s["gv"])
    D2 = g.sub(X2, X1)
    mag = g.add(g.sub(X1, X2), D2)
    q = mag if first else g.div(mag, s["dm"])
    if first: bad2 = bad1
    elif lowb:
        t2 = g.land(g.mul(s["dm"], g.land(q, m2)), m2); t1 = g.land(mag, m2)
        bad2 = g.add(bad1, g.add(g.sub(t1, t2), g.sub(t2, t1)))
    else:
        bad2 = g.add(bad1, g.mod(mag, s["dm"]))
    u = g.add(q, O)
    bad3 = g.add(bad2, g.add(g.land(u, HM), g.shr(u, s1)))
    lh = g.sub(g.shr(u, s0), T)
    return dict(fv=s["gv"], lf=s["lg"], df1=s["dg1"], fs=s["gs"], gv=q, lg=lh,
                dg1=g.land(g.shr(u, sm), m), gs=g.xor(s["fs"], g.sub(1, g.sub(1, D2))),
                dm=A, bad=g.add(bad3, g.sub(1, lh)))

def prepack(g, S, S2, d, s, A_):
    dT = g.var(("dT", S.b, S2.b), S2.T - S.T, f"(kT{S2.tag} - kT{S.tag})")
    OF, OG = S.O(d + 1), S.O(d)
    shF = [S.sh(S.W * p) for p in range(d, -1, -1)]; shG = [S.sh(S.W * p) for p in range(d - 1, -1, -1)]
    pF = [S2.sh(S2.W * k) for k in range(d, 0, -1)]; pG = [S2.sh(S2.W * k) for k in range(d - 1, 0, -1)]
    OF2, OG2 = S2.O(d + 1), S2.O(d)
    A_.append(("repack", S, S2, d, (S.M, ("shr", S.KO, S.sh(S.W * (24 - d))), ("shr", S.KO, S.sh(S.W * (25 - d))),
                                     shF, shG, pF, pG, ("shr", S2.KO, S2.sh(S2.W * (24 - d))), ("shr", S2.KO, S2.sh(S2.W * (25 - d))), dT)))
    dsF = [g.add(x, dT) for x in digsU(g, S.M, g.add(s["fv"], OF), shF)]
    dsG = [g.add(x, dT) for x in digsU(g, S.M, g.add(s["gv"], OG), shG)]
    t = dict(s)
    t.update(fv=g.sub(packL(g, dsF, pF), OF2), df1=dsF[1], gv=g.sub(packL(g, dsG, pG), OG2), dg1=dsG[1])
    return t

def unpackT(g, S, d, v, sgn):
    shs = [S.sh(S.W * p) for p in range(d, -1, -1)]
    u = g.add(v, S.O(d + 1)); T = S.Tv
    out = [g.add(g.shl(g.add(g.sub(x, T), g.sub(T, x)), 1), g.xor(g.sub(1, g.sub(1, g.sub(T, x))), sgn))
           for x in digsU(g, S.M, u, shs)]
    return out, (T, S.M, ("shr", S.KO, S.sh(S.W * (24 - d))), shs)

def need(band, t, margin=(0.02, 16)):
    mx = SIZES[band]["max"]; m = max(mx[t], mx[t + 1], mx[t + 2])
    return m + 1 + int(margin[0] * m) + margin[1]

def plan(band, cuts, steps, lowb_from):
    bounds = cuts + [steps]; segs = []
    for a, e in zip(bounds, bounds[1:]):
        b = max(need(band, t) for t in range(a, e)); segs.append((a, e, 3 * b + 3, b))
    return segs

def build(fz, name, segs, steps, lowb_from):
    g = G(fz)
    S = [Seg(g, f"{name}_{j}", W, b) for j, (_, _, W, b) in enumerate(segs)]
    L = {}; A_ = []
    s = pinit(g, S[0], [("x", i) for i in range(1, 25)], L)
    for j, (a, e, W, b) in enumerate(segs):
        if j > 0: s = prepack(g, S[j - 1], S[j], 24 - a, s, A_)
        for t in range(a, e): s = pstep(g, S[j], 22 - t, t == 0, t >= lowb_from, s, A_)
    tail = None
    if steps == 23:
        res, bad = g.add(g.shl(s["gv"], 1), s["gs"]), s["bad"]
    else:
        d = 24 - steps
        F, uf = unpackT(g, S[-1], d, s["fv"], s["fs"]); Gl, ug = unpackT(g, S[-1], d - 1, s["gv"], s["gs"])
        res, bad = v7_ops(g)(23 - steps, F, Gl, s["bad"])
        tail = (23 - steps, uf, ug)
    return g, res, bad, L, A_, tail, S

# ---------------- Lean text ----------------
def lt(g, r):
    """Lean term of a constant-position operand: variable, numeral or (shr x y)"""
    if isinstance(r, tuple) and r[0] == "shr": return f"(Nat.shiftRight {lt(g, r[1])} {lt(g, r[2])})"
    return g.cname(r)
def ll(g, rs): return "[" + ", ".join(lt(g, r) for r in rs) + "]"
def bl(x): return "true" if x else "false"

def lean_rhs(g, L, A_, tail):
    acts = []
    for a in A_:
        if a[0] == "step":
            _, S, dh, first, lowb, (T, m, O, HM, m2, sb, sW, s1, s0, sm) = a
            acts.append(f".step {S.W} {S.b} {dh} {lt(g, T)} {lt(g, m)} {lt(g, O)} {lt(g, HM)} {lt(g, m2)} "
                        f"{lt(g, sb)} {lt(g, sW)} {lt(g, s1)} {lt(g, s0)} {lt(g, sm)} {bl(first)} {bl(lowb)}")
        else:
            _, S, S2, d, (m, OF, OG, shF, shG, pF, pG, OF2, OG2, dT) = a
            acts.append(f".repack {S.W} {S.b} {S2.W} {S2.b} {d} {lt(g, m)} {lt(g, OF)} {lt(g, OG)} {ll(g, shF)} {ll(g, shG)} "
                        f"{ll(g, pF)} {ll(g, pG)} {lt(g, OF2)} {lt(g, OG2)} {lt(g, dT)}")
    init = (f"pinit {lt(g, L['T'])} {lt(g, L['l0'])} {lt(g, L['g0'])} {ll(g, L['shF'])} {ll(g, L['shG'])} "
            f"{ll(g, L['ks'])} {ll(g, L['kTs'])} {lt(g, L['O25'])} {lt(g, L['O24'])} "
            f"[{', '.join(f'f{i}' for i in range(1, 25))}]")
    actl = "[" + ",\n    ".join(acts) + "]"
    if tail is None:
        body = f"let s := prun {actl}\n    ({init})\n  (Nat.add (Nat.shiftLeft s.gv 1) s.gs, s.bad)"
    else:
        k, (T, m, OF, shF), (_, _, OG, shG) = tail
        body = (f"let s := prun {actl}\n    ({init})\n  run {k} (unpackT {lt(g, T)} {lt(g, m)} {lt(g, OF)} {ll(g, shF)} s.fv s.fs)\n"
                f"    (unpackT {lt(g, T)} {lt(g, m)} {lt(g, OG)} {ll(g, shG)} s.gv s.gs) s.bad")
    return body

def lean_band(name, band, cuts, steps, lowb_from, n):
    """Lean source for one band: constants, pkDagC, pkRhs, the kernel rfl link, pkDag."""
    import reference_answers as ref
    P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
    segs = plan(band, cuts, steps, lowb_from)
    g, res, bad, L, A_, tail, S = build(fz, name, segs, steps, lowb_from)
    assert zdec(g.val(res)) == ref.compute_answer("polydisc", n) and g.val(bad) == 0
    F25 = " ".join(f"f{i}" for i in range(25)); FL = ", ".join(f"f{i}" for i in range(25))
    nc = len(g.cvars); CB = " ".join(f"c{i}" for i in range(nc)); CL = ", ".join(f"c{i}" for i in range(nc))
    out = []
    for Sj in S:
        W, b, t = Sj.W, Sj.b, Sj.tag
        out.append(f"""/-- `rep {W} 25` by doubling. -/
def kR{t} : Nat := natdag% "shl 1 {W}\nadd 1 v0\nshl v1 {2 * W}\nadd v1 v2\nshl v3 {4 * W}\nadd v3 v4\nshl v5 {8 * W}\nadd v5 v6\nshl v5 {16 * W}\nadd v7 v8\nshl 1 {24 * W}\nadd v9 v10" []
def kO{t} : Nat := Nat.shiftLeft kR{t} {b}
def kH{t} : Nat := Nat.sub (Nat.shiftLeft kR{t} {W}) (Nat.shiftLeft kR{t} {b + 1})
def kT{t} : Nat := Nat.shiftLeft 1 {b}
def kM{t} : Nat := Nat.sub (Nat.shiftLeft 1 {W}) 1
def kQ{t} : Nat := Nat.sub (Nat.shiftLeft 1 {2 * b}) 1
""")
    args = " ".join(a if a.startswith("(") or a.isdigit() or not a.startswith("(kT") else a for a, _ in g.cvars)
    args = " ".join((f"(Nat.sub {a[1:-1].split(' - ')[0]} {a[1:-1].split(' - ')[1]})" if a.startswith("(kT") else a) for a, _ in g.cvars)
    dag = "\n".join(g.lines) + f"\napp x25 {g.tok(res)} {g.tok(bad)}"
    G.INLINE = True
    gi, resi, badi, _, _, _, _ = build(fz, name, segs, steps, lowb_from)
    G.INLINE = False
    assert zdec(gi.val(resi)) == zdec(g.val(res)) and gi.val(badi) == 0
    idag = "\n".join(gi.lines) + f"\napp x25 {gi.tok(resi)} {gi.tok(badi)}"
    out.append(f"""/-- The packed run of band `{name}` with its lane constants as variables. -/
def pkDagC{name} ({F25} {CB} : Nat) : Nat × Nat :=
  natdag% "{dag}" [{FL}, (@Prod.mk Nat Nat), {CL}]

set_option linter.unusedVariables false in
/-- The structured run over the same variables. -/
def pkRhs{name} ({F25} {CB} : Nat) : Nat × Nat :=
  {lean_rhs(g, L, A_, tail)}

/-- Statement of `pkDagC{name}_eq`. -/
def PkDagC{name}Eq : Prop := ∀ {F25} {CB} : Nat, pkDagC{name} {F25} {CB} = pkRhs{name} {F25} {CB}

open Lean Elab Term Command Meta in
/- `pkDagC{name}_eq : PkDagC{name}Eq` by `rfl`, checked by the kernel on open terms. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDagC{name}Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun ({F25} {CB} : Nat) =>
    @rfl (Nat × Nat) (pkDagC{name} {F25} {CB}))) none)
  addDecl (.thmDecl {{ name := `Submission.pkDagC{name}_eq, levelParams := [], type := ty, value := pf }})

/-- The packed run of band `{name}`, lane constants computed inside the graph. -/
def pkDag{name} ({F25} : Nat) : Nat × Nat :=
  natdag% "{idag}" [{FL}, (@Prod.mk Nat Nat)]

/-- Statement of `pkDag{name}_eq`. -/
def PkDag{name}Eq : Prop := ∀ {F25} : Nat, pkDag{name} {F25} = pkDagC{name} {F25} {args}

open Lean Elab Term Command Meta in
/- `pkDag{name}_eq : PkDag{name}Eq` by `rfl`: the two graphs differ only in closed constants. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag{name}Eq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun ({F25} : Nat) =>
    @rfl (Nat × Nat) (pkDag{name} {F25}))) none)
  addDecl (.thmDecl {{ name := `Submission.pkDag{name}_eq, levelParams := [], type := ty, value := pf }})
""")
    # structured run at the lane constants, named
    import re as _re
    argmap = {f"c{i}": a for i, (a, _) in enumerate(g.cvars)}
    def subK(txt):
        return _re.sub(r"\bc(\d+)\b", lambda m: (argmap[m.group(0)] if not argmap[m.group(0)].startswith("(kT")
            else "(Nat.sub " + " ".join(argmap[m.group(0)][1:-1].split(" - ")) + ")") if argmap[m.group(0)][0] != "(" or argmap[m.group(0)].startswith("(kT") else argmap[m.group(0)], txt)
    rhs = lean_rhs(g, L, A_, tail)
    i0 = rhs.index("prun ") + len("prun "); i1 = rhs.index("\n    (pinit ")
    acts_txt = subK(rhs[i0:i1])
    j0 = rhs.index("(pinit ") + 1; j1 = rhs.index(" [f1, f2")
    init_txt = subK(rhs[j0:j1])
    XB = " ".join(f"f{i}" for i in range(1, 25)); XL = ", ".join(f"f{i}" for i in range(1, 25))
    if tail is None:
        run_body = "let s := prun acts{0} (init{0} xs)\n  (Nat.add (Nat.shiftLeft s.gv 1) s.gs, s.bad)".format(name)
    else:
        k2 = rhs.index("  run ")
        run_body = ("let s := prun acts{0} (init{0} xs)\n".format(name) + subK(rhs[k2:]).replace("  run ", "  run ", 1))
    Ktxt = args
    out.append(f"""/-- The lane-constant act list of band `{name}`. -/
def acts{name} : List PAct := {acts_txt}

/-- The packed input of band `{name}`. -/
def init{name} (xs : List Nat) : PSt := {init_txt} xs

/-- The structured run of band `{name}`. -/
def pkRun{name} (xs : List Nat) : Nat × Nat :=
  {run_body}

/-- Statement of `pkDag{name}_struct`. -/
def PkDag{name}Struct : Prop := ∀ {F25} : Nat, pkDag{name} {F25} = pkRun{name} [{XL}]

open Lean Elab Term Command Meta in
/- `pkDag{name}_struct`: through the variable graph (`pkDag{name}_eq`, `pkDagC{name}_eq`), then `rfl`
between two structured terms. Checked by the kernel. -/
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(PkDag{name}Struct)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun ({F25} : Nat) =>
    Eq.trans (pkDag{name}_eq {F25}) (Eq.trans (pkDagC{name}_eq {F25} {Ktxt}) (@rfl (Nat × Nat) (pkRun{name} [{XL}]))))) none)
  addDecl (.thmDecl {{ name := `Submission.pkDag{name}_struct, levelParams := [], type := ty, value := pf }})
""")
    return "\n".join(out), len(g.lines), nc

if __name__ == "__main__":
    import reference_answers as ref
    sys.path.insert(0, "/home/claude/polypack"); import cost
    for name, band, cuts, steps, lb, n in [("15", "D1", [0, 15], 23, 99, 300000), ("205", "D3", [0, 7, 11], 14, 0, 1099511628553)]:
        P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
        segs = plan(band, cuts, steps, lb)
        g, res, bad, L, A_, tail, S = build(fz, name, segs, steps, lb)
        ok = zdec(g.val(res)) == ref.compute_answer("polydisc", n) and g.val(bad) == 0
        print(name, ok, "nodes", len(g.lines), "consts", len(g.cvars), f"{cost.price(g.cost) + 5000 * len(g.lines):,}")
        print(lean_rhs(g, L, A_, tail)[:600])
