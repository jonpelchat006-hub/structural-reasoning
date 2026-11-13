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
overflow: the first row has distinct shifts of a single 1, hence all lanes are at most
1, and after `k` rows every lane is at most `3^(k-1) < 2^W`
(`hl_one_bound`, `hl_bound_tight`, `three_lt_width_aux`).
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

open Lean Elab Term Meta in
/-- `eval% c` is the value of the closed natural-number term `c`, computed at elaboration time and
embedded as a literal (used for the large constant lane masks). -/
elab "eval% " e:term : term => do
  let e ← elabTermEnsuringType e (some (mkConst ``Nat))
  synthesizeSyntheticMVarsNoPostponing
  let r ← withTransparency .all <| whnf (← instantiateMVars e)
  match r with
  | .lit (.natVal n) => return mkRawNatLit n
  | _ => throwError "eval%: not a numeral: {r}"



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

/-- Tight width: the first row introduces no multiplicity. -/
def width (d : Nat) : Nat := Nat.div (Nat.add (Nat.mul (nat_lit 27) (Nat.sub d (nat_lit 1))) (nat_lit 17)) (nat_lit 17)

def main (d s : Nat) : Nat :=
  Nat.land (loop d s (width d) d) (Nat.sub (Nat.shiftLeft (nat_lit 1) (width d)) (nat_lit 1))

def implOld (n : Nat) : Nat :=
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

theorem three_distinct_indicators (a b c m n : Nat) (h1 : a ≠ b) (h2 : a ≠ c) (h3 : b ≠ c) :
    (if a + m < n then if a + m = n - 1 then 1 else 0 else 0) +
    ((if b + m < n then if b + m = n - 1 then 1 else 0 else 0) +
    (if c + m < n then if c + m = n - 1 then 1 else 0 else 0)) ≤ 1 := by
  split <;> (try split) <;> (try split) <;> (try split) <;> (try split) <;> (try split) <;> omega

theorem hl_one_bound (d seed m : Nat) (hd : 3 ≤ d) : hl d seed 1 m ≤ 1 := by
  have c1 := col1_facts d seed (d - 1) hd (by omega)
  have c2 := col2_facts d seed (d - 1) hd (by omega)
  have h1 : 2 ^ (d - 1) ≠ 2 ^ permanentColumnOne d seed (d - 1) := by
    intro h
    have := (Nat.pow_right_inj (by decide : 1 < 2)).mp h
    omega
  have h2 : 2 ^ (d - 1) ≠ 2 ^ permanentColumnTwo d seed (d - 1) := by
    intro h
    have := (Nat.pow_right_inj (by decide : 1 < 2)).mp h
    omega
  have h3 : 2 ^ permanentColumnOne d seed (d - 1) ≠ 2 ^ permanentColumnTwo d seed (d - 1) := by
    intro h
    have := (Nat.pow_right_inj (by decide : 1 < 2)).mp h
    omega
  have hs : supp d seed (d - 1) = [d - 1, permanentColumnOne d seed (d - 1), permanentColumnTwo d seed (d - 1)] := by
    unfold supp
    rw [if_neg (by omega : ¬d < 3)]
  have hg (i a b m n : Nat) (ha : 2 ^ i ≠ 2 ^ a) (hb : 2 ^ i ≠ 2 ^ b) (hc : 2 ^ a ≠ 2 ^ b) :
      (([i, a, b].map (fun j => if 2 ^ j + m < n then if 2 ^ j + m = n - 1 then 1 else 0 else 0)).sum) ≤ 1 := by
    exact three_distinct_indicators (2 ^ i) (2 ^ a) (2 ^ b) m n ha hb hc
  change ((supp d seed (d - 1)).map (fun j => if 2 ^ j + m < 2 ^ d then if 2 ^ j + m = 2 ^ d - 1 then 1 else 0 else 0)).sum ≤ 1
  rw [hs]
  exact hg (d - 1) (permanentColumnOne d seed (d - 1)) (permanentColumnTwo d seed (d - 1)) m (2 ^ d) h1 h2 h3
theorem hl_bound_tight (d seed : Nat) (hd : 3 ≤ d) :
    ∀ k m, hl d seed k m ≤ 3 ^ (k - 1)
  | 0, m => by simp only [hl]; split <;> simp
  | 1, m => by simpa using hl_one_bound d seed m hd
  | k + 2, m => by
    change ((supp d seed (d - 1 - (k + 1))).map (fun j => if 2 ^ j + m < 2 ^ d then hl d seed (k + 1) (2 ^ j + m) else 0)).sum ≤ 3 ^ (k + 1)
    have h1 := sum_map_le (fun j => if 2 ^ j + m < 2 ^ d then hl d seed (k + 1) (2 ^ j + m) else 0)
      (3 ^ k) (supp d seed (d - 1 - (k + 1))) (fun j (_ : j ∈ supp d seed (d - 1 - (k + 1))) => by
        show (if 2 ^ j + m < 2 ^ d then hl d seed (k + 1) (2 ^ j + m) else 0) ≤ 3 ^ k
        split
        · simpa using hl_bound_tight d seed hd (k + 1) _
        · exact Nat.zero_le _)
    have h2 := Nat.mul_le_mul_right (3 ^ k) (supp_length d seed (d - 1 - (k + 1)))
    simpa only [Nat.pow_succ, Nat.mul_comm] using Nat.le_trans h1 h2

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

theorem loop_eq (d seed W : Nat) (hd : 3 ≤ d) (hW : 3 ^ (d - 1) < 2 ^ W) : ∀ k, k ≤ d →
    loop d seed W k = enc W (hl d seed k) (2 ^ d)
  | 0, _ => base_eq W d seed
  | k + 1, hk => by
    show row d seed W (Nat.sub (Nat.sub d k) 1) (loop d seed W k) = _
    rw [loop_eq d seed W hd hW k (by omega), row_eq,
      show Nat.sub (Nat.sub d k) 1 = d - 1 - k by show d - k - 1 = _; omega]
    have hi : d - 1 - k < d := by omega
    have hb : ∀ m, m < 2 ^ d → hl d seed k m < 2 ^ W := fun m _ =>
      Nat.lt_of_le_of_lt (hl_bound_tight d seed hd k m)
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
  have hW : 3 ^ (d - 1) < 2 ^ width d := three_lt_width_aux d (d - 1) (by omega)
  show loop d s (width d) d &&& (1 <<< width d - 1) = _
  rw [loop_eq d s (width d) hd hW d (Nat.le_refl d), Nat.one_shiftLeft,
    Nat.and_two_pow_sub_one_eq_mod]
  have e : 2 ^ d = 1 + (2 ^ d - 1) := by have := Nat.two_pow_pos d; omega
  have h0 := hl_correct d s d (Nat.le_refl d) 0 (Nat.two_pow_pos d) (by rw [pc_zero]; omega)
  rw [pc_zero, Nat.sub_self, if_pos rfl] at h0
  rw [e, enc_mod _ _ _ (by
    rw [h0]
    exact Nat.lt_of_le_of_lt (by
      have := hl_bound_tight d s hd d 0
      rw [h0] at this; exact this) hW), h0]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows d (M d s) 0 = permanentRows (M d s).length (M d s) 0
  rw [M_length]

theorem implOld_correct : ∀ n, implOld n = permanentSpecN n := by
  intro n
  rcases Nat.lt_or_ge (n >>> 32) 3 with h | h
  · obtain ⟨t, ht⟩ : ∃ t, Nat.sub (nat_lit 3) (Nat.shiftRight n (nat_lit 32)) = t + 1 :=
      ⟨2 - (n >>> 32), by show 3 - (n >>> 32) = _; omega⟩
    unfold implOld
    rw [ht]
  · have ht : Nat.sub (nat_lit 3) (Nat.shiftRight n (nat_lit 32)) = 0 := by
      show 3 - (n >>> 32) = 0; omega
    unfold implOld
    rw [ht]
    exact main_eq _ _ h


/-! ## Lane library for packed vectors with `V`-bit lanes -/

section Lanes

variable (V : Nat)

theorem enc_mulc (g : Nat → Nat) (c : Nat) : ∀ L, enc V g L * c = enc V (fun m => g m * c) L
  | 0 => by simp [enc]
  | L + 1 => by
    simp only [enc]
    rw [Nat.add_mul, enc_mulc g c L, Nat.mul_right_comm]

theorem enc_tb (hV : 0 < V) (g : Nat → Nat) (p : Nat) : ∀ L, (∀ m, m < L → g m < 2 ^ V) →
    (enc V g L).testBit p = (decide (p / V < L) && (g (p / V)).testBit (p % V))
  | 0, _ => by simp [enc]
  | L + 1, h => by
    have h' : ∀ m, m < L → g m < 2 ^ V := fun m hm => h m (by omega)
    have hlt := enc_lt V g L h'
    rw [enc_succ_or V g L h', Nat.testBit_or, Nat.testBit_shiftLeft, enc_tb hV g p L h']
    rcases Nat.lt_or_ge p (V * L) with h1 | h1
    · have hq : p / V < L := (Nat.div_lt_iff_lt_mul hV).2 (by rw [Nat.mul_comm]; exact h1)
      simp [hq, show p / V < L + 1 by omega, show ¬ p ≥ V * L by omega]
    · rcases Nat.lt_or_ge p (V * (L + 1)) with h2 | h2
      · have hq : p / V = L := by
          apply Nat.div_eq_of_lt_le
          · rw [Nat.mul_comm]; exact h1
          · rw [Nat.mul_comm]; exact h2
        have hr : p % V = p - V * L := by
          rw [Nat.mod_eq_sub_mul_div, hq]
        simp [hq, hr, h1]
      · have hq : L + 1 ≤ p / V := (Nat.le_div_iff_mul_le hV).2 (by rw [Nat.mul_comm]; exact h2)
        have hb : (g L).testBit (p - V * L) = false := by
          apply Nat.testBit_lt_two_pow
          apply Nat.lt_of_lt_of_le (h L (by omega))
          apply Nat.pow_le_pow_right (by omega)
          rw [Nat.mul_add, Nat.mul_one] at h2; omega
        simp [hb, show ¬ p / V < L by omega, show ¬ p / V < L + 1 by omega]

theorem enc_xor (hV : 0 < V) (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ V)
    (hb : ∀ m, m < L → b m < 2 ^ V) :
    enc V a L ^^^ enc V b L = enc V (fun m => a m ^^^ b m) L := by
  apply Nat.eq_of_testBit_eq; intro p
  rw [Nat.testBit_xor, enc_tb V hV a p L ha, enc_tb V hV b p L hb,
    enc_tb V hV _ p L (fun m hm => Nat.xor_lt_two_pow (ha m hm) (hb m hm)), Nat.testBit_xor]
  by_cases h : p / V < L <;> simp [h]

theorem enc_and (hV : 0 < V) (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ V)
    (hb : ∀ m, m < L → b m < 2 ^ V) :
    enc V a L &&& enc V b L = enc V (fun m => a m &&& b m) L := by
  apply Nat.eq_of_testBit_eq; intro p
  rw [Nat.testBit_and, enc_tb V hV a p L ha, enc_tb V hV b p L hb,
    enc_tb V hV _ p L (fun m hm => Nat.and_lt_two_pow _ (hb m hm)), Nat.testBit_and]
  by_cases h : p / V < L <;> simp [h]

