import Spec

/-!
# Partition p(n) by Kronecker substitution

The generating function of partitions into parts `≤ k` is `∏_{s ≤ k} 1/(1 - x^s)`.
Truncated at degree `N`, each factor is the finite geometric series
`G_s = Σ_{j ≤ N/s} x^(s·j)`. We evaluate every polynomial at `x = B = 2^W` with `W`
large enough that no coefficient of degree `≤ N` reaches `B`; then a polynomial is one
natural number, multiplying polynomials is one `Nat.mul` (GMP in the kernel), and
truncating at degree `N` is one `% B^(N+1)`. `p(N)` is the base-`B` digit at position `N`.

The kernel therefore performs `N` big multiplications (plus one division each for the
closed-form geometric series) instead of the spec's exponential recursion.

Proof outline:
* `enc c B L = Σ_{m<L} c m · B^m` encodes a coefficient function.
* `mulGeo`: multiplying an encoding by `geo B s J` modulo `B^L` encodes `conv c s J`.
* `conv_eq_spec`: `conv (partAux k) (k+1) J` agrees with `partAux (k+1)` below `N+1`.
* `partAux_le`: `partAux k m ≤ 2^(m+k)`, so all digits are `< B = 2^(2N+1)` and no carries occur.
* `geoF_eq` and `loop_eq`: the closed-form geometric series and the `Nat.rec` loop agree
  with the proof-side `geo`/`step`.
-/

namespace Submission

/-! ## Implementation -/

/-- Horner form of `Σ_{j<J} B^(s·j)`. -/
def geo (B s : Nat) : Nat → Nat
  | 0 => 0
  | J + 1 => geo B s J * B ^ s + 1

/-- Encoded product `∏_{s=1}^{k} G_s` truncated modulo `M = B^(N+1)` (proof-side form). -/
def step (B M N : Nat) : Nat → Nat
  | 0 => 1
  | k + 1 => (step B M N k * geo B (k + 1) (N / (k + 1) + 1)) % M

/-- Closed form of the geometric series: `(B^(s·J) - 1) / (B^s - 1)`, one kernel division. -/
def geoF (B s J : Nat) : Nat := (B ^ (s * J) - 1) / (B ^ s - 1)

/-- Digit width: every coefficient needed is at most `2^(2N)`. -/
def width (N : Nat) : Nat := 2 * N + 1

def impl (N : Nat) : Nat :=
  let B := 2 ^ (2 * N + 1)
  let M := B ^ (N + 1)
  Nat.rec (motive := fun _ => Nat) 1
    (fun k acc => (acc * geoF B (k + 1) (N / (k + 1) + 1)) % M) N / B ^ N

/-! ## Encodings -/

def enc (c : Nat → Nat) (B : Nat) : Nat → Nat
  | 0 => 0
  | L + 1 => enc c B L + c L * B ^ L

theorem enc_congr {f g : Nat → Nat} (B : Nat) :
    ∀ L, (∀ m, m < L → f m = g m) → enc f B L = enc g B L
  | 0, _ => rfl
  | L + 1, h => by
    simp only [enc]
    rw [enc_congr B L (fun m hm => h m (by omega)), h L (by omega)]

theorem enc_zero {f : Nat → Nat} (B : Nat) :
    ∀ L, (∀ m, m < L → f m = 0) → enc f B L = 0
  | 0, _ => rfl
  | L + 1, h => by
    simp only [enc]
    rw [enc_zero B L (fun m hm => h m (by omega)), h L (by omega)]
    simp

theorem enc_add (f g : Nat → Nat) (B : Nat) :
    ∀ L, enc (fun m => f m + g m) B L = enc f B L + enc g B L
  | 0 => rfl
  | L + 1 => by
    simp only [enc]
    rw [enc_add f g B L, Nat.add_mul]
    omega

/-- Shift coefficients up by `t`. -/
def sh (c : Nat → Nat) (t m : Nat) : Nat := if t ≤ m then c (m - t) else 0

