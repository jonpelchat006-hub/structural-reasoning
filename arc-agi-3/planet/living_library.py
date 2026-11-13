#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
living_library.py - MIKA'S LIVING LIBRARY: library (raw) -> brain (digested) -> spiral drive (organized) -> void search.

Jonathan, Oct 13 2026: "the library was for the raw files but then the brain could be the digested files. and
then maybe the spiral drive would be the organized version of the library? and once its on the spiral drive the
void search method we had in the project could find things easier?"

  LIBRARY  D:\shovelcat-colony\companion\library          the raw files (DNA). Never edited here; `ingest` copies
                                                          new or changed files in from the sources you list.
  BRAIN    D:\shovelcat-colony\brain\library\<id>.json    one digest per raw file: title, summary, outline,
                                                          key terms, mentions, twins. Rewritten in place when the
                                                          raw file changes, so nothing piles up.
  SPIRAL   D:\shovelcat-network\<zone>\library\armNN\<id>.json   the organized library. Every digest gets an address:
             angle  = WHAT it is about. The void search's domain tree (recursive Fiedler cuts) lays the domains
                      around the circle; seam files sit on the boundaries between domains.
             radius = HOW HOT it is. Heat = search hits + how connected it is + how recent. Hottest at the centre.
             The zone follows the radius with spiral-drive.ts's Fibonacci areas (L0 1/54 ... L7 21/54) and its
             arm counts per zone (1,1,2,3,5,8,13,21). The angle comes from the void search, not the golden angle.
           L0-origin\library-index.json = the hot map; L4-spacetime\library\signatures.npz = the search vectors;
           L1-time\library-heat.json = the hits.
  SEARCH   the void search (planet/voidsearch.py) over the spiral: tf-idf atoms -> kNN contact graph -> Fiedler
           void lines. Each result comes with its domain, its seam distance (near 0 = a bridge between domains),
           its zone and arm, and its nearest neighbours one hop down the void line. Each hit warms the file, so
           what gets used moves inward.

Usage:
  python living_library.py sync                    digest changed files, rebuild the spiral, write the index
  python living_library.py search "spiral storage" [--k 8] [--json] [--no-heat]
  python living_library.py ingest                  copy new/changed files from D:\planet\mika\library_sources.json, then sync
  python living_library.py stats
  python living_library.py crystallize --top 20    local-model summaries for the hottest files (optional, slow)
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shutil, sys, time, zipfile
from collections import Counter
import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)      # pypdf warns once per font; the library has 59 PDFs

WIN = os.name == "nt"
LIBRARY = r"D:\shovelcat-colony\companion\library" if WIN else "/tmp/ll/library"
BRAIN = r"D:\shovelcat-colony\brain\library" if WIN else "/tmp/ll/brain"
NETWORK = r"D:\shovelcat-network" if WIN else "/tmp/ll/network"
SOURCES = r"D:\planet\mika\library_sources.json" if WIN else "/tmp/ll/sources.json"
ZONES = ["L0-origin", "L1-time", "L2-plane", "L3-space", "L4-spacetime", "L5-facts", "L6-memory", "L7-imagination"]
FIB = [1, 1, 2, 3, 5, 8, 13, 21]
ARMS = FIB                                      # arms per zone, as in spiral-drive.ts
TEXT_EXT = {".md", ".txt", ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".tex", ".html", ".yml", ".yaml", ".csv", ".geo"}
DOC_EXT = {".pdf", ".docx"}
MAX_CHARS = 200_000
DIGEST_VERSION = 3                               # 2: PDF/DOCX text kept in brain\library\text; 3: better code titles
STOP = set("the a an and or of to in for is are was were be been with as at by on from this that it its if then else "
           "not no we you i our your they them there here have has had do does did can could will would should may "
           "might must self def return import class true false none null var let const function new export type "
           "string number int str float list dict void any print len range value data".split())


