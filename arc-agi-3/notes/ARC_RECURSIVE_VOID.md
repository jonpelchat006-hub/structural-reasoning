# Recursive re-based void — every border is a void line, and the zero re-bases to the parent's fill per shell

*Session Aug 2026. Extends `ARC_VOID_DOMAIN`. Jonathan: every object has a border = a void line where the
local colour falls to a reference; the framework is RECURSIVE, so each bordered cluster becomes a new outer
shell you can isolate (and run the bounce inside); and when you ZOOM IN on a square inside a cluster, its void
does NOT go to 0 — it goes to the CLUSTER'S colour. The zero-level is re-based per shell. `recursive_void.py`,
figure `recursive_void.png`. Grounds in `FOLDING_REBASING` (each pixel is the whole brain shifted one notch
inward, with a fresh void), `FOLDING_VOID_LINE_DRAW` (the void line as a segmenting/drawing primitive),
`VOID_LINE_PAPER` (devil's-staircase zoom = multiresolution/wavelets, continuity holds at every scale).*

## The idea
- **Border = void line.** An object's outline is where the local colour drops to a reference; drawing that
  line segments the object (the void-line-as-drawing-primitive).
- **Recursion.** Each bordered region is a new outer shell: isolate it and process it independently (its own
  bounce/solve), then descend into its interior — the squares within a cluster, each with their own borders,
  which are the *old* void line one level down.
- **The zero re-bases (the crux).** The reference the border falls to is NOT global 0 at every level. At the
  root it is 0 (the wall of 0s). Inside a cluster it is the **cluster's fill colour**. So "drive the void to 0"
  generalises to "drive the void to the **local reference = the parent shell's fill**." Zoom in and the void
  goes to the cluster colour, not 0.

## Measured (300 nested images: background 0 → clusters colour C → inner squares near C, bordered by C)
| level | detector | recovered |
|---|---|---|
| L1 clusters (border → 0) | either | **100%** (897/897) |
| L2 inner squares | GLOBAL-ZERO (void ≡ 0 everywhere) | **0.0%** (0 / 6829) |
| L2 inner squares | RE-BASED (void ≡ parent fill) | **93.8%** (6406 / 6829) |
| — | re-based reference == cluster colour (not 0) | **95%** (850/897) |

**The recursion requires re-basing the void.** A global-zero border detector is *completely blind* below the
first level — it recovers 0 of 6,829 inner squares, because inside a cluster there is no 0 to border against.
Re-basing the zero to the cluster's fill recovers 93.8% of the nested structure. And the re-based reference
*is* the cluster colour, not 0, 95% of the time — Jonathan's "after zooming in it wouldn't go to 0, it goes to
that colour," confirmed.

## What this is
This is `FOLDING_REBASING` made operational on the screen: each level's **void/zero is the parent level's
fill**, so the image is a **pyramid of nested void lines** — formally a Laplacian pyramid / multiresolution
decomposition (`VOID_LINE_PAPER`'s devil's-staircase: finer resolution reveals more borders, continuity holds
at every scale, down to a finite floor). Each cluster, once bordered, is a self-contained shell with its own
re-based void — so the whole game-loop (probe → meaning DAG → collapse → surprise → void-to-reference) can run
*recursively inside it*, which is Jonathan's "that window becomes a new outer shell we could build the bouncing
balls in."

## Why it matters for the build
- **Segmentation must be re-based, not global-thresholded.** Perception that keys everything off a single
  background colour (void ≡ 0) sees only the top layer. To read nested structure — a cluster of shapes, a
  grid-of-panels, an object made of parts — the detector must **isolate a region and re-base its zero to that
  region's fill**, then recurse. This is a concrete perception rule for the game-loop's ψ-1.
- **The void reference is the operator's target.** In `ARC_VOID_DOMAIN` we drove the void to 0; recursively,
  we drive it to the **local reference**. An operator inside a cluster (a square rotating) is measured against
  the cluster colour, not 0 — so the re-based zero is what makes the inner surprise/alignment well-defined.
- **Recursive isolation = per-object shells.** Each bordered region can be handed the full loop independently
  (its own probe/meaning/collapse/void), then results compose upward — the scale-recursion `FOLDING_REBASING`
  predicts, now with a measured segmentation mechanism under it.

## Honest bounds
Synthetic nested images, exact truth. The re-based detector uses the region's modal colour as the fill
reference (robust here; real screens with texture/anti-aliasing would need a tolerance band — the θ-cone of
`ARC_VOID_DOMAIN`). The 6.2% L2 miss is adjacent same-colour squares merging into one component (a genuine
under-segmentation, not a false claim). Two levels shown; deeper nesting follows by the same re-basing but
isn't separately measured here. No claim about the real ARC-3 environment (not loaded). `recursive_void.py`;
scripts live in the session.
