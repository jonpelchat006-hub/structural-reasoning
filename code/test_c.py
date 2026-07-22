import numpy as np, pickle, torch, esm
R=pickle.load(open("R.pkl","rb")); PROTEINS=list(R.keys())
poolB=np.load("poolB.npz")
t2o={'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G','HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S','THR':'T','TRP':'W','TYR':'Y','VAL':'V'}
model,alphabet=esm.pretrained.esm2_t6_8M_UR50D(); model.eval(); torch.set_num_threads(4)
bc=alphabet.get_batch_converter()
def z(x):
    x=np.asarray(x,float);m=~np.isnan(x);o=np.full(len(x),np.nan);s=x[m].std()
    if s>0:o[m]=(x[m]-x[m].mean())/s
    return o
def corr(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);m=~np.isnan(a)&~np.isnan(b)
    if m.sum()<5 or a[m].std()==0 or b[m].std()==0:return np.nan
    return np.corrcoef(a[m],b[m])[0,1]
def auc(s,l):
    s=np.asarray(s,float);y=np.asarray(l).astype(bool);m=~np.isnan(s);s,y=s[m],y[m]
    if y.sum()==0 or y.sum()==len(y):return np.nan
    o=np.argsort(s);r=np.empty(len(s));r[o]=np.arange(1,len(s)+1)
    return (r[y].sum()-y.sum()*(y.sum()+1)/2)/(y.sum()*(~y).sum())
def run(seq):
    _,_,toks=bc([("x",seq)])
    with torch.no_grad():
        out=model(toks); logits=out["logits"]; c=model.predict_contacts(toks)[0].numpy()
    lp=torch.log_softmax(logits,dim=-1)[0]
    L=len(seq); sup=np.array([-lp[i+1,toks[0,i+1]].item() for i in range(L)])
    ii,jj=np.meshgrid(np.arange(L),np.arange(L),indexing='ij'); lm=np.abs(ii-jj)>12
    br=np.array([c[i][lm[i]].sum() for i in range(L)])
    return sup,br
segs={};st=0
for p in PROTEINS: L=len(R[p]['coords']);segs[p]=(st,st+L);st+=L
pool={k:[] for k in ['sup','bridge','mix','seam','seam2','B','rama','dens']}
lines=[f"{'pdb':6}{'L':>5}{'AUC sup->seam':>14}{'AUC brdg->seam':>15}{'AUC brdg->seam2':>16}{'r(sup,rama)':>12}{'r(sup,-dens)':>13}"]
for p in PROTEINS:
    d=R[p]; seq="".join(t2o.get(r,'X') for r in d['res'])
    sup,br=run(seq); s,e=segs[p]
    seam=poolB['seam'][s:e];seam2=poolB['seam2'][s:e];B=poolB['B'][s:e];rama=poolB['rama'][s:e];dens=poolB['dens'][s:e];mix=poolB['mix'][s:e]
    lines.append(f"{p:6}{len(seq):>5}{auc(sup,seam):>14.3f}{auc(br,seam):>15.3f}{auc(br,seam2):>16.3f}{corr(sup,rama):>12.3f}{corr(sup,-dens):>13.3f}")
    for k,v in [('sup',z(sup)),('bridge',z(br)),('mix',mix),('seam',seam),('seam2',seam2),('B',B),('rama',rama),('dens',dens)]:
        pool[k].append(v)
for k in pool: pool[k]=np.concatenate(pool[k])
np.savez("poolC.npz",**pool)
lines.append(f"\n== POOLED n={len(pool['sup'])} ==")
lines.append("PER-RESIDUE SURPRISE (local pLM route):")
lines.append(f"  AUC surprise -> primary seam   = {auc(pool['sup'],pool['seam']):.3f}")
lines.append(f"  AUC surprise -> secondary seam = {auc(pool['sup'],pool['seam2']):.3f}")
lines.append(f"  corr(surprise, rama-atypical)  = {corr(pool['sup'],pool['rama']):+.3f}")
lines.append(f"  corr(surprise, low density)    = {corr(pool['sup'],-pool['dens']):+.3f}")
lines.append(f"  corr(surprise, B-factor)       = {corr(pool['sup'],pool['B']):+.3f}")
lines.append("CONTACT-WEB BRIDGE (pairwise pLM route):")
lines.append(f"  AUC bridge -> primary seam     = {auc(pool['bridge'],pool['seam']):.3f}")
lines.append(f"  AUC bridge -> secondary seam   = {auc(pool['bridge'],pool['seam2']):.3f}")
lines.append(f"  corr(bridge, mixedness)        = {corr(pool['bridge'],pool['mix']):+.3f}")
lines.append(f"  corr(bridge, low density)      = {corr(pool['bridge'],-pool['dens']):+.3f}")
open("resultC.txt","w").write("\n".join(lines)); print("\n".join(lines))
