**Temperature-dependent magnetism, an aperture, and a returning liquid loop — 12 September 2026**

Cooling can strengthen the magnetic response of a suitable liquid, so the proposed hot-to-cold path is worth testing. The full passage matters: a stronger attraction on approach can become stronger braking on departure. Our new reduced tests support thermally driven circulation with suitable heater placement; they do not produce or establish a Navier–Stokes singularity.

**What the computer search recovered**

The closely related earlier files are in `C:\Users\GamerTech\Desktop\Vesica AI\Physics`:

- [magnetism_alpha_point.py](<C:/Users/GamerTech/Desktop/Vesica AI/Physics/magnetism_alpha_point.py:159>) fits an assumed atomic-number-distance formula to three hard-coded Fe/Co/Ni magnetic moments. Its later temperature discussion proposes an alpha coordinate and a colder strongest state. It does not provide measured magnetization-versus-temperature curves or establish a universal material law.
- [ferrofluid_pulser_pump.py](<C:/Users/GamerTech/Desktop/Vesica AI/Physics/ferrofluid_pulser_pump.py:497>) contains the earlier magnetic pump proposal. Its `run_cycle` repeatedly credits an algebraic energy estimate without evolving a depleted supply or an actual thermal cycle. Those printed totals cannot verify sustained energy extraction. Its discussion near line 737 links cooling and magnetism conceptually.
- [buildable_ferrofluid_pump.py](<C:/Users/GamerTech/Desktop/Vesica AI/Physics/buildable_ferrofluid_pump.py>) contains proposed construction and observation guides; [pulser_pump_theory.py](<C:/Users/GamerTech/Desktop/Vesica AI/Physics/pulser_pump_theory.py>) contains simplified cycle and symmetry models. The inspected files are proposals/calculations, not laboratory measurement records.

This recovers relevant history, but the searched material does not yet identify the remembered measured temperature “sweet spot.” The alpha/atomic-number interpretation is not used as a physical constitutive law in the new tests.

