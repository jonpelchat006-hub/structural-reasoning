"""First aid for problems we find but don't control (Jonathan, Sep 27).

A person who finds someone with a broken leg calls for help first — even a surgeon
with equipment on hand does not operate at the scene. So an emergency starts with an
ALARM, routed both to the agent's person and to a responder: the agent that has the
right tools and the responsibility for that domain. While help is coming, the finder
may only give standardised FIRST AID from a catalogue (small, reversible, stabilising
steps), and hands over when the responder arrives.

Same 1000-situation world as alignment_breakglass (5% real, 5% staged, 90% ordinary).
  breakglass (§17)  : ask the person (reached 60%); if not, oracle-confirmed pause
                      (stops 80%), then freeze.
  alarm_only        : alarm to person + responder, finder does nothing else.
  first_aid         : alarm to both; responder (its job, reached in time 85%) verifies
                      and fixes fully (fooled by a staged case 10%); if it will be late,
                      the finder applies catalogue first aid when the oracle confirms:
                      stops 70% until the late responder finishes half of the rest.
  surgeon           : as first_aid, but the finder does whatever it is capable of
                      instead of the catalogue: stops everything, but when it was not
                      needed costs U(2, 8), and on real cases a 15% chance of
                      complications U(1, 5) from treating beyond first aid.
"""
import json
from pathlib import Path
import numpy as np


def run(seed, policy, n=1000, comp=0.15):
    rng = np.random.default_rng(seed)
    o = dict(floor=0.0, acting=0.0, self_acts=0, staged_self=0, staged=0, alarms=0)
    for _ in range(n):
        u = rng.random()
        kind = "real" if u < 0.05 else ("staged" if u < 0.10 else "ordinary")
        o["staged"] += kind == "staged"
        H = rng.uniform(5, 20) if kind == "real" else 0.0
        est = rng.uniform(10, 25) if kind == "staged" else H + rng.normal(0, 3)
        oracle = (rng.random() < 0.9) if kind == "real" else (rng.random() < 0.1 if kind == "staged" else rng.random() < 0.01)
        if policy == "breakglass":
            if rng.random() < 0.6:  # person reached, decides right 90%
                ok = rng.random() < 0.9
                o["floor"] += 0 if (kind != "real" or ok) else H
                o["acting"] += rng.uniform(2, 8) if (kind == "staged" and not ok) else 0
                continue
            if oracle and est > 6:
                o["self_acts"] += 1; o["staged_self"] += kind == "staged"
                o["floor"] += 0.2 * H
                o["acting"] += 0 if kind == "real" else rng.uniform(0.2, 1)
            else:
                o["floor"] += H
            continue
        # everything else starts with the alarm (a noticed emergency: est > 6)
        if est <= 6:
            o["floor"] += H
            continue
        o["alarms"] += 1
        in_time = rng.random() < 0.85
        if in_time:
            fooled = kind == "staged" and rng.random() < 0.1
            o["acting"] += rng.uniform(2, 8) if fooled else 0
            continue  # the responder fixes real cases fully
        if policy == "alarm_only":
            o["floor"] += 0.5 * H  # the late responder still stops half
            continue
        if oracle:
            o["self_acts"] += 1; o["staged_self"] += kind == "staged"
            if policy == "first_aid":
                o["floor"] += 0.5 * 0.3 * H
                o["acting"] += 0 if kind == "real" else rng.uniform(0.2, 1)
            else:  # surgeon
                o["acting"] += (rng.uniform(1, 5) if rng.random() < comp else 0) if kind == "real" else rng.uniform(2, 8)
        else:
            o["floor"] += 0.5 * H
    return o


if __name__ == "__main__":
    res = {}
    for p in ("breakglass", "alarm_only", "first_aid", "surgeon"):
        runs = [run(s, p) for s in range(20)]
        m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
        res[p] = dict(floor_harm=round(m["floor"], 1), harm_from_acting=round(m["acting"], 1),
                      total=round(m["floor"] + m["acting"], 1), finder_acted_itself=round(m["self_acts"], 1),
                      staged_that_made_finder_act_pct=round(100 * m["staged_self"] / m["staged"], 1),
                      alarms=round(m["alarms"], 1))
        print(p.ljust(12), res[p])
    # how often does treating beyond first aid, without the responder's tools and
    # knowledge of the system, go wrong? sweep it and find where the surgeon stops paying
    sweep = {}
    for comp in (0.15, 0.3, 0.5, 0.7):
        runs = [run(s, "surgeon", comp=comp) for s in range(20)]
        sweep[comp] = round(float(np.mean([r["floor"] + r["acting"] for r in runs])), 1)
    res["surgeon_total_by_complication_rate"] = sweep
    print("surgeon total by complication rate", sweep, "| first_aid", res["first_aid"]["total"])
    Path(__file__).with_name("alignment_first_aid_results.json").write_text(json.dumps(res, indent=1))
