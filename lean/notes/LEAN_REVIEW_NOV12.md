# Lean Kernel Challenge: the newer research, the board on Nov 12, and a Rule 110 lead

*Nov 12, 2026. Stage 1 deadline: Nov 20, 23:59 AoE. Follows `LEAN_KERNEL_CHALLENGE_V4.md`, `LEAN_PERMANENT_V8T.md`, `LEAN_PARTITION_V6.md`.*

Jonathan, Nov 12: *"you can see if any of the newer research we did can go into the lean kernel challenge."*

## Short answer

- **Nothing in the research since Oct 27 lowers a kernel count.** That covers the P vs NP library, the 16 floor-flow parts and the Q-tube.
- **All eight latest entries are on the board.**
- **Rereading the entries gave one lead that has nothing to do with the research:** a Rule 110 step in 2 kernel operations instead of 6. A prototype measures 3.07M locally against 3.72M for the current entry (−17.5%). It has no proof yet.

## The board (official counts, submissions through Nov 12, 00:00 UTC)

| Problem | Our entry | Official | Rank | 1st | Places just above us |
|---|---|---|---|---|---|
| permanent | v8t | 28,551,504 | 6 of 51 | 23,929,510 | 5th 28,149,536; 4th 27,419,770 |
| polydisc | v9 | 888,306,258 | 7 of 50 | 631,894,932 | 6th 799,432,179; 5th 756,021,245 |
| fib | v9 | 8,001,992 | 16 of 66 | 3,717,308 | 15th 7,927,612; 10th 7,338,064; 2nd 6,615,816 |
| mertens | v9 | 2,318,772 | 16 of 48 | 1,504,216 | 15th 1,869,944 |
| primecount | v6 | 1,644,480 | 16 of 50 | 1,393,196 | 15th 1,571,070; 13th 1,515,477 |
| sha256 | v8 | 10,222,243,224 | 16 of 50 | 8,904,014,603 | 15th 10,219,979,922; 13th 10,182,298,373; 10th 10,100,416,959; 8th 10,034,441,544 |
| partition | v6 | 1,462,922 | 20 of 64 | 1,387,225 | 19th 1,458,640; 10th 1,451,363; 7th 1,431,500; 2nd 1,422,330 |
| ca-rule110 | v7 | 3,977,952 | 20 of 56 | 3,013,383 | 17th 3,814,311; 12th 3,553,850; 11th 3,431,791; 10th 3,261,423 |

The versions are inferred: each official count matches that version's local count with the usual margin.

**Official against local.**

| Problem | Local | Official | Difference |
|---|---|---|---|
| partition v6 | 1.454M | 1.463M | +0.6% |
| primecount v6 | 1.626M | 1.644M | +1.1% |
| mertens v9 | 2.281M | 2.319M | +1.7% |
| sha256 v8 | 10.242B | 10.222B | −0.2% |
| ca-rule110 v7 | 3.723M | 3.978M | +6.9% |
| permanent v8t | 25.05M | 28.55M | +14% (the estimate was 28.2M) |
| fib v9 | about 6.68M | 8.00M | +20% |
| polydisc v9 | about 692M | 888M | +28% |

The gap grows with the size of the numbers a case builds, as the Oct 26 calibration found (copies and fresh memory are charged). fib and polydisc were planned with local counts only.

**Other things the board shows.**
- **b-mehta is first on fib, partition, mertens and primecount.** The fib count (3.72M; 2nd is 6.62M) is about the fixed cost (1.13M) plus what GMP's own Fibonacci routine needs (2.62M by our Oct 24 measurement). That leaves almost nothing for per-operation overhead. I could not work out the method.
- **The small problems are decided by single operations.** On partition, places 2 to 20 lie within 40k (6.8k per case). On mertens and primecount the first ten entries are 27–50k per case above the fixed cost. Our fast paths use 6 big operations (primecount) and 17 (mertens). I don't know how the entries above us get so low; the v9 mertens README noted that such counts look more like a packed table than a computation.
- **The standings are provisional.** Final entries are re-evaluated under the confirmed rules after the deadline.

