# Mixedness as Confidence — the C-field is the detector's uncertainty map, and anomalous mixedness is a fake tell

*Captures a working-session thread (Jonathan + Claude). The protein "C" mixedness field maps onto the
detector three ways at once: the C core **marks boundaries**, the spread of mixed pixels is the
**blur/width** of a boundary, and how mixed a pixel is **is how confident we are there** — which flags
where the picture is unsure or faked. Grounded in the tested `FOLDING_TRAIL` / `VOID_LINE_PAPER` §8;
companion to `SHOVELCAT_CHECKER_V6` (disagreement = seam), `FOLDING_CONTEXT_ROUTER`,
`FOLDING_VOID_LINE_DRAW` (thickness). Status: the confidence half is already computed by the engine;
the image-mixedness/blur observer is the new build.*

---

## 1. The protein grounding is tested (FOLDING_TRAIL)

Mixedness was defined precisely: per pixel, the **distance-weighted fraction of nearby material from
the *other* domain** — 0 deep in a pure region, ~0.5 at the interface. On the canonical 8 proteins:

- **The C core marks the boundary.** C-as-a-graded-field is the min-cut surface; one connected trail.
- **Mixedness peaks at the core and tapers outward** (corr with distance-to-center −0.43 to −0.68) —
  "higher closer to the center," fading with distance. That taper *is* the blur profile.
- **The spread grows with the interface.** Strict threshold → 3–17% of pixels; fine threshold → up to
  **66% (6LDH, most-knitted)** vs **15% (calmodulin, the floor)**. A bigger core → a wider mixed zone
  spreading further, exactly "larger core → larger void line → mixed pixels spread further."

So Jonathan's three claims — cores mark boundaries, spread = blur width, larger core = wider spread —
are measured, not hypothetical.

## 2. Mixedness = confidence, and the detector already computes it

"How mixed a pixel is = how confident we are there" is exactly right, and it is **already in the
engine**: the committee's per-cell **disagreement** *is* the mixedness field. When the observers
cannot agree whether a cell is real or fake, that cell is "mixed" — hard to label — which is low
confidence. `combine()` computes `disagreement = pstdev(observer authenticity)` per cell and flags
`is_seam` where it is high. Read that map as a **confidence overlay** and it is the "where is the
picture unsure" map Jonathan is describing. Nearly free to surface — and a strong product/trust
feature ("solid verdict here, shaky there").

## 3. The new signal — the image's *own* mixedness (blur), physical vs anomalous

Distinct from observer disagreement is the image's own soft-segmentation / boundary blur — how softly
each region blends into its neighbours (person vs background). This has **physics**, which makes it a
fake tell:

- **Real photo:** *physically consistent* mixedness — a sharp subject with a coherently blurred
  background (one focal plane, depth of field), or directional motion blur. The mixed zone sits on a
  true boundary with a sensible, structured width.
- **AI image (esp. a composite / inpaint — the "person on a background" case):** *anomalous*
  mixedness — melted boundaries where objects meet, halos around a pasted subject, blur that matches no
  focal plane, mixed regions that are not at a real edge. **AI smears at the seam.**

A mixedness/blur observer measures the soft-segmentation field and asks *is this blur physically
coherent?* Anomalous spread is the tell. It is **orthogonal** to both the semantic vision routes and
the global spectral route (it is *local boundary structure*), it targets the most common real-world
fake (compositing), and it is **model-free** (free to compute and benchmark).

## 4. Honest discipline — mixedness locates, it does not judge

Same lesson the proteins taught twice: mixedness **marks the boundary and the uncertainty; it does not
by itself mean fake.** A real photo's depth-of-field blur is high-mixedness and completely authentic.
So mixedness is a "look here / how confident" map; the **fake signal is mixedness that is *anomalous***
(inconsistent with a physical blur), not mixedness that is merely high. This mirrors the tested
correction: "blurry = boundary" held (the graded C field), but "blurry = weak / where-to-cut" was
refined — the cut runs through the **rigid buried core**, not the floppy pixels (`FOLDING_PIXEL_STRAIN`,
|r| ≤ 0.05; seam is *less* mobile). The field marks the boundary; the judgment needs more than "it's
blurry."

## 5. One object, four names

The spread of the mixed zone **is** the void-line **thickness** (`FOLDING_VOID_LINE_DRAW`, thickness by
level), which **is** the **confidence width**: wide uncertain zone → the detector genuinely can't tell
(soft region or a clever blend); narrow → confident. Thickness, mixedness, boundary-blur, and
confidence are the same quantity seen four ways.

## 6. Builds

1. **Surface the confidence map** — expose the per-cell disagreement the engine already computes as a
   confidence overlay (nearly free; product trust feature).
2. **Mixedness/blur observer** — a fourth, model-free, orthogonal route: local sharpness map (DoF
   structure), edge-transition width (melt), gradient statistics, and a color-mixedness field; scored
   for *anomalous* (physically-inconsistent) blur. Free to benchmark on the existing 50-image sets;
   aimed squarely at composited fakes.

*Sources: `FOLDING_TRAIL` / `VOID_LINE_PAPER` §8 (mixedness field: connected trail, center-peaked,
spread grows with interface — tested 8 proteins), `FOLDING_PIXEL_TRANSMISSION` (graded per-border
efficiency; seam woven), `FOLDING_PIXEL_STRAIN` (the cut is rigid core, not blurry pixels — the
"blurry = weak" correction), `SHOVELCAT_CHECKER_V6` (disagreement = seam = the confidence field),
`FOLDING_VOID_LINE_DRAW` (thickness), `FOLDING_CONTEXT_ROUTER` (orthogonal axes). Code target:
`mixedness_observer.py`.*
