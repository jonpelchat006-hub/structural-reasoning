#!/usr/bin/env python3
"""Rule 110, proposed v8 design: model, self-check and a measurement-only Lean prototype (no proofs).

usage:  ca_v8_proto.py check            # compare the model with the judge's reference (512 cases per width)
        ca_v8_proto.py emit W OUT.lean  # W = 9 or 19; writes impl/go2/go4/go8 with raw literals, no proofs

Design (see README.md):
  mixer   256 lanes of 65 bits, one per cell; the cell is lane bit 31; the seed is folded into the lane constant.
  gather  one `% (2^256 - 1)`: ring index i (cell (i - 8) mod 256) lands at bit (w i + 3) mod 256.
  expand  one multiplication by sum_j 2^(256 j) and one mask: ring index i at bit w i + 3, i < 272
          (an 8-cell halo on each side comes for free, so the cyclic row needs no tripling for t <= 8).
  step    lane = 8 cell + 1 (cell at bit 3, a helper bit at bit 0). One multiplication by
          K = 2^(2w) + 3 2^w + 11 and one mask: the lane sum is 8 (l + 3 c + 11 r) + 15, its bit 5 is
          Rule 110 of (l, c, r) and its bit 2 is always 1, which is the next step's helper bit.
  finish  w = 9: two multiply-and-mask stages and `% (2^512 - 1)`;  w = 19: one stage and `% (2^288 - 1)`.
"""
import sys

M32 = (1 << 32) - 1
GOLD, C1, C2 = 0x9E3779B9, 0x7FEB352D, 0x846CA68B
LW, NL, HALO, NRING, CELLBIT = 65, 256, 8, 272, 31
INV65 = pow(65, -1, 256)


class Design:
    def __init__(self, w, t):
        assert w in (9, 19)
        self.w, self.t = w, t
        self.K = (1 << (2 * w)) + (3 << w) + 11
        self.slot = lambda i: (w * i + 3) % 256                   # dense slot of ring index i
        self.lane = lambda i: ((self.slot(i) - CELLBIT) * INV65) % 256
        self.cell = lambda i: (i - HALO) % 256
        assert len({self.lane(i) for i in range(256)}) == 256
        cR = sum(1 << (LW * l) for l in range(NL))
        cT = sum((self.cell(i) + 1) << (LW * self.lane(i)) for i in range(256))
        self.cR, self.cRM = cR, cR * M32
        # lane input: n + (cell + 1) GOLD + 2^48 - t 2^32 = seed + (cell + 1) GOLD + 2^48
        self.K0 = GOLD * cT + ((1 << 48) - (t << 32)) * cR
        self.cE = sum(1 << (LW * self.lane(i) + CELLBIT) for i in range(256) if self.cell(i) >= 2)
        self.J = (w * (NRING - 1) + 3) // 256 + 1
        self.MEXP = sum(1 << (256 * j) for j in range(self.J))
        self.MASKW = sum(1 << (w * i + 3) for i in range(NRING) if self.cell(i) >= 2)
        self.HELP = (sum(1 << (w * i) for i in range(NRING))
                     + sum(1 << (w * i + 3) for i in range(NRING) if self.cell(i) == 0))
        self.step_masks, base = [], 0
        for k in range(t):
            base += w + 2
            if k < t - 1:
                self.step_masks.append(sum((1 << (w * i + base)) | (1 << (w * i + base + 3)) for i in range(NRING)))
            else:
                self.step_masks.append(sum(1 << (w * i + base + 3) for i in range(HALO, HALO + 256)))
        P0 = w * HALO + base + 3                                   # bit of cell 0 after the last step
        if w == 9:
            e = (-(P0 + 504)) % 512
            self.un = [(sum(1 << (8 * i) for i in range(8)) << e,
                        sum(0xFF << (P0 + e + 56 + 72 * g) for g in range(32))),
                       (sum(1 << (64 * i) for i in range(8)),
                        sum(((1 << 64) - 1) << (P0 + e + 504 + 576 * h) for h in range(4)))]
            self.fin = (1 << 512) - 1
        else:
            e = (-(P0 + 270)) % 288
            self.un = [(sum(1 << (18 * i) for i in range(16)) << e,
                        sum(0xFFFF << (P0 + e + 270 + 304 * g) for g in range(16)))]
            self.fin = (1 << 288) - 1

    def run(self, n):
        X0 = self.K0 + n * self.cR
        A1 = self.cRM & (X0 ^ (X0 >> 16))
        X1 = self.cRM & (C1 * A1)
        A2 = self.cRM & (X1 ^ (X1 >> 15))
        X2 = C2 * A2
        R = (self.cE & X2) % ((1 << 256) - 1)
        Y = self.HELP + (self.MASKW & (self.MEXP * R))
        for m in self.step_masks:
            Y = m & (self.K * Y)
        for mul, mask in self.un:
            Y = mask & (mul * Y)
        return Y % self.fin


