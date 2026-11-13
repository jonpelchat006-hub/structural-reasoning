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

end Submission


/-! # The flattening command (used once, for the dimension-16 fast path) -/

section FlatSec
open Lean Meta Elab Command


namespace Flat

/-- Is `e` a closed natural-number literal? -/
def litVal? (e : Expr) : Option Nat :=
  match e with
  | .lit (.natVal n) => some n
  | _ => none

def binOps : List (Name × (Nat → Nat → Nat)) :=
  [(``Nat.add, (· + ·)), (``Nat.sub, (· - ·)), (``Nat.mul, (· * ·)), (``Nat.div, (· / ·)),
   (``Nat.mod, (· % ·)), (``Nat.land, (· &&& ·)), (``Nat.lor, (· ||| ·)), (``Nat.xor, (· ^^^ ·)),
   (``Nat.shiftLeft, (· <<< ·)), (``Nat.shiftRight, (· >>> ·)), (``Nat.pow, (· ^ ·))]

/-- Fold `op lit lit` to a literal. -/
def fold? (e : Expr) : Option Expr := do
  let fn := e.getAppFn
  let .const c _ := fn | none
  let args := e.getAppArgs
  guard (args.size == 2)
  let f ← binOps.lookup c
  let a ← litVal? args[0]!
  let b ← litVal? args[1]!
  some (mkRawNatLit (f a b))

