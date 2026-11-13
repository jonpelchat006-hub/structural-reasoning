# The market cube — companies as a fold in the money solvent (Oct 14 2026)

*Jonathan's design, talked through on Oct 14 after the old trading signals failed their backtest (`claude/MIKA_JOBS.md`). It replaces the old per-company "matter / antimatter / void" verdict with a place in the alignment framework.*

## Where it sits in the framework

The alignment grid's **humans row, Water column** reads "money as the carrier" (`ARC_ALIGNMENT` §7). The market cube is that one cell opened up, with **money as its solvent**.

**The faces** (Jonathan):
- **Bottom: people** (customers, workers).
- **Top: banks and authority.**
- **Left and right: other companies and businesses.**
- **Front and back: popularity** (social media, content creators, the news, and the old trading reads). This is the Air axis: signal and trust, the fast layer that moves before Water (`Shovelcat_29` §4.1).

**The pieces:**
- **Companies** are boxes with their own size and dimensions, placed according to what is on each side of them. A grocer lies against the people face, and a lender against the top. A supplier that sells only to other companies is buried in the middle.
- **Tunnels** are money paths between faces. A tunnel that runs from people up through companies to the banks, and back down as wages and loans, is a **closed cycle**: `ARC_ALIGNMENT` rule 1, applied to companies. A company on closed tunnels is healthy even with a lot of debt. That is the check the old "debt = collapse" verdict should have been.
- **The fold** (from the protein work): market actions are the DNA, and the cube is the fold they make. Unlike a protein, the chain never finishes being written, so the fold keeps re-forming (like co-translational folding). What the protein work predicts here:
  - **The easy half** is rebuilding the shape from the contact web (0.0 Å from the full web). For companies, that means drawing the cube from known money flows.
  - **The wall** is predicting the web from the sequence alone. For companies, that is predicting how tunnels shift from new market actions.
- **Our view is from the front** (Jonathan): we see companies through what people say about them.
  - Movement along that line of sight can't show up as sideways motion, only as **blur**, which is uncertainty. Compare the void-line paper: observers' disagreement encodes depth.
  - **Tunnels leak**, and the leaks push their tunnels back into more blur.
- **Popularity tunnels.** A front-to-back popularity tunnel with no bottom-face money tunnel behind it is the three-body paper's **artificial rain**: it looks like growth, and it is temporary. Outside evidence fits:
  - Barber & Odean 2008: stocks that grab attention are bought and then underperform.
  - Da, Engelberg & Gao 2011: a search-volume spike is followed by a 2-week rise, then a reversal.

**What the market already measures:**
- **Blur** is idiosyncratic volatility; options put a forward number on it (implied volatility).
- **Earnings reports are when the blur collapses** ("volatility crush").
- **A leak** is the gap between reported earnings and the cash that arrived (accruals, Sloan 1996), or sales booked but not collected (receivables growth).

**The old agent's front face was blind.** Its news emotion read "flow" on 4,384 of 4,398 ticker-days, and its news count was 4–6 every time. Its calls came almost entirely from the debt reading. Script: `D:\planet\mika\trading_frontface.py`.

## Faces made of pins, cycles closing wall to wall, and cubes inside cubes (Jonathan, Oct 14 evening)

**Complete cycles.** Every line has to end on a wall at both ends, so every face shows the endings of all the lines that touch it. As in the alignment grid, each person or company is a line, and the faces are made of those pins, oriented differently on each side:
- **People (bottom):** small, equal pins standing up, one per person, like the grid's non-human rows.
- **Authority (top):** lines lying flat across the face. Rules, rates and regulations span the face, and lines from below land on them (loans, taxes). These are the grid's horizontal bars, which are rules and qualifications.
- **Business (sides):** company line-ends, thicker for bigger companies.
- **Popularity (front and back):** creators' line-ends, sized by audience.

**Leak, made precise.** A leak is **a line with only one ending**. The leak test above read one company's own books, so it saw only one end of each line. That is probably why it missed.

