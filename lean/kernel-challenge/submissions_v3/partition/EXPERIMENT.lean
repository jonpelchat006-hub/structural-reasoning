import Spec

/-!
# Partitions by the Durfee-square series, one big division per square

`p(n) = Σ_{d ≥ 0} x^{d²} / ((1-x)…(1-x^d))²` (every partition splits along its Durfee square).
Evaluated in Horner form from the inside out,
`T_D = 1`, `T_{d-1} = 1 + x^{2d-1} · T_d / (1 - x^d)²`, `p(n) = [x^n] T_0`, with `D ≥ ⌊√n⌋`.

The power series live in one natural number, `n + 1` digits in base `B = 2^(n+4)`, in reverse
order (degree `j` at position `n - j`). In this layout one level is a single kernel division:
`Y ↦ B^n + (Y · B) / (B^d - 1)²` (the division by `(1 - x^d)²` together with the shift by
`x^{2d-1}`, which drops the digits beyond degree `n`); the floor is exact because every coefficient
stays below `2^(j+3)`. So `p(n)` costs about `√n` big-number steps (`D = ⌊(n+25)/10⌋`).

Proof outline:
* series operations: shift `sh`, division by `1 - x^s` (the spec's own sum, `specSum`), and the
  operators `Dop k = 1/((1-x)…(1-x^k))`; they are linear and commute;
* the Durfee identity, via `S d m = Σ_{i ≤ m} x^{i d} / (x;x)_i`: a two-line recurrence gives the
  telescoping `D_d S(d+1,d) = D_{d-1} S(d,d-1) + x^{d²}/(x;x)_d²`, and `S` with `m → ∞` gives
  `1/(x;x)_∞` (the spec's `partAux n n`);
* the Horner loop computes that sum;
* digit bounds and the exactness of the floor divisions in base `B`.
-/

namespace Submission

/-! ## Implementation -/

/-- `k` Horner levels: `Y ↦ B^n + Y·B / q²`, `q = B^d - 1 ↦ B^(d-1) - 1`. -/
def loop (B BN : Nat) : Nat → Nat → Nat → Nat :=
  fun k => Nat.rec (motive := fun _ => Nat → Nat → Nat) (fun Y _ => Y)
    (fun _ ih Y q => ih (Nat.add BN (Nat.div (Nat.mul Y B) (Nat.mul q q))) (Nat.div q B)) k

def go (N B D : Nat) : Nat :=
  Nat.mod (loop B (Nat.pow B N) D (Nat.pow B N) (Nat.sub (Nat.pow B D) (nat_lit 1))) B

def implV2 (N : Nat) : Nat :=
  go N (Nat.pow (nat_lit 2) (Nat.add N (nat_lit 4))) (Nat.div (Nat.add N (nat_lit 25)) (nat_lit 10))

/-! ## Power series as coefficient functions -/

/-- Multiplication by `x^t`. -/
def sh (c : Nat → Nat) (t m : Nat) : Nat := if t ≤ m then c (m - t) else 0

def one (m : Nat) : Nat := if m = 0 then 1 else 0

theorem foldl_add_start (l : List Nat) (a : Nat) :
    l.foldl (· + ·) a = a + l.foldl (· + ·) 0 := by
  induction l generalizing a with
  | nil => simp
  | cons x l ih =>
    simp only [List.foldl_cons]
    rw [ih (a + x), ih (0 + x)]
    omega

/-- The spec's inner sum `Σ_{j ≤ m/s} c (m - j·s)`: division by `1 - x^s`. -/
def specSum (c : Nat → Nat) (s m : Nat) : Nat :=
  ((List.range (m / s + 1)).map (fun j => c (m - j * s))).foldl (· + ·) 0

/-- Division by `1 - x^s`. -/
def dv (s : Nat) (c : Nat → Nat) : Nat → Nat := specSum c s

theorem specSum_rec (c : Nat → Nat) {s : Nat} (hs : 0 < s) (m : Nat) :
    specSum c s m = c m + sh (specSum c s) s m := by
  unfold specSum
  rw [List.range_succ_eq_map, List.map_cons, List.foldl_cons, foldl_add_start, List.map_map]
  simp only [Nat.zero_mul, Nat.sub_zero, Nat.zero_add]
  unfold sh
  by_cases hm : s ≤ m
  · rw [if_pos hm, Nat.div_eq_sub_div hs hm]
    congr 2
    apply List.map_congr_left
    intro j _
    simp only [Function.comp, Nat.succ_mul]
    congr 1
    omega
  · rw [if_neg hm, Nat.div_eq_of_lt (by omega)]
    simp

theorem dv_rec {s : Nat} (hs : 0 < s) (c : Nat → Nat) (m : Nat) :
    dv s c m = c m + sh (dv s c) s m := specSum_rec c hs m

/-- `dv s c` is the only solution of `g = c + x^s g`. -/
theorem dv_unique {s : Nat} (hs : 0 < s) (c g : Nat → Nat) (h : ∀ m, g m = c m + sh g s m) :
    g = dv s c := by
  funext m
  induction m using Nat.strongRecOn with
  | ind m ih =>
    rw [h m, dv_rec hs c m]
    unfold sh
    split
    · rw [ih (m - s) (by omega)]
    · rfl

theorem sh_zero (c : Nat → Nat) : sh c 0 = c := by
  funext m; simp [sh]

theorem sh_sh (c : Nat → Nat) (a b : Nat) : sh (sh c a) b = sh c (a + b) := by
  funext m
  unfold sh
  by_cases h1 : b ≤ m
  · by_cases h2 : a ≤ m - b
    · rw [if_pos h1, if_pos h2, if_pos (by omega)]; congr 1; omega
    · rw [if_pos h1, if_neg h2, if_neg (by omega)]
  · rw [if_neg h1, if_neg (by omega)]

theorem sh_add (c d : Nat → Nat) (t : Nat) :
    sh (fun m => c m + d m) t = fun m => sh c t m + sh d t m := by
  funext m; unfold sh; split <;> simp

theorem dv_add {s : Nat} (hs : 0 < s) (c d : Nat → Nat) :
    dv s (fun m => c m + d m) = fun m => dv s c m + dv s d m := by
  symm
  apply dv_unique hs
  intro m
  rw [dv_rec hs c m, dv_rec hs d m]
  unfold sh; split <;> (try simp only []) <;> omega

theorem dv_sh {s : Nat} (hs : 0 < s) (c : Nat → Nat) (t : Nat) : dv s (sh c t) = sh (dv s c) t := by
  symm
  apply dv_unique hs
  intro m
  unfold sh
  by_cases h1 : t ≤ m
  · rw [if_pos h1, if_pos h1, dv_rec hs c (m - t)]
    unfold sh
    by_cases h2 : s ≤ m - t
    · rw [if_pos h2, if_pos (by omega), if_pos (by omega), show m - t - s = m - s - t by omega]
    · rw [if_neg h2]
      by_cases h3 : s ≤ m
      · rw [if_pos h3, if_neg (by omega)]
      · rw [if_neg h3]
  · rw [if_neg h1, if_neg h1]
    by_cases h3 : s ≤ m
    · rw [if_pos h3, if_neg (by omega)]
    · rw [if_neg h3]

theorem dv_comm {a b : Nat} (ha : 0 < a) (hb : 0 < b) (c : Nat → Nat) :
    dv a (dv b c) = dv b (dv a c) := by
  apply dv_unique hb
  intro m
  have e : dv b c = fun m => c m + sh (dv b c) b m := funext (dv_rec hb c)
  conv => lhs; rw [e]
  rw [dv_add ha, dv_sh ha]

/-- `1/((1-x)(1-x²)…(1-x^k))` as an operator. -/
def Dop : Nat → (Nat → Nat) → (Nat → Nat)
  | 0, c => c
  | k + 1, c => dv (k + 1) (Dop k c)

theorem Dop_add : ∀ k (c d : Nat → Nat), Dop k (fun m => c m + d m) = fun m => Dop k c m + Dop k d m
  | 0, _, _ => rfl
  | k + 1, c, d => by
    show dv (k + 1) (Dop k _) = _
    rw [Dop_add k c d, dv_add (by omega)]
    rfl

theorem Dop_sh : ∀ k (c : Nat → Nat) (t : Nat), Dop k (sh c t) = sh (Dop k c) t
  | 0, _, _ => rfl
  | k + 1, c, t => by
    show dv (k + 1) (Dop k _) = sh (dv (k + 1) (Dop k c)) t
    rw [Dop_sh k c t, dv_sh (by omega)]

theorem Dop_dv {s : Nat} (hs : 0 < s) : ∀ k (c : Nat → Nat), Dop k (dv s c) = dv s (Dop k c)
  | 0, _ => rfl
  | k + 1, c => by
    show dv (k + 1) (Dop k _) = dv s (dv (k + 1) (Dop k c))
    rw [Dop_dv hs k c, dv_comm (by omega) hs]

theorem Dop_Dop : ∀ k l (c : Nat → Nat), Dop k (Dop l c) = Dop l (Dop k c)
  | 0, _, _ => rfl
  | k + 1, l, c => by
    show dv (k + 1) (Dop k (Dop l c)) = Dop l (dv (k + 1) (Dop k c))
    rw [Dop_Dop k l c, Dop_dv (by omega)]

/-! ## The Durfee identity -/

/-- `1/((1-x)…(1-x^i))`: partitions into parts `≤ i`. -/
def A (i : Nat) : Nat → Nat := Dop i one

theorem A_eq : ∀ k, A k = partAux k
  | 0 => by
    funext m; cases m <;> rfl
  | k + 1 => by
    show dv (k + 1) (Dop k one) = partAux (k + 1)
    funext m
    show specSum (A k) (k + 1) m = partAux (k + 1) m
    rw [A_eq k, partAux]
    rfl

theorem partAux_stab (N : Nat) : ∀ K, N ≤ K → partAux K N = partAux N N
  | 0, h => by rw [show N = 0 by omega]
  | K + 1, h => by
    rcases Nat.lt_or_ge N (K + 1) with hlt | hge
    · have e := specSum_rec (partAux K) (s := K + 1) (by omega) N
      unfold sh at e
      rw [if_neg (by omega), Nat.add_zero] at e
      have : partAux (K + 1) N = specSum (partAux K) (K + 1) N := by rw [partAux]; rfl
      rw [this, e, partAux_stab N K (by omega), Nat.add_zero]
    · rw [show K + 1 = N by omega]

/-- `S d m = Σ_{i ≤ m} x^{i d} A_i`. -/
def S (d : Nat) : Nat → (Nat → Nat)
  | 0 => one
  | m + 1 => fun j => S d m j + sh (A (m + 1)) ((m + 1) * d) j

theorem A_succ_eq (i : Nat) : A (i + 1) = fun m => A i m + sh (A (i + 1)) (i + 1) m :=
  funext (dv_rec (by omega) (A i))

theorem term_eq (i d : Nat) :
    sh (A (i + 1)) ((i + 1) * d) = fun j => sh (A (i + 1)) ((i + 1) * (d + 1)) j + sh (sh (A i) (i * d)) d j := by
  conv => lhs; rw [A_succ_eq i]
  rw [sh_add, sh_sh, sh_sh, show i + 1 + (i + 1) * d = (i + 1) * (d + 1) by
    rw [Nat.mul_succ]; omega, show i * d + d = (i + 1) * d by rw [Nat.succ_mul]]
  funext m
  exact Nat.add_comm _ _

theorem term_pt (i d j : Nat) : sh (A (i + 1)) ((i + 1) * d) j
    = sh (A (i + 1)) ((i + 1) * (d + 1)) j + sh (sh (A i) (i * d)) d j := congrFun (term_eq i d) j

theorem sh_S (d m j : Nat) :
    sh (S d (m + 1)) d j = sh (S d m) d j + sh (sh (A (m + 1)) ((m + 1) * d)) d j := by
  unfold sh
  by_cases h : d ≤ j
  · rw [if_pos h, if_pos h, if_pos h]; rfl
  · rw [if_neg h, if_neg h, if_neg h]

/-- The recurrence `S(d, m+1) = S(d+1, m+1) + x^d S(d, m)`. -/
theorem S_K (d : Nat) (j : Nat) : ∀ m, S d (m + 1) j = S (d + 1) (m + 1) j + sh (S d m) d j
  | 0 => by
    show one j + sh (A 1) (1 * d) j = (one j + sh (A 1) (1 * (d + 1)) j) + sh one d j
    rw [term_pt 0 d j, Nat.zero_mul, sh_zero]
    show one j + (sh (A 1) (1 * (d + 1)) j + sh one d j) = _
    omega
  | m + 1 => by
    show S d (m + 1) j + sh (A (m + 1 + 1)) ((m + 1 + 1) * d) j
      = (S (d + 1) (m + 1) j + sh (A (m + 1 + 1)) ((m + 1 + 1) * (d + 1)) j) + sh (S d (m + 1)) d j
    rw [S_K d j m, term_pt (m + 1) d j, sh_S]
    omega

/-- The telescoped sum `Σ_{e ≤ d} x^{e²} A_e²`. -/
def DS : Nat → (Nat → Nat)
  | 0 => one
  | d + 1 => fun j => DS d j + sh (Dop (d + 1) (A (d + 1))) ((d + 1) * (d + 1)) j

theorem telescope : ∀ d, Dop d (S (d + 1) d) = DS d
  | 0 => rfl
  | d + 1 => by
    funext j
    have hfun : (fun j => S (d + 1 + 1) (d + 1) j + sh (S (d + 1) d) (d + 1) j)
        = fun j => S (d + 1) d j + sh (A (d + 1)) ((d + 1) * (d + 1)) j := by
      funext j
      have hK := S_K (d + 1) j d
      have hS : S (d + 1) (d + 1) j = S (d + 1) d j + sh (A (d + 1)) ((d + 1) * (d + 1)) j := rfl
      omega
    have h1 := congrFun (congrArg (Dop (d + 1)) hfun) j
    rw [Dop_add, Dop_add, Dop_sh, Dop_sh] at h1
    have h2 : Dop (d + 1) (S (d + 1) d) j = Dop d (S (d + 1) d) j + sh (Dop (d + 1) (S (d + 1) d)) (d + 1) j :=
      dv_rec (by omega) _ j
    have h3 := congrFun (telescope d) j
    show Dop (d + 1) (S (d + 1 + 1) (d + 1)) j = DS d j + sh (Dop (d + 1) (A (d + 1))) ((d + 1) * (d + 1)) j
    simp only [] at h1
    omega

/-! ## `S` for `m → ∞`: the infinite product -/

theorem S_mono (d m j : Nat) (h : j < (m + 1) * d) : S d (m + 1) j = S d m j := by
  show S d m j + sh (A (m + 1)) ((m + 1) * d) j = S d m j
  unfold sh; rw [if_neg (by omega), Nat.add_zero]

theorem S_tail (d D j : Nat) (h : j < (D + 1) * d) : ∀ k, S d (D + k) j = S d D j
  | 0 => rfl
  | k + 1 => by
    have : (D + 1) * d ≤ (D + k + 1) * d := Nat.mul_le_mul_right _ (by omega)
    rw [show D + (k + 1) = D + k + 1 by omega, S_mono d (D + k) j (by omega), S_tail d D j h k]

theorem S_stab (d j : Nat) (hd : 1 ≤ d) (k : Nat) : S d (j + k) j = S d j j := by
  apply S_tail
  have : (j + 1) * 1 ≤ (j + 1) * d := Nat.mul_le_mul_left _ hd
  omega

/-- The diagonal: all `i` that can contribute to degree `j`. -/
def C (d : Nat) : Nat → Nat := fun j => S d j j

theorem C_rec (d : Nat) (hd : 1 ≤ d) (j : Nat) : C d j = C (d + 1) j + sh (C d) d j := by
  cases j with
  | zero =>
    show one 0 = one 0 + sh (C d) d 0
    unfold sh; rw [if_neg (by omega), Nat.add_zero]
  | succ m =>
    show S d (m + 1) (m + 1) = S (d + 1) (m + 1) (m + 1) + sh (C d) d (m + 1)
    rw [S_K d (m + 1) m]
    congr 1
    unfold sh C
    split
    · have := S_stab d (m + 1 - d) hd (d - 1)
      rw [show m + 1 - d + (d - 1) = m by omega] at this
      exact this
    · rfl

theorem C_eq (d : Nat) (hd : 1 ≤ d) : C d = dv d (C (d + 1)) :=
  dv_unique (by omega) _ _ (C_rec d hd)

theorem chain (D : Nat) : ∀ k, Dop D (C (D + 1)) = Dop (D + k) (C (D + k + 1))
  | 0 => rfl
  | k + 1 => by
    rw [chain D k, show D + (k + 1) = D + k + 1 by omega]
    show Dop (D + k) (C (D + k + 1)) = dv (D + k + 1) (Dop (D + k) (C (D + k + 1 + 1)))
    rw [← Dop_dv (by omega), ← C_eq (D + k + 1) (by omega)]

/-- Agreement on the degrees `≤ n`. -/
def agree (f g : Nat → Nat) (n : Nat) : Prop := ∀ j, j ≤ n → f j = g j

theorem agree_dv {s : Nat} (hs : 0 < s) {f g : Nat → Nat} {n : Nat} (h : agree f g n) :
    agree (dv s f) (dv s g) n := by
  intro j
  induction j using Nat.strongRecOn with
  | ind j ih =>
    intro hj
    rw [dv_rec hs f j, dv_rec hs g j, h j hj]
    unfold sh
    split
    · rw [ih (j - s) (by omega) (by omega)]
    · rfl

theorem agree_Dop {f g : Nat → Nat} {n : Nat} (h : agree f g n) : ∀ k, agree (Dop k f) (Dop k g) n
  | 0 => h
  | k + 1 => agree_dv (by omega) (agree_Dop h k)

theorem C_big (K N : Nat) (hK : N ≤ K) : agree (C (K + 1)) one N := by
  intro j hj
  show S (K + 1) j j = one j
  have := S_tail (K + 1) 0 j (by omega) j
  rw [Nat.zero_add] at this
  rw [this]; rfl

theorem S_agree (D N : Nat) (h : N < (D + 1) * (D + 1)) : agree (S (D + 1) D) (C (D + 1)) N := by
  intro j hj
  show S (D + 1) D j = S (D + 1) j j
  rcases Nat.le_total j D with hjD | hjD
  · have := S_stab (D + 1) j (by omega) (D - j)
    rw [show j + (D - j) = D by omega] at this
    exact this
  · have := S_tail (D + 1) D j (by omega) (j - D)
    rw [show D + (j - D) = j by omega] at this
    exact this.symm

/-- The Durfee identity at degree `N`. -/
theorem durfee (N D : Nat) (h : N < (D + 1) * (D + 1)) : DS D N = partAux N N := by
  rw [← telescope D, agree_Dop (S_agree D N h) D N (Nat.le_refl N), chain D N,
    agree_Dop (C_big (D + N) N (by omega)) (D + N) N (Nat.le_refl N)]
  show A (D + N) N = _
  rw [A_eq, partAux_stab N (D + N) (by omega)]

/-! ## The Horner form -/

/-- One Horner level: `T ↦ 1 + x^{2d-1} T / (1 - x^d)²`. -/
def stepS (d : Nat) (f : Nat → Nat) : Nat → Nat := fun j => one j + sh (dv d (dv d f)) (2 * d - 1) j

/-- Levels `k, k-1, …, 1`. -/
def U : Nat → (Nat → Nat) → (Nat → Nat)
  | 0, f => f
  | k + 1, f => U k (stepS (k + 1) f)

def W (k : Nat) (f : Nat → Nat) : Nat → Nat := sh (Dop k (Dop k f)) (k * k)

def DS' : Nat → (Nat → Nat)
  | 0 => fun _ => 0
  | k + 1 => fun j => DS' k j + W k one j

theorem W_step (k : Nat) (f : Nat → Nat) :
    W k (stepS (k + 1) f) = fun j => W k one j + W (k + 1) f j := by
  unfold W stepS
  rw [Dop_add, Dop_add, Dop_sh, Dop_sh, sh_add, sh_sh, Dop_dv (by omega), Dop_dv (by omega),
    Dop_dv (by omega), Dop_dv (by omega)]
  have e : Dop (k + 1) (Dop (k + 1) f) = dv (k + 1) (dv (k + 1) (Dop k (Dop k f))) := by
    show dv (k + 1) (Dop k (dv (k + 1) (Dop k f))) = _
    rw [Dop_dv (by omega)]
  have hsq : (k + 1) * (k + 1) = k * k + 2 * k + 1 := by
    simp only [Nat.add_mul, Nat.mul_add, Nat.mul_one, Nat.one_mul]; omega
  rw [e, show 2 * (k + 1) - 1 + k * k = (k + 1) * (k + 1) by omega]

theorem horner : ∀ k (f : Nat → Nat), U k f = fun j => DS' k j + W k f j
  | 0, f => by
    funext j
    show f j = 0 + sh f (0 * 0) j
    rw [Nat.zero_mul, sh_zero]; omega
  | k + 1, f => by
    show U k (stepS (k + 1) f) = _
    rw [horner k, W_step]
    funext j
    show DS' k j + (W k one j + W (k + 1) f j) = (DS' k j + W k one j) + W (k + 1) f j
    omega

theorem DS_eq : ∀ d, (fun j => DS' d j + W d one j) = DS d
  | 0 => by
    funext j
    show 0 + sh one (0 * 0) j = one j
    rw [Nat.zero_mul, sh_zero]; omega
  | d + 1 => by
    funext j
    have := congrFun (DS_eq d) j
    show (DS' d j + W d one j) + W (d + 1) one j = DS d j + sh (Dop (d + 1) (A (d + 1))) ((d + 1) * (d + 1)) j
    rw [this]
    rfl

theorem U_DS (D : Nat) : U D one = DS D := by
  rw [horner, DS_eq]

/-! ## Coefficient bounds -/

def Bd (c : Nat) (f : Nat → Nat) : Prop := ∀ j, f j ≤ c * 2 ^ j

theorem dv_bd {s c : Nat} (hs : 0 < s) {f : Nat → Nat} (h : Bd c f) : Bd (2 * c) (dv s f) := by
  intro j
  induction j using Nat.strongRecOn with
  | ind j ih =>
    rw [dv_rec hs f j]
    unfold sh
    split
    · have h1 := ih (j - s) (by omega)
      have h2 : 2 ^ (j - s) * 2 ≤ 2 ^ j := by
        rw [← Nat.pow_succ]; exact Nat.pow_le_pow_right (by omega) (by omega)
      have h3 : 2 * c * 2 ^ (j - s) ≤ c * 2 ^ j := by
        calc 2 * c * 2 ^ (j - s) = c * (2 ^ (j - s) * 2) := by
              rw [Nat.mul_comm 2 c, Nat.mul_assoc, Nat.mul_comm 2]
          _ ≤ c * 2 ^ j := Nat.mul_le_mul_left _ h2
      have h4 := h j
      have : 2 * c * 2 ^ j = c * 2 ^ j + c * 2 ^ j := by rw [Nat.mul_assoc, Nat.two_mul]
      omega
    · have h4 := h j
      have : c * 2 ^ j ≤ 2 * c * 2 ^ j := by
        rw [Nat.mul_assoc]; exact Nat.le_mul_of_pos_left _ (by omega)
      omega

theorem one_bd : Bd 2 one := by
  intro j; unfold one; split
  · have := Nat.one_le_two_pow (n := j); omega
  · omega

theorem sh_bd {c t : Nat} {f : Nat → Nat} (h : Bd (c * 2 ^ t) f) : Bd c (sh f t) := by
  intro j
  unfold sh
  split
  · have h1 := h (j - t)
    have : c * 2 ^ t * 2 ^ (j - t) = c * 2 ^ j := by
      rw [Nat.mul_assoc, ← Nat.pow_add, show t + (j - t) = j by omega]
    omega
  · exact Nat.zero_le _

theorem stepS_bd {d : Nat} (hd : 2 ≤ d) {f : Nat → Nat} (h : Bd 2 f) : Bd 2 (stepS d f) := by
  have hg : Bd 8 (dv d (dv d f)) := dv_bd (by omega) (dv_bd (by omega) h)
  have hg' : Bd (1 * 2 ^ (2 * d - 1)) (dv d (dv d f)) := by
    intro j
    have h1 := hg j
    have : 8 ≤ 1 * 2 ^ (2 * d - 1) := by
      rw [Nat.one_mul]
      calc 8 = 2 ^ 3 := rfl
        _ ≤ 2 ^ (2 * d - 1) := Nat.pow_le_pow_right (by omega) (by omega)
    have := Nat.mul_le_mul_right (2 ^ j) this
    omega
  have hs := sh_bd hg'
  intro j
  have h1 := hs j
  show one j + _ ≤ _
  have : one j ≤ 2 ^ j := by
    unfold one; split
    · exact Nat.one_le_two_pow
    · omega
  omega

theorem stepS1_bd {f : Nat → Nat} (h : Bd 2 f) : Bd 5 (stepS 1 f) := by
  have hg : Bd (4 * 2 ^ 1) (dv 1 (dv 1 f)) := dv_bd (by omega) (dv_bd (by omega) h)
  have hs := sh_bd hg
  intro j
  have h1 := hs j
  show one j + sh (dv 1 (dv 1 f)) 1 j ≤ _
  have : one j ≤ 2 ^ j := by
    unfold one; split
    · exact Nat.one_le_two_pow
    · omega
  omega

theorem U_bd : ∀ k (f : Nat → Nat), Bd 2 f → Bd 5 (U k f)
  | 0, f, h => fun j => by have := h j; show f j ≤ 5 * 2 ^ j; omega
  | 1, f, h => stepS1_bd h
  | k + 2, f, h => U_bd (k + 1) _ (stepS_bd (by omega) h)

/-! ## Series as base-`B` numbers (degree `j` at position `n - j`) -/

section Enc

variable (B : Nat)

def E (f : Nat → Nat) : Nat → Nat
  | 0 => f 0
  | n + 1 => E f n * B + f (n + 1)

theorem E_add (f g : Nat → Nat) : ∀ n, E B (fun j => f j + g j) n = E B f n + E B g n
  | 0 => rfl
  | n + 1 => by
    show E B (fun j => f j + g j) n * B + (f (n + 1) + g (n + 1)) = (E B f n * B + f (n + 1)) + (E B g n * B + g (n + 1))
    rw [E_add f g n, Nat.add_mul]; omega

theorem E_one : ∀ n, E B one n = B ^ n
  | 0 => rfl
  | n + 1 => by
    show E B one n * B + one (n + 1) = _
    rw [E_one n, Nat.pow_succ]; rfl

theorem E_lt {f : Nat → Nat} {n : Nat} (h : ∀ j, j ≤ n → f j < B) : E B f n < B ^ (n + 1) := by
  induction n with
  | zero => show f 0 < B ^ 1; rw [Nat.pow_one]; exact h 0 (Nat.le_refl 0)
  | succ n ih =>
    have h1 := ih (fun j hj => h j (by omega))
    have h2 := h (n + 1) (Nat.le_refl _)
    show E B f n * B + f (n + 1) < B ^ (n + 1 + 1)
    have : (E B f n + 1) * B ≤ B ^ (n + 1) * B := Nat.mul_le_mul_right _ h1
    rw [show B ^ (n + 1 + 1) = B ^ (n + 1) * B from Nat.pow_succ B (n + 1)]
    rw [Nat.add_mul, Nat.one_mul] at this
    omega

theorem E_mod {f : Nat → Nat} {n : Nat} (h : f n < B) : E B f n % B = f n := by
  cases n with
  | zero => exact Nat.mod_eq_of_lt h
  | succ n =>
    show (E B f n * B + f (n + 1)) % B = _
    rw [Nat.mul_comm, Nat.mul_add_mod, Nat.mod_eq_of_lt h]

theorem E_div_pow (hB : 0 < B) {f : Nat → Nat} {n : Nat} (h : ∀ j, j ≤ n → f j < B) :
    ∀ t, t ≤ n → E B f n / B ^ t = E B f (n - t)
  | 0, _ => by simp
  | t + 1, ht => by
    rw [Nat.pow_succ, ← Nat.div_div_eq_div_mul, E_div_pow hB h t (by omega)]
    rw [show n - t = (n - (t + 1)) + 1 by omega]
    show (E B f (n - (t + 1)) * B + f (n - (t + 1) + 1)) / B = _
    rw [Nat.mul_comm, Nat.mul_add_div hB, Nat.div_eq_of_lt (h _ (by omega)), Nat.add_zero]

theorem E_sh (g : Nat → Nat) (t : Nat) : ∀ n, E B (sh g t) n = if t ≤ n then E B g (n - t) else 0
  | 0 => by
    show sh g t 0 = _
    unfold sh
    by_cases h : t ≤ 0
    · rw [if_pos h, if_pos h, show t = 0 by omega]; rfl
    · rw [if_neg h, if_neg h]
  | n + 1 => by
    show E B (sh g t) n * B + sh g t (n + 1) = _
    rw [E_sh g t n]
    unfold sh
    by_cases h1 : t ≤ n
    · rw [if_pos h1, if_pos (by omega), if_pos (by omega), show n + 1 - t = (n - t) + 1 by omega]
      rfl
    · by_cases h2 : t = n + 1
      · subst h2
        rw [if_neg h1, if_pos (Nat.le_refl _), if_pos (Nat.le_refl _), Nat.sub_self, Nat.zero_mul,
          Nat.zero_add]
        rfl
      · rw [if_neg h1, if_neg (by omega), if_neg (by omega), Nat.zero_mul]

theorem E_shdiv (hB : 0 < B) {g : Nat → Nat} {n : Nat} (h : ∀ j, j ≤ n → g j < B) (t : Nat) :
    E B (sh g t) n = E B g n / B ^ t := by
  rw [E_sh]
  split
  · rw [E_div_pow B hB h t (by assumption)]
  · rw [Nat.div_eq_of_lt]
    exact Nat.lt_of_lt_of_le (E_lt B h) (Nat.pow_le_pow_right hB (by omega))

theorem mod_mul_add (x r k : Nat) (hB : 0 < B) (hr : r < B) :
    (x * B + r) % (B ^ k * B) = (x % B ^ k) * B + r := by
  have hk : 0 < B ^ k := Nat.pow_pos hB
  have e := Nat.div_add_mod x (B ^ k)
  have hlt : (x % B ^ k) * B + r < B ^ k * B := by
    have h1 : x % B ^ k + 1 ≤ B ^ k := Nat.mod_lt _ hk
    have : (x % B ^ k + 1) * B ≤ B ^ k * B := Nat.mul_le_mul_right _ h1
    rw [Nat.add_mul, Nat.one_mul] at this
    omega
  conv => lhs; rw [← e]
  rw [show (B ^ k * (x / B ^ k) + x % B ^ k) * B + r = (x % B ^ k * B + r) + (B ^ k * B) * (x / B ^ k) by
    rw [Nat.add_mul]; grind, Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt hlt]

/-- The low `k` digits are at most `M (B^k - 1)/(B - 1)`. -/
theorem E_low (hB : 0 < B) {f : Nat → Nat} {M : Nat} (hM : M < B) :
    ∀ k n, (∀ j, j ≤ n → f j ≤ M) → (E B f n % B ^ k) * (B - 1) ≤ M * (B ^ k - 1)
  | 0, n, _ => by rw [Nat.pow_zero, Nat.mod_one, Nat.zero_mul]; exact Nat.zero_le _
  | k + 1, 0, h => by
    have h0 := h 0 (Nat.le_refl 0)
    have hB1 : B ≤ B ^ (k + 1) := by
      calc B = B ^ 1 := (Nat.pow_one B).symm
        _ ≤ B ^ (k + 1) := Nat.pow_le_pow_right hB (by omega)
    show (f 0 % B ^ (k + 1)) * (B - 1) ≤ _
    rw [Nat.mod_eq_of_lt (by omega)]
    calc f 0 * (B - 1) ≤ M * (B - 1) := Nat.mul_le_mul_right _ h0
      _ ≤ M * (B ^ (k + 1) - 1) := Nat.mul_le_mul_left _ (by omega)
  | k + 1, n + 1, h => by
    have ih := E_low hB hM k n (fun j hj => h j (by omega))
    have hr := h (n + 1) (Nat.le_refl _)
    show ((E B f n * B + f (n + 1)) % B ^ (k + 1)) * (B - 1) ≤ _
    rw [Nat.pow_succ, mod_mul_add B _ _ _ hB (by omega)]
    have hk : 1 ≤ B ^ k := Nat.pow_pos hB
    generalize E B f n % B ^ k = x at ih ⊢
    generalize f (n + 1) = r at hr ⊢
    obtain ⟨c, hc⟩ : ∃ c, B = c + 1 := ⟨B - 1, by omega⟩
    obtain ⟨e, he⟩ : ∃ e, B ^ k = e + 1 := ⟨B ^ k - 1, by omega⟩
    rw [he, hc] at ih ⊢
    simp only [Nat.add_sub_cancel] at ih ⊢
    have h2 : r * c ≤ M * c := Nat.mul_le_mul_right _ hr
    have h3 : x * (c + 1) * c ≤ M * e * (c + 1) := by
      calc x * (c + 1) * c = x * c * (c + 1) := by grind
        _ ≤ M * e * (c + 1) := Nat.mul_le_mul_right _ ih
    have h4 : (x * (c + 1) + r) * c = x * (c + 1) * c + r * c := by grind
    have h5 : M * ((e + 1) * (c + 1) - 1) = M * e * (c + 1) + M * c := by
      rw [show (e + 1) * (c + 1) - 1 = e * (c + 1) + c by grind]; grind
    rw [h4, h5]
    omega

/-- One division by `1 - x^s` is exact in base `B`. -/
theorem E_dv (hB : 0 < B) {s : Nat} (hs : 0 < s) (f : Nat → Nat) (n : Nat)
    (h : ∀ j, j ≤ n → dv s f j < B) :
    E B f n * B ^ s = E B (dv s f) n * (B ^ s - 1) + E B (dv s f) n % B ^ s := by
  have hrec : dv s f = fun j => f j + sh (dv s f) s j := funext (dv_rec hs f)
  have hX : E B (dv s f) n = E B f n + E B (dv s f) n / B ^ s := by
    conv => lhs; rw [hrec]
    rw [E_add, E_shdiv B hB h]
  have hd := Nat.div_add_mod (E B (dv s f) n) (B ^ s)
  have hP : 1 ≤ B ^ s := Nat.pow_pos hB
  generalize E B (dv s f) n / B ^ s = Q at hX hd
  generalize E B (dv s f) n % B ^ s = R at hX hd
  generalize E B (dv s f) n = X at hX hd ⊢
  generalize E B f n = Y at hX ⊢
  obtain ⟨P, hP'⟩ : ∃ P, B ^ s = P + 1 := ⟨B ^ s - 1, by omega⟩
  rw [hP'] at hd ⊢
  rw [Nat.add_sub_cancel]
  have hY : Y = P * Q + R := by
    have : (P + 1) * Q = P * Q + Q := by grind
    omega
  subst hY
  rw [← hd]
  grind

end Enc

/-! ## One Horner level is one division -/

theorem E_dv2 (B : Nat) (hB : 2 ≤ B) {d : Nat} (hd : 1 ≤ d) (f : Nat → Nat) (n G H : Nat)
    (hGH : G + H + 2 ≤ B) (hg : ∀ j, j ≤ n → dv d (dv d f) j ≤ G) (hh : ∀ j, j ≤ n → dv d f j ≤ H) :
    (E B f n * B) / ((B ^ d - 1) * (B ^ d - 1)) = E B (sh (dv d (dv d f)) (2 * d - 1)) n := by
  have hB0 : 0 < B := by omega
  have hBd : B ≤ B ^ d := by
    calc B = B ^ 1 := (Nat.pow_one B).symm
      _ ≤ B ^ d := Nat.pow_le_pow_right hB0 hd
  have e1 := E_dv B hB0 (s := d) (by omega) f n (fun j hj => by have := hh j hj; omega)
  have e2 := E_dv B hB0 (s := d) (by omega) (dv d f) n (fun j hj => by have := hg j hj; omega)
  have bh := E_low B hB0 (M := H) (by omega) d n hh
  have bg := E_low B hB0 (M := G) (by omega) d n hg
  have hsh := E_shdiv B hB0 (g := dv d (dv d f)) (n := n) (fun j hj => by have := hg j hj; omega) (2 * d - 1)
  rw [hsh]
  generalize E B (dv d f) n % B ^ d = Rh at e1 bh
  generalize E B (dv d (dv d f)) n % B ^ d = Rg at e2 bg
  generalize E B (dv d (dv d f)) n = Eg at e2 ⊢
  generalize E B (dv d f) n = Eh at e1 e2
  generalize E B f n = Ef at e1 ⊢
  have hP : B ^ (2 * d - 1) * B = B ^ d * B ^ d := by
    rw [← Nat.pow_succ, ← Nat.pow_add]; congr 1; omega
  obtain ⟨q, hq⟩ : ∃ q, B ^ d = q + 1 := ⟨B ^ d - 1, by omega⟩
  obtain ⟨c, hc⟩ : ∃ c, B = c + 1 := ⟨B - 1, by omega⟩
  rw [hq] at e1 e2 bh bg hP hBd ⊢
  simp only [Nat.add_sub_cancel] at e1 e2 bh bg ⊢
  rw [hc] at bh bg hGH hBd
  simp only [Nat.add_sub_cancel] at bh bg
  -- the full numerator
  have hnum : (Ef * B) * B ^ (2 * d - 1) = Eg * (q * q) + (q * Rg + (q + 1) * Rh) := by
    rw [Nat.mul_assoc, Nat.mul_comm B, hP]
    grind
  -- the remainder is below `q²`
  have hq0 : 0 < q := by omega
  have hH : H < q := by omega
  have hrem : q * Rg + (q + 1) * Rh < q * q := by
    have A1 : c * (q * Rg + (q + 1) * Rh) = q * (Rg * c) + (q + 1) * (Rh * c) := by grind
    have A2 : q * (Rg * c) ≤ q * (G * q) := Nat.mul_le_mul_left _ bg
    have A3 : (q + 1) * (Rh * c) ≤ (q + 1) * (H * q) := Nat.mul_le_mul_left _ bh
    have A4 : q * (G * q) + (q + 1) * (H * q) = q * ((G + H) * q + H) := by grind
    have A5 : (G + H) * q + H < c * q := by
      have : (G + H + 1) * q ≤ c * q := Nat.mul_le_mul_right _ (by omega)
      have : (G + H + 1) * q = (G + H) * q + q := by grind
      omega
    have A6 : q * ((G + H) * q + H) < q * (c * q) := Nat.mul_lt_mul_of_pos_left A5 hq0
    have A7 : q * (c * q) = c * (q * q) := by grind
    have : c * (q * Rg + (q + 1) * Rh) < c * (q * q) := by omega
    exact Nat.lt_of_mul_lt_mul_left this
  have hPpos : 0 < B ^ (2 * d - 1) := Nat.pow_pos hB0
  rw [← Nat.mul_div_mul_right _ _ hPpos, hnum, ← Nat.div_div_eq_div_mul,
    show Eg * (q * q) + (q * Rg + (q + 1) * Rh) = (q * q) * Eg + (q * Rg + (q + 1) * Rh) by
      rw [Nat.mul_comm Eg],
    Nat.mul_add_div (Nat.mul_pos hq0 hq0), Nat.div_eq_of_lt hrem, Nat.add_zero]

/-! ## The loop and the final digit -/

theorem level (N d : Nat) (hd : 1 ≤ d) (f : Nat → Nat) (hf : Bd 2 f) :
    Nat.add ((2 ^ (N + 4)) ^ N) (Nat.div (Nat.mul (E (2 ^ (N + 4)) f N) (2 ^ (N + 4)))
      (Nat.mul ((2 ^ (N + 4)) ^ d - 1) ((2 ^ (N + 4)) ^ d - 1)))
    = E (2 ^ (N + 4)) (stepS d f) N := by
  have hp : 1 ≤ 2 ^ N := Nat.one_le_two_pow
  have hB : 2 ^ (N + 4) = 16 * 2 ^ N := by rw [Nat.pow_add]; omega
  have hg : ∀ j, j ≤ N → dv d (dv d f) j ≤ 8 * 2 ^ N := by
    intro j hj
    have := dv_bd (s := d) (by omega) (dv_bd (s := d) (by omega) hf) j
    have : 2 ^ j ≤ 2 ^ N := Nat.pow_le_pow_right (by omega) hj
    have : 2 * (2 * 2) * 2 ^ j ≤ 2 * (2 * 2) * 2 ^ N := Nat.mul_le_mul_left _ this
    omega
  have hh : ∀ j, j ≤ N → dv d f j ≤ 4 * 2 ^ N := by
    intro j hj
    have := dv_bd (s := d) (by omega) hf j
    have : 2 ^ j ≤ 2 ^ N := Nat.pow_le_pow_right (by omega) hj
    have : 2 * 2 * 2 ^ j ≤ 2 * 2 * 2 ^ N := Nat.mul_le_mul_left _ this
    omega
  show (2 ^ (N + 4)) ^ N + E (2 ^ (N + 4)) f N * 2 ^ (N + 4) / (((2 ^ (N + 4)) ^ d - 1) * ((2 ^ (N + 4)) ^ d - 1)) = _
  rw [E_dv2 (2 ^ (N + 4)) (by omega) hd f N (8 * 2 ^ N) (4 * 2 ^ N) (by omega) hg hh,
    ← E_one (2 ^ (N + 4)) N, ← E_add]
  rfl

theorem pow_sub_one_div (B k : Nat) (hB : 0 < B) : (B ^ (k + 1) - 1) / B = B ^ k - 1 := by
  have hk : 1 ≤ B ^ k := Nat.pow_pos hB
  rw [Nat.pow_succ]
  obtain ⟨e, he⟩ : ∃ e, B ^ k = e + 1 := ⟨B ^ k - 1, by omega⟩
  rw [he]
  have h1 : (e + 1) * B - 1 = B * e + (B - 1) := by
    rw [Nat.add_mul, Nat.one_mul, Nat.mul_comm]; omega
  have h2 : (B * e + (B - 1)) / B = e := by
    rw [Nat.mul_add_div hB]
    have : (B - 1) / B = 0 := Nat.div_eq_of_lt (by omega)
    omega
  rw [h1, h2]
  omega

theorem loop_eq (N : Nat) : ∀ k (f : Nat → Nat), Bd 2 f →
    loop (2 ^ (N + 4)) ((2 ^ (N + 4)) ^ N) k (E (2 ^ (N + 4)) f N) ((2 ^ (N + 4)) ^ k - 1)
      = E (2 ^ (N + 4)) (U k f) N
  | 0, _, _ => rfl
  | k + 1, f, hf => by
    show loop (2 ^ (N + 4)) ((2 ^ (N + 4)) ^ N) k
      (Nat.add ((2 ^ (N + 4)) ^ N) (Nat.div (Nat.mul (E (2 ^ (N + 4)) f N) (2 ^ (N + 4)))
        (Nat.mul ((2 ^ (N + 4)) ^ (k + 1) - 1) ((2 ^ (N + 4)) ^ (k + 1) - 1))))
      (Nat.div ((2 ^ (N + 4)) ^ (k + 1) - 1) (2 ^ (N + 4))) = _
    rw [level N (k + 1) (by omega) f hf,
      show Nat.div ((2 ^ (N + 4)) ^ (k + 1) - 1) (2 ^ (N + 4)) = (2 ^ (N + 4)) ^ k - 1 from
        pow_sub_one_div _ k (Nat.pow_pos (by omega))]
    cases k with
    | zero => rfl
    | succ k => exact loop_eq N (k + 1) _ (stepS_bd (by omega) hf)

theorem D_big (N : Nat) : N < ((N + 25) / 10 + 1) * ((N + 25) / 10 + 1) := by
  generalize hx : (N + 25) / 10 + 1 = x
  have hx1 : N + 26 ≤ 10 * x := by omega
  -- `x² + 25 ≥ 10 x`
  rcases Nat.lt_or_ge x 5 with h | h
  · rcases (by omega : x = 0 ∨ x = 1 ∨ x = 2 ∨ x = 3 ∨ x = 4) with h' | h' | h' | h' | h' <;>
      subst h' <;> omega
  · obtain ⟨y, rfl⟩ : ∃ y, x = y + 5 := ⟨x - 5, by omega⟩
    have : (y + 5) * (y + 5) = y * y + 10 * y + 25 := by
      simp only [Nat.add_mul, Nat.mul_add]; omega
    omega

theorem implV2_correct : ∀ n, implV2 n = partitionSpec n := by
  intro N
  show Nat.mod (loop (2 ^ (N + 4)) ((2 ^ (N + 4)) ^ N) ((N + 25) / 10) ((2 ^ (N + 4)) ^ N)
    ((2 ^ (N + 4)) ^ ((N + 25) / 10) - 1)) (2 ^ (N + 4)) = partAux N N
  have hl := loop_eq N ((N + 25) / 10) one one_bd
  rw [E_one] at hl
  rw [hl]
  have hb := U_bd ((N + 25) / 10) one one_bd N
  have hp : 1 ≤ 2 ^ N := Nat.one_le_two_pow
  have hB : 2 ^ (N + 4) = 16 * 2 ^ N := by rw [Nat.pow_add]; omega
  show E (2 ^ (N + 4)) (U ((N + 25) / 10) one) N % 2 ^ (N + 4) = _
  rw [E_mod _ (by omega), U_DS, durfee N _ (D_big N)]


/-! ## V3: process two Horner levels per recursion step -/

def loop2 (B BN : Nat) : Nat → Nat → Nat → Nat :=
  fun k => Nat.rec (motive := fun _ => Nat → Nat → Nat) (fun Y _ => Y)
    (fun _ ih Y q =>
      ih (Nat.add BN (Nat.div
        (Nat.mul (Nat.add BN (Nat.div (Nat.mul Y B) (Nat.mul q q))) B)
        (Nat.mul (Nat.div q B) (Nat.div q B))))
        (Nat.div (Nat.div q B) B)) k

def loopFast (B BN k Y q : Nat) : Nat :=
  Nat.rec (motive := fun _ => Nat)
    (loop2 B BN (Nat.div k (nat_lit 2)) Y q)
    (fun _ _ => loop2 B BN (Nat.div k (nat_lit 2))
      (Nat.add BN (Nat.div (Nat.mul Y B) (Nat.mul q q))) (Nat.div q B))
    (Nat.mod k (nat_lit 2))

theorem loop2_eq (B BN : Nat) : ∀ k Y q,
    loop2 B BN k Y q = loop B BN (2 * k) Y q
  | 0, _, _ => rfl
  | k + 1, Y, q => by
    rw [show 2 * (k + 1) = (2 * k + 1) + 1 by omega]
    exact loop2_eq B BN k _ _

theorem loopFast_eq (B BN k Y q : Nat) : loopFast B BN k Y q = loop B BN k Y q := by
  rcases Nat.mod_two_eq_zero_or_one k with h | h
  · unfold loopFast
    rw [show Nat.mod k (nat_lit 2) = 0 from h]
    change loop2 B BN (k / 2) Y q = _
    rw [loop2_eq]
    congr 1 <;> omega
  · unfold loopFast
    rw [show Nat.mod k (nat_lit 2) = 1 from h]
    change loop2 B BN (k / 2) _ _ = _
    rw [loop2_eq]
    conv => rhs; rw [show k = 2 * (k / 2) + 1 by omega]
    rfl

def goFast (N B D : Nat) : Nat :=
  Nat.mod (loopFast B (Nat.pow B N) D (Nat.pow B N) (Nat.sub (Nat.pow B D) (nat_lit 1))) B

def impl (N : Nat) : Nat :=
  goFast N (Nat.pow (nat_lit 2) (Nat.add N (nat_lit 4))) (Nat.div (Nat.add N (nat_lit 25)) (nat_lit 10))

theorem impl_correct : ∀ n, impl n = partitionSpec n := by
  intro n
  unfold impl goFast
  rw [loopFast_eq]
  exact implV2_correct n

end Submission