theorem enc_mul_pow (c : Nat → Nat) (B t : Nat) :
    ∀ L, enc c B L * B ^ t = enc (sh c t) B (L + t)
  | 0 => by
    rw [Nat.zero_add, enc_zero B t (fun m hm => by simp [sh]; omega)]
    simp [enc]
  | L + 1 => by
    have e : L + 1 + t = (L + t) + 1 := by omega
    rw [e]
    simp only [enc]
    rw [Nat.add_mul, enc_mul_pow c B t L]
    have hs : sh c t (L + t) = c L := by
      simp [sh]
    rw [hs, Nat.pow_add, Nat.mul_assoc]

/-- The part of an encoding above position `L` is a multiple of `B^L`. -/
theorem enc_split (c : Nat → Nat) (B L : Nat) :
    ∀ d, ∃ X, enc c B (L + d) = enc c B L + B ^ L * X
  | 0 => ⟨0, by simp⟩
  | d + 1 => by
    obtain ⟨X, hX⟩ := enc_split c B L d
    refine ⟨X + c (L + d) * B ^ d, ?_⟩
    have e : L + (d + 1) = (L + d) + 1 := by omega
    rw [e]
    simp only [enc]
    rw [hX, Nat.pow_add, Nat.mul_add]
    have : c (L + d) * (B ^ L * B ^ d) = B ^ L * (c (L + d) * B ^ d) := by
      rw [Nat.mul_left_comm]
    rw [this]
    omega

