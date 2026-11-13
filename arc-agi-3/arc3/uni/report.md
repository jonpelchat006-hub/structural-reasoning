# Mika's university: the board's report

Practice final (held back, never used to choose): bp35, lp85, r11l, sc25, tu93

Ratings on the TRAINING games (mean over 8 seeds; seeds won against plain; levels per seed).

## click (6 training games: ft09, s5i5, sb26, su15, tn36, vc33)

| professor | score | vs plain | seeds won | levels/seed | waste (spent/shortest) | cheap wins kept | verdict |
|---|---|---|---|---|---|---|---|
| plain | 0.224 | +0.000 | 0/8 | 4.8 | 73x | yes (1) | plain (reference) |
| runs-if-runs | 0.266 | +0.042 | 7/8 | 4.8 | 67x | yes (1) | passes |
| runs | 0.367 | +0.143 | 5/8 | 4.8 | 67x | yes (1) | fails: won 5/8 seeds |
| runs-light | 0.367 | +0.143 | 5/8 | 4.8 | 67x | yes (1) | fails: won 5/8 seeds |
| replay | 0.157 | -0.067 | 3/8 | 4.8 | 70x | no (1) | fails: gain below 0.02, won 3/8 seeds, breaks a cheap win |
| clicks-last | 0.224 | +0.000 | 0/8 | 4.8 | 73x | yes (1) | fails: gain below 0.02, won 0/8 seeds |
| fresh-kinds | 0.147 | -0.077 | 1/8 | 2.1 | 39x | no (1) | fails: gain below 0.02, won 1/8 seeds, breaks a cheap win |
| model | 0.224 | +0.000 | 0/8 | 4.8 | 73x | yes (1) | fails: gain below 0.02, won 0/8 seeds |
| route-prior | 0.219 | -0.005 | 6/8 | 5.0 | 78x | yes (1) | fails: gain below 0.02, won 6/8 seeds |
| route-prior-light | 0.233 | +0.009 | 5/8 | 5.0 | 76x | yes (1) | fails: gain below 0.02, won 5/8 seeds |
| took-control | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| took-light | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| win-event | 0.240 | +0.016 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| two-rungs | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| far-change | 0.248 | +0.025 | 7/8 | 4.8 | 57x | yes (1) | passes |
| far-change-win | 0.247 | +0.023 | 7/8 | 4.8 | 59x | yes (1) | passes |
| far-rare | 0.248 | +0.025 | 7/8 | 4.8 | 57x | yes (1) | passes |
| three-rungs | 0.246 | +0.022 | 7/8 | 4.8 | 59x | yes (1) | passes |
| win-image | 0.240 | +0.016 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| took-image | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| two-rungs-image | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| goal-search | 0.240 | +0.016 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| two-rungs-search | 0.239 | +0.015 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |
| pick-only | 0.240 | +0.016 | 7/8 | 4.8 | 60x | yes (1) | fails: gain below 0.02 |

**Board's choice for click: runs-if-runs.** As plain; and if the last level's winning route was long runs of one press, explore the next level by runs: keep pressing what just changed something.

## keys (5 training games: g50t, ls20, re86, tr87, wa30)

| professor | score | vs plain | seeds won | levels/seed | waste (spent/shortest) | cheap wins kept | verdict |
|---|---|---|---|---|---|---|---|
| plain | 0.181 | +0.000 | 0/8 | 1.2 | 21x | yes (0) | plain (reference) |
| runs-if-runs | 0.181 | +0.000 | 0/8 | 1.2 | 21x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| runs | 0.181 | +0.000 | 5/8 | 1.2 | 20x | yes (0) | fails: gain below 0.02, won 5/8 seeds |
| runs-light | 0.181 | +0.000 | 5/8 | 1.2 | 20x | yes (0) | fails: gain below 0.02, won 5/8 seeds |
| replay | 0.181 | +0.000 | 0/8 | 1.2 | 21x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| clicks-last | 0.181 | +0.000 | 0/8 | 1.2 | 21x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| fresh-kinds | 0.181 | +0.000 | 0/8 | 1.2 | 21x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| model | 0.183 | +0.002 | 6/8 | 1.2 | 22x | yes (0) | fails: gain below 0.02, won 6/8 seeds |
| route-prior | 0.001 | -0.180 | 0/8 | 1.0 | 43x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| route-prior-light | 0.001 | -0.180 | 0/8 | 1.0 | 43x | yes (0) | fails: gain below 0.02, won 0/8 seeds |
| took-control | 0.182 | +0.001 | 7/8 | 1.4 | 34x | yes (0) | fails: gain below 0.02 |
| took-light | 0.182 | +0.000 | 5/8 | 1.1 | 19x | yes (0) | fails: gain below 0.02, won 5/8 seeds |
| win-event | 0.181 | -0.000 | 3/8 | 1.2 | 24x | yes (0) | fails: gain below 0.02, won 3/8 seeds |
| two-rungs | 0.182 | +0.001 | 7/8 | 1.4 | 34x | yes (0) | fails: gain below 0.02 |
| far-change | 0.003 | -0.179 | 2/8 | 0.9 | 25x | yes (0) | fails: gain below 0.02, won 2/8 seeds |
| far-change-win | 0.003 | -0.179 | 2/8 | 0.9 | 25x | yes (0) | fails: gain below 0.02, won 2/8 seeds |
| far-rare | 0.002 | -0.179 | 1/8 | 0.9 | 28x | yes (0) | fails: gain below 0.02, won 1/8 seeds |
| three-rungs | 0.002 | -0.179 | 1/8 | 0.9 | 31x | yes (0) | fails: gain below 0.02, won 1/8 seeds |
| win-image | 0.181 | -0.000 | 3/8 | 1.2 | 24x | yes (0) | fails: gain below 0.02, won 3/8 seeds |
| took-image | 0.182 | +0.001 | 7/8 | 1.4 | 34x | yes (0) | fails: gain below 0.02 |
| two-rungs-image | 0.182 | +0.001 | 7/8 | 1.4 | 34x | yes (0) | fails: gain below 0.02 |
| goal-search | 0.181 | -0.000 | 3/8 | 1.2 | 24x | yes (0) | fails: gain below 0.02, won 3/8 seeds |
| two-rungs-search | 0.182 | +0.001 | 7/8 | 1.4 | 34x | yes (0) | fails: gain below 0.02 |
| pick-only | 0.181 | -0.000 | 3/8 | 1.2 | 24x | yes (0) | fails: gain below 0.02, won 3/8 seeds |