/-- Lane-wise shift right followed by a mask that clears what the next lane shifted in. -/
theorem enc_shr_and (hV : 0 < V) (a b : Nat → Nat) (s L : Nat) (hs : s ≤ V)
    (ha : ∀ m, m < L → a m < 2 ^ V) (hb : ∀ m, m < L → b m < 2 ^ (V - s)) :
    (enc V a L >>> s) &&& enc V b L = enc V (fun m => (a m >>> s) &&& b m) L := by
  have hb' : ∀ m, m < L → b m < 2 ^ V := fun m hm =>
    Nat.lt_of_lt_of_le (hb m hm) (Nat.pow_le_pow_right (by omega) (by omega))
  apply Nat.eq_of_testBit_eq; intro p
  rw [Nat.testBit_and, Nat.testBit_shiftRight, enc_tb V hV a _ L ha, enc_tb V hV b p L hb',
    enc_tb V hV _ p L (fun m hm => Nat.and_lt_two_pow _ (hb' m hm)), Nat.testBit_and,
    Nat.testBit_shiftRight]
  have hp := Nat.div_add_mod p V
  have hr := Nat.mod_lt p hV
  by_cases hc : p % V < V - s
  · have e1 : (s + p) / V = p / V := by
      rw [show s + p = (s + p % V) + V * (p / V) by omega, Nat.add_mul_div_left _ _ hV,
        Nat.div_eq_of_lt (by omega), Nat.zero_add]
    have e2 : (s + p) % V = s + p % V := by
      rw [show s + p = (s + p % V) + V * (p / V) by omega, Nat.add_mul_mod_self_left,
        Nat.mod_eq_of_lt (by omega)]
    rw [e1, e2]
    by_cases h : p / V < L <;> simp [h]
  · have hz : ∀ m, m < L → (b m).testBit (p % V) = false := fun m hm =>
      Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (hb m hm) (Nat.pow_le_pow_right (by omega) (by omega)))
    by_cases h : p / V < L
    · simp [h, hz _ h]
    · simp [h]

theorem enc_xs_and (hV : 0 < V) (a b : Nat → Nat) (s L : Nat) (hs : s ≤ V)
    (ha : ∀ m, m < L → a m < 2 ^ V) (hb : ∀ m, m < L → b m < 2 ^ (V - s)) :
    (enc V a L ^^^ (enc V a L >>> s)) &&& enc V b L
      = enc V (fun m => (a m ^^^ (a m >>> s)) &&& b m) L := by
  have hb' : ∀ m, m < L → b m < 2 ^ V := fun m hm =>
    Nat.lt_of_lt_of_le (hb m hm) (Nat.pow_le_pow_right (by omega) (by omega))
  rw [Nat.and_xor_distrib_right, enc_and V hV a b L ha hb', enc_shr_and V hV a b s L hs ha hb,
    enc_xor V hV _ _ L (fun m hm => Nat.and_lt_two_pow _ (hb' m hm))
      (fun m hm => Nat.and_lt_two_pow _ (hb' m hm))]
  apply enc_congr; intro m _
  rw [Nat.and_xor_distrib_right]

theorem enc_sub (a b : Nat → Nat) (L : Nat) (h : ∀ m, m < L → b m ≤ a m) :
    enc V a L - enc V b L = enc V (fun m => a m - b m) L := by
  have e : enc V a L = enc V (fun m => a m - b m) L + enc V b L := by
    rw [← enc_add]; exact enc_congr V L (fun m hm => by have := h m hm; omega)
  rw [e, Nat.add_sub_cancel]

theorem enc_get (a : Nat → Nat) (L j : Nat) (hj : j < L) (ha : ∀ m, m < L → a m < 2 ^ V) :
    (enc V a L >>> (V * j)) % 2 ^ V = a j := by
  rw [enc_shiftRight V a j L (by omega) ha, show L - j = 1 + (L - j - 1) by omega,
    enc_mod V _ _ (by simpa using ha j hj)]
  simp

theorem enc_low (a : Nat → Nat) (L t : Nat) (ha : ∀ m, m < L + t → a m < 2 ^ V) :
    enc V a (L + t) % 2 ^ (V * L) = enc V a L := by
  rw [enc_split, Nat.add_mul_mod_self_left,
    Nat.mod_eq_of_lt (enc_lt V a L (fun m hm => ha m (by omega)))]

theorem enc_high (a : Nat → Nat) (L t : Nat) (ha : ∀ m, m < L + t → a m < 2 ^ V) :
    enc V a (L + t) >>> (V * L) = enc V (fun m => a (L + m)) t := by
  rw [enc_shiftRight V a L (L + t) (by omega) ha, Nat.add_sub_cancel_left]

theorem enc_eq_zero (a : Nat → Nat) : ∀ L, enc V a L = 0 → ∀ m, m < L → a m = 0
  | 0, _, m, hm => absurd hm (Nat.not_lt_zero _)
  | L + 1, h, m, hm => by
    simp only [enc] at h
    have h1 : enc V a L = 0 := by omega
    have h2 : a L * 2 ^ (V * L) = 0 := by omega
    rcases Nat.lt_or_ge m L with hl | hl
    · exact enc_eq_zero a L h1 m hl
    · rw [show m = L by omega]
      rcases Nat.mul_eq_zero.mp h2 with h3 | h3
      · exact h3
      · exact absurd h3 (Nat.pos_iff_ne_zero.mp (Nat.two_pow_pos _))

theorem enc_ones (hV : 0 < V) : ∀ L, (2 ^ (V * L) - 1) / (2 ^ V - 1) = enc V (fun _ => 1) L := by
  have hd : 0 < 2 ^ V - 1 := by
    have : 2 ≤ 2 ^ V := by
      calc 2 = 2 ^ 1 := rfl
        _ ≤ 2 ^ V := Nat.pow_le_pow_right (by omega) hV
    omega
  have key : ∀ L, 2 ^ (V * L) - 1 = (2 ^ V - 1) * enc V (fun _ => 1) L := by
    intro L
    induction L with
    | zero => simp [enc]
    | succ L ih =>
      have e1 : enc V (fun _ => 1) (L + 1) = enc V (fun _ => 1) L + 2 ^ (V * L) := by simp [enc]
      rw [e1, Nat.mul_add (2 ^ V - 1), ← ih, show V * (L + 1) = V * L + V by rw [Nat.mul_succ], Nat.pow_add]
      have h1 : 1 ≤ 2 ^ (V * L) := Nat.one_le_two_pow
      have h2 : 1 ≤ 2 ^ V := Nat.one_le_two_pow
      have h3 : (2 ^ V - 1) * 2 ^ (V * L) = 2 ^ (V * L) * 2 ^ V - 2 ^ (V * L) := by
        rw [Nat.sub_mul, Nat.one_mul, Nat.mul_comm]
      have h4 : 2 ^ (V * L) ≤ 2 ^ (V * L) * 2 ^ V := Nat.le_mul_of_pos_right _ h2
      omega
  intro L
  rw [key L, Nat.mul_div_cancel_left _ hd]

end Lanes

/-! ## Primitive-op forms of the lane lemmas -/

section LanesP
variable (V : Nat)

theorem P_add (a b : Nat → Nat) (L : Nat) :
    Nat.add (enc V a L) (enc V b L) = enc V (fun m => a m + b m) L := (enc_add V a b L).symm

theorem P_mulr (a : Nat → Nat) (c L : Nat) :
    Nat.mul (enc V a L) c = enc V (fun m => a m * c) L := enc_mulc V a c L

theorem P_mull (a : Nat → Nat) (c L : Nat) :
    Nat.mul c (enc V a L) = enc V (fun m => a m * c) L := by
  rw [← enc_mulc]; exact Nat.mul_comm _ _

theorem P_xor (hV : 0 < V) (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ V)
    (hb : ∀ m, m < L → b m < 2 ^ V) :
    Nat.xor (enc V a L) (enc V b L) = enc V (fun m => a m ^^^ b m) L := enc_xor V hV a b L ha hb

theorem P_and (hV : 0 < V) (a b : Nat → Nat) (L : Nat) (ha : ∀ m, m < L → a m < 2 ^ V)
    (hb : ∀ m, m < L → b m < 2 ^ V) :
    Nat.land (enc V a L) (enc V b L) = enc V (fun m => a m &&& b m) L := enc_and V hV a b L ha hb

theorem P_shr_and (hV : 0 < V) (a b : Nat → Nat) (s L : Nat) (hs : s ≤ V)
    (ha : ∀ m, m < L → a m < 2 ^ V) (hb : ∀ m, m < L → b m < 2 ^ (V - s)) :
    Nat.land (Nat.shiftRight (enc V a L) s) (enc V b L) = enc V (fun m => (a m >>> s) &&& b m) L :=
  enc_shr_and V hV a b s L hs ha hb

theorem P_xs_and (hV : 0 < V) (a b : Nat → Nat) (s L : Nat) (hs : s ≤ V)
    (ha : ∀ m, m < L → a m < 2 ^ V) (hb : ∀ m, m < L → b m < 2 ^ (V - s)) :
    Nat.land (Nat.xor (enc V a L) (Nat.shiftRight (enc V a L) s)) (enc V b L)
      = enc V (fun m => (a m ^^^ (a m >>> s)) &&& b m) L :=
  enc_xs_and V hV a b s L hs ha hb

theorem P_sub (a b : Nat → Nat) (L : Nat) (h : ∀ m, m < L → b m ≤ a m) :
    Nat.sub (enc V a L) (enc V b L) = enc V (fun m => a m - b m) L := enc_sub V a b L h

end LanesP

/-! ## Seeded columns of all rows at once (72-bit lanes) -/

/-- Salted row offset of lane `j`: lanes `j < D` are row `j` with the first salt, lanes `D + i`
are row `i` with the second salt. -/
def kOf (D j : Nat) : Nat :=
  (if j < D then j else j - D) * 0x9e3779b9 ^^^ (if j < D then 0x85ebca6b else 0xc2b2ae35)

def kcOf (D j : Nat) : Nat := (kOf D j ^^^ (kOf D j >>> 16)) &&& 0xffffffff

def mixT (T : Nat) : Nat :=
  let y1 := (T * 0x7feb352d) &&& 0xffffffff
  let v := (y1 ^^^ (y1 >>> 15)) &&& 0xffffffff
  let y2 := (v * 0x846ca68b) &&& 0xffffffff
  (y2 ^^^ (y2 >>> 16)) &&& 0xffffffff

theorem mulmask (A c : Nat) : (A * c) &&& 0xffffffff = ((A &&& 0xffffffff) * c) &&& 0xffffffff := by
  rw [show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl]
  simp only [Nat.and_two_pow_sub_one_eq_mod]
  rw [Nat.mul_mod A c, Nat.mul_mod (A % 2 ^ 32) c, Nat.mod_mod]

theorem lt72_of_lt32 {x : Nat} (h : x < 2 ^ 32) : x < 2 ^ 72 :=
  Nat.lt_of_lt_of_le h (Nat.pow_le_pow_right (by decide) (by decide))

theorem mul_lt72 {x c : Nat} (h : x < 2 ^ 32) (hc : c < 2 ^ 40) : x * c < 2 ^ 72 := by
  calc x * c < 2 ^ 32 * 2 ^ 40 := Nat.mul_lt_mul'' h hc
    _ = 2 ^ 72 := by rw [← Nat.pow_add]

theorem and32 (x : Nat) : x &&& 0xffffffff < 2 ^ 32 := Nat.and_lt_two_pow _ (by decide)

theorem xs_split (s K : Nat) (hs : s < 2 ^ 32) :
    ((s ^^^ K) ^^^ ((s ^^^ K) >>> 16)) &&& 0xffffffff
      = (s ^^^ (s >>> 16)) ^^^ ((K ^^^ (K >>> 16)) &&& 0xffffffff) := by
  apply Nat.eq_of_testBit_eq; intro i
  simp only [Nat.testBit_and, Nat.testBit_xor, Nat.testBit_shiftRight]
  rw [show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl, Nat.testBit_two_pow_sub_one]
  by_cases hi : i < 32
  · simp only [hi, decide_true, Bool.and_true]
    cases s.testBit i <;> cases K.testBit i <;> cases s.testBit (16 + i) <;>
      cases K.testBit (16 + i) <;> rfl
  · have e1 : s.testBit i = false :=
      Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hs (Nat.pow_le_pow_right (by omega) (by omega)))
    have e2 : s.testBit (16 + i) = false :=
      Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hs (Nat.pow_le_pow_right (by omega) (by omega)))
    simp [hi, e1, e2]

theorem mix_split (s K : Nat) (hs : s < 2 ^ 32) :
    permanentMix32 (s ^^^ K)
      = mixT ((s ^^^ (s >>> 16)) ^^^ ((K ^^^ (K >>> 16)) &&& 0xffffffff)) := by
  unfold permanentMix32 mixT
  simp only []
  rw [mulmask ((s ^^^ K) ^^^ ((s ^^^ K) >>> 16)), xs_split s K hs,
    mulmask (_ ^^^ _ >>> 15) 0x846ca68b]

theorem kcOf_lt (D j : Nat) : kcOf D j < 2 ^ 32 := Nat.and_lt_two_pow _ (by decide)

/-- All `2·D` mixer outputs as one vector (lane `j` = `mixT (t0 ^^^ kc j)`). -/
def vecZ (R Kc Mv s : Nat) : Nat :=
  share t0 := Nat.xor s (Nat.shiftRight s (nat_lit 16));
  share X1 := Nat.xor (Nat.mul R t0) Kc;
  share X2 := Nat.land (Nat.mul (nat_lit 0x7feb352d) X1) Mv;
  share X3 := Nat.land (Nat.xor X2 (Nat.shiftRight X2 (nat_lit 15))) Mv;
  share X4 := Nat.land (Nat.mul (nat_lit 0x846ca68b) X3) Mv;
  Nat.land (Nat.xor X4 (Nat.shiftRight X4 (nat_lit 16))) Mv

theorem vecZ_eq (n s : Nat) (kc : Nat → Nat) (hs : s < 2 ^ 32) (hkc : ∀ j, j < n → kc j < 2 ^ 32) :
    vecZ (enc 72 (fun _ => 1) n) (enc 72 kc n) (enc 72 (fun _ => 0xffffffff) n) s
      = enc 72 (fun j => mixT ((s ^^^ (s >>> 16)) ^^^ kc j)) n := by
  have h72 : (0 : Nat) < 72 := by decide
  have ht0 : s ^^^ (s >>> 16) < 2 ^ 32 :=
    Nat.xor_lt_two_pow hs (Nat.lt_of_le_of_lt (Nat.shiftRight_le s 16) hs)
  have hM : ∀ j, j < n → (0xffffffff : Nat) < 2 ^ 72 := fun _ _ => by decide
  have hM15 : ∀ j, j < n → (0xffffffff : Nat) < 2 ^ (72 - 15) := fun _ _ => by decide
  have hM16 : ∀ j, j < n → (0xffffffff : Nat) < 2 ^ (72 - 16) := fun _ _ => by decide
  have hT : ∀ j, j < n → (s ^^^ (s >>> 16)) ^^^ kc j < 2 ^ 32 := fun j hj =>
    Nat.xor_lt_two_pow ht0 (hkc j hj)
  have e1 : Nat.xor (Nat.mul (enc 72 (fun _ => 1) n) (Nat.xor s (Nat.shiftRight s 16)))
      (enc 72 kc n) = enc 72 (fun j => (s ^^^ (s >>> 16)) ^^^ kc j) n := by
    rw [P_mulr, P_xor 72 h72 _ _ n (fun j _ => by simp; exact lt72_of_lt32 ht0)
      (fun j hj => lt72_of_lt32 (hkc j hj))]
    apply enc_congr; intro j _; simp
  unfold vecZ
  rw [e1, P_mull, P_and 72 h72 _ _ n (fun j hj => mul_lt72 (hT j hj) (by decide)) hM,
    P_xs_and 72 h72 _ _ 15 n (by decide) (fun j _ => lt72_of_lt32 (and32 _)) hM15,
    P_mull, P_and 72 h72 _ _ n (fun j hj => mul_lt72 (and32 _) (by decide)) hM,
    P_xs_and 72 h72 _ _ 16 n (by decide) (fun j _ => lt72_of_lt32 (and32 _)) hM16]
  rfl

/-- Lane-wise `z mod m` through a multiply-high quotient. -/
def vecK (Mg S m Mv Z : Nat) : Nat :=
  Nat.sub Z (Nat.mul m (Nat.land (Nat.shiftRight (Nat.mul Mg Z) S) Mv))

theorem modlane (x Mg S m : Nat) (hx : x < 2 ^ 32)
    (hdiv : ∀ y, y < 2 ^ 32 → y * Mg / 2 ^ S = y / m) :
    ((x * Mg) >>> S) &&& 0xffffffff = x / m := by
  rw [Nat.shiftRight_eq_div_pow, hdiv x hx, show (0xffffffff : Nat) = 2 ^ 32 - 1 from rfl,
    Nat.and_two_pow_sub_one_eq_mod, Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt (Nat.div_le_self x m) hx)]

theorem vecK_eq (n Mg S m : Nat) (z : Nat → Nat) (hz : ∀ j, j < n → z j < 2 ^ 32)
    (hMg : Mg < 2 ^ 40) (hS : S ≤ 40) (hdiv : ∀ x, x < 2 ^ 32 → x * Mg / 2 ^ S = x / m) :
    vecK Mg S m (enc 72 (fun _ => 0xffffffff) n) (enc 72 z n) = enc 72 (fun j => z j % m) n := by
  have h72 : (0 : Nat) < 72 := by decide
  have hM : ∀ j, j < n → (0xffffffff : Nat) < 2 ^ (72 - S) := fun _ _ =>
    Nat.lt_of_lt_of_le (by decide : (0xffffffff : Nat) < 2 ^ 32) (Nat.pow_le_pow_right (by omega) (by omega))
  unfold vecK
  rw [P_mull, P_shr_and 72 h72 _ _ S n (by omega) (fun j hj => mul_lt72 (hz j hj) hMg) hM, P_mull,
    P_sub 72 _ _ n (fun j hj => by rw [modlane _ _ _ _ (hz j hj) hdiv]; exact Nat.div_mul_le_self _ _)]
  apply enc_congr; intro j hj
  rw [modlane _ _ _ _ (hz j hj) hdiv, Nat.mod_eq_sub_mul_div, Nat.mul_comm]

/-! ## The skip maps, lane-parallel -/

def vecC (g1 o K1 : Nat) : Nat := Nat.land (Nat.shiftRight (Nat.add g1 K1) (nat_lit 5)) o

def vecA (K1 C : Nat) : Nat := Nat.add K1 C

def vecB (g0 g2 o K1 K2 C : Nat) : Nat :=
  Nat.add (Nat.add K2 (Nat.land (Nat.shiftRight (Nat.sub (Nat.add g0 K2) K1) (nat_lit 5)) o))
    (Nat.land (Nat.shiftRight (Nat.sub (Nat.add g2 K2) C) (nat_lit 5)) o)

theorem bit5 (x : Nat) (hx : x < 64) : (x >>> 5) &&& 1 = if 32 ≤ x then 1 else 0 := by
  rw [Nat.shiftRight_eq_div_pow, Nat.and_one_is_mod]
  split <;> omega

theorem small72 {x : Nat} (h : x < 64) : x < 2 ^ 72 := Nat.lt_of_lt_of_le h (by decide)

theorem vecC_eq (n : Nat) (k1 : Nat → Nat) (hn : n ≤ 16) (hk1 : ∀ i, i < n → k1 i < 16) :
    vecC (enc 72 (fun i => 32 - i) n) (enc 72 (fun _ => 1) n) (enc 72 k1 n)
      = enc 72 (fun i => if i ≤ k1 i then 1 else 0) n := by
  have h72 : (0 : Nat) < 72 := by decide
  unfold vecC
  rw [P_add, P_shr_and 72 h72 _ _ 5 n (by decide)
    (fun i hi => small72 (by have := hk1 i hi; omega)) (fun _ _ => by decide)]
  apply enc_congr; intro i hi
  have := hk1 i hi
  rw [bit5 _ (by omega)]
  by_cases h : i ≤ k1 i
  · rw [if_pos (by omega), if_pos h]
  · rw [if_neg (by omega), if_neg h]

theorem vecA_eq (n : Nat) (k1 c : Nat → Nat) :
    vecA (enc 72 k1 n) (enc 72 c n) = enc 72 (fun i => k1 i + c i) n := P_add 72 k1 c n

theorem vecB_eq (n : Nat) (k1 k2 c : Nat → Nat) (hn : n ≤ 16) (hk1 : ∀ i, i < n → k1 i < 16)
    (hk2 : ∀ i, i < n → k2 i < 16) (hc : ∀ i, i < n → c i ≤ 1) :
    vecB (enc 72 (fun _ => 32) n) (enc 72 (fun i => 33 - i) n) (enc 72 (fun _ => 1) n)
      (enc 72 k1 n) (enc 72 k2 n) (enc 72 c n)
      = enc 72 (fun i => (k2 i + (if k1 i ≤ k2 i then 1 else 0)) +
          (if i + c i ≤ k2 i + 1 then 1 else 0)) n := by
  have h72 : (0 : Nat) < 72 := by decide
  unfold vecB
  rw [P_add, P_sub 72 _ _ n (fun i hi => by have := hk1 i hi; omega),
    P_shr_and 72 h72 _ _ 5 n (by decide)
      (fun i hi => small72 (by have := hk2 i hi; omega)) (fun _ _ => by decide),
    P_add, P_add, P_sub 72 _ _ n (fun i hi => by have := hc i hi; omega),
    P_shr_and 72 h72 _ _ 5 n (by decide)
      (fun i hi => small72 (by have := hk2 i hi; omega)) (fun _ _ => by decide), P_add]
  apply enc_congr; intro i hi
  have := hk1 i hi; have := hk2 i hi; have := hc i hi
  rw [bit5 _ (by omega), bit5 _ (by omega)]
  congr 1
  · congr 1
    by_cases h : k1 i ≤ k2 i
    · rw [if_pos (by omega), if_pos h]
    · rw [if_neg (by omega), if_neg h]
  · by_cases h : i + c i ≤ k2 i + 1
    · rw [if_pos (by omega), if_pos h]
    · rw [if_neg (by omega), if_neg h]

/-- The skip maps in terms of the two reduced mixer values. -/
theorem skip_lanes (i k1 k2 : Nat) :
    k1 + (if i ≤ k1 then 1 else 0) = permanentSkipOne i k1 ∧
    (k2 + (if k1 ≤ k2 then 1 else 0)) + (if i + (if i ≤ k1 then 1 else 0) ≤ k2 + 1 then 1 else 0)
      = permanentSkipTwo i (permanentSkipOne i k1) k2 := by
  unfold permanentSkipTwo permanentSkipOne
  simp only [Nat.min_def, Nat.max_def]
  constructor
  · split <;> split <;> omega
  · by_cases h1 : k1 < i <;> by_cases h2 : i ≤ k1 <;> by_cases h3 : k1 ≤ k2 <;>
      simp only [h1, h2, h3, if_true, if_false] <;> (repeat' split) <;> omega

/-! ## Reading one lane -/

def colV (A i : Nat) : Nat :=
  Nat.mod (Nat.shiftRight A (Nat.mul (nat_lit 72) i)) (nat_lit 4722366482869645213696)

theorem colV_eq (a : Nat → Nat) (n i : Nat) (hi : i < n) (ha : ∀ j, j < n → a j < 2 ^ 72) :
    colV (enc 72 a n) i = a i := by
  show (enc 72 a n >>> (72 * i)) % 2 ^ 72 = a i
  exact enc_get 72 a n i hi ha

/-! ## All seeded columns from one vector computation -/

theorem mixT_lt (T : Nat) : mixT T < 2 ^ 32 := and32 _

theorem kOf_lo (D i : Nat) (hi : i < D) : kOf D i = i * 0x9e3779b9 ^^^ 0x85ebca6b := by
  unfold kOf; rw [if_pos hi, if_pos hi]

theorem kOf_hi (D i : Nat) : kOf D (D + i) = i * 0x9e3779b9 ^^^ 0xc2b2ae35 := by
  unfold kOf; rw [if_neg (by omega), if_neg (by omega), Nat.add_sub_cancel_left]

theorem cols_eq (D s R Kc Mv P sh MvD Mg1 S1 Mg2 S2 g1 g0 g2 o : Nat) (hD : 3 ≤ D) (hD16 : D ≤ 16)
    (hs : s < 2 ^ 32)
    (hR : R = enc 72 (fun _ => 1) (D + D)) (hKc : Kc = enc 72 (kcOf D) (D + D))
    (hMv : Mv = enc 72 (fun _ => 0xffffffff) (D + D)) (hP : P = 2 ^ (72 * D)) (hsh : sh = 72 * D)
    (hMvD : MvD = enc 72 (fun _ => 0xffffffff) D)
    (hMg1 : Mg1 < 2 ^ 40) (hS1 : S1 ≤ 40) (hdiv1 : ∀ x, x < 2 ^ 32 → x * Mg1 / 2 ^ S1 = x / (D - 1))
    (hMg2 : Mg2 < 2 ^ 40) (hS2 : S2 ≤ 40) (hdiv2 : ∀ x, x < 2 ^ 32 → x * Mg2 / 2 ^ S2 = x / (D - 2))
    (hg1 : g1 = enc 72 (fun i => 32 - i) D) (hg0 : g0 = enc 72 (fun _ => 32) D)
    (hg2 : g2 = enc 72 (fun i => 33 - i) D) (ho : o = enc 72 (fun _ => 1) D) :
    (∀ i, i < D → colV (vecA (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P))
        (vecC g1 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P)))) i
        = permanentColumnOne D s i) ∧
    (∀ i, i < D → colV (vecB g0 g2 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P))
        (vecK Mg2 S2 (D - 2) MvD (Nat.shiftRight (vecZ R Kc Mv s) sh))
        (vecC g1 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P)))) i
        = permanentColumnTwo D s i) := by
  subst hR hKc hMv hP hsh hMvD hg1 hg0 hg2 ho
  -- the mixer outputs
  let z : Nat → Nat := fun j => mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D j)
  have hz : ∀ j, j < D + D → z j < 2 ^ 72 := fun j _ => lt72_of_lt32 (mixT_lt _)
  have hZ := vecZ_eq (D + D) s (kcOf D) hs (fun j _ => kcOf_lt D j)
  have hZ1 : Nat.mod (vecZ (enc 72 (fun _ => 1) (D + D)) (enc 72 (kcOf D) (D + D))
      (enc 72 (fun _ => 0xffffffff) (D + D)) s) (2 ^ (72 * D)) = enc 72 z D := by
    rw [hZ]; exact enc_low 72 z D D hz
  have hZ2 : Nat.shiftRight (vecZ (enc 72 (fun _ => 1) (D + D)) (enc 72 (kcOf D) (D + D))
      (enc 72 (fun _ => 0xffffffff) (D + D)) s) (72 * D) = enc 72 (fun j => z (D + j)) D := by
    rw [hZ]; exact enc_high 72 z D D hz
  rw [hZ1, hZ2, vecK_eq D Mg1 S1 (D - 1) z (fun j _ => mixT_lt _) hMg1 hS1 hdiv1,
    vecK_eq D Mg2 S2 (D - 2) (fun j => z (D + j)) (fun j _ => mixT_lt _) hMg2 hS2 hdiv2]
  have hk1 : ∀ i, i < D → z i % (D - 1) < 16 := fun i _ =>
    Nat.lt_of_lt_of_le (Nat.mod_lt _ (by omega)) (by omega)
  have hk2 : ∀ i, i < D → z (D + i) % (D - 2) < 16 := fun i _ =>
    Nat.lt_of_lt_of_le (Nat.mod_lt _ (by omega)) (by omega)
  rw [vecC_eq D (fun i => z i % (D - 1)) hD16 hk1, vecA_eq,
    vecB_eq D _ _ _ hD16 hk1 hk2 (fun i _ => by split <;> omega)]
  -- lane values are the spec columns
  have hm1 : ∀ i, i < D → z i % (D - 1)
      = permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0x85ebca6b) % (D - 1) := by
    intro i hi
    show mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D i) % (D - 1) = _
    unfold kcOf
    rw [← mix_split s _ hs, kOf_lo D i hi, Nat.xor_assoc]
  have hm2 : ∀ i, i < D → z (D + i) % (D - 2)
      = permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35) % (D - 2) := by
    intro i hi
    show mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D (D + i)) % (D - 2) = _
    unfold kcOf
    rw [← mix_split s _ hs, kOf_hi D i, Nat.xor_assoc]
  constructor
  · intro i hi
    rw [colV_eq _ D i hi (fun j hj => small72 (by
      have := hk1 j hj; split <;> omega))]
    show z i % (D - 1) + (if i ≤ z i % (D - 1) then 1 else 0) = _
    rw [hm1 i hi]
    unfold permanentColumnOne
    exact (skip_lanes i _ (permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35) % (D - 2))).1
  · intro i hi
    rw [colV_eq _ D i hi (fun j hj => small72 (by
      have := hk1 j hj; have := hk2 j hj; split <;> split <;> split <;> omega))]
    show (z (D + i) % (D - 2) + (if z i % (D - 1) ≤ z (D + i) % (D - 2) then 1 else 0)) +
      (if i + (if i ≤ z i % (D - 1) then 1 else 0) ≤ z (D + i) % (D - 2) + 1 then 1 else 0) = _
    rw [hm1 i hi, hm2 i hi]
    unfold permanentColumnTwo permanentColumnOne
    exact (skip_lanes i _ _).2

/-! ## The packed DP with columns read from the vectors, and an overflow check -/

def loopV (D W A B : Nat) (k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (Nat.shiftLeft (nat_lit 1) (Nat.mul W (Nat.sub (Nat.shiftLeft (nat_lit 1) D) (nat_lit 1))))
    (fun k G => row3 W G (Nat.sub (Nat.sub D k) (nat_lit 1))
      (colV A (Nat.sub (Nat.sub D k) (nat_lit 1))) (colV B (Nat.sub (Nat.sub D k) (nat_lit 1)))) k

theorem loopV_succ (D W A B k : Nat) : loopV D W A B (k + 1)
    = row3 W (loopV D W A B k) (D - 1 - k) (colV A (D - 1 - k)) (colV B (D - 1 - k)) := by
  show row3 W (loopV D W A B k) (Nat.sub (Nat.sub D k) 1) (colV A (Nat.sub (Nat.sub D k) 1))
    (colV B (Nat.sub (Nat.sub D k) 1)) = _
  rw [show Nat.sub (Nat.sub D k) 1 = D - 1 - k by show D - k - 1 = _; omega]

/-- Lane mask of the bits `c, …, W-1`. -/
def topMask (W c : Nat) : Nat := (2 ^ W - 1) ^^^ (2 ^ c - 1)

theorem topMask_lt (W c : Nat) (hcW : c ≤ W) : topMask W c < 2 ^ W :=
  Nat.xor_lt_two_pow (Nat.sub_lt (Nat.two_pow_pos W) (by decide))
    (Nat.lt_of_lt_of_le (Nat.sub_lt (Nat.two_pow_pos c) (by decide))
      (Nat.pow_le_pow_right (by decide) hcW))

theorem land_mask_lt (x W c : Nat) (hx : x < 2 ^ W) (h : x &&& topMask W c = 0) : x < 2 ^ c := by
  apply Nat.lt_pow_two_of_testBit
  intro i hi
  by_cases hiW : i < W
  · have := congrArg (fun y => y.testBit i) h
    simp only [Nat.testBit_and, topMask, Nat.testBit_xor, Nat.testBit_two_pow_sub_one,
      Nat.zero_testBit] at this
    simp only [hiW, decide_true, show ¬ i < c by omega, decide_false, Bool.true_xor,
      Bool.not_false, Bool.and_true] at this
    exact this
  · exact Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le hx (Nat.pow_le_pow_right (by decide) (by omega)))

theorem hl_step_bound (d seed k b : Nat) (hb : ∀ m, m < 2 ^ d → hl d seed k m ≤ b) :
    ∀ m, hl d seed (k + 1) m ≤ 3 * b := by
  intro m
  rw [hl_succ]
  have h1 := sum_map_le (fun j => if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0) b
    (supp d seed (d - 1 - k)) (fun j _ => by
      show (if 2 ^ j + m < 2 ^ d then hl d seed k (2 ^ j + m) else 0) ≤ b
      split
      · exact hb _ (by assumption)
      · exact Nat.zero_le _)
  have h2 := Nat.mul_le_mul_right b (supp_length d seed (d - 1 - k))
  omega

theorem hl_zero_lt (d seed W m : Nat) (hW : 1 ≤ W) : hl d seed 0 m < 2 ^ W := by
  have : 2 ≤ 2 ^ W := by
    calc 2 = 2 ^ 1 := rfl
      _ ≤ 2 ^ W := Nat.pow_le_pow_right (by decide) hW
  simp only [hl]; split <;> omega

theorem loopV_eq (D K seed W c A B Mask : Nat) (hd : 3 ≤ D) (hK : K ≤ D)
    (hA : ∀ i, i < D → colV A i = permanentColumnOne D seed i)
    (hB : ∀ i, i < D → colV B i = permanentColumnTwo D seed i)
    (hW : 1 ≤ W) (hc : 3 * 2 ^ c ≤ 2 ^ W) (hcW : c ≤ W)
    (hMask : Mask = enc W (fun _ => topMask W c) (2 ^ D))
    (hchk : ∀ k, k < K → 2 ^ W ≤ 3 ^ k → Nat.land (loopV D W A B k) Mask = 0) :
    ∀ k, k ≤ K → loopV D W A B k = enc W (hl D seed k) (2 ^ D) ∧
      ∀ m, m < 2 ^ D → hl D seed k m < 2 ^ W
  | 0, _ => ⟨base_eq W D seed, fun m _ => hl_zero_lt D seed W m hW⟩
  | k + 1, hk => by
    obtain ⟨ih1, ih2⟩ := loopV_eq D K seed W c A B Mask hd hK hA hB hW hc hcW hMask hchk k (by omega)
    have hi : D - 1 - k < D := by omega
    have c1 := col1_facts D seed _ hd hi
    have c2 := col2_facts D seed _ hd hi
    have e : loopV D W A B (k + 1) = enc W (hl D seed (k + 1)) (2 ^ D) := by
      rw [loopV_succ, ih1, hA _ hi, hB _ hi, row3_def, enc_sh W D _ _ hi ih2,
        enc_sh W D _ _ c1.1 ih2, enc_sh W D _ _ c2.1 ih2, ← enc_add, ← enc_add]
      apply enc_congr
      intro m _
      have hs : supp D seed (D - 1 - k) = [D - 1 - k, permanentColumnOne D seed (D - 1 - k),
          permanentColumnTwo D seed (D - 1 - k)] := by
        unfold supp; rw [if_neg (by omega)]
      rw [hl_succ, hs, List.map_cons, List.map_cons, List.map_cons, List.map_nil, List.sum_cons,
        List.sum_cons, List.sum_cons, List.sum_nil, Nat.add_zero, Nat.add_assoc]
    refine ⟨e, fun m hm => ?_⟩
    by_cases h3 : 3 ^ k < 2 ^ W
    · exact Nat.lt_of_le_of_lt (by simpa using hl_bound_tight D seed hd (k + 1) m) h3
    · have hz := hchk k (by omega) (by omega)
      rw [ih1, hMask] at hz
      have hz' : enc W (fun m => hl D seed k m &&& topMask W c) (2 ^ D) = 0 := by
        rw [← enc_and W (by omega) _ _ _ ih2 (fun _ _ => topMask_lt W c hcW)]; exact hz
      have hlt : ∀ m, m < 2 ^ D → hl D seed k m ≤ 2 ^ c - 1 := fun m hm => by
        have := land_mask_lt _ W c (ih2 m hm) (enc_eq_zero W _ _ hz' m hm)
        omega
      have := hl_step_bound D seed k (2 ^ c - 1) hlt m
      have : 1 ≤ 2 ^ c := Nat.one_le_two_pow
      omega

theorem final_eq (D seed W G : Nat) (hG : G = enc W (hl D seed D) (2 ^ D))
    (hb : ∀ m, m < 2 ^ D → hl D seed D m < 2 ^ W) :
    Nat.land G (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1))
      = permanentSpec (genPermanentMatrix D seed) := by
  show G &&& (1 <<< W - 1) = _
  rw [hG, Nat.one_shiftLeft, Nat.and_two_pow_sub_one_eq_mod]
  have e : 2 ^ D = 1 + (2 ^ D - 1) := by have := Nat.two_pow_pos D; omega
  have h0 := hl_correct D seed D (Nat.le_refl D) 0 (Nat.two_pow_pos D) (by rw [pc_zero]; omega)
  rw [pc_zero, Nat.sub_self, if_pos rfl] at h0
  rw [e, enc_mod _ _ _ (by rw [e] at hb; exact hb 0 (by omega)), h0]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows D (M D seed) 0 = permanentRows (M D seed).length (M D seed) 0
  rw [M_length]

