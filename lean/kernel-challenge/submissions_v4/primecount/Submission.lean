import Spec
import Lean

/-!
# Prime counting: one division, one mask

Every `m ≤ N` owns one `w`-bit slot of a natural number, slot `N - m` (reverse order). A rational
`ρ = Σ_{t ≥ 1} c(t) · B^(-t)` (`B = 2^w`) whose base-`B` digits are `0 ≤ c(t) < B` puts `c(m)` into
slot `N - m` of `⌊B^N · ρ⌋`; for `ρ = R / D` that is one shift and one kernel division,
`(R <<< (w N)) / D`.

`impl` has two branches.

## `fast`, for `N ≤ 1368 < 37²`

Every composite `m ≤ N` has a prime factor `p ≤ 31` with `2p ≤ m`. With `B = 2^8`, the digits of
`ρ = 37 / (B - 1) - 1 / B - Σ_{p ≤ 31} 1 / (B^p (B^p - 1))` are
`c(t) = 37 - [t = 1] - #{p ≤ 31 : p ∣ t, 2p ≤ t}` (`1 / (B^p (B^p - 1)) = Σ_{k ≥ 2} B^(-k p)` marks
the multiples `2p, 3p, …`). So `c(m) = 37` exactly when `m` is prime, and `c(m) ∈ [33, 36]`
otherwise (at most four primes `≤ 31` divide an `m ≤ 1368`). Among `33 … 37`, only `37 = 100101₂`
has bits `0` and `2` both set, so `C &&& (C >>> 2)` has the slot values `[m prime]` (nothing
spills between slots: every slot value lies in `[33, 37]`, slot `N` is `0`), and one `% (B - 1)`
adds them up (`B ≡ 1`, and `π(1368) = 220 < 255`). The numerator and denominator are numerals
computed at elaboration time (`numeral%`) from the formulas in the source; `fast_ok` checks
`fast N = slow N` for every `N ≤ 1368` in the kernel (`decide +kernel`), and `impl` inlines `fast`.

## `slow`, for every `N`

The multiples `2d, 3d, … ≤ N` of a divisor `d` are one kernel division:
`B^N / (B^(2d) - B^d) = B^(N-d) / (B^d - 1)` is the geometric series with a `1` exactly in those
slots. The marks of `d = 2, 3` and of `d = 6k ± 1` (`k = 1 … K`, a 6-wheel: every prime `≥ 5` has
this form) are combined with `|||`; then a slot is marked exactly when `m` is composite. One
`% (B - 1)` adds all slots, and `π(N) = N - 1 - #composites`. `K` comes from two Newton steps for
`√N`, and `w = ⌊N / 1024⌋ + 11`.

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

/-- `B^d - 1` for `B = 2^8` (a `numeral%` helper). -/
macro "bm% " d:term:max : term => `(Nat.pow 256 $d - 1)

/-- `∏_{p ≤ 31} (B^p - 1)` for `B = 2^8` (a `numeral%` helper). -/
macro "prodP%" : term => `(bm% 2 * bm% 3 * bm% 5 * bm% 7 * bm% 11 * bm% 13 * bm% 17 * bm% 19 *
  bm% 23 * bm% 29 * bm% 31)


open Finset

/-! ## Implementation -/

/-- One Newton step towards `√N`; it never goes below `⌊√N⌋`. -/
def sqStep (N x : Nat) : Nat := Nat.shiftRight (Nat.add x (Nat.div N x)) (nat_lit 1)

/-- Marks of `d = 6j+5` and `d = 6j+7` for `K` consecutive `j`, starting from `Q = B^(6j+5)`. -/
def wheel (BN B2 B6 : Nat) : Nat → Nat → Nat → Nat :=
  fun K => Nat.rec (motive := fun _ => Nat → Nat → Nat) (fun acc _ => acc)
      (fun _ ih acc Q => ih (Nat.lor (Nat.lor acc (Nat.div BN (Nat.sub (Nat.mul Q Q) Q)))
          (Nat.div BN (Nat.sub (Nat.mul (Nat.mul Q B2) (Nat.mul Q B2)) (Nat.mul Q B2))))
        (Nat.mul Q B6)) K

