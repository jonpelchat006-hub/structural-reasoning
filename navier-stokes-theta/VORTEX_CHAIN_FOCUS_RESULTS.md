**Chaining vortex stages, entry focusing, and a possible circular path — 12 September 2026**

A second aligned stage carries the tagged fluid through the upper region in these tests. There is a small indication of radial narrowing on entry to that stage, followed by stronger widening on departure. The chain therefore improves transport in this setup but does not produce lasting compression, a shrinking radius, or a demonstrated velocity singularity.

**Why entering below a stage can matter**

The circulation component of our chosen forcing shape has radial direction proportional to

\[
d_r=-r(r^2-1)e^{-r^2/0.8}g'(z),
\qquad g(z)=e^{-(z-z_{\rm stage})^2/(2\times0.8^2)}.
\]

Below a stage, \(g'>0\). This pushes material outside radius 1 inward and material inside radius 1 outward, toward a preferred annular radius. Above the stage, those radial directions reverse. Thus the proposed entry side is a plausible focusing region for this shape, but the departure side can undo it. The preferred radius 1 was built into the forcing model; it is not a measured material property, theta threshold, or physical void line.

This formula describes the imposed forcing direction, not the resulting velocity. The new runs test the fluid response, including pressure, advection, swirl, and viscosity.

For incompressible liquid, narrowing a material element requires compensating extension in another direction; density does not simply increase. This is the geometrical basis of vortex stretching, although viscous dynamics must also be accounted for. [Fluid-dynamics notes](https://math.nyu.edu/faculty/tabak/vorticity.pdf).

**What was run**

Six three-dimensional periodic Navier–Stokes runs completed: three arrangements at each of 24-cubed and 32-cubed resolution. The side length is \(2\pi\), viscosity 0.03, time step 0.01, and duration 6. All start at rest. Each receives the same delivered kinetic energy, **0.236**, through the existing controller: power rises to 0.04 over the first 0.2 time units, then remains supplied.

The lower stage is at \(z=2\); the optional upper stage is at \(z=3.6\). Each uses the preceding experiment's moderate-swirl forcing shape, with mixing parameter 0.25. The three arrangements are one stage, an aligned pair, and a pair with the entire upper forcing direction reversed. The combined direction is normalized before energy increments are applied. The pair does not receive twice the total energy, and the separate work delivered by each stage is not independently fixed.

At time 1, 144 passive labels start at height 1.6: 48 equally spaced azimuths at each radius 0.95, 1.10, and 1.25. They are tags in the existing liquid, not newly injected mass. We record first upward crossings of the upper stage's entrance, waist, and exit planes at heights 3.0, 3.6, and 4.2. Crossings after any periodic-boundary crossing are excluded. The same labels are compared at both ends of each reported segment.

These are ideal powered body-force stages. No tube walls, magnets, heating, gravity, real inlet/outlet, central attracting object, or circular geometry is included.

**Transport result**

Both spatial grids give these counts by time 6:

| Arrangement | Reach entrance, z=3.0 | Reach waist, z=3.6 | Reach exit, z=4.2 |
|---|---:|---:|---:|
| Lower stage only | 144/144 | 48/144 | 0/144 |
| Aligned pair | 144/144 | 144/144 | 144/144 |
| Upper stage reversed | 0/144 | 0/144 | 0/144 |

This supports an orientation-dependent handoff between powered stages. Failure to reach a plane within six time units is not proof that a parcel can never reach it. These fixed seed locations are an exploratory sample, not a universal transport-efficiency measurement.

Peak total speeds on the finer grid are 2.81372, 2.47601, and 2.22837 for the one-stage, aligned-pair, and reversed-pair cases respectively. More successful transport through the upper region does not mean a higher maximum speed anywhere in the domain. All are finite during the observation interval.

**Did the upper stage squeeze the band?**

For the aligned pair, all 144 labels cross all three planes. Define radial spread as the standard deviation of their distances from the column axis at the crossing events. It measures variation around the mean annular radius, which is separate from the mean radius itself.

| Aligned pair diagnostic | 24 cubed | 32 cubed |
|---|---:|---:|
| Entrance-to-waist spread ratio | 0.97295 | 0.98230 |
| Waist-to-exit spread ratio | 1.05954 | 1.08353 |
| Entrance-to-exit spread ratio | 1.03089 | 1.06435 |

A ratio below 1 means narrower by this diagnostic. Both grids show small entry narrowing, then widening. The finer run gives approximately **1.8% narrowing on entry, 8.4% widening on departure, and 6.4% net widening across the complete upper stage**. The coarse run gives 2.7%, 6.0%, and 3.1% respectively. The small entry effect is not quantitatively converged; it should be treated as a tentative focusing signal.

On the finer grid, the mean annular radius moves from 0.9338 at entrance to 0.9770 at the waist and 1.1170 at exit. Thus the small reduction in spread is not a collapse toward the column axis. Mean crossing speed rises from 1.2816 to 1.3687 at the waist, then falls to 1.2893 at exit. Mean axial speed follows 0.9691, 1.0219, and 0.8921.

There are two measurement limitations. First, these are equal-weight label statistics at different crossing times, not simultaneous cross-sections of a steady material tube, volume-weighted widths, or a measured compression ratio. Second, only 48 labels reach the waist in the one-stage case; their entrance radii are nearly identical. Its large spread ratio is highly sensitive to the tiny denominator and spatial sampling, so it is not a useful quantitative comparison with the full 144-label aligned group.

![Transport counts and matched-label radial diagnostics](D:/shovelcat-colony/navier_stokes_theta/vortex_chain_focus.png)

**Horizontal orientation and the collider analogy**

Turning a straight chain horizontal is a rotation of this gravity-free model. A 90-degree coordinate rotation of the periodic cube would give equivalent dynamics. A real apparatus can differ because of gravity, buoyancy, free surfaces, and supports; those effects have not been modeled here.

Bending the chain into a circle introduces a different geometry. Fluid could travel around a large ring while swirling around its local centerline. The radius of the large orbit and the width of the local swirling band are independent quantities. Bending the large orbit does not automatically reduce that width.

The useful part of the CERN analogy is the division of functions. CERN uses dipole magnets to bend charged-particle beams, quadrupoles to focus them, and RF electric fields to supply energy. Its beams travel in vacuum. A liquid would need its own pressure, boundary, and body-force mechanisms to perform those roles. [CERN explanation](https://home.cern/how-accelerator-works/).

For circular motion at speed \(U\) and radius \(R\), the necessary normal acceleration is \(U^2/R\). A purely normal guide force does no instantaneous work because it is perpendicular to velocity. It changes direction, not speed. A central attraction can help bend an orbit, but a static conservative attraction does not add net energy on each completed circuit. Sustained acceleration must be supplied and balanced against losses.

No circular chain or central-attractor configuration was numerically tested in this turn. The periodic box should not be mistaken for such a simulation. The present evidence supports testing repeated transport stages, while leaving repeated net focusing and a closed curved loop unresolved.

**Checks and practical limits**

- Maximum kinetic-energy accounting error: \(9.46\times10^{-11}\); maximum recorded CFL: 0.144. Maximum recorded divergence is below \(1.74\times10^{-16}\), and net plane flux below \(7.31\times10^{-16}\).
- Peak speeds change by less than 2.7% between grids, and gate-arrival counts match exactly. The small width changes remain sensitive to spatial resolution. No time-step refinement of these particular chain runs was performed.
- The gate tracker was independently tested in an analytically known incompressible straining flow, \(u_x=-0.2x\), \(u_y=-0.2y\), \(u_z=0.4(z-1.6)+1\), with horizontal coordinates measured from the column axis. Gate-time errors were below \(1.12\times10^{-8}\), and width-ratio errors below \(2.00\times10^{-9}\).
- The solver uses projection, strict two-thirds dealiasing, and RK4 between discrete energy increments. The controller is not a smooth-forcing singularity construction. Neither finite duration nor finite energy accounting settles the full Navier–Stokes blow-up question.

Reproduce from `D:\shovelcat-colony`:

```powershell
python navier_stokes_theta/vortex_chain_focus.py --n 24
python navier_stokes_theta/vortex_chain_focus.py --n 32
python navier_stokes_theta/summarize_vortex_chain_focus.py
```

[Simulation](D:/shovelcat-colony/navier_stokes_theta/vortex_chain_focus.py), [finer-grid results](D:/shovelcat-colony/navier_stokes_theta/vortex_chain_focus_32_0.01_results.json), [checks](D:/shovelcat-colony/navier_stokes_theta/vortex_chain_focus_checks.json), [vector figure](D:/shovelcat-colony/navier_stokes_theta/vortex_chain_focus.svg).
