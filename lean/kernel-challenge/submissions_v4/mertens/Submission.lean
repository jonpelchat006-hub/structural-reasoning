import Spec
import Lean

/-!
# Mertens function: the Möbius function in packed lanes

Every `m ≤ N` owns one `w`-bit lane (`B = 2^w`) of a few natural numbers, lane `N - m`. A rational
`ρ = Σ_{t ≥ 1} c(t) · B^(-t)` whose base-`B` digits are `0 ≤ c(t) < B` puts `c(m)` in lane `N - m` of
`⌊B^N · ρ⌋`; for `ρ = R / D` that is one shift and one kernel division, `(R <<< (w N)) / D`.
For example `B^N / (B^d - 1)` has a `1` in the lanes of the multiples of `d`.

`impl` has two branches.

## `fast`, for `N ≤ 840 < 29²`

Here `B = 2^11`, the primes `p ≤ √N` are among `2, 3, 5, 7` (`A`) and `11, 13, 17, 19, 23`, and the
numerators and denominators are numerals computed at elaboration time (`numeral%`) from the
formulas in the source.

* `C(m) = 1040 + #{p ≤ 23 : p ∣ m} - 6 · #{p ≤ 23 : p² ∣ m}`, from
  `ρ = 1040 / (B - 1) + Σ_p 1 / (B^p - 1) - 6 · Σ_p 1 / (B^(p²) - 1)`. An `m ≤ 840` has at most four
  prime factors `≤ 23` and at most two square ones, so `C(m) ∈ [1040, 1044]` if `m` is squarefree
  and `C(m) ∈ [1030, 1038]` otherwise: bits `4` and `10` are both set exactly for squarefree `m`
  (`(C >>> 4) &&& (C >>> 10)` is the lane vector of `[m squarefree]`, with nothing left over in
  the other bits), and bit `0` is the parity of the number of prime factors `≤ 23`.
* `W(m) = m / S(m) - gcd(m, 210) + 1023`, where `S(m)` is the product of the primes `11 … 23`
  dividing `m`, from
  `ρ = Σ_t (t + 1023) B^(-t) - Σ_{d ∣ 210} φ(d) / (B^d - 1) - Σ_{p = 11 … 23} (p - 1) B^p / (B^p - 1)²`:
  the first term has the digits `t + 1023`; by Gauss, `gcd(m, 210) = Σ_{d ∣ gcd(m, 210)} φ(d)`;
  and `B^p / (B^p - 1)² = Σ_k k B^(-k p)` has the digit `m / p` at the multiples of `p`, so the
  last sum turns `m` into `m / p` where `p ∣ m`. (Two of these primes divide `m ≤ 840` only when
  `m = p p' k` with `k ≤ 5`; then the digit is not `m / (p p')`, but it stays in `[0, 1024)`.)
  A squarefree `m` is `gcd(m, 210) · S(m) · q` with `q = 1` or a prime `≥ 29`, so bit `10` of
  `W(m)` is set exactly when `m` has a prime factor `> 23`.
* so for squarefree `m`, `μ(m) = -1` exactly when bit `0` of `C(m)` differs from bit `10` of
  `W(m)`. Two lane sums (`% (B - 1)`, as `B ≡ 1`) count `A₁ = #{m ≤ N squarefree}` and
  `A₂ = #{m ≤ N : μ(m) = -1}`, and `M(N) = A₁ - 2 A₂`.

`fast_ok` checks `fast N = slow N` for every `N ≤ 840` in the kernel (`decide +kernel`); `impl`
inlines the body of `fast`.

## `slow`, for every `N`

A lane-parallel sieve with `w = ⌊N / 1024⌋ + 11` and a 6-wheel over the candidates `2, 3, 6k ± 1`
up to `√N` (two Newton steps); a candidate `d` is skipped unless lane `d` of `S` is `1` (i.e. `d`
is prime). Per prime: the mask `B^N / ((B^p - 1) / (B - 1))`, the product of the processed primes
`S ← S + (S &&& mask) · (p - 1)`, their parity `^^^ B^N / (B^p - 1)`, and the square marks
`||| B^N / (B^(p²) - 1)`; at the end `m` has a prime factor `> √N` exactly when `S(m) < m`.
`slow_correct` is the general proof.

All numerals are raw `nat_lit`s or `numeral%` literals, and every operation is a GMP-accelerated
kernel `Nat` primitive.
-/

namespace Submission

open Lean Elab Term Meta in
/-- `share x := v; b` elaborates `b` with every `x` replaced by the same term `v` (one shared
expression node instead of a kernel `let`, so the kernel evaluates `v` once). -/
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

/-- `B^d - 1` for `B = 2^11` (a `numeral%` helper). -/
macro "bm% " d:term:max : term => `(Nat.pow 2048 $d - 1)

/-- The denominator of the `C` digits: `∏_{p ≤ 23} (B^(p²) - 1)` (a `numeral%` helper). -/
macro "denC%" : term => `(bm% 4 * bm% 9 * bm% 25 * bm% 49 * bm% 121 * bm% 169 * bm% 289 *
  bm% 361 * bm% 529)

/-- The denominator of the `W` digits: `(B^210 - 1) (B - 1) ∏_{p = 11 … 23} (B^p - 1)²`
(a `numeral%` helper). -/
macro "denW%" : term => `(bm% 210 * bm% 1 * (bm% 11 * bm% 11) * (bm% 13 * bm% 13) *
  (bm% 17 * bm% 17) * (bm% 19 * bm% 19) * (bm% 23 * bm% 23))


open Finset

/-! ## Implementation -/
def upd (Q Bm1 b dm1 S P NS : Nat) (k : Nat → Nat → Nat → Int) : Int :=
  k (Nat.add S (Nat.mul (Nat.land S (Nat.mul (Nat.div Q (Nat.sub b (nat_lit 1))) Bm1)) dm1))
    (Nat.xor P (Nat.div Q (Nat.sub b (nat_lit 1))))
    (Nat.lor NS (Nat.div Q (Nat.sub (Nat.pow b (Nat.add dm1 (nat_lit 1))) (nat_lit 1))))
def step (Q B Bm1 b dm1 S P NS : Nat) (k : Nat → Nat → Nat → Int) : Int :=
  Nat.rec (motive := fun _ => Int) (upd Q Bm1 b dm1 S P NS k) (fun _ _ => k S P NS)
    (Nat.sub (Nat.mod (Nat.div S (Nat.div Q b)) B) (nat_lit 1))
def wheel (Q B Bm1 B2 B6 : Nat) (fin : Nat → Nat → Nat → Int) :
    Nat → Nat → Nat → Nat → Nat → Nat → Int :=
  fun K => Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat → Nat → Int)
    (fun _ _ S P NS => fin S P NS)
    (fun _ ih b dm1 S P NS => step Q B Bm1 b dm1 S P NS (fun S P NS =>
       step Q B Bm1 (Nat.mul b B2) (Nat.add dm1 (nat_lit 2)) S P NS (fun S P NS =>
         ih (Nat.mul b B6) (Nat.add dm1 (nat_lit 6)) S P NS))) K
def fin (N B Bm1 w ones S P NS : Nat) : Int :=
  let L := Nat.land (Nat.shiftRight (Nat.add (Nat.sub (Nat.div (Nat.sub (Nat.mul B ones) N) Bm1) S)
    (Nat.mul (Nat.sub (Nat.shiftRight B (nat_lit 1)) (nat_lit 1)) ones)) (Nat.sub w (nat_lit 1))) ones
  let O := Nat.xor P L
  Int.subNatNat (Nat.sub N (Nat.mod NS Bm1)) (Nat.mul (nat_lit 2) (Nat.mod (Nat.sub O (Nat.land O NS)) Bm1))
def sqStep (N x : Nat) : Nat := Nat.shiftRight (Nat.add x (Nat.div N x)) (nat_lit 1)
def go (N w B Q : Nat) : Int :=
  let Bm1 := Nat.sub B (nat_lit 1)
  let ones := Nat.div Q Bm1
  let B2 := Nat.mul B B
  let B3 := Nat.mul B2 B
  upd Q Bm1 B2 (nat_lit 1) ones (nat_lit 0) (nat_lit 0) (fun S P NS =>
    upd Q Bm1 B3 (nat_lit 2) S P NS (fun S P NS =>
      wheel Q B Bm1 B2 (Nat.mul B3 B3) (fin N B Bm1 w ones)
        (Nat.div (Nat.add (sqStep N (sqStep N (Nat.add (Nat.shiftRight N (nat_lit 6)) (nat_lit 16))))
          (nat_lit 1)) (nat_lit 6))
        (Nat.mul B3 B2) (nat_lit 4) S P NS))
def slow (N : Nat) : Int :=
  go N (Nat.add (Nat.shiftRight N (nat_lit 10)) (nat_lit 11))
    (Nat.shiftLeft (nat_lit 1) (Nat.add (Nat.shiftRight N (nat_lit 10)) (nat_lit 11)))
    (Nat.pow (Nat.shiftLeft (nat_lit 1) (Nat.add (Nat.shiftRight N (nat_lit 10)) (nat_lit 11))) N)

set_option exponentiation.threshold 600 in
/-- `M(N)` for `N ≤ 840` (see the module doc). -/
def fast (N : Nat) : Int :=
  share N11 := Nat.mul N (nat_lit 11);
  -- the lanes `C(m) = 1040 + #{p ≤ 23 : p ∣ m} - 6 · #{p ≤ 23 : p² ∣ m}`:
  -- `ρ = 1040 / (B - 1) + Σ_p 1 / (B^p - 1) - 6 · Σ_p 1 / (B^(p²) - 1)`, times `denC`
  share C := Nat.div (Nat.shiftLeft (numeral% (
      1040 * (denC% / bm% 1) + denC% / bm% 2 + denC% / bm% 3 + denC% / bm% 5 + denC% / bm% 7 +
      denC% / bm% 11 + denC% / bm% 13 + denC% / bm% 17 + denC% / bm% 19 + denC% / bm% 23 -
      6 * (denC% / bm% 4 + denC% / bm% 9 + denC% / bm% 25 + denC% / bm% 49 + denC% / bm% 121 +
        denC% / bm% 169 + denC% / bm% 289 + denC% / bm% 361 + denC% / bm% 529)))
    N11) (numeral% denC%);
  -- the lanes `W(m) = m / S(m) - gcd(m, 210) + 1023`: `ρ = Σ_t (t + 1023) B^(-t) -
  -- Σ_{d ∣ 210} φ(d) / (B^d - 1) - Σ_{p = 11 … 23} (p - 1) B^p / (B^p - 1)²`, times `denW`,
  -- where `Σ_t (t + 1023) B^(-t) = (B + 1023 (B - 1)) / (B - 1)² = 2096129 / (B - 1)²`
  share W := Nat.div (Nat.shiftLeft (numeral% (2096129 * (denW% / (bm% 1 * bm% 1)) -
      (denW% / bm% 1 + denW% / bm% 2 + 2 * (denW% / bm% 3) + 4 * (denW% / bm% 5) +
       2 * (denW% / bm% 6) + 6 * (denW% / bm% 7) + 4 * (denW% / bm% 10) +
       6 * (denW% / bm% 14) + 8 * (denW% / bm% 15) + 12 * (denW% / bm% 21) +
       8 * (denW% / bm% 30) + 24 * (denW% / bm% 35) + 12 * (denW% / bm% 42) +
       24 * (denW% / bm% 70) + 48 * (denW% / bm% 105) + 48 * (denW% / bm% 210)) -
      (10 * Nat.pow 2048 11 * (denW% / (bm% 11 * bm% 11)) +
       12 * Nat.pow 2048 13 * (denW% / (bm% 13 * bm% 13)) +
       16 * Nat.pow 2048 17 * (denW% / (bm% 17 * bm% 17)) +
       18 * Nat.pow 2048 19 * (denW% / (bm% 19 * bm% 19)) +
       22 * Nat.pow 2048 23 * (denW% / (bm% 23 * bm% 23)))))
    N11) (numeral% denW%);
  -- `[m squarefree]` (bits `4` and `10` of `C(m)`)
  share SF := Nat.land (Nat.shiftRight C (nat_lit 4)) (Nat.shiftRight C (nat_lit 10));
  -- `A₁ = #{m ≤ N squarefree}` and `2 A₂ = 2 · #{m ≤ N : μ(m) = -1}`
  share A1 := Nat.mod SF (nat_lit 2047);
  share A2 := Nat.shiftLeft (Nat.mod (Nat.land (Nat.xor C (Nat.shiftRight W (nat_lit 10))) SF)
    (nat_lit 2047)) (nat_lit 1);
  Nat.rec (motive := fun _ => Int) (Int.ofNat (Nat.sub A1 A2)) (fun k _ => Int.negSucc k)
    (Nat.sub A2 A1)

