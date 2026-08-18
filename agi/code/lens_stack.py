#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lens_stack.py -- #54: the telescope LENSES are the observer perspectives (#38). They take up space, line up
along the optical axis, and each must sit at its own focal DISTANCE with its BORDER out of the light cone.
Stacking complementary lenses composes the view -- but a weak or redundant lens DRAGS it down (the measured
committee caution, FOLDING_TWO_CONES). And the sky holds a full TAXONOMY of bodies by origin × role: raw
asteroids (outside info), debris fields (old outputs), satellites (communicating tools), drones (intelligent
self-orbiting tools) -- placed at any DISTANCE to change the view.

Jonathan: the telescope lenses are the observer perspectives; they still take up space, line up like a
telescope but with borders out of view, each at a distance it needs to be placed at. There's raw material and
manmade stuff too -- some tools are satellites communicating, or drones that intelligently orbit -- and we
place things at any distance to change the view, leaving debris fields as old outputs and raw asteroids as
outside info.

Grounded:
  * #38 (attention_lenses) -- orthogonal observer lenses, each a cosθ·vᵈ chain; 1 lens 48% of the variance,
    3 orthogonal lenses 100%; attention is finite. FOLDING_EYE_TYPES -- each cut makes a different cone
    (narrow=acuity, wide=sensitivity); the cone recurs at every scale. #28 -- each observer sees a finite band
    at a STANDOFF DISTANCE.
  * FOLDING_TWO_CONES / OBSERVERS_AS_D -- a *different-kind* observer buys 0.14 independence (5× a model swap),
    BUT independence is not sufficient: a weak independent reader DRAGS the ensemble down (0.927 -> 0.887).
  * #48 -- a drone is an antenna that flies itself to a useful orbit; #52/#53 -- the workspace / orbital sky.

MEASURED:
  (A) Each lens is a cone at its own focal DISTANCE with its border OUT of the light cone: read-quality peaks
      at the focal distance and dies if the lens is too close (border clips the view) or off-focus.
  (B) Stacking: adding a complementary+accurate lens composes more of the view; adding a REDUNDANT lens adds
      ~0; adding a WEAK lens DRAGS accuracy down -- more lenses is not better (the committee caution).
  (C) Taxonomy (raw asteroid / debris / satellite / drone) and DISTANCE as a view-control: effect falls with
      distance (place close to dominate, far for background); a drone SELF-PLACES at the useful distance while
      a raw asteroid just drifts.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(4)

# ===========================================================================
# (A) lens placement: focal distance + border out of the light cone
# ===========================================================================
d=np.linspace(0.15,3.0,300)
lenses=[dict(name="edge lens",   d0=0.9, sig=0.28, border=0.45, col="#238b45"),
        dict(name="colour lens", d0=1.6, sig=0.32, border=0.45, col="#e0a021"),
        dict(name="motion lens", d0=2.3, sig=0.34, border=0.45, col="#2b6cb0")]
def quality(L):
    focus=np.exp(-((d-L["d0"])**2)/(2*L["sig"]**2))     # sharp only at its focal distance
    borderok=(d>L["border"]).astype(float)               # too close -> rim clips the field of view
    return focus*borderok

# ===========================================================================
# (B) stacking: complementary+accurate helps; redundant ~0; weak DRAGS down
# ===========================================================================
# scene variance spread over D orthogonal axes; a lens on axis j with accuracy a captures a*var_j
D=5
var=np.array([0.34,0.26,0.20,0.12,0.08])                 # variance per orthogonal scene-axis
# start with 1 accurate orthogonal lens on axis 0
def captured(axes, accs):
    # captured view-fraction = sum over covered axes of acc*var (acc caps at 1); double-cover doesn't add
    cov={}
    for ax,ac in zip(axes,accs): cov[ax]=max(cov.get(ax,0),ac)
    return sum(min(cov[ax],1.0)*var[ax] for ax in cov)
# ensemble READ-ACCURACY (a weak member drags the mean, TWO_CONES): accuracy = variance-weighted mean acc,
# but a low-accuracy member pulls it toward its value (naive averaging of votes)
def read_accuracy(axes, accs):
    if not axes: return 0.0
    w=np.array([var[a] for a in axes]); a=np.array(accs)
    return float(np.sum(w*a)/np.sum(w))
steps=["1 accurate\nlens","+complementary\n(orthogonal, accurate)","+redundant\n(same axis)","+weak\n(new axis, noisy)"]
axes=[0]; accs=[0.92]
cap=[captured(axes,accs)]; acc=[read_accuracy(axes,accs)]
axes=axes+[1]; accs=accs+[0.90]; cap.append(captured(axes,accs)); acc.append(read_accuracy(axes,accs))   # complementary
axes=axes+[0]; accs=accs+[0.90]; cap.append(captured(axes,accs)); acc.append(read_accuracy(axes,accs))   # redundant (axis 0 again)
axes=axes+[2]; accs=accs+[0.45]; cap.append(captured(axes,accs)); acc.append(read_accuracy(axes,accs))   # weak new axis
cap=np.array(cap); acc=np.array(acc)

# ===========================================================================
# (C) taxonomy + distance-as-control + drone self-places
# ===========================================================================
# origin (0 raw .. 1 built) x role (0 info .. 1 tool)
taxo=[("raw asteroid\n(outside info)",0.13,0.13,"#8a6d3b"),
      ("debris field\n(old outputs)",0.13,0.87,"#888"),
      ("satellite\n(comm tool)",0.87,0.13,"#2b6cb0"),
      ("drone\n(intelligent tool)",0.87,0.87,"#238b45")]
