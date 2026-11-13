#!/usr/bin/env python3
"""
Alteration observer — the "second layer" detector (model-free, $0).
===================================================================
Jonathan's read: an alteration is a SECOND LAYER laid over the original, and it
comes in two forms with complementary signatures —

  LOCAL composite / inpaint  → the layer covers PART of the image, so it has a
      BORDER: a closed seam where the pasted region meets the original. Only the
      segments on each side of that border flag it. Signature = INCONSISTENCY
      across the boundary (noise level, compression/ELA), i.e. spatial variance
      in the forensic maps.

  GLOBAL filter / style pass  → the layer covers the WHOLE image ("two pieces of
      paper glued together"), so there is no internal border — but the glue shows
      as a UNIFORM second-surface signature everywhere: natural sensor noise is
      suppressed and flattened by the pass. Signature = uniformly low / consistent
      noise (a too-clean, too-even layer).

So one axis, two readouts:
  local_score           spatial inconsistency of the noise map (composite seam)
  ela_incons            spatial inconsistency of Error-Level-Analysis (splice tell)
  global_suppression    uniform noise suppression (the whole-image filter layer)

Both are "detect a layer" — bounded (find the border) vs full (find the overlay).
Feeds the axis_router 'alteration' axis (local) and complements 'reconstruct'
(the deeper manifold/layer detector, which needs a model — next build).
Self-tested on synthetic composites and filters (no dataset, reset-safe).
"""
import io
import numpy as np
from PIL import Image
from scipy import ndimage

B = 16  # forensic block size


def _noise_map(gray):
    resid = gray - ndimage.gaussian_filter(gray, 1.5)
    return np.sqrt(ndimage.uniform_filter(resid ** 2, size=12))


def _blocks(m):
    H, W = m.shape
    h, w = H // B * B, W // B * B
    return m[:h, :w].reshape(h // B, B, w // B, B).mean((1, 3))


def _ela(rgb_u8, q=90):
    buf = io.BytesIO(); Image.fromarray(rgb_u8).save(buf, "JPEG", quality=q); buf.seek(0)
    re = np.asarray(Image.open(buf).convert("RGB"), float)
    return np.abs(rgb_u8.astype(float) - re).mean(2)


def features(rgb_u8):
    gray = rgb_u8.astype(float).mean(2)
    nm = _noise_map(gray)
    nb = _blocks(nm)
    # local = a BOUNDED region whose noise differs (a splice) — robust to overall noise level.
    anom = np.abs(nb - np.median(nb))
    mask = anom > (anom.mean() + 2 * anom.std())
    lbl, n = ndimage.label(mask)
    blob = 0.0
    if n:
        sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))
        blob = float(sizes.max() / mask.size)                    # largest bounded anomaly / frame
    global_suppression = float(1.0 / (1.0 + nm.mean()))          # filter layer: uniform low noise
    eb = _blocks(_ela(rgb_u8))
    ela_incons = float(eb.std() / (eb.mean() + 1e-6))
    return {"local_score": blob, "ela_incons": ela_incons,
            "global_suppression": global_suppression, "noise_mean": float(nm.mean())}


def localize(rgb_u8):
    """Return an alteration heatmap (block grid) + the largest bounded anomaly (the composite region)."""
    gray = rgb_u8.astype(float).mean(2)
    nb = _blocks(_noise_map(gray))
    anom = np.abs(nb - np.median(nb))
    mask = anom > (anom.mean() + 2 * anom.std())
    lbl, n = ndimage.label(mask)
    biggest = 0.0
    if n:
        sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))
        biggest = float(sizes.max() / mask.size)                 # fraction of the frame that is one bounded anomaly
    return anom, biggest


def verdict(rgb_u8, blob_tau=0.04, global_tau=0.5):
    f = features(rgb_u8)
    flags, notes = [], []
    if f["local_score"] > blob_tau:
        flags.append("local_composite")
        notes.append("a bounded region's noise differs from its surround — a splice seam.")
    if f["global_suppression"] > global_tau and f["local_score"] <= blob_tau:
        flags.append("global_filter_layer")
        notes.append("uniformly suppressed noise across the whole frame — a filter/style layer ('glued paper').")
    # map to an axis_router 'alteration' value: -1 = altered, +0.5 = clean
    altered = bool(flags)
    value = -min(1.0, 4.0 * f["local_score"] + 1.2 * max(0.0, f["global_suppression"] - global_tau)) if altered else 0.5
    return {"value": float(value), "confidence": 0.7 if altered else 0.4,
            "flags": flags, "note": " ".join(notes), "features": f}


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST — synthetic composites and filters (no dataset)
# ══════════════════════════════════════════════════════════════════════════════

def _base(seed=0):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:256, 0:256]
    img = (60 + 0.4 * x + 0.3 * y) % 255
    img = np.stack([img, (img * 0.9) % 255, (img * 1.1) % 255], -1)
    img[40:120, 60:150] = [180, 90, 70]          # a shape
    img += rng.normal(0, 9, img.shape)           # natural sensor noise
    return np.clip(img, 0, 255).astype(np.uint8)


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  [{'PASS' if c else 'FAIL'}] {n}"); ok = ok and c

    clean = _base(0)

    # composite: paste a low-noise patch from a "different source"
    comp = clean.copy()
    rng = np.random.default_rng(1)
    patch = np.clip(np.stack([np.full((96, 96), 150.0)] * 3, -1) + rng.normal(0, 1.0, (96, 96, 3)), 0, 255)
    comp[120:216, 120:216] = patch.astype(np.uint8)   # a smoother (different-noise) pasted block

    # global filter: blur the whole thing (a uniform layer that suppresses noise)
    filt = np.stack([ndimage.gaussian_filter(clean[..., c].astype(float), 2.0) for c in range(3)], -1)
    filt = np.clip(filt, 0, 255).astype(np.uint8)

    fc, fp, ff = features(clean), features(comp), features(filt)
    print(f"   clean : local {fc['local_score']:.2f}  global {fc['global_suppression']:.2f}")
    print(f"   comp  : local {fp['local_score']:.2f}  global {fp['global_suppression']:.2f}")
    print(f"   filter: local {ff['local_score']:.2f}  global {ff['global_suppression']:.2f}")

    check("composite raises LOCAL inconsistency above clean & filter",
          fp["local_score"] > fc["local_score"] and fp["local_score"] > ff["local_score"])
    check("filter raises GLOBAL suppression above clean & composite",
          ff["global_suppression"] > fc["global_suppression"] and ff["global_suppression"] > fp["global_suppression"])
    check("composite localizes a bounded anomaly", localize(comp)[1] > 0.02)
    check("composite verdict flags local_composite", "local_composite" in verdict(comp)["flags"])
    check("filter verdict flags global_filter_layer", "global_filter_layer" in verdict(filt)["flags"])
    check("clean verdict flags nothing", not verdict(clean)["flags"])

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if self_test() else 1)
