/-!
# Congruences and two's-complement residues

`MEq n a b` is `n ∣ a − b` (core Lean has no `Int.ModEq`). `res q x` is the residue of `x` mod
`2^q` as a natural number; for `|x| < 2^(q-1)` the top bit is the sign and `x` is recovered
(`res_val`).
-/

namespace V9

def MEq (n a b : Int) : Prop := n ∣ a - b

namespace MEq

theorem refl (n a : Int) : MEq n a a := ⟨0, by simp⟩

theorem symm {n a b : Int} (h : MEq n a b) : MEq n b a := by
  obtain ⟨k, hk⟩ := h; exact ⟨-k, by rw [Int.mul_neg, ← hk]; grind⟩

theorem trans {n a b c : Int} (h1 : MEq n a b) (h2 : MEq n b c) : MEq n a c := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k + l, by rw [Int.mul_add, ← hk, ← hl]; grind⟩

theorem add {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a + c) (b + d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k + l, by rw [Int.mul_add, ← hk, ← hl]; grind⟩

theorem sub {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a - c) (b - d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  exact ⟨k - l, by rw [Int.mul_sub, ← hk, ← hl]; grind⟩

theorem mul {n a b c d : Int} (h1 : MEq n a b) (h2 : MEq n c d) : MEq n (a * c) (b * d) := by
  obtain ⟨k, hk⟩ := h1; obtain ⟨l, hl⟩ := h2
  refine ⟨k * c + b * l, ?_⟩
  have e : a * c - b * d = (a - b) * c + b * (c - d) := by grind
  rw [e, hk, hl]; grind

theorem mul_left {n a b : Int} (c : Int) (h : MEq n a b) : MEq n (c * a) (c * b) := (refl n c).mul h

theorem of_dvd {m n a b : Int} (hmn : m ∣ n) (h : MEq n a b) : MEq m a b := Int.dvd_trans hmn h

theorem emod (n a : Int) : MEq n (a % n) a := ⟨-(a / n), by rw [Int.emod_def]; grind⟩

theorem add_mul (n a k : Int) : MEq n (a + n * k) a := ⟨k, by grind⟩

theorem zero_of_dvd {n a : Int} (h : n ∣ a) : MEq n a 0 := by
  obtain ⟨k, hk⟩ := h; exact ⟨k, by rw [Int.sub_zero, hk]⟩

theorem of_eq {n a b : Int} (h : a = b) : MEq n a b := by rw [h]; exact refl n b

theorem self (n : Int) : MEq n n 0 := ⟨1, by grind⟩

theorem nat_sub {M t : Nat} {e : Int} (ht : t ≤ M) (h : MEq M t e) : MEq M ((M - t : Nat) : Int) (-e) := by
  rw [Int.ofNat_sub ht]; obtain ⟨k, hk⟩ := h; exact ⟨1 - k, by grind⟩

theorem emod_eq {n a b : Int} (h : MEq n a b) : a % n = b % n :=
  Int.emod_eq_emod_iff_emod_sub_eq_zero.2 (Int.dvd_iff_emod_eq_zero.1 h)

end MEq

/-- Residue of `x` mod `2^q`. -/
def res (q : Nat) (x : Int) : Nat := (x % (2 ^ q : Int)).toNat

theorem two_pow_pos (q : Nat) : (0 : Int) < 2 ^ q := Int.pow_pos (by decide)

theorem cast_two_pow (q : Nat) : ((2 ^ q : Nat) : Int) = (2 : Int) ^ q := by rw [Int.natCast_pow]; rfl

theorem pow2_dvd {m n : Nat} (h : m ≤ n) : (2 : Int) ^ m ∣ 2 ^ n := by
  rw [← cast_two_pow, ← cast_two_pow]; exact Int.natCast_dvd_natCast.2 (Nat.pow_dvd_pow 2 h)

theorem res_cast (q : Nat) (x : Int) : ((res q x : Nat) : Int) = x % 2 ^ q :=
  Int.toNat_of_nonneg (Int.emod_nonneg _ (Int.ne_of_gt (two_pow_pos q)))

theorem res_lt (q : Nat) (x : Int) : res q x < 2 ^ q := by
  have h := Int.emod_lt_of_pos x (two_pow_pos q)
  have h2 := res_cast q x
  have : ((res q x : Nat) : Int) < ((2 ^ q : Nat) : Int) := by rw [h2, cast_two_pow]; exact h
  exact Int.ofNat_lt.1 this

theorem res_meq (q : Nat) (x : Int) : MEq (2 ^ q) (res q x) x := by
  rw [res_cast]; exact MEq.emod _ _

theorem pow_succ_two (q : Nat) : (2 : Int) ^ (q + 1) = 2 * 2 ^ q := by
  rw [Int.pow_succ, Int.mul_comm]

/-- The sign bit and the value of a residue of a small integer. -/
theorem res_val (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) :
    res (q + 1) x >>> q = (if x < 0 then 1 else 0) ∧
    ((res (q + 1) x : Nat) : Int) - ((res (q + 1) x >>> q : Nat) : Int) * 2 ^ (q + 1) = x := by
  have hP : (0 : Int) < 2 ^ q := two_pow_pos q
  have hx' : -(2 ^ q : Int) < x ∧ x < 2 ^ q := by
    have : ((x.natAbs : Nat) : Int) < ((2 ^ q : Nat) : Int) := Int.ofNat_lt.2 hx
    rw [cast_two_pow] at this
    omega
  have hc := res_cast (q + 1) x
  rw [pow_succ_two] at hc
  rw [Nat.shiftRight_eq_div_pow]
  by_cases hneg : x < 0
  · have e : x % (2 * 2 ^ q) = x + 2 * 2 ^ q := by
      rw [show x = (x + 2 * 2 ^ q) + (2 * 2 ^ q) * (-1) by grind, Int.add_mul_emod_self_left]
      rw [Int.emod_eq_of_lt (by omega) (by omega)]; grind
    rw [e] at hc
    have hd : res (q + 1) x / 2 ^ q = 1 := by
      have : ((res (q + 1) x / 2 ^ q : Nat) : Int) = 1 := by
        rw [Int.natCast_ediv, hc, cast_two_pow]
        exact ((Int.ediv_emod_unique (r := x + 2 ^ q) (q := 1) hP).2 ⟨by omega, by omega, by omega⟩).1
      exact Int.ofNat_inj.1 this
    rw [hd, if_pos hneg]; refine ⟨rfl, ?_⟩
    rw [hc, pow_succ_two]; simp only [Int.natCast_one]; omega
  · have e : x % (2 * 2 ^ q) = x := Int.emod_eq_of_lt (by omega) (by omega)
    rw [e] at hc
    have hd : res (q + 1) x / 2 ^ q = 0 := by
      have : ((res (q + 1) x / 2 ^ q : Nat) : Int) = 0 := by
        rw [Int.natCast_ediv, hc, cast_two_pow]
        exact Int.ediv_eq_zero_of_lt (by omega) (by omega)
      exact Int.ofNat_inj.1 this
    rw [hd, if_neg hneg]; refine ⟨rfl, ?_⟩
    rw [hc]; simp only [Int.natCast_zero]; omega

/-- Equal residues of two small integers mean equal integers. -/
theorem res_zero (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) (h : res (q + 1) x = 0) : x = 0 := by
  have := (res_val q x hx).2
  rw [h] at this; simpa using this.symm

end V9
