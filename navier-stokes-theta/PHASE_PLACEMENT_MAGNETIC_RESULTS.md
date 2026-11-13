# Phase, drive placement, and a magnetic sheet

These are three separate controlled tests. The column test examines timing, the three-dimensional fluid test examines where powered rotational drives act, and the magnetic test examines the force and work available from a specified field. They are not a single coupled simulation of an oscillating magnetic vortex column. All numerical parameters are illustrative scaled quantities, with no material calibration or original-theta coupling.

## 1. Timing with a fixed work budget

The earlier finite-reservoir oscillator is driven by smooth feedback pulses:

    x' = Q
    Q' = p - x - 0.2 Q
    theta = atan2(x, Q)
    p = 0.3 tanh(10 cos(theta-delta)) exp(2[cos(2(theta-delta))-1]).

Here theta = 0 is the upward equilibrium crossing, and theta = pi is the downward crossing. Positive delta places the pulse centre later in the cycle. The controller measures the instantaneous state; this is not merely changing the initial phase of an otherwise identical sinusoidal clock. The pulse shape has finite width and opposite pressure signs on the two halves of the cycle.

All runs begin with mechanical energy 0.08. Each drive stops when accumulated **positive** pressure work reaches 0.4; negative work absorbed by the actuator is counted separately. Thus comparisons use the same supplied positive work, not the same elapsed time or net work. Pressure magnitude is bounded by 0.3 in all cases. Two starting conditions have the same energy: (x,Q) = (0,0.4), and (0.4,0). The finite reservoirs retain their |x| < 2 capacity limit, which none of these runs reaches.

| Pulse offset | Energy when work budget is spent, starting at upward crossing | Energy when work budget is spent, starting at upper turning point |
|---:|---:|---:|
| -45 degrees | 0.132631 | 0.119275 |
| -15 degrees | 0.221421 | 0.191826 |
| 0 degrees | 0.202179 | 0.231010 |
| +15 degrees | 0.234406 | 0.223310 |
| +45 degrees | 0.156187 | 0.155811 |
| +75 degrees | 0.094633 | 0.093310 |

At the upward-crossing start, +15 degrees retains about 15.94% more final energy than zero offset, but its peak flow is lower (0.61044 versus 0.62696). The +15-degree drive spends its budget by time 7.307; zero offset does so by 9.208. Different stopping phases, transient motion, and accumulated dissipation all matter. With the turning-point start, +15 degrees retains about 3.33% less energy than zero offset. There is no universal best offset, even within this small experiment, and the best offset depends on the chosen outcome measure.

This is compatible with the earlier cosine-of-phase work calculation. That calculation held sinusoidal pressure and motion amplitudes fixed. This test changes the transient motion using a finite-width feedback pulse and stops at a work budget, so its final stored energy is a different comparison.

The -75-degree cases do not spend the full budget by time 120 (positive work 0.35928 and 0.38821). They are excluded from the equal-budget table. They spend a substantial portion of the cycle opposing the motion.

Energy accounting uses E = (x^2+Q^2)/2 and E-E_initial = positive_work - absorbed_work - dissipation. Maximum residual is below 1e-10. Halving dt from 0.005 to 0.0025 for the zero and +15-degree cases changes final energy by less than 1.6e-10. These checks validate the numerical solution of this chosen feedback law; they do not establish that the law is physically optimal.

Code and full time series: [phase_budget.py](phase_budget.py), [phase_budget_results.json](phase_budget_results.json).

## 2. Spatial placement at fixed delivered energy

The existing incompressible periodic three-dimensional solver starts at rest, with viscosity 0.03 and domain [0,2pi)^3. Total delivered kinetic work is 0.156 through time 4, using the same power 0.04 and initial 0.2-time ramp in every case. A localized rotational drive sits on radius 0.8 at z = pi, with Gaussian width 0.38. Its location changes every 0.2 time units. There are twenty location slots.

Schedules are: one fixed position; cyclic 45-degree increments; golden-angle increments; increments of 360(sqrt(2)-1) degrees; a nearby rational increment of 360(55/144) = 137.5 degrees; and three seeded random schedules. The simultaneous-eight control distributes the drive across eight equally spaced locations at once. It has a different spatial actuator distribution, although it receives the same energy.

The rational 55/144 schedule would repeat after 144 slots, beyond this twenty-slot test. Its purpose is to check whether the observed finite-time effect requires exact irrationality. All numerical angle representations are finite precision; a computation cannot certify an angle's mathematical irrationality from its decimal representation.

