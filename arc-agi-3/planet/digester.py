#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digester.py — FOOD for the ocean: outside documents (theory files, papers, repos' docs) are
eaten as LINES and compacted into the core.

The channel model (valves grow in dimension going out): a document arrives as a LINE — it
can only be read front to back. The digester walks it in order, exactly like the speech
pressure line: every chunk adds pressure = its NOVELTY (atoms never seen before in this
document); when the pressure crosses a threshold a THRESHOLD bubble is dropped (the place
where the text started saying something new), and wherever a chunk DEFINES something
("X is ...", "we call ...", "X := ...") a PROJECTION bubble is dropped. The document ends
with a CLOSURE bubble: the loop closes, and the closed path is its identity (.geo v2).

What goes DOWN toward the core loses a dimension per stage:
  line of text  →  per-chunk atom sets (the line collapsed to points)
                →  term graph: which atoms co-occur more than chance (lift), definitions
                →  library core: a few numbers per term, merged across documents
Sediment ratio for a document = bytes kept (its digest) / bytes eaten (raw text).

Nothing here needs a model. Ollama (the lower ocean) is optional (--ollama): for the
strongest new terms it is asked to restate the definition USING ONLY the chunk it is given
— a reproduction test, like the concept registry: a term whose definition the lower ocean
cannot rebuild from the text stays a candidate.

Usage:
  python digester.py --root D:\\planet\\ocean --inbox D:\\planet\\ocean\\inbox [more paths/globs] [--ollama]
Outputs:
  <root>/library/<doc>.json    the digest: chunks (with atoms), definitions, bubbles, term graph
  <root>/library/<doc>.geo     the document as a closed loop (dormant until re-read)
  <root>/core_library.json     the compacted library core: terms, definitions, doc list, sediment
  <root>/inbox/eaten/          eaten files are moved here (the ground = least processed)
"""
from __future__ import annotations
import argparse, glob, hashlib, json, math, os, re, shutil, sys, time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, HERE)
import geo

STOP = set("""a an the and or of to in on at by for with from as is are was were be been being it its this that these those
we you they he she i our your their his her them us me my not no nor but if then than so such which who whom whose what
when where why how all any both each few more most other some own same too very can will just should would could may
might must shall do does did doing done have has had having into over under again further once here there also only
via per etc eg ie let thus hence therefore however moreover whereas while because since until about above below between
through during before after up down out off one two three first second new old use used using given get gets got
set sets see seen show shows shown call called calls make makes made take takes taken like well still even yet""".split())
DEF_PATTERNS = [
    re.compile(r"\b([A-Z][\w\-]*(?:\s+[A-Za-z][\w\-]*){0,3})\s+(?:is|are|means|denotes|refers to)\s+(?:a|an|the)\b"),
    re.compile(r"\bwe\s+(?:call|define|name|say)\s+(?:this|it|that|the)?\s*([A-Za-z][\w\-]*(?:\s+[A-Za-z][\w\-]*){0,3})"),
    re.compile(r"\b([A-Za-z][\w\-]*(?:\s+[A-Za-z][\w\-]*){0,2})\s*(?::=|=def|\\equiv|\\coloneqq)"),
    re.compile(r"\*\*([^*]{2,60}?)\.?\*\*\s*[:—.-]"),
    re.compile(r"\\textbf\{([^}]{2,60})\}\s*[:—-]?"),
]


# ----------------------------------------------------------------------------- reading (the line)
def read_text(path: str) -> Optional[str]:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(path)
                return "\n\n".join(page.get_text() for page in doc)
            except ImportError:
                return None
        if ext in (".md", ".txt", ".tex", ".rst", ".py", ".ts", ".js", ".json", ".yaml", ".yml", ".html", ".csv"):
            with open(path, "r", encoding="utf-8", errors="replace") as f: return f.read()
    except Exception:
        return None
    return None


def chunks_of(text: str, target: int = 600) -> List[str]:
    """The line, cut where the author paused: paragraphs, merged up to ~target chars, split if huge."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > target and cur:
            out.append(cur); cur = p
        else:
            cur = (cur + "\n" + p).strip()
        while len(cur) > 3 * target:
            cut = cur.rfind(". ", 0, 2 * target)
            cut = cut + 1 if cut > target // 2 else 2 * target
            out.append(cur[:cut].strip()); cur = cur[cut:].strip()
    if cur: out.append(cur)
    return out


# ----------------------------------------------------------------------------- atoms (points)
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")


def atoms_of(chunk: str) -> Set[str]:
    words = [w.lower() for w in TOKEN.findall(chunk)]
    words = [w for w in words if w not in STOP and not w.isdigit()]
    at = set(words)
    for a, b in zip(words, words[1:]):           # bigrams carry the technical vocabulary ("critical line")
        at.add(a + "_" + b)
    return at


