"""Global hotkeys. Space and Esc are swallowed only while they belong to the app."""

from __future__ import annotations

import ctypes
import os
import queue
import threading
from ctypes import wintypes

from idle_lab import win32_api
from idle_lab.flight_deck.keys import DEFAULT_EXPAND_VK, menu_token_from_vk

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
VK_SPACE = 0x20
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_0 = 0x30
VK_9 = 0x39
VK_A = 0x41
VK_I = 0x49
VK_R = 0x52
VK_Z = 0x5A
LLKHF_UP = 0x80
LLMHF_INJECTED = 0x01


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
        self.screenshot_busy = False
        self.observation_active = False
        self.walkthrough_active = False
        # Live Control Overlay mode (keyboard hit-targets).
        self.live_control_active = False
        # Legacy pause flag (deck Pause removed); kept for LCO gray-out experiments.
        self.live_control_paused = False
        # Set immediately on Esc / deactivate so in-flight scrolls abort before the UI drains.
        self.live_control_cancel = threading.Event()
        # Hotkey token for the armed toggle (e.g. "A") — second press cancels on the hook thread.
        self.live_control_toggle_token: str | None = None
        # True while Loops / Missions / collection / playback / etc. can be Esc-stopped.
        self.stoppable = False
        # Flight deck activate model: inactive = only activate VK; active = shell + hotkeys.
        self.flight_deck_open = False
        self.flight_deck_active = False
        self.flight_deck_expanded = False
        self.flight_deck_anchored = False
        self.flight_deck_remap = False
        self.flight_deck_expand_vk = DEFAULT_EXPAND_VK
        # Always True so Activate works before any window is anchored.
        self.flight_deck_expand_armed = True
        self.quit_confirm = False
        self.molecule_lab_active = False
        self.molecule_lab_close_confirm = False
        self.lab_visible = True
        # Post-Deactivate resume handle — Esc opens Idle Lab while deck is inactive.
        self.resume_handle = False
        # True while Deck has abandoned menu letters (LOL / floating Lab / Settings).
        self.deck_mode_active = False
        # Atom Create is a distinct Deck mode that owns C/E/W/S/R/F.
        self.atom_create_active = False
        self.our_pid = os.getpid()


