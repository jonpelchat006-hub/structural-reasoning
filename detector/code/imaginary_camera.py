"""
imaginary_camera.py -- fit a camera to the image, then ask if any camera could have made it.

JONATHAN'S MOVE
---------------
"couldnt we still build an imaginary camera based on what we do see in the
picture? we could still see if any camera could output the file we see right?"

This removes the enrollment constraint, which is the biggest limitation on the
whole PRNU direction. PRNU asks "does this match THIS camera" and needs a
reference pattern from the physical device. Jonathan's version asks "is this file
consistent with having come from SOME camera at all" -- a PLAUSIBILITY test rather
than an IDENTITY test. No enrollment, and it works on a stranger's photo.

WHY IT CAN WORK: A CAMERA IS NOT AN ARBITRARY FUNCTION
------------------------------------------------------
A sensor obeys photon statistics. Light arrives as discrete quanta, so the count
in a well is Poisson, and Poisson variance equals its mean. After gain g and read
noise, the measured relationship is the **photon transfer curve**:

        sigma^2  =  a * I  +  b

`a` is the system gain, `b` is the read-noise floor. This is not a style or a
convention -- it is counting statistics. **Every authentic region of one exposure
sits on one line**, because there is one sensor, one gain, one ISO.

A diffusion decoder has no photon budget. Its smooth regions are smooth because
the model made them smooth, not because more light fell there. Its noise, where
it has any, does not track intensity.

So: fit `a` and `b` FROM THE IMAGE ITSELF -- that is the imaginary camera -- and
then ask two questions.

  1. GLOBAL, "could any camera output this?"  Is the fitted camera PHYSICAL?
     A real sensor has a > 0: brighter means noisier. If the best fit comes back
     with a <= 0, or with no intensity dependence at all, then no photon-counting
     device produced this frame. This needs NO reference of any kind.

  2. LOCAL, "does every part come from the SAME camera?"  Which blocks sit off
     the image's own line? A region that was regenerated carries whatever noise
     the decoder produced, and it will not lie on the line the rest of the frame
     defines.

The fit must be ROBUST, because the edited blocks are exactly the points trying to
drag the line toward themselves. Iteratively reweighted, dropping the worst
residuals -- the same lesson as the trimmed within-image baseline and the
low-quartile mask threshold: estimate from the population the signal cannot
dominate.

PRE-REGISTERED
--------------
  1. Authentic frames fit with a > 0 and a decent R^2.
  2. The fully regenerated frame fits with a near 0 or a much worse R^2 --
     "no camera could output this".
  3. Locally edited blocks sit off the frame's own line; the untouched original
     read at the same blocks does not.
  4. Risk, and it is the serious one: modern phones apply SPATIALLY VARYING noise
     reduction. That is a per-region operation and it will bend the photon
     transfer curve on authentic images too. If the control arm rises with the
     edited arm, that is what happened.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

BLOCK = 64


def _noise_field(g):
    """High-pass residual whose local variance estimates sensor noise.

    The Laplacian-of-differences kernel used in the within-image observers,
    scaled so its output variance equals the underlying noise variance for white
    noise -- so the fitted `a` and `b` stay in intensity units and remain
    physically interpretable.
    """
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], float) / 6.0
    return ndi.convolve(g, k)


def block_stats(gray, block=BLOCK):
    """Per-block (mean intensity, robust noise variance)."""
    r = _noise_field(gray)
    H, W = gray.shape
    nby, nbx = H // block, W // block
    I = np.empty((nby, nbx))
    V = np.empty((nby, nbx))
    for i in range(nby):
        for j in range(nbx):
            gi = gray[i * block:(i + 1) * block, j * block:(j + 1) * block]
            ri = r[i * block:(i + 1) * block, j * block:(j + 1) * block]
            I[i, j] = gi.mean()
            # MAD instead of variance: texture and edges are outliers in the
            # residual, and a plain variance would read them as noise
            V[i, j] = (1.4826 * np.median(np.abs(ri - np.median(ri)))) ** 2
    return I, V


def fit_camera(I, V, drop=0.30, iters=8):
    """Fit sigma^2 = a*I + b robustly. This IS the imaginary camera."""
    x = I.ravel()
    y = V.ravel()
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 12:
        return {"a": np.nan, "b": np.nan, "r2": np.nan, "n": len(x)}
    w = np.ones(len(x), bool)
    a = b = 0.0
    for _ in range(iters):
        A = np.vstack([x[w], np.ones(w.sum())]).T
        (a, b), *_ = np.linalg.lstsq(A, y[w], rcond=None)
        res = np.abs(y - (a * x + b))
        thr = np.quantile(res[w], 1.0 - drop) if w.sum() > 12 else np.inf
        nw = res <= thr
        if nw.sum() < 12 or (nw == w).all():
            break
        w = nw
    pred = a * x + b
    ss = 1.0 - ((y[w] - pred[w]) ** 2).sum() / \
        (((y[w] - y[w].mean()) ** 2).sum() + 1e-30)
    return {"a": float(a), "b": float(b), "r2": float(ss), "n": int(w.sum()),
            "inlier_frac": float(w.mean())}


def plausibility(cam):
    """Could ANY photon-counting device have produced this? No reference needed.

    A physical sensor has positive gain -- brighter regions are noisier, because
    more photons means more shot noise. Zero or negative fitted gain means the
    frame's noise does not respond to light at all, which no camera does.
    """
    a, r2 = cam["a"], cam["r2"]
    if not np.isfinite(a) or not np.isfinite(r2):
        return "unmeasurable", np.nan
    score = a * max(r2, 0.0)
    if a <= 0:
        return "NO CAMERA -- gain is non-positive", score
    if r2 < 0.15:
        return "NO CAMERA -- noise does not track intensity", score
    return "physical", score


def offline_map(I, V, cam):
    """Per-block distance from the image's own photon transfer line, in robust
    scale units. High = this block does not belong to the camera the rest of the
    frame implies."""
    pred = cam["a"] * I + cam["b"]
    res = V - pred
    s = 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-12
    return np.abs(res) / s
