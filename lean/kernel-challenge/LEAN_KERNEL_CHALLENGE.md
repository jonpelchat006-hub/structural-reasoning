# Lean Kernel Challenge (SAIR / Lean FRO), Stage 1

*Started Sep 29 2026. Team: Jonathan (Shovelcat). Deadline: **Nov 20 2026, 23:59 AoE**. Stage 2 starts Dec 2026.*

## What the challenge is

There are 8 fixed problems. For each one we submit a single `Submission.lean` containing:

- `impl : Nat → Output`, the algorithm;
- `impl_correct : ∀ n, impl n = spec n`, a full Lean proof that it matches the trusted spec.

The Lean kernel then replays `impl n = value` on hidden cases. Each problem has its own leaderboard, ranked by the **sum of median kernel instruction counts, lowest first**.

**Rules:**

- no `sorry`, `native_decide`, `partial` or `unsafe`;
- only the axioms `propext`, `Quot.sound` and `Classical.choice`;
- no lookup tables or hardcoded answers;
- human-readable code only, at most 1 MiB;
- the latest formal entry before the deadline counts, even if an earlier one scored better.

**Links:**

- repo: https://github.com/SAIRcompetition/lean-kernel-challenge
- playground: https://playground.sair.foundation/playground/lean-kernel-challenge (2 runs/day)
- registration: https://competition.sair.foundation/ (individual or team, SAIR account needed)

## Why it fits the framework

The kernel plays the role of the **inner core**. Nothing counts until a small trusted checker has verified
it for every input, which is "commit only closed cycles" enforced by a machine. Passing examples is
explicitly not enough (rule R3). This is the same distinction the ARC work keeps meeting: a rule that fits
the train pairs versus a rule that is actually right.

## Triage (local kernel wall time, organizers' worked examples, unseeded public plan)

| Problem | Lean deps | Largest case, example | Opportunity | Proof effort |
|---|---|---|---|---|
| **partition** | core | 20.7 s (n=36) | huge: spec is exponential | medium, **done** |
| permanent | core | 42 s (dim 16) | large: subset DP over column masks | medium-high |
| sha256 | core | 50 s (512 steps) | large: representation/rounds | high (bit-level equivalence) |
| ca-rule110 | core | 0.08 s (example is already bit-packed) | small: micro-optimizations | medium |
| polydisc | core | 0.7 s | unclear: resultant algebra | very high |
| fib | Mathlib | fast doubling given | small | low |
| mertens / primecount | Mathlib | not measured yet (Mathlib setup running) | sieve-style algorithms | medium-high |

Other teams are active, and at least one is using Claude heavily. Their public playground totals are
roughly 13M (fib), 25M (primecount), 47M (partition v2), 84M (mertens), 113M (rule 110), 660M (permanent)
and 14.5B (sha256), each over 3 public cases.

## Entry 1: partition, by Kronecker substitution. ACCEPTED locally

`submissions/partition/Submission.lean` (335 lines, core Lean, no Mathlib):

- **Idea:** p(N) is the coefficient of x^N in ∏_{s≤N} 1/(1−x^s). Truncate each factor to a finite geometric
  series and evaluate every polynomial at x = B = 2^(2N+1).
- A whole coefficient table is then one natural number. Multiplying polynomials is one kernel `Nat.mul`
  (GMP), and truncating is one `%`.
- **Loop:** `Nat.rec` over s = 1..N computes `acc * (B^(s·J) − 1)/(B^s − 1) % B^(N+1)`. The answer is the
  base-B digit at position N.
- **Proof:**
  - encodings `enc c B L = Σ c m·B^m`;
  - multiplying by a geometric series modulo B^L equals the spec's inner sum (`mulGeo`, `conv_eq_specSum`);
  - the bound `partAux k m ≤ 2^(m+k)` gives no carries;
  - the closed-form geometric series and the loop agree with the proof-side versions (`geoF_eq`, `loop_eq`).
- **Result:** the judge's local check (interface + universal proof + axioms) is **accepted**. Total kernel
  wall time over the 6 public cases went from **34 s to 0.0074 s (about 4,600×)**.
- Instructions, estimated with valgrind because the sandbox has no PMU (not the official counter):
  about 4.3M at n=14 and 11.5M at n=36, **about 46M for 6 cases**.
