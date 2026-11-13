"""ARC-AGI-3 live client + local mock — the wall meets the active tests.

Protocol (docs.arcprize.org):
  GET  {base}/api/games                          -> [{game_id, title}, ...]
  POST {base}/api/scorecard/open                 -> {card_id}
  POST {base}/api/cmd/RESET   {game_id, card_id} -> frame json (guid born here)
  POST {base}/api/cmd/ACTION1..5 {game_id, guid} -> frame json
  POST {base}/api/cmd/ACTION6 {game_id, guid, x, y}   (x,y in 0..63)
  POST {base}/api/cmd/ACTION7 {game_id, guid}    (undo — we do not use it: no-undo law)
  POST {base}/api/scorecard/close {card_id}
Frame json: {frame: [ [ [row0...], ... 64x64 ... ] ] (1..N layers), state, score, guid}
  state in {NOT_PLAYED, NOT_FINISHED, IN_PROGRESS, WIN, GAME_OVER}; colors 0..15.
Auth: X-API-Key header. Key from env ARC_API_KEY or --key.

Usage:
  python arc3_client.py --mock                 # run agent loop against the local mock
  ARC_API_KEY=... python arc3_client.py --list # list live games
  ARC_API_KEY=... python arc3_client.py --game ls20   # play a live game (prefix ok)
"""
import json, os, sys, time, urllib.request
import http.cookiejar
import numpy as np

BASE = os.environ.get("ARC3_BASE", "https://three.arcprize.org")
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

