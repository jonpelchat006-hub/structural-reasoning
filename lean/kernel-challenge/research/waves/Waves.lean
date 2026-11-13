import Mathlib.Combinatorics.Enumerative.Partition.Basic
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic

/-!
# The soundtrack of partitions into parts at most 3

Rung 1 of the "answer as a frequency equation" idea (Jonathan, Oct 26).

* The floor holds the 1s (one way to make every number), level 2 marks where a 2 can be added,
  level 3 marks where a 3 can be added. Each level repeats with its own period, so each one is
  a frequency.
* `card_restricted_le_three`: the number of partitions of `n` into parts `≤ 3` (Mathlib's
  `Nat.Partition.restricted`) equals the count of multiplicity triples `a + 2b + 3c = n`.
* `p3_eq_round`: that count is `round ((n + 3)² / 12) = ((n + 3)² + 6) / 12` for every `n`,
  so it is a fixed formula with no case split and no loop.
* `p3_waves`: Sylvester's wave form (1857) of the same count, over `ℝ`:
  `p₃(n) = (n + 3)² / 12 - 7 / 72 + (-1)^n / 8 + (2 / 9) · cos (2πn / 3)`:
  a slow drone from the floor, a note of period 2 and a note of period 3.
* `soundtrack3`: the formula written with kernel `Nat` primitives, proved equal to the count.
-/

open Finset

namespace Waves

/-! ## The count as a sum over the number of 3s -/

/-- For each number `c` of 3s, the rest `n - 3c` is made of 1s and 2s in `⌊(n - 3c)/2⌋ + 1` ways. -/
def p3 (n : ℕ) : ℕ := ∑ c ∈ range (n / 3 + 1), ((n - 3 * c) / 2 + 1)

/-- One full turn of the two notes (period 6) adds `n + 6`. -/
theorem p3_add_six (n : ℕ) : p3 (n + 6) = p3 n + (n + 6) := by
  unfold p3
  rw [show (n + 6) / 3 + 1 = (n / 3 + 1) + 2 by omega, sum_range_succ', sum_range_succ']
  have h : ∀ i ∈ range (n / 3 + 1), (n + 6 - 3 * (i + 1 + 1)) / 2 + 1 = (n - 3 * i) / 2 + 1 := by
    intro i _; congr 2; omega
  rw [sum_congr rfl h]
  omega

/-- The closed form satisfies the same turn. -/
theorem round_add_six (n : ℕ) : ((n + 6 + 3) ^ 2 + 6) / 12 = ((n + 3) ^ 2 + 6) / 12 + (n + 6) := by
  rw [show (n + 6 + 3) ^ 2 + 6 = (n + 3) ^ 2 + 6 + (n + 6) * 12 by ring, Nat.add_mul_div_right _ _ (by norm_num)]

/-- **The count is a fixed formula:** `p₃(n) = round ((n + 3)² / 12)` for every `n`. -/
theorem p3_eq_round (n : ℕ) : p3 n = ((n + 3) ^ 2 + 6) / 12 := by
  induction n using Nat.strong_induction_on with
  | _ n ih =>
    rcases Nat.lt_or_ge n 6 with h | h
    · interval_cases n <;> decide
    · obtain ⟨m, rfl⟩ : ∃ m, n = m + 6 := ⟨n - 6, by omega⟩
      rw [p3_add_six, ih m (by omega), round_add_six]

/-! ## Partitions into parts `≤ 3` are multiplicity triples -/

/-- The triples `(a, b, c)` of 1s, 2s and 3s with `a + 2b + 3c = n`, listed by the number of 3s
and then of 2s. -/
def triples (n : ℕ) : Finset (ℕ × ℕ × ℕ) :=
  (range (n / 3 + 1)).biUnion fun c =>
    (range ((n - 3 * c) / 2 + 1)).image fun b => (n - 3 * c - 2 * b, b, c)

