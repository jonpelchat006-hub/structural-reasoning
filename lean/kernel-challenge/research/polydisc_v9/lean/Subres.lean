import V9.Det

/-!
# Subresultants and the normal PRS

Polynomials are degree-indexed coefficient functions `Nat → Int`.
-/

namespace V9

/-- Coefficient of `x^t · P` at degree `e`. -/
def shc (P : Nat → Int) (t e : Nat) : Int := if t ≤ e then P (e - t) else 0

/-- Degree read by column `c` of the `j`-th subresultant matrix (last column: degree `i`). -/
def colDeg (p q j i c : Nat) : Nat := if c + 1 < p + q - 2 * j then p + q - j - 1 - c else i

/-- The `j`-th subresultant matrix of `X` (formal degree `p`) and `Y` (formal degree `q`).
With `conv = true` the `q - j` rows `x^k X` come first, otherwise the `p - j` rows `x^k Y`. -/
def sxM (X Y : Nat → Int) (p q j i : Nat) (conv : Bool) : Nat → Nat → Int := fun r c =>
  if conv then
    (if r < q - j then shc X (q - j - 1 - r) (colDeg p q j i c)
     else shc Y (p - j - 1 - (r - (q - j))) (colDeg p q j i c))
  else
    (if r < p - j then shc Y (p - j - 1 - r) (colDeg p q j i c)
     else shc X (q - j - 1 - (r - (p - j))) (colDeg p q j i c))

/-- Coefficient of `x^i` in the `j`-th subresultant. -/
def sres (X Y : Nat → Int) (p q j i : Nat) (conv : Bool) : Int :=
  det (p + q - 2 * j) (sxM X Y p q j i conv)

/-- Pseudo-remainder of `A` (formal degree `d+1`) by `B` (formal degree `d`):
`B_d² A − (A_{d+1} B_d x + γ) B`, which has formal degree `d − 1`. -/
def premF (A B : Nat → Int) (d : Nat) : Nat → Int := fun e =>
  if e < d then
    B d * B d * A e - A (d + 1) * B d * (if 1 ≤ e then B (e - 1) else 0)
      - (B d * A d - A (d + 1) * B (d - 1)) * B e
  else 0

theorem premF_id (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : ∀ e, d + 1 < e → A e = 0) (hB : ∀ e, d < e → B e = 0) (e : Nat) :
    B d * B d * A e + (-(A (d + 1) * B d)) * (if 1 ≤ e then B (e - 1) else 0)
      + (-(B d * A d - A (d + 1) * B (d - 1))) * B e = premF A B d e := by
  unfold premF
  by_cases h1 : e < d
  · rw [if_pos h1]; grind
  · rw [if_neg h1]
    by_cases h2 : e = d
    · subst h2; rw [if_pos hd]; grind
    · by_cases h3 : e = d + 1
      · subst h3
        rw [if_pos (by omega), show d + 1 - 1 = d by omega, hB (d + 1) (by omega)]; grind
      · rw [hA e (by omega), hB e (by omega), if_pos (by omega), hB (e - 1) (by omega)]; grind

