# Lean Kernel Challenge — optimisation pass v4 (Oct 3, 2026; latest: fib v7, polydisc v7, ca-rule110 v7, permanent v7)

All v4 files are in `submissions_v4/<problem>/Submission.lean` on the PC, with a README.

Every file was checked the same way:

- accepted by `run.py`;
- strict build with `warningAsError`;
- only the three permitted axioms.

| Problem | v4 file | Local total | Before | 10th (official) |
|---|---|---|---|---|
| partition | v5 | 1.571M | 3.20M (11th) | 2.40M |
| primecount | v6 | 1.626M | 4.21M (9th) | 4.81M |
| mertens | v8 | 2.327M | 10.0M (11th) | 9.12M |
| fib | v7 | 6.954M | 11.15M (15th) | 10.13M |
| ca-rule110 | v7 | 3.723M | 5.78M (12th) | 4.45M |
| sha256 | v8 | 10.24B | 13.72B (11th) | 10.81B |
| permanent | v7 | 18.17M (6 cases) | 58.0M (10th) | — |
| polydisc | v7 | 1.305B | 1.66B (8th, but v2 used `partial`) | 3.61B |

### What the kernel actually charges (profiled with callgrind)

- **Per operation, about 3.5–4k instructions on small numbers.** The cost has several parts:
  - two `whnf` cache probes and an insert;
  - `whnf_core` plus `reduce_recursor`, which does an environment lookup of the head constant (about 450);
  - the `reduce_nat` dispatch;
  - two `is_equal(arg, Nat.zero)` checks (about 250);
  - `mk_lit`.
- **The dispatch is a linear scan, about 87 instructions per position.** The order, read from
  `type_checker.cpp` (v4.33.1), is add, sub, mul, pow, gcd, mod, div, beq, ble, land, lor, xor,
  shiftLeft, shiftRight. (An earlier version of this note had a different order and 110 per
  position.)
  - On small numbers, `Nat.div x 2^k` beats `x >>> k`, and `Nat.mod x 2^32` beats `x &&& 0xffffffff`.
  - `x + x` beats `x <<< 1`.
  - `Nat.pow` sits at position 4, so squares by `Nat.pow x 2` are cheap to dispatch, and GMP squares.
  - `Nat.sub` replaces xor when the subtrahend's bits are contained in the minuend's.
- **Numbers of 2^63 and above become GMP objects and cost about 2–2.7k more per operation.** The
  extra goes to allocation, a copy into the Lean object, and the literal hash (`mod64`).
  - On big numbers `Nat.div` is *slower* than `shiftRight`, because the divisor is boxed and
    GMP has no power-of-two shortcut.
  - In sha256, each Σ/σ now touches the possibly-big duplicated word only once.
- **Instantiation is about 400 instructions per rebuilt node, roughly 20% of sha256.** A binary op
  is 2 app nodes, but partial applications whose first argument is closed are not rebuilt.
  So put literals first in commutative ops, and share partial applications (e.g. `T1 + d` and
  `T1 + T2` share `App(add, T1)`).
- **Branching.**
  - A `pick` definition costs about 15k (zero) or 29k (succ).
  - An inline `Nat.rec` is cheaper, but only if its minor premises reference small terms. Shared
    graph nodes under a lambda are instantiated again.
  - Splitting branches into separate definitions means only the chosen branch is instantiated
    (ca-rule110: −3.6%).
- **The official counter is user+kernel (`exclude_hv` only).** Big GMP-heavy problems (permanent)
  read about 2× higher officially than locally. Small-number problems read about the same.

### What did not work

- **SIMD message schedule for sha256 (64-bit lanes in one big number).** It cut 291 of 2380 ops
  but gained only 1.5%. Every lane op is a big-number op, and the words still have to be extracted.
  Not worth the lane proofs.
- **Lucas-number doubling for fib.** `Nat.mul x x` never squares (the `mpz` wrapper copies the first
  operand), but `Nat.pow x 2` does: a 52,000-bit square costs 0.77× a product. Even so, Lucas
  doubling with `Nat.pow` squares in the last 3 levels gained only 1.5% at n = 150,000 and nothing
  at 80,000, because the extra linear-size operations eat the saving.
