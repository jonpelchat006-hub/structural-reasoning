# Uniqueness-routing test — does signature isolation predict difficulty?

**Hypothesis (from the sphere-generator thread):** ARC tasks that are *unique*
(isolated in 7D-colour signature space, far from all others) should be the *hard*
ones — the tasks needing a per-task "tail" / forced completion rather than reuse.
If so, signature isolation could **route** tasks: resonant → cheap reuse,
unique → expensive forced-completion solver.

**Method.** Encoded all 400 ARC tasks with the real `signature.ts` encoder
(`run_isolation.ts` → `sig_all.json`). For each task, isolation = distance to its
nearest *other* task, using `signature.ts`'s own weighted L1 (domain dim ×3, dark
×2). Solved set = the 53 tasks banked in `arc-learned.json` (coordinator snapshot).
Analysis: `iso_analysis.py`.

## Result — hypothesis FALSIFIED (and informatively)

| group | solved | rate |
|-------|--------|------|
| has an identical-signature twin (**resonant**) | 34 / 305 | **11.1%** |
| no twin (**unique**) | 19 / 95 | **20.0%** |

Solve rate by isolation bucket: `0 → 11.1%`, `1–2 → 20.0%`, `3–4 → 20.0%`.
Solved tasks have **higher** mean isolation (0.509) than unsolved (0.262).

**Isolated/unique tasks are solved ~1.8× MORE often, not less.** The naive
routing idea ("unique = hard = send to the tail solver") is wrong on this signal.

## Why (the honest read)

The 7D signature is coarse — 305/400 tasks share an exact twin, so the space is
heavily degenerate. In it, "isolation" does **not** mean "needs a forced
completion." It means the task has a **distinctive, legible surface feature** (a
clear odd-one-out, a sharp size change) — exactly the kind of clear handle the
generic muscle already solves well. Crowded (twinned) buckets just mean "the
signature can't tell these apart," so they sit at the base solve rate (~11%).

This is the **Test B/C lesson again, one level up:** the certificate you measured
(signature isolation) proves one kind of independence (surface distinctiveness),
**not** the utility-relevant kind (forced-completion necessity). The deep
"uniqueness that needs a tail" is a property of the **joint-constraint system**
(Test G's incidence quadratic), invisible at the surface-signature level.

## What is actually usable

- **Signature isolation is a poor difficulty predictor** — do not route on it.
- **The real near-term lever is the resonant bucket, not the unique one:** 271 of
  the 336 unsolved tasks *have* twins. They share coarse structure with other
  tasks yet aren't solved — i.e. the solver is **under-exploiting** the resonance
  it can already see. That is a bigger, more tractable target (271) than the 76
  unique-unsolved.
- **A deeper uniqueness detector is needed** for tail-routing — one built on the
  joint train-pair constraint structure, not the 7D surface signature.

## Caveat
Solved labels are the 53-task coordinator snapshot in `arc-learned.json`, not the
later 66–67 muscle-group run; re-running against the current solved set could
shift magnitudes but not the direction (isolated solve at least as well).

Files: `run_isolation.ts`, `sig_all.json`, `iso_analysis.py`.

---

# Anchor-availability test — is the unsolved frontier "blind" or adjacent to known work?

**Idea (the anchored/mirror placement law):** rather than route unique tasks to a
blind solver, extend a ribbon *adjacent to a solved task* so one edge starts
informed, then rotate toward the target and mirror the far edge. Precondition:
does an anchor (a nearby solved task) actually exist? (`anchor_test.py`.)

## Result — the frontier is overwhelmingly anchored, not blind

For each of the 347 unsolved tasks, distance to the nearest **solved** task:

| anchor strength | count | share |
|-----------------|-------|-------|
| exact solved twin (dist 0) | 109 | 31.4% |
| solved neighbour within dist ≤ 1 | 239 | **68.9%** |
| truly blind (no solved task within dist 3) | 42 | **12.1%** |

median nearest-solved distance = 1, mean = 1.18, max = 7.

**So blind placement (golden-angle, §J.4) is the right tool for only ~12% of the
frontier; for ~88% there is a known neighbour to anchor to.** This is the
construction-pole search the framework was missing, and it is the common case.

## Compounding target
Of the 271 resonant-unsolved (has-twin) tasks: **109 have a twin that is already
solved** (a strong, ready anchor); the other **162 have only unsolved peers**
(weaker — anchor to a peer, or solve one representative and it becomes the anchor
for the cluster). Targeted compounding with a concrete hit list, vs. the weak
blind compounding measured earlier (Brick 6: 0%→8%).

## Honest bounds
- Surface-close (signature dist ≤1) ≠ solution-transferable (see isolation test
  above). The anchor is a *starting boundary condition* to rotate/adapt from, not
  a guaranteed solution.
- Mirror completion is exact only when the problem has reflection symmetry
  (orchard C₂ / Test G's ± branches); generally the far edge is forced by closure.

Files: `anchor_test.py` (+ `sig_all.json`, `arc-learned.json`).

---

# Twin-anchor transfer test — does adapting a solved twin's program work? NO.

Direct follow-up: 109 unsolved tasks have a solved signature-twin. Lifted each
solved task's program to a template, tagged by 7D signature; for each unsolved
task, tried ONLY its twins' templates (morph-bind to its palette + cmap).

## Result: 0 / 109. base 66 → 66 (16.5%).
Adapting a solved twin's program solved **zero** of its same-signature unsolved
twins. This quantitatively confirms the caveat: **same 7D signature ≠ same
solution.** The signature captures surface features (count, size-direction,
symmetry-presence); tasks that match on those still have entirely different rules.

## This is the FOURTH transfer test, all converging:
  - morph leave-one-out (structural skeletons): ~2-5, net-new 0
  - floor-collapse compounding: 2 reuses, 0%→8%
  - codon-roof recall: 0
  - twin-anchor (signature): **0 / 109**
ARC transfer/reuse is near-zero BY DESIGN — the benchmark is built so tasks share
surface structure but not solutions. No anchor/twin/resonance mechanism moves the
number, because the thing they key on (surface similarity) is decoupled from the
solution (Test B/C/E lesson, now proven a fourth time).

## So "can we go higher?" — yes, but NOT via transfer.
The ONLY lever that has ever moved the ARC number is MORE PRIMITIVES (muscle):
  11 ops → 26 ; 25 ops → 39 ; +bug-finder → 44 ; +relational+nesting → 56 ;
  +muscle batch (panels/symmetry/occlusion) → 64 ; +move/induce/generate → 67.
Each well-chosen primitive family adds ~+several; the muscle taxonomy
(SPHERE_GENERATOR_TEST / arc-proposer RESULTS) gives the priority order:
object-move-to/align, count→emit, flood-fill-region, sub-grid/panel-select,
scale-to-reference, and the GENERATOR family (the 6% INK_ADDED gap).
Transfer is a dead end on ARC; muscle is the live path up.
