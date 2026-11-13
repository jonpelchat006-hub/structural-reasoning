"""memory/time of the kernel rfl link for the first K low steps"""
import sys, subprocess, time, os
sys.path.insert(0, "/home/claude/v9dev/gen")
import lowdag2
from lowdag2 import zenc, Dag, TAB, low2_ops, QW
from lowdag import ladder
import reference_answers as ref, random
random.seed(5); n = random.randint(2 ** 57, 2 ** 63)
P = ref.candidate_polynomial(n)[0]; fz = [zenc(c) for c in P]
F25 = " ".join(f"f{i}" for i in range(25)); FL = ", ".join(f"f{i}" for i in range(25))
def graph(K):
    g = Dag(list(fz) + [0, TAB]); lstep = low2_ops(g, ("x", 26))
    X = [("x", i) for i in range(25)]
    qmf, qmg = g.sub(g.shl(1, QW[0]), 1), g.sub(g.shl(1, QW[1]), 1)
    zres = lambda mag, s, qm: g.land(g.add(g.xor(mag, g.mul(s, qm)), s), qm)
    A = [zres(g.shr(x, 1), g.land(x, 1), qmf) for x in X]
    B = [zres(g.mul(g.shr(X[i], 1), 24 - i), g.land(X[i], 1), qmg) for i in range(24)]
    H, bad = lstep(QW[0], QW[1], QW[2], True, [], A, B); A, B = B, H
    for k in range(1, K):
        H, b = lstep(QW[k], QW[k + 1], QW[k + 2], False, ladder(QW[k + 2] + 128), A, B)
        bad = g.add(bad, b); A, B = B, H
    return g, B[0], bad
for K in [int(a) for a in sys.argv[1:]]:
    g, r, bad = graph(K)
    body = "\n".join(g.lines) + f"\napp x25 {g.tok(r)} {g.tok(bad)}"
    src = f'''import V9.Dag
import V9.Low
namespace V9
def lowRunK (xs : List Nat) : Nat × Nat :=
  let qmf := Nat.sub (Nat.shiftLeft 1 3485) 1
  let qmg := Nat.sub (Nat.shiftLeft 1 3489) 1
  let A := xs.map (fun x => zres (Nat.shiftRight x 1) (Nat.land x 1) qmf)
  let B := List.zipWith (fun x k => zres (Nat.mul (Nat.shiftRight x 1) k) (Nat.land x 1) qmg) xs dks
  let r0 := lstep 3485 3489 3500 3484 3488 true [] A B
  let r := lrun (lparams.take {K - 1}) B r0.1 r0.2
  (r.1.headD 0, r.2)
def dagK ({F25} : Nat) : Nat × Nat :=
  natdag% "{body}" [{FL}, (@Prod.mk Nat Nat), dbTab]
def DagKEq : Prop := ∀ {F25} : Nat, dagK {F25} = lowRunK [{FL}]
open Lean Elab Term Command Meta in
run_cmd liftTermElabM do
  let ty ← instantiateMVars (← elabTerm (← `(DagKEq)) none)
  let pf ← instantiateMVars (← elabTerm (← `(fun ({F25} : Nat) => @rfl (Nat × Nat) (dagK {F25}))) none)
  addDecl (.thmDecl {{ name := `V9.dagK_eq, levelParams := [], type := ty, value := pf }})
end V9
'''
    open("/home/claude/v9dev/V9/RflK.lean", "w").write(src)
    r = subprocess.run(["python3", "/home/claude/v9dev/gen/memrun.py", "exec lake env lean V9/RflK.lean"], capture_output=True, text=True)
    print(K, "nodes", len(g.lines), r.stdout.strip()[-200:], flush=True)
