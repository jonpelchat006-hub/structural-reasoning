import os, sys; os.chdir("/home/claude/strain")
import numpy as np, torch, esm
from scipy.stats import spearmanr
MODEL = sys.argv[1] if len(sys.argv)>1 else "esm2_t6_8M_UR50D"
TAG   = sys.argv[2] if len(sys.argv)>2 else "8M"
MAXLEN=1022; CHUNK=4

def load_fasta(p):
    d={};name=None;buf=[]
    for line in open(p):
        line=line.rstrip()
        if line.startswith(">"):
            if name:d[name]="".join(buf)
            name=line[1:].strip();buf=[]
        else:buf.append(line)
    if name:d[name]="".join(buf)
    return d
seqs=load_fasta("ddg/S669.fasta")
rows=[]
for line in open("ddg/S669.tsv").read().splitlines()[1:]:
    f=line.split("\t")
    if len(f)<5:continue
    rows.append((f[0],f[1],int(f[2]),f[3],float(f[4])))

model,alphabet=getattr(esm.pretrained,MODEL)(); model.eval(); torch.set_num_threads(4)
bc=alphabet.get_batch_converter(); mask_idx=alphabet.mask_idx
tok={aa:alphabet.get_idx(aa) for aa in "ACDEFGHIKLMNPQRSTVWY"}

# collect valid mutations on sequences within length limit, verify numbering
byseq={}
for pid,wt,pos,mt,ddg in rows:
    if pid not in seqs: continue
    s=seqs[pid]
    if len(s)>MAXLEN: continue
    if pos<1 or pos>len(s) or s[pos-1]!=wt: continue
    if wt not in tok or mt not in tok: continue
    byseq.setdefault(pid,[]).append((wt,pos,mt,ddg))

print(f"[{TAG}] scoring {sum(len(v) for v in byseq.values())} mutations on {len(byseq)} sequences (<= {MAXLEN} aa)",flush=True)
scores=[]; ddgs=[]; done=0
for pid,muts in byseq.items():
    s=seqs[pid]; _,_,toks=bc([("x",s)])
    positions=sorted(set(p for _,p,_,_ in muts))
    lpcache={}
    for i in range(0,len(positions),CHUNK):
        chunk=positions[i:i+CHUNK]
        batch=toks.repeat(len(chunk),1).clone()
        for r,pos in enumerate(chunk): batch[r,pos]=mask_idx   # token index = pos (BOS at 0)
        with torch.no_grad():
            lg=model(batch)["logits"]
            lp=torch.log_softmax(lg,dim=-1)
        for r,pos in enumerate(chunk): lpcache[pos]=lp[r,pos]
    for wt,pos,mt,ddg in muts:
        scores.append((lpcache[pos][tok[mt]]-lpcache[pos][tok[wt]]).item()); ddgs.append(ddg)
    done+=1
    if done%15==0: print(f"  {done}/{len(byseq)} sequences done",flush=True)
scores=np.array(scores); ddgs=np.array(ddgs)
rho,pval=spearmanr(scores,ddgs)
tol=ddgs>-0.5; dest=ddgs<-1.0
allv=np.concatenate([scores[tol],scores[dest]]); lab=np.concatenate([np.ones(tol.sum()),np.zeros(dest.sum())])
o=np.argsort(allv); rk=np.empty(len(allv)); rk[o]=np.arange(1,len(allv)+1)
auc=(rk[lab==1].sum()-lab.sum()*(lab.sum()+1)/2)/(lab.sum()*(lab==0).sum())
print(f"\n[{TAG}] masked-marginal on {len(scores)} variants:",flush=True)
print(f"  Spearman(score, measured ddG) = {rho:+.3f}  (p={pval:.1e})",flush=True)
print(f"  AUC(tolerated>destabilizing)  = {auc:.3f}   (tol n={tol.sum()} mean {scores[tol].mean():+.2f}, dest n={dest.sum()} mean {scores[dest].mean():+.2f})",flush=True)
np.savez(f"s669_{TAG}_masked.npz",scores=scores,ddgs=ddgs,rho=rho,auc=auc)
print(f"[{TAG}] DONE",flush=True)
