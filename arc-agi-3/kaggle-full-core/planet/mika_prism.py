"""mika_prism.py - THE TUBE AND THE PRISM (Nov 2 2026, the last attempt; MIKA_PRISM=1, on top of voice4 + voice5).

Jonathan, Oct 31:
  "its like a collection of all those A=B=C chains isnt it? and with those panels its like those chains would cut across them"
  "i think its like a tube too, not just a ring. so its like a wall she looks at and has to turn to see. i think its attached
   to the roof of our space, and then all of our floors would be able to see it. we also had the reflective layer between her
   core and that layer. its like the webbing at the edge of the core turns into a prism that bends things towards the llm ring"
  "i think making that kind of change on the last attempt is the irrational thing here"

In her terms:
  THE TUBE     the language model, read as a store of chains nobody has certified: touch A -> B changes -> then C. One narrow
               question shows one face of it, so she has to turn to choose which face she looks at.
  THE FLOORS   the tube hangs from the roof, so every floor of her can turn to it, each with its own face and at its own event:
                 planner    GOAL   what wins the level, in order                    (a new level; a plan ran out)
                 eye        WHAT   what the lettered things are for                 (things tried, nothing changed)
                 relations  LINK   what a change she caused is connected to         (things changed, no relation yet)
                 core       MATCH  what else has to match before the target takes it (a relation, but the level resets)
                 body       REACH  how to get to the thing she needs                (the source is out of reach)
                 meter      ORDER  what to do first with the moves left              (bar low, nothing changed)
  THE PRISM    the edge of her core splits what she knows into the pieces her chain is still missing (the gaps) and bends
               the question toward the face that answers the strongest one. She does not ask the same face twice in a row
               unless something changed; otherwise she turns to the next gap.
  REFLECTION   the answer comes back as chains in her terms ("Chain: B (turns the picture in A) -> D (wins the level)"). The
               first link becomes a claim her facts check filters. When a link holds it turns GOLD, is kept for the whole game,
               and the next link of the same chain goes to the front; a link that misses breaks the chain. Every later
               question starts with what is gold, so the model is told what she has certified.
"""
from __future__ import annotations
import os, re, time

ON = os.environ.get("MIKA_PRISM", "0") == "1"
FACES = ["GOAL", "WHAT", "LINK", "MATCH", "REACH", "ORDER"]            # the ring she turns through
FLOOR = {"GOAL": "planner", "WHAT": "eye", "LINK": "relations", "MATCH": "core", "REACH": "body", "ORDER": "meter"}
LAST_CHAINS = None                                                      # chains parsed from the latest answer (one game per process)
FACE_NOW = {}                                                           # level -> the face of the question being asked

FORMAT_PRISM = ("Answer me like a friend, in a few plain sentences. Then write one or two lines that start with \"Chain:\": a short "
                "plan as letters joined by arrows, each letter with a few words on what you expect it to do - for example: "
                "Chain: B (turns the picture in A) -> D (wins the level). Finish with one line that starts with \"Try:\" and the "
                "first letter of your best chain.")
GOLD_MAX = 8


def _gaps(s, lvl, v5):
    """the prism: the pieces her chain for this level is still missing, strongest first, as (face, words)"""
    life_res = s.life_res.get(lvl, {})
    tried = set(life_res) | set(s.results.get(lvl, {}))
    rel = bool(v5.BODY.get("relation") or v5.BODY.get("relation carried"))
    changed = [t for t, rs in life_res.items() if any(r in ("changed", "refill") for r in rs) and not str(t).startswith("open@")]
    resets = sum(1 for lv_, _ in getattr(s, "resets_at", []) if int(lv_) == lvl)
    screen = [t for t in getattr(s, "_prism_screen", {}).get(lvl, {}) if not str(t).startswith("open@")]
    untried = [t for t in screen if t not in tried]
    out = []
    if v5.LEVEL_EVENTS.get("unreach_src", 0) >= 2: out.append(("REACH", "how to get to the thing I need"))
    if rel and resets >= 1: out.append(("MATCH", "what else has to match before the target takes it"))
    if changed and not rel: out.append(("LINK", "what the changes I caused are connected to"))
    full = getattr(s, "_v5_full", {}).get(lvl, 0)
    if s.energy is not None and full and s.energy <= 0.25 * full: out.append(("ORDER", "what to do first with the moves I have left"))
    if len(untried) >= 3: out.append(("WHAT", "what most of these things are for"))
    if lvl not in s.cleared: out.append(("GOAL", "what wins this level"))
    return out


