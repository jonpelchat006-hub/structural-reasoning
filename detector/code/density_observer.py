"""
density_observer.py -- Jonathan's data-density idea, with the format confound removed.

THE OBSERVATION
---------------
"the ai class has 11.92 bits per pixel and real is only 3.73. but we have jpeg
and png, but then a real photo should be evenly spread or computable right?"

The 11.92-vs-3.73 as measured is worthless: it is filesize/pixels, so it is
mostly PNG-vs-JPEG plus whatever quality slider each pipeline happened to use.
It says nothing about the image. But the idea underneath it is sound and has not
been tested in this project: **an image has an intrinsic information content, and
where that information sits in the frame is a property of how the image was
made.** Strip the file history and that quantity is measurable.

So: re-encode every image through ONE identical encoder and measure what comes
out. Format history erased, content complexity preserved.

THREE CHANNELS, because "density" is not one thing
--------------------------------------------------
  lossy      JPEG bits/pixel at fixed quality, header-corrected. Structure only
             -- the encoder discards grain. "How much scene is here."
  lossless   zlib bits/pixel after a horizontal-difference predictor. Structure
             PLUS grain, because nothing is discarded.
  noise      zlib bits/pixel of the residual after a 3x3 median filter. The grain
             channel on its own, with structure removed.

The third is the one that matters and it is the sharp form of "evenly spread".
A photograph has a sensor noise floor EVERYWHERE. Even a blank patch of sky
carries photon shot noise, so its local incompressible content never falls to
zero. A diffusion decoder produces genuinely smooth gradients: its flat regions
are flat all the way down. So the claim is not about the average density, it is
about **the floor** -- the emptiest part of the frame -- and about whether the
floor is bounded away from zero.

PRE-REGISTERED PREDICTIONS, written before the run
--------------------------------------------------
  1. Every `*_mean` FAILS the real-vs-real control. Mean density is scene
     complexity, which is genre, which is what killed the other 15 features.
     Foliage is dense, studio backdrop is not. Expect controls at or above target.
  2. `noise_floor_ratio` (= 10th-percentile cell noise density / mean cell noise
     density) is the candidate, because dividing by the image's own mean makes it
     SCALE-FREE: it asks "how empty is the emptiest region relative to this
     image", not "how complex is this image". Genre changes the numerator and
     denominator together.
  3. Direction: REAL should be HIGHER. Grain everywhere raises the floor.
  4. Honest risk: a real photo of a clear sky, and any real image that has been
     denoised (every phone applies noise reduction, every stock photo is
     processed), also has a low floor. Prediction 2 may well die on that. Say so
     if it does.

Nothing here is a claim until it clears `control_arms.py`. That gate killed
15 of 15 existing features.
"""
from __future__ import annotations

import io
import os
import zlib

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

G = 6
JQ = 75
_HDR = {}


def _jpeg_bits(a8):
    """Bits to JPEG-encode this patch at fixed quality, minus the header cost.

    The header matters: at a 128px cell a ~600-byte JPEG header is ~0.3 bpp,
    comparable to the signal. It is measured once per patch shape by encoding a
    flat mid-grey patch of the same size, and subtracted.
    """
    h, w = a8.shape
    key = (h, w)
    if key not in _HDR:
        b = io.BytesIO()
        Image.fromarray(np.full((h, w), 128, np.uint8)).save(b, "JPEG", quality=JQ)
        _HDR[key] = b.getbuffer().nbytes * 8
    b = io.BytesIO()
    Image.fromarray(a8).save(b, "JPEG", quality=JQ)
    return max(0.0, (b.getbuffer().nbytes * 8 - _HDR[key])) / float(h * w)


def _zlib_bpp(a8):
    return len(zlib.compress(a8.tobytes(), 6)) * 8 / float(a8.size)


def _channels(g8):
    """The three density channels for one 8-bit grayscale patch."""
    d = np.diff(g8.astype(np.int16), axis=1)          # horizontal predictor
    d = (d + 255).astype(np.uint16).astype(np.uint8)
    resid = g8.astype(np.int16) - ndi.median_filter(g8, 3).astype(np.int16)
    resid = np.clip(resid + 128, 0, 255).astype(np.uint8)
    return {"lossy": _jpeg_bits(g8),
            "lossless": _zlib_bpp(d),
            "noise": _zlib_bpp(resid)}


def _cells(h, w):
    for i in range(G):
        for j in range(G):
            yield i * G + j, slice(i * h // G, (i + 1) * h // G), \
                  slice(j * w // G, (j + 1) * w // G)


def per_cell(path):
    """Per-cell density in each channel. Shape (3, G*G)."""
    from image_io import load_pil
    g8 = np.asarray(load_pil(path).convert("L"))
    h, w = g8.shape
    out = {k: np.full(G * G, np.nan) for k in ("lossy", "lossless", "noise")}
    for idx, sy, sx in _cells(h, w):
        c = _channels(np.ascontiguousarray(g8[sy, sx]))
        for k, v in c.items():
            out[k][idx] = v
    return out


def _gini(x):
    x = np.sort(np.asarray([v for v in x if np.isfinite(v)], float))
    if len(x) < 2 or x.sum() <= 0:
        return np.nan
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def features(path):
    """Global density features. All shape-normalised; none uses filesize."""
    c = per_cell(path)
    f = {}
    for k, v in c.items():
        v = np.asarray(v, float)
        good = v[np.isfinite(v)]
        if len(good) < 4:
            continue
        mean = float(good.mean())
        floor = float(np.quantile(good, 0.10))
        peak = float(np.quantile(good, 0.90))
        f[f"{k}_mean"] = mean
        f[f"{k}_floor"] = floor
        f[f"{k}_cv"] = float(good.std() / (mean + 1e-9))
        f[f"{k}_gini"] = _gini(good)
        # scale-free: how empty is the emptiest region RELATIVE to this image
        f[f"{k}_floor_ratio"] = floor / (mean + 1e-9)
        f[f"{k}_dyn_range"] = peak / (floor + 1e-9)
    # how much of the data is incompressible grain rather than structure
    if "noise_mean" in f and "lossless_mean" in f:
        f["grain_share"] = f["noise_mean"] / (f["lossless_mean"] + 1e-9)
    if "lossy_mean" in f and "lossless_mean" in f:
        f["lossy_share"] = f["lossy_mean"] / (f["lossless_mean"] + 1e-9)
    return f


def dev_trim(v, drop=0.30, iters=6):
    """Same trimmed within-image baseline used in seam_rerun."""
    v = np.asarray(v, float)
    keep = np.isfinite(v)
    m = np.nanmedian(v)
    for _ in range(iters):
        d = np.abs(v - m)
        thr = np.nanquantile(d[keep], 1.0 - drop) if keep.sum() > 4 else np.inf
        sel = keep & (d <= thr)
        if sel.sum() < 4:
            break
        mn = np.median(v[sel])
        if np.isclose(mn, m):
            break
        m = mn
    s = np.median(np.abs(v[keep] - m)) + 1e-9
    return np.abs(v - m) / s


def within_image(path):
    """Per-cell deviation from the image's own trimmed density baseline --
    the localisation form. A regenerated region should carry a different
    amount of information per pixel than the authentic texture around it."""
    c = per_cell(path)
    return {f"dens_{k}_dev": dev_trim(v) for k, v in c.items()}