/-- Flatten: unfold the given constants, unroll `Nat.rec` on literals, beta/zeta, fold literal arithmetic.
Shares results through a pointer cache. -/
partial def go (unfold : NameSet) (evs : Std.HashMap Name Nat) (cache : IO.Ref (Std.HashMap Expr Expr)) (e : Expr) :
    MetaM Expr := do
  if let some v := (← cache.get)[e]? then return v
  let r ← match e with
    | .const c _ => pure ((evs[c]?.map mkRawNatLit).getD e)
    | .lit _ | .bvar _ | .fvar _ | .sort _ | .mvar _ => pure e
    | .mdata _ b => go unfold evs cache b
    | .letE _ _ v b _ => go unfold evs cache (b.instantiate1 v)
    | .lam n t b bi => do pure (.lam n t (← go unfold evs cache b) bi)
    | .forallE .. => pure e
    | .proj .. => pure e
    | .app .. => do
      let fn := e.getAppFn
      let args := e.getAppArgs
      if fn.isLambda then go unfold evs cache (fn.betaRev args.reverse)
      else match fn with
      | .const c lvls => do
        if unfold.contains c then
          let some ci := (← getEnv).find? c | throwError "flatten: unknown {c}"
          let some v := ci.value? (allowOpaque := true) | throwError "flatten: no value {c}"
          go unfold evs cache ((v.instantiateLevelParams ci.levelParams lvls).betaRev args.reverse)
        else if c == ``OfNat.ofNat && args.size == 3 && (litVal? args[1]!).isSome then pure args[1]!
        else if c == ``Nat.rec && args.size ≥ 4 then do
          let n ← go unfold evs cache args[3]!
          match litVal? n with
          | some 0 => go unfold evs cache (mkAppN args[1]! (args.extract 4 args.size))
          | some (k + 1) =>
            let kE := mkRawNatLit k
            let recK := mkAppN fn (#[args[0]!, args[1]!, args[2]!, kE])
            go unfold evs cache (mkAppN (mkAppN args[2]! #[kE, recK]) (args.extract 4 args.size))
          | none => do
            let args' ← args.mapM (go unfold evs cache)
            pure (mkAppN fn args')
        else do
          let args' ← args.mapM (go unfold evs cache)
          let e' := mkAppN fn args'
          pure ((fold? e').getD e')
      | _ => do
        let args' ← args.mapM (go unfold evs cache)
        pure (mkAppN (← go unfold evs cache fn) args')
  cache.modify fun m => m.insert e r
  return r

def flatten (unfold : NameSet) (evs : Std.HashMap Name Nat) (e : Expr) : MetaM Expr := do
  let cache ← IO.mkRef (∅ : Std.HashMap Expr Expr)
  go unfold evs cache e

/-- `#flatten src tgt [c1, c2, ...]` defines `tgt` as the flattened body of `src : Nat → Nat` and proves
`∀ s, tgt s = src s` by `rfl` (kernel). -/
elab "#flatten " src:ident tgt:ident " [" cs:ident,* "]" " [" es:ident,* "]" : command => do
  liftTermElabM do
    let srcN ← realizeGlobalConstNoOverload src
    let tgtN := (← getCurrNamespace) ++ tgt.getId
    let unfold ← cs.getElems.foldlM (fun s c => do return s.insert (← realizeGlobalConstNoOverload c)) (NameSet.empty.insert srcN)
    let mut evs0 : Std.HashMap Name Nat := {}
    for c in es.getElems do
      let n ← realizeGlobalConstNoOverload c
      let v ← unsafe Meta.evalExpr Nat (mkConst ``Nat) (mkConst n)
      evs0 := evs0.insert n v
    let evs := evs0
    let body ← withLocalDeclD `s (mkConst ``Nat) fun s => do
      let b ← flatten unfold evs (mkApp (mkConst srcN) s)
      mkLambdaFVars #[s] b
    let ty := mkForall `s .default (mkConst ``Nat) (mkConst ``Nat)
    let h := match (← getEnv).find? srcN with
      | some (.defnInfo v) => match v.hints with | .regular h => h + 1 | _ => 1000
      | _ => 1000
    let decl := Declaration.defnDecl (mkDefinitionValEx tgtN [] ty body (.regular h) .safe [tgtN])
    addDecl decl
    compileDecl decl
    let eqTy ← withLocalDeclD `s (mkConst ``Nat) fun s => do
      mkForallFVars #[s] (← mkEq (mkApp (mkConst tgtN) s) (mkApp (mkConst srcN) s))
    let pf ← withLocalDeclD `s (mkConst ``Nat) fun s => do
      mkLambdaFVars #[s] (← mkEqRefl (mkApp (mkConst tgtN) s))
    if (← getEnv).contains `Flat.skipEq then pure () else
    addDecl (.thmDecl { name := tgtN ++ `eq, levelParams := [], type := eqTy, value := pf })

end Flat

end FlatSec


namespace Submission
namespace P8

def R_16 : Nat := nat_lit 792410683174719618142571720505663388360869145415628935849784770729038206636739624672674324645392283828538182961934658086718989816470611763197919760378504724216940161110135589588850855184192680067516067802108393823950972743052371474879246898325875055791210763247864193095570120770219029159388069332812088997296455239296354405443683535627202481764257460719843539509796755628363853516838732776920663601267852069365353492858366287653646410517766866028853493216372112039725133369267020824336255115570493268066510784466685799507010716400799822457858621889565830208660966947579868181222689014929178586924463159217995098337463330014190272481542326905724262895373108811848143077377
def Kc_16 : Nat := nat_lit 1807786524559845181626822831298290589613291078781722958591061239541658936200910550760228325219779552848138877491358778142309410780571924951667334933679955446267048700643706904305460332427126181847109692741867314043114262222913450452300494932634391174119092801406232506063037529309765852293593309916128914018516517359311532838265125227277935132539902981276698510639863495300995883496935083721655465847739528205874426979904382592959105027844393031522725372685878042903392106506724400262367747249144865966772092872377818383106538864715427887474961744241030516997196519217935506799032970317989638996248605496910567008524143737795399229417569489105363598666876615023153816079092276744064
def Mv_16 : Nat := nat_lit 3403377968444027530717234186763705115288816637334725461330478623070292404310248633399711304538172331488928883480235586409465335117179329851577349982859914611514752476940063250299656919648888761868379903097058083518849415614846373956797279502539823616879550576601564687947038478087290940226223099997620392624017618672209240984109790749848801971520319693751475159711617397520929925214993089066118780977142345172822264657940699272602973620667952706028572279710822579760695188610515012562608155804151713853363331704049209525923538150155955349298309296749456342495721878782931513238762582431076588772054883904273666722829713875672739106215362785218284257423609509169364083023814869385215
def MvD_16 : Nat := nat_lit 55635907736909100174744216292761755673086900744109744494696699963363873391063016074143765629495550101296528430771105429223970849309479151161246791557619853853683694039856035484654422898649623958732407833788850179914748367621329025213432444868963248080262362971222576307600853665490375406617400149439392288861072264697661010289251844095
def g1_16 : Nat := nat_lit 220213651598353952767564312346801173268066949406100927264285516274397767009365889331903308373641099775705353775970442197431848049729979104114445076862373527731149981466029954544421365695756738135600727833164290752870682474077940082642726792582734240461012079723465745535549276241556615729372997427701589900313269925466981007392
def g0_16 : Nat := nat_lit 414519814773372146385998248065443343856424132284693409715543456502069580605273622781474637548749391173533699698329221791004829334306568412917308915118021946036233602862718221352356428771546202583933075253194263440199711174723282452103011470267045173988547359841798851658829061536705371585782192733102186111886170362637220577312
def g2_16 : Nat := nat_lit 233167395810021832342126757598846277763580203539997596317896249290087441403280690043824390797039518249878281891543230378400748966427059367018110980459811713544782281555489898961682504094867556966348636434826611485376923448288042659270945901028579402148154184718521959649887684414578658591428690950611033216309712749299394150433
def o_16 : Nat := nat_lit 12953744211667879574562445252045104495513254133896669053610733015689674393914800711921082423398418474172928115572788180968900916697080262903665903597438185813632300089459944417261138399110818830747908601662320732506240974210102576628219108445845161687142104995056214114338408173022042862055693522909443315996442823832413143041
/-! Literal constants for dimension 16 (generated). -/
def c16_MSP : Nat := nat_lit 6280169744314813970682846465436021536748048475744209938874822610089805348303977270306564710906208723937989904407137837102692172783558057971689944046116267623228040895618715322122156602525023166274566301572453736727034551897632101196794782039610892839180998486999360476151717171058821875704320480187345470970941228305352891611711346426603037892467412114815468270758701060929682344816448082987014811014713807044844862680510747331012305930648114250857212302589105148457355363494095991195185667584282110199677807499357593381583510634327369556112342887387479613045699723220511222745288400415058188397313061844677793806654579463991857220487322184172204461689874993503960032787035464140036617255943995256335694093089106497210278241244476463871721114436123034325645255796193446177982592099258845553026460479632128035084791135006139602139063158042105473858298366577053847359454055253477417635014930767795698088035396638242664252997210774139520703545564762178178657200260875464826340860292449384357454344714533264054449310780283243267637825498172233743626854349443868588540611616084219770110698869470919860974399885656059529019546594549945920441509851699144555662479046116421545583598445258467776208268571677864741374970875560008835693517593145150474635551767673552332068579850512283783998021990531969372988284573495864509499921252883702008042817589424618774876507304100550127479917764999272207837053229981741110009353706378829951810367587033189341677138204830312946286401273665691091965970734234022693316495566421124313712149343564385559281562525682710778729555556481797550481710916747391746986005042215119451532620895407112085983206881372602860904904042818609026872534320855345547134569372923654807003520407676481813229125012589380748695634406597505028829668734048918493135944668291899024389973245372163500748865791534717905515991444106765967045526451835239638555272406120115369759468800272157595194011067164784614588743424239476786261919836768318135687817473358716104909203822737152740572528641
def c16_M4 : Nat := nat_lit 141298271255464358948306400375751531633413326263844849568058131217975351771404075357670095439017909697928328899286359544686712229294921924517651963705143917833989106045956321481882259741801374257013436051443482666623156952628607916377303190310682300817307450238924415776495958905057044622160948819291085449191786199126327211978184414715818146459678338016216975523203091929388718289860233999880891187426604242382049937688990672533622057161101319617705478888782075736540343055496164716593278378181727033624015522857609805500503716700635969123481831408937688737868881580752922902777619215445611962109398160822273134943322507274279856468515701606406498562175234596849709364655541097099124693741813722611868723565814294752083427886418415444639487260157235939706872870629708467256861210763684367410954963008934988201241810566009986639107820356678727655233049597680675638903335360073680507762679817463723568331748084246560521430425106758397796429414923047468692710146729617957903376292424747971602927156059446726195121524441995687261843793279104499715321469011337582511529396861464912839323153906942188809073512055560217194013307258128387637338258514456713852525092833116459831025394120595506929141679244753918696769013496911765487328818148202767630566161067704899199134543449789047833984875295432254760266616823185956380680722975623372668969737921550142957257608809034559532074862372681825598823873608468191148124973398925338475097329427735490928543390344475295067420589074536024441049486702527155572679137876991575995447679136424296461410371880145767073261979451084800668456329264062341566762480924310580584139746442680494986568028142816905644678868516965272846646722409127894779823766937079488819339879219438200226988408504314027787790605934270066575741408756517026963922799915695400902125742031664143653444902797779646132123876399982321830467975527787554639127754784453585863329626839779902654398738027010403115955180161629364431552212549279471167911766609401213344942626578364773311812349231762228480637726461264856825479505510089440852321003133919879687519708945572909695392451308215236844954917294941771258433887466617651452550930128785569337348764499579070360569193482092813463355191906373577959027139572493977268965641252125406854201512550598521611546653980963892958281270142796922942992952669188430655241607934921626895066179410420345800900669663625855231334888736035766987127634777866255
def c16_REP16 : Nat := nat_lit 1766874025136433896750911497805568136923323180981774075523881651146915841
def c16_CPAT : Nat := nat_lit 249655991310621099328280119504482889699791155501438159320058820825319042874483187860097453392521406494250024480431210327987001521460358298657076527190702471848864354743728797087652944609861711899507324704162831906111849221801893749003418331726464007336784972594325889824049105789238003033925466690662198306546564186329772142770483674539501448951249894151599931506526752459410816981396361729543966376820057611575248584230832740959194965722395738905085781699253690238665142239743713114724086338440941854790225248527155806533959753650057762865801813879238631242047322761804905405099652975633603558334752845345515963984993694515318137041552924094506505698511857337204632487882232378910726678713645141128981084635750156699375988589893036478505005404676636565345659521494073613026067386894245702231200686867660762648301798513899737050423444243757138220773035734702906435552557994011535908666015659784274451931301764320860046644856724133167548309228178336030802903550774116660333303062305719015761026591403892524323544455623673178175064609826287189296931901780324164753784637979240589828058745808779863002955964115593042893820962480142622573496486365614097674937694231638890245460514931158059984647467637835548721362214507287318011799634358619200968445705566492340822749296741015448298567231655837862656613534172003379175138304335345832582119256168607928055086801844830915387210964971361662998007522768722803909842734125216675210294945068926010233549030080019046599721983843440439172465393782424610379761703703149068649529430195252313190168062897286269584824286539733213704181376124982184231733435692042291734799832896190493288579193796585944616343976817715144098235954741579786868648694794517964583296256285327804386037164137023535164837605648729070608075306509350287313903980558298388505510258011235488360461169107707120161447268790137904214833142451035109331376154097169882632919029988237033578077242851385815001425760056396703480754783487582744911395107163497465849611380711817135839398354508969802081347445780263917197320271993501654352247064277942411541407620879485549204677919854543767474841903183264024042661290189584458543713232309068810921697480545455636269117221802692500957315566231533800801546648835655753670152868768469231773815930875922069969829995481797344874045433215716812771573191884037151277814176262757175710322349137401040043025645115709906330990804836378828070761877565083071089970636365476318840098132800694556669808964582007559779889630941347840
def c16_K15 : Nat := nat_lit 249656245277961988890589206851403722235812351109231561554550878047544365266449827241076730264408786272363765574767000520281499386627874585399629151997609246756444563708444264028063590118573633591141417169510560356322244573726098548894779252438060494625291886595513828610668363378353521592309660173450647963458572128678296098400321655382137792366085153420359635121064069295666902329902515004719046851533519205007513193136850678898127776708286696729990042015526675953858407517237867963267969219309887669115528432692212718717104057652333533188782962165471663806019056507137526147184709750734978373919672720430595443234725415908846181421274212127791601220148416164262982450079226055218957749946479287120078607460816873813560581640514166928511193610835302090381649843764590380177045518140617983609548414242072957074529862636073761412699177549875980102214496974371028224062157223684312007443551912252783485778111411059960476764124327022986354724255538667433858314892410408037448290326090827983369190194876228597255802041067992803040458630422185308162659333573671005071639651641308889374123446278305263042900882505450920138982269505666209730374028547836080226220517201608820342659871492464846181713745200287236351925175279433548398744786662275092132693650722866586989913024668745417203445597049781149137528404360771711137630660655972035062878012787531750854085311879984805744759939304740909472519749444729858415980128865250876221041268834372351699329845554750199765704725404181690606185020633670764714950649450590493661750691156515398982165116314738645833907246907434611939346073340075704956525815705724062732810412733389599168211955954501294830717095930482068118075785749022079844707796518129709189780735003859600412699861258627753962313169307446561414763780946429662871841736366816845112047711517682881517742940266370753385107067111164334765331189363769488053253643725379967578540070573802822167873081096658007408392135178623232838969084166616966176970615107431415599590403840013680024164936113764723568484256796113979649893668708135521971187022168125178295869925370559186562355366665909994856938644635980358367123770785419399365487210765229779425269921725182289953917134967116852371076392389762659559194031536146052062302269569097471983725358019954323950459721863782911676175930142750187148166711597626900898008200610052311109691973455714165641945621154263218314359718620337438810619283789295914659446833194613551248244857282923050257832215744486609564318074038845455
def c16_ONESUB : Nat := nat_lit 16643749685197465926039280456760248149054156740615437436970058536502957684429988482738448684293919084824251038317800034685433292441858305693308610133173949783762970913896284268537572674571575572742761144634037357088149638248406569926318616829204032975019459106367588574044557558556901439487310678230043197563904808578553073226688110358809186157739010228023975674737604619711126821993501000314603123435567947000500879542456711926541851780552446448666002801035111730257227167815857864217864614620659177941035228846147514581140270510155568879252197477698110920401270433809168409812313983382331891594644848028706362882315027727256412094751614141852773414676561077617532163338615070347930516663098619141338573830721124920904038776034277795234079574055686806025443322917639358678469701209374532240636560949471530471635324175738250760846611836658398673480966464958068548270810481578954133829570127483518899051874094070664031784274955134865756981617035911162257220992827360535829886021739388532224612679658415239817053469404532853536030575361479020544177288904911400338109310109420592624941563085220350869526725500363394675932151300377747315358268569855738681748034480107254689510658099497656412114249680019149090128345018628903226582985777485006142179576714857772465994201644583027813563039803318743275835226957384780742508710710398135670858534185835450056939020791998987049650662620316060631501316629648657227732008591016725081402751255624823446621989703650013317713648360278779373745668042244717647663376630039366244116712743767693265477674420982576388927149793828974129289738222671713663768387713714937515520694182225973277880797063633419655381139728698804541205052383268138656313853101208647279318715666923973360846657417241850264154211287163104094317585396428644191456115757787789674136514101178858767849529351091383559007137807410955651022079290917965870216909581691997838569338038253521477858205406443867160559475678574882189264605611107797745131374340495427706639360256000912001610995740917648237898950453074265309992911247209034798079134811208345219724661691370612437490357777727332990462576309065357224474918052361293291032480717681985295017994781678819330261142331141123491405092825984177303946268769076403470820151304606498132248357201330288263363981457585527445078395342850012476544447439841793393200546707336820740646131563714277709463041410284214554290647908022495920707952252619727643963122212974236749882990485528203350522147716299107304287871602589697
def c16_LOW : Nat := nat_lit 9419884750364290596553760025050102108894221750922989971203875414531690118093442320419725609730398105453045650810714532290728065973214474103019890269844560827664532061996139090430180313383641889043080006223018139191082583097301068144950789780776908116783196959428252122736517016077795177203150458324995573240833195900781795313468279322108120806112773181505864854613342274783473007736322103467786361664230540552632979978077664835829155773428105086523006507933578158177903021877623266077701934954777760645552335617564688277440114940323914082236715094008135149491534798475924364839902672291418288292158254791507011178710186377143413590606596055863560951340226503481143015154542400279744889738235166830510062523508976315557968937658671557814986271566300192402387094190306660603847947996219065856724348548388605346308860955717420194116605624901524785797612525391702038325952564811057877614448040438422628995406552393549463655364738893881036628339830776315511617830142989138198612692412165166110928117390511745214880681685872200907578959178979821238342219820902485776402036806202685786329205479088993193244158939485554584625484034139535899250054280756020171138042132199823717934843841882268847521546652081091707497022458425371044978909687044353355420794638873223054597529774663733146245930198287980746081914600600509088957183969701642656240827492014166754955537839617629024572735104422962634792544269681887628491464155770412086525867026493564344227992921597235673402223237473437238344698049516453943845771710216647953088346101478214924253068266712942415510643595621208813308551715833427607668086162759809397940578726961863084569486084540095075238859255851344676346598010308191184349318668834210122684273907800039545419416945376959861807021571473653801637760597284266408517101281173682921273863173311688047673987863007947053596402750595126995919541630346232227174442667708365287089858863756540233019767469638218639677566292375359787556550605367720889406056294513447033557208628884608503856285532165971337535312193398968276645187142890535109724382318632065386887531902882686538010563685413294324431563286716630678290780301911913824736734414968290594099276926492066461693976389272949297355166256081573074007849432510064705380888672564746002741039826920514805172061414535034476617260751006763322427989547610504892757734642584663668822534661521961066366606089781344033103116930730050418865855409422335
def c16_DIAG : Nat := nat_lit 143736034398869180245266113663484224073703334822433318652402884132868806733604792360415639030443258300640876089196308150760718393398609942658971312333583734727104523526898124274896530890325661917121736976505480082431519919293445983179247964409750726357369334631945992842497722699843233819650159040111946118715329001880524882828364190400163660831866996553026734507222585880010075276804322152868174555566567817257487142206659940852997979189981733534756673492593016955443874136911375042970193095509050187063785147118683672617021600398941564464741890814416738527905254744317635404878420333813644299360602600839104021649261691916852423791692996484634301309965268859023519468920868674004361718641831617887616308840647432608206551550543016021384890877008174978234313118412951596905946434540198064458013307345781040401026589749745537735600967006177728555594604431777124333009576795910580383144201669245279751339970174441561086255829418593250468609024802995687361750240917451027145076936894882548466701015543262863542647187685567228362361454160057191620781930975579138871831812948992648741914543880255121882768448549045728702477023779754932539096585159646475990444273840403880009870990314699317202173281795823416800016954399910939656490297449613790667930121869105219866672579713360501500852664619724892464378485048830943748100856363132505526102395897224540429534746922403466776643984460368019109111587336675626441445911577333782759108888096315845271003404884014164651307629007200978621588770577446720978022299939578302584019658540942621359808237987874414305685646649547264447255667213494925588170521653162147326200826329123695954188253518924310299548807778548607951063598812463326608524930092609616946804624450974946190200130758400026547425044001543856227708895166236396616732720526912997216021504132366576069439951680819027811722424801435552703232303283556711543593419095202296688887816100069484884980221462417430273760947596501948797958911475367541456322964704680287245028397988883144845911262427384036927854051021170341624383444046394925522205202314722383447302006708074910863836807520835743175224363026527639674562622086153692670681595886347270329544340696161663092679605893581433913951480956174076812024937805784991623024074565154239680823875609033062155629902152641969453076947506988206225706207149881393598887230556370410244814410354486691315174940418476381289200021945417683400120074241
def c16_KEYBASE : Nat := nat_lit 931142584286131225326741624302541079318000228816195868879531109304777114112
def c16_MS2 : Nat := nat_lit 46043437542181227785252935465622921390851162224716410819670763921250615998267048820859363957972111652232716779129032701342852049434577380275680076363994121091992350500582785783408746270125976505195048543507057843901687443403776944071336934752564101399053151493156586089540937637039752382011598965025332232789989464240704915696635274373339344387386321078136759932229453602629540262516365596281852223754129002799912742603811331991038290812972403988480355973584329033734855754568529663379207741084471514732100150520841550847336738735831971508218508059343919402859659365043516479242942554106422291908770160601431433867389768409940493433234121138940673703071364436496238345079736600353897080072304299631524375788613957118093449164424877906629530677274078077598557502047751311093043598956907234058896632982053045502288555767781836000770367049064252456398489463121562848630882221171211682638045100357030578394462344412002784784117372979220964417676878038838381871084111699284083385567303467320519075808899036060858132599539528026053610232832118920781132570809222918359515126666054536506350335756417476546291711217892181880916767284663190611082547343170352298835545526515364715200608191218127056149905745380936021856924595227833189169282236607817388099131573790382676223291595061574933702677908914900768361117579441763506606268387781711978108924516505057617888310961236898306991501316147309603886693094106890581500677167614659369154836217348825810725227675777420565842830111085266668318950149185702010510128583062441681214377204631807683275561458746993025609923430786701179904633573345999230447342788553489176067109516899530337343551149349491720005754725334202913156897297928740865081297884874056744055724056540784266477110623168676343090809567893492853972313772579819275823314946728402791065607978500687549972041796256147257017749080992390588572008172116299764474527358983684544206473326272635127703187688342019753364484256745539957696895720700512030948702118381490173463731659530606529390700579454707555457594734617336229194306790078136076857543989176682043549540171929440090498426967440177334149577441283310637455250555443191898719779846769322794545038793123913802524730542012268580426727427964323987624717570058315401483042541315659350765731841
def c16_L016 : Nat := nat_lit 5331384476964569693803814691761117550963988531690963117451663938106460296755241587851647815933096631500862987166616465226726950465541009294487821376381242886543815092078149418714718678865134831986600903767960508106360052577083717590455205312594316632272011259526892426867034171432556406894461330782203323199746647359117193100742729925186917449940241641665522062620399282235002883830922148377942135356351452196918463507302432998525752333897696984831402825475419860554498869912812536910705304094908456226198361831890569614684668435549674485301985027617541625270913898685762636030928023999836358013561425446497218981371247926888752890440945465880501053150508268112397266264740355744444677009724645386025678947160260149016025633694856040437133814978249602415158755203967144233328420360839392338685426634616064476147896183490639413719484480979408737599564008473118580931494434276832288066320453843116884112186239863426757285818267762044640233001722235584404221520982487200741061073844746318182226396623595593959189173666626993793109035778384608606521616714220215089272080157800453075269727085182823444977867563640425547718388097762867683226577550405990723380074523097315220890523123015858984853274770299123726442310470351426563287775072540141192513613050681856993077645052078147123660283665336235130439318944019885066057540897510696484952665745423853613768344260310283912278149068862146572926899413090684012710364140166743551252177764085959233074193331468089488542942662087571295780091376787270154882928772346018328626240924408839035362668312692674527222202815965002911667609201701851312614799966231513358719393025163130791020881024952591325433620034461430666999320150009489541787057099245861605240184977948147852371936679583708792992860636731896904480865635558199863712168081748605236030212504998773726619513356765263058812658633896331169437577669744761966536352514210522690304527767574879941334013461438149543240721536122313264771157432386730288810082124774334001533720271774612549602563895590095323664321016063111992766833313103563155683627927623346036561923858614175290319360501691419106031826130384909614006423320135348942580116339548110487173737002636628186181638164501581948143220638881954809342968325761001308957604514907692936222632943327184129664400642386159899747833280490148144680416173205883193401044002471935
def c16_L05 : Nat := nat_lit 2521903086685002830669386670398941696496279003317614353261640071432063312724688932988495953214709629610540209081637452079477156701484264715482146374728290676476055052329635034411479042417321733296477119353120862917481675896690245598597869301753625018698899047002878846919631636749969460803056401224510612942582529459565621211917671895640412618419889996057544578335734763855727312104350142667524318242876249608674332322062644738754838213944130716865392348969833152928808498776183545345721590401192677851715102110148892317925150247990232838092035337699607696397319460734853768474231612786982941915318595999716392590562427492691711903618971686004356948922953479995182959551490822126768673034278843472446723847744992212092725942542771606829192771256973184937360515927717730544490440698649899481181784171406088330824517916963604514004791621429185486619157461854988571128043449493885724117737606914421658769783679495936972241708496232904308342459043096103098052447554087178194444087726972394348806260705446912531240777960867274091498895386128372118748304236527453540359113220291661636276211789740864069494375440190023529095445655461187124132507882239806400011937288716209229382867426771826177316724160818994972453065149628354672494407984264047867062211102023919535903059382229687355359255262461635599963666548632279500233215347872611444778097781462416449634831343093290627613071200651965266815196182281394741649825106357962158980964533251922426570534726108350868159475433351868622403033992224084455655310779625033465894765677220935532101056194300341959928103872662166632512335168272791496010662988527915070119801385214878378296289185527280553726134448284189374791774237434869547499790494798530705156721359828985785054246388450369612921014415788339117096312423930788064012775013873605894818594455710108881135346212859131072300181851694304818075301865599872144085251055779754381619598089491436303980383265500612433668457581747031528311678956343764995088312289128013337110632920195513680288082410365346075129227916349377764183593998721453541255702536908884216577701069917440054930955604675882998199231098526469795288000654981243873044687671106911194054869109357373522112318350492851764590521702988335989770840285322210125546436865219172671441239356727591485764803843960798914964260802551225947739267587844394277797091082271
def c16_TILE : Nat := nat_lit 81351712473709768731270537754804570854718677526374656556827099078453655249183513967370837200474504180985168034891530712241198603273685958563940205636396473434711453300955968851983194916687797848273455463003898803789731480538395019309608687153342742538674162806544478932891343120966756800098593587887439127180081595469858748771537803085174600594189999872824018655991443995346042325946778795726590911060524180924978462002020798024349619804649377963399753192575262997703499960522049849861986787135247672635971035811254590900811298322265575422323720570955086980558692281769476402394568154418804577913503096765044922276207338473926190439321667290463127384611402580489772888757768455702215259170285273304733027346612652002991159436863600220296541008289457578624532771861862275628723893504835467134896263593744784865307029579471113354993278110618886665134111672741566810582046757867281423152826029497472863541409015997966846506725684932397043305130422454938646853146906038006272389926676528849961492280820868146169057353576363680370932109229947487701558201178304952914810103880376181815361670636802066757883078715807210615982117918102810455887351039993754839094751248909975141382820218446005719894327768354676530744037084785634596593805944001544098781003291094178577518044588054430818040492337472116127860211246202564523652107995890691767035412305239240310801011067525504116550683891998879574683747815528862633865326011547166418740791395223304082920475035753253811595981721028020077517225555615627601784218697581724706282763781320501035517941751623934191229157182650536532655973170090048258408483500900486132896818877899302525686747920234856571810788654328689509412072175318372499993241767694538876023269671902767259814399627431277836161755348010939261171368513896389161702419802374383703825627603551899391462781059971970074199414570784026389525866632253940131782292121927560697406389983594719483238169854858465602208309088613920268118676011089193389945557713806881842278481296629473557680077753720841133200900527399282715599806410369469072764597964802716663796808707014195320353406602447838651588099952466767589935504999394963646602828100222941743705455140560436197171559693317798857758764612526967411962589849103552436981834361908795852943205055728757605316253030993513385943896856491159604492502833690137993454551041
def c16_GUARD16 : Nat := nat_lit 4710014244295980380985330106063046401224473309441436413769872428219644797279101517593859293196699246501646446719546712353743454120855907338181975499538667417424450852330655157018633531837265238729894646279329493934743176667923421087567673449858819335786248538438162288209814443928239755345888978689150147920281104192825480565067957226319354582661224561098408172060273131305483230602026439100212458976325724465227397389511694840016018560825393262763193366170252370293332207536216665641781292509318038618043166758470431150914132698016846214186811325253049097101375025199650409507498752813690310074882760250371583769039069004443966987670663608125996265408049775937592039682368892536303968061989623051837243133750547583859060443262368957144754255690616078502196083046127544894588991530328928816558227713948238650917048230669847027097168430865540004288031849119330012846033625447909430589306986939593083190989271516469502175310776898980602857060190354441240324911240184147104480669946773909561652438401652382195791717059321893329359080405536137672053068728028269686749705379806967389126961244202153489833289084139202756221986126965504117595571506398310352755800176820383361399083894267157787374472277338723019321926175595980138885617038606383928441727301847833570657692159245917566738180220302137073130574160867894740626367655744005898522918062994128575972885693577332232809939481219678639152851005248128386517254863146179343118632955277960119503515252230078866957260258572207086687709860174794580482768709855483636633843366952592456518265674275573313061002049917078971457917488737769983185593154517638427583991511788911719770701457514455412000105899072813952155723256302415636358563731446698669415095558263396594557159601222434130643053068651082441017260078611594440745988781284798076818523666179558921891832368887531991336643401716657074880469064517972650035128364011104199700320366942462964150327923172429211641939303708793614383963534549316824659459108241651520494432171378513030508320200168071241143772182090446211781635649625956427488343020018852805333495771628288280728315416855463926496886637356077730468181718670170019210701355148866196497216850954330263474299509021072748542520605467017418007007098565496303744883802893134920543501839452680691781156762515968714882038609735097589827120797987350642036857385644529779506779824349608914666986317997330911371373092029637478071203937681408
def c16_ONES16L : Nat := nat_lit 143738227670165416900187075990693554724867959882856335869441907599476464760714767992976663000387550247242628378892416758842268497340573344060729232774007184369642665171223607086750290888588416709286335640848678403770238545774030184557118940730554789300117448072453683111871778684333488627499053304722599729012484869165816667635130530588359209675940690951489507203987827493453467730774732638556288420908377821814800945724844202881348222681439003380224406926582408761393194810065205860650063858316590533997899376174024388150455709778346136907556497963044711215251923376454175094833335962331857607265709236156359367951631744520384734731160388431579475873048394041064210195384792863046385744079273164423743992118852160151948866066356474522239814931964602005071901948429185330035064438791776392106879507871955525235505622273860077731236829555222778451172846957987366114686084760983564165933440763537386571990639389540695256814904080169085780549932566969031992337379156010348647481382653012376759412793019176702752432771585751139201632092454105763917635154053597097373953411248991924717009315313786422419228792850927818488219791472335941088732040600534373558221440943004863323946652046727227397902596354331146829892766589232792324390168414501462659964822444086717854543828101987230430242316293400179233721135280392295551341786369140805008633974090396990233547537035441047143858016394643513157740814369144543045570521946599711398884062355894779037582862922060512297279670976935030721670833135217119765709494319320179340632426969988783463081838204210611360504212949129607283261642112358703100146275467457227404296615960354971916830488815748761352542294283227964848502296640088367808794059187216145917208726753643694902257067908399479084565828511080396759559938922472974876281395913232363184159047429796109676874767116929076884052838187153841396498689713072895814060313843112310781870128385695280888376706639783606312315042227441211376463730912759912861921969856007431655713872417557160354868170171144752232170781924146918084156361377745252303721405640223779459640373890023446067148297633528562209987995524782645583135428426213684668295329441798895156775416594065254622628769196199729874954852461762006164764620927902108878933221523838345963851984846578390252110496902953146816468463431857226252048364196391315980128704395890191024987177256762967366546213317789639629253329224537276552465940481
def c16_CPAT1 : Nat := nat_lit 2299809449417883259013401391832236866540822814477881386784559963234904133867881560072437569776807349176814832432695950607695311021711199796448148959674481352848494342633411860687747935491045183911931486852598281127884956170114498510169885750000840692994179939758464427796956369464776087321620745217597295636874278796400290578766210736676646924567345028661606077563253984986866158485516200294185717102611007023936349408069031090669547498666710353998478074002372356895846683625911811687375752874107243251799694299207037895202076518510018328795510642359053210418114493206463375997948019530017705871234268585153464129194357365250406324203246277713234992971787046582359778004258778808747934816242281337156929818862907589431826674171457404590723956228976812529601340952005534521234651122493508268303125481737996966337701753902328230213564527137325568725008145505704615752243605571216372546346953933734188820532734265769005569195409371859010941277577710179401744961629597368232654615820184699179521517707225236334473805560742662516962577170701688903880551731717594312763173858584342068813325331101942460126193007045452072724383631001143738938069988887126088696790442976828035632292723776969676485652006478794577458958169522483976301940277997424608909320460551958799464929276875500450561210724572896240288165795214281972315937631334288103546280178942030770629304349343441344410996621288333665281146395175459939915902242899237516022696976516544655847023941003053646082192255434028646376540611377833411750595582614394926407256026837949810808371324044806758005343363108801125099125242072051433151469886047180652137612323519369420631523921395706536410237553168504662155380395183801530006857652496989717489019246265973950419179336867046900869236456411150604101127792606662442601980019679526420268479188896522741544510681642566630098325149898223348181854838263017327413359728893898806920229241694868659259274865768489982385854593374985049557267746071970280179372812886015625925008227038971484550085434949733548158038495802513858342857240540331195856371249445458946181398850797179432641810986995094438862687910221608788914504706320739022286865081149042800546553745372123422404324788421411948214453713443697226543644950038753505013401069887795241817194295013328502161355835237620341866299640636032150125285304383210077569869859524393293218756613370300086901846433091293058649025917729410562398489804801
def c16_K31 : Nat := nat_lit 4455885057775127923905799355711500196470906756368546411952699135583770407582157807782276553012014057664521479745664919524110323417557773665882606215994222715458922620307931819689259017546240917987876404866309030516877394918994935721270687162647198468303640890246064176468025139214338147452470652446400591599387030944140316696689046448239135499954161419496174723323622652297057499654016711795244941048159712476258829317470170289321794903124609104786956614724054671603189039112021381680151979607814306553934880661394756032664127003128730244134251436854386047672809624670079427939833414832287585825236986320847140406500584080131926776665972041378963752064500215272990516056928578754437958066457468097136063755684416964710414848057050710189434262890902662157228960401304745231086997602545068155313264744030621282300674290489662409668341716211906131986358255697608349555268627590490489143936663669658983731709821075761552961262026485241659197047909576039991762458753836320808071922862243383679541796583594477785325415919158285315250594866077278681446689775661510018592555748718749666227288774727379094996092578378762373134813535642414173750693258616565580304864669233150763042346213448544049334980486984265551726675764266216562056095220849545342458909495766688253490858671161604143337511805095405556245355193692161162091595377443364955267653196802306697239973648098672461459598508233948907889965245443480834412686180344591053365405933032738150165068750583875881215669800284985952371795827191730712736994323898925559559605236069652287355536984330528952175630601423017825781110905483119796104534539491174049533195094771004129421745153288211601928811122780066910303571195842739402072615834803700523433470529362954541969969105160383851621540683843492299546358106596662221164723273310203258708930470323679399983117780624801383405637983801769083291459381105259770235869729136481634237973979956553707539677905833291795681766309050677552670375658295557298719581065536230381327130044944271971000913275305487319197294239648554460608847202710102821415363574846937163248851590590726828081597226639385428509627861268262013077198281212624224717155212695765749860037914416022893301491845082191626123600426314622191107703248764965375246929867238988724879411530243930097815425403991547551310522366387574013813499290088130795383989836272595921774602494959651988362932612851478828506853205960655573126444154911
def c16_MG : Nat := nat_lit 53921538889076947220779976828605564007308691576147311567174480461825
def c16_MR : Nat := nat_lit 143736034398869180245266113663484224073703334822433318652402884132868806733604792360415639030443258300640876089196308150760718393398609942658971312333583734727104523526898124274896530890325661917121736976505480082431519919293445983179247964409750726357369334631945992842497722699843233819650159040111946118715329001880524882828364190400163660831866996553026734507222585880010075276804322152868174555566567817257487142206659940852997979189981733534756673492593016955443874136911375042970193095509050187063785147118683672617021600398941564464741890814416738527905254744317635404878420333813644299360602600839104021649261691916852423791692996484634301309965268859023519468920868674004361718641831617887616308840647432608206551550543016021384890877008174978234313118412951596905946434540198064458013307345781040401026589749745537735600967006177728555594604431777124333009576795910580383144201669245279751339970174441561086255829418593250468609024802995687361750240917451027145076936894882548466701015543262863542647187685567228362361454160057191620781930975579138871831812948992648741914543880255121882768448549045728702477023779754932539096585159646475990444273840403880009870990314699317202173281795823416800016954399910939656490297449613790667930121869105219866672579713360501500852664619724892464378485048830943748100856363132505526102395897224540429534746922403466776643984460368019109111587336675626441445911577333782759108888096315845271003404884014164651307629007200978621588770577446720978022299939578302584019658540942621359808237987874414305685646649547264447255667213494925588170521653162147326200826329123695954188253518924310299548807778548607951063598812463326608524930092609616946804624450974946190200130758400026547425044001543856227708895166236396616732720526912997216021504132366576069439951680819027811722424801435552703232303283556711543593419095202296688887816100069484884980221462417430273760947596501948797958911475367541456322964704680287245028397988883144845911262427384036927854051021170341624383444046394925522205202314722383447302006708074910863836807520835743175224363026527639674562622086153692670681595886347270329544340696161663092679605893581433913951480956174076812024937805784991623024074565154239680823875609033062155629902152641969453076947506988206225706207149881393598887230556370410244814410354486691315174940418476381289200021945417683400120074241
def c16_M256 : Nat := nat_lit 115792089237316195423570985008687907853269984665640564039457584007913129639935
def c16_M512 : Nat := nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084095
def c16_ONESL : Nat := nat_lit 81351712473709768731270537754804570854718677526374656556827099078453655249183513967370837200474504180985168034891530712241198603273685958563940205636396473434711453300955968851983194916687797848273455463003898803789731480538395019309608687153342742538674162806544478932891343120966756800098593587887439127180081595469858748771537803085174600594189999872824018655991443995346042325946778795726590911060524180924978462002020798024349619804649377963399753192575262997703499960522049849861986787135247672635971035811254590900811298322265575422323720570955086980558692281769476402394568154418804577913503096765044922276207338473926190439321667290463127384611402580489772888757768455702215259170285273304733027346612652002991159436863600220296541008289457578624532771861862275628723893504835467134896263593744784865307029579471113354993278110618886665134111672741566810582046757867281423152826029497472863541409015997966846506725684932397043305130422454938646853146906038006272389926676528849961492280820868146169057353576363680370932109229947487701558201178304952914810103880376181815361670636802066757883078715807210615982117918102810455887351039993754839094751248909975141382820218446005719894327768354676530744037084785634596593805944001544098781003291094178577518044588054430818040492337472116127860211246202564523652107995890691767035412305239240310801011067525504116550683891998879574683747815528862633865326011547166418740791395223304082920475035753253811595981721028020077517225555615627601784218697581724706282763781320501035517941751623934191229157182650536532655973170090048258408483500900486132896818877899302525686747920234856571810788654328689509412072175318372499993241767694538876023269671902767259814399627431277836161755348010939261171368513896389161702419802374383703825627603551899391462781059971970074199414570784026389525866632253940131782292121927560697406389983594719483238169854858465602208309088613920268118676011089193389945557713806881842278481296629473557680077753720841133200900527399282715599806410369469072764597964802716663796808707014195320353406602447838651588099952466767589935504999394963646602828100222941743705455140560436197171559693317798857758764612526967411962589849103552436981834361908795852943205055728757605316253030993513385943896856491159604492502833690137993454551041
def c16_RIDX : Nat := nat_lit 1220275687105646530969058066322068562820780162895619848352406486176804828737752709510562558007117562714777520523372960683617979049105289378459103084545947095453183892558764570614451146497657058958653200522110908478177036453651339611321185281793060086913211186510718515352627899553660487364116928905185908934878885232174647220969193422718007108740379228197092016782174856660163410451383751944646450825494223766705093977114855779873874568571281011398983397852729612702422761755433386840685443111633317481332519049519050254910029758217181657612412858340949011414551552786956542317188429885915330115246713111319609907123757741845839270915011256751961050100139618116578596097112876155332619455498946944368878690016896358408633241789687196594881474173846048182616263516874683809356665705391828976780116367156166119023362889804036757550060875210330871334947806363946889868671727239396271019556318910050365485380664624411480647560458033181067393019242112442367162988640129971977597822372262614055984989718083612701633542789287693301590710453583784330111799728706552906296073060517773587604571854896544881201831364403591616398671990270462143750286545035158545259308310536009138828489027845708175709787325684040191045240417458978489560412335592428373108538935724802727419172328331267655275787158840504811563413030015515564169833778307151303835716047781000086972534911749393575671435789683872180355778419041937908164165574896979122040030173320470817534716498811535949847934597373049174930234349167475022182636784471508781611341604561469101699236061511900123433786306090227754442375187025551441221474323172839078436465056470898733588120224135735327337018095834586995209110768890660628077077059080793412843626480867538777464868978180071685397391329213328564703255332829304678860153043917748626717349048388688930846959162440236017809727619467362371495309549713434711007971845948394760316757417380511660561360158065639581020753992185564680697500028139522793747068464642433740057199805784632040382807334870219509395743510899239620032012247935096025980005149951074006590739230508835503450759066086565074725089507452523104638751858564255146773147437443875156628001070724481724661771972296376031250448851681975975239983648610904622718838782625519976651545029215822745504757146110341652647558450653362710310584615944530394183809105920
def c16_MC32 : Nat := nat_lit 81351712473709768731270537754804570854718677526374656556827099078453655249183513967370837200474504180985168034891530712241198603273685958563940231696058596616908933721768011121057454821973495812342596482993087501499478512860834351945462592829405221781202207109824535443006190937958474128592194483299820099498788571908640384597419555456181165728739260407644112534898989749448696773400324830720534781005168492809501117234999769954302037292012513491919924594539724631016029023198878640269018093948565530261877274264625886143529126622001355834718629394562287715275729569986982869271834935347630062525972895240229512682880183773108331341138999726784581250039507895487508244487101288184893400524272518970966179015879698244575642054387046873828916705329674462787327354813473147852725091931587547972909731512078050614148294997635150780905630584721598186928348616841911675139343283565260670432659931460114420572759298281422300775170981859616266658757124613976150868602398270423580747135490004104794664091372333495609455636361579490223723798256869623633622687408267518065979427596432803043251755678828474942711964840944998130338162306539966213546487448148301396262252142441375231626644446837688469561690760319456896353028443168761056200179242341281421473693184486619383282820418248006837190488356403457041362244718095815422407185328044289815327036607775239292633746847146529113327184314978228635058867609635325050603978793601852470796554122020242996796152330885642727980996037924864480158490655357051832294580956162572872369652972490548547859873340056114663980464822781637133038591820951110782256841234958396728352734534820454926761907821217618722118362062683807653086151633064227912205159266402643177984619256221093449132547637220856140014652658002958270317641252532017981164747420446321156176240079373885668784523070042298492097232926646755764709050126502454789205030771771016792596676999182735200186066157375201775783037743484806893548312062969892935882708760995921197375642400960651723313294947215853521389651147564841511643274959635442569171580320181830465087419668002945177260295556431219386171038649553955024475568595834040628707610837550310281519481600418679521262221876518861705552465284972637409811393656339621832157896605739659966365771982706578118960114740874380971344745465372526824364922221528396638837538816
def c16_MC32M : Nat := nat_lit 13407807929942597099574024998205846127479365820592393377723561443721764030073546976801874298166903427690031858186486050853753882811946569946433649006084095
def c16_REP32 : Nat := nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041
def c16_GUARD32 : Nat := nat_lit 545374067936687760001320356235082532867175309625106876302855354574407017882254977608208322175386509307646124458466164179330772225059015551663419797650154256377376381974943717818088685662359948549083938362625054069730659668821710956750199039911702849833026853727346218776451845223244095989237548026226518594108961524802979206470532892740927110272555550549860981025203665280969579533473460189621939716306937268665124839816340549767233835640570412971388870847690616210390804838578309023911203890560863445221713873675018620913992097820402247651430192889871948396355613699605650434870485807334810401886086569557531606318959830766586033486862657601574428665746648809938036817122250797847787588296623428252809682059208322257758466952889907270010501207186664896913001936561242863164633306537950047979245552130025267091422959344751389856747448852208036882452152566242232831448863770050646556006614090363187591938329810207436482574465259136943219756235732753249737657384669454471446638408671580793613940105587819904803711446784298946357090489598362538927274509609366603824883877756714732388290640112778033311430558478645774514160765293241200891218411208287601477256818318972652576337876167508036061121203223070250361241728318473916402358986101982349749152449375446313020540825710007476813949686357326965176405746881190922510990047578352074749442487226003970520426874650195064187993989494385962096611550004439681122289707728518803222971408878431670270346883833754512943410418544039114187687911127404433567818586775026086112025524829551782936250190398217051255503645963261871176049417693640050125589860300699355294298441520652606239742005086579858343421163235788013936951526741409532994044455661987260151313463769788779645174485237114709302159837794220033743822029657660726001528753214892457379364520072676758583064412560306348271417238456102666838932355222328861798875498417353335227108307541294777791435222438674314619003990893590848604180565100981778582493828035776969021684959380854363131461052697228956246151181383633307640316582988185114770861098571150471954738209630444068499564604503396038873755627808261727006706927439246305607891074936255365445894680247869058694815367287580509912585339391841711810997422100564025149712682538540394182612700683886016947685546368312949170103484701004860002367890233848284463625256552269163508320742291119238372259582967365149272361789856168546101698766285695565522138194720352577409011519920219072250257480241586829011940805213618700288
def c16_ONES32L : Nat := nat_lit 253959590539656467736382203286086457253981060173877922959092703915390660000152409825571031391334957120775303085551673629940847039715859830222753713675846465107694446097567546096671691938471025111658469942689432795034097353379107525921519398648153454918892520352893610846461656141674190754647156235867421419410482759030060473117294205697685065806170716206478411809170462787602832323626363738263929130652424538817780483428547414842636247929451248129545185178374227234344372916304650261956827664077684024917759873752956567757759288801067624078798197624213969519527449132690974713708500288117123023553791721145404319427423100344178282416827351600664867398211103309848362960443948767077078851077995928122107722824070752718373419229355597528633894960948575705714990355335754744319540125568374082436433784724224948832496516101412190989007916698329167851457443351970162629824533951492349876093964134512090865493905642166471333510459055722199017068480948337004397836227281696382652334127887888249761397068196823776142537336230417222882197466491890390835364586491774117492550927101035943435640372388427161290976478941107995116226731470432691691079368446156196984116369075594773784437159154335053666085565100922365841102659850601999276484821970566338742688507482151646642266225866045559204160089770949895110170239061671738750762328309170936583281721559355021696736512077131804166358890707784314684854610825162232444756528236213514219490535966321672438805403110456891797208422116953467106301296096017786100422305415862279996287787719420987617340958862666530187941922789095840964489345296118431783090280508948189809126053713565974607943559571439334351299872266029945545341599146560548336265820852474896307714965087263276635284761542973438884206040666541100360370254915980960243162118464192588524597007815109919096838875003301700703528355088132744114348830293085827398521592103575046745645025531432953566049794870742743191776792934905201478014031937803038667186083288759444384688958237345499513419835221594644825044638190247727390526134049606097289762039934820715316915050908198612043431310217546317201925268307450100316995255387968526039221824582785072478416692580966771903827491815937920432810364007876120419705948839226749329693933268329312178591592555812567913758357226994330608334152354395417497664638903852684639219779778397252554223287054858747111754297729285969060082822039801881695957279897153175213438549414441258371347337924046009895511660837375944951521607681
def c16_CPATV : Nat := nat_lit 507919181197572085355141551768284217276839878358241958443462703549557080277835189145153530878850625330167295512975408941047023028572140967005169645510824468130024378911696327980958239404838019843768880403449975671692374757005466563108529553559712248122753183508418256854517464201060195565045613684467001043723303380107261074456803909934079571106525239817203957476569229351140165574015403384297774595702536772388175494400457899972433772486038170731880212467646043619105696166598429380047207506827064411434221080068007610498679275142153944857207864304463269492348849927891873273605918533772743321981913703740124674212895066147626210528258428135370545280912871198022106131820693532964834091767423762562848396445457080063342343855381488188723972486938022665849736362258735217621650218008568778782619619155593397548591161523434349298624903213548269991413340110292680430245399198300559735425610174425765319285672424583199663484027395145649196516661714890076992076556808779158271552841197107434713618624732751124733141557295343153054747175396366359238490648110899605341255233119838250963529576030259861734451919227315731728388426614955664165358210062844484937304257927702031761643327928152016049124067688386598780330580389305467534356467157091885330076794313637496861194662431323786230201675537811440121580886685509080336056984156599291379454120759663857849089350255015207435582240740859811581490320723495785890949560746360626497348167663396101898543993048937757909895146840565364278079187751042737444787323246842458937061607652253362050460549422898264394932134320483265008602888131709115737316623398197782067796036275679749217097413638870065970238958458439839289674421491308034770830238240410008866404462903725741930921442271716446883238074207035122943069353608467290902554894343635403934047048444920788493551205766574902196818888928377717543404694691636395486886931407625314635075458640892831679815437705928581420121209074768612451540126731576008411868589665645997134065258987714613828858047717700376085415053640630845772196610988883070103520095960140304140936779323027555387695362030144751274798691631408506097279178867977985993271770910146856709723134450679543033613269619545733451377073660529548397947387954763368556296667043707251441851650566863274027682171843429463251583214327961129124946900781301890160952549929615366713658019763947975897030838508559005475165600492063862690928250123853571735204344433623968080063284857783536647698756256867261317843517441
def c16_K31B : Nat := nat_lit 7872747306729350499827848301868680174873412865390215611731873821377110460004724704592701973131383670744034395652101882528166258231191654736905365123951240418338527829024593928996822450092601778461412568223372416646057017954752333303567101358092757102485668130939701936240311340391899913394061843311890064001724965529931874666636120376628237039991292202400830766084284346415687802032417275886181803050225160703351194986284969860121723685812988692015900740529601044264675560405444158120661657586408204772450556086341653600490537952833096346442744126350633055105350923113420216124963508931630813730167543355507533902250116110669526754921647899620610889344544202605299251773762411779389444383417873771785339407546193334269575996110023523387650743789405846877164701015408397073905743892619596555529447326450973413807391999143777920659245417648204203395180743911075041524560552496262846158912888169874816830311074907160611338824230727388169529122909398447136332923045732587862222357964524535742603309114101537060418657423142933909348121461248602115896302181244997642269078740132114246504851544041242000020270847174347848603028675583413442423460421830842106507607441343437987317551933784386663648652518128593341074182455368661977571029481087556501023343731946701045910253001847412335328962782899446748415277410911823901273632177584299034081733368340005672598831874391085929157125611941313755230492935580029205787452375322618940804206614955971845602967496424163645713461085625557480295340178976551369113091467891730679884921419302050616137569724742662435826199606461971069899169704179671385275798695777393884082907665120545212846250346714619364890296040246928311905589573543376998424240446426721785539163917705161575693827607832176605410387260662774111171477902395409767538025672389970244262507242268407492002005125102352721809379007732115067544813739085660649354169355210826449114995791474421560547543640993025038945080580982061245818434990071894198682768581951542775925357705357710484916014891869433989576383783897679549106310155537789015982623237979442174824366578154156973346370616743935833259683317530953109826852917027024307215876562066337246830917470009969929018652246294075533417121284244159733010884414016029229220511931318208677536339369230189605326509074036824248858358722986257942427603806019433223815813173130314829180921898700621160464383229607865040862567483233858332574675676811748431616595031847679009511767475645426306760861485958654293497169838111
def c16_SUF : Nat := nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041
def c16_ONES32C : Nat := nat_lit 3121748551042830955846434448392195761173861469553377210925551749450926617608515916953419850934372115559970022585814835838873106672153732883415041

/-! ## Column vectors (v7 vectorized generator, `72`-bit lanes) -/
def colK1 (s : Nat) : Nat :=
  vecK (nat_lit 2290649225) (nat_lit 35) (nat_lit 15) MvD_16 (Nat.mod (vecZ R_16 Kc_16 Mv_16 s) (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496))
def colK2 (s : Nat) : Nat :=
  vecK (nat_lit 4908534053) (nat_lit 36) (nat_lit 14) MvD_16 (Nat.shiftRight (vecZ R_16 Kc_16 Mv_16 s) (nat_lit 1152))
def colA (s : Nat) : Nat := vecA (colK1 s) (vecC g1_16 o_16 (colK1 s))
def colB (s : Nat) : Nat := vecB g0_16 g2_16 o_16 (colK1 s) (colK2 s) (vecC g1_16 o_16 (colK1 s))

/-! ## Row one-hots: lane `i` (512 bits) holds indicators at 16-bit sub-lanes `i`, `a_i`, `b_i` -/
def ohFold (X : Nat) : Nat :=
  Nat.add (Nat.add (Nat.land X c16_LOW) (Nat.land (Nat.shiftRight X (nat_lit 256)) c16_LOW)) c16_DIAG
def rowV (A B : Nat) : Nat :=
  ohFold (Nat.sub c16_ONESUB (Nat.land (Nat.shiftRight (Nat.add (Nat.xor (Nat.mul (Nat.land
    (Nat.mul (Nat.add A (Nat.shiftLeft B (nat_lit 256))) c16_MSP) c16_M4) c16_REP16) c16_CPAT) c16_K15)
    (nat_lit 4)) c16_ONESUB))

/-! ## Labels (heuristic): rank columns by touch count -/
def c16_KEYB2 : Nat := nat_lit 28974967111251610034557208917472518548564985757358913995594580676308625342464
/-- Row lanes with `0xffff` masks at the row's columns. -/
def maskRow (ROW : Nat) : Nat := Nat.mul ROW (nat_lit 65535)
def c16_K1 : Nat := nat_lit 57898694929695802362630618871590662278840377317591754680842077826433285193729
def c16_K2 : Nat := nat_lit 57900461803720938796527369783088467846977300640772736454917601708084432109570
def c16_TW16 : Nat := nat_lit 3533748050272867793501822995611136273846646361963548151047763302293831682
/-- Per column count `cnt ↦ 2·[cnt ≤ 1] + [cnt ≤ 2]` (16-bit cells). -/
def fV (CNT : Nat) : Nat :=
  Nat.add (Nat.land (Nat.shiftRight (Nat.sub c16_K1 CNT) (nat_lit 14)) c16_TW16)
    (Nat.land (Nat.shiftRight (Nat.sub c16_K2 CNT) (nat_lit 15)) c16_REP16)
/-- Column score `g c = Σ_{rows r ∋ c} Σ_{c' ∈ r} f (cnt c')` (16-bit cells). -/
def gV (ROW : Nat) : Nat :=
  Nat.mod (Nat.land (Nat.mul (Nat.land (Nat.shiftRight (Nat.mul (Nat.land (maskRow ROW)
    (Nat.mul (fV (Nat.mod ROW c16_M512)) c16_TILE)) c16_REP16) (nat_lit 240)) c16_L016) c16_REP16) (maskRow ROW)) c16_M512
/-- Label key: fewer touches and more low-count neighbours give a higher label. -/
def keyC (ROW : Nat) : Nat :=
  Nat.sub c16_KEYB2 (Nat.mul (Nat.sub (Nat.mul (Nat.mod ROW c16_M512) (nat_lit 64)) (gV ROW)) (nat_lit 16))
def rank16 (KL KC : Nat) : Nat :=
  Nat.land (Nat.shiftRight (Nat.mul (Nat.land (Nat.shiftRight (Nat.sub (Nat.lor (Nat.mul KL c16_REP16)
    c16_GUARD16) (Nat.mul KC c16_TILE)) (nat_lit 15)) c16_ONES16L) c16_REP16) (nat_lit 240)) c16_L05
def labRK (ROW : Nat) : Nat := rank16 (Nat.land (Nat.mul (keyC ROW) c16_MS2) c16_L016) (keyC ROW)

/-! ## Weights `E c = 2^(r c - 1)` -/
def oh16 (X : Nat) : Nat :=
  Nat.sub c16_ONES16L (Nat.land (Nat.shiftRight (Nat.add (Nat.xor (Nat.mul X c16_REP16) c16_CPAT1) c16_K31)
    (nat_lit 5)) c16_ONES16L)
def eV (RK : Nat) : Nat := Nat.land (Nat.shiftRight (Nat.mul (oh16 RK) c16_MG) (nat_lit 225)) c16_L016
def eRev (E : Nat) : Nat := Nat.land (Nat.shiftRight (Nat.mul E c16_MR) (nat_lit 7680)) c16_M256
def oV (ROW Er : Nat) : Nat := Nat.land (Nat.shiftRight (Nat.mul ROW Er) (nat_lit 240)) c16_L016

/-! ## Sorted row weights -/
def r1V (O : Nat) : Nat := Nat.land O (Nat.sub O c16_ONESL)
def loV (O : Nat) : Nat := Nat.sub O (r1V O)
def hiV (O : Nat) : Nat := Nat.land (r1V O) (Nat.sub (r1V O) c16_ONESL)
def midV (O : Nat) : Nat := Nat.sub (r1V O) (hiV O)

/-! ## Row order (heuristic): sort rows by `hi`, vee -/
def k2L (hi : Nat) : Nat := Nat.add (Nat.mul hi (nat_lit 16)) c16_RIDX
def rank32 (KL KC : Nat) : Nat :=
  Nat.land (Nat.shiftRight (Nat.mul (Nat.land (Nat.shiftRight (Nat.sub (Nat.lor (Nat.mul KL c16_REP32)
    c16_GUARD32) (Nat.mul KC c16_TILE)) (nat_lit 31)) c16_ONES32L) c16_REP32) (nat_lit 480)) c16_L05
def ordRK (hi : Nat) : Nat :=
  rank32 (k2L hi) (Nat.land (Nat.shiftRight (Nat.mul (k2L hi) c16_MC32) (nat_lit 7680)) c16_MC32M)
def ohQ (RK2 : Nat) : Nat :=
  Nat.sub c16_ONES32L (Nat.land (Nat.shiftRight (Nat.add (Nat.xor (Nat.mul RK2 c16_REP32) c16_CPATV) c16_K31B)
    (nat_lit 5)) c16_ONES32L)
def permV (MQ V : Nat) : Nat := Nat.mod (Nat.land (Nat.mul V c16_REP32) MQ) c16_M512

/-! ## Packed DP -/
def gat32 (V k : Nat) : Nat := Nat.mod (Nat.shiftRight V (Nat.mul (nat_lit 32) k)) (nat_lit 4294967296)
def stepL (S z y : Nat) : Nat := Nat.add (Nat.add S (Nat.shiftLeft S z)) (Nat.shiftLeft S y)
def stepR (S x y : Nat) : Nat := Nat.add (Nat.add S (Nat.shiftRight S x)) (Nat.shiftRight S y)
/-- Phase 1: levels `0 … k` (base `minP`, left shifts). -/
def ph1 (ZW YW : Nat) (k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) (nat_lit 1) (fun j S => stepL S (gat32 ZW j) (gat32 YW j)) k
/-- Trim on reaching levels `10, 12, 14`. -/
def trim16 (REMW lev S : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) (Nat.mod S (Nat.shiftLeft (nat_lit 1) (gat32 REMW lev)))
    (fun _ _ => Nat.rec (motive := fun _ => Nat) (Nat.mod S (Nat.shiftLeft (nat_lit 1) (gat32 REMW lev)))
      (fun _ _ => Nat.rec (motive := fun _ => Nat) (Nat.mod S (Nat.shiftLeft (nat_lit 1) (gat32 REMW lev)))
        (fun _ _ => S) (Nat.xor lev (nat_lit 14))) (Nat.xor lev (nat_lit 12))) (Nat.xor lev (nat_lit 10))
/-- Phase 2: from the rebased level-7 state, `k` more rows. -/
def ph2 (XW YW REMW S7 : Nat) (k : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat) S7
    (fun j S => trim16 REMW (Nat.add (nat_lit 8) j)
      (stepR S (gat32 XW (Nat.add (nat_lit 7) j)) (gat32 YW (Nat.add (nat_lit 7) j)))) k
def lastRow (S x y : Nat) : Nat :=
  Nat.add (Nat.add (Nat.land S (nat_lit 2047)) (Nat.land (Nat.shiftRight S x) (nat_lit 2047)))
    (Nat.land (Nat.shiftRight S y) (nat_lit 2047))

/-! ## The fast path -/
def amtY (P1 : Nat) : Nat := Nat.mul P1 (nat_lit 11)
def amtX (P2 : Nat) : Nat := Nat.mul P2 (nat_lit 11)
def preV (P1 : Nat) : Nat := Nat.mod (Nat.mod P1 (nat_lit 26959946667150639794667015087019630673637144422540572481103610249216)) (nat_lit 4294967295)
def remW (P1 : Nat) : Nat :=
  Nat.mul (Nat.add (Nat.shiftRight (Nat.mul P1 c16_SUF) (nat_lit 480)) c16_ONES32C) (nat_lit 11)
def c1V (hi : Nat) : Nat := Nat.sub (Nat.mod hi c16_M512) (nat_lit 65535)

def dp16 (XW YW ZW REMW C1 PRE : Nat) : Nat :=
  lastRow (ph2 XW YW REMW (Nat.shiftRight (Nat.shiftLeft (ph1 ZW YW (nat_lit 7))
      (Nat.mul (Nat.sub C1 PRE) (nat_lit 11))) (Nat.mul (Nat.sub PRE C1) (nat_lit 11))) (nat_lit 8))
    (gat32 XW (nat_lit 15)) (gat32 YW (nat_lit 15))

def lev16 (XW YW ZW REMW C1 PRE k : Nat) : Nat :=
  ph2 XW YW REMW (Nat.shiftRight (Nat.shiftLeft (ph1 ZW YW (nat_lit 7))
      (Nat.mul (Nat.sub C1 PRE) (nat_lit 11))) (Nat.mul (Nat.sub PRE C1) (nat_lit 11))) k


def c16_GM : Nat := 1536 * ((2 ^ (11 * 131072) - 1) / 2047)

def levChk (XW YW ZW REMW C1 PRE : Nat) : Nat :=
  Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add (Nat.add
    (Nat.land (ph1 ZW YW (nat_lit 6)) c16_GM) (Nat.land (ph1 ZW YW (nat_lit 7)) c16_GM))
    (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 1)) c16_GM)) (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 2)) c16_GM))
    (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 3)) c16_GM)) (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 4)) c16_GM))
    (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 5)) c16_GM)) (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 6)) c16_GM))
    (Nat.land (lev16 XW YW ZW REMW C1 PRE (nat_lit 7)) c16_GM)

