# submissions_v4 — candidates (Oct 3, 2026)

Versions: partition v5, primecount v6, mertens v8, fib v7, ca-rule110 v7, sha256 v8,
permanent v7, polydisc v7.

Every file here was checked the same way:

- accepted by the local judge (`evaluation/run.py`);
- strict build with `-DwarningAsError=true`, no warnings;
- `#print axioms Submission.impl_correct` shows only `propext`, `Classical.choice`, `Quot.sound`.

Counts are local valgrind instruction counts inside the judge's replay window, summed over the
default public cases (6 cases; group endpoints, seeds 1 and 2). They track the official counter
closely for small-number problems (partition: 3.20M local vs 3.26M official). For problems with
very large numbers (permanent) the official count has been about 2× the local one. About 215k per
case (1.29M per problem) is fixed overhead that every entry pays.

| Problem | Version | Local total | Previous | 10th place (official) |
|---|---|---|---|---|
| partition | v5 | 1,570,942 | v4 1.583M; v2 3.20M (official 3.26M, 11th) | 2,403,920 |
| primecount | v6 | 1,626,199 | v5 1.634M; v2 4.21M (9th) | 4,811,807 |
| mertens | v8 | 2,326,561 | v7 2.337M; v2 10.0M (11th) | 9,119,182 |
| fib | v7 | 6,954,474 | v6 7.11M; v5 9.03M; v2 11.15M (15th) | 10,128,913 |
| ca-rule110 | v7 | 3,722,688 | v6 3.88M; Astra v3 5.78M (12th) | 4,449,793 |
| sha256 | v8 | 10,241,952,741 | v6 10.55B; v2 13.72B (11th) | 10,810,632,799 |
| permanent | v7 | 18,171,137 | v6 18.24M; v2 58.0M (10th) | (we were 10th) |
| polydisc | v7 | 1,304,590,582 | v6 1.353B; v2 1.66B (8th) | 3,609,411,620 |

## What changed since the last README

### Branch selection (all problems with a fast path)

- **The kernel's dispatch order, read from `type_checker.cpp` (v4.33.1):** add, sub, mul, pow,
  gcd, mod, div, beq, ble, land, lor, xor, shiftLeft, shiftRight. Each position costs about 87
  instructions. Earlier notes had a different order and 110 per position; this list is the
  source of truth.
- **Closed branches.** A branch selector written as
  `Nat.rec (motive := fun _ => Nat → Nat) (fun n => fast n) (fun _ _ n => slow n) test n`
  applies the branches to `n` after the test. Unfolding `impl` then substitutes `n` only into the
  test, not into the branch bodies.
- **`Bool.rec` on `Nat.ble`/`Nat.beq`.** This is about 13k instructions cheaper per level than a
  `Nat.rec` on a numeral.
  - `Bool.rec` compiles only where Mathlib is imported (its `compile_inductive`), which covers
    fib, primecount and mertens.
  - Core-only problems (ca-rule110) need `@[implemented_by]` (see ca-rule110 v7 below).
  - `Bool.casesOn` is slow; it is not used.
- **partition v5, primecount v6, mertens v8.** Closed-branch `Nat.rec` selectors. The proofs are
  unchanged. Totals moved 1.583M → 1.571M, 1.634M → 1.626M and 2.337M → 2.327M.
- **permanent v7.** The d = 6 / 12 / 16 selector is three nested closed-branch `Nat.rec`s on
  `Nat.xor d k`; `rec3_eq` turns them into `if`s for the proof. Total 18.24M → 18.17M.
  - Peak memory is not worse. Both versions were judged back to back: mean peak RSS was 40.17 MB
    for v7 and 40.51 MB for v6, and the d = 16 maximum was 44.4 MB for v7 and 44.8 MB for v6.
  - Absolute local RSS varies between sessions (earlier runs read about 63–68 MB for the same
    files), so only same-session comparisons mean anything.