- **Lane-offset drift for permanent d = 16** (drop the smallest of the three shifts per row). It
  was 6% *slower*: the drifted state never shrinks, every add involves the full-size number, and
  sorting the three shift amounts costs 8 scalar ops per row.

### permanent v5d (Oct 2, evening)

- **Columns lane-parallel.** All 2·d mixer inputs sit in 72-bit lanes of one number. The 32-bit
  mixer, `z mod (d−1)` and `z mod (d−2)` (multiply-high quotient, exact for z < 2^32), and both skip
  maps (guard-bit comparisons; `b = k2 + [k2 ≥ k1] + [k2 + 1 ≥ i + [k1 ≥ i]]`) take about 40 lane
  operations in total, versus about 38 scalar ops per row before.
- **Narrow lanes, checked.** The provable lane bound `3^(k−1)` forces W = 24 at d = 16. Real lanes
  stay below 2^11 (200k-seed simulation). v5d uses W = 12 (d = 16) and W = 10 (d = 12). Each row
  `k` with `3^k ≥ 2^W` is checked with one `&&&` against a mask of the top two bits of every lane;
  if any check fails, a `pickZ` falls back to the old proved `main`. The check fails for about 1 seed
  in 30,000 at d = 16 and for none of 100,000 at d = 12.
- **Last row reads three lanes** (only lane 0 of the result matters).
- **The d = 16 mask is an elaboration-time literal** (`eval%`, 237k digits). That saves four
  full-size big ops (about 1M instructions per case). The judge parses the literal before the
  measured window, at about 3.7 s per run.
- **Proof structure.** Generic lane library (`enc`, testBit lemmas for xor/and/shift-and-mask/sub)
  proves the vectors are the spec columns. `loopV_eq` carries `G_k = enc W (hl k)` plus lane bounds,
  using the provable bound or the check. Each unrolled graph is proved equal to its structured form
  by kernel `rfl`.
- **Kernel-check pitfall.** A top-level inline `Nat.rec` whose major premise is symbolic makes the
  kernel's `rfl` try to reduce it, and with a big literal inside `Nat.land` that ran out of memory.
  Wrapping the branch in a definition (`pickZ`) makes the kernel compare arguments instead.

### permanent v6 (Oct 3)

- **d = 16 only changes.** d = 6 and d = 12 keep v5's code (d = 12 keeps its two 12k-digit literals).
- **Relabeled columns.** A heuristic label table (columns of rows 0–4 first, then rows 5–8, then
  the rest; 32-bit lanes, computed lane-parallel) is not trusted. The proof needs only injectivity,
  checked at run time: the lane-wise exponentiation gives shift amounts `12·2^λ(c)`, and their sum
  (one `Nat.mod (2^32 − 1)`) must equal `12·(2^16 − 1)`. A popcount argument turns that into
  injectivity (`relab_inj_of_pc`).
- **Trimming.** After row k only lanes using labels of rows still to come can reach lane 0
  (`hlT_eq`). At levels 5, 7, 9, 11 the state is cut with `&&& (2^x − 1)`. The bound uses the
  shift amounts: `12·2^λ` has bits λ+2 and λ+3, so `((Y &&& Y>>1) >>> 2) + 1` with Y the OR of the
  remaining rows' shift amounts bounds every allowed lane. Later masks are right shifts of the
  first. The overflow-check mask is `(TM7 / 4095) · 3072`.
- **Result.** d = 16: 5.2–7.2M per case (6.2M average over seeds 1–6) versus 8.2–8.8M.
  Six-case local total 18.24M (v5d 21.84M).
- **Rejected along the way.**
  - Trimming without relabeling only saved about 1M per case.
  - Building the full-width mask with a doubling chain (v5e) cost +0.25M per case.

### Kernel and elaborator pitfalls found while proving v6

