"""Common diagnostic thresholds and passive material transport.
No transition, explosion, or extra forcing is switched on at a threshold.
Regions are fixed Gaussian averages sigma=.2 at radii 0,.6,1.2 and z=2,
chosen from the PREVIOUS thermal run. This is exploratory, not held-out.
"""
from pathlib import Path
import json
import numpy as np
from thermal_loop import run

L=2*np.pi
def interp(v,points):
    n=v.shape[1];q=(points%L)*n/L;idx=np.floor(q).astype(int);r=q-idx
    out=np.zeros_like(points)
    for i in (0,1):
        for j in (0,1):
            for k in (0,1):
                w=(r[:,0] if i else 1-r[:,0])*(r[:,1] if j else 1-r[:,1])*(r[:,2] if k else 1-r[:,2])
                out+=w[:,None]*v[:,(idx[:,0]+i)%n,(idx[:,1]+j)%n,(idx[:,2]+k)%n].T
    return out

class Observer:
    def __init__(self):
        self.centers=np.array([[np.pi,np.pi-r,2.] for r in (0,.6,1.2)])
        self.thresholds=(.1,.2,.3,.5)
        self.crossings=[[{str(q):None for q in self.thresholds} for _ in range(3)] for _ in range(3)]
        self.maximum=np.zeros((3,3));self.paths={};self.weights=None
        rng=np.random.default_rng(51);d=rng.normal(size=(256,3));d/=np.linalg.norm(d,axis=1)[:,None]
        self.seed_offsets=d*(.15*rng.random(256)**(1/3))[:,None]
    def __call__(self,t,heat,v,dt,grid):
        if self.weights is None:
            self.weights=[]
            for c in self.centers:
                d2=sum(((a-b+np.pi)%L-np.pi)**2 for a,b in zip(grid,c))
                w=np.exp(-d2/(2*.2**2));self.weights.append(w/w.sum())
        # Advance previously seeded passive parcels, without thermal diffusion.
        for index,track in self.paths.items():
            p=track['points'];mid=p+dt*interp(v,p)/2
            track['points']=p+dt*interp(v,mid)
            dist=np.linalg.norm((track['points']-self.centers[index]+np.pi)%L-np.pi,axis=1)
            track['ever_out']|=dist>.3
        means=np.array([[float((field*w).sum()) for w in self.weights] for field in heat])
        self.maximum=np.maximum(self.maximum,means)
        for cooling in range(3):
            for region in range(3):
                for q in self.thresholds:
                    if means[cooling,region]>=q and self.crossings[cooling][region][str(q)] is None:
                        self.crossings[cooling][region][str(q)]=t
        # Labels are seeded upon first insulated-region crossing of .2.
        for j,c in enumerate(self.centers):
            if j not in self.paths and means[0,j]>=.2:
                self.paths[j]=dict(start=t,initial=c+self.seed_offsets,points=c+self.seed_offsets,
                                   ever_out=np.zeros(256,dtype=bool))
    def results(self):
        paths={}
        for j,track in self.paths.items():
            disp=track['points']-track['initial']
            dist=np.linalg.norm((track['points']-self.centers[j]+np.pi)%L-np.pi,axis=1)
            paths[str(j)]=dict(seeded_at=track['start'],fraction_ever_out=float(track['ever_out'].mean()),
                              fraction_out_at_end=float((dist>.3).mean()),
                              mean_vertical_displacement=float(disp[:,2].mean()))
        return dict(region_centers=self.centers.tolist(),max_region_excess=self.maximum.tolist(),
                    first_crossings=self.crossings,passive_parcels=paths)

if __name__=='__main__':
    out=Path(__file__).with_name('threshold_transport_results.json');results=[]
    for n,dt in ((24,.02),(32,.02),(32,.01)):
        ob=Observer();thermal=run(n,dt,observer=ob)
        result=dict(n=n,dt=dt,total_energy_error=thermal['total_error'],**ob.results())
        results.append(result);out.write_text(json.dumps(results,indent=2)+'\n')
        print('regions:',ob.maximum.tolist(),'parcels:',result['passive_parcels'],flush=True)