- **Profiling note:** the per-iteration kernel overhead (about 300k instructions per step) now dominates.
  The arithmetic does not. Width and shift-versus-power variants changed nothing. The next win has to cut
  the number of kernel steps: fewer than N big operations, or a cheaper loop form.

## Tooling

- The official evaluator is set up in the cloud workspace (`evaluation/setup.sh`, `run.py`).
- `scripts/bench_instr.py PROBLEM SUBMISSION [n...]` is ours. It builds the judge's exact
  `impl n = v := Eq.refl v` theorem, exports it and replays it with the judge's timer kernel. It reports
  wall time and a valgrind instruction estimate with the n=0 overhead subtracted.

## ARC kernel tier: the verified-rule test (`arc-slice/src/kerneltier.ts`)

This is the challenge's gates translated to ARC rules. The program is chosen **without looking at the test
output**: it is the first stage whose program fits train. The gates are:

- **K1 total:** returns a grid on every input.
- **K2 universal:** leave-one-out re-induction must reproduce each held-out train pair. This is the stand-in
  for "∀ n".
- **K3 no lookup table:** the leave-one-out programs give the same test answer as the full program.
- **Cost:** median replay ms, which is the leaderboard metric.

| set | train-fit programs | test precision, train-fit alone | kernel-accepted | **test precision, accepted** | wrong answers blocked | correct solves lost |
|---|---|---|---|---|---|---|
| ARC-1 training | 107 | 93/107 = 86.9% | 75 | **72/75 = 96.0%** | 11 of 14 | 21 |
| ARC-1 evaluation (held out) | 34 | 27/34 = 79.4% | 21 | **20/21 = 95.2%** | 6 of 7 | 7 |

**Reading:**

- The kernel gate works as a trust filter on held-out data too. Precision rises from about 80% to about 95%,
  and it catches 17 of 21 wrong answers across both sets.
- The cost: about a quarter of the correct solves fail leave-one-out. Many ARC tasks have only 2–3 train
  pairs, so dropping one leaves too little to re-induce the rule. A rejection there means "the proof didn't
  go through", not "the rule is wrong".
- This matches the §32 balance-acceptance finding (higher precision, lower coverage). The kernel gate keeps
  far more coverage: 21 accepted on eval, against 1 under balance.
- **Use:** as the commit gate for the rule-learning loop (write only kernel-accepted rules into the trusted
  library), and as a confidence signal when attempts are limited.

## Playground log
- partition (Kronecker): **accepted** on the playground (Sep 29).
- fib and primecount: rejected with "comparator: Child exited with 1". Cause: the partition file had been
  uploaded to those problems. It calls `partitionSpec`, which does not exist there, so the judge's
  `lake build` failed. Each problem needs its own file.

## Entry 2: primecount, packed sieve with proof. ACCEPTED locally
`submissions/primecount/Submission.lean` (Mathlib, imports only `Spec`):
- Slots are w = log₂N + 2 bits wide.
- For each d ≤ √N, one closed-form geometric series marks d², d²+d, … ≤ N. The marks are combined with `|||`.
- The slot sum is read as the value mod (2^w − 1). π(N) = N − 1 − #composites.
- Proof: `enc_or` (bitwise OR acts slot by slot, via `Nat.shiftLeft_add_eq_or_of_lt`); `prog_eq`
  (`sum_nbij'` onto the arithmetic progression); `enc_mod` (2^w ≡ 1); `marked_iff` (via `Nat.minFac`,
  `minFac_sq_le_self`); then card arithmetic on `range (N+1)`.
- Local judge: accepted. Kernel wall time over the 6 public cases: 0.0125 s. Valgrind estimate: about 69M,
  against 6.34B for the example.

