"""The task as a wire dropped into a structure of anchors (Jonathan, Sep 26).

A task is a line that has to get from one side to the other. It is dropped into the
space and settles: its own weight (task depth) pulls it down, anchors (people's pins)
catch it from below like lines across the window, and dissent pushes down on it as a
force — stronger when the dissenter has found evidence (papers). A pin that is loaded
past its strength snaps and the wire re-settles. The task may bend and pins may break;
it is allowed to stay as long as no point of the settled wire touches the floor.

Wire: 60 nodes under tension, ends held at height 1. Anchor pins: one-sided springs
(catch the wire only if it sags below the pin), stiffness and strength from the
person's thickness, at a set height (higher anchors = held further above the floor).
Truth: harmful tasks carry hidden point loads the proposal does not show.
Decision: settle with the visible load + dissent forces; accept if the settled wire
clears the floor by 0.05. Harm: an accepted task whose TRUE settled wire (visible +
hidden load, no dissent) touches the floor.
Dissent variants: none; headcount (dissenters push at random points — they object but
cannot say where); evidence (agents that find papers push where the hidden load is,
in proportion to it); flooding (also fake-paper pushes on benign tasks); verified
flooding (a paper's push counts only if a witness from different work confirms it:
real papers 80%, fake 15%).
"""
import json
from pathlib import Path
import numpy as np

M, TENSION, END_H = 60, 20.0, 1.0


def settle(load, pins, max_iter=40):
    """load[i] >= 0 pushes down. pins: list of (node, height, stiffness, strength).
    Returns heights and the list of pins still standing (snapped pins are removed)."""
    pins = list(pins)
    while True:
        active = set()
        for _ in range(max_iter):
            A = np.zeros((M, M)); b = load.copy()
            for i in range(M):
                A[i, i] = -2 * TENSION
                if i > 0: A[i, i - 1] = TENSION
                else: b[i] -= TENSION * END_H
                if i < M - 1: A[i, i + 1] = TENSION
                else: b[i] -= TENSION * END_H
            for idx in active:
                n, h, k, _ = pins[idx]
                A[n, n] -= k; b[n] -= k * h
            H = np.linalg.solve(A, b)
            new = {idx for idx, (n, h, k, _) in enumerate(pins) if H[n] < h}
            if new == active:
                break
            active = new
        snapped = [idx for idx in active if pins[idx][2] * (pins[idx][1] - H[pins[idx][0]]) > pins[idx][3]]
        if not snapped:
            return H, pins
        pins = [p for idx, p in enumerate(pins) if idx not in snapped]


def make_pins(rng, height, n=6):
    pos = np.sort(rng.choice(np.arange(5, M - 5), n, replace=False))
    thick = rng.gamma(2.0, 0.6, n)
    return [(int(p), height, 4.0 * t, 1.2 * t) for p, t in zip(pos, thick)]


def run(seed, dissent, anchor_h, depth, n_tasks=200):
    rng = np.random.default_rng(seed)
    out = dict(harm=0, harmful=0, benign_rejected=0, benign=0, accepted=0)
    for _ in range(n_tasks):
        pins = make_pins(rng, anchor_h)
        visible = np.full(M, 0.02 * depth)
        harmful = rng.random() < 0.4
        hidden = np.zeros(M)
        if harmful:
            for n in rng.choice(M, 2, replace=False):
                hidden[n] += rng.uniform(0.6, 1.4)
        push = np.zeros(M)
        if dissent == "headcount":
            k = rng.binomial(5, 0.6 if harmful else 0.3)
            for n in rng.choice(M, k):
                push[n] += 0.35
        if dissent in ("evidence", "flooding", "verified"):
            for _agent in range(3):
                if harmful and rng.random() < 0.6:
                    counts = dissent != "verified" or rng.random() < 0.8
                    if counts:
                        push += 0.7 * hidden
            if dissent in ("flooding", "verified") and not harmful and rng.random() < 0.3:
                fake = np.zeros(M); fake[rng.integers(M)] = rng.uniform(0.6, 1.4) * 0.7
                if dissent == "flooding" or rng.random() < 0.15:
                    push += fake
        H, _ = settle(visible + push, pins)
        accept = H.min() > 0.05
        Htrue, _ = settle(visible + hidden, pins)
        touches = Htrue.min() <= 0
        out["accepted"] += accept
        if harmful:
            out["harmful"] += 1
        else:
            out["benign"] += 1
            out["benign_rejected"] += not accept
        if accept and touches:
            out["harm"] += 1
    return out


if __name__ == "__main__":
    res = {}
    for depth in (1.0, 2.0, 3.0):
        for anchor_h in (0.3, 0.7):
            for d in ("none", "headcount", "evidence", "flooding", "verified"):
                runs = [run(s, d, anchor_h, depth) for s in range(4)]
                m = {k: sum(r[k] for r in runs) for k in runs[0]}
                res[f"depth {depth} | anchors {anchor_h} | {d}"] = dict(
                    harm_per_100=round(100 * m["harm"] / (200 * len(runs)), 1),
                    harmful_let_through_pct=round(100 * m["harm"] / max(1, m["harmful"]), 1),
                    benign_rejected_pct=round(100 * m["benign_rejected"] / max(1, m["benign"]), 1))
    Path(__file__).with_name("alignment_wire_results.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k.ljust(38), v)
