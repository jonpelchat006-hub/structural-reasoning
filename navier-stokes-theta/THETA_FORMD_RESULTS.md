# Form D: magnitude-plane nucleation, geometry-gated sink, Q-R closure — 15 September 2026

Built from the evidence of THETA_TUBES_RESULTS.md: the interface must be
nucleated by the magnitude plane (r_E), the frame geometry gates the sink,
the field needs a floor at -pi, and J lives on the pressure exchange.
`theta_formD.py`. Isothermal antiparallel tubes, 48^3, nu = .02.

## Definition

    theta_s = 1 + 0.96 ln r_E          MODIFIED weight (entropy factor's w p, no root)
    theta_s, theta clipped to [-pi, pi]; wall at 3 (k = 1); relax-diffuse-advect, D = nu
    Gamma = { theta >= 3 }             (the wall onset; theta >= pi is unreachable once the
                                        source is clipped at pi and the field is smoothed)
    J: on Gamma remove power kappa * a * j^+     a = vorticity-strain alignment (gate),
                                                 j = -u.grad Pi (pressure-plane exchange)
    Q = |w|^2/4 - |S|^2/2, R = -det(grad u), D = 27 R^2/4 + Q^3     (velocity-gradient invariants)

## The relaxation time decides whether an interface can exist at all

With tau = 0.1 (all earlier runs) the dynamic field never reaches Gamma at
E0 = .6 (theta_max 3.04-3.07, 0-4 cells), although the static source has 388
cells pinned at pi and the dealiased static field still 200. Neither the wall
(identical results without it) nor advection (an Eulerian field is *lower*,
2.5-2.9) is the cause. The loaded structure moves through space at ~U, so at
any place — material or fixed — the load persists for about h/U ~ 0.06, less
than tau: the field leaves the source before it saturates. With tau = 0.02
the interface forms.

| E0 | tau | kappa | Gamma cells | Gamma in top-1% grad / top-1% in Gamma (t = .4/.6/.8) | j on Gamma (t = .4/.6/.8) | sink / E0 | peak vorticity |
|---:|---:|---:|---:|---|---|---:|---:|
| .6 | .1 | 0 | 0-4 | — | — | 0 | 30.66 |
| .6 | .02 | 0 | 74-114 | .48/.38/.35 ; .43/.26/.35 | 7.7 / 4.0 / 3.7 | 0 | 30.66 |
| .6 | .02 | 1 | 78-100 | .38/.38/.54 ; .35/.32/.37 | 9.4 / 7.0 / 9.1 | 1.64% | 28.66 (-6.5%) |
| .15 | .02 | 1 | 70-90 | .00/.00/.51 ; .00/.00/.33 | 2.6 / 2.4 / 2.2 | 0.92% | 12.73 (-0.0%) |

Energy accounting (kinetic + dissipation + sink = E0) closes to 1.5e-8 or better.

**Reading.** With a fast field the interface nucleates on the load: a third
to a half of Gamma lies in the top-1% gradient cells and a third of those
cells are in Gamma (Jaccard-level agreement ~0.2-0.3, the best of any
dynamic theta so far). The exchange on Gamma is positive and large (4-9 vs a
bulk |j| of ~0.1), and draining Gamma raises the delivery into it (7.7 -> 9.4
at t = .4), the same feedback seen on the forced ring. The sink share grows
with load (0.92% -> 1.64% of E0) and trims the peak vorticity by 6.5% at
E0 = .6 while leaving E0 = .15 untouched. The direction is right; the
magnitude is small because Gamma is ~100 cells of 110k and the gate a ~ .9.

Form D is *not* silent at low load: with the modified weight the static
p99 of theta_s is 3.7 already at E0 = .15, so Gamma forms there too (though
it misses the load until t = .8). A weight that makes pi require the strong
case would sit between Table 1's 0.4 (never) and 0.96 (always); it is a
theory choice, and tau is a second one this test has now forced.

## The closure diagnostic (quaternions and the Q-R plane)

The velocity gradient A = S + W has a closed invariant description: with
tr A = 0 its characteristic polynomial is fixed by Q and R, and the sign of
D = 27R^2/4 + Q^3 separates vortical (D > 0, complex eigenvalues) from
strain-dominated (D < 0) cells. The vorticity is the pure quaternion of W
(W^2 acts as the quaternion square, -|w|^2 up to the projector); the strain
frame is a unit quaternion and the third-ring rate is its derivative. The
restricted-Euler closure (isotropic pressure Hessian; Vieillefosse 1982)
blows up in finite time along the tail D -> 0, R > 0; the true pressure
Hessian, anisotropic, prevents it (Chevillard-Meneveau). Our measured
orthogonality of the pressure and strain frames at the load is that
anisotropy, seen directly.

Measured, both E0, all times: the top-1% gradient cells have **D > 0 in 100%
of cases** (D < 0 fraction 0.00-0.03) — vortical, never on or near the
Vieillefosse tail — with R > 0 during the collision (t <= .6: compressing)
and R < 0 afterwards (stretching). The bulk is generic (~50% D < 0, ~45-65%
R > 0). So the load in this flow does not take the restricted-Euler route
to a singularity, and the third ring is the reason the closure that would
blow up does not apply. Whether the Cayley-Dickson closure ladder of the
theory adds anything beyond this quaternion bookkeeping is not tested; the
honest position is that quaternions are the right *representation* for the
frame (orientation, rates, Q-R plane), and the fluid's own closure problem
— the pressure Hessian — is where the theory's "closure equation" has a
physical counterpart.

Data: theta_formD_E*_results.json. Code: [theta_formD.py](theta_formD.py).

## Addendum: pushing the Reynolds number (cloud runs, 15 Sep 2026)

Same Form D (theta_s = 1 + 0.96 ln r_E, clip [-pi, pi], wall 3, Gamma = theta >= 3,
sink kappa a j^+ on Gamma, tau = .02), E0 = .6, dt = .005, t <= 1.6, run in a
2-core cloud container (64^3: 1.4 s/step; 96^3: 6.4 s/step). Resolution was
chosen so k_eta stays below k_max: 64^3 for nu = .02 and .01, 96^3 for
nu = .007. Energy accounting closes to 2.8e-8 or better in every run.
Reynolds number U L / nu ~ 100-300: an enstrophy-GROWING regime (stretching
beats dissipation over the whole window at nu <= .01), not yet a regime
where Navier-Stokes is hard.

| n | nu | peak enstrophy, control -> sink | peak vorticity, control -> sink | sink / E0 | Gamma (max cells, % vol) | Gamma in top-1% grad (t = .4/.8/1.2) | D < 0 at load (max) |
|---:|---:|---|---|---:|---|---|---:|
| 64 | .02 | 3.945 -> 3.934 (-0.3%) | 33.6 -> 30.6 (-9%) | 0.71% | 292 (0.11%) | .43/.34/.74 ; sink .07/.26/.90 | .03 |
| 64 | .01 | 6.115 -> 5.823 (-4.8%) | 58.5 -> 51.3 (-12%) | 2.22% | 490 (0.19%) | .17/.47/.13 ; sink .07/.23/.15 | .05 |
| 96 | .007 | 8.141 -> 7.633 (-6.2%) | 74.5 -> 69.5 (-7%) | 1.72% | 2040 (0.23%) | .00/.20/.10 ; sink .01/.05/.11 | .15 (transient), else ~0 |

Enstrophy in time at nu = .007, control vs sink: 4.28/4.27 (t=.2), 5.13/5.04 (.6),
6.40/6.15 (1.0), 7.03/6.69 (1.2), 8.14/7.63 (1.6): the suppression grows from
0.3% to 6.2% as the growth proceeds. At nu = .01: 4.20/4.16 -> 5.96/5.63.

**What holds up as Re rises.** The sink's effect on enstrophy growth
increases monotonically with Reynolds number (-0.3%, -4.8%, -6.2%) and, at
fixed nu, increases through time as the load builds. The J channel is
positive on Gamma during nucleation (10.5, 6.0, 2.5 at t = .4) and draining
Gamma raises delivery into it at nu = .01 (5.96 -> 7.68). The loaded cells
remain vortical (D > 0) except for a transient 10-15% at nu = .007 during
the collision; the restricted-Euler route is still not taken. The 64^3
control reproduces the 48^3 peak enstrophy to 0.03%.

**What does not.** The interface dilutes: Gamma grows from 0.1% to 0.23% of
the volume and its overlap with the top-1% gradient region falls from ~0.4
to ~0.1 as nu drops. With the 0.96 weight the field saturates over a
broad band at higher Re, so Gamma is no longer a thin interface on the
load; the sink's share of energy is not monotonic (0.71 -> 2.22 -> 1.72%)
partly for that reason and partly because the 96^3 grid resolves a thinner
band. A weight or threshold that keeps Gamma thin as Re rises is the open
modelling question; the theory's wall/threshold structure (3, pi, the
pi - 3 cushion) is the natural place to put it.

