#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voidsearch.py — SEAM SEARCH: the void-line toolkit turned into a search system.

From the RH/void-lines work (FOLDING_CRITICAL_LINE, CRITICAL_LINE_PAPER): "the corpus's methods —
find the outlier, cut the seam — detect structure that maximally-mixed spaces hide." Keyword search
finds what you name; SEAM search finds how a corpus actually CUTS, and what refuses to mix:

  1. every file becomes a bag of atoms (tf-idf) — a node
  2. nodes are joined by cosine similarity (kNN graph) — the contact graph
  3. the graph Laplacian's FIEDLER VECTOR draws the void line through the corpus:
       - the SIGN of each file's component = which domain it belongs to (the cut)
       - files NEAR ZERO = the seam — the mixed pixels, the bridges between domains
       - files with extreme leverage or near-isolation = the OUTLIERS — the findable structure,
         the things you would not think to search for
  4. recursing on each half gives the domain tree — the corpus sorts ITSELF

Usage:
  python voidsearch.py --roots D:\\planet C:\\Users\\GamerTech\\boys-colony --out map.md
  python voidsearch.py --roots <dirs> --query "spiral storage"      (seam-aware retrieval:
      results come with their domain and seam-distance, so you see WHERE an answer lives)
"""
from __future__ import annotations
import argparse, math, os, re, sys
from collections import Counter
from typing import Dict, List, Tuple
import numpy as np

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

EXT = {".py", ".md", ".txt", ".ts", ".js", ".json", ".tex", ".bat", ".yaml", ".yml", ".html"}
SKIP = {"node_modules", ".git", "__pycache__", "dist", "hf", "lives", "clips", "shots", ".venv", "venv"}
MAXB = 200_000
STOP = set("the a an and or of to in for is are was were be been with as at by on from this that it its "
           "if then else not no we you i our your they them there here have has had do does did can could "
           "will would should may might must self def return import class true false none null var let "
           "const function".split())


def tokens(s: str) -> Counter:
    return Counter(t for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", s.lower()) if t not in STOP)


def harvest(roots: List[str]) -> List[Tuple[str, Counter]]:
    docs = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in EXT: continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > MAXB or os.path.getsize(p) < 80: continue
                    txt = open(p, encoding="utf-8", errors="replace").read()
                except Exception: continue
                tk = tokens(fn + " " + txt)
                if len(tk) >= 10: docs.append((p, tk))
    return docs


def vectors(docs) -> Tuple[np.ndarray, List[str]]:
    df = Counter(t for _, tk in docs for t in tk)
    vocab = [t for t, c in df.items() if 2 <= c <= 0.5 * len(docs)]
    vi = {t: i for i, t in enumerate(vocab)}
    n = len(docs)
    M = np.zeros((n, len(vocab)), dtype=np.float32)
    for i, (_, tk) in enumerate(docs):
        for t, c in tk.items():
            j = vi.get(t)
            if j is not None: M[i, j] = (1 + math.log(c)) * math.log(n / df[t])
    norms = np.linalg.norm(M, axis=1, keepdims=True); norms[norms == 0] = 1
    return M / norms, vocab


def fiedler(sim: np.ndarray, k: int = 8):
    n = sim.shape[0]
    A = np.zeros_like(sim)
    for i in range(n):
        nn = np.argsort(-sim[i])[1:k + 1]
        A[i, nn] = sim[i, nn]
    A = np.maximum(A, A.T)
    d = A.sum(1); L = np.diag(d) - A
    dm = np.where(d > 0, 1 / np.sqrt(d), 0)
    Ln = dm[:, None] * L * dm[None, :]
    w, v = np.linalg.eigh(Ln)
    return v[:, 1], A, d          # the Fiedler vector, adjacency, degrees


def cut(docs, M, depth=0, idx=None, lines=None, maxdepth=3, minsize=6):
    if lines is None: lines = []
    if idx is None: idx = np.arange(len(docs))
    if len(idx) < minsize or depth >= maxdepth:
        return lines
    sim = M[idx] @ M[idx].T
    f, A, d = fiedler(sim)
    order = np.argsort(f)
    seam = idx[np.argsort(np.abs(f))[:max(2, len(idx) // 20)]]
    iso = idx[np.argsort(d)[:max(1, len(idx) // 30)]]
    top = {}
    for side, sel in (("A", idx[f < 0]), ("B", idx[f >= 0])):
        cnt = Counter()
        for i in sel: cnt.update(dict(docs[i][1]))
        top[side] = ", ".join(t for t, _ in cnt.most_common(6))
    pad = "  " * depth
    lines.append(f"{pad}CUT depth {depth}: {sum(f<0)} vs {sum(f>=0)} files")
    lines.append(f"{pad}  A: {top['A']}")
    lines.append(f"{pad}  B: {top['B']}")
    lines.append(f"{pad}  seam (mixed pixels, bridge files): " + "; ".join(os.path.basename(docs[i][0]) for i in seam[:5]))
    lines.append(f"{pad}  outliers (near-isolated — the findable structure): "
                 + "; ".join(os.path.basename(docs[i][0]) for i in iso[:4]))
    for sel in (idx[f < 0], idx[f >= 0]):
        cut(docs, M, depth + 1, sel, lines, maxdepth, minsize)
    return lines


def query(docs, M, vocab, q: str, k: int = 10):
    vi = {t: i for i, t in enumerate(vocab)}
    qv = np.zeros(len(vocab), dtype=np.float32)
    for t, c in tokens(q).items():
        j = vi.get(t)
        if j is not None: qv[j] = 1
    nq = np.linalg.norm(qv)
    if nq == 0: print("query has no known atoms"); return
    qv /= nq
    sim_all = M @ M.T
    f, _, d = fiedler(sim_all)
    scores = M @ qv
    for i in np.argsort(-scores)[:k]:
        if scores[i] <= 0: break
        print(f"  {scores[i]:.3f}  dom {'A' if f[i] < 0 else 'B'}  seam-dist {abs(f[i]):.3f}  "
              f"deg {d[i]:.1f}  {docs[i][0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--query", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    docs = harvest(a.roots)
    print(f"seam search: {len(docs)} documents harvested")
    if len(docs) < 6: return
    M, vocab = vectors(docs)
    if a.query:
        query(docs, M, vocab, a.query); return
    lines = cut(docs, M)
    out = "\n".join(lines)
    print(out)
    if a.out:
        open(a.out, "w", encoding="utf-8").write("# Seam map (voidsearch)\n\n```\n" + out + "\n```\n")


if __name__ == "__main__":
    main()
