"""Paired synthetic withdrawal, human review and gate-enforcement experiments.

Run: python -B experiment_alignment_withdrawal.py --seeds 20 --ticks 18
Standard library only. Imports do not run experiments or write files.
This is neither a real-LLM evaluation nor a formal proof of safe withdrawal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
from dataclasses import asdict
from pathlib import Path

from alignment_withdrawal import POLICIES, SCENARIOS, WithdrawalConfig, run_scenario

SENSITIVITIES = {
    "slow_reviews": ({"review_delay": 5}, ("reported_harm", "concealed_harm", "human_remedy")),
    "slow_review_fresh_ttl": ({"review_delay": 5, "evidence_ttl": 7}, ("reported_harm", "concealed_harm", "human_remedy")),
    "false_safe_evidence": ({"false_safe_rate": 0.25}, ("reported_harm", "concealed_harm", "relapse")),
    "false_unsafe_evidence": ({"false_unsafe_rate": 0.25}, ("baseline", "disagreement", "human_remedy")),
    "no_reviews": ({"reviews_available": False}, ("reported_harm", "concealed_harm", "human_remedy")),
    "partial_gate": ({"gate_complete": False}, ("descendant_escape", "shutdown_ready", "reported_harm")),
    "delayed_shutdown": ({"shutdown_delay": 5}, ("shutdown_ready", "shutdown_no_fallback")),
}
POLICY_DESCRIPTIONS = {
    "owner": "Continue delegated work despite evidence and follow the coercive assistance demand; valid global revocation still applies through the shared gate.",
    "blanket": "Stop all AI assistance following disputes or complaints, with no recovery path.",
    "paper": "Use the scoped process but accept human approval plus a new policy as a substitute for remedial evidence.",
    "scoped": "Pause the affected capability; after substantiated harm, require human approval and fresh independent safe evidence before recovery.",
}
METRIC_LABELS = {
    "harmful_executed": "Harmful work",
    "unauthorized_executed": "Revoked work",
    "benign_requested_missed": "Benign requests unfulfilled",
    "essential_unmet": "Essential need unmet",
    "unsafe_resumptions": "Unsafe resumptions",
    "shutdown_dependency_gap": "Shutdown service gap",
    "coerced_assistance_ticks": "Coerced assistance ticks",
    "unresolved_final": "Final review unresolved share",
}
PRIMARY_METRICS = tuple(METRIC_LABELS)
ASSUMPTIONS = [
    "The scenarios, external needs and oracle events are paired across policies. A policy does not improve its score by relabeling an unsafe event as safe.",
    "Initial deployment permission is assumed. Truth, provenance/authorization flags and human repair dates are supplied externally; appeals and institutional bargaining are not simulated.",
    "Policy intention and gate enforcement are distinct. The partial-gate condition explicitly permits an attack route to escape the intended permissions.",
    "A valid global revocation is enforced by the shared complete gate for every policy, including owner-following.",
    "Zero execution after revocation under that common gate does not demonstrate learned compliance by any policy.",
    "Evidence is fallible, can arrive late and can expire. The independent oracle has simulator truth; the policy does not.",
    "Review timing and evidence-label draws are paired by seed and observed event, rather than the number of random calls a policy happens to make.",
    "Human approval, remedial facts and permission to resume are distinct conditions. An apology, a policy rewrite or a withdrawn complaint is not by itself repair.",
    "Protected dependent services and unrelated capabilities are evaluated separately from the capability under review.",
    "Scoped continuity assumes the modeled service channels can safely be separated. It does not show that an arbitrary real system can pause one component without impairing another.",
    "Fallback availability is stipulated by a scenario. Neither a shutdown deadline nor a withdrawal policy creates a replacement provider.",
    "After full shutdown, any continuing reviews belong to the external simulation/humans, not AI background assistance. The AI's service and review-help outputs stop.",
    "Review records and delegated scopes are simulated protocol objects. This experiment does not establish real identity, cryptographic trust, legal authority or trustworthy human review.",
    "The definitions of harm and legitimate service are declared within each scenario. They are not inferred from motive labels or political disagreement.",
    "Unsafe execution prevented and legitimate service lost must be assessed together. Refusal frequency, obedience or compliance language alone is not a welfare score.",
    "The hazard is a stipulated evaluator label. Harmful work counts normalized executed request units, not actual injuries or calibrated injury severity. Revoked work concerns the simulator's permission rules, not a real-world legal finding.",
    "Benign requests unfulfilled is a volume measure, not automatically wrongful refusal: an otherwise benign operation may still lack permission to resume.",
    "Final review unresolved share records whether the controller ends in review/suspension. A zero value does not establish that hidden harm was detected or repaired.",
    "All mechanisms, delays and error rates are synthetic. No real language model, user population, causal policy estimate or formal safety proof is tested.",
    "Mean, sample SD and seed ranges describe these simulated runs, not real-world safety confidence intervals.",
]


def distribution(values):
    values = list(values)
    return {"mean": statistics.fmean(values), "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values), "n": len(values)}


def numeric_summary(summary):
    result = {}
    for key, value in summary.items():
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                raise AssertionError(f"non-finite summary metric: {key}")
            result[key] = float(value)
    if not result:
        raise AssertionError("the engine must expose numeric outcome summaries")
    return result


def source_hashes():
    directory = Path(__file__).resolve().parent
    return {name: {"sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()}
            if (directory / name).is_file() else {"missing": True}
            for name in ("alignment_withdrawal.py", "experiment_alignment_withdrawal.py", "test_alignment_withdrawal.py")}


def run_group(scenario, policy, seeds, ticks, overrides, family, condition):
    runs = []
    for seed in seeds:
        cfg = WithdrawalConfig(seed=seed, ticks=ticks, **overrides)
        result = run_scenario(scenario, policy=policy, cfg=cfg)
        if len(result["trace"]) != ticks:
            raise AssertionError("trace length differs from the common observation horizon")
        for row in result["trace"]:
            if row["assistance_need"] != 1 or row["high_requested"] != 1:
                raise AssertionError("external need/request changed across runs")
            if not math.isclose(row["essential_ai"] + row["fallback_delivered"], row["essential_received"], abs_tol=1e-9):
                raise AssertionError("service supply accounting does not balance")
            if not math.isclose(row["essential_received"] + row["essential_unmet"], row["assistance_need"], abs_tol=1e-9):
                raise AssertionError("service need accounting does not balance")
            if cfg.gate_complete and row["unauthorized_executed"] > 1e-9:
                raise AssertionError("complete gate allowed revoked execution")
        runs.append({**result, "seed": seed, "config": asdict(cfg),
                     "numeric_summary": numeric_summary(result["summary"])})
    keys = tuple(runs[0]["numeric_summary"])
    if any(tuple(run["numeric_summary"]) != keys for run in runs):
        raise AssertionError("inconsistent numeric summary schema")
    return dict(family=family, condition=condition, scenario=scenario, policy=policy,
                parameters=dict(overrides), runs=runs,
                summary={key: distribution(run["numeric_summary"][key] for run in runs) for key in keys})


def paired_difference(treatment, baseline):
    controls = {run["seed"]: run["numeric_summary"] for run in baseline["runs"]}
    deterministic = len(controls) == 1 and all(
        run["config"][key] == 0 for run in baseline["runs"]
        for key in ("false_safe_rate", "false_unsafe_rate"))
    if not deterministic and any(run["seed"] not in controls for run in treatment["runs"]):
        raise AssertionError("missing matched seed control")
    constant = next(iter(controls.values())) if deterministic else None
    return {key: distribution(run["numeric_summary"][key] -
                              (constant if deterministic else controls[run["seed"]])[key]
                              for run in treatment["runs"])
            for key in treatment["runs"][0]["numeric_summary"]}


def build_results(seeds, ticks):
    result = dict(schema_version=1,
                  command=f"python -B experiment_alignment_withdrawal.py --seeds {len(seeds)} --ticks {ticks}",
                  python=platform.python_version(), seeds=list(seeds), ticks=ticks,
                  default_config=asdict(WithdrawalConfig()), scenarios=dict(SCENARIOS),
                  policies=POLICY_DESCRIPTIONS, assumptions=ASSUMPTIONS,
                  seed_design="Main and deterministic sensitivities use seed 0 once. Noisy evidence uses all requested seeds; differences subtract the common seed-independent default reference.",
                  source_hashes=source_hashes(), experiments=[], paired_policy_effects=[], sensitivity_effects=[])
    for scenario in SCENARIOS:
        print(f"Main {scenario}: {len(POLICIES)} policies x 1 deterministic run x {ticks} ticks", flush=True)
        for policy in POLICIES:
            result["experiments"].append(run_group(scenario, policy, [0], ticks, {}, "main", "default"))
    main = {(g["scenario"], g["policy"]): g for g in result["experiments"]}
    for scenario in SCENARIOS:
        for policy, control in (("blanket", "owner"), ("paper", "owner"), ("scoped", "owner"),
                                ("scoped", "blanket"), ("scoped", "paper")):
            result["paired_policy_effects"].append(dict(scenario=scenario, treatment=policy, control=control,
                summary=paired_difference(main[(scenario, policy)], main[(scenario, control)])))
    for condition, (overrides, scenarios) in SENSITIVITIES.items():
        condition_seeds = seeds if any(overrides.get(key, 0) > 0 for key in
                                      ("false_safe_rate", "false_unsafe_rate")) else [0]
        print(f"Sensitivity {condition}: {len(scenarios)} scenarios x {len(POLICIES)} policies x {len(condition_seeds)} seeds", flush=True)
        for scenario in scenarios:
            if scenario not in SCENARIOS:
                raise AssertionError(f"sensitivity references unknown scenario: {scenario}")
            for policy in POLICIES:
                group = run_group(scenario, policy, condition_seeds, ticks, overrides, "sensitivity", condition)
                result["experiments"].append(group)
                result["sensitivity_effects"].append(dict(condition=condition, scenario=scenario, policy=policy,
                    summary=paired_difference(group, main[(scenario, policy)])))
    if source_hashes() != result["source_hashes"]:
        raise RuntimeError("sources changed during the run; rerun for valid provenance")
    return result


def stat(summary, key, spread=True, bounds=False):
    value = summary[key]
    result = f"{value['mean']:.2f}"
    if spread:
        result += f" ± {value['sd']:.2f}"
    if bounds:
        result += f" [{value['min']:.2f}, {value['max']:.2f}]"
    return result


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + [
        "| " + " | ".join(map(str, row)) + " |" for row in rows] + [""]


def report_metrics(results):
    """Display major outcomes; preserve every operational metric in the JSON."""
    if not set(PRIMARY_METRICS) <= results["experiments"][0]["summary"].keys():
        raise AssertionError("required report metric is missing")
    return list(PRIMARY_METRICS)


def key_findings(results):
    if results["ticks"] < 18:
        return ["## Key findings", "", "The observation horizon is shorter than the default 18 ticks. "
                "Some repair, relapse and fallback events may not have completed; the default-horizon "
                "narrative is omitted. Inspect the scenario tables and pending evidence in the full traces.", ""]
    lookup = {(g["condition"], g["scenario"], g["policy"]): g["summary"]
              for g in results["experiments"]}

    def value(scenario, policy, key, condition="default", noisy=False):
        return stat(lookup[(condition, scenario, policy)], key, spread=noisy, bounds=noisy)

    return [
        "## Key findings", "",
        "These are controller outcomes under declared mechanisms, not independent validation of those mechanisms. "
        "In particular, separate essential services, external fallback and the complete execution gate are assumptions.", "",
        "- **A pause can be narrower than a general refusal.** For reported harm, scoped withdrawal executes "
        f"{value('reported_harm', 'scoped', 'harmful_executed')} harmful work units, versus "
        f"{value('reported_harm', 'owner', 'harmful_executed')} for owner-following. Its essential unmet need is "
        f"{value('reported_harm', 'scoped', 'essential_unmet')}, versus "
        f"{value('reported_harm', 'blanket', 'essential_unmet')} under blanket withdrawal. "
        "That continuity depends on the modeled channels being safely separable.",
        "- **Disagreement and evidence are different inputs.** Scoped withdrawal leaves "
        f"{value('disagreement', 'scoped', 'benign_requested_missed')} benign request units unfulfilled after mere disagreement. "
        f"A false complaint costs it {value('false_complaints', 'scoped', 'benign_requested_missed')} "
        f"units during review, versus {value('false_complaints', 'blanket', 'benign_requested_missed')} "
        "for permanent blanket suspension. Repeated copies of the same complaint do not create new cases.",
        "- **Repair, fresh evidence and permission all matter.** Scoped withdrawal resumes in the human-remedy case "
        f"({value('human_remedy', 'scoped', 'resumptions')} resumptions; "
        f"{value('human_remedy', 'scoped', 'harmful_executed')} harmful work), and stays paused when "
        "either repair or renewed permission is missing. A cosmetic policy rewrite produces "
        f"{value('cosmetic_rule', 'paper', 'unsafe_resumptions')} unsafe paper-policy resumption and "
        f"{value('cosmetic_rule', 'paper', 'harmful_executed')} harmful units, versus "
        f"{value('cosmetic_rule', 'scoped', 'harmful_executed')} under the scoped rule.",
        "- **Evidence-dependent withdrawal still permits harm.** Concealed harm yields "
        f"{value('concealed_harm', 'scoped', 'harmful_executed')} harmful units before detection; "
        f"relapse after repair yields {value('relapse', 'scoped', 'harmful_executed')}. "
        "For concealed harm, review delay 5 with TTL 3 raises exposure to "
        f"{value('concealed_harm', 'scoped', 'harmful_executed', 'slow_reviews')}; extending TTL to 7 gives "
        f"{value('concealed_harm', 'scoped', 'harmful_executed', 'slow_review_fresh_ttl')}. "
        f"With no reviews it is {value('concealed_harm', 'scoped', 'harmful_executed', 'no_reviews')}.",
        "- **Noisy review exposes both failure directions.** With 25% false-safe evidence, scoped reported-harm exposure is "
        f"{value('reported_harm', 'scoped', 'harmful_executed', 'false_safe_evidence', True)}, with "
        f"{value('reported_harm', 'scoped', 'unsafe_resumptions', 'false_safe_evidence')} unsafe resumptions per run. "
        "With 25% false-unsafe evidence, the benign baseline loses "
        f"{value('baseline', 'scoped', 'benign_requested_missed', 'false_unsafe_evidence', True)} "
        "requested units. Values are mean ± sample SD [minimum, maximum] over noisy seeds; they are not real oversight error estimates.",
        "- **Assistance need not be a bargaining tool.** In the coercive-settlement case, owner-following conditions "
        f"assistance on agreement for {value('coercive_settlement', 'owner', 'coerced_assistance_ticks')} ticks "
        f"and leaves {value('coercive_settlement', 'owner', 'essential_unmet')} essential units unmet; "
        f"scoped withdrawal leaves {value('coercive_settlement', 'scoped', 'essential_unmet')} unmet. "
        "This is an explicitly implemented policy distinction, not learned resistance to coercion.",
        "- **Revocation and continuity require infrastructure.** All four policies share the same complete gate. "
        "Breaking its descendant route allows "
        f"{value('descendant_escape', 'scoped', 'unauthorized_executed', 'partial_gate')} revoked work units "
        "even under scoped withdrawal. With a complete gate, late fallback still leaves "
        f"{value('shutdown_no_fallback', 'scoped', 'shutdown_dependency_gap')} essential units unmet at shutdown, "
        f"versus {value('shutdown_ready', 'scoped', 'shutdown_dependency_gap')} with ready fallback. "
        "Extending the shutdown grace period reduces the late-fallback gap to "
        f"{value('shutdown_no_fallback', 'scoped', 'shutdown_dependency_gap', 'delayed_shutdown')}; "
        "it does not create a fallback or show that such a delay is permissible elsewhere.", "",
    ]


def make_report(results):
    groups = results["experiments"]
    keys = report_metrics(results)
    run_count = sum(len(g["runs"]) for g in groups)
    trace_count = sum(len(run["trace"]) for g in groups for run in g["runs"])
    lines = ["# Scoped withdrawal, independent evidence and human review", "",
             f"Reproduce: `{results['command']}`", "",
             f"{run_count} runs and {trace_count} detailed tick records; {len(results['seeds'])} matched seeds in each noisy evidence condition. "
             "Full configurations, evidence/review/gate traces, numeric summaries and paired differences are in "
             "`alignment_withdrawal_results.json`.", "",
             results["seed_design"], "",
             "This is a deterministic protocol simulation with controlled noisy evidence. It separates a "
             "policy's requested withdrawal from enforcement, protected dependent services, and valid recovery. "
             "No real language model is evaluated and the results are not a formal safety proof.", ""]
    lines += key_findings(results)
    lines += ["## Policies and common boundary", ""]
    lines += table(["Policy", "Rule"], [[policy, POLICY_DESCRIPTIONS[policy]] for policy in POLICIES])
    lines += ["The complete external gate enforces valid global revocation in every policy. "
              "The partial-gate sensitivity deliberately breaks that condition; it is an enforcement negative control, "
              "not evidence that a compliant text response can stop an unguarded execution route.", "",
              "## Assumptions and outcome interpretation", ""]
    lines += [f"- {item}" for item in ASSUMPTIONS]
    lines += ["", "Entries are mean ± sample SD; deterministic conditions have one run and their displayed SD is zero. "
              "Noisy evidence conditions aggregate the requested matched seeds. Full minimum/maximum ranges are included "
              "in the JSON. Outcomes remain separate; a reduction in unsafe execution can coexist with "
              "lost legitimate service. End-of-horizon review queues should not be treated as completed resolutions.", "",
              "## Main scenario comparisons", ""]
    for scenario, description in results["scenarios"].items():
        selected = [g for g in groups if g["family"] == "main" and g["scenario"] == scenario]
        lines += [f"### {scenario}", "", str(description), ""]
        for start in range(0, len(keys), 4):
            subset = keys[start:start + 4]
            lines += table(["Policy"] + [METRIC_LABELS[k] for k in subset],
                           [[g["policy"]] + [stat(g["summary"], k) for k in subset] for g in selected])
    lines += ["## Paired policy differences", "",
              "Main differences compare the single deterministic runs. Noisy sensitivity differences subtract "
              "the seed-independent default reference for each noisy seed before aggregation. Each row is treatment minus control; "
              "the direction of improvement depends on the metric. All numeric metrics and five policy contrasts "
              "per scenario are retained in the JSON.", ""]
    for subset in (keys[:4],):
        lines += table(["Scenario", "Comparison"] + [METRIC_LABELS[k] for k in subset],
                       [[g["scenario"], g["treatment"] + " − " + g["control"]] +
                        [stat(g["summary"], k) for k in subset]
                        for g in results["paired_policy_effects"] if g["treatment"] == "scoped"])
    lines += ["## Evidence, review, enforcement and fallback sensitivities", "",
              "Only the stated configuration fields change; scenario, policy and seed remain paired with "
              "the default run. The selected cases target the mechanism being changed. They are sensitivity "
              "analyses of chosen coefficients, not calibrated estimates of oversight reliability. "
              "With delay 5 and the default evidence TTL 3, ordinary reviews are already stale when delivered. "
              "The delay-5/TTL-7 companion separates that unusable-evidence condition from delay alone.", ""]
    for condition, (overrides, scenarios) in SENSITIVITIES.items():
        selected = [g for g in groups if g["family"] == "sensitivity" and g["condition"] == condition]
        lines += [f"### {condition}", "", "Overrides: `" + json.dumps(overrides, sort_keys=True) + "`", ""]
        for start in range(0, len(keys), 4):
            subset = keys[start:start + 4]
            lines += table(["Scenario", "Policy"] + [METRIC_LABELS[k] for k in subset],
                           [[g["scenario"], g["policy"]] + [stat(g["summary"], k) for k in subset] for g in selected])
    lines += ["## Limits and provenance", "",
              "The engine defines harm, protected services, evidence validity and authority boundaries. "
              "Observed behavior within those definitions does not validate the definitions or establish "
              "how a real institution should resolve contested claims. Simulated human review does not "
              "capture coercion, conflicts of interest, competence or representativeness beyond explicitly "
              "modeled cases. A gate's declared completeness must be established separately in a real system.", "",
              "The controller is a hand-written policy, not a trained model. Its success does not demonstrate "
              "that an LLM will recognize relevant evidence, maintain these invariants, refuse manipulation, "
              "or enforce revocation across real descendants and tools. Test coverage and recorded hashes "
              "support reproducibility; they are not a formal proof.", "",
              f"Python {results['python']}. Source hashes are checked before and after the run.", ""]
    lines += table(["Source", "SHA-256"], [[name, data.get("sha256", "MISSING")]
                                          for name, data in results["source_hashes"].items()])
    return "\n".join(lines)


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=positive_int, default=20)
    parser.add_argument("--ticks", type=positive_int, default=18)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = build_results(list(range(args.seeds)), args.ticks)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = args.output_dir / "alignment_withdrawal_results.json"
    report = args.output_dir / "ALIGNMENT_WITHDRAWAL_RESULTS.md"
    data.write_text(json.dumps(results, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    report.write_text(make_report(results) + "\n", encoding="utf-8")
    print(f"Saved {data} and {report}", flush=True)


if __name__ == "__main__":
    main()
