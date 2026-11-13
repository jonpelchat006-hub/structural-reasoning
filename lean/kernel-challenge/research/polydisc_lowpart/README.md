# polydisc D5: the "low part only" method and its provable width bound (Oct 19-20, 2026)

Scripts (run in the Linux workspace; need prs_model.py, reference_answers.py, gmpcost):

- `price.py`: GMP cost of D5 today (full numerators + exact division) vs the low-part method with measured widths.
- `subres_check.py`: checks that each PRS polynomial equals +-(the subresultant determinant): 223/223.
- `bound_price.py`: column-sum (Hadamard-type) bound from the spec's width limits: 1.4-1.8x too wide, cost 471M (no gain).
- `bound2.py`: permutation bound |det| <= k! x (largest permutation product), the largest product found by a max-weight assignment on the width limits.
- `bound_price2.py`: low-part cost with the permutation bound: 281.6M per D5 case vs 469M today (bound within 0.2-0.8% of actual widths).
- `transpose.py`: permanent, DP state counts for A vs its transpose (200 seeds, d = 12 and 16).

What a real v9 would still need in Lean (core, no Mathlib): integer determinants, the identity PRS step = +-subresultant
determinant (so every division is exact in the normal case), |det| <= k! x max product (Leibniz), and dual potentials
certifying the max product offline. See the project doc claude/PROBLEM_ATLAS.md.
