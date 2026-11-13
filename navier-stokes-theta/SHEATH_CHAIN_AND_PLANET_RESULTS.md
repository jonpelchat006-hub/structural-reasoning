**Surrounding the vortex chain, and using a planet to bend the large loop — 12 September 2026**

The surrounding drive changes passage through the upper stage. The opposite-spin forcing is the strongest candidate for reducing the entrance-to-exit spread in this small comparison. It does not hold the liquid in a fixed-width tunnel: the tagged annulus still moves outward, and its same-time radial spread grows again downstream. These results concern one chosen geometry and finite observation interval.

Two separate calculations were completed: **13 three-dimensional fluid runs** for the outer-layer comparison and refinement, and **five point-parcel trajectories** for the planetary-gravity question. The fluid calculation is straight and gravity-free. No combined planet-scale fluid ring, four-vortex launcher with solid magnetic apertures, or heat cycle was simulated.

**What gravity can do around a planet**

Your clarification places the planet at the centre of the large circular route. For a freely moving parcel, the circular-orbit condition is

\[
\frac{U^2}{R}=\frac{GM}{R^2},\qquad U_{\rm circ}=\sqrt{\frac{GM}{R}}.
\]

Here R is measured from the planet centre. Gravity can supply the inward acceleration that closes this orbit. It is perpendicular to the velocity of a circular orbit and does not keep increasing its speed. The formula and the distinction between height and orbital speed are described by [NASA](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/flight-to-orbit/).

Using explicitly rounded Earth parameters, GM = 3.986e14 m³/s² and radius 6371 km, the illustrative calculation at 400 km altitude gives speed **7.673 km/s**, period **92.41 minutes**, and local gravity **8.694 m/s²**. These are orbital calculations, not a validated liquid-ring design.

The separate dimensionless trajectory check starts at radius 1 with GM = 1. With gravity absent, the parcel follows its tangent. At the circular speed it completes the circle; at 0.8 or 1.2 times that speed it follows an ellipse; at 1.5 times that speed its positive orbital energy gives an unbound trajectory. The plotted duration is one reference circular period, which need not complete an ellipse. This point-gravity model omits a finite planet surface: an inward path could intersect a real planet before completing its mathematical orbit.

If we insist on the same radius while changing speed, another guide must supply the signed inward acceleration

\[
a_{\rm guide}=\frac{U^2}{R}-\frac{GM}{R^2}.
\]

At twice the circular speed, this is three times the local gravitational acceleration in addition to gravity. Thus planetary gravity helps bend the route at an appropriate speed; it does not close the same route at arbitrarily increasing speeds. Keeping the much smaller fluid cross-section together is another problem, involving pressure, shear, boundaries and gravity gradients.

![Separate point-gravity trajectory check](D:/shovelcat-colony/navier_stokes_theta/planet_orbit_check.png)

**What the surrounding-flow experiment contains**

The baseline is the previous pair of continuous annular driving shapes at z = 2 and 3.6, with inner swirl-mixing parameter 0.25. The domain is a periodic cube of side 2π; viscosity is 0.03, initial velocity is zero, and duration is 6. The powered controller supplies total kinetic work **0.236 in every case**, ramping to power 0.04 over the first 0.2 time units. It delivers discrete energy increments around unforced Navier–Stokes steps. This is an idealised drive, not a motor or magnetic-material model.

The new outer drive is centred on radius 1.8 with radial width parameter 0.35. Before incompressible projection its envelope is

\[
B(r,z)=\exp\!\left[-\frac12\left(\frac{r^2-1.8^2}{2(1.8)(0.35)}\right)^2\right]
\exp[0.8(\cos(z-3.1)-1)].
\]

An axial component B e_z and an azimuthal component B(-y,x,0)/1.8 are separately projected and normalized, with coordinates measured from the column axis. Their zero spatial modes are removed to preserve a mean-zero recirculating experiment. Projection and compensation introduce forces beyond the nominal annulus. Therefore the outer layer has no hard boundary, and the whole cross-section has zero net flux even when local streams move onward.

The spinning outer direction combines normalized axial and azimuthal shapes with coefficients sqrt(0.75) and ±sqrt(0.25). The axial-only control uses the axial shape. The final normalized direction is proportional to (1−η) times the inner direction plus η times the outer direction, with η = 0, 0.2 or 0.5. **η is a forcing-shape coefficient, not the fraction of delivered energy.** Equal total work allows the distribution of that work to change; the original core drive is not independently held fixed.

Each case tracks the same 144 inner fluid labels, seeded at time 1 and height 1.6 on radii 0.95, 1.10 and 1.25. An additional 144 outer labels start on radii 1.55, 1.80 and 2.05. They are passive tags in a single liquid, with no separate interface or material law. We record first upward crossings of z = 3, 3.6 and 4.2 before any periodic-boundary crossing.

**Comparison at equal total work**

The spread below is the standard deviation of label radii. The ratio is exit spread divided by entrance spread, using the same labels at both gates. Values below 1 indicate narrower radial spread at those crossing events. They do not measure density compression, shrinking mean radius, a simultaneous cross-section, or an infinite-time stable tube.

