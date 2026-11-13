"""Oct 16 night: give old lives their reset positions (where in the experiment list each reset fell), read from the
play logs, so a recipe can be cut at the level's last put-back. Only writes a life when the log's experiment count
matches the journal's exactly. Usage: python backfill_resets.py ls20 1 D:\\planet\\mika\\logs\\ls20_20261013_083813.log [--write]"""
import json, re, sys

game, life_no, log_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
write = "--write" in sys.argv
J = rf"D:\planet\mika\{game}.json"
j = json.load(open(J, encoding="utf-8"))
life = j["lives"][life_no - 1]
exps = life["experiments"]
res = re.compile(r"experiment (\S+?)(?: \(relation \w+\))?: (?!path of)([A-Za-z]+)")
lines = open(log_path, encoding="utf-8", errors="replace").read().splitlines()
# the life's own stretch of the log: from its header to the next life's header
starts = [i for i, l in enumerate(lines) if re.match(rf"life {life_no} of {game}", l.strip())]
i0 = starts[0] if starts else 0
ends = [i for i, l in enumerate(lines) if i > i0 and re.match(rf"life \d+ of {game}", l.strip())]
i1 = ends[0] if ends else len(lines)
seen, resets, lvl, got = 0, [], 0, []
for l in lines[i0:i1]:
    m = res.search(l)
    if m and not l.strip().startswith("mind:"):
        got.append((m.group(1), m.group(2).lower())); seen += 1
    if re.search(r"\bRESET #\d+", l): resets.append([lvl, seen])
    mm = re.search(r">>> LEVEL (\d+) at press", l)
    if mm: lvl = int(mm.group(1))
print(f"log: {seen} experiment results, journal: {len(exps)}; resets {len(resets)}")
bad = [(k, a, b) for k, (a, b) in enumerate(zip(got, exps)) if a[0] != str(b["id"]) or a[1] != str(b["result"]).lower()]
print("mismatches:", bad[:5])
print("resets_at:", resets)
if write and seen == len(exps) and not bad:
    life["resets_at"] = resets
    json.dump(j, open(J, "w", encoding="utf-8"), indent=1)
    print("written")
