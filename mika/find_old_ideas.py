"""One-off search (Oct 13 2026): where do the older ideas live - the main brain / mini-brain spawner,
the living library, the website layer? Writes D:\\planet\\mika\\old_ideas_hits.json."""
import os, re, json, zipfile, time, sys
ROOTS = [r"C:\Users\GamerTech\Shovelcat-AI", r"D:\shovelcat-colony", r"D:\shovelcat-network", r"C:\Users\GamerTech\Shovelcat-Club",
         r"C:\Users\GamerTech\Shovelcat-DNA", r"C:\Users\GamerTech\boys-colony", r"C:\Users\GamerTech\structural-reasoning",
         r"C:\Users\GamerTech\Desktop\Vesica AI", r"C:\Users\GamerTech\shovelcat", r"C:\Users\GamerTech\.shovelcat", r"D:\Shovelcat",
         r"C:\Users\GamerTech\Downloads", r"C:\Users\GamerTech\OneDrive\Desktop", r"C:\Users\GamerTech\Documents"]
SKIP = {"node_modules", ".git", ".next", "dist", "dist-galaxy", ".venv", "venv", "__pycache__", "release", "cache", "win-unpacked", "kohya_ss", "SteamLibrary"}
PATS = {"living_library": re.compile(r"living[\s_-]*library", re.I),
        "mini_brain": re.compile(r"mini[\s_-]*brains?", re.I),
        "main_brain": re.compile(r"main[\s_-]*brain", re.I),
        "spawner": re.compile(r"\bspawn(er|s|ing|ed)?\b", re.I),
        "library_alive": re.compile(r"library (that|which) (is )?(alive|lives|grows|learns)|alive library|library is alive", re.I)}
TEXT = {".md", ".txt", ".ts", ".tsx", ".js", ".py", ".json", ".tex", ".html", ".geo", ".yml", ".yaml"}
hits = {}; t0 = time.time(); n = 0
def note(path, text):
    for k, p in PATS.items():
        ms = list(p.finditer(text))
        if ms:
            h = hits.setdefault(path, {})
            m = ms[0]; s = max(0, m.start() - 160); e = min(len(text), m.end() + 220)
            h[k] = {"count": len(ms), "snippet": re.sub(r"\s+", " ", text[s:e])}
for root in ROOTS:
    if not os.path.isdir(root): continue
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".") or d == ".shovelcat"]
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower(); p = os.path.join(dp, fn)
            try:
                sz = os.path.getsize(p)
                if ext in TEXT and sz < 3_000_000:
                    with open(p, encoding="utf-8", errors="ignore") as fh: note(p, fh.read()); n += 1
                elif ext == ".docx" and sz < 30_000_000:
                    with zipfile.ZipFile(p) as z: x = z.read("word/document.xml").decode("utf-8", "ignore")
                    note(p, re.sub(r"<[^>]+>", " ", x)); n += 1
            except Exception: pass
json.dump({"scanned": n, "seconds": round(time.time() - t0), "hits": hits}, open(r"D:\planet\mika\old_ideas_hits.json", "w", encoding="utf-8"), indent=1)
print("done", n, len(hits), round(time.time() - t0))
