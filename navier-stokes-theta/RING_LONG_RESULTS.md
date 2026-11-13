# Longer powered loop and energy accounting

Extends `ring_power.run` to t=8 for eight drives, 24 and 32 cubed grids,
dt=.02, viscosity .03, power ramp to .04 over t=.2. Total supplied kinetic
energy .316. Geometry, spatial force direction and power stay fixed.
The output is `ring_long_results.json`.

The domain remains a periodic cube: it has no open top, gravity, reservoir
capacity, physical wall, or column-height degree of freedom. Thus the test
cannot answer whether a column rises, spills, or carries away material. It
tests longer-time power/dissipation balance in the existing finite loop.

Kinetic energy accounting is K(t)=input(t)-viscous_dissipation(t), initially
at rest. Cumulative dissipation can also be interpreted as heat produced,
but temperature is not evolved or coupled back. For an insulated physical
system that heat would accumulate; in an isothermal interpretation it must
be removed by the environment. A kinetic steady state is not automatically
a thermal steady state. "Full" internal energy requires a specified capacity
or transition criterion, neither of which is supplied by this model.

A rising gravitational column consumes power at rate mass_flux*g*height;
height therefore is not an energy source. A return flow can recover some
potential energy but cannot replace net dissipative losses without input.
The present calculations omit gravity entirely.

## Results at t=8

| Grid | Kinetic energy | Instantaneous viscous power loss | Maximum vorticity |
|---|---:|---:|---:|
| 24 cubed | .089909 | .036025 | 7.4652 |
| 32 cubed | .090147 | .035977 | 8.0969 |

Input power is .04: about 90% is dissipated at t=8, while energy continues
to increase at about .004 per unit time. This is slower accumulation, not a
demonstrated steady state. Of .316 supplied energy, about .22585 has been
dissipated by t=8 in the finer run. Bulk energy differs by .27% between
grids, but maximum vorticity differs by about 8.5%; fine structure is not
converged. No inference about a singularity is justified by these runs.
