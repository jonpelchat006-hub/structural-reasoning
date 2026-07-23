# Onto the pLM — the observers ARE the attention heads (closing the compatibility gap)

*Companion to `FOLDING_OBSERVERS.md`, `FOLDING_CLIMB_WALL.md`, `FOLDING_ADAPTIVE_SIZE.md`. Jonathan's point: we *pasted* the pLM on rather than integrating; the task is to get the ideas *onto* the pLM. Tested whether his core construct already lives in ESM's internals; `onto_plm.py`.*

## Observers = attention heads (CONFIRMED)
ESM-2 35M has 12 layers × 20 heads = **240 attention maps**. Treating each head as an observer (Fiedler-partition its attention vs the true seam): **no single head is the truth** (range 50% chance → 95% excellent — each sees a partial shadow); **the committee recovers it** — a *blind* average of all 240 heads gives 89–94%, and ESM's trained contact head is a *learned* version of the same committee (agreement across observers = the invariant). Crucially, **the seam is in the ATTENTION, not the embeddings** — clustering per-residue embeddings recovers the split only at 52–62% (near chance). The nonlocal web lives in the *relational* attention, not any per-residue quantity — the framework's own thesis, restated by the model.

## The bridge (how the ideas get onto the pLM)
Connect concepts to mechanism, not output to output: **observers ↔ attention heads**, agreement-is-the-invariant ↔ head consensus, the global web ↔ the attention itself, local windows ↔ per-residue embeddings. Lined up this way the framework is a **reading of what the pLM already computes**, not a paste. Free next step: ESM's 12 layers may be the recursion depth (C1, C2, C3…) / the multiresolution scales — test whether coarse structure emerges at some layers and finer at others. Honest bounds: shown for the seam (coarse), three proteins, one small model.

*Artifacts: `onto_plm.py`. ESM-2 35M; 2LZM, 4AKE, 1GD1.*
