"""Spot-check: 2 random classified events against the original Form 4 XML on EDGAR, and one return window by hand."""
import json, re, time, urllib.request
import numpy as np, pandas as pd
H = {"User-Agent": "Shovelcat Research shovelcat.ai", "Accept": "*/*", "Accept-Encoding": "identity"}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read().decode("utf-8", "replace")
E = pd.read_csv(r"D:\planet\mika\pins\pins_events.csv", dtype={"RPTOWNERCIK": str})
T = pd.read_csv(r"D:\planet\mika\pins\insider_trades.csv", dtype=str)
T["fd"] = pd.to_datetime(T.FILING_DATE, format="%d-%b-%Y", errors="coerce")
rng = np.random.default_rng(16)
for k in rng.choice(len(E), 2, replace=False):
    e = E.iloc[k]
    lines = T[(T.ticker == e.ticker) & (T.RPTOWNERCIK == e.RPTOWNERCIK) & (T.fd == pd.Timestamp(e.fd)) & (T.TRANS_CODE == ("P" if e.dir == 1 else "S"))]
    acc = lines.ACCESSION_NUMBER.iloc[0]; cik = int(lines.cik.iloc[0])
    print(f"\n{e.ticker} {e['name']} {('buy' if e.dir == 1 else 'sell')} filed {e.fd[:10]} trade {e.td[:10]} kind {e.kind} | ours: {len(lines)} line(s), "
          f"shares {pd.to_numeric(lines.TRANS_SHARES).sum():,.0f}, accession {acc}")
    idx = json.loads(get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/index.json"))
    xml = [f["name"] for f in idx["directory"]["item"] if f["name"].endswith(".xml")][0]
    time.sleep(0.3); x = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{xml}")
    nd = x.split("<nonDerivativeTable>")[1].split("</nonDerivativeTable>")[0] if "<nonDerivativeTable>" in x else ""
    for t in re.findall(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>", nd, re.S):
        code = re.search(r"<transactionCode>(\w)</transactionCode>", t); sh = re.search(r"<transactionShares>\s*<value>([\d.]+)", t)
        dt = re.search(r"<transactionDate>\s*<value>([\d-]+)", t)
        print(f"   EDGAR line: date {dt.group(1) if dt else '?'} code {code.group(1) if code else '?'} shares {sh.group(1) if sh else '?'}")
    time.sleep(0.3)
e = E.dropna(subset=["rel126"]).iloc[1000]
px = pd.concat([pd.read_pickle(r"D:\planet\mika\cube\prices_2010_2026.pkl"), pd.read_pickle(r"D:\planet\mika\cube2\prices_2010_2026.pkl")], axis=1)
c = px[e.ticker]["Close"]; c = c.loc[:, ~c.columns.duplicated()].iloc[:, 0] if isinstance(c, pd.DataFrame) else c
c.index = pd.DatetimeIndex(c.index).tz_localize(None)
i = int(np.searchsorted(c.index.values, np.datetime64(pd.Timestamp(e.fd) + pd.Timedelta(days=1))))
print(f"\nwindow check {e.ticker} filed {e.fd[:10]}: entry {c.index[i].date()} close {c.iloc[i]:.2f} -> {c.index[i + 126].date()} close {c.iloc[i + 126]:.2f}; "
      f"stock {100 * (c.iloc[i + 126] / c.iloc[i] - 1):+.2f}%, file rel126 {100 * e.rel126:+.2f}% (= stock minus the average)")
