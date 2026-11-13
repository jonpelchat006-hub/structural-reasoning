import V9.LowSpec
import V9.Cert

/-!
# The low-part run computes the chain

`lrunR_spec`: if every step's checks pass, the run of steps `k … 22` ends with the residues of
`F_24` and every leading coefficient of the chain is nonzero. Bounds come from the size
certificates (`chain_bound`), exactness from `chain_exact`.
-/

namespace V9

theorem lstep_cps {α : Type} (qA qB q qhA qhB : Nat) (first : Bool) (nw : List Nat) (A B : List Nat)
    (k : List Nat → Nat → α) :
    lstep qA qB q qhA qhB first nw A B k =
      k (lstep qA qB q qhA qhB first nw A B Prod.mk).1 (lstep qA qB q qhA qhB first nw A B Prod.mk).2 := rfl

/-- The run with its result returned as a pair. -/
def lrunR (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat) : List Nat × Nat :=
  lrun ps A B bad Prod.mk

theorem lrun_cps {α : Type} : ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat)
    (k : List Nat → Nat → α), lrun ps A B bad k = k (lrunR ps A B bad).1 (lrunR ps A B bad).2
  | [], _, _, _, _ => rfl
  | (qA, qB, q, qhA, qhB, nw) :: ps, A, B, bad, k => by
    unfold lrunR
    simp only [lrun]
    rw [lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) k),
      lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) Prod.mk)]
    exact lrun_cps ps _ _ _ k

theorem lrunR_cons (qA qB q qhA qhB : Nat) (nw : List Nat) (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat))
    (A B : List Nat) (bad : Nat) :
    lrunR ((qA, qB, q, qhA, qhB, nw) :: ps) A B bad =
      lrunR ps B (lstep qA qB q qhA qhB false nw A B Prod.mk).1
        (bad + (lstep qA qB q qhA qhB false nw A B Prod.mk).2) := by
  unfold lrunR; simp only [lrun]
  rw [lstep_cps _ _ _ _ _ _ _ _ _ (fun H b => lrun ps B H (Nat.add bad b) Prod.mk)]; rfl

theorem lrunR_mono : ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (A B : List Nat) (bad : Nat),
    bad ≤ (lrunR ps A B bad).2
  | [], _, _, _ => Nat.le_refl _
  | (qA, qB, q, qhA, qhB, nw) :: ps, A, B, bad => by
    rw [lrunR_cons]
    exact Nat.le_trans (Nat.le_add_right _ _) (lrunR_mono ps _ _ _)

/-! ## The parameters and the certificates -/

def qw (k : Nat) : Nat := qws.getD k 0

/-- Step `k`'s parameters: the widths of `F_k`, `F_(k+1)`, `F_(k+2)`, their sign bits, a Newton
ladder to `q + 128`. -/
def stepsOK : Nat → List (Nat × Nat × Nat × Nat × Nat × List Nat) → Bool
  | k, [] => k == 23
  | k, (qA, qB, q, qhA, qhB, nw) :: ps =>
    (qA == qw k) && (qB == qw (k + 1)) && (q == qw (k + 2)) && (qhA + 1 == qA) && (qhB + 1 == qB) &&
      Nat.ble 64 qA && Nat.ble qA q && Nat.ble qB q && ladderOK 3 nw (q + 128) && stepsOK (k + 1) ps

theorem stepsOK_lparams : stepsOK 1 lparams = true := by decide

/-- Certificate `i` is for `S_(22-i)` with the width of `F_(i+2)`. -/
def certIdx : Nat → List (Nat × Nat × Nat × Nat × List Nat × List Nat) → Bool
  | k, [] => k == 23
  | k, (j, _, _, q, _, _) :: cs => (j + k == 22) && (q == qw (k + 2)) && certIdx (k + 1) cs

theorem certIdx_ok : certIdx 0 certD5 = true := by decide

