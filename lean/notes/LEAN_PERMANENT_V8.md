# Lean Kernel Challenge — permanent v8 (Oct 25, 2026)

File: `submissions_v6/permanent/Submission.lean` on the PC (single file, about 355 KB), with a README.

Board when we started: 1st 29,436,124; main 49,185,317; us (v7) 89,586,544 in 9th.

## Status

- Strict build in the official workspace (`warningAsError = true`), no warnings.
- Axioms: `propext`, `Classical.choice`, `Quot.sound` only.
- Local judge (`evaluation/run.py`): accepted, all 15 public cases OK.
- **Delivered final (v8e, Oct 25), local valgrind counts on the 15 public cases:**
  - R1 (d = 6) 4.20M;
  - R2 (d = 12) 7.73M;
  - R3 (d = 16) 16.01M (3.04 / 3.98 / 2.96 / 3.34 / 2.69M).
  - **Total 27.94M**, against v7's 48.87M local / 89.59M official.
- **Page faults in the window:** about 98 in v8e (all in R3), 302 in the first draft, 5,967 in v7.
  - The official counter pays about 6.8k instructions per fault: (89.59 − 48.87)M / 5,967.
  - So v8e's official count should be about 28.6M. The current 1st is 29.44M.
- **Versions this round** (all accepted by the local judge, strict build, 3 axioms):
  - **v8 draft:** cnt labels. Total 29.23M.
  - **v8b:** cs labels (Σ over rows of the row's counts). R3 16.70M.
  - **v8c:** f2 labels (`64·cnt − Σ f(cnt)` over co-row columns, `f(1) = 3`, `f(2) = 1`). R3 16.75M,
    faults 98.
  - **v8d:** + `Bool.rec`/`Nat.beq` dispatch with `@[implemented_by implC]`. Total 28.54M.
  - **v8e:** + 10-bit lanes. Guard `< 2^8` at levels 6–14; the worst lane over 1,500 seeds was 129.
- Jonathan submits (SAIR login).

## What changed

- **d = 6 and d = 12 keep v7's code. d = 16 gets a new algorithm.**
- **Generating-function DP.** Give column `c` the weight `2^λ(c)`, where `λ` is a bijection onto
  `0..15`. Then `per = [x^T] Π_rows (x^lo + x^mid + x^hi)` with `T = 2^16 − 1`. Sixteen powers of
  two sum to `2^16 − 1` only when they are distinct, so no subset masks are needed.
- **One big number holds the polynomial.** It uses 10-bit lanes (v8e; 11 in the first draft).
  - **Phase 1 (rows 0–6):** left shifts, with lane 0 standing for the weight `Σ lo`.
  - **Rebase at row 7.** Lane `i` then stands for the weight `i + T − D_7`, where `D_7` is the sum
    of the remaining rows' `hi`.
  - **Phase 2:** right shifts.
  - **Trims** at levels 10, 12 and 14 keep only lanes that can still reach `T`, which is a suffix
    sum of `hi − lo`.
  - **Last row:** read three lanes and add.
- **Run-time checks.** If any fails, the code falls back to `main 16 s`.
  - The weights sum to `T`.
  - The row-order one-hot is a permutation.
  - Guard bits 9–10 of every lane are clear at levels 6–14.
  - `C1 + PRE < 2^17`.
- **Heuristics, lane-parallel.** Labels are ranked by touch count. Rows are sorted by `hi` and
  placed in a vee order.
  - The proof never looks inside them. It only needs their outputs masked to 5 bits.
  - So either heuristic can be changed without touching the proof.
- **Cost model (Python DSL `p8/`).** About 306 big ops per case.
  - Setup is about 1.14M: columns, one-hots, labels, weights, sorting and permuting.
  - The DP is about 1.33M, and checks plus the last row about 0.27M.
  - Modelled memory is about 0.7 MB per R3 case (about 170 page faults). v7 had about
    1000–1400 faults per R3 case.
- **Tuning.** It was rechecked with page-fault weighting (about 1.66 instructions per byte
  allocated).
  - The split at m = 7 and trims at (10, 12, 14) are still best.
  - Trimming at the rebase, more trims, and m = 6 or 8 were all worse.
  - Ordering rows by the diagonal label instead of sorting by `hi`: +15% (rejected).

## Proof structure (`Submission.P8`)

- **`#flatten` metaprogram.**
  - The structured definitions are the source of truth. `mainV16` is their unrolled DAG, linked
    by `mainV16.eq` (kernel `rfl`).
  - The flattened definition needs a reducibility height above the source's height. Otherwise the
    kernel unfolds `Nat.add` on big literals during the `rfl`.
- **Lane library.**
  - `enc` encodings, plus nested lanes (`enc_nest`, `enc_nest32`).
  - Disjoint-bit sums (`tsum`/`sep`) and multiplication as convolution (`enc_mul_conv`).
- **Stages:**
  - `rowV_eq`;
  - `labRK_lanes`, `eV_eq`, `chkE_spec`;
  - `eRev_eq`, `oV_eq`;
  - `lohi_vec`;
  - `ohQ_eq`, `permchk`, `permV_eq`.
- **DP:**
  - `F`, `P1st_eq`;
  - `rebase`, `Inv_step` and `ph2_inv` (trims and guard checks);
  - `lastRow_eq`, `dp16_eq`.
- **Glue:**
  - `gat32_enc`, `c1V_eq`, `preV_eq`, `remW_eq` (suffix sums through `conv_suf`);
  - `sort3'` (non-strict sort of a triple);
  - `order_perm` (the row order is a permutation of `range 16`);
  - `cnt_perm` and `spec_cnt`;
  - then `fastS16_eq` and `impl_correct`.
- **Lean pitfalls hit this round.**
  - `generalize` on a function misses beta-reduced occurrences. Use
    `obtain ⟨f, hf⟩ : ∃ f, ∀ i, f i = …`.
  - `split` fails on `(fun m => if …) m`. Run `dsimp only` first.
  - `Nat.mod` written in a `show` does not match the `%` patterns of `rw`. Write `%`.
  - Parallel lake builds (3 at once) ran out of memory on the 7 GB container (exit 137).

## What was tried this round and dropped

- **Literal-first commutative ops in the flattened DAG.** +240k per R3 case. The kernel copies
  the first operand of a big op, so a big literal should be the second argument.
- **Greedy cover labels** (H2, sequential min-uncovered-count).
  - In the model with constant weights it was −24% on R3. In the kernel it needs 16 sequential
    steps, too many ops.
  - A one-round batch refinement (b1) nets only about −0.1M per case. Not done.
- **The generating-function algorithm at d = 12.** The model gave 8.7M against v7's measured
  7.8M; setup dominates.
- **Ordering rows by diagonal label, other vee patterns, other trims, and m = 6 or 8.** All worse.
- **W = 9 lanes.** −0.4M more in the model, but the guard `< 2^7` was hit by 1 of 1,500 seeds, too
  risky.

## Official result and the unexplained overhead (Oct 26)

v8e scored **31,460,683** officially, which is **2nd** (1st: 29,436,124). The local count was 27.94M,
so the official counter added **3.52M**. The page-fault model had predicted +0.67M.

| Model of the official overhead | Fit on v7 (+40.72M) | Prediction for v8e | Actual |
|---|---|---|---|
| 6.8k per local page fault (v7: 5,967 faults) | exact by construction | +0.67M (98 faults) | +3.52M |
| proportional to local GMP work (v7: 23.3M → k = 1.75) | exact by construction | +13.2M (GMP 5.55M in R3 + 2.0M in R1/R2) | +3.52M |

Neither model fits.

**Local page faults are sensitive to the process's memory history.** The R2 code (d = 12) is identical
in v7 and v8e. Yet it had 295 faults in the window under v7 and 0 under v8e (`kpf.py`, Oct 26). For v8e
the R3 cases have 0–88 faults each.

**Other problems, official minus local:**

| Problem | Official − local | Per case |
|---|---|---|
| sha256 | −19M | −3k |
| partition | +9k | +1.4k |
| mertens | +45k | +7.5k |
| ca-rule110 | +251k | +42k |
| permanent v8e | +3.52M | +235k |

So the overhead grows with the size of the numbers and the memory the case touches. It is not a
per-operation cost.

**To win 1st** we need about 2.0M less official. Without the official counter we cannot tell which
memory change pays. A playground run (SAIR, 2 per day, Jonathan's login) that shows per-case official
counts would calibrate it.
