## Addendum — degeneracy weight carried in Form D, and the ring lock at 96³ (theta_formD_weight.py, theta_rings.py; 17 Sep 2026)

### A. Degeneracy weight as the θ-source weight (theta_formD_weight.py)
θ_s = 1 + w(x) ln r_E with w = 0.4 + 0.56|s*| carried (a) per cell, (b) per Γ bubble (bubble = connected component of
the previous step's Γ dilated one cell; each bubble takes its mean cell weight; cell weight elsewhere). Same protocol as
the Re-trend runs: 64³, E₀=.6, κ=1, τ=.02, wall 3, T=1.6. Baselines: κ=0 peak Ω 3.9447 (ν=.02), 6.1153 (ν=.01);
fixed w=.96 with κ=1: −0.28 % / −4.78 %, sink 0.75 % / 2.31 % of E₀, Γ 200–500 cells.

| ν | weight | peak Ω | vs κ=0 | sink /E₀ | Γ cells (t=.2…1.6) | w on Γ / bulk | Γ∩top-1 % |
|---|---|---|---|---|---|---|---|
| .02 | fixed .96 | 3.9336 | −0.28 % | 0.75 % | 224 → 258 | .96 / .96 | — |
| .02 | cell | 3.9447 | 0.00 % | 0.08 % | 38, 6, 12, 8, … 64 | .78–.93 / .56–.70 | 0–.67 |
| .02 | bubble | 3.9446 | 0.00 % | 0.08 % | ~same, 4–18 bubbles | .78–.84 / .56–.70 | 0–.50 |
| .01 | fixed .96 | 5.8230 | −4.78 % | 2.31 % | 490 → 210 | .96 / .96 | — |
| .01 | cell | 6.0374 | −1.27 % | 0.66 % | 60–92 | .82–.85 / .64–.69 | 0–.70 |
| .01 | bubble | 6.0471 | −1.12 % | 0.69 % | 80, 34 bubbles | .78 / .69 | 0 |

Energy closure ≤ 2e-8 in all runs.

Finding: **carried into the source, the measured weight weakens the sink, it does not sharpen it.** Since w ≤ .96
everywhere, θ_s is lower everywhere and Γ shrinks 4–8× (6–92 cells vs 200–500), so the sink energy drops ~3× and the
peak-enstrophy reduction goes −0.28 → 0.00 % (ν=.02) and −4.78 → −1.2 % (ν=.01). Per-bubble vs per-cell makes no
difference (6.047 vs 6.037). The weight's demonstrated value (LINES) was as a *locator at fixed volume*; as an amplitude
in θ_s it is a volume knob, and the comparison above is confounded by Γ volume. A matched-volume test (lower the wall or
renormalise w so Γ has the fixed-weight volume) is the open item; until then the fixed .96 remains the Form D default.
Ledger: "degeneracy weight sharpens the sink" — **falsified as run**; matched-volume version — open.

### B. Ring lock at 96³ (theta_rings.py --n 96, E₀=.6, dt=.005, top 1 % of live cells ≈ 9 000 cells)

| t | region | rate about c / i / e | fastest c / i / e | radii c / i / e | 2nd/fastest | lock (ctrl) |
|---|---|---|---|---|---|---|
| 0.4 | load | .30 / .71 / .16 | .15 / .84 / .01 | .81 / .30 / .51 | .39 | .45 (.46) |
| 0.8 | load | .15 / 1.31 / .10 | .16 / .84 / 0 | .79 / .22 / .57 | .22 | .35 (.46) |
| 1.2 | load | 2.59 / 2.59 / .74 | .51 / .44 / .05 | .80 / .24 / .56 | .41 | .44 (.46) |
| 1.6 | load | 2.45 / 3.07 / .91 | .42 / .46 / .12 | .77 / .16 / .61 | .39 | .48 (.45) |
| 2.0 | load | 1.99 / 3.42 / .90 | .34 / .54 / .11 | .75 / .15 / .65 | .43 | .42 (.46) |
| 0.4–2.0 | bulk | .14–.64 / .60–.92 / .18–.45 | i fastest .46–.76 | .69–.76 / .09–.16 / .65–.72 | .26–.43 | .41–.45 (.45) |

Findings: (1) **No rational lock at the load.** With 8× the sample of the 48³ run the load lock fraction is .35–.48
against a control of .45–.46 — the 48³ values of .61 and .51 were noise. Ring-rate ratios are generic (irrational);
the frame never returns periodically to the straight set-up, at the load or in the bulk. Closed. (2) The rest of the
48³ picture holds at 96³: intermediate (vorticity) ring fastest in the bulk (.46–.76) and early at the load (.84);
compressive ring spins up as the lines merge (rate .15 → 2.6 → 2.0, fastest share .15 → .51), radii c/i/e ≈ .8/.2/.6;
ratio of second-fastest to fastest ≈ .4. E₀=.15 at 96³ not run (the lock question is answered by the E₀=.6 sample).

Files: theta_formD_weight.py, theta_formD_weight_{cell,bubble}_n64_nu{0.02,0.01}_k1.0_results.json and logs;
theta_rings.py (now with checkpoint/resume), theta_rings_E0.6_n96_results.json, theta_rings_E0.6_n96.log.
