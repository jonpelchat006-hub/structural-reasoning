import os; os.chdir("/home/claude/strain")
import numpy as np, pickle
from numpy.linalg import eigh
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())

def wfiedler(W):
    W=(W+W.T)/2.0; np.fill_diagonal(W,0)
    deg=W.sum(1); deg[deg<1e-9]=1e-9
    Dm=np.diag(1/np.sqrt(deg)); w,v=eigh(np.eye(len(W))-Dm@W@Dm)
    return (v[:,1]>=0).astype(int)
def agree(a,b):
    a=np.asarray(a);b=np.asarray(b);s=(a==b).mean();return max(s,1-s)

def coarse_test(coords,fine,b):
    n=len(coords); D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1))
    Ares=((D<8)&(D>0)).astype(float)
    blk=np.arange(n)//b; nb=blk.max()+1
    if nb<2: return None
    # coarse weighted adjacency = residue-contact counts between blocks
    W=np.zeros((nb,nb))
    for p in range(nb):
        rp=np.where(blk==p)[0]
        for q in range(p+1,nb):
            rq=np.where(blk==q)[0]
            c=Ares[np.ix_(rp,rq)].sum()
            W[p,q]=W[q,p]=c
    if W.sum()==0: return None
    blab=wfiedler(W); rlab=blab[blk]              # coarse cut propagated to residues
    ag=agree(rlab,fine)
    # permutation baseline: shuffle block labels keeping counts
    rng=np.random.default_rng(0); base=[]
    k=int(blab.sum())
    for _ in range(120):
        r=np.zeros(nb,int); r[rng.choice(nb,k,replace=False)]=1
        base.append(agree(r[blk],fine))
    ch=np.mean(base)
    # interior hidden: fraction of blocks containing BOTH fine domains
    mixed=0
    for p in range(nb):
        rp=np.where(blk==p)[0]
        if len(set(fine[rp]))>1: mixed+=1
    return ag,ch,mixed/nb

BS=[1,2,3,5,8,12]
print("C-LINE SURVIVAL across floors (coarse cut vs fine cut agreement) + interior hidden")
print("block b:      " + "".join(f"{b:>8}" for b in BS))
agg={b:[] for b in BS}; chg={b:[] for b in BS}; mixg={b:[] for b in BS}
for p in PROTEINS:
    d=R[p]; coords=d['coords']; fine=d['dom']
    row=[]
    for b in BS:
        r=coarse_test(coords,fine,b)
        if r is None: row.append("   -    "); continue
        ag,ch,mx=r; agg[b].append(ag); chg[b].append(ch); mixg[b].append(mx)
        row.append(f"{ag:>5.2f}  ")
    print(f"{p:6} agree "+"".join(row))
print("\n== MEANS across 8 ==")
print("block b (~pixel size):     "+"".join(f"{b:>8}" for b in BS))
print("C-line agree (survival):   "+"".join(f"{np.mean(agg[b]):>8.2f}" for b in BS))
print("  chance baseline:         "+"".join(f"{np.mean(chg[b]):>8.2f}" for b in BS))
print("  gain over chance:        "+"".join(f"{np.mean(agg[b])-np.mean(chg[b]):>+8.2f}" for b in BS))
print("interior hidden (mixed blk):"+"".join(f"{np.mean(mixg[b]):>8.2f}" for b in BS))
