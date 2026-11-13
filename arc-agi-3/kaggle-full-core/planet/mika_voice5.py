"""mika_voice5.py - she briefs her voice before she asks it anything (Oct 30 2026). MIKA_VOICE5=1, on top of voice4.

Jonathan, Oct 30: "if she is just showing a picture and asking what do i do the model cant really help. the questions would
have to be more specific and the model would have to be able to catch up to her thinking. if she shows a picture she
should say what shes tried, or what game she thinks shes playing too"

Voice v4 sent the screen, a list of thing ids with result counts, how earlier levels were won, and "propose up to 3
things". Everything she understands was missing: what moves her, the bar and its refills, the relation that won the earlier
levels, what blocks her now. Her body logs all of it every press. Now every question has four parts:

  1. WHAT GAME SHE THINKS THIS IS - in plain words, from her body's own model: which buttons move the body and how much
     she trusts them, clicks, the bar (how fast it drains, how many moves are left) and the things that refilled it, the
     "touch X until the picture matches Y" relation that won earlier levels, and her guess at the kind of game (the
     objective types of the failure map: matching, movement, filling, pushing, connecting, toggling ...).
  2. WHAT SHE HAS DONE ON THIS LEVEL - her experiments in order with what happened, how often the level was put back.
  3. ONE QUESTION, matched to where she is stuck (the picture-turner cannot be reached; turning the picture did not win;
     only a few things change anything; nothing changes anything).
  4. CATCHING UP - what she asked last time on this level, what the voice answered, what happened when she tried it,
     and what the voice thought the game was.

The answer stays checkable (claims: a thing, what to expect, why; plus "game": one sentence on the goal), so her facts
check still filters every proposal before the body moves.
"""
from __future__ import annotations
import json, os, re

ON = os.environ.get("MIKA_VOICE5", "0") == "1"
# ask before pressing (Nov 2): on reaching a level, before any press there, she asks once. The square makes a level's
# first presses its most expensive, so that is where a friend's knowledge is worth the most.
ASK_FIRST = os.environ.get("MIKA_ASK_FIRST", "0") == "1"
START_WORDS = "I haven't pressed anything on this level yet"
EXTRA_DUE = None                        # a hook: (mind, level, events) -> a reason to ask, or None (set by mika_prism)
BODY = {}                               # the latest line of each kind her body logged (one game per process)
LEVEL_EVENTS = {"resets": 0, "refills": 0, "deaths": 0, "unreach_src": 0}
DIRS = {1: "up", 2: "down", 3: "left", 4: "right", 5: "the fifth button", 6: "click", 7: "undo"}
TYPES = "matching, symmetry, movement, filling, pushing, sorting, toggling, connecting, removing, covering, rotating, timing, levers, merging"

SYSTEM5 = """You are helping a friend who is stuck in a puzzle game she has never seen before. The game has no instructions
and no words; it is a small grid of coloured cells. She tells you in her own words what she sees, what she has worked out,
what she has tried and what happened, marks the things she can touch with letters (on the picture too), and asks you one
question. Talk to her like a friend who has played a lot of puzzle games: plain English, a few sentences - what kind of
puzzle you think this is, what the goal might be, and what you would try next and why. She checks your ideas against what
she has already seen before she acts on them, so it is fine to guess."""

FORMAT5 = ("Answer only with a JSON object with two keys. \"game\": one sentence, what you think the goal of this level is. "
           "\"claims\": a list of up to 3 proposals, best first; each is an object with \"try\" (one thing id copied exactly "
           "from the list above), \"expect\" (exactly one word: changed, refill, level or pass) and \"because\" (one sentence "
           "that answers her question, in your own words).")


def tap(logf):
    """wrap the life's log function: remember the latest line of each kind her body writes"""
    if not ON:
        return logf
    def log(s):
        try:
            t = str(s).strip()
            m = re.match(r"^\d+\.\s+(.*)$", t)
            core = m.group(1) if m else t
            for key in ("sleep (", "meter: bar", "meter: the drain", "relation: ", "relation carried", "relation loop:",
                        "route: no order", "buttons: ", "magnets: ", "core: level", "detour check"):
                if core.startswith(key):
                    BODY[key.strip(" (:")] = core
            if core.startswith("RESET #"): LEVEL_EVENTS["resets"] += 1
            if core.startswith("REFILL"): LEVEL_EVENTS["refills"] += 1
            if "the relation's src cannot be reached" in core: LEVEL_EVENTS["unreach_src"] += 1
            if t.startswith(">>> LEVEL") or re.match(r"^\S+-[0-9a-f]{6,}: \d+ levels", t):
                for k in LEVEL_EVENTS: LEVEL_EVENTS[k] = 0
                for k in [k for k in BODY if k.startswith(("relation", "core"))]: BODY.pop(k, None)
        except Exception:
            pass
        return logf(s)
    return log


