#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dot14_env_port_test.py
======================

The ".14 as the environment port" test  (FOLDING_TRAMPOLINE.md §9, experiment 2).

HYPOTHESIS
----------
The flat two-atom detector gets ~0.86 accuracy (25/29) and leaves ~0.14 it cannot
close, and those errors sit in the LOW-|z| abstention band (ENVIRONMENT_BRIDGE:
the 4 errors carry |z| 0.52/0.59/0.65/0.81 vs a correct-call mean of 1.30).

If the .14 residual is the PORT to the outer shell (the environment) — not noise —
then the images the internal detector cannot close should be the images where the
ENVIRONMENT observer k fires and carries the missing axis. Two predictions:

    P1 (coincidence): the error set is ENRICHED for k-fires vs base rate
                      -> one-tailed hypergeometric p.
    P2 (resolution):  among errors where k fired, k's direction would FLIP the
                      call to the correct label -> fraction corrected.

If P1 holds and P2 corrects most of them, the .14 is the door to the outer shell,
shown on data you already have. If the errors sit elsewhere, drop the port story.

HONEST POWER NOTE
-----------------
n = 29, ~4 errors, ~11 k-fires. This has almost no statistical power; it is a LOOK,
not a proof. Treat a positive as "worth a bigger set", a negative as "port story
does not hold on this data". The script prints the caveat with the result.

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------
Two modes; the script auto-detects.

MODE A  (live — preferred): it imports your existing modules and runs the two
        detectors over the image set itself. Edit the CONFIG + the three ADAPTER
        functions so they match your actual APIs (they are the ONLY place you
        should need to touch). Then:  python dot14_env_port_test.py

MODE B  (CSV fallback): if the imports/adapters do not line up, export one CSV
        with columns:  image,true_label,pred_label,z,env_fired,env_value
        and run:       python dot14_env_port_test.py --csv results.csv
        (true_label/pred_label in {"real","ai"}; env_fired in {0,1};
         z = signed or unsigned magnitude of the two-atom verdict;
         env_value = env_scale_agreement, higher = more "real".)