/-- `Σ_{j<n} f (k0 + j)`. -/
def chkSum (f : Nat → Nat) (k0 n : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) (nat_lit 0) (fun j acc => Nat.add acc (f (Nat.add k0 j))) n

theorem chkSum_zero (f : Nat → Nat) (k0 : Nat) : ∀ n, chkSum f k0 n = 0 → ∀ j, j < n → f (k0 + j) = 0
  | 0, _, j, hj => absurd hj (Nat.not_lt_zero _)
  | n + 1, h, j, hj => by
    have h' : chkSum f k0 n + f (k0 + n) = 0 := h
    rcases Nat.lt_or_ge j n with hl | hl
    · exact chkSum_zero f k0 n (by omega) j hl
    · rw [show j = n by omega]; omega

/-- The packed mask `topMask W c` in every one of the `2^D` lanes. -/
def maskV (D W c : Nat) : Nat :=
  Nat.mul (Nat.xor (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1))
      (Nat.sub (Nat.shiftLeft (nat_lit 1) c) (nat_lit 1)))
    (Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (Nat.mul W (Nat.shiftLeft (nat_lit 1) D))) (nat_lit 1))
      (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1)))

theorem maskV_eq (D W c : Nat) (hW : 0 < W) : maskV D W c = enc W (fun _ => topMask W c) (2 ^ D) := by
  show ((1 <<< W - 1) ^^^ (1 <<< c - 1)) * ((1 <<< (W * 1 <<< D) - 1) / (1 <<< W - 1)) = _
  simp only [Nat.one_shiftLeft]
  rw [enc_ones W hW, Nat.mul_comm, enc_mulc]
  apply enc_congr; intro m _
  simp [topMask]

theorem rec_eq (x z s : Nat) :
    Nat.rec (motive := fun _ => Nat) z (fun _ _ => s) x = if x = 0 then z else s := by
  cases x <;> rfl

/-- `z` if `c = 0`, else `f`. A definition (not an inline recursor) so that the kernel compares
the unrolled and structured forms argument by argument instead of reducing `c` symbolically. -/
def pickZ (c z f : Nat) : Nat := Nat.rec (motive := fun _ => Nat) z (fun _ _ => f) c

/-- Fast path with the overflow check: if every checked row has all lanes below `2^c`, the packed
result is exact; otherwise fall back to `main` (`W`-bit lanes with the proved width). -/
def fastV (D W c s A B k0 n : Nat) : Nat :=
  pickZ (chkSum (fun k => Nat.land (loopV D W A B k) (maskV D W c)) k0 n)
    (Nat.land (loopV D W A B D) (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1)))
    (main D s)

theorem fastV_eq (D W c s A B k0 n : Nat) (hd : 3 ≤ D)
    (hA : ∀ i, i < D → colV A i = permanentColumnOne D s i)
    (hB : ∀ i, i < D → colV B i = permanentColumnTwo D s i)
    (hW : 1 ≤ W) (hc : 3 * 2 ^ c ≤ 2 ^ W) (hcW : c ≤ W)
    (hrange : ∀ k, k < D → 2 ^ W ≤ 3 ^ k → k0 ≤ k ∧ k < k0 + n) :
    fastV D W c s A B k0 n = permanentSpec (genPermanentMatrix D s) := by
  unfold fastV pickZ
  rw [rec_eq]
  split
  · rename_i h0
    have hchk : ∀ k, k < D → 2 ^ W ≤ 3 ^ k → Nat.land (loopV D W A B k) (maskV D W c) = 0 := by
      intro k hk h3
      have := chkSum_zero _ k0 n h0 (k - k0) (by have := hrange k hk h3; omega)
      rwa [show k0 + (k - k0) = k by have := hrange k hk h3; omega] at this
    obtain ⟨h1, h2⟩ := loopV_eq D D s W c A B (maskV D W c) hd (Nat.le_refl D) hA hB hW hc hcW
      (maskV_eq D W c (by omega)) hchk D (Nat.le_refl D)
    exact final_eq D s W _ h1 h2
  · exact main_eq D s hd

/-- Without checks: valid when `3^(D-1) < 2^W`. -/
theorem plainV_eq (D W s A B : Nat) (hd : 3 ≤ D)
    (hA : ∀ i, i < D → colV A i = permanentColumnOne D s i)
    (hB : ∀ i, i < D → colV B i = permanentColumnTwo D s i)
    (hW2 : 2 ≤ W) (hW : 3 ^ (D - 1) < 2 ^ W) :
    Nat.land (loopV D W A B D) (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1))
      = permanentSpec (genPermanentMatrix D s) := by
  have h4 : 2 ^ 2 ≤ 2 ^ W := Nat.pow_le_pow_right (by decide) hW2
  obtain ⟨h1, h2⟩ := loopV_eq D D s W 0 A B (enc W (fun _ => topMask W 0) (2 ^ D)) hd (Nat.le_refl D) hA hB
    (by omega) (by simp at h4 ⊢; omega) (by omega) rfl
    (fun k hk h3 => absurd (Nat.lt_of_le_of_lt h3 (Nat.lt_of_le_of_lt
      (Nat.pow_le_pow_right (by decide) (by omega)) hW)) (Nat.lt_irrefl _)) D (Nat.le_refl D)
  exact final_eq D s W _ h1 h2

/-! ## Last row: only lane 0 of the result is needed, read the three source lanes directly -/

def lastRow (W G a b : Nat) : Nat :=
  Nat.add (Nat.add
      (Nat.shiftRight (Nat.land (Nat.sub (Nat.shiftLeft (nat_lit 1) (Nat.add W W)) (nat_lit 1)) G) W)
      (Nat.land (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1)) (Nat.shiftRight G (Nat.shiftLeft W a))))
    (Nat.land (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1)) (Nat.shiftRight G (Nat.shiftLeft W b)))

theorem lane_get (W L x : Nat) (f : Nat → Nat) (hx : x < L) (hf : ∀ m, m < L → f m < 2 ^ W) :
    Nat.land (Nat.sub (Nat.shiftLeft (nat_lit 1) W) (nat_lit 1)) (Nat.shiftRight (enc W f L) (W * x))
      = f x := by
  show (1 <<< W - 1) &&& (enc W f L >>> (W * x)) = _
  rw [Nat.one_shiftLeft, Nat.and_comm, Nat.and_two_pow_sub_one_eq_mod]
  exact enc_get W f L x hx hf

theorem lastRow_eq (W D a b : Nat) (f : Nat → Nat) (hD : 1 ≤ D) (ha : a < D) (hb : b < D)
    (hf : ∀ m, m < 2 ^ D → f m < 2 ^ W) :
    lastRow W (enc W f (2 ^ D)) a b = f 1 + f (2 ^ a) + f (2 ^ b) := by
  have h2 : 2 ≤ 2 ^ D := by
    calc 2 = 2 ^ 1 := rfl
      _ ≤ 2 ^ D := Nat.pow_le_pow_right (by decide) hD
  have hxa : 2 ^ a < 2 ^ D := Nat.pow_lt_pow_right (by decide) ha
  have hxb : 2 ^ b < 2 ^ D := Nat.pow_lt_pow_right (by decide) hb
  have e1 : Nat.shiftRight (Nat.land (Nat.sub (Nat.shiftLeft (nat_lit 1) (Nat.add W W)) (nat_lit 1))
      (enc W f (2 ^ D))) W = f 1 := by
    show ((1 <<< (W + W) - 1) &&& enc W f (2 ^ D)) >>> W = _
    rw [Nat.one_shiftLeft, Nat.and_comm, Nat.and_two_pow_sub_one_eq_mod,
      show 2 ^ D = 2 + (2 ^ D - 2) by omega, show W + W = W * 2 by omega,
      enc_low W f 2 _ (fun m hm => hf m (by omega))]
    have := enc_shiftRight W f 1 2 (by omega) (fun m hm => hf m (by omega))
    rw [Nat.mul_one] at this
    rw [this]
    simp [enc]
  have ea : Nat.shiftLeft W a = W * 2 ^ a := Nat.shiftLeft_eq W a
  have eb : Nat.shiftLeft W b = W * 2 ^ b := Nat.shiftLeft_eq W b
  unfold lastRow
  rw [e1, ea, eb, lane_get W _ _ f hxa hf, lane_get W _ _ f hxb hf]
  rfl

theorem hl_last (D seed : Nat) (hd : 3 ≤ D) :
    hl D seed D 0 = hl D seed (D - 1) 1 + hl D seed (D - 1) (2 ^ permanentColumnOne D seed 0)
      + hl D seed (D - 1) (2 ^ permanentColumnTwo D seed 0) := by
  obtain ⟨k, rfl⟩ : ∃ k, D = k + 1 := ⟨D - 1, by omega⟩
  have c1 := col1_facts (k + 1) seed 0 hd (by omega)
  have c2 := col2_facts (k + 1) seed 0 hd (by omega)
  have hs : supp (k + 1) seed (k + 1 - 1 - k) = [0, permanentColumnOne (k + 1) seed 0,
      permanentColumnTwo (k + 1) seed 0] := by
    rw [show k + 1 - 1 - k = 0 by omega]; unfold supp; rw [if_neg (by omega)]
  rw [hl_succ, hs, show k + 1 - 1 = k by omega]
  have h1 : 2 ^ 0 + 0 < 2 ^ (k + 1) := by
    rw [Nat.pow_zero, Nat.add_zero]; exact Nat.one_lt_two_pow (by omega)
  have ha : 2 ^ permanentColumnOne (k + 1) seed 0 + 0 < 2 ^ (k + 1) := by
    rw [Nat.add_zero]; exact Nat.pow_lt_pow_right (by decide) c1.1
  have hb : 2 ^ permanentColumnTwo (k + 1) seed 0 + 0 < 2 ^ (k + 1) := by
    rw [Nat.add_zero]; exact Nat.pow_lt_pow_right (by decide) c2.1
  simp only [List.map_cons, List.map_nil, List.sum_cons, List.sum_nil, if_pos h1, if_pos ha, if_pos hb]
  rw [Nat.pow_zero, Nat.add_zero 1, Nat.add_zero (2 ^ permanentColumnOne (k + 1) seed 0),
    Nat.add_zero (2 ^ permanentColumnTwo (k + 1) seed 0),
    Nat.add_zero (hl (k + 1) seed k (2 ^ permanentColumnTwo (k + 1) seed 0)), Nat.add_assoc]

theorem spec_of_hl (D seed : Nat) :
    hl D seed D 0 = permanentSpec (genPermanentMatrix D seed) := by
  have h0 := hl_correct D seed D (Nat.le_refl D) 0 (Nat.two_pow_pos D) (by rw [pc_zero]; omega)
  rw [pc_zero, Nat.sub_self, if_pos rfl] at h0
  rw [h0]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows D (M D seed) 0 = permanentRows (M D seed).length (M D seed) 0
  rw [M_length]

theorem mod72_colV0 (X : Nat) : Nat.mod X (nat_lit 4722366482869645213696) = colV X 0 := by
  show X % 2 ^ 72 = (X >>> (72 * 0)) % 2 ^ 72
  simp

/-- Checked fast path whose last row only reads the three lanes that feed lane `0`. -/
def fastL (D W c s A B k0 n : Nat) : Nat :=
  pickZ (chkSum (fun k => Nat.land (loopV D W A B k) (maskV D W c)) k0 n)
    (lastRow W (loopV D W A B (Nat.sub D (nat_lit 1)))
      (Nat.mod A (nat_lit 4722366482869645213696)) (Nat.mod B (nat_lit 4722366482869645213696)))
    (main D s)

theorem fastL_eq (D W c s A B k0 n : Nat) (hd : 3 ≤ D)
    (hA : ∀ i, i < D → colV A i = permanentColumnOne D s i)
    (hB : ∀ i, i < D → colV B i = permanentColumnTwo D s i)
    (hW : 1 ≤ W) (hc : 3 * 2 ^ c ≤ 2 ^ W) (hcW : c ≤ W)
    (hrange : ∀ k, k < D - 1 → 2 ^ W ≤ 3 ^ k → k0 ≤ k ∧ k < k0 + n) :
    fastL D W c s A B k0 n = permanentSpec (genPermanentMatrix D s) := by
  unfold fastL pickZ
  rw [rec_eq]
  split
  · rename_i h0
    have hchk : ∀ k, k < D - 1 → 2 ^ W ≤ 3 ^ k →
        Nat.land (loopV D W A B k) (maskV D W c) = 0 := by
      intro k hk h3
      have := chkSum_zero _ k0 n h0 (k - k0) (by have := hrange k hk h3; omega)
      rwa [show k0 + (k - k0) = k by have := hrange k hk h3; omega] at this
    obtain ⟨h1, h2⟩ := loopV_eq D (D - 1) s W c A B (maskV D W c) hd (by omega) hA hB hW hc hcW
      (maskV_eq D W c (by omega)) hchk (D - 1) (Nat.le_refl _)
    have c1 := col1_facts D s 0 hd (by omega)
    have c2 := col2_facts D s 0 hd (by omega)
    rw [show Nat.sub D (nat_lit 1) = D - 1 from rfl, h1, mod72_colV0 A, mod72_colV0 B, hA 0 (by omega),
      hB 0 (by omega),
      lastRow_eq W D _ _ _ (by omega) c1.1 c2.1 h2, ← hl_last D s hd, spec_of_hl D s]
  · exact main_eq D s hd

/-! ## Relabeled columns: column `j` is lane-index bit `lam j` -/

section Relabel

variable (d seed : Nat) (lam : Nat → Nat)

/-- Lane values of the relabeled backward DP (no masks). -/
def hlR : Nat → Nat → Nat
  | 0, m => if m = 2 ^ d - 1 then 1 else 0
  | k + 1, m => ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ lam j + m < 2 ^ d then hlR k (2 ^ lam j + m) else 0)).sum

/-- Ways to finish the last `n` rows when the labels in `m` are taken. -/
def gsR : Nat → Nat → Nat
  | 0, _ => 1
  | n + 1, m => ((supp d seed (d - 1 - n)).map
      (fun j => if m.testBit (lam j) then 0 else gsR n (2 ^ lam j + m))).sum

/-- Label mask of the columns `c < n` set in `m`. -/
def relab (m : Nat) : Nat → Nat
  | 0 => 0
  | c + 1 => relab m c + (if m.testBit c then 2 ^ lam c else 0)

end Relabel

theorem testBit_two_pow_add (x i p : Nat) (hx : x.testBit i = false) :
    (2 ^ i + x).testBit p = (x.testBit p || decide (p = i)) := by
  rw [add_eq_or x i hx, Nat.testBit_or, Nat.one_shiftLeft, Nat.testBit_two_pow]
  by_cases h : p = i
  · subst h; simp
  · simp [h, Ne.symm h]

theorem relab_tb_false (lam : Nat → Nat) (m : Nat) (n : Nat)
    (hinj : ∀ a b, a < n → b < n → lam a = lam b → a = b) :
    ∀ p, (∀ c, c < n → m.testBit c = true → lam c ≠ p) → (relab lam m n).testBit p = false := by
  induction n with
  | zero => intro p _; simp [relab]
  | succ n ih =>
    intro p hp
    have ih' := ih (fun a b ha hb h => hinj a b (by omega) (by omega) h)
    simp only [relab]
    by_cases hb : m.testBit n = true
    · rw [if_pos hb]
      have hfree : (relab lam m n).testBit (lam n) = false :=
        ih' (lam n) (fun c hc hmc h => by have := hinj c n (by omega) (by omega) h; omega)
      rw [Nat.add_comm, testBit_two_pow_add _ _ _ hfree, ih' p (fun c hc hmc => hp c (by omega) hmc)]
      have := hp n (by omega) hb
      simp [Ne.symm this]
    · rw [if_neg hb, Nat.add_zero]
      exact ih' p (fun c hc hmc => hp c (by omega) hmc)

theorem relab_tb_true (lam : Nat → Nat) (m : Nat) (n : Nat)
    (hinj : ∀ a b, a < n → b < n → lam a = lam b → a = b) :
    ∀ c, c < n → m.testBit c = true → (relab lam m n).testBit (lam c) = true := by
  induction n with
  | zero => intro c hc; omega
  | succ n ih =>
    intro c hc hmc
    have ih' := ih (fun a b ha hb h => hinj a b (by omega) (by omega) h)
    simp only [relab]
    by_cases hb : m.testBit n = true
    · rw [if_pos hb]
      have hfree : (relab lam m n).testBit (lam n) = false :=
        relab_tb_false lam m n (fun a b ha hb h => hinj a b (by omega) (by omega) h) (lam n)
          (fun c' hc' _ h => by have := hinj c' n (by omega) (by omega) h; omega)
      rw [Nat.add_comm, testBit_two_pow_add _ _ _ hfree]
      by_cases hcn : c = n
      · subst hcn; simp
      · rw [ih' c (by omega) hmc]; simp
    · rw [if_neg hb, Nat.add_zero]
      have hcn : c ≠ n := fun h => by subst h; exact hb hmc
      exact ih' c (by omega) hmc

theorem relab_tb (lam : Nat → Nat) (m n : Nat)
    (hinj : ∀ a b, a < n → b < n → lam a = lam b → a = b) (j : Nat) (hj : j < n) :
    (relab lam m n).testBit (lam j) = m.testBit j := by
  cases h : m.testBit j
  · exact relab_tb_false lam m n hinj (lam j) (fun c hc hmc he => by
      have := hinj c j hc hj he; subst this; rw [h] at hmc; exact Bool.false_ne_true hmc)
  · exact relab_tb_true lam m n hinj j hj h

theorem relab_add (lam : Nat → Nat) (m j : Nat) (hm : m.testBit j = false) :
    ∀ n, relab lam (2 ^ j + m) n = relab lam m n + (if j < n then 2 ^ lam j else 0)
  | 0 => by simp [relab]
  | n + 1 => by
    simp only [relab]
    rw [relab_add lam m j hm n, testBit_two_pow_add _ _ _ hm]
    by_cases hn : n = j
    · subst hn
      simp [hm]
    · have : (j < n + 1) = (j < n) := by apply propext; omega
      simp only [hn, decide_false, Bool.or_false, this]
      split <;> split <;> omega

theorem relab_zero (lam : Nat → Nat) : ∀ n, relab lam 0 n = 0
  | 0 => rfl
  | n + 1 => by simp [relab, relab_zero lam n]

theorem gsR_relab (d seed : Nat) (lam : Nat → Nat)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b) :
    ∀ n, n ≤ d → ∀ m, m < 2 ^ d → gsR d seed lam n (relab lam m d) = gs d seed (d - n) m
  | 0, _, m, _ => by rw [Nat.sub_zero, gs_top]; rfl
  | n + 1, hn, m, hm => by
    have hi : d - 1 - n < d := by omega
    rw [show d - (n + 1) = d - 1 - n by omega, gs_step d seed _ m hi]
    simp only [gsR]
    apply sum_map_congr
    intro j hj
    have hjd := supp_lt d seed _ hi j hj
    rw [relab_tb lam m d hinj j hjd]
    cases hb : m.testBit j
    · simp only [Bool.false_eq_true, ↓reduceIte]
      have hlt : 2 ^ j + m < 2 ^ d := by
        rw [add_eq_or m j hb, Nat.one_shiftLeft]
        exact Nat.or_lt_two_pow hm (Nat.pow_lt_pow_right (by omega) hjd)
      have e := relab_add lam m j hb d
      rw [if_pos hjd] at e
      rw [Nat.add_comm (2 ^ lam j), ← e, gsR_relab d seed lam hinj n (by omega) _ hlt,
        show d - n = d - 1 - n + 1 by omega]
    · rfl

theorem hlR_correct (d seed : Nat) (lam : Nat → Nat) (hlam : ∀ j, j < d → lam j < d) :
    ∀ k, k ≤ d → ∀ m, m < 2 ^ d → pc m ≤ d - k →
      hlR d seed lam k m = if pc m = d - k then gsR d seed lam k m else 0
  | 0, _, m, hm, _ => by
    simp only [hlR, gsR, Nat.sub_zero]
    have := (pc_le d m hm).2
    by_cases h : m = 2 ^ d - 1
    · rw [if_pos h, if_pos (this.mpr h)]
    · rw [if_neg h, if_neg (fun h' => h (this.mp h'))]
  | k + 1, hk, m, hm, hp => by
    have hi : d - 1 - k < d := by omega
    simp only [hlR, gsR]
    rw [← sum_map_ite]
    apply sum_map_congr
    intro j hj
    have hjd := hlam j (supp_lt d seed _ hi j hj)
    cases hb : m.testBit (lam j)
    · have hpc := pc_clear (lam j) m hb
      have hlt : 2 ^ lam j + m < 2 ^ d := by
        rw [add_eq_or m (lam j) hb, Nat.one_shiftLeft]
        exact Nat.or_lt_two_pow hm (Nat.pow_lt_pow_right (by omega) hjd)
      rw [if_pos hlt, hlR_correct d seed lam hlam k (by omega) _ hlt (by omega)]
      simp only [Bool.false_eq_true, ↓reduceIte]
      by_cases hc : pc m = d - (k + 1)
      · rw [if_pos (by omega), if_pos hc]
      · rw [if_neg (by omega), if_neg hc]
    · have hpc := pc_set (lam j) m hb
      simp only [↓reduceIte, ite_self]
      split
      · rename_i hlt
        rw [hlR_correct d seed lam hlam k (by omega) _ hlt (by omega), if_neg (by omega)]
      · rfl

theorem hlR_final (d seed : Nat) (lam : Nat → Nat) (hlam : ∀ j, j < d → lam j < d)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b) :
    hlR d seed lam d 0 = permanentSpec (genPermanentMatrix d seed) := by
  rw [hlR_correct d seed lam hlam d (Nat.le_refl d) 0 (Nat.two_pow_pos d) (by rw [pc_zero]; omega),
    pc_zero, Nat.sub_self, if_pos rfl, ← relab_zero lam d,
    gsR_relab d seed lam hinj d (Nat.le_refl d) 0 (Nat.two_pow_pos d), Nat.sub_self]
  unfold gs permanentSpec
  rw [List.drop_zero]
  show permanentRows d (M d seed) 0 = permanentRows (M d seed).length (M d seed) 0
  rw [M_length]

/-! ## Trimming: lanes above a bound are dropped -/

section Trim

variable (d seed : Nat) (lam bnd : Nat → Nat)

/-- The relabeled DP where, on reaching level `k`, lanes `m ≥ bnd k` are cleared. -/
def hlT : Nat → Nat → Nat
  | 0, m => if m < bnd 0 then hlR d seed lam 0 m else 0
  | k + 1, m => if m < bnd (k + 1) then ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ lam j + m < 2 ^ d then hlT k (2 ^ lam j + m) else 0)).sum else 0

/-- `m` only uses labels of columns of the rows `r` with `r + k < d` (those still to come at
level `k`). -/
def inU (k m : Nat) : Prop :=
  ∀ p, m.testBit p = true → ∃ r, r + k < d ∧ ∃ j, j ∈ supp d seed r ∧ lam j = p

end Trim

theorem hlT_succ_eq (d seed : Nat) (lam bnd : Nat → Nat) (k m : Nat) :
    hlT d seed lam bnd (k + 1) m = if m < bnd (k + 1) then ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ lam j + m < 2 ^ d then hlT d seed lam bnd k (2 ^ lam j + m) else 0)).sum
      else 0 := rfl

theorem hlT_succ_zero (d seed : Nat) (lam bnd : Nat → Nat) (k : Nat) :
    hlT d seed lam bnd (k + 1) 0 = if 0 < bnd (k + 1) then ((supp d seed (d - 1 - k)).map
      (fun j => if 2 ^ lam j < 2 ^ d then hlT d seed lam bnd k (2 ^ lam j) else 0)).sum else 0 := by
  rw [hlT_succ_eq]; simp only [Nat.add_zero]

