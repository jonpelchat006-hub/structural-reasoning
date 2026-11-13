# Lean Kernel Challenge — the fib planner, fib v8 (Oct 18) and fib v9 (Oct 24, 2026)

Jonathan, Oct 18:
- *"our theta equation had those thresholds too, so we could set the max to that big size cut off right? and then we could recurse or collapse or expand when we hit it, so if theres a lot more work leftover and the big number thing becomes more efficient then we could use that."*
- *"would we want to cut all the numbers like a sheet? and then we would assemble those slices into an optimized closure equation? that reminds of the cutting in the protein folding stuff."*

## The idea, made precise

- **Thresholds.** The kernel has two measured cliffs:
  - numbers of 2^63 and above become GMP objects (about +2–2.7k per operation);
  - every operation carries about 3–4k of bookkeeping, however small its numbers.
- **Where to cut.** As in the folding work, the cut goes where the fewest values cross: the thin waist. In fib only a pair of numbers passes from one doubling to the next, so switching form there costs a few operations.
- **Assembly.** Each slice uses the cheapest form for the sizes it meets, plus the conversion at each cut. The kernel itself prices every assembled plan.

## The planner (`research/fib_planner/` on the PC)

A plan for an `L`-bit `n` has four parts:

1. a top table of `t` bits (one modular power);
2. `P` doublings, the first `c` of them in the `(F, L)` form (one product and one square, three operations) and the rest as Lucas pairs (two squares, five operations), with one conversion `L(j+1) = (5F(j) + L(j))/2` at the switch;
3. a low table of `P` bits joined by the addition formula;
4. `r = L − t − P` last bits: `C` (none), `A` (one bit from `(F, F')`), or `D` (selected Lucas-pair doublings, then the last bit).

How plans were checked and priced:

- `planner.py` checks every plan's formulas in Python: 2,805 (plan, n) pairs, 0 wrong.
- It writes each plan as an unrolled Lean chain in the v7 `share` style.
- `batch_bench.py` prices the chains with the judge's own timer kernel. One change makes the count exact: a copy of the timer whose PMU enable/disable calls toggle callgrind instead (`timer_control_callgrind.c`). Valgrind then counts exactly the judge's measured window.
- That count reproduces the Oct 3 numbers: v7 at the six endpoints is 6,952,406 here, against 6.954M in the V4 notes.
- The earlier "subtract the n = 0 run" method counted the parsing of the big answer literal, which inflated the large cases about 200×.

## What the passes showed

| Pass | What | Lesson |
|---|---|---|
| 1 | 335 plans, one point per bit length | best per size −3.1% |
| 2 | top 3 plans per size, at the group endpoints | same winners, but the 17-bit hybrid *loses* 21k at n = 80,000 |
| 3 | top plans at 5–8 random points per hidden range | the 15- and 16-bit "wins" were luck of the chosen point; they were dropped |

**A plan's cost depends on the bits of `n`.** The table indices, the selected bits and the parities all change with `n`, so pricing at a single point misleads. Pass 3 is the one to trust.

## fib v8

| Size (group) | v8 chain | Mean over the range, v7 → v8 |
|---|---|---|
| < 2^14 (F1, both cases) | 7-bit top table, 7 `(F, L)` doublings, 7 low bits | 13-bit 537.9k → 515.0k; 14-bit 593.2k → 552.3k |
| 15 bits (F2 case 0) | v7's chain; one test fewer | 749.3k → 735.7k |
| 16 bits (F2 case 1) | v7's chain | 951.5k → 950.5k |
| 17 bits (F3 case 0, and case 1 below 131,072) | **hybrid**: 8-bit table, 6 `(F, L)` + 1 Lucas-pair doubling, 7 low bits, 2 last bits | 1,654k → 1,624k; 2,368k → 2,285k |
| 18 bits (F3 case 1) | **hybrid**: 7-bit table, 7 `(F, L)` + 1 pair doubling, 8 low bits, 3 last bits | 2,588k → 2,557k |

**Expected official total** (inward jitter, F3 case 1 is 17-bit 16% of the time): **7,039k → 6,891k (−148k, −2.1%)**. At the six group endpoints the total is 6,952k → 6,840k (−1.6%).

Why each change wins:

- **Smaller top table.** Its single division costs about 8^bits: roughly 47k for 8 bits and 6k for 7 bits. On small inputs, saving that pays for the extra doubling.
- **The hybrid.** On the last level two squares beat a product and a square (a square is about 0.77 of a product). Below that level the `(F, L)` form's three operations beat the pair's five. This is the threshold switch Jonathan described.
- **One chain for every n < 2^14.** Each `Bool.rec` test costs about 14k. Sharing one chain saves a test on the 14- and 15-bit cases (−14k each) and costs one cheap doubling on the 13-bit case (+12k).

**Proofs.** Four new structured specs (`new_specs.lean`): `conv_spec`, `chainH_spec`, `chainH3_spec`, and `chainA_spec'`/`chainC_spec'` (any top table). Each unrolled chain is linked to its structured form by kernel `rfl`, as in v7.

**Checks.** The file is `submissions_v5/fib/Submission.lean` (65 KB).
- The strict build (`warningAsError`) passes.
- The axioms are only `propext`, `Classical.choice` and `Quot.sound`.
- The **official local judge accepts it** (`evaluation/run.py`, all public cases OK).

**Not submitted.** Submitting needs Jonathan's SAIR login.

## Where a case's instructions go (n = 150,000, v7, 2.63M)

| Part | Instructions | Share |
|---|---|---|
| final 52k × 52k-bit product | 846k | 32% |
| the 16 squares | 713k | 27% |
| linear big-number operations | about 450k | |
| kernel bookkeeping | about 250k | |
| fixed window floor | about 188k | |

