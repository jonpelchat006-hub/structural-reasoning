#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
player.py — the PERSON AT THE DESK, for a real game window (Windows).

Rules (Jonathan's): screen only, like a person — no game memory, no code; a coarse
box of pixels, not exact pixels (targets are picked at random INSIDE a box); a fixed
number of looks per second, so anything that happens between two looks is missed;
and the hand only ever presses keys.

Loop (the fast loop and the middle loop, on the PC; the slow loop is outside):
  look  : grab the game window, downscale to a small grid, quantize to a few levels
  see   : SurpriseMonitor (camera / mover / counter) predicts, measures surprise,
          learns; charge accumulates per region
  gaze  : the hottest region (surprise x pressure) — surprise steals the gaze
  hand  : PROBE first (each key a few times), then move toward a random target inside
          the gaze box using the mover's learned displacements; blocked → escalate
          (jump, action key, other way); reserve: a little randomness always
  narrate: one line per event to narration.txt (grounded in atoms — it can only say
          what a species detected)
  death : luminance collapse (fade to black) then recovery = death → Coach.at_death,
          record the life, reseed, next life
  files : lives/<world>_<n>.npz (frames, actions, events), core_<world>.json (coach),
          lightning.json (outbox — charge for the clouds), rain.json (inbox — pressure
          map + untrusted hypotheses), STOP (create to stop)

Run:  python player.py --world limbo --title LIMBO --fps 8 --minutes 20
"""
from __future__ import annotations
import argparse, ctypes, json, os, random, sys, time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from species import SurpriseMonitor
from coach import Coach, _save, _load
from wall import Wall, Atlas
from rotation import RotationEye
from translation import TranslationEye
from border import MailBand, BAND_ROWS
import geo

# ------------------------------------------------------------------ window (Windows only)
user32 = ctypes.windll.user32 if os.name == "nt" else None


def find_window(title_part: str) -> Optional[int]:
    if user32 is None: return None
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1); user32.GetWindowTextW(hwnd, buf, n + 1)
            if title_part.lower() in buf.value.lower() and user32.IsWindowVisible(hwnd): found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def client_rect(hwnd) -> Tuple[int, int, int, int]:
    class RECT(ctypes.Structure): _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    class POINT(ctypes.Structure): _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    r = RECT(); user32.GetClientRect(hwnd, ctypes.byref(r))
    p = POINT(0, 0); user32.ClientToScreen(hwnd, ctypes.byref(p))
    return p.x, p.y, r.r - r.l, r.b - r.t


def is_foreground(hwnd) -> bool:
    return user32 is not None and user32.GetForegroundWindow() == hwnd


VK = {"left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "ctrl": 0x11, "F8": 0x77, "F9": 0x78, "F10": 0x79,
      "A": 0x41, "D": 0x44, "W": 0x57, "S": 0x53, "space": 0x20, "shift": 0x10, "E": 0x45, "lmb": 0x01, "rmb": 0x02}


def key_down(name: str) -> bool:
    return user32 is not None and bool(user32.GetAsyncKeyState(VK[name]) & 0x8000)


_last_cursor = [None]
_raw = [None]
def mouse_delta() -> Tuple[int, int]:
    """Physical mouse motion since the last look. Raw Input first (cursor-lock games hide the
    mouse from GetCursorPos — the Warframe lesson); cursor delta as the fallback."""
    if user32 is None: return (0, 0)
    if _raw[0] is None:
        try:
            from rawmouse import RawMouse
            _raw[0] = RawMouse()
        except Exception: _raw[0] = False
    if _raw[0] and getattr(_raw[0], "ok", False):
        return _raw[0].delta()
    class POINT(ctypes.Structure): _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    p = POINT(); user32.GetCursorPos(ctypes.byref(p))
    prev = _last_cursor[0]; _last_cursor[0] = (p.x, p.y)
    return (0, 0) if prev is None else (p.x - prev[0], p.y - prev[1])


CHANNEL_KEYS = {"l": ["left", "A"], "r": ["right", "D"], "u": ["up", "W", "space"],
                "c": ["ctrl", "shift", "E", "lmb", "rmb"]}


def human_action() -> str:
    """Read the keyboard as an action name (same vocabulary as the hand, so laws transfer expert→novice)."""
    # arrows+ctrl (Limbo) and WASD/space/shift/E/mouse (most other games) read into ONE vocabulary
    l = key_down("left") or key_down("A"); r = key_down("right") or key_down("D")
    u = key_down("up") or key_down("W") or key_down("space")
    c = key_down("ctrl") or key_down("shift") or key_down("E") or key_down("lmb") or key_down("rmb")
    if c and u and l: return "jumpgrableft"       # the chords: read the whole hand shape,
    if c and u and r: return "jumpgrabright"      # not just its loudest finger
    if c and u: return "jumpgrab"
    if c and l: return "grableft"
    if c and r: return "grabright"
    if c: return "grab"
    if u and l: return "jumpleft"
    if u and r: return "jumpright"
    if u: return "jump"
    if l: return "left"
    if r: return "right"
    return "wait"


def human_keys() -> Dict[str, str]:
    """WHICH physical key carries each channel right now — the expert's own fingers, recorded so a
    playing hand can later press the same keys this game actually listens to (dead cells is space
    and the mouse, limbo is arrows; the novice must inherit the expert's keys, not ours)."""
    out = {}
    for ch, keys in CHANNEL_KEYS.items():
        for k in keys:
            if key_down(k): out[ch] = k; break
    return out


# ------------------------------------------------------------------ the eye
class Eye:
    """Grab the window, downscale by block mean to (H, W), quantize luminance to `levels`."""
    EDGES = [16, 22, 30, 40, 54, 74, 104]          # 8 levels (first edge above the film grain)
    def __init__(self, hwnd, H=96, W=160, levels=8, rect_fn=None):
        import mss
        self.sct = mss.mss(); self.hwnd = hwnd; self.H, self.W, self.levels = H, W, levels
        self.rect_fn = rect_fn                      # porthole mode: () -> (x, y, w, h) on screen
        self.last_raw = None
        self.hist = np.ones(256)          # running luminance histogram: the eye ADAPTS (dark games, bright games)
        self.ema = None                   # temporal smoothing: film grain is random per frame, the scene is not
        self.raw_shape = None
        try:                              # the ROUND screen (fovea.py): only if D:\planet\fovea.json exists
            from fovea import Fovea
            self.fovea = Fovea.load()
        except Exception:
            self.fovea = None

    EDGE_EDGES = [1.2, 2.5, 5.0]                        # 4 edge levels; symbol = lum + 8 * edge  (0..31)
    def look(self) -> Optional[np.ndarray]:
        try:
            from scipy import ndimage
            x, y, w, h = self.rect_fn() if self.rect_fn is not None else client_rect(self.hwnd)
            if w < 64 or h < 64: return None
            shot = self.sct.grab({"left": x, "top": y, "width": w, "height": h}); self.last_raw = shot
            img = np.asarray(shot)[:, :, :3]
            self.raw_shape = img.shape
            lum = (0.114 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.299 * img[:, :, 2])   # BGRA
            # stage 1: a mid-resolution retina (5x the grid) — block mean kills the film grain
            H5, W5 = self.H * 5, self.W * 5
            hh, ww = (h // H5) * H5, (w // W5) * W5
            mid = lum[:hh, :ww].reshape(H5, hh // H5, W5, ww // W5).mean(axis=(1, 3))
            mid = (mid / 255.0) ** 0.6 * 255.0                                   # lift the darks
            # stage 2: the two lenses — luminance (what) and silhouette edge (outline: the boy against fog)
            small = mid.reshape(self.H, 5, self.W, 5).mean(axis=(1, 3))
            sm = ndimage.gaussian_filter(mid, 1.5)
            mag = np.hypot(ndimage.sobel(sm, axis=0), ndimage.sobel(sm, axis=1)) / 8.0
            edge = mag.reshape(self.H, 5, self.W, 5).mean(axis=(1, 3))
            self.ema = small if self.ema is None else 0.3 * self.ema + 0.7 * small
            self.ema_e = edge if getattr(self, "ema_e", None) is None else 0.3 * self.ema_e + 0.7 * edge
            self.last_edge = self.ema_e
            L = np.digitize(self.ema, self.EDGES); E = np.digitize(self.ema_e, self.EDGE_EDGES)
            sym = (L + 8 * E).astype(int)
            if self.fovea is not None:                 # what is actually seen is round
                sym = self.fovea.apply(sym)
            return sym
        except Exception:
            return None


# ------------------------------------------------------------------ the hand
class Hand:
    """A CONTINUOUS hand: keys are a held STATE, not taps. Each look the policy says which keys should be
    down; the hand presses what is newly needed and releases what is no longer wanted, so 'right' across
    ten looks is one long hold and a jump is 'up' tapped while 'right' stays down (Jonathan: 'the right
    button needs to be held during the jump — a continuous flow in and out')."""
    KEYS = {"left": ["left"], "right": ["right"], "jump": ["up"], "jumpleft": ["left", "up"],
            "jumpright": ["right", "up"], "grab": ["ctrl"], "grableft": ["ctrl", "left"],
            "grabright": ["ctrl", "right"], "wait": [],
            # chords: three fingers down at once, like a guitar chord — run+jump+attack is ONE shape
            "jumpgrab": ["up", "ctrl"], "jumpgrableft": ["left", "up", "ctrl"],
            "jumpgrabright": ["right", "up", "ctrl"]}
    TAP = {"up"}                                      # keys that are tapped, not held (a jump is an impulse)

    def __init__(self, hwnd, hold: float = 0.35, dry: bool = False, emit: Optional[Dict[str, str]] = None):
        self.hwnd, self.hold, self.dry = hwnd, hold, dry
        # emit: component -> the PHYSICAL key this game actually listens to, learned from watching
        # the expert (models/hand_keys.json). Default = the component itself (arrows+ctrl, Limbo).
        self.emit = {k: v.lower() if v not in ("lmb", "rmb") else v for k, v in (emit or {}).items()}
        if not dry:
            import pydirectinput
            pydirectinput.PAUSE = 0; pydirectinput.FAILSAFE = False; self.pdi = pydirectinput   # keys only; STOP file is our fail-safe
        self.held: Set[str] = set()

    def _down(self, comp: str):
        p = self.emit.get(comp, comp)
        if p == "lmb": self.pdi.mouseDown()
        elif p == "rmb": self.pdi.mouseDown(button="right")
        else: self.pdi.keyDown(p)

    def _up(self, comp: str):
        p = self.emit.get(comp, comp)
        if p == "lmb": self.pdi.mouseUp()
        elif p == "rmb": self.pdi.mouseUp(button="right")
        else: self.pdi.keyUp(p)

    def press(self, action: str) -> bool:
        """Bring the held state to what `action` wants, keep it for one look, tap the impulses."""
        want = set(self.KEYS[action])
        if self.dry or (self.hwnd is not None and not is_foreground(self.hwnd)):
            time.sleep(self.hold); return False
        for k in self.held - want:                    # release what is no longer wanted
            self._up(k)
        for k in want - self.held:                    # press what is newly wanted (holds stay down)
            if k not in self.TAP: self._down(k)
        self.held = {k for k in want if k not in self.TAP}
        taps = [k for k in want if k in self.TAP]
        for k in taps: self._down(k)
        time.sleep(self.hold if not taps else min(self.hold, 0.12))
        for k in taps: self._up(k)
        if taps and self.hold > 0.12: time.sleep(self.hold - 0.12)
        return True

    def release_all(self):
        if self.dry: self.held = set(); return
        for k in ("left", "right", "up", "ctrl"):
            try: self._up(k)
            except Exception: pass
        self.held = set()


# ------------------------------------------------------------------ the person
class Player:
    def __init__(self, world: str, title: str, root: str, fps: float = 8, H=96, W=160, tile=8,
                 dry: bool = False, seed: int = 0, sound: bool = False, hands_off: bool = False, hwnd=None,
                 rect_fn=None):
        self.world, self.root, self.sound = world, root, sound
        self.hands_off = hands_off                      # SPORE observe/practice: eyes on, hand never touches a key
        self.atlas_path = os.path.join(root, f"atlas_{world}.npz")
        self.atlas = Atlas.load(self.atlas_path, H, W) if os.path.exists(self.atlas_path) else Atlas(H, W)
        # the rotation eye (mouse-driven sheet turning → a panorama ring + the HUD layer); persists per world
        self.rot_paths = (os.path.join(root, f"panorama_{world}.npz"), os.path.join(root, f"panorama_{world}.json"))
        self.rot = RotationEye.load(H, W, *self.rot_paths) if os.path.exists(self.rot_paths[0]) else RotationEye(H, W)
        self.depth_path = os.path.join(root, f"depth_{world}.npz")
        self.trans = TranslationEye.load(H, W, self.depth_path) if os.path.exists(self.depth_path) else TranslationEye(H, W)
        os.makedirs(os.path.join(root, "lives"), exist_ok=True)
        self.rect_fn = rect_fn
        if rect_fn is not None:
            self.hwnd = None                        # the porthole IS the window
        else:
            self.hwnd = hwnd if hwnd is not None else (find_window(title) if not dry else None)
            if self.hwnd is None and not dry:
                raise SystemExit(f"no window with '{title}' in its title — launch the game first")
        self.eye = Eye(self.hwnd, H, W, rect_fn=rect_fn) if not dry else None
        # the expert's own keys, counted while watching: models/hand_keys.json {channel: {physkey: n}}
        self._keycount_path = os.path.join(root, "models", "hand_keys.json")
        try:
            with open(self._keycount_path, "r", encoding="utf-8") as f: self.keycount = json.load(f)
        except Exception:
            self.keycount = {}
        emit = self._emit_map()
        self.hand = Hand(self.hwnd, dry=dry, emit=emit)
        self._emit_note = emit
        self.fps, self.H, self.W, self.tile = fps, H, W, tile
        self.rng = random.Random(seed)
        self.coach = Coach(root, world)
        self.narr = open(os.path.join(root, f"narration_{world}.txt"), "a", encoding="utf-8")
        self.actions = [a for a in Hand.KEYS if a != "wait"]
        self.mode = "human" if hands_off else "agent"; self.demo: List[Tuple[str, float]] = []; self.demo_n = 0
        self.practice = {"hand_hit": 0, "hand_n": 0, "eye_miss": 0, "eye_n": 0}   # practice recognising: prequential
        self.plan: deque = deque()                         # the action stream: a route sent out continuously
        os.makedirs(os.path.join(root, "demos"), exist_ok=True)
        # the pressure line for speech: charge fills with surprise; a thought is spoken when it crosses the
        # threshold; a big surprise while it fills interrupts and empties the line (the message changes)
        self.speech_charge = 0.0; self.speech_threshold = 60.0
        self._shot_t = 0.0; self._shot_n = 0; self._stats_dir = None      # the stats organ's raw samples
        from collections import deque as _dq
        self._clipbuf: deque = deque(maxlen=40)                            # the dashcam: last ~10 s of raw footage
        self._clip_t = 0.0
        self.life_n = self.coach.core["lives"] + 1
        self.new_life()
        if self._emit_note and not hands_off:
            self.say("hand keymap learned from watching: " + ", ".join(f"{k}->{v}" for k, v in self._emit_note.items()))

    def _emit_map(self) -> Dict[str, str]:
        """Majority physical key per channel, from watching the expert. Channel 'l' maps the hand's
        'left' component, etc. Only overrides when the majority key differs from the default."""
        PHYS = {"A": "a", "D": "d", "W": "w", "E": "e", "space": "space", "shift": "shift",
                "left": "left", "right": "right", "up": "up", "ctrl": "ctrl", "lmb": "lmb", "rmb": "rmb"}
        comp = {"l": "left", "r": "right", "u": "up", "c": "ctrl"}
        emit = {}
        for ch, hand_key in comp.items():
            cnt = self.keycount.get(ch) or {}
            if cnt:
                best = max(cnt, key=lambda k: cnt[k])
                phys = PHYS.get(best, best.lower())
                if phys != hand_key: emit[hand_key] = phys
        return emit

    # ---------------- narration (grounded: only atoms and numbers)
    def say(self, text: str):
        line = f"[{time.strftime('%H:%M:%S')} L{getattr(self, 'life_n', 1)} a{self.n_act}] {text}"
        try: self.narr.write(line + "\n"); self.narr.flush()
        except Exception: pass
        print(line, flush=True)

    # ---------------- life
    def new_life(self):
        self.mon = SurpriseMonitor(self.H, self.W, self.tile, use_camera=True)
        seed = self.coach.reseed()
        self.pressure = seed["pressure"]
        self.n_act = 0; self.frames: List[np.ndarray] = []; self.acts: List[str] = []; self.events: List[Set[str]] = []
        self.path: List[Dict] = []; self.life_t0 = time.time(); self.last_rest = time.time(); self.mouse: List[Tuple[int, int]] = []
        self.probe_queue = deque([a for a in self.actions for _ in range(2)])
        self.rng.shuffle(self.probe_queue)
        self.pos_hist: deque = deque(maxlen=6); self.scroll_total = 0
        self.dark_frames = 0; self.was_dark = False; self.escalate = 0; self.gaze = None; self.cuts = 0
        self.progress_dir: Dict[str, float] = {a: 0.0 for a in self.actions + ["wait"]}
        self.wall = Wall(self.H, self.W, sound=self.sound, atlas=self.atlas); self.born = False; self.last_action = None
        self.drive = 0.0; self.tilt: Dict[str, float] = {}; self.tilt_why = ""
        self.flower: Dict[int, int] = {}; self.flower_surp = [0, 0]      # engaged-channel histogram; [sum, n] on surprise steps
        self._engaged: Set[str] = set()
        mail = [h["text"] if isinstance(h, dict) else str(h) for h in seed.get("hypotheses", [])]
        ctx = _load(os.path.join(self.root, "rain.json"), {}).get("context")
        if ctx: mail = [str(ctx)] + mail
        self.mailband = MailBand(mail, self.W, sound=self.sound) if mail else None
        if mail: self.say(f"mail at the border: {len(mail)} letter(s) will cross the window edge this life")
        self.trained = self._load_trained_hand(); self.ttilt: Dict[str, float] = {}
        try:
            import pickle
            with open(os.path.join(self.root, "models", "eye.pkl"), "rb") as f: self.trained_eye = pickle.load(f)
        except Exception: self.trained_eye = None
        # innate cost of actions (the reserve law): a jump spends more than a step; the hand prefers cheap moves
        self.cost = {a: (1.6 if "jump" in a else 1.2 if "grab" in a else 1.0) for a in self.actions + ["wait"]}
        for k, v in seed["mover_prior"].items():          # invariants as PRIORS (weak votes), re-earned by play
            a = k
            if a in self.actions and tuple(v) in self.mon.mover.S:
                self.mon.mover.votes[a][self.mon.mover.S.index(tuple(v))] += 3
        self.say(f"born. pressure={'yes' if self.pressure is not None else 'none'} priors={list(seed['mover_prior'])} "
                 f"concepts={len(seed['concepts'])} hypotheses={len(seed['hypotheses'])}")
        for h in seed["hypotheses"]: self.say(f"rain (untrusted): {h['text']}")

    def atoms_for(self, action: str, info: Dict, frame: np.ndarray) -> Set[str]:
        ev = set()
        m = self.mon.mover
        d = m.displacement(action)
        moved = m.obj_pos is not None and len(self.pos_hist) >= 1 and self.pos_hist[-1] is not None and \
            m.obj_pos != self.pos_hist[-1]
        ev |= set(info.get("body", set()))
        if d != (0, 0): ev.add(f"mover.moved:{action}" if moved else f"mover.blocked:{action}")
        if info["cam"] != (0, 0): ev.add("camera.scrolled"); self.scroll_total += abs(info["cam"][0]) + abs(info["cam"][1])
        for (a, c), (delta, end) in m and self.mon.counter.laws().items():
            if a == action: ev.add(f"counter.{'down' if delta < 0 else 'up'}:{c}")
        if info["err"] > 0.3 * frame.size: ev.add("surprise.big")
        elif info["err"] > 0: ev.add("surprise.small")
        return ev

    def _seal_clip(self, why: str):
        """Seal the dashcam buffer as a clip (the rawest sediment; clips.py digests it in the sleep)."""
        if len(self._clipbuf) < 8 or time.time() - self._clip_t < 45: return
        self._clip_t = time.time()
        try:
            cdir = os.path.join(self.root, "clips"); os.makedirs(cdir, exist_ok=True)
            buf = list(self._clipbuf)
            np.savez_compressed(os.path.join(cdir, time.strftime("clip_%Y%m%d_%H%M%S.npz")),
                                J=np.array([b for _, b, _ in buf], dtype=object),
                                T=np.array([t for t, _, _ in buf]),
                                A=np.array([a for _, _, a in buf]))
            self.say(f"(kept the last {len(buf)} looks as a clip: {why})")
        except Exception: pass

    def _save_shot(self):
        """A raw screenshot every ~20 s (and at deposits) → <root>/stats/session_*/ for the stats
        organ: the lower ocean's seeing model reads the HUD numbers from these in the sleep."""
        self._shot_t = time.time()
        try:
            from PIL import Image
            raw = self.eye.last_raw
            if raw is None: return
            img = np.asarray(raw)[:, :, :3][:, :, ::-1]                    # BGRA → RGB
            if self._stats_dir is None:
                self._stats_dir = os.path.join(self.root, "stats", time.strftime("session_%Y%m%d_%H%M%S"))
                os.makedirs(self._stats_dir, exist_ok=True)
            im = Image.fromarray(img)
            if im.width > 960: im = im.resize((960, int(im.height * 960 / im.width)))
            self._shot_n += 1
            im.save(os.path.join(self._stats_dir, f"shot_{self._shot_n:04d}.jpg"), quality=72)
        except Exception:
            pass

    def _load_trained_hand(self):
        """train.py's behaviour-cloning model, if the sleep has produced one: an untrusted prior on the hand."""
        p = os.path.join(self.root, "models", "hand.pkl")
        try:
            import pickle
            with open(p, "rb") as f: d = pickle.load(f)
            self.say(f"trained hand loaded ({time.strftime('%H:%M', time.localtime(os.path.getmtime(p)))})")
            return d
        except Exception:
            return None

    def trained_tilt(self, frame: np.ndarray) -> Dict[str, float]:
        if not self.trained or frame is None: return {}
        try:
            import train as _tr
            x = _tr.features(frame, self.last_action or "wait", self.mouse[-1] if self.mouse else (0, 0))[None, :]
            pr = self.trained["model"].predict_proba(x)[0]
            cls = list(self.trained["model"].classes_)
            return {self.trained["actions"][int(c)]: float(pr[i]) for i, c in enumerate(cls)}
        except Exception:
            return {}

    def choose(self) -> str:
        E = self._engaged
        if self.plan: E.add("mover"); return self.plan.popleft()   # a planned stream flows out until it ends or is cut
        if self.probe_queue: return self.probe_queue.popleft()
        m = self.mon.mover
        if self.rng.random() < 0.12: return self.rng.choice(self.actions)          # the reserve
        # blocked? (position unchanged over recent moves)
        if len(self.pos_hist) >= 4 and len({p for p in self.pos_hist if p is not None}) <= 1:
            self.escalate += 1
            lead_a = max(self.progress_dir, key=self.progress_dir.get)
            d = "right" if lead_a in ("right", "jumpright", "grabright") else "left" if lead_a in ("left", "jumpleft", "grableft") else self.rng.choice(["left", "right"])
            # blocked: plan a continuous move — run, jump while still running, land running (held + tap)
            routes = [[d, "jump" + d, d, d], ["grab" + d, "grab" + d, d], [d, d, "jump" + d, "jump" + d, d],
                      [("left" if d == "right" else "right")] * 2 + [d, "jump" + d, d]]
            E.add("mover"); E.add("map")
            self.plan.extend(routes[self.escalate % len(routes)])
            return self.plan.popleft()
        self.escalate = 0
        # gaze: hottest region; target = random point INSIDE that box
        i, j = self.mon.hottest_region(self.pressure)
        self.gaze = (i, j)
        if self.mon.surprise.max() < 4.0 and self.wall.window.misalignment() > 0:
            E.add("map")
            ty, tx = self.wall.target_in_window(self.rng)          # nothing surprising: go where the window is
        else:
            ty = i * self.tile + self.rng.randrange(self.tile); tx = j * self.tile + self.rng.randrange(self.tile)
        if self.mon.body.pos is None:
            # no known body yet (black on black): salience is innate — walk toward contrast, and re-probe
            if self.n_act % 60 == 0: self.probe_queue.extend(self.actions)
            if max(self.progress_dir.values()) > 0.5:
                return max(self.actions, key=lambda a: self.progress_dir[a] + self.rng.random() * 0.1)
            f = self.frames[-1] if self.frames else None
            if f is not None:
                col = f.astype(float).std(axis=0); left, right = col[: self.W // 2].mean(), col[self.W // 2:].mean()
                return self.rng.choice(["right", "jumpright"]) if right > left else self.rng.choice(["left", "jumpleft"])
            return self.rng.choice(self.actions)
        if self.mon.body.hidden_for > 0:
            E.add("body")
            # can't see him: don't reset — keep doing what was opening ground (walk past the tree)
            lead_a = max(self.progress_dir, key=self.progress_dir.get)
            return lead_a if self.progress_dir[lead_a] > 0.3 else self.last_action or self.rng.choice(self.actions)
        oy, ox = self.mon.body.pos
        E.add("body"); E.add("mover")
        if max(list(self.tilt.values()) or [0]) > 0.05 or max(list(self.ttilt.values()) or [0]) > 0.05: E.add("tilt")
        best, bd = None, float("inf")
        for a in self.actions:
            dy, dx = m.displacement(a)
            if (dy, dx) == (0, 0): continue
            dist = (abs(oy + dy - ty) + abs(ox + dx - tx)) * self.cost[a] - 0.5 * self.progress_dir[a] \
                - 3.0 * self.tilt.get(a, 0.0) - 4.0 * self.ttilt.get(a, 0.0)   # persona tilt + trained hand (both untrusted)
            if dist < bd: best, bd = a, dist
        return best or self.rng.choice(self.actions)

    def hotkeys(self) -> None:
        """F8: you take the controls (expert); the hand lets go and the eyes keep learning from YOUR keys.
        F9: you are done; the demonstration is saved and the hand WAITS (paused) for your reset.
        F10: reset done — the novice replays your inputs, then continues on its own."""
        if self.hand.dry or self.hands_off: return
        if key_down("F8") and self.mode != "human":
            self.hand.release_all(); self.mode = "human"; self.demo = []; self.probe_queue.clear()
            self.say("you have the controls — watching (expert plays, novice learns)")
            time.sleep(0.3)
        elif key_down("F9") and self.mode == "human":
            self.mode = "paused"; self.demo_n += 1
            path = os.path.join(self.root, "demos", f"{self.world}_demo_{self.demo_n:03d}.json")
            _save(path, {"steps": self.demo, "t": time.time()})
            self.say(f"demonstration recorded: {len(self.demo)} steps ({sum(1 for a,_ in self.demo if a!='wait')} presses) -> {os.path.basename(path)}. "
                     "paused: reset the game to where you started, then press F10 and I will repeat it")
            time.sleep(0.3)
        elif key_down("F10") and self.mode == "paused":
            self.mode = "replay"; self.replay_i = 0
            self.say("replaying your demonstration (the novice re-grows the expert's path in its own coordinates)")
            time.sleep(0.3)

    def step(self) -> bool:
        t0 = time.time()
        self.hotkeys()
        if self.mode == "human":
            if self.hand.held: self.hand.release_all()
            action = human_action(); hold = 1.0 / self.fps
            if action != "wait":                       # count WHICH keys the expert's fingers used
                for ch, k in human_keys().items():
                    self.keycount.setdefault(ch, {})[k] = self.keycount.get(ch, {}).get(k, 0) + 1
            time.sleep(hold)
            if not self.hands_off: self.demo.append((action, round(hold, 3)))
        elif self.mode == "paused":
            time.sleep(0.2); return True
        elif self.mode == "replay":
            if self.replay_i >= len(self.demo):
                self.mode = "agent"; self.say("demonstration replayed — continuing on my own"); return True
            action, hold = self.demo[self.replay_i]; self.replay_i += 1
            old = self.hand.hold; self.hand.hold = hold; pressed = self.hand.press(action); self.hand.hold = old
            if not pressed: self.say("waiting: game window is not in the foreground"); time.sleep(1.0); return True
        else:
            self.ttilt = self.trained_tilt(self.eye.ema_frame() if self.eye and hasattr(self.eye, "ema_frame") else self.frames[-1] if self.frames else None)
            action = self.choose()
            pressed = self.hand.press(action)
            if not pressed and not self.hand.dry:
                self.say("waiting: game window is not in the foreground"); time.sleep(1.0); return True
        frame = self.eye.look() if self.eye else self.fake_frame(action)
        if frame is None: time.sleep(0.5); return True
        if self.eye is not None and time.time() - self._shot_t > 20:
            self._save_shot()
        if self.eye is not None and self.eye.last_raw is not None:
            try:
                from PIL import Image
                import io as _io
                img = np.asarray(self.eye.last_raw)[:, :, :3][:, :, ::-1]
                im = Image.fromarray(img)
                if im.width > 480: im = im.resize((480, int(im.height * 480 / im.width)))
                b = _io.BytesIO(); im.save(b, format="JPEG", quality=60)
                self._clipbuf.append((time.time(), b.getvalue(), action))
            except Exception: pass
        mail_mask = None
        if self.mailband is not None and not self.mailband.done:
            band = self.mailband.step()
            if band is not None:
                vis = band >= 0
                frame = frame.copy(); frame[:BAND_ROWS, :][vis] = band[vis]
                mail_mask = self.mailband.mask(self.H)
            elif self.mailband.done:
                self.say("the letter finished crossing the border")
        info = self.mon.step(frame, action)
        if not self.born:
            b = self.wall.birth(frame); self.born = True
            self.say("I recognise this place: map position %s" % (self.wall.atlas.pos,) if "wall.recognised" in b
                     else "unknown place: starting a new region of the map")
        self.n_act += 1
        mdx, mdy = mouse_delta() if not self.hand.dry else (0, 0)
        self.mouse.append((mdx, mdy))
        rinfo = self.rot.step(self.frames[-1] if self.frames else None, frame, (mdx, mdy))
        if self.n_act % 2 == 0:
            tinfo = self.trans.step(self.frames[-1] if self.frames else None, frame, action,
                                    rinfo["shift"], hud=self.rot.hud_mask())
        else: tinfo = {"used": False}
        if self.hands_off and self.trained and self.frames:          # practice: guess what the human will do / what will change
            try:
                import train as _tr
                x = _tr.features(self.frames[-1], self.last_action or "wait", self.mouse[-2] if len(self.mouse) > 1 else (0, 0))[None, :]
                guess = self.trained["actions"][int(self.trained["model"].predict(x)[0])]
                self.practice["hand_n"] += 1; self.practice["hand_hit"] += int(guess == action)
                if getattr(self, "trained_eye", None):
                    xa = x.copy(); xa[0, -len(_tr.ACTIONS):] = 0; xa[0, -len(_tr.ACTIONS) + _tr.ACTIONS.index(action)] = 1
                    pred = (self.trained_eye["model"].predict(xa)[0] > 0.5)
                    real = _tr.region_change(self.frames[-1], frame).astype(bool)
                    self.practice["eye_n"] += real.size; self.practice["eye_miss"] += int((pred != real).sum())
            except Exception: pass
        self.frames.append(frame.astype(np.int8)); self.acts.append(action)
        ev = self.atoms_for(action, info, frame)
        ev |= rinfo["events"]
        if "rotation.turn_closed" in ev: self.say(f"the ring closed: one full turn is {int(self.rot.turn_width)} px — " + self.rot.summary())
        if "rotation.gain_learned:x" in ev or "rotation.gain_learned:y" in ev: self.say("learned how far the mouse turns the sheet: " + self.rot.summary())
        if abs(mdx) + abs(mdy) > 6:
            ev.add("mouse.moved:" + ("R" if mdx > 0 else "L" if mdx < 0 else "") + ("D" if mdy > 0 else "U" if mdy < 0 else ""))
        if key_down("lmb") and not self.hand.dry: ev.add("mouse.left")
        if key_down("rmb") and not self.hand.dry: ev.add("mouse.right")
        # the window is dragged ahead in the direction that has been opening new ground
        lead_a = max(self.progress_dir, key=self.progress_dir.get)
        lead = {"left": (0, -self.W // 4), "right": (0, self.W // 4), "jumpleft": (0, -self.W // 4),
                "jumpright": (0, self.W // 4), "jump": (-self.H // 4, 0)}.get(lead_a, (0, 0)) \
            if self.progress_dir[lead_a] > 0.5 else (0, 0)
        bmask = self.mon.mover.obj_mask if self.mon.body.visible() else None
        if mail_mask is not None:
            bmask = mail_mask if bmask is None else (bmask | mail_mask)      # mail is weather, not geography
        wev = self.wall.update(frame, info["cam"], self.mon.body.pos, bmask, progress=lead)
        for e in ("body.confirmed", "body.occluded", "body.reacquired", "body.lost", "camera.drift"):
            if e in ev and (e != "camera.drift" or self.n_act % 10 == 0):
                self.say(f"{e} at {None if self.mon.body.pos is None else tuple(int(v) for v in self.mon.body.pos)}")
        if "body.occluded" in ev and self.wall.body_world is not None: self.wall.occluders.append(self.wall.body_world)
        if self.mode == "human": ev.add("hand.human")          # the expert's steps (train.py weights them)
        if mail_mask is not None: ev.add("border.mail")
        ev |= wev
        # the flower: which of the seven channels were engaged this look
        E = self._engaged
        if any(e.startswith("body.") for e in ev): E.add("body")
        if any(e.startswith(("mover.", "object.")) for e in ev): E.add("mover")
        if any(e.startswith("counter.") for e in ev): E.add("counter")
        if any(e.startswith(("wall.", "window.")) for e in ev): E.add("map")
        if any(e.startswith("rotation.") for e in ev) or rinfo["shift"] != (0, 0): E.add("rotation")
        if tinfo.get("used"): E.add("rotation")                      # the depth reading is the same sheet-eye
        k = max(1, len(E))                                            # the center (attention) is always on
        self.flower[k] = self.flower.get(k, 0) + 1
        if "surprise.big" in ev: self.flower_surp[0] += k; self.flower_surp[1] += 1
        self._engaged = set()
        self.events.append(ev)
        if "wall.realigned" in wev and self.wall.realigns % 5 == 1: self.say(f"realigned the map ({self.wall.realigns}x)")
        for e in wev:
            if e.startswith("window.exit"): self.say(f"body crossed the window border ({e.split(':')[1]})")
        self.pos_hist.append(None if self.mon.body.pos is None else (round(self.mon.body.pos[0]), round(self.mon.body.pos[1])))
        self.last_action = action
        # the loop's segment for this look: the body's world delta (camera-compensated), jump as an impulse
        bw = self.wall.body_world
        prev_bw = getattr(self, "_prev_bw", None)
        dyx = (bw[0] - prev_bw[0], bw[1] - prev_bw[1]) if (bw is not None and prev_bw is not None) else (0.0, 0.0)
        self._prev_bw = bw
        self.path.append({"t": round(time.time() - self.life_t0, 3), "dx": round(float(dyx[1]), 2),
                          "dy": round(float(dyx[0]), 2), "jump": 1.0 if "jump" in action else 0.0})
        self.life_t0 = time.time()
        new_ground = self.wall.new_ground_total - getattr(self, "_ng_prev", 0); self._ng_prev = self.wall.new_ground_total
        reward = 0.002 * new_ground + (0.3 if "camera.scrolled" in ev else 0.0) + (0.5 if "body.confirmed" in ev else 0.0)
        self.drive = 0.98 * self.drive + reward                              # expanding the map feels good
        if reward > 0: self.progress_dir[action] = 0.9 * self.progress_dir[action] + reward
        else: self.progress_dir[action] *= 0.95
        # the observer's speech is a PRESSURE line: it fills with surprise and time, is spoken at the threshold,
        # and a big surprise while it fills empties it (the thought changes before it is said)
        self.speech_charge += 0.5 + 0.02 * info["err"]
        if info["err"] > 0.35 * frame.size and self.plan:
            self.plan.clear(); self.say("(plan cut: a real surprise while the route was flowing)")
        if info["err"] > 0.35 * frame.size and self.speech_charge > 0.3 * self.speech_threshold:
            self._engaged.add("speech")
            self.speech_charge = 0.0
            if time.time() - getattr(self, "_int_t", 0) > 5:
                self._int_t = time.time(); self.say("(interrupted: the surprise changed what I was going to say)")
        if self.speech_charge >= self.speech_threshold and self.coach.models and self.mode == "agent":
            self._engaged.add("speech")
            self.speech_charge = 0.0
            # the observer NEVER holds the hand: advice is fetched in a thread and lands when ready
            # (a synchronous Ollama call here froze the play loop to 3 actions a minute)
            if getattr(self, "_advising", None) is None or not self._advising.is_alive():
                from collections import Counter
                import threading as _th
                cnt = dict(Counter(a for e in self.events[-120:] for a in e).most_common(10))
                ctx = _load(os.path.join(self.root, "rain.json"), {}).get("context", "an unknown place")   # the teacher's hint, untrusted
                concepts = list(self.coach.core["concepts"]); summ = self.wall.summary()
                def _adv():
                    try:
                        import lower
                        adv = lower.advise(self.coach.models[0], cnt, concepts, summ, self.actions, context=ctx)
                        if adv and adv.get("why"):
                            self.tilt, self.tilt_why = adv["tendency"], adv["why"]
                            self.say("the observer thinks: " + self.tilt_why)
                    except Exception: pass
                self._advising = _th.Thread(target=_adv, daemon=True); self._advising.start()
        # narration on events worth a sentence
        if self.n_act == len(self.actions) * 2 + 1:
            self.say("probe done: " + ", ".join(f"{a}->{self.mon.mover.displacement(a)}" for a in self.actions
                                                 if self.mon.mover.displacement(a) != (0, 0)) or "nothing moved")
        if "surprise.big" in ev and time.time() - getattr(self, "_surp_say_t", 0) > 2:      # narrate at most one per 2 s (menus flood otherwise)
            self._surp_say_t = time.time()
            self.say(f"big surprise ({info['err']} px) at region {self.mon.hottest_region()} after {action}")
        if "surprise.big" in ev and info["err"] > 0.5 * frame.size: self._seal_clip("surprise")
        if self.n_act % 50 == 0 and self.eye is not None and self.eye.last_raw is not None:
            try:
                import mss.tools
                mss.tools.to_png(self.eye.last_raw.rgb, self.eye.last_raw.size, output=os.path.join(self.root, "debug_last.png"))
                np.save(os.path.join(self.root, "debug_grid.npy"), frame)
                if getattr(self.eye, "last_edge", None) is not None: np.save(os.path.join(self.root, "debug_edge.npy"), self.eye.last_edge)
                if len(self.frames) >= 2: np.save(os.path.join(self.root, "debug_grid_prev.npy"), self.frames[-2])
                np.savez_compressed(os.path.join(self.root, "debug_frames.npz"), F=np.array(self.frames[-60:], dtype=np.int8),
                                    A=np.array(self.acts[-60:]))
            except Exception: pass
        if self.n_act % 40 == 0:
            self.say(f"explained {100*self.mon.explained_fraction():.0f}% so far; gaze {self.gaze}; scroll {self.scroll_total}; "
                     f"body at {None if self.mon.body.pos is None else tuple(int(v) for v in self.mon.body.pos)}"
                     f"{' (hidden %d)' % self.mon.body.hidden_for if self.mon.body.hidden_for else ''}; "
                     + self.wall.summary() + f"; drive {self.drive:.1f}")
        # death: the SCENE's light collapses (fade to black) then returns — judged on the eye's raw luminance,
        # not on symbols (black is a level too)
        lum = float(self.eye.ema.mean()) if self.eye is not None and self.eye.ema is not None else float(frame.mean())
        self.lum_avg = lum if not hasattr(self, "lum_avg") else 0.98 * self.lum_avg + 0.02 * lum
        dark = lum < 0.35 * max(1e-6, self.lum_avg) if self.eye is not None else frame.mean() < 0.4
        cut = info["e0"] > 0.6 * frame.size and info["cam"] == (0, 0) and self.n_act > 30 and not self.hands_off
        self.cuts = self.cuts + 1 if cut else 0
        if self.cuts >= 2:
            self.die("scene-cut"); self.cuts = 0; return True
        # REST: even without dying, deposit every 6 minutes (sleep is the other between-runs moment)
        if time.time() - self.last_rest > (180 if self.hands_off else 360):
            self.rest()
        if dark: self.dark_frames += 1
        elif self.dark_frames >= 3:
            self.die("fade-to-black"); self.dark_frames = 0; return True
        else: self.dark_frames = 0
        if self.n_act >= 600 and self.scroll_total == 0 and self.mon.mover.obj_pos is None:
            self.die("nothing-ever-moved"); return True
        # pace: fixed looks per second
        dt = time.time() - t0
        if dt < 1.0 / self.fps: time.sleep(1.0 / self.fps - dt)
        return True

    def rest(self):
        """Sleep: deposit what this life has so far into the ocean without ending it."""
        self.last_rest = time.time()
        self.deposit("rest")
        self.say("rested: deposited so far (life continues)")

    def die(self, cause: str):
        self.hand.release_all()
        self.deposit(cause)
        self.life_n += 1
        self.new_life()

    def deposit(self, cause: str):
        life = {"n_actions": self.n_act, "cause": cause, "events": self.events,
                "mover_laws": {a: list(self.mon.mover.displacement(a)) for a in self.actions if self.mon.mover.displacement(a) != (0, 0)},
                "counter_laws": {f"{a}:{c}": [d, e] for (a, c), (d, e) in self.mon.counter.laws().items()},
                "charge": self.mon.surprise.tolist(), "explained": round(self.mon.explained_fraction(), 3),
                "camera_scroll_total": self.scroll_total}
        n = self.life_n
        np.savez_compressed(os.path.join(self.root, "lives", f"{self.world}_{n:03d}.npz"),
                            F=np.array(self.frames, dtype=np.int8), A=np.array(self.acts),
                            E=np.array(["|".join(sorted(e)) for e in self.events]), M=np.array(self.mouse, dtype=np.int32).reshape(-1, 2))
        life["map"] = self.wall.summary(); life["occluders"] = [list(map(float, o)) for o in self.wall.occluders]
        life["drive"] = round(self.drive, 2)
        if self.hands_off:
            p = self.practice
            life["practice"] = {"hand_acc": round(p["hand_hit"] / max(1, p["hand_n"]), 3), "steps": p["hand_n"],
                                "eye_err": round(p["eye_miss"] / max(1, p["eye_n"]), 4)}
            self.say(f"practice: guessed your key {100*life['practice']['hand_acc']:.0f}% of {p['hand_n']} steps, "
                     f"eye error {life['practice']['eye_err']}")
            self.practice = {"hand_hit": 0, "hand_n": 0, "eye_miss": 0, "eye_n": 0}
        try:   # the inner core: bytes of what survives (atlas + core) over bytes of everything seen (lives)
            raw = sum(os.path.getsize(os.path.join(self.root, "lives", f)) for f in os.listdir(os.path.join(self.root, "lives")))
            kept = sum(os.path.getsize(os.path.join(self.root, f)) for f in os.listdir(self.root)
                       if f.startswith(("atlas_", "core_")))
            life["sediment_ratio"] = round(kept / max(1, raw), 3)
        except Exception: life["sediment_ratio"] = None
        self.wall.atlas.save(self.atlas_path)
        if self.keycount:                              # the expert's keys: what a playing hand must press
            try:
                os.makedirs(os.path.dirname(self._keycount_path), exist_ok=True)
                with open(self._keycount_path, "w", encoding="utf-8") as f: json.dump(self.keycount, f, indent=1)
            except Exception: pass
        if self.eye is not None: self._save_shot()                         # end screens carry the score
        if self.eye is not None: self._seal_clip(cause)
        try: self.trans.save(self.depth_path)
        except Exception: pass
        if self.flower:
            tot = sum(self.flower.values())
            mean = sum(k * n for k, n in self.flower.items()) / tot
            mode = max(self.flower, key=self.flower.get)
            surp = self.flower_surp[0] / self.flower_surp[1] if self.flower_surp[1] else None
            life["flower"] = {"hist": {str(k): n for k, n in sorted(self.flower.items())}, "mean": round(mean, 2),
                              "mode": mode, "surprise_mean": None if surp is None else round(surp, 2)}
            self.say(f"flower: mode {mode}, mean {mean:.1f} channels engaged" +
                     (f", {surp:.1f} on surprise steps" if surp else "") + f" | {self.trans.summary()}")
        try:
            self.rot.save(*self.rot_paths); life["rotation"] = self.rot.summary()
            if self.rot.evidence["x"] + self.rot.evidence["y"] > 0: self.say(self.rot.summary())
        except Exception as e: self.say(f"(panorama save failed: {e})")
        # the coach works in the SLEEP between lives, never in the frame loop: digestion runs in a
        # background thread (Ollama builders can take minutes); the hand is free immediately.
        if getattr(self, "_digesting", None) is not None and self._digesting.is_alive():
            self.say("(still digesting the previous deposit; this one is kept as npz only)"); return
        import threading, copy as _copy
        snap = (life, n, cause, list(self.path), [sorted(e) for e in self.events])
        self._digesting = threading.Thread(target=self._digest, args=snap, daemon=True); self._digesting.start()

    def _digest(self, life, n, cause, path, events):
        try:
            out = self.coach.at_death(life)
        except Exception as e:
            self.say(f"(coach failed: {e})"); return
        self.say(f"died ({cause}) after {life['n_actions']} actions, explained {100*life['explained']:.0f}%, scroll {life['camera_scroll_total']}, "
                 f"drive {life['drive']:.1f}, sediment ratio {life.get('sediment_ratio')}. "
                 f"coach: graduated {out['graduated'] or 'nothing'}; hot {[(round(h[0],2),h[1],h[2]) for h in out['hot']]}")
        if out.get("story"): self.say("the lower ocean says: " + out["story"].replace("\n", " "))
        _save(os.path.join(self.root, "lightning.json"), self.coach.core["lightning"])
        # the life as a .geo loop (the colony's format): segments = the body's path, bubbles at thresholds, closure at death
        try:
            tail = ""
            try:
                with open(os.path.join(self.root, f"narration_{self.world}.txt"), "r", encoding="utf-8") as f:
                    tail = "".join(f.readlines()[-80:])
            except Exception: pass
            cont = geo.life_container(self.world, n, path, events, tail,
                                      {"mover": life["mover_laws"], "counter": life["counter_laws"]},
                                      self.atlas_path, self.coach.core_path, cause,
                                      {"drive": life["drive"], "explained": life["explained"], "scroll": life["camera_scroll_total"],
                                       "W": self.W, "H": self.H, "sediment_ratio": life.get("sediment_ratio")})
            geo.write_geo(os.path.join(self.root, "lives", f"{self.world}_{n:03d}{'' if cause != 'rest' else '_rest'}.geo"),
                          cont, dormant=(cause == "rest"))
        except Exception as e:
            self.say(f"(geo write failed: {e})")

    # dry-run world (no window): a scrolling synthetic strip so the loop can be tested anywhere
    def fake_frame(self, a: str):
        if not hasattr(self, "_w"):
            r = np.random.default_rng(0); self._w = r.integers(0, 5, (self.H, self.W * 8)); self._ox = 40; self._oy = self.H // 2; self._t = 0
        dx = {"left": -3, "right": 3, "jumpleft": -3, "jumpright": 3}.get(a, 0)
        dy = {"jump": -3, "jumpleft": -3, "jumpright": -3}.get(a, 0)
        self._ox = int(np.clip(self._ox + dx, 40, self.W * 7)); self._oy = int(np.clip(self._oy + dy, 4, self.H - 8)); self._t += 1
        if dy == 0 and self._oy < 30: self._oy += 3      # gravity
        cam = self._ox - 40
        f = self._w[:, cam:cam + self.W].copy(); f[self._oy:self._oy + 4, 40:44] = 7
        if self._t % 150 in (0, 1, 2, 3): f[:] = 0
        return f

    def run(self, minutes: float):
        end = time.time() + minutes * 60
        self.say(f"start world={self.world} fps={self.fps} grid={self.H}x{self.W}")
        try:
            while time.time() < end and not os.path.exists(os.path.join(self.root, "STOP")):
                self.step()
        finally:
            self.hand.release_all()
            if self.n_act >= 5:
                self.deposit("stopped")
                if getattr(self, "_digesting", None) is not None: self._digesting.join(timeout=300)
            self.say("stopped"); self.narr.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="limbo"); ap.add_argument("--title", default="LIMBO")
    ap.add_argument("--root", default=HERE); ap.add_argument("--fps", type=float, default=8)
    ap.add_argument("--minutes", type=float, default=20); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--sound", action="store_true")
    ap.add_argument("--hands-off", action="store_true", help="spore observe/practice: watch the human play, never press")
    a = ap.parse_args()
    Player(a.world, a.title, a.root, fps=a.fps, dry=a.dry, sound=a.sound, hands_off=a.hands_off).run(a.minutes)
