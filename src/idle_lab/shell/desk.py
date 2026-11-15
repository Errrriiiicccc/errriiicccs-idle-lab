"""Middle action desk — one visible pane; builders run lazily on first visit."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look, default_look
from idle_lab.shell.nav import normalize_nav_path
from idle_lab.shell.paint import paint_widget_tree


PaneBuilder = Callable[[ctk.CTkFrame], Any]


class ActionDesk(ctk.CTkFrame):
    """Single middle host. Left rail drives ``show(path)``; no inner lab tabs.

    Panes build lazily on first visit, then stay stacked via ``place`` + ``lift``
    so return trips do not re-run pack geometry on hundreds of widgets.
    """

    def __init__(
        self,
        master,
        *,
        builders: dict[str, PaneBuilder],
        look: Look | None = None,
        **kwargs,
    ) -> None:
        self._look = look or default_look()
        super().__init__(master, fg_color=self._look.bg, **kwargs)
        self._builders = dict(builders)
        self._panes: dict[str, ctk.CTkFrame] = {}
        self._active: str | None = None

    def apply_look(self, look: Look) -> None:
        self._look = look
        try:
            self.configure(fg_color=look.bg)
        except Exception:
            pass
        for pane in self._panes.values():
            paint_widget_tree(pane, look)

    @property
    def active_path(self) -> str | None:
        return self._active

    def show(self, path: str) -> str:
        key = normalize_nav_path(path)
        if key == self._active and key in self._panes:
            return key
        if key not in self._panes:
            holder = ctk.CTkFrame(self, fg_color=self._look.bg)
            builder = self._builders.get(key)
            if builder is not None:
                builder(holder)
            else:
                ctk.CTkLabel(
                    holder,
                    text=f"No pane for {key}",
                    text_color=self._look.esc_pop,
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=12)
            paint_widget_tree(holder, self._look)
            try:
                holder.place(relx=0, rely=0, relwidth=1, relheight=1)
            except Exception:
                holder.pack(fill="both", expand=True)
            self._panes[key] = holder
        try:
            self._panes[key].lift()
            self._panes[key].tkraise()
        except Exception:
            pass
        self._active = key
        return key

    def get(self) -> str:
        return self._active or "Info"

    def set(self, path: str) -> str:
        """Tabview-compatible alias used by older App call sites."""

        return self.show(path)
