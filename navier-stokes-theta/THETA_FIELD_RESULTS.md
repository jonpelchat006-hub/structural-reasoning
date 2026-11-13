# The recovered theta, evaluated on the thermal ring — 13 September 2026

This is the first experiment in the folder that evaluates the user-confirmed
formula from ORIGINAL_THETA.md,

    theta = (1 + ln r_S)(1 + sqrt(ln r_T))(1 + sqrt(ln r_E)),

rather than the invented P/D diagnostic. It is a diagnostic only: theta is
computed from the existing one-way thermal ring (thermal_loop.py) and never
feeds back into the flow. Dynamics are bit-identical to thermal_loop.run
(heat_mean agrees to 2e-17). Reproduce:

    python navier_stokes_theta/theta_field.py --n 24
    python navier_stokes_theta/theta_field.py --n 32
    python navier_stokes_theta/theta_field.py --n 32 --dt 0.01
    python navier_stokes_theta/plot_theta_field.py

## The mapping, stated so it can be rejected

The source supplies no baselines for a fluid (unresolved item 3) and no rule
for ratios below 1 (item 2). These are the choices made here; none of them
comes from the source.

| Input | Definition used | Domain status in this flow |
|---|---|---|
| T0 | absolute baseline temperature = 1; T = T0 + excess | assumption: the formula needs an absolute scale |
| r_S(x,t) | ln(1+dT)/dT: entropy actually gained per unit heat, relative to depositing the same heat at T0 | in (0,1], -> 1 at the reference state, so ln r_S is finite and 1+ln r_S > 0 everywhere |
| r_T(x,t) | T_ref/T_act = T0/(T0+dT) | <= 1 wherever heated: the sqrt(ln r_T) factor is OUTSIDE the real domain everywhere in this flow |
| r_E(t) | P_demanded/D: controller requested power over instantaneous viscous dissipation rate (global) | > 1 throughout these runs (the fluid never absorbs the full demand by t=3) |

Two below-domain rules are evaluated side by side and never mixed:
"clamp" sets the factor to 1 (ln -> 0); "signed" uses 1 + sign(L) sqrt|L|.
Complex values and absolute values were not used. theta(x,t) is the product
of the two local factors and the global energy factor; thresholds 1,
sqrt(phi), phi, sqrt(pi), pi are the ones tested in FINDINGS.md.

## Results

Insulated case, 32 cubed, dt=.01, unless stated. All values dimensionless.

| Quantity at t=3 | 24^3 dt .02 | 32^3 dt .02 | 32^3 dt .01 |
|---|---:|---:|---:|
| r_E = P/D | 1.4655 | 1.4670 | 1.4660 |
| theta_E (both rules) | 1.6182 | 1.6190 | 1.6185 |
| domain minimum theta, signed | 0.1748 | 0.1425 | 0.1431 |
| domain minimum theta, clamp | 1.0288 | 0.9898 | 0.9903 |
| volume fraction with theta < 1, signed | 0.1101 | 0.1056 | 0.1058 |
| hottest cell excess | 0.9918 | 1.0809 | 1.0790 |

First time the domain minimum of theta falls below each constant, with the
hottest-cell excess at that instant in parentheses:

| Threshold | signed 24^3 | signed 32^3 | signed 32^3 dt .01 | clamp 24^3 | clamp 32^3 | clamp 32^3 dt .01 |
|---|---:|---:|---:|---:|---:|---:|
| pi | .04 (.000) | .04 (.000) | .03 (.000) | .04 (.000) | .04 (.000) | .03 (.000) |
| sqrt(pi) | .32 (.060) | .32 (.056) | .32 (.056) | .72 (.287) | .72 (.295) | .71 (.288) |
| phi | .36 (.079) | .38 (.090) | .36 (.078) | .94 (.375) | .92 (.384) | .92 (.381) |
| sqrt(phi) | .52 (.156) | .48 (.151) | .48 (.150) | 1.94 (.715) | 1.96 (.712) | 1.95 (.708) |
| 1 | .66 (.246) | .64 (.242) | .64 (.239) | none | 2.96 (1.071) | 2.95 (1.067) |