def chk16 (E OHQ XW YW ZW REMW C1 PRE : Nat) : Nat :=
  Nat.add (Nat.add (Nat.add (Nat.xor (Nat.mod E c16_M512) (nat_lit 65535)) (Nat.xor (Nat.mod OHQ c16_M512) c16_ONES32C))
    (levChk XW YW ZW REMW C1 PRE)) (Nat.shiftRight (Nat.add C1 PRE) (nat_lit 17))

def fastD (s E OHQ XW YW ZW REMW C1 PRE : Nat) : Nat :=
  pickZ (chk16 E OHQ XW YW ZW REMW C1 PRE) (dp16 XW YW ZW REMW C1 PRE) (main (nat_lit 16) s)
def fastP (s E hi OHQ P1 P2 : Nat) : Nat :=
  fastD s E OHQ (amtX P2) (amtY P1) (Nat.sub (amtY P1) (amtX P2)) (remW P1) (c1V hi) (preV P1)
def fastQ (s E hi V1 V2 OHQ : Nat) : Nat :=
  fastP s E hi OHQ (permV (Nat.mul OHQ (nat_lit 4294967295)) V1) (permV (Nat.mul OHQ (nat_lit 4294967295)) V2)
def fastH (s E lo mid hi : Nat) : Nat := fastQ s E hi (Nat.sub hi lo) (Nat.sub hi mid) (ohQ (ordRK hi))
def fastO (s E O : Nat) : Nat := fastH s E (loV O) (midV O) (hiV O)
def fastE (s ROW E : Nat) : Nat := fastO s E (oV ROW (eRev E))
def fastB (s ROW : Nat) : Nat := fastE s ROW (eV (labRK ROW))
def fastS16 (s : Nat) : Nat := fastB s (rowV (colA s) (colB s))

#flatten fastS16 mainV16 [c16_KEYB2, c16_K1, c16_K2, c16_TW16, fV, gV, maskRow, R_16, Kc_16, Mv_16, MvD_16, g1_16, g0_16, g2_16, o_16, c16_MSP, c16_M4, c16_REP16, c16_CPAT, c16_K15, c16_ONESUB, c16_LOW, c16_DIAG, c16_KEYBASE, c16_MS2, c16_L016, c16_L05, c16_TILE, c16_GUARD16, c16_ONES16L, c16_CPAT1, c16_K31, c16_MG, c16_MR, c16_M256, c16_M512, c16_ONESL, c16_RIDX, c16_MC32, c16_MC32M, c16_REP32, c16_GUARD32, c16_ONES32L, c16_CPATV, c16_K31B, c16_SUF, c16_ONES32C, colK1, colK2, colA, colB, ohFold, rowV, keyC, rank16, labRK, oh16, eV, eRev, oV, r1V, loV, hiV, midV, k2L, rank32, ordRK, ohQ, permV, gat32, stepL, stepR, ph1, trim16, ph2, lastRow, amtY, amtX, preV, remW, c1V, dp16, lev16, levChk, chk16, fastD, fastP, fastQ, fastH, fastO, fastE, fastB, fastS16, vecZ, vecK, vecC, vecA, vecB] [c16_GM]

end P8
end Submission


/-! # Proof part: NewCore -/

section
namespace Submission

/-- Weighted choice count: sequences picking one column per row (list order), weights summing to `t`. -/
def cnt (e : Nat → Nat) : List (List Nat) → Nat → Nat
  | [], t => if t = 0 then 1 else 0
  | S :: L, t => (S.map (fun c => if e c ≤ t then cnt e L (t - e c) else 0)).sum

theorem sum_map_add' (B : List Nat) (g h : Nat → Nat) :
    (B.map (fun b => g b + h b)).sum = (B.map g).sum + (B.map h).sum := by
  induction B with
  | nil => rfl
  | cons b B ih => simp only [List.map_cons, List.sum_cons, ih]; omega

theorem sum_map_zero' (B : List Nat) : (B.map (fun _ => (0 : Nat))).sum = 0 := by
  induction B with
  | nil => rfl
  | cons b B ih => simp only [List.map_cons, List.sum_cons, ih]

