"""qtest.py - the first test of the nested quaternion model (Nov 1 2026). See NESTED_QUATERNION_MODEL.md.

Task (the ls20 rotator in miniature): a key picture (7x7) and 8 candidates; one candidate is the key turned by a quarter
turn and/or mirrored, the others are other pictures (turned too) or near-misses (the key turned, with 1-3 cells flipped).
Pick the match.

Training uses four of the eight turns {identity, 90, 180, mirror}. Tests use new pictures with (a) those four turns and
(b) the four turns never seen in training {270, mirror+90, mirror+180, mirror+270}: does the model learn the turning, or
only the turns it was shown?

Models (all: encoder -> 8 nodes x 16 numbers, then 8 learned turns, best turn wins; parameter counts matched):
  real          ordinary real-valued network, turns are learned 4x4 matrices          (the control the warning asks for)
  quat          quaternion layers, turns are unit quaternions Q q Q^-1, cosine score   (flat quaternion model)
  nested_fit    quaternion layers; each node is a sedenion ((node, cube), pins); the score is the bridge product
                with the key's sedenion, and a MATCH is a product near ZERO (Jonathan's socket reading)
  nested_loss   the same, but a match is a LARGE product and non-matches go to zero (the other reading)
  nested_random nested_fit with the sedenion table replaced by a random table of the same shape (does the algebra matter?)

    python qtest.py --steps 3000 --seeds 3 --device cuda --out qtest_results.json
"""
from __future__ import annotations
import argparse, json, math, time
import numpy as np
import torch, torch.nn as nn, torch.nn.functional as F

import cayley

# ------------------------------------------------------------------------------------------------ the algebra tables
def table(n, random_seed=None):
    """C[i,j,k] = coefficient of e_k in e_i e_j (Cayley-Dickson); with random_seed, a random table of the same shape
    (each (i,j) goes to a random k with a random sign; e_0 stays the identity)"""
    C = np.zeros((n, n, n), dtype=np.float32)
    rng = np.random.default_rng(random_seed) if random_seed is not None else None
    for i in range(n):
        for j in range(n):
            if rng is None:
                p = cayley.mul(cayley.e(i, n), cayley.e(j, n))
                k = int(np.argmax(np.abs(p))); C[i, j, k] = p[k]
            else:
                if i == 0: C[i, j, j] = 1.0
                elif j == 0: C[i, j, i] = 1.0
                else: C[i, j, int(rng.integers(n))] = float(rng.choice([-1.0, 1.0]))
    return torch.tensor(C)


def prod(a, b, C):
    return torch.einsum("...i,...j,ijk->...k", a, b, C)


def qconj(q):
    return torch.cat([q[..., :1], -q[..., 1:]], -1)


# ------------------------------------------------------------------------------------------------ the pictures
TURNS = [lambda g: g, lambda g: np.rot90(g, 1), lambda g: np.rot90(g, 2), lambda g: np.rot90(g, 3),
         lambda g: np.fliplr(g), lambda g: np.rot90(np.fliplr(g), 1), lambda g: np.rot90(np.fliplr(g), 2),
         lambda g: np.rot90(np.fliplr(g), 3)]
SEEN, UNSEEN = [0, 1, 2, 4], [3, 5, 6, 7]


def shape(rng, n=7):
    """a random connected shape of 10-18 cells on an n x n grid"""
    g = np.zeros((n, n), dtype=np.float32)
    r, c = rng.integers(1, n - 1, size=2); g[r, c] = 1
    target = rng.integers(10, 19)
    while g.sum() < target:
        rr, cc = np.argwhere(g > 0)[rng.integers(int(g.sum()))]
        dr, dc = [(0, 1), (1, 0), (0, -1), (-1, 0)][rng.integers(4)]
        if 0 <= rr + dr < n and 0 <= cc + dc < n: g[rr + dr, cc + dc] = 1
    return g


POOLS = {}


