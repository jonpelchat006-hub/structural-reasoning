#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
superfuel_context.py -- the superfuel is BURNING CONTEXT: muscle growth, orthogonally.

Jonathan reaching back to the earliest theory (Shovelcat 0-10): θ/φ/ψ acted like
budgets that emerge at different conditions; an "overflowing tanks" model with a
SUPERFUEL that comes out only when the tanks are FULL and the fuel must be COMPRESSED
-- and that superfuel is what you burn. His mapping now: the three budgets are the
VOID RESERVE, MATTER, and CONTEXT (the orthogonal plane). The superfuel = BURNING
CONTEXT = the fibers on the orthogonal (context) plane doing exactly what the muscles
do on the matter plane in Test 5 -- but invisibly, on the context layer: remove the
old, currently-failing context and grow a new one.

Grounding (all in-project):
  * three axes = Imagination(ψ,+1,possibility) / Memory(vesica,0,overlap) / Facts(φ,-1,
    constraint) -- SHOVELCAT_THEORY.md: exactly void/matter/context in the old language.
  * superfuel = Fire: Shovelcat_29 §9 -- Fire ignites from FUEL (accumulated unresolved
    problems = the full tanks) + HEAT, and "Fire cools into new Ground." Compression-
    when-full -> a higher-order fuel that burns into new structure.
  * consciousness = collapse/decision: SHOVELCAT_THEORY.md -- weights accumulate across
    the three axes until one crosses a COLLAPSE THRESHOLD ("that option becomes the
    decision"), "observation forces collapse" (the photon deciding wave/particle).
  * the growth mechanism is Test 5 (allocate-a-fiber-on-failure) applied to the CONTEXT
    coordinate; Test 8 established context = the coordinate that seals the return path.

THE SETUP -- a drifting environment
-----------------------------------
Each sample: a matter input x, a hidden REGIME r∈{0,1} setting the answer y=g_r(x)
(g0(x)=x, g1(x)=1-x -- two branches). The regime is readable from ONE component of a
context vector c∈R^K -- but WHICH component carries it DRIFTS over epochs (the old
context goes stale; a new one takes over). The matter-plane machinery (g0,g1) never
changes; only the right CONTEXT coordinate moves.

  FIXED    -- keep the original context coordinate. Works until the drift, then the
              stale context reads the regime no better than a coin -> error locks high.
  BURN     -- watch the residual; when the current context is FAILING, BURN it and GROW
              a new context coordinate (search for the component that now cuts the
              residual -- Test-5 growth, on the context axis). Recover after each drift.

The BURN is the superfuel: compress/discard the failing context, mint a new one. It is
the same muscle expansion as Test 5, run on the orthogonal (context) plane -- so it is
invisible on the matter plane, which is untouched.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(4)
K   = 5        # context components
D   = 22       # epochs between drifts (the signaling component rotates)
T   = 150      # epochs
N   = 60       # samples per epoch
THRESH = 0.10  # residual above this = the context is failing
MARGIN = 0.05  # a candidate must beat the current context by this to be worth burning for

def g(r, x):                       # the two regime branches (matter plane, FIXED)
    return np.where(r == 0, x, 1.0 - x)

def epoch_data(ep):
    s = (ep // D) % K                              # which context component carries r now
    r = rng.integers(0, 2, N)
    x = rng.uniform(0, 1, N)
    c = rng.uniform(0, 1, (N, K))                  # all components are noise...
    c[:, s] = np.where(r == 0, 0.15, 0.85) + rng.normal(0, 0.05, N)  # ...except the signaler
    y = g(r, x) + rng.normal(0, 0.02, N)
    return x, c, y, s

def predict_err(x, c, y, comp):
    """Use context component `comp` to read the regime, then predict with g_{r̂}."""
    rhat = (c[:, comp] > 0.5).astype(int)
    yhat = g(rhat, x)
    return float(np.mean(np.abs(yhat - y))), rhat

# ---- run both policies over the same drifting stream ----
def run(policy):
    comp = 0                                        # start on component 0
    errs = []; burns = []; used = []
    buf_x = np.empty((0,)); buf_c = np.empty((0, K)); buf_y = np.empty((0,))
    for ep in range(T):
        x, c, y, s = epoch_data(ep)
        # predict this epoch with the current context coordinate
        e, _ = predict_err(x, c, y, comp)
        errs.append(e); used.append(comp)
        # keep a short buffer of recent experience (the tank of context to search)
        buf_x = np.concatenate([buf_x, x])[-3*N:]
        buf_c = np.concatenate([buf_c, c])[-3*N:]
        buf_y = np.concatenate([buf_y, y])[-3*N:]
        if policy == "burn" and e > THRESH:         # context is FAILING -> consider burning
            cand = [(predict_err(buf_x, buf_c, buf_y, j)[0], j) for j in range(K)]
            best_e, best_j = min(cand)
            cur_e = predict_err(buf_x, buf_c, buf_y, comp)[0]
            if best_j != comp and best_e < cur_e - MARGIN:
                comp = best_j                       # BURN old context, GROW the new one
                burns.append(ep)
    return np.array(errs), burns

err_fixed, _        = run("fixed")
err_burn, burns     = run("burn")

drifts = [ep for ep in range(T) if ep % D == 0 and ep > 0]
print("="*72)
print("  THE SUPERFUEL = BURNING CONTEXT (Test 5 muscle growth, on the context plane)")
print("="*72)
print(f"  {K} context channels; the signaling one drifts every {D} epochs; matter plane fixed")
print(f"  drifts at epochs: {drifts}")
print()
print(f"  {'policy':22}{'mean error':>12}{'post-drift error':>18}{'burns':>8}")
# post-drift = mean error over the 6 epochs right after each drift
def post_drift_mean(e):
    idx = [ep for d in drifts for ep in range(d, min(d+6, T))]
    return float(np.mean(e[idx]))
print(f"  {'FIXED (stale context)':22}{err_fixed.mean():>12.3f}{post_drift_mean(err_fixed):>18.3f}{'—':>8}")
print(f"  {'BURN (grow new context)':22}{err_burn.mean():>12.3f}{post_drift_mean(err_burn):>18.3f}{len(burns):>8}")
print()
print(f"  -> FIXED keeps the original context coordinate. The matter machinery is fine, but")
print(f"     after each drift the stale context reads the regime no better than a coin, so")
print(f"     error locks near {err_fixed[-1]:.2f} (mean {err_fixed.mean():.3f}).")
print(f"  -> BURN detects the failing context, burns it, and grows a new coordinate that")
print(f"     re-separates the regimes -- recovering after every drift ({len(burns)} burns, mean error")
print(f"     {err_burn.mean():.3f}). Same muscle growth as Test 5, but on the orthogonal context plane:")
print(f"     invisible on the matter plane (g0,g1 never changed), the superfuel is the burn.")

# ---------------------------------------------------------------------------
# PLOT: error over epochs; drifts (grey), burns (green ticks). Fixed locks high;
# burn recovers after each drift.
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.6, 5.0))
for d in drifts:
    ax.axvline(d, color="#ccc", lw=1.0, zorder=0)
ax.axhline(THRESH, color="#c0392b", ls=":", lw=1.0)
ax.text(1, THRESH+0.005, "context-failing line", color="#c0392b", fontsize=8)
ax.plot(err_fixed, color="#e6820a", lw=2.0, label="FIXED context (stale → locks high)")
ax.plot(err_burn,  color="#238b45", lw=2.0, label="BURN context (grow a new coordinate)")
for b in burns:
    ax.plot([b],[err_burn[b]], marker="v", color="#238b45", ms=7, zorder=5)
ax.text(drifts[0]+0.5, 0.28, "grey = drift\n(the useful context moves)", color="#888", fontsize=8)
ax.set_xlabel("epoch"); ax.set_ylabel("prediction error")
ax.set_title("The superfuel is burning context: after each drift the stale context fails;\n"
             "burning it and growing a new coordinate recovers (Test-5 growth, orthogonal plane)")
ax.legend(loc="upper right", fontsize=9, framealpha=0.93); ax.set_ylim(-0.01, 0.33)
fig.tight_layout(); fig.savefig("superfuel_context.png", dpi=130)
print("\n  wrote superfuel_context.png")
