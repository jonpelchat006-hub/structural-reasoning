# Re-test on fresh companies — written BEFORE the fresh data was fetched (Oct 14 2026, ~13:40 MDT)

Set 1 = the 148 companies from the trading test (D:\planet\mika\cube). Set 2 = the 374 current S&P 500 members
not in set 1 (D:\planet\mika\cube2). Same code, same settings, non-financials, 10-K events 2011-2026.

Claims to check on set 2:
1. (found after looking at set 1, so this is the real test) mismatch = |leak - year median| comes before a
   HIGHER 252-session return vs the rest: year-averaged rank corr > 0. Set 1: +0.096, t 2.75, 11/15 years.
2. (planned, failed on set 1) leak -> blur change over 63 sessions > 0. Set 1: -0.015, t -0.5.
3. (planned, failed on set 1) leak -> 252-session return < 0 (Sloan 1996). Set 1: +0.002, t 0.1.
4. (planned, failed on set 1) blur -> 252-session return < 0 (Ang et al. 2006). Set 1: +0.042, t 0.9.
5. blur persistence (blur now -> blur next 63) > 0. Set 1: +0.676, t 19.

Pass = same sign and t above 2 on set 2. Known bias in both sets: they are today's large companies (survivors).

## Outcome (run 14:05 MDT, 3,915 events from 371 companies)
1. mismatch -> return 252: +0.049, t 1.88, 9/15 years. NOT passed (same sign, half the size, under t 2).
2. leak -> blur change 63: +0.036, t 1.45. NOT passed.
3. leak -> return 252: -0.044, t -1.61. NOT passed (Sloan's sign this time).
4. blur -> return 252: +0.036, t 0.82. NOT passed.
5. blur persistence: +0.639, t 13.0, 15/16. PASSED.
Not pre-registered, seen in both sets: leak quintile 1 (cash far ahead of earnings, 32% losses) did better (+4.5% / +10.0%).
Survivorship (today's large companies only) is the obvious alternative explanation for that one.
