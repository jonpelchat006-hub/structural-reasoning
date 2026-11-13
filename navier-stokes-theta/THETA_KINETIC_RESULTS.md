# Form B: a kinetic theta coupled to Navier–Stokes — 13 September 2026

A second form of theta, built from how the first paper actually uses the
field rather than from the static three-factor formula alone. It is proposed
here, specified before running, and tested on the existing two-tube pulse
flow with one held-out case. Reproduce:

    python navier_stokes_theta/theta_kinetic.py --n 24
    python navier_stokes_theta/theta_kinetic.py --n 32 --kinds aligned --betas 0 0.5 1
    python navier_stokes_theta/theta_kinetic.py --n 32 --kinds transverse --betas 0 0.5 1
    python navier_stokes_theta/theta_kinetic.py --n 32 --dt 0.005 --kinds aligned --betas 0.5
    python navier_stokes_theta/plot_theta_kinetic.py

## What the first paper says theta is

Shovelcat_Theory_1.pdf (Oct 2025):

- theta is a dimensionless *load* field with its own Euler–Lagrange equation
  of reaction–diffusion type, K[theta] - V'(theta) = Q + delta_Gamma J
  (Sec. 3.3, Eq. 2). Balanced systems sit at theta ~ 1.
- At theta = pi an interface Gamma nucleates (Thm. 2, Prop. 1) with
  theta|Gamma = pi. In the load-balanced limit it "acts as a perfect
  information sink": it *extracts* perturbation energy and *damps* chaos.
- Near equilibrium, g_eff = g_N exp(-|theta-1|): efficiency peaks at 1 and
  any departure is penalised symmetrically.
- **Table 1 (p. 37) locks the weights and powers**: (w_S,w_T,w_E) =
  (0.8, 0.6, 0.4), (p_S,p_T,p_E) = (1.2, 1.0, 0.8). ORIGINAL_THETA.md
  records these as not provided; they are. Unresolved item 1 is closed.

So in the paper's own mechanism theta is a *damping* device. A faithful fluid
version should be dynamical, sourced by the flow, and coupled back as extra
dissipation — not a static relabeling (THETA_FIELD_RESULTS.md) and not a
blow-up amplifier.

## The proposed form

Isothermal liquid, so r_S = r_T = 1 exactly and only the energy factor is
live. Every choice below is explicit and none comes from the source.