theorem sum_map_mono (f g : Nat → Nat) : ∀ l : List Nat, (∀ j, j ∈ l → f j ≤ g j) →
    (l.map f).sum ≤ (l.map g).sum
  | [], _ => Nat.le_refl _
  | j :: l, h => by
    simp only [List.map_cons, List.sum_cons]
    exact Nat.add_le_add (h j (by simp)) (sum_map_mono f g l (fun x hx => h x (by simp [hx])))

theorem hlT_le (d seed : Nat) (lam bnd : Nat → Nat) :
    ∀ k m, hlT d seed lam bnd k m ≤ hlR d seed lam k m
  | 0, m => by simp only [hlT]; split <;> omega
  | k + 1, m => by
    simp only [hlT, hlR]
    split
    · apply sum_map_mono
      intro j _
      split
      · exact hlT_le d seed lam bnd k _
      · exact Nat.le_refl _
    · exact Nat.zero_le _

theorem hlT_eq (d seed : Nat) (lam bnd : Nat → Nat) (hlam : ∀ j, j < d → lam j < d)
    (hbnd : ∀ k, k ≤ d → ∀ m, m < 2 ^ d → inU d seed lam k m → m < bnd k) :
    ∀ k, k ≤ d → ∀ m, m < 2 ^ d → inU d seed lam k m → pc m ≤ d - k →
      hlT d seed lam bnd k m = hlR d seed lam k m
  | 0, _, m, hm, hu, _ => by
    simp only [hlT]; rw [if_pos (hbnd 0 (Nat.zero_le _) m hm hu)]
  | k + 1, hk, m, hm, hu, hp => by
    simp only [hlT, hlR]
    rw [if_pos (hbnd (k + 1) hk m hm hu)]
    apply sum_map_congr
    intro j hj
    have hi : d - 1 - k < d := by omega
    have hjd := hlam j (supp_lt d seed _ hi j hj)
    split
    · rename_i hlt
      cases hb : m.testBit (lam j)
      · have hpc := pc_clear (lam j) m hb
        apply hlT_eq d seed lam bnd hlam hbnd k (by omega) _ hlt _ (by omega)
        intro p hpb
        rw [testBit_two_pow_add _ _ _ hb] at hpb
        by_cases hpj : p = lam j
        · exact ⟨d - 1 - k, by omega, j, hj, hpj.symm⟩
        · have : m.testBit p = true := by simpa [hpj] using hpb
          obtain ⟨r, hr, j', hj', he⟩ := hu p this
          exact ⟨r, by omega, j', hj', he⟩
      · have hpc := pc_set (lam j) m hb
        have h0 : hlR d seed lam k (2 ^ lam j + m) = 0 := by
          rw [hlR_correct d seed lam hlam k (by omega) _ hlt (by omega), if_neg (by omega)]
        have := hlT_le d seed lam bnd k (2 ^ lam j + m)
        omega
    · rfl

theorem hlT_final (d seed : Nat) (lam bnd : Nat → Nat) (hlam : ∀ j, j < d → lam j < d)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b)
    (hbnd : ∀ k, k ≤ d → ∀ m, m < 2 ^ d → inU d seed lam k m → m < bnd k) :
    hlT d seed lam bnd d 0 = permanentSpec (genPermanentMatrix d seed) := by
  rw [hlT_eq d seed lam bnd hlam hbnd d (Nat.le_refl d) 0 (Nat.two_pow_pos d)
    (fun p hp => by simp at hp) (by rw [pc_zero]; omega), hlR_final d seed lam hlam hinj]

/-! ## Lane bounds of the relabeled DP -/

theorem hlR_one_bound (d seed : Nat) (lam : Nat → Nat) (hd : 3 ≤ d)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b) (m : Nat) :
    hlR d seed lam 1 m ≤ 1 := by
  have c1 := col1_facts d seed (d - 1) hd (by omega)
  have c2 := col2_facts d seed (d - 1) hd (by omega)
  have hne : ∀ a b, a < d → b < d → a ≠ b → 2 ^ lam a ≠ 2 ^ lam b := fun a b ha hb hab h =>
    hab (hinj a b ha hb ((Nat.pow_right_inj (by decide : 1 < 2)).mp h))
  have hs : supp d seed (d - 1) = [d - 1, permanentColumnOne d seed (d - 1),
      permanentColumnTwo d seed (d - 1)] := by
    unfold supp; rw [if_neg (by omega : ¬d < 3)]
  change ((supp d seed (d - 1 - 0)).map (fun j => if 2 ^ lam j + m < 2 ^ d then
    (if 2 ^ lam j + m = 2 ^ d - 1 then 1 else 0) else 0)).sum ≤ 1
  rw [Nat.sub_zero, hs]
  exact three_distinct_indicators _ _ _ m (2 ^ d) (hne _ _ (by omega) c1.1 (by omega))
    (hne _ _ (by omega) c2.1 (by omega)) (hne _ _ c1.1 c2.1 (by omega))

theorem hlR_bound_tight (d seed : Nat) (lam : Nat → Nat) (hd : 3 ≤ d)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b) :
    ∀ k m, hlR d seed lam k m ≤ 3 ^ (k - 1)
  | 0, m => by simp only [hlR]; split <;> simp
  | 1, m => by simpa using hlR_one_bound d seed lam hd hinj m
  | k + 2, m => by
    change ((supp d seed (d - 1 - (k + 1))).map (fun j => if 2 ^ lam j + m < 2 ^ d then
      hlR d seed lam (k + 1) (2 ^ lam j + m) else 0)).sum ≤ 3 ^ (k + 1)
    have h1 := sum_map_le (fun j => if 2 ^ lam j + m < 2 ^ d then
      hlR d seed lam (k + 1) (2 ^ lam j + m) else 0) (3 ^ k) (supp d seed (d - 1 - (k + 1)))
      (fun j _ => by
        show (if 2 ^ lam j + m < 2 ^ d then hlR d seed lam (k + 1) (2 ^ lam j + m) else 0) ≤ 3 ^ k
        split
        · simpa using hlR_bound_tight d seed lam hd hinj (k + 1) _
        · exact Nat.zero_le _)
    have h2 := Nat.mul_le_mul_right (3 ^ k) (supp_length d seed (d - 1 - (k + 1)))
    simpa only [Nat.pow_succ, Nat.mul_comm] using Nat.le_trans h1 h2

theorem hlT_step_bound (d seed : Nat) (lam bnd : Nat → Nat) (k b : Nat)
    (hb : ∀ m, m < 2 ^ d → hlT d seed lam bnd k m ≤ b) :
    ∀ m, hlT d seed lam bnd (k + 1) m ≤ 3 * b := by
  intro m
  simp only [hlT]
  split
  · have h1 := sum_map_le (fun j => if 2 ^ lam j + m < 2 ^ d then
      hlT d seed lam bnd k (2 ^ lam j + m) else 0) b (supp d seed (d - 1 - k)) (fun j _ => by
        show (if 2 ^ lam j + m < 2 ^ d then hlT d seed lam bnd k (2 ^ lam j + m) else 0) ≤ b
        split
        · exact hb _ (by assumption)
        · exact Nat.zero_le _)
    have h2 := Nat.mul_le_mul_right b (supp_length d seed (d - 1 - k))
    omega
  · exact Nat.zero_le _

theorem sum_map_zero (f : Nat → Nat) : ∀ l : List Nat, (∀ j, j ∈ l → f j = 0) → (l.map f).sum = 0
  | [], _ => rfl
  | j :: l, h => by
    simp only [List.map_cons, List.sum_cons]
    rw [h j (by simp), sum_map_zero f l (fun x hx => h x (by simp [hx]))]

/-- Once lanes `m ≥ b` are empty they stay empty: rows only move lanes down. -/
theorem hlT_high_zero (d seed : Nat) (lam bnd : Nat → Nat) (b k0 : Nat)
    (h0 : ∀ m, b ≤ m → hlT d seed lam bnd k0 m = 0) :
    ∀ t m, b ≤ m → hlT d seed lam bnd (k0 + t) m = 0
  | 0, m, hm => h0 m hm
  | t + 1, m, hm => by
    show hlT d seed lam bnd (k0 + t + 1) m = 0
    simp only [hlT]
    split
    · apply sum_map_zero
      intro j _
      split
      · exact hlT_high_zero d seed lam bnd b k0 h0 t _ (Nat.le_trans hm (Nat.le_add_left m _))
      · rfl
    · rfl

/-! ## Packed rows with relabeled shifts, and trimming -/

def stepR (G a b c : Nat) : Nat :=
  Nat.add (Nat.add (Nat.shiftRight G a) (Nat.shiftRight G b)) (Nat.shiftRight G c)

theorem enc_trim (W L b : Nat) (f : Nat → Nat) (hb : b ≤ L) (hf : ∀ m, m < L → f m < 2 ^ W) :
    Nat.land (enc W f L) (2 ^ (W * b) - 1) = enc W (fun m => if m < b then f m else 0) L := by
  show enc W f L &&& (2 ^ (W * b) - 1) = _
  rw [Nat.and_two_pow_sub_one_eq_mod]
  obtain ⟨t, rfl⟩ : ∃ t, L = b + t := ⟨L - b, by omega⟩
  rw [enc_low W f b t hf, enc_pad W f b (b + t) (by omega)]

theorem stepR_eq (W d : Nat) (g : Nat → Nat) (pa pb pc : Nat) (ha : pa < d) (hb : pb < d)
    (hc : pc < d) (hg : ∀ m, m < 2 ^ d → g m < 2 ^ W) :
    stepR (enc W g (2 ^ d)) (W * 2 ^ pa) (W * 2 ^ pb) (W * 2 ^ pc)
      = enc W (fun m => ([pa, pb, pc].map
          (fun p => if 2 ^ p + m < 2 ^ d then g (2 ^ p + m) else 0)).sum) (2 ^ d) := by
  rw [← Nat.shiftLeft_eq, ← Nat.shiftLeft_eq, ← Nat.shiftLeft_eq]
  show sh W (enc W g (2 ^ d)) pa + sh W (enc W g (2 ^ d)) pb + sh W (enc W g (2 ^ d)) pc = _
  rw [enc_sh W d pa g ha hg, enc_sh W d pb g hb hg, enc_sh W d pc g hc hg, ← enc_add, ← enc_add]
  apply enc_congr; intro m _
  simp only [List.map_cons, List.map_nil, List.sum_cons, List.sum_nil]
  omega

theorem stepR_lam (W d : Nat) (g lam : Nat → Nat) (i a b : Nat) (hi : lam i < d) (ha : lam a < d)
    (hb : lam b < d) (hg : ∀ m, m < 2 ^ d → g m < 2 ^ W) :
    stepR (enc W g (2 ^ d)) (W * 2 ^ lam i) (W * 2 ^ lam a) (W * 2 ^ lam b)
      = enc W (fun m => ([i, a, b].map
          (fun j => if 2 ^ lam j + m < 2 ^ d then g (2 ^ lam j + m) else 0)).sum) (2 ^ d) := by
  rw [stepR_eq W d g _ _ _ hi ha hb hg]
  apply enc_congr; intro m _
  simp only [List.map_cons, List.map_nil]

theorem ones_shr (a b : Nat) (h : b ≤ a) : (2 ^ a - 1) >>> (a - b) = 2 ^ b - 1 := by
  apply Nat.eq_of_testBit_eq; intro i
  rw [Nat.testBit_shiftRight, Nat.testBit_two_pow_sub_one, Nat.testBit_two_pow_sub_one]
  simp only [decide_eq_decide]; omega

/-! ## Labels: a 32-bit-lane table, its lane-wise exponentiation, gathers -/

/-- Lane `c` (32 bits) of `x`. -/
def lane32 (x c : Nat) : Nat := (x >>> (32 * c)) % 2 ^ 32

theorem digits_enc (V x : Nat) : ∀ L, x % 2 ^ (V * L) = enc V (fun c => (x >>> (V * c)) % 2 ^ V) L
  | 0 => by simp [enc, Nat.mod_one]
  | L + 1 => by
    simp only [enc]
    rw [← digits_enc V x L, show V * (L + 1) = V * L + V by rw [Nat.mul_succ], Nat.pow_add,
      Nat.mod_mul, Nat.shiftRight_eq_div_pow, Nat.mul_comm (2 ^ (V * L))]

def ONES32 : Nat := nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041

theorem ONES32_eq : ONES32 = enc 32 (fun _ => 1) 16 := by decide +kernel

theorem ONES32_lt : ONES32 < 2 ^ (32 * 16) := by decide +kernel

theorem land_mod_of_lt (x y n : Nat) (hy : y < 2 ^ n) : x &&& y = (x % 2 ^ n) &&& y := by
  apply Nat.eq_of_testBit_eq; intro i
  rw [Nat.testBit_and, Nat.testBit_and, Nat.testBit_mod_two_pow]
  by_cases hi : i < n
  · simp [hi]
  · have : y.testBit i = false := Nat.testBit_lt_two_pow
      (Nat.lt_of_lt_of_le hy (Nat.pow_le_pow_right (by omega) (by omega)))
    simp [this]

set_option exponentiation.threshold 1000 in
theorem bit_lanes (Λ b : Nat) (hb : b < 32) :
    Nat.land (Nat.shiftRight Λ b) ONES32 = enc 32 (fun c => (lane32 Λ c >>> b) % 2) 16 := by
  show (Λ >>> b) &&& ONES32 = _
  rw [land_mod_of_lt _ _ _ ONES32_lt, digits_enc, ONES32_eq,
    enc_and 32 (by decide) _ _ 16 (fun c _ => Nat.mod_lt _ (Nat.two_pow_pos _))
      (fun c _ => by decide)]
  apply enc_congr; intro c _
  unfold lane32
  rw [Nat.and_one_is_mod, Nat.mod_mod_of_dvd _ (by decide : 2 ∣ 2 ^ 32), Nat.shiftRight_eq_div_pow,
    Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow]
  have e1 : 2 ^ 32 = 2 ^ b * 2 ^ (32 - b) := by rw [← Nat.pow_add]; congr 1; omega
  rw [e1, Nat.mod_mul_right_div_self, Nat.mod_mod_of_dvd _ (Nat.pow_dvd_pow_iff_le_right'.mpr
    (by omega : 1 ≤ 32 - b) |> fun h => by simpa using h), Nat.div_div_eq_div_mul,
    Nat.div_div_eq_div_mul, Nat.mul_comm (2 ^ b)]

/-- Lane value after the first `b` doubling steps: `12 · 2^(x mod 2^b)`. -/
def ev (b x : Nat) : Nat := 12 * 2 ^ (x % 2 ^ b)

def expStep (V K b Λ : Nat) : Nat :=
  Nat.add V (Nat.land (Nat.mul V K) (Nat.mul (Nat.land (Nat.shiftRight Λ b) ONES32)
    (nat_lit 4294967295)))

theorem ev_succ (b x : Nat) :
    ev b x + ((ev b x * (2 ^ 2 ^ b - 1)) &&& ((x >>> b) % 2 * 4294967295)) = ev (b + 1) x
      ∨ ev b x * (2 ^ 2 ^ b - 1) ≥ 2 ^ 32 := by
  rcases Nat.lt_or_ge (ev b x * (2 ^ 2 ^ b - 1)) (2 ^ 32) with h | h
  · left
    have hm : x % 2 ^ (b + 1) = x % 2 ^ b + 2 ^ b * (x / 2 ^ b % 2) := Nat.mod_pow_succ
    rw [Nat.shiftRight_eq_div_pow]
    unfold ev at h ⊢
    rcases Nat.mod_two_eq_zero_or_one (x / 2 ^ b) with h2 | h2
    · rw [h2, Nat.zero_mul, Nat.and_zero, Nat.add_zero, hm, h2, Nat.mul_zero, Nat.add_zero]
    · rw [h2, Nat.one_mul, show (4294967295 : Nat) = 2 ^ 32 - 1 from rfl,
        Nat.and_two_pow_sub_one_eq_mod, Nat.mod_eq_of_lt h, hm, h2, Nat.mul_one, Nat.pow_add]
      have : 1 ≤ 2 ^ 2 ^ b := Nat.one_le_two_pow
      rw [Nat.mul_sub, Nat.mul_one, Nat.mul_assoc]
      have : 12 * 2 ^ (x % 2 ^ b) ≤ 12 * (2 ^ (x % 2 ^ b) * 2 ^ 2 ^ b) := by
        apply Nat.mul_le_mul_left; exact Nat.le_mul_of_pos_right _ (Nat.two_pow_pos _)
      omega
  · right; exact h

theorem ev_small (b x : Nat) (hb : b < 4) : ev b x * (2 ^ 2 ^ b - 1) < 2 ^ 32 := by
  unfold ev
  have h1 : x % 2 ^ b < 2 ^ b := Nat.mod_lt _ (Nat.two_pow_pos _)
  have h2 : 2 ^ (x % 2 ^ b) ≤ 2 ^ (2 ^ b - 1) := Nat.pow_le_pow_right (by omega) (by omega)
  have h3 : 12 * 2 ^ (x % 2 ^ b) * (2 ^ 2 ^ b - 1) ≤ 12 * 2 ^ (2 ^ b - 1) * (2 ^ 2 ^ b - 1) :=
    Nat.mul_le_mul_right _ (Nat.mul_le_mul_left _ h2)
  have h4 : 12 * 2 ^ (2 ^ b - 1) * (2 ^ 2 ^ b - 1) < 2 ^ 32 := by
    rcases (show b = 0 ∨ b = 1 ∨ b = 2 ∨ b = 3 by omega) with h | h | h | h <;> subst h <;> decide
  omega

theorem expStep_eq (Λ b : Nat) (hb : b < 4) :
    expStep (enc 32 (fun c => ev b (lane32 Λ c)) 16) (2 ^ 2 ^ b - 1) b Λ
      = enc 32 (fun c => ev (b + 1) (lane32 Λ c)) 16 := by
  unfold expStep
  rw [bit_lanes Λ b (by omega), P_mulr, P_mulr,
    P_and 32 (by decide) _ _ 16 (fun c _ => ev_small b _ hb)
      (fun c _ => by
        rcases Nat.mod_two_eq_zero_or_one (lane32 Λ c >>> b) with h | h <;> rw [h] <;> decide),
    P_add]
  apply enc_congr; intro c _
  rcases ev_succ b (lane32 Λ c) with h | h
  · exact h
  · exact absurd h (Nat.not_le.mpr (ev_small b _ hb))

def WONES : Nat := nat_lit 37460982612513971470157213380706349134086337634640526531106620993411119411302191003441038211212465386719640271029778030066477280065844794600980492

theorem WONES_eq : WONES = enc 32 (fun _ => 12) 16 := by decide +kernel

/-- Lane-wise `12 · 2^(λ mod 16)` of a label table. -/
def expW (Λ : Nat) : Nat :=
  expStep (expStep (expStep (expStep WONES (nat_lit 1) (nat_lit 0) Λ) (nat_lit 3) (nat_lit 1) Λ)
    (nat_lit 15) (nat_lit 2) Λ) (nat_lit 255) (nat_lit 3) Λ

theorem expW_eq (Λ : Nat) : expW Λ = enc 32 (fun c => 12 * 2 ^ (lane32 Λ c % 16)) 16 := by
  have e0 : WONES = enc 32 (fun c => ev 0 (lane32 Λ c)) 16 := by
    rw [WONES_eq]; apply enc_congr; intro c _; simp [ev, Nat.mod_one]
  unfold expW
  rw [e0, show (nat_lit 1) = 2 ^ 2 ^ 0 - 1 from rfl, expStep_eq Λ 0 (by decide),
    show (nat_lit 3) = 2 ^ 2 ^ 1 - 1 from rfl, expStep_eq Λ 1 (by decide),
    show (nat_lit 15) = 2 ^ 2 ^ 2 - 1 from rfl, expStep_eq Λ 2 (by decide),
    show (nat_lit 255) = 2 ^ 2 ^ 3 - 1 from rfl, expStep_eq Λ 3 (by decide)]
  rfl

/-- Gather lane `x / 32` of a table. -/
def gat (Ls x : Nat) : Nat := Nat.mod (Nat.shiftRight Ls x) (nat_lit 4294967296)

theorem gat_eq (f : Nat → Nat) (a : Nat) (ha : a < 16) (hf : ∀ c, c < 16 → f c < 2 ^ 32) :
    gat (enc 32 f 16) (32 * a) = f a := by
  show (enc 32 f 16 >>> (32 * a)) % 2 ^ 32 = f a
  exact enc_get 32 f 16 a ha hf

/-! ## The relabeling is injective when the shift amounts sum right -/

