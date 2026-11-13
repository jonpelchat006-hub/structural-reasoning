import Spec

/-!
# Matrix permanent by a packed backward subset DP

`g_i(mask)` = the spec's `permanentRows d (rows i..) mask` = number of ways to finish the
matching from row `i` when the columns in `mask` are used. Then
`g_i(mask) = Σ_{j ∈ support(row i), bit j ∉ mask} g_{i+1}(mask + 2^j)` and `g_d ≡ 1`.

All `2^d` values of `g_i` are packed into ONE natural number, one `W`-bit slot per mask
(`W = 2d + 1`; every value is at most `3^d < 2^W`). One DP row is then only kernel
big-number operations: for each of the ≤ 3 support columns `j`, shift right by `2^j`
slots (slot `mask` now holds `g(mask + 2^j)`) and `&&&` with the pattern of slots whose
index has bit `j` clear; add the three results. The kernel performs `3d` shift/and/add
steps plus `d²` cheap pattern-building steps instead of a depth-first search.

Proof outline:
* `enc g L = Σ_{m<L} g m · 2^(W·m)`; `enc_shiftRight`, `enc_and`, `enc_add` act slot by slot.
* `patD_eq`: the doubling construction encodes "bit `j` of the slot index is clear".
* `term_eq`: shift + and encodes `if bit j of m then 0 else g(2^j + m)`, and
  `2^j + m = m ||| 1 <<< j` when bit `j` of `m` is clear (`add_eq_or`).
* `spec_step`/`range_sum_supp`: the spec's fold over all columns equals the sum over the
  row's support (the diagonal and two distinct seeded columns, or all columns if `d < 3`).
* `loop_eq`: induction over rows, with the slot bound `g ≤ 3^k`.
-/

namespace Submission

/-! ## Implementation -/

/-- Pattern over `2^k` slots of width `W`: all-ones slots whose index has bit `j` clear. -/
def patD (W j : Nat) : Nat → Nat
  | 0 => 2 ^ W - 1
  | k + 1 => if k = j then patD W j k else patD W j k + (patD W j k <<< (W * 2 ^ k))

/-- Columns holding a one in row `i`. -/
def supp (d seed i : Nat) : List Nat :=
  if d < 3 then List.range d
  else [i, permanentColumnOne d seed i, permanentColumnTwo d seed i]

/-- One backward DP row. -/
def rowStep (W : Nat) (pats cols : List Nat) (G : Nat) : Nat :=
  cols.foldl (fun acc j => acc + ((G >>> (W * 2 ^ j)) &&& pats.getD j 0)) 0

/-- All-ones slots count: `Σ_{m < 2^d} B^m` in closed form. -/
def ones (W d : Nat) : Nat := ((2 ^ W) ^ (2 ^ d) - 1) / (2 ^ W - 1)

def loop (W d seed : Nat) (pats : List Nat) (k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) (ones W d)
    (fun k G => rowStep W pats (supp d seed (d - 1 - k)) G) k

def impl (n : Nat) : Nat :=
  let d := permanentDimension n
  let W := 2 * d + 1
  loop W d (permanentSeed n) ((List.range d).map (fun j => patD W j d)) d % 2 ^ W

/-! ## Generic list-sum facts -/

theorem foldl_add (T : Nat → Nat) : ∀ (l : List Nat) (a : Nat),
    l.foldl (fun acc j => acc + T j) a = a + (l.map T).sum
  | [], a => by simp
  | j :: l, a => by
    simp only [List.foldl_cons, List.map_cons, List.sum_cons]
    rw [foldl_add T l (a + T j)]
    omega

theorem foldl_ite (c : Nat → Bool) (v : Nat → Nat) : ∀ (l : List Nat) (a : Nat),
    l.foldl (fun t j => if c j = true then t else t + v j) a
      = a + (l.map (fun j => if c j = true then 0 else v j)).sum
  | [], a => by simp
  | j :: l, a => by
    simp only [List.foldl_cons, List.map_cons, List.sum_cons]
    by_cases h : c j = true
    · rw [if_pos h, if_pos h, foldl_ite c v l a]; omega
    · rw [if_neg h, if_neg h, foldl_ite c v l (a + v j)]; omega

