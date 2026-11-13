"""Base.lean = v7 (impl removed, impl_correct turned into fastDisc_spec) + packed definitions + band
graphs, rfl links and structured runs + the new impl. Dev.lean holds the new proofs; mkfinal.py
concatenates both into one Submission.lean."""
import sys
sys.path.insert(0, "/home/claude/polyv8"); sys.path.insert(0, "/home/claude/polypack")
from gen10 import *
V7 = open("/home/claude/work/submissions_v4/polydisc/Submission.lean").read()
PACK = open("/home/claude/polyv8/lean/PackDefs.lean").read()
CFG = [("15", "D1", [0, 15], 23, 99, 300000), ("205", "D3", [0, 7, 11], 14, 0, 1099511628553)]
F25 = " ".join(f"f{i}" for i in range(25))

def v7_part():
    s = V7
    s = s.replace("def impl (n : Nat) : Int := genFastC n (kont n)\n", "")
    old = ("theorem impl_correct : ∀ n, impl n = discSpec n := by\n  intro n\n  unfold impl\n"
           "  rw [genFastC_eq n (kont n) (discSpec n)]\n  show fastDisc n (genF n) = _\n")
    assert old in s
    s = s.replace(old, "/-- The v7 path (also the fallback of the packed runs). -/\n"
                       "theorem fastDisc_spec (n : Nat) : fastDisc n (genF n) = discSpec n := by\n")
    i = s.rindex("end Submission")
    return s[:i]

IMPL = f'''
/- The graphs are evaluated only by the kernel; the elaborator must not unfold them. -/
attribute [irreducible] pkDag15 pkDagC15 pkDag205 pkDagC205 prsDag kont

/-! ## v8 entry point -/

/-- Read off the packed result unless a check failed (then the v7 path `fb`). -/
def finish8 (r : Nat × Nat) (fb : Int) : Int :=
  Nat.rec (motive := fun _ => Int) (zdec r.1) (fun _ _ => fb) r.2

/-- Band 15: the packed run, the v7 path as fallback. -/
def kont15 (n {F25} : Nat) : Int := finish8 (pkDag15 {F25}) (kont n {F25})
/-- Band 205: the packed prefix with v7 tail, the v7 path as fallback. -/
def kont205 (n {F25} : Nat) : Int := finish8 (pkDag205 {F25}) (kont n {F25})

/-- The band dispatch of v7 with the packed continuations for bands 15 and 205. -/
def genFastC8 (n : Nat) : Int :=
  Nat.rec (motive := fun _ => Int) (genLane15C (lcgSeed n) (kont15 n))
    (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane36C (lcgSeed n) (kont n))
      (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane205C (lcgSeed n) (kont205 n))
        (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane1001C (lcgSeed n) (kont n))
          (fun _ _ => genLane3484C (lcgSeed n) (kont n)) (Nat.div n (nat_lit 72057594037927936)))
        (Nat.div n (nat_lit 70368744177664)))
      (Nat.div n (nat_lit 68719476736)))
    (Nat.div n (nat_lit 67108864))

def impl (n : Nat) : Int := genFastC8 n
'''

def base_text():
    body = [v7_part(), PACK]
    for c in CFG:
        txt, k, nc = lean_band(*c); body.append(txt)
    body.append(IMPL)
    return "\n".join(body)

if __name__ == "__main__":
    src = base_text() + "\nend Submission\n"
    open("/home/claude/polydev/Base.lean", "w").write(src)
    print("Base bytes", len(src.encode()))
