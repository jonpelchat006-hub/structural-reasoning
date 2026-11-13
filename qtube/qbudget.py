"""Infer a consumable strip from observation history, without game-specific rules.

One frame must represent one executed action unless action_indices is supplied.
The detector searches both axes and all observed colours for an initially uniform
run progressively replaced from one edge by another uniform colour. It rejects
moving/scattered patches, pools matching adjacent scan lines, and reports jumps
as possible reset/refill events. This is an observational resource hypothesis;
remaining actions assume future drain does not exceed the observed maximum.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import numpy as np


@dataclass
class BudgetEstimate:
    status: str = "unknown"
    remaining_actions_estimate: float | None = None
    remaining_actions_lower_bound: int | None = None
    remaining_pixels: int | None = None
    consume_slope: float | None = None
    max_observed_consume_per_action: float | None = None
    evidence: dict = field(default_factory=dict)
    uncertainty: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def can_afford(self, n, reserve=1):
        """Conservative only under the reported stationary-drain assumption."""
        if n < 0 or reserve < 0:
            raise ValueError("n and reserve must be nonnegative")
        return bool(self.status == "inferred" and self.remaining_actions_lower_bound is not None
                    and self.remaining_actions_lower_bound >= math.ceil(n + reserve))


def _runs(values):
    edges = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
    for a, b in zip(edges[:-1], edges[1:]):
        yield int(a), int(b), int(values[a])


def infer_budget(frames, *, action_indices=None, exclusions=None, min_run=8,
                 min_decrements=6, max_candidates=8):
    """Return BudgetEstimate inferred from integer frames[T,H,W].

    exclusions optionally supplies a static HxW boolean mask; a run crossing it
    is ignored. No bar position, colour, body, HUD, or action meaning is built in.
    A negative answer from can_afford means insufficient evidence/capacity, not
    proof that the environment will terminate. Pixel quantization and unobserved
    action-dependent costs remain explicit uncertainties.
    """
    F = np.asarray(frames)
    if F.ndim != 3 or not np.issubdtype(F.dtype, np.integer):
        raise ValueError("frames must be an integer array [T,H,W]")
    if len(F) < min_decrements + 1:
        return BudgetEstimate(uncertainty=["Insufficient action observations."])
    times = np.arange(len(F), dtype=float) if action_indices is None else np.asarray(action_indices, float)
    if times.shape != (len(F),) or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("action_indices must strictly increase and align with frames")
    exclusion = np.zeros(F.shape[1:], bool) if exclusions is None else np.asarray(exclusions, bool)
    if exclusion.shape != F.shape[1:]:
        raise ValueError("exclusions must match a frame")
    found = []
    # First-frame full runs preserve capacity without selecting coordinates by hand.
    # Replenishments within this history are detected from their width jumps.
    for orientation, data, omit in (("horizontal", F, exclusion),
                                     ("vertical", F.transpose(0, 2, 1), exclusion.T)):
        for line in range(data.shape[1]):
            for start, stop, colour in _runs(data[0, line]):
                width = stop - start
                if width < min_run or omit[line, start:stop].any():
                    continue
                patch = data[:, line, start:stop]
                mask = patch == colour
                lengths = mask.sum(axis=1).astype(int)
                positions = np.arange(width)[None, :]
                anchored_left = np.array_equal(mask, positions < lengths[:, None])
                anchored_right = np.array_equal(mask, positions >= width - lengths[:, None])
                if not (anchored_left or anchored_right):
                    continue
                other = np.unique(patch[~mask])
                if len(other) != 1:
                    continue
                delta = np.diff(lengths)
                negatives = delta < 0
                if int(negatives.sum()) < min_decrements or int(-delta[negatives].sum()) < 4:
                    continue
                # Small back-and-forth motion is not a draining strip. Large gains
                # are retained as reset/refill candidates, rather than erased.
                gains = np.flatnonzero(delta > 0)
                if any(delta[i] < max(3, width * .25) for i in gains):
                    continue
                drops = -delta[negatives] / np.diff(times)[negatives]
                if not len(drops) or not np.isfinite(drops).all():
                    continue
                signature = (orientation, start, stop, colour, int(other[0]),
                             "left" if anchored_left else "right", tuple(map(int, lengths)))
                found.append({"signature": signature, "line": line, "lengths": lengths,
                              "drops": drops, "gains": gains, "width": width})
    groups = {}
    for candidate in found:
        groups.setdefault(candidate["signature"], []).append(candidate)
    ranked = sorted(groups.values(), key=lambda g: (
        len(g), int((np.diff(g[0]["lengths"]) < 0).sum()),
        g[0]["width"]), reverse=True)
    if not ranked:
        return BudgetEstimate(uncertainty=["No anchored, repeatedly shrinking uniform strip was observed."])
    group = ranked[0]
    best = group[0]
    orientation, start, stop, colour, replacement, anchor, _ = best["signature"]
    lines = sorted(c["line"] for c in group)
    contiguous = all(b == a + 1 for a, b in zip(lines, lines[1:]))
    if not contiguous:
        return BudgetEstimate(uncertainty=["Matching scan lines are spatially disjoint; strip identity is ambiguous."])
    lengths = best["lengths"]
    delta = np.diff(lengths)
    interval = np.diff(times)
    ordinary = delta <= 0
    # Include zero-pixel action transitions: integer displays can quantize costs.
    slope = float((-delta[ordinary]).sum() / interval[ordinary].sum())
    max_drain = float(best["drops"].max())
    remaining = int(lengths[-1])
    resets = []
    for i in best["gains"]:
        similarity = float(np.mean(F[int(i) + 1] == F[0]))
        resets.append({"frame_index": int(i) + 1,
                       "previous_pixels": int(lengths[i]), "new_pixels": int(lengths[i + 1]),
                       "after_exhaustion": bool(lengths[i] == 0),
                       "similarity_to_initial_frame": similarity,
                       "interpretation": "possible_reset_or_refill"})
    rect = ([lines[0], start, lines[-1], stop - 1] if orientation == "horizontal"
            else [start, lines[0], stop - 1, lines[-1]])
    status = "exhausted" if remaining == 0 else "inferred"
    if resets and resets[-1]["frame_index"] == len(F) - 1:
        status = "reset_or_refill_observed"
    result = BudgetEstimate(
        status=status,
        remaining_actions_estimate=float(remaining / slope) if slope > 0 else None,
        remaining_actions_lower_bound=int(math.floor(remaining / max_drain)),
        remaining_pixels=remaining, consume_slope=slope,
        max_observed_consume_per_action=max_drain,
        evidence={"rectangle_y0_x0_y1_x1": rect, "orientation": orientation,
                  "remaining_colour": colour, "replacement_colour": replacement,
                  "fixed_edge": anchor, "replicated_scan_lines": len(lines),
                  "frames": len(F), "action_span": float(times[-1] - times[0]),
                  "decrement_transitions": int((delta < 0).sum()),
                  "zero_change_transitions": int((delta == 0).sum()),
                  "observed_initial_capacity_pixels": int(lengths[0]),
                  "width_by_frame": list(map(int, lengths)), "reset_or_refill_events": resets,
                  "candidate_groups": len(ranked),
                  "competing_candidates": [
                      {"orientation": g[0]["signature"][0], "scan_lines": len(g),
                       "initial_width": g[0]["width"],
                       "remaining_pixels": int(g[0]["lengths"][-1])}
                      for g in ranked[1:max_candidates]]},
        uncertainty=["A shrinking strip is a resource/timer hypothesis, not an observed termination rule.",
                     "Action capacity assumes future consumption does not exceed the largest observed pixel drain.",
                     "Pixel quantization, conditional costs, replenishment, and hidden state can alter that bound.",
                     "History is assumed to contain one observation per action unless action_indices is supplied."])
    if len(group) == 1:
        result.uncertainty.append("Only one scan line supports this meter.")
    # Independent, equally replicated strips with different predicted capacities
    # cannot safely be collapsed into a single controlling budget.
    if len(ranked) > 1 and len(ranked[1]) == len(group):
        second = ranked[1][0]
        second_capacity = int(second["lengths"][-1]) / float(second["drops"].max())
        if abs(second_capacity - result.remaining_actions_lower_bound) > 2:
            result.status = "ambiguous"
            result.uncertainty.append("Equally supported strips predict different action capacities.")
    return result


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("npz", help="Observation archive containing F[T,H,W]")
    parser.add_argument("--prefix", type=int, help="Use only the first N frames")
    parser.add_argument("--cost", type=int, default=0)
    parser.add_argument("--reserve", type=int, default=1)
    args = parser.parse_args()
    with np.load(args.npz, allow_pickle=False) as archive:
        observations = archive["F"]
        if args.prefix is not None:
            observations = observations[:args.prefix]
        estimate = infer_budget(observations)
    print(json.dumps({**estimate.to_dict(), "requested_actions": args.cost,
                      "reserve": args.reserve,
                      "can_afford": estimate.can_afford(args.cost, args.reserve)}, indent=2))
