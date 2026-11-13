import urllib.request
u = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2024q1_form345.zip"
for h in [{"User-Agent": "Shovelcat Research shovelcat.ai", "Accept": "*/*", "Accept-Encoding": "gzip, deflate"},
          {"User-Agent": "Shovelcat Research shovelcat.ai", "Referer": "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"},
          {"User-Agent": "Shovelcat Research shovelcat.ai", "Range": "bytes=0-1023"}]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=h, method="HEAD"), timeout=30)
        print("OK", r.status, r.headers.get("Content-Length"), list(h))
    except Exception as e:
        print("ERR", e, list(h))
