import io, time, urllib.request, zipfile
u = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2024q1_form345.zip"
t = time.time(); b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Shovelcat Research shovelcat.ai"}), timeout=120).read()
print("MB", round(len(b) / 1e6, 1), "s", round(time.time() - t, 1))
z = zipfile.ZipFile(io.BytesIO(b)); print(z.namelist())
for n in ["SUBMISSION.tsv", "REPORTINGOWNER.tsv", "NONDERIV_TRANS.tsv"]:
    with z.open(n) as f:
        print(n, f.readline().decode().strip().split("\t")); print("   ", f.readline().decode()[:300])
