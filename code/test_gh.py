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
    v=coords[dom==0].mean(0)-coords[dom==1].mean(0); return v/(np.linalg.norm(v)+1e-9)
def basis(n):
    a=np.array([1.0,0,0]) if abs(n[0])<0.9 else np.array([0,1.0,0])
    u=a-a.dot(n)*n; u/=np.linalg.norm(u); v=np.cross(n,u); return u,v
def linelike(pts2d):
    if len(pts2d)<3: return np.nan
    C=np.cov((pts2d-pts2d.mean(0)).T); ev=np.sort(np.linalg.eigvalsh(C))[::-1]
    return ev[0]/(ev.sum()+1e-12)

def parse_lig(path):
    xs=[]
    for line in open(path):
        if line.startswith("ENDMDL"): break
        if not line.startswith("HETATM"): continue
        if line[17:20].strip() in ("HOH","WAT","DOD"): continue
        xs.append((float(line[30:38]),float(line[38:46]),float(line[46:54])))
    return np.array(xs) if xs else None

rng=np.random.default_rng(0)
print("== TEST G: does C1 make a PATTERN (a stripe) on the C2 wall? ==")
print(f"{'pdb':6}{'C1 line-likeness':>18}{'random null':>13}")
gll=[]; gnull=[]
S={}
for p in PROTEINS:
    d=R[p]; coords=d['coords']; dom=d['dom']; mix1=d['mix']
    big=0 if (dom==0).sum()>=(dom==1).sum() else 1
    ix=np.where(dom==big)[0]; sub=coords[ix]; sdom=fiedler(sub); smix=mixed(sub,sdom)
    n2=normal(sub,sdom); u,v=basis(n2)
    seam1=coords[mix1>0.15]
    proj=np.column_stack([seam1@u, seam1@v])
    ll=linelike(proj)
    # null: random residues same count
    nulls=[]
    for _ in range(50):
        r=coords[rng.choice(len(coords),len(seam1),replace=False)]
        nulls.append(linelike(np.column_stack([r@u,r@v])))
    nl=np.nanmean(nulls)
    gll.append(ll); gnull.append(nl)
    print(f"{p:6}{ll:>18.3f}{nl:>13.3f}")
    # store convergence spots for Test H
    O=coords.mean(0)
    S1=seam1.mean(0)
    seam2=sub[smix>0.15]; S2=seam2.mean(0) if len(seam2) else sub.mean(0)
    # third level: recurse into larger sub-domain
    sbig=0 if (sdom==0).sum()>=(sdom==1).sum() else 1
    jx=np.where(sdom==sbig)[0]; sub2=sub[jx]; s2dom=fiedler(sub2); s2mix=mixed(sub2,s2dom)
    seam3=sub2[s2mix>0.15]; S3=seam3.mean(0) if len(seam3) else sub2.mean(0)
    S[p]=(O,S1,S2,S3,coords)
print(f"\nmean C1 line-likeness on C2 wall = {np.mean(gll):.3f}   vs random null {np.mean(gnull):.3f}")
print(f"  ({(np.array(gll)>np.array(gnull)).sum()}/8 proteins more line-like than random → C1 casts a stripe)")

print("\n== TEST H: the reference spots (convergence points) across cuts — shells & approach to the ligand D ==")
print(f"{'pdb':6}{'r(S1)':>7}{'r(S2)':>7}{'r(S3)':>7}{'|S1-S2|':>9}{'|S2-S3|':>9}{'ligand?':>9}{'d(S1,D)':>9}{'d(S2,D)':>9}{'d(S3,D)':>9}")
contract=[]; approach=[]
for p in PROTEINS:
    O,S1,S2,S3,coords=S[p]
    Rg=np.sqrt(((coords-O)**2).sum(1)).mean()  # radius of gyration-ish scale
    r1,r2,r3=[np.linalg.norm(x-O)/Rg for x in (S1,S2,S3)]
    d12=np.linalg.norm(S1-S2)/Rg; d23=np.linalg.norm(S2-S3)/Rg
    contract.append(d23<d12)
    lig=parse_lig(f"{p}.pdb")
    if lig is not None and len(lig)>=3:
        D=lig.mean(0)
        dd=[np.linalg.norm(x-D)/Rg for x in (S1,S2,S3)]
        approach.append(dd[2]<dd[0])
        print(f"{p:6}{r1:>7.2f}{r2:>7.2f}{r3:>7.2f}{d12:>9.2f}{d23:>9.2f}{'yes':>9}{dd[0]:>9.2f}{dd[1]:>9.2f}{dd[2]:>9.2f}")
    else:
        print(f"{p:6}{r1:>7.2f}{r2:>7.2f}{r3:>7.2f}{d12:>9.2f}{d23:>9.2f}{'no':>9}{'-':>9}{'-':>9}{'-':>9}")
print(f"\nspots contract (|S2-S3|<|S1-S2|): {sum(contract)}/8   (do successive reference spots settle?)")
if approach: print(f"spots approach ligand D (d(S3)<d(S1)): {sum(approach)}/{len(approach)} proteins with a ligand")
import pickle as pk; pk.dump(S,open("spotsH.pkl","wb"))