- **`ite` inside a `Nat.rec` step.** It made the kernel's `rfl` check (unrolled graph against
  structured form) take more than 10 minutes. The same dispatch written as nested
  `Nat.rec … (Nat.xor k t)` checks in seconds. Use `tr16_ite` (`simp only [rec_eq, xor_eq_zero_iff]`)
  to reason about it.
- **`simpa` in a proof about lanes.** It produced a proof term whose kernel check ran out of memory.
  Plain `exact` with `[a,b,c].length` reduced by `rfl` was fine.
- **Unfolding in proofs.** `unfold f` of a definition whose body has a `Nat.rec` on a big
  computation, and `rfl`/`show` that compare `List.map` over different lists, can make the
  elaborator or kernel evaluate symbolic `Nat` terms or `enc … 65536` (OOM). Fixes: prove generic
  unfolding lemmas (`pickZ_eq`, `hlT_succ_eq`, `hlT_succ_zero`) and rewrite with explicit
  instances; keep both sides syntactically aligned (`stepR_lam`); mark big heuristic definitions
  `@[irreducible]`.
- **Peak memory has a per-definition threshold.** Locally, one unrolled definition with roughly
  360–420 or more DAG nodes raises the baseline RSS of every case by about 2.2 MB, whatever the
  export size. The same junk split into a separate definition did not. v6 therefore splits the
  d = 16 graph: `a2U16`, `b2U16`, `lsU16`, `mainU16` (326 nodes). Cost: about 0.09M instructions
  per d = 16 case (instantiation plus structural cache hits).
- **Local peak RSS (MB).**

  | Version | d = 6 | d = 12 | d = 16 |
  |---|---|---|---|
  | v4a | 65.0 | 65.6 | 80.6 |
  | v5d | 64.9 | 65.0 | 71.7 |
  | v6 | 63.3 | 63.6 | 66.2 |

### sha256 v8 and polydisc v5 (Oct 3, afternoon)

- **Literal-first operations save instantiation.** When the kernel substitutes arguments into a
  body, an application whose first argument is closed (`App(Nat.land, 0xffffffff)`) is reused, so
  `Nat.land 0xffffffff x` rebuilds one node where `Nat.mod x 2^32` rebuilds two. Net about −230
  instructions per mask even though `land` sits four places later in the dispatch list
  (sha256 −0.4%). Sharing a partial application between two operations (`App(xor, g)`) gained
  nothing: the substitution cache costs about as much as the rebuild.
- **σ₁ factoring (sha256).** `σ₁(x) = (y ⊕ (y >> 2) ⊕ x) >> 10` with `y = dup x >> 7` reuses σ₀'s
  `y`; the plain shift folds into the final shift. One operation less per schedule word (−1.5%).
- **`x + 0` can be dropped.** The kernel reduces `Nat.add x 0` to `x` (recursion on the second
  argument) when checking a flat graph against its structured form; `Nat.add 0 x` cannot be dropped.
- **Several chain steps per graph (sha256 `stepF8`).** Each substitution of the chain state into a
  step body costs about 70k beyond the per-node work. Eight steps per graph: −0.7%.
- **`natdag%` elaborator.** Builds a shared `Expr` from a line-per-node string in linear time. Nested
  `share` for an 18.7k-node graph took 47 s and 3.9 GB; `natdag%` takes seconds. Supports a final
  `app f …` or `list …` line.
- **Aggregated exactness check (polydisc).** Floor-division remainders are non-negative, so
  `Σ |eᵢ| − dm·Σ ⌊|eᵢ|/dm⌋ = 0` iff every division is exact: one product per PRS step instead of
  one per element (D5 −10%). 2-adic or reciprocal-estimate quotients are not sound with an
  aggregated check (no non-negativity), and a per-element full check costs as much as division.
- **Unrolled generator (polydisc).** The two `Nat.rec` loops of the LCG coefficient generator cost
  12M (D1) to 62M (D5) per case; unrolled per width band and checked by kernel `rfl` they cost
  about 6M to 27M. A lane-parallel jump-ahead LCG would bring D5 to about 2M (not done).
