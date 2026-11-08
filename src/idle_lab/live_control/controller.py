"""Live Control Overlay session: playbook overlay + keyboard actuation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from idle_lab.ai_batch.panel_detect import detect_upgrade_panel
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.automations.tower_nav import click_normalized, drag_list, fling_list, seek_list_top
from idle_lab.humanize import HumanizeProfile
from idle_lab.live_control.buy_detect import BuyGridDetection, DetectedBuySlot, detect_buy_grid
from idle_lab.live_control.overlay import LiveControlOverlay, LiveControlOverlayState
from idle_lab.live_control.playbook import LiveControlPlaybook, PlaybookError, default_playbook_path, load_playbook
from idle_lab.models import Rect


LogFn = Callable[[str, str], None]
AnchorFn = Callable[[], tuple[str | None, int | None, Rect | None]]
HumanizeFn = Callable[[], HumanizeProfile]
RunEventFn = Callable[[str], None]
EvidenceFn = Callable[..., None]
PostEventFn = Callable[[tuple], None]
LegendFn = Callable[[bool], None]
PauseFn = Callable[[bool], None]


class LiveControlError(RuntimeError):
    """Live Control Overlay refused to start or act."""


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
        overlay: LiveControlOverlay,
        project_root: Path,
        get_anchor: AnchorFn,
        get_humanize: HumanizeFn | None = None,
        run_event_once: RunEventFn | None = None,
        on_evidence: EvidenceFn | None = None,
        post_event: PostEventFn | None = None,
        on_legend_change: LegendFn | None = None,
        on_pause_change: PauseFn | None = None,
        log: LogFn | None = None,
        restore_cursor: bool = True,
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
        self._log = log or (lambda _m, _l="info": None)
        self.restore_cursor = False
        self._settings_restore_cursor = restore_cursor
        self.active = False
        self.evidence = False
        self.paused = False
        self.show_hotkeys = False
        self.playbook: LiveControlPlaybook | None = None
        self.panel_open = False
        self.tab: str | None = None
        self.aligned = True
        self.live_slots: tuple[DetectedBuySlot, ...] = ()
        self._busy = False
        self._lock = threading.Lock()
        self._last_detection: BuyGridDetection | None = None

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
        self.show_hotkeys = False
        self.active = True
        self._notify_legend()
        self._notify_pause()
        if self.panel_open:
            self._apply_detection(detect_buy_grid(image), context="enter")
        else:
            self.live_slots = ()
            self.aligned = True
            self._last_detection = None
        mode = "troubleshoot" if self.evidence else "play"
        map_note = " · object map" if playbook.object_map is not None else ""
        self._log(
            f"Live Control ON ({mode}) · {playbook.title}{map_note} · "
            f"panel={'open:' + (self.tab or '?') if self.panel_open else 'closed'} "
            f"({panel.reason})",
            "run",
        )
        self._repaint(f"Live Control · {panel.reason}")
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
        self.active = False
        self.evidence = False
        self.paused = False
        self.show_hotkeys = False
        self.overlay.hide()
        self._log(f"Live Control OFF ({reason})", "warn")
        self.playbook = None
        self.panel_open = False
        self.tab = None
        self.aligned = True
        self.live_slots = ()
        self._last_detection = None
        self._notify_legend()
        self._notify_pause()

    def handle_token(self, token: str) -> bool:
        """Compatibility: treat as a key-down (fire immediately)."""

        return self.handle_key(token, phase="down")

    def handle_key(self, token: str, *, phase: str = "down") -> bool:
        if not self.active or self.playbook is None:
            return False
        action = self.playbook.action_for_token(token)
        if action is None:
            return False
        if phase != "down":
            return True
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return True
        return self._run_action(action)

    def toggle_pause(self) -> bool:
        """Backtick: gray out / re-arm LCO without exiting the session."""

        if not self.active:
            return False
        self.paused = not self.paused
        if self.paused:
            self._log("Live Control paused — marks inert. ` resumes · Esc exits.", "warn")
            self._repaint("Paused")
        else:
            self._log("Live Control resumed.", "ok")
            self._repaint("Resumed")
        self._notify_pause()
        return True

    def _run_action(self, action: str) -> bool:
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return True
        if self._busy:
            self._log("Live Control busy — wait for current action.", "warn")
            return True
        try:
            self._busy = True
            self._dispatch(action)
        except LiveControlError as exc:
            self._log(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control action failed: {exc}", "error")
        finally:
            self._busy = False
        return True

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
        elif action == "refresh":
            self._do_refresh()
        elif action == "toggle_legend":
            self._toggle_legend()
        else:
            raise LiveControlError(f"unknown Live Control action: {action}")

    def _notify_legend(self) -> None:
        if self.on_legend_change is None:
            return
        try:
            self.on_legend_change(bool(self.show_hotkeys))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control legend notify failed: {exc}", "warn")

    def _notify_pause(self) -> None:
        if self.on_pause_change is None:
            return
        try:
            self.on_pause_change(bool(self.paused))
        except Exception as exc:  # noqa: BLE001
            self._log(f"Live Control pause notify failed: {exc}", "warn")

    def _toggle_legend(self) -> None:
        if self.paused:
            self._log("Live Control paused — press ` to resume.", "warn")
            return
        self.show_hotkeys = not self.show_hotkeys
        mode = "hotkeys" if self.show_hotkeys else "icons"
        self._log(f"Legend → {mode}", "ok")
        self._notify_legend()
        self._repaint(f"Legend · {mode}")

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
        }
        if extra:
            meta.update(extra)
        return meta

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

    def _relayout_from_screen(self, rect: Rect, *, context: str) -> BuyGridDetection:
        image = self._grab(rect)
        detection = detect_buy_grid(image)
        self._apply_detection(detection, context=context)
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
        """Re-home list to first page so buy 1–6 match playbook labels."""

        assert self.playbook is not None
        look_for = self._seek_look_for(tab)
        scroll = self._scroll_params(tab)
        self._log(f"Tab home → seek top ({look_for or 'edge'})", "run")
        seek_list_top(
            hwnd=hwnd,
            rect=rect,
            look_for=look_for,
            drag_fraction=float(scroll.get("drag_fraction") or 0.10),
            hold_end_ms=int(scroll.get("hold_end_ms") or 350),
            settle_ms=max(200, int(scroll.get("settle_ms") or 450)),
            settle_confirm_ms=200,
            restore_cursor=False,
            log=self._log,
        )

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
            self._relayout_from_screen(rect, context="retab")
            self._emit_evidence(
                f"tab_{tab}",
                "after",
                detail=f"retab {label}",
                meta=self._grid_meta(extra={"retap": True, "object_id": tab_obj.id if tab_obj else None}),
            )
            self._repaint(f"Already on {label}")
            return
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        time.sleep(0.20)
        self.panel_open = True
        self.tab = tab
        # Game remembers per-tab scroll; re-home so 1–6 match page-1 labels.
        self._seek_tab_top(hwnd=hwnd, rect=rect, tab=tab)
        self._relayout_from_screen(rect, context="tab")
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
        label = f"Buy {index}"
        object_id: str | None = None
        object_map = self._object_map()
        if self.tab and object_map is not None:
            buy = object_map.buy_button(self.tab, index)
            if buy is not None:
                label = buy.label
                object_id = buy.id
        if self.tab and object_id is None:
            match = next((s for s in self.playbook.buy_slots(self.tab) if s.index == index), None)
            if match is not None:
                label = match.label
        if self.live_slots:
            for slot in self.live_slots:
                if slot.index == index:
                    return slot.nx, slot.ny, label, object_id
            raise LiveControlError(f"slot {index} not visible (detected {len(self.live_slots)})")
        slots = self.playbook.buy_slots(self.tab)
        slot = next((s for s in slots if s.index == index), None)
        if slot is None:
            raise LiveControlError(f"no buy slot {index}")
        return slot.nx, slot.ny, slot.label, object_id

    def _do_buy(self, index: int) -> None:
        assert self.playbook is not None
        if not self.panel_open or not self.tab:
            raise LiveControlError("Open an upgrade tab first (Q/W/E).")
        if not self.aligned:
            self._log("Buy with unsure geometry (amber) — still clicking.", "warn")
        nx, ny, label, object_id = self._slot_for_index(index)
        object_map = self._object_map()
        buy_obj = object_map.buy_button(self.tab, index) if object_map is not None else None
        effects = buy_obj.effects if buy_obj is not None else {}
        hwnd, rect = self._anchor_ready()
        self._click(hwnd=hwnd, rect=rect, nx=nx, ny=ny)
        self._log(f"Buy {index} {label}", "ok")
        self._emit_evidence(
            f"buy_{index}",
            "after",
            detail=label,
            meta=self._grid_meta(
                extra={
                    "nx": nx,
                    "ny": ny,
                    "label": label,
                    "object_id": object_id or (buy_obj.id if buy_obj else None),
                    "effects": effects,
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
            settle_ms = max(200, int(scroll.get("fling_settle_ms") or scroll.get("settle_ms") or 700))
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
            )
        else:
            rows = max(1, int(scroll.get("rows_per_key") or 1))
            row_fraction = float(scroll.get("drag_fraction") or scroll.get("row_fraction") or 0.15)
            hold_end_ms = int(scroll.get("hold_end_ms") or 280)
            settle_ms = max(0, int(scroll.get("settle_ms") or 400))
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
                )
                if settle_ms and index + 1 < rows:
                    time.sleep(settle_ms / 1000.0)

        if settle_ms:
            time.sleep(settle_ms / 1000.0)

        detection = self._relayout_from_screen(rect, context=f"scroll-{direction}-{mode_norm}")
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
        else:
            self.live_slots = ()
            self.aligned = True
            self._last_detection = None
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
            show_hotkeys=self.show_hotkeys,
            paused=self.paused,
        )
        self.overlay.show(self.playbook, rect, state)
