import V9.Low
import V9.Mod
import V9.Bridge

/-!
# The low-part step computes the chain

`coef_spec`: one coefficient. The three products and the sign corrections give the numerator
times `inv²` modulo `M = 2^(q + 2sh)`; if that is `2^(2sh)·C` the low `q` bits after the shift are
the residue of `C`.
-/

namespace V9

theorem nadd (a b : Nat) : Nat.add a b = a + b := rfl
theorem nsub (a b : Nat) : Nat.sub a b = a - b := rfl
theorem nmul (a b : Nat) : Nat.mul a b = a * b := rfl
theorem nshl (a b : Nat) : Nat.shiftLeft a b = a * 2 ^ b := Nat.shiftLeft_eq a b
theorem nshr (a b : Nat) : Nat.shiftRight a b = a / 2 ^ b := Nat.shiftRight_eq_div_pow a b
theorem nmask (a k : Nat) : Nat.land a (2 ^ k - 1) = a % 2 ^ k := Nat.and_two_pow_sub_one_eq_mod a k

theorem sign_le (q : Nat) (x : Int) (hx : x.natAbs < 2 ^ q) : res (q + 1) x >>> q ≤ 1 := by
  rw [(res_val q x hx).1]; split <;> omega

theorem natCast_mod_pow (a k : Nat) : ((a % 2 ^ k : Nat) : Int) = (a : Int) % 2 ^ k := by
  rw [Int.natCast_emod, cast_two_pow]

