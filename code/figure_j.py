import os; os.chdir("/home/claude/strain")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=np.load("bandJ.npz"); real=d['real']; null=d['null']
PHI=(1+5**0.5)/2; INVPHI=1/PHI
fig,ax=plt.subplots(figsize=(9,5))
bins=np.linspace(0.5,0.9,25)
ax.hist(null,bins=bins,density=True,color="#a0aec0",alpha=0.65,label=f"uniform-density blob null (n={len(null)})",edgecolor='white')
ax.hist(real,bins=bins,density=True,histtype='step',color="#2b6cb0",lw=2.5,label=f"real protein cuts (n={len(real)})")
ax.axvline(0.5,color="#718096",ls=':',lw=1.8); ax.axvline(INVPHI,color="#d69e2e",ls='--',lw=2.2)
ax.text(0.502,ax.get_ylim()[1]*0.92,"even\n0.5",fontsize=9,color="#718096")
ax.text(INVPHI+0.004,ax.get_ylim()[1]*0.92,"golden\n1/φ=0.618",fontsize=9,color="#b7791f")
ax.axvspan(0.5,INVPHI,color="#d69e2e",alpha=0.06)
ax.set_xlabel("larger-fraction kept per cut"); ax.set_ylabel("density")
ax.set_title("The cut ratio DOES live in the [0.5, φ] band (74%) — but a fair uniform null does too (82%)\nAUC real-vs-null = 0.514: the band is generic to bisecting compact shapes, not golden-specific",fontsize=10.5)
ax.legend(fontsize=9.5)
plt.tight_layout(); plt.savefig("golden_band.png",dpi=140); print("saved")
