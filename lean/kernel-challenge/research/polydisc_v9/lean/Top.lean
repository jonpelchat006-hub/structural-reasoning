import V9.Run

/-!
# The low-part run is the specification's normal resultant

`lowRun_spec`: on the 25 encoded coefficients of a monic polynomial whose coefficients are within
the D5 widths, a run with no failed check returns the specification's `normalResultant`.
-/

namespace V9

/-- v7's encoding `2·|x| + [x < 0]` (identical to the submission's `zdec`). -/
def zdec (z : Nat) : Int := if z % 2 = 1 then -((z / 2 : Nat) : Int) else ((z / 2 : Nat) : Int)

theorem zres_spec (mag s q : Nat) (hs : s ≤ 1) (hm : mag < 2 ^ q) :
    zres mag s (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q) = res q (if s = 1 then -(mag : Int) else mag) := by
  have e1 : Nat.shiftLeft 1 q = 2 ^ q := by rw [nshl, Nat.one_mul]
  unfold zres
  rw [e1]
  simp only [nmask, nadd, nmul, nsub]
  apply Int.ofNat_inj.1
  rw [res_cast, natCast_mod_pow]
  rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hs with h | h <;> subst h
  · simp only [Nat.sub_zero, Nat.one_mul, Nat.zero_mul, Nat.add_zero, show ¬((0 : Nat) = 1) by decide, ↓reduceIte]
  · simp only [Nat.sub_self, Nat.zero_mul, Nat.zero_add, Nat.one_mul, ↓reduceIte]
    rw [Int.ofNat_sub (Nat.le_of_lt hm), cast_two_pow]
    rw [show (2 : Int) ^ q - mag = -(mag : Int) + 2 ^ q * 1 by grind, Int.add_mul_emod_self_left]

theorem zdec_eq (x : Nat) : zdec x = if x % 2 = 1 then -((x / 2 : Nat) : Int) else ((x / 2 : Nat) : Int) := rfl

theorem zres_z (x k q : Nat) (hm : x / 2 * k < 2 ^ q) :
    zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q)
      = res q ((k : Int) * zdec x) := by
  rw [show Nat.mul (Nat.shiftRight x 1) k = x / 2 * k by rw [nmul, nshr, Nat.pow_one], and_one]
  rw [zres_spec _ _ _ (by omega) hm, zdec_eq]
  congr 1
  by_cases h : x % 2 = 1
  · rw [if_pos h, if_pos h]; push_cast; grind
  · rw [if_neg h, if_neg h]; push_cast; grind

theorem zres_z1 (x q : Nat) (hm : x / 2 < 2 ^ q) :
    zres (Nat.shiftRight x 1) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 q) 1) (Nat.shiftLeft 1 q) = res q (zdec x) := by
  have := zres_z x 1 q (by omega)
  rw [show Nat.mul (Nat.shiftRight x 1) 1 = Nat.shiftRight x 1 from Nat.mul_one _] at this
  rw [this]; simp

/-! ## The input lists -/

theorem map_toN (h : Nat → Nat) (q : Nat) : ∀ (n : Nat) (L : List Nat), L.length = n + 1 →
    (∀ x ∈ L, h x = res q (zdec x)) →
    L.map h = toN q (fun e => if e ≤ n then zdec (L.getD (n - e) 0) else 0) n
  | 0, [x], _, hh => by simp [toN, toL, hh x (by simp)]
  | n + 1, x :: L, hl, hh => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    rw [List.map_cons, map_toN h q n L hl (fun y hy => hh y (List.mem_cons_of_mem _ hy)), toN_succ,
      hh x (by simp)]
    simp only [Nat.le_refl, ↓reduceIte, Nat.sub_self, List.getD_cons_zero]
    congr 1
    unfold toN; congr 1; apply toL_congr; intro e he
    rw [if_pos he, if_pos (by omega), show n + 1 - e = (n - e) + 1 by omega, List.getD_cons_succ]

def dksN : Nat → List Nat
  | 0 => [1]
  | n + 1 => (n + 2) :: dksN n

theorem dks_eq : dks = dksN 23 := rfl

theorem zip_toN (h : Nat → Nat → Nat) (q : Nat) : ∀ (n : Nat) (L : List Nat), L.length = n + 2 →
    (∀ x ∈ L, ∀ k, k ≤ n + 1 → h x k = res q ((k : Int) * zdec x)) →
    List.zipWith h L (dksN n) =
      toN q (fun e => if e ≤ n then ((e + 1 : Nat) : Int) * zdec (L.getD (n - e) 0) else 0) n
  | 0, [x, y], _, hh => by simp [toN, toL, dksN, hh x (by simp) 1 (by omega)]
  | n + 1, x :: L, hl, hh => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    rw [dksN, List.zipWith_cons_cons, zip_toN h q n L hl (fun y hy k hk => hh y (List.mem_cons_of_mem _ hy) k (by omega)),
      toN_succ, hh x (by simp) (n + 2) (by omega)]
    simp only [Nat.le_refl, ↓reduceIte, Nat.sub_self, List.getD_cons_zero]
    congr 1
    unfold toN; congr 1; apply toL_congr; intro e he
    rw [if_pos he, if_pos (by omega), show n + 1 - e = (n - e) + 1 by omega, List.getD_cons_succ]

