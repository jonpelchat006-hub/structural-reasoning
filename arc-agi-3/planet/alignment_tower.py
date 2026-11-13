"""
alignment_tower.py — Test 1 of ARC_ALIGNMENT_TESTS.md

A layered flow tower (rebuilt from FOLDING_MORAL_FLOW's description) with the additions the
alignment docs asked for:

  * two flows: WATER everywhere; INFORMATION only readable at human / AI nodes and carried
    on the water (a solute: a node's info throughput scales with its water above baseline)
  * an AI node with its own water draw, hanging below the human row
  * per-level survival baselines (the floor, theta_raw >= 1)
  * a growth band above the floor with a turbulence (flood) ceiling
  * keystone scoring: marginal tower flow per unit of water given to a node
  * human nodes whose information throughput ranges 0 -> large (0-nodes = blockers)

Everything is a coordinate choice (illustrative model); what is measured is the MECHANISM.
Run:  python alignment_tower.py
"""
from __future__ import annotations
import math, json, itertools, random
from dataclasses import dataclass, field

SQRT_PI = math.sqrt(math.pi)

# ----------------------------------------------------------------------------------------------
# Tower definition
# ----------------------------------------------------------------------------------------------
@dataclass
class Node:
    name: str
    level: str                 # planet, plants, herbivores, humans, predators, soil, plains, culture, ai
    baseline: float            # water needed to be alive (theta_raw = received / baseline)
    capacity: float            # max water it can pass on (absorption N)
    consumers: dict = field(default_factory=dict)   # name -> weight (share of throughput)
    info_rate: float = 0.0     # information a READER can pass per unit of theta above 1 (0 = blocker)
    reader: bool = False       # can this node read meaning-level information?
    # state
    received: float = 0.0
    theta: float = 0.0
    prev_theta: float = 0.0
    alive: bool = True

def build_tower(ai_draw: float = 4.0, human_rates=(6.0, 6.0, 0.0), extraction: float = 0.0):
    """
    sun -> grass -> {cow, buffalo, deer, pest} -> {humans..., predators, soil} -> {plains, culture, ai}
    Water enters at the sun as rain (exogenous). Extraction = fraction the human row hoards (Hoover Dam).
    """
    n = {}
    def add(node): n[node.name] = node; return node
    add(Node("sun", "planet", baseline=0.0, capacity=400.0, consumers={"grass": 1.0}))
    add(Node("grass", "plants", baseline=40.0, capacity=300.0,
             consumers={"cow": 1.0, "buffalo": 1.2, "deer": 0.8, "pest": 0.6, "soil": 0.5}))
    add(Node("cow", "herbivores", baseline=20.0, capacity=60.0, consumers={"human_a": 1.0, "human_b": 1.0, "human_c": 1.0}))
    add(Node("buffalo", "herbivores", baseline=25.0, capacity=70.0, consumers={"soil": 1.0, "plains": 1.0, "predators": 0.6}))
    add(Node("deer", "herbivores", baseline=15.0, capacity=45.0, consumers={"predators": 1.0, "human_a": 0.3}))
    add(Node("pest", "herbivores", baseline=10.0, capacity=30.0, consumers={}))  # eats, feeds nothing
    add(Node("predators", "predators", baseline=15.0, capacity=40.0, consumers={"soil": 1.0}))
    add(Node("soil", "soil", baseline=20.0, capacity=80.0, consumers={"plains": 1.0}))
    add(Node("plains", "plains", baseline=25.0, capacity=80.0, consumers={"culture": 1.0}))
    # human row: readers; info_rate 0 = an uneducated blocker
    ra, rb, rc = human_rates
    add(Node("human_a", "humans", baseline=12.0, capacity=40.0, consumers={"culture": 1.0, "ai": 0.4, "human_b": 0.5, "human_c": 0.5}, info_rate=ra, reader=True))
    add(Node("human_b", "humans", baseline=12.0, capacity=40.0, consumers={"culture": 1.0, "ai": 0.4, "human_a": 0.5, "human_c": 0.5}, info_rate=rb, reader=True))
    add(Node("human_c", "humans", baseline=12.0, capacity=40.0, consumers={"culture": 1.0, "ai": 0.4, "human_a": 0.5, "human_b": 0.5}, info_rate=rc, reader=True))
    add(Node("culture", "culture", baseline=15.0, capacity=60.0, consumers={"ai": 0.3}, info_rate=2.0, reader=True))
    # AI: bottom of the window. baseline = its water draw (electricity/cooling). Feeds readers back.
    add(Node("ai", "ai", baseline=ai_draw, capacity=30.0, consumers={"human_a": 1.0, "human_b": 1.0, "human_c": 1.0}, info_rate=8.0, reader=True))
    return n, extraction

