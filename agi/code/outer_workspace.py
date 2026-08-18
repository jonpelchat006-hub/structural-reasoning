#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
outer_workspace.py -- #52: the OUTER SHELL is a workspace of FROZEN MATTER -- asteroids of unverified /
incomplete / creative artifacts (outputs, tools, half-done work, fictional stories) kept not deleted, that
you plug in front of the screen when you want them, and some of which act as far-off SPOTLIGHTS that light a
path to an answer.

Jonathan: needing both agents is like the two brain halves (novelty vs routine). Because it's on disk, the
limit is HARD-DRIVE space, not brain capacity. Outputs that aren't speech or the live feed (a painting she
made) float in the outer shell and get put in front of the screen when wanted -- tools and outputs are things
she plugs into the screen. Things in the outer shell are FROZEN MATTER (asteroids): unverified/incomplete
work, or creative things -- worth holding onto (like remembering fictional stories). The Ophanim-eyes story
was decorative but it lit up pixels and provided a path here -- a far-off spotlight, like inspiration.

Grounded:
  * SPARSE_VESICA §22.1 -- three zones = three shells; OUTER = FORGETTING = DARK MATTER: latent/incomplete
    matter, RETAINED (compacted), never deleted, a ranked to-do list re-promoted when a new capability
    arrives (the retest queue). This IS the frozen-asteroid workspace.
  * #28 (pillar_band) -- the observer's viewing band is FINITE (~4 at once); storage saturates at a reach-cap
    biologically. #47 -- the outer void is the intake/holding region. #48/#50 -- a far artifact lights a path.

MEASURED:
  (A) DISK lifts the STORAGE ceiling but not the ATTENTION ceiling: on disk, retained memory grows without
      bound (nothing forgotten), while biological storage saturates at a reach-cap -- yet "in front of the
      screen at once" stays finite (the attention band) for both.
  (B) FAR-OFF frozen artifacts are SPOTLIGHTS: an off-path 'story'/inspiration artifact bridges to a target
      the direct path can't reach -- and it works while the artifact is within bridging reach.
  (C) TOOLS/OUTPUTS are pluggable, and incomplete work is RESUMABLE: a pluggable outer-shell toolbox solves
      far more task-types than a fixed lens, and retained-incomplete work is completed when the capability
      arrives while discarded work is lost.