Files: theta_formD_n{64,96}_nu*_E0.6_k*_tau0.02_results.json, log_*.txt,
theta_formD.py (now takes --nu, --n, --tau, --eulerian, --nowall).

## Addendum: a two-sided interface — the bubble (theta_bubble.py) — 16 Sep 2026

Jonathan: when theta hits pi something else should happen — the parts above pi
leak into a second bubble with its own coordinates; the interface is
double-sided. Standing mathematics for each piece: the paper's own Prop. 1
jump condition [[kappa d_n theta]] = J is a two-sided flux balance; the
inner problem of Appendix A (stretched coordinate zeta = dist/eps) is a
bubble with its own axes; Leray's self-similar ansatz is the same bubble for
Navier-Stokes, and Necas-Ruzicka-Sverak (1996) rule out a nontrivial one;
Tao's averaged-NS blow-up and the Luo-Hou Euler scenario are chains of such
bubbles (a subcircuit added at each scale); in turbulence modelling the
sub-grid energy equation is a reservoir with its own dynamics and
backscatter (energy leaking back). The bubble is sub-grid at our resolution.

Test: the one-sided sink of Form D is replaced by a reservoir E_b.
dE_b/dt = J_in - E_b/tau_b; a fraction beta_b of the outflow returns to the
flow on Gamma as a velocity increment along u (backscatter), the rest is
bubble dissipation. Accounting E + E_b + dissipated + bubble-dissipated = E0
closes to 1.4e-8. 64^3, nu = .01, E0 = .6, tau = .02, kappa = 1, tau_b = .2.

