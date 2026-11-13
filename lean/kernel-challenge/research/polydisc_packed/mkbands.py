"""Lean band theorems (pkX_ok) for the configured bands, from the generator's plan."""
import sys
sys.path.insert(0, "/home/claude/polyv8"); sys.path.insert(0, "/home/claude/polypack")
from gen10 import *
import reference_answers as ref
F = " ".join(f"f{i}" for i in range(25)); FL = ", ".join(f"f{i}" for i in range(25)); XL = ", ".join(f"f{i}" for i in range(1, 25))
Z = " ".join(f"(zdec f{i})" for i in range(1, 25))
KS = "[23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]"

def band_text(name, band, cuts, steps, lowb_from, n):
    segs = plan(band, cuts, steps, lowb_from)
    W0, b0 = segs[0][2], segs[0][3]
    We, be = segs[-1][2], segs[-1][3]
    out = f'''
/-! ## Band {name} -/

theorem init{name}_spec (xs : List Nat) (hxs : xs.length = 24) (hb : ∀ x ∈ xs, 24 * (zdec x).natAbs < 2 ^ {b0}) :
    PInv {W0} {b0} 24 true (init{name} xs) (1 :: xs.map zdec) (24 :: derA {KS} ((xs.take 23).map zdec)) := by
  unfold init{name}
  exact pinit_spec {W0} {b0} xs _ _ _ _ _ _ _ _ _ (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) rfl (by decide +kernel) (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide) hxs hb

theorem acts{name}_ok : actsOK {W0} {b0} 24 true acts{name} = true := by decide +kernel

theorem pk{name}_ok ({F} : Nat) (h0 : zdec f0 = 1) (hb : ∀ x ∈ [{XL}], 24 * (zdec x).natAbs < 2 ^ {b0})
    (hbad : (pkDag{name} {F}).2 = 0) :
    normalResultant ([{FL}].map zdec) (derivHL ([{FL}].map zdec)) = some (zdec (pkDag{name} {F}).1) := by
  rw [pkDag{name}_struct {F}] at hbad ⊢
  unfold pkRun{name} at hbad ⊢
  dsimp only at hbad ⊢
  have hfs : (init{name} [{XL}]).fs = 0 := by unfold init{name} pinit; rfl
  have hgs : (init{name} [{XL}]).gs = 0 := by unfold init{name} pinit; rfl
'''
    if steps == 23:
        out += f'''  have hend : aEnd {W0} {b0} 24 acts{name} = ({We}, {be}, 1) := by decide +kernel
  have hn : nsteps acts{name} = 23 := by decide +kernel
  have hF : [{FL}].map zdec = 1 :: [{XL}].map zdec := by simp [h0]
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq {Z}
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact full_run_spec acts{name} {W0} {b0} _ _ _ {We} {be} acts{name}_ok hend hn
    (init{name}_spec [{XL}] rfl hb) hfs hgs hbad
'''
    else:
        dend = 24 - steps; k = 23 - steps
        out += f'''  have hend : aEnd {W0} {b0} 24 acts{name} = ({We}, {be}, {dend}) := by decide +kernel
  have hn : nsteps acts{name} + {dend} = 24 := by decide +kernel
  have hF : [{FL}].map zdec = 1 :: [{XL}].map zdec := by simp [h0]
  have hbad0 : (prun acts{name} (init{name} [{XL}])).bad = 0 := run_bad0 _ _ _ _ hbad
  rw [hF]
  apply normalResultant_of_go _ (by simp) rfl
  have hG := derivHL_eq {Z}
  simp only [List.map_cons, List.map_nil] at hG ⊢
  rw [hG]
  exact hyb_run_spec acts{name} {W0} {b0} _ _ _ {We} {be} {dend} {k} acts{name}_ok hend hn rfl (by decide) (by decide)
    (init{name}_spec [{XL}] rfl hb) hfs hgs hbad0 _ _ _ _ _ _ (by decide +kernel) (by decide +kernel)
    (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide +kernel) (by decide) hbad
'''
    return out

if __name__ == "__main__":
    CFG = [("15", "D1", [0, 15], 23, 99, 300000), ("205", "D3", [0, 7, 11], 14, 0, 1099511628553)]
    print("".join(band_text(*c) for c in CFG))
