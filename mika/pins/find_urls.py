import re, urllib.request
UA = {"User-Agent": "Shovelcat Research shovelcat.ai"}
for u in ["https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
          "https://www.sec.gov/dera/data/form-345"]:
    try:
        h = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
        links = sorted(set(re.findall(r'href="([^"]+\.zip)"', h)))
        print(u, "->", len(links), "zip links"); print("\n".join(links[:5])); print("..."); print("\n".join(links[-5:]))
        break
    except Exception as e:
        print(u, "ERR", e)
