# Rule 110 v8 design: a 2-operation step (prototype, Nov 12 2026)

**Status: measured prototype, no proof yet. Nothing here is a submission.** The current entry is still v7
(`submissions_v4/ca-rule110`, official 3,977,952, 20th of 56 on Nov 12).

## The idea

Rule 110 is one bit of a weighted sum. Give each cell an 8-bit (or wider) lane holding `8·cell + 1`: the cell
at bit 3 and a helper bit at bit 0. Multiply the whole row by `K = 2^(2w) + 3·2^w + 11` (lane width `w`). Each
lane then holds

`8·(l + 3c + 11r) + 15`

for its left, centre and right cells. Bit 5 of that number is Rule 110 of `(l, c, r)`, and bit 2 is always 1.
So one mask keeps the new cell and the next step's helper bit, in the same `8·cell + 1` form, moved up by
`w + 2` bits. A step is one multiplication by a small constant and one `land`: 2 kernel operations instead
of v7's 6.

`rule110_weighted_sum.py` checks all 8 neighbourhoods and lists the other weight sets. Two facts from the
searches:
- no weight set works without an added constant, so the helper bit (or an extra `add`) is needed;
- two fused steps are not a single bit of a weighted sum for any modulus up to 256 (`two_step_search.c`).

## The pipeline (design B)

| Stage | Operations | What it does |
|---|---|---|
| mixer | 12 | 256 lanes of 65 bits, one per cell. The seed is folded into the lane constant (`n·cR + K0`, no `land` to extract the seed). The cell is lane bit 31. |
| gather | 1 | `% (2^256 − 1)`. Ring index `i` (cell `(i − 8) mod 256`) lands at bit `(w·i + 3) mod 256`: a dense, permuted row. |
| expand | 3 | Multiply by `Σ_j 2^(256j)`, mask, add the helper bits. Ring index `i` sits at bit `w·i + 3` for `i < 272`, so an 8-cell halo on each side comes for free and the row is not tripled. |
| steps | 2 per step | `land MASK_k (mul K Y)`. |
| finish | 5 (`w = 9`) or 3 (`w = 19`) | Multiply-and-mask stages pack the cells back together; the last `%` leaves the 256-bit row. |

Total: `21 + 2t` operations for `w = 9` (`19 + 2t` for `w = 19`), against `20 + 6t` in v7.

## Measured (callgrind, judge's replay window, the six public cases)

| Case | v7 (current) | spread gather, `w = 8` | design B, `w = 9` | design B, `w = 19` |
|---|---|---|---|---|
| 2 steps, seed 1 | 511,301 | 500,884 | 470,915 | 467,101 |
| 2 steps, seed 2 | 513,224 | 500,833 | 471,223 | 467,759 |
| 4 steps, seed 1 | 596,233 | 535,384 | 506,601 | 502,761 |
| 4 steps, seed 2 | 597,209 | 534,463 | 504,505 | 501,371 |
| 8 steps, seed 1 | 751,588 | 589,490 | 561,624 | 563,213 |
| 8 steps, seed 2 | 753,194 | 589,989 | 562,168 | 563,364 |
| **Total** | **3,722,749** | 3,251,043 | **3,077,036** | **3,065,569** |

- The v7 total reproduces the Oct 3 figure (3,722,688), so the bench matches the earlier sessions.
- Design B is −17.5% locally. A step costs about 10.5k, against about 35k in v7.
- v7's official count is 255k above its local count. With the same margin, design B would score about
  3.3M, which is around 11th on the Nov 12 board (10th 3,261,423; 11th 3,431,791).
- The first version gathered straight into the spread layout with `% (2^2232 − 1)`. That division alone
  cost about 70k per case; design B's small gather plus one multiplication and mask replaces it.
- `w = 9` and `w = 19` are equal locally. `w = 9` keeps the numbers half as long, which should count for a
  little on the official counter.

## What is checked

- The Python model equals the judge's `ca_reference` on 512 cases per width (`t = 1…8`, 64 seeds each).
- The Lean prototype (`Proto_w9.lean`) replays in the judge's kernel against the reference answer on 17
  cases: the six public ones and 11 with random seeds.

## What is missing: the proof

`impl_correct` has to be rebuilt for the new branches (core Lean, no Mathlib). The pieces:
1. the lane library for 65-bit lanes (v7's `enc` lemmas are written for 64), plus the seed fold: the extra
   `2^48` in each lane disappears under the first xor-shift and mask;
2. the gather: single bits at `65ℓ + 31` reduce to distinct bits below 256 (254 of them, so never `2^256 − 1`);
3. the expansion: `R · Σ_j 2^(256j)` repeats `R` in blocks, and the mask keeps bit `w·i + 3`;
4. the step: lanes `8x + h` with `x, h ≤ 1`, the lane sum (at most 135, no overflow), `decide` over the 8
   neighbourhoods, and the window of valid lanes shrinking by one on each side per step;
5. the finish: the multiplication has no two terms on the same bit, so each stage is a sum of distinct powers;
6. the link to the spec's cyclic `stepRow` (as v7's `agree_step`, with a halo instead of three copies), and
   the kernel `rfl` between each unrolled branch and its structured form.

## Files

- `ca_v8_proto.py`: the model, the self-check and the Lean emitter (`check`, or `emit W OUT.lean`).
- `Proto_w9.lean`, `Proto_w19.lean`: measurement-only prototypes (raw literals, `impl` without a proof).
- `kbench.py`: counts instructions in the judge's replay window for any problem (needs the callgrind build
  of the timer kernel, as in `research/fib_planner/timer_control_callgrind.c`).
- `rule110_weighted_sum.py`, `two_step_search.c`: the searches.