theorem mem_triples {n : ℕ} {t : ℕ × ℕ × ℕ} : t ∈ triples n ↔ t.1 + 2 * t.2.1 + 3 * t.2.2 = n := by
  rcases t with ⟨a, b, c⟩
  simp only [triples, mem_biUnion, mem_range, mem_image, Prod.mk.injEq]
  constructor
  · rintro ⟨c', hc, b', hb, h1, h2, h3⟩
    subst h2 h3
    omega
  · intro h
    exact ⟨c, by omega, b, by omega, by omega, rfl, rfl⟩

theorem card_triples (n : ℕ) : (triples n).card = p3 n := by
  unfold triples p3
  rw [card_biUnion]
  · refine sum_congr rfl fun c _ => ?_
    rw [card_image_of_injective _ (fun b b' h => by simp only [Prod.mk.injEq] at h; exact h.2.1),
      card_range]
  · intro c _ c' _ hne
    simp only [Function.onFun, disjoint_left, mem_image]
    rintro t ⟨b, _, rfl⟩ ⟨b', _, h⟩
    simp only [Prod.mk.injEq] at h
    exact hne h.2.2.symm

/-- A multiset of parts in `{1, 2, 3}` is its 1s, its 2s and its 3s. -/
theorem eq_replicate_of_le_three {s : Multiset ℕ} (hs : ∀ i ∈ s, 0 < i ∧ i ≤ 3) :
    s = Multiset.replicate (s.count 1) 1 + Multiset.replicate (s.count 2) 2 +
      Multiset.replicate (s.count 3) 3 := by
  ext x
  simp only [Multiset.count_add, Multiset.count_replicate]
  by_cases hx : x ∈ s
  · obtain ⟨h0, h3⟩ := hs x hx
    interval_cases x <;> simp
  · have h0 : s.count x = 0 := Multiset.count_eq_zero.mpr hx
    split_ifs <;> subst_vars <;> simp_all

theorem sum_replicate_three (a b c : ℕ) :
    (Multiset.replicate a 1 + Multiset.replicate b 2 + Multiset.replicate c 3).sum =
      a + 2 * b + 3 * c := by
  simp [Multiset.sum_replicate]
  ring

/-- The partition with `a` 1s, `b` 2s and `c` 3s. -/
def ofTriple (n : ℕ) (t : ℕ × ℕ × ℕ) (h : t.1 + 2 * t.2.1 + 3 * t.2.2 = n) : n.Partition where
  parts := Multiset.replicate t.1 1 + Multiset.replicate t.2.1 2 + Multiset.replicate t.2.2 3
  parts_pos := by
    intro i hi
    simp only [Multiset.mem_add, Multiset.mem_replicate] at hi
    omega
  parts_sum := by rw [sum_replicate_three]; exact h

/-- **Partitions into parts at most 3 are counted by `p₃`.** -/
theorem card_restricted_le_three (n : ℕ) :
    (Nat.Partition.restricted n (· ≤ 3)).card = p3 n := by
  rw [← card_triples]
  refine card_bij (fun p _ => (p.parts.count 1, p.parts.count 2, p.parts.count 3)) ?_ ?_ ?_
  · intro p hp
    simp only [Nat.Partition.restricted, mem_filter, mem_univ, true_and] at hp
    rw [mem_triples]
    have hdec := eq_replicate_of_le_three fun i hi => ⟨p.parts_pos hi, hp i hi⟩
    have hs := p.parts_sum
    rw [hdec, sum_replicate_three] at hs
    exact hs
  · intro p hp q hq hpq
    simp only [Nat.Partition.restricted, mem_filter, mem_univ, true_and] at hp hq
    simp only [Prod.mk.injEq] at hpq
    obtain ⟨h1, h2, h3⟩ := hpq
    apply Nat.Partition.ext
    rw [eq_replicate_of_le_three fun i hi => ⟨p.parts_pos hi, hp i hi⟩,
      eq_replicate_of_le_three fun i hi => ⟨q.parts_pos hi, hq i hi⟩, h1, h2, h3]
  · intro t ht
    refine ⟨ofTriple n t (mem_triples.mp ht), ?_, ?_⟩
    · simp only [Nat.Partition.restricted, mem_filter, mem_univ, true_and, ofTriple]
      intro i hi
      simp only [Multiset.mem_add, Multiset.mem_replicate] at hi
      omega
    · rcases t with ⟨a, b, c⟩
      simp [ofTriple, Multiset.count_replicate]

/-- **The partitions of `n` into parts at most 3 number `round ((n + 3)² / 12)`.** -/
theorem card_restricted_le_three_eq (n : ℕ) :
    (Nat.Partition.restricted n (· ≤ 3)).card = ((n + 3) ^ 2 + 6) / 12 := by
  rw [card_restricted_le_three, p3_eq_round]

/-! ## The waves: a drone, a note of period 2 and a note of period 3 -/

open Real in
/-- The period-3 note takes only two values. -/
theorem cos_third (n : ℕ) : cos (2 * π * n / 3) = if n % 3 = 0 then 1 else -1 / 2 := by
  have h : (n : ℝ) = ((n % 3 : ℕ) : ℝ) + 3 * ((n / 3 : ℕ) : ℝ) := by
    exact_mod_cast (Nat.mod_add_div n 3).symm
  rw [h, show 2 * π * (((n % 3 : ℕ) : ℝ) + 3 * ((n / 3 : ℕ) : ℝ)) / 3 =
      2 * π * ((n % 3 : ℕ) : ℝ) / 3 + ((n / 3 : ℕ) : ℝ) * (2 * π) by ring, cos_add_nat_mul_two_pi]
  have hr : n % 3 < 3 := Nat.mod_lt _ (by norm_num)
  generalize n % 3 = r at hr ⊢
  interval_cases r
  · simp
  · rw [show 2 * π * ((1 : ℕ) : ℝ) / 3 = π - π / 3 by push_cast; ring, cos_pi_sub,
      cos_pi_div_three]
    norm_num
  · rw [show 2 * π * ((2 : ℕ) : ℝ) / 3 = π / 3 + π by push_cast; ring, cos_add_pi,
      cos_pi_div_three]
    norm_num

open Real in
/-- **Sylvester's waves for parts at most 3**: the count is a drone from the floor,
`(n + 3)² / 12 - 7 / 72`, plus a note of period 2, `(-1)ⁿ / 8`, plus a note of period 3,
`(2 / 9) cos (2πn / 3)`. Exact for every `n`. -/
theorem p3_waves (n : ℕ) :
    (p3 n : ℝ) = ((n : ℝ) + 3) ^ 2 / 12 - 7 / 72 + (-1) ^ n / 8 + 2 / 9 * cos (2 * π * n / 3) := by
  induction n using Nat.strong_induction_on with
  | _ n ih =>
    rw [cos_third]
    rcases Nat.lt_or_ge n 6 with h | h
    · interval_cases n <;> simp [p3, Finset.sum_range_succ] <;> norm_num
    · obtain ⟨m, rfl⟩ : ∃ m, n = m + 6 := ⟨n - 6, by omega⟩
      have hm := ih m (by omega)
      rw [cos_third] at hm
      rw [p3_add_six, show (m + 6) % 3 = m % 3 by omega]
      push_cast
      rw [hm, pow_add]
      ring

/-! ## The formula as a kernel computation -/

/-- `round ((n + 3)² / 12)` with the kernel's `Nat` primitives: four operations for any `n`. -/
def soundtrack3 (n : ℕ) : ℕ :=
  Nat.div (Nat.add (Nat.mul (Nat.add n 3) (Nat.add n 3)) 6) 12

theorem soundtrack3_eq (n : ℕ) : soundtrack3 n = (Nat.Partition.restricted n (· ≤ 3)).card := by
  rw [card_restricted_le_three_eq, soundtrack3]
  show ((n + 3) * (n + 3) + 6) / 12 = _
  rw [sq]

example : soundtrack3 1000000 = 83333833334 := by decide

end Waves

#print axioms Waves.card_restricted_le_three_eq
#print axioms Waves.p3_waves
#print axioms Waves.soundtrack3_eq
