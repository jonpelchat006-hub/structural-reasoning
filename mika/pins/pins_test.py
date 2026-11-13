r"""Bent pins, step 2: the pre-registered test (PREREGISTERED.md). Aligned = routine, bent = opportunistic
(Cohen, Malloy & Pomorski 2012). Reads insider_trades.csv and the cached prices; writes pins_results.json and
pins_events.csv."""
import json, math, os
import numpy as np, pandas as pd

HOME = r"D:\planet\mika\pins"
T = pd.read_csv(os.path.join(HOME, "insider_trades.csv"), dtype=str)
T = T[T.DOCUMENT_TYPE == "4"].copy()                                   # originals only; amendments repeat lines
T["fd"] = pd.to_datetime(T.FILING_DATE, format="%d-%b-%Y", errors="coerce")
T["td"] = pd.to_datetime(T.TRANS_DATE, format="%d-%b-%Y", errors="coerce")
T = T.dropna(subset=["fd", "td", "RPTOWNERCIK", "ticker"])
T = T[(T.td <= T.fd) & ((T.fd - T.td).dt.days <= 365)]
T["dir"] = np.where(T.TRANS_CODE == "P", 1, -1)
T["value"] = pd.to_numeric(T.TRANS_SHARES, errors="coerce") * pd.to_numeric(T.TRANS_PRICEPERSHARE, errors="coerce")
T["plan"] = T.AFF10B5ONE.isin(["1", "true", "True", "TRUE"])
print(f"open-market lines: {len(T)} ({int((T.dir == 1).sum())} buys, {int((T.dir == -1).sum())} sells), "
      f"{T.RPTOWNERCIK.nunique()} insiders at {T.ticker.nunique()} companies, trades {T.td.min().date()}..{T.td.max().date()}")

# each pin's history: the months it traded this company's stock, per year
T["y"], T["m"] = T.td.dt.year, T.td.dt.month
hist = T.groupby(["ticker", "RPTOWNERCIK", "y"]).m.apply(set).to_dict()


def kind(r):
    h = [hist.get((r.ticker, r.RPTOWNERCIK, r.y - k)) for k in (1, 2, 3)]
    if any(x is None for x in h): return "unclassified"
    return "aligned" if r.m in (h[0] & h[1] & h[2]) else "bent"


ev = (T.sort_values("td").groupby(["ticker", "RPTOWNERCIK", "fd", "dir"], as_index=False)
      .agg(td=("td", "first"), y=("y", "first"), m=("m", "first"), value=("value", "sum"), plan=("plan", "max"),
           rel=("RPTOWNER_RELATIONSHIP", "first"), name=("RPTOWNERNAME", "first")))
ev["kind"] = [kind(r) for r in ev.itertuples()]
print("events by kind:", ev.groupby(["kind", "dir"]).size().to_dict())

C = []
for d in [r"D:\planet\mika\cube", r"D:\planet\mika\cube2"]:
    px = pd.read_pickle(os.path.join(d, "prices_2010_2026.pkl"))
    C.append(pd.DataFrame({t: px[t]["Close"] for t in px.columns.get_level_values(0).unique() if t != "SPY"}))
C = pd.concat(C, axis=1); C = C.loc[:, ~C.columns.duplicated()].sort_index()
C.index = pd.DatetimeIndex(C.index).tz_localize(None)
days = C.index
F = {h: C.shift(-h) / C - 1 for h in (21, 126)}
U = {h: F[h].mean(axis=1) for h in F}
ev = ev[ev.kind != "unclassified"].copy()
idx = np.searchsorted(days.values, (ev.fd + pd.Timedelta(days=1)).values.astype("datetime64[ns]"))
ev["i"] = idx
ev = ev[(ev.i < len(days)) & ev.ticker.isin(C.columns)]
for h in (21, 126):
    col = C.columns.get_indexer(ev.ticker)
    vals = F[h].values[ev.i.values, col]
    ev[f"rel{h}"] = vals - U[h].values[ev.i.values]
    ev[f"dr{h}"] = ev.dir * ev[f"rel{h}"]
ev["year"] = days[ev.i.values].year
ev.to_csv(os.path.join(HOME, "pins_events.csv"), index=False)


def by_year(sub, col, min_n=20):
    g = sub.dropna(subset=[col]).groupby("year")[col]
    m = g.mean()[g.size() >= min_n]
    if len(m) < 3: return None
    return {"n": int(sub[col].notna().sum()), "years": int(len(m)), "mean_pct": round(100 * float(m.mean()), 2),
            "t": round(float(m.mean() / (m.std(ddof=1) / math.sqrt(len(m)))), 2), "years_positive": int((m > 0).sum())}


res = {"events": int(len(ev)), "years": [int(ev.year.min()), int(ev.year.max())], "groups": {}}
print("\n%-14s %-6s %7s %6s %8s %7s %8s" % ("group", "window", "n", "years", "mean %", "t", "yrs > 0"))
for name, sub in [("bent buys", ev[(ev.kind == "bent") & (ev.dir == 1)]), ("bent sells", ev[(ev.kind == "bent") & (ev.dir == -1)]),
                  ("aligned buys", ev[(ev.kind == "aligned") & (ev.dir == 1)]), ("aligned sells", ev[(ev.kind == "aligned") & (ev.dir == -1)]),
                  ("bent all", ev[ev.kind == "bent"]), ("aligned all", ev[ev.kind == "aligned"])]:
    for h in (21, 126):
        s = by_year(sub, f"dr{h}"); res["groups"][f"{name} {h}"] = s
        if s: print("%-14s %-6s %7d %6d %8.2f %7.2f %5d/%d" % (name, h, s["n"], s["years"], s["mean_pct"], s["t"], s["years_positive"], s["years"]))
# claim 4: bent minus aligned, direction-adjusted, 126 sessions, per year
d = (ev[ev.kind == "bent"].groupby("year").dr126.mean() - ev[ev.kind == "aligned"].groupby("year").dr126.mean()).dropna()
res["bent_minus_aligned_126"] = {"mean_pct": round(100 * d.mean(), 2), "t": round(float(d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))), 2),
                                 "years": int(len(d)), "years_positive": int((d > 0).sum())}
print("\nbent minus aligned (direction-adjusted, 126):", res["bent_minus_aligned_126"])
# claim 5: before trouble - share of sells followed by a fall of 20%+ vs the rest within 126 sessions
sells = ev[ev.dir == -1].dropna(subset=["rel126"]).copy(); sells["fall"] = sells.rel126 <= -0.20
f = sells.groupby(["year", "kind"]).fall.mean().unstack().dropna()
dd = f["bent"] - f["aligned"]
res["trouble_after_sells"] = {"bent_share": round(float(f["bent"].mean()), 3), "aligned_share": round(float(f["aligned"].mean()), 3),
                              "diff_t": round(float(dd.mean() / (dd.std(ddof=1) / math.sqrt(len(dd)))), 2), "years": int(len(dd))}
print("falls of 20%+ after sells:", res["trouble_after_sells"])
pl = ev[(ev.dir == -1) & (ev.year >= 2023)]
res["planned_share_of_sells_2023on"] = pl.groupby("kind").plan.mean().round(3).to_dict()
print("share of sells marked as pre-planned (10b5-1), 2023 on:", res["planned_share_of_sells_2023on"])
json.dump(res, open(os.path.join(HOME, "pins_results.json"), "w"), indent=1)
print("\nwritten", os.path.join(HOME, "pins_results.json"))
