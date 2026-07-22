import os; os.chdir("/home/claude/strain")
import numpy as np, torch, esm
from scipy.stats import spearmanr

# ---- load S669 ----
def load_fasta(p):
    d={}; name=None; buf=[]
    for line in open(p):
        line=line.rstrip()
        if line.startswith(">"):
            if name: d[name]="".join(buf)
            name=line[1:].strip(); buf=[]
        else: buf.append(line)
    if name: d[name]="".join(buf)
    return d
seqs=load_fasta("ddg/S669.fasta")
rows=[]
for line in open("ddg/S669.tsv").read().splitlines()[1:]:
    f=line.split("\t")
    if len(f)<5: continue
    pid,wt,pos,mt,ddg=f[0],f[1],int(f[2]),f[3],float(f[4])
    rows.append((pid,wt,pos,mt,ddg))
print(f"loaded {len(rows)} mutations, {len(seqs)} sequences")

# ---- ESM2-8M wt-marginal variant scores ----
model,alphabet=esm.pretrained.esm2_t6_8M_UR50D(); model.eval(); torch.set_num_threads(4)
bc=alphabet.get_batch_converter()
tok={aa:alphabet.get_idx(aa) for aa in "ACDEFGHIKLMNPQRSTVWY"}

# one forward pass per unique sequence -> log-prob matrix
uniq=sorted(set(r[0] for r in rows if r[0] in seqs))
logp={}
for i,pid in enumerate(uniq):
    s=seqs[pid]
    if len(s)>1000: continue
    _,_,toks=bc([("x",s)])
    with torch.no_grad():
        lp=torch.log_softmax(model(toks)["logits"][0],dim=-1)  # [L+2, vocab]
    logp[pid]=lp

scores=[]; ddgs=[]; kept=0; skip_mismatch=0; skip_missing=0
for pid,wt,pos,mt,ddg in rows:
    if pid not in logp: skip_missing+=1; continue
    s=seqs[pid]
    if pos<1 or pos>len(s): skip_mismatch+=1; continue
    if s[pos-1]!=wt: skip_mismatch+=1; continue   # numbering must match
    if wt not in tok or mt not in tok: continue
    lp=logp[pid]
    sc=(lp[pos, tok[mt]]-lp[pos, tok[wt]]).item()  # +1 offset for BOS -> position `pos` (1-indexed) aligns to token pos
    scores.append(sc); ddgs.append(ddg); kept+=1
scores=np.array(scores); ddgs=np.array(ddgs)
print(f"scored {kept} (skipped {skip_mismatch} numbering-mismatch, {skip_missing} missing-seq)")

rho,pval=spearmanr(scores,ddgs)
print(f"\nSpearman(ESM variant score, measured ddG) = {rho:+.3f}  (p={pval:.1e}, n={kept})")
print(f"  ddG range [{ddgs.min():.1f}, {ddgs.max():.1f}]  mean {ddgs.mean():.2f}  (convention: sign below)")
print(f"  most destabilizing rows have ddG≈{np.sort(ddgs)[:3]}, most stabilizing≈{np.sort(ddgs)[-3:]}")

# AUC: does ESM rank tolerated (folders) above strongly destabilizing (failures)?
# orient by data: destabilizing = the tail with LOW stability. Detect via correlation sign of ddg with esm.
# S669 convention: ddG<0 = destabilizing. Define destabilizing = ddg < -1.0, tolerated = ddg > -0.5
dest = ddgs < -1.0
tol  = ddgs > -0.5
def auc(sc,pos,neg):
    s=sc; y=np.zeros(len(sc),bool);
    allv=np.concatenate([s[pos],s[neg]]); lab=np.concatenate([np.ones(pos.sum()),np.zeros(neg.sum())])
    o=np.argsort(allv); rk=np.empty(len(allv)); rk[o]=np.arange(1,len(allv)+1)
    return (rk[lab==1].sum()-lab.sum()*(lab.sum()+1)/2)/(lab.sum()*(lab==0).sum())
a=auc(scores,tol,dest)
print(f"\nAUC(ESM ranks TOLERATED above DESTABILIZING) = {a:.3f}")
print(f"  tolerated (ddG>-0.5): n={tol.sum()}, mean ESM {scores[tol].mean():+.2f}")
print(f"  destabilizing (ddG<-1.0): n={dest.sum()}, mean ESM {scores[dest].mean():+.2f}")
np.savez("s669.npz", scores=scores, ddgs=ddgs)
print("DONE")
