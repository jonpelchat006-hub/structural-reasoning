"""Did the old agent's 'front face' readings (news emotion, news count) say anything about what came next?
Uses the rows from trading_backtest.py; compares each stock with the average of all tickers over the same window."""
import json, glob, os
import pandas as pd, numpy as np
rows = []
for f in sorted(glob.glob(r"D:\shovelcat-colony\brain\trading\*\signals.json")):
    for s in json.load(open(f, encoding="utf-8")):
        if s.get("ticker") and s.get("scannedAt"):
            rows.append({"ticker": s["ticker"].upper(), "at": s["scannedAt"], "emo": s.get("newsEmotion"), "news": s.get("newsCount") or 0})
S = pd.DataFrame(rows); S["at"] = pd.to_datetime(S["at"], utc=True, errors="coerce")
S["day"] = S["at"].dt.tz_convert("America/New_York").dt.date.astype(str)
S = S.sort_values("at").groupby(["ticker", "day"], as_index=False).last()
R = pd.read_csv(r"D:\planet\mika\trading_backtest_rows.csv")
R = R.merge(S[["ticker", "day", "emo", "news"]], on=["ticker", "day"], how="left")
sign = np.where(R["dir"] == "long", 1, -1)
for h in (5, 20): R[f"rel{h}"] = R[f"univ{h}"] * sign          # stock minus the all-ticker average, no direction
def show(col):
    g = R.dropna(subset=["rel20"]).groupby(col)
    t = pd.DataFrame({"n": g.size(), "rel5_%": 100 * g["rel5"].mean(), "rel20_%": 100 * g["rel20"].mean(),
                      "days": g["day"].nunique()}).sort_values("n", ascending=False)
    print(t.round(2).to_string()); print()
show("emo")
R["news_band"] = pd.cut(R["news"], [-1, 0, 3, 6, 100], labels=["0", "1-3", "4-6", "7+"])
show("news_band")
