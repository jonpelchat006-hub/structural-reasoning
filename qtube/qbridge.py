"""qbridge.py - round 5b (Nov 1 2026): the sedenion bridge on top of the flat-object quaternion nodes.

Each node is 4 placed quaternions (w + x i + y j, from 4 attention heads over the picture), read as one sedenion
((q0, q1), (q2, q3)). A turn Q moves all four by Q q Q^-1 (blockwise, which is an automorphism of the sedenions: it
keeps every product and every zero). The key's node meets the candidate's node at the bridge, ratio |a b| / (|a||b|).
  dist           the control: the same nodes, scored by the squared distance of their 16 numbers (no bridge)
  socket         score = -ratio with the sedenion table (zero = fits, Jonathan's socket reading)
  socket_random  the same with a random table of the same shape
Trained on rotations only with her 8 learned turns (same task as rounds 2-4). Tested on rotations and on mirrors with
  turns  her 8 learned turns
  spins  the 4 quarter spins inside the picture's plane
  cube   the 24 turns of a cube (48 unit quaternions), which include turning the picture over

    python qbridge.py --device cuda --seeds 3 --steps 3000 --out r5_bridge.json
"""
from __future__ import annotations
import argparse, itertools, json, math, time
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F

import qtest as Q
from qlift import SymConv, grid, ROT, MIR


