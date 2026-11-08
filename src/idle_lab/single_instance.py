"""Ensure only one Idle Lab GUI process runs at a time (Windows)."""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable
from ctypes import wintypes
from typing import Any

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
INFINITE = 0xFFFFFFFF

MUTEX_NAME = "Local\\ErrriiicccIdleLab.Single"
EVENT_NAME = "Local\\ErrriiicccIdleLab.Wake"

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.SetEvent.argtypes = [wintypes.HANDLE]
kernel32.SetEvent.restype = wintypes.BOOL
kernel32.ResetEvent.argtypes = [wintypes.HANDLE]
kernel32.ResetEvent.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.WaitForMultipleObjects.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.BOOL,
    wintypes.DWORD,
]
kernel32.WaitForMultipleObjects.restype = wintypes.DWORD
kernel32.SetLastError.argtypes = [wintypes.DWORD]

user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]

SW_RESTORE = 9

_mutex: Any = None
_wake_event: Any = None
_watcher_stop: Any = None
_watcher_thread: threading.Thread | None = None


def try_acquire() -> bool:
    """Return True if this process owns the single-instance lock."""

    global _mutex, _wake_event
    if _mutex:
        return True
    _wake_event = kernel32.CreateEventW(None, True, False, EVENT_NAME)
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return True  # fail open — don't block launch on mutex errors
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        # Opened someone else's mutex — drop this handle and wake them.
        kernel32.CloseHandle(handle)
        _signal_wake()
        _nudge_existing_windows()
        return False
    _mutex = handle
    return True


def release() -> None:
    """Drop the lock (Restart must call this before spawning a successor)."""

    global _mutex, _wake_event, _watcher_stop, _watcher_thread
    stop_wake_watcher()
    if _mutex:
        try:
            kernel32.ReleaseMutex(_mutex)
        except Exception:
            pass
        try:
            kernel32.CloseHandle(_mutex)
        except Exception:
            pass
        _mutex = None
    if _wake_event:
        try:
            kernel32.CloseHandle(_wake_event)
        except Exception:
            pass
        _wake_event = None


def start_wake_watcher(schedule: Callable[[Callable[[], None]], None], on_wake: Callable[[], None]) -> None:
    """Background wait on the wake event; marshals ``on_wake`` onto the UI thread."""

    global _watcher_stop, _watcher_thread, _wake_event
    if _wake_event is None:
        _wake_event = kernel32.CreateEventW(None, True, False, EVENT_NAME)
    if _watcher_thread and _watcher_thread.is_alive():
        return
    _watcher_stop = kernel32.CreateEventW(None, True, False, None)

    def loop() -> None:
        handles = (wintypes.HANDLE * 2)(_wake_event, _watcher_stop)
        while True:
            result = kernel32.WaitForMultipleObjects(2, handles, False, INFINITE)
            if result == WAIT_OBJECT_0 + 1:
                return
            if result == WAIT_OBJECT_0:
                try:
                    kernel32.ResetEvent(_wake_event)
                except Exception:
                    pass
                try:
                    schedule(on_wake)
                except Exception:
                    pass

    _watcher_thread = threading.Thread(target=loop, name="idle-lab-wake", daemon=True)
    _watcher_thread.start()


def stop_wake_watcher() -> None:
    global _watcher_stop, _watcher_thread
    if _watcher_stop:
        try:
            kernel32.SetEvent(_watcher_stop)
        except Exception:
            pass
    thread = _watcher_thread
    if thread and thread.is_alive() and thread.ident != threading.get_ident():
        thread.join(timeout=1.5)
    _watcher_thread = None
    if _watcher_stop:
        try:
            kernel32.CloseHandle(_watcher_stop)
        except Exception:
            pass
        _watcher_stop = None


def _signal_wake() -> None:
    event = kernel32.CreateEventW(None, True, False, EVENT_NAME)
    if event:
        kernel32.SetEvent(event)
        kernel32.CloseHandle(event)


def _nudge_existing_windows() -> None:
    """Best-effort restore of any visible Idle Lab HWND (wake handler does the real show)."""

    titles = ("Errriiiccc's Idle Lab", "Idle Lab · Flight deck", "Idle Lab Tray")
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _lparam):  # type: ignore[no-untyped-def]
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value.strip()
        if title in titles:
            found.append(int(hwnd))
        return True

    user32.EnumWindows(_cb, 0)
    for hwnd in found:
        try:
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