theorem sum_map_sum_comm (A B : List Nat) (f : Nat → Nat → Nat) :
    (A.map (fun a => (B.map (fun b => f a b)).sum)).sum
      = (B.map (fun b => (A.map (fun a => f a b)).sum)).sum := by
  induction A with
  | nil => simp only [List.map_nil, List.sum_nil]; exact (sum_map_zero' B).symm
  | cons a A ih =>
    simp only [List.map_cons, List.sum_cons, ih]
    exact (sum_map_add' B (fun b => f a b) (fun b => (A.map (fun a => f a b)).sum)).symm

theorem cnt_swap (e : Nat → Nat) (S1 S2 : List Nat) (L : List (List Nat)) (t : Nat) :
    cnt e (S1 :: S2 :: L) t = cnt e (S2 :: S1 :: L) t := by
  simp only [cnt]
  have h1 : ∀ c1, (if e c1 ≤ t then (S2.map (fun c2 => if e c2 ≤ t - e c1 then cnt e L (t - e c1 - e c2) else 0)).sum else 0)
      = (S2.map (fun c2 => if e c1 + e c2 ≤ t then cnt e L (t - e c1 - e c2) else 0)).sum := by
    intro c1
    by_cases h : e c1 ≤ t
    · rw [if_pos h]; apply sum_map_congr; intro c2 _
      by_cases h' : e c2 ≤ t - e c1
      · rw [if_pos h', if_pos (by omega)]
      · rw [if_neg h', if_neg (by omega)]
    · rw [if_neg h, List.map_congr_left (fun c2 _ => if_neg (by omega))]
      exact (sum_map_zero' S2).symm
  have h2 : ∀ c2, (if e c2 ≤ t then (S1.map (fun c1 => if e c1 ≤ t - e c2 then cnt e L (t - e c2 - e c1) else 0)).sum else 0)
      = (S1.map (fun c1 => if e c1 + e c2 ≤ t then cnt e L (t - e c1 - e c2) else 0)).sum := by
    intro c2
    by_cases h : e c2 ≤ t
    · rw [if_pos h]; apply sum_map_congr; intro c1 _
      by_cases h' : e c1 ≤ t - e c2
      · rw [if_pos h', if_pos (by omega), show t - e c2 - e c1 = t - e c1 - e c2 by omega]
      · rw [if_neg h', if_neg (by omega)]
    · rw [if_neg h, List.map_congr_left (fun c1 _ => if_neg (by omega))]
      exact (sum_map_zero' S1).symm
  rw [List.map_congr_left (fun c1 _ => h1 c1), List.map_congr_left (fun c2 _ => h2 c2)]
  exact sum_map_sum_comm S1 S2 _

theorem cnt_perm (e : Nat → Nat) {L L' : List (List Nat)} (h : L.Perm L') : ∀ t, cnt e L t = cnt e L' t := by
  induction h with
  | nil => intro t; rfl
  | cons S _ ih => intro t; simp only [cnt]; apply sum_map_congr; intro c _; split <;> simp [ih]
  | swap S1 S2 L => intro t; exact cnt_swap e S2 S1 L t
  | trans _ _ ih1 ih2 => intro t; rw [ih1, ih2]

/-- Rows `i, i+1, …, d-1` (as supports). -/
def rowsFrom (d seed : Nat) : Nat → Nat → List (List Nat)
  | 0, _ => []
  | n + 1, i => supp d seed i :: rowsFrom d seed n (i + 1)

theorem hlR_cnt (d seed : Nat) (lam : Nat → Nat) :
    ∀ k, k ≤ d → ∀ m, m < 2 ^ d →
      hlR d seed lam k m = cnt (fun c => 2 ^ lam c) (rowsFrom d seed k (d - k)) (2 ^ d - 1 - m)
  | 0, _, m, hm => by
    simp only [hlR, rowsFrom, cnt]
    by_cases h : m = 2 ^ d - 1
    · rw [if_pos h, if_pos (by omega)]
    · rw [if_neg h, if_neg (by omega)]
  | k + 1, hk, m, hm => by
    simp only [hlR]
    rw [show d - (k + 1) = d - 1 - k by omega]
    simp only [rowsFrom, cnt]
    apply sum_map_congr; intro j _
    by_cases h : 2 ^ lam j + m < 2 ^ d
    · rw [if_pos h, if_pos (by omega), hlR_cnt d seed lam k (by omega) _ h,
        show d - 1 - k + 1 = d - k by omega, show 2 ^ d - 1 - (2 ^ lam j + m) = 2 ^ d - 1 - m - 2 ^ lam j by omega]
    · rw [if_neg h, if_neg (by omega)]

theorem rowsFrom_eq (d seed : Nat) : ∀ n i, rowsFrom d seed n i = (List.range' i n).map (supp d seed)
  | 0, _ => rfl
  | n + 1, i => by simp [rowsFrom, rowsFrom_eq d seed n (i + 1), List.range'_succ]

/-- The spec permanent is the weighted count over the rows in their natural order. -/
theorem spec_cnt (d seed : Nat) (lam : Nat → Nat) (hlam : ∀ j, j < d → lam j < d)
    (hinj : ∀ a b, a < d → b < d → lam a = lam b → a = b) :
    permanentSpec (genPermanentMatrix d seed)
      = cnt (fun c => 2 ^ lam c) ((List.range d).map (supp d seed)) (2 ^ d - 1) := by
  rw [← hlR_final d seed lam hlam hinj, hlR_cnt d seed lam d (Nat.le_refl d) 0 (Nat.two_pow_pos d),
    Nat.sub_self, rowsFrom_eq, List.range_eq_range']
  rfl

end Submission

end


/-! # Proof part: Bits -/

section
namespace Submission
namespace P8

theorem add_eq_or_of_and (a b : Nat) (h : a &&& b = 0) : a + b = a ||| b := by
  have ha : a < 2 ^ (a + b + 1) := Nat.lt_of_lt_of_le (Nat.lt_two_pow_self) (Nat.pow_le_pow_right (by omega) (by omega))
  have hb : b < 2 ^ (a + b + 1) := Nat.lt_of_lt_of_le (Nat.lt_two_pow_self) (Nat.pow_le_pow_right (by omega) (by omega))
  have hab : a + b < 2 ^ (a + b + 1) := Nat.lt_of_lt_of_le (Nat.lt_two_pow_self) (Nat.pow_le_pow_right (by omega) (by omega))
  have key := BitVec.add_eq_or_of_and_eq_zero (BitVec.ofNat (a + b + 1) a) (BitVec.ofNat (a + b + 1) b) (by
    apply BitVec.eq_of_toNat_eq
    simp [BitVec.toNat_and, Nat.mod_eq_of_lt ha, Nat.mod_eq_of_lt hb, h])
  have := congrArg BitVec.toNat key
  simp [BitVec.toNat_add, BitVec.toNat_or, Nat.mod_eq_of_lt ha, Nat.mod_eq_of_lt hb, Nat.mod_eq_of_lt hab] at this
  exact this

/-! ## Bit-disjoint sums of shifted values -/

/-- `Σ v · 2^q` over a list of `(v, q)`. -/
def tsum : List (Nat × Nat) → Nat
  | [] => 0
  | (v, q) :: ts => v * 2 ^ q + tsum ts

/-- Bit `p` of the terms read as a disjoint union of `w`-bit fields. -/
def tbit (w p : Nat) : List (Nat × Nat) → Bool
  | [] => false
  | (v, q) :: ts => (decide (q ≤ p) && decide (p < q + w) && v.testBit (p - q)) || tbit w p ts

/-- The fields `[q, q + w)` are pairwise disjoint. -/
def sep (w : Nat) : List (Nat × Nat) → Prop
  | [] => True
  | (_, q) :: ts => (∀ t ∈ ts, q + w ≤ t.2 ∨ t.2 + w ≤ q) ∧ sep w ts

def sepB (w : Nat) : List (Nat × Nat) → Bool
  | [] => true
  | (_, q) :: ts => ts.all (fun t => decide (q + w ≤ t.2) || decide (t.2 + w ≤ q)) && sepB w ts

theorem sep_of_sepB (w : Nat) : ∀ ts : List (Nat × Nat), sepB w ts = true → sep w ts
  | [], _ => trivial
  | (v, q) :: ts, h => by
    simp only [sepB, Bool.and_eq_true, List.all_eq_true, Bool.or_eq_true, decide_eq_true_eq] at h
    exact ⟨h.1, sep_of_sepB w ts h.2⟩

theorem tbit_false (w p : Nat) : ∀ ts : List (Nat × Nat), (∀ t ∈ ts, ¬ (t.2 ≤ p ∧ p < t.2 + w)) → tbit w p ts = false
  | [], _ => rfl
  | (v, q) :: ts, h => by
    simp only [tbit]
    have h1 := h (v, q) (by simp)
    have h2 := tbit_false w p ts (fun t ht => h t (by simp [ht]))
    rw [h2]
    by_cases c : q ≤ p ∧ p < q + w
    · exact absurd c h1
    · simp only [Bool.or_false]
      rcases Decidable.not_and_iff_or_not.mp c with c | c <;> simp [c]

theorem tsum_tb (w : Nat) : ∀ ts : List (Nat × Nat), (∀ t ∈ ts, t.1 < 2 ^ w) → sep w ts →
    ∀ p, (tsum ts).testBit p = tbit w p ts
  | [], _, _, p => by simp [tsum, tbit]
  | (v, q) :: ts, hv, ⟨hs, hr⟩, p => by
    have hv0 : v < 2 ^ w := hv (v, q) (by simp)
    have ih := tsum_tb w ts (fun t ht => hv t (by simp [ht])) hr
    have hand : v * 2 ^ q &&& tsum ts = 0 := by
      apply Nat.eq_of_testBit_eq; intro j
      rw [Nat.testBit_and, Nat.testBit_mul_two_pow, ih, Nat.zero_testBit]
      by_cases c : q ≤ j ∧ j < q + w
      · rw [tbit_false w j ts (fun t ht hh => by have := hs t ht; omega)]; simp
      · by_cases c1 : q ≤ j
        · have c2 : ¬ j < q + w := fun h => c ⟨c1, h⟩
          have : v.testBit (j - q) = false := Nat.testBit_lt_two_pow
            (Nat.lt_of_lt_of_le hv0 (Nat.pow_le_pow_right (by omega) (by omega)))
          simp [this]
        · simp [c1]
    simp only [tsum, tbit]
    rw [add_eq_or_of_and _ _ hand, Nat.testBit_or, Nat.testBit_mul_two_pow, ih]
    by_cases c1 : q ≤ p
    · by_cases c2 : p < q + w
      · simp [c1, c2]
      · have : v.testBit (p - q) = false := Nat.testBit_lt_two_pow
          (Nat.lt_of_lt_of_le hv0 (Nat.pow_le_pow_right (by omega) (by omega)))
        simp [c1, c2, this]
    · simp [c1]


theorem tsum_append (xs ys : List (Nat × Nat)) : tsum (xs ++ ys) = tsum xs + tsum ys := by
  induction xs with
  | nil => simp [tsum]
  | cons x xs ih => obtain ⟨v, q⟩ := x; simp only [List.cons_append, tsum, ih]; omega

theorem tsum_shift (s : Nat) : ∀ xs : List (Nat × Nat),
    tsum (xs.map (fun t => (t.1, t.2 + s))) = tsum xs * 2 ^ s
  | [] => by simp [tsum]
  | (v, q) :: xs => by
    simp only [List.map_cons, tsum, tsum_shift s xs, Nat.pow_add, Nat.add_mul, Nat.mul_assoc]

theorem enc_tsum (W : Nat) (f : Nat → Nat) : ∀ L, enc W f L = tsum ((List.range L).map (fun i => (f i, W * i)))
  | 0 => rfl
  | L + 1 => by
    rw [List.range_succ, List.map_append, tsum_append, ← enc_tsum W f L]
    simp [enc, tsum]

theorem tsum_flatMap {α : Type} (f : α → List (Nat × Nat)) : ∀ l : List α,
    tsum (l.flatMap f) = (l.map (fun x => tsum (f x))).sum
  | [] => rfl
  | x :: l => by simp only [List.flatMap_cons, tsum_append, tsum_flatMap f l, List.map_cons, List.sum_cons]

theorem tsum_mul_enc_ones (xs : List (Nat × Nat)) (W : Nat) : ∀ L,
    tsum xs * enc W (fun _ => 1) L
      = tsum ((List.range L).flatMap (fun j => xs.map (fun t => (t.1, t.2 + W * j))))
  | 0 => by simp [enc, tsum]
  | L + 1 => by
    rw [List.range_succ, List.flatMap_append, tsum_append, ← tsum_mul_enc_ones xs W L]
    simp only [enc, List.flatMap_cons, List.flatMap_nil, List.append_nil, tsum_shift, Nat.one_mul]
    rw [Nat.mul_add]

/-! ### Spreading `72`-bit lanes (two 4-bit fields per row) to `512`-bit lanes -/

def spTerms (a b : Nat → Nat) : List (Nat × Nat) :=
  (List.range 16).flatMap (fun j => ((List.range 16).flatMap (fun i => [(a i, 72 * i), (b i, 72 * i + 256)])).map
    (fun t => (t.1, t.2 + 440 * j)))

theorem spTerms_mem (a b : Nat → Nat) (t : Nat × Nat) : t ∈ spTerms a b →
    ∃ i j, i < 16 ∧ j < 16 ∧ ((t.1 = a i ∧ t.2 = 72 * i + 440 * j) ∨ (t.1 = b i ∧ t.2 = 72 * i + 256 + 440 * j)) := by
  intro h
  simp only [spTerms, List.mem_flatMap, List.mem_range, List.mem_map, List.mem_cons, List.mem_nil_iff, or_false] at h
  obtain ⟨j, hj, ⟨v, q⟩, ⟨i, hi, hvq⟩, rfl⟩ := h
  rcases hvq with h | h
  · simp only [Prod.mk.injEq] at h; obtain ⟨rfl, rfl⟩ := h
    exact ⟨i, j, hi, hj, Or.inl ⟨rfl, rfl⟩⟩
  · simp only [Prod.mk.injEq] at h; obtain ⟨rfl, rfl⟩ := h
    exact ⟨i, j, hi, hj, Or.inr ⟨rfl, rfl⟩⟩

theorem spTerms_sum (a b : Nat → Nat) :
    (enc 72 a 16 + 2 ^ 256 * enc 72 b 16) * enc 440 (fun _ => 1) 16 = tsum (spTerms a b) := by
  have h1 : enc 72 a 16 + 2 ^ 256 * enc 72 b 16 = tsum ((List.range 16).flatMap (fun i => [(a i, 72 * i), (b i, 72 * i + 256)])) := by
    rw [tsum_flatMap]
    rw [enc_tsum, enc_tsum, Nat.mul_comm (2 ^ 256)]
    simp only [tsum]
    rw [← tsum_shift]
    simp only [List.map_map]
    generalize List.range 16 = l
    induction l with
    | nil => rfl
    | cons x l ih => simp only [List.map_cons, tsum, List.sum_cons, Function.comp]; omega
  rw [h1, tsum_mul_enc_ones]
  rfl

/-- The positions of the spread terms are bit-disjoint `4`-bit fields. -/
theorem spTerms_sep (a b : Nat → Nat) : sep 4 (spTerms a b) := by
  have key : ∀ ts : List (Nat × Nat), sep 4 (ts.map (fun t => (0, t.2))) → sep 4 ts := by
    intro ts
    induction ts with
    | nil => intro _; trivial
    | cons t ts ih =>
      intro ⟨h1, h2⟩
      refine ⟨fun u hu => ?_, ih h2⟩
      have := h1 (0, u.2) (List.mem_map.mpr ⟨u, hu, rfl⟩)
      exact this
  apply key
  have e : (spTerms a b).map (fun t => (0, t.2)) = (spTerms (fun _ => 0) (fun _ => 0)).map (fun t => (0, t.2)) := by
    simp [spTerms, List.map_flatMap]
  rw [e]
  exact sep_of_sepB 4 _ (by decide +kernel)


theorem tbit_iff (w p : Nat) : ∀ ts : List (Nat × Nat),
    tbit w p ts = true ↔ ∃ t ∈ ts, t.2 ≤ p ∧ p < t.2 + w ∧ t.1.testBit (p - t.2) = true
  | [] => by simp [tbit]
  | (v, q) :: ts => by
    simp only [tbit, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq, tbit_iff w p ts,
      List.mem_cons, exists_eq_or_imp]
    constructor
    · intro h
      rcases h with ⟨⟨h1, h2⟩, h3⟩ | h
      · exact Or.inl ⟨h1, h2, h3⟩
      · exact Or.inr h
    · intro h
      rcases h with ⟨h1, h2, h3⟩ | h
      · exact Or.inl ⟨⟨h1, h2⟩, h3⟩
      · exact Or.inr h

theorem tb15 (q : Nat) : (15 + 15 * 2 ^ 256).testBit q = (decide (q < 4) || (decide (256 ≤ q) && decide (q < 260))) := by
  rw [Nat.add_comm, Nat.mul_comm, Nat.testBit_two_pow_mul_add 15 (by decide : (15 : Nat) < 2 ^ 256)]
  have t15 : ∀ r, (15 : Nat).testBit r = decide (r < 4) := fun r => by
    rw [show (15 : Nat) = 2 ^ 4 - 1 from rfl, Nat.testBit_two_pow_sub_one]
  split
  · rename_i hq
    rw [t15]; apply Bool.eq_iff_iff.mpr; simp only [Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]; omega
  · rename_i hq
    rw [t15]; apply Bool.eq_iff_iff.mpr; simp only [Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]; omega

theorem tb_ab (x y q : Nat) (hx : x < 16) :
    (x + 2 ^ 256 * y).testBit q = if q < 256 then x.testBit q else y.testBit (q - 256) := by
  rw [Nat.add_comm, Nat.testBit_two_pow_mul_add y (Nat.lt_of_lt_of_le hx (by decide))]

theorem spread_eq (a b : Nat → Nat) (ha : ∀ i, i < 16 → a i < 16) (hb : ∀ i, i < 16 → b i < 16) :
    Nat.land (Nat.mul (Nat.add (enc 72 a 16) (Nat.shiftLeft (enc 72 b 16) 256)) (enc 440 (fun _ => 1) 16))
      (enc 512 (fun _ => 15 + 15 * 2 ^ 256) 16) = enc 512 (fun i => a i + 2 ^ 256 * b i) 16 := by
  have e1 : Nat.add (enc 72 a 16) (Nat.shiftLeft (enc 72 b 16) 256) = enc 72 a 16 + 2 ^ 256 * enc 72 b 16 := by
    show enc 72 a 16 + enc 72 b 16 <<< 256 = _
    rw [Nat.shiftLeft_eq, Nat.mul_comm]
  rw [e1, show Nat.mul (enc 72 a 16 + 2 ^ 256 * enc 72 b 16) (enc 440 (fun _ => 1) 16)
      = (enc 72 a 16 + 2 ^ 256 * enc 72 b 16) * enc 440 (fun _ => 1) 16 from rfl, spTerms_sum]
  have hbd : ∀ t ∈ spTerms a b, t.1 < 2 ^ 4 := by
    intro t ht
    obtain ⟨i, j, hi, _, h⟩ := spTerms_mem a b t ht
    rcases h with ⟨h1, _⟩ | ⟨h1, _⟩ <;> rw [h1]
    · exact ha i hi
    · exact hb i hi
  apply Nat.eq_of_testBit_eq; intro p
  rw [show Nat.land (tsum (spTerms a b)) (enc 512 (fun _ => 15 + 15 * 2 ^ 256) 16)
      = tsum (spTerms a b) &&& enc 512 (fun _ => 15 + 15 * 2 ^ 256) 16 from rfl,
    Nat.testBit_and, tsum_tb 4 _ hbd (spTerms_sep a b),
    enc_tb 512 (by decide) _ p 16 (fun _ _ => by decide +kernel),
    enc_tb 512 (by decide) _ p 16 (fun i hi => by
      have := ha i hi; have := hb i hi
      calc a i + 2 ^ 256 * b i < 16 + 2 ^ 256 * 16 := by
            have : 2 ^ 256 * b i ≤ 2 ^ 256 * 15 := Nat.mul_le_mul_left _ (by omega)
            omega
        _ ≤ 2 ^ 512 := by decide +kernel), tb15]
  clear e1 hbd
  by_cases hk : p / 512 < 16
  · have hq := Nat.mod_lt p (show 0 < 512 by decide)
    have hp := Nat.div_add_mod p 512
    rw [tb_ab _ _ _ (ha _ hk)]
    simp only [hk, decide_true, Bool.true_and]
    generalize hk' : p / 512 = k at *
    generalize hq' : p % 512 = q at *
    by_cases c1 : q < 4
    · -- the `a k` field
      simp only [c1, decide_true, Bool.true_or, Bool.and_true, show q < 256 by omega, ↓reduceIte]
      apply Bool.eq_iff_iff.mpr
      rw [tbit_iff]
      constructor
      · rintro ⟨t, ht, h1, h2, h3⟩
        obtain ⟨i, j, hi, hj, h⟩ := spTerms_mem a b t ht
        rcases h with ⟨e1, e2⟩ | ⟨e1, e2⟩
        · have : i = k ∧ j = k := by omega
          rw [this.1] at e1; rw [this.1, this.2] at e2
          rw [e1, e2] at h3
          have ex : p - (72 * k + 440 * k) = q := by omega
          rw [ex] at h3; exact h3
        · omega
      · intro h
        refine ⟨(a k, 72 * k + 440 * k), ?_, by omega, by omega, ?_⟩
        · simp only [spTerms, List.mem_flatMap, List.mem_range, List.mem_map]
          exact ⟨k, hk, (a k, 72 * k), ⟨k, hk, by simp⟩, rfl⟩
        · have ex : p - (72 * k + 440 * k) = q := by omega
          show (a k).testBit (p - (72 * k + 440 * k)) = true
          rw [ex]; exact h
    · by_cases c2 : 256 ≤ q ∧ q < 260
      · simp only [c1, decide_false, Bool.false_or, c2.1, c2.2, decide_true, Bool.and_self, Bool.and_true,
          show ¬ q < 256 by omega, ↓reduceIte]
        apply Bool.eq_iff_iff.mpr
        rw [tbit_iff]
        constructor
        · rintro ⟨t, ht, h1, h2, h3⟩
          obtain ⟨i, j, hi, hj, h⟩ := spTerms_mem a b t ht
          rcases h with ⟨e1, e2⟩ | ⟨e1, e2⟩
          · omega
          · have : i = k ∧ j = k := by omega
            rw [this.1] at e1; rw [this.1, this.2] at e2
            rw [e1, e2] at h3
            have ex : p - (72 * k + 256 + 440 * k) = q - 256 := by omega
            rw [ex] at h3; exact h3
        · intro h
          refine ⟨(b k, 72 * k + 256 + 440 * k), ?_, by omega, by omega, ?_⟩
          · simp only [spTerms, List.mem_flatMap, List.mem_range, List.mem_map]
            exact ⟨k, hk, (b k, 72 * k + 256), ⟨k, hk, by simp⟩, rfl⟩
          · have ex : p - (72 * k + 256 + 440 * k) = q - 256 := by omega
            show (b k).testBit (p - (72 * k + 256 + 440 * k)) = true
            rw [ex]; exact h
      · have : (decide (q < 4) || (decide (256 ≤ q) && decide (q < 260))) = false := by
          by_cases c3 : 256 ≤ q
          · simp [c1, c3, show ¬ q < 260 from fun h => c2 ⟨c3, h⟩]
          · simp [c1, c3]
        rw [this, Bool.and_false]
        symm
        split
        · exact Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (ha k hk)
            (Nat.pow_le_pow_right (by decide) (by omega) : 2 ^ 4 ≤ 2 ^ q))
        · exact Nat.testBit_lt_two_pow (Nat.lt_of_lt_of_le (hb k hk)
            (Nat.pow_le_pow_right (by decide) (by omega) : 2 ^ 4 ≤ 2 ^ (q - 256)))
  · simp [hk]

end P8
end Submission

end


/-! # Proof part: Lanes -/

section
namespace Submission
namespace P8

theorem enc_succ (W : Nat) (f : Nat → Nat) (L : Nat) : enc W f (L + 1) = enc W f L + f L * 2 ^ (W * L) := rfl

/-- Nested lanes: `L` outer lanes of `32` inner `16`-bit sub-lanes = `32 L` flat sub-lanes. -/
theorem enc_nest (g : Nat → Nat → Nat) : ∀ L,
    enc 512 (fun i => enc 16 (g i) 32) L = enc 16 (fun t => g (t / 32) (t % 32)) (32 * L)
  | 0 => by rw [Nat.mul_zero, enc, enc]
  | L + 1 => by
    have h1 := enc_succ 512 (fun i => enc 16 (g i) 32) L
    have h2 := enc_split 16 (fun t => g (t / 32) (t % 32)) (32 * L) 32
    have h3 : 32 * (L + 1) = 32 * L + 32 := by omega
    have h4 : enc 16 (fun m => (fun t => g (t / 32) (t % 32)) (32 * L + m)) 32 = enc 16 (g L) 32 := by
      apply enc_congr; intro t ht
      show g ((32 * L + t) / 32) ((32 * L + t) % 32) = g L t
      have e1 : (32 * L + t) / 32 = L := by omega
      have e2 : (32 * L + t) % 32 = t := by omega
      rw [e1, e2]
    have h5 : 2 ^ (16 * (32 * L)) = 2 ^ (512 * L) := by rw [show 16 * (32 * L) = 512 * L by omega]
    rw [h1, h3, h2, h4, h5, enc_nest g L, Nat.mul_comm (2 ^ (512 * L))]

end P8
end Submission

namespace Submission
namespace P8

theorem enc_halves (f g : Nat → Nat) :
    enc 16 f 16 + 2 ^ 256 * enc 16 g 16 = enc 16 (fun t => if t < 16 then f t else g (t - 16)) 32 := by
  have h := enc_split 16 (fun t => if t < 16 then f t else g (t - 16)) 16 16
  rw [show (16 : Nat) + 16 = 32 from rfl, show (16 : Nat) * 16 = 256 from rfl] at h
  rw [h]
  have e1 : enc 16 (fun t => if t < 16 then f t else g (t - 16)) 16 = enc 16 f 16 :=
    enc_congr 16 16 (fun t ht => by simp [ht])
  have e2 : enc 16 (fun m => (fun t => if t < 16 then f t else g (t - 16)) (16 + m)) 16 = enc 16 g 16 :=
    enc_congr 16 16 (fun t _ => by
      show (if 16 + t < 16 then f (16 + t) else g (16 + t - 16)) = g t
      rw [if_neg (by omega), show 16 + t - 16 = t by omega])
  rw [e1, e2]

theorem rep_eq (x w n : Nat) : x * enc w (fun _ => 1) n = enc w (fun _ => x) n := by
  rw [Nat.mul_comm, enc_mulc]; apply enc_congr; intro _ _; simp

end P8
end Submission

end


/-! # Proof part: DP -/

section
namespace Submission
namespace P8

/-! ## Generic packed-DP facts -/

theorem enc_shl (W : Nat) (f : Nat → Nat) : ∀ L d, enc W f L <<< (W * d)
    = enc W (fun i => if d ≤ i then f (i - d) else 0) (L + d) := by
  intro L d
  induction d with
  | zero =>
    simp only [Nat.mul_zero, Nat.shiftLeft_zero, Nat.add_zero]
    apply enc_congr; intro i _; simp
  | succ d ih =>
    rw [show L + (d + 1) = (d + 1) + L by omega, enc_split]
    rw [enc_zero W (d + 1) (fun i hi => if_neg (by omega)), Nat.zero_add, Nat.shiftLeft_eq]
    rw [Nat.mul_comm (enc W f L)]
    congr 1
    apply enc_congr; intro i _
    simp only [show d + 1 ≤ d + 1 + i by omega, ↓reduceIte, show d + 1 + i - (d + 1) = i by omega]

theorem enc_shl' (W : Nat) (f : Nat → Nat) (L d : Nat) : Nat.shiftLeft (enc W f L) (W * d)
    = enc W (fun i => if d ≤ i then f (i - d) else 0) (L + d) := enc_shl W f L d

theorem enc_pad' (W : Nat) (f : Nat → Nat) (L L' : Nat) (h : L ≤ L') (hz : ∀ i, L ≤ i → i < L' → f i = 0) :
    enc W f L = enc W f L' := by
  rw [enc_pad W f L L' h]
  apply enc_congr; intro i hi
  by_cases h' : i < L
  · simp [h']
  · simp [h', hz i (by omega) hi]

/-- Lanes of a bounded encoding, read by shift + mask. -/
theorem enc_lane_and (W : Nat) (f : Nat → Nat) (L j : Nat) (hj : j < L) (hf : ∀ m, m < L → f m < 2 ^ W) :
    (enc W f L >>> (W * j)) &&& (2 ^ W - 1) = f j := by
  rw [Nat.and_two_pow_sub_one_eq_mod, enc_get W f L j hj hf]

/-! ## Forward weighted counts over a row sequence -/

variable (e : Nat → Nat) (R : Nat → List Nat)

/-- `F k t`: sequences choosing a column of each of the rows `R 0 … R (k-1)` with weights summing to `t`. -/
def F : Nat → Nat → Nat
  | 0, t => if t = 0 then 1 else 0
  | k + 1, t => ((R k).map (fun c => if e c ≤ t then F k (t - e c) else 0)).sum

theorem F_cnt : ∀ k t, F e R k t = cnt e ((List.range k).map R).reverse t
  | 0, t => by simp [F, cnt]
  | k + 1, t => by
    rw [List.range_succ, List.map_append, List.reverse_append]
    simp only [List.map_cons, List.map_nil, List.reverse_cons, List.reverse_nil, List.nil_append,
      List.cons_append]
    simp only [F, cnt]
    apply sum_map_congr; intro c _
    split <;> simp [F_cnt k]

theorem F_le_pow (h3 : ∀ k, (R k).length ≤ 3) : ∀ k t, F e R k t ≤ 3 ^ k
  | 0, t => by simp only [F]; split <;> simp
  | k + 1, t => by
    simp only [F]
    have : ∀ l : List Nat, l.length ≤ 3 → (l.map (fun c => if e c ≤ t then F e R k (t - e c) else 0)).sum ≤ l.length * 3 ^ k := by
      intro l _
      induction l with
      | nil => simp
      | cons c l ih =>
        simp only [List.map_cons, List.sum_cons, List.length_cons]
        have h1 : (if e c ≤ t then F e R k (t - e c) else 0) ≤ 3 ^ k := by
          split
          · exact F_le_pow h3 k _
          · exact Nat.zero_le _
        have := ih (by simp at *; omega)
        rw [Nat.succ_mul]; omega
    have h := this (R k) (h3 k)
    calc _ ≤ (R k).length * 3 ^ k := h
      _ ≤ 3 * 3 ^ k := Nat.mul_le_mul_right _ (h3 k)
      _ = 3 ^ (k + 1) := by rw [Nat.pow_succ, Nat.mul_comm]


-- each row's weight multiset, sorted
variable (lo mid hi : Nat → Nat)

theorem F_succ_tri (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k]) (k t : Nat) :
    F e R (k + 1) t = (if lo k ≤ t then F e R k (t - lo k) else 0)
      + (if mid k ≤ t then F e R k (t - mid k) else 0) + (if hi k ≤ t then F e R k (t - hi k) else 0) := by
  simp only [F]
  have h := ((hR k).map (fun w => if w ≤ t then F e R k (t - w) else 0)).sum_nat
  rw [List.map_map] at h
  have e1 : ((fun w => if w ≤ t then F e R k (t - w) else 0) ∘ e)
      = (fun c => if e c ≤ t then F e R k (t - e c) else 0) := rfl
  rw [e1] at h
  rw [h]
  simp [Nat.add_assoc]

/-- Lower and upper support of `F`. -/
def mp : Nat → Nat
  | 0 => 0
  | k + 1 => mp k + lo k

def sp : Nat → Nat
  | 0 => 0
  | k + 1 => sp k + (hi k - lo k)

theorem F_supp (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) :
    ∀ k t, (t < mp lo k ∨ mp lo k + sp lo hi k < t) → F e R k t = 0
  | 0, t, h => by simp only [F, mp, sp] at *; split <;> omega
  | k + 1, t, h => by
    rw [F_succ_tri e R lo mid hi hR]
    have h1 := hs k
    simp only [mp, sp] at h
    have z : ∀ w, lo k ≤ w → w ≤ hi k → (if w ≤ t then F e R k (t - w) else 0) = 0 := by
      intro w hw1 hw2
      split
      · exact F_supp hR hs k _ (by omega)
      · rfl
    rw [z _ (Nat.le_refl _) (by omega), z _ h1.1 h1.2, z _ (by omega) (Nat.le_refl _)]

/-! ### Phase 1: base `mp k`, left shifts -/

variable (W : Nat)

def P1st (z y : Nat → Nat) : Nat → Nat
  | 0 => 1
  | k + 1 => stepL (P1st z y k) (z k) (y k)

theorem P1st_eq (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (z y : Nat → Nat)
    (hz : ∀ k, z k = W * (mid k - lo k)) (hy : ∀ k, y k = W * (hi k - lo k)) :
    ∀ k, P1st z y k = enc W (fun i => F e R k (i + mp lo k)) (sp lo hi k + 1)
  | 0 => by simp [P1st, enc, F, mp, sp]
  | k + 1 => by
    simp only [P1st, stepL]
    rw [P1st_eq hR hs z y hz hy k, hz k, hy k, enc_shl', enc_shl']
    have h1 := hs k
    have L1 : sp lo hi (k + 1) + 1 = sp lo hi k + 1 + (hi k - lo k) := by simp only [sp]; omega
    rw [L1]
    -- pad all three to the common length
    rw [enc_pad' W (fun i => F e R k (i + mp lo k)) (sp lo hi k + 1) (sp lo hi k + 1 + (hi k - lo k))
        (by omega) (fun i hi1 _ => F_supp e R lo mid hi hR hs k _ (Or.inr (by omega))),
      enc_pad' W (fun i => if mid k - lo k ≤ i then F e R k (i - (mid k - lo k) + mp lo k) else 0)
        (sp lo hi k + 1 + (mid k - lo k)) (sp lo hi k + 1 + (hi k - lo k)) (by omega)
        (fun i hi1 _ => by
          split
          · exact F_supp e R lo mid hi hR hs k _ (Or.inr (by omega))
          · rfl),
      P_add, P_add]
    apply enc_congr; intro i _
    rw [F_succ_tri e R lo mid hi hR, show mp lo (k + 1) = mp lo k + lo k from rfl]
    have a1 : (if lo k ≤ i + (mp lo k + lo k) then F e R k (i + (mp lo k + lo k) - lo k) else 0)
        = F e R k (i + mp lo k) := by rw [if_pos (by omega)]; congr 1; omega
    have a2 : (if mid k ≤ i + (mp lo k + lo k) then F e R k (i + (mp lo k + lo k) - mid k) else 0)
        = (if mid k - lo k ≤ i then F e R k (i - (mid k - lo k) + mp lo k) else 0) := by
      by_cases h : mid k - lo k ≤ i
      · rw [if_pos (by omega), if_pos h]; congr 1; omega
      · rw [if_neg h]
        split
        · exact F_supp e R lo mid hi hR hs k _ (Or.inl (by omega))
        · rfl
    have a3 : (if hi k ≤ i + (mp lo k + lo k) then F e R k (i + (mp lo k + lo k) - hi k) else 0)
        = (if hi k - lo k ≤ i then F e R k (i - (hi k - lo k) + mp lo k) else 0) := by
      by_cases h : hi k - lo k ≤ i
      · rw [if_pos (by omega), if_pos h]; congr 1; omega
      · rw [if_neg h]
        split
        · exact F_supp e R lo mid hi hR hs k _ (Or.inl (by omega))
        · rfl
    rw [a1, a2, a3]


/-! ### Phase 2: base `T - D k`, right shifts -/

/-- `suf f k n = f k + … + f (k + n - 1)`. -/
def suf (f : Nat → Nat) : Nat → Nat → Nat
  | _, 0 => 0
  | k, n + 1 => f k + suf f (k + 1) n

variable (T n : Nat)

/-- Lane `i` at level `k`: sequences of the first `k` rows with weight `i + T - D k`, where `D k` is the
sum of the remaining rows' maxima. -/
def G (k i : Nat) : Nat :=
  if suf hi k (n - k) ≤ i + T then F e R k (i + T - suf hi k (n - k)) else 0

theorem G_succ (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (k i : Nat) (hk : k < n) :
    G e R hi T n (k + 1) i = G e R hi T n k i + G e R hi T n k (i + (hi k - mid k))
      + G e R hi T n k (i + (hi k - lo k)) := by
  have hD : suf hi k (n - k) = hi k + suf hi (k + 1) (n - (k + 1)) := by
    rw [show n - k = (n - (k + 1)) + 1 by omega]; rfl
  unfold G
  rw [hD]
  generalize suf hi (k + 1) (n - (k + 1)) = D'
  have h1 := hs k
  by_cases hc : D' ≤ i + T
  · rw [if_pos hc, F_succ_tri e R lo mid hi hR]
    have g1 : (if hi k + D' ≤ i + T then F e R k (i + T - (hi k + D')) else 0)
        = (if hi k ≤ i + T - D' then F e R k (i + T - D' - hi k) else 0) := by
      by_cases h : hi k + D' ≤ i + T
      · rw [if_pos h, if_pos (by omega)]; congr 1; omega
      · rw [if_neg h, if_neg (by omega)]
    have g2 : (if hi k + D' ≤ i + (hi k - mid k) + T then F e R k (i + (hi k - mid k) + T - (hi k + D')) else 0)
        = (if mid k ≤ i + T - D' then F e R k (i + T - D' - mid k) else 0) := by
      by_cases h : mid k ≤ i + T - D'
      · rw [if_pos (by omega), if_pos h]; congr 1; omega
      · rw [if_neg (by omega), if_neg h]
    have g3 : (if hi k + D' ≤ i + (hi k - lo k) + T then F e R k (i + (hi k - lo k) + T - (hi k + D')) else 0)
        = (if lo k ≤ i + T - D' then F e R k (i + T - D' - lo k) else 0) := by
      by_cases h : lo k ≤ i + T - D'
      · rw [if_pos (by omega), if_pos h]; congr 1; omega
      · rw [if_neg (by omega), if_neg h]
    rw [g1, g2, g3]; omega
  · rw [if_neg hc, if_neg (by omega), if_neg (by omega), if_neg (by omega)]

/-- One phase-2 step on a bounded encoding. -/
theorem stepR_enc (g : Nat → Nat) (N d1 d2 : Nat) (_hW : 0 < W) (hg : ∀ m, m < N → g m < 2 ^ W)
    (hz : ∀ m, N ≤ m → g m = 0) :
    stepR (enc W g N) (W * d1) (W * d2) = enc W (fun i => g i + g (i + d1) + g (i + d2)) N := by
  have shr : ∀ d, Nat.shiftRight (enc W g N) (W * d) = enc W (fun i => g (i + d)) N := by
    intro d
    by_cases hd : d ≤ N
    · have := enc_shiftRight W g d N hd hg
      rw [show Nat.shiftRight (enc W g N) (W * d) = enc W g N >>> (W * d) from rfl, this]
      apply enc_pad' W _ (N - d) N (by omega) (fun i hi1 _ => hz _ (by omega)) |>.trans
      apply enc_congr; intro i _; rw [Nat.add_comm]
    · have hlt := enc_lt W g N hg
      rw [show Nat.shiftRight (enc W g N) (W * d) = enc W g N >>> (W * d) from rfl,
        Nat.shiftRight_eq_div_pow, Nat.div_eq_of_lt (Nat.lt_of_lt_of_le hlt (Nat.pow_le_pow_right (by omega)
          (Nat.mul_le_mul_left _ (by omega))))]
      exact (enc_zero W N (fun i _ => hz _ (by omega))).symm
  unfold stepR
  rw [shr, shr, P_add, P_add]

end P8
end Submission

end


/-! # Proof part: Stage1 -/

section
set_option exponentiation.threshold 100000

namespace Submission
namespace P8

theorem c16_MSP_eq : c16_MSP = enc 440 (fun _ => 1) 16 := by decide +kernel
theorem c16_M4_eq : c16_M4 = enc 512 (fun _ => 15 + 15 * 2 ^ 256) 16 := by decide +kernel
theorem c16_REP16_eq : c16_REP16 = enc 16 (fun _ => 1) 16 := by decide +kernel
theorem c16_CPAT_eq : c16_CPAT = enc 16 (fun t => t % 16) 512 := by decide +kernel
theorem c16_K15_eq : c16_K15 = enc 16 (fun _ => 15) 512 := by decide +kernel
theorem c16_ONESUB_eq : c16_ONESUB = enc 16 (fun _ => 1) 512 := by decide +kernel
theorem c16_LOW_eq : c16_LOW = enc 512 (fun _ => 2 ^ 256 - 1) 16 := by decide +kernel
theorem c16_DIAG_eq : c16_DIAG = enc 512 (fun i => enc 16 (fun t => if i = t then 1 else 0) 16) 16 := by decide +kernel

/-- Per sub-lane: the zero test. -/
theorem zt4 : ∀ x, x < 16 → ∀ c, c < 16 → 1 - (((x ^^^ c) + 15) >>> 4 &&& 1) = if x = c then 1 else 0 := by
  decide


/-- The indicator of the column set of row `i` (columns `i`, `a i`, `b i`). -/
def rowInd (a b : Nat → Nat) (i t : Nat) : Nat :=
  (if a i = t then 1 else 0) + (if b i = t then 1 else 0) + (if i = t then 1 else 0)

theorem rowV_eq (a b : Nat → Nat) (ha : ∀ i, i < 16 → a i < 16) (hb : ∀ i, i < 16 → b i < 16) :
    rowV (enc 72 a 16) (enc 72 b 16) = enc 512 (fun i => enc 16 (rowInd a b i) 16) 16 := by
  -- spread, then replicate into the 32 sub-lanes of each row lane
  have hSP := spread_eq a b ha hb
  rw [← c16_MSP_eq, ← c16_M4_eq] at hSP
  let x : Nat → Nat → Nat := fun i t => if t < 16 then a i else b i
  have hREP : Nat.mul (enc 512 (fun i => a i + 2 ^ 256 * b i) 16) c16_REP16
      = enc 16 (fun t => x (t / 32) (t % 32)) 512 := by
    rw [c16_REP16_eq, P_mulr]
    have : ∀ i, (a i + 2 ^ 256 * b i) * enc 16 (fun _ => 1) 16 = enc 16 (x i) 32 := by
      intro i
      rw [Nat.add_mul, Nat.mul_assoc, rep_eq, rep_eq, enc_halves]
    rw [show (fun m => (a m + 2 ^ 256 * b m) * enc 16 (fun _ => 1) 16) = (fun m => enc 16 (x m) 32) from
      funext this, enc_nest]
  have hx : ∀ t, t < 512 → x (t / 32) (t % 32) < 16 := by
    intro t ht
    show (if t % 32 < 16 then a (t / 32) else b (t / 32)) < 16
    split
    · exact ha _ (by omega)
    · exact hb _ (by omega)
  have h16 : (0 : Nat) < 16 := by decide
  -- xor with the pattern, add 15, shift-and-mask, complement
  have hV : Nat.xor (enc 16 (fun t => x (t / 32) (t % 32)) 512) c16_CPAT
      = enc 16 (fun t => x (t / 32) (t % 32) ^^^ (t % 16)) 512 := by
    rw [c16_CPAT_eq, P_xor 16 h16 _ _ 512 (fun t ht => Nat.lt_of_lt_of_le (hx t ht) (by decide))
      (fun t _ => Nat.lt_of_lt_of_le (Nat.mod_lt _ (by decide)) (by decide))]
  have hxor : ∀ t, t < 512 → x (t / 32) (t % 32) ^^^ (t % 16) < 16 := fun t ht =>
    Nat.xor_lt_two_pow (n := 4) (hx t ht) (Nat.mod_lt t (by decide : 0 < 16))
  have hA : Nat.add (enc 16 (fun t => x (t / 32) (t % 32) ^^^ (t % 16)) 512) c16_K15
      = enc 16 (fun t => (x (t / 32) (t % 32) ^^^ (t % 16)) + 15) 512 := by
    rw [c16_K15_eq, P_add]
  have hS : Nat.land (Nat.shiftRight (enc 16 (fun t => (x (t / 32) (t % 32) ^^^ (t % 16)) + 15) 512) 4) c16_ONESUB
      = enc 16 (fun t => ((x (t / 32) (t % 32) ^^^ (t % 16)) + 15) >>> 4 &&& 1) 512 := by
    rw [c16_ONESUB_eq, P_shr_and 16 h16 _ _ 4 512 (by decide)
      (fun t ht => by have := hxor t ht; omega) (fun _ _ => by decide)]
  have hO : Nat.sub c16_ONESUB (enc 16 (fun t => ((x (t / 32) (t % 32) ^^^ (t % 16)) + 15) >>> 4 &&& 1) 512)
      = enc 16 (fun t => if x (t / 32) (t % 32) = t % 16 then 1 else 0) 512 := by
    rw [c16_ONESUB_eq, P_sub 16 _ _ 512 (fun t _ => Nat.and_le_right)]
    apply enc_congr; intro t ht
    exact zt4 _ (hx t ht) _ (Nat.mod_lt _ (by decide))
  -- back to row lanes
  let ind : Nat → Nat → Nat := fun i t => if x i t = t % 16 then 1 else 0
  have hN : enc 16 (fun t => if x (t / 32) (t % 32) = t % 16 then 1 else 0) 512 = enc 512 (fun i => enc 16 (ind i) 32) 16 := by
    rw [enc_nest]
    apply enc_congr; intro t ht
    show (if x (t / 32) (t % 32) = t % 16 then 1 else 0) = (if x (t / 32) (t % 32) = t % 32 % 16 then 1 else 0)
    rw [show t % 32 % 16 = t % 16 by omega]
  have hind : ∀ i t, t < 32 → ind i t < 2 ^ 16 := fun i t _ => by
    show (if x i t = t % 16 then 1 else 0) < 2 ^ 16
    split <;> decide
  have henc32 : ∀ i, enc 16 (ind i) 32 < 2 ^ 512 := fun i => enc_lt 16 _ 32 (fun t ht => hind i t ht)
  -- the fold: low half (a), high half (b), diagonal
  have hlo : ∀ i, enc 16 (ind i) 32 &&& (2 ^ 256 - 1) = enc 16 (fun t => if a i = t then 1 else 0) 16 := by
    intro i
    rw [Nat.and_two_pow_sub_one_eq_mod, show (32 : Nat) = 16 + 16 from rfl,
      show (256 : Nat) = 16 * 16 from rfl, enc_low 16 _ 16 16 (fun t ht => hind i t ht)]
    apply enc_congr; intro t ht
    show (if (if t < 16 then a i else b i) = t % 16 then 1 else 0) = (if a i = t then 1 else 0)
    rw [if_pos ht, Nat.mod_eq_of_lt ht]
  have hhi : ∀ i, (enc 16 (ind i) 32 >>> 256) &&& (2 ^ 256 - 1) = enc 16 (fun t => if b i = t then 1 else 0) 16 := by
    intro i
    rw [Nat.and_two_pow_sub_one_eq_mod, show (32 : Nat) = 16 + 16 from rfl,
      show (256 : Nat) = 16 * 16 from rfl, enc_high 16 _ 16 16 (fun t ht => hind i t ht)]
    rw [Nat.mod_eq_of_lt (enc_lt 16 _ 16 (fun t ht => hind i _ (by omega)))]
    apply enc_congr; intro t ht
    show (if (if 16 + t < 16 then a i else b i) = (16 + t) % 16 then 1 else 0) = (if b i = t then 1 else 0)
    rw [show (if 16 + t < 16 then a i else b i) = b i from if_neg (by omega), show (16 + t) % 16 = t by omega]
  -- assemble
  unfold rowV ohFold
  rw [hSP, hREP, hV, hA, hS, hO, hN, c16_LOW_eq, c16_DIAG_eq,
    P_and 512 (by decide) _ _ 16 (fun i _ => henc32 i) (fun _ _ => by decide +kernel),
    P_shr_and 512 (by decide) _ _ 256 16 (by decide) (fun i _ => henc32 i) (fun _ _ => by decide +kernel),
    P_add, P_add]
  apply enc_congr; intro i _
  rw [hlo, hhi, ← enc_add, ← enc_add]
  apply enc_congr; intro t _
  rfl

end P8
end Submission

end


/-! # Proof part: Stage2 -/

section
set_option exponentiation.threshold 100000

namespace Submission
namespace P8

/-- Masking with a constant per-lane pattern exposes the lanes of any number. -/
theorem land_lanes (X m L : Nat) (hm : m < 2 ^ 512) :
    Nat.land X (enc 512 (fun _ => m) L) = enc 512 (fun i => ((X >>> (512 * i)) % 2 ^ 512) &&& m) L := by
  show X &&& _ = _
  rw [land_mod_of_lt _ _ _ (enc_lt 512 _ L (fun _ _ => hm)), digits_enc,
    enc_and 512 (by decide) _ _ L (fun _ _ => Nat.mod_lt _ (Nat.two_pow_pos _)) (fun _ _ => hm)]

theorem c16_L05_eq : c16_L05 = enc 512 (fun _ => 31) 16 := by decide +kernel
theorem c16_L016_eq : c16_L016 = enc 512 (fun _ => 0xffff) 16 := by decide +kernel
theorem c16_CPAT1_eq : c16_CPAT1 = enc 16 (fun t => if t % 32 < 16 then t % 32 + 1 else 0) 512 := by decide +kernel
theorem c16_K31_eq : c16_K31 = enc 16 (fun t => if t % 32 < 16 then 31 else 0) 512 := by decide +kernel
theorem c16_ONES16L_eq : c16_ONES16L = enc 16 (fun t => if t % 32 < 16 then 1 else 0) 512 := by decide +kernel
theorem c16_ONESL_eq : c16_ONESL = enc 512 (fun _ => 1) 16 := by decide +kernel
theorem c16_M512_eq : c16_M512 = 2 ^ 512 - 1 := by decide +kernel

/-- Any number masked with the `31`-per-lane pattern is an encoding with lanes `< 32`. -/
theorem mask31_lanes (X : Nat) : ∃ ρ : Nat → Nat, (∀ i, ρ i < 32) ∧ Nat.land X c16_L05 = enc 512 ρ 16 :=
  ⟨fun i => ((X >>> (512 * i)) % 2 ^ 512) &&& 31, fun i => Nat.lt_of_le_of_lt Nat.and_le_right (by decide),
    by rw [c16_L05_eq, land_lanes X 31 16 (by decide)]⟩

theorem labRK_lanes (ROW : Nat) : ∃ ρ : Nat → Nat, (∀ i, ρ i < 32) ∧ labRK ROW = enc 512 ρ 16 := by
  unfold labRK rank16; exact mask31_lanes _

theorem zt5 : ∀ r, r < 32 → ∀ c, c < 16 → 1 - (((r ^^^ (c + 1)) + 31) >>> 5 &&& 1) = if r = c + 1 then 1 else 0 := by
  decide


/-- Lane value of the weight vector: `2^(r-1)` for a valid rank `r ∈ [1, 16]`, else `0`. -/
def epow (r : Nat) : Nat := if 1 ≤ r ∧ r ≤ 16 then 2 ^ (r - 1) else 0

theorem epow_lane : ∀ r, r < 32 →
    ((enc 16 (fun k => if r = k + 1 then 1 else 0) 16 * c16_MG) >>> 225) &&& 0xffff = epow r := by
  decide +kernel

theorem enc_nest512 (g : Nat → Nat → Nat) :
    enc 512 (fun i => enc 16 (g i) 32) 16 = enc 16 (fun t => g (t / 32) (t % 32)) 512 := enc_nest g 16

theorem enc_pad16 (f : Nat → Nat) : enc 16 f 16 = enc 16 (fun t => if t < 16 then f t else 0) 32 := by
  rw [enc_pad 16 f 16 32 (by decide)]

theorem oh16_eq (ρ : Nat → Nat) (hρ : ∀ i, ρ i < 32) :
    oh16 (enc 512 ρ 16) = enc 512 (fun i => enc 16 (fun k => if ρ i = k + 1 then 1 else 0) 16) 16 := by
  have h16 : (0 : Nat) < 16 := by decide
  let y : Nat → Nat := fun t => if t % 32 < 16 then ρ (t / 32) else 0
  have hy : ∀ t, y t < 32 := fun t => by
    show (if t % 32 < 16 then ρ (t / 32) else 0) < 32
    split
    · exact hρ _
    · decide
  have hREP : Nat.mul (enc 512 ρ 16) c16_REP16 = enc 16 y 512 := by
    rw [c16_REP16_eq, P_mulr]
    have : (fun i => ρ i * enc 16 (fun _ => 1) 16) = (fun i => enc 16 (fun t => if t < 16 then ρ i else 0) 32) := by
      funext i; rw [rep_eq, enc_pad16]
    rw [this, enc_nest512]
  have hc : ∀ t, (if t % 32 < 16 then t % 32 + 1 else 0) < 32 := fun t => by split <;> omega
  have hX : Nat.xor (enc 16 y 512) c16_CPAT1
      = enc 16 (fun t => y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0)) 512 := by
    rw [c16_CPAT1_eq, P_xor 16 h16 _ _ 512 (fun t _ => Nat.lt_of_lt_of_le (hy t) (by decide))
      (fun t _ => Nat.lt_of_lt_of_le (hc t) (by decide))]
  have hxb : ∀ t, y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0) < 32 := fun t =>
    Nat.xor_lt_two_pow (n := 5) (hy t) (hc t)
  have hA : Nat.add (enc 16 (fun t => y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0)) 512) c16_K31
      = enc 16 (fun t => (y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0)) + (if t % 32 < 16 then 31 else 0)) 512 := by
    rw [c16_K31_eq, P_add]
  have hS : Nat.land (Nat.shiftRight (enc 16 (fun t => (y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0))
        + (if t % 32 < 16 then 31 else 0)) 512) 5) c16_ONES16L
      = enc 16 (fun t => ((y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0)) + (if t % 32 < 16 then 31 else 0)) >>> 5
          &&& (if t % 32 < 16 then 1 else 0)) 512 := by
    rw [c16_ONES16L_eq, P_shr_and 16 h16 _ _ 5 512 (by decide)
      (fun t _ => by
        have h1 := hxb t
        have h2 : (if t % 32 < 16 then 31 else 0) ≤ 31 := by split <;> omega
        omega) (fun t _ => by split <;> decide)]
  have hO : Nat.sub c16_ONES16L (enc 16 (fun t => ((y t ^^^ (if t % 32 < 16 then t % 32 + 1 else 0))
        + (if t % 32 < 16 then 31 else 0)) >>> 5 &&& (if t % 32 < 16 then 1 else 0)) 512)
      = enc 16 (fun t => if t % 32 < 16 then (if ρ (t / 32) = t % 32 + 1 then 1 else 0) else 0) 512 := by
    rw [c16_ONES16L_eq, P_sub 16 _ _ 512 (fun t _ => Nat.and_le_right)]
    apply enc_congr; intro t _
    by_cases h : t % 32 < 16
    · simp only [h, ↓reduceIte, y]
      exact zt5 _ (hρ _) _ h
    · simp only [h, ↓reduceIte, Nat.and_zero, Nat.sub_zero]
  unfold oh16
  rw [hREP, hX, hA, hS, hO]
  have hN := (enc_nest512 (fun i t => if t < 16 then (if ρ i = t + 1 then 1 else 0) else 0)).symm
  refine Eq.trans ?_ (hN.trans ?_)
  · rfl
  · apply enc_congr; intro i _
    rw [enc_pad16]

