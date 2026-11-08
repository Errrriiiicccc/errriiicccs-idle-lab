"""Windows notification-area (system tray) presence for Idle Lab.

Uses Shell_NotifyIcon directly (ctypes). pystray on this machine can toast
without ever showing a tray glyph — native NIM_ADD is what we need.
"""

from __future__ import annotations

import atexit
import ctypes
import os
import tempfile
import threading
import time
import traceback
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_USER = 0x0400
WM_TRAY = WM_USER + 42
WM_APP_STOP = WM_USER + 43

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040

CW_USEDEFAULT = 0x80000000
WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
SW_HIDE = 0

ID_OPEN_LAB = 1001
ID_SHOW_DECK = 1002
ID_QUIT = 1003


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersionOrTimeout", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_ubyte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.RegisterClassExW.restype = wintypes.ATOM
user32.LoadImageW.restype = wintypes.HANDLE
user32.DestroyIcon.argtypes = [wintypes.HICON]
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.LPVOID,
]
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


def make_tray_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (20, 26, 34, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((4, 4, size - 5, size - 5), radius=12, fill=(30, 40, 52, 255))
    cx = cy = size // 2
    r = 16
    draw.polygon(
        [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
        fill=(127, 212, 240, 255),
    )
    return img


def _write_tray_ico() -> Path:
    path = Path(tempfile.gettempdir()) / "idle_lab_tray_icon.ico"
    img = make_tray_image()
    # Multi-size ICO for crisp tray glyphs.
    img.save(
        path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )
    return path


class TrayController:
    """Native Shell_NotifyIcon tray presence."""

    def __init__(
        self,
        *,
        schedule: Callable[[Callable[[], None]], None],
        on_open_lab: Callable[[], None],
        on_show_deck: Callable[[], None],
        on_quit: Callable[[], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._schedule = schedule
        self._on_open_lab = on_open_lab
        self._on_show_deck = on_show_deck
        self._on_quit = on_quit
        self._on_error = on_error
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._hwnd: int = 0
        self._hicon: int = 0
        self._started = False
        self._wndproc_ref: Any = None
        self._class_atom = 0
        self._ico_path: Path | None = None
        self._last_error: str | None = None

    @property
    def active(self) -> bool:
        return bool(self._started and self._hwnd)

    def start(self) -> str | None:
        if self._started:
            return None
        self._started = True
        self._ready.clear()
        self._thread = threading.Thread(target=self._thread_main, name="idle-lab-tray", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            self._started = False
            err = self._last_error or "Tray thread failed to become ready."
            return err
        if self._last_error:
            return self._last_error
        atexit.register(self.stop)
        return None

    def stop(self) -> None:
        hwnd = self._hwnd
        self._started = False
        if hwnd:
            try:
                user32.PostMessageW(hwnd, WM_APP_STOP, 0, 0)
            except Exception:
                pass
        thread = self._thread
        if thread and thread.is_alive() and thread.ident != threading.get_ident():
            thread.join(timeout=2.0)
        self._thread = None
        self._hwnd = 0

    def _report_error(self, message: str) -> None:
        self._last_error = message
        if self._on_error is None:
            return
        try:
            self._schedule(lambda: self._on_error(message))
        except Exception:
            traceback.print_exc()

    def _thread_main(self) -> None:
        try:
            self._run_message_loop()
        except Exception as exc:
            self._report_error(f"Tray crashed: {exc}")
            self._ready.set()

    def _run_message_loop(self) -> None:
        # Helps Windows 11 associate tray identity with this process.
        try:
            shell32.SetCurrentProcessExplicitAppUserModelID("Errriiiccc.IdleLab")
        except Exception:
            pass

        class_name = f"IdleLabTrayHidden_{os.getpid()}"
        controller = self

        @WNDPROC
        def wnd_proc(hwnd, msg, wparam, lparam):  # type: ignore[no-untyped-def]
            if msg == WM_TRAY:
                if lparam in (WM_LBUTTONUP,):
                    controller._schedule(controller._on_open_lab)
                elif lparam in (WM_RBUTTONUP,):
                    controller._popup_menu(hwnd)
                return 0
            if msg == WM_COMMAND:
                cmd = int(wparam) & 0xFFFF
                if cmd == ID_OPEN_LAB:
                    controller._schedule(controller._on_open_lab)
                elif cmd == ID_SHOW_DECK:
                    controller._schedule(controller._on_show_deck)
                elif cmd == ID_QUIT:
                    controller._schedule(controller._on_quit)
                return 0
            if msg == WM_APP_STOP:
                controller._delete_icon(hwnd)
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                controller._delete_icon(hwnd)
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        # Keep reference so ctypes doesn't GC the callback.
        self._wndproc_ref = wnd_proc
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = wnd_proc
        wc.hInstance = hinst
        wc.lpszClassName = class_name
        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not atom:
            # Already registered in this process — fine.
            atom = 1
        self._class_atom = int(atom)

        # Real top-level tool window (hidden). HWND_MESSAGE often fails to
        # surface a visible tray glyph on Windows 11 even when NIM_ADD succeeds.
        hwnd = user32.CreateWindowExW(
            WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            class_name,
            "Idle Lab Tray",
            WS_POPUP,
            -32000,
            -32000,
            1,
            1,
            None,
            None,
            hinst,
            None,
        )
        if not hwnd:
            self._last_error = f"CreateWindowEx failed ({ctypes.get_last_error()})"
            self._ready.set()
            return
        self._hwnd = int(hwnd)
        user32.ShowWindow(hwnd, SW_HIDE)

        try:
            self._ico_path = _write_tray_ico()
            handle = user32.LoadImageW(
                None,
                str(self._ico_path),
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            self._hicon = int(handle or 0)
        except Exception as exc:
            self._hicon = 0
            self._last_error = f"Tray icon load failed: {exc}"

        if not self._hicon:
            # MAKEINTRESOURCE(IDI_APPLICATION)
            self._hicon = int(
                user32.LoadIconW(None, ctypes.cast(IDI_APPLICATION, wintypes.LPCWSTR)) or 0
            )

        if not self._add_icon(hwnd):
            err = ctypes.get_last_error()
            self._last_error = f"Shell_NotifyIcon ADD failed ({err})"
            self._ready.set()
            user32.DestroyWindow(hwnd)
            return

        # Balloon so the new icon is findable under overflow.
        self._balloon(hwnd, "Idle Lab is running — click to open Lab.")
        self._ready.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        self._hwnd = 0

    def _nid(self, hwnd: int, *, flags: int) -> NOTIFYICONDATAW:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = flags
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = self._hicon
        tip = "Idle Lab"
        nid.szTip = tip
        return nid

    def _add_icon(self, hwnd: int) -> bool:
        nid = self._nid(hwnd, flags=NIF_MESSAGE | NIF_ICON | NIF_TIP)
        if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
            return True
        # Explorer may not be ready — retry a couple times.
        for _ in range(5):
            time.sleep(0.2)
            if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
                return True
        return False

    def _delete_icon(self, hwnd: int) -> None:
        try:
            nid = self._nid(hwnd, flags=0)
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        except Exception:
            pass
        if self._hicon:
            try:
                user32.DestroyIcon(self._hicon)
            except Exception:
                pass
            self._hicon = 0

    def _balloon(self, hwnd: int, text: str) -> None:
        nid = self._nid(hwnd, flags=NIF_INFO | NIF_ICON | NIF_TIP | NIF_MESSAGE)
        nid.szInfo = text[:255]
        nid.szInfoTitle = "Idle Lab"
        nid.dwInfoFlags = NIIF_INFO
        nid.uVersionOrTimeout = 4
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def _popup_menu(self, hwnd: int) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN_LAB, "Open Lab")
        user32.AppendMenuW(menu, MF_STRING, ID_SHOW_DECK, "Show Flight Deck")
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT, "Quit Idle Lab")
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        cmd = user32.TrackPopupMenu(
            menu,
            TPM_RETURNCMD | TPM_RIGHTBUTTON,
            int(pt.x),
            int(pt.y),
            0,
            hwnd,
            None,
        )
        user32.DestroyMenu(menu)
        if cmd:
            user32.PostMessageW(hwnd, WM_COMMAND, int(cmd), 0)
