"""Bridge lab: can Jonathan's theta-field equation GENERATE the Riemann-Siegel theta?
Stationary limit of  dtheta/dt = D grad^2 theta - (theta-1)/tau + S :
with tau -> inf (the void-line / frictionless regime), theta'' = -S/D.
Candidate sources along the line:
  point    : S ~ delta at the base        -> theta linear
  uniform  : S = const                    -> theta quadratic
  ray      : S = -D/(2x)  (the Haar measure dx/x of the mover ray, Part XIV)
             -> theta(x) = (x/2)ln x - x/2 + C1 x + C2
Prediction if the bridge is real: C1 = -1/2 ln(2pi)  (the pi-plane calibration)
                                  C2 = -pi/8         (the 7/8's source)
and the remaining residual = the known 1/(48t) tail of RS theta.
Also: with relaxation ON (finite tau) the log profile is screened away.
"""
import numpy as np, mpmath as mp, json
mp.mp.dps = 15

t = np.linspace(20, 1500, 600)
theta_true = np.array([float(mp.siegeltheta(x)) for x in t])

out = {}
# --- candidate profiles, least-squares fits ---
def fit(design, y):
    A = np.vstack(design).T
    c, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ c
    return c, float(np.sqrt(np.mean((y-pred)**2))), pred

# point source (theta linear): a x + b
c_pt, rms_pt, pred_pt = fit([t, np.ones_like(t)], theta_true)
# uniform source (theta quadratic): a x^2 + b x + c
c_un, rms_un, pred_un = fit([t**2, t, np.ones_like(t)], theta_true)
# ray source: (x/2)ln x - x/2 fixed shape + C1 x + C2
base = t/2*np.log(t) - t/2
c_ray, rms_ray, pred_ray = fit([t, np.ones_like(t)], theta_true - base)
out["rms_point"] = rms_pt
out["rms_uniform"] = rms_un
out["rms_ray"] = rms_ray
out["C1_fit"] = float(c_ray[0]); out["C1_predicted"] = float(-0.5*np.log(2*np.pi))
out["C2_fit"] = float(c_ray[1]); out["C2_predicted"] = float(-np.pi/8)

# --- parameter-free version: fix the pi constants, residual should be 1/(48t) ---
fixed = t/2*np.log(t/(2*np.pi)) - t/2 - np.pi/8
resid = theta_true - fixed
out["fixed_resid_max"] = float(np.abs(resid).max())
out["resid_vs_1_48t"] = [(float(tt), float(r), float(1/(48*tt)))
                         for tt,r in zip(t[[0,100,300,599]], resid[[0,100,300,599]])]

# --- relaxation ON: finite tau screens the profile (BVP via finite differences) ---
# theta'' = (theta-1)/(D tau) - S/D  with ray source; D=1, tau=100
n = 2000; xg = np.linspace(2*np.pi, 1500, n); h = xg[1]-xg[0]
tau = 100.0
S = 1/(2*xg)
A = np.zeros((n,n)); b = np.zeros(n)
for i in range(1,n-1):
    A[i,i-1] = 1/h**2; A[i,i+1] = 1/h**2
    A[i,i] = -2/h**2 - 1/tau
    b[i] = -S[i] - 1/tau*1.0*0 - 0   # theta measured as deviation u = theta-1: u'' = u/tau - S
# u(0)=theta_true[0]... boundary: match left value, free (Neumann) right
A[0,0]=1; b[0]= float(mp.siegeltheta(2*np.pi))
A[n-1,n-1]=1/h; A[n-1,n-2]=-1/h; b[n-1]=0
u = np.linalg.solve(A,b)
out["relaxed_final_over_true"] = float(u[-1]/theta_true[-1])

json.dump(out, open("/home/claude/rh_voidline/theta_bridge_res.json","w"), indent=1)
np.savez("/home/claude/rh_voidline/theta_bridge_out.npz", t=t, theta_true=theta_true,
         pred_pt=pred_pt, pred_un=pred_un, pred_ray=base+pred_ray, fixed=fixed,
         resid=resid, xg=xg, relaxed=u)
print(json.dumps(out, indent=1))