def go (N B BN B2 B6 K : Nat) : Nat :=
  Nat.sub (Nat.sub N (nat_lit 1)) (Nat.mod
    (wheel BN B2 B6 K
      (Nat.lor (Nat.div BN (Nat.sub (Nat.mul B2 B2) B2))
        (Nat.div BN (Nat.sub (Nat.mul (Nat.mul B2 B) (Nat.mul B2 B)) (Nat.mul B2 B))))
      (Nat.pow B (nat_lit 5)))
    (Nat.sub B (nat_lit 1)))

/-- Slot width: `2^wd N > N + 2`. -/
def wd (N : Nat) : Nat := Nat.add (Nat.shiftRight N (nat_lit 10)) (nat_lit 11)

def slow (N : Nat) : Nat :=
  go N (Nat.shiftLeft (nat_lit 1) (wd N)) (Nat.pow (Nat.shiftLeft (nat_lit 1) (wd N)) N)
    (Nat.shiftLeft (nat_lit 1) (Nat.shiftLeft (wd N) (nat_lit 1)))
    (Nat.pow (Nat.shiftLeft (nat_lit 1) (wd N)) (nat_lit 6))
    (Nat.div (Nat.add (sqStep N (sqStep N (Nat.add (Nat.shiftRight N (nat_lit 6)) (nat_lit 16))))
      (nat_lit 1)) (nat_lit 6))


/-- `π(N)` for `N ≤ 1368` (see the module doc). -/
def fast (N : Nat) : Nat :=
  -- `ρ = 37 / (B - 1) - 1 / B - Σ_{p ≤ 31} 1 / (B^p (B^p - 1))` over `D = B^31 ∏_{p ≤ 31} (B^p - 1)`
  share C := Nat.div (Nat.shiftLeft
    (numeral% (37 * (Nat.pow 256 31 * (prodP% / bm% 1)) - Nat.pow 256 30 * prodP% -
      (Nat.pow 256 29 * (prodP% / bm% 2) +
        Nat.pow 256 28 * (prodP% / bm% 3) +
        Nat.pow 256 26 * (prodP% / bm% 5) +
        Nat.pow 256 24 * (prodP% / bm% 7) +
        Nat.pow 256 20 * (prodP% / bm% 11) +
        Nat.pow 256 18 * (prodP% / bm% 13) +
        Nat.pow 256 14 * (prodP% / bm% 17) +
        Nat.pow 256 12 * (prodP% / bm% 19) +
        Nat.pow 256 8 * (prodP% / bm% 23) +
        Nat.pow 256 2 * (prodP% / bm% 29) +
        Nat.pow 256 0 * (prodP% / bm% 31))))
    (Nat.shiftLeft N (nat_lit 3))) (numeral% (Nat.pow 256 31 * prodP%));
  Nat.mod (Nat.land C (Nat.shiftRight C (nat_lit 2))) (nat_lit 255)

/-- `fast` (inlined) for `N ≤ 1368`, `slow` otherwise. The branches are closed functions of `N`
(applied after the test), so unfolding `impl` does not rebuild them. -/
def impl (N : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat → Nat) (fun N =>
    -- `ρ = 37 / (B - 1) - 1 / B - Σ_{p ≤ 31} 1 / (B^p (B^p - 1))` over `D = B^31 ∏_{p ≤ 31} (B^p - 1)`
    share C := Nat.div (Nat.shiftLeft
      (numeral% (37 * (Nat.pow 256 31 * (prodP% / bm% 1)) - Nat.pow 256 30 * prodP% -
        (Nat.pow 256 29 * (prodP% / bm% 2) +
          Nat.pow 256 28 * (prodP% / bm% 3) +
          Nat.pow 256 26 * (prodP% / bm% 5) +
          Nat.pow 256 24 * (prodP% / bm% 7) +
          Nat.pow 256 20 * (prodP% / bm% 11) +
          Nat.pow 256 18 * (prodP% / bm% 13) +
          Nat.pow 256 14 * (prodP% / bm% 17) +
          Nat.pow 256 12 * (prodP% / bm% 19) +
          Nat.pow 256 8 * (prodP% / bm% 23) +
          Nat.pow 256 2 * (prodP% / bm% 29) +
          Nat.pow 256 0 * (prodP% / bm% 31))))
      (Nat.shiftLeft N (nat_lit 3))) (numeral% (Nat.pow 256 31 * prodP%));
    Nat.mod (Nat.land C (Nat.shiftRight C (nat_lit 2))) (nat_lit 255)
    ) (fun _ _ N => slow N) (Nat.sub N (nat_lit 1368)) N

