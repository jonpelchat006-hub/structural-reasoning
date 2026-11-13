#!/usr/bin/env python3
"""The fib planner (Oct 18, Jonathan's "cut at thresholds, pick the cheapest form per slice, assemble").

A plan cuts the computation of F(n), for an L-bit n, into slices:

  TAB   the top t bits m of n from one modular power: (F(m), F(m+1))            [table of t bits]
  P pure doublings, the first c of them in the (F, L) form (one product + one square per level)
        and the rest in the Lucas-pair form (L, L') (two squares per level); the cut between the
        two forms costs one conversion L(j+1) = (5 F(j) + L(j)) / 2
  ADD   the next P bits d from a second modular power, joined by the addition formula
  FIN   the last r bits: 'C' (r = 0, the join is the answer), 'A' (r = 1, from (F, F')),
        'D' (r >= 1, from the Lucas pair: r - 1 selected doublings, then the last bit)

with L = t + P + r. Every value crossing a cut is one or two numbers (the thin waist), so the
conversion at each cut is a few operations. `simulate` runs a plan in Python (to check the formulas);
`emit` writes it as a Lean `share` chain in the v7 style; the kernel bench prices it.
"""
import itertools, random, sys
from dataclasses import dataclass

sys.set_int_max_str_digits(0)


def fib_pair(n):
    a, b = 0, 1
    for bit in bin(n)[2:] if n else "":
        c = a * (2 * b - a); d = a * a + b * b
        a, b = (c, d) if bit == "0" else (d, c + d)
    return a, b


def K_of(bits):
    """smallest K with F(2^bits) + 2 <= 2^K (the table's lane width)"""
    f = fib_pair(2 ** bits)[0]
    K = 1
    while f + 2 > 2 ** K: K += 1
    return K


@dataclass(frozen=True)
class Plan:
    L: int          # bit length of n
    t: int          # top table bits
    P: int          # pure doublings (= low table bits)
    c: int          # how many of the doublings use the (F, L) form (the rest: Lucas pairs)
    fin: str        # 'C', 'A' or 'D'

    @property
    def r(self): return self.L - self.t - self.P

    def ok(self):
        if self.P < 1 or self.t < 1 or self.r < 0 or not (0 <= self.c <= self.P): return False
        if self.fin == "C": return self.r == 0 and self.c == self.P
        if self.fin == "A": return self.r == 1 and self.c == self.P
        if self.fin == "D": return self.r >= 1
        return False

    def name(self): return f"L{self.L}_t{self.t}_P{self.P}_c{self.c}_{self.fin}"


# ------------------------------------------------------------------ Python simulation (checks the formulas)
def simulate(p, n):
    L, t, P, c, r = p.L, p.t, p.P, p.c, p.r
    m = n >> (L - t)
    K = K_of(t); X = 2 ** K; M = X * X - X - 1
    R = pow(X, m + 1) % M; a, b = R % X, R // X                      # F(m), F(m+1)
    assert (a, b) == fib_pair(m)
    if c >= 1:
        x = a * (2 * b - a); y = b * (2 * a + b) - x; f, l = x, 2 * y - x   # F(2m), L(2m)
        for _ in range(c - 1): f, l = f * l, l * l - 2
        if c < P:
            p_, q_ = l, (5 * f + l) // 2
            for _ in range(P - c): p_, q_ = p_ * p_ - 2, (q_ * q_ + 2) - (p_ * p_ - 2)
            form = "LL"
        else:
            form = "FL"
    else:
        x = a * (2 * b - a); y = b * (2 * a + b) - x
        p_, q_ = 2 * y - x, 2 * x + y                                     # L(2m), L(2m+1)
        for _ in range(P - 1): p_, q_ = p_ * p_ - 2, (q_ * q_ + 2) - (p_ * p_ - 2)
        form = "LL"
    d = (n >> r) % (2 ** P)
    Kd = K_of(P); Xd = 2 ** Kd; Md = Xd * Xd - Xd - 1
    Q = pow(Xd, d + 1) % Md; u, v = Q % Xd, Q // Xd                     # F(d), F(d+1)
    if p.fin == "C":
        le = 2 * v - u
        return (f * le + l * u) // 2
    if p.fin == "A":
        A, B = f, (f + l) // 2
        P_, Q_ = A * (v - u) + B * u, A * u + B * v                        # F(n'), F(n'+1)
        t1 = (n >> 1) % 2; D = 2 * Q_ - P_
        return P_ * D if n % 2 == 0 else Q_ * D + 2 * t1 - 1
    # 'D': Lucas pair
    if form == "FL":
        p_, q_ = l, (5 * f + l) // 2
    Pp, Qq = (v - u) * p_ + u * q_, u * p_ + v * q_                        # L(h_r), L(h_r + 1)
    for k in range(r - 1, 0, -1):                                          # selected doublings to h_k
        par = (n >> (k + 1)) % 2; tb = (n >> k) % 2
        s0 = Pp * Pp + 4 * par - 2; s2 = Qq * Qq + 2 - 4 * par; s1 = s2 - s0
        Pp, Qq = s0 + tb * (s1 - s0), s1 + tb * s0
    t1 = (n >> 1) % 2
    Fh = (2 * Qq - Pp) // 5
    return Fh * Pp if n % 2 == 0 else Fh * Qq + 1 - 2 * t1


