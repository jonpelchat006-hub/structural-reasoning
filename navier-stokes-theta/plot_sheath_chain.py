"""Standalone figures from completed simulations and the separate orbit check."""
import sys
sys.path.insert(0, 'C:/Users/GamerTech/.codex/tmp/fluid_plot_packages')
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).parent
runs = []
for p in root.glob('sheath_chain_*_results.json'):
    runs += json.loads(p.read_text())
by = {(r['n'],r['dt'],r['mode']): r for r in runs}
modes = ['bare','co_weak','co_strong','counter_weak','axial_weak']
names = ['No outer\ndrive','Same spin\nweak','Same spin\nstrong','Opposite spin\nweak','Axial only\nweak']
fig, axes = plt.subplots(1, 3, figsize=(15,4.9), layout='constrained')
for n, shift, color, marker in [(24,-.15,'#86929d','s'),(32,0,'#287c97','o'),(40,.15,'#b65030','D')]:
    available = [(i,by[(n,.01,m)]) for i,m in enumerate(modes) if (n,.01,m) in by]
    axes[0].scatter([i+shift for i,r in available],
        [100*(r['labels']['matched_gate_pairs'][-1]['width_ratio']-1) for i,r in available],
        label=f'{n} cubed', color=color, marker=marker, s=45)
axes[0].axhline(0,color='#737373',lw=1)
axes[0].set(xticks=range(5),xticklabels=names,ylabel='Exit spread change from entrance (%)',
            title='Gate crossings: narrowing is below zero')
axes[0].tick_params(axis='x',labelsize=8)
axes[0].legend(frameon=False,fontsize=9)
for mode, label, color in [('bare','No outer drive','#596c7d'),('counter_weak','Opposite outer drive','#087f83')]:
    n = max(r['n'] for r in runs if r['mode']==mode and r['dt']==.01)
    r = by[(n,.01,mode)]
    pairs = r['labels']['matched_gate_pairs']
    axes[1].plot([3,3.6,4.2],[pairs[0]['mean_radius_in'],pairs[0]['mean_radius_out'],pairs[1]['mean_radius_out']],
                 marker='o',color=color,lw=2,label=f'{label} ({n} cubed)')
    data = [a for a in r['rows'] if a['t']>=1]
    axes[2].plot([a['t'] for a in data],
                [a['simultaneous_inner']['all_valid']['radial_sd'] for a in data],
                color=color,lw=2,label=label)
axes[1].set(xticks=[3,3.6,4.2],xticklabels=['Entrance','Waist','Exit'],
            ylabel='Mean distance from the local axis',title='The band still moves outward')
axes[1].legend(frameon=False,fontsize=8)
axes[2].set(xlabel='Time since driving began',ylabel='Radial spread of all 144 tags',
            title='Same-time cohort: downstream spreading')
axes[2].legend(frameon=False,fontsize=9)
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(alpha=.15)
fig.suptitle('A surrounding driven layer: local focusing and lasting confinement are different tests',fontsize=14,weight='bold')
fig.supxlabel('Equal total input energy 0.236; dimensionless straight periodic flow. Gate-crossing times differ among tags; same-time cohorts also span different heights.',fontsize=9)
fig.savefig(root/'sheath_chain.png',dpi=170)
fig.savefig(root/'sheath_chain.svg')

orb = json.loads((root/'planet_orbit_check_results.json').read_text())
fig, axes = plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
colors = ['#a5a5a5','#a25931','#087f83','#466ab2','#8b518a']
for r,c in zip(orb['runs'],colors):
    xy=np.array(r['positions'])
    label=f"{r['speed_ratio']:g} x circular speed" if r['gravity'] else 'Gravity off; tangent motion'
    axes[0].plot(xy[:,0],xy[:,1],color=c,label=label,lw=2)
    axes[1].plot(np.array(r['times'])/(2*np.pi),np.linalg.norm(xy,axis=1),color=c,lw=2)
axes[0].scatter([0],[0],color='#384454',s=35)
axes[0].scatter([1],[0],color='#384454',s=15)
axes[0].set(xlabel='x / initial orbit radius',ylabel='y / initial orbit radius',
            aspect='equal',title='Same launch point, different tangential speeds')
axes[0].legend(frameon=False,fontsize=8,loc='upper left')
axes[1].axhline(1,color='#999',ls=':',lw=1)
axes[1].set(xlabel='Time / reference circular period',ylabel='Distance from planet centre / initial radius',
            title='Gravity closes a circle only at the matching speed')
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(alpha=.15)
fig.suptitle('Planet-centred gravity: a separate point-parcel check',fontsize=14,weight='bold')
fig.supxlabel('Ideal point gravity only. No fluid forces or finite planet surface; an inward trajectory could intersect a real planet.',fontsize=9)
fig.savefig(root/'planet_orbit_check.png',dpi=170)
fig.savefig(root/'planet_orbit_check.svg')
print('Saved sheath_chain and planet_orbit_check figures as PNG and SVG.')
