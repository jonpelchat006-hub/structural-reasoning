"""
image_io.py -- the single place every observer should load an image from.

WHY THIS FILE EXISTS
--------------------
Neither PIL's `Image.open` nor `skimage.io.imread` applies the EXIF Orientation
tag (tag 274). A phone photo taken in portrait is stored as a landscape-shaped
buffer plus a flag that says "rotate me". Every loader in this project ignored
that flag, so:

  * 15 of 22 photos in `real photos/` were scored ROTATED 90 DEGREES, while
    0 of 17 images in `ai photos/` were -- they have no EXIF at all. Stored
    aspect ratio therefore separated the two classes at AUC 1.000. Applying the
    tag drops that to 0.591.

  * 7 of the 13 seam pairs in `more photos/altered/` have the original stored
    4000x2252 with orientation=6 while the edit -- rewritten by the editing app,
    which baked the rotation in -- is stored 2252x4000 with orientation=1. Read
    naively, those two arrays are not even the same shape, so any pixel diff
    between them is meaningless.

Use `load_rgb` / `load_gray` everywhere. Never call `Image.open` or `imread`
directly in an observer.
"""
from __future__ import annotations

import io as _io
import os

import numpy as np
from PIL import Image, ImageOps


def load_pil(path):
    """Open `path` with the EXIF Orientation tag APPLIED. Always upright."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def load_rgb(path):
    """float64 HxWx3 in [0,1], upright."""
    return np.asarray(load_pil(path), dtype=np.float64) / 255.0


def load_gray(path):
    """float64 HxW in [0,1] (CIE L* / 100), upright."""
    from skimage import color
    return color.rgb2lab(load_rgb(path))[..., 0] / 100.0


def is_sideways(path):
    """True if this file's stored buffer needs rotating to display correctly."""
    im = Image.open(path)
    return ImageOps.exif_transpose(im).size != im.size


def parity(path, dst, side=512, q=85, square=None):
    """Write a parity-normalised copy of `path` to `dst`.

    Equalises, in this order:
      orientation  -- EXIF applied, so nothing is scored sideways
      geometry     -- if `square` is set, centre-crop to square then resize to
                      square x square. This is what kills aspect ratio, pixel
                      count AND the per-image resampling ratio in one step.
                      Without it, only the longest side is matched and a
                      landscape photo is still downsampled differently from a
                      portrait one.
      encoding     -- one identical JPEG quality-q round trip for every class,
                      so PNG-native generator output and camera JPEG arrive at
                      the observers through the same encoder.
    """
    im = load_pil(path)
    if square:
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        im = im.resize((square, square), Image.LANCZOS)
    else:
        w, h = im.size
        sc = side / float(max(w, h))
        if sc < 1.0:
            im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)
    buf = _io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    buf.seek(0)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    Image.open(buf).save(dst, "JPEG", quality=q)
    return dst


def audit(paths, label=""):
    """Report the trivial separators for a group of files. Call this on every
    new class BEFORE benchmarking it -- if stored aspect ratio or bits-per-pixel
    separates your classes, no observer result from that set can be trusted."""
    rows = []
    for p in paths:
        im = Image.open(p)
        w, h = im.size
        tw, th = ImageOps.exif_transpose(im).size
        rows.append({"path": p, "stored_ar": w / h, "true_ar": tw / th,
                     "bpp": os.path.getsize(p) * 8 / (w * h),
                     "megapixels": w * h / 1e6,
                     "sideways": (tw, th) != (w, h),
                     "format": im.format})
    if label:
        n = sum(r["sideways"] for r in rows)
        fmts = sorted({r["format"] for r in rows})
        print(f"  {label:<12} n={len(rows):<4} sideways={n}/{len(rows)}  "
              f"formats={','.join(fmts)}  "
              f"bpp median={np.median([r['bpp'] for r in rows]):.2f}  "
              f"stored_ar median={np.median([r['stored_ar'] for r in rows]):.2f}")
    return rows
