# The invisible vortex — written BEFORE the tax data was fetched (Oct 16 2026, ~11:00 MDT)

Jonathan: a bad actor builds their own vortex that doesn't touch the walls (the hidden Hoover Dam). It shows by
its missing water and by breaking all at once. Company-level shadow: money that avoids the authority face.
Prior evidence: Kim, Li & Zhang (2011), corporate tax avoidance -> higher stock-price crash risk.

Companies: the ~520 of D:\planet\mika\cube and cube2, leaving out financials (SIC 6000-6999) and utilities
(SIC 4900-4999), as Kim-Li-Zhang did. Event = first trading day after each original 10-K is filed.

Avoidance (known at the event): long-run cash tax rate = cash taxes paid / pre-tax income summed over the
3 fiscal years ending with that 10-K (pre-tax sum > 0; capped to [0, 1]), minus that year's median among firms
in the same 2-digit SIC (year median if fewer than 5). AVOID = minus that number (higher = less tax paid).

Crash measures over the 52 weeks after the event, from weekly firm-specific returns
(simple weekly return regressed on SPY's weekly return at lags -1, 0, +1; W = ln(1 + residual)):
- NCSKEW: negative skewness of W
- DUVOL: log of down-week variance over up-week variance
- CRASH: 1 if any week has W below mean(W) - 3.09 sd(W)
Same three measured over the 52 weeks BEFORE the event serve as controls.

Claims (statistics: rank correlation or rank-regression slope per filing year, averaged over years,
t = mean / (sd / sqrt(years))):
1. AVOID -> higher NCSKEW next year (rank corr > 0).
2. AVOID -> higher DUVOL next year (rank corr > 0).
3. AVOID -> higher CRASH frequency: top avoidance quintile crashes more often than the bottom one.
4. With prior-year NCSKEW and size (log assets) as controls, the AVOID slope on next NCSKEW stays > 0.
Pass = right sign and t > 2. Known limits: today's large companies only (survivors); cash taxes paid are
reported by fiscal year and include taxes on earlier years' income.

## Outcome (run Oct 16 ~11:35 MDT; 3,759 events from 356 companies, filed 2011-2025; crash rate 27.2%)
1. AVOID -> NCSKEW next year: rank corr +0.039, t 2.18, 10/15 years. PASSED (just).
2. AVOID -> DUVOL next year: rank corr +0.043, t 2.50, 12/15 years. PASSED.
3. Crash frequency, top vs bottom avoidance quintile: 27.0% vs 24.3% (+3.0 points, t 1.69). NOT passed (right sign).
   By quintile 1..5: 24.3%, 27.7%, 26.8%, 30.1%, 27.0% (not a clean staircase).
4. With prior-year NCSKEW and size as controls: AVOID slope +0.038, t 2.20. PASSED.
Side: the book (GAAP) tax rate shows nothing (-0.007, t -0.3); crash skew itself does not persist year to year.
Spot-checks: Apple FY2021-23 cash tax rate 0.1860 by hand from its 10-Ks = file; NCSKEW = minus scipy's
bias-corrected skewness of the same residuals (-0.7567 both).
NOT pre-registered robustness: same sign in 2011-2017 (t 1.2 / DUVOL 2.0) and 2018-2025 (t 1.8 / 1.7);
stronger without near-zero-tax reports (t 2.3 / 2.7); with blur, leak, profitability, past skew and size
as controls the AVOID slope is +0.035, t 2.06.
