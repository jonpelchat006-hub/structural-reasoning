"""Frozen-attention pose diagnostic: quaternion means plus second moments.

No training or new learned parameters are introduced. The original normalized
quaternion means are compared with the same means augmented by each attention
head's centered covariance. Covariances transform as R M R^T and are divided by
the fixed grid radius squared (9 cell units squared), rather than a learned scale.

Second moments retain the orientation of the centered bars and rectangles tested
here, whose centroids vanish. They do not distinguish every possible shape. This
small representation diagnostic is not an ARC evaluation or a general solver.

Run: python qmoments.py --checkpoint models_r6_ports_clean/dist_s0.pt
Commands apply left-to-right: RF means rotate, then reflect.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

import qtest as Q
from qports import PortBridge


@dataclass(frozen=True)
class MomentCode:
    """Leading batch dimensions, then nodes/heads/quaternion or covariance."""

    quaternions: torch.Tensor  # (..., nodes, heads, 4)
    covariance: torch.Tensor   # (..., nodes, heads, 3, 3)


class QuaternionMoments(nn.Module):
    """Reuse a frozen, identity-port qports distance encoder and its attention."""

    def __init__(self, encoder: PortBridge):
        super().__init__()
        if encoder.variant != "dist":
            raise ValueError("This diagnostic requires the identity-port 'dist' model.")
        self.encoder = encoder.cpu().double().eval()
        self.encoder.requires_grad_(False)
        self.register_buffer(
            "grid3", torch.cat((encoder.G, torch.zeros_like(encoder.G[:, :1])), -1)
        )
        self.covariance_scale = float(encoder.G.abs().max().square())

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> "QuaternionMoments":
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        if checkpoint.get("kind") != "dist":
            raise ValueError("Checkpoint kind must be 'dist'.")
        model = PortBridge("dist", sym=checkpoint["config"]["sym"],
                           seed=checkpoint.get("seed", 0))
        model.load_state_dict(checkpoint["state_dict"])
        return cls(model)

    def encode(self, images: torch.Tensor) -> MomentCode:
        images = images.to(device="cpu", dtype=torch.float64)
        shape = images.shape[:-1]
        if images.shape[-1] != 49:
            raise ValueError("Expected flattened 7x7 pictures.")
        model = self.encoder
        h = F.gelu(model.c1(images.reshape(-1, 1, 7, 7)))
        h = F.gelu(model.c2(h))
        h = model.c3(h).flatten(2)
        nh = model.nodes * model.heads
        attention = h[:, :nh].softmax(-1)
        mean = attention @ self.grid3
        scalar = (attention * h[:, nh:]).sum(-1)
        quaternions = torch.cat((scalar[..., None], mean), -1)
        centered = self.grid3[None, None] - mean[:, :, None]
        covariance = torch.einsum(
            "bhs,bhsi,bhsj->bhij", attention, centered, centered
        )
        return MomentCode(
            quaternions.reshape(*shape, model.nodes, model.heads, 4),
            covariance.reshape(*shape, model.nodes, model.heads, 3, 3),
        )

    @staticmethod
    def transform(code: MomentCode, rotation: torch.Tensor) -> MomentCode:
        """Apply one exact physical 3x3 rotation to every head."""
        if rotation.shape != (3, 3):
            raise ValueError("Expected one 3x3 physical rotation.")
        rotation = rotation.to(code.quaternions)
        vector = torch.einsum("ab,...nhb->...nha", rotation,
                              code.quaternions[..., 1:])
        covariance = torch.einsum("ai,...nhij,bj->...nhab", rotation,
                                  code.covariance, rotation)
        return MomentCode(
            torch.cat((code.quaternions[..., :1], vector), -1), covariance
        )

    def distance(self, left: MomentCode, right: MomentCode,
                 augmented: bool = True) -> torch.Tensor:
        """Existing mean distance plus mean covariance Frobenius distance."""
        a = F.normalize(left.quaternions.flatten(-2), dim=-1, eps=1e-12)
        b = F.normalize(right.quaternions.flatten(-2), dim=-1, eps=1e-12)
        distance = ((a - b) ** 2).sum(-1).mean(-1)
        if augmented:
            delta = (left.covariance - right.covariance) / self.covariance_scale
            distance = distance + delta.square().sum((-1, -2)).mean((-1, -2))
        return distance

    def full_code(self, code: MomentCode, augmented: bool = True) -> torch.Tensor:
        """Flatten diagnostic features; scoring averages covariance heads."""
        means = F.normalize(code.quaternions.flatten(-2), dim=-1, eps=1e-12)
        means = means.flatten(-2)
        if not augmented:
            return means
        covariance = (code.covariance / self.covariance_scale).flatten(-4)
        return torch.cat((means, covariance), -1)


def exact_actions() -> dict[str, torch.Tensor]:
    """R is counterclockwise; F flips x via a physical 180-degree y rotation."""
    return {
        "R": torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]],
                          dtype=torch.float64),
        "F": torch.diag(torch.tensor([-1., 1., -1.], dtype=torch.float64)),
    }


def command_rotation(command: str, actions: dict[str, torch.Tensor]) -> torch.Tensor:
    result = torch.eye(3, dtype=torch.float64)
    for letter in command:
        result = actions[letter] @ result
    return result


def apply_command(picture: np.ndarray, command: str) -> np.ndarray:
    for letter in command:
        picture = np.rot90(picture) if letter == "R" else np.fliplr(picture)
    return picture.copy()


def distinct_orbit(picture: np.ndarray) -> tuple[list[np.ndarray], list[int]]:
    pictures, labels, seen = [], [], set()
    for turn, operation in enumerate(Q.TURNS):
        transformed = operation(picture).copy()
        key = transformed.tobytes()
        if key not in seen:
            seen.add(key)
            pictures.append(transformed)
            labels.append(turn)
    return pictures, labels


def uniform_tie_result(distances: torch.Tensor, target: int,
                       atol: float, rtol: float) -> dict:
    """Expected correctness when every numerically tied minimum is equally likely."""
    best = distances.min()
    ties = torch.isclose(distances, best, atol=atol, rtol=rtol)
    tie_count = int(ties.sum())
    return {
        "expected_accuracy": float(ties[target]) / tie_count,
        "tie_count": tie_count,
        "target_in_tie": bool(ties[target]),
        "distances": distances.tolist(),
    }


def pairwise_code_gaps(features: torch.Tensor) -> dict:
    differences = [features[i] - features[j] for i in range(len(features))
                   for j in range(i)]
    if not differences:
        return {"max_abs_gap": 0.0, "min_distinct_l2_gap": 0.0}
    return {
        "max_abs_gap": max(float(d.abs().max()) for d in differences),
        "min_distinct_l2_gap": min(float(d.norm()) for d in differences),
    }


def evaluate_pattern(model: QuaternionMoments, picture: np.ndarray,
                     rng: np.random.Generator, atol: float, rtol: float) -> dict:
    actions = exact_actions()
    orbit, labels = distinct_orbit(picture)
    images = torch.tensor(np.stack(orbit).reshape(len(orbit), 49),
                          dtype=torch.float64)
    encoded = model.encode(images)
    original = model.encode(torch.tensor(picture.reshape(49), dtype=torch.float64))
    means_error = covariance_error = 0.0
    for turn, operation in enumerate(Q.TURNS):
        observed = model.encode(torch.tensor(operation(picture).copy().reshape(49)))
        rotation = torch.linalg.matrix_power(actions["R"], turn % 4)
        if turn >= 4:
            rotation = rotation @ actions["F"]
        predicted = model.transform(original, rotation)
        means_error = max(means_error, float(
            (observed.quaternions - predicted.quaternions).abs().max()))
        covariance_error = max(covariance_error, float(
            (observed.covariance - predicted.covariance).abs().max()))

    cases = []
    for source_index, source in enumerate(orbit):
        source_code = model.encode(images[source_index])
        for command in ("R", "F", "RF", "FR"):
            target_picture = apply_command(source, command)
            permutation = rng.permutation(len(orbit))
            candidates = [orbit[int(i)] for i in permutation]
            target = next(i for i, candidate in enumerate(candidates)
                          if np.array_equal(candidate, target_picture))
            candidate_code = MomentCode(encoded.quaternions[permutation],
                                        encoded.covariance[permutation])
            moved = model.transform(source_code, command_rotation(command, actions))
            cases.append({
                "source_turn": labels[source_index], "command": command,
                "candidate_turns": [labels[int(i)] for i in permutation],
                "target_candidate": target,
                "centroid": uniform_tie_result(
                    model.distance(moved, candidate_code, augmented=False),
                    target, atol, rtol),
                "moments": uniform_tie_result(
                    model.distance(moved, candidate_code, augmented=True),
                    target, atol, rtol),
            })
    return {
        "picture": ["".join(str(int(cell)) for cell in row) for row in picture],
        "cells": int(picture.sum()),
        "invariant_180": bool(np.array_equal(picture, np.rot90(picture, 2))),
        "invariant_90": bool(np.array_equal(picture, np.rot90(picture))),
        "distinct_orientations": len(orbit),
        "max_position_norm": float(encoded.quaternions[..., 1:].norm(dim=-1).max()),
        "raw_quaternion_code_gaps": pairwise_code_gaps(
            encoded.quaternions.flatten(-3)),
        "centroid_full_code_gaps": pairwise_code_gaps(
            model.full_code(encoded, augmented=False)),
        "moments_full_code_gaps": pairwise_code_gaps(
            model.full_code(encoded, augmented=True)),
        "equivariance": {"mean_max_abs_error": means_error,
                         "covariance_max_abs_error": covariance_error},
        "centroid_uniform_tie_accuracy": float(np.mean([
            case["centroid"]["expected_accuracy"] for case in cases])),
        "moments_uniform_tie_accuracy": float(np.mean([
            case["moments"]["expected_accuracy"] for case in cases])),
        "cases": cases,
    }


def main() -> None:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path,
                        default=directory / "models_r6_ports_clean" / "dist_s0.pt")
    parser.add_argument("--out", type=Path, default=directory / "qmoments_results.json")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tie-atol", type=float, default=1e-12)
    parser.add_argument("--tie-rtol", type=float, default=1e-9)
    args = parser.parse_args()
    torch.set_num_threads(1)
    model = QuaternionMoments.from_checkpoint(args.checkpoint)
    bar = np.zeros((7, 7), dtype=np.float64)
    bar[3, 1:6] = 1
    rectangle = np.zeros((7, 7), dtype=np.float64)
    rectangle[2:5, 1:6] = 1
    rng = np.random.default_rng(args.seed)
    with torch.no_grad():
        patterns = {
            name: evaluate_pattern(model, picture, rng, args.tie_atol, args.tie_rtol)
            for name, picture in (("bar", bar), ("rectangle", rectangle))
        }
    cases = [case for pattern in patterns.values() for case in pattern["cases"]]
    result = {
        "checkpoint": str(args.checkpoint.resolve()),
        "device": "cpu", "dtype": "float64", "training": False,
        "new_learned_parameters": 0,
        "command_convention": "Letters apply left-to-right: RF is rotate then reflect.",
        "covariance_scale": model.covariance_scale,
        "distance": "mean-node normalized quaternion squared distance plus mean-head covariance squared Frobenius distance / grid_coordinate_radius^4",
        "tie_atol": args.tie_atol, "tie_rtol": args.tie_rtol,
        "seed": args.seed, "cases": len(cases),
        "centroid_uniform_tie_accuracy": float(np.mean([
            case["centroid"]["expected_accuracy"] for case in cases])),
        "moments_uniform_tie_accuracy": float(np.mean([
            case["moments"]["expected_accuracy"] for case in cases])),
        "limitations": [
            "Second moments fix these orientation-collapse examples, not every possible shape.",
            "Both source shapes have only two distinct D4 orientations; RF and FR can coincide on these shapes.",
            "This diagnostic introduces no training and makes no ARC performance claim.",
        ],
        "patterns": patterns,
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "patterns"},
                     indent=2))
    for name, pattern in patterns.items():
        print(json.dumps({"pattern": name, **{key: value for key, value in pattern.items()
                         if key not in {"picture", "cases"}}}, indent=2))


if __name__ == "__main__":
    main()
