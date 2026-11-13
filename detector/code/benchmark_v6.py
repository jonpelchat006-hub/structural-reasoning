#!/usr/bin/env python3
"""
Benchmark harness for the Shovelcat v6 committee.
=================================================
Runs the committee over a labeled set (real vs AI-generated) and reports
accuracy, AUC, and a confusion matrix. Cost-aware: prints the API-call estimate
and refuses to spend without --go.

Dataset layout (either form):
    --data DIR          expects DIR/real/*.{jpg,png,webp} and DIR/ai/*.{...}
    --real DIR --ai DIR two explicit folders

Scoring: check_image() returns authenticity_score in [0,1] (1 = authentic).
Label convention: real = 1 (positive), ai = 0. A higher score should mean "real".

    python3 benchmark_v6.py --selftest              # verify metrics, no API/keys
    python3 benchmark_v6.py --data set/ --limit 25  # dry-run: shows cost, no calls
    python3 benchmark_v6.py --data set/ --limit 25 --go   # actually runs (spends)
"""

import os
import sys
import glob
import json
import argparse
import statistics

IMG_EXT = ("*.jpg", "*.jpeg", "*.png", "*.webp")
CALLS_PER_IMAGE = 2   # committee roster size (Gemini + Claude)


# ── dataset loading ───────────────────────────────────────────────────────────

def _images(folder):
    out = []
    for ext in IMG_EXT:
        out += glob.glob(os.path.join(folder, "**", ext), recursive=True)
    return sorted(out)


def load_dataset(data=None, real=None, ai=None, limit=None):
    if data:
        real = os.path.join(data, "real")
        ai = os.path.join(data, "ai")
    if not (real and ai):
        raise SystemExit("provide --data DIR (with real/ and ai/) or --real and --ai")
    real_imgs = _images(real)
    ai_imgs = _images(ai)
    if limit:
        real_imgs, ai_imgs = real_imgs[:limit], ai_imgs[:limit]
    if not real_imgs or not ai_imgs:
        raise SystemExit(f"need images in both classes: real={len(real_imgs)} ai={len(ai_imgs)}")
    # label 1 = real (positive), 0 = ai
    return [(p, 1) for p in real_imgs] + [(p, 0) for p in ai_imgs]


# ── metrics (pure python; no numpy/sklearn) ───────────────────────────────────

def auc_real_over_ai(scored):
    """P(random real scores higher than random AI) + 0.5 ties = ROC-AUC for 'real'."""
    reals = [s for s, y in scored if y == 1]
    ais = [s for s, y in scored if y == 0]
    if not reals or not ais:
        return float("nan")
    wins = ties = 0
    for r in reals:
        for a in ais:
            if r > a:
                wins += 1
            elif r == a:
                ties += 1
    return (wins + 0.5 * ties) / (len(reals) * len(ais))


def confusion_at(scored, thr=0.5):
    # predict real if score >= thr
    tp = fp = tn = fn = 0
    for s, y in scored:
        pred_real = s >= thr
        if y == 1 and pred_real: tp += 1
        elif y == 1 and not pred_real: fn += 1
        elif y == 0 and not pred_real: tn += 1   # correctly caught AI
        else: fp += 1                             # AI called real (the dangerous miss)
    return tp, fp, tn, fn


def best_threshold(scored):
    """Sweep thresholds, return the one maximizing balanced accuracy."""
    scores = sorted({s for s, _ in scored})
    best, best_thr = -1, 0.5
    for thr in scores + [1.01]:
        tp, fp, tn, fn = confusion_at(scored, thr)
        tpr = tp / (tp + fn) if (tp + fn) else 0
        tnr = tn / (tn + fp) if (tn + fp) else 0
        bal = (tpr + tnr) / 2
        if bal > best:
            best, best_thr = bal, thr
    return best_thr, best