def quat_R(Qs):
    w, x, y, z = F.normalize(Qs, dim=-1).unbind(-1)
    return torch.stack([torch.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
                        torch.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
                        torch.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)


def cube_quats():
    """the binary octahedral group: 48 unit quaternions, the 24 turns of a cube (each twice)"""
    out = []
    for i in range(4):
        for s in (1, -1):
            v = np.zeros(4); v[i] = s; out.append(v)
    for signs in itertools.product((0.5, -0.5), repeat=4): out.append(np.array(signs))
    r = 1 / math.sqrt(2)
    for i, j in itertools.combinations(range(4), 2):
        for si, sj in itertools.product((r, -r), repeat=2):
            v = np.zeros(4); v[i] = si; v[j] = sj; out.append(v)
    return torch.tensor(np.stack(out), dtype=torch.float32)


def spin_quats():
    return torch.tensor([[math.cos(k * math.pi / 4), 0, 0, math.sin(k * math.pi / 4)] for k in range(4)], dtype=torch.float32)


class Bridge(nn.Module):
    def __init__(s, kind, sym="free", nodes=12, heads=4, ch=24, turns=8, seed=0):
        super().__init__()
        s.kind, s.nodes, s.heads = kind, nodes, heads
        s.c1, s.c2 = SymConv(1, ch, 5, sym), SymConv(ch, ch, 5, sym)
        s.c3 = SymConv(ch, 2 * nodes * heads, 1, sym)
        s.register_buffer("G", grid())
        s.register_buffer("C16", Q.table(16, random_seed=1000 + seed) if kind == "socket_random" else Q.table(16))
        s.T = nn.Parameter(torch.randn(turns, 4))
        s.log_tau = nn.Parameter(torch.tensor(math.log(10.0) if kind != "dist" else 0.0))

    def place(s, X):                                                            # (..., 49) -> (..., nodes, heads, 4)
        sh = X.shape[:-1]; nh = s.nodes * s.heads
        h = F.gelu(s.c1(X.reshape(-1, 1, 7, 7))); h = F.gelu(s.c2(h)); h = s.c3(h).flatten(2)
        a = torch.softmax(h[:, :nh], -1)
        pos = a @ s.G; w = (a * h[:, nh:]).sum(-1)
        q = torch.cat([w[..., None], pos, torch.zeros_like(pos[..., :1])], -1)
        return q.reshape(*sh, s.nodes, s.heads, 4)

    def scores(s, K, Cn, R):
        """R: (M, 3, 3) moves -> (B, 8, M) scores, and the bridge ratios (B, 8, M) when there is a bridge"""
        qk, qc = s.place(K), s.place(Cn)                                        # (B, n, h, 4), (B, 8, n, h, 4)
        v = torch.einsum("mab,...nhb->...mnha", R, qk[..., 1:])               # each of the 4 quaternions moved by Q q Q^-1
        w = qk[..., :1].unsqueeze(-4).expand(*v.shape[:-1], 1)
        a = torch.cat([w, v], -1).flatten(-2)[:, None]                         # (B, 1, M, n, 16) the key, moved
        b = qc.flatten(-2)[:, :, None]                                          # (B, 8, 1, n, 16)
        B, M = qk.shape[0], R.shape[0]
        a = a.expand(B, qc.shape[1], M, s.nodes, 16); b = b.expand_as(a)
        if s.kind == "dist":
            return -((a - b) ** 2).sum(-1).mean(-1), None
        ratio = Q.prod(a, b, s.C16).norm(dim=-1) / (a.norm(dim=-1) * b.norm(dim=-1) + 1e-6)
        return -ratio.mean(-1), ratio.mean(-1)

    def forward(s, K, Cn, R=None):
        sc, _ = s.scores(K, Cn, quat_R(s.T) if R is None else R)
        return s.log_tau.exp() * sc.max(-1).values


def evaluate(m, rng, turns, n, device, P, R, bs=50):
    m.eval(); right = 0; rr, rw = [], []
    with torch.no_grad():
        for _ in range(n // bs):
            K, Cn, Y = Q.batch(rng, bs, turns, P=P, near_n=7, fmin=1, fmax=1, nkind="move")
            K, Cn, Y = K.to(device), Cn.to(device), Y.to(device)
            sc, ratio = m.scores(K, Cn, R)
            best, bt = sc.max(-1); pred = best.argmax(-1); right += int((pred == Y).sum())
            if ratio is not None:
                bi = torch.arange(len(Y), device=device)
                r = ratio.gather(-1, bt[..., None])[..., 0]                    # (B, 8) ratio at each candidate's best move
                mask = F.one_hot(Y, 8).bool()
                rr.append(r[mask].mean().item()); rw.append(r[~mask].mean().item())
    m.train()
    return right / (n // bs * bs), (round(float(np.mean(rr)), 4) if rr else None), (round(float(np.mean(rw)), 4) if rw else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--kinds", default="dist,socket,socket_random")
    ap.add_argument("--sym", default="free")
    ap.add_argument("--ntest", type=int, default=2000)
    ap.add_argument("--out", default="r5_bridge.json")
    a = ap.parse_args()
    CUBE, SPIN = quat_R(cube_quats()).to(a.device), quat_R(spin_quats()).to(a.device)
    res = []
    for kind in a.kinds.split(","):
        for seed in range(a.seeds):
            torch.manual_seed(seed); rng = np.random.default_rng(seed)
            m = Bridge(kind, sym=a.sym, seed=seed).to(a.device)
            opt = torch.optim.Adam(m.parameters(), lr=3e-3)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.steps)
            Ptr, Pte = Q.pool(seed, 20000), Q.pool(10_000 + seed, 4000)
            t0 = time.time()
            for step in range(a.steps):
                K, Cn, Y = Q.batch(rng, a.batch, ROT, P=Ptr, near_n=7, fmin=1, fmax=1, nkind="move")
                loss = F.cross_entropy(m(K.to(a.device), Cn.to(a.device)), Y.to(a.device))
                opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            row = {"kind": kind, "sym": a.sym, "seed": seed, "steps": a.steps, "params": sum(p.numel() for p in m.parameters()),
                   "loss": round(float(loss), 4)}
            for mode, R in (("turns", None), ("spins", SPIN), ("cube", CUBE)):
                for label, turns in (("rot", ROT), ("mirror", MIR)):
                    RR = quat_R(m.T).detach() if R is None else R
                    acc, r_right, r_wrong = evaluate(m, np.random.default_rng(10_000 + seed), turns, a.ntest, a.device, Pte, RR)
                    row[f"{mode}_{label}"] = round(acc, 4)
                    if r_right is not None: row[f"{mode}_{label}_ratio_right"] = r_right; row[f"{mode}_{label}_ratio_wrong"] = r_wrong
            row["seconds"] = round(time.time() - t0, 1)
            res.append(row); print(json.dumps(row), flush=True)
            json.dump(res, open(a.out, "w"), indent=1)
    print("\nsummary (mean over seeds):")
    for kind in a.kinds.split(","):
        rs = [r for r in res if r["kind"] == kind]
        f = lambda k: np.mean([r[k] for r in rs]) if all(k in r for r in rs) else float("nan")
        print(f"  {kind:13s} rotations: turns {f('turns_rot'):.3f} spins {f('spins_rot'):.3f} cube {f('cube_rot'):.3f} | "
              f"mirrors: turns {f('turns_mirror'):.3f} spins {f('spins_mirror'):.3f} cube {f('cube_mirror'):.3f}"
              f" | ratio right/wrong (turns, rotations) {f('turns_rot_ratio_right'):.3f}/{f('turns_rot_ratio_wrong'):.3f}")


if __name__ == "__main__":
    main()