- The fixed floor is the same for an identity `impl`.
- The final product is the floor of this scheme: F(n) has 104k bits.

## fib v9 (Oct 24)

Jonathan, Oct 24: *"based on the leaderboard we know we can save like 25%."* The board then showed #1 at
6,591,519, "main" at 7,353,781 and us at 8,691,915 (15th).

### Calibration: the board number is probably not v7

- **Official counts have tracked local counts before.** partition: 3.20M local vs 3.26M official.
  sha256's 512-step case: 6.40B vs 6.41B.
- **Official cases are never above the test points.** They are jittered *inward* from the range
  endpoints, so they never exceed the endpoints measured locally.
- **Two possible extra official costs were checked:**
  - Page faults in the measured window, with a software counter: 0–37 per case, well under 1%.
  - GMP's CPU-specific code paths. All variants were run on 24-limb operands. `mul_basecase` costs:
    zen 2,382, coreibwl 2,924, k8 3,455, ours (coreihwl) 4,151, core2 4,235, coreisbr 4,868. None
    is 25% worse than ours.
- **The upstream judge is unchanged since Sep 17** (same commit as the local copy).
- **Conclusion.** v7 should score about 6.9–7.0M officially. 8.69M fits v5 much better (9.03M at the
  endpoints, a little less after jitter).
- **Open:** confirm which entry the board shows, ideally with a playground run of v8 or v9.

### Where v8 spends (judge's kernel, callgrind, per function)

| | n = 5,375 | n = 140,000 |
|---|---|---|
| total | 533k | 2,435k |
| GMP products and squares | 14k | 978k |
| GMP linear (including Toom internals) | 25k | 498k |
| allocation and free | 169k | 300k |
| kernel bookkeeping | 247k | 383k |

- **Fixed floor:** 188k per case for an identity `impl`, the same in any environment.
- **Per operation:** about 3.4k on small numbers and about 7.5k on big ones. The extra for big
  numbers is mostly glibc malloc/free for GMP temporaries and copying the result.
- **GMP's own `mpz_fib_ui`** at the six endpoints totals 2.62M. Our GMP work matches its structure:
  one half-size product at the end and two squares per level.
- **Bool.rec tests:** about 14k each. Cases pay 2 or 3 of them (about 233k in total).

### What changed

- **`tab0`: exponent-m tables.** `X^m mod M` gives `(F(m+1) − F(m), F(m))`, which saves the `+1`.
- **`sgc`: the first doubling straight from the table.** `L(m) = lo + (lo + hi)`, then
  `F(2m) = F(m) L(m)` and `L(2m) = L(m)² + 4(m mod 2) − 2`. The parity is read with `Nat.land`.
  This is 6 big operations instead of 9.
- **The four-way end (`fin4L`): Jonathan's "closure equation per section".**
  - From the squares `a = L(j)²` and `b = L(j+1)²` at `j = n/4`, there is one closed formula for
    each `n mod 4`, chosen by two `Bool.rec` tests.
  - For `n = 4j+2` the ±2 terms cancel exactly: `F(2j+1) = (a + b)/5`.
  - For 18 bits, `sel2a` adds one branched selected doubling in front. Its branch fixes `ε` for the end.
- **Measured on 17 and 18 bits alone** (before re-planning): −4 to −10k and −30k. The linear
  big-number steps it removes cost only about 5.5k each, not the 10k estimated beforehand.
- **Re-planned with these blocks** (`planner3.py`; passes A and B, then the same 34 random points as v8):
  - 14 bits: t7 P7 C.
  - 15 bits: t8 P7 C.
  - 16 bits: t8 P7 A.
  - 17 bits: t8 P7 c6 with the end at `n/4`.
  - 18 bits: t8 P7 c6 with the end at `n/8`.
- **Result:** expected official total **6,891k → 6,683k (−3.0%)**. At the endpoints: 6,840k → 6,713k.
  - F1: −2.2%, −2.5%. F2: −2.7%, −1.9%. F3: −3.4%, −3.8%.
- **Checks:**
  - The strict build passes.
  - Only the three permitted axioms are used.
  - The official local judge accepts it (all six public cases).
- **File:** PC `submissions_v6/fib/Submission.lean` (68 KB; dead v8 code removed). Scripts and data are
  in `research/fib_planner/v9/`.

### Tried and not worth it

- **Merging chains to save a test.** chain16 on 15-bit inputs costs +26k; chain18 on 17-bit inputs
  costs +18k. Each saves one 14k test, so the net is −4k at best.
- **`shiftRight` instead of `Nat.div … 2`:** −0 to −7k per case.
- **The packed ring `s² mod M` for small doublings:** it needs either a fixed full-width X or 3–4
  operations to re-pack at each level. That is break-even at best.
- **The octonion / sections idea at the GMP level:** GMP already does this inside one multiply
  (Toom-Cook).

### Gap to #1

If official counts equal local ones, v9 at about 6.68M is about 1.4% behind #1 (6.59M) and ahead of
main (7.35M). The remaining costs are the fixed floor (1.13M), GMP (about 3M, already at the
`mpz_fib_ui` structure) and about 70 kernel operations plus 2–3 tests per case.

## Next

- **Calibrate.** Confirm which fib entry the board shows. One playground run of `submissions_v6/fib`
  gives official per-case numbers to compare with the local ones above.
- **Submit v9.** It needs Jonathan's SAIR login. Only the latest formal entry before Nov 20 counts.
- **Remaining leads, each about 0.1–0.2%:**
  - merge chain15 into chain16 with a reordered dispatch;
  - `shiftRight` halvings in the 16-bit chain;
  - a `Bool.rec` end for chain16.
- **The same planner fits polydisc's small-width cases (D1/D3).** It does not fit sha256.
