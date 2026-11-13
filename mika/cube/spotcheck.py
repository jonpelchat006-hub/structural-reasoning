"""Spot-checks for the leak test: Apple FY2023 against its published 10-K numbers, and one blur window by hand."""
import math, numpy as np, pandas as pd
X = pd.read_csv(r"D:\planet\mika\cube\leak_blur_events.csv")
a = X[(X.ticker == "AAPL") & (X.fy_end == "2023-09-30")].iloc[0]
expect = (96_995 - 110_543) / ((352_583 + 352_755) / 2)       # 10-K FY2023: net income, operating cash flow, total assets
print(f"AAPL FY2023 leak: file {a.leak:+.4f}  by hand from the 10-K {expect:+.4f}  filed {a.filed} event {a.event}")
px = pd.read_pickle(r"D:\planet\mika\cube\prices_2010_2026.pkl")
c = px["AAPL"]["Close"].dropna(); s = px["SPY"]["Close"].dropna()
c.index = pd.DatetimeIndex(c.index).tz_localize(None); s.index = pd.DatetimeIndex(s.index).tz_localize(None)
r = np.log(c).diff(); m = np.log(s).diff()
i = c.index.get_loc(pd.Timestamp(a.event))
x, y = r.iloc[i - 252:i], m.iloc[i - 252:i]
beta = np.cov(x, y)[0, 1] / np.var(y, ddof=1)
pre = (r.iloc[i - 63:i] - beta * m.iloc[i - 63:i]).std(ddof=1) * math.sqrt(252)
post = (r.iloc[i + 1:i + 64] - beta * m.iloc[i + 1:i + 64]).std(ddof=1) * math.sqrt(252)
print(f"AAPL beta file {a.beta:.3f} hand {beta:.3f} | blur before file {a.blur_before:.4f} hand {pre:.4f} | after file {a.blur_after63:.4f} hand {post:.4f}")
print("leak spread across all reports (median, 10th, 90th pct):", X.leak.median().round(4), X.leak.quantile(.1).round(4), X.leak.quantile(.9).round(4))
