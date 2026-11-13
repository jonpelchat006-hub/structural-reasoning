"""polydisc v9 = v8 + the low-part D5 run (V9 namespace) as the band-3484 continuation.

Reads /home/claude/polyv8/Submission_v8b.lean and the V9 dev modules, writes
/home/claude/polyv9/Submission.lean."""
import os, re
V8 = open("/home/claude/polyv8/Submission_v8b.lean").read()
DEV = "/home/claude/v9dev/V9"
ORDER = ["Mod", "Det", "Subres", "Bridge", "Cert", "Low", "LowSpec", "Run", "Top", "Conv", "LowDag"]
F25 = " ".join(f"f{i}" for i in range(25))
FL = ", ".join(f"f{i}" for i in range(25))

def sub(s, old, new, count=1):
    assert s.count(old) >= 1, old[:80]
    return s.replace(old, new, count)

s = V8
# 1. natdag% learns gcd
s = sub(s, '("shr", ``Nat.shiftRight)]', '("shr", ``Nat.shiftRight), ("gcd", ``Nat.gcd)]')
s = sub(s, "`op a b`, with `op` one of `add sub mul div mod land lor xor shl shr`",
        "`op a b`, with `op` one of `add sub mul div mod land lor xor shl shr gcd`")
# 2. the V9 modules before the entry point
marker = "/- The graphs are evaluated only by the kernel; the elaborator must not unfold them. -/"
i = s.index(marker)
parts = []
for f in ORDER:
    t = open(f"{DEV}/{f}.lean").read()
    t = "\n".join(l for l in t.split("\n") if not l.startswith("import "))
    parts.append(t.strip() + "\n")
v9 = ("\nend Submission\n\n/-! # v9: the low-part normal PRS for the D5 band (namespace `V9`)\n\n"
      "Determinants and the subresultant chain (`chain_val`, `chain_exact`), the spec's PRS on chain\n"
      "functions (`normalResultant_chain`), size certificates (`sres_lt`), the low-part step and run\n"
      "(`lstep_spec`, `lrunR_spec`, `lowRun_spec`) and the shared graph `lowDag` (`lowDag_eq`). -/\n\n"
      + "\n".join(parts) + "\nnamespace Submission\n\n")
s = s[:i] + v9 + s[i:]
# 3. entry point
s = sub(s, "attribute [irreducible] pkDag15 pkDagC15 pkDag205 pkDagC205 prsDag kont",
        "attribute [irreducible] pkDag15 pkDagC15 pkDag205 pkDagC205 prsDag kont V9.lowDag")
old_disp = s[s.index("/-- The band dispatch of v7 with the packed continuations for bands 15 and 205. -/"):
             s.index("def impl (n : Nat) : Int := genFastC8 n")]
new_disp = old_disp.replace("/-- The band dispatch of v7 with the packed continuations for bands 15 and 205. -/",
    f"/-- Band 3484: the low-part run (v9), the v7 path as fallback. -/\n"
    f"def kont3484 (n {F25} : Nat) : Int := finish8 (V9.lowDag {F25}) (kont n {F25})\n\n"
    "/-- The band dispatch of v7 with the packed continuations for bands 15 and 205 and the low-part\n"
    "run for band 3484. -/")
