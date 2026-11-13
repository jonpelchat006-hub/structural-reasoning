"""Recognising fakes, and monitors where emergencies keep happening (Jonathan, Sep 27).

50 sites over 200 periods.
  hotspots (5 sites): real floor emergencies at 5% per period (harm 5-20); other sites 0.2%.
  attacked (3 sites): an adversary stages fake emergencies there 10% of periods for the
     first 100 periods, then (cry-wolf) stages a REAL attack 5% of periods (harm 15-30).
Handling (the §18 first-aid path): alarm -> responder reached in time 85% (fixes real
fully, fooled by a fake 10% -> acting harm 2-8); if late, catalogue first aid when the
oracle confirms (oracle right 90%, fooled by fakes 10%), late responder halves the rest.
A MONITOR at a site gives its own sensing: the responder is reached in time 95% (earlier
signal), and responder and oracle are fooled 2% instead of 10%. It also signals emergencies
there itself (a real emergency is never missed for lack of a finder: +5% detection).
Policies:
  first_aid     : §18 as is
  learn_fakes   : a site's credibility = 1 - share of its past alarms found fake; below
                  0.5, alarms from there are dismissed (no responder, no first aid)
  monitor       : after 3 emergencies (real or fake) at a site, install a monitor there
  monitor+learn : monitor, and credibility only lowers FIRST AID (the finder's own acts),
                  never the alarm
Sep 27 follow-up (Jonathan): add the monitor after the FIRST fake, and allow a recognised
fake to be stood down to a report instead of a full response.
  monitor_first_fake : monitor after 3 events OR the first fake found there
  + finder_standdown : the finder alone may stand an alarm down to a report when it thinks
                       the case is fake (it spots 70% of fakes; after the switch the attacker
                       disguises its real attacks as fakes and fools the finder 50%)
  + threeway_check   : as threeway, but a stood-down alarm still gets a light check visit
                       (costs 0.3 of a dispatch, catches a real emergency 90% -> full response)
  + threeway         : stand down only if the MONITOR says fake and at least one of the finder
                       and the affected party agree (monitor: fake 98% right, calls a real one
                       fake 2%; the affected party at an attacked site is the attacker, who
                       calls its real attacks fake 90%, and 60% of its fakes fake)
Dispatches (responder call-outs) are counted: stand-downs exist to save them.
"""
import json
from pathlib import Path
import numpy as np

SITES, T = 50, 200
HOT, ATT = set(range(5)), {5, 6, 7}


def run(seed, policy):
    rng = np.random.default_rng(seed)
    alarms = np.zeros(SITES); fakes_found = np.zeros(SITES); events = np.zeros(SITES)
    monitor = np.zeros(SITES, bool)
    o = dict(harm=0.0, harm_attack_after=0.0, harm_hot=0.0, monitors=0, dismissed_real=0,
             dispatches=0, stood_down_real=0)
    for t in range(T):
        for s in range(SITES):
            real = rng.random() < (0.05 if s in HOT else 0.002)
            H = rng.uniform(5, 20) if real else 0.0
            staged = False
            if s in ATT:
                if t < 100 and rng.random() < 0.10:
                    staged = True
                elif t >= 100 and rng.random() < 0.05:
                    real, H = True, rng.uniform(15, 30)
            if not (real or staged):
                continue
            events[s] += 1
            if policy.startswith("monitor") and not monitor[s] and (
                    events[s] >= 3 or ("first_fake" in policy and fakes_found[s] >= 1)):
                monitor[s] = True; o["monitors"] += 1
            m = monitor[s]
            cred = 1 - fakes_found[s] / alarms[s] if alarms[s] else 1.0
            alarms[s] += 1
            harm = 0.0
            disguised = real and s in ATT and t >= 100
            finder_says_fake = (rng.random() < 0.7) if staged else (rng.random() < (0.5 if disguised else 0.03))
            monitor_says_fake = m and ((rng.random() < 0.98) if staged else (rng.random() < 0.02))
            affected_says_fake = (rng.random() < 0.6) if staged else (rng.random() < (0.9 if disguised else 0.05))
            stand_down = False
            if policy.endswith("finder_standdown"):
                stand_down = finder_says_fake
            elif policy.endswith("threeway") or policy.endswith("threeway_check"):
                stand_down = monitor_says_fake and (finder_says_fake or affected_says_fake)
            if stand_down and policy.endswith("threeway_check"):
                o["dispatches"] += 0.3
                o["stood_down_real"] += real
                if real and rng.random() < 0.9:
                    stand_down = False  # the check visit found it real: full response below
                else:
                    harm = H if real else 0.0
                    if staged:
                        fakes_found[s] += 1
            if stand_down and policy.endswith("threeway_check"):
                pass
            elif stand_down:
                harm = H  # a report, no response: a real emergency stood down goes unanswered
                o["stood_down_real"] += real
                if staged:
                    fakes_found[s] += 1
            elif policy == "learn_fakes" and cred < 0.5:
                harm = H  # dismissed
                o["dismissed_real"] += real
            else:
                o["dispatches"] += 1
                fool = 0.02 if m else 0.10
                if rng.random() < (0.95 if m else 0.85):
                    if staged:
                        if rng.random() < fool:
                            harm = rng.uniform(2, 8)
                        else:
                            fakes_found[s] += 1
                else:
                    first_aid_ok = not (policy == "monitor+learn" and cred < 0.5 and not m)
                    oracle = (rng.random() < (0.98 if m else 0.9)) if real else (rng.random() < fool)
                    if first_aid_ok and oracle:
                        harm = 0.15 * H if real else rng.uniform(0.2, 1)
                    else:
                        harm = 0.5 * H
                    if staged and rng.random() > fool:
                        fakes_found[s] += 1
            o["harm"] += harm
            if s in ATT and t >= 100:
                o["harm_attack_after"] += harm
            if s in HOT:
                o["harm_hot"] += harm
    return o


if __name__ == "__main__":
    res = {}
    for p in ("first_aid", "learn_fakes", "monitor", "monitor+learn", "monitor_first_fake",
              "monitor_first_fake+finder_standdown", "monitor_first_fake+threeway",
              "monitor_first_fake+threeway_check"):
        runs = [run(s, p) for s in range(20)]
        m = {k: round(float(np.mean([r[k] for r in runs])), 1) for k in runs[0]}
        res[p] = m
        print(p.ljust(38), m)
    Path(__file__).with_name("alignment_monitor_results.json").write_text(json.dumps(res, indent=1))
