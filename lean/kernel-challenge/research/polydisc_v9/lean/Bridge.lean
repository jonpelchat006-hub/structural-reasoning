import Spec
import V9.Subres

/-!
# The chain functions run the specification's normal PRS

`toL P n` is the high-to-low coefficient list of a degree-`n` polynomial `P : Nat → Int`.
When every leading coefficient of the chain is nonzero, the specification's `normalResultant`
on `toL f m`, `toL g (m-1)` returns the constant of the last chain polynomial
(`normalResultant_chain`). The pseudo-remainder step is `prem_eq'`: unlike v7's `prem_eq` it
needs no `c₁ ≠ 0` (a zero `c₁` is trimmed and the second stage is a plain scaling).
-/

namespace V9

/-! ## From v7 (identical copies) -/

def r2 (LG LF C1 : Int) : List Int → List Int → List Int
  | X :: Xs, Z :: Zs => (LG * (LG * X - LF * Zs.headD 0) - C1 * Z) :: r2 LG LF C1 Xs Zs
  | _, _ => []

theorem cancel_r2 (LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    cancelPseudoLeading LG C1 (cancelPseudoLeading LG LF Xs Zs.tail) Zs = r2 LG LF C1 Xs Zs
  | [], _, _ => by simp [cancelPseudoLeading, r2]
  | _ :: _, [], h => by simp at h
  | X :: Xs, Z :: Zs, h => by
    have ih := cancel_r2 LG LF C1 Xs Zs (by simpa using h)
    cases Zs with
    | nil =>
      cases Xs with
      | nil => simp [cancelPseudoLeading, r2]
      | cons _ _ => simp at h
    | cons Z' Zs' =>
      simp only [List.tail_cons] at ih ⊢
      simp only [cancelPseudoLeading, r2, List.headD_cons]
      rw [← ih]

theorem exactDivide_map (D : Int) (hD : D ≠ 0) : ∀ Qs : List Int,
    exactDividePolynomial D (Qs.map (fun q => q * D)) = some Qs
  | [] => rfl
  | q :: Qs => by
    simp only [List.map_cons, exactDividePolynomial]
    rw [exactDivide_map D hD Qs]
    simp [hD, Int.mul_emod_left, Int.mul_ediv_cancel _ hD]

theorem trim_cons (c : Int) (cs : List Int) (h : c ≠ 0) : trimLeading (c :: cs) = c :: cs := by
  cases c using Int.rec with
  | ofNat n => cases n with
    | zero => exact absurd rfl h
    | succ k => rfl
  | negSucc k => rfl

theorem cancel_length (a b : Int) : ∀ xs ys : List Int,
    (cancelPseudoLeading a b xs ys).length = xs.length
  | [], _ => by simp [cancelPseudoLeading]
  | x :: xs, [] => by simp [cancelPseudoLeading, cancel_length a b xs []]
  | x :: xs, y :: ys => by simp [cancelPseudoLeading, cancel_length a b xs ys]

theorem scale_one : ∀ l : List Int, scalePolynomial 1 l = l
  | [] => rfl
  | c :: cs => by simp [scalePolynomial, scale_one cs]

/-! ## The pseudo-remainder without `c₁ ≠ 0` -/

theorem cancel_zero (LG : Int) : ∀ R Zs : List Int, cancelPseudoLeading LG 0 R Zs = scalePolynomial LG R
  | [], _ => by cases ‹List Int› <;> rfl
  | r :: R, [] => by simp [cancelPseudoLeading, scalePolynomial, cancel_zero LG R []]
  | r :: R, z :: Zs => by simp [cancelPseudoLeading, scalePolynomial, cancel_zero LG R Zs]

theorem scale_length (c : Int) : ∀ l : List Int, (scalePolynomial c l).length = l.length
  | [] => rfl
  | _ :: l => by simp [scalePolynomial, scale_length c l]

theorem trimLeading_zero (cs : List Int) : trimLeading (0 :: cs) = trimLeading cs := rfl

theorem prem_eq' (lf f1 lg z0 : Int) (xs zs : List Int)
    (hlf : lf ≠ 0) (hlg : lg ≠ 0) (hlen : xs.length = zs.length + 1)
    (hr2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).headD 0 ≠ 0) :
    pseudoRemainder (lf :: f1 :: xs) (lg :: z0 :: zs)
      = some (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)) := by
  by_cases hc1 : lg * f1 - lf * z0 = 0
  · -- `c₁ = 0`: the first stage leaves a polynomial one shorter, scaled once by `lg`
    have hR2 : cancelPseudoLeading lg (lg * f1 - lf * z0) (cancelPseudoLeading lg lf xs zs) (z0 :: zs)
        = r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) :=
      cancel_r2 lg lf _ xs (z0 :: zs) (by simpa using hlen)
    rw [hc1, cancel_zero] at hR2
    rw [hc1] at hr2 ⊢
    rw [← hR2] at hr2 ⊢
    generalize hR : cancelPseudoLeading lg lf xs zs = R at hR2 hr2 ⊢
    have hRl : R.length = zs.length + 1 := by rw [← hR, cancel_length]; exact hlen
    obtain ⟨r0, rt, rfl⟩ : ∃ r0 rt, R = r0 :: rt := by
      cases R with
      | nil => simp at hRl
      | cons r0 rt => exact ⟨r0, rt, rfl⟩
    simp only [scalePolynomial, List.headD_cons] at hr2
    have hr0 : r0 ≠ 0 := by intro h; apply hr2; rw [h]; simp
    have hR1 : cancelPseudoLeading lg lf (f1 :: xs) (z0 :: zs) = (lg * f1 - lf * z0) :: (r0 :: rt) := by
      rw [← hR]; rfl
    unfold pseudoRemainder
    simp only [trim_cons lf _ hlf, trim_cons lg _ hlg, List.isEmpty_cons, Bool.false_eq_true,
      if_false, List.length_cons]
    rw [if_neg (by omega), show xs.length + 1 + 1 - (zs.length + 1 + 1) + 1 = 2 by omega]
    rw [show xs.length + 1 + 1 + 1 = (zs.length + 3) + 1 by omega]
    simp only [pseudoRemainderGo, trim_cons lf _ hlf, List.length_cons, hR1, hc1,
      trimLeading_zero, trim_cons r0 rt hr0]
    simp only [List.length_cons] at hRl
    rw [if_neg (by omega), if_pos (by omega)]
    simp [scalePolynomial, Int.pow_one]
  · have hR1 : cancelPseudoLeading lg lf (f1 :: xs) (z0 :: zs)
        = (lg * f1 - lf * z0) :: cancelPseudoLeading lg lf xs zs := rfl
    have hR2 : cancelPseudoLeading lg (lg * f1 - lf * z0) (cancelPseudoLeading lg lf xs zs) (z0 :: zs)
        = r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) :=
      cancel_r2 lg lf _ xs (z0 :: zs) (by simpa using hlen)
    have hl2 : (r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs)).length = zs.length + 1 := by
      rw [← hR2, cancel_length, cancel_length]; exact hlen
    obtain ⟨r0, rt, hr⟩ : ∃ r0 rt, r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) = r0 :: rt := by
      cases h : r2 lg lf (lg * f1 - lf * z0) xs (z0 :: zs) with
      | nil => rw [h] at hl2; simp at hl2
      | cons r0 rt => exact ⟨r0, rt, rfl⟩
    rw [hr] at hr2 hl2 hR2 ⊢
    simp only [List.headD_cons] at hr2
    unfold pseudoRemainder
    simp only [trim_cons lf _ hlf, trim_cons lg _ hlg, List.isEmpty_cons, Bool.false_eq_true,
      if_false, List.length_cons]
    rw [if_neg (by omega), show xs.length + 1 + 1 - (zs.length + 1 + 1) + 1 = 2 by omega]
    rw [show xs.length + 1 + 1 + 1 = (zs.length + 3) + 1 by omega]
    simp only [pseudoRemainderGo, trim_cons lf _ hlf, List.length_cons, hR1, trim_cons _ _ hc1,
      cancel_length, hR2, trim_cons _ _ hr2]
    simp [hlen, scale_one]
    simp only [List.length_cons] at hl2
    rw [if_neg (by omega), if_pos (by omega)]

