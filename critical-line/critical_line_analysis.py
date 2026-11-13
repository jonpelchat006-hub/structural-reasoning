"""Tests A & B: level repulsion in the void-line operator spectrum vs zeta zeros,
and C-pixel placement between crossings."""
import numpy as np, json, mpmath as mp
from scipy import stats
from scipy.integrate import cumulative_trapezoid

D = np.load("/home/claude/rh_voidline/pipeline_out.npz")
PDBS = ["1cll","3pgk","1php","1gd1","6ldh","8tln","4ake","2lzm"]
out = {}

# ---------- zeta zeros ----------
NZ = 500
zeros = np.array([float(mp.zetazero(n).imag) for n in range(1, NZ+1)])
def NvM(t):  # Riemann-von Mangoldt smooth counting
    return t/(2*np.pi)*np.log(t/(2*np.pi)) - t/(2*np.pi) + 7/8.0
zeta_unf = NvM(zeros)
zeta_sp = np.diff(zeta_unf)
zeta_sp = zeta_sp/zeta_sp.mean()
out["zeta"] = dict(n=NZ, mean_spacing=float(np.diff(zeta_unf).mean()))

# ---------- reference distributions (numerical CDFs) ----------
sgrid = np.linspace(0, 6, 4001)
def cdf_from_pdf(p):
    c = cumulative_trapezoid(p, sgrid, initial=0.0)
    return c/c[-1]
p_poisson = np.exp(-sgrid)
p_goe = (np.pi/2)*sgrid*np.exp(-np.pi*sgrid**2/4)
p_gue = (32/np.pi**2)*sgrid**2*np.exp(-4*sgrid**2/np.pi)
CDFS = {"Poisson": cdf_from_pdf(p_poisson),
        "GOE": cdf_from_pdf(p_goe),
        "GUE": cdf_from_pdf(p_gue)}
def ks_against(sample, cdfvals):
    f = lambda x: np.interp(x, sgrid, cdfvals)
    return stats.kstest(sample, f)

# ---------- Test A: unfolded spacings of contact-Laplacian eigenvalues ----------
def unfold(eigs, trim=0.05, deg=9):
    e = np.sort(eigs)
    e = e[1:]                      # drop the trivial 0 mode
    n = len(e)
    lo, hi = int(n*trim), int(n*(1-trim))
    idx = np.arange(1, n+1).astype(float)
    coef = np.polyfit(e, idx, deg)  # smooth staircase fit
    unf = np.polyval(coef, e)
    sp = np.diff(unf[lo:hi])
    sp = sp[sp > 0]
    return sp/sp.mean()

pooled = []
perprot = {}
for pid in PDBS:
    sp = unfold(D[f"{pid}_eigs"])
    pooled.append(sp)
    r = {}
    for name, c in CDFS.items():
        ks = ks_against(sp, c)
        r[name] = (round(float(ks.statistic),3), float(ks.pvalue))
    perprot[pid] = dict(n_sp=len(sp), ks=r)
pooled = np.concatenate(pooled)
pooled = pooled/pooled.mean()
out["testA_perprotein"] = perprot
out["testA_pooled"] = {name: (round(float(ks_against(pooled,c).statistic),4),
                              float(ks_against(pooled,c).pvalue)) for name,c in CDFS.items()}
out["testA_pooled_n"] = len(pooled)
# zeta spacings vs same references + direct zeta-vs-protein two-sample KS
out["zeta_ks"] = {name: (round(float(ks_against(zeta_sp,c).statistic),4),
                         float(ks_against(zeta_sp,c).pvalue)) for name,c in CDFS.items()}
ks2 = stats.ks_2samp(pooled, zeta_sp)
out["zeta_vs_protein_2samp"] = (round(float(ks2.statistic),4), float(ks2.pvalue))
# small-s repulsion check: fraction of spacings < 0.25
for name, arr in [("protein_pooled", pooled), ("zeta", zeta_sp)]:
    out[f"frac_small_{name}"] = round(float((arr<0.25).mean()),4)
out["frac_small_poisson_expected"] = round(1-np.exp(-0.25),4)
out["frac_small_goe_expected"] = round(float(np.interp(0.25, sgrid, CDFS["GOE"])),4)
out["frac_small_gue_expected"] = round(float(np.interp(0.25, sgrid, CDFS["GUE"])),4)

# ---------- Test B: C pixels vs crossing points along the seam ----------
CORRIDOR = 6.0
rowsC, rowsN = [], []
perB = {}
for pid in PDBS:
    ca, s, mid = D[f"{pid}_ca"], D[f"{pid}_s"], D[f"{pid}_mid"]
    axis, cross = D[f"{pid}_axis"], D[f"{pid}_crossxyz"]
    Cset = set(D[f"{pid}_C"].tolist())
    if len(cross)==0: continue
    corridor = np.where(np.abs(s) < CORRIDOR)[0]
    u = (ca - mid) @ axis
    uc = (cross - mid) @ axis
    scale = np.std(u[corridor]) or 1.0
    dC, dN = [], []
    for i in corridor:
        d = np.min(np.abs(u[i]-uc))/scale
        (dC if i in Cset else dN).append(d)
    if len(dC)>=3 and len(dN)>=3:
        mw = stats.mannwhitneyu(dC, dN, alternative="greater")  # C farther from zeros?
        perB[pid] = dict(nC=len(dC), nN=len(dN),
                         medC=round(float(np.median(dC)),3),
                         medN=round(float(np.median(dN)),3),
                         p_greater=round(float(mw.pvalue),4))
    rowsC += dC; rowsN += dN
mwp = stats.mannwhitneyu(rowsC, rowsN, alternative="greater")
mwl = stats.mannwhitneyu(rowsC, rowsN, alternative="less")
out["testB_perprotein"] = perB
out["testB_pooled"] = dict(nC=len(rowsC), nN=len(rowsN),
    medC=round(float(np.median(rowsC)),3), medN=round(float(np.median(rowsN)),3),
    p_C_farther=float(mwp.pvalue), p_C_closer=float(mwl.pvalue))

json.dump(out, open("/home/claude/rh_voidline/analysis_out.json","w"), indent=1)
np.savez("/home/claude/rh_voidline/spacings.npz", pooled=pooled, zeta=zeta_sp,
         sgrid=sgrid, **{k:v for k,v in CDFS.items()})
print(json.dumps({k:v for k,v in out.items() if "perprotein" not in k}, indent=1))
print("perA:", json.dumps(out["testA_perprotein"], indent=0))
print("perB:", json.dumps(out["testB_perprotein"], indent=0))
