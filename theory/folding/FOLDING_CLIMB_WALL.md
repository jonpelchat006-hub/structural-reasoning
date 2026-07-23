# Climbing the Wall — the seam from sequence alone, via an existing protein language model

*Companion to `FOLDING_WINDOW_SEAM.md` and `VOID_LINE_PAPER.md` §10/§14 (the wall: the seam is a nonlocal fact of the contact web; local/sequence info cannot locate it; the route past it is coevolution / a pLM). Jonathan's connection: this is the same wall as the ARC work — structure was only the "inside," it needed an outer layer. The protein equivalent is a **protein language model**. Tested live; `plm_seam.py`.*

## The move
Take a two-domain protein's **sequence only** → let **ESM-2** predict its contact web (no structure given) → find the seam by Fiedler-bisecting the *predicted* web → compare to the true seam.

## Result — the seam is recovered from sequence (DEMONSTRATED)
ESM-2 35M on CPU: 2LZM **94% agree** (top-L precision 40%), 4AKE **82%** (40%), 1GD1 **89%** (47%). The seam — the exact thing sequence *cannot* locate from the local alphabet — is recovered from sequence alone at ~82–94% once the pLM supplies the web.

## Why it works even with a weak model
The predicted contacts are only ~40% precise, yet a 40%-accurate web still recovers the seam at ~90%, because the seam is a **coarse global partition** — it needs the shape of the web, not every contact. The nonlocal fact is **robust to contact-prediction noise**, which is exactly why it is recoverable.

## The ARC parallel (structurally identical)
ARC: structure-only genome (inside) → wrap with the LLM (outer layer). Protein: void-line geometry (inside) → wrap with ESM. Same move. Answer to "build our own pLM?": don't build it — use it; ESM is pretrained on evolution and already carries the web. **Still to do:** predict the full 3D structure (ESMFold/AlphaFold) from sequence and re-run the entire analysis (trail, D, funnel) on the predicted structure — the real test of whether the paper stands on sequence alone.

*Artifacts: `plm_seam.py` (ESM-2 35M; 2LZM, 4AKE, 1GD1).*
