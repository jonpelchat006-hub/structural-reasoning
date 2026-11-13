# Synthetic support and learning experiments

Reproduce: `python -B experiment_alignment_support.py --seeds 20 --weeks 16`

20 matched seeds, 16 weeks per run; 2320 runs across 6 experiment families. All full weekly traces, configurations, seed-level outcomes, descriptive statistics and paired differences are saved in `alignment_support_results.json`.

This report tests conditional consequences of explicit toy assumptions. It does not identify an objectively moral policy. No clinical or population data were used.

## Definitions and common limits

- This is a synthetic resource-and-learning world, not evidence that an objective establishes morality.
- Policies are heuristics; initial conditions, resource limits and seeds are identical within a comparison. External job-offer draws are matched; actual probabilities vary with skills and AI assistance.
- Policy names indicate priorities, not exclusive activities: education can work/search, employment can study, and all can rest.
- Water means closing cash >= 0; Ground means true mastery of every configured required topic.
- Negative cash is allowed as unpriced debt. A Water shortfall is flagged but does not itself block lessons, cause death, or force other stocks to decline.
- Air means social support >= its floor; Fire requires both attention and physical resources >= their floors.
- Fire is an explicit proxy for usable initiative/energy; recovery coefficients are not clinically validated.
- Void means free time >= the protected reserve. Every policy shares that constraint, so preserving Void is not a comparative policy finding.
- Enjoyment is a cumulative stipulated preference payoff with arbitrary ordering, not measured human welfare.
- A stipend and earned wages are alternative sources of the same cash resource; work has no intrinsic moral bonus.
- School supplies true training examples. Held-out task performance evaluates knowledge separately from message volume.
- More AI capacity cannot remove upstream teacher limits, human absorption limits, or the resource cost of upkeep.
- Jobs follow delayed uncertain applications. Delay 1 is the earliest next-week outcome; same-week search income is excluded.
- Job chance is the base rate: actual application probability is capped at 1 after multiplying by (1 + skill_job_bonus * confident topics) and (1 + ai_search_bonus * AI assistance).
- AI capacity is shared between examples and application assistance; upkeep is charged for provision even if capacity is unused.
- Knowledge area is the sum of end-of-week mastered-topic counts. It mixes earlier acquisition, retention, and final coverage.
- Statistics describe variation across simulated seeds, not a sampled human population or calibrated uncertainty about reality.
- Social, attention and physical states are coarse invented variables. Synthetic exercise/rest sensitivities are not medical advice or evidence.
- Study gives zero social support in the baseline. Separate school-social sensitivities add chosen support gains per study block; schools are not assumed universally supportive.

Default time: 12 blocks/week, with 2 protected. The same limit applies to every policy. Requirements, learning fidelity and budgets are held fixed inside each policy comparison. External offer draws are matched; actual probabilities depend on skills and AI use. Different profile endowments are not controlled interventions against each other.

Entries are mean ± sample SD across seeds; ranges are [minimum, maximum]. Every summarized numeric metric includes all three in the JSON. Shortfall counts are end-of-week counts, not the duration or severity of deprivation inside a week.

## Main comparisons

The original five profiles use eight topics. A pilot showed final mastery reaching that ceiling, so two 64-topic sensitivities were specified before their runs: long_funded and long_cash_limited. They supplement the original results and use the same seeds, horizon and policies. This is an exploratory response to an observed limitation, not independent confirmation. Knowledge area and action counts are reported for both curriculum sizes.

Every main run meets the two-topic Ground floor at every measured week end. This grid therefore does not distinguish policies by Ground-floor protection. Broader knowledge and acquisition timing still differ. The shared protected-time rule also makes Void preservation a common constraint rather than a comparative result.

### funded

Overrides: `{}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 | 15.00 ± 0.00 |
| balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |

| Policy | Final knowledge / 8 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 8.00 ± 0.00 [8.00, 8.00] | 54.03 ± 0.22 [53.08, 54.08] | 61.92 ± 0.64 [61.20, 63.60] | 8.00 ± 0.00 | 8.00 ± 0.00 | 0.98 ± 0.04 |
| employment | 8.00 ± 0.00 [8.00, 8.00] | 57.88 ± 0.89 [54.08, 58.08] | 56.11 ± 0.33 [55.70, 56.50] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |
| balanced | 8.00 ± 0.00 [8.00, 8.00] | 57.88 ± 0.89 [54.08, 58.08] | 65.83 ± 0.22 [65.00, 66.00] | 8.00 ± 0.00 | 7.96 ± 0.11 | 1.00 ± 0.00 |
| bottleneck | 8.00 ± 0.00 [8.00, 8.00] | 2.08 ± 0.00 [2.08, 2.08] | 47.95 ± 0.46 [47.40, 49.10] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 128.00 ± 0.00 | 9.25 ± 0.91 | 4.00 ± 0.00 | 51.95 ± 0.22 | 76.15 ± 0.49 | 0.00 ± 0.00 | 35.70 ± 0.98 |
| employment | 125.00 ± 0.00 | 10.25 ± 0.91 | 4.10 ± 0.45 | 55.80 ± 0.89 | 62.85 ± 0.37 | 0.00 ± 0.00 | 44.00 ± 0.92 |
| balanced | 121.95 ± 0.22 | 9.25 ± 0.91 | 4.10 ± 0.45 | 55.80 ± 0.89 | 58.70 ± 0.92 | 16.00 ± 0.00 | 32.15 ± 0.67 |
| bottleneck | 127.00 ± 0.00 | 9.25 ± 0.91 | 0.00 ± 0.00 | 0.00 ± 0.00 | 34.10 ± 0.31 | 16.00 ± 0.00 | 116.65 ± 1.09 |

### cash_limited

Overrides: `{"initial_cash": 3, "initial_skills": 4, "stipend": 0.2}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 1.50 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.50 ± 0.89 |
| employment | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.05 ± 0.22 | 0.00 ± 0.00 | 14.85 ± 0.49 |
| balanced | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.90 ± 0.45 |
| bottleneck | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.90 ± 0.45 |

