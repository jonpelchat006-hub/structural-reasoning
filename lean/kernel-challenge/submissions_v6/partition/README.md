# partition v6: the pentagonal division with 15-bit digits

Single file: `Submission.lean`. Same algorithm and proof as v5 (submissions_v4), with a smaller fast path.

- **Fast path (`n ≤ 38`):** `p(n)` is the last base-`2^15` digit of `⌊2^(15·(n + 35)) / P⌋`, where
  `P = B^35 · E(1/B)` is Euler's pentagonal polynomial truncated at degree 35 (10 terms, a 525-bit
  numeral). v5 used `B = 2^32` and degree 64 (a 2048-bit numeral) for `n ≤ 64`; the hidden cases are
  at most 36.
- 15 bits are enough: `p(38) = 26015 < 2^15`, and the digits past position `n` add up to less than one.
- `fast_ok : ∀ n < 39, fast n = slow n` is checked by the kernel (`decide +kernel`) against the
  Durfee-square algorithm, which is proved for every `n` (unchanged from v5).
- Larger `n` use the Durfee algorithm (dispatch `Nat.rec` on `n - 38`, as in v5).

Checks:
- strict build in the official `problems/partition` workspace (`warningAsError = true`);
- `#print axioms Submission.impl_correct`: `propext`, `Classical.choice`, `Quot.sound`;
- local judge `evaluation/run.py --problem partition`: accepted, all 6 public cases OK.
- SHA-256: `a8e125772809431db10f32d9db978aa5fefafe25288b70315e93007678df966e`.

Local counts (valgrind, judge replay window, public cases 14 / 18 / 22 / 26 / 32 / 36):

| | v6 | v5 |
|---|---|---|
| per case | 241.4k · 241.6k · 242.7k · 241.8k · 242.6k · 243.4k | about 262k |
| **total** | **1.454M** | 1.571M (official 1,580,120) |

For scale: a trivial `impl` that returns a constant costs 192.3k per case here (the replay's fixed cost),
so v6 spends about 50k per case on the computation and the dispatch. The current 1st is 1,430,108.
