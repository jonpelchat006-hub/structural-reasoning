import json, statistics as st
sigs=json.load(open("sig_all.json"))
learned=json.load(open("arc-learned.json"))
solved=set(t for L in learned["learnings"] for t in L.get("tasks",[]))
def dist(a,b):
    d=0
    for i in range(len(a["light"])): d+=(3 if i==7 else 1)*abs(a["light"][i]-b["light"][i])
    for i in range(len(a["dark"])):  d+=2*abs(a["dark"][i]-b["dark"][i])
    return d
by={s["id"]:s for s in sigs}
unsolved=[s for s in sigs if s["id"] not in solved]

# For each UNSOLVED task: distance to nearest SOLVED task (the anchor it could build from)
print("=== ANCHOR AVAILABILITY: nearest SOLVED neighbour for each unsolved task ===")
near=[]
has_solved_twin=0; has_solved_close=0
for u in unsolved:
    ds=[(dist(u,by[t]), t) for t in solved]
    dmin=min(d for d,_ in ds)
    near.append(dmin)
    if dmin==0: has_solved_twin+=1
    if dmin<=1: has_solved_close+=1
print(f"  unsolved tasks: {len(unsolved)}")
print(f"  with a SOLVED twin (dist 0, exact anchor):   {has_solved_twin}  ({100*has_solved_twin/len(unsolved):.1f}%)")
print(f"  with a SOLVED neighbour within dist<=1:        {has_solved_close}  ({100*has_solved_close/len(unsolved):.1f}%)")
print(f"  median nearest-solved distance: {st.median(near)} | mean {st.mean(near):.2f} | max {max(near)}")

# truly blind: no solved task anywhere close
blind=[d for d in near if d>=3]
print(f"  'going out blind' (no solved task within dist 3): {len(blind)}  ({100*len(blind)/len(unsolved):.1f}%)")

# of the resonant-unsolved (has any twin at all), how many have a SOLVED twin specifically?
def twins(a): return [b for b in sigs if b['id']!=a['id'] and dist(a,b)==0]
res_unsolved=[u for u in unsolved if len(twins(u))>0]
res_with_solved_twin=[u for u in res_unsolved if any(t["id"] in solved for t in twins(u))]
print(f"\n=== the 'work the resonant bucket' target ===")
print(f"  resonant-unsolved (has a twin):              {len(res_unsolved)}")
print(f"  of those, twin set INCLUDES a solved task:   {len(res_with_solved_twin)}  <- direct anchor exists")
print(f"  of those, twins are ALL unsolved:            {len(res_unsolved)-len(res_with_solved_twin)}  <- anchor is a peer, weaker")
