# Folding-Rip Investigation — Roadmap (what's done, what's left)

*Companion to `RIP_TEST_RESULTS.md`. Same discipline: name the empirical claim, test it, believe the number.*

## Confirmed (7 bricks)
1. Rip = min-cut finds domain boundaries to ~1 residue. 2. Seam-depth contrast detects rippable vs solid before cutting. 3. Weave = cross-domain upper floors predicts un-rippable folds (~4×). 4. Border-dominant segments are the mechanism (~4.4×). 5. Wet seam (the rip line is polar/exposed). 6. Gate (spots break and reseal reversibly, ADK 77/54). 7. Rhythm (functional motion in the slow-mode subspace, ~7× above chance, 9/10). All operate on the known structure's contact web.

## T1 — THE BIG BET, RESOLVED: the rip is web-easy, NOT sequence-easy
Predict the seam from sequence alone: structure ripper (has the web) median boundary error **2 residues**; **sequence-only median 30, mean 37 ≈ random (38.7)**. The linker signal exists but ranking fails — a true inter-domain linker and an intra-domain surface loop look identical from sequence; telling them apart needs the contact web. "The rip is the easy direction" is TRUE given a structure/web (fast domain parsing, gate-finding, seam detection all near-perfect) but is NOT a shortcut past the fold wall. The seam is downstream of the web.

## Open tests / questions
Non-contiguous partition for woven folds; B-factors for the bouncing bits; pore/hole detection; allostery (modes apo vs holo); a principled recursion stop-rule; escort/quaternary. The honest way past T1 is T1′ — feed a *predicted* contact web (coevolution/pLM) into the ripper (climbing the wall, not going around it). Q1: does any of this feed the ARC solver (tearing a task at its thin seam into independent sub-problems)? The reframed bottom line: the web is the pivot; everything above it is cheap and confirmed; sequence→web is the one wall.
