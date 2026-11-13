"""
environment_observer.py — the k candidate: the third observer, outside both cones.

THE IDEA (Jonathan)
-------------------
"would the k axis come from another observer watching the cones from a different
angle? maybe its methods would focus on making environments and seeing if the 2
sides can make sense in the right place. like the environment is the bridge?"

i and j are STATISTICS -- read the pixel field, reduce to a number. Every such
number is ultimately a function of the same frequency content, which is why they
collapse onto one direction (FOLDING_AXIS_INDEPENDENCE: spectral vs mixedness
r = 0.97; FOLDING_OBSERVER_FRAME: effective rank 2.82).

k is a SYNTHESIS. Hypothesise an environment -- here, a distant illuminant -- and
test whether it reconciles what BOTH observers see. Nothing about that is a
function of the pixel distribution, so there is no mechanism forcing it onto i.

THE BRIDGE, MADE LITERAL
------------------------
FOLDING_UNIVERSAL_READER measured that every C residue "sees both faces" and
locally confirms A on one side and B on the other (95-100%). A hypothesised
environment plays exactly that role between the two sides of the window: it is the
registrar both sides must agree with. FOLDING_SKIN_DETECTOR 3 names the failure:
the two domains both reach the seam, overlap is attempted, and cannot be reconciled
(theta != 1). A generated image should be one where NO single environment
reconciles both sides.

WHAT IS MEASURED (no model, no API, no GPU)
-------------------------------------------
For a Lambertian surface under a distant light, I = rho * (n . l). Without depth we
do not know n, but for a convex-ish region intensity rises toward the light, so the
fitted shading ramp of a region points at the projected illuminant. Fit a planar
ramp per region, keep only regions where the ramp actually explains the pixels
(smooth shading, not texture), and ask whether ONE illuminant explains them all.

  env_concentration       circular resultant of the per-region light azimuths.
                          1 = one light explains every region.
  env_scale_agreement     THE BRIDGE. Estimate the illuminant from the STRUCTURE
                          scale and again from the MARK scale. One environment must
                          explain both sides of the window. Angular agreement in
                          [0,1].
  env_residual            weighted circular variance left over after the best single
                          illuminant -- what one environment cannot account for.
  env_shaded_frac         fraction of the image that qualified as shaded surface.
                          The FIRED flag: this observer is conditional by design and
                          must report did-not-fire rather than a neutral score.

Sign is not asserted. Same rule as every other axis in this project: emit raw, fit
the sign on data (FOLDING_RECONSTRUCTION Part 0; the price of getting it wrong is
0.42 AUC -- FOLDING_OBSERVER_FRAME Part III).
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from skimage import color, io, segmentation, transform

WORK_SIDE = 512
K_STRUCTURE = 40      # the observer looking along the primary direction
K_MARK = 400          # the observer looking back
MIN_R2 = 0.55         # a region only votes if a planar ramp really explains it
MIN_AREA = 40
MIN_GRAD = 1e-3


def _load(path):
    img = io.imread(path)
    if img.ndim == 2:
        img = np.stack([img] * 3, -1)
    img = img[..., :3].astype(np.float64) / 255.0
    h, w = img.shape[:2]
    sc = WORK_SIDE / float(max(h, w))
    if sc < 1.0:
        img = transform.resize(img, (int(round(h * sc)), int(round(w * sc))),
                               anti_aliasing=True)
    return img


def _region_lights(lum, labels):
    """Per region: fit I = a + b*x + c*y. (b,c) points at the projected illuminant.

    Only regions the ramp genuinely explains get a vote -- on a textured region the
    'ramp' is noise, and letting it vote would turn this into a texture measure,
    which is the trap every other axis fell into.
    """
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    out = []
    for lb in np.unique(labels):
        m = labels == lb
        n = int(m.sum())
        if n < MIN_AREA:
            continue
        z = lum[m]
        if z.std() < 1e-4:
            continue
        A = np.stack([np.ones(n), xx[m] - xx[m].mean(), yy[m] - yy[m].mean()], 1)
        try:
            coef, *_ = np.linalg.lstsq(A, z, rcond=None)
        except np.linalg.LinAlgError:
            continue
        pred = A @ coef
        ss_res = float(((z - pred) ** 2).sum())
        ss_tot = float(((z - z.mean()) ** 2).sum()) + 1e-12
        r2 = 1.0 - ss_res / ss_tot
        b, c = coef[1], coef[2]
        g = float(np.hypot(b, c))
        if r2 < MIN_R2 or g < MIN_GRAD:
            continue
        # weight: how convincingly this region behaves like a shaded surface
        out.append((float(np.arctan2(c, b)), r2 * g * np.sqrt(n), n))
    return out


def _resultant(votes):
    """Weighted circular mean direction and resultant length in [0,1]."""
    if not votes:
        return np.nan, 0.0, 0.0
    ang = np.array([v[0] for v in votes])
    wgt = np.array([v[1] for v in votes])
    wgt = wgt / (wgt.sum() + 1e-12)
    z = (wgt * np.exp(1j * ang)).sum()
    return float(np.angle(z)), float(np.abs(z)), float(wgt.sum())


def _ang_agreement(a, b):
    """1 when two illuminant estimates coincide, 0 when opposed."""
    if np.isnan(a) or np.isnan(b):
        return np.nan
    return float((np.cos(a - b) + 1.0) / 2.0)


def analyse(path):
    rgb = _load(path)
    lum = color.rgb2lab(rgb)[..., 0] / 100.0
    h, w = lum.shape

    res = {"path": path, "fired": False, "env_concentration": np.nan,
           "env_scale_agreement": np.nan, "env_residual": np.nan,
           "env_shaded_frac": 0.0, "n_struct": 0, "n_mark": 0}

    lab_s = segmentation.slic(rgb, n_segments=K_STRUCTURE, compactness=10.0,
                              start_label=0, channel_axis=-1)
    lab_m = segmentation.slic(rgb, n_segments=K_MARK, compactness=10.0,
                              start_label=0, channel_axis=-1)

    vs = _region_lights(lum, lab_s)
    vm = _region_lights(lum, lab_m)
    res["n_struct"], res["n_mark"] = len(vs), len(vm)
    shaded_px = sum(v[2] for v in vm)
    res["env_shaded_frac"] = float(shaded_px / (h * w))

    # this observer is conditional: it must decline rather than guess
    if len(vs) < 3 or len(vm) < 8:
        return res
    res["fired"] = True

    a_s, R_s, _ = _resultant(vs)
    a_m, R_m, _ = _resultant(vm)
    all_v = vs + vm
    _, R_all, _ = _resultant(all_v)

    res["env_concentration"] = R_all
    res["env_residual"] = 1.0 - R_all
    # THE BRIDGE: does one environment explain both sides of the window?
    res["env_scale_agreement"] = _ang_agreement(a_s, a_m)
    res["env_struct_R"] = R_s
    res["env_mark_R"] = R_m
    return res


EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
FEATS = ["env_concentration", "env_scale_agreement", "env_residual",
         "env_shaded_frac", "env_struct_R", "env_mark_R"]


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
    ap.add_argument("--json", default="environment_metrics.json")
    a = ap.parse_args()

    rows = []
    for folder, label in ((a.real, "real"), (a.ai, "ai")):
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith(EXTS):
                continue
            r = analyse(os.path.join(folder, f))
            r["label"] = label
            rows.append(r)
            flag = "" if r["fired"] else "   [did not fire]"
            print(f"  [{label}] {f[:38]:<38} conc={r['env_concentration']:.3f} "
                  f"bridge={r['env_scale_agreement']:.3f} "
                  f"shaded={r['env_shaded_frac']:.2f}{flag}", flush=True)

    fired = [r for r in rows if r["fired"]]
    real = [r for r in fired if r["label"] == "real"]
    ai = [r for r in fired if r["label"] == "ai"]
    print(f"\n=== environment observer   fired on {len(fired)}/{len(rows)} "
          f"(real {len(real)}, ai {len(ai)}) ===")
    print(f"{'feature':<24}{'real':>10}{'ai':>10}{'AUC':>8}{'|d|':>7}")
    for f in FEATS:
        x = [r.get(f, np.nan) for r in real]
        y = [r.get(f, np.nan) for r in ai]
        v = _auc(x, y)
        if np.isnan(v):
            continue
        print(f"{f:<24}{np.nanmean(x):>10.3f}{np.nanmean(y):>10.3f}"
              f"{v:>8.3f}{abs(v - 0.5):>7.3f}")

    with open(a.json, "w") as fh:
        json.dump({"rows": rows}, fh, indent=2, default=str)
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
