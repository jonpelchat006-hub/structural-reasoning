import Base

set_option maxRecDepth 200000

namespace Submission

/-! ## Evaluation of digit lists -/

/-- Value of a high-to-low integer list at `B`. -/
def ev (B : Int) : List Int → Int
  | [] => 0
  | a :: as => a * B ^ as.length + ev B as

theorem ev_cons (B a : Int) (as : List Int) : ev B (a :: as) = a * B ^ as.length + ev B as := rfl

theorem ev_natAbs_lt (B : Nat) (hB : 0 < B) : ∀ l : List Int, (∀ x ∈ l, x.natAbs < B) →
    (ev B l).natAbs < B ^ l.length
  | [], _ => by simp [ev]
  | a :: as, h => by
    have ha : a.natAbs < B := h a (by simp)
    have ih := ev_natAbs_lt B hB as (fun x hx => h x (by simp [hx]))
    rw [ev_cons, List.length_cons]
    have h1 : (a * (B : Int) ^ as.length + ev B as).natAbs ≤ a.natAbs * B ^ as.length + (ev B as).natAbs := by
      have := Int.natAbs_add_le (a * (B : Int) ^ as.length) (ev B as)
      rw [Int.natAbs_mul, Int.natAbs_pow, Int.natAbs_natCast] at this
      exact this
    have h2 : a.natAbs * B ^ as.length ≤ (B - 1) * B ^ as.length := Nat.mul_le_mul_right _ (by omega)
    have h3 : (B - 1) * B ^ as.length + B ^ as.length = B ^ (as.length + 1) := by
      rw [Nat.pow_succ, Nat.sub_mul, Nat.one_mul, Nat.mul_comm]
      have : B ^ as.length ≤ B ^ as.length * B := Nat.le_mul_of_pos_right _ hB
      omega
    omega

theorem ev_eq_zero (B : Nat) (hB : 0 < B) : ∀ l : List Int, (∀ x ∈ l, x.natAbs < B) →
    ev B l = 0 → ∀ x ∈ l, x = 0
  | [], _, _ => by simp
  | a :: as, h, h0 => by
    have hlt := ev_natAbs_lt B hB as (fun x hx => h x (by simp [hx]))
    rw [ev_cons] at h0
    have ha : a = 0 := by
      by_cases hne : a = 0
      · exact hne
      exfalso
      have h1 : (a * (B : Int) ^ as.length).natAbs = (ev B as).natAbs := by
        rw [show a * (B : Int) ^ as.length = - ev B as by omega, Int.natAbs_neg]
      rw [Int.natAbs_mul, Int.natAbs_pow, Int.natAbs_natCast] at h1
      have : 1 ≤ a.natAbs := by omega
      have : B ^ as.length ≤ a.natAbs * B ^ as.length := Nat.le_mul_of_pos_left _ (by omega)
      omega
    subst ha
    have h0' : ev B as = 0 := by simpa using h0
    have ih := ev_eq_zero B hB as (fun x hx => h x (by simp [hx])) h0'
    intro x hx
    simp only [List.mem_cons] at hx
    rcases hx with rfl | hx
    · rfl
    · exact ih x hx

/-- Elementwise `n − k·q`. -/
def dlist (k : Int) : List Int → List Int → List Int
  | n :: ns, q :: qs => (n - k * q) :: dlist k ns qs
  | _, _ => []

theorem ev_dlist (B k : Int) : ∀ N Q : List Int, N.length = Q.length →
    ev B (dlist k N Q) = ev B N - k * ev B Q
  | [], [], _ => by simp [dlist, ev]
  | n :: ns, q :: qs, h => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    have ih := ev_dlist B k ns qs h
    have hl : (dlist k ns qs).length = ns.length := by
      clear ih; induction ns generalizing qs with
      | nil => simp [dlist]
      | cons a as iha => cases qs with
        | nil => simp at h
        | cons b bs => simp [dlist, iha bs (by simpa using h)]
    simp only [dlist, ev_cons, ih, hl, ← h]
    grind
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h

theorem dlist_zero (k : Int) : ∀ N Q : List Int, N.length = Q.length →
    (∀ x ∈ dlist k N Q, x = 0) → N = Q.map (fun q => k * q)
  | [], [], _, _ => rfl
  | n :: ns, q :: qs, h, h0 => by
    simp only [dlist, List.mem_cons, forall_eq_or_imp] at h0
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    rw [List.map_cons, dlist_zero k ns qs h h0.2]
    congr 1; omega
  | [], _ :: _, h, _ => by simp at h
  | _ :: _, [], h, _ => by simp at h

/-- The E-argument: an integer combination that vanishes at `B` with all coefficients below `B`
in absolute value vanishes coefficientwise. -/
theorem eq_map_of_ev (B : Nat) (hB : 0 < B) (k : Int) (N Q : List Int) (hl : N.length = Q.length)
    (hb : ∀ x ∈ dlist k N Q, x.natAbs < B) (he : ev B N = k * ev B Q) : N = Q.map (fun q => k * q) := by
  apply dlist_zero k N Q hl
  apply ev_eq_zero B hB _ hb
  rw [ev_dlist _ _ _ _ hl]; omega


/-! ## Lanes and digits -/

/-- High-to-low digits in lns of width `W`. -/
def ofD (W : Nat) : List Nat → Nat
  | [] => 0
  | d :: ds => d * 2 ^ (W * ds.length) + ofD W ds

/-- Shift amounts `W·p, W·(p−1), …, 0`. -/
def lns (W : Nat) : Nat → List Nat
  | 0 => [0]
  | p + 1 => W * (p + 1) :: lns W p

/-- Shift amounts `W·p, …, W` (every digit but the last). -/
def lns1 (W : Nat) : Nat → List Nat
  | 0 => []
  | p + 1 => W * (p + 1) :: lns1 W p

theorem lanes_length (W : Nat) : ∀ p, (lns W p).length = p + 1
  | 0 => rfl
  | p + 1 => by simp [lns, lanes_length W p]

theorem ofD_lt (W : Nat) : ∀ ds : List Nat, (∀ d ∈ ds, d < 2 ^ W) → ofD W ds < 2 ^ (W * ds.length)
  | [], _ => by simp [ofD]
  | d :: ds, h => by
    have hd : d < 2 ^ W := h d (by simp)
    have ih := ofD_lt W ds (fun x hx => h x (by simp [hx]))
    simp only [ofD, List.length_cons]
    have h1 : d * 2 ^ (W * ds.length) ≤ (2 ^ W - 1) * 2 ^ (W * ds.length) := Nat.mul_le_mul_right _ (by omega)
    have h2 : 2 ^ (W * (ds.length + 1)) = 2 ^ W * 2 ^ (W * ds.length) := by
      rw [Nat.mul_add, Nat.mul_one, Nat.pow_add, Nat.mul_comm]
    rw [h2, Nat.sub_mul, Nat.one_mul] at *
    have h3 : 2 ^ (W * ds.length) ≤ 2 ^ W * 2 ^ (W * ds.length) :=
      Nat.le_mul_of_pos_left _ (Nat.two_pow_pos W)
    omega

theorem land_shr (u s W : Nat) : Nat.land (Nat.shiftRight u s) (2 ^ W - 1) = u / 2 ^ s % 2 ^ W := by
  rw [nand, nshr, Nat.and_two_pow_sub_one_eq_mod, Nat.shiftRight_eq_div_pow]

theorem digit_add_mul (W a r q n : Nat) (hq : q < n) :
    (a * 2 ^ (W * n) + r) / 2 ^ (W * q) % 2 ^ W = r / 2 ^ (W * q) % 2 ^ W := by
  have hx : W * n = W * (n - q - 1) + W + W * q := by
    rw [show W * (n - q - 1) + W + W * q = W * ((n - q - 1) + 1 + q) by
      rw [Nat.mul_add, Nat.mul_add, Nat.mul_one]]
    congr 1; omega
  have e : a * 2 ^ (W * n) = (a * 2 ^ (W * (n - q - 1)) * 2 ^ W) * 2 ^ (W * q) := by
    rw [hx, Nat.pow_add, Nat.pow_add]; simp only [Nat.mul_assoc]
  rw [e, Nat.add_comm, Nat.add_mul_div_right _ _ (Nat.two_pow_pos _), Nat.add_mul_mod_self_right]

theorem digit_top (W d r n : Nat) (hd : d < 2 ^ W) (hr : r < 2 ^ (W * n)) :
    (d * 2 ^ (W * n) + r) / 2 ^ (W * n) % 2 ^ W = d := by
  rw [Nat.add_comm, Nat.add_mul_div_right _ _ (Nat.two_pow_pos _), Nat.div_eq_of_lt hr, Nat.zero_add,
    Nat.mod_eq_of_lt hd]

theorem digit_mod (W u q n : Nat) (hq : q < n) :
    u / 2 ^ (W * q) % 2 ^ W = u % 2 ^ (W * n) / 2 ^ (W * q) % 2 ^ W := by
  conv => lhs; rw [← Nat.div_add_mod u (2 ^ (W * n)), Nat.mul_comm]
  exact digit_add_mul W _ _ q n hq

theorem digsU_add_mul (W a r n : Nat) : ∀ q, q < n →
    digsU (2 ^ W - 1) (a * 2 ^ (W * n) + r) (lns W q) = digsU (2 ^ W - 1) r (lns W q)
  | 0, h => by
    simp only [lns, digsU, land_shr]
    exact congrArg (· :: []) (digit_add_mul W a r 0 n h)
  | q + 1, h => by
    simp only [lns, digsU, land_shr]
    rw [digit_add_mul W a r (q + 1) n h, digsU_add_mul W a r n q (by omega)]

theorem digsU_mod (W u n : Nat) : ∀ q, q < n →
    digsU (2 ^ W - 1) u (lns W q) = digsU (2 ^ W - 1) (u % 2 ^ (W * n)) (lns W q) := by
  intro q hq
  conv => lhs; rw [← Nat.div_add_mod u (2 ^ (W * n)), Nat.mul_comm]
  exact digsU_add_mul W _ _ n q hq

theorem digsU_ofD (W : Nat) : ∀ ds : List Nat, (∀ d ∈ ds, d < 2 ^ W) → ∀ p, ds.length = p + 1 →
    digsU (2 ^ W - 1) (ofD W ds) (lns W p) = ds
  | [], _, p, h => by simp at h
  | d :: ds, h, p, hl => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    subst hl
    have hd : d < 2 ^ W := h d (by simp)
    have hr := ofD_lt W ds (fun x hx => h x (by simp [hx]))
    cases ds with
    | nil =>
      simp only [ofD, List.length_nil, Nat.mul_zero, Nat.pow_zero, Nat.mul_one, Nat.add_zero, lns, digsU,
        land_shr, Nat.div_one]
      rw [Nat.mod_eq_of_lt hd]
    | cons e es =>
      simp only [List.length_cons] at hr ⊢
      simp only [ofD, List.length_cons, lns, digsU, land_shr]
      rw [show ofD W (e :: es) = e * 2 ^ (W * es.length) + ofD W es from rfl] at hr
      have htop := digit_top W d (e * 2 ^ (W * es.length) + ofD W es) (es.length + 1) hd hr
      rw [htop, digsU_add_mul W d _ (es.length + 1) es.length (by omega)]
      have := digsU_ofD W (e :: es) (fun x hx => h x (List.mem_cons_of_mem d hx)) es.length (by simp)
      simp only [ofD] at this
      rw [this]

theorem ofD_digsU (W : Nat) : ∀ p u, u < 2 ^ (W * (p + 1)) →
    ofD W (digsU (2 ^ W - 1) u (lns W p)) = u ∧ (digsU (2 ^ W - 1) u (lns W p)).length = p + 1
  | 0, u, h => by
    simp only [lns, digsU, land_shr, Nat.mul_zero, Nat.pow_zero, Nat.div_one, ofD, List.length_cons,
      List.length_nil, Nat.mul_one, Nat.add_zero, Nat.zero_add] at h ⊢
    exact ⟨Nat.mod_eq_of_lt h, trivial⟩
  | p + 1, u, h => by
    have ih := ofD_digsU W p (u % 2 ^ (W * (p + 1))) (Nat.mod_lt _ (Nat.two_pow_pos _))
    simp only [lns, digsU, land_shr]
    rw [digsU_mod W u (p + 1) p (by omega)]
    refine ⟨?_, by simp [ih.2]⟩
    simp only [ofD, ih.2]
    rw [ih.1]
    have hq : u / 2 ^ (W * (p + 1)) < 2 ^ W := by
      rw [Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add]
      rw [show W + W * (p + 1) = W * (p + 1 + 1) by rw [Nat.mul_add W (p + 1) 1]; omega]
      exact h
    rw [Nat.mod_eq_of_lt hq, Nat.mul_comm]
    exact Nat.div_add_mod u _

theorem packL_ofD (W : Nat) : ∀ ds : List Nat, ∀ p, ds.length = p + 1 → packL ds (lns1 W p) = ofD W ds
  | [], _, h => by simp at h
  | [d], p, h => by
    simp at h; subst h; simp [packL, ofD]
  | d :: e :: ds, p, h => by
    simp only [List.length_cons] at h
    obtain ⟨q, rfl⟩ : ∃ q, p = q + 1 := ⟨p - 1, by omega⟩
    simp only [lns1, packL]
    rw [packL_ofD W (e :: ds) q (by simp; omega), nadd, nshl, Nat.shiftLeft_eq]
    simp only [ofD, List.length_cons]
    rw [show q + 1 = ds.length + 1 by omega]
    omega

