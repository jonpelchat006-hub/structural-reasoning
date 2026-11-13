# Community evidence and authorized upstream resources

Reproduce: `python -B experiment_alignment_community.py --seeds 20 --weeks 24`

76 condition groups × 20 seeds × 24 weeks. Full weekly household outcomes, cash/goods ledgers, reports, audits, actions, queues, configurations and source hashes are preserved in `alignment_community_results.json`.

This factorial test separates knowing about a problem from having authority and resources to address it. It preserves the same households and protected needs in all four arms. Outcomes are conditional on invented mechanics; this is not a claim about actual taxation, institutions or moral optimality.

## Key findings from this run

Transfers, truthful audits and capacity expansion are stipulated mechanisms. The following are observed outcomes of the common controller under those assumptions, not empirical estimates:

- With available goods but scarce public cash, authorized taxation reduces mean unmet goods from 77.60 to 9.60. It collects 92.40 cash under the chosen rate, cap, cost and delay.
- Correcting diversion reduces unmet goods from 53.60 to 1.20, with 0.00 new tax collected. The resource problem need not always be inadequate taxation.
- Where local enrollment/access repairs are already permitted, community leads reduce unmet goods from 24.72 to 16.88; failure household-weeks fall from 30.90 to 21.10.
- With supply fixed at eight goods/week and no expansion mandate, increasing the weekly budget from 8 to 30 leaves unmet goods at 96.00 versus 96.00. Cash alone does not remove this modeled physical constraint.
- Community input can also worsen this controller's audit allocation: in the expandable-supply case, unmet goods rise from 16.00 to 20.00 when community leads are added. With a shared blind spot, they rise from 24.72 to 26.36.
- In the mixed case, unmet goods are 89.76 with neither channel, 89.76 with community alone, 26.58 with upstream authority alone, and 21.14 with both. The paired interaction is -5.44 ± 3.72, range [-10.20, 3.40]; the combination is not uniformly better across seeds.

## Four matched arms

| Arm | Community audit leads | Authorized upstream options |
| --- | --- | --- |
| local | no | no |
| community | yes | no |
| upstream | no | yes |
| combined | yes | yes |

The controller, baseline audits and audit/action capacities are held fixed. Community reports compete for the same audit slots. An authenticated or repeated claim would still require factual checking; this simulation does not implement cryptographic witness authentication.

## Assumptions and measured outcomes

- The cohort and protected real-goods needs are fixed across all arms. Policies cannot improve the score by removing households or lowering their needs.
- Cash and actual goods are separate conserved accounts. Higher budgets or taxes collected do not themselves count as meeting a need.
- Community reports are fallible audit leads, not ground truth or extra money. Both arms have the same audit and action capacities.
- Audits are stipulated truthful checks. False-report controls therefore test audit attention and authorization gates, not robustness to corrupted auditors or a shared verification failure.
- Baseline audits remain available without community reports. Information can help through local correction even without upstream authority.
- Upstream authority permits only the configured actions. It does not guarantee an action's success or make resources unlimited.
- A paid supply expansion raises future stipulated production after a delay. Goods conservation is stock-flow accounting including that production, not a model of all labor, energy or physical inputs.
- Reserves and diverted funds exist outside the initial public spending account but are included in the system accounts. Releasing them transfers resources rather than creating them.
- Tax is an authorized synthetic option on protected surplus, with rates, caps, delays and collection costs chosen as inputs. It is not a legal or economic recommendation.
- Private basic purchases precede public top-ups and bypass public delivery capacity and access barriers. These limits apply only to public assistance in this model.
- Public allocations are proportional to enrolled households' remaining needs, including blocked households. A blocked share stays unspent and is not reassigned that week; physical stock then limits actual receipt.
- Prices, incomes, production responses and household needs are stipulated. There is no calibrated macroeconomy, tax avoidance, inflation, labor response or political process.
- The shared-blind-spot condition models correlated omission. It does not establish resistance to colluding witnesses, forged signatures, or correlated false assertions.
- Randomness is paired by seed and external event. Different actions can cause different observed paths; the arms do not receive an identical sequence of decisions.
- All outcome truth is evaluated by the simulator. A real deployment would need independent measurement, representative testimony and enforceable authorization.
- Across-seed SD and ranges describe these simulated worlds, not sampling uncertainty about people or real policy effects.