# ------------------------------------------------------------------ Lean emission (v7 `share` style)
HEADER = r'''import Spec
import Lean

namespace Submission

open Lean Elab Term Meta in
elab "share " x:ident " := " v:term "; " b:term : term <= ty => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b ty)
    return b.replaceFVar fv v

open Lean Elab Term Meta in
elab "numeral% " e:term : term => do
  let e ← elabTermEnsuringType e (some (mkConst ``Nat))
  synthesizeSyntheticMVarsNoPostponing
  let some n ← (evalNat (← instantiateMVars e)).run | throwError "numeral%: cannot evaluate {e}"
  return mkRawNatLit n

def pick (x z s : Nat) : Nat := Nat.rec (motive := fun _ => Nat) z (fun _ _ => s) x

def lvl (n : Nat) : Nat → Nat → Nat → Nat :=
  fun L => Nat.rec (motive := fun _ => Nat → Nat → Nat) (fun a _ => a)
    (fun k ih a b =>
      Nat.rec (motive := fun _ => Nat)
        (ih (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a))
            (Nat.sub (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b))
              (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a))))
        (fun _ _ => ih (Nat.sub (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b))
              (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a)))
            (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b)))
        (Nat.land (Nat.shiftRight n k) (nat_lit 1))) L

def gen (n : Nat) : Nat := lvl n (Nat.add (Nat.log2 n) (nat_lit 1)) (nat_lit 0) (nat_lit 1)
'''

DISPATCH = r'''
def impl (n : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat)
    (fun n => Bool.rec (motive := fun _ => Nat → Nat)
      (fun n => Bool.rec (motive := fun _ => Nat → Nat) gen chain18 (Nat.ble n (nat_lit 262143)) n)
      (fun n => Bool.rec (motive := fun _ => Nat → Nat) chain17 chain16 (Nat.ble n (nat_lit 65535)) n)
      (Nat.ble n (nat_lit 131071)) n)
    (fun n => Bool.rec (motive := fun _ => Nat → Nat)
      (fun n => Bool.rec (motive := fun _ => Nat → Nat) chain15 chain14 (Nat.ble n (nat_lit 16383)) n)
      chain13 (Nat.ble n (nat_lit 8191)) n)
    (Nat.ble n (nat_lit 32767)) n

end Submission
'''


def lit(v): return f"(nat_lit {v})"