## Entry 4: permanent, packed backward subset DP. ACCEPTED locally (15/15)
`submissions/permanent/Submission.lean` (core Lean; warnings are errors in the participant build):
- g_i(mask) = the spec's `permanentRows d (rows i..) mask`.
- All 2^d values are packed into one Nat with W = 2d+1 bits per slot (every value ≤ 3^d < 2^W).
- One row costs ≤ 3 × (shift right by 2^j slots, `&&&` with the "bit j clear" slot pattern), then an add.
- The patterns are built by doubling (`patD`); the all-ones start is a closed-form repunit.
- Proof:
  - `enc_shiftRight` / `enc_and` / `enc_pad` / `enc_listSum` act slot by slot;
  - `add_eq_or` gives 2^j + m = m ||| 1<<<j when bit j is clear;
  - `range_sum_supp` reduces the spec's fold over all columns to the 3 distinct seeded columns;
  - `gs_bound` gives g ≤ 3^k.
- Local judge: accepted, 15/15. Total kernel wall time 0.54 s. The worst case (d=16) went from about 42 s
  to 0.08 s.
- Valgrind estimate: about 41M / 111M / 232M per case at d = 6 / 12 / 16, so about 1.9B for the 15 cases.
- Another team's public playground figure is 660M for 3 public cases (one per group), which scales to about
  3.3B for 15.
- Next wins:
  - fewer pattern-building steps (d² doublings; cache them across dimensions or use a closed form);
  - narrower slots.

## Entry 5: sha256, kernel-cheap word ops. ACCEPTED locally (6/6)
`submissions/sha256/Submission.lean` (core Lean, about 560 lines):
- Word operations call `Nat.add`/`Nat.land`/`Nat.xor`/`Nat.shiftRight` directly. This alone was about 3× in
  the rounds, because the kernel then skips unfolding `HAdd`/`AndOp` instances every time.
- Rotation = one right shift of the word duplicated into 64 bits (`x * 0x100000001`). The garbage above
  bit 31 is harmless because each value only feeds a sum reduced mod 2^32 once.
- Ch = g ⊕ (e ∧ (f ⊕ g)) and Maj = ((a ∨ b) ∧ c) ∨ (a ∧ b).
- The rounds are a `Nat.rec` loop with the 8 working variables and a rolling 16-word schedule window as
  plain arguments. Using no structures and no `brecOn` gave another ~1.4×.
- Proof:
  - bitwise `testBit` lemmas (`S1_mod`…`maj_eq`);
  - `round_eq` (fast round = spec round on 32-bit words);
  - `loopA_eq`/`loopB_eq` against the spec's `rounds`;
  - the schedule, through the organizers' window lemmas (`extend_eq`, adapted from their example);
  - `stepN_eq`, then `iterN_eq`.
- Local judge: accepted. Kernel time over the 6 public cases is 7.5 s, against about 100 s for the example.
  The 512-step cases dropped from about 50 s to 3.6 s.
- Valgrind estimate: about 24M instructions per hash step. The example is about 150M. Another team's
  public figure is about 26.5M.
- Lessons (they apply to the other entries too):
  1. The judge compiles `Solution.lean`, so `impl` must be **computable**. `noncomputable` and `List.rec`
     are rejected ("Child exited with 1"); `Nat.rec` is fine.
  2. Elaborator `rfl`/`rw` on definitions that unfold into 64 symbolic rounds can run out of memory.
     Use raw-argument `rfl` lemmas, `unfold f; rfl`, and `@[irreducible]` on the step.
  3. Using `Nat.add` and friends directly makes each kernel step ~3× cheaper, so partition, primecount
     and permanent may also gain.

## Entry 6: mertens, packed Möbius sieve. ACCEPTED locally (Sep 30)
`submissions/mertens/Submission.lean` (Mathlib, about 800 lines):
- Composite sieve → prime indicator Σ B^p.
- Primes are removed lowest first with `x &&& (x-1)`. For each prime, one division `(B^N·b − 1)/(b − 1)`
  (b = B^p) marks all its multiples in a **reversed** layout (number m at slot N−m). This needs no log2, which
  matters because `Nat.log2` is NOT kernel-accelerated: an early version spent 7 s computing log2 of big
  numbers.
- Squares are marked with the same division at b = B^(d²). Parity bits and two digit sums then give M(N).
- Local judge: 0.016 s over the 6 public cases, against 1.44 s for the example. Valgrind estimate about 93M
  in total (a looser prototype measured 53M, so there is room).