| Policy | Final knowledge / 8 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 8.00 ± 0.00 [8.00, 8.00] | 27.18 ± 1.74 [24.28, 28.28] | 61.31 ± 0.77 [59.60, 62.50] | 8.00 ± 0.00 | 8.00 ± 0.00 | 0.98 ± 0.04 |
| employment | 8.00 ± 0.00 [8.00, 8.00] | 28.08 ± 0.89 [24.28, 28.28] | 55.90 ± 0.39 [55.00, 56.30] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |
| balanced | 8.00 ± 0.00 [8.00, 8.00] | 28.08 ± 0.89 [24.28, 28.28] | 64.73 ± 0.37 [63.80, 65.60] | 8.00 ± 0.00 | 7.96 ± 0.11 | 1.00 ± 0.00 |
| bottleneck | 8.00 ± 0.00 [8.00, 8.00] | 2.28 ± 0.00 [2.28, 2.28] | 58.40 ± 0.75 [57.40, 59.40] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 128.00 ± 0.00 | 5.35 ± 0.99 | 4.40 ± 0.82 | 54.90 ± 1.74 | 77.55 ± 0.94 | 0.00 ± 0.00 | 34.90 ± 1.89 |
| employment | 127.95 ± 0.22 | 7.35 ± 0.99 | 4.10 ± 0.45 | 55.80 ± 0.89 | 62.85 ± 0.37 | 0.00 ± 0.00 | 45.95 ± 1.10 |
| balanced | 125.90 ± 0.45 | 6.30 ± 0.92 | 4.10 ± 0.45 | 55.80 ± 0.89 | 58.85 ± 0.99 | 16.00 ± 0.00 | 34.95 ± 0.94 |
| bottleneck | 126.90 ± 0.45 | 7.30 ± 0.92 | 4.10 ± 0.45 | 30.00 ± 0.00 | 50.95 ± 0.83 | 16.00 ± 0.00 | 67.85 ± 1.63 |

### exhausted

Overrides: `{"initial_attention": 0.5, "initial_cash": 6, "initial_physical": 1, "initial_skills": 1, "stipend": 2.3}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 | 15.00 ± 0.00 |
| employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 ± 0.00 | 14.00 ± 0.00 |
| balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |

| Policy | Final knowledge / 8 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 8.00 ± 0.00 [8.00, 8.00] | 60.03 ± 2.08 [52.88, 60.88] | 62.49 ± 0.88 [59.90, 63.30] | 8.00 ± 0.00 | 8.00 ± 0.00 | 0.98 ± 0.04 |
| employment | 8.00 ± 0.00 [8.00, 8.00] | 64.48 ± 1.23 [60.88, 64.88] | 56.04 ± 0.35 [55.60, 56.60] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |
| balanced | 8.00 ± 0.00 [8.00, 8.00] | 62.83 ± 2.72 [56.88, 64.88] | 66.85 ± 0.28 [66.00, 67.10] | 8.00 ± 0.00 | 7.96 ± 0.11 | 1.00 ± 0.00 |
| bottleneck | 8.00 ± 0.00 [8.00, 8.00] | 8.88 ± 0.00 [8.88, 8.88] | 48.93 ± 0.45 [48.40, 50.10] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 125.00 ± 0.00 | 10.25 ± 0.91 | 3.40 ± 1.05 | 51.15 ± 2.08 | 78.65 ± 1.04 | 0.00 ± 0.00 | 34.60 ± 2.06 |
| employment | 121.95 ± 0.22 | 11.25 ± 0.91 | 4.20 ± 0.62 | 55.60 ± 1.23 | 63.75 ± 0.55 | 0.00 ± 0.00 | 43.10 ± 0.79 |
| balanced | 119.95 ± 0.22 | 9.25 ± 0.91 | 4.00 ± 1.38 | 53.95 ± 2.72 | 59.10 ± 1.07 | 16.00 ± 0.00 | 32.70 ± 1.22 |
| bottleneck | 123.00 ± 0.00 | 9.20 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 36.10 ± 0.31 | 16.00 ± 0.00 | 114.70 ± 1.08 |

### isolated

Overrides: `{"initial_cash": 6, "initial_skills": 4, "initial_social": 0.1, "stipend": 2.3}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 15.00 ± 0.00 |
| employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.05 ± 0.22 | 0.05 ± 0.22 | 0.00 ± 0.00 | 14.95 ± 0.22 |
| balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 15.00 ± 0.00 |
| bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |

