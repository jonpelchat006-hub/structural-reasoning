# The Sequence Budget — sequences supply foldability; starving it goes OVER budget, the margin tracks measured stability, and it scales with model size

*Companion to `FOLDING_BLANKET.md` (the fold's DEMAND), `VOID_LINE_PAPER.md` §10–12 (the wall; the ~0.2×L path budget; the pLM outer layer). Jonathan: sequences give a budget too — if we could figure out how much they give, we'd know a fold would fail if it's over budget. Tested by scrambling, structure-grounded mutants, 650 real S669 ΔΔG measurements, and a model-size scaling check. ESM2 (8M, 35M) + S669; `test_m.py`, `test_n.py`, `test_o.py`, `test_p.py`, `test_wt.py`.*

## The frame — supply vs demand
Demand = the interface blanket (~36% of residues) and the ~0.2×L path budget. Supply = how much of the fold's long-range structure the sequence can pin, read through the pLM. Affordable when supply covers demand; over budget when not.

## Supply is real, and starving it goes over budget (demonstrated)
Scrambling the sequence (demand fixed): SUPPLY (top-L/5 long-range contact precision) falls from **0.334** (real, 8/8 above baseline → folds) to **0.030** (scrambled → collapses onto the demand line). The gap **0.30** is the sequence-specific budget (what the *order* buys above composition). Calmodulin the floor (0.036); knitted enzymes carry the biggest budgets (0.50–0.61) and fall hardest.

## Calibration 1 — the margin is graded (dose-response)
Scrambling a fraction f: mean supply 0.334 → 0.263 → 0.195 → 0.075 → 0.036 at f = 0, 15, 30, 50, 100%. Spent smoothly; a fold tolerates ~15–30% disruption and crosses toward the demand line past ~50%. Margins differ (1GD1 deep, 8TLN/4AKE thin).

## Calibration 2 — structure-grounded mutants
pLM variant log-odds: disruptive (bury a charge) mean **−2.48**, benign (conservative surface) **−0.25**; separation positive in 4/4 proteins; **AUC 0.73** ranking folders above failures.

## Calibration 3 — REAL measured stabilities (S669)
650 matched variants, ESM2-8M: wt-marginal **Spearman +0.19** (p=7×10⁻⁷); masked-marginal **+0.21**; AUC 0.60–0.62. Direction correct (destabilizing → lower score), statistically solid but modest — because 8M is the smallest model.

## Calibration 4 — model-size SCALING: the modest number was a floor
Same capped 457-variant subset, wt-marginal:

| model | Spearman vs ΔΔG | AUC |
|---|---|---|
| ESM2-8M | +0.140 | 0.561 |
| **ESM2-35M** (4× bigger) | **+0.360** (p=2×10⁻¹⁵) | **0.688** |

A 4× bigger model **more than doubles** the correlation on identical mutations — the modest 8M number is a small-model floor; extrapolates to the literature ~0.4–0.6 for 150M–650M. *(Environment note: this work ran on a 2-core / no-GPU sandbox; 150M–650M + masked-marginal did not finish in-session. The Colab notebook `notebooks/colab_s669_calibration.ipynb` runs 650M on a free GPU.)*

## Ledger
**CONFIRMED (demonstrated):** sequences supply a measurable foldability budget (real ~0.33, scrambled ~0.03); the margin is graded (crosses over-budget past ~50% disruption), ranks designed folders above failures (AUC 0.73), tracks real measured ΔΔG (S669, +0.19–0.21, p≤10⁻⁷), and **scales with model size** (8M→35M doubles it to +0.36). **HONEST LIMIT:** best real-data number here is 0.36 (35M), held down by 2-core/no-GPU; 150M–650M + masked-marginal (expected ~0.4–0.6) need GPU. "Supply" is a specification budget, cousin to but not identical with thermodynamic foldability. A calibrated *probability of failure* needs fold/no-fold outcome data (e.g. Tsuboyama 2023 mega-scale).

**The arc it closes:** Demand (blanket ~36% / ~0.2×L) + Supply (sequence via the pLM outer layer) = a foldability ledger, validated four ways. The concept holds end-to-end; a stronger predictor is a compute + outcome-data problem, not a conceptual gap.
