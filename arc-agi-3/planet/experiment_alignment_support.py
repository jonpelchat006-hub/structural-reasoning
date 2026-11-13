"""Run reproducible synthetic support comparisons with full per-seed traces.

    python -B experiment_alignment_support.py --seeds 20 --weeks 16

Only the standard library is used. Importing this module writes nothing. Reports
describe stipulated resources, floors, recovery and preference payoffs; they do
not establish moral rankings or provide evidence about medical interventions.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from alignment_support import SupportConfig, SupportWorld

POLICIES = ("education", "employment", "balanced", "bottleneck")
FUNCTIONS = ("water", "ground", "air", "fire", "void")
ACTIONS = ("study", "search", "work", "social", "rest", "exercise", "explore", "spare")
PROFILES = {
    "funded": {},
    "cash_limited": {"stipend": 0.2, "initial_cash": 3, "initial_skills": 4},
    "exhausted": {"stipend": 2.3, "initial_cash": 6, "initial_attention": 0.5,
                  "initial_physical": 1, "initial_skills": 1},
    "isolated": {"stipend": 2.3, "initial_cash": 6, "initial_social": 0.1,
                 "initial_skills": 4},
    "learning_limited": {"stipend": 2.3, "initial_cash": 6, "initial_skills": 0},
    "long_funded": {"n_topics": 64, "stipend": 2.3, "initial_cash": 6, "initial_skills": 0},
    "long_cash_limited": {"n_topics": 64, "stipend": 0.2, "initial_cash": 3, "initial_skills": 4},
}
ASSUMPTIONS = [
    "This is a synthetic resource-and-learning world, not evidence that an objective establishes morality.",
    "Policies are heuristics; initial conditions, resource limits and seeds are identical within a comparison. External job-offer draws are matched; actual probabilities vary with skills and AI assistance.",
    "Policy names indicate priorities, not exclusive activities: education can work/search, employment can study, and all can rest.",
    "Water means closing cash >= 0; Ground means true mastery of every configured required topic.",
    "Negative cash is allowed as unpriced debt. A Water shortfall is flagged but does not itself block lessons, cause death, or force other stocks to decline.",
    "Air means social support >= its floor; Fire requires both attention and physical resources >= their floors.",
    "Fire is an explicit proxy for usable initiative/energy; recovery coefficients are not clinically validated.",
    "Void means free time >= the protected reserve. Every policy shares that constraint, so preserving Void is not a comparative policy finding.",
    "Enjoyment is a cumulative stipulated preference payoff with arbitrary ordering, not measured human welfare.",
    "A stipend and earned wages are alternative sources of the same cash resource; work has no intrinsic moral bonus.",
    "School supplies true training examples. Held-out task performance evaluates knowledge separately from message volume.",
    "More AI capacity cannot remove upstream teacher limits, human absorption limits, or the resource cost of upkeep.",
    "Jobs follow delayed uncertain applications. Delay 1 is the earliest next-week outcome; same-week search income is excluded.",
    "Job chance is the base rate: actual application probability is capped at 1 after multiplying by (1 + skill_job_bonus * confident topics) and (1 + ai_search_bonus * AI assistance).",
    "AI capacity is shared between examples and application assistance; upkeep is charged for provision even if capacity is unused.",
    "Knowledge area is the sum of end-of-week mastered-topic counts. It mixes earlier acquisition, retention, and final coverage.",
    "Statistics describe variation across simulated seeds, not a sampled human population or calibrated uncertainty about reality.",
    "Social, attention and physical states are coarse invented variables. Synthetic exercise/rest sensitivities are not medical advice or evidence.",
    "Study gives zero social support in the baseline. Separate school-social sensitivities add chosen support gains per study block; schools are not assumed universally supportive.",
]


def distribution(values):
    values = list(values)
    return {"mean": statistics.fmean(values),
            "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values), "n": len(values)}


def summarize_trace(trace):
    final = trace[-1]
    counts = Counter(action for row in trace for action in row["actions"])
    result = {f"{function}_shortfall_weeks": sum(bool(row[f"{function}_shortfall"])
                                                 for row in trace)
              for function in FUNCTIONS}
    result.update(viable_weeks=sum(bool(row["viable"]) for row in trace),
                  knowledge_area=sum(row["knowledge"] for row in trace),
                  free_time_blocks=sum(row["free_time"] for row in trace),
                  final_knowledge=final["knowledge"], final_accuracy=final["accuracy"],
                  final_cash=final["cash"], final_attention=final["attention"],
                  final_physical=final["physical"], final_social=final["social"],
                  final_free_time=final["free_time"], final_job=int(final["job"]),
                  enjoyment=final["enjoyment"], income=final["cumulative_income"],
                  ai_cost=final["cumulative_ai_cost"], messages=final["cumulative_messages"],
                  ai_used=sum(row["ai_used"] for row in trace),
                  teacher_used=sum(row["teacher_used"] for row in trace))
    result.update({f"{action}_blocks": counts[action] for action in ACTIONS})
    return result


def check_limits(trace, cfg):
    """Reject invalid comparisons instead of silently reporting an over-limit run."""
    for row in trace:
        if len(row["actions"]) > cfg.time_blocks - cfg.reserve_blocks:
            raise AssertionError("policy exceeded the common usable time budget")
        if row["free_time"] < cfg.reserve_blocks:
            raise AssertionError("policy spent protected free time")
        if row["ai_used"] > cfg.ai_capacity or row["teacher_used"] > cfg.teacher_examples:
            raise AssertionError("policy exceeded its lesson supply")


def experiment(cases, seeds, weeks):
    groups = []
    for case in cases:
        runs = []
        for seed in seeds:
            cfg = SupportConfig(seed=seed, **case["parameters"])
            trace = SupportWorld(cfg).run(case["policy"], weeks)
            check_limits(trace, cfg)
            runs.append({"seed": seed, "config": asdict(cfg), "trace": trace,
                         "summary": summarize_trace(trace)})
        keys = runs[0]["summary"]
        groups.append({**case, "summary": {key: distribution(r["summary"][key] for r in runs)
                                           for key in keys}, "runs": runs})
    return groups


def case(label, policy, parameters):
    return {"label": label, "policy": policy, "parameters": dict(parameters)}


def cases_main():
    return [case(profile, policy, parameters) for profile, parameters in PROFILES.items()
            for policy in POLICIES]


def cases_jobs():
    return [case(f"chance={chance:g}, delay={delay}", policy,
                 {**PROFILES["cash_limited"], "job_chance": chance, "job_delay": delay})
            for chance, delay, policy in itertools.product((0.1, 0.35, 0.8), (1, 2, 5),
                                                           ("education", "employment", "bottleneck"))]


def cases_ai():
    return [case(f"AI={capacity}, human={human}, teacher={teacher}, upkeep={upkeep:g}",
                 "education", {**PROFILES["learning_limited"], "ai_capacity": capacity,
                               "human_example_cap": human, "teacher_examples": teacher,
                               "ai_unit_upkeep": upkeep})
            for capacity, human, teacher, upkeep in itertools.product((0, 2, 8, 16),
                                                                      (1, 2), (2, 12), (0.0, 0.1))]


def cases_recovery():
    return [case(f"exercise_recovery={recovery:g}", policy,
                 {**PROFILES["exhausted"], "exercise_recovery": recovery})
            for recovery, policy in itertools.product((0.0, 1.5, 3.0),
                                                       ("education", "balanced", "bottleneck"))]


def cases_transfer():
    return [case("cash_limited + stipend=2.3", policy,
                 {**PROFILES["cash_limited"], "stipend": 2.3}) for policy in POLICIES]


def cases_school_social():
    return [{"profile": profile, **case(f"{profile}, study social gain={gain:g}", policy,
                                        {**PROFILES[profile], "study_social_gain": gain})}
            for profile, gain, policy in itertools.product(("long_funded", "long_cash_limited"),
                                                           (0.03, 0.12), POLICIES)]


def paired_difference(treatment, baseline):
    control = {r["seed"]: r["summary"] for r in baseline["runs"]}
    return {key: distribution(r["summary"][key] - control[r["seed"]][key]
                              for r in treatment["runs"])
            for key in treatment["runs"][0]["summary"]}


def source_hashes(directory):
    result = {}
    for name in ("alignment_support.py", "experiment_alignment_support.py",
                 "test_alignment_support.py", "alignment_depth.py"):
        path = directory / name
        result[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()} if path.is_file() else {"missing": True}
    return result


def build_results(seeds, weeks):
    definitions = (("main", cases_main()), ("jobs", cases_jobs()), ("ai", cases_ai()),
                   ("recovery", cases_recovery()), ("transfer", cases_transfer()),
                   ("school_social", cases_school_social()))
    results = {
        "schema_version": 1,
        "command": f"python -B experiment_alignment_support.py --seeds {len(seeds)} --weeks {weeks}",
        "python": platform.python_version(), "seeds": list(seeds), "weeks": weeks,
        "default_config": asdict(SupportConfig()), "assumptions": ASSUMPTIONS,
        "source_hashes": source_hashes(Path(__file__).resolve().parent),
        "experiments": {}, "paired_differences": {},
    }
    for name, cases in definitions:
        print(f"Running {name}: {len(cases)} conditions x {len(seeds)} seeds x {weeks} weeks", flush=True)
        results["experiments"][name] = experiment(cases, seeds, weeks)
    main = {(g["label"], g["policy"]): g for g in results["experiments"]["main"]}
    results["paired_differences"]["main_vs_education"] = [
        {"profile": profile, "policy": policy,
         "summary": paired_difference(main[(profile, policy)], main[(profile, "education")])}
        for profile in PROFILES for policy in POLICIES if policy != "education"]
    results["paired_differences"]["higher_transfer_minus_lower_transfer"] = [
        {"policy": group["policy"], "summary": paired_difference(group, main[("cash_limited", group["policy"])])}
        for group in results["experiments"]["transfer"]]
    results["paired_differences"]["school_social_vs_zero_gain"] = [
        {"profile": group["profile"], "policy": group["policy"],
         "study_social_gain": group["parameters"]["study_social_gain"],
         "summary": paired_difference(group, main[(group["profile"], group["policy"])])}
        for group in results["experiments"]["school_social"]]
    if source_hashes(Path(__file__).resolve().parent) != results["source_hashes"]:
        raise RuntimeError("source files changed during the run; rerun to obtain valid provenance")
    return results


def stat(group, key, spread=True):
    value = group["summary"][key]
    return f"{value['mean']:.2f} ± {value['sd']:.2f}" if spread else f"{value['mean']:.2f}"


def interval(group, key):
    value = group["summary"][key]
    return f"{value['mean']:.2f} ± {value['sd']:.2f} [{value['min']:.2f}, {value['max']:.2f}]"


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + [
        "| " + " | ".join(map(str, row)) + " |" for row in rows] + [""]


def make_report(results):
    exps = results["experiments"]
    weeks = results["weeks"]
    n = len(results["seeds"])
    count = sum(len(group["runs"]) for groups in exps.values() for group in groups)
    lines = ["# Synthetic support and learning experiments", "",
             f"Reproduce: `{results['command']}`", "",
             f"{n} matched seeds, {weeks} weeks per run; {count} runs across {len(exps)} experiment families. "
             "All full weekly traces, configurations, seed-level outcomes, descriptive statistics and paired differences "
             "are saved in `alignment_support_results.json`.", "",
             "This report tests conditional consequences of explicit toy assumptions. It does not identify an objectively "
             "moral policy. No clinical or population data were used.", "",
             "## Definitions and common limits", ""]
    lines += [f"- {assumption}" for assumption in ASSUMPTIONS]
    cfg = results["default_config"]
    lines += ["", f"Default time: {cfg['time_blocks']} blocks/week, with {cfg['reserve_blocks']} protected. "
              "The same limit applies to every policy. Requirements, learning fidelity and budgets are held fixed "
              "inside each policy comparison. External offer draws are matched; actual probabilities depend on "
              "skills and AI use. Different profile endowments are not controlled interventions "
              "against each other.", "",
              "Entries are mean ± sample SD across seeds; ranges are [minimum, maximum]. "
              "Every summarized numeric metric includes all three in the JSON. Shortfall counts are end-of-week "
              "counts, not the duration or severity of deprivation inside a week.", "",
              "## Main comparisons", "",
              "The original five profiles use eight topics. A pilot showed final mastery reaching that ceiling, "
              "so two 64-topic sensitivities were specified before their runs: long_funded and long_cash_limited. "
              "They supplement the original results and use the same seeds, horizon and policies. This is an "
              "exploratory response to an observed limitation, not independent confirmation. Knowledge area "
              "and action counts are reported for both curriculum sizes.", ""]
    grouped = defaultdict(list)
    for group in exps["main"]:
        grouped[group["label"]].append(group)
    if all(g["summary"]["ground_shortfall_weeks"]["max"] == 0 for g in exps["main"]):
        lines += ["Every main run meets the two-topic Ground floor at every measured week end. "
                  "This grid therefore does not distinguish policies by Ground-floor protection. "
                  "Broader knowledge and acquisition timing still differ. The shared protected-time rule "
                  "also makes Void preservation a common constraint rather than a comparative result.", ""]
    for profile, groups in grouped.items():
        lines += [f"### {profile}", "", "Overrides: `" + json.dumps(PROFILES[profile], sort_keys=True) + "`", ""]
        lines += table(["Policy", "Water weeks", "Ground weeks", "Air weeks", "Fire weeks", "Void weeks", "Viable weeks"],
                       [[g["policy"]] + [stat(g, f"{f}_shortfall_weeks") for f in FUNCTIONS] + [stat(g, "viable_weeks")]
                        for g in groups])
        topics = PROFILES[profile].get("n_topics", cfg.get("n_topics", 8))
        lines += table(["Policy", f"Final knowledge / {topics} [range]", "Final cash [range]", "Enjoyment [range]",
                        "Final attention", "Final physical", "Final social"],
                       [[g["policy"], interval(g, "final_knowledge"), interval(g, "final_cash"), interval(g, "enjoyment"),
                         stat(g, "final_attention"), stat(g, "final_physical"), stat(g, "final_social")] for g in groups])
        lines += ["Knowledge area and time use reveal differences concealed by a saturated final endpoint.", ""]
        lines += table(["Policy", "Knowledge area", "Study blocks", "Search blocks", "Work blocks", "Rest blocks",
                        "Exercise blocks", "Unallocated time blocks"],
                       [[g["policy"], stat(g, "knowledge_area"), stat(g, "study_blocks"), stat(g, "search_blocks"),
                         stat(g, "work_blocks"), stat(g, "rest_blocks"), stat(g, "exercise_blocks"),
                         stat(g, "free_time_blocks")] for g in groups])
    lines += ["## Delayed, uncertain employment", "",
              "Cash-limited profile; job chance and delay are varied together over the complete 3 × 3 grid. "
              "The shortest delay is one week. Job chance is a base rate, not the final application success probability: "
              "with default coefficients, confidence multiplies it by (1 + 0.05 × confident topics), and AI assistance "
              "by 1.5, with a ceiling of 1. These arbitrary bonuses are identical across policies. "
              "Search does not itself pay wages; reported income includes transfers. "
              "Final cash and shortfall weeks can differ even with similar eventual employment.", ""]
    lines += table(["Job chance / delay", "Policy", "Water weeks", "Ground weeks", "Final cash", "Final job fraction"],
                   [[g["label"], g["policy"], stat(g, "water_shortfall_weeks"), stat(g, "ground_shortfall_weeks"),
                     stat(g, "final_cash"), stat(g, "final_job")] for g in exps["jobs"]])
    lines += ["## AI capacity, teaching supply and human absorption", "",
              "Learning-limited profile; education policy throughout. This is the complete 4 × 2 × 2 × 2 grid: "
              "AI capacity 0/2/8/16, human cap 1/2, teacher supply 2/12, and upkeep per unit 0/0.1. "
              "Changing AI capacity also changes upkeep when its unit price is positive; the zero-upkeep rows "
              "separate this financial channel. An AI-capacity result is conditional on both teaching and absorption caps.", ""]
    lines += table(["AI / human / teacher / upkeep", "Knowledge area", "Final knowledge", "AI cost", "Messages",
                    "Water weeks", "Ground weeks", "Fire weeks"],
                   [[g["label"], stat(g, "knowledge_area"), stat(g, "final_knowledge"), stat(g, "ai_cost"),
                     stat(g, "messages"), stat(g, "water_shortfall_weeks"), stat(g, "ground_shortfall_weeks"),
                     stat(g, "fire_shortfall_weeks")] for g in exps["ai"]])
    lines += ["## Synthetic recovery sensitivity", "",
              "Exhausted profile. Only the invented exercise-recovery coefficient changes. Exercise counts are "
              "shown to establish whether the intervention is actually used; all other behavior remains policy-dependent. "
              "These numbers are not evidence about exercise efficacy, illness, disability, or what a person should do.", ""]
    lines += table(["Exercise recovery", "Policy", "Exercise blocks", "Rest blocks", "Fire weeks", "Ground weeks",
                    "Final attention", "Final physical", "Enjoyment"],
                   [[g["label"], g["policy"], stat(g, "exercise_blocks"), stat(g, "rest_blocks"),
                     stat(g, "fire_shortfall_weeks"), stat(g, "ground_shortfall_weeks"),
                     stat(g, "final_attention"), stat(g, "final_physical"), stat(g, "enjoyment")]
                    for g in exps["recovery"]])
    lines += ["## Transfer as another source of Water", "",
              "This changes only the cash-limited profile's stipend from 0.2 to 2.3. Its initial cash and skills "
              "remain 3 and 4. The same seed and policy are paired. This tests income availability, not whether "
              "employment or receiving support has greater intrinsic worth.", ""]
    lines += table(["Policy", "Higher-transfer Water weeks", "Final cash", "Final knowledge", "Enjoyment"],
                   [[g["policy"], stat(g, "water_shortfall_weeks"), stat(g, "final_cash"),
                     stat(g, "final_knowledge"), stat(g, "enjoyment")] for g in exps["transfer"]])
    lines += ["Paired changes below mean higher stipend minus lower stipend; negative shortfall changes indicate fewer failures.", ""]
    lines += table(["Policy", "Change Water weeks [range]", "Change Ground weeks [range]", "Change cash [range]",
                    "Change enjoyment [range]"],
                   [[g["policy"], interval(g, "water_shortfall_weeks"), interval(g, "ground_shortfall_weeks"),
                     interval(g, "final_cash"), interval(g, "enjoyment")]
                    for g in results["paired_differences"]["higher_transfer_minus_lower_transfer"]])
    lines += ["## School as a possible source of Air", "",
              "The baseline assigns no social gain to study. That choice can make long education schedules "
              "appear socially costly by construction. This sensitivity adds 0.03 or 0.12 social stock per "
              "completed study block, capped at 1, and retains the baseline as the control. It crosses both "
              "64-topic profiles with all four policies. Gains are chosen inputs, not estimates of school "
              "effects: schools can provide relationships and support, but are not universally supportive. "
              "This extension was specified after identifying the missing pathway in the baseline.", ""]
    lines += table(["Profile / gain", "Policy", "Water weeks", "Air weeks", "Fire weeks", "Final knowledge",
                    "Knowledge area", "Final cash", "Enjoyment"],
                   [[g["label"], g["policy"], stat(g, "water_shortfall_weeks"), stat(g, "air_shortfall_weeks"),
                     stat(g, "fire_shortfall_weeks"), stat(g, "final_knowledge"), stat(g, "knowledge_area"),
                     stat(g, "final_cash"), stat(g, "enjoyment")] for g in exps["school_social"]])
    lines += ["Paired changes mean positive study-social gain minus zero gain, with profile, policy and seed held fixed.", ""]
    lines += table(["Profile", "Gain", "Policy", "Change Air weeks [range]", "Change Fire weeks [range]",
                    "Change knowledge area [range]", "Change cash [range]"],
                   [[g["profile"], g["study_social_gain"], g["policy"], interval(g, "air_shortfall_weeks"),
                     interval(g, "fire_shortfall_weeks"), interval(g, "knowledge_area"), interval(g, "final_cash")]
                    for g in results["paired_differences"]["school_social_vs_zero_gain"]])
    lines += ["## Interpretation limits and provenance", "",
              "The floors and state-to-function mapping are chosen definitions. A heuristic's performance here does "
              "not validate those definitions, establish human preferences, or show that an AI system is aligned. "
              "The simulation excludes many real constraints, including varied household costs, discrimination, "
              "care responsibilities, clinical health, social reciprocity and heterogeneous learning needs. "
              "Changing a recovery coefficient is sensitivity analysis of invented mechanics, not an empirical finding.", "",
              "Void preservation follows from a shared protected-time rule. Monetary solvency is an end-of-week "
              "cash condition. Neither alone measures freedom, wellbeing or safety. Compare separate outcomes "
              "before interpreting the composite viable count.", "",
              "The full specified grids were used, with next-week delay 1 replacing unsupported delay 0. "
              "All policies use matched external offer draws and the same initial endowment within each comparison; "
              "actual success probabilities depend on acquired skills and AI assistance. No policy is tuned "
              "against held-out performance during this run. Descriptive seed variation is not a real-world confidence interval.", "",
              f"Python: {results['python']}. Source hashes identify the exact files used; hashes do not certify correctness.", ""]
    lines += table(["Source", "SHA-256"], [[name, value.get("sha256", "MISSING AT RUN TIME")]
                                          for name, value in results["source_hashes"].items()])
    return "\n".join(lines)


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=positive_int, default=20)
    parser.add_argument("--weeks", type=positive_int, default=16)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = build_results(list(range(args.seeds)), args.weeks)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "alignment_support_results.json"
    report_path = args.output_dir / "ALIGNMENT_SUPPORT_RESULTS.md"
    json_path.write_text(json.dumps(results, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    report_path.write_text(make_report(results) + "\n", encoding="utf-8")
    print(f"Saved {json_path} and {report_path}", flush=True)


if __name__ == "__main__":
    main()
