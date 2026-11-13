# Ring of mechanical drive surrogates

Run `python navier_stokes_theta/pin_ring.py`; raw results are in
`pin_ring_results.json`.

Initially stationary, periodic 3D incompressible liquid model, viscosity .03.
Two, four, eight or sixteen Gaussian rotational body forces lie on a circle
of radius .8 at z=pi. Their rotation axes are tangent to that circle, with
opposite axes on opposite sides. Four drives therefore form two perpendicular
pairs. Rotation signs favor upward motion on the outside, downward inside.
Force is projected divergence-free and normalized to total spatial RMS .3.
All drives remain powered for one dimensionless time unit.

These are body-force surrogates for rotating pins, not resolved solid pins.
There is no vessel, inverted-valley wall, free surface, thermal or magnetic
coupling. Periodic boundary conditions permit recirculation across boundaries.
The force orientations deliberately select a circulation sense; emergence of
that sense is a response to the chosen forcing, not an independent discovery.
Equal force RMS and duration do not guarantee equal delivered energy. Signed
work is recorded for each case. Increasing drive count changes spatial coverage.

At the drive-height cross-section, core means r<.45, outer means 1<r<1.5.
Eight azimuthal sector means estimate the uniformity of outer upward velocity;
their coefficient of variation is a coarse diagnostic affected by the grid.
Grids 24 cubed and 32 cubed, dt=.02, RK4, strict 2/3 spectral dealiasing.
Energy balance and CFL assertions run for every case.

A near-axisymmetric meridional circulation is consistent with a toroidal
recirculation cell. It is not proof of a single isolated vortex ring, and
does not imply an azimuthal swirl around the central axis. In this geometry
the local vortex axes follow the ring; parallel axial vortices would produce
a different flow. No singularity or physical void channel is being tested.

## Results at t=1, 32 cubed

| Drives | Mean core vertical velocity | Mean outer vertical velocity | Sector variation |
|---|---:|---:|---:|
| 2 | -1.78992 | .39690 | 1.162 |
| 4 | -2.11107 | .56899 | .163 |
| 8 | -2.19986 | .60012 | .011 |
| 16 | -2.20015 | .60349 | .008 |

The selected rotation sense produces upward outer and downward core flow.
Four drives are less patchy than two; eight and sixteen approach similar
azimuthally uniform circulation. This is saturation toward a smooth ring of
forcing, not evidence that adding drives leads to unlimited amplification.
Coarse-to-fine core/outer averages differ by up to approximately 4%; detailed
sector variation is less converged. No claim of full numerical convergence.
