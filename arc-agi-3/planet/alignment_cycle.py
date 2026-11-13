"""
alignment_cycle.py — Test 1b: the teach / AI-capacity cycle with SEVERAL people on one AI,
a renewable per-round budget, and AI upkeep (its water draw scales with its capacity).

Question (Jonathan): AI capacity is limited by what its people can actually use (the truck needs a
licence). Someone at 0 needs a small AI capacity to learn the basics; the rest goes into the person;
when they learn you get more; keep cycling. Does the AI's capacity end up sized by the sum of what its
people can read, and who gets taught first?

Model (deliberately small; a coordinate choice):
  people i have reading rates r_i  (0 = uneducated blocker)
  the AI has capacity C, split evenly across its people; the link to person i carries min(C/n, r_i)
  people also pass information to each other: min(r_i, r_j) * PEER per pair
  each round: budget B (renewable), minus AI upkeep UPKEEP * C (its water draw), is spent greedily on
     TEACH i   (+1 rate for TEACH_COST water; needs C >= TEACH_MIN — the basics need some AI)
     AI        (+1 capacity for AI_COST water)
     STOP      (keep the reserve)
  greedy = the action with the best information after the round; repeat until budget is spent or STOP.
Run: python alignment_cycle.py
"""
import json

PEER, TEACH_COST, AI_COST, UPKEEP, TEACH_MIN = 0.25, 1.0, 0.5, 0.15, 1.0

def info(C, rates):
    n = len(rates)
    ai_links = sum(min(C / n, r) for r in rates)
    peer = sum(min(rates[i], rates[j]) * PEER for i in range(n) for j in range(i + 1, n))
    return ai_links + peer

def run(rates, C=1.0, rounds=20, budget=8.0, policy="greedy", step=1.0):
    rates = list(rates); traj = []
    for rd in range(1, rounds + 1):
        left = budget - UPKEEP * C
        actions = []
        while left > 0:
            cands = []
            if policy in ("greedy", "all_teach"):
                for i in range(len(rates)):
                    if C >= TEACH_MIN and left >= TEACH_COST * step:
                        nr = list(rates); nr[i] += step
                        cands.append((info(C, nr), f"teach{i}", C, nr, TEACH_COST * step))
            if policy in ("greedy", "all_ai") and left >= AI_COST * step:
                cands.append((info(C + step, rates), "ai", C + step, list(rates), AI_COST * step))
            if policy == "greedy":
                cands.append((info(C, rates), "stop", C, list(rates), 0.0))
            if not cands:
                break
            v, act, C, rates, cost = max(cands, key=lambda t: t[0])
            if act == "stop":
                break
            left -= cost; actions.append(act)
        traj.append(dict(round=rd, C=round(C, 1), rates=[round(r, 1) for r in rates],
                         sum_rates=round(sum(rates), 1), info=round(info(C, rates), 1),
                         actions="".join(a[-1] if a.startswith("teach") else "A" for a in actions) or "-"))
    return traj

if __name__ == "__main__":
    start = [0.0, 0.0, 3.0, 6.0, 12.0]
    out = {p: run(start, policy=p) for p in ["greedy", "all_ai", "all_teach"]}
    # who gets taught first? count teach actions per person in the first 5 greedy rounds
    first = out["greedy"][:5]
    out["greedy_first5_teach_counts"] = {str(i): sum(t["actions"].count(str(i)) for t in first) for i in range(5)}
    # does C track what people can read?  C/n vs each rate at the end
    last = out["greedy"][-1]
    out["greedy_end"] = dict(C_per_person=round(last["C"] / 5, 2), rates=last["rates"],
                             C=last["C"], sum_rates=last["sum_rates"])
    print(json.dumps(out, indent=1))
