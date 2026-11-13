r"""Market cube, step 2: do LEAKS come before BLUR, and before weaker returns? (Jonathan, Oct 14 2026)

  leak      = (net income - cash from operations) / average assets, from each original 10-K
              (earnings the tunnel reported that did not arrive as cash; Sloan 1996 calls this accruals)
  leak_ar   = (receivables growth) / average assets  (sales booked but not collected)
  blur      = idiosyncratic volatility: daily stock return minus beta x SPY, annualised (beta from the prior year)
  event     = the first trading day after the 10-K was filed (point in time: only numbers public that day)
  before    = 63 sessions before the event; after = the next 63 / 126 sessions
  returns   = 126 / 252 sessions after the event, minus the average of all the companies over the same window

Each filing year is one cross-section (filings cluster in Feb-Mar, so the same year's events share a market).
Statistics are rank correlations per year, averaged; t = mean / (sd / sqrt(years)). Financials (SIC 6000-6999)
are left out of the main test: a bank's operating cash flow is not a customer tunnel.
Reads only the cache from cube_fetch.py. Writes leak_blur_results.json and leak_blur_events.csv."""
import glob, json, math, os
import numpy as np, pandas as pd

HOME = os.environ.get("CUBE_HOME", r"D:\planet\mika\cube")
NI = ["NetIncomeLoss", "ProfitLoss"]
CFO = ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]


def annual(entries, forms=("10-K", "10-K/A", "10-KT")):
    """duration facts ~1 year long from annual reports; per period end keep the FIRST filed value"""
    out = {}
    for e in entries:
        if e.get("form") not in forms or "start" not in e: continue
        d = (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days
        if not 340 <= d <= 380: continue
        k = e["end"]
        if k not in out or e["filed"] < out[k][1]: out[k] = (float(e["val"]), e["filed"])
    return out


def instant(entries):
    out = {}
    for e in entries:
        k = e["end"]
        if k not in out or e["filed"] < out[k][1]: out[k] = (float(e["val"]), e["filed"])
    return out


def first_of(facts, names, fn):
    merged = {}
    for n in names:
        for k, v in fn(facts.get(n, [])).items(): merged.setdefault(k, v)
    return merged


def near(series, date, lo, hi):
    """value of an instant series whose end date is within [date+lo, date+hi] days, first filed"""
    best = None
    for k, (v, f) in series.items():
        dd = (pd.Timestamp(k) - date).days
        if lo <= dd <= hi and (best is None or abs(dd - (lo + hi) / 2) < abs(best[0] - (lo + hi) / 2)): best = (dd, v)
    return None if best is None else best[1]


rows = []
for f in sorted(glob.glob(os.path.join(HOME, "sec", "*.json"))):
    t = os.path.basename(f)[:-5]
    d = json.load(open(f, encoding="utf-8")); facts, meta = d["facts"], d["meta"]
    ni, cfo = first_of(facts, NI, annual), first_of(facts, CFO, annual)
    assets, ar = instant(facts.get("Assets", [])), instant(facts.get("AccountsReceivableNetCurrent", []))
    for end, (niv, filed) in ni.items():
        if end not in cfo: continue
        E, F = pd.Timestamp(end), pd.Timestamp(filed)
        if not 20 <= (F - E).days <= 120: continue                    # the original report, not a later comparative
        a1, a0 = near(assets, E, -5, 5), near(assets, E, -380, -350)
        if not a1 or not a0 or a1 <= 0 or a0 <= 0: continue
        avg = (a1 + a0) / 2
        r1, r0 = near(ar, E, -5, 5), near(ar, E, -380, -350)
        sic = int(meta.get("sic") or 0)
        rows.append({"ticker": t, "fy_end": end, "filed": filed, "sic": sic, "fin": 6000 <= sic <= 6999,
                     "leak": (niv - cfo[end][0]) / avg, "leak_ar": (r1 - r0) / avg if r1 is not None and r0 is not None else np.nan,
                     "ni_a": niv / avg, "cfo_a": cfo[end][0] / avg})
ev = pd.DataFrame(rows)
print(f"annual reports with leak numbers: {len(ev)} from {ev.ticker.nunique()} companies "
      f"({int(ev.fin.sum())} bank/insurer reports set aside)")

px = pd.read_pickle(os.path.join(HOME, "prices_2010_2026.pkl"))
names = [t for t in px.columns.get_level_values(0).unique()]
C = pd.DataFrame({t: px[t]["Close"] for t in names}).sort_index()
C.index = pd.DatetimeIndex(C.index).tz_localize(None)
R = np.log(C).diff()
spy = R["SPY"]; days = C.index
univ = [t for t in names if t != "SPY"]


def blur(t, i, a, b, beta):
    x = R[t].iloc[i + a:i + b]; m = spy.iloc[i + a:i + b]
    ok = x.notna() & m.notna()
    if ok.sum() < 0.8 * (b - a): return np.nan
    return float((x[ok] - beta * m[ok]).std(ddof=1) * math.sqrt(252))


def fwd(i, h):
    if i + h >= len(days): return None
    return C.iloc[i + h] / C.iloc[i] - 1


fw = {}
out = []
for r in ev.itertuples():
    if r.ticker not in C.columns: continue
    i = int(np.searchsorted(days.values, np.datetime64(pd.Timestamp(r.filed) + pd.Timedelta(days=1))))
    if i < 260 or i + 64 >= len(days): continue
    x = R[r.ticker].iloc[i - 252:i]; m = spy.iloc[i - 252:i]; ok = x.notna() & m.notna()
    if ok.sum() < 200: continue
    beta = float(np.cov(x[ok], m[ok])[0, 1] / np.var(m[ok], ddof=1))
    rec = r._asdict(); rec.pop("Index", None)
    rec.update(event=str(days[i].date()), year=days[i].year, beta=beta, blur_before=blur(r.ticker, i, -63, 0, beta),
               blur_after63=blur(r.ticker, i, 1, 64, beta), blur_after126=blur(r.ticker, i, 1, 127, beta) if i + 127 < len(days) else np.nan)
    for h in (126, 252):
        if (i, h) not in fw: fw[i, h] = fwd(i, h)
        v = fw[i, h]
        if v is None or pd.isna(v.get(r.ticker)): rec[f"rel{h}"] = np.nan; continue
        rec[f"rel{h}"] = float(v[r.ticker] - v[univ].mean())
    out.append(rec)
X = pd.DataFrame(out)
X["dblur63"] = np.log(X.blur_after63 / X.blur_before)
X["dblur126"] = np.log(X.blur_after126 / X.blur_before)
X.to_csv(os.path.join(HOME, "leak_blur_events.csv"), index=False)
M = X[~X.fin]
print(f"events with prices: {len(X)}; main test (no banks/insurers): {len(M)} events, years {M.year.min()}-{M.year.max()}")


def yearly(df, a, b, min_n=25):
    vals = []
    for y, g in df.dropna(subset=[a, b]).groupby("year"):
        if len(g) >= min_n: vals.append(g[a].rank().corr(g[b].rank()))
    v = np.array(vals)
    if len(v) < 3: return None
    return {"years": len(v), "mean_rank_corr": round(float(v.mean()), 3), "t": round(float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), 2),
            "years_same_sign": int((np.sign(v) == np.sign(v.mean())).sum())}