Primary outcomes are unmet real-goods units and household-weeks below the fixed needs. A run has 288 possible household-weeks. Worst-household unmet goods guards against hiding persistent exclusion in an average. Claimed deliveries and actual goods are reported separately. More reports, approved funds or taxes collected are not themselves successes.

Dashboard coverage is allocated public top-ups divided by enrolled households' remaining need; actual coverage is received private-plus-public goods divided by the entire cohort's fixed need. Their denominators deliberately differ. The former can report closure while excluded or blocked households still lack goods. Both are reported as average weekly fractions, not a causal effect by themselves.

Numbers are mean ± sample SD; brackets show seed minimum and maximum. Every summary metric has all these statistics in the JSON. No real-population confidence intervals are inferred.

## Main profiles

### adequate

Overrides: `{"base_budget": 8.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 134.40 ± 0.00 | 134.40 ± 0.00 |
| community | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 134.40 ± 0.00 | 134.40 ± 0.00 |
| upstream | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 134.40 ± 0.00 | 134.40 ± 0.00 |
| combined | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 134.40 ± 0.00 | 134.40 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 61.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 61.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 / 48.00 |
| upstream | 61.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| combined | 61.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| community | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| upstream | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| combined | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |

### eligibility_and_access

Overrides: `{"base_budget": 8.0, "blocked_ids": [3, 4], "hidden_ids": [0, 1, 2]}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| community | 21.10 ± 2.00 [20.00, 25.00] | 16.88 ± 1.60 [16.00, 20.00] | 4.92 ± 0.29 | 117.52 ± 1.60 | 124.08 ± 1.35 |
| upstream | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| combined | 21.10 ± 2.00 [20.00, 25.00] | 16.88 ± 1.60 [16.00, 20.00] | 4.92 ± 0.29 | 117.52 ± 1.60 | 124.08 ± 1.35 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| community | 76.48 ± 1.60 | 0.00 ± 0.00 | 0.00 ± 0.00 | 208.88 ± 1.60 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 29.10 / 48.00 |
| upstream | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| combined | 76.48 ± 1.60 | 0.00 ± 0.00 | 0.00 ± 0.00 | 208.88 ± 1.60 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 29.10 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| community | 1.00 ± 0.00 | 0.94 ± 0.01 | 10.32 ± 1.35 |
| upstream | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| combined | 1.00 ± 0.00 | 0.94 ± 0.01 | 10.32 ± 1.35 |

### outside_reserves

Overrides: `{"allowed_upstream": ["release_reserve"], "reserve_cash": 50.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 184.00 ± 0.00 [184.00, 184.00] | 77.60 ± 0.00 [77.60, 77.60] | 11.09 ± 0.00 | 56.80 ± 0.00 | 56.80 ± 0.00 |
| community | 184.00 ± 0.00 [184.00, 184.00] | 77.60 ± 0.00 [77.60, 77.60] | 11.09 ± 0.00 | 56.80 ± 0.00 | 56.80 ± 0.00 |
| upstream | 72.00 ± 0.00 [72.00, 72.00] | 27.60 ± 0.00 [27.60, 27.60] | 3.94 ± 0.00 | 106.80 ± 0.00 | 106.80 ± 0.00 |
| combined | 72.00 ± 0.00 [72.00, 72.00] | 27.60 ± 0.00 [27.60, 27.60] | 3.94 ± 0.00 | 106.80 ± 0.00 | 106.80 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 0.00 ± 0.00 | 50.00 ± 0.00 | 0.00 ± 0.00 | 269.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 0.00 ± 0.00 | 50.00 ± 0.00 | 0.00 ± 0.00 | 269.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 184.00 / 48.00 |
| upstream | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 219.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| combined | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 219.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 72.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 0.42 ± 0.00 | 0.73 ± 0.00 | 0.00 ± 0.00 |
| community | 0.42 ± 0.00 | 0.73 ± 0.00 | 0.00 ± 0.00 |
| upstream | 0.79 ± 0.00 | 0.90 ± 0.00 | 0.00 ± 0.00 |
| combined | 0.79 ± 0.00 | 0.90 ± 0.00 | 0.00 ± 0.00 |

### cash_scarce_tax

Overrides: `{"allowed_upstream": ["tax"]}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 184.00 ± 0.00 [184.00, 184.00] | 77.60 ± 0.00 [77.60, 77.60] | 11.09 ± 0.00 | 56.80 ± 0.00 | 56.80 ± 0.00 |
| community | 184.00 ± 0.00 [184.00, 184.00] | 77.60 ± 0.00 [77.60, 77.60] | 11.09 ± 0.00 | 56.80 ± 0.00 | 56.80 ± 0.00 |
| upstream | 24.00 ± 0.00 [24.00, 24.00] | 9.60 ± 0.00 [9.60, 9.60] | 1.37 ± 0.00 | 124.80 ± 0.00 | 124.80 ± 0.00 |
| combined | 24.00 ± 0.00 [24.00, 24.00] | 9.60 ± 0.00 [9.60, 9.60] | 1.37 ± 0.00 | 124.80 ± 0.00 | 124.80 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 269.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 269.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 184.00 / 48.00 |
| upstream | 11.80 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 201.60 ± 0.00 | 92.40 ± 0.00 | 4.62 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| combined | 11.80 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 201.60 ± 0.00 | 92.40 ± 0.00 | 4.62 ± 0.00 | 0.00 ± 0.00 | 32.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 0.42 ± 0.00 | 0.73 ± 0.00 | 0.00 ± 0.00 |
| community | 0.42 ± 0.00 | 0.73 ± 0.00 | 0.00 ± 0.00 |
| upstream | 0.93 ± 0.00 | 0.97 ± 0.00 | 0.00 ± 0.00 |
| combined | 0.93 ± 0.00 | 0.97 ± 0.00 | 0.00 ± 0.00 |