/-! ## Coefficient lists of chain functions -/

/-- High-to-low coefficients `P n, …, P 0`. -/
def toL (P : Nat → Int) : Nat → List Int
  | 0 => [P 0]
  | n + 1 => P (n + 1) :: toL P n

theorem toL_length (P : Nat → Int) : ∀ n, (toL P n).length = n + 1
  | 0 => rfl
  | n + 1 => by simp [toL, toL_length P n]

theorem toL_cons (P : Nat → Int) : ∀ n, toL P n = P n :: (toL P n).tail
  | 0 => rfl
  | _ + 1 => rfl

theorem toL_head (P : Nat → Int) (n : Nat) : (toL P n).headD 0 = P n := by
  rw [toL_cons]; rfl

theorem toL_congr (P Q : Nat → Int) : ∀ n, (∀ e, e ≤ n → P e = Q e) → toL P n = toL Q n
  | 0, h => by simp [toL, h 0 (Nat.le_refl 0)]
  | n + 1, h => by
    simp only [toL]
    rw [h (n + 1) (Nat.le_refl _), toL_congr P Q n (fun e he => h e (by omega))]

theorem toL_map (P : Nat → Int) (c : Int) : ∀ n,
    (toL P n).map (fun q => q * c) = toL (fun e => P e * c) n
  | 0 => rfl
  | n + 1 => by simp [toL, toL_map P c n]

