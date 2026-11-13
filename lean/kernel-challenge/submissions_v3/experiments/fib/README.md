# Fibonacci experiments, October 1, 2026

**Keep V2. Neither checked experiment established a speed improvement.**

- `SHARED.lean`: elaboration-time sharing of the two doubling products and their difference. It is definitionally the same arithmetic as V2, and the existing universal proof still checks.
- `Submission.lean`: the shared arithmetic with two input bits consumed per structural recursion step. `pairLvl_eq` proves equivalence to the one-bit loop for arbitrary starting values; `run_eq` handles odd and even bit lengths. The existing universal Fibonacci proof then applies.

Both files use only `import Spec`, with the pinned permitted Mathlib closure. There are no added dependencies in either submitted file, no answer tables, and no input-specific answer constants.

Each passed the participant package's strict Lean 4.33.1 build (`autoImplicit = false`, `warningAsError = true`). Each was then compared with the unchanged V2 implementation, renamed only to `Baseline`, over all six public endpoints, with 31 alternating-order synchronous kernel checks per endpoint. Timing uses `Kernel.Environment.addDeclCore`; these are local Windows wall times, not official instruction counts.

| Input | Shared / V2 | Two-bit / V2 |
|---:|---:|---:|
| 5,000 | 0.996 | 1.108 |
| 10,000 | 0.988 | 1.073 |
| 20,000 | 0.989 | 1.125 |
| 40,000 | 1.000 | 1.058 |
| 80,000 | 0.973 | 1.107 |
| 150,000 | 1.012 | 1.055 |

The sum of per-input medians changed from 1.4149 ms to 1.4067 ms for sharing (0.6%, inconclusive), and from 1.5930 ms to 1.7244 ms for batching (8.2% slower). These were separate runs; their baseline totals differ, so compare each candidate only with its own paired baseline measurements.

Reports and exact source hashes are in `../../results/fib-shared.json` and `../../results/fib-paired.json`. All 372 computation checks in each report passed, and both correctness-axiom audits printed only `propext`, `Classical.choice`, and `Quot.sound`. The saved experiment hashes match the measured sources exactly. The two-bit experiment also passes the unchanged evaluator `Solution.lean` bridge under strict settings; final build, bridge, and axiom outputs are saved as `../../results/fib-build.txt`, `fib-bridge.txt`, and `fib-axioms.txt`.

A further elaborator experiment specialized the whole loop to fixed public bit lengths. Its build was stopped after several minutes without completion. That scratch experiment has no validated correctness or performance result and is not included as a candidate.

Pinned dependencies and builds are local to `.v3-work/fib`. The setup script fetched dependency build artifacts into Mathlib's nested package workspace; those cached build directories were copied into the matching outer pinned-package directories so the participant build could reuse them. No global PATH, toolchain, or dependency settings were changed. No website submission or official evaluator replay was performed.