| model | peak enstrophy | peak vorticity | energy through Gamma | returned | bubble-dissipated |
|---|---:|---:|---:|---:|---:|
| control | 6.115 | 58.5 | 0 | 0 | 0 |
| one-sided sink (energy vanishes) | 5.823 (-4.8%) | 51.3 (-12%) | 1.33e-2 | 0 | — |
| two-sided, half return (beta_b = .5) | 5.923 (-3.1%) | 51.9 (-11%) | 1.23e-2 | 3.8e-3 | 7.5e-3 |
| two-sided, full return (beta_b = 1) | 6.028 (-1.4%) | 53.8 (-8%) | 1.17e-2 | 1.0e-2 | 0 |

Enstrophy at t = 1.6: control 6.115, one-sided 5.823, half 5.92, full 6.028.

**Reading.** Making the interface two-sided costs most of the enstrophy
suppression in proportion to what is returned (-4.8% -> -3.1% -> -1.4%),
but the peak-vorticity reduction survives better (-12% -> -11% -> -8%):
energy that goes through the bubble and comes back comes back *smoother*
— the interface redistributes it along the local velocity rather than at
the gradient peak. With full return the two-sided interface is close to
neutral on the integrated load and still an 8% cap on the pointwise
extreme. The bubble's own coordinates are not modelled here (the reservoir
is a scalar with a decay time); a bubble with structure — its own
production and transport, an inner frame composed with the outer — is the
sub-grid energy equation, and would be the next model if this direction is
pursued. Whether the bubble should dissipate (beta_b < 1) or only redirect
(beta_b = 1) is the theory's "different material on the return leg"
question in fluid form.

Data: theta_bubble_n64_nu0.01_k1.0_taub0.2_betab{1.0,0.5}_results.json. Code: theta_bubble.py.

## Addendum: a chain of bubbles along a line, and single-sided ends (theta_chain.py) — 16 Sep 2026

Jonathan: a blow-up along a void line would be a chain of bubbles with the
void line running between them; a finite chain would have single-sided walls
at its two ends. The fluid version is the Crow-type multi-site pinching of
antiparallel tubes: a k-wavelength perturbation pinches at k sites along the
line. Two cases, 64^3, nu = .01, E0 = .6, Form D nucleation (passive,
tau = .02), Gamma = theta >= 3, connected components by scipy.ndimage.label
(no periodic wrap, so a bubble at x = 0 appears as two halves):

  chain3  a cos(3x) perturbation, periodic  -> 3 sites, no ends (control for ends)
  ends2   a cos(2x) under a Gaussian envelope of width 1.2 about x = pi
          -> 2 sites with quiet tube beyond: a finite chain with free ends

Each pinch site nucleates a mirror pair of bubbles (one per tube). Sizes
below are the larger components (>= 20 cells); j_lo / j_hi are the mean
pressure-plane exchange in the low-x and high-x halves of each bubble.

**chain3 (periodic, no ends).** At t = .2 six sites load (both extrema of
cos 3x); by t = .6-1.0 three survive at x = 0, 2.10, 4.19 — spacing 2 pi/3,
one per wavelength — each 23-25 cells. Every large bubble has symmetric
halves at every time: (68.2, 67.9), (-34.2, -30.6), (-10.6, -11.3),
(-9.6, -10.1), (-2.9, -3.3). A periodic chain has no one-sided walls.

**ends2 (finite chain).** t = .2: two bubbles at x = 1.74 and 4.56 (62 and
61 cells), symmetric halves (7.9/7.6, 7.1/7.9). From t = .4 the chain has a
centre bubble and flanking bubbles, and the flanks are one-sided with
mirror symmetry:

| t | inner bubble(s), (j_lo, j_hi) | left flank | right flank |
|---|---|---|---|
| .4 | x=2.11 (-5.7, -5.6); x=4.17 (-5.6, -5.7) | x=1.14 (+1.0, -2.9) | x=5.14 (-3.0, +1.1) |
| .6 | x=3.14 (-22.0, -25.3), (-17.0, -15.9) | x=1.93 (-9.5, -16.3) | x=4.32 (-18.7, -9.3) |
| .8 | x=3.14, 94 cells (-9.3, -10.7) | x=2.20 (-6.4, -17.9) | x=4.08 (-16.3, -6.4) |
| 1.0 | x=3.14, 87 cells (-13.0, -13.1) | — | — |

