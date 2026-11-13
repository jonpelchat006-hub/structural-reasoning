"""
parity_arms.py -- how much of the retired 0.952 was provenance, and how much was
file format, aspect ratio and orientation?

Four preparation arms, identical feature extraction in each. The only thing that
changes between arms is what is equalised before the observers see the image.

  A  AS-SHIPPED      what benchmark_v6.py did: no resize, no re-encode, no EXIF
                     orientation. Real class = ~1900px JPEG at 3.7 bpp, stored
                     sideways 15/22 of the time. AI class = ~2000-3000px PNG at
                     11.9 bpp, always upright.
  B  CURRENT PARITY  what bench_all_axes.py does today: longest side -> 512,
                     re-encode both classes through one JPEG q85 path.
                     Fixes format. Does NOT fix aspect ratio or orientation.
  C  + ORIENTATION   B, plus PIL exif_transpose so every image is upright.
  D  FULL PARITY     C, plus centre-crop to square then resize to a FIXED
                     448x448. Kills aspect ratio, pixel count and the
                     per-image resampling ratio all at once.

Trivial-separator baselines are reported alongside, because a feature that only
matches the aspect-ratio detector has not detected anything.
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mixedness_observer as mx
import nonlocal_observer as nl
import spectral_observer as sp

Q = 85
SIDE = 512
SQ = 448


# ---------------------------------------------------------------- preparation

def prep(src, dst, arm):
    """Write the arm's version of `src` to `dst` and return it."""
    im = Image.open(src)
    if arm in ("C", "D"):
        im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")

    if arm == "A":
        # as-shipped: hand the observers the original pixels, original encoding
        im.save(dst, "JPEG", quality=97, subsampling=0)
        return dst

    if arm == "D":
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        im = im.resize((SQ, SQ), Image.LANCZOS)
    else:
        w, h = im.size
        sc = SIDE / float(max(w, h))
        if sc < 1.0:
            im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=Q)
    buf.seek(0)
    Image.open(buf).save(dst, "JPEG", quality=Q)
    return dst


# ---------------------------------------------------------------- features

def feats(path):
    f = {}
    for k, v in sp.features(path).items():
        if isinstance(v, (int, float)):
            f["spectral." + k] = float(v)
    for k, v in mx.features(path).items():
        if isinstance(v, (int, float)):
            f["mixed." + k] = float(v)
    n = nl.analyse(path)
    for k in ("nonlocal_err_fine", "nonlocal_err_coarse", "nonlocal_asymmetry"):
        if isinstance(n.get(k), (int, float)):
            f["window." + k] = float(n[k])
    return f


def auc(pos, neg):
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    real = sorted(glob.glob("/mnt/user-data/uploads/Vesica AI/AI Detector/real photos/*"))
    ai = sorted(glob.glob("/mnt/user-data/uploads/Vesica AI/AI Detector/ai photos/*"))
    print(f"real {len(real)}   ai {len(ai)}")

    # ---- trivial separators, measured on the ORIGINAL files
    triv = {}
    for lab, paths in (("real", real), ("ai", ai)):
        rows = []
        for p in paths:
            im = Image.open(p)
            w, h = im.size
            tw, th = ImageOps.exif_transpose(im).size
            rows.append({"stored_ar": w / h, "true_ar": tw / th,
                         "bpp": os.path.getsize(p) * 8 / (w * h),
                         "megapixels": w * h / 1e6})
        triv[lab] = rows
    print(f"\n{'='*84}\nTRIVIAL SEPARATORS on the original files "
          f"(these know nothing about provenance)\n{'='*84}")
    triv_auc = {}
    for k in ("stored_ar", "true_ar", "bpp", "megapixels"):
        a = auc([r[k] for r in triv["real"]], [r[k] for r in triv["ai"]])
        triv_auc[k] = a
        flag = "  <-- PERFECT SEPARATION" if abs(a - 0.5) > 0.45 else ""
        print(f"  {k:<14} AUC {a:.3f}   |AUC-0.5| {abs(a-0.5):.3f}{flag}")

    out = {"trivial": triv_auc, "arms": {}}
    work = "_arms"
    os.makedirs(work, exist_ok=True)

    for arm in ("A", "B", "C", "D"):
        F = {"real": [], "ai": []}
        for lab, paths in (("real", real), ("ai", ai)):
            d = os.path.join(work, arm, lab)
            os.makedirs(d, exist_ok=True)
            for p in paths:
                dst = os.path.join(d, os.path.splitext(os.path.basename(p))[0] + ".jpg")
                prep(p, dst, arm)
                F[lab].append(feats(dst))
        keys = sorted({k for v in F.values() for r in v for k in r})
        res = {}
        for k in keys:
            res[k] = auc([r.get(k, np.nan) for r in F["real"]],
                         [r.get(k, np.nan) for r in F["ai"]])
        out["arms"][arm] = res
        print(f"  arm {arm} done", flush=True)

    NAMES = {"A": "A as-shipped (no parity)", "B": "B current parity (512+q85)",
             "C": "C + EXIF orientation", "D": "D full parity (square 448)"}
    keys = sorted(out["arms"]["A"])
    print(f"\n{'='*84}\nSTRENGTH OF EACH FEATURE, |AUC - 0.5|, BY ARM\n{'='*84}")
    print(f"{'feature':<30}" + "".join(f"{a:>13}" for a in "ABCD") + "   A->D collapse")
    for k in keys:
        v = [out["arms"][a].get(k, np.nan) for a in "ABCD"]
        s = [abs(x - 0.5) if np.isfinite(x) else np.nan for x in v]
        coll = "" if not (np.isfinite(s[0]) and np.isfinite(s[3])) else \
            f"{s[0]-s[3]:+.3f}"
        print(f"{k:<30}" + "".join(f"{x:>13.3f}" if np.isfinite(x) else f"{'-':>13}"
                                   for x in s) + f"   {coll:>8}")
    print(f"\n{'-'*84}")
    for i, a in enumerate("ABCD"):
        s = [abs(x - 0.5) for x in out["arms"][a].values() if np.isfinite(x)]
        print(f"{NAMES[a]:<32} best |AUC-0.5| {max(s):.3f}   "
              f"mean {np.mean(s):.3f}   n_features {len(s)}")
    print(f"\naspect-ratio-only detector (arm A input): |AUC-0.5| "
          f"{abs(triv_auc['stored_ar']-0.5):.3f}")
    print(f"bits-per-pixel detector   (arm A input): |AUC-0.5| "
          f"{abs(triv_auc['bpp']-0.5):.3f}")

    json.dump(out, open("parity_arms.json", "w"), indent=2, default=str)
    print("\nwrote parity_arms.json")


if __name__ == "__main__":
    main()