There is an established physical counterpart: temperature-sensitive ferrofluid pumps. An experimental closed-loop device used a heat source, heat sink, and permanent magnet to circulate ferrofluid. The energy supply is the heat source. [Experimental study, 2019](https://doi.org/10.1007/s42452-019-1738-z). A material study found that cooling performance depends on saturation magnetization, thermal response, viscosity, and other properties; within its tested conditions, putting the Curie temperature near the heat-load temperature improved performance. That is an operating-range result, not a universal maximum-magnetism temperature for every substance. [Pattanaik et al., 2021](https://www.nature.com/articles/s41598-021-03514-2).

**Test 1: finite-speed passage through a hole**

We represent an aperture by the axis of a thin circular current loop. This is an analytically known field surrogate, not the computed field of a particular magnetized plate. In dimensionless units,

\[
B(z)=(1+z^2)^{-3/2},\quad \Phi(z)=B^2/2,
\qquad \dot z=v,\quad \dot v=\chi\Phi'(z)-\gamma v.
\]

The axial current-loop field follows the Biot–Savart law. [OpenStax derivation](https://openstax.org/books/university-physics-volume-2/pages/12-4-magnetic-field-of-a-current-loop). We assume positive, constant linear magnetic response in this transit test; temperature evolves in Test 2. The path is constrained to the axis. Radial attraction to the rim, walls, gravity, and free-surface deformation are omitted.

The magnetic force points toward the plane from either side and is zero at the central field maximum. Magnetic braking is reversible work against attraction; viscous drag is a separate dissipative term.

| Response χ | Drag γ | Speed at z = −3 | Speed near the aperture | Outcome |
|---|---:|---:|---:|---|
| 0.6 | 0 | 0.25 | 0.814 | Reaches z = +3 at speed 0.25 |
| 1.2 | 0 | 0.25 | 1.123 | Reaches z = +3 at speed 0.25 |
| 0.6 | 0.05 | 0.25 | 0.749 | Crosses, then returns and oscillates near the aperture during the run |
| 1.2 | 0.05 | 0.25 | 1.065 | Crosses, then returns and oscillates near the aperture during the run |
| 1.2 | 0.05 | 1.00 | 1.374 | Reaches z = +3 at speed 0.658 |

All speeds are finite. With no drag, the incoming and outgoing speeds at equal field strength agree because \(v^2/2-\chi\Phi\) is conserved. With drag, additional finite launch energy can still get through. These outcomes directly show why a return-directed magnetic force does not require infinite speed before the plate. “Reaches z = +3” is the test's exit condition, not an escape-to-infinity claim.

**Test 2: temperature evolves around a closed liquid path**

The earlier magnetic-sheet experiment imposed a susceptibility contrast. This experiment instead evolves temperature through advection, diffusion, finite heat exchange, magnetic thermal coupling, and drag heating. The assumed liquid stays in one phase. A closed conduit and a uniform bulk flow are prescribed; vortices and the return path do not emerge from a 3D simulation.

Let \(s\) run periodically from \(-\pi\) to \(\pi\), with positive flow crossing the aperture at \(s=0\). We choose a smooth field-energy profile \(\Phi(s)=\exp[4(\cos s-1)]\). This is an illustrative field-strength landscape along the path, not a globally solved Maxwell field for a plate. The heater and cooler are localized smooth zones of width parameter 0.35.

The assumed dimensionless susceptibility is \(\chi(T)=a-bT\), with \(a=1.8\), \(b=0.6\). Temperatures, response values, and rates are illustrative scaled quantities, not kelvin, degrees Celsius, or calibrated material data. All simulated temperatures remain positive and all susceptibilities remain positive. There is no fitted Curie transition or imposed threshold switch.

Writing angle brackets for a spatial mean, the equations are

\[
\dot Q=\langle\chi(T)\Phi_s\rangle-RQ-C|Q|Q,
\]
\[
c(T_t+QT_s)=c\kappa T_{ss}+q_h+q_c+bTQ\Phi_s+D,
\quad D=RQ^2+C|Q|^3.
\]

Here \(c=4\), \(R=0.05\), \(C=0.03\), and \(\kappa=0.003\). The baths have temperatures 2 and 1; heat exchange is proportional to the local bath–liquid temperature difference. The default exchange rate is 0.8. Every case starts from uniform temperature 1.5 and the same seed flow 0.15. Runs end at time 300.

The magnetic thermal term follows an explicit illustrative free energy,

\[
\psi=cT(1-\ln T)-(a-bT)\Phi,
\quad S=c\ln T-b\Phi,\quad e=cT-a\Phi.
\]

Consequently, with drag heat returned to the liquid,

\[
\frac{d}{dt}\left[\frac{Q^2}{2}+c\langle T\rangle-a\langle\Phi\rangle\right]
=\langle q_h+q_c\rangle.
\]

This makes the heat cost of magnetic work explicit. It is a consistent toy constitutive model, not a validated equation of state for a real ferrofluid. Static-field interaction is included in this effective energy; field-source dynamics are not simulated.

| Arrangement | Final flow, 96 cells | Final flow, 192 cells | Heat received from hot bath, 192 cells |
|---|---:|---:|---:|
| Hot base at −2.2, cooling on approach at −0.8 | 0.002189 | 0.002174 | 7.640 |
| Same arrangement, slower cooling (0.1) | 0.001088 | 0.001074 | 3.592 |
| Same arrangement, faster cooling (3.2) | 0.002753 | 0.002751 | 12.994 |
| Heat at aperture, cool on remote return | 0.504012 | 0.513502 | 46.014 |
| Heat slightly after aperture (+0.35), cool on return | 0.517865 | 0.522700 | 49.926 |
| Heat at aperture, slower return cooling (0.1) | 0.228311 | 0.234946 | 11.748 |
| Heat at aperture, faster return cooling (3.2) | 0.588013 | 0.597597 | 62.644 |
| Temperature-independent susceptibility | 0.000000042 | 0.000000042 | 2.386 |
| No magnetic field | 0.000000042 | 0.000000042 | 2.386 |

The bath temperatures and baseline coupling strengths are controlled, but the heat consumed differs. This is a placement comparison, not an equal-energy efficiency ranking. The small hot-base flows still have a slowly changing temperature distribution; the larger aperture-heated flows are essentially stationary over the last 30 time units. The two spatial grids support the qualitative distinction; they do not establish an exact optimum or a continuum-converged flow rate.

Cooling on approach does not by itself ensure a large net gain. A useful circuit has stronger response while entering increasing field strength and weaker response while leaving it. In the usual temperature-sensitive response, this means cold approach followed by heating through the strong-field region. The remote cooling region then prepares the next circuit. A published thermomagnetic-loop analysis makes the same entry/exit force distinction and locates its field around the heater. [Aursand et al., section 6.1](https://arxiv.org/html/1605.09554v1).

Thus the proposed hot vortex can supply heat, but its location relative to the magnetic-force gradients is crucial. Cooling all the way into the aperture without subsequently weakening the exit attraction is not sufficient to guarantee strong circulation. The chosen hot-base arrangement still produces a small positive flow, so this test does not justify declaring that arrangement universally impossible.

**Controls and numerical checks**

- The 11 cases ran at 96 cells with time step 0.02 and 192 cells with time steps 0.01 and 0.005. Spatial advection uses conservative first-order upwinding; diffusion uses a centered second derivative; time integration uses RK4. Numerical diffusion is included in the limitations.
- Halving the time step at 192 cells changes final flow by at most \(4.10\times10^{-11}\). The four sustained aperture-heated flows change by approximately 0.9–2.9% between spatial grids. More grids would be needed for quantitative extrapolation.
- The maximum recorded total-energy discrepancy is \(1.48\times10^{-11}\); the separate kinetic-work discrepancy is \(1.47\times10^{-11}\). The maximum recorded advection-plus-diffusion step indicator is 0.239. Positive temperature and response are checked throughout.
- Fluid-plus-bath entropy change remains nonnegative in the accepted runs, including entropy produced by numerical diffusion. This is a consistency check for the chosen model, not experimental validation.
- The no-field and constant-response controls match the analytic viscous decay law, ending at \(Q=4.21\times10^{-8}\). No net magnetic work is available from a constant susceptibility around this fixed closed path.
- Equal-temperature baths leave only a small decaying transient: final \(Q=-8.56\times10^{-6}\), with late mean about \(-1.15\times10^{-5}\). This is not a sustained pumping result.
- Switching off both thermal exchanges at time 120 leaves a decaying oscillation. Its last-30-time-unit RMS flow is 0.00430, versus sustained flow 0.51350 with exchanges maintained. Its instantaneous final flow is phase-sensitive between grids; it should not be quoted as a settled residual flow.
- The aperture energy checks are below \(3.2\times10^{-12}\). Halving the lossless transit time step preserves the exit time to within \(10^{-8}\) and returns the same finite outgoing speed.

The tests support a possible heat-driven magnetic circulation mechanism. They do not establish a link to void lines, quantum entanglement, the original weighted theta equation, or finite-time blow-up of the full 3D equations. Finite energy alone would not rule out a spatial singularity; this reduced model cannot resolve that question.

The next physically discriminating input is a measured \(M(B,T)\) curve for a chosen single-phase liquid or suspension, alongside its viscosity and heat capacity. Those data would determine whether cooling along the available travel time actually changes the response enough. A real aperture field and its radial forces would then need to replace the prescribed path profile.

Reproducible files: [simulation](D:/shovelcat-colony/navier_stokes_theta/temperature_aperture.py), [summary and control checks](D:/shovelcat-colony/navier_stokes_theta/summarize_temperature_aperture.py), [192-cell results](D:/shovelcat-colony/navier_stokes_theta/temperature_aperture_192_0.01_results.json), [numerical audit](D:/shovelcat-colony/navier_stokes_theta/temperature_aperture_checks.json).

```powershell
python navier_stokes_theta/temperature_aperture.py --n 96 --dt 0.02 --transit
python navier_stokes_theta/temperature_aperture.py --n 192 --dt 0.01
python navier_stokes_theta/temperature_aperture.py --n 192 --dt 0.005
python navier_stokes_theta/summarize_temperature_aperture.py
```