The inward-facing half of each end bubble extracts 2-3x more strongly than
the outward-facing half (or the outward half even delivers, +1.0/+1.1 at
t = .4), and the pattern is an exact mirror across the chain centre. The
centre bubble, which has neighbours on both sides, is symmetric to a few
percent. This is the single-sided wall at the chain ends, observed, with
the periodic chain as the control in which it does not occur.

**Void lines between the bubbles.** Correlation along x between the Gamma
density and the zero-divisor-channel density (P ~ 0 with live w, S), 12
slices: negative while the chain forms — chain3 t = .2: -0.35; ends2 t =
.2/.4/.6: -0.71/-0.45/-0.57 — then near zero or positive once the flow
decays and mixes (chain3 t = 1.2-1.4: +0.6/+0.7). So during nucleation the
channels do run between the bubbles, as proposed, and the earlier finding
(the interface is never *on* a channel) is the same fact from the other
side. Later the chain does not close into a line in this window; the
bubbles at the far sites dissolve and only the centre survives.

Caveats: one grid, one nu, coarse 12-slice profiles, no periodic wrap in
the labelling, small bubbles (20-90 cells). The component halves are a
crude split; a proper flux through each bubble's two faces would be the
next diagnostic.

Data: theta_chain_chain3_results.json, theta_chain_ends2_results.json, log_chain3.txt, log_ends2.txt. Code: theta_chain.py.

## Addendum: the flux through each bubble's two faces (theta_faces.py) — 16 Sep 2026

For incompressible flow the pressure-plane exchange is a divergence,
-u.grad Pi = -div(Pi u), so the exchange integrated over a bubble equals the
inward flux of the current Pi u through its boundary. Per bubble (connected
component of Gamma, now merged across the periodic boundary) we report the
inward flux of Pi u through the faces whose outward normal is -x (P_lo,
looking toward smaller x) and +x (P_hi), and their symmetry
s = min(|P_lo|,|P_hi|)/max(|P_lo|,|P_hi|): s = 1 is a two-sided bubble,
s -> 0 a single-sided one. 64^3, nu = .01, E0 = .6, Form D nucleation.

**Periodic 3-site chain (no ends).** Every bubble is two-sided:

| t | bubbles (x, cells): P_lo / P_hi, s |
|---|---|
| .2 | 1.06 (54): +.142/+.128, .90 · 2.12 (62): +.129/+.208, .62 · 3.14 (38): +.153/+.153, 1.00 · 4.16 (62): +.208/+.129, .62 · 5.22 (54): +.128/+.142, .90 · 0 (56): +.136/+.136, 1.00 |
| .6 | 2.10 (23): -.144/-.150, .96 · 4.19 (23): -.150/-.144, .96 · 0 (16): -.100/-.100, 1.00 |
| 1.0 | 2.10 (25): -.082/-.086, .95 · 4.19 (25): -.086/-.082, .95 · 0 (21): -.075/-.075, 1.00 |

**Finite 2-site chain with free ends.** The centre bubble is two-sided to
three digits; every flanking bubble is single-sided, in exact mirror pairs:

| t | centre bubble x = 3.14 | flanking bubbles: P_lo / P_hi, s |
|---|---|---|
| .4 | — | 1.14: +.154/-.031, .20 · 2.11: -.035/+.497, .07 · 4.17: +.498/-.035, .07 · 5.14: -.032/+.155, .21 |
| .6 | -.004/-.004, .94 and -.031/-.031, 1.00 | 1.93: +.123/+.512, .24 · 2.36: +.187/-.062, .33 · 3.93: -.062/+.188, .33 · 4.32: +.653/-.002, .00 |
| .8 | -.208/-.208, 1.00 | 2.06: -.112/+.474, .24 · 2.21: -.012/+.374, .03 · 4.07: +.429/-.098, .23 · 4.22: +.475/-.112, .24 |
| 1.0 | -.503/-.494, .98 | (dissolved) |
| 1.2 | -.347/-.347, 1.00 | (dissolved) |

The inner pair at t = .4 (x = 2.11 and 4.17) receives +0.50 through the
face that looks toward the chain centre and -0.03 through the face that
looks away: energy enters the end bubbles from the chain side only, 14x
asymmetry. The bubble that wraps through x = 0 (the quiet tube, which has
neighbours on both sides by periodicity) is two-sided (s = .95-.98), as it
should be. The kinetic-energy current (|u|^2/2) u shows the same pattern
(centre -.929/-.930 at t = .8; flanks asymmetric with sign flips).

