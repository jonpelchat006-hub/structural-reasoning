"""
within_image_observers.py — the model-free axes asked the question they were built for.

They all failed at CLASS SEPARATION ("is this image generated") on the matched
benchmark: nothing above |AUC-0.5| = 0.164 (FOLDING_MATCHED_BENCHMARK).

But that is not the question they were designed around. nonlocal_asymmetry compares
a region against the rest of the SAME image. The reconstruction axis asks whether a
region settles back the way its neighbours do. Those are within-image questions, and
they have never been asked one.

This runs them per-cell on Jonathan's 13 edited/original pairs, where ground truth
is a mask inside a single image, so camera, lens, processing, compression, content
and lighting are identical on both sides of the seam.

FOUR PER-CELL MEASURES, each expressed as DEVIATION FROM THE IMAGE'S OWN MEDIAN --
that framing is the whole point, and it is why these can work here after failing
across images:

  noise_dev    robust sensor-noise level of the cell vs the image's own noise field.
               A real frame has one noise floor; a regenerated patch is denoised and
               carries a different one. The classic forensic signal, and the closest
               thing to "is this region inconsistent with that one".
  sharp_dev    local sharpness vs the image median.
  spec_dev     residual from a 1/f fit on the cell's own spectrum, vs the image
               median. This is the resonance term -- the ONE feature that survived
               the matched benchmark (FOLDING_AXIS_INDEPENDENCE: resid_rms is the
               spectral axis's genuinely independent content).
  nl_asym      non-local predictability: can the REST of the image predict this
               cell's content? Fine scale over coarse. FOLDING_TWO_SIDED_WINDOW's
               measure, restricted to a cell.

Control arm: identical computation on the UNTOUCHED original, reading the same
cells. If a measure flags those cells there too, it is reacting to the region rather
than to the edit -- the same control that showed the committee was doing exactly
that (FOLDING_SEAM_TEST).
"""

from __future__ import annotations

import json
import os

import numpy as np
from scipy import ndimage as ndi
from skimage import color, io
from skimage.util import view_as_windows

G = 6


def _cells(h, w):
    for i in range(G):
        for j in range(G):
            yield i * G + j, slice(i * h // G, (i + 1) * h // G), \
                  slice(j * w // G, (j + 1) * w // G)


def _noise_field(g):
    """Immerkaer-style robust noise estimate, computed densely."""
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], float)
    r = np.abs(ndi.convolve(g, k))
    return ndi.uniform_filter(r, 16)


def _spec_resid(patch):
    """How far this patch's radial power spectrum departs from a 1/f law."""
    p = patch - patch.mean()
    if p.shape[0] < 24 or p.shape[1] < 24 or p.std() < 1e-6:
        return np.nan
    F = np.abs(np.fft.fftshift(np.fft.fft2(p))) ** 2
    h, w = F.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - h / 2, xx - w / 2).astype(int)
    nb = min(h, w) // 2
    prof = np.array([F[r == k].mean() if (r == k).any() else np.nan
                     for k in range(1, nb)])
    m = np.isfinite(prof) & (prof > 0)
    if m.sum() < 8:
        return np.nan
    x = np.log(np.arange(1, nb)[m])
    y = np.log(prof[m])
    a, b = np.polyfit(x, y, 1)
    return float(np.sqrt(np.mean((y - (a * x + b)) ** 2)))


def _nl_cell(gray, b, targets_per_cell=14, rng=None):
    """Per-cell non-local error: does the rest of the image predict this cell?"""
    p = 3 * b
    step = max(3, b)          # coarse sampling; the candidate pool is capped below
    W = view_as_windows(gray, (p, p), step=step)
    gh, gw = W.shape[:2]
    if gh < 8 or gw < 8:
        return np.full(G * G, np.nan)
    Wf = W.reshape(gh * gw, p, p)
    ring = np.ones((p, p), bool)
    ring[b:2 * b, b:2 * b] = False
    R = Wf[:, ring]
    R = R - R.mean(1, keepdims=True)
    Rn = R / (np.linalg.norm(R, axis=1, keepdims=True) + 1e-9)
    C = Wf[:, b:2 * b, b:2 * b].reshape(len(Wf), -1)
    gy, gx = np.divmod(np.arange(len(Wf)), gw)
    py, px = gy * step + p / 2, gx * step + p / 2
    h, w = gray.shape
    out = np.full(G * G, np.nan)
    for idx, sy, sx in _cells(h, w):
        inside = ((py >= sy.start) & (py < sy.stop) &
                  (px >= sx.start) & (px < sx.stop))
        cand = ~inside                      # the REST of the image is the model
        if inside.sum() < 4 or cand.sum() < 40:
            continue
        ii = np.flatnonzero(inside)
        if len(ii) > targets_per_cell:
            ii = rng.choice(ii, targets_per_cell, replace=False)
        cj = np.flatnonzero(cand)
        if len(cj) > 3000:                  # cap the pool; 3000 candidates is plenty
            cj = rng.choice(cj, 3000, replace=False)
        errs = []
        for i in ii:
            d = 1.0 - Rn[i] @ Rn[cj].T
            j = cj[int(np.argmin(d))]
            a_ = C[i] - C[i].mean()
            b_ = C[j] - C[j].mean()
            errs.append(float(np.abs(a_ - b_).mean()))
        if errs:
            out[idx] = float(np.median(errs))
    return out