theorem r2_toL (LG LF C1 : Int) (X Z : Nat → Int) : ∀ n,
    r2 LG LF C1 (toL X n) (toL Z n)
      = toL (fun e => LG * (LG * X e - LF * (if 1 ≤ e then Z (e - 1) else 0)) - C1 * Z e) n
  | 0 => by simp [toL, r2]
  | n + 1 => by
    simp only [toL, r2]
    rw [r2_toL LG LF C1 X Z n, toL_head]
    simp

/-- One pseudo-remainder of chain functions: `A` of degree `d + 1`, `B` of degree `d`. -/
theorem prem_toL (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d) (ha : A (d + 1) ≠ 0) (hb : B d ≠ 0)
    (hp : premF A B d (d - 1) ≠ 0) :
    pseudoRemainder (toL A (d + 1)) (toL B d) = some (toL (premF A B d) (d - 1)) := by
  obtain ⟨d0, rfl⟩ : ∃ d0, d = d0 + 1 := ⟨d - 1, by omega⟩
  have eA : toL A (d0 + 1 + 1) = A (d0 + 1 + 1) :: A (d0 + 1) :: toL A d0 := rfl
  have eB : toL B (d0 + 1) = B (d0 + 1) :: B d0 :: (toL B d0).tail := by
    show B (d0 + 1) :: toL B d0 = _; exact congrArg _ (toL_cons B d0)
  have hr2 : r2 (B (d0 + 1)) (A (d0 + 1 + 1)) (B (d0 + 1) * A (d0 + 1) - A (d0 + 1 + 1) * B d0)
      (toL A d0) (B d0 :: (toL B d0).tail) = toL (premF A B (d0 + 1)) d0 := by
    rw [← toL_cons B d0, r2_toL]
    apply toL_congr; intro e he
    simp only [premF, if_pos (show e < d0 + 1 by omega), Nat.add_sub_cancel]
    by_cases h1 : 1 ≤ e
    · simp only [h1, ↓reduceIte]; grind
    · simp only [h1, ↓reduceIte]; grind
  rw [eA, eB, prem_eq' _ _ _ _ _ _ ha hb (by rw [toL_length, List.length_tail, toL_length]; omega) (by
    rw [hr2, toL_head]; simpa using hp), hr2]
  simp

