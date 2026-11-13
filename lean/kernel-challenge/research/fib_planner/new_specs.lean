/-! ### v8: any top table, and the hybrid chains (Oct 18)

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

/-- The hybrid chain with two last bits: the top `t` bits by `tab`, `c` doublings in the `(F, L)` form,
the conversion, `w − c` Lucas-pair doublings, the low bits `(n / 4) mod 2^w` by a second `tab` and
`combL`, the selected doubling (bit `1`), then the last bit. -/
def chainH (n s w c X M Xd Md : Nat) : Nat :=
  tab X M (Nat.div n (Nat.pow 2 s)) fun a b =>
  dbl1 a b fun f l =>
  lucas (Nat.sub c 1) f l fun f l =>
  conv f l fun p q =>
  lpair (Nat.sub w c) p q fun p q =>
  tab Xd Md (Nat.mod (Nat.div n 4) (Nat.pow 2 w)) fun u v =>
  combL p q u v fun P Q =>
  selL (Nat.mod (Nat.div n 4) 2) (Nat.mod (Nat.div n 2) 2) P Q fun A B =>
  finL (Nat.mod n 2) (Nat.mod (Nat.div n 2) 2) A B

/-- The hybrid chain with three last bits (two selected doublings). -/
def chainH3 (n s w c X M Xd Md : Nat) : Nat :=
  tab X M (Nat.div n (Nat.pow 2 s)) fun a b =>
  dbl1 a b fun f l =>
  lucas (Nat.sub c 1) f l fun f l =>
  conv f l fun p q =>
  lpair (Nat.sub w c) p q fun p q =>
  tab Xd Md (Nat.mod (Nat.div n 8) (Nat.pow 2 w)) fun u v =>
  combL p q u v fun P Q =>
  selL (Nat.mod (Nat.div n 8) 2) (Nat.mod (Nat.div n 4) 2) P Q fun A B =>
  selL (Nat.mod (Nat.div n 4) 2) (Nat.mod (Nat.div n 2) 2) A B fun A B =>
  finL (Nat.mod n 2) (Nat.mod (Nat.div n 2) 2) A B