This makes the earlier half-split result quantitative: a bubble with a
neighbour on each side exchanges symmetrically through both faces; a
bubble at the end of a chain exchanges through one face. The single-sided
wall is a property of chain position, not of the bubble.

Caveats: the volume integral of the spectral -div(Pi u) and the
central-difference face sum differ by up to a factor 2 on the smallest
bubbles (different discrete divergences); the *ratio* between a bubble's two
faces uses one consistent discretisation and is the quantity reported. One
grid, one nu; bubbles of 15-94 cells.

Data: theta_faces_chain3_results.json, theta_faces_ends2_results.json, log_faces_*.txt. Code: theta_faces.py.

## Addendum: the carried weight (theta_carried.py) — 17 Sep 2026

Jonathan: the weight is not a constant; it is carried between the base plane,
the walls and the third ring, and shifts as the ring lifts the walls. The
measurable version: A = (pressure-driven frame rotation - total) / pressure-
driven, the share of the strain frame's rotation carried by the vorticity
ring rather than the pressure base (~0 in the bulk). Carried weight
w = w_base + (w_wall - w_base) A with w_base = 0.4 (Table 1) and w_wall = 0.96
(the entropy weight). Static theta_s = 1 + w ln r_E compared for fixed 0.96,
fixed 0.7, and carried; Gamma_static = {theta_s >= pi}. 64^3, nu = .02.

**Correction first.** The earlier statement "A ~ 0.4-0.5 at the load" was a
ratio of medians (median pressure rate minus median total, over median
pressure) — a collective property of the loaded region. The per-cell median
of A in the top-1% gradient cells is intermittent: 0.01-0.40 (E0 = .15),
0.01-0.41 (E0 = .6). The ring's cancellation is a property of the loaded
region as a whole, not of each cell in it.

| E0 | t | per-cell A at load | carried w at load | fixed 0.96: vol / J / coverage | fixed 0.7 | carried |
|---:|---:|---:|---:|---|---|---|
| .15 | .8 | .40 | .62 | .127% / .40 / .65 | .053% / .40 / .44 | .023% / .21 / .22 |
| .15 | 1.2 | .22 | .52 | .166% / .40 / .70 | .037% / .25 / .26 | .006% / .00 / .00 |
| .6 | .4 | .24 | .54 | .229% / .25 / .75 | .102% / .28 / .49 | .037% / .17 / .21 |
| .6 | 1.2 | .32 | .58 | .187% / .30 / .64 | .056% / .19 / .25 | .026% / .18 / .19 |
| .6 | 1.4 | .41 | .63 | .243% / .19 / .51 | .055% / .21 / .26 | .023% / .16 / .17 |

(vol = Gamma_static volume fraction; J = Jaccard with the top-1% gradient
cells; coverage = fraction of those cells inside Gamma.)

**Per-cell carried weight: silent at low load, and nearly silent at high
load.** It never lifts w above ~0.63 in the loaded cells, so Gamma_static
stays at 0.00-0.04% of the volume and covers at most 21% of the load at
E0 = .6. As a nucleation weight it is too weak: the ring does not carry
enough per cell to reach pi.

**Collective carried weight: a global w(t) that discriminates, marginally.**
Using the region-level A (from the third-ring medians): E0 = .15 gives
w = 0.40-0.62 against a required 0.79-0.91 for pi (never reaches); E0 = .6
gives w = 0.40-0.66 against a required 0.67-0.82 (reaches or nearly at
t = .4 and 2.0). So "the weight shifts through the cycle" as a *global*
statement — the whole loaded region carries more on the ring when the load
is strong — does separate the two cases, in the right direction, by a small
margin. It lands in the 0.67-0.77 window derived independently from
requiring pi between the two energies, which is why it is worth recording;
but it is a two-point, one-family, marginal agreement, not a derivation.

**Fixed 0.7 for comparison** fires at both energies (0.03-0.05% vs
0.04-0.10% of volume) with better coverage at high load; it is not silent
at low load either. Fixed 0.96 has the best coverage and the worst dilution.

Reading: the carried-weight idea is right in kind — the load *is*
distributed between base, walls and ring, and the distribution shifts with
load — but per cell the ring's share is too intermittent to be the weight.
If the theory wants the weight carried, it should be carried at the level of
the interface (a property of Gamma as a body), not of the cell; that is the
same lesson as the bubble: the object with its own state is the region, not
the point.

Data: theta_carried_E0.15_results.json, theta_carried_E0.6_results.json. Code: theta_carried.py.

## Addendum: three lines from the origin — the degeneracy weight (theta_lines.py) — 17 Sep 2026