/-! ## The mask check -/

theorem testBit_lane (W b j : Nat) (hbW : b + 1 ≤ W) :
    (2 ^ W - 2 ^ (b + 1)).testBit j = (decide (b + 1 ≤ j) && decide (j < W)) := by
  have e : 2 ^ W - 2 ^ (b + 1) = (2 ^ (W - (b + 1)) - 1) * 2 ^ (b + 1) := by
    rw [Nat.sub_mul, Nat.one_mul, ← Nat.pow_add, Nat.sub_add_cancel hbW]
  rw [e, Nat.testBit_mul_two_pow, Nat.testBit_two_pow_sub_one]
  by_cases h1 : b + 1 ≤ j
  · simp only [h1, decide_true, Bool.true_and]
    congr 1; apply propext; omega
  · simp [h1]

theorem hmask_testBit (W b : Nat) (hbW : b + 1 ≤ W) : ∀ L p j, p < L → b + 1 ≤ j → j < W →
    (hmask W b L).testBit (W * p + j) = true
  | 0, p, j, h, _, _ => absurd h (by omega)
  | L + 1, p, j, hp, h1, h2 => by
    have hl : 2 ^ W - 2 ^ (b + 1) < 2 ^ W := by
      have := Nat.two_pow_pos (b + 1); have := Nat.two_pow_pos W; omega
    simp only [hmask]
    rw [Nat.testBit_two_pow_mul_add _ hl]
    cases p with
    | zero =>
      simp only [Nat.mul_zero, Nat.zero_add, h2, if_true]
      rw [testBit_lane W b j hbW]; simp [h1, h2]
    | succ p =>
      rw [if_neg (by rw [Nat.mul_add]; omega)]
      rw [show W * (p + 1) + j - W = W * p + j by rw [Nat.mul_add]; omega]
      exact hmask_testBit W b hbW L p j (by omega) h1 h2

theorem mask_digit (W b L u : Nat) (hbW : b + 1 ≤ W) (h : Nat.land u (hmask W b L) = 0) :
    ∀ p, p < L → u / 2 ^ (W * p) % 2 ^ W < 2 ^ (b + 1) := by
  intro p hp
  apply Nat.lt_pow_two_of_testBit
  intro j hj
  rw [← Nat.shiftRight_eq_div_pow, Nat.testBit_mod_two_pow, Nat.testBit_shiftRight]
  by_cases hjW : j < W
  · simp only [hjW, decide_true, Bool.true_and]
    have h0 := congrArg (fun x => x.testBit (W * p + j)) h
    simp only [nand, Nat.testBit_and, Nat.zero_testBit] at h0
    rw [hmask_testBit W b hbW L p j hp hj hjW, Bool.and_true] at h0
    exact h0
  · simp [hjW]

/-- What the two lane checks give: the digits of `u` in lns `0 … L−1`, each below `2^(b+1)`. -/
theorem decode (W b L u : Nat) (hbW : b + 1 ≤ W) (hL : 1 ≤ L) (hm : Nat.land u (hmask W b L) = 0)
    (hs : Nat.shiftRight u (W * L) = 0) :
    ofD W (digsU (2 ^ W - 1) u (lns W (L - 1))) = u ∧
    (digsU (2 ^ W - 1) u (lns W (L - 1))).length = L ∧
    ∀ d ∈ digsU (2 ^ W - 1) u (lns W (L - 1)), d < 2 ^ (b + 1) := by
  have hu : u < 2 ^ (W * L) := by
    rw [nshr, Nat.shiftRight_eq_div_pow] at hs
    exact (Nat.div_eq_zero_iff_lt (Nat.two_pow_pos _)).mp hs
  obtain ⟨h1, h2⟩ := ofD_digsU W (L - 1) u (by rw [Nat.sub_add_cancel hL]; exact hu)
  refine ⟨h1, by rw [h2]; omega, ?_⟩
  -- every digit is a lane value
  have key : ∀ q, q < L → ∀ d ∈ digsU (2 ^ W - 1) u (lns W q), d < 2 ^ (b + 1) := by
    intro q
    induction q with
    | zero => intro _ d hd; simp [lns, digsU] at hd; subst hd
              have := mask_digit W b L u hbW hm 0 (by omega); simpa using this
    | succ q ih =>
      intro hq d hd
      simp only [lns, digsU, List.mem_cons, land_shr] at hd
      rcases hd with rfl | hd
      · exact mask_digit W b L u hbW hm (q + 1) hq
      · exact ih (by omega) d hd
  exact key (L - 1) (by omega)


/-! ## Offset digits -/

theorem rep_succ' (W : Nat) : ∀ n, rep W (n + 1) = 2 ^ (W * n) + rep W n
  | 0 => by simp [rep]
  | n + 1 => by
    have ih := rep_succ' W n
    show 2 ^ W * rep W (n + 1) + 1 = 2 ^ (W * (n + 1)) + (2 ^ W * rep W n + 1)
    rw [ih, Nat.mul_add, ← Nat.pow_add, show W + W * n = W * (n + 1) by rw [Nat.mul_add, Nat.mul_one]; omega]
    omega

/-- Offset digits `x + T` of an integer list. -/
def offs (T : Nat) (S : List Int) : List Nat := S.map (fun x => (x + (T : Int)).toNat)

theorem offs_length (T : Nat) (S : List Int) : (offs T S).length = S.length := by simp [offs]

theorem ofD_offs (W T : Nat) : ∀ S : List Int, (∀ x ∈ S, -(T : Int) ≤ x) →
    (ofD W (offs T S) : Int) = ev ((2 ^ W : Nat) : Int) S + T * rep W S.length
  | [], _ => by simp [offs, ofD, ev, rep]
  | x :: xs, h => by
    have hx : -(T : Int) ≤ x := h x (by simp)
    have ih := ofD_offs W T xs (fun y hy => h y (by simp [hy]))
    simp only [offs, List.map_cons, ofD, List.length_map, List.length_cons, rep_succ'] at ih ⊢
    rw [ev_cons]
    push_cast
    rw [ih, Int.toNat_of_nonneg (by omega), ← Int.pow_mul]
    grind

theorem offs_lt (T : Nat) (S : List Int) (h : ∀ x ∈ S, -(T : Int) ≤ x ∧ x < T) : ∀ d ∈ offs T S, d < 2 * T := by
  intro d hd
  simp only [offs, List.mem_map] at hd
  obtain ⟨x, hx, rfl⟩ := hd
  have := h x hx
  omega

/-- Digits below `2T` decode to integers in `[−T, T)` whose offset digits they are. -/
theorem undigits (T : Nat) (ds : List Nat) (h : ∀ d ∈ ds, d < 2 * T) :
    offs T (ds.map (fun d : Nat => (d : Int) - T)) = ds ∧
    ∀ x ∈ ds.map (fun d : Nat => (d : Int) - T), -(T : Int) ≤ x ∧ x < T := by
  constructor
  · simp only [offs, List.map_map]
    conv => rhs; rw [← List.map_id ds]
    apply List.map_congr_left
    intro d _; simp
  · intro x hx
    simp only [List.mem_map] at hx
    obtain ⟨d, hd, rfl⟩ := hx
    have := h d hd
    omega

/-! ## The normal step on integer lists -/

theorem ev_r2 (B LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    ev B (r2 LG LF C1 Xs Zs) =
      LG * LG * ev B Xs - LG * LF * (B * ev B Zs - Zs.headD 0 * B ^ Zs.length) - C1 * ev B Zs
  | [], [], _ => by simp [r2, ev]
  | X :: Xs, Z :: Zs, h => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at h
    have ih := ev_r2 B LG LF C1 Xs Zs h
    have hl : (r2 LG LF C1 Xs Zs).length = Xs.length := by
      clear ih; induction Xs generalizing Zs with
      | nil => simp [r2]
      | cons a as iha => cases Zs with
        | nil => simp at h
        | cons b bs => simp [r2, iha bs (by simpa using h)]
    simp only [r2, ev_cons, hl, ih, List.headD_cons, List.length_cons, h]
    rw [Int.pow_succ]
    grind
  | [], _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h

theorem ev_step (B lf f1 lg : Int) (xs zs : List Int) (h : xs.length = zs.length) :
    ev B (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs) =
      lg * lg * ev B (lf :: f1 :: xs) - (lf * lg * B + (lg * f1 - lf * zs.headD 0)) * ev B (lg :: zs) := by
  rw [ev_r2 B lg lf _ xs zs h]
  simp only [ev_cons, List.length_cons, h]
  rw [Int.pow_succ]
  grind

theorem headD_mul (c : Int) (l : List Int) : (l.map (c * ·)).headD 0 = c * l.headD 0 := by
  cases l <;> simp

theorem r2_sign (sF sG : Int) (hG : sG * sG = 1) (LG LF C1 : Int) : ∀ Xs Zs : List Int,
    r2 (sG * LG) (sF * LF) (sF * sG * C1) (Xs.map (sF * ·)) (Zs.map (sG * ·)) =
      (r2 LG LF C1 Xs Zs).map (sF * ·)
  | [], _ => by simp [r2]
  | _ :: _, [] => by simp [r2]
  | X :: Xs, Z :: Zs => by
    simp only [List.map_cons, r2]
    rw [r2_sign sF sG hG LG LF C1 Xs Zs, headD_mul]
    congr 1
    have e : sG * LG * (sG * LG * (sF * X) - sF * LF * (sG * Zs.headD 0)) - sF * sG * C1 * (sG * Z)
        = (sG * sG) * (sF * (LG * (LG * X - LF * Zs.headD 0) - C1 * Z)) := by grind
    rw [e, hG, Int.one_mul]

theorem r2_bound (LG LF : Nat) (C1 : Int) (TX TZ : Nat) : ∀ Xs Zs : List Int,
    (∀ x ∈ Xs, x.natAbs ≤ TX) → (∀ z ∈ Zs, z.natAbs ≤ TZ) →
    ∀ e ∈ r2 LG LF C1 Xs Zs, e.natAbs ≤ LG * (LG * TX + LF * TZ) + C1.natAbs * TZ
  | [], _, _, _ => by simp [r2]
  | _ :: _, [], _, _ => by simp [r2]
  | X :: Xs, Z :: Zs, hX, hZ => by
    intro e he
    simp only [r2, List.mem_cons] at he
    rcases he with rfl | he
    · have hx := hX X (by simp)
      have hz := hZ Z (by simp)
      have hy : (Zs.headD 0).natAbs ≤ TZ := by
        cases Zs with
        | nil => simp
        | cons y ys => exact hZ y (by simp)
      have h1 := Int.natAbs_sub_le ((LG : Int) * ((LG : Int) * X - (LF : Int) * Zs.headD 0)) (C1 * Z)
      have h2 := Int.natAbs_sub_le ((LG : Int) * X) ((LF : Int) * Zs.headD 0)
      simp only [Int.natAbs_mul, Int.natAbs_natCast] at h1 h2
      have h3 : LG * (LG * X - LF * Zs.headD 0 : Int).natAbs ≤ LG * (LG * TX + LF * TZ) :=
        Nat.mul_le_mul_left _ (Nat.le_trans h2 (Nat.add_le_add (Nat.mul_le_mul_left _ hx) (Nat.mul_le_mul_left _ hy)))
      have h4 : C1.natAbs * Z.natAbs ≤ C1.natAbs * TZ := Nat.mul_le_mul_left _ hz
      omega
    · exact r2_bound LG LF C1 TX TZ Xs Zs (fun x hx => hX x (by simp [hx])) (fun z hz => hZ z (by simp [hz])) e he


/-! ## One packed step -/

/-- The packed state `s` holds the sign-normalized `F̂`, `Ĝ` (degrees `d`, `d − 1`) in lanes `(W, b)`;
`ini`: the next step is the initial one (`dm = 1`). -/
def PInv (W b d : Nat) (ini : Bool) (s : PSt) (F G : List Int) : Prop :=
  F.length = d + 1 ∧ G.length = d ∧
  (∀ x ∈ F, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int)) ∧
  (∀ x ∈ G, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int)) ∧
  1 ≤ F.headD 0 ∧ 1 ≤ G.headD 0 ∧
  (s.fv : Int) = ev ((2 ^ W : Nat) : Int) F ∧ (s.gv : Int) = ev ((2 ^ W : Nat) : Int) G ∧
  (s.lf : Int) = F.headD 0 ∧ (s.lg : Int) = G.headD 0 ∧
  (s.df1 : Int) = F.tail.headD 0 + ((2 ^ b : Nat) : Int) ∧
  (2 ≤ d → (s.dg1 : Int) = G.tail.headD 0 + ((2 ^ b : Nat) : Int)) ∧
  s.fs < 2 ∧ s.gs < 2 ∧
  (s.dm : Int) = (if ini then 1 else F.headD 0 ^ 2)

theorem sg_xor (a b : Nat) (ha : a < 2) (hb : b < 2) : sg (Nat.xor a b) = sg a * sg b := by
  rw [nxor, xor_bits a b ha hb]
  have := sg_add a b
  rw [Nat.mod_eq_of_lt ha, Nat.mod_eq_of_lt hb] at this
  exact this