theorem enc_mod_of_le (c : Nat → Nat) (B L L' : Nat) (h : L ≤ L') :
    enc c B L' % B ^ L = enc c B L % B ^ L := by
  obtain ⟨X, hX⟩ := enc_split c B L (L' - L)
  have e : L + (L' - L) = L' := by omega
  rw [e] at hX
  rw [hX, Nat.add_mul_mod_self_left]

theorem enc_lt {c : Nat → Nat} {B : Nat} :
    ∀ L, (∀ m, m < L → c m < B) → enc c B L < B ^ L
  | 0, _ => by simp [enc]
  | L + 1, h => by
    simp only [enc]
    have h1 := enc_lt L (fun m hm => h m (by omega))
    have h2 : c L + 1 ≤ B := h L (by omega)
    have h3 : (c L + 1) * B ^ L ≤ B * B ^ L := Nat.mul_le_mul_right _ h2
    rw [Nat.add_mul, Nat.one_mul] at h3
    rw [Nat.pow_succ, Nat.mul_comm (B ^ L) B]
    omega

theorem enc_div {c : Nat → Nat} {B : Nat} (hB : 0 < B) (L : Nat)
    (h : ∀ m, m < L → c m < B) : enc c B (L + 1) / B ^ L = c L := by
  simp only [enc]
  rw [Nat.add_mul_div_right _ _ (Nat.pow_pos hB), Nat.div_eq_of_lt (enc_lt L h)]
  simp

/-! ## Multiplying by a geometric series -/

/-- `conv c s J m = Σ_{j<J, j·s ≤ m} c (m - j·s)`, in the recursive form produced by Horner. -/
def conv (c : Nat → Nat) (s : Nat) : Nat → Nat → Nat
  | 0, _ => 0
  | J + 1, m => c m + sh (conv c s J) s m

theorem mod_mul_add_congr {a a' M : Nat} (t x : Nat) (h : a % M = a' % M) :
    (a * t + x) % M = (a' * t + x) % M := by
  rw [Nat.add_mod, Nat.mul_mod, h, ← Nat.mul_mod, ← Nat.add_mod]

theorem mod_add_congr {a a' M : Nat} (x : Nat) (h : a % M = a' % M) :
    (a + x) % M = (a' + x) % M := by
  rw [Nat.add_mod, h, ← Nat.add_mod]

theorem mulGeo (c : Nat → Nat) (B s L : Nat) :
    ∀ J, (enc c B L * geo B s J) % B ^ L = enc (conv c s J) B L % B ^ L
  | 0 => by
    rw [enc_zero (f := conv c s 0) B L (fun m _ => rfl)]
    simp [geo]
  | J + 1 => by
    have e1 : enc c B L * geo B s (J + 1) = (enc c B L * geo B s J) * B ^ s + enc c B L := by
      simp only [geo]
      rw [Nat.mul_add, Nat.mul_one, Nat.mul_assoc]
    rw [e1, mod_mul_add_congr _ _ (mulGeo c B s L J), enc_mul_pow,
      mod_add_congr _ (enc_mod_of_le _ B L (L + s) (by omega)), ← enc_add]
    congr 1
    apply enc_congr
    intro m _
    simp only [conv]
    omega

/-! ## The spec's sum as a recursion -/

theorem foldl_add_start (l : List Nat) (a : Nat) :
    l.foldl (· + ·) a = a + l.foldl (· + ·) 0 := by
  induction l generalizing a with
  | nil => simp
  | cons x l ih =>
    simp only [List.foldl_cons]
    rw [ih (a + x), ih (0 + x)]
    omega

/-- The spec's inner sum `Σ_{j ≤ m/s} c (m - j·s)`. -/
def specSum (c : Nat → Nat) (s m : Nat) : Nat :=
  ((List.range (m / s + 1)).map (fun j => c (m - j * s))).foldl (· + ·) 0

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

theorem conv_eq_specSum (c : Nat → Nat) {s : Nat} (hs : 0 < s) :
    ∀ J m, m / s + 1 ≤ J → conv c s J m = specSum c s m
  | 0, m, h => absurd h (Nat.not_succ_le_zero _)
  | J + 1, m, h => by
    rw [specSum_rec c hs m]
    simp only [conv]
    congr 1
    unfold sh
    by_cases hm : s ≤ m
    · rw [if_pos hm, if_pos hm]
      apply conv_eq_specSum c hs J
      rw [Nat.div_eq_sub_div hs hm] at h
      omega
    · rw [if_neg hm, if_neg hm]

theorem partAux_succ (k m : Nat) : partAux (k + 1) m = specSum (partAux k) (k + 1) m := by
  rw [partAux]
  rfl

/-! ## Coefficient bounds -/

theorem foldl_le (l : List Nat) (b : Nat) (h : ∀ x, x ∈ l → x ≤ b) :
    l.foldl (· + ·) 0 ≤ l.length * b := by
  induction l with
  | nil => simp
  | cons x l ih =>
    rw [List.foldl_cons, foldl_add_start, List.length_cons, Nat.succ_mul]
    have hx := h x (by simp)
    have hl := ih (fun y hy => h y (by simp [hy]))
    omega

theorem partAux_le : ∀ k m, partAux k m ≤ 2 ^ (m + k)
  | 0, 0 => by simp [partAux]
  | 0, m + 1 => by simp [partAux]
  | k + 1, m => by
    induction m using Nat.strongRecOn with
    | ind m ihm =>
      rw [partAux_succ, specSum_rec _ (by omega : 0 < k + 1)]
      have h1 := partAux_le k m
      have h2 : 2 ^ (m + k) + 2 ^ (m + k) = 2 ^ (m + (k + 1)) := by
        rw [← Nat.add_assoc, Nat.pow_succ]; omega
      unfold sh
      by_cases hm : k + 1 ≤ m
      · rw [if_pos hm, ← partAux_succ]
        have h3 := ihm (m - (k + 1)) (by omega)
        have h4 : m - (k + 1) + (k + 1) = m := by omega
        rw [h4] at h3
        have h5 : 2 ^ m ≤ 2 ^ (m + k) := Nat.pow_le_pow_right (by omega) (by omega)
        omega
      · rw [if_neg hm]
        omega

theorem partAux_lt_base (N k m : Nat) (hk : k ≤ N) (hm : m ≤ N) :
    partAux k m < 2 ^ width N := by
  have h1 := partAux_le k m
  have h2 : 2 ^ (m + k) < 2 ^ width N :=
    Nat.pow_lt_pow_right (by decide) (by unfold width; omega)
  omega

/-! ## The geometric series in closed form -/

theorem geo_mul (q : Nat) (hq : 1 ≤ q) : ∀ J, (q - 1) * geo (q) 1 J + 1 = q ^ J := by
  intro J
  induction J with
  | zero => simp [geo]
  | succ J ih =>
    simp only [geo, Nat.pow_one] at ih ⊢
    rw [Nat.pow_succ, ← ih, Nat.mul_add, Nat.mul_one, Nat.add_mul, Nat.one_mul,
      ← Nat.mul_assoc]
    omega

theorem geo_pow (B s : Nat) : ∀ J, geo B s J = geo (B ^ s) 1 J
  | 0 => rfl
  | J + 1 => by simp only [geo, Nat.pow_one]; rw [geo_pow B s J]

theorem geoF_eq (B s J : Nat) (hB : 2 ≤ B) (hs : 0 < s) : geoF B s J = geo B s J := by
  have hq : 2 ≤ B ^ s := by
    calc 2 ≤ B := hB
      _ = B ^ 1 := (Nat.pow_one B).symm
      _ ≤ B ^ s := Nat.pow_le_pow_right (by omega) hs
  unfold geoF
  rw [Nat.pow_mul, ← geo_mul (B ^ s) (by omega) J, geo_pow B s J, Nat.add_sub_cancel,
    Nat.mul_div_cancel_left _ (by omega)]

theorem loop_eq (B M N : Nat) (hB : 2 ≤ B) : ∀ k,
    Nat.rec (motive := fun _ => Nat) 1
      (fun k acc => (acc * geoF B (k + 1) (N / (k + 1) + 1)) % M) k = step B M N k
  | 0 => rfl
  | k + 1 => by
    simp only [step]
    rw [← loop_eq B M N hB k, geoF_eq B (k + 1) _ hB (by omega)]

/-! ## Main correctness -/

theorem step_eq (N : Nat) :
    ∀ k, k ≤ N → step (2 ^ width N) ((2 ^ width N) ^ (N + 1)) N k
      = enc (partAux k) (2 ^ width N) (N + 1)
  | 0, _ => by
    simp only [step]
    have : ∀ L, enc (partAux 0) (2 ^ width N) (L + 1) = 1 := by
      intro L
      induction L with
      | zero => simp [enc, partAux]
      | succ L ih =>
        simp only [enc] at ih ⊢
        rw [ih]
        simp [partAux]
    rw [this]
  | k + 1, hk => by
    simp only [step]
    rw [step_eq N k (by omega), mulGeo]
    have hs : 0 < k + 1 := by omega
    rw [enc_congr _ (N + 1) (g := partAux (k + 1)) (fun m hm => by
      rw [conv_eq_specSum _ hs _ _ (by
        have := Nat.div_le_div_right (c := k + 1) (show m ≤ N by omega)
        omega), partAux_succ])]
    apply Nat.mod_eq_of_lt
    apply enc_lt
    intro m hm
    exact partAux_lt_base N (k + 1) m hk (by omega)

theorem impl_correct : ∀ n, impl n = partitionSpec n := by
  intro N
  simp only [impl, partitionSpec]
  rw [loop_eq _ _ N (by
      have : 2 ^ 1 ≤ 2 ^ (2 * N + 1) := Nat.pow_le_pow_right (by omega) (by omega)
      simpa using this)]
  have e : 2 * N + 1 = width N := rfl
  rw [e, step_eq N N (Nat.le_refl N)]
  apply enc_div (Nat.two_pow_pos _) N
  intro m hm
  exact partAux_lt_base N N m (Nat.le_refl N) (by omega)

end Submission
