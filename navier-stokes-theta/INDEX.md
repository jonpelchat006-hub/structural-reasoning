# navier_stokes_theta — index and claim ledger

Status codes: **E** established within the model (grid/dt checked, energy audited);
**S** suggestive (one grid or one flow, or trend without convergence); **N** negative
(tested and rejected); **U** untested. "Model" always means the dimensionless periodic
Navier–Stokes solver in this folder, never a claim about the continuum equations.

## Part 1 — 9–13 Sep 2026 (Jonathan's runs)

| File | Question | Answer | Status |
|---|---|---|---|
| RESULTS.md / FINDINGS.md / experiment.py | Does theta_E = P/D (an invented ratio) predict the 10% off-shear marker in 2D shear flow? | No common threshold; crossings neither necessary nor sufficient. 2D cannot blow up by theorem. | N |
| ORIGINAL_THETA.md / BROWSER_RECOVERY.md | What is the original theta? | Recovered user-confirmed formula (Aug 2025) and Theory-1 weighted form; weights found later in Table 1 p.37. | E (recovery) |
| SEAM_TRIGGER_RESULTS.md | Does a lowered seam threshold release stored energy? | Yes in the specified scalar model; no fluid content. | E (model) |
| VORTEX3D / FOUR_VORTICES | Does pulse orientation amplify vorticity in helical tubes? | Aligned pulse raises peak vorticity ~2x; not equal-energy; no singularity. | E |
| PIN_RING / RING_POWER / RING_LONG | Ring of drives: circulation, power balance? | Toroidal cell; ~90% of input dissipated by t=8; no steady state; no self-sustaining energy. | E |
| THERMAL_LOOP / THRESHOLD_TRANSPORT | Where does dissipated heat go; do fixed thresholds pick a region? | Hot spot off-axis below the drive plane; region ranking depends on threshold. | E |
| STACKED_LAYERS / RETURN_PATHS | Do stacked rings change transport; does upward flow return? | Yes / yes (100% of first cohort return). | E |
| FINITE_RESERVOIRS / PHASE_PLACEMENT | Can a reversing column oscillate; does phase or placement matter? | Yes with periodic drive; +15 deg best at one start, not universal; golden-angle vs rational indistinguishable. | E |
| MAGNETIC / TEMPERATURE_APERTURE | Can a maintained susceptibility contrast or a thermomagnetic loop drive circulation? | Yes; heater placement relative to field gradient decisive; no singularity. | E |
| HELICAL_ANNULUS / VORTEX_CHAIN_FOCUS / SHEATH_CHAIN | Rising spiral band; chained stages; outer sheath? | Geometry exists; small entry narrowing then widening; counter-spin sheath narrows least; not converged. | S |
| PLANET (orbit check) | Can gravity bend the large loop? | Yes at circular speed; no speed increase. | E |
| REVIEW_2026-09-13.md | Outside review | Numerics good; regime laminar (Re ~30–100); theta not tested; diagnostics should be vorticity-based. | — |

## Part 2 — 13–16 Sep 2026 (theta programme)