theorem shc_comb (A B : Nat → Int) (d : Nat) (hd : 1 ≤ d)
    (hA : ∀ e, d + 1 < e → A e = 0) (hB : ∀ e, d < e → B e = 0) (t e : Nat) :
    B d * B d * shc A t e + ((-(A (d + 1) * B d)) * shc B (t + 1) e
      + (-(B d * A d - A (d + 1) * B (d - 1))) * shc B t e) = shc (premF A B d) t e := by
  unfold shc
  by_cases h : t ≤ e
  · rw [if_pos h, if_pos h, if_pos h, ← premF_id A B d hd hA hB (e - t)]
    by_cases h' : t + 1 ≤ e
    · rw [if_pos h', if_pos (by omega), show e - t - 1 = e - (t + 1) by omega]; grind
    · rw [if_neg h', if_neg (by omega)]; grind
  · rw [if_neg h, if_neg h, if_neg (by omega), if_neg h]; grind

theorem sq_eq (b : Int) : b ^ 2 = b * b := by
  rw [Int.pow_succ, Int.pow_succ, Int.pow_zero, Int.one_mul]

theorem pow_two_mul (b : Int) (m : Nat) : b ^ (2 * m) = (b * b) ^ m := by
  rw [Int.pow_mul, sq_eq]

theorem skip_of_lt {r i : Nat} (h : i < r) : skip r i = i := by unfold skip; rw [if_pos h]
theorem skip_of_ge {r i : Nat} (h : r ≤ i) : skip r i = i + 1 := by
  unfold skip; rw [if_neg (by omega)]

/-! ## Lemma A, rows of `A` first -/

theorem lemmaA_true (A B : Nat → Int) (j t i : Nat) (_hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i true =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i false := by
  -- notation
  have hN : j + 1 + t + 1 + (j + 1 + t) - 2 * j = (2 * t + 1) + 1 + 1 := by omega
  have hN' : j + 1 + t + (j + t) - 2 * j = 2 * t + 1 := by omega
  unfold sres
  rw [hN, hN']
  generalize hd : j + 1 + t = d at *
  have hd1 : 1 ≤ d := by omega
  let b := B d
  let a := A (d + 1)
  let g := B d * A d - A (d + 1) * B (d - 1)
  let M0 := sxM A B (d + 1) d j i true
  let M1 := blockOp M0 0 (t + 1) (b * b) (-(a * b)) (-g) (fun r => t + 1 + r) (fun r => t + 1 + r + 1)
  have e1 : det (2 * t + 1 + 1 + 1) M1 = (b * b) ^ (t + 1) * det (2 * t + 1 + 1 + 1) M0 :=
    det_blockOp _ M0 0 _ _ _ _ _ (t + 1) (by omega) (fun r h1 h2 => ⟨by omega, by omega, by omega, by omega⟩)
  -- the matrix after the row operations
  let M3 : Nat → Nat → Int := fun r c =>
    if r < t + 1 then shc (premF A B d) (t + 1 - 1 - r) (colDeg (d + 1) d j i c) else M0 r c
  have e3 : det (2 * t + 1 + 1 + 1) M1 = det (2 * t + 1 + 1 + 1) M3 := by
    apply det_congr
    intro r c hr hc
    simp only [M1, M3, blockOp]
    by_cases hrt : r < t + 1
    · rw [if_pos ⟨Nat.zero_le _, by omega⟩, if_pos hrt]
      simp only [M0, sxM, if_true]
      rw [if_pos (by omega), if_neg (by omega), if_neg (by omega)]
      rw [show d + 1 - j - 1 - (t + 1 + r - (d - j)) = t + 1 - 1 - r + 1 by omega,
        show d + 1 - j - 1 - (t + 1 + r + 1 - (d - j)) = t + 1 - 1 - r by omega,
        show d - j - 1 - r = t + 1 - 1 - r by omega]
      exact shc_comb A B d hd1 hA hB _ _
    · rw [if_neg (by omega), if_neg hrt]
  -- first expansion, at row t+1
  have colz : colDeg (d + 1) d j i 0 = 2 * d - j := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have colo : colDeg (d + 1) d j i 1 = 2 * d - j - 1 := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have hp0 : ∀ e, d ≤ e → premF A B d e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  have e4 : det (2 * t + 1 + 1 + 1) M3 = sgn (t + 1) * b * det (2 * t + 1 + 1) (minor M3 (t + 1)) := by
    rw [det_single (2 * t + 1 + 1) (t + 1) M3 (by omega)]
    · congr 2
      simp only [M3, M0, sxM, if_true]
      rw [if_neg (by omega), if_neg (by omega), colz]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      simp only [M3]
      by_cases h1 : r < t + 1
      · rw [if_pos h1, colz]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, if_true]
        rw [if_neg (by omega), colz]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  -- second expansion, again at row t+1 of the minor
  have e5 : det (2 * t + 1 + 1) (minor M3 (t + 1)) =
      sgn (t + 1) * b * det (2 * t + 1) (minor (minor M3 (t + 1)) (t + 1)) := by
    rw [det_single (2 * t + 1) (t + 1) _ (by omega)]
    · congr 2
      show M3 (skip (t + 1) (t + 1)) (0 + 1) = b
      rw [skip_of_ge (Nat.le_refl _)]
      simp only [M3, M0, sxM, if_true]
      rw [if_neg (by omega), if_neg (by omega), colo]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      show M3 (skip (t + 1) r) (0 + 1) = 0
      by_cases h1 : r < t + 1
      · rw [skip_of_lt h1]; simp only [M3]
        rw [if_pos h1, colo]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [skip_of_ge (by omega)]; simp only [M3]
        rw [if_neg (by omega)]; simp only [M0, sxM, if_true]
        rw [if_neg (by omega), colo]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  -- what is left is the next subresultant matrix, rows of `premF` first
  have e6 : det (2 * t + 1) (minor (minor M3 (t + 1)) (t + 1)) =
      det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i false) := by
    apply det_congr
    intro r c hr hc
    have cd : colDeg (d + 1) d j i (c + 1 + 1) = colDeg d (j + t) j i c := by
      unfold colDeg
      by_cases hc' : c + 1 < 2 * t + 1
      · rw [if_pos (by omega), if_pos (by omega)]; omega
      · rw [if_neg (by omega), if_neg (by omega)]
    show M3 (skip (t + 1) (skip (t + 1) r)) (c + 1 + 1) = _
    simp only [sxM, Bool.false_eq_true, ↓reduceIte]
    by_cases h1 : r < t + 1
    · rw [skip_of_lt h1, skip_of_lt h1]; simp only [M3]
      rw [if_pos h1, if_pos (by omega), cd]
      congr 1; omega
    · rw [skip_of_ge (show t + 1 ≤ r by omega), skip_of_ge (show t + 1 ≤ r + 1 by omega)]
      simp only [M3]
      rw [if_neg (by omega), if_neg (by omega)]
      simp only [M0, sxM, if_true]
      rw [if_neg (by omega), cd]
      congr 1; omega
  rw [pow_two_mul, sq_eq, ← e1, e3, e4, e5, e6]
  have := sgn_mul_self (t + 1)
  generalize sgn (t + 1) = s at *
  generalize det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i false) = D
  grind

/-! ## Lemma A, rows of `B` first -/

theorem lemmaA_false (A B : Nat → Int) (j t i : Nat) (_hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i false =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i true := by
  have hN : j + 1 + t + 1 + (j + 1 + t) - 2 * j = (2 * t + 1) + 1 + 1 := by omega
  have hN' : j + 1 + t + (j + t) - 2 * j = 2 * t + 1 := by omega
  unfold sres
  rw [hN, hN']
  generalize hd : j + 1 + t = d at *
  have hd1 : 1 ≤ d := by omega
  let b := B d
  let a := A (d + 1)
  let g := B d * A d - A (d + 1) * B (d - 1)
  let M0 := sxM A B (d + 1) d j i false
  let M1 := blockOp M0 (t + 2) (t + 1) (b * b) (-(a * b)) (-g) (fun r => r - (t + 2))
    (fun r => r - (t + 2) + 1)
  have e1 : det (2 * t + 1 + 1 + 1) M1 = (b * b) ^ (t + 1) * det (2 * t + 1 + 1 + 1) M0 :=
    det_blockOp _ M0 (t + 2) _ _ _ _ _ (t + 1) (by omega)
      (fun r h1 h2 => ⟨by omega, by omega, by omega, by omega⟩)
  let M3 : Nat → Nat → Int := fun r c =>
    if t + 2 ≤ r then shc (premF A B d) (t - (r - (t + 2))) (colDeg (d + 1) d j i c) else M0 r c
  have e3 : det (2 * t + 1 + 1 + 1) M1 = det (2 * t + 1 + 1 + 1) M3 := by
    apply det_congr
    intro r c hr hc
    simp only [M1, M3, blockOp]
    by_cases hrt : t + 2 ≤ r
    · rw [if_pos ⟨hrt, by omega⟩, if_pos hrt]
      simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), if_pos (by omega)]
      rw [show d + 1 - j - 1 - (r - (t + 2)) = t - (r - (t + 2)) + 1 by omega,
        show d + 1 - j - 1 - (r - (t + 2) + 1) = t - (r - (t + 2)) by omega,
        show d - j - 1 - (r - (d + 1 - j)) = t - (r - (t + 2)) by omega]
      exact shc_comb A B d hd1 hA hB _ _
    · rw [if_neg (fun h => hrt h.1), if_neg hrt]
  have colz : colDeg (d + 1) d j i 0 = 2 * d - j := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have colo : colDeg (d + 1) d j i 1 = 2 * d - j - 1 := by
    unfold colDeg; rw [if_pos (by omega)]; omega
  have hp0 : ∀ e, d ≤ e → premF A B d e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  have e4 : det (2 * t + 1 + 1 + 1) M3 = sgn 0 * b * det (2 * t + 1 + 1) (minor M3 0) := by
    rw [det_single (2 * t + 1 + 1) 0 M3 (by omega)]
    · congr 2
      simp only [M3, M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), colz]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      simp only [M3]
      by_cases h1 : t + 2 ≤ r
      · rw [if_pos h1, colz]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
        rw [if_pos (by omega), colz]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  have e5 : det (2 * t + 1 + 1) (minor M3 0) =
      sgn 0 * b * det (2 * t + 1) (minor (minor M3 0) 0) := by
    rw [det_single (2 * t + 1) 0 _ (by omega)]
    · congr 2
      show M3 (skip 0 0) (0 + 1) = b
      rw [skip_of_ge (Nat.le_refl _)]
      simp only [M3, M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_neg (by omega), if_pos (by omega), colo]
      unfold shc; rw [if_pos (by omega)]
      congr 1; omega
    · intro r hr hrt
      show M3 (skip 0 r) (0 + 1) = 0
      rw [skip_of_ge (Nat.zero_le _)]
      simp only [M3]
      by_cases h1 : t + 2 ≤ r + 1
      · rw [if_pos h1, colo]; unfold shc; rw [if_pos (by omega)]; exact hp0 _ (by omega)
      · rw [if_neg h1]; simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
        rw [if_pos (by omega), colo]; unfold shc; rw [if_pos (by omega)]; exact hB _ (by omega)
  have e6 : det (2 * t + 1) (minor (minor M3 0) 0) =
      det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i true) := by
    apply det_congr
    intro r c hr hc
    have cd : colDeg (d + 1) d j i (c + 1 + 1) = colDeg d (j + t) j i c := by
      unfold colDeg
      by_cases hc' : c + 1 < 2 * t + 1
      · rw [if_pos (by omega), if_pos (by omega)]; omega
      · rw [if_neg (by omega), if_neg (by omega)]
    show M3 (skip 0 (skip 0 r)) (c + 1 + 1) = _
    rw [skip_of_ge (show 0 ≤ r by omega), skip_of_ge (show 0 ≤ r + 1 by omega)]
    simp only [sxM, ↓reduceIte]
    simp only [M3]
    by_cases h1 : r < t
    · rw [if_neg (by omega), if_pos (by omega)]
      simp only [M0, sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_pos (by omega), cd]
      congr 1; omega
    · rw [if_pos (by omega), if_neg (by omega), cd]
      congr 1; omega
  rw [pow_two_mul, sq_eq, ← e1, e3, e4, e5, e6]
  simp only [sgn, Nat.zero_mod, ↓reduceIte]
  generalize det (2 * t + 1) (sxM B (premF A B d) d (j + t) j i true) = D
  grind

