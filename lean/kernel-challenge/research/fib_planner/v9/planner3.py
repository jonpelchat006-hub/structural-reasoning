"""Planner v3: v8's plan space plus
  tab  'm1' (X^(m+1): (F m, F(m+1)), v8)  |  'm0' (X^m: (F(m-1), F m))
  conv 'xy' (v8: one Fibonacci-pair doubling)  |  'sg' (L(m) then F(2m) = F(m)L(m), L(2m) = L(m)^2 + 4c - 2)
  fin  'C' | 'A' (pick) | 'Ab' (Bool.rec on bit 0) | 'D' (v8 selected doublings) | 'E' (branched, land bits)
"""
import sys, random
from dataclasses import dataclass
sys.path.insert(0, "/home/claude/fibvar")
sys.set_int_max_str_digits(0)
from planner import K_of, fib_pair, lit
import planner2 as p2

@dataclass(frozen=True)
class Plan3:
    L: int; t: int; P: int; c: int; fin: str; tab: str = "m1"; conv: str = "xy"
    @property
    def r(self): return self.L - self.t - self.P
    def ok(self):
        if self.P < 1 or self.t < 1 or self.r < 0 or not (0 <= self.c <= self.P): return False
        if self.conv == "sg" and self.c < 1: return False
        if self.fin == "C": return self.r == 0 and self.c == self.P
        if self.fin in ("A", "Ab"): return self.r == 1 and self.c == self.P
        if self.fin == "D": return self.r >= 1
        if self.fin == "E": return self.r >= 2
        return False
    def name(self): return f"L{self.L}_t{self.t}_P{self.P}_c{self.c}_{self.fin}_{self.tab}_{self.conv}"

def tab_py(idx, K, mode):
    X = 2 ** K; M = X * X - X - 1
    R = pow(X, idx + (1 if mode == "m1" else 0)) % M
    return R % X, R // X            # m1: (F idx, F(idx+1));  m0: (F(idx-1), F idx)

def simulate(p, n):
    L, t, P, c, r = p.L, p.t, p.P, p.c, p.r
    m = n >> (L - t)
    lo, hi = tab_py(m, K_of(t), p.tab)
    a, b = (lo, hi) if p.tab == "m1" else (hi, lo + hi)      # (F m, F(m+1)) for the simulation
    if p.conv == "xy" or c == 0:
        x = a * (2 * b - a); y = b * (2 * a + b) - x
        f, l = x, 2 * y - x
    else:
        l0 = 2 * b - a if p.tab == "m1" else 2 * lo + hi       # L(m)
        f = a * l0 if p.tab == "m1" else hi * l0
        l = l0 * l0 + 4 * (m % 2) - 2
    if c >= 1:
        for _ in range(c - 1): f, l = f * l, l * l - 2
        if c < P:
            pp, qq = l, (5 * f + l) // 2
            for _ in range(P - c): pp, qq = pp * pp - 2, (qq * qq + 2) - (pp * pp - 2)
    else:
        pp, qq = 2 * y - x, 2 * x + y
        for _ in range(P - 1): pp, qq = pp * pp - 2, (qq * qq + 2) - (pp * pp - 2)
    d = (n >> r) % (2 ** P)
    elo, ehi = tab_py(d, K_of(P), p.tab)
    u, v = (elo, ehi) if p.tab == "m1" else (ehi, elo + ehi)   # (F d, F(d+1))
    if p.fin == "C":
        le = 2 * v - u if p.tab == "m1" else 2 * elo + ehi
        return (f * le + l * u) // 2
    if p.fin in ("A", "Ab"):
        A, B = f, (f + l) // 2
        P_, Q_ = A * (v - u) + B * u, A * u + B * v
        t1 = (n >> 1) % 2; D = 2 * Q_ - P_
        return P_ * D if n % 2 == 0 else Q_ * D + 2 * t1 - 1
    if c == P:
        pp, qq = l, (5 * f + l) // 2
    Pp, Qq = (v - u) * pp + u * qq, u * pp + v * qq
    if p.fin == "D":
        for k in range(r - 1, 0, -1):
            par = (n >> (k + 1)) % 2; tb = (n >> k) % 2
            s0 = Pp * Pp + 4 * par - 2; s2 = Qq * Qq + 2 - 4 * par; s1 = s2 - s0
            Pp, Qq = s0 + tb * (s1 - s0), s1 + tb * s0
        t1 = (n >> 1) % 2; Fh = (2 * Qq - Pp) // 5
        return Fh * Pp if n % 2 == 0 else Fh * Qq + 1 - 2 * t1
    for k in range(r - 1, 1, -1):
        cpar = (n >> (k + 1)) % 2; bit = (n >> k) % 2
        A_, B_, C_ = p2._ABC(Pp * Pp, Qq * Qq, cpar)
        Pp, Qq = (A_, B_) if bit == 0 else (B_, C_)
    return p2.fin4_py(n, Pp * Pp, Qq * Qq, (n >> 2) % 2)

