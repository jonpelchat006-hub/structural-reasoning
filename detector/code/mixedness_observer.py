#!/usr/bin/env python3
"""
Mixedness / blur observer (Jonathan's C-field idea, image side).
================================================================
Model-free, local boundary-structure route — orthogonal to the semantic vision
routes and to the global spectral route. Measures how the image blends region to
region (the "mixedness" / blur field) and whether that blur is physically
structured (real: depth-of-field, coherent) or anomalous (AI: melted seams, flat
soft, composited halos).

Features per image:
  lap_var       global sharpness (variance of Laplacian)
  sharp_cv      coeff. of variation of the LOCAL sharpness map = depth-of-field
                structure (real photos: sharp subject + blurred bg -> high CV)
  blur_ratio    |grad(blur(x))| / |grad(x)|  (already-soft images -> near 1; AI melt higher)
  grad_kurt     kurtosis of gradient magnitude (natural images heavy-tailed)
  mix_mean      mean color-assignment ambiguity (the mixedness field)
  mix_frac      fraction of strongly-mixed pixels (spread of the mixed zones)

Reports AUC per feature on the art set and the photo set (label-free
discrimination). No API cost.
"""
import glob
import numpy as np
from PIL import Image
from scipy import ndimage


def auc(scores, labels):
    reals = [s for s, y in zip(scores, labels) if y == 1]
    ais = [s for s, y in zip(scores, labels) if y == 0]
    w = sum(1 for r in reals for a in ais if r > a) + 0.5 * sum(1 for r in reals for a in ais if r == a)
    return w / (len(reals) * len(ais))

S = 320   # analysis size


def _kmeans_dists(X, k=6, iters=8):
    idx = np.linspace(0, len(X) - 1, k).astype(int)
    C = X[idx].astype(float)
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
        a = d.argmin(1)
        for j in range(k):
            m = a == j
            if m.any():
                C[j] = X[m].mean(0)
    return ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)


def features(path):
    im = Image.open(path).convert("RGB").resize((S, S))
    rgb = np.asarray(im, dtype=np.float64)
    g = rgb.mean(2)
    g = (g - g.mean()) / (g.std() + 1e-6)

    # sharpness
    lap = ndimage.laplace(g)
    lap_var = float(lap.var())
    local_sharp = ndimage.uniform_filter(lap ** 2, size=20)
    sharp_cv = float(local_sharp.std() / (local_sharp.mean() + 1e-9))   # DoF structure

    # edge melt: how much a mild blur changes the gradient
    gx = ndimage.sobel(g, axis=0); gy = ndimage.sobel(g, axis=1)
    grad = np.hypot(gx, gy)
    gb = ndimage.gaussian_filter(g, 2.0)
    gbx = ndimage.sobel(gb, axis=0); gby = ndimage.sobel(gb, axis=1)
    gradb = np.hypot(gbx, gby)
    blur_ratio = float(gradb.mean() / (grad.mean() + 1e-9))             # melt -> higher

    gm = grad.ravel()
    gm = (gm - gm.mean()) / (gm.std() + 1e-9)
    grad_kurt = float((gm ** 4).mean())                                 # heavy tail

    # color mixedness field (down-sample for k-means)
    small = np.asarray(im.resize((96, 96)), dtype=np.float64).reshape(-1, 3)
    d = _kmeans_dists(small, k=6, iters=8)
    ds = np.sort(d, axis=1)
    gap = (ds[:, 1] - ds[:, 0]) / (ds[:, 0] + 1e-6)     # small gap = ambiguous
    ambiguity = 1.0 / (1.0 + gap)
    mix_mean = float(ambiguity.mean())
    mix_frac = float((ambiguity > 0.6).mean())

    return {"lap_var": lap_var, "sharp_cv": sharp_cv, "blur_ratio": blur_ratio,
            "grad_kurt": grad_kurt, "mix_mean": mix_mean, "mix_frac": mix_frac}


def run(name, real_glob, ai_glob):
    reals = sorted(glob.glob(real_glob)); ais = sorted(glob.glob(ai_glob))
    rows = [features(p) for p in reals] + [features(p) for p in ais]
    labels = [1] * len(reals) + [0] * len(ais)
    print(f"\n=== {name}  ({len(reals)} real / {len(ais)} ai) ===")
    best = None
    for k in rows[0]:
        a = auc([r[k] for r in rows], labels)
        sep = abs(a - 0.5)
        print(f"  {k:<12} AUC {a:.3f}  sep {sep:.3f}")
        if best is None or sep > best[1]:
            best = (k, sep, a)
    print(f"  best: {best[0]} (AUC {best[2]:.3f})")
    return rows, labels


if __name__ == "__main__":
    run("ART", "/home/claude/bench/real/*.jpg", "/home/claude/bench/ai/*.jpg")
    run("PHOTO", "/home/claude/bench_photo/real/*.jpg", "/home/claude/bench_photo/ai/*.jpg")
