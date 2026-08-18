#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_bubble.py -- the space-time bubble: a window of frames seals what one frame can't.

Where Test 8 left it: a single reading is the folded shadow (the below-view), and the
return path can't close it without context. Jonathan's next step: make the context REAL
and carry TIME -- "model things like a video instead of just images"; recall returns "a
round scene, the place, a small window of time." So the disambiguating context is not a
label -- it is a SHORT WINDOW OF THE VIDEO around the moment: the space-time bubble.

This is measurable and rigorous. A moving state s(t)=(p,v) runs on a Van der Pol limit
cycle. We observe only the POSITION  y = p  -- one flat frame, a photo. That single frame
is non-invertible in the state: it keeps position but DROPS the whole velocity dimension
(a photo of a pendulum can't tell you which way it's swinging, or how fast). Recovering
the full state from one frame is the collapsed bottle -- the same non-invertibility as
Test 8's fold, one dimension deeper: the return path is missing a coordinate.

Give the return path a WINDOW instead -- the delay vector [y_t, y_{t-L}, ..., y_{t-KL}],
a little clip of the recent past. Takens' embedding theorem says a window of a scalar
observation reconstructs the full state of a dynamical system -- the time window RESTORES
the dimension the single frame dropped. That theorem IS "the bubble seals the bottle,"
and here it's run on the real MuyGPyS GP.

  * instantaneous (one frame, y_t only) -> (p,v): velocity collapsed, high error.
  * windowed (the space-time bubble)     -> (p,v): recovers the limit cycle.
  * error falls as the window grows: more time in the bubble = more of the state sealed.

Honest bound: Takens is established theory; this is a clean demonstration on a real
nonlinear oscillator with the real GP. The identification "space-time bubble = delay
embedding = episodic clip" is the framework mapping.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from MuyGPyS.gp import MuyGPS
from MuyGPyS.gp.kernels import Matern
from MuyGPyS.gp.deformation import Isotropy, l2
from MuyGPyS.gp.hyperparameter import ScalarParam
from MuyGPyS.gp.noise import HomoscedasticNoise
from MuyGPyS.neighbors import NN_Wrapper

rng = np.random.default_rng(9)

# ---- the moving state: a Van der Pol limit cycle (a real 2-D dynamical system) ----
def vanderpol(T=240.0, dt=0.02, mu=1.5, p0=2.0, v0=0.0):
    n = int(T/dt); p = np.empty(n); v = np.empty(n); p[0], v[0] = p0, v0
    for t in range(n-1):                       # RK4
        def d(p_, v_): return v_, mu*(1-p_*p_)*v_ - p_
        k1 = d(p[t], v[t])
        k2 = d(p[t]+0.5*dt*k1[0], v[t]+0.5*dt*k1[1])
        k3 = d(p[t]+0.5*dt*k2[0], v[t]+0.5*dt*k2[1])
        k4 = d(p[t]+dt*k3[0], v[t]+dt*k3[1])
        p[t+1] = p[t] + dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0])
        v[t+1] = v[t] + dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1])
    return p, v

p, v = vanderpol()
burn = 2000                                    # drop the transient onto the cycle
p, v = p[burn:], v[burn:]
y = p.copy()                                    # ONE FLAT FRAME: observe only position p
y = y + rng.normal(0, 0.01, y.shape)            # a little sensor noise

# ---- GP helper (scalar target) ----
def gp(ls):
    return MuyGPS(kernel=Matern(smoothness=ScalarParam(1.5),
                  deformation=Isotropy(l2, length_scale=ScalarParam(ls))),
                  noise=HomoscedasticNoise(1e-3))
def predict(Xtr, Ytr, Xte, ls=1.5, nn=30):
    g = gp(ls); k = min(nn, len(Xtr)-1)
    nbrs = NN_Wrapper(Xtr, k, nn_method="exact", algorithm="ball_tree")
    ni, _ = nbrs.get_nns(Xte)
    cw, pw, nt = g.make_predict_tensors(np.arange(len(Xte)), ni, Xte, Xtr, Ytr)
    m = g.posterior_mean(g.kernel(pw), g.kernel(cw), nt)
    return np.asarray(m).ravel()

def delay_matrix(y, K, L):
    """The space-time bubble: [y_t, y_{t-L}, ..., y_{t-KL}] at each valid t."""
    span = K*L
    idx = np.arange(span, len(y))
    cols = [y[idx - j*L] for j in range(K+1)]
    return np.stack(cols, axis=1), idx

