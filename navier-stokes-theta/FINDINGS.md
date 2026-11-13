# Interpretation of the first tests

These 13 simulated runs test the newly proposed global energy ratio theta_E=P/D, not the unrecovered original laptop theta equation. Nine runs vary viscosity and initial amplitude. Four check spatial resolution, time step, or perturbation seed. Three additional unperturbed runs check the exact shear solution.

## What changed with viscosity

At initial shear amplitude 1, the off-shear energy reached 10% at t=14.5 for nu=.03 and t=10.5 for nu=.01. It did not reach that marker by t=20 for nu=.1. This is consistent with viscosity affecting the growth of perturbations in this flow family. Forcing was scaled with viscosity to keep the reference equilibrium shear amplitude fixed; the initial perturbation and geometry were fixed. These are controlled dimensionless parameter changes, not simulations of named materials.

The 10% marker is an operational choice measuring energy in modes with nonzero streamwise wave number. It detects departure from parallel shear. It does not distinguish coherent vortices from sustained turbulence, and its crossing time is not the first instant of instability.

## Do the proposed theta thresholds identify the change?

They do not identify it for this diagnostic and experiment:

- The stable nu=.1, amplitude=.5 run crossed sqrt(pi), phi, and sqrt(phi) downward by t=.6 without reaching the flow-change marker by t=20. It began with theta near 2, so an upward onset threshold was already exceeded at initialization.
- The nu=.01, amplitude=1 run reached the marker at t=10.5 while theta was approximately .959. It never crossed 1, sqrt(phi), phi, sqrt(pi), or pi during the sampled interval.
- Across the six changing runs in the main sweep, theta at the marker ranged from about .702 to 1.018. There is no common threshold among the tested constants at this marker.

Thus exceeding these constants is not sufficient for the marker, and crossing them is not necessary. This does not reject an independently specified material-dependent theta model. Fitting a separate threshold to each observed run would not provide an independent prediction. Such a model needs a fixed definition, normalization, and a test on conditions excluded from fitting.

Crossing times are sampled at .1 time intervals; they are not interpolated. Tiny sign changes near theta=1 can reflect small fluctuations about balance and should not be interpreted as new phases. Neither theta nor the compactified gradient feeds back into the solver.

## Gradients and the infinity comparison

For nu=.01, amplitude=1, peak sampled velocity-gradient magnitude was 4.896, 4.839, and 4.858 on 48, 64, and 96 grids. The corresponding compactified value A/(1+A) was around .83, not close to 1. There is no evidence of divergent gradients in this finite run. A finite numerical grid cannot prove absence of a singularity; this is also the two-dimensional system, not the three-dimensional regularity problem.

Compactification changes how a quantity is represented. For example, the scalar ODE A'=A^2 with A(0)=1 has A=1/(1-t), and q=A/(1+A)=1/(2-t). q stays finite and reaches 1 at t=1 while the original A diverges. This exact example shows why a finite transformed coordinate does not remove blow-up. It is an illustration, not a Navier-Stokes solution.

## Numerical evidence and limits

- Exact shear maximum velocity error: 1.64e-12 at t=2 over three starting amplitudes.
- Maximum instantaneous discrete energy-budget residual across runs: 8.89e-16 or less. This checks the spatial operator identity, not accumulated time-integration error.
- Halving dt from .01 to .005 on the 48 grid changed sampled energy by at most 6.35e-11 and theta by 1.97e-9 for the selected low-viscosity run.
- Refining 64 to 96 changed sampled energy by at most 4.13e-6, theta by .000169, and off-shear energy fraction by .000125. Maximum sampled gradient difference was .0496, so pointwise extrema are less converged than global quantities.
- The 10% marker remained t=10.5 across all refinements and the second perturbation seed, to the .1 sampling resolution.
- Only one parameter case received refinement checks. No ensemble confidence intervals, sustained-turbulence diagnosis, or material-dependent constitutive model was established.

The next informative experiment is to specify the original or revised theta independently of these results, then test its predictions on a held-out viscosity/forcing set. For the three-dimensional question, a separate validated 3D solver and vorticity-stretching diagnostics are required; these 2D results cannot substitute for them.
