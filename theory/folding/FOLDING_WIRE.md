# The Wire Budget — exactly enough wire, detours bulge out, and "is it the sequence?"

*Companion to `FOLDING_STRANDS.md`, `FOLDING_WINDOW_SEAM.md`, `FOLDING_CONSTRAINT_LADDER.md`. Jonathan: each strand has twists; we must use *exactly* the wire given; as we lay it down it wants to jump out, land in a substructure, and come back to the border — or is that the sequence? Tested on 12 enzymes, 168 loops; `wire.py`.*

## Results
1. **"Use exactly the wire given" (CONFIRMED, r=0.87):** wire GIVEN = contour length; wire NEEDED = span + out-and-back detour (2×excursion). contour vs (span+detour) **r = 0.87** over 168 loops; mean slack = **29 Å = the detour budget**. The chain length is metered to spanning its anchors plus its detour.
2. **But the detours bulge OUT, not toward ATP (HONEST NEGATIVE):** for excursion loops the tip is 17.4 Å from the ligand vs the anchor at 13.0 Å — farther; only 27% head toward ATP. The big detours bulge to the solvent surface; functional loops at the ligand are the *short* cleft loops. (The "organelle" version is real one level up — signal sequences send whole proteins to organelles, a different scale.)
3. **Is it the sequence? the split, again (the wall):** the **kind of wire** (coil vs regular per residue) is weakly in the sequence (58% vs 52% baseline); **where it jumps** (routing/detour depth from sequence) is **not** (r = −0.21 ≈ 0). The sequence tells you what each piece of wire is *like*, not where it *goes* — same split as window→seam.

*Artifacts: `wire.py`, `wire.png`.*
