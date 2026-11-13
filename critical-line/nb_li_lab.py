"""Nyman-Beurling + Li labs.
NB: RH <=> the constant 1 lies in the closure of span{ {1/(kx)} } in L^2(0,1).
    d_N^2 = 1 - b^T G^-1 b; conjectured (BBLS) d_N^2 ~ C/log N, C = 2+gamma-log(4pi).
Li: lambda_n = sum_rho [1-(1-1/rho)^n] >= 0 for all n <=> RH. Computed from 500 zeros
    + smooth tail; counterfeit test: inject off-line quadruple at 0.75 +- 2i.
"""
import numpy as np, json
EULER = 0.5772156649015329

# ---------- NB ----------
# log-spaced grid on (1e-5, 1); region below 1e-5 contributes < 1e-5 per entry
M = 400000
x = np.exp(np.linspace(np.log(1e-5), 0.0, M))
w = np.gradient(x)                      # trapezoid-ish weights on the nonuniform grid
NMAX = 48
ks = np.arange(1, NMAX+1)
F = np.empty((NMAX, M))
for i,k in enumerate(ks):
    v = 1.0/(k*x)
    F[i] = v - np.floor(v)
Fw = F*w
G = Fw @ F.T
b = Fw @ np.ones(M)
b_exact = (np.log(ks) + 1 - EULER)/ks
quad_err = float(np.max(np.abs(b - b_exact)))
nb = {"b_quadrature_max_err": quad_err}
C = 2 + EULER - np.log(4*np.pi)
res_d = []
for N in [2,4,8,16,24,32,40,48]:
    GN = G[:N,:N] + 1e-12*np.eye(N)
    c = np.linalg.solve(GN, b_exact[:N])
    d2 = 1 - float(b_exact[:N] @ c)
    res_d.append((N, d2, d2*np.log(N)))
    if N==48: c48 = c
nb["dN2"] = [(n, round(d,5), round(dl,5)) for n,d,dl in res_d]
nb["C_target"] = round(float(C),5)
# Moebius comparison for the optimal coefficients (c_k ~ mu(k)-ish pattern)
def moebius(n):
    if n==1: return 1
    m, res, p = n, 1, 2
    while p*p<=m:
        if m%p==0:
            m//=p
            if m%p==0: return 0
            res=-res
        p+=1
    if m>1: res=-res
    return res
mu = np.array([moebius(int(k)) for k in ks])
mask = mu!=0
sign_match = float((np.sign(c48[mask])==np.sign(mu[mask])).mean())
corr = float(np.corrcoef(c48[mask], mu[mask])[0,1])
nb["c_vs_moebius_signmatch"] = round(sign_match,3)
nb["c_vs_moebius_corr"] = round(corr,3)

# ---------- Li ----------
zeros = np.load("/home/claude/rh_voidline/zeros500.npy")
rho = 0.5 + 1j*zeros
def li_from(rhos, n):
    return float(np.sum(2*np.real(1 - ((rhos-1)/rhos)**n)))
def tail(n, gmax):
    g = np.linspace(gmax, 1e6, 200000)
    dens = np.log(g/(2*np.pi))/(2*np.pi)
    return float(n*np.trapezoid(dens/(0.25+g**2), g))
gmax = zeros[-1]
ns = np.arange(1, 81)
lam = np.array([li_from(rho, int(n)) + tail(int(n), gmax) for n in ns])
asym = ns/2*(np.log(ns) - np.log(2*np.pi) - 1 + EULER) + 0.5*(1+EULER) + 1  # leading-order shape
li = {"lambda_first10": [round(float(v),4) for v in lam[:10]],
      "all_positive_n80": bool((lam>0).all()),
      "lam80": round(float(lam[-1]),3), "asym80": round(float(asym[-1]),3)}
# counterfeit: add off-line quadruple at beta=0.75, gamma0=2
cf = np.array([0.75+2j, 0.25+2j])   # rho and 1-rho-bar representatives (pairs give 2Re)
lam_cf = np.array([li_from(rho, int(n)) + tail(int(n), gmax)
                   + float(np.sum(2*np.real(1-((cf-1)/cf)**int(n)))) for n in ns])
first_neg = int(ns[np.argmax(lam_cf<0)]) if (lam_cf<0).any() else None
li["counterfeit_first_negative_n"] = first_neg
li["counterfeit_lam_min"] = round(float(lam_cf.min()),2)

np.savez("/home/claude/rh_voidline/nb_li_out.npz", ns=ns, lam=lam, lam_cf=lam_cf,
         asym=asym, dN=np.array(res_d), c48=c48, mu=mu)
json.dump({"NB":nb, "Li":li}, open("/home/claude/rh_voidline/nb_li_res.json","w"), indent=1)
print(json.dumps({"NB":nb, "Li":li}, indent=1))
