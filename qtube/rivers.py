"""rivers.py - where a trained nested model builds (Nov 1 2026). See NESTED_QUATERNION_MODEL.md, "Rivers, bridges and the web".

For each right answer of a trained model saved by qtest.py --save-dir:
  - how close the key's node sits to a river: the smallest singular value of b -> a*b over |a| (0 = on a river,
    i.e. a is an exact zero divisor; the bridge ratio can never go below it)
  - which of her 7 directions the river points at: a = (x, y) in octonion halves, s = Im(conj(x) y) / |..|
    (every river of the group that leaves out unit S points at +/- e_S; tilted rivers point in between;
    a zero divisor and all its partners point the same way, so a bridge never changes direction)
  - whether the turned target sits on a bridge from it: |cos(s(key node), s(target node))| (1 = same direction)
  - which turn was used (a mirror turn Q q* Q^-1 or an ordinary one)
On the unseen turns the same is split into hits and misses.

    python rivers.py --dir models_r3 --device cuda --out rivers_r3.json
"""
from __future__ import annotations
import argparse, glob, json, os, re
import numpy as np
import torch, torch.nn.functional as F

import qtest as Q


def direction(a, C8):
    """a: (..., 16) -> unit 7-vector s = Im(conj(x) y) (which of her 7 directions this node's river points at)"""
    x, y = a[..., :8], a[..., 8:]
    xc = torch.cat([x[..., :1], -x[..., 1:]], -1)
    return F.normalize(Q.prod(xc, y, C8)[..., 1:], dim=-1)


def off_river(a, C16):
    """smallest singular value of b -> a*b, over |a| (0 = a is an exact zero divisor)"""
    L = torch.einsum("...i,ijk->...jk", a, C16)
    return torch.linalg.svdvals(L)[..., -1] / a.norm(dim=-1).clamp_min(1e-9)