Run this from inside the AI Detector folder so the imports resolve. It writes
`dot14_env_port_report.txt` and `dot14_env_port_perimage.csv` next to itself.
Stdlib only (uses math.comb); numpy optional.
"""

import os
import sys
import csv
import math
import argparse

# =============================================================================
# CONFIG  -- edit these paths to your set
# =============================================================================
REAL_DIR = r"real photos"          # folder of genuine photographs
AI_DIR   = r"ai"                   # folder of generated images
# Label convention used throughout: "real" vs "ai".

# env_scale_agreement cutoff for turning k into a directional vote.
# None  -> use the median agreement over the images where k FIRED (data-driven).
# float -> use this fixed cutoff (doc class means were real 0.833 / ai 0.718,
#          so ~0.775 is the midpoint if you prefer a fixed value).
ENV_CUTOFF = None

# An image counts as "in the abstention band" if |z| is at/below this percentile
# of all |z| (used only for the descriptive band table, not for P1/P2).
ABSTAIN_PCTL = 40.0

# =============================================================================
# ADAPTERS  -- the ONLY functions you should need to edit for MODE A.
# Each is wrapped so a mismatch fails loudly with a hint rather than silently.
# =============================================================================

def load_image(path):
    """Return an image object your observers accept.
    MUST go through the EXIF-correct loader (STATE_OF_THE_DETECTOR §8:
    'no observer may call Image.open / imread directly')."""
    import image_io
    for fn in ("load", "load_image", "read", "imread", "open_image"):
        if hasattr(image_io, fn):
            return getattr(image_io, fn)(path)
    raise AttributeError(
        "image_io has no load/read function I recognise -- point load_image() "
        "at your EXIF-correct loader.")


def two_atom_verdict(img):
    """Return (signed_score, z_magnitude) from the two-atom free detector.
    sign(signed_score) -> predicted label (see PRED_SIGN below);
    z_magnitude        -> polar confidence |z| (ENVIRONMENT_BRIDGE Part II)."""
    import shovelcat_free as sf
    for fn in ("verdict", "two_atom", "detect", "score", "predict", "run"):
        if hasattr(sf, fn):
            out = getattr(sf, fn)(img)
            return _coerce_score(out)
    raise AttributeError(
        "shovelcat_free has no verdict/detect function I recognise -- point "
        "two_atom_verdict() at the two-atom polar verdict call.")


def env_read(img):
    """Return (fired: bool, env_value: float|None) from the environment observer.
    env_value = env_scale_agreement (higher => more 'real'); None if not fired."""
    import environment_observer as eo
    for fn in ("read", "observe", "run", "environment", "detect", "score"):
        if hasattr(eo, fn):
            out = getattr(eo, fn)(img)
            return _coerce_env(out)
    raise AttributeError(
        "environment_observer has no read/observe function I recognise -- point "
        "env_read() at the k observer call.")

# Which sign of the two-atom score means "ai". Flip if your detector is inverted.
PRED_SIGN_AI = +1   # if signed_score * PRED_SIGN_AI > 0  -> predicted "ai"

# ---- small coercers so common return shapes 'just work' ----------------------

def _coerce_score(out):
    """Accept float, (score,), (score,z), {'score':,'z':}, or an object w/ attrs."""
    if isinstance(out, dict):
        s = out.get("score", out.get("verdict", out.get("value")))
        z = out.get("z", out.get("magnitude", out.get("conf", abs(s) if s is not None else None)))
        return float(s), float(z)
    if isinstance(out, (tuple, list)):
        if len(out) >= 2:
            return float(out[0]), float(abs(out[1]))
        return float(out[0]), float(abs(out[0]))
    for a in ("score", "verdict", "value"):
        if hasattr(out, a):
            s = float(getattr(out, a))
            z = float(getattr(out, "z", getattr(out, "magnitude", abs(s))))
            return s, z
    s = float(out)
    return s, abs(s)


def _coerce_env(out):
    if isinstance(out, dict):
        fired = bool(out.get("fired", out.get("did_fire", out.get("active", False))))
        val = out.get("env_scale_agreement",
                      out.get("agreement", out.get("value", out.get("bridge"))))
        return fired, (float(val) if (fired and val is not None) else (float(val) if val is not None else None))
    if isinstance(out, (tuple, list)):
        fired = bool(out[0])
        val = float(out[1]) if len(out) > 1 and out[1] is not None else None
        return fired, val
    if hasattr(out, "fired"):
        val = getattr(out, "env_scale_agreement", getattr(out, "agreement", None))
        return bool(out.fired), (float(val) if val is not None else None)
    # a bare number: treat as agreement, assume fired
    return True, float(out)

# =============================================================================
# CORE  -- collection + statistics (no edits needed below here)
# =============================================================================

IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic")


def _list_images(folder):
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(IMG_EXTS)]


def collect_live():
    """MODE A: run both observers over the image set."""
    rows = []
    sets = [(REAL_DIR, "real"), (AI_DIR, "ai")]
    total = sum(len(_list_images(d)) for d, _ in sets)
    if total == 0:
        raise FileNotFoundError(
            f"No images found in {REAL_DIR!r} or {AI_DIR!r}. Fix CONFIG paths, "
            f"or use MODE B: --csv results.csv")
    for folder, true_label in sets:
        for path in _list_images(folder):
            img = load_image(path)
            score, z = two_atom_verdict(img)
            pred = "ai" if (score * PRED_SIGN_AI > 0) else "real"
            fired, env_val = env_read(img)
            rows.append(dict(image=os.path.basename(path), true_label=true_label,
                             pred_label=pred, z=abs(z),
                             env_fired=bool(fired), env_value=env_val))
    return rows


def collect_csv(path):
    """MODE B: read a pre-exported CSV."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ev = r.get("env_value", "")
            rows.append(dict(
                image=r["image"],
                true_label=r["true_label"].strip().lower(),
                pred_label=r["pred_label"].strip().lower(),
                z=abs(float(r["z"])),
                env_fired=str(r.get("env_fired", "0")).strip() in ("1", "true", "True", "yes"),
                env_value=(float(ev) if ev not in ("", None) else None),
            ))
    if not rows:
        raise ValueError("CSV had no rows.")
    return rows