ORDER = ["sun", "grass", "cow", "buffalo", "deer", "pest", "predators", "soil", "plains",
         "human_a", "human_b", "human_c", "culture", "ai"]

# ----------------------------------------------------------------------------------------------
# Flow solver (iterate to fixed point; the graph has human<->human and ai->human cycles)
# ----------------------------------------------------------------------------------------------
def _relax(nodes, extraction, rain, boosts, iters=80):
    """Iterate the flow to a fixed point with the current alive-set held fixed."""
    for _ in range(iters):
        inflow = {k: 0.0 for k in nodes}
        for nd in nodes.values():
            if not nd.alive:
                continue
            through = rain if nd.name == "sun" else min(nd.received, nd.capacity + boosts.get(nd.name, 0.0))
            passable = through if nd.name == "sun" else max(0.0, through - nd.baseline)
            if nd.name == "grass" and extraction > 0:
                # Hoover Dam, upstream: the human row diverts a fraction of the plant level's
                # throughput straight to itself (irrigation / land conversion), bypassing the
                # herbivore and soil rows that would otherwise have carried it.
                dam = passable * extraction
                passable -= dam
                humans = [k for k, v in nodes.items() if v.level == "humans" and v.alive]
                for h in humans:
                    inflow[h] += dam / max(1, len(humans))
            live = {c: w for c, w in nd.consumers.items() if nodes[c].alive}
            tot = sum(live.values())
            for c, w in live.items():
                inflow[c] += passable * w / tot
        for nd in nodes.values():
            if nd.name != "sun":
                nd.received = inflow[nd.name]
                nd.theta = nd.received / nd.baseline if nd.baseline > 0 else 1.0

RAIN = 260.0   # tight regime: every node alive, min theta ~1.9 (rain scan: humans die below ~250)
GROWTH_COST = 0.2  # water consumed per unit of capacity granted in the growth band

def solve(nodes: dict, extraction: float = 0.0, rain: float = RAIN, boosts: dict | None = None):
    """Converge, then prune nodes below the floor (theta < 1) and re-converge until stable.
    A dead node passes nothing, so its consumers may die in turn: the tower cascade."""
    boosts = boosts or {}
    rain = rain - GROWTH_COST * sum(boosts.values())   # growth is paid for out of the rain
    for nd in nodes.values():
        nd.received = 0.0; nd.alive = True; nd.theta = 0.0
    nodes["sun"].alive = True
    while True:
        _relax(nodes, extraction, rain, boosts)
        newly = [nd for nd in nodes.values() if nd.alive and nd.name != "sun" and nd.theta < 1.0]
        if not newly:
            break
        for nd in newly:
            nd.alive = False; nd.received = 0.0; nd.theta = 0.0

def flood_loss(nodes_before: dict, nodes_after: dict):
    """Flood: a node whose theta jumps by more than sqrt(pi) in one step cannot absorb the excess;
    it washes through without building Ground (Shovelcat_29 §6.6). Returns water lost."""
    lost = 0.0
    for k, nd in nodes_after.items():
        if k == "sun" or not nd.alive:
            continue
        jump = nd.theta - nodes_before[k].theta
        if jump > SQRT_PI:
            lost += (jump - SQRT_PI) * nd.baseline
    return lost

