"""
aggregation_test.py -- Jonathan's ratchet: is the verdict a MAX, not a MEAN?

THE CLAIM
---------
"when im looking for a fake myself i usually get one thing that tells me for sure
its fake and then nothing else changes that verdict after. its like a threshold,
once one spot reaches that fake bar i call the whole thing fake, and i can
continue searching to see how fake it is but its always going to be fake from
there."

That is a different aggregation rule from anything this project has tested.
EVERY combination so far has been an AVERAGE: the committee averages observers,
the free stack averages features, per-image scores average cells. Averaging is
the correct rule when every element is a noisy estimate of ONE global quantity.
It is the WRONG rule when the evidence is local and sparse -- because a single
decisive cell gets divided by 36.

This matters mechanically here. FOLDING_SEAM_REBUILD found spec_dev localises
edits of 0.5-1% of frame (0.97, 0.88) and nothing above 4%. A 0.5% edit is ONE
cell out of 36. Under a mean, one screaming cell moves the image score by 1/36 of
its magnitude. Under a max, it decides it. If the ratchet model is right, the
image-level detection that came back "not significant" (+9.6 points, 8/13,
mean/se 1.89) was measured with the wrong operator.

FOUR RULES, same per-cell evidence, paired design
-------------------------------------------------
  mean        average of all 36 cell deviations              (what was used)
  top3        average of the 3 most anomalous cells
  max         the single most anomalous cell                 (the pure ratchet)
  count@bar   how many cells exceed a fixed deviation bar     (ratchet + "how fake")

Paired, so each edited image is compared against ITS OWN untouched original --
same camera, scene, lighting, compression. The only difference is the edit. This
is the strongest form of control available and it needs no threshold calibration:
the question is simply whether the edited member of each pair scores higher.

TWO COMBINATION RULES ACROSS TOOLS
----------------------------------
Jonathan's other point: "arent they kind of like tools for specific things to
check?" If the measures are specialists rather than panel members, they should be
combined by MAX -- any tool firing counts -- not by average, which lets four
silent tools drown the one that had jurisdiction.

  mean-over-tools   average the per-cell deviations across measures, then aggregate
  max-over-tools    take the per-cell max across measures, then aggregate

PRE-REGISTERED
--------------
  1. max and top3 beat mean at image-level detection, because the evidence is sparse.
  2. The gain is largest on the SMALL edits, where mean dilution is worst.
  3. max-over-tools beats mean-over-tools, for the same dilution reason.
  4. Risk, and it is the serious one: max over 36 cells x 7 measures is the
     maximum of ~250 noisy draws, and a maximum has no cancellation -- noise only
     ever pushes it up. It will rise on the UNTOUCHED originals too. The paired
     design is what catches that: if max rises equally on both arms, the rule is
     amplifying noise, not finding edits. Report both arms always.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import density_observer as D
import seam_rerun as S
import within_image_observers as W

G = W.G
FEATS = ["noise_dev", "sharp_dev", "spec_dev", "nl_asym_dev"]
BAR = 3.0          # deviation units; "this cell does not belong in this image"


# ------------------------------------------------------------------ aggregators
def agg(v, rule):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 4:
        return np.nan
    if rule == "mean":
        return float(v.mean())
    if rule == "top3":
        return float(np.sort(v)[-3:].mean())
    if rule == "max":
        return float(v.max())
    if rule == "count@bar":
        return float((v >= BAR).sum())
    raise ValueError(rule)


RULES = ["mean", "top3", "max", "count@bar"]


def sign_test(wins, n):
    """Two-sided exact binomial p under p=0.5."""
    from math import comb
    k = max(wins, n - wins)
    p = sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n * 2
    return min(1.0, p)


def main():
    rows = json.load(open("seam/index.json"))
    per = []
    for r in rows:
        mask = np.load(f"seam/{r['name']}_mask.npy")
        cov = W.coverage(mask)
        sel = cov >= 0.05
        if sel.sum() == 0:
            sel = np.zeros(G * G, bool)
            sel[int(np.argmax(cov))] = True
        rec = {"name": r["name"], "frac": r["mask_frac"],
               "n_pos": int(sel.sum()), "sel": sel.tolist()}
        for kind in ("edit", "orig"):
            p = f"seam/{r['name']}_{kind}.jpg"
            raw = S.raw_measure(p)
            dens = D.per_cell(p)
            dev = {f: S.dev_trim(raw[f]) for f in FEATS}
            for k, v in dens.items():
                dev[f"dens_{k}"] = S.dev_trim(v)
            rec[f"{kind}_dev"] = {k: np.asarray(v).tolist() for k, v in dev.items()}
        per.append(rec)
        print(f"  {r['name']} ({100*rec['frac']:.2f}%, {rec['n_pos']} cells)", flush=True)

    TOOLS = FEATS + ["dens_lossy", "dens_lossless", "dens_noise"]

    def stack(rec, kind):
        M = np.array([rec[f"{kind}_dev"][t] for t in TOOLS], float)
        return M                                      # (n_tools, 36)

    # ---------------------------------------------------------- 1. image level
    print(f"\n{'='*100}")
    print("1. IMAGE-LEVEL DETECTION -- paired, each edit against ITS OWN original")
    print("=" * 100)
    print(f"{'combination':<20}{'rule':<12}{'edited wins':>13}{'sign p':>9}"
          f"{'mean edit':>11}{'mean orig':>11}{'edit-orig':>11}")
    best = {}
    for comb_name, combf in (("mean-over-tools", lambda M: M.mean(0)),
                             ("max-over-tools", lambda M: M.max(0)),
                             ("spec_dev alone", None)):
        for rule in RULES:
            E, O = [], []
            for rec in per:
                if combf is None:
                    e = np.asarray(rec["edit_dev"]["spec_dev"], float)
                    o = np.asarray(rec["orig_dev"]["spec_dev"], float)
                else:
                    e, o = combf(stack(rec, "edit")), combf(stack(rec, "orig"))
                E.append(agg(e, rule))
                O.append(agg(o, rule))
            E, O = np.array(E), np.array(O)
            k = np.isfinite(E) & np.isfinite(O)
            wins = int((E[k] > O[k]).sum())
            p = sign_test(wins, int(k.sum()))
            best[f"{comb_name}|{rule}"] = {"wins": wins, "n": int(k.sum()), "p": p,
                                           "edit": float(E[k].mean()),
                                           "orig": float(O[k].mean())}
            flag = "  <--" if p < 0.10 else ""
            print(f"{comb_name:<20}{rule:<12}{wins:>8}/{k.sum():<4}{p:>9.3f}"
                  f"{E[k].mean():>11.2f}{O[k].mean():>11.2f}"
                  f"{E[k].mean()-O[k].mean():>+11.2f}{flag}")

    # ---------------------------------------------------------- 2. argmax hits
    print(f"\n{'='*100}")
    print("2. DOES THE SINGLE MOST ANOMALOUS CELL LAND ON THE EDIT?")
    print("   chance = that image's own mask cell fraction, so each pair is its own null")
    print("=" * 100)
    print(f"{'image':<22}{'edit%':>8}{'pos cells':>11}{'chance':>9}"
          f"{'argmax in mask?':>17}{'ctrl argmax in same cells?':>28}")
    hit = ch = 0.0
    chit = 0.0
    n = 0
    for rec in per:
        sel = np.array(rec["sel"], bool)
        e = np.array([rec["edit_dev"][t] for t in TOOLS], float).max(0)
        o = np.array([rec["orig_dev"][t] for t in TOOLS], float).max(0)
        if not np.isfinite(e).any():
            continue
        ai = int(np.nanargmax(e))
        ao = int(np.nanargmax(o))
        c = sel.mean()
        hit += sel[ai]
        chit += sel[ao]
        ch += c
        n += 1
        print(f"{rec['name']:<22}{100*rec['frac']:>7.2f}%{sel.sum():>11}"
              f"{c:>9.2f}{'YES' if sel[ai] else 'no':>17}"
              f"{('YES' if sel[ao] else 'no'):>28}")
    print(f"\n  argmax lands in the edited region : {hit:.0f}/{n} = {hit/n:.2f}")
    print(f"  chance from the masks themselves  : {ch/n:.2f}")
    print(f"  CONTROL, same cells on originals  : {chit:.0f}/{n} = {chit/n:.2f}")
    print(f"  lift over chance                  : {hit/n - ch/n:+.2f}   "
          f"control lift {chit/n - ch/n:+.2f}")

    # ---------------------------------------------------------- 3. by edit size
    print(f"\n{'='*100}")
    print("3. WHERE THE MAX RULE HELPS -- image-level edit-minus-original, by edit size")
    print("=" * 100)
    print(f"{'image':<22}{'edit%':>8}{'mean rule':>12}{'max rule':>11}"
          f"{'top3 rule':>12}{'count@3':>10}")
    for rec in sorted(per, key=lambda x: x["frac"]):
        line = f"{rec['name']:<22}{100*rec['frac']:>7.2f}%"
        for rule in ("mean", "max", "top3", "count@bar"):
            e = agg(stack(rec, "edit").max(0), rule)
            o = agg(stack(rec, "orig").max(0), rule)
            line += f"{e-o:>+12.2f}" if rule != "count@bar" else f"{e-o:>+10.0f}"
        print(line)

    json.dump({"image_level": best,
               "argmax": {"hit": hit / n, "chance": ch / n, "control": chit / n,
                          "n": n}},
              open("aggregation_results.json", "w"), indent=2, default=str)
    print("\nwrote aggregation_results.json")


if __name__ == "__main__":
    main()
