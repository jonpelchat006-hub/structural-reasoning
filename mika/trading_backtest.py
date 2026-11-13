r"""Honest check of the trading agent's saved signals (D:\shovelcat-colony\brain\trading\<date>\signals.json).

For every (ticker, scan day) the last signal of that day is kept. Entry = the next session's open after the scan
(no look-ahead). Forward returns at 1, 5 and 20 sessions (close h-1 sessions after entry vs entry open).
  dir_ret   = sign * stock return            (sign +1 long, -1 short)  -> what the trade itself made, before costs
  vs_spy    = sign * (stock - SPY)            -> did the direction beat just holding / shorting the market?
  vs_univ   = sign * (stock - mean of all 152 tickers that day)  -> skill at picking WHICH names, not the market
Dates are clustered: signals from the same day move together, so the t-stat uses one average per scan day.
No orders are placed anywhere; this reads files and public daily prices only.
"""
import json, glob, os, sys, math
from collections import Counter, defaultdict
import numpy as np, pandas as pd

ROOT = r"D:\shovelcat-colony\brain\trading"
OUT = r"D:\planet\mika\trading_backtest.json"
CACHE = r"D:\planet\mika\prices_2026.pkl"
H = [1, 5, 20]

rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "*", "signals.json"))):
    try: ss = json.load(open(f, encoding="utf-8"))
    except Exception: continue
    ss = ss if isinstance(ss, list) else ss.get("signals", [])
    for s in ss:
        if not s.get("ticker") or s.get("direction") not in ("long", "short"): continue
        rows.append({"ticker": s["ticker"].upper(), "dir": s["direction"], "conf": float(s.get("confidence") or 0),
                     "at": s.get("scannedAt"), "trade": bool(s.get("shouldTrade")), "shark": s.get("sharkSignal"),
                     "pi": s.get("piClass"), "dome": s.get("domeType"), "llm_off": "LLM offline" in (s.get("thesis") or "")})
df = pd.DataFrame(rows)
df["at"] = pd.to_datetime(df["at"], utc=True, errors="coerce")
df = df.dropna(subset=["at"])
df["day"] = df["at"].dt.tz_convert("America/New_York").dt.date
raw_n = len(df)
flips = df.groupby(["ticker", "day"])["dir"].nunique()
df = df.sort_values("at").groupby(["ticker", "day"], as_index=False).last()
print(f"signals: {raw_n} saved -> {len(df)} ticker-days after keeping the last per day; "
      f"{int((flips > 1).sum())} ticker-days flipped direction within the day")
print("direction:", dict(Counter(df["dir"])), " LLM offline in thesis:", f"{df['llm_off'].mean():.0%}")

tickers = sorted(set(df["ticker"])) + ["SPY"]
if os.path.exists(CACHE): px = pd.read_pickle(CACHE)
else:
    import yfinance as yf
    px = yf.download(tickers, start="2026-03-01", end="2026-10-14", auto_adjust=True, group_by="ticker", progress=False, threads=True)
    px.to_pickle(CACHE)
have = [t for t in tickers if t in px.columns.get_level_values(0) and px[t]["Close"].notna().sum() > 50]
missing = sorted(set(tickers) - set(have))
print(f"prices: {len(have)} tickers with data, missing {len(missing)}: {missing[:20]}")
opens = pd.DataFrame({t: px[t]["Open"] for t in have}); closes = pd.DataFrame({t: px[t]["Close"] for t in have})
sessions = closes.index.tz_localize(None) if closes.index.tz is not None else closes.index
opens.index = closes.index = sessions
univ = [t for t in have if t != "SPY"]

F = {h: (closes.shift(-(h - 1)) / opens.where(opens > 0) - 1) for h in H}       # open of session i -> close of i+h-1
U = {h: F[h][univ].mean(axis=1) for h in H}
def fwd(t, i, h): return float(F[h][t].iloc[i])