The energy-calibrated velocity increments always add the prescribed work. This is an ideal powered numerical controller. It is not a magnet, a resolved mechanical actuator, or a construction with smooth forcing at all space-time scales. The flow here does not have the reservoir oscillator's global back-and-forth degree of freedom, so this spatial test does not claim to synchronize pulses to that absent motion.

The primary transport diagnostic integrates upward volume flux through z = pi+0.8 over time. A parcel can cross repeatedly, and downward flow balances upward flow: this measures circulation across a plane, not unique fluid delivered elsewhere or escape from the domain. Effective energy volume fraction, mean(e)^2/mean(e^2), is also recorded; smaller values mean a more concentrated kinetic-energy distribution.

Numerical comparisons and refinement results are saved alongside this report in the ring-placement JSON files. The completed comparison table is below.

<!-- PLACEMENT_RESULTS_START -->
| Schedule | Upward crossing volume, 24 cubed | Upward crossing volume, 32 cubed | Final energy, 32 cubed | Effective energy volume fraction, 32 cubed |
|---|---:|---:|---:|---:|
| Eight simultaneous drives | 6.326024 | 6.317065 | 0.072181 | 0.057959 |
| One fixed drive | 6.617904 | 6.222777 | 0.051603 | 0.060671 |
| 45-degree cyclic steps | 5.112957 | 5.080048 | 0.060091 | 0.048752 |
| Golden-angle steps | 5.938068 | 5.937016 | 0.067144 | 0.056107 |
| sqrt(2) steps | 5.842932 | 5.852505 | 0.066293 | 0.055924 |
| Rational 137.5-degree steps | 5.938050 | 5.936988 | 0.067143 | 0.056106 |
| Random seed 2026 | 5.390052 | 5.370044 | 0.058942 | 0.051471 |
| Random seed 2027 | 5.420565 | 5.389807 | 0.053760 | 0.052513 |
| Random seed 2028 | 5.373511 | 5.370287 | 0.057398 | 0.050097 |

At 32 cubed, golden-angle scheduling gives 16.87% more upward crossing volume than the 45-degree cyclic schedule in this run. The nearby rational schedule differs from the golden result by only 0.000469%. This is evidence for the effect of spatial scheduling, not for a requirement of mathematical irrationality.

The largest crossing-volume change between the grids is 6.35%. Rankings of close alternatives must therefore be treated cautiously. These are two grid sizes, not an established asymptotic convergence study.

Accepted paired time-step checks at 32 cubed change crossing volume by at most 0.0092%. The 45-degree schedule at dt = 0.02 exceeded the chosen CFL limit (0.520853 versus 0.5), so that run was rejected and is not included in the accepted comparisons. All nine schedules were completed at dt = 0.01.

Across accepted runs the maximum absolute energy residual is 7.1e-08, and maximum CFL is 0.4150. At 32 cubed, the largest measured speed is 3.59232 and sampled vorticity magnitude is 18.28164, both finite. These finite-grid peaks are not proofs about continuum regularity.

Data: [24 cubed](ring_placement_24_0.02_results.json), [32 cubed](ring_placement_32_0.01_results.json), [accepted coarser-time comparisons](ring_placement_32_0.02_results.json).
<!-- PLACEMENT_RESULTS_END -->

Code: [ring_placement.py](ring_placement.py). Run `python ring_placement.py --n 24` for the coarse grid and `python ring_placement.py --n 32 --dt .01` for the finer grid. Selected accepted comparisons at dt = 0.02 provide the temporal check; the 45-degree schedule needs the smaller step to satisfy the chosen CFL limit.

## 3. A magnetic sheet and a closed return path

For a concrete magnetic interpretation, the fluid is assumed to have a positive, weak, linear magnetic response. In this approximation the magnetic force density is proportional to chi times the gradient of B^2/2. Field direction and force direction are therefore different quantities. A negatively susceptible liquid would have a different attraction/repulsion response.

A two-mode strip pattern represents a sheet above the fluid, at z = 1.25. Below it, define

    b1 = exp(z-1.25), b2 = 0.25 exp(2(z-1.25))
    Bx = b1 sin(x) + b2 sin(2x)
    Bz = -b1 cos(x) - b2 cos(2x).

This prescribed field is curl-free and divergence-free in the fluid region. The magnetic potential factor is

    Phi = B^2/2 = (b1^2+b2^2)/2 + b1 b2 cos(x).

