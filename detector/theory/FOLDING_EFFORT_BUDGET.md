# Level 4 — the human action budget

*2026-07-28. Jonathan: "We really only have mouse and keyboard or touchpads. If there was an edit that
would take years to get perfect with available programs, that would say something. Is time like a 4th
level?"*

**Yes — but not as a clock. The declared clock is dead. Time is readable only as effort, and effort is
readable from the shape of the change.**

Result: **22 of 22 real generative edits exceed the most complex single human gesture, by a median
factor of 16×, with a re-encode-only control at 72× separation.** And the output is an effort bound,
not a verdict — which is the honest thing it can support.

---

## 1. The declared clock carries nothing — measured first because it was cheap

Across 13 `altered` pairs and 9 `camera 2` edits:

> **`DateTimeOriginal`, `DateTimeDigitized` and `DateTime` (modify) are byte-identical between every
> original and its edit.**

The editor copies all three forward verbatim. There is no capture-to-modification gap to read, on any
pair, in either set. So the obvious version of "time as a fourth level" — look for a suspicious
interval — has no signal at all in this data. Recorded so it is never re-attempted.

That failure is what forces the useful formulation. If time is readable it must be read from the
**pixels**, as *how much work this cost*, not from a field.

## 2. Why an effort measure is the right answer to Jonathan's objection

His objection to `FOLDING_DISCRETE_IMAGINARY_CAMERA` is correct and important: downloading,
re-uploading and passing through a messaging app rewrite the container, and those hops are the most
common things that happen to an image. Every signature-level measure degrades on exactly the path
real files take.

**An effort measure does not live in the container. It lives in the shape of the change, and shape
survives re-encoding.** That is the property that makes this worth building rather than another
container feature.

## 3. The tool grammar is small, and that is the whole leverage

A person works through an enumerable set of selection primitives, and each has a short description:

| tool | boundary description |
|---|---|
| rectangle | 4 vertices |
| ellipse | a conic — ~40 vertices to 2 px |
| lasso | as many vertices as they clicked — tens |
| brush | a swept disc; curvature bounded by the brush radius |

A machine-computed mask has no such bound. It follows the object contour at pixel resolution. So the
measure is **Douglas–Peucker vertex count at fixed pixel tolerance** — literally *how many points
would a person have had to place*.

## 4. Results

**Real generative edits (22 pairs, three cameras, two editing sessions):**

| | median | range |
|---|---|---|
| vertices @ 2 px | **1231** | 454 – 5302 |
| vertices @ 5 px | 526 | 193 – 2375 |
| connected components | 19 | 7 – 138 |
| gradient adherence | **1.24×** the frame's own median gradient | 0.57 – 6.63 |

**Tool-grammar controls, synthesised at the same median area.** These are not sampled from anything —
they *are* the grammar, so they are a floor rather than an estimate:

| tool | components | vertices @ 2 px |
|---|---|---|
| rectangle select | 1 | 4 |
| lasso, 8 clicks | 1 | 8 |
| lasso, 24 clicks | 1 | 23 |
| ellipse select | 1 | 43 |
| lasso, 60 clicks | 1 | 53 |
| **brush stroke** | 1 | **75** |

**22 / 22 real edits exceed the most complex single gesture. Median 16.4× the brush stroke.**

Gradient adherence above 1 means the boundary **snaps to object contours** — it is placed where the
image already has edges. No unaided hand gesture does that; a lasso cuts across texture wherever the
hand happened to be.

## 5. The control that could have killed it, and did not

The masks come from a **pixel difference**, and re-encoding a whole JPEG perturbs every block. Some
component counts (138 on a 7% edit) looked like speckle. If re-encode alone produced a
thousand-vertex mask, the measure would be reading the codec, not the edit.

Same measurement on 8 frames where **nothing was edited**, only re-encoded:

| condition | area % | components | vertices @ 2 px |
|---|---|---|---|
| re-encode q95, no edit | 0.00 | 0 | **0** |
| re-encode q85, no edit | 0.00 | 0 | **0** |
| re-encode q75, no edit | 0.01 | 2 | **17** |

**72× separation.** The low-quartile threshold estimator holds the codec below the floor. The mask
shape is the edit.

## 6. What this licences, exactly — and what it does not

> *"If a human produced this edit with a pointing device, the boundary alone required at least 1231
> deliberate placements at 2 px accuracy."*

It does **not** licence "this is AI". A patient human with a pen tool reaches the same number given
enough hours. That ambiguity is irreducible from the image alone — and it is the honest content of
Jonathan's own framing: *years to get perfect*. Complexity buys you a lower bound on time, not a
verdict on authorship.

But a lower bound on time is not a consolation prize. It is a **different and more defensible
product**, because it converts an unanswerable question into an economic one:

- nobody spends forty hours retouching a $50 insurance claim photo
- nobody hand-masks 138 disjoint regions at pixel accuracy to fake a delivery confirmation
- an effort bound is **auditable and explainable to a non-expert** — "this would have taken a person
  a working day" is a sentence a claims adjuster or a judge can act on, which "0.87 fake" is not

And it degrades gracefully in the direction that matters: it is **conservative**. Overestimating how
easy an edit was produces a *miss*, never a false accusation. That matches the stated product
priority — zero false positives first.

## 7. Where it sits in the stack

| level | question | status |
|---|---|---|
| 1 — imaginary camera | which device layout wrote this? | **measured**, 1/61 FP |
| 2 — imaginary programs | which editor / platform rewrote it? | catalogue exists, untested |
| 3 — plausible human action | could a person have done this at all? | untested |
| **4 — effort budget** | **could a person have done it in the time available?** | **measured, 22/22** |

Level 4 turns out not to be a refinement of level 3 but its **quantitative form**: level 3 asks
whether the operation is in the grammar, level 4 asks how many grammar operations it would take.

**All four are consistency tests between two things inside one artefact.** That is why they escape
the confound that killed 40 of 42 features — the control is the file itself.

## 8. Open, in priority order

1. **A human arm.** Every edit in the corpus is machine-assisted (Samsung's object eraser). The
   tool-grammar controls are synthetic — correct as a floor, but a set of genuinely hand-made edits
   (Photoshop lasso, GIMP, a phone paint app) would test whether real human work lands where the
   grammar predicts. **This is the single highest-value data request outstanding.**
2. **Survival through platform hops.** The claim is that shape survives re-encoding; only q75 was
   tested. Resize + re-encode (the actual WhatsApp/Instagram path) is untested here, and that is the
   path where every container measure died.
3. **The pen-tool adversary.** A patient forger is the named failure mode. Worth checking whether
   *human-slow* precision differs in kind from *machine* precision — a hand-placed pen curve is a
   spline with controlled continuity, while a machine mask is per-pixel. If those separate, level 4
   gains an authorship claim it currently cannot make.
4. **Geometric-art case.** Jonathan's original example. A vector tool's shapes are *exactly*
   axis-consistent under one renderer's anti-aliasing rule; a decoder's are only approximately
   geometric. Directly measurable with the same machinery.

**Code:** `effort.py`, `effort.json`.
