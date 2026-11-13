# Lean Kernel Challenge — permanent v8t (Oct 27, 2026)

Follows `claude/LEAN_PERMANENT_V8.md` (v8e, official 31,460,683, 2nd place).

## Round 2 (Oct 26–27): v8f … v8t — candidate v8t

**Calibration from the playground** (one public case per group, official vs local):

| Case | Official | Local (v8e) |
|---|---|---|
| R1 n=28064292647 | 841,114 | 840,663 |
| R2 n=53794586207 | 1,736,979 | 1,552,882 |
| R3 n=71077100717 | 3,324,588 | 3,044,466 |

Official − local ≈ 1.1 × the local `__gmpn_copyi_core2` count for R2 and R3, and about 0 for R1. So the
official counter charges extra for copying big numbers. Every big Nat op copies its first operand
(`lean::mpz::mpz(const&)` → `__gmpz_init_set`), and `Nat.add` then reallocs to one more limb (another copy).

**What changed, and what it saved (local valgrind counts, 15 public cases):**

- **v8f:** d = 6 by a generating-function product (`R6`, x = 2^10, 54 ops). R1 ≈ 0.6M per case.
- **v8g–v8j:** d = 16 rows from the R16 compare (`R16.rowN`), `trimM` with `land` instead of
  `Nat.mod 2^r` (generic GMP division), `stepZ` sharing `S >>> x`, d = 12 with W = 9.
  v8j total 26.17M.
- **v8l: larger operand first in both DP phases.**
  - `stepL S z y = (S <<< y) + ((S <<< z) + S)`.
  - `stepZ S x z = S + (T + (T >>> z))` with `T = S >>> x`.
  - R3 −510k (15.49M → 14.97M).
- **Small literal first in `land`** (`land 65535 (shr AM c)`, mask first): the big operand is not copied.
- **Dropped or neutral:**
  - **d = 12 amounts precompute (R12, all 24 shift amounts `9·2^col` from one compare pipeline).**
    Fewer ops, but the vectors are 12,480 bits, so shifts copy more, multiplications and glibc
    mallocs cost more. +25k per case before the mask-first fix, −8k after. Dropped for the v7-style
    graph.
  - **`lor` chains for the overflow checks.** They save ops, but each `lor` result is as big as the
    level, while a `land` with the guard mask is nearly zero. Neutral on R3, so the R3 check keeps
    the `land` chain.
  - **More trims** (levels 9, 11, 13). Each trim builds a mask of r bits (three copies of r bits),
    which costs more than it saves (model over 65 seeds, every variant worse).
  - **CRT-style one-op extraction of the shift amounts** needs a wide dot product, too expensive.
- **Smaller wins:**
  - `#flatten` drops `x >>> 0` and `x <<< 0` (kernel defeq).
  - The last row reads the top 32-bit cells by one shift (`gat32_top`).
  - **`eRev` by `Nat.mod ((E <<< 240)) (2^528 − 1)`.** Since `2^528 ≡ 1`, lane `c` lands at bit
    `240 − 16c`. This replaces a 128 × 124-limb multiplication.
  - **`ordRK`'s key row by `Nat.mod (k2L <<< 480) (2^544 − 1)`.** The cells come out reversed, but the
    rank is a count over all cells. The proof never looks inside `ordRK` (output masked to 5 bits).

**Lessons:**
- Per-op cost is about 5.5–6.5k all-in (kernel `whnf`/`reduce_nat`, `instantiate`, Expr allocation,
  literal hashing).
- Ops on big vectors cost more: the copies, `mk_lit` hashing (`mpz::mod64`), and glibc malloc for big
  limb arrays.
- A gather by multiplication with a sparse constant costs the full |a|·|b| limbs. A gather that is a
  rotation (lane spacing ≡ cell spacing mod m) is one `Nat.mod (2^m − 1)`.

**v8t (candidate, Oct 27):** local 25.05M on the 15 public cases.

| Group | v8e | v8j | v8t |
|---|---|---|---|
| R1 | 4.20M | 2.98M | 2.99M |
| R2 | 7.73M | 7.71M | 7.67M |
| R3 | 16.01M | 15.49M | 14.40M |

- R3 per case: 2.78 / 3.37 / 2.72 / 3.00 / 2.52M.
- Local GMP copy counts: R2 0.72M, R3 1.42M (v8j: 0.69M, 1.58M).
- **Estimated official:** about 27.4M on the public cases, about 28.2M on the hidden set
  (1st: 29,436,124).
- Strict build, 3 axioms, local judge accepted. SHA-256 `cbef7989…df2ef2`.
- On the PC: `submissions_v6/permanent_v8t/` (Submission.lean + README).
- **Next:** a playground run to confirm the official per-case counts, then submit (Jonathan's
  login).

**Per-op anatomy (R3, smallest case, 2.52M):**
- Kernel `whnf`/`reduce_nat`/`is_def_eq`: about 1.23M.
- `instantiate` of the graph body: 0.26M.
- `mk_lit` for each big result: 0.21M, about 760 per big literal (`mpz::mod64` hashing).
- mimalloc 0.32M and glibc malloc 0.30M.
- GMP: 0.63M (the multiplications that remain are the row spread, about 0.12M).