# ------------------------------------------------------------------ Lean
def emit(p, fname):
    L, t, P, c, r = p.L, p.t, p.P, p.c, p.r
    out = []
    def sh(name, expr): out.append(f"  share {name} := {expr};")
    def tab(prefix, idx, K):
        e = f"(Nat.add {idx} (nat_lit 1))" if p.tab == "m1" else idx
        sh(f"{prefix}r", f"Nat.mod (Nat.pow (numeral% (Nat.pow 2 {K})) {e}) "
                         f"(numeral% (Nat.pow 2 {2 * K} - Nat.pow 2 {K} - 1))")
        sh(f"{prefix}lo", f"Nat.mod {prefix}r (numeral% (Nat.pow 2 {K}))")
        sh(f"{prefix}hi", f"Nat.div {prefix}r (numeral% (Nat.pow 2 {K}))")
        return f"{prefix}lo", f"{prefix}hi"
    sh("m", f"Nat.div n {lit(2 ** (L - t))}")
    lo, hi = tab("t", "m", K_of(t))
    if p.conv == "xy" or c == 0:
        if p.tab == "m1": a, b = lo, hi
        else:
            sh("tb1", f"Nat.add {lo} {hi}"); a, b = hi, "tb1"
        sh("x0", f"Nat.mul {a} (Nat.sub (Nat.add {b} {b}) {a})")
        sh("y0", f"Nat.sub (Nat.mul {b} (Nat.add (Nat.add {a} {a}) {b})) x0")
        f0, l0e = "x0", "Nat.sub (Nat.add y0 y0) x0"
    else:
        if p.tab == "m1":
            sh("l0", f"Nat.sub (Nat.add {hi} {hi}) {lo}"); sh("x0", f"Nat.mul {lo} l0")
        else:
            sh("l0", f"Nat.add {lo} (Nat.add {lo} {hi})"); sh("x0", f"Nat.mul {hi} l0")
        # 4c with c = m mod 2 = bit (L - t) of n:  land (n >> (L-t-2)) 4
        s = L - t - 2
        c4 = f"(Nat.land (Nat.div n {lit(2 ** s)}) (nat_lit 4))" if s > 0 else "(Nat.land n (nat_lit 4))"
        f0, l0e = "x0", f"Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) {c4}) (nat_lit 2)"
    if c >= 1:
        sh("f1", f0); sh("l1", l0e)
        f, l = "f1", "l1"
        for k in range(2, c + 1):
            sh(f"f{k}", f"Nat.mul {f} {l}"); sh(f"l{k}", f"Nat.sub (Nat.pow {l} (nat_lit 2)) (nat_lit 2)")
            f, l = f"f{k}", f"l{k}"
        if c < P:
            sh("cq", f"Nat.div (Nat.add (Nat.mul (nat_lit 5) {f}) {l}) (nat_lit 2)")
            pp, qq = l, "cq"
            for k in range(c + 1, P + 1):
                sh(f"p{k}", f"Nat.sub (Nat.pow {pp} (nat_lit 2)) (nat_lit 2)")
                sh(f"z{k}", f"Nat.add (Nat.pow {qq} (nat_lit 2)) (nat_lit 2)")
                sh(f"q{k}", f"Nat.sub z{k} p{k}")
                pp, qq = f"p{k}", f"q{k}"
    else:
        sh("p1", "Nat.sub (Nat.add y0 y0) x0"); sh("q1", "Nat.add (Nat.add x0 x0) y0")
        pp, qq = "p1", "q1"
        for k in range(2, P + 1):
            sh(f"p{k}", f"Nat.sub (Nat.pow {pp} (nat_lit 2)) (nat_lit 2)")
            sh(f"z{k}", f"Nat.add (Nat.pow {qq} (nat_lit 2)) (nat_lit 2)")
            sh(f"q{k}", f"Nat.sub z{k} p{k}")
            pp, qq = f"p{k}", f"q{k}"
    hr = "n" if r == 0 else f"(Nat.div n {lit(2 ** r)})"
    sh("d", f"Nat.mod {hr} {lit(2 ** P)}")
    elo, ehi = tab("e", "d", K_of(P))
    if p.tab == "m1": u, v, um = elo, ehi, f"(Nat.sub {ehi} {elo})"      # F d, F(d+1), F(d-1)
    else: u, v, um = ehi, f"(Nat.add {elo} {ehi})", elo
    helpers = []
    if p.fin == "C":
        le = f"Nat.sub (Nat.add {v} {v}) {u}" if p.tab == "m1" else f"Nat.add {elo} (Nat.add {elo} {ehi})"
        sh("le", le)
        out.append(f"  Nat.div (Nat.add (Nat.mul {f} le) (Nat.mul {l} {u})) (nat_lit 2)")
    elif p.fin in ("A", "Ab"):
        if p.tab == "m0": sh("ev", v); v = "ev"
        sh("A", f); sh("B", f"Nat.div (Nat.add {f} {l}) (nat_lit 2)")
        sh("P", f"Nat.add (Nat.mul A {um}) (Nat.mul B {u})")
        sh("Q", f"Nat.add (Nat.mul A {u}) (Nat.mul B {v})")
        sh("D", "Nat.sub (Nat.add Q Q) P")
        if p.fin == "A":
            sh("h1", f"Nat.div n {lit(2)}"); sh("t1", f"Nat.mod h1 {lit(2)}")
            out.append(f"  pick (Nat.mod n (nat_lit 2)) (Nat.mul P D)\n"
                       f"    (Nat.sub (Nat.add (Nat.mul Q D) (Nat.add t1 t1)) (nat_lit 1))")
        else:
            out.append(f"  finAb n P Q D")
    else:
        if c == P:
            sh("cq", f"Nat.div (Nat.add (Nat.mul (nat_lit 5) {f}) {l}) (nat_lit 2)")
            pp, qq = l, "cq"
        if p.tab == "m0": sh("ev", v); v = "ev"
        sh("P0", f"Nat.add (Nat.mul {um} {pp}) (Nat.mul {u} {qq})")
        sh("Q0", f"Nat.add (Nat.mul {u} {pp}) (Nat.mul {v} {qq})")
        if p.fin == "D":
            Pn, Qn = "P0", "Q0"
            for k in range(r - 1, 0, -1):
                sh(f"hp{k}", f"Nat.div n {lit(2 ** (k + 1))}"); sh(f"par{k}", f"Nat.mod hp{k} {lit(2)}")
                sh(f"hb{k}", f"Nat.div n {lit(2 ** k)}"); sh(f"tb{k}", f"Nat.mod hb{k} {lit(2)}")
                sh(f"s0_{k}", f"Nat.sub (Nat.add (Nat.pow {Pn} (nat_lit 2)) (Nat.mul (nat_lit 4) par{k})) (nat_lit 2)")
                sh(f"s2_{k}", f"Nat.sub (Nat.add (Nat.pow {Qn} (nat_lit 2)) (nat_lit 2)) (Nat.mul (nat_lit 4) par{k})")
                sh(f"s1_{k}", f"Nat.sub s2_{k} s0_{k}")
                sh(f"sA{k}", f"Nat.add s0_{k} (Nat.mul tb{k} (Nat.sub s1_{k} s0_{k}))")
                sh(f"sB{k}", f"Nat.add s1_{k} (Nat.mul tb{k} s0_{k})")
                Pn, Qn = f"sA{k}", f"sB{k}"
            sh("h1", f"Nat.div n {lit(2)}"); sh("t1", f"Nat.mod h1 {lit(2)}")
            sh("Fh", f"Nat.div (Nat.sub (Nat.add {Qn} {Qn}) {Pn}) (nat_lit 5)")
            out.append(f"  pick (Nat.mod n (nat_lit 2)) (Nat.mul Fh {Pn})\n"
                       f"    (Nat.sub (Nat.add (Nat.mul Fh {Qn}) (nat_lit 1)) (Nat.add t1 t1))")
        else:
            def cont(k, cm):
                if k < 2: return {"a": "fin4L", 0: "fin4Lc0", 1: "fin4Lc1"}[cm]
                nm = f"{fname}_s{k}_{cm}"
                helpers.append(p2.selL_def(nm, k, cm, cont(k - 1, 0), cont(k - 1, 1)))
                return nm
            first = cont(r - 1, "a")
            out.append(f"  {first} n (Nat.pow P0 (nat_lit 2)) (Nat.pow Q0 (nat_lit 2))")
    seen, hs = set(), []
    for h in helpers:
        nm = h.split()[1]
        if nm not in seen: seen.add(nm); hs.append(h)
    body = "\n".join(out)
    return "\n".join(reversed(hs)) + f"\nset_option exponentiation.threshold 2000 in\ndef {fname} (n : Nat) : Nat :=\n{body}\n"

