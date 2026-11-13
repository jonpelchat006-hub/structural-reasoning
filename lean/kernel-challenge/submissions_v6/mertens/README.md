# mertens v9: a leaner fixed-prime branch

Single file: `Submission.lean`. Same algorithm and proofs as v8 (submissions_v4); only the fast branch changed.

## What changed

- **The fast branch now covers `N ≤ 528 < 23²`** (v8: `N ≤ 840 < 29²`). The hidden cases are at most 500.
  - So the primes up to 19 suffice, and 23 drops out of both lane rationals.
  - The `C` denominator shrinks from 17,116 to 11,297 bits, and the `W` denominator from 4,147 to 3,641.
- **The squarefree lanes take one fewer operation:** `(C >>> 4) &&& ONES` (ONES = one bit in each
  of the 528 lanes) replaces `(C >>> 4) &&& (C >>> 10)`. The digit expansion has exactly N lanes,
  so the mask is exact.
- `fast_ok : ∀ N < 529, fast N = slow N` is checked by `decide +kernel`.

## Checks

- strict build in the official `problems/mertens` workspace (`warningAsError = true`);
- axioms `propext`, `Classical.choice`, `Quot.sound`;
- local judge `evaluation/run.py --problem mertens`: accepted, 6/6 OK.
- SHA-256: `d996483c9740f57b44b31e4e1460ea227123ae8b12f7030614e80b441a971dad`

## Local counts (valgrind, judge replay window)

| n | 25 | 50 | 80 | 150 | 300 | 500 | total |
|---|---|---|---|---|---|---|---|
| v9 | 363.2k | 363.7k | 365.7k | 364.1k | 392.4k | 431.7k | **2.281M** |
| v8 | 369.4k | 370.7k | 371.9k | 371.7k | 401.8k | 440.7k | 2.326M (official 2,371,061) |

That is about −2%, so roughly 2.32M official.

For scale:
- a constant Int answer costs 223.7k per case here (the replay's fixed cost);
- main's 1,515,217 is only about 25k per case above that, which looks like a packed table rather
  than a computation.
