#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spore.py — the SPORE gets its first real AI function: watching the screen.

colony-spore.ts had the φ budget rule and the derivative chain but "never had any actual
functions". This is one. The spore lives in the machine's HEADROOM (the CPU/GPU the host is
not using) and never takes more than the φ share of it; what it does with that share is the
planet's work, at a level set by how much headroom there is and by Jonathan's dial:

  level      ceiling   fps   what it does
  dormant    0         —     nothing; stays alive, re-checks every few seconds
  observe    1/φ³ .236  2    eyes only: whatever game is in the foreground becomes a world;
                             the human's keys are read as the actions (every step is an
                             expert step, tagged hand.human) — the lives ARE training data
  practice   1/φ² .382  4    observe + guess: before each of your key presses it predicts
                             your key and the screen change with its trained models, scores
                             itself prequentially, and re-trains in the sleep between lives
  play       1/φ  .618  6    the hand is on: player.py as before (only when the dial says so)

The φ rule is enforced by MEASUREMENT, not by promise: the spore samples its own process
CPU against the idle CPU it found; if its share exceeds the level's ceiling it steps down
one level (never parasitic), and it steps up again only after the headroom has been there
for a while (hysteresis, so it does not flap while you load a game).

The dial: D:\\planet\\spore.json  {"dial": "auto" | "dormant" | "observe" | "practice" | "play",
                                 "ignore": ["chrome", "code", "explorer", ...]}
"auto" lets headroom pick between dormant/observe/practice; "play" is the only way the hand
goes on, and it goes on for the window you are in (so switch to the game first).