/-! ## The whole run -/

def fX (xs : List Nat) (e : Nat) : Int := if e ≤ 24 then zdec (xs.getD (24 - e) 0) else 0
def gX (xs : List Nat) (e : Nat) : Int := if e ≤ 23 then ((e + 1 : Nat) : Int) * zdec (xs.getD (23 - e) 0) else 0

theorem width_le (k i : Nat) : coefficientWidth k i ≤ k := by
  unfold coefficientWidth clampWidth
  split <;> simp only <;> omega

set_option exponentiation.threshold 4000 in
theorem FbN_le (e : Nat) : FbN e ≤ 2 ^ 3483 := by
  unfold FbN
  split
  · exact Nat.one_le_two_pow
  · split
    · exact Nat.pow_le_pow_right (by decide) (by have := width_le 3484 (24 - e); omega)
    · exact Nat.zero_le _

theorem natAbs_zdec (x : Nat) : (zdec x).natAbs = x / 2 := by
  unfold zdec; split <;> omega

theorem zenc_spec (a : Nat) (L : Int) (hL : L.natAbs < 2 ^ a) :
    zdec (Nat.add (Nat.shiftLeft (Nat.add (Nat.sub (res (a + 1) L) (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))))
      (Nat.sub (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))) (res (a + 1) L))) 1)
      (Nat.shiftRight (res (a + 1) L) a)) = L := by
  rw [mag_spec a L hL]
  have hs : Nat.shiftRight (res (a + 1) L) a = if L < 0 then 1 else 0 := (res_val a L hL).1
  rw [hs, nadd, nshl, Nat.pow_one]
  unfold zdec
  by_cases h : L < 0
  · rw [if_pos h, if_pos (by omega), show (L.natAbs * 2 + 1) / 2 = L.natAbs by omega]; omega
  · rw [if_neg h, if_neg (by omega), show (L.natAbs * 2 + 0) / 2 = L.natAbs by omega]; omega

def initA (xs : List Nat) : List Nat :=
  xs.map (fun x => zres (Nat.shiftRight x 1) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 3485) 1) (Nat.shiftLeft 1 3485))

def initB (xs : List Nat) : List Nat :=
  List.zipWith (fun x k => zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) (Nat.sub (Nat.shiftLeft 1 3489) 1)
    (Nat.shiftLeft 1 3489)) xs dks

def zencW (u : Nat) : Nat :=
  Nat.add (Nat.shiftLeft (Nat.add (Nat.sub u (Nat.mul (Nat.shiftRight u 81024) (Nat.shiftLeft 1 81025)))
    (Nat.sub (Nat.mul (Nat.shiftRight u 81024) (Nat.shiftLeft 1 81025)) u)) 1) (Nat.shiftRight u 81024)

theorem lowRun_eq (xs : List Nat) : lowRun xs =
    (zencW (hd0 (lrunR lparams (initB xs) (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).1
        (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).2).1),
      (lrunR lparams (initB xs) (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).1
        (lstep 3485 3489 3500 3484 3488 true [] (initA xs) (initB xs) Prod.mk).2).2) := by
  unfold lowRun
  simp only
  rw [lstep_cps, lrun_cps]
  rfl

theorem qw_vals : qw 1 = 3489 ∧ qw 2 = 3500 ∧ qw 24 = 81025 := by decide