- **Rejected for sha256:** a small-number rotation base (`x·2^26 + x/64`, 3 ops) instead of the
  possibly-big duplicated word (+1.6%); bit-sliced/spread representations; SIMD rounds.
- **Remaining sha256 ideas (about −0.4% together):** merge the constant parts of rounds 0–3, skip
  the reduction of a64, e64, W62, W63 and of the first digest word. Each needs special first/last
  rounds in the structured proof.

### polydisc v6 and ca-rule110 v6 (Oct 3, evening)

- **Kernel list matching is expensive.** In polydisc v5 the generator built a 25-element
  `List Nat` and the PRS matched it with `| [f0, …, f24] => …`. The compiled matcher walks the list
  through `List.casesOn` one cons cell at a time, with motive and minor-premise instantiation at
  every level: about 10M per case, measured by swapping the matcher for a direct call. v6 passes
  the 25 coefficients to a continuation instead (`genFlat…C s k` ends in `k c0 … c24`), so no list
  is built or matched. The proof keeps the list form: `appL k d L` applies `k` to a 25-element
  list (default `d` otherwise), and `genFlat…C s k = appL k d (2 :: genFlat… s)` is one kernel
  `rfl` per width band. polydisc 1.411B → 1.353B (−4.2%); per case D1 43.4M, D3 54.9M, D5 578M.
- **Literal-first constants in ca-rule110.** Every product, mask and or with a constant now has
  the constant first (`Nat.mul 0x7feb352d x`, `Nat.land MASK x`, `Nat.lor 1 x`): 3.914M → 3.883M
  (−0.8%). The proofs flip operands back with `Nat.mul_comm`/`Nat.and_comm`/`Nat.or_comm`;
  `show` patterns on `testBit` goals had to be restated with the new operand order (otherwise
  `show` unfolds into a max-recursion error).
- **A left-drifting rule-110 step** (`T = S + S`, `S' = (T ||| S) − ((T + T) &&& T &&& S)`, final
  shift by 256 + k) avoids the right shift but measured only −0.3% in a prototype; not adopted.
- **polydisc D5 product sizes.** Most limb work is in products whose small operand has ≤ 1024
  limbs at a 2:1 size ratio (49%) or ≤ 512 limbs at 2:1 (22%); there are 231 divisions per case.
  GMP is already in its Toom range there, so the clearest remaining D5 saving is in the generator
  (about 27M per case for 697 sequential LCG words).

### More measurements (Oct 2, evening)

- **Fixed overhead per case is about 215k instructions** (theorem type check, sharecommon). It is
  the same for every competitor, and it is 25–35% of the smallest cases.
- **A `Nat.rec` dispatch costs 14k (zero branch) or 28k (succ branch).**
- **sha256 profile (re-measured Oct 4, 4-step case, about 4.06k instructions per operation).**
  2,338 operations per compression; per operation:
  - `is_equal` about 940 (23%). The dispatch scan costs about 73 per position (xor is 12th, land
    10th, div 7th; average position 7.1). Four `== Nat.zero` checks on the arguments and the
    `f == f0` test in `whnf_core` add the rest.
  - Instantiation of the step graph about 740 (18%). Most operations rebuild two `App` nodes; a
    literal-first operation rebuilds one.
  - `reduce_recursor` environment lookup about 470 (11.5%).
  - `whnf` cache probe and insert about 300 (7%).
  - Cache teardown (`~type_checker`) about 310 and object freeing about 320 (7–8% each).
  - Everything else (`whnf` logic, `mk_lit`, small GMP, big-number dups) about 1k.
  - The op count looks minimal for these primitives. The levers left are a cheaper rotation
    representation (no known one) and xor/land dispatch.
  - Peak RSS grows by about 385 KB per compression (H3: 267 MB versus 70 MB for H1). That is about
    165 bytes per retained cache entry. The official user+kernel counter pays page faults on this
    growth (estimated 1–2%).