def definitions_of(chunk: str) -> List[Tuple[str, str]]:
    found = []
    for pat in DEF_PATTERNS:
        for m in pat.finditer(chunk):
            term = re.sub(r"^(?:the|a|an)\s+", "", m.group(1).strip().lower())
            if 2 <= len(term) <= 60 and term.split()[0] not in STOP:
                s0 = chunk.rfind(".", 0, m.start()) + 1
                s1 = chunk.find(".", m.end())
                sent = chunk[s0: s1 + 1 if s1 > 0 else len(chunk)].strip().replace("\n", " ")
                found.append((term, sent[:400]))
    return found


# ----------------------------------------------------------------------------- one document
def digest_document(path: str, threshold: float = 12.0) -> Optional[Dict]:
    text = read_text(path)
    if not text or len(text) < 200: return None
    t0 = time.time()
    raw_bytes = len(text.encode("utf-8"))
    chunks = chunks_of(text)
    seen: Set[str] = set(); df: Counter = Counter(); pair: Counter = Counter()
    pressure, events, bubbles, defs, chunk_atoms = 0.0, [], [], [], []
    for i, ch in enumerate(chunks):
        at = atoms_of(ch)
        new = at - seen; seen |= at
        df.update(at)
        core = sorted(at, key=lambda a: -len(a))[:40]           # bounded co-occurrence: the longest atoms
        for x in range(len(core)):
            for y in range(x + 1, len(core)):
                pair[(core[x], core[y]) if core[x] < core[y] else (core[y], core[x])] += 1
        d = definitions_of(ch)
        defs.extend((i, t, s) for t, s in d)
        novelty = len(new) / max(8.0, math.sqrt(len(at) + 1))
        pressure += novelty
        ev = set()
        if pressure >= threshold:
            ev.add("surprise.big"); bubbles.append({"chunk": i, "role": "threshold", "pressure": round(pressure, 2)})
            pressure = 0.0
        if d:
            ev.add("body.confirmed"); bubbles.append({"chunk": i, "role": "projection", "terms": [t for t, _ in d]})
        events.append(sorted(ev))
        chunk_atoms.append({"i": i, "chars": len(ch), "new": len(new), "old": len(at) - len(new),
                            "atoms": sorted(new)[:60], "defs": [t for t, _ in d], "text": ch[:1200]})
    n = max(1, len(chunks))
    # the term graph (the line collapsed one more time): lift of co-occurrence over chance
    graph = []
    for (a, b), c in pair.items():
        if c < 2: continue
        lift = c * n / max(1e-9, df[a] * df[b])
        if lift > 3.0: graph.append([a, b, c, round(lift, 2)])
    graph.sort(key=lambda r: -r[2] * r[3])
    graph = graph[:400]
    terms = [t for t, c in df.most_common(200) if c >= 2]
    doc_id = os.path.splitext(os.path.basename(path))[0]
    digest = {"doc": doc_id, "path": os.path.abspath(path), "sha": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
              "chars": len(text), "chunks": chunk_atoms, "definitions": [{"chunk": i, "term": t, "sentence": s} for i, t, s in defs],
              "bubbles": bubbles, "terms": terms, "graph": graph, "seconds": round(time.time() - t0, 2)}
    digest["kept_bytes"] = len(json.dumps({k: digest[k] for k in ("definitions", "terms", "graph")}).encode("utf-8"))
    digest["sediment_ratio"] = round(digest["kept_bytes"] / raw_bytes, 4)
    # the document as a closed loop: one segment per chunk (w: chars, x: new atoms, y: recurring atoms, z: definitions)
    body_path = [{"t": c["chars"] / 1000.0, "dx": c["new"], "dy": c["old"], "jump": len(c["defs"])} for c in chunk_atoms]
    narration = "\n".join(f"[{d['chunk']}] {d['term']}: {d['sentence']}" for d in digest["definitions"][:80])
    cont = geo.life_container("library", 0, body_path, events, narration, {"terms": terms[:60], "graph": graph[:60]},
                              path, "", "read", {"drive": float(len(bubbles)), "W": 0, "H": 0, "doc": doc_id,
                                                 "sediment_ratio": digest["sediment_ratio"]})
    cont["manifest"]["name"] = f"library-{doc_id}"; cont["manifest"]["tags"] = ["planet", "library", "document"]
    digest["_geo"] = cont
    return digest


# ----------------------------------------------------------------------------- the library core (compaction)
def load_json(p, default):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default


