# permanent — v8t candidate (Oct 27, 2026)

`Submission.lean` (single file, 394,958 bytes)
SHA-256 `cbef7989c2347dca3ebf9cd3024c75e4205ab000043167cd3bb2992ddcdf2ef2`

- Strict build in the official workspace (`warningAsError = true`), no warnings.
- Axioms: `propext`, `Classical.choice`, `Quot.sound` only. No `native_decide`, no `sorry`.
- Local judge (`evaluation/run.py`): accepted, all 15 public cases OK.

## Local valgrind counts (15 public cases)

| Group | v8e (submitted, 31.46M official) | v8j | **v8t** |
|---|---|---|---|
| R1 (d = 6) | 4.20M | 2.98M | **2.99M** |
| R2 (d = 12) | 7.73M | 7.71M | **7.67M** |
| R3 (d = 16) | 16.01M | 15.49M | **14.40M** |
| Total | 27.94M | 26.17M | **25.05M** |

**Estimated official count:** about 27.4M on the public cases, so about 28.2M on the hidden set. The
1st place is 29,436,124.
- The estimate uses the playground calibration: official − local ≈ 1.1 × the local GMP copy count
  for R2 and R3, and about 0 for R1.

## What changed since v8e

- **d = 6:** a generating-function product. The row factors `x^lo + x^mid + x^hi` (x = 2^10) come
  from one lane-parallel compare, and the product is read at `x^63`. 54 ops.
- **d = 16 rows:** from one lane-parallel compare (`R16.rowN`).
- **d = 16 DP, larger operand first in every add:** `(S <<< y) + ((S <<< z) + S)` and
  `S + (T + (T >>> z))`. This alone is −0.5M on R3.
- **d = 16 trims:** `land (2^r − 1) S` instead of `Nat.mod S 2^r`, which is generic GMP division.
- **d = 16 gathers by rotation instead of multiplication.** `eRev` is `(E <<< 240) mod (2^528 − 1)`
  and the order keys are `(k2L <<< 480) mod (2^544 − 1)`. The 2^m ≡ 1 trick replaces two
  128 × 124-limb multiplications.
- **d = 12:** W = 9 lanes, and the overflow check is one `lor` chain.
- `#flatten` drops shifts by 0, and the last d = 16 row reads the top cells with one shift.

Next step: a playground run to see the official per-case counts, then submit.
