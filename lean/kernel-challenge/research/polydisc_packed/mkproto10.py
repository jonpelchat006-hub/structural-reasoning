import sys
sys.path.insert(0, "/home/claude/polyv8"); sys.path.insert(0, "/home/claude/polypack")
from gen10 import *
V7 = open("/home/claude/work/submissions_v4/polydisc/Submission.lean").read()
PACK = open("/home/claude/polyv8/lean/PackDefs.lean").read()
F25 = " ".join(f"f{i}" for i in range(25))
CFG = [("15", "D1", [0, 15], 23, 99, 300000), ("205", "D3", [0, 7, 11], 14, 0, 1099511628553)]
def main(out, cfg=CFG):
    head = V7[:V7.index("def impl (n : Nat) : Int := genFastC n (kont n)")]
    body = [PACK]
    for c in cfg:
        txt, k, nc = lean_band(*c); body.append(txt); print(c[0], "nodes", k, "consts", nc)
    names = [c[0] for c in cfg]
    k15 = "kont15" if "15" in names else "kont"; k205 = "kont205" if "205" in names else "kont"
    tail = "\n/-- Read off the packed result unless a check failed (then the v7 path `fb`). -/\n" \
           "def finish8 (r : Nat × Nat) (fb : Int) : Int :=\n  Nat.rec (motive := fun _ => Int) (zdec r.1) (fun _ _ => fb) r.2\n\n"
    for nm in names:
        tail += f"def kont{nm} (n {F25} : Nat) : Int := finish8 (pkDag{nm} {F25}) (kont n {F25})\n"
    tail += f'''
def genFastC8 (n : Nat) : Int :=
  Nat.rec (motive := fun _ => Int) (genLane15C (lcgSeed n) ({k15} n))
    (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane36C (lcgSeed n) (kont n))
      (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane205C (lcgSeed n) ({k205} n))
        (fun _ _ => Nat.rec (motive := fun _ => Int) (genLane1001C (lcgSeed n) (kont n))
          (fun _ _ => genLane3484C (lcgSeed n) (kont n)) (Nat.div n (nat_lit 72057594037927936)))
        (Nat.div n (nat_lit 70368744177664)))
      (Nat.div n (nat_lit 68719476736)))
    (Nat.div n (nat_lit 67108864))

def impl (n : Nat) : Int := genFastC8 n

end Submission
'''
    src = head + "\n".join(body) + tail
    open(out, "w").write(src); print("bytes", len(src.encode()))
if __name__ == "__main__":
    which = sys.argv[2:] if len(sys.argv) > 2 else None
    main(sys.argv[1], [c for c in CFG if which is None or c[0] in which])
