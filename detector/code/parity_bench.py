"""
parity_bench.py — compression-parity harness for the reconstruction axis.

The problem this exists to solve: Jonathan's AI set is PNG straight out of
Midjourney/Grok; his real set is camera JPEG. Scoring them as-is would let any
axis that responds to compression post a beautiful and entirely spurious AUC.
The q75 control in FOLDING_RECONSTRUCTION Part V already showed the round-trip
measure moving 0.691 -> 0.865 on compression alone.

So: put BOTH classes through the SAME encoder at the SAME quality, then score.

Honest limitation, stated up front. The real photos were born as JPEG. Transcoding
them to PNG does not remove the artifacts already baked in, so a "both classes as
PNG" setting is NOT achievable parity here -- it would just be JPEG-vs-clean again
with the labels hidden. The only defensible setting is BOTH AS JPEG: the AI PNGs
get compressed once, the real photos get recompressed (double-compressed) once.
A residual asymmetry survives that, and it is noted in the output rather than
papered over. Genuine parity needs camera RAW or PNG-native real photos.

Usage:
    python parity_bench.py --real "real photos" --ai "ai photos" --q 85
"""

import argparse
import io
import json
import os
import shutil

import numpy as np
from PIL import Image

import reconstruction_observer as ro

EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def transcode(src_dir, dst_dir, quality):
    """Resize to the observer's working side, then encode everything through
    one identical JPEG path. Resize first so the encoder sees the same pixel
    count for every image -- resolution is the other half of this confound."""
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(src_dir)):
        if not f.lower().endswith(EXTS):
            continue
        im = Image.open(os.path.join(src_dir, f)).convert("RGB")
        w, h = im.size
        sc = ro.WORK_SIDE / float(max(w, h))
        if sc < 1.0:
            im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=quality)
        buf.seek(0)
        Image.open(buf).save(os.path.join(dst_dir, os.path.splitext(f)[0] + ".jpg"),
                             "JPEG", quality=quality)
        n += 1
    return n


def run(folder, label):
    rows = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(EXTS):
            continue
        r = ro.analyse(os.path.join(folder, f))
        d = r.__dict__.copy()
        d["label"] = label
        rows.append(d)
        print(f"  [{label}] {f[:44]:<44} "
              f"seedconv={r.seed_convergence:.3f} "
              f"orphan={r.nonmonotone_fraction:.3f} "
              f"tslope={r.thermal_slope:+.2f} "
              f"roundtrip={r.roundtrip_fixed_point:.3f} "
              f"resid={r.struct_residual:.3f}"
              + ("  [!] " + r.note if r.note else ""), flush=True)
    return rows


FEATS = ["seed_convergence", "ladder_fb_agreement", "nonmonotone_fraction",
         "return_rate", "return_at_low", "return_at_high", "thermal_slope",
         "return_spread", "mean_displacement", "restoring_fraction",
         "roundtrip_fixed_point", "struct_residual", "rest_energy_ratio"]


def report(rows, tag):
    real = [r for r in rows if r["label"] == "real" and r["ok"]]
    ai = [r for r in rows if r["label"] == "ai" and r["ok"]]
    print(f"\n=== {tag}   n_real={len(real)}  n_ai={len(ai)} ===")
    print(f"{'sub-measure':<24}{'real':>9}{'ai':>9}{'AUC':>8}{'|d|':>7}  direction")
    out = {}
    for f in FEATS:
        a = np.array([r[f] for r in real], float)
        b = np.array([r[f] for r in ai], float)
        if len(a) < 2 or len(b) < 2:
            continue
        v = ro._auc(a, b)
        out[f] = {"auc_real_over_ai": v, "real_mean": float(a.mean()),
                  "ai_mean": float(b.mean())}
        d = "higher in REAL" if v > 0.5 else "higher in AI"
        print(f"{f:<24}{a.mean():>9.3f}{b.mean():>9.3f}{v:>8.3f}"
              f"{abs(v - 0.5):>7.3f}  {d}")
    print("\nAUC is unsigned: 0.10 is as strong as 0.90, it just points the "
          "other way.\nn is small -- treat |AUC-0.5| < 0.25 as noise.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True)
    ap.add_argument("--ai", required=True)
    ap.add_argument("--q", type=int, default=85)
    ap.add_argument("--json", default="parity_metrics.json")
    a = ap.parse_args()

    work = "_parity"
    shutil.rmtree(work, ignore_errors=True)
    nr = transcode(a.real, f"{work}/real", a.q)
    na = transcode(a.ai, f"{work}/ai", a.q)
    print(f"transcoded both classes -> {ro.WORK_SIDE}px, JPEG q{a.q}  "
          f"(real={nr}, ai={na})\n")

    rows = run(f"{work}/real", "real") + run(f"{work}/ai", "ai")
    res = report(rows, f"COMPRESSION PARITY, both classes JPEG q{a.q}")

    with open(a.json, "w") as fh:
        json.dump({"parity": {"work_side": ro.WORK_SIDE, "jpeg_q": a.q,
                              "n_real": nr, "n_ai": na},
                   "caveat": ("real photos were born JPEG and are therefore "
                              "double-compressed here; AI PNGs are compressed "
                              "once. residual asymmetry remains."),
                   "auc": res, "rows": rows}, fh, indent=2, default=str)
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