/-! ## The whole chain is the specification's normal PRS -/

theorem chain_first (f g : Nat → Int) (m : Nat) : (chainP f g m 1).2 = premF f g (m - 1) := by
  funext e; simp [chainP, nextC]

theorem chain_succ (f g : Nat → Int) (m k : Nat) :
    chainP f g m (k + 1) = ((chainP f g m k).2,
      nextC (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) (k == 0)) := rfl

/-- One step of `normalResultantGo` on chain functions: `premF A B d = s · C` with `s = 1` on the
initial step and `s = lc(A)²` after it. -/
theorem go_step (fuel : Nat) (initial : Bool) (A B C : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : A (d + 1) ≠ 0) (hB : B d ≠ 0) (hC : C (d - 1) ≠ 0)
    (hP : ∀ e, premF A B d e = (if initial then 1 else A (d + 1) * A (d + 1)) * C e) :
    normalResultantGo (fuel + 1) initial (toL A (d + 1)) (toL B d) =
      if d = 1 then some (C 0) else normalResultantGo fuel false (toL B d) (toL C (d - 1)) := by
  have hAA : A (d + 1) * A (d + 1) ≠ 0 := Int.mul_ne_zero hA hA
  have hp : premF A B d (d - 1) ≠ 0 := by
    rw [hP]; cases initial
    · exact Int.mul_ne_zero hAA hC
    · simpa using hC
  have hdiv : (if initial then some (toL (premF A B d) (d - 1))
      else exactDividePolynomial ((toL A (d + 1)).headD 0 ^ 2) (toL (premF A B d) (d - 1)))
        = some (toL C (d - 1)) := by
    cases initial
    · simp only [Bool.false_eq_true, ↓reduceIte, toL_head]
      have e1 : toL (premF A B d) (d - 1) = (toL C (d - 1)).map (fun q => q * A (d + 1) ^ 2) := by
        rw [toL_map]; apply toL_congr; intro e _
        rw [hP, sq_eq]; simp only [Bool.false_eq_true, ↓reduceIte]; exact Int.mul_comm _ _
      rw [e1, exactDivide_map _ (by rw [sq_eq]; exact hAA)]
    · simp only [↓reduceIte]
      congr 1; apply toL_congr; intro e _; rw [hP]; simp
  rw [normalResultantGo.eq_def]
  simp only
  rw [prem_toL A B d hd hA hB hp]
  simp only
  rw [hdiv]
  simp only
  obtain ⟨d1, rfl⟩ : ∃ d1, d = d1 + 1 := ⟨d - 1, by omega⟩
  cases d1 with
  | zero =>
    rw [show (0 + 1 - 1 : Nat) = 0 from rfl] at hC ⊢
    have e0 : toL C 0 = [C 0] := rfl
    rw [e0, trim_cons _ _ hC]
    rfl
  | succ d2 =>
    simp only [show d2 + 1 + 1 - 1 = d2 + 1 by omega] at hC ⊢
    have eC : toL C (d2 + 1) = C (d2 + 1) :: C d2 :: (toL C d2).tail := by
      show C (d2 + 1) :: toL C d2 = _; exact congrArg _ (toL_cons C d2)
    rw [eC, trim_cons _ _ hC]
    simp only [List.length_cons, List.length_tail, toL_length]
    rw [if_pos (by simp), if_neg (by omega)]

