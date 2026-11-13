r"""Vortex test, step 1: tax figures for the ~520 companies (SEC XBRL company facts), cached per company."""
import json, os, time, urllib.request
HOME = r"D:\planet\mika\vortex"
H = {"User-Agent": "Shovelcat Research shovelcat.ai", "Accept": "*/*", "Accept-Encoding": "identity"}
KEEP = ["IncomeTaxesPaidNet", "IncomeTaxesPaid",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeTaxExpenseBenefit", "Assets"]
meta = {}
for d in [r"D:\planet\mika\cube", r"D:\planet\mika\cube2"]:
    meta.update(json.load(open(os.path.join(d, "companies.json"), encoding="utf-8")))
json.dump(meta, open(os.path.join(HOME, "companies.json"), "w", encoding="utf-8"), indent=1)
print("companies:", len(meta), flush=True)
for t, m in sorted(meta.items()):
    out = os.path.join(HOME, "sec", f"{t}.json")
    if os.path.exists(out): continue
    for k in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(m['cik']):010d}.json", headers=H), timeout=60)
            g = json.loads(r.read()).get("facts", {}).get("us-gaap", {}); break
        except Exception as e:
            g = None; time.sleep(2 + 3 * k)
    if g is None: print(t, "failed", flush=True); continue
    keep = {c: g[c]["units"].get("USD", []) for c in KEEP if c in g}
    json.dump({"meta": m, "facts": keep}, open(out, "w", encoding="utf-8"))
    print(t, {c[:22]: len(v) for c, v in keep.items()}, flush=True)
    time.sleep(0.12)
print("all done", flush=True)
