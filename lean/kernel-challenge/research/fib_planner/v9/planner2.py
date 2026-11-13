"""Planner extension: branched end-games ('E').

After the join (L-pair at n >> r), the selected doublings for bits r-1 .. 2 are Bool.rec branches
(each branch: two squares and two or three linear steps), and bits 1, 0 are a 4-way closed formula
from the pair (p, q) = (L(j), L(j+1)), j = n >> 2, a = p^2, b = q^2, eps = (-1)^j:
  A = L(2j) = a - 2eps,  B = L(2j+1) = b - a + 4eps,  C = L(2j+2) = b + 2eps
  F(2j) = (2B - A)/5,    F(2j+1) = (a + b)/5
  F(4j) = F(2j) A,  F(4j+1) = F(2j) B + 1,  F(4j+2) = F(2j+1) B,  F(4j+3) = F(2j+1) C - 1.
"""
import sys
sys.path.insert(0, "/home/claude/fibvar")
import planner as pl
from planner import Plan, K_of, fib_pair, lit

def _ABC(a, b, c):
    eps = 1 - 2 * c
    return a - 2 * eps, b - a + 4 * eps, b + 2 * eps

def fin4_py(n, a, b, c):
    A, B, C = _ABC(a, b, c)
    r = n % 4
    if r < 2:
        F2j = (2 * B - A) // 5
        return F2j * A if r == 0 else F2j * B + 1
    F2j1 = (a + b) // 5
    return F2j1 * B if r == 2 else F2j1 * C - 1

def simulateE(p, n):
    """same as planner.simulate up to the join, then the branched end-game."""
    L, t, P, c, r = p.L, p.t, p.P, p.c, p.r
    assert r >= 2
    m = n >> (L - t)
    K = K_of(t); X = 2 ** K; M = X * X - X - 1
    R = pow(X, m + 1) % M; a, b = R % X, R // X
    if c >= 1:
        x = a * (2 * b - a); y = b * (2 * a + b) - x; f, l = x, 2 * y - x
        for _ in range(c - 1): f, l = f * l, l * l - 2
        p_, q_ = l, (5 * f + l) // 2
        for _ in range(P - c): p_, q_ = p_ * p_ - 2, (q_ * q_ + 2) - (p_ * p_ - 2)
    else:
        x = a * (2 * b - a); y = b * (2 * a + b) - x
        p_, q_ = 2 * y - x, 2 * x + y
        for _ in range(P - 1): p_, q_ = p_ * p_ - 2, (q_ * q_ + 2) - (p_ * p_ - 2)
    d = (n >> r) % (2 ** P)
    Kd = K_of(P); Xd = 2 ** Kd; Md = Xd * Xd - Xd - 1
    Q = pow(Xd, d + 1) % Md; u, v = Q % Xd, Q // Xd
    Pp, Qq = (v - u) * p_ + u * q_, u * p_ + v * q_                        # L(n>>r), L(n>>r + 1)
    assert Pp == 2 * fib_pair(n >> r)[1] - fib_pair(n >> r)[0]
    for k in range(r - 1, 1, -1):
        cpar = (n >> (k + 1)) % 2; bit = (n >> k) % 2
        A, B, C = _ABC(Pp * Pp, Qq * Qq, cpar)
        Pp, Qq = (A, B) if bit == 0 else (B, C)
    return fin4_py(n, Pp * Pp, Qq * Qq, (n >> 2) % 2)

# ------------------------------------------------------------------ Lean
MOT = "(motive := fun _ => Nat → Nat → Nat → Nat)"

def _abc_lean(cm, cexpr=None):
    """Lean expressions for A, B, C (over bound a, b) for parity mode cm in {'a', 0, 1}."""
    if cm == 0:
        return "(Nat.sub a (nat_lit 2))", "(Nat.sub (Nat.add (nat_lit 4) b) a)", "(Nat.add (nat_lit 2) b)"
    if cm == 1:
        return "(Nat.add (nat_lit 2) a)", "(Nat.sub b (Nat.add (nat_lit 4) a))", "(Nat.sub b (nat_lit 2))"
    c = cexpr
    return (f"(Nat.sub (Nat.add a (Nat.mul (nat_lit 4) {c})) (nat_lit 2))",
            f"(Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.mul (nat_lit 8) {c})))",
            f"(Nat.sub (Nat.add (nat_lit 2) b) (Nat.mul (nat_lit 4) {c}))")

