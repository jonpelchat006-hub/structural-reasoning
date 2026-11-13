/-!
# Determinants over `Int`, from scratch (core Lean only)

Matrices are functions `Nat → Nat → Int`; `det n M` uses rows and columns `< n`.
The determinant is defined by Laplace expansion along column 0.
-/

namespace V9

/-- The `i`-th row index of the minor that drops row `r`. -/
def skip (r i : Nat) : Nat := if i < r then i else i + 1

/-- Drop row `r` and column `0`. -/
def minor (M : Nat → Nat → Int) (r : Nat) : Nat → Nat → Int :=
  fun i j => M (skip r i) (j + 1)

def sumTo : Nat → (Nat → Int) → Int
  | 0, _ => 0
  | n + 1, f => sumTo n f + f n

def sgn (r : Nat) : Int := if r % 2 = 0 then 1 else -1

def det : Nat → (Nat → Nat → Int) → Int
  | 0, _ => 1
  | n + 1, M => sumTo (n + 1) (fun r => sgn r * M r 0 * det n (minor M r))

/-! ## Finite sums -/

theorem sumTo_congr : ∀ (n : Nat) (f g : Nat → Int), (∀ r, r < n → f r = g r) →
    sumTo n f = sumTo n g
  | 0, _, _, _ => rfl
  | n + 1, f, g, h => by
    simp only [sumTo]
    rw [sumTo_congr n f g (fun r hr => h r (by omega)), h n (by omega)]

theorem sumTo_add : ∀ (n : Nat) (f g : Nat → Int),
    sumTo n (fun r => f r + g r) = sumTo n f + sumTo n g
  | 0, _, _ => by simp [sumTo]
  | n + 1, f, g => by
    simp only [sumTo]; rw [sumTo_add n f g]; omega

theorem sumTo_mul : ∀ (n : Nat) (c : Int) (f : Nat → Int),
    sumTo n (fun r => c * f r) = c * sumTo n f
  | 0, _, _ => by simp [sumTo]
  | n + 1, c, f => by
    simp only [sumTo]; rw [sumTo_mul n c f, Int.mul_add]

theorem sumTo_zero : ∀ (n : Nat) (f : Nat → Int), (∀ r, r < n → f r = 0) → sumTo n f = 0
  | 0, _, _ => rfl
  | n + 1, f, h => by
    simp only [sumTo]; rw [sumTo_zero n f (fun r hr => h r (by omega)), h n (by omega)]; rfl

theorem sumTo_single : ∀ (n p : Nat) (f : Nat → Int), p < n →
    (∀ r, r < n → r ≠ p → f r = 0) → sumTo n f = f p
  | 0, _, _, hp, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, p, f, hp, h => by
    simp only [sumTo]
    by_cases hpn : p = n
    · subst hpn
      rw [sumTo_zero p f (fun r hr => h r (by omega) (by omega))]; omega
    · rw [sumTo_single n p f (by omega) (fun r hr hrp => h r (by omega) hrp),
        h n (by omega) (fun e => hpn e.symm)]; omega

theorem sumTo_pair : ∀ (n p q : Nat) (f : Nat → Int), p < n → q < n → p ≠ q →
    (∀ r, r < n → r ≠ p → r ≠ q → f r = 0) → sumTo n f = f p + f q
  | 0, _, _, _, hp, _, _, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, p, q, f, hp, hq, hpq, h => by
    simp only [sumTo]
    by_cases hpn : p = n
    · subst hpn
      rw [sumTo_single p q f (by omega) (fun r hr hrq => h r (by omega) (by omega) hrq)]; omega
    · by_cases hqn : q = n
      · subst hqn
        rw [sumTo_single q p f (by omega) (fun r hr hrp => h r (by omega) hrp (by omega))]
      · rw [sumTo_pair n p q f (by omega) (by omega) hpq
          (fun r hr h1 h2 => h r (by omega) h1 h2), h n (by omega) (fun e => hpn e.symm)
          (fun e => hqn e.symm)]; omega

/-! ## Signs and the skip map -/

theorem sgn_succ (r : Nat) : sgn (r + 1) = -sgn r := by
  unfold sgn; split <;> split <;> omega

theorem sgn_mul_self (r : Nat) : sgn r * sgn r = 1 := by
  unfold sgn; split <;> rfl

theorem skip_lt (r i n : Nat) (_hr : r < n + 1) (hi : i < n) : skip r i < n + 1 := by
  unfold skip; split <;> omega