| Policy | Final knowledge / 8 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 8.00 ± 0.00 [8.00, 8.00] | 63.78 ± 1.74 [60.88, 64.88] | 62.73 ± 0.72 [61.10, 63.70] | 8.00 ± 0.00 | 8.00 ± 0.00 | 0.98 ± 0.04 |
| employment | 8.00 ± 0.00 [8.00, 8.00] | 64.68 ± 0.89 [60.88, 64.88] | 56.95 ± 0.42 [56.00, 57.70] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |
| balanced | 8.00 ± 0.00 [8.00, 8.00] | 64.68 ± 0.89 [60.88, 64.88] | 67.13 ± 0.21 [66.30, 67.30] | 8.00 ± 0.00 | 7.96 ± 0.11 | 1.00 ± 0.00 |
| bottleneck | 8.00 ± 0.00 [8.00, 8.00] | 8.88 ± 0.00 [8.88, 8.88] | 47.89 ± 0.48 [47.30, 49.00] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 128.00 ± 0.00 | 5.35 ± 0.99 | 4.40 ± 0.82 | 54.90 ± 1.74 | 78.50 ± 0.89 | 0.00 ± 0.00 | 33.00 ± 1.78 |
| employment | 127.95 ± 0.22 | 7.35 ± 0.99 | 4.10 ± 0.45 | 55.80 ± 0.89 | 62.85 ± 0.37 | 0.00 ± 0.00 | 44.90 ± 1.17 |
| balanced | 125.90 ± 0.45 | 6.30 ± 0.92 | 4.10 ± 0.45 | 55.80 ± 0.89 | 59.65 ± 0.93 | 16.00 ± 0.00 | 32.15 ± 0.67 |
| bottleneck | 128.00 ± 0.00 | 5.35 ± 0.99 | 0.00 ± 0.00 | 0.00 ± 0.00 | 33.10 ± 0.45 | 16.00 ± 0.00 | 119.55 ± 1.15 |

### learning_limited

Overrides: `{"initial_cash": 6, "initial_skills": 0, "stipend": 2.3}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 | 0.00 ± 0.00 | 14.00 ± 0.00 |
| balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |

| Policy | Final knowledge / 8 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 8.00 ± 0.00 [8.00, 8.00] | 60.83 ± 0.22 [59.88, 60.88] | 62.17 ± 0.49 [61.50, 63.00] | 8.00 ± 0.00 | 8.00 ± 0.00 | 0.98 ± 0.04 |
| employment | 8.00 ± 0.00 [8.00, 8.00] | 64.08 ± 2.09 [56.88, 64.88] | 55.82 ± 0.34 [55.40, 56.40] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |
| balanced | 8.00 ± 0.00 [8.00, 8.00] | 64.53 ± 0.99 [60.88, 64.88] | 65.75 ± 0.17 [65.60, 66.30] | 8.00 ± 0.00 | 7.96 ± 0.11 | 1.00 ± 0.00 |
| bottleneck | 8.00 ± 0.00 [8.00, 8.00] | 8.88 ± 0.00 [8.88, 8.88] | 48.73 ± 0.45 [48.20, 49.90] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 124.00 ± 0.00 | 11.25 ± 0.91 | 4.00 ± 0.00 | 51.95 ± 0.22 | 77.05 ± 0.39 | 0.00 ± 0.00 | 33.80 ± 0.62 |
| employment | 121.95 ± 0.22 | 13.25 ± 0.91 | 4.40 ± 1.05 | 55.20 ± 2.09 | 61.70 ± 0.57 | 0.00 ± 0.00 | 43.30 ± 0.98 |
| balanced | 118.00 ± 0.00 | 11.20 ± 0.89 | 4.10 ± 0.45 | 55.65 ± 0.99 | 57.00 ± 0.79 | 16.00 ± 0.00 | 32.05 ± 0.22 |
| bottleneck | 123.00 ± 0.00 | 11.20 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 34.10 ± 0.31 | 16.00 ± 0.00 | 114.70 ± 1.08 |

### long_funded

Overrides: `{"initial_cash": 6, "initial_skills": 0, "n_topics": 64, "stipend": 2.3}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 0.00 ± 0.00 | 10.35 ± 1.14 | 8.85 ± 0.37 | 0.00 ± 0.00 | 4.65 ± 1.14 |
| employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 13.00 ± 0.00 | 14.05 ± 0.22 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |
| bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 16.00 ± 0.00 |

