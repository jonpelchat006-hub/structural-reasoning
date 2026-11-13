import Spec
import Lean

/-!
# Matrix permanent by a packed backward subset DP without masks

`gs i m` = the spec's `permanentRows d (rows i..) m` (ways to finish from row `i` with the
columns of `m` used). The kernel keeps one `W`-bit lane per mask `m < 2^d` and runs, for
rows `d-1, …, 0`, `H ↦ Σ_{j ∈ support(row)} H >>> (W·2^j)` (lane `m` receives lane
`m + 2^j`). No "bit `j` clear" masks are applied: when bit `j` of `m` is set, `m + 2^j`
carries and has popcount `≤ popcount m`. Starting from the single top lane `2^d - 1`,
the lane function `hl k` after `k` rows equals `[pc m = d-k] · gs (d-k) m` on every mask
with `pc m ≤ d - k` (`hl_correct`), which includes the answer lane `0`. Lanes never
overflow because every value is at most `3^k < 2^W` (`hl_bound`, `three_lt_width_aux`).
The seeded columns are computed with the spec's own mixer written in raw kernel ops.
-/

namespace Submission

/-! ## Implementation -/

open Lean Elab Term Meta in
/-- Substitute shared Nat expressions during elaboration, avoiding kernel let reductions. -/
elab "share " x:ident " := " v:term "; " b:term : term => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b (some (mkConst ``Nat)))
    return b.replaceFVar fv v



def mix (x : Nat) : Nat :=
  share x := Nat.land (Nat.mul (Nat.xor x (Nat.shiftRight x (nat_lit 16))) (nat_lit 0x7feb352d))
    (nat_lit 0xffffffff);
  share x := Nat.land (Nat.mul (Nat.xor x (Nat.shiftRight x (nat_lit 15))) (nat_lit 0x846ca68b))
    (nat_lit 0xffffffff);
  Nat.xor x (Nat.shiftRight x (nat_lit 16))

def skip1 (e k : Nat) : Nat := Nat.add k (Nat.sub (nat_lit 1) (Nat.sub e k))

def col1 (d x i : Nat) : Nat :=
  skip1 i (Nat.mod (mix (Nat.xor x (nat_lit 0x85ebca6b))) (Nat.sub d (nat_lit 1)))

def col2 (d x i a : Nat) : Nat :=
  skip1 (Nat.add a (Nat.sub i a)) (skip1 (Nat.sub i (Nat.sub i a))
    (Nat.mod (mix (Nat.xor x (nat_lit 0xc2b2ae35))) (Nat.sub d (nat_lit 2))))

def sh (W G j : Nat) : Nat := Nat.shiftRight G (Nat.shiftLeft W j)

def row3 (W G i a b : Nat) : Nat := Nat.add (Nat.add (sh W G i) (sh W G a)) (sh W G b)

def row (d s W i G : Nat) : Nat :=
  share x := Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9));
  share a0 := Nat.xor x (nat_lit 0x85ebca6b);
  share a1 := Nat.land (Nat.mul (Nat.xor a0 (Nat.shiftRight a0 (nat_lit 16))) (nat_lit 0x7feb352d)) (nat_lit 0xffffffff);
  share a2 := Nat.land (Nat.mul (Nat.xor a1 (Nat.shiftRight a1 (nat_lit 15))) (nat_lit 0x846ca68b)) (nat_lit 0xffffffff);
  share a3 := Nat.xor a2 (Nat.shiftRight a2 (nat_lit 16));
  share b0 := Nat.xor x (nat_lit 0xc2b2ae35);
  share b1 := Nat.land (Nat.mul (Nat.xor b0 (Nat.shiftRight b0 (nat_lit 16))) (nat_lit 0x7feb352d)) (nat_lit 0xffffffff);
  share b2 := Nat.land (Nat.mul (Nat.xor b1 (Nat.shiftRight b1 (nat_lit 15))) (nat_lit 0x846ca68b)) (nat_lit 0xffffffff);
  share b3 := Nat.xor b2 (Nat.shiftRight b2 (nat_lit 16));
  share ak := Nat.mod a3 (Nat.sub d (nat_lit 1));
  share a := Nat.add ak (Nat.sub (nat_lit 1) (Nat.sub i ak));
  share bk := Nat.mod b3 (Nat.sub d (nat_lit 2));
  share delta := Nat.sub i a;
  share lo := Nat.sub i delta;
  share hi := Nat.add a delta;
  share bk1 := Nat.add bk (Nat.sub (nat_lit 1) (Nat.sub lo bk));
  share b := Nat.add bk1 (Nat.sub (nat_lit 1) (Nat.sub hi bk1));
  Nat.add (Nat.add (Nat.shiftRight G (Nat.shiftLeft W i))
    (Nat.shiftRight G (Nat.shiftLeft W a))) (Nat.shiftRight G (Nat.shiftLeft W b))

