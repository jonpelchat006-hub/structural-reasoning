import os; os.chdir("/home/claude/strain")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=np.load("budgetM.npz",allow_pickle=True); rows=d['rows']; prots=[str(x) for x in d['prots']]
L=rows[:,0]; base=rows[:,1]; sr=rows[:,2]; ss=rows[:,3]
x=np.arange(len(prots)); w=0.38
fig,ax=plt.subplots(figsize=(10,5.4))
b1=ax.bar(x-w/2, sr, w, label="SUPPLY — real sequence", color="#2b6cb0", edgecolor='k')
b2=ax.bar(x+w/2, ss, w, label="SUPPLY — scrambled sequence", color="#cbd5e0", edgecolor='k')
ax.plot(x, base, 'r_', ms=18, mew=2.5, label="baseline (random) = the demand line")
for i in range(len(prots)):
    ax.annotate("", xy=(x[i]-w/2, sr[i]), xytext=(x[i]-w/2, base[i]),
                arrowprops=dict(arrowstyle="-", color="#2b6cb0", lw=0))
ax.set_xticks(x); ax.set_xticklabels(prots, rotation=45, fontsize=9)
ax.set_ylabel("long-range contact precision (top-L/5)")
ax.set_title("Sequences supply a foldability budget — real seqs pay for the fold, scrambling goes OVER budget\n"
             "real supply 0.33 (8/8 under budget → folds)   scrambled 0.03 (collapses to the demand line → would fail)",
             fontsize=10.5, weight='bold')
ax.legend(fontsize=9, loc='upper left')
ax.annotate("1CLL = calmodulin (the floor):\nthin budget — barely any long-range\nstructure to specify",
            xy=(0, sr[0]), xytext=(0.4, 0.30), fontsize=8, color="#4a5568",
            arrowprops=dict(arrowstyle="->", color="#4a5568"))
plt.tight_layout(); plt.savefig("sequence_budget.png",dpi=140); print("saved")
