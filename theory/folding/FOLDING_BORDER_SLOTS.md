# Border Slots — the paths land on windows, but the coarse outline is orientation-free

*Companion to `FOLDING_OUTLINE.md`, `FOLDING_WINDOW_SEAM.md`, `FOLDING_SLOTS.md`, `FOLDING_ADAPTIVE_SIZE.md`. Jonathan: the paths point to slots on the border; the border residues have windows too; with 4 window positions, do we have to check all those orientations? Tested; `slots_border.py`.*

## The paths land on border windows — but the windows are only weakly distinctive
Border (|f|<0.20) vs interior Ramachandran-basin distribution: the border **leans helix, away from β** (TV-distance ≤ 0.22) but weakly and inconsistently (4AKE flat). Matches the seam being a **committed** stretch (a hinge helix, not a floppy loop) — but it does **not locate** the seam (helix is everywhere). The wall: the slots exist on the border; they are not a distinctive lock the paths uniquely key into.

## The 4 orientations — NOT needed for the coarse outline
The coarse seam is the **fundamental mode of the whole contact web** (`FOLDING_OUTLINE.md`) — computed from which residues touch which, not from any residue's φ/ψ — so it is **orientation-independent**. The top of the stack carries zero orientation combinatorics; the 4 orientations only matter *down* the stack, for the fine slot each residue sits in (exactly the fine detail that didn't survive cheap prediction, `FOLDING_WRAP_FULL.md`). Reachability: never enumerate every residue's 4 orientations to find the seam — read the coarse **group** (which side of the outline) from the global mode and stop; pay the orientation price only when the fine slot is actually needed.

*Artifacts: `slots_border.py`. 2LZM, 4AKE, 1GD1, 8TLN.*
