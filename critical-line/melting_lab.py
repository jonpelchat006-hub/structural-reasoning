"""My exploration: the pinning horizon.
Hypothesis (furniture-derived): the two-eyed approximant with N gears pins the line only up
to the height where the root cell saturates, t ~ 2 pi N^2; off-line pair-defects melt in as a
UNIVERSAL function of u = t/(2 pi N^2) (the central eye has no other scale).
Also: the inter-level flow law lead ~ (1/2) pi(sqrt x) should hold mod 3 as well (p^2 = 1 mod 3).
"""
import numpy as np, json
from scipy.special import loggamma

def chi(s):
    return np.exp(s*np.log(2) + (s-1)*np.log(np.pi) + np.log(np.sin(np.pi*s/2)) + loggamma(1-s))

def vortices(f, sig, tt):
    a = np.angle(f)
    w = lambda d: (d + np.pi) % (2*np.pi) - np.pi
    wind = w(a[:-1,1:]-a[:-1,:-1]) + w(a[1:,1:]-a[:-1,1:]) \
         + w(a[1:,:-1]-a[1:,1:]) + w(a[:-1,:-1]-a[1:,:-1])
    iy, ix = np.where(np.abs(wind) > 5.0)
    return 0.5*(sig[ix]+sig[ix+1]), 0.5*(tt[iy]+tt[iy+1])

sig = np.linspace(-0.35, 1.35, 341)
tt  = np.linspace(20.0, 420.0, 4001)
S = sig[None,:] + 1j*tt[:,None]
CHI = chi(S)

results = []
for N in [3, 4, 5, 6, 8, 10, 12]:
    f1 = sum(np.exp(-S*np.log(n)) for n in range(1, N+1))
    f2 = f1 + CHI*sum(np.exp((S-1)*np.log(n)) for n in range(1, N+1))
    sx, ty = vortices(f2, sig, tt)
    horizon = 2*np.pi*N*N
    # bin by u = t/(2 pi N^2); defect = off-line vortex (|Re-1/2| > 0.02)
    ubins = np.linspace(0.1, 3.0, 30)
    for i in range(len(ubins)-1):
        lo, hi = ubins[i]*horizon, ubins[i+1]*horizon
        m = (ty >= lo) & (ty < hi) & (lo >= 20) & (hi <= 420)
        if not m.any() and not (lo >= 20 and hi <= 420): continue
        if hi > 420 or lo < 20: continue
        n_tot = int(m.sum())
        n_def = int(((np.abs(sx-0.5) > 0.02) & m).sum())
        if n_tot > 0:
            results.append(dict(N=N, u=float(0.5*(ubins[i]+ubins[i+1])),
                                defect_frac=n_def/n_tot, n=n_tot))
json.dump(results, open("/home/claude/rh_voidline/melting_res.json","w"), indent=0)

# summary: defect fraction below vs above the horizon, per N
print("N   below horizon (u<1)   above horizon (u>1)")
for N in [3,4,5,6,8,10,12]:
    lo = [r for r in results if r["N"]==N and r["u"]<1]
    hi = [r for r in results if r["N"]==N and r["u"]>1]
    fl = sum(r["defect_frac"]*r["n"] for r in lo)/max(sum(r["n"] for r in lo),1)
    fh = sum(r["defect_frac"]*r["n"] for r in hi)/max(sum(r["n"] for r in hi),1)
    print("%-3d   %.3f (n=%d)          %.3f (n=%d)"%(N, fl, sum(r['n'] for r in lo), fh, sum(r['n'] for r in hi)))

# --- second check: the level-flow law mod 3 ---
from sympy import primerange, primepi
print()
for X in [2*10**6, 10**7]:
    lead = 0
    for p in primerange(5, X):
        lead += 1 if p % 3 == 2 else -1
    print("mod 3, x=%-9d  lead = %4d   (1/2) pi(sqrt x) = %6.1f"%(X, lead, 0.5*primepi(int(X**0.5))))
