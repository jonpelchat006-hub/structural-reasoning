**An upward spiral between two downward regions — 12 September 2026**

The new 3D tests produce rising spiral paths in an annulus while the center and an outer region move downward. This pattern persists with moderate swirl. Stronger swirl changes the return geometry, and the tracked rising paths widen instead of forming a contracting, tightly wound column. No velocity blow-up is established by these finite-resolution, finite-duration calculations.

**Recovered earlier designs**

The purifier idea is in *Unified Waveguide Civilian Applications*, page 5, section 2.2, “Double-Helix Flow Geometry.” It proposes counter-rotating helical transport paths. Page 8 explicitly discusses tighter pitch increasing contact length at a cost to throughput. Page 17 places laboratory demonstration and characterization in a future development roadmap. These are design proposals, not measured flow results. The complete relevant pages were extracted and visually inspected. :codex-file-citation{path="D:/shovelcat-colony/companion/library/Unified_Waveguide_Civilian_Applications.pdf" purpose="source"}

The related *MD-DEDS Concept Paper v5*, page 3, section 2.1, describes a triple-helix optical vortex pattern. This confirms the remembered geometric connection; an optical intensity pattern is not itself a measurement of a liquid's velocity. No device performance or containment claims from that proposal are assumed in this fluid test. :codex-file-citation{path="D:/shovelcat-colony/companion/library/MD-DEDS_Concept_Paper_v5.pdf" purpose="source"}

The previously saved eight-drive liquid run demonstrated upward flow outside a central downward return. It did not establish the additional outer downward region now requested. The present test therefore uses a new forcing shape that deliberately includes both downward regions around a rising annulus. It tests how added swirl changes that seeded geometry, not whether the geometry appears spontaneously.

**What was simulated**

The solver evolves incompressible 3D Navier–Stokes flow in a periodic cube of side \(2\pi\), initially at rest, with viscosity \(\nu=0.03\). The total delivered kinetic energy is **0.156 in every case**. Power rises linearly to 0.04 over the first 0.2 time units and remains supplied until the endpoint, time 4. All quantities are dimensionless.

The upward/downward forcing shape comes from the curl of an azimuthal vector potential,

\[
A_\phi=r(r^2-1)e^{-r^2/0.8}\,g(z),
\qquad g(z)=e^{-(z-\pi)^2/(2\times0.8^2)}.
\]

Before spectral projection, its vertical component is upward between approximate radii 0.597 and 1.498, and downward on either side. A separate smooth rotational shape around the column axis is centered near radius 1.05. Both are projected into divergence-free, band-limited, periodic fields with zero mean and normalized to equal spatial squared norm. The rotational shape is orthogonalized against the first shape.

The direction supplied to the powered controller is

\[
d=\sqrt{1-\beta}\,d_{\rm circulation}
 +\sqrt{\beta}\,d_{\rm swirl},
\quad \beta\in\{0,0.25,0.75,0.95,1\}.
\]

Here “25% swirl shape” means \(\beta=0.25\), the squared-norm mixing parameter of the forcing direction. It is **not** the percentage of actual kinetic energy or delivered work in swirl after the flow evolves. Actual radial, tangential, and axial kinetic energies are recorded separately.

Energy-calibrated increments act before and after each unforced RK4 step. This is an ideal numerical actuator, not a motor model or the smooth forcing needed for a mathematical singularity construction. There are no tube walls, magnetic plate, heat source, free surface, gravity, phase changes, or theta-dependent material properties in this experiment. In particular, it does not test confinement by the earlier proposed tube.

**Results at 32 cubed resolution**

Vertical averages below are at the drive plane \(z=\pi\), at time 4: center \(r<0.5\), rising band \(0.75<r<1.35\), and outer region \(1.65<r<2.15\). Negative means downward.

| Swirl-shape parameter | Maximum total speed during run | Center mean vertical speed | Band mean vertical speed | Outer mean vertical speed | Sampled maximum vorticity |
|---|---:|---:|---:|---:|---:|
| 0 | 3.29819 | −0.85251 | +0.73356 | −0.28333 | 7.77444 |
| 0.25 | 2.81299 | −0.95741 | +0.81966 | −0.22195 | 6.81048 |
| 0.75 | 1.80812 | −1.28135 | +0.88195 | −0.03248 | 4.94386 |
| 0.95 | 1.58414 | −1.02924 | +0.32978 | +0.20647 | 3.22216 |
| 1, rotation-only forcing | 1.59304 | approximately 0 | approximately 0 | approximately 0 | 3.20760 |

At moderate swirl, the requested radial ordering exists: **downward center, upward spiraling band, downward exterior region**. At parameter 0.75 the outer downward average is weak. At 0.95 that region becomes upward, although downward motion still occurs farther out; the chosen three-band arrangement has changed.

Added swirl can raise the mean upward velocity in the selected band while lowering the maximum total speed anywhere in the domain. These are different diagnostics. The integrated positive crossing volume through the whole drive plane decreases from 14.446 without swirl to 14.109, 12.801, and 8.064 at parameters 0.25, 0.75, and 0.95. This counts crossings, including possible repeated crossings, not unique transported fluid or escape. Net plane flux remains zero.

The rotation-only control has essentially zero vertical speed at the symmetry plane, but does develop finite secondary vertical motion elsewhere. It is not a motionless-fluid control.

