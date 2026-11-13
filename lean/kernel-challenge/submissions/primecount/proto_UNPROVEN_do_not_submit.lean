import Spec

namespace Submission

/-- `Σ_{j<J} B^(d·j)` in closed form. -/
def rep (B d J : Nat) : Nat := (B ^ (d * J) - 1) / (B ^ d - 1)

/-- Slot `m` of `marks B N s` = number of `d ∈ [2, s]` with `d ∣ m` and `d² ≤ m ≤ N`. -/
def marks (B N : Nat) : Nat → Nat
  | 0 => 0
  | k + 1 =>
    let d := k + 2
    marks B N k + (if d * d ≤ N then B ^ (d * d) * rep B d ((N - d * d) / d + 1) else 0)

def impl (N : Nat) : Nat :=
  if N < 2 then 0 else
  let w := N.log2 + 2
  let B := 2 ^ w
  let R := rep B 1 (N + 1)
  let X := marks B N (Nat.sqrt N - 1)
  let H := (X + (2 ^ (w - 1) - 1) * R) &&& (2 ^ (w - 1) * R)
  N - 1 - (H >>> (w - 1)) % (B - 1)

theorem impl_correct : ∀ n, impl n = primeCountSpec n := sorry

end Submission