def _ops_words():
    s = BODY.get("sleep", "")
    m = re.search(r"\):\s*(.*?)\s*\|", s)
    ops = m.group(1) if m else ""
    move, other = [], []
    for a, q, kind, n, b in re.findall(r"(\d):(\??)([a-z\-]+)(?: \(promoted\))?(?: h[\d.]+)?\((\d+)\)(?: b([\d.]+))?", ops):
        a = int(a); d = DIRS.get(a, f"button {a}")
        if kind == "displace":
            move.append(f"{d}" + (f" (trusted {float(b):.0%})" if b else "") + (" (not sure yet)" if q else ""))
        elif kind == "click":
            other.append("clicking things " + ("has done little so far" if q else "changes them"))
        elif kind == "cycle":
            other.append(f"button {a} ({d}) seems to cycle something through states")
        elif kind == "restore":
            other.append(f"button {a} ({d}) seems to put something back")
        elif kind == "-":
            other.append(f"{d} has done nothing she can explain yet")
    out = []
    if move: out.append("She moves a body with direction buttons: " + ", ".join(move) + ". Walls stop it.")
    out += [o[0].upper() + o[1:] + "." for o in other]
    b = re.search(r"budget colour (\d+) drains ([\d.]+)/press, (\d+) left", s)
    mt = BODY.get("meter: bar", "")
    mm = re.search(r"bar colour (\d+) drains (\d+) cells per move.*?(\d+) moves left", mt)
    if mm: out.append(f"A bar in colour {mm.group(1)} drains {mm.group(2)} cell(s) per move; about {mm.group(3)} moves are left before the level is put back.")
    elif b: out.append(f"A bar in colour {b.group(1)} drains as she moves; about {b.group(3)} presses are left before the level is put back.")
    return out


def _relation_words(s, lvl):
    out = []
    r = BODY.get("relation") or ""
    m = re.match(r"relation: (\S+) -> region rows (\d+)-(\d+) cols (\d+)-(\d+) \((\d+) states seen\) -> (\S+)(?: \(D4 (\S+) away\))?", r)
    if m:
        src, r0, r1, c0, c1, k, tgt, away = m.groups()
        out.append(f"On this level, touching {src} changes the picture at rows {r0}-{r1}, cols {c0}-{c1} (she has seen it in {k} states); "
                   f"she thinks it must be made to match the picture in {tgt}" + (f", which looks {away} turn(s) away" if away and away != "None" else "") + ".")
        return out, src, tgt
    rc = BODY.get("relation carried") or ""
    m = re.search(r"by colour: (\S+) -> region rows (\d+)-(\d+) cols (\d+)-(\d+) -> (\S+)", rc)
    if m:
        src, r0, r1, c0, c1, tgt = m.groups()
        out.append(f"From the last level she carries the rule: touching a thing of colour {src.split('@')[0]} changes the picture at rows "
                   f"{r0}-{r1}, cols {c0}-{c1} until it matches the target, here maybe {tgt}.")
        return out, src, tgt
    return out, None, None


def _game_guess(s, lvl, ops, rel_src):
    kinds = []
    if rel_src or s.rel_mem or s.rel_new: kinds.append("matching (make a shown picture equal a target, then go to the target)")
    if any("moves a body" in o for o in ops): kinds.append("movement (walk a body around walls)")
    if any("bar" in o for o in ops): kinds.append("a move budget (a bar that runs out; refills help)")
    if any("click" in o.lower() for o in ops) and not any("moves a body" in o for o in ops): kinds.append("clicking things to change them")
    return kinds


def _done_words(s, lvl):
    seq = getattr(s, "_v5_seq", {}).get(lvl, [])[-12:]
    lines = []
    for tid, res in seq:
        lines.append(f"{tid}: {res}")
    return lines


