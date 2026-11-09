"""Standalone LCO console window — live log, copy, user comments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from idle_lab.live_control.console import ConsoleSession

_BG = "#141A22"
_PANEL = "#0E1319"
_MUTED = "#7E8796"
_ACCENT = "#9FD4F0"
_BTN = "#2A3140"
_BTN_HOVER = "#3A4558"


class LcoConsoleWindow(ctk.CTkToplevel):
    """Resizable console surface owned by the lab when console is ON."""

    _deactivate_windows_window_header_manipulation = True

    def __init__(
        self,
        master: Any,
        *,
        console: ConsoleSession,
        on_close: Callable[[], None] | None = None,
        on_geometry: Callable[[str], None] | None = None,
        geometry: str | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Idle Lab · LCO Console")
        self.configure(fg_color=_BG)
        self.minsize(420, 280)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        self._console = console
        self._on_close = on_close
        self._on_geometry = on_geometry
        self._show_timestamps = True
        self._geometry_job: str | None = None
        self._refresh_job: str | None = None

        if geometry:
            try:
                self.geometry(geometry)
            except Exception:
                self.geometry("560x420")
        else:
            self.geometry("560x420")

        self.protocol("WM_DELETE_WINDOW", self._handle_close)
        self._build()
        self.bind("<Configure>", self._on_configure)
        self.after(0, self._lift)
        self.refresh()

    def _lift(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _build(self) -> None:
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=10)

        toolbar = ctk.CTkFrame(pad, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            toolbar,
            text="LCO Console",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=_ACCENT,
        ).pack(side="left")

        self.copy_button = ctk.CTkButton(
            toolbar,
            text="Copy",
            width=72,
            height=28,
            fg_color=_BTN,
            hover_color=_BTN_HOVER,
            command=self._copy_log,
        )
        self.copy_button.pack(side="right")

        self.timestamps_button = ctk.CTkButton(
            toolbar,
            text="Timestamps: ON",
            width=128,
            height=28,
            fg_color=_BTN,
            hover_color=_BTN_HOVER,
            command=self._toggle_timestamps,
        )
        self.timestamps_button.pack(side="right", padx=(0, 8))

        self.log = ctk.CTkTextbox(
            pad,
            fg_color=_PANEL,
            text_color="#DCE4EE",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            activate_scrollbars=True,
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        comment_row = ctk.CTkFrame(pad, fg_color="transparent")
        comment_row.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            comment_row,
            text="User Comment:",
            text_color=_MUTED,
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        self.comment_entry = ctk.CTkEntry(
            comment_row,
            placeholder_text="",
            height=32,
            fg_color=_PANEL,
            border_color="#2A3140",
        )
        self.comment_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.comment_entry.bind("<Return>", self._send_comment_event)

        self.send_button = ctk.CTkButton(
            comment_row,
            text="Send",
            width=72,
            height=32,
            fg_color="#1E3A4A",
            hover_color="#2A5568",
            text_color=_ACCENT,
            command=self._send_comment,
        )
        self.send_button.pack(side="left")

        self.status = ctk.CTkLabel(
            pad,
            text="",
            anchor="w",
            text_color=_MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.status.pack(fill="x", pady=(6, 0))

    def refresh(self) -> None:
        """Pull the latest console lines into the textbox."""

        if not self.winfo_exists():
            return
        lines = self._console.snapshot(show_timestamps=self._show_timestamps)
        text = "\n".join(lines)
        at_end = self._near_bottom()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        if text:
            self.log.insert("1.0", text)
        self.log.configure(state="disabled")
        if at_end:
            self.log.see("end")
        folder = self._console.folder.name if self._console.folder else "—"
        level = self._console.verbosity
        self.status.configure(text=f"verbosity={level} · {folder}")

    def schedule_refresh(self) -> None:
        """Coalesce bursty worker-thread updates onto the UI thread."""

        if self._refresh_job is not None:
            return
        try:
            self._refresh_job = self.after(50, self._do_scheduled_refresh)
        except Exception:
            self._refresh_job = None

    def _do_scheduled_refresh(self) -> None:
        self._refresh_job = None
        self.refresh()

    def _near_bottom(self) -> bool:
        try:
            return float(self.log.yview()[1]) >= 0.98
        except Exception:
            return True

    def _toggle_timestamps(self) -> None:
        self._show_timestamps = not self._show_timestamps
        state = "ON" if self._show_timestamps else "OFF"
        self.timestamps_button.configure(text=f"Timestamps: {state}")
        self.refresh()

    def _copy_log(self) -> None:
        text = "\n".join(self._console.snapshot(show_timestamps=self._show_timestamps))
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.configure(text="Copied to clipboard.")
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text=f"Copy failed: {exc}")

    def _send_comment_event(self, _event=None) -> None:
        self._send_comment()

    def _send_comment(self) -> None:
        text = self.comment_entry.get()
        if not self._console.user_comment(text):
            self.status.configure(text="Enter a comment first." if not str(text or "").strip() else "Console is off.")
            return
        self.comment_entry.delete(0, "end")
        self.refresh()
        self.status.configure(text="Comment logged.")

    def _handle_close(self) -> None:
        if self._on_close is not None:
            try:
                self._on_close()
                return
            except Exception:
                pass
        self.destroy_window()

    def destroy_window(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass

    def current_geometry(self) -> str:
        return self.geometry()

    def _on_configure(self, _event=None) -> None:
        if self._on_geometry is None or not self.winfo_viewable():
            return
        if self._geometry_job is not None:
            try:
                self.after_cancel(self._geometry_job)
            except Exception:
                pass

        def save() -> None:
            self._geometry_job = None
            if self._on_geometry is None or not self.winfo_viewable():
                return
            try:
                self._on_geometry(self.geometry())
            except Exception:
                pass

        self._geometry_job = self.after(400, save)
