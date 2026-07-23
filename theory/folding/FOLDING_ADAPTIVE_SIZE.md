# Adaptive Sizing — the seam needs a tiny model and few (but spread-out) paths

*Companion to `FOLDING_CLIMB_WALL.md`, `FOLDING_OBSERVERS.md`, `FOLDING_RECURSIVE_C.md`. Jonathan: efficiency / lesser hardware is a goal — can we size the model, or make it adaptive? Tested; `adaptive_size.py`.*

## The tiny model works, and you need very few paths (CONFIRMED)
ESM-2 **8M** (smallest, CPU) matches 35M on the coarse seam (2LZM 94%=94%; 1GD1 87% vs 89%). Minimal **contact budget** (fewest top predicted contacts still recovering the seam ≥85%): 2LZM **41 = 0.2×L**, 1GD1 **83 = 0.2×L** — a fifth of the sequence length, a tiny fraction of the L² map. The budget **adapts to complexity**: ~0.2×L for clean two-domain folds, ~2×L for the tangled three-domain ADK (4AKE, the honest hard case). The minimal path count *is* a working "size we need" estimator.

## Honest correction — count, not bounding area (the nonlocality shows up)
Jonathan's *geometric* half — "smallest circle over the paths" — **does not shrink**: the needed paths are few but **spread across the whole map**, because the seam by nature connects distant sequence regions. The right knob is the **NUMBER of confident long-range paths, not a compact region** — there is no compact region, because the seam's whole job is to reach across. Multi-agent: because the paths are few-but-spread, decompose by region (recursive bisection / committee) — many tiny models on sub-regions, combined by agreement. The structure that describes the protein also parallelizes the work.

*Artifacts: `adaptive_size.py`. ESM-2 8M vs 35M; 2LZM, 4AKE, 1GD1.*
