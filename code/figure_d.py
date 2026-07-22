import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D=np.load("resultD.npz",allow_pickle=True)
prots=[str(x) for x in D['prots']]; x=np.arange(len(prots))
pa,pc,sa,sc=D['prim_ag'],D['prim_ch'],D['sec_ag'],D['sec_ch']
fig,ax=plt.subplots(1,2,figsize=(13,4.8))
w=0.38
a=ax[0]
a.bar(x-w/2,pa,w,label='primary cut',color="#2b6cb0",edgecolor='k')
a.bar(x+w/2,sa,w,label='secondary cut',color="#63b3ed",edgecolor='k')
a.plot(x-w/2,pc,'_',color='k',ms=14,mew=2); a.plot(x+w/2,sc,'_',color='#c53030',ms=14,mew=2,label='chance')
a.set_xticks(x); a.set_xticklabels(prots,rotation=45,fontsize=9)
a.set_ylabel("agreement with true cut"); a.set_ylim(0,1)
a.axhline(0.5,color='gray',ls=':',lw=.8)
a.set_title("PLM contact-web min-cut vs the true cut\n(dashes = per-protein chance baseline)",fontsize=11)
a.legend(fontsize=8,loc='lower right')
b=ax[1]
gp=np.array(pa)-np.array(pc); gs=np.array(sa)-np.array(sc)
b.bar(x-w/2,gp,w,label='primary',color="#2b6cb0",edgecolor='k')
b.bar(x+w/2,gs,w,label='secondary',color="#63b3ed",edgecolor='k')
b.axhline(0,color='k',lw=.8)
b.set_xticks(x); b.set_xticklabels(prots,rotation=45,fontsize=9)
b.set_ylabel("gain over chance"); b.set_title("How far above chance the web ranks each cut",fontsize=11)
b.text(0.5,0.93,f"primary +{gp.mean():.2f}  →  secondary +{gs.mean():.2f}  (8/8 positive)",ha='center',transform=b.transAxes,fontsize=9.5,weight='bold',color="#2b6cb0")
b.legend(fontsize=8)
plt.suptitle("The PLM ranks the NEXT cut the same way it ranks the first — nonlocal web→min-cut, weaker but present at the finer level",fontsize=12,weight='bold')
plt.tight_layout(rect=[0,0,1,0.93]); plt.savefig("plm_recursion.png",dpi=140); print("saved")
