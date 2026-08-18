#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
think_search.py -- thinking = searching the three budgets, each with its own method.

Jonathan: exploring / just thinking is trying new orientations and shapes, swinging the
structure around an anchor and switching which anchor you're on. The shape is a person:
the VOLUME budget is height/weight (grow it or make small changes); the ORIENTATION
budget is the pose and position (which reference points, which muscles engaged); and you
can also try different SPINS and which anchor you look from -- "but different spins would
probably need other search methods."

That last line is exactly right and it is textbook. A person / shape is carried on the
three budgets = the three parts of a Fourier descriptor (FOLDING_FREQUENCY): a signal
  y(t) = A · sin(f·t + φ)
    A  = VOLUME       (amplitude / size)
    φ  = ORIENTATION  (phase / pose)
    f  = FREQUENCY    (spin / pattern)
"Thinking" = searching A, φ, f to match what you're after. The claim: each budget has its
own search GEOMETRY, so one search method can't do all three --

  * VOLUME (A):      the error-vs-A landscape is a single bowl  -> local search works.
  * ORIENTATION (φ): error-vs-φ is a single cosine bowl per turn -> local search works.
  * FREQUENCY (f):   error-vs-f is JAGGED, many local minima     -> local search STALLS;
                     the spin axis needs a SPECTRAL method (FFT), not gradient descent.

And "switching which anchor you look from" = restarting the search from several vantage
points (multi-start): it partly rescues the spin search, but the matched spectral method
is the clean answer.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng = np.random.default_rng(3)
N = 400
t = np.linspace(0, 10, N)
A0, PHI0, F0 = 1.0, 0.7, 3.0                       # the target person: volume, pose, spin
y = A0*np.sin(F0*t + PHI0) + rng.normal(0, 0.03, N)

def model(A, phi, f): return A*np.sin(f*t + phi)
def mse(A, phi, f):    return float(np.mean((y - model(A,phi,f))**2))

def hillclimb(cost, x0, lo, hi, step0=0.2, iters=200):
    """generic local search (numerical-gradient descent with shrinking step)."""
    x = x0; step = step0
    for _ in range(iters):
        g = (cost(min(x+1e-3,hi)) - cost(max(x-1e-3,lo)))/2e-3
        xn = np.clip(x - step*np.sign(g)*max(abs(g),1e-6)/ (abs(g)+1e-6), lo, hi)
        # simple: move a small step downhill
        xn = np.clip(x - step*np.sign(g), lo, hi)
        if cost(xn) < cost(x): x = xn
        else: step *= 0.6
        if step < 1e-4: break
    return x

# --- per-budget local search, success over many random single starts ---
def success_rate(axis, trials=200, tol=0.15):
    ok = 0
    for _ in range(trials):
        if axis == "volume":
            x0 = rng.uniform(0.1, 3.0)
            xh = hillclimb(lambda A: mse(A, PHI0, F0), x0, 0.05, 3.0)
            ok += abs(xh - A0) < tol
        elif axis == "orientation":
            x0 = rng.uniform(0, 2*np.pi)
            xh = hillclimb(lambda p: mse(A0, p, F0), x0, 0, 2*np.pi)
            d = abs((xh-PHI0+np.pi)%(2*np.pi)-np.pi); ok += d < tol
        else:  # frequency
            x0 = rng.uniform(0.3, 8.0)
            xh = hillclimb(lambda f: mse(A0, PHI0, f), x0, 0.2, 8.0, step0=0.15)
            ok += abs(xh - F0) < tol
    return ok/trials

def freq_multistart(restarts, trials=200, tol=0.15):
    ok = 0
    for _ in range(trials):
        best=None; bestc=1e9
        for _ in range(restarts):
            x0 = rng.uniform(0.3, 8.0)
            xh = hillclimb(lambda f: mse(A0, PHI0, f), x0, 0.2, 8.0, step0=0.15)
            c = mse(A0, PHI0, xh)
            if c<bestc: bestc=c; best=xh
        ok += abs(best - F0) < tol
    return ok/trials