def sumL (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => sumL f n + f n

theorem two_pow_mod_m1 (V : Nat) : ∀ L, 2 ^ (V * L) % (2 ^ V - 1) = 1 % (2 ^ V - 1)
  | 0 => by simp
  | L + 1 => by
    rw [show V * (L + 1) = V * L + V by rw [Nat.mul_succ], Nat.pow_add, Nat.mul_mod,
      two_pow_mod_m1 V L]
    have : 2 ^ V % (2 ^ V - 1) = 1 % (2 ^ V - 1) := by
      have h := Nat.one_le_two_pow (n := V)
      generalize hm : 2 ^ V - 1 = m
      rw [show 2 ^ V = m + 1 by omega, Nat.add_mod_left]
    rw [this, ← Nat.mul_mod, Nat.one_mul]

theorem enc_mod_m1 (V : Nat) (f : Nat → Nat) : ∀ L,
    enc V f L % (2 ^ V - 1) = sumL f L % (2 ^ V - 1)
  | 0 => rfl
  | L + 1 => by
    simp only [enc, sumL]
    rw [Nat.add_mod, enc_mod_m1 V f L, Nat.mul_mod, two_pow_mod_m1 V L, ← Nat.mul_mod,
      Nat.mul_one, ← Nat.add_mod]

theorem sumL_mul (f : Nat → Nat) (c : Nat) : ∀ n, sumL (fun i => c * f i) n = c * sumL f n
  | 0 => rfl
  | n + 1 => by simp only [sumL]; rw [sumL_mul f c n, Nat.mul_add]

theorem sumL_le (f : Nat → Nat) (b : Nat) : ∀ n, (∀ i, i < n → f i ≤ b) → sumL f n ≤ n * b
  | 0, _ => Nat.zero_le _
  | n + 1, h => by
    simp only [sumL]
    have := sumL_le f b n (fun i hi => h i (by omega))
    have := h n (by omega)
    rw [Nat.succ_mul]; omega

theorem relab_full (lam : Nat → Nat) (m : Nat) : ∀ n, (∀ c, c < n → m.testBit c = true) →
    relab lam m n = sumL (fun c => 2 ^ lam c) n
  | 0, _ => rfl
  | n + 1, h => by
    simp only [relab, sumL]
    rw [relab_full lam m n (fun c hc => h c (by omega)), if_pos (h n (by omega))]

theorem relab_pc_le (lam : Nat → Nat) (m : Nat) : ∀ n, pc (relab lam m n) ≤ n
  | 0 => by simp [relab, pc]
  | n + 1 => by
    simp only [relab]
    have ih := relab_pc_le lam m n
    split
    · rw [Nat.add_comm]
      cases hb : (relab lam m n).testBit (lam n)
      · rw [pc_clear _ _ hb]; omega
      · have := pc_set _ _ hb; omega
    · rw [Nat.add_zero]; omega

theorem relab_inj_of_pc (lam : Nat → Nat) (m : Nat) : ∀ n, (∀ c, c < n → m.testBit c = true) →
    pc (relab lam m n) = n → ∀ a b, a < n → b < n → lam a = lam b → a = b
  | 0, _, _, a, _, ha, _, _ => absurd ha (Nat.not_lt_zero _)
  | n + 1, hm, hp, a, b, ha, hb, hab => by
    simp only [relab] at hp
    rw [if_pos (hm n (by omega)), Nat.add_comm] at hp
    have hle := relab_pc_le lam m n
    cases hbit : (relab lam m n).testBit (lam n)
    · rw [pc_clear _ _ hbit] at hp
      have ih := relab_inj_of_pc lam m n (fun c hc => hm c (by omega)) (by omega)
      have hfresh : ∀ c, c < n → lam c ≠ lam n := fun c hc he => by
        have := relab_tb_true lam m n ih c hc (hm c (by omega))
        rw [he, hbit] at this; exact Bool.false_ne_true this
      rcases Nat.lt_or_ge a n with h1 | h1 <;> rcases Nat.lt_or_ge b n with h2 | h2
      · exact ih a b h1 h2 hab
      · exact absurd (by rw [show b = n by omega] at hab; exact hab) (hfresh a h1)
      · exact absurd (by rw [show a = n by omega] at hab; exact hab.symm) (hfresh b h2)
      · omega
    · have := pc_set _ _ hbit; omega

/-! ## Trim bounds from the shift amounts (`12 · 2^λ` has bits `λ+2`, `λ+3`) -/

def yAcc (Ls A2 B2 : Nat) (R : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (Nat.lor (Nat.lor (gat Ls (Nat.mul (nat_lit 32) (nat_lit 0))) (gat Ls (colV A2 (nat_lit 0))))
      (gat Ls (colV B2 (nat_lit 0))))
    (fun r Y => Nat.lor (Nat.lor (Nat.lor Y (gat Ls (Nat.mul (nat_lit 32) (Nat.add r (nat_lit 1)))))
      (gat Ls (colV A2 (Nat.add r (nat_lit 1))))) (gat Ls (colV B2 (Nat.add r (nat_lit 1))))) R

def zB (Y : Nat) : Nat :=
  Nat.add (Nat.shiftRight (Nat.land Y (Nat.shiftRight Y (nat_lit 1))) (nat_lit 2)) (nat_lit 1)

def xB (Y : Nat) : Nat := Nat.mul (nat_lit 12) (zB Y)

theorem yAcc_succ (Ls A2 B2 r : Nat) : yAcc Ls A2 B2 (r + 1)
    = ((yAcc Ls A2 B2 r ||| gat Ls (32 * (r + 1))) ||| gat Ls (colV A2 (r + 1)))
      ||| gat Ls (colV B2 (r + 1)) := rfl

theorem yAcc_zero (Ls A2 B2 : Nat) : yAcc Ls A2 B2 0
    = (gat Ls (32 * 0) ||| gat Ls (colV A2 0)) ||| gat Ls (colV B2 0) := rfl

/-- Every bit of a row-`r` shift amount (`r ≤ R`) is a bit of `yAcc R`. -/
theorem yAcc_mem (Ls A2 B2 : Nat) : ∀ R r q, r ≤ R →
    ((gat Ls (32 * r)).testBit q = true ∨ (gat Ls (colV A2 r)).testBit q = true ∨
      (gat Ls (colV B2 r)).testBit q = true) → (yAcc Ls A2 B2 R).testBit q = true
  | 0, r, q, hr, h => by
    rw [show r = 0 by omega] at h
    rw [yAcc_zero, Nat.testBit_or, Nat.testBit_or]
    rcases h with h | h | h <;> simp [h]
  | R + 1, r, q, hr, h => by
    rw [yAcc_succ, Nat.testBit_or, Nat.testBit_or, Nat.testBit_or]
    rcases Nat.lt_or_ge r (R + 1) with h1 | h1
    · simp [yAcc_mem Ls A2 B2 R r q (by omega) h]
    · rw [show r = R + 1 by omega] at h
      rcases h with h | h | h <;> simp [h]

theorem yAcc_mono (Ls A2 B2 : Nat) : ∀ R t q, (yAcc Ls A2 B2 R).testBit q = true →
    (yAcc Ls A2 B2 (R + t)).testBit q = true
  | _, 0, _, h => h
  | R, t + 1, q, h => by
    rw [show R + (t + 1) = (R + t) + 1 by omega, yAcc_succ, Nat.testBit_or, Nat.testBit_or,
      Nat.testBit_or, yAcc_mono Ls A2 B2 R t q h]
    simp

theorem yAcc_lt (Ls A2 B2 : Nat) (R : Nat) (hv : ∀ r, r ≤ R → gat Ls (32 * r) < 2 ^ 19 ∧
    gat Ls (colV A2 r) < 2 ^ 19 ∧ gat Ls (colV B2 r) < 2 ^ 19) : yAcc Ls A2 B2 R < 2 ^ 19 := by
  induction R with
  | zero =>
    rw [yAcc_zero]
    obtain ⟨h1, h2, h3⟩ := hv 0 (Nat.le_refl 0)
    exact Nat.or_lt_two_pow (Nat.or_lt_two_pow h1 h2) h3
  | succ R ih =>
    rw [yAcc_succ]
    obtain ⟨h1, h2, h3⟩ := hv (R + 1) (Nat.le_refl _)
    exact Nat.or_lt_two_pow (Nat.or_lt_two_pow (Nat.or_lt_two_pow
      (ih (fun r hr => hv r (by omega))) h1) h2) h3

theorem testBit_12 (p q : Nat) : (12 * 2 ^ p).testBit q = (decide (q = p + 2) || decide (q = p + 3)) := by
  rw [Nat.testBit_mul_two_pow]
  have h12 : ∀ i, (12 : Nat).testBit i = (decide (i = 2) || decide (i = 3)) := by
    intro i
    rcases Nat.lt_or_ge i 4 with hi | hi
    · rcases (show i = 0 ∨ i = 1 ∨ i = 2 ∨ i = 3 by omega) with h | h | h | h <;> subst h <;> decide
    · rw [Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (by decide : (12 : Nat) < 2 ^ 4)
        (Nat.pow_le_pow_right (by omega) hi))]
      have e2 : ¬ i = 2 := by omega
      have e3 : ¬ i = 3 := by omega
      simp [e2, e3]
  rw [h12]
  by_cases h : p ≤ q
  · have e2 : (q - p = 2) = (q = p + 2) := propext ⟨fun _ => by omega, fun _ => by omega⟩
    have e3 : (q - p = 3) = (q = p + 3) := propext ⟨fun _ => by omega, fun _ => by omega⟩
    simp only [h, decide_true, Bool.true_and, e2, e3]
  · have e2 : ¬ q = p + 2 := by omega
    have e3 : ¬ q = p + 3 := by omega
    simp [h, e2, e3]

theorem zB_testBit (Y p : Nat) :
    ((Y &&& (Y >>> 1)) >>> 2).testBit p = (Y.testBit (p + 2) && Y.testBit (p + 3)) := by
  rw [Nat.testBit_shiftRight, Nat.testBit_and, Nat.testBit_shiftRight]
  rw [show 2 + p = p + 2 by omega, show 1 + (p + 2) = p + 3 by omega]

theorem zB_lt (Y : Nat) (hY : Y < 2 ^ 19) : zB Y ≤ 2 ^ 16 := by
  show (Y &&& (Y >>> 1)) >>> 2 + 1 ≤ 2 ^ 16
  have : (Y &&& (Y >>> 1)) >>> 2 < 2 ^ 16 := by
    apply Nat.lt_pow_two_of_testBit
    intro p hp
    rw [zB_testBit, Nat.testBit_lt_two_pow (x := Y) (i := p + 3)
      (Nat.lt_of_lt_of_le hY (Nat.pow_le_pow_right (by omega) (by omega)))]
    simp
  omega

theorem zB_mono (Y Y' : Nat) (h : ∀ q, Y.testBit q = true → Y'.testBit q = true) : zB Y ≤ zB Y' := by
  show (Y &&& (Y >>> 1)) >>> 2 + 1 ≤ (Y' &&& (Y' >>> 1)) >>> 2 + 1
  have : (Y &&& (Y >>> 1)) >>> 2 ≤ (Y' &&& (Y' >>> 1)) >>> 2 := by
    apply Nat.le_of_testBit
    intro p hp
    rw [zB_testBit] at hp ⊢
    simp only [Bool.and_eq_true] at hp ⊢
    exact ⟨h _ hp.1, h _ hp.2⟩
  omega

/-- Masks using only labels of rows `r ≤ R` lie below `zB (yAcc R)`. -/
theorem zB_bound (d seed : Nat) (lam : Nat → Nat) (Ls A2 B2 R k : Nat) (hRk : R + k + 1 = d)
    (hshift : ∀ r, r ≤ R → ∀ j, j ∈ supp d seed r →
      ((gat Ls (32 * r)) = 12 * 2 ^ lam j ∨ gat Ls (colV A2 r) = 12 * 2 ^ lam j ∨
        gat Ls (colV B2 r) = 12 * 2 ^ lam j))
    (m : Nat) (hm : inU d seed lam k m) : m < zB (yAcc Ls A2 B2 R) := by
  show m < (yAcc Ls A2 B2 R &&& (yAcc Ls A2 B2 R >>> 1)) >>> 2 + 1
  have : m ≤ (yAcc Ls A2 B2 R &&& (yAcc Ls A2 B2 R >>> 1)) >>> 2 := by
    apply Nat.le_of_testBit
    intro p hp
    obtain ⟨r, hr, j, hj, hlj⟩ := hm p hp
    rw [zB_testBit]
    have hbits : ∀ q, (12 * 2 ^ lam j).testBit q = true →
        (yAcc Ls A2 B2 R).testBit q = true := by
      intro q hq
      apply yAcc_mem Ls A2 B2 R r q (by omega)
      rcases hshift r (by omega) j hj with h | h | h
      · left; rw [h]; exact hq
      · right; left; rw [h]; exact hq
      · right; right; rw [h]; exact hq
    rw [hbits (p + 2) (by rw [testBit_12, hlj]; simp), hbits (p + 3) (by rw [testBit_12, hlj]; simp)]
    rfl
  omega

theorem xor_zero_eq {a b : Nat} (h : Nat.xor a b = 0) : a = b := by
  apply Nat.eq_of_testBit_eq
  intro i
  have := congrArg (fun x => Nat.testBit x i) h
  simp only [show Nat.xor a b = a ^^^ b from rfl, Nat.testBit_xor, Nat.zero_testBit] at this
  revert this; cases Nat.testBit a i <;> cases Nat.testBit b i <;> simp

/-! ## Checks with a starting value -/

def chkSumI (a : Nat) (f : Nat → Nat) (k0 n : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) a (fun j acc => Nat.add acc (f (Nat.add k0 j))) n

theorem chkSumI_zero (a : Nat) (f : Nat → Nat) (k0 : Nat) : ∀ n, chkSumI a f k0 n = 0 →
    a = 0 ∧ ∀ j, j < n → f (k0 + j) = 0
  | 0, h => ⟨h, fun j hj => absurd hj (Nat.not_lt_zero _)⟩
  | n + 1, h => by
    have h' : chkSumI a f k0 n + f (k0 + n) = 0 := h
    obtain ⟨ha, hf⟩ := chkSumI_zero a f k0 n (by omega)
    refine ⟨ha, fun j hj => ?_⟩
    rcases Nat.lt_or_ge j n with hl | hl
    · exact hf j hl
    · rw [show j = n by omega]; omega

/-! ## Dimension 16: relabeled columns, trimmed lanes -/

/-- The label table (a heuristic: columns of rows `0..4` first, then of rows `5..8`, then the
rest, in 32-bit lanes). Only the lane-wise exponentiation and the injectivity check below matter
for correctness. Irreducible so that elaboration never unfolds it. -/
@[irreducible] def lab16 (A2 B2 : Nat) : Nat :=
  share v1 := (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 288)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 288)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 216)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 216)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 144)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 144)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 72)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 72)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 0)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 0)) (nat_lit 4722366482869645213696))) (nat_lit 340282367000166625996085689103316680705)))))))))));
  share v2 := (Nat.mod (Nat.mul v1 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096));
  share v3 := (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 576)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 576)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 504)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 504)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 432)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 432)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight B2 (nat_lit 360)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight A2 (nat_lit 360)) (nat_lit 4722366482869645213696))) (Nat.lor v1 (nat_lit 115792089264276142096998726540203105341796590047689226336812880642240023625729))))))))));
  share v4 := (Nat.sub v3 v1);
  share v5 := (Nat.mod (Nat.mul v4 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096));
  share v6 := (Nat.shiftRight v2 (nat_lit 480));
  share v7 := (Nat.sub (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041) v3);
  (Nat.sub (Nat.add (Nat.add (Nat.land v2 (Nat.mul v1 (nat_lit 4294967295))) (Nat.land (Nat.add v5 (Nat.mul v6 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041))) (Nat.mul v4 (nat_lit 4294967295)))) (Nat.land (Nat.add (Nat.mod (Nat.mul v7 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096)) (Nat.mul (Nat.add v6 (Nat.shiftRight v5 (nat_lit 480))) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041))) (Nat.mul v7 (nat_lit 4294967295)))) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041))

def TMa (Ls A2 B2 : Nat) : Nat :=
  Nat.sub (Nat.shiftLeft (nat_lit 1) (xB (yAcc Ls A2 B2 (nat_lit 10)))) (nat_lit 1)
def TMb (Ls A2 B2 : Nat) : Nat :=
  Nat.shiftRight (TMa Ls A2 B2) (Nat.sub (xB (yAcc Ls A2 B2 (nat_lit 10))) (xB (yAcc Ls A2 B2 (nat_lit 8))))
def TMc (Ls A2 B2 : Nat) : Nat :=
  Nat.shiftRight (TMb Ls A2 B2) (Nat.sub (xB (yAcc Ls A2 B2 (nat_lit 8))) (xB (yAcc Ls A2 B2 (nat_lit 6))))
def TMd (Ls A2 B2 : Nat) : Nat :=
  Nat.shiftRight (TMc Ls A2 B2) (Nat.sub (xB (yAcc Ls A2 B2 (nat_lit 6))) (xB (yAcc Ls A2 B2 (nat_lit 4))))

/-- Trim on reaching levels `5, 7, 9, 11` (a `Nat.rec` dispatch on `k ^^^ t`, which the kernel
reduces cheaply when it compares the unrolled graph with this form). -/
def tr16 (Ls A2 B2 k G : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) (Nat.land G (TMa Ls A2 B2))
    (fun _ _ => Nat.rec (motive := fun _ => Nat) (Nat.land G (TMb Ls A2 B2))
      (fun _ _ => Nat.rec (motive := fun _ => Nat) (Nat.land G (TMc Ls A2 B2))
        (fun _ _ => Nat.rec (motive := fun _ => Nat) (Nat.land G (TMd Ls A2 B2)) (fun _ _ => G)
          (Nat.xor k (nat_lit 11))) (Nat.xor k (nat_lit 9))) (Nat.xor k (nat_lit 7))) (Nat.xor k (nat_lit 5))

theorem xor_eq_zero_iff (k a : Nat) : Nat.xor k a = 0 ↔ k = a :=
  ⟨xor_zero_eq, fun h => by
    subst h
    show k ^^^ k = 0
    exact Nat.xor_self k⟩

theorem tr16_ite (Ls A2 B2 k G : Nat) : tr16 Ls A2 B2 k G =
    if k = 5 then Nat.land G (TMa Ls A2 B2) else if k = 7 then Nat.land G (TMb Ls A2 B2) else
    if k = 9 then Nat.land G (TMc Ls A2 B2) else if k = 11 then Nat.land G (TMd Ls A2 B2) else G := by
  unfold tr16
  simp only [rec_eq, xor_eq_zero_iff]

def H16 (Ls A2 B2 k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (tr16 Ls A2 B2 (nat_lit 0) (Nat.shiftLeft (nat_lit 1) (nat_lit 786420)))
    (fun k G => tr16 Ls A2 B2 (Nat.add k (nat_lit 1))
      (stepR G (gat Ls (Nat.mul (nat_lit 32) (Nat.sub (nat_lit 15) k)))
        (gat Ls (colV A2 (Nat.sub (nat_lit 15) k))) (gat Ls (colV B2 (Nat.sub (nat_lit 15) k))))) k

def chkM16 (Ls A2 B2 : Nat) : Nat :=
  Nat.mul (Nat.div (TMb Ls A2 B2) (nat_lit 4095)) (nat_lit 3072)

def inj16 (Ls : Nat) : Nat := Nat.xor (Nat.mod Ls (nat_lit 4294967295)) (nat_lit 786420)

def chk16 (Ls A2 B2 : Nat) : Nat :=
  chkSumI (inj16 Ls) (fun k => Nat.land (H16 Ls A2 B2 k) (chkM16 Ls A2 B2)) (nat_lit 8) (nat_lit 7)

def res16 (Ls A2 B2 : Nat) : Nat :=
  Nat.add (Nat.add
    (Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 (nat_lit 15)) (gat Ls (Nat.mul (nat_lit 32) (nat_lit 0)))))
    (Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 (nat_lit 15)) (gat Ls (colV A2 (nat_lit 0))))))
    (Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 (nat_lit 15)) (gat Ls (colV B2 (nat_lit 0)))))

def fast16 (s A B : Nat) : Nat :=
  pickZ (chk16 (expW (lab16 (Nat.mul (nat_lit 32) A) (Nat.mul (nat_lit 32) B))) (Nat.mul (nat_lit 32) A)
      (Nat.mul (nat_lit 32) B))
    (res16 (expW (lab16 (Nat.mul (nat_lit 32) A) (Nat.mul (nat_lit 32) B))) (Nat.mul (nat_lit 32) A)
      (Nat.mul (nat_lit 32) B))
    (main (nat_lit 16) s)

theorem H16_zero (Ls A2 B2 : Nat) :
    H16 Ls A2 B2 0 = tr16 Ls A2 B2 0 (Nat.shiftLeft 1 786420) := rfl

theorem H16_succ (Ls A2 B2 k : Nat) :
    H16 Ls A2 B2 (k + 1) = tr16 Ls A2 B2 (k + 1) (stepR (H16 Ls A2 B2 k)
      (gat Ls (32 * (15 - k))) (gat Ls (colV A2 (15 - k))) (gat Ls (colV B2 (15 - k)))) := rfl


def bnd16 (Ls A2 B2 k : Nat) : Nat :=
  if k = 5 then zB (yAcc Ls A2 B2 10) else if k = 7 then zB (yAcc Ls A2 B2 8) else
  if k = 9 then zB (yAcc Ls A2 B2 6) else if k = 11 then zB (yAcc Ls A2 B2 4) else 2 ^ 16

theorem tr16_other (Ls A2 B2 k G : Nat) (h5 : k ≠ 5) (h7 : k ≠ 7) (h9 : k ≠ 9) (h11 : k ≠ 11) :
    tr16 Ls A2 B2 k G = G := by
  rw [tr16_ite, if_neg h5, if_neg h7, if_neg h9, if_neg h11]

theorem bnd16_other (Ls A2 B2 k : Nat) (h5 : k ≠ 5) (h7 : k ≠ 7) (h9 : k ≠ 9) (h11 : k ≠ 11) :
    bnd16 Ls A2 B2 k = 2 ^ 16 := by
  unfold bnd16; rw [if_neg h5, if_neg h7, if_neg h9, if_neg h11]

theorem tr16_eq (Ls A2 B2 : Nat) (hY : ∀ R, R ≤ 15 → yAcc Ls A2 B2 R < 2 ^ 19) (k : Nat) (f : Nat → Nat)
    (hf : ∀ m, m < 2 ^ 16 → f m < 2 ^ 12) :
    tr16 Ls A2 B2 k (enc 12 f (2 ^ 16))
      = enc 12 (fun m => if m < bnd16 Ls A2 B2 k then f m else 0) (2 ^ 16) := by
  have hz108 : zB (yAcc Ls A2 B2 8) ≤ zB (yAcc Ls A2 B2 10) :=
    zB_mono _ _ (fun q h => yAcc_mono Ls A2 B2 8 2 q h)
  have hz86 : zB (yAcc Ls A2 B2 6) ≤ zB (yAcc Ls A2 B2 8) :=
    zB_mono _ _ (fun q h => yAcc_mono Ls A2 B2 6 2 q h)
  have hz64 : zB (yAcc Ls A2 B2 4) ≤ zB (yAcc Ls A2 B2 6) :=
    zB_mono _ _ (fun q h => yAcc_mono Ls A2 B2 4 2 q h)
  have hTMa : TMa Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 10)) - 1 := by
    show (1 <<< (12 * zB (yAcc Ls A2 B2 10))) - 1 = _
    rw [Nat.one_shiftLeft]
  have hTMb : TMb Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 8)) - 1 := by
    show TMa Ls A2 B2 >>> (12 * zB (yAcc Ls A2 B2 10) - 12 * zB (yAcc Ls A2 B2 8)) = _
    rw [hTMa, ones_shr _ _ (Nat.mul_le_mul_left _ hz108)]
  have hTMc : TMc Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 6)) - 1 := by
    show TMb Ls A2 B2 >>> (12 * zB (yAcc Ls A2 B2 8) - 12 * zB (yAcc Ls A2 B2 6)) = _
    rw [hTMb, ones_shr _ _ (Nat.mul_le_mul_left _ hz86)]
  have hTMd : TMd Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 4)) - 1 := by
    show TMc Ls A2 B2 >>> (12 * zB (yAcc Ls A2 B2 6) - 12 * zB (yAcc Ls A2 B2 4)) = _
    rw [hTMc, ones_shr _ _ (Nat.mul_le_mul_left _ hz64)]
  by_cases h5 : k = 5
  · subst h5
    have e1 : tr16 Ls A2 B2 5 (enc 12 f (2 ^ 16)) = Nat.land (enc 12 f (2 ^ 16)) (TMa Ls A2 B2) := by
      rw [tr16_ite, if_pos rfl]
    have e2 : bnd16 Ls A2 B2 5 = zB (yAcc Ls A2 B2 10) := by unfold bnd16; rw [if_pos rfl]
    rw [e1, e2, hTMa]
    exact enc_trim 12 _ _ f (zB_lt _ (hY 10 (by decide))) hf
  by_cases h7 : k = 7
  · subst h7
    have e1 : tr16 Ls A2 B2 7 (enc 12 f (2 ^ 16)) = Nat.land (enc 12 f (2 ^ 16)) (TMb Ls A2 B2) := by
      rw [tr16_ite, if_neg (by decide), if_pos rfl]
    have e2 : bnd16 Ls A2 B2 7 = zB (yAcc Ls A2 B2 8) := by
      unfold bnd16; rw [if_neg (by decide), if_pos rfl]
    rw [e1, e2, hTMb]
    exact enc_trim 12 _ _ f (zB_lt _ (hY 8 (by decide))) hf
  by_cases h9 : k = 9
  · subst h9
    have e1 : tr16 Ls A2 B2 9 (enc 12 f (2 ^ 16)) = Nat.land (enc 12 f (2 ^ 16)) (TMc Ls A2 B2) := by
      rw [tr16_ite, if_neg (by decide), if_neg (by decide), if_pos rfl]
    have e2 : bnd16 Ls A2 B2 9 = zB (yAcc Ls A2 B2 6) := by
      unfold bnd16; rw [if_neg (by decide), if_neg (by decide), if_pos rfl]
    rw [e1, e2, hTMc]
    exact enc_trim 12 _ _ f (zB_lt _ (hY 6 (by decide))) hf
  by_cases h11 : k = 11
  · subst h11
    have e1 : tr16 Ls A2 B2 11 (enc 12 f (2 ^ 16)) = Nat.land (enc 12 f (2 ^ 16)) (TMd Ls A2 B2) := by
      rw [tr16_ite, if_neg (by decide), if_neg (by decide), if_neg (by decide), if_pos rfl]
    have e2 : bnd16 Ls A2 B2 11 = zB (yAcc Ls A2 B2 4) := by
      unfold bnd16; rw [if_neg (by decide), if_neg (by decide), if_neg (by decide), if_pos rfl]
    rw [e1, e2, hTMd]
    exact enc_trim 12 _ _ f (zB_lt _ (hY 4 (by decide))) hf
  rw [tr16_other Ls A2 B2 k _ h5 h7 h9 h11, bnd16_other Ls A2 B2 k h5 h7 h9 h11]
  exact enc_congr 12 _ (fun m hm => by rw [if_pos hm])

