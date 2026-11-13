# Common thresholds and transport near the thermal maximum

Run `python navier_stokes_theta/threshold_transport.py`. Results are in
`threshold_transport_results.json`. This observes the existing one-way thermal
ring simulation without altering dynamics at a threshold.

Three fixed regions at z=2 and cylindrical radii 0,.6,1.2 use normalized
Gaussian weights of width .2. The middle region is near the previously
observed hot spot. These regions are chosen from earlier results, so this is
an exploratory comparison, not an independent prediction or validation.
Widths and centers stay fixed when refining the grid. The central axis is
only a geometric reference, not a physical vacuum or zero-divisor channel.

Every region uses the SAME diagnostic temperature-excess thresholds .1,.2,
.3,.5, for cooling rates 0,.5,2. There is no claimed material threshold,
latent heat, explosion, density change, pressure pulse or viscosity feedback.
A crossing labels an observation, not a simulated physical transition.

At the first crossing of .2 in each insulated region, 256 passive labels
are seeded inside radius .15 of its center. They follow interpolated velocity
with midpoint integration; no kick is applied. We track exits from radius .3
and unwrapped vertical displacement. Thresholds choose the label start time
only; labels leaving a region cannot demonstrate heating-induced ejection.
The globally periodic domain has no external escape boundary.

Grid comparisons 24 and 32 cubed; dt .02 and .01. First-crossing time is
quantized to dt. Constant velocity interpolation across periodic boundaries
is checked independently. Local thermal accuracy remains limited by the
first-order heat advection in `thermal_loop.py`.

## Results, insulated, 32 cubed, dt=.02

| Region radius | First reach .2 | First reach .5 | Maximum regional excess |
|---|---:|---:|---:|
| 0 (central) | .88 | 1.74 | .7992 |
| .6 (near previous hot spot) | .98 | 1.64 | .8724 |
| 1.2 (outer) | 1.50 | not by t=3 | .2984 |

The preferred region depends on the specified threshold; the middle does
not ignite first for every threshold. No lowered middle threshold was used.
Rank reversal occurs under the same material coefficients through different
heating/transport histories. These diagnostics are not combustion ignition.

All passive labels left their radius-.3 starting region at least once. Mean
vertical displacement at t=3 was -1.639, +.247, +.716 for central/middle/outer
labels respectively. Some middle labels returned (7.4% were inside at t=3).
Thus leaving a local region is compatible with circulation and return, not
escape from the physical domain. Different label groups start at different
times; their displacement is not a matched-duration speed comparison.

Halving dt changes the .2 crossing times by .01. Peak regional excess changes
by under .2%. Coarse-to-fine middle-region maximum changes about 3.7%; its
label displacement changes materially (.148 to .247). One moderate-cooling
outer-region threshold (.2) is crossed at 32 cubed but not at 24 cubed: near
threshold, the yes/no outcome is resolution-sensitive. Do not treat those
marginal outcomes as reliable material predictions.

Combined energy residual remained below 1e-8. Constant-flow interpolation
test error was below 4.5e-16. No pressure-driven ejection or fluid singularity
was tested or established.
