#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eye.py — THE SMALL EYE: a few-hundred-thousand-parameter net that looks at a frame and a press and
says what the next frame will be. It is the test of Jonathan's claim (Sep 3 2026): "cats and flies
see with almost no brain — recognition is not a size thing; we can do it with a small machine over
more time." Trained on the touches collect.py kept (D:\planet\eye\<game>.npz).

Three measures, on cells that actually changed (a model that predicts "nothing changes" scores 0):
  FLY      the eye has NEVER seen this game (trained on the other games) — fixed circuits
  CAT      the same eye after ~80 of this game's own touches (test-time training) — the small
           machine over more time
  SCRATCH  an eye trained ONLY on those 80 touches, nothing else — is the other games' seeing worth anything
Also the change-detection F1 (did it know WHICH cells would change), because that is what a planner
needs first.

Usage:  python eye.py                    (5 folds over the games, results -> D:\planet\eye\eye_results.json)
        python eye.py --epochs 30 --tune 300 --device cuda
        python eye.py --summary
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
OUT = r"D:\planet\eye" if os.name == "nt" else "/tmp/eye"
NC = 16            # colors
NA = 7             # 0 reset, 1-6


def layers(F, A):
    """THE LAYERS BEHIND THE SCREEN (Jonathan, Sep 3): every press adds a layer to each pixel that changed.
    H[i] = how many times each cell had changed before press i (reset to 0 at a RESET). Walls stay at 0."""
    H = np.zeros_like(F[:-1]); h = np.zeros(F.shape[1:], dtype=F.dtype)
    for i in range(len(A)):
        H[i] = h
        if A[i] == 0: h = np.zeros_like(h)
        else: h = h + (F[i + 1] != F[i])
    return H


def load_games(split=80):
    """{game: (F0, F1, A, X, Y, H, first_n)} without RESET transitions."""
    games = {}
    for p in sorted(glob.glob(os.path.join(OUT, "*.npz"))):
        if os.path.basename(p).startswith("play_"): continue
        z = np.load(p); F, A, X, Y = z["F"].astype(np.int64), z["A"], z["X"], z["Y"]
        keep = [i for i in range(len(A)) if A[i] != 0]
        if len(keep) < 20: continue
        H = layers(F, A)
        F0 = F[[i for i in keep]]; F1 = F[[i + 1 for i in keep]]
        games[os.path.basename(p)[:-4]] = (F0, F1, A[keep], X[keep], Y[keep], H[keep], min(split, int(0.67 * len(keep))))
    return games


def make_model():
    import torch, torch.nn as nn
    class Block(nn.Module):
        def __init__(s, c, d):
            super().__init__()
            s.c1 = nn.Conv2d(c, c, 3, padding=d, dilation=d); s.c2 = nn.Conv2d(c, c, 3, padding=1)
            s.n1 = nn.GroupNorm(8, c); s.n2 = nn.GroupNorm(8, c); s.act = nn.GELU()
        def forward(s, x):
            h = s.act(s.n1(s.c1(x))); h = s.n2(s.c2(h)); return s.act(x + h)
    class Eye(nn.Module):
        def __init__(s, c=48):
            super().__init__()
            s.inp = nn.Conv2d(NC + NA + 5, c, 3, padding=1)
            s.blocks = nn.Sequential(*[Block(c, d) for d in (1, 2, 4, 8, 16, 1)])
            s.out = nn.Conv2d(c, NC, 1)
            s.keep = nn.Parameter(torch.tensor(4.0))       # "nothing changes" is the default the net deviates from
        def forward(s, x):
            return s.out(s.blocks(s.inp(x))) + s.keep * x[:, :NC]
    return Eye()


