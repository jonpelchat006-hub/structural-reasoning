"""One-off (Oct 13 2026): how much would each candidate source add to the library?"""
import os, sys, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
EXT = {".csv", ".docx", ".geo", ".html", ".js", ".json", ".jsx", ".md", ".pdf", ".py", ".tex", ".ts", ".tsx", ".txt", ".yaml", ".yml"}
SKIP = {"node_modules", ".git", "__pycache__", "dist", "dist-galaxy", ".next", ".venv", "venv", "env", "site-packages", "release", "win-unpacked", "cache", ".cache"}
ROOTS = sys.argv[1:]
for root in ROOTS:
    n = 0; b = 0; ext = Counter(); top = Counter(); big = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
        for fn in fns:
            e = os.path.splitext(fn)[1].lower()
            if e not in EXT: continue
            try: s = os.path.getsize(os.path.join(dp, fn))
            except Exception: continue
            if s > 25e6 or s < 40: big += s > 25e6; continue
            n += 1; b += s; ext[e] += 1
            rel = os.path.relpath(dp, root).split(os.sep)[0]
            top[rel] += 1
    print(f"{root}: {n} files, {b/1e6:.0f} MB, too big {big} | " + ", ".join(f"{k} {v}" for k, v in ext.most_common(6)))
    print("    top dirs: " + ", ".join(f"{k} {v}" for k, v in top.most_common(8)))