def ipath(*p): return os.path.join(*p)
def zone_dir(z): return ipath(NETWORK, ZONES[z], "library")
INDEX = lambda: ipath(NETWORK, "L0-origin", "library-index.json")
HEAT = lambda: ipath(NETWORK, "L1-time", "library-heat.json")
SIGS = lambda: ipath(NETWORK, "L4-spacetime", "library", "signatures.npz")


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as fh: return json.load(fh)
    except Exception: return default


def save_json(p, obj, indent=1):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh: json.dump(obj, fh, indent=indent)
    os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------ reading
def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in TEXT_EXT:
            with open(path, encoding="utf-8", errors="replace") as fh: return fh.read(MAX_CHARS), "text"
        if ext == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(path); out = []
            for pg in r.pages[:40]:
                try: out.append(pg.extract_text() or "")
                except Exception: pass
                if sum(map(len, out)) > MAX_CHARS: break
            return "\n".join(out)[:MAX_CHARS], "pdf"
        if ext == ".docx":
            with zipfile.ZipFile(path) as z: x = z.read("word/document.xml").decode("utf-8", "ignore")
            x = re.sub(r"</w:p>", "\n", x)
            return re.sub(r"<[^>]+>", "", x)[:MAX_CHARS], "docx"
    except Exception:
        return "", "unreadable"
    return "", "binary"


def tokens(s):
    """atoms: whole identifiers, plus their parts (mini_brain_spawner -> mini, brain, spawner; spiralSearch -> spiral, search)"""
    out = []
    for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", s):
        tl = t.lower()
        if tl not in STOP and not tl.isdigit(): out.append(tl)
        if "_" in t or re.search(r"[a-z][A-Z]", t):
            for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", t.replace("_", " ")):
                pl = p.lower()
                if len(pl) >= 3 and pl != tl and pl not in STOP: out.append(pl)
    return out


def title_of(text, fn, ext):
    m = re.search(r"^\s*#\s+(.+)$", text, re.M) if ext in (".md", ".txt", "") else None
    if m: return m.group(1).strip()[:120]
    junk = re.compile(r"copyright|license|coding[:=]|^!|all rights reserved|^author|^@|^(import|export|from|const|let|var|require|package|#include)\b"
                      r"|^[\"']use (client|strict|server)", re.I)
    m = re.search(r'^\s*(?:r|u)?("""|\'\'\')\s*\n?\s*(.+)', text[:4000], re.M)     # python docstring (after any comments)
    if m and not junk.search(m.group(2)): return m.group(2).strip().strip('"\'')[:120]
    m = re.search(r"/\*\*\s*\n?\s*\*?\s*(.+)", text[:4000])                          # /** comment
    if m and not junk.search(m.group(1)): return m.group(1).strip()[:120]
    m = re.search(r"^export\s+default\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", text[:20000], re.M)
    if m and ext in (".tsx", ".jsx", ".ts", ".js"):                                  # a React page or component
        return f"{m.group(1)} ({os.path.splitext(fn)[0]})"
    for line in text.splitlines()[:40]:
        line = line.strip().strip("#*/ -=")
        if len(line) >= 12 and not junk.search(line) and not line.endswith((";", "{", "(")): return line[:120]
    return os.path.splitext(fn)[0]


def summary_of(text):
    body = re.sub(r"[=\-~\u2500-\u257f]{4,}", " ", text[:20000])
    for block in re.split(r"\n\s*\n", body):
        b = re.sub(r"\s+", " ", block).strip(" #*/\"'")
        if len(b) >= 80 and not b.startswith(("import ", "from ", "const ", "export ", "{", "<")):
            return b[:600]
    return re.sub(r"\s+", " ", body).strip()[:300]