/-- One coefficient of a low-part step. -/
theorem coef_spec (q a b sh2 : Nat) (m1 m2 m3 : Nat) (X Y Z C : Int)
    (hX : X.natAbs < 2 ^ a) (hY : Y.natAbs < 2 ^ b) (hZ : Z.natAbs < 2 ^ b)
    (hcong : MEq (2 ^ (q + sh2)) ((m1 : Int) * X + m2 * Y + m3 * Z) (2 ^ sh2 * C)) :
    coef m1 m2 m3 (m1 * 2 ^ (a + 1) % 2 ^ (q + sh2)) (m2 * 2 ^ (b + 1) % 2 ^ (q + sh2))
      (m3 * 2 ^ (b + 1) % 2 ^ (q + sh2)) (2 ^ (q + sh2) * 4) sh2 (2 ^ q - 1) a b
      (res (a + 1) X) (res (b + 1) Y) (res (b + 1) Z) = res q C := by
  obtain ⟨sX, vX⟩ := res_val a X hX
  obtain ⟨sY, vY⟩ := res_val b Y hY
  obtain ⟨sZ, vZ⟩ := res_val b Z hZ
  have bX := sign_le a X hX; have bY := sign_le b Y hY; have bZ := sign_le b Z hZ
  generalize res (a + 1) X = x at sX vX bX
  generalize res (b + 1) Y = y at sY vY bY
  generalize res (b + 1) Z = z at sZ vZ bZ
  generalize hM : 2 ^ (q + sh2) = M at hcong ⊢
  have hMpos : 0 < M := by rw [← hM]; exact Nat.two_pow_pos _
  unfold coef
  simp only [nadd, nsub, nmul, nshr, nmask]
  rw [← Nat.shiftRight_eq_div_pow x a, ← Nat.shiftRight_eq_div_pow y b, ← Nat.shiftRight_eq_div_pow z b]
  generalize x >>> a = s1 at sX vX bX ⊢
  generalize y >>> b = s2 at sY vY bY ⊢
  generalize z >>> b = s3 at sZ vZ bZ ⊢
  -- the corrections are below `3M`, so the subtraction is exact
  have hc1 := Nat.mod_lt (m1 * 2 ^ (a + 1)) hMpos
  have hc2 := Nat.mod_lt (m2 * 2 ^ (b + 1)) hMpos
  have hc3 := Nat.mod_lt (m3 * 2 ^ (b + 1)) hMpos
  have hCr : s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M)
      ≤ M * 4 := by
    have e1 : s1 * (m1 * 2 ^ (a + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bX with h | h <;> rw [h] <;> omega
    have e2 : s2 * (m2 * 2 ^ (b + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bY with h | h <;> rw [h] <;> omega
    have e3 : s3 * (m3 * 2 ^ (b + 1) % M) ≤ M := by
      rcases Nat.le_one_iff_eq_zero_or_eq_one.1 bZ with h | h <;> rw [h] <;> omega
    omega
  generalize hT : m1 * x + m2 * y + m3 * z + M * 4 -
      (s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M)) = T
  -- `T ≡ 2^sh2 · C (mod M)`
  have hTi : (T : Int) = m1 * x + m2 * y + m3 * z + M * 4 -
      (s1 * (m1 * 2 ^ (a + 1) % M) + s2 * (m2 * 2 ^ (b + 1) % M) + s3 * (m3 * 2 ^ (b + 1) % M) : Nat) := by
    rw [← hT, Int.ofNat_sub (by omega)]; push_cast; rfl
  have hMi : (M : Int) = 2 ^ (q + sh2) := by rw [← hM, cast_two_pow]
  have hcT : MEq M T (2 ^ sh2 * C) := by
    have k1 : MEq M ((m1 * 2 ^ (a + 1) % M : Nat) : Int) ((m1 : Int) * 2 ^ (a + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    have k2 : MEq M ((m2 * 2 ^ (b + 1) % M : Nat) : Int) ((m2 : Int) * 2 ^ (b + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    have k3 : MEq M ((m3 * 2 ^ (b + 1) % M : Nat) : Int) ((m3 : Int) * 2 ^ (b + 1)) := by
      rw [Int.natCast_emod]; push_cast; exact MEq.emod _ _
    generalize m1 * 2 ^ (a + 1) % M = c1 at k1 hTi
    generalize m2 * 2 ^ (b + 1) % M = c2 at k2 hTi
    generalize m3 * 2 ^ (b + 1) % M = c3 at k3 hTi
    obtain ⟨u1, hu1⟩ := k1; obtain ⟨u2, hu2⟩ := k2; obtain ⟨u3, hu3⟩ := k3
    have hsum : MEq M (T : Int) ((m1 : Int) * X + m2 * Y + m3 * Z) := by
      refine ⟨4 - s1 * u1 - s2 * u2 - s3 * u3, ?_⟩
      have ex : (x : Int) = X + s1 * 2 ^ (a + 1) := by omega
      have ey : (y : Int) = Y + s2 * 2 ^ (b + 1) := by omega
      have ez : (z : Int) = Z + s3 * 2 ^ (b + 1) := by omega
      rw [hTi]; push_cast
      rw [ex, ey, ez]
      grind
    exact hsum.trans (by rw [← hMi] at hcong; exact hcong)
  obtain ⟨t, ht⟩ := hcT
  -- shift and mask
  have hdiv : ((T / 2 ^ sh2 : Nat) : Int) = C + 2 ^ q * t := by
    rw [Int.natCast_ediv, cast_two_pow]
    have : (T : Int) = 2 ^ sh2 * (C + 2 ^ q * t) := by
      rw [hMi, Int.pow_add] at ht; grind
    rw [this, Int.mul_ediv_cancel_left _ (Int.ne_of_gt (two_pow_pos sh2))]
  apply Int.ofNat_inj.1
  rw [natCast_mod_pow, hdiv, res_cast, Int.add_mul_emod_self_left]

theorem res_zero_int (q : Nat) : res q 0 = 0 := by simp [res]

theorem zshr (n : Nat) : Nat.shiftRight 0 n = 0 := by rw [nshr, Nat.zero_div]

/-- The constant coefficient is `coef` with `y = 0`. -/
theorem coefL_eq (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x z : Nat) :
    coefL m1 m3 c1 c3 K sh2 qm qhA qhB x z = coef m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB x 0 z := by
  unfold coefL coef
  simp only [nadd, nsub, nmul, Nat.mul_zero, Nat.add_zero, zshr, Nat.zero_mul]

/-! ## Lists of residues -/

def toN (q : Nat) (P : Nat → Int) (n : Nat) : List Nat := (toL P n).map (res q)

theorem toN_zero (q : Nat) (P : Nat → Int) : toN q P 0 = [res q (P 0)] := rfl
theorem toN_succ (q : Nat) (P : Nat → Int) (n : Nat) : toN q P (n + 1) = res q (P (n + 1)) :: toN q P n := rfl
theorem toN_cons (q : Nat) (P : Nat → Int) (n : Nat) : toN q P n = res q (P n) :: (toN q P n).tail := by
  cases n <;> rfl
theorem toN_length (q : Nat) (P : Nat → Int) (n : Nat) : (toN q P n).length = n + 1 := by
  simp [toN, toL_length]

theorem hd0_cons (a : Nat) (l : List Nat) : hd0 (a :: l) = a := rfl

theorem lqs_spec (m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB qA qB q : Nat) (A B C : Nat → Int) :
    ∀ n, (∀ e, 1 ≤ e → e ≤ n → coef m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB (res qA (A e)) (res qB (B (e - 1)))
        (res qB (B e)) = res q (C e)) →
      coefL m1 m3 c1 c3 K sh2 qm qhA qhB (res qA (A 0)) (res qB (B 0)) = res q (C 0) →
      lqs m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB (toN qA A n) (toN qB B n) = toN q C n
  | 0, _, h0 => by rw [toN_zero, toN_zero, toN_zero]; simp only [lqs, h0]
  | n + 1, h, h0 => by
    rw [toN_succ qA A n, toN_succ qB B n, toN_succ q C n, toN_cons qA A n, toN_cons qB B n]
    simp only [lqs]
    rw [← toN_cons, ← toN_cons, lqs_spec m1 m2 m3 c1 c2 c3 K sh2 qm qhA qhB qA qB q A B C n
      (fun e he1 he2 => h e he1 (by omega)) h0]
    have := h (n + 1) (by omega) (Nat.le_refl _)
    rw [Nat.add_sub_cancel] at this
    rw [this]

/-! ## Newton's inverse -/

def ladderOK : Nat → List Nat → Nat → Bool
  | p, [], t => p == t
  | p, p' :: ps, t => Nat.ble p' (2 * p) && ladderOK p' ps t

theorem newton_step (a x p p' : Nat) (hp : p' ≤ 2 * p) (h : MEq (2 ^ p) ((a : Int) * x) 1) :
    MEq (2 ^ p') ((a : Int) * (Nat.land (Nat.mul x (Nat.sub (Nat.add (Nat.sub (Nat.shiftLeft 1 p') 1) 3)
      (Nat.land (Nat.mul (Nat.land a (Nat.sub (Nat.shiftLeft 1 p') 1)) x) (Nat.sub (Nat.shiftLeft 1 p') 1))))
      (Nat.sub (Nat.shiftLeft 1 p') 1) : Nat)) 1 := by
  have e1 : Nat.shiftLeft 1 p' = 2 ^ p' := by rw [nshl, Nat.one_mul]
  simp only [e1, nmask, nmul, nadd, nsub]
  have hP : 0 < 2 ^ p' := Nat.two_pow_pos p'
  generalize ht : a % 2 ^ p' * x % 2 ^ p' = t
  have htl : t < 2 ^ p' := by rw [← ht]; exact Nat.mod_lt _ hP
  have hsub : 2 ^ p' - 1 + 3 - t = 2 ^ p' + 2 - t := by omega
  rw [hsub]
  -- `t ≡ a·x`
  have hta : MEq (2 ^ p') (t : Int) ((a : Int) * x) := by
    rw [← ht, Int.natCast_emod, Int.natCast_mul, Int.natCast_emod, cast_two_pow]
    exact (MEq.emod _ _).trans ((MEq.emod _ _).mul (MEq.refl _ _))
  obtain ⟨δ, hδ⟩ := h
  have hxx : MEq (2 ^ p') ((a : Int) * ((x * (2 ^ p' + 2 - t) % 2 ^ p' : Nat) : Int))
      ((a : Int) * x * (2 - (a : Int) * x)) := by
    rw [Int.natCast_emod, cast_two_pow]
    refine (MEq.mul_left _ (MEq.emod _ _)).trans ?_
    rw [Int.natCast_mul, Int.ofNat_sub (by omega)]
    push_cast
    have := (MEq.refl (2 ^ p' : Int) ((a : Int) * x)).mul
      ((MEq.add_mul (2 ^ p' : Int) 2 1).sub hta)
    refine MEq.trans ?_ this
    exact ⟨0, by grind⟩
  refine hxx.trans ?_
  -- `a·x·(2 − a·x) = 1 − (2^p δ)²`
  have hax : (a : Int) * x = 1 + 2 ^ p * δ := by omega
  rw [hax]
  refine ⟨-(2 ^ (2 * p - p') * δ * δ), ?_⟩
  have e2 : (2 : Int) ^ p * 2 ^ p = 2 ^ p' * 2 ^ (2 * p - p') := by
    rw [← Int.pow_add, ← Int.pow_add]; congr 1; omega
  grind

theorem newton_spec (a : Nat) : ∀ (ps : List Nat) (x p t : Nat), ladderOK p ps t = true →
    MEq (2 ^ p) ((a : Int) * x) 1 → MEq (2 ^ t) ((a : Int) * newton a x ps) 1
  | [], x, p, t, h, hx => by
    simp only [ladderOK, beq_iff_eq] at h; subst h; exact hx
  | p' :: ps, x, p, t, h, hx => by
    simp only [ladderOK, Bool.and_eq_true, Nat.ble_eq] at h
    exact newton_spec a ps _ p' t h.2 (newton_step a x p p' h.1 hx)

theorem odd_sq (o : Nat) (h : o % 2 = 1) : MEq (2 ^ 3) ((o : Int) * o) 1 := by
  have h8 : (o * o) % 8 = 1 := by
    rw [Nat.mul_mod]
    have h1 : o % 8 % 2 = 1 := by omega
    have h2 : o % 8 < 8 := Nat.mod_lt _ (by decide)
    generalize o % 8 = r at h1 h2
    have : r = 1 ∨ r = 3 ∨ r = 5 ∨ r = 7 := by omega
    rcases this with rfl | rfl | rfl | rfl <;> rfl
  refine ⟨(o * o / 8 : Nat), ?_⟩
  have := Nat.div_add_mod (o * o) 8
  push_cast; omega

/-! ## Per-step scalars -/

/-- Sign extension of a residue to a larger power-of-two modulus. -/
theorem ext_spec (b : Nat) (Y : Int) (hY : Y.natAbs < 2 ^ b) (M : Nat) (hM : 2 ^ (b + 1) ≤ M) :
    MEq M ((Nat.add (res (b + 1) Y) (Nat.mul (Nat.shiftRight (res (b + 1) Y) b) (Nat.sub M (Nat.shiftLeft 1 (b + 1)))) : Nat) : Int) Y := by
  obtain ⟨_, v⟩ := res_val b Y hY
  have e1 : Nat.shiftLeft 1 (b + 1) = 2 ^ (b + 1) := by rw [nshl, Nat.one_mul]
  have e2 : Nat.shiftRight (res (b + 1) Y) b = res (b + 1) Y >>> b := rfl
  rw [e1, e2]
  generalize res (b + 1) Y = u at v
  generalize u >>> b = s at v
  refine ⟨(s : Int), ?_⟩
  simp only [nadd, nmul, nsub]
  rw [Int.natCast_add, Int.natCast_mul, Int.ofNat_sub hM, cast_two_pow]
  grind

/-- The magnitude of a residue's value. -/
theorem mag_spec (a : Nat) (L : Int) (hL : L.natAbs < 2 ^ a) :
    Nat.add (Nat.sub (res (a + 1) L) (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))))
      (Nat.sub (Nat.mul (Nat.shiftRight (res (a + 1) L) a) (Nat.shiftLeft 1 (a + 1))) (res (a + 1) L)) = L.natAbs := by
  obtain ⟨s, v⟩ := res_val a L hL
  have e1 : Nat.shiftLeft 1 (a + 1) = 2 ^ (a + 1) := by rw [nshl, Nat.one_mul]
  have hlt := res_lt (a + 1) L
  have e2 : Nat.shiftRight (res (a + 1) L) a = res (a + 1) L >>> a := rfl
  simp only [e1, e2, nadd, nmul, nsub]
  rw [← cast_two_pow] at v
  generalize res (a + 1) L = u at s v hlt ⊢
  generalize 2 ^ (a + 1) = P at v hlt ⊢
  rw [s] at v ⊢
  by_cases hneg : L < 0
  · rw [if_pos hneg] at v ⊢
    simp only [Int.natCast_one, Int.one_mul, Nat.one_mul] at v ⊢
    omega
  · rw [if_neg hneg] at v ⊢
    simp only [Int.natCast_zero, Int.zero_mul, Int.sub_zero, Nat.zero_mul] at v ⊢
    omega

theorem and_one (x : Nat) : Nat.land x 1 = x % 2 := Nat.and_one_is_mod x

/-- The valuation checks: `v₂(L) = sh` and the odd part. -/
theorem sh_check (a : Nat) (L : Int) (sh : Nat) (_hL : L.natAbs < 2 ^ a) (ha : 64 ≤ a + 1)
    (h : Nat.add (Nat.sub 1 (Nat.land (Nat.shiftRight (Nat.land (res (a + 1) L) 18446744073709551615) sh) 1))
      (Nat.land (Nat.land (res (a + 1) L) 18446744073709551615) (Nat.sub (Nat.shiftLeft 1 sh) 1)) = 0) :
    sh < 64 ∧ L.natAbs % 2 ^ sh = 0 ∧ (L.natAbs / 2 ^ sh) % 2 = 1 := by
  have e64 : (18446744073709551615 : Nat) = 2 ^ 64 - 1 := rfl
  have e1 : Nat.shiftLeft 1 sh = 2 ^ sh := by rw [nshl, Nat.one_mul]
  simp only [e64, e1, nmask, nadd, nsub, nshr, and_one] at h
  generalize hx : res (a + 1) L % 2 ^ 64 = xL at h
  have hxl : xL < 2 ^ 64 := by rw [← hx]; exact Nat.mod_lt _ (Nat.two_pow_pos 64)
  have c1 : xL / 2 ^ sh % 2 = 1 := by omega
  have c2 : xL % 2 ^ sh = 0 := by omega
  have hsh : sh < 64 := by
    apply Nat.lt_of_not_le; intro hge
    have : xL / 2 ^ sh = 0 := Nat.div_eq_of_lt (Nat.lt_of_lt_of_le hxl (Nat.pow_le_pow_right (by decide) (by omega)))
    omega
  refine ⟨hsh, ?_⟩
  -- `xL ≡ 2^sh (mod 2^(sh+1))`
  have hP : 0 < 2 ^ sh := Nat.two_pow_pos sh
  have hx2 : xL % 2 ^ (sh + 1) = 2 ^ sh := by
    have d1 := Nat.div_add_mod xL (2 ^ sh)
    have d2 := Nat.div_add_mod (xL / 2 ^ sh) 2
    rw [c2, Nat.add_zero] at d1
    rw [c1] at d2
    rw [Nat.pow_succ]
    have : xL = 2 ^ sh * 2 * (xL / 2 ^ sh / 2) + 2 ^ sh := by
      calc xL = 2 ^ sh * (xL / 2 ^ sh) := d1.symm
        _ = 2 ^ sh * (2 * (xL / 2 ^ sh / 2) + 1) := by rw [d2]
        _ = _ := by rw [Nat.mul_add, Nat.mul_one, Nat.mul_assoc]
    rw [this, Nat.mul_add_mod]
    exact Nat.mod_eq_of_lt (by omega)
  -- the same for `L`
  have hLx : MEq (2 ^ (sh + 1)) L (xL : Int) := by
    have m1 : MEq (2 ^ (a + 1)) L (res (a + 1) L : Int) := (res_meq (a + 1) L).symm
    have m2 : MEq (2 ^ 64) ((res (a + 1) L : Nat) : Int) (xL : Int) := by
      rw [← hx, Int.natCast_emod, cast_two_pow]; exact (MEq.emod _ _).symm
    have d1 : (2 : Int) ^ (sh + 1) ∣ 2 ^ (a + 1) := pow2_dvd (by omega)
    have d2 : (2 : Int) ^ (sh + 1) ∣ 2 ^ 64 := pow2_dvd (by omega)
    exact (m1.of_dvd d1).trans (m2.of_dvd d2)
  have hLm : L % 2 ^ (sh + 1) = 2 ^ sh := by
    rw [hLx.emod_eq, ← cast_two_pow, ← Int.natCast_emod, hx2, cast_two_pow]
  have hv : L.natAbs % 2 ^ (sh + 1) = 2 ^ sh := by
    have hP2 : (0 : Int) < 2 ^ (sh + 1) := two_pow_pos _
    apply Int.ofNat_inj.1
    rw [Int.natCast_emod, cast_two_pow, cast_two_pow]
    rcases Int.natAbs_eq L with hl | hl
    · rw [← hl, hLm]
    · have e : (L.natAbs : Int) = -L := by omega
      rw [e]
      have q := Int.emod_add_mul_ediv L (2 ^ (sh + 1))
      rw [hLm] at q
      have : -L = 2 ^ sh + 2 ^ (sh + 1) * (-(L / 2 ^ (sh + 1)) - 1) := by
        rw [pow_succ_two] at q ⊢; grind
      rw [this, Int.add_mul_emod_self_left]
      exact Int.emod_eq_of_lt (Int.le_of_lt (two_pow_pos sh)) (by rw [pow_succ_two]; have := two_pow_pos sh; omega)
  have d1 := Nat.div_add_mod L.natAbs (2 ^ (sh + 1))
  rw [hv] at d1
  rw [Nat.pow_succ] at d1
  have hdecomp : L.natAbs = 2 ^ sh * (2 * (L.natAbs / (2 ^ sh * 2)) + 1) := by
    rw [Nat.mul_add, Nat.mul_one, ← Nat.mul_assoc]; omega
  rw [hdecomp, Nat.mul_mod_right, Nat.mul_div_cancel_left _ hP]
  omega

theorem meq_mod (M a : Nat) : MEq M ((a % M : Nat) : Int) (a : Int) := by
  rw [Int.natCast_emod]; exact MEq.emod _ _

/-- The three multipliers of a step: `m₁X + m₂Y + m₃Z ≡ inv²·(lg²X − lf·lg·Y − (lg·f₁ − lf·g₁)·Z)`. -/
theorem mult_cong (M sh inv o sf Lg F1 G1 : Nat) (lf lg f1 g1 : Int) (hMpos : 0 < M)
    (hLg : MEq M Lg lg) (hF1 : MEq M F1 f1) (hG1 : MEq M G1 g1) (hsf : sf ≤ 1)
    (hlf : lf = (if sf = 1 then -1 else 1) * 2 ^ sh * o) (hinv : MEq M ((o : Int) * inv) 1) (X Y Z : Int) :
    MEq M (((Lg * inv % M) * (Lg * inv % M) % M : Nat) * X
      + ((sf * ((Lg * inv % M) * 2 ^ sh % M) + (1 - sf) * (M - (Lg * inv % M) * 2 ^ sh % M)) : Nat) * Y
      + ((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) + M
          - (F1 * (Lg * inv % M)) % M) * inv % M : Nat) * Z)
      ((inv : Int) * inv * (lg * lg * X - lf * lg * Y - (lg * f1 - lf * g1) * Z)) := by
  generalize hσ : (if sf = 1 then (-1 : Int) else 1) = σ at hlf
  have hw : MEq M ((Lg * inv % M : Nat) : Int) (lg * inv) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hLg.mul (MEq.refl _ _)
  have hm1 : MEq M (((Lg * inv % M) * (Lg * inv % M) % M : Nat) : Int) (lg * inv * (lg * inv)) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hw.mul hw
  have ht2 : MEq M (((Lg * inv % M) * 2 ^ sh % M : Nat) : Int) (lg * inv * 2 ^ sh) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hw.mul (MEq.refl _ _)
  have hh : MEq M ((G1 * 2 ^ sh % M : Nat) : Int) (g1 * 2 ^ sh) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hG1.mul (MEq.refl _ _)
  have hv : MEq M ((F1 * (Lg * inv % M) % M : Nat) : Int) (f1 * (lg * inv)) := by
    refine (meq_mod M _).trans ?_; push_cast; exact hF1.mul hw
  have lt1 := Nat.mod_lt ((Lg * inv % M) * 2 ^ sh) hMpos
  have lt2 := Nat.mod_lt (G1 * 2 ^ sh) hMpos
  have lt3 := Nat.mod_lt (F1 * (Lg * inv % M)) hMpos
  -- `m₂ ≡ −σ·lg·inv·2^sh`, `m₃ ≡ (σ·2^sh·g₁ − f₁·lg·inv)·inv`
  have hm2 : MEq M (((sf * ((Lg * inv % M) * 2 ^ sh % M) + (1 - sf) * (M - (Lg * inv % M) * 2 ^ sh % M)) : Nat) : Int)
      (-σ * (lg * inv * 2 ^ sh)) := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp at hσ <;> subst hσ
    · simp only [Nat.zero_mul, Nat.zero_add, Nat.sub_zero, Nat.one_mul]
      exact (MEq.nat_sub (Nat.le_of_lt lt1) ht2).trans (MEq.of_eq (by grind))
    · simp only [Nat.one_mul, Nat.sub_self, Nat.zero_mul, Nat.add_zero]
      exact ht2.trans (MEq.of_eq (by grind))
  have hhs : MEq M ((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) : Nat) : Int)
      (σ * (g1 * 2 ^ sh)) := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp at hσ <;> subst hσ
    · simp only [Nat.sub_zero, Nat.one_mul, Nat.sub_self, Nat.zero_mul, Nat.add_zero]
      exact hh.trans (MEq.of_eq (by grind))
    · simp only [Nat.sub_self, Nat.zero_mul, Nat.zero_add, Nat.sub_zero, Nat.one_mul]
      exact (MEq.nat_sub (Nat.le_of_lt lt2) hh).trans (MEq.of_eq (by grind))
  have hs_le : ((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) ≤ M := by
    rcases Nat.le_one_iff_eq_zero_or_eq_one.1 hsf with h0 | h0 <;> subst h0 <;> simp <;> omega
  have hm3 : MEq M (((((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M)) + M
          - (F1 * (Lg * inv % M)) % M) * inv % M : Nat) : Int)
      ((σ * (g1 * 2 ^ sh) - f1 * (lg * inv)) * inv) := by
    refine (meq_mod M _).trans ?_
    rw [Int.natCast_mul, Int.ofNat_sub (by omega), Int.natCast_add]
    refine MEq.mul ?_ (MEq.refl _ _)
    exact ((hhs.add (MEq.self _)).sub hv).trans (MEq.of_eq (by grind))
  refine (((hm1.mul (MEq.refl _ X)).add (hm2.mul (MEq.refl _ Y))).add (hm3.mul (MEq.refl _ Z))).trans ?_
  -- the remaining difference is a multiple of `o·inv − 1`
  obtain ⟨k, hk⟩ := hinv
  refine ⟨σ * 2 ^ sh * inv * k * (lg * Y - g1 * Z), ?_⟩
  rw [hlf]
  have : (o : Int) * inv = 1 + M * k := by omega
  grind

/-! ## One step -/

theorem nmask' (x k : Nat) : Nat.land x (Nat.sub (2 ^ k) 1) = x % 2 ^ k := nmask x k

theorem vSh_true (lf : Nat) : vSh true lf = 0 := rfl
theorem vInv_true (nw : List Nat) (o : Nat) : vInv true nw o = 1 := rfl
theorem vSh_false (lf : Nat) : vSh false lf = dbSh (Nat.gcd (Nat.land lf 18446744073709551615) (Nat.shiftLeft 1 64)) := rfl
theorem vInv_false (nw : List Nat) (o : Nat) : vInv false nw o = newton o o nw := rfl
theorem cnd_true (x y : Nat) : cnd true x y = x := rfl
theorem cnd_false (x y : Nat) : cnd false x y = y := rfl

theorem lstep_spec {α : Type} (a b q : Nat) (first : Bool) (nw : List Nat) (A B C : Nat → Int) (n : Nat)
    (ha : 64 ≤ a + 1) (haq : a + 1 ≤ q) (hbq : b + 1 ≤ q)
    (hA : ∀ e, e ≤ n + 2 → (A e).natAbs < 2 ^ a) (hB : ∀ e, e ≤ n + 1 → (B e).natAbs < 2 ^ b)
    (hfirst : first = true → A (n + 2) = 1)
    (hnw : first = false → ladderOK 3 nw (q + 128) = true)
    (hP : ∀ e, e ≤ n → premF A B (n + 1) e = (if first then 1 else A (n + 2) * A (n + 2)) * C e)
    (k : List Nat → Nat → α) :
    ∃ H bad, lstep (a + 1) (b + 1) q a b first nw (toN (a + 1) A (n + 2)) (toN (b + 1) B (n + 1)) k = k H bad ∧
      (bad = 0 → H = toN q C n ∧ C n ≠ 0) := by
  have eA : toN (a + 1) A (n + 2) = res (a + 1) (A (n + 2)) :: res (a + 1) (A (n + 1)) :: toN (a + 1) A n := rfl
  have eB : toN (b + 1) B (n + 1) = res (b + 1) (B (n + 1)) :: res (b + 1) (B n) :: (toN (b + 1) B n).tail := by
    show res (b + 1) (B (n + 1)) :: toN (b + 1) B n = _; exact congrArg _ (toN_cons (b + 1) B n)
  rw [eA, eB]
  unfold lstep
  simp only [hd0_cons, List.tail_cons]
  rw [← toN_cons (b + 1) B n]
  refine ⟨_, _, rfl, ?_⟩
  intro hbad
  -- the leading coefficient of `A`
  have hL := hA (n + 2) (Nat.le_refl _)
  obtain ⟨hsf, -⟩ := res_val a (A (n + 2)) hL
  have hmag := mag_spec a (A (n + 2)) hL
  have hsfle := sign_le a (A (n + 2)) hL
  rw [show vMag (res (a + 1) (A (n + 2))) a (Nat.shiftLeft 1 (a + 1)) = (A (n + 2)).natAbs from hmag]
    at hbad ⊢
  generalize hsh : vSh first (res (a + 1) (A (n + 2))) = sh at hbad ⊢
  generalize hsh2 : Nat.shiftLeft sh 1 = sh2 at hbad ⊢
  have hsh2' : sh2 = sh + sh := by rw [← hsh2, nshl]; omega
  generalize hM : Nat.shiftLeft 1 (Nat.add q sh2) = M at hbad ⊢
  have hM' : M = 2 ^ (q + sh2) := by rw [← hM, nshl, Nat.one_mul]; rfl
  have hMpos : 0 < M := by rw [hM']; exact Nat.two_pow_pos _
  have em : ∀ x, Nat.land x (M - 1) = x % M := by intro x; rw [hM']; exact nmask x _
  have hLg := ext_spec b (B (n + 1)) (hB (n + 1) (Nat.le_refl _)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  have hF1 := ext_spec a (A (n + 1)) (hA (n + 1) (by omega)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  have hG1 := ext_spec b (B n) (hB n (by omega)) M
    (by rw [hM']; exact Nat.pow_le_pow_right (by decide) (by omega))
  rw [← vExt] at hLg hF1 hG1
  generalize vExt (res (b + 1) (B (n + 1))) b (Nat.sub M (Nat.shiftLeft 1 (b + 1))) = Lg at hLg hbad ⊢
  generalize vExt (res (a + 1) (A (n + 1))) a (Nat.sub M (Nat.shiftLeft 1 (a + 1))) = F1 at hF1 hbad ⊢
  generalize vExt (res (b + 1) (B n)) b (Nat.sub M (Nat.shiftLeft 1 (b + 1))) = G1 at hG1 hbad ⊢
  generalize hinv : vInv first nw (Nat.shiftRight (A (n + 2)).natAbs sh) = inv at hbad ⊢
  simp only [nshl, vSel, nadd, nmul, nsub, Nat.one_mul] at hbad ⊢
  simp only [em] at hbad ⊢
  have hsf' : Nat.shiftRight (res (a + 1) (A (n + 2))) a = if A (n + 2) < 0 then 1 else 0 := hsf
  have hsfle' : Nat.shiftRight (res (a + 1) (A (n + 2))) a ≤ 1 := hsfle
  generalize Nat.shiftRight (res (a + 1) (A (n + 2))) a = sf at hsf' hsfle' hbad ⊢
  have mc := mult_cong M sh inv ((A (n + 2)).natAbs / 2 ^ sh) sf Lg F1 G1 (A (n + 2)) (B (n + 1)) (A (n + 1)) (B n)
    hMpos hLg hF1 hG1 hsfle'
  generalize hw : Lg * inv % M = w at mc hbad ⊢
  generalize w * w % M = m1 at mc hbad ⊢
  generalize sf * (w * 2 ^ sh % M) + (1 - sf) * (M - w * 2 ^ sh % M) = m2 at mc hbad ⊢
  generalize ((1 - sf) * (G1 * 2 ^ sh % M) + (1 - (1 - sf)) * (M - G1 * 2 ^ sh % M) + M - F1 * w % M) * inv % M
    = m3 at mc hbad ⊢
  -- the failure count
  have hb2 : ∀ x y : Nat, cnd first x (y + x) = 0 → x = 0 ∧ (first = false → y = 0) := by
    intro x y h; cases first
    · simp only [cnd_false] at h; exact ⟨by omega, fun _ => by omega⟩
    · simp only [cnd_true] at h; exact ⟨h, fun h' => absurd h' (by decide)⟩
  obtain ⟨hlead, hchk⟩ := hb2 _ _ hbad
  -- the leading coefficient `σ·2^sh·o`, the inverse, and the scaling
  have hpos : ∀ x : Int, 0 ≤ x → x = (x.natAbs : Int) := fun x hx => by omega
  have key : A (n + 2) = (if sf = 1 then -1 else 1) * 2 ^ sh * (((A (n + 2)).natAbs / 2 ^ sh : Nat) : Int)
      ∧ MEq M ((((A (n + 2)).natAbs / 2 ^ sh : Nat) : Int) * inv) 1
      ∧ (∀ c : Int, MEq M ((inv : Int) * inv * ((if first then 1 else A (n + 2) * A (n + 2)) * c))
          (2 ^ sh2 * c)) := by
    cases first
    · have hc := hchk rfl
      unfold vChk at hc
      obtain ⟨hs64, hm0, hodd⟩ := sh_check a (A (n + 2)) sh hL ha hc
      have hdec : (A (n + 2)).natAbs = 2 ^ sh * ((A (n + 2)).natAbs / 2 ^ sh) := by
        have := Nat.div_add_mod (A (n + 2)).natAbs (2 ^ sh); omega
      generalize ho : (A (n + 2)).natAbs / 2 ^ sh = o at hdec hodd hinv ⊢
      rw [vInv_false, nshr, ho] at hinv
      have hnv := newton_spec o nw o 3 (q + 128) (hnw rfl) (odd_sq o hodd)
      rw [hinv] at hnv
      have hdvd : (M : Int) ∣ 2 ^ (q + 128) := by rw [hM', cast_two_pow]; exact pow2_dvd (by omega)
      have hoi : MEq M ((o : Int) * inv) 1 := hnv.of_dvd hdvd
      refine ⟨?_, hoi, ?_⟩
      · rw [hsf']
        by_cases hneg : A (n + 2) < 0
        · rw [if_pos hneg, if_pos rfl]
          have : ((A (n + 2)).natAbs : Int) = -A (n + 2) := by omega
          rw [hdec] at this; push_cast at this; grind
        · rw [if_neg hneg, if_neg (by decide)]
          have : ((A (n + 2)).natAbs : Int) = A (n + 2) := by omega
          rw [hdec] at this; push_cast at this; grind
      · intro c
        simp only [Bool.false_eq_true, ↓reduceIte]
        have hsq : A (n + 2) * A (n + 2) = 2 ^ sh2 * ((o : Int) * o) := by
          have : ((A (n + 2)).natAbs : Int) * (A (n + 2)).natAbs = A (n + 2) * A (n + 2) := by
            rw [← Int.natCast_mul]; exact Int.natAbs_mul_self
          rw [← this, hdec, hsh2']; push_cast; rw [Int.pow_add]; grind
        rw [hsq]
        have := ((hoi.mul hoi).mul_left ((2 : Int) ^ sh2 * c))
        refine MEq.trans (MEq.of_eq (by grind)) (this.trans (MEq.of_eq (by grind)))
    · have h1 := hfirst rfl
      rw [vSh_true] at hsh; subst hsh
      rw [vInv_true] at hinv; subst hinv
      have hsh0 : sh2 = 0 := by omega
      subst hsh0
      rw [h1] at hsf' ⊢
      simp only [show ¬((1 : Int) < 0) by decide, ↓reduceIte] at hsf'
      subst hsf'
      refine ⟨by simp, by simp; exact MEq.refl _ _, fun c => by simp; exact MEq.refl _ _⟩
  obtain ⟨klf, kinv, kscale⟩ := key
  have mc' := mc klf kinv
  -- every coefficient
  have hcoef : ∀ e, e ≤ n → ∀ Y : Int, (Y = if 1 ≤ e then B (e - 1) else 0) →
      MEq (2 ^ (q + sh2)) ((m1 : Int) * A e + m2 * Y + m3 * B e) (2 ^ sh2 * C e) := by
    intro e he Y hY
    have h1 := mc' (A e) Y (B e)
    have h2 := hP e he
    unfold premF at h2
    rw [if_pos (by omega), show n + 1 - 1 = n by omega] at h2
    rw [← hY] at h2
    have hMi : (M : Int) = 2 ^ (q + sh2) := by rw [hM', cast_two_pow]
    rw [← hMi]
    refine h1.trans ?_
    have e3 : B (n + 1) * B (n + 1) * A e - A (n + 2) * B (n + 1) * Y - (B (n + 1) * A (n + 1) - A (n + 2) * B n) * B e
        = (if first = true then 1 else A (n + 2) * A (n + 2)) * C e := h2
    rw [e3]
    exact kscale (C e)
  have hlq := lqs_spec m1 m2 m3 (m1 * 2 ^ (a + 1) % M) (m2 * 2 ^ (b + 1) % M) (m3 * 2 ^ (b + 1) % M)
    (M * 2 ^ 2) sh2 (2 ^ q - 1) a b (a + 1) (b + 1) q A B C n
    (fun e he1 he2 => by
      rw [hM', show (2 : Nat) ^ 2 = 4 from rfl]
      exact coef_spec q a b sh2 m1 m2 m3 (A e) (B (e - 1)) (B e) (C e) (hA e (by omega)) (hB (e - 1) (by omega))
        (hB e (by omega)) (hcoef e he2 _ (by rw [if_pos he1])))
    (by
      rw [coefL_eq _ m2 _ _ (m2 * 2 ^ (b + 1) % M), hM', show (2 : Nat) ^ 2 = 4 from rfl]
      have := coef_spec q a b sh2 m1 m2 m3 (A 0) 0 (B 0) (C 0) (hA 0 (by omega)) (by simp; exact Nat.two_pow_pos b)
        (hB 0 (by omega)) (hcoef 0 (by omega) 0 (by simp))
      rwa [res_zero_int] at this)
  rw [hlq] at hlead ⊢
  refine ⟨rfl, ?_⟩
  intro h0
  rw [toN_cons, hd0_cons, h0, res_zero_int] at hlead
  exact absurd hlead (by decide)
end V9