def loop (d s W : Nat) (k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (Nat.shiftLeft (nat_lit 1) (Nat.mul W (Nat.sub (Nat.shiftLeft (nat_lit 1) d) (nat_lit 1))))
    (fun k G => row d s W (Nat.sub (Nat.sub d k) (nat_lit 1)) G) k

def width (d : Nat) : Nat := Nat.div (Nat.add (Nat.mul (nat_lit 27) d) (nat_lit 17)) (nat_lit 17)

def main (d s : Nat) : Nat :=
  Nat.land (loop d s (width d) d) (Nat.sub (Nat.shiftLeft (nat_lit 1) (width d)) (nat_lit 1))

def impl (n : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (main (Nat.shiftRight n (nat_lit 32)) (Nat.land n (nat_lit 0xffffffff)))
    (fun _ _ => permanentSpecN n) (Nat.sub (nat_lit 3) (Nat.shiftRight n (nat_lit 32)))

/-- Columns holding a one in row `i`. -/
def supp (d seed i : Nat) : List Nat :=
  if d < 3 then List.range d
  else [i, permanentColumnOne d seed i, permanentColumnTwo d seed i]

/-! ## Generic list-sum facts -/

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

theorem sum_map_ite (c : Prop) [Decidable c] (f : Nat → Nat) : ∀ l : List Nat,
    (l.map (fun j => if c then f j else 0)).sum = if c then (l.map f).sum else 0
  | [] => by simp
  | j :: l => by
    simp only [List.map_cons, List.sum_cons]
    rw [sum_map_ite c f l]
    split <;> simp

/-! ## Bits and popcount -/

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

/-- Number of set bits. -/
def pc : Nat → Nat
  | 0 => 0
  | m + 1 => (m + 1) % 2 + pc ((m + 1) / 2)

theorem pc_zero : pc 0 = 0 := by simp [pc]

theorem pc_dec (q r : Nat) (hr : r < 2) : pc (2 * q + r) = r + pc q := by
  rcases Nat.eq_zero_or_pos (2 * q + r) with h | h
  · have h1 : q = 0 := by omega
    have h2 : r = 0 := by omega
    subst h1 h2
    simp [pc]
  · obtain ⟨m, hm⟩ : ∃ m, 2 * q + r = m + 1 := ⟨2 * q + r - 1, by omega⟩
    rw [hm, pc, ← hm]
    have e1 : (2 * q + r) % 2 = r := by omega
    have e2 : (2 * q + r) / 2 = q := by omega
    rw [e1, e2]

theorem pc_half (m : Nat) : pc m = m % 2 + pc (m / 2) := by
  have := pc_dec (m / 2) (m % 2) (Nat.mod_lt _ (by omega))
  rwa [show 2 * (m / 2) + m % 2 = m by omega] at this

theorem pc_le : ∀ d m, m < 2 ^ d → pc m ≤ d ∧ (pc m = d ↔ m = 2 ^ d - 1)
  | 0, m, h => by
    have : m = 0 := by simp at h; omega
    subst this
    simp [pc]
  | d + 1, m, h => by
    have e : 2 ^ (d + 1) = 2 * 2 ^ d := by rw [Nat.pow_succ]; omega
    have hq : m / 2 < 2 ^ d := by omega
    have ih := pc_le d (m / 2) hq
    have hp := pc_half m
    have hr : m % 2 < 2 := Nat.mod_lt _ (by omega)
    constructor
    · omega
    · rw [e]
      constructor
      · intro h1
        have := ih.2.mp (by omega)
        omega
      · intro h1
        have := ih.2.mpr (by omega)
        omega

theorem pc_clear : ∀ j m, m.testBit j = false → pc (2 ^ j + m) = pc m + 1
  | 0, m, h => by
    rw [Nat.testBit_zero] at h
    have h0 : m % 2 = 0 := by simp at h; omega
    have e1 := pc_half (2 ^ 0 + m)
    have e2 := pc_half m
    rw [Nat.pow_zero] at e1 ⊢
    rw [show (1 + m) / 2 = m / 2 by omega, show (1 + m) % 2 = 1 by omega] at e1
    omega
  | j + 1, m, h => by
    rw [Nat.testBit_succ] at h
    have ih := pc_clear j (m / 2) h
    have e1 := pc_half (2 ^ (j + 1) + m)
    have e2 := pc_half m
    have p : 2 ^ (j + 1) = 2 * 2 ^ j := by rw [Nat.pow_succ]; omega
    rw [p] at e1 ⊢
    rw [show (2 * 2 ^ j + m) / 2 = 2 ^ j + m / 2 by omega,
      show (2 * 2 ^ j + m) % 2 = m % 2 by omega] at e1
    omega

theorem pc_succ_le_aux : ∀ n m, m < n → pc (m + 1) ≤ pc m + 1
  | 0, _, h => absurd h (Nat.not_lt_zero _)
  | n + 1, m, h => by
    have e1 := pc_half (m + 1)
    have e2 := pc_half m
    rcases Nat.lt_or_ge (m % 2) 1 with hr | hr
    · rw [show (m + 1) / 2 = m / 2 by omega, show (m + 1) % 2 = 1 by omega] at e1
      omega
    · rw [show (m + 1) / 2 = m / 2 + 1 by omega, show (m + 1) % 2 = 0 by omega] at e1
      have := pc_succ_le_aux n (m / 2) (by omega)
      omega

theorem pc_set : ∀ j m, m.testBit j = true → pc (2 ^ j + m) ≤ pc m
  | 0, m, h => by
    rw [Nat.testBit_zero] at h
    have h0 : m % 2 = 1 := by simp at h; omega
    have e1 := pc_half (2 ^ 0 + m)
    have e2 := pc_half m
    rw [Nat.pow_zero] at e1 ⊢
    rw [show (1 + m) / 2 = m / 2 + 1 by omega, show (1 + m) % 2 = 0 by omega] at e1
    have := pc_succ_le_aux (m / 2 + 1) (m / 2) (by omega)
    omega
  | j + 1, m, h => by
    rw [Nat.testBit_succ] at h
    have ih := pc_set j (m / 2) h
    have e1 := pc_half (2 ^ (j + 1) + m)
    have e2 := pc_half m
    have p : 2 ^ (j + 1) = 2 * 2 ^ j := by rw [Nat.pow_succ]; omega
    rw [p] at e1 ⊢
    rw [show (2 * 2 ^ j + m) / 2 = 2 ^ j + m / 2 by omega,
      show (2 * 2 ^ j + m) % 2 = m % 2 by omega] at e1
    omega

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

theorem enc_mod (g : Nat → Nat) (L : Nat) (h : g 0 < 2 ^ W) :
    enc W g (1 + L) % 2 ^ W = g 0 := by
  rw [enc_split]
  simp only [enc, Nat.mul_zero, Nat.pow_zero, Nat.mul_one, Nat.zero_add, Nat.mul_one]
  rw [Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt h]

end Enc

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

/-! ## Raw columns agree with the spec -/

theorem xor32_mask (x : Nat) (hx : x < 2 ^ 32) :
    Nat.land (Nat.xor x (Nat.shiftRight x (nat_lit 16))) (nat_lit 0xffffffff)
      = Nat.xor x (Nat.shiftRight x (nat_lit 16)) := by
  exact Nat.and_two_pow_sub_one_of_lt_two_pow
    (Nat.xor_lt_two_pow hx (Nat.lt_of_le_of_lt (Nat.shiftRight_le x 16) hx))

theorem mix_eq (x : Nat) : mix x = permanentMix32 x := by
  unfold mix permanentMix32
  dsimp only
  symm
  apply xor32_mask
  exact Nat.and_lt_two_pow _ (by decide)

theorem skip1_eq (e k : Nat) : skip1 e k = permanentSkipOne e k := by
  show k + (1 - (e - k)) = _
  unfold permanentSkipOne
  split <;> omega

theorem skipTwo_eq (i a k : Nat) :
    skip1 (Nat.add a (Nat.sub i a)) (skip1 (Nat.sub i (Nat.sub i a)) k) = permanentSkipTwo i a k := by
  show (k + (1 - (i - (i - a) - k))) + (1 - (a + (i - a) - (k + (1 - (i - (i - a) - k))))) = _
  unfold permanentSkipTwo
  simp only [Nat.min_def, Nat.max_def]
  by_cases h1 : i ≤ a <;> by_cases h2 : k < i <;> by_cases h3 : k < a <;>
    by_cases h4 : k + 1 < i <;> by_cases h5 : k + 1 < a <;>
    simp only [h1, h2, h3, h4, h5, if_true, if_false] <;> omega

theorem col1_eq (d s i : Nat) :
    col1 d (Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9))) i = permanentColumnOne d s i := by
  unfold col1 permanentColumnOne
  rw [skip1_eq, mix_eq]
  rfl

