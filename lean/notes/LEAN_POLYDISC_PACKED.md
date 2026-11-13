# Lean Kernel Challenge — polydisc v8: packed lanes (Oct 19, 2026)

Jonathan, Oct 19:
- *"we could do that on higher levels too right? might have to see how else we can combine them, or if they can transfer ownership of the numbers."*
- The context was the head/tail split (Lehmer, half-GCD) and his octonion idea: two glued quaternions, used to chunk big numbers.

## What was tried

| Idea | Result |
|---|---|
| Head/tail split, one level and recursive | Correct, but never cheaper at degree 24. k = 2 changes the cost by 0.0%; k = 11 makes it 25% worse. The expensive steps are the last ones, where the polynomials are short and the numbers huge. |
| One shared division across lanes | 2.5–3× slower than separate exact divisions, because the quotient lanes must be padded. |
| **Packing: a whole polynomial as one number** | **Large win wherever per-operation overhead dominates (D1, D3).** |
| Packing D5 | Loses. D5 is GMP-bound, and the proof needs lanes 3× the coefficient width. |
| Merging the generator and PRS graphs | Saves only 0.36M on D5. Not used. |

## Where v7's time went

| Case | Total | Where it goes |
|---|---|---|
| D1 | 42.2M | The 7,777-node graph at about 5k instructions per node; GMP work is only about 2M |
| D3 | 53.0M | About 45M overhead; GMP 7.5M |
| D5 | 557M | GMP 489M: products 298M, exact divisions 191M |

## The v8 design

**Each polynomial is one number.**
- The polynomial is held as its value `Ŝ(B)` at `B = 2^W`, sign-normalized so the leading coefficient is positive. The sign is kept as a bit.
- Its offset form `Ŝ(B) + T·(1 + B + … + B^d)` (with `T = 2^b`) has every coefficient as one base-`B` digit `Ŝᵢ + T`.

**One step is two products, one division and five checks.** The step computes `R(B) = (lg²·F̂(B) − (lf·lg·B + c₁)·Ĝ(B)) / dm`. That is about 40 graph nodes, where v7 needs about 340. The checks:
1. `c₁ ≠ 0`;
2. exact division (a remainder, or the low `2b` bits);
3. one AND with a lane mask (every digit below `2T`);
4. one shift (no digit above the degree);
5. leading digit `> 0`.

**The proof idea: lanes 3× wide.**
- The packed integers satisfy `±N(B) = dm·H(B)`.
- The mask check bounds every digit of `H`. With `W ≥ 3b + 3`, every coefficient of `E = ±N − dm·H` is then below `B`.
- An integer polynomial that vanishes at `B` with all coefficients below `B` is zero: its lowest nonzero coefficient would be a multiple of `B`. So the packed step is exactly the specification's coefficientwise step, divisibility included (`eq_map_of_ev`, `pstep_spec`).

**Transfer of ownership.** Lanes start narrow and are repacked wider as the coefficients grow (`prepack`). The two current polynomials are unpacked digit by digit and repacked in wider lanes.
- D1 uses two lane widths: 1,092 bits, then 1,857.
- D3 uses three: 2,115, 4,107 and 6,159 bits for its first 14 steps. Its last 9 steps go back to v7's coefficient-by-coefficient steps, which are cheaper once the polynomials are short and the coefficients large.

**Safety.** If any check fails, the run falls back to the v7 path, so correctness never depends on the lane sizes. The widths carry a margin of 2% + 16 bits over sampled coefficient sizes. Simulating the exact graphs on 3,000 random D1 inputs and 6,400 random D3 inputs gave 0 fallbacks.

## Results (judge's replay window, same random points)

| Group | v7 | v8 | Change |
|---|---|---|---|
| D1 (mean of 4 points) | 42.17M | 11.43M | −72.9% |
| D3 (mean of 4 points) | 52.97M | 34.25M | −35.3% |
| D5 (mean of 2 points) | 556.96M | 556.98M | unchanged |
| **polydisc total (2 cases per group)** | **1,304.2M** | **1,205.3M** | **−98.9M (−7.6%)** |

