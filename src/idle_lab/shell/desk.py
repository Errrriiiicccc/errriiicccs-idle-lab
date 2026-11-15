"""Middle action desk — one visible pane; builders run lazily on first visit."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from idle_lab.shell.nav import normalize_nav_path


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
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._builders = dict(builders)
        self._panes: dict[str, ctk.CTkFrame] = {}
        self._active: str | None = None

    @property
    def active_path(self) -> str | None:
        return self._active

    def show(self, path: str) -> str:
        key = normalize_nav_path(path)
        if key == self._active and key in self._panes:
            return key
        if key not in self._panes:
            holder = ctk.CTkFrame(self, fg_color="transparent")
            builder = self._builders.get(key)
            if builder is not None:
                builder(holder)
            else:
                ctk.CTkLabel(
                    holder,
                    text=f"No pane for {key}",
                    text_color="#E7C36A",
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=12)
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
