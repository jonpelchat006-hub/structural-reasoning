import Spec
import Lean

/-!
# Fibonacci: modular-power tables, Lucas doubling, the addition formula and a branched end (v9)

`X = 2^K` and `M = X² − X − 1`. In `ℤ[x] / (x² − x − 1)`, `x^j = F(j) x + F(j−1)`, and evaluating at
`x = X` is a ring map to `ℤ / M`; while `F(j+1) + 2 ≤ X` the representative `F(j) X + F(j−1)` is
already reduced, so one power and one kernel `%` give `F(j)` and `F(j−1)` (`tab0_spec`; for `j = 0`
the low half is `1 = F(1) − F(0)`).

Building blocks, each priced in the judge's kernel window (Oct 24):
* `tab0`: the top `t` bits `m` of `n` give `(F(m+1) − F(m), F(m))` from one modular power
  (`K = 88` for `t = 7`, `177` for `t = 8`);
* `sgc`: the first doubling straight from the table: `L(m) = lo + (lo + hi)`, `F(2m) = F(m) L(m)`,
  `L(2m) = L(m)² + 4 (m mod 2) − 2`, the parity read with one `Nat.land`;
* `(F, L)` doublings `(F(j), L(j)) ↦ (F(j) L(j), L(j)² − 2)` (even `j`): one product and one square;
* the switch `L(j+1) = (5 F(j) + L(j)) / 2` (`conv`) to Lucas pairs, and Lucas-pair doublings by two
  squares (`L(2j) = L(j)² − 2`, `L(2j+2) = L(j+1)² + 2`, `L(2j+1) = L(2j+2) − L(2j)`);
* the low bits from a second `tab0`, joined by the addition formula (`combL0` for a Lucas pair,
  `comb0` for a Fibonacci pair, or `2 F(N + e) = F(N) L(e) + L(N) F(e)` when no bits remain);
* the end (`fin4L`): from the squares `a = L(j)²`, `b = L(j+1)²` at `j = n / 4`, with
  `A = L(2j) = a − 2ε`, `B = L(2j+1) = b − a + 4ε`, `C = L(2j+2) = b + 2ε` (`ε = (−1)^j`),
  `F(2j) = (2B − A) / 5` and `F(2j+1) = (a + b) / 5`, one closed formula for each `n mod 4`:
  `F(4j) = F(2j) A`, `F(4j+1) = F(2j) B + 1`, `F(4j+2) = F(2j+1) B`, `F(4j+3) = F(2j+1) C − 1`,
  chosen by two `Bool.rec` tests on `Nat.land n 2` and `Nat.land n 1`. `sel2a` puts one branched
  selected doubling (bit 2) in front; its branch also fixes `ε` for the end (`fin4Lc0`, `fin4Lc1`).
By bit length:
* `n < 2^14` (`chain14` = `chainC0`): 7-bit top table, 7 `(F, L)` doublings, the 7 low bits joined;
* 15 bits (`chain15` = `chainC0`): 8-bit top table, 7 doublings, the 7 low bits joined;
* 16 bits (`chain16` = `chainA0`): 8-bit top table, 7 doublings, 7 low bits at `n / 2`, the last bit;
* 17 bits (`chain17` = `chainE2`): 8-bit top table, 6 `(F, L)` doublings, the switch, 1 Lucas-pair
  doubling, 7 low bits at `n / 4`, the four-way end;
* 18 bits (`chain18` = `chainE3`): the same with the low bits at `n / 8` and `sel2a` before the end.
The bit length is found by two or three `Bool.rec` tests on `Nat.ble` whose branches are closed
functions applied to `n`; other inputs use the general doubling from `(F(0), F(1))` (`gen`, with
`Nat.log2`). Every unrolled branch is proved equal to its structured chain by `rfl` (checked by the
kernel). All numerals are raw `nat_lit`s or `numeral%` literals (computed at elaboration time).
-/

namespace Submission

open Lean Elab Term Meta in
/-- `share x := v; b`: elaborate `b` with every `x` replaced by the same term `v` (one shared
expression node, not a kernel `let`). -/
elab "share " x:ident " := " v:term "; " b:term : term <= ty => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b ty)
    return b.replaceFVar fv v

open Lean Elab Term Meta in
/-- `numeral% e` is the value of the closed arithmetic expression `e`, inserted as a raw numeral
(computed once at elaboration time, so the kernel never recomputes it). -/
elab "numeral% " e:term : term => do
  let e ← elabTermEnsuringType e (some (mkConst ``Nat))
  synthesizeSyntheticMVarsNoPostponing
  let some n ← (evalNat (← instantiateMVars e)).run | throwError "numeral%: cannot evaluate {e}"
  return mkRawNatLit n

/-! ## Implementation -/

/-- Process bits `k-1, …, 0` of `n` from the pair `(a, b) = (F(m), F(m+1))`. -/
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

/-- `z` if `x = 0`, else `s`. -/
def pick (x z s : Nat) : Nat := Nat.rec (motive := fun _ => Nat) z (fun _ _ => s) x

/-- General path: all bits, from `(F(0), F(1))`. -/
def gen (n : Nat) : Nat := lvl n (Nat.add (Nat.log2 n) (nat_lit 1)) (nat_lit 0) (nat_lit 1)

/-! ## Doubling steps and the addition formula (used on the tested range) -/

/-- The last bit `t0` (with `t1 = m mod 2`): `F(2m) = a(2b − a)` or `F(2m+1) = b(2b − a) + 2 t1 − 1`. -/
def fin (t0 t1 a b : Nat) : Nat :=
  pick t0 (Nat.mul a (Nat.sub (Nat.add b b) a))
    (Nat.sub (Nat.add (Nat.mul b (Nat.sub (Nat.add b b) a)) (Nat.add t1 t1)) 1)

/-- `(F(j), F(j+1))` from the modular power `X^(j+1) mod M` (`X = 2^K`, `M = X² − X − 1`), passed
to `k` (`tab_spec`). -/
def tab (X M j : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.mod (Nat.mod (Nat.pow X (Nat.add j 1)) M) X) (Nat.div (Nat.mod (Nat.pow X (Nat.add j 1)) M) X)

/-- `n` Lucas doublings of an even index: `(F(j), L(j)) ↦ (F(j) L(j), L(j)² − 2)`. -/
def lucas (n : Nat) : Nat → Nat → (Nat → Nat → Nat) → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat → (Nat → Nat → Nat) → Nat) (fun f l k => k f l)
    (fun _ ih f l k => ih (Nat.mul f l) (Nat.sub (Nat.pow l 2) 2) k) n

/-- `(F(j), L(j)) ↦ (F(j), F(j+1))`, `F(j+1) = (F(j) + L(j)) / 2`. -/
def unL (f l : Nat) (k : Nat → Nat → Nat) : Nat := k f (Nat.div (Nat.add f l) 2)

/-- Addition formula: `(F(N + d), F(N + d + 1))` from `(F(N), F(N+1))` and `(F(d), F(d+1))`. -/
def comb (A B u v : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.add (Nat.mul A (Nat.sub v u)) (Nat.mul B u)) (Nat.add (Nat.mul A u) (Nat.mul B v))

/-! ## Lucas pairs -/

/-- `n` doublings of the Lucas pair of an even index, two squares each:
`(L(j), L(j+1)) ↦ (L(2j), L(2j+1))` with `L(2j) = L(j)² − 2`, `L(2j+2) = L(j+1)² + 2` and
`L(2j+1) = L(2j+2) − L(2j)`. -/
def lpair (n : Nat) : Nat → Nat → (Nat → Nat → Nat) → Nat :=
  Nat.rec (motive := fun _ => Nat → Nat → (Nat → Nat → Nat) → Nat) (fun p q k => k p q)
    (fun _ ih p q k => ih (Nat.sub (Nat.pow p 2) 2)
      (Nat.sub (Nat.add (Nat.pow q 2) 2) (Nat.sub (Nat.pow p 2) 2)) k) n

/-- Addition formula for the Lucas pair: `(L(N + d), L(N + d + 1))` from `(L(N), L(N+1))` and
`(F(d), F(d+1))`, by `G(N + d) = F(d−1) G(N) + F(d) G(N+1)`. -/
def combL (p q u v : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.add (Nat.mul (Nat.sub v u) p) (Nat.mul u q)) (Nat.add (Nat.mul u p) (Nat.mul v q))

/-! ## v9 helpers (branched ends) -/

def fin4L (n a b : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun n a b => Nat.sub (Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) (Nat.sub (Nat.add (nat_lit 2) b) (Nat.land n (nat_lit 4)))) (nat_lit 1)) (fun n a b => share A := (Nat.sub (Nat.add a (Nat.land n (nat_lit 4))) (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.land n (nat_lit 4)) (Nat.land n (nat_lit 4))))); Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) B) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun n a b => share A := (Nat.sub (Nat.add a (Nat.land n (nat_lit 4))) (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.land n (nat_lit 4)) (Nat.land n (nat_lit 4))))); Nat.add (nat_lit 1) (Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) B)) (fun n a b => share A := (Nat.sub (Nat.add a (Nat.land n (nat_lit 4))) (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.land n (nat_lit 4)) (Nat.land n (nat_lit 4))))); Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) A) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (Nat.beq (Nat.land n (nat_lit 2)) (nat_lit 0)) n a b

def fin4Lc0 (n a b : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ a b => Nat.sub (Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) (Nat.add (nat_lit 2) b)) (nat_lit 1)) (fun _ a b => share A := (Nat.sub a (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) a); Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) B) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ a b => share A := (Nat.sub a (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) a); Nat.add (nat_lit 1) (Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) B)) (fun _ a b => share A := (Nat.sub a (nat_lit 2)); share B := (Nat.sub (Nat.add (nat_lit 4) b) a); Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) A) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (Nat.beq (Nat.land n (nat_lit 2)) (nat_lit 0)) n a b

def fin4Lc1 (n a b : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ a b => Nat.sub (Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) (Nat.sub b (nat_lit 2))) (nat_lit 1)) (fun _ a b => share A := (Nat.add (nat_lit 2) a); share B := (Nat.sub b (Nat.add (nat_lit 4) a)); Nat.mul (Nat.div (Nat.add a b) (nat_lit 5)) B) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (fun n a b => Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ a b => share A := (Nat.add (nat_lit 2) a); share B := (Nat.sub b (Nat.add (nat_lit 4) a)); Nat.add (nat_lit 1) (Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) B)) (fun _ a b => share A := (Nat.add (nat_lit 2) a); share B := (Nat.sub b (Nat.add (nat_lit 4) a)); Nat.mul (Nat.div (Nat.sub (Nat.add B B) A) (nat_lit 5)) A) (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n a b)
    (Nat.beq (Nat.land n (nat_lit 2)) (nat_lit 0)) n a b

def sel2a (n a b : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat)
    (fun n a b => share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2)) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))))); fin4Lc1 n (Nat.pow B (nat_lit 2)) (Nat.pow (Nat.sub (Nat.add (nat_lit 2) b) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))) (nat_lit 2)))
    (fun n a b => share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2)) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))))); fin4Lc0 n (Nat.pow (Nat.sub (Nat.add a (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))) (nat_lit 2)) (nat_lit 2)) (Nat.pow B (nat_lit 2)))
    (Nat.beq (Nat.land n (nat_lit 4)) (nat_lit 0)) n a b

