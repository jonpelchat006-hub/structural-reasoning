#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bottle_closure.py -- the ship in the bottle seen from BOTH sides of the waterline.

Jonathan's read: the GP curve we measured is the ship-in-the-bottle seen from UNDER
the water -- the outline the bottle leaves on the surface (the forward view / the
"below" silhouette). But we are BIDIRECTIONAL, so there is a RETURN PATH: a second
curve seen from ABOVE that should CLOSE the shape. Two observers reading the same
screen -- but the screen is the water's surface -- and the shadow from below and the
shadow from above are NOT the same. Where they differ is the seam.

Framework backing (all in-project):
  * two cones (void observer z=0 up, infinity observer z=inf down) meet at x=1 ->
    the VESICA (Double_Bounce Fig 24; Shovelcat_15 4.2).
  * meet-in-the-middle: forward reachable-map + upside-down (roof/retro) reachable-map,
    and where they OVERLAP is the closed shape (SPARSE_VESICA 18.17-18.18: "two shapes
    meet in the vesica -> closure").
  * round-trip identity in the vesica: theta -> ln(theta) -> e^ln = theta; forward
    COMPRESSES (psi/integrate), return EXPANDS (phi/differentiate); they are mutual
    inverses ONLY in the overlap -- outside it the round-trip loses information
    (Shovelcat_10_1; "measurement is irreversible").
  * refraction at the waterline -> the two eyes disagree = the SEAM (waterline model
    4.2; FOLDING_SKIN_DETECTOR 3: the seam is a vesica of FAILED verification).

THE MEASURED CLAIM
------------------
Take a NON-MONOTONE field y=f(x) (it folds -- the sin makes it bend back). Then:
  forward  f: x -> y      (the below silhouette / generate)
  return   g: y -> x      (the above silhouette / verify)
Round-trip  x -> f(x) -> g(.) = x_hat.  Closure error = |x_hat - x|.

  * On the MONOTONE stretches the two silhouettes coincide -- the bottle SEALS,
    round-trip ~ noise. That is the vesica where forward and return are mutual
    inverses; a sealed point is an invariant (sinks to the seabed).
  * At the FOLDS the return is genuinely MULTIVALUED (same y, two x's): the shadow
    from above CANNOT tell which branch, so it lands between them -> big closure
    error. That is the seam, forced by geometry, not injected.
  * REAL CONTEXT closes it. Give the return path the branch/scene the miss happened
    in (which fold you're on) and the ambiguity collapses -- the bottle seals even
    across the folds. "We can add real context too" = context is what SEALS THE
    BOTTLE, measured.

Honest bound: 1-D toy on the real MuyGPyS posterior. It demonstrates the MECHANISM
(return path closes only in the vesica; context disambiguates the seam), not a full
agent's inverse model.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from MuyGPyS.gp import MuyGPS
from MuyGPyS.gp.kernels import Matern
from MuyGPyS.gp.deformation import Isotropy, l2
from MuyGPyS.gp.hyperparameter import ScalarParam
from MuyGPyS.gp.noise import HomoscedasticNoise
from MuyGPyS.neighbors import NN_Wrapper

rng = np.random.default_rng(7)
NOISE = 0.015

def f(x):                       # a folding field: bends back on itself twice
    x = np.asarray(x, float)
    return 0.7*np.sin(5.5*x) + 0.5*x

def fp(x):                      # slope -> sign gives the monotone branch
    x = np.asarray(x, float)
    return 0.7*5.5*np.cos(5.5*x) + 0.5

def gp(ls):
    return MuyGPS(kernel=Matern(smoothness=ScalarParam(1.5),
                  deformation=Isotropy(l2, length_scale=ScalarParam(ls))),
                  noise=HomoscedasticNoise(1e-4))

def predict(Xtr, Ytr, Xte, ls, nn=25):
    g = gp(ls); k = min(nn, len(Xtr)-1)
    nbrs = NN_Wrapper(Xtr, k, nn_method="exact", algorithm="ball_tree")
    ni, _ = nbrs.get_nns(Xte)
    cw, pw, nt = g.make_predict_tensors(np.arange(len(Xte)), ni, Xte, Xtr, Ytr)
    m = g.posterior_mean(g.kernel(pw), g.kernel(cw), nt)
    v = g.posterior_variance(g.kernel(pw), g.kernel(cw))
    return np.asarray(m).ravel(), np.asarray(v).ravel()

def branch_of(x):
    """REAL CONTEXT: which monotone fold-branch a query sits on (0,1,2,...),
    counted by slope-sign changes -- 'which side of the fold / which scene'."""
    x = np.atleast_1d(np.asarray(x, float))
    # turning points of f on [0,1] where slope changes sign
    xs = np.linspace(0, 1, 4000); s = np.sign(fp(xs))
    turns = xs[1:][s[1:] != s[:-1]]
    return np.searchsorted(turns, x)          # branch index per x

# ---- training data ----
Xtr = np.sort(rng.uniform(0, 1, 160))[:, None]
Ytr = f(Xtr) + rng.normal(0, NOISE, (len(Xtr), 1))

# ---- FORWARD (below silhouette): x -> y ----
Xq = np.linspace(0.02, 0.98, 220)[:, None]
yq_true = f(Xq).ravel()
yhat, vfwd = predict(Xtr, Ytr, Xq, ls=0.05)

# ---- RETURN, no context (above silhouette): y -> x ----
Yin = Ytr.copy()                          # inputs are now the y-values
Xout = Xtr.copy()                         # targets are now the x-values
y_query = (f(Xq) + rng.normal(0, NOISE, Xq.shape))   # the y we bounce back from
xhat_nc, vinv_nc = predict(Yin, Xout, y_query, ls=0.05)

# ---- RETURN, WITH real context: [y, branch] -> x ----
CSCALE = 3.0                              # push different branches far apart in NN space
Btr = branch_of(Xtr.ravel())[:, None] * CSCALE
Yin_c = np.hstack([Ytr, Btr])                        # 2-D input: (y, context)
Bq = branch_of(Xq.ravel())[:, None] * CSCALE         # the query's real branch/scene
y_query_c = np.hstack([y_query, Bq])
xhat_c, vinv_c = predict(Yin_c, Xout, y_query_c, ls=0.05)

# ---- round-trip closure error along x ----
err_nc = np.abs(xhat_nc - Xq.ravel())
err_c  = np.abs(xhat_c  - Xq.ravel())

# fold locations (the seams)
xs = np.linspace(0, 1, 4000); s = np.sign(fp(xs))
folds = xs[1:][s[1:] != s[:-1]]

# THE REAL AXIS: how many x share this query's reading y (preimage multiplicity).
# 1 = the reading is unique -> the bottle seals there on its own. >=2 = the shadow
# from above cannot tell the branches apart -> ambiguous, needs context.
def multiplicity(yval):
    d = f(xs) - yval
    return int(np.sum(d[1:]*d[:-1] < 0))
mult = np.array([multiplicity(y) for y in f(Xq.ravel())])
uniq = mult <= 1
ambig = mult >= 2

print("="*72)
print("  THE BOTTLE FROM BOTH SIDES: forward (below) + return (above) closure")
print("="*72)
print(f"  folds (where f bends back -> the map stops being invertible): x = "
      f"{', '.join(f'{v:.2f}' for v in folds)}")
print(f"  a reading y is shared by up to {mult.max()} states x (the folds stack branches)")
print()
print(f"  round-trip closure error |x_hat - x|            {'no context':>12} {'+ context':>12}")
print(f"  {'unique reading (naturally sealed)':46s} {err_nc[uniq].mean():>12.3f} {err_c[uniq].mean():>12.3f}")
print(f"  {'shared reading (>=2 branches = the seam)':46s} {err_nc[ambig].mean():>12.3f} {err_c[ambig].mean():>12.3f}")
print(f"  {'overall':46s} {err_nc.mean():>12.3f} {err_c.mean():>12.3f}")
print()
fix_a = 100*(err_nc[ambig].mean()-err_c[ambig].mean())/max(err_nc[ambig].mean(),1e-9)
fix_o = 100*(err_nc.mean()-err_c.mean())/max(err_nc.mean(),1e-9)
print(f"  -> the FORWARD view is single-valued and closes trivially; the RETURN view is")
print(f"     the hard half. Where a reading has one preimage the bottle seals on its own")
print(f"     ({err_nc[uniq].mean():.3f}); where the folds stack 2+ branches under one reading, the")
print(f"     shadow from above lands BETWEEN them -- error {err_nc[ambig].mean():.3f}. That gap is the seam.")
print(f"  -> adding the REAL CONTEXT (which branch/scene the query is on) collapses the")
print(f"     shared-reading error by {fix_a:.0f}% (overall {fix_o:.0f}%): context is the missing")
print(f"     coordinate that makes the return path a true inverse -- it SEALS the bottle.")

# ---------------------------------------------------------------------------
# PLOT
#   left  : the (x,y) plane. black = true curve. the RETURN silhouette plotted as
#           (x_hat, y): with context it lands ON the curve (closed); without, it is
#           pulled OFF at the folds (the shadow disagrees). folds marked.
#   right : round-trip closure error vs x -- no-context spikes at the seams,
#           context stays flat (the vesica extended across the folds).
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.3))

order = np.argsort(Xq.ravel())
axL.plot(Xq.ravel()[order], yq_true[order], color="#111", lw=2.4, zorder=3,
         label="the object  y=f(x)  (the bottle)")
axL.plot(Xq.ravel()[order], yhat[order], color="#2b8cbe", lw=1.4, ls=":", zorder=3,
         label="forward / below silhouette")
axL.scatter(xhat_nc, y_query.ravel(), s=16, color="#e6820a", alpha=0.75, zorder=4,
            label="return / above, NO context (shadow off at folds)")
axL.scatter(xhat_c, y_query.ravel(), s=14, color="#238b45", alpha=0.8, zorder=5,
            label="return / above, + REAL context (seals)")
for xf in folds:
    axL.axvline(xf, color="#c0392b", lw=1, ls="--", alpha=0.5)
axL.text(folds[0], axL.get_ylim()[1], "  seams (folds)", color="#c0392b",
         fontsize=8.5, va="top")
axL.set_xlabel("x  (the state)"); axL.set_ylabel("y  (the reading at the surface)")
axL.set_title("Two silhouettes of one bottle\nreturn lands on the curve only where it can pick the branch")
axL.legend(loc="lower right", fontsize=7.6, framealpha=0.92)

axR.axhline(0, color="#ccc", lw=0.8)
for xf in folds:
    axR.axvline(xf, color="#c0392b", lw=1, ls="--", alpha=0.5)
axR.plot(Xq.ravel(), err_nc, color="#e6820a", lw=2.0, label="round-trip error, NO context")
axR.plot(Xq.ravel(), err_c,  color="#238b45", lw=2.0, label="round-trip error, + REAL context")
axR.fill_between(Xq.ravel(), 0, err_nc, where=ambig, color="#e6820a", alpha=0.12)
axR.set_xlabel("x  (the state)"); axR.set_ylabel("|x_hat - x|   (closure error)")
axR.set_title("The seam is where the round-trip fails to close\ncontext extends the vesica across the folds")
axR.legend(loc="upper right", fontsize=8.2, framealpha=0.92)

fig.tight_layout(); fig.savefig("bottle_closure.png", dpi=130)
print("\n  wrote bottle_closure.png")
