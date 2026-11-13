# V3 candidates — October 1, 2026

V1 is already ranked on the website and V2 has run in the playground, with processing pending (reported by Jonathan). No website submissions were made in this work. All eight V2 files remain byte-for-byte unchanged; see `v2_baseline_sha256.json`.

## Current files to compare in the playground

| Priority | File | Change | Local kernel wall-time result versus V2 |
|---|---|---|---|
| 1 | [SHA-256](sha256/Submission.lean) | Direct Nat final digest packing; rounds and schedule unchanged | **25.7% lower** six-case median sum in final five-repeat comparison; earlier three-repeat comparison was 26.5% lower |
| 2 | [Permanent](permanent/Submission.lean) | Shared row graph, redundant mixer masks removed, tighter proved lane width | **10.6% lower** six-case median sum; an additional input set was 14.5% lower |
| 3 | [Rule 110](ca-rule110/Submission.lean) | Shared initial mixer and two inlined steps per recursion iteration | **2.3% lower** six-case median sum in final 101-repeat comparison; modest and mixed per-case gains |
| Cleanup | [Polydisc](polydisc/Submission.lean) | Replace partial elaborator helper with terminating recursion | No numerical algorithm change or speedup claimed |

**These percentages are local Windows kernel wall times, not official instruction counts or predicted leaderboard positions.** Every listed candidate passes a strict Lean 4.33.1 participant build, the unchanged evaluator `Solution.lean` bridge, and the permitted-axiom audit. Full official export replay, memory-limit checks, and playground scoring remain to be run.

## SHA-256

Replace `fin` with direct `Nat.add`, `Nat.land`, and `Nat.mul` operations. This avoids constructing a Digest, accessing fields, calling eight `add32` helpers, traversing an eight-word list, and reducing arithmetic typeclass wrappers on every hash. The original round graph and universal correctness proof are retained.

Final five-repeat result: sum of six case medians **4.3552 s → 3.2356 s**. The two 512-step cases improved by approximately 25% and 27%. See `results/sha256-final-quiet.json` for every sample and source hash, and [the experiment notes](experiments/sha256/README.md) for the earlier comparison and rejected constant-folding attempt.

## Permanent

The mask-free packed dynamic program from V2 is retained. Three improvements are combined:

1. Expand the seeded-column computation and three shifts into a shared expression graph, borrowing the technique already used in V2 SHA-256 and polydisc.
2. Remove the final mask from each mixer after proving its input and XOR output remain within 32 bits. Essential multiplication masks remain.
3. Prove that the first DP row has at most 1 in any lane: its three distinct shifts move the single initial 1 to distinct lanes. Subsequent rows grow a lane by at most a factor of 3, giving `3^(k-1)` instead of `3^k`.

The last change narrows lanes at dimensions 6/12/16 from **10/20/26 bits to 8/18/24 bits**. The universal proof and the small-dimension fallback remain.

Six-case median sum versus V2: **17.4934 ms → 15.6314 ms** (31 repeats). The additional 14-input set checks small dimensions and seeds 0, 7, and 0xffffffff at the published dimensions. Large-case timings are variable: one dimension-16 seed regressed against the earlier V3 candidate in one comparison, although all six cases improved against V2 in the recorded run. Official instruction measurement is still required.

[Detailed permanent results](experiments/permanent-mixers/README.md) include comparisons against both V2 and the earlier shared-row V3. The directory name is historical; paired mixer packing was not implemented. The previous V3 file is preserved as `experiments/permanent-shared-row/Submission.lean`.

## Rule 110

The initial packed mixer shares intermediates. Two automaton steps are expanded into one recursion body; quotient/remainder decomposition preserves all step counts, and the existing 256-step re-copy logic remains.

Final six-case median sum: **0.9472 ms → 0.9250 ms** (101 repeats). This is a small improvement. Extra checks cover zero steps, odd counts, and both sides of the 256-step boundary, including 511 and 512 steps. The universal proof covers every input. Larger chunk sizes were screened but offered worse tradeoffs on small cases.

