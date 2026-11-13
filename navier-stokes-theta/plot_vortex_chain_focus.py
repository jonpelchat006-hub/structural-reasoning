"""Actual gate diagnostics: transport and temporary radial-width changes."""
import sys
sys.path.insert(0,'C:/Users/GamerTech/.codex/tmp/fluid_plot_packages')
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).parent
coarse=json.loads((root/'vortex_chain_focus_24_0.01_results.json').read_text())
fine=json.loads((root/'vortex_chain_focus_32_0.01_results.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
colors={'single':'#516579','aligned':'#087f83','reversed':'#b86131'}
names={'single':'One stage','aligned':'Aligned pair','reversed':'Upper stage reversed'}
for r in fine:
    axes[0].plot([g['z'] for g in r['labels']['gates']],
        [g['count'] for g in r['labels']['gates']],marker='o',lw=2,
        color=colors[r['mode']],label=names[r['mode']])
axes[0].set(xlabel='Position along the column',ylabel='Labels reaching each plane',
            ylim=(-5,155),yticks=[0,48,96,144],title='Transport by time 6')
axes[0].legend(frameon=False,fontsize=9)
for run,label,color in [(coarse,'24 cubed','#819398'),(fine,'32 cubed','#087f83')]:
    pair=run[1]['labels']['matched_gate_pairs']
    z=[3,3.6,4.2]
    width=[pair[0]['radial_sd_in'],pair[0]['radial_sd_out'],pair[1]['radial_sd_out']]
    radius=[pair[0]['mean_radius_in'],pair[0]['mean_radius_out'],pair[1]['mean_radius_out']]
    axes[1].plot(z,np.array(width)/width[0],marker='o',lw=2,color=color,label=label)
    axes[2].plot(z,radius,marker='o',lw=2,color=color,label=label)
axes[1].axhline(1,color='#9a9a9a',ls=':',lw=1)
axes[1].set(xlabel='Position along the upper stage',ylabel='Radial spread / entrance spread',
            title='Aligned pair: slight entry narrowing')
axes[1].legend(frameon=False,fontsize=9)
axes[2].set(xlabel='Position along the upper stage',ylabel='Mean distance from the column axis',
            title='Band center still moves outward')
axes[2].legend(frameon=False,fontsize=9)
for ax in axes:
    ax.set_xticks([3,3.6,4.2],['Entrance','Waist','Exit'])
    ax.grid(alpha=.15)
    ax.spines[['right','top']].set_visible(False)
fig.suptitle('A second vortex stage carries the flow onward, without lasting compression',fontsize=15,weight='bold')
fig.supxlabel('Dimensionless 3D model. Equal energy supplied. Spread uses the same 144 labels at their first upward crossings, which occur at different times.',fontsize=9)
fig.savefig(root/'vortex_chain_focus.png',dpi=170)
fig.savefig(root/'vortex_chain_focus.svg')
print('Saved vortex_chain_focus.png and .svg')
