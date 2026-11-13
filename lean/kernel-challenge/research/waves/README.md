# Waves: the soundtrack of partitions into parts at most 3 (rung 1)

`Waves.lean` uses Mathlib at the challenge's pinned revision. It builds with `warningAsError`, has
no `sorry`, and uses only `propext`, `Classical.choice` and `Quot.sound`.

## What it proves

- **`card_restricted_le_three_eq`:** the number of partitions of `n` into parts at most 3 equals
  `((n + 3)² + 6) / 12`, i.e. `round((n + 3)² / 12)`, for every `n`.
  - The partitions are Mathlib's `Nat.Partition.restricted n (· ≤ 3)`.
  - The proof goes through a bijection with multiplicity triples `a + 2b + 3c = n`.
- **`p3_waves`:** Sylvester's wave form of the same count, over ℝ:
  `p₃(n) = (n + 3)²/12 − 7/72 + (−1)ⁿ/8 + (2/9)·cos(2πn/3)`.
  - The first part is a drone from the floor (the 1s).
  - The second is a note of period 2 (the marks where a 2 can be added).
  - The third is a note of period 3 (the marks for a 3).
- **`soundtrack3_eq`:** the formula written with kernel `Nat` primitives (4 operations) equals the count.
  - `example : soundtrack3 1000000 = 83333833334 := by decide` checks one value in the kernel.

## Kernel cost

Measured with the judge's replay window, as if it were a challenge problem:

| n | Instructions |
|---|---|
| 36 | 224.5k |
| 10⁶ | 224.2k |
| 10¹² | 236.6k |

The cost is flat in `n`, because a fixed equation replaces the count.

The full `p(n)` needs one wave per part size up to `n`. Rung 2 (the change of perspective
η(−1/z) = √(−iz)·η(z)) and rung 3 (Rademacher's series) are what make the full count scale.
