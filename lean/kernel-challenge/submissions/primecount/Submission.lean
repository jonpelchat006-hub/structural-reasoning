import Spec

/-!
# Prime counting by a packed sieve

Every `m ≤ N` owns one slot of `w = log₂ N + 2` bits inside a single natural number.
For each `d = 2, …, ⌊√N⌋` one closed-form geometric series (a single kernel division)
puts a `1` in the slots `d², d² + d, …, ≤ N`, and the marks are combined with one `|||`.
A slot is marked exactly when its index is composite. Since `B = 2^w ≡ 1 (mod B − 1)`,
reducing the packed number modulo `B − 1` adds up all slots at once, so
`π(N) = N − 1 − #composites` costs about `√N` kernel steps of big-number arithmetic.

Proof outline:
* `enc a L = Σ_{m<L} a m · 2^(w·m)` encodes a slot function.
* `prog_eq`: one closed-form series encodes the indicator of `{d², d² + d, …} ∩ [0, N]`.
* `enc_or`: `|||` acts slot by slot on encodings with small slots.
* `marks_eq`: the loop encodes "has a divisor `2 ≤ d ≤ √N` with `d² ≤ m`".
* `enc_mod`: the slot sum is the value modulo `2^w − 1`.
* `marked_iff`: for `m ≤ N`, marked ↔ `2 ≤ m ∧ ¬ m.Prime` (via `Nat.minFac`).
-/

namespace Submission

open Finset

/-! ## Implementation -/

/-- `Σ_{j<J} B^(d·j)` in closed form. -/
def rep (B d J : Nat) : Nat := (B ^ (d * J) - 1) / (B ^ d - 1)

/-- Marks from the divisors `d = 2, …, k + 1`. -/
def marks (B N : Nat) : Nat → Nat
  | 0 => 0
  | k + 1 => marks B N k |||
      B ^ ((k + 2) * (k + 2)) * rep B (k + 2) ((N - (k + 2) * (k + 2)) / (k + 2) + 1)

def impl (N : Nat) : Nat :=
  if N < 2 then 0 else
    N - 1 - marks (2 ^ (N.log2 + 2)) N (Nat.sqrt N - 1) % (2 ^ (N.log2 + 2) - 1)

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

theorem rep_eq (B d J : Nat) (hB : 2 ≤ B) (hd : 1 ≤ d) :
    rep B d J = ∑ j ∈ range J, (B ^ d) ^ j := by
  have hq : 2 ≤ B ^ d := by
    calc 2 ≤ B := hB
      _ = B ^ 1 := (pow_one B).symm
      _ ≤ B ^ d := Nat.pow_le_pow_right (by omega) hd
  unfold rep
  rw [pow_mul, ← geom_mul (B ^ d) (by omega) J, Nat.add_sub_cancel,
    Nat.mul_div_cancel_left _ (by omega)]

/-! ## Encodings with `w`-bit slots -/

section Enc

variable (w : Nat)

def enc (a : Nat → Nat) (L : Nat) : Nat := ∑ m ∈ range L, a m * 2 ^ (w * m)

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

theorem enc_congr {a b : Nat → Nat} : ∀ L, (∀ m, m < L → a m = b m) → enc w a L = enc w b L
  | 0, _ => rfl
  | L + 1, h => by
    rw [enc_succ, enc_succ, enc_congr L (fun m hm => h m (by omega)), h L (by omega)]

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

end Enc

/-! ## One divisor's marks -/

/-- Indicator of `m ∈ {d², d² + d, …}` with `m ≤ N`. -/
def ind (N d m : Nat) : Nat := if d * d ≤ m ∧ d ∣ m ∧ m ≤ N then 1 else 0