def _face_of_reason(reason, gaps, v5):
    r = reason or ""
    have = [g for g, _ in gaps]
    if v5.START_WORDS in r: return "GOAL"
    if "plan worked" in r: return "GOAL"
    if "connect to" in r: return "LINK"
    if "failing to reach" in r: return "REACH"
    if "bar is almost empty" in r: return "ORDER"
    if "keeps failing" in r: return "MATCH"
    if "nothing has changed yet" in r: return "WHAT"
    if "started over" in r:
        for g in ("MATCH", "LINK", "REACH"):
            if g in have: return g
        return "GOAL"
    return have[0] if have else "GOAL"


def _turn(s, lvl, face, gaps):
    """do not look at the same face twice in a row unless something changed since: turn to the next gap on the ring"""
    s._prism_last = getattr(s, "_prism_last", {})
    info = (len(s.j.get("gold", [])), sum(len(v) for v in s.life_res.get(lvl, {}).values() if any(r in ("changed", "refill") for r in v)))
    last = s._prism_last.get(lvl)
    if last and last[0] == face and last[1] == info:
        have = [g for g, _ in gaps]
        ring = FACES[FACES.index(face) + 1:] + FACES[:FACES.index(face)]
        nxt = next((g for g in ring if g in have), None)
        if nxt: face = nxt
    s._prism_last[lvl] = (face, info)
    return face


def _gold_words(s):
    g = s.j.get("gold", [])[-GOLD_MAX:]
    if not g: return None
    return ("What I've confirmed so far (each of these held when I tested it): "
            + "; ".join(f"{x['what']} {x['did']} (level {x['level'] + 1})" for x in g) + ".")


DID = {"changed": "changed something", "refill": "refilled the bar", "level": "won the level", "pass": "let me through"}


