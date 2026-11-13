#!/usr/bin/env python3
"""
Spectral fingerprint observer (Jonathan's idea, rigorous form).
================================================================
Hypothesis: human/natural images sit near the golden/natural reference field —
broadband, non-resonant, ~1/f power spectrum ("almost random"). AI-generated
images DEVIATE with a resonant pattern (periodic peaks, over-regular spectra,
"too smooth" high frequencies). Measure that deviation, no model needed.

This is a MODEL-FREE, maximally-independent axis for the committee. Here we just
test which spectral features separate real vs AI on the 50-image art set, and
report AUC per feature (label-free discrimination). No API cost.
"""
import os, glob, math
import numpy as np
from PIL import Image

N = 256  # analysis size


def radial_power(gray):
    """Radially-averaged log power spectrum P(r)."""
    f = np.fft.fftshift(np.fft.fft2(gray))
    power = np.log1p(np.abs(f) ** 2)
    cy, cx = np.array(power.shape) // 2
    y, x = np.indices(power.shape)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(int)
    tbin = np.bincount(r.ravel(), power.ravel())
    nr = np.bincount(r.ravel())
    prof = tbin / np.maximum(nr, 1)
    return prof[1:N // 2]  # drop DC, keep to Nyquist


def features(path):
    g = np.asarray(Image.open(path).convert("L").resize((N, N)), dtype=np.float64)
    g = (g - g.mean()) / (g.std() + 1e-6)
    P = radial_power(g)
    fr = np.arange(1, len(P) + 1, dtype=np.float64)
    logf, logP = np.log(fr), P

    # 1/f power-law fit (natural images follow it smoothly)
    A = np.vstack([logf, np.ones_like(logf)]).T
    slope, intercept = np.linalg.lstsq(A, logP, rcond=None)[0]
    fit = slope * logf + intercept
    resid = logP - fit
    resid_rms = float(np.sqrt(np.mean(resid ** 2)))          # deviation from 1/f
    ss_res = np.sum(resid ** 2); ss_tot = np.sum((logP - logP.mean()) ** 2)
    r2 = float(1 - ss_res / (ss_tot + 1e-9))                  # how power-law-like

    # resonance / peakiness: energy in spikes above a smoothed baseline
    k = 5
    smooth = np.convolve(P, np.ones(k) / k, mode="same")
    peaks = np.clip(P - smooth, 0, None)
    peak_energy = float(np.sum(peaks) / (np.sum(np.abs(P)) + 1e-9))  # AI grid tell

    # high-frequency energy fraction (AI art is often "too smooth" up high)
    hf = float(P[len(P) * 2 // 3:].mean() / (P.mean() + 1e-9))

    # spectral entropy of the radial profile (higher = more spread/random)
    p = np.abs(P) / (np.sum(np.abs(P)) + 1e-9)
    spec_entropy = float(-np.sum(p * np.log(p + 1e-12)) / math.log(len(p)))

    return {"slope": slope, "resid_rms": resid_rms, "one_over_f_r2": r2,
            "peak_energy": peak_energy, "hf_frac": hf, "spec_entropy": spec_entropy}


def auc(scores, labels):
    """P(real scores higher than ai); labels: 1=real,0=ai. Returns AUC and |dir|."""
    reals = [s for s, y in zip(scores, labels) if y == 1]
    ais = [s for s, y in zip(scores, labels) if y == 0]
    w = sum(1 for r in reals for a in ais if r > a) + 0.5 * sum(1 for r in reals for a in ais if r == a)
    a = w / (len(reals) * len(ais))
    return a


def main():
    reals = sorted(glob.glob("/home/claude/bench/real/*.jpg"))
    ais = sorted(glob.glob("/home/claude/bench/ai/*.jpg"))
    rows, labels = [], []
    for p in reals: rows.append(features(p)); labels.append(1)
    for p in ais:   rows.append(features(p)); labels.append(0)
    keys = list(rows[0].keys())
    print(f"spectral features on {len(reals)} real + {len(ais)} ai images\n")
    print(f"{'feature':<16} {'AUC':>6}  {'|separation|':>12}   (AUC=0.5 chance; distance from 0.5 = signal)")
    best = None
    for k in keys:
        vals = [row[k] for row in rows]
        a = auc(vals, labels)
        sep = abs(a - 0.5)
        print(f"{k:<16} {a:>6.3f}  {sep:>12.3f}")
        if best is None or sep > best[1]:
            best = (k, sep, a)
    print(f"\nbest single spectral feature: {best[0]}  (AUC {best[2]:.3f}, separation {best[1]:.3f})")
    print("note: AUC<0.5 means the feature is HIGHER for AI (flip the sign to use it).")


if __name__ == "__main__":
    main()