set_option exponentiation.threshold 600 in
/-- `fast` (inlined) for `N ≤ 840`, `slow` otherwise. The branches are closed functions of `N`
(applied after the test), so unfolding `impl` does not rebuild them. -/
def impl (N : Nat) : Int :=
  Nat.rec (motive := fun _ => Nat → Int) (fun N =>
    share N11 := Nat.mul N (nat_lit 11);
    -- the lanes `C(m) = 1040 + #{p ≤ 23 : p ∣ m} - 6 · #{p ≤ 23 : p² ∣ m}`:
    -- `ρ = 1040 / (B - 1) + Σ_p 1 / (B^p - 1) - 6 · Σ_p 1 / (B^(p²) - 1)`, times `denC`
    share C := Nat.div (Nat.shiftLeft (numeral% (
        1040 * (denC% / bm% 1) + denC% / bm% 2 + denC% / bm% 3 + denC% / bm% 5 + denC% / bm% 7 +
      denC% / bm% 11 + denC% / bm% 13 + denC% / bm% 17 + denC% / bm% 19 + denC% / bm% 23 -
        6 * (denC% / bm% 4 + denC% / bm% 9 + denC% / bm% 25 + denC% / bm% 49 + denC% / bm% 121 +
        denC% / bm% 169 + denC% / bm% 289 + denC% / bm% 361 + denC% / bm% 529)))
      N11) (numeral% denC%);
    -- the lanes `W(m) = m / S(m) - gcd(m, 210) + 1023`: `ρ = Σ_t (t + 1023) B^(-t) -
    -- Σ_{d ∣ 210} φ(d) / (B^d - 1) - Σ_{p = 11 … 23} (p - 1) B^p / (B^p - 1)²`, times `denW`,
    -- where `Σ_t (t + 1023) B^(-t) = (B + 1023 (B - 1)) / (B - 1)² = 2096129 / (B - 1)²`
    share W := Nat.div (Nat.shiftLeft (numeral% (2096129 * (denW% / (bm% 1 * bm% 1)) -
        (denW% / bm% 1 + denW% / bm% 2 + 2 * (denW% / bm% 3) + 4 * (denW% / bm% 5) +
       2 * (denW% / bm% 6) + 6 * (denW% / bm% 7) + 4 * (denW% / bm% 10) +
       6 * (denW% / bm% 14) + 8 * (denW% / bm% 15) + 12 * (denW% / bm% 21) +
       8 * (denW% / bm% 30) + 24 * (denW% / bm% 35) + 12 * (denW% / bm% 42) +
       24 * (denW% / bm% 70) + 48 * (denW% / bm% 105) + 48 * (denW% / bm% 210)) -
        (10 * Nat.pow 2048 11 * (denW% / (bm% 11 * bm% 11)) +
       12 * Nat.pow 2048 13 * (denW% / (bm% 13 * bm% 13)) +
       16 * Nat.pow 2048 17 * (denW% / (bm% 17 * bm% 17)) +
       18 * Nat.pow 2048 19 * (denW% / (bm% 19 * bm% 19)) +
       22 * Nat.pow 2048 23 * (denW% / (bm% 23 * bm% 23)))))
      N11) (numeral% denW%);
    -- `[m squarefree]` (bits `4` and `10` of `C(m)`)
    share SF := Nat.land (Nat.shiftRight C (nat_lit 4)) (Nat.shiftRight C (nat_lit 10));
    -- `A₁ = #{m ≤ N squarefree}` and `2 A₂ = 2 · #{m ≤ N : μ(m) = -1}`
    share A1 := Nat.mod SF (nat_lit 2047);
    share A2 := Nat.shiftLeft (Nat.mod (Nat.land (Nat.xor C (Nat.shiftRight W (nat_lit 10))) SF)
      (nat_lit 2047)) (nat_lit 1);
    Nat.rec (motive := fun _ => Int) (Int.ofNat (Nat.sub A1 A2)) (fun k _ => Int.negSucc k)
      (Nat.sub A2 A1)
    ) (fun _ _ N => slow N) (Nat.sub N (nat_lit 840)) N

/-! ## Lane encodings -/

section Enc

variable (w : Nat)

/-- Lane `i` (of `w` bits) holds `a i`. -/
def enc (a : Nat → Nat) (L : Nat) : Nat := ∑ i ∈ range L, a i * 2 ^ (w * i)

theorem enc_succ (a : Nat → Nat) (L : Nat) :
    enc w a (L + 1) = a L <<< (w * L) + enc w a L := by
  unfold enc
  rw [sum_range_succ, Nat.shiftLeft_eq, Nat.add_comm]

theorem enc_lt (a : Nat → Nat) : ∀ L, (∀ m, m < L → a m < 2 ^ w) → enc w a L < 2 ^ (w * L)
  | 0, _ => by simp [enc]
  | L + 1, h => by
    rw [enc_succ, Nat.shiftLeft_eq]
    have h1 := enc_lt a L (fun m hm => h m (by omega))
    have h2 : a L + 1 ≤ 2 ^ w := h L (by omega)
    have h3 : (a L + 1) * 2 ^ (w * L) ≤ 2 ^ w * 2 ^ (w * L) := Nat.mul_le_mul_right _ h2
    rw [Nat.add_mul, Nat.one_mul] at h3
    have e : 2 ^ (w * (L + 1)) = 2 ^ w * 2 ^ (w * L) := by
      rw [Nat.mul_succ, pow_add, Nat.mul_comm]
    rw [e]
    omega

theorem enc_congr {a b : Nat → Nat} (L : Nat) (h : ∀ m, m < L → a m = b m) : enc w a L = enc w b L := by
  unfold enc
  apply sum_congr rfl
  intro m hm
  rw [h m (mem_range.mp hm)]

theorem enc_add (a b : Nat → Nat) (L : Nat) :
    enc w a L + enc w b L = enc w (fun m => a m + b m) L := by
  unfold enc
  rw [← sum_add_distrib]
  apply sum_congr rfl
  intro m _
  ring

theorem enc_mul (a : Nat → Nat) (c L : Nat) : enc w a L * c = enc w (fun m => a m * c) L := by
  unfold enc
  rw [sum_mul]
  apply sum_congr rfl
  intro m _
  ring

theorem enc_sub (a b : Nat → Nat) (L : Nat) (h : ∀ m, m < L → b m ≤ a m) :
    enc w a L - enc w b L = enc w (fun m => a m - b m) L := by
  have e : enc w a L = enc w (fun m => a m - b m) L + enc w b L := by
    rw [enc_add]
    apply enc_congr
    intro m hm
    have := h m hm
    omega
  omega

theorem bits_split (op : Bool → Bool → Bool) (f : Nat → Nat → Nat)
    (hf : ∀ x y i, (f x y).testBit i = op (x.testBit i) (y.testBit i)) (hop : op false false = false)
    (a b x y k : Nat) (hx : x < 2 ^ k) (hy : y < 2 ^ k) :
    f (a <<< k ||| x) (b <<< k ||| y) = (f a b) <<< k ||| f x y := by
  apply Nat.eq_of_testBit_eq
  intro i
  simp only [hf, Nat.testBit_or, Nat.testBit_shiftLeft]
  by_cases h : k ≤ i
  · have hle : 2 ^ k ≤ 2 ^ i := Nat.pow_le_pow_right (by omega) h
    have hx' : x.testBit i = false := Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hx hle)
    have hy' : y.testBit i = false := Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hy hle)
    simp [hx', hy', h, hop]
  · simp [show ¬ i ≥ k by omega]

