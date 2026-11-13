# Alignment depth: learning, access, and continuity

This is a synthetic mechanism experiment, not evidence that an AI is aligned or that the five-element ontology describes society. No people, animals, language models, or real schools were tested. Ethical priorities are inputs to the experiment.

## Question and design

Can information traffic, durable capability, access, and enjoyment come apart? When does withdrawing education break an explicitly required capability, and can a substitute preserve it?

Each comparison uses the same 20 seeds (0–19), with 40 rounds in the main experiment. There are eight agents and eight hidden modular rules. Rules map x to (a*x+b) mod 5. Learning uses only inputs 0, 1, 2; independent evaluation uses inputs 3 and 4. Policies select actions using uncertainty, never hidden evaluation answers.

Two agents initially know four topics, and an inherited school archive covers four topics. Every policy receives the same eight resource units per round and may save unspent units. A lesson or peer example costs one unit; a direct experiment costs two by default. The common inherited archive's historical acquisition cost is not charged: this tests operating choices given an endowment. The quality/cost sweep equalizes school coverage and the initial experts' knowledge to all eight topics for both policies. Reserve is an accounting balance, not an interest-bearing or spendable asset.

Ground is operationalized as correctly mastered rules per agent, checked against the hidden truth. Wrong confident beliefs do not count. Air is represented by communication and peer connectivity; Fire by paid discovery; Water by an abstract renewable work budget, not measured physical water; Void by unused budget. These are proposed mappings, not established equivalences. Enjoyment has its own additive metric and no assumed learning effect.

The contextual floor requires mastering topics 0 and 1 (or 0–3 in the continuity comparison). This strict threshold is chosen for the scenario, not derived as a moral law or a physiological survival condition. Forgetting resets a topic with the stated probability each round; matched worlds receive exactly the same forgetting events. Physical survival, ecological resource effects, consent, trust, and real wellbeing are not implemented.

## Equal-budget policies

Depth is the mean number of truly mastered topics, maximum eight. Accuracy is expected correctness on held-out inputs under each agent's candidate distribution. Failures count agents missing at least one required capability. Values below are seed means; full standard deviations, ranges, traces, and per-seed results are in the JSON.

| Policy | Depth | Held-out accuracy | Floor failures / 8 | Messages | Spent | Enjoyment |
|---|---:|---:|---:|---:|---:|---:|
| reserve | 0.63 | 26.3% | 7.35 | 0.0 | 0.0 | 0.0 |
| enjoy | 0.63 | 26.3% | 7.35 | 0.0 | 320.0 | 320.0 |
| repeat | 0.63 | 26.3% | 7.35 | 2560.0 | 320.0 | 0.0 |
| school | 4.00 | 60.0% | 0.00 | 73.5 | 73.5 | 0.0 |
| peer | 3.95 | 59.5% | 0.00 | 72.4 | 72.4 | 0.0 |
| discover | 8.00 | 100.0% | 0.00 | 144.3 | 288.6 | 0.0 |
| mixed | 8.00 | 100.0% | 0.00 | 150.8 | 220.1 | 0.0 |

The repeat policy broadcasts the same example to all eligible people for one unit per broadcast. Its large message count is an explicit stress test of a traffic metric, not a fair claim about teaching efficiency. Enjoyment and reserve have the same learning dynamics by construction; their difference is the separately valued enjoyment payoff. Neither comparison establishes the moral value of leisure.

## Access and support outage

The restricted classroom admits only the first four agents. The last four receive no lessons. Access is not inferred from country, wealth, identity, or worth.

| Learning access | Total mean depth | First four | Last four | Floor failures / 8 |
|---|---:|---:|---:|---:|
| open | 4.00 | 4.00 | 4.00 | 0.00 |
| restricted | 2.00 | 4.00 | 0.00 | 4.00 |

Separately, the same initial state is evaluated with a perfect external answering service, with restricted service access, and during an outage. The service covers archive topics. Assistance is counted as legitimate access; it does not become internal mastery. This is a controlled accounting demonstration with stipulated perfect service, not measured reliability.

| Service | Internal depth | Accessible depth | Unaided failures | Failures with support |
|---|---:|---:|---:|---:|
| all_access | 1.00 | 4.00 | 6.00 | 0.00 |
| half_access | 1.00 | 2.00 | 6.00 | 4.00 |
| outage | 1.00 | 1.00 | 6.00 | 6.00 |

## Continuity: withdraw schooling and offer substitutes

