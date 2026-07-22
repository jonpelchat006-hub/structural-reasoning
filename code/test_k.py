import numpy as np
def x_of_k(k): return (1+np.sqrt(1+4*k))/2      # fixed point / larger:smaller ratio
def frac_of_k(k): x=x_of_k(k); return x/(1+x)    # larger-fraction of the section
def k_of_frac(f):
    x=f/(1-f)                                     # larger:smaller ratio
    return x*x - x                                # closure: k = x^2 - x

print("closure unit k  ->  field sqrt(1+4k)  ->  larger-fraction f = x/(1+x)")
for k in [0,0.25,0.5,0.75,1.0]:
    print(f"  k={k:4.2f}   sqrt(1+4k)={np.sqrt(1+4*k):.4f}   x=(1+sqrt)/2={x_of_k(k):.4f}   f={frac_of_k(k):.4f}")
print()
print(f"EVEN split  f=0.5    <->  k = {k_of_frac(0.5):.3f}   (unit 0: whole=part, no self-reference)")
print(f"GOLDEN      f=0.618  <->  k = {k_of_frac(1/((1+5**0.5)/2)):.3f}   (unit 1: one full unit -> sqrt5)")
print(f"MEASURED pooled f=0.576  <->  k = {k_of_frac(0.576):.3f}   (field sqrt(1+4k)={np.sqrt(1+4*k_of_frac(0.576)):.4f})")
print(f"NULL uniform    f=0.572  <->  k = {k_of_frac(0.572):.3f}")
print(f"k=1/2 exactly gives f = {frac_of_k(0.5):.4f}  (compare measured 0.576)")
# per-protein k
pf={'1CLL':0.518,'3PGK':0.608,'1PHP':0.546,'1GD1':0.548,'6LDH':0.626,'8TLN':0.544,'4AKE':0.591,'2LZM':0.593}
print("\nper-protein: mean fraction -> closure unit k")
ks=[]
for p,f in pf.items():
    k=k_of_frac(f); ks.append(k); print(f"  {p}: f={f:.3f}  k={k:.3f}")
print(f"  mean k = {np.mean(ks):.3f}  (range {min(ks):.2f}-{max(ks):.2f})")

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
kk=np.linspace(0,1.4,300); ff=frac_of_k(kk)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.axvspan(0,1,color="#d69e2e",alpha=0.08)
ax.plot(kk,ff,color="#2b6cb0",lw=2.5)
ax.axvline(0,color="#718096",ls=':',lw=1.5); ax.axvline(1,color="#d69e2e",ls='--',lw=2)
ax.scatter([0,1],[0.5,frac_of_k(1)],c=['#718096','#d69e2e'],s=90,zorder=5)
ax.annotate("k=0: even split (0.500)\nno self-reference",xy=(0,0.5),xytext=(0.08,0.53),fontsize=9,color="#4a5568")
ax.annotate("k=1: golden (0.618)\none full unit → √5",xy=(1,frac_of_k(1)),xytext=(0.62,0.588),fontsize=9,color="#b7791f")
km=k_of_frac(0.576)
ax.scatter([km],[0.576],c='#c53030',s=110,zorder=6,marker='D')
ax.annotate(f"measured folds: f=0.576\n→ k≈{km:.2f}  (field √{1+4*km:.2f}≈√3)",xy=(km,0.576),xytext=(0.05,0.60),fontsize=9.5,color="#c53030",
            arrowprops=dict(arrowstyle="->",color="#c53030"))
# per-protein
for p,f in pf.items():
    ax.scatter([k_of_frac(f)],[f],c="#2b6cb0",s=28,alpha=0.6,zorder=4)
ax.set_xlabel("closure unit  k   (the free number in x² = x + k)")
ax.set_ylabel("larger-fraction of the section  f")
ax.set_title("The band [½, φ] IS the closure-unit band k∈[0,1]\nfrom no self-reference (even) to one full unit (golden); folds sit at k≈½",fontsize=11,weight='bold')
ax.set_xlim(-0.03,1.4); ax.set_ylim(0.48,0.66)
plt.tight_layout(); plt.savefig("closure_unit.png",dpi=140); print("\nsaved closure_unit.png")
