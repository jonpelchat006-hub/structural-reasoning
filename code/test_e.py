import os; os.chdir("/home/claude/strain")
import numpy as np, pickle
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())

def fiedler(coords,cutoff=8.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1))
    A=((D<cutoff)&(D>0)).astype(float); deg=A.sum(1); deg[deg==0]=1
    Dm=np.diag(1/np.sqrt(deg)); w,v=eigh(np.eye(len(coords))-Dm@A@Dm)
    return (v[:,1]>=0).astype(int)
def mixed(coords,dom,sigma=6.0,cut=10.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1)); n=len(dom); m=np.zeros(n)
    for i in range(n):
        nb=np.where((D[i]<cut)&(D[i]>0))[0]
        if len(nb)==0: continue
        wt=np.exp(-(D[i,nb]/sigma)**2); m[i]=wt[dom[nb]!=dom[i]].sum()/wt.sum()
    return m
def normal(coords,dom):
    cA=coords[dom==0].mean(0); cB=coords[dom==1].mean(0); v=cA-cB
    return v/ (np.linalg.norm(v)+1e-9)

print(f"{'pdb':6}{'angle(C1,C2)':>13}{'geometry':>13}{'corr(mix1,mix2)':>17}")
angs=[]; corrs=[]
for p in PROTEINS:
    d=R[p]; coords=d['coords']; dom=d['dom']; mix1=d['mix']
    n1=normal(coords,dom)
    big=0 if (dom==0).sum()>=(dom==1).sum() else 1
    ix=np.where(dom==big)[0]; sub=coords[ix]
    sdom=fiedler(sub); n2=normal(sub,sdom)
    ang=np.degrees(np.arccos(np.clip(abs(np.dot(n1,n2)),0,1)))
    angs.append(ang)
    # within larger domain: do the level-1-ambiguous (higher mix1) residues become the level-2 seam?
    mix2=mixed(sub,sdom); m1=mix1[ix]
    c=np.corrcoef(m1,mix2)[0,1] if m1.std()>0 and mix2.std()>0 else np.nan
    corrs.append(c)
    geo="cross ⟂-ish" if ang>55 else ("parallel-ish" if ang<35 else "oblique")
    print(f"{p:6}{ang:>12.1f}°{geo:>13}{c:>17.3f}")
angs=np.array(angs); corrs=np.array(corrs)
print(f"\nmean angle between successive cut planes = {angs.mean():.1f}°  (0=parallel/stacked, 90=crossing)")
print(f"  crossing (>55°): {(angs>55).sum()}/8   oblique(35-55): {((angs>=35)&(angs<=55)).sum()}/8   parallel(<35°): {(angs<35).sum()}/8")
print(f"mean corr(level-1 mixedness, level-2 seam-ness) within larger domain = {np.nanmean(corrs):+.3f}")
print(f"  (positive → the ambiguous 'leftover' pixels of floor 1 become the cut of floor 2)")