theorem chkM16_eq (Ls A2 B2 : Nat)
    (hTMb : TMb Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 8)) - 1) :
    chkM16 Ls A2 B2 = enc 12 (fun _ => 3072) (zB (yAcc Ls A2 B2 8)) := by
  show (TMb Ls A2 B2 / (2 ^ 12 - 1)) * 3072 = _
  rw [hTMb, enc_ones 12 (by decide), enc_mulc]

theorem pickZ_eq (c z f : Nat) : pickZ c z f = if c = 0 then z else f := by
  unfold pickZ; exact rec_eq c z f

theorem pc_full16 : pc (2 ^ 16 - 1) = 16 := ((pc_le 16 (2 ^ 16 - 1) (by decide)).2).mpr rfl

theorem fast16_eq (s A B : Nat) (hA : A = enc 72 (permanentColumnOne 16 s) 16)
    (hB : B = enc 72 (permanentColumnTwo 16 s) 16) :
    fast16 s A B = permanentSpec (genPermanentMatrix 16 s) := by
  rw [fast16, pickZ_eq]
  split
  next h0 =>
    generalize hA2 : Nat.mul (nat_lit 32) A = A2 at h0 ⊢
    generalize hB2 : Nat.mul (nat_lit 32) B = B2 at h0 ⊢
    generalize hL : expW (lab16 A2 B2) = Ls at h0 ⊢
    -- the label table
    let lam : Nat → Nat := fun c => lane32 (lab16 A2 B2) c % 16
    let ls : Nat → Nat := fun c => 12 * 2 ^ lam c
    have hlam : ∀ c, c < 16 → lam c < 16 := fun c _ => Nat.mod_lt _ (by decide)
    have hls : ∀ c, c < 16 → ls c < 2 ^ 19 := by
      intro c hc
      show 12 * 2 ^ lam c < 2 ^ 19
      have : 2 ^ lam c ≤ 2 ^ 15 := Nat.pow_le_pow_right (by decide) (by have := hlam c hc; omega)
      calc 12 * 2 ^ lam c ≤ 12 * 2 ^ 15 := Nat.mul_le_mul_left _ this
        _ < 2 ^ 19 := by decide
    have hls32 : ∀ c, c < 16 → ls c < 2 ^ 32 := fun c hc =>
      Nat.lt_of_lt_of_le (hls c hc) (Nat.pow_le_pow_right (by decide) (by decide))
    have hLs : Ls = enc 32 ls 16 := by rw [← hL, expW_eq]
    -- the seeded columns
    let c1 : Nat → Nat := permanentColumnOne 16 s
    let c2 : Nat → Nat := permanentColumnTwo 16 s
    have hc1 : ∀ i, i < 16 → c1 i < 16 := fun i hi => (col1_facts 16 s i (by decide) hi).1
    have hc2 : ∀ i, i < 16 → c2 i < 16 := fun i hi => (col2_facts 16 s i (by decide) hi).1
    have hA2v : ∀ r, r < 16 → colV A2 r = 32 * c1 r := by
      intro r hr
      rw [← hA2, hA, P_mull, colV_eq _ 16 r hr (fun j hj => Nat.lt_of_lt_of_le
        (by have := hc1 j hj; show c1 j * 32 < 2 ^ 72; omega) (Nat.le_refl _)), Nat.mul_comm]
    have hB2v : ∀ r, r < 16 → colV B2 r = 32 * c2 r := by
      intro r hr
      rw [← hB2, hB, P_mull, colV_eq _ 16 r hr (fun j hj => Nat.lt_of_lt_of_le
        (by have := hc2 j hj; show c2 j * 32 < 2 ^ 72; omega) (Nat.le_refl _)), Nat.mul_comm]
    have gD : ∀ r, r < 16 → gat Ls (32 * r) = ls r := fun r hr => by
      rw [hLs, gat_eq ls r hr hls32]
    have gA : ∀ r, r < 16 → gat Ls (colV A2 r) = ls (c1 r) := fun r hr => by
      rw [hA2v r hr, hLs, gat_eq ls _ (hc1 r hr) hls32]
    have gB : ∀ r, r < 16 → gat Ls (colV B2 r) = ls (c2 r) := fun r hr => by
      rw [hB2v r hr, hLs, gat_eq ls _ (hc2 r hr) hls32]
    -- the checks
    obtain ⟨hinj0, hchk⟩ := chkSumI_zero _ _ 8 7 h0
    -- injectivity of the labels
    have hinj : ∀ a b, a < 16 → b < 16 → lam a = lam b → a = b := by
      have h1 : Ls % (2 ^ 32 - 1) = 786420 := by
        have := xor_zero_eq hinj0
        exact this
      rw [hLs, enc_mod_m1] at h1
      have hs1 : sumL ls 16 ≤ 16 * 2 ^ 19 := sumL_le ls (2 ^ 19) 16 (fun i hi => Nat.le_of_lt (hls i hi))
      rw [Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt hs1 (by decide))] at h1
      have h2 : sumL (fun c => 2 ^ lam c) 16 = 2 ^ 16 - 1 := by
        have : sumL ls 16 = 12 * sumL (fun c => 2 ^ lam c) 16 := sumL_mul (fun c => 2 ^ lam c) 12 16
        omega
      have h3 : relab lam (2 ^ 16 - 1) 16 = 2 ^ 16 - 1 := by
        rw [relab_full lam _ 16 (fun c hc => by rw [Nat.testBit_two_pow_sub_one]; simp [hc]), h2]
      exact relab_inj_of_pc lam (2 ^ 16 - 1) 16
        (fun c hc => by rw [Nat.testBit_two_pow_sub_one]; simp [hc]) (by rw [h3, pc_full16])

    -- trim bounds
    have hgv : ∀ r, r ≤ 15 → gat Ls (32 * r) < 2 ^ 19 ∧ gat Ls (colV A2 r) < 2 ^ 19 ∧
        gat Ls (colV B2 r) < 2 ^ 19 := fun r hr =>
      ⟨by rw [gD r (by omega)]; exact hls r (by omega),
        by rw [gA r (by omega)]; exact hls _ (hc1 r (by omega)),
        by rw [gB r (by omega)]; exact hls _ (hc2 r (by omega))⟩
    have hYlt : ∀ R, R ≤ 15 → yAcc Ls A2 B2 R < 2 ^ 19 := fun R _ =>
      yAcc_lt Ls A2 B2 R (fun r hr => hgv r (by omega))
    have hsupp : ∀ r, supp 16 s r = [r, c1 r, c2 r] := fun r => by
      unfold supp; rw [if_neg (by decide)]
    have hshift : ∀ R, R ≤ 15 → ∀ r, r ≤ R → ∀ j, j ∈ supp 16 s r →
        (gat Ls (32 * r) = 12 * 2 ^ lam j ∨ gat Ls (colV A2 r) = 12 * 2 ^ lam j ∨
          gat Ls (colV B2 r) = 12 * 2 ^ lam j) := by
      intro R hR r hr j hj
      rw [hsupp r] at hj
      simp only [List.mem_cons, List.mem_nil_iff, or_false] at hj
      rcases hj with h | h | h
      · left; rw [h]; exact gD r (by omega)
      · right; left; rw [h]; exact gA r (by omega)
      · right; right; rw [h]; exact gB r (by omega)
    let bnd : Nat → Nat := bnd16 Ls A2 B2
    have hbnd : ∀ k, k ≤ 16 → ∀ m, m < 2 ^ 16 → inU 16 s lam k m → m < bnd k := by
      intro k _ m hm hu
      show m < bnd16 Ls A2 B2 k
      by_cases h5 : k = 5
      · subst h5; exact zB_bound 16 s lam Ls A2 B2 10 5 rfl (hshift 10 (by decide)) m hu
      by_cases h7 : k = 7
      · subst h7; exact zB_bound 16 s lam Ls A2 B2 8 7 rfl (hshift 8 (by decide)) m hu
      by_cases h9 : k = 9
      · subst h9; exact zB_bound 16 s lam Ls A2 B2 6 9 rfl (hshift 6 (by decide)) m hu
      by_cases h11 : k = 11
      · subst h11; exact zB_bound 16 s lam Ls A2 B2 4 11 rfl (hshift 4 (by decide)) m hu
      rw [bnd16_other Ls A2 B2 k h5 h7 h9 h11]; exact hm
    have hb7 : bnd 7 = zB (yAcc Ls A2 B2 8) := rfl
    have hb7le : bnd 7 ≤ 2 ^ 16 := zB_lt _ (hYlt 8 (by decide))
    have hTMb : TMb Ls A2 B2 = 2 ^ (12 * zB (yAcc Ls A2 B2 8)) - 1 := by
      have hz108 : zB (yAcc Ls A2 B2 8) ≤ zB (yAcc Ls A2 B2 10) :=
        zB_mono _ _ (fun q h => yAcc_mono Ls A2 B2 8 2 q h)
      show ((1 <<< (12 * zB (yAcc Ls A2 B2 10))) - 1) >>>
        (12 * zB (yAcc Ls A2 B2 10) - 12 * zB (yAcc Ls A2 B2 8)) = _
      rw [Nat.one_shiftLeft, ones_shr _ _ (Nat.mul_le_mul_left _ hz108)]
    have hchkM := chkM16_eq Ls A2 B2 hTMb
    -- lanes above `bnd 7` stay empty from level 7 on
    have hhigh : ∀ t m, bnd 7 ≤ m → hlT 16 s lam bnd (7 + t) m = 0 :=
      hlT_high_zero 16 s lam bnd (bnd 7) 7 (fun m hm => by
        show (if m < bnd 7 then _ else 0) = 0
        rw [if_neg (by omega)])
    -- the invariant
    have hinv : ∀ k, k ≤ 15 → H16 Ls A2 B2 k = enc 12 (hlT 16 s lam bnd k) (2 ^ 16) ∧
        ∀ m, m < 2 ^ 16 → hlT 16 s lam bnd k m < 2 ^ 12 := by
      intro k
      induction k with
      | zero =>
        intro _
        have hb0 : bnd 0 = 2 ^ 16 := bnd16_other Ls A2 B2 0 (by decide) (by decide) (by decide) (by decide)
        have e0 : ∀ m, m < 2 ^ 16 → hlT 16 s lam bnd 0 m = hl 16 s 0 m := fun m hm => by
          show (if m < bnd 0 then hlR 16 s lam 0 m else 0) = _
          rw [hb0, if_pos hm]; rfl
        refine ⟨?_, fun m hm => ?_⟩
        · rw [H16_zero, tr16_other Ls A2 B2 0 _ (by decide) (by decide) (by decide) (by decide),
            enc_congr 12 _ e0, ← base_eq 12 16 s]
          rfl
        · rw [e0 m hm]; have := hl_zero_lt 16 s 12 m (by decide); exact this
      | succ k ih =>
        intro hk
        obtain ⟨ih1, ih2⟩ := ih (by omega)
        have hi : 15 - k < 16 := by omega
        -- one row of shifts
        let U : Nat → Nat := fun m => ([15 - k, c1 (15 - k), c2 (15 - k)].map
          (fun j => if 2 ^ lam j + m < 2 ^ 16 then hlT 16 s lam bnd k (2 ^ lam j + m) else 0)).sum
        have hstep : stepR (H16 Ls A2 B2 k) (gat Ls (32 * (15 - k))) (gat Ls (colV A2 (15 - k)))
            (gat Ls (colV B2 (15 - k))) = enc 12 U (2 ^ 16) := by
          rw [ih1, gD _ hi, gA _ hi, gB _ hi]
          exact stepR_lam 12 16 _ lam _ _ _ (hlam _ hi) (hlam _ (hc1 _ hi)) (hlam _ (hc2 _ hi)) ih2
        -- the untrimmed lanes are below 2^12
        have hU : ∀ m, m < 2 ^ 16 → U m < 2 ^ 12 := by
          intro m _
          have hUle : ∀ b, (∀ m', m' < 2 ^ 16 → hlT 16 s lam bnd k m' ≤ b) → U m ≤ 3 * b := by
            intro b hb
            show ([15 - k, c1 (15 - k), c2 (15 - k)].map _).sum ≤ 3 * b
            have := sum_map_le (fun j => if 2 ^ lam j + m < 2 ^ 16 then hlT 16 s lam bnd k (2 ^ lam j + m) else 0)
              b [15 - k, c1 (15 - k), c2 (15 - k)] (fun j _ => by
                show (if 2 ^ lam j + m < 2 ^ 16 then hlT 16 s lam bnd k (2 ^ lam j + m) else 0) ≤ b
                split
                · exact hb _ (by assumption)
                · exact Nat.zero_le _)
            exact this
          by_cases hk8 : k < 8
          · have hb : ∀ m', m' < 2 ^ 16 → hlT 16 s lam bnd k m' ≤ 3 ^ (k - 1) := fun m' _ =>
              Nat.le_trans (hlT_le 16 s lam bnd k m') (hlR_bound_tight 16 s lam (by decide) hinj k m')
            have h3 : 3 * 3 ^ (k - 1) < 2 ^ 12 := by
              have : 3 ^ (k - 1) ≤ 3 ^ 6 := Nat.pow_le_pow_right (by decide) (by omega)
              have : 3 * 3 ^ 6 < 2 ^ 12 := by decide
              omega
            exact Nat.lt_of_le_of_lt (hUle _ hb) h3
          · -- the check at level k
            have hck := hchk (k - 8) (by omega)
            simp only [show 8 + (k - 8) = k by omega] at hck
            rw [ih1, hchkM] at hck
            have hk7 : k = 7 + (k - 7) := by omega
            have hpad : enc 12 (hlT 16 s lam bnd k) (2 ^ 16) = enc 12 (hlT 16 s lam bnd k) (bnd 7) := by
              rw [enc_pad 12 _ (bnd 7) (2 ^ 16) hb7le]
              apply enc_congr; intro m' _
              by_cases h : m' < bnd 7
              · rw [if_pos h]
              · rw [if_neg h, hk7, hhigh (k - 7) m' (by omega)]
            rw [hpad, ← hb7, P_and 12 (by decide) _ _ _ (fun m' hm' => ih2 m' (by omega))
              (fun _ _ => by decide)] at hck
            have hb : ∀ m', m' < 2 ^ 16 → hlT 16 s lam bnd k m' ≤ 2 ^ 10 - 1 := by
              intro m' hm'
              by_cases h : m' < bnd 7
              · have h1 := enc_eq_zero 12 _ _ hck m' h
                have := land_mask_lt _ 12 10 (ih2 m' hm') (by rw [show topMask 12 10 = 3072 from rfl]; exact h1)
                omega
              · rw [hk7, hhigh (k - 7) m' (by omega)]; exact Nat.zero_le _
            exact Nat.lt_of_le_of_lt (hUle _ hb) (by decide)
        have hT : ∀ m, m < 2 ^ 16 → hlT 16 s lam bnd (k + 1) m = if m < bnd (k + 1) then U m else 0 := by
          intro m _
          rw [hlT_succ_eq 16 s lam bnd k m, show 16 - 1 - k = 15 - k by omega, hsupp]
        refine ⟨?_, fun m hm => ?_⟩
        · rw [H16_succ, hstep, tr16_eq Ls A2 B2 hYlt (k + 1) U hU]
          exact enc_congr 12 _ (fun m hm => (hT m hm).symm)
        · rw [hT m hm]; split
          · exact hU m hm
          · exact Nat.two_pow_pos _
    -- the answer lane
    obtain ⟨h15, h15b⟩ := hinv 15 (by decide)
    have hb16 : bnd 16 = 2 ^ 16 := bnd16_other Ls A2 B2 16 (by decide) (by decide) (by decide) (by decide)
    have hlane : ∀ j, j < 16 → Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 15) (ls j))
        = hlT 16 s lam bnd 15 (2 ^ lam j) := by
      intro j hj
      rw [h15]
      exact lane_get 12 (2 ^ 16) (2 ^ lam j) _ (Nat.pow_lt_pow_right (by decide) (hlam j hj)) h15b
    show (Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 15) (gat Ls (32 * 0))) +
      Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 15) (gat Ls (colV A2 0)))) +
      Nat.land (nat_lit 4095) (Nat.shiftRight (H16 Ls A2 B2 15) (gat Ls (colV B2 0))) = _
    rw [gD 0 (by decide), gA 0 (by decide), gB 0 (by decide), hlane 0 (by decide),
      hlane _ (hc1 0 (by decide)), hlane _ (hc2 0 (by decide)),
      ← hlT_final 16 s lam bnd hlam hinj hbnd]
    have h0 : ∀ j, j < 16 → 2 ^ lam j < 2 ^ 16 := fun j hj => Nat.pow_lt_pow_right (by decide) (hlam j hj)
    rw [show hlT 16 s lam bnd 16 0 = hlT 16 s lam bnd (15 + 1) 0 from rfl,
      hlT_succ_zero 16 s lam bnd 15, hb16, if_pos (by decide), show (16 - 1 - 15 : Nat) = 0 from rfl,
      hsupp, List.map_cons, List.map_cons, List.map_cons, List.map_nil, List.sum_cons, List.sum_cons,
      List.sum_cons, List.sum_nil, if_pos (h0 0 (by decide)), if_pos (h0 _ (hc1 0 (by decide))),
      if_pos (h0 _ (hc2 0 (by decide)))]
    omega
  next => exact main_eq 16 s (by decide)

theorem cols_enc (D s R Kc Mv P sh MvD Mg1 S1 Mg2 S2 g1 g0 g2 o : Nat) (hD : 3 ≤ D) (hD16 : D ≤ 16)
    (hs : s < 2 ^ 32)
    (hR : R = enc 72 (fun _ => 1) (D + D)) (hKc : Kc = enc 72 (kcOf D) (D + D))
    (hMv : Mv = enc 72 (fun _ => 0xffffffff) (D + D)) (hP : P = 2 ^ (72 * D)) (hsh : sh = 72 * D)
    (hMvD : MvD = enc 72 (fun _ => 0xffffffff) D)
    (hMg1 : Mg1 < 2 ^ 40) (hS1 : S1 ≤ 40) (hdiv1 : ∀ x, x < 2 ^ 32 → x * Mg1 / 2 ^ S1 = x / (D - 1))
    (hMg2 : Mg2 < 2 ^ 40) (hS2 : S2 ≤ 40) (hdiv2 : ∀ x, x < 2 ^ 32 → x * Mg2 / 2 ^ S2 = x / (D - 2))
    (hg1 : g1 = enc 72 (fun i => 32 - i) D) (hg0 : g0 = enc 72 (fun _ => 32) D)
    (hg2 : g2 = enc 72 (fun i => 33 - i) D) (ho : o = enc 72 (fun _ => 1) D) :
    vecA (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P))
        (vecC g1 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P)))
        = enc 72 (permanentColumnOne D s) D ∧
    vecB g0 g2 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P))
        (vecK Mg2 S2 (D - 2) MvD (Nat.shiftRight (vecZ R Kc Mv s) sh))
        (vecC g1 o (vecK Mg1 S1 (D - 1) MvD (Nat.mod (vecZ R Kc Mv s) P)))
        = enc 72 (permanentColumnTwo D s) D := by
  subst hR hKc hMv hP hsh hMvD hg1 hg0 hg2 ho
  -- the mixer outputs
  let z : Nat → Nat := fun j => mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D j)
  have hz : ∀ j, j < D + D → z j < 2 ^ 72 := fun j _ => lt72_of_lt32 (mixT_lt _)
  have hZ := vecZ_eq (D + D) s (kcOf D) hs (fun j _ => kcOf_lt D j)
  have hZ1 : Nat.mod (vecZ (enc 72 (fun _ => 1) (D + D)) (enc 72 (kcOf D) (D + D))
      (enc 72 (fun _ => 0xffffffff) (D + D)) s) (2 ^ (72 * D)) = enc 72 z D := by
    rw [hZ]; exact enc_low 72 z D D hz
  have hZ2 : Nat.shiftRight (vecZ (enc 72 (fun _ => 1) (D + D)) (enc 72 (kcOf D) (D + D))
      (enc 72 (fun _ => 0xffffffff) (D + D)) s) (72 * D) = enc 72 (fun j => z (D + j)) D := by
    rw [hZ]; exact enc_high 72 z D D hz
  rw [hZ1, hZ2, vecK_eq D Mg1 S1 (D - 1) z (fun j _ => mixT_lt _) hMg1 hS1 hdiv1,
    vecK_eq D Mg2 S2 (D - 2) (fun j => z (D + j)) (fun j _ => mixT_lt _) hMg2 hS2 hdiv2]
  have hk1 : ∀ i, i < D → z i % (D - 1) < 16 := fun i _ =>
    Nat.lt_of_lt_of_le (Nat.mod_lt _ (by omega)) (by omega)
  have hk2 : ∀ i, i < D → z (D + i) % (D - 2) < 16 := fun i _ =>
    Nat.lt_of_lt_of_le (Nat.mod_lt _ (by omega)) (by omega)
  rw [vecC_eq D (fun i => z i % (D - 1)) hD16 hk1, vecA_eq,
    vecB_eq D _ _ _ hD16 hk1 hk2 (fun i _ => by split <;> omega)]
  -- lane values are the spec columns
  have hm1 : ∀ i, i < D → z i % (D - 1)
      = permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0x85ebca6b) % (D - 1) := by
    intro i hi
    show mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D i) % (D - 1) = _
    unfold kcOf
    rw [← mix_split s _ hs, kOf_lo D i hi, Nat.xor_assoc]
  have hm2 : ∀ i, i < D → z (D + i) % (D - 2)
      = permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35) % (D - 2) := by
    intro i hi
    show mixT ((s ^^^ (s >>> 16)) ^^^ kcOf D (D + i)) % (D - 2) = _
    unfold kcOf
    rw [← mix_split s _ hs, kOf_hi D i, Nat.xor_assoc]
  constructor
  · apply enc_congr; intro i hi
    show z i % (D - 1) + (if i ≤ z i % (D - 1) then 1 else 0) = _
    rw [hm1 i hi]
    unfold permanentColumnOne
    exact (skip_lanes i _ (permanentMix32 (s ^^^ (i * 0x9e3779b9) ^^^ 0xc2b2ae35) % (D - 2))).1
  · apply enc_congr; intro i hi
    show (z (D + i) % (D - 2) + (if z i % (D - 1) ≤ z (D + i) % (D - 2) then 1 else 0)) +
      (if i + (if i ≤ z i % (D - 1) then 1 else 0) ≤ z (D + i) % (D - 2) + 1 then 1 else 0) = _
    rw [hm1 i hi, hm2 i hi]
    unfold permanentColumnTwo permanentColumnOne
    exact (skip_lanes i _ _).2


/-! ## Dimension 6 -/
def R_6 : Nat := nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257
def Kc_6 : Nat := nat_lit 93360064040038295861878278266449805078272207139597033035313552624026289263382838638669157893022302823968925714209858097937549203947864038948570033198531935483825594063526935668802557571010778940553232012643557418342380277048862780003419698770956160
def Mv_6 : Nat := nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815
def MvD_6 : Nat := nat_lit 10086913583928444095571737024782708124157061913240334445906995829324624462141156261912157103264042300304278683329232895
def g1_6 : Nat := nat_lit 63410649734893497153029901163931573765123782577529205880778083243883794596581216907076865979769752095576555552
def g0_6 : Nat := nat_lit 75153362648762663292479293440823898048570817167000267523346500019946713654432379183271295970240759099828469792
def g2_6 : Nat := nat_lit 65759192317667330380919879083957320579141620613997964240882661369507129398282228756554093978839775817446195233
def o_6 : Nat := nat_lit 2348542582773833227889977920025746814017838036468758360104578125623334801701011849477227999070023721869639681

noncomputable def K1_6 (s : Nat) : Nat :=
  vecK (nat_lit 3435973837) (nat_lit 34) (nat_lit 5) MvD_6 (Nat.mod (vecZ R_6 Kc_6 Mv_6 s) (nat_lit 11090678776483259438313656736572334813745748301503266300681918322458485231222502492159897624416558312389564843845614287315896631296))

noncomputable def K2_6 (s : Nat) : Nat :=
  vecK (nat_lit 1073741824) (nat_lit 32) (nat_lit 4) MvD_6 (Nat.shiftRight (vecZ R_6 Kc_6 Mv_6 s) (nat_lit 432))

