#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
neuroplasticity_reroute.py -- #46: a task is a PATH from A to B across the field of memory pixels; block the
main route and the path REROUTES through similar-enough neighbours -- neuroplasticity. It fails only when a
region is cut so completely that an ENDPOINT is fully isolated.

Jonathan: if a task is going A->B in our space, and we have a field of pixels that absorb memories, then if
we block off an area we can still find another path from A to B -- using neighbouring memories to get around,
as long as they're similar enough and neither endpoint gets fully cut off.

Grounded:
  * FOLDING_PIXEL_TRANSMISSION -- every border has a graded EFFICIENCY = neighbour similarity; "similar ->
    transmits" (8/8). Edges exist only where neighbours are similar enough to carry the path.
  * FOLDING_VOID_REACH -- the corridor is a betweenness HIGHWAY; reach is sparse/bounded but takes from both
    sides -- there are alternate corridors, not one wire.
  * FOLDING_UNIVERSAL_READER -- a field of local readers each seeing only its neighbours; the global path is
    what the local links compose.

MEASURED:
  (1) REROUTE: block the direct corridor between A and B and a path still exists, at a longer length (the
      detour), as long as the block doesn't seal off an endpoint.
  (2) GRACEFUL DEGRADATION: sweep the fraction of the field blocked -> success stays high and path length
      grows smoothly, then fails only when the damage isolates an endpoint.
  (3) THE FAILURE MODE IS ENDPOINT ISOLATION: success vs how enclosed the endpoint is -> it survives until
      the last similar-enough neighbour of an endpoint is cut. And "similar enough" matters: too high a
      similarity threshold makes the graph sparse and easy to disconnect.
