"""Fresh companies for a clean re-test: the current S&P 500 (Wikipedia list) minus the 148 already used.
Also keeps each member's GICS sector and CIK (handy later for the cube's side faces)."""
import json, os, re, urllib.request
import pandas as pd
req = urllib.request.Request("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers={"User-Agent": "Shovelcat Research shovelcat.ai"})
html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
tbl = html[html.index('id="constituents"'):]; tbl = tbl[:tbl.index("</table>")]
strip = lambda s: re.sub(r"<[^>]+>", "", s).strip()
members = []
for row in tbl.split("<tr")[2:]:
    cells = [strip(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
    if len(cells) >= 7: members.append({"ticker": cells[0].upper().replace(".", "-"), "name": cells[1], "sector": cells[2], "cik": cells[6]})
used = set(pd.read_csv(r"D:\planet\mika\trading_backtest_rows.csv")["ticker"].str.upper())
fresh = sorted({m["ticker"] for m in members} - used)
os.makedirs(r"D:\planet\mika\cube2", exist_ok=True)
open(r"D:\planet\mika\cube2\tickers.txt", "w").write("\n".join(fresh))
json.dump(members, open(r"D:\planet\mika\cube\sp500_members.json", "w", encoding="utf-8"), indent=1)
print(len(members), "in the S&P 500 list;", len(fresh), "not used before; e.g.", fresh[:8])
