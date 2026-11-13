# Form B with all three factors live — 13 September 2026

Follow-on to THETA_KINETIC_RESULTS.md, which found that an isothermal fluid
cannot reach theta = pi under Table-1 weights. Here the kinetic theta runs on
the powered thermal ring so the entropy and temperature factors are live.
Reproduce:

    python navier_stokes_theta/theta_three.py --n 24
    python navier_stokes_theta/theta_three.py --n 32
    python navier_stokes_theta/plot_theta_three.py

## Definitions

Reference states follow Shovelcat_Theory_1 Appendix B, where T_ref is a
*monthly mean* and S_ref a local-variance proxy: the reference is the mean of
the surroundings, not a fixed baseline. That choice is decisive (see below).

| Factor | Ratio | Form, Table-1 weights |
|---|---|---|
| S | r_S = (s + 1e-3)/(<s> + 1e-3), s = ln(1+dT) | 1 + w_S p_S ln r_S = 1 + 0.96 ln r_S (no root in the source) |
| T | r_T = <T>/T(x), T = 1 + dT | 1 + 0.6 sr(ln r_T), sr = signed root |
| E | r_E = (P_w^+ + d<D_w>)/(D_w + d<D_w>) as in Form B | 1 + 0.4 sr(0.8 ln r_E) |

theta_s = f_S f_T f_E; theta_t + u.grad theta = D lap theta + (theta_s - theta)/tau;
cap theta <= pi (applied in physical space before every use; the stored
spectral field overshoots the cap by up to 9% through dealiasing, so reported
theta_max is min(theta, pi)); nu_eff = nu exp(beta|theta-1|), with the extra
dissipation delivered to the heat field. beta = 0 reproduces thermal_loop.run
(24^3 max vorticity 7.6328, 32^3 kinetic energy 0.061293, as in RING_POWER).
Insulated case only, dt = 0.02, t = 3.

## Results, 32^3

| Quantity | beta = 0 (passive) | beta = 0.5 |
|---|---:|---:|
| first time theta_max = pi | 0.42 | 0.40 |
| peak of f_S (domain max) | 4.79 | 4.87 |
| peak of f_T | 1.12 | 1.14 |
| peak of f_E | 1.60 | 1.58 |
| max volume fraction at the cap | 0.15% | 0.16% |
| theta_max at t = 3 | 3.05 | 2.78 |
| kinetic energy at t = 3 | 0.06129 | 0.04754 |
| max vorticity at t = 3 | 7.920 | 6.925 |
| hottest-cell excess at t = 3 | 1.081 | 1.289 |

24^3 gives the same picture: pi crossing at 0.38 on both betas, f_S peak
4.60/4.72, energy 0.06119/0.04779, hot spot 0.992/1.258. Energy and
thermal accounting errors are below 1.2e-8 in every run.

![Factor maxima, capped theta, and the effect of coupling](D:/shovelcat-colony/navier_stokes_theta/theta_three.png)

## What this shows

1. **pi is reached, and one factor does it.** The entropy factor alone peaks
   near 4.8 at the hottest cell. It is the only factor without a square root
   and it has the largest weight (w_S p_S = 0.96), so a hot-spot-to-mean
   entropy contrast of e^2.2 ~ 9 is enough. The temperature factor never
   exceeds 1.14 and the energy factor never exceeds 1.6. In this flow the
   interface is a *thermal* phenomenon; the kinetic load is a spectator.

2. **The interface is transient and sits on the hot spot.** theta_max hits
   pi at t ~ 0.4 while the surroundings are still near baseline (maximum
   contrast), occupies at most 0.15% of the volume, and relaxes back below pi
   after t ~ 2.3 as the mean temperature rises and the contrast falls. The
   location of maximum theta coincides with the hottest cell throughout. This
   is the paper's picture — interfaces nucleate under load and dissolve when
   the budget rebalances — and it depends entirely on the mean-of-surroundings
   reference. With a fixed baseline reference (THETA_FIELD_RESULTS.md) both
   thermal factors are <= 1 everywhere and pi is unreachable.

3. **Coupling acts as a kinetic sink that concentrates heat.** With beta =
   0.5 the flow loses 22% of its kinetic energy and 13% of its peak vorticity
   relative to the passive run, while the hottest cell gets 19% hotter. The
   loop is heat -> entropy contrast -> theta -> viscosity -> more local
   dissipation -> more heat. In an insulated liquid this is a positive
   feedback on temperature and a negative feedback on motion. Whether it
   saturates depends on cooling, which this run does not include.

4. **The below-baseline pathology is worst in the S factor.** Where the
   local entropy is far below the mean, f_S goes negative (down to -2.7), so
   theta_s < 0 in cold regions. The source gives no rule for this; the field
   equation simply relaxes toward those negative values. Any published fluid
   form needs a stated floor for f_S.

## Limits