**Board's choice for keys: plain.** Try what you have not tried, nearest first; on a new level, click first the kinds of thing that were on the last winning route.

## mixed (9 training games: ar25, cd82, cn04, dc22, ka59, lf52, m0r0, sk48, sp80)

| professor | score | vs plain | seeds won | levels/seed | waste (spent/shortest) | cheap wins kept | verdict |
|---|---|---|---|---|---|---|---|
| plain | 0.338 | +0.000 | 0/8 | 7.8 | 47x | yes (1) | plain (reference) |
| runs-if-runs | 0.340 | +0.002 | 7/8 | 8.6 | 51x | yes (1) | fails: gain below 0.02 |
| runs | 0.084 | -0.255 | 1/8 | 8.1 | 60x | no (1) | fails: gain below 0.02, won 1/8 seeds, breaks a cheap win |
| runs-light | 0.084 | -0.254 | 1/8 | 7.9 | 60x | no (1) | fails: gain below 0.02, won 1/8 seeds, breaks a cheap win |
| replay | 0.338 | -0.000 | 1/8 | 7.5 | 43x | yes (1) | fails: gain below 0.02, won 1/8 seeds |
| clicks-last | 0.323 | -0.015 | 0/8 | 7.5 | 48x | yes (1) | fails: gain below 0.02, won 0/8 seeds |
| fresh-kinds | 0.272 | -0.066 | 0/8 | 6.8 | 44x | yes (1) | fails: gain below 0.02, won 0/8 seeds |
| model | 0.328 | -0.011 | 0/8 | 6.8 | 52x | yes (1) | fails: gain below 0.02, won 0/8 seeds |
| route-prior | 0.092 | -0.246 | 0/8 | 6.0 | 53x | no (1) | fails: gain below 0.02, won 0/8 seeds, breaks a cheap win |
| route-prior-light | 0.127 | -0.211 | 0/8 | 6.9 | 52x | no (1) | fails: gain below 0.02, won 0/8 seeds, breaks a cheap win |
| took-control | 0.381 | +0.043 | 3/8 | 6.9 | 41x | yes (1) | fails: won 3/8 seeds |
| took-light | 0.323 | -0.015 | 3/8 | 6.9 | 40x | yes (1) | fails: gain below 0.02, won 3/8 seeds |
| win-event | 0.327 | -0.011 | 1/8 | 6.9 | 42x | yes (1) | fails: gain below 0.02, won 1/8 seeds |
| two-rungs | 0.381 | +0.043 | 3/8 | 6.9 | 41x | yes (1) | fails: won 3/8 seeds |
| far-change | 0.331 | -0.007 | 2/8 | 6.5 | 44x | yes (1) | fails: gain below 0.02, won 2/8 seeds |
| far-change-win | 0.332 | -0.006 | 2/8 | 6.2 | 39x | yes (1) | fails: gain below 0.02, won 2/8 seeds |
| far-rare | 0.319 | -0.020 | 1/8 | 6.8 | 47x | yes (1) | fails: gain below 0.02, won 1/8 seeds |
| three-rungs | 0.322 | -0.016 | 2/8 | 6.6 | 35x | yes (1) | fails: gain below 0.02, won 2/8 seeds |
| win-image | 0.328 | -0.011 | 1/8 | 7.4 | 48x | yes (1) | fails: gain below 0.02, won 1/8 seeds |
| took-image | 0.381 | +0.043 | 3/8 | 6.9 | 41x | yes (1) | fails: won 3/8 seeds |
| two-rungs-image | 0.381 | +0.043 | 3/8 | 6.9 | 41x | yes (1) | fails: won 3/8 seeds |
| goal-search | 0.328 | -0.011 | 1/8 | 7.4 | 48x | yes (1) | fails: gain below 0.02, won 1/8 seeds |
| two-rungs-search | 0.381 | +0.043 | 3/8 | 6.9 | 41x | yes (1) | fails: won 3/8 seeds |
| pick-only | 0.328 | -0.011 | 1/8 | 7.4 | 48x | yes (1) | fails: gain below 0.02, won 1/8 seeds |

**Board's choice for mixed: plain.** Try what you have not tried, nearest first; on a new level, click first the kinds of thing that were on the last winning route.

## The practice final (opened after the choices above)

| game | department | professor chosen | its score | plain's score | best professor here (for reference) |
|---|---|---|---|---|---|
| bp35 | mixed | plain | 0.00 | 0.00 | runs (0.02) |
| lp85 | click | runs-if-runs | 2.55 | 2.60 | plain (2.60) |
| r11l | click | runs-if-runs | 2.49 | 2.49 | two-rungs (3.20) |
| sc25 | mixed | plain | 1.95 | 1.95 | runs-light (3.17) |
| tu93 | keys | plain | 0.62 | 0.62 | took-control (0.88) |

Practice final: university 1.522 vs plain 1.533; university better on 0/8 seeds, worse on 1/8.

All 25 games: university 0.526 vs plain 0.518.
