import pandas as pd, numpy as np
R = pd.read_csv(r"D:\planet\mika\trading_backtest_rows.csv")
px = pd.read_pickle(r"D:\planet\mika\prices_2026.pkl")
rng = np.random.default_rng(7)
for i in rng.choice(len(R), 5, replace=False):
    r = R.iloc[i]
    o = px[r.ticker]["Open"].dropna(); c = px[r.ticker]["Close"].dropna()
    days = c.index[c.index >= pd.Timestamp(r.entry)]
    if len(days) < 20: continue
    e = o.loc[days[0]]; x5 = c.loc[days[4]]; x20 = c.loc[days[19]]
    sign = 1 if r.dir == "long" else -1
    print(f"{r.ticker} {r.dir} scan {r.day} entry {days[0].date()} open {e:.2f} | 5d close {x5:.2f} -> {sign*(x5/e-1)*100:+.2f}% (file {r.dir5*100:+.2f}%) "
          f"| 20d close {x20:.2f} -> {sign*(x20/e-1)*100:+.2f}% (file {r.dir20*100:+.2f}%)")
spy = px["SPY"]["Close"].dropna()
print("SPY", spy.loc["2026-03-16":].iloc[0], "->", spy.loc["2026-04-30":].iloc[0], "| SPY 2026-06-03", spy.loc["2026-06-03":].iloc[0], "-> 2026-07-20", spy.loc["2026-07-20":].iloc[0], "| last", spy.index[-1].date(), spy.iloc[-1])
sh = R[R.dir == "short"].dropna(subset=["dir20"])
print("shorts losing at 20 sessions:", f"{(sh.dir20 < 0).mean():.1%}", " stocks' own 20-session move for shorted names, mean:", f"{sh.r20.mean()*100:+.2f}%")
