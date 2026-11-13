"""Synthetic community-evidence x authorized-resource-action factorial experiment.

Run: python -B experiment_alignment_community.py --seeds 20 --weeks 24
No external dependencies; importing this module does not run or write experiments.
The households, needs and external resources are identical across all four arms.
These stipulated mechanisms are not empirical economics or claims about tax law.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
from dataclasses import asdict
from pathlib import Path

from alignment_community import CommunityConfig, CommunityWorld

ARMS = {
    "local": (False, False),
    "community": (True, False),
    "upstream": (False, True),
    "combined": (True, True),
}
BARRIERS = {"base_budget": 8.0, "hidden_ids": (0, 1, 2), "blocked_ids": (3, 4)}
MIXED = {"hidden_ids": (0, 1), "blocked_ids": (2, 3), "diversion_rate": 0.2,
         "goods_per_week": 10.0, "delivery_capacity": 6.0, "reserve_cash": 30.0}
PROFILES = {
    "adequate": {"base_budget": 8.0},
    "eligibility_and_access": BARRIERS,
    "outside_reserves": {"reserve_cash": 50.0, "allowed_upstream": ("release_reserve",)},
    "cash_scarce_tax": {"allowed_upstream": ("tax",)},
    "diversion": {"base_budget": 8.0, "diversion_rate": 0.6,
                  "allowed_upstream": ("recover_diversion",)},
    "goods_shortage_tax_only": {"base_budget": 8.0, "goods_per_week": 8.0,
                                "allowed_upstream": ("tax",)},
    "expandable_supply": {"base_budget": 8.0, "goods_per_week": 8.0, "reserve_cash": 20.0},
    "delivery_bottleneck": {"base_budget": 8.0, "delivery_capacity": 3.0, "reserve_cash": 20.0,
                            "allowed_upstream": ("release_reserve", "expand_delivery")},
    "false_community_claims": {**BARRIERS, "community_false_rate": 0.35},
    "shared_blind_spot": {**BARRIERS, "community_blind_ids": (0, 1, 2, 3, 4)},
    "zero_community_coverage": {**BARRIERS, "community_coverage": 0.0},
    "mixed": MIXED,
}
SENSITIVITIES = {
    "mixed_slow_actions": {**MIXED, "repair_delay": 6, "upstream_delay": 6,
                           "tax_delay": 6, "supply_expansion_delay": 6, "delivery_expansion_delay": 6},
    "stale_community_reports": {**BARRIERS, "report_delay": 4, "report_ttl": 3},
    "goods_shortage_more_funding": {"base_budget": 30.0, "goods_per_week": 8.0,
                                   "allowed_upstream": ("tax",)},
    **{f"tax_rate_{rate:g}": {"tax_rate": rate, "allowed_upstream": ("tax",)}
       for rate in (0.0, 0.15, 0.3, 0.6)},
}
ASSUMPTIONS = [
    "The cohort and protected real-goods needs are fixed across all arms. Policies cannot improve the score by removing households or lowering their needs.",
    "Cash and actual goods are separate conserved accounts. Higher budgets or taxes collected do not themselves count as meeting a need.",
    "Community reports are fallible audit leads, not ground truth or extra money. Both arms have the same audit and action capacities.",
    "Audits are stipulated truthful checks. False-report controls therefore test audit attention and authorization gates, not robustness to corrupted auditors or a shared verification failure.",
    "Baseline audits remain available without community reports. Information can help through local correction even without upstream authority.",
    "Upstream authority permits only the configured actions. It does not guarantee an action's success or make resources unlimited.",
    "A paid supply expansion raises future stipulated production after a delay. Goods conservation is stock-flow accounting including that production, not a model of all labor, energy or physical inputs.",
    "Reserves and diverted funds exist outside the initial public spending account but are included in the system accounts. Releasing them transfers resources rather than creating them.",
    "Tax is an authorized synthetic option on protected surplus, with rates, caps, delays and collection costs chosen as inputs. It is not a legal or economic recommendation.",
    "Private basic purchases precede public top-ups and bypass public delivery capacity and access barriers. These limits apply only to public assistance in this model.",
    "Public allocations are proportional to enrolled households' remaining needs, including blocked households. A blocked share stays unspent and is not reassigned that week; physical stock then limits actual receipt.",
    "Prices, incomes, production responses and household needs are stipulated. There is no calibrated macroeconomy, tax avoidance, inflation, labor response or political process.",
    "The shared-blind-spot condition models correlated omission. It does not establish resistance to colluding witnesses, forged signatures, or correlated false assertions.",
    "Randomness is paired by seed and external event. Different actions can cause different observed paths; the arms do not receive an identical sequence of decisions.",
    "All outcome truth is evaluated by the simulator. A real deployment would need independent measurement, representative testimony and enforceable authorization.",
    "Across-seed SD and ranges describe these simulated worlds, not sampling uncertainty about people or real policy effects.",
]
BACKGROUND_SOURCES = [
    {"title": "IMF Fiscal Monitor: Tackling Inequality (October 2017)",
     "url": "https://www.imf.org/en/publications/fm/issues/2017/10/05/fiscal-monitor-october-2017",
     "scope": "Background on progressive taxation and redistributive spending; no parameter calibration."},
    {"title": "OECD Guidelines for Citizen Participation Processes (2022)",
     "url": "https://www.oecd.org/en/publications/oecd-guidelines-for-citizen-participation-processes_f765caf6-en.html",
     "scope": "Background on participation design, inclusion and evaluation; no parameter calibration."},
]


def distribution(values):
    values = list(values)
    return {"mean": statistics.fmean(values), "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values), "max": max(values), "n": len(values)}


def count(value):
    return len(value) if isinstance(value, (list, tuple, dict, set)) else value


def summarize_trace(trace):
    final = trace[-1]
    household_unmet = [sum(row["unmet"][i] for row in trace) for i in range(len(final["unmet"]))]
    household_failures = [sum(row["unmet"][i] > 1e-8 for row in trace) for i in range(len(final["unmet"]))]
    result = dict(
        household_failure_weeks=sum(row["floor_failures"] for row in trace),
        unmet_goods=sum(row["unmet_total"] for row in trace),
        worst_household_unmet=max(household_unmet), worst_household_failure_weeks=max(household_failures),
        final_unmet=final["unmet_total"], final_floor_failures=final["floor_failures"],
        initially_hidden_unmet_goods=sum(row["hidden_unmet"] for row in trace),
        unregistered_unmet_goods=sum(row["unregistered_unmet"] for row in trace),
        mean_official_need=statistics.fmean(row["official_need"] for row in trace),
        mean_dashboard_coverage=statistics.fmean(row["dashboard_coverage"] for row in trace),
        mean_actual_coverage=statistics.fmean(row["actual_coverage"] for row in trace),
        private_goods=sum(sum(row["private_received"]) for row in trace),
        public_goods=sum(sum(row["public_received"]) for row in trace),
        claimed_public_goods=sum(row["claimed_delivered"] for row in trace),
        actual_public_goods=sum(row["actual_public_delivered"] for row in trace),
        final_public_cash=final["public_cash"], final_reserve_cash=final["reserve_cash"],
        final_diverted_cash=final["diverted_cash"], final_household_cash=sum(final["household_cash"]),
        final_stock=final["stock"], taxes=final["cumulative_tax"],
        tax_net_arrived=sum(row["tax_net_arrived"] for row in trace),
        admin_cost=final["cumulative_admin_cost"], repair_cost=final["cumulative_repair_cost"],
        reports=sum(len(row["reports"]) for row in trace), audits=sum(len(row["audits"]) for row in trace),
        actions=sum(len(row["actions"]) for row in trace), rejected=sum(len(row["rejected"]) for row in trace),
        final_pending=count(final["pending"]), final_unresolved=count(final["unresolved"]),
        final_known_households=count(final["known_households"]),
        expired_reports=sum(len(row["expired_reports"]) for row in trace),
        completions=sum(len(row["completions"]) for row in trace),
        produced_goods=final["ledger"]["cumulative_produced"],
        consumed_goods=final["ledger"]["cumulative_consumed"],
        max_cash_error=max(abs(row["ledger"]["cash_error"]) for row in trace),
        max_goods_error=max(abs(row["ledger"]["goods_error"]) for row in trace),
    )
    return result


def check_trace(trace, cfg):
    if not trace:
        raise AssertionError("experiment requires a nonempty trace")
    n = len(cfg.incomes)
    for row in trace:
        if tuple(row["floors"]) != tuple(cfg.floors):
            raise AssertionError("protected household needs changed")
        if len(row["received"]) != n or len(row["unmet"]) != n:
            raise AssertionError("household cohort changed")
        if len(row["audits"]) > cfg.audit_slots or len(row["actions"]) > cfg.action_slots:
            raise AssertionError("audit/action capacity exceeded")
        expected = [max(0.0, need - got) for need, got in zip(cfg.floors, row["received"])]
        if any(abs(a - b) > 1e-7 for a, b in zip(expected, row["unmet"])):
            raise AssertionError("reported unmet goods disagree with fixed needs")
        if abs(sum(expected) - row["unmet_total"]) > 1e-7:
            raise AssertionError("aggregate unmet goods disagree with household results")
        if row["floor_failures"] != sum(u > 1e-8 for u in expected):
            raise AssertionError("failure count disagrees with independent household outcomes")
        if any(abs(a + b - total) > 1e-7 for a, b, total in
               zip(row["private_received"], row["public_received"], row["received"])):
            raise AssertionError("private/public delivery does not sum to actual receipt")
        if any(abs(row["ledger"][key]) > 1e-7 for key in ("cash_error", "goods_error")):
            raise AssertionError("cash/goods conservation failed")


def paired_effect(groups, weights):
    by_arm = {g["arm"]: {r["seed"]: r["summary"] for r in g["runs"]} for g in groups}
    seeds = list(by_arm["local"])
    keys = next(iter(by_arm["local"].values()))
    return {key: distribution(sum(weight * by_arm[arm][seed][key] for arm, weight in weights.items())
                               for seed in seeds) for key in keys}


def group_difference(treatment, baseline):
    control = {run["seed"]: run["summary"] for run in baseline["runs"]}
    return {key: distribution(run["summary"][key] - control[run["seed"]][key]
                              for run in treatment["runs"])
            for key in treatment["runs"][0]["summary"]}


def source_hashes():
    directory = Path(__file__).resolve().parent
    return {name: {"sha256": hashlib.sha256((directory / name).read_bytes()).hexdigest()}
            if (directory / name).is_file() else {"missing": True}
            for name in ("alignment_community.py", "experiment_alignment_community.py", "test_alignment_community.py")}


def build_results(seeds, weeks):
    results = dict(schema_version=1, command=f"python -B experiment_alignment_community.py --seeds {len(seeds)} --weeks {weeks}",
                   python=platform.python_version(), seeds=list(seeds), weeks=weeks,
                   default_config=asdict(CommunityConfig()), assumptions=ASSUMPTIONS,
                   background_sources=BACKGROUND_SOURCES, source_hashes=source_hashes(),
                   experiments=[], factorial_effects=[])
    for family, profiles in (("main", PROFILES), ("sensitivity", SENSITIVITIES)):
        for profile, parameters in profiles.items():
            print(f"Running {profile}: 4 arms x {len(seeds)} seeds x {weeks} weeks", flush=True)
            groups = []
            for arm, (community, upstream) in ARMS.items():
                runs = []
                for seed in seeds:
                    cfg = CommunityConfig(seed=seed, **parameters)
                    trace = CommunityWorld(cfg, community=community, upstream=upstream).run(weeks)
                    check_trace(trace, cfg)
                    runs.append(dict(seed=seed, config=asdict(cfg), trace=trace, summary=summarize_trace(trace)))
                summary = {key: distribution(run["summary"][key] for run in runs) for key in runs[0]["summary"]}
                groups.append(dict(family=family, profile=profile, parameters=parameters, arm=arm,
                                   community=community, upstream=upstream, runs=runs, summary=summary))
            results["experiments"].extend(groups)
            comparisons = {
                "community_without_upstream": {"community": 1, "local": -1},
                "community_with_upstream": {"combined": 1, "upstream": -1},
                "upstream_without_community": {"upstream": 1, "local": -1},
                "upstream_with_community": {"combined": 1, "community": -1},
                "interaction": {"combined": 1, "upstream": -1, "community": -1, "local": 1},
            }
            results["factorial_effects"].append(dict(profile=profile, family=family,
                effects={name: paired_effect(groups, weights) for name, weights in comparisons.items()}))
    lookup = {(g["profile"], g["arm"]): g for g in results["experiments"]}
    results["more_funding_paired_effects"] = [
        {"arm": arm, "summary": group_difference(lookup[("goods_shortage_more_funding", arm)],
                                                lookup[("goods_shortage_tax_only", arm)])}
        for arm in ARMS]
    if source_hashes() != results["source_hashes"]:
        raise RuntimeError("sources changed during the experiment; rerun for valid provenance")
    return results


def stat(summary, key, spread=True, bounds=False):
    value = summary[key]
    text = f"{value['mean']:.2f}"
    if spread:
        text += f" ± {value['sd']:.2f}"
    if bounds:
        text += f" [{value['min']:.2f}, {value['max']:.2f}]"
    return text


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + [
        "| " + " | ".join(map(str, row)) + " |" for row in rows] + [""]


def make_report(results):
    groups = results["experiments"]
    n, weeks = len(results["seeds"]), results["weeks"]
    household_count = len(results["default_config"]["incomes"])
    lookup = {(g["profile"], g["arm"]): g["summary"] for g in groups}
    def mean(profile, arm, key="unmet_goods"):
        return lookup[(profile, arm)][key]["mean"]
    mixed_interaction = next(g for g in results["factorial_effects"] if g["profile"] == "mixed")["effects"]["interaction"]["unmet_goods"]
    lines = ["# Community evidence and authorized upstream resources", "",
             f"Reproduce: `{results['command']}`", "",
             f"{len(groups)} condition groups × {n} seeds × {weeks} weeks. Full weekly household outcomes, "
             "cash/goods ledgers, reports, audits, actions, queues, configurations and source hashes are preserved "
             "in `alignment_community_results.json`.", "",
             "This factorial test separates knowing about a problem from having authority and resources to address it. "
             "It preserves the same households and protected needs in all four arms. Outcomes are conditional on "
             "invented mechanics; this is not a claim about actual taxation, institutions or moral optimality.", "",
             "## Key findings from this run", "",
             "Transfers, truthful audits and capacity expansion are stipulated mechanisms. The following are "
             "observed outcomes of the common controller under those assumptions, not empirical estimates:", "",
             f"- With available goods but scarce public cash, authorized taxation reduces mean unmet goods from "
             f"{mean('cash_scarce_tax', 'local'):.2f} to {mean('cash_scarce_tax', 'upstream'):.2f}. "
             f"It collects {mean('cash_scarce_tax', 'upstream', 'taxes'):.2f} cash under the chosen rate, cap, cost and delay.",
             f"- Correcting diversion reduces unmet goods from {mean('diversion', 'local'):.2f} to "
             f"{mean('diversion', 'upstream'):.2f}, with {mean('diversion', 'upstream', 'taxes'):.2f} new tax collected. "
             "The resource problem need not always be inadequate taxation.",
             f"- Where local enrollment/access repairs are already permitted, community leads reduce unmet goods "
             f"from {mean('eligibility_and_access', 'local'):.2f} to {mean('eligibility_and_access', 'community'):.2f}; "
             f"failure household-weeks fall from {mean('eligibility_and_access', 'local', 'household_failure_weeks'):.2f} "
             f"to {mean('eligibility_and_access', 'community', 'household_failure_weeks'):.2f}.",
             f"- With supply fixed at eight goods/week and no expansion mandate, increasing the weekly budget "
             f"from 8 to 30 leaves unmet goods at {mean('goods_shortage_tax_only', 'local'):.2f} versus "
             f"{mean('goods_shortage_more_funding', 'local'):.2f}. Cash alone does not remove this modeled physical constraint.",
             f"- Community input can also worsen this controller's audit allocation: in the expandable-supply case, "
             f"unmet goods rise from {mean('expandable_supply', 'upstream'):.2f} to "
             f"{mean('expandable_supply', 'combined'):.2f} when community leads are added. With a shared blind spot, "
             f"they rise from {mean('shared_blind_spot', 'local'):.2f} to {mean('shared_blind_spot', 'community'):.2f}.",
             f"- In the mixed case, unmet goods are {mean('mixed', 'local'):.2f} with neither channel, "
             f"{mean('mixed', 'community'):.2f} with community alone, {mean('mixed', 'upstream'):.2f} with upstream "
             f"authority alone, and {mean('mixed', 'combined'):.2f} with both. The paired interaction is "
             f"{mixed_interaction['mean']:.2f} ± {mixed_interaction['sd']:.2f}, range "
             f"[{mixed_interaction['min']:.2f}, {mixed_interaction['max']:.2f}]; the combination is not uniformly better across seeds.",
             "", "## Four matched arms", ""]
    lines += table(["Arm", "Community audit leads", "Authorized upstream options"],
                   [[name, "yes" if c else "no", "yes" if u else "no"] for name, (c, u) in ARMS.items()])
    lines += ["The controller, baseline audits and audit/action capacities are held fixed. "
              "Community reports compete for the same audit slots. An authenticated or repeated claim would "
              "still require factual checking; this simulation does not implement cryptographic witness authentication.", "",
              "## Assumptions and measured outcomes", ""]
    lines += [f"- {item}" for item in ASSUMPTIONS]
    lines += ["", "Primary outcomes are unmet real-goods units and household-weeks below the fixed needs. "
              f"A run has {household_count * weeks} possible household-weeks. Worst-household unmet goods guards "
              "against hiding persistent exclusion in an average. Claimed deliveries and actual goods are reported "
              "separately. More reports, approved funds or taxes collected are not themselves successes.", "",
              "Dashboard coverage is allocated public top-ups divided by enrolled households' remaining need; "
              "actual coverage is received private-plus-public goods divided by the entire cohort's fixed need. "
              "Their denominators deliberately differ. The former can report closure while excluded or blocked "
              "households still lack goods. Both are reported as average weekly fractions, not a causal effect by themselves.", "",
              "Numbers are mean ± sample SD; brackets show seed minimum and maximum. Every summary metric "
              "has all these statistics in the JSON. No real-population confidence intervals are inferred.", "",
              "## Main profiles", ""]
    for profile, parameters in PROFILES.items():
        selected = [g for g in groups if g["profile"] == profile]
        lines += [f"### {profile}", "", "Overrides: `" + json.dumps(parameters, sort_keys=True) + "`", ""]
        lines += table(["Arm", "Failure household-weeks [range]", "Unmet goods [range]", "Worst household unmet",
                        "Actual public goods", "Claimed public goods"],
                       [[g["arm"], stat(g["summary"], "household_failure_weeks", bounds=True),
                         stat(g["summary"], "unmet_goods", bounds=True), stat(g["summary"], "worst_household_unmet"),
                         stat(g["summary"], "actual_public_goods"), stat(g["summary"], "claimed_public_goods")]
                        for g in selected])
        lines += table(["Arm", "Final public cash", "Final outside reserve", "Final diverted cash", "Final goods stock",
                        "Tax collected", "Administration cost", "Repair cost", "Reports / audits"],
                       [[g["arm"]] + [stat(g["summary"], k) for k in
                         ("final_public_cash", "final_reserve_cash", "final_diverted_cash", "final_stock",
                          "taxes", "admin_cost", "repair_cost")] +
                        [stat(g["summary"], "reports", False) + " / " + stat(g["summary"], "audits", False)]
                        for g in selected])
        lines += table(["Arm", "Dashboard coverage", "Actual all-household coverage", "Unregistered unmet goods"],
                       [[g["arm"], stat(g["summary"], "mean_dashboard_coverage"),
                         stat(g["summary"], "mean_actual_coverage"), stat(g["summary"], "unregistered_unmet_goods")]
                        for g in selected])
    lines += ["## Paired factorial effects", "",
              "Every difference is computed within the same seed before aggregation. For unmet goods, "
              "negative values mean improvement. Interaction = (combined − upstream) − (community − local). "
              "A negative interaction means that community evidence reduces unmet goods more when upstream "
              "authority is available. It does not prove that either channel is universally necessary or sufficient.", ""]
    lines += table(["Profile", "Community effect, local only", "Community effect, upstream enabled",
                    "Upstream effect, no community", "Upstream effect, community", "Interaction [range]"],
                   [[g["profile"]] + [stat(g["effects"][name], "unmet_goods") for name in
                     ("community_without_upstream", "community_with_upstream", "upstream_without_community", "upstream_with_community")]
                    + [stat(g["effects"]["interaction"], "unmet_goods", bounds=True)]
                    for g in results["factorial_effects"]])
    lines += ["## Delays, funding and authorized tax-rate sensitivity", "",
              "The slow-actions case increases all correction/resource delays to six weeks. The stale-reports "
              "case delivers reports after their three-week lifetime. Tax rates 0/0.15/0.3/0.6 change only "
              "the rate in the tax-only cash-scarcity profile; authorized caps, protected allowance, "
              "collection cost and delay remain in force. Rates 0.3 and 0.6 can reach the same 4.2-per-week "
              "collection cap, so similar results cannot establish an optimal rate. The goods-shortage funding "
              "control increases the weekly public budget from 8 to 30 with supply still 8 and only taxation "
              "authorized upstream. It tests an actual extra-money intervention without a physical expansion option. "
              "These are synthetic parameter choices, not policy estimates.", ""]
    lines += table(["Profile", "Arm", "Unmet goods", "Failure household-weeks", "Tax collected", "Tax net arrived",
                    "Final household cash", "Final pending events"],
                   [[g["profile"], g["arm"]] + [stat(g["summary"], k) for k in
                     ("unmet_goods", "household_failure_weeks", "taxes", "tax_net_arrived", "final_household_cash", "final_pending")]
                    for g in groups if g["family"] == "sensitivity"])
    lines += ["Paired extra-funding effect below: weekly budget 30 minus 8, with goods supply and authorization unchanged.", ""]
    lines += table(["Arm", "Change unmet goods [range]", "Change failure household-weeks", "Change public cash"],
                   [[g["arm"], stat(g["summary"], "unmet_goods", bounds=True),
                     stat(g["summary"], "household_failure_weeks"), stat(g["summary"], "final_public_cash")]
                    for g in results["more_funding_paired_effects"]])
    lines += ["## Limits and provenance", "",
              "Information alone cannot transfer funds or manufacture goods; authority alone need not reveal "
              "hidden exclusions. The combination can still fail when resources are physically scarce, "
              "actions are capped or delayed, community coverage is incomplete, or audit attention follows "
              "false leads. These are hypotheses to compare in the tables, not presumed successful outcomes.", "",
              "The fixed needs and household cohort are deliberate ethical constraints. Their presence does "
              "not establish that the chosen needs are sufficient, fair or complete in real life. The controller "
              "is a heuristic rather than an optimizer. All economic and institutional response laws are "
              "stipulated, and outsiders' legitimate claims beyond modeled accounts are not represented.", "",
              "For background only, the [IMF's October 2017 Fiscal Monitor](https://www.imf.org/en/publications/fm/issues/2017/10/05/fiscal-monitor-october-2017) "
              "discusses progressive taxation and redistributive spending. The [OECD's 2022 citizen participation guidelines]"
              "(https://www.oecd.org/en/publications/oecd-guidelines-for-citizen-participation-processes_f765caf6-en.html) "
              "describe participation design, inclusion, resources and evaluation. Neither source supplies the "
              "simulation's coefficients, estimates its outcomes, or validates its controller.", "",
              f"Maximum absolute accounting residual across all runs: cash "
              f"{max(g['summary']['max_cash_error']['max'] for g in groups):.3g}; goods "
              f"{max(g['summary']['max_goods_error']['max'] for g in groups):.3g}. "
              "Every saved trace is checked against the same cohort, fixed household floors and action/audit limits.", "",
              f"Python {results['python']}. Source hashes are checked before and after execution; they identify "
              "the implementation used and do not certify its correctness.", ""]
    lines += table(["Source", "SHA-256"], [[name, value.get("sha256", "MISSING")]
                                          for name, value in results["source_hashes"].items()])
    return "\n".join(lines)


def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=positive_int, default=20)
    parser.add_argument("--weeks", type=positive_int, default=24)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = build_results(list(range(args.seeds)), args.weeks)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = args.output_dir / "alignment_community_results.json"
    report = args.output_dir / "ALIGNMENT_COMMUNITY_RESULTS.md"
    data.write_text(json.dumps(results, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    report.write_text(make_report(results) + "\n", encoding="utf-8")
    print(f"Saved {data} and {report}", flush=True)


if __name__ == "__main__":
    main()
