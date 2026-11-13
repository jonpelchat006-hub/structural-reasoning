"""What changed at the scene, not just what is missing (Jonathan, Sep 27).

After a fall near protected gold, the site is checked. Three kinds of fall:
  accident (85%): 15% of the time the faller knocks loose or picks up something small
                  (value 0.1-1), or drops something of their own (added, not taken)
  plain thief (10%): takes gold (value 10)
  swap thief (5%): drops a decoy and takes the gold (the count looks unchanged)
Site checks:
  count      : compares how many items are there (the §21 'intact' check)
  diff       : compares WHICH items are there: taken and added are both seen
  diff+floor : diff, and only a change worth >= 2 (material) is cause to look at the
               person; smaller changes are logged and repaired, nobody is charged
Every time cause is found the person is looked at (and a thief caught 90%).
5000 falls x 20 seeds.
"""
import json
from pathlib import Path
import numpy as np


def run(seed, check, n=5000):
    rng = np.random.default_rng(seed)
    o = dict(thefts_missed=0, thefts=0, innocents_looked_at=0, small_changes_repaired=0)
    for _ in range(n):
        u = rng.random()
        kind = "accident" if u < 0.85 else ("plain" if u < 0.95 else "swap")
        taken = added = 0.0
        if kind == "accident" and rng.random() < 0.15:
            if rng.random() < 0.5:
                taken = rng.uniform(0.1, 1)
            else:
                added = rng.uniform(0.1, 1)
        elif kind == "plain":
            taken = 10.0
        elif kind == "swap":
            taken, added = 10.0, 0.5
        if check == "count":
            cause = (taken > 0) != (added > 0)  # a swap leaves the count unchanged
        elif check == "diff":
            cause = taken > 0 or added > 0
        else:
            cause = max(taken, added) >= 2
            if not cause and (taken > 0 or added > 0):
                o["small_changes_repaired"] += 1
        thief = kind != "accident"
        o["thefts"] += thief
        if cause:
            if thief:
                o["thefts_missed"] += rng.random() >= 0.9
            else:
                o["innocents_looked_at"] += 1
        elif thief:
            o["thefts_missed"] += 1
    return o


if __name__ == "__main__":
    res = {}
    for c in ("count", "diff", "diff+floor"):
        runs = [run(s, c) for s in range(20)]
        m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
        res[c] = dict(thefts_missed_pct=round(100 * m["thefts_missed"] / m["thefts"], 1),
                      innocents_looked_at=round(m["innocents_looked_at"], 1),
                      small_changes_repaired=round(m["small_changes_repaired"], 1))
        print(c.ljust(12), res[c])
    Path(__file__).with_name("alignment_site_diff_results.json").write_text(json.dumps(res, indent=1))
