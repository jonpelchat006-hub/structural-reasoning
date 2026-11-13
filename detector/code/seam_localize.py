"""Does committee disagreement land ON the edited region?  The first real seam test.

Ground truth is a mask INSIDE one image, so camera, lens, processing, compression,
content and lighting are identical on both sides of the seam. Every confound that
killed the model-free axes cancels exactly.

Control arm: the SAME cells on the UNEDITED original. If the committee flags them
there too, it is reacting to the region, not to the edit.
"""
import json, os, sys, threading
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import committee_experiment as ce
from concurrent.futures import ThreadPoolExecutor

G=6; ROSTER=["claude","gpt","grok"]; CACHE="seam_cache.json"
_c={}; _l=threading.Lock()
PROMPT=f"""You are one observer on a panel assessing photographic authenticity.

Divide the image into a {G}x{G} grid, row-major, rows top to bottom.

For EACH of the {G*G} cells give an authenticity score 0-100:
  100 = certainly an unaltered photograph of a real scene
    0 = certainly synthetic, generated, or digitally altered

Some images are untouched. Judge each cell on what you can see there and how it
sits with the rest of the image.

STRICT JSON only:
{{"cells": [{G*G} integers], "global": <integer 0-100>}}"""

def parse(t):
    import re
    m=re.search(r'\{.*\}',t,re.S)
    if not m: return None
    try: d=json.loads(m.group(0))
    except Exception: return None
    c=d.get("cells")
    if not isinstance(c,list) or len(c)!=G*G: return None
    try: c=[float(x) for x in c]
    except Exception: return None
    return {"cells":c,"global":float(d.get("global",np.mean(c)))}

import base64, urllib.request
def _b64(p):
    with open(p,"rb") as fh: return base64.b64encode(fh.read()).decode()

def _claude(path):
    body={"model":ce.CLAUDE_MODEL,"max_tokens":1500,"temperature":1.0,
          "messages":[{"role":"user","content":[
              {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":_b64(path)}},
              {"type":"text","text":PROMPT}]}]}
    req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=json.dumps(body).encode(),
        headers={"x-api-key":ce.ENV["ANTHROPIC_API_KEY"],"anthropic-version":"2023-06-01","content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as r: d=json.load(r)
    return parse("".join(b.get("text","") for b in d.get("content",[])))

def _oai(path,base,key,model):
    body={"model":model,"max_completion_tokens":2000,"messages":[{"role":"user","content":[
        {"type":"text","text":PROMPT},
        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{_b64(path)}"}}]}]}
    req=urllib.request.Request(base,data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {key}","content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=240) as r: d=json.load(r)
    return parse(d["choices"][0]["message"]["content"])

CALL={"claude":_claude,
      "gpt":lambda p:_oai(p,"https://api.openai.com/v1/chat/completions",ce.ENV["OPENAI_API_KEY"],ce.OPENAI_MODEL),
      "grok":lambda p:_oai(p,"https://api.x.ai/v1/chat/completions",ce.ENV["XAI_API_KEY"],ce.XAI_MODEL)}

def get(path,model):
    k=f"{path}|{model}"
    with _l:
        if k in _c and _c[k] and len(_c[k].get("cells",[]))==G*G: return _c[k]
    out=None
    for _ in range(3):
        try:
            out=CALL[model](path)
            if out: break
        except Exception: pass
    with _l: _c[k]=out
    return out

def coverage(mask):
    h,w=mask.shape; out=np.zeros(G*G)
    for i in range(G):
        for j in range(G):
            sub=mask[i*h//G:(i+1)*h//G, j*w//G:(j+1)*w//G]
            out[i*G+j]=sub.mean()
    return out

def auc(pos,neg):
    pos,neg=np.asarray(pos,float),np.asarray(neg,float)
    if len(pos)<1 or len(neg)<1: return np.nan
    x=np.concatenate([pos,neg]); r=np.argsort(np.argsort(x))+1.0
    return float((r[:len(pos)].sum()-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg)))

def main():
    global _c
    if os.path.exists(CACHE): _c=json.load(open(CACHE)); print(f"resumed {len(_c)}")
    rows=json.load(open("seam/index.json"))
    jobs=[(f"seam/{r['name']}_{k}.jpg",m) for r in rows for k in ("edit","orig") for m in ROSTER]
    done=[0]
    def w(t):
        get(*t)
        with _l:
            done[0]+=1
            if done[0]%15==0: print(f"  {done[0]}/{len(jobs)}",flush=True); json.dump(_c,open(CACHE,"w"))
    with ThreadPoolExecutor(max_workers=6) as ex: list(ex.map(w,jobs))
    json.dump(_c,open(CACHE,"w"))

    res=[]
    for r in rows:
        cov=coverage(np.load(f"seam/{r['name']}_mask.npy"))
        sel=cov>=0.05
        if sel.sum()==0: sel=np.zeros(G*G,bool); sel[int(np.argmax(cov))]=True
        if sel.all(): continue
        row={"name":r["name"],"frac":r["mask_frac"],"n_cells":int(sel.sum())}
        for kind in ("edit","orig"):
            R=[get(f"seam/{r['name']}_{kind}.jpg",m) for m in ROSTER]
            R=[x for x in R if x and len(x["cells"])==G*G]
            if len(R)<2: continue
            C=np.array([x["cells"] for x in R],float)
            sc=C.mean(0); dis=C.std(0)
            row[f"{kind}_score_auc"]=auc(sc[~sel],sc[sel])     # >0.5 = edited cells score LOWER
            row[f"{kind}_disag_auc"]=auc(dis[sel],dis[~sel])   # >0.5 = edited cells disagree MORE
        res.append(row)

    print(f"\n{'='*76}\nDOES THE SEAM MAP LAND ON THE EDIT?  ({len(res)} pairs, {G}x{G} grid, 3 families)\n{'='*76}")
    print(f"{'image':<20}{'edit%':>7}{'cells':>6}   EDITED: score  disagree   ORIGINAL(control): score  disagree")
    for r in sorted(res,key=lambda x:x["frac"]):
        f=lambda k: f"{r[k]:.2f}" if k in r and np.isfinite(r.get(k,np.nan)) else "  - "
        print(f"{r['name']:<20}{100*r['frac']:>6.1f}%{r['n_cells']:>6}          {f('edit_score_auc'):>5} {f('edit_disag_auc'):>9}"
              f"                {f('orig_score_auc'):>5} {f('orig_disag_auc'):>9}")
    for k,lbl in [("edit_score_auc","EDITED  cells score lower"),("edit_disag_auc","EDITED  cells disagree more"),
                  ("orig_score_auc","CONTROL cells score lower"),("orig_disag_auc","CONTROL cells disagree more")]:
        v=[r[k] for r in res if k in r and np.isfinite(r[k])]
        print(f"\n{lbl:<32} mean AUC {np.mean(v):.3f}   above chance on {sum(1 for x in v if x>0.5)}/{len(v)}")
    json.dump(res,open("seam_results.json","w"),indent=2)
    print("\nwrote seam_results.json")
main()