def hypergeom_sf(k, N, K, n):
    """One-tailed P(X >= k): draw n from N with K 'successes'. Exact, stdlib."""
    k = int(k); N = int(N); K = int(K); n = int(n)
    lo = max(0, n - (N - K))
    hi = min(K, n)
    if k <= lo:
        return 1.0
    denom = math.comb(N, n)
    if denom == 0:
        return float("nan")
    return sum(math.comb(K, x) * math.comb(N - K, n - x)
               for x in range(max(k, lo), hi + 1)) / denom


def percentile(vals, p):
    if not vals:
        return float("nan")
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    idx = (p / 100.0) * (len(s) - 1)
    lo = int(math.floor(idx)); hi = int(math.ceil(idx))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def analyse(rows):
    N = len(rows)
    errors  = [r for r in rows if r["pred_label"] != r["true_label"]]
    correct = [r for r in rows if r["pred_label"] == r["true_label"]]
    fires   = [r for r in rows if r["env_fired"]]

    n_err, n_cor, n_fire = len(errors), len(correct), len(fires)
    err_and_fire = [r for r in errors if r["env_fired"]]

    # P1 -- enrichment of k-fires within the error set
    p1 = hypergeom_sf(len(err_and_fire), N, n_fire, n_err) if n_err and n_fire else float("nan")
    fire_rate_err = (len(err_and_fire) / n_err) if n_err else float("nan")
    fire_rate_cor = (sum(1 for r in correct if r["env_fired"]) / n_cor) if n_cor else float("nan")

    # env cutoff for the directional (flip) test
    fired_vals = [r["env_value"] for r in fires if r["env_value"] is not None]
    if ENV_CUTOFF is not None:
        cutoff = ENV_CUTOFF
    elif fired_vals:
        cutoff = percentile(fired_vals, 50.0)   # median over fired images
    else:
        cutoff = None

    # P2 -- would k flip the error to the correct label?
    flips = []
    for r in err_and_fire:
        if r["env_value"] is None or cutoff is None:
            continue
        env_pred = "real" if r["env_value"] >= cutoff else "ai"
        flips.append((r, env_pred, env_pred == r["true_label"]))
    n_flip_ok = sum(1 for _, _, ok in flips if ok)

    # descriptive: abstention band (are errors low-|z|?)
    zs = [r["z"] for r in rows]
    band_cut = percentile(zs, ABSTAIN_PCTL)
    z_err = [r["z"] for r in errors]
    z_cor = [r["z"] for r in correct]
    mean = lambda xs: (sum(xs) / len(xs)) if xs else float("nan")

    return dict(
        N=N, n_err=n_err, n_cor=n_cor, n_fire=n_fire,
        err_and_fire=err_and_fire, n_err_fire=len(err_and_fire),
        p1=p1, fire_rate_err=fire_rate_err, fire_rate_cor=fire_rate_cor,
        cutoff=cutoff, flips=flips, n_flip_ok=n_flip_ok,
        band_cut=band_cut, z_err_mean=mean(z_err), z_cor_mean=mean(z_cor),
        errors=errors,
    )


def fmt(x, nd=3):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "n/a"
        return f"{x:.{nd}f}"
    except Exception:
        return str(x)


