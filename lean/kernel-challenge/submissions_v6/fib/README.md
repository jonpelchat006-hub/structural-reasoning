# fib v9 (Oct 24, 2026)

`Submission.lean` here is fib v9. md5 `2fd889231abc019323e18d716b2918c3`, 68 KB.

## Checks

- The strict build (`warningAsError`) passes.
- `#print axioms Submission.impl_correct` shows only `propext`, `Classical.choice` and `Quot.sound`.
- The official local judge accepts it (`evaluation/run.py --problem fib`): all six public cases OK.

## Counts (judge's replay window, callgrind)

| | v8 | v9 | change |
|---|---|---|---|
| Expected official total (the 34 random points in the hidden ranges) | 6,891k | 6,683k | −208k (−3.0%) |
| The six group endpoints | 6,840k | 6,713k | −127k |

Per group (mean over the random points):

| Group | v8 | v9 | change |
|---|---|---|---|
| F1 13-bit | 515.0k | 503.7k | −2.2% |
| F1 14-bit | 552.3k | 538.6k | −2.5% |
| F2 15-bit | 735.7k | 715.8k | −2.7% |
| F2 16-bit | 950.5k | 932.6k | −1.9% |
| F3 17-bit | 1,624k | 1,568k | −3.4% |
| F3 18-bit | 2,557k | 2,460k | −3.8% |

## What changed from v8

- **Exponent-m tables (`tab0`).** `X^m mod (X² − X − 1)` gives `F(m)` and `F(m−1)` directly. This saves the
  `+1` on every table index.
- **First doubling straight from the table (`sgc`).**
  - From the table: `L(m) = 2F(m−1) + F(m)`, `F(2m) = F(m)·L(m)`, and `L(2m) = L(m)² ± 2`.
  - The sign comes from the parity of `m`, read with one `Nat.land`.
  - This replaces v8's Fibonacci-pair doubling: 6 big operations instead of 9.
- **Branched four-way end for 17 and 18 bits (`fin4L`, `sel2a`).**
  - Start from the squares `a = L(j)²`, `b = L(j+1)²` with `j = n/4`.
  - There is one closed formula for each value of `n mod 4`, chosen by two `Bool.rec` tests:
    - `F(4j) = (2B − A)/5 · A`
    - `F(4j+1) = (2B − A)/5 · B + 1`
    - `F(4j+2) = (a + b)/5 · B`
    - `F(4j+3) = (a + b)/5 · C − 1`
  - Here `A`, `B`, `C` are `L(2j)`, `L(2j+1)`, `L(2j+2)`, built from `a` and `b` with small constants.
  - These are the same squares and the same one product as before, with about 10 fewer big linear steps.
  - For 18 bits, one branched selected doubling (bit 2) comes first. Its branch also fixes the parity
    constants for the end.
- **Plans re-priced** with the new blocks, at the same random points as v8:
  - 14 bits: 7 + 7 C.
  - 15 bits: 8 + 7 C.
  - 16 bits: 8 + 7 A.
  - 17 bits: 8 + 7, ending in the four-way end.
  - 18 bits: 8 + 7, then the selected doubling and the four-way end.

## Proofs

- New structured chains: `chainC0`, `chainA0`, `chainE2`, `chainE3`.
- Specs for every new block: `tab0_spec`, `sgc_spec`, `combL0_spec`, `comb0_spec`, `luc_add0`,
  `fin4L_spec`, `fin4Lc0_spec`, `fin4Lc1_spec`, `sel2a_spec`, `land_two_pow`.
- Each unrolled chain is linked to its structured form by kernel `rfl`, as in v8.
- v8 definitions that nothing uses any more were removed.

## Not submitted

Submitting needs Jonathan's SAIR login. Do not push this to the organizers' repository.
