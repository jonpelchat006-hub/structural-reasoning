# Channels — filling the void doesn't seal it; the fill stays porous so the void keeps flowing

*Companion to `FOLDING_DEFICIT_SITE.md`, `FOLDING_VOID_REACH.md`, `FOLDING_SATURATION_BUDGET.md`, `FOLDING_TWO_WALLS.md`. Jonathan's idea: the new stuff fills the void, but it must let the void **keep flowing** — there have to be **channels through it**; you close the pixel without poking into the void. Prediction: a bound ligand completes the deficit but does **not** seal the site. Tested on the ligand-bound structures; `channels.py`.*

## Method
Voxel model: obstacles = protein + ligand vdW. Exterior solvent = probe-accessible free space connected to the box boundary. A ligand atom is **exposed** if exterior solvent reaches its surface; **mouths** = connected components of exterior solvent touching the ligand.

## Result — the fill is POROUS, not a seal (CONFIRMED for substrates)
| site | ligand | exposed | mouths |
|---|---|---|---|
| 1AKE | AP5A | **11%** (89% buried) | **7** |
| 1PHP | ADP | 63% | 10 |
| 3PGK | ATP | 65% | 11 |

Every substrate stays perforated with solvent openings. The headline is **AP5A**: the ADK lid closed right over it (only 11% exposed) yet it keeps **7 separate channels** to solvent — exactly "close the pixel without poking into the void." The deficit is filled, the site sits on the reach corridor, and the fill is porous enough to keep that corridor conducting.

## The budget capstone — spend everything to zero EXCEPT the flow reserve
The open question ("lowest budget for all, or 0 remaining for all?") has an answer the data leans to, and it is neither:
- **Not Liebig's law of the minimum** — the budgets are *matched*, not one-bottlenecked: supply meets demand (≈0), packing pinned at the close-packing max, void held at ~1/5. That is **symmorphosis** — no excess capacity.
- **Not all-zero either** — spending the void/flow budget to zero would plug the channel; no reserve, no flow, the vortex locks.

So: **drive every budget to zero *against* one fixed, non-zero reserve — the flow/void budget.** The channels above are that reserve made visible: even the most deeply buried site (AP5A) refuses to consume its openings.

## Honest ledger
**CONFIRMED** — filling does not seal: substrate sites stay porous (7–11 mouths), the deeply buried AP5A (89% buried) keeps 7 channels.
**INCONCLUSIVE — the metal contrast.** Ca²⁺/Zn²⁺ are single atoms and the mouth metric isn't built for point ligands (Zn read "0 mouths" but 100% exposed — a threshold artifact). "Metals seal, substrates channel" is **not** established; only the substrate half stands.
**CAVEAT** — "mouths" proves porosity, not a clean in-one-side-out-the-other tunnel.

*Artifacts: `channels.py`/`.png`. Structures: 1AKE, 1PHP, 3PGK (substrates); 1CLL, 8TLN (metals — inconclusive).*
