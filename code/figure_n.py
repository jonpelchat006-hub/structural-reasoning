import os; os.chdir("/home/claude/strain")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=np.load("doseN.npz",allow_pickle=True)
fracs=d['fracs']; dose=d['dose']; base=float(d['base']); dis=d['dis']; ben=d['ben']
prots=['1CLL','3PGK','1PHP','1GD1','6LDH','8TLN','4AKE','2LZM']
fig,ax=plt.subplots(1,2,figsize=(13,5))
a=ax[0]
for j,p in enumerate(prots):
    a.plot(np.array(fracs)*100, dose[:,j], '-', lw=1, alpha=0.45, color="#90cdf4")
a.plot(np.array(fracs)*100, dose.mean(1), '-o', lw=2.8, color="#2b6cb0", ms=8, label="mean supply")
a.axhline(base, color="#c53030", ls='--', lw=2, label="demand line (baseline)")
a.axvspan(50,100,color="#c53030",alpha=0.06)
a.set_xlabel("% of sequence scrambled  (budget spent →)"); a.set_ylabel("supply (long-range contact precision)")
a.set_title("Dose-response: supply degrades gracefully;\npast ~50% disruption it crosses into OVER budget",fontsize=10.5)
a.legend(fontsize=9); a.annotate("over budget\n(→ would fail)", xy=(75,0.05), fontsize=9, color="#c53030", ha='center')
b=ax[1]
rng=np.random.default_rng(0)
b.scatter(rng.normal(0,0.06,len(dis)), dis, c="#c53030", s=30, alpha=0.7, label=f"disruptive (bury charge)  mean {dis.mean():+.1f}")
b.scatter(rng.normal(1,0.06,len(ben)), ben, c="#2b6cb0", s=30, alpha=0.7, label=f"benign (surface cons.)  mean {ben.mean():+.1f}")
b.boxplot([dis,ben],positions=[0,1],widths=0.5,showfliers=False)
b.set_xticks([0,1]); b.set_xticklabels(["disruptive\n(should FAIL)","benign\n(should FOLD)"])
b.set_ylabel("pLM variant score (log-odds mut vs wt)")
# AUC
v=np.concatenate([dis,ben]); y=np.concatenate([np.zeros(len(dis)),np.ones(len(ben))])
o=np.argsort(v); rk=np.empty(len(v)); rk[o]=np.arange(1,len(v)+1)
auc=(rk[y==1].sum()-(y==1).sum()*((y==1).sum()+1)/2)/((y==1).sum()*(y==0).sum())
b.set_title(f"Point mutants: the pLM margin ranks folders above failures\nAUC = {auc:.2f}  (n={len(v)}, 4 proteins)",fontsize=10.5)
b.legend(fontsize=8.5, loc='lower right')
plt.suptitle("Calibrating the budget: how much disruption tips a fold over, and does the margin rank folders above failures",fontsize=11.5,weight='bold')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig("budget_calibration.png",dpi=140); print("saved")