- **Retained results.** Every big-op result stays in the kernel's whnf cache. Allocated memory, and
  with it page faults in the official user+kernel count, grows with the number and size of big ops.

### Dispatch, fib v6/v7, polydisc v7, ca-rule110 v7 (Oct 3, night)

- **Closed branches.** A selector written as
  `Nat.rec (motive := fun _ => Nat → Nat) (fun n => fast n) (fun _ _ n => slow n) test n` applies
  the branches to `n` after the test, so unfolding `impl` substitutes `n` only into the test.
  partition v5 (1.583M → 1.571M), primecount v6 (1.634M → 1.626M), mertens v8 (2.337M → 2.327M),
  permanent v7 (18.24M → 18.17M, three nested selectors on `Nat.xor d k`) use it.
- **`Bool.rec` on `Nat.ble`/`Nat.beq`.** About 13k cheaper than a `Nat.rec` on a numeral when the
  succ branch is taken. On a zero branch it gains nothing: mertens measured ±3k per case for both
  its selector and its sign test, so mertens keeps `Nat.rec`.
  - It compiles only where Mathlib is imported (its `compile_inductive`). fib uses it.
  - Core-only ca-rule110 v7 (3.883M → 3.723M) needs `@[implemented_by implC]` (`implC` is the same
    selection with `if`). The theorem `implC_eq` proves the two agree. The fallback without the
    attribute (closed-branch `Nat.rec`) is about 3.81M.
  - `Bool.casesOn` is slow.
- **fib v6 (9.03M → 7.11M).**
  - **Tables from one modular power.** `X^(j+1) mod (X² − X − 1) = F(j+1)·X + F(j)` for `X = 2^K`,
    while `F(j+1) + 2 ≤ X`. The top 8 bits come from one table with K = 178, and the low bits from a
    second, small table.
  - **Lucas doubling.** `(F, L) ↦ (F·L, L² − 2)` with `Nat.pow l 2`.
  - **Addition formula and last bit.** `F(N + d) = F(N)F(d−1) + F(N+1)F(d)` joins the two halves,
    and Cassini handles the last bit.
  - **13–15 bits (`chainC`).** These finish with `2F(N + e) = F(N)L(e) + L(N)F(e)`.
- **fib v7 (7.11M → 6.95M).** For 18-bit n (`chainD`) the doublings carry the Lucas pair
  `(L(j), L(j+1))` and use two squares per bit.
  - The identities are `L(2j) = L(j)² − 2`, `L(2j+2) = L(j+1)² + 2` and
    `L(2j+1) = L(2j+2) − L(2j)`.
  - The selected doubling for bit 1 is two squares, with the sign of `L(2n')` taken from the parity
    of `n'`.
  - The result comes from `F(h) = (2L(h+1) − L(h))/5`, then `F(h)L(h)` or `F(h)L(h+1) + (−1)^h`.
  - n = 150,000 went 2.80M → 2.64M. The same scheme is worse for 16–17 bits (+20k to +60k): the
    extra linear operations outweigh the squares there.
- **polydisc v7 (1.353B → 1.305B).**
  - **Lane-parallel jump-ahead LCG.** States are `(a_j·s + c_j) mod 2^64`, held in even and odd
    128-bit lane packs. Two products, two sums and two masks give the stream.
  - **Per case:** D1 42.4M, D3 52.8M, D5 557.2M.
- **Mining earlier work for ideas.**
  - The quaternion and closure code on the PC (`lib/quaternion.ts`, `closure-test.ts`, the erdos-Fk
    jet-closure scripts) is floating-point verification and structure checking. There is no
    integer-arithmetic technique to port, which agrees with the Sep 29 review.
  - The mathematics behind those ideas is already in the entries:
    - x² = x + 1 as fib's table ring;
    - det = ±1 as Cassini;
    - doubling as Lucas doubling;
    - nested copies as rule110's tripled row and sha256's duplicated word.
  - Viewing fib as a closure/doubling problem is what suggested v7.
