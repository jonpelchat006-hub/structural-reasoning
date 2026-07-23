# Solvent Supply — water is O(A) + H(B): the amphoteric universal filler that supplies both terms

*Companion to `FOLDING_DEFICIT_SITE.md`, `FOLDING_CHANNELS.md`, `RIP_TEST_RESULTS.md`. Jonathan's idea: H supplies B, O supplies A; water is O + 2H, so water supplies both. Tested on the water-containing canonical structures; `water_supply.py`.*

## The mapping
From the deficit algebra: **B = a donor** (an H to give) → fills an unsatisfied acceptor; **A = an acceptor** (a lone pair) → fills an unsatisfied donor. Water carries **O (A/acceptor)** and **H (B/donor)**, so it should complete *both* kinds of deficit. Heavy-atom proxy: protein N = donor, protein O = acceptor; a polar atom is a deficit with no protein N/O partner within 3.5 Å; a crystallographic water O within 3.5 Å satisfies it.

## Result — water supplies BOTH A and B (CONFIRMED)
Across seven water-bearing structures, waters reach **48%** of unsatisfied **acceptors** (water's H donating — supplies B) and **33%** of unsatisfied **donors** (water's O accepting — supplies A). Both substantial, both directions. Water is the amphoteric universal filler exactly as O(A) + H(B).

## What did NOT show up — the single bridging water
**Zero** waters bridge two *deficits* at once. Deficits are sparse and scattered, so two hungry sites rarely land on one water. Water supplies both terms across the population, not usually through one bridging molecule.

## Honest ledger
**CONFIRMED** — water fills both deficit types (acceptors 48% via H/B; donors 33% via O/A).
**NEGATIVE** — no single water bridges two deficits at once.
**CAVEAT** — heavy-atom proxy (N=donor, O=acceptor) is rough for both-ways groups; no explicit hydrogens; deficit counts small (6–61 per protein).

*Artifacts: `water_supply.py`/`.png`. Set: 1CLL, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM (3PGK has ~no waters).*
