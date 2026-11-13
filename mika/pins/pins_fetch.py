r"""Bent pins, step 1: open-market insider buys (P) and sells (S) from the SEC's quarterly Form 3/4/5 data sets,
kept only for the ~520 companies whose prices are cached in D:\planet\mika\cube and cube2.
Output: D:\planet\mika\pins\insider_trades.csv (one row per transaction line)."""
import csv, gzip, io, json, os, time, urllib.request, zipfile
import pandas as pd

HOME = r"D:\planet\mika\pins"
H = {"User-Agent": "Shovelcat Research shovelcat.ai", "Accept": "*/*", "Accept-Encoding": "gzip, deflate"}
BASE = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{}q{}_form345.zip"
BASE2 = "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/{}q{}_form345.zip"

cik_ticker = {}
for d in [r"D:\planet\mika\cube", r"D:\planet\mika\cube2"]:
    for t, m in json.load(open(os.path.join(d, "companies.json"), encoding="utf-8")).items(): cik_ticker[int(m["cik"])] = t
print("companies:", len(cik_ticker), flush=True)


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=180); b = r.read()
    return gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b


def tsv(z, name, cols):
    with z.open(name) as f:
        d = pd.read_csv(f, sep="\t", dtype=str, usecols=lambda c: c in cols, quoting=csv.QUOTE_NONE, encoding="latin-1", on_bad_lines="skip")
    for c in cols:
        if c not in d.columns: d[c] = None                        # older quarters lack AFF10B5ONE
    return d[cols]


out_path = os.path.join(HOME, "insider_trades.csv"); first = not os.path.exists(out_path)
done = set(open(os.path.join(HOME, "done.txt")).read().split()) if os.path.exists(os.path.join(HOME, "done.txt")) else set()
for y in range(2011, 2027):
    for q in range(1, 5):
        tag = f"{y}q{q}"
        if tag in done or (y == 2026 and q == 4): continue
        b = None
        for base in (BASE, BASE2):
            try: b = get(base.format(y, q)); break
            except Exception as e: err = e
        if b is None: print(tag, "not available:", err, flush=True); continue
        z = zipfile.ZipFile(io.BytesIO(b))
        s = tsv(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"])
        s = s[s.DOCUMENT_TYPE.isin(["4", "4/A"])].copy()
        s["cik"] = pd.to_numeric(s.ISSUERCIK, errors="coerce")
        s = s[s.cik.isin(cik_ticker.keys())]
        o = tsv(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"])
        o = o.drop_duplicates("ACCESSION_NUMBER", keep="first")          # joint filings: one pin per filing
        t = tsv(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
        t = t[t.TRANS_CODE.isin(["P", "S"])]
        m = t.merge(s, on="ACCESSION_NUMBER").merge(o, on="ACCESSION_NUMBER", how="left")
        m["ticker"] = m.cik.astype(int).map(cik_ticker)
        m["quarter"] = tag
        m.drop(columns=["ISSUERCIK"]).to_csv(out_path, mode="a", header=first, index=False); first = False
        open(os.path.join(HOME, "done.txt"), "a").write(tag + "\n")
        print(tag, f"{len(b) / 1e6:.0f} MB", "filings kept", len(s), "P/S lines kept", len(m), flush=True)
        time.sleep(0.5)
print("all done", flush=True)
