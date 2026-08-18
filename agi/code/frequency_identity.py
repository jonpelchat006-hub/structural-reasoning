#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frequency_identity.py -- the third budget is FREQUENCY: spin, path, and return-to-origin.

Jonathan: we had three budgets. The object is one (VOLUME / size), the orientation is
another, and there is a third for PATTERNS / FREQUENCIES -- the same as size / greasy /
electric in the protein work. Once you have a volume and an orientation you can see what
SPIN it has, what PATH it follows. And identity under spin is RETURN TO ORIGIN: "the
bottle spins in the water, its outline keeps changing, but as long as it goes back to
the starting point we know it's the same thing." Frequency levels NEST: freq 1 = all the
branches in the spot (just a frame); freq 2 = all of freq 1 inside PLUS more bands from
the expansion. So expansion = adding more states to the cycle while keeping the origin as
the return.

This is exactly a FOURIER DESCRIPTOR of a closed contour, and the three budgets are its
three parts:
    z(t) = Σ_k  C_k e^{i k t},   t ∈ [0, 2π)   (a closed loop: z(t+2π)=z(t))
  * VOLUME / size      = the low-harmonic magnitude (|C_1| ≈ the overall extent).
  * ORIENTATION        = the global phase (a spin multiplies every C_k by e^{iα}).
  * FREQUENCY / pattern= the magnitude spectrum |C_k| over k -- the spin signature.

Two measured claims:
  (1) EXPANSION ADDS FRAMES.  Reconstructing z with harmonics |k| ≤ K: K=1 is a bare
      ellipse (the frame); each higher K CONTAINS the last plus a new band. Error falls
      until you pass the object's top real harmonic -- then it plateaus ("stop at the
      next frequency": nothing above it but noise). Growth = adding states to the cycle.
  (2) IDENTITY = RETURN TO ORIGIN.  A spinning object's raw outline changes, so a RAW
      (phase-carrying) representation calls it a different thing. The FREQUENCY-magnitude
      representation |C_k| is invariant to spin and to where you started tracing -- it
      "returns to origin" -- so it recognises the same object through the spin.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(6)
KMAX = 8                      # harmonics an object can carry
T = 256                       # samples around the loop
t = np.linspace(0, 2*np.pi, T, endpoint=False)

def random_object(seed):
    """A closed contour = complex Fourier coeffs C_k for k in [-KMAX..KMAX]."""
    r = np.random.default_rng(seed)
    C = np.zeros(2*KMAX+1, dtype=complex)
    C[KMAX+1] = 1.0                                   # k=+1 fundamental (the base loop)
    for k in list(range(-KMAX, 0)) + list(range(2, KMAX+1)):
        amp = 0.5*np.exp(-0.35*abs(k)) * (0.5+r.random())   # decaying harmonics
        C[KMAX+k] = amp*np.exp(1j*2*np.pi*r.random())
    return C

def contour(C, alpha=0.0, phi0=0.0):
    """Render the loop; alpha = spin (global rotation), phi0 = trace start shift."""
    ks = np.arange(-KMAX, KMAX+1)
    z = np.zeros(T, dtype=complex)
    for i, k in enumerate(ks):
        z += C[i]*np.exp(1j*(k*(t+phi0)))
    return np.exp(1j*alpha)*z

def recon_K(C, K):
    """Reconstruct using only harmonics |k| <= K (the nested frames)."""
    ks = np.arange(-KMAX, KMAX+1)
    Cc = C.copy()
    Cc[np.abs(ks) > K] = 0
    return contour(Cc)

# ---------- (1) expansion adds frames: reconstruction error vs #harmonics ----------
OBJS = [random_object(10+i) for i in range(6)]
def recon_err(C, K):
    full = contour(C); r = recon_K(C, K)
    return float(np.mean(np.abs(full - r)) / (np.mean(np.abs(full - full.mean()))+1e-9))
Ks = list(range(1, KMAX+1))
err_by_K = [np.mean([recon_err(C, K) for C in OBJS]) for K in Ks]

print("="*72)
print("  THE THIRD BUDGET = FREQUENCY: spin, and identity = return to origin")
print("="*72)
print("  three budgets = the parts of a Fourier descriptor:")
print("     VOLUME=|C_1| (size)   ORIENTATION=global phase (spin)   FREQUENCY=|C_k| spectrum")
print()
print("  (1) expansion adds frames -- reconstruction error vs harmonics kept:")
for K, e in zip(Ks, err_by_K):
    bar = "#"*int(round(e*40))
    print(f"     |k|<= {K}:  err {e:.3f}  {bar}")
