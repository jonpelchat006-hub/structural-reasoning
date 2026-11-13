# Four-vortex orientation comparison

Reproduce with `python navier_stokes_theta/four_vortices.py`.
Uses the 3D incompressible periodic solver in `vortex3d.py` (viscosity .03).
All initial flows have mean kinetic energy .1. Every forced case receives
exactly .02 additional mean kinetic energy, then evolves unforced to t=1.
The pulse is a smooth spatial velocity increment applied instantaneously;
its amplitude solves the quadratic energy increment, not a resolved heating
or reservoir release process. It differs from the earlier finite-duration
constant-force experiment. No liquid phase transition is modeled.

Two opposite tubes, four same-sense tubes and four alternating tubes share
helical radius .7 and width .45. Projection enforces periodic solenoidality.
The zero vorticity Fourier mode cannot be inverted to periodic velocity:
the same-sense configuration therefore has a compensating background, not
four isolated vortices carrying nonzero net mean vorticity.

Aligned means the tube bundle is centered on x=y=pi. Displaced shifts the
bundle by .8 in x while the pulse center stays at (pi+.7,pi,0).
No physical seam acts on the liquid; the reference line only specifies
placement. Forcing follows projected local INITIAL velocity times a fixed
Gaussian envelope of width .55. Equal input energy does not mean identical
impulse shape, impulse amplitude or initial enstrophy.

Controls: unforced case for each pattern; 24 and 32 cubed grids; alternating
aligned repeated with dt halved from .02 to .01. Pulse width stays fixed as
grid resolution changes. Translating an unforced 32-cubed alternating field
by four grid cells reproduced the translated velocity within 8.9e-16.

Interpretation limits: these are short, low-resolution comparisons. A larger
initial/post-pulse vorticity is not evidence of a nonlinear singularity.
Pattern comparisons hold energy fixed, but initial vorticity differs. This
does not test algebraic zero divisors, entanglement or the original theta.

## Measured peaks (32 cubed)

| Pattern | Unforced | Pulse, aligned | Pulse, displaced |
|---|---:|---:|---:|
| Two opposite | 4.8869 | 11.4158 | 8.6354 |
| Four same-sense | 2.2144 | 7.4214 | 6.2291 |
| Four alternating | 6.3450 | 15.1717 | 11.5559 |

All forced peaks occur at t=0 immediately after the velocity increment,
then decline over the observed window. Four alternating has the largest
absolute peak, but it also starts with the largest peak vorticity. Therefore
the table does not isolate spontaneous nonlinear amplification.
The largest forced-peak resolution change is approximately 5.7% (displaced
alternating); aligned alternating changes about 2.1%. Quantitative spatial
convergence is incomplete. Halving dt does not change the instantaneous
peak by construction; the later evolution is the meaningful temporal check.