def install():
    if not ON:
        return
    import mika_voice5 as v5, mika_think as mt
    TM = mt.ThinkingMind
    if getattr(TM, "_prism", False):
        return

    # ---- the floors: more reasons to turn to the tube than being stuck
    def extra_due(s, lvl, e):
        if lvl in getattr(s, "_prism_spent", set()) and not e.get("spent"):
            e["spent"] = True; return "Your plan worked as far as it went, but the level isn't won yet."
        life_res = s.life_res.get(lvl, {})
        changed = [t for t, rs in life_res.items() if any(r in ("changed", "refill") for r in rs) and not str(t).startswith("open@")]
        rel = bool(v5.BODY.get("relation") or v5.BODY.get("relation carried"))
        if changed and not rel and not e.get("link") and s.exp_since.get(lvl, 0) >= 3:
            e["link"] = True; return "Some things I touched changed the screen, but I can't tell what they connect to."
        return None
    v5.EXTRA_DUE = extra_due

    # ---- the prism: her request bent toward one face, with what is gold and what is still missing
    orig_brief = v5.brief
    def brief(s, goals, lvl, f):
        text, letters, q = orig_brief(s, goals, lvl, f)
        try:
            import mika_voice4 as v4
            lvl_i = int(lvl)
            asking = v4.CURRENT.get("frame") is not None             # a real question (voice4 snapshots brief too, framelessly)
            reason = getattr(s, "_v5_reason", {}).get(lvl_i)
            gaps = _gaps(s, lvl_i, v5)
            if asking:
                face = _turn(s, lvl_i, _face_of_reason(reason, gaps, v5), gaps)
                FACE_NOW[lvl_i] = face
            else:
                face = FACE_NOW.get(lvl_i) or _face_of_reason(reason, gaps, v5)
            rev = {v: k for k, v in letters.items()}
            def name(t): return f"{rev[t]} ({v5._desc_of(s, lvl_i, t)})" if t in rev else v5._desc_of(s, lvl_i, t)
            life_res = s.life_res.get(lvl_i, {})
            changed = [t for t, rs in life_res.items() if any(r in ("changed", "refill") for r in rs) and not str(t).startswith("open@")]
            new_q = None
            if face == "GOAL":
                new_q = ("What kind of puzzle does this look like to you, what do you think wins the level, and what would you do, "
                         "in order, so I waste as few moves as possible?") if lvl_i == 0 and not s.cleared else (
                         "What do you think wins this level, step by step, using what I've confirmed so far?")
            elif face == "WHAT":
                new_q = ("Looking at the picture, what do you think the lettered things are for - something to collect, a switch, a "
                         "key, a door, a wall, something to push, the goal? Just the ones you can guess, and which one you'd touch first.")
            elif face == "LINK" and changed:
                new_q = (f"When I touched {', '.join(name(t) for t in changed[:3])}, something on the screen changed, but I can't "
                         f"tell what that's connected to. What do you think it's for, and what should I do next?")
            elif face == "ORDER":
                new_q = "My bar is almost empty and nothing has changed. With the moves I have left, what should I do first?"
            elif face == "REACH" and "can't get to" not in q:
                new_q = "I keep failing to get to the thing I need. Looking at the picture, how could I get there?"
            if new_q:
                text = text.replace("My question: " + q, "My question: " + new_q); q = new_q
            pre = []
            gw = _gold_words(s)
            if gw: pre.append(gw)
            missing = [w for g, w in gaps if g != face][:3]
            if missing: pre.append("What I haven't worked out yet: " + "; ".join(missing) + ".")
            try:                                                     # THE Q-TUBE (Nov 2): her fit, a tool's pin in the socket
                import qtube_fit
                if qtube_fit.on() and asking:
                    qn = qtube_fit.take()
                    if qn: pre.append("What my shape fit says (a shape laid on another after the best spin or turn-over): " + "; ".join(qn) + ".")
            except Exception:
                pass
            if pre:
                text = text.replace("My question: ", "\n\n".join(pre) + "\n\nMy question: ", 1)
            text = text.replace(v5.FORMAT5L, FORMAT_PRISM)
            if asking:
                s.log(f"  prism: level {lvl_i + 1}: she turns to the {face} face (the {FLOOR[face]} floor asks); "
                      f"gaps {[g for g, _ in gaps]}, gold {len(s.j.get('gold', []))}")
                s._t("prism", level=lvl_i, face=face, gaps=[g for g, _ in gaps], reason=reason, gold=len(s.j.get("gold", [])))
        except Exception as e_:
            s.log(f"  prism: briefing failed ({str(e_)[:120]}); the plain question goes")
        return text, letters, q
    v5.brief = brief

    # ---- the reflection: the answer's chains, in her terms
    orig_parse = v5.parse_friend
    def parse_friend(text):
        global LAST_CHAINS
        claims, goal = orig_parse(text)
        chains = []
        for line in (text or "").splitlines():
            if not re.match(r"^\s*[\*\-]*\s*chain\b", line, re.I): continue
            body = line.split(":", 1)[-1]
            steps = []
            for part in re.split(r"->|→|=>|, then | then ", body):
                m = re.search(r"\b([A-HJ-NP-Z])\b(?:\s*\(([^)]*)\))?", part)
                if m and m.group(1) not in [x[0] for x in steps]: steps.append((m.group(1), m.group(2) or part.strip()))
            if steps: chains.append(steps)
        chains = chains[:2]
        LAST_CHAINS = chains
        have = [c["try"] for c in claims]
        for ch in chains:                                        # every chain's first link is proposed
            L_, w = ch[0]
            if L_ not in have and len(claims) < 3:
                claims.append({"try": L_, "expect": v5.expect_of(w), "because": f"{w} - first link of the plan"}); have.append(L_)
        return claims, goal
    v5.parse_friend = parse_friend

    orig_think = TM._maybe_think
    def _maybe_think(s, goals, lvl, f):
        global LAST_CHAINS
        lvl_i = int(lvl)
        s._prism_screen = getattr(s, "_prism_screen", {}); s._prism_screen[lvl_i] = {str(g["id"]): g for g in goals}
        LAST_CHAINS = None
        before = s.calls.get(lvl_i, 0)
        r = orig_think(s, goals, lvl, f)
        if s.calls.get(lvl_i, 0) > before and LAST_CHAINS:
            letters = getattr(s, "_v5_letters", {}).get(lvl_i, {})
            s._prism_chains = getattr(s, "_prism_chains", {})
            for ch in LAST_CHAINS:
                steps = [(letters[L_], v5.expect_of(w), w) for L_, w in ch if L_ in letters]
                if len(steps) >= 1:
                    s._prism_chains.setdefault(lvl_i, []).append({"steps": steps, "i": 0, "face": FACE_NOW.get(lvl_i), "broken": False})
                    s.log(f"  prism: level {lvl_i + 1}: chain from the {FACE_NOW.get(lvl_i)} face: "
                          + " -> ".join(f"{t} ({e})" for t, e, _ in steps))
            s._prism_chains[lvl_i] = s._prism_chains.get(lvl_i, [])[-6:]
            s._t("chains", level=lvl_i, face=FACE_NOW.get(lvl_i), chains=[[(t, e, w[:80]) for t, e, w in c["steps"]] for c in s._prism_chains[lvl_i]])
            LAST_CHAINS = None
        return r
    TM._maybe_think = _maybe_think

    # ---- certification, link by link: a link that holds turns gold and the next link goes to the front
    orig_observe = TM.observe
    def observe(s, e):
        lv = int(e.get("level", -1)); tid = str(e.get("id"))
        c = (s.active.get(lv) or {}).get(tid)
        out = orig_observe(s, e)
        try:
            if c is None or c.get("outcome") not in ("held", "missed"): return out
            for ch in getattr(s, "_prism_chains", {}).get(lv, []):
                if ch["broken"] or ch["i"] >= len(ch["steps"]) or ch["steps"][ch["i"]][0] != tid: continue
                if c["outcome"] == "missed":
                    ch["broken"] = True
                    s.log(f"  prism: level {lv + 1}: link {tid} missed - that chain is broken")
                    continue
                g = {"level": lv, "what": "touching " + __import__("mika_voice5")._desc_of(s, lv, tid),
                     "did": DID.get(c.get("result"), str(c.get("result"))), "t": time.strftime("%Y-%m-%d %H:%M:%S")}
                gold = s.j.setdefault("gold", [])
                if not any(x["what"] == g["what"] and x["level"] == lv for x in gold): gold.append(g)
                s.j["gold"] = gold[-40:]
                ch["i"] += 1
                s.log(f"  prism: level {lv + 1}: link {tid} held - gold ({g['what']} {g['did']})")
                s._t("gold", level=lv, link=tid, did=g["did"], chain_at=ch["i"], chain_len=len(ch["steps"]))
                if ch["i"] >= len(ch["steps"]):
                    if c.get("result") != "level":
                        s._prism_spent = getattr(s, "_prism_spent", set()) | {lv}
                    continue
                nid, nexp, nw = ch["steps"][ch["i"]]
                claim = {"level": lv, "try": nid, "expect": nexp, "because": f"next link of the plan: {nw}"[:240],
                         "shell": s.shell, "made": time.strftime("%Y-%m-%d %H:%M:%S")}
                why = s._check(claim, lv, getattr(s, "_prism_screen", {}).get(lv, {}))
                if why:
                    ch["broken"] = True
                    s.log(f"  prism: level {lv + 1}: next link {nid} fails her check ({why}) - chain stops")
                    continue
                claim["rank"] = -1; claim["at"] = getattr(s, "exp_all", {}).get(lv, 0)
                s.active.setdefault(lv, {})[nid] = claim; s.tested.add((lv, nid))
                s.log(f"  prism: level {lv + 1}: next link {nid} -> {nexp} goes first")
        except Exception as e_:
            s.log(f"  prism: review failed ({str(e_)[:120]})")
        return out
    TM.observe = observe
    TM._prism = True
