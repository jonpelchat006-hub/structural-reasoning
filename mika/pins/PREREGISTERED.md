# Bent pins — written BEFORE the insider data was fetched (Oct 16 2026, ~08:30 MDT)

Jonathan: each person is a pin; tunnels are bundles of aligned pins; a bad actor's pin doesn't align with the rest
and bends or breaks off to touch its own spot on the edge.

Data: SEC Form 3/4/5 quarterly data sets, open-market purchases (code P) and sales (code S) by officers,
directors and 10% owners of the ~520 companies in D:\planet\mika\cube and cube2 (their prices are cached).
Event = first trading day after the Form 4 FILING date (when the trade became public).

Pin classification (Cohen, Malloy & Pomorski 2012, decided at each trade from that insider's own history):
- usable insider-year: the insider traded this company's stock in each of the 3 previous calendar years
- ALIGNED (routine) trade: made in a calendar month in which the insider traded in each of those 3 years
- BENT (opportunistic) trade: any other trade by a usable insider
- insiders without 3 years of history are left out

Outcome: return over the next 21 and 126 trading sessions minus the average of all ~520 companies,
signed by the trade's direction (buy +1, sell -1). One observation per (company, insider, filing date, direction).
Statistics: mean per calendar year, then mean over years with t = mean / (sd / sqrt(years)).

Claims:
1. Bent buys come before a higher return vs the rest (21 and 126 sessions).
2. Bent sells come before a lower return vs the rest (direction-adjusted > 0).
3. Aligned trades carry no signal (direction-adjusted mean not different from 0).
4. Bent minus aligned (direction-adjusted, 126 sessions) > 0.
5. "Before trouble": the share of bent-sell events followed by a fall of 20% or more vs the rest within 126
   sessions is higher than for aligned sells.
Pass = right sign and t > 2. Known limits: today's large companies only (survivors); filing dates, not trade dates.

## Outcome (run Oct 16 ~09:10 MDT)
Data: 367,419 open-market lines (21,998 buys, 345,421 sells), 14,238 insiders, 516 companies, trades 2010-2026.
Classified events 2014-2026: bent 36,208 (35,241 sells, 967 buys), aligned 14,736; 98k had no 3-year history.
1. Bent buys: 21 sessions -0.43% (t -0.56); 126 sessions +0.53% (t 0.11). NOT passed.
2. Bent sells, direction-adjusted: 21 -0.15% (t -1.15); 126 -0.29% (t -0.48). NOT passed (wrong sign, small).
3. Aligned trades: no signal (buys +0.40%, sells -1.59%, both |t| < 1.5). Consistent with the claim (a null).
4. Bent minus aligned, 126: +0.45% (t 0.50, 7/14 years). NOT passed.
5. Falls of 20%+ within 126 sessions after sells: bent 13.9% vs aligned 13.8% (t 0.07). NOT passed.
Side fact: since 2023 (when Form 4 got the 10b5-1 checkbox) 53% of "bent" sells were pre-planned trading-plan sales
(aligned: 63%). The calendar-month rule calls planned selling programs "bent".
Spot-check: KLAC 2018-07-02 sale of 235 shares and LOW 2014-08-22 sale of 15,979 shares match the EDGAR XML
(a same-day code J line on the KLAC filing is correctly excluded).
