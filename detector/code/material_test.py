"""
material_test.py -- does a per-material baseline beat a whole-image one?

Head to head on the 13 rebuilt seam pairs, same measures, same masks, same
control arm. The ONLY thing that changes is what each cell is compared against:

    global   the image's own trimmed baseline over all 36 cells   (seam_rerun)
    material the trimmed baseline of the cells sharing that cell's
             colour+texture cluster                                (this file)

Bars to beat, from seam_rerun on the rebuilt masks:
    spec_dev     edited 0.582  control 0.428  delta +0.154  corr(size) -0.58
    nl_asym_dev  edited 0.577  control 0.517  delta +0.059  corr(size) -0.02
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import material_context as M
import seam_rerun as S
import within_image_observers as W

FEATS = ["noise_dev", "sharp_dev", "spec_dev", "nl_asym_dev"]


def main():
    rows = json.load(open("seam/index.json"))
    res = []
    for r in rows:
        mask = np.load(f"seam/{r['name']}_mask.npy")
        cov = W.coverage(mask)
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(W.G * W.G, bool)
            sel[int(np.argmax(cov))] = True
        if sel.all():
            continue
        row = {"name": r["name"], "frac": r["mask_frac"]}
        for kind in ("edit", "orig"):
            p = f"seam/{r['name']}_{kind}.jpg"
            raw = S.raw_measure(p)
            lab = M.material_labels(p)
            if kind == "edit":
                occ = M.occupancy(lab)
                row["clusters"] = occ
                # how much of the edit sits inside one cluster
                big = max(occ.values())
                row["max_cluster"] = big
                inside = [int(((lab == c) & sel).sum()) for c in occ]
                row["edit_cluster_share"] = float(
                    max(inside[i] / max(occ[c], 1) for i, c in enumerate(occ)))
            for f in FEATS:
                row[f"{kind}.global.{f}"] = W.auc(S.dev_trim(raw[f])[sel],
                                                  S.dev_trim(raw[f])[~sel])
                dm = M.dev_material(raw[f], lab)
                row[f"{kind}.material.{f}"] = W.auc(dm[sel], dm[~sel])
        res.append(row)
        print(f"  {r['name']} ({100*row['frac']:.2f}%) clusters={row['clusters']}",
              flush=True)

    sz = np.array([r["frac"] for r in res])
    print(f"\n{'='*98}\nGLOBAL BASELINE vs MATERIAL BASELINE "
          f"({len(res)} pairs)\n{'='*98}")
    print(f"{'measure':<14}{'baseline':<11}{'EDITED':>9}{'>chance':>9}"
          f"{'CONTROL':>10}{'>chance':>9}{'edit-control':>14}{'corr w/ size':>14}")
    summ = {}
    for f in FEATS:
        for b in ("global", "material"):
            e = np.array([r[f"edit.{b}.{f}"] for r in res], float)
            c = np.array([r[f"orig.{b}.{f}"] for r in res], float)
            k = np.isfinite(e) & np.isfinite(c)
            if k.sum() < 3:
                continue
            summ[f"{f}.{b}"] = {"edit": float(e[k].mean()),
                                "control": float(c[k].mean()),
                                "delta": float(e[k].mean() - c[k].mean()),
                                "above": int((e[k] > 0.5).sum()), "n": int(k.sum()),
                                "corr_size": float(np.corrcoef(sz[k], e[k])[0, 1])}
            print(f"{f:<14}{b:<11}{e[k].mean():>9.3f}"
                  f"{(e[k]>0.5).sum():>6}/{k.sum():<3}{c[k].mean():>10.3f}"
                  f"{(c[k]>0.5).sum():>6}/{k.sum():<3}"
                  f"{e[k].mean()-c[k].mean():>+14.3f}"
                  f"{summ[f'{f}.{b}']['corr_size']:>+14.2f}")

    print(f"\n{'-'*98}\nDID THE MATERIAL BASELINE HELP?")
    for f in FEATS:
        a, b = summ.get(f"{f}.global"), summ.get(f"{f}.material")
        if not a or not b:
            continue
        d = b["delta"] - a["delta"]
        print(f"  {f:<14} edit-control {a['delta']:+.3f} -> {b['delta']:+.3f} "
              f"({d:+.3f})   above chance {a['above']}/{a['n']} -> "
              f"{b['above']}/{b['n']}   corr(size) {a['corr_size']:+.2f} -> "
              f"{b['corr_size']:+.2f}   {'BETTER' if d > 0.03 else 'no gain'}")

    print(f"\n{'-'*98}\nPER-IMAGE, spec_dev")
    print(f"{'image':<22}{'edit%':>8}{'glob E':>9}{'mat E':>8}{'glob C':>9}"
          f"{'mat C':>8}{'largest cluster':>17}")
    for r in sorted(res, key=lambda x: x["frac"]):
        print(f"{r['name']:<22}{100*r['frac']:>7.2f}%"
              f"{r['edit.global.spec_dev']:>9.2f}{r['edit.material.spec_dev']:>8.2f}"
              f"{r['orig.global.spec_dev']:>9.2f}{r['orig.material.spec_dev']:>8.2f}"
              f"{r['max_cluster']:>14}/36")

    json.dump({"summary": summ, "rows": res},
              open("material_results.json", "w"), indent=2, default=str)
    print("\nwrote material_results.json")


if __name__ == "__main__":
    main()