| Policy | Final knowledge / 64 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 64.00 ± 0.00 [64.00, 64.00] | 15.58 ± 1.66 [12.88, 16.88] | 68.04 ± 0.88 [66.30, 69.90] | 7.97 ± 0.13 | 7.96 ± 0.18 | 0.71 ± 0.30 |
| employment | 39.65 ± 2.98 [36.00, 47.00] | 64.08 ± 2.09 [56.88, 64.88] | 49.69 ± 0.23 [49.60, 50.50] | 1.08 ± 0.37 | 7.85 ± 0.15 | 0.00 ± 0.00 |
| balanced | 51.05 ± 3.20 [46.00, 59.00] | 36.78 ± 0.45 [34.88, 36.88] | 71.59 ± 0.04 [71.40, 71.60] | 5.40 ± 0.00 | 7.50 ± 0.00 | 1.00 ± 0.00 |
| bottleneck | 64.00 ± 0.00 [64.00, 64.00] | 8.88 ± 0.00 [8.88, 8.88] | 72.79 ± 0.90 [70.60, 74.50] | 8.00 ± 0.00 | 8.00 ± 0.00 | 1.00 ± 0.00 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 485.75 ± 12.82 | 88.25 ± 2.05 | 3.65 ± 0.49 | 6.70 ± 1.66 | 57.05 ± 1.05 | 0.00 ± 0.00 | 32.80 ± 1.36 |
| employment | 172.35 ± 14.11 | 60.35 ± 0.88 | 4.40 ± 1.05 | 55.20 ± 2.09 | 40.05 ± 0.22 | 0.00 ± 0.00 | 32.00 ± 0.00 |
| balanced | 230.30 ± 16.29 | 64.00 ± 0.00 | 4.10 ± 0.45 | 27.90 ± 0.45 | 32.00 ± 0.00 | 16.00 ± 0.00 | 32.00 ± 0.00 |
| bottleneck | 458.45 ± 13.32 | 85.80 ± 1.94 | 0.00 ± 0.00 | 0.00 ± 0.00 | 36.65 ± 1.04 | 16.00 ± 0.00 | 44.60 ± 2.16 |

### long_cash_limited

Overrides: `{"initial_cash": 3, "initial_skills": 4, "n_topics": 64, "stipend": 0.2}`

| Policy | Water weeks | Ground weeks | Air weeks | Fire weeks | Void weeks | Viable weeks |
| --- | --- | --- | --- | --- | --- | --- |
| education | 15.00 ± 0.00 | 0.00 ± 0.00 | 9.40 ± 0.60 | 8.10 ± 0.31 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| employment | 1.10 ± 0.45 | 0.00 ± 0.00 | 13.00 ± 0.00 | 14.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| balanced | 11.20 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 4.80 ± 0.89 |
| bottleneck | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.90 ± 0.45 |

| Policy | Final knowledge / 64 [range] | Final cash [range] | Enjoyment [range] | Final attention | Final physical | Final social |
| --- | --- | --- | --- | --- | --- | --- |
| education | 64.00 ± 0.00 [64.00, 64.00] | -18.37 ± 1.93 [-20.72, -15.72] | 67.78 ± 0.90 [66.30, 69.40] | 7.97 ± 0.13 | 7.96 ± 0.18 | 0.77 ± 0.22 |
| employment | 46.50 ± 3.19 [42.00, 55.00] | 28.08 ± 0.89 [24.28, 28.28] | 49.62 ± 0.09 [49.60, 50.00] | 1.14 ± 0.27 | 7.88 ± 0.11 | 0.00 ± 0.00 |
| balanced | 57.80 ± 3.00 [54.00, 64.00] | 0.23 ± 0.51 [-1.72, 1.28] | 71.58 ± 0.08 [71.30, 71.60] | 5.42 ± 0.09 | 7.47 ± 0.16 | 1.00 ± 0.00 |
| bottleneck | 63.85 ± 0.67 [61.00, 64.00] | 2.28 ± 0.00 [2.28, 2.28] | 65.04 ± 0.52 [63.90, 66.10] | 6.19 ± 1.83 | 7.85 ± 0.21 | 0.79 ± 0.15 |

Knowledge area and time use reveal differences concealed by a saturated final endpoint.

| Policy | Knowledge area | Study blocks | Search blocks | Work blocks | Rest blocks | Exercise blocks | Unallocated time blocks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| education | 540.75 ± 11.29 | 83.75 ± 2.07 | 3.85 ± 0.37 | 9.35 ± 1.93 | 58.40 ± 0.82 | 0.00 ± 0.00 | 32.50 ± 1.10 |
| employment | 239.70 ± 17.85 | 60.10 ± 0.45 | 4.10 ± 0.45 | 55.80 ± 0.89 | 40.00 ± 0.00 | 0.00 ± 0.00 | 32.00 ± 0.00 |
| balanced | 300.75 ± 17.77 | 63.95 ± 0.22 | 4.10 ± 0.45 | 27.95 ± 0.51 | 32.00 ± 0.00 | 16.00 ± 0.00 | 32.00 ± 0.00 |
| bottleneck | 350.70 ± 17.35 | 73.05 ± 1.70 | 4.10 ± 0.45 | 30.00 ± 0.00 | 30.25 ± 0.91 | 16.00 ± 0.00 | 32.10 ± 0.31 |