theorem skip_ne (r i : Nat) : skip r i ≠ r := by
  unfold skip; split <;> omega

/-! ## Congruence -/

theorem det_congr : ∀ (n : Nat) (M M' : Nat → Nat → Int),
    (∀ i j, i < n → j < n → M i j = M' i j) → det n M = det n M'
  | 0, _, _, _ => rfl
  | n + 1, M, M', h => by
    simp only [det]
    apply sumTo_congr
    intro r hr
    rw [h r 0 hr (by omega), det_congr n (minor M r) (minor M' r) (fun i j hi hj => by
      simp only [minor]; exact h _ _ (skip_lt r i n hr hi) (by omega))]

/-- Expansion when column 0 has a single nonzero entry, in row `p`. -/
theorem det_single (n p : Nat) (M : Nat → Nat → Int) (hp : p < n + 1)
    (h : ∀ r, r < n + 1 → r ≠ p → M r 0 = 0) :
    det (n + 1) M = sgn p * M p 0 * det n (minor M p) := by
  simp only [det]
  exact sumTo_single (n + 1) p _ hp (fun r hr hrp => by rw [h r hr hrp]; simp)

/-! ## Row updates -/

def setRow (M : Nat → Nat → Int) (p : Nat) (v : Nat → Int) : Nat → Nat → Int :=
  fun i j => if i = p then v j else M i j

/-- Position of row `p` inside the minor that drops row `r ≠ p`. -/
def posIn (r p : Nat) : Nat := if p < r then p else p - 1

theorem skip_eq_iff (r p i : Nat) (hrp : r ≠ p) : skip r i = p ↔ i = posIn r p := by
  unfold skip posIn; split <;> split <;> omega

theorem minor_setRow_self (M : Nat → Nat → Int) (p : Nat) (v : Nat → Int) :
    minor (setRow M p v) p = minor M p := by
  funext i j; simp only [minor, setRow, if_neg (skip_ne p i)]

theorem minor_setRow_other (M : Nat → Nat → Int) (p r : Nat) (v : Nat → Int) (hrp : r ≠ p) :
    minor (setRow M p v) r = setRow (minor M r) (posIn r p) (fun j => v (j + 1)) := by
  funext i j
  simp only [minor, setRow]
  by_cases h : skip r i = p
  · rw [if_pos h, if_pos ((skip_eq_iff r p i hrp).1 h)]
  · rw [if_neg h, if_neg (fun e => h ((skip_eq_iff r p i hrp).2 e))]

theorem posIn_lt (r p n : Nat) (hrp : r ≠ p) (hp : p < n + 1) (hr : r < n + 1) :
    posIn r p < n := by
  unfold posIn; split <;> omega

theorem det_linear : ∀ (n : Nat) (M : Nat → Nat → Int) (p : Nat) (a b : Int) (u w : Nat → Int),
    p < n →
    det n (setRow M p (fun j => a * u j + b * w j)) =
      a * det n (setRow M p u) + b * det n (setRow M p w)
  | 0, _, _, _, _, _, _, hp => absurd hp (Nat.not_lt_zero _)
  | n + 1, M, p, a, b, u, w, hp => by
    simp only [det]
    rw [← sumTo_mul, ← sumTo_mul, ← sumTo_add]
    apply sumTo_congr
    intro r hr
    by_cases hrp : r = p
    · subst hrp
      simp only [minor_setRow_self, setRow]
      generalize det n (minor M r) = D
      grind
    · simp only [setRow, if_neg hrp]
      rw [minor_setRow_other M p r _ hrp, minor_setRow_other M p r _ hrp,
        minor_setRow_other M p r _ hrp]
      rw [det_linear n (minor M r) (posIn r p) a b (fun j => u (j + 1)) (fun j => w (j + 1))
        (posIn_lt r p n hrp hp hr)]
      generalize det n (setRow (minor M r) (posIn r p) fun j => u (j + 1)) = X
      generalize det n (setRow (minor M r) (posIn r p) fun j => w (j + 1)) = Y
      grind

theorem setRow_self (M : Nat → Nat → Int) (p : Nat) : setRow M p (M p) = M := by
  funext i j; simp only [setRow]; split <;> simp_all

/-! ## Equal rows -/

theorem minor_adj (M : Nat → Nat → Int) (p : Nat) (h : ∀ j, M p j = M (p + 1) j) :
    minor M p = minor M (p + 1) := by
  funext i j
  simp only [minor, skip]
  by_cases h1 : i < p
  · rw [if_pos h1, if_pos (by omega)]
  · by_cases h2 : i = p
    · subst h2; rw [if_neg (by omega), if_pos (by omega)]; exact (h (j + 1)).symm
    · rw [if_neg h1, if_neg (by omega)]

theorem det_adj_eq : ∀ (n : Nat) (M : Nat → Nat → Int) (p : Nat), p + 1 < n →
    (∀ j, M p j = M (p + 1) j) → det n M = 0
  | 0, _, _, hp, _ => absurd hp (Nat.not_lt_zero _)
  | n + 1, M, p, hp, h => by
    simp only [det]
    rw [sumTo_pair (n + 1) p (p + 1) _ (by omega) hp (by omega)]
    · rw [minor_adj M p h, h 0, sgn_succ]
      generalize det n (minor M (p + 1)) = D
      grind
    · intro r hr h1 h2
      have hz : det n (minor M r) = 0 := by
        by_cases hrp : r < p
        · apply det_adj_eq n (minor M r) (p - 1) (by omega)
          intro j
          simp only [minor, skip]
          rw [if_neg (by omega), if_neg (by omega), show p - 1 + 1 = p by omega]
          exact h (j + 1)
        · apply det_adj_eq n (minor M r) p (by omega)
          intro j
          simp only [minor, skip]
          rw [if_pos (by omega), if_pos (by omega)]
          exact h (j + 1)
      rw [hz]; simp

def swapRows (M : Nat → Nat → Int) (p q : Nat) : Nat → Nat → Int :=
  fun i j => if i = p then M q j else if i = q then M p j else M i j

theorem det_swap_adj (n : Nat) (M : Nat → Nat → Int) (p : Nat) (hp : p + 1 < n) :
    det n (swapRows M p (p + 1)) = -det n M := by
  -- N x y : row p := x, row p+1 := y
  let N : (Nat → Int) → (Nat → Int) → Nat → Nat → Int :=
    fun x y => setRow (setRow M (p + 1) y) p x
  have hN : ∀ x y, det n (N x y) = det n (setRow (setRow M p x) (p + 1) y) := by
    intro x y; congr 1; funext i j; simp only [N, setRow]
    by_cases h1 : i = p
    · subst h1; simp
    · simp [h1]
  -- linearity in row p (outer) and row p+1
  have linP : ∀ x x' y, det n (N (fun j => x j + x' j) y) = det n (N x y) + det n (N x' y) := by
    intro x x' y
    have := det_linear n (setRow M (p + 1) y) p 1 1 x x' (by omega)
    simp only [Int.one_mul] at this; exact this
  have linQ : ∀ x y y', det n (N x (fun j => y j + y' j)) = det n (N x y) + det n (N x y') := by
    intro x y y'
    rw [hN, hN, hN]
    have := det_linear n (setRow M p x) (p + 1) 1 1 y y' hp
    simp only [Int.one_mul] at this; exact this
  have zero : ∀ x, det n (N x x) = 0 := by
    intro x
    apply det_adj_eq n (N x x) p hp
    intro j; simp only [N, setRow]; simp
  let u := M p
  let w := M (p + 1)
  have h0 := zero (fun j => u j + w j)
  rw [linP, linQ, linQ, zero u, zero w] at h0
  have hM : N u w = M := by
    funext i j; simp only [N, setRow, u, w]
    by_cases h1 : i = p
    · simp [h1]
    · by_cases h2 : i = p + 1
      · simp [h2]
      · simp [h1, h2]
  have hS : N w u = swapRows M p (p + 1) := by
    funext i j; simp only [N, setRow, swapRows, u, w]
  rw [hM, hS] at h0
  omega

theorem det_eq_rows_aux : ∀ (k n : Nat) (M : Nat → Nat → Int) (p : Nat), p + k + 1 < n →
    (∀ j, M p j = M (p + k + 1) j) → det n M = 0
  | 0, n, M, p, hq, h => det_adj_eq n M p hq h
  | k + 1, n, M, p, hq, h => by
    have hsw := det_swap_adj n M (p + k + 1) hq
    have hz : det n (swapRows M (p + k + 1) (p + k + 1 + 1)) = 0 := by
      apply det_eq_rows_aux k n _ p (by omega)
      intro j
      show (if p = p + k + 1 then M (p + k + 1 + 1) j else if p = p + k + 1 + 1 then M (p + k + 1) j
          else M p j) = (if p + k + 1 = p + k + 1 then M (p + k + 1 + 1) j
          else if p + k + 1 = p + k + 1 + 1 then M (p + k + 1) j else M (p + k + 1) j)
      rw [if_neg (by omega), if_neg (by omega), if_pos rfl,
        show p + k + 1 + 1 = p + (k + 1) + 1 by omega]
      exact h j
    omega

theorem det_eq_rows (n : Nat) (M : Nat → Nat → Int) (p q : Nat) (hp : p < n) (hq : q < n)
    (hpq : p ≠ q) (h : ∀ j, M p j = M q j) : det n M = 0 := by
  by_cases hlt : p < q
  · have := det_eq_rows_aux (q - p - 1) n M p (by omega)
      (by rw [show p + (q - p - 1) + 1 = q by omega]; exact h)
    exact this
  · have := det_eq_rows_aux (p - q - 1) n M q (by omega)
      (by rw [show q + (p - q - 1) + 1 = p by omega]; exact fun j => (h j).symm)
    exact this

/-- Scaling row `p` by `s` and adding multiples of two other rows multiplies the
determinant by `s`. -/
theorem det_rowop (n : Nat) (M : Nat → Nat → Int) (p q1 q2 : Nat) (s c1 c2 : Int)
    (hp : p < n) (h1 : q1 < n) (h2 : q2 < n) (hp1 : p ≠ q1) (hp2 : p ≠ q2) :
    det n (setRow M p (fun j => s * M p j + (c1 * M q1 j + c2 * M q2 j))) = s * det n M := by
  have e1 := det_linear n M p s 1 (M p) (fun j => c1 * M q1 j + c2 * M q2 j) hp
  simp only [Int.one_mul] at e1
  rw [e1, setRow_self]
  have e2 := det_linear n M p c1 c2 (M q1) (M q2) hp
  rw [e2]
  have z1 : det n (setRow M p (M q1)) = 0 :=
    det_eq_rows n _ p q1 hp h1 hp1 (fun j => by simp [setRow, Ne.symm hp1])
  have z2 : det n (setRow M p (M q2)) = 0 :=
    det_eq_rows n _ p q2 hp h2 hp2 (fun j => by simp [setRow, Ne.symm hp2])
  rw [z1, z2]; simp

/-- Applying `det_rowop` to a contiguous block of rows `[a0, a0 + m)`, each combined with
two rows outside the block. -/
def blockOp (M : Nat → Nat → Int) (a0 m : Nat) (s : Int) (c1 c2 : Int) (b1 b2 : Nat → Nat) :
    Nat → Nat → Int :=
  fun i j => if a0 ≤ i ∧ i < a0 + m then s * M i j + (c1 * M (b1 i) j + c2 * M (b2 i) j)
    else M i j

theorem det_blockOp (n : Nat) (M : Nat → Nat → Int) (a0 : Nat) (s c1 c2 : Int)
    (b1 b2 : Nat → Nat) :
    ∀ m, a0 + m ≤ n →
    (∀ i, a0 ≤ i → i < a0 + m → b1 i < n ∧ b2 i < n ∧
      ¬(a0 ≤ b1 i ∧ b1 i < a0 + m) ∧ ¬(a0 ≤ b2 i ∧ b2 i < a0 + m)) →
    det n (blockOp M a0 m s c1 c2 b1 b2) = s ^ m * det n M
  | 0, _, _ => by
    have : blockOp M a0 0 s c1 c2 b1 b2 = M := by
      funext i j; simp only [blockOp]; rw [if_neg (by omega)]
    rw [this]; simp
  | m + 1, hm, hb => by
    have ih := det_blockOp n M a0 s c1 c2 b1 b2 m (by omega) (fun i h1 h2 => by
      obtain ⟨x1, x2, x3, x4⟩ := hb i h1 (by omega)
      exact ⟨x1, x2, fun e => x3 ⟨e.1, by omega⟩, fun e => x4 ⟨e.1, by omega⟩⟩)
    obtain ⟨y1, y2, y3, y4⟩ := hb (a0 + m) (by omega) (by omega)
    have key : blockOp M a0 (m + 1) s c1 c2 b1 b2 =
        setRow (blockOp M a0 m s c1 c2 b1 b2) (a0 + m)
          (fun j => s * blockOp M a0 m s c1 c2 b1 b2 (a0 + m) j +
            (c1 * blockOp M a0 m s c1 c2 b1 b2 (b1 (a0 + m)) j +
             c2 * blockOp M a0 m s c1 c2 b1 b2 (b2 (a0 + m)) j)) := by
      funext i j
      simp only [blockOp, setRow]
      by_cases hi : i = a0 + m
      · subst hi
        rw [if_pos (by omega), if_pos rfl, if_neg (by omega),
          if_neg (fun e => y3 ⟨e.1, by omega⟩), if_neg (fun e => y4 ⟨e.1, by omega⟩)]
      · rw [if_neg hi]
        by_cases h3 : a0 ≤ i ∧ i < a0 + m
        · rw [if_pos ⟨h3.1, by omega⟩, if_pos h3]
        · rw [if_neg (fun e => h3 ⟨e.1, by omega⟩), if_neg h3]
    rw [key, det_rowop n _ (a0 + m) (b1 (a0 + m)) (b2 (a0 + m)) s c1 c2 (by omega) y1 y2
      (fun e => y3 ⟨by omega, by omega⟩) (fun e => y4 ⟨by omega, by omega⟩), ih]
    rw [Int.pow_succ]; grind

end V9

namespace V9

/-! ## Scaling a block of rows -/

def scaleBlock (M : Nat → Nat → Int) (a0 m : Nat) (s : Int) : Nat → Nat → Int :=
  fun i j => if a0 ≤ i ∧ i < a0 + m then s * M i j else M i j

theorem det_scale_row (n : Nat) (M : Nat → Nat → Int) (p : Nat) (s : Int) (hp : p < n) :
    det n (setRow M p (fun j => s * M p j)) = s * det n M := by
  have e := det_linear n M p s 0 (M p) (M p) hp
  simp only [Int.zero_mul, Int.add_zero] at e
  rw [e, setRow_self]

theorem det_scaleBlock (n : Nat) (M : Nat → Nat → Int) (a0 : Nat) (s : Int) :
    ∀ m, a0 + m ≤ n → det n (scaleBlock M a0 m s) = s ^ m * det n M
  | 0, _ => by
    have : scaleBlock M a0 0 s = M := by
      funext i j; simp only [scaleBlock]; rw [if_neg (by omega)]
    rw [this]; simp
  | m + 1, hm => by
    have key : scaleBlock M a0 (m + 1) s =
        setRow (scaleBlock M a0 m s) (a0 + m) (fun j => s * scaleBlock M a0 m s (a0 + m) j) := by
      funext i j
      simp only [scaleBlock, setRow]
      by_cases hi : i = a0 + m
      · subst hi; rw [if_pos (by omega), if_pos rfl, if_neg (by omega)]
      · rw [if_neg hi]
        by_cases h3 : a0 ≤ i ∧ i < a0 + m
        · rw [if_pos ⟨h3.1, by omega⟩, if_pos h3]
        · rw [if_neg (fun e => h3 ⟨e.1, by omega⟩), if_neg h3]
    rw [key, det_scale_row n _ (a0 + m) s (by omega), det_scaleBlock n M a0 s m (by omega),
      Int.pow_succ]
    grind

/-! ## The size bound -/

def sumN : Nat → (Nat → Nat) → Nat
  | 0, _ => 0
  | n + 1, f => sumN n f + f n

def prodN : Nat → (Nat → Nat) → Nat
  | 0, _ => 1
  | n + 1, f => prodN n f * f n

def fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * fact n

theorem natAbs_sumTo_le : ∀ (n : Nat) (f : Nat → Int),
    (sumTo n f).natAbs ≤ sumN n (fun r => (f r).natAbs)
  | 0, _ => by simp [sumTo, sumN]
  | n + 1, f => by
    simp only [sumTo, sumN]
    exact Nat.le_trans (Int.natAbs_add_le _ _) (Nat.add_le_add_right (natAbs_sumTo_le n f) _)

theorem sumN_le : ∀ (n : Nat) (f g : Nat → Nat), (∀ r, r < n → f r ≤ g r) → sumN n f ≤ sumN n g
  | 0, _, _, _ => by simp [sumN]
  | n + 1, f, g, h => by
    simp only [sumN]
    exact Nat.add_le_add (sumN_le n f g (fun r hr => h r (by omega))) (h n (by omega))

theorem sumN_const : ∀ (n c : Nat), sumN n (fun _ => c) = n * c
  | 0, _ => by simp [sumN]
  | n + 1, c => by simp only [sumN]; rw [sumN_const n c, Nat.succ_mul]

theorem sumN_mul_right : ∀ (n : Nat) (f : Nat → Nat) (k : Nat),
    sumN n (fun r => f r * k) = sumN n f * k
  | 0, _, _ => by simp [sumN]
  | n + 1, f, k => by simp only [sumN]; rw [sumN_mul_right n f k, Nat.add_mul]

theorem prodN_skip (U : Nat → Nat) : ∀ (n r : Nat), r < n + 1 →
    U r * prodN n (fun i => U (skip r i)) = prodN (n + 1) U
  | 0, r, hr => by
    have : r = 0 := by omega
    subst this; simp [prodN]
  | n + 1, r, hr => by
    by_cases h : r = n + 1
    · subst h
      have : prodN (n + 1) (fun i => U (skip (n + 1) i)) = prodN (n + 1) U := by
        have aux : ∀ k, k ≤ n + 1 → prodN k (fun i => U (skip (n + 1) i)) = prodN k U := by
          intro k
          induction k with
          | zero => intro _; rfl
          | succ k ih =>
            intro hk
            simp only [prodN]
            rw [ih (by omega)]
            simp only [skip]; rw [if_pos (by omega)]
        exact aux (n + 1) (Nat.le_refl _)
      rw [this]; simp only [prodN]; rw [Nat.mul_comm]
    · show U r * (prodN n (fun i => U (skip r i)) * U (skip r n)) = prodN (n + 1) U * U (n + 1)
      rw [← Nat.mul_assoc, prodN_skip U n r (by omega)]
      simp only [skip]; rw [if_neg (by omega)]

theorem prodN_shift (V : Nat → Nat) : ∀ n, V 0 * prodN n (fun c => V (c + 1)) = prodN (n + 1) V
  | 0 => by simp [prodN]
  | n + 1 => by
    simp only [prodN]
    rw [← Nat.mul_assoc, prodN_shift V n]
    simp only [prodN]

theorem natAbs_sgn (r : Nat) : (sgn r).natAbs = 1 := by
  unfold sgn; split <;> rfl

/-- `|det M| · k^n ≤ n! · ∏ U · ∏ V` when every entry satisfies `|M r c| · k ≤ U r · V c`. -/
theorem det_bound : ∀ (n : Nat) (M : Nat → Nat → Int) (U V : Nat → Nat) (k : Nat),
    (∀ r c, r < n → c < n → (M r c).natAbs * k ≤ U r * V c) →
    (det n M).natAbs * k ^ n ≤ fact n * prodN n U * prodN n V
  | 0, _, _, _, _, _ => by simp [det, fact, prodN]
  | n + 1, M, U, V, k, h => by
    simp only [det]
    have step : ∀ r, r < n + 1 →
        (sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1) ≤
          fact n * prodN (n + 1) U * prodN (n + 1) V := by
      intro r hr
      have ih := det_bound n (minor M r) (fun i => U (skip r i)) (fun c => V (c + 1)) k
        (fun i c hi hc => h _ _ (skip_lt r i n hr hi) (by omega))
      have h0 := h r 0 hr (by omega)
      rw [Int.natAbs_mul, Int.natAbs_mul, natAbs_sgn, Nat.one_mul, Nat.pow_succ]
      calc (M r 0).natAbs * (det n (minor M r)).natAbs * (k ^ n * k)
          = ((M r 0).natAbs * k) * ((det n (minor M r)).natAbs * k ^ n) := by
            rw [Nat.mul_comm (k ^ n) k]; grind
        _ ≤ (U r * V 0) * (fact n * prodN n (fun i => U (skip r i)) *
              prodN n (fun c => V (c + 1))) := Nat.mul_le_mul h0 ih
        _ = fact n * (U r * prodN n (fun i => U (skip r i))) *
              (V 0 * prodN n (fun c => V (c + 1))) := by grind
        _ = fact n * prodN (n + 1) U * prodN (n + 1) V := by
            rw [prodN_skip U n r hr, prodN_shift V n]
    calc (sumTo (n + 1) fun r => sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1)
        ≤ sumN (n + 1) (fun r => (sgn r * M r 0 * det n (minor M r)).natAbs) * k ^ (n + 1) :=
          Nat.mul_le_mul_right _ (natAbs_sumTo_le _ _)
      _ = sumN (n + 1) (fun r => (sgn r * M r 0 * det n (minor M r)).natAbs * k ^ (n + 1)) :=
          (sumN_mul_right _ _ _).symm
      _ ≤ sumN (n + 1) (fun _ => fact n * prodN (n + 1) U * prodN (n + 1) V) :=
          sumN_le _ _ _ step
      _ = fact (n + 1) * prodN (n + 1) U * prodN (n + 1) V := by
          rw [sumN_const]; simp only [fact]; grind

end V9