def report(a, rows, mode):
    L = []
    P = L.append
    P("=" * 70)
    P("  .14-AS-ENVIRONMENT-PORT TEST  --  FOLDING_TRAMPOLINE.md 9(2)")
    P("=" * 70)
    P(f"mode: {mode}   images: {a['N']}   errors: {a['n_err']}   "
      f"correct: {a['n_cor']}   k-fires: {a['n_fire']}")
    P("")
    P(f"flat two-atom accuracy: {fmt(a['n_cor']/a['N'] if a['N'] else float('nan'))}"
      f"   (residual = {fmt(a['n_err']/a['N'] if a['N'] else float('nan'))})")
    P("")
    P("-- descriptive: is the residual the low-|z| abstention band? -----------")
    P(f"   mean |z|  errors : {fmt(a['z_err_mean'])}")
    P(f"   mean |z|  correct: {fmt(a['z_cor_mean'])}")
    P(f"   (ENVIRONMENT_BRIDGE recorded 0.52-0.81 vs 1.30; errors should be LOWER)")
    P("")
    P("-- P1: are errors ENRICHED for k-fires? --------------------------------")
    P(f"   errors that are also k-fires : {a['n_err_fire']} / {a['n_err']}")
    P(f"   k-fire rate | error         : {fmt(a['fire_rate_err'])}")
    P(f"   k-fire rate | correct       : {fmt(a['fire_rate_cor'])}")
    P(f"   one-tailed hypergeometric p : {fmt(a['p1'])}")
    P("")
    P("-- P2: would k FLIP the errors to the correct label? -------------------")
    P(f"   env cutoff (agreement)      : {fmt(a['cutoff'])}"
      f"{'  [median of fired]' if ENV_CUTOFF is None else '  [fixed]'}")
    if a["flips"]:
        for r, env_pred, ok in a["flips"]:
            P(f"     {r['image'][:34]:34s} true={r['true_label']:4s} "
              f"agreement={fmt(r['env_value'])} -> k says {env_pred:4s} "
              f"{'FLIPS-CORRECT' if ok else 'no'}")
        P(f"   corrected by k              : {a['n_flip_ok']} / {len(a['flips'])}")
    else:
        P("   (no errors where k fired AND an agreement value was present)")
    P("")
    P("-- verdict ------------------------------------------------------------")
    verdict = _verdict(a)
    for line in verdict:
        P("   " + line)
    P("")
    P("-- POWER CAVEAT -------------------------------------------------------")
    P("   n~29 with ~4 errors: almost no statistical power. A positive here is")
    P("   'worth a bigger, content-matched set', not a proof. A clean negative")
    P("   (errors NOT enriched for k-fires) is the more informative outcome:")
    P("   it says the .14 is not the environment door on this data.")
    P("=" * 70)
    return "\n".join(L)


def _verdict(a):
    out = []
    if a["n_err"] == 0:
        return ["No errors in this run -- nothing to attach. Re-check labels/paths."]
    enriched = (not math.isnan(a["p1"])) and a["p1"] <= 0.10 and \
               (a["fire_rate_err"] > a["fire_rate_cor"])
    flips_ok = a["flips"] and (a["n_flip_ok"] >= max(1, len(a["flips"]) - 1))
    if enriched and flips_ok:
        out.append("SUPPORTS the port story: errors cluster on k-fires AND k would")
        out.append("flip most of them. The .14 behaves like the door to the outer")
        out.append("shell. Next: repeat on a larger, content-matched set.")
    elif enriched and not flips_ok:
        out.append("PARTIAL: errors ARE enriched for k-fires, but k's direction does")
        out.append("not resolve them. The residual sits where the environment engages,")
        out.append("yet this k reading is not the missing axis. Try another outer domain.")
    elif (not enriched) and flips_ok:
        out.append("MIXED: k did not preferentially fire on the errors, but where it")
        out.append("did it corrected them. Weak, inconclusive at this n.")
    else:
        out.append("DOES NOT SUPPORT the port story on this data: the errors are not")
        out.append("where k fires. The .14 is not the environment door here -- drop it,")
        out.append("or the environment observer is too weak/confounded to show it.")
    return out


def main():
    ap = argparse.ArgumentParser(description="The .14-as-environment-port test.")
    ap.add_argument("--csv", help="MODE B: read image,true_label,pred_label,z,"
                                   "env_fired,env_value from this file")
    args = ap.parse_args()

    if args.csv:
        rows, mode = collect_csv(args.csv), f"CSV ({args.csv})"
    else:
        try:
            rows, mode = collect_live(), "live (imported observers)"
        except Exception as e:
            print("MODE A (live) failed:\n  ", repr(e))
            print("\nEither fix CONFIG/ADAPTERS above, or run MODE B:")
            print("  python dot14_env_port_test.py --csv results.csv")
            print("  (columns: image,true_label,pred_label,z,env_fired,env_value)")
            sys.exit(2)

    a = analyse(rows)
    text = report(a, rows, mode)
    print(text)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "dot14_env_port_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    with open(os.path.join(here, "dot14_env_port_perimage.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "true_label", "pred_label", "z", "correct", "env_fired", "env_value"])
        for r in rows:
            w.writerow([r["image"], r["true_label"], r["pred_label"], fmt(r["z"]),
                        int(r["pred_label"] == r["true_label"]),
                        int(r["env_fired"]), fmt(r["env_value"])])
    print("\nwrote dot14_env_port_report.txt and dot14_env_port_perimage.csv")


if __name__ == "__main__":
    main()
