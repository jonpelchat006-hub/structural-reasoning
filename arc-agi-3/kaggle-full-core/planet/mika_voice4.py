"""mika_voice4.py - a better job for her voice (Oct 30 2026). Switched on by MIKA_VOICE4=1; her body and core are unchanged.

Why (voice v3, 25 public games): 282 proposals, ~100 failed her facts check (58 named things not on the screen, 33 named
things that had done nothing every time), 100 of the 183 she accepted were openings, the body could not reach 128 of them,
32 copied the prompt's placeholder as their reason, and none led to a level. The voice read a text list of ids that her
code had already ranked, with no picture.

What changes:
  1. THE PICTURE. The screen goes with the question, drawn in the game's own colours (64x64 cells, 8x8 pixels each).
  2. THINGS, NOT OPENINGS. Only things are offered (openings are the body's own exploring), and not a thing the body
     could not reach the last time it tried this life.
  3. NO PLACEHOLDER. The answer format is described in words, not with an example to copy; a reason with <...> is refused.
  4. NOT OVER A RUNNING LOOP. While the body's carried relation loop is allowed on a level, she does not ask.
  5. EVERYTHING IS WRITTEN DOWN. Every question and answer, every experiment result, and a snapshot of her evidence every
     6 experiments on an uncleared level (asked or not) go to MIKA_THINK_LOG, for study and for retraining her voice.
"""
from __future__ import annotations
import base64, io, os, re, time, zlib, struct

ON = os.environ.get("MIKA_VOICE4", "0") == "1"
SNAP_EVERY = 6
COLOUR_HEX = ["FFFFFF", "CCCCCC", "999999", "666666", "333333", "000000", "E53AA3", "FF7BCC",
              "F93C31", "1E93FF", "88D8F1", "FFDC00", "FF851B", "921231", "4FCC30", "A356D6"]
COLOUR_NAME = ["white", "off-white", "light grey", "grey", "dark grey", "black", "magenta", "pink",
               "red", "blue", "light blue", "yellow", "orange", "maroon", "green", "purple"]
CURRENT = {"frame": None}
NOTRIED = {"unreachable", "untestable"}


def png_b64(f, scale=8):
    """the frame as a PNG in the game's colours (no PIL needed)"""
    import numpy as np
    a = np.asarray(f, dtype=int) % 16
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in COLOUR_HEX], dtype=np.uint8)
    rgb = pal[a].repeat(scale, 0).repeat(scale, 1)
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


FORMAT = ("Answer only with a JSON object with one key, \"claims\": a list of up to 3 proposals, best first. Each proposal is "
          "an object with three keys: \"try\" is one thing id copied exactly from the list above; \"expect\" is exactly one "
          "word, changed, refill, level or pass; \"because\" is one sentence in your own words that names the evidence "
          "(a result count, a relation, how an earlier level was won, or what you see in the picture).")
PICTURE = ("The picture is the screen now: 64 rows by 64 columns of cells, row 0 at the top, each cell drawn as an 8x8 "
           "square. A thing id is colour@row,col of the thing's top-left cell. Colours: "
           + ", ".join(f"{i} {n}" for i, n in enumerate(COLOUR_NAME)) + ".")


def install():
    if not ON:
        return
    import mika_mind as mm, mika_think as mt
    if getattr(mt.ThinkingMind, "_v4", False):
        return
    TM = mt.ThinkingMind

    # ---- 5. everything written down (with the life it happened in)
    orig_t = TM._t
    def _t(s, kind, **kw):
        if s.tlog_path:
            kw.setdefault("life", getattr(s, "life_k", None))
        return orig_t(s, kind, **kw)
    TM._t = _t

    orig_observe = TM.observe
    def observe(s, e):
        try:
            s._t("exp", level=int(e.get("level", -1)), id=str(e.get("id")), result=e.get("result"), rel=e.get("rel"),
                 n=getattr(s, "exp_all", {}).get(int(e.get("level", -1)), 0))
        except Exception:
            pass
        return orig_observe(s, e)
    TM.observe = observe

    # ---- 4. not over a running loop
    orig_allow = TM.allow_relation
    def allow_relation(s, lvl, r, reset=False):
        ok = orig_allow(s, lvl, r, reset)
        s._rel_live = getattr(s, "_rel_live", {}); s._rel_live[int(lvl)] = bool(ok)
        return ok
    TM.allow_relation = allow_relation

    # ---- 3. no placeholder: the format in words; the picture explained
    orig_ev = TM._evidence
    def _evidence(s, goals, lvl, f):
        text = orig_ev(s, goals, lvl, f)
        cut = text.find("\"try\" must be one thing id")
        if cut > 0:
            text = text[:cut].rstrip() + "\n" + FORMAT
        return PICTURE + "\n\n" + text
    TM._evidence = _evidence

    orig_check = TM._check
    def _check(s, c, lvl, on_screen):
        if re.search(r"<[^>]*>", c.get("because", "")):
            return "its reason is the format's placeholder, not a reason"
        return orig_check(s, c, lvl, on_screen)
    TM._check = _check

    # ---- 1, 2, 5. the picture, things not openings, snapshots
    orig_think = TM._maybe_think
    def _maybe_think(s, goals, lvl, f):
        lvl = int(lvl)
        life_res = s.life_res.get(lvl, {})
        things = [g for g in goals if not str(g["id"]).startswith("open@")
                  and not (life_res.get(str(g["id"])) and life_res[str(g["id"])][-1] in NOTRIED)]
        n_all = getattr(s, "exp_all", {}).get(lvl, 0)
        s._snap_at = getattr(s, "_snap_at", {})
        if things and lvl not in s.cleared and n_all >= s._snap_at.get(lvl, 0) + SNAP_EVERY:
            s._snap_at[lvl] = n_all
            try:
                s._t("snap", level=lvl, n=n_all, ids=[str(g["id"]) for g in things], prompt=s._evidence(things, lvl, f),
                     frame=[[int(v) for v in row] for row in f])
            except Exception as e_:
                s._t("error", where="snap", error=str(e_)[:200])
        if not things or getattr(s, "_rel_live", {}).get(lvl):
            return
        CURRENT["frame"] = f
        try:
            return orig_think(s, things, lvl, f)
        finally:
            CURRENT["frame"] = None
    TM._maybe_think = _maybe_think

    orig_post = mm._post
    def _post(url, body, timeout=180):
        if url.endswith("/api/chat") and CURRENT["frame"] is not None and os.environ.get("MIKA_VOICE_IMAGES", "1") == "1":
            try:
                msgs = body.get("messages") or []
                for m in reversed(msgs):
                    if m.get("role") == "user":
                        m["images"] = [png_b64(CURRENT["frame"])]; break
            except Exception:
                pass
        return orig_post(url, body, timeout)
    mm._post = _post

    TM._v4 = True