def pool(seed, n):
    """n shapes with all 8 turns precomputed: (n, 8, 7, 7). Training and test pools use different seeds (new pictures)."""
    if (seed, n) not in POOLS:
        r = np.random.default_rng(seed)
        S = np.stack([shape(r) for _ in range(n)])
        POOLS[(seed, n)] = np.stack([np.stack([TURNS[t](s) for t in range(8)]) for s in S]).astype(np.float32)
    return POOLS[(seed, n)]


def batch(rng, B, turns, ncand=8, P=None, near_n=3, fmin=1, fmax=3, nkind="flip"):
    """key, 8 candidates (the match turned; 3 near-misses: the key turned with 1-3 cells flipped; 4 other pictures turned)"""
    n = len(P); turns = np.asarray(turns)
    ki = rng.integers(n, size=B)
    K = P[ki, 0]                                                   # the key, as drawn
    tm = turns[rng.integers(len(turns), size=(B, 1 + near_n))]
    match = P[ki, tm[:, 0]]
    near = P[ki[:, None], tm[:, 1:]].copy()                        # (B, near_n, 7, 7)
    nflip = rng.integers(fmin, fmax + 1, size=(B, near_n))
    cells = np.argsort(rng.random((B, near_n, 49)), -1)[..., :fmax]    # distinct cells per near-miss
    if nkind == "flip":                                            # flip fmin-fmax cells (the cell count changes)
        for f in range(fmax):
            bi, ci = np.nonzero(nflip > f)
            cell = cells[bi, ci, f]
            near[bi, ci, cell // 7, cell % 7] = 1 - near[bi, ci, cell // 7, cell % 7]
    else:                                                          # "move": a filled cell goes to an empty one (same count)
        fl = near.reshape(B, near_n, 49)
        for f in range(fmax):
            bi, ci = np.nonzero(nflip > f)
            sub = fl[bi, ci]
            on = np.argmax(np.where(sub > 0, rng.random(sub.shape), -1), -1)
            off = np.argmax(np.where(sub == 0, rng.random(sub.shape), -1), -1)
            fl[bi, ci, on] = 0; fl[bi, ci, off] = 1
        near = fl.reshape(B, near_n, 7, 7)
    n_other = ncand - 1 - near_n
    oi = rng.integers(n, size=(B, n_other)); to = turns[rng.integers(len(turns), size=(B, n_other))]
    other = P[oi, to]
    cands = np.concatenate([match[:, None], near, other], 1)       # (B, 8, 7, 7), the match first
    perm = np.argsort(rng.random((B, ncand)), 1)
    cands = np.take_along_axis(cands, perm[:, :, None, None], 1)
    Y = np.argmax(perm == 0, 1)
    return (torch.tensor(np.ascontiguousarray(K.reshape(B, 49))), torch.tensor(np.ascontiguousarray(cands.reshape(B, ncand, 49))),
            torch.tensor(Y))


# ------------------------------------------------------------------------------------------------ layers
class QLinear(nn.Module):
    """quaternion layer: out_o = sum_i W_oi (x) x_i + b_o (Hamilton products): 1/4 of a real layer's weights"""
    def __init__(s, nin, nout, C4):
        super().__init__()
        s.W = nn.Parameter(torch.randn(nout, nin, 4) / math.sqrt(4 * nin)); s.b = nn.Parameter(torch.zeros(nout, 4))
        s.register_buffer("C", C4)

    def forward(s, x):                                              # x: (..., nin, 4)
        return torch.einsum("oia,...ib,abk->...ok", s.W, x, s.C) + s.b


class QEncoder(nn.Module):
    def __init__(s, C4, h=48, nodes=8):
        super().__init__()
        s.l1, s.l2, s.l3 = QLinear(13, h, C4), QLinear(h, h, C4), QLinear(h, nodes * 4, C4)
        s.nodes = nodes

    def forward(s, x):                                              # x: (..., 49)
        x = F.pad(x, (0, 3)).reshape(*x.shape[:-1], 13, 4)
        x = F.gelu(s.l1(x)); x = F.gelu(s.l2(x)); x = s.l3(x)
        return x.reshape(*x.shape[:-2], s.nodes, 4, 4)              # (..., nodes, 4 quaternions, 4)


class REncoder(nn.Module):
    def __init__(s, h=72, nodes=8):
        super().__init__()
        s.net = nn.Sequential(nn.Linear(52, h), nn.GELU(), nn.Linear(h, h), nn.GELU(), nn.Linear(h, nodes * 16))
        s.nodes = nodes

    def forward(s, x):
        x = s.net(F.pad(x, (0, 3)))
        return x.reshape(*x.shape[:-1], s.nodes, 4, 4)


class Model(nn.Module):
    def __init__(s, kind, turns=8, seed=0, mirror_turns=0):
        super().__init__()
        s.kind = kind
        s.register_buffer("mirror", torch.arange(turns) >= turns - mirror_turns)   # mirror turns: Q q* Q^-1
        C4 = table(4)
        s.register_buffer("C4", C4)
        s.register_buffer("C16", table(16, random_seed=1000 + seed) if kind == "nested_random" else table(16))
        s.enc = REncoder() if kind == "real" else QEncoder(C4)
        if kind == "real":
            s.T = nn.Parameter(torch.eye(4).repeat(turns, 1, 1) + 0.3 * torch.randn(turns, 4, 4))
        else:
            s.T = nn.Parameter(torch.randn(turns, 4))                  # her big set: 8 turns (unit quaternions)
        s.tau = nn.Parameter(torch.tensor(10.0))

    def turn(s, z):                                                 # z: (..., nodes, 4, 4) -> (..., turns, nodes, 4, 4)
        if s.kind == "real":
            return torch.einsum("tab,...nqb->...tnqa", s.T, z)
        Q = F.normalize(s.T, dim=-1)                                # Q q Q^-1 on each of the node's 4 quaternions
        Qb = Q[:, None, None, :]
        zz = z.unsqueeze(-4)
        if bool(s.mirror.any()):                                    # q* flips the three planes: a mirror-type turn
            zz = torch.where(s.mirror.view(-1, 1, 1, 1), qconj(zz), zz)
        return prod(prod(Qb, zz, s.C4), qconj(Qb), s.C4)

    def forward(s, K, Cn):
        zk = s.enc(K)                                               # (B, nodes, 4, 4)
        zc = s.turn(s.enc(Cn))                                      # (B, ncand, turns, nodes, 4, 4)
        zk = zk[:, None, None]
        if s.kind in ("real", "quat"):
            sc = F.cosine_similarity(zk.flatten(-2), zc.flatten(-2), dim=-1).mean(-1)      # (B, ncand, turns)
        else:
            a, b = zk.flatten(-2), zc.flatten(-2)                   # sedenions: ((node, cube), pins)
            p = prod(a.expand_as(b), b, s.C16)                      # the bridge
            ratio = p.norm(dim=-1) / (a.norm(dim=-1) * b.norm(dim=-1) + 1e-6)
            sc = (-ratio if s.kind != "nested_loss" else ratio).mean(-1)
            s.last_ratio = ratio.mean(-1)
        best, _ = sc.max(-1)                                        # she turns to the face that fits best
        return s.tau * best


def params(m): return sum(p.numel() for p in m.parameters())


def evaluate(m, rng, turns, n, device, bs=250, P=None, **bk):
    m.eval(); right = 0; rm, rn = [], []
    with torch.no_grad():
        for _ in range(n // bs):
            K, Cn, Y = batch(rng, bs, turns, P=P, **bk)
            K, Cn, Y = K.to(device), Cn.to(device), Y.to(device)
            out = m(K, Cn); right += int((out.argmax(-1) == Y).sum())
            if hasattr(m, "last_ratio"):
                r = m.last_ratio.max(-1).values if m.kind == "nested_loss" else m.last_ratio.min(-1).values
                mask = F.one_hot(Y, r.shape[1]).bool()
                rm.append(r[mask].mean().item()); rn.append(r[~mask].mean().item())
    m.train()
    return right / (n // bs * bs), (float(np.mean(rm)) if rm else None), (float(np.mean(rn)) if rn else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--kinds", default="real,quat,nested_fit,nested_loss,nested_random")
    ap.add_argument("--ntest", type=int, default=2000)
    ap.add_argument("--out", default="qtest_results.json")
    ap.add_argument("--split", default="quarter", choices=["quarter", "rotmirror"])
    ap.add_argument("--near", type=int, default=3, help="near-misses among the 7 wrong candidates")
    ap.add_argument("--flips", default="1-3", help="cells flipped in a near-miss, e.g. 1-1")
    ap.add_argument("--nkind", default="flip", choices=["flip", "move"], help="move keeps the cell count")
    ap.add_argument("--mirror-turns", type=int, default=0, help="how many of the 8 turns are Q q* Q^-1 (not for real)")
    ap.add_argument("--save-dir", default=None, help="save each trained model here (for rivers.py)")
    ap.add_argument("--steps-list", default=None, help="comma list of step budgets (overrides --steps)")
    a = ap.parse_args()
    global SEEN, UNSEEN
    if a.split == "rotmirror": SEEN, UNSEEN = [0, 1, 2, 3], [4, 5, 6, 7]
    fmin, fmax = [int(x) for x in a.flips.split("-")]
    bk = dict(near_n=a.near, fmin=fmin, fmax=fmax, nkind=a.nkind)
    res = []
    budgets = [int(x) for x in a.steps_list.split(",")] if a.steps_list else [a.steps]
    for steps_, kind, seed in [(st, k, sd) for st in budgets for k in a.kinds.split(",") for sd in range(a.seeds)]:
        a.steps = steps_
        if True:
            torch.manual_seed(seed); rng = np.random.default_rng(seed)
            m = Model(kind, seed=seed, mirror_turns=0 if kind == "real" else a.mirror_turns).to(a.device)
            opt = torch.optim.Adam(m.parameters(), lr=3e-3)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.steps)
            t0 = time.time()
            Ptr, Pte = pool(seed, 20000), pool(10_000 + seed, 4000)   # the test pictures are never seen in training
            for step in range(a.steps):
                K, Cn, Y = batch(rng, a.batch, SEEN, P=Ptr, **bk)
                loss = F.cross_entropy(m(K.to(a.device), Cn.to(a.device)), Y.to(a.device))
                opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            trng = np.random.default_rng(10_000 + seed)
            acc_in, rm_in, rn_in = evaluate(m, trng, SEEN, a.ntest, a.device, P=Pte, **bk)
            acc_out, rm_out, rn_out = evaluate(m, trng, UNSEEN, a.ntest, a.device, P=Pte, **bk)
            row = {"kind": kind, "seed": seed, "steps": a.steps, "split": a.split, "near": a.near, "nkind": a.nkind, "mirror_turns": 0 if kind == "real" else a.mirror_turns, "flips": a.flips, "params": params(m), "loss": round(float(loss), 4),
                   "acc_seen_turns": round(acc_in, 4), "acc_unseen_turns": round(acc_out, 4),
                   "bridge_match": rm_in, "bridge_nonmatch": rn_in, "seconds": round(time.time() - t0, 1)}
            if a.save_dir:
                import os; os.makedirs(a.save_dir, exist_ok=True)
                torch.save(m.state_dict(), os.path.join(a.save_dir, f"{kind}_s{seed}_st{a.steps}_{a.split}_m{row['mirror_turns']}.pt"))
            res.append(row); print(json.dumps(row), flush=True)
            json.dump(res, open(a.out, "w"), indent=1)
    print("\nsummary (mean over seeds):")
    for st, kind in [(st, k) for st in budgets for k in a.kinds.split(",")]:
        rs = [r for r in res if r["kind"] == kind and r["steps"] == st]
        print(f"  steps {st:5d}", end="")
        print(f"  {kind:14s} params {rs[0]['params']:6d}  seen turns {np.mean([r['acc_seen_turns'] for r in rs]):.3f} "
              f"+/- {np.std([r['acc_seen_turns'] for r in rs]):.3f}   unseen turns {np.mean([r['acc_unseen_turns'] for r in rs]):.3f} "
              f"+/- {np.std([r['acc_unseen_turns'] for r in rs]):.3f}")


if __name__ == "__main__":
    main()