def report(scored):
    n = len(scored)
    auc = auc_real_over_ai(scored)
    tp, fp, tn, fn = confusion_at(scored, 0.5)
    acc = (tp + tn) / n if n else 0
    ai_recall = tn / (tn + fp) if (tn + fp) else 0   # fraction of AI images caught
    thr, bal = best_threshold(scored)
    print("\n" + "=" * 56)
    print(f"  BENCHMARK — {n} images "
          f"({sum(1 for _,y in scored if y==1)} real / {sum(1 for _,y in scored if y==0)} ai)")
    print("=" * 56)
    print(f"  AUC (real vs AI)          : {auc:.3f}   (0.5 = chance, 1.0 = perfect)")
    print(f"  Accuracy @0.5             : {acc:.3f}")
    print(f"  AI caught (recall on AI)  : {ai_recall:.3f}")
    print(f"  Confusion @0.5   TP={tp} FN={fn} | TN={tn} FP={fp}")
    print(f"    (FP = AI image called real — the miss that matters)")
    print(f"  Best threshold            : {thr:.2f}  (balanced acc {bal:.3f})")
    print("=" * 56)
    return {"n": n, "auc": auc, "accuracy": acc, "ai_recall": ai_recall,
            "best_threshold": thr, "balanced_acc": bal}


# ── running the committee ─────────────────────────────────────────────────────

def run(dataset, score_fn, cache_path=None):
    cache = {}
    if cache_path and os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path))
        except Exception:
            cache = {}
    scored = []
    for i, (path, label) in enumerate(dataset, 1):
        try:
            key = os.path.abspath(path)
            if key in cache:
                score, verdict = cache[key]; note = " (cached)"
            else:
                score, verdict = score_fn(path)
                cache[key] = [score, verdict]
                if cache_path:
                    json.dump(cache, open(cache_path, "w"))
                note = ""
            scored.append((score, label))
            tag = "real" if label == 1 else "ai  "
            print(f"  [{i:>3}/{len(dataset)}] {tag} score={score:.2f} {verdict:<18} "
                  f"{os.path.basename(path)}{note}", flush=True)
        except Exception as e:
            print(f"  [{i:>3}/{len(dataset)}] ERROR {os.path.basename(path)}: {e}",
                  file=sys.stderr, flush=True)
    return scored


# ── self-test (no keys, verifies the metrics) ─────────────────────────────────

def self_test():
    ok = True
    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and cond

    # perfect separation: reals high, ais low
    perfect = [(0.9, 1), (0.8, 1), (0.85, 1), (0.1, 0), (0.2, 0), (0.15, 0)]
    r = report(perfect)
    check("perfect AUC = 1.0", abs(r["auc"] - 1.0) < 1e-9)
    check("perfect accuracy = 1.0", abs(r["accuracy"] - 1.0) < 1e-9)

    # chance: overlapping
    chance = [(0.6, 1), (0.4, 1), (0.55, 0), (0.45, 0)]
    r2 = report(chance)
    check("chance AUC ~ 0.5", abs(r2["auc"] - 0.5) < 0.26)

    # inverted (detector backwards) -> AUC < 0.5
    inv = [(0.1, 1), (0.2, 1), (0.9, 0), (0.8, 0)]
    r3 = report(inv)
    check("inverted AUC < 0.5", r3["auc"] < 0.5)

    print("\nHARNESS SELF-TEST:", "ALL PASS" if ok else "FAILURES")
    return ok


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Shovelcat v6 benchmark")
    ap.add_argument("--data"); ap.add_argument("--real"); ap.add_argument("--ai")
    ap.add_argument("--limit", type=int, help="max images PER CLASS")
    ap.add_argument("--go", action="store_true", help="actually spend API calls (else dry-run)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", help="write metrics JSON here")
    ap.add_argument("--cache", default="bench_cache.json", help="per-image result cache (resumable)")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if self_test() else 1)

    dataset = load_dataset(args.data, args.real, args.ai, args.limit)
    calls = len(dataset) * CALLS_PER_IMAGE
    print(f"Loaded {len(dataset)} images → ~{calls} API calls "
          f"({CALLS_PER_IMAGE}/image: Gemini + Claude).")

    if not args.go:
        print("DRY RUN — re-run with --go to actually call the models and spend.")
        return

    # load keys from .env if present, then import the live committee
    envp = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(envp):
        for line in open(envp):
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                os.environ.setdefault(k, v)
    from shovelcat_checker_v6 import check_image

    def score_fn(path):
        res = check_image(path)
        return res.authenticity_score, res.verdict

    scored = run(dataset, score_fn, cache_path=args.cache)
    metrics = report(scored)
    if args.out:
        json.dump(metrics, open(args.out, "w"), indent=2)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
