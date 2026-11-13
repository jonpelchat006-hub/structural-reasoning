"""
ratchet_committee.py -- test the ratchet on the instrument that actually works.

aggregation_test.py showed the max rule fails on the free per-cell measures. That
is not a verdict on the IDEA, it is a verdict on those instruments: a maximum has
no cancellation, so it faithfully amplifies whatever the loudest noise is, and
those measures' extremes are noise.

The ratchet needs an instrument whose extremes are EVIDENCE -- one that, when it
fires hard on one region, is usually right. The vision committee is the only thing
in this project with any claim to that property, and its per-cell scores for all
58 matched-benchmark images are already cached. So this costs nothing.

The cells are AUTHENTICITY scores, 0-100, where 0 = certainly synthetic. So
Jonathan's rule -- "once one spot reaches that fake bar i call the whole thing
fake" -- is the MINIMUM over cells, and "i can continue searching to see how fake
it is" is the count of cells below the bar.

  mean        average of all cells                    (what the product does now)
  min         the single most-fake cell               (the pure ratchet)
  bottom3     average of the 3 most-fake cells
  count@bar   how many cells fall below a fixed bar   (ratchet + severity)
  q10         10th percentile of cells

AUC is computed WITHIN each content bucket and pooled, the same stratification
the 0.932 was measured under, so portrait-vs-landscape cannot masquerade as
real-vs-AI.

PRE-REGISTERED
  1. If the ratchet is right, min / bottom3 / count@bar beat mean.
  2. Risk: with 16-64 cells per image, min is an extreme order statistic and a
     single hallucinated low cell on a REAL photo costs a false positive. If the
     committee is well behaved this shows up as bottom3 beating both mean and min
     -- the compromise that keeps most of the sensitivity and some averaging.
"""
from __future__ import annotations

import collections
import json

import numpy as np

CACHE = "/mnt/user-data/uploads/Vesica AI/AI Detector/committee_cache.json"
BARS = (10, 20, 30, 40, 50)