theorem col2_eq (d s i : Nat) :
    col2 d (Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9))) i (permanentColumnOne d s i)
      = permanentColumnTwo d s i := by
  unfold col2 permanentColumnTwo
  rw [skipTwo_eq, mix_eq]
  rfl

theorem row_eq (d s W i G : Nat) :
    row d s W i G = row3 W G i (permanentColumnOne d s i) (permanentColumnTwo d s i) := by
  show row3 W G i (col1 d (Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9))) i)
    (col2 d (Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9))) i
      (col1 d (Nat.xor s (Nat.mul i (nat_lit 0x9e3779b9))) i)) = _
  rw [col1_eq, col2_eq]

/-! ## Lane functions -/

/-- Lane values after `k` backward rows (no masking). -/
def hl (d seed : Nat) : Nat → Nat → Nat
  | 0, m => if m = 2 ^ d - 1 then 1 else 0
  | k + 1, m => ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0)).sum

theorem hl_bound (d seed : Nat) : ∀ k m, hl d seed k m ≤ 3 ^ k
  | 0, m => by simp only [hl]; split <;> simp
  | k + 1, m => by
    simp only [hl]
    have h1 := sum_map_le (fun j => if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0)
      (3 ^ k) (supp d seed (d - 1 - k)) (fun j (_ : j ∈ supp d seed (d - 1 - k)) => by
        show (if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0) ≤ 3 ^ k
        split
        · exact hl_bound d seed k _
        · exact Nat.zero_le _)
    have h2 := Nat.mul_le_mul_right (3 ^ k) (supp_length d seed (d - 1 - k))
    rw [Nat.pow_succ]
    omega

