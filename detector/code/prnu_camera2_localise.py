"""
prnu_camera2_localise.py -- the test the whole session has been building toward.

A PCE-1460 reference from camera-original flat frames, against edited pairs shot
on the same phone at native resolution. FOLDING_PRNU's localisation number
(+0.410) was n=1 on a file whose fingerprint was 13x weaker than this.

ALIGNMENT, done self-verifyingly
--------------------------------
The editor writes its output already rotated (orientation=1) while the camera
originals carry a rotate-me tag. Rather than reasoning about which way each
orientation code turns -- and getting it wrong silently -- every candidate
rotation of the edit is tried and the one that CORRELATES WITH THE ORIGINAL is
kept. A wrong rotation correlates at ~0; the right one at ~1. The alignment
check is the data, not my arithmetic.

MASK
----
Built in sensor coordinates by differencing the aligned pair, with the noise
floor estimated from the low quartile (the lesson from rebuild_seam: estimate
scale from a region the signal cannot occupy).

CONTROL ARM
-----------
The identical block computation on the UNTOUCHED original, reading the same
cells. If the fingerprint is weak inside those cells on the original too, the
measure is reacting to the region rather than to the edit.
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
from prnu import centre_crop, load_sensor_gray, ncc, noise_residual, pce, zero_mean

NEW = "/mnt/user-data/uploads/Vesica AI/AI Detector/more photos/camera 2"
EDT = "/mnt/user-data/uploads/Vesica AI/AI Detector/more photos/camera 2 edits"
FLATBAR = 0.035
FRAME = (2252, 4000)          # sensor frame the reference lives in
BLOCK = 128


def gray_stored(path):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def to_frame(g):
    """Crop a 4:3 sensor readout to the 16:9 frame the reference uses."""
    if g.shape == FRAME:
        return g
    if g.shape[1] == FRAME[1] and g.shape[0] > FRAME[0]:
        o = (g.shape[0] - FRAME[0]) // 2
        return np.ascontiguousarray(g[o:o + FRAME[0]])
    return None


def align_to(edit_g, orig_g):
    """Return the edit rotated into the original's stored frame, self-verified."""
    best, bk, bc = None, None, -2.0
    for k in range(4):
        r = np.rot90(edit_g, k)
        if r.shape != orig_g.shape:
            continue
        c = ncc(r, orig_g)
        if c > bc:
            best, bk, bc = np.ascontiguousarray(r), k, c
    return best, bk, bc


def build_mask(a, b):
    d = np.abs(a - b) / 255.0
    d = ndi.uniform_filter(d, 3)
    floor = float(np.quantile(d, 0.25))
    thr = max(10.0 * floor, 0.02)
    m = d > thr
    m = ndi.binary_opening(m, np.ones((5, 5)))
    m = ndi.binary_closing(m, np.ones((15, 15)))
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    if n:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.flatnonzero(sizes >= 2e-4 * m.size))
    return m, thr


def blocks(W, K, mask):
    H, Wd = K.shape
    v, c = [], []
    for y in range(0, H - BLOCK + 1, BLOCK):
        for x in range(0, Wd - BLOCK + 1, BLOCK):
            v.append(ncc(W[y:y + BLOCK, x:x + BLOCK], K[y:y + BLOCK, x:x + BLOCK]))
            c.append(mask[y:y + BLOCK, x:x + BLOCK].mean())
    return np.array(v), np.array(c)