set_option exponentiation.threshold 800 in
/-- `F(n)` for `n < 2^14` (plan `L14_t7_P7_c7_C_m0_sg`). -/
def chain14 (n : Nat) : Nat :=
  share m := Nat.div n (nat_lit 128);
  share tr := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) m) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share tlo := Nat.mod tr (numeral% (Nat.pow 2 88));
  share thi := Nat.div tr (numeral% (Nat.pow 2 88));
  share l0 := Nat.add tlo (Nat.add tlo thi);
  share x0 := Nat.mul thi l0;
  share f1 := x0;
  share l1 := Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) (Nat.land (Nat.div n (nat_lit 32)) (nat_lit 4))) (nat_lit 2);
  share f2 := Nat.mul f1 l1;
  share l2 := Nat.sub (Nat.pow l1 (nat_lit 2)) (nat_lit 2);
  share f3 := Nat.mul f2 l2;
  share l3 := Nat.sub (Nat.pow l2 (nat_lit 2)) (nat_lit 2);
  share f4 := Nat.mul f3 l3;
  share l4 := Nat.sub (Nat.pow l3 (nat_lit 2)) (nat_lit 2);
  share f5 := Nat.mul f4 l4;
  share l5 := Nat.sub (Nat.pow l4 (nat_lit 2)) (nat_lit 2);
  share f6 := Nat.mul f5 l5;
  share l6 := Nat.sub (Nat.pow l5 (nat_lit 2)) (nat_lit 2);
  share f7 := Nat.mul f6 l6;
  share l7 := Nat.sub (Nat.pow l6 (nat_lit 2)) (nat_lit 2);
  share d := Nat.mod n (nat_lit 128);
  share er := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) d) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share elo := Nat.mod er (numeral% (Nat.pow 2 88));
  share ehi := Nat.div er (numeral% (Nat.pow 2 88));
  share le := Nat.add elo (Nat.add elo ehi);
  Nat.div (Nat.add (Nat.mul f7 le) (Nat.mul l7 ehi)) (nat_lit 2)

set_option exponentiation.threshold 800 in
/-- `F(n)` for `n < 2^15` (plan `L15_t8_P7_c7_C_m0_sg`). -/
def chain15 (n : Nat) : Nat :=
  share m := Nat.div n (nat_lit 128);
  share tr := Nat.mod (Nat.pow (numeral% (Nat.pow 2 177)) m) (numeral% (Nat.pow 2 354 - Nat.pow 2 177 - 1));
  share tlo := Nat.mod tr (numeral% (Nat.pow 2 177));
  share thi := Nat.div tr (numeral% (Nat.pow 2 177));
  share l0 := Nat.add tlo (Nat.add tlo thi);
  share x0 := Nat.mul thi l0;
  share f1 := x0;
  share l1 := Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) (Nat.land (Nat.div n (nat_lit 32)) (nat_lit 4))) (nat_lit 2);
  share f2 := Nat.mul f1 l1;
  share l2 := Nat.sub (Nat.pow l1 (nat_lit 2)) (nat_lit 2);
  share f3 := Nat.mul f2 l2;
  share l3 := Nat.sub (Nat.pow l2 (nat_lit 2)) (nat_lit 2);
  share f4 := Nat.mul f3 l3;
  share l4 := Nat.sub (Nat.pow l3 (nat_lit 2)) (nat_lit 2);
  share f5 := Nat.mul f4 l4;
  share l5 := Nat.sub (Nat.pow l4 (nat_lit 2)) (nat_lit 2);
  share f6 := Nat.mul f5 l5;
  share l6 := Nat.sub (Nat.pow l5 (nat_lit 2)) (nat_lit 2);
  share f7 := Nat.mul f6 l6;
  share l7 := Nat.sub (Nat.pow l6 (nat_lit 2)) (nat_lit 2);
  share d := Nat.mod n (nat_lit 128);
  share er := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) d) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share elo := Nat.mod er (numeral% (Nat.pow 2 88));
  share ehi := Nat.div er (numeral% (Nat.pow 2 88));
  share le := Nat.add elo (Nat.add elo ehi);
  Nat.div (Nat.add (Nat.mul f7 le) (Nat.mul l7 ehi)) (nat_lit 2)

set_option exponentiation.threshold 800 in
/-- `F(n)` for `n < 2^16` (plan `L16_t8_P7_c7_A_m0_sg`). -/
def chain16 (n : Nat) : Nat :=
  share m := Nat.div n (nat_lit 256);
  share tr := Nat.mod (Nat.pow (numeral% (Nat.pow 2 177)) m) (numeral% (Nat.pow 2 354 - Nat.pow 2 177 - 1));
  share tlo := Nat.mod tr (numeral% (Nat.pow 2 177));
  share thi := Nat.div tr (numeral% (Nat.pow 2 177));
  share l0 := Nat.add tlo (Nat.add tlo thi);
  share x0 := Nat.mul thi l0;
  share f1 := x0;
  share l1 := Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) (Nat.land (Nat.div n (nat_lit 64)) (nat_lit 4))) (nat_lit 2);
  share f2 := Nat.mul f1 l1;
  share l2 := Nat.sub (Nat.pow l1 (nat_lit 2)) (nat_lit 2);
  share f3 := Nat.mul f2 l2;
  share l3 := Nat.sub (Nat.pow l2 (nat_lit 2)) (nat_lit 2);
  share f4 := Nat.mul f3 l3;
  share l4 := Nat.sub (Nat.pow l3 (nat_lit 2)) (nat_lit 2);
  share f5 := Nat.mul f4 l4;
  share l5 := Nat.sub (Nat.pow l4 (nat_lit 2)) (nat_lit 2);
  share f6 := Nat.mul f5 l5;
  share l6 := Nat.sub (Nat.pow l5 (nat_lit 2)) (nat_lit 2);
  share f7 := Nat.mul f6 l6;
  share l7 := Nat.sub (Nat.pow l6 (nat_lit 2)) (nat_lit 2);
  share d := Nat.mod (Nat.div n (nat_lit 2)) (nat_lit 128);
  share er := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) d) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share elo := Nat.mod er (numeral% (Nat.pow 2 88));
  share ehi := Nat.div er (numeral% (Nat.pow 2 88));
  share ev := (Nat.add elo ehi);
  share A := f7;
  share B := Nat.div (Nat.add f7 l7) (nat_lit 2);
  share P := Nat.add (Nat.mul A elo) (Nat.mul B ehi);
  share Q := Nat.add (Nat.mul A ehi) (Nat.mul B ev);
  share D := Nat.sub (Nat.add Q Q) P;
  share h1 := Nat.div n (nat_lit 2);
  share t1 := Nat.mod h1 (nat_lit 2);
  pick (Nat.mod n (nat_lit 2)) (Nat.mul P D)
    (Nat.sub (Nat.add (Nat.mul Q D) (Nat.add t1 t1)) (nat_lit 1))

set_option exponentiation.threshold 800 in
/-- `F(n)` for `n < 2^17` (plan `L17_t8_P7_c6_E_m0_sg`). -/
def chain17 (n : Nat) : Nat :=
  share m := Nat.div n (nat_lit 512);
  share tr := Nat.mod (Nat.pow (numeral% (Nat.pow 2 177)) m) (numeral% (Nat.pow 2 354 - Nat.pow 2 177 - 1));
  share tlo := Nat.mod tr (numeral% (Nat.pow 2 177));
  share thi := Nat.div tr (numeral% (Nat.pow 2 177));
  share l0 := Nat.add tlo (Nat.add tlo thi);
  share x0 := Nat.mul thi l0;
  share f1 := x0;
  share l1 := Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) (Nat.land (Nat.div n (nat_lit 128)) (nat_lit 4))) (nat_lit 2);
  share f2 := Nat.mul f1 l1;
  share l2 := Nat.sub (Nat.pow l1 (nat_lit 2)) (nat_lit 2);
  share f3 := Nat.mul f2 l2;
  share l3 := Nat.sub (Nat.pow l2 (nat_lit 2)) (nat_lit 2);
  share f4 := Nat.mul f3 l3;
  share l4 := Nat.sub (Nat.pow l3 (nat_lit 2)) (nat_lit 2);
  share f5 := Nat.mul f4 l4;
  share l5 := Nat.sub (Nat.pow l4 (nat_lit 2)) (nat_lit 2);
  share f6 := Nat.mul f5 l5;
  share l6 := Nat.sub (Nat.pow l5 (nat_lit 2)) (nat_lit 2);
  share cq := Nat.div (Nat.add (Nat.mul (nat_lit 5) f6) l6) (nat_lit 2);
  share p7 := Nat.sub (Nat.pow l6 (nat_lit 2)) (nat_lit 2);
  share z7 := Nat.add (Nat.pow cq (nat_lit 2)) (nat_lit 2);
  share q7 := Nat.sub z7 p7;
  share d := Nat.mod (Nat.div n (nat_lit 4)) (nat_lit 128);
  share er := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) d) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share elo := Nat.mod er (numeral% (Nat.pow 2 88));
  share ehi := Nat.div er (numeral% (Nat.pow 2 88));
  share ev := (Nat.add elo ehi);
  share P0 := Nat.add (Nat.mul elo p7) (Nat.mul ehi q7);
  share Q0 := Nat.add (Nat.mul ehi p7) (Nat.mul ev q7);
  fin4L n (Nat.pow P0 (nat_lit 2)) (Nat.pow Q0 (nat_lit 2))

set_option exponentiation.threshold 800 in
/-- `F(n)` for `n < 2^18` (plan `L18_t8_P7_c6_E_m0_sg`). -/
def chain18 (n : Nat) : Nat :=
  share m := Nat.div n (nat_lit 1024);
  share tr := Nat.mod (Nat.pow (numeral% (Nat.pow 2 177)) m) (numeral% (Nat.pow 2 354 - Nat.pow 2 177 - 1));
  share tlo := Nat.mod tr (numeral% (Nat.pow 2 177));
  share thi := Nat.div tr (numeral% (Nat.pow 2 177));
  share l0 := Nat.add tlo (Nat.add tlo thi);
  share x0 := Nat.mul thi l0;
  share f1 := x0;
  share l1 := Nat.sub (Nat.add (Nat.pow l0 (nat_lit 2)) (Nat.land (Nat.div n (nat_lit 256)) (nat_lit 4))) (nat_lit 2);
  share f2 := Nat.mul f1 l1;
  share l2 := Nat.sub (Nat.pow l1 (nat_lit 2)) (nat_lit 2);
  share f3 := Nat.mul f2 l2;
  share l3 := Nat.sub (Nat.pow l2 (nat_lit 2)) (nat_lit 2);
  share f4 := Nat.mul f3 l3;
  share l4 := Nat.sub (Nat.pow l3 (nat_lit 2)) (nat_lit 2);
  share f5 := Nat.mul f4 l4;
  share l5 := Nat.sub (Nat.pow l4 (nat_lit 2)) (nat_lit 2);
  share f6 := Nat.mul f5 l5;
  share l6 := Nat.sub (Nat.pow l5 (nat_lit 2)) (nat_lit 2);
  share cq := Nat.div (Nat.add (Nat.mul (nat_lit 5) f6) l6) (nat_lit 2);
  share p7 := Nat.sub (Nat.pow l6 (nat_lit 2)) (nat_lit 2);
  share z7 := Nat.add (Nat.pow cq (nat_lit 2)) (nat_lit 2);
  share q7 := Nat.sub z7 p7;
  share d := Nat.mod (Nat.div n (nat_lit 8)) (nat_lit 128);
  share er := Nat.mod (Nat.pow (numeral% (Nat.pow 2 88)) d) (numeral% (Nat.pow 2 176 - Nat.pow 2 88 - 1));
  share elo := Nat.mod er (numeral% (Nat.pow 2 88));
  share ehi := Nat.div er (numeral% (Nat.pow 2 88));
  share ev := (Nat.add elo ehi);
  share P0 := Nat.add (Nat.mul elo p7) (Nat.mul ehi q7);
  share Q0 := Nat.add (Nat.mul ehi p7) (Nat.mul ev q7);
  sel2a n (Nat.pow P0 (nat_lit 2)) (Nat.pow Q0 (nat_lit 2))