noncomputable def A_6 (s : Nat) : Nat := vecA (K1_6 s) (vecC g1_6 o_6 (K1_6 s))

noncomputable def B_6 (s : Nat) : Nat :=
  vecB g0_6 g2_6 o_6 (K1_6 s) (K2_6 s) (vecC g1_6 o_6 (K1_6 s))

noncomputable def mainS6 (s : Nat) : Nat :=
  Nat.land (loopV (nat_lit 6) (nat_lit 8) (A_6 s) (B_6 s) (nat_lit 6)) (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 8)) (nat_lit 1))

theorem R_6_eq : R_6 = enc 72 (fun _ => 1) (6 + 6) := by decide +kernel
theorem Kc_6_eq : Kc_6 = enc 72 (kcOf 6) (6 + 6) := by decide +kernel
theorem Mv_6_eq : Mv_6 = enc 72 (fun _ => 0xffffffff) (6 + 6) := by decide +kernel
theorem MvD_6_eq : MvD_6 = enc 72 (fun _ => 0xffffffff) 6 := by decide +kernel
theorem g1_6_eq : g1_6 = enc 72 (fun i => 32 - i) 6 := by decide +kernel
theorem g0_6_eq : g0_6 = enc 72 (fun _ => 32) 6 := by decide +kernel
theorem g2_6_eq : g2_6 = enc 72 (fun i => 33 - i) 6 := by decide +kernel
theorem o_6_eq : o_6 = enc 72 (fun _ => 1) 6 := by decide +kernel

theorem div_6a : ∀ x, x < 2 ^ 32 → x * 3435973837 / 2 ^ 34 = x / (6 - 1) := by
  intro x hx; omega

theorem div_6b : ∀ x, x < 2 ^ 32 → x * 1073741824 / 2 ^ 32 = x / (6 - 2) := by
  intro x hx; omega

theorem cols_6 (s : Nat) (hs : s < 2 ^ 32) :
    (∀ i, i < 6 → colV (A_6 s) i = permanentColumnOne 6 s i) ∧
    (∀ i, i < 6 → colV (B_6 s) i = permanentColumnTwo 6 s i) :=
  cols_eq 6 s R_6 Kc_6 Mv_6 (nat_lit 11090678776483259438313656736572334813745748301503266300681918322458485231222502492159897624416558312389564843845614287315896631296) (nat_lit 432) MvD_6 (nat_lit 3435973837) (nat_lit 34)
    (nat_lit 1073741824) (nat_lit 32) g1_6 g0_6 g2_6 o_6 (by decide) (by decide) hs R_6_eq Kc_6_eq
    Mv_6_eq (by decide +kernel) rfl MvD_6_eq (by decide) (by decide) div_6a (by decide) (by decide)
    div_6b g1_6_eq g0_6_eq g2_6_eq o_6_eq

theorem mainS6_eq (s : Nat) (hs : s < 2 ^ 32) :
    mainS6 s = permanentSpec (genPermanentMatrix 6 s) :=
  plainV_eq 6 8 s (A_6 s) (B_6 s) (by decide) (cols_6 s hs).1 (cols_6 s hs).2 (by decide)
    (by decide)

/-- `mainS6` as one shared graph (`mainU6_eq`, by `rfl`). -/
def mainU6 (s : Nat) : Nat :=
  share v1 := (Nat.land (Nat.mul (nat_lit 2146121005) (Nat.xor (Nat.mul (nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257) (Nat.xor s (Nat.shiftRight s (nat_lit 16)))) (nat_lit 93360064040038295861878278266449805078272207139597033035313552624026289263382838638669157893022302823968925714209858097937549203947864038948570033198531935483825594063526935668802557571010778940553232012643557418342380277048862780003419698770956160))) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815));
  share v2 := (Nat.land (Nat.mul (nat_lit 2221713035) (Nat.land (Nat.xor v1 (Nat.shiftRight v1 (nat_lit 15))) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815))) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815));
  share v3 := (Nat.land (Nat.xor v2 (Nat.shiftRight v2 (nat_lit 16))) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815));
  share v4 := (Nat.mod v3 (nat_lit 11090678776483259438313656736572334813745748301503266300681918322458485231222502492159897624416558312389564843845614287315896631296));
  share v5 := (Nat.sub v4 (Nat.mul (nat_lit 5) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 3435973837) v4) (nat_lit 34)) (nat_lit 10086913583928444095571737024782708124157061913240334445906995829324624462141156261912157103264042300304278683329232895))));
  share v6 := (Nat.land (Nat.shiftRight (Nat.add (nat_lit 63410649734893497153029901163931573765123782577529205880778083243883794596581216907076865979769752095576555552) v5) (nat_lit 5)) (nat_lit 2348542582773833227889977920025746814017838036468758360104578125623334801701011849477227999070023721869639681));
  share v7 := (Nat.add v5 v6);
  share v8 := (Nat.shiftRight v3 (nat_lit 432));
  share v9 := (Nat.sub v8 (Nat.mul (nat_lit 4) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 1073741824) v8) (nat_lit 32)) (nat_lit 10086913583928444095571737024782708124157061913240334445906995829324624462141156261912157103264042300304278683329232895))));
  share v10 := (Nat.add (Nat.add v9 (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 75153362648762663292479293440823898048570817167000267523346500019946713654432379183271295970240759099828469792) v9) v5) (nat_lit 5)) (nat_lit 2348542582773833227889977920025746814017838036468758360104578125623334801701011849477227999070023721869639681))) (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 65759192317667330380919879083957320579141620613997964240882661369507129398282228756554093978839775817446195233) v9) v6) (nat_lit 5)) (nat_lit 2348542582773833227889977920025746814017838036468758360104578125623334801701011849477227999070023721869639681)));
  share v11 := (Nat.add (Nat.add (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 504))) (nat_lit 256)) (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 504))) (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 360)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 504))) (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 360)) (nat_lit 4722366482869645213696)))));
  share v12 := (Nat.add (Nat.add (Nat.shiftRight v11 (nat_lit 128)) (Nat.shiftRight v11 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 288)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v11 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 288)) (nat_lit 4722366482869645213696)))));
  share v13 := (Nat.add (Nat.add (Nat.shiftRight v12 (nat_lit 64)) (Nat.shiftRight v12 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 216)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v12 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 216)) (nat_lit 4722366482869645213696)))));
  share v14 := (Nat.add (Nat.add (Nat.shiftRight v13 (nat_lit 32)) (Nat.shiftRight v13 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 144)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v13 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 144)) (nat_lit 4722366482869645213696)))));
  share v15 := (Nat.add (Nat.add (Nat.shiftRight v14 (nat_lit 16)) (Nat.shiftRight v14 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 72)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v14 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 72)) (nat_lit 4722366482869645213696)))));
  (Nat.land (Nat.add (Nat.add (Nat.shiftRight v15 (nat_lit 8)) (Nat.shiftRight v15 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v7 (nat_lit 0)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v15 (Nat.shiftLeft (nat_lit 8) (Nat.mod (Nat.shiftRight v10 (nat_lit 0)) (nat_lit 4722366482869645213696))))) (nat_lit 255))

/- `mainU6_eq : ∀ s, mainU6 s = mainS6 s` by `rfl`, checked by the kernel. -/
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ s, mainU6 s = mainS6 s)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) => @rfl Nat (mainU6 s))) none)
  addDecl (.thmDecl { name := `Submission.mainU6_eq, levelParams := [], type := ty, value := pf })

/-! ## Dimension 12 -/
def R_12 : Nat := nat_lit 3203854756451720653596302694069914683010064521722337228716078589420628389963666873815297152521011908797927909892172339172247998610741944836415349102305292598640512812698758740606302504230171602668335177067240621671007950745046817604754032144939971063958401594415325336508220252790814369055897122299601322967077105830745908288830097511728931320902038428941534136663772264123316046145254418786893449609040806415805329070464718506115258859148860756401346230018404653793529032257213848438481111448813569
def Kc_12 : Nat := nat_lit 797584179815601220711449694182656039856580818180895747782305602898464931901338694803277296132708121882102437249503836233791460588948963787232419546656657358580202495756810376830283071476857599265764148169769618146757708786443619931687733437139532823032311124083087586961826292086251233007953759192232913266604434766143906105934493490755411475162639051001745891262995708569481392831256884159720541025440718147321601315691518146961353401605894558294347179975218298857434478223225906391275204209511196659502976
def Mv_12 : Nat := nat_lit 13760451396890330453672144203950674006968519276637255468296492382211331933242455461311593140784372948592623136754587173248452525662342088757098049430408840816566563992569629477999457726545186185698234317601832485972447398134946964856248804581895875457947688088489676967087675484393180191511138167161402873682328531286307481555594682624536638928575404951137070584096962285737744265142578548143940940720560799876310059444358716435146294300503368485252743951900595236119004876177733506864363193147904345407225855
def MvD_12 : Nat := nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815
def g1_12 : Nat := nat_lit 546985558947175545920734186557391422392603015011690677945494349474822896135161200582492062143503582928425503082007982205114756174428678022997481466403205702890894810049920918432476946095565237596985989686728644967584071614913707336013971488
def g0_12 : Nat := nat_lit 833501804109981784260157974712576488236654146967639848852014917206387745066422600176123631502164765459617112854368802159512186321608767882282771097020286178090388199078334187205439780611627138229795091141473563425442923143030041827126280224
def g2_12 : Nat := nat_lit 573032490325612476678864123267159437649998457104429423222119815637522513168486906837995925627946231849038537858707007272599511996978952019318818063185089645956219441271118861782646939239678585666667086284899693824629162963133396143111667745
def o_12 : Nat := nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257

noncomputable def K1_12 (s : Nat) : Nat :=
  vecK (nat_lit 3123612579) (nat_lit 35) (nat_lit 11) MvD_12 (Nat.mod (vecZ R_12 Kc_12 Mv_12 s) (nat_lit 123003155723136208567847447683223664415731869180715065944930703618254955521953492303010368693540149343822709050322214299552689203876695953600699775494388206142090885899729347827083318884583758435450548517566916626912548274908112766882031433928533568160966639616))

noncomputable def K2_12 (s : Nat) : Nat :=
  vecK (nat_lit 3435973837) (nat_lit 35) (nat_lit 10) MvD_12 (Nat.shiftRight (vecZ R_12 Kc_12 Mv_12 s) (nat_lit 864))

noncomputable def A_12 (s : Nat) : Nat := vecA (K1_12 s) (vecC g1_12 o_12 (K1_12 s))

noncomputable def B_12 (s : Nat) : Nat :=
  vecB g0_12 g2_12 o_12 (K1_12 s) (K2_12 s) (vecC g1_12 o_12 (K1_12 s))

noncomputable def mainS12 (s : Nat) : Nat := fastL (nat_lit 12) (nat_lit 10) (nat_lit 8) s (A_12 s) (B_12 s) (nat_lit 7) (nat_lit 4)

theorem R_12_eq : R_12 = enc 72 (fun _ => 1) (12 + 12) := by decide +kernel
theorem Kc_12_eq : Kc_12 = enc 72 (kcOf 12) (12 + 12) := by decide +kernel
theorem Mv_12_eq : Mv_12 = enc 72 (fun _ => 0xffffffff) (12 + 12) := by decide +kernel
theorem MvD_12_eq : MvD_12 = enc 72 (fun _ => 0xffffffff) 12 := by decide +kernel
theorem g1_12_eq : g1_12 = enc 72 (fun i => 32 - i) 12 := by decide +kernel
theorem g0_12_eq : g0_12 = enc 72 (fun _ => 32) 12 := by decide +kernel
theorem g2_12_eq : g2_12 = enc 72 (fun i => 33 - i) 12 := by decide +kernel
theorem o_12_eq : o_12 = enc 72 (fun _ => 1) 12 := by decide +kernel

theorem div_12a : ∀ x, x < 2 ^ 32 → x * 3123612579 / 2 ^ 35 = x / (12 - 1) := by
  intro x hx; omega

theorem div_12b : ∀ x, x < 2 ^ 32 → x * 3435973837 / 2 ^ 35 = x / (12 - 2) := by
  intro x hx; omega

theorem cols_12 (s : Nat) (hs : s < 2 ^ 32) :
    (∀ i, i < 12 → colV (A_12 s) i = permanentColumnOne 12 s i) ∧
    (∀ i, i < 12 → colV (B_12 s) i = permanentColumnTwo 12 s i) :=
  cols_eq 12 s R_12 Kc_12 Mv_12 (nat_lit 123003155723136208567847447683223664415731869180715065944930703618254955521953492303010368693540149343822709050322214299552689203876695953600699775494388206142090885899729347827083318884583758435450548517566916626912548274908112766882031433928533568160966639616) (nat_lit 864) MvD_12 (nat_lit 3123612579) (nat_lit 35)
    (nat_lit 3435973837) (nat_lit 35) g1_12 g0_12 g2_12 o_12 (by decide) (by decide) hs R_12_eq Kc_12_eq
    Mv_12_eq (by decide +kernel) rfl MvD_12_eq (by decide) (by decide) div_12a (by decide) (by decide)
    div_12b g1_12_eq g0_12_eq g2_12_eq o_12_eq

theorem mainS12_eq (s : Nat) (hs : s < 2 ^ 32) :
    mainS12 s = permanentSpec (genPermanentMatrix 12 s) :=
  fastL_eq 12 10 8 s (A_12 s) (B_12 s) 7 4 (by decide) (cols_12 s hs).1 (cols_12 s hs).2
    (by decide) (by decide) (by decide) (by decide)

/-- `mainS12` as one shared graph (`mainU12_eq`, by `rfl`). -/
def mainU12 (s : Nat) : Nat :=
  share v1 := (Nat.land (Nat.mul (nat_lit 2146121005) (Nat.xor (Nat.mul (nat_lit 3203854756451720653596302694069914683010064521722337228716078589420628389963666873815297152521011908797927909892172339172247998610741944836415349102305292598640512812698758740606302504230171602668335177067240621671007950745046817604754032144939971063958401594415325336508220252790814369055897122299601322967077105830745908288830097511728931320902038428941534136663772264123316046145254418786893449609040806415805329070464718506115258859148860756401346230018404653793529032257213848438481111448813569) (Nat.xor s (Nat.shiftRight s (nat_lit 16)))) (nat_lit 797584179815601220711449694182656039856580818180895747782305602898464931901338694803277296132708121882102437249503836233791460588948963787232419546656657358580202495756810376830283071476857599265764148169769618146757708786443619931687733437139532823032311124083087586961826292086251233007953759192232913266604434766143906105934493490755411475162639051001745891262995708569481392831256884159720541025440718147321601315691518146961353401605894558294347179975218298857434478223225906391275204209511196659502976))) (nat_lit 13760451396890330453672144203950674006968519276637255468296492382211331933242455461311593140784372948592623136754587173248452525662342088757098049430408840816566563992569629477999457726545186185698234317601832485972447398134946964856248804581895875457947688088489676967087675484393180191511138167161402873682328531286307481555594682624536638928575404951137070584096962285737744265142578548143940940720560799876310059444358716435146294300503368485252743951900595236119004876177733506864363193147904345407225855));
  share v2 := (Nat.land (Nat.mul (nat_lit 2221713035) (Nat.land (Nat.xor v1 (Nat.shiftRight v1 (nat_lit 15))) (nat_lit 13760451396890330453672144203950674006968519276637255468296492382211331933242455461311593140784372948592623136754587173248452525662342088757098049430408840816566563992569629477999457726545186185698234317601832485972447398134946964856248804581895875457947688088489676967087675484393180191511138167161402873682328531286307481555594682624536638928575404951137070584096962285737744265142578548143940940720560799876310059444358716435146294300503368485252743951900595236119004876177733506864363193147904345407225855))) (nat_lit 13760451396890330453672144203950674006968519276637255468296492382211331933242455461311593140784372948592623136754587173248452525662342088757098049430408840816566563992569629477999457726545186185698234317601832485972447398134946964856248804581895875457947688088489676967087675484393180191511138167161402873682328531286307481555594682624536638928575404951137070584096962285737744265142578548143940940720560799876310059444358716435146294300503368485252743951900595236119004876177733506864363193147904345407225855));
  share v3 := (Nat.land (Nat.xor v2 (Nat.shiftRight v2 (nat_lit 16))) (nat_lit 13760451396890330453672144203950674006968519276637255468296492382211331933242455461311593140784372948592623136754587173248452525662342088757098049430408840816566563992569629477999457726545186185698234317601832485972447398134946964856248804581895875457947688088489676967087675484393180191511138167161402873682328531286307481555594682624536638928575404951137070584096962285737744265142578548143940940720560799876310059444358716435146294300503368485252743951900595236119004876177733506864363193147904345407225855));
  share v4 := (Nat.mod v3 (nat_lit 123003155723136208567847447683223664415731869180715065944930703618254955521953492303010368693540149343822709050322214299552689203876695953600699775494388206142090885899729347827083318884583758435450548517566916626912548274908112766882031433928533568160966639616));
  share v5 := (Nat.sub v4 (Nat.mul (nat_lit 11) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 3123612579) v4) (nat_lit 35)) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815))));
  share v6 := (Nat.land (Nat.shiftRight (Nat.add (nat_lit 546985558947175545920734186557391422392603015011690677945494349474822896135161200582492062143503582928425503082007982205114756174428678022997481466403205702890894810049920918432476946095565237596985989686728644967584071614913707336013971488) v5) (nat_lit 5)) (nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257));
  share v7 := (Nat.add v5 v6);
  share v8 := (Nat.shiftRight v3 (nat_lit 864));
  share v9 := (Nat.sub v8 (Nat.mul (nat_lit 10) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 3435973837) v8) (nat_lit 35)) (nat_lit 111870718405495885826347633528873532567574430670379267942442105132924004067158833450166007411825918417200035716619940723232194168914250307489090993864793783951211339652981077410242853244341051732231690968880411656855797680891019901562169293658914815))));
  share v10 := (Nat.add (Nat.add v9 (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 833501804109981784260157974712576488236654146967639848852014917206387745066422600176123631502164765459617112854368802159512186321608767882282771097020286178090388199078334187205439780611627138229795091141473563425442923143030041827126280224) v9) v5) (nat_lit 5)) (nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257))) (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 573032490325612476678864123267159437649998457104429423222119815637522513168486906837995925627946231849038537858707007272599511996978952019318818063185089645956219441271118861782646939239678585666667086284899693824629162963133396143111667745) v9) v6) (nat_lit 5)) (nat_lit 26046931378436930758129936709768015257395442092738745276625466162699617033325706255503863484442648920613034776699025067484755822550273996321336596781883943065324631221197943350169993144113348069681096598171048857045091348219688807097696257)));
  share v11 := (Nat.add (Nat.add (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 40950))) (nat_lit 20480)) (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 40950))) (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 792)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight (eval% (Nat.shiftLeft (nat_lit 1) (nat_lit 40950))) (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 792)) (nat_lit 4722366482869645213696)))));
  share v12 := (Nat.add (Nat.add (Nat.shiftRight v11 (nat_lit 10240)) (Nat.shiftRight v11 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 720)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v11 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 720)) (nat_lit 4722366482869645213696)))));
  share v13 := (Nat.add (Nat.add (Nat.shiftRight v12 (nat_lit 5120)) (Nat.shiftRight v12 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 648)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v12 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 648)) (nat_lit 4722366482869645213696)))));
  share v14 := (Nat.add (Nat.add (Nat.shiftRight v13 (nat_lit 2560)) (Nat.shiftRight v13 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 576)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v13 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 576)) (nat_lit 4722366482869645213696)))));
  share v15 := (Nat.add (Nat.add (Nat.shiftRight v14 (nat_lit 1280)) (Nat.shiftRight v14 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 504)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v14 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 504)) (nat_lit 4722366482869645213696)))));
  share v16 := (Nat.add (Nat.add (Nat.shiftRight v15 (nat_lit 640)) (Nat.shiftRight v15 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 432)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v15 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 432)) (nat_lit 4722366482869645213696)))));
  share v17 := (Nat.add (Nat.add (Nat.shiftRight v16 (nat_lit 320)) (Nat.shiftRight v16 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 360)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v16 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 360)) (nat_lit 4722366482869645213696)))));
  share v18 := (Nat.add (Nat.add (Nat.shiftRight v17 (nat_lit 160)) (Nat.shiftRight v17 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 288)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v17 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 288)) (nat_lit 4722366482869645213696)))));
  share v19 := (Nat.add (Nat.add (Nat.shiftRight v18 (nat_lit 80)) (Nat.shiftRight v18 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 216)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v18 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 216)) (nat_lit 4722366482869645213696)))));
  share v20 := (Nat.add (Nat.add (Nat.shiftRight v19 (nat_lit 40)) (Nat.shiftRight v19 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 144)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v19 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 144)) (nat_lit 4722366482869645213696)))));
  share v21 := (Nat.add (Nat.add (Nat.shiftRight v20 (nat_lit 20)) (Nat.shiftRight v20 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v7 (nat_lit 72)) (nat_lit 4722366482869645213696))))) (Nat.shiftRight v20 (Nat.shiftLeft (nat_lit 10) (Nat.mod (Nat.shiftRight v10 (nat_lit 72)) (nat_lit 4722366482869645213696)))));
  pickZ (Nat.add (Nat.add (Nat.add (Nat.add (nat_lit 0) (Nat.land v17 (eval% (Nat.mul (nat_lit 768) (Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 40960)) (nat_lit 1)) (nat_lit 1023)))))) (Nat.land v18 (eval% (Nat.mul (nat_lit 768) (Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 40960)) (nat_lit 1)) (nat_lit 1023)))))) (Nat.land v19 (eval% (Nat.mul (nat_lit 768) (Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 40960)) (nat_lit 1)) (nat_lit 1023)))))) (Nat.land v20 (eval% (Nat.mul (nat_lit 768) (Nat.div (Nat.sub (Nat.shiftLeft (nat_lit 1) (nat_lit 40960)) (nat_lit 1)) (nat_lit 1023))))))
    (Nat.add (Nat.add (Nat.shiftRight (Nat.land (nat_lit 1048575) v21) (nat_lit 10)) (Nat.land (nat_lit 1023) (Nat.shiftRight v21 (Nat.shiftLeft (nat_lit 10) (Nat.mod v7 (nat_lit 4722366482869645213696)))))) (Nat.land (nat_lit 1023) (Nat.shiftRight v21 (Nat.shiftLeft (nat_lit 10) (Nat.mod v10 (nat_lit 4722366482869645213696))))))
    (main (nat_lit 12) s)

/- `mainU12_eq : ∀ s, mainU12 s = mainS12 s` by `rfl`, checked by the kernel. -/
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ s, mainU12 s = mainS12 s)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) => @rfl Nat (mainU12 s))) none)
  addDecl (.thmDecl { name := `Submission.mainU12_eq, levelParams := [], type := ty, value := pf })