def auc(pos, neg):
    from scipy.stats import rankdata
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 1 or len(neg) < 1:
        return np.nan
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    # ---- reference from the flat camera-original frames, FULL RESOLUTION
    print("building the reference from flat camera-original frames...", flush=True)
    REF = {}
    acc, n = None, 0
    for p in sorted(glob.glob(f"{NEW}/*.jpg")):
        g = gray_stored(p)
        if g.shape != FRAME:
            continue
        c = centre_crop(g, 1024)
        if float(np.sqrt(np.mean(ndi.laplace(c / 255.0) ** 2))) > FLATBAR:
            continue
        w = zero_mean(noise_residual(g))
        REF[os.path.basename(p)] = w
        acc = w if acc is None else acc + w
        n += 1
        print(f"  {n}: {os.path.basename(p)}", flush=True)
    K = zero_mean(acc / n)
    print(f"reference from {n} flat frames, {K.shape}")
    print("  reference members:", ", ".join(sorted(REF)))

    def ref_excluding(base):
        """LEAVE-ONE-OUT. Several pair originals are themselves reference members
        (145939, 145954, 150002, 171926). Leaving them in makes the original
        correlate with itself -- which is what produced PCE 523724 and 934162 in
        the first run. Those numbers were leakage, not fingerprint strength."""
        k = f"{base}.jpg"
        if k not in REF:
            return K, False
        keep = [v for kk, v in REF.items() if kk != k]
        return zero_mean(np.mean(keep, axis=0)), True

    # ---- pairs
    pairs = []
    for p in sorted(glob.glob(f"{EDT}/*.jpg")):
        b = os.path.basename(p)
        if "(1)" not in b:
            continue
        base = b.split("(1)")[0]
        o = f"{NEW}/{base}.jpg"
        if os.path.exists(o):
            pairs.append((b.replace(".jpg", ""), o, p))
    print(f"\n{len(pairs)} edited files with originals\n")

    res = []
    for name, op, ep in pairs:
        og = gray_stored(op)
        eg = gray_stored(ep)
        al, k, c = align_to(eg, og)
        if al is None:
            print(f"  {name:<26} SKIP - no rotation matches {eg.shape} to {og.shape}")
            continue
        ogf, alf = to_frame(og), to_frame(al)
        if ogf is None or alf is None:
            print(f"  {name:<26} SKIP - {og.shape} not reducible to {FRAME}")
            continue
        Kp, held = ref_excluding(name.split("(1)")[0])
        mask, thr = build_mask(ogf, alf)
        frac = float(mask.mean())
        Wo = zero_mean(noise_residual(ogf))
        We = zero_mean(noise_residual(alf))
        row = {"name": name, "rot_k": k, "align_ncc": c, "frac": frac,
               "held_out": held,
               "pce_orig": pce(Wo, Kp), "pce_edit": pce(We, Kp),
               "ncc_orig": ncc(Wo, Kp), "ncc_edit": ncc(We, Kp)}
        for tag, W in (("edit", We), ("orig", Wo)):
            v, cov = blocks(W, Kp, mask)
            ins, outs = v[cov >= 0.4], v[cov <= 0.05]
            if len(ins) < 1 or len(outs) < 2:
                row[f"{tag}_auc"] = np.nan
                continue
            row[f"{tag}_in"] = float(ins.mean())
            row[f"{tag}_out"] = float(outs.mean())
            row[f"{tag}_auc"] = auc(outs, ins)
            row[f"{tag}_n_in"] = len(ins)
            row[f"{tag}_n_out"] = len(outs)
        res.append(row)
        print(f"  {name:<26} rot{k*90:<4} align r={c:.3f}  edit {100*frac:>5.2f}%  "
              f"{'LOO' if held else '   '} PCE orig {row['pce_orig']:>8.1f} edit {row['pce_edit']:>8.1f}  "
              f"AUC {row.get('edit_auc', np.nan):.3f} / ctrl "
              f"{row.get('orig_auc', np.nan):.3f}", flush=True)

    good = [r for r in res if np.isfinite(r.get("edit_auc", np.nan))
            and np.isfinite(r.get("orig_auc", np.nan))]
    e = np.array([r["edit_auc"] for r in good])
    o = np.array([r["orig_auc"] for r in good])
    print(f"\n{'='*98}\nDOES THE FINGERPRINT DROP INSIDE THE EDIT?  "
          f"({len(good)} pairs)\n{'='*98}")
    print(f"{'image':<26}{'edit%':>8}{'blocks in':>11}{'NCC in':>10}{'NCC out':>10}"
          f"{'EDITED AUC':>12}{'CONTROL':>10}")
    for r in sorted(good, key=lambda x: x["frac"]):
        print(f"{r['name']:<26}{100*r['frac']:>7.2f}%{r.get('edit_n_in',0):>11}"
              f"{r.get('edit_in',np.nan):>10.5f}{r.get('edit_out',np.nan):>10.5f}"
              f"{r['edit_auc']:>12.3f}{r['orig_auc']:>10.3f}")
    print(f"\n  EDITED   mean AUC {e.mean():.3f}   above chance {int((e>0.5).sum())}/{len(e)}")
    print(f"  CONTROL  mean AUC {o.mean():.3f}   above chance {int((o>0.5).sum())}/{len(o)}")
    print(f"  edit - control = {e.mean()-o.mean():+.3f}")
    from math import comb
    w = int((e > o).sum())
    p = min(1.0, sum(comb(len(e), i) for i in range(max(w, len(e)-w), len(e)+1))
            / 2 ** len(e) * 2)
    print(f"  edited beats its own control on {w}/{len(e)}   sign p = {p:.3f}")
    print(f"\n{'-'*98}\nWHOLE-IMAGE DETECTION -- fingerprint strength, original vs edited")
    print(f"{'image':<26}{'edit%':>8}{'PCE orig':>12}{'PCE edit':>12}{'ratio':>9}"
          f"{'NCC orig':>11}{'NCC edit':>11}")
    for r in sorted(res, key=lambda x: x["frac"]):
        rt = r["pce_edit"] / r["pce_orig"] if r["pce_orig"] > 0 else float("nan")
        print(f"{r['name']:<26}{100*r['frac']:>7.2f}%{r['pce_orig']:>12.1f}"
              f"{r['pce_edit']:>12.1f}{rt:>9.3f}{r['ncc_orig']:>11.5f}{r['ncc_edit']:>11.5f}")

    print(f"\n  for comparison, FOLDING_PRNU n=1: edited 0.812  control 0.403  (+0.410)")
    print(f"  best free measure to date: spec_dev 0.582 / 0.428 (+0.154)")

    json.dump({"rows": res, "n_ref": n}, open("prnu_camera2_localise.json", "w"),
              indent=2, default=str)
    print("\nwrote prnu_camera2_localise.json")


if __name__ == "__main__":
    main()
