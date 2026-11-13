#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
porthole.py — the planet's WINDOW: a frame you place over anything, and what shows through
it is what the planet sees.

Jonathan's design: "what if we made a browser for it? or a window. whatever is over that
window it could see — a youtube video placed over that space, or fullscreen to capture the
screen I play on. the window could also show the chat or what it's thinking in different
tabs. it could also take control in that space to play too."

The porthole is an always-on-top frame whose CENTER IS A HOLE (transparent): whatever you
put underneath shows through, and the eye captures exactly that screen rectangle. Showing it
something is a physical act — drag a video, a game, a document under the hole. The side
panel is the roof's channels in tabs: THOUGHTS (the live narration), CHAT (talk to the
planet's own chatbot), STATUS (flower, map, depth). The HAND toggle lets it act in that
space: keys go to whatever window has focus (click the thing under the hole first). The
world's name comes from the entry box, so 'youtube', 'inside', 'reading' each get their own
ocean under D:\\planet\\ocean\\.

Run:  python porthole.py  (needs the planet folder beside it; the spore ignores this window)
"""
from __future__ import annotations
import os, sys, threading, time
import tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT_OCEAN = r"D:\planet\ocean"
HOLE_COLOR = "#ff00ff"                 # transparency key — anything painted this shows through


class Porthole:
    def __init__(self):
        self.tk = tk.Tk()
        self.tk.title("Planet Porthole")
        self.tk.geometry("1060x620+120+120")
        self.tk.configure(bg="#101418")
        self.tk.attributes("-topmost", True)
        try: self.tk.wm_attributes("-transparentcolor", HOLE_COLOR)
        except Exception: pass
        self.player = None; self.thread = None; self.world = None
        self._narr_pos = 0; self._chat_busy = False; self._scene_busy = False; self._scene_t = 0.0
        self._build()
        self._tick()

    # ------------------------------------------------------------------ layout
    def _build(self):
        top = tk.Frame(self.tk, bg="#101418"); top.pack(fill="x", padx=6, pady=4)
        tk.Label(top, text="world:", fg="#9ab", bg="#101418").pack(side="left")
        self.world_var = tk.StringVar(value="porthole")
        tk.Entry(top, textvariable=self.world_var, width=16, bg="#182028", fg="#cde",
                 insertbackground="#cde").pack(side="left", padx=4)
        self.watch_btn = tk.Button(top, text="WATCH", command=self.toggle_watch, bg="#1c3a2a", fg="#9fd")
        self.watch_btn.pack(side="left", padx=4)
        self.hand_var = tk.BooleanVar(value=False)
        self.hand_btn = tk.Checkbutton(top, text="hand", variable=self.hand_var, command=self.toggle_hand,
                                       bg="#101418", fg="#d99", selectcolor="#101418", activebackground="#101418")
        self.hand_btn.pack(side="left", padx=4)
        tk.Button(top, text="fullscreen hole", command=self.fullscreen, bg="#182028", fg="#9ab").pack(side="left", padx=4)
        self.status_var = tk.StringVar(value="idle — place something under the hole and press WATCH")
        tk.Label(top, textvariable=self.status_var, fg="#7f8", bg="#101418").pack(side="left", padx=10)

        body = tk.Frame(self.tk, bg="#101418"); body.pack(fill="both", expand=True, padx=6, pady=4)
        # the hole: whatever is beneath this rectangle is what the planet sees
        self.hole = tk.Frame(body, bg=HOLE_COLOR, width=640, height=520)
        self.hole.pack(side="left", fill="both", expand=True)
        # the roof's channels, in tabs
        panel = ttk.Notebook(body); panel.pack(side="right", fill="both"); panel.configure(width=380)
        self.thoughts = tk.Text(panel, bg="#0c1014", fg="#9fb89f", width=48, wrap="word", state="disabled")
        panel.add(self.thoughts, text="thoughts")
        chat_f = tk.Frame(panel, bg="#0c1014")
        self.chat_log = tk.Text(chat_f, bg="#0c1014", fg="#9fb8c8", wrap="word", state="disabled")
        self.chat_log.pack(fill="both", expand=True)
        entry_f = tk.Frame(chat_f, bg="#0c1014"); entry_f.pack(fill="x")
        self.chat_var = tk.StringVar()
        e = tk.Entry(entry_f, textvariable=self.chat_var, bg="#182028", fg="#cde", insertbackground="#cde")
        e.pack(side="left", fill="x", expand=True); e.bind("<Return>", lambda _e: self.ask())
        tk.Button(entry_f, text="ask", command=self.ask, bg="#182028", fg="#9ab").pack(side="right")
        panel.add(chat_f, text="chat")
        self.status_txt = tk.Text(panel, bg="#0c1014", fg="#b8a88f", width=48, wrap="word", state="disabled")
        panel.add(self.status_txt, text="status")

    def hole_rect(self):
        self.tk.update_idletasks()
        x = self.hole.winfo_rootx(); y = self.hole.winfo_rooty()
        return (x, y, max(64, self.hole.winfo_width()), max(64, self.hole.winfo_height()))

    # ------------------------------------------------------------------ watching
    def toggle_watch(self):
        if self.player is None: self.start_watch()
        else: self.stop_watch()

    def start_watch(self):
        from player import Player
        import re
        world = re.sub(r"[^a-z0-9_]+", "_", self.world_var.get().lower()) or "porthole"
        wroot = os.path.join(ROOT_OCEAN, world)
        try:
            self.player = Player(world, "", wroot, fps=4, hands_off=not self.hand_var.get(),
                                 rect_fn=self.hole_rect, sound=False)
        except Exception as e:
            self.status_var.set(f"could not start: {e}"); self.player = None; return
        self.world = world
        def run():
            try: self.player.run(minutes=24 * 60)
            except Exception as e: self.status_var.set(f"player error: {e}")
        self.thread = threading.Thread(target=run, daemon=True); self.thread.start()
        self.watch_btn.configure(text="STOP", bg="#3a1c1c")
        self.status_var.set(f"watching '{world}' through the hole" + (" — HAND ON" if self.hand_var.get() else ""))
        self._narr_pos = 0

    def stop_watch(self):
        if self.player is None: return
        try:
            open(os.path.join(self.player.root, "STOP"), "w").close()
            if self.thread: self.thread.join(timeout=120)
            os.remove(os.path.join(self.player.root, "STOP"))
        except Exception: pass
        self.player = None; self.watch_btn.configure(text="WATCH", bg="#1c3a2a")
        self.status_var.set("stopped (deposited)")

    def toggle_hand(self):
        if self.player is not None:
            on = self.hand_var.get()
            self.player.hands_off = not on
            self.player.mode = "agent" if on else "human"
            if not on:
                try: self.player.hand.release_all()
                except Exception: pass
            self.status_var.set(("HAND ON — click the thing under the hole so keys reach it"
                                 if on else "hands off — watching your play"))

    def fullscreen(self):
        self.tk.geometry(f"{self.tk.winfo_screenwidth()}x{self.tk.winfo_screenheight()}+0+0")

    # ------------------------------------------------------------------ tabs
    def ask(self):
        q = self.chat_var.get().strip()
        if not q or self._chat_busy: return
        self.chat_var.set(""); self._chat_busy = True
        self._chat_append(f"you> {q}\n")
        def go():
            try:
                import chat as chatmod
                sed = getattr(self, "_sed", None)
                if sed is None: sed = self._sed = chatmod.Sediment(ROOT_OCEAN)
                models = __import__("lower").available([chatmod.DEFAULT_MODEL])
                out, _ = chatmod.answer(models[0], sed, q, []) if models else ("(Ollama is not running)", False)
            except Exception as e:
                out = f"(chat failed: {e})"
            self.tk.after(0, lambda: (self._chat_append(f"planet> {out}\n\n"), setattr(self, "_chat_busy", False)))
        threading.Thread(target=go, daemon=True).start()

    def _chat_append(self, s):
        self.chat_log.configure(state="normal"); self.chat_log.insert("end", s)
        self.chat_log.see("end"); self.chat_log.configure(state="disabled")

    def _scene(self):
        """The live voice: every ~45 s the lower ocean's seeing model looks through the hole and says,
        in one plain sentence, what it thinks it is watching. Labeled sees> — untrusted commentary,
        the legible layer over the fast loop's surprise talk."""
        if self.player is None or self._scene_busy or time.time() - self._scene_t < 45: return
        eye = getattr(self.player, "eye", None)
        raw = getattr(eye, "last_raw", None) if eye else None
        if raw is None: return
        self._scene_busy = True; self._scene_t = time.time()
        def go():
            try:
                import base64, io
                import numpy as np
                from PIL import Image
                import lower
                img = np.asarray(raw)[:, :, :3][:, :, ::-1]
                im = Image.fromarray(img)
                if im.width > 640: im = im.resize((640, int(im.height * 640 / im.width)))
                buf = io.BytesIO(); im.save(buf, format="JPEG", quality=70)
                b64 = base64.b64encode(buf.getvalue()).decode()
                # the witness: each look rides the line of the looks before it, and an antenna
                # (the standing prediction) sticks out past the newest memory
                from witness import Witness
                w = getattr(self, "_witness", None)
                if w is None or w.world != self.world:
                    w = self._witness = Witness(os.path.join(ROOT_OCEAN, self.world), self.world)
                tl = ""
                try:
                    from storyteller import truths_line
                    tl = truths_line(os.path.join(ROOT_OCEAN, self.world)) if self.world else ""
                except Exception: pass
                out = lower._ask_image("gemma3:4b", w.prompt(tl), b64, timeout=90.0, num_predict=160)
                if out:
                    obs, pred = w.absorb(out)
                    ep = w.compress(ask=lambda p: lower._ask("gemma3:4b", p, timeout=60.0, num_predict=90))
                    if ep: self.tk.after(0, lambda: self._thoughts_append(f"(the wake fades: {ep})\n"))
                    line = f"sees> {obs}\n" + (f"next> {pred}\n" if pred else "")
                    r = w.rate()
                    if r is not None and (w.antenna['fed'] + w.antenna['broken']) % 10 == 0:
                        line += f"(antenna: {int(100*r)}% of predictions fed)\n"
                    self.tk.after(0, lambda: self._thoughts_append(line))
            except Exception: pass
            finally: self._scene_busy = False
        threading.Thread(target=go, daemon=True).start()

    def _thoughts_append(self, s):
        self.thoughts.configure(state="normal"); self.thoughts.insert("end", s)
        self.thoughts.see("end"); self.thoughts.configure(state="disabled")

    def _tick(self):
        # thoughts: tail the current world's narration
        if self.player is not None and self.world:
            p = os.path.join(ROOT_OCEAN, self.world, f"narration_{self.world}.txt")
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self._narr_pos); new = f.read(); self._narr_pos = f.tell()
                if new:
                    self.thoughts.configure(state="normal"); self.thoughts.insert("end", new)
                    self.thoughts.delete("1.0", f"end-{4000}c") if float(self.thoughts.index("end-1c").split(".")[0]) > 400 else None
                    self.thoughts.see("end"); self.thoughts.configure(state="disabled")
            except Exception: pass
            # status
            try:
                pl = self.player
                lines = [f"world: {self.world}   actions: {pl.n_act}   drive: {pl.drive:.1f}",
                         f"map: {pl.wall.summary()}",
                         f"{pl.rot.summary()}", f"{pl.trans.summary()}",
                         f"flower: {dict(sorted(pl.flower.items()))}"]
                self.status_txt.configure(state="normal"); self.status_txt.delete("1.0", "end")
                self.status_txt.insert("end", "\n\n".join(lines)); self.status_txt.configure(state="disabled")
            except Exception: pass
        self._scene()
        self.tk.after(1500, self._tick)

    def run(self):
        try:
            self.tk.mainloop()
        finally:
            self.stop_watch()


if __name__ == "__main__":
    Porthole().run()
