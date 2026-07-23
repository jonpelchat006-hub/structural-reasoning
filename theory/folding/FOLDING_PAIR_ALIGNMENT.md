# Pair Alignment — points defining a center come in pairs; aligned-vs-non-aligned is real, but it's GEOMETRY, not N/S

*Companion to `FOLDING_THE_KNIFE.md` R4 (the two walls are complementary imprints — paired points across the void), `FOLDING_METAL_WELLS.md` (the soft-N/S magnetic wells vs hard-O wells), `FOLDING_FLOORS.md` (the nested cut recursion / D as the nested-C convergence). Jonathan's idea: surrounding the void, a point on one side requires a point on the other (pairs straddling the void); pulling the D part in adds an aligned pair and cascades new defining pairs down the floors; and — the testable claim — **aligned** (collinear/axial) pairs might be "the N/S stuff" while **non-aligned** (in-plane) points are "the lines that fill the pixel." Tested on the metal centers; `coord_alignment.py`.*

## The mapping tested
Around a metal, decompose the coordination sphere: an **aligned pair** = *trans* ligands (~180°, straddling the center on one axis, a point on each side); a **non-aligned** set sits in a plane at ~90° (the equatorial "pixel"). Test whether aligned pairs are the N/S (soft) donors and non-aligned points are the pixel-fillers.

## Result 1 — the pairing dichotomy is REAL (CONFIRMED)
Centers split cleanly into two classes by aligned (trans) pairs:
| center | coord # | aligned pairs | donors | class |
|---|---|---|---|---|
| heme Fe (1MBN) | 6 | **3** | 5N, 1O | aligned (octahedral) |
| Ca (1CLL) | 6–7 | **3** | all O | aligned (octahedral) |
| Fe-S₄ (5RXN) | 4 | 0 | 4S | non-aligned (tetrahedral) |
| Cu (1PLC) | 3 | 0 | 2N, S | non-aligned (planar) |
| Zn (8TLN) | 4 | 0 | 2N, 2O | non-aligned (tetrahedral) |
| Mg (3PGK) | 3 | 0 | all O | non-aligned (planar) |

The octahedral centers are **fully trans-paired** — every coordinating point has a partner straight across the metal, exactly "a point on one side requires one on the other." The low-coordination centers are flat **planar clusters** — three or four points defining a plane with no partner across, which is the "lines that fill a pixel" picture. So the aligned-vs-non-aligned split exists.

## Result 2 — but "aligned = N/S" is REFUTED; alignment tracks GEOMETRY, not donor identity
The two aligned centers are **heme Fe (nitrogen donors) and Ca (all-oxygen donors)** — one soft, one hard. So alignment cannot be the N/S signature. What it actually tracks is **coordination geometry** — octahedral (6-coordinate, centrosymmetric, trans-paired) vs tetrahedral/trigonal (3–4, no partner across) — which is set by the metal's size and d-electron count, not by whether the donors are soft or hard. The dichotomy is a geometry class, not an element class.

## Note — heme's pixel-plane + axial pair is real but geometry-degenerate
Chemically a heme *is* a 4-nitrogen porphyrin **pixel plane** plus an **axial pair** (proximal His + distal ligand) straddling the iron — precisely aligned-axis + non-aligned-plane in one center. But blind geometry cannot extract it from coordinates: an octahedron has **three equivalent planes**, and nothing in the point cloud marks the porphyrin as the special one. That decomposition needs the ring's chemical identity, not just positions.

## Honest ledger
**CONFIRMED** — points defining a center come in pairs; aligned (trans-paired, octahedral) vs non-aligned (planar cluster) is a genuine dichotomy.
**REFUTED** — "aligned = N/S": the aligned set is heme-N *and* Ca-O; alignment tracks octahedral-vs-tetrahedral geometry (coordination number / metal identity), not donor softness.
**REAL BUT UNEXTRACTABLE** — heme's porphyrin-pixel + axial-pair needs chemical identity, not blind geometry.

*Artifacts: `coord_alignment.py`, `coord_alignment.png`. Centers: 1MBN, 5RXN, 1PLC, 1CLL, 8TLN, 3PGK.*