/-- The branch for the bit length of `n` (`≤ 14`, `15 … 18`), `gen` otherwise. One chain serves every
`n < 2^14` (the planner's price: one test fewer on the 14- and 15-bit groups, about 14k each, for one
more cheap doubling on the 13-bit group, about 12k). The tests are `Bool.rec` on `Nat.ble` (a `Bool`
match is cheaper for the kernel than a `Nat.rec` on a numeral), and the branches are closed functions
applied to `n` afterwards (so unfolding `impl` does not rebuild them). -/
def impl (n : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat)
    (fun n => Bool.rec (motive := fun _ => Nat → Nat)
      (fun n => Bool.rec (motive := fun _ => Nat → Nat) gen chain18 (Nat.ble n (nat_lit 262143)) n)
      (fun n => Bool.rec (motive := fun _ => Nat → Nat) chain17 chain16 (Nat.ble n (nat_lit 65535)) n)
      (Nat.ble n (nat_lit 131071)) n)
    (fun n => Bool.rec (motive := fun _ => Nat → Nat) chain15 chain14 (Nat.ble n (nat_lit 16383)) n)
    (Nat.ble n (nat_lit 32767)) n

/-! ## Correctness -/

theorem bit_eq (n k : Nat) : Nat.land (Nat.shiftRight n k) (nat_lit 1) = n / 2 ^ k % 2 := by
  show (n >>> k) &&& 1 = _
  rw [Nat.and_one_is_mod, Nat.shiftRight_eq_div_pow]

theorem lvl_succ (n k a b : Nat) : lvl n (k + 1) a b =
    Nat.rec (motive := fun _ => Nat)
        (lvl n k (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a))
            (Nat.sub (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b))
              (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a))))
        (fun _ _ => lvl n k (Nat.sub (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b))
              (Nat.mul a (Nat.sub (Nat.shiftLeft b (nat_lit 1)) a)))
            (Nat.mul b (Nat.add (Nat.shiftLeft a (nat_lit 1)) b)))
        (Nat.land (Nat.shiftRight n k) (nat_lit 1)) := rfl

theorem dbl_X (m : Nat) :
    Nat.mul (Nat.fib m) (Nat.sub (Nat.shiftLeft (Nat.fib (m + 1)) (nat_lit 1)) (Nat.fib m)) = Nat.fib (2 * m) := by
  show Nat.fib m * ((Nat.fib (m + 1) <<< 1) - Nat.fib m) = _
  rw [Nat.shiftLeft_eq, pow_one, Nat.fib_two_mul, Nat.mul_comm (Nat.fib (m + 1)) 2]

theorem dbl_Z (m : Nat) :
    Nat.mul (Nat.fib (m + 1)) (Nat.add (Nat.shiftLeft (Nat.fib m) (nat_lit 1)) (Nat.fib (m + 1)))
      = Nat.fib (2 * m + 2) := by
  show Nat.fib (m + 1) * ((Nat.fib m <<< 1) + Nat.fib (m + 1)) = _
  rw [Nat.shiftLeft_eq, pow_one, Nat.fib_two_mul_add_two, Nat.mul_comm (Nat.fib m) 2]

theorem dbl_Y (m : Nat) : Nat.sub (Nat.fib (2 * m + 2)) (Nat.fib (2 * m)) = Nat.fib (2 * m + 1) := by
  show Nat.fib (2 * m + 2) - Nat.fib (2 * m) = _
  rw [Nat.fib_add_two]; omega

/-- From `(F(m), F(m+1))`, the low `k` bits of `n` are appended to `m`. -/
theorem lvl_spec (n : Nat) : ∀ k m, lvl n k (Nat.fib m) (Nat.fib (m + 1)) = Nat.fib (m * 2 ^ k + n % 2 ^ k)
  | 0, m => by simp [lvl, Nat.mod_one]
  | k + 1, m => by
    rw [lvl_succ, dbl_X, dbl_Z, dbl_Y, bit_eq]
    have hmod : n % 2 ^ (k + 1) = n % 2 ^ k + 2 ^ k * (n / 2 ^ k % 2) := by
      rw [Nat.mod_pow_succ]
    rcases Nat.mod_two_eq_zero_or_one (n / 2 ^ k) with h | h
    · rw [h]
      show lvl n k (Nat.fib (2 * m)) (Nat.fib (2 * m + 1)) = _
      rw [lvl_spec n k (2 * m), hmod, h, pow_succ]
      congr 1; ring
    · rw [h]
      show lvl n k (Nat.fib (2 * m + 1)) (Nat.fib (2 * m + 1 + 1)) = _
      rw [lvl_spec n k (2 * m + 1), hmod, h, pow_succ]
      congr 1; ring

theorem pick_eq (x z s : Nat) : pick x z s = if x = 0 then z else s := by
  cases x <;> rfl

theorem gen_eq (n : Nat) : gen n = Nat.fib n := by
  unfold gen
  have h := lvl_spec n (Nat.add (Nat.log2 n) (nat_lit 1)) 0
  rw [Nat.fib_zero, Nat.zero_add, Nat.fib_one, Nat.zero_mul, Nat.zero_add] at h
  rw [show (nat_lit 0 : Nat) = 0 from rfl, show (nat_lit 1 : Nat) = 1 from rfl] at *
  rw [h, Nat.mod_eq_of_lt]
  show n < 2 ^ (n.log2 + 1)
  exact Nat.lt_log2_self

/-! ## Correctness of the unrolled doubling -/

theorem two_mul_eq (x : Nat) : Nat.add x x = 2 * x := by show x + x = 2 * x; omega

theorem dbl_X2 (m : Nat) :
    Nat.mul (Nat.fib m) (Nat.sub (Nat.add (Nat.fib (m + 1)) (Nat.fib (m + 1))) (Nat.fib m)) = Nat.fib (2 * m) := by
  rw [two_mul_eq]
  show Nat.fib m * (2 * Nat.fib (m + 1) - Nat.fib m) = _
  rw [Nat.fib_two_mul]

/-- Cassini's identity, in `Nat`: `F(m)² + F(m)F(m+1) + 1 = F(m+1)² + 2 (m mod 2)`. -/
theorem cassini (m : Nat) : Nat.fib m * Nat.fib m + Nat.fib m * Nat.fib (m + 1) + 1
    = Nat.fib (m + 1) * Nat.fib (m + 1) + 2 * (m % 2) := by
  induction m with
  | zero => simp
  | succ k ih =>
    have h2 : Nat.fib (k + 1 + 1) = Nat.fib k + Nat.fib (k + 1) := Nat.fib_add_two
    rw [h2]
    have e1 : (Nat.fib k + Nat.fib (k + 1)) * (Nat.fib k + Nat.fib (k + 1))
        = Nat.fib k * Nat.fib k + 2 * (Nat.fib k * Nat.fib (k + 1)) + Nat.fib (k + 1) * Nat.fib (k + 1) := by
      ring
    have e2 : Nat.fib (k + 1) * (Nat.fib k + Nat.fib (k + 1))
        = Nat.fib k * Nat.fib (k + 1) + Nat.fib (k + 1) * Nat.fib (k + 1) := by ring
    rw [e1, e2]
    omega

/-- The odd last bit with one product: `F(2m+1) = F(m+1)(2F(m+1) − F(m)) + 2 (m mod 2) − 1`. -/
theorem odd_last (m : Nat) :
    Nat.sub (Nat.add (Nat.mul (Nat.fib (m + 1)) (Nat.sub (Nat.add (Nat.fib (m + 1)) (Nat.fib (m + 1)))
      (Nat.fib m))) (Nat.add (m % 2) (m % 2))) 1 = Nat.fib (2 * m + 1) := by
  rw [Nat.fib_two_mul_add_one]
  have hc := cassini m
  have hab : Nat.fib m ≤ Nat.fib (m + 1) := Nat.fib_le_fib_succ
  have hmul : Nat.fib m * Nat.fib (m + 1) ≤ Nat.fib (m + 1) * Nat.fib (m + 1) :=
    Nat.mul_le_mul_right _ hab
  have hP : Nat.fib (m + 1) * (Nat.fib (m + 1) + Nat.fib (m + 1) - Nat.fib m)
      = Nat.fib (m + 1) * Nat.fib (m + 1) + Nat.fib (m + 1) * Nat.fib (m + 1) - Nat.fib m * Nat.fib (m + 1) := by
    rw [Nat.mul_sub, Nat.mul_add, Nat.mul_comm (Nat.fib (m + 1)) (Nat.fib m)]
  show Nat.fib (m + 1) * (Nat.fib (m + 1) + Nat.fib (m + 1) - Nat.fib m) + (m % 2 + m % 2) - 1 = _
  rw [hP, pow_two, pow_two]
  omega

theorem fin_eq (m t0 : Nat) (ht : t0 < 2) :
    fin t0 (m % 2) (Nat.fib m) (Nat.fib (m + 1)) = Nat.fib (2 * m + t0) := by
  unfold fin
  rw [pick_eq]
  rcases (show t0 = 0 ∨ t0 = 1 by omega) with rfl | rfl
  · simp only [if_true]; rw [dbl_X2]; rfl
  · simp only [one_ne_zero, if_false]
    exact odd_last m

/-! ## The modular power -/

/-- `X^(m+1) = q · (X² - X - 1) + (F(m+1) X + F(m))`. -/
theorem pow_fib (X : Nat) (hX : 2 ≤ X) : ∀ m, ∃ q,
    X ^ (m + 1) = q * (X * X - X - 1) + (Nat.fib (m + 1) * X + Nat.fib m)
  | 0 => ⟨0, by simp⟩
  | m + 1 => by
    obtain ⟨q, hq⟩ := pow_fib X hX m
    refine ⟨X * q + Nat.fib (m + 1), ?_⟩
    have hle : X + 1 ≤ X * X := by
      calc X + 1 ≤ X * 2 := by omega
        _ ≤ X * X := Nat.mul_le_mul_left X hX
    have hM : X * X = (X * X - X - 1) + X + 1 := by omega
    have e : Nat.fib (m + 1 + 1) = Nat.fib (m + 1) + Nat.fib m := by rw [Nat.fib_add_two, Nat.add_comm]
    rw [pow_succ, hq, e]
    generalize X * X - X - 1 = M at hM ⊢
    calc (q * M + (Nat.fib (m + 1) * X + Nat.fib m)) * X
        = q * M * X + Nat.fib (m + 1) * (X * X) + Nat.fib m * X := by ring
      _ = q * M * X + Nat.fib (m + 1) * (M + X + 1) + Nat.fib m * X := by rw [hM]
      _ = (X * q + Nat.fib (m + 1)) * M + ((Nat.fib (m + 1) + Nat.fib m) * X + Nat.fib (m + 1)) := by
        ring

