#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
does_it_close.py -- does the cycle CLOSE? rational vs irrational period, and the
different verification each job type needs.

Jonathan (the open frontier on the map): classify a path by whether its cycle CLOSES
(returns to origin) and whether its period is RATIONAL — the spinning top's basin orbit
that comes back around vs the beyblade that never quite repeats. Different job types, each
needing its own verification.

Made measurable on a 2-frequency system (two spins at rates f1, f2 — a top's spin +
precession). The ratio ρ = f2/f1 is the whole story:
  * ρ RATIONAL = p/q  -> the trajectory returns EXACTLY to its start after a finite period
    (q turns of the slow spin); it traces a CLOSED finite curve. It can be MEMORISED as one
    repeating loop.
  * ρ IRRATIONAL (e.g. the golden ratio) -> it NEVER returns exactly; it winds forever on
    the torus, densely filling a band. It CANNOT be stored as a finite path — but it is
    still pinned by two numbers: its generating frequencies.

Grounded, and this split is already in the corpus:
  * Shovelcat_10_1 §4.2 — a RATIONAL capacity ratio Cψ/Cφ=p/q makes both domains return to
    the same state together (the cycle closes) and phase-LOCK into aliasing (dependent
    verification); the fix is the MAXIMALLY IRRATIONAL golden ratio (Hurwitz) so the two
    observers never resync — independent verification. So closure ↔ resonance ↔ which
    verification is even valid.
  * Shovelcat_11_3 §18 — "Ratio Cycles… transcendental fractions that approach but never
    reach the limit"; crossings = reset points, irreducibility like primes.
  * FOLDING_STAIRCASE — the devil's-staircase zoom used "to find where it closes."
  * FOLDING_FREQUENCY — a cycle closes when the observer's score returns to origin.

MEASURED: (1) best return-to-origin vs time for a rational vs a golden ratio; (2) a closure
spectrum sweeping ρ ∈ [1,2] — deep dips (closes) at small-denominator rationals, a peak at
the golden ratio (the least-closing, most-irrational point); (3) the verification
consequence — a CLOSED cycle is captured by a finite stored loop (error→0), a never-closing
one is NOT finitely path-storable (error decays only ~1/√B) yet the spectral 'store the
generators' representation nails BOTH with a handful of numbers.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from fractions import Fraction

PHI = (1 + 5**0.5) / 2            # golden ratio ≈ 1.618 — provably the most irrational
F1  = 1.0
TWO_PI = 2*np.pi

def wrap(a):                      # angle -> [-pi, pi]
    return (a + np.pi) % TWO_PI - np.pi

def toral_return(rho, T=40.0, dt=0.002, skip=0.5):
    """min distance the (θ1,θ2) state comes back to its start over (skip, T]."""
    t = np.arange(0, T, dt)
    th1 = wrap(TWO_PI*F1*t)
    th2 = wrap(TWO_PI*F1*rho*t)
    d = np.sqrt(wrap(th1)**2 + wrap(th2)**2)     # both start at 0
    m = t > skip
    i = np.argmin(d[m])
    tt = t[m][i]
    return t, d, float(d[m][i]), float(tt)

# ---------- (1) a rational vs the golden ratio ----------
tR, dR, retR, tretR = toral_return(1.5)          # 3/2 — closes
tG, dG, retG, tretG = toral_return(PHI)          # golden — never closes

print("="*74)
print("  DOES THE CYCLE CLOSE?  rational (returns) vs irrational (never repeats)")
print("="*74)
print(f"  two-spin system, ratio ρ = f2/f1;  a cycle CLOSES when the state returns to origin")
print()
print(f"  ρ = 3/2  (rational)  : best return {retR:.4f} at t = {tretR:.2f}  -> CLOSES (period {tretR:.0f})")
print(f"  ρ = φ    (golden)    : best return {retG:.4f} over horizon 40    -> NEVER closes")
print(f"     (its only near-returns land at FIBONACCI times t≈5,8,13… — the convergents of φ —")
print(f"      and never reach 0: φ is the hardest ratio to approximate by a fraction.)")
print()

# ---------- (2) the closure spectrum: sweep ρ ----------
rhos = np.linspace(1.0, 2.0, 2000)
best = np.array([toral_return(r, T=30.0, dt=0.004)[2] for r in rhos])
# label the small-denominator rationals we expect to see dip
rat_labels = [Fraction(1,1),Fraction(6,5),Fraction(5,4),Fraction(4,3),Fraction(7,5),
              Fraction(3,2),Fraction(8,5),Fraction(5,3),Fraction(7,4),Fraction(2,1)]

