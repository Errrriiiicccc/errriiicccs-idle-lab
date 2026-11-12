"""Small Win32 helpers. This module is Windows-only."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from idle_lab.models import Rect

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t

GA_PARENT = 1
GA_ROOT = 2
GW_OWNER = 4
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8
HWND_TOPMOST = -1
SW_SHOW = 5
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020

WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
OVERLAY_EXSTYLE = (
    WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
)

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
WHEEL_DELTA = 120
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002
CWP_SKIPTRANSPARENT = 0x0004

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ChildWindowFromPointEx.argtypes = [wintypes.HWND, wintypes.POINT, wintypes.UINT]
user32.ChildWindowFromPointEx.restype = wintypes.HWND
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.mouse_event.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ULONG_PTR,
]
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.CallWindowProcW.argtypes = [
    ctypes.c_ssize_t,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallWindowProcW.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostThreadMessageW.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


def set_dpi_aware() -> None:
    """Match cursor pixels to window pixels on a per-monitor desktop."""

    if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
        return
    try:
        ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
    except (OSError, AttributeError):
        user32.SetProcessDPIAware()


def virtual_screen() -> Rect:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return Rect(left, top, left + width, top + height)


def cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return int(point.x), int(point.y)


def set_cursor_pos(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))


def window_from_point(x: int, y: int) -> int:
    hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    return int(hwnd or 0)


def root_window_at(x: int, y: int) -> int:
    hwnd = window_from_point(x, y)
    if not hwnd:
        return 0
    root = user32.GetAncestor(hwnd, GA_ROOT)
    return int(root or hwnd)


def pid_of(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def is_window(hwnd: int) -> bool:
    return bool(hwnd and user32.IsWindow(hwnd))


def is_iconic(hwnd: int) -> bool:
    return bool(hwnd and user32.IsIconic(hwnd))


def is_window_visible(hwnd: int) -> bool:
    return bool(hwnd and user32.IsWindowVisible(hwnd))


_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def iter_top_level_windows() -> list[tuple[int, str, int, bool, bool]]:
    """Return ``(hwnd, title, pid, visible, minimized)`` for top-level windows."""

    from idle_lab.window_find import WindowCandidate  # local import keeps models light

    found: list[WindowCandidate] = []

    def _callback(hwnd, _lparam):  # type: ignore[no-untyped-def]
        hwnd_i = int(hwnd or 0)
        if not hwnd_i:
            return True
        # Top-level: no owner.
        owner = int(user32.GetWindow(hwnd_i, GW_OWNER) or 0)
        if owner:
            return True
        title = get_window_text(hwnd_i)
        if not title:
            return True
        found.append(
            WindowCandidate(
                hwnd=hwnd_i,
                title=title,
                pid=pid_of(hwnd_i),
                visible=is_window_visible(hwnd_i),
                minimized=is_iconic(hwnd_i),
            )
        )
        return True

    cb = _EnumWindowsProc(_callback)
    user32.EnumWindows(cb, 0)
    return [(c.hwnd, c.title, c.pid, c.visible, c.minimized) for c in found]


def find_window_by_title(title: str, *, our_pid: int | None = None) -> int | None:
    """Exact title match among top-level windows; None if missing or ambiguous."""

    import os

    from idle_lab.window_find import WindowCandidate, pick_window_by_title

    pid = int(our_pid if our_pid is not None else os.getpid())
    candidates = [
        WindowCandidate(hwnd=h, title=t, pid=p, visible=v, minimized=m)
        for h, t, p, v, m in iter_top_level_windows()
    ]
    return pick_window_by_title(candidates, title, our_pid=pid)


def get_window_text(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value.strip()


def get_window_rect(hwnd: int) -> Rect | None:
    raw = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(raw)):
        return None
    return Rect(int(raw.left), int(raw.top), int(raw.right), int(raw.bottom))


def widget_hwnd(widget) -> int:
    """Win32 HWND for a Tk widget's top-level frame — never its owner.

    GetParent() on an owned top-level returns the owner; that used to make
    style/orphan calls hit Lab instead of the flight deck. GA_ROOT follows
    the real parent chain only.
    """

    hwnd = int(widget.winfo_id())
    root = int(user32.GetAncestor(hwnd, GA_ROOT) or 0)
    if root:
        return root
    parent = int(user32.GetParent(hwnd) or 0)
    return parent or hwnd


def window_owner(hwnd: int) -> int:
    if not hwnd:
        return 0
    return int(user32.GetWindow(hwnd, GW_OWNER) or 0)


def show_window(hwnd: int) -> None:
    if hwnd and is_window(hwnd):
        user32.ShowWindow(hwnd, SW_SHOW)


def clear_window_owner(hwnd: int) -> None:
    """Clear Win32 owner so a Toplevel is not hidden/minimized with its Tk master.

    Tk on Windows sets GWLP_HWNDPARENT to the master; owned windows disappear when
    the owner is shown/lifted/alpha-toggled. Orphaning keeps the flight deck alive.
    """

    if not hwnd or not is_window(hwnd):
        return
    if window_owner(hwnd):
        user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, 0)
    user32.SetWindowPos(
        hwnd,
        ctypes.c_void_p(HWND_TOPMOST),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )
    show_window(hwnd)


def add_exstyle(hwnd: int, extra: int) -> None:
    style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | extra)


def raise_topmost(hwnd: int) -> None:
    user32.SetWindowPos(
        hwnd,
        ctypes.c_void_p(HWND_TOPMOST),
        0,
        0,
        0,
        0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def focus_window(hwnd: int) -> bool:
    if not is_window(hwnd):
        return False
    if int(user32.GetForegroundWindow() or 0) == int(hwnd):
        return True
    foreground = int(user32.GetForegroundWindow() or 0)
    our_thread = int(kernel32.GetCurrentThreadId())
    foreground_thread = int(user32.GetWindowThreadProcessId(foreground, None)) if foreground else 0
    target_thread = int(user32.GetWindowThreadProcessId(hwnd, None))
    attached_foreground = False
    attached_target = False
    try:
        if foreground_thread and foreground_thread != our_thread:
            attached_foreground = bool(user32.AttachThreadInput(our_thread, foreground_thread, True))
        if target_thread and target_thread != our_thread:
            attached_target = bool(user32.AttachThreadInput(our_thread, target_thread, True))
        user32.ShowWindow(hwnd, SW_SHOW)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        if attached_target:
            user32.AttachThreadInput(our_thread, target_thread, False)
        if attached_foreground:
            user32.AttachThreadInput(our_thread, foreground_thread, False)
    return int(user32.GetForegroundWindow() or 0) == int(hwnd)


def screen_to_client(hwnd: int, x: int, y: int) -> tuple[int, int]:
    point = wintypes.POINT(int(x), int(y))
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    return int(point.x), int(point.y)


def client_to_screen(hwnd: int, x: int, y: int) -> tuple[int, int]:
    point = wintypes.POINT(int(x), int(y))
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return int(point.x), int(point.y)


def child_at_screen_point(anchor_hwnd: int, x: int, y: int) -> tuple[int, int, int]:
    """Deepest child of the anchor under a screen point, plus that child's client coords."""

    current = int(anchor_hwnd)
    client_x, client_y = screen_to_client(current, x, y)
    for _ in range(16):
        child = user32.ChildWindowFromPointEx(
            current,
            wintypes.POINT(int(client_x), int(client_y)),
            CWP_SKIPINVISIBLE | CWP_SKIPDISABLED | CWP_SKIPTRANSPARENT,
        )
        child = int(child or 0)
        if not child or child == current:
            break
        screen_x, screen_y = client_to_screen(current, client_x, client_y)
        client_x, client_y = screen_to_client(child, screen_x, screen_y)
        current = child
    return current, client_x, client_y


