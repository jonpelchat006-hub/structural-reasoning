import os; os.chdir("/home/claude/strain")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
PHI=(1+5**0.5)/2; INVPHI=1/PHI
perlevel=[0.591,0.587,0.555,0.555,0.596,0.577]
lv=np.arange(1,len(perlevel)+1)
prots=['1CLL','3PGK','1PHP','1GD1','6LDH','8TLN','4AKE','2LZM']
pmean=[0.518,0.608,0.546,0.548,0.626,0.544,0.591,0.593]
pnull=[0.697,0.681,0.694,0.695,0.700,0.689,0.719,0.683]
fig,ax=plt.subplots(1,2,figsize=(13,4.8))
a=ax[0]
a.axhline(INVPHI,color="#d69e2e",lw=2,ls='--',label=f"golden section 1/φ = {INVPHI:.3f}")
a.axhline(0.5,color="#718096",lw=1.5,ls=':',label="even split = 0.500")
a.axhspan(0.55,0.60,color="#2b6cb0",alpha=0.10)
a.plot(lv,perlevel,'-o',color="#2b6cb0",lw=2.5,ms=9,label="real cut (per level)")
a.set_xlabel("recursion depth (floor)"); a.set_ylabel("larger-fraction kept per cut")
a.set_ylim(0.45,0.72); a.set_xticks(lv)
a.set_title("Self-similar: flat ≈0.58 across depth\n(you can follow it down) — but it is NOT 1/φ",fontsize=10.5)
a.legend(fontsize=8.5,loc='upper right')
b=ax[1]; x=np.arange(len(prots)); w=0.38
b.bar(x-w/2,pmean,w,label="real protein",color="#2b6cb0",edgecolor='k')
b.bar(x+w/2,pnull,w,label="shape-matched blob null",color="#a0aec0",edgecolor='k')
b.axhline(INVPHI,color="#d69e2e",lw=2,ls='--',label=f"1/φ = {INVPHI:.3f}")
b.axhline(0.5,color="#718096",lw=1.2,ls=':')
b.set_xticks(x); b.set_xticklabels(prots,rotation=45,fontsize=9); b.set_ylim(0,0.8)
b.set_ylabel("mean larger-fraction"); b.legend(fontsize=8.5,loc='lower right')
b.set_title("Real = 0.576 (CI 0.552–0.601, excludes both 1/φ and 0.5)\nblob null is MORE uneven — nothing golden-specific",fontsize=10.5)
plt.suptitle("Following the cut recursion to depth: the recursion is self-similar (real), the spacing is not golden (0.576 ≠ 0.618)",fontsize=11.5,weight='bold')
plt.tight_layout(rect=[0,0,1,0.93]); plt.savefig("golden_depth.png",dpi=140); print("saved")
