"""Global hotkeys. Space and Esc are swallowed only while they belong to the app."""

from __future__ import annotations

import ctypes
import os
import queue
import threading
from ctypes import wintypes

from idle_lab import win32_api

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
VK_SPACE = 0x20
VK_ESCAPE = 0x1B
VK_F6 = 0x75
VK_F7 = 0x76
LLKHF_UP = 0x80


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HookFlags:
    """Booleans the UI thread sets and the hook thread reads."""

    def __init__(self) -> None:
        self.anchor_armed = False
        self.recording = False
        self.playback = False
        self.screenshot_mode = False
        self.title_dialog_open = False
        self.our_pid = os.getpid()


class InputHooks:
    def __init__(self) -> None:
        self.state = HookFlags()
        self.events: queue.Queue = queue.Queue()
        self._ready = threading.Event()
        self._running = False
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._kb_hook = None
        self._mouse_hook = None
        self._kb_proc = None
        self._mouse_proc = None
        self._space_down = False
        self._esc_down = False
        self._f6_down = False
        self._f7_down = False
        self._swallow_up = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="input-hooks", daemon=True)
        self._thread.start()
        if not self._ready.wait(2):
            raise OSError("The hotkey hook did not start.")
        if not self._kb_hook or not self._mouse_hook:
            raise OSError("The hotkey hook did not install.")

    def stop(self) -> None:
        self._running = False
        if self._thread_id:
            win32_api.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(2)

    def drain(self) -> list:
        items = []
        while True:
            try:
                items.append(self.events.get_nowait())
            except queue.Empty:
                break
        return items

    def _run(self) -> None:
        self._thread_id = int(win32_api.kernel32.GetCurrentThreadId())
        self._kb_proc = win32_api.HOOKPROC(self._keyboard)
        self._mouse_proc = win32_api.HOOKPROC(self._mouse)
        module = win32_api.kernel32.GetModuleHandleW(None)
        self._kb_hook = win32_api.user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, module, 0)
        self._mouse_hook = win32_api.user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, module, 0)
        self._ready.set()
        if not self._kb_hook or not self._mouse_hook:
            if self._kb_hook:
                win32_api.user32.UnhookWindowsHookEx(self._kb_hook)
            if self._mouse_hook:
                win32_api.user32.UnhookWindowsHookEx(self._mouse_hook)
            self._kb_hook = None
            self._mouse_hook = None
            return
        message = wintypes.MSG()
        while self._running:
            result = win32_api.user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result == 0 or result == -1:
                break
            win32_api.user32.TranslateMessage(ctypes.byref(message))
            win32_api.user32.DispatchMessageW(ctypes.byref(message))
        if self._kb_hook:
            win32_api.user32.UnhookWindowsHookEx(self._kb_hook)
        if self._mouse_hook:
            win32_api.user32.UnhookWindowsHookEx(self._mouse_hook)

    def _next(self, hook, n_code, w_param, l_param):
        return win32_api.user32.CallNextHookEx(hook, n_code, w_param, l_param)

    def _keyboard(self, n_code, w_param, l_param):
        try:
            return self._keyboard_impl(n_code, w_param, l_param)
        except Exception:
            return self._next(self._kb_hook, n_code, w_param, l_param)

    def _keyboard_impl(self, n_code, w_param, l_param):
        if n_code < 0:
            return self._next(self._kb_hook, n_code, w_param, l_param)
        if w_param not in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
            return self._next(self._kb_hook, n_code, w_param, l_param)
        data = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        is_up = bool(data.flags & LLKHF_UP)
        vk = int(data.vkCode)
        swallow = False
        if vk == VK_SPACE:
            # Pass Space through while a title dialog is open so titles can include spaces.
            if self.state.title_dialog_open:
                pass
            elif self.state.recording:
                swallow = True
                if is_up:
                    self._space_down = False
                    self.events.put(("space_up",))
                elif not self._space_down:
                    self._space_down = True
                    x, y = win32_api.cursor_pos()
                    self.events.put(("space_down", x, y))
            elif self.state.screenshot_mode:
                swallow = True
                if is_up:
                    self._space_down = False
                elif not self._space_down:
                    self._space_down = True
                    self.events.put(("screen_map_space",))
        elif vk == VK_ESCAPE:
            # Pass Esc through while a title dialog is open so the dialog can cancel first.
            if self.state.title_dialog_open:
                pass
            else:
                armed = (
                    self.state.anchor_armed
                    or self.state.recording
                    or self.state.playback
                    or self.state.screenshot_mode
                )
                if is_up:
                    self._esc_down = False
                elif armed and not self._esc_down:
                    self._esc_down = True
                    swallow = True
                    self.events.put(("escape",))
                elif armed:
                    swallow = True
        elif vk == VK_F6:
            swallow = True
            if is_up:
                self._f6_down = False
            elif not self._f6_down:
                self._f6_down = True
                self.events.put(("f6",))
        elif vk == VK_F7:
            swallow = True
            if is_up:
                self._f7_down = False
            elif not self._f7_down:
                self._f7_down = True
                self.events.put(("f7",))
        if swallow:
            return 1
        return self._next(self._kb_hook, n_code, w_param, l_param)

    def _mouse(self, n_code, w_param, l_param):
        try:
            return self._mouse_impl(n_code, w_param, l_param)
        except Exception:
            return self._next(self._mouse_hook, n_code, w_param, l_param)

    def _mouse_impl(self, n_code, w_param, l_param):
        if n_code < 0:
            return self._next(self._mouse_hook, n_code, w_param, l_param)
        if self._swallow_up and w_param == WM_LBUTTONUP:
            self._swallow_up = False
            return 1
        if w_param == WM_LBUTTONDOWN and self.state.anchor_armed:
            data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            x, y = int(data.pt.x), int(data.pt.y)
            hwnd = win32_api.root_window_at(x, y)
            if hwnd and win32_api.pid_of(hwnd) == self.state.our_pid:
                title = win32_api.get_window_text(hwnd)
                if title != "Click logger":
                    return self._next(self._mouse_hook, n_code, w_param, l_param)
            self.state.anchor_armed = False
            self._swallow_up = True
            self.events.put(("anchor_click", x, y, hwnd))
            return 1
        return self._next(self._mouse_hook, n_code, w_param, l_param)