theorem sum_map_add (f g : Nat → Nat) : ∀ l : List Nat,
    (l.map (fun j => f j + g j)).sum = (l.map f).sum + (l.map g).sum
  | [] => rfl
  | j :: l => by simp only [List.map_cons, List.sum_cons]; rw [sum_map_add f g l]; omega

theorem sum_map_congr {f g : Nat → Nat} : ∀ l : List Nat, (∀ j, j ∈ l → f j = g j) →
    (l.map f).sum = (l.map g).sum
  | [], _ => rfl
  | j :: l, h => by
    simp only [List.map_cons, List.sum_cons]
    rw [h j (by simp), sum_map_congr l (fun x hx => h x (by simp [hx]))]

theorem sum_map_le (f : Nat → Nat) (b : Nat) : ∀ l : List Nat, (∀ j, j ∈ l → f j ≤ b) →
    (l.map f).sum ≤ l.length * b
  | [], _ => by simp
  | j :: l, h => by
    simp only [List.map_cons, List.sum_cons, List.length_cons, Nat.succ_mul]
    have h1 := h j (by simp)
    have h2 := sum_map_le f b l (fun x hx => h x (by simp [hx]))
    omega

theorem sum_range_zero (F : Nat → Nat) : ∀ d, (∀ j, j < d → F j = 0) →
    ((List.range d).map F).sum = 0
  | 0, _ => rfl
  | d + 1, h => by
    rw [List.range_succ, List.map_append, List.sum_append, sum_range_zero F d
      (fun j hj => h j (by omega))]
    simp [h d (by omega)]

theorem sum_range_ite_eq (F : Nat → Nat) (a : Nat) : ∀ d, a < d →
    ((List.range d).map (fun j => if j = a then F j else 0)).sum = F a
  | 0, h => absurd h (Nat.not_lt_zero _)
  | d + 1, h => by
    rw [List.range_succ, List.map_append, List.sum_append]
    by_cases had : a = d
    · subst had
      rw [sum_range_zero _ a (fun j hj => by simp; omega)]
      simp
    · rw [sum_range_ite_eq F a d (by omega)]
      simp [Ne.symm had]

/-! ## Bits -/