def lit(x):
    return f"(nat_lit 0x{x:x})"


def go(w, t, name):
    d = Design(w, t)
    L = [f"def {name} (n : Nat) : Nat :=",
         f"  share X0 := Nat.add {lit(d.K0)} (Nat.mul n {lit(d.cR)});",
         f"  share X1 := Nat.land {lit(d.cRM)} (Nat.mul (nat_lit 0x7feb352d) (Nat.land {lit(d.cRM)} (Nat.xor X0 (Nat.shiftRight X0 (nat_lit 16)))));",
         f"  share X2 := Nat.mul (nat_lit 0x846ca68b) (Nat.land {lit(d.cRM)} (Nat.xor X1 (Nat.shiftRight X1 (nat_lit 15))));",
         f"  share R := Nat.mod (Nat.land {lit(d.cE)} X2) {lit((1 << 256) - 1)};",
         f"  share Y0 := Nat.add {lit(d.HELP)} (Nat.land {lit(d.MASKW)} (Nat.mul R {lit(d.MEXP)}));"]
    for k, m in enumerate(d.step_masks):
        L.append(f"  share Y{k+1} := Nat.land {lit(m)} (Nat.mul {lit(d.K)} Y{k});")
    cur = f"Y{t}"
    for k, (mul, mask) in enumerate(d.un):
        L.append(f"  share Z{k+1} := Nat.land {lit(mask)} (Nat.mul {lit(mul)} {cur});")
        cur = f"Z{k+1}"
    L.append(f"  Nat.mod {cur} {lit(d.fin)}")
    return "\n".join(L) + "\n"


HEADER = '''import Spec
import Lean

/-! Measurement-only prototype of the Rule 110 v8 design. NOT a submission: there is no `impl_correct`. -/

set_option exponentiation.threshold 30000
set_option maxRecDepth 100000

namespace Submission

open Lean Elab Term Meta in
elab "share " x:ident " := " v:term "; " b:term : term => do
  let v ← instantiateMVars (← elabTermEnsuringType v (some (mkConst ``Nat)))
  withLocalDeclD x.getId (mkConst ``Nat) fun fv => do
    let b ← instantiateMVars (← elabTermEnsuringType b (some (mkConst ``Nat)))
    return b.replaceFVar fv v

'''

FOOTER = '''
def implC (n : Nat) : Nat :=
  if Nat.shiftRight n 32 = 2 then go2 n
  else if Nat.shiftRight n 32 = 4 then go4 n
  else if Nat.shiftRight n 32 = 8 then go8 n
  else caSpecN n

/-- Same selector shape as v7. Other step counts fall back to the spec here (v7's `slow` in a real entry). -/
@[implemented_by implC]
def impl (n : Nat) : Nat :=
  share t := Nat.shiftRight n (nat_lit 32);
  Bool.rec (motive := fun _ => Nat)
    (Bool.rec (motive := fun _ => Nat)
      (Bool.rec (motive := fun _ => Nat) (caSpecN n) (go8 n) (Nat.beq t (nat_lit 8)))
      (go4 n) (Nat.beq t (nat_lit 4)))
    (go2 n) (Nat.beq t (nat_lit 2))

end Submission
'''


def check():
    import random
    sys.path.insert(0, "/home/claude/lkc_src/repo/evaluation/judge")   # the challenge repo's evaluation/judge
    import reference_answers as ref
    random.seed(20261112)
    for w in (9, 19):
        bad = tot = 0
        for t in range(1, 9):
            d = Design(w, t)
            for s in [0, 1, 2, 0xFFFFFFFF] + [random.getrandbits(32) for _ in range(60)]:
                tot += 1
                bad += d.run((t << 32) | s) != ref.ca_reference(t, s)
        print(f"w={w}: {tot} cases (t = 1..8, 64 seeds each): {bad} mismatches")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check()
    else:
        w = int(sys.argv[2])
        out = HEADER + go(w, 2, "go2") + "\n" + go(w, 4, "go4") + "\n" + go(w, 8, "go8") + FOOTER
        open(sys.argv[3], "w").write(out)
        print(len(out), "bytes")