theorem hl_correct (d seed : Nat) : ∀ k, k ≤ d → ∀ m, m < 2 ^ d → pc m ≤ d - k →
    hl d seed k m = if pc m = d - k then gs d seed (d - k) m else 0
  | 0, _, m, hm, _ => by
    rw [Nat.sub_zero, gs_top]
    simp only [hl]
    have := (pc_le d m hm).2
    by_cases h : m = 2 ^ d - 1
    · rw [if_pos h, if_pos (this.mpr h)]
    · rw [if_neg h, if_neg (fun h' => h (this.mp h'))]
  | k + 1, hk, m, hm, hp => by
    have hi : d - 1 - k < d := by omega
    have e1 : d - (k + 1) = d - 1 - k := by omega
    have e2 : d - 1 - k + 1 = d - k := by omega
    rw [e1, gs_step d seed _ m hi, e2]
    simp only [hl]
    rw [← sum_map_ite]
    apply sum_map_congr
    intro j hj
    have hjd := supp_lt d seed _ hi j hj
    cases hb : m.testBit j
    · have hpc := pc_clear j m hb
      have hor := add_eq_or m j hb
      have hlt : 2 ^ j + m < 2 ^ d := by
        rw [hor, Nat.one_shiftLeft]
        exact Nat.or_lt_two_pow hm (Nat.pow_lt_pow_right (by omega) hjd)
      rw [if_pos hlt, hl_correct d seed k (by omega) _ hlt (by omega)]
      simp only [Bool.false_eq_true, ↓reduceIte]
      by_cases hc : pc m = d - 1 - k
      · rw [if_pos (by omega), if_pos hc]
      · rw [if_neg (by omega), if_neg hc]
    · have hpc := pc_set j m hb
      simp only [↓reduceIte, ite_self]
      split
      · rename_i hlt
        rw [hl_correct d seed k (by omega) _ hlt (by omega), if_neg (by omega)]
      · rfl