theorem cert_get : ∀ (k : Nat) (cs : List (Nat × Nat × Nat × Nat × List Nat × List Nat)),
    certIdx k cs = true → certAll cs = true →
    ∀ i, k ≤ i → i ≤ 22 → ∃ N K u v, certOK (22 - i) N K (qw (i + 2)) u v = true
  | k, [], h, _, i, hi, hi2 => by simp [certIdx] at h; omega
  | k, (j, N, K, q, u, v) :: cs, h, ha, i, hi, hi2 => by
    simp only [certIdx, Bool.and_eq_true, beq_iff_eq] at h
    simp only [certAll, Bool.and_eq_true] at ha
    by_cases hik : i = k
    · subst hik
      refine ⟨N, K, u, v, ?_⟩
      rw [show 22 - i = j by omega, ← h.1.2]; exact ha.1
    · exact cert_get (k + 1) cs h.2 ha.2 i (by omega) hi2

/-- Every chain polynomial `F_k` (`k ≥ 2`) is below its width. -/
theorem chain_bound (f g : Nat → Int) (hf : ∀ e, 24 < e → f e = 0) (hg : ∀ e, 23 < e → g e = 0)
    (hfb : ∀ e, (f e).natAbs ≤ FbN e) (hgb : ∀ e, (g e).natAbs ≤ GbN e) (k : Nat) (hk2 : 2 ≤ k) (hk : k ≤ 24)
    (hL : ∀ k', k' < k - 1 → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0) :
    ∀ e, e ≤ 24 - k → ((chainP f g 24 (k - 1)).2 e).natAbs < 2 ^ (qw k - 1) := by
  intro e he
  rw [chain_val f g 24 (by decide) hf hg (k - 1) (by omega) (by omega) hL e (by omega)]
  obtain ⟨N, K, u, v, hc⟩ := cert_get 0 certD5 certIdx_ok certD5_ok (k - 2) (by omega) (by omega)
  rw [show k - 2 + 2 = k by omega, show 22 - (k - 2) = 24 - k by omega] at hc
  rw [show 24 - (k - 1 + 1) = 24 - k by omega]
  exact sres_lt f g hfb hgb (24 - k) N K (qw k) u v hc e (by omega)

/-! ## The run -/

