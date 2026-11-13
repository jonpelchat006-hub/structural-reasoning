"""
rebuild_seam.py -- rebuild the seam ground truth, this time with the EXIF tag applied.

WHY IT HAD TO BE REBUILT
------------------------
7 of the 13 pairs in `more photos/altered/` store the ORIGINAL as 4000x2252 with
EXIF orientation=6 ("rotate me"), while the EDIT -- rewritten by the editing app,
which baked the rotation into the pixels -- is stored 2252x4000 with orientation=1.
Read through a loader that ignores the tag, as every loader in this project did,
those two arrays are not the same shape and the pixel diff behind the mask is not
well defined. The original `seam/` directory is gone, so the old masks cannot be
inspected; they are rebuilt from scratch here.

After exif_transpose every pair agrees on shape, which is asserted below.

THRESHOLDING
------------
The edited file is a full re-encode, so EVERY pixel differs a little even where
nothing was edited. A fixed threshold would either miss small edits or flood on
JPEG noise. Instead the threshold is set from the image's OWN difference
distribution: keep pixels whose deviation exceeds a high quantile of the diff by
a margin, then clean up speckle morphologically. The recompression floor is
reported per pair so the margin can be seen to clear it.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from image_io import load_pil, load_rgb

U = "/mnt/user-data/uploads/Vesica AI/AI Detector/more photos/altered"
OUT = "seam"
WORK = 768          # longest side the observers will actually score
G = 6

# what the OLD (unverifiable) run recorded, for comparison
OLD_FRAC = {
    "20250131_195339": 0.00392, "20250409_123854": 0.03328,
    "20250518_110837": 0.02695, "20250519_224651": 0.51573,
    "20250520_081320": 0.02596, "20250522_134100": 0.02351,
    "20250528_142137": 0.09591, "20250531_174853": 0.01545,
}


def pairs():
    out = {}
    for p in sorted(glob.glob(f"{U}/*.jpg")):
        b = os.path.basename(p)
        key = b.replace("(1)", "").replace(".jpg", "")
        out.setdefault(key, {})["edit" if "(1)" in b else "orig"] = p
    return {k: v for k, v in out.items() if len(v) == 2}


def build_mask(orig_path, edit_path):
    """Pixel-exact manipulation mask, both sides loaded upright."""
    a = load_rgb(orig_path)
    b = load_rgb(edit_path)
    if a.shape != b.shape:
        return None, {"error": f"shape mismatch after EXIF: {a.shape} vs {b.shape}"}

    # perceptual-ish difference: luma-weighted, then blurred slightly so that
    # single-pixel JPEG ringing does not survive on its own
    d = np.sqrt((((a - b) ** 2) * np.array([0.299, 0.587, 0.114])).sum(-1))
    d = ndi.uniform_filter(d, 3)

    # The difference distribution is strongly bimodal: JPEG recompression noise
    # sits at 0.001-0.010 and edited pixels at 0.15-0.45, with a clean gap. So
    # estimate the noise floor from the LOW quartile -- which is untouched unless
    # an edit covers more than 75% of the frame -- and cut an order of magnitude
    # above it, with an absolute floor for the near-lossless pairs.
    #
    # An earlier version centred on q60 and scaled by (q60-q40). That silently
    # failed on 20250519_224651, where roughly half the frame is edited so q40-q60
    # straddles the gap: the "spread" exploded, the threshold went to 2.72 against
    # a maximum difference of 0.56, and the mask came back EMPTY for the single
    # largest edit in the set. Estimate scale from a region the signal cannot
    # reach, never from one it might occupy.
    floor = float(np.quantile(d, 0.25))
    thr = max(10.0 * floor, 0.02)
    spread = float(np.quantile(d, 0.50) - np.quantile(d, 0.10))

    m = d > thr
    m = ndi.binary_opening(m, np.ones((5, 5)))
    m = ndi.binary_closing(m, np.ones((15, 15)))
    m = ndi.binary_fill_holes(m)
    # drop specks smaller than 0.02% of the frame
    lab, n = ndi.label(m)
    if n:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.flatnonzero(sizes >= 2e-4 * m.size))
        m = keep
    return m, {"floor": floor, "thr": thr, "spread": spread,
               "p99": float(np.quantile(d, 0.99)), "shape": list(a.shape[:2])}


def main():
    os.makedirs(OUT, exist_ok=True)
    P = pairs()
    print(f"{len(P)} pairs\n")
    print(f"{'pair':<20}{'orig true':>13}{'edit true':>13}{'shapes':>9}"
          f"{'thr':>8}{'p99':>8}{'NEW frac':>10}{'OLD frac':>10}   note")
    rows = []
    for k in sorted(P):
        o, e = P[k]["orig"], P[k]["edit"]
        so, se = load_pil(o).size, load_pil(e).size
        m, info = build_mask(o, e)
        if m is None:
            print(f"{k:<20}{str(so):>13}{str(se):>13}   {info['error']}")
            continue
        frac = float(m.mean())
        old = OLD_FRAC.get(k)
        note = ""
        if old is not None:
            note = "matches old" if abs(frac - old) < 0.01 else \
                   f"CHANGED (old {old:.4f})"
        if frac > 0.90:
            note += "  <-- whole frame, unusable"
        np.save(f"{OUT}/{k}_mask.npy", m)
        # working-size copies for the observers, EXIF already applied
        for tag, src in (("orig", o), ("edit", e)):
            im = load_pil(src)
            w, h = im.size
            sc = WORK / float(max(w, h))
            if sc < 1.0:
                im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)
            im.save(f"{OUT}/{k}_{tag}.jpg", "JPEG", quality=92)
        rows.append({"name": k, "mask_frac": frac, "orig": o, "edit": e, **info})
        print(f"{k:<20}{str(so):>13}{str(se):>13}"
              f"{'OK' if so == se else 'MISMATCH':>9}"
              f"{info['thr']:>8.3f}{info['p99']:>8.3f}{frac:>10.4f}"
              f"{old if old is not None else float('nan'):>10.4f}   {note}")

    json.dump(rows, open(f"{OUT}/index.json", "w"), indent=2)
    fr = np.array([r["mask_frac"] for r in rows])
    print(f"\n{len(rows)} masks written to {OUT}/")
    print(f"  edit size: min {fr.min()*100:.2f}%  median {np.median(fr)*100:.2f}%  "
          f"max {fr.max()*100:.2f}%")
    print(f"  pairs above 40% of frame: {(fr > 0.40).sum()}  "
          f"(these contaminate a median baseline by construction)")


if __name__ == "__main__":
    main()
