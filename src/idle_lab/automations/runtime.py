"""Execute automation events on a worker thread."""

from __future__ import annotations

import queue
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from idle_lab.automations.capture import CaptureError, crop_roi, grab_anchor, save_screenshot
from idle_lab.automations.collections_runner import run_collection
from idle_lab.automations.csv_log import append_run_row
from idle_lab.automations.decide import decide_ab_with_reason
from idle_lab.automations.ocr import OcrError, ocr_field
from idle_lab.tool_export import ToolExportError, load_tool_export
from idle_lab.automations.scheduler import Scheduler
from idle_lab.automations.schema import Event, Roi
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.template_match import (
    TemplateMatchError,
    match_template,
    resolve_template_path,
)
from idle_lab.automations.tower_nav import (
    BUY_CLICK,
    TAB_CLICK,
    check_list_top,
    click_normalized,
    drag_list,
    observe_panel,
    panel_status_vars,
    seek_list_top,
)
from idle_lab.click_foreground import foreground_drag
from idle_lab import win32_api
from idle_lab.automations.video import VideoError, clip_name, record_clip
from idle_lab.evidence import write_failure_pack
from idle_lab.humanize import HumanizeProfile, interruptible_sleep
from idle_lab.lab_mode import SuperviseGate
from idle_lab.live_control.controller import LiveControlController, LiveControlError, NullOverlay
from idle_lab.models import Rect, normalized_to_screen
from idle_lab.trace_log import TraceLog


LogFn = Callable[[str, str], None]  # message, level
AnchorFn = Callable[[], Rect | None]
AnchorHwndFn = Callable[[], tuple[int | None, Rect | None]]
HumanizeFn = Callable[[], HumanizeProfile]


@dataclass
class RuntimeState:
    variables: dict[str, Any] = field(default_factory=dict)
    last_image: Any = None
    last_screenshot_path: Path | None = None
    states: dict[str, bool] = field(default_factory=dict)