### diversion

Overrides: `{"allowed_upstream": ["recover_diversion"], "base_budget": 8.0, "diversion_rate": 0.6}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 184.00 ± 0.00 [184.00, 184.00] | 53.60 ± 0.00 [53.60, 53.60] | 7.66 ± 0.00 | 80.80 ± 0.00 | 80.80 ± 0.00 |
| community | 184.00 ± 0.00 [184.00, 184.00] | 53.60 ± 0.00 [53.60, 53.60] | 7.66 ± 0.00 | 80.80 ± 0.00 | 80.80 ± 0.00 |
| upstream | 8.00 ± 0.00 [8.00, 8.00] | 1.20 ± 0.00 [1.20, 1.20] | 0.17 ± 0.00 | 133.20 ± 0.00 | 133.20 ± 0.00 |
| combined | 8.00 ± 0.00 [8.00, 8.00] | 1.20 ± 0.00 [1.20, 1.20] | 0.17 ± 0.00 | 133.20 ± 0.00 | 133.20 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 0.00 ± 0.00 | 0.00 ± 0.00 | 115.20 ± 0.00 | 245.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 0.00 ± 0.00 | 0.00 ± 0.00 | 115.20 ± 0.00 | 245.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 184.00 / 48.00 |
| upstream | 60.48 ± 0.00 | 0.00 ± 0.00 | 1.92 ± 0.00 | 193.20 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.40 ± 0.00 | 0.00 / 48.00 |
| combined | 60.48 ± 0.00 | 0.00 ± 0.00 | 1.92 ± 0.00 | 193.20 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.40 ± 0.00 | 16.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 0.60 ± 0.00 | 0.81 ± 0.00 | 0.00 ± 0.00 |
| community | 0.60 ± 0.00 | 0.81 ± 0.00 | 0.00 ± 0.00 |
| upstream | 0.99 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| combined | 0.99 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |

### goods_shortage_tax_only

Overrides: `{"allowed_upstream": ["tax"], "base_budget": 8.0, "goods_per_week": 8.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |
| community | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |
| upstream | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |
| combined | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 157.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 157.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 / 48.00 |
| upstream | 157.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| combined | 157.60 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |
| community | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |
| upstream | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |
| combined | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |

### expandable_supply

Overrides: `{"base_budget": 8.0, "goods_per_week": 8.0, "reserve_cash": 20.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |
| community | 192.00 ± 0.00 [192.00, 192.00] | 96.00 ± 0.00 [96.00, 96.00] | 13.71 ± 0.00 | 38.40 ± 0.00 | 134.40 ± 0.00 |
| upstream | 32.00 ± 0.00 [32.00, 32.00] | 16.00 ± 0.00 [16.00, 16.00] | 2.29 ± 0.00 | 118.40 ± 0.00 | 134.40 ± 0.00 |
| combined | 40.00 ± 0.00 [40.00, 40.00] | 20.00 ± 0.00 [20.00, 20.00] | 2.86 ± 0.00 | 114.40 ± 0.00 | 134.40 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 157.60 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 157.60 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 / 48.00 |
| upstream | 73.60 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 4.00 ± 0.00 | 0.00 / 48.00 |
| combined | 77.60 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 4.00 ± 0.00 | 48.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |
| community | 1.00 ± 0.00 | 0.67 ± 0.00 | 0.00 ± 0.00 |
| upstream | 1.00 ± 0.00 | 0.94 ± 0.00 | 0.00 ± 0.00 |
| combined | 1.00 ± 0.00 | 0.93 ± 0.00 | 0.00 ± 0.00 |

### delivery_bottleneck

Overrides: `{"allowed_upstream": ["release_reserve", "expand_delivery"], "base_budget": 8.0, "delivery_capacity": 3.0, "reserve_cash": 20.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 192.00 ± 0.00 [192.00, 192.00] | 62.40 ± 0.00 [62.40, 62.40] | 8.91 ± 0.00 | 72.00 ± 0.00 | 72.00 ± 0.00 |
| community | 192.00 ± 0.00 [192.00, 192.00] | 62.40 ± 0.00 [62.40, 62.40] | 8.91 ± 0.00 | 72.00 ± 0.00 | 72.00 ± 0.00 |
| upstream | 32.00 ± 0.00 [32.00, 32.00] | 10.40 ± 0.00 [10.40, 10.40] | 1.49 ± 0.00 | 124.00 ± 0.00 | 124.00 ± 0.00 |
| combined | 40.00 ± 0.00 [40.00, 40.00] | 13.00 ± 0.00 [13.00, 13.00] | 1.86 ± 0.00 | 121.40 ± 0.00 | 121.40 ± 0.00 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 124.00 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 254.40 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 / 48.00 |
| community | 124.00 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 254.40 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 192.00 / 48.00 |
| upstream | 70.00 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 202.40 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| combined | 72.60 ± 0.00 | 20.00 ± 0.00 | 0.00 ± 0.00 | 205.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 48.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 0.54 ± 0.00 | 0.78 ± 0.00 | 0.00 ± 0.00 |
| community | 0.54 ± 0.00 | 0.78 ± 0.00 | 0.00 ± 0.00 |
| upstream | 0.92 ± 0.00 | 0.96 ± 0.00 | 0.00 ± 0.00 |
| combined | 0.90 ± 0.00 | 0.95 ± 0.00 | 0.00 ± 0.00 |

### false_community_claims

Overrides: `{"base_budget": 8.0, "blocked_ids": [3, 4], "community_false_rate": 0.35, "hidden_ids": [0, 1, 2]}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| community | 27.15 ± 3.84 [22.00, 35.00] | 21.72 ± 3.07 [17.60, 28.00] | 6.76 ± 0.88 | 112.68 ± 3.07 | 121.04 ± 3.28 |
| upstream | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| combined | 27.15 ± 3.84 [22.00, 35.00] | 21.72 ± 3.07 [17.60, 28.00] | 6.76 ± 0.88 | 112.68 ± 3.07 | 121.04 ± 3.28 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| community | 81.32 ± 3.07 | 0.00 ± 0.00 | 0.00 ± 0.00 | 213.72 ± 3.07 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 121.80 / 48.00 |
| upstream | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| combined | 81.32 ± 3.07 | 0.00 ± 0.00 | 0.00 ± 0.00 | 213.72 ± 3.07 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 121.80 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| community | 1.00 ± 0.00 | 0.92 ± 0.01 | 13.36 ± 3.28 |
| upstream | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| combined | 1.00 ± 0.00 | 0.92 ± 0.01 | 13.36 ± 3.28 |

### shared_blind_spot

Overrides: `{"base_budget": 8.0, "blocked_ids": [3, 4], "community_blind_ids": [0, 1, 2, 3, 4], "hidden_ids": [0, 1, 2]}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| community | 32.95 ± 3.68 [27.00, 40.00] | 26.36 ± 2.94 [21.60, 32.00] | 6.92 ± 0.54 | 108.04 ± 2.94 | 118.40 ± 2.22 |
| upstream | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| combined | 32.95 ± 3.68 [27.00, 40.00] | 26.36 ± 2.94 [21.60, 32.00] | 6.92 ± 0.54 | 108.04 ± 2.94 | 118.40 ± 2.22 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| community | 85.96 ± 2.94 | 0.00 ± 0.00 | 0.00 ± 0.00 | 218.36 ± 2.94 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 3.00 / 48.00 |
| upstream | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| combined | 85.96 ± 2.94 | 0.00 ± 0.00 | 0.00 ± 0.00 | 218.36 ± 2.94 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 3.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| community | 1.00 ± 0.00 | 0.91 ± 0.01 | 16.00 ± 2.22 |
| upstream | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| combined | 1.00 ± 0.00 | 0.91 ± 0.01 | 16.00 ± 2.22 |

### zero_community_coverage

Overrides: `{"base_budget": 8.0, "blocked_ids": [3, 4], "community_coverage": 0.0, "hidden_ids": [0, 1, 2]}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| community | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| upstream | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |
| combined | 30.90 ± 3.37 [26.00, 37.00] | 24.72 ± 2.70 [20.80, 29.60] | 6.64 ± 0.59 | 109.68 ± 2.70 | 119.16 ± 2.07 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| community | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| upstream | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |
| combined | 84.32 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 216.72 ± 2.70 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| community | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| upstream | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |
| combined | 1.00 ± 0.00 | 0.91 ± 0.01 | 15.24 ± 2.07 |

### mixed

Overrides: `{"blocked_ids": [2, 3], "delivery_capacity": 6.0, "diversion_rate": 0.2, "goods_per_week": 10.0, "hidden_ids": [0, 1], "reserve_cash": 30.0}`

| Arm | Failure household-weeks [range] | Unmet goods [range] | Worst household unmet | Actual public goods | Claimed public goods |
| --- | --- | --- | --- | --- | --- |
| local | 181.20 ± 1.88 [180.00, 184.00] | 89.76 ± 0.00 [89.76, 89.76] | 15.19 ± 0.20 | 44.64 ± 0.00 | 52.55 ± 0.99 |
| community | 184.00 ± 0.00 [184.00, 184.00] | 89.76 ± 0.00 [89.76, 89.76] | 15.15 ± 0.56 | 44.64 ± 0.00 | 50.28 ± 1.49 |
| upstream | 44.00 ± 5.11 [37.00, 52.00] | 26.58 ± 2.47 [23.18, 29.98] | 7.45 ± 0.59 | 107.82 ± 2.47 | 117.68 ± 1.79 |
| combined | 40.05 ± 4.66 [34.00, 49.00] | 21.14 ± 2.31 [19.78, 26.58] | 5.65 ± 0.42 | 113.26 ± 2.31 | 119.80 ± 2.31 |

| Arm | Final public cash | Final outside reserve | Final diverted cash | Final goods stock | Tax collected | Administration cost | Repair cost | Reports / audits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local | 0.00 ± 0.00 | 30.00 ± 0.00 | 10.56 ± 0.00 | 41.76 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.60 ± 0.00 | 0.00 / 48.00 |
| community | 0.00 ± 0.00 | 30.00 ± 0.00 | 10.56 ± 0.00 | 41.76 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.60 ± 0.00 | 184.00 / 48.00 |
| upstream | 4.72 ± 0.43 | 0.00 ± 0.00 | 0.18 ± 0.00 | 45.98 ± 5.41 | 42.00 ± 3.05 | 2.10 ± 0.15 | 6.00 ± 0.00 | 0.00 / 48.00 |
| combined | 5.66 ± 0.40 | 0.00 ± 0.00 | 0.18 ± 0.00 | 45.54 ± 4.89 | 48.72 ± 2.86 | 2.44 ± 0.14 | 6.00 ± 0.00 | 48.05 / 48.00 |

| Arm | Dashboard coverage | Actual all-household coverage | Unregistered unmet goods |
| --- | --- | --- | --- |
| local | 0.45 ± 0.01 | 0.69 ± 0.00 | 9.84 ± 1.76 |
| community | 0.42 ± 0.01 | 0.69 ± 0.00 | 7.36 ± 2.10 |
| upstream | 0.95 ± 0.01 | 0.91 ± 0.01 | 9.84 ± 1.76 |
| combined | 0.94 ± 0.02 | 0.93 ± 0.01 | 7.00 ± 1.24 |

## Paired factorial effects

Every difference is computed within the same seed before aggregation. For unmet goods, negative values mean improvement. Interaction = (combined − upstream) − (community − local). A negative interaction means that community evidence reduces unmet goods more when upstream authority is available. It does not prove that either channel is universally necessary or sufficient.

| Profile | Community effect, local only | Community effect, upstream enabled | Upstream effect, no community | Upstream effect, community | Interaction [range] |
| --- | --- | --- | --- | --- | --- |
| adequate | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| eligibility_and_access | -7.84 ± 3.29 | -7.84 ± 3.29 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| outside_reserves | 0.00 ± 0.00 | 0.00 ± 0.00 | -50.00 ± 0.00 | -50.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| cash_scarce_tax | 0.00 ± 0.00 | 0.00 ± 0.00 | -68.00 ± 0.00 | -68.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| diversion | 0.00 ± 0.00 | 0.00 ± 0.00 | -52.40 ± 0.00 | -52.40 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| goods_shortage_tax_only | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| expandable_supply | 0.00 ± 0.00 | 4.00 ± 0.00 | -80.00 ± 0.00 | -76.00 ± 0.00 | 4.00 ± 0.00 [4.00, 4.00] |
| delivery_bottleneck | 0.00 ± 0.00 | 2.60 ± 0.00 | -52.00 ± 0.00 | -49.40 ± 0.00 | 2.60 ± 0.00 [2.60, 2.60] |
| false_community_claims | -3.00 ± 3.49 | -3.00 ± 3.49 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| shared_blind_spot | 1.64 ± 0.61 | 1.64 ± 0.61 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| zero_community_coverage | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| mixed | 0.00 ± 0.00 | -5.44 ± 3.72 | -63.18 ± 2.47 | -68.62 ± 2.31 | -5.44 ± 3.72 [-10.20, 3.40] |
| mixed_slow_actions | 0.00 ± 0.00 | -0.00 ± 0.00 | -35.63 ± 0.00 | -35.63 ± 0.00 | -0.00 ± 0.00 [-0.00, 0.00] |
| stale_community_reports | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| goods_shortage_more_funding | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| tax_rate_0 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| tax_rate_0.15 | 0.00 ± 0.00 | 0.00 ± 0.00 | -39.90 ± 0.00 | -39.90 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| tax_rate_0.3 | 0.00 ± 0.00 | 0.00 ± 0.00 | -68.00 ± 0.00 | -68.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |
| tax_rate_0.6 | 0.00 ± 0.00 | 0.00 ± 0.00 | -68.00 ± 0.00 | -68.00 ± 0.00 | 0.00 ± 0.00 [0.00, 0.00] |

## Delays, funding and authorized tax-rate sensitivity

The slow-actions case increases all correction/resource delays to six weeks. The stale-reports case delivers reports after their three-week lifetime. Tax rates 0/0.15/0.3/0.6 change only the rate in the tax-only cash-scarcity profile; authorized caps, protected allowance, collection cost and delay remain in force. Rates 0.3 and 0.6 can reach the same 4.2-per-week collection cap, so similar results cannot establish an optimal rate. The goods-shortage funding control increases the weekly public budget from 8 to 30 with supply still 8 and only taxation authorized upstream. It tests an actual extra-money intervention without a physical expansion option. These are synthetic parameter choices, not policy estimates.

| Profile | Arm | Unmet goods | Failure household-weeks | Tax collected | Tax net arrived | Final household cash | Final pending events |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mixed_slow_actions | local | 89.76 ± 0.00 | 181.20 ± 1.88 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| mixed_slow_actions | community | 89.76 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| mixed_slow_actions | upstream | 54.13 ± 0.00 | 103.20 ± 4.96 | 7.14 ± 3.08 | 0.00 ± 0.00 | 424.86 ± 3.08 | 1.70 ± 0.73 |
| mixed_slow_actions | combined | 54.13 ± 0.00 | 109.25 ± 4.95 | 10.92 ± 3.95 | 0.00 ± 0.00 | 421.08 ± 3.95 | 2.60 ± 0.94 |
| stale_community_reports | local | 24.72 ± 2.70 | 30.90 ± 3.37 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| stale_community_reports | community | 24.72 ± 2.70 | 30.90 ± 3.37 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| stale_community_reports | upstream | 24.72 ± 2.70 | 30.90 ± 3.37 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| stale_community_reports | combined | 24.72 ± 2.70 | 30.90 ± 3.37 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| goods_shortage_more_funding | local | 96.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| goods_shortage_more_funding | community | 96.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| goods_shortage_more_funding | upstream | 96.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| goods_shortage_more_funding | combined | 96.00 ± 0.00 | 192.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0 | local | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0 | community | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0 | upstream | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0 | combined | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.15 | local | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.15 | community | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.15 | upstream | 37.70 ± 0.00 | 184.00 ± 0.00 | 46.20 ± 0.00 | 39.90 ± 0.00 | 385.80 ± 0.00 | 2.00 ± 0.00 |
| tax_rate_0.15 | combined | 37.70 ± 0.00 | 184.00 ± 0.00 | 46.20 ± 0.00 | 39.90 ± 0.00 | 385.80 ± 0.00 | 2.00 ± 0.00 |
| tax_rate_0.3 | local | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.3 | community | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.3 | upstream | 9.60 ± 0.00 | 24.00 ± 0.00 | 92.40 ± 0.00 | 79.80 ± 0.00 | 339.60 ± 0.00 | 2.00 ± 0.00 |
| tax_rate_0.3 | combined | 9.60 ± 0.00 | 24.00 ± 0.00 | 92.40 ± 0.00 | 79.80 ± 0.00 | 339.60 ± 0.00 | 2.00 ± 0.00 |
| tax_rate_0.6 | local | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.6 | community | 77.60 ± 0.00 | 184.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 432.00 ± 0.00 | 0.00 ± 0.00 |
| tax_rate_0.6 | upstream | 9.60 ± 0.00 | 24.00 ± 0.00 | 92.40 ± 0.00 | 79.80 ± 0.00 | 339.60 ± 0.00 | 2.00 ± 0.00 |
| tax_rate_0.6 | combined | 9.60 ± 0.00 | 24.00 ± 0.00 | 92.40 ± 0.00 | 79.80 ± 0.00 | 339.60 ± 0.00 | 2.00 ± 0.00 |

Paired extra-funding effect below: weekly budget 30 minus 8, with goods supply and authorization unchanged.

| Arm | Change unmet goods [range] | Change failure household-weeks | Change public cash |
| --- | --- | --- | --- |
| local | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 528.00 ± 0.00 |
| community | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 528.00 ± 0.00 |
| upstream | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 528.00 ± 0.00 |
| combined | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 | 528.00 ± 0.00 |

## Limits and provenance

Information alone cannot transfer funds or manufacture goods; authority alone need not reveal hidden exclusions. The combination can still fail when resources are physically scarce, actions are capped or delayed, community coverage is incomplete, or audit attention follows false leads. These are hypotheses to compare in the tables, not presumed successful outcomes.

The fixed needs and household cohort are deliberate ethical constraints. Their presence does not establish that the chosen needs are sufficient, fair or complete in real life. The controller is a heuristic rather than an optimizer. All economic and institutional response laws are stipulated, and outsiders' legitimate claims beyond modeled accounts are not represented.

For background only, the [IMF's October 2017 Fiscal Monitor](https://www.imf.org/en/publications/fm/issues/2017/10/05/fiscal-monitor-october-2017) discusses progressive taxation and redistributive spending. The [OECD's 2022 citizen participation guidelines](https://www.oecd.org/en/publications/oecd-guidelines-for-citizen-participation-processes_f765caf6-en.html) describe participation design, inclusion, resources and evaluation. Neither source supplies the simulation's coefficients, estimates its outcomes, or validates its controller.

Maximum absolute accounting residual across all runs: cash 4.55e-13; goods 8.53e-14. Every saved trace is checked against the same cohort, fixed household floors and action/audit limits.

Python 3.14.3. Source hashes are checked before and after execution; they identify the implementation used and do not certify its correctness.

| Source | SHA-256 |
| --- | --- |
| alignment_community.py | e6bdd4848559522ea1666d31252408aff0c08cfbb857ea0e36a7e274b54a9fbf |
| experiment_alignment_community.py | 9c743765296e1baff3528cdd506f4d156af27e13c222f63c320105466dacce17 |
| test_alignment_community.py | 5081e0581749e8b676143c04d6a92bd0038850d730dc294b8a4a82261c329bdc |

