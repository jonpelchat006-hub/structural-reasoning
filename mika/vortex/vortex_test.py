r"""Vortex test, step 2 (claims in PREREGISTERED.md): does money that avoids the authority face (a low long-run
cash tax rate) come before a sudden break (crash risk) in the following year?"""
import glob, json, math, os
import numpy as np, pandas as pd

HOME = r"D:\planet\mika\vortex"
PAID = ["IncomeTaxesPaidNet", "IncomeTaxesPaid"]
PRE = ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
       "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]


def annual(entries):
    out = {}
    for e in entries:
        if e.get("form") not in ("10-K", "10-K/A", "10-KT") or "start" not in e: continue
        if not 340 <= (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days <= 380: continue
        if e["end"] not in out or e["filed"] < out[e["end"]][1]: out[e["end"]] = (float(e["val"]), e["filed"])
    return out


def merged(facts, names, fn):
    m = {}
    for n in names:
        for k, v in fn(facts.get(n, [])).items(): m.setdefault(k, v)
    return m


def near(series, date, lo, hi):
    best = None
    for k, (v, f) in series.items():
        dd = (pd.Timestamp(k) - date).days
        if lo <= dd <= hi and (best is None or abs(dd - (lo + hi) / 2) < abs(best[0] - (lo + hi) / 2)): best = (dd, v)
    return None if best is None else best[1]


def instant(entries):
    out = {}
    for e in entries:
        if e["end"] not in out or e["filed"] < out[e["end"]][1]: out[e["end"]] = (float(e["val"]), e["filed"])
    return out


rows = []
for f in sorted(glob.glob(os.path.join(HOME, "sec", "*.json"))):
    t = os.path.basename(f)[:-5]; d = json.load(open(f, encoding="utf-8")); fa, meta = d["facts"], d["meta"]
    sic = int(meta.get("sic") or 0)
    if 6000 <= sic <= 6999 or 4900 <= sic <= 4999: continue
    paid, pre, assets = merged(fa, PAID, annual), merged(fa, PRE, annual), instant(fa.get("Assets", []))
    gaap = annual(fa.get("IncomeTaxExpenseBenefit", []))
    for end, (pv, filed) in pre.items():
        E, F = pd.Timestamp(end), pd.Timestamp(filed)
        if not 20 <= (F - E).days <= 120 or end not in paid: continue
        P = [pv, near({k: v for k, v in pre.items()}, E, -385, -345), near(pre, E, -750, -710)]
        T = [paid[end][0], near(paid, E, -385, -345), near(paid, E, -750, -710)]
        if any(x is None for x in P + T) or sum(P) <= 0: continue
        a = near(assets, E, -5, 5)
        g = gaap.get(end, (None,))[0]
        rows.append({"ticker": t, "sic2": sic // 100, "fy_end": end, "filed": filed, "cetr3": min(max(sum(T) / sum(P), 0), 1),
                     "getr": min(max(g / pv, 0), 1) if g is not None and pv > 0 else np.nan, "size": math.log(a) if a and a > 0 else np.nan})
X = pd.DataFrame(rows)
X["year"] = pd.to_datetime(X.filed).dt.year
def adj(g):
    out = g.cetr3.copy()
    for s, gg in g.groupby("sic2"):
        if len(gg) >= 5: out[gg.index] = gg.cetr3 - gg.cetr3.median()
        else: out[gg.index] = gg.cetr3 - g.cetr3.median()
    return out
X["avoid"] = -pd.concat([adj(g) for _, g in X.groupby("year")])
print(f"reports with a 3-year cash tax rate: {len(X)} from {X.ticker.nunique()} companies, filed {X.year.min()}-{X.year.max()}; "
      f"median cash tax rate {X.cetr3.median():.3f}")

C = []
for d in [r"D:\planet\mika\cube", r"D:\planet\mika\cube2"]:
    px = pd.read_pickle(os.path.join(d, "prices_2010_2026.pkl"))
    C.append(pd.DataFrame({t: px[t]["Close"] for t in px.columns.get_level_values(0).unique()}))
C = pd.concat(C, axis=1); C = C.loc[:, ~C.columns.duplicated()].sort_index(); C.index = pd.DatetimeIndex(C.index).tz_localize(None)
Wk = C.resample("W-FRI").last().pct_change(fill_method=None)
m = Wk["SPY"]; weeks = Wk.index


def crash_stats(r):
    """firm-specific weekly returns: residuals on SPY at lags -1, 0, +1; returns NCSKEW, DUVOL, CRASH"""
    df = pd.DataFrame({"r": r, "m0": m.reindex(r.index), "m1": m.shift(1).reindex(r.index), "mf": m.shift(-1).reindex(r.index)}).dropna()
    if len(df) < 40: return None
    Z = np.column_stack([np.ones(len(df)), df.m1, df.m0, df.mf])
    e = df.r.values - Z @ np.linalg.lstsq(Z, df.r.values, rcond=None)[0]
    w = np.log1p(e); n = len(w); w0 = w - w.mean()
    ncskew = -(n * (n - 1) ** 1.5 * (w0 ** 3).sum()) / ((n - 1) * (n - 2) * ((w0 ** 2).sum()) ** 1.5)
    dn, up = w0[w0 < 0], w0[w0 >= 0]
    duvol = math.log(((len(up) - 1) * (dn ** 2).sum()) / ((len(dn) - 1) * (up ** 2).sum())) if len(dn) > 2 and len(up) > 2 else np.nan
    return ncskew, duvol, int((w0 < -3.09 * w.std(ddof=1)).any())


out = []
for r in X.itertuples():
    if r.ticker not in Wk.columns: continue
    i = int(np.searchsorted(weeks.values, np.datetime64(pd.Timestamp(r.filed) + pd.Timedelta(days=1))))
    if i < 53 or i + 53 > len(weeks): continue                     # week i holds the filing; the year after starts at i+1
    post = crash_stats(Wk[r.ticker].iloc[i + 1:i + 53]); prev = crash_stats(Wk[r.ticker].iloc[i - 52:i])
    if post is None or prev is None: continue
    rec = r._asdict(); rec.pop("Index", None)
    rec.update(ncskew=post[0], duvol=post[1], crash=post[2], ncskew_pre=prev[0], duvol_pre=prev[1], crash_pre=prev[2])
    out.append(rec)
E = pd.DataFrame(out); E.to_csv(os.path.join(HOME, "vortex_events.csv"), index=False)
print(f"events with a full year after: {len(E)}, years {E.year.min()}-{E.year.max()}, crash rate {E.crash.mean():.3f}")


def yearly(a, b, df=None, min_n=25):
    df = E if df is None else df
    v = np.array([g[a].rank().corr(g[b].rank()) for _, g in df.dropna(subset=[a, b]).groupby("year") if len(g) >= min_n])
    return {"years": len(v), "rank_corr": round(float(v.mean()), 3), "t": round(float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), 2),
            "same_sign": int((np.sign(v) == np.sign(v.mean())).sum())}


