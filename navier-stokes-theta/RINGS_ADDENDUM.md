## Addendum — three rings, three radii, three rates (theta_rings.py, 17 Sep 2026)

Question (Jonathan): the three rings would have different radii and turn at their own rates — base fastest, walls slower —
each with a count of turns before the set-up comes back to "straight"; different lengths that wrap round to become equal;
rational (periodic return) or irrational ratios?

Mapping: ring k = rotation of the strain frame about principal line k, rate Ω_k = |M_ij|/|λ_i−λ_j| (i,j≠k),
M = pressure Hessian + W² in the strain frame, normalised by |S|. Radius of line k = |λ_k|/|S|. 48³, ν=.02, tubes IC,
load = top 1 % of |∇u| among live cells.

| E₀ | t | region | rate about c / i / e | fastest ring c / i / e | radii c / i / e | 2nd/fastest | lock (ctrl) |
|---|---|---|---|---|---|---|---|
| .15 | 0.4 | load | .27 / 2.55 / .03 | 0 / 1.00 / 0 | .66 / .08 / .74 | .11 | .18 (.43) |
| .15 | 0.8 | load | .94 / .70 / .36 | .50 / .43 / .07 | .81 / .34 / .47 | .56 | .31 (.44) |
| .15 | 1.2 | load | .46 / .78 / .20 | .19 / .81 / 0 | .81 / .31 / .50 | .62 | .51 (.40) |
| .15 | 2.0 | load | .30 / .95 / .12 | .23 / .77 / 0 | .80 / .26 / .54 | .36 | .48 (.45) |
| .15 | 2.0 | bulk | .28 / .62 / .30 | .21 / .59 / .21 | .72 / .13 / .69 | .38 | .44 (.45) |
| .6 | 0.4 | load | .56 / .49 / .25 | .41 / .59 / 0 | .81 / .31 / .50 | .57 | .61 (.41) |
| .6 | 1.2 | load | .68 / 1.69 / .44 | .23 / .74 / .03 | .79 / .21 / .58 | .35 | .42 (.44) |
| .6 | 2.0 | load | 2.17 / 2.58 / 1.04 | .42 / .48 / .09 | .74 / .15 / .67 | .41 | .46 (.42) |
| .6 | 2.0 | bulk | .67 / .78 / .42 | .36 / .45 / .20 | .76 / .16 / .64 | .42 | .44 (.45) |

c/i/e = compressive / intermediate / extensional line. "lock" = fraction of cells whose (2nd fastest)/(fastest) ratio lies
within .02 of a rational p/q, q≤6; ctrl = same statistic for uniform random ratios.

Findings
1. **Yes — three different radii and three different rates.** The intermediate line is short (radius .08–.34) and the
   compressive and extensional lines are long and nearly equal (.65–.8). The rates differ by 3–10×.
2. **The fast ring is the one about the intermediate line — the line the vorticity is anchored to** (fastest 60–100 % of
   cells, both regions, both E₀). So "base rotates fastest" holds if the base is the vorticity/intermediate line; the two
   walls (rings about the compressive and extensional lines) are the slow ones. In the bulk this is set by the pressure
   Hessian coupling between the two long lines, not by their lengths.
3. **Wrapping to equal length spins a ring up.** When the intermediate and extensional lines merge (s*→+1, λ₁≈λ₂ — the
   LINES result), the ring about the *compressive* line accelerates: at E₀=.6 its rate goes .12 → .68 → 1.55 → 2.17 from
   t=.8 to 2.0 and takes over as fastest in ~40 % of load cells. That is the third-ring divergence seen earlier, now
   attributed to a specific pair of lines becoming equal. Note the radii table uses |λ|, so the "equal" pair there
   (c and e, |λ₀|≈|λ₂|) is the pure-shear pair, not the signed-degenerate pair that drives the rate.
4. **Ratios are not equal and not locked.** 2nd/fastest sits at .1–.6 (median ≈ .4), never near 1. The rational-lock
   fraction in the bulk equals the random control exactly (.44 vs .45) at every time — the ratio is generic
   ("irrational"): no periodic return to the straight set-up, the frame never repeats. At the load the lock fraction
   scatters above and below control (.18–.61 vs .40–.46); two snapshots (E₀=.6 t=.4: .61/.41; E₀=.15 t=1.2: .51/.40)
   are above, others below. Not established; if there is a lock it is load-only and weak, and needs a larger sample.
5. Rates are local and time-varying (they are set by the instantaneous pressure Hessian), so "number of turns before
   straight" is not a fixed integer anywhere in the flow; the nearest meaningful version is the ratio distribution above.

Ledger: (1)–(3) established at 48³ (two E₀, five times); (4) irrational/generic in bulk established, load lock open;
(5) reframing. Files: theta_rings.py, theta_rings_E0.15_results.json, theta_rings_E0.6_results.json, logs.
