"""
recon_control.py -- put the reconstruction axis through the gate that killed 28 features.

WHY THIS ONE IS WORTH THE COMPUTE
---------------------------------
Everything the field's localisation models are good at, they are good at because a
COMPOSITED patch leaves a seam. TGIF2, pixel F1: CAT-Net 0.89 spliced -> 0.02 fully
regenerated. TruFor 0.75 -> 0.14. When the whole frame goes through a VAE and is
re-encoded, there is no local discontinuity left to find.

But a fully regenerated image is not LESS detectable in principle -- it is more
ON-MANIFOLD. `roundtrip_fixed_point` (FOLDING_RECONSTRUCTION) measures exactly
that: apply our own draw operator and see whether the image moves. Generated
content barely moves because it already IS what a piecewise-smooth fill engine
would have drawn.

So the prediction is that these two tools fail in OPPOSITE regimes:

    composited edit      local seam present   -> seam models strong, manifold weak
    fully regenerated    no local seam        -> seam models dead, manifold STRONGEST

That is the ideal condition for a router. It is also the only structural argument
in this project for why a framework-derived measure would beat the field's models
somewhere rather than everywhere.

WHY IT IS NOT YET AN ASSET
--------------------------
`roundtrip_fixed_point` scored AUC 0.848 signed, |d| 0.348 -- the strongest measure
in that benchmark. But that benchmark was 12 real phone JPEGs vs 17 AI PNGs: it is
THE SET FOLDING_PHOTO_SET_AUTOPSY destroyed. Stored aspect ratio separated those
classes at AUC 1.000 and bits-per-pixel at 0.008. The number has never seen parity
or a real-vs-real control.

Prior should be low: 28 of 28 free features have died at this gate.

PRE-REGISTERED
--------------
  1. Most likely outcome, given the base rate: it is another genre detector. A
     smooth studio portrait is closer to a piecewise-smooth drawable manifold than
     a foliage landscape is, for reasons that have nothing to do with provenance.
     That is the CTRL1 arm and it is the one to watch.
  2. If it clears CTRL1, it is structurally different from the 28 that died --
     those were all STATIC statistics (sharpness, spectrum, density). This one
     applies an OPERATOR and measures displacement. Different kind of quantity,
     so the base rate may not apply to it.
  3. Direction: AI should score HIGHER (closer to a fixed point). Raw AUC < 0.5
     with real-as-positive.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

U = "/mnt/user-data/uploads/Vesica AI/AI Detector"
SQ = 448
KEYS = ["roundtrip_fixed_point", "return_at_low", "return_at_high",
        "thermal_slope", "seed_convergence", "nonmonotone_fraction"]


def prep_one(args):
    p, tag = args
    from image_io import parity
    dst = os.path.join("_recon", tag,
                       os.path.splitext(os.path.basename(p))[0] + ".jpg")
    return parity(p, dst, square=SQ)


def score_one(path):
    import reconstruction_observer as ro
    try:
        r = ro.analyse(path)
        if not r.ok:
            return path, None
        return path, {k: float(getattr(r, k)) for k in KEYS}
    except Exception as e:
        return path, {"_error": str(e)}


def auc(pos, neg):
    from scipy.stats import rankdata
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = rankdata(x)
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    groups = {
        "his_real": sorted(glob.glob(f"{U}/real photos/*")),
        "his_ai": sorted(glob.glob(f"{U}/ai photos/*")),
        "web_p": sorted(glob.glob(f"{U}/more photos/real portrait/*")),
        "web_l": sorted(glob.glob(f"{U}/more photos/real landscape/*")),
    }
    jobs = [(p, t) for t, ps in groups.items() for p in ps]
    print(f"{len(jobs)} images, full parity (EXIF + square {SQ} + one q85 encode)",
          flush=True)
    prepped = {}
    with ProcessPoolExecutor(max_workers=2) as ex:
        for (p, t), dst in zip(jobs, ex.map(prep_one, jobs)):
            prepped[dst] = t

    F = {t: [] for t in groups}
    done = 0
    with ProcessPoolExecutor(max_workers=2) as ex:
        for path, res in ex.map(score_one, list(prepped)):
            done += 1
            if res and "_error" not in res:
                F[prepped[path]].append(res)
            elif res:
                print(f"  ERROR {os.path.basename(path)}: {res['_error'][:60]}")
            if done % 10 == 0:
                print(f"  {done}/{len(prepped)}", flush=True)

    print(f"\n  usable: " + "  ".join(f"{t}={len(v)}" for t, v in F.items()))
    ARMS = [("TARGET  his real vs his AI", "his_real", "his_ai"),
            ("CTRL1   web portrait vs web landscape (BOTH REAL)", "web_p", "web_l"),
            ("CTRL2   his phone vs web portrait (BOTH REAL)", "his_real", "web_p")]

    print(f"\n{'='*92}")
    print("RECONSTRUCTION AXIS vs THE CONTROL ARMS  (|AUC-0.5|)")
    print("=" * 92)
    print(f"{'measure':<26}{'TARGET':>12}{'CTRL1 content':>16}{'CTRL2 device':>15}"
          f"{'raw target AUC':>17}   verdict")
    out = {}
    for k in KEYS:
        v, raws = [], None
        for lab, a, b in ARMS:
            r = auc([x[k] for x in F[a]], [x[k] for x in F[b]])
            v.append(abs(r - 0.5) if np.isfinite(r) else np.nan)
            if lab.startswith("TARGET"):
                raws = r
        wc = np.nanmax(v[1:])
        ok = np.isfinite(v[0]) and v[0] >= 0.25 and wc < v[0] - 0.02
        verdict = ("CLEARS CONTROLS" if ok else
                   "clean but weak" if wc < v[0] - 0.02 else "CONFOUNDED")
        out[k] = {"target": v[0], "ctrl1": v[1], "ctrl2": v[2],
                  "raw_target": raws, "verdict": verdict}
        print(f"{k:<26}" + "".join(f"{x:>12.3f}" if np.isfinite(x) else f"{'-':>12}"
                                   for x in [v[0]]) +
              f"{v[1]:>16.3f}{v[2]:>15.3f}{raws:>17.3f}   {verdict}")

    print(f"\n  prediction 3 was: AI closer to a fixed point, so raw target AUC < 0.5")
    print(f"  observed roundtrip_fixed_point raw AUC = "
          f"{out['roundtrip_fixed_point']['raw_target']:.3f}  "
          f"({'direction confirmed' if out['roundtrip_fixed_point']['raw_target'] < 0.5 else 'DIRECTION WRONG'})")
    surv = [k for k, r in out.items() if r["verdict"] == "CLEARS CONTROLS"]
    print(f"  clears every control: {', '.join(surv) if surv else 'NONE'}")
    print(f"\n  running tally of free features tested against real-vs-real controls: "
          f"{28 + len(KEYS)}, passed: {len(surv)}")

    json.dump({"results": out, "n": {t: len(v) for t, v in F.items()},
               "raw": {t: v for t, v in F.items()}},
              open("recon_control_results.json", "w"), indent=2, default=str)
    print("\nwrote recon_control_results.json")


if __name__ == "__main__":
    main()