theorem c16_MG_lt : c16_MG < 2 ^ 226 := by decide +kernel

theorem eV_eq (ρ : Nat → Nat) (hρ : ∀ i, ρ i < 32) : eV (enc 512 ρ 16) = enc 512 (fun i => epow (ρ i)) 16 := by
  unfold eV
  rw [oh16_eq ρ hρ, P_mulr, c16_L016_eq]
  have hu : ∀ i, enc 16 (fun k => if ρ i = k + 1 then 1 else 0) 16 < 2 ^ 256 := fun i =>
    enc_lt 16 _ 16 (fun k _ => by split <;> decide)
  rw [P_shr_and 512 (by decide) _ _ 225 16 (by decide)
    (fun i _ => by
      have h1 := hu i
      have h2 := c16_MG_lt
      calc _ < 2 ^ 256 * 2 ^ 226 := Nat.mul_lt_mul'' h1 h2
        _ ≤ 2 ^ 512 := by rw [← Nat.pow_add]; exact Nat.pow_le_pow_right (by decide) (by decide))
    (fun _ _ => by decide)]
  apply enc_congr; intro i _
  exact epow_lane _ (hρ i)


/-! ### The weight check: all labels valid and distinct -/

def valid (r : Nat) : Prop := 1 ≤ r ∧ r ≤ 16

def nInv (ρ : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => nInv ρ n + (if 1 ≤ ρ n ∧ ρ n ≤ 16 then 0 else 1)

theorem epow_v (r : Nat) (h : 1 ≤ r ∧ r ≤ 16) : epow r = 2 ^ (r - 1) := if_pos h
theorem epow_nv (r : Nat) (h : ¬ (1 ≤ r ∧ r ≤ 16)) : epow r = 0 := if_neg h

theorem epow_sum_pc (ρ : Nat → Nat) : ∀ n, pc (sumL (fun c => epow (ρ c)) n) + nInv ρ n ≤ n
  | 0 => by simp [sumL, nInv, pc_zero]
  | n + 1 => by
    have ih := epow_sum_pc ρ n
    simp only [sumL, nInv]
    by_cases hv : 1 ≤ ρ n ∧ ρ n ≤ 16
    · rw [epow_v _ hv, if_pos hv, Nat.add_comm (sumL _ n)]
      cases hb : (sumL (fun c => epow (ρ c)) n).testBit (ρ n - 1)
      · rw [pc_clear _ _ hb]; omega
      · have := pc_set _ _ hb; omega
    · rw [epow_nv _ hv, if_neg hv, Nat.add_zero]; omega

theorem sumL_epow_lt (ρ : Nat → Nat) : ∀ n, sumL (fun c => epow (ρ c)) n ≤ n * 2 ^ 15 := by
  intro n
  apply sumL_le
  intro i _
  unfold epow
  split
  · rename_i h; exact Nat.pow_le_pow_right (by decide) (by omega)
  · exact Nat.zero_le _

theorem chkE_spec (ρ : Nat → Nat)
    (h : Nat.xor (Nat.mod (enc 512 (fun i => epow (ρ i)) 16) c16_M512) 65535 = 0) :
    (∀ i, i < 16 → 1 ≤ ρ i ∧ ρ i ≤ 16) ∧ (∀ a b, a < 16 → b < 16 → ρ a = ρ b → a = b) ∧
      sumL (fun c => 2 ^ (ρ c - 1)) 16 = 2 ^ 16 - 1 := by
  have h1 := xor_zero_eq h
  rw [c16_M512_eq] at h1
  change enc 512 (fun i => epow (ρ i)) 16 % (2 ^ 512 - 1) = 65535 at h1
  rw [enc_mod_m1, Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt (sumL_epow_lt ρ 16) (by decide +kernel))] at h1
  have hpc := epow_sum_pc ρ 16
  rw [h1, show (65535 : Nat) = 2 ^ 16 - 1 from rfl, pc_full16] at hpc
  have hall : ∀ n, n ≤ 16 → nInv ρ n = 0 → ∀ i, i < n → 1 ≤ ρ i ∧ ρ i ≤ 16 := by
    intro n
    induction n with
    | zero => intro _ _ i hi; omega
    | succ n ih =>
      intro hn h0 i hi
      simp only [nInv] at h0
      have h0' : nInv ρ n = 0 := by omega
      rcases Nat.lt_or_ge i n with hi' | hi'
      · exact ih (by omega) h0' i hi'
      · rw [show i = n by omega]
        by_cases hv : 1 ≤ ρ n ∧ ρ n ≤ 16
        · exact hv
        · rw [if_neg hv] at h0; omega
  have hv := hall 16 (Nat.le_refl _) (by omega)
  have hsum : sumL (fun c => epow (ρ c)) 16 = sumL (fun c => 2 ^ (ρ c - 1)) 16 := by
    have : ∀ n, n ≤ 16 → sumL (fun c => epow (ρ c)) n = sumL (fun c => 2 ^ (ρ c - 1)) n := by
      intro n
      induction n with
      | zero => intro _; rfl
      | succ n ih =>
        intro hn
        simp only [sumL]
        rw [ih (by omega), epow_v _ (hv n (by omega))]
    exact this 16 (Nat.le_refl _)
  have hrel : relab (fun c => ρ c - 1) (2 ^ 16 - 1) 16 = sumL (fun c => 2 ^ (ρ c - 1)) 16 :=
    relab_full _ _ 16 (fun c hc => by rw [Nat.testBit_two_pow_sub_one]; simp [hc])
  have hpcr : pc (relab (fun c => ρ c - 1) (2 ^ 16 - 1) 16) = 16 := by
    rw [hrel, ← hsum, h1, show (65535 : Nat) = 2 ^ 16 - 1 from rfl, pc_full16]
  have hinj := relab_inj_of_pc (fun c => ρ c - 1) (2 ^ 16 - 1) 16
    (fun c hc => by rw [Nat.testBit_two_pow_sub_one]; simp [hc]) hpcr
  refine ⟨hv, fun a b ha hb hab => hinj a b ha hb (by simp only [hab]), ?_⟩
  rw [← hsum, h1]

end P8
end Submission

end


/-! # Proof part: Stage3 -/

section
set_option exponentiation.threshold 100000

namespace Submission
namespace P8

/-! ## Compressing the weights to a reversed `16`-bit row (`eRev`) -/

theorem tsum_mul_ones_list (xs : List (Nat × Nat)) : ∀ S : List Nat,
    tsum xs * tsum (S.map (fun s => (1, s))) = tsum (S.flatMap (fun s => xs.map (fun t => (t.1, t.2 + s))))
  | [] => by simp [tsum]
  | s :: S => by
    simp only [List.map_cons, List.flatMap_cons, tsum, tsum_append, tsum_shift, Nat.one_mul]
    rw [Nat.mul_add, tsum_mul_ones_list xs S]

def mrS : List Nat := (List.range 16).map (fun t => 7920 - 528 * t)

theorem c16_MR_eq : c16_MR = tsum (mrS.map (fun s => (1, s))) := by decide +kernel

def erTerms (ε : Nat → Nat) : List (Nat × Nat) :=
  mrS.flatMap (fun s => ((List.range 16).map (fun c => (ε c, 512 * c))).map (fun t => (t.1, t.2 + s)))

theorem erTerms_mem (ε : Nat → Nat) (t : Nat × Nat) : t ∈ erTerms ε →
    ∃ c u, c < 16 ∧ u < 16 ∧ t.1 = ε c ∧ t.2 = 512 * c + (7920 - 528 * u) := by
  intro h
  simp only [erTerms, mrS, List.mem_flatMap, List.mem_map, List.mem_range] at h
  obtain ⟨s, ⟨u, hu, rfl⟩, ⟨v, q⟩, ⟨c, hc, hvq⟩, rfl⟩ := h
  simp only [Prod.mk.injEq] at hvq
  obtain ⟨rfl, rfl⟩ := hvq
  exact ⟨c, u, hc, hu, rfl, rfl⟩

theorem erTerms_sep (ε : Nat → Nat) : sep 16 (erTerms ε) := by
  have key : ∀ ts : List (Nat × Nat), sep 16 (ts.map (fun t => (0, t.2))) → sep 16 ts := by
    intro ts
    induction ts with
    | nil => intro _; trivial
    | cons t ts ih =>
      intro ⟨h1, h2⟩
      exact ⟨fun u hu => h1 (0, u.2) (List.mem_map.mpr ⟨u, hu, rfl⟩), ih h2⟩
  apply key
  have e : (erTerms ε).map (fun t => (0, t.2)) = (erTerms (fun _ => 0)).map (fun t => (0, t.2)) := by
    simp [erTerms, List.map_flatMap, Function.comp_def]
  rw [e]
  exact sep_of_sepB 16 _ (by decide +kernel)

