"""Observation session: timeline.jsonl + Screen Map dual-write shots."""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageFilter

from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.models import Rect, screen_to_normalized
from idle_lab.screen_map.batch import BatchSession, ScreenMapError, add_shot, create_batch
from idle_lab.screen_map.manifest import load_manifest, save_manifest
from idle_lab.screen_map.names import sanitize_slug, unique_dir


class ObservationError(RuntimeError):
    """User-facing observation failure."""


# Maturity ladder (see docs/GAMEPLAY-TEST.md):
# - discovery: sparse scaled JPEG keyframes + coalesced timeline
# - refined: crop ROIs (panel/default_crop) + same sparse rules
# - semantic: timeline only (marks optional)
@dataclass(frozen=True)
class ObservationPolicy:
    mode: str = "discovery"
    frames: str = "sparse"  # sparse | before_after_click | before_only | marks_only | none
    move_hz: float = 12.0
    move_min_px: float = 6.0
    drag_threshold_px: float = 12.0
    settle_ms: int = 180
    burst_gap_ms: int = 350
    debounce_down_ms: int = 45
    debounce_locus_px: float = 16.0
    max_pending_frames: int = 2
    max_shots: int = 30
    keyframe_min_interval_ms: int = 2000
    nav_ny_min: float = 0.92
    defer_session_start: bool = True
    flush_every_ms: int = 2000
    keyframe_scale: float = 0.5
    keyframe_format: str = "jpeg"  # jpeg | png — marks always png full-res
    jpeg_quality: int = 65
    skip_similar: bool = True
    similar_hash_threshold: int = 6
    # Refined default: lower upgrade-panel band (Tower-ish). Override per target later.
    default_crop: tuple[float, float, float, float] | None = None
    refined_panel_crop: tuple[float, float, float, float] = (0.02, 0.50, 0.96, 0.42)


@dataclass
class ObservationSummary:
    folder: Path
    title: str
    shot_count: int
    event_count: int
    duration_ms: int
    end_reason: str


@dataclass
class _PendingDown:
    button: str
    x: int
    y: int
    nx: float
    ny: float
    t_ms: int
    down_at: float


@dataclass
class _OpenBurst:
    button: str
    nx: float
    ny: float
    x: int
    y: int
    count: int
    started_t_ms: int
    last_t_ms: int
    nav: bool


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _rect_meta(rect: Rect) -> dict[str, int]:
    return {
        "left": int(rect.left),
        "top": int(rect.top),
        "width": int(rect.width),
        "height": int(rect.height),
    }


def _anchor_payload(title: str | None, rect: Rect | None) -> dict[str, Any] | None:
    if rect is None:
        return None
    return {"title": title or "", "rect": _rect_meta(rect)}


def auto_observation_title(when: datetime | None = None) -> str:
    stamp = (when or datetime.now()).strftime("%Y-%m-%d %H%M")
    return f"Observation {stamp}"


def crop_normalized(image: Image.Image, crop: tuple[float, float, float, float]) -> Image.Image:
    nx, ny, nw, nh = crop
    w, h = image.size
    left = max(0, int(round(nx * w)))
    top = max(0, int(round(ny * h)))
    right = min(w, int(round((nx + nw) * w)))
    bottom = min(h, int(round((ny + nh) * h)))
    if right <= left or bottom <= top:
        return image
    return image.crop((left, top, right, bottom))


def average_hash(image: Image.Image, size: int = 8) -> int:
    gray = image.convert("L").resize((size, size), Image.Resampling.BILINEAR)
    pixels = list(gray.getdata())
    avg = sum(pixels) / max(len(pixels), 1)
    bits = 0
    for i, value in enumerate(pixels):
        if value >= avg:
            bits |= 1 << i
    return bits


def hash_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