# Observation event flood control (hook thread → UI queue).
_OBS_QUEUE_SOFT = 64
_OBS_QUEUE_HARD = 200


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
        self._f8_down = False
        self._expand_down = False
        self._enter_down = False
        self._shell_key_down: set[int] = set()
        self._menu_down: set[int] = set()
        self._swallow_up = False
        self._letter_down: set[int] = set()
        self._last_obs_move_ms = 0
        self._obs_latest_move: tuple[int, int] | None = None
        self._obs_events_dropped = 0

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
        # Coalesced move held while the queue was soft-full.
        if self._obs_latest_move is not None:
            x, y = self._obs_latest_move
            self._obs_latest_move = None
            items.append(("observation_move", x, y))
        return items

    def _put_observation(self, event: tuple) -> None:
        """Enqueue observation mouse traffic with backpressure (never block the hook)."""

        kind = event[0]
        try:
            qsize = self.events.qsize()
        except NotImplementedError:  # pragma: no cover
            qsize = 0
        if kind == "observation_move":
            if qsize >= _OBS_QUEUE_SOFT:
                self._obs_latest_move = (int(event[1]), int(event[2]))
                self._obs_events_dropped += 1
                return
            self._obs_latest_move = None
            self.events.put(event)
            return
        if qsize >= _OBS_QUEUE_HARD:
            self._obs_events_dropped += 1
            return
        if qsize >= _OBS_QUEUE_SOFT and kind == "observation_down":
            # Prefer keeping ups paired; drop excess downs under soft pressure.
            self._obs_events_dropped += 1
            return
        self.events.put(event)

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
        # Prefer w_param; LLKHF_UP alone has been flaky for some key-up paths.
        is_up = w_param in (WM_KEYUP, WM_SYSKEYUP) or bool(data.flags & LLKHF_UP)
        vk = int(data.vkCode)
        swallow = False
        # Remap expand key: next non-modifier keydown becomes the binding.
        if self.state.flight_deck_remap and vk != VK_ESCAPE:
            if is_up:
                return 1
            swallow = True
            self.state.flight_deck_remap = False
            self.events.put(("flight_deck_remap_key", vk))
            return 1
        # Idle Lab surface → no keyboard hotkeys (buttons only). Pass keys through
        # except Esc while a runner is stoppable (Stop all still reachable via F8 chrome).
        if (
            self.state.lab_visible
            and not self.state.live_control_active
            and not self.state.molecule_lab_active
            and not self.state.flight_deck_remap
        ):
            if vk == VK_ESCAPE and self.state.stoppable:
                if is_up:
                    self._esc_down = False
                elif not self._esc_down:
                    self._esc_down = True
                    swallow = True
                    self.events.put(("escape",))
                elif self.state.stoppable:
                    swallow = True
                if swallow:
                    return 1
            return self._next(self._kb_hook, n_code, w_param, l_param)
        # Molecule Lab needs real typing — but not while Live Control is armed.
        # LCO (incl. molecule marks / rebind) must keep letters+digits; Lab typing
        # resumes when LCO is off or paused.
        lab_typing = self.state.molecule_lab_active and not (
            self.state.live_control_active and not self.state.live_control_paused
        )
        if lab_typing:
            if vk == VK_ESCAPE:
                if is_up:
                    self._esc_down = False
                    return 1
                if not self._esc_down:
                    self._esc_down = True
                    self.events.put(("escape",))
                return 1
            return self._next(self._kb_hook, n_code, w_param, l_param)
        # While LCO is armed, Activate key = pause / resume (stay in Live Overlay Lab).
        # Do not require expand_armed/open — LCO ownership alone is enough.
        if self.state.live_control_active and vk == int(self.state.flight_deck_expand_vk):
            swallow = True
            if is_up:
                self._expand_down = False
            elif not self._expand_down:
                self._expand_down = True
                self.events.put(("flight_deck_activate",))
            return 1
        if (
            vk == VK_SPACE
            and self.state.flight_deck_expanded
            and not self.state.live_control_active
        ):
            # Flagship menu key while the flight-deck tree is open.
            swallow = True
            if is_up:
                self._space_down = False
            elif not self._space_down:
                self._space_down = True
                token = menu_token_from_vk(VK_SPACE)
                if token is not None:
                    self.events.put(("flight_deck_menu_key", token))
        elif vk == VK_SPACE:
            # Pass Space through while a title dialog is open so titles can include spaces.
            if self.state.title_dialog_open:
                pass
            elif self.state.walkthrough_active:
                swallow = True
                if is_up:
                    self._space_down = False
                elif not self._space_down:
                    self._space_down = True
                    self.events.put(("walkthrough_space",))
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
                    # Ignore Space while capturing/saving so presses do not pile up.
                    if not self.state.screenshot_busy:
                        self.events.put(("screen_map_space",))
        elif vk == VK_ESCAPE:
            # Pass Esc through while a title dialog is open so the dialog can cancel first.
            if self.state.title_dialog_open:
                pass
            else:
                # Inactive deck owns only Activate — Esc passes through to other apps.
                armed = (
                    self.state.anchor_armed
                    or self.state.recording
                    or self.state.playback
                    or self.state.screenshot_mode
                    or self.state.observation_active
                    or self.state.walkthrough_active
                    or self.state.live_control_active
                    or self.state.molecule_lab_active
                    or self.state.stoppable
                    or self.state.flight_deck_remap
                    or self.state.quit_confirm
                    or self.state.flight_deck_active
                    or self.state.deck_mode_active
                )
                if is_up:
                    self._esc_down = False
                elif armed and not self._esc_down:
                    self._esc_down = True
                    if self.state.live_control_active:
                        self.state.live_control_cancel.set()
                    swallow = True
                    self.events.put(("escape",))
                elif armed:
                    swallow = True
        elif (
            vk == int(self.state.flight_deck_expand_vk)
            and (self.state.flight_deck_expand_armed or self.state.flight_deck_open)
            and not self.state.molecule_lab_active
        ):
            # Activate / Deactivate — only global deck key while inactive.
            # While Molecule Lab is open, pass through so Lab text boxes can type.
            swallow = True
            if is_up:
                self._expand_down = False
            elif not self._expand_down:
                self._expand_down = True
                self.events.put(("flight_deck_activate",))
        elif self.state.quit_confirm and vk == VK_RETURN and not self.state.molecule_lab_active:
            swallow = True
            if is_up:
                self._enter_down = False
            elif not self._enter_down:
                self._enter_down = True
                self.events.put(("shell_enter",))
        elif (
            self.state.flight_deck_active
            and (not self.state.flight_deck_anchored)
            and vk == VK_RETURN
            and not self.state.molecule_lab_active
        ):
            swallow = True
            if is_up:
                self._enter_down = False
            elif not self._enter_down:
                self._enter_down = True
                self.events.put(("shell_enter",))
        elif (
            self.state.flight_deck_active
            and (not self.state.flight_deck_anchored)
            and vk == VK_A
            and not self.state.molecule_lab_active
        ):
            swallow = True
            if is_up:
                self._shell_key_down.discard(vk)
            elif vk not in self._shell_key_down:
                self._shell_key_down.add(vk)
                self.events.put(("shell_a",))
        elif (
            self.state.live_control_active
            and not self.state.live_control_paused
            and (
                (VK_A <= vk <= VK_Z)
                or (VK_0 <= vk <= VK_9)
                or menu_token_from_vk(vk) is not None
            )
        ):
            # Live Control Overlay: playbook hotkeys own letters/digits while armed.
            # When paused, keys pass through for typing (` resumes, Esc exits).
            # Molecule Lab may stay open underneath — LCO still owns keys until paused/exit.
            swallow = True
            token = menu_token_from_vk(vk)
            if is_up:
                was_down = vk in self._menu_down
                self._menu_down.discard(vk)
                if was_down and token is not None:
                    self.events.put(("live_control_key", token, "up"))
            elif vk not in self._menu_down:
                self._menu_down.add(vk)
                if token is not None:
                    # Armed toggle (A): cancel on the hook thread so the pack aborts
                    # before the UI queue finishes the current step.
                    armed = self.state.live_control_toggle_token
                    if armed and token == armed:
                        self.state.live_control_cancel.set()
                    self.events.put(("live_control_key", token, "down"))
        elif (
            self.state.flight_deck_active
            and (not self.state.lab_visible)
            and vk == VK_I
            and not self.state.molecule_lab_active
            and not self.state.live_control_active
        ):
            # Open Lab only while the deck is active.
            swallow = True
            if is_up:
                self._shell_key_down.discard(vk)
            elif vk not in self._shell_key_down:
                self._shell_key_down.add(vk)
                self.events.put(("shell_i",))
        elif (
            self.state.flight_deck_active
            and (not self.state.lab_visible)
            and vk == VK_R
            and not self.state.molecule_lab_active
            and not self.state.live_control_active
        ):
            # Restart only while Deck is active — inactive Deck must not eat R.
            swallow = True
            if is_up:
                self._shell_key_down.discard(vk)
            elif vk not in self._shell_key_down:
                self._shell_key_down.add(vk)
                self.events.put(("shell_r",))
        elif (
            self.state.flight_deck_active
            and (not self.state.lab_visible)
            and (
                (not self.state.deck_mode_active)
                or self.state.atom_create_active
            )
            and self.state.flight_deck_anchored
            and self.state.flight_deck_expanded
            and not self.state.molecule_lab_active
            and not self.state.live_control_active
            and (
                (VK_A <= vk <= VK_Z)
                or (VK_0 <= vk <= VK_9)
                or menu_token_from_vk(vk) is not None
            )
        ):
            # Accordion in menu mode, and Atom Create (create keymap, same grammar).
            swallow = True
            if is_up:
                self._menu_down.discard(vk)
            elif vk not in self._menu_down:
                self._menu_down.add(vk)
                token = menu_token_from_vk(vk)
                if token is not None:
                    self.events.put(("flight_deck_menu_key", token))
        elif (
            self.state.walkthrough_active
            and (not self.state.lab_visible)
            and VK_A <= vk <= VK_Z
        ):
            swallow = True
            if is_up:
                self._letter_down.discard(vk)
            elif vk not in self._letter_down:
                self._letter_down.add(vk)
                letter = chr(vk)
                self.events.put(("walkthrough_key", letter))
        elif vk == VK_F6 and not self.state.lab_visible:
            swallow = True
            if is_up:
                self._f6_down = False
            elif not self._f6_down:
                self._f6_down = True
                self.events.put(("f6",))
        elif vk == VK_F7 and not self.state.lab_visible:
            swallow = True
            if is_up:
                self._f7_down = False
            elif not self._f7_down:
                self._f7_down = True
                self.events.put(("f7",))
        elif vk == VK_F8 and not self.state.lab_visible:
            # Stop all via F8 only on Deck; Idle Lab uses chrome Stop all.
            swallow = True
            if is_up:
                self._f8_down = False
            elif not self._f8_down:
                self._f8_down = True
                self.events.put(("f8",))
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
        # Observation: pass mouse through to the game; only mirror events to the UI queue.
        if self.state.observation_active and not self.state.anchor_armed:
            data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            if int(data.flags) & LLMHF_INJECTED:
                return self._next(self._mouse_hook, n_code, w_param, l_param)
            x, y = int(data.pt.x), int(data.pt.y)
            if w_param == WM_MOUSEMOVE:
                # Coarse enqueue throttle; ObservationController samples further.
                now_ms = int(data.time)
                if now_ms - self._last_obs_move_ms >= 40:
                    self._last_obs_move_ms = now_ms
                    self._put_observation(("observation_move", x, y))
            elif w_param == WM_LBUTTONDOWN:
                self._put_observation(("observation_down", "left", x, y))
            elif w_param == WM_LBUTTONUP:
                self._put_observation(("observation_up", "left", x, y))
            elif w_param == WM_RBUTTONDOWN:
                self._put_observation(("observation_down", "right", x, y))
            elif w_param == WM_RBUTTONUP:
                self._put_observation(("observation_up", "right", x, y))
            elif w_param == WM_MBUTTONDOWN:
                self._put_observation(("observation_down", "middle", x, y))
            elif w_param == WM_MBUTTONUP:
                self._put_observation(("observation_up", "middle", x, y))
            elif w_param == WM_MOUSEWHEEL:
                # high word of mouseData is signed wheel delta (multiples of 120)
                raw = ctypes.c_short(data.mouseData >> 16).value
                notches = int(raw // 120) if raw else 0
                if notches:
                    self._put_observation(("observation_wheel", x, y, notches))
        return self._next(self._mouse_hook, n_code, w_param, l_param)
