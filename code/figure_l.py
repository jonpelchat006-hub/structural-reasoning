import os; os.chdir("/home/claude/strain")
import numpy as np, pickle, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())
def contacts(coords,cut=8.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1)); return ((D<cut)&(D>0)).astype(float)
def fied(A):
    deg=A.sum(1); deg[deg==0]=1; Dm=np.diag(1/np.sqrt(deg))
    w,v=eigh(np.eye(len(A))-Dm@A@Dm); return (v[:,1]>=0).astype(int)
def recurse(coords,maxd=7,minn=25):
    A0=contacts(coords); tot=A0.sum()/2; idx=np.arange(len(coords)); sev=[]; seam=set()
    for d in range(maxd):
        C=A0[np.ix_(idx,idx)]
        if len(idx)<minn or C.sum()==0: break
        lab=fied(C)
        if lab.sum()==0 or lab.sum()==len(lab): break
        sev.append(C[np.ix_(lab==0,lab==1)].sum())
        for a in np.where(lab==0)[0]:
            if C[a][lab==1].sum()>0: seam.add(idx[a])
        for b in np.where(lab==1)[0]:
            if C[b][lab==0].sum()>0: seam.add(idx[b])
        big=0 if (lab==0).sum()>=(lab==1).sum() else 1; idx=idx[lab==big]
    return np.array(sev), tot, len(seam)

fig,ax=plt.subplots(1,2,figsize=(13,4.8))
a=ax[0]
for p in PROTEINS:
    sev,tot,_=recurse(R[p]['coords'])
    a.plot(range(1,len(sev)+1), sev/sev[0], '-o', ms=4, label=p, alpha=0.8)
a.set_xlabel("recursion depth (fold level)"); a.set_ylabel("edges severed this level  (/ level-1)")
a.set_title("The budget is SPENT DOWN\nearly folds cut the big cloth, later folds get scraps",fontsize=10.5)
a.legend(fontsize=7,ncol=2)
b=ax[1]
seamL=[]; cumE=[]
for p in PROTEINS:
    sev,tot,nseam=recurse(R[p]['coords']); seamL.append(nseam/len(R[p]['coords'])); cumE.append(sev.sum()/tot)
x=np.arange(len(PROTEINS)); w=0.38
b.bar(x-w/2, seamL, w, label=f"seam residues / L  (mean {np.mean(seamL):.2f}, CV {np.std(seamL)/np.mean(seamL):.2f})", color="#2b6cb0", edgecolor='k')
b.bar(x+w/2, cumE, w, label=f"total contacts cut / all  (mean {np.mean(cumE):.2f}, CV {np.std(cumE)/np.mean(cumE):.2f})", color="#dd6b20", edgecolor='k')
b.axhline(np.mean(seamL), color="#2b6cb0", ls=':', lw=1); b.axhline(np.mean(cumE), color="#dd6b20", ls=':', lw=1)
b.set_xticks(x); b.set_xticklabels(PROTEINS, rotation=45, fontsize=9); b.set_ylabel("fraction")
b.set_title("The TOTAL is a definite size (tight across proteins)\nthe blanket has a fixed area we can track",fontsize=10.5)
b.legend(fontsize=8, loc='upper left')
plt.suptitle("The finite blanket: folding keeps creating seam, but only up to a DEFINITE bounded total (~36% of residues, CV 0.15)",fontsize=11.5,weight='bold')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig("blanket.png",dpi=140); print("saved")
