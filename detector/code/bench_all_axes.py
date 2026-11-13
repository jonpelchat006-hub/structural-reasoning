"""
bench_all_axes.py — the content-matched, compression-matched benchmark.

WHY THIS EXISTS
---------------
Two confounds were caught in this line, one layer apart:

  1. COMPRESSION. AI output is PNG-native, real photos are camera JPEG. Scoring
     them as-is lets any sharpness-sensitive measure post a spurious AUC.
     Fixed by transcoding both classes through one identical encoder.

  2. CONTENT. The AI class was ~13 studio beauty portraits; the real class was
     outdoor snapshots. Splitting the REAL class by content alone reproduced
     54-77% of the apparent "AI signal" -- one real face out-scored the AI mean
     on blur_ratio. See FOLDING_PHYSICS_OBSERVER Part I.

This harness closes both. The content fix is STRATIFICATION: AUC is computed
WITHIN each content bucket and then pooled, so "portrait vs landscape" cannot
masquerade as "AI vs real". It also reports the raw pooled AUC beside it, and the
gap between the two IS the confound size -- if stratified << pooled, the naive
number was mostly content.

REQUIRED LAYOUT
---------------
    data/
      real/portrait/*.jpg      ai/portrait/*.png
      real/landscape/*.jpg     ai/landscape/*.png
      real/<bucket>/...        ai/<bucket>/...

Bucket names must match across real/ and ai/. Any bucket present on only one side
is skipped with a warning -- an unmatched bucket is exactly the confound.

    python bench_all_axes.py --data data --q 85
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reconstruction_observer as ro
import nonlocal_observer as nl
import environment_observer as env

try:
    import mixedness_observer as mx
except ImportError:
    mx = None
try:
    import spectral_observer as sp
except ImportError:
    sp = None

EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
WORK_SIDE = 512


# ── parity ────────────────────────────────────────────────────────────────────

def transcode(src, dst, q, square=None):
    """Parity-normalise every image in `src` into `dst`.

    THREE things are equalised here, and the second and third were missing
    until they were caught on Jonathan's own photo set:

      1. ENCODING. One identical JPEG q round trip for both classes, so
         PNG-native generator output and camera JPEG reach the observers
         through the same encoder. (This was always here.)

      2. ORIENTATION -- ADDED. PIL does not apply the EXIF Orientation tag.
         15 of 22 files in `real photos/` are stored sideways with a rotate-me
         flag; 0 of 17 in `ai photos/` are, because generator output has no
         EXIF. Result: STORED ASPECT RATIO SEPARATED THE CLASSES AT AUC 1.000
         while true aspect ratio gives 0.591. Without exif_transpose, two
         thirds of the real class is scored 90 degrees rotated and the
         benchmark contains a perfect free separator.

      3. GEOMETRY -- ADDED, optional via `square`. Matching only the longest
         side leaves landscape and portrait images downsampled by different
         ratios, which is itself a sharpness confound. Centre-cropping to
         square and resizing to a fixed square kills aspect ratio, pixel
         count and resampling ratio together. Recommended whenever the two
         classes differ in shape.
    """
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(EXTS):
            continue
        im = ImageOps.exif_transpose(Image.open(os.path.join(src, f))).convert("RGB")
        w, h = im.size
        if square:
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2,
                          (w - s) // 2 + s, (h - s) // 2 + s))
            im = im.resize((square, square), Image.LANCZOS)
        else:
            sc = WORK_SIDE / float(max(w, h))
            if sc < 1.0:
                im = im.resize((int(round(w * sc)), int(round(h * sc))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        buf.seek(0)
        Image.open(buf).save(os.path.join(dst, os.path.splitext(f)[0] + ".jpg"),
                             "JPEG", quality=q)
        n += 1
    return n


def trivial_audit(groups):
    """Report free separators BEFORE any observer runs.

    A benchmark whose classes are separable by stored aspect ratio, bits per
    pixel or megapixels cannot support ANY provenance claim, however good the
    observer numbers look. Run this first and read it first.
    """
    import numpy as _np
    print(f"\n{'='*88}\nTRIVIAL SEPARATOR AUDIT -- these know nothing about "
          f"provenance\n{'='*88}")
    stats = {}
    for lab, paths in groups.items():
        rows = []
        for p in paths:
            im = Image.open(p)
            w, h = im.size
            tw, th = ImageOps.exif_transpose(im).size
            rows.append({"stored_ar": w / h, "true_ar": tw / th,
                         "bpp": os.path.getsize(p) * 8 / (w * h),
                         "megapixels": w * h / 1e6,
                         "sideways": (tw, th) != (w, h)})
        stats[lab] = rows
        print(f"  {lab:<10} n={len(rows):<4} stored sideways "
              f"{sum(r['sideways'] for r in rows)}/{len(rows)}")
    labs = list(stats)
    if len(labs) == 2:
        a, b = labs
        for k in ("stored_ar", "true_ar", "bpp", "megapixels"):
            v = auc(_np.array([r[k] for r in stats[a]]),
                    _np.array([r[k] for r in stats[b]]))
            bad = abs(v - 0.5) >= 0.35
            print(f"  {k:<14} AUC {v:.3f}  |AUC-0.5| {abs(v-0.5):.3f}"
                  f"{'   <-- FREE SEPARATOR, benchmark is invalid' if bad else ''}")
    return stats


# ── feature extraction across every axis ──────────────────────────────────────

SKIP_RECON = os.environ.get("SKIP_RECON") == "1"


def all_features(path):
    f = {}
    r = None if SKIP_RECON else ro.analyse(path)
    if r is not None and r.ok:
        for k in ("seed_convergence", "ladder_fb_agreement", "nonmonotone_fraction",
                  "return_at_low", "return_at_high", "thermal_slope",
                  "roundtrip_fixed_point", "struct_residual"):
            f["recon." + k] = getattr(r, k)
        f["_recon_note"] = r.note
    n = nl.analyse(path)
    for k in ("nonlocal_err_fine", "nonlocal_err_coarse", "nonlocal_asymmetry"):
        f["window." + k] = n[k]
    e = env.analyse(path)
    f["_env_fired"] = e["fired"]
    if e["fired"]:
        for k in ("env_scale_agreement", "env_concentration", "env_struct_R"):
            import math as _m
            if isinstance(e.get(k), float) and _m.isfinite(e[k]):
                f["bridge." + k] = e[k]
    if mx:
        for k, v in mx.features(path).items():
            f["mixed." + k] = v
    if sp:
        for k, v in sp.features(path).items():
            if isinstance(v, (int, float)):
                f["spectral." + k] = v
    return f


# ── metrics ───────────────────────────────────────────────────────────────────

def auc(pos, neg):
    """Unsigned Mann-Whitney AUC. 0.10 is as strong as 0.90."""
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def stratified_auc(rows, feat):
    """AUC computed WITHIN each content bucket, pooled by pair count.

    This is the content fix. A measure that only separates portraits from
    landscapes scores ~0.5 here no matter how well it separates the raw classes.
    """
    num = den = 0.0
    per = {}
    for b in sorted({r["bucket"] for r in rows}):
        p = np.array([r["f"][feat] for r in rows
                      if r["bucket"] == b and r["label"] == "real"
                      and feat in r["f"]], float)
        q = np.array([r["f"][feat] for r in rows
                      if r["bucket"] == b and r["label"] == "ai"
                      and feat in r["f"]], float)
        a = auc(p, q)
        if np.isnan(a):
            continue
        per[b] = (a, len(p) * len(q))
        num += a * len(p) * len(q)
        den += len(p) * len(q)
    return (num / den if den else np.nan), per


def content_drift(rows, feat):
    """How much of the gap is reproducible inside the REAL class alone?"""
    buckets = sorted({r["bucket"] for r in rows})
    means = {}
    for b in buckets:
        v = [r["f"][feat] for r in rows if r["bucket"] == b
             and r["label"] == "real" and feat in r["f"]]
        if v:
            means[b] = float(np.mean(v))
    if len(means) < 2:
        return np.nan
    real_all = np.mean([r["f"][feat] for r in rows if r["label"] == "real"
                        and feat in r["f"]])
    ai_all = np.mean([r["f"][feat] for r in rows if r["label"] == "ai"
                      and feat in r["f"]])
    gap = abs(real_all - ai_all)
    drift = max(means.values()) - min(means.values())
    return float(drift / gap) if gap > 1e-12 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--q", type=int, default=85)
    ap.add_argument("--json", default="bench_all_axes.json")
    a = ap.parse_args()

    real_root = os.path.join(a.data, "real")
    ai_root = os.path.join(a.data, "ai")
    rb = {d for d in os.listdir(real_root) if os.path.isdir(os.path.join(real_root, d))}
    ab = {d for d in os.listdir(ai_root) if os.path.isdir(os.path.join(ai_root, d))}
    for b in sorted(rb ^ ab):
        print(f"  [!] bucket '{b}' exists on only one side — SKIPPED "
              f"(an unmatched bucket is the confound)")
    buckets = sorted(rb & ab)
    if not buckets:
        raise SystemExit("no matched content buckets found")

    work = "_bench"
    shutil.rmtree(work, ignore_errors=True)
    rows = []
    for b in buckets:
        for label, root in (("real", real_root), ("ai", ai_root)):
            dst = os.path.join(work, label, b)
            n = transcode(os.path.join(root, b), dst, a.q)
            print(f"  {label}/{b}: {n} images -> {WORK_SIDE}px JPEG q{a.q}")
            for f in sorted(os.listdir(dst)):
                p = os.path.join(dst, f)
                rows.append({"path": p, "label": label, "bucket": b,
                             "f": all_features(p)})
                print(f"    {label}/{b}/{f[:34]:<34} done", flush=True)

    feats = sorted({k for r in rows for k in r["f"] if not k.startswith("_")})
    print(f"\n{'='*88}\nCONTENT-MATCHED + COMPRESSION-MATCHED  "
          f"(buckets: {', '.join(buckets)})\n{'='*88}")
    print(f"{'feature':<32}{'pooled':>9}{'STRATIFIED':>12}{'drift':>8}  verdict")
    out = {}
    for f in feats:
        p = np.array([r["f"][f] for r in rows if r["label"] == "real" and f in r["f"]], float)
        q = np.array([r["f"][f] for r in rows if r["label"] == "ai" and f in r["f"]], float)
        pooled = auc(p, q)
        strat, per = stratified_auc(rows, f)
        drift = content_drift(rows, f)
        if np.isnan(strat):
            continue
        note = ""
        if abs(pooled - 0.5) - abs(strat - 0.5) > 0.10:
            note = "was mostly CONTENT"
        elif abs(strat - 0.5) >= 0.25:
            note = "REAL SIGNAL"
        out[f] = {"pooled": pooled, "stratified": strat, "per_bucket": per,
                  "content_drift": drift}
        print(f"{f:<32}{pooled:>9.3f}{strat:>12.3f}{drift:>8.2f}  {note}")

    # independence audit across every axis at once
    print(f"\n{'='*88}\nINDEPENDENCE — max |r| against features of OTHER axes\n{'='*88}")
    axes = {}
    for f in feats:
        axes.setdefault(f.split(".")[0], []).append(f)
    V = {f: np.array([r["f"][f] for r in rows if f in r["f"]], float) for f in feats}
    for f in feats:
        mine = f.split(".")[0]
        worst, who = 0.0, ""
        for g in feats:
            if g.split(".")[0] == mine or len(V[g]) != len(V[f]):
                continue
            c = abs(np.corrcoef(V[f], V[g])[0, 1])
            if c > worst:
                worst, who = c, g
        if f in out:
            out[f]["max_r_other_axis"] = worst
            out[f]["max_r_with"] = who
            if abs(out[f]["stratified"] - 0.5) >= 0.20:
                print(f"{f:<32}{worst:>6.2f}  vs {who:<28}"
                      f"{'REDUNDANT' if worst > 0.7 else 'INDEPENDENT'}")

    with open(a.json, "w") as fh:
        json.dump({"buckets": buckets, "jpeg_q": a.q, "work_side": WORK_SIDE,
                   "n": {b: {l: sum(1 for r in rows if r["bucket"] == b
                                    and r["label"] == l) for l in ("real", "ai")}
                         for b in buckets},
                   "results": out,
                   "rows": [{k: v for k, v in r.items() if k != "f"} | {"f": r["f"]}
                            for r in rows]}, fh, indent=2, default=str)
    print(f"\nwrote {a.json}")
    print("\nRead the STRATIFIED column, not the pooled one. Where they diverge by "
          "more than 0.10\nthe pooled number was measuring what the picture is of, "
          "not who made it.")


if __name__ == "__main__":
    main()
