"""
predictability_observer.py — the two-sided window (Jonathan's predictability asymmetry).

THE IDEA
--------
"real things are more predictable aren't they? the shape of a person should settle
back into a person, but the prediction of a person would settle back into the
prediction. and a mark on someones face is completely random, we wouldn't be able
to predict it at all, so things should drift more from things like that."

Decomposed, that is a claim about TWO SCALES AT ONCE:

    real  =  predictable at the STRUCTURE scale  +  UNpredictable at the MARK scale
    fake  =  predictable at BOTH

A photograph's global layout is heavily constrained (a face is a face), but the
exact placement of a moley freckle is irreducibly random -- it is information that
entered from outside the image-generating process (optics, skin, dust, a sensor).
A generated image has no such outside: its marks came from the same predictor that
made its structure, so they are conditionally predictable from context in a way a
real mark is not.

WHY THIS IS THE MEASURE THAT MIGHT SURVIVE
------------------------------------------
Every sub-measure in FOLDING_RECONSTRUCTION that carried signal turned out to be
redundant with the blur axis (|r| = 0.79-0.81), because they were all ABSOLUTE
magnitudes and blur moves every absolute magnitude at once. This measure is a
RATIO of two reads of the same image. A common-mode blur/compression term appears
in numerator and denominator and cancels. That is the specific reason to expect it
to clear the independence bar where the others did not.

THE FRAMEWORK ALREADY MEASURED BOTH HALVES, FROM OPPOSITE ENDS
--------------------------------------------------------------
  FOLDING_OBSERVERS (honest ceiling): the committee "gets the big true things every
    time and the tiny things never" -- the global observer resolves coarse
    invariants and degrades on fine detail.
  FOLDING_UNIVERSAL_READER / FOLDING_WINDOW_SEAM: a C residue confirms the boundary
    it sits on (95-100%) but "cannot know where the whole C line goes from its own
    neighborhood" -- the local observer resolves its own mark and cannot see the whole.

Two observers on the two sides of the window, each blind to what the other resolves.
FOLDING_UNIVERSAL_READER names the architecture literally: "two cones tip-to-tip...
outside cone catches the point; inside cone sends it on."

THE MEASUREMENT
---------------
Mask a checkerboard of b x b blocks and reconstruct them from their surrounding
context by harmonic (Laplace) diffusion -- which IS our fill engine, the diffusion-
curves fill of FOLDING_VOID_LINE_DRAW Part III, run as a predictor. Do it at
b = 2, 4, 8, 16, 32 and record the normalised error E(b).

    E(b) small  ->  context at scale b predicts the content
    E(b) large  ->  the content carries information context cannot supply

  predictability_asymmetry = E(fine) / E(coarse)
      the headline. High = fine detail is much less predictable than coarse
      structure = an outside entered the image. Predicted higher in REAL.

  predict_slope = d log E / d log b
      how fast predictability degrades with scale -- the shape of the curve, not
      just its endpoints.

Sign is NOT hard-coded here either. Same rule as the reconstruction axis: emit raw,
fit the sign on data.
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from skimage import color, io, transform

WORK_SIDE = 512
SCALES = (2, 4, 8, 16, 32)


def _checkerboard(shape, b):
    """Mask alternate b x b blocks, so every masked block is fully surrounded by
    context. This is what makes it a prediction rather than an extrapolation."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return ((yy // b) + (xx // b)) % 2 == 1


def _laplace_inpaint(img, mask, iters):
    """Predict the masked pixels from their boundary by harmonic diffusion.

    This is deliberately the SAME operator as the fill engine -- matter bleeding in
    from the void lines (FOLDING_VOID_LINE_DRAW Part III / diffusion curves). We are
    asking how well our own generative fill can guess what was removed.
    """
    out = img.copy()
    seed = img[~mask].mean(0) if img.ndim == 3 else img[~mask].mean()
    out[mask] = seed
    for _ in range(iters):
        sm = 0.25 * (np.roll(out, 1, 0) + np.roll(out, -1, 0)
                     + np.roll(out, 1, 1) + np.roll(out, -1, 1))
        out[mask] = sm[mask]
    return out


