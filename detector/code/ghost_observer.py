"""
ghost_observer.py -- the edge-on observer, second channel: counting the layers.

JONATHAN'S FRAME
----------------
"the 2 observers would be looking at the window from the edge and they would see
the layers on the window stacking up that hold the provenance info? then the
other 2 would be looking at what image that stack makes."

That is the two-channel result stated as geometry, and it is worth taking
literally. The existing two-sided window (FOLDING_TWO_SIDED_WINDOW) has BOTH its
observers looking THROUGH the glass at the content, from opposite ends of the
scale axis -- forward coarse-to-fine and backward fine-to-coarse. Both are
face-on. That is why the whole free stack collapses to 2.8 effective dimensions
and why PC1 turned out to be photographic genre.

An EDGE-ON observer does not look at the picture at all. It looks at the stack of
processing layers the picture was pushed through. PRNU is already one of these --
it reads the BOTTOM layer, the sensor, through everything above it, and its
strength degrades monotonically as layers accumulate:

    camera-original   PCE 1460
    resized/reshared  PCE   18
    regenerated       PCE  5.7

This file is the SECOND edge-on channel, and unlike PRNU it needs no reference
and no enrolled device.

THE METHOD -- JPEG ghosts (Farid 2009)
--------------------------------------
A JPEG that was compressed at quality q is close to a FIXED POINT of the quality-q
quantiser: re-encode it at q and little changes. Re-encode at any other quality
and more changes. So sweeping q and recording how much the image moves traces a
curve whose minimum sits at the quality it was last saved at.

A region that has been through the press TWICE carries two quantisers in its
history and its curve has a different shape from a region pressed once. That is
Jonathan's "layers stacking up", made into a number -- and because it is computed
per block, it LOCALISES.

WHY IT IS INDEPENDENT OF EVERYTHING ELSE HERE
---------------------------------------------
It reads the compression history, not the content and not the sensor. It should
therefore be uncorrelated with the 34 dead content features AND with PRNU. If it
carries signal, the edge-on axis has two independent channels rather than one,
which is the difference between a lucky measure and an axis.

PRE-REGISTERED
--------------
  1. Camera originals (one compression) and their edits (camera compression, then
     the editor's re-save) should differ in ghost shape. The edits are q94, the
     originals q96 -- so the minimum should sit at a different place.
  2. Risk, and it is serious: the whole file is re-saved by the editor, so the
     GLOBAL curve may be identical for both. The interesting question is whether
     the edited REGION differs from its own surroundings, since those pixels went
     through the generator and then one press, while the rest went through the
     camera and then the same press.
  3. Everything is measured against the untouched original, same blocks. If the
     original shows the same pattern, the measure is reading content.
"""
from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image

QUALITIES = list(range(60, 100, 3))
BLOCK = 128


def _reencode(im, q):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    b.seek(0)
    return np.asarray(Image.open(b).convert("L"), dtype=np.float64)


def ghost_stack(path, qualities=QUALITIES):
    """Difference field for each re-encode quality. Shape (len(q), H, W)."""
    im = Image.open(path).convert("RGB")
    base = np.asarray(im.convert("L"), dtype=np.float64)
    out = np.empty((len(qualities),) + base.shape, dtype=np.float32)
    for i, q in enumerate(qualities):
        out[i] = (base - _reencode(im, q)) ** 2
    return out, base.shape


def block_curves(stack, shape, block=BLOCK):
    """Mean squared difference per block per quality. Shape (nby, nbx, nq)."""
    nq, H, W = stack.shape
    nby, nbx = H // block, W // block
    c = np.empty((nby, nbx, nq), dtype=np.float64)
    for i in range(nby):
        for j in range(nbx):
            c[i, j] = stack[:, i * block:(i + 1) * block,
                            j * block:(j + 1) * block].mean(axis=(1, 2))
    return c


def curve_features(curve, qualities=QUALITIES):
    """Summarise one block's ghost curve.

    q_min      the quality this block is closest to a fixed point of -- i.e. what
               it was last pressed at
    depth      how sharply it sits in that minimum, normalised. A block pressed
               ONCE sits in a deep clean minimum; a block whose content was
               generated and then pressed has weaker attachment to any single
               quantiser
    slope_hi   how fast the curve falls approaching the top of the sweep
    """
    q = np.asarray(qualities, float)
    c = np.asarray(curve, float)
    if not np.isfinite(c).all() or c.max() <= 0:
        return {"q_min": np.nan, "depth": np.nan, "slope_hi": np.nan}
    i = int(np.argmin(c))
    lo, hi = c.max(), c[i]
    return {"q_min": float(q[i]),
            "depth": float((lo - hi) / (lo + 1e-12)),
            "slope_hi": float((c[-1] - c[i]) / (lo + 1e-12))}


def image_features(path):
    st, shp = ghost_stack(path)
    cur = block_curves(st, shp)
    nby, nbx, _ = cur.shape
    feats = np.empty((nby, nbx, 3))
    for i in range(nby):
        for j in range(nbx):
            f = curve_features(cur[i, j])
            feats[i, j] = [f["q_min"], f["depth"], f["slope_hi"]]
    glob = curve_features(cur.reshape(-1, cur.shape[-1]).mean(0))
    return {"per_block": feats, "global": glob, "grid": (nby, nbx)}
