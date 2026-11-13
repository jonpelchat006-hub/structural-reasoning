"""Part XXXII lab — the wall-net prototype.

Spec (Part XXXI) implemented literally:
  * neurons live at Stern-Brocot mediants (wall pixels); support = the Farey cell (Ford footprint)
  * spawn rule = load quantum: always split the cell holding the most integrated residual load
    (priority-queue version of "spawn when local load winds through one full cell")
  * learning rule = the shave: each neuron fits ONLY the residual left by its ancestors
  * addressing = which pixel (LR-word / continued-fraction path) + coordinate inside the pixel
Baselines / ablations:
  * dense LSQ: uniform grid of the same hat functions, FULL joint least squares (dense gets
    every advantage: global fit, no greed)
  * breadth-first: same net, but fill the wall level-by-level with no load routing
  * no-shave: each neuron fits the full target on its support instead of the residual
    (Part XXX predicted this over-coverage is the killer)
Targets:
  * T1 synthetic multiscale: smooth background + sharp features parked at rational pixels
  * T2 real: S(t) = N(t) - theta(t)/pi - 1 on t in [20,120]  (the zeta ledger itself)
"""
import numpy as np, json, os
os.chdir("/home/claude/rh_voidline")
rng = np.random.default_rng(7)

# ---------- targets ----------
M = 4000
xs = np.linspace(0.0, 1.0, M)

def target_synth(x):
    y = np.sin(2*np.pi*x) + 0.3*np.cos(6*np.pi*x)
    # sharp furniture parked at low-denominator pixels, width ~ Ford radius 1/(2q^2)
    for (p, q, a) in [(1,2,1.2), (1,3,-0.9), (2,3,0.7), (2,5,0.5), (3,5,-0.6), (1,7,0.45)]:
        w = 1.0/(2*q*q)
        y += a*np.exp(-0.5*((x - p/q)/(0.6*w))**2)
    return y

y1 = target_synth(xs)

# real S(t): cache
if os.path.exists("wallnet_S.npz"):
    D = np.load("wallnet_S.npz"); y2 = D["S"]
else:
    import mpmath as mp
    mp.mp.dps = 20
    zeros = np.load("zeros500.npy")
    tt = 20.0 + 100.0*xs
    theta = np.array([float(mp.siegeltheta(t)) for t in tt])
    Ncount = np.searchsorted(zeros, tt)
    y2 = Ncount - theta/np.pi - 1.0
    np.savez("wallnet_S.npz", S=y2)

# ---------- wall cells & neurons ----------
def hat(x, L, m, R):
    """hat peaked at mediant m, supported on the cell [L,R]"""
    y = np.zeros_like(x)
    l = (x >= L) & (x <= m); r = (x > m) & (x <= R)
    if m > L: y[l] = (x[l] - L)/(m - L)
    if R > m: y[r] = (R - x[r])/(R - m)
    return y

class Cell:
    __slots__ = ("p1","q1","p2","q2","word")
    def __init__(s, p1,q1,p2,q2, word=""):
        s.p1,s.q1,s.p2,s.q2,s.word = p1,q1,p2,q2,word
    @property
    def L(s): return s.p1/s.q1
    @property
    def R(s): return s.p2/s.q2
    @property
    def mediant(s): return (s.p1+s.p2)/(s.q1+s.q2)
    @property
    def mq(s): return (s.p1+s.p2, s.q1+s.q2)
    def kids(s):
        pm, qm = s.mq
        return (Cell(s.p1,s.q1,pm,qm,s.word+"L"), Cell(pm,qm,s.p2,s.q2,s.word+"R"))

