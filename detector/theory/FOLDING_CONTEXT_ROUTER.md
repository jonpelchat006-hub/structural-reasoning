# The Context Router — the orthogonal observer as a parameter-gate (extends SHOVELCAT_CHECKER_V6 §10)

*Refinement of the type/context axis (`SHOVELCAT_CHECKER_V6` §10.2–10.5) from a working session
(Jonathan + Claude). The context observer is not a passive label — it is an **active router** with
three jobs: it **raises** (sees the whole window from a thickened, elevated vantage), it **finds the
borders** (the grid relaxes onto the domain seams), and it **routes/gates** (activates the authenticity
checks that matter for the medium and **zeros the ones that don't**). Companion to `FOLDING_OBSERVERS`
(the spanning frame), `FOLDING_SKIN` (torus thickness; "zero everywhere else"), `FOLDING_FLOORS` (the
reference frame), `FOLDING_VOID_LINE_DRAW` (thickness by level; the wires). Status: BUILT into
`shovelcat_checker_v6.py` (two-pass committee); mechanism verified by self-test + live smoke test;
empirical benefit pending the full re-benchmark.*

---

## Job 1 — RAISE: thickness lifts the vantage (the torus)

The per-cell authenticity screen is flat — one plane, dissecting the image into the grid. Give the
**orthogonal** context observer *thickness* and it stops being a flat read and becomes a **tube with an
axis** — the torus of `FOLDING_SKIN` §3 (outer wrap + inner spiral). The thickness is the **corridor**
(stacked screens, `FOLDING_SKIN_DETECTOR` §4 — "the flat lens swept into a solid seam corridor"); the
**height is the hole/axis**, and climbing that axis is what **raises the point of view**. That raised
observer is `FOLDING_OBSERVERS`' "larger structure looking down" — it works *because* it is lifted above
the per-cell plane (`FOLDING_SHADOW`: a height is hidden from a single flat angle). Raised, it sees
**more of the window** — the whole-image gestalt and its surround, which no single cell can.

*In build terms:* the context observer reads the **whole image** (not cell-by-cell), and its "thickness"
is the stack of context sub-reads — type + palette + lighting — plus, later, the same read across the
zoom levels. That stack is exactly what lets it judge "what kind of thing is this."

## Job 2 — FIND THE BORDERS: the grid relaxes onto the domain seams

The common grid (the scaffold of thin void lines) is not the answer — the lines **migrate**: dissolve
where pixels stay coherent, concentrate where they don't (the tested dissolve criterion,
`FOLDING_PIXEL_TRANSMISSION`), until they land on the real **domain borders**. So the grid *extends out
to* the borders; after relaxation the grid **is** the seam map. The raised context observer (Job 1) sees
the whole layout, so it can **guide the lines to the borders** instead of leaving them on a fixed
lattice. Raised view finds the borders; the grid runs out to meet them. *(Grid-relaxation is the next
build layer; the current engine uses the fixed 8×8 grid.)*

## Job 3 — ROUTE / GATE: which wires fire, and which parameters to zero

From its raised vantage the context observer knows the layout, so it does not merely *label* — it
**routes**. It knows what to send down each wire: how much of a channel ("how much red"), at which level
("when"), composed with which others ("with what") — the full `cosθ·v^d` per line (magnitude, feature,
endpoint; `FOLDING_SKIN` §2). Sending that content **activates** the relevant checks, and the activation
is **sparse**: only the needed wires fire, **everything else is zeroed** ("zero everywhere else" — the
sparsity that keeps the framework small). So the context read is an **activation mask over the
authenticity checks**:

- **photo** → activate photographic_grain, lens_optics, lighting_physics, material_texture, … 
- **digital_painting** → **zero** photographic_grain, lens_optics, lighting_physics, material_texture;
  activate brushstroke, palette_intent, style_continuity, …
- **edge_coherence** stays active in **every** medium — the universal generative tell.

This is the precise cure for the §10.1 bias: the 16 false positives were the detector firing
*photo-parameters on art*. The router turns those off. And it is not only more accurate — it is
**cheaper**: zeroing irrelevant checks makes the detector **adaptively sparse per image** (resistance =
commitment; coast the void, `FOLDING_SKIN` §3.5). Type = the **reference frame** (the trace stored on
the shell, `FOLDING_FLOORS`); authenticity = the **residual within it** (the sinθ).

**Bonus detector (orthogonal, free):** where the observers **disagree on the type itself** (a "photo"
with painterly smears; a "render" with photographic noise), that is a **seam in the context plane** —
an independent AI tell, non-redundant because the axis is orthogonal (`SPHERE_GENERATOR` E.2). The
engine flags it as a TYPE-SEAM.

*One boundary:* the full "send red down the wire" — timed colour on rails — is the **generative**
direction (the drawing primitive, `FOLDING_VOID_LINE_DRAW`); the detector uses the same routing in the
**read** direction, as a gate deciding which checks fire. Same wires, one paints, one prunes.

---

## Build status (`shovelcat_checker_v6.py`)

The engine is now a **two-pass committee**:

1. **Context pass** — each observer reads the whole image → `type`; `combine_context` aggregates to a
   consensus type (+ `type_disagreement` → TYPE-SEAM), and `activation_mask(type)` yields the
   active/zeroed check sets.
2. **Conditioned authenticity pass** — the per-cell prompt is built from the type + mask
   (`build_auth_prompt`): "judge whether this is an authentic {type}, apply {active}, ignore {zeroed}".
3. **Convergence combine** (unchanged) — agreement = invariant, disagreement = seam. `ScanResult` now
   carries `image_type`, `type_confidence`, `type_disagreement`, `active_checks`, `zeroed_checks`.

**Verified:** self-test green (convergence engine + activation mask + type consensus/seam). Live smoke
test — a real artwork was correctly classified `digital_painting` (conf 0.79) and the router zeroed
`photographic_grain, lens_optics, lighting_physics, material_texture`, exactly the cues that were
mis-flagging art.

**Not yet shown (honest):** whether the mask *moves the benchmark* — on the one smoke image the verdict
stayed AI even after zeroing (n=1, a hard case). The full re-benchmark (same 50, ~2× the API cost of the
Level-0 run because of the second pass) is the test. Expect two complementary effects to measure
separately: (a) does zeroing **raise real-art scores** (better separation / AUC), and (b) the earlier
result already showed the **0.5 threshold is wrong** — so **per-type threshold calibration** (a separate
FAKE_TAU / verdict band per medium, set from the benchmark) is the other half of the fix, still to add.

*Sources: `FOLDING_OBSERVERS` (raised observer, spanning frame), `FOLDING_SKIN` §2/§3/§3.5 (torus
thickness; zero-everywhere-else; resistance = commitment), `FOLDING_SHADOW` (height hidden from one
angle), `FOLDING_FLOORS` (reference frame on the shell), `FOLDING_PIXEL_TRANSMISSION` (similar borders
dissolve), `SPHERE_GENERATOR` E.2 (orthogonal = certified non-redundant), `FOLDING_VOID_LINE_DRAW` (the
wires; thickness by level; generative direction), `SHOVELCAT_CHECKER_V6` §10 (the type axis).
Code: `shovelcat_checker_v6.py`.*
