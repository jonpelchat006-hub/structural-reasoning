# Finite reservoirs and a reversing liquid column

The test supports sustained back-and-forth flow when a periodic pressure drive replaces dissipated energy. A constant pressure instead produces a level difference and eventually zero flow. Removing all losses produces resonant growth in this ideal model, but the finite reservoirs reach their capacity while the flow remains finite.

## What was tested

This is a reduced hydraulic model of a liquid column connecting two open reservoirs, analogous to a U-tube. It tests the proposed restoring pressure and oscillation mechanism. It does not simulate the complete geometry of a central column passing through the earlier vortex arrangement. In particular, the previous three-dimensional periodic solver does not acquire open top and bottom boundaries from this calculation.

Let x be the liquid volume transferred between reservoirs and Q = dx/dt the volume flow. The model is

    I dQ/dt = p(t) - K x - R Q - C |Q| Q.

For a tube of length L and cross-sectional area a, neglecting reservoir inertia, I = rho L/a. For constant reservoir surface areas A1 and A2, the hydrostatic stiffness is K = rho g (1/A1 + 1/A2). A displaced liquid level provides the restoring pressure; inertia allows the flow to overshoot equal levels.

All reported values use illustrative scaled units, with I = K = 1. Each reservoir initially contains volume 2 and can hold volume 4, so their volumes are 2-x and 2+x. The simulation stops at |x| = 2, when a reservoir empties and the other reaches capacity. The model is not continued beyond that event.

Baseline resistance is R = 0.2, with C = 0 unless specified. Pressure is either zero, constant at 0.2, or 0.2 cos(omega t). Release tests begin at x = 0.6 with zero flow; driven tests begin at rest with equal levels. The undamped natural angular frequency is 1.

No material-specific coefficients have been fitted. There is no spatial vortex interaction, thermal release, magnetic coupling, void-line force, or quantum mechanism in these equations. The recovered weighted theta equation is not used: its weights and a physical coupling law remain unspecified.

## Results

| Test | Observed behavior |
|---|---|
| Displace and release, R = 0.2 | Repeated reversals decay toward equal levels; final flow at time 150 is 1.84e-7. |
| Displace and release, R = 2.5 | Overdamped return toward equal levels without crossing the equilibrium position. |
| Constant pressure 0.2 | Settles at x = 0.2, with reservoir volumes 1.8 and 2.2; final flow is -6.15e-8. |
| Periodic pressure, omega = 1 | Maintains bounded oscillation with transferred-volume amplitude approximately 1. |
| Same periodic pressure, extra quadratic drag C = 0.4 | Fundamental transferred-volume amplitude decreases to approximately 0.528. |
| Periodic pressure, omega = 1, no losses | Reaches reservoir capacity at time 20.25998. Flow at that event is finite: Q = 0.42224. |

The frequency scan used the same pressure amplitude in every case:

| Driving angular frequency | Late transferred-volume amplitude |
|---:|---:|
| 0.50 | 0.264327 |
| 0.75 | 0.432433 |
| 1.00 | 0.999999 |
| 1.25 | 0.324911 |
| 1.50 | 0.155582 |

The largest response among these sampled frequencies occurs near the natural frequency. The scan does not locate the precise damped resonance maximum. Equal pressure amplitude is not equal supplied energy: the driver does different work depending on the flow response. The amplitudes are least-squares fundamental harmonic amplitudes over the final four forcing cycles, not necessarily the peak excursion for the nonlinear-drag case.

## Energy and numerical checks

Stored energy is E = (I Q^2 + K x^2)/2. The model obeys

    dE/dt = p(t) Q - R Q^2 - C |Q|^3.

Pressure work is signed: an ideal pressure actuator can also absorb energy during part of a cycle. At omega = 1 with baseline resistance, accumulated net pressure work at time 150 is 13.95001, dissipated energy is 13.45001, and remaining stored energy is 0.50000. The continued motion is powered; it does not refuel itself.

The RK4 calculation integrates pressure work and dissipation alongside the motion. Maximum absolute energy-accounting residual across the reported cases is 4.21e-8. Halving the time step from 0.02 to 0.01 changes the resonant amplitude by approximately 2.45e-9. An unforced, undamped reference agrees with x = 0.6 cos(t) to within 1.45e-8 over time 20. Linear forced amplitudes agree with their analytic steady-state values to within 1.04e-6; remaining differences include the finite transient and measurement window.

The finite-capacity event is located within an integration step by bisection. Reaching it is a boundary of this model's applicability, not a numerical divergence or a fluid singularity. Even if unlimited reservoirs were assumed in the lossless resonant oscillator, its secular growth would remain finite at every finite time.

## Meaning for the vortex proposal

This supplies a concrete way for the proposed column to reverse: changing levels create restoring pressure, while a correctly timed drive maintains the motion. In a fuller model, the vortex layers would need to generate that pressure pattern and supply its measured work. A passive upper layer could redirect motion or store and return energy; sustained added energy requires an identified source.

This calculation establishes the behavior of the chosen hydraulic oscillator. It does not establish a theta threshold, an unlimited jet, or Navier-Stokes blow-up. A useful follow-on is to compare the timing of powered layers under a fixed work budget, rather than treating increased response at fixed pressure as free amplification.

The general damping and periodic-forcing comparison is consistent with [OpenStax's treatment of forced oscillations](https://openstax.org/books/university-physics-volume-1/pages/15-6-forced-oscillations). The hydraulic reduction and numerical results above are from this experiment.

Reproduce with `python finite_reservoirs.py` from this directory. Code: [finite_reservoirs.py](finite_reservoirs.py). Full time series and diagnostics: [finite_reservoirs_results.json](finite_reservoirs_results.json).
