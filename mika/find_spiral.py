"""One-off search (Oct 13 2026): where is the 'spiral drive' and the void search? Prints hits."""
import os, re, zipfile, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOTS = [r"C:\Users\GamerTech\Shovelcat-AI", r"D:\shovelcat-colony", r"D:\shovelcat-network", r"C:\Users\GamerTech\Shovelcat-Club",
         r"C:\Users\GamerTech\Shovelcat-DNA", r"C:\Users\GamerTech\boys-colony", r"C:\Users\GamerTech\structural-reasoning",
         r"C:\Users\GamerTech\Desktop\Vesica AI", r"C:\Users\GamerTech\shovelcat", r"C:\Users\GamerTech\.shovelcat", r"D:\Shovelcat",
         r"C:\Users\GamerTech\Downloads", r"C:\Users\GamerTech\OneDrive\Desktop", r"C:\Users\GamerTech\Documents", r"D:\planet", r"D:\boys-colony"]
SKIP = {"node_modules", ".git", ".next", "dist", "dist-galaxy", ".venv", "venv", "__pycache__", "release", "cache", "win-unpacked"}
P = re.compile(r"spiral[\s_-]*(drive|disk|storage|store|layout|librar\w*|index|address)|drive[\s_-]*spiral|spiral_?drive|SpiralDrive|void[\s_-]*search|voidsearch", re.I)
TEXT = {".md", ".txt", ".ts", ".tsx", ".js", ".py", ".json", ".tex", ".html", ".yml"}
hits = {}
for root in ROOTS:
    if not os.path.isdir(root): continue
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower(); p = os.path.join(dp, fn)
            if re.search(r"spiral|voidsearch|void_search", fn, re.I): hits.setdefault(p, []).append("NAME")
            try:
                if ext in TEXT and os.path.getsize(p) < 3_000_000:
                    t = open(p, encoding="utf-8", errors="ignore").read()
                elif ext == ".docx" and os.path.getsize(p) < 30_000_000:
                    with zipfile.ZipFile(p) as z: t = re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8", "ignore"))
                else: continue
            except Exception: continue
            for m in list(P.finditer(t))[:2]:
                s = max(0, m.start() - 120); e = min(len(t), m.end() + 160)
                hits.setdefault(p, []).append(re.sub(r"\s+", " ", t[s:e]))
for p, h in sorted(hits.items()):
    print("##", p); [print("   ", x[:300]) for x in h[:2]]
print("TOTAL", len(hits))