theorem lrunR_spec (f g : Nat → Int) (hf : ∀ e, 24 < e → f e = 0) (hg : ∀ e, 23 < e → g e = 0)
    (hfb : ∀ e, (f e).natAbs ≤ FbN e) (hgb : ∀ e, (g e).natAbs ≤ GbN e)
    (hgw : ∀ e, (g e).natAbs < 2 ^ (qw 1 - 1)) :
    ∀ (ps : List (Nat × Nat × Nat × Nat × Nat × List Nat)) (k : Nat) (A B : List Nat) (bad : Nat),
      stepsOK k ps = true → 1 ≤ k →
      A = toN (qw k) (chainP f g 24 k).1 (24 - k) → B = toN (qw (k + 1)) (chainP f g 24 k).2 (23 - k) →
      (∀ k', k' ≤ k → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0) →
      (lrunR ps A B bad).2 = 0 →
      (lrunR ps A B bad).1 = toN (qw 24) (chainP f g 24 23).2 0 ∧
        ∀ k', k' ≤ 23 → (chainP f g 24 k').2 (24 - (k' + 1)) ≠ 0
  | [], k, A, B, bad, hs, _, _, hB, hL, _ => by
    simp only [stepsOK, beq_iff_eq] at hs
    subst hs
    exact ⟨hB, hL⟩
  | (qA, qB, q, qhA, qhB, nw) :: ps, k, A, B, bad, hs, hk1, hA, hB, hL, hbad => by
    simp only [stepsOK, Bool.and_eq_true, beq_iff_eq, Nat.ble_eq] at hs
    obtain ⟨⟨⟨⟨⟨⟨⟨⟨⟨hqA, hqB⟩, hq⟩, hhA⟩, hhB⟩, h64⟩, hAq⟩, hBq⟩, hnw⟩, hrest⟩ := hs
    have hk22 : k ≤ 22 := by
      have hq0 : qw (k + 2) ≠ 0 := by omega
      apply Nat.le_of_not_lt; intro hc
      apply hq0; unfold qw
      rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none (by simp [qws]; omega)]; rfl
    rw [lrunR_cons] at hbad ⊢
    -- one step
    obtain ⟨a, rfl⟩ : ∃ a, qA = a + 1 := ⟨qhA, by omega⟩
    obtain ⟨b, rfl⟩ : ∃ b, qB = b + 1 := ⟨qhB, by omega⟩
    have ha : a = qhA := by omega
    have hb : b = qhB := by omega
    subst ha hb
    have hn : 24 - k = (22 - k) + 2 := by omega
    have hn1 : 23 - k = (22 - k) + 1 := by omega
    rw [hn, ← hqA] at hA; rw [hn1, ← hqB] at hB
    subst hA; subst hB
    have hAb : ∀ e, e ≤ 22 - k + 2 → ((chainP f g 24 k).1 e).natAbs < 2 ^ a := by
      intro e he
      cases k with
      | zero => omega
      | succ k0 =>
        rw [chainP_fst_succ]
        cases k0 with
        | zero => simpa [chainP, ← hqA] using hgw e
        | succ k1 =>
          have := chain_bound f g hf hg hfb hgb (k1 + 2) (by omega) (by omega)
            (fun k' hk' => hL k' (by omega)) e (by omega)
          rw [show k1 + 2 - 1 = k1 + 1 by omega, ← hqA] at this
          simpa using this
    have hBb : ∀ e, e ≤ 22 - k + 1 → ((chainP f g 24 k).2 e).natAbs < 2 ^ b := by
      intro e he
      have := chain_bound f g hf hg hfb hgb (k + 1) (by omega) (by omega)
        (fun k' hk' => hL k' (by omega)) e (by omega)
      rw [show k + 1 - 1 = k by omega, ← hqB] at this
      simpa using this
    have hP : ∀ e, e ≤ 22 - k → premF (chainP f g 24 k).1 (chainP f g 24 k).2 (22 - k + 1) e =
        (if false then 1 else (chainP f g 24 k).1 (22 - k + 2) * (chainP f g 24 k).1 (22 - k + 2)) *
          (chainP f g 24 (k + 1)).2 e := by
      intro e _
      have := chain_exact f g 24 (by decide) hf hg k (by omega) hk1 hL e
      rw [show 24 - (k + 1) = 22 - k + 1 by omega, show 22 - k + 1 + 1 = 22 - k + 2 by omega] at this
      simpa using this
    obtain ⟨H, b', hst, hok⟩ := lstep_spec a b q false nw (chainP f g 24 k).1 (chainP f g 24 k).2
      (chainP f g 24 (k + 1)).2 (22 - k) h64 hAq (by omega) hAb hBb (fun h => absurd h (by decide))
      (fun _ => hnw) hP Prod.mk
    rw [hst] at hbad ⊢
    simp only at hbad ⊢
    have hb0 : b' = 0 := by
      have := lrunR_mono ps (toN (b + 1) (chainP f g 24 k).2 (22 - k + 1)) H (bad + b'); omega
    obtain ⟨hH, hC⟩ := hok hb0
    exact lrunR_spec f g hf hg hfb hgb hgw ps (k + 1) _ H _ hrest (by omega)
      (by rw [show (chainP f g 24 (k + 1)).1 = (chainP f g 24 k).2 from chainP_fst_succ f g 24 k, hqB,
            show 24 - (k + 1) = 22 - k + 1 by omega])
      (by rw [hH, hq, show 23 - (k + 1) = 22 - k by omega])
      (fun k' hk' => by
        by_cases h : k' = k + 1
        · subst h; rw [show 24 - (k + 1 + 1) = 22 - k by omega]; exact hC
        · exact hL k' (by omega))
      hbad

end V9
