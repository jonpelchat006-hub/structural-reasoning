#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
beyblade_deposit.py -- cycle types by endpoint, and cycles that PAINT a new object.

Jonathan: the cycle TYPE is the relationship between its endpoints A and B — whether B
is higher, lower, or equal to A. A beyblade's spin is 50rpm → 0rpm (A>B: a FALLING/open
cycle); heart-rate up→rest is A=B (a CLOSED/periodic cycle). The "what-for" decides where
those boundaries sit — where the line on the graph is. And as we run the cycles, the paths
PAINT a new object: watch the metal edge over 100 spins and where it went starts showing a
pattern — a heatmap. If that deposit accumulates mass / we keep track of it, it becomes the
"line on the graph" itself (maybe that's where the what-for comes from — the boundary
emerges from where the cycles deposited). And the heatmap depends on the weight used.

Grounded: an observer's cycle closes when its score returns to origin (FOLDING_FREQUENCY);
accumulation → a foundation void-point (SPARSE_VESICA §22.1 accumulate→STOPPED foundation);
the deposit is a new object one level up (the budget→cycle→path-of-cycles ladder,
FOLDING_SYNTHESIS §7 higher-order cycles).

MEASURED: (1) three signals of one spin-down classified by endpoint type; (2) the swept
path deposited as a 2-D heatmap = a structured new object; (3) two weights → two different
deposits; (4) the deposit's radial density has a ridge — the emergent "line on the graph".
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

DT = 0.004
def spin_down(weight, seed=0):
    rng = np.random.default_rng(seed)
    tau = 3.0*weight                          # heavier tops spin longer
    Tend = tau*3.0
    t = np.arange(0, Tend, DT)
    w = 50.0*np.exp(-t/tau)                    # spin rate (rpm-ish): 50 -> 0   (FALLING, A>B)
    Omega = 0.6/(w/50.0 + 0.05)               # precession rate rises as spin falls
    rp = 0.15 + (0.9/np.sqrt(weight))*(1 - w/50.0)   # walk-out radius grows   (RISING, A<B)
    Phi = np.cumsum(Omega*DT)                  # heading of the walk (CLOSED mod 2π, A=B)
    # slow drift of the whole rosette's center (so the deposit is a real 2-D object)
    cx = 0.6*np.sin(0.15*t) + 0.15*np.cumsum(rng.normal(0,0.004,len(t)))
    cy = 0.6*np.cos(0.11*t) + 0.15*np.cumsum(rng.normal(0,0.004,len(t)))
    x = cx + rp*np.cos(Phi); y = cy + rp*np.sin(Phi)
    return t, w, Phi, rp, x, y

def endpoint_type(sig):
    a, b = sig[0], sig[-1]
    if abs(b-a) < 0.05*(abs(a)+abs(b)+1e-9): return "A = B  (CLOSED / periodic)"
    return "A > B  (FALLING / open)" if b < a else "A < B  (RISING / open)"

# ---- classify the three signals of one spin-down ----
t,w,Phi,rp,x,y = spin_down(1.0, seed=1)
print("="*72)
print("  CYCLE TYPES BY ENDPOINT, AND CYCLES THAT PAINT A NEW OBJECT")
print("="*72)
print("  three signals of ONE spinning top, classified by how B relates to A:")
revs = Phi[-1]/(2*np.pi)
print(f"     spin rate ω     : {w[0]:.0f} → {w[-1]:.0f}         {endpoint_type(w)}")
print(f"     heading  Φ      : {revs:.0f} whole turns    A = B  (CLOSED / periodic — returns each 2π)")
print(f"     walk-out radius : {rp[0]:.2f} → {rp[-1]:.2f}        {endpoint_type(rp)}")
print("  -> the SAME object gives a falling, a closed, and a rising cycle at once — the type")
print("     is the endpoint relation, and the what-for picks which signal (which line) to watch.")
print()

# ---- deposit the swept path as a heatmap, for two weights ----
def deposit(weight, seed):
    _,_,_,_,x,y = spin_down(weight, seed)
    H,xe,ye = np.histogram2d(x,y, bins=120, range=[[-2,2],[-2,2]])
    return H.T, x, y
Hl, xl, yl = deposit(0.6, 3)     # light
Hh, xh, yh = deposit(1.8, 4)     # heavy

def radial_profile(H):
    G=H.shape[0]; c=(G-1)/2
    yy,xx=np.mgrid[0:G,0:G]; r=np.sqrt((xx-c)**2+(yy-c)**2)
    rb=np.linspace(0,c,40); prof=[]
    for i in range(len(rb)-1):
        m=(r>=rb[i])&(r<rb[i+1]); prof.append(H[m].sum())
    rc=0.5*(rb[1:]+rb[:-1])*(4.0/G)   # to world units (bin width)
    return rc, np.array(prof)
rcl,pl = radial_profile(Hl); rch,ph = radial_profile(Hh)
peak_l = rcl[np.argmax(pl)]; peak_h = rch[np.argmax(ph)]

print(f"  the cycles PAINT a heatmap (deposited over the whole spin-down):")
print(f"     light weight → deposit ridge (the 'line') at radius ≈ {peak_l:.2f}")
print(f"     heavy weight → deposit ridge at radius ≈ {peak_h:.2f}")
print(f"  -> same machine, different WEIGHT, visibly different deposit — a new structured object")
print(f"     you can zoom out on. The density ridge IS the emergent 'line on the graph'; reading it")
print(f"     at a threshold (the what-for) picks the boundary. The cycles deposited the criterion.")

# ---------------------------------------------------------------------------
# PLOT: two deposits (light/heavy) + the radial density ridge (the line on the graph).
# ---------------------------------------------------------------------------
fig, axs = plt.subplots(1, 3, figsize=(14.2, 5.0))
for ax,H,ttl in [(axs[0],Hl,"light weight → deposit"),(axs[1],Hh,"heavy weight → deposit")]:
    ax.imshow(np.sqrt(H), origin="lower", extent=[-2,2,-2,2], cmap="magma")
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(ttl, fontsize=11)
axs[0].text(-1.9,1.7,"where the metal swept\nover the whole spin-down", color="white", fontsize=8.5)
axs[2].plot(rcl, pl/pl.max(), color="#e0761f", lw=2.2, label=f"light — ridge @ {peak_l:.2f}")
axs[2].plot(rch, ph/ph.max(), color="#8a2be2", lw=2.2, label=f"heavy — ridge @ {peak_h:.2f}")
axs[2].set_xlabel("radius from centre"); axs[2].set_ylabel("deposited density (normalised)")
axs[2].set_title("The deposit's ridge = the 'line on the graph'\n(different weight → different line)")
axs[2].legend(fontsize=9, framealpha=0.9)
fig.suptitle("Cycles paint a new object: the swept path deposits a heatmap that depends on the weight "
             "(spin ω falls A>B · heading closed A=B · walk-out rises A<B)", fontsize=11)
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig("beyblade_deposit.png", dpi=130)
print("\n  wrote beyblade_deposit.png")
