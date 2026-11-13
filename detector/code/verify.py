"""
verify.py -- prove the instrument works before believing what it says.

Three checks, in the order that matters:

  1. IS MY AUC CORRECT?      cross-check against sklearn.roc_auc_score on random
                             data, and on a known-perfect and known-chance case.
  2. IS THE PIPELINE ALIVE?  positive control. Feed it a difference it MUST
                             find -- each real photo against a blurred copy of
                             itself. If the sharpness features cannot see that,
                             the null result is a broken instrument, not data.
  3. IS THE CONTROL REALLY   bootstrap CI on target and on the strongest control,
     ABOVE THE TARGET?       plus a permutation test on the difference. At n~20
                             per group the honest claim may only be "control is
                             not below target", and that still kills the feature.
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mixedness_observer as mx
import spectral_observer as sp

U = "/mnt/user-data/uploads/Vesica AI/AI Detector"
SQ, Q = 448, 85
rng = np.random.default_rng(7)


def auc(pos, neg):
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


# ---------------------------------------------------------------- 1. AUC check
print("=" * 78)
print("CHECK 1 -- is the AUC implementation correct?")
print("=" * 78)
try:
    from sklearn.metrics import roc_auc_score
    worst = 0.0
    for trial in range(300):
        n1, n2 = rng.integers(3, 40), rng.integers(3, 40)
        a, b = rng.normal(rng.normal(0, 1), 1, n1), rng.normal(0, 1, n2)
        mine = auc(a, b)
        theirs = roc_auc_score([1] * n1 + [0] * n2, np.concatenate([a, b]))
        worst = max(worst, abs(mine - theirs))
    print(f"  vs sklearn.roc_auc_score over 300 random trials: max abs diff {worst:.2e}")
    print(f"  {'PASS' if worst < 1e-9 else 'FAIL'}")
except ImportError:
    print("  sklearn unavailable -- falling back to analytic cases")
print(f"  perfect separation   auc([5,6,7],[1,2,3]) = {auc([5,6,7],[1,2,3]):.3f}  (expect 1.000)")
print(f"  perfect, inverted    auc([1,2,3],[5,6,7]) = {auc([1,2,3],[5,6,7]):.3f}  (expect 0.000)")
print(f"  identical groups     auc([1,2,3],[1,2,3]) = {auc([1,2,3],[1,2,3]):.3f}  (expect 0.500)")
big = [auc(rng.normal(0, 1, 4000), rng.normal(0, 1, 4000)) for _ in range(20)]
print(f"  chance, n=4000       mean {np.mean(big):.4f} +/- {np.std(big):.4f}  (expect 0.500)")


# ---------------------------------------------------------------- prep/feats
def prep_pil(im):
    im = im.convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    im = im.resize((SQ, SQ), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=Q)
    buf.seek(0)
    return Image.open(buf)


def feats_pil(im, tmp="_v.jpg"):
    im.save(tmp, "JPEG", quality=Q)
    f = {}
    for k, v in sp.features(tmp).items():
        if isinstance(v, (int, float)):
            f["spectral." + k] = float(v)
    for k, v in mx.features(tmp).items():
        if isinstance(v, (int, float)):
            f["mixed." + k] = float(v)
    return f


# ---------------------------------------------------------------- 2. positive control
print("\n" + "=" * 78)
print("CHECK 2 -- positive control: can the features see a difference they MUST see?")
print("=" * 78)
his = sorted(glob.glob(f"{U}/real photos/*"))
sharp, blur = [], []
for p in his:
    im = prep_pil(ImageOps.exif_transpose(Image.open(p)))
    sharp.append(feats_pil(im))
    blur.append(feats_pil(im.filter(ImageFilter.GaussianBlur(1.2))))
keys = sorted(sharp[0])
print(f"  {len(his)} real photos, each vs a Gaussian-blurred (sigma 1.2) copy of ITSELF")
print(f"  {'feature':<26}{'|AUC-0.5|':>11}")
alive = 0
for k in keys:
    a = abs(auc([r[k] for r in sharp], [r[k] for r in blur]) - 0.5)
    if a > 0.40:
        alive += 1
    print(f"  {k:<26}{a:>11.3f}{'   <-- responds' if a > 0.40 else ''}")
print(f"  --> {alive}/{len(keys)} features respond strongly. "
      f"{'PIPELINE IS ALIVE' if alive >= 3 else 'PIPELINE MAY BE BROKEN'}")


# ---------------------------------------------------------------- 3. CIs
print("\n" + "=" * 78)
print("CHECK 3 -- is the control genuinely at or above the target? (bootstrap)")
print("=" * 78)
tab = json.load(open("control_arms.json"))
T = "TARGET    his real vs his AI"
C1 = "CONTROL1  web portrait vs web landscape (both real)"


def load(tag, folder):
    out = []
    for p in sorted(glob.glob(f"{U}/{folder}/*")):
        out.append(feats_pil(prep_pil(ImageOps.exif_transpose(Image.open(p)))))
    return out


G = {"his_real": load("his_real", "real photos"),
     "his_ai": load("his_ai", "ai photos"),
     "web_port": load("web_port", "more photos/real portrait"),
     "web_land": load("web_land", "more photos/real landscape")}


def boot(a, b, k, n=4000):
    A = np.array([r[k] for r in a], float)
    B = np.array([r[k] for r in b], float)
    out = np.empty(n)
    for i in range(n):
        out[i] = abs(auc(rng.choice(A, len(A)), rng.choice(B, len(B))) - 0.5)
    return out


print(f"  {'feature':<24}{'TARGET (95% CI)':>26}{'CTRL1 both-real (95% CI)':>28}"
      f"{'P(ctrl>target)':>16}")
for k in ("spectral.slope", "spectral.spec_entropy", "spectral.hf_frac",
          "mixed.blur_ratio", "mixed.lap_var"):
    bt, bc = boot(G["his_real"], G["his_ai"], k), boot(G["web_port"], G["web_land"], k)
    pt = np.percentile(bt, [2.5, 97.5])
    pc = np.percentile(bc, [2.5, 97.5])
    print(f"  {k:<24}{f'{bt.mean():.3f} [{pt[0]:.3f},{pt[1]:.3f}]':>26}"
          f"{f'{bc.mean():.3f} [{pc[0]:.3f},{pc[1]:.3f}]':>28}"
          f"{np.mean(bc > bt):>16.3f}")
print("\n  P(ctrl>target) near 1.0 = the feature separates two real populations MORE")
print("  strongly than it separates real from AI. Anything above ~0.5 already means")
print("  the target number cannot be attributed to provenance.")