def measure(path, seed=0):
    rng = np.random.default_rng(seed)
    # WAS: rgb = io.imread(path)[..., :3] -- skimage.io.imread does NOT apply the
    # EXIF Orientation tag, and neither does PIL's Image.open. 7 of the 13 seam
    # pairs have the ORIGINAL stored 4000x2252 with orientation=6 while the EDIT,
    # rewritten by the editing app, is stored 2252x4000 with orientation=1. Read
    # naively those two arrays are not the same shape, so the pixel diff that
    # produces the ground-truth mask is meaningless for more than half the set.
    # load_rgb applies the tag, so both sides of every pair arrive upright and
    # the same shape. See image_io.py.
    from image_io import load_rgb
    rgb = load_rgb(path)
    g = color.rgb2lab(rgb)[..., 0] / 100.0
    h, w = g.shape
    nf = _noise_field(g)
    lap = ndi.laplace(g)
    sharp = ndi.uniform_filter(lap ** 2, 24)

    noise = np.full(G * G, np.nan)
    shp = np.full(G * G, np.nan)
    spec = np.full(G * G, np.nan)
    for idx, sy, sx in _cells(h, w):
        noise[idx] = float(np.median(nf[sy, sx]))
        shp[idx] = float(np.median(sharp[sy, sx]))
        spec[idx] = _spec_resid(g[sy, sx])

    fine = _nl_cell(g, 4, rng=rng)
    coarse = _nl_cell(g, 16, rng=rng)
    nl = fine / (coarse + 1e-9)

    def dev(v):
        m = np.nanmedian(v)
        s = np.nanmedian(np.abs(v - m)) + 1e-9
        return np.abs(v - m) / s          # deviation from the image's OWN field

    def dev_trimmed(v, drop=0.30, iters=6):
        """ROADMAP ITEM 1, NOT YET THE DEFAULT AND NOT YET MEASURED.

        `dev` above centres on the plain median of all 36 cells. When an edit
        covers a large share of the frame the median IS the edited content, so
        the deviation collapses by construction -- which is the named suspect
        for the size trend (spec_dev scores 0.94 on a 0.2% edit and 0.28 on a
        51.6% one). This re-estimates the centre from the least-deviant cells
        only, iteratively, so a large edit stops being its own reference.

        It is blind -- it never looks at the mask -- but note the honest limit:
        at 51.6% coverage the edited cells are the MAJORITY, and no location
        estimator can know which mode is the authentic one from location alone.
        Expect this to fix the mid-size cases and not the largest one. Run it
        against `dev` on the same pairs and report both.
        """
        v = np.asarray(v, float)
        keep = np.isfinite(v)
        m = np.nanmedian(v)
        for _ in range(iters):
            d = np.abs(v - m)
            thr = np.nanquantile(d[keep], 1.0 - drop) if keep.sum() > 4 else np.inf
            sel = keep & (d <= thr)
            if sel.sum() < 4:
                break
            m_new = np.median(v[sel])
            if np.isclose(m_new, m):
                break
            m = m_new
        s = np.median(np.abs(v[keep] - m)) + 1e-9
        return np.abs(v - m) / s

    return {"noise_dev": dev(noise), "sharp_dev": dev(shp),
            "spec_dev": dev(spec), "nl_asym_dev": dev(nl)}


def coverage(mask):
    h, w = mask.shape
    out = np.zeros(G * G)
    for idx, sy, sx in _cells(h, w):
        out[idx] = mask[sy, sx].mean()
    return out