/-! ## Geometric series -/

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

/-! ## One divisor: a single division -/

/-- Slot indicator of the multiples `m ≥ 2d` of `d`. -/
def ind (d m : Nat) : Nat := if 2 * d ≤ m ∧ d ∣ m then 1 else 0

/-- `B^N / (B^(2d) - B^d)` has a `1` in slot `N - m` for every multiple `2d ≤ m ≤ N` of `d`. -/
theorem mark_eq (B N d : Nat) (hB : 4 ≤ B) (hd : 1 ≤ d) :
    B ^ N / (B ^ d * B ^ d - B ^ d) = ∑ m ∈ range (N + 1), ind d m * B ^ (N - m) := by
  have hBd : B ≤ B ^ d := by
    calc B = B ^ 1 := (pow_one B).symm
      _ ≤ B ^ d := Nat.pow_le_pow_right (by omega) hd
  have hfac : B ^ d * B ^ d - B ^ d = B ^ d * (B ^ d - 1) := by
    rw [Nat.mul_sub, Nat.mul_one]
  rw [hfac]
  by_cases hdN : d ≤ N
  · obtain ⟨L, rfl⟩ : ∃ L, N = d + L := ⟨N - d, by omega⟩
    rw [pow_add, Nat.mul_div_mul_left _ _ (pow_pos (by omega : 0 < B) d)]
    set T := L / d
    set r := L % d
    have hL : L = r + d * T := (Nat.mod_add_div L d).symm
    have hr : r < d := Nat.mod_lt _ (by omega)
    have hg := geom_mul (B ^ d) (by omega) T
    have hBL : B ^ L = (B ^ d - 1) * (B ^ r * ∑ j ∈ range T, (B ^ d) ^ j) + B ^ r := by
      rw [hL, pow_add, pow_mul, ← hg]
      ring
    have hrlt : B ^ r < B ^ d - 1 := by
      have h1 : B ^ r * B ≤ B ^ d := by
        rw [← pow_succ]; exact Nat.pow_le_pow_right (by omega) (by omega)
      have h2 : 0 < B ^ r := pow_pos (by omega) r
      have h3 : B ^ r * 4 ≤ B ^ r * B := Nat.mul_le_mul_left _ hB
      omega
    rw [hBL, Nat.mul_add_div (by omega), Nat.div_eq_of_lt hrlt, Nat.add_zero, mul_sum]
    -- reindex: `j ↦ m = d + L - r - d j = d (T + 1 - j)`
    simp only [ind, ite_mul, one_mul, zero_mul]
    rw [← sum_filter]
    apply sum_nbij' (fun j => d * (T + 1 - j)) (fun m => T + 1 - m / d)
    · intro j hj
      simp only [mem_range, mem_filter] at hj ⊢
      refine ⟨?_, ?_, Dvd.intro _ rfl⟩
      · have : d * (T + 1 - j) ≤ d * (T + 1) := Nat.mul_le_mul_left _ (by omega)
        have : d * (T + 1) = d + d * T := by ring
        omega
      · have : d * 2 ≤ d * (T + 1 - j) := Nat.mul_le_mul_left _ (by omega)
        omega
    · intro m hm
      simp only [mem_range, mem_filter] at hm ⊢
      obtain ⟨h1, h2, ⟨c, rfl⟩⟩ := hm
      rw [Nat.mul_div_cancel_left _ (by omega)]
      have : d * 2 ≤ d * c := by omega
      have hc : 2 ≤ c := Nat.le_of_mul_le_mul_left this (by omega)
      have : d * c < d * (T + 2) := by
        have : d * (T + 2) = d * T + 2 * d := by ring
        omega
      have : c < T + 2 := Nat.lt_of_mul_lt_mul_left this
      omega
    · intro j hj
      simp only [mem_range] at hj
      show T + 1 - d * (T + 1 - j) / d = j
      rw [Nat.mul_div_cancel_left _ (by omega)]
      omega
    · intro m hm
      simp only [mem_range, mem_filter] at hm
      obtain ⟨h1, h2, ⟨c, rfl⟩⟩ := hm
      show d * (T + 1 - (T + 1 - d * c / d)) = d * c
      rw [Nat.mul_div_cancel_left _ (by omega)]
      have : d * 2 ≤ d * c := by omega
      have hc : 2 ≤ c := Nat.le_of_mul_le_mul_left this (by omega)
      have : d * c < d * (T + 2) := by
        have : d * (T + 2) = d * T + 2 * d := by ring
        omega
      have : c < T + 2 := Nat.lt_of_mul_lt_mul_left this
      congr 1
      omega
    · intro j hj
      simp only [mem_range] at hj
      rw [← pow_mul, ← pow_add]
      congr 1
      have : d * (T + 1 - j) = d * (T + 1) - d * j := Nat.mul_sub _ _ _
      have : d * (T + 1) = d + d * T := by ring
      have : d * j ≤ d * T := Nat.mul_le_mul_left _ (by omega)
      have : d * j = j * d := Nat.mul_comm _ _
      omega
  · have hlt : B ^ N < B ^ d * (B ^ d - 1) := by
      have h1 : B ^ N < B ^ d := Nat.pow_lt_pow_right (by omega) (by omega)
      have h2 : 1 ≤ B ^ d - 1 := by omega
      have h3 : B ^ d * 1 ≤ B ^ d * (B ^ d - 1) := Nat.mul_le_mul_left _ h2
      omega
    rw [Nat.div_eq_of_lt hlt]
    symm
    apply sum_eq_zero
    intro m hm
    simp only [mem_range] at hm
    simp only [ind]
    rw [if_neg (by omega), zero_mul]