/-! ## The packed loop -/

theorem row3_def (W G i a b : Nat) : row3 W G i a b = sh W G i + sh W G a + sh W G b := rfl

theorem enc_sh (W d j : Nat) (g : Nat → Nat) (hj : j < d) (hb : ∀ m, m < 2 ^ d → g m < 2 ^ W) :
    sh W (enc W g (2 ^ d)) j
      = enc W (fun m => if 2 ^ j + m < 2 ^ d then g (2 ^ j + m) else 0) (2 ^ d) := by
  have hjd : 2 ^ j ≤ 2 ^ d := Nat.pow_le_pow_right (by omega) (by omega)
  have := Nat.two_pow_pos j
  show enc W g (2 ^ d) >>> (W <<< j) = _
  rw [Nat.shiftLeft_eq, enc_shiftRight W g _ _ hjd hb, enc_pad W _ _ (2 ^ d) (by omega)]
  apply enc_congr
  intro m _
  by_cases h : m < 2 ^ d - 2 ^ j
  · rw [if_pos h, if_pos (by omega)]
  · rw [if_neg h, if_neg (by omega)]

theorem base_eq (W d seed : Nat) :
    Nat.shiftLeft (nat_lit 1) (Nat.mul W (Nat.sub (Nat.shiftLeft (nat_lit 1) d) (nat_lit 1)))
      = enc W (hl d seed 0) (2 ^ d) := by
  obtain ⟨t, ht⟩ : ∃ t, 2 ^ d = t + 1 := ⟨2 ^ d - 1, by have := Nat.two_pow_pos d; omega⟩
  show 1 <<< (W * (1 <<< d - 1)) = _
  rw [Nat.one_shiftLeft, Nat.one_shiftLeft, ht, Nat.add_sub_cancel, enc_split W _ t 1,
    enc_zero W t (fun m hm => by simp only [hl]; rw [if_neg (by omega)])]
  simp only [enc, hl, Nat.mul_zero, Nat.pow_zero, Nat.mul_one, Nat.zero_add, Nat.add_zero]
  rw [if_pos (by omega), Nat.mul_one]

theorem three_lt_width_aux : ∀ n d, d < n → 3 ^ d < 2 ^ ((27 * d + 17) / 17)
  | 0, d, h => absurd h (Nat.not_lt_zero _)
  | n + 1, d, h => by
    by_cases h17 : d < 17
    · have key : ∀ e, e < 17 → 3 ^ e < 2 ^ ((27 * e + 17) / 17) := by decide
      exact key d h17
    · obtain ⟨e, rfl⟩ : ∃ e, d = e + 17 := ⟨d - 17, by omega⟩
      have ih := three_lt_width_aux n e (by omega)
      rw [show (27 * (e + 17) + 17) / 17 = (27 * e + 17) / 17 + 27 by omega, Nat.pow_add,
        Nat.pow_add]
      exact Nat.mul_lt_mul_of_lt_of_lt ih (by decide)

