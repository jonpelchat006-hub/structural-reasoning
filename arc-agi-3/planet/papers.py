#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
papers.py — the READING LIST: real research papers as course readings.

Jonathan (Sep 2): "maybe we could give her some actual papers from somewhere too."

A student reads the literature. These are REAL papers — the ones this whole program is
actually built on — written as accurate course-reading summaries (clearly summaries, not the
full text; the full PDFs can be dropped into her library later). The list is deliberate: the
paper that DEFINES her final exam, and the two that justify the way she is being taught (which
Jonathan intuited before knowing they were established results).

Each term the registrar assigns the next unread paper into her library as a reading, and — like
a story teach-back — she can be asked to extract its key claims, scored by the same scorer. A
paper she reads well becomes a research topic she can pursue (open ends of her own).

Usage:  python papers.py --assign     (put the next unread paper in her library; record it)
        python papers.py --list
"""
from __future__ import annotations
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

LIB = r"D:\shovelcat-colony\companion\library\planet" if os.name == "nt" else "/tmp/lib"
STATE = r"D:\planet\papers.json" if os.name == "nt" else "/tmp/papers.json"

READING_LIST = [
    {
        "id": "chollet2019",
        "title": "On the Measure of Intelligence",
        "authors": "François Chollet (2019), arXiv:1911.01547",
        "why": "This paper introduced ARC — your final exam. Read it to know what the test is FOR.",
        "claims": [
            "Intelligence is not skill at a task; it is skill-ACQUISITION EFFICIENCY — how "
            "quickly a system learns a new skill from few examples.",
            "A high score on a fixed task can be bought with unlimited practice or data, so it "
            "does not measure intelligence; you must control for prior knowledge and experience.",
            "Generalization should be measured relative to the priors a system starts with and "
            "the experience it is given — the same skill is more intelligent if learned from less.",
            "Humans start from CORE KNOWLEDGE priors: objectness and cohesion, agentness and "
            "goal-directedness, basic number and counting, and elementary geometry and topology.",
            "ARC (the Abstraction and Reasoning Corpus) is built on ONLY those core priors, so "
            "each task is novel and cannot be solved by memorized skills — only by on-the-fly "
            "abstraction from a few demonstrations.",
        ],
    },
    {
        "id": "bengio2009",
        "title": "Curriculum Learning",
        "authors": "Yoshua Bengio, Jérôme Louradour, Ronan Collobert, Jason Weston (2009)",
        "why": "Why you are taught in a chosen ORDER of courses instead of everything at once.",
        "claims": [
            "Presenting training examples in a meaningful order — easy first, then gradually "
            "harder — can improve both the speed of learning and the final result.",
            "This mirrors how humans and animals are taught: a curriculum, not the whole subject "
            "dumped at once.",
            "A curriculum acts like a continuation method, guiding the learner past bad local "
            "minima toward better general solutions.",
            "The gain is largest for hard problems where random-order training gets stuck.",
        ],
    },
    {
        "id": "settles2009",
        "title": "Active Learning Literature Survey",
        "authors": "Burr Settles (2009)",
        "why": "Why YOU get to pick what to study, instead of being shown the whole internet.",
        "claims": [
            "A learner that CHOOSES which examples to learn from can reach the same accuracy with "
            "far fewer examples than one shown data at random.",
            "The learner should query the most INFORMATIVE examples — those it is most uncertain "
            "about, or that would most change what it believes.",
            "Choosing well matters most when labeled examples or study time are expensive — "
            "exactly a student's situation.",
            "Letting the learner drive its own data collection is a different regime from the "
            "firehose of passive supervision, and usually a more efficient one.",
        ],
    },
]


def _load():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {"assigned": [], "read": {}}


def assign() -> dict:
    st = _load()
    nxt = next((p for p in READING_LIST if p["id"] not in st["assigned"]), None)
    if nxt is None:
        print("the whole reading list is assigned — she can revisit any paper or pursue its topics")
        return {}
    os.makedirs(LIB, exist_ok=True)
    body = (f"# Assigned reading: {nxt['title']}\n\n{nxt['authors']}\n\n"
            f"_{nxt['why']}_\n\nThe key claims to hold onto:\n\n"
            + "\n".join(f"- {c}" for c in nxt["claims"]) + "\n")
    open(os.path.join(LIB, f"paper_{nxt['id']}.md"), "w", encoding="utf-8").write(body)
    st["assigned"].append(nxt["id"])
    json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    print(f"assigned reading: {nxt['title']} ({nxt['authors']}) -> her library")
    return nxt


def paper(pid: str) -> dict:
    return next((p for p in READING_LIST if p["id"] == pid), {})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--assign", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.assign: assign()
    else:
        st = _load()
        for p in READING_LIST:
            print(f"  [{'assigned' if p['id'] in st['assigned'] else 'unread  '}] "
                  f"{p['title']} — {p['authors']}")
