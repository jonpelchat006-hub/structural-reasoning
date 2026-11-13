# Lean: the Kernel Challenge entries

Entries to Stage 1 of the 2026 Lean Kernel Challenge (SAIR / Lean FRO). There are eight fixed problems. Each
is answered by one `Submission.lean` holding an algorithm `impl` and a full proof
`impl_correct : ∀ n, impl n = spec n`, and entries are ranked by how many instructions the Lean kernel
spends checking `impl n = v` on the test inputs. The problem statements, specs and judge belong to the
organisers and are not copied here: see <https://github.com/SAIRcompetition/lean-kernel-challenge>.

The kernel-checked library around P vs NP is a separate repository,
[pvsnp-lean](https://github.com/jonpelchat006-hub/pvsnp-lean).

## Latest entry for each problem

Board scores are kernel instruction counts from the official leaderboard, provisional, for submissions through
Nov 12 2026 00:00 UTC. Lower is better.

| Problem | Version | Folder | Board score | Place |
|---|---|---|---|---|
| permanent | v8t | `kernel-challenge/submissions_v6/permanent_v8t/` | 28,551,504 | 6 of 51 |
| polydisc | v9 | `kernel-challenge/submissions_v6/polydisc/` | 888,306,258 | 7 of 50 |
| fib | v9 | `kernel-challenge/submissions_v6/fib/` | 8,001,992 | 16 of 66 |
| mertens | v9 | `kernel-challenge/submissions_v6/mertens/` | 2,318,772 | 16 of 48 |
| primecount | v6 | `kernel-challenge/submissions_v4/primecount/` | 1,644,480 | 16 of 50 |
| sha256 | v8 | `kernel-challenge/submissions_v4/sha256/` | 10,222,243,224 | 16 of 50 |
| partition | v6 | `kernel-challenge/submissions_v6/partition/` | 1,462,922 | 20 of 64 |
| ca-rule110 | v7 | `kernel-challenge/submissions_v4/ca-rule110/` | 3,977,952 | 20 of 56 |

## What is here

- `kernel-challenge/submissions/` to `submissions_v6/` are every round of entries, oldest to newest. The
  README in a folder says which version of each problem it holds and how it was checked.
- `kernel-challenge/research/` is the work behind particular entries: the fib planner, the polydisc packed-lane
  and low-part methods, and the first rung of the partition "waves" idea. `ca_rule110_v8/` is an unfinished
  Rule 110 design that measured about 17% fewer instructions than v7 on a local build of the judge's kernel.
  It has no correctness proof, so it was never entered.
- `kernel-challenge/scripts/` has the two local benchmark scripts.
- `kernel-challenge/LEAN_KERNEL_CHALLENGE.md` is the running log.
- `notes/` has the session write-ups for individual entries and the Nov 12 review of the board.

## Files

**`kernel-challenge/`**

- [`LEAN_KERNEL_CHALLENGE.md`](kernel-challenge/LEAN_KERNEL_CHALLENGE.md) — Lean Kernel Challenge (SAIR / Lean FRO), Stage 1

**`kernel-challenge/research/`**

- [`SHA256_QUATERNION_SOURCE_MAP.md`](kernel-challenge/research/SHA256_QUATERNION_SOURCE_MAP.md) — SHA-256, Euler–phi, and quaternion source map

**`kernel-challenge/research/ca_rule110_v8/`**

- [`ca_v8_proto.py`](kernel-challenge/research/ca_rule110_v8/ca_v8_proto.py) — Rule 110, proposed v8 design: model, self-check and a measurement-only Lean prototype (no proofs).
- [`kbench.py`](kernel-challenge/research/ca_rule110_v8/kbench.py) — Count kernel instructions inside the judge's replay window (callgrind), for any problem.
- [`rule110_weighted_sum.py`](kernel-challenge/research/ca_rule110_v8/rule110_weighted_sum.py) — Rule 110: neighborhood (l,c,r) -> bit ((110 >> (4l+2c+r)) & 1)

**`kernel-challenge/research/fib_planner/`**

- [`analyze.py`](kernel-challenge/research/fib_planner/analyze.py) — Read a pricing pass and report, per bit length, the cheapest plans against v7's plan.
- [`batch_bench.py`](kernel-challenge/research/fib_planner/batch_bench.py) — Price many fib plans in one go: one module with a chain per plan ('cand<i>'), one Perf file with a
- [`bench_fib.py`](kernel-challenge/research/fib_planner/bench_fib.py) — Local kernel instruction bench for fib variants (adapted from bench_instr.py, Oct 18).
- [`make_v8.py`](kernel-challenge/research/fib_planner/make_v8.py) — Assemble fib v8 from v7: the chosen plan per bit length (unrolled by the planner), the v7 structured
- [`planner.py`](kernel-challenge/research/fib_planner/planner.py) — The fib planner (Oct 18, Jonathan's "cut at thresholds, pick the cheapest form per slice, assemble").

**`kernel-challenge/research/fib_planner/v9/`**

- [`make_v9.py`](kernel-challenge/research/fib_planner/v9/make_v9.py) — Assemble fib v9 from v8: new building blocks (exponent tables, the sg first doubling, the branched
- [`measure_impl.py`](kernel-challenge/research/fib_planner/v9/measure_impl.py) — Measure Submission.impl n = F(n) in the judge's window (callgrind) using a given lake project dir.
- [`pass_a.py`](kernel-challenge/research/fib_planner/v9/pass_a.py) — Price planner3 variants at fixed paired points (judge's kernel window, callgrind).
- [`pass_b.py`](kernel-challenge/research/fib_planner/v9/pass_b.py) — Pass B: the best planner3 plans per size at the v8 comparison points (paired with v8's chains).
- [`pass_c.py`](kernel-challenge/research/fib_planner/v9/pass_c.py) — Pass C: can neighbouring chains merge (one test fewer)? Price the larger chain on the smaller inputs.
- [`pfrun.py`](kernel-challenge/research/fib_planner/v9/pfrun.py) — Build a Submission, export impl n = F(n) for each n, run the page-fault timer natively (no valgrind).
- [`planner2.py`](kernel-challenge/research/fib_planner/v9/planner2.py) — Planner extension: branched end-games ('E').
- [`planner3.py`](kernel-challenge/research/fib_planner/v9/planner3.py) — Planner v3: v8's plan space plus
- [`xbench.py`](kernel-challenge/research/fib_planner/v9/xbench.py) — Generic kernel-window bench: defs 'Submission.x<i> : Nat → Nat' with bodies in 'n', one theorem

**`kernel-challenge/research/polydisc_lowpart/`**

- [`bound2.py`](kernel-challenge/research/polydisc_lowpart/bound2.py) — Tighter provable bound: /det/ <= (number of permutations) x (largest single permutation product).
- [`bound_price.py`](kernel-challenge/research/polydisc_lowpart/bound_price.py) — Can a PROVABLE bound fix the kept width tight enough to keep the D5 saving?
- [`bound_price2.py`](kernel-challenge/research/polydisc_lowpart/bound_price2.py) — Can a PROVABLE bound fix the kept width tight enough to keep the D5 saving?
- [`price.py`](kernel-challenge/research/polydisc_lowpart/price.py) — Price D5's PRS GMP work two ways with Lean's own GMP:
- [`subres_check.py`](kernel-challenge/research/polydisc_lowpart/subres_check.py) — Is our PRS step output exactly +-(the subresultant determinant)? Small random cases, exact integers.
- [`transpose.py`](kernel-challenge/research/polydisc_lowpart/transpose.py) — permanent: does the mirror (transpose, perm(A) = perm(A^T)) give a smaller DP? Exact state counts.

**`kernel-challenge/research/polydisc_packed/`**

- [`bench_poly.py`](kernel-challenge/research/polydisc_packed/bench_poly.py) — Replay-window instruction bench for polydisc (as bench_fib.py): builds SUBMISSION in a scratch copy
- [`cost.py`](kernel-challenge/research/polydisc_packed/cost.py) — Fast GMP price of an op list from the oracle grid (log-log bilinear interpolation).
- [`gen10.py`](kernel-challenge/research/polydisc_packed/gen10.py) — polydisc v8 generator with every lane constant as a graph input ("c" variables).
- [`gen8.py`](kernel-challenge/research/polydisc_packed/gen8.py) — polydisc v8 graphs: the packed normal PRS (D1: all 23 steps; D3: a packed prefix, then v7's
- [`halfgcd_model.py`](kernel-challenge/research/polydisc_packed/halfgcd_model.py) — Jonathan's head/tail split on polydisc's PRS (Lehmer / half-GCD style), priced with the GMP oracle.
- [`hybrid.py`](kernel-challenge/research/polydisc_packed/hybrid.py) — Packed prefix (segmented lanes) + v7 element steps for the tail: price every switch point.
- [`merge.py`](kernel-challenge/research/polydisc_packed/merge.py) — Merge v7's generator graph (genLaneXC) with its PRS graph (prsDag) into one natdag: no 49-argument
- [`mkbands.py`](kernel-challenge/research/polydisc_packed/mkbands.py) — Lean band theorems (pkX_ok) for the configured bands, from the generator's plan.
- [`mkbase.py`](kernel-challenge/research/polydisc_packed/mkbase.py) — Base.lean = v7 (impl removed, impl_correct turned into fastDisc_spec) + packed definitions + band
- [`mkfinal.py`](kernel-challenge/research/polydisc_packed/mkfinal.py) — Final single-file polydisc v8 Submission.lean = Base (generated) + Dev (proofs).
- [`mkproto10.py`](kernel-challenge/research/polydisc_packed/mkproto10.py)
- [`packdag.py`](kernel-challenge/research/polydisc_packed/packdag.py) — Packed normal PRS for polydisc as a Nat expression graph (natdag-style), with real values.
- [`packed_model.py`](kernel-challenge/research/polydisc_packed/packed_model.py) — Packed PRS: every polynomial is ONE integer F(B) (Kronecker evaluation at B = 2^W); a normal step is
- [`prs_model.py`](kernel-challenge/research/polydisc_packed/prs_model.py) — polydisc: the v7 normal PRS in Python, with every product/division logged by operand size.
- [`robust.py`](kernel-challenge/research/polydisc_packed/robust.py) — How often does the packed path fall back? Simulate the exact v8 graphs on random inputs.
- [`search.py`](kernel-challenge/research/polydisc_packed/search.py)
- [`seg.py`](kernel-challenge/research/polydisc_packed/seg.py) — Choose lane-width segments for the packed PRS by dynamic programming over the 23 steps.

**`kernel-challenge/research/polydisc_v9/gen/`**

- [`bench_poly9.py`](kernel-challenge/research/polydisc_v9/gen/bench_poly9.py) — Replay-window instruction bench for polydisc (as bench_fib.py): builds SUBMISSION in a scratch copy
- [`brk.py`](kernel-challenge/research/polydisc_v9/gen/brk.py)
- [`brk2.py`](kernel-challenge/research/polydisc_v9/gen/brk2.py) — tag ops by the function that created them
- [`brk3.py`](kernel-challenge/research/polydisc_v9/gen/brk3.py)
- [`cbisect.py`](kernel-challenge/research/polydisc_v9/gen/cbisect.py)
- [`cert.py`](kernel-challenge/research/polydisc_v9/gen/cert.py) — Size certificates for the D5 band: integer potentials u, v with bnd(r,c) * 2^K <= 2^(u_r) * 2^(v_c)
- [`lowdag.py`](kernel-challenge/research/polydisc_v9/gen/lowdag.py) — polydisc v9: the low-part normal PRS for the D5 band, as a hash-consed Nat graph.
- [`lowdag2.py`](kernel-challenge/research/polydisc_v9/gen/lowdag2.py) — polydisc v9: the low-part normal PRS for D5 with residue storage (two's complement, one width per
- [`memrun.py`](kernel-challenge/research/polydisc_v9/gen/memrun.py)
- [`mklowdag.py`](kernel-challenge/research/polydisc_v9/gen/mklowdag.py) — V9/LowDag.lean: the low-part graph (natdag%) and its kernel rfl link to the structured lowRun.
- [`mkv9.py`](kernel-challenge/research/polydisc_v9/gen/mkv9.py) — polydisc v9 = v8 + the low-part D5 run (V9 namespace) as the band-3484 continuation.
- [`perstep.py`](kernel-challenge/research/polydisc_v9/gen/perstep.py) — price each PRS step: low part vs v7's exact element step, on the exact chain of a D5 input
- [`perstep2.py`](kernel-challenge/research/polydisc_v9/gen/perstep2.py)
- [`rflpart.py`](kernel-challenge/research/polydisc_v9/gen/rflpart.py) — rfl tests of parts: init lists, then step-0 values
- [`rflscale.py`](kernel-challenge/research/polydisc_v9/gen/rflscale.py) — memory/time of the kernel rfl link for the first K low steps

**`kernel-challenge/scripts/`**

- [`bench_instr.py`](kernel-challenge/scripts/bench_instr.py) — Local instruction-count bench (our tool, not the official judge).
- [`bench_v3_kernel.py`](kernel-challenge/scripts/bench_v3_kernel.py) — Compare kernel declaration-check wall time; NOT official instruction scoring.

**`kernel-challenge/submissions_v3/experiments/ca-rule110/`**

- [`NOTES.md`](kernel-challenge/submissions_v3/experiments/ca-rule110/NOTES.md) — Rule 110 candidate: shared mixer and two-step chunks

**`kernel-challenge/submissions_v6/permanent/`**

- [`README_v8d.md`](kernel-challenge/submissions_v6/permanent/README_v8d.md) — permanent v8 — packed generating-function DP for d = 16

**`notes/`**

- [`LEAN_FIB_PLANNER.md`](notes/LEAN_FIB_PLANNER.md) — Lean Kernel Challenge — the fib planner, fib v8 (Oct 18) and fib v9 (Oct 24, 2026)
- [`LEAN_KERNEL_CHALLENGE_V4.md`](notes/LEAN_KERNEL_CHALLENGE_V4.md) — Lean Kernel Challenge — optimisation pass v4 (Oct 3, 2026; latest: fib v7, polydisc v7, ca-rule110 v7, permanent v7)
- [`LEAN_PARTITION_V6.md`](notes/LEAN_PARTITION_V6.md) — Lean Kernel Challenge — partition v6 and the cost floor (Oct 26, 2026)
- [`LEAN_PERMANENT_V8.md`](notes/LEAN_PERMANENT_V8.md) — Lean Kernel Challenge — permanent v8 (Oct 25, 2026)
- [`LEAN_PERMANENT_V8T.md`](notes/LEAN_PERMANENT_V8T.md) — Lean Kernel Challenge — permanent v8t (Oct 27, 2026)
- [`LEAN_POLYDISC_PACKED.md`](notes/LEAN_POLYDISC_PACKED.md) — Lean Kernel Challenge — polydisc v8: packed lanes (Oct 19, 2026)
- [`LEAN_POLYDISC_V9.md`](notes/LEAN_POLYDISC_V9.md) — Lean Kernel Challenge — polydisc v9: the D5 core, proved once (Oct 20, 2026)
- [`LEAN_REVIEW_NOV12.md`](notes/LEAN_REVIEW_NOV12.md) — Lean Kernel Challenge: the newer research, the board on Nov 12, and a Rule 110 lead