/-- With `X = 2^K` and `M = X² − X − 1`: `X^(j+1) mod M = F(j+1) X + F(j)` while
`F(j+1) + 2 ≤ X`, so the low and high halves (`% X`, `/ X`) are `F(j)` and `F(j+1)`. -/
theorem tab_spec (K j : Nat) (hK : 1 ≤ K) (hb : Nat.fib (j + 1) + 2 ≤ 2 ^ K) (k : Nat → Nat → Nat) :
    tab (2 ^ K) (2 ^ (2 * K) - 2 ^ K - 1) j k = k (Nat.fib j) (Nat.fib (j + 1)) := by
  have hX : 2 ≤ 2 ^ K := by
    calc 2 = 2 ^ 1 := rfl
      _ ≤ 2 ^ K := Nat.pow_le_pow_right (by decide) hK
  obtain ⟨q, hq⟩ := pow_fib (2 ^ K) hX j
  have h2K : 2 ^ (2 * K) = 2 ^ K * 2 ^ K := by rw [two_mul, pow_add]
  have hm : Nat.fib j ≤ Nat.fib (j + 1) := Nat.fib_le_fib_succ
  have hlt : Nat.fib (j + 1) * 2 ^ K + Nat.fib j < 2 ^ K * 2 ^ K - 2 ^ K - 1 := by
    have h1 : (Nat.fib (j + 1) + 2) * 2 ^ K ≤ 2 ^ K * 2 ^ K := Nat.mul_le_mul_right _ hb
    have h2 : (Nat.fib (j + 1) + 2) * 2 ^ K = Nat.fib (j + 1) * 2 ^ K + 2 * 2 ^ K := by ring
    generalize Nat.fib (j + 1) * 2 ^ K = a at h2 ⊢
    generalize 2 ^ K * 2 ^ K = P at h1 ⊢
    omega
  have hmod : Nat.mod (Nat.pow (2 ^ K) (Nat.add j 1)) (2 ^ (2 * K) - 2 ^ K - 1)
      = Nat.fib (j + 1) * 2 ^ K + Nat.fib j := by
    show (2 ^ K) ^ (j + 1) % (2 ^ (2 * K) - 2 ^ K - 1) = _
    rw [hq, h2K, Nat.add_comm, Nat.add_mul_mod_self_right, Nat.mod_eq_of_lt hlt]
  have hfm : Nat.fib j < 2 ^ K := by omega
  unfold tab
  rw [hmod]
  congr 1
  · show (Nat.fib (j + 1) * 2 ^ K + Nat.fib j) % 2 ^ K = _
    rw [Nat.add_comm, Nat.add_mul_mod_self_right, Nat.mod_eq_of_lt hfm]
  · show (Nat.fib (j + 1) * 2 ^ K + Nat.fib j) / 2 ^ K = _
    rw [Nat.add_comm, Nat.add_mul_div_right _ _ (Nat.two_pow_pos K),
      Nat.div_eq_of_lt hfm, Nat.zero_add]

/-- The Lucas number `L(j) = 2 F(j+1) − F(j)`. -/
def luc (j : Nat) : Nat := 2 * Nat.fib (j + 1) - Nat.fib j

theorem fib_le_two (j : Nat) : Nat.fib j ≤ 2 * Nat.fib (j + 1) := by
  have := Nat.fib_le_fib_succ (n := j); omega

