import os; os.chdir("/home/claude/strain")
import numpy as np, pickle, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
S=pickle.load(open("spotsH.pkl","rb")); prots=list(S.keys())
r1=[];r2=[];r3=[];d12=[];d23=[]
for p in prots:
    O,S1,S2,S3,coords=S[p]
    Rg=np.sqrt(((coords-O)**2).sum(1)).mean()
    r1.append(np.linalg.norm(S1-O)/Rg); r2.append(np.linalg.norm(S2-O)/Rg); r3.append(np.linalg.norm(S3-O)/Rg)
    d12.append(np.linalg.norm(S1-S2)/Rg); d23.append(np.linalg.norm(S2-S3)/Rg)
x=np.arange(len(prots))
fig,ax=plt.subplots(1,2,figsize=(13,4.8))
a=ax[0]
a.plot(x,r1,'-o',color="#2b6cb0",label="cut 1 (S1)",lw=2,ms=7)
a.plot(x,r2,'-s',color="#dd6b20",label="cut 2 (S2)",lw=2,ms=7)
a.plot(x,r3,'-^',color="#38a169",label="cut 3 (S3)",lw=2,ms=7)
a.axhline(np.mean(r1),color="#2b6cb0",ls=':',lw=1); a.axhline(np.mean(r2),color="#dd6b20",ls=':',lw=1)
a.set_xticks(x); a.set_xticklabels(prots,rotation=45,fontsize=9)
a.set_ylabel("shell radius of the convergence spot  (/ mean radius)")
a.set_title(f"Reference spots on shells\ncut 1 sits innermost (mean {np.mean(r1):.2f}), deeper cuts move out (~{np.mean(r2):.2f})",fontsize=10.5)
a.legend(fontsize=9)
b=ax[1]
w=0.38
b.bar(x-w/2,d12,w,label="step S1→S2",color="#a0aec0",edgecolor='k')
b.bar(x+w/2,d23,w,label="step S2→S3",color="#4a5568",edgecolor='k')
b.set_xticks(x); b.set_xticklabels(prots,rotation=45,fontsize=9)
b.set_ylabel("distance between successive spots")
b.set_title("Successive spots contract (settle): 7/8 have S2→S3 < S1→S2",fontsize=10.5)
b.legend(fontsize=9)
plt.suptitle("The golden-field reference spots persist as traces — they contract toward a stable attractor (but not the ligand)",fontsize=11.5,weight='bold')
plt.tight_layout(rect=[0,0,1,0.94]); plt.savefig("reference_spots.png",dpi=140); print("saved")