theorem add_eq_or (m j : Nat) (h : m.testBit j = false) : 2 ^ j + m = m ||| 1 <<< j := by
  have hbit : m / 2 ^ j % 2 = 0 := by
    rw [Nat.testBit_eq_decide_div_mod_eq] at h
    have : m / 2 ^ j % 2 < 2 := Nat.mod_lt _ (by omega)
    simp at h
    omega
  have hr : m % 2 ^ (j + 1) < 2 ^ j := by
    rw [Nat.mod_pow_succ, hbit, Nat.mul_zero, Nat.add_zero]
    exact Nat.mod_lt _ (Nat.two_pow_pos j)
  have hm := (Nat.div_add_mod m (2 ^ (j + 1))).symm
  have e2 : 2 ^ (j + 1) = 2 ^ j * 2 := Nat.pow_succ 2 j
  generalize m / 2 ^ (j + 1) = q at hm
  generalize m % 2 ^ (j + 1) = r at hm hr
  have hm' : m = 2 ^ j * (2 * q) ||| r := by
    rw [← Nat.two_pow_add_eq_or_of_lt hr, hm, e2, Nat.mul_assoc]
  have h1 : 2 * q ||| 1 = 2 * q + 1 := by
    have := Nat.two_pow_add_eq_or_of_lt (i := 1) (b := 1) (by decide) q
    simpa using this.symm
  have hl : 2 ^ j + m = 2 ^ j * (2 * q ||| 1) ||| r := by
    rw [← Nat.two_pow_add_eq_or_of_lt hr, h1, hm, e2, Nat.mul_add, Nat.mul_one, Nat.mul_assoc]
    omega
  rw [hl, hm', Nat.one_shiftLeft]
  have h3 : 2 ^ j * (2 * q ||| 1) = 2 ^ j * (2 * q) ||| 2 ^ j := by
    rw [Nat.mul_comm, ← Nat.shiftLeft_eq, Nat.shiftLeft_or_distrib, Nat.shiftLeft_eq,
      Nat.shiftLeft_eq, Nat.one_mul, Nat.mul_comm]
  rw [h3, Nat.or_assoc, Nat.or_comm (2 ^ j) r, ← Nat.or_assoc]

theorem or_and_or (a b x y k : Nat) (hx : x < 2 ^ k) (hy : y < 2 ^ k) :
    (a <<< k ||| x) &&& (b <<< k ||| y) = (a &&& b) <<< k ||| (x &&& y) := by
  apply Nat.eq_of_testBit_eq
  intro i
  simp only [Nat.testBit_and, Nat.testBit_or, Nat.testBit_shiftLeft]
  by_cases h : k ≤ i
  · have hle : 2 ^ k ≤ 2 ^ i := Nat.pow_le_pow_right (by omega) h
    have hx' : x.testBit i = false := Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hx hle)
    have hy' : y.testBit i = false := Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hy hle)
    simp [hx', hy', h]
  · simp [show ¬ i ≥ k by omega]

/-! ## Encodings with `W`-bit slots -/

section Enc

variable (W : Nat)

def enc (g : Nat → Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => enc g L + g L * 2 ^ (W * L)

theorem enc_congr {f g : Nat → Nat} : ∀ L, (∀ m, m < L → f m = g m) → enc W f L = enc W g L
  | 0, _ => rfl
  | L + 1, h => by
    simp only [enc]
    rw [enc_congr L (fun m hm => h m (by omega)), h L (by omega)]

theorem enc_zero {f : Nat → Nat} : ∀ L, (∀ m, m < L → f m = 0) → enc W f L = 0
  | 0, _ => rfl
  | L + 1, h => by
    simp only [enc]
    rw [enc_zero L (fun m hm => h m (by omega)), h L (by omega)]
    simp

theorem enc_add (f g : Nat → Nat) : ∀ L, enc W (fun m => f m + g m) L = enc W f L + enc W g L
  | 0 => rfl
  | L + 1 => by
    simp only [enc]
    rw [enc_add f g L, Nat.add_mul]
    omega

theorem enc_lt (g : Nat → Nat) : ∀ L, (∀ m, m < L → g m < 2 ^ W) → enc W g L < 2 ^ (W * L)
  | 0, _ => by simp [enc]
  | L + 1, h => by
    simp only [enc]
    have h1 := enc_lt g L (fun m hm => h m (by omega))
    have h2 : g L + 1 ≤ 2 ^ W := h L (by omega)
    have h3 : (g L + 1) * 2 ^ (W * L) ≤ 2 ^ W * 2 ^ (W * L) := Nat.mul_le_mul_right _ h2
    rw [Nat.add_mul, Nat.one_mul] at h3
    have e : 2 ^ (W * (L + 1)) = 2 ^ W * 2 ^ (W * L) := by
      rw [Nat.mul_succ, Nat.pow_add, Nat.mul_comm]
    rw [e]
    omega

theorem enc_split (g : Nat → Nat) (s : Nat) : ∀ L,
    enc W g (s + L) = enc W g s + 2 ^ (W * s) * enc W (fun m => g (s + m)) L
  | 0 => by simp [enc]
  | L + 1 => by
    rw [show s + (L + 1) = (s + L) + 1 by omega]
    simp only [enc]
    rw [enc_split g s L, Nat.mul_add, Nat.mul_add, Nat.pow_add]
    have : g (s + L) * (2 ^ (W * s) * 2 ^ (W * L)) = 2 ^ (W * s) * (g (s + L) * 2 ^ (W * L)) := by
      rw [Nat.mul_left_comm]
    rw [this]
    omega

theorem enc_shiftRight (g : Nat → Nat) (s L : Nat) (hs : s ≤ L) (hb : ∀ m, m < L → g m < 2 ^ W) :
    enc W g L >>> (W * s) = enc W (fun m => g (s + m)) (L - s) := by
  obtain ⟨t, rfl⟩ : ∃ t, L = s + t := ⟨L - s, by omega⟩
  rw [Nat.add_sub_cancel_left, enc_split, Nat.shiftRight_eq_div_pow, Nat.mul_comm (2 ^ (W * s)),
    Nat.add_mul_div_right _ _ (Nat.two_pow_pos _),
    Nat.div_eq_of_lt (enc_lt W g s (fun m hm => hb m (by omega))), Nat.zero_add]

theorem enc_pad (f : Nat → Nat) (L' L : Nat) (h : L' ≤ L) :
    enc W f L' = enc W (fun m => if m < L' then f m else 0) L := by
  obtain ⟨t, rfl⟩ : ∃ t, L = L' + t := ⟨L - L', by omega⟩
  rw [enc_split, enc_zero W t (fun m _ => if_neg (by omega)), Nat.mul_zero, Nat.add_zero]
  exact enc_congr W L' (fun m hm => by simp [hm])

theorem enc_succ_or (g : Nat → Nat) (L : Nat) (hb : ∀ m, m < L → g m < 2 ^ W) :
    enc W g (L + 1) = g L <<< (W * L) ||| enc W g L := by
  simp only [enc]
  rw [Nat.add_comm, ← Nat.shiftLeft_eq, Nat.shiftLeft_add_eq_or_of_lt (enc_lt W g L hb)]

theorem enc_and (a b : Nat → Nat) : ∀ L, (∀ m, m < L → a m < 2 ^ W) → (∀ m, m < L → b m < 2 ^ W) →
    enc W a L &&& enc W b L = enc W (fun m => a m &&& b m) L
  | 0, _, _ => by simp [enc]
  | L + 1, ha, hb => by
    have ha' : ∀ m, m < L → a m < 2 ^ W := fun m hm => ha m (by omega)
    have hb' : ∀ m, m < L → b m < 2 ^ W := fun m hm => hb m (by omega)
    have hab : ∀ m, m < L → a m &&& b m < 2 ^ W := fun m hm =>
      Nat.lt_of_le_of_lt Nat.and_le_left (ha' m hm)
    rw [enc_succ_or W a L ha', enc_succ_or W b L hb', enc_succ_or W _ L hab,
      or_and_or _ _ _ _ _ (enc_lt W a L ha') (enc_lt W b L hb'), enc_and a b L ha' hb']

theorem enc_mod (g : Nat → Nat) (L : Nat) (h : g 0 < 2 ^ W) :
    enc W g (1 + L) % 2 ^ W = g 0 := by
  rw [enc_split]
  simp only [enc, Nat.mul_zero, Nat.pow_zero, Nat.mul_one, Nat.zero_add, Nat.mul_one]
  rw [Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt h]

theorem enc_listSum (F : Nat → Nat → Nat) (L : Nat) : ∀ cols : List Nat,
    (cols.map (fun j => enc W (F j) L)).sum = enc W (fun m => (cols.map (fun j => F j m)).sum) L
  | [] => by
    simp only [List.map_nil, List.sum_nil]
    exact (enc_zero W L (fun _ _ => rfl)).symm
  | j :: cols => by
    simp only [List.map_cons, List.sum_cons]
    rw [enc_listSum F L cols, ← enc_add]

end Enc

/-! ## Patterns and the all-ones start -/

/-- Slot value of the bit-`j`-clear pattern. -/
def pj (W j m : Nat) : Nat := if m.testBit j then 0 else 2 ^ W - 1

theorem patD_eq (W j : Nat) : ∀ k, patD W j k = enc W (pj W j) (2 ^ k)
  | 0 => by simp [patD, enc, pj, Nat.zero_testBit]
  | k + 1 => by
    have e : 2 ^ (k + 1) = 2 ^ k + 2 ^ k := by rw [Nat.pow_succ, Nat.mul_two]
    rw [e, enc_split]
    simp only [patD]
    by_cases hkj : k = j
    · rw [if_pos hkj, ← patD_eq W j k, enc_zero W (2 ^ k) (fun m hm => by
        simp only [pj]
        rw [if_pos]
        rw [← hkj, Nat.testBit_two_pow_add_eq, Nat.testBit_lt_two_pow hm]
        rfl)]
      simp
    · rw [if_neg hkj, ← patD_eq W j k, Nat.shiftLeft_eq, Nat.mul_comm (patD W j k)]
      congr 2
      rw [patD_eq W j k]
      apply enc_congr
      intro m hm
      simp only [pj]
      rcases Nat.lt_or_gt_of_ne hkj with hlt | hgt
      · have h1 : (2 ^ k + m).testBit j = false := by
          apply Nat.testBit_lt_two_pow
          have : 2 ^ k + m < 2 ^ (k + 1) := by rw [Nat.pow_succ]; omega
          exact Nat.lt_of_lt_of_le this (Nat.pow_le_pow_right (by omega) (by omega))
        have h2 : m.testBit j = false := by
          apply Nat.testBit_lt_two_pow
          exact Nat.lt_of_lt_of_le hm (Nat.pow_le_pow_right (by omega) (by omega))
        rw [h1, h2]
      · rw [Nat.testBit_two_pow_add_gt hgt]

theorem geo_mul (q : Nat) (hq : 1 ≤ q) : ∀ L, (q - 1) * enc 0 (fun m => q ^ m) L + 1 = q ^ L
  | 0 => by simp [enc]
  | L + 1 => by
    simp only [enc, Nat.zero_mul, Nat.pow_zero, Nat.mul_one]
    have ih := geo_mul q hq L
    rw [Nat.mul_add, Nat.pow_succ]
    have : (q - 1) * q ^ L + q ^ L = q ^ L * q := by
      obtain ⟨r, rfl⟩ : ∃ r, q = r + 1 := ⟨q - 1, by omega⟩
      rw [Nat.add_sub_cancel, Nat.mul_succ, Nat.mul_comm (n := r)]
    omega

theorem ones_eq (W d : Nat) (hW : 1 ≤ W) : ones W d = enc W (fun _ => 1) (2 ^ d) := by
  have hB : 2 ≤ 2 ^ W := by
    calc 2 = 2 ^ 1 := rfl
      _ ≤ 2 ^ W := Nat.pow_le_pow_right (by omega) hW
  have e : enc W (fun _ => 1) (2 ^ d) = enc 0 (fun m => (2 ^ W) ^ m) (2 ^ d) := by
    have : ∀ L, enc W (fun _ => 1) L = enc 0 (fun m => (2 ^ W) ^ m) L := by
      intro L
      induction L with
      | zero => rfl
      | succ L ih => simp only [enc]; rw [ih, ← Nat.pow_mul]; simp
    exact this _
  rw [e]
  unfold ones
  rw [← geo_mul (2 ^ W) (by omega) (2 ^ d), Nat.add_sub_cancel, Nat.mul_div_cancel_left _ (by omega)]

/-! ## The seeded support -/

theorem skipOne_ne (e k : Nat) : permanentSkipOne e k ≠ e := by
  unfold permanentSkipOne; split <;> omega

theorem skipTwo_ne (a b k : Nat) (_hab : a ≠ b) :
    permanentSkipTwo a b k ≠ a ∧ permanentSkipTwo a b k ≠ b := by
  unfold permanentSkipTwo
  simp only [Nat.min_def, Nat.max_def]
  split <;> split <;> split <;> omega

theorem col1_facts (d seed i : Nat) (hd : 3 ≤ d) (hi : i < d) :
    permanentColumnOne d seed i < d ∧ permanentColumnOne d seed i ≠ i := by
  unfold permanentColumnOne
  refine ⟨?_, skipOne_ne _ _⟩
  have := Nat.mod_lt (permanentMix32 (seed ^^^ (i * 0x9e3779b9) ^^^ 0x85ebca6b)) (show d - 1 > 0 by omega)
  unfold permanentSkipOne; split <;> omega

theorem col2_facts (d seed i : Nat) (hd : 3 ≤ d) (hi : i < d) :
    permanentColumnTwo d seed i < d ∧ permanentColumnTwo d seed i ≠ i ∧
      permanentColumnTwo d seed i ≠ permanentColumnOne d seed i := by
  have h1 := col1_facts d seed i hd hi
  unfold permanentColumnTwo
  simp only
  have hne := skipTwo_ne i (permanentColumnOne d seed i)
    (permanentMix32 (seed ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35) % (d - 2)) (Ne.symm h1.2)
  refine ⟨?_, hne.1, hne.2⟩
  have := Nat.mod_lt (permanentMix32 (seed ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35)) (show d - 2 > 0 by omega)
  unfold permanentSkipTwo
  simp only [Nat.min_def, Nat.max_def]
  split <;> split <;> split <;> omega

theorem supp_lt (d seed i : Nat) (hi : i < d) : ∀ j, j ∈ supp d seed i → j < d := by
  intro j hj
  unfold supp at hj
  split at hj
  · exact List.mem_range.mp hj
  · simp only [List.mem_cons, List.not_mem_nil, or_false] at hj
    rcases hj with rfl | rfl | rfl
    · exact hi
    · exact (col1_facts d seed i (by omega) hi).1
    · exact (col2_facts d seed i (by omega) hi).1

theorem supp_length (d seed i : Nat) : (supp d seed i).length ≤ 3 := by
  unfold supp; split
  · simp; omega
  · simp

theorem entry_01 (d seed i j : Nat) :
    permanentEntry d seed i j = 0 ∨ permanentEntry d seed i j = 1 := by
  unfold permanentEntry; split
  · exact Or.inr rfl
  · split
    · exact Or.inr rfl
    · exact Or.inl rfl

/-- The spec's fold over all columns equals the sum over the support. -/
theorem range_sum_supp (d seed i : Nat) (hi : i < d) (F : Nat → Nat) :
    ((List.range d).map (fun j => if permanentEntry d seed i j = 0 then 0 else F j)).sum
      = ((supp d seed i).map F).sum := by
  unfold supp
  by_cases hd : d < 3
  · rw [if_pos hd]
    apply sum_map_congr
    intro j _
    simp [permanentEntry, hd]
  · rw [if_neg hd]
    have c1 := col1_facts d seed i (by omega) hi
    have c2 := col2_facts d seed i (by omega) hi
    generalize ha : permanentColumnOne d seed i = a at c1 c2
    generalize hb : permanentColumnTwo d seed i = b at c2
    have pw : ∀ j, (if permanentEntry d seed i j = 0 then 0 else F j) =
        (if j = i then F j else 0) + ((if j = a then F j else 0) + (if j = b then F j else 0)) := by
      intro j
      unfold permanentEntry
      rw [if_neg hd, ha, hb]
      by_cases h1 : j = i
      · subst h1; simp [c1.2.symm, c2.2.1.symm]
      · by_cases h2 : j = a
        · subst h2; simp [c1.2, c2.2.2.symm]
        · by_cases h3 : j = b
          · subst h3; simp [c2.2.1, c2.2.2]
          · simp [h1, h2, h3, Ne.symm h1]
    rw [sum_map_congr _ (fun j _ => pw j), sum_map_add, sum_map_add,
      sum_range_ite_eq F i d hi, sum_range_ite_eq F a d c1.1, sum_range_ite_eq F b d c2.1]
    simp

/-! ## The spec, row by row -/

def M (d seed : Nat) : List (List Nat) := genPermanentMatrix d seed

theorem M_length (d seed : Nat) : (M d seed).length = d := by
  simp [M, genPermanentMatrix]

/-- Slot function: ways to finish from row `i` with used-column mask `m`. -/
def gs (d seed i m : Nat) : Nat := permanentRows d ((M d seed).drop i) m

theorem gs_top (d seed m : Nat) : gs d seed d m = 1 := by
  unfold gs
  rw [List.drop_eq_nil_of_le (by rw [M_length]; exact Nat.le_refl d)]
  rfl

theorem gs_step (d seed i m : Nat) (hi : i < d) :
    gs d seed i m = ((supp d seed i).map
      (fun j => if m.testBit j then 0 else gs d seed (i + 1) (2 ^ j + m))).sum := by
  unfold gs
  have hlen : i < (M d seed).length := by rw [M_length]; exact hi
  rw [List.drop_eq_getElem_cons hlen]
  simp only [permanentRows]
  rw [foldl_ite, Nat.zero_add, ← range_sum_supp d seed i hi]
  apply sum_map_congr
  intro j hj
  have hj' : j < d := List.mem_range.mp hj
  have hrow : ((M d seed)[i]'hlen).getD j 0 = permanentEntry d seed i j := by
    simp [M, genPermanentMatrix, genPermanentRow, List.getD_eq_getElem?_getD, hj']
  rw [hrow]
  rcases entry_01 d seed i j with he | he
  · simp [he]
  · rw [he]
    by_cases hb : m.testBit j
    · simp [hb]
    · simp only [hb, Bool.or_false, Nat.one_mul]
      simp only [Bool.not_eq_true] at hb
      rw [add_eq_or m j hb]
      simp

/-! ## Main invariant -/

theorem gs_bound (d seed : Nat) : ∀ k, k ≤ d → ∀ m, gs d seed (d - k) m ≤ 3 ^ k
  | 0, _, m => by rw [Nat.sub_zero, gs_top]; simp
  | k + 1, hk, m => by
    have hi : d - (k + 1) < d := by omega
    rw [gs_step d seed _ m hi]
    have e : d - (k + 1) + 1 = d - k := by omega
    have := sum_map_le (fun j => if m.testBit j = true then 0 else gs d seed (d - (k + 1) + 1) (2 ^ j + m))
      (3 ^ k) (supp d seed (d - (k + 1))) (fun j _ => by
      split
      · exact Nat.zero_le _
      · rw [e]; exact gs_bound d seed k (by omega) _)
    have hl := supp_length d seed (d - (k + 1))
    have := Nat.mul_le_mul_right (3 ^ k) hl
    rw [Nat.pow_succ]
    omega

theorem three_pow_lt (d k : Nat) (hk : k ≤ d) : 3 ^ k < 2 ^ (2 * d + 1) := by
  have h1 : 3 ^ k ≤ 4 ^ d :=
    Nat.le_trans (Nat.pow_le_pow_right (by omega) hk) (Nat.pow_le_pow_left (by omega) d)
  have h2 : 4 ^ d = 2 ^ (2 * d) := by rw [Nat.pow_mul]
  have h3 : 2 ^ (2 * d) < 2 ^ (2 * d + 1) := Nat.pow_lt_pow_right (by omega) (by omega)
  omega

theorem term_eq (W d j : Nat) (g : Nat → Nat) (hj : j < d) (hb : ∀ m, m < 2 ^ d → g m < 2 ^ W) :
    (enc W g (2 ^ d) >>> (W * 2 ^ j)) &&& patD W j d
      = enc W (fun m => if m.testBit j then 0 else g (2 ^ j + m)) (2 ^ d) := by
  have hjd : 2 ^ j ≤ 2 ^ d := Nat.pow_le_pow_right (by omega) (by omega)
  have hj0 := Nat.two_pow_pos j
  have hW : 2 ^ W - 1 < 2 ^ W := by have := Nat.two_pow_pos W; omega
  rw [enc_shiftRight W g _ _ hjd hb, enc_pad W _ _ (2 ^ d) (by omega), patD_eq,
    enc_and W _ _ _ (fun m _ => by
      split
      · exact hb _ (by omega)
      · exact Nat.two_pow_pos W)
      (fun m _ => by unfold pj; split <;> omega)]
  apply enc_congr
  intro m hm
  unfold pj
  by_cases hbit : m.testBit j
  · simp [hbit]
  · simp only [hbit, if_false, Bool.false_eq_true]
    have hor := add_eq_or m j (by simpa using hbit)
    have hlt : 2 ^ j + m < 2 ^ d := by
      rw [hor, Nat.one_shiftLeft]
      exact Nat.or_lt_two_pow hm (Nat.pow_lt_pow_right (by omega) hj)
    rw [if_pos (by omega), Nat.and_two_pow_sub_one_of_lt_two_pow (hb _ hlt)]

theorem loop_eq (d seed : Nat) (hW : 1 ≤ 2 * d + 1) : ∀ k, k ≤ d →
    loop (2 * d + 1) d seed ((List.range d).map (fun j => patD (2 * d + 1) j d)) k
      = enc (2 * d + 1) (gs d seed (d - k)) (2 ^ d)
  | 0, _ => by
    rw [Nat.sub_zero]
    show ones _ d = _
    rw [ones_eq _ d hW]
    exact enc_congr _ _ (fun m _ => (gs_top d seed m).symm)
  | k + 1, hk => by
    show rowStep _ _ (supp d seed (d - 1 - k)) (loop _ d seed _ k) = _
    rw [loop_eq d seed hW k (by omega)]
    unfold rowStep
    rw [foldl_add, Nat.zero_add]
    have hi : d - 1 - k < d := by omega
    have e1 : d - (k + 1) = d - 1 - k := by omega
    have e2 : d - 1 - k + 1 = d - k := by omega
    have hb : ∀ m, m < 2 ^ d → gs d seed (d - k) m < 2 ^ (2 * d + 1) := fun m _ =>
      Nat.lt_of_le_of_lt (gs_bound d seed k (by omega) m) (three_pow_lt d k (by omega))
    rw [sum_map_congr (g := fun j => enc (2 * d + 1)
        (fun m => if m.testBit j then 0 else gs d seed (d - k) (2 ^ j + m)) (2 ^ d)) _ (by
      intro j hj
      have hjd := supp_lt d seed _ hi j hj
      have hp : ((List.range d).map (fun j => patD (2 * d + 1) j d)).getD j 0 = patD (2 * d + 1) j d := by
        simp [List.getD_eq_getElem?_getD, hjd]
      rw [hp, term_eq _ d j _ hjd hb])]
    rw [enc_listSum, e1]
    apply enc_congr
    intro m _
    rw [gs_step d seed _ m hi, e2]

/-! ## Main correctness -/

theorem impl_correct : ∀ n, impl n = permanentSpecN n := by
  intro n
  unfold impl permanentSpecN
  simp only
  generalize permanentDimension n = d
  generalize permanentSeed n = seed
  rw [loop_eq d seed (by omega) d (Nat.le_refl d), Nat.sub_self]
  have e : 2 ^ d = 1 + (2 ^ d - 1) := by have := Nat.two_pow_pos d; omega
  rw [e, enc_mod _ _ _ (by
    have := gs_bound d seed d (Nat.le_refl d) 0
    rw [Nat.sub_self] at this
    exact Nat.lt_of_le_of_lt this (three_pow_lt d d (Nat.le_refl d)))]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows d (M d seed) 0 = permanentRows (M d seed).length (M d seed) 0
  rw [M_length]

end Submission
