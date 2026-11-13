# Frequency — the third budget: spin, path, and identity as return-to-origin

*Records the third of Jonathan's three budgets, worked out live (Aug 2026). Companion to `FOLDING_SUPERFUEL.md`
(the three budgets = void/matter/context; §1) and `FOLDING_MOVEMENT.md` (Test 9 the video/frames; Test 5
growth; Test 8 the return-path closure). Jonathan: "we had three budgets — the object is one (VOLUME), the
orientation is another, and there'd be one for PATTERNS / FREQUENCIES — like size / greasy / electric in the
protein work. Once you have a volume and an orientation you can see what SPIN it has, what PATH it follows.
The bottle spins in the water, its outline keeps changing, but as long as it goes back to the starting point
we know it's the same thing. Freq 1 is all the branches in the spot (just a frame); freq 2 has all of freq 1
inside plus more bands from the expansion — so expansion adds more states to the cycle while keeping the
origin as its return." Measured: `frequency_identity.py`.*

## 1. The three budgets are the three parts of a Fourier descriptor
A closed contour (the bottle's outline, traced once around) is a periodic loop `z(t)=Σ_k C_k e^{ikt}`,
`t∈[0,2π)`, with `z(t+2π)=z(t)` — it **returns to origin**. Its three natural parts are exactly Jonathan's
three budgets:

| budget | protein property | Fourier part | meaning |
|---|---|---|---|
| **VOLUME** | size | low-harmonic magnitude \|C_1\| | the object's overall extent |
| **ORIENTATION** | (the frame) | global phase (a spin ⇒ ×e^{iα} on every C_k) | which way it's turned |
| **FREQUENCY** | greasy / electric (the pattern) | the magnitude spectrum \|C_k\| over k | the spin/path signature |

So "once you have a volume and an orientation you can see the spin" is literal: fix the size (|C_1|) and the
phase (orientation), and what's left — the **spectrum of magnitudes** — *is* the frequency budget, the
pattern the shape makes as it goes around. (`FOLDING_SUPERFUEL` §1's void/matter/context and this
volume/orientation/frequency are two cuts of the same triad — one by charge, one by what a closed loop carries.)

## 2. Identity = return to origin (MEASURED)
"The bottle spins, its outline keeps changing, but as long as it goes back to the starting point it's the same
thing." A spin rotates the whole loop (global phase) and shifts where you started tracing (a phase per
harmonic) — the **momentary outline changes**, but the **magnitude spectrum |C_k| is invariant** to both, so
it *returns to origin*. Measured on a library of 6 objects, recognise-the-same-object accuracy:

| representation | no spin | SPINNING (random rotation + start) |
|---|---|---|
| **RAW outline** (phase-carrying sample points) | 1.00 | **0.18** (≈ chance) |
| **FREQUENCY magnitude** \|C_k\| (returns to origin) | 1.00 | **1.00** |

- Aligned, both work. Under spin, the **raw outline collapses to chance** (0.18 ≈ 1/6) — the phase-carrying
  representation reads a spun object as a *different* thing. The **frequency-magnitude signature holds at
  1.00** — it is invariant to the spin and to the trace start, so it recognises the same object through the
  rotation. **Identity is the closed cycle, not the momentary shape.** This is the same "return-to-origin"
  invariant as `FOLDING_MOVEMENT` Test 8's round-trip closure and the vesica identity θ→ln θ→e=θ
  (`Shovelcat_10_1`), now as the thing that makes a spinning object *one object*.

## 3. Expansion = adding frames to the cycle (MEASURED)
"Freq 1 = a frame; freq 2 = all of freq 1 inside plus more bands." Reconstructing the loop with harmonics
`|k| ≤ K` **nests**: each K contains the previous plus one new band. Mean reconstruction error over the 6
objects as the expansion grows:

| harmonics kept | \|k\|≤1 | ≤2 | ≤3 | ≤4 | ≤5 | ≤6 | ≤7 | ≤8 |
|---|---|---|---|---|---|---|---|---|
| error | 0.41 | 0.31 | 0.22 | 0.15 | 0.09 | 0.06 | 0.04 | **0.00** |

- **`|k|≤1` is a bare ellipse — the frame** (just the fundamental loop). Each higher harmonic **adds a band
  and nests the last inside it**, and the error falls monotonically to ~0. So **expansion = adding more states
  to the cycle** — the growth of `FOLDING_MOVEMENT` Test 5 (add a fiber on need), here adding a *frame to the
  cycle*, and the frame-across-time of Test 9 (the video), with the fundamental (the return point) preserved
  the whole way.
- **"Would we just stop at the next frequency?" — yes.** The object is band-limited (top real harmonic here is
  8); once the expansion reaches it the error hits zero and **plateaus** — there is nothing real above it, only
  noise, so you stop at the next frequency. The band limit is the object's intrinsic complexity; expansion
  past it adds no new states. `frequency_identity.png`.

## 4. Honest ledger
**MEASURED** — (2) rotation/start-invariant recognition: raw outline 0.18 under spin vs frequency-magnitude
1.00 (6 objects, 600 trials); (3) nested reconstruction error 0.41 (bare frame) → 0.00 at the band limit,
then plateau. `frequency_identity.py`, `frequency_identity.png`.

**GROUNDED / DESIGN** — the mapping "three budgets = the three parts of a Fourier descriptor
(size/orientation/spectrum)" and "greasy/electric = the frequency budget" is a clean identification of
Jonathan's picture with elliptic-Fourier / shape-descriptor math; it is consistent and the pieces are
standard, but the identity across the whole framework (that these are *the* three budgets everywhere) is the
unification claim, not an independent measurement.

**HONEST BOUNDS** — a toy: objects are band-limited complex-Fourier contours, recognition is nearest-template.
It demonstrates the *mechanism* (magnitude spectrum = spin-invariant identity; harmonics = nested expansion),
which is textbook Fourier shape analysis, framed in the budget language. Not a full perception system.

## 5. One-line
The third budget is **frequency**: a shape is a closed loop `z(t)=Σ_k C_k e^{ikt}`, and its three budgets are
the descriptor's three parts — **volume** (size, |C_1|), **orientation** (phase/spin), and **frequency** (the
|C_k| spectrum, the pattern); a spinning object stays *the same thing* because its frequency signature
**returns to origin** (measured: 1.00 recognition under spin vs 0.18 for the raw outline), and **expansion
adds frames to the cycle** — freq 1 a bare frame, each harmonic nesting the last plus a new band until you
reach the object's band limit and stop at the next frequency (error 0.41 → 0.00, then plateau).
