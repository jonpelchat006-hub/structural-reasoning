import Spec
import Lean

/-!
# Rule 110: lane-parallel seeded row, tripled-row evolution

**Initial row.** The 254 seeded cells need 254 evaluations of `caMix32`. All of them run at once:
one natural number holds 320 lanes of 64 bits, lane `ℓ = 5q + r` (`r < 4`) carrying cell
`q + 64r` (lanes with `r = 4` are idle and hold `0`). The mixer is a handful of big-number
operations (multiply by a constant is lane-exact because products stay below `2^64`; xor-shifts
are cleaned by a lane mask). Bit 31 of every lane is moved to the lane bottom, and a single
`% (2^319 - 1)` collects them: `2^(64ℓ) ≡ 2^(q + 64r)`, so each cell's bit lands on its own index.

**Evolution.** The cyclic 256-cell row is stored three times side by side (768 bits). One step of
Rule 110 is then six plain bitwise operations, `(c ||| r) ^^^ (l &&& c &&& r)`, with no rotation:
after `k ≤ 256` steps the middle copy is still exact (each step only spoils one more bit at each
outer edge). Longer runs re-copy the middle every 256 steps.

**`impl`.** For the evolution lengths `2`, `4` and `8` (the tested scales) the whole computation is
one shared expression per length (`go2`, `go4`, `go8`): the lane constants are numerals computed
at elaboration time (`eval%` evaluates the definitions `cR`, `cT`, … once), and the steps are
unrolled. `impl` selects the branch with `Bool.rec` on `Nat.beq` tests (cheaper for the kernel than
a `Nat.rec` on a numeral); other lengths use the general `slow` (`run`, with loops). The kernel
checks `go2_eq`, `fast2_eq`, … by `rfl`, identifying the unrolled branches with `run`. Core Lean's
code generator cannot compile `Bool.rec`, so compiled code uses `implC` (`@[implemented_by]`, the
same branches with `if`); `implC_eq` proves that the two agree on every input.

All numerals in the implementation are raw `nat_lit`s or `eval%` literals, and all operations are
the kernel's GMP-accelerated `Nat` primitives.
-/

set_option exponentiation.threshold 2048

namespace Submission

/-! ## Implementation -/

open Lean Elab Term Meta in
/-- Elaborate a Nat expression with shared nodes, without runtime let reductions. -/
elab "share " x:ident " := " v:term "; " b:term : term => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b (some (mkConst ``Nat)))
    return b.replaceFVar fv v



open Lean Elab Term Meta in
/-- `eval% c` is the value of the closed natural-number term `c` (definitions unfolded), computed
once at elaboration time and inserted as a raw numeral. -/
elab "eval% " e:term : term => do
  let e ← elabTermEnsuringType e (some (mkConst ``Nat))
  synthesizeSyntheticMVarsNoPostponing
  let r ← withTransparency .all <| whnf (← instantiateMVars e)
  match r with
  | .lit (.natVal n) => return mkRawNatLit n
  | _ => throwError "eval%: not a numeral: {r}"

/-- `Σ_{q<64} 2^(320 q)`. -/
def cR5 : Nat :=
  Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 20480)) (nat_lit 1))
    (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 320)) (nat_lit 1))

/-- `Σ_{q<64} (q+1) 2^(320 q)`. -/
def cT5 : Nat :=
  Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 20486)) cR5)
    (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 320)) (nat_lit 1))

/-- A one in every active lane. -/
def cR : Nat := Nat.mul (nat_lit 0x1000000000000000100000000000000010000000000000001) cR5

/-- Active lane `ℓ` holds `cell ℓ + 1`. -/
def cT : Nat :=
  Nat.add (Nat.mul (nat_lit 0x1000000000000000100000000000000010000000000000001) cT5)
    (Nat.mul (nat_lit 0xc0000000000000008000000000000000400000000000000000) cR5)

/-- 32 ones in every active lane. -/
def cRM : Nat := Nat.mul cR (nat_lit 0xffffffff)

/-- A one in every active lane except those of cells 0 and 1. -/
def cE : Nat := Nat.sub cR (Nat.add (Nat.shiftLeft (nat_lit 1) (nat_lit 320)) (nat_lit 1))

/-- Bit 31 of the mixer for every seeded cell, at the bottom of its lane. -/
def mixAll (s : Nat) : Nat :=
  share X0 := Nat.add (Nat.mul cR s) (Nat.mul (nat_lit 0x9e3779b9) cT);
  share X1 := Nat.land cRM (Nat.mul (nat_lit 0x7feb352d)
    (Nat.land cRM (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));
  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land cRM (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));
  Nat.land cE (Nat.shiftRight X2 (nat_lit 31))

/-- The initial row as a 256-bit number. -/
def row0 (s : Nat) : Nat :=
  Nat.lor (nat_lit 1) (Nat.mod (mixAll s)
    (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1)))

/-- `k` raw Rule 110 steps on a non-cyclic bit string. -/
def fpowV2 (X k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) X
    (fun _ Y => Nat.sub (Nat.lor Y (Nat.shiftRight Y (nat_lit 1)))
      (Nat.land (Nat.land (Nat.add Y Y) Y) (Nat.shiftRight Y (nat_lit 1)))) k


def rawStep (X : Nat) : Nat := Nat.sub (Nat.lor X (Nat.shiftRight X (nat_lit 1))) (Nat.land (Nat.land (Nat.add X X) X) (Nat.shiftRight X (nat_lit 1)))

def chunkStep (X : Nat) : Nat :=
  share X1 := Nat.sub (Nat.lor X (Nat.shiftRight X (nat_lit 1))) (Nat.land (Nat.land (Nat.add X X) X) (Nat.shiftRight X (nat_lit 1)));
  share X2 := Nat.sub (Nat.lor X1 (Nat.shiftRight X1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add X1 X1) X1) (Nat.shiftRight X1 (nat_lit 1)));
  X2

def chunks (X k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) X (fun _ Y =>
    share X1 := Nat.sub (Nat.lor Y (Nat.shiftRight Y (nat_lit 1))) (Nat.land (Nat.land (Nat.add Y Y) Y) (Nat.shiftRight Y (nat_lit 1)));
      share X2 := Nat.sub (Nat.lor X1 (Nat.shiftRight X1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add X1 X1) X1) (Nat.shiftRight X1 (nat_lit 1)));
      X2) k

theorem fpowV2_add (X a : Nat) : ∀ b, fpowV2 X (a + b) = fpowV2 (fpowV2 X a) b
  | 0 => rfl
  | b + 1 => by
    change rawStep (fpowV2 X (a + b)) = rawStep (fpowV2 (fpowV2 X a) b)
    rw [fpowV2_add X a b]

theorem chunks_eq (X : Nat) : ∀ k, chunks X k = fpowV2 X (2 * k)
  | 0 => rfl
  | k + 1 => by
    change chunkStep (chunks X k) = _
    rw [chunks_eq X k, show 2 * (k + 1) = 2 * k + 2 by omega, fpowV2_add]
    rfl

def fpow (X k : Nat) : Nat :=
  fpowV2 (chunks X (Nat.shiftRight k (nat_lit 1))) (Nat.mod k (nat_lit 2))

theorem fpow_eq (X k : Nat) : fpow X k = fpowV2 X k := by
  unfold fpow
  rw [chunks_eq, ← fpowV2_add]
  congr 1
  exact Nat.div_add_mod k 2

/-- Three copies of a 256-bit row. -/
def triple (m : Nat) : Nat :=
  Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) m

/-- The middle copy. -/
def middle (X : Nat) : Nat :=
  Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff)
    (Nat.shiftRight X (nat_lit 256))

