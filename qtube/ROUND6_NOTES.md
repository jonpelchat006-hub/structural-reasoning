# Quaternion model: round 6, November 1, 2026

## What the current model actually contains

`qtest.py` builds quaternion layers followed by a sedenion matching score.
`qlift.py` instead puts learned features at positions in the image. `qbridge.py`
packs four such quaternions into each 16-dimensional node. This gives structured
features and a bilinear relation score. It does not yet implement recursive
object/part reasoning, a learned action model, or an autonomous ARC agent.

The downloaded Kaggle QTUBE notebook uses deterministic image transforms in
`qtube_fit.py`; it does not load these learned models. Its public-game results
cannot be attributed to the learned quaternion architecture.

## The socket objective needed different roles

With one encoder and a perfectly aligned match, the bridge receives `a=b`.
Every nonzero sedenion satisfies `||a*a|| / ||a||^2 = 1`. Minimizing that ratio
therefore does not directly reward equality. A socket needs a compatible partner
code, which can differ from the object's own code.

This does not prevent classification: incorrect pairs can have ratios above 1.
The issue is whether the system actually uses near-zero compatibility, rather
than merely ranking a self-product of 1 below other products.

`qports.py` adds independent object and socket ports. Split the four quaternion
heads into scalar channels `w` and vector channels `V`, and use

    P(w, V) = (A w + c, B V).

`A` and `B` are learned 4x4 matrices; the bias affects scalars only. These maps
commute with all spatial quaternion rotations, preserving the physical meaning
of the placed nodes. The two ports add 72 trainable parameters in total.

A concrete nonzero annihilator pair under the existing multiplication convention
is `a=e1+e10`, `b=e5+e14`, for which `a*b=0`. A quaternion-head permutation can
map the first code to the second, so complementary ports are mathematically
compatible with this representation. This establishes possibility, not a learned
advantage on ARC.

## Controlled experiment

Run from this directory:

```powershell
python -u qports.py --steps 1000 --seeds 3 --device cuda --batch 64 --ntest 2000 --save-dir models_r6_ports_clean --out r6_ports_clean.json
```

Compare normalized distance, distance with separate ports, tied socket,
separate-port sedenion socket, and separate-port random-table socket. All use
the same initial CNN weights and identical training batches for each seed.
The dual-port distance and random-table variants match the dual socket's
parameter count.

Important protocol details:

- The encoder has explicit D4 symmetry (`flat`). Mirror behavior is an
  architectural prior, not a discovery of mirror symmetry from the data.
- Training uses the four known physical planar rotations. Evaluation adds the
  four plane-preserving 3D half-turns that implement image reflections.
- There is no learned free rotation bank that can manufacture a nongeometric
  socket relationship.
- Each port code is normalized before multiplication. The old additive
  `+1e-6` denominator could reduce ratios just by shrinking both codes.
- Training accepts all C4-equivalent candidates; evaluation accepts all
  D4-equivalent candidates. The generator can accidentally make a nominal
  distractor into another valid match. Designated-label accuracy is also saved.
- Training and evaluation shapes come from independently seeded pools. Those
  pools do not explicitly reject cross-pool D4-orbit collisions.
- Ratios, near-zero ratio fractions, temperature, and code norm quantiles are
  recorded. A small classification loss alone does not establish annihilation.
- The positions-off ablation is descriptive. For sedenion sockets it restricts
  codes to a quaternion subalgebra whose normalized product norm is always 1;
  loss of discrimination in this condition is not proof of learned geometry.

An interrupted first pilot used full D4 target labels during rotation-only
training. Its partial results are preserved as `r6_ports_pilot.json`; use the
`*_clean` experiment for conclusions. Original round 1–5 code/results were kept.

### Completed results

Three seeds, 1,000 steps each, and 2,000 test examples per condition per seed:

| Scorer | Rotations | Mirrors | Mirrors, positions removed |
|---|---:|---:|---:|
| Distance | 100.000% | 100.000% | 100.000% |
| Distance with dual ports | 100.000% | 100.000% | 97.967% |
| Tied sedenion socket | 99.933% | 100.000% | 12.383% |
| Dual sedenion socket | 99.933% | 99.983% | 12.300% |
| Dual random-table socket | 98.850% | 98.800% | 90.917% |

Results and all diagnostics: `r6_ports_clean.json`. Training/evaluation of the
15 models took 263.7 seconds, excluding shape-pool generation and process startup.
These numbers describe this synthetic benchmark, not ARC-AGI-3 game performance.

The true-table scorers beat the random-table control on this setup, but neither
beats distance. All three distance models remain perfect after positions are
removed: invariant scalar features can solve the recognition task. Correct-match
bridge ratios average 1.000 for tied sockets and 0.981 for dual sockets on mirror
evaluation. No correct candidate's mean node ratio is below 0.05. The experiment
therefore does not demonstrate useful near-zero annihilation.

## The next capability: actions must operate on the representation

Matching eight different shapes admits invariant scalar fingerprints. It does
not test whether the representation can execute an ordered transformation.
`qcompose.py` tests eight differently oriented copies of the *same* asymmetric
shape. Given an ordered action string, it must select the exact resulting
orientation. Invariant features cannot distinguish these candidates.