/-! ## The top subresultant and scaling -/

theorem sres_top (X Y : Nat → Int) (j i : Nat) (c : Bool) :
    sres X Y (j + 1) j j i c = Y i := by
  unfold sres
  rw [show j + 1 + j - 2 * j = 0 + 1 by omega]
  rw [det_single 0 0 _ (by omega) (fun r hr hr0 => by omega)]
  have h1 : sxM X Y (j + 1) j j i c 0 0 = Y i := by
    have hc : colDeg (j + 1) j j i 0 = i := by
      unfold colDeg; rw [if_neg (by omega)]
    cases c
    · simp only [sxM, Bool.false_eq_true, ↓reduceIte]
      rw [if_pos (by omega), hc]; unfold shc; rw [if_pos (by omega)]; congr 1; omega
    · simp only [sxM, ↓reduceIte]
      rw [if_neg (by omega), hc]; unfold shc; rw [if_pos (by omega)]; congr 1; omega
  rw [h1]; simp [det, sgn]

theorem lemmaA (A B : Nat → Int) (j t i : Nat) (c : Bool) (hi : i ≤ j)
    (hA : ∀ e, j + 1 + t + 1 < e → A e = 0) (hB : ∀ e, j + 1 + t < e → B e = 0) :
    B (j + 1 + t) ^ (2 * (t + 1)) * sres A B (j + 1 + t + 1) (j + 1 + t) j i c =
      B (j + 1 + t) ^ 2 * sres B (premF A B (j + 1 + t)) (j + 1 + t) (j + t) j i (!c) := by
  cases c
  · exact lemmaA_false A B j t i hi hA hB
  · exact lemmaA_true A B j t i hi hA hB