/-- `t` cyclic steps: whole chunks of 256 steps, re-copied, then the rest. -/
def run (m t : Nat) : Nat :=
  middle (fpow (Nat.rec (motive := fun _ => Nat) (triple m)
    (fun _ Y => triple (middle (fpow Y (nat_lit 256)))) (Nat.shiftRight t (nat_lit 8)))
    (Nat.land t (nat_lit 255)))

def slow (n : Nat) : Nat :=
  run (row0 (Nat.land n (nat_lit 0xffffffff))) (Nat.shiftRight n (nat_lit 32))

set_option exponentiation.threshold 21000 in
/-- `mixAll` with the lane constants as numerals. -/
def mixAllL (s : Nat) : Nat :=
  share X0 := Nat.add (Nat.mul (eval% cR) s) (eval% (Nat.mul (nat_lit 0x9e3779b9) cT));
  share X1 := Nat.land (eval% cRM) (Nat.mul (nat_lit 0x7feb352d)
    (Nat.land (eval% cRM) (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));
  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land (eval% cRM) (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));
  Nat.land (eval% cE) (Nat.shiftRight X2 (nat_lit 31))

/-- `row0` with the constants as numerals. -/
def row0L (s : Nat) : Nat :=
  Nat.lor (nat_lit 1)
    (Nat.mod (mixAllL s) (eval% (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1))))

/-- `run m 2`, unrolled. -/
def fast2 (m : Nat) : Nat :=
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) m;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S2 (nat_lit 256)))

/-- `run m 4`, unrolled. -/
def fast4 (m : Nat) : Nat :=
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) m;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  share S3 := (Nat.sub (Nat.lor S2 (Nat.shiftRight S2 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S2 S2) S2) (Nat.shiftRight S2 (nat_lit 1))));
  share S4 := (Nat.sub (Nat.lor S3 (Nat.shiftRight S3 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S3 S3) S3) (Nat.shiftRight S3 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S4 (nat_lit 256)))

/-- `run m 8`, unrolled. -/
def fast8 (m : Nat) : Nat :=
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) m;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  share S3 := (Nat.sub (Nat.lor S2 (Nat.shiftRight S2 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S2 S2) S2) (Nat.shiftRight S2 (nat_lit 1))));
  share S4 := (Nat.sub (Nat.lor S3 (Nat.shiftRight S3 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S3 S3) S3) (Nat.shiftRight S3 (nat_lit 1))));
  share S5 := (Nat.sub (Nat.lor S4 (Nat.shiftRight S4 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S4 S4) S4) (Nat.shiftRight S4 (nat_lit 1))));
  share S6 := (Nat.sub (Nat.lor S5 (Nat.shiftRight S5 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S5 S5) S5) (Nat.shiftRight S5 (nat_lit 1))));
  share S7 := (Nat.sub (Nat.lor S6 (Nat.shiftRight S6 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S6 S6) S6) (Nat.shiftRight S6 (nat_lit 1))));
  share S8 := (Nat.sub (Nat.lor S7 (Nat.shiftRight S7 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S7 S7) S7) (Nat.shiftRight S7 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S8 (nat_lit 256)))

set_option exponentiation.threshold 21000 in
/-- `2` steps from the seed: the lane-parallel initial row and `2` unrolled steps, one shared
expression. -/
def go2 (n : Nat) : Nat :=
  share s := Nat.land n (nat_lit 0xffffffff);
  share X0 := Nat.add (Nat.mul (eval% cR) s) (eval% (Nat.mul (nat_lit 0x9e3779b9) cT));
  share X1 := Nat.land (eval% cRM) (Nat.mul (nat_lit 0x7feb352d)
    (Nat.land (eval% cRM) (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));
  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land (eval% cRM) (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));
  share R0 := Nat.lor (nat_lit 1) (Nat.mod (Nat.land (eval% cE) (Nat.shiftRight X2 (nat_lit 31)))
    (eval% (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1))));
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) R0;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S2 (nat_lit 256)))

set_option exponentiation.threshold 21000 in
/-- `4` steps from the seed: the lane-parallel initial row and `4` unrolled steps, one shared
expression. -/
def go4 (n : Nat) : Nat :=
  share s := Nat.land n (nat_lit 0xffffffff);
  share X0 := Nat.add (Nat.mul (eval% cR) s) (eval% (Nat.mul (nat_lit 0x9e3779b9) cT));
  share X1 := Nat.land (eval% cRM) (Nat.mul (nat_lit 0x7feb352d)
    (Nat.land (eval% cRM) (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));
  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land (eval% cRM) (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));
  share R0 := Nat.lor (nat_lit 1) (Nat.mod (Nat.land (eval% cE) (Nat.shiftRight X2 (nat_lit 31)))
    (eval% (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1))));
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) R0;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  share S3 := (Nat.sub (Nat.lor S2 (Nat.shiftRight S2 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S2 S2) S2) (Nat.shiftRight S2 (nat_lit 1))));
  share S4 := (Nat.sub (Nat.lor S3 (Nat.shiftRight S3 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S3 S3) S3) (Nat.shiftRight S3 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S4 (nat_lit 256)))

set_option exponentiation.threshold 21000 in
/-- `8` steps from the seed: the lane-parallel initial row and `8` unrolled steps, one shared
expression. -/
def go8 (n : Nat) : Nat :=
  share s := Nat.land n (nat_lit 0xffffffff);
  share X0 := Nat.add (Nat.mul (eval% cR) s) (eval% (Nat.mul (nat_lit 0x9e3779b9) cT));
  share X1 := Nat.land (eval% cRM) (Nat.mul (nat_lit 0x7feb352d)
    (Nat.land (eval% cRM) (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));
  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land (eval% cRM) (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));
  share R0 := Nat.lor (nat_lit 1) (Nat.mod (Nat.land (eval% cE) (Nat.shiftRight X2 (nat_lit 31)))
    (eval% (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1))));
  share S0 := Nat.mul (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001) R0;
  share S1 := (Nat.sub (Nat.lor S0 (Nat.shiftRight S0 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S0 S0) S0) (Nat.shiftRight S0 (nat_lit 1))));
  share S2 := (Nat.sub (Nat.lor S1 (Nat.shiftRight S1 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S1 S1) S1) (Nat.shiftRight S1 (nat_lit 1))));
  share S3 := (Nat.sub (Nat.lor S2 (Nat.shiftRight S2 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S2 S2) S2) (Nat.shiftRight S2 (nat_lit 1))));
  share S4 := (Nat.sub (Nat.lor S3 (Nat.shiftRight S3 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S3 S3) S3) (Nat.shiftRight S3 (nat_lit 1))));
  share S5 := (Nat.sub (Nat.lor S4 (Nat.shiftRight S4 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S4 S4) S4) (Nat.shiftRight S4 (nat_lit 1))));
  share S6 := (Nat.sub (Nat.lor S5 (Nat.shiftRight S5 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S5 S5) S5) (Nat.shiftRight S5 (nat_lit 1))));
  share S7 := (Nat.sub (Nat.lor S6 (Nat.shiftRight S6 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S6 S6) S6) (Nat.shiftRight S6 (nat_lit 1))));
  share S8 := (Nat.sub (Nat.lor S7 (Nat.shiftRight S7 (nat_lit 1))) (Nat.land (Nat.land (Nat.add S7 S7) S7) (Nat.shiftRight S7 (nat_lit 1))));
  (Nat.land (nat_lit 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff) (Nat.shiftRight S8 (nat_lit 256)))

/-- Compiled code for `impl` (the kernel never runs it): the same branches with `if`. The core
code generator has no implementation of `Bool.rec`, which `impl` uses for the kernel. -/
def implC (n : Nat) : Nat :=
  if Nat.shiftRight n 32 = 2 then go2 n
  else if Nat.shiftRight n 32 = 4 then go4 n
  else if Nat.shiftRight n 32 = 8 then go8 n
  else slow n