For actions executed first `R` then `F`, the composite is
`q_total = q_F * q_R`, with the rightmost quaternion acting first. A left-right
image reflection is a 180-degree 3D turn about the y axis, using
`q_F=(0,0,1,0)`. Quaternion multiplication composes the operators; a maximum
over arbitrary turns would erase the requested action and is disallowed here.

Known operators provide a geometry diagnostic. Learning two primitive
quaternions on single-action examples and evaluating unseen ordered products
is a separate, stronger experiment. Neither is an ARC game score.

### Completed action-composition results

For each of the three distance checkpoints, freeze the encoder and learn only
two action quaternions (8 stored numbers) on 512 new asymmetric shape orbits.
Train on single `R` and `F` actions only. Test on 1,000 additional asymmetric
orbits per seed, rejecting exact D4-orbit overlap with encoder/action training.
All eight differently oriented candidates depict the same shape. Results:

| Action supervision | R / F / RF / FR | Length 3 | Length 4 | Length 5 | Length 6 |
|---|---:|---:|---:|---:|---:|
| Candidate classification, 300 steps | 100% | 100% | 99.167% | 96.533% | 95.267% |
| Next-pose feature distance, 300 steps | 100% | 100% | 100% | 100% | 100% |

Classification can stop improving while primitive rotation matrices are still
inaccurate: Frobenius errors range from 0.240 to 0.691. Those errors accumulate
when composing actions. Directly minimizing the target pose's feature distance
reduces primitive matrix errors to between 4.98e-6 and 4.18e-5 across all six
learned operators. No composed sequence is shown in either training condition.

With supplied exact action operators, all three models score 100% in every
tested group. Removing positions produces approximately 12.5% uniform-tie
accuracy, as expected for eight indistinguishable orientations. These tests
verify a small compositional action mechanism with explicit geometric priors;
they do not demonstrate general rule discovery or an ARC-solving agent.

Reproduce the pose-supervised experiment for seed 0:

```powershell
python qcompose.py --checkpoint models_r6_ports_clean/dist_s0.pt --device cuda --n 1000 --fit-steps 300 --fit-loss pose --out r7_compose_pose_s0.json
```

Detailed results are `r7_compose_s0.json` through `r7_compose_s2.json` for
classification and `r7_compose_pose_s0.json` through `r7_compose_pose_s2.json`
for pose supervision.

## Symmetric shapes require more than centroids

For any centered image with 180-degree symmetry, every invariant attention
head's positional mean must be zero. A horizontal bar and its vertical version
then receive the same quaternion code, even though they are different pictures.
The same problem occurs with a filled 3x5 rectangle. This is a representation
limit, not an optimization failure. The asymmetric action benchmark deliberately
excludes such cases, so its perfect score does not cover this issue.

`qmoments.py` retains the centered covariance of each existing attention map,
with no extra learned parameters or training. Quaternions move the means;
covariances move by `M_next = R M R^T`. Covariance is divided by the fixed grid
radius squared (9) before scoring, so its scale cannot be learned away.

The CPU float64 diagnostic covers both distinct source orientations of a
centered length-5 bar and a centered 3x5 rectangle, each under `R,F,RF,FR`,
with shuffled distinct candidates: 16 cases total. Centroids alone achieve 50%
with uniform tie breaking; means plus covariance achieve 100%. Full D4
covariance equivariance holds to maximum absolute error 2.67e-15. On these
two-orientation shapes some command orders coincide, so this diagnostic tests
retention of orientation, not noncommutative action semantics.

```powershell
python qmoments.py --checkpoint models_r6_ports_clean/dist_s0.pt --out qmoments_results.json
```

Second moments fix this class of collapse, but different shapes can share the
same low-order moments. A fuller model should retain distributions, richer
tensor features, or sets of parts with symmetry-aware correspondence.

## A concrete route toward the nested agent

1. Preserve object identity/features while actions change pose. Test ordered
   composition and inverse actions before introducing more algebra dimensions.
2. Add a tree of part/object/scene frames. Store each child pose relative to its
   parent; compute world poses by quaternion composition and rotated translation.
   This is the missing recursive meaning of "nested" in the current model.
3. Learn action effects from observed `(frame, action, next frame)` transitions.
   Predict both the next object state and confidence; reject a law when the next
   observation contradicts it.
4. Plan short action sequences through that transition model, then verify them
   against the environment. Keep learned compatibility as a ranking of hypotheses;
   level completion and exact observed conditions confirm success.

The current hybrid already has useful integration seams in the downloaded
`planet/mika_core.py`: `_target` ranks goal hypotheses; `_plan` and `solve` search
observed operators; `see` attributes observed changes to the touched thing and
calls `NodeBook.observe`. A learned model must respect the real glyph sizes:
the experimental encoder currently accepts only 7x7 binary masks.

## Submission timing

The organizer lists code submissions due November 2 and papers due November 8:
https://arcprize.org/competitions/2026 . The paper track requires a corresponding
Kaggle code submission demonstrating the described approach, even if its score
is low: https://arcprize.org/competitions/2026/paper . A synthetic matching result
does not establish that the existing Kaggle entry demonstrates this architecture.