The global factor theta_E alone crosses pi at t=.03-.04 (during the power
ramp, when D is still ~1e-4) and sqrt(pi) at t=1.88-1.92; it does not reach
phi by t=3. The location of minimum theta coincides with the hottest cell at
every sampled time, as it must (see below).

![theta_E, domain minimum, and theta versus excess](D:/shovelcat-colony/navier_stokes_theta/theta_field.png)

## What this establishes

1. **Under one-way coupling, theta is a relabeling of the temperature field.**
   Both local factors are monotone decreasing functions of dT only, and the
   energy factor is spatially uniform. So at any instant theta(x) = F_t(dT(x))
   with F_t monotone, and "theta crosses c somewhere" is exactly "excess
   crosses dT*(c,t) somewhere". At t=3 (32^3, dt .01) those equivalents are:

   | Threshold | dT* signed | dT* clamp |
   |---|---:|---:|
   | 1 | 0.125 | 1.057 |
   | sqrt(phi) | 0.040 | 0.513 |
   | phi | ~0 (theta_E = 1.6185 is only 5e-4 above phi) | 0.0005 |
   | sqrt(pi) | not reachable, theta_E < sqrt(pi) | not reachable |

   THRESHOLD_TRANSPORT_RESULTS.md already showed that which region "ignites
   first" depends on the excess threshold chosen. The same holds for theta;
   nothing is added by the transformation until theta acts on the flow.
   The recovered formula therefore cannot be tested as a predictor in a
   one-way model; item 4 of ORIGINAL_THETA.md (a coupling law) is the real
   blocker, not items 2-3.

2. **The temperature factor is below its real domain everywhere the fluid is
   heated.** Any fluid that starts at its reference temperature and is
   heated by dissipation has T_act > T_ref. The formula as recovered (with
   T_ref/T_act inside the root) is therefore not real-valued for viscous
   heating without an extension rule, and the two natural rules give
   qualitatively different fields: under clamp, theta stays above 1 almost
   everywhere (0.99 at the single hottest cell at t=3); under the signed
   root, 10.6% of the volume is below 1. The choice of rule is not a detail.

3. **theta_E = phi at t=3 is a coincidence of the endpoint.** P/D = 1.466
   gives theta_E = 1.6185, within 3e-4 of phi, on all three grids. But
   theta_E is monotonically falling (2.81 at t=.1, 1.89 at t=1.1, 1.67 at
   t=2.6), and RING_LONG_RESULTS.md gives D=.035977 at t=8, i.e. theta_E =
   1.325 there. It passes through phi near t=3 because the run was stopped
   at t=3. A steady state would give P=D, r_E=1, theta_E=1 exactly.

4. **Grid and time-step sensitivity** of the crossing times is at most .04
   time units across the three runs, and of the hottest-cell excess ~9%
   (24 to 32 cubed), consistent with THERMAL_LOOP_RESULTS.md. Energy and
   thermal accounting errors are below 1e-10 and 1e-16.

## What would make it a test

The formula only has content once theta changes something. The historical
June proposal (BROWSER_RECOVERY.md) adds grad(theta) to the momentum
equation. In an incompressible periodic box a pure gradient is absorbed into
pressure, so that coupling is invisible here by construction. The candidates
that would not be absorbed are a theta-dependent viscosity nu(theta), or a
theta-dependent heat capacity / cooling rate. Either needs a functional form
chosen BEFORE running, plus a held-out case, as FINDINGS.md already required.
The signed-root field is the one with spatial structure worth coupling to;
the clamp field is nearly uniform.

Data: [24^3](theta_field_24_0.02_results.json), [32^3](theta_field_32_0.02_results.json),
[32^3 dt .01](theta_field_32_0.01_results.json). Code: [theta_field.py](theta_field.py),
[plot_theta_field.py](plot_theta_field.py).