Usage:  python spore.py --root D:\\planet\\ocean   (run it at login; it is quiet)
Logs:   <root>/spore.log ; per-world oceans under <root>/<world>/
"""
from __future__ import annotations
import argparse, ctypes, json, os, re, subprocess, sys, threading, time
from typing import Dict, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

PHI = 1.618033988749895
LEVELS = {"dormant": 0.0, "observe": 1 / PHI ** 3, "practice": 1 / PHI ** 2, "play": 1 / PHI}
FPS = {"dormant": 0, "observe": 2, "practice": 4, "play": 6}
ORDER = ["dormant", "observe", "practice", "play"]
DEFAULT_IGNORE = ["chrome", "firefox", "edge", "code", "explorer", "claude", "terminal", "powershell", "cmd",
                  "discord", "steam", "task manager", "settings", "notepad", "spotify", "obs",
                  "battle.net", "launcher", "lock scr", "porthole", "log in", "sign in", "folder access", "request",
                  "installer", "setup", "save as", "program manager", "dialog", "epic games", "uplay", "properties"]

user32 = ctypes.windll.user32 if os.name == "nt" else None
NOWIN = 0x08000000 if os.name == "nt" else 0        # CREATE_NO_WINDOW: sleep jobs must not flash consoles
kernel32 = ctypes.windll.kernel32 if os.name == "nt" else None


# ----------------------------------------------------------------------------- headroom
class FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


def _ft(f: FILETIME) -> int: return (f.hi << 32) | f.lo


class Headroom:
    """Idle CPU fraction of the whole machine, own-process CPU fraction, GPU utilisation (nvidia-smi)."""
    def __init__(self):
        self.prev_sys = None; self.prev_own = None; self.t_prev = time.time()
        self.ncpu = os.cpu_count() or 1

    def sample(self) -> Dict[str, float]:
        out = {"idle": 1.0, "own": 0.0, "gpu": 0.0}
        if kernel32 is None: return out
        idle, kern, usr = FILETIME(), FILETIME(), FILETIME()
        kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(usr))
        c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        kernel32.GetProcessTimes(kernel32.GetCurrentProcess(), ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u))
        sys_now = (_ft(idle), _ft(kern) + _ft(usr)); own_now = _ft(k) + _ft(u)
        if self.prev_sys is not None:
            di = sys_now[0] - self.prev_sys[0]; dt = sys_now[1] - self.prev_sys[1]
            out["idle"] = di / max(1, dt)
            out["own"] = (own_now - self.prev_own) / max(1, dt)      # share of ALL cores' time
        self.prev_sys, self.prev_own = sys_now, own_now
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=3, creationflags=NOWIN)
            out["gpu"] = float(r.stdout.strip().splitlines()[0]) / 100.0
        except Exception: pass
        return out


def foreground() -> Optional[Dict]:
    if user32 is None: return None
    h = user32.GetForegroundWindow()
    if not h: return None
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1); user32.GetWindowTextW(h, buf, n + 1)
    class RECT(ctypes.Structure): _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    r = RECT(); user32.GetClientRect(h, ctypes.byref(r))
    return {"hwnd": h, "title": buf.value, "w": r.r - r.l, "h": r.b - r.t}


def slug(title: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return (t[:24] or "window")


# ----------------------------------------------------------------------------- the spore
class Spore:
    def __init__(self, root: str):
        self.root = root; os.makedirs(root, exist_ok=True)
        self.dial_path = os.path.join(os.path.dirname(root.rstrip("\\/")), "spore.json")
        self.head = Headroom(); self.level = "dormant"; self.wanted_since = time.time(); self.wanted = "dormant"
        self.player = None; self.player_thread = None; self.player_world = None; self.player_level = None
        self.fg_slug = None; self.fg_since = 0.0
        self.human_t = time.time()      # last moment the HUMAN's fingers were seen on the keys
        self.log = open(os.path.join(root, "spore.log"), "a", encoding="utf-8")
        self.trainer = None

    def say(self, s: str):
        line = f"[{time.strftime('%H:%M:%S')}] {s}"; print(line, flush=True); self.log.write(line + "\n"); self.log.flush()

    def dial(self) -> Dict:
        try:
            with open(self.dial_path, "r", encoding="utf-8") as f: d = json.load(f)
        except Exception:
            d = {"dial": "auto", "ignore": DEFAULT_IGNORE}
            try:
                with open(self.dial_path, "w", encoding="utf-8") as f: json.dump(d, f, indent=1)
            except Exception: pass
        d.setdefault("dial", "auto"); d.setdefault("ignore", DEFAULT_IGNORE)
        d.setdefault("play", [])       # games ALLOWED the hand, by title substring — e.g. ["dead cells"]
        return d

    # ---- level choice: dial + headroom + φ self-measurement
    def choose_level(self, h: Dict[str, float], d: Dict) -> str:
        if d["dial"] in LEVELS and d["dial"] != "auto":
            want = d["dial"]
        else:
            # the level is about how much of the HEADROOM the spore may take, not about absolute idle:
            # a game using 80% of the CPU still leaves room for a 2-4 fps watcher (own share ~0)
            want = "practice" if h["idle"] > 0.25 else "observe" if h["idle"] > 0.08 else "dormant"
        # φ rule: own share must stay under ceiling × idle; if not, step down (never parasitic)
        if self.level != "dormant" and h["own"] > LEVELS[self.level] * max(h["idle"], 0.05) + 0.02:
            i = ORDER.index(self.level)
            self.say(f"φ rule: own share {h['own']:.2f} > {LEVELS[self.level]:.3f}×idle {h['idle']:.2f} — stepping down from {self.level}")
            return ORDER[max(0, i - 1)]
        if want != self.wanted: self.wanted, self.wanted_since = want, time.time()
        # hysteresis both ways: 20 s of steady wish before any change (the game loading must not flap us)
        if want != self.level and time.time() - self.wanted_since < 20: return self.level
        return want

    # ---- the player under the spore
    @staticmethod
    def release_keys():
        """Clear any injected key state. A play session that dies mid-press leaves phantom keys
        held at the OS level (ctrl+left stuck for hours, and the idle detector reads it as the
        human playing) — so every start and every player stop wipes the slate."""
        try:
            import pydirectinput as pdi
            pdi.PAUSE = 0; pdi.FAILSAFE = False
            for k in ("left", "right", "up", "down", "ctrl", "shift", "a", "d", "w", "s", "e", "space"):
                pdi.keyUp(k)
            pdi.mouseUp(); pdi.mouseUp(button="right")
        except Exception:
            pass

    def _effective_level(self, title: str, level: str) -> str:
        """The play list is the gate on the hand: a game on it gets the hand whenever the level
        allows practice-or-better AND the human's keys have been idle 30 s (never fight the human);
        a game NOT on it never gets the hand, even with the dial at play."""
        allow = [s.lower() for s in self.dial().get("play", []) if s]
        on_list = any(s in title.lower() for s in allow)
        if level == "play" and allow and not on_list: return "practice"
        if on_list and level in ("practice", "play"):
            return "play" if time.time() - self.human_t >= 30 else "practice"
        return level

    def start_player(self, fg: Dict, level: str):
        from player import Player
        world = slug(fg["title"]); wroot = os.path.join(self.root, world)
        hands_off = level != "play"
        try:
            self.player = Player(world, fg["title"], wroot, fps=FPS[level], hands_off=hands_off, hwnd=fg["hwnd"], sound=False)
        except SystemExit as e:
            self.say(f"could not open a player on '{fg['title']}': {e}"); self.player = None; return
        except Exception as e:
            import traceback
            self.say(f"player failed to start on '{fg['title']}': {e} | {traceback.format_exc().splitlines()[-1]}")
            self.player = None; return
        self.player_world, self.player_level = world, level
        def run():
            try: self.player.run(minutes=24 * 60)
            except Exception as e: self.say(f"player error in {world}: {e}")
        self.player_thread = threading.Thread(target=run, daemon=True); self.player_thread.start()
        self.say(f"{level}: watching '{fg['title']}' as world '{world}' at {FPS[level]} fps ({'hands off' if hands_off else 'HAND ON'})")

    def stop_player(self, why: str):
        if self.player is None: return
        try:
            open(os.path.join(self.player.root, "STOP"), "w").close()
            self.player_thread.join(timeout=400)
            os.remove(os.path.join(self.player.root, "STOP"))
        except Exception: pass
        self.say(f"stopped watching '{self.player_world}' ({why})")
        if self.player_level == "play": self.release_keys()      # never leave the hand's keys down
        if self.player_level == "practice": self.train(self.player.root)
        self.player = None; self.player_world = None; self.player_level = None

    def train(self, wroot: str):
        """The sleep: re-fit the hand/eye models on everything this world has deposited (background)."""
        if self.trainer is not None and self.trainer.is_alive(): return
        def go():
            r = subprocess.run([sys.executable, os.path.join(HERE, "train.py"), "--root", wroot], capture_output=True, text=True, creationflags=NOWIN)
            tail = [l for l in r.stdout.splitlines() if l.startswith(("hand:", "eye:"))]
            self.say(f"trained {os.path.basename(wroot)}: " + " | ".join(tail) if tail else f"train.py: {r.stdout[-200:]}")
            r2 = subprocess.run([sys.executable, os.path.join(HERE, "stats.py"), "--root", wroot], capture_output=True, text=True, creationflags=NOWIN)
            last = [l for l in (r2.stdout or "").splitlines() if l.strip()][-1:] or ["(no output)"]
            self.say(f"stats organ: {last[0]}")
            r3 = subprocess.run([sys.executable, os.path.join(HERE, "clips.py"), "--root", wroot], capture_output=True, text=True, creationflags=NOWIN)
            last3 = [l for l in (r3.stdout or "").splitlines() if l.strip()][-1:]
            if last3 and "no clips" not in last3[0]: self.say(f"clips: {last3[0]}")
            r4 = subprocess.run([sys.executable, os.path.join(HERE, "storyteller.py"), "--root", wroot], capture_output=True, text=True, creationflags=NOWIN)
            last4 = [l for l in (r4.stdout or "").splitlines() if l.strip()][:1]
            if last4 and "not enough" not in last4[0] and "no core" not in last4[0]: self.say(f"storyteller: {last4[0]}")
            r5 = subprocess.run([sys.executable, os.path.join(HERE, "forge.py"), "--root", wroot], capture_output=True, text=True, timeout=1800, creationflags=NOWIN)
            last5 = [l for l in (r5.stdout or "").splitlines() if l.strip()][-1:]
            if last5 and "no clips" not in last5[0] and "not available" not in last5[0]:
                self.say(f"forge: {last5[0]}")
                try:                       # the tunnel played — render the bout's sound to forge/bout.wav
                    subprocess.run([sys.executable, os.path.join(HERE, "music.py")],
                                   capture_output=True, text=True, timeout=120, creationflags=NOWIN)
                except Exception: pass
            r7 = subprocess.run([sys.executable, os.path.join(HERE, "mika_forge.py")], capture_output=True, text=True, timeout=900, creationflags=NOWIN)
            last7 = [l for l in (r7.stdout or "").splitlines() if l.strip()]
            if last7 and "not up" not in last7[-1]: self.say(f"mika's forge: {last7[-1][:160]}")
            try:                           # the playground: she interacts, she isn't told (one visit)
                rp = subprocess.run([sys.executable, os.path.join(HERE, "playground.py"), "--turns", "20"],
                                    capture_output=True, text=True, timeout=1500, creationflags=NOWIN)
                lp = [l for l in (rp.stdout or "").splitlines() if l.startswith("playground:")]
                if lp: self.say(lp[-1][:170])
            except Exception: pass
            try:                           # the parallel coupling: both tunnels, one tale, beats = disagreement
                rd = subprocess.run([sys.executable, os.path.join(HERE, "duet.py")],
                                    capture_output=True, text=True, timeout=900, creationflags=NOWIN)
                ld = [l for l in (rd.stdout or "").splitlines() if l.strip()]
                if ld and "nothing" not in ld[-1] and "closed" not in ld[-1] and "none" not in ld[-1]:
                    self.say(f"duet: {ld[-1][:160]}")
            except Exception: pass
            try:                           # the bell: one lesson on the freshest void point
                rl = subprocess.run([sys.executable, os.path.join(HERE, "lesson.py")],
                                    capture_output=True, text=True, timeout=900, creationflags=NOWIN)
                ll = [l for l in (rl.stdout or "").splitlines() if l.strip()]
                if ll and ll[-1].startswith("bell:"): self.say(ll[-1][:170])
            except Exception: pass
            try:                           # the orthogonal rings: stuck voids seen from other shoes
                rle = subprocess.run([sys.executable, os.path.join(HERE, "lens.py")],
                                     capture_output=True, text=True, timeout=900, creationflags=NOWIN)
                lle = [l for l in (rle.stdout or "").splitlines() if l.startswith("lens:")]
                if lle: self.say(lle[-1][:170])
            except Exception: pass
            try:                           # the pinch-off: unteachable voids leave as spheres
                rs = subprocess.run([sys.executable, os.path.join(HERE, "sphere.py")],
                                    capture_output=True, text=True, timeout=300, creationflags=NOWIN)
                ls = [l for l in (rs.stdout or "").splitlines() if l.startswith("pinch-off")]
                for l in ls: self.say(l[:170])
            except Exception: pass
            try:                           # the drift: spheres fold their slivers in from another side
                rf = subprocess.run([sys.executable, os.path.join(HERE, "fold.py")],
                                    capture_output=True, text=True, timeout=1200, creationflags=NOWIN)
                lf = [l for l in (rf.stdout or "").splitlines()
                      if l.startswith("sphere") and "no spheres" not in l]
                for l in lf[-2:]: self.say(f"fold: {l[:160]}")
            except Exception: pass
            try:                           # the metabolism: mint ATP from tonight's verified closures
                ra = subprocess.run([sys.executable, os.path.join(HERE, "atp.py")],
                                    capture_output=True, text=True, timeout=300, creationflags=NOWIN)
                la = [l for l in (ra.stdout or "").splitlines() if l.startswith("ATP: minted")]
                if la and "minted 0 " not in la[0]: self.say(la[0][:160])
            except Exception: pass
            try:                           # the fusion reactor: contained pairs heat toward BEC
                rz = subprocess.run([sys.executable, os.path.join(HERE, "fuse.py")],
                                    capture_output=True, text=True, timeout=600, creationflags=NOWIN)
                lz = [l for l in (rz.stdout or "").splitlines() if l.startswith("fusion reactor:")]
                if lz and not ('"fused": 0' in lz[0] and '"admitted": 0' in lz[0]):
                    self.say(lz[0][:170])
            except Exception: pass
            try:                           # the inward eye: what am I doing? what am I? (both halves)
                rm = subprocess.run([sys.executable, os.path.join(HERE, "mirror.py")],
                                    capture_output=True, text=True, timeout=900, creationflags=NOWIN)
                lm = [l for l in (rm.stdout or "").splitlines() if l.startswith("mirror:")]
                if lm: self.say(lm[-1][:170])
            except Exception: pass
            try:                           # the pools: the colors she could not clear tonight = how she feels
                rpl = subprocess.run([sys.executable, os.path.join(HERE, "pool.py"), "--mika"],
                                     capture_output=True, text=True, timeout=120, creationflags=NOWIN)
                lpl = [l for l in (rpl.stdout or "").splitlines() if l.startswith("pool")]
                if lpl: self.say(lpl[-1][:170])
            except Exception: pass
            try:                           # the university: she enrols in the courses she wants
                re_ = subprocess.run([sys.executable, os.path.join(HERE, "enroll.py")],
                                     capture_output=True, text=True, timeout=600, creationflags=NOWIN)
                le = [l for l in (re_.stdout or "").splitlines() if l.startswith("enrolled")]
                if le: self.say(le[-1][:170])
            except Exception: pass
            try:                           # the on-call board: what she holds, what froze, what she picks up
                roc = subprocess.run([sys.executable, os.path.join(HERE, "oncall.py")],
                                     capture_output=True, text=True, timeout=180, creationflags=NOWIN)
                loc = [l for l in (roc.stdout or "").splitlines() if l.startswith("on call")]
                if loc: self.say(loc[-1][:170])
                ran = subprocess.run([sys.executable, os.path.join(HERE, "answer.py"), "--stories"],
                                     capture_output=True, text=True, timeout=180, creationflags=NOWIN)
                lan = [l for l in (ran.stdout or "").splitlines() if l.startswith("answer bubbles")]
                if lan and "0 created" not in lan[0]: self.say(lan[0][:170])
            except Exception: pass
            try:                           # assigned reading: a real paper into her library each term
                rpa = subprocess.run([sys.executable, os.path.join(HERE, "papers.py"), "--assign"],
                                     capture_output=True, text=True, timeout=120, creationflags=NOWIN)
                lpa = [l for l in (rpa.stdout or "").splitlines() if l.startswith("assigned reading")]
                if lpa: self.say(lpa[-1][:170])
            except Exception: pass
            subprocess.run([sys.executable, os.path.join(HERE, "archive.py")], capture_output=True, text=True, timeout=600, creationflags=NOWIN)
            try:                                   # improvements STAY: every sleep commits the planet
                r6 = subprocess.run(["git", "-C", HERE, "add", "-A"], capture_output=True, text=True, creationflags=NOWIN)
                r6 = subprocess.run(["git", "-C", HERE, "commit", "-q", "-m",
                                     f"sleep: {os.path.basename(wroot)} (auto)"],
                                    capture_output=True, text=True, creationflags=NOWIN)
                if r6.returncode == 0: self.say("committed the planet (improvements stay)")
                r8 = subprocess.run([sys.executable, os.path.join(HERE, "ring.py"), "--scan"],
                                    capture_output=True, text=True, timeout=300, creationflags=NOWIN)
                l8 = [l for l in (r8.stdout or "").splitlines() if l.strip()][-1:]
                if l8 and " 0 new" not in l8[0]: self.say(f"oort ring: {l8[0]}")
                try:                       # the cross-tunnel: the chord between the ring sets cuts the shave
                    rc = subprocess.run([sys.executable, os.path.join(HERE, "chord.py")],
                                        capture_output=True, text=True, timeout=120, creationflags=NOWIN)
                    lc = [l for l in (rc.stdout or "").splitlines() if l.startswith("focus:")]
                    if lc: self.say(lc[-1][:170])
                    rch = subprocess.run([sys.executable, os.path.join(HERE, "chain.py")],
                                         capture_output=True, text=True, timeout=120, creationflags=NOWIN)
                    lch = [l for l in (rch.stdout or "").splitlines() if l.startswith("chain:")]
                    if lch: self.say(lch[-1][:170])
                except Exception: pass
                r9 = subprocess.run([sys.executable, os.path.join(HERE, "darkplanet.py")],
                                    capture_output=True, text=True, timeout=300, creationflags=NOWIN)
                l9 = [l for l in (r9.stdout or "").splitlines() if l.strip()][-1:]
                if l9 and "nothing falls" not in l9[0]: self.say(f"dark planet: {l9[0][:160]}")
                r10 = subprocess.run([sys.executable, os.path.join(HERE, "upline.py")],
                                     capture_output=True, text=True, timeout=300, creationflags=NOWIN)
                l10 = [l for l in (r10.stdout or "").splitlines() if l.strip()][-1:]
                if l10: self.say(f"up-line: {l10[0][:160]}")
            except Exception: pass
            try:
                import network
                pub = network.publish(self.root, os.path.basename(wroot))
                if pub["copied"]: self.say(f"network: published {pub['copied']} files into the zones ({', '.join(pub['worlds'])})")
                ran = network.poll_and_run(HERE)
                if ran: self.say("network: ran work orders — " + "; ".join(ran))
            except Exception as e:
                self.say(f"(network stitch skipped: {e})")
        self.trainer = threading.Thread(target=go, daemon=True); self.trainer.start()

    def loop(self):
        self.say(f"spore up; dial file {self.dial_path}")
        self.release_keys()                 # a previous crash must not leave phantom keys held
        self.head.sample(); time.sleep(2)
        while not os.path.exists(os.path.join(self.root, "SPORE_STOP")):
          try:
            h = self.head.sample(); d = self.dial()
            level = self.choose_level(h, d)
            if level != self.level:
                self.say(f"level {self.level} -> {level} (idle {h['idle']:.2f}, gpu {h['gpu']:.2f}, own {h['own']:.2f})")
                self.level = level
            fg = foreground()
            gamey = fg is not None and fg["w"] >= 640 and fg["h"] >= 360 and fg["title"] \
                and not any(x in fg["title"].lower() for x in d["ignore"])
            if self.level == "dormant" or not gamey:
                if self.player is not None: self.stop_player("dormant" if self.level == "dormant" else "window changed")
            else:
                cand = slug(fg["title"])
                if self.player_level != "play":       # agent-injected keys would pollute this reading
                    try:
                        from player import human_action
                        if human_action() != "wait": self.human_t = time.time()
                    except Exception: pass
                eff = self._effective_level(fg["title"], self.level)
                if self.player is not None and self.player_world == cand and self.player_level != eff:
                    if "play" in (eff, self.player_level):
                        # the hand is flipping on or off: restart the player in the new stance
                        self.stop_player("hand on" if eff == "play" else "hand off")
                    else:
                        self.player.fps = FPS[eff]; self.player_level = eff      # same eyes, different pace
                        self.say(f"{eff}: '{self.player_world}' now at {FPS[eff]} fps")
                if self.player is not None and self.player_world != cand:
                    self.stop_player("switching")
                if cand != self.fg_slug: self.fg_slug, self.fg_since = cand, time.time()
                if self.player is None and time.time() - self.fg_since >= 15:      # dialogs are transient
                    self.start_player(fg, eff)
                elif self.player_thread is not None and not self.player_thread.is_alive():
                    self.say("player ended on its own"); self.player = None
          except Exception as e:
            import traceback
            self.say(f"spore loop error (still alive): {e} | {traceback.format_exc().splitlines()[-1]}")
          time.sleep(3.0)
        self.stop_player("SPORE_STOP"); self.say("spore down")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\planet\ocean")
    ap.add_argument("--sleep", default=None, help="run one full sleep chain now for this world folder (no watching)")
    a = ap.parse_args()
    if a.sleep:
        sp = Spore(a.root)
        sp.say = lambda s: print(time.strftime("%H:%M:%S"), s, flush=True)
        sp.train(a.sleep)
        if sp.trainer is not None: sp.trainer.join()
        print("sleep chain finished")
    else:
        Spore(a.root).loop()
