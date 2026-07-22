import os, sys; os.chdir("/home/claude/strain")
import numpy as np, torch, esm
from scipy.stats import spearmanr
MODEL=sys.argv[1]; TAG=sys.argv[2]; MAXLEN=int(sys.argv[3]) if len(sys.argv)>3 else 450
def load_fasta(p):
    d={};name=None;buf=[]
    for l in open(p):
        l=l.rstrip()
        if l.startswith(">"):
            if name:d[name]="".join(buf)
            name=l[1:].strip();buf=[]
        else:buf.append(l)
    if name:d[name]="".join(buf)
    return d
seqs=load_fasta("ddg/S669.fasta")
rows=[r.split("\t") for r in open("ddg/S669.tsv").read().splitlines()[1:] if len(r.split("\t"))>=5]
model,alphabet=getattr(esm.pretrained,MODEL)(); model.eval(); torch.set_num_threads(2)
bc=alphabet.get_batch_converter(); tok={a:alphabet.get_idx(a) for a in "ACDEFGHIKLMNPQRSTVWY"}
uniq=sorted({r[0] for r in rows if r[0] in seqs and len(seqs[r[0]])<=MAXLEN})
print(f"[{TAG}] {len(uniq)} sequences <= {MAXLEN} aa",flush=True)
logp={}
for i,pid in enumerate(uniq):
    _,_,toks=bc([("x",seqs[pid])])
    with torch.no_grad(): logp[pid]=torch.log_softmax(model(toks)["logits"][0],dim=-1)
    if (i+1)%10==0: print(f"  {i+1}/{len(uniq)}",flush=True)
sc=[];dg=[]
for r in rows:
    pid,wt,pos,mt,ddg=r[0],r[1],int(r[2]),r[3],float(r[4])
    if pid not in logp: continue
    s=seqs[pid]
    if pos<1 or pos>len(s) or s[pos-1]!=wt or wt not in tok or mt not in tok: continue
    sc.append((logp[pid][pos,tok[mt]]-logp[pid][pos,tok[wt]]).item()); dg.append(ddg)
sc=np.array(sc);dg=np.array(dg)
rho,pv=spearmanr(sc,dg); tol=dg>-0.5; dest=dg<-1.0
av=np.concatenate([sc[tol],sc[dest]]); lab=np.concatenate([np.ones(tol.sum()),np.zeros(dest.sum())])
o=np.argsort(av); rk=np.empty(len(av)); rk[o]=np.arange(1,len(av)+1)
auc=(rk[lab==1].sum()-lab.sum()*(lab.sum()+1)/2)/(lab.sum()*(lab==0).sum())
print(f"[{TAG}] wt-marginal {len(sc)} variants: Spearman {rho:+.3f} (p={pv:.1e}) AUC {auc:.3f}",flush=True)
np.savez(f"s669_{TAG}.npz",scores=sc,ddgs=dg,rho=rho,auc=auc); print(f"[{TAG}] DONE",flush=True)