## Entry 7: ca-rule110, SWAR initial row. ACCEPTED locally (Sep 30)
`submissions/ca-rule110/Submission.lean` (core Lean, about 440 lines):
- The cost was almost all in the seeded initial row (254 `caMix32` calls).
- The 256 mixer inputs now sit in 64-bit lanes of one 16384-bit number. The mixer runs lane-parallel in
  about 12 operations, then bit 31 of each lane is gathered.
- Proof: `enc_tb` makes every lane operation a per-lane fact; `mix_generic` handles the masked-multiply
  equivalence.
- The automaton steps and their lemmas come from the organizers' example, acknowledged.
- Local judge: 0.014 s total, against 0.38 s.

## Optimisation pass v2 (Sep 30 – Oct 1): all eight problems rewritten

All v2 files are in `submissions_v2/<problem>/Submission.lean`.

Every one was checked the same way:

- accepted by `evaluation/run.py`;
- clean strict `lake build` with `warningAsError`;
- only the axioms propext, Classical.choice and Quot.sound.

Counts are local valgrind instructions inside the judge's replay window, summed over the default public cases.
The judge uses hardware counters, so absolute numbers differ, but ratios carry over.
The score is the sum over all cases, 15 for permanent and 6 for the others.

| Problem | v1 local | v2 local | Playground 1st / 10th | Idea |
|---|---|---|---|---|
| partition | 49.4M | 3.20M | 1.44M / 3.62M | Durfee-square series with Kronecker packing; one big number per level |
| primecount | 70.9M | 4.21M | 1.44M / 7.99M | packed sieve, 6k±1 wheel, Newton square root |
| mertens | 94.9M | 10.0M | 1.56M / 13.4M | packed Möbius lanes (product, parity, square marks), 6k±1 wheel |
| ca-rule110 | 103.5M | 6.00M | 3.43M / 7.26M | 320 lanes × 64 bits, SWAR rule step, closed-form initial row |
| fib | 60.6M (example) | ~13.65M | 7.00M / 10.14M | MSB-first fast doubling at the exact bit length (likely 11th–12th) |
| permanent | 775.7M (6 cases) | 58.0M (6 cases) | 51.4M / 425M (15 cases) | backward subset DP with **no masks**; stray values never reach lane 0 |
| sha256 | 25.46B | 13.72B | 9.37B / 19.42B | one SHA step as a single shared expression graph (`share` elaborator) |
| polydisc | 9.97B (example) | 1.66B | 1.23B / 4.83B | `Nat`-encoded integers, fused normal PRS step, shared graph |

### Kernel cost model (measured)

- **Fixed costs.** About 200k instructions per case. A kernel-accelerated `Nat` op costs about 4k on small
  numbers and about 6k past 2^63, where numbers become GMP objects.
- **Loops and calls.** A `Nat.rec` iteration costs about 20k. A def call is about 4k plus the cost of
  instantiating its body.
- **`let` is expensive.** Each `let` re-instantiates the whole remaining body. Use shared expression nodes
  instead (the `share` elaborator in sha256 and polydisc).
- **`Int` is very expensive.** Each `Int` op costs about 130–160k, because it unfolds through `match`.
  Encode as `Nat` (`2·|x| + sign`).
- **Things to avoid.** `Nat.log2` is not accelerated: it is well-founded recursion, linear in the bits.
  `Nat.sqrt` is similar. Instance ops cost about 5× a direct op. Always write literals as `nat_lit`.
- **Caching.** The kernel caches `whnf` results for closed terms across the whole check. A closed constant
  expression is evaluated only once.

### Proof-engineering lessons

- **Big literals.** Never write `Nat.add x BIG` with a symbolic `x`. When the kernel compares two copies, it
  unfolds `Nat.add` and peels the literal one successor at a time, until it runs out of memory. Put the
  literal first: `Nat.add BIG x`.
- **Large graphs.** Prove `graph = structured version` by `rfl`, checked by the kernel via `addDecl`.
  The elaborator's unifier can take more than 10 minutes on the same goal.
- **Computability.** The comparator's `Solution.lean` re-declares `impl`, so `impl` must be computable.
  `Nat.rec` compiles. `List.rec` does not.
- **Fallbacks.** When a fast path can fail (an abnormal PRS step), count every check. If any fails, return the
  spec itself. Then only the normal path needs a proof.

