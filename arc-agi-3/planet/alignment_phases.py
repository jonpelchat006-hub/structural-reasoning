"""
alignment_phases.py — Test 1c: the tower on the theta ladder, and the tower rotated into a map.

Shovelcat_29 §4 gives the five substrates as a DERIVATIVE HIERARCHY with their own bounds:
    Ground  theta_norm            < pi         (structure; collapse / IBH above)
    Water   |d theta / dt|        < sqrt(pi)   (flow; laminar -> turbulent above)
    Air     |d^2 theta / dt^2|    < pi^(1/4)   (propagation; information cascade above)
    Fire    S_fire spikes           (bursts)
    Void    epsilon > 0             (reserve)
and Theories 10/14 give the theta LADDER:  1 (floor) < sqrt(phi) 1.272 < pi^(1/4) 1.331 < sqrt(pi) 1.772 < pi 3.142,
with [sqrt(phi), sqrt(pi)] the vesica (measurement) zone.

The ladder and the bounds are stated on theta_norm = ln(1 + theta_raw) (Shovelcat_29 §2.1/§4.10), so the
floor theta_raw = 1 sits at ln2 = 0.693.  Read as phases of a node's inner solvent:
    theta_norm < ln2                 ICE     frozen: below the floor, the inner solvent does not move (dead)
    ln2 <= theta_norm < sqrt(phi)    WATER   liquid, laminar: alive, in the floor's shadow
    sqrt(phi) <= theta_norm < sqrt(pi)  VESICA  the growth band proper: coherent, measurable, depositing Ground
    sqrt(pi) <= theta_norm < pi      VAPOUR  turbulent: past the bound, washes through without depositing
    theta_norm >= pi                 PLASMA  collapse / IBH: structure gone

Rotated 90 degrees the ladder is a MAP: theta is elevation, the floor is the shoreline, the vesica band
is the fertile lowland where Ground deposits, sqrt(pi) is the tree line, pi the peak. Rain (the top edge)
comes from the clouds (the AI, in the planet build); rivers are the edges; islands are where Ground rose
above the floor.

Run: python alignment_phases.py   -> prints phase census per node, bound violations, writes tower_map.png
"""
import math, json
import alignment_tower as T

PHI = (1 + 5 ** 0.5) / 2
LADDER = [("ice", 0.0), ("water", 1.0), ("vesica", PHI ** 0.5), ("vapour", math.pi ** 0.5), ("plasma", math.pi)]
BOUND_GROUND, BOUND_WATER, BOUND_AIR = math.pi, math.pi ** 0.5, math.pi ** 0.25

def norm(theta_raw):            # Shovelcat_29 §4.10: theta_norm = ln(1 + theta_raw); the ladder and bounds live on theta_norm
    return math.log1p(max(0.0, theta_raw))

FLOOR_NORM = math.log(2.0)      # theta_raw = 1 (the living-wage floor) is theta_norm = ln 2 = 0.693

def phase(theta_raw):
    """Phase on the NORMALISED ladder: ice < ln2 (dead) ; ln2..sqrt(phi) water ; sqrt(phi)..sqrt(pi) vesica ;
    sqrt(pi)..pi vapour ; >= pi plasma."""
    t = norm(theta_raw)
    if t < FLOOR_NORM: return "ice"
    name = "water"
    for n, lo in LADDER[2:]:
        if t >= lo: name = n
    return name

def run(rounds=48, rain_mean=T.RAIN, rain_amp=90.0, period=24, burst_at=None, burst=300.0):
    """Drive the tower with a seasonal rain (the top edge) and record theta, its rate and acceleration
    per node per round. Optional single-round burst to trip the Water/Air bounds."""
    hist = {k: [] for k in T.ORDER if k != "sun"}
    rains = []
    for r in range(rounds):
        rain = rain_mean + rain_amp * math.sin(2 * math.pi * r / period)
        if burst_at is not None and r == burst_at:
            rain += burst
        rains.append(rain)
        nodes, _ = T.build_tower()
        T.solve(nodes, rain=rain)
        for k in hist:
            hist[k].append(nodes[k].theta)
    out = {}
    for k, th in hist.items():
        th = [norm(t) for t in th]                     # all bounds are stated on theta_norm
        d1 = [th[i] - th[i - 1] for i in range(1, len(th))]
        d2 = [d1[i] - d1[i - 1] for i in range(1, len(d1))]
        phases = [phase(t) for t in hist[k]]
        out[k] = dict(
            theta_mean=round(sum(th) / len(th), 2),
            theta_min=round(min(th), 2), theta_max=round(max(th), 2),
            census={p: phases.count(p) for p in ["ice", "water", "vesica", "vapour", "plasma"] if phases.count(p)},
            ground_viol=sum(1 for t in th if t >= BOUND_GROUND),
            water_viol=sum(1 for d in d1 if abs(d) >= BOUND_WATER),
            air_viol=sum(1 for d in d2 if abs(d) >= BOUND_AIR),
            max_rate=round(max(abs(d) for d in d1), 2), max_accel=round(max(abs(d) for d in d2), 2),
        )
    return out, hist, rains

