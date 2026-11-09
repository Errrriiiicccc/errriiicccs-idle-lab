"""Interactive LCO molecule marks — draggable, rebindable, not screen-bound."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from idle_lab.composer.lco_placement import MoleculeLcoPlacement
from idle_lab.models import Rect

_SIZE = 34
_OUTLINE = "#9FD4F0"
_FILL = "#1A2836"
_GLYPH = "#F2F6FA"
_ORANGE = "#E0A050"
_ORANGE_FILL = "#2A1C08"
_RED = "#F09595"
_RED_FILL = "#301018"
_GRAY_OUTLINE = "#4A5058"
_GRAY_FILL = "#141618"
_GRAY_GLYPH = "#7A8088"
_TITLE_BG = "#1A222C"
_TITLE_FG = "#F2F6FA"


@dataclass
class MoleculeMarkVisual:
    hotkey: str | None
    title: str
    rebinding: bool = False
    conflict_flash: bool = False
    dimmed: bool = False
    show_title: bool = False


class MoleculeMark(tk.Toplevel):
    """Small non-click-through badge over the game; drag moves, click starts rebind."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        molecule_id: str,
        on_moved: Callable[[str, float, float], None],
        on_released: Callable[[str, float, float], None],
        on_rebind_click: Callable[[str], None],
    ) -> None:
        super().__init__(root)
        self.molecule_id = molecule_id
        self._on_moved = on_moved
        self._on_released = on_released
        self._on_rebind_click = on_rebind_click
        self.dragging = False
        self._press_xy: tuple[int, int] | None = None
        self._moved = False
        self._anchor: Rect | None = None
        self._nx = 0.08
        self._ny = 0.42
        self._visual = MoleculeMarkVisual(hotkey="?", title=molecule_id)
        self._flash_job: str | None = None

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "magenta")
        self.configure(bg="magenta")
        self.canvas = tk.Canvas(
            self,
            width=_SIZE + 120,
            height=_SIZE + 28,
            bg="magenta",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.withdraw()

    def destroy_mark(self) -> None:
        if self._flash_job is not None:
            try:
                self.after_cancel(self._flash_job)
            except Exception:
                pass
            self._flash_job = None
        try:
            self.destroy()
        except Exception:
            pass

    def apply_placement(self, placement: MoleculeLcoPlacement, *, anchor: Rect) -> None:
        self._anchor = anchor
        self._nx = float(placement.nx)
        self._ny = float(placement.ny)
        self._visual.hotkey = placement.hotkey
        self._visual.title = placement.title or placement.molecule_id
        self._paint()
        self._place()

    def set_visual(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._visual, key):
                setattr(self._visual, key, value)
        self._paint()
        self._place()

    def flash_conflict(self, duration_ms: int = 1000) -> None:
        self._visual.conflict_flash = True
        self._paint()
        if self._flash_job is not None:
            try:
                self.after_cancel(self._flash_job)
            except Exception:
                pass

        def _clear() -> None:
            self._flash_job = None
            self._visual.conflict_flash = False
            self._paint()

        self._flash_job = self.after(duration_ms, _clear)

    def _place(self) -> None:
        if self._anchor is None or self.dragging:
            return
        screen_x = int(self._anchor.left + self._nx * self._anchor.width)
        screen_y = int(self._anchor.top + self._ny * self._anchor.height)
        w = _SIZE + (120 if self._visual.show_title else 0)
        h = _SIZE + (22 if self._visual.show_title else 0)
        left = screen_x - _SIZE // 2
        top = screen_y - _SIZE // 2
        self.geometry(f"{w}x{h}+{left}+{top}")
        if not self.winfo_viewable():
            self.deiconify()
            self.lift()

    def _paint(self) -> None:
        self.canvas.delete("all")
        v = self._visual
        if v.rebinding:
            outline, fill, glyph = _ORANGE, _ORANGE_FILL, "?"
            text = "?"
        elif v.conflict_flash:
            outline, fill, glyph = _RED, _RED_FILL, _GLYPH
            text = (v.hotkey or "?")[:1]
        elif v.dimmed:
            outline, fill, glyph = _GRAY_OUTLINE, _GRAY_FILL, _GRAY_GLYPH
            text = (v.hotkey or "?")[:1]
        else:
            outline, fill, glyph = _OUTLINE, _FILL, _GLYPH
            text = (v.hotkey or "?")[:1]
        r = _SIZE
        self.canvas.create_oval(2, 2, r - 2, r - 2, fill=fill, outline=outline, width=2)
        self.canvas.create_text(r // 2, r // 2, text=text, fill=glyph, font=("Segoe UI", 11, "bold"))
        if v.show_title:
            label = (v.title or "")[:22]
            self.canvas.create_rectangle(
                r + 4,
                4,
                r + 8 + 7 * max(len(label), 1),
                r - 4,
                fill=_TITLE_BG,
                outline=outline,
            )
            self.canvas.create_text(
                r + 10,
                r // 2,
                text=label,
                fill=_TITLE_FG,
                font=("Segoe UI", 9),
                anchor="w",
            )

    def _press(self, event) -> None:
        self.dragging = True
        self._moved = False
        self._press_xy = (int(event.x_root), int(event.y_root))

    def _drag(self, event) -> None:
        if not self.dragging or self._anchor is None:
            return
        if self._press_xy is not None:
            dx = abs(int(event.x_root) - self._press_xy[0])
            dy = abs(int(event.y_root) - self._press_xy[1])
            if dx + dy > 4:
                self._moved = True
        left = int(event.x_root) - _SIZE // 2
        top = int(event.y_root) - _SIZE // 2
        w = _SIZE + (120 if self._visual.show_title else 0)
        h = _SIZE + (22 if self._visual.show_title else 0)
        self.geometry(f"{w}x{h}+{left}+{top}")
        nx = (float(event.x_root) - self._anchor.left) / max(self._anchor.width, 1)
        ny = (float(event.y_root) - self._anchor.top) / max(self._anchor.height, 1)
        self._nx = min(0.98, max(0.02, nx))
        self._ny = min(0.98, max(0.02, ny))
        self._on_moved(self.molecule_id, self._nx, self._ny)

    def _release(self, event) -> None:
        was_drag = self.dragging
        moved = self._moved
        self.dragging = False
        self._press_xy = None
        self._moved = False
        if not was_drag:
            return
        if self._anchor is not None:
            nx = (float(event.x_root) - self._anchor.left) / max(self._anchor.width, 1)
            ny = (float(event.y_root) - self._anchor.top) / max(self._anchor.height, 1)
            self._nx = min(0.98, max(0.02, nx))
            self._ny = min(0.98, max(0.02, ny))
            self._on_released(self.molecule_id, self._nx, self._ny)
        if not moved:
            self._on_rebind_click(self.molecule_id)


class MoleculeMarkLayer:
    """Owns the set of molecule badges for an LCO session."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        on_moved: Callable[[str, float, float], None],
        on_released: Callable[[str, float, float], None],
        on_rebind_click: Callable[[str], None],
    ) -> None:
        self.root = root
        self._on_moved = on_moved
        self._on_released = on_released
        self._on_rebind_click = on_rebind_click
        self._marks: dict[str, MoleculeMark] = {}
        self._rebinding_id: str | None = None
        self._show_titles = False

    def clear(self) -> None:
        for mark in list(self._marks.values()):
            mark.destroy_mark()
        self._marks.clear()
        self._rebinding_id = None

    def sync(
        self,
        placements: list[MoleculeLcoPlacement],
        *,
        anchor: Rect,
        rebinding_id: str | None = None,
        show_titles: bool = False,
    ) -> None:
        self._rebinding_id = rebinding_id
        self._show_titles = bool(show_titles)
        want = {p.molecule_id for p in placements if p.enabled}
        for mid in list(self._marks):
            if mid not in want:
                self._marks.pop(mid).destroy_mark()
        for place in placements:
            if not place.enabled:
                continue
            mark = self._marks.get(place.molecule_id)
            if mark is None:
                mark = MoleculeMark(
                    self.root,
                    molecule_id=place.molecule_id,
                    on_moved=self._on_moved,
                    on_released=self._on_released,
                    on_rebind_click=self._on_rebind_click,
                )
                self._marks[place.molecule_id] = mark
            mark.apply_placement(place, anchor=anchor)
            rebinding = rebinding_id == place.molecule_id
            dimmed = rebinding_id is not None and not rebinding
            mark.set_visual(
                hotkey=place.hotkey,
                title=place.title,
                rebinding=rebinding,
                dimmed=dimmed,
                show_title=show_titles,
            )

    def flash_conflict(self, molecule_id: str) -> None:
        mark = self._marks.get(molecule_id)
        if mark is not None:
            mark.flash_conflict()

    def set_show_titles(self, show: bool) -> None:
        self._show_titles = bool(show)
        for mark in self._marks.values():
            mark.set_visual(show_title=self._show_titles)