def _load(path, jpeg_q=None):
    img = io.imread(path)
    if img.ndim == 2:
        img = np.stack([img] * 3, -1)
    img = img[..., :3].astype(np.float64) / 255.0
    h, w = img.shape[:2]
    sc = WORK_SIDE / float(max(h, w))
    if sc < 1.0:
        img = transform.resize(img, (int(round(h * sc)), int(round(w * sc))),
                               anti_aliasing=True)
    if jpeg_q is not None:
        import io as _io
        from PIL import Image
        buf = _io.BytesIO()
        Image.fromarray((img * 255).astype(np.uint8)).save(buf, "JPEG", quality=jpeg_q)
        buf.seek(0)
        img = np.asarray(Image.open(buf), dtype=np.float64) / 255.0
    return img


def analyse(path, jpeg_q=None):
    rgb = _load(path, jpeg_q)
    lab_l = color.rgb2lab(rgb)[..., 0] / 100.0     # luminance; chroma adds little here
    norm = float(lab_l.std()) + 1e-6               # the image's own contrast
    h, w = lab_l.shape

    curve = {}
    for b in SCALES:
        m = _checkerboard((h, w), b)
        # harmonic fill needs ~ b^2 sweeps to reach a block centre; cap for cost
        it = int(min(600, max(40, 8 * b * b / 4)))
        pred = _laplace_inpaint(lab_l, m, it)
        curve[b] = float(np.median(np.abs(pred[m] - lab_l[m])) / norm)

    fine = curve[SCALES[0]]
    coarse = curve[SCALES[-1]]
    logb = np.log(np.array(SCALES, float))
    loge = np.log(np.array([curve[b] for b in SCALES], float) + 1e-9)
    slope = float(np.polyfit(logb, loge, 1)[0])

    return {
        "path": path,
        "predict_err_fine": fine,
        "predict_err_coarse": coarse,
        "predictability_asymmetry": float(fine / (coarse + 1e-9)),
        "predict_slope": slope,
        "curve": {str(b): round(curve[b], 5) for b in SCALES},
    }


EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
FEATS = ["predictability_asymmetry", "predict_slope",
         "predict_err_fine", "predict_err_coarse"]


def _auc(pos, neg):
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--ai", required=True)
    ap.add_argument("--jpeg", type=int, default=None)
    ap.add_argument("--json", default="predictability_metrics.json")
    a = ap.parse_args()

    rows = []
    for folder, label in ((a.real, "real"), (a.ai, "ai")):
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith(EXTS):
                continue
            r = analyse(os.path.join(folder, f), a.jpeg)
            r["label"] = label
            rows.append(r)
            print(f"  [{label}] {f[:40]:<40} "
                  f"asym={r['predictability_asymmetry']:.3f} "
                  f"slope={r['predict_slope']:+.3f} "
                  f"fine={r['predict_err_fine']:.4f} "
                  f"coarse={r['predict_err_coarse']:.4f}", flush=True)

    real = [r for r in rows if r["label"] == "real"]
    ai = [r for r in rows if r["label"] == "ai"]
    print(f"\n=== predictability asymmetry   n_real={len(real)} n_ai={len(ai)} ===")
    print(f"{'feature':<28}{'real':>10}{'ai':>10}{'AUC':>8}{'|d|':>7}")
    for f in FEATS:
        x = np.array([r[f] for r in real]); y = np.array([r[f] for r in ai])
        v = _auc(x, y)
        print(f"{f:<28}{x.mean():>10.4f}{y.mean():>10.4f}{v:>8.3f}{abs(v-0.5):>7.3f}")

    with open(a.json, "w") as fh:
        json.dump({"scales": list(SCALES), "rows": rows}, fh, indent=2)
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
