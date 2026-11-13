# permanent v8 — packed generating-function DP for d = 16

Single file: `Submission.lean`. Dimensions 6 and 12 keep v7's code; d = 16 has a new fast path
(`P8.mainV16`) with a fallback to the generic `main 16 s` when a run-time check fails.

Checked the same way as earlier rounds:

- strict build in the official `problems/permanent` workspace (`warningAsError = true`), no warnings;
- `#print axioms Submission.P8.fastS16_eq` (and `impl_correct`) shows only `propext`,
  `Classical.choice`, `Quot.sound`;
- local judge `evaluation/run.py --problem permanent`: accepted, all 15 public cases OK (correctness replay ok, computation replay complete).
- SHA-256 of `Submission.lean`: `714d9040f36bcb7e8f11c2efd272454a4412e5432559b365cd7b73e831f9133a`.

## Local counts (valgrind, judge replay window, 15 public cases)

| Group | v8 (this file) | v8 with 11-bit lanes | first v8 draft | v7 |
|---|---|---|---|---|
| R1 (d = 6) | **4.20M** (841k · 843k · 837k · 838k · 841k) | 4.20M | 4.18M | same code |
| R2 (d = 12) | **7.73M** (1.559 · 1.544 · 1.544 · 1.557 · 1.528M) | 7.73M | 7.80M | same code |
| R3 (d = 16) | **16.01M** (3,043,275 · 3,976,967 · 2,959,307 · 3,339,563 · 2,692,113) | 16.61M | 17.25M | about 36.9M |
| **Total** | **27.94M** | 28.54M | 29.23M | 48.87M (official 89.59M) |

**Page faults.** v7's official count was 1.83× its local count, and the gap is page faults.
v7 had 5,967 fresh-page faults in the window over the 15 cases. That is about 6.8k instructions
per fault in the official counter (89.59M − 48.87M = 40.7M).

| Version | Faults (R1 / R2 / R3) | Estimated official count |
|---|---|---|
| v7 | 0 / 295 / 5,672 | 89.6M (measured) |
| first v8 draft | 0 / 0 / ~300 | ~31.3M |
| **v8 (this file)** | 0 / 0 / ~98 | **~28.6M** |

The current 1st place is 29.44M.

**Changes since the first v8 draft.**

- **Better column labels** (still untrusted; the proof only needs the check).
  - The key is `64·cnt − g`, where `cnt` is the number of rows touching a column.
  - `g` sums `f(cnt)` over the columns that share a row with it, with `f(1) = 3`, `f(2) = 1`
    and `f = 0` otherwise.
  - Columns that touch few rows, and whose rows hold other rarely used columns, get the high
    weights.
  - This reduces `Σ hi`, the DP state size and the memory use (faults 302 → 98).
- **10-bit DP lanes** (was 11).
  - The guard check now asks for lanes `< 2^8` at levels 6–14 (guard bits 8–9). That keeps every
    three-term sum below `2^10`.
  - Over 1,500 random seeds the largest lane at those levels was 129, so the check never failed.
    The headroom is about 2×.
  - If the check does fail, the code falls back to `main 16 s`, which is slower but still correct.
- **Dispatch.** The d = 6 / 12 / 16 tests are `Bool.rec` on `Nat.beq`, which is cheaper than
  `Nat.rec` on a numeral.
  - Core Lean cannot compile `Bool.rec`, so `impl` has `@[implemented_by implC]`.
  - `implC` is the same selection written with `if`, and `implC_eq` proves the two agree.
  - This is the same pattern as ca-rule110 v7.

## The d = 16 algorithm

Give column `c` a weight `E c = 2^λ(c)` with `λ` a bijection onto `0..15` (labels from the heuristic
above, checked at run time). Then

`per = [x^T] Π_rows Σ_{c ∈ row} x^{E c}`, with `T = 2^16 − 1`,

because a choice of one column per row has weight `T` exactly when the 16 chosen labels are
distinct (16 powers of two summing to `2^16 − 1` must be `2^0 … 2^15`). No subset masks are needed.

- Each row has three columns (`i`, `a_i`, `b_i`), so each row multiplies the polynomial by
  `x^lo + x^mid + x^hi`. The polynomial is stored in 10-bit lanes of one big number.
- **Phase 1 (rows 0–6, sorted order):** base `Σ lo`, so a row is `S + S << (mid−lo) + S << (hi−lo)`.
- **Rebase at row 7:** shift so lane `i` stands for weight `i + T − D_7` (`D_7` = sum of the
  remaining rows' `hi`); lanes above `C1 = Σhi − T` can never reach `T`.
- **Phase 2 (rows 7–15):** `S + S >> (hi−mid) + S >> (hi−lo)`; at levels 10, 12, 14 the state is cut
  to the lanes that can still reach the answer (`rem k + 1` lanes, a suffix sum of `hi − lo`).
- **Last row:** read three lanes and add.
- **Checks** (any failure → `main 16 s`): the weights sum to `T` (labels valid and distinct); the row
  order one-hot has one row per step (a permutation); guard bits 8–9 of every lane are clear at
  levels 6–14 (so no lane overflows 10 bits); `C1 + PRE < 2^17` (the guard mask covers every lane).
- Everything before the DP (columns, one-hots, labels, weights, sorting each row's three weights,
  ordering the rows by `hi`, permuting the shift amounts, suffix sums) is lane-parallel arithmetic.

## Proof outline (`Submission.P8`)

- `fastS16_eq : ∀ s < 2^32, fastS16 s = permanentSpec (genPermanentMatrix 16 s)`, and
  `mainV16.eq : mainV16 s = fastS16 s` by kernel `rfl` (the `#flatten` command builds the unrolled
  definition from the structured one).
- Lane library: `enc` encodings, nested lanes, disjoint-bit sums, multiplication as convolution.
- Stage lemmas: `rowV_eq` (row one-hots), `labRK_lanes`/`eV_eq`/`chkE_spec` (weights), `eRev_eq`,
  `oV_eq` (row weight sums), `lohi_vec` (sorted triple), `ohQ_eq`/`permchk`/`permV_eq` (row order).
- DP: `F` (forward weighted counts), `P1st_eq` (phase 1), `rebase`, `Inv_step`/`ph2_inv`
  (phase 2 with trims and guard checks), `lastRow_eq`, `dp16_eq`.
- Counting: `F_cnt`, `cnt_perm` (row order does not matter), `spec_cnt` (the spec permanent is the
  weighted count for any injective labelling).