/-- Lucas doubling for an even index: `L(2j) = L(j)² − 2`. -/
theorem luc_double (j : Nat) (hj : j % 2 = 0) : luc (2 * j) = luc j ^ 2 - 2 := by
  have hc := cassini j
  rw [hj] at hc
  unfold luc
  rw [Nat.fib_two_mul_add_one, Nat.fib_two_mul]
  have hab : Nat.fib j ≤ Nat.fib (j + 1) := Nat.fib_le_fib_succ
  obtain ⟨c, hcb⟩ : ∃ c, Nat.fib (j + 1) = Nat.fib j + c := ⟨_, (Nat.add_sub_cancel' hab).symm⟩
  rw [hcb] at hc ⊢
  generalize Nat.fib j = a at hc ⊢
  have e1 : 2 * (a + c) - a = a + 2 * c := by omega
  rw [e1]
  have e2 : 2 * ((a + c) ^ 2 + a ^ 2) - a * (a + 2 * c) = 3 * (a * a) + 2 * (a * c) + 2 * (c * c) := by
    have : 2 * ((a + c) ^ 2 + a ^ 2) = 3 * (a * a) + 2 * (a * c) + 2 * (c * c) + a * (a + 2 * c) := by ring
    omega
  have e3 : (a + 2 * c) ^ 2 = a * a + 4 * (a * c) + 4 * (c * c) := by ring
  have e4 : a * a + 1 = a * c + c * c := by
    have h5 : (a + c) * (a + c) = a * a + 2 * (a * c) + c * c := by ring
    have h6 : a * (a + c) = a * a + a * c := by ring
    rw [h5, h6] at hc
    omega
  rw [e2, e3]
  omega

theorem lucas_spec : ∀ (n j : Nat) (k : Nat → Nat → Nat), j % 2 = 0 →
    lucas n (Nat.fib j) (luc j) k = k (Nat.fib (j * 2 ^ n)) (luc (j * 2 ^ n))
  | 0, j, k, _ => by
    show k (Nat.fib j) (luc j) = _
    rw [pow_zero, Nat.mul_one]
  | n + 1, j, k, hj => by
    show lucas n (Nat.mul (Nat.fib j) (luc j)) (Nat.sub (Nat.pow (luc j) 2) 2) k = _
    have e1 : Nat.mul (Nat.fib j) (luc j) = Nat.fib (2 * j) := by
      show Nat.fib j * (2 * Nat.fib (j + 1) - Nat.fib j) = _
      rw [Nat.fib_two_mul]
    have e2 : Nat.sub (Nat.pow (luc j) 2) 2 = luc (2 * j) := (luc_double j hj).symm
    rw [e1, e2, lucas_spec n (2 * j) k (by omega)]
    rw [show 2 * j * 2 ^ n = j * 2 ^ (n + 1) by ring]

theorem unL_spec (j : Nat) (k : Nat → Nat → Nat) :
    unL (Nat.fib j) (luc j) k = k (Nat.fib j) (Nat.fib (j + 1)) := by
  unfold unL luc
  congr 1
  show (Nat.fib j + (2 * Nat.fib (j + 1) - Nat.fib j)) / 2 = _
  have := fib_le_two j
  omega

theorem comb_spec (N d : Nat) (k : Nat → Nat → Nat) :
    comb (Nat.fib N) (Nat.fib (N + 1)) (Nat.fib d) (Nat.fib (d + 1)) k
      = k (Nat.fib (N + d)) (Nat.fib (N + d + 1)) := by
  unfold comb
  congr 1
  · show Nat.fib N * (Nat.fib (d + 1) - Nat.fib d) + Nat.fib (N + 1) * Nat.fib d = _
    rcases d with _ | d
    · simp
    · rw [show Nat.fib (d + 1 + 1) - Nat.fib (d + 1) = Nat.fib d by rw [Nat.fib_add_two]; omega,
        show N + (d + 1) = N + d + 1 by omega, Nat.fib_add]
  · show Nat.fib N * Nat.fib d + Nat.fib (N + 1) * Nat.fib (d + 1) = _
    rw [Nat.fib_add]

theorem fib_tab_bound {w Kd d : Nat} (hd : d < 2 ^ w) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    Nat.fib (d + 1) + 2 ≤ 2 ^ Kd :=
  le_trans (Nat.add_le_add_right (Nat.fib_mono (by omega)) 2) hb

/-- `2 F(N + e) = F(N) L(e) + L(N) F(e)`. -/
theorem luc_add (N e : Nat) :
    (Nat.fib N * (Nat.fib (e + 1) + Nat.fib (e + 1) - Nat.fib e) + luc N * Nat.fib e) / 2
      = Nat.fib (N + e) := by
  have hc := comb_spec N e (fun a _ => a)
  unfold comb at hc
  simp only at hc
  have hc' : Nat.fib N * (Nat.fib (e + 1) - Nat.fib e) + Nat.fib (N + 1) * Nat.fib e = Nat.fib (N + e) := hc
  unfold luc
  have h1 : Nat.fib e ≤ Nat.fib (e + 1) := Nat.fib_le_fib_succ
  have h2 : Nat.fib N ≤ Nat.fib (N + 1) := Nat.fib_le_fib_succ
  obtain ⟨c, hcv⟩ : ∃ c, Nat.fib (e + 1) = Nat.fib e + c := ⟨_, (Nat.add_sub_cancel' h1).symm⟩
  obtain ⟨d, hdv⟩ : ∃ d, Nat.fib (N + 1) = Nat.fib N + d := ⟨_, (Nat.add_sub_cancel' h2).symm⟩
  rw [hcv, hdv] at hc' ⊢
  rw [← hc']
  generalize Nat.fib e = u
  generalize Nat.fib N = A
  have e1 : u + c + (u + c) - u = u + 2 * c := by omega
  have e2 : 2 * (A + d) - A = A + 2 * d := by omega
  have e3 : u + c - u = c := by omega
  rw [e1, e2, e3]
  have e4 : A * (u + 2 * c) + (A + 2 * d) * u = 2 * (A * c + (A + d) * u) := by ring
  rw [e4]
  omega

/-! ### Lucas pairs -/

theorem luc_int (j : Nat) : (luc j : ℤ) = 2 * (Nat.fib (j + 1) : ℤ) - Nat.fib j := by
  unfold luc
  rw [Nat.cast_sub (fib_le_two j)]
  push_cast
  ring

theorem cassini_int (m : Nat) : (Nat.fib m : ℤ) * Nat.fib m + Nat.fib m * Nat.fib (m + 1) + 1
    = Nat.fib (m + 1) * Nat.fib (m + 1) + 2 * ((m % 2 : Nat) : ℤ) := by
  exact_mod_cast cassini m

/-- `L(j+2) = L(j+1) + L(j)`. -/
theorem luc_succ_succ (j : Nat) : luc (j + 2) = luc (j + 1) + luc j := by
  apply Nat.cast_injective (R := ℤ)
  push_cast
  rw [luc_int, luc_int, luc_int]
  have h1 : (Nat.fib (j + 2) : ℤ) = Nat.fib j + Nat.fib (j + 1) := by exact_mod_cast Nat.fib_add_two
  have h2 : (Nat.fib (j + 2 + 1) : ℤ) = Nat.fib (j + 1) + Nat.fib (j + 2) := by
    exact_mod_cast (Nat.fib_add_two (n := j + 1))
  rw [show j + 1 + 1 = j + 2 from rfl, h2, h1]
  ring

/-- `L(N + d + 1) = F(d) L(N) + F(d+1) L(N+1)`. -/
theorem luc_add1 (N d : Nat) :
    luc (N + d + 1) = Nat.fib d * luc N + Nat.fib (d + 1) * luc (N + 1) := by
  have h1 : (Nat.fib (N + d + 1) : ℤ) = Nat.fib N * Nat.fib d + Nat.fib (N + 1) * Nat.fib (d + 1) := by
    exact_mod_cast Nat.fib_add N d
  have h2 : (Nat.fib (N + d + 1 + 1) : ℤ)
      = Nat.fib (N + 1) * Nat.fib d + Nat.fib (N + 1 + 1) * Nat.fib (d + 1) := by
    rw [show N + d + 1 + 1 = N + 1 + d + 1 by omega]; exact_mod_cast Nat.fib_add (N + 1) d
  apply Nat.cast_injective (R := ℤ)
  push_cast
  rw [luc_int, luc_int, luc_int, h2, h1]
  ring

/-- Lucas doubling for an even index: `L(2j) + 2 = L(j)²`. -/
theorem luc_sq_even (j : Nat) (hj : j % 2 = 0) : luc (2 * j) + 2 = luc j ^ 2 := by
  apply Nat.cast_injective (R := ℤ)
  push_cast
  rw [luc_int, luc_int]
  have hc := cassini_int j
  rw [hj] at hc
  have e1 : (Nat.fib (2 * j + 1) : ℤ) = Nat.fib (j + 1) ^ 2 + Nat.fib j ^ 2 := by
    exact_mod_cast Nat.fib_two_mul_add_one j
  have e2 : (Nat.fib (2 * j) : ℤ) = Nat.fib j * (2 * Nat.fib (j + 1) - Nat.fib j) := by
    rw [Nat.fib_two_mul, Nat.cast_mul, Nat.cast_sub (fib_le_two j)]; push_cast; ring
  rw [e1, e2]
  push_cast at hc
  generalize (Nat.fib j : ℤ) = a at hc ⊢
  generalize (Nat.fib (j + 1) : ℤ) = b at hc ⊢
  have h0 : a * a + a * b + 1 - b * b = 0 := by rw [hc]; ring
  have key : 2 * (b ^ 2 + a ^ 2) - a * (2 * b - a) + 2 - (2 * b - a) ^ 2
      = 2 * (a * a + a * b + 1 - b * b) := by ring
  rw [h0, mul_zero] at key
  exact sub_eq_zero.mp key

/-- Lucas doubling for an odd index: `L(2j) = L(j)² + 2`. -/
theorem luc_sq_odd (j : Nat) (hj : j % 2 = 1) : luc (2 * j) = luc j ^ 2 + 2 := by
  apply Nat.cast_injective (R := ℤ)
  push_cast
  rw [luc_int, luc_int]
  have hc := cassini_int j
  rw [hj] at hc
  have e1 : (Nat.fib (2 * j + 1) : ℤ) = Nat.fib (j + 1) ^ 2 + Nat.fib j ^ 2 := by
    exact_mod_cast Nat.fib_two_mul_add_one j
  have e2 : (Nat.fib (2 * j) : ℤ) = Nat.fib j * (2 * Nat.fib (j + 1) - Nat.fib j) := by
    rw [Nat.fib_two_mul, Nat.cast_mul, Nat.cast_sub (fib_le_two j)]; push_cast; ring
  rw [e1, e2]
  push_cast at hc
  generalize (Nat.fib j : ℤ) = a at hc ⊢
  generalize (Nat.fib (j + 1) : ℤ) = b at hc ⊢
  have h0 : a * a + a * b + 1 - (b * b + 2) = 0 := by rw [hc]; ring
  have key : 2 * (b ^ 2 + a ^ 2) - a * (2 * b - a) - ((2 * b - a) ^ 2 + 2)
      = 2 * (a * a + a * b + 1 - (b * b + 2)) := by ring
  rw [h0, mul_zero] at key
  exact sub_eq_zero.mp key

/-- `2 L(j+1) − L(j) = 5 F(j)`. -/
theorem five_fib (j : Nat) : 2 * luc (j + 1) - luc j = 5 * Nat.fib j := by
  have h2 : Nat.fib (j + 1 + 1) = Nat.fib j + Nat.fib (j + 1) := Nat.fib_add_two
  have hl := fib_le_two j
  have hl1 := fib_le_two (j + 1)
  unfold luc
  omega

theorem lpair_spec : ∀ (n j : Nat) (k : Nat → Nat → Nat), j % 2 = 0 →
    lpair n (luc j) (luc (j + 1)) k = k (luc (j * 2 ^ n)) (luc (j * 2 ^ n + 1))
  | 0, j, k, _ => by
    show k (luc j) (luc (j + 1)) = _
    rw [pow_zero, Nat.mul_one]
  | n + 1, j, k, hj => by
    show lpair n (Nat.sub (Nat.pow (luc j) 2) 2)
      (Nat.sub (Nat.add (Nat.pow (luc (j + 1)) 2) 2) (Nat.sub (Nat.pow (luc j) 2) 2)) k = _
    have e1 : Nat.sub (Nat.pow (luc j) 2) 2 = luc (2 * j) := by
      have := luc_sq_even j hj
      show luc j ^ 2 - 2 = _
      omega
    have e2 : Nat.add (Nat.pow (luc (j + 1)) 2) 2 = luc (2 * j + 2) := by
      have := luc_sq_odd (j + 1) (by omega)
      show luc (j + 1) ^ 2 + 2 = _
      rw [show 2 * j + 2 = 2 * (j + 1) by ring]
      omega
    have e3 : Nat.sub (luc (2 * j + 2)) (luc (2 * j)) = luc (2 * j + 1) := by
      have := luc_succ_succ (2 * j)
      show luc (2 * j + 2) - luc (2 * j) = _
      omega
    rw [e1, e2, e3, lpair_spec n (2 * j) k (by omega)]
    rw [show 2 * j * 2 ^ n = j * 2 ^ (n + 1) by ring]

theorem combL_spec (N d : Nat) (k : Nat → Nat → Nat) :
    combL (luc N) (luc (N + 1)) (Nat.fib d) (Nat.fib (d + 1)) k
      = k (luc (N + d)) (luc (N + d + 1)) := by
  unfold combL
  congr 1
  · show (Nat.fib (d + 1) - Nat.fib d) * luc N + Nat.fib d * luc (N + 1) = _
    rcases d with _ | d
    · simp
    · rw [show Nat.fib (d + 1 + 1) - Nat.fib (d + 1) = Nat.fib d by rw [Nat.fib_add_two]; omega,
        show N + (d + 1) = N + d + 1 by omega, luc_add1]
  · show Nat.fib d * luc N + Nat.fib (d + 1) * luc (N + 1) = _
    rw [luc_add1]

/-! ### Switching form part way (v8, Oct 18)

The planner (`fibvar/planner.py`) cuts the computation at its thin waists and prices every cut in the
kernel. Two changes win: the top table may cover `t` bits with its own width `Kt` (7 bits beats 8 on
most sizes: its single division shrinks about eight-fold), and the doublings may switch form part way —
`(F, L)` levels while the numbers are small (one product and one square, three operations), then the
Lucas pair `(L, L')` for the last levels, where two squares beat a product and a square. The switch
costs one conversion `L(j+1) = (5 F(j) + L(j)) / 2` (`conv`). -/

/-- `(F(j), L(j)) ↦ (L(j), L(j+1))`, `L(j+1) = (5 F(j) + L(j)) / 2`. -/
def conv (f l : Nat) (k : Nat → Nat → Nat) : Nat := k l (Nat.div (Nat.add (Nat.mul 5 f) l) 2)

theorem conv_spec (j : Nat) (k : Nat → Nat → Nat) :
    conv (Nat.fib j) (luc j) k = k (luc j) (luc (j + 1)) := by
  unfold conv
  congr 1
  show (5 * Nat.fib j + luc j) / 2 = luc (j + 1)
  have h2 : Nat.fib (j + 1 + 1) = Nat.fib j + Nat.fib (j + 1) := Nat.fib_add_two
  have hl := fib_le_two j
  have hl1 := fib_le_two (j + 1)
  unfold luc
  omega

/-- The index reached by `c` doublings in one form and `w − c` in the other: `m · 2^w`. -/
theorem idx_eq (m c w : Nat) (hc : 1 ≤ c) (hcw : c ≤ w) :
    2 * m * 2 ^ (c - 1) * 2 ^ (w - c) = m * 2 ^ w := by
  have e : 2 * m * 2 ^ (c - 1) * 2 ^ (w - c) = m * (2 * 2 ^ (c - 1) * 2 ^ (w - c)) := by ring
  rw [e, ← pow_succ', ← pow_add, show c - 1 + 1 + (w - c) = w by omega]

theorem even_idx (m c : Nat) : 2 * m * 2 ^ (c - 1) % 2 = 0 := by
  rw [Nat.mul_assoc]; exact Nat.mul_mod_right 2 _

/-! ## v9 blocks (Oct 24)

Exponent-`m` tables (`tab0`), the first doubling straight from the table (`sgc`), the joins for those
tables (`combL0`, `comb0`, `luc_add0`), the four-way end (`fin4L`, `fin4Lc0`, `fin4Lc1`) with the
branched selected doubling `sel2a`, and the structured chains `chainC0`, `chainA0`, `chainE2`, `chainE3`
with their specs. Bits are read with `Nat.land` (`land_two_pow`). -/

theorem land_two_pow (x k : Nat) : Nat.land x (2 ^ k) = 2 ^ k * (x / 2 ^ k % 2) := by
  show x &&& 2 ^ k = _
  apply Nat.eq_of_testBit_eq; intro i
  rw [Nat.testBit_and, Nat.testBit_two_pow]
  rcases Nat.mod_two_eq_zero_or_one (x / 2 ^ k) with h | h
  · rw [h, Nat.mul_zero, Nat.zero_testBit]
    by_cases hki : k = i
    · subst hki; rw [Nat.testBit_eq_decide_div_mod_eq, h]; simp
    · simp [hki]
  · rw [h, Nat.mul_one, Nat.testBit_two_pow]
    by_cases hki : k = i
    · subst hki; rw [Nat.testBit_eq_decide_div_mod_eq, h]; simp
    · simp [hki]

theorem land1 (x : Nat) : Nat.land x 1 = x % 2 := by
  have h := land_two_pow x 0
  rw [pow_zero, Nat.div_one, Nat.one_mul] at h
  exact h
theorem land2 (x : Nat) : Nat.land x 2 = 2 * (x / 2 % 2) := land_two_pow x 1
theorem land4 (x : Nat) : Nat.land x 4 = 4 * (x / 4 % 2) := land_two_pow x 2

/-- Table from the power `X^j` (exponent `j`): low half `F(j+1) − F(j)`, high half `F(j)`. -/
def tab0 (X M j : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.mod (Nat.mod (Nat.pow X j) M) X) (Nat.div (Nat.mod (Nat.pow X j) M) X)

theorem tab0_spec (K j : Nat) (hK : 2 ≤ K) (hb : Nat.fib (j + 1) + 2 ≤ 2 ^ K) (k : Nat → Nat → Nat) :
    tab0 (2 ^ K) (2 ^ (2 * K) - 2 ^ K - 1) j k = k (Nat.fib (j + 1) - Nat.fib j) (Nat.fib j) := by
  rcases j with _ | j
  · have hX : 4 ≤ 2 ^ K := by
      calc 4 = 2 ^ 2 := rfl
        _ ≤ 2 ^ K := Nat.pow_le_pow_right (by decide) hK
    have h2K : 2 ^ (2 * K) = 2 ^ K * 2 ^ K := by rw [two_mul, pow_add]
    have hM : 1 < 2 ^ (2 * K) - 2 ^ K - 1 := by
      rw [h2K]
      have : 2 ^ K * 4 ≤ 2 ^ K * 2 ^ K := Nat.mul_le_mul_left _ hX
      omega
    unfold tab0
    show k ((2 ^ K) ^ 0 % (2 ^ (2 * K) - 2 ^ K - 1) % 2 ^ K)
      ((2 ^ K) ^ 0 % (2 ^ (2 * K) - 2 ^ K - 1) / 2 ^ K) = _
    rw [pow_zero, Nat.mod_eq_of_lt hM, Nat.mod_eq_of_lt (by omega : 1 < 2 ^ K),
      Nat.div_eq_of_lt (by omega : 1 < 2 ^ K)]
    simp
  · have h := tab_spec K j (by omega) (le_trans (Nat.add_le_add_right (Nat.fib_mono (by omega)) 2) hb) k
    unfold tab at h
    unfold tab0
    rw [show Nat.add j 1 = j + 1 from rfl] at h
    rw [h]
    congr 1
    rw [Nat.fib_add_two]; omega

/-- `5 F(2j+1) = L(j)² + L(j+1)²`. -/
theorem five_fib_odd (j : Nat) : 5 * Nat.fib (2 * j + 1) = luc j ^ 2 + luc (j + 1) ^ 2 := by
  apply Nat.cast_injective (R := ℤ)
  push_cast
  rw [luc_int, luc_int]
  have e1 : (Nat.fib (2 * j + 1) : ℤ) = Nat.fib (j + 1) ^ 2 + Nat.fib j ^ 2 := by
    exact_mod_cast Nat.fib_two_mul_add_one j
  have e2 : (Nat.fib (j + 1 + 1) : ℤ) = Nat.fib j + Nat.fib (j + 1) := by exact_mod_cast Nat.fib_add_two
  rw [e1, e2]; ring

theorem brec3_eq {α : Sort _} (x y : Nat → Nat → Nat → α) (c : Bool) (n a b : Nat) :
    Bool.rec (motive := fun _ => Nat → Nat → Nat → α) x y c n a b = if c = true then y n a b else x n a b := by
  cases c <;> rfl

theorem beq0 (x : Nat) : (Nat.beq x 0 = true) = (x = 0) := by
  simp [Nat.beq_eq]

/-- `F(2h) = F(h) L(h)`. -/
theorem fib_even_luc (h : Nat) : Nat.fib (2 * h) = Nat.fib h * luc h := by
  rw [Nat.fib_two_mul]; rfl

/-- `F(2h+1) + 2 (h mod 2) = F(h) L(h+1) + 1`. -/
theorem fib_odd_luc (h : Nat) : Nat.fib (2 * h + 1) + 2 * (h % 2) = Nat.fib h * luc (h + 1) + 1 := by
  have hc := cassini h
  have h2 : Nat.fib (h + 1 + 1) = Nat.fib h + Nat.fib (h + 1) := Nat.fib_add_two
  have hl : luc (h + 1) = 2 * Nat.fib h + Nat.fib (h + 1) := by
    unfold luc; rw [h2]; omega
  rw [hl, Nat.fib_two_mul_add_one]
  have e1 : Nat.fib h * (2 * Nat.fib h + Nat.fib (h + 1))
      = 2 * (Nat.fib h * Nat.fib h) + Nat.fib h * Nat.fib (h + 1) := by ring
  have e2 : Nat.fib (h + 1) ^ 2 + Nat.fib h ^ 2
      = Nat.fib (h + 1) * Nat.fib (h + 1) + Nat.fib h * Nat.fib h := by ring
  rw [e1, e2]
  omega

/-- The three Lucas numbers at the doubled index from the squares `a = L(j)²`, `b = L(j+1)²`, with
`c4 = 4 (j mod 2)`. -/
theorem abc_luc (j c4 : Nat) (hc : c4 = 4 * (j % 2)) :
    luc j ^ 2 + c4 - 2 = luc (2 * j) ∧ 2 + luc (j + 1) ^ 2 - c4 = luc (2 * j + 2) ∧
    4 + luc (j + 1) ^ 2 - (luc j ^ 2 + (c4 + c4)) = luc (2 * j + 1) := by
  have hrec := luc_succ_succ (2 * j)
  rcases Nat.mod_two_eq_zero_or_one j with h | h
  · have e0 := luc_sq_even j h
    have e2 := luc_sq_odd (j + 1) (by omega)
    rw [show 2 * (j + 1) = 2 * j + 2 by ring] at e2
    rw [h] at hc; subst hc
    refine ⟨by omega, by omega, by omega⟩
  · have e0 := luc_sq_odd j h
    have e2 := luc_sq_even (j + 1) (by omega)
    rw [show 2 * (j + 1) = 2 * j + 2 by ring] at e2
    rw [h] at hc; subst hc
    refine ⟨by omega, by omega, by omega⟩

theorem five_fib_even (j : Nat) : (luc (2 * j + 1) + luc (2 * j + 1) - luc (2 * j)) / 5 = Nat.fib (2 * j) := by
  have := five_fib (2 * j); omega

theorem five_fib_odd' (j : Nat) : (luc j ^ 2 + luc (j + 1) ^ 2) / 5 = Nat.fib (2 * j + 1) := by
  have := five_fib_odd j; omega

/-- The four-way end from the squares at `j = n / 4`, given the three Lucas numbers `A, B, C` at `2j`. -/
theorem fin4_core (n : Nat) (A B C F0 F1 : Nat) (hA : A = luc (2 * (n / 4))) (hB : B = luc (2 * (n / 4) + 1))
    (hC : C = luc (2 * (n / 4) + 2)) (hF0 : F0 = Nat.fib (2 * (n / 4))) (hF1 : F1 = Nat.fib (2 * (n / 4) + 1)) :
    (n % 4 = 0 → F0 * A = Nat.fib n) ∧ (n % 4 = 1 → 1 + F0 * B = Nat.fib n) ∧
    (n % 4 = 2 → F1 * B = Nat.fib n) ∧ (n % 4 = 3 → F1 * C - 1 = Nat.fib n) := by
  subst hA hB hC hF0 hF1
  set j := n / 4 with hj
  have hn : n = 4 * j + n % 4 := by omega
  refine ⟨fun h => ?_, fun h => ?_, fun h => ?_, fun h => ?_⟩
  · rw [hn, h, show 4 * j + 0 = 2 * (2 * j) by ring]; exact (fib_even_luc (2 * j)).symm
  · have := fib_odd_luc (2 * j)
    rw [show 2 * j % 2 = 0 by omega] at this
    rw [hn, h, show 4 * j + 1 = 2 * (2 * j) + 1 by ring]; omega
  · rw [hn, h, show 4 * j + 2 = 2 * (2 * j + 1) by ring]; exact (fib_even_luc (2 * j + 1)).symm
  · have := fib_odd_luc (2 * j + 1)
    rw [show (2 * j + 1) % 2 = 1 by omega, show 2 * j + 1 + 1 = 2 * j + 2 by ring] at this
    rw [hn, h, show 4 * j + 3 = 2 * (2 * j + 1) + 1 by ring]; omega

theorem bits4 (n : Nat) :
    (Nat.land n 2 = 0 ↔ n / 2 % 2 = 0) ∧ (Nat.land n 1 = 0 ↔ n % 2 = 0) := by
  rw [land2, land1]; omega

theorem fin4L_spec (n : Nat) :
    fin4L n (luc (n / 4) ^ 2) (luc (n / 4 + 1) ^ 2) = Nat.fib n := by
  obtain ⟨hA, hC, hB⟩ := abc_luc (n / 4) (Nat.land n 4) (by rw [land4])
  have hcore := fin4_core n _ _ _ _ _ rfl rfl rfl (five_fib_even (n / 4)) (five_fib_odd' (n / 4))
  have hb := bits4 n
  unfold fin4L
  simp only [brec3_eq, beq0]
  have h4 : n % 4 = 2 * (n / 2 % 2) + n % 2 := by omega
  split_ifs with h2 h1 h1
  · show (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4))
        + (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4)))
        - (luc (n / 4) ^ 2 + Nat.land n 4 - 2)) / 5 * (luc (n / 4) ^ 2 + Nat.land n 4 - 2) = _
    rw [hB, hA]; exact hcore.1 (by omega)
  · show 1 + (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4))
        + (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4)))
        - (luc (n / 4) ^ 2 + Nat.land n 4 - 2)) / 5 * (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4))) = _
    rw [hB, hA]; exact hcore.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5
        * (4 + luc (n / 4 + 1) ^ 2 - (luc (n / 4) ^ 2 + (Nat.land n 4 + Nat.land n 4))) = _
    rw [hB]; exact hcore.2.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5 * (2 + luc (n / 4 + 1) ^ 2 - Nat.land n 4) - 1 = _
    rw [hC]; exact hcore.2.2.2 (by omega)