theorem hl_succ (d seed k m : Nat) : hl d seed (k + 1) m = ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0)).sum := rfl

theorem loop_eq (d seed W : Nat) (hd : 3 ≤ d) (hW : 3 ^ d < 2 ^ W) : ∀ k, k ≤ d →
    loop d seed W k = enc W (hl d seed k) (2 ^ d)
  | 0, _ => base_eq W d seed
  | k + 1, hk => by
    show row d seed W (Nat.sub (Nat.sub d k) 1) (loop d seed W k) = _
    rw [loop_eq d seed W hd hW k (by omega), row_eq,
      show Nat.sub (Nat.sub d k) 1 = d - 1 - k by show d - k - 1 = _; omega]
    have hi : d - 1 - k < d := by omega
    have hb : ∀ m, m < 2 ^ d → hl d seed k m < 2 ^ W := fun m _ =>
      Nat.lt_of_le_of_lt (hl_bound d seed k m)
        (Nat.lt_of_le_of_lt (Nat.pow_le_pow_right (by omega) (by omega)) hW)
    have c1 := col1_facts d seed _ hd hi
    have c2 := col2_facts d seed _ hd hi
    rw [row3_def]
    rw [enc_sh W d _ _ hi hb, enc_sh W d _ _ c1.1 hb, enc_sh W d _ _ c2.1 hb, ← enc_add, ← enc_add]
    apply enc_congr
    intro m _
    have hs : supp d seed (d - 1 - k) = [d - 1 - k, permanentColumnOne d seed (d - 1 - k),
        permanentColumnTwo d seed (d - 1 - k)] := by
      unfold supp; rw [if_neg (by omega)]
    rw [hl_succ, hs, List.map_cons, List.map_cons, List.map_cons, List.map_nil, List.sum_cons,
      List.sum_cons, List.sum_cons, List.sum_nil, Nat.add_zero, Nat.add_assoc]

theorem main_eq (d s : Nat) (hd : 3 ≤ d) : main d s = permanentSpec (genPermanentMatrix d s) := by
  have hW : 3 ^ d < 2 ^ width d := three_lt_width_aux (d + 1) d (by omega)
  show loop d s (width d) d &&& (1 <<< width d - 1) = _
  rw [loop_eq d s (width d) hd hW d (Nat.le_refl d), Nat.one_shiftLeft,
    Nat.and_two_pow_sub_one_eq_mod]
  have e : 2 ^ d = 1 + (2 ^ d - 1) := by have := Nat.two_pow_pos d; omega
  have h0 := hl_correct d s d (Nat.le_refl d) 0 (Nat.two_pow_pos d) (by rw [pc_zero]; omega)
  rw [pc_zero, Nat.sub_self, if_pos rfl] at h0
  rw [e, enc_mod _ _ _ (by
    rw [h0]
    exact Nat.lt_of_le_of_lt (by
      have := hl_bound d s d 0
      rw [h0] at this; exact this) hW), h0]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows d (M d s) 0 = permanentRows (M d s).length (M d s) 0
  rw [M_length]

theorem impl_correct : ∀ n, impl n = permanentSpecN n := by
  intro n
  rcases Nat.lt_or_ge (n >>> 32) 3 with h | h
  · obtain ⟨t, ht⟩ : ∃ t, Nat.sub (nat_lit 3) (Nat.shiftRight n (nat_lit 32)) = t + 1 :=
      ⟨2 - (n >>> 32), by show 3 - (n >>> 32) = _; omega⟩
    unfold impl
    rw [ht]
  · have ht : Nat.sub (nat_lit 3) (Nat.shiftRight n (nat_lit 32)) = 0 := by
      show 3 - (n >>> 32) = 0; omega
    unfold impl
    rw [ht]
    exact main_eq _ _ h

end Submission
