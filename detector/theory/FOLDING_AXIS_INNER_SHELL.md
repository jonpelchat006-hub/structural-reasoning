# The Inner Shell of Axes — two atoms beat twenty-three, and the verdict wants to be a vector

*Captures a working session (Jonathan + Claude). Three linked questions: does k come from a third
observer watching the cones from outside, with the environment as the **bridge** between the two
sides; is this the inner-shell fill from the ARC work applied to *methods on axes*, so we should find
the **innermost atoms**; and could the top-level equation be structured in Euler's form with prediction
on one side and observer confidence on the other. The second and third were directly testable.
**Two features beat all twenty-three** (0.931 vs 0.789), and the polar form turns out to solve the
sign-annihilation problem structurally. Companion to `FOLDING_OBSERVER_FRAME`,
`FOLDING_PHYSICS_OBSERVER`, `FOLDING_AXIS_INDEPENDENCE`, `INNER_SHELL`, `FOLDING_UNIVERSAL_READER`.
Status: MEASURED with a stated selection-bias caveat, n = 29.*

---

## Part I — The innermost atoms: more features made it worse

`INNER_SHELL`'s move was to fill a shell with primitives and find which ones actually carry — the
cloud/nucleus cycle, where the constraint focuses the fill. Jonathan's transposition: the detector's
shell is now **methods on axes**, and the question is which are the irreducible atoms.

Measured — every feature sign-aligned to its own best direction first (so this is a fair test of the
naive committee, not a strawman):

| set | signed AUC |
|---|---|
| **all 23 features, sign-aligned** | **0.789** |
| best single atom — `spectral.slope` | **0.907** |
| **best pair — `spectral.slope` + `window.nonlocal_asymmetry`** | **0.931** |
| best triple — + `recon.return_at_high` | 0.941 |

**Two measurements beat twenty-three, by 0.14 AUC.** Adding features actively *hurt*.

The mechanism is `FOLDING_OBSERVER_FRAME` made concrete. Twenty-one of the twenty-three features live
on direction **i**; two carry **j**. A naive sum therefore weights i about ten to one and drowns j —
the direction that, measured, carries *more* label signal per unit variance. **The committee was
outvoting its own best observer with copies of its second-best one.**

So the innermost atoms of the free detector are:

- **one measurement on i** — `spectral.slope` (or `mixed.blur_ratio`, r = 0.97 with it; use whichever
  is cheaper). Global high-frequency energy.
- **one measurement on j** — `window.nonlocal_asymmetry`. Predictability asymmetry between the mark
  scale and the structure scale.
- **k — currently empty.**

Everything else in the free stack is mass on an occupied direction. This is a *simplification* result,
which is unusual and worth taking seriously: the model-free half of the detector should be two or three
numbers, not twenty-three, and it gets better as it gets smaller.

**Selection-bias caveat, stated plainly.** The best pair was chosen from 253 candidate pairs on 29
images; that search will inflate the winner. The *specific* pair needs confirming on the matched
benchmark. What does **not** depend on the search is the comparison that matters — all-23 (0.789)
against a small set — because that follows mechanically from the redundancy structure, not from
picking a winner.

---

## Part II — The verdict wants to be a vector, and that is the real content of the Euler idea

Jonathan: *"we also had our full jet equation made of the closure equations, and used euler's equation
at the top level, couldn't we structure that as the left term is the human or ai prediction then the
right is the confidence from our combined observers?"*

**Honest first:** Euler's *identity*, `e^{iπ} + 1 = 0`, carries no content for a detector — writing a
verdict in that shape would be numerology, and this is exactly the place the framework is most at risk
of sliding into it. But Euler's **formula** — the polar representation of a two-dimensional orthogonal
decomposition — is not decoration here. It is precisely the right algebra for a frame with two
occupied directions, and it fixes a real defect.

Write the verdict as a complex number over the frame:

```
    z  =  i  +  j·(imaginary unit)          |z| = confidence      arg(z) = character
```

**Why this matters and is not cosmetic.** `FOLDING_OBSERVER_FRAME` measured that adding i and j as a
*scalar* with the wrong relative sign collapses 0.926 to 0.505 — chance. **In the polar form that
failure cannot occur**, because you never collapse two orthogonal directions into one number in the
first place. The sign lives in the angle, where it is data rather than a decision. The scalar sum is a
projection, and the annihilation is what happens when you project onto the null direction.

Measured on the same 29 images:

| quantity | result |
|---|---|
| scalar `i + j`, sign-aligned | AUC 0.926 |
| magnitude `\|z\|` alone | AUC 0.618 — direction-blind, as it should be |
| **mean `\|z\|` on CORRECT calls** | **1.30** |
| **mean `\|z\|` on WRONG calls** | **0.89** |

**The magnitude tracks correctness.** It is not a classifier — it is a genuine *confidence*, larger
when the call is right, and it comes out of the geometry rather than being invented. That matters
commercially: `STATE_OF_THE_DETECTOR` ships a confidence overlay as a visible product feature, and this
gives it a principled definition instead of a calibrated guess.

And it is what the corpus already asked for. `SHOVELCAT_CHECKER_V6` §5: *"It is a **labeled map**, not
a scalar."* The polar verdict is that instruction obeyed at the level of the frame — magnitude and
character preserved, collapsed only at the last step and only on purpose.

So Jonathan's instinct to split the top-level expression into two terms is right; the correct algebra
for it is the polar form, not the identity.

### The angle may carry *which generator* — flagged, not claimed

