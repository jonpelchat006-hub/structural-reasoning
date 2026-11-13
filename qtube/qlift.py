"""qlift.py - round 4 (Nov 1 2026): the picture enters her space as a flat object, and a mirror is the same thing moved.

Jonathan: "to actually mirror something she would just kind of pick up the thing as a picture and move it? so one method
wouldnt be the same thing to her while the other should be the same thing just moved."

Each picture -> 24 nodes, each a quaternion w + x i + y j + 0 k: (x, y) = where the node sits in the picture (an
attention-weighted spot over the cells), w = what it is (a feature). A turn Q moves a node by Q q Q^-1 (w stays, the
position turns in 3D). Trained on rotations only with her 8 learned turns (same task as rounds 2-3: a key, 8 candidates,
7 near-misses with one cell moved). Tested on rotations and on mirrors three ways:
  turns  her 8 learned turns
  spin   the best turn inside the picture's plane (closed form)
  lift   the best 3D move, so picking it up and turning it over is allowed (closed form: for flat things the best 3D
         move is the best spin or the best flip)
Placement nets (two 5x5 convs over the picture, then attention):
  free   no constraint: keeping "the same thing, moved" under quarter turns has to be learned from the examples
  spin   kernels averaged over the 4 quarter turns: placements turn exactly with the picture, but may come out handed
  flat   kernels averaged over all 8 turns: placements also mirror exactly (the check: works by construction)
Handedness: |place(turned picture) - turned(place(picture))|, for a quarter turn and for a mirror.
--mirror-examples N mixes a fixed handful of N mirror examples into training (2 per batch).

    python qlift.py --device cuda --seeds 3 --steps 3000 --out r4_lift.json
"""
from __future__ import annotations
import argparse, json, math, time
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F

import qtest as Q

ROT, MIR = [0, 1, 2, 3], [4, 5, 6, 7]


def grid():
    r, c = np.divmod(np.arange(49), 7)
    return torch.tensor(np.stack([c - 3, 3 - r], 1), dtype=torch.float32)        # x across, y up


def turn_matrix(t):
    """the 2x2 map of positions that TURNS[t] makes on the picture"""
    G = grid().numpy(); M = []
    for idx in (3 * 7 + 4, 2 * 7 + 3):                                          # cells at (1, 0) and (0, 1)
        g = np.zeros((7, 7)); g.flat[idx] = 1
        j = int(np.argmax(Q.TURNS[t](g))); M.append(G[j])
    return torch.tensor(np.stack(M, 1), dtype=torch.float32)                   # columns: images of (1,0), (0,1)


def d4(W):
    out = []
    for f in (False, True):
        V = torch.flip(W, dims=(-1,)) if f else W
        for k in range(4): out.append(torch.rot90(V, k, dims=(-2, -1)))
    return out


class SymConv(nn.Module):
    def __init__(s, cin, cout, k, sym):
        super().__init__()
        s.W = nn.Parameter(torch.randn(cout, cin, k, k) / math.sqrt(cin * k * k)); s.b = nn.Parameter(torch.zeros(cout))
        s.sym, s.pad = sym, k // 2

    def forward(s, x):
        W = s.W if s.sym == "free" else torch.stack(d4(s.W)[:4] if s.sym == "spin" else d4(s.W)).mean(0)
        return F.conv2d(x, W, s.b, padding=s.pad)