def _question(s, lvl, rel_src, rel_tgt):
    life_res = s.life_res.get(lvl, {})
    changed = sorted(t for t, rs in life_res.items() if any(r in ("changed", "refill", "level") for r in rs))
    if rel_src:
        src_res = life_res.get(rel_src, []) + [r for t, rs in life_res.items() if t != rel_src and t.split("@")[0] == rel_src.split("@")[0] for r in rs]
        unreach = sum(1 for r in src_res if r in ("unreachable", "untestable")) + LEVEL_EVENTS["unreach_src"]
        if unreach >= 2:
            return (f"The thing that changes the picture here ({rel_src}) could not be reached {unreach} times (walls, or the bar ran out "
                    f"on the way). Which thing on the list could open a way to it, refill the bar on the way, or change the picture "
                    f"another way?")
        if LEVEL_EVENTS["resets"] >= 1:
            return (f"Turning the picture with {rel_src} has not won this level; it was put back {LEVEL_EVENTS['resets']} time(s). "
                    f"What else might have to match the target {rel_tgt or ''} (colour, shape, size, position), and which thing on "
                    f"the list could change that?")
        return (f"She is turning the picture with {rel_src} toward {rel_tgt or 'the target'}. Is there anything else on the screen that "
                f"has to be done first or at the same time, and which thing is it?")
    if changed:
        return (f"Only {', '.join(changed[:5])} changed anything on this level so far. Looking at the picture, which two things look "
                f"like they should match or fit together, and which thing on the list could change one of them?")
    return ("Nothing she touched on this level changed the board yet. Looking at the picture, what kind of game could this be ("
            + TYPES + "), and which thing would you touch first to find out?")


def _catch_up(s, lvl):
    out = []
    last = getattr(s, "_v5_last", {}).get(lvl)
    if not last: return out
    out.append(f"Last time she asked: {last['question']}")
    if last.get("game"): out.append(f"You thought the goal was: {last['game']}")
    for c in [c for c in s.j.get("claims", []) if c.get("level") == lvl][-3:]:
        out.append(f"You proposed {c['try']} expecting {c['expect']}: " +
                   ({"held": f"it held ({c.get('result')}).", "missed": f"the body saw {c.get('result')}.",
                     "untried": f"the body could not try it ({c.get('result')})."}.get(c.get("outcome"), "not tried yet.")))
    return out



COLOUR = ["white", "off-white", "light grey", "grey", "dark grey", "black", "magenta", "pink",
          "red", "blue", "light blue", "yellow", "orange", "maroon", "green", "purple"]
LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def _where(box):
    """rows/cols box -> plain words for where it is on the screen"""
    r0, c0, r1, c1 = box
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if h <= 2 and w >= 30: return "a long line across the " + ("top" if r0 < 21 else "bottom" if r0 > 42 else "middle")
    if w <= 4 and h >= 30: return "a long line down the " + ("left side" if c0 < 21 else "right side" if c0 > 42 else "middle")
    rr, cc = (r0 + r1) / 2, (c0 + c1) / 2
    v = "top" if rr < 21 else "bottom" if rr > 42 else "middle"
    hz = "left" if cc < 21 else "right" if cc > 42 else "centre"
    return "the centre" if (v, hz) == ("middle", "centre") else f"the {v}-{hz}" if v != "middle" else f"the middle {hz}" if hz != "centre" else "the centre"


def _what(d):
    """a thing's description (colour, n cells, box) -> 'a small red square in the top-left'"""
    try:
        r0, c0, r1, c1 = d["box"]; n = int(d["n"])
        h, w = r1 - r0 + 1, c1 - c0 + 1
        size = "tiny" if n <= 4 else "small" if n <= 16 else "medium" if n <= 60 else "big"
        fill = n / max(1, h * w)
        shape = ("line" if min(h, w) <= 2 and max(h, w) >= 6 else "square" if 0.8 <= h / max(1, w) <= 1.25 and fill > 0.7
                 else "frame" if fill < 0.45 else "block")
        col = COLOUR[int(d["colour"]) % 16]
        where = _where(d["box"])
        if where.startswith("a long line"): return "a long " + col + " line" + where[len("a long line"):]
        return f"a {size} {col} {shape} in {where}"
    except Exception:
        return "a thing"


def _inside(f, box):
    """other colours inside a thing's box: 'with a blue pattern inside'"""
    try:
        import numpy as np
        r0, c0, r1, c1 = [int(v) for v in box]
        a = np.asarray(f, dtype=int)[r0:r1 + 1, c0:c1 + 1] % 16
        if a.size < 9: return ""
        vals, cnt = np.unique(a, return_counts=True)
        order = [int(v) for v, c in sorted(zip(vals, cnt), key=lambda t: -t[1])]
        inner = [v for v, c in zip(vals, cnt) if c >= 0.08 * a.size and int(v) != order[0]]
        if not inner: return ""
        return " with a " + " and ".join(COLOUR[int(v)] for v in inner[:2]) + " pattern inside"
    except Exception:
        return ""


