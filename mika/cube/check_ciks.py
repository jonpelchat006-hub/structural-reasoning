"""company_tickers.json can list a ticker more than once (parent and subsidiary); the first entry is the listed
parent. Compare with what cube_fetch.py used and refetch any company that got the wrong filer."""
import json, os, urllib.request
HOME = r"D:\planet\mika\cube"
UA = {"User-Agent": "Shovelcat Research shovelcat.ai"}
m = json.loads(urllib.request.urlopen(urllib.request.Request("https://www.sec.gov/files/company_tickers.json", headers=UA), timeout=60).read())
first, allc = {}, {}
for v in m.values():
    t = v["ticker"].upper().replace(".", "-")
    first.setdefault(t, (int(v["cik_str"]), v["title"])); allc.setdefault(t, []).append((int(v["cik_str"]), v["title"]))
meta = json.load(open(os.path.join(HOME, "companies.json"), encoding="utf-8"))
bad = []
for t, mt in meta.items():
    if len(allc.get(t, [])) > 1: print(t, "listed", allc[t])
    if first.get(t, (None,))[0] != mt["cik"]:
        bad.append(t); print("WRONG FILER", t, "used", mt["cik"], mt["name"], "-> should be", first.get(t))
for t in bad: os.remove(os.path.join(HOME, "sec", f"{t}.json"))
print("to refetch:", bad)
