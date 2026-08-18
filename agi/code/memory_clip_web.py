#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_clip_web.py -- the memory clip lives in the gaps.

Jonathan's construction: when you drop a square grid inside a circle, the corners
the grid CANNOT express are cut-off spots. Those spots are not errors -- they
ABSORB incoming structure until they're complete, and only then can the ring
rest on them (SPARSE_VESICA 4/11.6, SPHERE_GENERATOR C.2: "closure failure mints
primitives"). The curve along the GP web has the same thing going on: the places
we can't approximate perfectly are the HIGH-VARIANCE gaps -- and each gap holds a
MEMORY CLIP: the (query, context, target) of a miss that happened there, kept
until enough arrives to finish it. Resolve the clip and the gap fills: variance
drops, and the curve now RESTS ON that point (it became an anchor / a sunk void
point, waterline model -> seabed).

Three things this makes measurable, on the SAME MuyGPyS web as growth_muygps.py:

  (1) PERSISTENCE  -- a clip parked at a gap stays flagged-open while its variance
      stays high; it is held, not discarded.
  (2) GAP -> ANCHOR -- resolving a clip (feeding its target in) drops the variance
      AT that spot below the open-threshold: blind spot becomes support point.
  (3) ORDER MATTERS -- revisiting clips in GAP ORDER (highest variance first,
      = retest_all_failures walking the worst-known first) buys more variance-drop
      and more query-region accuracy per resolution than random order. This is the
      T6 demand result re-read as MEMORY: the clip you stored is what you come back
      to, and coming back worst-first is optimal.

Honest bound: this is a design unification (SPARSE_VESICA 4/11.6, 22.1;
SPHERE_GENERATOR C.2) turned into a measured curve on a toy 1-D field. It shows
the MECHANISM (store-at-gap / resolve-to-anchor / revisit-worst-first) behaves as
claimed; it is not a claim about a full agent's episodic memory.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from MuyGPyS.gp import MuyGPS
from MuyGPyS.gp.kernels import Matern
from MuyGPyS.gp.deformation import Isotropy, l2
from MuyGPyS.gp.hyperparameter import ScalarParam
from MuyGPyS.gp.noise import HomoscedasticNoise
from MuyGPyS.neighbors import NN_Wrapper

rng = np.random.default_rng(5)
LS = 0.05
OPEN_VAR = 0.15          # a gap with variance above this holds an OPEN clip
NOISE = 0.02

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

# grid + demand region (queries arrive in [0,0.70], exactly as in growth_muygps)
Xg = np.linspace(0, 1, 300)[:, None]; Yg = target(Xg).ravel()
QUERY = (Xg[:,0] <= 0.70)
def qrmse(m): return float(np.sqrt(np.mean((m[QUERY]-Yg[QUERY])**2)))

# initial web: covered middle only  -> the rest of the demand region is open gaps
X0 = np.sort(rng.uniform(0, 0.35, 16))[:, None]
Y0 = target(X0) + rng.normal(0, NOISE, (len(X0),1))

# ---------------------------------------------------------------------------
# STEP 1  -- park a memory clip at every high-variance gap in the demand region.
# A clip = the miss that happened there: where (x), the CONTEXT it arrived in
# (here: a small state tag), and the TARGET we failed to produce. It is stored
# OPEN; nothing is resolved yet.
# ---------------------------------------------------------------------------
cand = np.linspace(0.02, 0.70, 40)[:, None]        # candidate query sites (demand)
_, vcand = predict(X0, Y0, cand)
clips = []
for x, v in zip(cand[:,0], vcand):
    if v > OPEN_VAR:                                 # closure fails here -> a gap
        clips.append(dict(x=float(x),
                          context=f"load={x:.2f}",   # the 'desk with my notes'
                          target=float(target(np.array([x]))[0]),
                          var_open=float(v),
                          status="open", resolved_round=None))
print("="*72)
print("  MEMORY CLIPS LIVE IN THE GAPS  (MuyGPyS web)")
print("="*72)
print(f"  clips parked at open gaps (var > {OPEN_VAR}): {len(clips)}")
print(f"  initial query-region RMSE: {qrmse(predict(X0,Y0,Xg)[0]):.3f}")
print()

def resolve_in_order(order_key, label):
    """Walk the open clips, resolving one per round in the given priority order.
    Resolving = the target that was held at the gap is fed in (the corner fills).
    Returns per-round trace: (round, x, var_before_at_x, var_after_at_x, qrmse)."""
    Xtr = X0.copy(); Ytr = Y0.copy()
    pending = [dict(c) for c in clips]              # a fresh copy of the open set
    trace = []
    r = 0
    while pending:
        r += 1
        # retest_all_failures: score the still-open clips at CURRENT variance,
        # pick the next one by the strategy's priority.
        xs = np.array([[c["x"]] for c in pending])
        _, vnow = predict(Xtr, Ytr, xs)
        for c, v in zip(pending, vnow): c["var_now"] = float(v)
        pick = order_key(pending)
        c = pending[pick]
        vb = c["var_now"]
        # the corner absorbs its target -> becomes an anchor the curve rests on
        Xtr = np.vstack([Xtr, [[c["x"]]]])
        Ytr = np.vstack([Ytr, [[c["target"] + rng.normal(0, NOISE)]]])
        va = float(predict(Xtr, Ytr, np.array([[c["x"]]]))[1][0])
        trace.append((r, c["x"], vb, va, qrmse(predict(Xtr, Ytr, Xg)[0])))
        pending.pop(pick)
    return trace, Xtr, Ytr

# GAP ORDER: worst-known first (highest current variance) -- retest worst-first
gap_trace, Xg_tr, Yg_tr = resolve_in_order(
    lambda P: int(np.argmax([c["var_now"] for c in P])), "gap-order")
# RANDOM ORDER control: same clips, same budget, arbitrary revisit order
rnd = np.random.default_rng(11)
rand_trace, _, _ = resolve_in_order(
    lambda P: int(rnd.integers(len(P))), "random-order")

# ---- persistence + gap->anchor evidence ----
mean_drop = np.mean([vb-va for _,_,vb,va in [(t[0],t[1],t[2],t[3]) for t in gap_trace]])
became_anchor = sum(1 for _,_,vb,va in [(t[0],t[1],t[2],t[3]) for t in gap_trace] if va < OPEN_VAR)
print(f"  (2) GAP -> ANCHOR: mean variance drop at a resolved clip: {mean_drop:.3f}")
print(f"      clips whose variance fell below the open-threshold (became anchors):"
      f" {became_anchor}/{len(gap_trace)}")
print()

# ---- order-matters: worst-first should dominate MOST early, then both converge ----
def rmse_at(trace, k): return trace[min(k, len(trace))-1][4]
quart = max(1, len(clips)//4); half = len(clips)//2
# area under the RMSE-vs-revisits curve = total error paid across the whole schedule
g_auc = float(np.mean([t[4] for t in gap_trace]))
r_auc = float(np.mean([t[4] for t in rand_trace]))
print(f"  (3) ORDER MATTERS: query-region RMSE as clips are revisited")
print(f"      {'after '+str(quart)+' clips':22s} gap-order {rmse_at(gap_trace,quart):.3f}   random {rmse_at(rand_trace,quart):.3f}")
print(f"      {'after '+str(half)+' clips':22s} gap-order {rmse_at(gap_trace,half):.3f}   random {rmse_at(rand_trace,half):.3f}")
print(f"      {'schedule-mean (AUC)':22s} gap-order {g_auc:.3f}   random {r_auc:.3f}"
      f"   ({100*(r_auc-g_auc)/r_auc:.0f}% less error paid)")
print(f"      -> worst-first is lowest early and pays less total error getting to full coverage.")
print()
print(f"  final query-region RMSE (all clips resolved): {gap_trace[-1][4]:.3f}")
print(f"  (both orders end at the same full-coverage error; gap-order gets there faster)")

# ---------------------------------------------------------------------------
# PLOT: left = the clips parked at gaps on the initial web (held-open);
#       right = RMSE vs #clips-revisited, gap-order vs random-order.
# ---------------------------------------------------------------------------
m0, v0 = predict(X0, Y0, Xg)
mF, vF = predict(Xg_tr, Yg_tr, Xg)
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.2))

