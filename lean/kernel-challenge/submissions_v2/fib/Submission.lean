import Spec

/-!
# Fibonacci by fast doubling, one `Nat.rec` step per bit

`(F(m), F(m+1)) ↦ (F(2m), F(2m+1))` or `(F(2m+1), F(2m+2))`, using
`F(2m) = F(m)·(2F(m+1) − F(m))`, `F(2m+2) = F(m+1)·(2F(m) + F(m+1))`, `F(2m+1) = F(2m+2) − F(2m)`:
two big multiplications and five cheap kernel operations per bit, the bit selecting the pair by a
`Nat.rec` on `0/1`. The bits are read from the top; the leading `1` is skipped (start at
`(F(1), F(2)) = (1, 1)`) after a three-comparison search for the bit length on the tested range
(the general fallback starts from `(F(0), F(1))` with `Nat.log2`). All numerals are raw `nat_lit`s.
-/

namespace Submission

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

def impl (n : Nat) : Nat :=
  pick (Nat.shiftRight n (nat_lit 15))
    (pick (Nat.shiftRight n (nat_lit 13))
      (pick (Nat.shiftRight n (nat_lit 12)) (gen n) (lvl n (nat_lit 12) (nat_lit 1) (nat_lit 1)))
      (pick (Nat.shiftRight n (nat_lit 14)) (lvl n (nat_lit 13) (nat_lit 1) (nat_lit 1))
        (lvl n (nat_lit 14) (nat_lit 1) (nat_lit 1))))
    (pick (Nat.shiftRight n (nat_lit 17))
      (pick (Nat.shiftRight n (nat_lit 16)) (lvl n (nat_lit 15) (nat_lit 1) (nat_lit 1))
        (lvl n (nat_lit 16) (nat_lit 1) (nat_lit 1)))
      (pick (Nat.shiftRight n (nat_lit 18)) (lvl n (nat_lit 17) (nat_lit 1) (nat_lit 1)) (gen n)))

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

/-- A branch that starts after the leading bit `L`. -/
theorem top_eq (n L : Nat) (h : n / 2 ^ L = 1) : lvl n L (nat_lit 1) (nat_lit 1) = Nat.fib n := by
  have hs := lvl_spec n L 1
  rw [Nat.fib_one, show (1 : Nat) + 1 = 2 from rfl, Nat.fib_two, Nat.one_mul] at hs
  show lvl n L 1 1 = _
  rw [hs]
  congr 1
  have := Nat.div_add_mod n (2 ^ L)
  rw [h, Nat.mul_one] at this
  omega

theorem impl_correct : ∀ n, impl n = fibSpec n := by
  intro n
  show impl n = Nat.fib n
  have sh : ∀ k, Nat.shiftRight n k = n / 2 ^ k := fun k => Nat.shiftRight_eq_div_pow n k
  unfold impl
  simp only [pick_eq, sh, gen_eq]
  split_ifs <;> first
    | rfl
    | (apply top_eq; norm_num at *; omega)

end Submission