def save_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def compact(core: Dict, digest: Dict) -> None:
    """Merge one digest into the library core. Terms gain evidence per document they recur in;
    definitions are kept by term (first + count); the graph keeps the pairs that recur across docs."""
    core.setdefault("docs", {}); core.setdefault("terms", {}); core.setdefault("definitions", {}); core.setdefault("graph", {})
    core["docs"][digest["doc"]] = {"sha": digest["sha"], "chars": digest["chars"], "chunks": len(digest["chunks"]),
                                   "definitions": len(digest["definitions"]), "sediment_ratio": digest["sediment_ratio"],
                                   "bubbles": len(digest["bubbles"]), "t": time.time()}
    for t in digest["terms"]:
        e = core["terms"].setdefault(t, {"docs": 0})
        e["docs"] += 1
    for d in digest["definitions"]:
        e = core["definitions"].setdefault(d["term"], {"count": 0, "sentences": [], "docs": []})
        e["count"] += 1
        if len(e["sentences"]) < 3 and d["sentence"] not in e["sentences"]: e["sentences"].append(d["sentence"])
        if digest["doc"] not in e["docs"]: e["docs"].append(digest["doc"])
    for a, b, c, lift in digest["graph"][:150]:
        k = a + "|" + b
        e = core["graph"].setdefault(k, {"docs": 0, "count": 0, "lift": 0.0})
        e["docs"] += 1; e["count"] += c; e["lift"] = max(e["lift"], lift)
    raw = sum(v["chars"] for v in core["docs"].values())
    core["sediment"] = {"docs": len(core["docs"]), "terms": len(core["terms"]), "definitions": len(core["definitions"]),
                        "raw_chars": raw, "kept_bytes": len(json.dumps(core["definitions"]).encode("utf-8")) + len(json.dumps(core["graph"]).encode("utf-8")),
                        "t": time.time()}


def lower_reproduce(model: str, term: str, chunk: str) -> Optional[str]:
    import lower
    prompt = ("Using ONLY the passage below, restate in one sentence what the term means. If the passage does not "
              "actually define it, answer exactly: UNDEFINED.\n"
              f"Term: {term}\nPassage: {chunk[:1500]}")
    out = lower._ask(model, prompt, timeout=40.0)
    return out.strip() if out else None


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\planet\ocean")
    ap.add_argument("--inbox", default=None, help="folder whose files are eaten and moved to inbox/eaten")
    ap.add_argument("paths", nargs="*", help="extra files/globs to digest in place (not moved)")
    ap.add_argument("--ollama", action="store_true", help="ask the lower ocean to rebuild the strongest definitions")
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--threshold", type=float, default=12.0)
    a = ap.parse_args()
    lib = os.path.join(a.root, "library"); os.makedirs(lib, exist_ok=True)
    core_path = os.path.join(a.root, "core_library.json")
    core = load_json(core_path, {"version": 1})
    files: List[Tuple[str, bool]] = []
    inbox = a.inbox or os.path.join(a.root, "inbox")
    if os.path.isdir(inbox):
        for f in sorted(os.listdir(inbox)):
            p = os.path.join(inbox, f)
            if os.path.isfile(p): files.append((p, True))
    for pat in a.paths:
        for p in sorted(glob.glob(pat, recursive=True)):
            if os.path.isfile(p): files.append((p, False))
    if not files:
        print("nothing to eat (inbox empty:", inbox, ")"); return
    log = open(os.path.join(a.root, "digester.log"), "a", encoding="utf-8")
    def say(s):
        line = f"[{time.strftime('%H:%M:%S')}] {s}"; print(line, flush=True); log.write(line + "\n"); log.flush()
    for p, move in files:
        doc = os.path.splitext(os.path.basename(p))[0]
        sha_seen = core.get("docs", {}).get(doc, {}).get("sha")
        d = digest_document(p, a.threshold)
        if d is None:
            say(f"could not read {p}"); continue
        if sha_seen == d["sha"]:
            say(f"already digested {doc}"); continue
        if a.ollama and d["definitions"]:
            import lower
            models = lower.available([a.model])
            if models:
                chunks = chunks_of(read_text(p) or "")
                rebuilt = 0
                for dd in d["definitions"][:6]:
                    out = lower_reproduce(models[0], dd["term"], chunks[dd["chunk"]])
                    dd["lower_ocean"] = out
                    if out and "UNDEFINED" not in out: rebuilt += 1
                say(f"  lower ocean rebuilt {rebuilt}/{min(6, len(d['definitions']))} definitions")
        cont = d.pop("_geo")
        save_json(os.path.join(lib, doc + ".json"), d)
        geo.write_geo(os.path.join(lib, doc + ".geo"), cont, dormant=True)
        compact(core, d)
        save_json(core_path, core)
        say(f"ate {doc}: {d['chars']} chars, {len(d['chunks'])} chunks, {len(d['definitions'])} definitions, "
            f"{len(d['bubbles'])} bubbles, {len(d['graph'])} edges, sediment {d['sediment_ratio']}")
        if move:
            eaten = os.path.join(inbox, "eaten"); os.makedirs(eaten, exist_ok=True)
            try: shutil.move(p, os.path.join(eaten, os.path.basename(p)))
            except Exception as e: say(f"  (could not move {p}: {e})")
    s = core.get("sediment", {})
    say(f"library core: {s.get('docs')} docs, {s.get('terms')} terms, {s.get('definitions')} definitions, "
        f"kept {s.get('kept_bytes')} bytes of {s.get('raw_chars')} chars")


if __name__ == "__main__":
    main()