def run_wallnet(y, n_max=256, mode="shave", routing="load"):
    """grow the net; return (rmse_curve, neurons) — neurons = (p,q,word,coef,depth)"""
    pred = np.full(M, y.mean())          # level-0: the mover / mean fluid
    neurons = []
    frontier = [Cell(0,1,1,1)]
    rmse = [float(np.sqrt(np.mean((y-pred)**2)))]
    while len(neurons) < n_max:
        resid = y - pred
        # routing: pick which pixel spawns next
        if routing == "load":
            loads = [np.trapezoid(np.abs(resid[(xs>=c.L)&(xs<=c.R)]),
                                  xs[(xs>=c.L)&(xs<=c.R)]) if ((xs>=c.L)&(xs<=c.R)).sum()>3 else 0.0
                     for c in frontier]
            c = frontier.pop(int(np.argmax(loads)))
        else:                              # breadth-first: shallowest word first
            frontier.sort(key=lambda c: (len(c.word), c.L))
            c = frontier.pop(0)
        phi = hat(xs, c.L, c.mediant, c.R)
        den = float(phi@phi)
        if den < 1e-12:
            continue
        src = resid if mode == "shave" else (y - y.mean())   # no-shave: fit full target
        coef = float(phi@src)/den
        pred = pred + coef*phi
        pm, qm = c.mq
        neurons.append(dict(p=pm, q=qm, word=c.word, coef=coef, depth=len(c.word)+1))
        frontier.extend(c.kids())
        rmse.append(float(np.sqrt(np.mean((y-pred)**2))))
    return rmse, neurons, pred

def dense_lsq(y, n_basis):
    """uniform grid of the same hats, full joint least squares"""
    knots = np.linspace(0, 1, n_basis+2)
    A = np.column_stack([hat(xs, knots[i], knots[i+1], knots[i+2]) for i in range(n_basis)])
    A = np.column_stack([np.ones(M), A])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A@coef
    return float(np.sqrt(np.mean((y-pred)**2)))

results = {}
for name, y in [("synth", y1), ("S_of_t", y2)]:
    r_shave, neurons, pred = run_wallnet(y, 256, "shave", "load")
    r_bf,    _,       _    = run_wallnet(y, 256, "shave", "breadth")
    r_nosh,  _,       _    = run_wallnet(y, 256, "noshave", "load")
    dense = {n: dense_lsq(y, n) for n in [8, 16, 32, 64, 128, 256]}
    results[name] = dict(rmse_shave=r_shave, rmse_breadth=r_bf, rmse_noshave=r_nosh,
                         dense=dense, neurons=neurons,
                         pred=pred.tolist() if name=="synth" else None)
    print(f"--- target {name} ---   rmse0={r_shave[0]:.4f}")
    for n in [8, 32, 128, 256]:
        print(f"  n={n:4d}  wall-net {r_shave[n]:.5f}   breadth {r_bf[n]:.5f}   "
              f"no-shave {r_nosh[n]:.5f}   dense-LSQ {dense.get(n,float('nan')):.5f}")

# ---------- the addressing demo: which pixel, then coords in the pixel ----------
def address(x, depth=8):
    c = Cell(0,1,1,1)
    word = ""
    for _ in range(depth):
        m = c.mediant
        kl, kr = c.kids()
        c = kl if x < m else kr
        word += c.word[-1]
    # coordinate inside the final pixel
    u = (x - c.L)/(c.R - c.L)
    return word, (c.p1,c.q1), (c.p2,c.q2), u

print("\naddressing demo (pixel word | cell | local coord):")
for x in [0.5, 1/np.sqrt(2), (np.sqrt(5)-1)/2, np.pi-3]:
    w, a, b, u = address(float(x))
    print(f"  x={x:.6f} -> word {w}  cell [{a[0]}/{a[1]}, {b[0]}/{b[1]}]  local u={u:.4f}")

# golden ratio should be the pure RLRLRL... = the golden gear
w, *_ = address((np.sqrt(5)-1)/2, 12)
print("  golden pixel word:", w, " (pure alternation = the RL golden gear)" if w in ("RLRLRLRLRLRL","LRLRLRLRLRLR") else "")

json.dump({k: {kk: vv for kk, vv in v.items() if kk != "pred"} for k, v in results.items()},
          open("wallnet_res.json","w"))