def auc(pos, neg):
    pos = np.asarray([v for v in pos if np.isfinite(v)], float)
    neg = np.asarray([v for v in neg if np.isfinite(v)], float)
    if len(pos) < 1 or len(neg) < 1:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


FEATS = ["noise_dev", "sharp_dev", "spec_dev", "nl_asym_dev"]


def main():
    rows = json.load(open("seam/index.json"))
    res = []
    for r in rows:
        mask = np.load(f"seam/{r['name']}_mask.npy")
        cov = coverage(mask)
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(G * G, bool)
            sel[int(np.argmax(cov))] = True
        if sel.all():
            continue
        row = {"name": r["name"], "frac": r["mask_frac"], "n_cells": int(sel.sum())}
        for kind in ("edit", "orig"):
            m = measure(f"seam/{r['name']}_{kind}.jpg")
            for f in FEATS:
                row[f"{kind}.{f}"] = auc(m[f][sel], m[f][~sel])
        res.append(row)
        print(f"  {r['name']} ({100*r['mask_frac']:.1f}%) done", flush=True)

    print(f"\n{'='*80}\nMODEL-FREE OBSERVERS, WITHIN-IMAGE  "
          f"({len(res)} pairs, {G}x{G} grid)\n{'='*80}")
    print(f"{'measure':<16}{'EDITED':>9}{'>chance':>9}   {'CONTROL':>9}{'>chance':>9}   "
          f"{'edit-control':>13}")
    summary = {}
    for f in FEATS:
        e = [r[f"edit.{f}"] for r in res if np.isfinite(r.get(f"edit.{f}", np.nan))]
        c = [r[f"orig.{f}"] for r in res if np.isfinite(r.get(f"orig.{f}", np.nan))]
        if not e or not c:
            continue
        me, mc = float(np.mean(e)), float(np.mean(c))
        summary[f] = {"edit": me, "control": mc, "delta": me - mc,
                      "edit_above": sum(1 for x in e if x > 0.5), "n": len(e)}
        print(f"{f:<16}{me:>9.3f}{sum(1 for x in e if x>0.5):>6}/{len(e):<3}"
              f"{mc:>12.3f}{sum(1 for x in c if x>0.5):>6}/{len(c):<3}"
              f"{me-mc:>+13.3f}")

    print("\nper-image, best measure:")
    best = max(summary, key=lambda k: summary[k]["delta"]) if summary else None
    if best:
        print(f"{'image':<20}{'edit%':>7}{'EDITED':>9}{'CONTROL':>10}")
        for r in sorted(res, key=lambda x: x["frac"]):
            print(f"{r['name']:<20}{100*r['frac']:>6.1f}%"
                  f"{r.get(f'edit.{best}', float('nan')):>9.2f}"
                  f"{r.get(f'orig.{best}', float('nan')):>10.2f}")
        print(f"\nbest separation: {best}  "
              f"edited {summary[best]['edit']:.3f} vs control "
              f"{summary[best]['control']:.3f}  (delta {summary[best]['delta']:+.3f})")

    # size trend + combination
    import numpy as _np
    sz=_np.array([r["frac"] for r in res])
    for f in FEATS:
        a=_np.array([r.get(f"edit.{f}",_np.nan) for r in res])
        k=_np.isfinite(a)
        if k.sum()>3:
            print(f"  corr(edit size, {f}) = {_np.corrcoef(sz[k],a[k])[0,1]:+.2f}")
    ce=_np.array([r.get("edit.spec_dev",_np.nan) for r in res])
    cn=_np.array([r.get("edit.nl_asym_dev",_np.nan) for r in res])
    co=_np.array([r.get("orig.spec_dev",_np.nan) for r in res])
    cm=_np.array([r.get("orig.nl_asym_dev",_np.nan) for r in res])
    comb_e=_np.nanmean(_np.stack([ce,cn]),0); comb_o=_np.nanmean(_np.stack([co,cm]),0)
    print(f"\nspec_dev + nl_asym_dev averaged:  EDITED {_np.nanmean(comb_e):.3f} "
          f"({int((comb_e>0.5).sum())}/{len(comb_e)})   CONTROL {_np.nanmean(comb_o):.3f} "
          f"({int((comb_o>0.5).sum())}/{len(comb_o)})")
    json.dump({"summary": summary, "rows": res},
              open("within_image_results.json", "w"), indent=2, default=str)
    print("\nwrote within_image_results.json")


if __name__ == "__main__":
    main()