class ObservationController:
    """Owns one active observation (Screen Map batch + timeline)."""

    def __init__(
        self,
        *,
        policy: ObservationPolicy | None = None,
        clock: Callable[[], float] | None = None,
        grab_fn: Callable[[Rect | None], Image.Image] | None = None,
    ) -> None:
        self.policy = policy or ObservationPolicy()
        self._clock = clock or time.perf_counter
        self._grab_fn = grab_fn or grab_anchor
        self.active = False
        self.batch: BatchSession | None = None
        self.folder: Path | None = None
        self.title = ""
        self.end_reason = ""
        self._started_at_wall = ""
        self._t0 = 0.0
        self._event_i = 0
        self._counts = self._empty_counts()
        self._anchor_title: str | None = None
        self._anchor_rect: Rect | None = None
        self._last_sample_xy: tuple[int, int] | None = None
        self._last_sample_at = 0.0
        self._pending: _PendingDown | None = None
        self._open_burst: _OpenBurst | None = None
        self._burst_gen = 0
        self._wheel_gen = 0
        self._session_start_taken = False
        self._last_down_xy: tuple[int, int] | None = None
        self._last_down_at = 0.0
        self._last_keyframe_at = 0.0
        self._last_hash: int | None = None
        self._last_flush_at = 0.0
        self._timeline: Path | None = None
        self._header_path: Path | None = None
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self._jobs: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
        self._pending_frames = 0
        self.ui_events: queue.Queue = queue.Queue()

    @staticmethod
    def _empty_counts() -> dict[str, int]:
        return {
            "events": 0,
            "clicks": 0,
            "scrolls": 0,
            "drags": 0,
            "marks": 0,
            "shots": 0,
            "frames_dropped": 0,
            "bursts": 0,
            "clicks_coalesced": 0,
            "downs_debounced": 0,
            "similar_skipped": 0,
            "live_control_actions": 0,
        }

    @property
    def shot_count(self) -> int:
        return len(self.batch.manifest.shots) if self.batch else 0

    def start(
        self,
        screen_maps_root: Path,
        *,
        title: str | None = None,
        anchor_title: str | None = None,
        anchor_rect: Rect | None = None,
    ) -> BatchSession:
        if self.active:
            raise ObservationError("An observation is already active.")
        if anchor_rect is None:
            raise ObservationError("Anchor a window before starting an observation.")
        human = (title or "").strip() or auto_observation_title()
        screen_maps_root = Path(screen_maps_root)
        screen_maps_root.mkdir(parents=True, exist_ok=True)
        try:
            batch = create_batch(screen_maps_root, human)
        except ScreenMapError as exc:
            raise ObservationError(str(exc)) from exc
        self.batch = batch
        self.folder = batch.folder
        self.title = human
        self.active = True
        self.end_reason = ""
        self._started_at_wall = _now_iso()
        self._t0 = self._clock()
        self._event_i = 0
        self._counts = self._empty_counts()
        self._anchor_title = anchor_title
        self._anchor_rect = anchor_rect
        self._last_sample_xy = None
        self._last_sample_at = 0.0
        self._pending = None
        self._open_burst = None
        self._burst_gen = 0
        self._wheel_gen = 0
        self._session_start_taken = False
        self._last_down_xy = None
        self._last_down_at = 0.0
        self._last_keyframe_at = 0.0
        self._last_hash = None
        self._last_flush_at = self._clock()
        self._timeline = batch.folder / "timeline.jsonl"
        self._header_path = batch.folder / "observation.json"
        self._timeline.write_text("", encoding="utf-8")
        self._write_header(ended=False)
        self._pending_frames = 0
        self._jobs = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, name="observation-frames", daemon=True)
        self._worker.start()
        self._append(
            {
                "type": "session_start",
                "anchor": _anchor_payload(anchor_title, anchor_rect),
                "policy": asdict(self.policy),
            }
        )
        if (
            not self.policy.defer_session_start
            and self.policy.mode != "semantic"
            and self.policy.frames != "none"
        ):
            self._take_session_start(anchor_title, anchor_rect)
        return batch

    def handle_move(
        self,
        x: int,
        y: int,
        *,
        anchor_title: str | None,
        anchor_rect: Rect | None,
    ) -> None:
        if not self.active or self._pending is not None:
            return
        self._maybe_anchor_changed(anchor_title, anchor_rect)
        if anchor_rect is None:
            return
        now = self._clock()
        min_dt = 1.0 / max(self.policy.move_hz, 1.0)
        if self._last_sample_at and (now - self._last_sample_at) < min_dt:
            return
        if self._last_sample_xy is not None:
            dx = x - self._last_sample_xy[0]
            dy = y - self._last_sample_xy[1]
            if (dx * dx + dy * dy) < (self.policy.move_min_px * self.policy.move_min_px):
                return
        self._last_sample_xy = (x, y)
        self._last_sample_at = now
        nx, ny = screen_to_normalized(anchor_rect, x, y)
        self._append({"type": "pointer_sample", "x": x, "y": y, "nx": nx, "ny": ny})

    def handle_button(
        self,
        *,
        down: bool,
        button: str,
        x: int,
        y: int,
        anchor_title: str | None,
        anchor_rect: Rect | None,
    ) -> None:
        if not self.active:
            return
        self._maybe_anchor_changed(anchor_title, anchor_rect)
        if anchor_rect is None:
            return
        self._ensure_session_start(anchor_title, anchor_rect)
        nx, ny = screen_to_normalized(anchor_rect, x, y)
        t_ms = self._t_ms()
        if down:
            if self._pending is not None:
                return
            if self._should_debounce_down(x, y):
                self._counts["downs_debounced"] += 1
                return
            self._last_down_xy = (x, y)
            self._last_down_at = self._clock()
            self._pending = _PendingDown(
                button=button,
                x=x,
                y=y,
                nx=nx,
                ny=ny,
                t_ms=t_ms,
                down_at=self._clock(),
            )
            if self.policy.frames == "before_after_click":
                self._append(
                    {
                        "type": "pointer_down",
                        "button": button,
                        "x": x,
                        "y": y,
                        "nx": nx,
                        "ny": ny,
                    }
                )
                self._enqueue_shot(
                    role="before",
                    title=f"before {button}",
                    event_type="pointer_down_frame",
                    extra={"button": button},
                    rect=anchor_rect,
                    window_title=anchor_title,
                    force=True,
                )
            return

        pending = self._pending
        if pending is None or pending.button != button:
            return
        self._pending = None
        hold_ms = int((self._clock() - pending.down_at) * 1000)
        dist_sq = (x - pending.x) ** 2 + (y - pending.y) ** 2
        is_drag = dist_sq >= (self.policy.drag_threshold_px * self.policy.drag_threshold_px)
        if is_drag:
            self._flush_open_burst(write_timeline=True)
            self._counts["drags"] += 1
            self._append(
                {
                    "type": "drag",
                    "button": button,
                    "x0": pending.x,
                    "y0": pending.y,
                    "x1": x,
                    "y1": y,
                    "nx0": pending.nx,
                    "ny0": pending.ny,
                    "nx1": nx,
                    "ny1": ny,
                    "duration_ms": hold_ms,
                }
            )
            self._schedule_keyframe(
                kind="drag",
                title=f"after drag {self._counts['drags']}",
                rect=anchor_rect,
                window_title=anchor_title,
                extra={"button": button, "drag": True},
                force=True,
            )
            return

        self._counts["clicks"] += 1
        is_nav = ny >= float(self.policy.nav_ny_min)
        if self.policy.frames == "before_after_click":
            self._append(
                {
                    "type": "pointer_up",
                    "button": button,
                    "x": x,
                    "y": y,
                    "nx": nx,
                    "ny": ny,
                    "hold_ms": hold_ms,
                    "nav": is_nav,
                }
            )
            self._enqueue_shot(
                role="after",
                title=f"after click {self._counts['clicks']}",
                event_type="pointer_up_frame",
                extra={"button": button},
                rect=anchor_rect,
                window_title=anchor_title,
                delay_s=max(0, self.policy.settle_ms) / 1000.0,
                force=True,
            )
            return

        self._note_click_burst(
            button=button,
            x=x,
            y=y,
            nx=nx,
            ny=ny,
            t_ms=t_ms,
            nav=is_nav,
            rect=anchor_rect,
            window_title=anchor_title,
        )

    def handle_wheel(
        self,
        *,
        x: int,
        y: int,
        dy: int,
        anchor_title: str | None,
        anchor_rect: Rect | None,
    ) -> None:
        if not self.active or dy == 0:
            return
        self._maybe_anchor_changed(anchor_title, anchor_rect)
        if anchor_rect is None:
            return
        self._ensure_session_start(anchor_title, anchor_rect)
        self._flush_open_burst(write_timeline=True)
        nx, ny = screen_to_normalized(anchor_rect, x, y)
        self._counts["scrolls"] += 1
        self._append({"type": "wheel", "x": x, "y": y, "nx": nx, "ny": ny, "dy": int(dy)})
        if self.policy.frames in {"none", "marks_only"} or self.policy.mode == "semantic":
            return
        self._wheel_gen += 1
        gen = self._wheel_gen
        delay = max(int(self.policy.burst_gap_ms), int(self.policy.settle_ms)) / 1000.0
        self._enqueue_shot(
            role="after",
            title=f"after scroll {self._counts['scrolls']}",
            event_type="keyframe",
            extra={"kind": "wheel", "dy": int(dy), "gen": gen},
            rect=anchor_rect,
            window_title=anchor_title,
            delay_s=delay,
            gen=("wheel", gen),
            force=True,
        )

    def mark(
        self,
        *,
        label: str | None = None,
        anchor_title: str | None = None,
        anchor_rect: Rect | None = None,
    ) -> None:
        if not self.active:
            raise ObservationError("No observation is active.")
        self._maybe_anchor_changed(anchor_title, anchor_rect)
        if anchor_rect is None:
            raise ObservationError("Anchor not ready — mark refused.")
        self._ensure_session_start(anchor_title, anchor_rect)
        self._flush_open_burst(write_timeline=True)
        self._counts["marks"] += 1
        human = (label or "").strip() or f"mark {self._counts['marks']}"
        self._enqueue_shot(
            role="mark",
            title=human,
            event_type="mark",
            extra={"label": human},
            rect=anchor_rect,
            window_title=anchor_title,
            force=True,
            full_res=True,
        )

    def note_live_control(
        self,
        *,
        action: str,
        phase: str,
        detail: str = "",
        meta: dict[str, Any] | None = None,
        anchor_title: str | None = None,
        anchor_rect: Rect | None = None,
        capture: bool = True,
    ) -> None:
        """Record a Live Control Overlay action (timeline + optional forced keyframe).

        Injected Live Control mouse is ignored by the Observation hook, so Live Control
        must push evidence explicitly during troubleshoot sessions.
        """

        if not self.active:
            raise ObservationError("No observation is active.")
        phase_norm = (phase or "").strip().lower() or "after"
        if phase_norm not in {"before", "after"}:
            phase_norm = "after"
        action_id = (action or "").strip() or "live_control"
        self._maybe_anchor_changed(anchor_title, anchor_rect)
        if capture and anchor_rect is None:
            raise ObservationError("Anchor not ready — Live Control evidence refused.")
        self._ensure_session_start(anchor_title, anchor_rect)
        self._flush_open_burst(write_timeline=True)
        self._counts["live_control_actions"] += 1
        payload_meta = dict(meta or {})
        human = (detail or "").strip() or f"{action_id} {phase_norm}"
        self._append(
            {
                "type": "live_control_action",
                "action": action_id,
                "phase": phase_norm,
                "detail": human,
                "meta": payload_meta,
            }
        )
        if not capture or anchor_rect is None:
            return
        title = f"live-control {action_id} {phase_norm}"
        self._enqueue_shot(
            role=phase_norm,
            title=title,
            event_type="keyframe",
            extra={
                "kind": "live_control",
                "action": action_id,
                "phase": phase_norm,
                "detail": human,
                "meta": payload_meta,
            },
            rect=anchor_rect,
            window_title=anchor_title,
            delay_s=0.0,
            force=True,
        )

    def stop(self, *, reason: str = "operator") -> ObservationSummary | None:
        if not self.active or self.batch is None or self.folder is None:
            self.active = False
            return None
        self.end_reason = reason or "operator"
        self._pending = None
        self._flush_open_burst(write_timeline=True)
        if self._burst_gen > 0 and self._anchor_rect is not None and self.policy.frames not in {
            "none",
            "marks_only",
        }:
            self._enqueue_shot(
                role="after",
                title=f"after burst {self._counts['bursts'] + 1}",
                event_type="keyframe",
                extra={"kind": "burst", "flush": True, "gen": self._burst_gen},
                rect=self._anchor_rect,
                window_title=self._anchor_title,
                delay_s=0.0,
                gen=("burst", self._burst_gen),
                force=True,
            )
        self._jobs.put(None)
        if self._worker is not None:
            self._worker.join(timeout=30)
        self._worker = None
        duration_ms = self._t_ms()
        self._append(
            {
                "type": "session_end",
                "reason": self.end_reason,
                "counts": dict(self._counts),
                "duration_ms": duration_ms,
            }
        )
        self._write_header(ended=True, duration_ms=duration_ms)
        try:
            from idle_lab.observation.digest import write_observation_digest

            write_observation_digest(self.folder)
        except Exception:
            pass
        summary = ObservationSummary(
            folder=self.folder,
            title=self.title,
            shot_count=self.shot_count,
            event_count=self._counts["events"],
            duration_ms=duration_ms,
            end_reason=self.end_reason,
        )
        self.active = False
        self.batch = None
        self.ui_events.put(("ended", summary))
        return summary

    def rename(self, new_title: str) -> Path:
        if self.active:
            raise ObservationError("Stop the observation before renaming.")
        folder = self.folder
        if folder is None or not folder.exists():
            raise ObservationError("No observation folder to rename.")
        human = (new_title or "").strip()
        if not human:
            raise ObservationError("New title is required.")
        parent = folder.parent
        slug = sanitize_slug(human, fallback="observation")
        target = unique_dir(parent, slug)
        if target.resolve() != folder.resolve():
            folder.rename(target)
            folder = target
            self.folder = folder
        self.title = human
        manifest = load_manifest(folder)
        manifest.batch_title = human
        manifest.batch_slug = folder.name
        save_manifest(folder, manifest)
        header_path = folder / "observation.json"
        if header_path.is_file():
            try:
                payload = json.loads(header_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            payload["title"] = human
            payload["id"] = folder.name
            header_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            from idle_lab.observation.digest import write_observation_digest

            write_observation_digest(folder)
        except Exception:
            pass
        return folder

    def drain_ui(self) -> list:
        items = []
        while True:
            try:
                items.append(self.ui_events.get_nowait())
            except queue.Empty:
                break
        return items

    # --- internals ---------------------------------------------------------

    def _t_ms(self) -> int:
        return int((self._clock() - self._t0) * 1000)

    def _should_debounce_down(self, x: int, y: int) -> bool:
        if self._last_down_xy is None:
            return False
        dt = (self._clock() - self._last_down_at) * 1000.0
        if dt > float(self.policy.debounce_down_ms):
            return False
        dx = x - self._last_down_xy[0]
        dy = y - self._last_down_xy[1]
        return (dx * dx + dy * dy) <= (self.policy.debounce_locus_px * self.policy.debounce_locus_px)

    def _same_locus(self, nx: float, ny: float, other_nx: float, other_ny: float) -> bool:
        # ~normalized distance corresponding to debounce_locus_px on a ~600px-wide window.
        lim = 0.04
        return abs(nx - other_nx) <= lim and abs(ny - other_ny) <= lim

    def _note_click_burst(
        self,
        *,
        button: str,
        x: int,
        y: int,
        nx: float,
        ny: float,
        t_ms: int,
        nav: bool,
        rect: Rect,
        window_title: str | None,
    ) -> None:
        with self._lock:
            burst = self._open_burst
            merge = (
                burst is not None
                and burst.button == button
                and self._same_locus(nx, ny, burst.nx, burst.ny)
                and (t_ms - burst.last_t_ms) <= int(self.policy.burst_gap_ms)
                and (self.policy.mode == "semantic" or self.policy.frames in {"none", "marks_only"} or not nav)
            )
            if merge and burst is not None:
                burst.count += 1
                burst.last_t_ms = t_ms
                self._counts["clicks_coalesced"] += 1
                should_schedule = self.policy.frames not in {"none", "marks_only"} and self.policy.mode != "semantic"
                force_frame = False
            else:
                should_schedule = False
                force_frame = nav
        if merge:
            if should_schedule:
                self._schedule_keyframe(
                    kind="burst",
                    title=f"after burst {self._counts['bursts'] + 1}",
                    rect=rect,
                    window_title=window_title,
                    extra={"button": button, "nav": False, "nx": nx, "ny": ny},
                    force=False,
                )
            return

        self._flush_open_burst(write_timeline=True)
        with self._lock:
            self._open_burst = _OpenBurst(
                button=button,
                nx=nx,
                ny=ny,
                x=x,
                y=y,
                count=1,
                started_t_ms=t_ms,
                last_t_ms=t_ms,
                nav=nav,
            )
        if self.policy.frames in {"none", "marks_only"} or self.policy.mode == "semantic":
            return
        self._schedule_keyframe(
            kind="burst",
            title=f"after burst {self._counts['bursts'] + 1}",
            rect=rect,
            window_title=window_title,
            extra={"button": button, "nav": nav, "nx": nx, "ny": ny},
            force=force_frame,
        )

    def _flush_open_burst(self, *, write_timeline: bool) -> None:
        with self._lock:
            burst = self._open_burst
            self._open_burst = None
        if burst is None or not write_timeline:
            return
        if burst.count <= 1:
            self._append(
                {
                    "type": "pointer_up",
                    "button": burst.button,
                    "x": burst.x,
                    "y": burst.y,
                    "nx": burst.nx,
                    "ny": burst.ny,
                    "nav": burst.nav,
                    "count": 1,
                }
            )
            return
        self._append(
            {
                "type": "pointer_burst",
                "button": burst.button,
                "x": burst.x,
                "y": burst.y,
                "nx": burst.nx,
                "ny": burst.ny,
                "count": burst.count,
                "dt_ms": max(0, burst.last_t_ms - burst.started_t_ms),
                "nav": burst.nav,
            }
        )

    def _ensure_session_start(self, anchor_title: str | None, anchor_rect: Rect | None) -> None:
        if self._session_start_taken:
            return
        if self.policy.mode == "semantic" or self.policy.frames == "none":
            self._session_start_taken = True
            return
        if anchor_rect is None:
            return
        self._take_session_start(anchor_title, anchor_rect)

    def _take_session_start(self, anchor_title: str | None, anchor_rect: Rect | None) -> None:
        if self._session_start_taken or anchor_rect is None:
            return
        self._session_start_taken = True
        self._enqueue_shot(
            role="session-start",
            title="session start",
            event_type="mark",
            extra={"label": "session_start"},
            rect=anchor_rect,
            window_title=anchor_title,
            force=True,
            full_res=True,
        )

    def _schedule_keyframe(
        self,
        *,
        kind: str,
        title: str,
        rect: Rect,
        window_title: str | None,
        extra: dict[str, Any],
        force: bool = False,
    ) -> None:
        # Coalesce spam: only the latest *non-forced* burst settle should win.
        # Forced frames (nav / drag) must not share that cancellation token —
        # otherwise a drag ~1s after a tab click drops the nav keyframe.
        gen_id: tuple[str, int] | None = None
        gen_extra: dict[str, Any] = {"kind": kind, **extra}
        if kind == "burst":
            self._burst_gen += 1
            if not force:
                gen_id = ("burst", self._burst_gen)
                gen_extra["gen"] = self._burst_gen
        elif kind == "drag":
            # Invalidate in-flight burst settles (panel scrolled) without
            # tagging the drag shot as a cancellable burst generation.
            self._burst_gen += 1
        delay = max(int(self.policy.burst_gap_ms), int(self.policy.settle_ms)) / 1000.0
        if force:
            delay = max(0, int(self.policy.settle_ms)) / 1000.0
        self._enqueue_shot(
            role="after",
            title=title,
            event_type="keyframe",
            extra=gen_extra,
            rect=rect,
            window_title=window_title,
            delay_s=delay,
            gen=gen_id,
            force=force,
        )

    def _maybe_anchor_changed(self, title: str | None, rect: Rect | None) -> None:
        if rect is None:
            return
        prev = self._anchor_rect
        changed = prev is None or (
            prev.left != rect.left
            or prev.top != rect.top
            or prev.right != rect.right
            or prev.bottom != rect.bottom
            or (title or "") != (self._anchor_title or "")
        )
        if not changed:
            return
        self._anchor_rect = rect
        self._anchor_title = title
        self._append({"type": "anchor_changed", "anchor": _anchor_payload(title, rect)})

    def _append(self, record: dict[str, Any]) -> None:
        if self._timeline is None:
            return
        payload = {"t_ms": self._t_ms(), "ts": _now_iso(), "i": self._event_i, **record}
        self._event_i += 1
        self._counts["events"] += 1
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            with self._timeline.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
        self._maybe_periodic_flush()

    def _maybe_periodic_flush(self) -> None:
        now = self._clock()
        if (now - self._last_flush_at) * 1000.0 < float(self.policy.flush_every_ms):
            return
        self._last_flush_at = now
        self._write_header(ended=False)

    def _write_header(self, *, ended: bool, duration_ms: int | None = None) -> None:
        if self._header_path is None or self.folder is None:
            return
        payload: dict[str, Any] = {
            "version": 1,
            "kind": "observation",
            "id": self.folder.name,
            "title": self.title,
            "created_at": self._started_at_wall,
            "anchor": _anchor_payload(self._anchor_title, self._anchor_rect),
            "policy": asdict(self.policy),
            "counts": dict(self._counts),
        }
        if ended:
            payload["ended_at"] = _now_iso()
            payload["duration_ms"] = int(duration_ms or self._t_ms())
            payload["end_reason"] = self.end_reason
        text = json.dumps(payload, indent=2) + "\n"
        with self._lock:
            self._header_path.write_text(text, encoding="utf-8")

    def _resolve_crop(self, role: str) -> tuple[float, float, float, float] | None:
        if self.policy.default_crop is not None:
            return self.policy.default_crop
        if self.policy.mode == "refined" and role not in {"session-start", "mark"}:
            return self.policy.refined_panel_crop
        return None

    def _enqueue_shot(
        self,
        *,
        role: str,
        title: str,
        event_type: str,
        extra: dict[str, Any],
        rect: Rect,
        window_title: str | None,
        delay_s: float = 0.0,
        gen: tuple[str, int] | None = None,
        force: bool = False,
        full_res: bool = False,
    ) -> None:
        if self.policy.frames == "none" and not force:
            return
        if self.policy.frames == "marks_only" and role not in {"mark", "session-start"} and not force:
            return
        if self.policy.mode == "semantic" and role not in {"mark"} and not force:
            return
        try:
            job_q = self._jobs.qsize()
        except NotImplementedError:  # pragma: no cover
            job_q = 0
        with self._lock:
            if (
                not force
                and self.policy.max_shots > 0
                and self._counts["shots"] + self._pending_frames >= self.policy.max_shots
            ):
                self._counts["frames_dropped"] += 1
                return
            if (not force) and (
                self._pending_frames >= self.policy.max_pending_frames or job_q >= self.policy.max_pending_frames
            ):
                self._counts["frames_dropped"] += 1
                return
            # Adaptive budget: non-forced keyframes must respect min interval.
            if (
                not force
                and role == "after"
                and self._last_keyframe_at
                and (self._clock() - self._last_keyframe_at) * 1000.0 < float(self.policy.keyframe_min_interval_ms)
            ):
                self._counts["frames_dropped"] += 1
                return
            self._pending_frames += 1
        self._jobs.put(
            (
                "shot",
                {
                    "role": role,
                    "title": title,
                    "event_type": event_type,
                    "extra": extra,
                    "rect": rect,
                    "window_title": window_title,
                    "delay_s": delay_s,
                    "gen": gen,
                    "crop": self._resolve_crop(role),
                    "full_res": full_res or role in {"mark", "session-start"},
                    "force": force,
                },
            )
        )

    def _worker_loop(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                break
            kind, payload = job
            try:
                if kind == "shot":
                    self._do_shot(payload)
            except Exception as exc:  # pragma: no cover
                self.ui_events.put(("error", str(exc)))
            finally:
                with self._lock:
                    self._pending_frames = max(0, self._pending_frames - 1)

    def _do_shot(self, payload: dict[str, Any]) -> None:
        delay_s = float(payload.get("delay_s") or 0.0)
        if delay_s > 0:
            time.sleep(delay_s)
        gen = payload.get("gen")
        if isinstance(gen, tuple) and len(gen) == 2:
            family, number = gen
            if family == "burst" and number != self._burst_gen:
                self._counts["frames_dropped"] += 1
                return
            if family == "wheel" and number != self._wheel_gen:
                self._counts["frames_dropped"] += 1
                return
        # Flush coalesced click timeline when the burst keyframe actually fires.
        if payload.get("extra", {}).get("kind") == "burst":
            self._flush_open_burst(write_timeline=True)
        rect: Rect = payload["rect"]
        try:
            image = self._grab_fn(rect)
        except CaptureError as exc:
            self.ui_events.put(("error", f"Observation capture failed: {exc}"))
            return
        except Exception as exc:  # pragma: no cover
            self.ui_events.put(("error", f"Observation capture failed: {exc}"))
            return
        crop = payload.get("crop")
        if crop is not None:
            try:
                image = crop_normalized(image, tuple(crop))  # type: ignore[arg-type]
            except Exception:
                pass
        full_res = bool(payload.get("full_res"))
        if not full_res and self.policy.keyframe_scale < 0.999:
            scale = max(0.2, min(1.0, float(self.policy.keyframe_scale)))
            w = max(1, int(image.width * scale))
            h = max(1, int(image.height * scale))
            image = image.resize((w, h), Image.Resampling.BILINEAR)
        # Forced nav/drag/wheel frames bypass near-dupe skip — tab changes can
        # look similar at half-res hash when combat VFX dominate the frame.
        if self.policy.skip_similar and not full_res and not payload.get("force"):
            try:
                digest = average_hash(image.filter(ImageFilter.BoxBlur(1)))
            except Exception:
                digest = average_hash(image)
            if self._last_hash is not None and hash_distance(digest, self._last_hash) <= int(
                self.policy.similar_hash_threshold
            ):
                self._counts["similar_skipped"] += 1
                self._counts["frames_dropped"] += 1
                return
            self._last_hash = digest
        elif self.policy.skip_similar and not full_res and payload.get("force"):
            try:
                self._last_hash = average_hash(image.filter(ImageFilter.BoxBlur(1)))
            except Exception:
                self._last_hash = average_hash(image)
        if payload.get("extra", {}).get("kind") == "burst":
            self._counts["bursts"] += 1
        self._last_keyframe_at = self._clock()
        self._save_dual(image, payload)

    def _save_dual(self, image: Image.Image, payload: dict[str, Any]) -> None:
        batch = self.batch
        if batch is None:
            return
        title = str(payload.get("title") or "shot")
        full_res = bool(payload.get("full_res"))
        use_jpeg = (not full_res) and self.policy.keyframe_format.lower() in {"jpg", "jpeg"}
        # Compact per-shot meta — full anchor lives on observation.json.
        anchor_meta = {
            "role": payload.get("role"),
            "crop": payload.get("crop"),
            "scaled": not full_res,
            "format": "jpeg" if use_jpeg else "png",
        }
        try:
            with self._lock:
                if self.policy.max_shots > 0 and len(batch.manifest.shots) >= self.policy.max_shots:
                    self._counts["frames_dropped"] += 1
                    return
                shot = add_shot(
                    batch,
                    title=title,
                    image=image,
                    anchor=anchor_meta,
                    image_format="jpeg" if use_jpeg else "png",
                    jpeg_quality=int(self.policy.jpeg_quality),
                )
                self._counts["shots"] = len(batch.manifest.shots)
        except (ScreenMapError, OSError) as exc:
            self.ui_events.put(("error", f"Observation save failed: {exc}"))
            return
        self._append(
            {
                "type": str(payload.get("event_type") or "mark"),
                "shot": shot.filename,
                "role": payload.get("role"),
                **(payload.get("extra") or {}),
            }
        )
        self.ui_events.put(("shot", shot.filename, self.shot_count))
