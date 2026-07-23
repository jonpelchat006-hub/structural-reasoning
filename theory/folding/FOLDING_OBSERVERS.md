# Multiple Observers — agreement is the invariant, disagreement is the depth

*Companion to `FOLDING_SHADOW.md`, `SPHERE_GENERATOR.md` Part B, `SPARSE_VESICA_EXPANSION.md` §18.16. Jonathan: multiple observers at different spots (the larger structure looking down, the C cores, one inside the window, the neighboring C on the tangent) — one sees the invariant, another the shadow. Tested on 8 proteins; `observers_test.py`.*

## 1 — the "closes vs ends-at-a-height" label is viewpoint-dependent (CONFIRMED)
Even the net-0 ("closed") proteins show the ±1 height from some angles (1PHP 8%, 2LZM 29%, 3PGK 21% of directions). "Closes / ends at a height" lives in the vantage point, not the protein.

## 2 — a committee recovers the height, but only what is really there (CONFIRMED, honest split)
Single vs 3 random vs 3 **orthogonal** observers detecting |net|=1: big offsets (1CLL/6LDH/8TLN) — one observer fooled ~37% of the time, 3 orthogonal catch it **100%** (a large 3D height can't hide from a complete frame). Genuine near-closures (1PHP/1GD1/4AKE) — even 3 orthogonal catch only 23–45%, because the offset is truly tiny. **A committee recovers real structure; it does not manufacture it.**

## The refinement — agreement = invariant, disagreement = depth
The invariant is what ALL observers agree on (|net|≤1, undistortable); the height is recovered from where observers **disagree** (one sees ±1, another 0). That disagreement *is* the depth — **stereo vision exactly**. The four observers (global + normal + local + tangent) are a spanning orthonormal frame riding the chain; a complete frame is what recovers the large offsets fully. Honest ceiling: recovers the coarse ±1 invariant, degrades gracefully for fine 3D detail — gets the big true things every time, the tiny things never (a reader that must not hallucinate).

*Artifacts: `observers_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
