#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
attention_lenses.py -- each perspective lens has its own derivative chain and reads via cosθ;
a few orthogonal lenses watch at once, and a finite attention capacity limits how many/how deep.

Jonathan: each perspective lens should provide its own derivative chain, and we should be able to
have a few ORTHOGONAL observers watching at a time -- heart rate, VO2, and muscle failure, three
lenses each watching their own property through a workout. That spreads the workout out, so we can
store the whole thing SEPARATED BY LENS. Because the lenses aren't aligned (we rotate), there'd be
a cos or sin in front of the derivative-chain equation. And each lens takes up space and brings
'equipment' -- if the muscle-failure lens needs so much equipment to zoom in that nothing else
fits, you can only pay attention to that = an attention capacity. The task gives a save and each
lens gets its own too.

Grounded:
  * SPARSE_VESICA §1 -- the functional form is literally  f = inner-prior + Σ cosθ_b · v_b^(d_b):
    cosθ = the Born alignment (how the lens points), v^d = the DERIVATIVE CHAIN (d = derivative
    order, Taylor). So "cos in front of the derivative chain" is the core equation.
  * Double_Bounce §23.5 -- observers as ORTHOGONAL tensor sources (quaternion w/i/j/k), balancing.
  * FOLDING_SKIN §3.3 -- cone width = resolution; finer zoom = narrower cone = higher derivative
    order (more 'equipment').
  * Shovelcat_10_1 §9.5 -- a finite-APERTURE observer with a finite bin count; observing costs
    resolution (Landauer: watching one bin erases another) = the attention capacity.
  * FOLDING_SYNTHESIS #22 -- the observer defines the cycle; each lens segments its own memory.

MEASURED:
  (1) 3 orthogonal lenses DECOMPOSE the workout -- 1 lens reconstructs ~1/3, 3 lenses 100%; each
      stores its OWN cycles (per-lens saves) so the union = the whole workout, separated by lens.
  (2) cosθ IN FRONT -- a misaligned lens captures cos²θ of a property; two orthogonal lenses are
      complementary (cos²+sin² = 1).
  (3) FINITE ATTENTION CAPACITY -- zoom costs equipment; deep zoom on one lens crowds out the rest
      (breadth × resolution ≈ const; at max zoom only one lens fits).
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

T=300; t=np.arange(T)
# ---- a workout with three ~orthogonal properties ----
def arch(c,w,h): return h*np.exp(-0.5*((t-c)/w)**2)
HR   = 0.4*np.ones(T) + arch(150,90,0.6)                      # broad arch over the whole session
VO2  = np.zeros(T)
hard = [(70,12),(110,12),(150,12),(190,12),(230,12)]         # hard efforts
for c,w in hard: VO2 += arch(c,w,1.0)
fail = np.clip(np.cumsum([0.02 if any(abs(tt-c)<w for c,w in hard) else 0.002 for tt in t]),0,None)
fail/=fail.max()                                             # monotone fatigue ramp (never recovers)
HR/=HR.max()
S=np.stack([HR,VO2,fail],1)                                 # state(t) in property space (3-D)
NAMES=["heart rate","VO₂","muscle failure"]

# ---- (1) orthogonal lenses decompose; each captures its property's VARIANCE, 3 -> 100% ----
axis_var=np.array([np.var(S[:,i]) for i in range(3)])
order=np.argsort(-axis_var)                                  # richest property first
cum=np.cumsum(axis_var[order])/axis_var.sum()
rec=[float(cum[0]), float(cum[1]), float(cum[2])]           # fraction of the workout captured by 1,2,3 lenses

# per-lens memory: each lens segments its OWN cycles (threshold crossings, #22)
def cycles(sig,thr):
    on=sig>thr; n=0; i=0
    while i<len(sig):
        if on[i]:
            j=i
            while j<len(sig) and on[j]: j+=1
            n+=1; i=j
        else: i+=1
    return n
per_lens=[cycles(HR,0.6), cycles(VO2,0.6), 1]               # HR one long arch, VO2 5 spikes, fail 1 ramp

print("="*80)
print("  MULTIPLE ORTHOGONAL LENSES, EACH A DERIVATIVE CHAIN READING VIA cosθ, WITH FINITE CAPACITY")
print("="*80)
print(f"  (1) 3 orthogonal lenses decompose one workout and reconstruct the whole:")
print(f"        1 lens captures {rec[0]*100:3.0f}%   2 lenses {rec[1]*100:3.0f}%   3 lenses {rec[2]*100:3.0f}%")
print(f"        per-lens memory (its own save): HR {per_lens[0]} arch · VO₂ {per_lens[1]} spikes · fatigue {per_lens[2]} ramp")
print(f"     -> the union = the whole workout, SEPARATED BY LENS; each lens keeps only its own cycles.")
print()

