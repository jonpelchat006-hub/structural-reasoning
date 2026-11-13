"""Frozen qtube orientation/action-composition diagnostic (no encoder training).

Every candidate is a different orientation of the *same* asymmetric shape.
An ordered action string acts on the source from left to right: RF means rotate,
then flip. There is no search/max over possible turns. Known action quaternions
are an oracle for the geometry, not evidence of learned action semantics.

By default this only evaluates a saved qports distance checkpoint. With
--fit-steps N, it additionally learns just two primitive unit quaternions from
single R/F examples on a separate shape pool, freezes the entire checkpoint,
and tests composition without showing any composed-action training examples.

    python qcompose.py --checkpoint models_r6_ports_clean/dist_s0.pt --n 1000
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn.functional as F

import qtest as Q
from qbridge import quat_R
from qports import PortBridge


def orbit_key(orbit):
    """Canonical exact-pixel D4 key; no learned representation is involved."""
    return min(np.packbits(g.reshape(-1).astype(np.uint8)).tobytes() for g in orbit)


def unique_asymmetric_pool(seed, n, exclude):
    selected, keys = [], set()
    rejected_symmetric = rejected_overlap = rejected_duplicate = 0
    seeds = []
    attempt = 0
    while len(selected) < n:
        pool_seed = seed + attempt * 1_000_000
        seeds.append(pool_seed)
        # Usually one call suffices, including a small reserve for rejections.
        source = Q.pool(pool_seed, max(n - len(selected) + 32, math.ceil(1.1 * n)))
        for orbit in source:
            packed = [np.packbits(g.reshape(-1).astype(np.uint8)).tobytes() for g in orbit]
            if len(set(packed)) != 8:
                rejected_symmetric += 1
                continue
            key = min(packed)
            if key in exclude:
                rejected_overlap += 1
                continue
            if key in keys:
                rejected_duplicate += 1
                continue
            selected.append(orbit)
            keys.add(key)
            if len(selected) == n:
                break
        attempt += 1
    metadata = {
        "pool_seeds": seeds, "unique_asymmetric_orbits": n,
        "rejected_symmetric": rejected_symmetric,
        "rejected_excluded_orbits": rejected_overlap,
        "rejected_duplicate_orbits": rejected_duplicate,
        "orbit_set_sha256": hashlib.sha256(b"".join(sorted(keys))).hexdigest(),
    }
    return np.stack(selected), keys, metadata


def make_examples(orbits, seed):
    rng = np.random.default_rng(seed)
    n = len(orbits)
    initial = rng.integers(8, size=n)
    permutation = np.argsort(rng.random((n, 8)), axis=1)
    key = orbits[np.arange(n), initial].copy()
    candidates = np.take_along_axis(orbits, permutation[:, :, None, None], axis=1).copy()
    return key, candidates


def pixel_target(key, candidates, actions):
    """Independent exact-pixel oracle, applying actions in their written order."""
    target = key.copy()
    for column in actions.T:
        rotate, flip = column == 0, column == 1
        target[rotate] = np.rot90(target[rotate], axes=(-2, -1))
        target[flip] = np.flip(target[flip], axis=-1)
    valid = (candidates == target[:, None]).all(axis=(-2, -1))
    if not (valid.sum(-1) == 1).all():
        raise AssertionError("Each oriented target must have exactly one candidate.")
    return valid.argmax(-1)


def primitive_quaternions(device):
    # R: 90 degrees CCW about z. F: left-right reflection of the plane,
    # implemented physically by 180 degrees about y: (x,y,z)->(-x,y,-z).
    return torch.tensor([[math.sqrt(0.5), 0., 0., math.sqrt(0.5)],
                         [0., 0., 1., 0.]], device=device)


def compose(actions, primitives, C4):
    """For actions a1,...,aL, q_total = q_aL * ... * q_a1."""
    primitives = F.normalize(primitives, dim=-1)
    total = primitives.new_zeros((len(actions), 4))
    total[:, 0] = 1.
    for column in actions.unbind(-1):
        total = Q.prod(primitives[column], total, C4)
    return quat_R(total)


def check_known_composition(actions, R):
    """Check quaternion convention/order against independent integer 2D maps."""
    maps = np.asarray([[[0, -1], [1, 0]], [[-1, 0], [0, 1]]])
    expected = np.broadcast_to(np.eye(2), (len(actions), 2, 2)).copy()
    for column in actions.T:
        expected = maps[column] @ expected
    actual = R.detach().cpu().numpy()
    if not np.allclose(actual[:, :2, :2], expected, atol=1e-5):
        raise AssertionError("Quaternion composition disagrees with pixel action order.")
    if not np.allclose(actual[:, 2, :2], 0., atol=1e-5):
        raise AssertionError("A composed known action left the picture plane.")


def encode(model, key, candidates, device, bs):
    encoded_key, encoded_candidates = [], []
    with torch.no_grad():
        for start in range(0, len(key), bs):
            k = torch.from_numpy(key[start:start + bs].reshape(-1, 49)).to(device)
            c = torch.from_numpy(candidates[start:start + bs].reshape(-1, 8, 49)).to(device)
            encoded_key.append(model.place(k))
            encoded_candidates.append(model.place(c))
    return torch.cat(encoded_key), torch.cat(encoded_candidates)


def oriented_scores(model, encoded, R, positions=True):
    """qports distance score at ONE requested transform per example."""
    qk, qc = encoded
    if not positions:
        qk = torch.cat((qk[..., :1], torch.zeros_like(qk[..., 1:])), -1)
        qc = torch.cat((qc[..., :1], torch.zeros_like(qc[..., 1:])), -1)
    qk, qc = model.key_port(qk), model.socket_port(qc)
    vector = torch.einsum("bij,bnhj->bnhi", R, qk[..., 1:])
    a = F.normalize(torch.cat((qk[..., :1], vector), -1).flatten(-2), dim=-1)
    b = F.normalize(qc.flatten(-2), dim=-1)
    return -((a[:, None] - b) ** 2).sum(-1).mean(-1)


def accuracy(scores, targets, tie_atol):
    targets = torch.as_tensor(targets, device=scores.device)
    rows = torch.arange(len(targets), device=scores.device)
    best = scores.max(-1).values
    tied = scores >= best[:, None] - tie_atol
    # Scalar-only equivariant codes tie across orientations. Averaging uniform
    # tie breaking avoids interpreting roundoff (~1e-14) as pose information.
    tie_credit = tied[rows, targets] / tied.sum(-1)
    other = scores.clone()
    other[rows, targets] = -torch.inf
    margin = scores[rows, targets] - other.max(-1).values
    return {
        "accuracy": float((scores.argmax(-1) == targets).float().mean()),
        "uniform_tie_accuracy": float(tie_credit.float().mean()),
        "rows_with_ties": int((tied.sum(-1) > 1).sum()),
        "mean_target_margin": float(margin.mean()),
    }


def action_groups(n, seed):
    groups = {name: np.broadcast_to(np.asarray([int(c == "F") for c in name]),
                                    (n, len(name))).copy()
              for name in ("R", "F", "RF", "FR")}
    rng = np.random.default_rng(seed)
    for length in range(3, 7):
        words = np.asarray(list(itertools.product((0, 1), repeat=length)))
        # Cover words as evenly as possible, then shuffle their assignment to
        # shapes. Pure repetitions are retained and their endpoint baselines
        # are reported, so identity/reversal coincidences remain visible.
        choices = np.tile(np.arange(len(words)), math.ceil(n / len(words)))[:n]
        rng.shuffle(choices)
        groups[f"length_{length}"] = words[choices]
    return groups


def evaluate(model, encoded, key, candidates, groups, primitives, C4, tie_atol,
             known=False):
    results = {}
    identity = torch.eye(3, device=primitives.device).expand(len(key), 3, 3)
    with torch.no_grad():
        ignored_scores = oriented_scores(model, encoded, identity)
        for name, actions_np in groups.items():
            actions = torch.as_tensor(actions_np, device=primitives.device)
            R = compose(actions, primitives, C4)
            if known:
                check_known_composition(actions_np, R)
            reversed_R = compose(actions.flip(-1), primitives, C4)
            targets = pixel_target(key, candidates, actions_np)
            reverse_targets = pixel_target(key, candidates, actions_np[:, ::-1])
            identity_targets = pixel_target(key, candidates,
                                            np.empty((len(key), 0), dtype=np.int64))
            row = {
                "n": len(key), "length": actions_np.shape[1],
                "oriented": accuracy(oriented_scores(model, encoded, R), targets, tie_atol),
                "positions_off": accuracy(oriented_scores(model, encoded, R, positions=False),
                                           targets, tie_atol),
                "action_ignored": accuracy(ignored_scores, targets, tie_atol),
                "order_reversed": accuracy(oriented_scores(model, encoded, reversed_R),
                                            targets, tie_atol),
                "exact_pixel_accuracy": 1., "invariant_uniform_baseline": 0.125,
                "exact_action_ignored_accuracy": float(np.mean(identity_targets == targets)),
                "exact_order_reversed_accuracy": float(np.mean(reverse_targets == targets)),
            }
            words, counts = np.unique(actions_np, axis=0, return_counts=True)
            row["action_counts"] = {
                "".join("RF"[a] for a in word): int(count) for word, count in zip(words, counts)
            }
            results[name] = row
    return results


def fit_primitives(model, encoded, key, candidates, steps, batch, lr, seed, C4,
                   loss_kind="ce"):
    device = encoded[0].device
    generator = torch.Generator(device=device).manual_seed(seed)
    primitives = torch.nn.Parameter(torch.randn((2, 4), generator=generator, device=device))
    targets = torch.tensor(np.stack([pixel_target(key, candidates,
                           np.full((len(key), 1), action, dtype=np.int64))
                           for action in range(2)]), device=device)
    opt = torch.optim.Adam([primitives], lr=lr)
    start = time.perf_counter()
    initial_loss = final_loss = None
    for step in range(steps):
        indices = torch.randint(len(key), (batch,), generator=generator, device=device)
        action = torch.randint(2, (batch,), generator=generator, device=device)
        R = compose(action[:, None], primitives, C4)
        minibatch = encoded[0][indices], encoded[1][indices]
        scores = oriented_scores(model, minibatch, R)
        target = targets[action, indices]
        if loss_kind == "pose":
            # Learn the actual transition, including its continuous pose, rather
            # than stopping once it merely outranks the seven other poses.
            rows = torch.arange(batch, device=device)
            loss = -scores[rows, target].mean()
        else:
            loss = F.cross_entropy(scores * model.log_tau.exp().detach(), target)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_([primitives], 10.)
        opt.step()
        # Renormalizing keeps the parameter scale from changing its effective LR.
        with torch.no_grad():
            primitives.copy_(F.normalize(primitives, dim=-1))
        if step == 0:
            initial_loss = float(loss.detach())
        final_loss = float(loss.detach())
    fitted = F.normalize(primitives.detach(), dim=-1)
    truth = quat_R(primitive_quaternions(device))
    matrix_error = (quat_R(fitted) - truth).square().sum((-1, -2)).sqrt()
    return fitted, {
        "steps": steps, "trainable_numbers": 8, "encoder_frozen": True,
        "training_actions": ["R", "F"], "training_orbits": len(key),
        "learning_rate": lr, "loss_kind": loss_kind,
        "initial_minibatch_loss": initial_loss,
        "final_minibatch_loss": final_loss,
        "primitive_quaternions_R_F": fitted.cpu().tolist(),
        "rotation_matrix_frobenius_error_R_F": matrix_error.cpu().tolist(),
        "seconds": round(time.perf_counter() - start, 3),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--fit-steps", type=int, default=0)
    ap.add_argument("--fit-loss", choices=("ce", "pose"), default="ce",
                    help="ce: candidate classification; pose: target feature-distance without temperature")
    ap.add_argument("--fit-size", type=int, default=512)
    ap.add_argument("--fit-lr", type=float, default=0.05)
    ap.add_argument("--tie-atol", type=float, default=1e-8)
    ap.add_argument("--out", default="qcompose_results.json")
    a = ap.parse_args()
    if min(a.n, a.batch, a.fit_size) < 1 or a.fit_steps < 0 or a.fit_lr <= 0 or a.tie_atol < 0:
        ap.error("Positive sample/batch/fit sizes and LR, nonnegative steps/tie tolerance required.")
    if a.device == "cpu":
        torch.set_num_threads(min(4, torch.get_num_threads()))
    started = time.perf_counter()
    checkpoint_path = Path(a.checkpoint).resolve()
    # This is a local, user-selected project checkpoint with config metadata.
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if checkpoint["kind"] != "dist":
        ap.error("This diagnostic currently requires a qports dist checkpoint.")
    config = checkpoint["config"]
    model_seed = int(checkpoint["seed"])
    seed = model_seed if a.seed is None else a.seed
    model = PortBridge("dist", sym=config.get("sym", "flat"), seed=model_seed).to(a.device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    C4 = Q.table(4).to(a.device)

    # Regenerate canonical keys for the checkpoint's encoder-training shapes.
    # Different RNG seeds alone do not prove that two shape pools are disjoint.
    encoder_pool = Q.pool(model_seed, int(config.get("train_size", 6000)))
    encoder_keys = {orbit_key(orbit) for orbit in encoder_pool}
    excluded = encoder_keys.copy()
    fitted = fit_metadata = fit_pool_metadata = None
    if a.fit_steps:
        fit_orbits, fit_keys, fit_pool_metadata = unique_asymmetric_pool(
            40_000 + seed, a.fit_size, excluded)
        excluded |= fit_keys
        fit_key, fit_candidates = make_examples(fit_orbits, 140_000 + seed)
        fit_encoded = encode(model, fit_key, fit_candidates, a.device, a.batch)
        fitted, fit_metadata = fit_primitives(model, fit_encoded, fit_key, fit_candidates,
                                              a.fit_steps, a.batch, a.fit_lr,
                                              240_000 + seed, C4, a.fit_loss)

    test_orbits, test_keys, test_pool_metadata = unique_asymmetric_pool(
        30_000 + seed, a.n, excluded)
    assert not (test_keys & excluded)
    key, candidates = make_examples(test_orbits, 130_000 + seed)
    encoded = encode(model, key, candidates, a.device, a.batch)
    groups = action_groups(a.n, 230_000 + seed)
    known = primitive_quaternions(a.device)
    result = {
        "schema_version": 1, "checkpoint": str(checkpoint_path), "config": vars(a),
        "checkpoint_seed": model_seed, "evaluation_seed": seed,
        "task": {
            "candidates": "All eight distinct D4 orientations of the same shape, shuffled.",
            "source_orientation": "Uniform random D4 orientation, shared across action groups.",
            "action_order": "Left to right; RF means rotate then flip; q_total=q_last*...*q_first.",
            "R": "90 degrees counterclockwise in the picture plane.",
            "F": "Left-right pixel reflection; physical 180 degree rotation about y.",
            "scoring": "One specified transform; no maximization over turns.",
            "known_action_limit": "Known geometry is supplied, so this is an orientation diagnostic.",
            "tie_atol": a.tie_atol,
            "position_off_limit": "Raw argmax can exploit roundoff; uniform_tie_accuracy averages tied maxima.",
        },
        "encoder_training_orbits_excluded": len(encoder_keys),
        "test_pool": test_pool_metadata,
        "known_actions": evaluate(model, encoded, key, candidates, groups, known, C4,
                                   a.tie_atol, known=True),
    }
    if fitted is not None:
        result["primitive_fit"] = fit_metadata
        result["fit_pool"] = fit_pool_metadata
        result["fitted_actions"] = evaluate(model, encoded, key, candidates, groups,
                                            fitted, C4, a.tie_atol)
    result["seconds"] = round(time.perf_counter() - started, 3)
    output = Path(a.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(output), "n": a.n,
                      "known_accuracy": {k: round(v["oriented"]["accuracy"], 4)
                                         for k, v in result["known_actions"].items()},
                      "positions_off_uniform_tie_accuracy": {
                          k: round(v["positions_off"]["uniform_tie_accuracy"], 4)
                          for k, v in result["known_actions"].items()},
                      "fitted_accuracy": {k: round(v["oriented"]["accuracy"], 4)
                                          for k, v in result.get("fitted_actions", {}).items()},
                      "seconds": result["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