def joint(y, xs, min_n=25):
    co = []
    for _, g in E.dropna(subset=[y] + xs).groupby("year"):
        if len(g) < min_n: continue
        z = lambda s: (s.rank() - s.rank().mean()) / s.rank().std()
        Z = np.column_stack([np.ones(len(g))] + [z(g[x]) for x in xs])
        co.append(np.linalg.lstsq(Z, z(g[y]).values, rcond=None)[0][1:])
    co = np.array(co)
    return {x: {"slope": round(float(co[:, j].mean()), 3), "t": round(float(co[:, j].mean() / (co[:, j].std(ddof=1) / math.sqrt(len(co)))), 2)} for j, x in enumerate(xs)}


res = {"events": int(len(E)), "companies": int(E.ticker.nunique()), "crash_rate": round(float(E.crash.mean()), 3)}
res["1_avoid_ncskew"] = yearly("avoid", "ncskew"); res["2_avoid_duvol"] = yearly("avoid", "duvol")
E["q"] = E.groupby("year").avoid.transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) + 1 if len(s) >= 25 else np.nan)
cq = E.groupby(["year", "q"]).crash.mean().unstack()
diff = (cq[5] - cq[1]).dropna()
res["3_crash_top_vs_bottom"] = {"crash_rate_by_quintile": E.groupby("q").crash.mean().round(3).to_dict(), "top_minus_bottom": round(float(diff.mean()), 3),
                                "t": round(float(diff.mean() / (diff.std(ddof=1) / math.sqrt(len(diff)))), 2), "years": int(len(diff))}
res["4_joint_ncskew"] = joint("ncskew", ["avoid", "ncskew_pre", "size"])
res["side_gaap_rate_ncskew"] = yearly("getr", "ncskew"); res["side_persistence_ncskew"] = yearly("ncskew_pre", "ncskew")
for k, v in res.items(): print(k, ":", v)
json.dump(res, open(os.path.join(HOME, "vortex_results.json"), "w"), indent=1, default=str)