Two grids, one time step, one flow, one beta. The interface volume (0.15%)
is a handful of cells, so its shape is not resolved; its existence and
timing are grid-stable to 0.04 time units. The 1e-3 regulariser in r_S
matters only for t < 0.2. No cooling, no free surface, no material data.
The result depends on choosing the paper's mean-reference convention; that is
a modelling decision the folder should make explicitly and keep fixed.

Data: [24^3](theta_three_24_0.02_results.json), [32^3](theta_three_32_0.02_results.json).
Code: [theta_three.py](theta_three.py), [plot_theta_three.py](plot_theta_three.py).

## Addendum: a wall at 3 and a floor at -pi (Jonathan's proposal, same day)

Proposed structure: theta lives in [-pi, pi]; beyond |theta| = 3 a restoring
force pushes back; pi is the hard limit. Implemented as an extra source
-sign(theta) (|theta|-3)^+ / tau in the field equation, plus clipping to
[-pi, pi]. Run with `--wall 3 --floor -3.141592653589793`, 24^3 and 32^3.

| 32^3 | cap only | wall 3 + floor -pi |
|---|---:|---:|
| first theta = 3, beta 0 / 0.5 | — | 0.54 / 0.50 |
| first theta = pi, beta 0 / 0.5 | 0.42 / 0.40 | 1.04 / 0.56 |
| max volume above 3, beta 0 | — | 0.13% |
| max volume at pi, beta 0 | 0.15% | 0.06% |
| minimum theta at t = 3 | -2.7 | -2.95 (floor not reached by t = 3) |
| kinetic energy at t = 3, beta 0.5 | 0.04754 | 0.04775 |
| hottest cell at t = 3, beta 0.5 | 1.289 | 1.284 |

The wall delays contact with pi and thins the interface, but does not
prevent it: with a linear restoring force of the same strength as the
relaxation, the equilibrium above the wall is theta = (theta_s + 3)/2, so
pi is reached whenever theta_s > 2 pi - 3 = 3.28. The entropy factor
supplies theta_s ~ 4.8 here, so the interface still forms. A general
stiffness k (restoring force k(|theta|-3)/tau) gives theta_eq =
(theta_s + 3k)/(1+k) and an interface condition theta_s > pi + k(pi-3):
k ~ 12 would be needed for pi to require the observed peak load. That k is a
free parameter the theory would have to fix. The negative side behaves
symmetrically: cold regions descend to -2.95 by t = 3 and would meet the
-3 wall just after; the -pi floor was not exercised in this window.
Bulk flow quantities are unaffected at this interface volume.

## Addendum 2: does the interface sit on the zero-divisor channels? (theta_void_check.py)

Definition used (from arc-proposer/SPHERE_GENERATOR.md: a zero divisor is two
live things whose product collapses): the fluid channel is the set where the
enstrophy production P = w.S.w vanishes while |w| and |S| are both live.
Alignment a = P/(|w|^2 |S|_F). Passive 32^3 run, wall 3, floor -pi.

| t | interface cells (theta >= 3) | interface: median \|a\|, mean a, fraction \|a\|<0.1 | domain: median \|a\|, mean a, fraction \|a\|<0.1 |
|---:|---:|---|---|
| 1.0 | 16 | 0.35, +0.32, 0% | 0.15, +0.06, 34% |
| 1.5 | 40 | 0.24, +0.25, 0% | 0.17, +0.02, 24% |
| 2.0 | 44 | 0.27, +0.29, 0% | 0.20, -0.01, 20% |
| 2.5 | 24 | 0.27, +0.28, 0% | 0.22, -0.01, 19% |
| 3.0 | 12 | 0.27, +0.28, 0% | 0.23, -0.01, 18% |

No interface cell lies in a zero-divisor channel at any sampled time, while
18-43% of the domain does. The interface sits where the product is live and
positive (aligned stretching, a ~ +0.28 against a domain mean ~ 0). Under
this definition the placement hypothesis "IBH on void lines" is rejected; the
interface is anti-correlated with them. The interface also moves: its
argmax rides the downward return flow at r ~ 0.6-0.8 between drives
(azimuth ~ -146 deg), descending about one length unit per time unit, so it
is advected around the loop rather than pinned.

Arithmetic notes for the record: with the wall at 3, the cushion to pi is
pi - 3 = 0.1416 exactly and the k = 1 interface condition theta_s > 2pi - 3
= pi + (pi - 3) = 3.283 is an identity, not a measurement. The stiffness
needed to make pi require the observed peak load is k = (theta_s,max - pi)
/(pi - 3) = 11.6 at 32^3 and 10.9 at 24^3; it depends on the peak load of
this particular flow and is not a constant.

Data: theta_void_check_results.json.

## Addendum 3: the interface and the orthogonal plane (theta_plane_flux.py)

Mapping: normal plane = the solenoidal velocity (the executed path); orthogonal
plane = the gradient subspace removed by projection (the pressure head Pi,
lap Pi = div(u x w)). Globally the two exchange nothing (sum of -u.grad Pi is
zero to 1e-18), but locally j = -u.grad Pi is the pointwise hand-off between
the planes. Passive 32^3 thermal run, wall 3, floor -pi.

