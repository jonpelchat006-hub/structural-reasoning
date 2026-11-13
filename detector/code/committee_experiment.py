"""
committee_experiment.py — what does the committee architecture actually buy?

THE QUESTION
------------
The model-free half of the detector died on the matched benchmark
(FOLDING_MATCHED_BENCHMARK: nothing above |AUC-0.5| = 0.164). The vision committee
was never tested there. So: does it work, AND is the committee the reason?

The arm that has never been run is SAME MODEL TWICE. Without it, "observers
disagree at the seam" is indistinguishable from "the sampler is stochastic". The
old 0.733 -> 0.765 result (2xClaude -> Claude+Gemini) hinted independence helps,
but it was measured on the confounded set, so it needs redoing on clean data.

FOUR ARMS, same 58 content-matched, compression-matched images:

    A  claude x1              one observer
    B  claude x2              SAME model twice -- is disagreement just sampling noise?
    C  claude + gemini        genuinely independent observers
    D  claude x2 + gemini x2  four observers, two families

For each arm, two readings, which the framework says are different things:

    agreement    = mean authenticity across observers  (FOLDING_OBSERVERS: the invariant)
    disagreement = mean per-cell spread across observers (the seam / depth signal)

PRE-REGISTERED BARS (set before the run, per this project's discipline)
    - the committee is a shippable product if stratified AUC >= 0.80 in BOTH buckets
    - the committee ARCHITECTURE is justified only if C beats B by >= 0.05 AUC
      (independence beating sampling noise)
    - the seam claim survives only if disagreement carries |AUC-0.5| >= 0.10 on its own

Everything is stratified by content bucket, exactly as the model-free benchmark was.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ENV_PATH = "/mnt/user-data/uploads/Shovelcat-AI/.env.local"
CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_MODEL = "gemini-2.5-flash"   # new key; pro tiers 404 on it
OPENAI_MODEL = "gpt-5.1"
XAI_MODEL = "grok-4"
GRID = 4
CACHE = "committee_cache.json"
BENCH = "_bench"

PROMPT = f"""You are one observer on a panel assessing photographic authenticity.

Divide the image into a {GRID}x{GRID} grid, row-major, rows top to bottom.

For EACH of the {GRID*GRID} cells give an authenticity score 0-100:
  100 = certainly a real photograph of a real scene
    0 = certainly synthetic / AI-generated imagery

Judge only what you can see in that cell and how it relates to the rest of the
image. Do not assume a prior about how common generated images are.