theorem abc_luc0 (j : Nat) (hj : j % 2 = 0) :
    luc j ^ 2 - 2 = luc (2 * j) ∧ 2 + luc (j + 1) ^ 2 = luc (2 * j + 2) ∧
    4 + luc (j + 1) ^ 2 - luc j ^ 2 = luc (2 * j + 1) := by
  obtain ⟨h1, h2, h3⟩ := abc_luc j 0 (by rw [hj])
  refine ⟨by simpa using h1, by simpa using h2, by simpa using h3⟩

theorem abc_luc1 (j : Nat) (hj : j % 2 = 1) :
    2 + luc j ^ 2 = luc (2 * j) ∧ luc (j + 1) ^ 2 - 2 = luc (2 * j + 2) ∧
    luc (j + 1) ^ 2 - (4 + luc j ^ 2) = luc (2 * j + 1) := by
  obtain ⟨h1, h2, h3⟩ := abc_luc j 4 (by rw [hj])
  refine ⟨by omega, by omega, by omega⟩

theorem fin4Lc0_spec (n : Nat) (hc : n / 4 % 2 = 0) :
    fin4Lc0 n (luc (n / 4) ^ 2) (luc (n / 4 + 1) ^ 2) = Nat.fib n := by
  obtain ⟨hA, hC, hB⟩ := abc_luc0 (n / 4) hc
  have hcore := fin4_core n _ _ _ _ _ rfl rfl rfl (five_fib_even (n / 4)) (five_fib_odd' (n / 4))
  have hb := bits4 n
  have h4 : n % 4 = 2 * (n / 2 % 2) + n % 2 := by omega
  unfold fin4Lc0
  simp only [brec3_eq, beq0]
  split_ifs with h2 h1 h1
  · show (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2 + (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2)
        - (luc (n / 4) ^ 2 - 2)) / 5 * (luc (n / 4) ^ 2 - 2) = _
    rw [hB, hA]; exact hcore.1 (by omega)
  · show 1 + (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2 + (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2)
        - (luc (n / 4) ^ 2 - 2)) / 5 * (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2) = _
    rw [hB, hA]; exact hcore.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5 * (4 + luc (n / 4 + 1) ^ 2 - luc (n / 4) ^ 2) = _
    rw [hB]; exact hcore.2.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5 * (2 + luc (n / 4 + 1) ^ 2) - 1 = _
    rw [hC]; exact hcore.2.2.2 (by omega)

theorem fin4Lc1_spec (n : Nat) (hc : n / 4 % 2 = 1) :
    fin4Lc1 n (luc (n / 4) ^ 2) (luc (n / 4 + 1) ^ 2) = Nat.fib n := by
  obtain ⟨hA, hC, hB⟩ := abc_luc1 (n / 4) hc
  have hcore := fin4_core n _ _ _ _ _ rfl rfl rfl (five_fib_even (n / 4)) (five_fib_odd' (n / 4))
  have hb := bits4 n
  have h4 : n % 4 = 2 * (n / 2 % 2) + n % 2 := by omega
  unfold fin4Lc1
  simp only [brec3_eq, beq0]
  split_ifs with h2 h1 h1
  · show (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2) + (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2))
        - (2 + luc (n / 4) ^ 2)) / 5 * (2 + luc (n / 4) ^ 2) = _
    rw [hB, hA]; exact hcore.1 (by omega)
  · show 1 + (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2) + (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2))
        - (2 + luc (n / 4) ^ 2)) / 5 * (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2)) = _
    rw [hB, hA]; exact hcore.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5 * (luc (n / 4 + 1) ^ 2 - (4 + luc (n / 4) ^ 2)) = _
    rw [hB]; exact hcore.2.2.1 (by omega)
  · show (luc (n / 4) ^ 2 + luc (n / 4 + 1) ^ 2) / 5 * (luc (n / 4 + 1) ^ 2 - 2) - 1 = _
    rw [hC]; exact hcore.2.2.2 (by omega)

