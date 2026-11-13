"""
balance_observer.py — matter / antimatter / void, as a conservation law you can check.

JONATHAN'S PROPOSAL
-------------------
"pixels would be the matter, resonance the antimatter and we already have the void
lines. those had to be in balance... in a real photo we would know how much blur
there should be but that could also show up as resonance."

WHY THIS IS MORE THAN A NAMING
------------------------------
The labels are a naming. The CONSTRAINT they imply is not: the trinity says these
three are not free parameters, and that turns out to be exactly true in optics.

  A blur of scale sigma convolves the image spatially AND multiplies its spectrum by
  a Gaussian of width 1/sigma. The boundary thickness -- the void line width --
  DETERMINES the high-frequency content. One physical process writes both.

So the same quantity is readable two ways:

  MATTER     (spatial)  how sharp does this region look in the pixel domain?
  ANTIMATTER (spectral) how fast does its power spectrum fall off?
  VOID       (sigma)    the boundary width that has to reconcile them.

In a real photograph one lens and one sensor produced every region, so all cells lie
on ONE spatial-vs-spectral line. A synthesised patch is smooth because a prior made
it smooth, not because anything was out of focus -- so it can sit off that line.

  balance_dev = residual from the image's OWN spatial-vs-spectral fit.

This is a RECONCILIATION, not a magnitude -- the class of measure that has kept
landing off the crowded axis all session (FOLDING_ENVIRONMENT_BRIDGE: the bridge
measure was off-frame at 0.21/0.27 while the lighting magnitude was on it at 0.92).
Every magnitude measure of blur lands on direction i (FOLDING_OBSERVER_FRAME).
The *disagreement between two readings of blur* should not.

Control arm as always: identical computation on the untouched original.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import ndimage as ndi
from skimage import color, io

G = 6


def _cells(h, w):
    for i in range(G):
        for j in range(G):
            yield i * G + j, slice(i * h // G, (i + 1) * h // G), \
                  slice(j * w // G, (j + 1) * w // G)


def _spectral_sigma(patch):
    """Fit log P(f) = a - alpha*log f - (2 pi sigma)^2 f^2 and return sigma.

    The alpha term is the natural-scene 1/f law (content). The quadratic term is the
    blur kernel (optics). Separating them is the point: alpha is what collided with
    everything else all session; the quadratic term is the void-line width.
    """
    p = patch - patch.mean()
    if min(p.shape) < 24 or p.std() < 1e-6:
        return np.nan, np.nan
    F = np.abs(np.fft.fftshift(np.fft.fft2(p))) ** 2
    h, w = F.shape
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.hypot(yy - h / 2, xx - w / 2)
    nb = min(h, w) // 2
    ri = rr.astype(int)
    prof = np.array([F[ri == k].mean() if (ri == k).any() else np.nan
                     for k in range(1, nb)])
    f = np.arange(1, nb) / float(min(h, w))          # cycles per pixel
    m = np.isfinite(prof) & (prof > 0)
    if m.sum() < 10:
        return np.nan, np.nan
    X = np.stack([np.ones(m.sum()), -np.log(f[m]), -(f[m] ** 2)], 1)
    try:
        coef, *_ = np.linalg.lstsq(X, np.log(prof[m]), rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    alpha, q = coef[1], coef[2]
    sigma = float(np.sqrt(max(q, 0.0)) / (2 * np.pi)) if q > 0 else 0.0
    return sigma, float(alpha)


def _spatial_sharp(patch):
    """Matter side: normalised gradient energy in the pixel domain."""
    if patch.std() < 1e-6:
        return np.nan
    gy, gx = np.gradient(patch)
    return float(np.sqrt((gy ** 2 + gx ** 2).mean()) / (patch.std() + 1e-9))


def measure(path):
    rgb = io.imread(path)[..., :3].astype(np.float64) / 255.0
    g = color.rgb2lab(rgb)[..., 0] / 100.0
    h, w = g.shape
    sig = np.full(G * G, np.nan)      # void: boundary width from the spectrum
    alp = np.full(G * G, np.nan)      # antimatter: the 1/f content term
    shp = np.full(G * G, np.nan)      # matter: spatial sharpness
    for idx, sy, sx in _cells(h, w):
        c = g[sy, sx]
        s, a = _spectral_sigma(c)
        sig[idx], alp[idx] = s, a
        shp[idx] = _spatial_sharp(c)

    # THE BALANCE: within this one image, one lens and one sensor made every cell,
    # so spatial sharpness must be a single function of the spectral blur width.
    # Fit that line on the image's own cells; the residual is the imbalance.
    k = np.isfinite(sig) & np.isfinite(shp)
    bal = np.full(G * G, np.nan)
    if k.sum() >= 12:
        X = np.stack([np.ones(k.sum()), sig[k], alp[k]], 1)
        try:
            coef, *_ = np.linalg.lstsq(X, shp[k], rcond=None)
            pred = X @ coef
            r = shp[k] - pred
            s = np.median(np.abs(r - np.median(r))) + 1e-9
            bal[k] = np.abs(r - np.median(r)) / s
        except np.linalg.LinAlgError:
            pass

    def dev(v):
        m = np.nanmedian(v)
        s = np.nanmedian(np.abs(v - m)) + 1e-9
        return np.abs(v - m) / s

    return {"balance_dev": bal,          # the trinity residual
            "void_sigma_dev": dev(sig),  # void line width alone
            "matter_dev": dev(shp),      # spatial sharpness alone
            "antimatter_dev": dev(alp)}  # 1/f slope alone


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


FEATS = ["balance_dev", "void_sigma_dev", "matter_dev", "antimatter_dev"]


def main():
    rows = json.load(open("seam/index.json"))
    res = []
    for r in rows:
        cov = coverage(np.load(f"seam/{r['name']}_mask.npy"))
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(G * G, bool)
            sel[int(np.argmax(cov))] = True
        if sel.all():
            continue
        row = {"name": r["name"], "frac": r["mask_frac"]}
        for kind in ("edit", "orig"):
            m = measure(f"seam/{r['name']}_{kind}.jpg")
            for f in FEATS:
                row[f"{kind}.{f}"] = auc(m[f][sel], m[f][~sel])
        res.append(row)
        print(f"  {r['name']} done", flush=True)

    print(f"\n{'='*78}\nMATTER / ANTIMATTER / VOID BALANCE  ({len(res)} pairs)\n{'='*78}")
    print(f"{'measure':<18}{'EDITED':>9}{'>chance':>9}{'CONTROL':>10}{'>chance':>9}{'delta':>9}")
    summ = {}
    for f in FEATS:
        e = [r[f"edit.{f}"] for r in res if np.isfinite(r.get(f"edit.{f}", np.nan))]
        c = [r[f"orig.{f}"] for r in res if np.isfinite(r.get(f"orig.{f}", np.nan))]
        if not e or not c:
            continue
        summ[f] = {"edit": float(np.mean(e)), "control": float(np.mean(c)),
                   "delta": float(np.mean(e) - np.mean(c)), "n": len(e)}
        print(f"{f:<18}{np.mean(e):>9.3f}{sum(1 for x in e if x>0.5):>6}/{len(e):<3}"
              f"{np.mean(c):>10.3f}{sum(1 for x in c if x>0.5):>6}/{len(c):<3}"
              f"{np.mean(e)-np.mean(c):>+9.3f}")
    sz = np.array([r["frac"] for r in res])
    for f in FEATS:
        a = np.array([r.get(f"edit.{f}", np.nan) for r in res])
        k = np.isfinite(a)
        if k.sum() > 3:
            print(f"  corr(edit size, {f}) = {np.corrcoef(sz[k], a[k])[0,1]:+.2f}")
    json.dump({"summary": summ, "rows": res},
              open("balance_results.json", "w"), indent=2, default=str)
    print("\nwrote balance_results.json")


if __name__ == "__main__":
    main()