/-- The index reached by `c` doublings in one form and `w − c` in the other: `m · 2^w`. -/
theorem idx_eq (m c w : Nat) (hc : 1 ≤ c) (hcw : c ≤ w) :
    2 * m * 2 ^ (c - 1) * 2 ^ (w - c) = m * 2 ^ w := by
  have e : 2 * m * 2 ^ (c - 1) * 2 ^ (w - c) = m * (2 * 2 ^ (c - 1) * 2 ^ (w - c)) := by ring
  rw [e, ← pow_succ', ← pow_add, show c - 1 + 1 + (w - c) = w by omega]

theorem even_idx (m c : Nat) : 2 * m * 2 ^ (c - 1) % 2 = 0 := by
  rw [Nat.mul_assoc]; exact Nat.mul_mod_right 2 _

theorem chainH_spec (n s w c t Kt Kd : Nat) (hs : s = w + 2) (hc : 1 ≤ c) (hcw : c ≤ w)
    (h : n < 2 ^ s * 2 ^ t) (hn : 4 ≤ n) (hKt : 1 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 1 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainH n s w c (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 4 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainH
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab_spec Kt _ hKt (fib_tab_bound hm hbt)]
  try dsimp only
  rw [dbl1_spec, show Nat.sub c 1 = c - 1 from rfl, lucas_spec (c - 1) _ _ (by omega)]
  try dsimp only
  rw [conv_spec]
  try dsimp only
  rw [show Nat.sub w c = w - c from rfl, lpair_spec (w - c) _ _ (even_idx _ _)]
  try dsimp only
  rw [show Nat.mod (Nat.div n 4) (Nat.pow 2 w) = n / 4 % 2 ^ w from rfl,
    tab_spec Kd _ hKd (fib_tab_bound hd hb)]
  try dsimp only
  rw [combL_spec]
  have hN : 2 * (n / 2 ^ s) * 2 ^ (c - 1) * 2 ^ (w - c) + n / 4 % 2 ^ w = n / 4 := by
    rw [idx_eq _ _ _ hc hcw, hs, pow_add, show (2 : Nat) ^ 2 = 4 by rfl, Nat.mul_comm (2 ^ w) 4,
      ← Nat.div_div_eq_div_mul, Nat.div_add_mod']
  rw [hN, show Nat.mod (Nat.div n 4) 2 = n / 4 % 2 from rfl,
    show Nat.mod (Nat.div n 2) 2 = n / 2 % 2 from rfl,
    selL_spec (n / 4) (n / 2 % 2) (by omega) (Nat.mod_lt _ (by decide))]
  have e4 : 2 * (n / 4) + n / 2 % 2 = n / 2 := by omega
  rw [e4, show Nat.mod n 2 = n % 2 from rfl, finL_spec _ _ (Nat.mod_lt _ (by decide))]
  congr 1
  omega

theorem chainH3_spec (n s w c t Kt Kd : Nat) (hs : s = w + 3) (hc : 1 ≤ c) (hcw : c ≤ w)
    (h : n < 2 ^ s * 2 ^ t) (hn : 8 ≤ n) (hKt : 1 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 1 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainH3 n s w c (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 8 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainH3
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab_spec Kt _ hKt (fib_tab_bound hm hbt)]
  try dsimp only
  rw [dbl1_spec, show Nat.sub c 1 = c - 1 from rfl, lucas_spec (c - 1) _ _ (by omega)]
  try dsimp only
  rw [conv_spec]
  try dsimp only
  rw [show Nat.sub w c = w - c from rfl, lpair_spec (w - c) _ _ (even_idx _ _)]
  try dsimp only
  rw [show Nat.mod (Nat.div n 8) (Nat.pow 2 w) = n / 8 % 2 ^ w from rfl,
    tab_spec Kd _ hKd (fib_tab_bound hd hb)]
  try dsimp only
  rw [combL_spec]
  have hN : 2 * (n / 2 ^ s) * 2 ^ (c - 1) * 2 ^ (w - c) + n / 8 % 2 ^ w = n / 8 := by
    rw [idx_eq _ _ _ hc hcw, hs, pow_add, show (2 : Nat) ^ 3 = 8 by rfl, Nat.mul_comm (2 ^ w) 8,
      ← Nat.div_div_eq_div_mul, Nat.div_add_mod']
  rw [hN, show Nat.mod (Nat.div n 8) 2 = n / 8 % 2 from rfl,
    show Nat.mod (Nat.div n 4) 2 = n / 4 % 2 from rfl,
    selL_spec (n / 8) (n / 4 % 2) (by omega) (Nat.mod_lt _ (by decide))]
  have e8 : 2 * (n / 8) + n / 4 % 2 = n / 4 := by omega
  rw [e8, show Nat.mod (Nat.div n 2) 2 = n / 2 % 2 from rfl,
    selL_spec (n / 4) (n / 2 % 2) (by omega) (Nat.mod_lt _ (by decide))]
  have e4 : 2 * (n / 4) + n / 2 % 2 = n / 2 := by omega
  rw [e4, show Nat.mod n 2 = n % 2 from rfl, finL_spec _ _ (Nat.mod_lt _ (by decide))]
  congr 1
  omega

/-- `chainA` with any top table (`t` bits, width `Kt`). -/
theorem chainA_spec' (n s w t Kt Kd : Nat) (hs : s = w + 1) (hw : 1 ≤ w) (h : n < 2 ^ s * 2 ^ t)
    (hKt : 1 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKd : 1 ≤ Kd) (hb : Nat.fib (2 ^ w) + 2 ≤ 2 ^ Kd) :
    chainA n s w (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Kd) (2 ^ (2 * Kd) - 2 ^ Kd - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have hd : n / 2 % 2 ^ w < 2 ^ w := Nat.mod_lt _ (Nat.two_pow_pos w)
  unfold chainA
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab_spec Kt _ hKt (fib_tab_bound hm hbt)]
  try dsimp only
  rw [dbl1_spec, show Nat.sub w 1 = w - 1 from rfl, lucas_spec (w - 1) _ _ (by omega)]
  try dsimp only
  rw [unL_spec, show Nat.mod (Nat.div n 2) (Nat.pow 2 w) = n / 2 % 2 ^ w from rfl,
    tab_spec Kd _ hKd (fib_tab_bound hd hb)]
  try dsimp only
  rw [comb_spec]
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

/-- `chainC` with any top table (`t` bits, width `Kt`). -/
theorem chainC_spec' (n s t Kt Ke : Nat) (hs : 1 ≤ s) (h : n < 2 ^ s * 2 ^ t)
    (hKt : 1 ≤ Kt) (hbt : Nat.fib (2 ^ t) + 2 ≤ 2 ^ Kt)
    (hKe : 1 ≤ Ke) (hb : Nat.fib (2 ^ s) + 2 ≤ 2 ^ Ke) :
    chainC n s (2 ^ Kt) (2 ^ (2 * Kt) - 2 ^ Kt - 1) (2 ^ Ke) (2 ^ (2 * Ke) - 2 ^ Ke - 1)
      = Nat.fib n := by
  have hm : n / 2 ^ s < 2 ^ t := Nat.div_lt_of_lt_mul h
  have he : n % 2 ^ s < 2 ^ s := Nat.mod_lt _ (Nat.two_pow_pos s)
  unfold chainC
  rw [show Nat.div n (Nat.pow 2 s) = n / 2 ^ s from rfl, tab_spec Kt _ hKt (fib_tab_bound hm hbt)]
  try dsimp only
  rw [dbl1_spec, show Nat.sub s 1 = s - 1 from rfl, lucas_spec (s - 1) _ _ (by omega)]
  try dsimp only
  rw [show Nat.mod n (Nat.pow 2 s) = n % 2 ^ s from rfl, tab_spec Ke _ hKe (fib_tab_bound he hb)]
  try dsimp only
  show (Nat.fib (2 * (n / 2 ^ s) * 2 ^ (s - 1)) * (Nat.fib (n % 2 ^ s + 1) + Nat.fib (n % 2 ^ s + 1)
      - Nat.fib (n % 2 ^ s)) + luc (2 * (n / 2 ^ s) * 2 ^ (s - 1)) * Nat.fib (n % 2 ^ s)) / 2 = _
  rw [luc_add]
  congr 1
  have e1 : 2 * (n / 2 ^ s) * 2 ^ (s - 1) = n / 2 ^ s * 2 ^ s := by
    rw [show 2 * (n / 2 ^ s) * 2 ^ (s - 1) = n / 2 ^ s * (2 * 2 ^ (s - 1)) by ring, ← pow_succ',
      Nat.sub_add_cancel hs]
  rw [e1, Nat.div_add_mod']
