"""Round 6: can distinct object/socket ports make the bridge useful?

Uses qbridge's placed quaternion nodes, with fixed physical quarter turns in
training. Separate ports mix scalar channels and vector channels independently,
so they commute with every 3D rotation. Codes are normalized before multiplication
to remove the additive-denominator scale shortcut. Every model sees identical
training batches; evaluation accepts every candidate in the key's D4 orbit and
also reports the original designated-label accuracy.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

import qtest as Q
from qbridge import Bridge, quat_R, spin_quats
from qlift import MIR, ROT


class Port(nn.Module):
    """P(w, V) = (A w + c, B V), equivariant under V -> V R^T."""

    def __init__(self, heads=4):
        super().__init__()
        self.scalar = nn.Parameter(torch.eye(heads) + 0.1 * torch.randn(heads, heads))
        self.vector = nn.Parameter(torch.eye(heads) + 0.1 * torch.randn(heads, heads))
        self.bias = nn.Parameter(torch.zeros(heads))

    def forward(self, q):
        w = F.linear(q[..., 0], self.scalar, self.bias)
        v = torch.einsum("ij,...jd->...id", self.vector, q[..., 1:])
        return torch.cat((w[..., None], v), -1)


class PortBridge(Bridge):
    def __init__(self, kind, sym="flat", seed=0):
        super().__init__("socket_random" if kind == "random_dual" else
                         "dist" if kind.startswith("dist") else "socket", sym=sym, seed=seed)
        self.variant = kind
        self.T.requires_grad_(False)  # fixed geometric turns; no latent turn shortcut
        self.key_port = Port() if kind.endswith("dual") else nn.Identity()
        self.socket_port = Port() if kind.endswith("dual") else nn.Identity()
        # Common initial temperature across all bridge and distance controls.
        self.log_tau.data.fill_(math.log(10.0))

    def scores(self, K, Cn, R, positions=True):
        qk, qc = self.place(K), self.place(Cn)
        if not positions:
            qk = torch.cat((qk[..., :1], torch.zeros_like(qk[..., 1:])), -1)
            qc = torch.cat((qc[..., :1], torch.zeros_like(qc[..., 1:])), -1)
        qk, qc = self.key_port(qk), self.socket_port(qc)
        v = torch.einsum("mab,...nhb->...mnha", R, qk[..., 1:])
        w = qk[..., :1].unsqueeze(-4).expand(*v.shape[:-1], 1)
        a = torch.cat((w, v), -1).flatten(-2)[:, None]
        b = qc.flatten(-2)[:, :, None]
        a, b = torch.broadcast_tensors(a, b)
        a = F.normalize(a, dim=-1, eps=1e-12)
        b = F.normalize(b, dim=-1, eps=1e-12)
        if self.variant.startswith("dist"):
            return -((a - b) ** 2).sum(-1).mean(-1), None
        ratio = Q.prod(a, b, self.C16).norm(dim=-1).mean(-1)
        return -ratio, ratio

    def forward(self, K, Cn, R):
        scores, _ = self.scores(K, Cn, R)
        return self.log_tau.exp() * scores.max(-1).values


def valid_matches(K, Cn, mirrors=True):
    """A near-miss may accidentally be another exact C4 or D4 match."""
    key = K.numpy().reshape(-1, 7, 7)
    candidates = Cn.numpy().reshape(-1, Cn.shape[1], 7, 7)
    valid = np.zeros(candidates.shape[:2], dtype=bool)
    for source in ((key, np.flip(key, axis=-1)) if mirrors else (key,)):
        for k in range(4):
            transformed = np.rot90(source, k, axes=(-2, -1))
            valid |= (candidates == transformed[:, None]).all(axis=(-2, -1))
    return torch.from_numpy(valid)


def evaluate(model, P, turns, n, seed, device, R, bs=50, positions=True):
    rng = np.random.default_rng(seed)
    hits = designated = ambiguous = total = 0
    right_ratios, wrong_ratios, port_norms = [], [], []
    model.eval()
    with torch.no_grad():
        for start in range(0, n, bs):
            K, Cn, Y = Q.batch(rng, min(bs, n - start), turns, P=P,
                               near_n=7, fmin=1, fmax=1, nkind="move")
            valid = valid_matches(K, Cn).to(device)
            K, Cn, Y = K.to(device), Cn.to(device), Y.to(device)
            scores, ratio = model.scores(K, Cn, R, positions=positions)
            best, bt = scores.max(-1)
            pred = best.argmax(-1)
            bi = torch.arange(len(Y), device=device)
            hits += int(valid[bi, pred].sum())
            designated += int((pred == Y).sum())
            ambiguous += int((valid.sum(-1) > 1).sum())
            total += len(Y)
            if ratio is not None:
                chosen = ratio.gather(-1, bt[..., None])[..., 0]
                right_ratios.extend(chosen[valid].cpu().tolist())
                wrong_ratios.extend(chosen[~valid].cpu().tolist())
            for raw, port in ((model.place(K), model.key_port),
                              (model.place(Cn), model.socket_port)):
                if not positions:
                    raw = torch.cat((raw[..., :1], torch.zeros_like(raw[..., 1:])), -1)
                port_norms.extend(port(raw).flatten(-2).norm(dim=-1).flatten().cpu().tolist())
    model.train()
    result = {"accuracy": hits / total, "designated_accuracy": designated / total,
              "ambiguous": ambiguous, "n": total,
              "port_norm_min": float(np.min(port_norms)),
              "port_norm_p01": float(np.quantile(port_norms, 0.01)),
              "port_norm_median": float(np.median(port_norms))}
    if right_ratios:
        result.update(ratio_right=float(np.mean(right_ratios)),
                      ratio_wrong=float(np.mean(wrong_ratios)),
                      right_ratio_below_005=float(np.mean(np.asarray(right_ratios) < 0.05)),
                      wrong_ratio_below_005=float(np.mean(np.asarray(wrong_ratios) < 0.05)))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--sym", choices=("free", "spin", "flat"), default="flat")
    ap.add_argument("--kinds", default="dist,dist_dual,socket,socket_dual,random_dual")
    ap.add_argument("--train-size", type=int, default=6000)
    ap.add_argument("--test-size", type=int, default=2000)
    ap.add_argument("--ntest", type=int, default=2000)
    ap.add_argument("--save-dir")
    ap.add_argument("--out", default="r6_ports.json")
    a = ap.parse_args()
    if min(a.steps, a.seeds, a.batch, a.train_size, a.test_size, a.ntest) < 1:
        ap.error("steps, seeds, batch and dataset sizes must be positive")
    if a.save_dir:
        Path(a.save_dir).mkdir(parents=True, exist_ok=True)
    rotations = quat_R(spin_quats()).to(a.device)
    # These eight SO(3) rotations preserve the plane and implement all of D4.
    flip = torch.diag(torch.tensor([1., -1., -1.], device=a.device))
    all_turns = torch.cat((rotations, rotations @ flip))
    rows = []
    for seed in range(a.seeds):
        Ptr, Pte = Q.pool(seed, a.train_size), Q.pool(10_000 + seed, a.test_size)
        for kind in a.kinds.split(","):
            if kind not in {"dist", "dist_dual", "socket", "socket_dual", "random_dual"}:
                ap.error(f"unknown kind: {kind}")
            torch.manual_seed(seed)
            model = PortBridge(kind, sym=a.sym, seed=seed).to(a.device)
            opt = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=3e-3)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.steps)
            rng = np.random.default_rng(seed)
            t0 = time.time()
            for _ in range(a.steps):
                K, Cn, Y = Q.batch(rng, a.batch, ROT, P=Ptr, near_n=7,
                                   fmin=1, fmax=1, nkind="move")
                # Equal probability among all valid targets, including accidental matches.
                valid = valid_matches(K, Cn, mirrors=False).to(a.device)
                targets = valid.float() / valid.sum(-1, keepdim=True)
                logits = model(K.to(a.device), Cn.to(a.device), rotations)
                loss = -(targets * F.log_softmax(logits, -1)).sum(-1).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
                sched.step()
            row = {"kind": kind, "seed": seed, "sym": a.sym, "steps": a.steps,
                   "loss": float(loss.detach()),
                   "params": sum(p.numel() for p in model.parameters() if p.requires_grad),
                   "temperature": float(model.log_tau.exp().detach())}
            for label, turns, R in (("rot", ROT, rotations), ("mirror", MIR, all_turns)):
                row[label] = evaluate(model, Pte, turns, a.ntest, 20_000 + seed, a.device, R)
            row["mirror_no_positions"] = evaluate(model, Pte, MIR, a.ntest,
                20_000 + seed, a.device, all_turns, positions=False)
            row["seconds"] = round(time.time() - t0, 1)
            rows.append(row)
            if a.save_dir:
                torch.save({"state_dict": model.state_dict(), "config": vars(a),
                            "kind": kind, "seed": seed},
                           Path(a.save_dir) / f"{kind}_s{seed}.pt")
            Path(a.out).write_text(json.dumps({"config": vars(a), "results": rows}, indent=2))
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