/-! ## Slot encodings -/

section Slots

variable (w N : Nat)

/-- Slot `N - m` holds `f m`. -/
def S (f : Nat → Nat) : Nat := ∑ m ∈ range (N + 1), f m * (2 ^ w) ^ (N - m)

/-- The same number, slot by slot from the bottom. -/
def enc (a : Nat → Nat) (L : Nat) : Nat := ∑ j ∈ range L, a j * 2 ^ (w * j)

omit w in
theorem sum_reflect (g : Nat → Nat) : ∀ n, ∑ j ∈ range (n + 1), g (n - j) = ∑ j ∈ range (n + 1), g j
  | 0 => by simp
  | n + 1 => by
    rw [sum_range_succ', sum_range_succ (fun j => g j)]
    simp only [Nat.add_sub_add_right, Nat.sub_zero]
    rw [sum_reflect g n]

theorem S_eq_enc (f : Nat → Nat) : S w N f = enc w (fun j => f (N - j)) (N + 1) := by
  unfold S enc
  rw [← sum_reflect _ N]
  apply sum_congr rfl
  intro j hj
  simp only [mem_range] at hj
  rw [show N - (N - j) = j by omega, ← pow_mul]

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

theorem enc_or (a b : Nat → Nat) : ∀ L, (∀ m, m < L → a m < 2 ^ w) → (∀ m, m < L → b m < 2 ^ w) →
    enc w a L ||| enc w b L = enc w (fun m => a m ||| b m) L
  | 0, _, _ => by simp [enc]
  | L + 1, ha, hb => by
    have ha' : ∀ m, m < L → a m < 2 ^ w := fun m hm => ha m (by omega)
    have hb' : ∀ m, m < L → b m < 2 ^ w := fun m hm => hb m (by omega)
    rw [enc_succ, enc_succ, enc_succ,
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w a L ha'),
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w b L hb'),
      Nat.shiftLeft_add_eq_or_of_lt (enc_lt w _ L (fun m hm => Nat.or_lt_two_pow (ha' m hm) (hb' m hm))),
      ← enc_or a b L ha' hb', Nat.shiftLeft_or_distrib]
    ac_rfl

/-- The slot sum is the value modulo `2^w − 1`. -/
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

open Classical in
/-- Indicator slots of a predicate. -/
noncomputable def sl (P : Nat → Prop) : Nat := S w N (fun m => if P m then 1 else 0)

open Classical in
theorem sl_or (hw : 1 ≤ w) (P Q : Nat → Prop) : sl w N P ||| sl w N Q = sl w N (fun m => P m ∨ Q m) := by
  have h2 : (1 : Nat) < 2 ^ w := Nat.one_lt_two_pow (by omega)
  unfold sl
  rw [S_eq_enc, S_eq_enc, S_eq_enc, enc_or w _ _ _ (fun m _ => by split <;> omega)
    (fun m _ => by split <;> omega)]
  congr 1
  funext j
  by_cases hP : P (N - j) <;> by_cases hQ : Q (N - j) <;> simp [hP, hQ]

open Classical in
theorem sl_congr {P Q : Nat → Prop} (h : ∀ m, m ≤ N → (P m ↔ Q m)) : sl w N P = sl w N Q := by
  unfold sl S
  apply sum_congr rfl
  intro m hm
  simp only [mem_range] at hm
  show (if P m then 1 else 0) * _ = (if Q m then 1 else 0) * _
  rw [if_congr (h m (by omega)) rfl rfl]

open Classical in
theorem sl_mod (hw : 2 ≤ w) (P : Nat → Prop) :
    sl w N P % (2 ^ w - 1) = #({m ∈ range (N + 1) | P m}) % (2 ^ w - 1) := by
  unfold sl
  rw [S_eq_enc, enc_mod w _ _ hw, card_filter]
  congr 1
  exact sum_reflect (fun m => if P m then 1 else 0) N

open Classical in
theorem mark_sl (hw : 2 ≤ w) (d : Nat) (hd : 1 ≤ d) :
    (2 ^ w) ^ N / ((2 ^ w) ^ d * (2 ^ w) ^ d - (2 ^ w) ^ d) = sl w N (fun m => 2 * d ≤ m ∧ d ∣ m) := by
  have h4 : 4 ≤ 2 ^ w := by
    calc 4 = 2 ^ 2 := by norm_num
      _ ≤ 2 ^ w := Nat.pow_le_pow_right (by omega) hw
  rw [mark_eq _ _ _ h4 hd]
  unfold sl S
  apply sum_congr rfl
  intro m _
  unfold ind
  by_cases h : 2 * d ≤ m ∧ d ∣ m <;> simp [h]

end Slots

/-! ## The wheel loop -/

/-- Some `d = 6i+5` or `d = 6i+7` with `j ≤ i < j + K` has the multiple `m ≥ 2d`. -/
def wk (j K m : Nat) : Prop :=
  ∃ i, j ≤ i ∧ i < j + K ∧ ((2 * (6 * i + 5) ≤ m ∧ (6 * i + 5) ∣ m) ∨ (2 * (6 * i + 7) ≤ m ∧ (6 * i + 7) ∣ m))

theorem wheel_succ (BN B2 B6 K acc Q : Nat) : wheel BN B2 B6 (K + 1) acc Q =
    wheel BN B2 B6 K ((acc ||| BN / (Q * Q - Q)) ||| BN / ((Q * B2) * (Q * B2) - Q * B2)) (Q * B6) :=
  rfl

theorem wheel_eq (w N : Nat) (hw : 2 ≤ w) : ∀ K j (P : Nat → Prop),
    wheel ((2 ^ w) ^ N) ((2 ^ w) ^ 2) ((2 ^ w) ^ 6) K (sl w N P) ((2 ^ w) ^ (6 * j + 5))
      = sl w N (fun m => P m ∨ wk j K m)
  | 0, j, P => by
    show sl w N P = _
    apply sl_congr
    intro m _
    constructor
    · exact Or.inl
    · rintro (h | ⟨i, h1, h2, _⟩)
      · exact h
      · omega
  | K + 1, j, P => by
    have e1 : (2 ^ w) ^ (6 * j + 5) * (2 ^ w) ^ 2 = (2 ^ w) ^ (6 * j + 7) := by
      rw [← pow_add]
    have e2 : (2 ^ w) ^ (6 * j + 5) * (2 ^ w) ^ 6 = (2 ^ w) ^ (6 * (j + 1) + 5) := by
      rw [← pow_add, show 6 * j + 5 + 6 = 6 * (j + 1) + 5 by omega]
    rw [wheel_succ, e1, e2, mark_sl w N hw _ (by omega), mark_sl w N hw _ (by omega),
      sl_or w N (by omega), sl_or w N (by omega), wheel_eq w N hw K (j + 1)]
    apply sl_congr
    intro m _
    constructor
    · rintro (((h | h) | h) | ⟨i, h1, h2, h3⟩)
      · exact Or.inl h
      · exact Or.inr ⟨j, le_refl _, by omega, Or.inl h⟩
      · exact Or.inr ⟨j, le_refl _, by omega, Or.inr h⟩
      · exact Or.inr ⟨i, by omega, by omega, h3⟩
    · rintro (h | ⟨i, h1, h2, h3⟩)
      · exact Or.inl (Or.inl (Or.inl h))
      · rcases Nat.lt_or_ge i (j + 1) with hi | hi
        · have hij : i = j := by omega
          subst hij
          rcases h3 with h3 | h3
          · exact Or.inl (Or.inl (Or.inr h3))
          · exact Or.inl (Or.inr h3)
        · exact Or.inr ⟨i, hi, by omega, h3⟩

/-! ## `√N` by Newton steps -/

theorem two_mul_le (a b : Nat) : 2 * a * b ≤ a * a + b * b := by
  rcases Nat.le_total a b with h | h
  · obtain ⟨c, rfl⟩ : ∃ c, b = a + c := ⟨b - a, by omega⟩
    have : a * a + (a + c) * (a + c) = 2 * a * (a + c) + c * c := by ring
    omega
  · obtain ⟨c, rfl⟩ : ∃ c, a = b + c := ⟨a - b, by omega⟩
    have : (b + c) * (b + c) + b * b = 2 * (b + c) * b + c * c := by ring
    omega

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
    have h1 := two_mul_le s t
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

/-! ## Number theory -/

theorem prime_mod_six (p : Nat) (hp : p.Prime) (h5 : 5 ≤ p) : p % 6 = 1 ∨ p % 6 = 5 := by
  have h2 : ¬ 2 ∣ p := fun h => by
    rcases hp.eq_one_or_self_of_dvd 2 h with h | h <;> omega
  have h3 : ¬ 3 ∣ p := fun h => by
    rcases hp.eq_one_or_self_of_dvd 3 h with h | h <;> omega
  omega

theorem marked_iff (N s m : Nat) (hs : Nat.sqrt N ≤ s) (hm : m ≤ N) :
    (((2 * 2 ≤ m ∧ 2 ∣ m) ∨ (2 * 3 ≤ m ∧ 3 ∣ m)) ∨ wk 0 ((s + 1) / 6) m) ↔ (2 ≤ m ∧ ¬ m.Prime) := by
  constructor
  · have key : ∀ d, 2 ≤ d → 2 * d ≤ m → d ∣ m → 2 ≤ m ∧ ¬ m.Prime := by
      intro d hd h1 h2
      refine ⟨by omega, fun hp => ?_⟩
      rcases hp.eq_one_or_self_of_dvd d h2 with h | h <;> omega
    rintro ((⟨h1, h2⟩ | ⟨h1, h2⟩) | ⟨i, _, _, (⟨h1, h2⟩ | ⟨h1, h2⟩)⟩)
    · exact key 2 (by omega) h1 h2
    · exact key 3 (by omega) h1 h2
    · exact key _ (by omega) h1 h2
    · exact key _ (by omega) h1 h2
  · rintro ⟨h2, hnp⟩
    have hm1 : m ≠ 1 := by omega
    have hmin := Nat.minFac_prime hm1
    have hsq := Nat.minFac_sq_le_self (by omega) hnp
    rw [pow_two] at hsq
    have hdvd := Nat.minFac_dvd m
    set p := m.minFac
    have hp2 := hmin.two_le
    have h2p : 2 * p ≤ m := le_trans (Nat.mul_le_mul_right _ hp2) hsq
    have hpN : p ≤ s := by
      have : p ≤ Nat.sqrt N := Nat.le_sqrt.mpr (le_trans hsq hm)
      omega
    rcases Nat.lt_or_ge p 5 with hp5 | hp5
    · rcases (by omega : p = 2 ∨ p = 3 ∨ p = 4) with h | h | h
      · exact Or.inl (Or.inl ⟨by omega, h ▸ hdvd⟩)
      · exact Or.inl (Or.inr ⟨by omega, h ▸ hdvd⟩)
      · exact absurd (h ▸ hmin) (by decide)
    · right
      rcases prime_mod_six p hmin hp5 with h | h
      · refine ⟨p / 6 - 1, by omega, by omega, Or.inr ⟨?_, ?_⟩⟩
        · rw [show 6 * (p / 6 - 1) + 7 = p by omega]; exact h2p
        · rw [show 6 * (p / 6 - 1) + 7 = p by omega]; exact hdvd
      · refine ⟨p / 6, by omega, by omega, Or.inl ⟨?_, ?_⟩⟩
        · rw [show 6 * (p / 6) + 5 = p by omega]; exact h2p
        · rw [show 6 * (p / 6) + 5 = p by omega]; exact hdvd

/-! ## Main correctness -/

open Classical in
theorem go_eq (N w s : Nat) (hw : 2 ≤ w) (hbig : N + 2 < 2 ^ w) (hs : Nat.sqrt N ≤ s) :
    go N (2 ^ w) ((2 ^ w) ^ N) ((2 ^ w) ^ 2) ((2 ^ w) ^ 6) ((s + 1) / 6) = primeCountSpec N := by
  show N - 1 - (wheel ((2 ^ w) ^ N) ((2 ^ w) ^ 2) ((2 ^ w) ^ 6) ((s + 1) / 6)
    ((2 ^ w) ^ N / ((2 ^ w) ^ 2 * (2 ^ w) ^ 2 - (2 ^ w) ^ 2) |||
      (2 ^ w) ^ N / (((2 ^ w) ^ 2 * 2 ^ w) * ((2 ^ w) ^ 2 * 2 ^ w) - (2 ^ w) ^ 2 * 2 ^ w))
    ((2 ^ w) ^ 5)) % (2 ^ w - 1) = _
  rw [show (2 ^ w) ^ 2 * 2 ^ w = (2 ^ w) ^ 3 by ring, show (2 ^ w) ^ 5 = (2 ^ w) ^ (6 * 0 + 5) by norm_num,
    mark_sl w N hw 2 (by omega), mark_sl w N hw 3 (by omega), sl_or w N (by omega), wheel_eq w N hw,
    sl_mod w N hw]
  -- the slot sum counts composites
  rw [@filter_congr _ (fun m => ((2 * 2 ≤ m ∧ 2 ∣ m) ∨ (2 * 3 ≤ m ∧ 3 ∣ m)) ∨ wk 0 ((s + 1) / 6) m)
    (fun m => 2 ≤ m ∧ ¬ m.Prime) (fun _ => Classical.propDecidable _) _ (range (N + 1)) (fun m hm => by
    simp only [mem_range] at hm
    exact marked_iff N s m hs (by omega))]
  have hle : #({m ∈ range (N + 1) | 2 ≤ m ∧ ¬ m.Prime}) ≤ N + 1 := by
    calc _ ≤ #(range (N + 1)) := card_filter_le _ _
      _ = N + 1 := card_range _
  rw [Nat.mod_eq_of_lt (by omega)]
  -- π(N) + #composites = N − 1
  have hpc : Nat.primeCounting N = #({m ∈ range (N + 1) | m.Prime}) := by
    rw [Nat.primeCounting, Nat.primeCounting', Nat.count_eq_card_filter_range]
  have hsplit : #({m ∈ range (N + 1) | 2 ≤ m ∧ ¬ m.Prime}) + #({m ∈ range (N + 1) | m.Prime})
      = #({m ∈ range (N + 1) | 2 ≤ m}) := by
    rw [← card_union_of_disjoint]
    · congr 1
      ext m
      simp only [mem_union, mem_filter, mem_range]
      constructor
      · rintro (⟨h1, h2, _⟩ | ⟨h1, h2⟩)
        · exact ⟨h1, h2⟩
        · exact ⟨h1, h2.two_le⟩
      · rintro ⟨h1, h2⟩
        by_cases hp : m.Prime
        · exact Or.inr ⟨h1, hp⟩
        · exact Or.inl ⟨h1, h2, hp⟩
    · rw [disjoint_filter]
      intro m _ h1 h2
      exact h1.2 h2
  have hcard : #({m ∈ range (N + 1) | 2 ≤ m}) = N - 1 := by
    have : ({m ∈ range (N + 1) | 2 ≤ m}) = Ico 2 (N + 1) := by
      ext m; simp only [mem_filter, mem_range, mem_Ico]; omega
    rw [this, Nat.card_Ico]
    omega
  show _ = Nat.primeCounting N
  rw [hpc]
  omega

theorem wd_big (N : Nat) : 2 ≤ wd N ∧ N + 2 < 2 ^ wd N := by
  have hw : wd N = N / 1024 + 11 := by
    show N >>> 10 + 11 = _
    rw [Nat.shiftRight_eq_div_pow]
  rw [hw]
  refine ⟨by omega, ?_⟩
  have h1 : N / 1024 + 1 ≤ 2 ^ (N / 1024) := Nat.lt_two_pow_self
  have h2 : 2 ^ (N / 1024 + 11) = 2 ^ (N / 1024) * 2048 := by rw [pow_add]; norm_num
  have h3 : N < 1024 * (N / 1024 + 1) := by omega
  rw [h2]
  omega

theorem slow_correct : ∀ n, slow n = primeCountSpec n := by
  intro N
  obtain ⟨hw, hbig⟩ := wd_big N
  have e1 : Nat.shiftLeft (nat_lit 1) (wd N) = 2 ^ wd N := by
    show 1 <<< wd N = _
    rw [Nat.shiftLeft_eq, Nat.one_mul]
  have e2 : Nat.shiftLeft (nat_lit 1) (Nat.shiftLeft (wd N) (nat_lit 1)) = (2 ^ wd N) ^ 2 := by
    show 1 <<< (wd N <<< 1) = _
    rw [Nat.shiftLeft_eq, Nat.one_mul, Nat.shiftLeft_eq, ← pow_mul]
  have hx0 : 2 ≤ Nat.add (Nat.shiftRight N (nat_lit 6)) (nat_lit 16) := by
    show 2 ≤ N >>> 6 + 16; omega
  have hs := sqStep_ge N _ (sqStep_pos N _ hx0)
  unfold slow
  rw [e2, e1]
  exact go_eq N (wd N) _ hw hbig hs

/-! ## The fixed-divisor sieve -/

/-- The fixed-divisor sieve agrees with the general wheel sieve for every `N < 1369`
(evaluated by the kernel). -/
theorem fast_ok : ∀ N, N < 1369 → fast N = slow N := by decide +kernel

theorem impl_correct : ∀ n, impl n = primeCountSpec n := by
  intro n
  unfold impl
  rcases Nat.lt_or_ge n 1369 with h | h
  · have e : fast n = primeCountSpec n := (fast_ok n h).trans (slow_correct n)
    rw [show Nat.sub n 1368 = 0 by show n - 1368 = 0; omega]
    unfold fast at e
    exact e
  · obtain ⟨k, hk⟩ : ∃ k, Nat.sub n 1368 = k + 1 := ⟨n - 1369, by show n - 1368 = _; omega⟩
    rw [hk]
    exact slow_correct n

end Submission
