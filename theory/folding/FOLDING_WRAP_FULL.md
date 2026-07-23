# Wrapping the Full Structure — the seam survives on sequence, the fine geometry doesn't (cheaply)

*Companion to `FOLDING_CLIMB_WALL.md`, `FOLDING_ADAPTIVE_SIZE.md`, `VOID_LINE_PAPER.md` §11/§15.1. The next-step test: predict structure from sequence and re-run the WHOLE geometry (seam, trail, D). Hardware here: 7.8 GB RAM, 2 CPU — ESMFold/AlphaFold out of reach. Two cheap routes; `wrap_full.py`, `wrap_graph.py`.*

## Result (graph-native, the honest test)
Route 1 (reconstruct 3D from ESM contacts via MDS) **failed** — Cα-RMSD 28–204 Å, not a fold. Route 2 (run graph-native on the ESM-predicted contact web): **the seam survives (82–94%)** — reconfirms the wall-climb; a coarse global bipartition tolerates ~40%-accurate contacts. But **the fine geometry does NOT survive** — per-residue trail identity and the convergence point D show ~zero correlation between predicted and true webs (|r| ≤ 0.14); the connected-trail property fragments (45–60%) on two of three.

## Interpretation — no free lunch at the bottom of the recursion
Coarse features (the seam) are cheap and robust to noise; fine features (trail, D, funnel) need an **accurate** structure (AlphaFold/ESMFold level → GPU / >16 GB). This tightens the efficiency thesis: **capacity scales with feature granularity** (the seam is ~0.2×L paths and an 8M model; the trail and D demand real accuracy — the path budget predicted this). Status of §15.1: now a result, not a promise — the coarse layer wraps from sequence cheaply; the fine layer awaits a high-accuracy folding model on better hardware. Prediction (untested): on a real ~1–2 Å ESMFold/AlphaFold structure the fine geometry *will* survive — the experiment that would let the whole paper stand on sequence alone.

*Artifacts: `wrap_full.py`, `wrap_graph.py`. ESM-2 35M; 2LZM, 4AKE, 1GD1.*
