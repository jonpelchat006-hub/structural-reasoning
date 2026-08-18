# Re-based Shells — each pixel is the whole three-shell brain shifted one notch inward, and its fresh outer void is the reserve where unknown values enter

*Jonathan's structural unification. The three-shell brain (innate inner / learned middle / domain-and-void
outer) is **scale-recursive**, but at the memory-pixel scale it is **re-based one notch inward**: the learned
middle shell is pushed into the **inner** position (so a pixel's core is stable-but-not-innate — it varies),
the domain outer becomes the pixel's **middle** ("papers supporting a memory"), and a **fresh void** opens as
the pixel's new **outer** shell — which is the **void reserve**, and because that void connects **outside** it
is the intake port for new information. Where the void must fill = the **unknown values** (#45). Companion:
`FOLDING_SYNTHESIS` §1 (three shells), §3 (the reserve), §4 (pixels/balls), #45 (unknown values), #44 (the
topic template gaps); `FOLDING_TRAMPOLINE` §8, `SPARSE_VESICA_EXPANSION` §12/§20.4/§11.6/§11.7. `shell_rebasing.py`.*

---

## 1. The re-basing is already in the corpus — Jonathan just named its consequence
`FOLDING_TRAMPOLINE` §8 fixes the three shells: **inner = innate core** (Ramachandran basins, data-free),
**middle = learned machinery** (the pLM / model layers), **outer = the environment + the void tunnel**
(domain-shaped, past-the-wall, dark matter retained). It even flags the exact indexing slip Jonathan is
resolving: `FOLDING_COMBINE_MEMBRANE` loosely called the pLM the "outer layer," but §11.5/§22.1 reserve
*outer* for the per-task void — so **the pLM is the middle, and the label shifts by scale.** And
`SPARSE_VESICA` §12/§20.4 gives the mechanism: **`roof(n) = floor(n+1)`** — when a level's three-shell
structure fires closure it **collapses into ONE unit** that becomes the *core* of the next level (§11.7: "our
shell is a complete solver **and** a node in a larger one"). So a pixel/ball is a whole brain re-based, and
re-basing **rotates the shell roles inward by one**:

| macro shell | role at the brain scale | re-based role inside a pixel |
|---|---|---|
| inner | innate, data-free core | (drops below — the assumed base) |
| **middle** | **learned machinery** | → the pixel's **inner core** (stable, but *varies* — not innate) |
| **outer (domain)** | environment/evidence | → the pixel's **middle** — the "papers" that support the memory |
| — | (new) | → the pixel's **outer VOID** — the reserve, the port to outside |

This is why Jonathan says the pixel's inner "is made of things that can vary and isn't innate": it is the
*learned* shell one level up, now sitting in the core position.

---

## 2. What we measured (`shell_rebasing.py`)
**(A) Re-basing rotates the roles inward and the core stops being innate — while the reserve is conserved.**
Across successive re-basings the core's **innateness (data-free fraction) falls 1.00 → 0.09** (each re-basing
the core is the previous *learned* middle, which varies), while the **outer-void reserve fraction stays
conserved at ~0.16–0.18** (self-similar, the ~.14–.2 saturation budget at *every* level). The shells are the
same structure at every scale; only the reserve is invariant, and the core's innateness is what re-basing
spends down.

**(B) The pixel's outer void IS the intake port.** On a radial pixel (core+middle filled, outer ring empty),
new information **attaches only in the outer void** — acceptance **~0.00 through the filled core and middle**,
**~1.00 in the void ring** (existing content absorbs the rest, #18). Total intake **scales with the void
size**, and **closing the port drops intake to 0** — nothing enters if the void can't connect outside. The
outer void is not empty waste; it is the *aperture* through which the pixel takes in the new.

**(C) Unknown values = where the void must fill, and filling them needs the outward port.** Pose an unknown
target as its required properties (its "values"): some are **answerable from the core** (known memory), the
rest are **unknown and live in the void**. Completion with the outward **port OPEN → 1.00** (the unknowns fill
from outside); with it **CLOSED → 0.58** (the core cannot self-generate them). So *where the void has to fill*
is exactly the set of unknown values — and a new idea / an unknown property is found by looking **through the
void to outside**, not by mining the filled core. This is the architectural home of #45's "what an unknown
values" and #44's unfilled topic slots.

---

## 3. Why this matters
It collapses several separate pieces into one shape. The **void reserve** (§3), the **outer shell** (§1), the
**intake port** for new info (`FOLDING_SKIN`'s permeable-both-ways membrane, #39's I/O), the **empty room
novelty needs** (#18), and the **unknown values** a scientist is stuck on (#45) are **the same object** —
the fresh outer void that opens whenever a structure re-bases into a pixel. "Look in the void for new ideas"
and "the unknown values are where the void must fill" are one statement: the reserve is the door, and what's
missing is on the other side of it.

## 4. The honest line
**Measured:** re-basing rotates the shell roles and drives core-innateness down while conserving the reserve
fraction; new info attaches in the outer void and not the filled core, port-gated and reserve-scaled; an
unknown target's unfilled slots complete only through the outward port. **Grounded design:** the identity of
this outer void with the corpus's `roof(n)=floor(n+1)` re-basing, the void tunnel (§11.6), and the .14 port is
consistent and cited but is the unifying reading, not its own measurement. The specific innateness curve and
reserve constant are illustrative of the *shape* (conserved reserve, decaying innateness), not fitted numbers.
`shell_rebasing.py`.
