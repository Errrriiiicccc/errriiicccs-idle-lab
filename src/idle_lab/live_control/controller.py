"""Live Control Overlay session: playbook overlay + keyboard actuation."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from idle_lab.ai_batch.panel_detect import detect_upgrade_panel
from idle_lab.ai_batch.scroll_metrics import crop_normalized
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.automations.ocr import OcrError, run_ocr
from idle_lab.automations.tower_nav import click_normalized, drag_list, fling_list
from idle_lab.humanize import HumanizeProfile
from idle_lab.live_control.buy_detect import BuyGridDetection, DetectedBuySlot, detect_buy_grid
from idle_lab.live_control.buy_identity import (
    BoundBuy,
    ViewportIdentity,
    best_catalog_score,
    bind_by_offset,
    bind_from_slot_texts,
    nameplate_roi,
    slot_column,
    unknown_identity,
)
from idle_lab.live_control.console import ConsoleSession, DEFAULT_VERBOSITY, normalize_verbosity
from idle_lab.live_control.overlay import LiveControlOverlay, LiveControlOverlayState
from idle_lab.live_control.playbook import (
    FIRE_MODE_SPAM,
    FIRE_MODE_TOGGLE,
    LiveControlPlaybook,
    PlaybookError,
    default_playbook_path,
    fire_mode_for,
    is_actuation_action,
    load_playbook,
)
from idle_lab.models import Rect


LogFn = Callable[[str, str], None]
AnchorFn = Callable[[], tuple[str | None, int | None, Rect | None]]
HumanizeFn = Callable[[], HumanizeProfile]
RunEventFn = Callable[[str], None]
EvidenceFn = Callable[..., None]
PostEventFn = Callable[[tuple], None]
LegendFn = Callable[[bool], None]
PauseFn = Callable[[bool], None]
ToggleTokenFn = Callable[[str | None], None]


class LiveControlError(RuntimeError):
    """Live Control Overlay refused to start or act."""


class NullOverlay:
    """Draws nothing — for headless sessions driven by automation atoms."""

    def show(self, playbook: LiveControlPlaybook, anchor: Rect, state: LiveControlOverlayState) -> None:
        _ = playbook, anchor, state

    def hide(self) -> None:
        return None

    def pump(self) -> None:
        return None


@dataclass
class LiveControlSummary:
    active: bool
    tab: str | None
    panel_open: bool
    aligned: bool
    playbook_id: str | None
    evidence: bool


class LiveControlController:
    def __init__(
        self,
        *,
        overlay: LiveControlOverlay | NullOverlay,
        project_root: Path,
        get_anchor: AnchorFn,
        get_humanize: HumanizeFn | None = None,
        run_event_once: RunEventFn | None = None,
        on_evidence: EvidenceFn | None = None,
        post_event: PostEventFn | None = None,
        on_legend_change: LegendFn | None = None,
        on_pause_change: PauseFn | None = None,
        on_toggle_token: ToggleTokenFn | None = None,
        console_enabled: bool = False,
        console_verbosity: str = DEFAULT_VERBOSITY,
        cancel_event: threading.Event | None = None,
        log: LogFn | None = None,
        restore_cursor: bool = True,
        async_actions: bool = False,
    ) -> None:
        self.overlay = overlay
        self.project_root = Path(project_root)
        self.get_anchor = get_anchor
        self.get_humanize = get_humanize
        self.run_event_once = run_event_once
        self.on_evidence = on_evidence
        self.post_event = post_event
        self.on_legend_change = on_legend_change
        self.on_pause_change = on_pause_change
        self.on_toggle_token = on_toggle_token
        self.async_actions = bool(async_actions)
        self._log = log or (lambda _m, _l="info": None)
        self.restore_cursor = False
        self._settings_restore_cursor = restore_cursor
        self.active = False
        self.evidence = False
        self.paused = False
        self.show_descriptors = False
        self.playbook: LiveControlPlaybook | None = None
        self.panel_open = False
        self.tab: str | None = None
        self.aligned = True
        self.live_slots: tuple[DetectedBuySlot, ...] = ()
        self.identity: ViewportIdentity = unknown_identity(reason="inactive")
        self.console = ConsoleSession(project_root=self.project_root)
        self.console.configure(
            enabled=bool(console_enabled),
            verbosity=normalize_verbosity(console_verbosity),
        )
        self._busy = False
        self._lock = threading.Lock()
        self._last_detection: BuyGridDetection | None = None
        # Shared with the keyboard hook so Esc / ` abort mid-drag without waiting on the UI queue.
        self.cancel_event = cancel_event if cancel_event is not None else threading.Event()
        self._held_actions: list[str] = []
        self._toggled_action: str | None = None
        self._action_queue: list[str] = []
        self._current_action: str | None = None
        self._routine_remaining: list[str] = []
        self._ui_thread = threading.current_thread()
        self._worker: threading.Thread | None = None
        self.molecule_bridge = None  # optional MoleculeLcoBridge

    def attach_molecule_bridge(self, bridge) -> None:
        """Optional Lab→LCO molecule marks / hotkeys."""

        self.molecule_bridge = bridge

    def summary(self) -> LiveControlSummary:
        return LiveControlSummary(
            active=self.active,
            tab=self.tab,
            panel_open=self.panel_open,
            aligned=self.aligned,
            playbook_id=self.playbook.id if self.playbook else None,
            evidence=self.evidence,
        )

    def enter(self, playbook_path: Path | None = None, *, evidence: bool = False) -> None:
        if self.active:
            self._log("Live Control Overlay already on.", "info")
            self._repaint("Live Control already on")
            return
        title, hwnd, rect = self.get_anchor()
        if rect is None or not hwnd:
            raise LiveControlError("Anchor a window before entering Live Control Overlay.")
        path = Path(playbook_path) if playbook_path else default_playbook_path(self.project_root)
        try:
            playbook = load_playbook(path)
        except PlaybookError as exc:
            raise LiveControlError(str(exc)) from exc
        if playbook.surface != "main_gameplay":
            raise LiveControlError(f"playbook surface {playbook.surface!r} not supported yet")

        try:
            image = grab_anchor(rect)
        except CaptureError as exc:
            raise LiveControlError(f"Live Control enter capture failed: {exc}") from exc

        panel = detect_upgrade_panel(image)
        self.playbook = playbook
        self.panel_open = bool(panel.panel_open)
        self.tab = panel.tab if panel.panel_open else None
        self.evidence = bool(evidence)
        self.paused = False
        self.show_descriptors = False
        self._held_actions.clear()
        self._set_toggled_action(None)
        self._action_queue.clear()
        self._current_action = None
        self._routine_remaining.clear()
        self.cancel_event.clear()
        self.active = True
        self._ui_thread = threading.current_thread()
        self._notify_legend()
        self._notify_pause()
        if self.panel_open:
            self._apply_detection(detect_buy_grid(image), context="enter")
            # Mid-list is fine — OCR nameplates; never assume page-1 from geometry alone.
            self._bind_identity_from_image(image, context="enter", fallback_home=False)
        else:
            self.live_slots = ()
            self.aligned = True
            self._last_detection = None
            self._forget_identity("enter-closed")
        mode = "troubleshoot" if self.evidence else "play"
        map_note = " · object map" if playbook.object_map is not None else ""
        console_folder = self.console.start_run()
        console_note = ""
        if console_folder is not None:
            console_note = f" · console→{console_folder.name}"
        self._log(
            f"Live Control ON ({mode}) · {playbook.title}{map_note}{console_note} · "
            f"panel={'open:' + (self.tab or '?') if self.panel_open else 'closed'} "
            f"({panel.reason})",
            "run",
        )
        self.console.event(
            f"enter mode={mode} panel={'open:' + (self.tab or '?') if self.panel_open else 'closed'} "
            f"reason={panel.reason}"
        )
        self._repaint(f"Live Control · {panel.reason}")
        self._sync_molecule_marks(rect)
        if self.evidence:
            self._emit_evidence(
                "enter",
                "after",
                detail=panel.reason,
                meta=self._grid_meta(extra={"panel_open": self.panel_open, "tab": self.tab}),
            )
        _ = title

    def exit(self, *, reason: str = "operator") -> None:
        if not self.active:
            return
        if self.evidence:
            self._emit_evidence("exit", "after", detail=reason, meta={"reason": reason}, capture=False)
        self.interrupt()
        self.console.stop_run(reason=reason)
        self.active = False
        self.evidence = False
        self.paused = False
        self.show_descriptors = False
        self._set_toggled_action(None)
        self._action_queue.clear()
        self._current_action = None
        self._routine_remaining.clear()
        self.overlay.hide()
        if self.molecule_bridge is not None:
            try:
                self.molecule_bridge.clear()
            except Exception as exc:  # noqa: BLE001
                self._log(f"Molecule LCO clear failed: {exc}", "warn")
        self._log(f"Live Control OFF ({reason})", "warn")
        self.playbook = None
        self.panel_open = False
        self.tab = None
        self.aligned = True
        self.live_slots = ()
        self._last_detection = None
        self._forget_identity("exit")
        self._notify_legend()
        self._notify_pause()

    def interrupt(self) -> None:
        """Abort in-flight work and drop hold/toggle/user queues (Esc / `)."""

        self.cancel_event.set()
        self._held_actions.clear()
        self._set_toggled_action(None)
        self._action_queue.clear()
        self._routine_remaining.clear()

    def handle_token(self, token: str) -> bool:
        """Compatibility: treat as a key-down (fire immediately)."""

        return self.handle_key(token, phase="down")

    def handle_key(self, token: str, *, phase: str = "down") -> bool:
        if not self.active or self.playbook is None:
            return False
        # Molecule rebind / fire owns the token before playbook actions (except describe hold).
        if self.molecule_bridge is not None:
            if self.molecule_bridge.rebinding:
                return bool(self.molecule_bridge.handle_key(token, phase=phase))
            action_peek = self.playbook.action_for_token(token)
            if action_peek != "describe" and self.molecule_bridge.handle_key(token, phase=phase):
                return True
        action = self.playbook.action_for_token(token)
        if action is None:
            return False
        if action == "describe":
            return self._set_describe(held=phase == "down")
        mode = fire_mode_for(action)
        if phase == "up":
            if mode == FIRE_MODE_SPAM:
                self._release_action(action)
            return True
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return True
        if mode == FIRE_MODE_TOGGLE:
            return self._toggle_action(action)
        if mode == FIRE_MODE_SPAM:
            self._hold_action(action)
            return self._request_action(action, repeat="hold")
        return self._request_action(action)

    def cancel_molecule_rebind(self) -> bool:
        """Esc while rebinding a molecule hotkey — does not exit LCO."""

        if self.molecule_bridge is None or not self.molecule_bridge.rebinding:
            return False
        self.molecule_bridge.cancel_rebind()
        return True

    def refresh_molecule_marks(self) -> None:
        if not self.active:
            return
        _title, _hwnd, rect = self.get_anchor()
        self._sync_molecule_marks(rect)

    def _sync_molecule_marks(self, rect: Rect | None) -> None:
        if self.molecule_bridge is None:
            return
        try:
            remaps = self.molecule_bridge.refresh(anchor=rect, playbook=self.playbook)
            for mol_id, old, new in remaps:
                self._log(
                    f"Molecule “{mol_id}” hotkey remapped {old or '—'} → {new} (conflict).",
                    "warn",
                )
            self.molecule_bridge.set_show_titles(bool(self.show_descriptors))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Molecule LCO sync failed: {exc}", "warn")


    def run_action(self, action: str) -> None:
        """Headless entry for automation atoms: one action; failures raise instead of logging."""

        if not self.active or self.playbook is None:
            raise LiveControlError("Live Control is not active.")
        if not is_actuation_action(action):
            raise LiveControlError(f"unknown Live Control action: {action}")
        if self._busy:
            raise LiveControlError("Live Control busy — wait for current action.")
        try:
            self._busy = True
            self._dispatch(action)
        finally:
            self._busy = False

    def continue_repeat(self, action: str) -> None:
        """UI-queue continuation after a spam-hold or toggle fire finishes."""

        if not self.active or self.paused or self.cancel_event.is_set():
            return
        if self._action_queue:
            self.drain_queue()
            return
        if action in self._held_actions:
            self._kick_held(preferred=action)
            return
        if action == self._toggled_action:
            self._kick_toggle()

    def drain_queue(self) -> None:
        """Run the next user-queued action, or resume toggle/spam if the queue is empty."""

        if not self.active or self.paused or self.cancel_event.is_set() or self._busy:
            return
        if self._action_queue:
            action = self._action_queue.pop(0)
            repeat = None
            if action in self._held_actions:
                repeat = "hold"
            elif action == self._toggled_action:
                repeat = "toggle"
            self._run_action(action, repeat=repeat)
            return
        if self._held_actions:
            self._kick_held()
            return
        if self._toggled_action:
            self._kick_toggle()

    def toggle_pause(self) -> bool:
        """Backtick: gray out / re-arm LCO without exiting the session."""

        if not self.active:
            return False
        self.paused = not self.paused
        if self.paused:
            self.interrupt()
            if self.show_descriptors:
                self.show_descriptors = False
                self._notify_legend()
            self.console.event("paused")
            self.console.flush(reason="pause")
            self._log("Live Control paused — marks inert. ` resumes · Esc exits.", "warn")
            self._repaint("Paused")
        else:
            self.cancel_event.clear()
            self.console.event("resumed")
            self._log("Live Control resumed.", "ok")
            self._repaint("Resumed")
        self._notify_pause()
        return True

    def _hold_action(self, action: str) -> None:
        if action in self._held_actions:
            self._held_actions.remove(action)
        self._held_actions.append(action)

    def _release_action(self, action: str) -> None:
        if action in self._held_actions:
            self._held_actions.remove(action)

    def _toggle_action(self, action: str) -> bool:
        """Arm/disarm a repeating routine. Key-up is ignored; press again to stop."""

        if self._toggled_action == action:
            self._stop_toggle(reason="operator")
            return True
        if self._toggled_action is not None:
            self._stop_toggle(reason="switch")
        self._set_toggled_action(action)
        self.cancel_event.clear()
        label = action
        if self.playbook is not None:
            for routine in self.playbook.routines:
                if routine.action == action:
                    label = routine.label
                    break
        self._log(f"Toggle ON · {label} — press again to stop.", "run")
        self._repaint(f"Toggle ON · {label}")
        return self._request_action(action, repeat="toggle")

    def _stop_toggle(self, *, reason: str = "operator") -> None:
        if self._toggled_action is None:
            return
        was = self._toggled_action
        self._set_toggled_action(None)
        self.cancel_event.set()
        self._action_queue = [item for item in self._action_queue if item != was]
        self._routine_remaining.clear()
        label = was
        if self.playbook is not None:
            for routine in self.playbook.routines:
                if routine.action == was:
                    label = routine.label
                    break
        self._log(f"Toggle OFF · {label} ({reason})", "warn")
        self._repaint(f"Toggle OFF · {label}")

    def _set_toggled_action(self, action: str | None) -> None:
        self._toggled_action = action
        token = None
        if action and self.playbook is not None:
            token = self.playbook.hotkey_for(action)
        if self.on_toggle_token is not None:
            try:
                self.on_toggle_token(token)
            except Exception:
                pass

    def _enqueue(self, action: str) -> None:
        self._action_queue.append(action)
        pending = len(self._action_queue)
        self._log(f"Queued {action} (#{pending})", "info")
        self._repaint(f"Queued {action} · {pending} waiting")

    def _request_action(self, action: str, *, repeat: str | None = None) -> bool:
        """Run now, or FIFO-queue if something is already in flight."""

        if self._busy or self._action_queue:
            self._enqueue(action)
            return True
        # Only clear cancel when actually starting fresh work — never while enqueueing.
        self.cancel_event.clear()
        return self._run_action(action, repeat=repeat)

    def _kick_held(self, preferred: str | None = None) -> bool:
        if self.paused or self.cancel_event.is_set() or not self._held_actions:
            return True
        if self._busy or self._action_queue:
            return True
        action = preferred if preferred in self._held_actions else self._held_actions[-1]
        return self._run_action(action, repeat="hold")

    def _kick_toggle(self) -> bool:
        if self.paused or self.cancel_event.is_set() or not self._toggled_action:
            return True
        if self._busy or self._action_queue:
            return True
        return self._run_action(self._toggled_action, repeat="toggle")

    def _visible_queue(self) -> tuple[str, ...]:
        """Upcoming marks: remaining routine steps, then user-queued actions."""

        return tuple([*self._routine_remaining, *self._action_queue])

    def _schedule_next(self, action: str, *, repeat: str | None) -> None:
        if not self.active or self.paused or self.cancel_event.is_set() or self.post_event is None:
            return
        try:
            if self._action_queue:
                self.post_event(("live_control_dequeue",))
                return
            should_requeue = False
            if repeat == "hold" and action in self._held_actions:
                should_requeue = True
            if repeat == "toggle" and action == self._toggled_action:
                should_requeue = True
            if should_requeue:
                self.post_event(("live_control_repeat", action))
                return
            if self._toggled_action and action != self._toggled_action:
                self.post_event(("live_control_repeat", self._toggled_action))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control repeat queue failed: {exc}", "warn")

    def _run_action(self, action: str, *, repeat: str | None = None) -> bool:
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return True
        if self.cancel_event.is_set() and repeat is not None:
            return True
        if self._busy:
            self._enqueue(action)
            return True
        self._busy = True
        self._current_action = action
        self._repaint(action)

        # App path: never block the hotkey drain — worker finishes via live_control_done.
        if self.async_actions and self.post_event is not None:
            errors: list[BaseException] = []

            def worker() -> None:
                try:
                    self._dispatch(action)
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)
                finally:
                    payload = (
                        "live_control_done",
                        action,
                        repeat,
                        tuple(
                            ("live_control", str(exc))
                            if isinstance(exc, LiveControlError)
                            else ("error", str(exc))
                            for exc in errors
                        ),
                    )
                    try:
                        self.post_event(payload)
                    except Exception as exc:  # noqa: BLE001
                        self._busy = False
                        self._current_action = None
                        self._routine_remaining.clear()
                        self._log(f"Live Control done queue failed: {exc}", "warn")

            thread = threading.Thread(target=worker, name=f"lco-{action}", daemon=True)
            self._worker = thread
            thread.start()
            return True

        try:
            self._dispatch(action)
        except LiveControlError as exc:
            self._log(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control action failed: {exc}", "error")
        finally:
            self._busy = False
            self._current_action = None
            self._routine_remaining.clear()
        self._schedule_next(action, repeat=repeat)
        self._repaint("Ready" if not self._action_queue and not self._toggled_action else "…")
        return True

    def finish_action(
        self,
        action: str,
        *,
        repeat: str | None = None,
        errors: tuple[tuple[str, str], ...] = (),
    ) -> None:
        """UI-thread completion for async actuation (from live_control_done)."""

        for _kind, message in errors:
            self._log(message, "error")
        self._busy = False
        self._current_action = None
        self._routine_remaining.clear()
        self._worker = None
        self._schedule_next(action, repeat=repeat)
        self._repaint("Ready" if not self._action_queue and not self._toggled_action else "…")

    def _sleep_ms(self, ms: int) -> bool:
        """Interruptible pause. True if cancelled."""

        if self.cancel_event.is_set():
            return True
        if ms <= 0:
            return False
        deadline = time.monotonic() + ms / 1000.0
        while time.monotonic() < deadline:
            if self.cancel_event.is_set():
                return True
            remaining = deadline - time.monotonic()
            if self.cancel_event.wait(min(0.05, max(0.0, remaining))):
                return True
        return False

    def _settle_before_detect(self, scroll: dict[str, Any], *, gesture_ms: int) -> bool:
        """Wait until list motion settles enough for buy-grid detect. True if cancelled."""

        detect_ms = max(0, int(scroll.get("detect_settle_ms") or 0))
        wait_ms = max(max(0, int(gesture_ms)), detect_ms)
        if wait_ms <= 0:
            return False
        return self._sleep_ms(wait_ms)

    def run_scroll(self, direction: str, *, mode: str = "step", _retries: int = 0) -> None:
        """UI-thread entry for scroll step/fling."""

        _ = _retries
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return
        if self._busy:
            self._log("Live Control busy — wait for current action.", "warn")
            return
        try:
            self._busy = True
            self._do_scroll(direction, mode=mode)
        except LiveControlError as exc:
            self._log(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control action failed: {exc}", "error")
        finally:
            self._busy = False

    def _dispatch(self, action: str) -> None:
        self.console.event(f"action {action}")
        if action.startswith("tab_"):
            self._do_tab(action.removeprefix("tab_"))
        elif action.startswith("buy_"):
            self._do_buy(int(action.removeprefix("buy_")))
        elif action == "scroll_up":
            self._do_scroll("up", mode="step")
        elif action == "scroll_down":
            self._do_scroll("down", mode="step")
        elif action == "fling_up":
            self._do_scroll("up", mode="fling")
        elif action == "fling_down":
            self._do_scroll("down", mode="fling")
        elif action == "stat_collect":
            self._do_stat_collect()
        elif action == "claim_gem":
            self._do_claim_gem()
        elif action == "refresh":
            self._do_refresh()
        elif action.startswith("routine_"):
            self._do_routine(action)
        elif action == "describe":
            # Hold is handled in handle_key; never fire as a one-shot dispatch.
            return
        else:
            raise LiveControlError(f"unknown Live Control action: {action}")

    def _notify_legend(self) -> None:
        if self.on_legend_change is None:
            return
        try:
            self.on_legend_change(bool(self.show_descriptors))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control legend notify failed: {exc}", "warn")

    def _notify_pause(self) -> None:
        if self.on_pause_change is None:
            return
        try:
            self.on_pause_change(bool(self.paused))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control pause notify failed: {exc}", "warn")

    def _set_describe(self, *, held: bool) -> bool:
        """Hold D: show hotkey marks + HV descriptors; release clears."""

        if self.paused:
            if held:
                self._log("Live Control paused — press ` to resume.", "warn")
            return True
        want = bool(held)
        if self.show_descriptors == want:
            return True
        self.show_descriptors = want
        if self.molecule_bridge is not None:
            try:
                self.molecule_bridge.set_show_titles(want)
            except Exception as exc:  # noqa: BLE001
                self._log(f"Molecule title toggle failed: {exc}", "warn")
        self._notify_legend()
        self._repaint("Describe" if want else "Describe off")
        return True

    def _anchor_ready(self) -> tuple[int, Rect]:
        _title, hwnd, rect = self.get_anchor()
        if rect is None or not hwnd:
            raise LiveControlError("Anchor lost — leaving Live Control.")
        return int(hwnd), rect

    def _profile(self) -> HumanizeProfile:
        return HumanizeProfile.from_level("off")

    def _click(self, *, hwnd: int, rect: Rect, nx: float, ny: float) -> None:
        click_normalized(
            hwnd=hwnd,
            rect=rect,
            nx=nx,
            ny=ny,
            hold_ms=45,
            restore_cursor=False,
            profile=self._profile(),
        )

    def _grab(self, rect: Rect) -> Image.Image:
        try:
            return grab_anchor(rect)
        except CaptureError as exc:
            raise LiveControlError(f"capture failed: {exc}") from exc

    def _grid_meta(self, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        detection = self._last_detection
        meta: dict[str, Any] = {
            "aligned": self.aligned,
            "snapped": bool(detection.snapped) if detection else self.aligned,
            "slot_count": len(self.live_slots),
            "detection_reason": detection.reason if detection else "",
            "row_nys": list(detection.row_nys) if detection else [s.ny for s in self.live_slots],
            "tab": self.tab,
            "identity_known": self.identity.known,
            "identity_confidence": round(float(self.identity.confidence), 3),
            "catalog_offset": self.identity.offset if self.identity.known else None,
            "identity_reason": self.identity.reason,
            "offset_scores": list(self.identity.offset_scores),
            "slot_labels": {str(b.slot_index): b.display_label for b in self.identity.bindings},
            "slot_confidence": {
                str(b.slot_index): round(float(b.confidence), 3) for b in self.identity.bindings
            },
            "slot_source": {str(b.slot_index): b.source for b in self.identity.bindings},
        }
        if extra:
            meta.update(extra)
        return meta

    def _catalog(self) -> list:
        object_map = self._object_map()
        if object_map is None or not self.tab:
            return []
        return object_map.catalog_for_tab(self.tab)

    def _forget_identity(self, reason: str) -> None:
        slots = max(6, len(self.live_slots) or 6)
        self.identity = unknown_identity(slots, reason=reason)

    def _home_identity(self, *, reason: str = "homed") -> None:
        """Fallback when OCR misses after an explicit seek-top / fling-up."""

        catalog = self._catalog()
        if not catalog or not self.aligned:
            self._forget_identity(f"{reason}-unaligned" if not self.aligned else f"{reason}-empty")
            return
        slot_count = max(6, len(self.live_slots) or 6)
        self.identity = bind_by_offset(catalog, offset=0, slot_count=slot_count, source="page")
        self.identity = ViewportIdentity(
            known=self.identity.known,
            offset=0,
            bindings=self.identity.bindings,
            reason=reason,
        )
        self._log(
            f"Buy identity [{reason}]: "
            + ", ".join(f"{b.slot_index}={b.label}" for b in self.identity.bindings if b.known),
            "ok" if self.identity.known else "warn",
        )

    def _ocr_one_nameplate(
        self,
        crop: Image.Image,
        *,
        catalog: list,
        column: str,
        slot_index: int,
    ) -> str:
        """OCR one title crop: early-exit on a strong catalog match; keep fallbacks."""

        # Invert-first: white titles on dark cards. Early-exit preserves accuracy when strong.
        variants = (
            {"config": "--psm 6", "invert": True, "scale": 2},
            {"config": "--psm 6", "invert": True, "threshold": 170, "scale": 2},
            {"config": "--psm 7", "invert": True, "scale": 2},
            {"config": "--psm 6", "scale": 2},
        )
        best_text = ""
        best_rank = (-1.0, -1)
        for kwargs in variants:
            try:
                text = (run_ocr(crop, **kwargs) or "").strip()
            except OcrError:
                raise
            except Exception:  # noqa: BLE001
                continue
            if not text:
                continue
            score = best_catalog_score(text, catalog, column=column) if catalog else 0.0
            rank = (score, sum(ch.isalpha() for ch in text))
            if rank > best_rank:
                best_rank = rank
                best_text = text
            self.console.process(
                f"ocr slot {slot_index} prep={kwargs.get('config')} "
                f"inv={bool(kwargs.get('invert'))} score={score:.2f} text={text!r}"
            )
            if score >= 0.75:
                break
        return best_text

    def _ocr_nameplates(self, image: Image.Image) -> dict[int, str]:
        """Read each live slot's title band in parallel; early-exit per slot when strong."""

        object_map = self._object_map()
        grid = object_map.buy_grid(self.tab) if object_map is not None and self.tab else {}
        catalog = self._catalog()
        card_nw = float(grid.get("card_nw") or 0.30)
        card_nh = float(grid.get("card_nh") or 0.08)
        jobs: list[tuple[int, Image.Image, str]] = []
        for slot in self.live_slots:
            roi = nameplate_roi(slot.nx, slot.ny, card_nw=card_nw, card_nh=card_nh)
            crop = crop_normalized(image, **roi)
            jobs.append((int(slot.index), crop, slot_column(int(slot.index))))

        out: dict[int, str] = {}
        if not jobs:
            return out
        self.console.process(f"ocr begin slots={len(jobs)}")
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=min(6, len(jobs))) as pool:
            futures = {
                pool.submit(
                    self._ocr_one_nameplate,
                    crop,
                    catalog=catalog,
                    column=column,
                    slot_index=index,
                ): index
                for index, crop, column in jobs
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    out[index] = future.result()
                except OcrError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    self.console.process(f"ocr slot {index} failed: {exc}")
                    out[index] = ""
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self.console.process(f"ocr done {elapsed_ms}ms → {out}")
        return out

    def _bind_identity_from_image(self, image: Image.Image, *, context: str, fallback_home: bool = False) -> None:
        """OCR nameplates for live slots; never invent labels from scroll math alone."""

        catalog = self._catalog()
        if not catalog or not self.live_slots:
            self._forget_identity(f"{context}-empty")
            return
        slot_count = max(len(self.live_slots), 6)
        try:
            observations = self._ocr_nameplates(image)
            identity = bind_from_slot_texts(catalog, observations, slot_count=slot_count)
        except OcrError as exc:
            self._log(f"Buy identity OCR failed ({context}): {exc}", "warn")
            self.console.result(f"identity OCR failed ({context}): {exc}")
            if fallback_home and self.aligned:
                self._home_identity(reason=f"{context}-ocr-error-page")
            else:
                self._forget_identity(f"{context}-ocr-error")
            return

        if identity.known:
            self.identity = identity
            summary = ", ".join(
                f"{b.slot_index}={b.display_label}({b.source[0]}{b.confidence:.2f})"
                for b in identity.bindings
                if b.entry is not None
            )
            self._log(f"Buy identity [{context}/{identity.reason}]: {summary}", "ok")
            self.console.result(f"identity [{context}] {identity.reason} · {summary}")
            return

        # Surface partial OCR hits in Hold-D even when offset is not trusted.
        if any(b.known for b in identity.bindings):
            self.identity = identity
            summary = ", ".join(
                f"{b.slot_index}={b.display_label}({b.confidence:.2f})"
                for b in identity.bindings
                if b.known
            )
            self._log(f"Buy identity weak [{context}/{identity.reason}]: {summary}", "warn")
            self.console.result(f"identity weak [{context}] {identity.reason} · {summary}")
            if fallback_home and self.aligned:
                # Keep partial OCR labels visible; only fill unknowns from page-1 if homed.
                page = bind_by_offset(catalog, offset=0, slot_count=slot_count, source="page")
                merged = []
                for bound in page.bindings:
                    hit = identity.binding_for(bound.slot_index)
                    merged.append(hit if hit is not None and hit.known else bound)
                self.identity = ViewportIdentity(
                    known=True,
                    offset=0,
                    bindings=tuple(merged),
                    reason=f"{context}-ocr-weak-page",
                )
            return

        if fallback_home and self.aligned:
            self._home_identity(reason=f"{context}-ocr-miss-page")
            return
        self._forget_identity(identity.reason or f"{context}-ocr-unknown")
        self.console.result(f"identity unknown [{context}] {identity.reason}")

    def _binding_for_slot(self, index: int) -> BoundBuy | None:
        return self.identity.binding_for(index)

    def _emit_evidence(
        self,
        action: str,
        phase: str,
        *,
        detail: str = "",
        meta: dict[str, Any] | None = None,
        capture: bool = True,
    ) -> None:
        if not self.evidence or self.on_evidence is None:
            return
        try:
            self.on_evidence(
                action=action,
                phase=phase,
                detail=detail,
                meta=meta or {},
                capture=capture,
            )
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control evidence failed: {exc}", "warn")

    def _apply_detection(self, detection: BuyGridDetection, *, context: str) -> None:
        self._last_detection = detection
        self.live_slots = tuple(detection.slots)
        self.aligned = bool(detection.snapped and detection.slots)
        self._log(
            f"Buy grid [{context}]: {detection.reason}; slots={len(detection.slots)} aligned={self.aligned}",
            "ok" if self.aligned else "warn",
        )

    def _relayout_from_screen(
        self,
        rect: Rect,
        *,
        context: str,
        identity: str = "ocr",
    ) -> BuyGridDetection:
        """Detect buy geometry, then optionally OCR-bind catalog identity.

        identity:
          - ``ocr``: nameplate OCR only (scroll / refresh / enter)
          - ``home``: OCR first, fall back to page-1 catalog after seek-top
          - ``none``: geometry only (caller manages identity)
        """

        image = self._grab(rect)
        detection = detect_buy_grid(image)
        self._apply_detection(detection, context=context)
        if identity == "home":
            self._bind_identity_from_image(image, context=context, fallback_home=True)
        elif identity == "ocr":
            self._bind_identity_from_image(image, context=context, fallback_home=False)
        return detection

    def _object_map(self):
        assert self.playbook is not None
        return self.playbook.object_map

    def _scroll_params(self, tab: str | None = None) -> dict[str, Any]:
        assert self.playbook is not None
        object_map = self._object_map()
        if object_map is not None:
            return object_map.scroll_params(tab)
        return dict(self.playbook.scroll)

    def _seek_look_for(self, tab: str) -> str:
        assert self.playbook is not None
        object_map = self._object_map()
        if object_map is not None:
            listing = object_map.scroll_list_for_tab(tab)
            if listing is not None and listing.raw.get("seek_top"):
                return str(listing.raw["seek_top"])
        return self.playbook.seek_top.get(tab) or ""

    def _seek_tab_top(self, *, hwnd: int, rect: Rect, tab: str) -> None:
        """Re-home list to first page with one fling toward top (same physics as T)."""

        assert self.playbook is not None
        scroll = self._scroll_params(tab)
        nx = float(scroll.get("nx") or 0.45)
        ny = float(scroll.get("ny") or 0.72)
        drag_fraction = float(scroll.get("fling_fraction") or 0.42)
        drag_steps = max(3, int(scroll.get("fling_steps") or 5))
        step_ms = max(1, int(scroll.get("fling_step_ms") or 4))
        gesture_ms = max(30, int(scroll.get("fling_settle_ms") or scroll.get("settle_ms") or 80))
        look_for = self._seek_look_for(tab)
        self._log(f"Tab home → fling top ({look_for or 'edge'})", "run")
        fling_list(
            hwnd=hwnd,
            rect=rect,
            direction="up",
            nx=nx,
            ny=ny,
            drag_fraction=drag_fraction,
            drag_steps=drag_steps,
            step_ms=step_ms,
            restore_cursor=False,
            stop=self.cancel_event,
        )
        self._settle_before_detect(scroll, gesture_ms=gesture_ms)

    def _do_tab(self, tab: str) -> None:
        assert self.playbook is not None
        tab = tab.strip().lower()
        object_map = self._object_map()
        tab_obj = object_map.tab_button(tab) if object_map is not None else None
        target = self.playbook.tabs.get(tab)
        if tab_obj is None and target is None:
            raise LiveControlError(f"unknown tab: {tab}")
        if tab_obj is not None and tab_obj.hit is not None:
            label = tab_obj.label
            nx, ny = tab_obj.hit
        elif target is not None:
            label = target.label
            nx, ny = target.nx, target.ny
        else:
            raise LiveControlError(f"unknown tab: {tab}")
        no_retap = True
        if object_map is not None:
            no_retap = object_map.no_retap_if_active(tab)
        hwnd, rect = self._anchor_ready()
        already = bool(self.panel_open and self.tab == tab)
        panel_id = tab_obj.opens_panel() if tab_obj is not None else None
        self._emit_evidence(
            f"tab_{tab}",
            "before",
            detail=label,
            meta={
                "tab": tab,
                "already": already,
                "object_id": tab_obj.id if tab_obj else None,
                "opens_panel": panel_id,
            },
        )
        if already and no_retap:
            self._log(f"Already on {label} — skip retap.", "info")
            self._relayout_from_screen(rect, context="retab", identity="ocr")
            if not self.identity.known:
                # Establish binding without retapping the tab button.
                self._seek_tab_top(hwnd=hwnd, rect=rect, tab=tab)
                if self.cancel_event.is_set():
                    self._log(f"Tab → {label} interrupted during identity home", "warn")
                    self._repaint("Interrupted")
                    return
                self._relayout_from_screen(rect, context="retab-home", identity="home")
            self._emit_evidence(
                f"tab_{tab}",
                "after",
                detail=f"retab {label}",
                meta=self._grid_meta(extra={"retap": True, "object_id": tab_obj.id if tab_obj else None}),
            )
            self._repaint(f"Already on {label}")
            return
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        if self._sleep_ms(200):
            self._log(f"Tab → {label} interrupted", "warn")
            self._repaint("Interrupted")
            return
        self.panel_open = True
        self.tab = tab
        # Game remembers per-tab scroll; re-home, then OCR (page-1 fallback if OCR misses).
        self._seek_tab_top(hwnd=hwnd, rect=rect, tab=tab)
        if self.cancel_event.is_set():
            self._log(f"Tab → {label} interrupted during seek", "warn")
            self._repaint("Interrupted")
            return
        self._relayout_from_screen(rect, context="tab", identity="home")
        self._log(f"Tab → {label} (homed)", "ok")
        self._emit_evidence(
            f"tab_{tab}",
            "after",
            detail=f"{label} homed",
            meta=self._grid_meta(
                extra={"homed": True, "object_id": tab_obj.id if tab_obj else None, "opens_panel": panel_id}
            ),
        )
        self._repaint(f"Tab {label}")

    def _slot_for_index(self, index: int) -> tuple[float, float, str, str | None]:
        assert self.playbook is not None
        # Viewport coords from live detection; semantic label only when identity is known.
        binding = self._binding_for_slot(index)
        if self.identity.known and binding is not None and binding.known:
            label = binding.label
            object_id = binding.object_id
        else:
            label = "?"
            object_id = None
        if self.live_slots:
            for slot in self.live_slots:
                if slot.index == index:
                    return slot.nx, slot.ny, label, object_id
            raise LiveControlError(f"slot {index} not visible (detected {len(self.live_slots)})")
        slots = self.playbook.buy_slots(self.tab)
        slot = next((s for s in slots if s.index == index), None)
        if slot is None:
            raise LiveControlError(f"no buy slot {index}")
        return slot.nx, slot.ny, label, object_id

    def _do_buy(self, index: int) -> None:
        assert self.playbook is not None
        if not self.panel_open or not self.tab:
            raise LiveControlError("Open an upgrade tab first (Q/W/E).")
        if not self.aligned:
            self._log("Buy with unsure geometry (amber) — still clicking.", "warn")
        if not self.identity.known:
            self._log("Buy identity unknown — clicking slot only (no catalog label).", "warn")
        nx, ny, label, object_id = self._slot_for_index(index)
        object_map = self._object_map()
        buy_obj = object_map.buy_by_id(object_id) if object_map is not None and object_id else None
        effects = buy_obj.effects if buy_obj is not None else {}
        hwnd, rect = self._anchor_ready()
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        self._log(f"Buy {index} {label}", "ok")
        self.console.result(f"buy_{index} → {label} @ ({nx:.3f},{ny:.3f})")
        self._emit_evidence(
            f"buy_{index}",
            "after",
            detail=label,
            meta=self._grid_meta(
                extra={
                    "nx": nx,
                    "ny": ny,
                    "label": label,
                    "object_id": object_id,
                    "effects": effects,
                    "identity_source": binding.source if (binding := self._binding_for_slot(index)) else "unknown",
                }
            ),
        )
        self._repaint(f"Buy {label}")

    def _do_scroll(self, direction: str, *, mode: str = "step") -> None:
        """Tap = one calibrated row-drag; hold/fling = momentum swipe toward list end."""

        assert self.playbook is not None
        if not self.panel_open or not self.tab:
            raise LiveControlError("Open an upgrade tab before scrolling.")
        hwnd, rect = self._anchor_ready()
        object_map = self._object_map()
        listing = object_map.scroll_list_for_tab(self.tab) if object_map is not None else None
        scroll = self._scroll_params(self.tab)
        nx = float(scroll.get("nx") or 0.45)
        ny = float(scroll.get("ny") or 0.72)
        mode_norm = "fling" if mode == "fling" else "step"

        if mode_norm == "fling":
            row_fraction = float(scroll.get("fling_fraction") or 0.42)
            hold_end_ms = 0
            settle_ms = max(30, int(scroll.get("fling_settle_ms") or scroll.get("settle_ms") or 80))
            drag_steps = max(3, int(scroll.get("fling_steps") or 5))
            step_ms = max(1, int(scroll.get("fling_step_ms") or 4))
            rows = 1
            detail = f"fling {direction}"
            scroll_meta = {
                "direction": direction,
                "mode": "fling",
                "row_fraction": row_fraction,
                "hold_end_ms": hold_end_ms,
                "settle_ms": settle_ms,
                "detect_settle_ms": int(scroll.get("detect_settle_ms") or 0),
                "drag_steps": drag_steps,
                "step_ms": step_ms,
                "object_id": listing.id if listing else None,
                "list_parent": listing.parent if listing else None,
            }
            self._emit_evidence(
                f"scroll_{direction}",
                "before",
                detail=detail,
                meta=self._grid_meta(extra=scroll_meta),
            )
            fling_list(
                hwnd=hwnd,
                rect=rect,
                direction=direction,
                nx=nx,
                ny=ny,
                drag_fraction=row_fraction,
                drag_steps=drag_steps,
                step_ms=step_ms,
                restore_cursor=False,
                stop=self.cancel_event,
            )
        else:
            rows = max(1, int(scroll.get("rows_per_key") or 1))
            row_fraction = float(scroll.get("drag_fraction") or scroll.get("row_fraction") or 0.15)
            hold_end_ms = int(scroll.get("hold_end_ms") or 450)
            settle_ms = max(30, int(scroll.get("settle_ms") or 80))
            drag_steps = max(2, int(scroll.get("drag_steps") or 6))
            step_ms = max(1, int(scroll.get("step_ms") or 8))
            detail = f"row {direction} ×{rows}"
            scroll_meta = {
                "direction": direction,
                "mode": "step",
                "rows_per_key": rows,
                "row_fraction": row_fraction,
                "hold_end_ms": hold_end_ms,
                "settle_ms": settle_ms,
                "detect_settle_ms": int(scroll.get("detect_settle_ms") or 0),
                "drag_steps": drag_steps,
                "step_ms": step_ms,
                "object_id": listing.id if listing else None,
                "list_parent": listing.parent if listing else None,
            }
            self._emit_evidence(
                f"scroll_{direction}",
                "before",
                detail=detail,
                meta=self._grid_meta(extra=scroll_meta),
            )
            for index in range(rows):
                if self.cancel_event.is_set():
                    break
                drag_list(
                    hwnd=hwnd,
                    rect=rect,
                    direction=direction,
                    nx=nx,
                    ny=ny,
                    drag_fraction=row_fraction,
                    hold_end_ms=hold_end_ms,
                    drag_steps=drag_steps,
                    step_ms=step_ms,
                    restore_cursor=False,
                    stop=self.cancel_event,
                )
                if settle_ms and index + 1 < rows and self._sleep_ms(settle_ms):
                    break

        if self.cancel_event.is_set():
            self._log(f"{'Fling' if mode_norm == 'fling' else 'Scroll'} {direction} interrupted", "warn")
            self._repaint("Interrupted")
            return

        if self._settle_before_detect(scroll, gesture_ms=settle_ms):
            self._log(f"{'Fling' if mode_norm == 'fling' else 'Scroll'} {direction} interrupted", "warn")
            self._repaint("Interrupted")
            return

        # Geometry + OCR identity. Fling-up may fall back to page-1 if OCR misses.
        identity_mode = "home" if (mode_norm == "fling" and direction == "up") else "ocr"
        detection = self._relayout_from_screen(
            rect,
            context=f"scroll-{direction}-{mode_norm}",
            identity=identity_mode,
        )
        after_meta = self._grid_meta(extra=scroll_meta)
        level = "ok" if detection.slots else "warn"
        label = "Fling" if mode_norm == "fling" else "Scroll"
        self._log(
            f"{label} {direction}"
            + ("" if mode_norm == "fling" else f" ×{rows}")
            + f" → {len(self.live_slots)} slots ({detection.reason})",
            level,
        )
        self._emit_evidence(
            f"scroll_{direction}",
            "after",
            detail=detail,
            meta=after_meta,
        )
        self._repaint(f"{label} {direction}")

    def _routine_steps(self, action: str) -> list[str]:
        assert self.playbook is not None
        for routine in self.playbook.routines:
            if routine.action == action:
                return list(routine.steps)
        object_map = self._object_map()
        button = object_map.button_for_action(action) if object_map is not None else None
        if button is not None:
            for effect in button.effects.get("ui") or []:
                if not isinstance(effect, dict) or effect.get("type") != "run_sequence":
                    continue
                raw_steps = effect.get("actions") or []
                if isinstance(raw_steps, list):
                    return [str(step).strip() for step in raw_steps if str(step).strip()]
        raise LiveControlError(f"no sequence for routine {action}")

    def _do_routine(self, action: str) -> None:
        """Run a named left-rail pack inline on this session (Esc / ` abort between steps)."""

        steps = self._routine_steps(action)
        if not steps:
            raise LiveControlError(f"routine {action} has no steps")
        object_map = self._object_map()
        button = object_map.button_for_action(action) if object_map is not None else None
        label = button.label if button is not None else action
        self._log(f"Routine → {label} ({len(steps)} steps)", "run")
        self._emit_evidence(
            action,
            "before",
            detail=label,
            meta={"object_id": button.id if button else None, "steps": steps},
            capture=False,
        )
        for index, step in enumerate(steps, start=1):
            if self.cancel_event.is_set():
                self._log(f"Routine {label} interrupted at step {index}/{len(steps)}", "warn")
                self._routine_remaining.clear()
                self._repaint("Routine interrupted")
                return
            if not is_actuation_action(step) or step.startswith("routine_"):
                raise LiveControlError(f"routine {action} has invalid step {step!r}")
            self._current_action = step
            self._routine_remaining = list(steps[index:])
            self._log(f"Routine {label}: {index}/{len(steps)} → {step}", "run")
            self._repaint(f"{label} · {index}/{len(steps)}")
            self._dispatch(step)
        self._routine_remaining.clear()
        self._emit_evidence(
            action,
            "after",
            detail=label,
            meta=self._grid_meta(extra={"object_id": button.id if button else None, "steps": steps}),
        )
        self._log(f"Routine ✔ {label}", "ok")
        self._repaint(f"Routine {label}")

    def _do_stat_collect(self) -> None:
        assert self.playbook is not None
        object_map = self._object_map()
        button = object_map.button_for_action("stat_collect") if object_map is not None else None
        event_id = str(self.playbook.stat_collect.get("event") or "stat_collect").strip()
        if button is not None:
            for effect in button.effects.get("world") or []:
                if isinstance(effect, dict) and effect.get("type") == "run_event" and effect.get("event"):
                    event_id = str(effect["event"]).strip()
                    break
        if self.run_event_once is not None:
            self._log(f"Stat collect → atom {event_id}", "run")
            self.run_event_once(event_id)
            self._emit_evidence(
                "stat_collect",
                "after",
                detail=event_id,
                meta={"event": event_id, "object_id": button.id if button else None},
                capture=False,
            )
            self._repaint("Stat collect started")
            return
        hwnd, rect = self._anchor_ready()
        if button is not None and button.hit is not None:
            nx, ny = button.hit
        else:
            stat = self.playbook.stat_collect
            nx = float(stat.get("nx") or 0.15)
            ny = float(stat.get("ny") or 0.09)
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        self._log("Stat collect fallback: currency HUD tap", "ok")
        self._emit_evidence(
            "stat_collect",
            "after",
            detail="currency HUD tap",
            meta={"object_id": button.id if button else None},
        )
        self._repaint("Currency HUD tapped")

    def _do_claim_gem(self) -> None:
        """Tap the timed diamond CLAIM tile (opportunistic — fine if absent)."""

        assert self.playbook is not None
        hwnd, rect = self._anchor_ready()
        object_map = self._object_map()
        button = object_map.button_for_action("claim_gem") if object_map is not None else None
        if button is not None and button.hit is not None:
            nx, ny = button.hit
        else:
            chrome = self.playbook.chrome
            nx = float(chrome.get("claim_badge_nx") or 0.20)
            ny = float(chrome.get("claim_badge_ny") or 0.50)
        self._emit_evidence(
            "claim_gem",
            "before",
            detail="tap",
            meta={"object_id": button.id if button else None, "nx": nx, "ny": ny},
        )
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        self._log(f"Claim diamonds → ({nx:.3f}, {ny:.3f})", "ok")
        self._emit_evidence(
            "claim_gem",
            "after",
            detail="tap",
            meta={"object_id": button.id if button else None, "nx": nx, "ny": ny},
        )
        self._repaint("Claim diamonds")

    def _do_refresh(self) -> None:
        """Re-read panel + buy grid from the current frame — no scroll / seek."""

        assert self.playbook is not None
        _hwnd, rect = self._anchor_ready()
        object_map = self._object_map()
        refresh_obj = object_map.button_for_action("refresh") if object_map is not None else None
        self._emit_evidence(
            "refresh",
            "before",
            detail="redetect",
            meta=self._grid_meta(extra={"object_id": refresh_obj.id if refresh_obj else None}),
        )
        self._log("Refresh → redetect panel + buy grid", "run")
        image = self._grab(rect)
        panel = detect_upgrade_panel(image)
        self.panel_open = bool(panel.panel_open)
        self.tab = panel.tab if panel.panel_open else None
        if self.panel_open:
            self._apply_detection(detect_buy_grid(image), context="refresh-redetect")
            self._bind_identity_from_image(image, context="refresh", fallback_home=False)
        else:
            self.live_slots = ()
            self.aligned = True
            self._last_detection = None
            self._forget_identity("refresh-closed")
        detail = panel.reason
        if self.panel_open and self._last_detection is not None:
            detail = f"{panel.reason}; {self._last_detection.reason}"
        self._log(f"Refresh done — {detail}", "ok" if self.aligned or not self.panel_open else "warn")
        self._emit_evidence(
            "refresh",
            "after",
            detail=detail,
            meta=self._grid_meta(
                extra={
                    "panel_reason": panel.reason,
                    "object_id": refresh_obj.id if refresh_obj else None,
                    "mode": "redetect",
                }
            ),
        )
        self._repaint(f"Redetect · {detail}")

    def _repaint(self, status: str) -> None:
        if not self.active or self.playbook is None:
            return
        # Worker threads must not touch Tk — marshal to the UI queue.
        if self.post_event is not None and threading.current_thread() is not self._ui_thread:
            try:
                self.post_event(("live_control_repaint", status))
            except Exception as exc:  # noqa: BLE001
                self._log(f"Live Control repaint queue failed: {exc}", "warn")
            return
        self._repaint_now(status)

    def repaint_now(self, status: str = "") -> None:
        """UI-thread paint of current/queue/toggle focus colors."""

        self._repaint_now(status)

    def _repaint_now(self, status: str) -> None:
        if not self.active or self.playbook is None:
            return
        _title, _hwnd, rect = self.get_anchor()
        if rect is None:
            self.exit(reason="anchor-lost")
            return
        state = LiveControlOverlayState(
            panel_open=self.panel_open,
            tab=self.tab,
            aligned=self.aligned,
            status=status,
            surface_ok=True,
            live_slots=self.live_slots,
            show_descriptors=self.show_descriptors,
            paused=self.paused,
            toggled_action=self._toggled_action,
            current_action=self._current_action,
            queued_actions=self._visible_queue(),
            slot_labels={b.slot_index: b.display_label for b in self.identity.bindings},
            identity_known=self.identity.known,
        )
        self.overlay.show(self.playbook, rect, state)
        self._sync_molecule_marks(rect)
