# Sustained power versus shutdown

Run `python navier_stokes_theta/ring_power.py`; results saved incrementally
to `ring_power_results.json`. This extends the ring of mechanical body-force
surrogates, without physical pins, thermal expansion, magnetic forces or void
coupling. Same periodic cube and viscosity .03 as previous tests, initially
at rest, Gaussian rotational drives around radius .8, width .38.

An ideal controller delivers prescribed kinetic power, rising linearly from
zero to .04 over t=.2. It either stops at t=1 (total input .036), or continues
through t=3 (total input .116). Eight and sixteen drives therefore receive
the same energy when compared under the same schedule. The spatial direction
is fixed and solenoidal; the controller adjusts its amplitude. This is NOT
a constant-torque motor or a physical energy-release mechanism.

Each timestep brackets an unforced RK4 flow step with two increments of
exactly specified kinetic energy. An amplitude is obtained from the quadratic
energy-change formula. Timestep halving tests this split forcing approximation.
The ramp avoids demanding finite initial power from a fluid at zero speed.

Checks: 24 and 32 cubed for eight drives, both schedules; 32 cubed sixteen
drives at sustained power; 32 cubed eight drives repeated with dt .01 instead
of .02. Every run checks energy balance and a CFL ceiling. Pressure is handled
by incompressible projection. No claim of full spatial convergence or of
finite-time singularity can be made from these short, coarse runs.

## Results at t=3, 32 cubed

| Schedule | Drives | Total input | Remaining kinetic energy | Maximum vorticity at t=3 |
|---|---:|---:|---:|---:|
| Stop at t=1 | 8 | .036 | .009922 | 3.5717 |
| Continue | 8 | .116 | .061293 | 7.9198 |
| Continue | 16 | .116 | .061324 | 7.9197 |

Sustained eight-drive loss rate at t=3 is .027307 versus input power .04:
energy is still accumulating, so a steady state has NOT been established.
About 68% of instantaneous input power is balanced by viscous dissipation
at that time. Sixteen drives change final energy by about .05%, not a large
additional gain. Turning off power produces decay over the observed interval.
Stored heat from dissipation is not recycled into flow in this isothermal model.

Halving dt changes sustained eight-drive final vorticity from 7.9198 to
7.9209 (about .014%). Changing grid from 24 to 32 changes it from 7.6328
to 7.9198 (about 3.8%). Spatial resolution remains the larger limitation.
There is no evidence here for self-sustained energy production or a singularity.
