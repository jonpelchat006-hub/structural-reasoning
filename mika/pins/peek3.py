import gzip, io, time, urllib.request, zipfile
u = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2024q1_form345.zip"
H = {"User-Agent": "Shovelcat Research shovelcat.ai", "Accept": "*/*", "Accept-Encoding": "gzip, deflate"}
t = time.time(); r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=120); b = r.read()
if r.headers.get("Content-Encoding") == "gzip": b = gzip.decompress(b)
print("MB", round(len(b) / 1e6, 1), "s", round(time.time() - t, 1), "enc", r.headers.get("Content-Encoding"))
z = zipfile.ZipFile(io.BytesIO(b)); print(z.namelist())
for n in ["SUBMISSION.tsv", "REPORTINGOWNER.tsv", "NONDERIV_TRANS.tsv"]:
    with z.open(n) as f:
        print(n, f.readline().decode().strip().split("\t")); print("   ", f.readline().decode()[:400])
