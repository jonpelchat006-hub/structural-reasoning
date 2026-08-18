#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
growth_web.py — growth into the empty tail = capability expansion (the bicep getting bigger).

The web = a sum of tuning-curve fibers (Gaussian / cos^2 bumps). Each fiber peaks at its
perfect-match load and falls off (the alignment/friction penalty). Fitting = choosing fiber
weights; GROWTH = when a load fails (error over the tear threshold), allocate a NEW fiber at
that load and refit (recovery). This is a resource-allocating RBF net (Platt 1991) — and its
uncertainty-grows-away-from-data is exactly a Gaussian Process's predictive variance.

The point Jonathan made: the interesting signal is out in the TAIL (a sharp feature at x=0.86,
the "top-right corner"). We start covering only the middle. Growth is what carries coverage
OUT into the tail — and the honest control is a no-growth baseline with the SAME samples but
fibers fixed in the middle: it CANNOT reach the tail no matter how much data, because fixed
fibers = fixed vocabulary (the ceiling). Growth is the only thing that expands the frontier.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(1)
SIGMA = 0.05          # fiber tuning width
TOL   = 0.15          # |error| above this = a failure (tear) -> grow

def target(x):
    x = np.asarray(x, float)
    return 0.8*x + 0.45*np.sin(6.5*x) + 0.55*np.exp(-((x-0.86)/0.035)**2)  # sharp feature in the tail

def design(X, mus):
    X = np.atleast_1d(np.asarray(X, float))
    return np.exp(-0.5*((X[:, None] - np.asarray(mus)[None, :]) / SIGMA)**2)

def fit(mus, Xtr, Ytr, lam=1e-3):
    Phi = design(Xtr, mus)
    A = Phi.T @ Phi + lam*np.eye(len(mus))
    return np.linalg.solve(A, Phi.T @ np.asarray(Ytr))

def predict(mus, w, X):
    return design(X, mus) @ w

Xg = np.linspace(0, 1, 500); Yg = target(Xg)

def frontier(mus, w, tol=TOL):
    ok = np.abs(predict(mus, w, Xg) - Yg) < tol
    front = 0.0
    for i in range(len(Xg)):
        if np.mean(ok[max(0, i-15):i+1]) > 0.8:
            front = Xg[i]
    return front

def rmse(mus, w, lo=0.0, hi=1.0):
    m = (Xg >= lo) & (Xg <= hi)
    return float(np.sqrt(np.mean((predict(mus, w, Xg[m]) - Yg[m])**2)))

# --- initial web: fibers + samples ONLY in the middle [0, 0.4] ---
mus0 = np.linspace(0.03, 0.40, 9)
Xt = list(rng.uniform(0, 0.40, 60)); Yt = list(target(np.array(Xt)) + rng.normal(0, 0.02, 60))
w0 = fit(mus0, np.array(Xt), np.array(Yt))

# --- GROWTH: venture rightward; on failure, grow a fiber there and refit (recovery) ---
mus = list(mus0); Xtr = list(Xt); Ytr = list(Yt); w = w0.copy()
edge = 0.40; grown = 0
for _ in range(70):
    edge = min(1.0, edge + 0.011)          # the exploration frontier creeps right
    x = float(rng.uniform(0, edge))        # sample within where we've ventured
    y = float(target(x) + rng.normal(0, 0.02))
    err = abs(predict(np.array(mus), w, np.array([x]))[0] - y)
    Xtr.append(x); Ytr.append(y)
    if err > TOL:                          # failure -> grow a fiber at the load that broke us
        mus.append(x); grown += 1
    w = fit(np.array(mus), np.array(Xtr), np.array(Ytr))   # recovery = refit
mus = np.array(mus); wG = w

# --- no-growth control: SAME ventured samples, fibers FIXED in the middle ---
wB = fit(mus0, np.array(Xtr), np.array(Ytr))

print("="*70)
print("  GROWTH INTO THE TAIL = capability expansion")
print("="*70)
print(f"  {'state':28s}  {'#fibers':>8}  {'coverage frontier':>18}  {'tail RMSE [0.6,1]':>18}")
print(f"  {'initial (middle only)':28s}  {len(mus0):>8}  {frontier(mus0,w0):>18.2f}  {rmse(mus0,w0,0.6,1.0):>18.3f}")
print(f"  {'no-growth (same data)':28s}  {len(mus0):>8}  {frontier(mus0,wB):>18.2f}  {rmse(mus0,wB,0.6,1.0):>18.3f}")
print(f"  {'GROWN (fibers into tail)':28s}  {len(mus):>8}  {frontier(mus,wG):>18.2f}  {rmse(mus,wG,0.6,1.0):>18.3f}")
print()
print(f"  fibers grown into the tail: {grown}")
print("  -> same samples, but only GROWTH extends the frontier into the tail and captures")
print("     the sharp feature at 0.86. Fixed middle fibers can't reach it at any data volume")
print("     (fixed basis = fixed vocabulary = the ceiling). Growth IS the bicep getting bigger.")

# --- plot ---
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(Xg, Yg, color="#111", lw=2.4, label="target load-field")
ax.plot(Xg, predict(mus0, w0, Xg), color="#2b8cbe", lw=1.8, label="initial web (middle only)")
ax.plot(Xg, predict(mus0, wB, Xg), color="#d7301f", lw=1.6, ls="--", label="no-growth (same data, fixed fibers)")
ax.plot(Xg, predict(mus, wG, Xg), color="#238b45", lw=2.0, label="grown web (fibers into the tail)")
ax.plot(mus0, np.full_like(mus0, -0.15), "|", color="#2b8cbe", ms=12, mew=2)
ax.plot(mus[len(mus0):], np.full(len(mus)-len(mus0), -0.22), "|", color="#238b45", ms=12, mew=2)
ax.axvspan(0.6, 1.0, color="#f0f0f0", zorder=0)
ax.text(0.8, 1.55, "the tail\n(top-right corner)", ha="center", color="#555", fontsize=10)
ax.set_xlabel("load  x"); ax.set_ylabel("response")
ax.set_title("Growth into the empty tail = capability expansion\n(fibers = Gaussian tuning curves; grow on failure, refit on recovery)")
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
ax.set_ylim(-0.3, 1.9)
fig.tight_layout(); fig.savefig("growth_web.png", dpi=130)
print("\n  wrote growth_web.png")