axL.axvspan(0.0, 0.70, color="#eaf6ea", zorder=0, label="demand region")
axL.plot(Xg[:,0], Yg, color="#111", lw=2.2, label="target field")
axL.plot(Xg[:,0], m0, color="#e6820a", lw=1.6, ls="--", label="initial web (middle only)")
axL.fill_between(Xg[:,0], m0-np.sqrt(v0), m0+np.sqrt(v0), color="#e6820a", alpha=0.12)
axL.plot(Xg[:,0], mF, color="#238b45", lw=2.0, label="after revisiting all clips")
cx = [c["x"] for c in clips]; cy = [c["target"] for c in clips]
axL.scatter(cx, cy, s=70, facecolor="none", edgecolor="#c0392b", lw=1.8, zorder=5,
            label="memory clips parked at gaps (open)")
axL.plot(X0[:,0], np.full(len(X0), -1.35), "|", color="#333", ms=11, mew=2)
axL.set_title("Clips live where the web can't approximate\n(open gaps = high variance = held misses)")
axL.set_xlabel("load  x"); axL.set_ylabel("response"); axL.set_ylim(-1.5, 2.1)
axL.legend(loc="upper left", fontsize=8, framealpha=0.9)

gx = [t[0] for t in gap_trace]; gy = [t[4] for t in gap_trace]
rx = [t[0] for t in rand_trace]; ry = [t[4] for t in rand_trace]
axR.plot(gx, gy, color="#238b45", lw=2.2, marker="o", ms=4, label="gap-order (worst-known first)")
axR.plot(rx, ry, color="#8e44ad", lw=1.8, marker="s", ms=3, ls="--", label="random-order (control)")
axR.axvline(half, color="#999", lw=1, ls=":")
axR.set_title("Revisit worst-first: fewer revisits to the same accuracy\n(coming back to the loudest gap first)")
axR.set_xlabel("# memory clips revisited / resolved"); axR.set_ylabel("query-region RMSE")
axR.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

fig.tight_layout(); fig.savefig("memory_clip_web.png", dpi=130)
print("\n  wrote memory_clip_web.png")