def standardize(A, mu=None, sd=None):
    if mu is None: mu = A.mean(0); sd = A.std(0) + 1e-9
    return (A - mu)/sd, mu, sd

def run(K, L=80):
    X, idx = delay_matrix(y, K, L)
    P, V = p[idx], v[idx]
    Xs, mu, sd = standardize(X)
    # contiguous-block split (honest for a time series): first 55% train, last 40% test,
    # with a gap so test windows don't overlap training windows.
    n = len(idx); tr = np.arange(0, int(0.55*n)); te = np.arange(int(0.60*n), n)
    php = predict(Xs[tr], P[tr][:,None], Xs[te])
    vhp = predict(Xs[tr], V[tr][:,None], Xs[te])
    rp = float(np.sqrt(np.mean((php-P[te])**2)))
    rv = float(np.sqrt(np.mean((vhp-V[te])**2)))
    return dict(K=K, rmse_p=rp, rmse_v=rv, P=P[te], V=V[te], Ph=php, Vh=vhp)

Ks = [0, 1, 2, 4, 8]
res = {K: run(K) for K in Ks}

print("="*72)
print("  THE SPACE-TIME BUBBLE: a window of frames seals what one frame can't")
print("  (Van der Pol state (p,v) observed only as position y = p, real GP)")
print("="*72)
print(f"  observation is one flat frame y=p -> keeps position, DROPS velocity v")
print(f"  (std of the state over the cycle:  p {p.std():.2f}   v {v.std():.2f})")
print()
print(f"  {'bubble = window of frames':30s} {'RMSE  p (in frame)':>20} {'RMSE  v (hidden)':>18}")
for K in Ks:
    tag = "1 frame (instantaneous)" if K == 0 else f"{K+1} frames (K={K}, lag L=80)"
    print(f"  {tag:30s} {res[K]['rmse_p']:>20.3f} {res[K]['rmse_v']:>18.3f}")
print()
b0, bB = res[0], res[8]
print(f"  -> ONE frame cannot recover the hidden velocity v (RMSE {b0['rmse_v']:.3f} ~ its full")
print(f"     spread {v.std():.2f}): a photo doesn't say which way you're moving. Widening the bubble")
print(f"     to a short clip drops hidden-v error to {bB['rmse_v']:.3f} ({100*(b0['rmse_v']-bB['rmse_v'])/b0['rmse_v']:.0f}% lower) -- the time window")
print(f"     RESTORES the dropped dimension (Takens delay-embedding).")
print(f"  -> 'model it like a video, not an image': the clip of recent frames is the context")
print(f"     that seals the bottle -- the space-time bubble made measurable.")

# ---------------------------------------------------------------------------
# PLOT: left = phase plane (p,v). true cycle vs 1-frame reconstruction (collapsed)
#       vs bubble reconstruction (recovers the cycle). right = RMSE vs window length.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.4))

axL.plot(res[8]['P'], res[8]['V'], color="#111", lw=1.2, alpha=0.35, label="true state (p,v) — the limit cycle")
axL.scatter(res[0]['Ph'], res[0]['Vh'], s=10, color="#e6820a", alpha=0.5,
            label="1 frame → (p,v): velocity collapsed to ~0")
axL.scatter(res[8]['Ph'], res[8]['Vh'], s=10, color="#238b45", alpha=0.7,
            label="9-frame bubble → (p,v): cycle recovered")
axL.set_xlabel("position  p"); axL.set_ylabel("velocity  v  (the hidden coordinate)")
axL.set_title("One frame drops the velocity dimension; the time-window bubble restores it\n(state observed only as position y = p)")
axL.legend(loc="upper right", fontsize=8, framealpha=0.93)

nf = [K+1 for K in Ks]
axR.plot(nf, [res[K]['rmse_v'] for K in Ks], color="#238b45", lw=2.2, marker="o", ms=5,
         label="hidden velocity v")
axR.plot(nf, [res[K]['rmse_p'] for K in Ks], color="#2b8cbe", lw=1.8, marker="s", ms=4,
         label="position p")
axR.set_xlabel("frames in the bubble  (window length)"); axR.set_ylabel("state reconstruction RMSE")
axR.set_title("More time in the bubble = more of the state sealed\n(Takens delay-embedding on the real GP)")
axR.legend(loc="upper right", fontsize=8.5, framealpha=0.93)
axR.set_ylim(bottom=0)

fig.tight_layout(); fig.savefig("memory_bubble.png", dpi=130)
print("\n  wrote memory_bubble.png")
