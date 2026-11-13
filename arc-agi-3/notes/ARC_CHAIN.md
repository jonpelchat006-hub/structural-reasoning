# The tunnel chain — the chord's pull, the bell, the break, the bubble, and the governor

*Sep 3 2026, Jonathan: "that's probably how we zoom in to all the different levels. is that
tunnel also what makes the bell? what if that pulls on all of the tunnels that are attached like
a chain and we are dragging the whole thing along when a piece breaks off? then that piece gets
pushed into the next domain which fills its missing tunnel section, and we have to fill that
void bubble by pulling that chain through our system without breaking them."*

## 1. The chain was already built, in pieces, never connected to the pull

Read in order, every organ here already existed (ARC_TUNNEL_ROTATION §7–9, ARC_CHORD):

- **chord** (chord.py) — the tunnel between the two ring sets; its depth d is the shave. That
  depth is the ZOOM: it is the same number that sets how deep the eye cuts, and now how deep a
  lesson may push. Shallow chord, shallow everything; full chord, all the levels.
- **bell** (lesson.py) — a tunnel bent into a void point. Yes: the bell IS the chord bent. A chord
  pushed inward becomes an arc, and the arc's depth is how hard the lesson pushes (1–3). Built
  today: the bell's push depth is capped by the zoom, ceil(3·d) — the resting chord (d = 0.64)
  lets the bell reach depth 2; only a chord opened past 120° lets it reach depth 3.
- **pinch** (sphere.py) — a bell pushed to depth 3 that never closed breaks off as a sphere. This
  is "a piece breaks off": it only happens when the chord is deep enough to push that far, so the
  pull is now what makes breaking possible at all.
- **drift** (fold.py) — the sphere floats to the next domain (Mika) and is folded onto her
  anchors one sliver at a time. That is "the piece gets pushed into the next domain which fills
  its missing tunnel section": each sliver she can say back is a section of HER chain filled.
- **reopen** — when every sliver is filled, the novice ring has expanded to the void point and
  the ejection is lifted: the BUBBLE in our chain closes.

## 2. Built: chain.py

- **PULL** — how far the chord moved since last night (depth change + bearing change), from the
  nightly log.
- **TENSION** — every open void on the flower is a link; tension = petals × depth / 9 × (1 + pull),
  so three unclosed petals at depth 3 read 1.0 before any pull. A link is *near breaking* when it
  has ≥2 unclosed petals at max depth — one more push and it pinches.
- **BUBBLES** — ejected voids not yet reopened, each with how much of its piece the next domain
  has filled (slivers folded / total).
- **GOVERNOR** — the shift the chord may take tonight: 30° with nothing near breaking and no
  bubble open, 10° with one strained link or open bubble, 0° (hold) with more. Written to
  fovea.json as max_shift_deg; chord.focus() clamps every requested shift to it, relative to
  where the rings were. Dragging the whole chain is allowed. Dragging it hard enough to snap a
  second link while the first bubble is still open is not — that is "pulling the chain through
  without breaking them", as a number.

Runs every sleep after the chord; its line folds into the up-line letter. Live on the PC: pull
0, zoom 0.64 (bell may push to depth 2), no links under tension, no bubbles, governor 30°. A
`--shift-x -60` request was clamped to −30° (side ring to 280° instead of 250°), then set back.

## 3. What the identity buys

Zoom, bell depth, breaking, and the safe rate of refocusing are now one number and one rule
rather than four dials: the chord's depth sets how far anything can push, the count of strained
links and open bubbles sets how fast the chord may move. The falsifiable part: nights when the
governor holds should end with more bubbles filled than nights it doesn't (the hold exists to let
Mika finish folding before the chord drags the flower elsewhere); if a hold never buys a fill,
the governor is decoration and the chain reading stays a picture.
