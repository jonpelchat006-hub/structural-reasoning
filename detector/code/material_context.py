"""
material_context.py -- "knowing what we are looking at and what each piece should be doing".

THE GAP JONATHAN NAMED
----------------------
Every within-image measure in this project compares a cell against the WHOLE
IMAGE's baseline. That is a category error, and it is probably why they are weak.
A frame of sky, skin, foliage and asphalt has four different correct answers for
"how much high-frequency energy should be here", and the image median is an
average over all four -- a number that describes none of them. Sky is legitimately
smooth. Foliage is legitimately dense. Comparing a sky cell against a
sky-plus-foliage average tells you the cell is sky, not that it is fake.

So: **compare each region against its own material, not against the frame.**
Segment the image into material-like regions, then ask of each cell only whether
it is consistent with the OTHER cells made of the same stuff. Sky against sky.
Skin against skin.

This is the free proxy for the semantic context layer. It does not know that a
region IS sky -- it knows only that a set of cells cluster together in colour and
texture. A real material layer needs the vision model to name the region and
supply its expectation (skin has pores and subsurface scatter; sky has a smooth
gradient plus sensor grain; text has hard edges). That version is Channel-paid.
This one is $0 and tests whether the IDEA carries signal before anything is spent.

WHY IT COULD WORK WHERE THE GLOBAL BASELINE FAILED
--------------------------------------------------
Generative fill regenerates a patch and blends it into its surroundings. Against
the whole frame it is unremarkable -- it was built to be. Against the specific
material it replaced, it is a member of that material that behaves slightly
differently from every other member. The comparison is strictly harder to fake
because the reference set is narrower and is drawn from the same image.

It also directly attacks the failure mode measured in seam_rerun: every measure
anti-correlates with edit size. Under a material baseline, a large edit that
covers half the sky still has the rest of the sky to be compared against, and it
does not contaminate the foliage baseline at all.

PRE-REGISTERED, before running
------------------------------
  1. If the material framing is right, `spec_dev` under a material baseline
     beats `spec_dev` under the trimmed global baseline (0.582 edited / 0.428
     control on the rebuilt masks).
  2. The size anti-correlation should weaken (global trimmed: -0.58).
  3. The control arm on untouched originals must stay at or below chance. If it
     rises with the edited arm, the segmentation is just finding regions again
     and this is the committee's failure repeated.
  4. Risk: an edit large enough to dominate its own material cluster reproduces
     the contamination problem one level down. Report cluster occupancy so it is
     visible when that happens.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

G = 6
K = 4          # material clusters
MIN_MEMBERS = 4


def cell_descriptors(path):
    """A small colour+texture descriptor per cell, used only for clustering.

    Deliberately crude and deliberately NOT the measures being tested: cluster
    on what the material looks like, then score with an independent quantity.
    Using the same statistic for both would let the clustering absorb the signal.
    """
    from skimage import color
    from image_io import load_rgb
    rgb = load_rgb(path)
    lab = color.rgb2lab(rgb)
    L = lab[..., 0] / 100.0
    h, w = L.shape
    tex = ndi.uniform_filter(ndi.laplace(L) ** 2, 24)
    desc = []
    for i in range(G):
        for j in range(G):
            sy = slice(i * h // G, (i + 1) * h // G)
            sx = slice(j * w // G, (j + 1) * w // G)
            desc.append([
                float(np.median(lab[sy, sx, 0])) / 100.0,
                float(np.median(lab[sy, sx, 1])) / 128.0,
                float(np.median(lab[sy, sx, 2])) / 128.0,
                float(np.log1p(np.median(tex[sy, sx]) * 1e4)) / 10.0,
            ])
    return np.asarray(desc, float)


def kmeans(X, k, iters=40, seed=0):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)].copy()
    lab = np.zeros(len(X), int)
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        new = d.argmin(1)
        if (new == lab).all():
            break
        lab = new
        for c in range(k):
            if (lab == c).any():
                C[c] = X[lab == c].mean(0)
    return lab


def material_labels(path, k=K):
    return kmeans(cell_descriptors(path), k)


def dev_material(v, labels, drop=0.30):
    """Deviation of each cell from ITS OWN material's trimmed baseline.

    Clusters too small to form a reference fall back to the global trimmed
    baseline rather than being dropped, so every cell still gets a score and the
    comparison against the global-baseline run stays like-for-like.
    """
    v = np.asarray(v, float)
    out = np.full(len(v), np.nan)

    def trimmed_centre(x):
        m = np.nanmedian(x)
        for _ in range(6):
            d = np.abs(x - m)
            thr = np.nanquantile(d, 1.0 - drop)
            sel = d <= thr
            if sel.sum() < 3:
                break
            mn = np.median(x[sel])
            if np.isclose(mn, m):
                break
            m = mn
        return m, np.median(np.abs(x - m)) + 1e-9

    gfin = np.isfinite(v)
    gm, gs = trimmed_centre(v[gfin]) if gfin.sum() >= 4 else (np.nan, 1.0)
    for c in np.unique(labels):
        idx = np.flatnonzero((labels == c) & gfin)
        if len(idx) >= MIN_MEMBERS:
            m, s = trimmed_centre(v[idx])
        else:
            m, s = gm, gs
        out[idx] = np.abs(v[idx] - m) / s
    miss = ~gfin
    out[miss] = np.nan
    return out


def occupancy(labels):
    """Cluster sizes, so the 'edit dominates its own material' failure is visible."""
    u, c = np.unique(labels, return_counts=True)
    return {int(a): int(b) for a, b in zip(u, c)}