recs = []
for r in df.itertuples():
    if r.ticker not in have: continue
    # next session strictly after the scan day (scan times are often during or after market hours)
    i = int(np.searchsorted(sessions.values, np.datetime64(pd.Timestamp(r.day) + pd.Timedelta(days=1)), side="left"))
    if i >= len(sessions): continue
    sign = 1 if r.dir == "long" else -1
    rec = {"ticker": r.ticker, "day": str(r.day), "dir": r.dir, "conf": r.conf, "entry": str(sessions[i].date()),
           "shark": r.shark, "pi": r.pi, "dome": r.dome}
    for h in H:
        s_ = fwd(r.ticker, i, h); m_ = fwd("SPY", i, h)
        u_ = float(U[h].iloc[i])
        rec[f"r{h}"] = s_; rec[f"dir{h}"] = sign * s_; rec[f"spy{h}"] = sign * (s_ - m_)
        rec[f"univ{h}"] = sign * (s_ - u_) if not math.isnan(u_) else np.nan
    recs.append(rec)
R = pd.DataFrame(recs)

def summary(sub, col):
    sub = sub.dropna(subset=[col])
    if len(sub) == 0: return None
    per_day = sub.groupby("day")[col].mean()
    se = per_day.std(ddof=1) / math.sqrt(len(per_day)) if len(per_day) > 1 else float("nan")
    return {"n": int(len(sub)), "days": int(len(per_day)), "mean_pct": round(100 * sub[col].mean(), 3),
            "hit": round(float((sub[col] > 0).mean()), 3), "day_mean_pct": round(100 * per_day.mean(), 3),
            "t_days": round(per_day.mean() / se, 2) if se and se > 0 else None}

report = {"signals_saved": raw_n, "ticker_days": int(len(df)), "tested": int(len(R)), "missing_prices": missing,
          "llm_offline_share": round(float(df["llm_off"].mean()), 3), "by": {}}
groups = {"all": R, "short": R[R.dir == "short"], "long": R[R.dir == "long"],
          "conf>=0.8": R[R.conf >= 0.8], "conf<0.8": R[R.conf < 0.8],
          "Mar-Apr": R[R.day < "2026-05-01"], "June": R[R.day >= "2026-05-01"]}
print("\n%-10s %-7s %7s %5s %9s %6s %10s %7s" % ("group", "measure", "n", "days", "mean %", "hit", "day-mean %", "t(days)"))
for g, sub in groups.items():
    report["by"][g] = {}
    for col in ["dir1", "dir5", "dir20", "spy5", "spy20", "univ5", "univ20"]:
        s = summary(sub, col)
        report["by"][g][col] = s
        if s: print("%-10s %-7s %7d %5d %9.3f %6.3f %10.3f %7s" % (g, col, s["n"], s["days"], s["mean_pct"], s["hit"], s["day_mean_pct"], s["t_days"]))
# what a $2,000 account would have seen: equal weight per scan day, 5-session holds, no costs, no overlap handling
pd_ = R.dropna(subset=["dir5"]).groupby("day")["dir5"].mean()
report["equal_weight_5d_per_day"] = {"days": int(len(pd_)), "mean_pct": round(100 * pd_.mean(), 3), "worst_day_pct": round(100 * pd_.min(), 3),
                                     "best_day_pct": round(100 * pd_.max(), 3)}
# market over the same windows, for context
spy = closes["SPY"]
report["spy_context"] = {"2026-03-16..2026-04-30": round(100 * (spy.loc["2026-04-30":].iloc[0] / spy.loc["2026-03-16":].iloc[0] - 1), 2),
                         "2026-06-03..2026-07-20": round(100 * (spy.loc["2026-07-20":].iloc[0] / spy.loc["2026-06-03":].iloc[0] - 1), 2)}
print("\nequal weight, 5-session hold, per scan day:", report["equal_weight_5d_per_day"])
print("SPY over the scan periods (%):", report["spy_context"])
top = R.dropna(subset=["dir20"]).groupby("ticker")["dir20"].agg(["count", "mean"]).sort_values("count", ascending=False).head(12)
report["most_signalled"] = {t: {"n": int(v["count"]), "mean_dir20_pct": round(100 * v["mean"], 2)} for t, v in top.iterrows()}
print("\nmost signalled tickers (20-session direction-adjusted mean %):")
for t, v in report["most_signalled"].items(): print(f"  {t:<6} n={v['n']:<4} {v['mean_dir20_pct']:+.2f}")
json.dump(report, open(OUT, "w", encoding="utf-8"), indent=1, default=str)
R.to_csv(OUT.replace(".json", "_rows.csv"), index=False)
print("\nwritten", OUT)