np.savez("wallnet_out.npz",
         xs=xs, y1=y1, y2=y2,
         pred1=np.array(results["synth"]["pred"]),
         rmse1=np.array(results["synth"]["rmse_shave"]),
         rmse1_bf=np.array(results["synth"]["rmse_breadth"]),
         rmse1_nosh=np.array(results["synth"]["rmse_noshave"]),
         rmse2=np.array(results["S_of_t"]["rmse_shave"]),
         rmse2_bf=np.array(results["S_of_t"]["rmse_breadth"]),
         rmse2_nosh=np.array(results["S_of_t"]["rmse_noshave"]),
         dense1_n=np.array(sorted(results["synth"]["dense"])),
         dense1=np.array([results["synth"]["dense"][n] for n in sorted(results["synth"]["dense"])]),
         dense2=np.array([results["S_of_t"]["dense"][n] for n in sorted(results["S_of_t"]["dense"])]),
         neur_p=np.array([nn["p"] for nn in results["S_of_t"]["neurons"]]),
         neur_q=np.array([nn["q"] for nn in results["S_of_t"]["neurons"]]),
         neur_c=np.array([nn["coef"] for nn in results["S_of_t"]["neurons"]]),
         neur_d=np.array([nn["depth"] for nn in results["S_of_t"]["neurons"]]))
print("\nsaved wallnet_res.json / wallnet_out.npz")

# ---------- fair fight: same optimizer both sides (joint LSQ), basis vs basis ----------
def joint_refit(y, neurons_cells):
    A = np.column_stack([np.ones(M)] + [hat(xs, L, m, R) for (L, m, R) in neurons_cells])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(np.sqrt(np.mean((y - A@coef)**2))), coef

def run_wallnet_cells(y, n_max, routing="load"):
    """same growth as run_wallnet but keep the (L, mediant, R) geometry of each neuron"""
    pred = np.full(M, y.mean()); cells_out = []
    frontier = [Cell(0,1,1,1)]
    while len(cells_out) < n_max:
        resid = y - pred
        if routing == "load":
            loads = [np.trapezoid(np.abs(resid[(xs>=c.L)&(xs<=c.R)]),
                                  xs[(xs>=c.L)&(xs<=c.R)]) if ((xs>=c.L)&(xs<=c.R)).sum()>3 else 0.0
                     for c in frontier]
            c = frontier.pop(int(np.argmax(loads)))
        else:
            frontier.sort(key=lambda c: (len(c.word), c.L)); c = frontier.pop(0)
        phi = hat(xs, c.L, c.mediant, c.R); den = float(phi@phi)
        if den < 1e-12: continue
        pred = pred + (float(phi@resid)/den)*phi
        cells_out.append((c.L, c.mediant, c.R))
        frontier.extend(c.kids())
    return cells_out

print("\n--- joint-LSQ refit: adaptive Farey basis vs uniform grid (same optimizer) ---")
refit_res = {}
for name, y in [("synth", y1), ("S_of_t", y2)]:
    cells = run_wallnet_cells(y, 256, "load")
    rows = {}
    print(f"  target {name}:")
    for n in [8, 16, 32, 64, 128, 256]:
        r_ad, _ = joint_refit(y, cells[:n])
        r_dn = dense_lsq(y, n)
        rows[n] = (r_ad, r_dn)
        print(f"    n={n:4d}  wall-net(refit) {r_ad:.5f}   dense grid {r_dn:.5f}   ratio {r_dn/max(r_ad,1e-12):.2f}x")
    refit_res[name] = rows
json.dump({k: {str(n): v for n, v in rows.items()} for k, rows in refit_res.items()},
          open("wallnet_refit.json","w"))

# ---------- save the figure inputs for the refit story ----------
cells_syn = run_wallnet_cells(y1, 256, "load")
r64, coef64 = joint_refit(y1, cells_syn[:64])
A64 = np.column_stack([np.ones(M)] + [hat(xs, L, m, R) for (L, m, R) in cells_syn[:64]])
pred64 = A64@coef64
np.savez("wallnet_fig.npz",
         pred64=pred64, r64=r64,
         cell_m=np.array([m for (_, m, _) in cells_syn[:64]]),
         cell_w=np.array([R-L for (L, _, R) in cells_syn[:64]]),
         coef64=coef64[1:],
         ref_n=np.array([8,16,32,64,128,256]),
         ref1=np.array([refit_res["synth"][n][0] for n in [8,16,32,64,128,256]]),
         den1=np.array([refit_res["synth"][n][1] for n in [8,16,32,64,128,256]]),
         ref2=np.array([refit_res["S_of_t"][n][0] for n in [8,16,32,64,128,256]]),
         den2=np.array([refit_res["S_of_t"][n][1] for n in [8,16,32,64,128,256]]))
print("saved wallnet_fig.npz  (refit n=64 rmse %.5f)" % r64)
