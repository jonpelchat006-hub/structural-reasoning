# Lean Kernel Challenge — partition v6 and the cost floor (Oct 26, 2026)

File: `submissions_v6/partition/Submission.lean` on the PC, with a README. Strict build, 3 axioms,
local judge accepted (6/6).

Board (Oct 26): main 1st with **1,430,108**; us (v5) 1,580,120 official, 1.571M local.

## v6

- Same pentagonal one-division fast path as v5, with smaller numbers:
  - **15-bit digits, series cut at degree 35, valid for n ≤ 38** (v5: 32-bit digits, degree 64, n ≤ 64).
  - The divisor numeral drops from 2048 to 525 bits.
- `p(n) = ⌊2^(15(n+35)) / P⌋ mod 2^15`. `P = B^35·E(1/B)`, where `E` is Euler's pentagonal polynomial
  with exponents 0, 1, 2, 5, 7, 12, 15, 22, 26, 35. The next exponent is 40.
- `fast_ok : ∀ n < 39, fast n = slow n` is checked by `decide +kernel`; the Durfee proof is unchanged.
- **Local total: 1.454M** (241.4k · 241.6k · 242.7k · 241.8k · 242.6k · 243.4k).
- Expected official is about 1.46M: v5's official count was 0.6% above its local count.

## The cost map (local valgrind, judge replay window, n = 14)

The judge's theorem is `impl (OfNat.ofNat Nat n _) = OfNat.ofNat Nat v _ := Eq.refl _`. Both the input
and the answer are `Lean.mkNatLit`, i.e. wrapped in `OfNat`.

| `impl` | Count | Above the constant floor |
|---|---|---|
| `fun n => n` (no work, structurally equal) | 187.6k | −5.0k |
| **constant answer (the floor)** | **192.6k** | 0 |
| `Nat.add 121 n` (read `n`, one small op) | 208.2k | +15.6k (reading `n` through `OfNat` alone is about 12k) |
| `Nat.mul 15 n` | 208.1k | +15.5k |
| + `shiftLeft` (result 735 bits) | 219.5k | +26.9k |
| + `div` | 229.5k | +36.9k (the answer is a 225-bit literal here) |
| fast formula, no case split (4 ops) | 227.7k | +35.1k |
| case split alone (`Nat.rec` on `n - 38`, constant branch) | 221.0k | +28.4k |
| case split alone, `Bool.rec` on `Nat.ble` | 221.5k | +28.9k |
| **v6 (case split + fast formula)** | **241.4k** | **+48.8k** |

**Reading of the costs:**
- Reading the input costs about 12k per case, for everyone.
- Each extra op costs about 4k (small numbers) to 10k (big numbers).
- The case split costs about 14k on top of the formula.

**Against the floor** (Jonathan's 0.14, "π − 3" band over the integer floor):
- v6 spends **0.25** of the floor.
- main spends about **0.23**.
- The 0.14 line is 27k per case, **1.318M** total.
- Reading `n` and the case split alone take about 0.14. So 0.14 needs a formula with **no case split**,
  i.e. one that is correct for every `n` in a handful of ops.

**Tried and worse** (n = 14 / 36):
- **`Bool.rec`/`Nat.ble` dispatch:** same as `Nat.rec`.
- **Divisor as `pow 32768 (n+35)`:** +0.6k.
- **`mod 32768` instead of `land 32767`:** +0.4k.
- **Sharing `15n` between the test and the formula:** +1–2k.
- **The formula in its own definition:** +3–5k.
- **Branches without the closure:** +2k.
- **`abbrev impl`:** +26k.
- **Returning the answer wrapped in `OfNat` like the judge's literal:** +22k.
- **Raw `135` (with `OfNat`) instead of `nat_lit` in a constant `impl`:** +8k.

## Tools

- **`kb/kbench.py`:** the judge's statement, with reference answers.
- **`kb/kbself.py`:** the same, with `--vals v1,...`, to time any expression (for micro-experiments).

## Rung 1 of the analytic route: the soundtrack for parts ≤ 3 (Oct 26)

Jonathan's picture:
- The floor holds the 1s.
- Each level adds marks where a 2 or a 3 can be added.
- The answer is then an equation that "plays" these levels as waves.

This is Sylvester's wave decomposition (1857). Rung 1 proves it for parts ≤ 3 in Lean.

**File:** `research/waves/Waves.lean` on the PC, about 200 lines, with a README.
- Built against Mathlib at the challenge's pinned revision, with `warningAsError`.
- No `sorry`; axioms `propext`, `Classical.choice`, `Quot.sound` only.

**What it proves:**
- **`card_restricted_le_three_eq`:** `#(Nat.Partition.restricted n (· ≤ 3)) = ((n+3)² + 6) / 12`,
  i.e. `round((n+3)²/12)`, for every `n`. The proof goes through the multiplicity-triple bijection.
- **`p3_waves`:** over ℝ, `p₃(n) = (n+3)²/12 − 7/72 + (−1)ⁿ/8 + (2/9)·cos(2πn/3)`.
  - The first part is the drone from the floor.
  - The second is a note of period 2.
  - The third is a note of period 3.
- **`soundtrack3_eq`:** the same formula in kernel `Nat` primitives (4 operations).

**Kernel cost:** 224.5k at n = 36, 224.2k at n = 10⁶ and 236.6k at n = 10¹². It is flat in `n`.

**The ladder from here.**

Mathlib (pinned) already has:
- Euler's pentagonal theorem;
- the partition generating function;
- the Dedekind eta function, with its log-derivative equal to E2;
- E2's transformation law.

The next rungs:
- **Rung 2:** η(−1/z) = √(−iz)·η(z), the change of perspective.
- **Rung 3:** the circle method and Rademacher's series with an explicit error bound. This is
  what scales to all `n`. The general Durfee path costs 1.45M at n = 100, 50M at n = 300,
  4.9B at n = 1000 and 195B at n = 3000, about n^3.5.
- Rademacher's series needs 3, 4, 5, 6, 8 and 13 terms for n = 36, 100, 200, 500, 1000 and 2000.
