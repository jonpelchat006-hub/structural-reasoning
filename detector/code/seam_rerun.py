"""
seam_rerun.py -- the localisation test, on rebuilt masks, with BOTH baselines.

Two changes from the run recorded in FOLDING_WITHIN_IMAGE:

  1. The masks were rebuilt (rebuild_seam.py) with EXIF orientation applied, so
     all 13 pairs align, and were visually verified to land on the edited object.
     The previous masks are not on disk and their fractions differ from these by
     a median factor of ~2, so the old AUCs were computed against a ground truth
     that can no longer be inspected.

  2. Both within-image baselines are reported side by side:
       dev          centre on the plain median of all 36 cells (what was used)
       dev_trimmed  centre re-estimated from the least-deviant cells only
     FOLDING_WITHIN_IMAGE Part III named median contamination as the suspect for
     the anti-correlation with edit size. This is that test.

Control arm unchanged and load-bearing: the identical computation on the
UNTOUCHED original, reading the same cells. A measure that fires there is
reacting to the region, not the edit.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import within_image_observers as W

FEATS = ["noise_dev", "sharp_dev", "spec_dev", "nl_asym_dev"]
G = W.G


def raw_measure(path, seed=0):
    """Everything measure() computes, but returning the RAW per-cell values so
    both baselines can be applied to the same numbers."""
    from image_io import load_rgb
    from scipy import ndimage as ndi
    from skimage import color
    rng = np.random.default_rng(seed)
    g = color.rgb2lab(load_rgb(path))[..., 0] / 100.0
    h, w = g.shape
    nf = W._noise_field(g)
    sharp = ndi.uniform_filter(ndi.laplace(g) ** 2, 24)
    noise = np.full(G * G, np.nan)
    shp = np.full(G * G, np.nan)
    spec = np.full(G * G, np.nan)
    for idx, sy, sx in W._cells(h, w):
        noise[idx] = float(np.median(nf[sy, sx]))
        shp[idx] = float(np.median(sharp[sy, sx]))
        spec[idx] = W._spec_resid(g[sy, sx])
    fine = W._nl_cell(g, 4, rng=rng)
    coarse = W._nl_cell(g, 16, rng=rng)
    return {"noise_dev": noise, "sharp_dev": shp, "spec_dev": spec,
            "nl_asym_dev": fine / (coarse + 1e-9)}


def dev_plain(v):
    v = np.asarray(v, float)
    m = np.nanmedian(v)
    s = np.nanmedian(np.abs(v - m)) + 1e-9
    return np.abs(v - m) / s


def dev_trim(v, drop=0.30, iters=6):
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


BASE = {"median": dev_plain, "trimmed": dev_trim}


def main():
    rows = json.load(open("seam/index.json"))
    res = []
    t0 = time.time()
    for r in rows:
        mask = np.load(f"seam/{r['name']}_mask.npy")
        cov = W.coverage(mask)
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(G * G, bool)
            sel[int(np.argmax(cov))] = True
        if sel.all():
            print(f"  {r['name']} SKIPPED -- edit covers every cell")
            continue
        row = {"name": r["name"], "frac": r["mask_frac"], "n_cells": int(sel.sum())}
        for kind in ("edit", "orig"):
            raw = raw_measure(f"seam/{r['name']}_{kind}.jpg")
            for bname, bfn in BASE.items():
                for f in FEATS:
                    row[f"{kind}.{bname}.{f}"] = W.auc(bfn(raw[f])[sel],
                                                       bfn(raw[f])[~sel])
        res.append(row)
        print(f"  {r['name']} ({100*row['frac']:.2f}%, {row['n_cells']} cells) "
              f"[{time.time()-t0:.0f}s]", flush=True)

    print(f"\n{'='*94}\nWITHIN-IMAGE LOCALISATION, REBUILT MASKS "
          f"({len(res)} pairs, {G}x{G} grid, model-free)\n{'='*94}")
    print(f"{'measure':<14}{'baseline':<10}{'EDITED':>9}{'>chance':>9}"
          f"{'CONTROL':>10}{'>chance':>9}{'edit-control':>14}{'corr w/ size':>14}")
    summary = {}
    sz = np.array([r["frac"] for r in res])
    for f in FEATS:
        for bname in BASE:
            e = np.array([r[f"edit.{bname}.{f}"] for r in res], float)
            c = np.array([r[f"orig.{bname}.{f}"] for r in res], float)
            k = np.isfinite(e) & np.isfinite(c)
            if k.sum() < 3:
                continue
            corr = np.corrcoef(sz[k], e[k])[0, 1]
            summary[f"{f}.{bname}"] = {"edit": float(e[k].mean()),
                                       "control": float(c[k].mean()),
                                       "delta": float(e[k].mean() - c[k].mean()),
                                       "above": int((e[k] > 0.5).sum()),
                                       "n": int(k.sum()), "corr_size": float(corr)}
            print(f"{f:<14}{bname:<10}{e[k].mean():>9.3f}"
                  f"{(e[k]>0.5).sum():>6}/{k.sum():<3}{c[k].mean():>10.3f}"
                  f"{(c[k]>0.5).sum():>6}/{k.sum():<3}"
                  f"{e[k].mean()-c[k].mean():>+14.3f}{corr:>+14.2f}")

    print(f"\n{'-'*94}\nDID THE TRIMMED BASELINE FIX THE SIZE TREND?")
    for f in FEATS:
        a = summary.get(f"{f}.median")
        b = summary.get(f"{f}.trimmed")
        if not a or not b:
            continue
        print(f"  {f:<14} corr(size, AUC)  median {a['corr_size']:+.2f}  ->  "
              f"trimmed {b['corr_size']:+.2f}     "
              f"edit-control  {a['delta']:+.3f} -> {b['delta']:+.3f}")

    print(f"\n{'-'*94}\nPER-IMAGE, spec_dev, sorted by edit size")
    print(f"{'image':<20}{'edit%':>8}{'cells':>7}{'median':>10}{'trimmed':>10}"
          f"{'ctrl med':>10}{'ctrl trim':>11}")
    for r in sorted(res, key=lambda x: x["frac"]):
        print(f"{r['name']:<20}{100*r['frac']:>7.2f}%{r['n_cells']:>7}"
              f"{r.get('edit.median.spec_dev', np.nan):>10.2f}"
              f"{r.get('edit.trimmed.spec_dev', np.nan):>10.2f}"
              f"{r.get('orig.median.spec_dev', np.nan):>10.2f}"
              f"{r.get('orig.trimmed.spec_dev', np.nan):>11.2f}")

    json.dump({"summary": summary, "rows": res},
              open("seam_rerun_results.json", "w"), indent=2, default=str)
    print("\nwrote seam_rerun_results.json")


if __name__ == "__main__":
    main()