/-- Lengths `2, 4, 8`: one definition each (`go2`, `go4`, `go8`); `slow` otherwise. The tests are
`Bool.rec` on `Nat.beq` (a `Bool` match is cheaper for the kernel than a `Nat.rec` on a numeral),
so only the selected branch is unfolded. -/
@[implemented_by implC]
def impl (n : Nat) : Nat :=
  share t := Nat.shiftRight n (nat_lit 32);
  Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (slow n) (go8 n) (Nat.beq t (nat_lit 8)))
      (go4 n) (Nat.beq t (nat_lit 4)))
    (go2 n) (Nat.beq t (nat_lit 2))

/-! ## Spec helpers -/

theorem testBit_encodeRow (row : List Bool) (i : Nat) :
    (encodeRow row).testBit i = row.getD i false := by
  induction row generalizing i with
  | nil => simp [encodeRow]
  | cons b bs ih =>
    have hrec : encodeRow (b :: bs) = 2 * encodeRow bs + (if b then 1 else 0) := rfl
    cases i with
    | zero => rw [hrec]; cases b <;> simp [Nat.testBit_zero] <;> omega
    | succ j =>
      rw [hrec, Nat.testBit_succ]
      have : (2 * encodeRow bs + (if b then 1 else 0)) / 2 = encodeRow bs := by
        cases b <;> simp <;> omega
      rw [this, ih]; rfl

theorem encodeRow_lt (row : List Bool) : encodeRow row < 2 ^ row.length := by
  induction row with
  | nil => simp [encodeRow]
  | cons b bs ih =>
    have hrec : encodeRow (b :: bs) = 2 * encodeRow bs + (if b then 1 else 0) := rfl
    rw [hrec, List.length_cons, Nat.pow_succ]; split <;> omega

@[simp] theorem length_stepRow (row : List Bool) : (stepRow row).length = row.length := by
  simp [stepRow]

theorem getD_stepRow (row : List Bool) (i : Nat) :
    (stepRow row).getD i false =
      if i < row.length then
        rule110 (row.getD ((i + row.length - 1) % row.length) false)
                (row.getD i false) (row.getD ((i + 1) % row.length) false)
      else false := by
  by_cases h : i < row.length
  · rw [List.getD_eq_getElem?_getD]; simp [stepRow, h]
  · have hlen : (stepRow row).length ≤ i := by rw [length_stepRow]; omega
    rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none hlen, Option.getD_none, if_neg h]

theorem length_iterRow : ∀ (k : Nat) (row : List Bool), (iterRow k row).length = row.length
  | 0, _ => rfl
  | k + 1, row => by
    show (iterRow k (stepRow row)).length = _
    rw [length_iterRow k, length_stepRow]

theorem iterRow_succ' : ∀ (k : Nat) (row : List Bool),
    iterRow (k + 1) row = stepRow (iterRow k row)
  | 0, _ => rfl
  | k + 1, row => by
    show iterRow (k + 1) (stepRow row) = stepRow (iterRow k (stepRow row))
    rw [iterRow_succ' k]

theorem iterRow_add : ∀ (a b : Nat) (row : List Bool),
    iterRow (a + b) row = iterRow b (iterRow a row)
  | 0, _, _ => by rw [Nat.zero_add]; rfl
  | a + 1, b, row => by
    rw [show a + 1 + b = a + b + 1 by omega]
    show iterRow (a + b) (stepRow row) = iterRow b (iterRow a (stepRow row))
    rw [iterRow_add a b]

theorem tb_one (j : Nat) : Nat.testBit 1 j = decide (j = 0) := by
  cases j with
  | zero => rfl
  | succ k => rw [Nat.testBit_succ]; simp

theorem testBit_ge {m k : Nat} (hm : m < 2 ^ k) {j : Nat} (hj : k ≤ j) : m.testBit j = false :=
  Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hm (Nat.pow_le_pow_right (by omega) hj))

/-! ## Evolution on the tripled row -/

/-- `X` agrees with the cyclic row on bit positions `[a, b)`. -/
def Agree (X : Nat) (row : List Bool) (a b : Nat) : Prop :=
  ∀ p, a ≤ p → p < b → X.testBit p = row.getD (p % 256) false