FINAB = f"""/-- The last bit from the Fibonacci pair `(P, Q) = (F(h), F(h+1))`, `D = L(h)`, `h = n / 2`. -/
def finAb (n P Q D : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat → Nat)
    (fun n _ Q D => Nat.sub (Nat.add (Nat.mul Q D) (Nat.land n (nat_lit 2))) (nat_lit 1))
    (fun _ P _ D => Nat.mul P D)
    (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n P Q D
"""

def common_defs():
    return p2.fin4L_defs() + "\n" + FINAB

def plans_for(L, ts=(7, 8), Ps=range(5, 10), fins=("C", "A", "Ab", "D", "E"), tabs=("m1", "m0"), convs=("xy", "sg")):
    out = []
    for t in ts:
        for P in Ps:
            if K_of(P) > 356: continue
            for c in range(0, P + 1):
                for fin in fins:
                    for tb in tabs:
                        for cv in convs:
                            p = Plan3(L, t, P, c, fin, tb, cv)
                            if p.ok(): out.append(p)
    return out

if __name__ == "__main__":
    random.seed(3)
    bad = cnt = 0
    for L in range(13, 19):
        for p in plans_for(L):
            for n in [2 ** (L - 1), 2 ** L - 1] + [random.randrange(2 ** (L - 1), 2 ** L) for _ in range(2)]:
                cnt += 1
                if simulate(p, n) != fib_pair(n)[0]:
                    bad += 1; print("WRONG", p.name(), n); break
    print("checked", cnt, "bad", bad, {L: len(plans_for(L)) for L in range(13, 19)})
