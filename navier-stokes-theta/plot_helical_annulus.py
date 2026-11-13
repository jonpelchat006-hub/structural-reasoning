"""Plot actual computed paths and diagnostics; no invented helical trajectories."""
import sys
sys.path.insert(0,'C:/Users/GamerTech/.codex/tmp/fluid_plot_packages')
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).parent
runs=json.loads((root/'helical_annulus_32_0.01_1_4_4_results.json').read_text())
colors=['#465b71','#007f86','#8b4ab8','#dc7629','#83964a']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
    'axes.spines.right':False,'axes.labelcolor':'#243347','text.color':'#243347'})
fig=plt.figure(figsize=(15,5.4),layout='constrained')
ax=fig.add_subplot(131,projection='3d')
run=runs[1]
paths=np.array([r['positions'] for r in run['sample_paths']])
for j,label,color in [(0,'Central seed','#465b71'),(4,'Annular seed','#007f86'),(8,'Outer seed','#dc7629')]:
    p=paths[:,j,:]
    invalid=np.where(np.any((p<0)|(p>=2*np.pi),axis=1))[0]
    if invalid.size:
        p=p[:invalid[0]]
    q=p-np.pi
    ax.plot(*q.T,color=color,lw=2.3,label=label)
    ax.scatter(*q[0],color=color,s=22)
    if len(q)>2:
        v=q[-1]-q[-3]
        ax.quiver(*q[-3],*v,color=color,arrow_length_ratio=.7,linewidth=1.8)
ax.plot([0,0],[0,0],[-2.8,2.8],color='#aeb9c7',ls=':',lw=1)
angle=np.linspace(0,2*np.pi,150)
ax.plot(1.05*np.cos(angle),1.05*np.sin(angle),np.full_like(angle,-.4),
        color='#aeb9c7',ls=':',lw=1,alpha=.6)
ax.set(xlabel='x relative to axis',ylabel='y relative to axis',zlabel='height relative to drive',
       title='Computed parcel paths: 25% swirl shape',
       xlim=(-2.2,2.2),ylim=(-2.2,2.2),zlim=(-3.2,2.2),
       xticks=[-2,0,2],yticks=[-2,0,2])
ax.view_init(elev=23,azim=-67)
ax.set_box_aspect((1,1,1.4))
ax.legend(loc='upper left',fontsize=8,frameon=False)

ax=fig.add_subplot(132)
for j in (0,1,2,3):
    p=runs[j]['radial_profile']
    ax.plot([x['radius'] for x in p],[x['mean_axial'] for x in p],color=colors[j],lw=2,
            marker='o',ms=3,label=f"{runs[j]['swirl_fraction']:.0%} swirl shape")
ax.axhline(0,color='#768599',lw=.8)
ax.axvspan(.75,1.35,color='#007f86',alpha=.07)
ax.set(xlabel='Radius from column axis',ylabel='Mean vertical velocity',title='At the drive plane, time = 4')
ax.text(.02,.02,'Below zero = downward return',transform=ax.transAxes,fontsize=9)
ax.legend(fontsize=8,frameon=False)
ax.grid(alpha=.15)

ax=fig.add_subplot(133)
for j in (0,1,2,3,4):
    r=runs[j]
    ax.plot([x['t'] for x in r['rows']],[x['max_speed'] for x in r['rows']],color=colors[j],lw=2,
        label=f"{r['swirl_fraction']:.0%} swirl shape")
ax.set(xlabel='Time',ylabel='Maximum local total speed',title='Equal energy supplied in every run')
ax.legend(fontsize=8,frameon=False)
ax.grid(alpha=.15)
fig.suptitle('Annular rise with swirl: finite speeds and changing return paths',fontsize=16,weight='bold')
fig.supxlabel('Dimensionless 3D periodic model; viscosity 0.03. Paths stop before a periodic-boundary crossing. No physical tube or magnetic plate.',fontsize=10)
fig.savefig(root/'helical_annulus_results.png',dpi=170)
fig.savefig(root/'helical_annulus_results.svg')
print('Saved helical_annulus_results.png and .svg')