/-! ## Dimension 16 -/
def R_16 : Nat := nat_lit 792410683174719618142571720505663388360869145415628935849784770729038206636739624672674324645392283828538182961934658086718989816470611763197919760378504724216940161110135589588850855184192680067516067802108393823950972743052371474879246898325875055791210763247864193095570120770219029159388069332812088997296455239296354405443683535627202481764257460719843539509796755628363853516838732776920663601267852069365353492858366287653646410517766866028853493216372112039725133369267020824336255115570493268066510784466685799507010716400799822457858621889565830208660966947579868181222689014929178586924463159217995098337463330014190272481542326905724262895373108811848143077377
def Kc_16 : Nat := nat_lit 1807786524559845181626822831298290589613291078781722958591061239541658936200910550760228325219779552848138877491358778142309410780571924951667334933679955446267048700643706904305460332427126181847109692741867314043114262222913450452300494932634391174119092801406232506063037529309765852293593309916128914018516517359311532838265125227277935132539902981276698510639863495300995883496935083721655465847739528205874426979904382592959105027844393031522725372685878042903392106506724400262367747249144865966772092872377818383106538864715427887474961744241030516997196519217935506799032970317989638996248605496910567008524143737795399229417569489105363598666876615023153816079092276744064
def Mv_16 : Nat := nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215
def MvD_16 : Nat := nat_lit 55635907736909100174744216292761755673086900744109744494696699963363873391063016074143765629495550101296528430771105429223970849309479151161246791557619853853683694039856035484654422898649623958732407833788850179914748367621329025213432444868963248080262362971222576307600853665490375406617400149439392288861072264697661010289251844095
def g1_16 : Nat := nat_lit 220213651598353952767564312346801173268066949406100927264285516274397767009365889331903308373641099775705353775970442197431848049729979104114445076862373527731149981466029954544421365695756738135600727833164290752870682474077940082642726792582734240461012079723465745535549276241556615729372997427701589900313269925466981007392
def g0_16 : Nat := nat_lit 414519814773372146385998248065443343856424132284693409715543456502069580605273622781474637548749391173533699698329221791004829334306568412917308915118021946036233602862718221352356428771546202583933075253194263440199711174723282452103011470267045173988547359841798851658829061536705371585782192733102186111886170362637220577312
def g2_16 : Nat := nat_lit 233167395810021832342126757598846277763580203539997596317896249290087441403280690043824390797039518249878281891543230378400748966427059367018110980459811713544782281555489898961682504094867556966348636434826611485376923448288042659270945901028579402148154184718521959649887684414578658591428690950611033216309712749299394150433
def o_16 : Nat := nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041

noncomputable def K1_16 (s : Nat) : Nat :=
  vecK (nat_lit 2290649225) (nat_lit 35) (nat_lit 15) MvD_16 (Nat.mod (vecZ R_16 Kc_16 Mv_16 s) (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496))

noncomputable def K2_16 (s : Nat) : Nat :=
  vecK (nat_lit 4908534053) (nat_lit 36) (nat_lit 14) MvD_16 (Nat.shiftRight (vecZ R_16 Kc_16 Mv_16 s) (nat_lit 1152))

noncomputable def A_16 (s : Nat) : Nat := vecA (K1_16 s) (vecC g1_16 o_16 (K1_16 s))

noncomputable def B_16 (s : Nat) : Nat :=
  vecB g0_16 g2_16 o_16 (K1_16 s) (K2_16 s) (vecC g1_16 o_16 (K1_16 s))

noncomputable def mainS16 (s : Nat) : Nat := fast16 s (A_16 s) (B_16 s)

theorem R_16_eq : R_16 = enc 72 (fun _ => 1) (16 + 16) := by decide +kernel
theorem Kc_16_eq : Kc_16 = enc 72 (kcOf 16) (16 + 16) := by decide +kernel
theorem Mv_16_eq : Mv_16 = enc 72 (fun _ => 0xffffffff) (16 + 16) := by decide +kernel
theorem MvD_16_eq : MvD_16 = enc 72 (fun _ => 0xffffffff) 16 := by decide +kernel
theorem g1_16_eq : g1_16 = enc 72 (fun i => 32 - i) 16 := by decide +kernel
theorem g0_16_eq : g0_16 = enc 72 (fun _ => 32) 16 := by decide +kernel
theorem g2_16_eq : g2_16 = enc 72 (fun i => 33 - i) 16 := by decide +kernel
theorem o_16_eq : o_16 = enc 72 (fun _ => 1) 16 := by decide +kernel

theorem div_16a : ∀ x, x < 2 ^ 32 → x * 2290649225 / 2 ^ 35 = x / (16 - 1) := by
  intro x hx; omega

theorem div_16b : ∀ x, x < 2 ^ 32 → x * 4908534053 / 2 ^ 36 = x / (16 - 2) := by
  intro x hx; omega

theorem cols_16 (s : Nat) (hs : s < 2 ^ 32) :
    A_16 s = enc 72 (permanentColumnOne 16 s) 16 ∧ B_16 s = enc 72 (permanentColumnTwo 16 s) 16 :=
  cols_enc 16 s R_16 Kc_16 Mv_16 (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496) (nat_lit 1152) MvD_16 (nat_lit 2290649225) (nat_lit 35)
    (nat_lit 4908534053) (nat_lit 36) g1_16 g0_16 g2_16 o_16 (by decide) (by decide) hs R_16_eq Kc_16_eq
    Mv_16_eq (by decide +kernel) rfl MvD_16_eq (by decide) (by decide) div_16a (by decide) (by decide)
    div_16b g1_16_eq g0_16_eq g2_16_eq o_16_eq

theorem mainS16_eq (s : Nat) (hs : s < 2 ^ 32) :
    mainS16 s = permanentSpec (genPermanentMatrix 16 s) :=
  fast16_eq s (A_16 s) (B_16 s) (cols_16 s hs).1 (cols_16 s hs).2

/-- Part of the unrolled graph of `mainU16` (kept separate to keep each term small). -/
def a2U16 (s : Nat) : Nat :=
  share v1 := (Nat.land (Nat.mul (nat_lit 2146121005) (Nat.xor (Nat.mul (nat_lit 792410683174719618142571720505663388360869145415628935849784770729038206636739624672674324645392283828538182961934658086718989816470611763197919760378504724216940161110135589588850855184192680067516067802108393823950972743052371474879246898325875055791210763247864193095570120770219029159388069332812088997296455239296354405443683535627202481764257460719843539509796755628363853516838732776920663601267852069365353492858366287653646410517766866028853493216372112039725133369267020824336255115570493268066510784466685799507010716400799822457858621889565830208660966947579868181222689014929178586924463159217995098337463330014190272481542326905724262895373108811848143077377) (Nat.xor s (Nat.shiftRight s (nat_lit 16)))) (nat_lit 1807786524559845181626822831298290589613291078781722958591061239541658936200910550760228325219779552848138877491358778142309410780571924951667334933679955446267048700643706904305460332427126181847109692741867314043114262222913450452300494932634391174119092801406232506063037529309765852293593309916128914018516517359311532838265125227277935132539902981276698510639863495300995883496935083721655465847739528205874426979904382592959105027844393031522725372685878042903392106506724400262367747249144865966772092872377818383106538864715427887474961744241030516997196519217935506799032970317989638996248605496910567008524143737795399229417569489105363598666876615023153816079092276744064))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215));
  share v2 := (Nat.land (Nat.mul (nat_lit 2221713035) (Nat.land (Nat.xor v1 (Nat.shiftRight v1 (nat_lit 15))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215));
  share v3 := (Nat.mod (Nat.land (Nat.xor v2 (Nat.shiftRight v2 (nat_lit 16))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215)) (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496));
  share v4 := (Nat.sub v3 (Nat.mul (nat_lit 15) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 2290649225) v3) (nat_lit 35)) (nat_lit 55635907736909100174744216292761755673086900744109744494696699963363873391063016074143765629495550101296528430771105429223970849309479151161246791557619853853683694039856035484654422898649623958732407833788850179914748367621329025213432444868963248080262362971222576307600853665490375406617400149439392288861072264697661010289251844095))));
  (Nat.mul (nat_lit 32) (Nat.add v4 (Nat.land (Nat.shiftRight (Nat.add (nat_lit 220213651598353952767564312346801173268066949406100927264285516274397767009365889331903308373641099775705353775970442197431848049729979104114445076862373527731149981466029954544421365695756738135600727833164290752870682474077940082642726792582734240461012079723465745535549276241556615729372997427701589900313269925466981007392) v4) (nat_lit 5)) (nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041))))

/-- Part of the unrolled graph of `mainU16` (kept separate to keep each term small). -/
def b2U16 (s : Nat) : Nat :=
  share v1 := (Nat.land (Nat.mul (nat_lit 2146121005) (Nat.xor (Nat.mul (nat_lit 792410683174719618142571720505663388360869145415628935849784770729038206636739624672674324645392283828538182961934658086718989816470611763197919760378504724216940161110135589588850855184192680067516067802108393823950972743052371474879246898325875055791210763247864193095570120770219029159388069332812088997296455239296354405443683535627202481764257460719843539509796755628363853516838732776920663601267852069365353492858366287653646410517766866028853493216372112039725133369267020824336255115570493268066510784466685799507010716400799822457858621889565830208660966947579868181222689014929178586924463159217995098337463330014190272481542326905724262895373108811848143077377) (Nat.xor s (Nat.shiftRight s (nat_lit 16)))) (nat_lit 1807786524559845181626822831298290589613291078781722958591061239541658936200910550760228325219779552848138877491358778142309410780571924951667334933679955446267048700643706904305460332427126181847109692741867314043114262222913450452300494932634391174119092801406232506063037529309765852293593309916128914018516517359311532838265125227277935132539902981276698510639863495300995883496935083721655465847739528205874426979904382592959105027844393031522725372685878042903392106506724400262367747249144865966772092872377818383106538864715427887474961744241030516997196519217935506799032970317989638996248605496910567008524143737795399229417569489105363598666876615023153816079092276744064))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215));
  share v2 := (Nat.land (Nat.mul (nat_lit 2221713035) (Nat.land (Nat.xor v1 (Nat.shiftRight v1 (nat_lit 15))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215));
  share v3 := (Nat.land (Nat.xor v2 (Nat.shiftRight v2 (nat_lit 16))) (nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215));
  share v4 := (Nat.shiftRight v3 (nat_lit 1152));
  share v5 := (Nat.sub v4 (Nat.mul (nat_lit 14) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 4908534053) v4) (nat_lit 36)) (nat_lit 55635907736909100174744216292761755673086900744109744494696699963363873391063016074143765629495550101296528430771105429223970849309479151161246791557619853853683694039856035484654422898649623958732407833788850179914748367621329025213432444868963248080262362971222576307600853665490375406617400149439392288861072264697661010289251844095))));
  share v6 := (Nat.mod v3 (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496));
  share v7 := (Nat.sub v6 (Nat.mul (nat_lit 15) (Nat.land (Nat.shiftRight (Nat.mul (nat_lit 2290649225) v6) (nat_lit 35)) (nat_lit 55635907736909100174744216292761755673086900744109744494696699963363873391063016074143765629495550101296528430771105429223970849309479151161246791557619853853683694039856035484654422898649623958732407833788850179914748367621329025213432444868963248080262362971222576307600853665490375406617400149439392288861072264697661010289251844095))));
  (Nat.mul (nat_lit 32) (Nat.add (Nat.add v5 (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 414519814773372146385998248065443343856424132284693409715543456502069580605273622781474637548749391173533699698329221791004829334306568412917308915118021946036233602862718221352356428771546202583933075253194263440199711174723282452103011470267045173988547359841798851658829061536705371585782192733102186111886170362637220577312) v5) v7) (nat_lit 5)) (nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041))) (Nat.land (Nat.shiftRight (Nat.sub (Nat.add (nat_lit 233167395810021832342126757598846277763580203539997596317896249290087441403280690043824390797039518249878281891543230378400748966427059367018110980459811713544782281555489898961682504094867556966348636434826611485376923448288042659270945901028579402148154184718521959649887684414578658591428690950611033216309712749299394150433) v5) (Nat.land (Nat.shiftRight (Nat.add (nat_lit 220213651598353952767564312346801173268066949406100927264285516274397767009365889331903308373641099775705353775970442197431848049729979104114445076862373527731149981466029954544421365695756738135600727833164290752870682474077940082642726792582734240461012079723465745535549276241556615729372997427701589900313269925466981007392) v7) (nat_lit 5)) (nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041))) (nat_lit 5)) (nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041))))

/-- Part of the unrolled graph of `mainU16` (kept separate to keep each term small). -/
def lsU16 (s : Nat) : Nat :=
  share v1 := (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 288)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 288)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 216)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 216)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 144)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 144)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 72)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 72)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 0)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 0)) (nat_lit 4722366482869645213696))) (nat_lit 340282367000166625996085689103316680705)))))))))));
  share v2 := (Nat.mod (Nat.mul v1 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096));
  share v3 := (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 576)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 576)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 504)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 504)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 432)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 432)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 360)) (nat_lit 4722366482869645213696))) (Nat.lor (Nat.shiftLeft (nat_lit 1) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 360)) (nat_lit 4722366482869645213696))) (Nat.lor v1 (nat_lit 115792089264276142096998726540203105341796590047689226336812880642240023625729))))))))));
  share v4 := (Nat.sub v3 v1);
  share v5 := (Nat.mod (Nat.mul v4 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096));
  share v6 := (Nat.shiftRight v2 (nat_lit 480));
  share v7 := (Nat.sub (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041) v3);
  share v8 := (Nat.sub (Nat.add (Nat.add (Nat.land v2 (Nat.mul v1 (nat_lit 4294967295))) (Nat.land (Nat.add v5 (Nat.mul v6 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041))) (Nat.mul v4 (nat_lit 4294967295)))) (Nat.land (Nat.add (Nat.mod (Nat.mul v7 (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084096)) (Nat.mul (Nat.add v6 (Nat.shiftRight v5 (nat_lit 480))) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041))) (Nat.mul v7 (nat_lit 4294967295)))) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041));
  share v9 := (Nat.add (nat_lit 37460982612513971470157213380706349134086337634640526531106620993411119411302191003441038211212465386719640271029778030066477280065844794600980492) (Nat.land (Nat.mul (nat_lit 37460982612513971470157213380706349134086337634640526531106620993411119411302191003441038211212465386719640271029778030066477280065844794600980492) (nat_lit 1)) (Nat.mul (Nat.land (Nat.shiftRight v8 (nat_lit 0)) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 4294967295))));
  share v10 := (Nat.add v9 (Nat.land (Nat.mul v9 (nat_lit 3)) (Nat.mul (Nat.land (Nat.shiftRight v8 (nat_lit 1)) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 4294967295))));
  share v11 := (Nat.add v10 (Nat.land (Nat.mul v10 (nat_lit 15)) (Nat.mul (Nat.land (Nat.shiftRight v8 (nat_lit 2)) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 4294967295))));
  (Nat.add v11 (Nat.land (Nat.mul v11 (nat_lit 255)) (Nat.mul (Nat.land (Nat.shiftRight v8 (nat_lit 3)) (nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041)) (nat_lit 4294967295))))

/-- `mainS16` as one shared graph (`mainU16_eq`, by `rfl`). -/
def mainU16 (s : Nat) : Nat :=
  share v1 := (Nat.shiftLeft (nat_lit 1) (nat_lit 786420));
  share v2 := (Nat.add (Nat.add (Nat.shiftRight v1 (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 480)) (nat_lit 4294967296))) (Nat.shiftRight v1 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 1080)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) (Nat.shiftRight v1 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 1080)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296))));
  share v3 := (Nat.add (Nat.add (Nat.shiftRight v2 (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 448)) (nat_lit 4294967296))) (Nat.shiftRight v2 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 1008)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) (Nat.shiftRight v2 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 1008)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296))));
  share v4 := (Nat.add (Nat.add (Nat.shiftRight v3 (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 416)) (nat_lit 4294967296))) (Nat.shiftRight v3 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 936)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) (Nat.shiftRight v3 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 936)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296))));
  share v5 := (Nat.add (Nat.add (Nat.shiftRight v4 (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 384)) (nat_lit 4294967296))) (Nat.shiftRight v4 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 864)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) (Nat.shiftRight v4 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 864)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296))));
  share v6 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 0)) (nat_lit 4294967296));
  share v7 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 0)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v8 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 0)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v9 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 32)) (nat_lit 4294967296));
  share v10 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 72)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v11 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 72)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v12 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 64)) (nat_lit 4294967296));
  share v13 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 144)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v14 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 144)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v15 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 96)) (nat_lit 4294967296));
  share v16 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 216)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v17 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 216)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v18 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 128)) (nat_lit 4294967296));
  share v19 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 288)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v20 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 288)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v21 := (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor v6 v7) v8) v9) v10) v11) v12) v13) v14) v15) v16) v17) v18) v19) v20);
  share v22 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 160)) (nat_lit 4294967296));
  share v23 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 360)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v24 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 360)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v25 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 192)) (nat_lit 4294967296));
  share v26 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 432)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v27 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 432)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v28 := (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor v21 v22) v23) v24) v25) v26) v27);
  share v29 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 224)) (nat_lit 4294967296));
  share v30 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 504)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v31 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 504)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v32 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 256)) (nat_lit 4294967296));
  share v33 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 576)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v34 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 576)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v35 := (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor v28 v29) v30) v31) v32) v33) v34);
  share v36 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 288)) (nat_lit 4294967296));
  share v37 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 648)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v38 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 648)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v39 := (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 320)) (nat_lit 4294967296));
  share v40 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 720)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v41 := (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 720)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296));
  share v42 := (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor (Nat.lor v35 v36) v37) v38) v39) v40) v41);
  share v43 := (Nat.mul (nat_lit 12) (Nat.add (Nat.shiftRight (Nat.land v42 (Nat.shiftRight v42 (nat_lit 1))) (nat_lit 2)) (nat_lit 1)));
  share v44 := (Nat.sub (Nat.shiftLeft (nat_lit 1) v43) (nat_lit 1));
  share v45 := (Nat.land (Nat.add (Nat.add (Nat.shiftRight v5 (Nat.mod (Nat.shiftRight (lsU16 s) (nat_lit 352)) (nat_lit 4294967296))) (Nat.shiftRight v5 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (a2U16 s) (nat_lit 792)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) (Nat.shiftRight v5 (Nat.mod (Nat.shiftRight (lsU16 s) (Nat.mod (Nat.shiftRight (b2U16 s) (nat_lit 792)) (nat_lit 4722366482869645213696))) (nat_lit 4294967296)))) v44);
  share v46 := (Nat.add (Nat.add (Nat.shiftRight v45 v39) (Nat.shiftRight v45 v40)) (Nat.shiftRight v45 v41));
  share v47 := (Nat.mul (nat_lit 12) (Nat.add (Nat.shiftRight (Nat.land v35 (Nat.shiftRight v35 (nat_lit 1))) (nat_lit 2)) (nat_lit 1)));
  share v48 := (Nat.shiftRight v44 (Nat.sub v43 v47));
  share v49 := (Nat.land (Nat.add (Nat.add (Nat.shiftRight v46 v36) (Nat.shiftRight v46 v37)) (Nat.shiftRight v46 v38)) v48);
  share v50 := (Nat.add (Nat.add (Nat.shiftRight v49 v32) (Nat.shiftRight v49 v33)) (Nat.shiftRight v49 v34));
  share v51 := (Nat.mul (nat_lit 12) (Nat.add (Nat.shiftRight (Nat.land v28 (Nat.shiftRight v28 (nat_lit 1))) (nat_lit 2)) (nat_lit 1)));
  share v52 := (Nat.shiftRight v48 (Nat.sub v47 v51));
  share v53 := (Nat.land (Nat.add (Nat.add (Nat.shiftRight v50 v29) (Nat.shiftRight v50 v30)) (Nat.shiftRight v50 v31)) v52);
  share v54 := (Nat.add (Nat.add (Nat.shiftRight v53 v25) (Nat.shiftRight v53 v26)) (Nat.shiftRight v53 v27));
  share v55 := (Nat.land (Nat.add (Nat.add (Nat.shiftRight v54 v22) (Nat.shiftRight v54 v23)) (Nat.shiftRight v54 v24)) (Nat.shiftRight v52 (Nat.sub v51 (Nat.mul (nat_lit 12) (Nat.add (Nat.shiftRight (Nat.land v21 (Nat.shiftRight v21 (nat_lit 1))) (nat_lit 2)) (nat_lit 1))))));
  share v56 := (Nat.add (Nat.add (Nat.shiftRight v55 v18) (Nat.shiftRight v55 v19)) (Nat.shiftRight v55 v20));
  share v57 := (Nat.add (Nat.add (Nat.shiftRight v56 v15) (Nat.shiftRight v56 v16)) (Nat.shiftRight v56 v17));
  share v58 := (Nat.add (Nat.add (Nat.shiftRight v57 v12) (Nat.shiftRight v57 v13)) (Nat.shiftRight v57 v14));
  share v59 := (Nat.add (Nat.add (Nat.shiftRight v58 v9) (Nat.shiftRight v58 v10)) (Nat.shiftRight v58 v11));
  share v60 := (Nat.mul (Nat.div v48 (nat_lit 4095)) (nat_lit 3072));
  pickZ (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.xor (Nat.mod (lsU16 s) (nat_lit 4294967295)) (nat_lit 786420)) (Nat.land v50 v60)) (Nat.land v53 v60)) (Nat.land v54 v60)) (Nat.land v55 v60)) (Nat.land v56 v60)) (Nat.land v57 v60)) (Nat.land v58 v60))
    (Nat.add (Nat.add (Nat.land (nat_lit 4095) (Nat.shiftRight v59 v6)) (Nat.land (nat_lit 4095) (Nat.shiftRight v59 v7))) (Nat.land (nat_lit 4095) (Nat.shiftRight v59 v8)))
    (main (nat_lit 16) s)

/- `mainU16_eq : ∀ s, mainU16 s = mainS16 s` by `rfl`, checked by the kernel. -/
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(∀ s, mainU16 s = mainS16 s)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun (s : Nat) => @rfl Nat (mainU16 s))) none)
  addDecl (.thmDecl { name := `Submission.mainU16_eq, levelParams := [], type := ty, value := pf })

/-- Dimensions `6, 12, 16` (the tested scales) use the unrolled graphs; everything else `implOld`. -/
def impl (n : Nat) : Nat :=
  share d := Nat.shiftRight n (nat_lit 32);
  share s := Nat.land n (nat_lit 0xffffffff);
  Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU6 s)
    (fun _ _ d s n => Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU12 s)
      (fun _ _ d s n => Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU16 s)
        (fun _ _ _ _ n => implOld n) (Nat.xor d (nat_lit 16)) d s n)
      (Nat.xor d (nat_lit 12)) d s n)
    (Nat.xor d (nat_lit 6)) d s n

theorem rec3_eq (x d s n : Nat) (z f : Nat → Nat → Nat → Nat) :
    Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) z (fun _ _ => f) x d s n
      = if x = 0 then z d s n else f d s n := by
  cases x <;> rfl

theorem impl_correct : ∀ n, impl n = permanentSpecN n := by
  intro n
  have hs : Nat.land n (nat_lit 0xffffffff) < 2 ^ 32 := Nat.and_lt_two_pow _ (by decide)
  have hspec : ∀ D, Nat.shiftRight n (nat_lit 32) = D →
      permanentSpec (genPermanentMatrix D (Nat.land n (nat_lit 0xffffffff))) = permanentSpecN n := by
    intro D h
    unfold permanentSpecN permanentDimension permanentSeed
    rw [show n >>> 32 = D from h]
    rfl
  show Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU6 s)
    (fun _ _ d s n => Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU12 s)
      (fun _ _ d s n => Nat.rec (motive := fun _ => Nat → Nat → Nat → Nat) (fun _ s _ => mainU16 s)
        (fun _ _ _ _ n => implOld n) (Nat.xor d (nat_lit 16)) d s n)
      (Nat.xor d (nat_lit 12)) d s n)
    (Nat.xor (Nat.shiftRight n (nat_lit 32)) (nat_lit 6)) (Nat.shiftRight n (nat_lit 32))
      (Nat.land n (nat_lit 0xffffffff)) n = _
  simp only [rec3_eq]
  by_cases h6 : Nat.xor (Nat.shiftRight n (nat_lit 32)) (nat_lit 6) = 0
  · rw [if_pos h6, mainU6_eq, mainS6_eq _ hs]; exact hspec 6 (xor_zero_eq h6)
  rw [if_neg h6]
  by_cases h12 : Nat.xor (Nat.shiftRight n (nat_lit 32)) (nat_lit 12) = 0
  · rw [if_pos h12, mainU12_eq, mainS12_eq _ hs]; exact hspec 12 (xor_zero_eq h12)
  rw [if_neg h12]
  by_cases h16 : Nat.xor (Nat.shiftRight n (nat_lit 32)) (nat_lit 16) = 0
  · rw [if_pos h16, mainU16_eq, mainS16_eq _ hs]; exact hspec 16 (xor_zero_eq h16)
  rw [if_neg h16]
  exact implOld_correct n

end Submission