Evidence: `results/ca-final-quiet.json`, `results/ca-edge-cases.json`, and [experiment notes](experiments/ca-rule110/NOTES.md).

## Polydisc cleanup

Replace `partial def shareChain` with recursion on an explicitly decreasing Nat budget. The elaborator rejects a chain that exceeds 100,000 bindings instead of silently truncating it; this graph uses about 8,000 bindings. The numerical implementation and proof are unchanged. This addresses the checked-in rules' prohibition on `partial`.

## Experiments not recommended as replacements

- **Fibonacci:** sharing alone was effectively neutral. A proved two-bit loop was about 5–13% slower across the six endpoints. Fixed-length unrolling encountered excessive proof/build cost and was stopped. Keep V2. See `experiments/fib/` and `results/fib-*.json`.
- **Partition:** the proved two-level Durfee/Horner loop changed the six-case median sum only from 0.410 ms to 0.407 ms. This does not establish a useful improvement. It remains `partition/EXPERIMENT.lean`, with `results/partition-paired-loop.json`.
- **SHA round constant folding:** not promoted because symbolic equality checking became much slower. No complete successful proof build or runtime improvement is claimed for it.

## Validation and reproduction

`results/validation.json` records current candidate hashes, sizes, strict-build/bridge status, axiom output, and the exact toolchain. Build and audit logs are saved as `results/<problem>-v3-strict-build.txt` and `results/<problem>-v3-axioms.txt`. Only `propext`, `Classical.choice`, and `Quot.sound` occur in the correctness proofs.

The project-local Windows toolchain is `.local-tools/lean-4.33.1-windows`. No global PATH or toolchain setting was changed. Scratch workspaces are under `.v3-work/`; tools and scratch directories are excluded through `.git/info/exclude`. The pinned Mathlib closure has also been set up for the Fibonacci experiments.

The benchmark script `scripts/bench_v3_kernel.py` now builds both compared modules before timing, checks that source files stayed unchanged, and rejects incomplete sample sets. It compares the universal-proof-checked candidate with a namespace-renamed V2 baseline. Each reference equality is checked synchronously through `Kernel.Environment.addDeclCore` using a fresh kernel checker. The organizers' reference answers appear only in scratch benchmark equalities, never in submissions. Import and build time are outside the timed region.

With the pinned `lean` and `lake` on PATH, run from the repository root:

```powershell
python -X utf8 scripts/bench_v3_kernel.py sha256 .v3-work/sha-v3 --repeats 5 --output submissions_v3/results/sha256-recheck.json
python -X utf8 scripts/bench_v3_kernel.py permanent .v3-work/permanent-mixers --repeats 31 --output submissions_v3/results/permanent-recheck.json
python -X utf8 scripts/bench_v3_kernel.py ca-rule110 .v3-work/ca-v3 --repeats 101 --output submissions_v3/results/ca-recheck.json
```

An early experiment timed asynchronous declaration scheduling instead of kernel completion. Those measurements are explicitly marked invalid in `results/DISCARDED-asynchronous-timing.json`. Use the final reports above.

## Further ideas

- Compare these exact SHA-256 and permanent candidates in the playground before inferring ranks or replacing a formal entry.
- For permanent, a proved two-row bound of 2 could reduce the dimension-12 lane width from 18 to 17, but would leave dimensions 6 and 16 unchanged. This is not implemented.
- Paired permanent mixers and a two-lane SHA schedule remain possible. The latter needs masking before packed additions and careful handling of odd schedule offsets; operation savings remain unmeasured.
- The earlier Fibonacci/physics notes and framework paper were sampled. They do not supply a drop-in kernel algorithm. The directly transferred idea here was the shared-expression technique already present in V2 SHA-256 and polydisc.
