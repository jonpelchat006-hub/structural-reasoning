# The Saturation Budget — packing is PINNED (0.627 ± 0.014); a dense shell at the close-packing max, the void banked at the seam

*Companion to `FOLDING_THE_KNIFE.md`, `FOLDING_BLANKET.md` (demand ~0.36), `FOLDING_SEQUENCE_BUDGET.md` (supply ~0.30), `FOLDING_VORTEX.md`. Jonathan's idea: the system runs near **maximum saturation** but reserves a fixed void slack (~1/5) as **another kind of budget**; that reserve is where the fluid lives and where the vortex can still turn; if it saturates fully it locks. Tested on the canonical 8; `saturation_budget.py`.*

## Results
1. **Saturation is PINNED to a fixed value (CONFIRMED — headline):** whole-body packing = **0.627 ± 0.014** across all eight, from 1,130 to 10,100 atoms — every one within ~1% of the mean. A conserved quantity eight wildly different structures hold to is a **budget** — a third alongside demand (~0.36) and supply (~0.30). Trust the constancy over the absolute number.
2. **"Near maximum" is true in a SHELL, not globally (PARTIAL):** packing by depth — 0–1 Å:0.42, 1–2:**0.76**, 2–3:**0.73**, 3–4:0.62, deeper ~0.55. A dense shell 1–3 Å below the surface reaches the 0.740 close-packing max — but it's a shell, not the whole body (globally ~37% void, deep interior looser).
3. **The reserve is BANKED at the seam and cavities (reading):** the interior void pools into cavities and the **interdomain gap — the void line itself** (the ~27 Å depleted seam slab). Banked at the axle, where the vortex needs room to turn.
4. **The fluid does NOT occupy a distinct open reserve (NEGATIVE):** local packing at buried waters = **0.625**, dead-on the bulk 0.627. The waters fill ordinary-density cavities; no separate slack phase.

## Honest ledger
**CONFIRMED** — packing pinned to **0.627 ± 0.014** (real, conserved budget); a shell at 1–3 Å reaches the close-packing max 0.73–0.76.
**PARTIAL** — "near maximum" holds only in that shell; whole-body void ~0.37.
**READING** — the reserve is banked at the seam + cavities, not uniform slack.
**NEGATIVE** — buried waters at bulk density; no distinct loose fluid reserve.
**Caveat** — absolute packing is method-dependent; the **constancy** (±0.014) is the robust signal.

*Artifacts: `saturation_budget.py`/`.png`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