theorem sg_sq (a : Nat) (ha : a < 2) : sg a * sg a = 1 := by
  have := sg_mod2 a; rwa [Nat.mod_eq_of_lt ha] at this

theorem sg_ne (a : Nat) : sg a ≠ 0 := by
  unfold sg; omega

theorem xor_lt2 (a b : Nat) (ha : a < 2) (hb : b < 2) : Nat.xor a b < 2 := by
  rw [nxor, xor_bits a b ha hb]; exact Nat.mod_lt _ (by decide)

/-- `|X₁ − X₂|` and its sign bit from truncated subtractions. -/
theorem absdiff (X1 X2 : Nat) :
    Nat.sub 1 (Nat.sub 1 (Nat.sub X2 X1)) < 2 ∧
    (X1 : Int) - X2 = sg (Nat.sub 1 (Nat.sub 1 (Nat.sub X2 X1))) * (Nat.add (Nat.sub X1 X2) (Nat.sub X2 X1) : Nat) := by
  simp only [nsub, nadd]
  unfold sg
  by_cases h : X1 < X2
  · rw [show X2 - X1 = X2 - X1 from rfl, show 1 - (1 - (X2 - X1)) = 1 by omega]
    constructor
    · omega
    · push_cast; omega
  · rw [show 1 - (1 - (X2 - X1)) = 0 by omega]
    constructor
    · omega
    · push_cast; omega

/-- Exactness from the low-bits check: `mag − dm·q ∈ [0, dm)` vanishes mod `2^k > dm`. -/
theorem lowbits_exact (mag dm q k : Nat) (hq : q = mag / dm) (hdm0 : 0 < dm) (hdm : dm < 2 ^ k)
    (h : Nat.add (Nat.sub (Nat.land mag (2 ^ k - 1)) (Nat.land (Nat.mul dm (Nat.land q (2 ^ k - 1))) (2 ^ k - 1)))
      (Nat.sub (Nat.land (Nat.mul dm (Nat.land q (2 ^ k - 1))) (2 ^ k - 1)) (Nat.land mag (2 ^ k - 1))) = 0) :
    mag = dm * q := by
  simp only [nadd, nsub, nmul, nand, Nat.and_two_pow_sub_one_eq_mod] at h
  have e : mag % 2 ^ k = dm * (q % 2 ^ k) % 2 ^ k := by omega
  rw [Nat.mul_mod, Nat.mod_mod, ← Nat.mul_mod] at e
  have hdm' := Nat.div_add_mod mag dm
  have hlt := Nat.mod_lt mag hdm0
  rw [← hq] at hdm'
  have h0 := Nat.sub_mod_eq_zero_of_mod_eq e
  rw [show mag - dm * q = mag % dm by omega, Nat.mod_eq_of_lt (by omega)] at h0
  omega


theorem dlist_mem (k : Int) : ∀ N Q : List Int, ∀ x ∈ dlist k N Q, ∃ n ∈ N, ∃ q ∈ Q, x = n - k * q
  | n :: ns, q :: qs, x, hx => by
    simp only [dlist, List.mem_cons] at hx
    rcases hx with rfl | hx
    · exact ⟨n, by simp, q, by simp, rfl⟩
    · obtain ⟨n', hn, q', hq, e⟩ := dlist_mem k ns qs x hx
      exact ⟨n', by simp [hn], q', by simp [hq], e⟩
  | [], _, x, hx => by simp [dlist] at hx
  | _ :: _, [], x, hx => by simp [dlist] at hx

theorem dlist_length (k : Int) : ∀ N Q : List Int, N.length = Q.length → (dlist k N Q).length = N.length
  | [], _, _ => by simp [dlist]
  | _ :: _, [], h => by simp at h
  | n :: ns, q :: qs, h => by simp only [dlist, List.length_cons]; rw [dlist_length k ns qs (by simpa using h)]

theorem r2_length (LG LF C1 : Int) : ∀ Xs Zs : List Int, Xs.length = Zs.length →
    (r2 LG LF C1 Xs Zs).length = Xs.length
  | [], _, _ => by simp [r2]
  | _ :: _, [], h => by simp at h
  | X :: Xs, Z :: Zs, h => by simp only [r2, List.length_cons]; rw [r2_length LG LF C1 Xs Zs (by simpa using h)]

theorem pow3_lt (b W : Nat) (hW : 3 * b + 3 ≤ W) : 8 * (2 ^ b * 2 ^ b * 2 ^ b) ≤ 2 ^ W := by
  have : 2 ^ (3 * b + 3) ≤ 2 ^ W := Nat.pow_le_pow_right (by decide) hW
  have e : 2 ^ (3 * b + 3) = 8 * (2 ^ b * 2 ^ b * 2 ^ b) := by
    rw [Nat.pow_add, show 3 * b = b + b + b by omega, Nat.pow_add, Nat.pow_add]; omega
  omega

theorem natAbs_le_of_bounds (T : Nat) (x : Int) (h : -(T : Int) ≤ x ∧ x < T) : x.natAbs ≤ T := by omega



theorem digsU_head (W u : Nat) : ∀ p, (digsU (2 ^ W - 1) u (lns W p)).headD 0 = u / 2 ^ (W * p) % 2 ^ W
  | 0 => by simp [lns, digsU]
  | p + 1 => by simp [lns, digsU, Nat.shiftRight_eq_div_pow]

theorem digsU_second (W u p : Nat) :
    (digsU (2 ^ W - 1) u (lns W (p + 1))).tail.headD 0 = u / 2 ^ (W * p) % 2 ^ W := by
  cases p <;> simp [lns, digsU, Nat.shiftRight_eq_div_pow]

theorem ofD_val (W T : Nat) (ds : List Nat) (h : ∀ d ∈ ds, d < 2 * T) :
    (ofD W ds : Int) = ev ((2 ^ W : Nat) : Int) (ds.map (fun d : Nat => (d : Int) - T)) + T * rep W ds.length := by
  have hu := undigits T ds h
  have := ofD_offs W T (ds.map (fun d : Nat => (d : Int) - T)) (fun x hx => (hu.2 x hx).1)
  rw [hu.1, List.length_map] at this
  exact this


theorem bound5 (T lg lf dm : Nat) (c : Int) (hlg : lg ≤ T) (hlf : lf ≤ T) (hdm : dm ≤ T * T)
    (hc : c.natAbs ≤ lg * T + lf * T) :
    lg * (lg * T + lf * T) + c.natAbs * T + dm * T ≤ 5 * (T * T * T) := by
  have e1 : lg * (lg * T + lf * T) ≤ T * (T * T + T * T) :=
    Nat.mul_le_mul hlg (Nat.add_le_add (Nat.mul_le_mul_right _ hlg) (Nat.mul_le_mul_right _ hlf))
  have e2 : c.natAbs * T ≤ (T * T + T * T) * T :=
    Nat.mul_le_mul_right _ (Nat.le_trans hc (Nat.add_le_add (Nat.mul_le_mul_right _ hlg) (Nat.mul_le_mul_right _ hlf)))
  have e3 : dm * T ≤ T * T * T := Nat.mul_le_mul_right _ hdm
  have f1 : T * (T * T + T * T) = 2 * (T * T * T) := by grind
  have f2 : (T * T + T * T) * T = 2 * (T * T * T) := by grind
  omega

theorem sg_natAbs (a : Nat) (ha : a < 2) : (sg a).natAbs = 1 := by
  unfold sg; rcases (by omega : a = 0 ∨ a = 1) with rfl | rfl <;> decide


theorem sg_hxor (a b : Nat) (ha : a < 2) (hb : b < 2) : sg (a ^^^ b) = sg a * sg b := sg_xor a b ha hb

theorem hxor_lt2 (a b : Nat) (ha : a < 2) (hb : b < 2) : a ^^^ b < 2 := xor_lt2 a b ha hb

