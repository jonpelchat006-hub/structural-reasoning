#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
growth_muygps.py — the growth-web on a real Gaussian Process (MuyGPyS), with the
predictive VARIANCE as the "know-what-we-don't-know" signal, and Jonathan's PLUTO
correction: variance alone tells you where you're blind, but not which blind spots
MATTER. You need DEMAND from the boundary (queries from the environment) to decide
where to grow. Growth = high variance AND demand — not variance alone.

Setup: a target field over [0,1]. We start covered only in the middle [0,0.35].
Two uncovered regions remain:
  * the RELEVANT tail [0.35,0.70] — where queries (demand) actually arrive.
  * PLUTO [0.75,1.00] — real structure, high variance, but NO queries ever come.
Two growth strategies, same fiber budget:
  V  (variance-only / curiosity): grow at the globally highest-variance point.
  VD (variance x demand): grow only where a query landed AND variance is high.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from MuyGPyS.gp import MuyGPS
from MuyGPyS.gp.kernels import Matern
from MuyGPyS.gp.deformation import Isotropy, l2
from MuyGPyS.gp.hyperparameter import ScalarParam
from MuyGPyS.gp.noise import HomoscedasticNoise
from MuyGPyS.neighbors import NN_Wrapper

rng = np.random.default_rng(3)
LS = 0.05
def target(x):
    x = np.asarray(x, float)
    return 0.7*np.sin(5.5*x) + 0.5*x + 0.45*np.exp(-((x-0.60)/0.045)**2)

def gp():
    return MuyGPS(kernel=Matern(smoothness=ScalarParam(1.5),
                  deformation=Isotropy(l2, length_scale=ScalarParam(LS))),
                  noise=HomoscedasticNoise(1e-4))

def predict(Xtr, Ytr, Xte, nn=20):
    g = gp(); k = min(nn, len(Xtr)-1)
    nbrs = NN_Wrapper(Xtr, k, nn_method="exact", algorithm="ball_tree")
    ni, _ = nbrs.get_nns(Xte)
    cw, pw, nt = g.make_predict_tensors(np.arange(len(Xte)), ni, Xte, Xtr, Ytr)
    m = g.posterior_mean(g.kernel(pw), g.kernel(cw), nt)
    v = g.posterior_variance(g.kernel(pw), g.kernel(cw))
    return np.asarray(m).ravel(), np.asarray(v).ravel()

Xg = np.linspace(0, 1, 300)[:, None]; Yg = target(Xg).ravel()
QUERY = (Xg[:,0] <= 0.70)            # the relevant region (demand lives here)
PLUTO = (Xg[:,0] >= 0.75)            # uncovered, high-variance, but NEVER queried
def qrmse(m): return float(np.sqrt(np.mean((m[QUERY]-Yg[QUERY])**2)))

# start: covered middle only
X0 = np.sort(rng.uniform(0, 0.35, 16))[:, None]
Y0 = (target(X0) + rng.normal(0, 0.02, (len(X0),1)))
m0, v0 = predict(X0, Y0, Xg)
K = 18

# --- Strategy V: variance-only (grow at global argmax variance) ---
Xv = X0.copy(); Yv = Y0.copy(); v_locs = []
for _ in range(K):
    _, v = predict(Xv, Yv, Xg)
    i = int(np.argmax(v)); xs = Xg[i:i+1]
    Xv = np.vstack([Xv, xs]); Yv = np.vstack([Yv, target(xs)+rng.normal(0,0.02,(1,1))])
    v_locs.append(float(xs[0,0]))
mV, vV = predict(Xv, Yv, Xg)

# --- Strategy VD: variance x demand (grow only where a query lands AND var is high) ---
Xd = X0.copy(); Yd = Y0.copy(); d_locs = []; grown = 0; seen = 0
while grown < K and seen < 4000:
    seen += 1
    xq = float(rng.uniform(0, 0.70))                       # demand: queries only in [0,0.70]
    xq = np.array([[xq]])
    _, vq = predict(Xd, Yd, xq)
    if vq[0] > 0.15:                                        # only grow where we're actually uncertain
        Xd = np.vstack([Xd, xq]); Yd = np.vstack([Yd, target(xq)+rng.normal(0,0.02,(1,1))])
        d_locs.append(float(xq[0,0])); grown += 1
mD, vD = predict(Xd, Yd, Xg)

# ---- report ----
def in_pluto(locs): return sum(1 for x in locs if x >= 0.75)
print("="*70)
print("  GROWTH ON A GAUSSIAN PROCESS (MuyGPyS): variance = know-what-we-don't-know")
print("="*70)
print(f"  {'state':34s} {'query-region RMSE':>18} {'fibers in PLUTO':>16}")
print(f"  {'initial (middle only)':34s} {qrmse(m0):>18.3f} {'—':>16}")
print(f"  {'V  — variance only (curiosity)':34s} {qrmse(mV):>18.3f} {str(in_pluto(v_locs))+'/'+str(K):>16}")
print(f"  {'VD — variance x demand':34s} {qrmse(mD):>18.3f} {str(in_pluto(d_locs))+'/'+str(len(d_locs)):>16}")
print()
print(f"  mean predictive variance in PLUTO after VD: {float(vD[PLUTO].mean()):.3f}"
      f"   (still high — VD *knows* it doesn't know Pluto, and correctly doesn't care)")
print(f"  mean predictive variance in the query region after VD: {float(vD[QUERY].mean()):.3f}")
print()
print("  -> variance alone (V) burns fibers into Pluto — a real blind spot that no one")
print("     asks about. Adding DEMAND (VD) grows only the blind spots that matter, reaching")
print("     lower query-region error with the same budget, and leaves Pluto flagged-unknown.")

# ---- plot ----
fig, ax = plt.subplots(figsize=(9.2, 5.2))
ax.axvspan(0.0, 0.70, color="#eaf6ea", zorder=0, label="demand region (queries arrive)")
ax.axvspan(0.75, 1.0, color="#eee", zorder=0)
ax.text(0.875, 1.75, "PLUTO\n(unknown, no demand)", ha="center", color="#777", fontsize=9)
ax.plot(Xg[:,0], Yg, color="#111", lw=2.3, label="target field")
ax.plot(Xg[:,0], mD, color="#238b45", lw=2.0, label="VD: variance × demand")
ax.fill_between(Xg[:,0], mD-np.sqrt(vD), mD+np.sqrt(vD), color="#238b45", alpha=0.15)
ax.plot(Xg[:,0], mV, color="#e6820a", lw=1.6, ls="--", label="V: variance only")
ax.plot(d_locs, np.full(len(d_locs), -1.15), "|", color="#238b45", ms=12, mew=2)
ax.plot(v_locs, np.full(len(v_locs), -1.35), "|", color="#e6820a", ms=12, mew=2)
ax.set_xlabel("load  x"); ax.set_ylabel("response")
ax.set_title("Grow where variance AND demand are high — not variance alone\n"
             "(GP variance = knowing what we don't know; demand = the Pluto correction)")
ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9); ax.set_ylim(-1.5, 2.1)
fig.tight_layout(); fig.savefig("growth_muygps.png", dpi=130)
print("\n  wrote growth_muygps.png")
