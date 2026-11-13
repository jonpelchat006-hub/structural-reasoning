import json, statistics as st
sigs = json.load(open("sig_all.json"))
learned = json.load(open("arc-learned.json"))
solved = set()
for L in learned["learnings"]:
    for t in L.get("tasks",[]): solved.add(t)
print(f"tasks: {len(sigs)} | solved (from arc-learned): {len(solved)}")

def dist(a,b):
    d=0
    for i in range(len(a["light"])): d += (3 if i==7 else 1)*abs(a["light"][i]-b["light"][i])
    for i in range(len(a["dark"])):  d += 2*abs(a["dark"][i]-b["dark"][i])
    return d

# isolation = distance to nearest OTHER task
iso={}; twins={}
for a in sigs:
    best=10**9; ntwin=0
    for b in sigs:
        if a["id"]==b["id"]: continue
        d=dist(a,b); 
        if d<best: best=d
        if d==0: ntwin+=1
    iso[a["id"]]=best; twins[a["id"]]=ntwin

S=[t for t in iso if t in solved]; U=[t for t in iso if t not in solved]
print(f"\n=== ISOLATION: solved vs unsolved (higher = more unique) ===")
print(f"  mean isolation  solved={st.mean(iso[t] for t in S):.3f}  unsolved={st.mean(iso[t] for t in U):.3f}")
print(f"  median isolation solved={st.median([iso[t] for t in S])}  unsolved={st.median([iso[t] for t in U])}")

# the clean test: does having a signature TWIN (isolation 0) predict solving?
hasTwin=[t for t in iso if twins[t]>0]; noTwin=[t for t in iso if twins[t]==0]
def rate(grp): 
    n=len(grp); s=sum(1 for t in grp if t in solved); return s,n,(s/n if n else 0)
sT=rate(hasTwin); sN=rate(noTwin)
print(f"\n=== TWIN TEST (resonance = has an identical-signature twin) ===")
print(f"  has twin (resonant) : solved {sT[0]}/{sT[1]} = {sT[2]*100:.1f}%")
print(f"  no twin  (unique)   : solved {sN[0]}/{sN[1]} = {sN[2]*100:.1f}%")
lift = sT[2]/sN[2] if sN[2]>0 else float('inf')
print(f"  lift (resonant vs unique): {lift:.2f}x")

# solve-rate by isolation bucket
print(f"\n=== SOLVE RATE BY ISOLATION BUCKET ===")
buckets=[(0,0),(1,2),(3,4),(5,99)]
for lo,hi in buckets:
    g=[t for t in iso if lo<=iso[t]<=hi]
    s,n,r=rate(g)
    print(f"  isolation {lo}-{hi if hi<99 else '+'}: solved {s}/{n} = {r*100:.1f}%")

# routing value: how many unsolved are 'unique' (no twin) -> the tail-solver target
unsolved_unique=[t for t in noTwin if t not in solved]
print(f"\n=== ROUTING VALUE ===")
print(f"  unique (no twin) tasks total: {len(noTwin)}")
print(f"  of those, currently UNSOLVED: {len(unsolved_unique)}  <- the tail-solver target")
print(f"  resonant (has twin) unsolved: {len([t for t in hasTwin if t not in solved])}  <- should be reachable by reuse/knot")