theorem normalGo_chain (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (hf0 : f m ≠ 0)
    (hL : ∀ k', k' ≤ m - 1 → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ r k fuel, k + r + 2 = m → r + 1 ≤ fuel →
      normalResultantGo fuel (k == 0) (toL (chainP f g m k).1 (m - k)) (toL (chainP f g m k).2 (m - k - 1))
        = some ((chainP f g m (m - 1)).2 0) := by
  intro r
  induction r with
  | zero => ?_
  | succ r ih => ?_
  all_goals
    intro k fuel hkr hfuel
    obtain ⟨fuel', rfl⟩ : ∃ fuel', fuel = fuel' + 1 := ⟨fuel - 1, by omega⟩
    have hm1 : m - k = (m - k - 1) + 1 := by omega
    have hA : (chainP f g m k).1 (m - k - 1 + 1) ≠ 0 := by
      cases k with
      | zero => rw [← hm1]; simpa [chainP] using hf0
      | succ k0 =>
        rw [chainP_fst_succ, show m - (k0 + 1) - 1 + 1 = m - (k0 + 1) by omega]
        exact hL k0 (by omega)
    have hB : (chainP f g m k).2 (m - k - 1) ≠ 0 := by
      rw [show m - k - 1 = m - (k + 1) by omega]; exact hL k (by omega)
    have hC : (chainP f g m (k + 1)).2 (m - k - 1 - 1) ≠ 0 := by
      rw [show m - k - 1 - 1 = m - (k + 1 + 1) by omega]; exact hL (k + 1) (by omega)
    have hP : ∀ e, premF (chainP f g m k).1 (chainP f g m k).2 (m - k - 1) e =
        (if (k == 0) then 1 else (chainP f g m k).1 (m - k - 1 + 1) * (chainP f g m k).1 (m - k - 1 + 1)) *
          (chainP f g m (k + 1)).2 e := by
      intro e
      cases k with
      | zero =>
        simp only [beq_self_eq_true, ↓reduceIte, Int.one_mul]
        rw [chain_first]; simp [chainP]
      | succ k0 =>
        simp only [Nat.add_one_ne_zero, beq_iff_eq, ↓reduceIte]
        rw [show m - (k0 + 1) - 1 = m - (k0 + 1 + 1) by omega]
        exact chain_exact f g m hm hf hg (k0 + 1) (by omega) (by omega) (fun k' hk' => hL k' (by omega)) e
    have e1 : toL (chainP f g m k).1 (m - k) = toL (chainP f g m k).1 (m - k - 1 + 1) := congrArg _ hm1
    rw [e1, go_step fuel' (k == 0) _ _ _ (m - k - 1) (by omega) hA hB hC hP]
  · rw [if_pos (by omega)]
    rw [show m - 1 = k + 1 by omega]
  · rw [if_neg (by omega)]
    have := ih (k + 1) fuel' (by omega) (by omega)
    rw [chainP_fst_succ, show m - (k + 1) = m - k - 1 by omega] at this
    simpa using this

/-- The specification's normal resultant of the chain's first two polynomials. -/
theorem normalResultant_chain (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (hf0 : f m ≠ 0)
    (hL : ∀ k', k' ≤ m - 1 → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    normalResultant (toL f m) (toL g (m - 1)) = some ((chainP f g m (m - 1)).2 0) := by
  have hg0 : g (m - 1) ≠ 0 := by simpa [chainP] using hL 0 (by omega)
  have h := normalGo_chain f g m hm hf hg hf0 hL (m - 2) 0 (m + 1) (by omega) (by omega)
  simp only [chainP, beq_self_eq_true, Nat.sub_zero] at h
  unfold normalResultant
  have t1 : trimLeading (toL f m) = toL f m := by rw [toL_cons f m, trim_cons _ _ hf0]
  have t2 : trimLeading (toL g (m - 1)) = toL g (m - 1) := by rw [toL_cons g (m - 1), trim_cons _ _ hg0]
  have hne : (toL g (m - 1)).isEmpty = false := by rw [toL_cons]; rfl
  simp only [t1, t2, hne, toL_length, Bool.not_false, Bool.and_true]
  rw [if_pos (by simp; omega), show m - 1 + 1 + 1 = m + 1 by omega]
  exact h

end V9