def _desc_of(s, lvl, tid, f=None):
    d = getattr(s, "goals_seen", {}).get(lvl, {}).get(tid)
    if d and "box" in d: return _what(d)
    try: return f"a {COLOUR[int(str(tid).split('@')[0]) % 16]} thing"
    except Exception: return "a thing"


def _res_words(rs):
    c = {}
    for r in rs: c[r] = c.get(r, 0) + 1
    words = {"changed": "it changed the board", "refill": "it refilled the bar", "level": "it won the level",
             "nothing": "touching it did nothing", "pass": "I walked over it", "wall": "it blocked me",
             "unreachable": "I could not get to it", "untestable": "I could not test it"}
    return "; ".join(f"{words.get(k, k)}" + (f" ({v} times)" if v > 1 else "") for k, v in sorted(c.items(), key=lambda kv: -kv[1]))


def _region_words(r0, r1, c0, c1):
    r0, r1, c0, c1 = int(r0), int(r1), int(c0), int(c1)
    best, area = None, 0
    for L_, b in LABELS.items():                              # the listed thing that holds that picture, if any
        ov = max(0, min(r1, b[2]) - max(r0, b[0]) + 1) * max(0, min(c1, b[3]) - max(c0, b[1]) + 1)
        if ov > area: best, area = L_, ov
    if best and area >= 0.5 * (r1 - r0 + 1) * (c1 - c0 + 1):
        return f"the picture in {best}"
    return "the picture in " + _where((r0, c0, r1, c1))



FONT = {  # 5x7 letters for the labels drawn on the picture
 "A": ["01110","10001","10001","11111","10001","10001","10001"], "B": ["11110","10001","10001","11110","10001","10001","11110"],
 "C": ["01111","10000","10000","10000","10000","10000","01111"], "D": ["11110","10001","10001","10001","10001","10001","11110"],
 "E": ["11111","10000","10000","11110","10000","10000","11111"], "F": ["11111","10000","10000","11110","10000","10000","10000"],
 "G": ["01111","10000","10000","10011","10001","10001","01111"], "H": ["10001","10001","10001","11111","10001","10001","10001"],
 "J": ["00111","00010","00010","00010","00010","10010","01100"], "K": ["10001","10010","10100","11000","10100","10010","10001"],
 "L": ["10000","10000","10000","10000","10000","10000","11111"], "M": ["10001","11011","10101","10101","10001","10001","10001"],
 "N": ["10001","11001","10101","10011","10001","10001","10001"], "P": ["11110","10001","10001","11110","10000","10000","10000"],
 "Q": ["01110","10001","10001","10001","10101","10010","01101"], "R": ["11110","10001","10001","11110","10100","10010","10001"],
 "S": ["01111","10000","10000","01110","00001","00001","11110"], "T": ["11111","00100","00100","00100","00100","00100","00100"],
 "U": ["10001","10001","10001","10001","10001","10001","01110"], "V": ["10001","10001","10001","10001","10001","01010","00100"],
 "W": ["10001","10001","10001","10101","10101","10101","01010"], "X": ["10001","10001","01010","00100","01010","10001","10001"],
 "Y": ["10001","10001","01010","00100","00100","00100","00100"], "Z": ["11111","00001","00010","00100","01000","10000","11111"]}
LABELS = {}                              # letter -> box of the question being asked now (one game per process)


