"""
nonlocal_observer.py — the LOCAL side of the two-sided window, done with a
predictor that can tell "sharp" apart from "unpredictable".

WHY THE FIRST ATTEMPT FAILED
----------------------------
predictability_observer.py tested Jonathan's claim with a harmonic (Laplace) fill
as the predictor. The direction came out right (asymmetry 0.320 real vs 0.188 AI,
AUC 0.740) but it correlated |r| = 0.89 with lap_var -- it was measuring sharpness.

The reason is a property of the predictor, not of the idea. A Laplace fill blurs
across everything, so ANY high-frequency content scores as "unpredictable". But a
real edge is sharp AND perfectly predictable -- it continues, and a dozen other
edges in the same photo look just like it. Only a predictor that can reproduce
sharp-but-regular content can isolate the genuinely random part.

THE FIX -- READ FROM THE NEIGHBOURS
-----------------------------------
FOLDING_UNIVERSAL_READER asks exactly this: "do readers see only their neighbors
and confirm A/B/C" -- and measures that a C residue confirms the boundary it sits
on from its own neighbourhood alone (95-100%), while being unable to see the global
route. That is the LOCAL observer, and it works by comparison with neighbours, not
by smoothing.

So: predict each block by finding the patch elsewhere in the SAME image whose
surrounding ring best matches this block's ring, and copying its centre. The rest
of the image is the model.

    a sharp edge          -> other edges match its ring -> predicted well
    a repeated texture    -> recurs                     -> predicted well
    a mole, a stray hair,
    sensor grain          -> nothing else in the image
                             predicts it                -> predicted BADLY

That is the operational form of "a mark on someone's face is completely random, we
wouldn't be able to predict it at all". Sharpness is decoupled by construction,
which is the whole point.

PREDICTION (sign still fit on data, not asserted)
    real  = high non-local error at the mark scale (an outside entered the image)
    fake  = low  (marks came from the same predictor as the structure, and that
            predictor has a finite, repetitive vocabulary)
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from skimage import color, io, transform
from skimage.util import view_as_windows

WORK_SIDE = 512
FINE, COARSE = 4, 16      # the mark scale and the structure scale
N_TARGETS = 220           # sampled blocks per scale
EXCLUDE_R = 3             # candidates this close (in patch-grid units) are skipped


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


def _nonlocal_error(g, b, rng):
    """Mean error of predicting a b x b centre from the best ring-match elsewhere."""
    p = 3 * b                       # patch = centre block + a ring of width b
    step = max(2, b // 2)
    W = view_as_windows(g, (p, p), step=step)
    gh, gw = W.shape[:2]
    if gh < 8 or gw < 8:
        return np.nan
    W = W.reshape(gh * gw, p, p)

    ring = np.ones((p, p), bool)
    ring[b:2 * b, b:2 * b] = False
    R = W[:, ring]                                  # ring descriptors
    C = W[:, b:2 * b, b:2 * b].reshape(len(W), -1)  # centres

    R = R - R.mean(1, keepdims=True)                # match structure, not exposure
    Rn = R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-9)

    n = len(W)
    idx = rng.choice(n, size=min(N_TARGETS, n), replace=False)
    gy, gx = np.divmod(np.arange(n), gw)

    errs = []
    for i in idx:
        d = 1.0 - Rn[i] @ Rn.T                      # cosine distance on the ring
        near = (np.abs(gy - gy[i]) <= EXCLUDE_R) & (np.abs(gx - gx[i]) <= EXCLUDE_R)
        d[near] = np.inf                            # no self / neighbour copying
        j = int(np.argmin(d))
        if not np.isfinite(d[j]):
            continue
        # remove DC so this is "did the pattern recur", not "did the brightness"
        a = C[i] - C[i].mean()
        bb = C[j] - C[j].mean()
        errs.append(float(np.abs(a - bb).mean()))
    return float(np.median(errs)) if errs else np.nan


def analyse(path, seed=0):
    rng = np.random.default_rng(seed)
    rgb = _load(path)
    g = color.rgb2lab(rgb)[..., 0] / 100.0
    norm = float(g.std()) + 1e-6
    fine = _nonlocal_error(g, FINE, rng) / norm
    coarse = _nonlocal_error(g, COARSE, rng) / norm
    return {"path": path,
            "nonlocal_err_fine": fine,
            "nonlocal_err_coarse": coarse,
            "nonlocal_asymmetry": float(fine / (coarse + 1e-9))}


EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
FEATS = ["nonlocal_err_fine", "nonlocal_err_coarse", "nonlocal_asymmetry"]


def _auc(pos, neg):
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--ai", required=True)
    ap.add_argument("--json", default="nonlocal_metrics.json")
    a = ap.parse_args()

    rows = []
    for folder, label in ((a.real, "real"), (a.ai, "ai")):
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith(EXTS):
                continue
            r = analyse(os.path.join(folder, f))
            r["label"] = label
            rows.append(r)
            print(f"  [{label}] {f[:40]:<40} fine={r['nonlocal_err_fine']:.4f} "
                  f"coarse={r['nonlocal_err_coarse']:.4f} "
                  f"asym={r['nonlocal_asymmetry']:.3f}", flush=True)

    real = [r for r in rows if r["label"] == "real"]
    ai = [r for r in rows if r["label"] == "ai"]
    print(f"\n=== non-local predictability   n_real={len(real)} n_ai={len(ai)} ===")
    print(f"{'feature':<26}{'real':>10}{'ai':>10}{'AUC':>8}{'|d|':>7}")
    for f in FEATS:
        x = np.array([r[f] for r in real]); y = np.array([r[f] for r in ai])
        v = _auc(x, y)
        print(f"{f:<26}{x.mean():>10.4f}{y.mean():>10.4f}{v:>8.3f}{abs(v-0.5):>7.3f}")

    with open(a.json, "w") as fh:
        json.dump({"fine": FINE, "coarse": COARSE, "rows": rows}, fh, indent=2)
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