## Delayed, uncertain employment

Cash-limited profile; job chance and delay are varied together over the complete 3 × 3 grid. The shortest delay is one week. Job chance is a base rate, not the final application success probability: with default coefficients, confidence multiplies it by (1 + 0.05 × confident topics), and AI assistance by 1.5, with a ceiling of 1. These arbitrary bonuses are identical across policies. Search does not itself pay wages; reported income includes transfers. Final cash and shortfall weeks can differ even with similar eventual employment.

| Job chance / delay | Policy | Water weeks | Ground weeks | Final cash | Final job fraction |
| --- | --- | --- | --- | --- | --- |
| chance=0.1, delay=1 | education | 1.95 ± 1.76 | 0.00 ± 0.00 | 26.78 ± 4.14 | 1.00 ± 0.00 |
| chance=0.1, delay=1 | employment | 1.85 ± 1.84 | 0.00 ± 0.00 | 27.28 ± 4.47 | 1.00 ± 0.00 |
| chance=0.1, delay=1 | bottleneck | 2.40 ± 2.91 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.1, delay=2 | education | 3.70 ± 2.08 | 0.00 ± 0.00 | 22.83 ± 4.15 | 1.00 ± 0.00 |
| chance=0.1, delay=2 | employment | 3.50 ± 2.24 | 0.00 ± 0.00 | 23.28 ± 4.47 | 1.00 ± 0.00 |
| chance=0.1, delay=2 | bottleneck | 4.05 ± 3.24 | 0.00 ± 0.00 | 2.18 ± 0.45 | 1.00 ± 0.00 |
| chance=0.1, delay=5 | education | 9.55 ± 1.85 | 0.00 ± 0.00 | 10.83 ± 4.15 | 1.00 ± 0.00 |
| chance=0.1, delay=5 | employment | 9.35 ± 2.01 | 0.00 ± 0.00 | 11.28 ± 4.47 | 1.00 ± 0.00 |
| chance=0.1, delay=5 | bottleneck | 9.65 ± 2.37 | 0.00 ± 0.00 | 1.58 ± 3.13 | 1.00 ± 0.00 |
| chance=0.35, delay=1 | education | 0.25 ± 0.44 | 0.00 ± 0.00 | 31.18 ± 1.74 | 1.00 ± 0.00 |
| chance=0.35, delay=1 | employment | 0.05 ± 0.22 | 0.00 ± 0.00 | 32.08 ± 0.89 | 1.00 ± 0.00 |
| chance=0.35, delay=1 | bottleneck | 0.05 ± 0.22 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.35, delay=2 | education | 1.50 ± 0.89 | 0.00 ± 0.00 | 27.18 ± 1.74 | 1.00 ± 0.00 |
| chance=0.35, delay=2 | employment | 1.10 ± 0.45 | 0.00 ± 0.00 | 28.08 ± 0.89 | 1.00 ± 0.00 |
| chance=0.35, delay=2 | bottleneck | 1.10 ± 0.45 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.35, delay=5 | education | 7.50 ± 0.89 | 0.00 ± 0.00 | 15.23 ± 1.76 | 1.00 ± 0.00 |
| chance=0.35, delay=5 | employment | 7.10 ± 0.45 | 0.00 ± 0.00 | 16.08 ± 0.89 | 1.00 ± 0.00 |
| chance=0.35, delay=5 | bottleneck | 7.10 ± 0.45 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=1 | education | 0.05 ± 0.22 | 0.00 ± 0.00 | 31.98 ± 0.92 | 1.00 ± 0.00 |
| chance=0.8, delay=1 | employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 32.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=1 | bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=2 | education | 1.10 ± 0.45 | 0.00 ± 0.00 | 27.98 ± 0.92 | 1.00 ± 0.00 |
| chance=0.8, delay=2 | employment | 1.00 ± 0.00 | 0.00 ± 0.00 | 28.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=2 | bottleneck | 1.00 ± 0.00 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=5 | education | 7.10 ± 0.45 | 0.00 ± 0.00 | 16.03 ± 0.91 | 1.00 ± 0.00 |
| chance=0.8, delay=5 | employment | 7.00 ± 0.00 | 0.00 ± 0.00 | 16.28 ± 0.00 | 1.00 ± 0.00 |
| chance=0.8, delay=5 | bottleneck | 7.00 ± 0.00 | 0.00 ± 0.00 | 2.28 ± 0.00 | 1.00 ± 0.00 |

## AI capacity, teaching supply and human absorption

