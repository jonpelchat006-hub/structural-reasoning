import numpy as np, pickle
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb"))
PROTEINS=list(R.keys())

def parse_bb(path):
    # backbone N,CA,C per residue (first chain, first model)
    rec={}; order=[]; chain0=None
    for line in open(path):
        if line.startswith("ENDMDL"): break
        if not line.startswith("ATOM"): continue
        atom=line[12:16].strip()
        if atom not in ("N","CA","C"): continue
        if line[16] not in (" ","A"): continue
        ch=line[21]
        if chain0 is None: chain0=ch
        if ch!=chain0: continue
        key=line[22:27]
        xyz=(float(line[30:38]),float(line[38:46]),float(line[46:54]))
        if key not in rec: rec[key]={}; order.append(key)
        rec[key].setdefault(atom,xyz)
    return [rec[k] for k in order]

def dih(p0,p1,p2,p3):
    b0=p0-p1; b1=p2-p1; b2=p3-p2
    b1/=np.linalg.norm(b1)
    v=b0-np.dot(b0,b1)*b1; w=b2-np.dot(b2,b1)*b1
    x=np.dot(v,w); y=np.dot(np.cross(b1,v),w)
    return np.degrees(np.arctan2(y,x))

def phipsi(bb):
    n=len(bb); phi=np.full(n,np.nan); psi=np.full(n,np.nan)
    P=[ {k:np.array(v) for k,v in r.items()} for r in bb ]
    for i in range(n):
        if all(a in P[i] for a in("N","CA","C")):
            if i>0 and "C" in P[i-1]:
                phi[i]=dih(P[i-1]["C"],P[i]["N"],P[i]["CA"],P[i]["C"])
            if i<n-1 and "N" in P[i+1]:
                psi[i]=dih(P[i]["N"],P[i]["CA"],P[i]["C"],P[i+1]["N"])
    return phi,psi

# canonical basins (phi,psi): alpha, beta, left-handed alpha, ppII
BASINS=np.array([(-63,-42),(-135,135),(60,45),(-75,150),(-63,-42)])
def rama_atypical(phi,psi):
    n=len(phi); out=np.zeros(n)
    for i in range(n):
        if np.isnan(phi[i]) or np.isnan(psi[i]): out[i]=np.nan; continue
        d=[]
        for bx,by in BASINS:
            dp=abs((phi[i]-bx+180)%360-180); dq=abs((psi[i]-by+180)%360-180)
            d.append(np.hypot(dp,dq))
        out[i]=min(d)   # angular distance to nearest canonical basin
    return out

def ca_kink(coords):
    n=len(coords); k=np.full(n,np.nan)
    for i in range(1,n-1):
        a=coords[i-1]-coords[i]; b=coords[i+1]-coords[i]
        c=np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9)
        k[i]=np.degrees(np.arccos(np.clip(c,-1,1)))
    # irregularity = deviation from local running median
    irr=np.full(n,np.nan)
    for i in range(n):
        lo,hi=max(0,i-3),min(n,i+4)
        w=k[lo:hi]; w=w[~np.isnan(w)]
        if not np.isnan(k[i]) and len(w)>2: irr[i]=abs(k[i]-np.median(w))
    return irr

def z(x):
    x=np.asarray(x,float); m=~np.isnan(x)
    o=np.full(len(x),np.nan); s=x[m].std()
    if s>0: o[m]=(x[m]-x[m].mean())/s
    return o
def corr(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); m=~np.isnan(a)&~np.isnan(b)
    if m.sum()<5 or a[m].std()==0 or b[m].std()==0: return np.nan
    return np.corrcoef(a[m],b[m])[0,1]
def auc(score,label):
    s=np.asarray(score,float); y=np.asarray(label).astype(bool); m=~np.isnan(s)
    s,y=s[m],y[m]
    if y.sum()==0 or y.sum()==len(y): return np.nan
    order=np.argsort(s); ranks=np.empty(len(s)); ranks[order]=np.arange(1,len(s)+1)
    return (ranks[y].sum()-y.sum()*(y.sum()+1)/2)/(y.sum()*(~y).sum())