LAND = False

def fin4_defs(suffix=""):
    out = []
    for cm in ("a", 0, 1):
        name = {"a": "fin4", 0: "fin4c0", 1: "fin4c1"}[cm] + suffix
        cex = "(Nat.mod (Nat.div n (nat_lit 4)) (nat_lit 2))"
        A, B, C = _abc_lean(cm, "c")
        pre = f"share c := {cex}; " if cm == "a" else ""
        nv = "n" if cm == "a" else "_"
        def br(body): return f"(fun {nv} a b => {pre}share A := {A}; share B := {B}; {body})"
        r0 = br("Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) A")
        r1 = br("Nat.add (nat_lit 1) (Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) B)")
        r2 = br("Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) B")
        r3 = f"(fun {nv} a b => {pre}Nat.sub (Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) {C}) (nat_lit 1))"
        out.append(f"""/-- 4-way end ({name}): `F(n)` from `a = L(j)^2`, `b = L(j+1)^2`, `j = n / 4`. -/
def {name} (n a b : Nat) : Nat :=
  Bool.rec {MOT}
    (fun n a b => Bool.rec {MOT} {r3} {r2} (Nat.beq (Nat.mod n (nat_lit 2)) (nat_lit 0)) n a b)
    (fun n a b => Bool.rec {MOT} {r1} {r0} (Nat.beq (Nat.mod n (nat_lit 2)) (nat_lit 0)) n a b)
    (Nat.beq (Nat.mod (Nat.div n (nat_lit 2)) (nat_lit 2)) (nat_lit 0)) n a b
""")
    return "\n".join(out)

def sel_def(name, k, cm, k0, k1):
    """branched selected doubling for bit k (pair at n >> (k+1) as squares a, b) -> continuation."""
    cex = f"(Nat.mod (Nat.div n {lit(2 ** (k + 1))}) (nat_lit 2))"
    A, B, C = _abc_lean(cm, "c")
    pre = f"share c := {cex}; " if cm == "a" else ""
    return f"""def {name} (n a b : Nat) : Nat :=
  Bool.rec {MOT}
    (fun n a b => {pre}share B := {B}; {k1} n (Nat.pow B (nat_lit 2)) (Nat.pow {C} (nat_lit 2)))
    (fun n a b => {pre}share B := {B}; {k0} n (Nat.pow {A} (nat_lit 2)) (Nat.pow B (nat_lit 2)))
    (Nat.beq (Nat.mod (Nat.div n {lit(2 ** k)}) (nat_lit 2)) (nat_lit 0)) n a b
"""

def emitE(p, fname):
    """Lean for plan p with the 'E' end: reuse planner.emit's 'D' body up to P0/Q0."""
    q = Plan(p.L, p.t, p.P, p.c, "D")
    src = pl.emit(q, fname)
    head, _, _ = src.partition("  share hp")          # drop the D tail
    if "share h1 :=" in head:
        head = head.split("  share h1 :=")[0]
    r = p.r
    helpers = []
    # continuation chain: levels r-1 .. 2, then fin4
    def cont(k, cm):
        """name of the def that consumes the pair at n >> (k+1) with parity mode cm"""
        if k < 2:
            return {"a": "fin4", 0: "fin4c0", 1: "fin4c1"}[cm]
        nm = f"{fname}_s{k}_{cm}"
        helpers.append(sel_def(nm, k, cm, cont(k - 1, 0), cont(k - 1, 1)))
        return nm
    first = cont(r - 1, "a")
    body = head.rstrip() + f"\n  {first} n (Nat.pow P0 (nat_lit 2)) (Nat.pow Q0 (nat_lit 2))\n"
    # dedupe helpers (cont builds each once per (k, cm))
    seen, hs = set(), []
    for h in helpers:
        nm = h.split()[1]
        if nm not in seen: seen.add(nm); hs.append(h)
    return "\n".join(reversed(hs)) + "\n" + body