Learning-limited profile; education policy throughout. This is the complete 4 × 2 × 2 × 2 grid: AI capacity 0/2/8/16, human cap 1/2, teacher supply 2/12, and upkeep per unit 0/0.1. Changing AI capacity also changes upkeep when its unit price is positive; the zero-upkeep rows separate this financial channel. An AI-capacity result is conditional on both teaching and absorption caps.

| AI / human / teacher / upkeep | Knowledge area | Final knowledge | AI cost | Messages | Water weeks | Ground weeks | Fire weeks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AI=0, human=1, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=0, human=1, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=0, human=1, teacher=12, upkeep=0 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=0, human=1, teacher=12, upkeep=0.1 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=0, human=2, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=0, human=2, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=0, human=2, teacher=12, upkeep=0 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=0, human=2, teacher=12, upkeep=0.1 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=2, human=1, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=2, human=1, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 3.20 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=2, human=1, teacher=12, upkeep=0 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=2, human=1, teacher=12, upkeep=0.1 | 121.95 ± 0.22 | 8.00 ± 0.00 | 3.20 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=2, human=2, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=2, human=2, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 3.20 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=2, human=2, teacher=12, upkeep=0 | 123.00 ± 0.00 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| AI=2, human=2, teacher=12, upkeep=0.1 | 123.00 ± 0.00 | 8.00 ± 0.00 | 3.20 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| AI=8, human=1, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=8, human=1, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 12.80 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=8, human=1, teacher=12, upkeep=0 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=8, human=1, teacher=12, upkeep=0.1 | 121.95 ± 0.22 | 8.00 ± 0.00 | 12.80 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=8, human=2, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=8, human=2, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 12.80 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=8, human=2, teacher=12, upkeep=0 | 124.00 ± 0.00 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| AI=8, human=2, teacher=12, upkeep=0.1 | 124.00 ± 0.00 | 8.00 ± 0.00 | 12.80 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=1, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=1, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 25.60 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=1, teacher=12, upkeep=0 | 121.95 ± 0.22 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=16, human=1, teacher=12, upkeep=0.1 | 121.95 ± 0.22 | 8.00 ± 0.00 | 25.60 ± 0.00 | 18.45 ± 1.79 | 0.15 ± 0.37 | 0.00 ± 0.00 | 2.00 ± 0.00 |
| AI=16, human=2, teacher=2, upkeep=0 | 88.80 ± 2.46 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=2, teacher=2, upkeep=0.1 | 88.80 ± 2.46 | 8.00 ± 0.00 | 25.60 ± 0.00 | 18.15 ± 1.53 | 0.00 ± 0.00 | 1.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=2, teacher=12, upkeep=0 | 124.00 ± 0.00 | 8.00 ± 0.00 | 0.00 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| AI=16, human=2, teacher=12, upkeep=0.1 | 124.00 ± 0.00 | 8.00 ± 0.00 | 25.60 ± 0.00 | 18.45 ± 1.79 | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |

## Synthetic recovery sensitivity

Exhausted profile. Only the invented exercise-recovery coefficient changes. Exercise counts are shown to establish whether the intervention is actually used; all other behavior remains policy-dependent. These numbers are not evidence about exercise efficacy, illness, disability, or what a person should do.

| Exercise recovery | Policy | Exercise blocks | Rest blocks | Fire weeks | Ground weeks | Final attention | Final physical | Enjoyment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exercise_recovery=0 | education | 0.00 ± 0.00 | 78.65 ± 1.04 | 1.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 62.49 ± 0.88 |
| exercise_recovery=0 | balanced | 16.00 ± 0.00 | 59.50 ± 1.43 | 1.15 ± 0.37 | 0.00 ± 0.00 | 8.00 ± 0.00 | 7.96 ± 0.11 | 67.05 ± 0.34 |
| exercise_recovery=0 | bottleneck | 0.00 ± 0.00 | 25.20 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 32.25 ± 0.82 |
| exercise_recovery=1.5 | education | 0.00 ± 0.00 | 78.65 ± 1.04 | 1.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 62.49 ± 0.88 |
| exercise_recovery=1.5 | balanced | 16.00 ± 0.00 | 59.10 ± 1.07 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 7.96 ± 0.11 | 66.85 ± 0.28 |
| exercise_recovery=1.5 | bottleneck | 16.00 ± 0.00 | 36.10 ± 0.31 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 48.93 ± 0.45 |
| exercise_recovery=3 | education | 0.00 ± 0.00 | 78.65 ± 1.04 | 1.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 62.49 ± 0.88 |
| exercise_recovery=3 | balanced | 16.00 ± 0.00 | 58.30 ± 0.92 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 7.96 ± 0.11 | 66.45 ± 0.62 |
| exercise_recovery=3 | bottleneck | 16.00 ± 0.00 | 36.10 ± 0.31 | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.00 ± 0.00 | 8.00 ± 0.00 | 48.93 ± 0.45 |

## Transfer as another source of Water

