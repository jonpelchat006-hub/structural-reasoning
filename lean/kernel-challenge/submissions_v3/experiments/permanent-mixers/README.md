# Permanent: one-row lane bound

This candidate retains the current V3 shared row expression and reduces packed-DP lane width. Despite this experiment directory's original name, it does not pack the two mixers together.

The initial packed DP has one nonzero lane with value 1. The first row shifts that lane by three distinct column offsets, so every resulting lane is still at most 1. Each later row can increase a lane by at most a factor of 3. The strengthened bound is therefore `hl k m <= 3^(k-1)` (with truncated Nat subtraction), replacing `3^k`.

At the published dimensions, lane widths change from 10/20/26 bits to 8/18/24 bits. This reduces the size of the large integers used for DP shifts and additions. The universal proof and the small-dimension spec fallback are retained.

## Validation

- Strict Lean 4.33.1 build with `autoImplicit=false`, `warningAsError=true` passes for Submission, Baseline, and the unchanged evaluator Solution bridge.
- `Submission.impl_correct` uses only `propext`, `Classical.choice`, and `Quot.sound`.
- Six default published-dimension inputs (seeds 1 and 2) pass 31 synchronous kernel checks per implementation.
- Fourteen additional inputs cover dimensions 0, 2, 3, 4 and dimensions 6/12/16 with seeds 0, 7, and 0xffffffff. They pass 15 synchronous kernel checks per implementation.
- No website submission or official instruction replay was performed.

## Local timing

Numbers are local Windows synchronous `Kernel.Environment.addDeclCore` wall times from `scripts/bench_v3_kernel.py`. Each ratio compares alternating baseline/candidate runs. They are not official instruction counts.

| Dimension | Seed | Candidate / current V3 | Candidate / V2 |
|---|---|---|---|
| 6 | 1 | 1.016 | 0.728 |
| 6 | 2 | 1.012 | 0.725 |
| 12 | 1 | 0.763 | 0.687 |
| 12 | 2 | 0.792 | 0.670 |
| 16 | 1 | 0.878 | 0.896 |
| 16 | 2 | 1.071 | 0.976 |

Sum of the six per-case medians:

- Against current V3: 14.0486 ms candidate versus 14.9966 ms baseline, 6.3% lower.
- Against V2: 15.6314 ms candidate versus 17.4934 ms baseline, 10.6% lower.
- The extended set's aggregate median sum is 3.8% lower than current V3 and 14.5% lower than V2.

Dimension 12 consistently benefits; dimension 16 remains variable, including a regression for seed 2 against current V3 in this run. The candidate is worth comparing with V2 and current V3 in the playground. Its narrower representation is proved, but official instruction improvement is not yet established.

Raw reports include every sample, input, source hash, toolchain version, and axiom output. The scratch package is `.v3-work/permanent-mixers`; its `Baseline.lean` currently contains V2, and `BaselineCurrentV3.lean` preserves the current V3 baseline. Candidate source is `Submission.lean` in this directory. No existing V2 or current V3 submission was edited.

## Further reduction

A two-row coefficient bound of 2, followed by factors of 3, could reduce dimension 12's width from 18 to 17 bits, but would leave the other published dimensions at 8 and 24 bits. It requires proving that the sum of two powers of two determines their unordered exponent pair. This is a possible follow-up; it is not implemented here.