**Coarse data that already works this way.** The Federal Reserve's Financial Accounts of the US (Z.1, "flow of funds") divides the economy into households, businesses, financial firms, government and the rest of the world. Every asset of one sector is another sector's liability, and mismatches are reported as **statistical discrepancies**: measured missing endings, quarterly, for decades. The GDP-versus-GDI gap is the economy-wide version, and the income side caught the 2007 recession earlier (Nalewaik 2010).

**Recursion.** The main cube splits into **sector cubes**, each with the same six faces. Sector cubes split into company cubes, and company cubes into divisions. The same rule holds at every scale. This is the window's "the bottom edge is recursive" (`ARC_ALIGNMENT` §7).
- What looks from outside like the "other businesses" side faces is, from inside, the shared wall between two sector cubes. The BEA industry-to-industry tables are the money crossing those inner walls.
- **Leaks must be checked at every level.** Two companies' mismatches can cancel in their sector total, so a leak may only show when you zoom in. This is the grid result again: harm lives in which things are judged together.

**Other countries are neighbouring cubes**, beside ours the way Mars or Venus sit beside Earth at the planet level (§7: sideways = same tier, different instance).
- The rest-of-world sector is **not a face of our cube**. It is the walls we share with the neighbour cubes.
- A line crossing a shared wall (exports, imports, foreign investment) must find its ending inside the neighbour.
- A cube we can't see into is the window edge, and its flows are treated as rain. When an action can change that flow, the window must grow to include the neighbour.
- National accounts follow one international standard (the UN System of National Accounts), so the cubes line up face to face.
- The world's missing endings are measurable too. Countries' current-account balances should sum to zero and don't (the global current-account discrepancy).
- **Canada** is a natural first neighbour. The US is its biggest trading partner, and Statistics Canada publishes the same kind of sector accounts.

## Tunnels are made of people-pins (Jonathan, Oct 16)

**Resistance and middlemen.** A company wants direct access to its customers. Points between a company and the people face either provide a service that connects them or are a drain (a middleman).
- **Measurable:** the BEA input–output accounts value each product at both **producers' and purchasers' prices**. The difference is the wholesale, retail and transport margin, which is the toll on that tunnel, product by product.
- **Service vs drain** is the closed-cycle test. A middleman that lowers the tunnel's total resistance (storage, transport, trust, matching) is part of the cycle. One that only holds the passage and keeps what flows through it is the Hoover-Dam pathology.
- **"Going direct" often moves the toll to another face rather than removing it.** Selling direct means paying for attention (ads, platforms), so the middleman moves from a side face to the front face.

**Pins all the way down.** Every company comes down to individual people, so every connection is made of person-pins, and a tunnel is a bundle of aligned pins.
- **AI pins** form a layer around a human pin (the grid: each AI stems from one person). Even automation has a person who signed off on it, and that person is the **spine** of the connection. The real-world version: Sarbanes-Oxley §302 makes the CEO and CFO personally certify each financial report.
- **A bad actor is a pin that doesn't align with the bundle.** It bends or breaks off to touch its own spot on the edge. That is the twin of the leak: a leak is a **missing** ending, and a bent pin makes an **extra** ending where the tunnel shouldn't have one. A bent pin is a flag, not a verdict (untrusted until played).

**Public data for the pins:**
- **Form 4:** every officer's and director's trades in their own company, filed within two business days.
- **Related-person transactions:** S-K Item 404 requires disclosing those above $120,000.
- **Prior evidence:** Cohen, Malloy & Pomorski (2012) separated insiders' *routine* trades (same pattern every year: aligned pins) from *opportunistic* ones (off-pattern: bent pins). Only the opportunistic trades predicted returns, and they were the ones linked to SEC enforcement.

### Test: do bent pins come before trouble? (Oct 16; pre-registered in `D:\planet\mika\pins\PREREGISTERED.md`)

**Data.**
- The SEC's quarterly Form 3/4/5 data sets, open-market buys (P) and sells (S) only.
- The 516 companies of sets 1 and 2: 367,419 transaction lines from 14,238 insiders, 2010–2026. Only 6% of the lines are buys.
- **Pins:** each insider at each company.
- **Aligned** = a trade in a calendar month in which that insider traded in each of the three previous years (routine, per Cohen–Malloy–Pomorski). **Bent** = any other trade by an insider with three years of history.
- The event is the first trading day after the Form 4 filing date. The outcome is the return over the next 21 or 126 sessions minus the average of all 516, signed by the trade's direction. t is computed across years.
- Code: `pins_fetch.py`, `pins_test.py`, `pins_spotcheck.py`.