theorem land8 (x : Nat) : Nat.land x 8 = 8 * (x / 8 % 2) := land_two_pow x 3

theorem sel2a_spec (n : Nat) :
    sel2a n (luc (n / 8) ^ 2) (luc (n / 8 + 1) ^ 2) = Nat.fib n := by
  have hc4 : Nat.land n 8 / 2 = 4 * (n / 8 % 2) := by rw [land8]; omega
  obtain ⟨hA, hC, hB⟩ := abc_luc (n / 8) (Nat.land n 8 / 2) hc4
  have hl4 := land4 n
  unfold sel2a
  simp only [brec3_eq, beq0]
  split_ifs with h2
  · -- bit 2 = 0: pair (L(2i), L(2i+1)) = (L(n/4), L(n/4+1)), parity 0
    have e : 2 * (n / 8) = n / 4 := by omega
    have hc : n / 4 % 2 = 0 := by omega
    show fin4Lc0 n ((luc (n / 8) ^ 2 + Nat.land n 8 / 2 - 2) ^ 2)
      ((4 + luc (n / 8 + 1) ^ 2 - (luc (n / 8) ^ 2 + (Nat.land n 8 / 2 + Nat.land n 8 / 2))) ^ 2) = _
    rw [hA, hB, e]; exact fin4Lc0_spec n hc
  · have e : 2 * (n / 8) + 1 = n / 4 := by omega
    have hc : n / 4 % 2 = 1 := by omega
    show fin4Lc1 n ((4 + luc (n / 8 + 1) ^ 2 - (luc (n / 8) ^ 2 + (Nat.land n 8 / 2 + Nat.land n 8 / 2))) ^ 2)
      ((2 + luc (n / 8 + 1) ^ 2 - Nat.land n 8 / 2) ^ 2) = _
    rw [hB, hC, show 2 * (n / 8) + 2 = n / 4 + 1 by omega, e]; exact fin4Lc1_spec n hc

/-- From the exponent-`m` table `(lo, hi) = (F(m+1) − F(m), F(m))`: `L(m) = lo + (lo + hi)`,
`F(2m) = F(m) L(m)`, `L(2m) = L(m)² + 4 (m mod 2) − 2`. -/
def sgc (lo hi c4 : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.mul hi (Nat.add lo (Nat.add lo hi))) (Nat.sub (Nat.add (Nat.pow (Nat.add lo (Nat.add lo hi)) 2) c4) 2)

theorem luc_lohi (m : Nat) : Nat.fib (m + 1) - Nat.fib m + (Nat.fib (m + 1) - Nat.fib m + Nat.fib m) = luc m := by
  have := Nat.fib_le_fib_succ (n := m)
  unfold luc; omega

theorem sgc_spec (m c4 : Nat) (hc : c4 = 4 * (m % 2)) (k : Nat → Nat → Nat) :
    sgc (Nat.fib (m + 1) - Nat.fib m) (Nat.fib m) c4 k = k (Nat.fib (2 * m)) (luc (2 * m)) := by
  unfold sgc
  have hl := luc_lohi m
  congr 1
  · show Nat.fib m * (Nat.fib (m + 1) - Nat.fib m + (Nat.fib (m + 1) - Nat.fib m + Nat.fib m)) = _
    rw [hl, fib_even_luc]
  · show (Nat.fib (m + 1) - Nat.fib m + (Nat.fib (m + 1) - Nat.fib m + Nat.fib m)) ^ 2 + c4 - 2 = _
    rw [hl, hc]
    rcases Nat.mod_two_eq_zero_or_one m with h | h
    · have := luc_sq_even m h; rw [h]; omega
    · have := luc_sq_odd m h; rw [h]; omega

/-- `combL` with the exponent-`d` table `(lo, hi) = (F(d+1) − F(d), F(d))`. -/
def combL0 (p q lo hi : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.add (Nat.mul lo p) (Nat.mul hi q)) (Nat.add (Nat.mul hi p) (Nat.mul (Nat.add lo hi) q))

theorem combL0_spec (N d : Nat) (k : Nat → Nat → Nat) :
    combL0 (luc N) (luc (N + 1)) (Nat.fib (d + 1) - Nat.fib d) (Nat.fib d) k
      = k (luc (N + d)) (luc (N + d + 1)) := by
  have h := combL_spec N d k
  unfold combL at h
  unfold combL0
  have e : Nat.fib (d + 1) - Nat.fib d + Nat.fib d = Nat.fib (d + 1) := by
    have := Nat.fib_le_fib_succ (n := d); omega
  rw [show Nat.add (Nat.fib (d + 1) - Nat.fib d) (Nat.fib d) = Nat.fib (d + 1) from e]
  exact h

/-- `2 F(N + e) = F(N) L(e) + L(N) F(e)` with `L(e) = lo + (lo + hi)` from the exponent-`e` table. -/
theorem luc_add0 (N e : Nat) :
    (Nat.fib N * (Nat.fib (e + 1) - Nat.fib e + (Nat.fib (e + 1) - Nat.fib e + Nat.fib e))
      + luc N * Nat.fib e) / 2 = Nat.fib (N + e) := by
  have h := luc_add N e
  have e1 : Nat.fib (e + 1) - Nat.fib e + (Nat.fib (e + 1) - Nat.fib e + Nat.fib e)
      = Nat.fib (e + 1) + Nat.fib (e + 1) - Nat.fib e := by
    have := Nat.fib_le_fib_succ (n := e); omega
  rw [e1]; exact h

/-- The `A` join with the exponent-`d` table. -/
def comb0 (A B lo hi : Nat) (k : Nat → Nat → Nat) : Nat :=
  k (Nat.add (Nat.mul A lo) (Nat.mul B hi)) (Nat.add (Nat.mul A hi) (Nat.mul B (Nat.add lo hi)))

theorem comb0_spec (N d : Nat) (k : Nat → Nat → Nat) :
    comb0 (Nat.fib N) (Nat.fib (N + 1)) (Nat.fib (d + 1) - Nat.fib d) (Nat.fib d) k
      = k (Nat.fib (N + d)) (Nat.fib (N + d + 1)) := by
  have h := comb_spec N d k
  unfold comb at h
  unfold comb0
  have e : Nat.fib (d + 1) - Nat.fib d + Nat.fib d = Nat.fib (d + 1) := by
    have := Nat.fib_le_fib_succ (n := d); omega
  rw [show Nat.add (Nat.fib (d + 1) - Nat.fib d) (Nat.fib d) = Nat.fib (d + 1) from e]
  exact h

/-- E chain, two last bits: exponent tables, the `sg` first doubling, `c` `(F, L)` doublings, the
conversion, `w − c` Lucas-pair doublings, the low table at `n / 4`, then the four-way end. -/
def chainE2 (n s w c X M Xd Md : Nat) : Nat :=
  tab0 X M (Nat.div n (Nat.pow 2 s)) fun lo hi =>
  sgc lo hi (Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4) fun f l =>
  lucas (Nat.sub c 1) f l fun f l =>
  conv f l fun p q =>
  lpair (Nat.sub w c) p q fun p q =>
  tab0 Xd Md (Nat.mod (Nat.div n 4) (Nat.pow 2 w)) fun lo hi =>
  combL0 p q lo hi fun P Q =>
  fin4L n (Nat.pow P 2) (Nat.pow Q 2)

/-- E chain, three last bits (the branched selection `sel2a`). -/
def chainE3 (n s w c X M Xd Md : Nat) : Nat :=
  tab0 X M (Nat.div n (Nat.pow 2 s)) fun lo hi =>
  sgc lo hi (Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4) fun f l =>
  lucas (Nat.sub c 1) f l fun f l =>
  conv f l fun p q =>
  lpair (Nat.sub w c) p q fun p q =>
  tab0 Xd Md (Nat.mod (Nat.div n 8) (Nat.pow 2 w)) fun lo hi =>
  combL0 p q lo hi fun P Q =>
  sel2a n (Nat.pow P 2) (Nat.pow Q 2)

theorem c4_eq (n s : Nat) (hs : 2 ≤ s) :
    Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4 = 4 * (n / 2 ^ s % 2) := by
  show Nat.land (n / 2 ^ (s - 2)) 4 = _
  rw [land4, Nat.div_div_eq_div_mul, show 2 ^ (s - 2) * 4 = 2 ^ s by
    rw [show (4 : Nat) = 2 ^ 2 by rfl, ← pow_add, show s - 2 + 2 = s by omega]]

theorem tab_bound_of {t K m : Nat} (hm : m < 2 ^ t) (hb : Nat.fib (2 ^ t) + 2 ≤ 2 ^ K) :
    Nat.fib (m + 1) + 2 ≤ 2 ^ K := fib_tab_bound hm hb

