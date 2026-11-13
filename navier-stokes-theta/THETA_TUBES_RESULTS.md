# Interface formation without a forced hot channel: antiparallel tubes — 14 September 2026

Purpose: every earlier interface (THETA_THREE_RESULTS.md) formed on the
powered ring's hot return channel, so its placement, scaling and feedback
could all be artefacts of the forcing geometry. This test removes the drive.
Two antiparallel Gaussian vortex tubes (width .3, separation .8, Kerr-type
sinusoidal perturbation of amplitude .2) start with kinetic energy .15 and
decay freely. The insulated thermal field is driven only by viscous heating,
so heat exists only where the flow itself concentrates gradients. Three-factor
kinetic theta, mean-of-surroundings references, wall 3, floor -pi; optional
J sink. 48^3, dt .01, t <= 3. Reproduce:

    python navier_stokes_theta/theta_tubes.py --n 48 --nu 0.03
    python navier_stokes_theta/theta_tubes.py --n 48 --nu 0.02
    python navier_stokes_theta/theta_tubes.py --n 48 --nu 0.01
    python navier_stokes_theta/theta_tubes.py --n 48 --nu 0.01 --kappa 1.0
    python navier_stokes_theta/theta_tubes_place.py

## Results, 48^3

| nu | kappa | peak \|grad u\| | first theta = pi | Gamma cells (max) | peak j on Gamma | max f_S / f_T / f_E | sink / E0 | k_eta / k_max |
|---:|---:|---:|---:|---:|---:|---|---:|---|
| .03 | 0 | 9.58 | 0.6 | 22 | 0.23 | 4.00 / — / — | 0 | ~5 / 16 |
| .02 | 0 | 9.78 | 0.3 | 60 | 4.80 | 3.96 / 1.16 / 1.82 | 0 | 8.5 / 16 |
| .01 | 0 | 11.20 | 0.2 | 214 | 7.53 | 3.87 / 1.14 / 1.87 | 0 | 12.1 / 16 |
| .01 | 1 | 11.41 | 0.2 | 228 | 7.32 | 3.87 / 1.14 / 1.86 | 1.11% | 12.1 / 16 |

Energy accounting (kinetic + heat + sink = initial) closes to 3.7e-9 in all
runs. 32^3 at nu = .02 gives the same picture (first pi at 0.4, 52 cells).

**Placement (nu = .01, passive; theta_tubes_place.py).** At every sampled
time from 0.3 to 2.7, **100% of interface cells lie inside the top-10%
gradient region and inside the top-10% heat region**; the mean gradient on
Gamma is 10-15x the domain mean; the single strongest-gradient cell is inside
Gamma at t = 0.6 and 2.1 and within 0.5-1.8 length units of it otherwise
(Gamma is a band along the collision zone, not a point). With no drive and
no imposed hot spot, the interface forms on the gradient concentration.
Placement is a property of where the flow sharpens, not of the forcing.

**What drives theta.** Still the entropy factor (3.9-4.0); the kinetic
factor tops out at 1.87 and the temperature factor at 1.16, as in the ring.
The route is gradients -> viscous heating -> entropy contrast -> pi. The
interface is where gradients concentrate *because* that is where heat is
made; theta reads the gradients through their dissipation.

**Size and lifetime scale with viscosity.** Gamma grows from 22 to 214 cells
as nu falls from .03 to .01, forms earlier (0.6 -> 0.2) and lasts until
t ~ 2.7 before the mean warms and the contrast dissolves it. The sink at
kappa = 1 removes 1.1% of the initial energy at nu = .01.

**Scaling could not be tested here.** In a decaying flow the peak gradient
is set by the initial condition (9.6 -> 11.2 over the sweep), so the cubic
law measured on the forced ring has no lever to pull on in this geometry. The
exchange on Gamma still rises steeply with falling nu (0.23 -> 7.5) but
that is mostly Gamma growing into the high-exchange zone. A scaling test in
this geometry needs stronger initial data (E0, tighter tubes) at 64^3+.