/-- Any bitwise operation that maps `(0, 0)` to `0` acts lane by lane. -/
theorem enc_bitwise (op : Bool → Bool → Bool) (f : Nat → Nat → Nat)
    (hf : ∀ x y i, (f x y).testBit i = op (x.testBit i) (y.testBit i)) (hop : op false false = false)
    (hlt : ∀ x y, x < 2 ^ w → y < 2 ^ w → f x y < 2 ^ w)
    (a b : Nat → Nat) : ∀ L, (∀ m, m < L → a m < 2 ^ w) → (∀ m, m < L → b m < 2 ^ w) →
    f (enc w a L) (enc w b L) = enc w (fun m => f (a m) (b m)) L
  | 0, _, _ => by
    simp only [enc, range_zero, sum_empty]
    apply Nat.eq_of_testBit_eq; intro i; rw [hf]; simp [hop]
  | L + 1, ha, hb => by
    have ha' : ∀ m, m < L → a m < 2 ^ w := fun m hm => ha m (by omega)
    have hb' : ∀ m, m < L → b m < 2 ^ w := fun m hm => hb m (by omega)
    rw [enc_succ, enc_succ, enc_succ,
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w a L ha'),
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w b L hb'),
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w _ L (fun m hm => hlt _ _ (ha' m hm) (hb' m hm))),
      bits_split op f hf hop _ _ _ _ _ (enc_lt w a L ha') (enc_lt w b L hb'),
      enc_bitwise op f hf hop hlt a b L ha' hb']

theorem enc_and (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ w)
    (hb : ∀ m, m < L → b m < 2 ^ w) :
    enc w a L &&& enc w b L = enc w (fun m => a m &&& b m) L :=
  enc_bitwise w (· && ·) (· &&& ·) (fun x y i => Nat.testBit_and x y i) rfl
    (fun _ _ hx _ => Nat.lt_of_le_of_lt Nat.and_le_left hx) a b L ha hb

theorem enc_xor (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ w)
    (hb : ∀ m, m < L → b m < 2 ^ w) :
    enc w a L ^^^ enc w b L = enc w (fun m => a m ^^^ b m) L :=
  enc_bitwise w (· ^^ ·) (· ^^^ ·) (fun x y i => Nat.testBit_xor x y i) rfl
    (fun _ _ hx hy => Nat.xor_lt_two_pow hx hy) a b L ha hb

theorem enc_or (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ w)
    (hb : ∀ m, m < L → b m < 2 ^ w) :
    enc w a L ||| enc w b L = enc w (fun m => a m ||| b m) L :=
  enc_bitwise w (· || ·) (· ||| ·) (fun x y i => Nat.testBit_or x y i) rfl
    (fun _ _ hx hy => Nat.or_lt_two_pow hx hy) a b L ha hb

/-- The lane sum is the value modulo `2^w − 1`. -/
theorem enc_mod (a : Nat → Nat) (L : Nat) (hw : 2 ≤ w) :
    enc w a L % (2 ^ w - 1) = (∑ m ∈ range L, a m) % (2 ^ w - 1) := by
  unfold enc
  have h4 : 4 ≤ 2 ^ w := by
    calc 4 = 2 ^ 2 := by norm_num
      _ ≤ 2 ^ w := Nat.pow_le_pow_right (by omega) hw
  have hone : ∀ m, 2 ^ (w * m) % (2 ^ w - 1) = 1 := by
    intro m
    have hb : 2 ^ w % (2 ^ w - 1) = 1 := by
      obtain ⟨t, ht⟩ : ∃ t, 2 ^ w = t + 1 := ⟨2 ^ w - 1, by omega⟩
      rw [ht, Nat.add_sub_cancel, Nat.add_mod_left]
      exact Nat.mod_eq_of_lt (by omega)
    rw [pow_mul, Nat.pow_mod, hb, one_pow]
    exact Nat.mod_eq_of_lt (by omega)
  rw [sum_nat_mod, Finset.sum_nat_mod (range L) (2 ^ w - 1) a]
  congr 1
  apply sum_congr rfl
  intro m _
  rw [Nat.mul_mod, hone, Nat.mul_one, Nat.mod_mod]

