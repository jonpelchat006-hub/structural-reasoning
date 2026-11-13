"""Follow-up (found AFTER looking at the quintiles, so it needs a split-half check): does the SIZE of the
mismatch, in either direction, come before more blur? mismatch = |leak - that year's median leak|."""
import math, os
import numpy as np, pandas as pd
X = pd.read_csv(os.path.join(os.environ.get("CUBE_HOME", r"D:\planet\mika\cube"), "leak_blur_events.csv"))
M = X[~X.fin].copy()
M["mismatch"] = (M.leak - M.groupby("year").leak.transform("median")).abs()
M["loss"] = M.ni_a < 0


def yearly(df, a, b, min_n=25):
    v = np.array([g[a].rank().corr(g[b].rank()) for _, g in df.dropna(subset=[a, b]).groupby("year") if len(g) >= min_n])
    return f"years {len(v):2d}  rank corr {v.mean():+.3f}  t {v.mean() / (v.std(ddof=1) / math.sqrt(len(v))):+.2f}  same sign {(np.sign(v) == np.sign(v.mean())).sum()}/{len(v)}"


for label, df in [("all years", M), ("2011-2018", M[M.year <= 2018]), ("2019-2026", M[M.year >= 2019])]:
    print(f"{label:10s} mismatch -> blur change 63 : {yearly(df, 'mismatch', 'dblur63')}")
    print(f"{label:10s} mismatch -> blur change 126: {yearly(df, 'mismatch', 'dblur126')}")
    print(f"{label:10s} mismatch -> return 252     : {yearly(df, 'mismatch', 'rel252')}")
nl = M[~M.loss]
print(f"profitable only  mismatch -> blur change 63 : {yearly(nl, 'mismatch', 'dblur63')}")
print(f"profitable only  mismatch -> return 252     : {yearly(nl, 'mismatch', 'rel252')}")
M["q"] = M.groupby("year")["leak"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1 if len(s) >= 25 else np.nan)
print("\nshare of reports with a loss, by leak quintile:", M.groupby("q").loss.mean().round(2).to_dict())
print("median blur level (annualised %) by leak quintile:", (100 * M.groupby("q").blur_before.median()).round(1).to_dict())
