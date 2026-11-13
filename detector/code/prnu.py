"""
prnu.py -- sensor fixed-pattern noise. The one forensic test genre cannot confound.

WHY THIS ONE IS DIFFERENT FROM THE 34 THAT DIED
-----------------------------------------------
Every free measure tested so far asked "does this image look generated" and every
one turned out to be answering "what is this a picture of". PRNU asks a question
with no semantic content at all: **was this frame read off THIS silicon.**

Photo-response non-uniformity is a manufacturing defect. Each photosite has a
slightly different gain, fixed for the life of the sensor, unique to the
individual unit rather than the model. It multiplies the signal, so it appears in
every frame at the same pixel positions. It cannot be a genre detector, because
it is not a property of scenes.

Its cost is that estimating the reference needs many frames from ONE device, which
is why it is rarely available. We have 13 seam originals plus one full-resolution
photo from a single Galaxy S23 Ultra, all stored 4000x2252.

THE ORIENTATION TRAP -- AND IT IS THE EXACT INVERSE OF THE EARLIER BUG
---------------------------------------------------------------------
FOLDING_PHOTO_SET_AUTOPSY found the pipeline was scoring 15 of 22 photos sideways
because EXIF orientation was never applied, and the fix was to apply it everywhere.

**For PRNU that fix is wrong.** The fingerprint lives in SENSOR coordinates. The
stored buffer of a camera JPEG *is* the sensor readout; the orientation tag is a
display instruction. So:

  * originals   stored 4000x2252 -> already sensor coordinates. Use AS STORED.
                DO NOT call exif_transpose.
  * edits       7 of 13 are stored 2252x4000 because the editing app baked the
                rotation into the pixels. Those must be rotated BACK to sensor
                coordinates before they can be compared to the reference.

Get this backwards and every correlation is zero for a reason that has nothing to
do with forensics. Semantic work needs display orientation; sensor forensics needs
sensor orientation. Same file, two different correct answers.

THE CONTROL THAT MAKES THIS INTERPRETABLE
-----------------------------------------
Rather than reaching for another camera, rotate an S23 image by 90 degrees and
correlate it against the reference. Same sensor, same scene, same processing,
same everything -- only the pixel-to-photosite alignment is destroyed. If
correlation survives that, the measure is reading content and not the sensor.
This is the same move as the real-vs-real control arm, applied inside one device.

PRE-REGISTERED
--------------
  1. Held-out S23 originals correlate positively with the reference; rotated
     copies of the same images do not. If 1 fails, PRNU did not survive the
     consumer resize-and-recompress pipeline and every history-based device claim
     is dead for files like these -- which is a real and publishable negative.
  2. AI images centre-cropped to the same size show no correlation.
  3. Only if 1 holds: PRNU correlation drops INSIDE the edited regions of the 13
     pairs, with the untouched originals as the control arm.
  4. Risk: these files were resized and recompressed before we got them, and the
     seam originals sit at 4000x2252 where the S23 sensor is 12000x9000-class.
     Heavy downscaling averages photosites together and is the classic PRNU
     killer. Expect this to be weak at best.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pywt
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ALT = "/mnt/user-data/uploads/Vesica AI/AI Detector/more photos/altered"
REAL = "/mnt/user-data/uploads/Vesica AI/AI Detector/real photos"
AI = "/mnt/user-data/uploads/Vesica AI/AI Detector/ai photos"
CROP = 1024          # centre crop side for the survival test


# ---------------------------------------------------------------- noise residual

def _mihcak(coef, sigma0=3.0):
    """Wiener shrink in the wavelet domain, local variance from the min over
    several window sizes -- the standard PRNU denoiser (Mihcak et al. 1999)."""
    from scipy.ndimage import uniform_filter
    var = None
    for w in (3, 5, 7, 9):
        v = np.maximum(uniform_filter(coef ** 2, w) - sigma0 ** 2, 0.0)
        var = v if var is None else np.minimum(var, v)
    return coef * var / (var + sigma0 ** 2)


def noise_residual(gray, levels=4, sigma0=3.0):
    """W = I - denoise(I). Carries the PRNU plus everything else noisy."""
    c = pywt.wavedec2(gray, "db8", level=levels)
    out = [c[0]]
    for det in c[1:]:
        out.append(tuple(_mihcak(d, sigma0) for d in det))
    den = pywt.waverec2(out, "db8")
    den = den[:gray.shape[0], :gray.shape[1]]
    return gray - den


def zero_mean(w):
    """Remove row and column means.

    This is not cosmetic. CFA demosaicing and JPEG's 8x8 blocking imprint
    periodic row/column structure that is shared by every unit of the same MODEL.
    Left in, it produces strong correlations between any two same-model images
    and would be mistaken for a unit-specific fingerprint. Stripping it is what
    makes the measure about this individual sensor.
    """
    w = w - w.mean(axis=0, keepdims=True)
    w = w - w.mean(axis=1, keepdims=True)
    return w


def load_sensor_gray(path, target_shape=None, undo_exif=False):
    """Grayscale in SENSOR coordinates. See the orientation note in the header."""
    im = Image.open(path)
    orient = im.getexif().get(274)
    im = im.convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    g = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if undo_exif and target_shape is not None and g.shape != target_shape:
        # the editor baked the rotation in; put it back into sensor coordinates
        for k in (1, 3):
            r = np.rot90(g, k)
            if r.shape == target_shape:
                return np.ascontiguousarray(r), orient
        return None, orient
    return g, orient


def centre_crop(a, n):
    h, w = a.shape
    if h < n or w < n:
        return None
    y, x = (h - n) // 2, (w - n) // 2
    return np.ascontiguousarray(a[y:y + n, x:x + n])


def ncc(a, b):
    """Normalised cross-correlation, zero-lag."""
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else np.nan


def pce(a, b, radius=11):
    """Peak-to-correlation-energy: the standard PRNU statistic.

    Correlation at zero lag divided by the energy of the correlation surface
    away from the peak. Far more robust than raw NCC because it measures how
    much the true alignment stands out from every wrong alignment -- a built-in
    null, computed from the same data.
    """
    A = np.fft.rfft2(a - a.mean())
    B = np.fft.rfft2(b - b.mean())
    c = np.fft.irfft2(A * np.conj(B), s=a.shape)
    c = c / (np.sqrt((a - a.mean()).__pow__(2).sum() *
                     (b - b.mean()).__pow__(2).sum()) + 1e-12)
    peak = c[0, 0]
    m = np.ones_like(c, bool)
    m[:radius, :radius] = False
    m[:radius, -radius:] = False
    m[-radius:, :radius] = False
    m[-radius:, -radius:] = False
    energy = (c[m] ** 2).mean()
    return float(np.sign(peak) * peak ** 2 / (energy + 1e-20))


def main():
    pairs = {}
    for p in sorted(glob.glob(f"{ALT}/*.jpg")):
        b = os.path.basename(p)
        key = b.replace("(1)", "").replace(".jpg", "")
        pairs.setdefault(key, {})["edit" if "(1)" in b else "orig"] = p
    pairs = {k: v for k, v in pairs.items() if len(v) == 2}
    names = sorted(pairs)
    print(f"{len(names)} S23 Ultra pairs")

    # ---- originals, in sensor coordinates, centre-cropped
    print(f"\ncomputing noise residuals on {CROP}x{CROP} centre crops "
          f"(sensor coordinates, EXIF NOT applied)...", flush=True)
    W, shapes = {}, {}
    for n in names:
        g, orient = load_sensor_gray(pairs[n]["orig"])
        shapes[n] = g.shape
        c = centre_crop(g, CROP)
        W[n] = zero_mean(noise_residual(c))
        print(f"  {n:<20} stored {g.shape}  orient={orient}", flush=True)

    ref_shape = max(set(shapes.values()), key=list(shapes.values()).count)
    use = [n for n in names if shapes[n] == ref_shape]
    print(f"\nreference frame {ref_shape}: {len(use)}/{len(names)} originals usable")

    # ---- leave-one-out: does a held-out original match a reference built without it?
    print(f"\n{'='*94}")
    print("TEST 1 -- does the fingerprint survive?  leave-one-out on the originals")
    print("  a rotated copy of the SAME image is the control: same sensor, same")
    print("  scene, same processing -- only photosite alignment destroyed")
    print("=" * 94)
    print(f"{'held-out image':<22}{'NCC vs ref':>13}{'PCE':>12}"
          f"{'NCC rot90':>12}{'NCC rot180':>13}")
    rows = []
    for n in use:
        others = [m for m in use if m != n]
        K = np.mean([W[m] for m in others], axis=0)
        K = zero_mean(K)
        w = W[n]
        r = {"name": n,
             "ncc": ncc(w, K), "pce": pce(w, K),
             "ncc_rot90": ncc(np.rot90(w, 1), K),
             "ncc_rot180": ncc(np.rot90(w, 2), K)}
        rows.append(r)
        print(f"{n:<22}{r['ncc']:>13.5f}{r['pce']:>12.2f}"
              f"{r['ncc_rot90']:>12.5f}{r['ncc_rot180']:>13.5f}")

    nc = np.array([r["ncc"] for r in rows])
    n90 = np.array([r["ncc_rot90"] for r in rows])
    n180 = np.array([r["ncc_rot180"] for r in rows])
    pc = np.array([r["pce"] for r in rows])
    print(f"\n  true alignment   mean NCC {nc.mean():+.5f}   "
          f"sd {nc.std():.5f}   positive {int((nc>0).sum())}/{len(nc)}")
    print(f"  rot90  control   mean NCC {n90.mean():+.5f}   "
          f"sd {n90.std():.5f}   positive {int((n90>0).sum())}/{len(n90)}")
    print(f"  rot180 control   mean NCC {n180.mean():+.5f}   "
          f"sd {n180.std():.5f}   positive {int((n180>0).sum())}/{len(n180)}")
    print(f"  mean PCE {pc.mean():.2f}   PCE>50 on {int((pc>50).sum())}/{len(pc)}"
          f"   (PCE>50 is the usual identification bar)")

    ctrl = np.concatenate([n90, n180])
    t = (nc.mean() - ctrl.mean()) / np.sqrt(nc.var(ddof=1) / len(nc)
                                            + ctrl.var(ddof=1) / len(ctrl))
    print(f"\n  true vs rotated-control  t = {t:.2f}   "
          f"separation {nc.mean()-ctrl.mean():+.5f}")

    # ---- AI control
    print(f"\n{'-'*94}\nTEST 2 -- AI images against the same reference (expect nothing)")
    K_all = zero_mean(np.mean([W[m] for m in use], axis=0))
    ai_rows = []
    for p in sorted(glob.glob(f"{AI}/*")):
        g, _ = load_sensor_gray(p)
        c = centre_crop(g, CROP)
        if c is None:
            continue
        w = zero_mean(noise_residual(c))
        ai_rows.append({"name": os.path.basename(p)[:26],
                        "ncc": ncc(w, K_all), "pce": pce(w, K_all)})
    if ai_rows:
        a_ = np.array([r["ncc"] for r in ai_rows])
        print(f"  {len(ai_rows)} AI images large enough to crop")
        print(f"  mean NCC {a_.mean():+.5f}   sd {a_.std():.5f}   "
              f"positive {int((a_>0).sum())}/{len(a_)}")
        print(f"  S23 held-out mean {nc.mean():+.5f}  vs  AI mean {a_.mean():+.5f}"
              f"   separation {nc.mean()-a_.mean():+.5f}")

    verdict = ("SURVIVES" if (nc.mean() > 0 and t > 2.5)
               else "DOES NOT SURVIVE")
    print(f"\n{'='*94}\nVERDICT: the sensor fingerprint {verdict} the consumer pipeline")
    print("=" * 94)
    if verdict == "DOES NOT SURVIVE":
        print("  Then device attribution is unavailable for files like these, and every")
        print("  history-based claim about them is limited to what the container says.")
        print("  That is a real negative and it bounds the whole clean-history idea.")

    json.dump({"loo": rows, "ai": ai_rows, "crop": CROP,
               "ref_shape": list(ref_shape), "verdict": verdict,
               "t_vs_rotated": t},
              open("prnu_results.json", "w"), indent=2, default=str)
    print("\nwrote prnu_results.json")


if __name__ == "__main__":
    main()