def secondary_seam(coords,dom,Dm):
    # recurse into the LARGER domain, Fiedler-split it, compute within-subgraph mixedness
    big=0 if (dom==0).sum()>=(dom==1).sum() else 1
    idx=np.where(dom==big)[0]
    if len(idx)<30: return np.zeros(len(coords),bool), np.full(len(coords),np.nan)
    sub=coords[idx]
    Ds=np.sqrt(((sub[:,None]-sub[None])**2).sum(-1))
    A=((Ds<8)&(Ds>0)).astype(float); deg=A.sum(1); deg[deg==0]=1
    Dd=np.diag(1/np.sqrt(deg))
    w,v=eigh(np.eye(len(sub))-Dd@A@Dd)
    sd=(v[:,1]>=0).astype(int)
    smix=np.zeros(len(sub))
    for a in range(len(sub)):
        nb=np.where((Ds[a]<10)&(Ds[a]>0))[0]
        if len(nb)==0: continue
        wt=np.exp(-(Ds[a,nb]/6)**2)
        smix[a]=wt[sd[nb]!=sd[a]].sum()/wt.sum()
    full_smix=np.full(len(coords),np.nan); full_smix[idx]=smix
    seam2=np.zeros(len(coords),bool); seam2[idx[smix>0.15]]=True
    return seam2, full_smix

hdr=f"{'pdb':6}{'B@seam':>8}{'B@rest':>8}{'dens@seam':>10}{'B@seam2':>9}{'r(rama,B)':>10}{'r(kink,B)':>10}{'AUC rama→seam':>14}"
print(hdr)
pool={k:[] for k in ['B','dens','mix','rama','kink','plan','aniso','seam','seam2','smix']}
for p in PROTEINS:
    d=R[p]; coords=d['coords']; bf=d['bf']; dom=d['dom']; Dm=d['Dm']; mix=d['mix']
    bb=parse_bb(f"{p}.pdb")
    L=len(coords)
    if len(bb)!=L: bb=bb[:L]+[{}]*(L-len(bb))
    phi,psi=phipsi(bb); rama=rama_atypical(phi,psi); kink=ca_kink(coords)
    seam2,smix=secondary_seam(coords,dom,Dm)
    seam=mix>0.15
    bz=z(bf); dz=z(d['dens'])
    Bseam=np.nanmean(bz[seam]); Brest=np.nanmean(bz[~seam])
    densseam=np.nanmean(dz[seam])
    Bseam2=np.nanmean(bz[seam2]) if seam2.sum()>0 else np.nan
    print(f"{p:6}{Bseam:>8.2f}{Brest:>8.2f}{densseam:>10.2f}{Bseam2:>9.2f}{corr(rama,bf):>10.3f}{corr(kink,bf):>10.3f}{auc(rama,seam):>14.3f}")
    for k,val in [('B',bz),('dens',dz),('mix',z(mix)),('rama',z(rama)),('kink',z(kink)),('plan',z(d['plan'])),('aniso',z(d['aniso']))]:
        pool[k].append(val)
    pool['seam'].append(seam); pool['seam2'].append(seam2); pool['smix'].append(smix)
for k in pool: pool[k]=np.concatenate(pool[k])
np.savez("poolB.npz",**pool)
print(f"\n== POOLED n={len(pool['B'])} ==")
print(f"corr(B-factor , mixedness)      = {corr(pool['B'],pool['mix']):+.3f}   (is the seam more mobile/weak?)")
print(f"corr(B-factor , density)        = {corr(pool['B'],pool['dens']):+.3f}   (under-packed = mobile, expect -)")
print(f"corr(rama-atypical , B-factor)  = {corr(pool['rama'],pool['B']):+.3f}   (deformed backbone = weak?)")
print(f"corr(kink-irregular, B-factor)  = {corr(pool['kink'],pool['B']):+.3f}")
print(f"corr(rama-atypical , mixedness) = {corr(pool['rama'],pool['mix']):+.3f}   (deformed at the seam?)")
print(f"corr(kink-irregular, mixedness) = {corr(pool['kink'],pool['mix']):+.3f}")
m2=~np.isnan(pool['smix'])
print(f"\n--- recursive (secondary) cut, within larger domain ---")
print(f"corr(within-domain mix2, B-factor) = {corr(pool['smix'][m2],pool['B'][m2]):+.3f}   (does the NEXT cut follow weak material?)")
print(f"corr(within-domain mix2, density)  = {corr(pool['smix'][m2],pool['dens'][m2]):+.3f}")
print(f"AUC: B-factor ranks secondary-seam = {auc(pool['B'],pool['seam2']):.3f}")
print(f"AUC: rama      ranks secondary-seam= {auc(pool['rama'],pool['seam2']):.3f}")
print(f"AUC: low-density ranks secondary   = {auc(-pool['dens'],pool['seam2']):.3f}")