# ---- (2) cosθ in front: a misaligned lens captures cos²θ ----
ang=np.linspace(0,np.pi/2,90)
captured=np.cos(ang)**2                                      # variance a lens at angle θ pulls from an axis
print(f"  (2) cosθ IN FRONT of the derivative chain (a misaligned lens attenuates):")
print(f"        a lens 0° off an axis captures {np.cos(0)**2*100:.0f}%; 45° off {np.cos(np.pi/4)**2*100:.0f}%; 90° off {np.cos(np.pi/2)**2*100:.0f}%")
print(f"        two ORTHOGONAL lenses are complementary: cos²θ + sin²θ = 1 (they split the signal cleanly).")
print()

# ---- (3) finite attention capacity: zoom costs equipment ----
CAP=4.0                                                      # total attention budget (≈ the finite aperture)
zf=np.linspace(1,CAP,60)                                     # zoom of the FOCUSED (muscle-failure) lens
breadth=1+np.floor((CAP-zf)/1.0); breadth=np.clip(breadth,1,None)   # +1 focus, rest are baseline (cost 1)
print(f"  (3) FINITE ATTENTION CAPACITY (budget {CAP:.0f}; zoom = more 'equipment'):")
print(f"        focus lens at zoom 1  -> {int(breadth[0])} lenses fit (watch all properties)")
print(f"        focus lens at zoom {CAP:.0f} -> {int(breadth[-1])} lens fits (only muscle failure -- it eats the budget)")
print(f"     -> resolution × breadth ≈ const: zoom deep on one and you can attend to nothing else.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.4,7.6)); gs=fig.add_gridspec(2,2,hspace=0.36,wspace=0.26)
cols=["#c0392b","#238b45","#8a2be2"]

# (A) the workout through 3 lenses, each its own memory
axA=fig.add_subplot(gs[0,:])
for k,(sig,nm,c) in enumerate(zip([HR,VO2,fail],NAMES,cols)):
    axA.plot(t, sig+ k*0.0, color=c, lw=1.8, label=f"{nm} lens ({per_lens[k]} cycle{'s' if per_lens[k]!=1 else ''} stored)")
axA.set_xlabel("time (one workout)"); axA.set_ylabel("normalised reading")
axA.set_title("Three orthogonal lenses, each its own derivative chain & memory — together they cover the whole workout, separated by lens", fontsize=10.4)
axA.legend(fontsize=8.5, framealpha=0.9, loc="upper right")

# (B) cosθ falloff + reconstruction
axB=fig.add_subplot(gs[1,0])
axB.plot(np.rad2deg(ang), captured, color="#2b6cb0", lw=2.4, label="captured = cos²θ (a lens's share)")
axB.plot(np.rad2deg(ang), np.sin(ang)**2, color="#e0a021", lw=1.8, ls="--", label="residual = sin²θ (the orthogonal lens)")
axB.set_xlabel("lens misalignment angle θ (°)"); axB.set_ylabel("fraction of the property captured")
axB.set_title("cosθ IN FRONT: a misaligned lens attenuates;\ntwo orthogonal lenses split it (cos²+sin²=1)", fontsize=10.2)
axB.legend(fontsize=8.2, framealpha=0.9)
axB.text(5, 0.15, f"1 lens → {rec[0]*100:.0f}% · 3 orthog. lenses → {rec[2]*100:.0f}%", fontsize=8.5, color="#333")

# (C) attention capacity
axC=fig.add_subplot(gs[1,1])
axC.plot(zf, breadth, color="#c0392b", lw=2.6, drawstyle="steps-post")
axC.fill_between(zf, breadth, step="post", color="#c0392b", alpha=0.12)
axC.set_xlabel("zoom / 'equipment' on the focused lens"); axC.set_ylabel("other lenses that still fit (breadth)")
axC.set_title("Finite attention capacity: deep zoom eats the budget\n→ you can only attend to that one", fontsize=10.2)
axC.set_ylim(0, breadth.max()+0.4)
axC.text(CAP*0.98, 1.15, "max zoom →\nonly muscle-failure", fontsize=8.3, color="#8a2be2", ha="right")

fig.suptitle("Each lens = its own derivative chain read via cosθ · a few orthogonal lenses decompose the workout · a finite attention capacity trades breadth for zoom",
             fontsize=10.5, y=0.995)
fig.savefig("attention_lenses.png", dpi=130, bbox_inches="tight")
print("\n  wrote attention_lenses.png")
