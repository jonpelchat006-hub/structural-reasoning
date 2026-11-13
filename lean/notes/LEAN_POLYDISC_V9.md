# Lean Kernel Challenge — polydisc v9: the D5 core, proved once (Oct 20, 2026)

Jonathan, Oct 20: *"you can do that proof"*.
- This followed the problem atlas (Test 1 in `PROBLEM_ATLAS.md`).
- The atlas said polydisc's biggest lever is to prove the PRS structure once, so the D5 steps can keep only the low bits they need.

## What is proved (core Lean, no Mathlib, about 2,700 lines)

| Part | Statement | Lean |
|---|---|---|
| Determinants | Leibniz expansion along the first column, row operations, block operations, scaling | `det`, `det_rowop`, `det_blockOp` |
| Permutation bound | `|det| · k^N ≤ N! · ΠU · ΠV` whenever every entry satisfies `|M r c| · k ≤ U r · V c` | `det_bound` |
| Subresultant chain | Each normal-PRS polynomial is a subresultant determinant, and every division `prem / lc²` is exact, provided the leading coefficients are nonzero | `chain_val`, `chain_exact` |
| Bridge to the spec | On chain functions, the spec's `normalResultant` returns the last chain constant. The pseudo-remainder needs no `c₁ ≠ 0` | `normalResultant_chain`, `prem_eq'` |
| Size certificates | There are 23 certificates of integer potentials (the dual of a max-weight assignment), checked by the kernel in about 10 s. They give `|coefficient of F_k| < 2^(q_k − 1)` | `certOK`, `sres_lt`, `chain_bound` |
| Low-part step | Residues mod `2^q`; `sh = v₂(lc)` (checked); odd-part inverse by Newton; folded multipliers | `coef_spec`, `mult_cong`, `lstep_spec` |
| Whole run | No failed check means the result is the spec's `normalResultant` | `lrunR_spec`, `lowRun_spec` |
| Graph | 7,877 nodes, linked to the structured run by kernel `rfl` in about 2 s | `lowDag_eq` |

## The D5 step as built

Each chain polynomial `F_k` is stored as residues mod `2^(q_k)`, using one certified width per polynomial.

**Per step:**
- `sh = v₂(lc F_k)`, found by a gcd and a de Bruijn lookup. Two bit checks verify it, so the lookup itself needs no proof.
- `M = 2^(q + 2·sh)`.
- `inv` is the inverse of the odd part `o` mod `2^(q+128)`, by Newton.
- The multipliers fold the division in:
  - `w = lg·inv`
  - `m₁ = w²`
  - `m₂ = ∓(w << sh)`
  - `m₃ = inv·(±(g₁ << sh) − f₁·w)`
  - This works because `lf/o² = ±2^sh/o`.

**Per coefficient:**
- Three products of the multipliers with the residues.
- Sign corrections.
- One shift, one mask.

**First pricing (Lean's GMP, one D5 input):**

| Design | Graph nodes | GMP per case |
|---|---|---|
| v7/v8 (full numerators, exact division) | about 7,800 | 507M |
| Low part, inverse product per coefficient | 11,602 | 305M |
| + inverse folded into the multipliers | 11,464 | 276M |
| + residue storage (no sign-magnitude per coefficient) | 7,689 | 282M |
| **+ odd-part inverse and shift trick for the multipliers (v9)** | **7,877** | **244M** |

## Results

Replay-window instruction counts (callgrind on the timer kernel), with v8 and v9 measured on the same points.

| Case | v8 | v9 | Change |
|---|---|---|---|
| D5, n = 5537077001796702766 | 556.83M | 300.16M | −46.1% |
| D5, n = 2500179613334273093 | 557.40M | 300.88M | −46.0% |
| D3, n = 1099511628553 | 34.25M (v8 mean) | 34.16M | unchanged (same code) |
| D1, n = 300000 | 11.43M (v8 mean) | 11.37M | unchanged (same code) |
| **polydisc total (2 cases per group)** | **1,205.3M** | **about 692M** | **about −43%** |

The −43% beats the atlas estimate of −30%. The residue storage and the folded multipliers cut both the GMP work and the node count below the first pricing.

## Checks

- **Strict build:** `warningAsError` passes in 94 s.
- **Axioms:** `impl_correct` uses only `propext`, `Classical.choice` and `Quot.sound`.
- **Official local judge:** accepted, all six public cases OK.
  - The correctness replay takes 33.8 s with a 1.32 GB peak; the limit is 4 GB.
  - The D5 cases take 0.05 s wall each.
- **Robustness:** the graph simulated on 40 random D5 inputs gave the right discriminant with no fallback.
  - A failed check (`v₂(lc) ≥ 64`, a zero leading coefficient, or discriminant 0) falls back to the v7 path, so it stays correct.
- **Size:** 950,505 bytes; the limit is 1 MiB.
- **Location:** `submissions_v6/polydisc/Submission.lean` on the PC. The dev modules and generators are in `research/polydisc_v9/`.
- **Not submitted.** Submitting needs Jonathan's SAIR login.

## Kernel lessons

- **Lazy delta unfolds the higher definition.** A low-height wrapper compared against a high-height graph node makes the kernel unfold the graph node on open terms. `List.headD` and `cond` have height 1; `Nat.land` has height 11. In that case the kernel unfolded `Nat.land` through `Nat.bitwise`, and memory went past 6 GB.
  - Fix: wrappers whose bodies mention every graph operation (height 13) and are plain matches (`hd0`, `cnd`).
  - Pass results by continuation instead of `Prod` projections.
  - The `rfl` link went from more than 30 s and 7 GB to 2 s and 1.7 GB.
- **Arithmetic acceleration.** `Nat.log2` is not accelerated; `Nat.gcd` is. `natdag%` now accepts `gcd`.
- **Unchecked computation plus a cheap check.** The shift `sh` comes from a lookup table and is never proved; two bit tests prove the property that is needed.