| t | interface cells | mean j at interface | median j | domain mean \|j\| | interface \|j\| percentile | interface \|grad Pi\|^2 percentile |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 16 | +0.97 | +1.56 | 0.044 | 99.3 | 99.5 |
| 1.5 | 40 | +0.73 | +0.53 | 0.062 | 98.7 | 99.3 |
| 2.0 | 44 | +1.56 | +1.95 | 0.071 | 98.8 | 99.0 |
| 2.5 | 24 | +1.65 | +1.89 | 0.070 | 99.0 | 98.7 |
| 3.0 | 12 | +1.83 | +1.72 | 0.068 | 99.3 | 98.6 |

The theta = pi interface sits at the top ~1% of both the plane-exchange
density and the orthogonal-plane load, and the exchange has a definite sign:
positive, meaning the orthogonal plane is *delivering* energy to the normal
plane there (pressure driving flow through the high-dissipation return
channel). The interface is where the two planes are most strongly coupled,
20-40x the domain-typical magnitude.

Candidate J: on Gamma, intercept a fraction kappa of that delivery —
J = kappa j^+ chi_Gamma — so the orthogonal plane keeps what it would have
handed over. This is the paper's "interface as sink" with a concrete carrier.
With kappa = pi - 3 (the reserve) and the present interface volume (12-44
cells) the intercepted power is ~3e-4 against an input of 0.04, i.e. under 1%:
structurally right, quantitatively negligible unless Gamma grows. Whether J
of this form gives an unbounded sink (Ladyzhenskaya-type regularity) depends
on how j scales with gradients at the interface; not established here.
Data: theta_plane_flux_results.json.

## Addendum 4: how the interface flux scales, and J as a real sink (theta_J_sweep.py) — 14 Sep 2026

Same thermal ring, passive theta, wall 3, floor -pi, 32^3, dt .02, t <= 3,
fixed input power .04 (total .116). Gamma = cells with theta >= 3.
The J sink removes power kappa j^+ from each Gamma cell per step (rescaling
|u| there, then re-projecting) and is booked in the energy budget
(closure <= 1.2e-8 in every run).

| nu | kappa | peak \|grad u\| | peak j on Gamma | peak j anywhere | Gamma cells (max) | sink / input | final KE | k_eta / k_max |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| .03 | 0 | 7.26 | 3.06 | 7.79 | 48 | 0 | .06129 | 5.6 / 10.7 |
| .02 | 0 | 8.44 | 6.58 | 10.46 | 68 | 0 | .07243 | 7.3 / 10.7 |
| .015 | 0 | 9.26 | 7.66 | 12.84 | 88 | 0 | .07966 | 8.7 / 10.7 |
| .01 | 0 | 10.38 | 8.99 | 16.04 | 84 | 0 | .08848 | 11.2 / 10.7 (marginal) |
| .03 | pi-3 | 7.25 | 3.05 | 7.74 | 52 | 0.31% | .06105 | |
| .03 | 1 | 7.22 | 3.00 | 7.68 | 60 | 2.06% | .05966 | |
| .01 | 1 | 10.13 | 13.30 | 21.97 | 72 | 5.54% | .08240 | |

**Scaling.** Across the nu sweep the peak plane-exchange at the interface
grows as (peak gradient)^3.0 (log-log slope 2.99, four points), while the
domain-wide maximum of j grows as gradient^2.0. Dimensionally j = -u.grad Pi
~ U^3/L and |grad u| ~ U/L, so a cubic law is what fixed interface geometry
and rising U give; the interface is where that geometry is fixed (the hot
return channel) while the bulk is not. For comparison the viscous sink
scales as gradient^2 and a Ladyzhenskaya-type guarantee needs a sink growing
faster than gradient^2.5. The interface exchange clears that exponent in
this sweep. Caveats: four viscosities, one flow, one grid, nu=.01 marginally
resolved, and j is a transfer density, not yet a dissipation — it only becomes
a sink through kappa.

**J as a sink.** With kappa = pi-3 the sink takes 0.31% of the input at
nu = .03; with kappa = 1, 2.06% at nu = .03 and 5.54% at nu = .01. The share
grows as viscosity falls, i.e. the sink strengthens exactly when the viscous
sink weakens. Draining Gamma also raises the delivery into it (peak j on
Gamma 8.99 -> 13.30 at nu = .01): the orthogonal plane pushes harder where
the normal plane is being emptied, a positive feedback on the sink itself.
Gamma size grows with decreasing nu (48 -> 88 cells); onset stays at t ~ .5.

None of this is a proof. It is the first quantitative evidence that the
interface channel has the *scaling* a regularizing mechanism needs, and that
the paper's J can be given a concrete, energy-consistent carrier. The next
discriminating step is a flow where gradients concentrate without a thermal
hot spot (colliding rings), to separate the interface's placement from the
heat that currently drives theta to pi.

Data: theta_J_sweep_*_results.json. Code: theta_J_sweep.py.
