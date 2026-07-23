# Can you only read ONE side of the void line at a time? — no, the register is symmetric

*Companion to `FOLDING_MATCHING_SLOT.md`, `FOLDING_STRANDS.md`, `FOLDING_KNIT_WEAVE.md`. Jonathan's hypothesis: you can only read one side at a time, which is why single strands peel off — like DNA, where strands separate so one template is read at a time. Tested two structural forms on 8 proteins; `antiparallel_test.py`, `exposure_test.py`.*

## Form 1 — is the register ANTIPARALLEL? — NEGATIVE
If a single pass reads one direction, the two faces should run antiparallel. Measured: void line **43% antiparallel, mean cos +0.11** (slightly *parallel*) — statistically identical to within-domain packing (p=0.25). Two proteins lean antiparallel (6LDH 56%, 8TLN 65%), calmodulin 0%, but no general rule. Direction is not the reason.

## Form 2 — is the pairing a LOCKED / asymmetric register? — NEGATIVE
Exposure of the two partners at each cross-seam contact: asymmetric (one readable/one hidden) is **not enriched** at the seam (31% vs 39% baseline); partner exposures are **positively correlated** (both buried together or both exposed together); the largest bucket is **both-exposed (40%)** — directly contradicting one-at-a-time.

## What this settles
Both readings of "one side at a time" fail. The void-line register is **symmetric** — a palindrome-like complementary register, not DNA's polar template/coding. So DNA stays an anchor for **complementarity** (the matched +/− slots) but **not for directional reading** — a real, specific difference worth keeping honest. And the peeling single strands aren't caused by a reading constraint; they unbundle at the border to reach the ligand (a function reason, symmetric — both domains send loops).

*Artifacts: `antiparallel_test.py`, `exposure_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
