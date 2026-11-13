# Two helical tubes with localized forcing

This experiment solves dimensionless, constant-density incompressible 3D
Navier–Stokes on a periodic cube of side 2 pi. Viscosity .03, initial mean
kinetic energy .1, tube width .45, helical radius .7, run duration 2.
Opposite-circulation Gaussian tangent fields are projected to divergence-free
vorticity, then converted to velocity. Thus these are smooth approximate
helical tubes, not material walls or exactly prescribed vortex filaments.

The forcing lasts .3 time units with spatial RMS magnitude .3 and envelope
width .55. Its envelope is centered at one tube at z=0. Aligned/opposing refer
to the INITIAL local velocity; the transverse case uses its cross product
with the z axis. Incompressibility projects each force, so the effective force
is not strictly compact or exactly pointwise parallel/perpendicular. The force
direction is held fixed while the flow evolves.

All forced cases have equal force RMS and duration. They do NOT receive equal
net energy: signed work is integrated separately. An opposing pulse removes
energy in these runs. This is an orientation/forcing comparison, not an
equal-delivered-energy demonstration of enhanced efficiency.

Numerics: Fourier velocity projection, rotational nonlinearity, strict 2/3
dealiasing, RK4. Grids 24^3 and 32^3, dt .01; aligned case repeated at dt .005.
Exact unforced single-mode shear decay at n=16 over t=1 had maximum absolute
velocity error 2.23e-16. Each run checks integrated energy balance and CFL.

No original theta, void transport, quantum entanglement, material transitions,
reservoir release law or octant walls are present. Forcing is externally
specified. These low-resolution, short-time runs cannot establish or exclude
finite-time blow-up, and do not establish turbulence onset.

Run `python navier_stokes_theta/vortex3d.py` for results in
`vortex3d_results.json`, including time series of stretching production,
enstrophy, maximum speed/vorticity, divergence, CFL and energy.

## Results

| Case, 32 cubed | Signed work | Peak vorticity | Final kinetic energy |
|---|---:|---:|---:|
| Control | 0 | 4.88692 | .062270 |
| Aligned | .020868 | 9.97609 | .072700 |
| Opposing | -.013186 | 4.88692 | .053733 |
| Transverse | .003243 | 5.42165 | .064486 |

Peak means maximum over saved samples spaced .1 time units. Opposing peak
includes the initial state. The aligned peak changed from 9.77659 at 24 cubed
to 9.97609 at 32 cubed (about 2%). Halving dt retained 9.97609 to shown precision.
This supports pulse-driven amplification in this setup, not a singularity or
an independent test of the proposed seam/quantum/threshold mechanisms.
