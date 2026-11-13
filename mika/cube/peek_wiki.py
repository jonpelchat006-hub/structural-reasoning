import urllib.request
h = urllib.request.urlopen(urllib.request.Request("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers={"User-Agent": "Shovelcat Research shovelcat.ai"}), timeout=60).read().decode("utf-8")
i = h.find('id="constituents"'); print(len(h), i)
s = h[i:i + 6000]; j = s.find("<tr"); j = s.find("<tr", j + 5); print(repr(s[j:j + 900]))
try:
    import lxml; print("lxml ok")
except Exception as e: print("no lxml", e)