/-- The coefficient of `x^i` in the subresultant just below `B`'s degree is the
pseudo-remainder's coefficient. -/
theorem sres_prem (A B : Nat → Int) (j i : Nat) (c : Bool) (hi : i ≤ j) (hb : B (j + 1) ≠ 0)
    (hA : ∀ e, j + 1 + 1 < e → A e = 0) (hB : ∀ e, j + 1 < e → B e = 0) :
    sres A B (j + 1 + 1) (j + 1) j i c = premF A B (j + 1) i := by
  have h := lemmaA A B j 0 i c hi (by simpa using hA) (by simpa using hB)
  simp only [Nat.add_zero] at h
  rw [sres_top, show 2 * (0 + 1) = 2 by rfl] at h
  have hb2 : B (j + 1) ^ 2 ≠ 0 := by
    rw [sq_eq]; exact Int.mul_ne_zero hb hb
  exact Int.eq_of_mul_eq_mul_left hb2 h

def scaleP (s : Int) (Y : Nat → Int) : Nat → Int := fun e => s * Y e

theorem shc_scale (s : Int) (Y : Nat → Int) (t e : Nat) : shc (scaleP s Y) t e = s * shc Y t e := by
  unfold shc scaleP; split <;> simp

theorem sres_scale (X Y : Nat → Int) (s : Int) (p q j i : Nat) (c : Bool) (hq : j ≤ q) (hp : q ≤ p) :
    sres X (scaleP s Y) p q j i c = s ^ (p - j) * sres X Y p q j i c := by
  unfold sres
  cases c
  · rw [← det_scaleBlock (p + q - 2 * j) (sxM X Y p q j i false) 0 s (p - j) (by omega)]
    apply det_congr
    intro r col hr hc
    simp only [sxM, scaleBlock, Bool.false_eq_true, ↓reduceIte]
    by_cases h : r < p - j
    · rw [if_pos h, if_pos ⟨Nat.zero_le _, by omega⟩, if_pos h, shc_scale]
    · rw [if_neg h, if_neg (by omega), if_neg h]
  · rw [← det_scaleBlock (p + q - 2 * j) (sxM X Y p q j i true) (q - j) s (p - j) (by omega)]
    apply det_congr
    intro r col hr hc
    simp only [sxM, scaleBlock, ↓reduceIte]
    by_cases h : r < q - j
    · rw [if_pos h, if_neg (by omega), if_pos h]
    · rw [if_neg h, if_pos ⟨by omega, by omega⟩, if_neg h, shc_scale]

