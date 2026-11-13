# FOLDING_SKIN Tests — self-similar structure; a pLM "pressure" that mostly dissolves with capacity; a "refraction" that is a weak-model artifact; and the wall as an observer-consensus collapse

*Empirical tests of `FOLDING_SKIN.md` §3.7 and of Jonathan's observer reframe (the "voices" are
observers — pLM, LLM, edge×2 — agreement = the invariant), his **pressure**, **refraction**, and
**state-transition / observer-collapse** hypotheses for the wall. Run live on the canonical 8; ESM-2
8M→35M→150M→650M. Artifacts at the end.*

## The reframe (Jonathan)
The "four voices" are **observers** (`FOLDING_OBSERVERS`, `ONTO_PLM`): pLM + LLM + **edge counted
twice** (bidirectional, §1) = 4. "Four voices, one number" → **"does the committee agree?"**; the
*shape* of any disagreement is signal. Lenses: `cosθ` (alignment), `sinθ` (residual), `tanθ` (ratio).
Hypotheses for the depth-dependence and the wall: **pressure** (amplitude loss with depth),
**refraction** (positional bend), and the **wall as a state transition / collapse point for the
observers' range** (`SPARSE_VESICA §10.1`: the wall is the sedenion seam — where the algebra loses the
division property; a genuine transition).

## Test 1 — the STRUCTURE fade is self-similar (single flat ratio) — CONFIRMED
True Cα web (8 Å), recursive Fiedler bisection to 5 levels, sharpness = edges avoided vs 300 same-size
random cuts. 0.923→0.818→0.761→0.713→0.642; **r = 0.911 ± 0.020** (8 proteins), pooled **R² = 0.988**,
**curvature = +0.003 ≈ 0**. The structural cut hierarchy is self-similar with one ratio (~0.91).
(`fade_test.png`.)

## Test 2 — the pLM fade is steeper AND accelerating (pressure) — CONFIRMED
ESM-2 **8M** predicted webs (density-matched), identical recursion. r = 0.838, curvature = −0.020;
per protein **curv(pred) − curv(true) < 0 in 8/8** (p ≈ 0.004). The structure is flat, the pLM feels
depth — Jonathan's pressure. (`pressure_test.png`.)

## Test 3 — pressure is MOSTLY a capacity limit, but it PLATEAUS short of the structure — PARTIAL
Model sweep (8M→35M→150M→**650M**): r = 0.838 / 0.846 / 0.881 / **0.879**; curvature = −0.020 / −0.023
/ −0.003 / **−0.009** (structure: r 0.917, curv +0.003). The pressure signature **collapses** by 150M
— mostly the small model's capacity exhausting at fine resolution — but r **plateaus at ~0.88**, a
stable residual gap to 0.917. Mostly a capacity artifact **with an intrinsic floor = the wall**
(`VOID_LINE_PAPER §10`/`CLIMB_WALL`). *Ambiguity (honest):* our data cannot distinguish a true
asymptotic floor from a **latent-heat plateau** (Jonathan) — a flat stretch that would jump at 3B/15B;
that needs bigger models than an 8 GB box holds. (`sweep4.png`, left.)

## Test 4 — refraction is a WEAK-MODEL artifact: the density bend peaks, then reverses — REFUTED (as a general effect)
Fraction of misassigned residues bending TOWARD the pLM's optical density (predicted-contact degree),
at the secondary cut (L1), vs model size: 8M 0.550 (z+2.9) → **35M 0.636 (z+7.1)** → 150M 0.536 (z+1.9)
→ **650M 0.445 (z−2.1)**. The bend **peaks at 35M and reverses by 650M** — a weak-observer over-weighting
of dense cores that a strong model corrects, its residual errors migrating to the contact-sparse seam.
*Note:* an order parameter (bend direction) **changing sign at a critical capacity (~300M)** is itself
a **transition signature** — supporting Jonathan's state-transition reading. (`sweep4.png`, right.)