def encode(F0, A, X, Y, device, H=None):
    """frame one-hot (16) + action one-hot broadcast (7) + click map + row/col coordinates
    + the layers behind the screen (depth = changes so far, capped at 8; wall = never changed) -> (B, 28, 64, 64)"""
    import torch
    B = len(F0)
    f = torch.as_tensor(F0, device=device).clamp(0, NC - 1)
    oh = torch.nn.functional.one_hot(f, NC).permute(0, 3, 1, 2).float()
    a = torch.zeros(B, NA, 64, 64, device=device)
    a[torch.arange(B), torch.as_tensor(A, device=device).clamp(0, NA - 1)] = 1.0
    click = torch.zeros(B, 1, 64, 64, device=device)
    for i in range(B):
        if X[i] >= 0: click[i, 0, int(Y[i]), int(X[i])] = 1.0
    rr = torch.linspace(-1, 1, 64, device=device).view(1, 1, 64, 1).expand(B, 1, 64, 64)
    cc = torch.linspace(-1, 1, 64, device=device).view(1, 1, 1, 64).expand(B, 1, 64, 64)
    if H is None: H = np.zeros((B, 64, 64), dtype=np.int64)
    h = torch.as_tensor(np.asarray(H), device=device).float()
    depth = (h.clamp(0, 8) / 8.0).unsqueeze(1); wall = (h == 0).float().unsqueeze(1)
    return torch.cat([oh, a, click, rr, cc, depth, wall], 1)


def batches(F0, F1, A, X, Y, H, bs, device, shuffle=True):
    import torch
    idx = np.random.permutation(len(F0)) if shuffle else np.arange(len(F0))
    for s in range(0, len(idx), bs):
        j = idx[s:s + bs]
        yield encode(F0[j], A[j], X[j], Y[j], device, H[j]), torch.as_tensor(F1[j], device=device).clamp(0, NC - 1), \
              torch.as_tensor(F0[j], device=device).clamp(0, NC - 1)


def train(model, data, steps, device, lr=2e-3, bs=32, log=None, wchange=20.0):
    import torch
    F0, F1, A, X, Y, H = data
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=max(steps, 2))
    model.train(); n = 0; t0 = time.time()
    while n < steps:
        for x, y1, y0 in batches(F0, F1, A, X, Y, H, bs, device):
            logits = model(x)
            w = 1.0 + wchange * (y1 != y0).float()                     # changed cells count 21x
            loss = (torch.nn.functional.cross_entropy(logits, y1, reduction="none") * w).sum() / w.sum()
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); n += 1
            if log and n % 200 == 0: log(f"    step {n}/{steps} loss {loss.item():.4f} ({time.time() - t0:.0f}s)")
            if n >= steps: break
    return model


def evaluate(model, data, device, bs=64):
    """changed-cell accuracy, change-detection precision/recall/F1, whole-frame accuracy"""
    import torch
    F0, F1, A, X, Y, H = data
    model.eval(); hit = tot = tp = fp = fn = allhit = alltot = 0
    with torch.no_grad():
        for x, y1, y0 in batches(F0, F1, A, X, Y, H, bs, device, shuffle=False):
            pred = model(x).argmax(1)
            ch = (y1 != y0); pch = (pred != y0)
            hit += int((pred[ch] == y1[ch]).sum()); tot += int(ch.sum())
            tp += int((pch & ch).sum()); fp += int((pch & ~ch).sum()); fn += int((~pch & ch).sum())
            allhit += int((pred == y1).sum()); alltot += y1.numel()
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    return {"changed_acc": round(hit / tot, 3) if tot else None, "changed_cells": tot,
            "det_precision": round(prec, 3), "det_recall": round(rec, 3),
            "det_f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
            "frame_acc": round(allhit / alltot, 4)}