def emit(p, fname):
    L, t, P, c, r = p.L, p.t, p.P, p.c, p.r
    out = []
    def sh(name, expr): out.append(f"  share {name} := {expr};")
    def tab(prefix, idx, K):
        sh(f"{prefix}r", f"Nat.mod (Nat.pow (numeral% (Nat.pow 2 {K})) (Nat.add {idx} (nat_lit 1))) "
                         f"(numeral% (Nat.pow 2 {2 * K} - Nat.pow 2 {K} - 1))")
        sh(f"{prefix}lo", f"Nat.mod {prefix}r (numeral% (Nat.pow 2 {K}))")
        sh(f"{prefix}hi", f"Nat.div {prefix}r (numeral% (Nat.pow 2 {K}))")
        return f"{prefix}lo", f"{prefix}hi"
    sh("m", f"Nat.div n {lit(2 ** (L - t))}")
    a, b = tab("t", "m", K_of(t))
    sh("x0", f"Nat.mul {a} (Nat.sub (Nat.add {b} {b}) {a})")
    sh("y0", f"Nat.sub (Nat.mul {b} (Nat.add (Nat.add {a} {a}) {b})) x0")
    form = None
    if c >= 1:
        sh("f1", "x0"); sh("l1", "Nat.sub (Nat.add y0 y0) x0")
        f, l = "f1", "l1"
        for k in range(2, c + 1):
            sh(f"f{k}", f"Nat.mul {f} {l}"); sh(f"l{k}", f"Nat.sub (Nat.pow {l} (nat_lit 2)) (nat_lit 2)")
            f, l = f"f{k}", f"l{k}"
        form = "FL"
        if c < P:
            sh("cq", f"Nat.div (Nat.add (Nat.mul (nat_lit 5) {f}) {l}) (nat_lit 2)")
            pp, qq = l, "cq"
            for k in range(c + 1, P + 1):
                sh(f"p{k}", f"Nat.sub (Nat.pow {pp} (nat_lit 2)) (nat_lit 2)")
                sh(f"z{k}", f"Nat.add (Nat.pow {qq} (nat_lit 2)) (nat_lit 2)")
                sh(f"q{k}", f"Nat.sub z{k} p{k}")
                pp, qq = f"p{k}", f"q{k}"
            form = "LL"
    else:
        sh("p1", "Nat.sub (Nat.add y0 y0) x0"); sh("q1", "Nat.add (Nat.add x0 x0) y0")
        pp, qq = "p1", "q1"
        for k in range(2, P + 1):
            sh(f"p{k}", f"Nat.sub (Nat.pow {pp} (nat_lit 2)) (nat_lit 2)")
            sh(f"z{k}", f"Nat.add (Nat.pow {qq} (nat_lit 2)) (nat_lit 2)")
            sh(f"q{k}", f"Nat.sub z{k} p{k}")
            pp, qq = f"p{k}", f"q{k}"
        form = "LL"
    hr = "n" if r == 0 else f"(Nat.div n {lit(2 ** r)})"
    sh("d", f"Nat.mod {hr} {lit(2 ** P)}")
    u, v = tab("e", "d", K_of(P))
    if p.fin == "C":
        sh("le", f"Nat.sub (Nat.add {v} {v}) {u}")
        out.append(f"  Nat.div (Nat.add (Nat.mul {f} le) (Nat.mul {l} {u})) (nat_lit 2)")
    elif p.fin == "A":
        sh("A", f); sh("B", f"Nat.div (Nat.add {f} {l}) (nat_lit 2)")
        sh("P", f"Nat.add (Nat.mul A (Nat.sub {v} {u})) (Nat.mul B {u})")
        sh("Q", f"Nat.add (Nat.mul A {u}) (Nat.mul B {v})")
        sh("h1", f"Nat.div n {lit(2)}"); sh("t1", f"Nat.mod h1 {lit(2)}")
        sh("D", "Nat.sub (Nat.add Q Q) P")
        out.append(f"  pick (Nat.mod n (nat_lit 2)) (Nat.mul P D)\n"
                   f"    (Nat.sub (Nat.add (Nat.mul Q D) (Nat.add t1 t1)) (nat_lit 1))")
    else:
        if form == "FL":
            sh("cq", f"Nat.div (Nat.add (Nat.mul (nat_lit 5) {f}) {l}) (nat_lit 2)")
            pp, qq = l, "cq"
        sh("P0", f"Nat.add (Nat.mul (Nat.sub {v} {u}) {pp}) (Nat.mul {u} {qq})")
        sh("Q0", f"Nat.add (Nat.mul {u} {pp}) (Nat.mul {v} {qq})")
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
    body = "\n".join(out)
    return f"set_option exponentiation.threshold 2000 in\ndef {fname} (n : Nat) : Nat :=\n{body}\n"


def module(plans):
    """a Submission module with one plan per bit length 13..18 (the v7 dispatch)"""
    parts = [HEADER]
    for L in range(13, 19):
        parts.append(emit(plans[L], f"chain{L}"))
    parts.append(DISPATCH)
    return "\n".join(parts)


def plans_for(L, ts=(6, 7, 8), Ps=range(4, 10)):
    out = []
    for t in ts:
        for P in Ps:
            for c in range(0, P + 1):
                for fin in "CAD":
                    p = Plan(L, t, P, c, fin)
                    if p.ok() and K_of(P) <= 356: out.append(p)
    return out


V7 = {13: Plan(13, 8, 5, 5, "C"), 14: Plan(14, 8, 6, 6, "C"), 15: Plan(15, 8, 7, 7, "C"),
      16: Plan(16, 8, 7, 7, "A"), 17: Plan(17, 8, 8, 8, "A"), 18: Plan(18, 8, 8, 0, "D")}


if __name__ == "__main__":
    random.seed(1)
    bad = 0; count = 0
    for L in range(13, 19):
        for p in plans_for(L):
            for n in [2 ** (L - 1), 2 ** L - 1] + [random.randrange(2 ** (L - 1), 2 ** L) for _ in range(3)]:
                count += 1
                if simulate(p, n) != fib_pair(n)[0]:
                    bad += 1; print("WRONG", p, n); break
    print(f"checked {count} (plan, n) pairs, {bad} wrong; plans per L:",
          {L: len(plans_for(L)) for L in range(13, 19)})