| Piece | Definition |
|---|---|
| load ratio | r_E(x,t) = (P_w^+ + d<D_w>) / (D_w + d<D_w>), with P_w = w_i S_ij w_j the enstrophy production (positive part), D_w = nu \|grad w\|^2 the viscous enstrophy destruction, d = 0.01 so r_E -> 1 in quiescent fluid |
| static factor | theta_s = 1 + w_E sign(L) sqrt(\|p_E L\|), L = ln r_E, Table-1 weights, signed-root rule |
| field equation | theta_t + u.grad theta = D lap theta + (theta_s - theta)/tau, D = nu = 0.03, tau = 0.1 (fast relaxation, the paper's timescale-separation assumption A2) |
| interface | theta <= pi, enforced as a cap (Dirichlet value, the sink) |
| coupling | nu_eff = nu exp(beta \|theta-1\|), momentum gains div[2(nu_eff - nu)S]; the extra dissipation is booked in the energy budget. beta = 0 is the passive control |

The load ratio is the local form of the quantity that decides regularity:
enstrophy grows where stretching beats viscous destruction. That is the
natural "demanded / available" pair for an isothermal fluid, and it does
not degenerate at the rest state. A grad(theta) momentum term is omitted:
in a periodic incompressible box it is absorbed by pressure.

Pre-registered prediction: with beta > 0 the peak enstrophy and peak
vorticity are lower than the control, the effect grows with beta, and it
holds on the held-out transverse pulse. A fluid that produced *higher*
enstrophy under coupling would falsify this form.

## Results

Two helical tubes, viscosity 0.03, 0.3-time-unit pulse, run to t = 2.
Controls reproduce VORTEX3D_RESULTS.md peak vorticities exactly (9.7766 at
24^3, 9.9761 at 32^3, 5.4217 transverse).

| Case, 32^3 | beta | Peak vorticity | Peak enstrophy | Enstrophy at t=1 | Final energy | Max theta |
|---|---:|---:|---:|---:|---:|---:|
| Aligned | 0 | 9.9761 | 0.44692 | 0.41000 | 0.07270 | 1.687 |
| Aligned | 0.5 | 9.6980 | 0.43508 | 0.36842 | 0.06723 | 1.663 |
| Aligned | 1 | 9.3201 | 0.42052 | 0.32384 | 0.06078 | 1.652 |
| Transverse (held out) | 0 | 5.4217 | 0.37515* | 0.32036 | 0.06449 | 1.615 |
| Transverse (held out) | 0.5 | 5.3580 | 0.37515* | 0.28950 | 0.05946 | 1.607 |
| Transverse (held out) | 1 | 5.3011 | 0.37515* | 0.25572 | 0.05351 | 1.596 |

*The transverse peak enstrophy is the initial value; the pulse never raises
it above t = 0, so the post-pulse column is the informative one there.

The prediction holds in direction and ordering on both the fitted and the
held-out case: aligned peak enstrophy falls 2.6% and 5.9%, enstrophy at
t = 1 falls 10% and 21%; transverse enstrophy at t = 1 falls 10% and 20%.
The coupled model dissipates more, as booked.

The feedback is self-limiting: in the control, 19% of the volume has
theta > 1 at the end of the pulse; with beta = 0.5 it is 2%, because the
extra viscosity removes the production that raised theta. This is the
paper's "sink" behaviour, in a weak form.

**The interface never forms.** Max theta stays between 1.6 and 1.8 on all
runs; the volume above phi is at most 0.1%; the cap at pi is never touched.
This is structural, not a matter of Reynolds number: with Table-1 weights,
one factor reaches pi only if r_E = exp((pi-1)^2/(w_E^2 p_E)) = e^36. The
runs see r_E up to about 150 (theta ~ 1.8). Reaching pi requires all three
factors to contribute (each ~ pi^(1/3) = 1.46, i.e. r ~ 5 each) — so **an
isothermal fluid cannot nucleate the paper's interface**. The thermal and
entropic factors are not optional; a coupled thermal model is the only route
to theta = pi under the published weights.

![Enstrophy, theta statistics, and the static factor](D:/shovelcat-colony/navier_stokes_theta/theta_kinetic.png)

## Checks

- Kinetic-energy budget, including the theta-dependent dissipation, closes
  to 3e-10 or better in every run. CFL below 0.5. Controls match the earlier
  solver bit-for-bit at the printed precision.
- 24^3 to 32^3: peak vorticities change 2–3%, coupled enstrophy at t = 1
  changes below 0.2%, max theta changes 4–7% (24^3 is higher). The volume
  fraction with theta > 1 in the *control* is grid-sensitive (7.5% vs 19% at
  t = 0.3): the passive field has sharper structure than the coupled one. The
  coupled fractions agree to 0.2 points.
- Halving dt at 32^3 (aligned, beta 0.5) leaves peak vorticity, enstrophy and
  final energy unchanged to 5 significant figures.
- tau, D, d and beta are chosen, not derived. beta sets the strength of the
  g_eff analogue; the paper gives no fluid value.

## What this means for the folder's question

Translated faithfully, the paper's theta is an eddy-viscosity-like
regularizer keyed to local enstrophy-production excess, with a hard sink at
pi. Its own logic argues *against* Navier–Stokes blow-up: load concentration
raises theta, theta raises dissipation, and the interface caps the load. If
Shovelcat Theory has a statement to make about the Millennium problem, this
form says it is a regularity mechanism, not a singularity one — the same
role the IBH interface plays for the Moon in the paper.

Two follow-ons are well defined. (1) Couple this form to the thermal ring
(thermal_loop.py) so r_S and r_T become live, and see whether the three
factors together ever reach pi. (2) Push r_E: the colliding-ring initial
data of Lu–Doering / Ayala–Protas maximise enstrophy production and would
give the largest achievable single-factor theta; the sweep in nu would show
how theta_max scales with Reynolds number.

Data: [24^3](theta_kinetic_24_0.01_all_results.json),
[32^3 aligned](theta_kinetic_32_0.01_aligned_0.0_0.5_1.0_results.json),
[32^3 transverse](theta_kinetic_32_0.01_transverse_0.0_0.5_1.0_results.json),
[32^3 dt .005](theta_kinetic_32_0.005_aligned_0.5_results.json).
Code: [theta_kinetic.py](theta_kinetic.py), [plot_theta_kinetic.py](plot_theta_kinetic.py).