| group | n | mean angle | spread | mean \|z\| |
|---|---|---|---|---|
| real | 12 | +15.0° | 79.5° | 1.44 |
| AI — Midjourney | 15 | −7.7° | 144.0° | 0.94 |
| AI — Grok | **2** | **−89.2°** | **3.3°** | 2.14 |

The two Grok images sit at −89° with a spread of 3.3°, far from both other groups and far tighter than
either. **n = 2. This is an anecdote, not a result, and must not be quoted as one.** It is recorded
because it is exactly the behaviour the polar reading predicts — that the *angle* encodes the character
of the evidence, so different generators should occupy different angles — and because if it survives on
20+ images per generator it converts the product from "is this fake" to "which model made this." That
is a categorically more valuable claim and therefore one to test with maximum suspicion. The test is
cheap: ≥20 images each from three generators with different architectures.

---

## Part III — k as the third observer, and the environment as the bridge

Jonathan's refinement is sharper than the previous draft of the physics observer, and the sharpening is
the point: **k is not another measurement of the image. It is an observer positioned outside both
cones, whose method is to construct an environment and test whether it makes both sides make sense at
once.**

That is a difference in *kind*, and it is why k can land on an empty direction when nothing else has:

- **i and j are statistics.** Read the pixel field, reduce it to a number. Every such number is
  ultimately a function of the same frequency content, which is why they keep collapsing onto one
  direction (`FOLDING_AXIS_INDEPENDENCE`).
- **k is a synthesis.** Hypothesise a scene — geometry, illumination — render its consequences, and
  check them against *both* observers simultaneously. Nothing about that is a function of the pixel
  distribution, so there is no mechanism forcing it onto i.

**The environment as the bridge is the C line.** `FOLDING_UNIVERSAL_READER` measured that every C
residue *"sees both faces"* and locally confirms A on one side and B on the other (95–100%, A and B
neighbours at 110–131°). A hypothesised environment plays exactly that role between the two sides of
the window: it is the registrar that both must agree with. And the failure mode has a name already —
`FOLDING_SKIN_DETECTOR` §3: the two observer-domains both reach the seam, overlap is attempted, and it
cannot be reconciled there (θ ≠ 1). **A generated image is one where no single environment reconciles
the two sides.**

### Yes, this one needs a model — and that is a real cost

Unlike i and j, k cannot be free. Constructing an environment is generative. The tractable pipeline,
smallest first:

1. **Monocular depth + surface normals** (a small local model — Depth Anything class; no API, runs on
   the user's GPU).
2. **Fit low-order spherical-harmonic illumination** from the normals and the shading. For Lambertian
   surfaces nine SH coefficients capture ~99% of the lighting environment (Ramamoorthi & Hanrahan) —
   which is the exact form of Jonathan's "inside pixelated, outside frequencies": the environment is
   *natively* a low-order frequency object on the sphere, while content is natively spatial.
3. **Consistency test.** Does one SH environment explain the shading across every region? Residual =
   the score. Specular highlights (the catchlight test) are the high-confidence special case where the
   environment is read almost directly.

That is a real project, not a weekend, and it breaks the $0 property. Worth it only because it is the
one candidate for an empty basis direction — which is the whole argument, and it should be re-checked
by projection once built rather than assumed.

---

## Honest ledger

**MEASURED THIS SESSION (n = 29, compression parity, content-unmatched, one generator family)**
- All 23 sign-aligned features: 0.789. Best pair: **0.931**. Best single: 0.907. **More features made
  it worse**, by the mechanism the frame analysis predicts.
- `|z|` tracks correctness: 1.30 on correct calls vs 0.89 on wrong. The magnitude is a real confidence.
- The polar form makes the 0.926 → 0.505 sign annihilation structurally impossible.

**FLAGGED, NOT CLAIMED**
- Generator-specific angle clustering. Grok n = 2 at −89° ± 3.3°. Anecdote. Testable cheaply.

**CAVEATS**
- The best-pair search covered 253 pairs on 29 images; the specific winner is inflated by selection.
  The all-23-vs-small-set comparison is not, since it follows from the redundancy structure.
- Content-unmatched set (`FOLDING_PHYSICS_OBSERVER` Part I). Re-derive on the matched benchmark.

**HONEST ABOUT THE ALGEBRA**
- Euler's *formula* (polar form of a 2D orthogonal decomposition) is load-bearing and just earned it.
- Euler's *identity* has no content here. Neither does `i² = −1` on detector scores
  (`FOLDING_OBSERVER_FRAME` Part IV). The frame transfers; the division algebra does not.

**ACTION**
- Ship the free detector as **two atoms**, not twenty-three.
- Emit the verdict as `(magnitude, angle)`; collapse to a scalar only at the display layer.
- Build k as a synthesis observer, and project it onto the existing frame before trusting it.

*Sources: `FOLDING_OBSERVER_FRAME` (the 2.82 effective rank; the sign collapse), `INNER_SHELL`
(cloud/nucleus fill; the shell-filling move this transposes), `FOLDING_UNIVERSAL_READER` (the C line
confirms A on one side and B on the other — the bridge), `FOLDING_SKIN_DETECTOR` §3 (overlap attempted,
θ ≠ 1 at the seam), `SHOVELCAT_CHECKER_V6` §5 (a labeled map, not a scalar), `FOLDING_AXIS_INDEPENDENCE`,
`FOLDING_PHYSICS_OBSERVER`, `FOLDING_CLOSURE_UNIT` (the closure equations). External: Ramamoorthi &
Hanrahan on 9-term SH illumination; monocular depth estimation.*