def outline_of(text, ext):
    if ext == ".md": return [h.strip()[:90] for h in re.findall(r"^#{1,3}\s+(.+)$", text, re.M)][:25]
    if ext == ".py": return re.findall(r"^(?:class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M)[:30]
    if ext in (".ts", ".tsx", ".js", ".jsx"):
        return re.findall(r"^export\s+(?:async\s+)?(?:function|class|interface|const|type)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M)[:30]
    return []


# ------------------------------------------------------------------------------------------------ the brain
def walk_library():
    for dp, dns, fns in os.walk(LIBRARY):
        dns[:] = [d for d in dns if not d.startswith(".")]
        for fn in fns:
            p = ipath(dp, fn)
            yield p, os.path.relpath(p, LIBRARY)


def digest_all(log=print):
    """library -> brain: one digest per raw file, rewritten only when the raw file changed"""
    os.makedirs(BRAIN, exist_ok=True)
    seen, made, kept = set(), 0, 0
    for p, rel in walk_library():
        did = hashlib.sha1(rel.replace("\\", "/").lower().encode()).hexdigest()[:16]
        seen.add(did)
        dp = ipath(BRAIN, did + ".json")
        st = os.stat(p)
        old = load_json(dp, None)
        if old and old.get("v") == DIGEST_VERSION and old.get("mtime") == int(st.st_mtime) and old.get("size") == st.st_size:
            kept += 1
            continue
        with open(p, "rb") as fh: chash = hashlib.sha1(fh.read()).hexdigest()[:16]
        text, kind = read_text(p)
        ext = os.path.splitext(p)[1].lower()
        d = {"v": DIGEST_VERSION, "id": did, "rel": rel, "raw": p, "kind": kind, "ext": ext, "size": st.st_size,
             "mtime": int(st.st_mtime), "chash": chash, "title": title_of(text, os.path.basename(p), ext) if text else os.path.basename(p),
             "summary": summary_of(text) if text else "", "outline": outline_of(text, ext) if text else [],
             "words": len(tokens(text)) if text else 0, "digested": time.strftime("%Y-%m-%d %H:%M")}
        if old and old.get("crystal") and old.get("chash") == chash: d["crystal"] = old["crystal"]
        if kind in ("pdf", "docx") and text:                       # keep the extracted text in the brain: read once
            os.makedirs(ipath(BRAIN, "text"), exist_ok=True)
            with open(ipath(BRAIN, "text", did + ".txt"), "w", encoding="utf-8") as fh: fh.write(text)
            d["text"] = ipath(BRAIN, "text", did + ".txt")
        save_json(dp, d); made += 1
    gone = 0
    for fn in os.listdir(BRAIN):
        if fn.endswith(".json") and fn[:-5] not in seen:
            os.remove(ipath(BRAIN, fn)); gone += 1
    log(f"brain: {made} digested, {kept} unchanged, {gone} removed (raw file gone) -> {BRAIN}")
    return made + gone


def load_digests():
    out = {}
    for fn in os.listdir(BRAIN):
        if fn.endswith(".json"):
            d = load_json(ipath(BRAIN, fn), None)
            if d: out[d["id"]] = d
    return out


# ------------------------------------------------------------------------------------------------ the void search
def tfidf(docs_counts):
    from scipy import sparse
    n = len(docs_counts)
    df = Counter(t for tk in docs_counts for t in tk)
    vocab = sorted(t for t, c in df.items() if 2 <= c <= max(2, 0.5 * n))
    vi = {t: i for i, t in enumerate(vocab)}
    rows, cols, vals = [], [], []
    for i, tk in enumerate(docs_counts):
        for t, c in tk.items():
            j = vi.get(t)
            if j is not None:
                rows.append(i); cols.append(j); vals.append((1 + math.log(c)) * math.log(n / df[t]))
    M = sparse.csr_matrix((vals, (rows, cols)), shape=(n, len(vocab)), dtype=np.float32)
    norms = np.sqrt(np.asarray(M.multiply(M).sum(1)).ravel()); norms[norms == 0] = 1
    M = sparse.diags(1 / norms).dot(M).tocsr()
    idf = {t: math.log(n / df[t]) for t in vocab}
    return M, vocab, idf


def knn_graph(M, k=8, block=1000):
    """the contact graph: each file joined to its k most similar files (blocked, so the library can grow)"""
    from scipy import sparse
    n = M.shape[0]; MT = M.T.tocsc()
    rows, cols, vals, nbrs = [], [], [], []
    for b0 in range(0, n, block):
        S = (M[b0:b0 + block] @ MT).toarray()
        for r in range(S.shape[0]):
            i = b0 + r; S[r, i] = 0
            kk = min(k, n - 1)
            nn = np.argpartition(-S[r], kk)[:kk]
            nn = nn[np.argsort(-S[r, nn])]
            for j in nn:
                if S[r, j] > 0: rows.append(i); cols.append(int(j)); vals.append(float(S[r, j]))
            nbrs.append([(int(j), float(S[r, j])) for j in nn[:5] if S[r, j] > 0])
    A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    return A.maximum(A.T).tocsr(), nbrs


def components(A):
    from scipy.sparse.csgraph import connected_components
    return connected_components(A, directed=False)


def fiedler(A):
    """the void line through a (sub)graph: the second eigenvector of the normalized adjacency"""
    from scipy import sparse
    d = np.asarray(A.sum(1)).ravel()
    dm = np.where(d > 0, 1 / np.sqrt(np.maximum(d, 1e-12)), 0)
    S = sparse.diags(dm) @ A @ sparse.diags(dm)
    if A.shape[0] <= 2500:
        w, v = np.linalg.eigh(S.toarray()); vec = v[:, -2]
    else:
        from scipy.sparse.linalg import eigsh
        w, v = eigsh(S.tocsc(), k=2, which="LA", tol=1e-6, maxiter=5000); vec = v[:, np.argsort(w)[0]]
    f = vec * dm                                       # random-walk scaling: cleaner sign cut
    return f / (np.abs(f).max() or 1)


def domain_tree(A, M, vocab, idx, path, depth, out, maxdepth=7, minsize=12, leafsize=60, seams=None, seam_set=None):
    """recursive void lines: each cut splits by the Fiedler sign, until a domain holds <= leafsize files; the
    files nearest the line (|f| in the lowest 3% of that cut, on the first three cuts) are the seam - the
    bridge files between two domains"""
    seams = seams if seams is not None else {}
    seam_set = seam_set if seam_set is not None else set()
    sub = A[idx][:, idx]
    if len(idx) < minsize or len(idx) <= leafsize or depth >= maxdepth or sub.sum() == 0:
        out.append((path, idx)); return
    f = fiedler(sub)
    for j, i in enumerate(idx):
        seams.setdefault(int(i), []).append(round(float(abs(f[j])), 3))
    if depth <= 2:
        q = np.quantile(np.abs(f), 0.03)
        seam_set.update(int(i) for j, i in enumerate(idx) if abs(f[j]) <= q)
    a_idx, b_idx = idx[f < 0], idx[f >= 0]
    if len(a_idx) < 3 or len(b_idx) < 3:
        out.append((path, idx)); return
    a_idx = a_idx[np.argsort(f[f < 0])]; b_idx = b_idx[np.argsort(f[f >= 0])]
    domain_tree(A, M, vocab, a_idx, path + "A", depth + 1, out, maxdepth, minsize, leafsize, seams, seam_set)
    domain_tree(A, M, vocab, b_idx, path + "B", depth + 1, out, maxdepth, minsize, leafsize, seams, seam_set)
    return seams


def name_domain(M, vocab, idx, mean_all, n=4, titles=None):
    """a domain is named by the words its own titles use more than the rest of the library's titles do
    (titles say what a file is; body tokens in code are mostly syntax); body terms fill in when titles are thin"""
    words = []
    if titles is not None:
        inside = Counter(t for i in idx for t in set(tokens(titles[i])))
        allc = Counter(t for tl in titles for t in set(tokens(tl)))
        k, nall = len(idx), len(titles)
        sc = {t: c / k - allc[t] / nall for t, c in inside.items() if c >= 2 and len(t) > 3}
        words = [t for t, _ in sorted(sc.items(), key=lambda kv: -kv[1])[:n]]
    if len(words) < n:
        sub = np.asarray(M[idx].mean(0)).ravel()
        for j in np.argsort(-(sub - mean_all)):
            if vocab[j] not in words: words.append(vocab[j])
            if len(words) >= n: break
    return words


# ------------------------------------------------------------------------------------------------ the spiral
def build_spiral(log=print):
    digests = load_digests()
    heat = load_json(HEAT(), {})
    # twins: identical content keeps one canonical copy on the spiral (the shortest path)
    by_hash = {}
    for d in digests.values(): by_hash.setdefault(d["chash"], []).append(d)
    canon, twins = [], {}
    for group in by_hash.values():
        group.sort(key=lambda d: (len(d["rel"]), d["rel"]))
        if group[0].get("words", 0) < 10: continue
        canon.append(group[0]); twins[group[0]["id"]] = [g["rel"] for g in group[1:]]
    ids = [d["id"] for d in canon]
    toks = []
    for d in canon:
        text, _ = read_text(d["text"] if d.get("text") and os.path.exists(d["text"]) else d["raw"])
        toks.append(Counter(tokens(d["title"]) * 3 + tokens(os.path.basename(d["rel"]).replace("-", "_")) * 2 + tokens(text)[:30000]))
    n = len(ids)
    log(f"spiral: {len(digests)} digests, {n} placed ({sum(len(v) for v in twins.values())} twins folded, "
        f"{len(digests) - n - sum(len(v) for v in twins.values())} too small or unreadable)")
    if n < 12: log("spiral: too few documents to cut"); return None
    M, vocab, idf = tfidf(toks)
    A, nbrs = knn_graph(M)
    ncomp, lab = components(A)
    mean_all = np.asarray(M.mean(0)).ravel()
    leaves, seams, seam_set = [], {}, set()
    comps = sorted(range(ncomp), key=lambda c: -int((lab == c).sum()))
    for ci, c in enumerate(comps):
        idx = np.where(lab == c)[0]
        if len(idx) < 3:
            leaves.append((f"iso{ci}", idx)); continue
        domain_tree(A, M, vocab, idx, f"C{ci}.", 0, leaves, seams=seams, seam_set=seam_set)
    # angle = what: leaves in tree order share the circle by size; radius = how hot
    deg = np.asarray(A.sum(1)).ravel(); deg_n = deg / (deg.max() or 1)
    now = time.time()
    rec = np.array([math.exp(-(now - d["mtime"]) / (86400 * 120)) for d in canon])
    hits = np.array([heat.get(i, {}).get("hits", 0) for i in ids], float)
    h = np.log1p(hits) + 0.5 * deg_n + 0.3 * rec
    order = np.argsort(-h)
    sector = np.empty(n, int); sector[order] = np.arange(n)
    cum = np.cumsum(FIB) / sum(FIB)
    theta = np.zeros(n); dom_of = [""] * n; domains = []
    titles = [c["title"] for c in canon]
    start = 0.0
    for path, idx in leaves:
        width = 2 * math.pi * len(idx) / n
        words = name_domain(M, vocab, idx, mean_all, titles=titles) if len(idx) >= 2 else [vocab[j] for j in np.argsort(-M[idx[0]].toarray().ravel())[:3]]
        domains.append({"path": path, "name": " / ".join(words), "size": int(len(idx)), "theta": [round(start, 4), round(start + width, 4)],
                        "examples": [canon[i]["title"][:70] for i in idx[np.argsort(-deg[idx])][:3]]})
        for j, i in enumerate(idx):
            theta[i] = start + (j + 0.5) / len(idx) * width
            dom_of[i] = path
        start += width
    # write the organized library: one manifest per placed file, in its zone and arm
    for z in range(8):
        if os.path.isdir(zone_dir(z)) and z != 4: shutil.rmtree(zone_dir(z), ignore_errors=True)
        elif z == 4 and os.path.isdir(zone_dir(z)):
            for e in os.listdir(zone_dir(z)):
                if e.startswith("arm"): shutil.rmtree(ipath(zone_dir(z), e), ignore_errors=True)
    dom_name = {d["path"]: d["name"] for d in domains}
    items = {}
    for i, d in enumerate(canon):
        k = int(sector[i]); frac = (k + 0.5) / n
        z = int(np.searchsorted(cum, frac))
        arm = int(theta[i] / (2 * math.pi) * ARMS[z]) % ARMS[z]
        r = math.sqrt(frac)
        sm = seams.get(i, [])
        m = {"id": d["id"], "title": d["title"], "rel": d["rel"], "raw": d["raw"], "digest": ipath(BRAIN, d["id"] + ".json"),
             "kind": d["kind"], "words": d["words"], "domain": dom_of[i], "domain_name": dom_name.get(dom_of[i], ""),
             "seam": i in seam_set, "seam_dist": sm, "outlier": bool(deg[i] <= np.quantile(deg, 0.03)),
             "heat": round(float(h[i]), 3), "hits": int(hits[i]), "zone": ZONES[z], "arm": arm, "sector": k,
             "r": round(r, 4), "theta": round(float(theta[i]), 4), "x": round(r * math.cos(theta[i]), 4), "y": round(r * math.sin(theta[i]), 4),
             "neighbors": [{"id": ids[j], "title": canon[j]["title"][:70], "sim": round(sv, 3)} for j, sv in nbrs[i]],
             "twins": twins.get(d["id"], []), "summary": d["summary"][:300]}
        save_json(ipath(zone_dir(z), f"arm{arm:02d}", d["id"] + ".json"), m)
        items[d["id"]] = {"t": d["title"][:90], "rel": d["rel"], "z": z, "a": arm, "k": k, "dom": dom_of[i], "seam": m["seam"]}
    from scipy import sparse
    os.makedirs(os.path.dirname(SIGS()), exist_ok=True)
    tmp_sig = SIGS()[:-4] + ".tmp.npz"                     # write then swap, so a search mid-build never reads half a file
    sparse.save_npz(tmp_sig, M); os.replace(tmp_sig, SIGS())
    save_json(SIGS().replace(".npz", "_meta.json"), {"ids": ids, "vocab": vocab, "idf": [idf[t] for t in vocab]}, indent=None)
    zc = Counter(it["z"] for it in items.values())
    idx_doc = {"built": time.strftime("%Y-%m-%d %H:%M"), "library": LIBRARY, "brain": BRAIN, "placed": n,
               "twins_folded": sum(len(v) for v in twins.values()), "components": int(ncomp),
               "zones": {ZONES[z]: zc.get(z, 0) for z in range(8)}, "domains": domains, "items": items}
    save_json(INDEX(), idx_doc)
    log(f"spiral: {len(domains)} domains, {sum(1 for it in items.values() if it['seam'])} seam files, zones "
        + ", ".join(f"{ZONES[z].split('-')[0]} {zc.get(z, 0)}" for z in range(8)) + f" -> {NETWORK}\\Lz\\library")
    return idx_doc


# ------------------------------------------------------------------------------------------------ search
def search(q, k=8, warm=True):
    from scipy import sparse
    M = sparse.load_npz(SIGS())
    meta = load_json(SIGS().replace(".npz", "_meta.json"), None)
    index = load_json(INDEX(), {})
    ids, vocab = meta["ids"], meta["vocab"]
    vi = {t: i for i, t in enumerate(vocab)}
    qv = np.zeros(len(vocab), np.float32)
    for t, c in Counter(tokens(q)).items():
        j = vi.get(t)
        if j is not None: qv[j] = (1 + math.log(c)) * meta["idf"][j]
    if not qv.any(): return {"query": q, "results": [], "note": "none of the query's words are in the library"}
    qv /= np.linalg.norm(qv)
    s = M @ qv
    cand = [int(i) for i in np.argsort(-s)[:3 * k] if s[i] > 0]
    items = index.get("items", {}); doms = {d["path"]: d for d in index.get("domains", [])}
    out = []; top = []; by_title = {}
    for i in cand:
        if len(out) >= k: break
        it = items.get(ids[i], {})
        ttl = (it.get("t") or "").strip().lower()
        if ttl and ttl in by_title:                      # near-copies (same title, slightly different text) fold into the first
            by_title[ttl]["copies"].append(it.get("rel")); continue
        top.append(i)
        man = load_json(ipath(zone_dir(it.get("z", 7)), f"arm{it.get('a', 0):02d}", ids[i] + ".json"), {})
        out.append({"copies": [],"score": round(float(s[i]), 3), "id": ids[i], "title": man.get("title", it.get("t")), "rel": man.get("rel"),
                    "raw": man.get("raw"), "zone": man.get("zone"), "arm": man.get("arm"), "domain": man.get("domain"),
                    "domain_name": doms.get(man.get("domain"), {}).get("name"), "seam": man.get("seam"),
                    "seam_dist": man.get("seam_dist"), "summary": man.get("summary"),
                    "neighbors": man.get("neighbors", [])[:3], "twins": man.get("twins", [])})
        if ttl: by_title[ttl] = out[-1]
    # bridges: seam files one hop from the results that join two of the result domains
    rd = {r["domain"] for r in out}
    bridges = []
    if len(rd) > 1:
        for r in out:
            for nb in r["neighbors"]:
                it = items.get(nb["id"], {})
                if it.get("seam") and nb["id"] not in {x["id"] for x in out} and nb["id"] not in {b["id"] for b in bridges}:
                    bridges.append({"id": nb["id"], "title": it.get("t"), "rel": it.get("rel"), "domain": it.get("dom")})
    if warm and top:
        heat = load_json(HEAT(), {})
        for rank, i in enumerate(top[:3]):
            e = heat.setdefault(ids[i], {"hits": 0}); e["hits"] += 1; e["last"] = time.strftime("%Y-%m-%d %H:%M")
        save_json(HEAT(), heat)
    return {"query": q, "results": out, "bridges": bridges[:4]}


# ------------------------------------------------------------------------------------------------ ingest / crystallize / stats
def ingest(log=print):
    cfg = load_json(SOURCES, None)
    if cfg is None:
        save_json(SOURCES, {"note": "folders Mika copies into her library on `ingest` (raw files only; nothing is moved or edited)",
                            "sources": [], "extensions": sorted(TEXT_EXT | DOC_EXT), "max_mb": 25,
                            "skip_dirs": ["node_modules", ".git", "__pycache__", "dist", ".next", ".venv", "venv"]})
        log(f"ingest: wrote an empty source list to {SOURCES}; add folders there"); return 0
    g_exts = set(cfg.get("extensions", [])); g_skip = set(cfg.get("skip_dirs", []))
    cap_doc = cfg.get("max_mb", 25) * 1e6; cap_text = cfg.get("max_text_mb", 5) * 1e6
    copied = 0; per = Counter()
    for src in cfg.get("sources", []):
        src = src if isinstance(src, dict) else {"path": src}
        root = src["path"]
        label = src.get("label") or os.path.basename(root.rstrip("\\/"))
        exts = set(src.get("extensions", g_exts)); skip = g_skip | set(src.get("skip_dirs", []))
        skip_rel = [os.path.normcase(os.path.join(root, r)) for r in src.get("skip_paths", [])]
        if not os.path.isdir(root): log(f"ingest: {label}: {root} not found"); continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in skip and not d.startswith(".")
                      and not any(os.path.normcase(os.path.join(dp, d)).startswith(sr) for sr in skip_rel)]
            for fn in fns:
                p = ipath(dp, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in exts: continue
                try:
                    st = os.stat(p)
                    if st.st_size < 40 or st.st_size > (cap_doc if ext in DOC_EXT else cap_text): continue
                    dst = ipath(LIBRARY, "_sources", label, os.path.relpath(p, root))
                    if os.path.exists(dst) and os.path.getmtime(dst) >= st.st_mtime: continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(p, dst); copied += 1; per[label] += 1
                except Exception: pass
    log(f"ingest: {copied} new or changed files copied into {LIBRARY}\\_sources" + (" (" + ", ".join(f"{k} {v}" for k, v in per.most_common()) + ")" if per else ""))
    return copied


def crystallize(top=20, model="qwen2.5:3b", log=print):
    import urllib.request
    index = load_json(INDEX(), {})
    items = sorted(index.get("items", {}).items(), key=lambda kv: kv[1]["k"])[:top]
    done = 0
    for did, it in items:
        dp = ipath(BRAIN, did + ".json"); d = load_json(dp, None)
        if not d or d.get("crystal"): continue
        text, _ = read_text(d["text"] if d.get("text") and os.path.exists(d["text"]) else d["raw"])
        prompt = (f"File: {d['rel']}\nTitle: {d['title']}\n\n{text[:6000]}\n\n"
                  "In 2-3 plain sentences, say what this file is and what idea or tool it holds. No preamble.")
        body = {"model": model, "stream": False, "prompt": prompt, "options": {"temperature": 0.2, "num_ctx": 4096}}
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r: out = json.loads(r.read())["response"].strip()
        except Exception as e:
            log(f"crystallize: model call failed ({str(e)[:60]})"); break
        d["crystal"] = {"summary": out[:800], "model": model, "at": time.strftime("%Y-%m-%d %H:%M")}
        save_json(dp, d); done += 1
        log(f"  crystal: {d['rel']} - {out[:110]}")
    log(f"crystallize: {done} summaries written into the brain")


def stats():
    idx = load_json(INDEX(), None)
    if not idx: print("no spiral yet - run: python living_library.py sync"); return
    print(f"library {idx['library']}  brain {idx['brain']}  built {idx['built']}")
    print(f"placed {idx['placed']} files ({idx['twins_folded']} twins folded), {idx['components']} graph pieces")
    print("zones: " + ", ".join(f"{z} {c}" for z, c in idx["zones"].items()))
    print("domains (angle order):")
    for d in idx["domains"]:
        print(f"  {d['path']:<12} {d['size']:4d}  {d['name']:<48}  e.g. {d['examples'][0] if d['examples'] else ''}")


def main():
    ap = argparse.ArgumentParser(description="Mika's living library: library -> brain -> spiral drive -> void search")
    ap.add_argument("cmd", choices=["sync", "search", "ingest", "stats", "crystallize"])
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--k", type=int, default=8); ap.add_argument("--json", action="store_true"); ap.add_argument("--no-heat", action="store_true")
    ap.add_argument("--top", type=int, default=20); ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--lazy", action="store_true", help="rebuild the spiral only if something changed or it is 24h old")
    a = ap.parse_args()
    t0 = time.time()
    if a.cmd in ("sync", "ingest"):
        if a.cmd == "ingest": ingest()
        changed = digest_all()
        age_h = (time.time() - os.path.getmtime(INDEX())) / 3600 if os.path.exists(INDEX()) else 1e9
        if a.lazy and not changed and age_h < 24:
            print(f"spiral: nothing changed, index {age_h:.1f}h old - kept as is")
        else: build_spiral()
        print(f"done in {time.time() - t0:.0f}s")
    elif a.cmd == "search":
        res = search(a.query, a.k, warm=not a.no_heat)
        if a.json: print(json.dumps(res, ensure_ascii=False)); return
        print(f"void search: {a.query!r}")
        for r in res["results"]:
            print(f"  {r['score']:.3f}  {r['zone'].split('-')[0]}/arm{r['arm']:02d}  {r['domain']:<10} {r['title'][:70]}{'  [seam]' if r['seam'] else ''}")
            extra = len(r["twins"]) + len(r.get("copies", []))
            print(f"         {r['rel']}" + (f"   (+{extra} copies)" if extra else ""))
        if res.get("bridges"): print("  bridges between those domains: " + "; ".join(b["title"][:50] for b in res["bridges"]))
        if res.get("note"): print("  " + res["note"])
    elif a.cmd == "stats": stats()
    elif a.cmd == "crystallize": crystallize(a.top, a.model)


if __name__ == "__main__":
    main()