| Claim | Result | Passed? |
|---|---|---|
| Bent buys → higher return | 21 sessions −0.43% (t −0.6); 126 +0.53% (t 0.1), n ≈ 950 | no |
| Bent sells → lower return | 21 −0.15% (t −1.2); 126 −0.29% (t −0.5), wrong sign, n ≈ 35,000 | no |
| Aligned trades → nothing | buys +0.40%, sells −1.59%, both \|t\| < 1.5 | consistent (a null) |
| Bent − aligned, 126 | +0.45% (t 0.5, 7/14 years) | no |
| Falls of 20%+ after sells | bent 13.9% vs aligned 13.8% | no |

**Spot-check.** A KLAC sale (2018) and a LOW sale (2014) match the Form 4 XML on EDGAR line for line.

**Reading.**
- In today's large companies, insiders' trades in their own stock show no bent-pin signal that prices hadn't already absorbed.
- **The "bent" label is also too blunt.** Since 2023, Form 4 has a checkbox for pre-planned (10b5-1) trading-plan sales, and 53% of the "bent" sells since then carry it. Many off-calendar sells are scheduled programs, and many are tiny: one of the spot-checked "bent" sells was 235 shares.
- Cohen–Malloy–Pomorski's effect was strongest in smaller, less-followed companies, and their sample ended in 2007.
- **Better next design: start from known bent pins.**
  - SEC enforcement cases (litigation releases) are ground truth for actual bad actors. Learn what their pins looked like *before* the case, then look for that shape elsewhere.
  - Insider trading is the pin touching the trading face, which is legal and mostly routine. Jonathan's "touching its own spot on the edge" is more directly the related-person transactions in proxy statements (S-K Item 404). Those are text, not structured data, so they need parsing.

### The shape of a bad loop (Jonathan, Oct 16)

**What a bad actor wants.** A direct line from the company to their own spot, and the loop it makes, avoiding contact with every other face.

**Honest money takes the long way round.**
- Someone with two jobs simply has two pins pointing to them.
- Paying taxes touches the other side (authority) and comes back as services, so the loop is long, not a tight circle.

**The signature is not how many pins a person has but which faces their loops touch.** A bad loop closes on itself without touching the authority face (tax, disclosure) or an arm's-length counterparty. Examples are an inflated contract to an insider's own firm, or round-tripping.

**Framework tie (`ARC_ALIGNMENT_GRID`).** Closure collects one vote per domain a path crosses. A loop that crosses no other domain collects **zero votes**: it is self-certified.

**Data.**
- Banks screen for circular flows (round-tripping) in anti-money-laundering monitoring, but transaction-level data is private.
- The public, company-level shadow is **how much of a company's money touches the authority face**: cash taxes paid against pre-tax profit.
- Prior evidence: Kim, Li & Zhang (2011) found that more corporate tax avoidance comes before a higher risk of stock-price crashes (bad news hoarded, then released).

