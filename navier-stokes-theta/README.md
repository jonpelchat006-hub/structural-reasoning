# Navier–Stokes theta

Numerical experiments on a dimensionless periodic Navier–Stokes solver, testing the framework's theta
diagnostic and the interface and "bubble" pictures built on it (September 2026).

**Start with [`INDEX.md`](INDEX.md).** It is the claim ledger: every result is marked established within the
model (E), suggestive (S), negative (N) or untested (U). As the index says, "model" always means the solver
in this folder, never a claim about the continuum equations.

- Each `*_RESULTS.md` is the write-up of one experiment and the `.py` of the same name produced it.
- `results/` has the small JSON outputs. The large ones and the saved fields (`.npz`) are left out.
- `ORIGINAL_THETA.md`, `THETA_CONSOLIDATED.md` and `PARAMETER_TABLE.md` cover the recovered theta formula and
  its parameters.

## Files

**``**

- [`FINDINGS.md`](FINDINGS.md) — Interpretation of the first tests
- [`FINITE_RESERVOIRS_RESULTS.md`](FINITE_RESERVOIRS_RESULTS.md) — Finite reservoirs and a reversing liquid column
- [`FOUR_VORTICES_RESULTS.md`](FOUR_VORTICES_RESULTS.md) — Four-vortex orientation comparison
- [`HELICAL_ANNULUS_RESULTS.md`](HELICAL_ANNULUS_RESULTS.md) — An upward spiral between two downward regions — 12 September 2026** The new 3D tests produce rising spiral paths in an annulus wh…
- [`INDEX.md`](INDEX.md) — navier_stokes_theta — index and claim ledger
- [`ORIGINAL_THETA.md`](ORIGINAL_THETA.md) — Recovered baseline theta formula
- [`PARAMETER_TABLE.md`](PARAMETER_TABLE.md) — Parameters the theory must fix — with the constraints the runs impose
- [`PHASE_PLACEMENT_MAGNETIC_RESULTS.md`](PHASE_PLACEMENT_MAGNETIC_RESULTS.md) — Phase, drive placement, and a magnetic sheet
- [`PIN_RING_RESULTS.md`](PIN_RING_RESULTS.md) — Ring of mechanical drive surrogates
- [`RESULTS.md`](RESULTS.md) — First theta / fluid experiment
- [`RETURN_PATHS_RESULTS.md`](RETURN_PATHS_RESULTS.md) — Does upward flow return?
- [`REVIEW_2026-09-13.md`](REVIEW_2026-09-13.md) — Outside review of the navier_stokes_theta folder, 13 September 2026
- [`RINGS_ADDENDUM.md`](RINGS_ADDENDUM.md) — Addendum — three rings, three radii, three rates (theta_rings.py, 17 Sep 2026)
- [`RING_LONG_RESULTS.md`](RING_LONG_RESULTS.md) — Longer powered loop and energy accounting
- [`RING_POWER_RESULTS.md`](RING_POWER_RESULTS.md) — Sustained power versus shutdown
- [`SEAM_TRIGGER_RESULTS.md`](SEAM_TRIGGER_RESULTS.md) — Localized seam-trigger hypothesis test
- [`SHEATH_CHAIN_AND_PLANET_RESULTS.md`](SHEATH_CHAIN_AND_PLANET_RESULTS.md) — Surrounding the vortex chain, and using a planet to bend the large loop — 12 September 2026** The surrounding drive changes passa…
- [`STACKED_LAYERS_RESULTS.md`](STACKED_LAYERS_RESULTS.md) — Stacking driven circulation layers
- [`TEMPERATURE_APERTURE_RESULTS.md`](TEMPERATURE_APERTURE_RESULTS.md) — Temperature-dependent magnetism, an aperture, and a returning liquid loop — 12 September 2026** Cooling can strengthen the magnet…
- [`THERMAL_LOOP_RESULTS.md`](THERMAL_LOOP_RESULTS.md) — Where dissipated energy goes
- [`THETA_CONSOLIDATED.md`](THETA_CONSOLIDATED.md) — A load-field interface for incompressible Navier–Stokes: what four days of numerics established, falsified, and left open
- [`THETA_FIELD_RESULTS.md`](THETA_FIELD_RESULTS.md) — The recovered theta, evaluated on the thermal ring — 13 September 2026
- [`THETA_FORMD_RESULTS.md`](THETA_FORMD_RESULTS.md) — Form D: magnitude-plane nucleation, geometry-gated sink, Q-R closure — 15 September 2026
- [`THETA_KINETIC_RESULTS.md`](THETA_KINETIC_RESULTS.md) — Form B: a kinetic theta coupled to Navier–Stokes — 13 September 2026
- [`THETA_REVIEW_20260915.md`](THETA_REVIEW_20260915.md) — Review of the recent theta work — 15 September 2026
- [`THETA_THREE_RESULTS.md`](THETA_THREE_RESULTS.md) — Form B with all three factors live — 13 September 2026
- [`THETA_TUBES_RESULTS.md`](THETA_TUBES_RESULTS.md) — Interface formation without a forced hot channel: antiparallel tubes — 14 September 2026
- [`THRESHOLD_TRANSPORT_RESULTS.md`](THRESHOLD_TRANSPORT_RESULTS.md) — Common thresholds and transport near the thermal maximum
- [`VORTEX3D_RESULTS.md`](VORTEX3D_RESULTS.md) — Two helical tubes with localized forcing
- [`VORTEX_CHAIN_FOCUS_RESULTS.md`](VORTEX_CHAIN_FOCUS_RESULTS.md) — Chaining vortex stages, entry focusing, and a possible circular path — 12 September 2026** A second aligned stage carries the tag…
- [`WEIGHT_RINGS96_ADDENDUM.md`](WEIGHT_RINGS96_ADDENDUM.md) — Addendum — degeneracy weight carried in Form D, and the ring lock at 96³ (theta_formD_weight.py, theta_rings.py; 17 Sep 2026)
- [`bouncing_focus.py`](bouncing_focus.py) — Dimensionless collisionless controls, NOT a liquid or phase-change solver.
- [`build_return_view.py`](build_return_view.py) — Insert recorded sample data in the literal inline visualization fragment.
- [`experiment.py`](experiment.py) — Periodic 2D incompressible Navier-Stokes; diagnostic, not a 3D blow-up test.
- [`find_vortex_sources.py`](find_vortex_sources.py) — Read-only, bounded search of the two named concept-paper families.
- [`finite_reservoirs.py`](finite_reservoirs.py) — Lumped liquid column joining two finite open reservoirs.
- [`four_vortices.py`](four_vortices.py) — Equal-energy four-tube comparison using the vortex3d solver.
- [`helical_annulus.py`](helical_annulus.py) — Equal-work 3D annular rise with central/outer returns and added axial swirl.
- [`magnetic_sheet.py`](magnetic_sheet.py) — Smooth strip-magnet field and a reduced closed-loop force/work audit.
- [`phase_budget.py`](phase_budget.py) — Smooth feedback pulses in the finite-reservoir oscillator; fixed positive work.
- [`pin_ring.py`](pin_ring.py) — Localized rotational body-force surrogates, NOT solid pin boundaries.
- [`planet_orbit_check.py`](planet_orbit_check.py) — Point-parcel central-gravity check, separate from the 3D fluid experiment.
- [`plot_helical_annulus.py`](plot_helical_annulus.py) — Plot actual computed paths and diagnostics; no invented helical trajectories.
- [`plot_sheath_chain.py`](plot_sheath_chain.py) — Standalone figures from completed simulations and the separate orbit check.
- [`plot_theta_field.py`](plot_theta_field.py) — Figure for THETA_FIELD_RESULTS.md from theta_field_32_0.01_results.json.
- [`plot_theta_kinetic.py`](plot_theta_kinetic.py) — Figure for THETA_KINETIC_RESULTS.md.
- [`plot_theta_three.py`](plot_theta_three.py)
- [`plot_vortex_chain_focus.py`](plot_vortex_chain_focus.py) — Actual gate diagnostics: transport and temporary radial-width changes.
- [`return_paths.py`](return_paths.py) — Track up-and-return trajectories in the existing powered periodic ring.
- [`review_theta_20260915.py`](review_theta_20260915.py) — Independent checks of the September 15 theta work; does not modify its code.
- [`ring_placement.py`](ring_placement.py) — Equal delivered kinetic work, different azimuthal drive placement schedules.
- [`ring_power.py`](ring_power.py) — Equal-power ring controls using energy-calibrated discrete increments.
- [`seam_trigger.py`](seam_trigger.py) — Finite-reservoir reaction/diffusion hypothesis test, not fluid dynamics.
- [`sheath_chain.py`](sheath_chain.py) — Equal-total-work test of an outer driven layer around two annular stages.
- [`stacked_layers.py`](stacked_layers.py) — One or two driven vortex-ring layers at fixed delivered power.
- [`summarize_helical_annulus.py`](summarize_helical_annulus.py) — Audit matched-work helical runs and verify the passive-turn tracker.
- [`summarize_phase_placement.py`](summarize_phase_placement.py) — Build the comparison block only after the complete accepted runs exist.
- [`summarize_sheath_chain.py`](summarize_sheath_chain.py) — Audit numerical budgets and comparable cohorts; no singularity extrapolation.
- [`summarize_temperature_aperture.py`](summarize_temperature_aperture.py) — Summarize completed runs and independent physical/numerical controls.
- [`summarize_vortex_chain_focus.py`](summarize_vortex_chain_focus.py) — Numerical checks and matched-label comparisons for the staged flow test.
- [`temperature_aperture.py`](temperature_aperture.py) — Dimensionless, prescribed-conduit thermomagnetic tests; not 3D Navier--Stokes.
- [`thermal_loop.py`](thermal_loop.py) — Advected viscous heat on the powered ring; one-way thermal coupling.
- [`theta_J_sweep.py`](theta_J_sweep.py) — (1) nu sweep: how does the plane exchange j = -u.grad Pi at the interface
- [`theta_bubble.py`](theta_bubble.py) — Two-sided interface: sink energy enters a reservoir E_b (the 'bubble') instead of
- [`theta_carried.py`](theta_carried.py) — The carried weight. Jonathan: the weight is distributed between the base plane,
- [`theta_chain.py`](theta_chain.py) — Chain of bubbles along a void line. Antiparallel tubes with a k-wavelength
- [`theta_faces.py`](theta_faces.py) — Two-face flux per bubble. For incompressible flow -u.grad Pi = -div(Pi u), so the
- [`theta_field.py`](theta_field.py) — Diagnostic evaluation of the RECOVERED theta on the thermal ring.
- [`theta_formD.py`](theta_formD.py) — Form D (proposed 15 Sep 2026): magnitude-plane nucleation, geometry-gated sink, floor -pi.
- [`theta_formD_weight.py`](theta_formD_weight.py) — Form D with the degeneracy weight carried per cell or per bubble.
- [`theta_frame_interface.py`](theta_frame_interface.py) — Interface criterion built only from the frame geometry measured under load:
- [`theta_gyro.py`](theta_gyro.py) — Gyroscopic gate on the two kinetic planes. Frame rotation rate g = tilt//S/_F
- [`theta_kinetic.py`](theta_kinetic.py) — Form B: a kinetic theta field coupled to 3D Navier-Stokes (proposed 2026-09-13).
- [`theta_lines.py`](theta_lines.py) — Three lines from the origin: the strain principal axes with eigenvalues l1>=l2>=l3 (sum 0).
- [`theta_plane_flux.py`](theta_plane_flux.py) — Local exchange between the normal (solenoidal) and orthogonal (gradient) planes
- [`theta_planes2.py`](theta_planes2.py) — Second orthogonal plane: the DIRECTION of vorticity (Constantin-Fefferman).
- [`theta_rings.py`](theta_rings.py) — Three rings, three radii, three rates.
- [`theta_third_ring.py`](theta_third_ring.py) — The third ring: rotation of the STRAIN eigenframe, driven by the pressure Hessian
- [`theta_three.py`](theta_three.py) — Form B with all three factors live: kinetic theta on the powered THERMAL ring.
- [`theta_tubes.py`](theta_tubes.py) — Antiparallel vortex tubes (Kerr-type perturbation), unforced, decaying,
- [`theta_tubes_place.py`](theta_tubes_place.py) — Placement of Gamma relative to gradient concentration, tube flow, 48^3, nu=.01.
- [`theta_void_check.py`](theta_void_check.py) — Does the theta=pi interface sit on the fluid's zero-divisor channels?
- [`threshold_transport.py`](threshold_transport.py) — Common diagnostic thresholds and passive material transport.
- [`vortex3d.py`](vortex3d.py) — Periodic 3D Navier-Stokes controls; dimensionless, no void/quantum law.
- [`vortex_chain_focus.py`](vortex_chain_focus.py) — Two-stage recapture test in the existing periodic 3D NS solver.
- [`write_sheath_report.py`](write_sheath_report.py) — Write the report only after every planned run and refinement is present.