## What is established, and what is not

Established across two unrelated geometries: theta reaches pi via the
entropy factor with mean references; the interface is small, transient,
and sits where the two planes exchange most and where gradients concentrate;
the J sink is energy-consistent and grows in share as viscosity falls.
Not established: the cubic scaling outside the forced ring; any statement
about the continuum limit; a value for kappa; and whether, at Reynolds
numbers where NS is actually hard, Gamma stays a thin band or fills the
dissipative range. nu = .01 at 48^3 is at the resolution edge (k_eta 12.1
vs k_max 16).

Data: theta_tubes_48_*_results.json, theta_tubes_place_results.json.
Code: [theta_tubes.py](theta_tubes.py), [theta_tubes_place.py](theta_tubes_place.py).

## Addendum: stronger initial data — the mechanism weakens (E0 sweep, nu = .02, 48^3)

The only lever on gradients in a decaying flow is the initial energy.
E0 = .6 needs dt = .005 (CFL .30); the script now checkpoints and resumes.

| E0 | dt | peak \|grad u\| | first theta = pi | Gamma lifetime | Gamma cells (max) | peak j on Gamma | f_S max at t = .6 | reference / cooling |
|---:|---:|---:|---:|---|---:|---:|---:|---|
| .15 | .01 | 9.8 | 0.3 | 0.3 - 1.5 | 60 | 4.80 | 3.64 | global / none |
| .30 | .01 | 13.7 | 0.3 | 0.3 - 0.7 | 56 | 9.33 | 3.56 | global / none |
| .60 | .005 | 22.4 | never (max 3.10) | — | 44 (above 3 only) | 3.68 | 3.45 | global / none |
| .15 | .01 | 9.8 | never (max 1.97) | — | 0 | — | 2.02 | local, l = .5 / none |
| .15 | .01 | 9.8 | never (max 2.61) | — | 0 | — | 2.75 | local, l = 1.0 / none |
| .60 | .005 | 22.4 | 0.3 | 0.3 - 0.9 | 64 | 3.68 | 3.65 | global / rate 2 |

Energy accounting (kinetic + heat + removed heat + sink = E0) closes to
2.2e-8 or better in every run.

**Reading.** Doubling and quadrupling the initial energy sharpens the peak
gradient from 9.8 to 22.4, and the interface gets *weaker and shorter-lived*,
then fails to form at all. The entropy factor is a contrast between the hot
spot and its reference; a more energetic flow heats the whole box faster, so
the contrast collapses while the gradients grow. The cubic scaling measured
on the forced ring (THETA_THREE Add. 4) therefore came from the drive
maintaining a steady hot spot at a fixed place, not from gradients as such.

A local reference (Gaussian mean at l = .5 or 1.0) does not rescue it: the
hot band is wider than any reference scale small enough to avoid global
warming, so the contrast is smaller still and no interface forms. Cooling
(rate 2) restores formation at E0 = .6 but not the trend: lifetime under one
time unit and exchange on Gamma below the E0 = .3 value.

**Consequence for "always wins".** In transient, energetic flows the
three-factor theta with the published weights does not strengthen as
gradients sharpen; it weakens. The mechanism holds where a persistent heat
source keeps a contrast alive (the forced ring), which is the planetary
setting of the paper, and fails where the whole fluid heats together, which
is the blow-up setting. The kinetic factor, the one that tracks gradients
directly, tops out at 1.87 by construction (w_E = .4 under a square root)
and cannot carry the interface alone. Any regularity claim from theta
therefore needs a factor that follows gradients with weight comparable to
the entropy factor's .96 — a change to Table 1, not a change to the fluid.

Data: theta_tubes_48_nu0.02_k0.0_E*_results.json (suffixes refNone/ref0.5/ref1.0, cool0.0/cool2.0).

## Addendum: the second orthogonal plane — vorticity direction (theta_planes2.py) — 14 Sep 2026