### fib v6 and v7 (v5 was 9.03M, v6 7.11M)

- **A table of Fibonacci pairs from one modular power.** Let `X = 2^K` and `M = X² − X − 1`.
  Evaluating `ℤ[x]/(x² − x − 1)` at `x = X` gives
  `X^(j+1) mod M = F(j+1)·X + F(j)`. So one `Nat.pow`, one `%`, one `/` and one `%` give
  `(F(j), F(j+1))`, as long as `F(j+1) + 2 ≤ X`.
- **16 to 18 bits (`chainA`, `chainB`).**
  - The top 8 bits of `n` come from one table with `K = 178`.
  - One doubling is followed by Lucas doublings `(F, L) ↦ (F·L, L² − 2)`. Each costs one product and
    one square (`Nat.pow l 2`, which GMP squares), with no bit selection.
  - The low bits come from a second, small table.
  - They are joined by the addition formula `F(N + d) = F(N)F(d−1) + F(N+1)F(d)`.
  - The last bit uses Cassini (one product).
- **13 to 15 bits (`chainC`).** All low bits come from the second table, and the result is
  `2F(N + e) = F(N)L(e) + L(N)F(e)`.
- **Selector.** Three `Bool.rec` tests on `Nat.ble` with closed branches.
- **Proofs.** Every unrolled chain is proved equal to the structured `chainA`/`chainB`/`chainC` by
  kernel `rfl`.
- **v7: Lucas pairs for 18-bit n (`chainD`).** The doublings carry `(L(j), L(j+1))` and cost two
  squares per bit: `L(2j) = L(j)² − 2`, `L(2j+2) = L(j+1)² + 2`, `L(2j+1) = L(2j+2) − L(2j)`.
  A GMP square costs about 0.77 of a product.
  - The selected doubling for bit 1 is also two squares, with the sign of `L(2n')` taken from the
    parity of `n'`.
  - The result is `F(h) = (2L(h+1) − L(h))/5`, then `F(h)L(h)` or `F(h)L(h+1) + (−1)^h`.
  - n = 150,000: 2.80M → 2.64M. Tried for 16–17 bits as well; it was slower there.
- **Per case (n = 5k … 150k):** 0.54M, 0.60M, 0.73M, 0.96M, 1.49M, 2.64M.


### ca-rule110 v7 (v6 was 3.88M)

- `impl` selects `go2`/`go4`/`go8`/`slow` with `Bool.rec` on `Nat.beq (n >>> 32) k`.
- Core Lean's code generator has no `Bool.rec`, so the definition carries
  `@[implemented_by implC]`, where `implC` is the same selection written with `if`.
  - The kernel never runs compiled code, and the attribute adds no axiom.
  - The theorem `implC_eq : implC n = impl n` proves that the compiled function agrees with
    `impl` on every input.
- **Fallback.** If the organizers object to `implemented_by`, the closed-branch `Nat.rec` variant
  (no attribute) measured about 3.81M.

### polydisc v7 (v6 was 1.353B)

- **Lane-parallel jump-ahead generator.** Every LCG state is `(a_j·s + c_j) mod 2^64`, with
  jump-ahead constants `a_j, c_j`.
  - Even and odd states sit in 128-bit lanes of two packs, with the seed as word 0. Two products of
    the seed with packed constants, two sums and two masks give the whole stream.
  - Each coefficient is then one shift, one mask and four operations for the encoding.
- **Proofs.**
  - `lanes`, `interleave` and `laneY_eq` show that the packs are the LCG stream.
  - `genZ_eq` shows that the read-off is `genGo`.
  - `genLane…C_rfl` checks one band per kernel `rfl`.
- **Per case:** D1 42.4M, D3 52.8M, D5 557.2M (v6: 43.4M, 54.9M, 578M).

## Notes

- The official inputs are random and jittered. About half the fib cases have odd n.
- permanent has no big literals in the d = 16 path.
- Do not push these files to the organizers' repository.
