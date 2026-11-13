# Where dissipated energy goes

Run `python navier_stokes_theta/thermal_loop.py`. This adds a spatial thermal
field to the eight-drive equal-power ring. Heat is transported by the liquid,
diffuses with dimensionless diffusivity .02, and is optionally removed toward
a baseline at rates 0, .5, or 2. Heat capacity per mass is set to 1. Temperature
EXCESS begins at zero. No original theta formula or material thresholds are
applied. All thermal constants here are illustrative, not measured properties.

This is ONE-WAY coupling: the existing constant-density, constant-viscosity
velocity determines heating and transport. Temperature does not change
viscosity, buoyancy, density, or the supplied mechanical power. Thus the three
cooling cases share the same velocity, not three thermally coupled flows.

Viscous heating shape is 2 nu S:S, where S is the symmetric velocity-gradient
tensor, evaluated at a temporal midpoint approximation. It is nonnegative.
Each flow step normalizes that shape to the step's RK4-integrated viscous
energy loss. Global thermal/kinetic accounting is therefore enforced; the
local source distribution still has temporal and spatial approximation error.

Heat uses conservative donor-cell finite-volume advection and centered
diffusion, with positivity-limited substeps. Face velocities are projected
using the corresponding discrete divergence and Laplacian. This projection
slightly modifies the spectral flow for thermal transport only. Newton cooling
is integrated exactly in half steps around each thermal update. First-order
advection adds numerical diffusion, so local hot spots require refinement.

Checks: grids 24 and 32 cubed; dt .02 and .01 for sustained driving; an
additional 32-cubed run stops input at t=1. End time 3. The uniform-rate
cooling plus sinusoidal diffusion reference at n=24, t=.1 had max error
8.94e-6 and global accounting error 6.67e-16. Every production run checks
nonnegative temperature excess, divergence of thermal face fluxes, and
kinetic + thermal + removed-heat energy accounting.

Interpretation: heat storage and heat removal are separate from kinetic
energy growth. A local maximum is not a universal transition threshold or a
singularity. Finite heat capacity does not mean there is a universal "full"
temperature; a material's transition or damage criterion must be specified.

## Results, sustained input, n=32, t=3

| Cooling rate | Mean temperature excess | Maximum excess | Heat removed |
|---|---:|---:|---:|
| 0 (insulated) | .054707 | 1.080851 | 0 |
| .5 | .032575 | .724382 | .022132 |
| 2 | .012475 | .369656 | .042232 |

Energy is .116 supplied = .061293 kinetic + stored excess heat + removed heat.
The nonuniform thermal field arises from viscous source distribution and
transport, without imposing a lower activation threshold at a seam. It does
not establish that such a threshold exists. For the insulated 32-cubed case,
one maximum lies at radius .589 from the central axis and z=1.963, below the
drive plane z=pi. Equivalent azimuthal locations and grid effects must not be
interpreted as a unique privileged pixel.

Halving dt changes the insulated maximum from 1.080851 to 1.078969 (~.17%).
Changing n from 24 to 32 changes it from .991824 to 1.080851 (~9%); the mean
changes only ~.2%. Local temperatures are not spatially converged.

Stopping the drive at t=1 leaves mean insulated excess .026078 by t=3 and
maximum .578419. Kinetic energy keeps becoming heat after the power stops;
cooling is what removes thermal energy. A total-energy residual below 1e-8
and thermal residual below 1e-10 hold in these runs.
