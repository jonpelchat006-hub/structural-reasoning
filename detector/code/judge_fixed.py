"""Fair test of Jonathan's proposal: observers state REASONS, a judge weighs them."""
import json, os, sys, threading
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import committee_experiment as ce
from concurrent.futures import ThreadPoolExecutor

ROSTER=[("claude",0),("gpt",0),("grok",0)]
CACHE="judge_fixed_cache.json"; _c={}; _l=threading.Lock()

REASON = """Assess this image on a 4x4 grid (100 = certainly a real photograph,
0 = certainly AI-generated).

For the THREE cells you feel most strongly about, state the specific visual evidence
you are relying on -- what you actually see there, not a general impression.

STRICT JSON only:
{"cells":[16 integers], "global":<int>, "evidence":[{"cell":<0-15>,"score":<int>,"seen":"<what you see, one clause>"}]}"""

JUDGE = """Three observers examined this image independently. They did not confer.
Each gave a 4x4 grid reading and cited specific visual evidence for its strongest calls.

{panel}

You can see the image. Weigh the ARGUMENTS, not the numbers: which observer is
pointing at something actually present, and which is asserting an impression? An
observer that names a concrete visible feature outranks one that does not. Where
they conflict on the same cell, go and look at that cell.

STRICT JSON only:
{{"cells":[16 integers], "global":<int>, "carried_by":"<which observer and why, one sentence>"}}"""

def _parse_ext(t):
    import re
    m=re.search(r'\{.*\}',t,re.S)
    if not m: return None
    try: d=json.loads(m.group(0))
    except Exception: return None
    c=d.get("cells")
    if not isinstance(c,list) or len(c)!=16: return None
    try: c=[float(x) for x in c]
    except Exception: return None
    return {"cells":c,"global":float(d.get("global",np.mean(c))),
            "evidence":d.get("evidence",[]),"carried_by":d.get("carried_by","")}

def call(model,path,prompt):
    sp=ce.PROMPT; ce.PROMPT=prompt
    op=ce._parse; ce._parse=_parse_ext
    try: return ce.CALLERS[model](path,0)
    finally: ce.PROMPT=sp; ce._parse=op

def get(path,kind,model,panel=None):
    k=f"{path}|{kind}|{model}"
    with _l:
        if k in _c: return _c[k]
    out=None
    for _ in range(3):
        try:
            out=call(model,path,REASON if kind=="reason" else JUDGE.format(panel=panel))
            if out: break
        except Exception: pass
    with _l: _c[k]=out
    return out

def fmt(rs):
    s=[]
    for i,r in enumerate(rs):
        ev="; ".join(f"cell {e.get('cell')}={e.get('score')}: {e.get('seen','')}"
                     for e in (r.get("evidence") or [])[:3])
        s.append(f"Observer {chr(65+i)}: global={r['global']:.0f} | evidence: {ev or '(none given)'}")
    return "\n".join(s)

def main():
    global _c
    if os.path.exists(CACHE): _c=json.load(open(CACHE)); print(f"resumed {len(_c)}")
    ce._cache=json.load(open("committee_cache.json"))
    imgs=ce.images(); done=[0]
    def w1(p):
        for m,_ in ROSTER: get(p,"reason",m)
        with _l:
            done[0]+=1
            if done[0]%15==0: print(f"  reasons {done[0]}/{len(imgs)}",flush=True); json.dump(_c,open(CACHE,"w"))
    with ThreadPoolExecutor(max_workers=6) as ex: list(ex.map(lambda t:w1(t[0]),imgs))
    json.dump(_c,open(CACHE,"w"))
    done=[0]
    def w2(t):
        p=t[0]; rs=[get(p,"reason",m) for m,_ in ROSTER]
        if all(rs): get(p,"judge","claude",fmt(rs))
        with _l:
            done[0]+=1
            if done[0]%15==0: print(f"  judge {done[0]}/{len(imgs)}",flush=True); json.dump(_c,open(CACHE,"w"))
    with ThreadPoolExecutor(max_workers=6) as ex: list(ex.map(w2,imgs))
    json.dump(_c,open(CACHE,"w"))

    rows={"panel mean (reasoned)":[], "JUDGE weighing arguments":[]}
    for p,label,bucket in imgs:
        rs=[get(p,"reason",m) for m,_ in ROSTER]
        if not all(rs): continue
        C=np.array([r["cells"] for r in rs],float)
        rows["panel mean (reasoned)"].append({"agreement":float(C.mean()),
            "disagreement":float(C.std(0).mean()),"label":label,"bucket":bucket})
        j=get(p,"judge","claude",fmt(rs))
        if j: rows["JUDGE weighing arguments"].append({"agreement":float(np.mean(j["cells"])),
            "disagreement":float(C.std(0).mean()),"label":label,"bucket":bucket})
    print(f"\n{'condition':<34}{'score AUC':>11}{'seam |d|':>10}{'n':>5}")
    for k,v in rows.items():
        if len(v)<20: continue
        a=ce.stratified(v,"agreement")[0]; s=ce.stratified(v,"disagreement")[0]
        print(f"{k:<34}{a:>11.3f}{abs(s-0.5):>10.3f}{len(v):>5}")
    json.dump(_c,open(CACHE,"w"))

main()