theorem pstep_spec (W b d : Nat) (ini lowb : Bool) (s : PSt) (F G : List Int)
    (T m O HM m2 sb sW s1 s0 sm : Nat)
    (hT : T = 2 ^ b) (hm : m = 2 ^ W - 1) (hO : O = 2 ^ b * rep W (d - 1)) (hHM : HM = hmask W b (d - 1))
    (hm2 : m2 = 2 ^ (2 * b) - 1) (hsb : sb = b) (hsW : sW = W) (hs1 : s1 = W * (d - 1))
    (hs0 : s0 = W * (d - 2)) (hsm : sm = W * (d - 3)) (hW : 3 * b + 3 ≤ W) (hd : 2 ≤ d)
    (hI : PInv W b d ini s F G) (hbad : (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).bad = 0) :
    ∃ H, PInv W b (d - 1) false (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s) G H ∧
      ∀ fuel, normalResultantGo (fuel + 1) ini (F.map (sg s.fs * ·)) (G.map (sg s.gs * ·)) =
        if d = 2 then some (sg (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).gs * H.headD 0)
        else normalResultantGo fuel false (G.map (sg s.gs * ·))
          (H.map (sg (pstep T m O HM m2 sb sW s1 s0 sm ini lowb s).gs * ·)) := by
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, hlf, hlg, hdf1, hdg1, hfs, hgs, hdm⟩ := hI
  subst T m O HM m2 sb sW s1 s0 sm
  obtain ⟨lf, f1, xs, rfl⟩ : ∃ lf f1 xs, F = lf :: f1 :: xs := by
    match F, hFl with
    | lf :: f1 :: xs, _ => exact ⟨lf, f1, xs, rfl⟩
    | [], h => simp at h
    | [_], h => simp at h; omega
  obtain ⟨lg, zs, rfl⟩ : ∃ lg zs, G = lg :: zs := by
    match G, hGl with
    | lg :: zs, _ => exact ⟨lg, zs, rfl⟩
    | [], h => simp at h; omega
  simp only [List.length_cons] at hFl hGl
  simp only [List.headD_cons, List.tail_cons] at hF0 hG0 hlf hlg hdf1 hdg1 hdm
  have hdg1' := hdg1 hd
  simp only [pstep] at hbad ⊢
  simp only [nadd, nsub, nmul, ndiv, nmod, nand, nshr, nshl, nxor] at hbad ⊢
  generalize hP1 : s.lg * s.df1 + s.lf <<< b = P1 at hbad ⊢
  generalize hN1 : s.lf * s.dg1 + s.lg <<< b = N1 at hbad ⊢
  generalize hA : s.lg * s.lg = A at hbad ⊢
  generalize hX1 : A * s.fv = X1 at hbad ⊢
  generalize hM : (s.lf * s.lg) <<< W + P1 - N1 = M at hbad ⊢
  generalize hX2 : M * s.gv = X2 at hbad ⊢
  generalize hD2 : X2 - X1 = D2 at hbad ⊢
  generalize hmag : X1 - X2 + D2 = mag at hbad ⊢
  generalize hq : cond ini mag (mag / s.dm) = q at hbad ⊢
  generalize hu : q + 2 ^ b * rep W (d - 1) = u at hbad ⊢
  generalize hlh : u >>> (W * (d - 2)) - 2 ^ b = lh at hbad ⊢
  generalize hneg : 1 - (1 - D2) = neg at hbad ⊢
  -- the checks
  obtain ⟨hb1, hlead⟩ := Nat.add_eq_zero_iff.mp hbad
  obtain ⟨hcnd, hb2⟩ := Nat.add_eq_zero_iff.mp hb1
  obtain ⟨hmask0, hshr0⟩ := Nat.add_eq_zero_iff.mp hb2
  have hc1n : 1 - (P1 - N1 + (N1 - P1)) = 0 := by
    cases ini <;> cases lowb <;> simp only [cond] at hcnd <;> omega
  -- bounds of the digits
  have hT0 : 0 < 2 ^ b := Nat.two_pow_pos b
  have hlfb := hFb lf (by simp)
  have hf1b := hFb f1 (by simp)
  have hlgb := hGb lg (by simp)
  have hxsb : ∀ x ∈ xs, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := fun x hx => hFb x (by simp [hx])
  have hzsb : ∀ x ∈ zs, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := fun x hx => hGb x (by simp [hx])
  have hg1b : -((2 ^ b : Nat) : Int) ≤ zs.headD 0 ∧ zs.headD 0 < ((2 ^ b : Nat) : Int) := by
    cases zs with
    | nil => simp at hGl; omega
    | cons z zs' => exact hzsb z (by simp)
  have hlfn : s.lf < 2 ^ b := by have := hlfb.2; omega
  have hlgn : s.lg < 2 ^ b := by have := hlgb.2; omega
  have hdg1n : s.dg1 < 2 * 2 ^ b := by have := hg1b.2; omega
  have hdf1n : s.df1 < 2 * 2 ^ b := by have := hf1b.2; omega
  have e2b : 2 ^ (2 * b) = 2 ^ b * 2 ^ b := by rw [Nat.two_mul, Nat.pow_add]
  -- the divisor
  have hT1 : 1 ≤ 2 ^ b * 2 ^ b := Nat.mul_pos hT0 hT0
  have hdmle : s.dm ≤ 2 ^ b * 2 ^ b := by
    cases ini
    · simp only [Bool.false_eq_true, if_false] at hdm
      have : s.dm = s.lf * s.lf := by
        have : ((s.lf * s.lf : Nat) : Int) = lf ^ 2 := by push_cast; rw [hlf, Int.pow_succ, Int.pow_one]
        omega
      rw [this]; exact Nat.mul_le_mul (by omega) (by omega)
    · simp only [if_true] at hdm; omega
  -- exact division
  have hexact : mag = s.dm * q := by
    cases ini
    · cases lowb
      · simp only [cond] at hcnd hq
        have hmod : mag % s.dm = 0 := by omega
        rw [← hq]; exact (Nat.mul_div_cancel' (Nat.dvd_of_mod_eq_zero hmod)).symm
      · simp only [cond] at hcnd hq
        simp only [Bool.false_eq_true, if_false] at hdm
        have hdm' : s.dm = s.lf * s.lf := by
          have : ((s.lf * s.lf : Nat) : Int) = lf ^ 2 := by push_cast; rw [hlf, Int.pow_succ, Int.pow_one]
          omega
        apply lowbits_exact mag s.dm q (2 * b) hq.symm (by rw [hdm']; exact Nat.mul_pos (by omega) (by omega))
          (by rw [hdm', e2b]; exact Nat.mul_lt_mul_of_lt_of_lt hlfn hlfn)
        simp only [nadd, nsub, nmul, nand]; omega
    · simp only [cond] at hq
      simp only [if_true] at hdm
      have : s.dm = 1 := by omega
      rw [this, ← hq, Nat.one_mul]
  -- integer values of the step quantities
  have hP1i : (P1 : Int) = lg * (f1 + ((2 ^ b : Nat) : Int)) + lf * ((2 ^ b : Nat) : Int) := by
    rw [← hP1, Nat.shiftLeft_eq]; simp only [Int.natCast_add, Int.natCast_mul]; rw [hlg, hdf1, hlf]
  have hN1i : (N1 : Int) = lf * (zs.headD 0 + ((2 ^ b : Nat) : Int)) + lg * ((2 ^ b : Nat) : Int) := by
    rw [← hN1, Nat.shiftLeft_eq]; simp only [Int.natCast_add, Int.natCast_mul]; rw [hlg, hdg1', hlf]
  have hc1 : (P1 : Int) - N1 = lg * f1 - lf * zs.headD 0 := by rw [hP1i, hN1i]; grind
  have hc1ne : lg * f1 - lf * zs.headD 0 ≠ 0 := by rw [← hc1]; omega
  have hN1lt : N1 < 2 ^ W := by
    have h8 := pow3_lt b W hW
    have h1 : s.lf * s.dg1 ≤ 2 ^ b * (2 * 2 ^ b) := Nat.mul_le_mul (by omega) (by omega)
    have h2 : s.lg * 2 ^ b ≤ 2 ^ b * 2 ^ b := Nat.mul_le_mul (by omega) (by omega)
    have h3 : 2 ^ b * 2 ^ b ≤ 2 ^ b * 2 ^ b * 2 ^ b := Nat.le_mul_of_pos_right _ hT0
    rw [← hN1, Nat.shiftLeft_eq]
    have : 2 ^ b * (2 * 2 ^ b) = 2 * (2 ^ b * 2 ^ b) := by rw [Nat.mul_left_comm]
    omega
  have hMi : (M : Int) = lf * lg * ((2 ^ W : Nat) : Int) + (lg * f1 - lf * zs.headD 0) := by
    have hlflg : 1 ≤ s.lf * s.lg := Nat.mul_pos (by omega) (by omega)
    have : 2 ^ W ≤ s.lf * s.lg * 2 ^ W := Nat.le_mul_of_pos_left _ hlflg
    rw [← hM, Nat.shiftLeft_eq]
    rw [Int.ofNat_sub (by omega)]
    simp only [Int.natCast_add, Int.natCast_mul]
    rw [hlf, hlg, ← hc1]
    omega
  -- the numerator polynomial and its value at B
  have hlen : xs.length = zs.length := by omega
  have hX1i : (X1 : Int) = lg * lg * ev ((2 ^ W : Nat) : Int) (lf :: f1 :: xs) := by
    rw [← hX1, ← hA, Int.natCast_mul, Int.natCast_mul, hlg, hfv]
  have hX2i : (X2 : Int) = (lf * lg * ((2 ^ W : Nat) : Int) + (lg * f1 - lf * zs.headD 0)) *
      ev ((2 ^ W : Nat) : Int) (lg :: zs) := by
    rw [← hX2, Int.natCast_mul, hMi, hgv]
  have hevN : ev ((2 ^ W : Nat) : Int) (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs) = (X1 : Int) - X2 := by
    rw [ev_step _ lf f1 lg xs zs hlen, hX1i, hX2i]
  obtain ⟨hneg2, hsgn⟩ := absdiff X1 X2
  simp only [nsub, nadd] at hneg2 hsgn
  rw [hD2] at hneg2 hsgn
  rw [hmag] at hsgn
  rw [hneg] at hneg2 hsgn
  -- the new polynomial from the lane checks
  have hbW : b + 1 ≤ W := by omega
  have hL : 1 ≤ d - 1 := by omega
  obtain ⟨hdu, hdl, hdb⟩ := decode W b (d - 1) u hbW hL hmask0 hshr0
  rw [show d - 1 - 1 = d - 2 by omega] at hdu hdl hdb
  have hdb' : ∀ x ∈ digsU (2 ^ W - 1) u (lns W (d - 2)), x < 2 * 2 ^ b := by
    intro x hx; have := hdb x hx; rw [Nat.pow_succ] at this; omega
  generalize hds : digsU (2 ^ W - 1) u (lns W (d - 2)) = ds at hdu hdl hdb hdb'
  have hH := undigits (2 ^ b) ds hdb'
  have hHv := ofD_val W (2 ^ b) ds hdb'
  rw [hdu, hdl] at hHv
  generalize hHdef : ds.map (fun x : Nat => (x : Int) - ((2 ^ b : Nat) : Int)) = H at hH hHv
  have hHl : H.length = d - 1 := by rw [← hHdef, List.length_map, hdl]
  have hqv : (q : Int) = ev ((2 ^ W : Nat) : Int) H := by
    have : (u : Int) = q + ((2 ^ b : Nat) : Int) * (rep W (d - 1) : Nat) := by
      rw [← hu]; simp only [Int.natCast_add, Int.natCast_mul]
    omega
  -- the E-argument: the numerator is coefficientwise `± dm · H`
  have hN : r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs =
      H.map (fun h => (sg neg * (s.dm : Int)) * h) := by
    have hNl : (r2 lg lf (lg * f1 - lf * zs.headD 0) xs zs).length = H.length := by
      rw [r2_length _ _ _ xs zs hlen, hHl]; omega
    apply eq_map_of_ev (2 ^ W) (Nat.two_pow_pos W) _ _ H hNl
    · intro x hx
      obtain ⟨n, hn, h, hh, rfl⟩ := dlist_mem _ _ _ x hx
      have hnb := r2_bound s.lg s.lf (lg * f1 - lf * zs.headD 0) (2 ^ b) (2 ^ b) xs zs
        (fun x hx => natAbs_le_of_bounds _ x (hxsb x hx)) (fun x hx => natAbs_le_of_bounds _ x (hzsb x hx))
        n (by rw [hlg, hlf]; exact hn)
      have hhb := natAbs_le_of_bounds _ h (hH.2 h hh)
      have hc1b : (lg * f1 - lf * zs.headD 0).natAbs ≤ s.lg * 2 ^ b + s.lf * 2 ^ b := by
        have := Int.natAbs_sub_le (lg * f1) (lf * zs.headD 0)
        rw [Int.natAbs_mul, Int.natAbs_mul] at this
        have h1 : lg.natAbs = s.lg := by omega
        have h2 : lf.natAbs = s.lf := by omega
        rw [h1, h2] at this
        have := Nat.mul_le_mul_left s.lg (natAbs_le_of_bounds _ f1 hf1b)
        have := Nat.mul_le_mul_left s.lf (natAbs_le_of_bounds _ _ hg1b)
        omega
      have h5 := bound5 (2 ^ b) s.lg s.lf s.dm _ (by omega) (by omega) hdmle hc1b
      have h8 := pow3_lt b W hW
      have hk : (sg neg * (s.dm : Int) * h).natAbs ≤ s.dm * 2 ^ b := by
        rw [Int.natAbs_mul, Int.natAbs_mul, sg_natAbs neg hneg2, Int.natAbs_natCast, Nat.one_mul]
        exact Nat.mul_le_mul_left _ hhb
      have := Int.natAbs_sub_le n (sg neg * (s.dm : Int) * h)
      have hT3 : 0 < 2 ^ b * 2 ^ b * 2 ^ b := Nat.mul_pos (Nat.mul_pos hT0 hT0) hT0
      omega
    · rw [hevN, ← hqv, hsgn, hexact, Int.natCast_mul]; grind
  -- leading and second digits of H
  have hu_lt : u < 2 ^ (W * (d - 1)) := by
    rw [Nat.shiftRight_eq_div_pow] at hshr0
    exact (Nat.div_eq_zero_iff_lt (Nat.two_pow_pos _)).mp hshr0
  obtain ⟨δ0, rest, hdsc⟩ : ∃ δ0 rest, ds = δ0 :: rest := by
    cases ds with
    | nil => simp at hdl; omega
    | cons a l => exact ⟨a, l, rfl⟩
  have hδ0 : δ0 = u >>> (W * (d - 2)) := by
    have := digsU_head W u (d - 2)
    rw [hds, hdsc, List.headD_cons] at this
    rw [this, Nat.shiftRight_eq_div_pow]
    apply Nat.mod_eq_of_lt
    rw [Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add]
    rw [show W + W * (d - 2) = W * (d - 1) by
      rw [show d - 1 = (d - 2) + 1 by omega, Nat.mul_add, Nat.mul_one, Nat.add_comm]]
    exact hu_lt
  have hH0 : H.headD 0 = (δ0 : Int) - ((2 ^ b : Nat) : Int) := by
    rw [← hHdef, hdsc]; rfl
  have hlh1 : 1 ≤ lh := by omega
  have hlhi : (lh : Int) = H.headD 0 := by
    rw [hH0, hδ0]; rw [← hlh]; omega
  have hH01 : 1 ≤ H.headD 0 := by omega
  have hH1 : 2 ≤ d - 1 → ((u >>> (W * (d - 3)) &&& (2 ^ W - 1) : Nat) : Int) = H.tail.headD 0 + ((2 ^ b : Nat) : Int) := by
    intro h3
    have := digsU_second W u (d - 3)
    rw [show d - 3 + 1 = d - 2 by omega, hds] at this
    rw [Nat.and_two_pow_sub_one_eq_mod, Nat.shiftRight_eq_div_pow, ← this, ← hHdef]
    rw [hdsc] at hdl ⊢
    cases rest with
    | nil => simp at hdl; omega
    | cons δ1 rest' => simp
  have hneg' : neg < 2 := hneg2
  refine ⟨H, ?_, ?_⟩
  · -- the invariant one degree down
    simp only [PInv, List.length_cons, List.headD_cons, List.tail_cons, Bool.false_eq_true, if_false]
    refine ⟨by omega, hHl, hGb, hH.2, hG0, hH01, hgv, hqv, hlg, hlhi, hdg1', hH1, hgs,
      hxor_lt2 _ _ hfs hneg', ?_⟩
    rw [← hA, Int.natCast_mul, hlg, Int.pow_succ, Int.pow_one]
  · -- the specification's normal step
    intro fuel
    have hsF := sg_sq _ hfs
    have hsG := sg_sq _ hgs
    have hC : sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0
        = sg s.fs * sg s.gs * (lg * f1 - lf * zs.headD 0) := by rw [headD_mul]; grind
    have hR : r2 (sg s.gs * lg) (sg s.fs * lf)
        (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
        (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))
        = (H.map (fun x => sg (s.fs ^^^ neg) * x)).map (fun q => q * (s.dm : Int)) := by
      rw [hC, r2_sign _ _ hsG, hN, List.map_map, List.map_map]
      apply List.map_congr_left
      intro h _
      simp only [Function.comp_apply, sg_hxor _ _ hfs hneg']
      grind
    have hHne : H ≠ [] := by intro h; rw [h] at hH01; simp at hH01
    have hdm0 : (s.dm : Int) ≠ 0 := by
      cases ini
      · simp only [Bool.false_eq_true, if_false] at hdm; rw [hdm]; exact Int.pow_ne_zero (by omega)
      · simp only [if_true] at hdm; omega
    have hq0 : (H.map (fun x => sg (s.fs ^^^ neg) * x)).headD 0 ≠ 0 := by
      rw [headD_mul]; exact Int.mul_ne_zero (sg_ne _) (by omega)
    have hr2 : (r2 (sg s.gs * lg) (sg s.fs * lf)
        (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
        (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))).headD 0 ≠ 0 := by
      rw [hR]
      cases hH' : H.map (fun x => sg (s.fs ^^^ neg) * x) with
      | nil => rw [hH'] at hq0; simp at hq0
      | cons a l => rw [hH'] at hq0; simp only [List.map_cons, List.headD_cons] at hq0 ⊢
                    exact Int.mul_ne_zero hq0 hdm0
    have hdiv : (if ini then some (r2 (sg s.gs * lg) (sg s.fs * lf)
          (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
          (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x)))
        else exactDividePolynomial ((sg s.fs * lf) ^ 2) (r2 (sg s.gs * lg) (sg s.fs * lf)
          (sg s.gs * lg * (sg s.fs * f1) - sg s.fs * lf * (zs.map (fun x => sg s.gs * x)).headD 0)
          (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x))))
        = some (H.map (fun x => sg (s.fs ^^^ neg) * x)) := by
      rw [hR]
      cases ini
      · simp only [Bool.false_eq_true, if_false] at hdm ⊢
        rw [hdm, show (sg s.fs * lf) ^ 2 = lf ^ 2 by
          rw [Int.pow_succ, Int.pow_one, Int.pow_succ, Int.pow_one,
            show sg s.fs * lf * (sg s.fs * lf) = (sg s.fs * sg s.fs) * (lf * lf) by ac_rfl, hsF, Int.one_mul]]
        exact exactDivide_map _ (Int.pow_ne_zero (by omega)) _
      · simp only [if_true] at hdm ⊢
        rw [hdm]; simp
    have hstep := normal_step fuel ini (sg s.fs * lf) (sg s.fs * f1) (sg s.gs * lg)
      (xs.map (fun x => sg s.fs * x)) (zs.map (fun x => sg s.gs * x)) (H.map (fun x => sg (s.fs ^^^ neg) * x))
      (Int.mul_ne_zero (sg_ne _) (by omega)) (Int.mul_ne_zero (sg_ne _) (by omega))
      (by simp [hlen]) (by simp; omega)
      (by rw [hC]; exact Int.mul_ne_zero (Int.mul_ne_zero (sg_ne _) (sg_ne _)) hc1ne)
      hr2 hdiv hq0 (by simp; omega)
    simp only [List.map_cons]
    rw [hstep, List.length_map, headD_mul]
    by_cases h2 : d = 2
    · rw [if_pos (by omega), if_pos h2]
    · rw [if_neg (by omega), if_neg h2]


/-! ## Moving to wider lanes -/

theorem ev_pos (B : Nat) (hB : 0 < B) (a : Int) (as : List Int) (ha : 1 ≤ a) (h : ∀ x ∈ as, x.natAbs < B) :
    0 < ev B (a :: as) := by
  have := ev_natAbs_lt B hB as h
  rw [ev_cons]
  have h1 : ((B : Int) ^ as.length) = ((B ^ as.length : Nat) : Int) := by push_cast; rfl
  have h2 : (B ^ as.length : Int) ≤ a * (B : Int) ^ as.length := by
    rw [h1]; have := Int.mul_le_mul_of_nonneg_right ha (Int.natCast_nonneg (B ^ as.length)); omega
  omega

theorem offs_shift (T T' : Nat) (hTT : T ≤ T') (S : List Int) (h : ∀ x ∈ S, -(T : Int) ≤ x) :
    (offs T S).map (fun x => Nat.add x (T' - T)) = offs T' S := by
  simp only [offs, List.map_map]
  apply List.map_congr_left
  intro x hx
  have := h x hx
  simp only [Function.comp_apply, nadd]
  omega

/-- The packed value of a bounded list from its offset digits. -/
theorem pack_value (W T : Nat) (S : List Int) (hS : ∀ x ∈ S, -(T : Int) ≤ x ∧ x < T)
    (hl : S ≠ []) (hpos : 0 ≤ ev ((2 ^ W : Nat) : Int) S) :
    ((Nat.sub (packL (offs T S) (lns1 W (S.length - 1))) (T * rep W S.length) : Nat) : Int) =
      ev ((2 ^ W : Nat) : Int) S := by
  have hlen : (offs T S).length = S.length - 1 + 1 := by rw [offs_length]; cases S <;> simp_all
  rw [packL_ofD W _ _ hlen]
  have hv := ofD_offs W T S (fun x hx => (hS x hx).1)
  have hle : T * rep W S.length ≤ ofD W (offs T S) := by
    have : ((T * rep W S.length : Nat) : Int) ≤ (ofD W (offs T S) : Int) := by rw [Int.natCast_mul]; omega
    exact_mod_cast this
  rw [nsub, Int.ofNat_sub hle, hv, Int.natCast_mul]; omega

theorem prepack_spec (W b W' b' d : Nat) (ini : Bool) (s : PSt) (F G : List Int)
    (m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat)
    (hm : m = 2 ^ W - 1) (hOF : OF = 2 ^ b * rep W (d + 1)) (hOG : OG = 2 ^ b * rep W d)
    (hshF : shF = lns W d) (hshG : shG = lns W (d - 1)) (hpF : pF = lns1 W' d) (hpG : pG = lns1 W' (d - 1))
    (hOF' : OF' = 2 ^ b' * rep W' (d + 1)) (hOG' : OG' = 2 ^ b' * rep W' d) (hdT : dT = 2 ^ b' - 2 ^ b)
    (hbb : b ≤ b') (hW : b + 1 ≤ W) (hW' : b' + 1 ≤ W') (hd : 1 ≤ d)
    (hI : PInv W b d ini s F G) : PInv W' b' d ini (prepack m OF OG shF shG pF pG OF' OG' dT s) F G := by
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, hlf, hlg, hdf1, hdg1, hfs, hgs, hdm⟩ := hI
  subst m OF OG shF shG pF pG OF' OG' dT
  have hTT : 2 ^ b ≤ 2 ^ b' := Nat.pow_le_pow_right (by decide) hbb
  have h2T : 2 * 2 ^ b ≤ 2 ^ W := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW; rw [Nat.pow_succ] at this; omega
  have h2T' : 2 * 2 ^ b' ≤ 2 ^ W' := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW'; rw [Nat.pow_succ] at this; omega
  -- the old offset digits of F and G
  have hdigF : digsU (2 ^ W - 1) (Nat.add s.fv (2 ^ b * rep W (d + 1))) (lns W d) = offs (2 ^ b) F := by
    have hv := ofD_offs W (2 ^ b) F (fun x hx => (hFb x hx).1)
    have e : Nat.add s.fv (2 ^ b * rep W (d + 1)) = ofD W (offs (2 ^ b) F) := by
      rw [hFl] at hv
      have : ((Nat.add s.fv (2 ^ b * rep W (d + 1)) : Nat) : Int) = ((ofD W (offs (2 ^ b) F) : Nat) : Int) := by
        rw [hv, nadd, Int.natCast_add, Int.natCast_mul, hfv]
      exact_mod_cast this
    rw [e]
    exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ F hFb x hx) h2T) d (by rw [offs_length, hFl])
  have hdigG : digsU (2 ^ W - 1) (Nat.add s.gv (2 ^ b * rep W d)) (lns W (d - 1)) = offs (2 ^ b) G := by
    have hv := ofD_offs W (2 ^ b) G (fun x hx => (hGb x hx).1)
    have e : Nat.add s.gv (2 ^ b * rep W d) = ofD W (offs (2 ^ b) G) := by
      rw [hGl] at hv
      have : ((Nat.add s.gv (2 ^ b * rep W d) : Nat) : Int) = ((ofD W (offs (2 ^ b) G) : Nat) : Int) := by
        rw [hv, nadd, Int.natCast_add, Int.natCast_mul, hgv]
      exact_mod_cast this
    rw [e]
    exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ G hGb x hx) h2T) (d - 1)
      (by rw [offs_length, hGl]; omega)
  have hFb' : ∀ x ∈ F, -((2 ^ b' : Nat) : Int) ≤ x ∧ x < ((2 ^ b' : Nat) : Int) := by
    intro x hx; have := hFb x hx; omega
  have hGb' : ∀ x ∈ G, -((2 ^ b' : Nat) : Int) ≤ x ∧ x < ((2 ^ b' : Nat) : Int) := by
    intro x hx; have := hGb x hx; omega
  simp only [prepack, hdigF, hdigG, offs_shift _ _ hTT F (fun x hx => (hFb x hx).1),
    offs_shift _ _ hTT G (fun x hx => (hGb x hx).1), PInv]
  obtain ⟨f0, ft, rfl⟩ : ∃ f0 ft, F = f0 :: ft := by
    cases F with
    | nil => simp at hFl
    | cons a l => exact ⟨a, l, rfl⟩
  obtain ⟨g0, gt, rfl⟩ : ∃ g0 gt, G = g0 :: gt := by
    cases G with
    | nil => simp at hGl; omega
    | cons a l => exact ⟨a, l, rfl⟩
  have hBpos : 0 < 2 ^ W' := Nat.two_pow_pos W'
  have hevF : 0 ≤ ev ((2 ^ W' : Nat) : Int) (f0 :: ft) := Int.le_of_lt (ev_pos _ hBpos f0 ft hF0 (by
    intro x hx; have := hFb' x (by simp [hx]); omega))
  have hevG : 0 ≤ ev ((2 ^ W' : Nat) : Int) (g0 :: gt) := Int.le_of_lt (ev_pos _ hBpos g0 gt hG0 (by
    intro x hx; have := hGb' x (by simp [hx]); omega))
  have hpF := pack_value W' (2 ^ b') (f0 :: ft) hFb' (by simp) hevF
  have hpG := pack_value W' (2 ^ b') (g0 :: gt) hGb' (by simp) hevG
  simp only [List.length_cons] at hFl hGl hpF hpG
  rw [show ft.length + 1 - 1 = d by omega] at hpF
  rw [show gt.length + 1 - 1 = d - 1 by omega, show gt.length + 1 = d by omega] at hpG
  rw [show ft.length + 1 = d + 1 by omega] at hpF
  refine ⟨by simp; omega, by simp; omega, hFb', hGb', hF0, hG0, ?_, ?_, hlf, hlg, ?_, ?_, hfs, hgs, hdm⟩
  · exact hpF
  · exact hpG
  · simp only [offs, List.map_cons, List.tail_cons]
    cases ft with
    | nil => simp at hFl; omega
    | cons f1 fs => simp only [List.map_cons, List.headD_cons]; have := hFb (f1) (by simp); omega
  · intro h2
    simp only [offs, List.map_cons, List.tail_cons]
    cases gt with
    | nil => simp at hGl; omega
    | cons g1 gs => simp only [List.map_cons, List.headD_cons]; have := hGb g1 (by simp); omega


/-! ## A whole packed run -/

/-- The lane constants of one step. -/
def stepOK (W b dh T m O HM m2 sb sW s1 s0 sm : Nat) : Bool :=
  T == 2 ^ b && m == 2 ^ W - 1 && O == 2 ^ b * rep W (dh + 1) && HM == hmask W b (dh + 1) &&
  m2 == 2 ^ (2 * b) - 1 && sb == b && sW == W && s1 == W * (dh + 1) && s0 == W * dh &&
  sm == W * (dh - 1) && decide (3 * b + 3 ≤ W)

/-- The lane constants of one repacking at degree `d`. -/
def repackOK (W b W' b' d m OF OG : Nat) (shF shG pF pG : List Nat) (OF' OG' dT : Nat) : Bool :=
  m == 2 ^ W - 1 && OF == 2 ^ b * rep W (d + 1) && OG == 2 ^ b * rep W d && shF == lns W d &&
  shG == lns W (d - 1) && pF == lns1 W' d && pG == lns1 W' (d - 1) && OF' == 2 ^ b' * rep W' (d + 1) &&
  OG' == 2 ^ b' * rep W' d && dT == 2 ^ b' - 2 ^ b && decide (b ≤ b') && decide (b + 1 ≤ W) &&
  decide (3 * b' + 3 ≤ W') && decide (1 ≤ d)

/-- A run is well formed from lanes `(W, b)` at degree `d`: each act matches the current lanes and
degree; nothing follows the step to degree 0. -/
def actsOK : Nat → Nat → Nat → Bool → List PAct → Bool
  | _, _, _, _, [] => true
  | W, b, d, ini, .step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first _ :: as =>
      W1 == W && b1 == b && dh + 2 == d && first == ini && stepOK W b dh T m O HM m2 sb sW s1 s0 sm &&
      (if d = 2 then as.isEmpty else actsOK W b (d - 1) false as)
  | W, b, d, ini, .repack W1 b1 W' b' d1 m OF OG shF shG pF pG OF' OG' dT :: as =>
      W1 == W && b1 == b && d1 == d && repackOK W b W' b' d m OF OG shF shG pF pG OF' OG' dT &&
      actsOK W' b' d ini as

def nsteps : List PAct → Nat
  | [] => 0
  | .step .. :: as => nsteps as + 1
  | .repack .. :: as => nsteps as

/-- Lanes and degree after a run. -/
def aEnd : Nat → Nat → Nat → List PAct → Nat × Nat × Nat
  | W, b, d, [] => (W, b, d)
  | W, b, d, .step .. :: as => aEnd W b (d - 1) as
  | _, _, d, .repack _ _ W' b' _ _ _ _ _ _ _ _ _ _ _ :: as => aEnd W' b' d as

theorem pact_bad_le (a : PAct) (s : PSt) : s.bad ≤ (pact a s).bad := by
  cases a with
  | step W b dh T m O HM m2 sb sW s1 s0 sm first lowb =>
    simp only [pact, pstep]
    cases first <;> cases lowb <;> simp only [cond, nadd] <;> omega
  | repack => simp [pact, prepack]

theorem prun_bad_le : ∀ (acts : List PAct) (s : PSt), s.bad ≤ (prun acts s).bad
  | [], _ => Nat.le_refl _
  | a :: as, s => Nat.le_trans (pact_bad_le a s) (prun_bad_le as (pact a s))

theorem aEnd_d_of_nsteps : ∀ (as : List PAct) (W b d : Nat), nsteps as = 0 → (aEnd W b d as).2.2 = d
  | [], _, _, _, _ => rfl
  | .step .. :: _, _, _, _, h => by simp [nsteps] at h
  | .repack _ _ W' b' _ _ _ _ _ _ _ _ _ _ _ :: as, _, _, d, h => by
    simp only [nsteps] at h; simp only [aEnd]; exact aEnd_d_of_nsteps as W' b' d h

theorem pstep_fs (T m O HM m2 sb sW s1 s0 sm : Nat) (first lowb : Bool) (s : PSt) :
    (pstep T m O HM m2 sb sW s1 s0 sm first lowb s).fs = s.gs := rfl

theorem prun_spec : ∀ (acts : List PAct) (W b d : Nat) (ini : Bool) (s : PSt) (F G : List Int),
    actsOK W b d ini acts = true → PInv W b d ini s F G → (prun acts s).bad = 0 →
    ∃ F' G', PInv (aEnd W b d acts).1 (aEnd W b d acts).2.1 (aEnd W b d acts).2.2
        (ini && nsteps acts == 0) (prun acts s) F' G' ∧
      ∀ fuel, normalResultantGo (fuel + nsteps acts) ini (F.map (sg s.fs * ·)) (G.map (sg s.gs * ·)) =
        if (aEnd W b d acts).2.2 = 1 ∧ 0 < nsteps acts then some (sg (prun acts s).gs * G'.headD 0)
        else normalResultantGo fuel (ini && nsteps acts == 0) (F'.map (sg (prun acts s).fs * ·))
          (G'.map (sg (prun acts s).gs * ·))
  | [], W, b, d, ini, s, F, G, _, hI, _ => by
    refine ⟨F, G, ?_, ?_⟩
    · simpa [aEnd, nsteps, prun] using hI
    · intro fuel; simp [aEnd, nsteps, prun]
  | .step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as, W, b, d, ini, s, F, G, hok, hI, hbad => by
    simp only [actsOK, Bool.and_eq_true, beq_iff_eq] at hok
    obtain ⟨⟨⟨⟨⟨rfl, rfl⟩, hdh⟩, rfl⟩, hst⟩, hrest⟩ := hok
    simp only [stepOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hst
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨hT, hm⟩, hO⟩, hHM⟩, hm2⟩, hsb⟩, hsW⟩, hs1⟩, hs0⟩, hsm⟩, hW⟩ := hst
    have hd2 : 2 ≤ d := by omega
    have hbad1 : (pstep T m O HM m2 sb sW s1 s0 sm first lowb s).bad = 0 := by
      have := prun_bad_le as (pact (.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb) s)
      simp only [prun, pact] at hbad this; omega
    obtain ⟨H, hI', hspec⟩ := pstep_spec W1 b1 d first lowb s F G T m O HM m2 sb sW s1 s0 sm hT hm
      (by rw [hO]; congr 2; omega) (by rw [hHM]; congr 1; omega) hm2 hsb hsW (by rw [hs1]; congr 1; omega)
      (by rw [hs0]; congr 1; omega) (by rw [hsm]; congr 1; omega) hW hd2 hI hbad1
    by_cases hd : d = 2
    · -- the last step
      rw [if_pos hd] at hrest
      cases as with
      | cons _ _ => simp at hrest
      | nil =>
        refine ⟨G, H, ?_, ?_⟩
        · simpa [aEnd, nsteps, prun, pact] using hI'
        · intro fuel
          have := hspec fuel
          rw [if_pos hd] at this
          have hc : (aEnd W1 b1 d [PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb]).2.2 = 1 ∧
              0 < nsteps [PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb] := by
            simp [aEnd, nsteps]; omega
          rw [if_pos hc]
          simpa [nsteps, prun, pact] using this
    · rw [if_neg hd] at hrest
      have hbad2 : (prun as (pstep T m O HM m2 sb sW s1 s0 sm first lowb s)).bad = 0 := by
        simpa [prun, pact] using hbad
      obtain ⟨F', G', hI'', hspec'⟩ := prun_spec as W1 b1 (d - 1) false _ G H hrest hI' hbad2
      refine ⟨F', G', ?_, ?_⟩
      · simpa [aEnd, nsteps, prun, pact] using hI''
      · intro fuel
        have h1 := hspec (fuel + nsteps as)
        rw [if_neg hd] at h1
        have h2 := hspec' fuel
        rw [pstep_fs] at h2
        have e1 : nsteps (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) = nsteps as + 1 := rfl
        have e2 : aEnd W1 b1 d (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) =
            aEnd W1 b1 (d - 1) as := rfl
        have e3 : prun (PAct.step W1 b1 dh T m O HM m2 sb sW s1 s0 sm first lowb :: as) s =
            prun as (pstep T m O HM m2 sb sW s1 s0 sm first lowb s) := rfl
        rw [e1, e2, e3, show fuel + (nsteps as + 1) = fuel + nsteps as + 1 by omega, h1, h2]
        by_cases h0 : 0 < nsteps as
        · have hc : ((aEnd W1 b1 (d - 1) as).2.2 = 1 ∧ 0 < nsteps as) ↔
              ((aEnd W1 b1 (d - 1) as).2.2 = 1 ∧ 0 < nsteps as + 1) := by omega
          by_cases hh : (aEnd W1 b1 (d - 1) as).2.2 = 1
          · rw [if_pos ⟨hh, h0⟩, if_pos ⟨hh, by omega⟩]
          · rw [if_neg (by omega), if_neg (by omega)]
            simp [show (nsteps as == 0) = false by simp; omega]
        · have h00 : nsteps as = 0 := by omega
          have hend := aEnd_d_of_nsteps as W1 b1 (d - 1) h00
          rw [if_neg (by omega), if_neg (by omega)]
          simp [h00]
  | .repack W1 b1 W' b' d1 m OF OG shF shG pF pG OF' OG' dT :: as, W, b, d, ini, s, F, G, hok, hI, hbad => by
    simp only [actsOK, Bool.and_eq_true, beq_iff_eq] at hok
    obtain ⟨⟨⟨⟨rfl, rfl⟩, rfl⟩, hrp⟩, hrest⟩ := hok
    simp only [repackOK, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hrp
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨⟨hm, hOF⟩, hOG⟩, hshF⟩, hshG⟩, hpF⟩, hpG⟩, hOF'⟩, hOG'⟩, hdT⟩, hbb⟩, hbW⟩, hW'⟩, hd1⟩ := hrp
    have hI' := prepack_spec W1 b1 W' b' d1 ini s F G m OF OG shF shG pF pG OF' OG' dT hm hOF hOG hshF hshG
      hpF hpG hOF' hOG' hdT hbb hbW (by omega) hd1 hI
    have hbad2 : (prun as (prepack m OF OG shF shG pF pG OF' OG' dT s)).bad = 0 := by
      simpa [prun, pact] using hbad
    obtain ⟨F', G', hI'', hspec'⟩ := prun_spec as W' b' d1 ini _ F G hrest hI' hbad2
    refine ⟨F', G', by simpa [aEnd, nsteps, prun, pact] using hI'', ?_⟩
    intro fuel
    have := hspec' fuel
    exact this


/-! ## The input stage -/

/-- Derivative coefficients `k·a` for factors `ks` (the last value has factor 1). -/
def derA : List Nat → List Int → List Int
  | [], [a] => [a]
  | k :: ks, a :: as => (k : Int) * a :: derA ks as
  | _, _ => []

theorem derDigs_offs (T : Nat) : ∀ (ks : List Nat) (as : List Int), as.length = ks.length + 1 →
    (∀ k ∈ ks, 1 ≤ k) → (∀ a ∈ as, -(T : Int) ≤ a) → (∀ x ∈ derA ks as, -(T : Int) ≤ x) →
    derDigs (offs T as) ks (ks.map (fun k => (k - 1) * T)) = offs T (derA ks as)
  | [], [a], _, _, _, _ => by simp [offs, derDigs, derA]
  | [], [], h, _, _, _ => by simp at h
  | [], _ :: _ :: _, h, _, _, _ => by simp at h
  | k :: ks, [], h, _, _, _ => by simp at h
  | k :: ks, [a], h, _, _, _ => by simp at h
  | k :: ks, a :: e :: as, h, hk, ha, hx => by
    have ih := derDigs_offs T ks (e :: as) (by simpa using h) (fun k' hk' => hk k' (by simp [hk']))
      (fun a' ha' => ha a' (by simp [ha'])) (fun x hx' => hx x (by simp [derA, hx']))
    simp only [offs, List.map_cons] at ih ⊢
    simp only [derDigs, derA, List.map_cons]
    rw [ih]
    congr 1
    have h1 : 1 ≤ k := hk k (by simp)
    have h2 : -(T : Int) ≤ a := ha a (by simp)
    have h3 : -(T : Int) ≤ (k : Int) * a := hx _ (by simp [derA])
    simp only [nsub, nmul]
    have e1 : ((a + T).toNat : Int) = a + T := Int.toNat_of_nonneg (by omega)
    have e2 : ((((a + T).toNat * k - (k - 1) * T : Nat)) : Int) = (k : Int) * a + T := by
      rw [Int.ofNat_sub (by
        have : (((k - 1) * T : Nat) : Int) ≤ (((a + T).toNat * k : Nat) : Int) := by
          rw [Int.natCast_mul, Int.natCast_mul, e1, Int.ofNat_sub h1]; push_cast
          have : (k : Int) * a + T ≥ 0 := by omega
          grind
        exact_mod_cast this)]
      rw [Int.natCast_mul, Int.natCast_mul, e1, Int.ofNat_sub h1]; push_cast; grind
    omega

theorem inDig_eq (T x : Nat) (h0 : (zdec x).natAbs ≤ T) : inDig T x = (zdec x + T).toNat := by
  have h := h0
  unfold inDig zdec at *
  simp only [nsub, nadd, nmul, nshl, nshr, nand, Nat.shiftLeft_eq, Nat.shiftRight_eq_div_pow,
    Nat.and_one_is_mod, Nat.pow_one] at *
  split at h <;> rename_i hx
  · rw [if_pos hx, hx]; simp at h ⊢; omega
  · rw [if_neg hx, show x % 2 = 0 by omega]; simp at h ⊢; omega


theorem derA_mem : ∀ (ks : List Nat) (as : List Int), ∀ x ∈ derA ks as, ∃ k a, (k = 1 ∨ k ∈ ks) ∧ a ∈ as ∧ x = (k : Int) * a
  | [], [a], x, hx => by simp [derA] at hx; exact ⟨1, a, Or.inl rfl, by simp, by simp [hx]⟩
  | [], [], x, hx => by simp [derA] at hx
  | [], _ :: _ :: _, x, hx => by simp [derA] at hx
  | _ :: _, [], x, hx => by simp [derA] at hx
  | k :: ks, a :: as, x, hx => by
    simp only [derA, List.mem_cons] at hx
    rcases hx with rfl | hx
    · exact ⟨k, a, Or.inr (by simp), by simp, rfl⟩
    · obtain ⟨k', a', hk', ha', e⟩ := derA_mem ks as x hx
      exact ⟨k', a', by rcases hk' with h | h <;> simp [h], by simp [ha'], e⟩

theorem derA_length : ∀ (ks : List Nat) (as : List Int), as.length = ks.length + 1 → (derA ks as).length = as.length
  | [], [a], _ => rfl
  | [], [], h => by simp at h
  | [], _ :: _ :: _, h => by simp at h
  | _ :: _, [], h => by simp at h
  | k :: ks, a :: as, h => by simp only [derA, List.length_cons]; rw [derA_length ks as (by simpa using h)]

theorem pinit_spec (W b : Nat) (xs : List Nat) (T l0 g0 : Nat) (shF shG ks kTs : List Nat) (O25 O24 : Nat)
    (hT : T = 2 ^ b) (hl0 : l0 = 1 + 2 ^ b) (hg0 : g0 = 24 + 2 ^ b) (hshF : shF = lns1 W 24)
    (hshG : shG = lns1 W 23) (hks : ks = [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    (hkTs : kTs = ks.map (fun k => (k - 1) * 2 ^ b)) (hO25 : O25 = 2 ^ b * rep W 25)
    (hO24 : O24 = 2 ^ b * rep W 24) (h24 : 24 < 2 ^ b) (hW : b + 1 ≤ W) (hxs : xs.length = 24)
    (hbnd : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ b) :
    PInv W b 24 true (pinit T l0 g0 shF shG ks kTs O25 O24 xs) (1 :: xs.map zdec)
      (24 :: derA ks ((xs.take 23).map zdec)) := by
  subst T l0 g0 shF shG kTs O25 O24
  have hAb : ∀ a ∈ xs.map zdec, -((2 ^ b : Nat) : Int) ≤ a ∧ a < ((2 ^ b : Nat) : Int) := by
    intro a ha; simp only [List.mem_map] at ha; obtain ⟨x, hx, rfl⟩ := ha; have := hbnd x hx; omega
  have hds : xs.map (inDig (2 ^ b)) = offs (2 ^ b) (xs.map zdec) := by
    simp only [offs, List.map_map]; apply List.map_congr_left; intro x hx
    simp only [Function.comp_apply]; exact inDig_eq _ x (by have := hbnd x hx; omega)
  have hFdig : (1 + 2 ^ b) :: xs.map (inDig (2 ^ b)) = offs (2 ^ b) (1 :: xs.map zdec) := by
    rw [hds]; simp only [offs, List.map_cons]; congr 1
  have hderb : ∀ x ∈ derA ks ((xs.take 23).map zdec), -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx
    obtain ⟨k, a, hk, ha, rfl⟩ := derA_mem _ _ x hx
    have hk24 : k ≤ 24 := by rcases hk with rfl | hk; · omega
                             rw [hks] at hk; simp at hk; omega
    simp only [List.mem_map] at ha
    obtain ⟨y, hy, rfl⟩ := ha
    have := hbnd y (List.mem_of_mem_take hy)
    have h1 : ((k : Int) * zdec y).natAbs ≤ 24 * (zdec y).natAbs := by
      rw [Int.natAbs_mul, Int.natAbs_natCast]; exact Nat.mul_le_mul_right _ hk24
    omega
  have hA23 : ∀ a ∈ (xs.take 23).map zdec, -((2 ^ b : Nat) : Int) ≤ a := by
    intro a ha
    simp only [List.mem_map] at ha
    obtain ⟨x, hx, rfl⟩ := ha
    exact (hAb _ (List.mem_map_of_mem (List.mem_of_mem_take hx))).1
  have hl23 : ((xs.take 23).map zdec).length = ks.length + 1 := by rw [hks]; simp [hxs]
  have hGdig : (24 + 2 ^ b) :: derDigs ((xs.map (inDig (2 ^ b))).take 23) ks (ks.map (fun k => (k - 1) * 2 ^ b))
      = offs (2 ^ b) (24 :: derA ks ((xs.take 23).map zdec)) := by
    rw [hds, show (offs (2 ^ b) (xs.map zdec)).take 23 = offs (2 ^ b) ((xs.take 23).map zdec) by
      simp [offs, List.map_take]]
    rw [derDigs_offs (2 ^ b) ks _ hl23 (by rw [hks]; decide) hA23 (fun x hx => (hderb x hx).1)]
    simp only [offs, List.map_cons]; congr 1
  have hFl : (1 :: xs.map zdec).length = 25 := by simp [hxs]
  have hGl : (24 :: derA ks ((xs.take 23).map zdec)).length = 24 := by
    simp only [List.length_cons]; rw [derA_length _ _ hl23]; simp [hxs]
  have hFb : ∀ x ∈ 1 :: xs.map zdec, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx; simp only [List.mem_cons] at hx; rcases hx with rfl | hx
    · omega
    · exact hAb x hx
  have hGb : ∀ x ∈ 24 :: derA ks ((xs.take 23).map zdec), -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int) := by
    intro x hx; simp only [List.mem_cons] at hx; rcases hx with rfl | hx
    · omega
    · exact hderb x hx
  have hB := Nat.two_pow_pos W
  have hevF := ev_pos _ hB 1 (xs.map zdec) (by omega) (by
    intro x hx; have := hAb x hx; have := Nat.pow_lt_pow_right (show 1 < 2 by decide) (show b < W by omega); omega)
  have hevG := ev_pos _ hB 24 (derA ks ((xs.take 23).map zdec)) (by omega) (by
    intro x hx; have := hderb x hx; have := Nat.pow_lt_pow_right (show 1 < 2 by decide) (show b < W by omega); omega)
  have hpF := pack_value W (2 ^ b) (1 :: xs.map zdec) hFb (by simp) (Int.le_of_lt hevF)
  have hpG := pack_value W (2 ^ b) (24 :: derA ks ((xs.take 23).map zdec)) hGb (by simp) (Int.le_of_lt hevG)
  rw [hFl] at hpF; rw [hGl] at hpG
  have hgs : derDigs ((xs.map (inDig (2 ^ b))).take 23) ks (ks.map (fun k => (k - 1) * 2 ^ b))
      = offs (2 ^ b) (derA ks ((xs.take 23).map zdec)) := by
    have := hGdig; simp only [offs, List.map_cons] at this ⊢; exact (List.cons.inj this).2
  simp only [pinit, PInv]
  rw [hFdig, hGdig, hgs, hds]
  refine ⟨hFl, hGl, hFb, hGb, by simp, by simp, hpF, hpG, by simp, by simp, ?_, ?_, by decide, by decide, by simp⟩
  · simp only [List.tail_cons]
    cases xs with
    | nil => simp at hxs
    | cons x xs' => simp only [offs, List.map_cons, List.headD_cons]; have := hAb (zdec x) (by simp); omega
  · intro _
    simp only [List.tail_cons]
    cases hd : derA ks ((xs.take 23).map zdec) with
    | nil => rw [hd] at hGl; simp at hGl
    | cons y ys => simp only [offs, List.map_cons, List.headD_cons]; have := hderb y (by rw [hd]; simp); omega


/-! ## Size of the generated coefficients -/

theorem cnc_bound (w words word : Nat) (hw : 1 ≤ w) (hww : w ≤ 64 * words) (hword : word < 2 ^ (64 * words)) :
    (centeredNonzeroCoeff w words word).natAbs ≤ 2 ^ (w - 1) := by
  have hv : word >>> (64 * words - w) < 2 ^ w := by
    rw [Nat.shiftRight_eq_div_pow, Nat.div_lt_iff_lt_mul (Nat.two_pow_pos _), ← Nat.pow_add,
      show w + (64 * words - w) = 64 * words by omega]
    exact hword
  have e : 2 ^ w = 2 * 2 ^ (w - 1) := by
    rw [← Nat.pow_succ']; congr 1; omega
  have hp1 : 1 ≤ 2 ^ (w - 1) := Nat.one_le_two_pow
  unfold centeredNonzeroCoeff
  simp only [Int.ofNat_eq_natCast]
  generalize word >>> (64 * words - w) = v at *
  generalize 2 ^ (w - 1) = p at *
  split
  · simp; omega
  · omega

theorem width_bounds (k i : Nat) (hk : 2 ≤ k) : 2 ≤ coefficientWidth k i ∧ coefficientWidth k i ≤ k := by
  unfold coefficientWidth clampWidth
  split <;> simp only <;> omega

theorem coeffs_bound (k : Nat) (hk : 2 ≤ k) : ∀ count index state,
    ∀ a ∈ coefficientsFrom count k index state, a.natAbs ≤ 2 ^ (k - 1)
  | 0, _, _ => by simp [coefficientsFrom]
  | count + 1, index, state => by
    intro a ha
    simp only [coefficientsFrom, List.mem_cons] at ha
    rcases ha with rfl | ha
    · obtain ⟨h2, hk'⟩ := width_bounds k index hk
      have hwords : 1 ≤ (coefficientWidth k index + 63) / 64 := by omega
      have hlt := collect_lt ((coefficientWidth k index + 63) / 64) 0 state
      rcases hlt with hlt | hlt
      · rw [Nat.zero_add] at hlt
        have := cnc_bound (coefficientWidth k index) ((coefficientWidth k index + 63) / 64)
          (collectCoeffWord ((coefficientWidth k index + 63) / 64) 0 state).1 (by omega) (by omega) hlt
        exact Nat.le_trans this (Nat.pow_le_pow_right (by decide) (by omega))
      · omega
    · exact coeffs_bound k hk count (index + 1) _ a ha

theorem polyOf_bound (n : Nat) : ∀ a ∈ polyOf n, a.natAbs ≤ 2 ^ (kbitsOf n - 1) := by
  have hk : 2 ≤ kbitsOf n := by unfold kbitsOf; split <;> decide
  intro a ha
  simp only [polyOf, List.mem_cons] at ha
  rcases ha with rfl | ha
  · simp; exact Nat.one_le_two_pow
  · exact coeffs_bound _ hk 24 1 _ a ha


/-! ## Reading off results -/

theorem zdec_res (v s : Nat) (hs : s < 2) : zdec (Nat.add (Nat.shiftLeft v 1) s) = sg s * v := by
  unfold zdec sg
  simp only [nadd, nshl, Nat.shiftLeft_eq, Nat.pow_one]
  rcases (by omega : s = 0 ∨ s = 1) with rfl | rfl
  · rw [if_neg (by omega)]; simp
  · rw [if_pos (by omega)]; simp; omega

theorem zdig_val (T s : Nat) (x : Int) (hs : s < 2) (hx : -(T : Int) ≤ x) :
    zdec (zdig T s (x + (T : Int)).toNat) = sg s * x := by
  unfold zdig zdec sg
  simp only [nadd, nsub, nshl, nxor, Nat.shiftLeft_eq, Nat.pow_one]
  generalize hd : (x + (T : Int)).toNat = δ
  have hδ : (δ : Int) = x + T := by rw [← hd]; exact Int.toNat_of_nonneg (by omega)
  have hn : 1 - (1 - (T - δ)) < 2 := by omega
  rw [xor_bits _ _ hn hs]
  rcases (by omega : s = 0 ∨ s = 1) with rfl | rfl <;> by_cases hneg : δ < T
  · rw [show 1 - (1 - (T - δ)) = 1 by omega]; rw [if_pos (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 0 by omega]; rw [if_neg (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 1 by omega]; rw [if_neg (by omega)]; push_cast; omega
  · rw [show 1 - (1 - (T - δ)) = 0 by omega]; rw [if_pos (by omega)]; push_cast; omega

theorem unpackT_spec (W b d : Nat) (T m O : Nat) (shs : List Nat) (v sb : Nat) (S : List Int)
    (hT : T = 2 ^ b) (hm : m = 2 ^ W - 1) (hO : O = 2 ^ b * rep W (d + 1)) (hshs : shs = lns W d)
    (hW : b + 1 ≤ W) (hS : ∀ x ∈ S, -((2 ^ b : Nat) : Int) ≤ x ∧ x < ((2 ^ b : Nat) : Int))
    (hl : S.length = d + 1) (hv : (v : Int) = ev ((2 ^ W : Nat) : Int) S) (hs : sb < 2) :
    (unpackT T m O shs v sb).map zdec = S.map (sg sb * ·) ∧ (unpackT T m O shs v sb).length = d + 1 := by
  subst T m O shs
  have h2T : 2 * 2 ^ b ≤ 2 ^ W := by
    have := Nat.pow_le_pow_right (show 0 < 2 by decide) hW; rw [Nat.pow_succ] at this; omega
  have hval := ofD_offs W (2 ^ b) S (fun x hx => (hS x hx).1)
  have e : Nat.add v (2 ^ b * rep W (d + 1)) = ofD W (offs (2 ^ b) S) := by
    rw [hl] at hval
    have : ((Nat.add v (2 ^ b * rep W (d + 1)) : Nat) : Int) = ((ofD W (offs (2 ^ b) S) : Nat) : Int) := by
      rw [hval, nadd, Int.natCast_add, Int.natCast_mul, hv]
    exact_mod_cast this
  have hdig : digsU (2 ^ W - 1) (Nat.add v (2 ^ b * rep W (d + 1))) (lns W d) = offs (2 ^ b) S := by
    rw [e]; exact digsU_ofD W _ (fun x hx => Nat.lt_of_lt_of_le (offs_lt _ S hS x hx) h2T) d (by rw [offs_length, hl])
  unfold unpackT
  rw [hdig]
  refine ⟨?_, by simp [offs, hl]⟩
  simp only [offs, List.map_map]
  apply List.map_congr_left
  intro x hx
  exact zdig_val _ _ x hs (hS x hx).1

theorem derivHL_eq (a1 a2 a3 a4 a5 a6 a7 a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18 a19 a20 a21 a22 a23 a24 : Int) :
    derivHL [1, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20, a21, a22, a23, a24]
      = 24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20, a21, a22, a23] := by
  simp [derivHL, derA, List.range, List.range.loop]

/-- The specification's normal resultant from the normal run started at `P`, `P'`. -/
theorem normalResultant_of_go (P : List Int) (hP : P.length = 25) (h1 : P.headD 0 = 1)
    (r : Option Int) (h : normalResultantGo 25 true P (derivHL P) = r) : normalResultant P (derivHL P) = r := by
  obtain ⟨p0, ps, rfl⟩ : ∃ p0 ps, P = p0 :: ps := by
    cases P with
    | nil => simp at hP
    | cons a l => exact ⟨a, l, rfl⟩
  simp only [List.headD_cons] at h1
  subst h1
  have hd : derivHL (1 :: ps) = 24 * 1 :: (derivHL (1 :: ps)).tail := by
    simp [derivHL, List.length_cons] at hP ⊢
    rw [hP]; simp [List.range, List.range.loop]
  have hdl : (derivHL (1 :: ps)).length = 24 := by simp [derivHL]; simpa using hP
  unfold normalResultant
  rw [trim_cons 1 ps (by decide), hd, trim_cons _ _ (by decide)]
  rw [← hd]
  simp only [List.length_cons, hdl]
  have hl : ps.length = 24 := by simpa using hP
  have hne : (derivHL (1 :: ps)).isEmpty = false := by
    cases hq : derivHL (1 :: ps) with
    | nil => rw [hq] at hdl; simp at hdl
    | cons _ _ => rfl
  rw [hne, hl]
  exact h


/-! ## Whole runs -/

theorem map_one_mul (l : List Int) : l.map (sg 0 * ·) = l := by
  conv => rhs; rw [← List.map_id l]
  apply List.map_congr_left; intro x _; simp [sg]

/-- All 23 steps packed. -/
theorem full_run_spec (acts : List PAct) (W b : Nat) (s0 : PSt) (F G : List Int) (Wend bend : Nat)
    (hok : actsOK W b 24 true acts = true) (hend : aEnd W b 24 acts = (Wend, bend, 1)) (hn : nsteps acts = 23)
    (hI : PInv W b 24 true s0 F G) (hfs : s0.fs = 0) (hgs : s0.gs = 0) (hbad : (prun acts s0).bad = 0) :
    normalResultantGo 25 true F G = some (zdec (Nat.add (Nat.shiftLeft (prun acts s0).gv 1) (prun acts s0).gs)) := by
  obtain ⟨F', G', hI', hsp⟩ := prun_spec acts W b 24 true s0 F G hok hI hbad
  have h := hsp 2
  rw [hend, hn, hfs, hgs, map_one_mul, map_one_mul] at h
  rw [hend] at hI'
  dsimp only at hI' h
  rw [if_pos ⟨rfl, by decide⟩] at h
  rw [show (2 + 23 : Nat) = 25 from rfl] at h
  rw [h]
  obtain ⟨_, hGl, _, _, _, _, _, hgv, _, _, _, _, _, hgs', _⟩ := hI'
  obtain ⟨g, rfl⟩ : ∃ g, G' = [g] := by
    match G', hGl with
    | [g], _ => exact ⟨g, rfl⟩
  simp only [ev, List.length_nil, Int.pow_zero, Int.mul_one, Int.add_zero] at hgv
  rw [zdec_res _ _ hgs', hgv]
  rfl

/-- A packed prefix ending at degree `dend`, then `k = dend − 1` encoded v7 steps. -/
theorem hyb_run_spec (acts : List PAct) (W b : Nat) (s0 : PSt) (F G : List Int) (Wend bend dend k : Nat)
    (hok : actsOK W b 24 true acts = true) (hend : aEnd W b 24 acts = (Wend, bend, dend))
    (hn : nsteps acts + dend = 24) (hk : k + 1 = dend) (hd2 : 2 ≤ dend) (hd22 : dend ≤ 22)
    (hI : PInv W b 24 true s0 F G) (hfs : s0.fs = 0) (hgs : s0.gs = 0) (hbad0 : (prun acts s0).bad = 0)
    (T m OF OG : Nat) (shF shG : List Nat) (hT : T = 2 ^ bend) (hm : m = 2 ^ Wend - 1)
    (hOF : OF = 2 ^ bend * rep Wend (dend + 1)) (hOG : OG = 2 ^ bend * rep Wend dend)
    (hshF : shF = lns Wend dend) (hshG : shG = lns Wend (dend - 1)) (hW : bend + 1 ≤ Wend)
    (hrun : (run k (unpackT T m OF shF (prun acts s0).fv (prun acts s0).fs)
      (unpackT T m OG shG (prun acts s0).gv (prun acts s0).gs) (prun acts s0).bad).2 = 0) :
    normalResultantGo 25 true F G = some (zdec (run k (unpackT T m OF shF (prun acts s0).fv (prun acts s0).fs)
      (unpackT T m OG shG (prun acts s0).gv (prun acts s0).gs) (prun acts s0).bad).1) := by
  obtain ⟨F', G', hI', hsp⟩ := prun_spec acts W b 24 true s0 F G hok hI hbad0
  have hns : 0 < nsteps acts := by omega
  have h := hsp (k + 2)
  rw [hend, hfs, hgs, map_one_mul, map_one_mul] at h
  rw [hend] at hI'
  dsimp only at hI' h
  rw [if_neg (by omega)] at h
  rw [show k + 2 + nsteps acts = 25 by omega] at h
  rw [h, show (true && nsteps acts == 0) = false by simp; omega]
  obtain ⟨hFl, hGl, hFb, hGb, hF0, hG0, hfv, hgv, _, _, _, _, hfs', hgs', _⟩ := hI'
  obtain ⟨uF, hlF⟩ := unpackT_spec Wend bend dend T m OF shF _ _ F' hT hm hOF hshF hW hFb hFl hfv hfs'
  obtain ⟨uG, hlG⟩ := unpackT_spec Wend bend (dend - 1) T m OG shG _ _ G' hT hm
    (by rw [hOG]; congr 2; omega) hshG hW hGb (by omega) hgv hgs'
  rw [← uF, ← uG]
  apply run_spec k _ _ _ (k + 2) (by omega) (by rw [hlG]; omega) (by rw [hlF]; omega) (by omega)
  · rw [uF, headD_mul]
    exact Int.mul_ne_zero (sg_ne _) (by omega)
  · rw [uG, headD_mul]
    exact Int.mul_ne_zero (sg_ne _) (by omega)
  · exact hrun



theorem run_bad0 (k : Nat) (F G : List Nat) (bad : Nat) (h : (run k F G bad).2 = 0) : bad = 0 := by
  have := run_snd_ge k F G bad; omega


/-! ## Band 15 -/

theorem init15_spec (xs : List Nat) (hxs : xs.length = 24) (hb : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ 363) :
    PInv 1092 363 24 true (init15 xs) (1 :: xs.map zdec) (24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] ((xs.take 23).map zdec)) := by
  unfold init15
  exact pinit_spec 1092 363 xs _ _ _ _ _ _ _ _ _ (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) rfl (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide) hxs hb

theorem acts15_ok : actsOK 1092 363 24 true acts15 = true := by decide +kernel

theorem pk15_ok (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) (h0 : zdec f0 = 1) (hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 363)
    (hbad : (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).2 = 0) :
    normalResultant ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) (derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec)) = some (zdec (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).1) := by
  rw [pkDag15_struct f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24] at hbad ⊢
  unfold pkRun15 at hbad ⊢
  dsimp only at hbad ⊢
  have hfs : (init15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).fs = 0 := by unfold init15 pinit; rfl
  have hgs : (init15 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).gs = 0 := by unfold init15 pinit; rfl
  have hend : aEnd 1092 363 24 acts15 = (1857, 618, 1) := by decide +kernel
  have hn : nsteps acts15 = 23 := by decide +kernel
  have hF : [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec = 1 :: [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec := by simp [h0]
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq (zdec f1) (zdec f2) (zdec f3) (zdec f4) (zdec f5) (zdec f6) (zdec f7) (zdec f8) (zdec f9) (zdec f10) (zdec f11) (zdec f12) (zdec f13) (zdec f14) (zdec f15) (zdec f16) (zdec f17) (zdec f18) (zdec f19) (zdec f20) (zdec f21) (zdec f22) (zdec f23) (zdec f24)
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact full_run_spec acts15 1092 363 _ _ _ 1857 618 acts15_ok hend hn
    (init15_spec [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] rfl hb) hfs hgs hbad

/-! ## Band 205 -/

theorem init205_spec (xs : List Nat) (hxs : xs.length = 24) (hb : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ 704) :
    PInv 2115 704 24 true (init205 xs) (1 :: xs.map zdec) (24 :: derA [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] ((xs.take 23).map zdec)) := by
  unfold init205
  exact pinit_spec 2115 704 xs _ _ _ _ _ _ _ _ _ (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) rfl (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide) hxs hb

theorem acts205_ok : actsOK 2115 704 24 true acts205 = true := by decide +kernel

theorem pk205_ok (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) (h0 : zdec f0 = 1) (hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 704)
    (hbad : (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).2 = 0) :
    normalResultant ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec) (derivHL ([f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec)) = some (zdec (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24).1) := by
  rw [pkDag205_struct f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24] at hbad ⊢
  unfold pkRun205 at hbad ⊢
  dsimp only at hbad ⊢
  have hfs : (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).fs = 0 := by unfold init205 pinit; rfl
  have hgs : (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24]).gs = 0 := by unfold init205 pinit; rfl
  have hend : aEnd 2115 704 24 acts205 = (6159, 2052, 10) := by decide +kernel
  have hn : nsteps acts205 + 10 = 24 := by decide +kernel
  have hF : [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec = 1 :: [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24].map zdec := by simp [h0]
  have hbad0 : (prun acts205 (init205 [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24])).bad = 0 := run_bad0 _ _ _ _ hbad
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq (zdec f1) (zdec f2) (zdec f3) (zdec f4) (zdec f5) (zdec f6) (zdec f7) (zdec f8) (zdec f9) (zdec f10) (zdec f11) (zdec f12) (zdec f13) (zdec f14) (zdec f15) (zdec f16) (zdec f17) (zdec f18) (zdec f19) (zdec f20) (zdec f21) (zdec f22) (zdec f23) (zdec f24)
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact hyb_run_spec acts205 2115 704 _ _ _ 6159 2052 10 9 acts205_ok hend hn rfl (by decide) (by decide)
    (init205_spec [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] rfl hb) hfs hgs hbad0 _ _ _ _ _ _ (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide) hbad



theorem appL_25 (k : Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Nat → Int) (d : Int) (f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : appL k d [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24] = k f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 := rfl

theorem finish8_zero (r : Nat × Nat) (fb : Int) (h : r.2 = 0) : finish8 r fb = zdec r.1 := by
  unfold finish8; rw [h]; rfl

theorem finish8_succ (r : Nat × Nat) (fb : Int) (m : Nat) (h : r.2 = m + 1) : finish8 r fb = fb := by
  unfold finish8; rw [h]

theorem kont15_def (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : kont15 n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = finish8 (pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) := rfl

theorem kont205_def (n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 : Nat) : kont205 n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = finish8 (pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) (kont n f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24) := rfl

theorem kont15_ok (n : Nat) (hk : kbitsOf n = 15) : appL (kont15 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont15_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have key := pk15_ok f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 h0
    generalize pkDag15 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 363 := by
        intro x hx
        have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem (List.mem_cons_of_mem _ hx))
        have : 24 * 2 ^ (15 - 1) < 2 ^ 363 := by decide +kernel
        omega
      have hres := key hb h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm

theorem kont205_ok (n : Nat) (hk : kbitsOf n = 205) : appL (kont205 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd
  match L, hlen with
  | [f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont205_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have key := pk205_ok f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 h0
    generalize pkDag205 f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 f13 f14 f15 f16 f17 f18 f19 f20 f21 f22 f23 f24 = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hb : ∀ x ∈ [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24], 24 * (zdec x).natAbs < 2 ^ 704 := by
        intro x hx
        have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem (List.mem_cons_of_mem _ hx))
        have : 24 * 2 ^ (205 - 1) < 2 ^ 704 := by decide +kernel
        omega
      have hres := key hb h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm

theorem impl_correct : ∀ n, impl n = discSpec n := by
  intro n
  have hs := lcgSeed_lt n
  unfold impl genFastC8
  by_cases h0 : n < 67108864
  · rw [show Nat.div n 67108864 = 0 from Nat.div_eq_of_lt h0]
    have hk : kbitsOf n = 15 := by unfold kbitsOf difficultyLevel; simp [h0]
    rw [genLane15C_eq _ hs (kont15 n) (discSpec n)]
    have e : genF n = 2 :: genGo 15 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact kont15_ok n hk
  obtain ⟨m0, hm0⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h0)
  rw [hm0]
  by_cases h1 : n < 68719476736
  · rw [show Nat.div n 68719476736 = 0 from Nat.div_eq_of_lt h1]
    have hk : kbitsOf n = 36 := by unfold kbitsOf difficultyLevel; simp [h0, h1]
    rw [genLane36C_eq _ hs (kont n) (discSpec n)]
    have e : genF n = 2 :: genGo 36 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact fastDisc_spec n
  obtain ⟨m1, hm1⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h1)
  rw [hm1]
  by_cases h2 : n < 70368744177664
  · rw [show Nat.div n 70368744177664 = 0 from Nat.div_eq_of_lt h2]
    have hk : kbitsOf n = 205 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2]
    rw [genLane205C_eq _ hs (kont205 n) (discSpec n)]
    have e : genF n = 2 :: genGo 205 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact kont205_ok n hk
  obtain ⟨m2, hm2⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h2)
  rw [hm2]
  by_cases h3 : n < 72057594037927936
  · rw [show Nat.div n 72057594037927936 = 0 from Nat.div_eq_of_lt h3]
    have hk : kbitsOf n = 1001 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]
    rw [genLane1001C_eq _ hs (kont n) (discSpec n)]
    have e : genF n = 2 :: genGo 1001 24 1 (lcgSeed n) := by unfold genF; rw [hk]
    rw [← e]; exact fastDisc_spec n
  obtain ⟨m3, hm3⟩ := div_succ_of_le (by decide) (Nat.le_of_not_lt h3)
  rw [hm3]
  have hk : kbitsOf n = 3484 := by unfold kbitsOf difficultyLevel; simp [h0, h1, h2, h3]
  rw [genLane3484C_eq _ hs (kont n) (discSpec n)]
  have e : genF n = 2 :: genGo 3484 24 1 (lcgSeed n) := by unfold genF; rw [hk]
  rw [← e]; exact fastDisc_spec n

end Submission