theorem add_eq_xor_of_disj : ∀ (a b : Nat), (∀ i, a.testBit i = true → b.testBit i = false) →
    a + b = a ^^^ b := by
  intro a
  induction a using Nat.strongRecOn with
  | ind a ih =>
    intro b h
    rcases Nat.eq_zero_or_pos a with rfl | ha
    · simp
    · have hd : ∀ i, (a / 2).testBit i = true → (b / 2).testBit i = false := by
        intro i hi
        have := h (i + 1)
        rw [Nat.testBit_add_one, Nat.testBit_add_one] at this
        exact this hi
      have ih' := ih (a / 2) (Nat.div_lt_self ha (by decide)) (b / 2) hd
      have h0 := h 0
      simp only [Nat.testBit_zero, decide_eq_true_eq, decide_eq_false_iff_not] at h0
      have hx := Nat.div_add_mod (a ^^^ b) 2
      rw [Nat.xor_div_two, ← ih'] at hx
      have hm : (a ^^^ b) % 2 = a % 2 + b % 2 := by
        have key := Nat.xor_mod_two_eq_one (a := a) (b := b)
        rcases Nat.mod_two_eq_zero_or_one a with ha2 | ha2 <;>
          rcases Nat.mod_two_eq_zero_or_one b with hb2 | hb2 <;>
          rcases Nat.mod_two_eq_zero_or_one (a ^^^ b) with hx2 | hx2 <;> simp_all
      omega

theorem sub_eq_xor_of_sub (E D : Nat) (h : ∀ i, D.testBit i = true → E.testBit i = true) :
    E - D = E ^^^ D := by
  have hdisj : ∀ i, (E ^^^ D).testBit i = true → D.testBit i = false := by
    intro i hi
    rw [Nat.testBit_xor] at hi
    cases hD : D.testBit i
    · rfl
    · have := h i hD; rw [this, hD] at hi; simp at hi
  have hsum := add_eq_xor_of_disj (E ^^^ D) D hdisj
  rw [Nat.xor_assoc, Nat.xor_self, Nat.xor_zero] at hsum
  omega

theorem step_eq (X : Nat) :
    Nat.sub (Nat.lor X (Nat.shiftRight X 1)) (Nat.land (Nat.land (Nat.add X X) X) (Nat.shiftRight X 1))
      = Nat.xor (Nat.lor X (Nat.shiftRight X 1)) (Nat.land (Nat.land (Nat.shiftLeft X 1) X) (Nat.shiftRight X 1)) := by
  have h2 : Nat.add X X = Nat.shiftLeft X 1 := by
    show X + X = X <<< 1; rw [Nat.shiftLeft_eq]; omega
  rw [h2]
  apply sub_eq_xor_of_sub
  intro i hi
  show (X ||| X >>> 1).testBit i = true
  have : ((X <<< 1 &&& X) &&& X >>> 1).testBit i = true := hi
  simp only [Nat.testBit_and, Nat.testBit_or, Bool.and_eq_true] at this ⊢
  simp [this.1.2]

theorem fpow_succ (X k : Nat) : fpow X (k + 1) =
    Nat.xor (Nat.lor (fpow X k) (Nat.shiftRight (fpow X k) 1))
      (Nat.land (Nat.land (Nat.shiftLeft (fpow X k) 1) (fpow X k)) (Nat.shiftRight (fpow X k) 1)) := by
  simp only [fpow_eq]
  rw [← step_eq]
  rfl

theorem rule110_eq (l c r : Bool) : rule110 l c r = ((c || r) ^^ (l && c && r)) := by
  cases l <;> cases c <;> cases r <;> rfl

theorem agree_step {X : Nat} {row : List Bool} (hlen : row.length = 256) {a b : Nat}
    (h : Agree X row a b) :
    Agree (Nat.xor (Nat.lor X (Nat.shiftRight X 1))
      (Nat.land (Nat.land (Nat.shiftLeft X 1) X) (Nat.shiftRight X 1))) (stepRow row) (a + 1) (b - 1) := by
  intro p hp1 hp2
  show ((X ||| (X >>> 1)) ^^^ (((X <<< 1) &&& X) &&& (X >>> 1))).testBit p = _
  simp only [Nat.testBit_xor, Nat.testBit_or, Nat.testBit_and, Nat.testBit_shiftRight,
    Nat.testBit_shiftLeft]
  rw [getD_stepRow, hlen, if_pos (Nat.mod_lt _ (by omega)), rule110_eq]
  have e0 : X.testBit p = row.getD (p % 256) false := h p (by omega) (by omega)
  have e1 : X.testBit (1 + p) = row.getD ((p % 256 + 1) % 256) false := by
    rw [h (1 + p) (by omega) (by omega)]; congr 1; omega
  have e2 : X.testBit (p - 1) = row.getD ((p % 256 + 256 - 1) % 256) false := by
    rw [h (p - 1) (by omega) (by omega)]; congr 1; omega
  have hp : (p ≥ 1) = True := by apply propext; constructor <;> intro _ <;> first | trivial | omega
  simp only [e0, e1, e2, hp, decide_true, Bool.true_and]

theorem agree_fpow {row : List Bool} (hlen : row.length = 256) {X a b : Nat} (h : Agree X row a b) :
    ∀ k, Agree (fpow X k) (iterRow k row) (a + k) (b - k)
  | 0 => h
  | k + 1 => by
    rw [fpow_succ, iterRow_succ']
    have := agree_step (by rw [length_iterRow, hlen]) (agree_fpow hlen h k)
    rwa [show a + k + 1 = a + (k + 1) by omega, show b - k - 1 = b - (k + 1) by omega] at this

theorem K3_eq : (nat_lit 0x100000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001)
    = 2 ^ 512 + 2 ^ 256 + 1 := by decide

theorem triple_eq {m : Nat} (hm : m < 2 ^ 256) : triple m = (m <<< 512) ||| ((m <<< 256) ||| m) := by
  have h1 : (m <<< 256) + m = (m <<< 256) ||| m := Nat.shiftLeft_add_eq_or_of_lt hm m
  have h2 : (m <<< 256) ||| m < 2 ^ 512 := by
    rw [← h1, Nat.shiftLeft_eq]
    have : m * 2 ^ 256 + m < (m + 1) * 2 ^ 256 := by rw [Nat.add_mul]; omega
    have h3 : (m + 1) * 2 ^ 256 ≤ 2 ^ 256 * 2 ^ 256 := Nat.mul_le_mul_right _ hm
    have h4 : (2 : Nat) ^ 512 = 2 ^ 256 * 2 ^ 256 := by rw [← Nat.pow_add]
    omega
  rw [← Nat.shiftLeft_add_eq_or_of_lt h2 m, ← h1]
  show _ * m = _
  rw [Nat.mul_comm, K3_eq, Nat.shiftLeft_eq, Nat.shiftLeft_eq, Nat.mul_add, Nat.mul_add, Nat.mul_one]
  omega

theorem agree_triple (row : List Bool) (hlen : row.length = 256) :
    Agree (triple (encodeRow row)) row 0 768 := by
  intro p _ hp
  have hm : encodeRow row < 2 ^ 256 := hlen ▸ encodeRow_lt row
  rw [triple_eq hm, Nat.testBit_or, Nat.testBit_or, Nat.testBit_shiftLeft, Nat.testBit_shiftLeft,
    ← testBit_encodeRow]
  by_cases h1 : p < 256
  · simp [show ¬ (p ≥ 512) by omega, show ¬ (p ≥ 256) by omega, Nat.mod_eq_of_lt h1]
  · by_cases h2 : p < 512
    · rw [testBit_ge hm (show 256 ≤ p by omega)]
      simp [show ¬ (p ≥ 512) by omega, show p ≥ 256 by omega, show p - 256 = p % 256 by omega]
    · rw [testBit_ge hm (show 256 ≤ p by omega), testBit_ge hm (show 256 ≤ p - 256 by omega)]
      simp [show p ≥ 512 by omega, show p - 512 = p % 256 by omega]

theorem middle_eq {X : Nat} {row : List Bool} (hlen : row.length = 256) (h : Agree X row 256 512) :
    middle X = encodeRow row := by
  apply Nat.eq_of_testBit_eq
  intro p
  show ((2 ^ 256 - 1) &&& (X >>> 256)).testBit p = _
  rw [Nat.and_comm, Nat.testBit_and, Nat.testBit_shiftRight, Nat.testBit_two_pow_sub_one, testBit_encodeRow]
  by_cases hp : p < 256
  · rw [h (256 + p) (by omega) (by omega)]
    simp only [hp, decide_true, Bool.and_true]
    congr 1; omega
  · rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none (by omega)]
    simp [hp]

theorem run_chunks (row : List Bool) (hlen : row.length = 256) : ∀ a,
    Nat.rec (motive := fun _ => Nat) (triple (encodeRow row))
      (fun _ Y => triple (middle (fpow Y 256))) a = triple (encodeRow (iterRow (256 * a) row))
  | 0 => rfl
  | a + 1 => by
    show triple (middle (fpow (Nat.rec (motive := fun _ => Nat) (triple (encodeRow row))
      (fun _ Y => triple (middle (fpow Y 256))) a) 256)) = _
    rw [run_chunks row hlen a]
    have hl : (iterRow (256 * a) row).length = 256 := by rw [length_iterRow, hlen]
    have := agree_fpow hl (agree_triple _ hl) 256
    rw [middle_eq (by rw [length_iterRow, hl]) (fun p h1 h2 => this p (by omega) (by omega)),
      ← iterRow_add, show 256 * a + 256 = 256 * (a + 1) by omega]

theorem run_eq (row : List Bool) (hlen : row.length = 256) (t : Nat) :
    run (encodeRow row) t = encodeRow (iterRow t row) := by
  unfold run
  rw [run_chunks row hlen]
  have hl : (iterRow (256 * Nat.shiftRight t 8) row).length = 256 := by rw [length_iterRow, hlen]
  have hb : Nat.land t 255 < 256 := by
    have := @Nat.and_le_right t 255; exact Nat.lt_of_le_of_lt this (by decide)
  have := agree_fpow hl (agree_triple _ hl) (Nat.land t 255)
  rw [middle_eq (by rw [length_iterRow, hl]) (fun p h1 h2 => this p (by omega) (by omega)),
    ← iterRow_add]
  have ht : 256 * Nat.shiftRight t 8 + Nat.land t 255 = t := by
    show 256 * (t >>> 8) + (t &&& 255) = t
    rw [Nat.shiftRight_eq_div_pow, show (255 : Nat) = 2 ^ 8 - 1 from rfl,
      Nat.and_two_pow_sub_one_eq_mod]
    omega
  rw [ht]


/-! ## Lane encodings (64-bit lanes) -/

def enc (a : Nat → Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => enc a L + a L * 2 ^ (64 * L)

theorem enc_lt (a : Nat → Nat) : ∀ L, (∀ i, i < L → a i < 2 ^ 64) → enc a L < 2 ^ (64 * L)
  | 0, _ => by simp [enc]
  | L + 1, h => by
    simp only [enc]
    have h1 := enc_lt a L (fun i hi => h i (by omega))
    have h2 : a L + 1 ≤ 2 ^ 64 := h L (by omega)
    have h3 : (a L + 1) * 2 ^ (64 * L) ≤ 2 ^ 64 * 2 ^ (64 * L) := Nat.mul_le_mul_right _ h2
    rw [Nat.add_mul, Nat.one_mul] at h3
    have e : 2 ^ (64 * (L + 1)) = 2 ^ 64 * 2 ^ (64 * L) := by
      rw [Nat.mul_succ, Nat.pow_add, Nat.mul_comm]
    rw [e]
    omega

theorem enc_congr {a b : Nat → Nat} : ∀ L, (∀ i, i < L → a i = b i) → enc a L = enc b L
  | 0, _ => rfl
  | L + 1, h => by
    simp only [enc]
    rw [enc_congr L (fun i hi => h i (by omega)), h L (by omega)]

theorem enc_add (a b : Nat → Nat) : ∀ L, enc (fun i => a i + b i) L = enc a L + enc b L
  | 0 => rfl
  | L + 1 => by
    simp only [enc]
    rw [enc_add a b L, Nat.add_mul]
    omega

theorem enc_mul (a : Nat → Nat) (c : Nat) : ∀ L, enc (fun i => a i * c) L = enc a L * c
  | 0 => by simp [enc]
  | L + 1 => by
    simp only [enc]
    rw [enc_mul a c L, Nat.add_mul, Nat.mul_right_comm]

theorem enc_tb (a : Nat → Nat) (p : Nat) : ∀ L, (∀ i, i < L → a i < 2 ^ 64) →
    (enc a L).testBit p = (decide (p / 64 < L) && (a (p / 64)).testBit (p % 64))
  | 0, _ => by simp [enc]
  | L + 1, h => by
    have h' : ∀ i, i < L → a i < 2 ^ 64 := fun i hi => h i (by omega)
    simp only [enc]
    rw [Nat.add_comm, ← Nat.shiftLeft_eq, Nat.shiftLeft_add_eq_or_of_lt (enc_lt a L h'),
      Nat.testBit_or, Nat.testBit_shiftLeft, enc_tb a p L h']
    rcases Nat.lt_trichotomy (p / 64) L with hlt | heq | hgt
    · have : ¬ (p ≥ 64 * L) := by omega
      simp [this, hlt, show p / 64 < L + 1 by omega]
    · have h1 : p ≥ 64 * L := by omega
      have h2 : p - 64 * L = p % 64 := by omega
      simp [h1, h2, heq]
    · have h1 : p ≥ 64 * L := by omega
      have h3 : (a L).testBit (p - 64 * L) = false :=
        Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (h L (by omega))
          (Nat.pow_le_pow_right (by omega) (by omega)))
      simp [h1, h3, show ¬ (p / 64 < L) by omega, show ¬ (p / 64 < L + 1) by omega]

/-- Splitting off the lanes `L, …, L + k - 1`. -/
theorem enc_succ (a : Nat → Nat) (L : Nat) : enc a (L + 1) = enc a L + a L * 2 ^ (64 * L) := rfl

theorem enc_split (b : Nat → Nat) (L : Nat) : ∀ k,
    enc b (L + k) = enc b L + enc (fun r => b (L + r)) k * 2 ^ (64 * L)
  | 0 => by simp [enc]
  | k + 1 => by
    rw [show L + (k + 1) = L + k + 1 by omega]
    simp only [enc]
    rw [enc_split b L k, Nat.add_mul, show 64 * (L + k) = 64 * k + 64 * L by omega, Nat.pow_add,
      Nat.mul_assoc]
    omega

/-! ## Lane layout: lane `ℓ = 5q + r` (`r < 4`) holds cell `q + 64 r` -/

def cell (ℓ : Nat) : Nat := ℓ / 5 + 64 * (ℓ % 5)
def aR (ℓ : Nat) : Nat := if ℓ % 5 < 4 then 1 else 0
def aT (ℓ : Nat) : Nat := if ℓ % 5 < 4 then cell ℓ + 1 else 0
def aRM (ℓ : Nat) : Nat := if ℓ % 5 < 4 then 0xffffffff else 0
def aE (ℓ : Nat) : Nat := if ℓ % 5 < 4 ∧ 2 ≤ cell ℓ then 1 else 0

theorem cR_eq : cR = enc aR 320 := by decide +kernel
theorem cT_eq : cT = enc aT 320 := by decide +kernel
theorem cRM_eq : cRM = enc aRM 320 := by decide +kernel
theorem cE_eq : cE = enc aE 320 := by decide +kernel

theorem tb_M32 (j : Nat) : (0xffffffff : Nat).testBit j = decide (j < 32) := by
  rw [show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl, Nat.testBit_two_pow_sub_one]

theorem tb_aRM (ℓ j : Nat) : (aRM ℓ).testBit j = (decide (ℓ % 5 < 4) && decide (j < 32)) := by
  unfold aRM
  by_cases h : ℓ % 5 < 4
  · rw [if_pos h, tb_M32]; simp [h]
  · rw [if_neg h]; simp [h]

theorem aRM_lt (ℓ : Nat) : aRM ℓ < 2 ^ 64 := by unfold aRM; split <;> decide

theorem aE_le (ℓ : Nat) : aE ℓ ≤ 1 := by unfold aE; split <;> omega

theorem tb_le_one {x : Nat} (hx : x ≤ 1) (j : Nat) : x.testBit j = (decide (j = 0) && decide (x = 1)) := by
  rcases Nat.le_one_iff_eq_zero_or_eq_one.mp hx with h | h <;> subst h
  · simp
  · rw [tb_one]; simp

theorem land_M32_lt (x : Nat) : x &&& 0xffffffff < 2 ^ 32 := by
  rw [show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl, Nat.and_two_pow_sub_one_eq_mod]
  exact Nat.mod_lt _ (by decide)

theorem land_aRM_lt (x ℓ : Nat) : x &&& aRM ℓ < 2 ^ 32 := by
  unfold aRM
  split
  · exact land_M32_lt x
  · simp

/-! ## Lane-parallel operations -/

/-- Lane-wise xor-shift and mask, for shifts `s ≤ 32`. -/
theorem xs_lanes (a : Nat → Nat) (s : Nat) (hs : s ≤ 32) (h : ∀ i, i < 320 → a i < 2 ^ 64) :
    Nat.land (Nat.xor (enc a 320) (Nat.shiftRight (enc a 320) s)) (enc aRM 320)
      = enc (fun i => (a i ^^^ (a i >>> s)) &&& aRM i) 320 := by
  apply Nat.eq_of_testBit_eq
  intro p
  show ((enc a 320 ^^^ (enc a 320 >>> s)) &&& enc aRM 320).testBit p = _
  have h2 : ∀ i, i < 320 → (a i ^^^ (a i >>> s)) &&& aRM i < 2 ^ 64 :=
    fun i _ => Nat.lt_of_lt_of_le (land_aRM_lt _ _) (by decide)
  rw [Nat.testBit_and, Nat.testBit_xor, Nat.testBit_shiftRight, enc_tb _ p 320 h,
    enc_tb _ (s + p) 320 h, enc_tb _ p 320 (fun i _ => aRM_lt i), enc_tb _ p 320 h2,
    tb_aRM, Nat.testBit_and, Nat.testBit_xor, Nat.testBit_shiftRight, tb_aRM]
  by_cases hj : p % 64 < 32
  · have e1 : (s + p) / 64 = p / 64 := by omega
    have e2 : (s + p) % 64 = s + p % 64 := by omega
    rw [e1, e2]
    by_cases hl : p / 64 < 320 <;> simp [hl, hj]
  · simp [hj]

/-- Lane-wise mask. -/
theorem mask_lanes (a : Nat → Nat) (h : ∀ i, i < 320 → a i < 2 ^ 64) :
    Nat.land (enc a 320) (enc aRM 320) = enc (fun i => a i &&& aRM i) 320 := by
  apply Nat.eq_of_testBit_eq
  intro p
  show (enc a 320 &&& enc aRM 320).testBit p = _
  rw [Nat.testBit_and, enc_tb _ p 320 h, enc_tb _ p 320 (fun i _ => aRM_lt i),
    enc_tb _ p 320 (fun i _ => Nat.lt_of_lt_of_le (land_aRM_lt _ _) (by decide)), Nat.testBit_and]
  by_cases hl : p / 64 < 320 <;> simp [hl]

/-- Bit 31 of every lane, moved to the bottom and masked by `aE`. -/
theorem bit31_lanes (a : Nat → Nat) (h : ∀ i, i < 320 → a i < 2 ^ 64) :
    Nat.land (Nat.shiftRight (enc a 320) 31) (enc aE 320) = enc (fun i => (a i >>> 31) &&& aE i) 320 := by
  apply Nat.eq_of_testBit_eq
  intro p
  show ((enc a 320 >>> 31) &&& enc aE 320).testBit p = _
  have hE : ∀ i, i < 320 → aE i < 2 ^ 64 := fun i _ => Nat.lt_of_le_of_lt (aE_le i) (by decide)
  have h1 : ∀ i, i < 320 → (a i >>> 31) &&& aE i < 2 ^ 64 := fun i _ =>
    Nat.lt_of_le_of_lt (Nat.le_trans Nat.and_le_right (aE_le i)) (by decide)
  rw [Nat.testBit_and, Nat.testBit_shiftRight, enc_tb _ (31 + p) 320 h, enc_tb _ p 320 hE,
    enc_tb _ p 320 h1, Nat.testBit_and, Nat.testBit_shiftRight, tb_le_one (aE_le _)]
  by_cases hj : p % 64 = 0
  · have e1 : (31 + p) / 64 = p / 64 := by omega
    have e2 : (31 + p) % 64 = 31 := by omega
    rw [e1, e2, hj]
    by_cases hl : p / 64 < 320 <;> simp [hl]
  · simp [hj]

theorem enc_mulN (a : Nat → Nat) (c L : Nat) : Nat.mul (enc a L) c = enc (fun i => a i * c) L :=
  (enc_mul a c L).symm

/-! ## The lane values -/

def uL (s i : Nat) : Nat := s * aR i + 0x9e3779b9 * aT i
def yL (s i : Nat) : Nat := (((uL s i ^^^ (uL s i >>> 16)) &&& aRM i) * 0x7feb352d) &&& aRM i
def zL (s i : Nat) : Nat := ((yL s i ^^^ (yL s i >>> 15)) &&& aRM i) * 0x846ca68b
def bL (s i : Nat) : Nat := (zL s i >>> 31) &&& aE i

theorem uL_lt (s i : Nat) (hs : s < 2 ^ 32) (hi : i < 320) : uL s i < 2 ^ 64 := by
  unfold uL aR aT cell
  split <;> omega

/-- `mixAll` with the constants second (the orientation the lane lemmas are stated in). -/
def mixAllO (s : Nat) : Nat :=
  share X0 := Nat.add (Nat.mul s cR) (Nat.mul (nat_lit 0x9e3779b9) cT);
  share X1 := Nat.land (Nat.mul (Nat.land (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16))) cRM)
    (nat_lit 0x7feb352d)) cRM;
  share X2 := Nat.mul (Nat.land (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))) cRM) (nat_lit 0x846ca68b);
  Nat.land (Nat.shiftRight X2 (nat_lit 31)) cE

