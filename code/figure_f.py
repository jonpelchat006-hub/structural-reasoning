import os; os.chdir("/home/claude/strain")
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
BS=[1,2,3,5,8,12]
surv=[1.00,0.99,0.97,0.95,0.94,0.93]
chance=[0.56,0.57,0.56,0.56,0.57,0.58]
hidden=[0.00,0.01,0.03,0.05,0.09,0.12]
fig,ax=plt.subplots(figsize=(8.6,5.2))
ax.plot(BS,surv,'-o',color="#2b6cb0",lw=2.4,ms=8,label="C-line survives (coarse cut vs fine cut)")
ax.plot(BS,chance,'--',color="#c53030",lw=1.4,label="chance")
ax.fill_between(BS,chance,surv,color="#2b6cb0",alpha=0.08)
ax.plot(BS,hidden,'-s',color="#dd6b20",lw=2.4,ms=8,label="interior hidden (pixels straddling the seam)")
ax.set_xlabel("pixel size  =  higher floor  →",fontsize=11)
ax.set_ylabel("fraction"); ax.set_ylim(0,1.05); ax.set_xticks(BS)
ax.annotate("the C line stays on the wall,\nblurring only gently (0.99 → 0.93)",xy=(8,0.94),xytext=(5.2,0.72),
            fontsize=9.5,color="#2b6cb0",arrowprops=dict(arrowstyle="->",color="#2b6cb0"))
ax.annotate("the interior goes unreadable\n(0 → 12% mixed pixels)",xy=(12,0.12),xytext=(6.3,0.28),
            fontsize=9.5,color="#dd6b20",arrowprops=dict(arrowstyle="->",color="#dd6b20"))
ax.legend(loc="center right",fontsize=9)
ax.set_title("Reading across floors: the C line survives coarse-graining (blurry), the interior does not",fontsize=11.5,weight='bold')
plt.tight_layout(); plt.savefig("floors_reading.png",dpi=140); print("saved")