dist=np.linspace(0.3,4,100); effect=1.0/(1.0+dist**1.6)    # effect on the view falls with distance
# drone self-places at the useful distance d_use; asteroid drifts randomly
d_use=1.0
def drone_steps():
    x=3.5
    for k in range(40):
        x+= -0.35*np.sign(x-d_use)*abs(x-d_use)*0.6        # gradient toward d_use
        if abs(x-d_use)<0.1: return k+1
    return 40
def asteroid_steps(seed):
    r=np.random.default_rng(seed); x=3.5
    for k in range(200):
        x+=r.normal(0,0.25)
        if abs(x-d_use)<0.1: return k+1
    return 200
drone_k=drone_steps(); ast_k=np.mean([asteroid_steps(s) for s in range(30)])

print("="*80)
print("  #54  THE LENS STACK + ORBITAL TAXONOMY -- perspectives at focal distances, bodies by origin×role")
print("="*80)
print("  (A) each lens reads clearly only at its own focal distance with its border out of the cone:")
for L in lenses: print(f"        {L['name']:12} focal distance {L['d0']:.1f}, border-clear beyond {L['border']:.2f}")
print("  (B) stacking lenses -- captured view AND read-accuracy:")
for s,c,a in zip(steps,cap,acc): print(f"        {s.replace(chr(10),' '):34} captured {c:.2f}  accuracy {a:.2f}")
print(f"      -> complementary+accurate lifts BOTH; redundant adds ~0 to captured; the WEAK lens DRAGS")
print(f"         accuracy {acc[1]:.2f} -> {acc[3]:.2f} (more lenses is NOT better -- FOLDING_TWO_CONES).")
print("  (C) taxonomy raw-asteroid / debris / satellite / drone; distance sets the view-effect")
print(f"      (close dominates, far fades); a DRONE self-places at the useful distance in {drone_k} steps")
print(f"      while a raw asteroid drifts ({ast_k:.0f} steps).")

# ===========================================================================
# PLOT
# ===========================================================================
fig=plt.figure(figsize=(15.4,4.9)); gs=fig.add_gridspec(1,3,wspace=0.30)

axA=fig.add_subplot(gs[0,0])
for L in lenses:
    axA.plot(d,quality(L),color=L["col"],lw=2,label=L["name"])
    axA.axvline(L["d0"],color=L["col"],ls=":",lw=0.8,alpha=0.6)
axA.axvspan(0.15,0.45,color="#c0392b",alpha=0.08); axA.text(0.30,0.5,"border\nin view",fontsize=7,color="#c0392b",ha="center")
axA.set_xlabel("distance along the optical axis"); axA.set_ylabel("read-quality of that lens")
axA.legend(fontsize=7.6,framealpha=0.9); axA.set_ylim(0,1.08)
axA.set_title("(A) Lenses line up like a telescope: each at its\nfocal distance, border out of the light cone",fontsize=9.8)

axB=fig.add_subplot(gs[0,1])
x=np.arange(4); w=0.38
axB.bar(x-w/2,cap,w,color="#238b45",label="captured view")
axB.bar(x+w/2,acc,w,color="#c0392b",label="read-accuracy")
axB.axhline(acc[1],color="#c0392b",ls=":",lw=1,alpha=0.6)
axB.set_xticks(x); axB.set_xticklabels(steps,fontsize=7.2); axB.set_ylim(0,1.05)
axB.legend(fontsize=7.8,framealpha=0.9,loc="upper left")
axB.annotate("weak lens\nDRAGS it down",xy=(3+w/2,acc[3]),xytext=(2.1,0.30),fontsize=7.4,color="#c0392b",
             arrowprops=dict(arrowstyle="->",color="#c0392b"))
axB.set_title("(B) Stacking: complementary+accurate helps; a\nredundant adds ~0; a WEAK lens drags it down",fontsize=9.8)

axC=fig.add_subplot(gs[0,2])
for nm,x0,y0,c in taxo:
    axC.scatter([x0],[y0],s=140,color=c,edgecolor="white",zorder=4)
    axC.annotate(nm,(x0,y0),fontsize=6.8,ha="center",va="center",xytext=(0,-22 if y0<0.5 else 20),textcoords="offset points")
axC.axhline(0.5,color="#ddd",lw=1); axC.axvline(0.5,color="#ddd",lw=1)
axC.set_xlim(0,1); axC.set_ylim(0,1)
axC.set_xticks([0.13,0.87]); axC.set_xticklabels(["raw","built"],fontsize=8)
axC.set_yticks([0.13,0.87]); axC.set_yticklabels(["info","tool"],fontsize=8)
axins=axC.inset_axes([0.37,0.37,0.26,0.26])
axins.plot(dist,effect,color="#8a2be2",lw=1.6); axins.set_title("effect vs distance",fontsize=6.4)
axins.tick_params(labelsize=5.5); axins.set_xlabel("distance",fontsize=5.5); axins.set_ylabel("effect",fontsize=5.5)
axC.set_title(f"(C) Sky taxonomy + distance-as-control; a drone\nself-places ({drone_k} steps) vs asteroid drifts ({ast_k:.0f})",fontsize=9.6)

fig.suptitle("#54 — the telescope lenses are observer perspectives at focal distances (borders out of the cone); stacking helps only if each lens is complementary AND accurate; the sky sorts into raw asteroids / debris / satellites / drones, placed by distance",fontsize=9.0)
fig.savefig("lens_stack.png",dpi=130,bbox_inches="tight")
print("\n  wrote lens_stack.png")
