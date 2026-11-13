"""After the pre-registered run: spot-checks, and robustness checks that were NOT pre-registered (labelled so)."""
import math, os
import numpy as np, pandas as pd
from scipy import stats
E = pd.read_csv(r"D:\planet\mika\vortex\vortex_events.csv")
# spot-check 1: Apple FY2023, 3-year cash tax rate by hand from its 10-Ks (taxes paid / pre-tax income, FY2021-23, $M)
a = E[(E.ticker == "AAPL") & (E.fy_end == "2023-09-30")]
hand = (18_679 + 19_573 + 25_385) / (113_736 + 119_103 + 109_207)
print(f"AAPL FY2023 3-yr cash tax rate: file {a.cetr3.iloc[0]:.4f}  by hand {hand:.4f}" if len(a) else "AAPL FY2023 not in events")
# spot-check 2: NCSKEW equals minus scipy's bias-corrected skewness of the same weekly residuals (recomputed independently)
px = pd.concat([pd.read_pickle(r"D:\planet\mika\cube\prices_2010_2026.pkl"), pd.read_pickle(r"D:\planet\mika\cube2\prices_2010_2026.pkl")], axis=1)
C = pd.DataFrame({t: px[t]["Close"].iloc[:, 0] if isinstance(px[t]["Close"], pd.DataFrame) else px[t]["Close"] for t in ["AAPL", "SPY"]})
C.index = pd.DatetimeIndex(C.index).tz_localize(None)
W = C.resample("W-FRI").last().pct_change(fill_method=None)
i = int(np.searchsorted(W.index.values, np.datetime64(pd.Timestamp(a.filed.iloc[0]) + pd.Timedelta(days=1))))
r = W.AAPL.iloc[i + 1:i + 53]; m = W.SPY
df = pd.DataFrame({"r": r, "m0": m.reindex(r.index), "m1": m.shift(1).reindex(r.index), "mf": m.shift(-1).reindex(r.index)}).dropna()
Z = np.column_stack([np.ones(len(df)), df.m1, df.m0, df.mf]); e = df.r - Z @ np.linalg.lstsq(Z, df.r, rcond=None)[0]
print(f"AAPL year after FY2023 10-K: NCSKEW file {a.ncskew.iloc[0]:.4f}  scipy {-stats.skew(np.log1p(e), bias=False):.4f}; crash file {a.crash.iloc[0]}")


def yearly(df, x, y, min_n=25):
    v = np.array([g[x].rank().corr(g[y].rank()) for _, g in df.dropna(subset=[x, y]).groupby("year") if len(g) >= min_n])
    return f"rank corr {v.mean():+.3f}  t {v.mean() / (v.std(ddof=1) / math.sqrt(len(v))):+.2f}  same sign {(np.sign(v) == np.sign(v.mean())).sum()}/{len(v)}"


print("\nNOT pre-registered robustness:")
for label, df in [("2011-2017", E[E.year <= 2017]), ("2018-2025", E[E.year >= 2018]), ("tax rate above 2% only", E[E.cetr3 > 0.02])]:
    print(f"  {label:24s} avoid -> NCSKEW: {yearly(df, 'avoid', 'ncskew')}   avoid -> DUVOL: {yearly(df, 'avoid', 'duvol')}")
# add the cube's own measures (blur, leak, profitability) from the leak test as controls
L = pd.concat([pd.read_csv(r"D:\planet\mika\cube\leak_blur_events.csv"), pd.read_csv(r"D:\planet\mika\cube2\leak_blur_events.csv")])
M = E.merge(L[["ticker", "fy_end", "blur_before", "leak", "ni_a"]].drop_duplicates(["ticker", "fy_end"]), on=["ticker", "fy_end"], how="inner")
co = []
for _, g in M.dropna(subset=["ncskew", "avoid", "blur_before", "leak", "ni_a", "ncskew_pre", "size"]).groupby("year"):
    if len(g) < 25: continue
    z = lambda s: (s.rank() - s.rank().mean()) / s.rank().std()
    xs = ["avoid", "blur_before", "leak", "ni_a", "ncskew_pre", "size"]
    Zm = np.column_stack([np.ones(len(g))] + [z(g[c]) for c in xs])
    co.append(np.linalg.lstsq(Zm, z(g.ncskew).values, rcond=None)[0][1:])
co = np.array(co)
print(f"  with blur, leak, profitability, past skew and size as controls ({len(M)} events, {len(co)} years):")
for j, c in enumerate(["avoid", "blur_before", "leak", "ni_a", "ncskew_pre", "size"]):
    print(f"     {c:12s} slope {co[:, j].mean():+.3f}  t {co[:, j].mean() / (co[:, j].std(ddof=1) / math.sqrt(len(co))):+.2f}")
