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
from idle_lab.automations.csv_log import append_run_row
from idle_lab.automations.decide import decide_ab
from idle_lab.automations.ocr import OcrError, ocr_field
from idle_lab.automations.scheduler import Scheduler
from idle_lab.automations.schema import Event, Roi
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.video import VideoError, clip_name, record_clip
from idle_lab.models import Rect


LogFn = Callable[[str, str], None]  # message, level


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
        get_anchor_rect: Callable[[], Rect | None],
        play_preset: Callable[[str], None] | None = None,
        events_out: queue.Queue | None = None,
    ) -> None:
        self.store = store
        self.runs_dir = Path(runs_dir)
        self.get_anchor_rect = get_anchor_rect
        self.play_preset = play_preset
        self.events_out: queue.Queue = events_out or queue.Queue()
        self.scheduler = Scheduler()
        self.state = RuntimeState()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = False

    def emit(self, kind: str, **payload: Any) -> None:
        self.events_out.put({"kind": kind, **payload})

    def log(self, message: str, level: str = "info") -> None:
        self.emit("console", message=message, level=level)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._enabled = True
        self.scheduler.reset(list(self.store.events.values()))
        self._thread = threading.Thread(target=self._loop, name="idle-lab-automations", daemon=True)
        self._thread.start()
        self.log("Automations runtime started.", "ok")

    def stop(self) -> None:
        self._enabled = False
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self.log("Automations runtime stopped.", "warn")

    def reload_schedule(self) -> None:
        self.scheduler.reset(list(self.store.events.values()))
        self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])
        self.log("Scheduler reloaded from files.", "ok")

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self._enabled:
                time.sleep(0.1)
                continue
            events = [event for event in self.store.events.values() if event.enabled]
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
            try:
                self._run_event(chosen)
            except Exception as exc:  # noqa: BLE001
                self.log(f"event {chosen.id} failed: {exc}", "error")
                # Known dependency/setup errors: keep console readable (no full traceback).
                message = str(exc).lower()
                if not any(
                    tip in message
                    for tip in (
                        "tesseract",
                        "ffmpeg",
                        "anchor missing",
                        "not found on path",
                        "not installed",
                    )
                ):
                    self.log(traceback.format_exc(), "error")
            finally:
                self.scheduler.mark_finished(chosen, events)
                self.emit("queue", items=[item.__dict__ for item in self.scheduler.queue_snapshot()])

    def _run_event(self, event: Event) -> None:
        self.log(f"▶ {event.title} ({event.id})", "run")
        branch_actions: list | None = None
        for action in event.actions:
            if branch_actions is not None:
                # Skip siblings after a decide that selected a branch list inline.
                break
            if action.type == "decide":
                branch_actions = self._action_decide(action.raw)
                if branch_actions:
                    for nested in branch_actions:
                        self._dispatch(nested if isinstance(nested, dict) else nested.raw)
                continue
            self._dispatch(action.raw)
        self.log(f"✔ finished {event.id}", "ok")

    def _dispatch(self, raw: dict[str, Any]) -> None:
        action_type = raw.get("type")
        handlers = {
            "screenshot": self._action_screenshot,
            "ocr": self._action_ocr,
            "decide": lambda data: self._action_decide(data),
            "mouse": self._action_play_preset,
            "play_preset": self._action_play_preset,
            "record_clip": self._action_record_clip,
            "csv_append": self._action_csv_append,
            "log": self._action_log,
            "set_variable": self._action_set_variable,
        }
        handler = handlers.get(str(action_type))
        if handler is None:
            self.log(f"unknown action type: {action_type}", "error")
            return
        handler(raw)

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
        roi = self.store.rois.get(roi_id)
        if roi is None:
            raise OcrError(f"unknown roi: {roi_id}")
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
        self.log(
            f"OCR {roi_id}: observation={result.observation!r} inference={result.inference!r} → {variable}",
            "info",
        )

    def _action_decide(self, raw: dict[str, Any]) -> list[dict[str, Any]] | None:
        variable = str(raw.get("variable") or "signal")
        value = self.state.variables.get(variable)
        match_a = str(raw.get("match_a") or "A")
        mode = str(raw.get("mode") or "contains")
        branch = decide_ab(value, match_a=match_a, mode=mode)
        self.state.variables["branch"] = branch
        self.log(f"decide {variable}={value!r} → branch {branch}", "ok")
        if branch == "A":
            return list(raw.get("on_a") or [])
        return list(raw.get("on_b") or [])

    def _action_play_preset(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("preset") or raw.get("name") or "")
        if not name:
            self.log("play_preset missing preset name", "error")
            return
        if self.play_preset is None:
            self.log(f"play_preset stub: would run {name!r}", "warn")
            return
        self.log(f"playing preset {name!r}", "run")
        self.play_preset(name)

    def _action_record_clip(self, raw: dict[str, Any]) -> None:
        rect = self.get_anchor_rect()
        if rect is None:
            raise VideoError("anchor missing")
        duration_s = float(raw.get("duration_s") or 10)
        run_number = self.store.runtime.run_number
        wave = self.state.variables.get("wave_number") or "xx"
        name = clip_name(run_number, wave)
        dest = self.runs_dir / "clips" / f"{name}.mp4"
        self.log(f"recording clip {dest.name} ({duration_s:.0f}s)…", "warn")
        record_clip(rect, dest, duration_s=duration_s, should_abort=self._stop.is_set)
        self.state.variables["last_clip"] = str(dest)
        self.log(f"clip saved {dest}", "ok")

    def _action_csv_append(self, raw: dict[str, Any]) -> None:
        path_name = str(raw.get("path") or "run_log.csv")
        path = self.runs_dir / path_name
        run_number = self.store.runtime.run_number
        wave = self.state.variables.get("wave_number") or "xx"
        row = append_run_row(path, run_number=run_number, wave_number=wave)
        self.log(f"csv append {path.name}: {row}", "ok")

    def _action_log(self, raw: dict[str, Any]) -> None:
        message = str(raw.get("message") or "")
        level = str(raw.get("level") or "info")
        # Tiny template substitution for variables.
        for key, value in self.state.variables.items():
            message = message.replace("{" + key + "}", str(value))
        self.log(message, level)

    def _action_set_variable(self, raw: dict[str, Any]) -> None:
        name = str(raw.get("name") or "")
        if not name:
            return
        self.state.variables[name] = raw.get("value")
        self.log(f"set {name}={raw.get('value')!r}", "info")