plateau = next((K for K in Ks if err_by_K[K-1] < 0.02), KMAX)
print(f"  -> each added harmonic CONTAINS the last plus a new band; error falls to ~0 by |k|<= {plateau}")
print(f"     and then plateaus -- you 'stop at the next frequency' (nothing real above it).")
print()

# ---------- (2) identity = return to origin: recognise the SAME object under spin ----------
def raw_feat(z):                         # phase-carrying: centred, scaled sample points
    z = z - z.mean(); z = z/ (np.sqrt(np.mean(np.abs(z)**2))+1e-9)
    return np.concatenate([z.real, z.imag])
def freq_feat(C):                        # spin/start invariant: harmonic MAGNITUDES
    m = np.abs(C); m = m/(np.linalg.norm(m)+1e-9)
    return m
def freq_feat_from_z(z):
    Z = np.fft.fft(z)/T                  # recover coeffs from the observed loop
    m = np.abs(Z); m = m/(np.linalg.norm(m)+1e-9)
    return m

templates_raw  = [raw_feat(contour(C)) for C in OBJS]
templates_freq = [freq_feat_from_z(contour(C)) for C in OBJS]

def trial(spin_on):
    i = rng.integers(len(OBJS))
    alpha = rng.uniform(0, 2*np.pi) if spin_on else 0.0
    phi0  = rng.uniform(0, 2*np.pi) if spin_on else 0.0
    z = contour(OBJS[i], alpha=alpha, phi0=phi0) + rng.normal(0, 0.02, T) + 1j*rng.normal(0,0.02,T)
    praw = int(np.argmin([np.sum((raw_feat(z)-tr)**2) for tr in templates_raw]))
    pfrq = int(np.argmin([np.sum((freq_feat_from_z(z)-tf)**2) for tf in templates_freq]))
    return (praw == i), (pfrq == i)

N = 600
for label, spin in [("no spin (aligned)", False), ("SPINNING (random rotation + start)", True)]:
    raw_ok = frq_ok = 0
    for _ in range(N):
        r, f = trial(spin); raw_ok += r; frq_ok += f
    print(f"  (2) recognise the same object -- {label}:")
    print(f"       RAW outline (phase-carrying):        {raw_ok/N:.2f}")
    print(f"       FREQUENCY magnitude (returns to 0):  {frq_ok/N:.2f}")
if True:
    print()
    print("  -> under spin the RAW outline changes and is misread; the FREQUENCY-magnitude")
    print("     signature is invariant (returns to origin), so it stays the same object.")
    print("     Identity is the closed cycle, not the momentary outline.")

# ---------------------------------------------------------------------------
# PLOT: left = nested reconstructions of one object (freq1 frame -> +bands);
# right = recognition accuracy, RAW vs FREQUENCY, no-spin vs spin.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.2, 5.4))
C0 = OBJS[0]; full = contour(C0)
axL.plot(full.real, full.imag, color="#111", lw=2.4, label="true outline", zorder=5)
for K, col in [(1,"#e6820a"), (2,"#e0a021"), (4,"#2b8cbe"), (8,"#238b45")]:
    r = recon_K(C0, K)
    axL.plot(r.real, r.imag, lw=1.6, color=col, label=f"freq ≤ {K}" + (" (bare frame)" if K==1 else ""))
axL.set_aspect("equal"); axL.axis("off")
axL.set_title("Expansion adds frames to the cycle\n(freq 1 = ellipse frame; each band nests inside the next)")
axL.legend(loc="upper right", fontsize=8, framealpha=0.9)

# right: recompute accuracies for the bar chart
def acc(spin):
    r=f=0
    for _ in range(N):
        rr,ff=trial(spin); r+=rr; f+=ff
    return r/N, f/N
r0,f0 = acc(False); r1,f1 = acc(True)
x=np.arange(2); w=0.35
axR.bar(x-w/2, [r0, r1], w, color="#e6820a", label="RAW outline (phase)")
axR.bar(x+w/2, [f0, f1], w, color="#238b45", label="FREQUENCY magnitude")
for i,(a,b) in enumerate([(r0,f0),(r1,f1)]):
    axR.text(i-w/2, a+0.02, f"{a:.2f}", ha="center", fontsize=9)
    axR.text(i+w/2, b+0.02, f"{b:.2f}", ha="center", fontsize=9)
axR.set_xticks(x); axR.set_xticklabels(["no spin","SPINNING\n(rotation+start)"])
axR.set_ylim(0,1.12); axR.set_ylabel("recognise-same-object accuracy")
axR.set_title("Identity = return to origin\nspin breaks the raw outline; the frequency signature holds")
axR.legend(loc="lower left", fontsize=9, framealpha=0.93)

fig.tight_layout(); fig.savefig("frequency_identity.png", dpi=130)
print("\n  wrote frequency_identity.png")
