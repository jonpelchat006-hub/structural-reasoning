# Rule 110 candidate: shared mixer and two-step chunks

Universal proof and strict build pass on Lean 4.33.1. The mixer uses shared expressions; two cellular-automaton steps are inlined into each recursion iteration. An exact quotient/remainder decomposition handles every step count, including odd counts and the 256-step re-copy boundary.

Screened chunk sizes 2, 4, and 8. Eight-step batching regressed small cases. The inline two-step candidate was about 4.1% faster in the latest six-case aggregate wall-time screen (51 repeats); this remains local screening data, not official instruction scoring. Larger gains were concentrated at eight steps. The final 101-repeat six-case comparison found a 2.3% aggregate improvement (results/ca-final-quiet.json). Additional zero/odd/boundary/511/512-step inputs all passed (results/ca-edge-cases.json). The candidate is now copied to ../../ca-rule110/Submission.lean.

Screen report: ../../results/ca-inline2.json. Original v2 remains unchanged.