def make_lparam(x: int, y: int) -> int:
    return (int(x) & 0xFFFF) | ((int(y) & 0xFFFF) << 16)


def post_left_click(hwnd: int, client_x: int, client_y: int, *, down: bool) -> None:
    message = WM_LBUTTONDOWN if down else WM_LBUTTONUP
    button = MK_LBUTTON if down else 0
    user32.PostMessageW(hwnd, message, button, make_lparam(client_x, client_y))


def send_left_button(down: bool) -> None:
    flags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    if ctypes.sizeof(INPUT) not in (28, 40):
        user32.mouse_event(flags, 0, 0, 0, 0)
        return
    event = INPUT()
    event.type = INPUT_MOUSE
    event.union.mi.dwFlags = flags
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        user32.mouse_event(flags, 0, 0, 0, 0)


def send_mouse_wheel(notches: int) -> None:
    """Scroll the wheel at the current cursor. Positive = away/up, negative = toward/down."""

    notches = int(notches)
    if notches == 0:
        return
    data = notches * WHEEL_DELTA
    if ctypes.sizeof(INPUT) not in (28, 40):
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, data & 0xFFFFFFFF, 0)
        return
    event = INPUT()
    event.type = INPUT_MOUSE
    event.union.mi.dwFlags = MOUSEEVENTF_WHEEL
    event.union.mi.mouseData = data & 0xFFFFFFFF
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, data & 0xFFFFFFFF, 0)


def _vk_for_token(token: str) -> int | None:
    """Map a simple key token to a virtual-key code (letters, digits, common names)."""

    raw = str(token or "").strip()
    if not raw:
        return None
    named = {
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "space": 0x20,
        "tab": 0x09,
        "backspace": 0x08,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
    }
    lower = raw.lower()
    if lower in named:
        return named[lower]
    if len(raw) == 1:
        ch = raw.upper()
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            return ord(ch)
    return None


def send_key_token(token: str) -> bool:
    """Send a single key down/up via SendInput. Returns False if token unknown."""

    vk = _vk_for_token(token)
    if vk is None:
        return False
    down = INPUT()
    down.type = INPUT_KEYBOARD
    down.union.ki.wVk = vk
    up = INPUT()
    up.type = INPUT_KEYBOARD
    up.union.ki.wVk = vk
    up.union.ki.dwFlags = KEYEVENTF_KEYUP
    sent = user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    sent += user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    return sent == 2
