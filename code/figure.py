import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import pickle
R=pickle.load(open("R.pkl","rb"))
poolB=np.load("poolB.npz"); poolC=np.load("poolC.npz")
def corr(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);m=~np.isnan(a)&~np.isnan(b)
    return np.corrcoef(a[m],b[m])[0,1]
def auc(s,l):
    s=np.asarray(s,float);y=np.asarray(l).astype(bool);m=~np.isnan(s);s,y=s[m],y[m]
    o=np.argsort(s);r=np.empty(len(s));r[o]=np.arange(1,len(s)+1)
    return (r[y].sum()-y.sum()*(y.sum()+1)/2)/(y.sum()*(~y).sum())

fig,ax=plt.subplots(1,3,figsize=(15,4.6)); C="#2b6cb0"
# Panel A: deformation measures vs seam (Test A) -- all ~0
labels=['planarity','anisotropy','rama\natypical','kink\nirregular']
vals=[corr(poolB['plan'],poolB['mix']) if 'plan' in poolB else np.nan,
      corr(poolB['aniso'],poolB['mix']),
      corr(poolB['rama'],poolB['mix']),
      corr(poolB['kink'],poolB['mix'])]
a=ax[0]; a.bar(labels,vals,color="#a0aec0",edgecolor='k')
a.axhline(0,color='k',lw=.8); a.set_ylim(-0.3,0.3)
a.set_title("A · does deformation mark the cut?\ncorr(deformation, seam-ness)",fontsize=11)
a.set_ylabel("Pearson r (pooled, n=2310)")
a.text(0.5,-0.24,"all ≈ 0  →  NO",ha='center',color='#c53030',fontsize=11,weight='bold',transform=a.get_xaxis_transform())

# Panel B: B@seam - B@rest per protein (Test B)
prots=['1CLL','1PHP','1GD1','6LDH','8TLN','4AKE','2LZM']; diffs=[1.67,0.02,-0.59,-0.62,-0.26,-0.66,-0.76]
b=ax[1]; cols=['#c53030' if d>0 else C for d in diffs]
b.bar(prots,diffs,color=cols,edgecolor='k'); b.axhline(0,color='k',lw=.8)
b.set_title("B · is the cut line 'weak' (mobile)?\nB-factor at seam − rest",fontsize=11)
b.set_ylabel("Δ B-factor (z)"); b.tick_params(axis='x',labelrotation=45,labelsize=8)
b.text(0.5,0.92,"5/7 negative → seam is RIGID, not floppy",ha='center',color=C,fontsize=9.5,weight='bold',transform=b.transAxes)
b.text(0.02,0.80,"1CLL = calmodulin (the floor):\nexposed hinge, exception",fontsize=7.5,color='#c53030',transform=b.transAxes)

# Panel C: can the pLM rank the cut? (Test C) AUCs
cl=['per-residue\nsurprise\n→seam','per-residue\nsurprise\n→seam2','contact-count\nbridge\n→seam']
cv=[auc(poolC['sup'],poolC['seam']),auc(poolC['sup'],poolC['seam2']),auc(poolC['bridge'],poolC['seam'])]
c=ax[2]; c.bar(cl,cv,color="#a0aec0",edgecolor='k'); c.axhline(0.5,color='#c53030',ls='--',lw=1.2)
c.set_ylim(0,1); c.set_title("C · can a LOCAL pLM read rank the cut?\nAUC (0.5 = chance)",fontsize=11)
c.set_ylabel("AUC"); c.text(0.5,0.56,"chance line",ha='center',color='#c53030',fontsize=8,transform=c.transAxes)
c.text(0.5,0.12,"all ≈ 0.5  →  NO\n(the cut is nonlocal — the wall)",ha='center',color='#c53030',fontsize=10,weight='bold',transform=c.transAxes)
plt.suptitle("Deformed pixels & the next cut — the cut follows the rigid buried waist, not floppy deformed pixels (a correction)",fontsize=12.5,weight='bold')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig("pixel_strain.png",dpi=140)
print("saved pixel_strain.png")