if __name__ == "__main__":
    import random
    random.seed(7)
    bad = cnt = 0
    for L in range(14, 19):
        for t in (7, 8):
            for P in range(5, 9):
                for c in range(0, P + 1):
                    p = Plan(L, t, P, c, "D")
                    if p.r < 2 or not p.ok(): continue
                    for n in [2 ** (L - 1), 2 ** L - 1] + [random.randrange(2 ** (L - 1), 2 ** L) for _ in range(4)]:
                        cnt += 1
                        if simulateE(p, n) != fib_pair(n)[0]: bad += 1; print("WRONG", p, n)
    print("checked", cnt, "bad", bad)

# ---------------------------------------------------------------- land-based bit tests (variant 'L')
def fin4L_defs():
    """fin4 family with bit tests `Nat.beq (Nat.land n 2^k) 0` and parity constants from `Nat.land`."""
    out = []
    for cm in ("a", 0, 1):
        name = {"a": "fin4L", 0: "fin4Lc0", 1: "fin4Lc1"}[cm]
        nv = "n" if cm == "a" else "_"
        if cm == "a":   # c = bit 2 of n: 4c = land n 4, 8c = 2 * land n 4
            A = "(Nat.sub (Nat.add a (Nat.land n (nat_lit 4))) (nat_lit 2))"
            B = "(Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.land n (nat_lit 4)) (Nat.land n (nat_lit 4)))))"
            C = "(Nat.sub (Nat.add (nat_lit 2) b) (Nat.land n (nat_lit 4)))"
        else:
            A, B, C = _abc_lean(cm)
        def br(body): return f"(fun {nv} a b => share A := {A}; share B := {B}; {body})"
        r0 = br("Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) A")
        r1 = br("Nat.add (nat_lit 1) (Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) B)")
        r2 = br("Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) B")
        r3 = f"(fun {nv} a b => Nat.sub (Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) {C}) (nat_lit 1))"
        out.append(f"""def {name} (n a b : Nat) : Nat :=
  Bool.rec {MOT}
    (fun n a b => Bool.rec {MOT} {r3} {r2} (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (fun n a b => Bool.rec {MOT} {r1} {r0} (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (Nat.beq (Nat.land n (nat_lit 2)) (nat_lit 0)) n a b
""")
    return "\n".join(out)

def selL_def(name, k, cm, k0, k1):
    if cm == "a":   # c = bit k+1: 4c, 8c from land n 2^(k+1)
        w = 2 ** (k + 1)
        if w == 4: c4 = "(Nat.land n (nat_lit 4))"
        elif w > 4: c4 = f"(Nat.div (Nat.land n {lit(w)}) {lit(w // 4)})"
        c8 = f"(Nat.add {c4} {c4})"
        A = f"(Nat.sub (Nat.add a {c4}) (nat_lit 2))"
        B = f"(Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a {c8}))"
        C = f"(Nat.sub (Nat.add (nat_lit 2) b) {c4})"
    else:
        A, B, C = _abc_lean(cm)
    return f"""def {name} (n a b : Nat) : Nat :=
  Bool.rec {MOT}
    (fun n a b => share B := {B}; {k1} n (Nat.pow B (nat_lit 2)) (Nat.pow {C} (nat_lit 2)))
    (fun n a b => share B := {B}; {k0} n (Nat.pow {A} (nat_lit 2)) (Nat.pow B (nat_lit 2)))
    (Nat.beq (Nat.land n {lit(2 ** k)}) (nat_lit 0)) n a b
"""

def emitEL(p, fname):
    q = Plan(p.L, p.t, p.P, p.c, "D")
    src = pl.emit(q, fname)
    head = src.partition("  share hp")[0]
    if "share h1 :=" in head: head = head.split("  share h1 :=")[0]
    helpers = []
    def cont(k, cm):
        if k < 2: return {"a": "fin4L", 0: "fin4Lc0", 1: "fin4Lc1"}[cm]
        nm = f"{fname}_s{k}_{cm}"
        helpers.append(selL_def(nm, k, cm, cont(k - 1, 0), cont(k - 1, 1)))
        return nm
    first = cont(p.r - 1, "a")
    body = head.rstrip() + f"\n  {first} n (Nat.pow P0 (nat_lit 2)) (Nat.pow Q0 (nat_lit 2))\n"
    seen, hs = set(), []
    for h in helpers:
        nm = h.split()[1]
        if nm not in seen: seen.add(nm); hs.append(h)
    return "\n".join(reversed(hs)) + "\n" + body
