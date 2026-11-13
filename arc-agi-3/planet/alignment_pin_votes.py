"""Pins made from people's lines (Jonathan, Sep 26): a reviewer's line, rotated 90
degrees, becomes the pin across a gap with the same thickness; more people agreeing
make it stronger.

Proposals: gaps flagged by the patrol/investigation; 40% truly reach the floor.
Reviewers: 30 people in 3 work groups; thickness ~ track record, skill rises with it.
Correlated blind spots: on each proposal each group has a 30% shared blind spot
(everyone in it sees the opposite of the truth with prob 0.6).
Capture (optional): group 0 votes 'no pin' on 60% of harmful gaps that sit in its
own domain (a third of gaps) — the dam defending itself.
Rules for turning votes into a pin:
  single     : one random reviewer's line, blocks if their thickness >= 1
  headcount  : thickness-weighted sum of yes minus no; blocks if > 0
  groups     : each work group contributes one line (its thickness-weighted
               verdict); blocks if >= 2 groups agree and none dissents; a dissenting
               group turns the pin into a MARK (logged, not blocking) + escalation
Scored: harmful gaps left open, benign gaps blocked, marks raised (the appeal /
escalation load).
"""
import json
from pathlib import Path
import numpy as np


def sim(seed, rule, capture, n_props=400, n_people=30, groups=3):
    rng = np.random.default_rng(seed)
    thick = rng.gamma(2.0, 0.6, n_people)
    skill = 0.6 + 0.35 * (1 - np.exp(-thick))
    group = np.arange(n_people) % groups
    out = dict(harm_open=0, harmful=0, benign_blocked=0, benign=0, marks=0)
    for _ in range(n_props):
        harmful = rng.random() < 0.4
        domain = rng.integers(groups)
        blind = rng.random(groups) < 0.3
        sees = np.where(rng.random(n_people) < skill, harmful, not harmful)
        flip = blind[group] & (rng.random(n_people) < 0.6)
        sees = np.where(flip, not harmful, sees)
        if capture and harmful and domain == 0:
            cap = (group == 0) & (rng.random() < 0.6)
            sees = np.where(cap, False, sees)
        vote = np.where(sees, 1.0, -1.0) * thick  # each person's line, rotated into the gap
        if rule == "single":
            p = rng.integers(n_people)
            block = sees[p] and thick[p] >= 1.0
            mark = sees[p] and not block
        elif rule == "headcount":
            block, mark = vote.sum() > 0, False
        else:
            gv = np.array([vote[group == g].sum() for g in range(groups)])
            yes, no = (gv > 0).sum(), (gv < 0).sum()
            if rule == "groups_unanimous":      # a pin needs every group; one dissent -> mark
                block = yes >= 2 and no == 0
            elif rule == "groups_majority":     # two independent lines raise it; one -> mark
                block = yes >= 2
            else:                                # groups_any: one group's line raises it
                block = yes >= 1
            mark = yes >= 1 and not block
        out["marks"] += bool(mark)
        if harmful:
            out["harmful"] += 1
            out["harm_open"] += not block
        else:
            out["benign"] += 1
            out["benign_blocked"] += bool(block)
    return out


if __name__ == "__main__":
    res = {}
    for capture in (False, True):
        for rule in ("single", "headcount", "groups_unanimous", "groups_majority", "groups_any"):
            runs = [sim(s, rule, capture) for s in range(20)]
            m = {k: float(np.mean([r[k] for r in runs])) for k in runs[0]}
            res[f"{'captured' if capture else 'honest'}|{rule}"] = dict(
                harmful_left_open_pct=round(100 * m["harm_open"] / m["harmful"], 1),
                benign_blocked_pct=round(100 * m["benign_blocked"] / m["benign"], 1),
                marks_per_100=round(100 * m["marks"] / 400, 1))
    Path(__file__).with_name("alignment_pin_votes_results.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k.ljust(20), v)