Jonathan's question: the earlier work had two orthogonal planes, from rings
that rotate like a gyroscope; aligned, they form octants (walls). Only one
split had been used here (solenoidal / gradient). The fluid's second
orthogonal structure is the strain eigenframe: three mutually orthogonal
principal planes that rotate with the flow. When the vorticity direction xi
aligns with a principal axis the frame stops turning (octants lock); when it
is misaligned the strain tilts xi and the planes keep rotating. This is the
object of the Constantin-Fefferman theorem (1993): if xi varies smoothly
where |w| is large, the solution stays regular. Blow-up needs the direction
plane to rotate wildly at small scales.

Two kinetic-plane load ratios, built by the same recipe:

    magnitude plane   r_E = (w.S.w)^+ / (nu |grad w|^2)
    direction plane   r_R = |(I - xi xi^T) S xi| / (nu |grad xi|^2)
    alignment         a = |xi.S xi| / |S xi|   (1 = locked, 0 = fully tilting)

Isothermal antiparallel tubes, nu = .02, 48^3, E0 = .15 (dt .01) and .6
(dt .005), 99th percentile over cells with |w| > 5% of max.

| | E0 = .15 | E0 = .6 |
|---|---:|---:|
| peak gradient | 9.4 | 21.0 |
| r_E, 99th pct (peak over run) | 16.5 | 24.0 |
| r_R, 99th pct (peak over run) | 3.4 | 5.3 |
| mean alignment a, live cells | 0.56-0.62 | 0.54-0.61 |
| r_E in top-10% gradient / rest | 8-12 | 2-12 |
| r_R in top-10% gradient / rest | 1.1-2.3 | 1.1-3.0 |

**Both kinetic planes grow with the gradients; the thermal plane shrank.**
r_E rises 16.5 -> 24 and r_R rises 3.4 -> 5.3 as E0 quadruples, while the
entropy contrast fell (previous addendum). The magnitude plane is the
sharper locator (8-12x concentration in the top-gradient region); the
direction plane concentrates there too but more diffusely. Alignment sits
near 0.6 in both runs and drops slightly with E0: the planes rotate a little
more in the stronger flow, but the octant-locking level is nearly a fixed
statistic (as in turbulence, where vorticity prefers the intermediate strain
axis).

**What the weights do to it.** With Table-1 weights (f_E: w = .4, p = .8 under
a root; f_R given the temperature slot w = .6, p = 1) the two-plane product
is 2.44 at E0 = .15 and 2.78 at E0 = .6 (taken at the time of peak r_E): it grows with the gradients, in the
right direction, but does not reach pi. Removing the root and giving the
magnitude plane the entropy factor's weight (w p = .96) gives f_E = 4.05 at
E0 = .6 and a product of 6.9 (5.6 at E0 = .15). The evidence says: a theta that strengthens
with sharpening must be carried by the kinetic planes; whether that is done
by reweighting Table 1 or by treating the direction plane as the fourth
factor is a decision for the theory, not for the fluid.

Data: theta_planes2_E0.15_nu0.02_results.json, theta_planes2_E0.6_nu0.02_results.json.

## Addendum: the gyroscopic gate — octants lock under load (theta_gyro.py) — 14 Sep 2026

Frame rotation rate g = |(I - xi xi^T) S xi| / |S|_F (how fast the vorticity
direction turns, relative to the strain rate); alignment a (1 = locked).
Top = the 1% of live cells with the largest velocity gradient; rest = the
other live cells. Isothermal tubes, 48^3, nu .02.

| | E0 = .15, t = .6 / 1.0 / 2.0 | E0 = .6, t = .6 / 1.0 / 2.0 |
|---|---|---|
| alignment, top-1% gradient cells | .92 / .90 / .87 | .93 / .82 / .70 |
| alignment, rest | .59 / .57 / .59 | .55 / .57 / .55 |
| fraction locked (a > .9), top / rest | .65/.25, .66/.21, .41/.22 | .77/.20, .47/.23, .41/.20 |
| rotation rate g, top / rest | .06/.17, .11/.21, .13/.24 | .07/.25, .11/.27, .13/.30 |

