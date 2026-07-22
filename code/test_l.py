import os; os.chdir("/home/claude/strain")
import numpy as np, pickle
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())

def contacts(coords,cut=8.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1))
    return ((D<cut)&(D>0)), D

def fiedler_from_A(A):
    deg=A.sum(1); deg[deg==0]=1
    Dm=np.diag(1/np.sqrt(deg))
    w,v=eigh(np.eye(len(A))-Dm@A@Dm)
    return (v[:,1]>=0).astype(int)

def recurse_budget(coords, maxdepth=7, minn=25):
    """at each level: severed edges (min-cut cloth), region edges, seam residues. Track cumulative."""
    A0,_=contacts(coords); A0=A0.astype(float)
    total_edges=A0.sum()/2
    idx=np.arange(len(coords))
    severed=[]; seam_res=set(); region_edges0=None
    for d in range(maxdepth):
        sub=idx
        C=A0[np.ix_(sub,sub)]
        if len(sub)<minn or C.sum()==0: break
        lab=fiedler_from_A(C)
        if lab.sum()==0 or lab.sum()==len(lab): break
        cut_edges=C[np.ix_(lab==0,lab==1)].sum()   # edges severed by this cut = the cloth threads
        severed.append(cut_edges)
        # seam residues of this cut (both endpoints touching the other side)
        for a in np.where(lab==0)[0]:
            if C[a][lab==1].sum()>0: seam_res.add(sub[a])
        for b in np.where(lab==1)[0]:
            if C[b][lab==0].sum()>0: seam_res.add(sub[b])
        big=0 if (lab==0).sum()>=(lab==1).sum() else 1
        idx=sub[lab==big]
    return np.array(severed), total_edges, len(seam_res)

print(f"{'pdb':6}{'L':>5}{'totE':>7}{'cut1':>6}{'cut1/L':>8}{'cut1/E':>8}{'cumCut/E':>9}{'seamRes/L':>10}{'levels':>7}")
c1L=[]; c1E=[]; cumE=[]; seamL=[]
for p in PROTEINS:
    coords=R[p]['coords']; L=len(coords)
    sev,tot,nseam=recurse_budget(coords)
    print(f"{p:6}{L:>5}{tot:>7.0f}{sev[0]:>6.0f}{sev[0]/L:>8.2f}{sev[0]/tot:>8.3f}{sev.sum()/tot:>9.3f}{nseam/L:>10.2f}{len(sev):>7}")
    c1L.append(sev[0]/L); c1E.append(sev[0]/tot); cumE.append(sev.sum()/tot); seamL.append(nseam/L)
def tight(x): 
    x=np.array(x); return f"mean {x.mean():.3f}  sd {x.std():.3f}  CV {x.std()/x.mean():.2f}  range [{x.min():.2f},{x.max():.2f}]"
print(f"\nprimary cut / L        : {tight(c1L)}   (cloth threads per residue)")
print(f"primary cut / total-E  : {tight(c1E)}   (fraction of ALL contacts severed by cut 1)")
print(f"CUMULATIVE cut / total-E: {tight(cumE)}   (does deeper folding SPEND a fixed budget, or create?)")
print(f"seam residues / L      : {tight(seamL)}")
print("\nInterpretation check:")
print("  if cumCut/E stays small & bounded across depth -> the cloth is a fixed sparse budget (finite blanket)")
print("  the ratio cumCut/cut1 shows how much MORE is severed by going deeper:")
for p in PROTEINS:
    sev,tot,_=recurse_budget(R[p]['coords'])
    print(f"    {p}: cut1={sev[0]:.0f}  cumulative={sev.sum():.0f}  ratio={sev.sum()/sev[0]:.2f}  per-level={np.round(sev,0).tolist()}")