def labelled_png_b64(f, scale=8):
    """the screen in the game's colours with each letter drawn on a small white tag at its thing's top-left corner"""
    import base64, struct, zlib
    import numpy as np, mika_voice4 as v4
    a = np.asarray(f, dtype=int) % 16
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in v4.COLOUR_HEX], dtype=np.uint8)
    rgb = pal[a].repeat(scale, 0).repeat(scale, 1).copy()
    H, W, _ = rgb.shape
    for L_, box in LABELS.items():
        g = FONT.get(L_)
        if not g: continue
        k = 2                                                 # the letter drawn at 2x: a 20 x 24 px tag
        th, tw = 7 * k + 6, 5 * k + 6
        y0 = max(0, min(H - th, int(box[0]) * scale - th // 2)); x0 = max(0, min(W - tw, int(box[1]) * scale - tw // 2))
        rgb[y0:y0 + th, x0:x0 + tw] = (0, 0, 0)
        rgb[y0 + 1:y0 + th - 1, x0 + 1:x0 + tw - 1] = (255, 255, 255)
        for r, row in enumerate(g):
            for c, ch in enumerate(row):
                if ch == "1": rgb[y0 + 3 + r * k: y0 + 3 + (r + 1) * k, x0 + 3 + c * k: x0 + 3 + (c + 1) * k] = (0, 0, 0)
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(H))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def brief(s, goals, lvl, f):
    """her own request for help, in words a stranger who plays puzzle games could use"""
    import mika_mind as mm
    lvl = int(lvl)
    things = [g for g in goals if not str(g["id"]).startswith("open@")][:16]
    letters = {}; lines_things = []; LABELS.clear()
    life_res = s.life_res.get(lvl, {})
    for i, g in enumerate(things):
        tid = str(g["id"]); L_ = LETTERS[i]; letters[L_] = tid
        d = mm.describe(g, f)
        past = list(s.results.get(lvl, {}).get(tid, [])) + list(life_res.get(tid, []))
        if "box" in d: LABELS[L_] = d["box"]
        lines_things.append(f"- {L_}: {(_what(d) + _inside(f, d['box'])) if 'box' in d else _desc_of(s, lvl, tid)}" + (f" - {_res_words(past)}" if past else " - not touched yet"))
    rev = {v: k for k, v in letters.items()}
    def name(tid):
        return f"{rev[tid]} ({_desc_of(s, lvl, tid)})" if tid in rev else _desc_of(s, lvl, tid)
    P = []
    starting = START_WORDS in (getattr(s, "_v5_reason", {}).get(lvl) or "")
    if starting:
        P.append("I'm playing a puzzle game that has no instructions. Every move I make counts against me, so I'd like to "
                 "think before I press anything. The picture is the screen right now; the white tags with letters mark the "
                 "things I can touch (listed at the end).")
    else:
        P.append("I'm playing a puzzle game that has no instructions, and I'm stuck. The picture is the screen right now; "
                 "the white tags with letters mark the things I can touch (listed at the end).")
    # how I play
    ops = _ops_words()
    moves = [o for o in ops if o.startswith("She moves a body")]
    if moves:
        P.append("I move a piece around with the four arrow buttons; walls stop it, and I touch a thing by walking into it.")
    if any("lick" in o for o in ops):
        P.append("I can also click on things.")
    mt = BODY.get("meter: bar", ""); mm_ = re.search(r"bar colour (\d+) drains (\d+) cells per move.*?(\d+) moves left", mt)
    bud = re.search(r"budget colour (\d+) drains ([\d.]+)/press, (\d+) left", BODY.get("sleep", ""))
    if mm_ or bud:
        col = COLOUR[int((mm_ or bud).group(1)) % 16]; left = (mm_.group(3) if mm_ else bud.group(3))
        P.append(f"A {col} bar shrinks every move; when it runs out the level starts over. I have about {left} moves left now.")
        fills = sorted({t for (lv_, t) in getattr(s, "refill_ids", set())})
        if fills:
            P.append("Touching " + " or ".join(sorted({_desc_of(s, lvl, t) for t in fills})) + " refilled the bar before.")
    # what I learned from the levels I won
    for lv in sorted(set(s.recipes)):
        r = s.recipes.get(lv) or []
        if not r: continue
        steps, last = [], r[-1]
        k = 1
        for i, t in enumerate(r[:-1]):
            if i + 1 < len(r) - 1 and r[i + 1] == t: k += 1; continue
            res = [x for x in s.results.get(lv, {}).get(t, []) if x in ("changed", "refill")]
            act = "refilled the bar" if (lv, t) in getattr(s, "refill_ids", set()) else "changed something"
            steps.append(f"touched {_desc_of(s, lv, t)}" + (f" {k} times" if k > 1 else "") + f" ({act})"); k = 1
        P.append(f"I won level {lv + 1} like this: " + ", then ".join(steps + [f"went to {_desc_of(s, lv, last)}, and the level was won"]) + ".")
    rel = BODY.get("relation") or ""
    m = re.match(r"relation: (\S+) -> region rows (\d+)-(\d+) cols (\d+)-(\d+) \((\d+) states seen\) -> (\S+)", rel)
    src = tgt = None
    if m:
        src, r0, r1, c0, c1, k, tgt = m.groups()
        P.append(f"Here, touching {name(src)} changes {_region_words(r0, r1, c0, c1)} (I've seen it {k} different ways). "
                 f"I think it has to end up matching the picture inside {name(tgt)}, and then I go there.")
    else:
        rc = BODY.get("relation carried") or ""
        m = re.search(r"by colour: (\S+) -> region rows (\d+)-(\d+) cols (\d+)-(\d+) -> (\S+)", rc)
        if m:
            src, r0, r1, c0, c1, tgt = m.groups()
            P.append(f"On the last level, touching a {COLOUR[int(src.split('@')[0]) % 16]} thing changed {_region_words(r0, r1, c0, c1)} "
                     f"until it matched the picture inside the target. I expect the same here: maybe {name(src)} and {name(tgt)}.")
    # what I've done on this level
    seq = [(t, r) for t, r in getattr(s, "_v5_seq", {}).get(lvl, []) if not str(t).startswith("open@")][-10:]
    if seq:
        runs = []
        for t, r in seq:
            if runs and runs[-1][0] == t and runs[-1][1] == r: runs[-1][2] += 1
            else: runs.append([t, r, 1])
        P.append("On this level I've tried, in order: " + "; ".join(
            f"{name(t)}: {_res_words([r])}" + (f" ({k} times in a row)" if k > 1 else "") for t, r, k in runs) + ".")
    n_reset = sum(1 for lv_, _ in getattr(s, "resets_at", []) if int(lv_) == lvl)
    why_now0 = getattr(s, "_v5_reason", {}).get(lvl) or ""
    if n_reset and "started over" not in why_now0:
        P.append(f"The level has started over {n_reset} time{'s' if n_reset > 1 else ''} so far.")
    # catching up
    last = getattr(s, "_v5_last", {}).get(lvl)
    if last:
        prev = [c for c in s.j.get("claims", []) if c.get("level") == lvl][-3:]
        if prev:
            P.append("Last time you suggested " + "; ".join(
                f"{name(c['try'])}, expecting it to {({'changed': 'change something', 'refill': 'refill the bar', 'level': 'win the level', 'pass': 'let me through'}).get(c['expect'], c['expect'])} - "
                + ({"held": "you were right", "missed": f"it didn't ({_res_words([c.get('result')])})", "untried": f"I couldn't try it ({_res_words([c.get('result')])})"}.get(c.get("outcome"), "not tried yet"))
                for c in prev) + ".")
        if last.get("said"): P.append(f"Last time you told me: \"{last['said']}\"")
        elif last.get("game"): P.append(f"You thought the goal was: {last['game']}")
    why_now = getattr(s, "_v5_reason", {}).get(lvl)
    if why_now: P.append(why_now)
    # the question
    changed = [t for t, rs in life_res.items() if any(r in ("changed", "refill", "level") for r in rs) and not t.startswith("open@")]
    if src:
        src_res = list(life_res.get(src, [])) + [r for t, rs in life_res.items() if t != src and t.split("@")[0] == src.split("@")[0] for r in rs]
        unreach = sum(1 for r in src_res if r in ("unreachable", "untestable")) + LEVEL_EVENTS["unreach_src"]
        if unreach >= 2:
            q = (f"I can't get to {name(src)} - walls are in the way or I run out of moves first ({unreach} tries). "
                 f"How could I get there, or is there another way to change {('that picture')}?")
        elif sum(1 for lv_, _ in getattr(s, "resets_at", []) if int(lv_) == lvl) >= 1:
            q = (f"Changing the picture with {name(src)} hasn't been enough - the level keeps starting over. What else might have to "
                 f"match the picture inside {name(tgt) if tgt else 'the target'}: its colour, its shape, its size? Which thing could change that?")
        else:
            q = f"Is there anything I should do before or while I change the picture with {name(src)}?"
    elif changed:
        q = (f"Only {', '.join(name(t) for t in changed[:4])} did anything here. What do you think the goal of this level is, "
             f"and what should I try?")
    else:
        q = "Nothing I've touched here does anything yet. What kind of puzzle does this look like to you, and what would you try first?"
    if starting and lvl == 0:
        q = ("What kind of puzzle does this look like to you, what do you think the goal is, and what would you try first "
             "so I waste as few moves as possible?")
    elif starting:
        q = ("This is the next level. What looks new compared with what I described, what do you think I have to do here, "
             "and what would you try first so I waste as few moves as possible?")
    P.append("My question: " + q)
    text = "\n\n".join(P) + "\n\nThe things I can touch:\n" + "\n".join(lines_things) + "\n\n" + FORMAT5L
    return text, letters, q


FORMAT5L = ("Answer me like a friend, in a few plain sentences. Then finish with one line that starts with \"Try:\" and "
            "lists up to three letters, best first, each with a few words on what you think it will do - for example: "
            "Try: B (it might turn the picture), then D (I think it wins the level).")


def expect_of(words):
    w = (words or "").lower()
    if any(k in w for k in ("win", "level", "finish", "solve", "complete", "exit", "goal")): return "level"
    if any(k in w for k in ("refill", "fill the bar", "fills the bar", "more moves", "energy", "recharge")): return "refill"
    if any(k in w for k in ("through", "pass", "walk over", "open the way", "path")): return "pass"
    return "changed"


def parse_friend(text):
    """the friend's plain answer -> (claims, goal sentence): the letters on the 'Try:' line, else letters named after a verb"""
    text = text or ""
    claims = []
    tl = [l for l in text.splitlines() if re.match(r"^\s*\**\s*try\b", l, re.I)]
    if tl:
        line = tl[-1].split(":", 1)[-1] if ":" in tl[-1] else tl[-1]
        for L_, why in re.findall(r"\b([A-HJ-NP-Z])\b(?:\s*\(([^)]*)\))?", line):
            if L_ not in [c["try"] for c in claims]: claims.append({"try": L_, "expect": expect_of(why), "why": why})
    if not claims:
        for L_ in re.findall(r"(?:try|touch|go to|walk (?:in)?to|bump into|click(?: on)?|press|use|head (?:to|for))\s+(?:thing\s+)?([A-HJ-NP-Z])\b", text):
            if L_ not in [c["try"] for c in claims]: claims.append({"try": L_, "expect": "changed", "why": ""})
    body = re.sub(r"^\s*\**\s*try\b.*$", "", text, flags=re.I | re.M).strip()
    sents = re.split(r"(?<=[.!?])\s+", body)
    gist = " ".join(sents[:2])[:240]
    goal = next((x for x in sents if re.search(r"\bgoal\b|\bthe point\b|\byou need to\b|\bthe aim\b", x, re.I)), sents[0] if sents else "")
    out = [{"try": c["try"], "expect": c["expect"], "because": (c["why"] + " - " if c["why"] else "") + gist} for c in claims[:3]]
    return out, goal[:240]


def install():
    if not ON:
        return
    import mika_mind as mm, mika_think as mt
    TM = mt.ThinkingMind
    if getattr(TM, "_v5", False):
        return
    mt.SHELL_SYSTEM = SYSTEM5

    orig_observe = TM.observe
    def observe(s, e):
        try:
            lv = int(e.get("level", -1))
            s._v5_seq = getattr(s, "_v5_seq", {}); s._v5_seq.setdefault(lv, []).append((str(e.get("id")), str(e.get("result"))))
        except Exception:
            pass
        return orig_observe(s, e)
    TM.observe = observe

    orig_ev = TM._evidence                                   # voice4's (kept as the fallback)
    def _evidence(s, goals, lvl, f):
        try:
            text, letters, q = brief(s, goals, lvl, f)
            s._v5_letters = getattr(s, "_v5_letters", {}); s._v5_letters[int(lvl)] = letters
            s._v5_q = getattr(s, "_v5_q", {}); s._v5_q[int(lvl)] = q
            return text
        except Exception as e_:
            s.log(f"  think: voice5 briefing failed ({str(e_)[:120]}); the plain question goes")
            return orig_ev(s, goals, lvl, f)
    TM._evidence = _evidence

    orig_check = TM._check                                   # a letter in the answer -> the thing's id, then her facts check
    def _check(s, c, lvl, on_screen):
        L_ = str(c.get("try", "")).strip().strip(".").upper()
        letters = getattr(s, "_v5_letters", {}).get(int(lvl), {})
        if L_ in letters: c["try"] = letters[L_]
        return orig_check(s, c, lvl, on_screen)
    TM._check = _check

    import time as _time
    mt.CAP = 10 ** 6                                          # no count of questions per level: the game says when to ask
    T0 = float(os.environ.get("MIKA_T0", _time.time())); DEAD = float(os.environ.get("MIKA_DEADLINE_S", 7.5 * 3600))

    def due(s, lvl):
        """the game's own reasons to ask: the level was put back, the bar is nearly gone with nothing changed since the
        last reset, her rule stopped working, or (once) six things tried with nothing changed. Only Kaggle's clock is an
        outside limit: in the last fifth of the run she stops asking so every game can finish."""
        if _time.time() - T0 > 0.8 * DEAD: return None
        ev = getattr(s, "_v5_ev", None)
        if ev is None: ev = s._v5_ev = {}
        e = ev.setdefault(lvl, {"resets": 0, "low_at": -1, "unreach": 0, "veto": False, "first": False})
        resets = sum(1 for lv_, _ in getattr(s, "resets_at", []) if int(lv_) == lvl)
        life_res = s.life_res.get(lvl, {})
        if ASK_FIRST and not e.get("start") and not life_res and not s.results.get(lvl):
            e["start"] = True                                  # once per level per game, before its first experiment
            return (f"I just reached level {lvl + 1}. " if lvl else "I just started this game. ") + START_WORDS + "."
        if resets > e["resets"]:
            e["resets"] = resets; return "The level just started over" + (f" - that's {resets} times now." if resets > 1 else ".")
        if lvl in getattr(s, "rel_vetoed", set()) and not e["veto"]:
            e["veto"] = True; return "The rule that worked before keeps failing here, so I've stopped repeating it."
        if LEVEL_EVENTS["unreach_src"] > e["unreach"] and LEVEL_EVENTS["unreach_src"] >= 2:
            e["unreach"] = LEVEL_EVENTS["unreach_src"]; return "I keep failing to reach the thing I need."
        full = max(getattr(s, "_v5_full", {}).get(lvl, 0), s.energy or 0)
        s._v5_full = getattr(s, "_v5_full", {}); s._v5_full[lvl] = full
        if s.energy is not None and full and s.energy <= 0.25 * full and e["low_at"] != resets:
            changed_since = [t for t, rs in life_res.items() if any(r in ("changed", "level") for r in rs[-3:])]
            if not changed_since:
                e["low_at"] = resets; return "My bar is almost empty and nothing has changed since the level last started over."
        if not e["first"] and s.exp_since.get(lvl, 0) >= mt.STALL:
            e["first"] = True; return "I've tried several things here and nothing has changed yet."
        if EXTRA_DUE is not None:                              # more reasons from other floors (mika_prism)
            try:
                r_ = EXTRA_DUE(s, lvl, e)
            except Exception:
                r_ = None
            if r_: return r_
        return None

    orig_think = TM._maybe_think
    def _maybe_think(s, goals, lvl, f):
        lvl_i = int(lvl)
        try:
            reason = due(s, lvl_i) if (s.shell and lvl_i not in s.cleared and not s.active.get(lvl_i)) else None
        except Exception:
            reason = None
        s._v5_reason = getattr(s, "_v5_reason", {}); s._v5_reason[lvl_i] = reason
        keep = s.exp_since.get(lvl_i, 0)
        s.exp_since[lvl_i] = mt.STALL if reason else 0          # the base gate asks exactly when the game gave a reason
        if reason: s.log(f"  think: level {lvl_i + 1}: she has a reason to ask - {reason}")
        r = orig_think(s, goals, lvl, f)
        if not reason: s.exp_since[lvl_i] = keep
        try:                                                  # remember what she asked and what the voice thought the game was
            lvl_ = int(lvl)
            q = getattr(s, "_v5_q", {}).get(lvl_)
            ans = getattr(s, "_v5_answer", None)
            if q and ans is not None:
                game, said = None, None
                try:
                    o = json.loads(ans); game = o.get("game"); said = o.get("said")
                except Exception:
                    m = re.search(r"\"game\"\s*:\s*\"([^\"]+)\"", ans or ""); game = m.group(1) if m else None
                if said:
                    said = re.sub(r"^\s*\**\s*try\b.*$", "", said, flags=re.I | re.M).strip()
                    said = " ".join(re.split(r"(?<=[.!?])\s+", said)[:3])[:400]
                s._v5_last = getattr(s, "_v5_last", {}); s._v5_last[lvl_] = {"question": q, "game": game, "said": said}
                if game: s.log(f"  think: level {lvl_ + 1}: the voice thinks the goal is: {str(game)[:160]}")
                s._v5_answer = None
        except Exception:
            pass
        return r
    TM._maybe_think = _maybe_think

    orig_t = TM._t
    def _t(s, kind, **kw):
        if kind == "call":
            s._v5_answer = kw.get("answer")
        if kind in ("snap", "call"):
            kw.setdefault("letters", dict(getattr(s, "_v5_letters", {}).get(int(kw.get("level", -1)), {})))
            kw.setdefault("labels", {k: list(v) for k, v in LABELS.items()})
        return orig_t(s, kind, **kw)
    TM._t = _t
    orig_post = mm._post
    def _post(url, body, timeout=180):
        msgs = body.get("messages") or []
        friend = url.endswith("/api/chat") and msgs and msgs[0].get("content") == SYSTEM5
        if friend:
            body = dict(body); body.pop("format", None)
            body["options"] = dict(body.get("options") or {}, num_predict=700, temperature=0.5)
        r = orig_post(url, body, timeout)
        if friend:
            try:
                said = (r.get("message") or {}).get("content", "")
                claims, goal = parse_friend(said)
                r = dict(r); r["message"] = {"role": "assistant", "content": json.dumps({"claims": claims, "game": goal, "said": said})}
            except Exception:
                pass
        return r
    mm._post = _post

    import mika_voice4 as v4
    v4.png_b64 = labelled_png_b64                            # voice4 attaches the picture; now it carries the letters
    TM._v5 = True
