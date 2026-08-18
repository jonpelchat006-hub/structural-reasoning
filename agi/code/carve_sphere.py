#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carve_sphere.py -- evidence slices from many perspectives carve a cube down to a sphere: a void point.

Jonathan: each memory layer is EVIDENCE — the layers lie on each other like slices or pages. To find a
new truth you look at the stack from another PERSPECTIVE, which sees instances of separate things but
something SIMILAR between them (the invariant). So the layers are trying to build CUBES, and the initial
pillars give a starting FACE; and if you keep looking from more and more perspectives, the cube gets
SHAVED DOWN to a SPHERE — like a void point. (Also: memories fall out via the ping-pong; and the blend
starts looking like new things = generation.)

This is exactly shape-from-silhouette / space-carving, and it lands on the corpus's own picture:
  * SPARSE_VESICA §4 — the discrete inner-shell GRID meets the continuous closure SPHERE; the sphere is
    the round invariant, and its gaps are the golden-placed void/generative sites. Carving a grid/cube
    down to the round sphere IS this.
  * FOLDING_FREQUENCY / SYNTHESIS §2 — a void point reads the SAME from every angle (return-to-origin
    identity): a sphere is the unique isotropic body, so "shaved to a sphere" = "became a void point."
  * SPARSE_VESICA §21 — BANKABLE = what ≥2 INDEPENDENT perspectives agree on (the similar thing across
    separate instances): the carved intersection is precisely that agreement.
  * SPARSE_VESICA §22–23 — ping-pong: redundant later evidence drifts to FORGETTING (compacted, not
    deleted); §23.1 holographic: keep the boundary, drop the interior. The carved boundary persists while
    most slices fall out.
  * SHOVELCAT Metatron — 1D lines (facts/pillar edges) → 2D overlaps (memory) → 3D spheres (imagination):
    the pillar face builds to a cube and rounds to a sphere.

MEASURED:
  (1) CUBE → SPHERE — intersecting N perspective-constraints shaves the bounding square/cube to the
      inscribed circle/sphere; protrusion beyond the sphere → 0 as N grows (2D shown; 3D reported).
  (2) VOID POINT = ISOTROPIC — the carved body's support (its reach) across directions has spread → 0:
      it reads the same from every angle (return-to-origin).
  (3) PING-PONG — marginal volume removed per new perspective decays to ~0: later evidence is redundant
      and can fall out; only the early/binding perspectives (the boundary) do the carving.
