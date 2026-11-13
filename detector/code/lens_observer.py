"""
lens_observer.py — the environment wears a lens (Jonathan).

"those are all pictures i took, probably with a blurry lens, and with the same
phone. oh but our environment could also put on a blurry lens too couldn't it?"

WHY THIS IS THE RIGHT MOVE
--------------------------
Blur has been the villain of this whole project. It is direction i
(FOLDING_OBSERVER_FRAME), it is what spectral and mixedness both secretly measure
(r = 0.97, FOLDING_AXIS_INDEPENDENCE), and it is what made the reconstruction axis
redundant. Every attempt to measure blur MAGNITUDE lands on the same crowded axis.

Jonathan's move dissolves the problem instead of fighting it: put the lens INSIDE
the hypothesised environment. Then blur stops being a nuisance statistic and becomes
something the environment has to EXPLAIN. The question changes from

    "how much blur is in this image?"          (a magnitude -> lands on i)
to
    "does ONE physical lens account for all of it?"   (a reconciliation -> k)

That is the same bridge/statistic split that FOLDING_ENVIRONMENT_BRIDGE measured:
env_concentration (a magnitude) landed ON the frame at r = 0.92; env_scale_agreement
(a reconciliation) landed OFF it at 0.21/0.27. Reconciliations are where the free
direction is.

WHAT A REAL LENS MUST DO, AND A PAINTED ONE NEED NOT
----------------------------------------------------
1. LATERAL CHROMATIC ABERRATION IS RADIAL. A real lens focuses red and blue at
   slightly different magnifications, so R and B are displaced from G *along the
   radius from the optical centre*, by an amount that GROWS with radius. This is
   the strongest test here: it is a vector field with a mandated direction and a
   mandated profile. A generated image has no optical centre to be radial about.

2. SHARPNESS FALLS OFF TOWARD THE CORNERS, smoothly and roughly radially.

3. DEFOCUS IS SPATIALLY ORGANISED. Real depth of field produces few, connected
   blur zones (a focal plane and its neighbourhood). Painted bokeh can be
   scattered, because it follows semantics rather than depth.

All three are WITHIN-IMAGE consistency questions, so none of them can be faked by
the content confound (FOLDING_PHYSICS_OBSERVER Part I): a landscape and a portrait
can each be lens-consistent or not.

FEATURES
    ca_radial_ratio     fraction of the R/B-vs-G displacement that is RADIAL.
                        ~1 = a real optical centre. ~0.5 = no preferred direction.
    ca_growth           correlation of |radial displacement| with radius.
                        Positive = the lateral-CA profile a real lens must have.
    sharp_radial_slope  sharpness vs radius (real lenses fall off outward).
    blur_field_coherence  how well the local blur map is explained by a few
                        connected zones rather than scattered patches.

HONEST WARNING ON JPEG
    Chroma subsampling (4:2:0 below q95) halves colour resolution and directly
    attacks the CA measurement. Both classes go through the identical encoder here
    so the comparison stays fair, but the measure is BLUNTED. Run --native for the
    strong version, and expect the two to disagree.

Sign is not asserted. Emit raw; fit on data (the price of an inherited sign is
0.42 AUC -- FOLDING_OBSERVER_FRAME Part III).
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from scipy import ndimage as ndi
from skimage import io, transform
from skimage.registration import phase_cross_correlation

WORK_SIDE = 768        # CA is sub-pixel; 512 throws away the signal
PATCH = 96
STRIDE = 80
MIN_TEXTURE = 0.010
MAX_SHIFT = 3.0        # px; larger means the match failed, not that the lens is bad


def _load(path, native=False):
    img = io.imread(path)
    if img.ndim == 2:
        img = np.stack([img] * 3, -1)
    img = img[..., :3].astype(np.float64) / 255.0
    if not native:
        h, w = img.shape[:2]
        sc = WORK_SIDE / float(max(h, w))
        if sc < 1.0:
            img = transform.resize(img, (int(round(h * sc)), int(round(w * sc))),
                                   anti_aliasing=True)
    return img


def _ca_field(rgb):
    """Per-patch sub-pixel displacement of R and B relative to G."""
    h, w = rgb.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    recs = []
    for y in range(0, h - PATCH + 1, STRIDE):
        for x in range(0, w - PATCH + 1, STRIDE):
            g = rgb[y:y + PATCH, x:x + PATCH, 1]
            if g.std() < MIN_TEXTURE:
                continue
            py, px = y + PATCH / 2.0 - cy, x + PATCH / 2.0 - cx
            r = float(np.hypot(py, px))
            if r < 1e-6:
                continue
            u = np.array([py / r, px / r])          # outward radial unit vector
            for ch, nm in ((0, "R"), (2, "B")):
                c = rgb[y:y + PATCH, x:x + PATCH, ch]
                if c.std() < MIN_TEXTURE:
                    continue
                try:
                    sh, _, _ = phase_cross_correlation(g, c, upsample_factor=20,
                                                       normalization=None)
                except Exception:
                    continue
                sh = np.asarray(sh, float)
                mag = float(np.hypot(*sh))
                if mag > MAX_SHIFT:
                    continue                        # registration failure, not optics
                radial = float(np.dot(sh, u))
                recs.append({"r": r, "mag": mag, "radial": radial,
                             "tang": float(mag ** 2 - radial ** 2) ** 0.5
                             if mag ** 2 > radial ** 2 else 0.0,
                             "w": float(g.std()), "ch": nm})
    return recs


def _blur_map(gray, win=32):
    lap = ndi.laplace(gray)
    return ndi.uniform_filter(lap ** 2, size=win)


def analyse(path, native=False):
    rgb = _load(path, native)
    h, w = rgb.shape[:2]
    gray = rgb.mean(2)
    out = {"path": path, "n_patches": 0, "ca_radial_ratio": np.nan,
           "ca_growth": np.nan, "sharp_radial_slope": np.nan,
           "blur_field_coherence": np.nan, "fired": False}

    # ---- 1 & 2: lateral chromatic aberration -------------------------------
    recs = _ca_field(rgb)
    out["n_patches"] = len(recs)
    if len(recs) >= 12:
        out["fired"] = True
        rad = np.array([abs(x["radial"]) for x in recs])
        mag = np.array([x["mag"] for x in recs])
        rr = np.array([x["r"] for x in recs])
        wt = np.array([x["w"] for x in recs])
        wt = wt / (wt.sum() + 1e-12)
        # how much of the displacement points along the radius?
        out["ca_radial_ratio"] = float((wt * (rad / (mag + 1e-9))).sum())
        # does it grow outward, as a real lens must?
        if rr.std() > 1e-6 and rad.std() > 1e-9:
            out["ca_growth"] = float(np.corrcoef(rr, rad)[0, 1])

    # ---- 3: sharpness falls off toward the corners -------------------------
    bm = _blur_map(gray)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    r = (r / r.max()).ravel()
    s = np.log(bm.ravel() + 1e-8)
    keep = np.isfinite(s)
    if keep.sum() > 100:
        A = np.stack([np.ones(keep.sum()), r[keep]], 1)
        coef, *_ = np.linalg.lstsq(A, s[keep], rcond=None)
        out["sharp_radial_slope"] = float(coef[1])

    # ---- 4: is the blur field organised into a few connected zones? --------
    b = bm[::4, ::4]
    b = (b - b.min()) / (np.ptp(b) + 1e-12)
    lvl = np.clip((b * 3).astype(int), 0, 2)        # three depth-ish zones
    # coherence = how much of each zone sits in its single largest blob
    tot = frag = 0
    for k in range(3):
        m = lvl == k
        n = int(m.sum())
        if n < 20:
            continue
        lab, nl = ndi.label(m)
        if nl == 0:
            continue
        big = max(int((lab == i).sum()) for i in range(1, nl + 1))
        tot += n
        frag += big
    if tot:
        out["blur_field_coherence"] = float(frag / tot)
    return out


EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
FEATS = ["ca_radial_ratio", "ca_growth", "sharp_radial_slope",
         "blur_field_coherence"]


def _auc(pos, neg):
    pos = np.asarray([v for v in pos if np.isfinite(v)], float)
    neg = np.asarray([v for v in neg if np.isfinite(v)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--ai", required=True)
    ap.add_argument("--native", action="store_true",
                    help="read originals at full size (CA survives; parity does not)")
    ap.add_argument("--json", default="lens_metrics.json")
    a = ap.parse_args()

    rows = []
    for folder, label in ((a.real, "real"), (a.ai, "ai")):
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith(EXTS):
                continue
            r = analyse(os.path.join(folder, f), a.native)
            r["label"] = label
            rows.append(r)
            print(f"  [{label}] {f[:34]:<34} radial={r['ca_radial_ratio']:.3f} "
                  f"growth={r['ca_growth']:+.3f} "
                  f"coh={r['blur_field_coherence']:.3f} n={r['n_patches']}",
                  flush=True)

    real = [r for r in rows if r["label"] == "real"]
    ai = [r for r in rows if r["label"] == "ai"]
    print(f"\n=== lens observer   real {len(real)}  ai {len(ai)}"
          f"{'  [NATIVE]' if a.native else '  [parity, CA blunted by chroma subsampling]'} ===")
    print(f"{'feature':<22}{'real':>10}{'ai':>10}{'AUC':>8}{'|d|':>7}")
    for f in FEATS:
        x = [r[f] for r in real]
        y = [r[f] for r in ai]
        v = _auc(x, y)
        if np.isnan(v):
            continue
        print(f"{f:<22}{np.nanmean(x):>10.3f}{np.nanmean(y):>10.3f}"
              f"{v:>8.3f}{abs(v - 0.5):>7.3f}")

    with open(a.json, "w") as fh:
        json.dump({"native": a.native, "rows": rows}, fh, indent=2, default=str)
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
