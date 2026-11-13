import Submission
namespace Submission

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


theorem brec4_eq {α : Sort _} (x y : Nat → Nat → Nat → Nat → α) (c : Bool) (n a b d : Nat) :
    Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat → α) x y c n a b d
      = if c = true then y n a b d else x n a b d := by
  cases c <;> rfl

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


def sel2a (n a b : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat)
    (fun n a b => share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2)) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))))); fin4Lc1 n (Nat.pow B (nat_lit 2)) (Nat.pow (Nat.sub (Nat.add (nat_lit 2) b) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))) (nat_lit 2)))
    (fun n a b => share B := (Nat.sub (Nat.add (nat_lit 4) b) (Nat.add a (Nat.add (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2)) (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))))); fin4Lc0 n (Nat.pow (Nat.sub (Nat.add a (Nat.div (Nat.land n (nat_lit 8)) (nat_lit 2))) (nat_lit 2)) (nat_lit 2)) (Nat.pow B (nat_lit 2)))
    (Nat.beq (Nat.land n (nat_lit 4)) (nat_lit 0)) n a b


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

/-- The last bit from the Fibonacci pair `(P, Q) = (F(h), F(h+1))`, `D = L(h)`, `h = n / 2`. -/
def finAb (n P Q D : Nat) : Nat :=
  Bool.rec (motive := fun _ => Nat → Nat → Nat → Nat → Nat)
    (fun n _ Q D => Nat.sub (Nat.add (Nat.mul Q D) (Nat.land n (nat_lit 2))) (nat_lit 1))
    (fun _ P _ D => Nat.mul P D)
    (Nat.beq (Nat.land n (nat_lit 1)) (nat_lit 0)) n P Q D

theorem finAb_spec (n : Nat) :
    finAb n (Nat.fib (n / 2)) (Nat.fib (n / 2 + 1))
      (Nat.sub (Nat.add (Nat.fib (n / 2 + 1)) (Nat.fib (n / 2 + 1))) (Nat.fib (n / 2))) = Nat.fib n := by
  unfold finAb
  simp only [brec4_eq, beq0, land1]
  have hn : n = 2 * (n / 2) + n % 2 := by omega
  split_ifs with h
  · show Nat.fib (n / 2) * (Nat.fib (n / 2 + 1) + Nat.fib (n / 2 + 1) - Nat.fib (n / 2)) = _
    have := dbl_X2 (n / 2)
    rw [show Nat.fib n = Nat.fib (2 * (n / 2)) by congr 1; omega]; exact this
  · have h1 : n % 2 = 1 := by omega
    have := odd_last (n / 2)
    show Nat.fib (n / 2 + 1) * (Nat.fib (n / 2 + 1) + Nat.fib (n / 2 + 1) - Nat.fib (n / 2))
      + Nat.land n 2 - 1 = _
    rw [land2, show Nat.fib n = Nat.fib (2 * (n / 2) + 1) by congr 1; omega,
      show 2 * (n / 2 % 2) = n / 2 % 2 + n / 2 % 2 by omega]
    exact this

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
first doubling and the `Bool.rec` last bit. -/
def chainAb0 (n s w X M Xd Md : Nat) : Nat :=
  tab0 X M (Nat.div n (Nat.pow 2 s)) fun lo hi =>
  sgc lo hi (Nat.land (Nat.div n (Nat.pow 2 (Nat.sub s 2))) 4) fun f l =>
  lucas (Nat.sub w 1) f l fun f l =>
  unL f l fun A B =>
  tab0 Xd Md (Nat.mod (Nat.div n 2) (Nat.pow 2 w)) fun lo hi =>
  comb0 A B lo hi fun P Q =>
  finAb n P Q (Nat.sub (Nat.add Q Q) P)

theorem chainAb0_spec (n s w t Kt Kd : Nat) (hs : s = w + 1) (hw : 1 ≤ w) (h : n < 2 ^ s * 2 ^ t)
    (hKt : 2 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 2 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainAb0 n s w (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 2 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainAb0
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
  rw [hN]
  exact finAb_spec n


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

end Submission