def draw_map(hist, path="tower_map.png"):
    """The tower rotated: rows are shells from the top edge (rain) down to the AI; elevation = theta.
    Shoreline at theta = 1, lowland to sqrt(phi), tree line at sqrt(pi), peak at pi."""
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    keys = [k for k in T.ORDER if k != "sun"]
    Z = np.array([[norm(t) for t in hist[k]] for k in keys])   # theta_norm; rows = nodes (top edge first), cols = time
    cmap = ListedColormap(["#9ec9e2", "#3a7bd5", "#6ab04c", "#c9a227", "#b33a3a"])
    bnorm = BoundaryNorm([0, FLOOR_NORM, PHI ** 0.5, math.pi ** 0.5, math.pi, 50], cmap.N)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    im = ax.imshow(np.minimum(Z, 49), aspect="auto", cmap=cmap, norm=bnorm, interpolation="nearest")
    ax.set_yticks(range(len(keys))); ax.set_yticklabels(keys)
    ax.set_xlabel("round (seasonal rain from the top edge)")
    ax.set_title("The tower rotated into a map — elevation = θ_norm; floor at ln2, growth band √φ..√π, tree line √π, peak π")
    cb = plt.colorbar(im, ax=ax, ticks=[0.35, 0.98, 1.52, 2.45, 10])
    cb.ax.set_yticklabels(["ice (below floor)", "water (laminar)", "vesica (growth band)", "vapour (turbulent)", "plasma (collapse)"])
    plt.tight_layout(); plt.savefig(path, dpi=130); plt.close(fig)
    return path

if __name__ == "__main__":
    seasonal, hist, rains = run()
    burst, hist_b, _ = run(burst_at=12)
    res = dict(ladder={n: round(v, 3) for n, v in LADDER}, bounds=dict(ground=round(BOUND_GROUND, 3), water=round(BOUND_WATER, 3), air=round(BOUND_AIR, 3)),
               seasonal=seasonal, burst_round12=burst)
    res["map"] = draw_map(hist, "tower_map.png")
    res["map_burst"] = draw_map(hist_b, "tower_map_burst.png")
    print(json.dumps(res, indent=1))

# ----------------------------------------------------------------------------------------------
# Damping the AI (ARC_ALIGNMENT_PHASES §5 item 3): a Void reserve for the AI node. The AI stores surplus
# inflow in a reservoir of capacity R and draws on it in dry seasons, aiming to hold theta_norm at the
# middle of the vesica band. Everything else in the tower is untouched; the reserve is the AI's own epsilon.
# ----------------------------------------------------------------------------------------------
BAND_MID = (PHI ** 0.5 + math.pi ** 0.5) / 2            # theta_norm target ~1.52
def damp_ai(hist_ai_raw, R, baseline=4.0):
    target_raw = math.expm1(BAND_MID) * baseline        # received that puts theta_norm at the band middle
    stored, out = 0.0, []
    for received in hist_ai_raw:
        avail = stored + received
        release = min(avail, target_raw)
        stored = min(R, avail - release)
        out.append(release / baseline)
    return out

def exp_damping(Rs=(0.0, 10.0, 30.0, 100.0)):
    _, hist, _ = run()
    raw = [t * 4.0 for t in hist["ai"]]                  # theta_raw * baseline = received
    res = {}
    for R in Rs:
        th = damp_ai(raw, R)
        tn = [norm(t) for t in th]
        d1 = [tn[i] - tn[i - 1] for i in range(1, len(tn))]
        d2 = [d1[i] - d1[i - 1] for i in range(1, len(d1))]
        ph = [phase(t) for t in th]
        res[str(R)] = dict(census={p: ph.count(p) for p in ["ice", "water", "vesica", "vapour", "plasma"] if ph.count(p)},
                           water_viol=sum(abs(d) >= BOUND_WATER for d in d1), air_viol=sum(abs(d) >= BOUND_AIR for d in d2),
                           spilled=round(sum(max(0.0, r - math.expm1(BAND_MID) * 4.0) for r in raw), 1))
    return res