theorem chainE2_spec (n s w c t Kt Kd : Nat) (hs : s = w + 2) (hc : 1 ≤ c) (hcw : c ≤ w)
    (h : n < 2 ^ s * 2 ^ t) (hKt : 2 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 2 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainE2 n s w c (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 4 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainE2
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab0_spec Kt _ hKt (tab_bound_of hm hbt)]
  try dsimp only
  rw [sgc_spec _ _ (c4_eq n s (by omega))]
  try dsimp only
  rw [show Nat.sub c 1 = c - 1 from rfl, lucas_spec (c - 1) _ _ (by omega)]
  try dsimp only
  rw [conv_spec]
  try dsimp only
  rw [show Nat.sub w c = w - c from rfl, lpair_spec (w - c) _ _ (even_idx _ _)]
  try dsimp only
  rw [show Nat.mod (Nat.div n 4) (Nat.pow 2 w) = n / 4 % 2 ^ w from rfl,
    tab0_spec Kd _ hKd (tab_bound_of hd hb)]
  try dsimp only
  rw [combL0_spec]
  have hN : 2 * (n / 2 ^ s) * 2 ^ (c - 1) * 2 ^ (w - c) + n / 4 % 2 ^ w = n / 4 := by
    rw [idx_eq _ _ _ hc hcw, hs, pow_add, show (2 : Nat) ^ 2 = 4 by rfl, Nat.mul_comm (2 ^ w) 4,
      ← Nat.div_div_eq_div_mul, Nat.div_add_mod']
  rw [hN]
  exact fin4L_spec n

theorem chainE3_spec (n s w c t Kt Kd : Nat) (hs : s = w + 3) (hc : 1 ≤ c) (hcw : c ≤ w)
    (h : n < 2 ^ s * 2 ^ t) (hKt : 2 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 2 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainE3 n s w c (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 8 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainE3
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab0_spec Kt _ hKt (tab_bound_of hm hbt)]
  try dsimp only
  rw [sgc_spec _ _ (c4_eq n s (by omega))]
  try dsimp only
  rw [show Nat.sub c 1 = c - 1 from rfl, lucas_spec (c - 1) _ _ (by omega)]
  try dsimp only
  rw [conv_spec]
  try dsimp only
  rw [show Nat.sub w c = w - c from rfl, lpair_spec (w - c) _ _ (even_idx _ _)]
  try dsimp only
  rw [show Nat.mod (Nat.div n 8) (Nat.pow 2 w) = n / 8 % 2 ^ w from rfl,
    tab0_spec Kd _ hKd (tab_bound_of hd hb)]
  try dsimp only
  rw [combL0_spec]
  have hN : 2 * (n / 2 ^ s) * 2 ^ (c - 1) * 2 ^ (w - c) + n / 8 % 2 ^ w = n / 8 := by
    rw [idx_eq _ _ _ hc hcw, hs, pow_add, show (2 : Nat) ^ 3 = 8 by rfl, Nat.mul_comm (2 ^ w) 8,
      ← Nat.div_div_eq_div_mul, Nat.div_add_mod']
  rw [hN]
  exact sel2a_spec n

/-- C chain with the exponent tables and the `sg` first doubling. -/
def chainC0 (n s X M Xe Me : Nat) : Nat :=
  tab0 X M (Nat.div n (Nat.pow 2 s)) fun lo hi =>
  sgc lo hi (Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4) fun f l =>
  lucas (Nat.sub s 1) f l fun f l =>
  tab0 Xe Me (Nat.mod n (Nat.pow 2 s)) fun lo hi =>
  Nat.div (Nat.add (Nat.mul f (Nat.add lo (Nat.add lo hi))) (Nat.mul l hi)) 2

theorem chainC0_spec (n s t Kt Ke : Nat) (hs : 2 ≤ s) (h : n < 2 ^ s * 2 ^ t)
    (hKt : 2 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKe : 2 ≤ Ke) (hb : Nat.fib (2 ^ s) + 2 ≤ 2 ^ Ke) :
    chainC0 n s (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Ke) (2 ^ (2 * Ke) - 2 ^ Ke - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have he : n % 2 ^ s < 2 ^ s := Nat.mod_lt _ (Nat.two_pow_pos s)
  unfold chainC0
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab0_spec Kt _ hKt (tab_bound_of hm hbt)]
  try dsimp only
  rw [sgc_spec _ _ (c4_eq n s hs)]
  try dsimp only
  rw [show Nat.sub s 1 = s - 1 from rfl, lucas_spec (s - 1) _ _ (by omega)]
  try dsimp only
  rw [show Nat.mod n (Nat.pow 2 s) = n % 2 ^ s from rfl, tab0_spec Ke _ hKe (tab_bound_of he hb)]
  try dsimp only
  show (Nat.fib (2 * (n / 2 ^ s) * 2 ^ (s - 1)) * (Nat.fib (n % 2 ^ s + 1) - Nat.fib (n % 2 ^ s)
      + (Nat.fib (n % 2 ^ s + 1) - Nat.fib (n % 2 ^ s) + Nat.fib (n % 2 ^ s)))
      + luc (2 * (n / 2 ^ s) * 2 ^ (s - 1)) * Nat.fib (n % 2 ^ s)) / 2 = _
  rw [luc_add0]
  congr 1
  have e1 : 2 * (n / 2 ^ s) * 2 ^ (s - 1) = n / 2 ^ s * 2 ^ s := by
    rw [show 2 * (n / 2 ^ s) * 2 ^ (s - 1) = n / 2 ^ s * (2 * 2 ^ (s - 1)) by ring, ← pow_succ',
      Nat.sub_add_cancel (by omega : 1 ≤ s)]
  rw [e1, Nat.div_add_mod']

/-- A chain (one last bit, the Fibonacci-pair join at `n / 2`) with the exponent tables, the `sg`
first doubling and v8's `pick` last bit. -/
def chainA0 (n s w X M Xd Md : Nat) : Nat :=
  tab0 X M (Nat.div n (Nat.pow 2 s)) fun lo hi =>
  sgc lo hi (Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4) fun f l =>
  lucas (Nat.sub w 1) f l fun f l =>
  unL f l fun A B =>
  tab0 Xd Md (Nat.mod (Nat.div n 2) (Nat.pow 2 w)) fun lo hi =>
  comb0 A B lo hi fun P Q =>
  fin (Nat.mod n 2) (Nat.mod (Nat.div n 2) 2) P Q

theorem chainA0_spec (n s w t Kt Kd : Nat) (hs : s = w + 1) (hw : 1 ≤ w) (h : n < 2 ^ s * 2 ^ t)
    (hKt : 2 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 2 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainA0 n s w (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 2 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainA0
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab0_spec Kt _ hKt (tab_bound_of hm hbt)]
  try dsimp only
  rw [sgc_spec _ _ (c4_eq n s (by omega))]
  try dsimp only
  rw [show Nat.sub w 1 = w - 1 from rfl, lucas_spec (w - 1) _ _ (by omega)]
  try dsimp only
  rw [unL_spec, show Nat.mod (Nat.div n 2) (Nat.pow 2 w) = n / 2 % 2 ^ w from rfl,
    tab0_spec Kd _ hKd (tab_bound_of hd hb)]
  try dsimp only
  rw [comb0_spec]
  have hN : 2 * (n / 2 ^ s) * 2 ^ (w - 1) + n / 2 % 2 ^ w = n / 2 := by
    have e1 : 2 * (n / 2 ^ s) * 2 ^ (w - 1) = n / 2 / 2 ^ w * 2 ^ w := by
      rw [hs, pow_succ, Nat.mul_comm (2 ^ w) 2, ← Nat.div_div_eq_div_mul,
        show 2 * (n / 2 / 2 ^ w) * 2 ^ (w - 1) = n / 2 / 2 ^ w * (2 * 2 ^ (w - 1)) by ring,
        ← pow_succ', Nat.sub_add_cancel hw]
    rw [e1, Nat.div_add_mod']
  rw [hN, show Nat.mod (Nat.div n 2) 2 = n / 2 % 2 from rfl, show Nat.mod n 2 = n % 2 from rfl,
    fin_eq _ _ (Nat.mod_lt _ (by decide))]
  congr 1
  omega

/- `chain14_eq : ∀ n, chain14 n = chainC0 n 7 (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1)` by `rfl`, checked directly by the
kernel (the elaborator's unifier is slow on the unrolled graph). -/
set_option exponentiation.threshold 800 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← elabTerm (← `(∀ n, chain14 n = chainC0 n 7 (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1))) none
  synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let pf ← instantiateMVars (← elabTerm (← `(fun (n : Nat) => @rfl Nat (chain14 n))) none)
  addDecl (.thmDecl { name := `Submission.chain14_eq, levelParams := [], type := ty, value := pf })

/- `chain15_eq : ∀ n, chain15 n = chainC0 n 7 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1)` by `rfl`, checked directly by the
kernel (the elaborator's unifier is slow on the unrolled graph). -/
set_option exponentiation.threshold 800 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← elabTerm (← `(∀ n, chain15 n = chainC0 n 7 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1))) none
  synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let pf ← instantiateMVars (← elabTerm (← `(fun (n : Nat) => @rfl Nat (chain15 n))) none)
  addDecl (.thmDecl { name := `Submission.chain15_eq, levelParams := [], type := ty, value := pf })

/- `chain16_eq : ∀ n, chain16 n = chainA0 n 8 7 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1)` by `rfl`, checked directly by the
kernel (the elaborator's unifier is slow on the unrolled graph). -/
set_option exponentiation.threshold 800 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← elabTerm (← `(∀ n, chain16 n = chainA0 n 8 7 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1))) none
  synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let pf ← instantiateMVars (← elabTerm (← `(fun (n : Nat) => @rfl Nat (chain16 n))) none)
  addDecl (.thmDecl { name := `Submission.chain16_eq, levelParams := [], type := ty, value := pf })

/- `chain17_eq : ∀ n, chain17 n = chainE2 n 9 7 6 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1)` by `rfl`, checked directly by the
kernel (the elaborator's unifier is slow on the unrolled graph). -/
set_option exponentiation.threshold 800 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← elabTerm (← `(∀ n, chain17 n = chainE2 n 9 7 6 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1))) none
  synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let pf ← instantiateMVars (← elabTerm (← `(fun (n : Nat) => @rfl Nat (chain17 n))) none)
  addDecl (.thmDecl { name := `Submission.chain17_eq, levelParams := [], type := ty, value := pf })

/- `chain18_eq : ∀ n, chain18 n = chainE3 n 10 7 6 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1)` by `rfl`, checked directly by the
kernel (the elaborator's unifier is slow on the unrolled graph). -/
set_option exponentiation.threshold 800 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← elabTerm (← `(∀ n, chain18 n = chainE3 n 10 7 6 (2 ^ 177) (2 ^ (2 * 177) - 2 ^ 177 - 1) (2 ^ 88) (2 ^ (2 * 88) - 2 ^ 88 - 1))) none
  synthesizeSyntheticMVarsNoPostponing
  let ty ← instantiateMVars ty
  let pf ← instantiateMVars (← elabTerm (← `(fun (n : Nat) => @rfl Nat (chain18 n))) none)
  addDecl (.thmDecl { name := `Submission.chain18_eq, levelParams := [], type := ty, value := pf })

set_option exponentiation.threshold 800 in
theorem chain14_spec (n : Nat) (h : n < 2 ^ 14) : chain14 n = Nat.fib n := by
  rw [chain14_eq]
  exact chainC0_spec n 7 7 88 88 (by decide) (by rw [← pow_add]; exact h)
    (by decide) (by decide +kernel) (by decide) (by decide +kernel)

set_option exponentiation.threshold 800 in
theorem chain15_spec (n : Nat) (h : n < 2 ^ 15) : chain15 n = Nat.fib n := by
  rw [chain15_eq]
  exact chainC0_spec n 7 8 177 88 (by decide) (by rw [← pow_add]; exact h)
    (by decide) (by decide +kernel) (by decide) (by decide +kernel)

set_option exponentiation.threshold 800 in
theorem chain16_spec (n : Nat) (h : n < 2 ^ 16) : chain16 n = Nat.fib n := by
  rw [chain16_eq]
  exact chainA0_spec n 8 7 8 177 88 (by decide : 8 = 7 + 1) (by decide)
    (by rw [← pow_add]; exact h) (by decide) (by decide +kernel) (by decide) (by decide +kernel)

set_option exponentiation.threshold 800 in
theorem chain17_spec (n : Nat) (h : n < 2 ^ 17) : chain17 n = Nat.fib n := by
  rw [chain17_eq]
  exact chainE2_spec n 9 7 6 8 177 88 (by decide : 9 = 7 + 2) (by decide) (by decide)
    (by rw [← pow_add]; exact h) (by decide) (by decide +kernel) (by decide) (by decide +kernel)

set_option exponentiation.threshold 800 in
theorem chain18_spec (n : Nat) (h : n < 2 ^ 18) : chain18 n = Nat.fib n := by
  rw [chain18_eq]
  exact chainE3_spec n 10 7 6 8 177 88 (by decide : 10 = 7 + 3) (by decide) (by decide)
    (by rw [← pow_add]; exact h) (by decide) (by decide +kernel) (by decide) (by decide +kernel)

theorem brecF_eq (x y : Nat → Nat) (b : Bool) (n : Nat) :
    Bool.rec (motive := fun _ => Nat → Nat) x y b n = if b = true then y n else x n := by
  cases b <;> rfl

theorem impl_correct : ∀ n, impl n = fibSpec n := by
  intro n
  rw [show fibSpec n = Nat.fib n from rfl]
  unfold impl
  simp only [brecF_eq, Nat.ble_eq, gen_eq]
  split_ifs with hA hB hC hD hE
  · exact chain14_spec n (by omega)
  · exact chain15_spec n (by omega)
  · exact chain16_spec n (by omega)
  · exact chain17_spec n (by omega)
  · exact chain18_spec n (by omega)
  · rfl

end Submission