Jonathan: the planes are anchored at the origin and the third ring; when
they rotate one lies on top of the other and transfers its weight; a line
from the outer ring to the origin can drop; three such lines, one per plane,
end up lying on top of each other. The fluid objects: the three principal
axes of the strain with eigenvalues l1 >= l2 >= l3 (sum zero: the base plane
is the constraint). Two lines lying on top of each other is a degenerate
strain, measured by the Lund–Rogers strain state
s* = -3 sqrt6 l1 l2 l3 / (l1^2 + l2^2 + l3^2)^{3/2} in [-1, 1]:
s* = +1 is l1 = l2 > 0 > l3 = -2 l1 (two extensional lines coincide; a
sheet-forming, biaxial strain), s* = -1 is l1 > 0 > l2 = l3 (two compressive
lines coincide; a tube-stretching strain), s* = 0 is plane strain. The
position of the middle line between the extremes is beta = (l2 - l3)/(l1 -
l3). The anchor is the axis the vorticity direction lies along.
Candidate carried weights: w_deg = 0.4 + 0.56 |s*|, w_beta = 0.4 + 0.56 beta.
Static Gamma test as before (Gamma = {theta_s >= pi}, Jaccard and coverage
of the top-1% gradient cells). 64^3, nu = .02.

| E0 | t | s* load / bulk | beta load / bulk | anchor at load (l1, l2, l3) | w_deg load / bulk | w_deg: vol, J, cov | fixed 0.7: vol, J, cov |
|---:|---:|---|---|---|---|---|---|
| .15 | .4 | -.25 / -.09 | .43 / .47 | 0, 1.00, 0 | .54 / .55 | .028%, .00, .00 | .016%, .00, .00 |
| .15 | .8 | **+.97** / -.11 | .92 / .47 | .15, .85, 0 | .95 / .58 | .092%, .42, .57 | .053%, .40, .44 |
| .15 | 1.0 | +.95 / -.09 | .89 / .47 | .07, .93, 0 | .93 / .59 | .125%, .42, .65 | .051%, .41, .43 |
| .15 | 1.4 | +.89 / .00 | .83 / .50 | .03, .97, 0 | .90 / .62 | .122%, .30, .46 | .029%, .14, .16 |
| .6 | .4 | **+.92** / -.12 | .85 / .46 | 0, 1.00, 0 | .91 / .57 | .166%, .31, .70 | .102%, .28, .49 |
| .6 | .8 | +.72 / +.06 | .74 / .52 | 0, 1.00, 0 | .81 / .63 | .161%, .23, .49 | .057%, .17, .23 |
| .6 | 1.2 | +.78 / +.22 | .77 / .56 | .12, .88, 0 | .84 / .70 | .131%, .23, .42 | .056%, .19, .25 |

**Three findings.**

1. **Two lines lie on top of each other at the load.** From the collision
   onward the loaded cells have s* = +0.65 to +0.97 (l1 ~ l2 > 0, l3 ~ -2 l1),
   against -0.1 to +0.3 in the bulk. The two extensional planes have merged
   into one and the third line — the strong compression — has dropped. The
   bulk drifts toward degeneracy as the stronger flow decays (0.3 -> 0.55),
   which is the dilution mechanism seen at high Re.

2. **The vorticity is anchored to the intermediate line, always.** 75–100%
   of loaded cells and 65–96% of bulk cells have the vorticity direction along
   e2 — the classical turbulence alignment, reproduced in a collision. At the
   load, where e1 and e2 have merged, the vorticity therefore lies in the
   plane of the two coincident lines: the ring is anchored to the merged
   pair, not to the dropped line. Three lines cannot all coincide (they sum
   to zero); two do, and the ring sits on them.

3. **The degeneracy weight works as a carried weight.** w_deg = 0.4 +
   0.56 |s*| is 0.8–0.95 at the load and 0.55–0.70 in the bulk — it is high
   exactly where the lines have merged — and as a locator it beats fixed 0.7
   at every time (coverage .42–.70 vs .16–.49; Jaccard .23–.42 vs .14–.41)
   with less volume than fixed 0.96 (.09–.17% vs .13–.28%). w_beta is
   equivalent (beta and |s*| carry the same information here); the inverse,
   0.4 + 0.56 (1 - beta), kills the interface, so the direction is not
   arbitrary. It is not silent at low load: the E0 = .15 collision is a real
   load with merged lines, and the weight says so.

This is the first weight that is *measured from the frame* rather than
chosen: the base value 0.4 (Table 1) when the three lines are distinct and
the base carries everything, rising to the entropy weight 0.96 as two of
them merge and the walls carry the load. It replaces the "0.7" of the
parameter table with a rule. Caveats: one grid, one nu, two energies; the
0.4 and 0.96 endpoints are Table 1's numbers, not derived; whether the
merged-line criterion keeps Gamma thin as Re rises is untested (the bulk
|s*| rises with Re, so it may not by itself).

Data: theta_lines_E0.15_results.json, theta_lines_E0.6_results.json. Code: theta_lines.py.
## Addendum — three rings, three radii, three rates (theta_rings.py, 17 Sep 2026)

Question (Jonathan): the three rings would have different radii and turn at their own rates — base fastest, walls slower —
each with a count of turns before the set-up comes back to "straight"; different lengths that wrap round to become equal;
rational (periodic return) or irrational ratios?