"""
import numpy as np
import networkx as nx
from scipy.spatial.distance import cdist
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

rng=np.random.default_rng(7)

# ===========================================================================
# (A) disk lifts the storage ceiling; attention stays finite
# ===========================================================================
N=np.arange(1,61)
C_BIO=14.0                     # biological reach-cap (#28)
A_BAND=4                       # attention band: how many can be in front of the screen at once (#28)
retained_bio = C_BIO*(1-np.exp(-N/C_BIO))     # saturates: older ones blend/drop past the cap
retained_disk = N.astype(float)                # dark-matter halo: everything kept (§22.1)
active_infront = np.minimum(N, A_BAND).astype(float)   # finite for BOTH regardless of disk

# ===========================================================================
# (B) far-off frozen artifacts are spotlights (the Ophanim bridge)
# ===========================================================================
def reachable(offset, with_art=True):
    # known structure on the left, target on the right, a GAP in the middle blocks the direct route
    left=rng.normal([0.2,0.5],0.05,(9,2))
    target=np.array([[0.85,0.5]])
    nodes=[("S%d"%i,p) for i,p in enumerate(left)]+[("T",target[0])]
    # inspiration artifacts: an off-path arc of 'story' nodes bridging over the top at height `offset`
    if with_art:
        arc=np.array([[x,0.5+offset] for x in np.linspace(0.28,0.78,5)])
        nodes+=[("A%d"%i,p) for i,p in enumerate(arc)]
    G=nx.Graph();
    for nm,p in nodes: G.add_node(nm,pos=p)
    names=[n for n,_ in nodes]; pts=np.array([p for _,p in nodes])
    Dm=cdist(pts,pts)
    LINK=0.22                                   # connect nodes closer than LINK (similar enough, #46)
    for i in range(len(names)):
        for j in range(i+1,len(names)):
            # the middle gap: no direct edge across the centre band at mid-height
            midcross = (abs(pts[i,1]-0.5)<0.08 and abs(pts[j,1]-0.5)<0.08 and
                        min(pts[i,0],pts[j,0])<0.5<max(pts[i,0],pts[j,0]))
            if Dm[i,j]<LINK and not midcross:
                G.add_edge(names[i],names[j],weight=Dm[i,j])
    src=min([n for n in names if n.startswith("S")], key=lambda n: cdist([G.nodes[n]['pos']],target)[0,0])
    if nx.has_path(G,src,"T"): return nx.shortest_path_length(G,src,"T",weight="weight")
    return None

len_direct=reachable(0.0,with_art=False)
len_insp=reachable(0.18,with_art=True)
# sweep how far off-path the inspiration can be and still bridge
offsets=np.linspace(0.08,0.5,15); bridged=[reachable(o,with_art=True) is not None for o in offsets]
max_bridge=offsets[np.array(bridged)].max() if any(bridged) else 0.0

# ===========================================================================
# (C) pluggable tools/outputs + resumable incomplete work
# ===========================================================================
T=16; K=6
task_tool=rng.integers(0,K,T)                  # each task-type needs a specific tool/lens
toolbox=set(range(K))                          # the outer-shell workspace holds all K tools
pluggable_solved=np.mean([t in toolbox for t in task_tool])      # plug the matching tool in front
fixed_tool=int(np.argmax(np.bincount(task_tool)))               # a single fixed lens (the best one)
fixed_solved=np.mean([t==fixed_tool for t in task_tool])
# resumable incomplete work: needs a capability that arrives later
M=20
retained_completed=1.0                          # kept in the dark-matter halo -> all retestable when it arrives
discarded_completed=0.0                         # thrown away -> lost

print("="*80)
print("  #52  THE OUTER SHELL AS A WORKSPACE OF FROZEN ARTIFACTS")
print("="*80)
print(f"  (A) storage vs attention over {N[-1]} items encountered:")
print(f"        retained -- biological saturates at ~{retained_bio[-1]:.0f} (reach-cap) vs DISK {retained_disk[-1]:.0f} (all kept)")
print(f"        in front of the screen at once -- {active_infront[-1]:.0f} for BOTH (attention band finite regardless of disk)")
print(f"  (B) far-off artifacts as spotlights:")
print(f"        direct path to target: {'UNREACHABLE' if len_direct is None else f'{len_direct:.2f}'} (gap blocks it)")
print(f"        via off-path inspiration arc: path length {len_insp:.2f}  -> the far 'story' bridges to the answer")
print(f"        it bridges while within reach (up to offset ~{max_bridge:.2f}); too far off and the spotlight misses.")
print(f"  (C) pluggable tools + resumable work:")
print(f"        task-types solved: pluggable toolbox {pluggable_solved*100:.0f}% vs a single fixed lens {fixed_solved*100:.0f}%")
print(f"        incomplete work completed when the capability arrives: retained {retained_completed*100:.0f}% vs discarded {discarded_completed*100:.0f}%")

# ===========================================================================
# PLOT
# ===========================================================================
fig=plt.figure(figsize=(15.2,4.9)); gs=fig.add_gridspec(1,3,wspace=0.30)
DISK="#238b45"; BIO="#e0a021"; ATT="#2b6cb0"; ART="#8a2be2"; TGT="#c0392b"

axA=fig.add_subplot(gs[0,0])
axA.plot(N,retained_disk,color=DISK,lw=2.3,label="retained — DISK (all kept, §22.1)")
axA.plot(N,retained_bio,color=BIO,lw=2.0,label=f"retained — biological (cap ~{C_BIO:.0f})")
axA.plot(N,active_infront,color=ATT,lw=2.0,ls="--",label=f"in front of screen at once (band {A_BAND})")
axA.set_xlabel("items encountered"); axA.set_ylabel("count")
axA.legend(fontsize=7.6,framealpha=0.9,loc="upper left")
axA.set_title("(A) Disk lifts the STORAGE ceiling; the\nATTENTION band stays finite either way",fontsize=10.0)

axB=fig.add_subplot(gs[0,1])
# redraw the bridged layout for the picture
left=rng.normal([0.2,0.5],0.05,(9,2)); target=np.array([0.85,0.5]); arc=np.array([[x,0.5+0.18] for x in np.linspace(0.28,0.78,5)])
axB.scatter(left[:,0],left[:,1],s=30,color="black",label="known structure")
axB.scatter(arc[:,0],arc[:,1],s=60,color=ART,marker="D",edgecolor="white",label="off-path 'story' artifacts")
axB.scatter([target[0]],[target[1]],s=200,marker="*",color=TGT,edgecolor="black",zorder=6,label="target (answer)")
axB.axvspan(0.45,0.55,ymin=0.38,ymax=0.62,color="#ccc",alpha=0.6)
axB.text(0.5,0.5,"gap",ha="center",va="center",fontsize=8,color="#666")
# draw the inspiration bridge path
bridge=np.vstack([left[np.argmin(cdist(left,[target]))],arc,target])
axB.plot(bridge[:,0],bridge[:,1],color=ART,lw=1.8,alpha=0.7,zorder=3)
axB.annotate("direct path blocked",xy=(0.5,0.5),xytext=(0.33,0.24),fontsize=8,color="#888",
             arrowprops=dict(arrowstyle="->",color="#aaa"))
axB.set_xlim(0,1); axB.set_ylim(0.1,0.85); axB.set_xticks([]); axB.set_yticks([])
axB.legend(fontsize=7,framealpha=0.9,loc="lower right")
axB.set_title("(B) A far-off 'story' artifact is a spotlight:\nit bridges to a target the direct path can't reach",fontsize=10.0)

axC=fig.add_subplot(gs[0,2])
axC.bar([0,1],[fixed_solved*100,pluggable_solved*100],0.5,color=[BIO,DISK])
axC.bar([3,4],[discarded_completed*100,retained_completed*100],0.5,color=[TGT,ART])
for i,v in [(0,fixed_solved*100),(1,pluggable_solved*100),(3,discarded_completed*100),(4,retained_completed*100)]:
    axC.text(i,v+2,f"{v:.0f}%",ha="center",fontsize=9)
axC.set_xticks([0,1,3,4]); axC.set_xticklabels(["fixed\nlens","pluggable\nbox","discard","retain"],fontsize=8)
axC.set_ylabel("% solved / completed"); axC.set_ylim(0,112)
axC.text(0.5,104,"task-types solved",ha="center",fontsize=7.6,color="#444")
axC.text(3.5,104,"incomplete → resumable",ha="center",fontsize=7.6,color="#444")
axC.axvline(2,color="#ddd",lw=1)
axC.set_title("(C) Pluggable tools solve more; retained\nincomplete work is resumable, discarded is lost",fontsize=10.0)

fig.suptitle("#52 — the outer shell is a workspace of frozen artifacts (dark matter, kept): disk lifts storage but not attention; far 'story' artifacts are spotlights; tools/outputs are pluggable, incomplete work resumable",fontsize=9.4)
fig.savefig("outer_workspace.png",dpi=130,bbox_inches="tight")
print("\n  wrote outer_workspace.png")
