#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rawmouse.py — physical mouse motion via Raw Input (WM_INPUT).

Fullscreen shooters lock and recenter the cursor, so GetCursorPos shows nothing while the
player is aiming — exactly the games where the mouse IS the hand. Raw Input reports the
device's own motion regardless of cursor lock. A hidden message-only window registers for
mouse raw input with RIDEV_INPUTSINK (delivered even when unfocused) and a daemon thread
pumps messages; delta() returns the accumulated (dx, dy) since the last call.

Falls back cleanly: if registration fails (non-Windows, no session), ok stays False and the
caller keeps using cursor deltas.
"""
from __future__ import annotations
import ctypes, os, threading
from typing import Tuple

WM_INPUT = 0x00FF
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100
HWND_MESSAGE = -3
MOUSE_MOVE_ABSOLUTE = 0x0001


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", ctypes.c_uint32), ("dwSize", ctypes.c_uint32),
                ("hDevice", ctypes.c_void_p), ("wParam", ctypes.c_void_p)]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [("usFlags", ctypes.c_uint16), ("ulButtons", ctypes.c_uint32),
                ("ulRawButtons", ctypes.c_uint32), ("lLastX", ctypes.c_int32),
                ("lLastY", ctypes.c_int32), ("ulExtraInformation", ctypes.c_uint32)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", ctypes.c_uint16), ("usUsage", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32), ("hwndTarget", ctypes.c_void_p)]


class RawMouse:
    def __init__(self):
        self.ok = False; self.err = ""
        self._dx = 0; self._dy = 0; self._events = 0
        self._lock = threading.Lock()
        if os.name == "nt":
            threading.Thread(target=self._pump, daemon=True).start()

    def delta(self) -> Tuple[int, int]:
        with self._lock:
            d = (self._dx, self._dy); self._dx = 0; self._dy = 0
        return d

    def _pump(self):
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.CreateWindowExW.restype = ctypes.c_void_p
            user32.CreateWindowExW.argtypes = [ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                               ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                               ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                               ctypes.c_void_p, ctypes.c_void_p]
            user32.DefWindowProcW.restype = ctypes.c_ssize_t
            user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_ssize_t]
            user32.RegisterClassW.restype = ctypes.c_uint16
            user32.GetRawInputData.argtypes = [ctypes.c_ssize_t, ctypes.c_uint, ctypes.c_void_p,
                                               ctypes.POINTER(ctypes.c_uint), ctypes.c_uint]
            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                                         ctypes.c_ssize_t, ctypes.c_ssize_t)

            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_INPUT:
                    size = ctypes.c_uint(0)
                    user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size),
                                           ctypes.sizeof(RAWINPUTHEADER))
                    if 0 < size.value <= 1024:
                        buf = ctypes.create_string_buffer(size.value)
                        got = user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size),
                                                     ctypes.sizeof(RAWINPUTHEADER))
                        if got == size.value:
                            ri = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
                            if ri.header.dwType == 0 and not (ri.mouse.usFlags & MOUSE_MOVE_ABSOLUTE):
                                with self._lock:
                                    self._dx += ri.mouse.lLastX; self._dy += ri.mouse.lLastY
                                    self._events += 1
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            self._proc = WNDPROC(wndproc)                    # keep a reference (GC!)

            class WNDCLASSW(ctypes.Structure):
                _fields_ = [("style", ctypes.c_uint), ("lpfnWndProc", WNDPROC),
                            ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                            ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
                            ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                            ("lpszMenuName", ctypes.c_wchar_p), ("lpszClassName", ctypes.c_wchar_p)]

            wc = WNDCLASSW()
            wc.lpfnWndProc = self._proc
            wc.lpszClassName = "PlanetRawMouse"
            kernel32.GetModuleHandleW.restype = ctypes.c_void_p
            wc.hInstance = kernel32.GetModuleHandleW(None)
            atom = user32.RegisterClassW(ctypes.byref(wc))
            if not atom:
                self.err = f"RegisterClassW: {kernel32.GetLastError()}"; return
            hwnd = user32.CreateWindowExW(0, "PlanetRawMouse", None, 0, 0, 0, 0, 0,
                                          ctypes.c_void_p(HWND_MESSAGE & 0xFFFFFFFFFFFFFFFF), None,
                                          wc.hInstance, None)
            if not hwnd:
                self.err = f"CreateWindowExW: {kernel32.GetLastError()}"; return
            rid = RAWINPUTDEVICE(1, 2, RIDEV_INPUTSINK, hwnd)     # usage page 1 (generic), usage 2 (mouse)
            if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE)):
                self.err = f"RegisterRawInputDevices: {kernel32.GetLastError()}"; return
            self.ok = True
            msg = ctypes.create_string_buffer(48)                  # MSG struct
            while user32.GetMessageW(msg, None, 0, 0) > 0:
                user32.TranslateMessage(msg); user32.DispatchMessageW(msg)
        except Exception:
            self.ok = False


if __name__ == "__main__":
    import time
    rm = RawMouse(); time.sleep(1.0)
    print("raw input registered:", rm.ok, rm.err)
    for _ in range(5):
        time.sleep(1.0); print("delta", rm.delta(), "events", rm._events)