Mapping: ring k = rotation of the strain frame about principal line k, rate Ω_k = |M_ij|/|λ_i−λ_j| (i,j≠k),
M = pressure Hessian + W² in the strain frame, normalised by |S|. Radius of line k = |λ_k|/|S|. 48³, ν=.02, tubes IC,
load = top 1 % of |∇u| among live cells.

| E₀ | t | region | rate about c / i / e | fastest ring c / i / e | radii c / i / e | 2nd/fastest | lock (ctrl) |
|---|---|---|---|---|---|---|---|
| .15 | 0.4 | load | .27 / 2.55 / .03 | 0 / 1.00 / 0 | .66 / .08 / .74 | .11 | .18 (.43) |
| .15 | 0.8 | load | .94 / .70 / .36 | .50 / .43 / .07 | .81 / .34 / .47 | .56 | .31 (.44) |
| .15 | 1.2 | load | .46 / .78 / .20 | .19 / .81 / 0 | .81 / .31 / .50 | .62 | .51 (.40) |
| .15 | 2.0 | load | .30 / .95 / .12 | .23 / .77 / 0 | .80 / .26 / .54 | .36 | .48 (.45) |
| .15 | 2.0 | bulk | .28 / .62 / .30 | .21 / .59 / .21 | .72 / .13 / .69 | .38 | .44 (.45) |
| .6 | 0.4 | load | .56 / .49 / .25 | .41 / .59 / 0 | .81 / .31 / .50 | .57 | .61 (.41) |
| .6 | 1.2 | load | .68 / 1.69 / .44 | .23 / .74 / .03 | .79 / .21 / .58 | .35 | .42 (.44) |
| .6 | 2.0 | load | 2.17 / 2.58 / 1.04 | .42 / .48 / .09 | .74 / .15 / .67 | .41 | .46 (.42) |
| .6 | 2.0 | bulk | .67 / .78 / .42 | .36 / .45 / .20 | .76 / .16 / .64 | .42 | .44 (.45) |

c/i/e = compressive / intermediate / extensional line. "lock" = fraction of cells whose (2nd fastest)/(fastest) ratio lies
within .02 of a rational p/q, q≤6; ctrl = same statistic for uniform random ratios.

Findings
1. **Yes — three different radii and three different rates.** The intermediate line is short (radius .08–.34) and the
   compressive and extensional lines are long and nearly equal (.65–.8). The rates differ by 3–10×.
2. **The fast ring is the one about the intermediate line — the line the vorticity is anchored to** (fastest 60–100 % of
   cells, both regions, both E₀). So "base rotates fastest" holds if the base is the vorticity/intermediate line; the two
   walls (rings about the compressive and extensional lines) are the slow ones. In the bulk this is set by the pressure
   Hessian coupling between the two long lines, not by their lengths.
3. **Wrapping to equal length spins a ring up.** When the intermediate and extensional lines merge (s*→+1, λ₁≈λ₂ — the
   LINES result), the ring about the *compressive* line accelerates: at E₀=.6 its rate goes .12 → .68 → 1.55 → 2.17 from
   t=.8 to 2.0 and takes over as fastest in ~40 % of load cells. That is the third-ring divergence seen earlier, now
   attributed to a specific pair of lines becoming equal. Note the radii table uses |λ|, so the "equal" pair there
   (c and e, |λ₀|≈|λ₂|) is the pure-shear pair, not the signed-degenerate pair that drives the rate.
4. **Ratios are not equal and not locked.** 2nd/fastest sits at .1–.6 (median ≈ .4), never near 1. The rational-lock
   fraction in the bulk equals the random control exactly (.44 vs .45) at every time — the ratio is generic
   ("irrational"): no periodic return to the straight set-up, the frame never repeats. At the load the lock fraction
   scatters above and below control (.18–.61 vs .40–.46); two snapshots (E₀=.6 t=.4: .61/.41; E₀=.15 t=1.2: .51/.40)
   are above, others below. Not established; if there is a lock it is load-only and weak, and needs a larger sample.
5. Rates are local and time-varying (they are set by the instantaneous pressure Hessian), so "number of turns before
   straight" is not a fixed integer anywhere in the flow; the nearest meaningful version is the ratio distribution above.

Ledger: (1)–(3) established at 48³ (two E₀, five times); (4) irrational/generic in bulk established, load lock open;
(5) reframing. Files: theta_rings.py, theta_rings_E0.15_results.json, theta_rings_E0.6_results.json, logs.
## Addendum — degeneracy weight carried in Form D, and the ring lock at 96³ (theta_formD_weight.py, theta_rings.py; 17 Sep 2026)