## Checks

- Strict build (`warningAsError`) passes.
- The axioms are only `propext`, `Classical.choice` and `Quot.sound`.
- The **official local judge accepts all six public cases**.
- The file is 684 KB; the limit is 1 MiB.
- It is `submissions_v5/polydisc/Submission.lean` on the PC. The research files are in `research/polydisc_packed/`.
- **Not submitted.** Submitting needs Jonathan's SAIR login.

## Kernel lessons

- **Big constants and rfl.** Never compare a graph that holds big closed constants against a structured term with kernel `rfl`.
  - The kernel may unfold `Nat.sub x C` with `C` a huge literal, peeling one off at a time. That gives deep recursion.
  - Fix: link the graph with every lane constant as a variable (`pkDagC…_eq`, open terms, checked in seconds). Then link that to the graph with the constants inside (`pkDag…_eq`, the same shape).
- **Application size.** Passing about 100 constants into a graph as arguments cost about 2.3M per case. Computing them inside the graph is cheaper.
- **Keep the elaborator away from the graphs.**
  - Mark the graphs `irreducible`.
  - Prove list application with a generic lemma (`appL_25`).
  - Never `unfold` a read-off whose argument is a graph; generalize it to a variable first.
  - Any of these mistakes ran the build out of memory.

## Next

- **D5 is 92% of polydisc.** Its GMP work is close to the minimum for a subresultant PRS done in the kernel's GMP: 3 products and 1 exact division per coefficient. Packing it would triple that work.
- **The certificate is the hard limit.** Proving a packed step needs about 3× the coefficient bits of evaluation information, which is why lanes must be 3× wide. Two evaluation points need the same total.

## Oct 19, evening: "put the junk in the ratio part and only look at the rest"

Jonathan: *"if theres a lot of junk, couldnt we put it in the ratio part, and then only look at the rest? we would want to see how big each piece we have is and then each part would have a size and cost to access it that we would want to match?"*

**D5's junk, measured** (`sizes.json`, per-step maximum coefficient bits):
- Each PRS step builds numerators of about `2·s(t+1) + s(t)` bits and keeps about `s(t+2)` bits.
- Between 56% and 66% of every number a step builds is the known factor `dm = lc(F)²`, which the exact division then removes.
- At the last step, 216k bits are built and 81k bits are kept.

**A "low part only" variant, priced with Lean's own GMP** (`gmpcost`, two random D5 inputs):
- Every product is truncated to the kept width `q`, using masks.
- The division becomes one `q×q` product with `dm⁻¹ mod 2^q`. The Newton inverse is computed once per step and priced as 3 `q×q` products.
- GMP cost goes from **469M to 287M per case (−39%)**. It adds about 1,150 kernel operations, roughly 7M.
- If it were sound, polydisc would drop by about 350M (about −29%).
- These figures use the measured widths. A provable bound would be somewhat wider, so the real saving would be smaller.

**Why it is not sound as a check.**
- The low part alone cannot detect an inexact division or an overflow.
- As found on Oct 3, 2-adic quotients are not sound with the aggregated check. Any check that proves exactness needs about `bits(N)` of information. This is the same 3× limit as the packed lanes.

**What would make it sound:** proving two facts once, in core Lean without Mathlib.
1. The subresultant theorem for normal sequences: every division `prem(F, G) / lc(F)²` is exact when every degree drop is 1.
2. A bound on each step's coefficient width, so that `q` is fixed in advance.

Both facts are classical. Formalizing them from scratch, with determinants and Sylvester submatrices, is large. This is the biggest lead left in polydisc and the most expensive one. It has not been started.

**Update, Oct 20:** both facts are proved and the low-part run is built as v9 (`LEAN_POLYDISC_V9.md`). D5 went from 557M to 300M per case.
