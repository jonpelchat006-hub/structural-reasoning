#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
galaxy_codon_test.py  --  the observer -> codon/solvent recipe test
(FOLDING_GALAXY_BRIDGE.md, experiment 1)

IDEA
----
The colony treats each tool as a codon in a rank-3 tensor over 4 minerals =
4 solvent axes (water/alcohol/oil/liquidMetal). The detector's four observer
FAMILIES are the natural four axes. So each image's "recipe" is a 4-axis
solvent composition, and its dominant axis is a coarse codon. Two claims:

  C1 (recipe separates): within a content bucket, the 4-axis recipe should
     separate real vs fake better than any single material did (nearest-
     centroid, leave-one-out -- no fitted threshold, no label leakage).
  C2 (routing recovers .14): the two-atom detector's ERRORS should be
     recoverable by recipe -- i.e. the composition-nearest class centroid
     classifies the errors the scalar verdict missed. This is deposit-
     routing's "transport to the body whose composition gap matches",
     applied to the residual.

HYPOTHESIS MAPPING (observer family -> solvent axis) -- editable, not sacred:
     window/nonlocal  -> W water      (identity / relational)
     bridge/environment -> A alcohol  (i: translation / the bridge)
     mixed/mixedness  -> O oil         (j: insulation / texture)
     spectral         -> M liquidMetal (k: thermal / frequency conduction)

DATA
----
bench_matched.json : 58 content-matched images (landscape/portrait buckets),
                     19 features across the 4 families, per image.
free_run.json      : the two-atom calibration (i=spectral.slope,
                     j=window.nonlocal_asymmetry; mean/std/sign). The verdict
                     is reconstructed as sign(z_i + z_j) -- authentic if > 0.

HONEST BOUNDS
-------------
n per bucket is ~12-21/class: |AUC-0.5|~0.15 is the noise floor. Nearest-
centroid LOO at this n is a look, not a proof. The calibration was fit on the
parity-29 and applied to the 58 -- a mild set mismatch, flagged. The family->
solvent mapping is a hypothesis; the separation/recovery result does NOT depend
on which letter each family gets (the 4-vector is the same), only the codon
labels do.