class Lift(nn.Module):
    def __init__(s, sym, nodes=24, ch=24, turns=8, no_pos=False, sharp=1.0, on_shape=False):
        super().__init__()
        s.sharp, s.on_shape = sharp, on_shape                                   # round 5: nodes sit at real spots
        s.no_pos = no_pos                                                       # control: nodes have no place, only w
        s.c1, s.c2, s.c3 = SymConv(1, ch, 5, sym), SymConv(ch, ch, 5, sym), SymConv(ch, 2 * nodes, 1, sym)
        s.nodes = nodes
        s.register_buffer("G", grid())
        s.T = nn.Parameter(torch.randn(turns, 4))                                  # her big set: 8 learned turns
        s.log_tau = nn.Parameter(torch.tensor(0.0))

    def place(s, X):                                                            # (..., 49) -> pos (..., n, 2), w (..., n)
        sh = X.shape[:-1]
        h = F.gelu(s.c1(X.reshape(-1, 1, 7, 7))); h = F.gelu(s.c2(h)); h = s.c3(h).flatten(2)
        lg = h[:, :s.nodes] * s.sharp
        if s.on_shape:                                                          # a node can only sit on the shape's cells
            lg = lg.masked_fill(X.reshape(-1, 1, 49) <= 0, -1e9)
        a = torch.softmax(lg, -1)
        pos = (a @ s.G) * (0.0 if s.no_pos else 1.0)
        return pos.reshape(*sh, s.nodes, 2), (a * h[:, s.nodes:]).sum(-1).reshape(*sh, s.nodes)

    def R(s):                                                                   # unit quaternions -> 3x3 rotations
        w, x, y, z = F.normalize(s.T, dim=-1).unbind(-1)
        return torch.stack([torch.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
                            torch.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
                            torch.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1)], -2)

    def dist(s, K, Cn, mode):
        pk, wk = s.place(K); pc, wc = s.place(Cn)                               # key (B, n, .), candidates (B, 8, n, .)
        pk, wk = pk[:, None], wk[:, None]
        dw = ((wk - wc) ** 2).sum(-1)
        if mode.endswith("_where"):                                             # only where the nodes sit decides
            dw = dw * 0; mode = mode[:-6]
        if mode == "turns":
            z = torch.zeros_like(pk[..., :1])
            Rp = torch.einsum("tab,...nb->...tna", s.R(), torch.cat([pk, z], -1))           # (B, 1, T, n, 3)
            pc3 = torch.cat([pc, torch.zeros_like(pc[..., :1])], -1)[:, :, None]           # (B, 8, 1, n, 3)
            return ((Rp - pc3) ** 2).sum((-1, -2)).min(-1).values + dw
        nk, nc = (pk ** 2).sum((-1, -2)), (pc ** 2).sum((-1, -2))
        xk, yk, xc, yc = pk[..., 0], pk[..., 1], pc[..., 0], pc[..., 1]
        best = torch.sqrt(((xk * xc + yk * yc).sum(-1)) ** 2 + ((xk * yc - yk * xc).sum(-1)) ** 2 + 1e-12)
        if mode == "lift":                                                      # flipped over: key (x, y) -> (x, -y)
            flip = torch.sqrt(((xk * xc - yk * yc).sum(-1)) ** 2 + ((xk * yc + yk * xc).sum(-1)) ** 2 + 1e-12)
            best = torch.maximum(best, flip)
        return nk + nc - 2 * best + dw

    def forward(s, K, Cn, mode="turns"):
        return -s.log_tau.exp() * s.dist(K, Cn, mode)


