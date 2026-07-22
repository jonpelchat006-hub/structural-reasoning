import numpy as np
from numpy.linalg import eigh
PROTEINS = ["1CLL","3PGK","1PHP","1GD1","6LDH","8TLN","4AKE","2LZM"]

def parse_ca(path):
    coords, bf, res = [], [], []
    chain0=None; seen=set()
    for line in open(path):
        if line.startswith("ENDMDL"): break
        if not line.startswith("ATOM"): continue
        if line[12:16].strip()!="CA": continue
        if line[16] not in (" ","A"): continue
        ch=line[21]
        if chain0 is None: chain0=ch
        if ch!=chain0: continue
        rs=line[22:27]
        if rs in seen: continue
        seen.add(rs)
        coords.append((float(line[30:38]),float(line[38:46]),float(line[46:54])))
        bf.append(float(line[60:66])); res.append(line[17:20].strip())
    return np.array(coords), np.array(bf), res

def fiedler(coords, cutoff=8.0):
    D=np.sqrt(((coords[:,None,:]-coords[None,:,:])**2).sum(-1))
    A=((D<cutoff)&(D>0)).astype(float)
    deg=A.sum(1); deg[deg==0]=1
    Dm=np.diag(1/np.sqrt(deg))
    w,v=eigh(np.eye(len(coords))-Dm@A@Dm)
    return (v[:,1]>=0).astype(int), D

def mixedness(dom, Dm, sigma=6.0, cut=10.0):
    n=len(dom); mix=np.zeros(n)
    for i in range(n):
        nb=np.where((Dm[i]<cut)&(Dm[i]>0))[0]
        if len(nb)==0: continue
        w=np.exp(-(Dm[i,nb]/sigma)**2)
        mix[i]=w[dom[nb]!=dom[i]].sum()/w.sum()
    return mix

def local_shape(coords, Dm, cut=10.0):
    n=len(coords); plan=np.zeros(n); aniso=np.zeros(n); spher=np.zeros(n); dens=np.zeros(n)
    for i in range(n):
        nb=np.where((Dm[i]<cut)&(Dm[i]>=0))[0]; dens[i]=len(nb)-1
        pts=coords[nb]
        if len(pts)<4: continue
        ev=np.sort(np.linalg.eigvalsh(np.cov((pts-pts.mean(0)).T)))[::-1]
        s=ev.sum()
        if s<=0: continue
        l1,l2,l3=ev
        plan[i]=(l2-l3)/s; aniso[i]=(l1-l3)/s; spher[i]=3*l3/s
    return plan,aniso,spher,dens

def z(x):
    x=np.asarray(x,float); s=x.std(); return (x-x.mean())/s if s>0 else x*0
def corr(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    return np.nan if a.std()==0 or b.std()==0 else np.corrcoef(a,b)[0,1]
def partial(a,b,c):
    a,b,c=[z(x) for x in (a,b,c)]
    ra=a-np.polyval(np.polyfit(c,a,1),c); rb=b-np.polyval(np.polyfit(c,b,1),c)
    return corr(ra,rb)

R={}; pool={k:[] for k in ['plan','aniso','spher','dens','bf','dcen','mix']}
print(f"{'pdb':6}{'n':>5}{'r(plan,mix)':>13}{'r(spher,mix)':>13}{'r(aniso,mix)':>13}")
for p in PROTEINS:
    coords,bf,res=parse_ca(f"{p}.pdb")
    dom,Dm=fiedler(coords); mix=mixedness(dom,Dm)
    plan,aniso,spher,dens=local_shape(coords,Dm)
    seam=coords[mix>0.15]; cen=seam.mean(0) if len(seam) else coords.mean(0)
    dcen=np.sqrt(((coords-cen)**2).sum(1))
    R[p]=dict(coords=coords,bf=bf,res=res,dom=dom,Dm=Dm,mix=mix,plan=plan,aniso=aniso,spher=spher,dens=dens,dcen=dcen)
    np.savez(f"{p}_data.npz",coords=coords,bf=bf,dom=dom,mix=mix,plan=plan,aniso=aniso,spher=spher,dens=dens,dcen=dcen)
    for k in ['plan','aniso','spher','dens','bf','dcen']: pool[k].append(z(R[p][k]))
    pool['mix'].append(z(mix))
    print(f"{p:6}{len(coords):>5}{corr(plan,mix):>13.3f}{corr(spher,mix):>13.3f}{corr(aniso,mix):>13.3f}")
for k in pool: pool[k]=np.concatenate(pool[k])
np.savez("pool.npz",**pool)
print(f"\n== POOLED n={len(pool['mix'])} ==")
print(f"corr(planarity , mixedness)  = {corr(pool['plan'],pool['mix']):+.3f}")
print(f"corr(sphericity, mixedness)  = {corr(pool['spher'],pool['mix']):+.3f}  (expect - : less round at seam)")
print(f"corr(anisotropy, mixedness)  = {corr(pool['aniso'],pool['mix']):+.3f}")
print(f"corr(planarity , dist-to-seam)= {corr(pool['plan'],pool['dcen']):+.3f}  (expect - : flatter toward seam)")
print(f"\nCONTROL (burial): corr(plan,density)={corr(pool['plan'],pool['dens']):+.3f}  corr(mix,density)={corr(pool['mix'],pool['dens']):+.3f}")
print(f"partial corr(planarity, mixedness | density) = {partial(pool['plan'],pool['mix'],pool['dens']):+.3f}")
import pickle; pickle.dump(R, open("R.pkl","wb"))
