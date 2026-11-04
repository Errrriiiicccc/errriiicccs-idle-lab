"""A window that records clicks so foreground and background can be compared.

Also paints large WAVE / SIGNAL labels for Automations OCR harness demos.
Click the SIGNAL band to toggle A ↔ B.
"""

from __future__ import annotations

import ctypes
import tkinter as tk

from idle_lab.models import normalized_to_screen
from idle_lab import win32_api

TARGETS = (
    (0.25, 0.25, "upper"),
    (0.50, 0.50, "middle"),
    (0.75, 0.75, "lower"),
)
WM_LBUTTONDOWN = 0x0201


class ClickLogger:
    def __init__(self, root: tk.Misc) -> None:
        self.win = tk.Toplevel(root)
        self.win.title("Click logger")
        self.win.geometry("440x520")
        self.win.configure(bg="#161616")
        self.signal = "A"
        self.wave = 42
        self.canvas = tk.Canvas(
            self.win,
            width=440,
            height=420,
            bg="#1b1b1b",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.readout = tk.Label(
            self.win,
            text="Anchor this window. Click SIGNAL to toggle A/B for OCR demos.",
            bg="#161616",
            fg="#c8c8c8",
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.readout.pack(fill="x", padx=8, pady=8)
        self.canvas.bind("<Button-1>", self._on_tk_click)
        self._procs: list = []
        self._old_procs: list[tuple[int, int]] = []
        self.win.after(150, self._install_hooks)
        self.win.bind("<Configure>", lambda _event: self.redraw())
        self.win.after(200, self.redraw)

    def lift_window(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def redraw(self) -> None:
        if not self.win.winfo_exists():
            return
        self.canvas.delete("all")
        hwnd = win32_api.widget_hwnd(self.win)
        rect = win32_api.get_window_rect(hwnd)
        if rect is None:
            return
        origin_x = self.canvas.winfo_rootx()
        origin_y = self.canvas.winfo_rooty()
        for nx, ny, label in TARGETS:
            screen_x, screen_y = normalized_to_screen(rect, nx, ny)
            x = screen_x - origin_x
            y = screen_y - origin_y
            self.canvas.create_oval(x - 16, y - 16, x + 16, y + 16, outline="#3CE6FF", width=2, tags="target")
            self.canvas.create_text(x, y, text=label, fill="#d7f7ff", font=("Segoe UI", 9), tags="target")

        # OCR harness bands in window-normalized space (see automations/rois/).
        wave_x, wave_y = normalized_to_screen(rect, 0.50, 0.88)
        signal_x, signal_y = normalized_to_screen(rect, 0.50, 0.96)
        wx, wy = wave_x - origin_x, wave_y - origin_y
        sx, sy = signal_x - origin_x, signal_y - origin_y
        self.canvas.create_rectangle(wx - 90, wy - 22, wx + 90, wy + 22, fill="#101820", outline="#8EE0C2", width=2, tags="ocr")
        self.canvas.create_text(wx, wy, text=f"WAVE {self.wave}", fill="#8EE0C2", font=("Consolas", 18, "bold"), tags="ocr")
        self.canvas.create_rectangle(sx - 90, sy - 22, sx + 90, sy + 22, fill="#201010", outline="#E7C36A", width=2, tags="ocr")
        self.canvas.create_text(sx, sy, text=f"SIGNAL {self.signal}", fill="#E7C36A", font=("Consolas", 18, "bold"), tags="ocr")

    def _note(self, text: str) -> None:
        self.readout.configure(text=text)

    def _on_tk_click(self, event) -> None:
        hwnd = win32_api.widget_hwnd(self.win)
        rect = win32_api.get_window_rect(hwnd)
        if rect is not None:
            _, signal_y = normalized_to_screen(rect, 0.50, 0.96)
            if abs(event.y_root - signal_y) <= 28:
                self.signal = "B" if self.signal == "A" else "A"
                self.redraw()
                self._note(f"SIGNAL toggled to {self.signal}.")
                return
            _, wave_y = normalized_to_screen(rect, 0.50, 0.88)
            if abs(event.y_root - wave_y) <= 28:
                self.wave = 1 if self.wave >= 99 else self.wave + 1
                self.redraw()
                self._note(f"WAVE set to {self.wave}.")
                return
        self._mark_hit(event.x_root, event.y_root, "real click")

    def _mark_hit(self, screen_x: int, screen_y: int, source: str) -> None:
        hwnd = win32_api.widget_hwnd(self.win)
        rect = win32_api.get_window_rect(hwnd)
        if rect is None:
            return
        nearest = None
        nearest_distance = 10**9
        for nx, ny, label in TARGETS:
            target_x, target_y = normalized_to_screen(rect, nx, ny)
            distance = abs(target_x - screen_x) + abs(target_y - screen_y)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = label
        if nearest is not None and nearest_distance <= 28:
            self._note(f"Hit {nearest} ({source}).")
        else:
            self._note(f"Click at screen {screen_x}, {screen_y} ({source}).")

    def _install_hooks(self) -> None:
        if not self.win.winfo_exists():
            return
        hwnds = {int(self.canvas.winfo_id()), win32_api.widget_hwnd(self.win)}
        for hwnd in hwnds:
            if not hwnd:
                continue
            old = win32_api.user32.GetWindowLongPtrW(hwnd, -4)
            proc = win32_api.WNDPROC(self._wndproc)
            self._procs.append(proc)
            self._old_procs.append((hwnd, int(old)))
            address = ctypes.cast(proc, ctypes.c_void_p).value
            win32_api.user32.SetWindowLongPtrW(hwnd, -4, address or 0)

    def _wndproc(self, hwnd, msg, w_param, l_param):
        if msg == WM_LBUTTONDOWN:
            x = int(l_param) & 0xFFFF
            y = (int(l_param) >> 16) & 0xFFFF
            if x >= 0x8000:
                x -= 0x10000
            if y >= 0x8000:
                y -= 0x10000
            screen_x, screen_y = win32_api.client_to_screen(int(hwnd), x, y)
            self.win.after(0, lambda: self._mark_hit(screen_x, screen_y, "window message"))
        old = 0
        for hooked, proc in self._old_procs:
            if hooked == int(hwnd):
                old = proc
                break
        if old:
            return win32_api.user32.CallWindowProcW(old, hwnd, msg, w_param, l_param)
        return 0