The scaled acceleration is chi grad(Phi), with physical susceptibility, density, permeability, and field-amplitude factors absorbed into the units. Values chi = 1 +/- 0.25 below mean relative response, not a calibration asserting weak physical susceptibility equals one. Demagnetization, saturation, free-surface stresses, conducting-fluid effects, and magnetization dynamics are omitted.

Across the sampled region 0 <= z <= 1, the vertical field component changes sign, but the magnetic acceleration for uniform positive response points upward everywhere: its minimum is 0.06529 in these units. Thus following a field line upward and then downward is not the force law for this fluid.

For uniform chi, the bulk magnetic force is a gradient. Pressure can balance it in a homogeneous filled container, and its line integral around a closed path is zero. Free-surface deformation and transient attraction are outside that static bulk conclusion.

To test a possible circulation mechanism, prescribe a rectangular conduit rising at x = 0 from z = 0.1 to z = 1, crossing to x = pi, returning downward, and closing at the bottom. The return path is **imposed by this conduit model**, not discovered as a free vortex trajectory. Let chi(x) = 1 + epsilon cos(x). This gives a stronger magnetic response on one side and a weaker response on the other.

| Maintained response contrast epsilon | Integrated drive around the conduit | Late volume flow |
|---:|---:|---:|
| 0 | approximately 0 (-4.4e-16) | approximately 0 (2.7e-9) |
| +0.25 | +0.132159 | +0.356027 |
| -0.25 | -0.132159 | -0.356027 |

The reduced conduit dynamics are Q' = drive - 0.3Q - 0.2|Q|Q, starting at Q = 0.2 and run to time 60. With uniform response, the initial circulation decays. With maintained contrast, a finite steady flow develops; swapping the contrast reverses the flow. The asymmetry in force response, rather than the drawn direction of field lines, supplies the net drive in this model.

**The contrast is an imposed resource.** A temperature-dependent magnetic response could provide such a difference, but this calculation does not solve heating, cooling, advection of temperature, or the total thermodynamic energy budget. Maintaining contrast while liquid circulates would require an explicit physical mechanism. The mechanical work attributed to that maintained contrast is accounted for; it is not energy from an inexhaustible static magnet.

The line-integral results agree at 64- and 128-point quadrature to within 1e-12. Finite-difference checks of the field equations and force gradient have errors below 1.2e-10. The conduit flow agrees with its analytic steady value within 3e-9, and mechanical energy residuals are below 5.2e-13.

Code and diagnostics: [magnetic_sheet.py](magnetic_sheet.py), [magnetic_sheet_results.json](magnetic_sheet_results.json).

## Interpretation for blow-up

A finite-speed circulation can rise on one side and return on another. Turning around a loop, reaching a magnetic plate, or encountering a field-line bend does not require infinite speed. If a Navier-Stokes singularity is the objective, one must establish unbounded behavior at a finite time under the specified equations; no geometrical requirement places it before the turn. A classical smooth solution cannot simply be assumed to continue through a singular event.

The relation Q = area times mean speed is not sufficient to require a singularity either: prescribing a vanishing conduit area while demanding fixed nonzero flow imposes the divergence by assumption. Under finite available pressure, the volume flow may instead decrease. The fluid equations would have to generate concentration under the permitted smooth data and forcing, rather than receiving an infinite force or singular boundary from the model designer.

None of these tests establishes that behavior. Energy conservation alone does not exclude local concentration in the full PDE, and finite-grid results do not resolve arbitrarily small scales. The tests identify effects of phase, spatial scheduling, and a specified magnetic coupling, while retaining those distinctions.

The most concrete follow-on would be to give the magnetic response contrast an evolving temperature field, with explicit heater input and cooling, and ask whether it produces the desired circulation before adding the full vortex geometry.

## Physical references

- [NASA, Models of Ferrofluid in a Magnetic Field](https://ntrs.nasa.gov/api/citations/19680021013/downloads/19680021013.pdf): magnetic body forces depend on magnetization and gradients of field strength; force and equilibrium require a fluid model.
- [Finlayson, Convective instability of ferromagnetic fluids](https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/abs/convective-instability-of-ferromagnetic-fluids/D20A7EEB218B85A7A80B0110108B1832): the original study describes convection from temperature-dependent magnetization under imposed thermal conditions. Its abstract supports the mechanism; our prescribed contrast is not a reproduction of that stability calculation.