| File | Question | Answer | Status |
|---|---|---|---|
| THETA_FIELD_RESULTS.md | Recovered theta as a diagnostic on the thermal ring (fixed baseline)? | Monotone relabeling of temperature; T factor outside real domain wherever heated; theta_E ~ phi at t=3 is an endpoint coincidence. | N (as predictor) |
| THETA_KINETIC_RESULTS.md | Form B: kinetic theta with r_E = production/destruction, coupled via nu_eff = nu e^{beta|theta-1|}? | Lower enstrophy with coupling on fitted and held-out cases; pi unreachable from one factor under Table-1 weights. Table 1 weights recovered. | E |
| THETA_THREE_RESULTS.md | Three factors on the thermal ring with mean references? | pi reached at t~.4 via the entropy factor; interface small, transient, on the hot spot, advected. | E |
| ... Add.1 | Wall at 3 + floor -pi? | Delays and thins, does not prevent; theta_eq = (theta_s+3k)/(1+k); k~11–12 flow-dependent. | E |
| ... Add.2 | Interface on zero-divisor channels (P = w.S.w ~ 0)? | No: 0% vs 18–43% of domain; anti-correlated. | N |
| ... Add.3 | Interface vs the orthogonal (pressure) plane? | Interface at top-1% of exchange j = -u.grad Pi, positive sign. | E |
| ... Add.4 | nu sweep and J as sink (forced ring)? | j on Gamma ~ grad^3.0 (forced only); sink share 0.3–5.5%, grows as nu falls; draining raises delivery. | S |
| THETA_TUBES_RESULTS.md | Unforced tubes, heat only from dissipation? | Interface forms on the gradient concentration (100% of Gamma in top-10% gradient). | E |
| ... E0 sweep | Does the published form strengthen with sharper gradients? | No: weakens (contrast collapse); local references kill it; cooling restores formation not trend. | N (falsifies "always wins") |
| ... second plane | Do the kinetic planes track sharpening? | r_E 16.5->24, r_R 3.4->5.3 as E0 quadruples; alignment ~0.6. | E |
| ... gyro gate | Do octants lock under load? | Yes: alignment .85–.93 at top-1% gradient vs .57 bulk; alignment-gated theta crosses pi only under strong load. | E |
| ... third ring | Pressure frame vs strain frame; vorticity ring? | Orthogonal at load (cos .02–.11 vs .56–.71); vorticity counter-rotates and cancels pressure-driven frame rotation; tan phi < 1 at load. | E |
| ... frame interface | Can geometry alone nucleate the interface? | No (Jaccard <= .2); r_E locates (.3–.5); alignment gating hurts. | N |
| THETA_FORMD_RESULTS.md | Form D: r_E nucleation, geometry-gated sink, floor, wall? | tau must beat load residence time (~h/U); with tau = .02 Gamma forms on the load; sink .9–1.6% of E0, peak vorticity -6.5%. Q–R: load vortical, never on Vieillefosse tail. | E |
| ... high-Re | 64^3/96^3, nu .02/.01/.007? | Sink effect on peak enstrophy -0.3/-4.8/-6.2%, growing with Re; Gamma dilutes (0.1->0.23% vol). Re ~100–300. | S |
| ... bubble | Two-sided interface (reservoir + backscatter)? | Returned energy comes back smoother: enstrophy suppression mostly lost at full return, vorticity cap -8% survives. | E |
| ... chain | Chain of bubbles along a line? | 3-site periodic chain at 2pi/3 spacing; finite chain has one-sided flanks; channels between bubbles during nucleation. | E |
| ... carried weight | Is the weight carried between base, walls and ring (w = .4 + .56 A)? | Per cell: too weak to nucleate (w <= .63 at load). Region-level A gives w(t) .40-.66 that meets the pi requirement only at high load, marginally. | S |
| ... three lines / degeneracy weight | Do the strain's principal lines merge under load; is the weight carried by that? | Yes: s* = +.65 to +.97 at the load (two extensional lines coincide) vs -.1 to +.3 bulk; vorticity anchored to the intermediate line 75–100%. w = .4 + .56\|s*\| is .8–.95 at load, .55–.7 bulk; best locator so far at equal volume. | E |
| theta_rings.py — three rings, radii and rates | Do the three rings (rotation about each principal line) have different radii and rates; base fastest; rational lock? | Yes: radii c/i/e ≈ .75/.1–.3/.5–.7, rates differ 3–10×; the ring about the intermediate (vorticity) line is fastest 60–100%; when λ₁≈λ₂ merge at load the ring about the compressive line spins up (.1→2.2). Rate ratios ≈ .4, lock fraction = random control in bulk AND at load once sampled at 96³ (.35–.48 vs .45–.46): generic/irrational, no periodic return. Compressive-ring spin-up at load confirmed at 96³. | E |
| theta_formD_weight.py — degeneracy weight carried in Form D | Does w = .4+.56|s*| (per cell or per Γ bubble) in θ_s sharpen the sink / Re trend? | No: w ≤ .96 shrinks Γ 4–8×, sink energy ÷3, peak-Ω reduction −0.28→0.00 % (ν=.02), −4.78→−1.2 % (ν=.01); cell = bubble. Confounded by Γ volume; matched-volume version open. Fixed .96 stays the default. | F (as run) / O (matched volume) |
| ... faces | Flux through each bubble's two faces? | Periodic chain: all two-sided (s .62–1.0). Finite chain: centre two-sided to 3 digits, flanks single-sided (s .00–.33), 14x asymmetry, mirror pairs. | E |

## Open items (as of 17 Sep 2026)
1. Magnitude-plane weight (Table 1: 0.4 under a root; used here: 0.96, no root). Theory decision.
2. Field response time tau: must scale with load residence time h/U, not be a constant.
3. kappa (sink strength) and beta_b (bubble return fraction).
4. A thin-interface rule at high Re (Gamma dilutes with the fixed 0.96 weight).
5. A bubble with structure (sub-grid energy equation; inner frame composed with outer).
6. Consistent discrete divergence for absolute face fluxes (ratios are fine).
7. One external test on standard initial data (Kerr tubes / Taylor–Green) at 128^3+, with numbers stated beforehand.