/-! ## The normal PRS chain -/

def nextC (A B : Nat → Int) (d : Nat) (first : Bool) : Nat → Int :=
  fun e => if first then premF A B d e else premF A B d e / (A (d + 1) * A (d + 1))

/-- `chainP f g m k = (F_k, F_{k+1})`; `F_{k+1}` has formal degree `m − (k+1)`. -/
def chainP (f g : Nat → Int) (m : Nat) : Nat → (Nat → Int) × (Nat → Int)
  | 0 => (f, g)
  | k + 1 => ((chainP f g m k).2,
      nextC (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) (k == 0))

def conv (k : Nat) : Bool := k % 2 == 0

theorem conv_succ (k : Nat) : conv (k + 1) = !conv k := by
  unfold conv
  by_cases h : k % 2 = 0
  · have : (k + 1) % 2 = 1 := by omega
    simp [h, this]
  · have h1 : k % 2 = 1 := by omega
    have : (k + 1) % 2 = 0 := by omega
    simp [h1, this]

/-- The chain invariant for the pair `(F_k, F_{k+1})`, with `d = m − (k+1)`. -/
structure Inv (f g : Nat → Int) (m k : Nat) : Prop where
  degA : ∀ e, m - (k + 1) + 1 < e → (chainP f g m k).1 e = 0
  degB : ∀ e, m - (k + 1) < e → (chainP f g m k).2 e = 0
  rel : ∀ j i, j + 1 ≤ m - (k + 1) → i ≤ j →
    sres (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1) + 1) (m - (k + 1)) j i (conv k) =
      (if k = 0 then 1 else ((chainP f g m k).1 (m - (k + 1) + 1)) ^ (2 * (m - (k + 1) - j))) *
        sres f g m (m - 1) j i true
  val : 1 ≤ k → ∀ i, i ≤ m - (k + 1) →
    (chainP f g m k).2 i = sres f g m (m - 1) (m - (k + 1)) i true