## Submission notes (for the playground form)

- **partition:** "Durfee-square generating series with base-2^(N+4) Kronecker packing. Fully proved in
  core Lean, no table."
- **primecount:** "Packed sieve in one big Nat: repunit marks, 6k±1 wheel, slot sum via mod (B−1)."
- **mertens:** "Packed Möbius sieve: one lane per m, prime-product, parity and square-mark lanes, final
  lane sum via mod (B−1)."
- **ca-rule110:** "320×64-bit SWAR layout, closed-form packed initial row, bitwise rule step."
- **fib:** "MSB-first fast doubling, F(2k) and F(2k+1) via a(2b−a), b(2a+b); Nat.rec bit selection."
- **permanent:** "Backward subset DP in 2^d lanes with no column masks: stray values provably never reach
  lane 0; seeded columns computed with raw ops."
- **sha256:** "Each SHA-256 step is one shared expression graph of raw Nat ops (dup-rotations, 3-op Ch,
  reused a⊕b for Maj); proved by rfl against a structured round loop."
- **polydisc:** "Normal subresultant PRS on Nat-encoded integers (2|x|+sign), two pseudo-division stages
  fused per coefficient, 23 steps as one shared graph; spec fallback whenever a normal-path check fails."

## Status (Oct 1)

- All eight problems have v2 entries ready on the PC.
- Expected position (by local count against the playground's 10th place):
  - inside the top 10: partition, primecount, mertens, ca-rule110, permanent, sha256, polydisc;
  - fib is just outside the top 10.
- Ideas for later:
  - **fib:** unroll 2 bits per `Nat.rec` (about −0.8M).
  - **polydisc:** bulk LCG generation; a cheaper divisibility check.
  - **sha256:** 2-lane SIMD message schedule.
  - **permanent:** packed seeded-column mixer (about −20%).

## Entry 3: fib, the organizers' fast-doubling example (placeholder, acknowledged as theirs)
- Accepted locally. Sharing products with `let` changed nothing: the kernel already caches repeated terms.
- Valgrind overstates GMP-heavy work (the counts grow while wall time stays around 2 ms), so its numbers
  are not reliable for fib.

## Earlier framework work, reviewed (Sep 29)

These files were searched for material that carries over:
- `Physics/fractional_fibonacci.py`, `fibonacci_derivative_integral.py` (Fibonacci exponents on the (π−3) dust);
- `riemann_structural_events.py`, `six_number_alignment.py` (primes and zeros as alignments);
- the colony's `crypto-euler-phi.ts` (it uses SHA-256 as a hash; it does not implement it).

They are conceptual explorations. None contains an algorithm or a proof that transfers directly to the kernel
problems. What does transfer is the lesson from partition: **a kernel step costs about 300k instructions,
while GMP arithmetic on big numbers is nearly free.** So pack the structure into one big number and use as
few steps as possible. This is the framework's "compact it into a ball" move, and it can be measured here.

**Prime counting prototype (implementation only, proof not written yet, `submissions/primecount/proto.lean`):**
a packed sieve.
- Every n ≤ N gets a slot of w = log2 N + 2 bits in one big number.
- For each d from 2 to √N, one closed-form repunit adds 1 to the slots of d², d²+d, and so on.
- Adding 2^(w−1)−1 to every slot and masking the top bits turns each slot into a "composite?" bit.
- Taking the result mod (B−1) sums all the slots at once, because B ≡ 1 mod B−1.
- π(N) = N − 1 − #composites. The loop has about √N steps, 31 at N=1000.
- Estimated instructions (valgrind): **about 91M over 6 cases**, against 6.34B for the organizers' example
  (**about 70×**). Another team's public entry is about 25M per 3 cases, roughly 50M per 6, so this needs
  another ~2× before it leads.
- The proof against Mathlib's `Nat.primeCounting` reuses partition's encoding lemmas plus
  `Nat.prime_def_le_sqrt`-style facts. Estimated effort: one focused session.

## Next

1. Submit the v2 entries (2 playground runs per problem per day). Record playground ranks here.
2. fib: unroll the doubling loop to try to get into the top 10.
3. Cheaper refinements listed under Status, in order of expected gain.