theorem prog_eq (w N d : Nat) (hw : 1 ≤ w) (hd : 2 ≤ d) (hdN : d * d ≤ N) :
    (2 ^ w) ^ (d * d) * rep (2 ^ w) d ((N - d * d) / d + 1) = enc w (ind N d) (N + 1) := by
  have hB : 2 ≤ 2 ^ w := by
    calc 2 = 2 ^ 1 := rfl
      _ ≤ 2 ^ w := Nat.pow_le_pow_right (by omega) hw
  rw [rep_eq _ _ _ hB (by omega), mul_sum]
  unfold enc ind
  simp only [ite_mul, one_mul, zero_mul]
  rw [← sum_filter]
  symm
  apply sum_nbij' (fun m => (m - d * d) / d) (fun j => d * d + d * j)
  · intro m hm
    simp only [mem_filter, mem_range] at hm ⊢
    obtain ⟨_, h1, h2, h3⟩ := hm
    apply Nat.lt_succ_of_le
    exact Nat.div_le_div_right (by omega)
  · intro j hj
    simp only [mem_filter, mem_range] at hj ⊢
    have h1 : d * j ≤ N - d * d := by
      have := Nat.div_mul_le_self (N - d * d) d
      have h2 : j ≤ (N - d * d) / d := by omega
      calc d * j ≤ d * ((N - d * d) / d) := Nat.mul_le_mul_left _ h2
        _ = (N - d * d) / d * d := Nat.mul_comm _ _
        _ ≤ N - d * d := this
    refine ⟨by omega, by omega, ?_, by omega⟩
    exact Nat.dvd_add (Dvd.intro _ rfl) (Dvd.intro _ rfl)
  · intro m hm
    simp only [mem_filter, mem_range] at hm
    obtain ⟨_, h1, h2, _⟩ := hm
    have hdv : d ∣ m - d * d := Nat.dvd_sub h2 (Dvd.intro _ rfl)
    show d * d + d * ((m - d * d) / d) = m
    rw [Nat.mul_div_cancel' hdv]
    omega
  · intro j _
    show (d * d + d * j - d * d) / d = j
    rw [Nat.add_sub_cancel_left, Nat.mul_div_cancel_left _ (by omega)]
  · intro m hm
    simp only [mem_filter, mem_range] at hm
    obtain ⟨_, h1, h2, _⟩ := hm
    have hdv : d ∣ m - d * d := Nat.dvd_sub h2 (Dvd.intro _ rfl)
    rw [pow_mul 2 w m, ← pow_mul (2 ^ w) d, ← pow_add]
    congr 1
    rw [Nat.mul_div_cancel' hdv]
    omega

/-! ## The whole sieve -/

open Classical in
/-- Indicator of "has a divisor `2 ≤ d ≤ k + 1` with `d² ≤ m`" (and `m ≤ N`). -/
noncomputable def mk (N k m : Nat) : Nat :=
  if ∃ d, 2 ≤ d ∧ d ≤ k + 1 ∧ d * d ≤ m ∧ d ∣ m ∧ m ≤ N then 1 else 0

theorem mk_le (N k m : Nat) : mk N k m ≤ 1 := by
  unfold mk; split <;> omega

theorem ind_le (N d m : Nat) : ind N d m ≤ 1 := by
  unfold ind; split <;> omega

theorem marks_eq (w N : Nat) (hw : 1 ≤ w) :
    ∀ k, (k + 1) * (k + 1) ≤ N → marks (2 ^ w) N k = enc w (mk N k) (N + 1)
  | 0, _ => by
    simp only [marks]
    symm
    unfold enc
    apply sum_eq_zero
    intro m _
    have : mk N 0 m = 0 := by
      unfold mk
      rw [if_neg]
      rintro ⟨d, h1, h2, _⟩
      omega
    rw [this, zero_mul]
  | k + 1, hk => by
    have hB : 1 < 2 ^ w := by
      calc 1 < 2 ^ 1 := by norm_num
        _ ≤ 2 ^ w := Nat.pow_le_pow_right (by omega) hw
    have hk' : (k + 1) * (k + 1) ≤ N :=
      le_trans (Nat.mul_le_mul (by omega) (by omega)) hk
    simp only [marks]
    rw [marks_eq w N hw k hk', prog_eq w N (k + 2) hw (by omega) hk,
      enc_or w _ _ _ (fun m _ => by have := mk_le N k m; omega)
        (fun m _ => by have := ind_le N (k + 2) m; omega)]
    apply enc_congr
    intro m _
    have hiff : (∃ d, 2 ≤ d ∧ d ≤ k + 1 + 1 ∧ d * d ≤ m ∧ d ∣ m ∧ m ≤ N) ↔
        ((∃ d, 2 ≤ d ∧ d ≤ k + 1 ∧ d * d ≤ m ∧ d ∣ m ∧ m ≤ N) ∨
          ((k + 2) * (k + 2) ≤ m ∧ k + 2 ∣ m ∧ m ≤ N)) := by
      constructor
      · rintro ⟨d, h1, h2, h3, h4, h5⟩
        rcases Nat.lt_or_ge d (k + 2) with hlt | hge
        · exact Or.inl ⟨d, h1, by omega, h3, h4, h5⟩
        · have e : d = k + 2 := by omega
          subst e
          exact Or.inr ⟨h3, h4, h5⟩
      · rintro (⟨d, h1, h2, h3, h4, h5⟩ | ⟨h3, h4, h5⟩)
        · exact ⟨d, h1, by omega, h3, h4, h5⟩
        · exact ⟨k + 2, by omega, by omega, h3, h4, h5⟩
    unfold mk ind
    by_cases hA : ∃ d, 2 ≤ d ∧ d ≤ k + 1 ∧ d * d ≤ m ∧ d ∣ m ∧ m ≤ N <;>
    by_cases hB' : (k + 2) * (k + 2) ≤ m ∧ k + 2 ∣ m ∧ m ≤ N
    · rw [if_pos hA, if_pos hB', if_pos (hiff.mpr (Or.inl hA))]; rfl
    · rw [if_pos hA, if_neg hB', if_pos (hiff.mpr (Or.inl hA))]; rfl
    · rw [if_neg hA, if_pos hB', if_pos (hiff.mpr (Or.inr hB'))]; rfl
    · rw [if_neg hA, if_neg hB', if_neg (fun h => (hiff.mp h).elim hA hB')]; rfl

/-! ## Number theory -/

theorem marked_iff (N m : Nat) (hm : m ≤ N) :
    (∃ d, 2 ≤ d ∧ d ≤ Nat.sqrt N - 1 + 1 ∧ d * d ≤ m ∧ d ∣ m ∧ m ≤ N) ↔ (2 ≤ m ∧ ¬ m.Prime) := by
  constructor
  · rintro ⟨d, h1, _, h3, h4, _⟩
    have hdm : d < m := by
      have : d * 2 ≤ d * d := Nat.mul_le_mul_left _ h1
      omega
    refine ⟨by omega, fun hp => ?_⟩
    rcases hp.eq_one_or_self_of_dvd d h4 with h | h <;> omega
  · rintro ⟨h2, hnp⟩
    have hm1 : m ≠ 1 := by omega
    have hmin := Nat.minFac_prime hm1
    have hsq := Nat.minFac_sq_le_self (by omega) hnp
    rw [pow_two] at hsq
    refine ⟨m.minFac, hmin.two_le, ?_, hsq, Nat.minFac_dvd m, hm⟩
    have : m.minFac ≤ Nat.sqrt N := Nat.le_sqrt.mpr (le_trans hsq hm)
    omega

/-! ## Main correctness -/

theorem impl_correct : ∀ n, impl n = primeCountSpec n := by
  intro N
  unfold impl primeCountSpec
  by_cases hN : N < 2
  · rw [if_pos hN]
    rcases (by omega : N = 0 ∨ N = 1) with rfl | rfl <;> decide
  rw [if_neg hN]
  have hN2 : 2 ≤ N := by omega
  set w := N.log2 + 2 with hw
  have hs : 1 ≤ Nat.sqrt N := Nat.le_sqrt.mpr (by omega)
  have hsq : (Nat.sqrt N - 1 + 1) * (Nat.sqrt N - 1 + 1) ≤ N := by
    rw [Nat.sub_add_cancel hs]
    have := Nat.sqrt_le' N
    rwa [pow_two] at this
  rw [marks_eq w N (by omega) _ hsq, enc_mod w _ _ (by omega)]
  -- the slot sum counts composites
  have hsum : (∑ m ∈ range (N + 1), mk N (Nat.sqrt N - 1) m)
      = #({m ∈ range (N + 1) | 2 ≤ m ∧ ¬ m.Prime}) := by
    unfold mk
    rw [sum_boole]
    simp only [Nat.cast_id]
    congr 1
    ext m
    simp only [mem_filter, mem_range]
    constructor
    · rintro ⟨hm, h⟩
      exact ⟨hm, (marked_iff N m (by omega)).mp h⟩
    · rintro ⟨hm, h⟩
      exact ⟨hm, (marked_iff N m (by omega)).mpr h⟩
  have hbig : N + 1 < 2 ^ w - 1 := by
    have h1 := @Nat.lt_log2_self N
    have h2 : 2 ^ w = 2 * 2 ^ (N.log2 + 1) := by rw [hw, pow_succ]; ring
    omega
  have hle : #({m ∈ range (N + 1) | 2 ≤ m ∧ ¬ m.Prime}) ≤ N + 1 := by
    calc _ ≤ #(range (N + 1)) := card_filter_le _ _
      _ = N + 1 := card_range _
  rw [hsum, Nat.mod_eq_of_lt (by omega)]
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
  rw [hpc]
  omega

end Submission
