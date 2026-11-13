"""rfl tests of parts: init lists, then step-0 values"""
import sys, subprocess
sys.path.insert(0, "/home/claude/v9dev/gen")
from lowdag2 import zenc, Dag, TAB, low2_ops, QW
import reference_answers as ref, random
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
F25 = " ".join(f"f{i}" for i in range(25)); FL = ", ".join(f"f{i}" for i in range(25))
which = sys.argv[1]
g = Dag(list(fz) + [0, TAB]); lstep = low2_ops(g, ("x", 26))
X = [("x", i) for i in range(25)]
qmf, qmg = g.sub(g.shl(1, QW[0]), 1), g.sub(g.shl(1, QW[1]), 1)
zres = lambda mag, s, qm: g.land(g.add(g.xor(mag, g.mul(s, qm)), s), qm)
A = [zres(g.shr(x, 1), g.land(x, 1), qmf) for x in X]
B = [zres(g.mul(g.shr(X[i], 1), 24 - i), g.land(X[i], 1), qmg) for i in range(24)]
pre = '''  let qmf := Nat.sub (Nat.shiftLeft 1 3485) 1
  let qmg := Nat.sub (Nat.shiftLeft 1 3489) 1
  let A := xs.map (fun x => zres (Nat.shiftRight x 1) (Nat.land x 1) qmf)
  let B := List.zipWith (fun x k => zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) qmg) xs dks
'''
if which == "A":
    res = "list " + " ".join(g.tok(a) for a in A); rhs = pre + "  A"; ty = "List Nat"
elif which == "B":
    res = "list " + " ".join(g.tok(a) for a in B); rhs = pre + "  B"; ty = "List Nat"
elif which == "H":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "list " + " ".join(g.tok(a) for a in H); rhs = pre + "  (lstep 3485 3489 3500 3484 3488 true [] A B).1"; ty = "List Nat"
elif which == "h0a":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "list " + g.tok(H[0]); rhs = pre + "  [(lstep 3485 3489 3500 3484 3488 true [] A B).1.headD 0]"; ty = "List Nat"
elif which == "h0b":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "list " + g.tok(H[0]); rhs = pre + "  (lstep 3485 3489 3500 3484 3488 true [] A B).1.take 1"; ty = "List Nat"
elif which == "h0":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "add " + g.tok(H[0]) + " 0"; rhs = pre + "  Nat.add ((lstep 3485 3489 3500 3484 3488 true [] A B).1.headD 0) 0"; ty = "Nat"
elif which == "s0":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "add " + g.tok(bad) + " 0"; rhs = pre + "  Nat.add (Nat.sub 1 ((lstep 3485 3489 3500 3484 3488 true [] A B).1.headD 0)) 0"; ty = "Nat"
elif which == "b2":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "add " + g.tok(bad) + " 0"; rhs = pre + "  Nat.add ((lstep 3485 3489 3500 3484 3488 true [] A B).2) 0"; ty = "Nat"
elif which == "bad":
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B)
    res = "app x25 " + g.tok(H[0]) + " " + g.tok(bad); rhs = pre + "  lstep 3485 3489 3500 3484 3488 true [] A B (fun H b => (hd0 H, b))"; ty = "Nat × Nat"
body = "\n".join(g.lines) + "\n" + res
src = f'''import V9.Dag
import V9.Low
namespace V9
def rhsT (xs : List Nat) : {ty} :=
{rhs}
def dagT ({F25} : Nat) : {ty} :=
  natdag% "{body}" [{FL}, (@Prod.mk Nat Nat), dbTab]
def DagTEq : Prop := ∀ {F25} : Nat, dagT {F25} = rhsT [{FL}]
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(DagTEq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun ({F25} : Nat) => @rfl ({ty}) (dagT {F25}))) none)
  addDecl (.thmDecl {{ name := `V9.dagT_eq, levelParams := [], type := ty, value := pf }})
end V9
'''
open("/home/claude/v9dev/V9/RflT.lean", "w").write(src)
r = subprocess.run(["python3", "/home/claude/v9dev/gen/memrun.py", "exec lake env lean V9/RflT.lean"], capture_output=True, text=True)
print(which, "nodes", len(g.lines), r.stdout.strip()[-400:], flush=True)
