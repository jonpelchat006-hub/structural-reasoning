# SHA-256 v3: direct final digest packing

`Submission.lean` keeps all v2 SHA-256 rounds and the message schedule unchanged.
The only numerical implementation change is `fin`: adding the eight SHA-256
initial-state words and packing the result now uses `Nat.add`, `Nat.land`, and
`Nat.mul` directly. This avoids constructing a `Digest`, accessing its fields,
unfolding eight `add32` calls, traversing the eight-element list in
`encodeDigest`, and reducing the arithmetic typeclass wrappers on every hash.
The original universal correctness proof compiles without changes.

## Local results

This is synchronous kernel declaration-check wall time on Windows, **not**
the official instruction-count metric. V2 is compiled as `Baseline` in the same
imported environment. Timing alternates candidate/baseline order each repeat.

| Hash steps | Seed | Candidate / V2, median of 3 |
|---|---|---:|
| 4 | 1 | 0.920 |
| 4 | 2 | 0.869 |
| 32 | 1 | 0.910 |
| 32 | 2 | 0.724 |
| 512 | 1 | 0.726 |
| 512 | 2 | 0.737 |

The six median sum is 3.0196 s versus 4.1106 s, a 26.5% reduction. An earlier
five-repeat screen at 4 and 32 steps found ratios from 0.785 to 0.872. Both runs
check every answer against the organizers' reference computation. These are
screening results; a quiet repeat and playground instruction measurements are
the next validation steps.

Saved evidence in `../../results/`:

- `sha256-fin-screen.json`: four-case, five-repeat screen.
- `sha256-fin-six-case.json`: six-case, three-repeat check.
- `sha256-fin-validation.json`: source hash, toolchain, strict build and bridge status.
- `sha256-fin-strict-build.txt` and `sha256-fin-axioms.txt`.

Candidate SHA-256:
`73c655aa3d7261a4fcfb0f1a555e319cc5cd503b14cf78ba1a80eb47876166ed`.
It passes Lean 4.33.1 with `autoImplicit = false` and `warningAsError = true`,
the unchanged evaluator `Solution.lean`, and an axiom audit limited to
`propext`, `Classical.choice`, and `Quot.sound`. V2 is unchanged.

## Investigations not included

Constant-folding the round graph removes 102 closed or definitionally trivial
operations and seven constant bindings. However, its symbolic equality check
became much slower, including an attempted direct kernel declaration. Those
builds were stopped rather than promoted. This experiment has no successful
complete proof build or performance claim.

A two-lane message schedule remains possible. With 64-bit lane spacing,
right-shifted upper-lane bits spill into the unused high portion of the lower
lane. Each paired sigma result must be masked before the schedule sum so this
spill cannot create a carry into the upper lane. Odd offsets in the schedule
also need lane realignment. A rough operation count suggests about six saved
primitive operations per pair of schedule words, before proof and timing work.
This is a design estimate, not a tested improvement.

## Reproduction

With `.local-tools/lean-4.33.1-windows/bin` on PATH:

```powershell
python -X utf8 scripts/bench_v3_kernel.py sha256 .v3-work/sha-v3 --repeats 3 --output submissions_v3/results/sha256-fin-recheck.json
```

The scratch workspace contains the exact candidate and v2 baseline. No file
was submitted to the website.
