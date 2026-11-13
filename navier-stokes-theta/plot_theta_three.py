import json,numpy as np
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
R=json.load(open('theta_three_32_0.02_results.json'));r0,r1=R
GRID='#e5e5e5';INK='#333';C0='#7a7a7a';C1='#2a6f97';C2='#c46a2b';C3='#3a8f5a'
fig,ax=plt.subplots(1,3,figsize=(13,4))
for a in ax:a.grid(color=GRID,lw=.6);a.spines[['top','right']].set_visible(False)
t=[x['t'] for x in r0['rows']]
a=ax[0]
a.plot(t,[x['fS'][1] for x in r0['rows']],color=C2,lw=2);a.text(3.05,r0['rows'][-1]['fS'][1],'entropy factor',color=C2,fontsize=8,va='center')
a.plot(t,[x['fT'][1] for x in r0['rows']],color=C3,lw=2);a.text(3.05,r0['rows'][-1]['fT'][1],'temperature factor',color=C3,fontsize=8,va='center')
a.plot(t,[x['fE'][1] for x in r0['rows']],color=C1,lw=2);a.text(3.05,r0['rows'][-1]['fE'][1],'energy factor',color=C1,fontsize=8,va='center')
a.axhline(np.pi,color='#999',lw=.8,ls='--');a.text(0.02,np.pi+.06,'pi',fontsize=8,color=INK)
a.set_xlim(0,3.9);a.set_ylim(0,5);a.set_xlabel('time');a.set_title('Domain maximum of each factor (passive, 32 cubed)',fontsize=10,loc='left')
a=ax[1]
a.plot(t,[min(x['theta_max'],np.pi) for x in r0['rows']],color=C0,lw=2);a.text(3.05,min(r0['rows'][-1]['theta_max'],np.pi),'beta=0',color=C0,fontsize=8,va='center')
a.plot(t,[min(x['theta_max'],np.pi) for x in r1['rows']],color=C1,lw=2);a.text(3.05,min(r1['rows'][-1]['theta_max'],np.pi)-.12,'beta=0.5',color=C1,fontsize=8,va='center')
a.plot(t,[x['vol_theta_at_pi']*1000 for x in r0['rows']],':',color=C0,lw=1.5)
a.plot(t,[x['vol_theta_at_pi']*1000 for x in r1['rows']],':',color=C1,lw=1.5)
a.axhline(np.pi,color='#999',lw=.8,ls='--');a.text(0.02,np.pi+.06,'pi (interface)',fontsize=8,color=INK)
a.text(0.9,.3,'dotted: 1000 x volume fraction at the cap',fontsize=8,color=INK)
a.set_xlim(0,3.9);a.set_ylim(0,3.6);a.set_xlabel('time');a.set_title('Capped theta reaches pi at t = 0.4, then relaxes',fontsize=10,loc='left')
a=ax[2]
a.plot(t,[x['heat_max'] for x in r0['rows']],color=C0,lw=2);a.text(3.05,r0['rows'][-1]['heat_max'],'beta=0',color=C0,fontsize=8,va='center')
a.plot(t,[x['heat_max'] for x in r1['rows']],color=C1,lw=2);a.text(3.05,r1['rows'][-1]['heat_max'],'beta=0.5',color=C1,fontsize=8,va='center')
a.plot(t,[x['energy']*10 for x in r0['rows']],'--',color=C0,lw=1.5);a.plot(t,[x['energy']*10 for x in r1['rows']],'--',color=C1,lw=1.5)
a.text(0.05,1.2,'solid: hottest-cell excess    dashed: 10 x kinetic energy',fontsize=8,color=INK)
a.set_xlim(0,3.9);a.set_ylim(0,1.4);a.set_xlabel('time');a.set_title('Coupling moves energy from motion into the hot spot',fontsize=10,loc='left')
fig.suptitle('Form B with three live factors on the powered thermal ring (insulated)',fontsize=11,x=.01,ha='left')
fig.tight_layout();fig.savefig('theta_three.png',dpi=150);fig.savefig('theta_three.svg');print('ok')