## The newer research against the eight problems

| Research | Where it might have applied | Verdict |
|---|---|---|
| `pvsnp-lean` (classes, barrier, SAT, decision trees, representation and refinement files, `Orientations`, `Resolution`, `Table`) | any | These prove statements about problems and about search tools (correctness, lower bounds in restricted models). None is an algorithm the kernel can run faster. |
| `Void.lean` (permanent minus the size of the determinant) | permanent | It measures what cancellation absorbs. The determinant gives no route to the permanent of these matrices. |
| `CountingWaves.lean` | partition | It is the Oct 26 waves rung in core Lean: parts of size at most 3 only. The partition entry needs all parts. |
| floor flow 1–5 (flow, heat, folding, resolution, keys) | permanent, polydisc | Heuristics for number partitioning; none is exact. "See only the coarse part" is the low-part idea, and polydisc v9 already uses it with a proof. |
| floor flow 6–7 (sheets and tape) | permanent | The tape filters a search that has many copies of the answer. The permanent's DP counts every choice exactly, with one target total. The "grid of reachable totals" is already the d = 16 algorithm. |
| floor flow 12 (meeting in the middle) | permanent | Meeting two half-products needs one coefficient of their product: one multiplication of two numbers of several hundred thousand bits. That costs more than the rows it would replace. |
| floor flow 8–10 (backbone, 3-SAT, XOR-SAT) | none | About the shape of solution spaces. |
| floor flow 11, 13–15 (SHA-256 cone, knots, crossings, overlap) | sha256 | About running the hash backwards and about collisions. Running it forwards costs one kernel operation per word operation. The structure that helps forwards (constant schedule words, constant early rounds) was already folded into v8. |
| floor flow 16 (Maass forms, trace formula) | mertens, primecount | No bearing at N ≤ 1000. |
| Q-tube (nested quaternions) | none | Floating-point learning experiments; no integer arithmetic. |

**What the newer work does offer** is the cost knowledge from Oct 25–27 (the copy and memory charges, gathers by `%` instead of multiplication, operand order). Three entries predate it: ca-rule110 v7, primecount v6 and sha256 v8 (all Oct 3).

## The Rule 110 lead (v8 design)

**The step.** Give each cell a lane holding `8·cell + 1`: the cell at bit 3 and a helper bit at bit 0. Multiply the row by `K = 2^(2w) + 3·2^w + 11` (lane width `w`). Each lane then holds `8·(l + 3c + 11r) + 15`. Bit 5 of that is Rule 110 of `(l, c, r)`, and bit 2 is always 1. One mask keeps both, which is the same `8·cell + 1` form moved up by `w + 2` bits. So a step is one multiplication by a small constant and one `land`.

Searches (`rule110_weighted_sum.py`, `two_step_search.c`):
- No weight set works without an added constant, so the helper bit is needed (or one more `add` per step).
- Two fused steps are not one bit of a weighted sum for any modulus up to 256.

**The pipeline (design B).**

| Stage | Operations | What it does |
|---|---|---|
| mixer | 12 | 256 lanes of 65 bits, one per cell. The seed is folded into the lane constant. The cell is lane bit 31. |
| gather | 1 | `% (2^256 − 1)`. Ring index `i` (cell `(i − 8) mod 256`) lands at bit `(w·i + 3) mod 256`: a dense, permuted row. |
| expand | 3 | Multiply by `Σ_j 2^(256j)`, mask, add the helper bits. Ring index `i` sits at bit `w·i + 3` for `i < 272`. The 8-cell halo on each side comes for free, so the row is not tripled. |
| steps | 2 each | `land MASK_k (mul K Y)` |
| finish | 5 (`w = 9`) or 3 (`w = 19`) | Multiply-and-mask stages pack the cells together; a last `%` leaves the 256-bit row. |

