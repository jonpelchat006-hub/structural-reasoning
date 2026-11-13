"""
format_probe.py -- handle every file type, and keep file evidence OUT of pixel evidence.

Jonathan: "we probably should be able to handle multiple types of image files.
that doesnt really change what the image is it just gives different starting
conditions and needs the right methods for it."

Exactly right, and the consequence is a rule the project did not have:

    THERE ARE TWO KINDS OF EVIDENCE AND THEY MUST NEVER BE MIXED.

  CHANNEL A -- evidence about the FILE. Format, JPEG quantisation tables,
    estimated quality, chroma subsampling, EXIF completeness, camera make and
    model, ICC profile, software tag. This is real and often decisive: a file
    straight off a Galaxy S23 carries a Samsung quantisation table, a full EXIF
    block and a maker note, and a Midjourney PNG carries none of it. But it is
    evidence about the container, and it is trivially forged -- re-save any
    generated image through a phone's gallery app and the whole channel flips.

  CHANNEL B -- evidence about the IMAGE. Everything measured from pixels after
    parity normalisation.

Blending them is what produced the 0.952. Bits-per-pixel separated that
benchmark at AUC 0.008 -- but it was reading PNG-vs-JPEG, a Channel A fact, while
being reported as though it were a pixel measurement. Any Channel A quantity that
leaks into a pixel benchmark inflates it and cannot be detected after the fact.

So: probe the format explicitly, report it as its own declared channel, and hand
the observers only parity-normalised pixels.

WHAT "THE RIGHT METHODS FOR IT" MEANS IN PRACTICE
-------------------------------------------------
  JPEG source   Already 8x8 block-quantised. Its high-frequency tail is
                truncated, which is why the balance law could not be fitted
                (FOLDING_MATCHED_BENCHMARK: sigma degenerate in 49% of cells).
                Re-encoding is nearly free of extra damage at equal-or-lower
                quality. Block grid position is recoverable and is itself a
                manipulation cue -- a spliced region has a misaligned grid.
  PNG / WebP-   Never quantised. Carries the generator's full frequency
  lossless      content. Must be put through the SAME encoder as the JPEG class
                before any spectral comparison, or the comparison is
                PNG-vs-JPEG.
  WebP lossy    Different transform, different artifacts. Treat as its own
                source class; do not assume JPEG reasoning transfers.
  HEIC/AVIF     Phone-native now. Needs pillow-heif. Untested here.
  RAW           The only format where optics measures (chromatic aberration,
                the blur/spectrum balance law) are testable, because raw
                converters strip lens correction from everything else.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ExifTags

# Standard Annex-K luminance table, used as the reference for quality estimation
_STD_Y = np.array([
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99],
    float)


def estimate_jpeg_quality(qt):
    """Approximate the IJG quality setting from a luminance quantisation table.

    IJG builds the table as  table = std * scale / 100  where
        quality < 50 :  scale = 5000 / quality
        quality >= 50:  scale = 200 - 2 * quality
    so inverting from an observed scale s = 100 * median(table / std):
        s > 100 :  quality = 5000 / s          (the low-quality branch)
        s <= 100:  quality = (200 - s) / 2     (the high-quality branch)

    The first version of this had the two branches swapped, which reported
    quality 838 for a phone JPEG and 2825 for a Midjourney re-save -- numbers
    outside the 1-100 range the scale is defined on. A quality estimate that
    can exceed 100 is not a borderline result, it is a broken formula; the
    output range is the check.
    """
    q = np.asarray(qt, float).ravel()
    n = min(len(q), 64)
    s = float(np.median(q[:n] / _STD_Y[:n])) * 100.0
    qual = 5000.0 / max(s, 1e-6) if s > 100.0 else (200.0 - s) / 2.0
    return round(float(np.clip(qual, 1.0, 100.0)), 1)


def probe(path):
    """Channel A. Everything about the container, nothing about the content."""
    im = Image.open(path)
    out = {"path": path, "format": im.format, "mode": im.mode,
           "stored_size": list(im.size),
           "filesize_bytes": os.path.getsize(path),
           "filesize_bpp": os.path.getsize(path) * 8 / float(im.size[0] * im.size[1])}

    e = im.getexif()
    tags = {ExifTags.TAGS.get(k, k): v for k, v in e.items()}
    out["has_exif"] = bool(e)
    out["exif_tag_count"] = len(e)
    out["orientation"] = e.get(274)
    out["camera_make"] = str(tags.get("Make", "")) or None
    out["camera_model"] = str(tags.get("Model", "")) or None
    out["software"] = str(tags.get("Software", "")) or None
    out["has_icc"] = "icc_profile" in im.info
    try:
        out["has_makernote"] = bool(e.get_ifd(0x8769).get(0x927C))
    except Exception:
        out["has_makernote"] = False

    if im.format == "JPEG":
        qt = getattr(im, "quantization", {}) or {}
        out["jpeg_n_tables"] = len(qt)
        if 0 in qt:
            out["jpeg_quality_est"] = estimate_jpeg_quality(qt[0])
            out["jpeg_qt_dc"] = int(np.asarray(qt[0]).ravel()[0])
            out["jpeg_qt_mean"] = float(np.mean(qt[0]))
        out["jpeg_subsampling"] = im.info.get("subsampling")
        out["jpeg_progressive"] = bool(im.info.get("progressive"))
    else:
        out["jpeg_n_tables"] = 0
    return out


def source_class(p):
    """Coarse routing label. What kind of starting condition is this?"""
    if p["format"] in ("PNG", "TIFF") or p["mode"] in ("RGBA", "I;16"):
        return "lossless_native"
    if p["format"] == "WEBP":
        return "webp"
    if p["format"] == "JPEG":
        if p.get("has_makernote") and p.get("camera_make"):
            return "camera_jpeg"
        if p.get("has_exif") and p.get("camera_make"):
            return "camera_jpeg_stripped"
        return "recompressed_jpeg"
    return "unknown"


def report(paths, label=""):
    rows = [probe(p) for p in paths]
    for r in rows:
        r["source_class"] = source_class(r)
    if label:
        from collections import Counter
        print(f"\n  {label}  n={len(rows)}")
        for k, v in Counter(r["source_class"] for r in rows).most_common():
            print(f"    {k:<24}{v}")
        q = [r.get("jpeg_quality_est") for r in rows if r.get("jpeg_quality_est")]
        if q:
            print(f"    jpeg quality est       median {np.median(q):.0f} "
                  f"(range {min(q):.0f}-{max(q):.0f})")
        print(f"    has EXIF               {sum(r['has_exif'] for r in rows)}/{len(rows)}")
        print(f"    has camera make        "
              f"{sum(bool(r['camera_make']) for r in rows)}/{len(rows)}")
        print(f"    has maker note         "
              f"{sum(r['has_makernote'] for r in rows)}/{len(rows)}")
        print(f"    filesize bpp median    "
              f"{np.median([r['filesize_bpp'] for r in rows]):.2f}"
              f"   <-- CHANNEL A ONLY. Never feed this to a pixel benchmark.")
    return rows
