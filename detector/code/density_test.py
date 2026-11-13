"""
density_test.py -- put the density observer through the gate that killed 15 features.

Two questions, in order:

  1. CLASS SEPARATION, with the real-vs-real control attached from the start.
     No density feature counts unless it beats every control. Pre-registered
     prediction (density_observer docstring): every `*_mean` fails; the
     scale-free `noise_floor_ratio` is the only candidate.

  2. LOCALISATION on the 13 rebuilt seam pairs, against the untouched-original
     control arm. This is the question the project actually needs answered.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import density_observer as D
import format_probe as FP
from image_io import parity

U = "/mnt/user-data/uploads/Vesica AI/AI Detector"
SQ = 448
HIS_CLOSEUP = {"20161216_132803", "20230405_201827", "20230507_162100",
               "20250817_170808", "20260623_075030", "20260711_005016"}


def auc(pos, neg):
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def main():
    his_real = sorted(glob.glob(f"{U}/real photos/*"))
    his_ai = sorted(glob.glob(f"{U}/ai photos/*"))
    web_p = sorted(glob.glob(f"{U}/more photos/real portrait/*"))
    web_l = sorted(glob.glob(f"{U}/more photos/real landscape/*"))

    print("=" * 96)
    print("CHANNEL A -- the file evidence, reported separately and never mixed in")
    print("=" * 96)
    FP.report(his_real, "his real photos")
    FP.report(his_ai, "his ai photos")
    FP.report(web_p + web_l, "web real photos")

    print(f"\n{'='*96}")
    print("CHANNEL B -- density from pixels only, after full parity "
          "(EXIF, square 448, one q85 encode)")
    print("=" * 96)

    def grp(paths, tag):
        out = []
        for p in paths:
            dst = os.path.join("_dens", tag,
                               os.path.splitext(os.path.basename(p))[0] + ".jpg")
            out.append(D.features(parity(p, dst, square=SQ)))
        print(f"  featurised {tag} ({len(out)})", flush=True)
        return out

    stem = lambda p: os.path.splitext(os.path.basename(p))[0]
    Gp = {"his_real": grp(his_real, "his_real"), "his_ai": grp(his_ai, "his_ai"),
          "web_p": grp(web_p, "web_p"), "web_l": grp(web_l, "web_l")}
    Gp["his_close"] = [f for p, f in zip(his_real, Gp["his_real"])
                       if stem(p) in HIS_CLOSEUP]
    Gp["his_scene"] = [f for p, f in zip(his_real, Gp["his_real"])
                       if stem(p) not in HIS_CLOSEUP]

    ARMS = [("TARGET", "his_real", "his_ai"),
            ("CTRL1 content", "web_p", "web_l"),
            ("CTRL2 device", "his_real", "web_p"),
            ("CTRL3 content/1dev", "his_close", "his_scene")]
    keys = sorted({k for v in Gp.values() for r in v for k in r})
    tab = {lab: {k: auc([r.get(k, np.nan) for r in Gp[a]],
                        [r.get(k, np.nan) for r in Gp[b]]) for k in keys}
           for lab, a, b in ARMS}

    print(f"\n{'feature':<26}" + "".join(f"{a[0]:>20}" for a in ARMS) + "   verdict")
    surv = []
    for k in keys:
        v = [abs(tab[lab][k] - 0.5) if np.isfinite(tab[lab][k]) else np.nan
             for lab, _, _ in ARMS]
        wc = np.nanmax(v[1:])
        ok = np.isfinite(v[0]) and v[0] >= 0.25 and wc < v[0] - 0.02
        if ok:
            surv.append(k)
        vd = "CLEARS CONTROLS" if ok else (
            "clean but weak" if wc < v[0] - 0.02 else "CONFOUNDED")
        print(f"{k:<26}" + "".join(f"{x:>20.3f}" if np.isfinite(x) else f"{'-':>20}"
                                   for x in v) + f"   {vd}")
    print(f"\n  raw AUC direction for the pre-registered candidate: "
          f"noise_floor_ratio = {tab['TARGET'].get('noise_floor_ratio', float('nan')):.3f}"
          f"   (>0.5 means REAL is higher, as predicted)")
    print(f"  features clearing every control: "
          f"{', '.join(surv) if surv else 'NONE'}")

    # ---------------------------------------------------------------- localisation
    print(f"\n{'='*96}\nLOCALISATION on the 13 rebuilt seam pairs "
          f"(trimmed within-image baseline)\n{'='*96}")
    rows = json.load(open("seam/index.json"))
    res = []
    for r in rows:
        m = np.load(f"seam/{r['name']}_mask.npy")
        h, w = m.shape
        cov = np.array([m[i * h // D.G:(i + 1) * h // D.G,
                          j * w // D.G:(j + 1) * w // D.G].mean()
                        for i in range(D.G) for j in range(D.G)])
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(D.G * D.G, bool)
            sel[int(np.argmax(cov))] = True
        if sel.all():
            continue
        row = {"name": r["name"], "frac": r["mask_frac"]}
        for kind in ("edit", "orig"):
            wi = D.within_image(f"seam/{r['name']}_{kind}.jpg")
            for k, v in wi.items():
                row[f"{kind}.{k}"] = auc(v[sel], v[~sel])
        res.append(row)
        print(f"  {r['name']} ({100*r['mask_frac']:.2f}%)", flush=True)

    print(f"\n{'channel':<22}{'EDITED':>9}{'>chance':>9}{'CONTROL':>10}"
          f"{'>chance':>9}{'edit-control':>14}{'corr w/ size':>14}")
    sz = np.array([r["frac"] for r in res])
    out = {}
    for k in ("dens_lossy_dev", "dens_lossless_dev", "dens_noise_dev"):
        e = np.array([r[f"edit.{k}"] for r in res], float)
        c = np.array([r[f"orig.{k}"] for r in res], float)
        g = np.isfinite(e) & np.isfinite(c)
        out[k] = {"edit": float(e[g].mean()), "control": float(c[g].mean()),
                  "above": int((e[g] > 0.5).sum()), "n": int(g.sum()),
                  "corr_size": float(np.corrcoef(sz[g], e[g])[0, 1])}
        print(f"{k:<22}{e[g].mean():>9.3f}{(e[g]>0.5).sum():>6}/{g.sum():<3}"
              f"{c[g].mean():>10.3f}{(c[g]>0.5).sum():>6}/{g.sum():<3}"
              f"{e[g].mean()-c[g].mean():>+14.3f}{out[k]['corr_size']:>+14.2f}")

    print(f"\n{'-'*96}\nPER-IMAGE, dens_noise_dev, sorted by edit size")
    print(f"{'image':<22}{'edit%':>8}{'EDITED':>9}{'CONTROL':>10}")
    for r in sorted(res, key=lambda x: x["frac"]):
        print(f"{r['name']:<22}{100*r['frac']:>7.2f}%"
              f"{r.get('edit.dens_noise_dev', np.nan):>9.2f}"
              f"{r.get('orig.dens_noise_dev', np.nan):>10.2f}")

    json.dump({"class_separation": tab, "localisation": out, "rows": res},
              open("density_results.json", "w"), indent=2, default=str)
    print("\nwrote density_results.json")


if __name__ == "__main__":
    main()
