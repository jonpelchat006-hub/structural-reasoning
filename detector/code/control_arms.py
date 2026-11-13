"""
control_arms.py -- the control arms the photo benchmark never had.

The question is not "do these features separate Jonathan's real photos from his
AI images". They do, at |AUC-0.5| ~ 0.35. The question is whether that number
means anything, and the only way to find out is to give the features a job where
the correct answer is ALREADY KNOWN to be chance:

  TARGET      his real photos      vs  his AI images        (both, so we know
                                                             the scale)
  CONTROL 1   web real portrait    vs  web real landscape   BOTH REAL -- pure
              (content)                                     content difference
  CONTROL 2   his phone photos     vs  web real photos      BOTH REAL -- pure
              (population)                                  device/processing
  CONTROL 3   his real close-ups   vs  his real scenes      BOTH REAL, ONE PHONE
              (content, 1 device)                           -- content only

Everything runs through the same full-parity path used in arm D of parity_arms:
EXIF orientation applied, centre-cropped to square, resized to 448x448, one
identical JPEG q85 encode. If a feature scores as high on a control as on the
target, then on this data it is not a provenance detector. That is the whole
test.
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mixedness_observer as mx
import nonlocal_observer as nl
import spectral_observer as sp

U = "/mnt/user-data/uploads/Vesica AI/AI Detector"
SQ, Q = 448, 85

# Jonathan's real photos, bucketed by content from a visual pass over the set.
HIS_CLOSEUP = {  # face or animal filling the frame, shallow depth of field
    "20161216_132803", "20230405_201827", "20230507_162100",
    "20250817_170808", "20260623_075030", "20260711_005016",
}


def prep(src, dst):
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    im = im.resize((SQ, SQ), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=Q)
    buf.seek(0)
    Image.open(buf).save(dst, "JPEG", quality=Q)
    return dst


def feats(path):
    f = {}
    for k, v in sp.features(path).items():
        if isinstance(v, (int, float)):
            f["spectral." + k] = float(v)
    for k, v in mx.features(path).items():
        if isinstance(v, (int, float)):
            f["mixed." + k] = float(v)
    n = nl.analyse(path)
    for k in ("nonlocal_err_fine", "nonlocal_err_coarse", "nonlocal_asymmetry"):
        if isinstance(n.get(k), (int, float)):
            f["window." + k] = float(n[k])
    return f


def auc(pos, neg):
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


CACHE = {}


def group(paths, tag):
    out = []
    d = os.path.join("_ctrl", tag)
    os.makedirs(d, exist_ok=True)
    for p in paths:
        if p in CACHE:
            out.append(CACHE[p])
            continue
        dst = os.path.join(d, os.path.splitext(os.path.basename(p))[0] + ".jpg")
        f = feats(prep(p, dst))
        CACHE[p] = f
        out.append(f)
    return out


def main():
    his_real = sorted(glob.glob(f"{U}/real photos/*"))
    his_ai = sorted(glob.glob(f"{U}/ai photos/*"))
    web_port = sorted(glob.glob(f"{U}/more photos/real portrait/*"))
    web_land = sorted(glob.glob(f"{U}/more photos/real landscape/*"))

    stem = lambda p: os.path.splitext(os.path.basename(p))[0]
    his_close = [p for p in his_real if stem(p) in HIS_CLOSEUP]
    his_scene = [p for p in his_real if stem(p) not in HIS_CLOSEUP]

    print(f"his real {len(his_real)}  his ai {len(his_ai)}  "
          f"web portrait {len(web_port)}  web landscape {len(web_land)}")
    print(f"his close-ups {len(his_close)}  his scenes {len(his_scene)}")

    G = {}
    for tag, paths in (("his_real", his_real), ("his_ai", his_ai),
                       ("web_port", web_port), ("web_land", web_land)):
        G[tag] = group(paths, tag)
        print(f"  featurised {tag}", flush=True)
    G["his_close"] = group(his_close, "his_close")
    G["his_scene"] = group(his_scene, "his_scene")

    ARMS = [
        ("TARGET    his real vs his AI", "his_real", "his_ai"),
        ("CONTROL1  web portrait vs web landscape (both real)", "web_port", "web_land"),
        ("CONTROL2  his phone vs web real portrait (both real)", "his_real", "web_port"),
        ("CONTROL3  his close-ups vs his scenes (both real, 1 phone)",
         "his_close", "his_scene"),
    ]
    keys = sorted({k for v in G.values() for r in v for k in r})
    tab = {}
    for lab, a, b in ARMS:
        tab[lab] = {k: auc([r.get(k, np.nan) for r in G[a]],
                           [r.get(k, np.nan) for r in G[b]]) for k in keys}

    print(f"\n{'='*104}\n|AUC - 0.5| UNDER FULL PARITY.  A control column as high as the "
          f"target column means\nthe feature is not reading provenance.\n{'='*104}")
    hdr = ["TARGET", "CTRL1 content", "CTRL2 device", "CTRL3 content/1dev"]
    print(f"{'feature':<30}" + "".join(f"{h:>19}" for h in hdr) + "   verdict")
    rows = []
    for k in keys:
        v = [abs(tab[lab][k] - 0.5) if np.isfinite(tab[lab][k]) else np.nan
             for lab, _, _ in ARMS]
        worst_ctrl = np.nanmax(v[1:])
        verdict = ("CONFOUNDED" if worst_ctrl >= v[0] - 0.02
                   else "survives" if v[0] >= 0.25 else "weak")
        rows.append((k, v, worst_ctrl, verdict))
        print(f"{k:<30}" + "".join(f"{x:>19.3f}" if np.isfinite(x) else f"{'-':>19}"
                                   for x in v) + f"   {verdict}")

    print(f"\n{'-'*104}")
    print("HEADLINE")
    best_t = max(rows, key=lambda r: r[1][0] if np.isfinite(r[1][0]) else -1)
    print(f"  strongest feature on the target      : {best_t[0]} at "
          f"|AUC-0.5| {best_t[1][0]:.3f}")
    print(f"  ...and its best control              : {best_t[2]:.3f}")
    n_conf = sum(1 for r in rows if r[3] == "CONFOUNDED")
    print(f"  features whose control matches target: {n_conf}/{len(rows)}")
    surv = [r for r in rows if r[3] == "survives"]
    print(f"  features that survive all controls   : "
          f"{', '.join(r[0] for r in surv) if surv else 'NONE'}")

    json.dump({lab: tab[lab] for lab, _, _ in ARMS},
              open("control_arms.json", "w"), indent=2, default=str)
    print("\nwrote control_arms.json")


if __name__ == "__main__":
    main()