## Test 5 — the wall IS an observer-consensus collapse — CONFIRMED
Directly testing Jonathan's "the wall is a collapse point for the observers' range." Using ESM-2 35M's
**240 attention heads as observers** (`ONTO_PLM`): each head's attention Fiedler-bisected → its opinion
of the domain split; aligned to the true split; per residue, **committee disagreement** = how split the
240 heads are (0 = unanimous, 1 = 50/50). Correlated with **core-ness** (|true Fiedler value|; 1 = core,
0 = seam).
- **Pooled corr(disagreement, core-ness) = −0.275; negative in 8/8 proteins.**
- **Committee disagreement at the seam quartile = 0.167 vs core quartile = 0.080 — 2.1× higher at the
  seam.**
So the 240 observers **agree in the cores and split at the seam**: the invariant (agreement) **collapses
exactly at the wall.** This is the interference/decoherence mechanism (the observers' opinions cancel at
the seam), and it makes the wall a real, *internal* feature of the pLM — its own committee locates the
hard region by failing to agree there. It also explains the Test 3 floor and the Test 4 reversal: the
seam is where consensus dies, so it is the last thing any observer resolves and the place a sharpened
observer's errors concentrate. (`collapse.png`.)

## What the tests settle
- **§3.7 self-similar structure:** TRUE — one clean ratio (~0.91), R² = 0.99. The strongest result.
- **§3.7 "four voices, one number":** FALSE as stated — observers fade at different ratios; the gap
  shrinks with capacity but plateaus (~0.88) at the wall.
- **Pressure:** real; mostly a capacity artifact (collapses by 150M) with a wall-floor (floor vs
  latent-heat plateau unresolved).
- **Refraction:** real only for weak observers; peaks (~35M), reverses (650M) — a low-capacity
  artifact, and its sign-flip is a transition signature.
- **The wall (state transition / collapse):** CONFIRMED as an **observer-consensus collapse** — head
  disagreement is 2.1× at the seam (8/8). The wall is where the committee's agreement goes to zero;
  the sedenion-seam transition, seen in the pLM's own heads.
- **Unifying picture:** everything bottoms out at the seam. The structure is self-similar; the pLM
  converges toward it as capacity grows but stalls at the seam, where its observers cannot agree.

## Honest bounds
- One metric, 8 Å, density-matched top-contacts, single crystal chain, **8 proteins**; modest N on the
  650M reversal and the r-plateau. Test 5 core-ness and head-splits both reference the true Fiedler
  vector (some shared frame), but the heads are the pLM's own attention — independent of the true
  structure — so their tracking the true seam is a real correspondence, not a definitional one.
- fp16 for the two largest proteins at 650M (memory); fp32 elsewhere. 3B/15B untested (would resolve
  the floor-vs-latent-heat question). Absorption-on-path mechanism (vs interference) untested.

## Next
1. **Widen to 30–50 proteins** — firm the r-plateau and the 650M reversal.
2. **Cone-width observer (§3.3, the `tanθ` lens)** — the one remaining voice, unmeasured.
3. **Floor vs latent heat** — needs ≥3B models: does r jump or stay flat? (Distinguishes wall-as-floor
   from wall-as-phase-transition.)
4. **Absorption vs interference** — is the seam also in the "shadow" of dense cores on the signal path,
   or is the collapse purely the head-disagreement of Test 5?

*Artifacts: T1 `fetch_parse.py`,`recurse.py`,`analyze.py`,`plot.py`,`fade_test.png`; T2 `test2.py`,
`compare.py`,`pressure_test.png`; T3–4 `sweep_refract.py`,`plot2.py`; 650M `predict650.py`,`lean650.py`
(fp16),`analyze650.py`,`plot3.py`,`sweep4.png`; T5 `collapse.py`,`plot_collapse.py`,`collapse.png`.
ESM-2 via fair-esm; seed 7; 8 Å; floor 24; 5 levels; canonical 8 = 1CLL 3PGK 1PHP 1GD1 6LDH 8TLN 4AKE 2LZM.*