theorem nmul_comm (a b : Nat) : Nat.mul a b = Nat.mul b a := Nat.mul_comm a b
theorem nland_comm (a b : Nat) : Nat.land a b = Nat.land b a := Nat.and_comm a b

theorem mixAll_O (s : Nat) : mixAll s = mixAllO s := by
  unfold mixAll mixAllO
  simp only [nmul_comm cR s, nland_comm cRM, nmul_comm (nat_lit 0x7feb352d),
    nmul_comm (nat_lit 0x846ca68b), nland_comm cE]

theorem mixAll_eq (s : Nat) (hs : s < 2 ^ 32) : mixAll s = enc (bL s) 320 := by
  rw [mixAll_O]
  have hX : Nat.add (Nat.mul s cR) (Nat.mul 0x9e3779b9 cT) = enc (uL s) 320 := by
    show s * cR + 0x9e3779b9 * cT = _
    rw [cR_eq, cT_eq, Nat.mul_comm s, Nat.mul_comm 0x9e3779b9, ← enc_mul, ← enc_mul, ← enc_add]
    apply enc_congr; intro i _; unfold uL; rw [Nat.mul_comm (aR i), Nat.mul_comm (aT i)]
  unfold mixAllO
  simp only []
  rw [hX, cRM_eq, xs_lanes _ 16 (by omega) (fun i hi => uL_lt s i hs hi), enc_mulN,
    mask_lanes _ (fun i _ => by have := land_aRM_lt (uL s i ^^^ (uL s i >>> 16)) i; omega)]
  have hy : ∀ i, i < 320 → yL s i < 2 ^ 64 := fun i _ =>
    Nat.lt_of_lt_of_le (land_aRM_lt _ _) (by decide)
  show Nat.land (Nat.shiftRight (Nat.mul (Nat.land (Nat.xor (enc (yL s) 320)
    (Nat.shiftRight (enc (yL s) 320) 15)) (enc aRM 320)) 0x846ca68b) 31) cE = _
  rw [xs_lanes _ 15 (by omega) hy, enc_mulN, cE_eq,
    bit31_lanes _ (fun i _ => by have := land_aRM_lt (yL s i ^^^ (yL s i >>> 15)) i; omega)]
  rfl


