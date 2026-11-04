"""On-screen drawings for Collection Walkthrough mode."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field

from idle_lab.models import Rect
from idle_lab import win32_api


@dataclass
class GuideChoice:
    key: str
    label: str
    detail: str = ""


@dataclass
class GuideCard:
    title: str
    body: str
    hint: str
    choices: list[GuideChoice] = field(default_factory=list)
    accent: str = "#8EE0C2"


class GuideOverlay:
    """Topmost click-through canvas that paints a walkthrough card over the desktop."""

    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self._shown = False
        self._vs: Rect | None = None
        self._anchor: Rect | None = None
        self._card: GuideCard | None = None
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", "magenta")
        self.win.configure(bg="magenta")
        self.canvas = tk.Canvas(self.win, bg="magenta", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()
        self.win.update_idletasks()

    def destroy(self) -> None:
        try:
            self.win.destroy()
        except Exception:
            pass

    def hide(self) -> None:
        self._card = None
        self.canvas.delete("all")
        if self._shown:
            self.win.withdraw()
            self._shown = False

    def show(self, card: GuideCard, anchor: Rect | None) -> None:
        self._card = card
        self._anchor = anchor
        self._sync_geometry()
        if not self._shown:
            self.win.deiconify()
            self.win.update_idletasks()
            hwnd = win32_api.widget_hwnd(self.win)
            win32_api.add_exstyle(hwnd, win32_api.OVERLAY_EXSTYLE)
            win32_api.raise_topmost(hwnd)
            self._shown = True
        self._paint()

    def set_anchor(self, anchor: Rect | None) -> None:
        self._anchor = anchor
        if self._shown and self._card is not None:
            self._paint()

    def _sync_geometry(self) -> None:
        screen = win32_api.virtual_screen()
        if screen == self._vs:
            return
        self._vs = screen
        self.win.geometry(f"{screen.width}x{screen.height}+{screen.left}+{screen.top}")

    def _paint(self) -> None:
        self.canvas.delete("all")
        if self._card is None or self._vs is None:
            return
        card = self._card
        vs = self._vs

        # Highlight anchored window if present.
        if self._anchor is not None:
            ax1 = self._anchor.left - vs.left
            ay1 = self._anchor.top - vs.top
            ax2 = self._anchor.right - vs.left
            ay2 = self._anchor.bottom - vs.top
            self.canvas.create_rectangle(ax1, ay1, ax2, ay2, outline=card.accent, width=3, dash=(8, 4), tags="guide")
            # Corner brackets
            arm = 28
            for x, y, dx, dy in (
                (ax1, ay1, 1, 1),
                (ax2, ay1, -1, 1),
                (ax1, ay2, 1, -1),
                (ax2, ay2, -1, -1),
            ):
                self.canvas.create_line(x, y, x + arm * dx, y, fill=card.accent, width=4, tags="guide")
                self.canvas.create_line(x, y, x, y + arm * dy, fill=card.accent, width=4, tags="guide")

        # Card position: prefer above/left of anchor, else top-left of screen.
        if self._anchor is not None:
            card_left = max(24, self._anchor.left - vs.left)
            card_top = max(24, self._anchor.top - vs.top - 210)
            if card_top < 24:
                card_top = min(vs.height - 220, self._anchor.bottom - vs.top + 16)
        else:
            card_left, card_top = 40, 40

        width = 520
        # Rough height from content.
        body_lines = max(3, len(card.body) // 60 + card.body.count("\n") + 1)
        choice_h = 54 * len(card.choices)
        height = 110 + body_lines * 18 + choice_h
        height = max(160, min(height, 420))

        x1, y1 = card_left, card_top
        x2, y2 = card_left + width, card_top + height

        # Shadow + panel
        self.canvas.create_rectangle(x1 + 4, y1 + 4, x2 + 4, y2 + 4, fill="#0A0C10", outline="", tags="guide")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#141A24", outline=card.accent, width=2, tags="guide")
        self.canvas.create_rectangle(x1, y1, x1 + 8, y2, fill=card.accent, outline="", tags="guide")

        self.canvas.create_text(
            x1 + 22,
            y1 + 18,
            text="COLLECTION WALKTHROUGH",
            anchor="nw",
            fill="#9AA4B2",
            font=("Segoe UI", 9, "bold"),
            tags="guide",
        )
        self.canvas.create_text(
            x1 + 22,
            y1 + 38,
            text=card.title[:64],
            anchor="nw",
            fill="#F2F5F8",
            font=("Segoe UI", 16, "bold"),
            width=width - 40,
            tags="guide",
        )
        self.canvas.create_text(
            x1 + 22,
            y1 + 72,
            text=card.body,
            anchor="nw",
            fill="#C5D0DC",
            font=("Segoe UI", 11),
            width=width - 40,
            tags="guide",
        )

        cy = y2 - 28 - choice_h
        if card.choices:
            self.canvas.create_text(
                x1 + 22,
                cy - 8,
                text="Branches — press a key:",
                anchor="sw",
                fill="#E7C36A",
                font=("Segoe UI", 10, "bold"),
                tags="guide",
            )
            for index, choice in enumerate(card.choices):
                by = cy + index * 54
                self.canvas.create_rectangle(
                    x1 + 18,
                    by,
                    x2 - 18,
                    by + 46,
                    fill="#1C2433",
                    outline="#3A4558",
                    width=1,
                    tags="guide",
                )
                self.canvas.create_oval(x1 + 28, by + 10, x1 + 56, by + 38, outline=card.accent, width=2, tags="guide")
                self.canvas.create_text(
                    x1 + 42,
                    by + 24,
                    text=choice.key,
                    fill=card.accent,
                    font=("Consolas", 14, "bold"),
                    tags="guide",
                )
                self.canvas.create_text(
                    x1 + 68,
                    by + 12,
                    text=choice.label,
                    anchor="nw",
                    fill="#F2F5F8",
                    font=("Segoe UI", 11, "bold"),
                    width=width - 100,
                    tags="guide",
                )
                if choice.detail:
                    self.canvas.create_text(
                        x1 + 68,
                        by + 30,
                        text=choice.detail[:70],
                        anchor="nw",
                        fill="#9AA4B2",
                        font=("Segoe UI", 9),
                        width=width - 100,
                        tags="guide",
                    )

        self.canvas.create_text(
            x1 + 22,
            y2 - 12,
            text=card.hint,
            anchor="sw",
            fill="#8EE0C2",
            font=("Segoe UI", 10, "bold"),
            width=width - 40,
            tags="guide",
        )
