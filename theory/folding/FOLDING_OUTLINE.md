# Depth 0 — the whole's fundamental mode is the outline; the seam is sign(f), no cut

*Companion to `FOLDING_TOWER.md` (the algebra tower = recursion skeleton), `FOLDING_TRAIL.md` (the C trail), `FOLDING_CLEANUP.md` (the +1/−1/0 trinity), `FOLDING_CLIMB_WALL.md` (seam from sequence). Jonathan: Euler's equation is the top level = depth 0; 2⁰ − 1 = 0 cuts, but the "−1" leaves an OUTLINE — the global web we don't cut into. Could depth 0 hold the coarse seam? Tested; `depth0.py`.*

## Depth 0 = the whole, uncut, carrying one fundamental mode
2⁰ regions = 1 (the whole); 2⁰ − 1 = **0 cuts**. But the intact whole has a **fundamental mode** — the Fiedler eigenvector **f**, a smooth function over the entire graph, present with **no cut made**. Its **nodal outline** (f = 0, where + meets −) is the seam. Depth 0 is the reals (the tower's base, no imaginary axis); the recursion cuts *inside* it; the top level just holds the whole and reads its outline.

## The outline IS the trail (CONFIRMED)
Correlation of |f| (distance from the nodal outline) with mixedness (the trail):

| pdb | outline width (|f|<0.15) | corr(|f|, mixedness) |
|---|---|---|
| 8TLN | 9% | **−0.84** |
| 1CLL | 3% | **−0.74** |
| 1GD1 | 6% | **−0.73** |
| 2LZM | 9% | **−0.63** |
| 4AKE | 27% | **−0.44** |

Small |f| — right at the outline — is exactly where the trail is. **Depth-0's outline and depth-8's trail are the same object.**

## Three things unified
- **seam = sign(f)** — the +1/−1/0 of the fundamental mode's sign is the cleanup trinity. Cutting to depth 1 doesn't impose a division; it commits to a sign already there.
- **outline = trail** — |f| is distance from the seam-line, zero along the C trail.
- **it is what survived from sequence** — the climb-wall seam (82–94%) was literally sign(f) of the *predicted* web's fundamental mode. The coarse seam is the cheapest, most robust thing in the stack.

## The Euler flavor, made rigorous
The core the intuition points at is the **fundamental eigenmode**: Euler's e^{iθ} is the fundamental mode of the circle; the Fiedler vector is the protein graph's version — the lowest global oscillation, whose nodes are the boundaries. And **e^{iπ} + 1 = 0** is the complex-level face of the trinity: the far side (−1) and the near side (+1) meet at the void (0) = the nodal outline. The tower descends from there: reals (whole) → complex (first sign = seam) → quaternion → octonion → sedenion, each level cutting one algebra deeper into what the top already outlined.

*Artifacts: `depth0.py` (Fiedler fundamental mode of the whole web; |f| vs mixedness; 2LZM, 4AKE, 1GD1, 1CLL, 8TLN).*
