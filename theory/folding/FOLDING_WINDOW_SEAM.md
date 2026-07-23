# Window → Seam — can the seam be read from the window alphabet?

*Companion to `FOLDING_SLOTS.md`, `RIP_TEST_RESULTS.md`. Jonathan's idea: the windows (Ramachandran slots) each have unique traits; trace a sequence back to its window string, and maybe the **seam** — invisible in raw sequence — becomes visible in the window alphabet. Tested on 6 contiguous two-domain proteins; `harness.py`, `eval*.py`.*

## Two rungs
Ceiling rung: use TRUE window states (off structure) — does the seam show up at all? Real rung: use PREDICTED windows (from sequence). Ground truth = the min-cut seam; metric = percentile rank of the true seam among decoys (0.5 ≈ chance).

## Results
- **Result 1 — sequence → window WORKS (CONFIRMED):** per-residue window prediction, leave-one-protein-out, **chance 0.33 → 0.54–0.59**. The forward half is real; windows have sequence-readable traits.
- **Result 2 — window → seam FAILS, even with TRUE windows (CONFIRMED, bounds the idea):** the seam is not a distinctive position in the window string. Every local descriptor (coil fraction 0.16, regular-SS valley 0.14, change-point 0.22, wiggle 0.30, entropy 0.18, diversity 0.15) is **at or below chance** — the seam is if anything a *low*-coil, committed stretch, not a loose linker. Eight independent local readouts, none detects the seam. Calmodulin's "hinge" is a long α-helix, not a coil.

## The wall, one notch sharper
`sequence → window` (local, knowable, ~0.57) ✓; `window → seam` (needs the web) ✗ — invisible even with perfect windows. The seam carries **no local backbone signature** — it is a pure fact of the global contact web, and a per-residue local label is blind to the web by construction. The honest way past is T1′: feed a *predicted contact web* (coevolution/pLM) into the ripper — climbing the wall, not going around it via windows.

*Artifacts: `harness.py`, `eval2/3/4.py`, `window_seam.png`.*
