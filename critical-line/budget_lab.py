"""Budget lab v2 — perceive the budget, model it, predict the wall (of game over).

A budget meter is not a wiggling pixel — it is a SWEEP: a connected set of pixels that each
flip ONCE, in a spatial order (the bar drains end-to-end). Detector:
  1. record every frame of a live run;
  2. candidates = pixels changing 1-3 times total (meters flip once; the agent wiggles a lot);
  3. meter = connected candidate component (>=8 px) whose first-change times correlate
     |r| > 0.9 with a spatial axis and span most of the run — the drain is ordered;
  4. level(t) = meter pixels not yet flipped; fit on the FIRST 60% only; predict game over;
  5. budget type = which counter depletion is linear in (actions here = movement budget).
"""
import json, os, sys
import numpy as np
from scipy import ndimage

RECORD = "--record" in sys.argv

if RECORD:
    sys.path.insert(0, "/home/claude/rh_voidline")
    from arc3_client import api, frame_np
    key = os.environ["ARC_API_KEY"]
    games = api("/api/games", key)
    gid = next(g["game_id"] for g in games if g["game_id"].startswith("ls20"))
    card_id = api("/api/scorecard/open", key, {"tags": ["budget-lab"]}).get("card_id")
    print("scorecard:", card_id, "game:", gid)
    guid = {}
    def send(a, x=None, y=None):
        body = {"game_id": gid, "card_id": card_id, "guid": guid.get("v")}
        if x is not None: body.update(x=x, y=y)
        fr = api(f"/api/cmd/{a}", key, body)
        guid["v"] = fr["guid"]
        return fr
    frames = []
    try:
        fr = send("RESET")
        frames.append(frame_np(fr))
        rng = np.random.default_rng(1)
        acts = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
        while fr["state"] not in ("WIN", "GAME_OVER") and len(frames) < 400:
            fr = send(acts[rng.integers(4)])
            frames.append(frame_np(fr))
        final_state = fr["state"]
    finally:
        api("/api/scorecard/close", key, {"card_id": card_id})
    F = np.array(frames)
    np.savez("/home/claude/rh_voidline/budget_frames.npz", F=F, final_state=final_state)
    print(f"recorded {len(F)} frames; final state {final_state}")

D = np.load("/home/claude/rh_voidline/budget_frames.npz")
F = D["F"]; T = len(F)
print(f"analyzing {T} frames (final {D['final_state']})")

# ---- candidates: flip 1..3 times ----
nch = (np.diff(F, axis=0) != 0).sum(axis=0)
cand = (nch >= 1) & (nch <= 3)
# first change time per candidate
chg = (np.diff(F, axis=0) != 0)
tc = np.full((64, 64), -1)
ys, xs_ = np.where(cand)
for y, x in zip(ys, xs_):
    tc[y, x] = np.argmax(chg[:, y, x]) + 1

# ---- connected components; meter = spatially-ordered flip times spanning the run ----
lab, nlab = ndimage.label(cand)
meters = []
for i in range(1, nlab+1):
    yy, xx = np.where(lab == i)
    if len(yy) < 8: continue
    tt = tc[yy, xx].astype(float)
    span = (tt.max() - tt.min())/(T-1)
    ax = xx if np.ptp(xx) >= np.ptp(yy) else yy
    if np.ptp(ax) == 0 or tt.std() == 0: continue
    r = abs(np.corrcoef(ax, tt)[0, 1])
    if r > 0.9 and span > 0.5:
        meters.append((i, len(yy), r, span, (int(yy.min()), int(yy.max()))))
print("meter components:", [(f"px={n}", f"r={r:.3f}", f"span={s:.2f}", f"rows{rows}") for _, n, r, s, rows in meters])

assert meters, "no meter found"
mid = max(meters, key=lambda m: m[1])[0]
mono = (lab == mid)
ys, xs_ = np.where(mono)
start_vals = F[0, ys, xs_]
level = (F[:, ys, xs_] == start_vals).sum(axis=1)
t = np.arange(T)
cut = int(0.6*T)
A = np.polyfit(t[:cut], level[:cut], 1)
pred_end = -A[1]/A[0]
resid = level - np.polyval(A, t)
lin_r2 = 1 - np.var(resid)/np.var(level)
print(f"meter: {int(mono.sum())} px, rows {ys.min()}-{ys.max()}")
print(f"depletion (fit on first {cut} actions): {-A[0]:.4f} px/action")
print(f"PREDICTED game-over at action {pred_end:.0f};  ACTUAL at {T-1}  (error {abs(pred_end-(T-1))/(T-1)*100:.1f}%)")
print(f"linear in actions: R^2 = {lin_r2:.4f} -> {'MOVEMENT budget (per action)' if lin_r2 > 0.97 else 'not purely per-action'}")

np.savez("/home/claude/rh_voidline/budget_out.npz",
         mono=mono.astype(int), level=level, fit=A, pred_end=pred_end, T=T,
         first=F[0], mid_f=F[T//2], last=F[-1], cut=cut)
json.dump(dict(T=int(T), meter_px=int(mono.sum()), rate=float(-A[0]),
               pred_end=float(pred_end), actual_end=int(T-1), r2=float(lin_r2),
               n_meters=len(meters)),
          open("/home/claude/rh_voidline/budget_res.json","w"))
print("saved budget_out.npz / budget_res.json")