**The planes lock where the load is.** In the cells with the sharpest
gradients the vorticity direction aligns with a strain axis (a ~ .9, 60-77%
fully locked) and the frame nearly stops turning (g ~ .1), while the rest of
the fluid stays at the generic turbulence value (a ~ .57, ~20% locked) and
its frame turns faster the stronger the flow (g_rest .17 -> .30). This is
Jonathan's "aligned planes make octants and become walls," observed directly,
and it is the geometric depletion of Constantin-Fefferman: at the collision
the nonlinearity is depleted by alignment. The locking is strongest early
(the collision) and relaxes as the flow decays (.93 -> .70 at E0 = .6).

**Gated candidates** (modified weights, labelled: magnitude plane w p = .96
without root; direction plane w = .6). 99th-percentile values, peak over run:

| candidate | E0 = .15 | E0 = .6 |
|---|---:|---:|
| C1 = fE fR (ungated) | 2.5 | 4.3 |
| C2 = 1 + (fE fR - 1) a  (walls where locked) | 2.0 | 3.3 |
| C3 = 1 + (fE fR - 1)(1 - a)  (load where turning) | 1.7 | 2.5 |

All three grow with E0, unlike the entropy form. The alignment-gated C2
crosses pi only in the strong case (3.3 vs 2.0): an interface that appears
where gradients concentrate *and* only under sufficient load — the behaviour
a sink should have. The rotation-gated C3 stays below pi. The ungated
product is largest but not localised by the frame. Where a cell's product
collapses (P_w = 0, the zero-divisor set) fE goes strongly negative under
the no-root weight; a floor (Jonathan's -pi) is needed there — the same
below-baseline issue as the entropy factor, now on the kinetic plane.

Data: theta_gyro_E0.15_results.json, theta_gyro_E0.6_results.json.

## Addendum: the third ring — pressure turns the strain frame, vorticity anchors it (theta_third_ring.py) — 15 Sep 2026

Jonathan: two rotating walls cannot both lay flat (one falls forward, the
other only sweeps); something at an angle, or a third ring on another axis,
must anchor them. Two rotation axes cannot reach every orientation and lose
a degree of freedom when they align (gimbal lock); the aligned state is the
octant state. The fluid's third rotation is the rotation of the strain
eigenframe itself, which from DS/Dt = -S^2 - W^2 - H + nu lap S turns at
rate (H_ij + (W^2)_ij)/(lam_i - lam_j) in its own frame: the pressure
Hessian H (first plane) and the vorticity W (second plane) both drive it.
Also tan(phi) = tilt/stretch of the vorticity direction (the tangent
operator; alignment a = cos phi), and cos(H,S) = alignment of the most
compressive axes of the pressure-Hessian and strain frames.
Medians over the top-1% gradient cells (load) and the rest (bulk); rates are
relative to the local strain rate. Isothermal tubes, 48^3, nu .02.

| | E0 = .15, t = .4 / .8 / 1.6 | E0 = .6, t = .4 / 1.2 / 2.0 |
|---|---|---|
| strain-frame turn rate, load, total | 2.6 / 1.5 / 1.0 | 1.1 / 2.0 / 4.5 |
| ... pressure part alone | 2.6 / 2.5 / 1.1 | 1.5 / 3.4 / 8.2 |
| ... vorticity part alone | 0.3 / 1.5 / 0.4 | 0.8 / 1.8 / 4.0 |
| strain-frame turn rate, bulk, total | 1.5 / 1.2 / 1.0 | 1.1 / 1.6 / 1.6 |
| ... vorticity part, bulk | .06 / .08 / .15 | .09 / .21 / .26 |
| cos(H,S), load | .02 / .08 / .07 | .09 / .11 / .08 |
| cos(H,S), bulk | .69 / .67 / .69 | .66 / .62 / .56 |
| tan phi, load | .60 / .43 / .36 | .48 / .51 / .62 |
| tan phi, bulk | 1.1 / 1.3 / 1.5 | 1.3 / 1.3 / 1.5 |

Three findings.

1. **At the load the pressure frame is orthogonal to the strain frame.**
   cos(H,S) ~ 0.02-0.11 in the top-gradient cells at every time and both
   energies, against 0.56-0.71 (about 45-50 degrees) in the bulk. The
   "something at an angle" that anchors the rotations is a right angle: the
   two planes are literally orthogonal where the load is, and generic
   elsewhere.

2. **The vorticity ring counter-rotates against the pressure ring.** The
   pressure Hessian alone would turn the strain frame at 2.5-8.2 at the load;
   the total is 1.0-4.5, always below the pressure part, with the vorticity
   part comparable in size. In the bulk the vorticity part is negligible
   (0.06-0.26) and the total equals the pressure part. So the third ring is
   inert in the bulk and active only under load, where it cancels a large
   fraction of the pressure-driven rotation. This is the anchoring Jonathan
   described, and it grows with E0 (vorticity part 0.3-1.5 -> 0.8-4.0).

3. **tan phi < 1 at the load, > 1 in the bulk.** The tangent operator
   (rotation of the vorticity direction over stretching along it) is
   0.36-0.62 where the load is and 1.1-1.5 elsewhere, stable across E0.
   In the Alpha paper's language: cot large = mass accumulates = frozen;
   the walls form where stretching outpaces rotation.

Caveats: medians over a top-1% cell set, one flow family, one grid, two
energies; the "cancellation" is |total| < |pressure part|, not a signed
decomposition along one axis; the eigenframe rate is singular where two
strain eigenvalues coincide (masked). None of this is a theta value yet; it
is the geometry of the frame under load, measured.

A fourth observer: the vorticity direction is a line (xi ~ -xi), so it
distinguishes 8/2 = 4 octant pairs of the three principal planes. That is
arithmetic, recorded because it was asked about, not evidence.

Data: theta_third_ring_E0.15_results.json, theta_third_ring_E0.6_results.json.

## Addendum: can the frame geometry alone nucleate the interface? (theta_frame_interface.py) — 15 Sep 2026

Criterion from the four frame numbers measured under load: F = a (alignment)
x o (pressure-strain orthogonality) x c (cot-share, stretch over rotation)
x A (third-ring anchoring fraction), each in [0,1]. Tested as a LOCATOR of
the load: Jaccard overlap between each score's top-1% cells and the top-1%
gradient cells. Tubes, 48^3, nu .02.

| score | Jaccard with load, E0 = .15 (t = .8 / 1.2 / 1.6) | E0 = .6 (t = .4 / .8 / 1.2) |
|---|---|---|
| r_E (magnitude plane) | **.46 / .48 / .36** | **.39 / .31 / .32** |
| C2 (alignment-gated theta) | .14 / .09 / .04 | .20 / .06 / .05 |
| F (geometry only) | .20 / .02 / .03 | .07 / .00 / .13 |
| alignment alone | .02 / .01 / .01 | .01 / .01 / .01 |
| orthogonality alone | .06 / .04 / .04 | .03 / .04 / .02 |
| anchoring alone | .06 / .02 / .03 | .00 / .00 / .07 |

Median F is 0.10-0.19 at the load and ~0 in the bulk, so F is *characteristic*
of the load, as the previous addenda found. But its top-1% set barely
overlaps the load: locked, orthogonal, anchored cells occur in many benign
places at low intensity (20% of the bulk is locked), so the geometry is
necessary-looking, not sufficient. The magnitude-plane ratio r_E is by a wide
margin the best locator; gating it by alignment (C2) makes it *worse* as a
locator, because alignment saturates to 1 in cells that are not loaded.

Conclusion: the interface must be nucleated by the magnitude plane (r_E,
production over destruction); the frame geometry describes *how* the load
looks (planes orthogonal, third ring anchoring, direction locked, cot > 1)
and can gate or weight it, but cannot find it. The pure-geometry reading
of "aligned walls form the interface" is not supported as a nucleation rule.

Data: theta_frame_interface_E0.15_results.json, theta_frame_interface_E0.6_results.json.