| Outer driving arrangement | Spread ratio, 24 cubed | Spread ratio, 32 cubed | Inner labels reaching exit, 32 cubed | Peak speed, 32 cubed |
|---|---:|---:|---:|---:|
| No outer drive | 1.03089 | 1.06435 | 144/144 | 2.4760 |
| Weak outer drive, same spin | 1.05960 | 1.08887 | 144/144 | 2.4371 |
| Strong outer drive, same spin | 1.04309 | 1.05228 | 144/144 | 1.9046 |
| Weak outer drive, opposite spin | 0.94844 | 0.97376 | 144/144 | 2.5607 |
| Weak outer drive, axial only | 0.98435 | 1.01040 | 144/144 | 2.5119 |

All 144 inner labels reach all three gates in every planned case and refinement. The ranking is therefore not produced by comparing different subsets of successful inner labels. The two same-spin outer drives do not give net narrowing across the upper stage in either grid. The axial-only result lies close to the no-change boundary and must be interpreted with its grid sensitivity.

**Refinement of the opposite-spin candidate**

| Grid | Bare spread ratio | Opposite-drive spread ratio | Bare absolute exit spread | Opposite-drive absolute exit spread |
|---|---:|---:|---:|---:|
| 24 cubed | 1.030886 | 0.948444 | 0.078598 | 0.076745 |
| 32 cubed | 1.064355 | 0.973759 | 0.080647 | 0.077880 |
| 40 cubed | 1.077672 | 0.984738 | 0.081201 | 0.078135 |

On the 40-cubed grid, the opposite-drive ratio is **0.984738**, versus **1.077672** without the outer drive. Its mean radius nevertheless increases from **0.9330 to 1.0783** across the same gates. Mean axial crossing speed changes from **0.9848 to 0.9998**; global peak speed is **2.5647**, versus **2.4778** for the baseline. All are dimensionless.

The absolute spread columns matter because each forcing arrangement changes the incoming band before it reaches the entrance gate. A favourable exit/entrance ratio does not by itself establish a proportionate improvement over the baseline's absolute exit width.

The opposite-drive narrowing weakens as the grid is refined (about 5.2%, 2.6%, then 1.5%). We therefore cannot yet establish that net narrowing survives the continuum limit. Its lower spread ratio relative to the bare chain, and smaller outward shift of the mean radius, are more consistent across these three grids. This is evidence for a change in local transport, not a precise converged focusing percentage.

The same-time cohort diagnostic provides an additional limit: by time 6, its radial spread is **0.1415** for opposite drive and **0.1319** for the baseline. Mean radii are respectively **1.8907** and **1.8843**. These cohorts occupy different heights, so this is a same-time transport diagnostic, not a same-location cross-section comparison. Both have spread again after the local focusing region.

“Opposite spin” identifies the imposed outer torque. It does not mean every part of the resulting outer liquid rotates oppositely: the measured velocity contains the response to both drives and their nonlinear interaction. In particular, the outer-region mean swirl changes with height. The data support reduced swirl in parts of that layer, not a uniformly counter-rotating tunnel.

![Measured spreading, mean radius and same-time cohort evolution](D:/shovelcat-colony/navier_stokes_theta/sheath_chain.png)

**Checks and interpretation**

The baseline reproduces the previous chain's peak speeds and gate-width ratios to 1e-12. Maximum energy-budget error across all new fluid runs is **3.59e-11**, maximum recorded CFL is **0.163**, divergence is below **1.09e-16**, and net gate-plane flux is below **1.22e-15**. Halving the opposite-drive time step at 32 cubed changes the spread ratio by **5.07e-06** and peak speed by **3.12e-05**. Spatial refinement is still needed to interpret small width differences; these checks do not amount to a convergence proof or a perturbation-stability study.

For the separate orbital integrator, maximum absolute specific-energy drift is **3.41e-11** in its dimensionless units. The circular path and gravity-off straight path also pass analytic position checks.

There is an experimental analogue for the broad idea of focusing a central stream with a rotating outer stream: [microfluidic vortex focusing](https://www.nature.com/articles/s41467-022-34750-3). That work uses a bounded chamber and also promotes mixing. It does not establish a free-standing planet-scale tunnel.

The present outer-layer test does not demonstrate lasting confinement or a Navier–Stokes singularity. The useful finding is a measurable dependence on how the surrounding flow is driven, together with a clear downstream spreading problem. Planetary gravity can guide the large orbit, while controlling this local spreading still requires its own fluid mechanism.

**Reproduce and inspect**

Run these commands from D:\shovelcat-colony:

```powershell
python navier_stokes_theta/sheath_chain.py --n 24
python navier_stokes_theta/sheath_chain.py --n 32
python navier_stokes_theta/sheath_chain.py --n 40 --modes bare counter_weak
python navier_stokes_theta/sheath_chain.py --n 32 --dt 0.005 --modes counter_weak
python navier_stokes_theta/planet_orbit_check.py
python navier_stokes_theta/summarize_sheath_chain.py
python navier_stokes_theta/write_sheath_report.py
```

[Fluid simulation](D:/shovelcat-colony/navier_stokes_theta/sheath_chain.py), [numerical checks and metrics](D:/shovelcat-colony/navier_stokes_theta/sheath_chain_checks.json), [orbital calculation](D:/shovelcat-colony/navier_stokes_theta/planet_orbit_check.py), [orbital results](D:/shovelcat-colony/navier_stokes_theta/planet_orbit_check_results.json), [fluid vector figure](D:/shovelcat-colony/navier_stokes_theta/sheath_chain.svg), [orbit vector figure](D:/shovelcat-colony/navier_stokes_theta/planet_orbit_check.svg).