theorem inv_zero (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) : Inv f g m 0 where
  degA := by intro e he; exact hf e (by omega)
  degB := by intro e he; exact hg e (by omega)
  rel := by
    intro j i hj hi
    simp only [chainP, ↓reduceIte, Int.one_mul, conv, Nat.zero_mod]
    rw [show m - (0 + 1) + 1 = m by omega, show m - (0 + 1) = m - 1 by omega]
    rfl
  val := by intro h; omega

/-- One step of the chain: exactness and the value of the new polynomial. -/
theorem step_exact (f g : Nat → Int) (m k : Nat) (hI : Inv f g m k) (hd : 1 ≤ m - (k + 1))
    (hb : (chainP f g m k).2 (m - (k + 1)) ≠ 0)
    (ha : 1 ≤ k → (chainP f g m k).1 (m - (k + 1) + 1) ≠ 0) :
    ∀ i, i ≤ m - (k + 1) - 1 →
      premF (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) i =
        (if k = 0 then 1 else ((chainP f g m k).1 (m - (k + 1) + 1)) ^ 2) *
          sres f g m (m - 1) (m - (k + 1) - 1) i true := by
  intro i hi
  obtain ⟨j, hj⟩ : ∃ j, m - (k + 1) = j + 1 := ⟨m - (k + 1) - 1, by omega⟩
  rw [hj] at hi hb ha ⊢
  have hA := hI.degA; have hB := hI.degB; have hR := hI.rel
  rw [hj] at hA hB hR
  have e1 := sres_prem (chainP f g m k).1 (chainP f g m k).2 j i (conv k) (by omega) hb hA hB
  rw [← e1, hR j i (by omega) (by omega)]
  congr 1
  split
  · rfl
  · congr 1; omega