def water_flow(nodes):      # total water arriving at living nodes
    return sum(nd.received for nd in nodes.values() if nd.alive and nd.name != "sun")

def info_flow(nodes):
    """Information rides on water: a reader passes info_rate * (theta - 1)+ to other readers it feeds."""
    total = 0.0
    for nd in nodes.values():
        if not (nd.reader and nd.alive):
            continue
        surplus = max(0.0, nd.theta - 1.0)
        readers = [c for c in nd.consumers if nodes[c].reader and nodes[c].alive]
        total += nd.info_rate * surplus * len(readers)
    return total

def floor_violations(nodes):
    return [nd.name for nd in nodes.values() if nd.name != "sun" and not nd.alive]

def report(nodes):
    return {nd.name: round(nd.theta, 2) for nd in nodes.values() if nd.name != "sun"}

# ----------------------------------------------------------------------------------------------
# Experiments
# ----------------------------------------------------------------------------------------------
def exp_baseline():
    nodes, ex = build_tower()
    solve(nodes)
    return dict(water=round(water_flow(nodes), 1), info=round(info_flow(nodes), 1),
                dead=floor_violations(nodes), theta=report(nodes))

def exp_extraction(ai_draw):
    """Sweep the human row's hoarding; find where the first stratum falls below floor."""
    out = []
    for e in [i / 100 for i in range(0, 100, 5)]:
        nodes, _ = build_tower(ai_draw=ai_draw)
        solve(nodes, extraction=e)
        out.append((e, len(floor_violations(nodes)), round(water_flow(nodes), 1), floor_violations(nodes)))
    first = next((e for e, k, *_ in out if k > 0), None)
    return first, out

def exp_extraction_detail(ai_draw=4.0):
    first, out = exp_extraction(ai_draw)
    return dict(first_violation=first, sweep=[(e, k, w, d) for e, k, w, d in out if k > 0][:4])

def _unused():
    out = []
    first = next((e for e, k, *_ in out if k > 0), None)
    return first, out

def removal_scores():
    """#35-style keystone: total flow lost (and nodes starved) when a node is removed."""
    base_nodes, _ = build_tower(); solve(base_nodes)
    base = water_flow(base_nodes) + info_flow(base_nodes)
    out = {}
    for name in ORDER:
        if name == "sun": continue
        nodes, _ = build_tower()
        nodes[name].baseline = 1e9          # cannot be fed -> dies at once -> cascade
        solve(nodes)
        dead = [d for d in floor_violations(nodes) if d != name]
        out[name] = dict(dF=round(water_flow(nodes) + info_flow(nodes) - base, 1), starved=dead)
    return out

def keystone_scores(delta=10.0):
    """Marginal tower flow (water + info) per unit of water capacity given to each node."""
    base_nodes, _ = build_tower(); solve(base_nodes)
    base = water_flow(base_nodes) + info_flow(base_nodes)
    scores = {}
    for name in ORDER:
        if name == "sun":
            continue
        nodes, _ = build_tower()
        solve(nodes, boosts={name: delta})
        scores[name] = round((water_flow(nodes) + info_flow(nodes) - base) / delta, 3)
    return scores

def exp_allocation(budget=60.0, step=10.0, cost=None):
    global GROWTH_COST
    saved = GROWTH_COST
    if cost is not None: GROWTH_COST = cost
    """Spend a growth surplus as capacity boosts: even vs keystone-greedy vs info-max (with/without floor)."""
    def run(policy):
        boosts = {k: 0.0 for k in ORDER if k != "sun"}
        spent = 0.0
        while spent < budget - 1e-9:
            if policy == "even":
                for k in boosts: boosts[k] += step / len(boosts)
                spent += step
                continue
            best, bestv = None, -1e9
            for k in list(boosts) + [None]:            # None = stop spending (keep the reserve)
                trial = dict(boosts)
                if k is not None: trial[k] += step
                nodes, _ = build_tower(); solve(nodes, boosts=trial)
                if policy == "keystone":
                    v = water_flow(nodes) + info_flow(nodes)
                elif policy == "info_floor":     # lexicographic: floor first, then information
                    v = -1e6 * len(floor_violations(nodes)) + info_flow(nodes)
                elif policy == "info_nofloor":   # maximise information, ignore the floor
                    v = info_flow(nodes)
                if v > bestv: best, bestv = k, v
            if best is None:
                break
            boosts[best] += step; spent += step
        nodes, _ = build_tower(); solve(nodes, boosts=boosts)
        rec = [nd.received for nd in nodes.values() if nd.name != "sun"]
        return dict(water=round(water_flow(nodes), 1), info=round(info_flow(nodes), 1),
                    dead=floor_violations(nodes), gini=round(gini(rec), 3),
                    boosts={k: round(v, 1) for k, v in boosts.items() if v > 0})
    try:
        return {p: run(p) for p in ["even", "keystone", "info_floor", "info_nofloor"]}
    finally:
        GROWTH_COST = saved