Strong coupling between rotational and axial motion, including axial stagnation or reversal, is also found in ordinary viscous swirling-flow studies. Such “vortex breakdown” is a flow-structure change and should not be equated with infinite velocity. [Primary Navier–Stokes study](https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/abs/solutions-of-the-navierstokes-equations-for-vortex-breakdown/E772C440A161AB18E5DFBA6E999624BD).

**Did a tight rising coil form?**

We followed 64 passive parcels at each of three initial radii, 0.25, 1.05, and 1.9, starting at time 1 and height \(\pi-0.4\). These labels follow the fluid; they have no independent inertia or propulsion. Positions remain unwrapped to identify periodic boundary crossings. Angular diagnostics stop counting after a boundary crossing and exclude radii below 0.2. A continuous upward segment requires vertical speed above 0.02.

For the initially annular group:

| Swirl-shape parameter | Median maximum height gain | Median most turns in one continuous upward segment | Median largest radius while rising |
|---|---:|---:|---:|
| 0 | 2.519 | 0.00018 | 1.740 |
| 0.25 | 1.971 | 0.311 | 1.877 |
| 0.75 | 1.002 | 0.343 | 1.873 |
| 0.95 | 0.505 | 0.322 | 1.863 |
| 1 | 0.105 | 0.243 | 1.504 |

The mixed cases show rising spiral arcs, not multiple tightly packed turns. Their initial radius is 1.05, and the trajectories widen substantially. No annular label completes the defined upward-then-downward crossing of its initial height by time 4, and none of that group crosses a periodic boundary during the observation window. The downward velocity regions therefore establish instantaneous return branches, not a demonstrated completed round trip by those same annular parcels.

For a locally helical path, pitch is \(p=2\pi r u_z/|u_\phi|\). Small pitch means a small axial rise per revolution. It can result from slower axial motion, so it is not by itself evidence of increasing total speed. The full speed \(\sqrt{u_r^2+u_\phi^2+u_z^2}\), radius, and gradients must be examined separately.

![Computed parcel paths, radial velocity profiles, and maximum-speed histories](D:/shovelcat-colony/navier_stokes_theta/helical_annulus_results.png)

The figure uses actual computed trajectories, with no extra idealized turns added. It shows one seed from each radial group in the 0.25 case, clipped before any periodic-boundary crossing, along with final radial averages and speed histories. The complete recorded sample trajectories are in the result files.

**Verification and limits**

Twelve runs completed: five forcing mixes at each of 24 cubed and 32 cubed, one 32-cubed repeat with the time step halved, and one reversed-handedness check at 24 cubed. The spectral solver uses projection and strict two-thirds dealiasing. Time step is 0.01, or 0.005 in the repeat.

- Maximum total-speed changes between spatial grids are below 2.5%; sampled peak-vorticity changes are below 5.4%. Detailed regional averages are less settled: the no-swirl central mean changes from −1.158 to −0.853, a difference of about 36% relative to the finer-grid magnitude. Two grids do not establish quantitative continuum convergence.
- Halving the time step for parameter 0.75 changes peak speed by \(1.21\times10^{-5}\), peak vorticity by \(9.11\times10^{-7}\), and integrated dissipation by \(2.97\times10^{-7}\).
- Reversing the swirl handedness preserves scalar speed, vorticity, and dissipation to within \(3\times10^{-15}\), and reverses the signed parcel rotation, as expected for this symmetric setup.
- The maximum kinetic-energy balance error is \(3.26\times10^{-10}\). Maximum recorded CFL is 0.168, divergence is below \(1.51\times10^{-16}\), and net plane flux is below \(7.31\times10^{-16}\).
- An independent prescribed solid-body helix validates the parcel tracker: position error is below \(2.74\times10^{-7}\), and turn-count error below \(2.30\times10^{-8}\).
- Total speed is evaluated every time step; vorticity and detailed diagnostics are sampled every 0.1 time units. The finite simulation duration does not establish long-time stability. In particular, the 0.75 speed is still growing late in the run; that finite growth is not a demonstrated singularity.

The tests demonstrate this flow geometry within the numerical model, with a tradeoff between rotation, axial transport, and the placement of downward flow. They supply no evidence that this configuration develops an infinite speed. Finite energy does not by itself rule out a localized Navier–Stokes singularity, and this experiment is not a proof about the full equation.

The main missing mechanism for the specific “tightening coil” hypothesis is a demonstrated inward focusing process that survives viscous diffusion while accounting for its energy input. A physical tube could constrain spreading, but introduces walls and additional stresses; it has not been modeled here.

Reproduce from `D:\shovelcat-colony`:

```powershell
python navier_stokes_theta/helical_annulus.py --n 24
python navier_stokes_theta/helical_annulus.py --n 32
python navier_stokes_theta/helical_annulus.py --n 24 --fractions 0.75 --sign -1
python navier_stokes_theta/helical_annulus.py --n 32 --dt 0.005 --fractions 0.75
python navier_stokes_theta/summarize_helical_annulus.py
```

[Simulation](D:/shovelcat-colony/navier_stokes_theta/helical_annulus.py), [32-cubed data](D:/shovelcat-colony/navier_stokes_theta/helical_annulus_32_0.01_1_4_4_results.json), [verification results](D:/shovelcat-colony/navier_stokes_theta/helical_annulus_checks.json), [vector figure](D:/shovelcat-colony/navier_stokes_theta/helical_annulus_results.svg). The figure builder uses Matplotlib installed in an isolated temporary package directory, leaving the simulation environment unchanged.