new_disp = new_disp.replace("def genFastC8 (n : Nat) : Int :=", "def genFastC9 (n : Nat) : Int :=")
new_disp = new_disp.replace("(fun _ _ => genLane3484C (lcgSeed n) (kont n))", "(fun _ _ => genLane3484C (lcgSeed n) (kont3484 n))")
s = s.replace(old_disp, new_disp)
s = sub(s, "def impl (n : Nat) : Int := genFastC8 n", "def impl (n : Nat) : Int := genFastC9 n")
# 4. proofs
proofs = f'''
/-! ## Band 3484 (v9) -/

theorem zdec_v9 : V9.zdec = zdec := rfl

theorem coeffs_wbound (k : Nat) (hk : 2 ≤ k) : ∀ count index state i, i < count →
    ((coefficientsFrom count k index state).getD i 0).natAbs ≤ 2 ^ (coefficientWidth k (index + i) - 1)
  | 0, _, _, i, hi => absurd hi (Nat.not_lt_zero _)
  | count + 1, index, state, 0, _ => by
    simp only [coefficientsFrom, List.getD_cons_zero, Nat.add_zero]
    obtain ⟨h2, hk'⟩ := width_bounds k index hk
    have hlt := collect_lt ((coefficientWidth k index + 63) / 64) 0 state
    rcases hlt with hlt | hlt
    · rw [Nat.zero_add] at hlt
      exact cnc_bound (coefficientWidth k index) ((coefficientWidth k index + 63) / 64)
        (collectCoeffWord ((coefficientWidth k index + 63) / 64) 0 state).1 (by omega) (by omega) hlt
    · omega
  | count + 1, index, state, i + 1, hi => by
    simp only [coefficientsFrom, List.getD_cons_succ]
    rw [show index + (i + 1) = index + 1 + i by omega]
    exact coeffs_wbound k hk count (index + 1) _ i (by omega)

theorem getD_zdec : ∀ (l : List Nat) (j : Nat), zdec (l.getD j 0) = (l.map zdec).getD j 0
  | [], _ => by simp [zdec_zero]
  | _ :: _, 0 => rfl
  | _ :: l, j + 1 => by simp only [List.getD_cons_succ, List.map_cons]; exact getD_zdec l j

theorem polyOf_wbound (n : Nat) (hk : kbitsOf n = 3484) : ∀ e, (V9.fX (genF n) e).natAbs ≤ V9.FbN e := by
  intro e
  unfold V9.fX V9.FbN
  by_cases he : e ≤ 24
  · rw [if_pos he, zdec_v9, getD_zdec, genF_spec n]
    unfold polyOf; rw [hk]
    by_cases h24 : e = 24
    · subst h24; simp
    · rw [if_neg h24, if_pos (by omega)]
      obtain ⟨p, hp⟩ : ∃ p, 24 - e = p + 1 := ⟨23 - e, by omega⟩
      rw [hp, List.getD_cons_succ]
      have := coeffs_wbound 3484 (by decide) 24 1 (lcgSeed n) p (by omega)
      rw [show 1 + p = p + 1 by omega] at this
      exact this
  · rw [if_neg he]; simp

theorem lowDag_ok ({F25} : Nat) (h0 : zdec f0 = 1)
    (hxb : ∀ x ∈ [{FL}], x / 2 ≤ 2 ^ 3483)
    (hb : ∀ e, (V9.fX [{FL}] e).natAbs ≤ V9.FbN e)
    (hbad : (V9.lowDag {F25}).2 = 0) :
    normalResultant ([{FL}].map zdec) (derivHL ([{FL}].map zdec)) = some (zdec (V9.lowDag {F25}).1) := by
  rw [V9.lowDag_eq {F25}] at hbad ⊢
  have h := V9.lowRun_spec [{FL}] rfl (by simpa [zdec_v9] using h0) hxb hb hbad
  rw [V9.toL_fX, V9.toL_gX, zdec_v9] at h
  exact h

theorem kont3484_def (n {F25} : Nat) : kont3484 n {F25} = finish8 (V9.lowDag {F25}) (kont n {F25}) := rfl

set_option exponentiation.threshold 4000 in
theorem kont3484_ok (n : Nat) (hk : kbitsOf n = 3484) : appL (kont3484 n) (discSpec n) (genF n) = discSpec n := by
  have hlen : (genF n).length = 25 := by unfold genF; simp [genGo_length]
  have hspec := genF_spec n
  have hfd := fastDisc_spec n
  have hbnd := polyOf_bound n
  rw [hk] at hbnd
  have hwb := polyOf_wbound n hk
  unfold fastDisc at hfd
  generalize genF n = L at hlen hspec hfd hwb
  match L, hlen with
  | [{FL}], _ =>
    rw [appL_25] at hfd ⊢
    rw [kont3484_def]
    have h0 : zdec f0 = 1 := by
      have := congrArg (fun l => l.headD 0) hspec
      simp only [List.map_cons, List.headD_cons] at this
      rw [this]; rfl
    have hxb : ∀ x ∈ [{FL}], x / 2 ≤ 2 ^ 3483 := by
      intro x hx
      have := hbnd (zdec x) (by rw [← hspec]; exact List.mem_map_of_mem hx)
      rw [← zdec_v9, V9.natAbs_zdec] at this
      exact this
    have key := lowDag_ok {F25} h0 hxb hwb
    generalize V9.lowDag {F25} = r at key ⊢
    cases h : r.2 with
    | succ m => rw [finish8_succ r _ m h]; exact hfd
    | zero =>
      rw [finish8_zero r _ h]
      have hres := key h
      unfold discSpec
      rw [← hspec]
      exact (disc_eq _ (by simp) _ hres).symm

'''
s = sub(s, "theorem impl_correct : ∀ n, impl n = discSpec n := by", proofs + "theorem impl_correct : ∀ n, impl n = discSpec n := by")
s = sub(s, "  unfold impl genFastC8\n", "  unfold impl genFastC9\n")
old_tail = '''  rw [genLane3484C_eq _ hs (kont n) (discSpec n)]
  have e : genF n = 2 :: genGo 3484 24 1 (lcgSeed n) := by unfold genF; rw [hk]
  rw [← e]; exact fastDisc_spec n

end Submission'''
new_tail = '''  rw [genLane3484C_eq _ hs (kont3484 n) (discSpec n)]
  have e : genF n = 2 :: genGo 3484 24 1 (lcgSeed n) := by unfold genF; rw [hk]
  rw [← e]; exact kont3484_ok n hk

end Submission'''
s = sub(s, old_tail, new_tail)
# docs
s = sub(s, "# Polynomial discriminant by an encoded, shared-graph normal PRS (v7) and packed lanes (v8)",
        "# Polynomial discriminant by an encoded, shared-graph normal PRS (v7), packed lanes (v8) and a low-part D5 run (v9)")
os.makedirs("/home/claude/polyv9", exist_ok=True)
open("/home/claude/polyv9/Submission.lean", "w").write(s)
print("bytes", len(s.encode()))
