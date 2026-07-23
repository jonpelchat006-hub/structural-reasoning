# The Knife — is the cut flat, and what is the cutting plane made of?

*Companion to `FOLDING_WINDOW_SEAM.md`, `FOLDING_CONSTRAINT_LADDER.md`, `RIP_TEST_RESULTS.md`. Jonathan's question: the ripper is a "knife" — what is its shape, and what physical thing is "flat enough to cut into our sheets and always nearby"? Tested on 8 two-domain proteins; `knife.py`, `width.py`, `complement.py`, `medial.py`.*

## Result 1 — the cut IS a flat plane (CONFIRMED)
Split at the min-cut seam; a single flat plane separates the two domains' Cα clouds: **planar separability 0.85–0.98 (median ~0.94)**, margin 0.36–0.57, seven of eight ≥ 0.92. The knife is a plane.

## Result 2 — the plane is NOT aromatic rings (ruled out)
Planar aromatics (F/Y/W/H) show no consistent enrichment at the cut (0.40×–1.99×); they stack in domain cores, not the seam.

## Result 3 — the seam's scale, and why it is NOT light (measured)
Closest domain approach **~1.4 Å median**; depleted-slab void width **~27 Å median** — a ~1–30 Å feature. Visible light is 4000–7000 Å (150–5000× larger), and proteins fold in darkness. **The knife is not photons.** (A refractive-index jump exists — n≈1.5 vs 1.33 — so light *refracts* at the plane, but that is light responding to it, not making it.)

## Result 4 — PAINT THE WALLS: the two faces are complementary imprints (CONFIRMED)
- **SHAPE:** B's face fits A's **2.4× better in the true orientation than any rotated pose** — B is the negative mold of A.
- **CHARGE:** **70% of charged cross-cut contacts are opposite-sign** salt bridges (vs 50% chance).
- **POLARITY:** like-faces-like, weakly (z ≈ +0.7).
- **The exception proves it:** calmodulin (the only shape failure, 0.75×) — its lobes don't pack, so there's no wall to paint.

## Result 5 — the zero-divisor line, made real: an equidistant voxel trail (CONFIRMED)
The medial surface (voxels equidistant from A and B): the signed field d(A)−d(B) sweeps A-side(+) → **0 (null line)** → B-side(−) over ~5 Å; the null locus is a bounded **trail of ~440–600 cancelled voxels** that **terminates** (~50–60 Å patch with a rim) — it exists only where both walls are present and ends when it "runs out of paint." The digital bisector is a **45° zigzag** (y = ±x on a square grid). Cuts go to different depths (0–62 Å).

## What the plane physically is
The cutting plane is the **contact gap** — minimal contact density between two compact domains. Nothing slices there; it is where there is *no protein*. Water fills it, light refracts at it, fields line it — all **respond** to the plane; the fold geometry makes it. **The knife is a plane of absence**, its two walls complementary imprints, its midline a bounded equidistant trail that ends where the walls end. (Framework echo: optimal Void fraction 0.15–0.25 vs accessible Ramachandran ~0.18 — both keep ~1/5 open; the null-trail geometry is a measured realization of the zero-divisor / 45° light-cone picture.)

*Artifacts: `knife.py`, `width.py`, `complement.py`, `medial.py`, `paint_walls.png`, `zero_divisor.png`.*