# ---------------- transport ----------------
def api(path, key, body=None, method=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data,
        method=method or ("POST" if body is not None else "GET"),
        headers={"X-API-Key": key, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with _opener.open(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        raise RuntimeError(f"{e.code} on {path}: {detail}") from None

# ---------------- local mock (same wire format) ----------------
class MockGame:
    """A tiny probe-first world in the ARC-3 wire format: 64x64, colors 0..15.
    Agent (color 3) must touch the key (color 4) then reach the door (color 5).
    Walls color 8. ACTION1..4 = up/down/left/right. ACTION6 = click (teleport ping: reveals map)."""
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        g = np.zeros((64, 64), int)
        g[0, :] = g[-1, :] = g[:, 0] = g[:, -1] = 8
        for _ in range(30):
            x, y = rng.integers(2, 62, 2)
            g[y, x:min(x+rng.integers(3, 9), 62)] = 8
        self.g = g
        free = np.argwhere(g == 0)
        self.pos = tuple(free[rng.integers(len(free))])
        self.key = tuple(free[rng.integers(len(free))])
        self.door = tuple(free[rng.integers(len(free))])
        self.has_key = False
        self.score, self.state = 0, "NOT_FINISHED"
        self.guid = "mock-guid-%04d" % seed
    def frame(self):
        f = self.g.copy()
        f[self.key] = 0 if self.has_key else 4
        f[self.door] = 5
        f[self.pos] = 3
        return {"frame": [f.tolist()], "state": self.state,
                "score": self.score, "guid": self.guid}
    def act(self, name, x=None, y=None):
        d = {"ACTION1": (-1, 0), "ACTION2": (1, 0), "ACTION3": (0, -1), "ACTION4": (0, 1)}
        if name in d:
            ny, nx = self.pos[0] + d[name][0], self.pos[1] + d[name][1]
            if self.g[ny, nx] != 8:
                self.pos = (ny, nx)
        if self.pos == self.key and not self.has_key:
            self.has_key = True; self.score += 1
        if self.pos == self.door and self.has_key:
            self.state = "WIN"; self.score += 10
        return self.frame()

# ---------------- the agent skeleton (probe-first, no-undo, evidence store) ----------------
def frame_np(fr):
    return np.array(fr["frame"][-1], int)      # last layer = current screen

def play(send, max_steps=400, log=print):
    """send(action, x=None, y=None) -> frame json. The loop follows the measured laws:
       probe-first (learn what moves do), evidence store of before/after diffs (operator
       induction), never ACTION7 (no undo — fix forward), RESET only to test determinism."""
    fr = send("RESET")
    prev = frame_np(fr)
    evidence = []                              # (action, n_changed, bbox) — the induction feed
    moves = ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5"]
    # probe phase: try each simple action twice, record what changes
    for a in moves * 2:
        fr = send(a)
        cur = frame_np(fr)
        diff = np.argwhere(cur != prev)
        evidence.append((a, len(diff), diff[:4].tolist()))
        prev = cur
        if fr["state"] in ("WIN", "GAME_OVER"):
            break
    live = sorted({a for a, n, _ in evidence if n > 0})
    log(f"  probe: live actions = {live}  (affordance set = the router)")
    # play phase: greedy toward novel cells with live actions (placeholder for the full
    # psi/phi runtime); the point of v0 is wire-format + evidence, not cleverness
    rng = np.random.default_rng(0)
    seen = set()
    snaps = [prev.copy()]
    scores = [fr.get("score", 0)]
    steps = len(evidence)
    while fr["state"] not in ("WIN", "GAME_OVER") and steps < max_steps:
        a = live[rng.integers(len(live))] if live else "ACTION6"
        fr = send(a) if a != "ACTION6" else send(a, x=int(rng.integers(64)), y=int(rng.integers(64)))
        cur = frame_np(fr)
        ch = np.argwhere(cur != prev)
        if len(ch): evidence.append((a, len(ch), ch[:4].tolist()))
        prev = cur; steps += 1
        seen.add(cur.tobytes())
        scores.append(fr.get("score", 0))
        if steps % 25 == 0: snaps.append(cur.copy())
    snaps.append(prev.copy())
    return fr, steps, evidence, len(seen), snaps, scores

# ---------------- entry ----------------
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--mock" in args:
        wins = 0
        for seed in range(10):
            game = MockGame(seed)
            send = lambda a, x=None, y=None: game.frame() if a == "RESET" else game.act(a, x, y)
            fr, steps, ev, uniq, snaps, scores = play(send, log=lambda s: None)
            wins += fr["state"] == "WIN"
            print(f"mock seed {seed}: state={fr['state']:12s} score={fr['score']:3d} steps={steps} unique-frames={uniq}")
        print(f"\nmock: {wins}/10 wins with the v0 random-walk policy (the runtime slots in next)")
        sys.exit(0)
    key = os.environ.get("ARC_API_KEY", "")
    for i, a in enumerate(args):
        if a == "--key": key = args[i+1]
    if not key:
        print("need ARC_API_KEY (register at arcprize.org/platform -> profile -> API Keys)"); sys.exit(1)
    games = api("/api/games", key)
    print("live games:", [(g["game_id"], g.get("title")) for g in games])
    if "--list" in args: sys.exit(0)
    want = None
    for i, a in enumerate(args):
        if a == "--game": want = args[i+1]
    gid = next((g["game_id"] for g in games if g["game_id"].startswith(want or "")), games[0]["game_id"])
    card = api("/api/scorecard/open", key, {})
    card_id = card.get("card_id") or card.get("cardId")
    print("scorecard:", card_id, " game:", gid)
    guid = {}
    def send(a, x=None, y=None):
        if a == "RESET":
            fr = api("/api/cmd/RESET", key, {"game_id": gid, "card_id": card_id,
                                             "guid": guid.get("v")})
        else:
            body = {"game_id": gid, "card_id": card_id, "guid": guid["v"]}
            if x is not None: body.update(x=x, y=y)
            fr = api(f"/api/cmd/{a}", key, body)
        guid["v"] = fr["guid"]
        return fr
    try:
        fr, steps, ev, uniq, snaps, scores = play(send)
        print(f"live: state={fr['state']} score={fr.get('score')} steps={steps} unique-frames={uniq} max-score={max(scores)}")
        np.savez(f"arc3_run_{want or 'first'}.npz", snaps=np.array(snaps),
                 scores=np.array(scores))
        print(f"saved arc3_run_{want or 'first'}.npz ({len(snaps)} snapshots)")
    finally:
        out = api("/api/scorecard/close", key, {"card_id": card_id})
        print("scorecard closed:", json.dumps(out)[:400])
