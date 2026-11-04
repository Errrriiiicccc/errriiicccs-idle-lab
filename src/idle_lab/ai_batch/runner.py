"""Execute an AI information batch: click / scroll / screenshot → Screen Map + results."""

from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable

from idle_lab.ai_batch.panel_detect import detect_upgrade_panel
from idle_lab.ai_batch.schema import AiBatch, BatchRequest, RequestResult, now_iso
from idle_lab.ai_batch.scroll_metrics import ScrollStepMetric, crop_normalized, mean_abs_diff
from idle_lab.ai_batch.store import AiBatchStore
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.click_foreground import foreground_drag
from idle_lab.humanize import HumanizeProfile, human_click, human_scroll_gap_ms, human_wait
from idle_lab.models import Rect, normalized_to_screen
from idle_lab.screen_map.batch import BatchSession, ScreenMapError, add_shot, create_batch
from idle_lab import win32_api


class AiBatchRunnerError(RuntimeError):
    """User-facing batch run failure."""


class AiBatchRunner:
    """Background runner. Emits dict events on ``events_out`` for the UI thread."""

    def __init__(
        self,
        *,
        store: AiBatchStore,
        screen_maps_root: Path,
        get_anchor: Callable[[], tuple[str, int | None, Rect | None, str | None]],
        play_preset: Callable[[str], None] | None = None,
        restore_cursor: bool = True,
        get_humanize: Callable[[], HumanizeProfile] | None = None,
    ) -> None:
        self.store = store
        self.screen_maps_root = Path(screen_maps_root)
        self.get_anchor = get_anchor
        self.play_preset = play_preset
        self.restore_cursor = restore_cursor
        self.get_humanize = get_humanize or (lambda: HumanizeProfile.from_level("medium"))
        self.events_out: queue.Queue[dict[str, Any]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.active_slug: str | None = None

    def _profile(self) -> HumanizeProfile:
        return self.get_humanize()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, batch: AiBatch) -> None:
        with self._lock:
            if self.is_running:
                raise AiBatchRunnerError("An AI batch is already running.")
            runnable = [req for req in batch.requests if req.runnable and req.status == "pending"]
            if not runnable and not any(req.runnable for req in batch.requests):
                raise AiBatchRunnerError(
                    "This batch has no executable steps. Add steps[] to requests in batch.json "
                    "(click / scroll / screenshot / wait)."
                )
            self._stop.clear()
            self.active_slug = batch.slug
            self._thread = threading.Thread(
                target=self._run,
                args=(batch.slug,),
                name=f"ai-batch-{batch.slug}",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _emit(self, **payload: Any) -> None:
        self.events_out.put(payload)

    def _run(self, slug: str) -> None:
        report: dict[str, Any] = {
            "batch_slug": slug,
            "started_at": now_iso(),
            "requests": [],
            "screen_map_batch": None,
            "stopped": False,
            "error": None,
        }
        session: BatchSession | None = None
        try:
            self.store.load_all()
            batch = self.store.batches.get(slug)
            if batch is None:
                raise AiBatchRunnerError(f"Batch not found: {slug}")

            batch.status = "running"
            self.store.save(batch)
            self._emit(kind="status", message=f"Running AI batch: {batch.name}", level="run")
            self._emit(kind="refresh")

            self.screen_maps_root.mkdir(parents=True, exist_ok=True)
            session = create_batch(self.screen_maps_root, f"ai-run-{batch.slug}")
            report["screen_map_batch"] = session.folder.name
            self.store.link_screen_map(batch, session.folder.name)
            self._emit(
                kind="status",
                message=f"Screen Map batch: {session.folder.name}",
                level="ok",
            )

            for req in list(batch.requests):
                if self._stop.is_set():
                    report["stopped"] = True
                    break
                # Fresh copy from disk after each save
                self.store.load_all()
                batch = self.store.batches[slug]
                live = next((item for item in batch.requests if item.id == req.id), req)

                if live.status == "done":
                    report["requests"].append({"id": live.id, "status": "skipped_already_done"})
                    continue
                if not live.runnable:
                    if live.kind == "note":
                        self.store.mark_request(
                            batch,
                            live.id,
                            status="skipped",
                            result=RequestResult(
                                summary="Note/doc — skipped by runner; fill after analyzing Screen Map shots.",
                                captured_at=now_iso(),
                            ),
                        )
                        report["requests"].append({"id": live.id, "status": "skipped_note"})
                        self._emit(kind="refresh")
                        continue
                    self.store.mark_request(
                        batch,
                        live.id,
                        status="skipped",
                        result=RequestResult(
                            summary="No steps[] — cannot auto-run. Add executable steps.",
                            captured_at=now_iso(),
                        ),
                    )
                    report["requests"].append({"id": live.id, "status": "skipped_no_steps"})
                    self._emit(kind="refresh")
                    continue

                self._emit(kind="status", message=f"Request: {live.label}", level="info")
                try:
                    outcome = self._run_request(batch, live, session)
                    report["requests"].append(outcome)
                except Exception as exc:  # noqa: BLE001 — surface per-request
                    self.store.load_all()
                    batch = self.store.batches[slug]
                    self.store.mark_request(
                        batch,
                        live.id,
                        status="missed",
                        result=RequestResult(
                            summary=f"Failed: {exc}",
                            screen_map_batch=session.folder.name,
                            captured_at=now_iso(),
                        ),
                    )
                    report["requests"].append({"id": live.id, "status": "missed", "error": str(exc)})
                    self._emit(kind="status", message=f"Failed {live.id}: {exc}", level="error")
                self._emit(kind="refresh")

            self.store.load_all()
            batch = self.store.batches[slug]
            if report["stopped"]:
                batch.status = batch.recompute_status()
                if batch.status == "pending":
                    batch.status = "partial"
                self.store.save(batch)
                self._emit(kind="status", message="AI batch stopped.", level="warn")
            else:
                batch.status = batch.recompute_status()
                if batch.status == "completed" and not batch.completed_at:
                    batch.completed_at = now_iso()
                self.store.save(batch)
                self._emit(
                    kind="status",
                    message=f"AI batch finished: {batch.status} ({batch.done_count}/{batch.request_count})",
                    level="ok",
                )
        except Exception as exc:  # noqa: BLE001
            report["error"] = str(exc)
            self._emit(kind="status", message=f"AI batch aborted: {exc}", level="error")
            try:
                self.store.load_all()
                batch = self.store.batches.get(slug)
                if batch is not None:
                    batch.status = "failed"
                    self.store.save(batch)
            except Exception:
                pass
        finally:
            report["finished_at"] = now_iso()
            try:
                folder = self.store.folder_for(slug)
                if folder is not None:
                    (folder / "run_report.json").write_text(
                        json.dumps(report, indent=2) + "\n",
                        encoding="utf-8",
                    )
            except OSError:
                pass
            self.active_slug = None
            self._emit(kind="finished", report=report)
            self._emit(kind="refresh")

    def _run_request(
        self,
        batch: AiBatch,
        req: BatchRequest,
        session: BatchSession,
    ) -> dict[str, Any]:
        shot_names: list[str] = []
        scroll_maps: list[dict[str, Any]] = []
        ensures: list[dict[str, Any]] = []
        for index, step in enumerate(req.steps):
            if self._stop.is_set():
                raise AiBatchRunnerError("Stopped by user.")
            action = str(step.get("action") or "").strip().lower()
            if action == "wait":
                human_wait(max(0, int(step.get("ms") or 0)), self._profile(), stop=self._stop)
            elif action == "click":
                self._click(float(step["nx"]), float(step["ny"]), int(step.get("hold_ms") or 50))
            elif action == "scroll":
                self._scroll_from_step(step)
            elif action == "scroll_map":
                map_result = self._scroll_map(session, step, req_id=req.id, step_index=index)
                shot_names.extend(map_result["shots"])
                scroll_maps.append(map_result)
            elif action == "ensure_upgrade_tab":
                ensure_result = self._ensure_upgrade_tab(session, step, req_id=req.id)
                shot_names.extend(ensure_result["shots"])
                ensures.append(ensure_result)
            elif action == "screenshot":
                title = str(step.get("title") or req.label or f"{req.id}-{index}")
                shot = self._screenshot(session, title)
                shot_names.append(shot.filename)
            elif action == "play_preset":
                name = str(step.get("name") or "").strip()
                if not name or self.play_preset is None:
                    raise AiBatchRunnerError(f"play_preset missing name or handler ({name!r})")
                self.play_preset(name)
            else:
                raise AiBatchRunnerError(f"Unknown step action: {action!r}")

        summary = f"Ran {len(req.steps)} step(s)."
        if shot_names:
            summary += " Shots: " + ", ".join(shot_names)
        if ensures:
            bits = [
                f"ensure {item.get('tab')}: clicked={item.get('clicked')} "
                f"({item.get('decision')})"
                for item in ensures
            ]
            summary += " | " + "; ".join(bits)
        if scroll_maps:
            bits = []
            for item in scroll_maps:
                bits.append(
                    f"{item.get('title_prefix')}: down={item.get('scrolls_applied', 0)} "
                    f"up={item.get('seek_top_scrolls', 0)} "
                    f"stop={item.get('stop_reason')}, at_bottom={item.get('at_bottom')}"
                )
            summary += " | " + "; ".join(bits)
        payload: dict[str, Any] = {"shots": shot_names, "steps_run": len(req.steps)}
        if ensures:
            payload["ensures"] = ensures
        if scroll_maps:
            payload["scroll_maps"] = scroll_maps
        self.store.mark_request(
            batch,
            req.id,
            status="done",
            result=RequestResult(
                summary=summary,
                screen_map_batch=session.folder.name,
                screen_map_shot=shot_names[-1] if shot_names else None,
                path=shot_names[-1] if shot_names else None,
                captured_at=now_iso(),
                payload=payload,
            ),
        )
        return {
            "id": req.id,
            "status": "done",
            "shots": shot_names,
            "scroll_maps": scroll_maps,
            "ensures": ensures,
        }

    def _anchor_ready(self) -> tuple[int, Rect, str]:
        status, hwnd, rect, title = self.get_anchor()
        if status != "ok" or hwnd is None or rect is None:
            raise AiBatchRunnerError(f"Anchor not ready ({status}). Set anchor first.")
        return hwnd, rect, title or ""

    def _click(self, nx: float, ny: float, hold_ms: int) -> None:
        hwnd, rect, _title = self._anchor_ready()
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
        x, y = normalized_to_screen(rect, nx, ny)
        human_click(
            x,
            y,
            hold_ms,
            method="foreground",
            hwnd=hwnd,
            restore_cursor=self.restore_cursor,
            profile=self._profile(),
            rect=rect,
            stop=self._stop,
        )

    def _scroll_from_step(self, step: dict[str, Any]) -> None:
        self._scroll(
            float(step.get("nx", 0.45)),
            float(step.get("ny", 0.68)),
            str(step.get("direction") or "down"),
            int(step.get("amount") or 1),
            method=str(step.get("method") or "drag"),
            drag_fraction=float(step.get("drag_fraction") or 0.10),
            hold_end_ms=int(step.get("hold_end_ms") or 400),
            drag_steps=int(step.get("drag_steps") or 12),
            step_ms=int(step.get("step_ms") or 30),
        )

    def _scroll(
        self,
        nx: float,
        ny: float,
        direction: str,
        amount: int,
        *,
        method: str = "drag",
        drag_fraction: float = 0.10,
        hold_end_ms: int = 400,
        drag_steps: int = 12,
        step_ms: int = 30,
    ) -> None:
        hwnd, rect, _title = self._anchor_ready()
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
        method_key = method.strip().lower()
        repeats = max(1, abs(int(amount)))

        if method_key == "wheel":
            x, y = normalized_to_screen(rect, nx, ny)
            saved = win32_api.cursor_pos()
            try:
                win32_api.set_cursor_pos(x, y)
                time.sleep(0.05)
                # Win32: positive wheel = away/up; "scroll down the list" → negative.
                sign = 1 if direction.lower() in ("up", "left") else -1
                profile = self._profile()
                for _ in range(repeats):
                    if self._stop.is_set():
                        break
                    win32_api.send_mouse_wheel(sign)
                    human_wait(human_scroll_gap_ms(profile), profile, stop=self._stop)
            finally:
                if self.restore_cursor:
                    win32_api.set_cursor_pos(*saved)
            return

        # Controlled drag (default): partial swipe + hold-still before release (no fling).
        fraction = max(0.03, min(0.35, abs(float(drag_fraction))))
        # Finger moves opposite the list direction: down-list → drag up.
        delta = -fraction if direction.lower() in ("down", "right") else fraction
        start_ny = max(0.05, min(0.95, float(ny)))
        end_ny = max(0.05, min(0.95, start_ny + delta))
        start_x, start_y = normalized_to_screen(rect, nx, start_ny)
        end_x, end_y = normalized_to_screen(rect, nx, end_ny)
        for _ in range(repeats):
            if self._stop.is_set():
                break
            foreground_drag(
                start_x,
                start_y,
                end_x,
                end_y,
                restore_cursor=self.restore_cursor,
                steps=max(2, abs(int(drag_steps))),
                step_ms=max(1, abs(int(step_ms))),
                hold_end_ms=max(50, abs(int(hold_end_ms))),
                stop=self._stop,
            )
            time.sleep(0.05)

    def _ensure_upgrade_tab(
        self,
        session: BatchSession,
        step: dict[str, Any],
        *,
        req_id: str,
    ) -> dict[str, Any]:
        """Observe → detect open tab → click only if target panel is not already open."""

        tab = str(step.get("tab") or "").strip().lower()
        if tab not in ("attack", "defense", "utility"):
            raise AiBatchRunnerError(
                f"ensure_upgrade_tab needs tab=attack|defense|utility (got {tab!r})"
            )
        nx = float(step.get("nx", {"attack": 0.20, "defense": 0.40, "utility": 0.60}[tab]))
        ny = float(step.get("ny", 0.955))
        hold_ms = int(step.get("hold_ms") or 50)
        wait_ms = max(0, int(step.get("wait_ms") or 550))
        title_prefix = str(step.get("title_prefix") or f"{req_id}-{tab}")

        _hwnd, rect, window_title = self._anchor_ready()
        try:
            before_image = grab_anchor(rect)
        except CaptureError as exc:
            raise AiBatchRunnerError(str(exc)) from exc

        before_state = detect_upgrade_panel(before_image)
        before_shot = self._save_shot(
            session,
            f"{title_prefix}-00-observe",
            before_image,
            rect,
            window_title=window_title,
        )
        shots = [before_shot.filename]

        already_open = before_state.panel_open and before_state.tab == tab
        if already_open:
            return {
                "tab": tab,
                "clicked": False,
                "decision": f"already on {tab} — skipped click",
                "before": {
                    "panel_open": before_state.panel_open,
                    "tab": before_state.tab,
                    "reason": before_state.reason,
                    "mean_rgb": [round(c, 1) for c in before_state.mean_rgb],
                },
                "after": None,
                "shots": shots,
            }

        self._click(nx, ny, hold_ms)
        if wait_ms:
            time.sleep(wait_ms / 1000.0)
        try:
            after_image = grab_anchor(rect)
        except CaptureError as exc:
            raise AiBatchRunnerError(str(exc)) from exc
        after_state = detect_upgrade_panel(after_image)
        after_shot = self._save_shot(
            session,
            f"{title_prefix}-01-after-click",
            after_image,
            rect,
            window_title=window_title,
        )
        shots.append(after_shot.filename)

        decision = (
            f"was {before_state.tab or ('closed' if not before_state.panel_open else 'unknown')}; "
            f"clicked {tab}; now {after_state.tab or ('closed' if not after_state.panel_open else 'unknown')}"
        )
        return {
            "tab": tab,
            "clicked": True,
            "decision": decision,
            "before": {
                "panel_open": before_state.panel_open,
                "tab": before_state.tab,
                "reason": before_state.reason,
                "mean_rgb": [round(c, 1) for c in before_state.mean_rgb],
            },
            "after": {
                "panel_open": after_state.panel_open,
                "tab": after_state.tab,
                "reason": after_state.reason,
                "mean_rgb": [round(c, 1) for c in after_state.mean_rgb],
            },
            "shots": shots,
        }

    def _scroll_map(
        self,
        session: BatchSession,
        step: dict[str, Any],
        *,
        req_id: str,
        step_index: int,
    ) -> dict[str, Any]:
        """Map a list with observe→decide after every controlled partial drag.

        Each iteration: drag a fraction of the panel → hold still (kill fling) →
        settle → status screenshot → optional stability re-check → compare ROI to
        previous status → continue or stop at edge.
        """

        nx = float(step.get("nx", 0.45))
        ny = float(step.get("ny", 0.70))
        direction = str(step.get("direction") or "down")
        amount = max(1, abs(int(step.get("amount") or 1)))
        max_steps = max(1, abs(int(step.get("max_steps") or 12)))
        max_seek = max(1, abs(int(step.get("max_seek_steps") or 12)))
        if "settle_ms" in step:
            settle_ms = max(0, int(step.get("settle_ms") or 0))
        elif "wait_ms" in step:
            settle_ms = max(0, int(step.get("wait_ms") or 0))
        else:
            settle_ms = 700
        confirm_ms = (
            max(0, int(step.get("settle_confirm_ms") or 0))
            if "settle_confirm_ms" in step
            else 350
        )
        threshold = float(step["unchanged_threshold"]) if "unchanged_threshold" in step else 0.012
        title_prefix = str(step.get("title_prefix") or f"{req_id}-{step_index}")
        seek_top_first = bool(step.get("seek_top_first", False))
        include_before = bool(step.get("include_before", True))
        method = str(step.get("method") or "drag")
        drag_fraction = float(step["drag_fraction"]) if "drag_fraction" in step else 0.10
        hold_end_ms = int(step["hold_end_ms"]) if "hold_end_ms" in step else 400
        drag_steps = int(step["drag_steps"]) if "drag_steps" in step else 12
        step_ms = int(step["step_ms"]) if "step_ms" in step else 30
        roi = step.get("roi") if isinstance(step.get("roi"), dict) else {}
        roi_nx = float(roi.get("nx", 0.04))
        roi_ny = float(roi.get("ny", 0.55))
        roi_nw = float(roi.get("nw", 0.92))
        roi_nh = float(roi.get("nh", 0.36))

        shot_names: list[str] = []
        seek_metrics: list[ScrollStepMetric] = []
        down_metrics: list[ScrollStepMetric] = []
        _hwnd, rect, _window_title = self._anchor_ready()

        def grab_roi():
            try:
                image = grab_anchor(rect)
            except CaptureError as exc:
                raise AiBatchRunnerError(str(exc)) from exc
            return image, crop_normalized(
                image, nx=roi_nx, ny=roi_ny, nw=roi_nw, nh=roi_nh
            )

        def status_after_scroll() -> tuple[Any, Any, float]:
            """Settle, capture status, re-check once if the panel is still moving."""

            if settle_ms:
                time.sleep(settle_ms / 1000.0)
            image, roi_img = grab_roi()
            residual = 0.0
            if confirm_ms > 0:
                time.sleep(confirm_ms / 1000.0)
                image2, roi2 = grab_roi()
                residual = mean_abs_diff(roi_img, roi2)
                if residual >= threshold:
                    # Still sliding — wait once more, then trust the later frame.
                    time.sleep(settle_ms / 1000.0 if settle_ms else confirm_ms / 1000.0)
                    image, roi_img = grab_roi()
            return image, roi_img, residual

        def run_edge_loop(
            *,
            loop_direction: str,
            limit: int,
            title_stem: str,
            edge_label: str,
            metrics_out: list[ScrollStepMetric],
            start_roi,
            start_index: int = 1,
        ) -> tuple[Any, int, str, bool]:
            previous = start_roi
            applied = 0
            stop_reason = "max_steps"
            at_edge = False
            for index in range(start_index, start_index + limit):
                if self._stop.is_set():
                    raise AiBatchRunnerError("Stopped by user.")
                self._scroll(
                    nx,
                    ny,
                    loop_direction,
                    amount,
                    method=method,
                    drag_fraction=drag_fraction,
                    hold_end_ms=hold_end_ms,
                    drag_steps=drag_steps,
                    step_ms=step_ms,
                )
                applied += 1
                after_image, after_roi, _residual = status_after_scroll()
                delta = mean_abs_diff(previous, after_roi)
                changed = delta >= threshold
                title = f"{title_prefix}-{title_stem}-{index:02d}-status"
                stopped = False
                reason: str | None = None
                if not changed:
                    title = f"{title_prefix}-{title_stem}-{index:02d}-status-at-{edge_label}"
                    stopped = True
                    reason = "unchanged"
                    stop_reason = "unchanged"
                    at_edge = True
                elif index == start_index + limit - 1:
                    title = f"{title_prefix}-{title_stem}-{index:02d}-status-end"
                    reason = "max_steps"
                shot = self._save_shot(session, title, after_image, rect)
                shot_names.append(shot.filename)
                metrics_out.append(
                    ScrollStepMetric(
                        step_index=index,
                        title=title,
                        mean_abs_diff=round(delta, 5),
                        changed=changed,
                        stopped=stopped,
                        stop_reason=reason,
                    )
                )
                previous = after_roi
                if stopped:
                    break
            return previous, applied, stop_reason, at_edge

        before_image, before_roi = grab_roi()
        if include_before:
            label = (
                f"{title_prefix}-00-status-before-seek"
                if seek_top_first
                else f"{title_prefix}-00-status-before"
            )
            shot = self._save_shot(session, label, before_image, rect)
            shot_names.append(shot.filename)

        previous_roi = before_roi
        seek_scrolls = 0
        at_top = False
        if seek_top_first:
            previous_roi, seek_scrolls, _seek_stop, at_top = run_edge_loop(
                loop_direction="up",
                limit=max_seek,
                title_stem="seek-up",
                edge_label="top",
                metrics_out=seek_metrics,
                start_roi=previous_roi,
            )
            top_image, previous_roi = grab_roi()
            top_shot = self._save_shot(session, f"{title_prefix}-10-status-top", top_image, rect)
            shot_names.append(top_shot.filename)

        previous_roi, scrolls_applied, stop_reason, at_bottom = run_edge_loop(
            loop_direction=direction if direction in ("down", "up") else "down",
            limit=max_steps,
            title_stem="down" if direction != "up" else "up",
            edge_label="bottom" if direction != "up" else "top",
            metrics_out=down_metrics,
            start_roi=previous_roi,
        )

        def pack(metrics: list[ScrollStepMetric]) -> list[dict[str, Any]]:
            return [
                {
                    "step_index": item.step_index,
                    "title": item.title,
                    "mean_abs_diff": item.mean_abs_diff,
                    "changed": item.changed,
                    "stopped": item.stopped,
                    "stop_reason": item.stop_reason,
                }
                for item in metrics
            ]

        return {
            "title_prefix": title_prefix,
            "shots": shot_names,
            "scrolls_applied": scrolls_applied,
            "seek_top_first": seek_top_first,
            "seek_top_scrolls": seek_scrolls,
            "at_top": at_top if seek_top_first else None,
            "max_steps": max_steps,
            "amount_per_scroll": amount,
            "method": method,
            "drag_fraction": drag_fraction,
            "hold_end_ms": hold_end_ms,
            "settle_ms": settle_ms,
            "settle_confirm_ms": confirm_ms,
            "direction": direction,
            "unchanged_threshold": threshold,
            "roi": {"nx": roi_nx, "ny": roi_ny, "nw": roi_nw, "nh": roi_nh},
            "at_bottom": at_bottom,
            "stop_reason": stop_reason,
            "seek_steps": pack(seek_metrics),
            "steps": pack(down_metrics),
        }

    def _screenshot(self, session: BatchSession, title: str):
        _hwnd, rect, window_title = self._anchor_ready()
        try:
            image = grab_anchor(rect)
        except CaptureError as exc:
            raise AiBatchRunnerError(str(exc)) from exc
        return self._save_shot(session, title, image, rect, window_title=window_title)

    def _save_shot(
        self,
        session: BatchSession,
        title: str,
        image,
        rect: Rect,
        *,
        window_title: str | None = None,
    ):
        if window_title is None:
            _hwnd, _rect, window_title = self._anchor_ready()
        anchor = {
            "window_title": window_title or "",
            "width": rect.width,
            "height": rect.height,
            "left": rect.left,
            "top": rect.top,
        }
        try:
            return add_shot(session, title=title, image=image, anchor=anchor)
        except (ScreenMapError, OSError) as exc:
            raise AiBatchRunnerError(str(exc)) from exc
