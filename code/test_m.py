import os; os.chdir("/home/claude/strain")
import numpy as np, pickle, torch, esm
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())
t2o={'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}
model,alphabet=esm.pretrained.esm2_t6_8M_UR50D(); model.eval(); torch.set_num_threads(4)
bc=alphabet.get_batch_converter()

def true_contacts(coords,cut=8.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1))
    return (D<cut)&(D>0)

def plm_map(seq):
    _,_,toks=bc([("x",seq)])
    with torch.no_grad(): c=model.predict_contacts(toks)[0].numpy()
    return (c+c.T)/2

def lr_precision(cmap, true, L, frac=5, sep=12):
    n=len(cmap); ii,jj=np.meshgrid(np.arange(n),np.arange(n),indexing='ij')
    m=(jj-ii)>sep   # long-range upper triangle
    idx=np.argwhere(m); probs=cmap[m]
    k=max(1,L//frac)
    top=idx[np.argsort(probs)[::-1][:k]]
    hits=sum(1 for a,b in top if true[a,b])
    return hits/len(top)

def lr_baseline(true,sep=12):
    n=len(true); ii,jj=np.meshgrid(np.arange(n),np.arange(n),indexing='ij')
    m=(jj-ii)>sep
    return true[m].mean()

rng=np.random.default_rng(0)
print(f"{'pdb':6}{'L':>5}{'demand(LRdens)':>15}{'SUPPLY real':>12}{'SUPPLY scram':>13}{'baseline':>10}{'budget real':>12}{'budget scram':>13}")
rows=[]
for p in PROTEINS:
    coords=R[p]['coords']; L=len(coords); seq="".join(t2o.get(r,'X') for r in R[p]['res'])
    true=true_contacts(coords)
    base=lr_baseline(true)
    sup_real=lr_precision(plm_map(seq),true,L)
    scr=[]
    for _ in range(3):
        s=list(seq); rng.shuffle(s); scr.append(lr_precision(plm_map("".join(s)),true,L))
    sup_scr=np.mean(scr)
    # demand = how much long-range structure must be pinned (higher = more nonlocal fold)
    demand=base  # long-range contact density ~ how "knitted"/nonlocal
    budget_real=sup_real-base; budget_scr=sup_scr-base
    print(f"{p:6}{L:>5}{base:>15.3f}{sup_real:>12.3f}{sup_scr:>13.3f}{base:>10.3f}{budget_real:>12.3f}{budget_scr:>13.3f}")
    rows.append((p,L,base,sup_real,sup_scr,budget_real,budget_scr))
import numpy as np
br=np.array([r[5] for r in rows]); bs=np.array([r[6] for r in rows]); sr=np.array([r[3] for r in rows]); ss=np.array([r[4] for r in rows])
print(f"\n== MEANS ==")
print(f"SUPPLY real seq (top-L/5 long-range precision) = {sr.mean():.3f}   (how much structure the sequence pays for)")
print(f"SUPPLY scrambled seq                            = {ss.mean():.3f}   (composition kept, order destroyed)")
print(f"real budget (supply - baseline)  = {br.mean():.3f}   ({(br>0).sum()}/8 positive -> under budget, folds)")
print(f"scrambled budget                 = {bs.mean():.3f}   ({(bs<=0.02).sum()}/8 ~collapsed -> OVER budget, would fail)")
print(f"supply drop on scrambling        = {(sr-ss).mean():.3f}   (the sequence-specific budget)")
np.savez("budgetM.npz", rows=np.array([(r[1],r[2],r[3],r[4]) for r in rows]), prots=np.array(PROTEINS))