- **Cost anatomy of a small case (mertens, Int output).**
  - Fixed overhead with `impl = Int.ofNat 0` is 204k. About 39k of it is `sharecommon` of the
    theorem.
  - The fast path adds 108k at N = 0 and about 165k at N = 25–150 for its 17 operations, about
    10k each all-in: evaluation, substitution, freeing, cache teardown.
  - The two lane divisions by 17k- and 4k-bit denominators cost little GMP time (about 3k). The
    kernel bookkeeping around each operation dominates.

### Open ideas

- **sha256.** Board on Oct 4: 1st 9.3B total, 10th 10.81B. Ours there is still v2 (13.72B;
  6.41B on the 512-step case, matching local 6.40B, so official ≈ local here). v8 (10.24B) is
  about 9% behind 1st and 5% ahead of 10th. The concrete
  leads left are the boundary savings (about −0.3%) and the 2-lane SIMD message schedule
  (measured −1.5%, needs lane proofs).
  - **"Bent pin" ideas checked (Oct 4).** These were brainstormed with Jonathan.
    - v8 already bends the pin in three places:
      - every Σ/σ shifts the duplicated word once and reads the other rotations off that piece;
      - σ₁ reuses σ₀'s piece (`(y ⊕ (y >> 2) ⊕ x) >> 10`);
      - Maj reuses the previous round's `a ⊕ b`.
    - **Pin through the additions.** Keep every word as `x·(2^32+1)` and compare modulo
      `2^64 + 2^32`. This is valid (checked numerically), and garbage above bit 31 needs no mask.
      - The Σ outputs are not pinned words, though, so each one needs a multiply to rejoin.
      - It stays at 27 operations per round, with more multi-limb numbers, so it is not worth it.
    - **Rotated storage** (e.g. keep `ROTR6(e)`) saves one shift in Σ but costs one to set up.
      Every addition needs unrotated words.
    - **Brute force over all 2-operation bitwise programs** finds no Ch that uses the previous
      round's leftovers (`g⊕h`, `f∧(g⊕h)`, `Ch(f,g,h)`). The search was checked against a control.
      Ch stays at 3 operations.
    - **Floor of this design:** 2 new words per round, each needing one mask and one multiply.
    - **No free "glue rule" exists for the doubled word.**
      - A Σ read off a pin of any length (2–5 copies, 20k random words each) is never a
        repeating-digit number again. Only the low word survives.
      - Any rule must forgive two things:
        - the junk a rotation leaves on top, a multiple of `2^p`;
        - the carries an addition pushes into the copies, a multiple of `2^32·r` with `r` odd.
      - The only rule that forgives both is mod `gcd = 2^32`, which discards the copies. So every
        round must re-glue with real operations.
      - Longer pins also make every operation a big-number one, about +2–2.7k each.
    - **Where the picture does pay.** Copies separated by guard bits ("pins that can't touch") are
      lanes, which is the 2-lane schedule lead.
    - **Knot table: which glue rule each operation keeps** (checked on random words, `knots.py`).
      | Rule | Kept by | Broken by |
      |---|---|---|
      | "low 32 bits only" | add, mul, xor, and, or | sub, right shift |
      | "doubled word" (mod 2^64+2^32) | add, mul | everything else |
      | "clean word" | xor, and, or, sub, shift | add, mul |
      - No rule survives both an add and a right shift. Every add→rotate crossing therefore costs
        glue operations (mask + multiply), whatever route a search takes.
      - This is Jonathan's ops-as-elements picture (ARC_ATP: knot = what an op never changes). A
        rule rides along a path only if it is in the knot of every op the path crosses.
      - A cost-weighted search in the arc-proposer style would re-find v8 unless it is given a new
        kind of line, such as lanes.
  - **Pin search, run Oct 4.** Tools are in `outputs/lkc/pinsearch/`.
    - **Price list.** Measured in the judge's replay window as the per-op slope of 400- vs
      1200-op chains. Small numbers:
      | Operation | Instructions per op |
      |---|---|
      | add, numeral first | 2,978 |
      | mul, numeral first | 3,008 |
      | sub | 3,350 |
      | add, two variables | 3,398 |
      | land, numeral first | 3,449 |
      | mod | 3,616 |
      | div | 3,688 |
      | land, two variables | 3,985 |
      | lor | 4,054 |
      | xor | 4,213 |
      - A numeral first saves about 420 (one fewer rebuilt node).
      - Numbers of 2^63 and above add about 1.8–2.7k, nearly flat from 2 to 4 limbs.
      - A doubled-word pair (mul + first div) costs 6,696 when small and 11,184 when big.
    - **Route model.** It sums node prices over the step graph, using operand sizes from Python
      evaluation, and checks every route against hashlib.
      - v8 is predicted at 9.05M per step and measures 9.42M; the model leaves out about 3% of
        per-step overhead.
      - Relative predictions match earlier measurements:
        | Change | Model | Measured |
        |---|---|---|
        | SMALLY | +1.64% | +1.6% |
        | mod masks | +0.34% | +0.4% |
        | CHX/MJX | −0.01% | ~0 |
    - **Best route found.** v8 plus NOMOD, B0, B13 and BW16, plus numeral-first swaps on the 14 ops
      that had the numeral second.
      - 2328 ops per step (was 2338).
      - Measured per step 9.416M → 9.361M (−0.58%); at 24 steps the total is −0.49%.
      - Measurement-only file (no proofs) is `pinsearch/gen_trim.py`. A real v9 needs the special
        first/last rounds in the structured proof.
    - **Lanes, priced.**
      - 2-lane schedule: the lane work alone is 41.7k per word against 54.2k for v8. With packing,
        extraction and alignment it rises to about 70.9k, so it loses. (The earlier smarter design
        measured −1.5%.)
      - σ₀ of W1..W7 in 7 lanes: 147k against 173k, about −0.3%, but only if the digest arrives
        packed.
    - **Verdict.** With these kernel operations, v8 is within about 0.6% of the cheapest route.
      The 9% gap to 1st is not a routing problem.
  - **Crossing search, Oct 4** (`pinsearch/crossing_search.py`, Jonathan's swarm/Euler idea).
    - **Question.** Is there a one- or two-operation way from a sum still carrying junk above bit 31
      to the doubled word, or straight to a rotation window?
    - **Method.** Forward: 14,439 first operations over all kernel ops and about 10k structured
      constants. Backward: the last operation's constant is solved exactly for add, sub, xor, and,
      or and mul, and enumerated for div, mod and shifts. Checked on 40 test words, with junk up to
      2^30.
    - **From the junk-carrying sum.**
      - No one-operation crossing.
      - Only 4 two-operation routes exist, and all of them reach the doubled word, never a window:
        - mask + ×(2^32+1), which is v8;
        - mod 2^32 + ×(2^32+1);
        - ×(2^32+1) then mod (2^64+2^32), the "Euler" route (the multiplier is the binary
          e^{iπ}+1; mod forgets the windings);
        - ×(2^96+1) then the same mod.
      - Every one of these makes a number of 2^63 or more.
    - **From the clean word.** 6,413 two-operation routes reach a window, none of them all-small.
      The cheapest is v8's ×(2^32+1) then div, at about 8.9k on average. A three-op all-small route
      costs at least about 9k, so there is no gain there either.
    - **Conclusion.** The crossing toll is a hard floor for this vocabulary. The gap to 1st is
      probably in per-operation overhead (about 3k of bookkeeping per op), not in the maths.
- **polydisc.** D5 (85% of the total) is multiplication-bound. A (magnitude, sign) pair encoding
  would drop the `>> 1`/`<< 1` re-encoding of every big coefficient (estimated −3.8%), but the PRS
  proofs would have to be redone. Kronecker packing triples the multiplication work at D3/D5
  because the lanes have to be padded to the output width.
- **fib.** 16–17 bit cases are at the floor of the current scheme. The top product cannot become a
  square.
- **ca-rule110.** Left-drifting step, about −0.3% to −0.5%.