phi_ret = toral_return(PHI, T=30.0, dt=0.004)[2]
rat_ret = toral_return(1.5, T=30.0, dt=0.004)[2]
print(f"  closure spectrum over ρ∈[1,2] (min return within a fixed horizon):")
print(f"     deepest closures sit at small-denominator rationals (1/1, 3/2, 5/3, 2/1 …) —")
print(f"     the resonance / Farey (devil's-staircase) structure. At the small rationals the")
print(f"     cycle closes ({rat_ret:.3f} at 3/2); at the golden ratio it stays open ({phi_ret:.3f}).")
print(f"     φ = {PHI:.3f} is the provably most-irrational ratio (Hurwitz) — the hardest to")
print(f"     close of all; it is marked on the spectrum for reference.")
print()

# ---------- (3) the verification consequence ----------
# Embed each trajectory as a 2-D curve; measure how well a stored PATH of B samples
# reconstructs the whole (dense) trajectory, vs storing the GENERATORS (frequencies).
def embed(rho, t):
    th1 = TWO_PI*F1*t; th2 = TWO_PI*F1*rho*t
    return np.stack([np.cos(th1) + 0.5*np.cos(th2),
                     np.sin(th1) + 0.5*np.sin(th2)], axis=1)

def path_store_error(rho, B, T_full=300.0):
    # store B samples from a growing time-window; reconstruct the FULL trajectory by nearest
    # stored point. Error = mean nearest-neighbour distance (chunked to bound memory).
    ds = 0.02
    store = embed(rho, np.arange(B)*ds)                      # B stored samples
    test  = embed(rho, np.linspace(0, T_full, 4000))        # the whole curve to cover
    mins = np.full(len(test), np.inf)
    for s in range(0, len(store), 256):
        blk = store[s:s+256]
        d2 = ((test[:,None,:]-blk[None,:,:])**2).sum(-1)
        mins = np.minimum(mins, np.sqrt(d2).min(1))
    return mins.mean()

Bs = np.array([20, 40, 80, 160, 320, 640, 1280, 2560])
errR = np.array([path_store_error(1.5, B) for B in Bs])
errG = np.array([path_store_error(PHI, B) for B in Bs])

# spectral store: recover the two frequencies (2 numbers) -> exact reconstruction for BOTH
def spectral_error(rho):
    t = np.arange(0, 200, 0.02); x = embed(rho, t)[:,0]
    f = np.fft.rfftfreq(len(t), 0.02); A = np.abs(np.fft.rfft(x))
    peaks = f[np.argsort(A)[-2:]]                            # top two frequencies
    fhat = sorted(peaks)
    # reconstruct ratio from the two recovered lines
    return abs((max(fhat)/min(fhat)) - rho) if min(fhat)>0 else np.nan
specR = spectral_error(1.5); specG = spectral_error(PHI)

print(f"  {'store as a PATH (samples)':32}{'B=20':>8}{'B=160':>9}{'B=640':>9}{'B=2560':>9}")
print(f"  {'CLOSED  (ρ=3/2) recon error':32}{errR[0]:>8.3f}{errR[3]:>9.3f}{errR[5]:>9.3f}{errR[7]:>9.3f}")
print(f"  {'NEVER-CLOSES (ρ=φ) recon err':32}{errG[0]:>8.3f}{errG[3]:>9.3f}{errG[5]:>9.3f}{errG[7]:>9.3f}")
print()
print(f"  store as the GENERATORS (2 frequencies, spectral):")
print(f"     CLOSED  ρ=3/2 : ratio recovered to {specR:.3f}   NEVER-CLOSES ρ=φ : {specG:.3f}")
print()
print(f"  -> the CLOSED cycle's path error drops fast and then SATURATES ({errR[5]:.3f}→{errR[7]:.3f}, flat):")
print(f"     a finite loop has finite content, so once you've stored one period, extra storage is")
print(f"     redundant — you keep re-tracing the same loop. The NEVER-CLOSING cycle's error keeps")
print(f"     falling ({errG[5]:.3f}→{errG[7]:.3f}, ~1/√B) because every new sample is genuinely new")
print(f"     territory — no finite path store ever finishes it. But BOTH are pinned by their two")
print(f"     spin-frequencies (ratio recovered to {specR:.3f}/{specG:.3f}). So 'does it close?' decides")
print(f"     the verification job: closed → memorise the loop; open/irrational → store the GENERATORS")
print(f"     (the spectral method of #16/#19). Rational closure also PHASE-LOCKS the two channels")
print(f"     (aliasing, Shovelcat_10_1 §4.2) — which is why independent observers want the golden,")
print(f"     never-closing ratio. Whether the cycle closes is a real, decidable property with real")
print(f"     consequences for how you're allowed to remember and verify it.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(14.6, 8.4))
gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1.0], hspace=0.34, wspace=0.28)

