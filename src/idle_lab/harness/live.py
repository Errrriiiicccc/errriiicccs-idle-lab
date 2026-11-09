"""T3 live runner — auto-anchor from lab-context, no Tk Start click."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.ai_batch.runner import AiBatchRunner, AiBatchRunnerError
from idle_lab.ai_batch.store import AiBatchStore
from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.store import AutomationStore
from idle_lab.harness.context import load_lab_context
from idle_lab.harness.doctor import DoctorResult, run_doctor
from idle_lab.humanize import HumanizeProfile
from idle_lab.models import Rect
from idle_lab.presets import project_root
from idle_lab.settings_store import load_settings


class LiveHarnessError(RuntimeError):
    """Live harness could not start or finish."""


@dataclass
class LiveResult:
    ok: bool
    kind: str
    target_id: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    doctor: dict[str, Any] = field(default_factory=dict)


def _rect_from_doctor(doctor: DoctorResult) -> Rect | None:
    if not doctor.rect:
        return None
    r = doctor.rect
    return Rect(int(r["left"]), int(r["top"]), int(r["right"]), int(r["bottom"]))


def _anchor_getter(doctor: DoctorResult):
    rect = _rect_from_doctor(doctor)
    title = doctor.title or doctor.target_label
    hwnd = doctor.hwnd

    def get_anchor() -> tuple[str, int | None, Rect | None, str | None]:
        if hwnd is None or rect is None:
            return ("missing", None, None, None)
        return ("ok", hwnd, rect, title)

    return get_anchor


def run_live_mission(slug: str, *, root: Path | None = None, timeout_s: float = 600.0) -> LiveResult:
    project = root or project_root()
    ctx = load_lab_context(project)
    doctor = run_doctor(root=project, context=ctx)
    if not doctor.ok:
        return LiveResult(
            ok=False,
            kind="mission",
            target_id=ctx.active_target,
            summary=f"doctor failed: {doctor.hint}",
            doctor=doctor.to_dict(),
            details={"slug": slug},
        )

    settings, _ = load_settings(project / "settings.json")
    store = AiBatchStore(project / "ai-batches")
    store.ensure_example_batches()
    store.load_all()
    batch = store.batches.get(slug)
    if batch is None:
        known = ", ".join(sorted(store.batches)) or "(none)"
        raise LiveHarnessError(f"mission {slug!r} not found; known: {known}")

    runner = AiBatchRunner(
        store=store,
        screen_maps_root=project / "screen-maps",
        get_anchor=_anchor_getter(doctor),
        restore_cursor=settings.restore_cursor,
        get_humanize=lambda: HumanizeProfile.from_level(settings.humanize_level),
    )

    try:
        runner.start(batch)
    except AiBatchRunnerError as exc:
        return LiveResult(
            ok=False,
            kind="mission",
            target_id=ctx.active_target,
            summary=str(exc),
            doctor=doctor.to_dict(),
            details={"slug": slug},
        )

    deadline = time.monotonic() + max(5.0, float(timeout_s))
    while runner.is_running and time.monotonic() < deadline:
        time.sleep(0.1)
    if runner.is_running:
        runner.stop()
        runner._thread.join(timeout=10)  # noqa: SLF001
        return LiveResult(
            ok=False,
            kind="mission",
            target_id=ctx.active_target,
            summary=f"mission {slug} timed out after {timeout_s}s",
            doctor=doctor.to_dict(),
            details={"slug": slug, "timed_out": True},
        )

    store.load_all()
    again = store.batches.get(slug)
    folder = store.folder_for(slug)
    report_path = (folder / "run_report.json") if folder else None
    statuses = [req.status for req in (again.requests if again else [])]
    missed = sum(1 for status in statuses if status == "missed")
    done = sum(1 for status in statuses if status == "done")
    ok = missed == 0 and done > 0
    summary = f"mission {slug}: {done} done, {missed} missed"
    return LiveResult(
        ok=ok,
        kind="mission",
        target_id=ctx.active_target,
        summary=summary,
        doctor=doctor.to_dict(),
        details={
            "slug": slug,
            "statuses": statuses,
            "run_report": str(report_path) if report_path and report_path.exists() else None,
            "linked_screen_maps": list(again.linked_screen_map_batches) if again else [],
            "anchor_title": doctor.title,
            "match_mode": doctor.match_mode,
        },
    )


def run_live_atom(event_id: str, *, root: Path | None = None, timeout_s: float = 300.0) -> LiveResult:
    project = root or project_root()
    ctx = load_lab_context(project)
    doctor = run_doctor(root=project, context=ctx)
    if not doctor.ok:
        return LiveResult(
            ok=False,
            kind="atom",
            target_id=ctx.active_target,
            summary=f"doctor failed: {doctor.hint}",
            doctor=doctor.to_dict(),
            details={"event_id": event_id},
        )

    settings, _ = load_settings(project / "settings.json")
    store = AutomationStore(project / "automations")
    load_errors = store.load_all()
    if event_id not in store.events:
        known = ", ".join(sorted(store.events)[:20]) or "(none)"
        raise LiveHarnessError(f"atom {event_id!r} not found; sample: {known}")

    rect = _rect_from_doctor(doctor)
    hwnd = doctor.hwnd
    events: queue.Queue = queue.Queue()

    def get_anchor_rect() -> Rect | None:
        return rect

    def get_anchor_hwnd() -> tuple[int | None, Rect | None]:
        return hwnd, rect

    runtime = AutomationRuntime(
        store=store,
        runs_dir=project / "runs",
        get_anchor_rect=get_anchor_rect,
        get_anchor_hwnd=get_anchor_hwnd,
        get_humanize=lambda: HumanizeProfile.from_level(settings.humanize_level),
        restore_cursor=settings.restore_cursor,
        events_out=events,
        trace_level=settings.trace_level,
    )

    def drain_logs() -> list[str]:
        lines: list[str] = []
        while True:
            try:
                item = events.get_nowait()
            except queue.Empty:
                break
            if item.get("kind") == "console":
                lines.append(f"[{item.get('level') or 'info'}] {item.get('message') or ''}")
        return lines

    logs: list[str] = []
    try:
        runtime.run_event_once(event_id)
    except Exception as exc:  # noqa: BLE001
        logs.extend(drain_logs())
        return LiveResult(
            ok=False,
            kind="atom",
            target_id=ctx.active_target,
            summary=f"atom start failed: {exc}",
            doctor=doctor.to_dict(),
            details={"event_id": event_id, "load_errors": load_errors, "logs": logs},
        )

    deadline = time.monotonic() + max(5.0, float(timeout_s))
    while runtime.collection_running and time.monotonic() < deadline:
        logs.extend(drain_logs())
        time.sleep(0.05)
    logs.extend(drain_logs())
    if runtime.collection_running:
        runtime.stop()
        logs.extend(drain_logs())
        return LiveResult(
            ok=False,
            kind="atom",
            target_id=ctx.active_target,
            summary=f"atom {event_id} timed out after {timeout_s}s",
            doctor=doctor.to_dict(),
            details={"event_id": event_id, "timed_out": True, "logs": logs[-40:]},
        )

    error_logs = [line for line in logs if line.startswith("[error]")]
    ok = not error_logs
    return LiveResult(
        ok=ok,
        kind="atom",
        target_id=ctx.active_target,
        summary=(
            f"atom {event_id} finished"
            + (f" with {len(error_logs)} error(s)" if error_logs else " ok")
        ),
        doctor=doctor.to_dict(),
        details={
            "event_id": event_id,
            "load_errors": load_errors,
            "logs": logs[-80:],
            "anchor_title": doctor.title,
            "match_mode": doctor.match_mode,
        },
    )