def evaluate(m, rng, turns, n, device, P, mode, bs=250):
    m.eval(); right = 0
    with torch.no_grad():
        for _ in range(n // bs):
            K, Cn, Y = Q.batch(rng, bs, turns, P=P, near_n=7, fmin=1, fmax=1, nkind="move")
            right += int((m(K.to(device), Cn.to(device), mode).argmax(-1).cpu() == Y).sum())
    m.train()
    return right / (n // bs * bs)


def handedness(m, P, device, n=1000):
    """|place(turned) - turned(place)| in cell units, for a quarter turn (t=1) and a mirror (t=4); w gaps too"""
    m.eval(); out = {}
    with torch.no_grad():
        X = torch.tensor(P[:n].reshape(n, 8, 49)).to(device)
        p0, w0 = m.place(X[:, 0])
        for name, t in (("quarter_turn", 1), ("mirror", 4)):
            pt, wt = m.place(X[:, t])
            M = turn_matrix(t).to(device)
            out[name + "_pos_gap"] = round(float((pt - p0 @ M.T).norm(dim=-1).mean()), 4)
            out[name + "_w_gap"] = round(float((wt - w0).abs().mean() / (w0.abs().mean() + 1e-9)), 4)
        out["node_spread"] = round(float(p0.norm(dim=-1).mean()), 4)
    m.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--syms", default="free,spin,flat")
    ap.add_argument("--mirror-examples", type=int, default=0)
    ap.add_argument("--no-pos", action="store_true", help="control: positions switched off")
    ap.add_argument("--sharp", type=float, default=1.0, help="sharpen node placement (attention logits x this)")
    ap.add_argument("--on-shape", action="store_true", help="nodes can only sit on the shape's own cells")
    ap.add_argument("--ntest", type=int, default=2000)
    ap.add_argument("--out", default="r4_lift.json")
    a = ap.parse_args()
    res = []
    for sym in a.syms.split(","):
        for seed in range(a.seeds):
            torch.manual_seed(seed); rng = np.random.default_rng(seed)
            m = Lift(sym, no_pos=a.no_pos, sharp=a.sharp, on_shape=a.on_shape).to(a.device)
            opt = torch.optim.Adam(m.parameters(), lr=3e-3)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.steps)
            Ptr, Pte = Q.pool(seed, 20000), Q.pool(10_000 + seed, 4000)
            if a.mirror_examples:
                Km, Cm, Ym = Q.batch(np.random.default_rng(500 + seed), a.mirror_examples, MIR, P=Ptr, near_n=7, fmin=1, fmax=1, nkind="move")
            t0 = time.time()
            for step in range(a.steps):
                K, Cn, Y = Q.batch(rng, a.batch, ROT, P=Ptr, near_n=7, fmin=1, fmax=1, nkind="move")
                if a.mirror_examples:                                          # 2 of the handful, every batch
                    j = torch.tensor(rng.integers(a.mirror_examples, size=2))
                    K, Cn, Y = torch.cat([K[2:], Km[j]]), torch.cat([Cn[2:], Cm[j]]), torch.cat([Y[2:], Ym[j]])
                loss = F.cross_entropy(m(K.to(a.device), Cn.to(a.device)), Y.to(a.device))
                opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            row = {"sym": sym, "seed": seed, "steps": a.steps, "mirror_examples": a.mirror_examples, "no_pos": a.no_pos, "sharp": a.sharp, "on_shape": a.on_shape,
                   "params": sum(p.numel() for p in m.parameters()), "loss": round(float(loss), 4)}
            for mode in ("turns", "spin", "lift", "spin_where", "lift_where"):
                for label, turns in (("rot", ROT), ("mirror", MIR)):
                    row[f"{mode}_{label}"] = round(evaluate(m, np.random.default_rng(10_000 + seed), turns, a.ntest, a.device, Pte, mode), 4)
            row.update(handedness(m, Pte, a.device)); row["seconds"] = round(time.time() - t0, 1)
            res.append(row); print(json.dumps(row), flush=True)
            json.dump(res, open(a.out, "w"), indent=1)
    print("\nsummary (mean over seeds):")
    for sym in a.syms.split(","):
        rs = [r for r in res if r["sym"] == sym]
        f = lambda k: np.mean([r[k] for r in rs])
        print(f"  {sym:5s} mirror-examples {a.mirror_examples:3d} | rotations: turns {f('turns_rot'):.3f} spin {f('spin_rot'):.3f} "
              f"lift {f('lift_rot'):.3f} | mirrors: turns {f('turns_mirror'):.3f} spin {f('spin_mirror'):.3f} lift {f('lift_mirror'):.3f}"
              f" | where only: spin {f('spin_where_mirror'):.3f} lift {f('lift_where_mirror'):.3f} (rotations {f('spin_where_rot'):.3f})"
              f" | handed gap: quarter {f('quarter_turn_pos_gap'):.3f} mirror {f('mirror_pos_gap'):.3f} (spread {f('node_spread'):.2f})")


if __name__ == "__main__":
    main()
