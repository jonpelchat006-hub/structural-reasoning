r"""Market cube, step 1: public data for the 149 companies of the Oct 14 trading test.
SEC XBRL company facts (only the concepts the leak test needs), SIC codes, and daily prices 2010-2026.
Everything is cached in D:\planet\mika\cube so the analysis can be re-run offline."""
import json, os, time, urllib.request
import pandas as pd

HOME = os.environ.get("CUBE_HOME", r"D:\planet\mika\cube")
UA = {"User-Agent": "Shovelcat Research shovelcat.ai"}
KEEP = ["NetIncomeLoss", "ProfitLoss", "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", "Assets", "AccountsReceivableNetCurrent",
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax"]
os.makedirs(os.path.join(HOME, "sec"), exist_ok=True)


def get(url):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return json.loads(r.read())
        except Exception as e:
            err = e; time.sleep(2 + 3 * k)
    raise err


tickers = (sorted(open(os.environ["CUBE_TICKERS"]).read().split()) if os.environ.get("CUBE_TICKERS")
           else sorted(pd.read_csv(r"D:\planet\mika\trading_backtest_rows.csv")["ticker"].unique()))
m = get("https://www.sec.gov/files/company_tickers.json")
cik_of = {v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in m.values()}
meta, missing = {}, []
for t in tickers:
    cik = cik_of.get(t.replace(".", "-"))
    if not cik: missing.append(t); continue
    out = os.path.join(HOME, "sec", f"{t}.json")
    if os.path.exists(out): meta[t] = json.load(open(out, encoding="utf-8"))["meta"]; continue
    try:
        facts = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
        time.sleep(0.15)
        sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        time.sleep(0.15)
    except Exception as e:
        print(t, "fetch failed:", e); missing.append(t); continue
    g = facts.get("facts", {}).get("us-gaap", {})
    keep = {c: g[c]["units"].get("USD", []) for c in KEEP if c in g}
    mt = {"cik": cik, "name": facts.get("entityName"), "sic": sub.get("sic"), "sic_desc": sub.get("sicDescription")}
    json.dump({"meta": mt, "facts": keep}, open(out, "w", encoding="utf-8"))
    meta[t] = mt
    print(t, mt["name"], mt["sic"], {c: len(v) for c, v in keep.items()}, flush=True)
json.dump(meta, open(os.path.join(HOME, "companies.json"), "w", encoding="utf-8"), indent=1)
print("SEC done:", len(meta), "companies; missing", missing, flush=True)

px_path = os.path.join(HOME, "prices_2010_2026.pkl")
if not os.path.exists(px_path):
    import yfinance as yf
    px = yf.download(sorted(meta) + ["SPY"], start="2010-01-01", end="2026-10-14", auto_adjust=True,
                     group_by="ticker", progress=False, threads=True)
    px.to_pickle(px_path)
    print("prices:", px.shape, flush=True)
print("all done", flush=True)