set_option exponentiation.threshold 100000 in
/-- The low-part run on encoded coefficients: no failed check means the specification's result. -/
theorem lowRun_spec (xs : List Nat) (hlen : xs.length = 25) (h0 : zdec (xs.getD 0 0) = 1)
    (hxb : ∀ x ∈ xs, x / 2 ≤ 2 ^ 3483) (hb : ∀ e, (fX xs e).natAbs ≤ FbN e) (hbad : (lowRun xs).2 = 0) :
    normalResultant (toL (fX xs) 24) (toL (gX xs) 23) = some (zdec (lowRun xs).1) := by
  have hf : ∀ e, 24 < e → fX xs e = 0 := fun e he => by unfold fX; rw [if_neg (by omega)]
  have hg : ∀ e, 23 < e → gX xs e = 0 := fun e he => by unfold gX; rw [if_neg (by omega)]
  have hgf : ∀ e, e ≤ 23 → gX xs e = ((e + 1 : Nat) : Int) * fX xs (e + 1) := by
    intro e he; unfold gX fX; rw [if_pos he, if_pos (by omega), show 24 - (e + 1) = 23 - e by omega]
  have hgb : ∀ e, (gX xs e).natAbs ≤ GbN e := by
    intro e
    by_cases he : e ≤ 23
    · rw [hgf e he, Int.natAbs_mul]
      unfold GbN; rw [if_pos (by omega)]
      simp only [Int.natAbs_natCast]
      exact Nat.mul_le_mul_left _ (hb (e + 1))
    · rw [hg e (by omega)]; exact Nat.zero_le _
  have hgw : ∀ e, (gX xs e).natAbs < 2 ^ (qw 1 - 1) := by
    intro e
    rw [qw_vals.1]
    have h1 := hgb e
    have h2 : GbN e ≤ 24 * 2 ^ 3483 := by
      unfold GbN; split
      · exact Nat.mul_le_mul (by omega) (FbN_le _)
      · exact Nat.zero_le _
    have h3 : 24 * 2 ^ 3483 < 2 ^ (3489 - 1) := by
      have e : (2 : Nat) ^ (3489 - 1) = 2 ^ 3483 * 2 ^ 5 := by rw [← Nat.pow_add]
      have hp := Nat.two_pow_pos 3483
      rw [e]; generalize 2 ^ 3483 = P at hp ⊢; omega
    omega
  have hfw : ∀ e, e ≤ 24 → (fX xs e).natAbs < 2 ^ 3484 := fun e _ =>
    Nat.lt_of_le_of_lt (Nat.le_trans (hb e) (FbN_le e)) (Nat.pow_lt_pow_right (by decide) (by decide))
  have hf24 : fX xs 24 = 1 := by unfold fX; simpa using h0
  -- the input residues
  have hA0 : initA xs = toN 3485 (fX xs) 24 := by
    unfold initA
    rw [map_toN _ 3485 24 xs hlen (fun x hx => zres_z1 x 3485 (Nat.lt_of_le_of_lt (hxb x hx)
      (Nat.pow_lt_pow_right (by decide) (by decide))))]
    rfl
  have hB0 : initB xs = toN 3489 (gX xs) 23 := by
    unfold initB
    rw [dks_eq, zip_toN _ 3489 23 xs hlen (fun x hx k hk => zres_z x k 3489 (by
      have := hxb x hx
      have h3 : 24 * 2 ^ 3483 < 2 ^ 3489 := by
        have e : (2 : Nat) ^ 3489 = 2 ^ 3483 * 2 ^ 6 := by rw [← Nat.pow_add]
        have hp := Nat.two_pow_pos 3483
        rw [e]; generalize 2 ^ 3483 = P at hp ⊢; omega
      calc x / 2 * k ≤ 2 ^ 3483 * 24 := Nat.mul_le_mul this (by omega)
        _ < 2 ^ 3489 := by rw [Nat.mul_comm]; exact h3))]
    rfl
  -- step 0 (no division)
  obtain ⟨H0, b0, hst0, hok0⟩ := lstep_spec 3484 3488 3500 true [] (fX xs) (gX xs) (chainP (fX xs) (gX xs) 24 1).2 22
    (by decide) (by decide) (by decide)
    (fun e he => hfw e (by omega))
    (fun e he => by have := hgw e; rwa [qw_vals.1] at this)
    (fun _ => hf24) (fun h => absurd h (by decide))
    (fun e _ => by rw [chain_first]; simp)
    Prod.mk
  rw [lowRun_eq, hA0, hB0, hst0] at hbad ⊢
  simp only at hbad ⊢
  have hb0 : b0 = 0 := by
    have := lrunR_mono lparams (toN 3489 (gX xs) 23) H0 b0; omega
  obtain ⟨hH0, hC0⟩ := hok0 hb0
  -- steps 1 … 22
  obtain ⟨hF, hLall⟩ := lrunR_spec (fX xs) (gX xs) hf hg hb hgb hgw lparams 1 _ H0 b0 stepsOK_lparams
    (Nat.le_refl _) (by rw [qw_vals.1]; rfl) (by rw [hH0, qw_vals.2.1])
    (fun k' hk' => by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hk' with h | h <;> subst h
      · show gX xs 23 ≠ 0
        rw [hgf 23 (by decide), hf24]; decide
      · exact hC0)
    hbad
  rw [hF, qw_vals.2.2]
  -- the result
  have hdeg : ∀ e, 24 - 1 < e → gX xs e = 0 := fun e he => hg e (by omega)
  rw [normalResultant_chain (fX xs) (gX xs) 24 (by decide) hf hdeg (by rw [hf24]; decide) hLall]
  have hbnd := chain_bound (fX xs) (gX xs) hf hg hb hgb 24 (by decide) (by decide)
    (fun k' hk' => hLall k' (by omega)) 0 (by decide)
  rw [qw_vals.2.2] at hbnd
  have e0 : toN 81025 (chainP (fX xs) (gX xs) 24 23).2 0 = [res 81025 ((chainP (fX xs) (gX xs) 24 23).2 0)] := rfl
  rw [e0, hd0_cons]
  unfold zencW
  rw [zenc_spec 81024 _ hbnd]

end V9