Reply with STRICT JSON and nothing else:
{{"cells": [{GRID*GRID} integers], "global": <integer 0-100>}}"""

_lock = threading.Lock()
_cache = {}


def _env():
    e = {}
    for ln in open(ENV_PATH):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            e[k.strip()] = v.strip().strip('"').strip("'")
    return e


ENV = _env()
import os as _os
if _os.path.exists(".gemini_key"):
    ENV["GEMINI_API_KEY"] = open(".gemini_key").read().strip()


def _b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def _parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    cells = d.get("cells")
    if not isinstance(cells, list) or len(cells) != GRID * GRID:
        return None
    try:
        cells = [float(c) for c in cells]
    except Exception:
        return None
    g = d.get("global")
    g = float(g) if isinstance(g, (int, float)) else float(np.mean(cells))
    return {"cells": cells, "global": g}


def call_claude(path, seed):
    body = {
        "model": CLAUDE_MODEL, "max_tokens": 800, "temperature": 1.0,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": "image/jpeg",
                                         "data": _b64(path)}},
            {"type": "text", "text": PROMPT}]}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": ENV["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    return _parse("".join(b.get("text", "") for b in d.get("content", [])))


def call_gemini(path, seed):
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": _b64(path)}},
            {"text": PROMPT}]}],
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": 4000},
    }
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={ENV['GEMINI_API_KEY']}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return _parse("".join(p.get("text", "") for p in parts if "text" in p))


def _openai_like(path, base, key, model):
    body = {"model": model, "max_completion_tokens": 900,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{_b64(path)}"}}]}]}
    req = urllib.request.Request(base, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    return _parse(d["choices"][0]["message"]["content"])


def call_gpt(path, seed):
    return _openai_like(path, "https://api.openai.com/v1/chat/completions",
                        ENV["OPENAI_API_KEY"], OPENAI_MODEL)


def call_grok(path, seed):
    return _openai_like(path, "https://api.x.ai/v1/chat/completions",
                        ENV["XAI_API_KEY"], XAI_MODEL)


CALLERS = {"claude": call_claude, "gemini": call_gemini,
           "gpt": call_gpt, "grok": call_grok}


def observe(path, model, rep):
    key = f"{path}|{model}|{rep}"
    with _lock:
        if key in _cache:
            return _cache[key]
    out = None
    for attempt in range(4):
        try:
            out = CALLERS[model](path, rep)
            if out:
                break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(3 * (attempt + 1) + rep)
                continue
            print(f"    HTTP {e.code} {model} {os.path.basename(path)}", flush=True)
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    with _lock:
        _cache[key] = out
    return out


def images():
    out = []
    for label in ("real", "ai"):
        for bucket in sorted(os.listdir(os.path.join(BENCH, label))):
            d = os.path.join(BENCH, label, bucket)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                    out.append((os.path.join(d, f), label, bucket))
    return out


# ── arms ──────────────────────────────────────────────────────────────────────

ARMS = {
    "A claude x1":              [("claude", 0)],
    "B claude x2 SAME model":   [("claude", 0), ("claude", 1)],
    "C claude+gpt INDEPENDENT": [("claude", 0), ("gpt", 0)],
    "D 4 obs / 2 families":     [("claude", 0), ("claude", 1),
                                 ("gpt", 0), ("gpt", 1)],
    "E 3 families":             [("claude", 0), ("gpt", 0), ("grok", 0)],
    "F claude+gemini (v6 roster)": [("claude", 0), ("gemini", 0)],
    "G 4 families":             [("claude", 0), ("gpt", 0), ("grok", 0), ("gemini", 0)],
}


def reduce_arm(readings):
    """agreement = the invariant (mean); disagreement = the depth (spread)."""
    ok = [r for r in readings if r]
    if len(ok) == 0:
        return None
    cells = np.array([r["cells"] for r in ok], float)
    agreement = float(cells.mean())
    disagreement = float(cells.std(0).mean()) if len(ok) > 1 else 0.0
    return {"agreement": agreement, "disagreement": disagreement,
            "n_obs": len(ok)}


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 2 or len(neg) < 2:
        return np.nan
    x = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(x)) + 1.0
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def stratified(rows, key):
    num = den = 0.0
    per = {}
    for b in sorted({r["bucket"] for r in rows}):
        p = [r[key] for r in rows if r["bucket"] == b and r["label"] == "real"]
        q = [r[key] for r in rows if r["bucket"] == b and r["label"] == "ai"]
        a = auc(p, q)
        if np.isnan(a):
            continue
        per[b] = (a, len(p) * len(q))
        num += a * len(p) * len(q)
        den += len(p) * len(q)
    return (num / den if den else np.nan), per


def main():
    global _cache
    if os.path.exists(CACHE):
        _cache = json.load(open(CACHE))
        print(f"resumed cache with {len(_cache)} readings")

    imgs = images()
    need = ([(p, m, rep) for (p, _, _) in imgs
             for m in ("claude", "gpt") for rep in (0, 1)]
            + [(p, m, 0) for (p, _, _) in imgs for m in ("grok", "gemini")])
    print(f"{len(imgs)} images x 2 models x 2 passes = {len(need)} calls "
          f"+ grok ({CLAUDE_MODEL}, {OPENAI_MODEL}, {XAI_MODEL})\n")

    done = [0]

    def work(t):
        r = observe(*t)
        with _lock:
            done[0] += 1
            if done[0] % 20 == 0:
                print(f"  {done[0]}/{len(need)}", flush=True)
                json.dump(_cache, open(CACHE, "w"))
        return r

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, need))
    json.dump(_cache, open(CACHE, "w"))

    miss = sum(1 for k, v in _cache.items() if v is None)
    print(f"\nreadings: {len(_cache)}  failed: {miss}")

    print(f"\n{'='*84}\nWHAT THE COMMITTEE BUYS  (stratified by content bucket)\n{'='*84}")
    print(f"{'arm':<26}{'AGREEMENT':>11}{'|d|':>7}{'DISAGREE':>11}{'|d|':>7}   per-bucket (agreement)")
    results = {}
    for name, roster in ARMS.items():
        rows = []
        for p, label, bucket in imgs:
            red = reduce_arm([observe(p, m, rep) for m, rep in roster])
            if red:
                rows.append({**red, "label": label, "bucket": bucket})
        a_s, a_per = stratified(rows, "agreement")
        d_s, d_per = stratified(rows, "disagreement") if len(roster) > 1 else (np.nan, {})
        results[name] = {"agreement": a_s, "disagreement": d_s,
                         "per_bucket": a_per, "n": len(rows)}
        pb = ", ".join(f"{b}={v[0]:.2f}" for b, v in a_per.items())
        ds = f"{d_s:>11.3f}{abs(d_s-0.5):>7.3f}" if not np.isnan(d_s) else f"{'-':>11}{'-':>7}"
        print(f"{name:<26}{a_s:>11.3f}{abs(a_s-0.5):>7.3f}{ds}   {pb}")

    b = results["B claude x2 SAME model"]["agreement"]
    c = results["C claude+gpt INDEPENDENT"]["agreement"]
    print(f"\nPRE-REGISTERED BARS")
    print(f"  product (>=0.80 both buckets): "
          f"{'PASS' if all(v[0] >= 0.80 or v[0] <= 0.20 for v in results['C claude+gemini (indep)']['per_bucket'].values()) else 'FAIL'}")
    print(f"  architecture (C beats B by >=0.05): C={c:.3f} B={b:.3f} "
          f"delta={abs(c-0.5)-abs(b-0.5):+.3f} "
          f"{'PASS' if abs(c-0.5)-abs(b-0.5) >= 0.05 else 'FAIL'}")
    dd = results["C claude+gpt INDEPENDENT"]["disagreement"]
    print(f"  seam/disagreement (|d|>=0.10): {abs(dd-0.5):.3f} "
          f"{'PASS' if abs(dd-0.5) >= 0.10 else 'FAIL'}")

    json.dump({"models": [CLAUDE_MODEL, OPENAI_MODEL, XAI_MODEL], "grid": GRID,
               "results": {k: {kk: (vv if not isinstance(vv, float) or np.isfinite(vv) else None)
                               for kk, vv in v.items()} for k, v in results.items()}},
              open("committee_results.json", "w"), indent=2, default=str)
    print("\nwrote committee_results.json")


if __name__ == "__main__":
    main()