### A. Degeneracy weight as the θ-source weight (theta_formD_weight.py)
θ_s = 1 + w(x) ln r_E with w = 0.4 + 0.56|s*| carried (a) per cell, (b) per Γ bubble (bubble = connected component of
the previous step's Γ dilated one cell; each bubble takes its mean cell weight; cell weight elsewhere). Same protocol as
the Re-trend runs: 64³, E₀=.6, κ=1, τ=.02, wall 3, T=1.6. Baselines: κ=0 peak Ω 3.9447 (ν=.02), 6.1153 (ν=.01);
fixed w=.96 with κ=1: −0.28 % / −4.78 %, sink 0.75 % / 2.31 % of E₀, Γ 200–500 cells.

| ν | weight | peak Ω | vs κ=0 | sink /E₀ | Γ cells (t=.2…1.6) | w on Γ / bulk | Γ∩top-1 % |
|---|---|---|---|---|---|---|---|
| .02 | fixed .96 | 3.9336 | −0.28 % | 0.75 % | 224 → 258 | .96 / .96 | — |
| .02 | cell | 3.9447 | 0.00 % | 0.08 % | 38, 6, 12, 8, … 64 | .78–.93 / .56–.70 | 0–.67 |
| .02 | bubble | 3.9446 | 0.00 % | 0.08 % | ~same, 4–18 bubbles | .78–.84 / .56–.70 | 0–.50 |
| .01 | fixed .96 | 5.8230 | −4.78 % | 2.31 % | 490 → 210 | .96 / .96 | — |
| .01 | cell | 6.0374 | −1.27 % | 0.66 % | 60–92 | .82–.85 / .64–.69 | 0–.70 |
| .01 | bubble | 6.0471 | −1.12 % | 0.69 % | 80, 34 bubbles | .78 / .69 | 0 |

Energy closure ≤ 2e-8 in all runs.

Finding: **carried into the source, the measured weight weakens the sink, it does not sharpen it.** Since w ≤ .96
everywhere, θ_s is lower everywhere and Γ shrinks 4–8× (6–92 cells vs 200–500), so the sink energy drops ~3× and the
peak-enstrophy reduction goes −0.28 → 0.00 % (ν=.02) and −4.78 → −1.2 % (ν=.01). Per-bubble vs per-cell makes no
difference (6.047 vs 6.037). The weight's demonstrated value (LINES) was as a *locator at fixed volume*; as an amplitude
in θ_s it is a volume knob, and the comparison above is confounded by Γ volume. A matched-volume test (lower the wall or
renormalise w so Γ has the fixed-weight volume) is the open item; until then the fixed .96 remains the Form D default.
Ledger: "degeneracy weight sharpens the sink" — **falsified as run**; matched-volume version — open.

### B. Ring lock at 96³ (theta_rings.py --n 96, E₀=.6, dt=.005, top 1 % of live cells ≈ 9 000 cells)

| t | region | rate about c / i / e | fastest c / i / e | radii c / i / e | 2nd/fastest | lock (ctrl) |
|---|---|---|---|---|---|---|
| 0.4 | load | .30 / .71 / .16 | .15 / .84 / .01 | .81 / .30 / .51 | .39 | .45 (.46) |
| 0.8 | load | .15 / 1.31 / .10 | .16 / .84 / 0 | .79 / .22 / .57 | .22 | .35 (.46) |
| 1.2 | load | 2.59 / 2.59 / .74 | .51 / .44 / .05 | .80 / .24 / .56 | .41 | .44 (.46) |
| 1.6 | load | 2.45 / 3.07 / .91 | .42 / .46 / .12 | .77 / .16 / .61 | .39 | .48 (.45) |
| 2.0 | load | 1.99 / 3.42 / .90 | .34 / .54 / .11 | .75 / .15 / .65 | .43 | .42 (.46) |
| 0.4–2.0 | bulk | .14–.64 / .60–.92 / .18–.45 | i fastest .46–.76 | .69–.76 / .09–.16 / .65–.72 | .26–.43 | .41–.45 (.45) |

Findings: (1) **No rational lock at the load.** With 8× the sample of the 48³ run the load lock fraction is .35–.48
against a control of .45–.46 — the 48³ values of .61 and .51 were noise. Ring-rate ratios are generic (irrational);
the frame never returns periodically to the straight set-up, at the load or in the bulk. Closed. (2) The rest of the
48³ picture holds at 96³: intermediate (vorticity) ring fastest in the bulk (.46–.76) and early at the load (.84);
compressive ring spins up as the lines merge (rate .15 → 2.6 → 2.0, fastest share .15 → .51), radii c/i/e ≈ .8/.2/.6;
ratio of second-fastest to fastest ≈ .4. E₀=.15 at 96³ not run (the lock question is answered by the E₀=.6 sample).

Files: theta_formD_weight.py, theta_formD_weight_{cell,bubble}_n64_nu{0.02,0.01}_k1.0_results.json and logs;
theta_rings.py (now with checkpoint/resume), theta_rings_E0.6_n96_results.json, theta_rings_E0.6_n96.log.