class AutomationRuntime:
    def __init__(
        self,
        *,
        store: AutomationStore,
        runs_dir: Path,
        get_anchor_rect: AnchorFn,
        play_preset: Callable[[str], None] | None = None,
        get_anchor_hwnd: AnchorHwndFn | None = None,
        get_humanize: HumanizeFn | None = None,
        restore_cursor: bool = True,
        events_out: queue.Queue | None = None,
        supervise_gate: SuperviseGate | None = None,
        trace_level: str = "failure",
        templates_dir: Path | None = None,
        shared_lco: LiveControlController | None = None,
    ) -> None:
        self.store = store
        self.runs_dir = Path(runs_dir)
        self.get_anchor_rect = get_anchor_rect
        self.get_anchor_hwnd = get_anchor_hwnd
        self.get_humanize = get_humanize
        self.restore_cursor = restore_cursor
        self.play_preset = play_preset
        self.events_out: queue.Queue = events_out or queue.Queue()
        self.scheduler = Scheduler()
        self.state = RuntimeState()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = False
        self.supervise_gate = supervise_gate or SuperviseGate()
        self.trace = TraceLog(self.runs_dir, level=trace_level)
        self.templates_dir = Path(templates_dir) if templates_dir else self.runs_dir.parent / "automations" / "templates"
        self._current_event_id: str | None = None
        self._action_index: int = 0
        self._run_event_stack: list[str] = []
        self._collection_thread: threading.Thread | None = None
        self._session_events: list[Event] | None = None
        self._lco: LiveControlController | None = None
        # When the flight-deck LCO is already up, reuse it (no second enter/OCR).
        self._shared_lco = shared_lco

    def emit(self, kind: str, **payload: Any) -> None:
        self.events_out.put({"kind": kind, **payload})

    def log(self, message: str, level: str = "info") -> None:
        self.emit("console", message=message, level=level)

    @property
    def is_running(self) -> bool:
        return bool(self._enabled and self._thread is not None and self._thread.is_alive())

    def start(self, event_ids: list[str] | None = None) -> None:
        """Start the interval scheduler.

        ``event_ids`` — if set, only those events run (selection), even if
        ``enabled`` is false in JSON. If omitted, every file-``enabled`` event runs.
        """

        if self._thread and self._thread.is_alive():
            return
        if self.collection_running:
            raise RuntimeError("stop the collection pack before starting interval Loops")
        self._stop.clear()
        self._enabled = True
        self.trace.configure(run_number=self.store.runtime.run_number)
        if event_ids:
            wanted = {eid.strip() for eid in event_ids if eid and eid.strip()}
            selected = [self.store.events[eid] for eid in wanted if eid in self.store.events]
            missing = sorted(wanted - set(self.store.events))
            if missing:
                raise KeyError(f"unknown event id(s): {', '.join(missing)}")
            if not selected:
                raise RuntimeError("no events to start")
            # Clone with enabled=True so the scheduler accepts them for this session.
            session_events = [
                Event(
                    id=event.id,
                    title=event.title,
                    priority=event.priority,
                    every_ms=event.every_ms,
                    actions=list(event.actions),
                    enabled=True,
                    version=event.version,
                    description=event.description,
                    notes=event.notes,
                    overdue_policy=event.overdue_policy,
                    path=event.path,
                )
                for event in selected
            ]
            self._session_events = session_events
            self.scheduler.reset(session_events)
            labels = ", ".join(event.id for event in session_events)
            self.log(f"Automations runtime started (selection): {labels}", "ok")
        else:
            self._session_events = None
            self.scheduler.reset(list(self.store.events.values()))
            self.log("Automations runtime started (all file-enabled events).", "ok")
        self._thread = threading.Thread(target=self._loop, name="idle-lab-automations", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._enabled = False
        self._stop.set()
        # Never tear down the interactive overlay LCO from here — only our private session.
        if self._lco is not None and self._lco is not self._shared_lco:
            self._lco.interrupt()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        coll = self._collection_thread
        if coll and coll.is_alive():
            coll.join(timeout=2.0)
        self._collection_thread = None
        if self._lco is self._shared_lco:
            self._lco = None
        self.log("Automations runtime stopped.", "warn")

    def attach_shared_lco(self, controller: LiveControlController | None) -> None:
        """Point atom LCO actions at the flight-deck overlay session when present."""

        self._shared_lco = controller

    def reload_schedule(self) -> None:
        self.scheduler.reset(list(self.store.events.values()))
        self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])
        self.log("Scheduler reloaded from files.", "ok")

    def operator_snapshot(self) -> dict[str, Any]:
        """For Activity honesty: running / blocked / deferred summary."""

        active = self.scheduler.active_id
        deferred = self.scheduler.deferred_summary()
        if not self.is_running and not (self._collection_thread and self._collection_thread.is_alive()):
            return {"phase": "idle", "detail": "", "blocking_id": None, "deferred_summary": ""}
        if active:
            detail = f"running {active}"
            if deferred:
                detail += f" · deferred: {deferred}"
            return {
                "phase": "blocked" if deferred else "running",
                "detail": detail,
                "blocking_id": active,
                "deferred_summary": deferred,
            }
        if self._collection_thread and self._collection_thread.is_alive():
            return {
                "phase": "running",
                "detail": "collection runner",
                "blocking_id": "collection",
                "deferred_summary": deferred,
            }
        return {
            "phase": "running",
            "detail": "scheduler idle tick",
            "blocking_id": None,
            "deferred_summary": deferred,
        }

    def run_event_once(self, event_id: str) -> None:
        """Run one atom's actions immediately (no interval wait). Exclusive runway."""

        event = self.store.events.get(event_id)
        if event is None:
            raise KeyError(f"unknown event: {event_id}")
        if self._collection_thread and self._collection_thread.is_alive():
            raise RuntimeError("stop the running atom/molecule job first")
        if self.is_running:
            raise RuntimeError("stop interval Loops before running an atom once (single mouse runway)")

        self._stop.clear()
        self.trace.configure(run_number=self.store.runtime.run_number)

        def worker() -> None:
            try:
                self._run_event(event)
            except Exception as exc:  # noqa: BLE001
                self.log(f"atom {event_id} failed: {exc}", "error")
                self._write_failure(str(exc), meta={"event_id": event_id})
                self.log(traceback.format_exc(), "error")
            finally:
                self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])

        self._collection_thread = threading.Thread(
            target=worker, name=f"idle-lab-atom-once-{event_id}", daemon=True
        )
        self._collection_thread.start()
        self.log(f"Atom once started: {event_id}", "ok")

    def start_collection(self, collection_id: str, *, lco_pack: bool = False) -> None:
        """Run a once-molecule on a worker thread (exclusive with interval loop ownership).

        ``lco_pack`` — when the interactive overlay is up, paint queue/focus like key chords.
        """

        collection = self.store.collections.get(collection_id)
        if collection is None:
            raise KeyError(f"unknown collection: {collection_id}")
        if self._collection_thread and self._collection_thread.is_alive():
            raise RuntimeError("a collection is already running")
        if self.is_running:
            # Interval loop owns the runway — stop it first or refuse.
            raise RuntimeError("stop interval Loops before starting a collection (single mouse runway)")

        self._stop.clear()
        self.trace.configure(run_number=self.store.runtime.run_number)
        pack_armed = False
        if lco_pack:
            shared = self._shared_lco
            if shared is not None and shared.active:
                from idle_lab.automations.lco_focus import preview_molecule_focus_actions

                steps = preview_molecule_focus_actions(collection, self.store)
                shared.begin_external_pack(collection.title or collection_id, steps)
                pack_armed = True

        def worker() -> None:
            try:
                run_collection(
                    collection,
                    store=self.store,
                    variables=self.state.variables,
                    states=self.state.states,
                    run_event=self._run_event,
                    log=self.log,
                    should_abort=self._stop.is_set,
                )
            except Exception as exc:  # noqa: BLE001
                self.log(f"collection {collection_id} failed: {exc}", "error")
                self._write_failure(str(exc), meta={"collection_id": collection_id})
                self.log(traceback.format_exc(), "error")
            finally:
                if pack_armed:
                    shared = self._shared_lco
                    if shared is not None:
                        try:
                            reason = "stopped" if self._stop.is_set() else "done"
                            shared.end_external_pack(reason=reason)
                        except Exception:  # noqa: BLE001
                            pass
                self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])

        self._collection_thread = threading.Thread(
            target=worker, name=f"idle-lab-collection-{collection_id}", daemon=True
        )
        self._collection_thread.start()
        self.log(f"Collection runner started: {collection_id}", "ok")

    @property
    def collection_running(self) -> bool:
        return bool(self._collection_thread and self._collection_thread.is_alive())
    def _profile(self) -> HumanizeProfile:
        if self.get_humanize is not None:
            return self.get_humanize()
        return HumanizeProfile.from_level("medium")

    def _anchor(self) -> tuple[int | None, Rect | None]:
        if self.get_anchor_hwnd is not None:
            return self.get_anchor_hwnd()
        return None, self.get_anchor_rect()

    def _loop_events(self) -> list[Event]:
        if self._session_events is not None:
            return list(self._session_events)
        return [event for event in self.store.events.values() if event.enabled]

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self._enabled:
                time.sleep(0.1)
                continue
            events = self._loop_events()
            chosen = self.scheduler.pick_due(events)
            self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])
            if chosen is None:
                time.sleep(0.1)
                continue
            self.scheduler.mark_running(chosen)
            self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])
            if any(action.type == "record_clip" for action in chosen.actions):
                self.log(
                    f"scheduled recording ({chosen.id}) — priority {chosen.priority}; lower events deferred",
                    "warn",
                )
            for skip_msg in self.scheduler.take_skip_messages():
                self.log(skip_msg, "warn")
            try:
                self._run_event(chosen)
            except Exception as exc:  # noqa: BLE001
                self.log(f"event {chosen.id} failed: {exc}", "error")
                pack = self._write_failure(
                    str(exc),
                    meta={
                        "event_id": chosen.id,
                        "action_index": self._action_index,
                        "variables": dict(self.state.variables),
                    },
                )
                if pack is not None:
                    self.log(f"failure pack: {pack}", "warn")
                self.trace.append(
                    {
                        "source": "loops",
                        "event_id": chosen.id,
                        "action_index": self._action_index,
                        "ok": False,
                        "error": str(exc),
                        "failure_pack": str(pack) if pack else None,
                    },
                    is_failure=True,
                )
                message = str(exc).lower()
                if not any(
                    tip in message
                    for tip in (
                        "tesseract",
                        "ffmpeg",
                        "anchor missing",
                        "not found on path",
                        "not installed",
                        "opencv",
                    )
                ):
                    self.log(traceback.format_exc(), "error")
            finally:
                self.scheduler.mark_finished(chosen, events)
                self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])

    def _write_failure(self, error: str, *, meta: dict[str, Any]) -> Path | None:
        try:
            return write_failure_pack(
                self.runs_dir,
                error=error,
                meta=meta,
                window_image=self.state.last_image,
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"could not write failure pack: {exc}", "warn")
            return None

    def _supervise(self, description: str) -> bool:
        ok = self.supervise_gate.request(description, stop=self._stop)
        if not ok:
            self.log(f"supervised: declined/stopped — {description}", "warn")
        return ok

    def _run_event(self, event: Event) -> None:
        if event.id in self._run_event_stack:
            cycle = " → ".join([*self._run_event_stack, event.id])
            raise RuntimeError(f"run_event cycle detected: {cycle}")
        prev_id = self._current_event_id
        prev_index = self._action_index
        self._run_event_stack.append(event.id)
        self._current_event_id = event.id
        self._action_index = 0
        nested = len(self._run_event_stack) > 1
        prefix = "↳ " if nested else "▶ "
        self.log(f"{prefix}{event.title} ({event.id})", "run")
        self.trace.append(
            {"source": "loops", "event_id": event.id, "action_type": "event_start", "ok": True},
            is_failure=False,
        )
        # Non-LCO atoms (Stat collect) inside an LCO molecule pack: light the V mark.
        # Skip when the keyboard path already owns focus (V key → run_event_once).
        focus_token: str | None = None
        shared = self._shared_lco
        if shared is not None and shared.active and getattr(shared, "_pack_label", None):
            from idle_lab.automations.lco_focus import focus_token_for_event

            focus_token = focus_token_for_event(event, self.store)
            if focus_token:
                try:
                    shared.claim_external_focus(focus_token)
                    shared.console.event(f"action {focus_token} · atom {event.id}")
                    shared.console.result(f"{focus_token} → {event.title}")
                except Exception:  # noqa: BLE001
                    focus_token = None
        try:
            for index, action in enumerate(event.actions):
                if self._stop.is_set():
                    self.log(f"event {event.id} interrupted", "warn")
                    break
                self._action_index = index
                self._dispatch(action.raw)
            self.log(f"✔ finished {event.id}", "ok")
            if focus_token and shared is not None and shared.active:
                try:
                    shared.console.result(f"{focus_token} ✔ {event.title}")
                except Exception:  # noqa: BLE001
                    pass
        finally:
            if focus_token and shared is not None:
                try:
                    shared.clear_external_focus()
                except Exception:  # noqa: BLE001
                    pass
            self._run_event_stack.pop()
            self._current_event_id = prev_id
            self._action_index = prev_index
            if (
                not self._run_event_stack
                and self._lco is not None
                and self._lco.active
                and self._lco is not self._shared_lco
            ):
                self._lco.exit(reason="atom finished")

    def _action_run_event(self, raw: dict[str, Any]) -> None:
        event_id = str(raw.get("event") or raw.get("id") or "").strip()
        if not event_id:
            raise ValueError("run_event requires event id")
        event = self.store.events.get(event_id)
        if event is None:
            raise KeyError(f"unknown event: {event_id}")
        self._run_event(event)

    def _dispatch(self, raw: dict[str, Any]) -> None:
        action_type = raw.get("type")
        if action_type == "decide":
            branch_actions = self._action_decide(raw)
            if branch_actions:
                for nested in branch_actions:
                    nested_raw = nested if isinstance(nested, dict) else nested.raw
                    self._dispatch(nested_raw)
            return
        handlers = {
            "screenshot": self._action_screenshot,
            "ocr": self._action_ocr,
            "tool_export": self._action_tool_export,
            "mouse": self._action_play_preset,
            "play_preset": self._action_play_preset,
            "record_clip": self._action_record_clip,
            "csv_append": self._action_csv_append,
            "log": self._action_log,
            "set_variable": self._action_set_variable,
            "wait": self._action_wait,
            "wait_until": self._action_wait_until,
            "click": self._action_click,
            "drag": self._action_drag,
            "key": self._action_key,
            "detect_panel": self._action_detect_panel,
            "ensure_upgrade_tab": self._action_ensure_upgrade_tab,
            "scroll_list": self._action_scroll_list,
            "seek_list_top": self._action_seek_list_top,
            "match_template": self._action_match_template,
            "run_event": self._action_run_event,
            "lco": self._action_lco,
        }
        handler = handlers.get(str(action_type))
        if handler is None:
            self.log(f"unknown action type: {action_type}", "error")
            return
        try:
            handler(raw)
            self.trace.append(
                {
                    "source": "loops",
                    "event_id": self._current_event_id,
                    "action_index": self._action_index,
                    "action_type": action_type,
                    "ok": True,
                },
                is_failure=False,
            )
        except Exception:
            self.trace.append(
                {
                    "source": "loops",
                    "event_id": self._current_event_id,
                    "action_index": self._action_index,
                    "action_type": action_type,
                    "ok": False,
                },
                is_failure=True,
            )
            raise

    def _fresh_image(self, rect: Rect | None = None) -> Any:
        anchor = rect if rect is not None else self.get_anchor_rect()
        image = grab_anchor(anchor)
        self.state.last_image = image
        self.state.states["capture_failed"] = False
        self.state.states["anchor_missing"] = anchor is None
        return image

    def _action_screenshot(self, raw: dict[str, Any]) -> None:
        rect = self.get_anchor_rect()
        self.state.states["anchor_missing"] = rect is None
        try:
            image = grab_anchor(rect)
        except CaptureError as exc:
            self.state.states["capture_failed"] = True
            self.state.last_image = None
            raise CaptureError(str(exc)) from exc
        self.state.states["capture_failed"] = False
        self.state.last_image = image
        prefix = str(raw.get("prefix") or "shot")
        path = save_screenshot(image, self.runs_dir / "screenshots", prefix=prefix)
        self.state.last_screenshot_path = path
        self.state.variables["last_screenshot"] = str(path)
        self.log(f"screenshot saved {path}", "ok")

    def _action_ocr(self, raw: dict[str, Any]) -> None:
        roi_id = str(raw.get("roi") or "")
        variable = str(raw.get("variable") or roi_id or "ocr")
        parse_as = str(raw.get("parse_as") or "raw")
        roi = self.store.rois.get(roi_id) if roi_id else None
        if roi is None and all(k in raw for k in ("nx", "ny", "nw", "nh")):
            roi = Roi(
                id=roi_id or f"inline_{variable}",
                nx=float(raw["nx"]),
                ny=float(raw["ny"]),
                nw=float(raw["nw"]),
                nh=float(raw["nh"]),
                version=1,
                notes="inline Atom Create ROI",
                path=None,
            )
        if roi is None:
            raise OcrError(f"unknown roi: {roi_id or '(missing inline nx/ny/nw/nh)'}")
        rect = self.get_anchor_rect()
        if rect is None:
            self.state.states["anchor_missing"] = True
            raise CaptureError("anchor missing")
        image = self.state.last_image
        if image is None:
            image = grab_anchor(rect)
            self.state.last_image = image
        cropped = crop_roi(image, rect, roi)
        result = ocr_field(cropped, parse_as=parse_as)
        self.state.variables[f"{variable}_raw"] = result.observation
        self.state.variables[variable] = result.inference
        if parse_as == "wave":
            self.state.states["wave_readable"] = bool(result.inference)
            self.state.variables["wave_number"] = result.inference or self.state.variables.get("wave_number", "xx")
        if parse_as == "signal":
            self.state.states["signal_a_vs_b"] = result.inference in {"A", "B"}
        if parse_as == "game_over":
            self.state.states["game_over"] = result.inference == "GAME_OVER"
            self.state.variables["game_over"] = result.inference
        if parse_as == "presence":
            self.state.states[f"{variable}_present"] = result.inference == "PRESENT"
        label = roi_id or f"inline({roi.nx:.2f},{roi.ny:.2f})"
        self.log(
            f"OCR {label}: observation={result.observation!r} inference={result.inference!r} → {variable}",
            "info",
        )

    def _action_tool_export(self, raw: dict[str, Any]) -> None:
        """Load Tower tool_export into variables (Rend cache by default). No clicks / OCR."""

        path = raw.get("path")
        path_arg = str(path).strip() if path not in (None, "") else None
        field_map = raw.get("map") or raw.get("fields")
        mapping = None
        if isinstance(field_map, dict):
            mapping = {
                str(k).strip(): str(v).strip()
                for k, v in field_map.items()
                if str(k).strip() and str(v).strip()
            }
        max_age = raw.get("max_age_s")
        max_age_s = float(max_age) if max_age not in (None, "") else None
        try:
            snap = load_tool_export(path_arg, field_map=mapping, max_age_s=max_age_s)
        except ToolExportError as exc:
            self.state.states["tool_export_ok"] = False
            self.state.variables["tool_export_ok"] = "false"
            self.log(str(exc), "error")
            raise
        self.state.states["tool_export_ok"] = True
        self.state.variables["tool_export_ok"] = "true"
        self.state.states["wave_readable"] = bool(snap.variables.get("wave_number"))
        for key, value in snap.variables.items():
            self.state.variables[key] = value
        wave = snap.variables.get("wave_number")
        if wave not in (None, ""):
            self.state.variables["wave_number"] = wave
        round_active = str(snap.variables.get("round_active") or "").lower()
        self.state.states["round_active"] = round_active in {"true", "1", "yes"}
        self.log(
            f"tool_export {snap.path.name} age={snap.age_s:.1f}s "
            f"wave={snap.variables.get('wave_number')!r} "
            f"coins={snap.variables.get('coins')!r} "
            f"gems={snap.variables.get('gems')!r} "
            f"tier={snap.variables.get('tier')!r}",
            "ok",
        )

    def _action_decide(self, raw: dict[str, Any]) -> list[dict[str, Any]] | None:
        variable = str(raw.get("variable") or "signal")
        value = self.state.variables.get(variable)
        raw_key = f"{variable}_raw"
        raw_obs = self.state.variables.get(raw_key)
        match_a = str(raw.get("match_a") or "A")
        mode = str(raw.get("mode") or "contains")
        explain_a = str(raw.get("explain_a") or "run on_a actions")
        explain_b = str(raw.get("explain_b") or "run on_b actions")
        branch, reason = decide_ab_with_reason(value, match_a=match_a, mode=mode)
        self.state.variables["branch"] = branch
        self.log("── A/B decision ──", "info")
        self.log(
            f"saw OCR raw={raw_obs!r} → parsed {variable}={value!r}",
            "info",
        )
        self.log(
            f"rule: if {variable} {mode} {match_a!r} → PATH A, else → PATH B",
            "info",
        )
        self.log(reason, "ok")
        if branch == "A":
            self.log(f"PATH A does: {explain_a}", "run")
            return list(raw.get("on_a") or [])
        self.log(f"PATH B does: {explain_b}", "run")
        return list(raw.get("on_b") or [])

    def _action_play_preset(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("preset") or raw.get("name") or "")
        if not name:
            self.log("play_preset missing preset name", "error")
            return
        if not self._supervise(f"Play preset {name!r}"):
            return
        if self.play_preset is None:
            self.log(f"play_preset stub: would run {name!r}", "warn")
            return
        self.log(f"action: play preset {name!r}", "run")
        self.play_preset(name)
        self.log(f"finished preset {name!r}", "ok")

    def _action_record_clip(self, raw: dict[str, Any]) -> None:
        from datetime import datetime

        rect = self.get_anchor_rect()
        if rect is None:
            raise VideoError("anchor missing")
        duration_s = float(raw.get("duration_s") or 10)
        run_number = self.store.runtime.run_number
        wave = self.state.variables.get("wave_number") or "xx"
        kind = str(raw.get("kind") or raw.get("name_prefix") or "").strip()
        # Stamp b-roll (and any kinded clip) so same-wave repeats do not overwrite.
        stamp = ""
        if kind or bool(raw.get("stamp", False)):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = clip_name(run_number, wave, kind=kind, stamp=stamp)
        dest = self.runs_dir / "clips" / f"{name}.mp4"
        self.log(f"recording clip {dest.name} ({duration_s:.0f}s)…", "warn")
        record_clip(rect, dest, duration_s=duration_s, should_abort=self._stop.is_set)
        self.state.variables["last_clip"] = str(dest)
        self.state.variables["clip_name"] = dest.name
        self.state.variables["clip_duration_s"] = str(int(duration_s) if duration_s == int(duration_s) else duration_s)
        self.state.variables["clip_kind"] = kind or "clip"
        self.log(f"clip saved {dest}", "ok")

    def _action_csv_append(self, raw: dict[str, Any]) -> None:
        path_name = str(raw.get("path") or "run_log.csv")
        path = self.runs_dir / path_name
        run_number = self.store.runtime.run_number
        wave = self.state.variables.get("wave_number") or "xx"
        extras: dict[str, Any] = {}
        fields = raw.get("fields")
        if isinstance(fields, list):
            for field_name in fields:
                if not isinstance(field_name, str) or not field_name.strip():
                    continue
                key = field_name.strip()
                if key in {"datetime", "run_number", "wave_number"}:
                    continue
                extras[key] = self.state.variables.get(key, "")
        row = append_run_row(path, run_number=run_number, wave_number=wave, extras=extras or None)
        self.log(f"csv append {path.name}: {row}", "ok")

    def _action_log(self, raw: dict[str, Any]) -> None:
        message = str(raw.get("message") or "")
        level = str(raw.get("level") or "info")
        for key, value in self.state.variables.items():
            message = message.replace("{" + key + "}", str(value))
        self.log(message, level)

    def _action_set_variable(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("name") or "")
        if not name:
            return
        self.state.variables[name] = raw.get("value")
        self.log(f"set {name}={raw.get('value')!r}", "info")

    def _action_wait(self, raw: dict[str, Any]) -> None:
        ms = int(raw.get("ms") or raw.get("wait_ms") or 0)
        if ms > 0:
            self.log(f"wait {ms}ms", "info")
            if not interruptible_sleep(ms, self._stop):
                self.log("wait interrupted", "warn")

    def _action_wait_until(self, raw: dict[str, Any]) -> None:
        timeout_ms = int(raw.get("timeout_ms") or 5000)
        poll_ms = max(50, int(raw.get("poll_ms") or 200))
        check = str(raw.get("check") or "variable").strip().lower()
        equals = raw.get("equals")
        variable = str(raw.get("variable") or "")
        roi_id = str(raw.get("roi") or "")
        parse_as = str(raw.get("parse_as") or "raw")
        self.log(
            f"wait_until check={check} variable={variable or '-'} roi={roi_id or '-'} "
            f"equals={equals!r} timeout_ms={timeout_ms}",
            "info",
        )
        deadline = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < deadline:
            if self._stop.is_set():
                raise CaptureError("wait_until interrupted")
            ok = False
            if check in {"variable", "var"} and variable:
                current = self.state.variables.get(variable)
                if equals is None:
                    ok = current not in (None, "", "ABSENT")
                else:
                    ok = str(current).strip().lower() == str(equals).strip().lower()
            elif check in {"ocr", "roi"} or (check == "variable" and roi_id):
                if not roi_id:
                    raise CaptureError("wait_until ocr/roi needs roi")
                # Fresh OCR sample
                self._action_ocr(
                    {"roi": roi_id, "variable": variable or roi_id, "parse_as": parse_as}
                )
                current = self.state.variables.get(variable or roi_id)
                if equals is None:
                    ok = bool(current)
                else:
                    ok = str(current).strip().lower() == str(equals).strip().lower()
            elif check in {"panel_open", "panel"}:
                self._action_detect_panel({"refresh": True})
                want = True if equals is None else str(equals).strip().lower() in {"1", "true", "yes", "open"}
                ok = bool(self.state.states.get("panel_open")) is want
            elif check in {"template", "match_template"}:
                self._action_match_template(
                    {
                        "template": raw.get("template"),
                        "roi": roi_id or None,
                        "threshold": raw.get("threshold", 0.85),
                        "variable": variable or "template",
                        "click": False,
                    }
                )
                current = self.state.variables.get(variable or "template")
                want = "PRESENT" if equals is None else str(equals).strip().upper()
                ok = str(current).strip().upper() == want
            else:
                raise CaptureError(f"wait_until unknown check={check!r}")
            if ok:
                self.log("wait_until satisfied", "ok")
                return
            if not interruptible_sleep(poll_ms, self._stop):
                raise CaptureError("wait_until interrupted")
        raise CaptureError(f"wait_until timed out after {timeout_ms}ms")

    def _action_match_template(self, raw: dict[str, Any]) -> None:
        template_id = str(raw.get("template") or "")
        variable = str(raw.get("variable") or "template")
        threshold = float(raw.get("threshold") or 0.85)
        do_click = bool(raw.get("click", False))
        roi_id = str(raw.get("roi") or "")
        rect = self.get_anchor_rect()
        if rect is None:
            raise CaptureError("anchor missing")
        image = self.state.last_image
        if image is None:
            image = grab_anchor(rect)
            self.state.last_image = image
        scene = image
        offset_x = offset_y = 0
        if roi_id:
            roi = self.store.rois.get(roi_id)
            if roi is None:
                raise TemplateMatchError(f"unknown roi: {roi_id}")
            cropped = crop_roi(image, rect, roi)
            scene = cropped
            # crop_roi returns image already cropped; offsets approximated via normalized box
            offset_x = int(round(roi.nx * image.width))
            offset_y = int(round(roi.ny * image.height))
        path = resolve_template_path(self.templates_dir, template_id)
        result = match_template(scene, path, threshold=threshold)
        label = "PRESENT" if result.present else "ABSENT"
        self.state.variables[variable] = label
        self.state.variables[f"{variable}_score"] = f"{result.score:.4f}"
        self.state.states[f"{variable}_present"] = result.present
        self.log(
            f"match_template {template_id}: {label} score={result.score:.3f} "
            f"threshold={threshold:.2f} at=({result.x + offset_x},{result.y + offset_y})",
            "ok" if result.present else "warn",
        )
        if do_click and result.present:
            hwnd, anchor = self._anchor()
            if anchor is None or not hwnd:
                raise CaptureError("anchor missing")
            abs_x = result.x + offset_x
            abs_y = result.y + offset_y
            nx = abs_x / max(image.width, 1)
            ny = abs_y / max(image.height, 1)
            if not self._supervise(f"Template click {template_id} at ({nx:.3f},{ny:.3f})"):
                return
            click_normalized(
                hwnd=hwnd,
                rect=anchor,
                nx=nx,
                ny=ny,
                hold_ms=int(raw.get("hold_ms") or 70),
                restore_cursor=self.restore_cursor,
                profile=self._profile(),
                stop=self._stop,
            )
            self.state.last_image = None

    def _action_click(self, raw: dict[str, Any]) -> None:
        hwnd, rect = self._anchor()
        if rect is None or not hwnd:
            raise CaptureError("anchor missing")
        target = str(raw.get("target") or "").strip().lower()
        if target in BUY_CLICK:
            nx, ny = BUY_CLICK[target]
        elif target in TAB_CLICK:
            nx, ny = TAB_CLICK[target]
        else:
            if "nx" not in raw or "ny" not in raw:
                raise CaptureError("click needs nx/ny or target=health|damage|attack|defense|utility")
            nx = float(raw["nx"])
            ny = float(raw["ny"])
        hold_ms = int(raw.get("hold_ms") or 70)
        label = target or f"({nx:.2f},{ny:.2f})"
        times = self._spam_repeat_count(raw)
        interval_ms = max(10, int(raw.get("interval_ms") or 50))
        if not self._supervise(f"Click {label}" + (f" ×{times}" if times > 1 else "")):
            return
        self.log(f"click {label}" + (f" spam×{times} every {interval_ms}ms" if times > 1 else ""), "run")
        for i in range(times):
            if self._stop is not None and self._stop.is_set():
                break
            click_normalized(
                hwnd=hwnd,
                rect=rect,
                nx=nx,
                ny=ny,
                hold_ms=hold_ms,
                restore_cursor=self.restore_cursor,
                profile=self._profile(),
                stop=self._stop,
            )
            if i + 1 < times:
                interruptible_sleep(interval_ms, self._stop)
        # Clicks change UI — force a fresh frame next observe.
        self.state.last_image = None

    def _spam_repeat_count(self, raw: dict[str, Any]) -> int:
        if str(raw.get("mode") or "single").strip().lower() != "spam":
            return 1
        interval_ms = max(10, int(raw.get("interval_ms") or 50))
        spam_by = str(raw.get("spam_by") or "clicks").strip().lower()
        if spam_by == "timed":
            from idle_lab.shell.atom_create import snap_spam_duration_ms, spam_click_count

            duration_ms = snap_spam_duration_ms(int(raw.get("duration_ms") or 1000), interval_ms)
            return spam_click_count(duration_ms=duration_ms, interval_ms=interval_ms)
        return max(1, int(raw.get("click_amount") or 1))

    def _action_drag(self, raw: dict[str, Any]) -> None:
        hwnd, rect = self._anchor()
        if rect is None or not hwnd:
            raise CaptureError("anchor missing")
        nx0 = float(raw.get("nx0", raw.get("nx", 0.4)))
        ny0 = float(raw.get("ny0", raw.get("ny", 0.5)))
        nx1 = float(raw.get("nx1", 0.6))
        ny1 = float(raw.get("ny1", 0.5))
        label = f"({nx0:.2f},{ny0:.2f})→({nx1:.2f},{ny1:.2f})"
        if not self._supervise(f"Drag {label}"):
            return
        self.log(f"drag {label}", "run")
        if hwnd:
            win32_api.focus_window(hwnd)
            time.sleep(0.05)
        x0, y0 = normalized_to_screen(rect, nx0, ny0)
        x1, y1 = normalized_to_screen(rect, nx1, ny1)
        speed = str(raw.get("speed") or "medium").strip().lower()
        speed_steps = {"slow": 20, "medium": 12, "fast": 6}.get(speed, 12)
        speed_ms = {"slow": 35, "medium": 25, "fast": 12}.get(speed, 25)
        hold_end = int(raw.get("hold_end_ms") or 0)
        if "pause_end" in raw:
            hold_end = int(raw.get("pause_ms") or 200) if bool(raw.get("pause_end")) else 0
        foreground_drag(
            x0,
            y0,
            x1,
            y1,
            restore_cursor=self.restore_cursor,
            steps=int(raw.get("steps") or speed_steps),
            step_ms=int(raw.get("step_ms") or speed_ms),
            hold_end_ms=hold_end,
            stop=self._stop,
        )
        self.state.last_image = None

    def _action_key(self, raw: dict[str, Any]) -> None:
        token = str(raw.get("key") or "").strip()
        if not token:
            raise CaptureError("key action needs key")
        times = self._spam_repeat_count(raw)
        interval_ms = max(10, int(raw.get("interval_ms") or 50))
        if not self._supervise(f"Key {token}" + (f" ×{times}" if times > 1 else "")):
            return
        hwnd, _rect = self._anchor()
        if hwnd:
            win32_api.focus_window(hwnd)
            time.sleep(0.05)
        self.log(f"key {token}" + (f" spam×{times} every {interval_ms}ms" if times > 1 else ""), "run")
        for i in range(times):
            if self._stop is not None and self._stop.is_set():
                break
            if not win32_api.send_key_token(token):
                raise CaptureError(f"unsupported key token: {token}")
            if i + 1 < times:
                interruptible_sleep(interval_ms, self._stop)
        self.state.last_image = None

    def _action_detect_panel(self, raw: dict[str, Any]) -> None:
        rect = self.get_anchor_rect()
        if rect is None:
            raise CaptureError("anchor missing")
        refresh = bool(raw.get("refresh", True))
        image = self._fresh_image(rect) if refresh or self.state.last_image is None else self.state.last_image
        state = observe_panel(image)
        vars_map = panel_status_vars(state)
        self.state.variables.update(vars_map)
        self.state.states["panel_open"] = state.panel_open
        prefix = str(raw.get("prefix") or "")
        if prefix:
            path = save_screenshot(image, self.runs_dir / "screenshots", prefix=prefix)
            self.state.last_screenshot_path = path
            self.state.variables["last_screenshot"] = str(path)
        open_label = "open" if state.panel_open else "closed"
        tab_label = state.tab or "none"
        self.log(
            f"status: panel {open_label}, tab={tab_label} — {state.reason} (rgb={vars_map['panel_rgb']})",
            "ok",
        )

    def _action_ensure_upgrade_tab(self, raw: dict[str, Any]) -> None:
        tab = str(raw.get("tab") or "").strip().lower()
        if tab not in TAB_CLICK:
            raise CaptureError(f"ensure_upgrade_tab needs tab=attack|defense|utility (got {tab!r})")
        hwnd, rect = self._anchor()
        if rect is None or not hwnd:
            raise CaptureError("anchor missing")
        wait_ms = max(0, int(raw.get("wait_ms") or 550))
        hold_ms = int(raw.get("hold_ms") or 70)
        prefix = str(raw.get("prefix") or f"ensure_{tab}")

        before = self._fresh_image(rect)
        before_state = observe_panel(before)
        path = save_screenshot(before, self.runs_dir / "screenshots", prefix=f"{prefix}_before")
        self.state.variables.update(panel_status_vars(before_state))
        self.log(
            f"ensure {tab}: before panel={'open' if before_state.panel_open else 'closed'} "
            f"tab={before_state.tab or 'none'} — {before_state.reason}",
            "info",
        )

        if before_state.panel_open and before_state.tab == tab:
            self.log(f"ensure {tab}: already open — skipped click (retap would close)", "ok")
            self.state.variables["ensure_clicked"] = "no"
            self.state.variables["ensure_tab"] = tab
            self.state.variables["last_screenshot"] = str(path)
            return

        # Panel looks open but color did not match Attack/Defense/Utility.
        # Clicking the target tab might be a retap → accidental close. Stay put.
        if before_state.panel_open and before_state.tab is None:
            self.log(
                f"ensure {tab}: panel open but tab unmatched — skipping click to avoid closing it "
                f"({before_state.reason})",
                "warn",
            )
            self.state.variables["ensure_clicked"] = "no"
            self.state.variables["ensure_tab"] = "unknown"
            self.state.variables["last_screenshot"] = str(path)
            return

        nx, ny = TAB_CLICK[tab]
        if "nx" in raw:
            nx = float(raw["nx"])
        if "ny" in raw:
            ny = float(raw["ny"])
        self.log(
            f"ensure {tab}: clicking tab "
            f"(was {before_state.tab or 'closed'})",
            "run",
        )
        click_normalized(
            hwnd=hwnd,
            rect=rect,
            nx=nx,
            ny=ny,
            hold_ms=hold_ms,
            restore_cursor=self.restore_cursor,
            profile=self._profile(),
            stop=self._stop,
        )
        if wait_ms:
            interruptible_sleep(wait_ms, self._stop)
        after = self._fresh_image(rect)
        after_state = observe_panel(after)

        # Accidental close recovery: one reopen click (never a third — that would close again).
        if not after_state.panel_open:
            self.log(
                f"ensure {tab}: panel closed after click — reopening once (keep-open policy)",
                "warn",
            )
            click_normalized(
                hwnd=hwnd,
                rect=rect,
                nx=nx,
                ny=ny,
                hold_ms=hold_ms,
                restore_cursor=self.restore_cursor,
                profile=self._profile(),
                stop=self._stop,
            )
            if wait_ms:
                interruptible_sleep(wait_ms, self._stop)
            after = self._fresh_image(rect)
            after_state = observe_panel(after)

        after_path = save_screenshot(after, self.runs_dir / "screenshots", prefix=f"{prefix}_after")
        self.state.variables.update(panel_status_vars(after_state))
        self.state.variables["ensure_clicked"] = "yes"
        self.state.variables["ensure_tab"] = tab
        self.state.variables["last_screenshot"] = str(after_path)
        open_ok = after_state.panel_open and after_state.tab == tab
        self.log(
            f"ensure {tab}: after panel={'open' if after_state.panel_open else 'closed'} "
            f"tab={after_state.tab or 'none'} — {after_state.reason}",
            "ok" if open_ok else "warn",
        )

    def _action_seek_list_top(self, raw: dict[str, Any]) -> None:
        look_for = str(raw.get("look_for") or raw.get("keyword") or "").strip()
        hwnd, rect = self._anchor()
        if rect is None or not hwnd:
            raise CaptureError("anchor missing")
        prefix = str(raw.get("prefix") or "seek_top")

        # Status snapshot before deciding whether to scroll.
        before = self._fresh_image(rect)
        panel = observe_panel(before)
        self.state.variables.update(panel_status_vars(panel))
        path = save_screenshot(before, self.runs_dir / "screenshots", prefix=f"{prefix}_before")
        self.state.variables["last_screenshot"] = str(path)
        if look_for:
            check = check_list_top(before, look_for)
            self.state.variables["list_top_raw"] = check.observation
            self.state.variables["list_at_top"] = "yes" if check.at_top else "no"
            self.log(
                f"seek_list_top ({look_for}): panel tab={panel.tab or 'none'}; {check.reason}",
                "info",
            )
            if check.at_top:
                self.log(f"list already shows {look_for!r} — no scroll", "ok")
                self.state.variables["seek_steps"] = "0"
                self.state.variables["seek_reason"] = "ocr_match"
                return
        else:
            self.log(
                f"seek_list_top: panel tab={panel.tab or 'none'}; scrolling up until unchanged",
                "info",
            )

        def save_status(image: Any, stem: str) -> None:
            save_screenshot(image, self.runs_dir / "screenshots", prefix=f"{prefix}_{stem}")

        result = seek_list_top(
            hwnd=hwnd,
            rect=rect,
            look_for=look_for,
            max_steps=int(raw.get("max_steps") or 12),
            settle_ms=int(raw.get("settle_ms") or 800),
            settle_confirm_ms=int(raw.get("settle_confirm_ms") or 400),
            unchanged_threshold=float(raw.get("unchanged_threshold") or 0.015),
            drag_fraction=float(raw.get("drag_fraction") or 0.10),
            hold_end_ms=int(raw.get("hold_end_ms") or 450),
            restore_cursor=self.restore_cursor,
            stop=self._stop,
            log=self.log,
            save_status=save_status,
        )
        self.state.last_image = None
        self.state.variables["seek_steps"] = str(result.get("steps", 0))
        self.state.variables["seek_reason"] = str(result.get("stop_reason") or "")
        self.state.variables["list_at_top"] = "yes" if result.get("at_top") else "no"
        if result.get("observation"):
            self.state.variables["list_top_raw"] = str(result["observation"])
        self.log(
            f"seek_list_top done: steps={result.get('steps')} reason={result.get('stop_reason')} "
            f"at_top={result.get('at_top')}",
            "ok" if result.get("at_top") else "warn",
        )

    def _action_scroll_list(self, raw: dict[str, Any]) -> None:
        """Tab-agnostic controlled list scroll: ``direction`` + ``rows`` (playbook drag)."""

        direction = str(raw.get("direction") or "down").strip().lower()
        if direction not in ("up", "down"):
            raise CaptureError(f"scroll_list needs direction=up|down (got {direction!r})")
        rows = max(1, abs(int(raw.get("rows") or raw.get("amount") or 1)))
        drag_fraction = float(raw.get("drag_fraction") or 0.10)
        hold_end_ms = int(raw.get("hold_end_ms") or 450)
        settle_ms = int(raw.get("settle_ms") or 800)
        nx = float(raw.get("nx") or 0.45)
        ny = float(raw.get("ny") or 0.72)
        hwnd, rect = self._anchor()
        if rect is None or not hwnd:
            raise CaptureError("anchor missing")
        self.log(f"scroll_list: {direction} × {rows} row(s)", "run")
        for index in range(1, rows + 1):
            if self._stop.is_set():
                raise CaptureError("Stopped by user.")
            drag_list(
                hwnd=hwnd,
                rect=rect,
                direction=direction,
                nx=nx,
                ny=ny,
                drag_fraction=drag_fraction,
                hold_end_ms=hold_end_ms,
                restore_cursor=self.restore_cursor,
                stop=self._stop,
            )
            if settle_ms:
                interruptible_sleep(settle_ms, self._stop)
            self.log(f"scroll_list: row {index}/{rows} done", "ok")
        self.state.variables["scroll_list_direction"] = direction
        self.state.variables["scroll_list_rows"] = str(rows)

    def _lco_session(self) -> LiveControlController:
        """LCO for atom actions: reuse interactive overlay when armed; else headless enter."""

        shared = self._shared_lco
        if shared is not None and shared.active:
            # Shared overlay session: clear a prior Esc/` abort so atom steps can run.
            shared.cancel_event.clear()
            self._lco = shared
            return shared
        if self._lco is None or self._lco is shared:
            self._lco = LiveControlController(
                overlay=NullOverlay(),
                project_root=self.runs_dir.parent,
                get_anchor=lambda: (None, *self._anchor()),
                run_event_once=lambda event_id: self._action_run_event({"event": event_id}),
                log=self.log,
            )
        if not self._lco.active:
            self._lco.enter()
        return self._lco

    def _action_lco(self, raw: dict[str, Any]) -> None:
        """One Live Control action by ``action`` id or hotkey ``key``; optional ``times`` repeats it."""

        session = self._lco_session()
        assert session.playbook is not None
        action = str(raw.get("action") or "").strip().lower()
        key = str(raw.get("key") or "").strip()
        if not action and key:
            action = session.playbook.action_for_token(key) or ""
            if not action:
                raise LiveControlError(f"lco: no Live Control action bound to key {key!r}")
        if not action:
            raise LiveControlError("lco needs action or key")
        times = max(1, abs(int(raw.get("times") or 1)))
        label = action if times == 1 else f"{action} ×{times}"
        if not self._supervise(f"LCO {label}"):
            return
        for _ in range(times):
            if self._stop.is_set():
                raise CaptureError("Stopped by user.")
            session.run_action(action)
        self.state.last_image = None
        self.state.variables["lco_tab"] = session.tab or "none"
        self.state.variables["lco_slots"] = str(len(session.live_slots))
        self.state.variables["lco_aligned"] = "yes" if session.aligned else "no"