/-! ## Gathering: one `% (2^319 - 1)` -/

def encB (Z : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => encB Z n + Z n * 2 ^ (320 * n)

def encS (Z : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => encS Z n + Z n * 2 ^ n

def bs (b : Nat → Nat) (r : Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => bs b r n + b (5 * n + r) * 2 ^ n

theorem enc_blocks (b : Nat → Nat) : ∀ n,
    enc b (5 * n) = encB (fun q => enc (fun r => b (5 * q + r)) 5) n
  | 0 => rfl
  | n + 1 => by
    rw [show 5 * (n + 1) = 5 * n + 5 by omega, enc_split, enc_blocks b n]
    simp only [encB]
    rw [show 64 * (5 * n) = 320 * n by omega]

theorem two319_mod : 2 ^ 319 % (2 ^ 319 - 1) = 1 := by decide

theorem encB_mod (Z : Nat → Nat) : ∀ n, encB Z n % (2 ^ 319 - 1) = encS Z n % (2 ^ 319 - 1)
  | 0 => rfl
  | n + 1 => by
    simp only [encB, encS]
    have e : Z n * 2 ^ (320 * n) = Z n * 2 ^ n * (2 ^ 319) ^ n := by
      rw [Nat.mul_assoc, ← Nat.pow_mul, ← Nat.pow_add, show n + 319 * n = 320 * n by omega]
    have hp : (2 ^ 319) ^ n % (2 ^ 319 - 1) = 1 := by
      rw [Nat.pow_mod, two319_mod, Nat.one_pow]
    rw [Nat.add_mod, encB_mod Z n, e, Nat.mul_mod (Z n * 2 ^ n), hp, Nat.mul_one, Nat.mod_mod,
      ← Nat.add_mod]

theorem encS_eq (b : Nat → Nat) : ∀ n,
    encS (fun q => enc (fun r => b (5 * q + r)) 5) n = enc (fun r => bs b r n) 5
  | 0 => by simp [encS, enc, bs]
  | n + 1 => by
    simp only [encS, bs]
    rw [encS_eq b n, ← enc_mul, ← enc_add]

theorem bs_lt (b : Nat → Nat) (hb : ∀ i, b i ≤ 1) (r : Nat) : ∀ n, bs b r n < 2 ^ n
  | 0 => by simp [bs]
  | n + 1 => by
    simp only [bs]
    have := bs_lt b hb r n
    have h1 := hb (5 * n + r)
    have h2 : b (5 * n + r) * 2 ^ n ≤ 1 * 2 ^ n := Nat.mul_le_mul_right _ h1
    rw [Nat.pow_succ]
    omega

theorem bs_tb (b : Nat → Nat) (hb : ∀ i, b i ≤ 1) (r : Nat) : ∀ n j,
    (bs b r n).testBit j = (decide (j < n) && decide (b (5 * j + r) = 1))
  | 0, j => by simp [bs]
  | n + 1, j => by
    simp only [bs]
    rw [Nat.add_comm, ← Nat.shiftLeft_eq, Nat.shiftLeft_add_eq_or_of_lt (bs_lt b hb r n),
      Nat.testBit_or, Nat.testBit_shiftLeft, bs_tb b hb r n j, tb_le_one (hb _)]
    rcases Nat.lt_trichotomy j n with h | h | h
    · simp [h, show j < n + 1 by omega, show ¬ (j ≥ n) by omega]
    · subst h; simp
    · simp [show ¬ (j < n) by omega, show ¬ (j < n + 1) by omega, show j - n ≠ 0 by omega]

theorem gather (b : Nat → Nat) (hb : ∀ i, b i ≤ 1) (h4 : ∀ q, b (5 * q + 4) = 0) :
    enc b 320 % (2 ^ 319 - 1) = enc (fun r => bs b r 64) 5 := by
  have hz : bs b 4 64 = 0 := by
    have : ∀ n, bs b 4 n = 0 := by
      intro n; induction n with
      | zero => rfl
      | succ n ih => simp only [bs]; rw [ih, h4]; simp
    exact this 64
  have hlt : enc (fun r => bs b r 64) 5 < 2 ^ 319 - 1 := by
    have e : enc (fun r => bs b r 64) 5 = enc (fun r => bs b r 64) 4 := by
      rw [show (5 : Nat) = 4 + 1 from rfl, enc_succ, hz, Nat.zero_mul, Nat.add_zero]
    rw [e]
    have := enc_lt (fun r => bs b r 64) 4 (fun i _ => bs_lt b hb i 64)
    have h2 : (2 : Nat) ^ (64 * 4) < 2 ^ 319 - 1 := by decide
    omega
  rw [show (320 : Nat) = 5 * 64 from rfl, enc_blocks, encB_mod, encS_eq, Nat.mod_eq_of_lt hlt]

theorem gather_tb (b : Nat → Nat) (hb : ∀ i, b i ≤ 1) (h4 : ∀ q, b (5 * q + 4) = 0) (p : Nat) :
    (enc b 320 % (2 ^ 319 - 1)).testBit p
      = (decide (p < 320) && decide (b (5 * (p % 64) + p / 64) = 1)) := by
  rw [gather b hb h4, enc_tb _ p 5 (fun i _ => Nat.lt_of_lt_of_le (bs_lt b hb i 64) (by decide)),
    bs_tb b hb]
  by_cases h : p < 320
  · simp [h, show p / 64 < 5 by omega, show p % 64 < 64 by omega]
  · simp [h, show ¬ (p / 64 < 5) by omega]

/-! ## The mixer -/

theorem m1 (v c : Nat) : (v * c) &&& 0xffffffff = ((v &&& 0xffffffff) * c) &&& 0xffffffff := by
  rw [show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl, Nat.and_two_pow_sub_one_eq_mod,
    Nat.and_two_pow_sub_one_eq_mod, Nat.and_two_pow_sub_one_eq_mod,
    Nat.mul_mod v c, Nat.mul_mod (v % 2 ^ 32) c, Nat.mod_mod]

def gA (M c1 x : Nat) : Nat := (((x ^^^ (x >>> 16)) &&& M) * c1) &&& M
def gB (M c1 c2 x : Nat) : Nat := ((gA M c1 x ^^^ (gA M c1 x >>> 15)) &&& M) * c2

/-- The mixer identity, with the mask and constants abstract. -/
theorem mix_generic (x c1 c2 M : Nat) (hM : ∀ j, M.testBit j = decide (j < 32))
    (hm : ∀ v c, (v * c) &&& M = ((v &&& M) * c) &&& M) :
    ((((((((x ^^^ (x >>> 16)) * c1) &&& M) ^^^ ((((x ^^^ (x >>> 16)) * c1) &&& M) >>> 15)) * c2) &&& M) ^^^ (((((((x ^^^ (x >>> 16)) * c1) &&& M) ^^^ ((((x ^^^ (x >>> 16)) * c1) &&& M) >>> 15)) * c2) &&& M) >>> 16)) &&& M).testBit 31 = (gB M c1 c2 x).testBit 31 := by
  unfold gB gA
  rw [hm (x ^^^ (x >>> 16)) c1]
  generalize (((x ^^^ (x >>> 16)) &&& M) * c1) &&& M = y
  rw [hm (y ^^^ (y >>> 15)) c2]
  simp only [Nat.testBit_and, Nat.testBit_xor, Nat.testBit_shiftRight, hM]
  simp

theorem caMix32_eq (x : Nat) : caMix32 x = ((((((((x ^^^ (x >>> 16)) * 0x7feb352d) &&& 0xffffffff) ^^^ ((((x ^^^ (x >>> 16)) * 0x7feb352d) &&& 0xffffffff) >>> 15)) * 0x846ca68b) &&& 0xffffffff) ^^^ (((((((x ^^^ (x >>> 16)) * 0x7feb352d) &&& 0xffffffff) ^^^ ((((x ^^^ (x >>> 16)) * 0x7feb352d) &&& 0xffffffff) >>> 15)) * 0x846ca68b) &&& 0xffffffff) >>> 16)) &&& 0xffffffff) := rfl

theorem mix_bit (s i : Nat) :
    (caMix32 (s + (i + 1) * 0x9e3779b9)).testBit 31 =
      (gB 0xffffffff 0x7feb352d 0x846ca68b (s + 0x9e3779b9 * (i + 1))).testBit 31 := by
  rw [caMix32_eq, Nat.mul_comm (i + 1)]
  exact mix_generic _ _ _ _ tb_M32 m1

/-! ## The initial row -/

theorem bL_le (s i : Nat) : bL s i ≤ 1 := Nat.le_trans Nat.and_le_right (aE_le i)

theorem bL_four (s q : Nat) : bL s (5 * q + 4) = 0 := by
  unfold bL aE
  rw [if_neg (by omega)]
  simp

theorem M319_eq : Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1) = 2 ^ 319 - 1 := by
  decide

theorem row0_eq (s : Nat) (hs : s < 2 ^ 32) : row0 s = encodeRow (initRowFor s) := by
  apply Nat.eq_of_testBit_eq
  intro p
  unfold row0
  rw [M319_eq, mixAll_eq s hs, testBit_encodeRow]
  show (1 ||| (enc (bL s) 320 % (2 ^ 319 - 1))).testBit p = _
  rw [Nat.or_comm, Nat.testBit_or, gather_tb _ (bL_le s) (bL_four s), tb_one]
  unfold initRowFor ruleWidth
  rw [List.getD_eq_getElem?_getD]
  by_cases hp : p < 256
  · rw [List.getElem?_map, List.getElem?_range hp]
    simp only [Option.map_some, Option.getD_some]
    have hl5 : (5 * (p % 64) + p / 64) % 5 = p / 64 := by omega
    have hcell : cell (5 * (p % 64) + p / 64) = p := by unfold cell; omega
    have hb : bL s (5 * (p % 64) + p / 64) = (zL s (5 * (p % 64) + p / 64) >>> 31) &&& aE (5 * (p % 64) + p / 64) := rfl
    have haE : aE (5 * (p % 64) + p / 64) = if 2 ≤ p then 1 else 0 := by
      unfold aE; rw [hl5, hcell]
      by_cases h2 : 2 ≤ p
      · rw [if_pos ⟨by omega, h2⟩, if_pos h2]
      · rw [if_neg (by omega), if_neg h2]
    by_cases h0 : p = 0
    · subst h0; simp
    · by_cases h1 : p = 1
      · subst h1
        rw [hb, haE]; simp
      · rw [if_neg h0, if_neg h1, mix_bit, hb, haE, if_pos (by omega)]
        have hu : uL s (5 * (p % 64) + p / 64) = s + 0x9e3779b9 * (p + 1) := by
          unfold uL aR aT; rw [hl5, hcell, if_pos (by omega), if_pos (by omega)]; omega
        have hRM : aRM (5 * (p % 64) + p / 64) = 0xffffffff := by
          unfold aRM; rw [hl5, if_pos (by omega)]
        have hz : zL s (5 * (p % 64) + p / 64) = gB 0xffffffff 0x7feb352d 0x846ca68b (s + 0x9e3779b9 * (p + 1)) := by
          unfold zL yL gB gA; rw [hu, hRM]
        rw [hz]
        generalize gB 0xffffffff 0x7feb352d 0x846ca68b (s + 0x9e3779b9 * (p + 1)) = z
        have hz1 : (z >>> 31 &&& 1 = 1) = (z.testBit 31 = true) := by
          rw [Nat.testBit_eq_decide_div_mod_eq, Nat.shiftRight_eq_div_pow, Nat.and_one_is_mod]; simp
        simp only [hz1, show p < 320 by omega, h0, decide_true, decide_false, Bool.true_and,
          Bool.or_false, Bool.decide_eq_true]
  · rw [List.getElem?_eq_none (by simp; omega)]
    by_cases h3 : p < 320
    · have h4 : 5 * (p % 64) + p / 64 = 5 * (p % 64) + 4 := by omega
      rw [h4, bL_four]; simp [show p ≠ 0 by omega]
    · simp [h3, show p ≠ 0 by omega]

theorem slow_correct : ∀ n, slow n = caSpecN n := by
  intro n
  have hs : Nat.land n (nat_lit 0xffffffff) < 2 ^ 32 := land_M32_lt n
  show run (row0 (Nat.land n (nat_lit 0xffffffff))) (Nat.shiftRight n (nat_lit 32))
    = encodeRow (iterRow (caSteps n) (initRowFor (caSeed n)))
  rw [row0_eq _ hs, run_eq _ (by simp [initRowFor, ruleWidth])]
  rfl


/-! ## The unrolled branches -/

set_option exponentiation.threshold 21000 in
theorem lit_cR : cR = eval% cR := by decide +kernel
set_option exponentiation.threshold 21000 in
theorem lit_cT : Nat.mul (nat_lit 0x9e3779b9) cT = eval% (Nat.mul (nat_lit 0x9e3779b9) cT) := by decide +kernel
set_option exponentiation.threshold 21000 in
theorem lit_cRM : cRM = eval% cRM := by decide +kernel
set_option exponentiation.threshold 21000 in
theorem lit_cE : cE = eval% cE := by decide +kernel
set_option exponentiation.threshold 21000 in
theorem lit_M : Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1)
    = eval% (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 319)) (nat_lit 1)) := by decide +kernel

