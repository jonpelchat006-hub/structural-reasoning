# The Trust Gate — a memory upgrade must pass a functional regression test; stitch the gaps; the folded ball's trust is what it's made of

*Jonathan closed the loop on #42's "upgrade only what you trust" by connecting it to the trust/truth-detector
work in the economy corpus, and by making trust **functional**, **per-lens**, and **material**. The chain:
we already had a trust system (a truth detector in `Shovelcat_29`'s economy); the orthogonal lenses (#38)
each value different things for trust, and since a lens "switches off branches it sees," it changes **what
kind of trust it wants**; a new memory must be **tested for her own usage** — can it do what the old one did
**plus** more?; a similar-but-higher memory with **gaps** can be **stitched** to the old to cover the union;
and the **folding balls** (#30) are the operator that combines these memory layers — so **the trust is related
to what the ball is made of**. Companion: `FOLDING_SYNTHESIS` §4 (#41/#42, the memory-upgrade line), #38 (the
lenses), #30 (the ball), `Shovelcat_29` (the trust–economy), `FOLDING_OUTER_SLOT` (combine-by-dissipation),
`FOLDING_MATCHING_SLOT` (the seam/union), §18.19 (convergence-of-routes = agreement). `trust_stitch.py`.*

---

## 1. It is the trust system we already built
`Shovelcat_29` builds trust as a **field**, not a scalar: a reputation field **R(x,t)**, trust spreading as
**Air diffusion** (`D∇²R`), influence **reputation-weighted** by cumulative contribution, and — the key line
for us — **"Void = bandwidth for verification"** (§5.7: when the Void collapses there is *no bandwidth to
verify*, and misinformation wins). So verification is paid from the **.14 Void reserve**, exactly the reserve
that gates everything else (#33's conditions, #42's upgrade gate). The truth detector is the same machine as
#24 (verify a truth through a narrow gate) and the corpus's **convergence test** (§18.19: an answer is trusted
when independent routes converge to it, distinct-route count → 1, θ=1). #42 said *upgrade only what you trust*;
this says **what trust is** — functional, per-lens, and material.

---

## 2. The real gate is a FUNCTIONAL regression test (MEASURED)
#42's gate was a *confidence/similarity* gate. Jonathan's sharper version: **test the new memory for her own
usage — can it do everything the old one did, plus more?** That is a **regression test**, and it is stricter
and more honest than "is the new one better on average." Measured over a stream of 40 upgrade candidates, each
with a higher *mean* quality but silently **dropping a base skill or two** (the gaps) while adding new ones:

| policy | capabilities covered (end) | capabilities silently LOST (regressions) |
|---|---|---|
| naive — replace if higher **mean** score | 9 | **7** |
| regression gate — accept only if ≥ old on every covered cap **and** adds a new one | 7 | **0** |
| **stitch** — fold per-capability best (union) | **12** | **0** |

"Replace if higher average" is how upgrades **silently regress** — it trades away skills the old memory had for
a better headline number (**7 capabilities lost**). The regression gate never regresses but is *conservative*
(it rejects every gappy candidate, so it grows slowly, coverage 7). The fix that both keeps everything **and**
absorbs every gain is to **stitch** — and that is the next section.

---

## 3. Stitch the gaps — a gappy-but-strong memory + the old covers the union (MEASURED)
Jonathan: *"if we do have a similar memory that scores higher but still has gaps we could stitch them together."*
A candidate with **higher mean quality (0.58 vs old 0.49)** that nonetheless **misses base skills** *fails the
regression gate alone*. But stitched with the old — take the per-capability best — it covers the **union**:

- coverage: **old 7 · gappy candidate 8 · STITCH 11** — the stitch strictly dominates either memory.

This is the corpus's **combine-by-dissipation** (`FOLDING_OUTER_SLOT`): compatible layers **dissipate and
merge** (the candidate's real gains fold in), and it is the **seam-rebuild / matching-slot union**
(`FOLDING_MATCHING_SLOT`: each face answers the other's gap). So the answer to "upgrade or keep?" is usually
**neither — stitch**: keep the old's coverage as a floor and graft the new memory's gains on top.

---

## 4. The ball folds the layers — and its trust IS what it's made of (MEASURED)
Jonathan: *"the balls from before were folding something — wouldn't they be folding these memory layers and
combine them? and the trust could be related to what that ball is made of?"* Yes, literally. The **ball** (#30,
the fold/combine operator) folds memory **layers** into one; **"what it's made of"** is the **provenance** of
each capability (which layer supplied it); and a **lens trusts the ball in proportion to how much of it — on the
capabilities that lens values — is made of layers that lens trusts** (its truth detector accepts that source).
With 4 lenses, each valuing a different capability subset and trusting a different set of source layers:

- a ball folded from **one layer** is trusted only by the lens whose provenance it carries — trust by lens
  **L0 0.00 · L1 0.67 · L2 1.00 · L3 0.00** (uneven, blind outside its one source);
- a ball folded from **diverse trusted layers** is trusted by **all** — **L0 1.00 · L1 1.00 · L2 1.00 ·
  L3 1.00**. Diversity of trusted material *is* breadth of trust.

This is **convergence-of-routes = agreement** (§18.19) read as memory: a ball made of many independently-trusted
layers is the double-stranded, trusted answer; a ball made of one is a single unverified strand.

**Lenses switch branches → they change what trust they want (MEASURED).** Because a lens "switches off branches
it sees," it **re-weights** which capabilities it values. The *same* diverse ball, read by lens 0 before vs
after it switches branch: trust **1.00 → 0.00** — the material didn't change, but the lens now values
capabilities whose provenance it doesn't trust. Trust is a **relation between the ball's material and the lens's
current branch**, not a property of the ball alone. *(The 1.00→0.00 is an illustrative extreme; the measured
point is that re-weighting the lens moves its trust in a fixed ball.)*

---

## 5. The honest line
**Measured:** the functional regression test catches silent skill-loss that a mean-score gate misses (7 vs 0
regressions); stitching a gappy-but-strong memory covers the union (11 vs 7/8); a ball folded from diverse
trusted layers is trusted across all lenses while a one-layer ball is trusted by one; and re-weighting a lens
(a branch switch) changes its trust in a fixed ball. **Illustrative:** the specific capabilities, lens weights,
and trusted-provenance sets are a constructed scenario — the *mechanism* is measured, the moral/semantic content
is a stand-in. **Grounded design:** the identification of this trust with `Shovelcat_29`'s reputation field and
the §18.19 convergence test, and of the ball with #30's fold operator, is consistent and cited but is the
unifying reading, not its own measurement.

The upgrade rule the architecture now carries: **don't replace — regression-test, then stitch; and trust a
memory by what it's made of, through the lens that's currently looking.** `trust_stitch.py`.
