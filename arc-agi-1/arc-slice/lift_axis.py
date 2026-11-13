import json,os,collections
D="data-eval"; solved=set(open("verified_eval.txt").read().split())
def bg(g): c=collections.Counter(v for r in g for v in r); return c.most_common(1)[0][0]
def holes(g,b):  # enclosed bg regions (not touching border) = polygon interiors / topology
    R,C=len(g),len(g[0]); seen=[[False]*C for _ in range(R)]; h=0
    for y in range(R):
        for x in range(C):
            if g[y][x]!=b or seen[y][x]: continue
            st=[(y,x)]; seen[y][x]=True; edge=False; 
            while st:
                cy,cx=st.pop()
                if cy in (0,R-1) or cx in (0,C-1): edge=True
                for dy,dx in((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=cy+dy,cx+dx
                    if 0<=ny<R and 0<=nx<C and not seen[ny][nx] and g[ny][nx]==b:
                        seen[ny][nx]=True; st.append((ny,nx))
            if not edge: h+=1
    return h
def has_period(g):
    R,C=len(g),len(g[0])
    for p in range(1,R):
        if R%p==0 and all(g[y]==g[y%p] for y in range(R)) and p<R: return True
    for p in range(1,C):
        if C%p==0 and all(all(g[y][x]==g[y][x%p] for x in range(C)) for y in range(R)) and p<C: return True
    return False
def symdef(g):
    R,C=len(g),len(g[0]); dh=sum(1 for y in range(R) for x in range(C) if g[y][x]!=g[y][C-1-x]); dv=sum(1 for y in range(R) for x in range(C) if g[y][x]!=g[R-1-y][x]); return min(dh,dv)
def sym(g): return symdef(g)==0

ax=collections.Counter(); solv_by=collections.Counter()
N=0
for f in sorted(os.listdir(D)):
    if not f.endswith(".json"): continue
    tid=f[:-5]; tr=json.load(open(os.path.join(D,f)))["train"]; N+=1
    topo=peri=symc=False
    for p in tr:
        i,o=p["input"],p["output"]; bi,bo=bg(i),bg(o)
        if holes(o,bo)!=holes(i,bi): topo=True
        if has_period(o) and not has_period(i): peri=True
        if sym(o) and not sym(i): symc=True
    issolved=tid in solved
    for name,flag in [("TOPOLOGY (holes/enclosure)",topo),("PERIODICITY (torus/tiling)",peri),("SYMMETRY (geometry)",symc)]:
        if flag:
            ax[name]+=1
            if issolved: solv_by[name]+=1

print("="*64); print("WHICH DIMENSION TO LIFT — eval tasks by candidate NEW axis"); print("="*64)
print(f"eval tasks: {N} | solved {len(solved)}\n")
print(f"{'candidate lift-axis':<32}{'tasks':>7}{'solved':>8}{'solve%':>8}")
print("-"*55)
for name,tot in ax.most_common():
    s=solv_by[name]; print(f"{name:<32}{tot:>7}{s:>8}{(100*s/tot if tot else 0):>7.0f}%")
print("\n(low solve% on a high-count axis = a dimension the solver is BLIND to = the lift target)")