**The invisible vortex (Jonathan).** This is the dam from `Shovelcat_29` §6.6 (one node captures Water and doesn't release it) made invisible: the bad actor builds their own vortex without it touching the walls.
- **A dam is anchored to the canyon walls,** so everyone can see the reservoir. That is a visible cash pile, the three-body paper's Void: Berkshire's cash is a dam. **The vortex holds water with no wall anyone can see** (off the books).
- **Fluid rule (Helmholtz's vortex theorems).** A vortex line cannot end inside the fluid: it either ends on a boundary or closes on itself as a ring. Honest lines end on walls. The bad loop is the ring.
  - A vortex ring carries a bubble of trapped fluid with it.
  - Friction with its surroundings (viscosity) wears a vortex down, which is why the bad actor avoids contact: **contact is the friction** (taxes, audits, witnesses).
  - `Shovelcat_29`'s Water equation is written like Navier–Stokes, so this is the framework's own analogy, not a new one.
- **How an invisible vortex shows anyway:**
  1. **Its water is missing elsewhere:** the leak, the missing ending, and the downstream drought.
  2. **Nearby lines bend around it.**
  3. **When it breaks, the trapped water comes out all at once.** That is the "came-out-of-nowhere" spike of the hidden oscillatory term (`Shovelcat_29` §3.5) and Kim–Li–Zhang's crash.
- **So the tax-avoidance → crash test is the vortex test:** money that avoids the authority face, then a sudden release.

### Test: the vortex. Does money that avoids the authority face come before a sudden break? (Oct 16; pre-registered in `D:\planet\mika\vortex\PREREGISTERED.md`)

**Data.**
- The ~520 companies minus financials and utilities: 3,759 annual reports from 356 companies, filed 2011–2025.
- **Avoidance** = minus the 3-year cash tax rate (cash taxes paid / pre-tax income), adjusted by industry.
- **The year after each 10-K:** weekly firm-specific returns (residuals on SPY at lags −1, 0, +1). From them: NCSKEW (how lopsided the drops are), DUVOL (down-week vs up-week volatility) and CRASH (a week below mean − 3.09 sd).
- Code: `vortex_fetch.py`, `vortex_test.py`, `vortex_checks.py`.

| Claim | Result | Passed? |
|---|---|---|
| Avoidance → NCSKEW | rank corr +0.039, t 2.18, 10/15 years | **yes** (just) |
| Avoidance → DUVOL | +0.043, t 2.50, 12/15 | **yes** |
| Top vs bottom avoidance quintile, crash weeks | 27.0% vs 24.3% (t 1.69) | no (right sign) |
| Avoidance → NCSKEW, controlling for past skew and size | slope +0.038, t 2.20 | **yes** |

**Spot-checks.** Apple's FY2021–23 cash tax rate by hand from its 10-Ks is 0.1860, matching the file. NCSKEW matches scipy's skewness of the same residuals exactly.

**Robustness (not pre-registered).**
- The effect has the same sign in both halves, 2011–17 and 2018–25.
- It is *stronger* with near-zero-tax reports removed, which argues against "it's just companies with past losses".
- It survives adding blur, leak, profitability, past skew and size as controls (t 2.06).
- The book (GAAP) tax rate shows nothing. Only *cash actually paid* to the authority face carries the signal.

**Reading.**
- **This is the first of our cube tests to pass,** and it is the one where Jonathan's picture and the published evidence (Kim–Li–Zhang 2011) predicted the same shape in advance.
- **The effect is a small tilt** (rank corr about 0.04) across hundreds of companies, not a detector for any one of them. Low cash taxes have many legitimate causes (R&D credits, depreciation timing).
- **It measures the shape of the falls** (sudden drops), not whether these stocks earn less on average. Returns were not tested.

**Build order:**
1. The US cube from Z.1: five sectors, check the endings, and see whether the leaks grow before 2008 and 2020.
2. Split business into BEA industry cubes.
3. Canada beside it.
4. Companies.

## First test: do leaks come before blur, and before weaker returns? (set 1: the 148 companies of the trading test)

**Code and data.**
- Code is in `D:\planet\mika\cube\`: `cube_fetch.py`, `cube_leak_blur.py`, `cube_leak_size.py` and `spotcheck.py`.
- Data is SEC XBRL company facts (the first-filed value from each original 10-K, so it is point-in-time) and daily prices 2010–2026.

**Method.**
- The event is the first trading day after the 10-K was filed.
- **Leak** = (net income − operating cash flow) / average assets.
- **Blur** = annualised volatility of the daily return minus β × SPY, with β from the prior year.
- **Windows:** blur is measured over 63 sessions before the event and the 63 or 126 after. Returns are over 126 or 252 sessions, minus the average of the set.
- **Statistics:** each filing year is one cross-section. The statistic is the rank correlation within each year, averaged over years, with t = mean / (sd / √years).
- **Banks and insurers are left out**, because a bank's operating cash flow is not a customer tunnel.
- **Sample:** 1,666 events, 2011–2026.

**Spot-check.** Apple FY2023 by hand from the 10-K: leak −0.0384, matching the file. β, blur before and blur after were recomputed by hand and matched exactly.

| Test (planned) | Rank corr | t | Same sign |
|---|---|---|---|
| leak → blur change, next 63 | −0.015 | −0.5 | 8/16 |
| leak → blur change, next 126 | −0.003 | −0.1 | 10/16 |
| leak → return vs the rest, 252 (Sloan) | +0.002 | +0.1 | 6/15 |
| receivable leak → return, 252 | +0.043 | +1.2 | 9/15 |
| blur → return, 252 (Ang et al.) | +0.042 | +0.9 | 10/15 |
| **blur now → blur next 63** | **+0.676** | **+19.0** | **16/16** |

**Reading.**
- None of the three planned effects shows up in these large companies.
- Sloan's accrual effect fading after publication is also the published view (Green, Hand & Soliman 2011, "Going, going, gone?").
- What is solid is **the blur radius itself**: a company's blur is very stable from one quarter to the next, in every year. It is a real property of the box, like its size.
- **One unplanned pattern.** Both ends of the leak range did better than the middle:
  - quintile 1, cash far ahead of earnings (21% of these reports were losses, so many are big non-cash write-downs): +4.5%;
  - quintile 5, earnings ahead of cash: +3.7%;
  - middle quintiles: −5.1% to −0.4%.
  - The *size* of the mismatch either way gave rank corr +0.096 (t 2.75, 11/15 years). This was found after looking, so it was written down (`D:\planet\mika\cube2\PREREGISTERED.md`) and re-tested on fresh companies below.
- The mismatch does **not** come before more blur (+0.008, t 0.3).

## Re-test on fresh companies (set 2: the 374 current S&P 500 members not in set 1)

The claims and the pass bar (same sign, t > 2) were written down before the data was fetched: `D:\planet\mika\cube2\PREREGISTERED.md`. Set 2 has 3,915 events, 2011–2026, with the same code.

| Claim | Set 1 | Set 2 | Passed? |
|---|---|---|---|
| 1. mismatch → return 252 (found after looking) | +0.096, t 2.75 | +0.049, t 1.88, 9/15 | **no** (half the size, under the bar) |
| 2. leak → blur change 63 | −0.015, t −0.5 | +0.036, t 1.45 | **no** |
| 3. leak → return 252 (Sloan) | +0.002, t 0.1 | −0.044, t −1.61 | **no** (right sign in set 2 only) |
| 4. blur → return 252 (Ang) | +0.042, t 0.9 | +0.036, t 0.8 | **no** |
| 5. blur persistence | +0.676, t 19 | +0.639, t 13, 15/16 | **yes** |

**Seen in both sets, but not pre-registered and not trusted yet.** Quintile 1 did better afterwards: set 1 +4.5%, set 2 **+10.0%** (Q5 − Q1 −9.9%, t −2.6). Quintile 1 holds the reports whose cash is far ahead of their earnings, and 32% of them in set 2 are losses. This is Sloan's direction, concentrated at the low end.

It is also exactly what **survivorship** would produce. Both sets are companies that are big *today*. A company that posted big write-downs and then failed dropped out and isn't in the sample; one that recovered is. Testing this properly needs delisted companies' prices. Those are not on yfinance; CRSP-type data is paid.

## What it means for the cube

1. **The blur radius is real.** It is very stable for each company, in both sets and nearly every year. Keep it as a dimension of each box.
2. **Leaks read from one company's own books do not push it into blur.** A tunnel leak is between two ends, and this test only looked at one end. The real leak test needs the tunnels themselves, for example a customer's payments against a supplier's receipts. That means building the side faces first.
3. **None of the well-known single effects** (accruals, idiosyncratic volatility) gave a reliable signal on today's large companies. That is consistent with the literature on these effects fading.

## Next builds

- **Tunnels (side faces).**
  - Supplier → customer links from 10-K "major customer" disclosures. Customers worth ≥ 10% of revenue must be disclosed, and they are often named.
  - Industry-to-industry money flows from the BEA input–output tables.
  - Sector per company is already saved in `D:\planet\mika\cube\sp500_members.json` (S&P 500 list with GICS sector and CIK).
- **Front face.** Wikipedia page views as the first attention sensor. Test whether attention spikes with no money tunnel behind them fade (artificial rain).
- **Every test practice-only and pre-registered**, and graded on companies it wasn't designed on.
