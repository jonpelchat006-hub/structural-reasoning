import os; os.chdir("/home/claude/strain")
import numpy as np, pickle, torch, esm
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())
t2o={'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}
model,alphabet=esm.pretrained.esm2_t6_8M_UR50D(); model.eval(); torch.set_num_threads(4)
bc=alphabet.get_batch_converter(); mask_idx=alphabet.mask_idx
tok_of={aa:alphabet.get_idx(aa) for aa in "ACDEFGHIKLMNPQRSTVWY"}

def true_contacts(coords,cut=8.0):
    D=np.sqrt(((coords[:,None]-coords[None])**2).sum(-1)); return (D<cut)&(D>0)
def plm_map(seq):
    _,_,toks=bc([("x",seq)])
    with torch.no_grad(): c=model.predict_contacts(toks)[0].numpy()
    return (c+c.T)/2
def lr_prec(cmap,true,L,frac=5,sep=12):
    n=len(cmap); ii,jj=np.meshgrid(np.arange(n),np.arange(n),indexing='ij'); m=(jj-ii)>sep
    idx=np.argwhere(m); p=cmap[m]; k=max(1,L//frac)
    top=idx[np.argsort(p)[::-1][:k]]
    return sum(1 for a,b in top if true[a,b])/len(top)
def lr_base(true,sep=12):
    n=len(true); ii,jj=np.meshgrid(np.arange(n),np.arange(n),indexing='ij'); m=(jj-ii)>sep
    return true[m].mean()

rng=np.random.default_rng(0)
# ---------- PART 1: partial-scramble dose-response ----------
FRACS=[0.0,0.15,0.3,0.5,1.0]
print("=== PART 1: dose-response (supply vs fraction of sequence scrambled) ===")
print("pdb    " + "".join(f"f={f:<5}" for f in FRACS) + "  baseline")
dose={f:[] for f in FRACS}; bases=[]
for p in PROTEINS:
    coords=R[p]['coords']; L=len(coords); seq=list("".join(t2o.get(r,'X') for r in R[p]['res']))
    true=true_contacts(coords); base=lr_base(true); bases.append(base)
    row=[]
    for f in FRACS:
        vals=[]
        for _ in range(2):
            s=seq[:]; npos=int(round(f*L))
            pos=rng.choice(L,npos,replace=False); perm=rng.permutation(pos)
            for a,b in zip(pos,perm): s[a]=seq[b]
            vals.append(lr_prec(plm_map("".join(s)),true,L))
        m=np.mean(vals); dose[f].append(m); row.append(m)
    print(f"{p:6} " + "".join(f"{v:<7.3f}" for v in row) + f"  {base:.3f}")
print("MEAN   " + "".join(f"{np.mean(dose[f]):<7.3f}" for f in FRACS) + f"  {np.mean(bases):.3f}")

# ---------- PART 2: structure-grounded mutants, ESM variant log-odds ----------
CONS={'S':'T','T':'S','N':'Q','Q':'N','D':'E','E':'D','K':'R','R':'K','H':'N','Y':'F','F':'Y'}
HYD=set("AVLIMFWC")
def variant_logodds(seq, pos, wt, mut):
    _,_,toks=bc([("x",seq)]); toks=toks.clone(); toks[0,pos+1]=mask_idx
    with torch.no_grad(): lp=torch.log_softmax(model(toks)["logits"][0,pos+1],dim=-1)
    return (lp[tok_of[mut]]-lp[tok_of[wt]]).item()

print("\n=== PART 2: structure-grounded mutants (does the pLM score rank folders > failures?) ===")
print(f"{'pdb':6}{'disruptive(bury charge)':>24}{'benign(surface cons.)':>23}{'separation':>12}")
allpts=[]
for p in ['2LZM','1GD1','8TLN','4AKE']:
    coords=R[p]['coords']; L=len(coords); seq="".join(t2o.get(r,'X') for r in R[p]['res'])
    dens=R[p]['dens']; dz=(dens-dens.mean())/dens.std()
    res1=[t2o.get(r,'X') for r in R[p]['res']]
    buried=[i for i in range(L) if dz[i]>0.7 and res1[i] in HYD]
    surface=[i for i in range(L) if dz[i]<-0.5 and res1[i] in CONS]
    rng2=np.random.default_rng(1)
    bsel=rng2.choice(buried,min(6,len(buried)),replace=False) if buried else []
    ssel=rng2.choice(surface,min(6,len(surface)),replace=False) if surface else []
    dis=[variant_logodds(seq,i,res1[i],'D') for i in bsel]        # bury a charge -> should be bad
    ben=[variant_logodds(seq,i,res1[i],CONS[res1[i]]) for i in ssel]  # conservative surface -> benign
    for v in dis: allpts.append((v,0))
    for v in ben: allpts.append((v,1))
    print(f"{p:6}{np.mean(dis):>18.2f} (n{len(dis)}){np.mean(ben):>17.2f} (n{len(ben)}){np.mean(ben)-np.mean(dis):>12.2f}")
# ranking: does score separate benign(fold) from disruptive(fail)?
v=np.array([a for a,_ in allpts]); y=np.array([b for _,b in allpts])
o=np.argsort(v); rk=np.empty(len(v)); rk[o]=np.arange(1,len(v)+1)
auc=(rk[y==1].sum()-(y==1).sum()*((y==1).sum()+1)/2)/((y==1).sum()*(y==0).sum())
print(f"\nAUC(pLM score ranks benign/folding ABOVE disruptive/failing) = {auc:.3f}  (0.5=no power, 1=perfect)")
print(f"  disruptive mean log-odds {v[y==0].mean():+.2f}   benign mean {v[y==1].mean():+.2f}   n={len(v)}")
np.savez("doseN.npz", fracs=np.array(FRACS), dose=np.array([dose[f] for f in FRACS]), base=np.mean(bases),
         dis=v[y==0], ben=v[y==1])
print("DONE")
