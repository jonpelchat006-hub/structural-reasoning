# Metal Wells — metals aren't repelled to the edge; they're seized into wells, and the MAGNETIC ones are a distinct soft-donor class

*Companion to `FOLDING_DEFICIT_SITE.md`, `FOLDING_CHANNELS.md`, `FOLDING_TWO_WALLS.md` (life rejects the rock-forming metals). Jonathan's two ideas: (1) maybe metals are **repelled away** rather than sealed-in fillers; (2) **metals are the magnetic stuff inside**. Tested on the metal ions in the canonical set plus dedicated Fe/Cu metalloproteins; `metals_repelled.py`, `magnetic_metals.py`.*

## Result 1 — "repelled to the periphery" is REFUTED; metals are seized into wells (with one loose exception)
- The metals life builds with structurally — **4× Ca²⁺ in calmodulin, 4× Ca²⁺ + catalytic Zn²⁺ in thermolysin** — are **deeply buried** (exposure 0.00–0.22) and **heavily enveloped** (40–58 protein atoms within 6 Å). Clamped into the core, not held at arm's length.
- Only the two **Mg²⁺** ions (kinase nucleotide sites) look peripheral (exposure ~0.6, coordination **1**) — Mg²⁺ binding loosely while keeping its own water shell, not the scaffold repelling it.
- **The universal grip:** the coordination shell is **92% oxygen** across the hard cations — Ca/Zn sit in tight cages of 4–7 oxygens. The metal is **gripped by a precisely built oxygen well** — the negative well of `FOLDING_DEFICIT_SITE.md` made literal.

**Reconciliation with `FOLDING_TWO_WALLS.md`:** the compositional rejection of metals is real, but it is a **selection filter at the gate** (which metals, how many), *not* structural peripheralization. Repulsion at admission, seizure inside.

## Result 2 — the MAGNETIC metals are a distinct class: soft N/S wells, not hard-O wells
The diamagnetic closed-shell ions (Ca²⁺, Mg²⁺) sit in **hard-oxygen** wells (92% O). The paramagnetic transition metals (unpaired d-electrons → genuinely magnetic) sit in **soft N/S** wells:

| center | coord # | O | N | S | donor type | cage offset |
|---|---|---|---|---|---|---|
| heme Fe (1MBN) | 6 | 1 | 5 | 0 | **soft N** | 0.16 Å |
| Fe-S₄ (5RXN) | 4 | 0 | 0 | 4 | **soft S** | 0.05 Å |
| blue-copper Cu (1PLC) | 3 | 0 | 2 | 1 | **soft N/S** | 0.41 Å |

Every magnetic center is held by soft donors, and each sits at the **exact focus of its cage** (offset 0.05–0.41 Å). So "metals are the magnetic stuff inside" resolves cleanly: the paramagnetic transition metals are the magnetic centers (the C/H/N/O scaffold is diamagnetic), a **structurally distinct class** — soft N/S wells at the geometric focus.

## Honest ledger
**REFUTED** — metals are not repelled to the periphery; the structural metals (Ca/Zn) are buried and seized into tight wells (only loose Mg is peripheral).
**CONFIRMED** — hard cations sit in ~92%-O wells; the magnetic transition metals (Fe, Cu) sit in soft N/S wells at the exact cage focus.
**CAVEAT** — magnetism itself is an electronic fact stated, not measured from coordinates; the test confirms the *structural corollary*. The Cu–Met bond (~2.9 Å) falls just outside the 2.6 Å cutoff.

*Artifacts: `metals_repelled.py`/`.png`, `magnetic_metals.py`/`.png`. Metals: Ca/Zn/Mg from 1CLL, 8TLN, 1PHP, 3PGK; magnetic centers 1MBN, 5RXN, 1PLC.*
