"""Shared paint helpers — Live Overlay Lab and Atom Create import these (no fork)."""

from __future__ import annotations

from typing import Any

MARK_R = 15
GLYPH = "#F2F6FA"
QUEUE_NUM = "#F0C070"
CURRENT_OUTLINE = "#7CF0B8"
CURRENT_FILL = "#184838"
QUEUED_OUTLINE = "#E0A050"
QUEUED_FILL = "#2A1C08"
IDLE_OUTLINE = "#4A5058"
IDLE_FILL = "#141618"
PAUSED_OUTLINE = "#4A5058"
PAUSED_FILL = "#141618"
DESC_LINE = "#C8D4E0"
DESC_BOX_OUTLINE = "#D8E2EC"
DESC_BOX_FILL = "#1A222C"
DESC_TEXT = "#F2F6FA"


def nx_to_canvas(nx: float, ny: float, *, width: int, height: int) -> tuple[int, int]:
    x = int(round(float(nx) * max(width - 1, 0)))
    y = int(round(float(ny) * max(height - 1, 0)))
    return x, y


def queue_index(queue: list[str] | tuple[str, ...], token: str) -> int | None:
    want = str(token or "").strip().upper()
    if not want:
        return None
    for i, item in enumerate(queue):
        if str(item or "").strip().upper() == want:
            return i
    return None


def activity_style(
    *,
    current: bool = False,
    queued: bool = False,
    paused: bool = False,
) -> tuple[str, str]:
    if paused:
        return PAUSED_OUTLINE, PAUSED_FILL
    if current:
        return CURRENT_OUTLINE, CURRENT_FILL
    if queued:
        return QUEUED_OUTLINE, QUEUED_FILL
    return IDLE_OUTLINE, IDLE_FILL


def draw_queue_n(canvas: Any, x: int, y: int, n: int, *, r: int = MARK_R) -> None:
    canvas.create_text(
        x,
        y - r - 8,
        text=str(n),
        fill=QUEUE_NUM,
        font=("Segoe UI", 10, "bold"),
    )


def draw_key_circle(
    canvas: Any,
    x: int,
    y: int,
    glyph: str,
    *,
    outline: str,
    fill: str,
    queue_n: int | None = None,
    r: int = MARK_R,
) -> None:
    canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
    canvas.create_text(x, y, text=glyph, fill=GLYPH, font=("Segoe UI", 11, "bold"))
    if queue_n is not None:
        draw_queue_n(canvas, x, y, queue_n, r=r)


def draw_line(canvas: Any, x0: int, y0: int, x1: int, y1: int, *, fill: str = DESC_LINE) -> None:
    canvas.create_line(x0, y0, x1, y1, fill=fill, width=1)


def draw_label_box(
    canvas: Any,
    x: int,
    y: int,
    text: str,
    *,
    outline: str = DESC_BOX_OUTLINE,
    fill: str = DESC_BOX_FILL,
    text_fill: str = DESC_TEXT,
) -> None:
    pad_x, pad_y = 8, 4
    tw = max(40, int(len(text) * 7))
    th = 16
    canvas.create_rectangle(
        x - tw // 2 - pad_x,
        y - th // 2 - pad_y,
        x + tw // 2 + pad_x,
        y + th // 2 + pad_y,
        outline=outline,
        fill=fill,
        width=1,
    )
    canvas.create_text(x, y, text=text, fill=text_fill, font=("Segoe UI", 10))
