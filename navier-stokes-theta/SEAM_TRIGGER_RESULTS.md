# Localized seam-trigger hypothesis test

120 dimensionless reaction/diffusion runs: 64 and 128 square grids, uniform
or seam-lowered threshold, reservoir stripe at 0 or 45 degrees, pulse centers
0, .12 or .45 from the seam, and input energies 0, .03, .045, .06, .08.
The Gaussian pulse width stays .10 in physical model coordinates at both grids.
Run `python navier_stokes_theta/seam_trigger.py` to reproduce the JSON results.

This is a scalar heat/reservoir experiment, not Navier–Stokes, liquid flow,
octant reflection, a phase-change model, or a test of the original theta.
Rotating the stripe represents reservoir alignment, not moving solid walls.
Diffusion is isotropic; the seam has no special transport conductivity.
The lower threshold, reservoir distribution and release kinetics are assumptions.

At 128 resolution and pulse energy .06:

| Threshold | Stripe angle | At seam | Offset .12 | Offset .45 |
|---|---:|---:|---:|---:|
| Uniform | 0 | 0 | 0 | 0 |
| Uniform | 45 | 0 | 0 | 0 |
| Lowered near seam | 0 | .044009 | .028109 | 0 |
| Lowered near seam | 45 | .024259 | .016174 | 0 |

Entries are released reservoir energy, in addition to the supplied .06.
Total initial reservoir is .5. Accounting error across 120 runs was at most
2.23e-16. The zero-pulse controls do not release energy. In the lowered case,
the smallest TESTED pulse releasing over .005 (1% of reservoir) was .045 at
the seam and .06 at offset .12. This is a coarse sweep, not an exact threshold.
No tested pulse released over .005 at offset .45.

The maximum absolute release difference between 64 and 128 grids was .00673,
so precise release values are not established as converged. The discontinuous
activation law makes the discretization sensitive near threshold.

Interpretation: spatially localized activation can release stored energy in
this specified model. Seam preference is conditional on imposed material laws;
it is not independent evidence that mixed protein voxels have lower activation
thresholds, that zero divisors transport energy, or that an informational black
hole is a physical reservoir. No velocity or pressure was computed, and no fluid
singularity was tested. A future fluid coupling needs independently specified
material properties, pressure/energy conversion and appropriate conservation.
