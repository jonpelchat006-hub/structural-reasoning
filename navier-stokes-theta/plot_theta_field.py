"""Figure for THETA_FIELD_RESULTS.md from theta_field_32_0.01_results.json."""
import json,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from theta_field import THRESHOLDS,theta_field
r=json.load(open('theta_field_32_0.01_results.json'))
rows=r['rows'];t=[x['t'] for x in rows]
INK='#333';C1='#2a6f97';C2='#c46a2b';GRID='#e5e5e5'
fig,ax=plt.subplots(1,3,figsize=(13,4));
for a in ax: a.grid(color=GRID,lw=.6);a.spines[['top','right']].set_visible(False)
# 1 global factor
a=ax[0];a.plot(t,[x['theta']['signed']['theta_E'] for x in rows],color=C1,lw=2,label='theta_E(t) = 1+sqrt(ln P/D)')
a.plot([8],[1+np.sqrt(np.log(.04/.035977))],'o',color=C1,ms=7);a.annotate('t=8 from RING_LONG',(8,1.33),textcoords='offset points',xytext=(-70,10),fontsize=8,color=INK)
for k,v in THRESHOLDS.items():
    if v<3: a.axhline(v,color='#999',lw=.8,ls='--');a.text(8.3,v,k.replace('_',' '),va='center',fontsize=8,color=INK)
a.set_xlim(0,9);a.set_ylim(.9,3);a.set_xlabel('time');a.set_title('Global energy factor, still falling at t=3',fontsize=10,loc='left')
# 2 field minimum
a=ax[1]
a.plot(t,[x['theta']['signed']['min'] for x in rows],color=C1,lw=2);a.text(3.05,rows[-1]['theta']['signed']['min'],'signed root',fontsize=8,color=C1,va='center')
a.plot(t,[x['theta']['clamp']['min'] for x in rows],color=C2,lw=2);a.text(3.05,rows[-1]['theta']['clamp']['min'],'clamp',fontsize=8,color=C2,va='center')
for k,v in THRESHOLDS.items():
    if v<3: a.axhline(v,color='#999',lw=.8,ls='--')
a.set_xlim(0,3.6);a.set_ylim(0,3);a.set_xlabel('time');a.set_title('Minimum theta in the domain (at the hot spot)',fontsize=10,loc='left')
# 3 theta vs excess at t=3
a=ax[2];dT=np.linspace(0,1.2,400);thE=rows[-1]['theta']['signed']['theta_E']
a.plot(dT,theta_field(dT,thE,'signed'),color=C1,lw=2);a.text(1.21,theta_field(1.2,thE,'signed'),'signed root',fontsize=8,color=C1,va='center')
a.plot(dT,theta_field(dT,rows[-1]['theta']['clamp']['theta_E'],'clamp'),color=C2,lw=2);a.text(1.21,theta_field(1.2,thE,'clamp'),'clamp',fontsize=8,color=C2,va='center')
for k,v in THRESHOLDS.items():
    if v<2: a.axhline(v,color='#999',lw=.8,ls='--');a.text(0.01,v+.02,k.replace('_',' '),fontsize=8,color=INK)
a.axvline(rows[-1]['heat_max'][0],color='#999',lw=.8);a.text(rows[-1]['heat_max'][0]+.02,2.6,'hottest cell, t=3',fontsize=8,color=INK)
a.set_xlim(0,1.45);a.set_ylim(0,3);a.set_xlabel('temperature excess dT');a.set_title('theta is a monotone function of dT (t=3)',fontsize=10,loc='left')
fig.suptitle('Recovered theta evaluated on the powered thermal ring, 32 cubed, dt=.01, insulated',fontsize=11,x=.01,ha='left')
fig.tight_layout();fig.savefig('theta_field.png',dpi=150);fig.savefig('theta_field.svg');print('ok')