That is `21 + 2t` operations for `w = 9`, against `20 + 6t` in v7.

**Measured** (callgrind, judge's replay window, the six public cases):

| Case | v7 (current) | design B, `w = 9` | design B, `w = 19` |
|---|---|---|---|
| 2 steps (seeds 1, 2) | 511,301 · 513,224 | 470,915 · 471,223 | 467,101 · 467,759 |
| 4 steps | 596,233 · 597,209 | 506,601 · 504,505 | 502,761 · 501,371 |
| 8 steps | 751,588 · 753,194 | 561,624 · 562,168 | 563,213 · 563,364 |
| **Total** | **3,722,749** | **3,077,036** | **3,065,569** |

- The v7 total reproduces the Oct 3 figure (3,722,688), so this bench matches the earlier sessions.
- A step costs about 10.5k, against about 35k in v7.
- **Expected official count: about 3.3M**, using v7's margin of 255k. On the Nov 12 board that is around 11th (10th 3,261,423; 11th 3,431,791).
- A first version gathered straight into the spread layout with `% (2^2232 − 1)`. That division alone cost about 70k per case (total 3.25M). The small gather plus one multiplication and mask replaced it.
- The mixer is now the largest part: 12 operations on 16,640-bit numbers, about 145k per case.

**Checked.**
- The Python model equals the judge's `ca_reference` on 512 cases per width (`t = 1…8`, 64 seeds each).
- The Lean prototype replays in the judge's kernel against the reference answer on 17 cases (the six public ones and 11 random seeds).

**Missing: the proof.** `impl_correct` has to be rebuilt for the new branches, in core Lean:
1. the lane library for 65-bit lanes (v7's `enc` lemmas are written for 64), and the seed fold;
2. the gather: single bits at `65ℓ + 31` reduce to distinct bits below 256 (254 of them, so the value is never `2^256 − 1`);
3. the expansion: `R · Σ_j 2^(256j)` repeats `R` in blocks, and the mask keeps bit `w·i + 3`;
4. the step: lanes `8x + h` with `x, h ≤ 1`, lane sums of at most 135, `decide` over the 8 neighbourhoods, and the window of valid lanes shrinking by one per side per step;
5. the finish: no two terms of the multiplication share a bit, so each stage is a sum of distinct powers;
6. the link to the spec's cyclic `stepRow` (as v7's `agree_step`, with a halo instead of three copies) and the kernel `rfl` for each unrolled branch.

**Files** on the PC: `lean-kernel-challenge/research/ca_rule110_v8/` (`README.md`, `ca_v8_proto.py`, `Proto_w9.lean`, `Proto_w19.lean`, `kbench.py`, the two searches).

## Other leads, not built

| Lead | Basis | Expected effect |
|---|---|---|
| **sha256: the trimmed route** | Measured −0.58% on Oct 4 (`gen_trim.py`, no proof). | About 10.16B, 13th instead of 16th. The v8 generator is not on the PC, so it would have to be rebuilt first. |
| **primecount: one operation fewer** | Use 4 instead of 37 as the slot constant, so "prime" is a single bit; fold the shift into the divisor; mask with one literal. Not measured. | About −9k per case, to about 1.59M. No rank change (15th is 1.571M). |
| **fib: re-plan with the official cost** | The planner priced plans locally; the board charges about 20% more, mostly for big linear results. Not measured. | Unknown, probably a few percent. |
| **partition** | Places 10 to 19 are 0.7–1.9k per case below us. | No specific saving found. |

## Bench setup used here

- Lean 4.33.1 through elan; `scripts/setup.sh --tools-only` for comparator, lean4export and the timer kernel.
- A copy of the timer kernel built with `research/fib_planner/timer_control_callgrind.c`, so callgrind counts exactly the replay window.
- `kbench.py PROBLEM TAG SUBMISSION [inputs]` builds the judge's `impl n = v := Eq.refl v` theorems and reports one count per input.