def cat(d, idx):
    return tuple(a[idx] for a in d[:6])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5); ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--tune", type=int, default=300, help="test-time training steps on the held-out game's first touches")
    ap.add_argument("--device", default=None); ap.add_argument("--summary", action="store_true")
    ap.add_argument("--games", default=None)
    a = ap.parse_args()
    resp = os.path.join(OUT, "eye_results.json")
    if a.summary:
        summary(json.load(open(resp))); return
    import torch
    device = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    games = load_games()
    names = sorted(games)
    if a.games: names = [n for n in names if n in a.games.split(",")]
    print(f"eye: {len(games)} games, {sum(len(g[0]) for g in games.values())} touches, device {device}")
    model = make_model(); npar = sum(p.numel() for p in model.parameters()); print(f"parameters: {npar}")
    results = {"parameters": npar, "device": device, "games": {}, "started": time.strftime("%Y-%m-%d %H:%M")}
    folds = [names[i::a.folds] for i in range(a.folds)]
    for fi, held in enumerate(folds):
        train_names = [n for n in names if n not in held]
        tr = tuple(np.concatenate([games[n][k] for n in train_names]) for k in range(6))
        steps = a.epochs * max(1, len(tr[0]) // 32)
        print(f"\nfold {fi + 1}/{a.folds}: train on {len(train_names)} games ({len(tr[0])} touches, {steps} steps), hold out {held}")
        torch.manual_seed(fi); np.random.seed(fi)
        base = make_model().to(device)
        train(base, tr, steps, device, log=print)
        torch.save(base.state_dict(), os.path.join(OUT, f"eye_fold{fi}.pt"))
        for n in held:
            g = games[n]; first = g[6]
            early = cat(g, np.arange(first)); late = cat(g, np.arange(first, len(g[0])))
            fly = evaluate(base, late, device)
            tuned = make_model().to(device); tuned.load_state_dict(base.state_dict())
            train(tuned, early, a.tune, device, lr=1e-3)
            catr = evaluate(tuned, late, device)
            torch.manual_seed(100 + fi)
            scratch = make_model().to(device); train(scratch, early, a.tune, device, lr=2e-3)
            scr = evaluate(scratch, late, device)
            results["games"][n] = {"touches": int(len(g[0])), "first": int(first), "fly": fly, "cat": catr, "scratch": scr}
            print(f"  {n:6s} late touches {len(late[0]):3d} changed cells {fly['changed_cells']:6d} | "
                  f"FLY acc {fly['changed_acc']} f1 {fly['det_f1']} | CAT acc {catr['changed_acc']} f1 {catr['det_f1']} | "
                  f"SCRATCH acc {scr['changed_acc']} f1 {scr['det_f1']}")
            json.dump(results, open(resp, "w"), indent=1)
    results["finished"] = time.strftime("%Y-%m-%d %H:%M")
    json.dump(results, open(resp, "w"), indent=1)
    summary(results)


def summary(res):
    gs = res["games"]
    print(f"\nthe small eye: {res.get('parameters')} parameters on {res.get('device')}; {len(gs)} games")
    print(f"  {'game':6s} {'FLY acc':>8s} {'f1':>6s} {'CAT acc':>8s} {'f1':>6s} {'SCRATCH':>8s} {'f1':>6s}")
    def m(k, f):
        v = [g[k][f] for g in gs.values() if g[k][f] is not None]; return sum(v) / len(v) if v else 0
    for n, g in sorted(gs.items()):
        print(f"  {n:6s} {str(g['fly']['changed_acc']):>8s} {g['fly']['det_f1']:6.2f} {str(g['cat']['changed_acc']):>8s} {g['cat']['det_f1']:6.2f} "
              f"{str(g['scratch']['changed_acc']):>8s} {g['scratch']['det_f1']:6.2f}")
    print(f"  {'MEAN':6s} {m('fly', 'changed_acc'):8.3f} {m('fly', 'det_f1'):6.2f} {m('cat', 'changed_acc'):8.3f} {m('cat', 'det_f1'):6.2f} "
          f"{m('scratch', 'changed_acc'):8.3f} {m('scratch', 'det_f1'):6.2f}")


if __name__ == "__main__":
    main()