This changes only the cash-limited profile's stipend from 0.2 to 2.3. Its initial cash and skills remain 3 and 4. The same seed and policy are paired. This tests income availability, not whether employment or receiving support has greater intrinsic worth.

| Policy | Higher-transfer Water weeks | Final cash | Final knowledge | Enjoyment |
| --- | --- | --- | --- | --- |
| education | 0.00 ± 0.00 | 60.78 ± 1.74 | 8.00 ± 0.00 | 61.31 ± 0.77 |
| employment | 0.00 ± 0.00 | 61.68 ± 0.89 | 8.00 ± 0.00 | 55.90 ± 0.39 |
| balanced | 0.00 ± 0.00 | 61.68 ± 0.89 | 8.00 ± 0.00 | 64.73 ± 0.37 |
| bottleneck | 0.00 ± 0.00 | 5.88 ± 0.00 | 8.00 ± 0.00 | 46.39 ± 0.48 |

Paired changes below mean higher stipend minus lower stipend; negative shortfall changes indicate fewer failures.

| Policy | Change Water weeks [range] | Change Ground weeks [range] | Change cash [range] | Change enjoyment [range] |
| --- | --- | --- | --- | --- |
| education | -1.50 ± 0.89 [-3.00, -1.00] | 0.00 ± 0.00 [0.00, 0.00] | 33.60 ± 0.00 [33.60, 33.60] | 0.00 ± 0.00 [0.00, 0.00] |
| employment | -1.10 ± 0.45 [-3.00, -1.00] | 0.00 ± 0.00 [0.00, 0.00] | 33.60 ± 0.00 [33.60, 33.60] | 0.00 ± 0.00 [0.00, 0.00] |
| balanced | -1.10 ± 0.45 [-3.00, -1.00] | 0.00 ± 0.00 [0.00, 0.00] | 33.60 ± 0.00 [33.60, 33.60] | 0.00 ± 0.00 [0.00, 0.00] |
| bottleneck | -1.10 ± 0.45 [-3.00, -1.00] | 0.00 ± 0.00 [0.00, 0.00] | 3.60 ± 0.00 [3.60, 3.60] | -12.01 ± 0.76 [-12.80, -10.30] |

## School as a possible source of Air

The baseline assigns no social gain to study. That choice can make long education schedules appear socially costly by construction. This sensitivity adds 0.03 or 0.12 social stock per completed study block, capped at 1, and retains the baseline as the control. It crosses both 64-topic profiles with all four policies. Gains are chosen inputs, not estimates of school effects: schools can provide relationships and support, but are not universally supportive. This extension was specified after identifying the missing pathway in the baseline.

| Profile / gain | Policy | Water weeks | Air weeks | Fire weeks | Final knowledge | Knowledge area | Final cash | Enjoyment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| long_funded, study social gain=0.03 | education | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.85 ± 0.37 | 64.00 ± 0.00 | 485.75 ± 12.82 | 15.58 ± 1.66 | 66.02 ± 0.77 |
| long_funded, study social gain=0.03 | employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.05 ± 0.22 | 39.65 ± 2.98 | 172.35 ± 14.11 | 64.08 ± 2.09 | 49.69 ± 0.23 |
| long_funded, study social gain=0.03 | balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 51.05 ± 3.20 | 230.30 ± 16.29 | 36.78 ± 0.45 | 71.59 ± 0.04 |
| long_funded, study social gain=0.03 | bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 64.00 ± 0.00 | 472.60 ± 13.23 | 8.88 ± 0.00 | 68.09 ± 0.95 |
| long_funded, study social gain=0.12 | education | 0.00 ± 0.00 | 0.00 ± 0.00 | 8.85 ± 0.37 | 64.00 ± 0.00 | 485.75 ± 12.82 | 15.58 ± 1.66 | 64.89 ± 0.83 |
| long_funded, study social gain=0.12 | employment | 0.00 ± 0.00 | 0.00 ± 0.00 | 14.05 ± 0.22 | 39.65 ± 2.98 | 172.35 ± 14.11 | 64.08 ± 2.09 | 49.69 ± 0.23 |
| long_funded, study social gain=0.12 | balanced | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 63.50 ± 0.83 | 322.40 ± 15.76 | 37.83 ± 1.15 | 62.33 ± 0.23 |
| long_funded, study social gain=0.12 | bottleneck | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 | 64.00 ± 0.00 | 472.60 ± 13.23 | 8.88 ± 0.00 | 64.86 ± 1.10 |
| long_cash_limited, study social gain=0.03 | education | 15.00 ± 0.00 | 0.00 ± 0.00 | 8.10 ± 0.31 | 64.00 ± 0.00 | 540.75 ± 11.29 | -18.37 ± 1.93 | 65.61 ± 0.89 |
| long_cash_limited, study social gain=0.03 | employment | 1.10 ± 0.45 | 0.00 ± 0.00 | 14.00 ± 0.00 | 46.50 ± 3.19 | 239.70 ± 17.85 | 28.08 ± 0.89 | 49.62 ± 0.09 |
| long_cash_limited, study social gain=0.03 | balanced | 11.20 ± 0.89 | 0.00 ± 0.00 | 0.00 ± 0.00 | 57.80 ± 3.00 | 300.75 ± 17.77 | 0.23 ± 0.51 | 71.58 ± 0.08 |
| long_cash_limited, study social gain=0.03 | bottleneck | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 64.00 ± 0.00 | 377.75 ± 16.03 | 2.28 ± 0.00 | 61.65 ± 0.50 |
| long_cash_limited, study social gain=0.12 | education | 15.00 ± 0.00 | 0.00 ± 0.00 | 8.10 ± 0.31 | 64.00 ± 0.00 | 540.75 ± 11.29 | -18.37 ± 1.93 | 64.18 ± 0.65 |
| long_cash_limited, study social gain=0.12 | employment | 1.10 ± 0.45 | 0.00 ± 0.00 | 14.00 ± 0.00 | 46.50 ± 3.19 | 239.70 ± 17.85 | 28.08 ± 0.89 | 49.62 ± 0.09 |
| long_cash_limited, study social gain=0.12 | balanced | 11.15 ± 0.67 | 0.00 ± 0.00 | 0.00 ± 0.00 | 64.00 ± 0.00 | 391.45 ± 13.23 | 3.03 ± 0.91 | 62.09 ± 0.38 |
| long_cash_limited, study social gain=0.12 | bottleneck | 1.10 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 | 64.00 ± 0.00 | 377.75 ± 16.03 | 2.28 ± 0.00 | 60.55 ± 0.41 |

