import os; os.chdir("/home/claude/strain")
import numpy as np, pickle
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())
PHI=(1+5**0.5)/2; INVPHI=1/PHI  # 0.618

def fiedler(coords,cutoff=8.0):
    if len(coords)<4: return None
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1))
    A=((D<cutoff)&(D>0)).astype(float); deg=A.sum(1)
    if (deg==0).any(): deg=deg.copy(); deg[deg==0]=1
    Dm=np.diag(1/np.sqrt(deg))
    try: w,v=eigh(np.eye(len(coords))-Dm@A@Dm)
    except: return None
    return (v[:,1]>=0).astype(int)

def recurse_fractions(coords, maxdepth=7, minn=25):
    """repeatedly Fiedler-cut, keep the LARGER half, record larger-fraction + region radius each level"""
    idx=np.arange(len(coords)); fracs=[]; radii=[]; cents=[]
    for d in range(maxdepth):
        sub=coords[idx]
        if len(sub)<minn: break
        lab=fiedler(sub)
        if lab is None: break
        nA=(lab==0).sum(); nB=(lab==1).sum()
        if nA==0 or nB==0: break
        frac=max(nA,nB)/(nA+nB)
        fracs.append(frac)
        radii.append(np.sqrt(((sub-sub.mean(0))**2).sum(1)).mean())
        cents.append(sub.mean(0))
        big=0 if nA>=nB else 1
        idx=idx[lab==big]
    return np.array(fracs), np.array(radii), np.array(cents)

def blob_null(coords, ntrials=30, seed=0):
    """same-N points with the protein's own shape (matched covariance), recursive-cut ratio"""
    rng=np.random.default_rng(seed)
    C=np.cov((coords-coords.mean(0)).T); L=np.linalg.cholesky(C+1e-6*np.eye(3))
    out=[]
    for _ in range(ntrials):
        pts=(rng.standard_normal((len(coords),3))@L.T)+coords.mean(0)
        f,_,_=recurse_fractions(pts)
        if len(f)>=2: out.append(f.mean())
    return np.array(out)

print(f"golden section 1/phi = {INVPHI:.4f}   even split = 0.5\n")
print(f"{'pdb':6}{'levels':>7}{'larger-fractions per level':>34}{'mean':>7}{'blob-null mean±sd':>20}")
allf=[]; nullmeans=[]; protmeans=[]
stepratios=[]
for p in PROTEINS:
    coords=R[p]['coords']
    f,rad,cents=recurse_fractions(coords)
    nullm=blob_null(coords)
    allf.extend(f.tolist()); protmeans.append(f.mean()); nullmeans.append(nullm.mean())
    # spot-step contraction ratios between successive region centroids
    if len(cents)>=3:
        steps=np.linalg.norm(np.diff(cents,axis=0),axis=1)
        rr=steps[1:]/(steps[:-1]+1e-9)
        stepratios.extend(rr.tolist())
    fstr=" ".join(f"{x:.3f}" for x in f)
    print(f"{p:6}{len(f):>7}   {fstr:<31}{f.mean():>7.3f}{nullm.mean():>13.3f}±{nullm.std():.3f}")
allf=np.array(allf); protmeans=np.array(protmeans); nullmeans=np.array(nullmeans)
print(f"\n== POOLED across all {len(allf)} recursive cuts ==")
print(f"mean larger-fraction (real)       = {allf.mean():.4f}  (sd {allf.std():.3f})")
print(f"mean larger-fraction (blob null)  = {nullmeans.mean():.4f}")
print(f"golden section 1/phi              = {INVPHI:.4f}")
print(f"even split                        = 0.5000")
print(f"|real - 1/phi| = {abs(allf.mean()-INVPHI):.4f}   |real - 0.5| = {abs(allf.mean()-0.5):.4f}   |real - null| = {abs(allf.mean()-nullmeans.mean()):.4f}")
# is real closer to golden than the null is? and than 0.5?
from math import sqrt
se=allf.std()/sqrt(len(allf))
print(f"real mean 95% CI ~ [{allf.mean()-2*se:.3f}, {allf.mean()+2*se:.3f}]  (does it contain 1/phi? 0.5?)")
if stepratios:
    sr=np.array(stepratios)
    print(f"\nspot-step contraction ratio (successive |ΔS|): mean {sr.mean():.3f}, median {np.median(sr):.3f}  vs 1/phi {INVPHI:.3f}")
# self-similarity: is larger-fraction stable across depth?
maxL=max(len(recurse_fractions(R[p]['coords'])[0]) for p in PROTEINS)
print("\nper-level mean larger-fraction (self-similar if flat):")
for lv in range(maxL):
    vals=[recurse_fractions(R[p]['coords'])[0][lv] for p in PROTEINS if len(recurse_fractions(R[p]['coords'])[0])>lv]
    print(f"  level {lv+1}: {np.mean(vals):.3f}  (n={len(vals)})")