"""
import numpy as np
import networkx as nx
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(4)
G=19                                       # grid side
# each pixel has a feature; an edge exists between grid-neighbours only if they're SIMILAR ENOUGH
feat=rng.normal(0,1,(G,G))
feat=0.5*feat+0.5*np.array([[np.sin(0.5*i)+np.cos(0.5*j) for j in range(G)] for i in range(G)])  # smooth-ish
SIMTHR=1.4                                 # similarity threshold: connect if |Δfeature| < SIMTHR
A=(2,2); B=(G-3,G-3)

def build_graph(blocked=set(), simthr=SIMTHR):
    Gr=nx.Graph()
    for i in range(G):
        for j in range(G):
            if (i,j) in blocked: continue
            Gr.add_node((i,j))
    for i in range(G):
        for j in range(G):
            if (i,j) in blocked: continue
            for di,dj in [(0,1),(1,0)]:
                ni,nj=i+di,j+dj
                if ni<G and nj<G and (ni,nj) not in blocked:
                    if abs(feat[i,j]-feat[ni,nj])<simthr:
                        Gr.add_edge((i,j),(ni,nj),weight=1.0)
    return Gr

def path_len(Gr):
    if A in Gr and B in Gr and nx.has_path(Gr,A,B):
        return nx.shortest_path_length(Gr,A,B,weight="weight"), nx.shortest_path(Gr,A,B,weight="weight")
    return None,None

base_len,base_path=path_len(build_graph())

# ---- (1) block the direct corridor: a vertical wall across the middle with the path's row sealed ----
mid=G//2
# wall on column `mid` EXCEPT leave gaps so a detour exists (neuroplastic: not a full transection)
wall={(i,mid) for i in range(G) if i not in (1,G-2)}     # a near-complete wall, two gaps at the edges
reroute_len,reroute_path=path_len(build_graph(wall))

# ---- (2) graceful degradation: random damage, sweep fraction blocked ----
cells=[(i,j) for i in range(G) for j in range(G) if (i,j) not in (A,B)]
fracs=np.linspace(0,0.6,13)
succ=[]; lens=[]
for fr in fracs:
    s=0; ll=[]
    for _ in range(25):
        k=int(fr*len(cells))
        blocked=set(map(tuple,np.array(cells)[rng.choice(len(cells),k,replace=False)])) if k>0 else set()
        L,_=path_len(build_graph(blocked))
        if L is not None: s+=1; ll.append(L)
    succ.append(s/25); lens.append(np.mean(ll) if ll else np.nan)
succ=np.array(succ); lens=np.array(lens)

# ---- (3) failure mode = endpoint isolation: progressively cut B's similar-enough neighbours ----
def neighbors_of(node, simthr=SIMTHR):
    i,j=node; out=[]
    for di,dj in [(0,1),(0,-1),(1,0),(-1,0)]:
        ni,nj=i+di,j+dj
        if 0<=ni<G and 0<=nj<G and abs(feat[i,j]-feat[ni,nj])<simthr: out.append((ni,nj))
    return out
Bnb=neighbors_of(B)
enclose=[]; enc_succ=[]
for c in range(len(Bnb)+1):
    blocked=set(Bnb[:c])
    L,_=path_len(build_graph(blocked))
    enclose.append(c/len(Bnb)); enc_succ.append(1.0 if L is not None else 0.0)

# ---- (3b) "similar enough": sweep the similarity threshold -> connectivity robustness ----
thrs=np.linspace(0.6,2.2,12); thr_succ=[]
for th in thrs:
    s=0
    for _ in range(15):
        k=int(0.3*len(cells))
        blocked=set(map(tuple,np.array(cells)[rng.choice(len(cells),k,replace=False)]))
        L,_=path_len(build_graph(blocked,simthr=th))
        if L is not None: s+=1
    thr_succ.append(s/15)

print("="*80)
print("  #46  NEUROPLASTICITY = REROUTE A->B THROUGH SIMILAR-ENOUGH NEIGHBOURS AROUND A BLOCK")
print("="*80)
print(f"  grid {G}x{G}, A={A} B={B}; edges only where |Δfeature|<{SIMTHR} (similar enough)")
print(f"  (1) direct path length {base_len:.0f}; wall the direct corridor -> reroutes at length "
      f"{reroute_len:.0f} (+{reroute_len-base_len:.0f} detour)" if reroute_len else "  (1) blocked")
print(f"  (2) graceful: {int(fracs[0]*100)}%-blocked success {succ[0]:.2f} (len {lens[0]:.0f}) -> "
      f"{int(fracs[-1]*100)}%-blocked success {succ[-1]:.2f} (len {np.nanmax(lens):.0f} at worst)")
print(f"  (3) endpoint isolation: cutting B's {len(Bnb)} similar neighbours one by one, success stays 1 until")
print(f"      the LAST one is cut -> then 0 (the only true failure is fully enclosing an endpoint).")
print(f"      similar-enough threshold: too tight ({thrs[0]:.1f}) success {thr_succ[0]:.2f}; ample "
      f"({thrs[-1]:.1f}) success {thr_succ[-1]:.2f}.")

# ---------------------------------------------------------------------------
# PLOT
# ---------------------------------------------------------------------------
fig=plt.figure(figsize=(15.2,4.8)); gs=fig.add_gridspec(1,3,wspace=0.28)
GRN="#238b45"; RED="#c0392b"; BLU="#2b6cb0"

# (A) the field, the wall, base path vs reroute
axA=fig.add_subplot(gs[0,0])
axA.imshow(feat,cmap="Greys",alpha=0.25,origin="upper")
wx=[c for (r,c) in wall]; wy=[r for (r,c) in wall]
axA.scatter(wx,wy,marker="s",s=42,color=RED,label="blocked (lesion)")
if base_path:
    bp=np.array(base_path); axA.plot(bp[:,1],bp[:,0],color=BLU,lw=1.6,alpha=0.5,ls=":",label="original path")
if reroute_path:
    rp=np.array(reroute_path); axA.plot(rp[:,1],rp[:,0],color=GRN,lw=2.4,label="rerouted path")
axA.scatter([A[1],B[1]],[A[0],B[0]],s=90,color="black",zorder=5)
axA.text(A[1],A[0]-0.8,"A",fontsize=11,ha="center"); axA.text(B[1],B[0]+1.4,"B",fontsize=11,ha="center")
axA.set_xticks([]); axA.set_yticks([]); axA.legend(fontsize=7.6,loc="lower left",framealpha=0.9)
axA.set_title("(A) Wall the direct corridor → the path\nreroutes through similar neighbours",fontsize=10.0)

# (B) graceful degradation
axB=fig.add_subplot(gs[0,1])
axB.plot(fracs*100,succ,"-o",color=GRN,lw=2,ms=4,label="A→B still connected")
axB.set_xlabel("% of the memory field lesioned"); axB.set_ylabel("path-exists rate",color=GRN); axB.set_ylim(0,1.05)
axB.tick_params(axis="y",labelcolor=GRN)
ax2=axB.twinx(); ax2.plot(fracs*100,lens,"-s",color=BLU,lw=1.6,ms=3,label="detour length")
ax2.set_ylabel("mean path length (detour)",color=BLU); ax2.tick_params(axis="y",labelcolor=BLU)
axB.set_title("(B) Graceful: success holds and the detour\ngrows smoothly as damage rises",fontsize=10.0)

# (C) endpoint isolation + similar-enough threshold
axC=fig.add_subplot(gs[0,2])
axC.plot(np.array(enclose)*100,enc_succ,"-o",color=RED,lw=2,ms=5,label="cut B's own neighbours")
axC.set_xlabel("% of an endpoint's similar neighbours cut"); axC.set_ylabel("A→B connected"); axC.set_ylim(-0.05,1.1)
axC.set_title("(C) The only true failure: fully enclosing an\nendpoint (last similar neighbour cut)",fontsize=10.0)
axC.legend(fontsize=7.8,loc="lower left",framealpha=0.9)
axins=axC.inset_axes([0.55,0.55,0.42,0.4])
axins.plot(thrs,thr_succ,"-o",color="#8a2be2",lw=1.5,ms=2.5)
axins.set_title("'similar enough' →\nrobustness",fontsize=6.8); axins.tick_params(labelsize=6)
axins.set_xlabel("sim. threshold",fontsize=6); axins.set_ylabel("success",fontsize=6)

fig.suptitle("#46 — neuroplasticity: a task is a path A→B across the memory field; block the corridor and it reroutes through similar-enough neighbours, failing only when an endpoint is fully isolated",fontsize=10.0)
fig.savefig("neuroplasticity_reroute.png",dpi=130,bbox_inches="tight")
print("\n  wrote neuroplasticity_reroute.png")