Each seed is trained for 25 school rounds, then cloned into four branches for another 25 rounds. This comparison restricts the world to four topics so every substitute targets the same scope as the school. Forgetting is 4% per agent/topic/round. All branches retain the same inherited knowledge, shocks, and offered operating budget. Figures measure the average number of agents failing during withdrawal, rather than only the final instant. A substitute is imperfect if it cannot maintain the required outcome.

| Branch | Mean failures: two required tasks | Mean failures: four required tasks | Extra spent |
|---|---:|---:|---:|
| continued_school | 0.00 | 0.01 | 64.0 |
| withdrawn_no_substitute | 4.50 | 6.28 | 0.0 |
| withdrawn_peer_substitute | 0.00 | 0.01 | 64.0 |
| withdrawn_discovery_substitute | 0.24 | 0.63 | 125.1 |

A withdrawal effect supports conditional dependence on a service under these demands and shocks. A working substitute weakens the claim that this particular institution is indispensable. Neither result alone determines what society ought to guarantee.

## Can teaching lose?

Both school and discovery can reach all eight topics here; forgetting is 2%. Teaching fidelity is the probability that a delivered label is correct. Direct discovery is assumed correct, and its resource cost is varied. These assumptions deliberately expose crossover conditions.

| Teaching fidelity | Discovery cost | School depth | Discovery depth | Paired difference: school minus discovery (mean ± SD) |
|---|---:|---:|---:|---:|
| 100% | 1 | 8.00 | 8.00 | +0.00 ± 0.00 |
| 100% | 2 | 8.00 | 7.41 | +0.59 ± 0.66 |
| 100% | 4 | 8.00 | 1.86 | +6.14 ± 0.69 |
| 70% | 1 | 4.44 | 8.00 | -3.56 ± 0.53 |
| 70% | 2 | 4.44 | 7.41 | -2.96 ± 0.83 |
| 70% | 4 | 4.44 | 1.86 | +2.59 ± 0.76 |
| 40% | 1 | 2.08 | 8.00 | -5.92 ± 0.38 |
| 40% | 2 | 2.08 | 7.41 | -5.33 ± 0.75 |
| 40% | 4 | 2.08 | 1.86 | +0.22 ± 0.77 |

## Peer connectivity

Mixed allocation uses the same rule and budget while the probability of a peer edge changes. Both final capability and resource cost matter: a saturated endpoint can conceal differences in efficiency. This tests this scheduler's response to connectivity, not an optimal allocation theorem.

| Peer edge probability | Mixed depth | Floor failures / 8 | Resources spent |
|---|---:|---:|---:|
| 0% | 8.00 | 0.00 | 248.2 |
| 50% | 8.00 | 0.00 | 220.3 |
| 100% | 8.00 | 0.00 | 220.1 |

## What the comparisons establish

- **Traffic and Ground are different quantities.** Repeating one example is a constructed counterexample to traffic as sufficient learning; held-out evaluation detects the difference.
- **Access must be measured per person.** Total capability conceals the excluded classroom group's lack of progress. This experiment stipulates the access barrier; it does not explain real-world exclusion.
- **Continuity concerns functions and substitutes.** Compare withdrawal with the peer and discovery branches before calling the school indispensable. All conclusions depend on the stated forgetting, costs, and task requirements.
- **Teaching is not guaranteed to beat discovery.** The quality/cost sweep allows lower-quality instruction to lose. The noisy learner can become confidently wrong, and cannot correct that belief until further contradictory evidence or forgetting makes it revisable.
- **Social connectivity need not increase the final depth in a saturated world.** Inspect costs as well as the endpoint. Costs are chosen model parameters.
- **Enjoyment remains separately valued.** Zero learning transfer is an assumption of this control, not evidence that real enjoyment lacks restorative or social effects.

## Limits and next empirical test

The experiment separates quantities that the earlier flow score conflated. It does not derive an ethical floor, prove that schooling is always best, validate literal Air/Fire/Ground physics, or test model obedience under adversarial incentives. The tasks are small and exactly realizable; teacher acquisition is inherited, costs and forgetting are chosen, and policies are heuristics, not optimized agents. Repeated seeds quantify this model's variation, not uncertainty about real societies.

A next empirical step is an agreed learning task with a delayed, unaided assessment and separately measured access, participant preferences, and resource costs. An alignment test would additionally give an optimizing agent an incentive to inflate the visible flow score while evaluating actual outcomes independently.

## Reproduce

```powershell
python -B -m unittest test_alignment_depth -v
python -B experiment_alignment_depth.py --seeds 20 --rounds 40
```

Python: 3.14.3. Full assumptions: `alignment_depth.py`. Raw data: `alignment_depth_results.json`. Source SHA-256 hashes are recorded in its metadata.
