# Stacking driven circulation layers

Reproduce with `python navier_stokes_theta/stacked_layers.py`; raw time series
are in `stacked_layers_results.json`. Eight Gaussian rotational drives per
ring, radius .8, width .38. The lower layer is at z=pi-.55; the optional upper
layer is at pi+.55. Same-sense means upward outer and downward inner forcing
on both rings. Opposite-sense reverses the upper ring. These are prescribed
mechanical body-force fields, not physical repelling surfaces or solid pins.

All cases use the same ramped delivered power .04 (ramp duration .2), total
input .116 through t=3, starting from rest. The energy-calibrated controller
acts on the combined field, so the power split between layers is not fixed
independently. This is a fixed-total-input geometry comparison, not adding a
second full-power motor to the first. Viscosity .03 and periodic side 2*pi
remain unchanged. No temperature, magnetic coupling or active void line.

Axial velocity is sampled on fixed horizontal planes at the lower drive,
between drives (z=pi), and above both (z=pi+1.1). Periodic linear interpolation
in z avoids changing the nominal measurement plane with resolution. The
core is r<.45; the annulus is 1<r<1.5. Grid-cell radial masks still introduce
spatial sampling error. Net full-plane flow is zero in these runs: local
upflow must be paired with downflow, but not necessarily within the two masks.

Grids 24 and 32 cubed, dt=.02; same-sense 32 cubed repeated at dt=.01.
Every run checks kinetic energy accounting, full-plane flux, and CFL. Three
time units cannot establish a steady state, oscillation period or singularity.

## Top and bottom openings are a separate boundary problem

The solver identifies the top and bottom of its periodic cube. That is not
flow out of a vessel into an external reservoir and back. A through-column
model would need real inlet/outlet or reservoir conditions. Reversal requires
appropriate dynamics: for example pressure restoration from unequal fluid
levels/compliance, or an alternating applied pressure. Constant forcing can
instead produce a persistent through-flow or recirculation.

A lumped example is M*x'' + R*x' + K*x = F(t), with liquid inertia M,
loss coefficient R and a separately justified restoring coefficient K.
This is a possible future reduced model, not something solved by the present
stacked-ring calculation. Reference for driven/damped oscillator mechanics:
https://openstax.org/books/university-physics-volume-1/pages/15-5-damped-oscillations

## Results at t=3, 32 cubed

| Arrangement | Above-layer annular vertical velocity | Above-layer core velocity | Final kinetic energy |
|---|---:|---:|---:|
| Lower ring only | +.059002 | +.590932 | .061293 |
| Two same-sense rings | +.425868 | -.302723 | .063677 |
| Upper ring reversed | -.334344 | +2.059752 | .059988 |

At the plane between layers, annular/core velocities were respectively
.444860/-.242299 (single), .526295/-1.671601 (same-sense), and approximately
zero in both masks (opposing). This is a symmetric prescribed-drive comparison,
not a demonstrated passive barrier. No oscillatory forcing was used and no
repeatable oscillation period was established.

Adding a same-sense powered layer carries stronger outer upflow to the fixed
upper probe in this setup. Reversing its sense instead produces outer downflow
there. All cases receive total energy .116. This does not mean both layers
receive .116 independently, nor does it show power-free amplification: a
different spatial forcing distribution changes the flow.

The upper-annulus result changes by about 5% between grids for either stacked
case. The time-step-halving difference in the same-sense upper-annulus velocity
is about 6e-6. Spatial resolution remains the larger uncertainty. These runs
test placement and sense of driven circulation, not ejection into open space,
gravity-driven fall-back, magnetic repulsion, or a Navier–Stokes singularity.
