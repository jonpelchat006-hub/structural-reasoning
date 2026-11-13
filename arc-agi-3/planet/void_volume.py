"""Local pin intersections and explicit colour-test reserves. No game actions.

Coordinates are supplied hypothesis-space coordinates, NOT inferred 3D matter.
Shared annotations propose a factor; they do not establish a common cause.
"""
from copy import deepcopy
from math import isfinite


def _point(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(
        type(v) not in (int,float) or not isfinite(v) for v in value):
        raise ValueError('three finite coordinates required')
    return tuple(value)


def clip_segment(start,end,lower,upper):
    """Open box intersection in segment parameter t; tangencies are not volume."""
    start,end,lower,upper=map(_point,(start,end,lower,upper))
    if any(lo>=hi for lo,hi in zip(lower,upper)):
        raise ValueError('strictly positive volume required')
    if start==end:
        return None
    enter,leave=0.,1.
    for a,b,lo,hi in zip(start,end,lower,upper):
        delta=b-a
        if delta==0:
            if not lo<a<hi:
                return None
        else:
            near,far=sorted(((lo-a)/delta,(hi-a)/delta))
            enter,leave=max(enter,near),min(leave,far)
            if leave-enter<=1e-12:
                return None
    return (enter,leave) if leave-enter>1e-12 else None


def _factors_on_span(annotations,inside):
    """Keep only factors whose annotated intervals cover the whole inside span."""
    ranges={}
    for rec in annotations:
        a,b=rec['t']
        if any(type(v) not in (int,float) or not isfinite(v) for v in (a,b)) or not 0<=a<b<=1:
            raise ValueError('annotation interval must satisfy 0 <= a < b <= 1')
        factors=rec['factors']
        if not isinstance(factors,dict) or any(not isinstance(k,str) or not k or
            not isinstance(v,str) or not v for k,v in factors.items()):
            raise ValueError('named string-valued factors required')
        lo,hi=max(a,inside[0]),min(b,inside[1])
        if hi<=lo:
            continue
        for factor in factors.items():
            ranges.setdefault(factor,[]).append((lo,hi))
    out=set()
    for factor,intervals in ranges.items():
        reached=inside[0]
        for lo,hi in sorted(intervals):
            if lo>reached+1e-12:
                break
            reached=max(reached,hi)
        if reached>=inside[1]-1e-12:
            out.add(factor)
    # Conflicting labels cannot become a common factor.
    return {p for p in out if sum(q[0]==p[0] for q in out)==1}


def common_factors(pins, *, scope, version, space, action, effect, lower, upper):
    """Group only same-scope/version/space/action/effect pins; preserve provenance.

    Pins must carry stable observation_id values so copied hypotheses from one
    observation cannot inflate the independent-observation count.
    """
    if any(not isinstance(v,str) or not v for v in (scope,version,space,effect)) or type(action) is not int:
        raise ValueError('named experiment context and integer action required')
    clip_segment(lower,upper,lower,upper)  # validate even for an empty pin list
    if len(pins)>256:
        raise ValueError('bounded to 256 pins per volume')
    seen=set(); crossed=[]; rejected=[]; common=None
    for p in pins:
        if not isinstance(p.get('id'),str) or not p['id'] or p['id'] in seen:
            raise ValueError('unique pin IDs required')
        seen.add(p['id'])
        if type(p.get('action')) is not int or any(p.get(k)!=v for k,v in [('scope',scope),('version',version),('space',space),('action',action),('effect',effect)]):
            rejected.append({'id':p['id'],'reason':'incompatible_context'})
            continue
        if not isinstance(p.get('observation_id'),str) or not p['observation_id']:
            rejected.append({'id':p['id'],'reason':'missing_observation_provenance'})
            continue
        inside=clip_segment(p['start'],p['end'],lower,upper)
        if inside is None:
            continue
        annotations=p.get('annotations',[])
        if len(annotations)>64:
            raise ValueError('bounded to 64 annotated spans per pin')
        factors=_factors_on_span(annotations,inside)
        common=factors if common is None else common & factors
        crossed.append({'id':p['id'],'observation_id':p['observation_id'],
                        'inside_t':inside,'factors':sorted(factors)})
    distinct=len({p['observation_id'] for p in crossed})
    factors=sorted(common or set()) if distinct>=2 else []
    return {'scope':scope,'version':version,'space':space,'action':action,'effect':effect,
            'crossed':crossed,'rejected':rejected,'independent_observations':distinct,
            'common_factors':factors,'status':'candidate_common_factor' if factors else 'insufficient_shared_evidence',
            'causal_confirmation':False,'execution_authorized':False}


class ColourReserve:
    """Coverage of a declared finite set, for one fixed experiment context.

    Candidate colours are a caller's hypothesis set, not claimed game states.
    Reachability is True/False/None (unknown). Unreachable is not disproven.
    """
    def __init__(self, scope, question_id, colours):
        colours=tuple(colours)
        if not scope or not question_id or not colours or len(set(colours))!=len(colours) or any(type(c) is not int or not 0<=c<=15 for c in colours):
            raise ValueError('scope, question and unique ARC palette candidates required')
        self.scope,self.question_id=scope,question_id
        self._rows={c:{'fired':0,'silent':0,'reachable':None} for c in colours}
        self._observations={}

    def set_reachable(self,colour,value):
        if type(colour) is not int:
            raise ValueError('integer colour required')
        if value is not None and type(value) is not bool:
            raise ValueError('reachability is true, false or unknown')
        self._rows[colour]['reachable']=value

    def observe(self,observation_id, *, scope, question_id, colour, fired):
        if scope!=self.scope or question_id!=self.question_id or type(fired) is not bool or type(colour) is not int:
            raise ValueError('wrong experiment context or outcome')
        if not isinstance(observation_id,str) or not observation_id:
            raise ValueError('observed trial ID required')
        row=self._rows[colour]
        value=(colour,fired)
        if observation_id in self._observations:
            if self._observations[observation_id]!=value:
                raise ValueError('conflicting duplicate observation')
            return
        self._observations[observation_id]=value
        row['fired' if fired else 'silent']+=1

    def snapshot(self):
        rows=[]
        for colour,row in sorted(self._rows.items()):
            tested=row['fired']+row['silent']>0
            status='tested' if tested else 'untested_unreachable' if row['reachable'] is False else 'untested_reachable' if row['reachable'] is True else 'untested_reachability_unknown'
            rows.append({'colour':colour,**row,'status':status})
        untested=sum(r['status']!='tested' for r in rows)
        return deepcopy({'scope':self.scope,'question_id':self.question_id,'rows':rows,
                         'untested_count':untested,'candidate_count':len(rows),
                         'reserve_fraction':untested/len(rows),
                         'questions':[{'colour':r['colour'],
                            'kind':'find_reachable_case' if r['reachable'] is not True else 'propose_observed_trial',
                            'question':f"For {self.question_id}, can a legitimate observed trial with wall colour {r['colour']} be obtained?",
                            'blocker':r['status'],'execution_ready':False}
                            for r in rows if r['status']!='tested'],
                         'meaning':'coverage gap, not probability, energy, or pi residual',
                         'execution_authorized':False})