theorem inv_succ (f g : Nat → Int) (m k : Nat) (hI : Inv f g m k) (hd : 1 ≤ m - (k + 1))
    (hb : (chainP f g m k).2 (m - (k + 1)) ≠ 0)
    (ha : 1 ≤ k → (chainP f g m k).1 (m - (k + 1) + 1) ≠ 0) : Inv f g m (k + 1) := by
  obtain ⟨j0, hj⟩ : ∃ j0, m - (k + 1) = j0 + 1 := ⟨m - (k + 1) - 1, by omega⟩
  have hj' : m - (k + 1 + 1) = j0 := by omega
  let A := (chainP f g m k).1
  let B := (chainP f g m k).2
  let a := A (j0 + 1 + 1)
  have hP1 : (chainP f g m (k + 1)).1 = B := rfl
  have hP2 : (chainP f g m (k + 1)).2 = nextC A B (j0 + 1) (k == 0) := by
    show nextC A B (m - (k + 1)) (k == 0) = _; rw [hj]
  have hEx := step_exact f g m k hI hd hb ha
  rw [hj] at hEx hb ha
  have hpz : ∀ e, j0 + 1 ≤ e → premF A B (j0 + 1) e = 0 := by
    intro e he; unfold premF; rw [if_neg (by omega)]
  -- the raw remainder is the scaled next polynomial
  have hscale : premF A B (j0 + 1) =
      scaleP (if k = 0 then 1 else a ^ 2) (nextC A B (j0 + 1) (k == 0)) := by
    funext e
    simp only [scaleP, nextC]
    by_cases hk : k = 0
    · simp [hk]
    · have hk' : (k == 0) = false := by simp [hk]
      rw [hk', if_neg hk]; simp only [Bool.false_eq_true, ↓reduceIte]
      have ha0 : a ≠ 0 := ha (by omega)
      have hsq : a ^ 2 = a * a := sq_eq a
      by_cases he : e ≤ j0
      · have := hEx e (by omega)
        rw [if_neg hk] at this
        show premF A B (j0 + 1) e = a ^ 2 * (premF A B (j0 + 1) e / (A (j0 + 1 + 1) * A (j0 + 1 + 1)))
        rw [this, ← hsq, Int.mul_ediv_cancel_left _ (by rw [hsq]; exact Int.mul_ne_zero ha0 ha0)]
      · rw [hpz e (by omega)]; simp
  constructor
  · intro e he
    rw [hP1]; exact hI.degB e (by omega)
  · intro e he
    rw [hP2]; simp only [nextC]
    rw [hpz e (by omega)]; split <;> simp
  · intro j i hjj hi
    rw [hP1, hP2, hj']
    rw [if_neg (Nat.succ_ne_zero k)]
    have hjt : ∃ t, j0 + 1 = j + 1 + t + 1 := ⟨j0 - j - 1, by omega⟩
    obtain ⟨t, ht⟩ := hjt
    -- Lemma A on (A, B), then undo the scaling
    have hAd : ∀ e, j + 1 + (t + 1) + 1 < e → A e = 0 := by
      intro e he; exact hI.degA e (by omega)
    have hBd : ∀ e, j + 1 + (t + 1) < e → B e = 0 := by
      intro e he; exact hI.degB e (by omega)
    have LA := lemmaA A B j (t + 1) i (conv k) hi hAd hBd
    have hR := hI.rel j i (by omega) hi
    rw [show m - (k + 1) + 1 = j + 1 + (t + 1) + 1 by omega,
      show m - (k + 1) = j + 1 + (t + 1) by omega] at hR
    rw [hR, show j + 1 + (t + 1) = j0 + 1 by omega, hscale,
      sres_scale B _ _ _ _ _ _ _ (by omega) (by omega), show j + (t + 1) = j0 by omega] at LA
    rw [conv_succ, show j0 - j = t + 1 by omega]
    have hx : (if k = 0 then 1 else A (j0 + 1 + 1) ^ (2 * (j0 + 1 - j))) =
        (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) := by
      split
      · exact Int.one_pow.symm
      · rw [Int.pow_mul]
    rw [hx, show 2 * (t + 1 + 1) = 2 + 2 * (t + 1) by omega, Int.pow_add] at LA
    have hc0 : (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) ≠ 0 := by
      apply Int.pow_ne_zero
      split
      · decide
      · rw [sq_eq]; exact Int.mul_ne_zero (ha (by omega)) (ha (by omega))
    have hb2 : B (j0 + 1) ^ 2 ≠ 0 := by rw [sq_eq]; exact Int.mul_ne_zero hb hb
    generalize (if k = 0 then 1 else a ^ 2) ^ (j0 + 1 - j) = C at LA hc0
    generalize sres B (nextC A B (j0 + 1) (k == 0)) (j0 + 1) j0 j i (!conv k) = T at LA ⊢
    generalize sres f g m (m - 1) j i true = S at LA ⊢
    generalize B (j0 + 1) ^ 2 = b2 at LA hb2
    generalize B (j0 + 1) ^ (2 * (t + 1)) = bt at LA ⊢
    have h1 : b2 * (C * T) = b2 * (C * (bt * S)) := by rw [← LA]; grind
    have h2 := Int.eq_of_mul_eq_mul_left hb2 h1
    exact Int.eq_of_mul_eq_mul_left hc0 h2
  · intro _ i hi
    rw [hP2, hj']
    simp only [nextC]
    have := hEx i (by omega)
    by_cases hk : k = 0
    · subst hk
      simp only [↓reduceIte] at this ⊢
      rw [this, Int.one_mul]; congr 1
    · have hk' : (k == 0) = false := by simp [hk]
      rw [hk']; simp only [Bool.false_eq_true, ↓reduceIte]
      rw [if_neg hk] at this
      have ha0 : a ≠ 0 := ha (by omega)
      rw [this, sq_eq, show j0 + 1 - 1 = j0 by omega]
      exact Int.mul_ediv_cancel_left _ (Int.mul_ne_zero ha0 ha0)

theorem chainP_fst_succ (f g : Nat → Int) (m k : Nat) :
    (chainP f g m (k + 1)).1 = (chainP f g m k).2 := rfl

/-- The invariant holds as long as the leading coefficients met so far are nonzero. -/
theorem inv_upto (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) :
    ∀ k, k + 1 ≤ m → (∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) → Inv f g m k
  | 0, _, _ => inv_zero f g m hm hf hg
  | k + 1, hk, hL => by
    have ih := inv_upto f g m hm hf hg k (by omega) (fun k' hk' => hL k' (by omega))
    apply inv_succ f g m k ih (by omega) (hL k (by omega))
    intro hk1
    obtain ⟨k0, rfl⟩ : ∃ k0, k = k0 + 1 := ⟨k - 1, by omega⟩
    rw [chainP_fst_succ, show m - (k0 + 1 + 1) + 1 = m - (k0 + 1) by omega]
    exact hL k0 (by omega)

/-- Every polynomial of the chain from `F_2` on is a subresultant of `(f, g)`. -/
theorem chain_val (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 1 ≤ m)
    (hk1 : 1 ≤ k) (hL : ∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ i, i ≤ m - (k + 1) → (chainP f g m k).2 i = sres f g m (m - 1) (m - (k + 1)) i true :=
  (inv_upto f g m hm hf hg k hk hL).val hk1

theorem chain_deg (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 1 ≤ m)
    (hL : ∀ k', k' < k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ e, m - (k + 1) < e → (chainP f g m k).2 e = 0 :=
  (inv_upto f g m hm hf hg k hk hL).degB

/-- Exactness of the division at every step after the first. -/
theorem chain_exact (f g : Nat → Int) (m : Nat) (hm : 2 ≤ m)
    (hf : ∀ e, m < e → f e = 0) (hg : ∀ e, m - 1 < e → g e = 0) (k : Nat) (hk : k + 2 ≤ m)
    (hk1 : 1 ≤ k) (hL : ∀ k', k' ≤ k → (chainP f g m k').2 (m - (k' + 1)) ≠ 0) :
    ∀ e, premF (chainP f g m k).1 (chainP f g m k).2 (m - (k + 1)) e =
      ((chainP f g m k).1 (m - (k + 1) + 1) * (chainP f g m k).1 (m - (k + 1) + 1)) *
        (chainP f g m (k + 1)).2 e := by
  have hI := inv_upto f g m hm hf hg k (by omega) (fun k' hk' => hL k' (by omega))
  have hI1 := inv_upto f g m hm hf hg (k + 1) (by omega) (fun k' hk' => hL k' (by omega))
  obtain ⟨k0, rfl⟩ : ∃ k0, k = k0 + 1 := ⟨k - 1, by omega⟩
  have ha : (chainP f g m (k0 + 1)).1 (m - (k0 + 1 + 1) + 1) ≠ 0 := by
    rw [chainP_fst_succ, show m - (k0 + 1 + 1) + 1 = m - (k0 + 1) by omega]
    exact hL k0 (by omega)
  have hEx := step_exact f g m (k0 + 1) hI (by omega) (hL (k0 + 1) (by omega)) (fun _ => ha)
  intro e
  by_cases he : e ≤ m - (k0 + 1 + 1) - 1
  · rw [hEx e he, if_neg (by omega), sq_eq, hI1.val (by omega) e (by omega),
      show m - (k0 + 1 + 1 + 1) = m - (k0 + 1 + 1) - 1 by omega]
  · have h1 : premF (chainP f g m (k0 + 1)).1 (chainP f g m (k0 + 1)).2 (m - (k0 + 1 + 1)) e = 0 := by
      unfold premF; rw [if_neg (by omega)]
    rw [h1, hI1.degB e (by omega)]; simp

end V9