/-- Bit `r < w` of lane `q`. -/
theorem enc_tb (hw : 1 ≤ w) (a : Nat → Nat) (q r : Nat) (hr : r < w) :
    ∀ L, (∀ m, m < L → a m < 2 ^ w) →
    (enc w a L).testBit (w * q + r) = (decide (q < L) && (a q).testBit r)
  | 0, _ => by simp [enc]
  | L + 1, h => by
    have h' : ∀ m, m < L → a m < 2 ^ w := fun m hm => h m (by omega)
    rw [enc_succ, Nat.shiftLeft_add_eq_or_of_lt (enc_lt w a L h'), Nat.testBit_or,
      Nat.testBit_shiftLeft, enc_tb hw a q r hr L h']
    rcases Nat.lt_trichotomy q L with hlt | heq | hgt
    · have : w * q + r < w * L := by
        have : w * (q + 1) ≤ w * L := Nat.mul_le_mul_left _ hlt
        rw [Nat.mul_succ] at this; omega
      simp [show ¬ (w * q + r ≥ w * L) by omega, hlt, show q < L + 1 by omega]
    · subst heq
      simp
    · have h1 : w * L + w ≤ w * q := by
        have : w * (L + 1) ≤ w * q := Nat.mul_le_mul_left _ hgt
        rw [Nat.mul_succ] at this; exact this
      have h3 : (a L).testBit (w * q + r - w * L) = false :=
        Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (h L (by omega))
          (Nat.pow_le_pow_right (by omega) (by omega)))
      simp [h3, show ¬ (q < L) by omega, show ¬ (q < L + 1) by omega]

/-- Shift every lane right by `s < w` and keep only bit `0` where `g` says so. -/
theorem enc_shr_and (hw : 1 ≤ w) (f g : Nat → Nat) (s L : Nat) (hs : s < w)
    (hf : ∀ m, m < L → f m < 2 ^ w) (hg : ∀ m, g m ≤ 1) :
    (enc w f L >>> s) &&& enc w g L = enc w (fun m => (f m >>> s) &&& g m) L := by
  have hg' : ∀ m, m < L → g m < 2 ^ w := fun m _ =>
    Nat.lt_of_le_of_lt (hg m) (Nat.one_lt_two_pow (by omega))
  have hfg : ∀ m, m < L → (f m >>> s) &&& g m < 2 ^ w := fun m hm =>
    Nat.lt_of_le_of_lt Nat.and_le_right (hg' m hm)
  have hgb : ∀ m j, (g m).testBit j = (decide (j = 0) && decide (g m = 1)) := by
    intro m j
    rcases Nat.le_one_iff_eq_zero_or_eq_one.mp (hg m) with h | h <;> rw [h]
    · simp
    · cases j with
      | zero => rfl
      | succ k => rw [Nat.testBit_succ]; simp
  apply Nat.eq_of_testBit_eq
  intro p
  obtain ⟨q, r, hr, rfl⟩ : ∃ q r, r < w ∧ p = w * q + r :=
    ⟨p / w, p % w, Nat.mod_lt _ (by omega), (Nat.div_add_mod p w).symm⟩
  rw [Nat.testBit_and, Nat.testBit_shiftRight, enc_tb w hw g q r hr L hg', enc_tb w hw _ q r hr L hfg,
    Nat.testBit_and, Nat.testBit_shiftRight, hgb]
  by_cases hr0 : r = 0
  · subst hr0
    rw [show s + (w * q + 0) = w * q + s by omega, enc_tb w hw f q s hs L hf]
    simp only [Nat.add_zero]
    cases decide (q < L) <;> simp
  · simp [hr0]

theorem enc_split (a : Nat → Nat) (k n : Nat) :
    enc w a (k + n) = enc w a k + (2 ^ w) ^ k * enc w (fun i => a (k + i)) n := by
  unfold enc
  rw [sum_range_add, mul_sum]
  congr 1
  apply sum_congr rfl
  intro i _
  rw [← pow_mul, show w * (k + i) = w * k + w * i by ring, pow_add]
  ring

theorem enc_succ' (b : Nat → Nat) (n : Nat) :
    enc w b (n + 1) = b 0 + 2 ^ w * enc w (fun i => b (i + 1)) n := by
  unfold enc
  rw [sum_range_succ', mul_sum, Nat.add_comm]
  simp only [Nat.mul_zero, pow_zero, Nat.mul_one]
  congr 1
  apply sum_congr rfl
  intro i _
  rw [show w * (i + 1) = w + w * i by ring, pow_add]
  ring

/-- Lane extraction: lane `k` is `(x / B^k) % B`. -/
theorem enc_lane (a : Nat → Nat) (L k : Nat) (hk : k < L) (ha : ∀ m, m < L → a m < 2 ^ w) :
    enc w a L / (2 ^ w) ^ k % 2 ^ w = a k := by
  obtain ⟨t, rfl⟩ : ∃ t, L = k + (t + 1) := ⟨L - k - 1, by omega⟩
  have hlow : enc w a k < (2 ^ w) ^ k := by
    have := enc_lt w a k (fun m hm => ha m (by omega))
    rwa [← pow_mul]
  rw [enc_split, enc_succ', Nat.add_zero, Nat.add_comm, Nat.mul_add_div (by positivity),
    Nat.div_eq_of_lt hlow, Nat.add_zero, Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt (ha k (by omega))]

end Enc

/-! ## Closed forms -/

theorem geom_mul (q : Nat) (hq : 1 ≤ q) :
    ∀ J, (q - 1) * (∑ j ∈ range J, q ^ j) + 1 = q ^ J := by
  intro J
  induction J with
  | zero => simp
  | succ J ih =>
    obtain ⟨r, rfl⟩ : ∃ r, q = r + 1 := ⟨q - 1, by omega⟩
    rw [Nat.add_sub_cancel] at ih ⊢
    rw [sum_range_succ, pow_succ, ← ih]
    ring

theorem four_le (w : Nat) (hw : 2 ≤ w) : 4 ≤ 2 ^ w :=
  calc 4 = 2 ^ 2 := by norm_num
    _ ≤ 2 ^ w := Nat.pow_le_pow_right (by omega) hw

/-- One division marks the multiples `m ≥ d` of `d` (lane `N - m`). -/
theorem marks_eq (w N d : Nat) (hw : 2 ≤ w) (hd : 1 ≤ d) :
    (2 ^ w) ^ N / ((2 ^ w) ^ d - 1) = enc w (fun i => if i < N ∧ d ∣ N - i then 1 else 0) (N + 1) := by
  have hB := four_le w hw
  obtain ⟨T, r, hr, hN⟩ : ∃ T r, r < d ∧ N = r + d * T :=
    ⟨N / d, N % d, Nat.mod_lt _ (by omega), (Nat.mod_add_div N d).symm⟩
  generalize hBdef : 2 ^ w = B at hB
  have hBd : B ≤ B ^ d := by
    calc B = B ^ 1 := (pow_one B).symm
      _ ≤ B ^ d := Nat.pow_le_pow_right (by omega) hd
  have hg := geom_mul (B ^ d) (by omega) T
  have hBN : B ^ N = (B ^ d - 1) * (B ^ r * ∑ j ∈ range T, (B ^ d) ^ j) + B ^ r := by
    conv_lhs => rw [hN, pow_add, pow_mul, ← hg]
    ring
  have hrlt : B ^ r < B ^ d - 1 := by
    have h1 : B ^ r * B ≤ B ^ d := by
      rw [← pow_succ]; exact Nat.pow_le_pow_right (by omega) (by omega)
    have h2 : 0 < B ^ r := by positivity
    have h3 : B ^ r * 4 ≤ B ^ r * B := Nat.mul_le_mul_left _ hB
    omega
  -- the multiples, as `i = r + d t` with `t < T`
  have hmem : ∀ i, (i < N ∧ d ∣ N - i) → ∃ t, t < T ∧ i = r + d * t := by
    rintro i ⟨h1, ⟨u, hu⟩⟩
    have hu1 : 1 ≤ u := by
      rcases Nat.eq_zero_or_pos u with h | h
      · subst h; omega
      · exact h
    have huT : u ≤ T := by
      by_contra hc
      have : d * (T + 1) ≤ d * u := Nat.mul_le_mul_left _ (by omega)
      rw [Nat.mul_succ] at this; omega
    refine ⟨T - u, by omega, ?_⟩
    rw [Nat.mul_sub]
    have : d * u ≤ d * T := Nat.mul_le_mul_left _ huT
    omega
  rw [hBN, Nat.mul_add_div (by omega), Nat.div_eq_of_lt hrlt, Nat.add_zero, mul_sum]
  unfold enc
  simp only [ite_mul, one_mul, zero_mul]
  rw [← sum_filter]
  symm
  apply sum_nbij' (fun i => (i - r) / d) (fun t => r + d * t)
  · intro i hi
    simp only [mem_filter, mem_range] at hi ⊢
    obtain ⟨t, ht, rfl⟩ := hmem i hi.2
    rw [Nat.add_sub_cancel_left, Nat.mul_div_cancel_left _ (by omega)]
    exact ht
  · intro t ht
    simp only [mem_filter, mem_range] at ht ⊢
    have h1 : d * t < d * T := Nat.mul_lt_mul_of_pos_left ht (by omega)
    refine ⟨by omega, by omega, ⟨T - t, ?_⟩⟩
    rw [Nat.mul_sub]; omega
  · intro i hi
    simp only [mem_filter, mem_range] at hi
    obtain ⟨t, _, rfl⟩ := hmem i hi.2
    show r + d * ((r + d * t - r) / d) = r + d * t
    rw [Nat.add_sub_cancel_left, Nat.mul_div_cancel_left _ (by omega)]
  · intro t _
    show (r + d * t - r) / d = t
    rw [Nat.add_sub_cancel_left, Nat.mul_div_cancel_left _ (by omega)]
  · intro i hi
    simp only [mem_filter, mem_range] at hi
    obtain ⟨t, _, rfl⟩ := hmem i hi.2
    rw [Nat.add_sub_cancel_left, Nat.mul_div_cancel_left _ (by omega), ← pow_mul, ← pow_add, ← hBdef,
      ← pow_mul]

/-- Lanes holding `N - i` (i.e. the number `m` itself). -/
theorem lanes_m (w N : Nat) (hw : 2 ≤ w) :
    (2 ^ w * enc w (fun i => if i < N then 1 else 0) (N + 1) - N) / (2 ^ w - 1)
      = enc w (fun i => if i < N then N - i else 0) (N + 1) := by
  have hB := four_le w hw
  have hind : ∀ (g : Nat → Nat), enc w (fun i => if i < N then g i else 0) (N + 1)
      = ∑ i ∈ range N, g i * (2 ^ w) ^ i := by
    intro g
    unfold enc
    rw [sum_range_succ]
    simp only [lt_irrefl, ↓reduceIte, zero_mul, Nat.add_zero]
    apply sum_congr rfl
    intro i hi
    simp only [mem_range] at hi
    simp only [hi, ↓reduceIte, pow_mul]
  rw [hind, hind]
  obtain ⟨c, hc⟩ : ∃ c, 2 ^ w = c + 1 := ⟨2 ^ w - 1, by omega⟩
  rw [hc, Nat.add_sub_cancel]
  -- `c · Σ (N - i)(c+1)^i + N = (c+1) Σ (c+1)^i`
  have key : ∀ N, c * (∑ i ∈ range N, (N - i) * (c + 1) ^ i) + N = (c + 1) * ∑ i ∈ range N, 1 * (c + 1) ^ i := by
    intro N
    induction N with
    | zero => simp
    | succ N ih =>
      have hg := geom_mul (c + 1) (by omega) N
      rw [Nat.add_sub_cancel] at hg
      rw [sum_range_succ, sum_range_succ, show N + 1 - N = 1 by omega]
      have e : ∑ i ∈ range N, (N + 1 - i) * (c + 1) ^ i
          = ∑ i ∈ range N, (N - i) * (c + 1) ^ i + ∑ i ∈ range N, (c + 1) ^ i := by
        rw [← sum_add_distrib]
        apply sum_congr rfl
        intro i hi
        rw [show N + 1 - i = (N - i) + 1 by have := mem_range.mp hi; omega]
        ring
      rw [e]
      simp only [one_mul] at ih ⊢
      nlinarith [ih, hg]
  have hk := key N
  rw [← hk, Nat.add_sub_cancel, Nat.mul_div_cancel_left _ (by omega)]

/-! ## Number theory of the lane values -/

/-- The processed primes (`< c`) dividing `m`. -/
def Pset (c m : Nat) : Finset Nat := (range c).filter (fun p => p.Prime ∧ p ∣ m)

def Sv (c m : Nat) : Nat := ∏ p ∈ Pset c m, p
def Pv (c m : Nat) : Nat := (Pset c m).card % 2

open Classical in
noncomputable def NSv (c m : Nat) : Nat := if ∃ p, p < c ∧ p.Prime ∧ p * p ∣ m then 1 else 0

theorem Pset_succ (c m : Nat) :
    Pset (c + 1) m = if c.Prime ∧ c ∣ m then insert c (Pset c m) else Pset c m := by
  unfold Pset
  rw [range_add_one, filter_insert]

theorem not_mem_Pset (c m : Nat) : c ∉ Pset c m := by
  simp [Pset]

theorem Sv_succ (c m : Nat) : Sv (c + 1) m = if c.Prime ∧ c ∣ m then Sv c m * c else Sv c m := by
  unfold Sv
  rw [Pset_succ]
  split
  · rw [prod_insert (not_mem_Pset c m), Nat.mul_comm]
  · rfl

theorem Pv_succ (c m : Nat) :
    Pv (c + 1) m = Pv c m ^^^ (if c.Prime ∧ c ∣ m then 1 else 0) := by
  unfold Pv
  rw [Pset_succ]
  split
  · rw [card_insert_of_notMem (not_mem_Pset c m)]
    rcases Nat.mod_two_eq_zero_or_one (Pset c m).card with h | h
    · rw [h, show (0 : Nat) ^^^ 1 = 1 from rfl]; omega
    · rw [h, show (1 : Nat) ^^^ 1 = 0 from rfl]; omega
  · rw [Nat.xor_zero]

theorem NSv_succ (c m : Nat) :
    NSv (c + 1) m = NSv c m ||| (if c.Prime ∧ c * c ∣ m then 1 else 0) := by
  unfold NSv
  by_cases h1 : ∃ p, p < c ∧ p.Prime ∧ p * p ∣ m
  · rw [if_pos h1, if_pos (by obtain ⟨p, a, b, c⟩ := h1; exact ⟨p, by omega, b, c⟩)]
    split <;> rfl
  · rw [if_neg h1]
    by_cases h2 : c.Prime ∧ c * c ∣ m
    · rw [if_pos h2, if_pos ⟨c, by omega, h2.1, h2.2⟩]; rfl
    · rw [if_neg h2, if_neg]
      · rfl
      · rintro ⟨p, hp1, hp2, hp3⟩
        rcases Nat.lt_or_ge p c with h | h
        · exact h1 ⟨p, h, hp2, hp3⟩
        · exact h2 (by have : p = c := by omega
                       subst this; exact ⟨hp2, hp3⟩)

theorem Sv_dvd (c m : Nat) : Sv c m ∣ m := by
  unfold Sv
  apply Finset.prod_primes_dvd
  · intro p hp; simp only [Pset, mem_filter] at hp; exact hp.2.1.prime
  · intro p hp; simp only [Pset, mem_filter] at hp; exact hp.2.2

theorem Sv_pos (c m : Nat) : 1 ≤ Sv c m := by
  unfold Sv
  apply Nat.one_le_iff_ne_zero.mpr
  rw [prod_ne_zero_iff]
  intro p hp; simp only [Pset, mem_filter] at hp; exact hp.2.1.ne_zero

theorem Sv_le (c m : Nat) (hm : 1 ≤ m) : Sv c m ≤ m := Nat.le_of_dvd (by omega) (Sv_dvd c m)

theorem Pv_le (c m : Nat) : Pv c m ≤ 1 := by
  unfold Pv; have := Nat.mod_lt (Pset c m).card (show 0 < 2 by omega); omega

theorem NSv_le (c m : Nat) : NSv c m ≤ 1 := by unfold NSv; split <;> omega

/-- Lane `d` of `S` is `1` exactly when `d` is prime. -/
theorem Sv_self (d : Nat) (hd : 2 ≤ d) : Sv d d = 1 ↔ d.Prime := by
  constructor
  · intro h
    by_contra hnp
    have hmin := Nat.minFac_prime (show d ≠ 1 by omega)
    have hlt : d.minFac < d := (Nat.not_prime_iff_minFac_lt hd).mp hnp
    have hmem : d.minFac ∈ Pset d d := by
      simp only [Pset, mem_filter, mem_range]; exact ⟨hlt, hmin, Nat.minFac_dvd d⟩
    have hle : d.minFac ≤ Sv d d := by
      unfold Sv
      exact Finset.single_le_prod' (fun p hp => by
        simp only [Pset, mem_filter] at hp; exact hp.2.1.one_lt.le) hmem
    have := hmin.two_le
    omega
  · intro hp
    unfold Sv
    rw [show Pset d d = ∅ from by
      apply eq_empty_of_forall_notMem
      intro p hpm
      simp only [Pset, mem_filter, mem_range] at hpm
      obtain ⟨h1, h2, h3⟩ := hpm
      rcases hp.eq_one_or_self_of_dvd p h3 with h | h
      · exact h2.one_lt.ne' h
      · omega]
    rfl

/-- After all primes `< c` with `c² > N` are processed, the lanes determine `μ`. -/
theorem moebius_lane (c m N : Nat) (hm : 1 ≤ m) (hmN : m ≤ N) (hc : N < c * c) :
    (ArithmeticFunction.moebius m : Int) =
      if NSv c m = 1 then 0
      else if Pv c m ^^^ (if Sv c m < m then 1 else 0) = 1 then -1 else 1 := by
  have hm0 : m ≠ 0 := by omega
  -- squarefree ↔ no processed square divisor
  have hsq : NSv c m = 1 ↔ ¬ Squarefree m := by
    unfold NSv
    constructor
    · intro h
      split at h
      · rename_i hex
        obtain ⟨p, _, hp, hd⟩ := hex
        intro hsq
        have := Nat.isUnit_iff.mp (hsq p hd)
        exact hp.ne_one this
      · omega
    · intro hns
      rw [Nat.squarefree_iff_prime_squarefree] at hns
      push Not at hns
      obtain ⟨p, hp, hd⟩ := hns
      have hle := Nat.le_of_dvd (by omega) hd
      have hpc : p < c := by
        by_contra hc'
        have : c * c ≤ p * p := Nat.mul_le_mul (by omega) (by omega)
        omega
      rw [if_pos ⟨p, hpc, hp, hd⟩]
  by_cases hns : NSv c m = 1
  · rw [if_pos hns, ArithmeticFunction.moebius_eq_zero_of_not_squarefree (hsq.mp hns)]
  rw [if_neg hns]
  have hsqf : Squarefree m := by
    by_contra h; exact hns (hsq.mpr h)
  rw [ArithmeticFunction.moebius_apply_of_squarefree hsqf,
    ← (ArithmeticFunction.cardDistinctFactors_eq_cardFactors_iff_squarefree hm0).mpr hsqf,
    ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset,
    ← Nat.primeFactors.eq_1]
  -- split the prime factors at `c`
  have hPset : Pset c m = m.primeFactors.filter (· < c) := by
    ext p
    simp only [Pset, mem_filter, mem_range, Nat.mem_primeFactors]
    constructor
    · rintro ⟨h1, h2, h3⟩; exact ⟨⟨h2, h3, hm0⟩, h1⟩
    · rintro ⟨⟨h2, h3, _⟩, h1⟩; exact ⟨h1, h2, h3⟩
  set Lg := m.primeFactors.filter (fun p => ¬ p < c)
  have hcard : m.primeFactors.card = (Pset c m).card + Lg.card := by
    rw [hPset]
    exact (card_filter_add_card_filter_not (s := m.primeFactors) (fun p => p < c)).symm
  have hprod : Sv c m * ∏ p ∈ Lg, p = m := by
    unfold Sv
    rw [hPset, prod_filter_mul_prod_filter_not, Nat.prod_primeFactors_of_squarefree hsqf]
  -- at most one large prime factor
  have hL1 : Lg.card ≤ 1 := by
    rw [Finset.card_le_one]
    intro p hp q hq
    by_contra hpq
    simp only [Lg, mem_filter, Nat.mem_primeFactors] at hp hq
    have hcop : Nat.Coprime p q := (Nat.coprime_primes hp.1.1 hq.1.1).mpr hpq
    have hdvd : p * q ∣ m := hcop.mul_dvd_of_dvd_of_dvd hp.1.2.1 hq.1.2.1
    have hle := Nat.le_of_dvd (by omega) hdvd
    have : c * c ≤ p * q := Nat.mul_le_mul (by omega) (by omega)
    omega
  have hlarge : (Sv c m < m) ↔ Lg.card = 1 := by
    constructor
    · intro h
      rcases Nat.lt_or_ge Lg.card 1 with h0 | h0
      · have : Lg = ∅ := card_eq_zero.mp (by omega)
        rw [this, prod_empty, Nat.mul_one] at hprod
        omega
      · omega
    · intro h
      obtain ⟨q, hq⟩ := card_eq_one.mp h
      rw [hq, prod_singleton] at hprod
      have hqm : q ∈ Lg := by rw [hq]; exact mem_singleton_self q
      simp only [Lg, mem_filter, Nat.mem_primeFactors] at hqm
      have := hqm.1.1.two_le
      have := Sv_pos c m
      nlinarith
  rw [hcard]
  unfold Pv
  have h2 := Nat.mod_lt (Pset c m).card (show 0 < 2 by omega)
  by_cases hl : Sv c m < m
  · rw [if_pos hl, hlarge.mp hl]
    rcases Nat.mod_two_eq_zero_or_one (Pset c m).card with h | h
    · rw [h, show (0 : Nat) ^^^ 1 = 1 from rfl, if_pos rfl, pow_add, pow_one,
        Even.neg_one_pow (Nat.even_iff.mpr h)]
      ring
    · rw [h, show (1 : Nat) ^^^ 1 = 0 from rfl, if_neg (by omega), pow_add, pow_one,
        Odd.neg_one_pow (Nat.odd_iff.mpr h)]
      ring
  · have hl0 : Lg.card = 0 := by
      rcases Nat.lt_or_ge Lg.card 1 with h0 | h0
      · omega
      · exact absurd (hlarge.mpr (by omega)) hl
    rw [if_neg hl, hl0, Nat.add_zero, Nat.xor_zero]
    rcases Nat.mod_two_eq_zero_or_one (Pset c m).card with h | h
    · rw [h, if_neg (by omega), Even.neg_one_pow (Nat.even_iff.mpr h)]
    · rw [h, if_pos rfl, Odd.neg_one_pow (Nat.odd_iff.mpr h)]

/-! ## The sieve state as lane vectors -/

def sF (N c i : Nat) : Nat := if i < N then Sv c (N - i) else 0
def pF (N c i : Nat) : Nat := if i < N then Pv c (N - i) else 0
noncomputable def nF (N c i : Nat) : Nat := if i < N then NSv c (N - i) else 0
def ind (N d i : Nat) : Nat := if i < N ∧ d ∣ N - i then 1 else 0

theorem sF_le (N c i : Nat) : sF N c i ≤ N := by
  unfold sF; split
  · have := Sv_le c (N - i) (by omega); omega
  · omega

theorem pF_le (N c i : Nat) : pF N c i ≤ 1 := by unfold pF; split <;> [exact Pv_le _ _; omega]
theorem nF_le (N c i : Nat) : nF N c i ≤ 1 := by unfold nF; split <;> [exact NSv_le _ _; omega]
theorem ind_le (N d i : Nat) : ind N d i ≤ 1 := by unfold ind; split <;> omega

theorem lt_of_le_one {w x : Nat} (hw : 1 ≤ w) (h : x ≤ 1) : x < 2 ^ w :=
  Nat.lt_of_le_of_lt h (Nat.one_lt_two_pow (by omega))

/-- Nothing changes when `c` is not prime. -/
theorem state_nonprime (N c : Nat) (hc : ¬ c.Prime) :
    sF N (c + 1) = sF N c ∧ pF N (c + 1) = pF N c ∧ nF N (c + 1) = nF N c := by
  refine ⟨funext fun i => ?_, funext fun i => ?_, funext fun i => ?_⟩
  · unfold sF; simp only [Sv_succ, hc, false_and, ↓reduceIte]
  · unfold pF; simp only [Pv_succ, hc, false_and, ↓reduceIte, Nat.xor_zero]
  · unfold nF; simp only [NSv_succ, hc, false_and, ↓reduceIte, Nat.or_zero]

theorem marks_ind (w N d : Nat) (hw : 2 ≤ w) (hd : 1 ≤ d) :
    Nat.div ((2 ^ w) ^ N) (Nat.sub ((2 ^ w) ^ d) (nat_lit 1)) = enc w (ind N d) (N + 1) :=
  marks_eq w N d hw hd

/-- One prime (or a candidate beyond `N`): the masked multiply-add, the xor and the or. -/
theorem upd_eq (w N d : Nat) (hw : 2 ≤ w) (hN : N < 2 ^ w) (hd : 1 ≤ d) (hdp : d.Prime ∨ N < d)
    (k : Nat → Nat → Nat → Int) :
    upd ((2 ^ w) ^ N) (2 ^ w - 1) ((2 ^ w) ^ d) (d - 1)
      (enc w (sF N d) (N + 1)) (enc w (pF N d) (N + 1)) (enc w (nF N d) (N + 1)) k
    = k (enc w (sF N (d + 1)) (N + 1)) (enc w (pF N (d + 1)) (N + 1)) (enc w (nF N (d + 1)) (N + 1)) := by
  have hw1 : 1 ≤ w := by omega
  have hsl : ∀ i, i < N + 1 → sF N d i < 2 ^ w := fun i _ => Nat.lt_of_le_of_lt (sF_le N d i) hN
  have hdvd : ∀ i, i < N → d ∣ N - i → d.Prime := by
    intro i hi hdi
    rcases hdp with h | h
    · exact h
    · have := Nat.le_of_dvd (by omega) hdi; omega
  have hmask : ∀ i, ind N d i * (2 ^ w - 1) < 2 ^ w := by
    intro i; unfold ind; split <;> omega
  unfold upd
  rw [marks_ind w N d hw hd]
  congr 1
  · -- S
    show enc w (sF N d) (N + 1) + (enc w (sF N d) (N + 1) &&& enc w (ind N d) (N + 1) * (2 ^ w - 1)) * (d - 1)
      = enc w (sF N (d + 1)) (N + 1)
    rw [enc_mul, enc_and w _ _ _ hsl (fun i _ => hmask i), enc_mul, enc_add]
    apply enc_congr
    intro i _
    unfold ind sF
    by_cases hi : i < N
    · rw [if_pos hi, if_pos hi, Sv_succ]
      by_cases hd' : d ∣ N - i
      · have hp := hdvd i hi hd'
        rw [if_pos ⟨hi, hd'⟩, if_pos ⟨hp, hd'⟩, Nat.one_mul, Nat.and_two_pow_sub_one_eq_mod,
          Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt (Sv_le d (N - i) (by omega)) (by omega))]
        obtain ⟨e, rfl⟩ : ∃ e, d = e + 1 := ⟨d - 1, by omega⟩
        rw [Nat.add_sub_cancel]; ring
      · rw [if_neg (fun h => hd' h.2), if_neg (fun h => hd' h.2), Nat.zero_mul, Nat.and_zero,
          Nat.zero_mul, Nat.add_zero]
    · rw [if_neg hi, if_neg hi, if_neg (fun h => hi h.1)]; simp
  · -- P
    show enc w (pF N d) (N + 1) ^^^ enc w (ind N d) (N + 1) = enc w (pF N (d + 1)) (N + 1)
    rw [enc_xor w _ _ _ (fun i _ => lt_of_le_one hw1 (pF_le N d i))
      (fun i _ => lt_of_le_one hw1 (ind_le N d i))]
    apply enc_congr
    intro i _
    unfold ind pF
    by_cases hi : i < N
    · rw [if_pos hi, if_pos hi, Pv_succ]
      by_cases hd' : d ∣ N - i
      · rw [if_pos ⟨hi, hd'⟩, if_pos ⟨hdvd i hi hd', hd'⟩]
      · rw [if_neg (fun h => hd' h.2), if_neg (fun h => hd' h.2)]
    · rw [if_neg hi, if_neg hi, if_neg (fun h => hi h.1)]; rfl
  · -- NS
    show enc w (nF N d) (N + 1) ||| Nat.div ((2 ^ w) ^ N) (Nat.sub (((2 ^ w) ^ d) ^ (d - 1 + 1)) 1)
      = enc w (nF N (d + 1)) (N + 1)
    rw [Nat.sub_add_cancel hd, show ((2 ^ w) ^ d) ^ d = (2 ^ w) ^ (d * d) from (pow_mul _ _ _).symm,
      marks_ind w N (d * d) hw (Nat.one_le_iff_ne_zero.mpr
      (Nat.mul_ne_zero (by omega) (by omega))), enc_or w _ _ _ (fun i _ => lt_of_le_one hw1 (nF_le N d i))
      (fun i _ => lt_of_le_one hw1 (ind_le N (d * d) i))]
    apply enc_congr
    intro i _
    unfold ind nF
    by_cases hi : i < N
    · rw [if_pos hi, if_pos hi, NSv_succ]
      by_cases hd' : d * d ∣ N - i
      · rw [if_pos ⟨hi, hd'⟩, if_pos ⟨hdvd i hi (Dvd.dvd.trans (Dvd.intro d rfl) hd'), hd'⟩]
      · rw [if_neg (fun h => hd' h.2), if_neg (fun h => hd' h.2)]
    · rw [if_neg hi, if_neg hi, if_neg (fun h => hi h.1)]; rfl

/-- A wheel candidate: processed if prime (lane `d` of `S` is `1`), skipped otherwise. -/
theorem step_eq (w N d : Nat) (hw : 2 ≤ w) (hN : N < 2 ^ w) (hd : 2 ≤ d)
    (k : Nat → Nat → Nat → Int) :
    step ((2 ^ w) ^ N) (2 ^ w) (2 ^ w - 1) ((2 ^ w) ^ d) (d - 1)
      (enc w (sF N d) (N + 1)) (enc w (pF N d) (N + 1)) (enc w (nF N d) (N + 1)) k
    = k (enc w (sF N (d + 1)) (N + 1)) (enc w (pF N (d + 1)) (N + 1)) (enc w (nF N (d + 1)) (N + 1)) := by
  have hB : 0 < 2 ^ w := by positivity
  have hsl : ∀ i, i < N + 1 → sF N d i < 2 ^ w := fun i _ => Nat.lt_of_le_of_lt (sF_le N d i) hN
  unfold step
  rcases Nat.lt_or_ge N d with hNd | hdN
  · -- beyond `N`: the lane test reads `0`, and processing changes nothing
    have hq : (2 ^ w) ^ N / (2 ^ w) ^ d = 0 :=
      Nat.div_eq_of_lt (Nat.pow_lt_pow_right (Nat.one_lt_two_pow (by omega)) hNd)
    have hl : Nat.sub (Nat.mod (Nat.div (enc w (sF N d) (N + 1)) (Nat.div ((2 ^ w) ^ N) ((2 ^ w) ^ d))) (2 ^ w))
        (nat_lit 1) = 0 := by
      show (enc w (sF N d) (N + 1) / ((2 ^ w) ^ N / (2 ^ w) ^ d)) % 2 ^ w - 1 = 0
      rw [hq, Nat.div_zero, Nat.zero_mod]
    rw [hl]
    exact upd_eq w N d hw hN (by omega) (Or.inr hNd) k
  · have hq : (2 ^ w) ^ N / (2 ^ w) ^ d = (2 ^ w) ^ (N - d) := Nat.pow_div hdN hB
    have hlane : Nat.mod (Nat.div (enc w (sF N d) (N + 1)) (Nat.div ((2 ^ w) ^ N) ((2 ^ w) ^ d))) (2 ^ w)
        = Sv d d := by
      show (enc w (sF N d) (N + 1) / ((2 ^ w) ^ N / (2 ^ w) ^ d)) % 2 ^ w = _
      rw [hq, enc_lane w (sF N d) (N + 1) (N - d) (by omega) hsl]
      unfold sF
      rw [if_pos (by omega), show N - (N - d) = d by omega]
    rw [hlane]
    by_cases hp : d.Prime
    · rw [(Sv_self d hd).mpr hp]
      exact upd_eq w N d hw hN (by omega) (Or.inl hp) k
    · have h2 : 2 ≤ Sv d d := by
        have := Sv_pos d d
        have : Sv d d ≠ 1 := fun h => hp ((Sv_self d hd).mp h)
        omega
      obtain ⟨e, he⟩ : ∃ e, Nat.sub (Sv d d) (nat_lit 1) = e + 1 := ⟨Sv d d - 2, by show Sv d d - 1 = _; omega⟩
      rw [he]
      obtain ⟨h1, h2, h3⟩ := state_nonprime N d hp
      show k _ _ _ = _
      rw [h1, h2, h3]

theorem wheel_succ (Q B Bm1 B2 B6 : Nat) (fin : Nat → Nat → Nat → Int) (K b dm1 S P NS : Nat) :
    wheel Q B Bm1 B2 B6 fin (K + 1) b dm1 S P NS =
      step Q B Bm1 b dm1 S P NS (fun S P NS =>
        step Q B Bm1 (Nat.mul b B2) (Nat.add dm1 2) S P NS (fun S P NS =>
          wheel Q B Bm1 B2 B6 fin K (Nat.mul b B6) (Nat.add dm1 6) S P NS)) := rfl

theorem not_prime_mul {a b : Nat} (ha : 2 ≤ a) (hb : 2 ≤ b) : ¬ (a * b).Prime := by
  intro hp
  rcases hp.eq_one_or_self_of_dvd a (Dvd.intro b rfl) with h | h
  · omega
  · have : a * 1 < a * b := Nat.mul_lt_mul_of_pos_left (by omega) (by omega)
    omega

/-- The wheel: `K` rounds of the candidates `6j + 5`, `6j + 7`. -/
theorem wheel_eq (w N : Nat) (hw : 2 ≤ w) (hN : N < 2 ^ w) (fin : Nat → Nat → Nat → Int) :
    ∀ K j, wheel ((2 ^ w) ^ N) (2 ^ w) (2 ^ w - 1) ((2 ^ w) ^ 2) ((2 ^ w) ^ 6) fin K ((2 ^ w) ^ (6 * j + 5))
      (6 * j + 4) (enc w (sF N (6 * j + 5)) (N + 1)) (enc w (pF N (6 * j + 5)) (N + 1))
      (enc w (nF N (6 * j + 5)) (N + 1))
    = fin (enc w (sF N (6 * (j + K) + 5)) (N + 1)) (enc w (pF N (6 * (j + K) + 5)) (N + 1))
        (enc w (nF N (6 * (j + K) + 5)) (N + 1))
  | 0, j => rfl
  | K + 1, j => by
    rw [wheel_succ, show 6 * j + 4 = 6 * j + 5 - 1 by omega, step_eq w N _ hw hN (by omega)]
    obtain ⟨a1, a2, a3⟩ := state_nonprime N (6 * j + 6)
      (by rw [show 6 * j + 6 = 2 * (3 * j + 3) by ring]; exact not_prime_mul (by omega) (by omega))
    rw [show 6 * j + 5 + 1 = 6 * j + 6 by omega, ← a1, ← a2, ← a3,
      show Nat.mul ((2 ^ w) ^ (6 * j + 5)) ((2 ^ w) ^ 2) = (2 ^ w) ^ (6 * j + 7) by
        show (2 ^ w) ^ (6 * j + 5) * (2 ^ w) ^ 2 = _; rw [← pow_add],
      show Nat.add (6 * j + 5 - 1) 2 = 6 * j + 7 - 1 by show 6 * j + 5 - 1 + 2 = _; omega,
      step_eq w N _ hw hN (by omega)]
    obtain ⟨b1, b2, b3⟩ := state_nonprime N (6 * j + 8)
      (by rw [show 6 * j + 8 = 2 * (3 * j + 4) by ring]; exact not_prime_mul (by omega) (by omega))
    obtain ⟨c1, c2, c3⟩ := state_nonprime N (6 * j + 9)
      (by rw [show 6 * j + 9 = 3 * (2 * j + 3) by ring]; exact not_prime_mul (by omega) (by omega))
    obtain ⟨d1, d2, d3⟩ := state_nonprime N (6 * j + 10)
      (by rw [show 6 * j + 10 = 2 * (3 * j + 5) by ring]; exact not_prime_mul (by omega) (by omega))
    rw [show 6 * j + 7 + 1 = 6 * j + 8 by omega, ← b1, ← b2, ← b3, ← c1, ← c2, ← c3, ← d1, ← d2, ← d3,
      show Nat.mul ((2 ^ w) ^ (6 * j + 5)) ((2 ^ w) ^ 6) = (2 ^ w) ^ (6 * (j + 1) + 5) by
        show (2 ^ w) ^ (6 * j + 5) * (2 ^ w) ^ 6 = _
        rw [← pow_add, show 6 * j + 5 + 6 = 6 * (j + 1) + 5 by omega],
      show Nat.add (6 * j + 5 - 1) 6 = 6 * (j + 1) + 4 by show 6 * j + 5 - 1 + 6 = _; omega,
      show 6 * j + 10 + 1 = 6 * (j + 1) + 5 by ring, wheel_eq w N hw hN fin K (j + 1),
      show j + 1 + K = j + (K + 1) by omega]

/-! ## The final count -/

theorem sum_le_card {f : Nat → Nat} (L : Nat) (h : ∀ i, i < L → f i ≤ 1) :
    ∑ i ∈ range L, f i ≤ L := by
  calc ∑ i ∈ range L, f i ≤ ∑ _i ∈ range L, 1 := sum_le_sum (fun i hi => h i (mem_range.mp hi))
    _ = L := by simp

theorem fin_eq (w N c : Nat) (hw : 2 ≤ w) (hN : 2 * N + 1 < 2 ^ w) (hc : N < c * c) :
    fin N (2 ^ w) (2 ^ w - 1) w (enc w (ind N 1) (N + 1)) (enc w (sF N c) (N + 1))
      (enc w (pF N c) (N + 1)) (enc w (nF N c) (N + 1)) = mertensSpec N := by
  have hw1 : 1 ≤ w := by omega
  have hpow : 2 ^ w = 2 * 2 ^ (w - 1) := by
    rw [← pow_succ']; congr 1; omega
  set H := 2 ^ (w - 1) with hH
  have hNH : N < H := by omega
  -- lane functions
  set O1 : Nat → Nat := fun i => if i < N then 1 else 0 with hO1
  set Tl : Nat → Nat := fun i => if i < N then N - i else 0 with hTl
  set Dl : Nat → Nat := fun i => (Tl i - sF N c i) + O1 i * (H - 1) with hDl
  set Ll : Nat → Nat := fun i => (Dl i >>> (w - 1)) &&& O1 i with hLl
  set Ol : Nat → Nat := fun i => pF N c i ^^^ Ll i with hOl
  have hO1le : ∀ i, O1 i ≤ 1 := fun i => by simp only [hO1]; split <;> omega
  have hones : enc w (ind N 1) (N + 1) = enc w O1 (N + 1) := by
    apply enc_congr; intro i _; simp only [ind, hO1, Nat.one_dvd, and_true]
  have hT : (2 ^ w * enc w O1 (N + 1) - N) / (2 ^ w - 1) = enc w Tl (N + 1) := lanes_m w N hw
  have hsT : ∀ i, i < N + 1 → sF N c i ≤ Tl i := by
    intro i _; simp only [hTl, sF]; split
    · exact Sv_le c (N - i) (by omega)
    · omega
  have hDlt : ∀ i, i < N + 1 → Dl i < 2 ^ w := by
    intro i _; simp only [hDl, hTl, hO1]; split <;> omega
  have hLlv : ∀ i, Ll i = if i < N ∧ Sv c (N - i) < N - i then 1 else 0 := by
    intro i
    simp only [hLl, hDl, hTl, hO1, sF]
    by_cases hi : i < N
    · simp only [hi, ↓reduceIte, Nat.one_mul, true_and]
      have hs := Sv_le c (N - i) (by omega)
      rw [Nat.shiftRight_eq_div_pow, Nat.and_one_is_mod]
      by_cases hlt : Sv c (N - i) < N - i
      · rw [if_pos hlt, Nat.div_eq_of_lt_le (by rw [Nat.one_mul]; omega) (by omega)]
      · rw [if_neg hlt, Nat.div_eq_of_lt (by omega)]
    · simp [hi]
  have hLle : ∀ i, Ll i ≤ 1 := fun i => by rw [hLlv]; split <;> omega
  have hOle : ∀ i, Ol i ≤ 1 := by
    intro i; simp only [hOl]
    rcases Nat.le_one_iff_eq_zero_or_eq_one.mp (pF_le N c i) with h | h <;>
    rcases Nat.le_one_iff_eq_zero_or_eq_one.mp (hLle i) with h' | h' <;> rw [h, h'] <;> decide
  unfold fin
  show Int.subNatNat (N - (enc w (nF N c) (N + 1) % (2 ^ w - 1)))
    (2 * (((enc w (pF N c) (N + 1) ^^^ (((((((2 ^ w * enc w (ind N 1) (N + 1)) - N) / (2 ^ w - 1)) - enc w (sF N c) (N + 1)) + ((2 ^ w >>> 1) - 1) * enc w (ind N 1) (N + 1)) >>> (w - 1)) &&& enc w (ind N 1) (N + 1))) - ((enc w (pF N c) (N + 1) ^^^ (((((((2 ^ w * enc w (ind N 1) (N + 1)) - N) / (2 ^ w - 1)) - enc w (sF N c) (N + 1)) + ((2 ^ w >>> 1) - 1) * enc w (ind N 1) (N + 1)) >>> (w - 1)) &&& enc w (ind N 1) (N + 1))) &&& enc w (nF N c) (N + 1))) % (2 ^ w - 1))) = _
  have hshr : 2 ^ w >>> 1 = H := by
    rw [Nat.shiftRight_eq_div_pow, hpow]; simp
  rw [hones, hT, hshr, enc_sub w _ _ _ hsT, Nat.mul_comm (H - 1), enc_mul, enc_add,
    enc_shr_and w hw1 _ _ _ _ (by omega) hDlt hO1le,
    enc_xor w _ _ _ (fun i _ => lt_of_le_one hw1 (pF_le N c i)) (fun i _ => lt_of_le_one hw1 (hLle i)),
    enc_and w _ _ _ (fun i _ => lt_of_le_one hw1 (hOle i)) (fun i _ => lt_of_le_one hw1 (nF_le N c i)),
    enc_sub w _ _ _ (fun i _ => Nat.and_le_left), enc_mod w _ _ hw, enc_mod w _ _ hw]
  -- the two lane sums are small
  have hs1 : ∑ i ∈ range (N + 1), nF N c i ≤ N := by
    rw [sum_range_succ]; simp only [nF, lt_irrefl, ↓reduceIte, Nat.add_zero]
    exact sum_le_card N (fun i hi => by rw [if_pos hi]; exact NSv_le _ _)
  have hs2 : ∑ i ∈ range (N + 1), ((pF N c i ^^^ Ll i) - ((pF N c i ^^^ Ll i) &&& nF N c i)) ≤ N + 1 := by
    apply sum_le_card
    intro i _
    have := hOle i
    simp only [hOl] at this
    omega
  have h4 := four_le w hw
  have hsmall : N + 1 < 2 ^ w - 1 := by omega
  rw [Nat.mod_eq_of_lt (by omega), Nat.mod_eq_of_lt (by omega), Int.subNatNat_eq_coe,
    Nat.cast_sub hs1]
  -- lane by lane
  unfold mertensSpec
  conv_rhs => rw [← sum_range_reflect]
  simp only [show N + 1 - 1 = N by omega]
  have hterm : ∀ i ∈ range (N + 1), (ArithmeticFunction.moebius (N - i) : Int)
      = ((O1 i : Nat) : Int) - ((nF N c i : Nat) : Int) - 2 * (((Ol i - (Ol i &&& nF N c i)) : Nat) : Int) := by
    intro i hi
    rw [mem_range] at hi
    by_cases h : i < N
    · have hO1i : O1 i = 1 := by simp [hO1, h]
      rw [moebius_lane c (N - i) N (by omega) (by omega) hc, hO1i]
      simp only [hOl, hLlv, nF, h, ↓reduceIte, true_and]
      have hNS := NSv_le c (N - i)
      have hP := Pv_le c (N - i)
      rcases Nat.le_one_iff_eq_zero_or_eq_one.mp hNS with h1 | h1 <;>
      rcases Nat.le_one_iff_eq_zero_or_eq_one.mp hP with h2 | h2 <;>
      by_cases h3 : Sv c (N - i) < N - i <;> simp [h1, h2, h3, pF, h]
    · have : i = N := by omega
      subst this
      simp [hO1, hOl, hLlv, nF, pF]
  rw [sum_congr rfl hterm, sum_sub_distrib, sum_sub_distrib, ← mul_sum]
  have hN' : ∑ i ∈ range (N + 1), ((O1 i : Nat) : Int) = N := by
    rw [sum_range_succ]; simp only [hO1]
    simp only [lt_irrefl, ↓reduceIte, Nat.cast_zero, add_zero]
    rw [sum_congr rfl (fun i hi => by rw [if_pos (mem_range.mp hi)])]
    simp
  rw [hN']
  push_cast
  ring

/-! ## `√N` by Newton steps -/

theorem sqStep_ge (N x : Nat) (hx : 1 ≤ x) : Nat.sqrt N ≤ sqStep N x := by
  show Nat.sqrt N ≤ (x + N / x) >>> 1
  rw [Nat.shiftRight_eq_div_pow, pow_one]
  have hs : Nat.sqrt N * Nat.sqrt N ≤ N := Nat.sqrt_le N
  generalize Nat.sqrt N = s at hs ⊢
  have hq := (Nat.le_div_iff_mul_le (k := x) (by omega) (x := 0) (y := N)).mpr (by omega)
  suffices h : 2 * s ≤ x + N / x by omega
  rcases Nat.le_total (2 * s) x with h | h
  · omega
  · obtain ⟨t, ht⟩ : ∃ t, 2 * s = x + t := ⟨2 * s - x, by omega⟩
    have h1 : 2 * s * t ≤ s * s + t * t := by nlinarith [sq_nonneg ((s : Int) - t)]
    have h2 : t * (x + t) = t * x + t * t := by ring
    have h3 : t * (x + t) = 2 * s * t := by rw [← ht]; ring
    have h4 : t * x ≤ N := by omega
    have h5 : t ≤ N / x := (Nat.le_div_iff_mul_le (by omega)).mpr h4
    omega

theorem sqStep_pos (N x : Nat) (hx : 2 ≤ x) : 1 ≤ sqStep N x := by
  show 1 ≤ (x + N / x) >>> 1
  rw [Nat.shiftRight_eq_div_pow, pow_one]
  generalize N / x = q
  omega

/-! ## Main correctness -/

theorem state_two (w N : Nat) :
    enc w (sF N 2) (N + 1) = enc w (ind N 1) (N + 1) ∧ enc w (pF N 2) (N + 1) = 0 ∧
      enc w (nF N 2) (N + 1) = 0 := by
  have hP : ∀ m, Pset 2 m = ∅ := by
    intro m; apply eq_empty_of_forall_notMem; intro p hp
    simp only [Pset, mem_filter, mem_range] at hp
    have := hp.2.1.two_le; omega
  refine ⟨?_, ?_, ?_⟩
  · apply enc_congr; intro i _
    simp only [sF, ind, Sv, hP, prod_empty, Nat.one_dvd, and_true]
  · unfold enc; apply sum_eq_zero; intro i _
    simp only [pF, Pv, hP, card_empty, Nat.zero_mod, ite_self, zero_mul]
  · unfold enc; apply sum_eq_zero; intro i _
    have : NSv 2 (N - i) = 0 := by
      unfold NSv; rw [if_neg]; rintro ⟨p, h1, h2, _⟩; have := h2.two_le; omega
    simp only [nF, this, ite_self, zero_mul]

theorem slow_correct : ∀ n, slow n = mertensSpec n := by
  intro N
  have e0 : Nat.add (Nat.shiftRight N (nat_lit 10)) (nat_lit 11) = N / 1024 + 11 := by
    show N >>> 10 + 11 = _
    rw [Nat.shiftRight_eq_div_pow]
  have e1 : ∀ w, Nat.shiftLeft (nat_lit 1) w = 2 ^ w := by
    intro w; show 1 <<< w = _; rw [Nat.shiftLeft_eq, Nat.one_mul]
  unfold slow
  rw [e1, e0]
  generalize hw : N / 1024 + 11 = w
  have hw2 : 2 ≤ w := by omega
  have hbig : 2 * N + 1 < 2 ^ w := by
    have h1 : N / 1024 + 1 ≤ 2 ^ (N / 1024) := Nat.lt_two_pow_self
    have h2 : 2 ^ (N / 1024 + 11) = 2 ^ (N / 1024) * 2048 := by rw [pow_add]; norm_num
    have h3 : N < 1024 * (N / 1024 + 1) := by omega
    rw [← hw, h2]
    omega
  have hN : N < 2 ^ w := by omega
  obtain ⟨hS2, hP2, hN2⟩ := state_two w N
  -- d = 2 and d = 3
  have hu2 := upd_eq w N 2 hw2 hN (by omega) (Or.inl Nat.prime_two)
  have hu3 := upd_eq w N 3 hw2 hN (by omega) (Or.inl Nat.prime_three)
  rw [hS2, hP2, hN2] at hu2
  obtain ⟨a1, a2, a3⟩ := state_nonprime N 4 (by decide)
  have hones : (2 ^ w) ^ N / (2 ^ w - 1) = enc w (ind N 1) (N + 1) := by
    have := marks_eq w N 1 hw2 (le_refl 1); rwa [pow_one] at this
  unfold go
  simp only []
  rw [show Nat.pow (2 ^ w) N = (2 ^ w) ^ N from rfl, show Nat.sub (2 ^ w) (nat_lit 1) = 2 ^ w - 1 from rfl,
    show Nat.div ((2 ^ w) ^ N) (2 ^ w - 1) = (2 ^ w) ^ N / (2 ^ w - 1) from rfl, hones]
  have hB2 : Nat.mul (2 ^ w) (2 ^ w) = (2 ^ w) ^ 2 := by show 2 ^ w * 2 ^ w = _; ring
  have hB3 : Nat.mul ((2 ^ w) ^ 2) (2 ^ w) = (2 ^ w) ^ 3 := by show (2 ^ w) ^ 2 * 2 ^ w = _; ring
  have hB5 : Nat.mul ((2 ^ w) ^ 3) ((2 ^ w) ^ 2) = (2 ^ w) ^ (6 * 0 + 5) := by
    show (2 ^ w) ^ 3 * (2 ^ w) ^ 2 = _; ring
  have hB6 : Nat.mul ((2 ^ w) ^ 3) ((2 ^ w) ^ 3) = (2 ^ w) ^ 6 := by show (2 ^ w) ^ 3 * (2 ^ w) ^ 3 = _; ring
  rw [hB2, hB3, hB5, hB6]
  show upd ((2 ^ w) ^ N) (2 ^ w - 1) ((2 ^ w) ^ 2) (2 - 1) (enc w (ind N 1) (N + 1)) 0 0 _ = _
  rw [hu2]
  show upd ((2 ^ w) ^ N) (2 ^ w - 1) ((2 ^ w) ^ 3) (3 - 1) _ _ _ _ = _
  rw [hu3]
  show wheel ((2 ^ w) ^ N) (2 ^ w) (2 ^ w - 1) ((2 ^ w) ^ 2) ((2 ^ w) ^ 6) _ _ ((2 ^ w) ^ (6 * 0 + 5))
    (6 * 0 + 4) (enc w (sF N (3 + 1)) (N + 1)) (enc w (pF N (3 + 1)) (N + 1)) (enc w (nF N (3 + 1)) (N + 1)) = _
  rw [show 3 + 1 = 4 from rfl, ← a1, ← a2, ← a3, wheel_eq w N hw2 hN]
  -- the wheel ends beyond `√N`
  have hx0 : 2 ≤ Nat.add (Nat.shiftRight N (nat_lit 6)) (nat_lit 16) := by
    show 2 ≤ N >>> 6 + 16; omega
  have hs := sqStep_ge N _ (sqStep_pos N _ hx0)
  generalize sqStep N (sqStep N (Nat.add (Nat.shiftRight N (nat_lit 6)) (nat_lit 16))) = s at hs ⊢
  apply fin_eq w N _ hw2 hbig
  have h6 : s + 1 ≤ 6 * (0 + Nat.div (Nat.add s (nat_lit 1)) (nat_lit 6)) + 5 := by
    show s + 1 ≤ 6 * (0 + (s + 1) / 6) + 5; omega
  generalize 6 * (0 + Nat.div (Nat.add s (nat_lit 1)) (nat_lit 6)) + 5 = c at h6 ⊢
  have hlt : N < (Nat.sqrt N + 1) * (Nat.sqrt N + 1) := by
    have := Nat.lt_succ_sqrt' N
    rwa [pow_two] at this
  have : (Nat.sqrt N + 1) * (Nat.sqrt N + 1) ≤ c * c := Nat.mul_le_mul (by omega) (by omega)
  omega

/-! ## The fixed-prime branch -/

/-- `fast` agrees with the general sieve on `N ≤ 840` (checked by the kernel, value by value). -/
theorem fast_ok : ∀ N, N < 841 → fast N = slow N := by decide +kernel

theorem impl_correct : ∀ n, impl n = mertensSpec n := by
  intro n
  unfold impl
  rcases Nat.lt_or_ge n 841 with h | h
  · have e : fast n = mertensSpec n := (fast_ok n h).trans (slow_correct n)
    rw [show Nat.sub n 840 = 0 by show n - 840 = 0; omega]
    unfold fast at e
    exact e
  · obtain ⟨k, hk⟩ : ∃ k, Nat.sub n 840 = k + 1 := ⟨n - 841, by show n - 840 = _; omega⟩
    rw [hk]
    exact slow_correct n

end Submission