Paired changes mean positive study-social gain minus zero gain, with profile, policy and seed held fixed.

| Profile | Gain | Policy | Change Air weeks [range] | Change Fire weeks [range] | Change knowledge area [range] | Change cash [range] |
| --- | --- | --- | --- | --- | --- | --- |
| long_funded | 0.03 | education | -10.35 ± 1.14 [-13.00, -9.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.03 | employment | -13.00 ± 0.00 [-13.00, -13.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.03 | balanced | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.03 | bottleneck | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 14.15 ± 1.90 [10.00, 18.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.12 | education | -10.35 ± 1.14 [-13.00, -9.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.12 | employment | -13.00 ± 0.00 [-13.00, -13.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_funded | 0.12 | balanced | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 92.10 ± 5.42 [81.00, 101.00] | 1.05 ± 0.94 [0.00, 3.00] |
| long_funded | 0.12 | bottleneck | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 14.15 ± 1.90 [10.00, 18.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.03 | education | -9.40 ± 0.60 [-11.00, -9.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.03 | employment | -13.00 ± 0.00 [-13.00, -13.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.03 | balanced | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.03 | bottleneck | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 27.05 ± 4.07 [19.00, 31.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.12 | education | -9.40 ± 0.60 [-11.00, -9.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.12 | employment | -13.00 ± 0.00 [-13.00, -13.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] |
| long_cash_limited | 0.12 | balanced | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 90.70 ± 6.97 [78.00, 102.00] | 2.80 ± 0.77 [2.00, 4.00] |
| long_cash_limited | 0.12 | bottleneck | 0.00 ± 0.00 [0.00, 0.00] | 0.00 ± 0.00 [0.00, 0.00] | 27.05 ± 4.07 [19.00, 31.00] | 0.00 ± 0.00 [0.00, 0.00] |

## Interpretation limits and provenance

The floors and state-to-function mapping are chosen definitions. A heuristic's performance here does not validate those definitions, establish human preferences, or show that an AI system is aligned. The simulation excludes many real constraints, including varied household costs, discrimination, care responsibilities, clinical health, social reciprocity and heterogeneous learning needs. Changing a recovery coefficient is sensitivity analysis of invented mechanics, not an empirical finding.

Void preservation follows from a shared protected-time rule. Monetary solvency is an end-of-week cash condition. Neither alone measures freedom, wellbeing or safety. Compare separate outcomes before interpreting the composite viable count.

The full specified grids were used, with next-week delay 1 replacing unsupported delay 0. All policies use matched external offer draws and the same initial endowment within each comparison; actual success probabilities depend on acquired skills and AI assistance. No policy is tuned against held-out performance during this run. Descriptive seed variation is not a real-world confidence interval.

Python: 3.14.3. Source hashes identify the exact files used; hashes do not certify correctness.

| Source | SHA-256 |
| --- | --- |
| alignment_support.py | d635e671ecb22650b6e3c7bd7acf0b7e7b1b424b5e77798e1b7cbc7d268e727c |
| experiment_alignment_support.py | 3ad6f8804f65d052289cee888b759bcdbc2b8daaa437b2dc3050511a6754d08c |
| test_alignment_support.py | 2169e36b75dec9054a76b3fb6349b22f4c0e081347d5b14186eee3a93a338c5a |
| alignment_depth.py | 4f0d26f137fb9d367f1193ced13f5088d64dfc09b2260bdf1d2f4f69b610c1f5 |