def analyze(path, device, n=2000, bs=250):
    name = os.path.basename(path)[:-3]
    kind, seed, steps, split, mirror = re.match(r"(.+)_s(\d+)_st(\d+)_(quarter|rotmirror)_m(\d+)$", name).groups()
    seed, steps, mirror = int(seed), int(steps), int(mirror)
    m = Q.Model(kind, seed=seed, mirror_turns=mirror).to(device)
    m.load_state_dict(torch.load(path, map_location=device)); m.eval()
    seen, unseen = ([0, 1, 2, 3], [4, 5, 6, 7]) if split == "rotmirror" else ([0, 1, 2, 4], [3, 5, 6, 7])
    P = Q.pool(10_000 + seed, 4000)
    C8 = Q.table(8).to(device)
    nested = kind.startswith("nested")
    row = {"model": name, "kind": kind, "seed": seed, "steps": steps, "split": split, "mirror_turns": mirror}
    for label, turns in [("seen", seen), ("unseen", unseen)]:
        rng = np.random.default_rng(20_000 + seed)
        H, MU, RR, OFF, COS, GRP, ALN, RP = [], [], [], [], [], [], [], []
        for _ in range(n // bs):
            K, Cn, Y = Q.batch(rng, bs, turns, P=P, near_n=7, fmin=1, fmax=1, nkind="move")
            K, Cn, Y = K.to(device), Cn.to(device), Y.to(device)
            with torch.no_grad():
                zk = m.enc(K)                                       # (B, nodes, 4, 4)
                zc = m.turn(m.enc(Cn))                              # (B, cand, turns, nodes, 4, 4)
                b = zc.flatten(-2)
                aK = zk.flatten(-2)                                 # (B, nodes, 16)
                a = aK[:, None, None].expand_as(b)
                if nested:
                    ratio = Q.prod(a, b, m.C16).norm(dim=-1) / (a.norm(dim=-1) * b.norm(dim=-1) + 1e-6)
                    sc = (-ratio if kind != "nested_loss" else ratio).mean(-1)
                else:
                    sc = F.cosine_similarity(a, b, dim=-1).mean(-1)
                best, bt = sc.max(-1)                               # (B, cand)
                pred = best.argmax(-1); bi = torch.arange(len(Y), device=device)
                tY = bt[bi, Y]
                H.append((pred == Y).cpu()); MU.append(m.mirror[tY].cpu())
                if nested:
                    RR.append(ratio[bi, Y, tY].mean(-1).cpu())
                    RP.append(ratio[bi, pred, bt[bi, pred]].mean(-1).cpu())
                    OFF.append(off_river(aK, m.C16).cpu())          # (B, nodes)
                    if kind != "nested_random":
                        sa, sb = direction(aK, C8), direction(b[bi, Y, tY], C8)
                        COS.append((sa * sb).sum(-1).abs().cpu())
                        GRP.append(sa.abs().argmax(-1).cpu() + 1)   # unit 1..7
                        ALN.append(sa.abs().max(-1).values.cpu())
        H = torch.cat(H); MU = torch.cat(MU)
        d = {"acc": round(H.float().mean().item(), 4),
             "mirror_turn_used": round(MU.float().mean().item(), 4) if mirror else None}
        if nested:
            RR, RP, OFF = torch.cat(RR), torch.cat(RP), torch.cat(OFF)
            d.update(ratio_right=round(RR.mean().item(), 4),
                     ratio_right_hits=round(RR[H].mean().item(), 4) if H.any() else None,
                     ratio_right_misses=round(RR[~H].mean().item(), 4) if (~H).any() else None,
                     ratio_wrong_pick_misses=round(RP[~H].mean().item(), 4) if (~H).any() else None,
                     key_off_river=round(OFF.mean().item(), 4),
                     key_nodes_on_river=round((OFF < 0.05).float().mean().item(), 4))
            if COS:
                COS, GRP, ALN = torch.cat(COS), torch.cat(GRP), torch.cat(ALN)
                d.update(bridge_cos=round(COS.mean().item(), 4),
                         bridge_cos_hits=round(COS[H].mean().item(), 4) if H.any() else None,
                         bridge_cos_misses=round(COS[~H].mean().item(), 4) if (~H).any() else None,
                         axis_alignment=round(ALN.mean().item(), 4))
                hist = np.stack([np.bincount(GRP[:, k].numpy(), minlength=8)[1:] for k in range(GRP.shape[1])])  # nodes x 7
                share = hist / hist.sum(1, keepdims=True)
                d["groups_per_node"] = [{"top_unit": int(share[k].argmax()) + 1, "top_share": round(float(share[k].max()), 3),
                                         "units_over_10pct": int((share[k] > 0.10).sum())} for k in range(len(share))]
                tot = hist.sum(0) / hist.sum()
                d["group_share_all_nodes"] = [round(float(x), 3) for x in tot]
        row[label] = d
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="models_r3")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default="rivers_r3.json")
    ap.add_argument("--n", type=int, default=2000)
    a = ap.parse_args()
    rows = []
    for p in sorted(glob.glob(os.path.join(a.dir, "*.pt"))):
        r = analyze(p, a.device, n=a.n); rows.append(r); print(json.dumps(r), flush=True)
        json.dump(rows, open(a.out, "w"), indent=1)
    print("\nsummary (mean over seeds):")
    groups = sorted({(r["split"], r["mirror_turns"], r["kind"], r["steps"]) for r in rows})
    for g in groups:
        rs = [r for r in rows if (r["split"], r["mirror_turns"], r["kind"], r["steps"]) == g]
        f = lambda part, key: np.mean([r[part][key] for r in rs if r[part].get(key) is not None]) if any(
            r[part].get(key) is not None for r in rs) else float("nan")
        line = f"  {g[0]:9s} m{g[1]} {g[2]:13s} {g[3]:5d}  seen {f('seen','acc'):.3f} unseen {f('unseen','acc'):.3f}"
        if g[1]: line += f"  mirror-turn used: seen {f('seen','mirror_turn_used'):.2f} unseen {f('unseen','mirror_turn_used'):.2f}"
        if g[2].startswith("nested"):
            line += (f"  key off-river {f('seen','key_off_river'):.3f}  right ratio seen {f('seen','ratio_right'):.3f}"
                     f" unseen hits {f('unseen','ratio_right_hits'):.3f} misses {f('unseen','ratio_right_misses'):.3f}")
            if g[2] != "nested_random":
                line += (f"  bridge cos seen {f('seen','bridge_cos'):.3f} unseen hits {f('unseen','bridge_cos_hits'):.3f}"
                         f" misses {f('unseen','bridge_cos_misses'):.3f}  axis {f('seen','axis_alignment'):.2f}")
        print(line)


if __name__ == "__main__":
    main()