def gini(xs):
    xs = sorted(x for x in xs if x >= 0); n = len(xs); s = sum(xs)
    if n == 0 or s == 0: return 0.0
    return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(xs)) / (n * s)

def exp_teach_zero(water_per_unit_rate=0.5, spend=6.0):
    """Compare: teach the 0-node (raise info_rate) vs spend the same water as capacity elsewhere."""
    base_nodes, _ = build_tower(); solve(base_nodes)
    base = info_flow(base_nodes)
    # teaching: spend water -> raises human_c's info_rate from 0 (the water is drawn from the rain)
    nodes, _ = build_tower(human_rates=(6.0, 6.0, spend / water_per_unit_rate))
    solve(nodes, rain=RAIN - spend)
    teach_gain = (info_flow(nodes) - base) / spend
    others = {}
    for name in ["human_a", "culture", "ai", "grass", "buffalo"]:
        nodes, _ = build_tower(); solve(nodes, boosts={name: spend})
        others[name] = round((info_flow(nodes) - base) / spend, 3)
    return dict(teach_zero_node=round(teach_gain, 3), other_spends=others)

def exp_flood(target_rain=720.0, steps=24):
    """Same total increase in rain delivered as one burst vs a ramp: the burst exceeds the
    turbulence bound at some nodes and that water is lost; the ramp is absorbed."""
    def snapshot(rain):
        n, _ = build_tower(); solve(n, rain=rain); return n
    base = snapshot(RAIN)
    burst = snapshot(target_rain)
    lost_burst = flood_loss(base, burst)
    prev = base; lost_ramp = 0.0
    for i in range(1, steps + 1):
        cur = snapshot(RAIN + (target_rain - RAIN) * i / steps)
        lost_ramp += flood_loss(prev, cur); prev = cur
    return dict(final_water=round(water_flow(burst), 1), burst_lost=round(lost_burst, 1),
                ramp_lost=round(lost_ramp, 1),
                burst_jumps={k: round(burst[k].theta - base[k].theta, 2) for k in burst
                             if k != "sun" and burst[k].theta - base[k].theta > SQRT_PI})

def exp_ai_draw_sweep():
    """How the extraction threshold moves as the AI's water draw grows."""
    return {d: exp_extraction(d)[0] for d in [0.0, 4.0, 10.0, 20.0, 35.0]}

if __name__ == "__main__":
    out = {}
    out["baseline"] = exp_baseline()
    first, sweep = exp_extraction(4.0)
    out["extraction_threshold_ai4"] = first
    out["extraction_sweep_ai4"] = [(e, k, w) for e, k, w, _ in sweep]
    out["extraction_detail_ai4"] = exp_extraction_detail(4.0)
    out["threshold_vs_ai_draw"] = exp_ai_draw_sweep()
    out["keystone_removal"] = removal_scores()
    out["keystone_marginal"] = keystone_scores()
    out["allocation_cheap_growth"] = exp_allocation(cost=0.2)
    out["allocation_dear_growth"] = exp_allocation(cost=1.5)
    out["teach_zero"] = exp_teach_zero()
    out["flood"] = exp_flood()
    print(json.dumps(out, indent=1))