theorem eRev_eq (ε : Nat → Nat) (hε : ∀ c, c < 16 → ε c < 2 ^ 16) :
    eRev (enc 512 ε 16) = enc 16 (fun t => ε (15 - t)) 16 := by
  unfold eRev
  have hP : Nat.mul (enc 512 ε 16) c16_MR = tsum (erTerms ε) := by
    rw [c16_MR_eq, enc_tsum]
    exact tsum_mul_ones_list _ mrS
  rw [hP]
  have hbd : ∀ t ∈ erTerms ε, t.1 < 2 ^ 16 := by
    intro t ht
    obtain ⟨c, u, hc, _, h1, _⟩ := erTerms_mem ε t ht
    rw [h1]; exact hε c hc
  apply Nat.eq_of_testBit_eq; intro p
  rw [show Nat.land (Nat.shiftRight (tsum (erTerms ε)) 7680) c16_M256
      = (tsum (erTerms ε) >>> 7680) &&& c16_M256 from rfl, Nat.testBit_and, Nat.testBit_shiftRight,
    tsum_tb 16 _ hbd (erTerms_sep ε),
    show c16_M256 = 2 ^ 256 - 1 by decide +kernel, Nat.testBit_two_pow_sub_one,
    enc_tb 16 (by decide) _ p 16 (fun t _ => hε _ (by omega))]
  by_cases hp : p < 256
  · simp only [hp, decide_true, Bool.and_true, show p / 16 < 16 by omega, Bool.true_and]
    apply Bool.eq_iff_iff.mpr
    rw [tbit_iff]
    have hpd := Nat.div_add_mod p 16
    have hpm := Nat.mod_lt p (show 0 < 16 by decide)
    constructor
    · rintro ⟨t, ht, h1, h2, h3⟩
      obtain ⟨c, u, hc, hu, e1, e2⟩ := erTerms_mem ε t ht
      have : c = u := by omega
      rw [e1, e2] at h3
      have hc' : c = 15 - p / 16 := by omega
      have ex : 7680 + p - (512 * c + (7920 - 528 * u)) = p % 16 := by omega
      rw [ex, hc'] at h3; exact h3
    · intro h
      refine ⟨(ε (15 - p / 16), 512 * (15 - p / 16) + (7920 - 528 * (15 - p / 16))), ?_, by omega, by omega, ?_⟩
      · simp only [erTerms, mrS, List.mem_flatMap, List.mem_map, List.mem_range]
        exact ⟨7920 - 528 * (15 - p / 16), ⟨15 - p / 16, by omega, rfl⟩,
          (ε (15 - p / 16), 512 * (15 - p / 16)), ⟨15 - p / 16, by omega, rfl⟩, rfl⟩
      · have ex : 7680 + p - (512 * (15 - p / 16) + (7920 - 528 * (15 - p / 16))) = p % 16 := by omega
        show (ε (15 - p / 16)).testBit (7680 + p - (512 * (15 - p / 16) + (7920 - 528 * (15 - p / 16)))) = true
        rw [ex]; exact h
  · simp [hp, show ¬ p / 16 < 16 by omega]


/-! ## Products of encodings (convolution) -/

def conv (f g : Nat → Nat) : Nat → Nat → Nat
  | 0, _ => 0
  | L + 1, q => conv f g L q + (if L ≤ q then f L * g (q - L) else 0)

theorem conv_zero_high (f g : Nat → Nat) (M : Nat) (hg : ∀ m, M ≤ m → g m = 0) :
    ∀ L q, L + M ≤ q + 1 → conv f g L q = 0
  | 0, _, _ => rfl
  | L + 1, q, h => by
    simp only [conv]
    rw [conv_zero_high f g M hg L q (by omega), if_pos (by omega), hg _ (by omega), Nat.mul_zero]

theorem enc_mul_conv (W : Nat) (f g : Nat → Nat) (M : Nat) (hg : ∀ m, M ≤ m → g m = 0) :
    ∀ L, enc W f L * enc W g M = enc W (conv f g L) (L + M)
  | 0 => by
    rw [Nat.zero_add, show enc W f 0 = 0 from rfl, Nat.zero_mul]
    exact (enc_zero W M (fun q _ => rfl)).symm
  | L + 1 => by
    rw [enc_succ, Nat.add_mul, enc_mul_conv W f g M hg L, Nat.mul_assoc, Nat.mul_comm (2 ^ (W * L)),
      ← Nat.shiftLeft_eq, enc_shl, Nat.mul_comm (f L), enc_mulc]
    rw [enc_pad' W (conv f g L) (L + M) (L + 1 + M) (by omega)
        (fun q h1 _ => conv_zero_high f g M hg L q (by omega)),
      enc_pad' W (fun q => (if L ≤ q then g (q - L) else 0) * f L) (M + L) (L + 1 + M) (by omega)
        (fun q h1 _ => by rw [if_pos (by omega), hg _ (by omega), Nat.zero_mul]),
      ← enc_add]
    apply enc_congr; intro q _
    simp only [conv]
    split <;> simp [Nat.mul_comm]

/-- Indicator sums pick values. -/
def isum (h : Nat → Nat) (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => isum h f L + f L * h L

theorem conv15 (f h : Nat → Nat) : ∀ L, L ≤ 16 →
    conv f (fun t => if t < 16 then h (15 - t) else 0) L 15 = isum h f L
  | 0, _ => rfl
  | L + 1, hL => by
    simp only [conv, isum]
    rw [conv15 f h L (by omega), if_pos (by omega), if_pos (by omega), show 15 - (15 - L) = L by omega]

theorem isum_ind (h : Nat → Nat) (x : Nat) : ∀ L, isum h (fun c => if x = c then 1 else 0) L = if x < L then h x else 0
  | 0 => by simp [isum]
  | L + 1 => by
    simp only [isum]
    rw [isum_ind h x L]
    by_cases h1 : x = L
    · subst h1; simp
    · by_cases h2 : x < L
      · simp [h1, h2, show x < L + 1 by omega]
      · simp [h1, h2, show ¬ x < L + 1 by omega]

theorem isum_add (h f g : Nat → Nat) : ∀ L, isum h (fun c => f c + g c) L = isum h f L + isum h g L
  | 0 => rfl
  | L + 1 => by simp only [isum]; rw [isum_add h f g L, Nat.add_mul]; omega


theorem pow_and_pow (p q : Nat) (h : p ≠ q) : 2 ^ p &&& 2 ^ q = 0 := by
  apply Nat.eq_of_testBit_eq; intro j
  rw [Nat.testBit_and, Nat.testBit_two_pow, Nat.testBit_two_pow, Nat.zero_testBit]
  by_cases h1 : p = j
  · subst h1; simp [Ne.symm h]
  · simp [h1]

/-- Weights as powers of an injective label. -/
structure Wts (ε : Nat → Nat) (lam : Nat → Nat) : Prop where
  pow : ∀ c, c < 16 → ε c = 2 ^ lam c
  lt : ∀ c, c < 16 → lam c < 16
  inj : ∀ a b, a < 16 → b < 16 → lam a = lam b → a = b

def εp (ε : Nat → Nat) (j : Nat) : Nat := if j < 16 then ε j else 0

theorem εp_and (ε lam : Nat → Nat) (hw : Wts ε lam) (x y : Nat) (hxy : x ≠ y) : εp ε x &&& εp ε y = 0 := by
  unfold εp
  by_cases hx : x < 16
  · by_cases hy : y < 16
    · rw [if_pos hx, if_pos hy, hw.pow x hx, hw.pow y hy]
      exact pow_and_pow _ _ (fun h => hxy (hw.inj x y hx hy h))
    · rw [if_neg hy, Nat.and_zero]
  · rw [if_neg hx, Nat.zero_and]

theorem εp_lt (ε lam : Nat → Nat) (hw : Wts ε lam) (x : Nat) : εp ε x < 2 ^ 16 := by
  unfold εp
  split
  · rename_i h; rw [hw.pow x h]; exact Nat.pow_lt_pow_right (by decide) (hw.lt x h)
  · exact Nat.two_pow_pos _

theorem dist3 (ε lam : Nat → Nat) (hw : Wts ε lam) (x y z : Nat) (h1 : x ≠ y) (h2 : x ≠ z) (h3 : y ≠ z) :
    εp ε x + εp ε y + εp ε z < 2 ^ 16 := by
  rw [add_eq_or_of_and _ _ (εp_and ε lam hw x y h1)]
  rw [add_eq_or_of_and _ _ (by rw [Nat.and_or_distrib_right, εp_and ε lam hw x z h2, εp_and ε lam hw y z h3]; rfl)]
  exact Nat.or_lt_two_pow (Nat.or_lt_two_pow (εp_lt ε lam hw x) (εp_lt ε lam hw y)) (εp_lt ε lam hw z)

theorem conv_add (f1 f2 g : Nat → Nat) : ∀ L q, conv (fun c => f1 c + f2 c) g L q = conv f1 g L q + conv f2 g L q
  | 0, _ => rfl
  | L + 1, q => by
    simp only [conv]; rw [conv_add f1 f2 g L q]
    split <;> simp [Nat.add_mul] <;> omega

theorem conv_ind (x : Nat) (g : Nat → Nat) : ∀ L q,
    conv (fun c => if x = c then 1 else 0) g L q = if x < L ∧ x ≤ q then g (q - x) else 0
  | 0, _ => by simp [conv]
  | L + 1, q => by
    simp only [conv]; rw [conv_ind x g L q]
    by_cases hC : x = L
    · subst hC
      have hA : ¬ (x < x ∧ x ≤ q) := by omega
      rw [if_neg hA, if_pos (rfl : x = x), Nat.one_mul, Nat.zero_add]
      by_cases hB : x ≤ q
      · rw [if_pos hB, if_pos (show x < x + 1 ∧ x ≤ q from ⟨by omega, hB⟩)]
      · rw [if_neg hB, if_neg (show ¬ (x < x + 1 ∧ x ≤ q) by omega)]
    · rw [if_neg hC, Nat.zero_mul]
      have e : (if L ≤ q then (0 : Nat) else 0) = 0 := by split <;> rfl
      rw [e, Nat.add_zero]
      by_cases hA : x < L ∧ x ≤ q
      · rw [if_pos hA, if_pos (show x < L + 1 ∧ x ≤ q from ⟨by omega, hA.2⟩)]
      · rw [if_neg hA, if_neg (show ¬ (x < L + 1 ∧ x ≤ q) by omega)]

/-- One term of the lane product is bounded by the weight at a shifted, injectively chosen index. -/
def tidx (x q : Nat) : Nat := if x ≤ q ∧ q - x < 16 then 15 + x - q else 100 + x

theorem term_le (ε : Nat → Nat) (x q : Nat) :
    (if x < 16 ∧ x ≤ q then (fun t => if t < 16 then ε (15 - t) else 0) (q - x) else 0) ≤ εp ε (tidx x q) := by
  by_cases h : x < 16 ∧ x ≤ q
  · rw [if_pos h]
    show (if q - x < 16 then ε (15 - (q - x)) else 0) ≤ _
    by_cases h' : q - x < 16
    · have ht : tidx x q = 15 + x - q := if_pos ⟨h.2, h'⟩
      rw [if_pos h', ht]
      unfold εp
      rw [if_pos (show 15 + x - q < 16 by omega), show 15 - (q - x) = 15 + x - q by omega]
      exact Nat.le_refl _
    · rw [if_neg h']; exact Nat.zero_le _
  · rw [if_neg h]; exact Nat.zero_le _

theorem tidx_ne (x y q : Nat) (h : x ≠ y) : tidx x q ≠ tidx y q := by
  unfold tidx; split <;> split <;> omega

theorem oV_eq (a b ε lam : Nat → Nat) (hw : Wts ε lam) (ha : ∀ i, i < 16 → a i < 16) (hb : ∀ i, i < 16 → b i < 16)
    (hai : ∀ i, i < 16 → a i ≠ i) (hbi : ∀ i, i < 16 → b i ≠ i) (hab : ∀ i, i < 16 → a i ≠ b i) :
    oV (enc 512 (fun i => enc 16 (rowInd a b i) 16) 16) (enc 16 (fun t => ε (15 - t)) 16)
      = enc 512 (fun i => ε (a i) + ε (b i) + ε i) 16 := by
  let g : Nat → Nat := fun t => if t < 16 then ε (15 - t) else 0
  have hEr : enc 16 (fun t => ε (15 - t)) 16 = enc 16 g 16 := enc_congr 16 16 (fun t ht => by simp [g, ht])
  have hglt : ∀ t, g t < 2 ^ 16 := fun t => by
    show (if t < 16 then ε (15 - t) else 0) < 2 ^ 16
    split
    · have := εp_lt ε lam hw (15 - t); unfold εp at this; rwa [if_pos (by omega)] at this
    · exact Nat.two_pow_pos _
  have hrow : ∀ i t, rowInd a b i t < 2 ^ 16 := fun i t => by
    unfold rowInd; split <;> split <;> split <;> decide
  have hEr_lt : enc 16 g 16 < 2 ^ 256 := enc_lt 16 g 16 (fun t _ => hglt t)
  have hrow_lt : ∀ i, enc 16 (rowInd a b i) 16 < 2 ^ 256 := fun i => enc_lt 16 _ 16 (fun t _ => hrow i t)
  -- lane-wise product and extraction
  unfold oV
  rw [hEr, P_mulr, c16_L016_eq, P_shr_and 512 (by decide) _ _ 240 16 (by decide)
    (fun i _ => by
      calc _ < 2 ^ 256 * 2 ^ 256 := Nat.mul_lt_mul'' (hrow_lt i) hEr_lt
        _ = 2 ^ 512 := by rw [← Nat.pow_add])
    (fun _ _ => by decide)]
  apply enc_congr; intro i hi
  have hg0 : ∀ m, 16 ≤ m → g m = 0 := fun m hm => by simp [g, show ¬ m < 16 by omega]
  rw [enc_mul_conv 16 _ g 16 hg0 16]
  -- all product sub-lanes are small
  have hconv : ∀ q, q < 16 + 16 → conv (rowInd a b i) g 16 q < 2 ^ 16 := by
    intro q _
    have e : conv (rowInd a b i) g 16 q
        = conv (fun c => if a i = c then 1 else 0) g 16 q + conv (fun c => if b i = c then 1 else 0) g 16 q
          + conv (fun c => if i = c then 1 else 0) g 16 q := by
      unfold rowInd; rw [conv_add, conv_add]
    rw [e, conv_ind, conv_ind, conv_ind]
    have t1 := term_le ε (a i) q
    have t2 := term_le ε (b i) q
    have t3 := term_le ε i q
    have hd := dist3 ε lam hw (tidx (a i) q) (tidx (b i) q) (tidx i q)
      (tidx_ne _ _ q (hab i hi)) (tidx_ne _ _ q (hai i hi)) (tidx_ne _ _ q (hbi i hi))
    exact Nat.lt_of_le_of_lt (Nat.add_le_add (Nat.add_le_add t1 t2) t3) hd
  rw [show (0xffff : Nat) = 2 ^ 16 - 1 from rfl, show (240 : Nat) = 16 * 15 from rfl,
    enc_lane_and 16 _ (16 + 16) 15 (by decide) hconv, conv15 _ ε 16 (Nat.le_refl _)]
  unfold rowInd
  rw [isum_add, isum_add, isum_ind, isum_ind, isum_ind, if_pos (ha i hi), if_pos (hb i hi), if_pos hi]

end P8
end Submission

end


/-! # Proof part: Stage4 -/

section
set_option exponentiation.threshold 100000

namespace Submission
namespace P8

/-! ## Sorting each row's three weights (`lo`, `mid`, `hi`) -/

theorem lowbit (p k : Nat) : (2 ^ (p + 1) * k + 2 ^ p) &&& (2 ^ (p + 1) * k + 2 ^ p - 1) = 2 ^ (p + 1) * k := by
  have h1 : 2 ^ p < 2 ^ (p + 1) := Nat.pow_lt_pow_right (by decide) (by omega)
  have h2 : 2 ^ p - 1 < 2 ^ (p + 1) := by omega
  have e : 2 ^ (p + 1) * k + 2 ^ p - 1 = 2 ^ (p + 1) * k + (2 ^ p - 1) := by
    have := Nat.one_le_two_pow (n := p); omega
  rw [e]
  apply Nat.eq_of_testBit_eq; intro j
  rw [Nat.testBit_and, Nat.testBit_two_pow_mul_add k h1, Nat.testBit_two_pow_mul_add k h2]
  have e0 : 2 ^ (p + 1) * k = 2 ^ (p + 1) * k + 0 := rfl
  rw [e0, Nat.testBit_two_pow_mul_add k (Nat.two_pow_pos _)]
  by_cases hj : j < p + 1
  · simp only [hj, ↓reduceIte, Nat.zero_testBit, Nat.testBit_two_pow, Nat.testBit_two_pow_sub_one]
    by_cases hp : p = j
    · subst hp; simp
    · simp [hp]
  · simp [hj]

/-- `2^q + 2^r` with `q < r` is a multiple of `2^(q+1)`. -/
theorem dvd_two_pows (p q r : Nat) (hpq : p < q) (hqr : q < r) :
    ∃ k, 2 ^ q + 2 ^ r = 2 ^ (p + 1) * k := by
  refine ⟨2 ^ (q - (p + 1)) + 2 ^ (r - (p + 1)), ?_⟩
  rw [Nat.mul_add, ← Nat.pow_add, ← Nat.pow_add, show p + 1 + (q - (p + 1)) = q by omega,
    show p + 1 + (r - (p + 1)) = r by omega]

theorem lohi3 (p q r : Nat) (hpq : p < q) (hqr : q < r) :
    let O := 2 ^ p + 2 ^ q + 2 ^ r
    O &&& (O - 1) = 2 ^ q + 2 ^ r ∧ O - (O &&& (O - 1)) = 2 ^ p ∧
      (2 ^ q + 2 ^ r) &&& (2 ^ q + 2 ^ r - 1) = 2 ^ r ∧ (2 ^ q + 2 ^ r) - 2 ^ r = 2 ^ q := by
  intro O
  obtain ⟨k, hk⟩ := dvd_two_pows p q r hpq hqr
  have hO : O = 2 ^ (p + 1) * k + 2 ^ p := by
    show 2 ^ p + 2 ^ q + 2 ^ r = _; rw [Nat.add_assoc, hk, Nat.add_comm]
  have hA : O &&& (O - 1) = 2 ^ q + 2 ^ r := by rw [hO, lowbit, hk]
  have hr : 2 ^ r = 2 ^ (q + 1) * 2 ^ (r - (q + 1)) := by rw [← Nat.pow_add]; congr 1; omega
  have hB : (2 ^ q + 2 ^ r) &&& (2 ^ q + 2 ^ r - 1) = 2 ^ r := by
    rw [hr, Nat.add_comm, lowbit]
  refine ⟨hA, ?_, hB, Nat.add_sub_cancel _ _⟩
  rw [hA]; show 2 ^ p + 2 ^ q + 2 ^ r - (2 ^ q + 2 ^ r) = 2 ^ p
  rw [Nat.add_assoc, Nat.add_sub_cancel]


def mn3 (x y z : Nat) : Nat := min x (min y z)
def mx3 (x y z : Nat) : Nat := max x (max y z)
def md3 (x y z : Nat) : Nat := x + y + z - mn3 x y z - mx3 x y z

theorem sort3 (x y z : Nat) (h1 : x ≠ y) (h2 : x ≠ z) (h3 : y ≠ z) :
    mn3 x y z < md3 x y z ∧ md3 x y z < mx3 x y z ∧ [x, y, z].Perm [mn3 x y z, md3 x y z, mx3 x y z] := by
  unfold md3 mn3 mx3
  rcases Nat.lt_or_gt_of_ne h1 with a | a <;> rcases Nat.lt_or_gt_of_ne h2 with b | b <;>
    rcases Nat.lt_or_gt_of_ne h3 with c | c
  · -- x < y < z
    rw [show min x (min y z) = x by omega, show max x (max y z) = z by omega, show x + y + z - x - z = y by omega]
    exact ⟨a, c, List.Perm.refl _⟩
  · -- x < z < y
    rw [show min x (min y z) = x by omega, show max x (max y z) = y by omega, show x + y + z - x - y = z by omega]
    exact ⟨b, c, List.Perm.cons x (List.Perm.swap z y [])⟩
  · exfalso; omega
  · -- z < x < y
    rw [show min x (min y z) = z by omega, show max x (max y z) = y by omega, show x + y + z - z - y = x by omega]
    exact ⟨b, a, (List.Perm.cons x (List.Perm.swap z y [])).trans (List.Perm.swap z x [y])⟩
  · -- y < x < z
    rw [show min x (min y z) = y by omega, show max x (max y z) = z by omega, show x + y + z - y - z = x by omega]
    exact ⟨a, b, List.Perm.swap y x [z]⟩
  · exfalso; omega
  · -- y < z < x
    rw [show min x (min y z) = y by omega, show max x (max y z) = x by omega, show x + y + z - y - x = z by omega]
    exact ⟨c, b, (List.Perm.swap y x [z]).trans (List.Perm.cons y (List.Perm.swap z x []))⟩
  · -- z < y < x
    rw [show min x (min y z) = z by omega, show max x (max y z) = x by omega, show x + y + z - z - x = y by omega]
    exact ⟨c, a, ((List.Perm.swap y x [z]).trans (List.Perm.cons y (List.Perm.swap z x []))).trans
      (List.Perm.swap z y [x])⟩


theorem pow_le15 (p : Nat) (h : p < 16) : 2 ^ p ≤ 2 ^ 15 := Nat.pow_le_pow_right (by decide) (by omega)

theorem lohi_vec (L1 L2 L3 : Nat → Nat)
    (hd : ∀ i, i < 16 → L1 i ≠ L2 i ∧ L1 i ≠ L3 i ∧ L2 i ≠ L3 i ∧ L1 i < 16 ∧ L2 i < 16 ∧ L3 i < 16) :
    r1V (enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16)
        = enc 512 (fun i => 2 ^ md3 (L1 i) (L2 i) (L3 i) + 2 ^ mx3 (L1 i) (L2 i) (L3 i)) 16 ∧
      loV (enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16) = enc 512 (fun i => 2 ^ mn3 (L1 i) (L2 i) (L3 i)) 16 ∧
      hiV (enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16) = enc 512 (fun i => 2 ^ mx3 (L1 i) (L2 i) (L3 i)) 16 ∧
      midV (enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16) = enc 512 (fun i => 2 ^ md3 (L1 i) (L2 i) (L3 i)) 16 := by
  -- abbreviations as explicit functions
  generalize hmn : (fun i => mn3 (L1 i) (L2 i) (L3 i)) = mn
  generalize hmd : (fun i => md3 (L1 i) (L2 i) (L3 i)) = md
  generalize hmx : (fun i => mx3 (L1 i) (L2 i) (L3 i)) = mx
  have emn : ∀ i, mn3 (L1 i) (L2 i) (L3 i) = mn i := fun i => by rw [← hmn]
  have emd : ∀ i, md3 (L1 i) (L2 i) (L3 i) = md i := fun i => by rw [← hmd]
  have emx : ∀ i, mx3 (L1 i) (L2 i) (L3 i) = mx i := fun i => by rw [← hmx]
  simp only [emn, emd, emx]
  have hs : ∀ i, i < 16 → mn i < md i ∧ md i < mx i ∧ mx i < 16 ∧
      2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i = 2 ^ mn i + 2 ^ md i + 2 ^ mx i := by
    intro i hi
    obtain ⟨h1, h2, h3, h4, h5, h6⟩ := hd i hi
    obtain ⟨a, b, c⟩ := sort3 _ _ _ h1 h2 h3
    simp only [emn, emd, emx] at a b c
    refine ⟨a, b, ?_, ?_⟩
    · rw [← emx]; show max (L1 i) (max (L2 i) (L3 i)) < 16; omega
    · have := (c.map (fun x => 2 ^ x)).sum_nat
      simp only [List.map_cons, List.map_nil, List.sum_cons, List.sum_nil, Nat.add_zero, ← Nat.add_assoc] at this
      exact this
  have hO : enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16 = enc 512 (fun i => 2 ^ mn i + 2 ^ md i + 2 ^ mx i) 16 :=
    enc_congr 512 16 (fun i hi => (hs i hi).2.2.2)
  rw [hO]
  have b3 : ∀ i, i < 16 → 2 ^ mn i + 2 ^ md i + 2 ^ mx i < 2 ^ 512 := fun i hi => by
    obtain ⟨a, b, c, _⟩ := hs i hi
    have e1 := pow_le15 _ (show mn i < 16 by omega); have e2 := pow_le15 _ (show md i < 16 by omega)
    have e3 := pow_le15 _ c
    have : (2 : Nat) ^ 15 * 3 < 2 ^ 512 := by decide +kernel
    omega
  have b2 : ∀ i, i < 16 → 2 ^ md i + 2 ^ mx i < 2 ^ 512 := fun i hi =>
    Nat.lt_of_le_of_lt (by rw [Nat.add_assoc]; exact Nat.le_add_left _ _) (b3 i hi)
  have p1 : ∀ i, 1 ≤ 2 ^ mn i := fun i => Nat.one_le_two_pow
  have p2 : ∀ i, 1 ≤ 2 ^ md i := fun i => Nat.one_le_two_pow
  have hr1 : r1V (enc 512 (fun i => 2 ^ mn i + 2 ^ md i + 2 ^ mx i) 16) = enc 512 (fun i => 2 ^ md i + 2 ^ mx i) 16 := by
    unfold r1V
    rw [c16_ONESL_eq, P_sub 512 _ _ 16 (fun i _ => Nat.le_trans (p1 i) (by rw [Nat.add_assoc]; exact Nat.le_add_right _ _)),
      P_and 512 (by decide) _ _ 16 b3 (fun i hi => Nat.lt_of_le_of_lt (Nat.sub_le _ _) (b3 i hi))]
    apply enc_congr; intro i hi
    obtain ⟨a, b, _, _⟩ := hs i hi
    exact (lohi3 (mn i) (md i) (mx i) a b).1
  have hhi : Nat.land (r1V (enc 512 (fun i => 2 ^ mn i + 2 ^ md i + 2 ^ mx i) 16))
      (Nat.sub (r1V (enc 512 (fun i => 2 ^ mn i + 2 ^ md i + 2 ^ mx i) 16)) c16_ONESL) = enc 512 (fun i => 2 ^ mx i) 16 := by
    rw [hr1, c16_ONESL_eq, P_sub 512 _ _ 16 (fun i _ => Nat.le_trans (p2 i) (Nat.le_add_right _ _)),
      P_and 512 (by decide) _ _ 16 b2 (fun i hi => Nat.lt_of_le_of_lt (Nat.sub_le _ _) (b2 i hi))]
    apply enc_congr; intro i hi
    obtain ⟨a, b, _, _⟩ := hs i hi
    exact (lohi3 (mn i) (md i) (mx i) a b).2.2.1
  refine ⟨hr1, ?_, hhi, ?_⟩
  · unfold loV
    rw [hr1, P_sub 512 _ _ 16 (fun i _ => by rw [Nat.add_assoc]; exact Nat.le_add_left _ _)]
    apply enc_congr; intro i hi
    show 2 ^ mn i + 2 ^ md i + 2 ^ mx i - (2 ^ md i + 2 ^ mx i) = 2 ^ mn i
    rw [Nat.add_assoc, Nat.add_sub_cancel]
  · unfold midV
    rw [show hiV (enc 512 (fun i => 2 ^ mn i + 2 ^ md i + 2 ^ mx i) 16) = enc 512 (fun i => 2 ^ mx i) 16 from hhi,
      hr1, P_sub 512 _ _ 16 (fun i _ => Nat.le_add_left _ _)]
    apply enc_congr; intro i hi
    show 2 ^ md i + 2 ^ mx i - 2 ^ mx i = 2 ^ md i
    exact Nat.add_sub_cancel _ _

end P8
end Submission

end


/-! # Proof part: Stage5 -/

section
set_option exponentiation.threshold 100000

namespace Submission
namespace P8

/-! ## The row order: one-hot of the step of each row (`ohQ`), permuting lanes (`permV`) -/

def vinv (k : Nat) : Nat := if k < 8 then 2 * k else 2 * (15 - k) + 1

theorem enc_nest32 (g : Nat → Nat → Nat) : ∀ L,
    enc 512 (fun i => enc 32 (g i) 16) L = enc 32 (fun t => g (t / 16) (t % 16)) (16 * L)
  | 0 => by rw [Nat.mul_zero, enc, enc]
  | L + 1 => by
    have h1 := enc_succ 512 (fun i => enc 32 (g i) 16) L
    have h2 := enc_split 32 (fun t => g (t / 16) (t % 16)) (16 * L) 16
    have h3 : 16 * (L + 1) = 16 * L + 16 := by omega
    have h4 : enc 32 (fun m => (fun t => g (t / 16) (t % 16)) (16 * L + m)) 16 = enc 32 (g L) 16 := by
      apply enc_congr; intro t ht
      show g ((16 * L + t) / 16) ((16 * L + t) % 16) = g L t
      have e1 : (16 * L + t) / 16 = L := by omega
      have e2 : (16 * L + t) % 16 = t := by omega
      rw [e1, e2]
    have h5 : 2 ^ (32 * (16 * L)) = 2 ^ (512 * L) := by rw [show 32 * (16 * L) = 512 * L by omega]
    rw [h1, h3, h2, h4, h5, enc_nest32 g L, Nat.mul_comm (2 ^ (512 * L))]

theorem enc_nest32_16 (g : Nat → Nat → Nat) :
    enc 512 (fun i => enc 32 (g i) 16) 16 = enc 32 (fun t => g (t / 16) (t % 16)) 256 := enc_nest32 g 16

theorem c16_REP32_eq : c16_REP32 = enc 32 (fun _ => 1) 16 := by decide +kernel
theorem c16_CPATV_eq : c16_CPATV = enc 32 (fun t => vinv (t % 16) + 1) 256 := by decide +kernel
theorem c16_K31B_eq : c16_K31B = enc 32 (fun _ => 31) 256 := by decide +kernel
theorem c16_ONES32L_eq : c16_ONES32L = enc 32 (fun _ => 1) 256 := by decide +kernel
theorem c16_ONES32C_eq : c16_ONES32C = enc 32 (fun _ => 1) 16 := by decide +kernel

theorem zt5' : ∀ r, r < 32 → ∀ c, c < 32 → 1 - (((r ^^^ c) + 31) >>> 5 &&& 1) = if r = c then 1 else 0 := by
  decide

theorem vinv_lt : ∀ k, k < 16 → vinv k < 16 := by decide

theorem ohQ_eq (ρ : Nat → Nat) (hρ : ∀ i, ρ i < 32) :
    ohQ (enc 512 ρ 16) = enc 512 (fun r => enc 32 (fun k => if ρ r = vinv k + 1 then 1 else 0) 16) 16 := by
  have h32 : (0 : Nat) < 32 := by decide
  let y : Nat → Nat := fun t => ρ (t / 16)
  have hREP : Nat.mul (enc 512 ρ 16) c16_REP32 = enc 32 y 256 := by
    rw [c16_REP32_eq, P_mulr]
    have : (fun i => ρ i * enc 32 (fun _ => 1) 16) = (fun i => enc 32 (fun _ => ρ i) 16) := by
      funext i; rw [rep_eq]
    rw [this, enc_nest32_16]
  have hc : ∀ t, vinv (t % 16) + 1 < 32 := fun t => by have := vinv_lt (t % 16) (Nat.mod_lt _ (by decide)); omega
  have hX : Nat.xor (enc 32 y 256) c16_CPATV = enc 32 (fun t => y t ^^^ (vinv (t % 16) + 1)) 256 := by
    rw [c16_CPATV_eq, P_xor 32 h32 _ _ 256 (fun t _ => Nat.lt_of_lt_of_le (hρ _) (by decide))
      (fun t _ => Nat.lt_of_lt_of_le (hc t) (by decide))]
  have hxb : ∀ t, y t ^^^ (vinv (t % 16) + 1) < 32 := fun t => Nat.xor_lt_two_pow (n := 5) (hρ _) (hc t)
  have hA : Nat.add (enc 32 (fun t => y t ^^^ (vinv (t % 16) + 1)) 256) c16_K31B
      = enc 32 (fun t => (y t ^^^ (vinv (t % 16) + 1)) + 31) 256 := by rw [c16_K31B_eq, P_add]
  have hS : Nat.land (Nat.shiftRight (enc 32 (fun t => (y t ^^^ (vinv (t % 16) + 1)) + 31) 256) 5) c16_ONES32L
      = enc 32 (fun t => ((y t ^^^ (vinv (t % 16) + 1)) + 31) >>> 5 &&& 1) 256 := by
    rw [c16_ONES32L_eq, P_shr_and 32 h32 _ _ 5 256 (by decide)
      (fun t _ => by have := hxb t; omega) (fun _ _ => by decide)]
  have hO : Nat.sub c16_ONES32L (enc 32 (fun t => ((y t ^^^ (vinv (t % 16) + 1)) + 31) >>> 5 &&& 1) 256)
      = enc 32 (fun t => if ρ (t / 16) = vinv (t % 16) + 1 then 1 else 0) 256 := by
    rw [c16_ONES32L_eq, P_sub 32 _ _ 256 (fun t _ => Nat.and_le_right)]
    apply enc_congr; intro t _
    exact zt5' _ (hρ _) _ (hc t)
  unfold ohQ
  rw [hREP, hX, hA, hS, hO]
  exact (enc_nest32_16 (fun r k => if ρ r = vinv k + 1 then 1 else 0)).symm


theorem sumL_enc (W L : Nat) (h : Nat → Nat → Nat) : ∀ n,
    sumL (fun r => enc W (h r) L) n = enc W (fun k => sumL (fun r => h r k) n) L
  | 0 => (enc_zero W L (fun _ _ => rfl)).symm
  | n + 1 => by simp only [sumL]; rw [sumL_enc W L h n, ← enc_add]

theorem sumL_comm (g : Nat → Nat → Nat) : ∀ n m,
    sumL (fun k => sumL (fun r => g r k) n) m = sumL (fun r => sumL (fun k => g r k) m) n
  | n, 0 => by
    show 0 = sumL (fun r => 0) n
    induction n with
    | zero => rfl
    | succ n ih => simp only [sumL]; rw [← ih]
  | n, m + 1 => by
    simp only [sumL]
    rw [sumL_comm g n m]
    induction n with
    | zero => rfl
    | succ n ih => simp only [sumL]; rw [← ih]; omega

theorem sumL_congr' (f g : Nat → Nat) : ∀ n, (∀ i, i < n → f i = g i) → sumL f n = sumL g n
  | 0, _ => rfl
  | n + 1, h => by simp only [sumL]; rw [sumL_congr' f g n (fun i hi => h i (by omega)), h n (by omega)]

theorem sumL_all_one (f : Nat → Nat) : ∀ n, (∀ i, i < n → f i ≤ 1) → sumL f n = n → ∀ i, i < n → f i = 1
  | 0, _, _, i, hi => absurd hi (Nat.not_lt_zero _)
  | n + 1, hb, hs, i, hi => by
    simp only [sumL] at hs
    have h1 := sumL_le f 1 n (fun j hj => hb j (by omega))
    have h2 := hb n (by omega)
    rcases Nat.lt_or_ge i n with hi' | hi'
    · exact sumL_all_one f n (fun j hj => hb j (by omega)) (by omega) i hi'
    · rw [show i = n by omega]; omega

theorem le_sumL (f : Nat → Nat) : ∀ n r, r < n → f r ≤ sumL f n
  | 0, _, h => absurd h (Nat.not_lt_zero _)
  | n + 1, r, h => by
    simp only [sumL]
    rcases Nat.lt_or_ge r n with h1 | h1
    · have := le_sumL f n r h1; omega
    · rw [show r = n by omega]; omega

theorem sumL_zero_fun : ∀ n, sumL (fun _ => (0 : Nat)) n = 0
  | 0 => rfl
  | n + 1 => by simp only [sumL]; rw [sumL_zero_fun n]

/-- Exactly one index has the indicator; sums then pick that index. -/
theorem sumL_pick (ind f : Nat → Nat) (hb : ∀ r, ind r ≤ 1) : ∀ n, sumL ind n = 1 →
    sumL (fun r => ind r * f r) n = f (sumL (fun r => ind r * r) n) ∧ sumL (fun r => ind r * r) n < n ∧
      ind (sumL (fun r => ind r * r) n) = 1
  | 0, h => by simp [sumL] at h
  | n + 1, h => by
    simp only [sumL] at h ⊢
    by_cases hn : ind n = 1
    · have h0 : sumL ind n = 0 := by omega
      have hz : ∀ r, r < n → ind r = 0 := fun r hr => by have := le_sumL ind n r hr; omega
      have e1 : sumL (fun r => ind r * f r) n = 0 := by
        rw [sumL_congr' _ (fun _ => 0) n (fun r hr => by rw [hz r hr, Nat.zero_mul]), sumL_zero_fun]
      have e2 : sumL (fun r => ind r * r) n = 0 := by
        rw [sumL_congr' _ (fun _ => 0) n (fun r hr => by rw [hz r hr, Nat.zero_mul]), sumL_zero_fun]
      rw [e1, e2, hn]
      simp only [Nat.one_mul, Nat.zero_add]
      exact ⟨trivial, by omega, hn⟩
    · have hn0 : ind n = 0 := by have := hb n; omega
      obtain ⟨a, b, c⟩ := sumL_pick ind f hb n (by omega)
      rw [hn0, Nat.zero_mul, Nat.zero_mul, Nat.add_zero, Nat.add_zero]
      exact ⟨a, by omega, c⟩


def ind (ρ : Nat → Nat) (r k : Nat) : Nat := if ρ r = vinv k + 1 then 1 else 0
def πf (ρ : Nat → Nat) (k : Nat) : Nat := sumL (fun r => ind ρ r k * r) 16

theorem ind_le (ρ : Nat → Nat) (r k : Nat) : ind ρ r k ≤ 1 := by unfold ind; split <;> decide

theorem enc_inj (W : Nat) (f g : Nat → Nat) (L : Nat) (hf : ∀ m, m < L → f m < 2 ^ W) (hg : ∀ m, m < L → g m < 2 ^ W)
    (h : enc W f L = enc W g L) : ∀ k, k < L → f k = g k := by
  intro k hk
  rw [← enc_get W f L k hk hf, ← enc_get W g L k hk hg, h]

theorem vcount : ∀ v, v < 32 → sumL (fun k => if v = vinv k + 1 then 1 else 0) 16 ≤ 1 := by decide

theorem two_le_sumL (f : Nat → Nat) : ∀ n a b, a < n → b < n → a ≠ b → 1 ≤ f a → 1 ≤ f b → 2 ≤ sumL f n
  | 0, a, _, ha, _, _, _, _ => absurd ha (Nat.not_lt_zero _)
  | n + 1, a, b, ha, hb, hab, h1, h2 => by
    simp only [sumL]
    rcases Nat.lt_or_ge a n with a' | a' <;> rcases Nat.lt_or_ge b n with b' | b'
    · have := two_le_sumL f n a b a' b' hab h1 h2; omega
    · have := le_sumL f n a a'; rw [show b = n by omega] at h2; omega
    · have := le_sumL f n b b'; rw [show a = n by omega] at h1; omega
    · omega

theorem enc_lt_m1 (f : Nat → Nat) (hf : ∀ k, k < 16 → f k < 2 ^ 31) : enc 32 f 16 < 2 ^ 512 - 1 := by
  have h1 := enc_lt 32 f 15 (fun k hk => Nat.lt_of_lt_of_le (hf k (by omega)) (by decide))
  have h2 := hf 15 (by decide)
  rw [enc_succ]
  have : (2 : Nat) ^ (32 * 15) + (2 ^ 31 - 1) * 2 ^ (32 * 15) < 2 ^ 512 - 1 := by decide +kernel
  have h3 : f 15 * 2 ^ (32 * 15) ≤ (2 ^ 31 - 1) * 2 ^ (32 * 15) := Nat.mul_le_mul_right _ (by omega)
  omega

/-- The permutation check: every step has exactly one row, and the order is a bijection. -/
theorem permchk (ρ : Nat → Nat) (hρ : ∀ i, ρ i < 32)
    (h : Nat.xor (Nat.mod (ohQ (enc 512 ρ 16)) c16_M512) c16_ONES32C = 0) :
    (∀ k, k < 16 → sumL (fun r => ind ρ r k) 16 = 1) ∧ (∀ k, k < 16 → πf ρ k < 16 ∧ ind ρ (πf ρ k) k = 1) ∧
      (∀ r, r < 16 → ∃ k, k < 16 ∧ πf ρ k = r) := by
  have h1 := xor_zero_eq h
  rw [ohQ_eq ρ hρ, c16_M512_eq, c16_ONES32C_eq] at h1
  change enc 512 (fun r => enc 32 (fun k => ind ρ r k) 16) 16 % (2 ^ 512 - 1) = enc 32 (fun _ => 1) 16 at h1
  rw [enc_mod_m1, sumL_enc] at h1
  have hlt : ∀ k, k < 16 → sumL (fun r => ind ρ r k) 16 < 2 ^ 32 := fun k _ =>
    Nat.lt_of_le_of_lt (sumL_le _ 1 16 (fun r _ => ind_le ρ r k)) (by decide)
  rw [Nat.mod_eq_of_lt (enc_lt_m1 _ (fun k _ => Nat.lt_of_le_of_lt (sumL_le _ 1 16 (fun r _ => ind_le ρ r k)) (by decide)))] at h1
  have hc : ∀ k, k < 16 → sumL (fun r => ind ρ r k) 16 = 1 :=
    fun k hk => enc_inj 32 _ _ 16 hlt (fun _ _ => by decide) h1 k hk
  have hp : ∀ k, k < 16 → πf ρ k < 16 ∧ ind ρ (πf ρ k) k = 1 := fun k hk => by
    obtain ⟨_, b, c⟩ := sumL_pick (fun r => ind ρ r k) (fun r => r) (fun r => ind_le ρ r k) 16 (hc k hk)
    exact ⟨b, c⟩
  refine ⟨hc, hp, ?_⟩
  -- every row is hit: double counting
  have htot : sumL (fun k => sumL (fun r => ind ρ r k) 16) 16 = 16 := by
    rw [sumL_congr' _ (fun _ => 1) 16 hc]; rfl
  rw [sumL_comm] at htot
  have hrow : ∀ r, r < 16 → sumL (fun k => ind ρ r k) 16 = 1 :=
    sumL_all_one _ 16 (fun r _ => vcount (ρ r) (hρ r)) htot
  intro r hr
  -- some step `k` has row `r`
  obtain ⟨_, hk, hkr⟩ := sumL_pick (fun k => ind ρ r k) (fun k => k) (fun k => ind_le ρ r k) 16 (hrow r hr)
  generalize sumL (fun k => ind ρ r k * k) 16 = k at hk hkr
  refine ⟨k, hk, ?_⟩
  obtain ⟨b, c⟩ := hp k hk
  by_cases hne : πf ρ k = r
  · exact hne
  · have := two_le_sumL (fun r => ind ρ r k) 16 (πf ρ k) r b hr hne (by rw [c]; exact Nat.le_refl _) (by rw [hkr]; exact Nat.le_refl _)
    rw [hc k hk] at this; omega

theorem permV_eq (ρ v : Nat → Nat) (hρ : ∀ i, ρ i < 32) (hv' : ∀ r, v r < 2 ^ 31)
    (hc : ∀ k, k < 16 → sumL (fun r => ind ρ r k) 16 = 1) :
    permV (Nat.mul (ohQ (enc 512 ρ 16)) (nat_lit 4294967295)) (enc 512 v 16) = enc 32 (fun k => v (πf ρ k)) 16 := by
  have hv : ∀ r, v r < 2 ^ 32 := fun r => Nat.lt_of_lt_of_le (hv' r) (by decide)
  have hind : ∀ r k, ind ρ r k * 4294967295 < 2 ^ 32 := fun r k => by
    have := ind_le ρ r k; unfold ind at *; split <;> decide
  have hMQ : Nat.mul (ohQ (enc 512 ρ 16)) 4294967295
      = enc 512 (fun r => enc 32 (fun k => ind ρ r k * 4294967295) 16) 16 := by
    rw [ohQ_eq ρ hρ, P_mulr]
    apply enc_congr; intro r _
    rw [enc_mulc]; rfl
  unfold permV
  rw [hMQ, c16_REP32_eq, P_mulr]
  have hl1 : ∀ r, enc 32 (fun _ => v r) 16 < 2 ^ 512 := fun r => enc_lt 32 _ 16 (fun _ _ => hv r)
  have hl2 : ∀ r, enc 32 (fun k => ind ρ r k * 4294967295) 16 < 2 ^ 512 := fun r => enc_lt 32 _ 16 (fun k _ => hind r k)
  have e : (fun m => v m * enc 32 (fun _ => 1) 16) = (fun m => enc 32 (fun _ => v m) 16) := by funext m; rw [rep_eq]
  rw [e, P_and 512 (by decide) _ _ 16 (fun r _ => hl1 r) (fun r _ => hl2 r), c16_M512_eq]
  have e2 : (fun m => enc 32 (fun _ => v m) 16 &&& enc 32 (fun k => ind ρ m k * 4294967295) 16)
      = (fun m => enc 32 (fun k => ind ρ m k * v m) 16) := by
    funext m
    rw [enc_and 32 (by decide) _ _ 16 (fun _ _ => hv m) (fun k _ => hind m k)]
    apply enc_congr; intro k _
    unfold ind; split
    · rw [Nat.one_mul, Nat.one_mul, show (4294967295 : Nat) = 2 ^ 32 - 1 from rfl, Nat.and_two_pow_sub_one_eq_mod,
        Nat.mod_eq_of_lt (hv m)]
    · simp
  rw [e2]
  change enc 512 (fun m => enc 32 (fun k => ind ρ m k * v m) 16) 16 % (2 ^ 512 - 1) = _
  rw [enc_mod_m1, sumL_enc]
  have hpk : ∀ k, k < 16 → sumL (fun r => ind ρ r k * v r) 16 = v (πf ρ k) := fun k hk =>
    (sumL_pick (fun r => ind ρ r k) v (fun r => ind_le ρ r k) 16 (hc k hk)).1
  rw [enc_congr 32 16 hpk, Nat.mod_eq_of_lt (enc_lt_m1 _ (fun k _ => hv' _))]

end P8
end Submission

end


/-! # Proof part: DP2 -/

section
set_option exponentiation.threshold 2000000

namespace Submission
namespace P8

/-! ## Reading lanes, guard checks -/

theorem lane_read (W : Nat) (g : Nat → Nat) (N d : Nat) (hg : ∀ m, m < N → g m < 2 ^ W)
    (hz : ∀ m, N ≤ m → g m = 0) : (Nat.shiftRight (enc W g N) (W * d)) &&& (2 ^ W - 1) = g d := by
  by_cases hd : d < N
  · exact enc_lane_and W g N d hd hg
  · have hlt := enc_lt W g N hg
    rw [show Nat.shiftRight (enc W g N) (W * d) = enc W g N >>> (W * d) from rfl, Nat.shiftRight_eq_div_pow,
      Nat.div_eq_of_lt (Nat.lt_of_lt_of_le hlt (Nat.pow_le_pow_right (by omega) (Nat.mul_le_mul_left _ (by omega)))),
      Nat.zero_and, hz d (by omega)]

theorem c16_GM_eq : c16_GM = enc 11 (fun _ => 1536) 131072 := by
  unfold c16_GM
  rw [show (2047 : Nat) = 2 ^ 11 - 1 from rfl, enc_ones 11 (by decide), Nat.mul_comm, enc_mulc]

theorem g1536 (x : Nat) (hx : x < 2048) (h : x &&& 1536 = 0) : x < 512 := by
  have h9 : (x &&& 1536).testBit 9 = false := by rw [h]; rfl
  have h10 : (x &&& 1536).testBit 10 = false := by rw [h]; rfl
  rw [Nat.testBit_and, show (1536 : Nat).testBit 9 = true from rfl, Bool.and_true,
    Nat.testBit_eq_decide_div_mod_eq] at h9
  rw [Nat.testBit_and, show (1536 : Nat).testBit 10 = true from rfl, Bool.and_true,
    Nat.testBit_eq_decide_div_mod_eq] at h10
  simp only [decide_eq_false_iff_not] at h9 h10
  rw [show (2 : Nat) ^ 9 = 512 from rfl] at h9
  rw [show (2 : Nat) ^ 10 = 1024 from rfl] at h10
  omega

/-- A zero guard-bit check bounds every lane by `2^9`. -/
theorem chk_lanes (g : Nat → Nat) (N : Nat) (hN : N ≤ 131072) (hg : ∀ m, m < N → g m < 2 ^ 11)
    (h : Nat.land (enc 11 g N) c16_GM = 0) : ∀ m, m < N → g m < 2 ^ 9 := by
  rw [c16_GM_eq, enc_pad 11 g N 131072 hN, P_and 11 (by decide) _ _ 131072
    (fun m _ => by
      by_cases hm : m < N
      · rw [if_pos hm]; exact hg m hm
      · rw [if_neg hm]; exact Nat.two_pow_pos _) (fun _ _ => by decide)] at h
  intro m hm
  have := enc_eq_zero 11 _ 131072 h m (by omega)
  simp only [hm, ↓reduceIte] at this
  exact g1536 _ (hg m hm) this


theorem enc_mod_trim (W : Nat) (f : Nat → Nat) (N n : Nat) (hf : ∀ m, m < N → f m < 2 ^ W) :
    enc W f N % 2 ^ (W * n) = enc W (fun m => if m < n then f m else 0) N := by
  by_cases h : n ≤ N
  · obtain ⟨t, rfl⟩ : ∃ t, N = n + t := ⟨N - n, by omega⟩
    rw [enc_low W f n t hf, enc_pad W f n (n + t) (by omega)]
  · rw [Nat.mod_eq_of_lt (Nat.lt_of_lt_of_le (enc_lt W f N hf) (Nat.pow_le_pow_right (by omega)
      (Nat.mul_le_mul_left _ (by omega))))]
    apply enc_congr; intro m hm; rw [if_pos (by omega)]

variable (e : Nat → Nat) (R : Nat → List Nat) (lo mid hi : Nat → Nat) (T n : Nat)

def rem (k : Nat) : Nat := suf (fun j => hi j - lo j) k (n - k)

/-- Phase-2 invariant at level `k`: the state encodes a function agreeing with `G k` on the lanes that
can still reach the answer. -/
def Inv (N k S : Nat) : Prop :=
  ∃ g : Nat → Nat, S = enc 11 g N ∧ (∀ m, m < N → g m < 2 ^ 11) ∧ (∀ m, N ≤ m → g m = 0) ∧
    (∀ m, m ≤ rem lo hi n k → g m = G e R hi T n k m)

theorem Inv_step (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (N k S' : Nat) (hk : k < n) (g : Nat → Nat)
    (hb9 : ∀ m, m < N → g m < 2 ^ 9) (hz : ∀ m, N ≤ m → g m = 0)
    (hag : ∀ m, m ≤ rem lo hi n k → g m = G e R hi T n k m)
    (hS' : S' = stepR (enc 11 g N) (11 * (hi k - mid k)) (11 * (hi k - lo k)) ∨
      S' = stepR (enc 11 g N) (11 * (hi k - mid k)) (11 * (hi k - lo k)) % 2 ^ (11 * (rem lo hi n (k + 1) + 1))) :
    Inv e R lo hi T n N (k + 1) S' := by
  have hb : ∀ m, m < N → g m < 2 ^ 11 := fun m hm => Nat.lt_of_lt_of_le (hb9 m hm) (by decide)
  have hstep := stepR_enc 11 g N (hi k - mid k) (hi k - lo k) (by decide) hb hz
  have hb' : ∀ m, m < N → g m + g (m + (hi k - mid k)) + g (m + (hi k - lo k)) < 2 ^ 11 := by
    intro m hm
    have a1 := hb9 m hm
    have a2 : g (m + (hi k - mid k)) < 2 ^ 9 := by
      by_cases h : m + (hi k - mid k) < N
      · exact hb9 _ h
      · rw [hz _ (by omega)]; exact Nat.two_pow_pos _
    have a3 : g (m + (hi k - lo k)) < 2 ^ 9 := by
      by_cases h : m + (hi k - lo k) < N
      · exact hb9 _ h
      · rw [hz _ (by omega)]; exact Nat.two_pow_pos _
    have : (2 : Nat) ^ 9 * 3 ≤ 2 ^ 11 := by decide
    omega
  have hz' : ∀ m, N ≤ m → g m + g (m + (hi k - mid k)) + g (m + (hi k - lo k)) = 0 := by
    intro m hm; rw [hz m hm, hz _ (by omega), hz _ (by omega)]
  have hrem : rem lo hi n k = (hi k - lo k) + rem lo hi n (k + 1) := by
    unfold rem; rw [show n - k = (n - (k + 1)) + 1 by omega]; rfl
  have hag' : ∀ m, m ≤ rem lo hi n (k + 1) →
      g m + g (m + (hi k - mid k)) + g (m + (hi k - lo k)) = G e R hi T n (k + 1) m := by
    intro m hm
    have h1 := hs k
    rw [hag m (by omega), hag _ (by omega), hag _ (by omega), G_succ e R lo mid hi T n hR hs k m hk]
  rcases hS' with rfl | rfl
  · exact ⟨_, hstep, hb', hz', hag'⟩
  · refine ⟨fun m => if m < rem lo hi n (k + 1) + 1 then g m + g (m + (hi k - mid k)) + g (m + (hi k - lo k)) else 0,
      ?_, ?_, ?_, ?_⟩
    · rw [hstep, enc_mod_trim 11 _ N _ hb']
    · intro m hm; dsimp only; split
      · exact hb' m hm
      · exact Nat.two_pow_pos _
    · intro m hm; dsimp only; split
      · exact hz' m hm
      · rfl
    · intro m hm; dsimp only; rw [if_pos (by omega)]; exact hag' m hm


theorem trim16_cases (REMW lev S : Nat) :
    trim16 REMW lev S = S ∨ trim16 REMW lev S = S % 2 ^ (gat32 REMW lev) := by
  have e : Nat.mod S (Nat.shiftLeft 1 (gat32 REMW lev)) = S % 2 ^ (gat32 REMW lev) :=
    congrArg (Nat.mod S) (Nat.one_shiftLeft _)
  unfold trim16
  generalize Nat.xor lev (nat_lit 10) = a
  generalize Nat.xor lev (nat_lit 12) = b
  generalize Nat.xor lev (nat_lit 14) = c
  cases a with
  | zero => exact Or.inr e
  | succ a =>
    cases b with
    | zero => exact Or.inr e
    | succ b =>
      cases c with
      | zero => exact Or.inr e
      | succ c => exact Or.inl rfl

theorem suf_split (f : Nat → Nat) : ∀ a k b, suf f k (a + b) = suf f k a + suf f (k + a) b
  | 0, k, b => by simp [suf]
  | a + 1, k, b => by
    rw [show a + 1 + b = (a + b) + 1 by omega]
    show f k + suf f (k + 1) (a + b) = (f k + suf f (k + 1) a) + suf f (k + (a + 1)) b
    rw [suf_split f a (k + 1) b, show k + 1 + a = k + (a + 1) by omega, Nat.add_assoc]

theorem mp_sp (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) : ∀ k, mp lo k + sp lo hi k = suf hi 0 k
  | 0 => rfl
  | k + 1 => by
    have h := mp_sp hs k
    have h1 := hs k
    have h2 := suf_split hi k 0 1
    rw [Nat.zero_add] at h2
    rw [h2, ← h]
    show mp lo k + lo k + (sp lo hi k + (hi k - lo k)) = mp lo k + sp lo hi k + (hi k + 0)
    omega

theorem sum_split7 (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (n : Nat) (hn : 7 ≤ n) :
    suf hi 0 n = mp lo 7 + sp lo hi 7 + suf hi 7 (n - 7) := by
  have := suf_split hi 7 0 (n - 7)
  rw [show 7 + (n - 7) = n by omega, Nat.zero_add] at this
  rw [this, mp_sp lo mid hi hs 7]

theorem G_zero_above (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (k : Nat) (hk : k ≤ n) (i : Nat)
    (h : suf hi 0 n < i + T) : G e R hi T n k i = 0 := by
  have hsum := suf_split hi k 0 (n - k)
  rw [show k + (n - k) = n by omega, Nat.zero_add, ← mp_sp lo mid hi hs k] at hsum
  unfold G
  split
  · exact F_supp e R lo mid hi hR hs k _ (Or.inr (by omega))
  · rfl

theorem F_all_lt (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (k B : Nat) (hB : 0 < B)
    (h : ∀ i, i < sp lo hi k + 1 → F e R k (i + mp lo k) < B) : ∀ t, F e R k t < B := by
  intro t
  by_cases ht : t < mp lo k ∨ mp lo k + sp lo hi k < t
  · rw [F_supp e R lo mid hi hR hs k t ht]; exact hB
  · have := h (t - mp lo k) (by omega)
    rwa [Nat.sub_add_cancel (by omega)] at this

theorem F_step_lt (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k]) (k B : Nat) (hB : 0 < B)
    (h : ∀ t, F e R k t < B) : ∀ t, F e R (k + 1) t < 3 * B := by
  intro t
  rw [F_succ_tri e R lo mid hi hR]
  have g : ∀ w, (if w ≤ t then F e R k (t - w) else 0) < B := by
    intro w; split
    · exact h _
    · exact hB
  have := g (lo k); have := g (mid k); have := g (hi k)
  omega

theorem rebase (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (hn : 7 ≤ n) (hT : T ≤ suf hi 0 n)
    (hb : ∀ m, m < sp lo hi 7 + 1 → F e R 7 (m + mp lo 7) < 2 ^ 11) :
    Nat.shiftRight (Nat.shiftLeft (enc 11 (fun i => F e R 7 (i + mp lo 7)) (sp lo hi 7 + 1))
      (Nat.mul (Nat.sub (suf hi 0 n - T) (sp lo hi 7)) 11)) (Nat.mul (Nat.sub (sp lo hi 7) (suf hi 0 n - T)) 11)
    = enc 11 (G e R hi T n 7) (suf hi 0 n - T + 1) := by
  have hsum := sum_split7 lo mid hi hs n hn
  generalize hC : suf hi 0 n - T = C1
  generalize hP : sp lo hi 7 = PRE at hb hsum
  generalize hM : mp lo 7 = M at hb hsum
  generalize hD : suf hi 7 (n - 7) = D at hsum
  show Nat.shiftRight (Nat.shiftLeft (enc 11 (fun i => F e R 7 (i + M)) (PRE + 1)) ((C1 - PRE) * 11))
    ((PRE - C1) * 11) = _
  unfold G
  rw [hD]
  by_cases hc : PRE ≤ C1
  · rw [Nat.sub_eq_zero_of_le hc, Nat.zero_mul]
    show Nat.shiftLeft (enc 11 (fun i => F e R 7 (i + M)) (PRE + 1)) ((C1 - PRE) * 11) = _
    rw [Nat.mul_comm, enc_shl', show PRE + 1 + (C1 - PRE) = C1 + 1 by omega]
    apply enc_congr; intro i hi1
    by_cases h1 : C1 - PRE ≤ i
    · rw [if_pos h1, if_pos (show D ≤ i + T by omega)]
      congr 1; omega
    · rw [if_neg h1]
      split
      · exact (F_supp e R lo mid hi hR hs 7 _ (Or.inl (by rw [hM]; omega))).symm
      · rfl
  · rw [Nat.sub_eq_zero_of_le (by omega : C1 ≤ PRE), Nat.zero_mul]
    show enc 11 (fun i => F e R 7 (i + M)) (PRE + 1) >>> ((PRE - C1) * 11) = _
    rw [Nat.mul_comm, enc_shiftRight 11 _ (PRE - C1) (PRE + 1) (by omega) hb,
      show PRE + 1 - (PRE - C1) = C1 + 1 by omega]
    apply enc_congr; intro i hi1
    rw [if_pos (show D ≤ i + T by omega)]
    congr 1; omega


/-- The phase-2 loop, levels `7 … 15`. -/
theorem ph2_inv (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (XW YW REMW S7 N : Nat) (hN : N ≤ 131072)
    (hX : ∀ k, k < 16 → gat32 XW k = 11 * (hi k - mid k))
    (hY : ∀ k, k < 16 → gat32 YW k = 11 * (hi k - lo k))
    (hRM : ∀ k, k < 16 → gat32 REMW k = 11 * (rem lo hi 16 k + 1))
    (g7 : Nat → Nat) (h7 : S7 = enc 11 g7 N) (hb7 : ∀ m, m < N → g7 m < 2 ^ 9) (hz7 : ∀ m, N ≤ m → g7 m = 0)
    (ha7 : ∀ m, m ≤ rem lo hi 16 7 → g7 m = G e R hi T 16 7 m)
    (hchk : ∀ j, 1 ≤ j → j ≤ 7 → Nat.land (ph2 XW YW REMW S7 j) c16_GM = 0) :
    ∀ j, j ≤ 8 → ∃ g : Nat → Nat, ph2 XW YW REMW S7 j = enc 11 g N ∧ (∀ m, m < N → g m < 2 ^ 11) ∧
      (∀ m, N ≤ m → g m = 0) ∧ (∀ m, m ≤ rem lo hi 16 (7 + j) → g m = G e R hi T 16 (7 + j) m) ∧
      (j = 0 → ∀ m, m < N → g m < 2 ^ 9)
  | 0, _ => ⟨g7, h7, fun m hm => Nat.lt_of_lt_of_le (hb7 m hm) (by decide), hz7, ha7, fun _ => hb7⟩
  | j + 1, hj => by
    obtain ⟨g, hS, hb, hz, hag, h0⟩ := ph2_inv hR hs XW YW REMW S7 N hN hX hY hRM g7 h7 hb7 hz7 ha7 hchk j (by omega)
    have hb9 : ∀ m, m < N → g m < 2 ^ 9 := by
      by_cases hj0 : j = 0
      · exact h0 hj0
      · exact chk_lanes g N hN hb (by rw [← hS]; exact hchk j (by omega) (by omega))
    have ex : gat32 XW (Nat.add 7 j) = 11 * (hi (7 + j) - mid (7 + j)) := hX (7 + j) (by omega)
    have ey : gat32 YW (Nat.add 7 j) = 11 * (hi (7 + j) - lo (7 + j)) := hY (7 + j) (by omega)
    have e8 : Nat.add 8 j = 7 + j + 1 := by show 8 + j = 7 + j + 1; omega
    have hp : ph2 XW YW REMW S7 (j + 1) = trim16 REMW (Nat.add 8 j)
      (stepR (ph2 XW YW REMW S7 j) (gat32 XW (Nat.add 7 j)) (gat32 YW (Nat.add 7 j))) := rfl
    rw [ex, ey, e8, hS] at hp
    have hc := trim16_cases REMW (7 + j + 1)
      (stepR (enc 11 g N) (11 * (hi (7 + j) - mid (7 + j))) (11 * (hi (7 + j) - lo (7 + j))))
    rw [hRM (7 + j + 1) (by omega), ← hp] at hc
    have hI := Inv_step e R lo mid hi T 16 hR hs N (7 + j) _ (by omega) g hb9 hz hag
      (show ph2 XW YW REMW S7 (j + 1) = _ ∨ ph2 XW YW REMW S7 (j + 1) = _ from hc)
    obtain ⟨g', h1, h2, h3, h4⟩ := hI
    exact ⟨g', h1, h2, h3, h4, fun h => absurd h (by omega)⟩

theorem ph1_P1st (ZW YW : Nat)
    (hY : ∀ k, k < 16 → gat32 YW k = 11 * (hi k - lo k))
    (hZ : ∀ k, k < 16 → gat32 ZW k = 11 * (mid k - lo k)) :
    ∀ k, k ≤ 16 → ph1 ZW YW k = P1st (fun j => 11 * (mid j - lo j)) (fun j => 11 * (hi j - lo j)) k
  | 0, _ => rfl
  | k + 1, hk => by
    show stepL (ph1 ZW YW k) (gat32 ZW k) (gat32 YW k) = stepL (P1st _ _ k) _ _
    rw [ph1_P1st ZW YW hY hZ k (by omega), hZ k (by omega), hY k (by omega)]

theorem lastRow_eq (g : Nat → Nat) (N d1 d2 : Nat) (hg : ∀ m, m < N → g m < 2 ^ 11)
    (hz : ∀ m, N ≤ m → g m = 0) :
    lastRow (enc 11 g N) (11 * d1) (11 * d2) = g 0 + g d1 + g d2 := by
  have h0 := lane_read 11 g N 0 hg hz
  have h1 := lane_read 11 g N d1 hg hz
  have h2 := lane_read 11 g N d2 hg hz
  rw [show (2 : Nat) ^ 11 - 1 = 2047 from rfl] at h0 h1 h2
  have h0' : enc 11 g N &&& 2047 = g 0 := h0
  show (enc 11 g N &&& 2047) + (Nat.shiftRight (enc 11 g N) (11 * d1) &&& 2047)
    + (Nat.shiftRight (enc 11 g N) (11 * d2) &&& 2047) = _
  rw [h0', h1, h2]

theorem shr17 (x : Nat) (h : Nat.shiftRight x 17 = 0) : x < 131072 := by
  have h' : x / 2 ^ 17 = 0 := by rw [← Nat.shiftRight_eq_div_pow]; exact h
  have := Nat.div_add_mod x (2 ^ 17)
  have := Nat.mod_lt x (Nat.two_pow_pos 17)
  rw [h', Nat.mul_zero, Nat.zero_add] at *
  rw [show (2 : Nat) ^ 17 = 131072 from rfl] at *
  omega

theorem levChk_zero (XW YW ZW REMW C1 PRE : Nat) (h : levChk XW YW ZW REMW C1 PRE = 0) :
    Nat.land (ph1 ZW YW 6) c16_GM = 0 ∧ Nat.land (ph1 ZW YW 7) c16_GM = 0 ∧
    ∀ j, 1 ≤ j → j ≤ 7 → Nat.land (lev16 XW YW ZW REMW C1 PRE j) c16_GM = 0 := by
  have h' : Nat.land (ph1 ZW YW 6) c16_GM + Nat.land (ph1 ZW YW 7) c16_GM
    + Nat.land (lev16 XW YW ZW REMW C1 PRE 1) c16_GM + Nat.land (lev16 XW YW ZW REMW C1 PRE 2) c16_GM
    + Nat.land (lev16 XW YW ZW REMW C1 PRE 3) c16_GM + Nat.land (lev16 XW YW ZW REMW C1 PRE 4) c16_GM
    + Nat.land (lev16 XW YW ZW REMW C1 PRE 5) c16_GM + Nat.land (lev16 XW YW ZW REMW C1 PRE 6) c16_GM
    + Nat.land (lev16 XW YW ZW REMW C1 PRE 7) c16_GM = 0 := h
  refine ⟨by omega, by omega, ?_⟩
  intro j hj1 hj7
  have : j = 1 ∨ j = 2 ∨ j = 3 ∨ j = 4 ∨ j = 5 ∨ j = 6 ∨ j = 7 := by omega
  rcases this with rfl | rfl | rfl | rfl | rfl | rfl | rfl <;> omega


/-- The packed DP (phase 1, rebase, phase 2 with trims, last row) computes `F 16 T` when every check passes. -/
theorem dp16_eq (hR : ∀ k, ((R k).map e).Perm [lo k, mid k, hi k])
    (hs : ∀ k, lo k ≤ mid k ∧ mid k ≤ hi k) (XW YW ZW REMW C1 PRE : Nat)
    (hX : ∀ k, k < 16 → gat32 XW k = 11 * (hi k - mid k))
    (hY : ∀ k, k < 16 → gat32 YW k = 11 * (hi k - lo k))
    (hZ : ∀ k, k < 16 → gat32 ZW k = 11 * (mid k - lo k))
    (hRM : ∀ k, k < 16 → gat32 REMW k = 11 * (rem lo hi 16 k + 1))
    (hT : T ≤ suf hi 0 16) (hC1 : C1 = suf hi 0 16 - T) (hPRE : PRE = sp lo hi 7)
    (hc1 : Nat.shiftRight (Nat.add C1 PRE) 17 = 0)
    (hlev : levChk XW YW ZW REMW C1 PRE = 0) :
    dp16 XW YW ZW REMW C1 PRE = F e R 16 T := by
  obtain ⟨c6, c7, cl⟩ := levChk_zero XW YW ZW REMW C1 PRE hlev
  have hsm : C1 + PRE < 131072 := shr17 _ hc1
  subst hC1; subst hPRE
  have hP1 : ∀ k, k ≤ 16 → ph1 ZW YW k = enc 11 (fun i => F e R k (i + mp lo k)) (sp lo hi k + 1) := by
    intro k hk
    rw [ph1_P1st lo mid hi ZW YW hY hZ k hk]
    exact P1st_eq e R lo mid hi 11 hR hs _ _ (fun _ => rfl) (fun _ => rfl) k
  have h3 : ∀ k, (R k).length ≤ 3 := by
    intro k; have := (hR k).length_eq; simp at this; omega
  have sp67 : sp lo hi 7 = sp lo hi 6 + (hi 6 - lo 6) := rfl
  have b6 : ∀ m, m < sp lo hi 6 + 1 → F e R 6 (m + mp lo 6) < 2 ^ 11 := by
    intro m _; exact Nat.lt_of_le_of_lt (F_le_pow e R h3 6 _) (by decide)
  have c6' := chk_lanes _ _ (by omega) b6 (by rw [← hP1 6 (by decide)]; exact c6)
  have a6 := F_all_lt e R lo mid hi hR hs 6 (2 ^ 9) (Nat.two_pow_pos _) c6'
  have a7' := F_step_lt e R lo mid hi hR 6 (2 ^ 9) (Nat.two_pow_pos _) a6
  have b7 : ∀ m, m < sp lo hi 7 + 1 → F e R 7 (m + mp lo 7) < 2 ^ 11 := by
    intro m _; exact Nat.lt_of_lt_of_le (a7' _) (by decide)
  have c7' := chk_lanes _ _ (by omega) b7 (by rw [← hP1 7 (by decide)]; exact c7)
  have a7 := F_all_lt e R lo mid hi hR hs 7 (2 ^ 9) (Nat.two_pow_pos _) c7'
  have hS7 : Nat.shiftRight (Nat.shiftLeft (ph1 ZW YW 7) (Nat.mul (Nat.sub (suf hi 0 16 - T) (sp lo hi 7)) 11))
      (Nat.mul (Nat.sub (sp lo hi 7) (suf hi 0 16 - T)) 11) = enc 11 (G e R hi T 16 7) (suf hi 0 16 - T + 1) := by
    rw [hP1 7 (by decide)]
    exact rebase e R lo mid hi T 16 hR hs (by decide) hT b7
  have hb7 : ∀ m, m < suf hi 0 16 - T + 1 → G e R hi T 16 7 m < 2 ^ 9 := by
    intro m _; unfold G; split
    · exact a7 _
    · exact Nat.two_pow_pos _
  have hz7 : ∀ m, suf hi 0 16 - T + 1 ≤ m → G e R hi T 16 7 m = 0 := fun m hm =>
    G_zero_above e R lo mid hi T 16 hR hs 7 (by decide) m (by omega)
  obtain ⟨g, hS, hb, hz, hag, _⟩ := ph2_inv e R lo mid hi T hR hs XW YW REMW _ (suf hi 0 16 - T + 1) (by omega)
    hX hY hRM (G e R hi T 16 7) hS7 hb7 hz7 (fun _ _ => rfl) (fun j h1 h2 => cl j h1 h2) 8 (by decide)
  have hd : dp16 XW YW ZW REMW (suf hi 0 16 - T) (sp lo hi 7)
      = lastRow (ph2 XW YW REMW (Nat.shiftRight (Nat.shiftLeft (ph1 ZW YW 7)
        (Nat.mul (Nat.sub (suf hi 0 16 - T) (sp lo hi 7)) 11)) (Nat.mul (Nat.sub (sp lo hi 7) (suf hi 0 16 - T)) 11)) 8)
        (gat32 XW 15) (gat32 YW 15) := rfl
  rw [hd, hS, hX 15 (by decide), hY 15 (by decide), lastRow_eq g _ _ _ hb hz]
  have hr : rem lo hi 16 (7 + 8) = hi 15 - lo 15 + 0 := rfl
  have h15 := hs 15
  rw [hag 0 (by omega), hag _ (by omega), hag _ (by omega)]
  have hG := G_succ e R lo mid hi T 16 hR hs 15 0 (by decide)
  rw [Nat.zero_add, Nat.zero_add] at hG
  rw [show (7 + 8 : Nat) = 15 from rfl, ← hG]
  have h0 : suf hi 16 (16 - 16) = 0 := rfl
  unfold G
  rw [h0, if_pos (Nat.zero_le _), Nat.zero_add, Nat.sub_zero]

end P8
end Submission

end


/-! # Proof part: Glue -/

section
set_option exponentiation.threshold 2000000

namespace Submission
namespace P8

/-! ## Lane reads of 32-bit packed vectors -/

theorem gat32_enc (f : Nat → Nat) (k : Nat) (hk : k < 16) (hf : ∀ m, m < 16 → f m < 2 ^ 32) :
    gat32 (enc 32 f 16) k = f k :=
  enc_get 32 f 16 k hk hf

theorem c1V_eq (h : Nat → Nat) (hh : ∀ i, i < 16 → h i ≤ 2 ^ 15) :
    c1V (enc 512 h 16) = sumL h 16 - 65535 := by
  have hs : sumL h 16 ≤ 16 * 2 ^ 15 := sumL_le h _ 16 hh
  show enc 512 h 16 % c16_M512 - 65535 = _
  rw [c16_M512_eq, enc_mod_m1, Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt hs (by decide +kernel))]

theorem preV_eq (f : Nat → Nat) (hf : ∀ k, k < 16 → f k < 2 ^ 16) :
    preV (enc 32 f 16) = sumL f 7 := by
  have hs : sumL f 7 ≤ 7 * 2 ^ 16 := sumL_le f _ 7 (fun i hi => Nat.le_of_lt (hf i (by omega)))
  have hl := enc_low 32 f 7 9 (fun m hm => Nat.lt_of_lt_of_le (hf m hm) (by decide))
  show enc 32 f (7 + 9) % 2 ^ (32 * 7) % (2 ^ 32 - 1) = _
  rw [hl, enc_mod_m1, Nat.mod_eq_of_lt (Nat.lt_of_le_of_lt hs (by decide))]

/-! ## Suffix sums by a multiply -/

section Conv
variable (f : Nat → Nat)

def g16 (m : Nat) : Nat := if m < 16 then 1 else 0

theorem conv_low (k : Nat) : ∀ L, L ≤ k → conv f g16 L (15 + k) = 0
  | 0, _ => rfl
  | L + 1, h => by
    simp only [conv]
    rw [conv_low k L (by omega), if_pos (by omega)]
    show 0 + f L * (if 15 + k - L < 16 then 1 else 0) = 0
    rw [if_neg (by omega), Nat.mul_zero]

theorem conv_suf (k : Nat) : ∀ L, k ≤ L → L ≤ 16 → conv f g16 L (15 + k) = suf f k (L - k)
  | 0, h, _ => by rw [show k = 0 by omega]; rfl
  | L + 1, h, hL => by
    simp only [conv]
    by_cases hk : k ≤ L
    · rw [conv_suf k L hk (by omega), if_pos (by omega)]
      show suf f k (L - k) + f L * (if 15 + k - L < 16 then 1 else 0) = _
      rw [if_pos (by omega), Nat.mul_one, show L + 1 - k = (L - k) + 1 by omega, suf_split,
        show k + (L - k) = L by omega]
      rfl
    · rw [conv_low f k L (by omega), if_pos (by omega)]
      show 0 + f L * (if 15 + k - L < 16 then 1 else 0) = _
      rw [if_neg (by omega), Nat.mul_zero, show L + 1 - k = 0 by omega]
      rfl

theorem conv_le (B : Nat) (hf : ∀ j, j < 16 → f j ≤ B) : ∀ L q, L ≤ 16 → conv f g16 L q ≤ L * B
  | 0, _, _ => Nat.zero_le _
  | L + 1, q, hL => by
    simp only [conv]
    have ih := conv_le B hf L q (by omega)
    have hfL := hf L (by omega)
    have : (if L ≤ q then f L * g16 (q - L) else 0) ≤ B := by
      split
      · unfold g16; split
        · rw [Nat.mul_one]; exact hfL
        · rw [Nat.mul_zero]; exact Nat.zero_le _
      · exact Nat.zero_le _
    rw [Nat.succ_mul]; omega

theorem remW_eq (hf : ∀ k, k < 16 → f k < 2 ^ 16) :
    remW (enc 32 f 16) = enc 32 (fun k => (suf f k (16 - k) + 1) * 11) 16 := by
  have hSUF : c16_SUF = enc 32 g16 16 := by
    rw [show c16_SUF = c16_ONES32C from rfl, c16_ONES32C_eq]
    exact enc_congr 32 16 (fun m hm => (if_pos hm).symm)
  have hmul := enc_mul_conv 32 f g16 16 (fun m hm => if_neg (by omega)) 16
  have hB : ∀ q, conv f g16 16 q ≤ 16 * 2 ^ 16 := fun q =>
    conv_le f (2 ^ 16) (fun j hj => Nat.le_of_lt (hf j hj)) 16 q (by decide)
  have hlt : ∀ q, conv f g16 16 q < 2 ^ 32 := fun q => Nat.lt_of_le_of_lt (hB q) (by decide)
  have hsh : enc 32 (conv f g16 16) 32 >>> 480 = enc 32 (fun m => conv f g16 16 (15 + m)) 17 :=
    enc_high 32 (conv f g16 16) 15 17 (fun m _ => hlt m)
  have hpad : enc 32 (fun m => conv f g16 16 (15 + m)) 17 = enc 32 (fun m => conv f g16 16 (15 + m)) 16 :=
    (enc_pad' 32 _ 16 17 (by decide) (fun i h1 h2 => by
      rw [show i = 16 by omega]; exact conv_zero_high f g16 16 (fun m hm => if_neg (by omega)) 16 _ (by decide))).symm
  show Nat.mul (Nat.add (Nat.shiftRight (Nat.mul (enc 32 f 16) c16_SUF) 480) c16_ONES32C) 11 = _
  rw [hSUF, show Nat.mul (enc 32 f 16) (enc 32 g16 16) = enc 32 f 16 * enc 32 g16 16 from rfl, hmul,
    show Nat.shiftRight (enc 32 (conv f g16 16) (16 + 16)) 480 = enc 32 (conv f g16 16) 32 >>> 480 from rfl,
    hsh, hpad, c16_ONES32C_eq, P_add, P_mulr]
  apply enc_congr; intro k hk
  show (conv f g16 16 (15 + k) + 1) * 11 = _
  rw [conv_suf f k 16 (by omega) (by decide)]

end Conv

/-! ## Sorting three weights (non-strict) -/

theorem sort3' (x y z : Nat) :
    mn3 x y z ≤ md3 x y z ∧ md3 x y z ≤ mx3 x y z ∧ [x, y, z].Perm [mn3 x y z, md3 x y z, mx3 x y z] := by
  have hmn : mn3 x y z = min x (min y z) := rfl
  have hmx : mx3 x y z = max x (max y z) := rfl
  have hmd : md3 x y z = x + y + z - mn3 x y z - mx3 x y z := rfl
  by_cases h1 : x ≤ y <;> by_cases h2 : y ≤ z <;> by_cases h3 : x ≤ z
  · rw [show mn3 x y z = x by omega, show mx3 x y z = z by omega] at hmd ⊢
    rw [show md3 x y z = y by omega]; exact ⟨h1, h2, List.Perm.refl _⟩
  · omega
  · -- x ≤ z < y
    rw [show mn3 x y z = x by omega, show mx3 x y z = y by omega] at hmd ⊢
    rw [show md3 x y z = z by omega]
    exact ⟨h3, by omega, List.Perm.cons _ (List.Perm.swap z y [])⟩
  · -- z < x ≤ y
    rw [show mn3 x y z = z by omega, show mx3 x y z = y by omega] at hmd ⊢
    rw [show md3 x y z = x by omega]
    refine ⟨by omega, h1, ?_⟩
    -- [x, y, z] ~ [z, x, y]
    exact (List.Perm.cons x (List.Perm.swap z y [])).trans (List.Perm.swap z x [y])
  · -- y < x ≤ z
    rw [show mn3 x y z = y by omega, show mx3 x y z = z by omega] at hmd ⊢
    rw [show md3 x y z = x by omega]
    exact ⟨by omega, h3, List.Perm.swap y x [z]⟩
  · -- y ≤ z < x
    rw [show mn3 x y z = y by omega, show mx3 x y z = x by omega] at hmd ⊢
    rw [show md3 x y z = z by omega]
    refine ⟨h2, by omega, ?_⟩
    -- [x, y, z] ~ [y, z, x]
    exact (List.Perm.swap y x [z]).trans (List.Perm.cons y (List.Perm.swap z x []))
  · omega
  · -- z < y < x
    rw [show mn3 x y z = z by omega, show mx3 x y z = x by omega] at hmd ⊢
    rw [show md3 x y z = y by omega]
    refine ⟨by omega, by omega, ?_⟩
    -- [x, y, z] ~ [z, y, x]
    exact (List.Perm.swap y x [z]).trans ((List.Perm.cons y (List.Perm.swap z x [])).trans
      ((List.Perm.swap z y [x])))

theorem mn3_rot (x y z : Nat) : mn3 z x y = mn3 x y z := by unfold mn3; omega
theorem mx3_rot (x y z : Nat) : mx3 z x y = mx3 x y z := by unfold mx3; omega
theorem md3_rot (x y z : Nat) : md3 z x y = md3 x y z := by unfold md3 mn3 mx3; omega

/-! ## Sums -/

theorem sumL_list (f : Nat → Nat) : ∀ n, sumL f n = ((List.range n).map f).sum
  | 0 => rfl
  | n + 1 => by
    rw [List.range_succ, List.map_append, List.sum_append, ← sumL_list f n]
    simp [sumL]

theorem suf_sumL (f : Nat → Nat) : ∀ n, suf f 0 n = sumL f n
  | 0 => rfl
  | n + 1 => by
    have h := suf_split f n 0 1
    rw [Nat.zero_add] at h
    rw [h, suf_sumL f n]
    simp [suf, sumL]

theorem sp_sumL (lo hi : Nat → Nat) : ∀ k, sp lo hi k = sumL (fun j => hi j - lo j) k
  | 0 => rfl
  | k + 1 => by
    show sp lo hi k + (hi k - lo k) = sumL _ k + (hi k - lo k)
    rw [sp_sumL lo hi k]

theorem sumL_mono (f g : Nat → Nat) : ∀ n, (∀ i, i < n → f i ≤ g i) → sumL f n ≤ sumL g n
  | 0, _ => Nat.le_refl _
  | n + 1, h => by
    have := sumL_mono f g n (fun i hi => h i (by omega))
    have := h n (by omega)
    show sumL f n + f n ≤ sumL g n + g n
    omega


/-! ## The column generator (v7) -/

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

theorem colsP (s : Nat) (hs : s < 2 ^ 32) :
    colA s = enc 72 (permanentColumnOne 16 s) 16 ∧ colB s = enc 72 (permanentColumnTwo 16 s) 16 :=
  cols_enc 16 s R_16 Kc_16 Mv_16 (nat_lit 61172327492847069472032393719205726809135813743440799050195397570919697796091958321786863938157971792315844506873509046544459008355036150650333616890210625686064472971480622053109783197015954399612052812141827922088117778074833698589048132156300022844899841969874763871624802603515651998113045708569927237462546233168834543264678118409417047146496) (nat_lit 1152) MvD_16 (nat_lit 2290649225) (nat_lit 35)
    (nat_lit 4908534053) (nat_lit 36) g1_16 g0_16 g2_16 o_16 (by decide) (by decide) hs R_16_eq Kc_16_eq
    Mv_16_eq (by decide +kernel) rfl MvD_16_eq (by decide) (by decide) div_16a (by decide) (by decide)
    div_16b g1_16_eq g0_16_eq g2_16_eq o_16_eq

/-! ## Naming the intermediate vectors -/

def gROW (s : Nat) : Nat := rowV (colA s) (colB s)
def gE (s : Nat) : Nat := eV (labRK (gROW s))
def gO (s : Nat) : Nat := oV (gROW s) (eRev (gE s))
def gHi (s : Nat) : Nat := hiV (gO s)
def gLo (s : Nat) : Nat := loV (gO s)
def gMid (s : Nat) : Nat := midV (gO s)
def gOHQ (s : Nat) : Nat := ohQ (ordRK (gHi s))
def gP1 (s : Nat) : Nat := permV (Nat.mul (gOHQ s) (nat_lit 4294967295)) (Nat.sub (gHi s) (gLo s))
def gP2 (s : Nat) : Nat := permV (Nat.mul (gOHQ s) (nat_lit 4294967295)) (Nat.sub (gHi s) (gMid s))

theorem fastS16_unfold (s : Nat) : fastS16 s = fastD s (gE s) (gOHQ s) (amtX (gP2 s)) (amtY (gP1 s))
    (Nat.sub (amtY (gP1 s)) (amtX (gP2 s))) (remW (gP1 s)) (c1V (gHi s)) (preV (gP1 s)) := rfl

theorem fastD_spec (s E OHQ XW YW ZW REMW C1 PRE : Nat)
    (h : chk16 E OHQ XW YW ZW REMW C1 PRE = 0 →
      dp16 XW YW ZW REMW C1 PRE = permanentSpec (genPermanentMatrix 16 s)) :
    fastD s E OHQ XW YW ZW REMW C1 PRE = permanentSpec (genPermanentMatrix 16 s) := by
  unfold fastD
  rw [pickZ_eq]
  split
  · exact h ‹_›
  · exact main_eq 16 s (by decide)

theorem chk16_zero (E OHQ XW YW ZW REMW C1 PRE : Nat) (h : chk16 E OHQ XW YW ZW REMW C1 PRE = 0) :
    Nat.xor (Nat.mod E c16_M512) 65535 = 0 ∧ Nat.xor (Nat.mod OHQ c16_M512) c16_ONES32C = 0 ∧
      levChk XW YW ZW REMW C1 PRE = 0 ∧ Nat.shiftRight (Nat.add C1 PRE) 17 = 0 := by
  have h' : Nat.xor (Nat.mod E c16_M512) 65535 + Nat.xor (Nat.mod OHQ c16_M512) c16_ONES32C
    + levChk XW YW ZW REMW C1 PRE + Nat.shiftRight (Nat.add C1 PRE) 17 = 0 := h
  omega

theorem vinv_inj : ∀ x, x < 16 → ∀ y, y < 16 → vinv x = vinv y → x = y := by decide

theorem ind_one (ρ : Nat → Nat) (r k : Nat) (h : ind ρ r k = 1) : ρ r = vinv k + 1 := by
  unfold ind at h
  split at h
  · assumption
  · exact absurd h (by decide)

/-- The order is a permutation of the rows. -/
theorem order_perm (ρ : Nat → Nat)
    (hπ : ∀ k, k < 16 → πf ρ k < 16 ∧ ind ρ (πf ρ k) k = 1) (hsurj : ∀ r, r < 16 → ∃ k, k < 16 ∧ πf ρ k = r) :
    ((List.range 16).map (πf ρ)).Perm (List.range 16) := by
  have hinj : ∀ x y, x < 16 → y < 16 → πf ρ x = πf ρ y → x = y := by
    intro x y hx hy h
    have h1 := ind_one ρ _ _ (hπ x hx).2
    have h2 := ind_one ρ _ _ (hπ y hy).2
    rw [h] at h1
    exact vinv_inj x hx y hy (by omega)
  have hnd : ((List.range 16).map (πf ρ)).Nodup := by
    unfold List.Nodup
    rw [List.pairwise_map]
    exact List.Pairwise.imp_of_mem (fun {x y} hx hy (hxy : x < y) h =>
      absurd (hinj x y (List.mem_range.mp hx) (List.mem_range.mp hy) h) (by omega)) List.pairwise_lt_range
  apply (List.perm_ext_iff_of_nodup hnd List.nodup_range).mpr
  intro x
  rw [List.mem_map, List.mem_range]
  constructor
  · rintro ⟨k, hk, rfl⟩
    exact (hπ k (List.mem_range.mp hk)).1
  · intro hx
    obtain ⟨k, hk, he⟩ := hsurj x hx
    exact ⟨k, List.mem_range.mpr hk, he⟩


/-- The new dimension-16 path computes the spec permanent. -/
theorem fastS16_eq (s : Nat) (hs : s < 2 ^ 32) : fastS16 s = permanentSpec (genPermanentMatrix 16 s) := by
  rw [fastS16_unfold]
  apply fastD_spec
  intro hchk
  obtain ⟨cE, cQ, cL, c17⟩ := chk16_zero _ _ _ _ _ _ _ _ hchk
  -- columns
  obtain ⟨hA, hB⟩ := colsP s hs
  have ha : ∀ i, i < 16 → permanentColumnOne 16 s i < 16 := fun i hi => (col1_facts 16 s i (by decide) hi).1
  have hai : ∀ i, i < 16 → permanentColumnOne 16 s i ≠ i := fun i hi => (col1_facts 16 s i (by decide) hi).2
  have hb : ∀ i, i < 16 → permanentColumnTwo 16 s i < 16 := fun i hi => (col2_facts 16 s i (by decide) hi).1
  have hbi : ∀ i, i < 16 → permanentColumnTwo 16 s i ≠ i := fun i hi => (col2_facts 16 s i (by decide) hi).2.1
  have hab : ∀ i, i < 16 → permanentColumnOne 16 s i ≠ permanentColumnTwo 16 s i := fun i hi =>
    Ne.symm (col2_facts 16 s i (by decide) hi).2.2
  generalize ha_def : permanentColumnOne 16 s = a at hA ha hai hab
  generalize hb_def : permanentColumnTwo 16 s = b at hB hb hbi hab
  have hROW : gROW s = enc 512 (fun i => enc 16 (rowInd a b i) 16) 16 := by
    unfold gROW; rw [hA, hB]; exact rowV_eq a b ha hb
  -- labels and weights
  obtain ⟨ρ, hρ, hRK⟩ := labRK_lanes (gROW s)
  have hE : gE s = enc 512 (fun i => epow (ρ i)) 16 := by unfold gE; rw [hRK]; exact eV_eq ρ hρ
  rw [hE] at cE
  obtain ⟨hv, hinj, hsum⟩ := chkE_spec ρ cE
  have hw : Wts (fun c => epow (ρ c)) (fun c => ρ c - 1) :=
    ⟨fun c hc => epow_v _ (hv c hc), fun c hc => by have := hv c hc; show ρ c - 1 < 16; omega,
     fun x y hx hy h => hinj x y hx hy (by
       have h' : ρ x - 1 = ρ y - 1 := h; have := hv x hx; have := hv y hy; omega)⟩
  have hεlt : ∀ c, c < 16 → epow (ρ c) < 2 ^ 16 := by
    intro c hc; rw [epow_v _ (hv c hc)]
    exact Nat.pow_lt_pow_right (by decide) (by have := hv c hc; omega)
  have hEr : eRev (gE s) = enc 16 (fun t => epow (ρ (15 - t))) 16 := by
    rw [hE]; exact eRev_eq (fun c => epow (ρ c)) hεlt
  have hO : gO s = enc 512 (fun i => 2 ^ (ρ (a i) - 1) + 2 ^ (ρ (b i) - 1) + 2 ^ (ρ i - 1)) 16 := by
    unfold gO; rw [hEr, hROW, oV_eq a b _ _ hw ha hb hai hbi hab]
    apply enc_congr; intro i hi
    show epow (ρ (a i)) + epow (ρ (b i)) + epow (ρ i) = _
    rw [hw.pow _ (ha i hi), hw.pow _ (hb i hi), hw.pow _ hi]
  obtain ⟨L1, hL1⟩ : ∃ L1 : Nat → Nat, ∀ i, L1 i = ρ (a i) - 1 := ⟨_, fun _ => rfl⟩
  obtain ⟨L2, hL2⟩ : ∃ L2 : Nat → Nat, ∀ i, L2 i = ρ (b i) - 1 := ⟨_, fun _ => rfl⟩
  obtain ⟨L3, hL3⟩ : ∃ L3 : Nat → Nat, ∀ i, L3 i = ρ i - 1 := ⟨_, fun _ => rfl⟩
  have hd : ∀ i, i < 16 → L1 i ≠ L2 i ∧ L1 i ≠ L3 i ∧ L2 i ≠ L3 i ∧ L1 i < 16 ∧ L2 i < 16 ∧ L3 i < 16 := by
    intro i hi
    rw [hL1, hL2, hL3]
    exact ⟨fun h => hab i hi (hw.inj _ _ (ha i hi) (hb i hi) h), fun h => hai i hi (hw.inj _ _ (ha i hi) hi h),
      fun h => hbi i hi (hw.inj _ _ (hb i hi) hi h), hw.lt _ (ha i hi), hw.lt _ (hb i hi), hw.lt _ hi⟩
  have hO' : gO s = enc 512 (fun i => 2 ^ L1 i + 2 ^ L2 i + 2 ^ L3 i) 16 := by
    rw [hO]; apply enc_congr; intro i _; rw [hL1, hL2, hL3]
  obtain ⟨_, hloE, hhiE, hmidE⟩ := lohi_vec L1 L2 L3 hd
  have hL30 : ∀ i, L1 i ≤ 30 ∧ L2 i ≤ 30 ∧ L3 i ≤ 30 := by
    intro i; rw [hL1, hL2, hL3]
    have := hρ (a i); have := hρ (b i); have := hρ i
    exact ⟨by omega, by omega, by omega⟩
  have hsrt : ∀ i, mn3 (L1 i) (L2 i) (L3 i) ≤ md3 (L1 i) (L2 i) (L3 i) ∧
      md3 (L1 i) (L2 i) (L3 i) ≤ mx3 (L1 i) (L2 i) (L3 i) := fun i => ⟨(sort3' _ _ _).1, (sort3' _ _ _).2.1⟩
  have hmx30 : ∀ i, mx3 (L1 i) (L2 i) (L3 i) ≤ 30 := by
    intro i; have := hL30 i; unfold mx3; omega
  have hmx15 : ∀ i, i < 16 → mx3 (L1 i) (L2 i) (L3 i) < 16 := by
    intro i hi; have := hd i hi; unfold mx3; omega
  have hL3mx : ∀ i, L3 i ≤ mx3 (L1 i) (L2 i) (L3 i) := by intro i; unfold mx3; omega
  obtain ⟨loR, hloR⟩ : ∃ f : Nat → Nat, ∀ i, f i = 2 ^ mn3 (L1 i) (L2 i) (L3 i) := ⟨_, fun _ => rfl⟩
  obtain ⟨midR, hmidR⟩ : ∃ f : Nat → Nat, ∀ i, f i = 2 ^ md3 (L1 i) (L2 i) (L3 i) := ⟨_, fun _ => rfl⟩
  obtain ⟨hiR, hhiR⟩ : ∃ f : Nat → Nat, ∀ i, f i = 2 ^ mx3 (L1 i) (L2 i) (L3 i) := ⟨_, fun _ => rfl⟩
  have hLo : gLo s = enc 512 loR 16 := by
    unfold gLo; rw [hO', hloE]; exact enc_congr 512 16 (fun i _ => (hloR i).symm)
  have hHi : gHi s = enc 512 hiR 16 := by
    unfold gHi; rw [hO', hhiE]; exact enc_congr 512 16 (fun i _ => (hhiR i).symm)
  have hMid : gMid s = enc 512 midR 16 := by
    unfold gMid; rw [hO', hmidE]; exact enc_congr 512 16 (fun i _ => (hmidR i).symm)
  have hlm : ∀ i, loR i ≤ midR i ∧ midR i ≤ hiR i := by
    intro i; rw [hloR, hmidR, hhiR]
    exact ⟨Nat.pow_le_pow_right (by decide) (hsrt i).1, Nat.pow_le_pow_right (by decide) (hsrt i).2⟩
  have hhi30 : ∀ i, hiR i ≤ 2 ^ 30 := by
    intro i; rw [hhiR]; exact Nat.pow_le_pow_right (by decide) (hmx30 i)
  have hhi15 : ∀ i, i < 16 → hiR i ≤ 2 ^ 15 := by
    intro i hi; rw [hhiR]; exact Nat.pow_le_pow_right (by decide) (by have := hmx15 i hi; omega)
  -- the row order
  obtain ⟨ρ', hρ', hRK'⟩ : ∃ ρ' : Nat → Nat, (∀ i, ρ' i < 32) ∧ ordRK (gHi s) = enc 512 ρ' 16 := mask31_lanes _
  have hQ : gOHQ s = ohQ (enc 512 ρ' 16) := by unfold gOHQ; rw [hRK']
  rw [hQ] at cQ
  obtain ⟨hc, hπ, hsurj⟩ := permchk ρ' hρ' cQ
  have hperm := order_perm ρ' hπ hsurj
  have hπlt : ∀ k, k < 16 → πf ρ' k < 16 := fun k hk => (hπ k hk).1
  have bd : ∀ x y, x ≤ 2 ^ 15 → (x - y) * 11 < 2 ^ 32 := by
    intro x y h; have : (2 : Nat) ^ 15 = 32768 := rfl; have : (2 : Nat) ^ 32 = 4294967296 := rfl; omega
  have bd16 : ∀ x y, x ≤ 2 ^ 15 → x - y < 2 ^ 16 := by
    intro x y h; have : (2 : Nat) ^ 15 = 32768 := rfl; have : (2 : Nat) ^ 16 = 65536 := rfl; omega
  have hpi15 : ∀ k, k < 16 → hiR (πf ρ' k) ≤ 2 ^ 15 := fun k hk => hhi15 _ (hπlt k hk)
  -- packed differences in row order
  have hV1 : Nat.sub (gHi s) (gLo s) = enc 512 (fun i => hiR i - loR i) 16 := by
    rw [hHi, hLo]; exact enc_sub 512 hiR loR 16 (fun m _ => Nat.le_trans (hlm m).1 (hlm m).2)
  have hV2 : Nat.sub (gHi s) (gMid s) = enc 512 (fun i => hiR i - midR i) 16 := by
    rw [hHi, hMid]; exact enc_sub 512 hiR midR 16 (fun m _ => (hlm m).2)
  have h31 : ∀ (g : Nat → Nat) r, hiR r - g r < 2 ^ 31 := fun g r =>
    Nat.lt_of_le_of_lt (Nat.le_trans (Nat.sub_le _ _) (hhi30 r)) (by decide)
  have hP1 : gP1 s = enc 32 (fun k => hiR (πf ρ' k) - loR (πf ρ' k)) 16 := by
    unfold gP1; rw [hQ, hV1]; exact permV_eq ρ' _ hρ' (h31 loR) hc
  have hP2 : gP2 s = enc 32 (fun k => hiR (πf ρ' k) - midR (πf ρ' k)) 16 := by
    unfold gP2; rw [hQ, hV2]; exact permV_eq ρ' _ hρ' (h31 midR) hc
  -- the DP data
  have hR : ∀ k, ((supp 16 s (πf ρ' k)).map (fun c => 2 ^ (ρ c - 1))).Perm
      [loR (πf ρ' k), midR (πf ρ' k), hiR (πf ρ' k)] := by
    intro k
    generalize πf ρ' k = r
    have hsupp : supp 16 s r = [r, a r, b r] := by
      unfold supp; rw [if_neg (by decide), ha_def, hb_def]
    rw [hsupp]
    have hp := (sort3' (L3 r) (L1 r) (L2 r)).2.2
    rw [mn3_rot, md3_rot, mx3_rot] at hp
    have hp2 := hp.map (fun x => 2 ^ x)
    simp only [List.map] at hp2 ⊢
    rw [hloR r, hmidR r, hhiR r, ← hL3 r, ← hL1 r, ← hL2 r]
    exact hp2
  have hs' : ∀ k, loR (πf ρ' k) ≤ midR (πf ρ' k) ∧ midR (πf ρ' k) ≤ hiR (πf ρ' k) := fun k => hlm _
  have hX : ∀ k, k < 16 → gat32 (amtX (gP2 s)) k = 11 * (hiR (πf ρ' k) - midR (πf ρ' k)) := by
    intro k hk
    show gat32 (Nat.mul (gP2 s) 11) k = _
    rw [hP2, P_mulr, gat32_enc _ k hk (fun m hm => bd _ _ (hpi15 m hm)), Nat.mul_comm]
  have hY : ∀ k, k < 16 → gat32 (amtY (gP1 s)) k = 11 * (hiR (πf ρ' k) - loR (πf ρ' k)) := by
    intro k hk
    show gat32 (Nat.mul (gP1 s) 11) k = _
    rw [hP1, P_mulr, gat32_enc _ k hk (fun m hm => bd _ _ (hpi15 m hm)), Nat.mul_comm]
  have hZ : ∀ k, k < 16 → gat32 (Nat.sub (amtY (gP1 s)) (amtX (gP2 s))) k
      = 11 * (midR (πf ρ' k) - loR (πf ρ' k)) := by
    intro k hk
    show gat32 (Nat.sub (Nat.mul (gP1 s) 11) (Nat.mul (gP2 s) 11)) k = _
    rw [hP1, hP2, P_mulr, P_mulr]
    show gat32 (enc 32 (fun m => (hiR (πf ρ' m) - loR (πf ρ' m)) * 11) 16
      - enc 32 (fun m => (hiR (πf ρ' m) - midR (πf ρ' m)) * 11) 16) k = _
    rw [enc_sub 32 _ _ 16 (fun m _ => by have := hlm (πf ρ' m); exact Nat.mul_le_mul_right _ (by omega))]
    rw [gat32_enc _ k hk (fun m hm => Nat.lt_of_le_of_lt (Nat.sub_le _ _) (bd _ _ (hpi15 m hm)))]
    have := hlm (πf ρ' k)
    show (hiR (πf ρ' k) - loR (πf ρ' k)) * 11 - (hiR (πf ρ' k) - midR (πf ρ' k)) * 11 = _
    omega
  have hsuf : ∀ m, m < 16 → (suf (fun j => hiR (πf ρ' j) - loR (πf ρ' j)) m (16 - m) + 1) * 11 < 2 ^ 32 := by
    intro m hm
    rw [← conv_suf _ m 16 (by omega) (by decide)]
    have := conv_le (fun j => hiR (πf ρ' j) - loR (πf ρ' j)) (2 ^ 16)
      (fun j hj => Nat.le_of_lt (bd16 _ _ (hpi15 j hj))) 16 (15 + m) (by decide)
    have : (2 : Nat) ^ 16 = 65536 := rfl; have : (2 : Nat) ^ 32 = 4294967296 := rfl
    omega
  have hRM : ∀ k, k < 16 → gat32 (remW (gP1 s)) k
      = 11 * (rem (fun k => loR (πf ρ' k)) (fun k => hiR (πf ρ' k)) 16 k + 1) := by
    intro k hk
    rw [hP1, remW_eq _ (fun j hj => bd16 _ _ (hpi15 j hj)), gat32_enc _ k hk hsuf, Nat.mul_comm]
    rfl
  have hsumhi : suf (fun k => hiR (πf ρ' k)) 0 16 = sumL hiR 16 := by
    rw [suf_sumL, sumL_list, sumL_list]
    have : (List.range 16).map (fun k => hiR (πf ρ' k)) = ((List.range 16).map (πf ρ')).map hiR := by
      rw [List.map_map]; rfl
    rw [this]; exact (hperm.map hiR).sum_nat
  have hT : 65535 ≤ suf (fun k => hiR (πf ρ' k)) 0 16 := by
    rw [hsumhi]
    have h1 := sumL_mono (fun c => 2 ^ (ρ c - 1)) hiR 16 (fun i _ => by
      rw [hhiR, ← hL3 i]; exact Nat.pow_le_pow_right (by decide) (hL3mx i))
    rw [hsum] at h1
    exact h1
  have hC1 : c1V (gHi s) = suf (fun k => hiR (πf ρ' k)) 0 16 - 65535 := by
    rw [hHi, c1V_eq hiR hhi15, hsumhi]
  have hPRE : preV (gP1 s) = sp (fun k => loR (πf ρ' k)) (fun k => hiR (πf ρ' k)) 7 := by
    rw [hP1, preV_eq _ (fun j hj => bd16 _ _ (hpi15 j hj)), sp_sumL]
  have hdp := dp16_eq (fun c => 2 ^ (ρ c - 1)) (fun k => supp 16 s (πf ρ' k)) (fun k => loR (πf ρ' k))
    (fun k => midR (πf ρ' k)) (fun k => hiR (πf ρ' k)) 65535 hR hs' _ _ _ _ _ _ hX hY hZ hRM hT hC1 hPRE c17 cL
  rw [hdp, F_cnt]
  have hrows : (((List.range 16).map (fun k => supp 16 s (πf ρ' k))).reverse).Perm
      ((List.range 16).map (supp 16 s)) := by
    refine (List.reverse_perm _).trans ?_
    have : (List.range 16).map (fun k => supp 16 s (πf ρ' k)) = ((List.range 16).map (πf ρ')).map (supp 16 s) := by
      rw [List.map_map]; rfl
    rw [this]; exact hperm.map _
  rw [cnt_perm _ hrows, spec_cnt 16 s (fun c => ρ c - 1) hw.lt hw.inj]

end P8
end Submission

end


namespace Submission

/-- Compiled code for `impl` (core Lean cannot compile `Bool.rec`); `implC_eq` shows they agree. -/
def implC (n : Nat) : Nat :=
  if Nat.shiftRight n 32 = 6 then mainU6 (Nat.land n 0xffffffff)
  else if Nat.shiftRight n 32 = 12 then mainU12 (Nat.land n 0xffffffff)
  else if Nat.shiftRight n 32 = 16 then P8.mainV16 (Nat.land n 0xffffffff)
  else implOld n

/-- Dimensions `6, 12` use the v7 unrolled graphs, `16` the new packed DP (`P8.mainV16`);
everything else `implOld`. The tests are `Bool.rec` on `Nat.beq`, cheaper for the kernel than a
`Nat.rec` on a numeral. -/
@[implemented_by implC]
def impl (n : Nat) : Nat :=
  share d := Nat.shiftRight n (nat_lit 32);
  share s := Nat.land n (nat_lit 0xffffffff);
  Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (implOld n) (P8.mainV16 s) (Nat.beq d (nat_lit 16)))
      (mainU12 s) (Nat.beq d (nat_lit 12)))
    (mainU6 s) (Nat.beq d (nat_lit 6))

theorem brec_eq (x y : Nat) (b : Bool) :
    Bool.rec (motive := fun _ => Nat) x y b = if b = true then y else x := by
  cases b <;> rfl

theorem impl_correct : ∀ n, impl n = permanentSpecN n := by
  intro n
  have hs : Nat.land n (nat_lit 0xffffffff) < 2 ^ 32 := Nat.and_lt_two_pow _ (by decide)
  have hspec : ∀ D, Nat.shiftRight n (nat_lit 32) = D →
      permanentSpec (genPermanentMatrix D (Nat.land n (nat_lit 0xffffffff))) = permanentSpecN n := by
    intro D h
    unfold permanentSpecN permanentDimension permanentSeed
    rw [show n >>> 32 = D from h]
    rfl
  show Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (implOld n) (P8.mainV16 (Nat.land n (nat_lit 0xffffffff)))
        (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 16)))
      (mainU12 (Nat.land n (nat_lit 0xffffffff))) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 12)))
    (mainU6 (Nat.land n (nat_lit 0xffffffff))) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 6)) = _
  simp only [brec_eq, Nat.beq_eq]
  by_cases h6 : Nat.shiftRight n (nat_lit 32) = 6
  · rw [if_pos h6, mainU6_eq, mainS6_eq _ hs]; exact hspec 6 h6
  rw [if_neg h6]
  by_cases h12 : Nat.shiftRight n (nat_lit 32) = 12
  · rw [if_pos h12, mainU12_eq, mainS12_eq _ hs]; exact hspec 12 h12
  rw [if_neg h12]
  by_cases h16 : Nat.shiftRight n (nat_lit 32) = 16
  · rw [if_pos h16, P8.mainV16.eq, P8.fastS16_eq _ hs]; exact hspec 16 h16
  rw [if_neg h16]
  exact implOld_correct n

theorem implC_eq (n : Nat) : implC n = impl n := by
  show _ = Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (implOld n) (P8.mainV16 (Nat.land n (nat_lit 0xffffffff)))
        (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 16)))
      (mainU12 (Nat.land n (nat_lit 0xffffffff))) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 12)))
    (mainU6 (Nat.land n (nat_lit 0xffffffff))) (Nat.beq (Nat.shiftRight n (nat_lit 32)) (nat_lit 6))
  simp only [implC, brec_eq, Nat.beq_eq]

end Submission
