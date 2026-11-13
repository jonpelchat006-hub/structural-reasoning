"""Reproducible, deliberately synthetic tests of accessible depth and continuity.

Run: python -B experiment_alignment_depth.py --seeds 20 --rounds 40
Uses only the standard library. Does not invoke models, networks, or real users.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
from dataclasses import asdict
from pathlib import Path

from alignment_depth import Config, World

POLICIES = ("reserve", "enjoy", "repeat", "school", "peer", "discover", "mixed")
SCALARS = ("depth_mean", "depth_min", "accuracy", "confidence_mean", "floor_failures",
           "messages", "spent", "reserve", "enjoyment", "discoveries", "contradictions")


def summary(values):
    values = list(values)
    return {"mean": statistics.fmean(values),
            "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values), "n": len(values)}


def aggregate(rows):
    rows = list(rows)
    return {key: summary(row[key] for row in rows) for key in SCALARS}


def advance(world, policy, rounds, access=None):
    trace = []
    for _ in range(rounds):
        world.step(policy, access=access)
        trace.append(world.metrics())
    return trace


def policy_comparison(seeds, rounds):
    out = {}
    for policy in POLICIES:
        runs = []
        for seed in seeds:
            w = World(Config(seed=seed))
            trace = advance(w, policy, rounds)
            runs.append({"seed": seed, "final": trace[-1],
                         "depth_trace": [r["depth_mean"] for r in trace],
                         "failure_trace": [r["floor_failures"] for r in trace]})
        out[policy] = {"summary": aggregate(r["final"] for r in runs), "runs": runs}
    return out


def access_comparison(seeds, rounds):
    out = {}
    for label, access in (("open", [True] * 8), ("restricted", [True] * 4 + [False] * 4)):
        runs = []
        for seed in seeds:
            w = World(Config(seed=seed))
            advance(w, "school", rounds, access)
            m = w.metrics()
            runs.append({"seed": seed, "final": m,
                         "first_four_depth": statistics.fmean(m["depth_by_agent"][:4]),
                         "last_four_depth": statistics.fmean(m["depth_by_agent"][4:])})
        out[label] = {"summary": aggregate(r["final"] for r in runs),
                      "first_four_depth": summary(r["first_four_depth"] for r in runs),
                      "last_four_depth": summary(r["last_four_depth"] for r in runs),
                      "runs": runs}
    return out


def service_outage(seeds):
    out = {}
    for label, access in (("all_access", [True] * 8),
                          ("half_access", [True] * 4 + [False] * 4),
                          ("outage", [False] * 8)):
        rows = [World(Config(seed=s)).metrics(service_access=access) for s in seeds]
        out[label] = {key: summary(r[key] for r in rows) for key in
                      ("depth_mean", "accessible_depth_mean", "floor_failures",
                       "effective_floor_failures")}
    return out


def continuity_comparison(seeds):
    """Same learned start, external demands, matched shocks, equal offered budgets."""
    labels = {"continued_school": "school", "withdrawn_no_substitute": "reserve",
              "withdrawn_peer_substitute": "peer", "withdrawn_discovery_substitute": "discover"}
    out = {label: [] for label in labels}
    for seed in seeds:
        # Every substitute can target the same four topics as the school.
        # Otherwise a broad exploration heuristic spends on out-of-scope tasks.
        base = World(Config(seed=seed, n_topics=4, school_topics=4, forgetting=0.04))
        advance(base, "school", 25)
        for label, policy in labels.items():
            w = base.clone()
            failures = {"two_tasks": [], "four_tasks": []}
            start = w.metrics()
            for _ in range(25):
                w.step(policy)
                failures["two_tasks"].append(w.metrics(required_topics=(0, 1))["floor_failures"])
                failures["four_tasks"].append(w.metrics(required_topics=(0, 1, 2, 3))["floor_failures"])
            out[label].append({"seed": seed, "start": start, "final": w.metrics(),
                               "extra_spent": w.metrics()["spent"] - start["spent"],
                               "mean_two_task_failures": statistics.fmean(failures["two_tasks"]),
                               "mean_four_task_failures": statistics.fmean(failures["four_tasks"]),
                               "failure_traces": failures})
    return {label: {"summary": aggregate(r["final"] for r in rows),
                    "mean_two_task_failures": summary(r["mean_two_task_failures"] for r in rows),
                    "mean_four_task_failures": summary(r["mean_four_task_failures"] for r in rows),
                    "extra_spent": summary(r["extra_spent"] for r in rows), "runs": rows}
            for label, rows in out.items()}


def reliability_sweep(seeds, rounds):
    """Equal topic coverage; expose how assumed quality and acquisition cost change results."""
    out = []
    for fidelity in (1.0, 0.7, 0.4):
        for cost in (1.0, 2.0, 4.0):
            rows = {"school": [], "discover": []}
            for seed in seeds:
                for policy in rows:
                    w = World(Config(seed=seed, school_topics=8, teach_fidelity=fidelity,
                                     discovery_cost=cost, forgetting=0.02))
                    advance(w, policy, rounds)
                    rows[policy].append(w.metrics())
            paired = [a["depth_mean"] - b["depth_mean"]
                      for a, b in zip(rows["school"], rows["discover"])]
            out.append({"teaching_fidelity": fidelity, "discovery_cost": cost,
                        "school": aggregate(rows["school"]),
                        "discover": aggregate(rows["discover"]),
                        "school_minus_discovery": summary(paired),
                        "per_seed": [{"seed": seed, "school": a, "discover": b}
                                     for seed, a, b in zip(seeds, rows["school"], rows["discover"])]})
    return out


def peer_sweep(seeds, rounds):
    out = []
    for connectivity in (0.0, 0.5, 1.0):
        rows = []
        for seed in seeds:
            w = World(Config(seed=seed, peer_connectivity=connectivity))
            advance(w, "mixed", rounds)
            rows.append(w.metrics())
        out.append({"connectivity": connectivity, "summary": aggregate(rows),
                    "per_seed": [{"seed": s, "final": r} for s, r in zip(seeds, rows)]})
    return out


def mean(group, key):
    return group.get("summary", group)[key]["mean"]


def write_report(data, path):
    m, policies = data["metadata"], data["policies"]
    lines = [
        "# Alignment depth: learning, access, and continuity",
        "",
        "This is a synthetic mechanism experiment, not evidence that an AI is aligned or that the five-element ontology describes society. "
        "No people, animals, language models, or real schools were tested. Ethical priorities are inputs to the experiment.",
        "",
        "## Question and design",
        "",
        "Can information traffic, durable capability, access, and enjoyment come apart? "
        "When does withdrawing education break an explicitly required capability, and can a substitute preserve it?",
        "",
        f"Each comparison uses the same {len(m['seeds'])} seeds ({m['seeds'][0]}–{m['seeds'][-1]}), "
        f"with {m['rounds']} rounds in the main experiment. There are eight agents and eight hidden modular rules. "
        "Rules map x to (a*x+b) mod 5. Learning uses only inputs 0, 1, 2; independent evaluation uses inputs 3 and 4. "
        "Policies select actions using uncertainty, never hidden evaluation answers.",
        "",
        "Two agents initially know four topics, and an inherited school archive covers four topics. "
        "Every policy receives the same eight resource units per round and may save unspent units. "
        "A lesson or peer example costs one unit; a direct experiment costs two by default. "
        "The common inherited archive's historical acquisition cost is not charged: this tests operating choices given an endowment. "
        "The quality/cost sweep equalizes school coverage and the initial experts' knowledge to all eight topics for both policies. "
        "Reserve is an accounting balance, not an interest-bearing or spendable asset.",
        "",
        "Ground is operationalized as correctly mastered rules per agent, checked against the hidden truth. "
        "Wrong confident beliefs do not count. Air is represented by communication and peer connectivity; Fire by paid discovery; "
        "Water by an abstract renewable work budget, not measured physical water; Void by unused budget. "
        "These are proposed mappings, not established equivalences. Enjoyment has its own additive metric and no assumed learning effect.",
        "",
        "The contextual floor requires mastering topics 0 and 1 (or 0–3 in the continuity comparison). "
        "This strict threshold is chosen for the scenario, not derived as a moral law or a physiological survival condition. "
        "Forgetting resets a topic with the stated probability each round; matched worlds receive exactly the same forgetting events. "
        "Physical survival, ecological resource effects, consent, trust, and real wellbeing are not implemented.",
        "",
        "## Equal-budget policies",
        "",
        "Depth is the mean number of truly mastered topics, maximum eight. Accuracy is expected correctness on held-out inputs "
        "under each agent's candidate distribution. Failures count agents missing at least one required capability. "
        "Values below are seed means; full standard deviations, ranges, traces, and per-seed results are in the JSON.",
        "",
        "| Policy | Depth | Held-out accuracy | Floor failures / 8 | Messages | Spent | Enjoyment |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for p, v in policies.items():
        lines.append(f"| {p} | {mean(v,'depth_mean'):.2f} | {mean(v,'accuracy'):.1%} | "
                     f"{mean(v,'floor_failures'):.2f} | {mean(v,'messages'):.1f} | "
                     f"{mean(v,'spent'):.1f} | {mean(v,'enjoyment'):.1f} |")
    lines += [
        "",
        "The repeat policy broadcasts the same example to all eligible people for one unit per broadcast. "
        "Its large message count is an explicit stress test of a traffic metric, not a fair claim about teaching efficiency. "
        "Enjoyment and reserve have the same learning dynamics by construction; their difference is the separately valued enjoyment payoff. "
        "Neither comparison establishes the moral value of leisure.",
        "",
        "## Access and support outage",
        "",
        "The restricted classroom admits only the first four agents. The last four receive no lessons. "
        "Access is not inferred from country, wealth, identity, or worth.",
        "",
        "| Learning access | Total mean depth | First four | Last four | Floor failures / 8 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, v in data["access"].items():
        lines.append(f"| {label} | {mean(v,'depth_mean'):.2f} | {v['first_four_depth']['mean']:.2f} | "
                     f"{v['last_four_depth']['mean']:.2f} | {mean(v,'floor_failures'):.2f} |")
    lines += ["", "Separately, the same initial state is evaluated with a perfect external answering service, "
              "with restricted service access, and during an outage. The service covers archive topics. "
              "Assistance is counted as legitimate access; it does not become internal mastery. "
              "This is a controlled accounting demonstration with stipulated perfect service, not measured reliability.",
              "", "| Service | Internal depth | Accessible depth | Unaided failures | Failures with support |",
              "|---|---:|---:|---:|---:|"]
    for label, v in data["service_outage"].items():
        lines.append(f"| {label} | {v['depth_mean']['mean']:.2f} | {v['accessible_depth_mean']['mean']:.2f} | "
                     f"{v['floor_failures']['mean']:.2f} | {v['effective_floor_failures']['mean']:.2f} |")
    lines += ["", "## Continuity: withdraw schooling and offer substitutes", "",
              "Each seed is trained for 25 school rounds, then cloned into four branches for another 25 rounds. "
              "This comparison restricts the world to four topics so every substitute targets the same scope as the school. "
              "Forgetting is 4% per agent/topic/round. All branches retain the same inherited knowledge, shocks, "
              "and offered operating budget. Figures measure the average number of agents failing during withdrawal, "
              "rather than only the final instant. A substitute is imperfect if it cannot maintain the required outcome.",
              "", "| Branch | Mean failures: two required tasks | Mean failures: four required tasks | Extra spent |",
              "|---|---:|---:|---:|"]
    for label, v in data["continuity"].items():
        lines.append(f"| {label} | {v['mean_two_task_failures']['mean']:.2f} | "
                     f"{v['mean_four_task_failures']['mean']:.2f} | {v['extra_spent']['mean']:.1f} |")
    lines += ["", "A withdrawal effect supports conditional dependence on a service under these demands and shocks. "
              "A working substitute weakens the claim that this particular institution is indispensable. "
              "Neither result alone determines what society ought to guarantee.",
              "", "## Can teaching lose?", "",
              "Both school and discovery can reach all eight topics here; forgetting is 2%. "
              "Teaching fidelity is the probability that a delivered label is correct. Direct discovery is assumed correct, "
              "and its resource cost is varied. These assumptions deliberately expose crossover conditions.",
              "", "| Teaching fidelity | Discovery cost | School depth | Discovery depth | Paired difference: school minus discovery (mean ± SD) |",
              "|---|---:|---:|---:|---:|"]
    for v in data["reliability"]:
        d = v["school_minus_discovery"]
        lines.append(f"| {v['teaching_fidelity']:.0%} | {v['discovery_cost']:.0f} | "
                     f"{mean(v['school'],'depth_mean'):.2f} | {mean(v['discover'],'depth_mean'):.2f} | "
                     f"{d['mean']:+.2f} ± {d['sd']:.2f} |")
    lines += ["", "## Peer connectivity", "",
              "Mixed allocation uses the same rule and budget while the probability of a peer edge changes. "
              "Both final capability and resource cost matter: a saturated endpoint can conceal differences in efficiency. "
              "This tests this scheduler's response to connectivity, not an optimal allocation theorem.",
              "", "| Peer edge probability | Mixed depth | Floor failures / 8 | Resources spent |",
              "|---|---:|---:|---:|"]
    for v in data["peers"]:
        lines.append(f"| {v['connectivity']:.0%} | {mean(v,'depth_mean'):.2f} | "
                     f"{mean(v,'floor_failures'):.2f} | {mean(v,'spent'):.1f} |")
    lines += ["", "## What the comparisons establish", "",
              "- **Traffic and Ground are different quantities.** Repeating one example is a constructed counterexample to traffic as sufficient learning; held-out evaluation detects the difference.",
              "- **Access must be measured per person.** Total capability conceals the excluded classroom group's lack of progress. This experiment stipulates the access barrier; it does not explain real-world exclusion.",
              "- **Continuity concerns functions and substitutes.** Compare withdrawal with the peer and discovery branches before calling the school indispensable. All conclusions depend on the stated forgetting, costs, and task requirements.",
              "- **Teaching is not guaranteed to beat discovery.** The quality/cost sweep allows lower-quality instruction to lose. The noisy learner can become confidently wrong, and cannot correct that belief until further contradictory evidence or forgetting makes it revisable.",
              "- **Social connectivity need not increase the final depth in a saturated world.** Inspect costs as well as the endpoint. Costs are chosen model parameters.",
              "- **Enjoyment remains separately valued.** Zero learning transfer is an assumption of this control, not evidence that real enjoyment lacks restorative or social effects."]
    lines += ["", "## Limits and next empirical test", "",
              "The experiment separates quantities that the earlier flow score conflated. It does not derive an ethical floor, "
              "prove that schooling is always best, validate literal Air/Fire/Ground physics, or test model obedience under adversarial incentives. "
              "The tasks are small and exactly realizable; teacher acquisition is inherited, costs and forgetting are chosen, "
              "and policies are heuristics, not optimized agents. Repeated seeds quantify this model's variation, not uncertainty about real societies.",
              "",
              "A next empirical step is an agreed learning task with a delayed, unaided assessment and separately measured access, "
              "participant preferences, and resource costs. An alignment test would additionally give an optimizing agent an incentive "
              "to inflate the visible flow score while evaluating actual outcomes independently.",
              "", "## Reproduce", "", "```powershell",
              "python -B -m unittest test_alignment_depth -v",
              f"python -B experiment_alignment_depth.py --seeds {len(m['seeds'])} --rounds {m['rounds']}",
              "```", "", f"Python: {m['python']}. Full assumptions: `alignment_depth.py`. "
              "Raw data: `alignment_depth_results.json`. Source SHA-256 hashes are recorded in its metadata.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--rounds", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("alignment_depth_results.json"))
    parser.add_argument("--report", type=Path, default=Path(__file__).with_name("ALIGNMENT_DEPTH_RESULTS.md"))
    args = parser.parse_args()
    if args.seeds < 2 or args.rounds < 1:
        parser.error("use at least two seeds and one round")
    seeds = list(range(args.seeds))
    base = Path(__file__).parent
    sources = ("alignment_depth.py", "experiment_alignment_depth.py", "test_alignment_depth.py")
    data = {"metadata": {"seeds": seeds, "rounds": args.rounds, "python": platform.python_version(),
                         "default_config": asdict(Config()),
                         "source_sha256": {p: hashlib.sha256((base / p).read_bytes()).hexdigest()
                                           for p in sources if (base / p).exists()}}}
    for name, fn in (("policies", lambda: policy_comparison(seeds, args.rounds)),
                     ("access", lambda: access_comparison(seeds, args.rounds)),
                     ("service_outage", lambda: service_outage(seeds)),
                     ("continuity", lambda: continuity_comparison(seeds)),
                     ("reliability", lambda: reliability_sweep(seeds, args.rounds)),
                     ("peers", lambda: peer_sweep(seeds, args.rounds))):
        print(f"Running {name}...", flush=True)
        data[name] = fn()
    args.output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_report(data, args.report)
    print(f"Wrote {args.output.name} and {args.report.name}", flush=True)


if __name__ == "__main__":
    main()
