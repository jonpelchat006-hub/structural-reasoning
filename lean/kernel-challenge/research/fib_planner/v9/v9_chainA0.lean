import Submission
namespace Submission

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
