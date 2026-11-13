"""Figure for THETA_KINETIC_RESULTS.md."""
import json,glob,numpy as np
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
R=[]
for f in sorted(glob.glob('theta_kinetic_32_0.01_*_results.json')): R+=json.load(open(f))
get=lambda kind,beta:[r for r in R if r['kind']==kind and r['beta']==beta][0]
C={0.:'#7a7a7a',.5:'#2a6f97',1.:'#c46a2b'};GRID='#e5e5e5';INK='#333'
fig,ax=plt.subplots(1,3,figsize=(13,4))
for a in ax:a.grid(color=GRID,lw=.6);a.spines[['top','right']].set_visible(False)
a=ax[0]
for kind,ls in (('aligned','-'),('transverse','--')):
    for b in (0.,.5,1.):
        r=get(kind,b);t=[x['t'] for x in r['rows']];O=[x['enstrophy'] for x in r['rows']]
        a.plot(t,O,ls,color=C[b],lw=2)
        if kind=='aligned':a.text(2.03,O[-1],f'beta={b:g}',color=C[b],fontsize=8,va='center')
a.axvspan(0,.3,color='#f0f0f0');a.text(.02,.455,'pulse',fontsize=8,color=INK)
a.set_xlim(0,2.4);a.set_xlabel('time');a.set_ylabel('mean enstrophy');a.set_title('Enstrophy: aligned (solid), transverse held-out (dashed)',fontsize=10,loc='left')
a=ax[1]
for b in (0.,.5,1.):
    r=get('aligned',b);t=[x['t'] for x in r['rows']]
    a.plot(t,[x['theta_max'] for x in r['rows']],color=C[b],lw=2)
    a.plot(t,[x['vol_theta_gt1']*10 for x in r['rows']],':',color=C[b],lw=1.5)
a.axhline(np.pi,color='#999',lw=.8,ls='--');a.text(2.02,np.pi,'pi (interface)',fontsize=8,va='center',color=INK)
a.axhline(1.618,color='#999',lw=.8,ls='--');a.text(2.02,1.618,'phi',fontsize=8,va='center',color=INK)
a.text(1.0,.35,'dotted: 10 x volume fraction with theta > 1',fontsize=8,color=INK)
a.set_xlim(0,2.6);a.set_ylim(0,3.4);a.set_xlabel('time');a.set_title('Max theta never approaches pi (aligned, 32 cubed)',fontsize=10,loc='left')
a=ax[2]
r=np.logspace(-2,6,400);L=np.log(r);th=1+.4*np.sign(L)*np.sqrt(np.abs(.8*L))
a.plot(r,th,color='#2a6f97',lw=2);a.set_xscale('log')
a.axhline(np.pi,color='#999',lw=.8,ls='--');a.text(1.2e-2,np.pi+.05,'pi: needs r_E = e^36 from one factor',fontsize=8,color=INK)
a.axhline(np.pi**(1/3),color='#999',lw=.8,ls='--');a.text(1.2e-2,np.pi**(1/3)+.05,'pi^(1/3): r_E = 5.2 if all three factors share',fontsize=8,color=INK)
a.axvspan(1,150,color='#f0f0f0');a.text(1.3,.25,'range seen\nin the runs',fontsize=8,color=INK)
a.set_xlabel('r_E = enstrophy production / viscous destruction');a.set_ylim(0,3.4);a.set_title('Static factor, Table-1 weights',fontsize=10,loc='left')
fig.suptitle('Form B: kinetic theta coupled to the two-tube pulse flow',fontsize=11,x=.01,ha='left')
fig.tight_layout();fig.savefig('theta_kinetic.png',dpi=150);fig.savefig('theta_kinetic.svg');print('ok')