theorem row0L_eq (s : Nat) : row0L s = row0 s := by
  unfold row0L mixAllL row0 mixAll
  rw [← lit_cR, ← lit_cT, ← lit_cRM, ← lit_cE, ← lit_M]

/- `fast2_eq : ∀ m, fast2 m = run m 2` (and `4`, `8`) by `rfl`, checked by the kernel. -/
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  for (nm, k) in [(`Submission.fast2_eq, 2), (`Submission.fast4_eq, 4), (`Submission.fast8_eq, 8)] do
    let f := Lean.mkConst (Lean.Name.mkStr `Submission s!"fast{k}")
    let ty ← withLocalDeclD `m (Lean.mkConst ``Nat) fun m => do
      mkForallFVars #[m] (← mkEq (mkApp f m) (mkApp2 (Lean.mkConst ``Submission.run) m (mkRawNatLit k)))
    let pf ← withLocalDeclD `m (Lean.mkConst ``Nat) fun m => do
      mkLambdaFVars #[m] (← mkEqRefl (mkApp f m))
    addDecl (.thmDecl { name := nm, levelParams := [], type := ty, value := pf })

/- `goK_eq : ∀ n, goK n = fastK (row0L (n &&& 0xffffffff))` by `rfl`, checked by the kernel. -/
set_option exponentiation.threshold 21000 in
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  for (nm, k) in [(`Submission.go2_eq, 2), (`Submission.go4_eq, 4), (`Submission.go8_eq, 8)] do
    let g := Lean.mkConst (Lean.Name.mkStr `Submission s!"go{k}")
    let f := Lean.mkConst (Lean.Name.mkStr `Submission s!"fast{k}")
    let ty ← withLocalDeclD `n (Lean.mkConst ``Nat) fun n => do
      let s := mkApp2 (Lean.mkConst ``Nat.land) n (mkRawNatLit 0xffffffff)
      mkForallFVars #[n] (← mkEq (mkApp g n) (mkApp f (mkApp (Lean.mkConst ``Submission.row0L) s)))
    let pf ← withLocalDeclD `n (Lean.mkConst ``Nat) fun n => do
      mkLambdaFVars #[n] (← mkEqRefl (mkApp g n))
    addDecl (.thmDecl { name := nm, levelParams := [], type := ty, value := pf })

theorem brec_eq (x y : Nat) (b : Bool) :
    Bool.rec (motive := fun _ => Nat) x y b = if b = true then y else x := by
  cases b <;> rfl

theorem impl_correct : ∀ n, impl n = caSpecN n := by
  intro n
  rw [← slow_correct n]
  have hslow : slow n = run (row0 (Nat.land n (nat_lit 0xffffffff))) (Nat.shiftRight n (nat_lit 32)) := rfl
  show Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (slow n) (go8 n)
        (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 8)))
      (go4 n) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 4)))
    (go2 n) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 2)) = _
  simp only [brec_eq, Nat.beq_eq]
  by_cases h2 : Nat.shiftRight n (nat_lit 32) = 2
  · rw [if_pos h2, go2_eq, fast2_eq, row0L_eq, hslow, h2]
  rw [if_neg h2]
  by_cases h4 : Nat.shiftRight n (nat_lit 32) = 4
  · rw [if_pos h4, go4_eq, fast4_eq, row0L_eq, hslow, h4]
  rw [if_neg h4]
  by_cases h8 : Nat.shiftRight n (nat_lit 32) = 8
  · rw [if_pos h8, go8_eq, fast8_eq, row0L_eq, hslow, h8]
  rw [if_neg h8]

/-- The compiled code `implC` agrees with `impl` on every input. -/
theorem implC_eq (n : Nat) : implC n = impl n := by
  show _ = Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (slow n) (go8 n)
        (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 8)))
      (go4 n) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 4)))
    (go2 n) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 2))
  simp only [implC, brec_eq, Nat.beq_eq]

end Submission