def auc(pos, neg):
    """Mann-Whitney AUC WITH tie handling (average ranks).

    The project's usual `np.argsort(np.argsort(x))` version breaks ties
    arbitrarily. verify.py flagged that as harmless because the continuous
    features had zero tied values -- but `count@bar` is a small integer and is
    0 for 54 of 58 images, so almost every value ties. Under the arbitrary-rank
    version those columns came back AUC 0.000 and looked like a perfect inverted
    detector. They are not; they are one number repeated. Use average ranks
    whenever a feature can be quantised.
    """
    pos = np.asarray([x for x in pos if np.isfinite(x)], float)
    neg = np.asarray([x for x in neg if np.isfinite(x)], float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    from scipy.stats import rankdata
    x = np.concatenate([pos, neg])
    r = rankdata(x)                      # average ranks for ties
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def strat_auc(rows, key):
    """AUC within each (label-free) content bucket, pooled by pair count."""
    num = den = 0.0
    per = {}
    for b in sorted({r["bucket"] for r in rows}):
        p = [r[key] for r in rows if r["bucket"] == b and r["label"] == "real"]
        q = [r[key] for r in rows if r["bucket"] == b and r["label"] == "ai"]
        a = auc(p, q)
        if not np.isfinite(a):
            continue
        per[b] = (round(a, 3), len(p) * len(q))
        num += a * len(p) * len(q)
        den += len(p) * len(q)
    return (num / den if den else np.nan), per


def main():
    c = json.load(open(CACHE))
    by_img = collections.defaultdict(list)
    for k, v in c.items():
        if not v or not v.get("cells"):
            continue
        path = k.rsplit("|", 2)[0]
        by_img[path].append(np.asarray(v["cells"], float))

    rows = []
    for path, samples in by_img.items():
        parts = path.split("/")
        label = "real" if "/real/" in path else "ai"
        bucket = parts[-2]
        # average the observers per cell first -- that IS the current committee,
        # and keeps this a test of the AGGREGATION OVER CELLS, nothing else
        n = min(len(s) for s in samples)
        cells = np.mean([s[:n] for s in samples], axis=0)
        r = {"path": path, "label": label, "bucket": bucket,
             "n_cells": len(cells), "n_obs": len(samples),
             "mean": float(cells.mean()),
             "min": float(cells.min()),
             "bottom3": float(np.sort(cells)[:3].mean()),
             "q10": float(np.quantile(cells, 0.10)),
             "median": float(np.median(cells))}
        for b in BARS:
            r[f"count@{b}"] = float((cells < b).sum())
            r[f"frac@{b}"] = float((cells < b).mean())
        rows.append(r)

    nb = collections.Counter((r["bucket"], r["label"]) for r in rows)
    print(f"{len(rows)} images with cached cell scores")
    for k, v in sorted(nb.items()):
        print(f"  {k[0]:<12}{k[1]:<6}{v}")
    print(f"  observers per image: "
          f"{collections.Counter(r['n_obs'] for r in rows).most_common()}")
    print(f"  cells per image:     "
          f"{collections.Counter(r['n_cells'] for r in rows).most_common()}")

    print(f"\n{'='*84}")
    print("AGGREGATION OVER CELLS -- stratified AUC, real vs AI")
    print("cells are AUTHENTICITY 0-100, so the ratchet is the MINIMUM")
    print("=" * 84)
    print(f"{'rule':<14}{'stratified AUC':>16}{'pooled':>10}   per-bucket")
    out = {}
    keys = ["mean", "median", "q10", "bottom3", "min"] + \
           [f"count@{b}" for b in BARS] + [f"frac@{b}" for b in BARS]
    base = None
    for k in keys:
        s, per = strat_auc(rows, k)
        p = auc([r[k] for r in rows if r["label"] == "real"],
                [r[k] for r in rows if r["label"] == "ai"])
        out[k] = {"stratified": s, "pooled": p, "per_bucket": per}
        if k == "mean":
            base = s
        mark = ""
        if base is not None and np.isfinite(s):
            d = abs(s - 0.5) - abs(base - 0.5)
            mark = f"   {d:+.3f} vs mean" + ("  <-- BETTER" if d > 0.015 else "")
        print(f"{k:<14}{s:>16.3f}{p:>10.3f}   {per}{mark}")

    print(f"\n{'-'*84}")
    print("SEVERITY -- does the count of failing cells track anything, or just fire?")
    for b in BARS:
        r_ = [r[f"count@{b}"] for r in rows if r["label"] == "real"]
        a_ = [r[f"count@{b}"] for r in rows if r["label"] == "ai"]
        print(f"  bar {b:>3}: real median {np.median(r_):>5.1f} cells   "
              f"ai median {np.median(a_):>5.1f}   "
              f"real images with ZERO failing cells "
              f"{sum(1 for x in r_ if x == 0)}/{len(r_)}   "
              f"ai {sum(1 for x in a_ if x == 0)}/{len(a_)}")

    print(f"\n{'-'*84}")
    print("THE FALSE-POSITIVE QUESTION the ratchet lives or dies on:")
    print("  if ONE cell below the bar condemns the image, how many REAL photos does")
    print("  that condemn?")
    print(f"  {'bar':>5}{'AI caught':>12}{'REAL wrongly condemned':>26}{'balanced acc':>14}")
    for b in BARS:
        tp = sum(1 for r in rows if r["label"] == "ai" and r[f"count@{b}"] >= 1)
        na = sum(1 for r in rows if r["label"] == "ai")
        fp = sum(1 for r in rows if r["label"] == "real" and r[f"count@{b}"] >= 1)
        nr = sum(1 for r in rows if r["label"] == "real")
        ba = 0.5 * (tp / na + 1 - fp / nr)
        print(f"  {b:>5}{tp:>7}/{na:<4}{fp:>19}/{nr:<4}{ba:>14.3f}")

    json.dump({"rows": rows, "results": out},
              open("ratchet_results.json", "w"), indent=2, default=str)
    print("\nwrote ratchet_results.json")


if __name__ == "__main__":
    main()
