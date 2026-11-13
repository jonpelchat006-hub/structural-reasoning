# Does upward flow return?

Reproduce with `python navier_stokes_theta/return_paths.py`; data and sample
unwrapped trajectories are in `return_paths_results.json`.

This uses the powered eight-drive ring through t=8, initially stationary,
viscosity .03, ramped power .04. No heat is converted into extra propulsion.
Five groups of 128 passive labels start within radius .15 of (pi,pi-r,2):
r=0 and .6 at t=1.5, and r=1.2 at t=1.5,2.5,3.5. Later groups sample the
evolving upward branch; they are labels, not injected mass or repeated blasts.

Each label follows interpolated fluid velocity with midpoint integration.
A rise is at least .3 above its own starting height. A turn additionally
requires descent of .1 from its maximum with negative vertical velocity.
A return is a downward crossing of its initial height after the rise.
This is NOT necessarily return to the initial position. We record horizontal
offset and cylindrical radius at first return to distinguish these meanings.
Positions are unwrapped; returns after any periodic boundary crossing are
reported separately. Later boundary crossings do not invalidate an earlier
local return, but still indicate the limits of the periodic domain.

There is no gravity, free surface, ejecta, explosive transition, real pin,
physical void conduit, or material outside the liquid in this calculation.
This tests liquid recirculation. A freely launched drop falling under gravity
is a different problem. For constant gravity and no drag, a vertical launch
returns to its starting height at 2*v0/g with height gain v0^2/(2*g).
Reference: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ballistic-flight-equations/

Checks: 24 and 32 cubed with dt=.02; 32 cubed repeated at dt=.01. Total
kinetic energy input and dissipation are checked, with CFL below .5.
A prescribed spatially uniform ballistic velocity v_z=2-t validated the
tracker: at t=4, position and height-gain errors were below 1.2e-15; all
returns were detected by t=4.01 (one sampling step beyond exact equality).

The underlying loop was deliberately driven with upward outer/downward inner
circulation. Returning labels show its pathlines, not spontaneous creation
of energy or a mathematical singularity. Repeated circulation requires the
power supply to replace dissipated energy.

## Results through t=8, 32 cubed, dt=.01

| Outer group start time | Rose by .3 | Returned below starting height before any boundary crossing | Median first return time, for returners |
|---|---:|---:|---:|
| 1.5 | 100% | 100% | 5.02 |
| 2.5 | 88.3% | 67.2% | 6.515 |
| 3.5 | 100% | 84.4% | 7.34 |

Each group has 128 labels. Later groups have shorter observation windows;
non-return by t=8 does not establish escape. The first outer group rose a
median 1.194 units. It returned at median cylindrical radius .583 after
starting around radius 1.2, with median lateral offset .622. This is upward
outer flow bending inward and descending, not straight vertical retracing.
Many first-group labels crossed a periodic boundary LATER; all first height
returns preceded that crossing. Initial central and middle groups moved
downward and crossed the periodic boundary, without the defined .3 rise.

At n=24, returned fractions were 100%,65.6%,82.8%; their median return times
were 5.10,6.61,7.22. The first group's maximum rise changes by about 4.9%
between grids. At n=32, halving dt preserves all reported return fractions;
median return times change by at most .005. The qualitative return pattern
is more robust than detailed trajectories; this is not full convergence.

The inline view shows only the first recorded label of the first outer group,
from t=1.5 to 5.4, in radius-height projection (azimuth suppressed). It uses
32 cubed, dt=.01 output. Its data and script syntax were checked; a browser
preview of the local file was blocked by browser URL policy, so visual UI
inspection could not be completed. No workaround browser access was used.