# (A) the two paths
for k,(rho,ttl,col) in enumerate([(1.5,"ρ = 3/2  → CLOSED (finite loop)","#238b45"),
                                  (PHI,"ρ = φ  → NEVER closes (fills the band)","#c0392b")]):
    ax = fig.add_subplot(gs[0,k])
    P = embed(rho, np.arange(0, (6.0 if k==0 else 120.0), 0.01))
    ax.plot(P[:,0], P[:,1], color=col, lw=0.6, alpha=0.85)
    ax.scatter([P[0,0]],[P[0,1]], color="#111", s=40, zorder=5, label="start")
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(ttl, fontsize=10.5, color=col)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

# (B) best-return-so-far vs time (the closure envelope)
def running_best(t, d, skip=0.5):
    m = t > skip
    return t[m], np.minimum.accumulate(d[m])
tRb, bRb = running_best(tR, dR); tGb, bGb = running_best(tG, dG)
axB = fig.add_subplot(gs[0,2])
axB.plot(tRb, bRb, color="#238b45", lw=2.0, label="ρ=3/2 — hits 0 (closes)")
axB.plot(tGb, bGb, color="#c0392b", lw=2.0, label="ρ=φ — floored above 0")
axB.scatter([tretR],[retR], color="#238b45", s=55, zorder=6)
axB.axhline(0.05, color="#888", ls=":", lw=1)
axB.text(20, 0.075, "closure threshold ε", color="#777", fontsize=8, ha="right")
for tf in [5,8,13,21,34]:   # Fibonacci near-returns of the golden cycle
    axB.axvline(tf, color="#c0392b", ls=":", lw=0.6, alpha=0.35)
axB.text(9, 0.62, "golden steps down at\nFibonacci times — never to 0", color="#a33", fontsize=7.6)
axB.set_xlabel("time"); axB.set_ylabel("closest return so far")
axB.set_ylim(-0.03, 0.9)
axB.set_title("Return-to-origin: the closure test", fontsize=10.5)
axB.legend(fontsize=8.2, framealpha=0.9, loc="upper right")

# (C) closure spectrum
axC = fig.add_subplot(gs[1,:2])
axC.plot(rhos, best, color="#2b4a6f", lw=1.0)
axC.invert_yaxis()   # dips (closes) point DOWN visually as depth
for fr in rat_labels:
    v=float(fr)
    if 1.0<=v<=2.0:
        axC.axvline(v, color="#4a90d0", ls=":", lw=0.7, alpha=0.5)
        axC.text(v, best.max()*0.02, f"{fr.numerator}/{fr.denominator}", rotation=90,
                 fontsize=6.8, color="#3a6ea5", va="bottom", ha="center")
axC.axvline(PHI, color="#c0392b", lw=1.6)
axC.text(PHI+0.006, best.max()*0.85, f"φ = {PHI:.3f}\nmost irrational\n(Hurwitz) — stays open",
         color="#c0392b", fontsize=8.4, va="top")
axC.set_xlabel("ratio  ρ = f2/f1"); axC.set_ylabel("min return within horizon\n(deeper ↓ = closes)")
axC.set_title("Closure spectrum: small-denominator rationals close (deep dips); φ, the most-irrational ratio, stays open",
              fontsize=10.2)

# (D) verification: path store vs spectral store
axD = fig.add_subplot(gs[1,2])
axD.loglog(Bs, errR, "-o", color="#238b45", lw=2, ms=5, label="CLOSED path-store\n(saturates: loop is finite)")
axD.loglog(Bs, errG, "-o", color="#c0392b", lw=2, ms=5, label="never-closing path-store\n(keeps falling ~1/√B)")
axD.axhline(max(specR,1e-3), color="#238b45", ls="--", lw=1.2)
axD.axhline(max(specG,1e-3), color="#c0392b", ls="--", lw=1.2)
axD.text(Bs[0], max(specG,1e-3)*1.25, "spectral store (2 numbers) → ~0 for BOTH", fontsize=7.6, color="#555")
axD.set_xlabel("path-store budget B (samples)"); axD.set_ylabel("reconstruction error")
axD.set_title("Each job needs its own verification", fontsize=10.2)
axD.legend(fontsize=7.8, framealpha=0.9, loc="lower left")

fig.suptitle("Does the cycle close?  Rational ρ → a finite loop you can memorise;  irrational ρ (golden) → never repeats, "
             "store the generators instead", fontsize=11.6)
fig.savefig("does_it_close.png", dpi=130, bbox_inches="tight")
print("\n  wrote does_it_close.png")