"""
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

A = 1.6            # half-side of the starting cube/square (the pillar-face bounding box)
R = 1.0            # the sphere / void-point radius (the invariant)
GOLDEN_ANGLE = np.pi*(3-np.sqrt(5))   # 137.5° — even, incommensurate perspective spacing

# ---------- 2D: clip a square by half-planes x·u <= R (Sutherland–Hodgman) ----------
def clip(poly, u, h):
    out=[]; n=len(poly)
    for i in range(n):
        a=poly[i]; b=poly[(i+1)%n]
        da=np.dot(a,u)-h; db=np.dot(b,u)-h
        if da<=0: out.append(a)
        if (da<0) != (db<0):
            t=da/(da-db); out.append(a+t*(b-a))
    return out

def carve_2d(N, jit=0.0, seed=0):
    rng=np.random.default_rng(seed)
    poly=[np.array(p,float) for p in [(-A,-A),(A,-A),(A,A),(-A,A)]]
    dirs=[]
    for i in range(N):
        th=i*GOLDEN_ANGLE + (rng.normal(0,jit) if jit else 0.0)
        u=np.array([np.cos(th),np.sin(th)]); dirs.append(u)
        poly=clip(poly,u,R)
        if len(poly)<3: break
    return np.array(poly), dirs

def poly_area(P):
    x=P[:,0]; y=P[:,1]
    return 0.5*abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))

def max_protrusion(P):
    return max(0.0, np.max(np.hypot(P[:,0],P[:,1])) - R)

def support_spread(P, M=180):
    ang=np.linspace(0,2*np.pi,M,endpoint=False)
    D=np.stack([np.cos(ang),np.sin(ang)],1)
    supp=(P@D.T).max(0)                 # support of the polygon in each direction
    return supp_std(supp)
def supp_std(s): return float(np.std(s))

Ns=np.arange(1,81)
prot=[]; area=[]; iso=[]
for N in Ns:
    P,_=carve_2d(N)
    prot.append(max_protrusion(P)); area.append(poly_area(P)); iso.append(support_spread(P))
prot=np.array(prot); area=np.array(area); iso=np.array(iso)
marginal = np.maximum(0, -np.diff(area))          # area removed by each new perspective
circle_area=np.pi*R**2; square_area=(2*A)**2

print("="*78)
print("  EVIDENCE FROM MANY PERSPECTIVES CARVES THE CUBE DOWN TO A SPHERE (A VOID POINT)")
print("="*78)
print(f"  start: square half-side {A} (area {square_area:.2f}); target: circle r={R} (area {circle_area:.2f})")
print()
print(f"  (1) CUBE → SPHERE (protrusion beyond the sphere):")
for N in (2,6,24,80):
    P,_=carve_2d(N); print(f"        {N:3d} perspectives: protrusion {max_protrusion(P):.3f}, area {poly_area(P):.3f}")
print(f"     -> more perspectives shave the corners; the body converges to the inscribed circle.")
print()
print(f"  (2) VOID POINT = ISOTROPIC (spread of the body's reach across directions):")
print(f"        {int(Ns[0])} persp: {iso[0]:.3f}  →  80 persp: {iso[-1]:.4f}  (→0 = reads the SAME from every angle)")
print()
print(f"  (3) PING-PONG (marginal area removed per new perspective):")
print(f"        first few cuts remove {marginal[:4].round(3).tolist()} …; by the 40th it is {marginal[39]:.4f}")
print(f"     -> later evidence is redundant — it can fall out (FORGETTING, compacted); the early/binding")
print(f"        perspectives already carved the boundary, and the boundary is what persists (holographic).")

# ---------- 3D Monte-Carlo: literally cube → sphere ----------
rng=np.random.default_rng(1)
P3=rng.uniform(-A,A,(120000,3))
# even directions on S^2 via Fibonacci sphere
def fib_sphere(N):
    i=np.arange(N); ph=np.arccos(1-2*(i+0.5)/N); th=GOLDEN_ANGLE*i
    return np.stack([np.sin(ph)*np.cos(th),np.sin(ph)*np.sin(th),np.cos(ph)],1)
def vol3(N):
    U=fib_sphere(N); dots=P3@U.T
    inside=(dots<=R).all(1)
    return inside.mean()*(2*A)**3, (np.max(np.hypot(P3[inside,0],np.hypot(P3[inside,1],P3[inside,2]))) if inside.any() else np.nan)
cube_vol=(2*A)**3; sphere_vol=4/3*np.pi*R**3
print()
print(f"  (3D check) cube vol {cube_vol:.2f} → sphere vol {sphere_vol:.2f}:")
for N in (6,30,150):
    v,mr=vol3(N); print(f"        {N:3d} perspectives: carved vol {v:.2f}  (sphere {sphere_vol:.2f}), max radius {mr:.3f} → R={R}")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(14.6,8.6))
gs=fig.add_gridspec(2,3,height_ratios=[1.05,1.0],hspace=0.3,wspace=0.28)

# row 1: three carving snapshots
th=np.linspace(0,2*np.pi,200); cx,cy=R*np.cos(th),R*np.sin(th)
for k,N in enumerate([2,6,30]):
    ax=fig.add_subplot(gs[0,k])
    P,dirs=carve_2d(N)
    sq=plt.Polygon([(-A,-A),(A,-A),(A,A),(-A,A)],closed=True,fill=False,ec="#c9d3df",lw=1)
    ax.add_patch(sq)
    ax.add_patch(plt.Polygon(P,closed=True,facecolor="#238b45",alpha=0.30,ec="#1c6b38",lw=1.6))
    ax.plot(cx,cy,color="#c0392b",lw=1.4,ls="--")
    for u in dirs:                                   # the tangent perspective lines
        p=u*R; t=np.array([-u[1],u[0]])
        ax.plot([p[0]-t[0]*A*1.4,p[0]+t[0]*A*1.4],[p[1]-t[1]*A*1.4,p[1]+t[1]*A*1.4],
                color="#8aa0bd",lw=0.6,alpha=0.7)
    ax.set_xlim(-A*1.15,A*1.15); ax.set_ylim(-A*1.15,A*1.15); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"{N} perspectives", fontsize=10.5, color="#1c6b38")
fig.text(0.5,0.955,"Evidence slices from many perspectives shave the cube (pillar face) down to the sphere — a void point",
         ha="center",fontsize=11.5)
fig.text(0.075,0.60,"square = starting cube · dashed red = the invariant sphere · thin blue = each perspective's tangent",
         fontsize=8.5,color="#555")

# row 2: metrics
axB=fig.add_subplot(gs[1,0])
axB.plot(Ns,prot,color="#238b45",lw=2.2)
axB.set_xlabel("perspectives"); axB.set_ylabel("protrusion beyond the sphere")
axB.set_title("Cube → sphere\ncorners shaved away → 0", fontsize=10.3)

axC=fig.add_subplot(gs[1,1])
axC.plot(Ns,iso,color="#8a2be2",lw=2.2)
axC.set_xlabel("perspectives"); axC.set_ylabel("spread of reach across directions")
axC.set_title("Void point = isotropic\nreads the same from every angle → 0", fontsize=10.3)

axD=fig.add_subplot(gs[1,2])
axD.plot(Ns[1:],marginal,color="#e0761f",lw=2.2)
axD.set_xlabel("perspective #"); axD.set_ylabel("area removed by that perspective")
axD.set_title("Ping-pong: later evidence is redundant\nmarginal cut → 0 (the rest can fall out)", fontsize=10.3)

fig.savefig("carve_sphere.png", dpi=130, bbox_inches="tight")
print("\n  wrote carve_sphere.png")