def freq_spectral():
    Y = np.abs(np.fft.rfft(y - y.mean()))
    freqs = np.fft.rfftfreq(N, d=(t[1]-t[0])) * 2*np.pi   # angular frequency
    fhat = freqs[np.argmax(Y)]
    return abs(fhat - F0) < 0.15, fhat

sv = success_rate("volume"); so = success_rate("orientation"); sf = success_rate("frequency")
sf8 = freq_multistart(8)
spec_ok, fhat = freq_spectral()

print("="*72)
print("  THINKING = SEARCHING THE THREE BUDGETS (each needs its own method)")
print("="*72)
print(f"  target person: volume A={A0}, orientation φ={PHI0}, spin f={F0}")
print()
print(f"  local (gradient) search — success over 200 random starts:")
print(f"     VOLUME (amplitude)   : {sv*100:5.0f}%   (single bowl — local search works)")
print(f"     ORIENTATION (phase)  : {so*100:5.0f}%   (single cosine bowl — local search works)")
print(f"     FREQUENCY (spin)     : {sf*100:5.0f}%   (jagged — local search STALLS)")
print()
print(f"  the spin axis needs a different method:")
print(f"     local + 8-anchor multistart : {sf8*100:5.0f}%   (switching anchors partly rescues it)")
print(f"     SPECTRAL (FFT peak)         : {'100' if spec_ok else '  0'}%   (f̂={fhat:.2f} vs {F0}) — the matched method")
print()
print(f"  -> volume and orientation are smooth: you grow/adjust them by local search (small")
print(f"     changes, which reference points, which muscles). The SPIN axis is multimodal --")
print(f"     gradient search gets stuck at the wrong frequency; you need a spectral method.")
print(f"     'Different spins need other search methods,' measured. Switching anchors helps")
print(f"     but the matched (frequency-domain) operator is the clean answer.")

# ---------------------------------------------------------------------------
# PLOT: left = the three error landscapes (why each axis needs its own method);
# right = search success per budget + the spin rescues.
# ---------------------------------------------------------------------------
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.4, 5.2))

AA = np.linspace(0.05, 3, 300);  cA = [mse(a, PHI0, F0) for a in AA]
PP = np.linspace(0, 2*np.pi, 300); cP = [mse(A0, p, F0) for p in PP]
FF = np.linspace(0.2, 8, 600);   cF = [mse(A0, PHI0, f) for f in FF]
def nrm(c): c=np.array(c); return (c-c.min())/(c.max()-c.min()+1e-9)
axL.plot(np.linspace(0,1,300), nrm(cA), color="#2b8cbe", lw=2.0, label="VOLUME (amplitude) — one bowl")
axL.plot(np.linspace(0,1,300), nrm(cP), color="#e0a021", lw=2.0, label="ORIENTATION (phase) — one bowl")
axL.plot(np.linspace(0,1,600), nrm(cF), color="#c0392b", lw=1.6, label="FREQUENCY (spin) — jagged")
axL.set_xlabel("search parameter (normalised range)"); axL.set_ylabel("match error (normalised)")
axL.set_title("Each budget has its own search geometry\nvolume & orientation are smooth; spin is multimodal")
axL.legend(loc="upper center", fontsize=8.6, framealpha=0.93)

labels = ["volume\n(local)","orientation\n(local)","spin\n(local)","spin\n(+anchors)","spin\n(spectral)"]
vals = [sv, so, sf, sf8, 1.0 if spec_ok else 0.0]
cols = ["#2b8cbe","#e0a021","#c0392b","#c86a2b","#238b45"]
axR.bar(range(5), vals, color=cols)
for i,v in enumerate(vals): axR.text(i, v+0.02, f"{v*100:.0f}%", ha="center", fontsize=9)
axR.set_xticks(range(5)); axR.set_xticklabels(labels, fontsize=8.6)
axR.set_ylim(0,1.12); axR.set_ylabel("search success rate")
axR.set_title("Local search solves volume & orientation, stalls on spin;\nthe spin axis needs a spectral method (anchors help)")

fig.tight_layout(); fig.savefig("think_search.png", dpi=130)
print("\n  wrote think_search.png")
