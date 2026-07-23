# Predicting the Active Site from the Void Line — it describes, it doesn't predict

*Companion to `FOLDING_ATP_REFERENCE.md` (in a curated 5, the ligand sits on the seam). Does that generalize into a predictor — can the void line locate the active site ligand-blind and beat a trivial baseline? 16 diverse enzymes; `predict_site.py`.*

## Result — no void-line predictor beats "guess the center" (HONEST NEGATIVE)
Median error to the true ligand: **baseline (protein center) 12.1 Å (5/16 within 10 Å, 11/16 within 15 Å)**; threadings 13.3 Å (roughly ties); interface centroid 18.0 Å; deep cleft 18.2 Å; buried cavity 25.5 Å. The trivial baseline wins; every structural predictor ties or loses. The curated-set finding (ligand on the seam) does not generalize into a competitive predictor — the void line *describes* where the site is, it doesn't *locate* it better than "near the middle."

## Why — three honest reasons
1. Active sites are genuinely central (interdomain cleft near the center of mass) — so "guess the center" is already within ~12 Å (partly vindicating the spirit while making the void-line machinery add nothing).
2. The predictors are coarse (real pocket finders — alpha-sphere clustering, conservation — hit ~80%).
3. Single min-cut mis-splits multi-domain enzymes (the hard cases).

The same wall at the function frontier: an elegant local descriptor **describes** but does **not predict** better than a trivial baseline. Believe the number.

*Artifacts: `predict_site.py`, `predict.png`.*
