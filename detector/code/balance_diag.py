import json
import numpy as np
from skimage import color, io
import balance_observer as B
rows=json.load(open("seam/index.json"))
print("IS THE LAW EVEN READABLE?  within-image fit of spatial sharpness ~ spectral sigma")
print("(on the UNTOUCHED originals -- if the constraint is real and measurable, R^2 is high)")
print(f"{'image':<20}{'R2':>7}{'sigma spread':>14}{'sigma median':>14}")
r2s=[];sp=[]
for r in rows:
    g=color.rgb2lab(io.imread(f"seam/{r['name']}_orig.jpg")[...,:3].astype(float)/255)[...,0]/100
    h,w=g.shape
    sig=np.full(36,np.nan);alp=np.full(36,np.nan);shp=np.full(36,np.nan)
    for i,sy,sx in B._cells(h,w):
        s,a=B._spectral_sigma(g[sy,sx]); sig[i],alp[i]=s,a; shp[i]=B._spatial_sharp(g[sy,sx])
    k=np.isfinite(sig)&np.isfinite(shp)&np.isfinite(alp)
    if k.sum()<12: continue
    X=np.stack([np.ones(k.sum()),sig[k],alp[k]],1)
    coef,*_=np.linalg.lstsq(X,shp[k],rcond=None)
    pred=X@coef; ss=1-((shp[k]-pred)**2).sum()/(((shp[k]-shp[k].mean())**2).sum()+1e-12)
    r2s.append(ss); sp.append(np.nanstd(sig)/(np.nanmedian(sig)+1e-9))
    print(f"{r['name']:<20}{ss:>7.2f}{np.nanstd(sig):>14.4f}{np.nanmedian(sig):>14.4f}")
print(f"\nmean R2 = {np.mean(r2s):.2f}")
print(f"mean relative spread of sigma across cells = {np.mean(sp):.2f}")
print("\nverdict:", "the constraint IS readable -- my residual is just insensitive" if np.mean(r2s)>0.5
      else "sigma carries little usable variance -- the ESTIMATOR (or JPEG) is the problem, not necessarily the law")
