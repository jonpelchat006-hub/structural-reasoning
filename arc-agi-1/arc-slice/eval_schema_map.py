import json,os,collections
D="data-eval"
solved=set(open("verified_eval.txt").read().split())
def load(f):
    j=json.load(open(os.path.join(D,f)))
    return j["train"], j.get("test",[])
def bg(g):
    c=collections.Counter(v for r in g for v in r); return c.most_common(1)[0][0]
def nonbg(g,b): return sum(1 for r in g for v in r if v!=b)
def palette(g): return set(v for r in g for v in r)
def comps(g,b):  # 4-conn non-bg components
    R,C=len(g),len(g[0]); seen=[[False]*C for _ in range(R)]; n=0
    for y in range(R):
        for x in range(C):
            if g[y][x]!=b and not seen[y][x]:
                n+=1; st=[(y,x)]; seen[y][x]=True; col=g[y][x]
                while st:
                    cy,cx=st.pop()
                    for dy,dx in((1,0),(-1,0),(0,1),(0,-1)):
                        ny,nx=cy+dy,cx+dx
                        if 0<=ny<R and 0<=nx<C and not seen[ny][nx] and g[ny][nx]==col:
                            seen[ny][nx]=True; st.append((ny,nx))
    return n
def symdef(g):
    R,C=len(g),len(g[0]); dh=dv=t=0
    for y in range(R):
        for x in range(C):
            t+=1
            if g[y][x]!=g[y][C-1-x]: dh+=1
            if g[y][x]!=g[R-1-y][x]: dv+=1
    return min(dh,dv)/t

def label(train):
    # average signals across train pairs, then decision-tree to ONE formation schema
    sig=collections.Counter()
    for p in train:
        i,o=p["input"],p["output"]; bi=bg(i); bo=bg(o)
        ai=len(i)*len(i[0]); ao=len(o)*len(o[0])
        ratio=ao/ai
        inki=nonbg(i,bi); inko=nonbg(o,bo)
        pi,po=palette(i),palette(o)
        ci,co=comps(i,bi),comps(o,bo)
        sdi,sdo=symdef(i),symdef(o)
        # exact tiling: output dims are an integer multiple of input
        tile = ao>ai and len(o)%len(i)==0 and len(o[0])%len(i[0])==0
        sub  = ao<ai and len(o)<=len(i) and len(o[0])<=len(i[0])
        if tile: sig["TILE/REPEAT"]+=1
        elif ratio>1.25: sig["SCALE-UP"]+=1
        elif sub and co<=ci and inko<inki*1.1: sig["CROP/SELECT (extract a region/object)"]+=1
        elif ratio<0.8: sig["SHRINK/REDUCE"]+=1
        else: # same dims
            if sdo < sdi-0.02 and inko>inki*1.05: sig["SYMMETRY-COMPLETE"]+=1
            elif inko>inki*1.15: sig["INK-ADD / DRAW (generate content)"]+=1
            elif inko<inki*0.85: sig["INK-REMOVE / DENOISE"]+=1
            elif (po-pi) or (pi!=po and len(pi)==len(po)): sig["RECOLOR (by feature/map)"]+=1
            elif ci==co and inko==inki: sig["MOVE / REARRANGE (same content, new positions)"]+=1
            else: sig["OTHER / COMPOUND"]+=1
    return sig.most_common(1)[0][0] if sig else "OTHER / COMPOUND"

files=sorted(f for f in os.listdir(D) if f.endswith(".json"))
unsolved_by=collections.Counter(); solved_by=collections.Counter()
for f in files:
    tid=f[:-5]; train,_=load(f); lab=label(train)
    (solved_by if tid in solved else unsolved_by)[lab]+=1

print("="*64); print("EVAL GEOCHEMISTRY MAP — what formation schemas does eval ask for?"); print("="*64)
print(f"eval: 400 | solved {len(solved)} | unsolved {400-len(solved)}\n")
print(f"{'formation schema (inducer family)':<42}{'unsolved':>9}{'solved':>8}{'solve%':>8}")
print("-"*67)
allk=sorted(set(unsolved_by)|set(solved_by), key=lambda k:-unsolved_by[k])
for k in allk:
    u=unsolved_by[k]; s=solved_by[k]; tot=u+s
    print(f"{k:<42}{u:>9}{s:>8}{(100*s/tot if tot else 0):>7.0f}%")
print("-"*67)
top=allk[:5]; cov=sum(unsolved_by[k] for k in top)
print(f"top-5 schemas cover {cov}/{400-len(solved)} unsolved ({100*cov/(400-len(solved)):.0f}%)")
