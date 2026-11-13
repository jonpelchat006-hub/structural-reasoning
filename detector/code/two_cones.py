import json, sys
import numpy as np
sys.path.insert(0,'.')
import within_image_observers as W
cache=json.load(open('seam_cache.json'))
rows=json.load(open('seam/index.json'))
ROSTER=["claude","gpt","grok"]; allc=[]; res=[]
for r in rows:
    n=r['name']
    R=[cache.get(f"seam/{n}_edit.jpg|{m}") for m in ROSTER]
    R=[x for x in R if x and len(x.get('cells',[]))==36]
    if len(R)<2: continue
    comm=np.array([x['cells'] for x in R],float).mean(0)
    m=W.measure(f"seam/{n}_edit.jpg")
    cov=W.coverage(np.load(f"seam/{n}_mask.npy")); sel=cov>=0.05
    if sel.sum()==0: sel=np.zeros(36,bool); sel[int(np.argmax(cov))]=True
    if sel.all(): continue
    sd=m['spec_dev']; k=np.isfinite(sd)
    if k.sum()>10: allc.append(float(np.corrcoef(sd[k],comm[k])[0,1]))
    cleared=comm>=np.median(comm)
    for nm,sub in (("cleared",cleared),("flagged",~cleared)):
        a=W.auc(sd[sel&sub], sd[(~sel)&sub])
        if np.isfinite(a): res.append((nm,a))
    print(f"  {n} done",flush=True)
print(f"\nCORRELATION spec_dev vs committee cell score (n={len(allc)} images)")
print(f"  mean |r| = {np.mean(np.abs(allc)):.2f}   mean r = {np.mean(allc):+.2f}")
print(f"  -> {'INDEPENDENT: two different cones' if np.mean(np.abs(allc))<0.4 else 'same thing'}")
print(f"\nspec_dev LOCALISATION, split by what the committee thought:")
for nm in ("cleared","flagged"):
    v=[a for k,a in res if k==nm]
    print(f"  cells the committee {nm:<8} AUC {np.mean(v):.3f}   above chance {sum(1 for x in v if x>0.5)}/{len(v)}")
