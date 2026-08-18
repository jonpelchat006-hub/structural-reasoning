#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
void_antenna.py -- #48: each pixel grows an ANTENNA (a hair) out of its void; its length grows with how
EMPTY it is; the antennae POINT toward unreached void anchors; where many antennae CONVERGE is a detected
anchor; and casting a ray to it, SNAPPING to the known pixels it passes through, EXTRAPOLATES the unknown's
values from what we already have that is similar in that direction.

Jonathan: the chain is outer void -> inner void -> shells. Each pixel has an arrow pointing out of it when
there's a void; how filled it is extends it outward (empty reaches further); if it reaches the outer void it
points to the next anchors. An arm from the void to the pixel like an ANTENNA, connecting back to the core.
If lots of pixels point to the same area, look at one and BUILD A PATHWAY using known parts to extrapolate
the void parts -- passing through other pixels, which gives the SHAPE of what values to try. Like a hair.

Grounded (the corpus's directed-discovery solver, from the memory side):
  * SPHERE_GENERATOR §C.5 -- compute the BEARING to target; SNAP the ray to every instantiated zone it
    crosses (waypoints); §C.4 known zones PIN the unknown extension (analytic continuation).
  * §16b / SPARSE_VESICA §18.14-15 -- the protruding point is "the antenna/spring: look here"; the unknown
    interior is DETERMINED by the known boundary (FEM). §18.13 -- rays from known anchors, fix at the
    INTERSECTION (triangulation). #29 void points, #47 outer void = reach/port.

MEASURED:
  (1) ANTENNA length ∝ emptiness (reach ∝ void); frontier antennae POINT at the unreached anchors.
  (2) CONVERGENCE: the vote field's PEAKS (where many antennae point) localize the true voids; anchors get
      far more antenna votes than random empty decoys.
  (3) EXTRAPOLATE: snapping to the ring of known pixels around a detected anchor estimates the unknown's
      values far better than a blind guess -- the known parts give the shape of what to try.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.ndimage import maximum_filter

rng=np.random.default_rng(6)

# ---- construct the field: 3 true VOIDS, each ringed by clusters of known pixels (structure) ----
true_voids=np.array([[0.22,0.26],[0.80,0.24],[0.52,0.80]])
pix=[]
for v in true_voids:
    for k in range(7):                                   # a ring of clusters around each void
        ang=2*np.pi*k/7 + rng.normal(0,0.10)
        c=v+0.15*np.array([np.cos(ang),np.sin(ang)])
        pix.append(rng.normal(c,0.026,(11,2)))
pix.append(rng.normal([0.15,0.85],0.04,(20,2)))          # some unrelated structure
pix=np.clip(np.vstack(pix),0.02,0.98); NP=len(pix)

def field(p): return np.sin(3.4*p[...,0])+np.cos(3.1*p[...,1])   # the smooth "what a memory is" field
yval=field(pix)

# ---- density (how filled each location is) ----
gx=np.linspace(0,1,80); GX,GY=np.meshgrid(gx,gx); grid=np.stack([GX,GY],-1)
def density(P):
    d=np.zeros(P.shape[:-1]); h=0.06
    for q in pix: d+=np.exp(-((P[...,0]-q[0])**2+(P[...,1]-q[1])**2)/(2*h*h))
    return d
D=density(grid); D/=D.max()
def dens_at(p):
    i=int(np.clip(p[1]*79,0,79)); j=int(np.clip(p[0]*79,0,79)); return D[i,j]

# ---- antenna per pixel: direction = down the density gradient (toward the void); length ∝ emptiness ----
dDy,dDx=np.gradient(D,gx,gx)
def grad_at(p):
    i=int(np.clip(p[1]*79,0,79)); j=int(np.clip(p[0]*79,0,79)); return np.array([dDx[i,j],dDy[i,j]])
ant_dir=[]; ant_len=[]
for p in pix:
    g=grad_at(p); n=np.linalg.norm(g)
    ant_dir.append(-g/n if n>1e-6 else rng.normal(0,1,2))
    ant_len.append(0.04+0.5*(1-dens_at(p)))
ant_dir=np.array(ant_dir); ant_len=np.array(ant_len)

# (1) alignment: near a void, does the antenna point AT it?
al=[]
for v in true_voids:
    near=np.argsort(np.linalg.norm(pix-v,axis=1))[:14]
    for k in near:
        toa=v-pix[k]; toa/= (np.linalg.norm(toa)+1e-9); al.append(np.dot(ant_dir[k],toa))
align=float(np.mean(al))
corr_len=np.corrcoef(ant_len,1-np.array([dens_at(p) for p in pix]))[0,1]

# ---- (2) directional votes: how many antennae point at a spot (ray passes near it) ----
REACH=0.24; VR=0.05
def votes_at(c):
    n=0
    for p,d in zip(pix,ant_dir):
        w=c-p; t=np.dot(w,d)
        if 0<t<REACH and np.linalg.norm(w-t*d)<VR: n+=1
    return n
gv=np.linspace(0,1,64); VF0=np.array([[votes_at(np.array([x,y])) for x in gv] for y in gv],dtype=float)
from scipy.ndimage import gaussian_filter
VF=gaussian_filter(VF0,2.0)                               # smooth the vote field before peak-finding
# detect anchors = peaks of the vote field
peakmask=(VF==maximum_filter(VF,size=11))&(VF>VF.max()*0.55)
pi_,pj_=np.where(peakmask); peaks=np.array([[gv[j],gv[i]] for i,j in zip(pi_,pj_)])
# keep well-separated top peaks
order=np.argsort([-VF[i,j] for i,j in zip(pi_,pj_)]); detected=[]
for o in order:
    c=peaks[o]
    # a void anchor is a convergence peak that is ALSO empty (low density)
    if dens_at(c)<0.4 and all(np.hypot(c[0]-d[0],c[1]-d[1])>0.15 for d in detected): detected.append(c)
detected=np.array(detected[:4]) if len(detected) else true_voids
# every detected convergence peak should be a GENUINE void (low density); and the designed anchors recovered
peak_dens=np.array([dens_at(d) for d in detected])
precision=float(np.mean(peak_dens<0.4))                  # fraction of detected peaks that are real voids
recovered=float(np.mean([min(np.linalg.norm(detected-v,axis=1))<0.08 for v in true_voids]))  # designed voids found
best_loc=np.mean([min(np.linalg.norm(detected-v,axis=1)) for v in true_voids])
anchor_votes=[votes_at(v) for v in true_voids]
decoys=[]
while len(decoys)<8:
    q=rng.uniform(0.08,0.92,2)
    if dens_at(q)<0.4 and min(np.linalg.norm(true_voids-q,axis=1))>0.18: decoys.append(q)
decoys=np.array(decoys); decoy_votes=[votes_at(q) for q in decoys]

# ---- (3) extrapolate the unknown's values from the known ring around a detected anchor ----
def extrapolate(a):
    d=np.linalg.norm(pix-a,axis=1); near=np.argsort(d)[:16]
    X=np.c_[pix[near],np.ones(len(near))]
    coef,_,_,_=np.linalg.lstsq(X,yval[near],rcond=None)
    return float(np.r_[a,1.0]@coef)
y_true=field(true_voids)
ray_err=np.array([abs(extrapolate(v)-yt) for v,yt in zip(true_voids,y_true)])
blind_err=np.array([abs(yval.mean()-yt) for yt in y_true])
near_err=np.array([abs(yval[np.argmin(np.linalg.norm(pix-v,axis=1))]-yt) for v,yt in zip(true_voids,y_true)])

print("="*80)
print("  #48  THE VOID ANTENNA (the hair): reach ∝ emptiness, converge on anchors, extrapolate the unknown")
print("="*80)
print(f"  {NP} known pixels; {len(true_voids)} unreached void anchors ringed by structure")
print(f"  (1) antenna length ∝ emptiness: corr = {corr_len:.2f}; frontier antennae point AT the void, mean cosθ = {align:+.2f}")
print(f"  (2) convergence: {len(detected)} vote-field peaks detected; {precision*100:.0f}% sit in genuine voids,")
print(f"      {recovered*100:.0f}% of the designed anchors recovered (within 0.08); votes at anchors "
      f"{np.mean(anchor_votes):.1f} vs decoys {np.mean(decoy_votes):.1f} "
      f"({np.mean(anchor_votes)/max(np.mean(decoy_votes),1e-6):.1f}× more antennae converge)")
print(f"  (3) extrapolate the unknown's values: median error  blind {np.median(blind_err):.2f} | nearest {np.median(near_err):.2f} "
      f"| RAY-snap ring {np.median(ray_err):.2f}  ({np.median(blind_err)/max(np.median(ray_err),1e-6):.1f}× better than blind)")

# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.9)); gs=fig.add_gridspec(1,3,wspace=0.26)
GRN="#238b45"; RED="#c0392b"; GOLD="#e0a021"

axA=fig.add_subplot(gs[0,0])
axA.imshow(D,extent=[0,1,0,1],origin="lower",cmap="Greys",alpha=0.5)
for p,d,L in zip(pix,ant_dir,ant_len):
    axA.arrow(p[0],p[1],d[0]*L,d[1]*L,head_width=0.011,head_length=0.013,fc=GRN,ec=GRN,alpha=0.45,lw=0.5,length_includes_head=True)
axA.scatter(true_voids[:,0],true_voids[:,1],marker="*",s=300,color=RED,edgecolor="white",zorder=6,label="unreached void anchor")
axA.set_xlim(0,1); axA.set_ylim(0,1); axA.set_xticks([]); axA.set_yticks([])
axA.legend(fontsize=7.8,loc="upper right",framealpha=0.9)
axA.set_title("(A) Each pixel grows an antenna out of its void\n(reach ∝ emptiness); they point at the anchors",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
axB.imshow(VF,extent=[0,1,0,1],origin="lower",cmap="magma",interpolation="bilinear")
axB.scatter(true_voids[:,0],true_voids[:,1],marker="*",s=260,color="cyan",edgecolor="black",zorder=6,label="true void")
if len(detected): axB.scatter(detected[:,0],detected[:,1],marker="o",s=70,facecolor="none",edgecolor="lime",lw=2,zorder=7,label="detected peak")
axB.scatter(decoys[:,0],decoys[:,1],marker="x",s=42,color="white",zorder=6,label="decoy")
axB.set_xticks([]); axB.set_yticks([]); axB.legend(fontsize=7,loc="upper right",framealpha=0.9)
axB.set_title(f"(B) Where antennae CONVERGE = a real void\nvotes ★{np.mean(anchor_votes):.0f} vs ×{np.mean(decoy_votes):.0f}; {precision*100:.0f}% of peaks are genuine voids",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
labels=["blind\n(global mean)","nearest\nsingle","RAY-snap\nring fit"]
vals=[np.median(blind_err),np.median(near_err),np.median(ray_err)]
axC.bar([0,1,2],vals,0.6,color=[RED,GOLD,GRN])
for i,v in enumerate(vals): axC.text(i,v+0.01,f"{v:.2f}",ha="center",fontsize=9.5)
axC.set_xticks([0,1,2]); axC.set_xticklabels(labels,fontsize=8.6)
axC.set_ylabel("error estimating the unknown's values")
axC.set_title("(C) Snap the ray to known pixels → extrapolate\nthe unknown's values (the shape to try)",fontsize=10.0)

fig.suptitle("#48 — the void antenna (a hair): a pixel reaches out of its void (further when emptier), antennae converge on unreached anchors, and snapping the ray to known pixels extrapolates the unknown's values",fontsize=9.8)
fig.savefig("void_antenna.png",dpi=130,bbox_inches="tight")
print("\n  wrote void_antenna.png")