USAGE
-----
python galaxy_codon_test.py --bench bench_matched.json --free free_run.json
(defaults look for both in the current dir.)
Stdlib only.
"""

import json, math, argparse, os

FAMILIES = {
    "W_window":   {"solvent": "water",       "prefix": "window."},
    "A_bridge":   {"solvent": "alcohol",     "prefix": "bridge."},
    "O_mixed":    {"solvent": "oil",         "prefix": "mixed."},
    "M_spectral": {"solvent": "liquidMetal", "prefix": "spectral."},
}
CODON_LETTER = {"W_window": "W", "A_bridge": "A", "O_mixed": "O", "M_spectral": "M"}


def load(bench_path, free_path):
    rows = json.load(open(bench_path))["rows"]
    free = json.load(open(free_path))
    return rows, free["calibration"]


def two_atom_pred(f, cal):
    """Reconstruct the two-atom verdict from free_run calibration.
    pred 'real' if sign(z_i + z_j) > 0 (authentic), else 'ai'. None if missing."""
    def z(side):
        c = cal[side]; v = f.get(c["feature"])
        if v is None or (isinstance(v, float) and v != v):
            return None
        s = c["std"] or 1e-9
        return c["sign"] * (v - c["mean"]) / s
    zi, zj = z("i"), z("j")
    if zi is None or zj is None:
        return None, None
    scalar = (zi + zj) / math.sqrt(2)
    return ("real" if scalar > 0 else "ai"), scalar


def zscore_bucket(rows):
    """Per-bucket z-score every feature over all images in the bucket.
    Returns {feat: (mean,std)} ignoring NaN/missing."""
    feats = set()
    for r in rows:
        feats |= set(r["f"].keys())
    stats = {}
    for ft in feats:
        vals = [r["f"][ft] for r in rows
                if ft in r["f"] and isinstance(r["f"][ft], (int, float))
                and r["f"][ft] == r["f"][ft]]
        if not vals:
            stats[ft] = (0.0, 1.0); continue
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / max(1, len(vals) - 1)
        stats[ft] = (m, math.sqrt(var) if var > 0 else 1.0)
    return stats


def recipe_vector(f, stats):
    """4-axis composition: mean of per-bucket z-scores within each family.
    Missing features impute to 0 (bucket mean)."""
    vec = {}
    for fam, meta in FAMILIES.items():
        zs = []
        for ft, v in f.items():
            if not ft.startswith(meta["prefix"]):
                continue
            if not isinstance(v, (int, float)) or v != v:
                continue
            m, sd = stats.get(ft, (0.0, 1.0))
            zs.append((v - m) / (sd or 1e-9))
        vec[fam] = (sum(zs) / len(zs)) if zs else 0.0
    return vec


def dist(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in a))


def centroid(vecs):
    keys = list(FAMILIES.keys())
    n = len(vecs)
    return {k: (sum(v[k] for v in vecs) / n if n else 0.0) for k in keys}


def analyse_bucket(rows, cal):
    stats = zscore_bucket(rows)
    for r in rows:
        r["_vec"] = recipe_vector(r["f"], stats)
        p, s = two_atom_pred(r["f"], cal)
        r["_pred"], r["_scalar"] = p, s
        r["_codon"] = CODON_LETTER[max(r["_vec"], key=lambda k: r["_vec"][k])]

    real = [r for r in rows if r["label"] == "real"]
    ai   = [r for r in rows if r["label"] == "ai"]

    # C1: nearest-centroid LOO on the 4-axis recipe
    correct = 0; total = 0
    for r in rows:
        others_real = [x["_vec"] for x in real if x is not r]
        others_ai   = [x["_vec"] for x in ai   if x is not r]
        if not others_real or not others_ai:
            continue
        cr, ca = centroid(others_real), centroid(others_ai)
        pred = "real" if dist(r["_vec"], cr) < dist(r["_vec"], ca) else "ai"
        correct += (pred == r["label"]); total += 1
        r["_recipe_pred"] = pred
    recipe_acc = correct / total if total else float("nan")

    # two-atom accuracy + errors (reconstructed)
    verdicted = [r for r in rows if r["_pred"] is not None]
    ta_correct = sum(1 for r in verdicted if r["_pred"] == r["label"])
    ta_acc = ta_correct / len(verdicted) if verdicted else float("nan")
    errors = [r for r in verdicted if r["_pred"] != r["label"]]

    # C2: does the recipe recover the two-atom errors?
    recov = [r for r in errors if r.get("_recipe_pred") == r["label"]]

    # dominant-codon distribution per class
    def codon_hist(sub):
        h = {}
        for r in sub:
            h[r["_codon"]] = h.get(r["_codon"], 0) + 1
        return h

    return {
        "n_real": len(real), "n_ai": len(ai),
        "recipe_acc": recipe_acc,
        "ta_acc": ta_acc, "n_err": len(errors), "n_recovered": len(recov),
        "codon_real": codon_hist(real), "codon_ai": codon_hist(ai),
        "errors": [(os.path.basename(r["path"])[:36], r["label"], r["_pred"],
                    r.get("_recipe_pred"), r["_codon"]) for r in errors],
    }


def fmt(x, nd=3):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "n/a"
        return f"{x:.{nd}f}"
    except Exception:
        return str(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="bench_matched.json")
    ap.add_argument("--free",  default="free_run.json")
    a = ap.parse_args()
    rows, cal = load(a.bench, a.free)

    buckets = sorted(set(r.get("bucket", "?") for r in rows))
    L = []
    P = L.append
    P("=" * 70)
    P("  OBSERVER -> CODON / SOLVENT RECIPE TEST  (FOLDING_GALAXY_BRIDGE 1)")
    P("=" * 70)
    P(f"images: {len(rows)}  buckets: {buckets}")
    P("family->solvent: window=W(water) bridge=A(alcohol) mixed=O(oil) spectral=M(liquidMetal)")
    P("")
    agg = {"recipe": [], "ta": [], "err": 0, "rec": 0}
    for b in buckets:
        sub = [r for r in rows if r.get("bucket") == b]
        res = analyse_bucket(sub, cal)
        P(f"=== bucket: {b}   (real {res['n_real']} / ai {res['n_ai']}) ===")
        P(f"  two-atom verdict accuracy (reconstructed): {fmt(res['ta_acc'])}"
          f"   errors: {res['n_err']}")
        P(f"  RECIPE nearest-centroid LOO accuracy      : {fmt(res['recipe_acc'])}"
          f"   <- C1")
        P(f"  errors RECOVERED by recipe routing        : "
          f"{res['n_recovered']}/{res['n_err']}   <- C2")
        P(f"  dominant-codon | real: {res['codon_real']}")
        P(f"  dominant-codon | ai  : {res['codon_ai']}")
        if res["errors"]:
            P("  two-atom errors (img | true | 2atom | recipe | codon):")
            for name, tl, pr, rp, cd in res["errors"]:
                flag = "RECOVERED" if rp == tl else "missed"
                P(f"     {name:36s} {tl:4s} {pr:4s} {str(rp):4s} {cd}  {flag}")
        P("")
        if res["recipe_acc"] == res["recipe_acc"]:
            agg["recipe"].append(res["recipe_acc"])
        if res["ta_acc"] == res["ta_acc"]:
            agg["ta"].append(res["ta_acc"])
        agg["err"] += res["n_err"]; agg["rec"] += res["n_recovered"]

    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    P("=== overall (bucket-mean) ===")
    P(f"  two-atom accuracy : {fmt(mean(agg['ta']))}")
    P(f"  recipe accuracy   : {fmt(mean(agg['recipe']))}")
    P(f"  errors recovered  : {agg['rec']}/{agg['err']}")
    P("")
    P("READ: C1 holds if recipe accuracy clears the single-material noise floor")
    P("(~0.5+-0.15 at this n) and ideally beats the two-atom verdict. C2 holds if")
    P("recipe routing recovers a real fraction of the errors. Small n -- a look.")
    P("=" * 70)
    text = "\n".join(L)
    print(text)
    with open("galaxy_codon_report.txt", "w", encoding="utf-8") as fh:
        fh.write(text + "\n")


if __name__ == "__main__":
    main()
