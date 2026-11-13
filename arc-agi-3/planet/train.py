#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train.py — CLASSICAL OFFLINE TRAINING in the sleep: the lives (lives/*.npz) and the demonstrations
(demos/*.json) are replayed in order and two small models are fitted on them, prequentially
(each example is scored BEFORE it is trained on, so the number reported is an honest forecast,
not a fit):

  hand   — behaviour cloning: P(action | what the eye saw, what the hand held last).
           Every action ever taken is a sample, but the samples are WEIGHTED: human
           demonstration steps ×4 (the expert), agent steps by the drive earned in the
           following second (a step that opened new ground or confirmed the body counts,
           a random probe that did nothing counts little).
  eye    — a change predictor: P(region changes | frame, action) per 8×8 region — the
           trainable expectation that turns pixels into SURPRISE only where they are
           surprising. Its miss rate is the honest surprise; the untrained monitor treats
           every change as surprising.

Both are sklearn MLPs (no torch needed); they fit in seconds on CPU and are saved to
<root>/models/{hand,eye}.pkl with their prequential scores in <root>/models/train.json.
player.py loads hand.pkl if present as one more TILT on the hand (an untrusted prior, like
the lower ocean's advice) — never as the controller.

Usage: python train.py --root D:\\planet\\ocean\\limbo [--epochs 2]
"""
from __future__ import annotations
import argparse, glob, json, os, pickle, sys, time
from typing import Dict, List, Tuple
import numpy as np
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ACTIONS = ["left", "right", "jump", "jumpleft", "jumpright", "grab", "grabright", "grableft", "up", "wait",
           "jumpgrab", "jumpgrableft", "jumpgrabright"]   # chords appended at the END: old indices stay stable
POOL = 8      # 96x160 → 12x20 pooled features


def features(frame: np.ndarray, last_action: str, mouse=(0, 0)) -> np.ndarray:
    """The eye's symbol frame (L + 8E) pooled to 12×20: mean level, mean edge, plus the held action."""
    H, W = frame.shape
    f = frame.astype(np.float32)
    lvl = (f % 8) / 7.0; edge = (f // 8) / 7.0
    h, w = H // POOL, W // POOL
    pl = lvl[:h * POOL, :w * POOL].reshape(h, POOL, w, POOL).mean(axis=(1, 3))
    pe = edge[:h * POOL, :w * POOL].reshape(h, POOL, w, POOL).mean(axis=(1, 3))
    a = np.zeros(len(ACTIONS), np.float32)
    if last_action in ACTIONS: a[ACTIONS.index(last_action)] = 1.0
    m = np.array([max(-1.0, min(1.0, mouse[0] / 40.0)), max(-1.0, min(1.0, mouse[1] / 40.0))], np.float32)
    return np.concatenate([pl.ravel(), pe.ravel(), m, a])


def region_change(prev: np.ndarray, cur: np.ndarray, tile: int = 8) -> np.ndarray:
    H, W = cur.shape
    d = (prev != cur).astype(np.float32)
    h, w = H // tile, W // tile
    return (d[:h * tile, :w * tile].reshape(h, tile, w, tile).mean(axis=(1, 3)) > 0.15).astype(np.int8).ravel()


def load_lives(root: str) -> List[Dict]:
    out = []
    for p in sorted(glob.glob(os.path.join(root, "lives", "*.npz"))):
        try:
            z = np.load(p, allow_pickle=False)
            F, A = z["F"], z["A"]
            E = z["E"] if "E" in z else np.array([""] * len(A))
            M = z["M"] if "M" in z and len(z["M"]) == len(A) else np.zeros((len(A), 2), np.int32)
            if len(F) < 5: continue
            out.append({"path": p, "F": F, "A": [str(a) for a in A], "E": [str(e) for e in E], "M": M})
        except Exception as e:
            print("skip", p, e)
    return out


def step_weights(life: Dict, human_mask: np.ndarray) -> np.ndarray:
    """Drive earned in the following ~6 steps: new ground / scroll / body confirmed, from the events."""
    E = life["E"]; n = len(E)
    gain = np.zeros(n, np.float32)
    for i, e in enumerate(E):
        g = 0.0
        if "body.confirmed" in e: g += 0.5
        if "window.newground" in e or "camera.scroll" in e: g += 0.3
        if "surprise.big" in e: g += 0.1
        gain[i] = g
    w = np.zeros(n, np.float32)
    for i in range(n):
        w[i] = 0.15 + gain[i: i + 6].sum()
    w[human_mask] = 4.0
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    a = ap.parse_args()
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    lives = load_lives(a.root)
    if not lives:
        print("no lives to train on in", os.path.join(a.root, "lives")); return
    # which steps were the human's? player.py tags them in the events as 'hand.human' (new) —
    # older lives have no tag: nothing is weighted as expert there.
    X_hand, y_hand, w_hand, X_eye, y_eye = [], [], [], [], []
    for life in lives:
        F, A, E, M = life["F"], life["A"], life["E"], life["M"]
        human = np.array(["hand.human" in e for e in E])
        w = step_weights(life, human)
        last = "wait"
        for i in range(len(A)):
            if A[i] not in ACTIONS: last = A[i]; continue
            x = features(F[i], last, tuple(M[i - 1]) if i > 0 else (0, 0))
            X_hand.append(x); y_hand.append(ACTIONS.index(A[i])); w_hand.append(w[i])
            if i + 1 < len(F):
                xa = x.copy(); xa[-len(ACTIONS):] = 0; xa[-len(ACTIONS) + ACTIONS.index(A[i])] = 1
                X_eye.append(xa); y_eye.append(region_change(F[i], F[i + 1]))
            last = A[i]
    X_hand = np.array(X_hand); y_hand = np.array(y_hand); w_hand = np.array(w_hand)
    X_eye = np.array(X_eye); y_eye = np.array(y_eye)
    print(f"{len(lives)} lives, {len(X_hand)} steps ({int((w_hand >= 4).sum())} human), features {X_hand.shape[1]}")
    # ---- hand: prequential in blocks of 200 (score then fit), sample weights via duplication
    hand = MLPClassifier(hidden_layer_sizes=(128,), max_iter=1, random_state=0)
    classes = np.arange(len(ACTIONS))
    seen, hit, base_hit = 0, 0, 0
    t0 = time.time()
    B = 100
    for ep in range(a.epochs):
        for s in range(0, len(X_hand), B):
            xb, yb, wb = X_hand[s:s + B], y_hand[s:s + B], w_hand[s:s + B]
            if ep == 0 and seen > 0:
                pred = hand.predict(xb); hit += int((pred == yb).sum()); seen += len(yb)
                base_hit += int((yb == np.bincount(y_hand[:s]).argmax()).sum())
            elif ep == 0:
                seen += len(yb); base_hit += int((yb == yb[0]).sum())
            rep = np.clip(np.round(wb / 0.5), 1, 4).astype(int)         # weight by duplication
            xr = np.repeat(xb, rep, axis=0); yr = np.repeat(yb, rep)
            for _ in range(3): hand.partial_fit(xr, yr, classes=classes)
    hand_score = {"prequential_acc": round(hit / max(1, seen), 3), "majority_acc": round(base_hit / max(1, seen), 3),
                  "steps": int(len(X_hand)), "seconds": round(time.time() - t0, 1)}
    print("hand:", hand_score)
    # ---- eye: one MLP with multi-label output (region changes), prequential
    t0 = time.time()
    eye = MLPRegressor(hidden_layer_sizes=(128,), max_iter=1, random_state=0)   # multi-output 0/1, thresholded
    seen, miss, base_miss = 0, 0, 0
    for ep in range(a.epochs):
        for s in range(0, len(X_eye), B):
            xb, yb = X_eye[s:s + B], y_eye[s:s + B]
            if ep == 0 and s > 0:
                pred = (eye.predict(xb) > 0.5).astype(np.int8); miss += int((pred != yb).sum()); seen += yb.size
                base_miss += int(yb.sum())                                # "nothing changes" baseline
            for _ in range(2): eye.partial_fit(xb, yb.astype(np.float32))
    eye_score = {"prequential_region_error": round(miss / max(1, seen), 4),
                 "nothing_changes_error": round(base_miss / max(1, seen), 4), "regions": int(y_eye.shape[1]),
                 "seconds": round(time.time() - t0, 1)}
    print("eye:", eye_score)
    md = os.path.join(a.root, "models"); os.makedirs(md, exist_ok=True)
    with open(os.path.join(md, "hand.pkl"), "wb") as f: pickle.dump({"model": hand, "actions": ACTIONS, "pool": POOL}, f)
    with open(os.path.join(md, "eye.pkl"), "wb") as f: pickle.dump({"model": eye, "actions": ACTIONS, "pool": POOL}, f)
    hist = []
    try:
        with open(os.path.join(md, "train.json"), "r", encoding="utf-8") as f: hist = json.load(f)
    except Exception: pass
    hist.append({"t": time.time(), "lives": len(lives), "hand": hand_score, "eye": eye_score})
    with open(os.path.join(md, "train.json"), "w", encoding="utf-8") as f: json.dump(hist, f, indent=1)
    print("saved", md)


if __name__ == "__main__":
    main()