def joint(df, y, xs, min_n=25):
    """per year: regress rank(y) on standardised ranks of xs; average the slopes"""
    co = []
    for yr, g in df.dropna(subset=[y] + xs).groupby("year"):
        if len(g) < min_n: continue
        Z = np.column_stack([np.ones(len(g))] + [(g[x].rank() - g[x].rank().mean()) / g[x].rank().std() for x in xs])
        yy = (g[y].rank() - g[y].rank().mean()) / g[y].rank().std()
        co.append(np.linalg.lstsq(Z, yy.values, rcond=None)[0][1:])
    co = np.array(co)
    return {x: {"slope": round(float(co[:, j].mean()), 3), "t": round(float(co[:, j].mean() / (co[:, j].std(ddof=1) / math.sqrt(len(co)))), 2)}
            for j, x in enumerate(xs)} | {"years": len(co)}


res = {"events": int(len(M)), "companies": int(M.ticker.nunique()), "years": [int(M.year.min()), int(M.year.max())], "tests": {}}
tests = [("leak", "dblur63", "leak -> blur change, next 63 sessions"), ("leak", "dblur126", "leak -> blur change, next 126"),
         ("leak", "rel126", "leak -> return vs the rest, 126"), ("leak", "rel252", "leak -> return vs the rest, 252"),
         ("leak_ar", "dblur63", "receivable leak -> blur change, 63"), ("leak_ar", "rel252", "receivable leak -> return, 252"),
         ("blur_before", "rel252", "blur -> return vs the rest, 252"), ("blur_before", "blur_after63", "blur now -> blur next (persistence)")]
print("\n%-40s %6s %10s %7s %10s" % ("test", "years", "rank corr", "t", "same sign"))
for a, b, label in tests:
    s = yearly(M, a, b); res["tests"][label] = s
    if s: print("%-40s %6d %10.3f %7.2f %7d/%d" % (label, s["years"], s["mean_rank_corr"], s["t"], s["years_same_sign"], s["years"]))
res["joint_rel252"] = joint(M, "rel252", ["leak", "blur_before"])
res["joint_rel252_all3"] = joint(M, "rel252", ["leak", "leak_ar", "blur_before"])
res["joint_dblur63"] = joint(M, "blur_after63", ["blur_before", "leak"])
print("\ntogether, return 252:", res["joint_rel252"])
print("together with receivables:", res["joint_rel252_all3"])
print("next blur from blur now + leak:", res["joint_dblur63"])
# quintiles of leak inside each year, then averaged over years
M = M[M.groupby("year").ticker.transform("size") >= 25].copy(); M["q"] = M.groupby("year")["leak"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1)
Q = M.groupby(["year", "q"])[["dblur63", "rel252", "leak"]].mean().groupby("q").mean()
Q["n"] = M.groupby("q").size()
print("\nby leak quintile (1 = cash ahead of earnings, 5 = earnings ahead of cash), averaged over years:")
print((Q.assign(dblur63=Q.dblur63 * 100, rel252=Q.rel252 * 100, leak=Q.leak * 100)).round(2).to_string())
res["quintiles"] = Q.round(5).reset_index().to_dict("records")
sp = M[M.q == 5].groupby("year").rel252.mean() - M[M.q == 1].groupby("year").rel252.mean()
sp = sp.dropna()
res["q5_minus_q1_rel252"] = {"mean_pct": round(100 * sp.mean(), 2), "t": round(float(sp.mean() / (sp.std(ddof=1) / math.sqrt(len(sp)))), 2), "years": int(len(sp)),
                             "by_year_pct": {int(k): round(100 * v, 1) for k, v in sp.items()}}
print("\nhigh-leak minus low-leak, 252-session return vs the rest:", res["q5_minus_q1_rel252"])
json.dump(res, open(os.path.join(HOME, "leak_blur_results.json"), "w", encoding="utf-8"), indent=1, default=str)
print("\nwritten", os.path.join(HOME, "leak_blur_results.json"))
