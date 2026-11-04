"""Control panel for anchoring a window and playing presets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from idle_lab.anchor import Anchor
from idle_lab.automations.mouse_sync import play_points_sync
from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.ui import AutomationsPanel
from idle_lab.click_logger import ClickLogger
from idle_lab.hotkeys import InputHooks
from idle_lab.models import ClickPoint, Preset, normalized_to_screen, screen_to_normalized
from idle_lab.overlay import Overlay
from idle_lab.player import Player
from idle_lab.presets import PresetError, PresetStore, load_preset, preset_to_dict, project_root, slug
from idle_lab.recorder import Recorder
from idle_lab.settings_store import load_settings, save_settings
from idle_lab import win32_api

MODE_FROM_LABEL = {
    "Instantaneous": "instantaneous",
    "One second": "one_second",
    "Realtime": "realtime",
}
MODE_LABELS = {value: key for key, value in MODE_FROM_LABEL.items()}
STATUS_COLOR = {
    "info": "#9AA4B2",
    "ok": "#8EE0C2",
    "warn": "#E7C36A",
    "error": "#F09595",
    "run": "#8EE0C2",
}


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Errriiiccc's Idle Lab")
        self.geometry("1100x920")
        self.minsize(900, 700)
        root = project_root()
        self.store = PresetStore(root / "presets")
        self.settings_path = root / "settings.json"
        self.settings, settings_error = load_settings(self.settings_path)
        self.auto_store = AutomationStore(root / "automations")
        auto_errors = self.auto_store.load_all()
        self.auto_runtime = AutomationRuntime(
            store=self.auto_store,
            runs_dir=root / "runs",
            get_anchor_rect=self._automation_anchor_rect,
            play_preset=self._automation_play_preset,
        )
        self.auto_panel: AutomationsPanel | None = None
        self.anchor_target = Anchor()
        self.recorder = Recorder()
        self.player = Player()
        self.hooks = InputHooks()
        self.current: Preset | None = None
        self._rows: list[dict] = []
        self._load_depth = 0
        self._alive = True
        self._anchor_waiting = False
        self._logger: ClickLogger | None = None
        self._active_index: int | None = None
        self._begin_load()
        self._build()
        self._end_load()
        self.update_idletasks()
        self.overlay = Overlay(self, self._on_marker_moved, self._on_marker_released)
        errors = self.store.load_all()
        if self.store.presets:
            self._select(self.store.presets[0])
        else:
            self._rebuild_preset_list()
            self._rebuild_points()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.hooks.start()
        except OSError as exc:
            self._status(f"Hotkeys unavailable: {exc}", "error")
        self.after(120, self._poll_anchor)
        self.after(30, self._drain_hooks)
        self.after(50, self._drain_player)
        self.after(80, self._drain_automations)
        if settings_error:
            self._status(settings_error, "warn")
        elif errors:
            self._status("Skipped preset files: " + "; ".join(errors), "error")
        elif auto_errors:
            self._status("Skipped automation files: " + "; ".join(auto_errors), "error")
        else:
            self._status("Set anchor, then click the emulator window.", "info")

    def _build(self) -> None:
        self.status_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=980)
        self.status_label.pack(side="bottom", fill="x", padx=12, pady=(4, 10))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        clicker = self.tabs.add("Clicker")
        automations = self.tabs.add("Automations")

        self.body = ctk.CTkScrollableFrame(clicker, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=4, pady=(4, 0))
        self._build_clicker_body()

        self.auto_panel = AutomationsPanel(
            automations,
            store=self.auto_store,
            on_reload=self._reload_automations,
            on_start=self._start_automations,
            on_stop=self._stop_automations,
        )
        self.auto_panel.pack(fill="both", expand=True)

    def _build_clicker_body(self) -> None:
        header = ctk.CTkFrame(self.body, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(header, text="Errriiiccc's Idle Lab", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Presets are fractions of the anchored window, so they follow moves and resizes.",
            text_color="#9AA4B2",
            wraplength=520,
            justify="left",
        ).pack(anchor="w")

        anchor_frame = ctk.CTkFrame(self.body)
        anchor_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(anchor_frame, text="Anchor", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.anchor_label = ctk.CTkLabel(anchor_frame, text="No window anchored", anchor="w")
        self.anchor_label.pack(fill="x", padx=10)
        anchor_buttons = ctk.CTkFrame(anchor_frame, fg_color="transparent")
        anchor_buttons.pack(fill="x", padx=10, pady=(6, 10))
        self.anchor_button = ctk.CTkButton(anchor_buttons, text="Set anchor", width=140, command=self._toggle_anchor_mode)
        self.anchor_button.pack(side="left", padx=(0, 8))
        self.clear_button = ctk.CTkButton(anchor_buttons, text="Clear", width=90, command=self._clear_anchor)
        self.clear_button.pack(side="left")

        play_frame = ctk.CTkFrame(self.body)
        play_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(play_frame, text="Playback", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        options = ctk.CTkFrame(play_frame, fg_color="transparent")
        options.pack(fill="x", padx=10, pady=4)
        self.method_menu = ctk.CTkOptionMenu(
            options,
            values=["Foreground", "Background"],
            command=self._on_method,
            width=150,
        )
        self.method_menu.set("Background" if self.settings.click_method == "background" else "Foreground")
        self.method_menu.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(options, text="Countdown").pack(side="left", padx=(8, 4))
        self.countdown_menu = ctk.CTkOptionMenu(
            options,
            values=["0", "1", "3"],
            command=self._on_countdown,
            width=70,
        )
        self.countdown_menu.set(str(self.settings.countdown_seconds))
        self.countdown_menu.pack(side="left")

        switches = ctk.CTkFrame(play_frame, fg_color="transparent")
        switches.pack(fill="x", padx=10, pady=4)
        self.focus_switch = ctk.CTkSwitch(switches, text="Focus window first", command=self._on_focus_switch)
        self.restore_switch = ctk.CTkSwitch(switches, text="Restore cursor", command=self._on_restore_switch)
        if self.settings.focus_before_run:
            self.focus_switch.select()
        if self.settings.restore_cursor:
            self.restore_switch.select()
        self.focus_switch.pack(side="left", padx=(0, 16))
        self.restore_switch.pack(side="left")

        loops = ctk.CTkFrame(play_frame, fg_color="transparent")
        loops.pack(fill="x", padx=10, pady=4)
        self.forever_switch = ctk.CTkSwitch(loops, text="Loop forever", command=self._save_loop_from_ui)
        self.forever_switch.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(loops, text="Loops").pack(side="left", padx=(0, 4))
        self.loop_entry = ctk.CTkEntry(loops, width=60)
        self.loop_entry.insert(0, "2")
        self.loop_entry.pack(side="left")
        self.loop_entry.bind("<Return>", lambda _event: self._save_loop_from_ui())
        self.loop_entry.bind("<FocusOut>", lambda _event: self._save_loop_from_ui())
        self.forever_switch.select()
        self.loop_entry.configure(state="disabled")

        actions = ctk.CTkFrame(play_frame, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(4, 4))
        self.start_button = ctk.CTkButton(actions, text="Start", width=90, command=self._start_playback)
        self.stop_button = ctk.CTkButton(actions, text="Stop", width=90, command=self._stop_playback)
        self.pause_button = ctk.CTkButton(actions, text="Pause", width=90, command=self._toggle_pause)
        self.logger_button = ctk.CTkButton(actions, text="Click logger", width=120, command=self._open_logger)
        self.start_button.pack(side="left", padx=(0, 6))
        self.stop_button.pack(side="left", padx=(0, 6))
        self.pause_button.pack(side="left", padx=(0, 6))
        self.logger_button.pack(side="left")
        ctk.CTkLabel(
            play_frame,
            text="F6 starts or stops. F7 pauses. Esc stops a run. F6 and F7 are captured while this app is open.",
            text_color="#9AA4B2",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        preset_frame = ctk.CTkFrame(self.body)
        preset_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(preset_frame, text="Presets", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.preset_list = ctk.CTkScrollableFrame(preset_frame, height=84)
        self.preset_list.pack(fill="x", padx=10, pady=4)
        preset_buttons = ctk.CTkFrame(preset_frame, fg_color="transparent")
        preset_buttons.pack(fill="x", padx=10, pady=4)
        self.create_button = ctk.CTkButton(preset_buttons, text="Create", width=80, command=self._create_preset)
        self.rename_button = ctk.CTkButton(preset_buttons, text="Rename", width=80, command=self._rename_preset)
        self.duplicate_button = ctk.CTkButton(preset_buttons, text="Duplicate", width=90, command=self._duplicate_preset)
        self.delete_button = ctk.CTkButton(preset_buttons, text="Delete", width=80, command=self._delete_preset)
        for button in (self.create_button, self.rename_button, self.duplicate_button, self.delete_button):
            button.pack(side="left", padx=(0, 6))
        file_buttons = ctk.CTkFrame(preset_frame, fg_color="transparent")
        file_buttons.pack(fill="x", padx=10, pady=(0, 6))
        self.reload_button = ctk.CTkButton(file_buttons, text="Reload", width=80, command=self._reload_presets)
        self.import_button = ctk.CTkButton(file_buttons, text="Import", width=80, command=self._import_preset)
        self.export_button = ctk.CTkButton(file_buttons, text="Export", width=80, command=self._export_preset)
        for button in (self.reload_button, self.import_button, self.export_button):
            button.pack(side="left", padx=(0, 6))
        self.notes_label = ctk.CTkLabel(preset_frame, text="", anchor="w", justify="left", wraplength=520, text_color="#C5D0DC")
        self.notes_label.pack(fill="x", padx=10, pady=(0, 8))

        points_frame = ctk.CTkFrame(self.body)
        points_frame.pack(fill="both", expand=True, padx=12, pady=(6, 8))
        ctk.CTkLabel(points_frame, text="Points", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.banner = ctk.CTkLabel(points_frame, text="", anchor="w", justify="left", wraplength=520, text_color="#E7C36A")
        self.banner.pack(fill="x", padx=10)
        header_row = ctk.CTkFrame(points_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(4, 0))
        for text_label, width in (("#", 28), ("Position", 110), ("Delay", 64), ("Hold", 64), ("Label", 140)):
            ctk.CTkLabel(header_row, text=text_label, width=width, anchor="w", text_color="#9AA4B2").pack(side="left", padx=2)
        self.points_list = ctk.CTkFrame(points_frame, fg_color="transparent")
        self.points_list.pack(fill="x", padx=10, pady=(4, 10))
        self._sync_controls()

    def _switch_on(self, switch) -> bool:
        return switch.get() in (1, True, "1", "on")

    def _loading(self) -> bool:
        return self._load_depth > 0

    def _begin_load(self) -> None:
        self._load_depth += 1

    def _end_load(self) -> None:
        self._load_depth = max(0, self._load_depth - 1)

    def _status(self, text: str, level: str) -> None:
        self.status_label.configure(text=text, text_color=STATUS_COLOR.get(level, "#9AA4B2"))

    def _busy(self) -> bool:
        return self.recorder.active or self.player.is_active

    def _sync_controls(self) -> None:
        busy = self._busy()
        self.anchor_button.configure(text="Cancel anchor" if self._anchor_waiting else "Set anchor")
        self.anchor_button.configure(state="disabled" if busy else "normal")
        self.clear_button.configure(state="disabled" if busy else "normal")
        self.create_button.configure(state="disabled" if busy else "normal")
        can_edit = self.current is not None and not busy
        for button in (self.rename_button, self.duplicate_button, self.delete_button, self.export_button):
            button.configure(state="normal" if can_edit else "disabled")
        self.start_button.configure(state="disabled" if busy or self.current is None else "normal")
        self.stop_button.configure(state="normal" if self.player.is_active else "disabled")
        self.pause_button.configure(state="normal" if self.player.is_active else "disabled")
        self._update_banner()

    def _update_banner(self) -> None:
        if self.recorder.active:
            label = MODE_LABELS.get(self.recorder.mode, self.recorder.mode)
            self.banner.configure(
                text=f"Recording {label}. {len(self.recorder.points)} points. Space adds a point. Esc saves."
            )
        else:
            self.banner.configure(text="")

    def _save_settings(self) -> None:
        save_settings(self.settings_path, self.settings)

    def _on_method(self, value: str) -> None:
        if self._loading():
            return
        self.settings.click_method = "background" if value == "Background" else "foreground"
        self._save_settings()

    def _on_countdown(self, value: str) -> None:
        if self._loading():
            return
        self.settings.countdown_seconds = int(value)
        self._save_settings()

    def _on_focus_switch(self) -> None:
        if self._loading():
            return
        self.settings.focus_before_run = self._switch_on(self.focus_switch)
        self._save_settings()

    def _on_restore_switch(self) -> None:
        if self._loading():
            return
        self.settings.restore_cursor = self._switch_on(self.restore_switch)
        self._save_settings()

    def _poll_anchor(self) -> None:
        try:
            status, _hwnd, rect, title = self.anchor_target.snapshot()
            self._render_anchor(status, rect, title)
            if status == "ok" and rect is not None:
                self.overlay.set_visible(True)
                self.overlay.set_frame(rect)
                self._place_markers(rect)
            else:
                self.overlay.set_visible(False)
        except Exception as exc:
            self._status(f"Anchor poll failed: {exc}", "error")
        if self._alive:
            self.after(100, self._poll_anchor)

    def _render_anchor(self, status: str, rect, title: str) -> None:
        if status == "ok" and rect is not None:
            text = f"{title}   {rect.width} x {rect.height}"
        elif status == "minimized":
            text = f"{title} is minimized"
        elif status == "closed":
            text = "Anchored window closed"
        else:
            text = "No window anchored"
        self.anchor_label.configure(text=text)

    def _toggle_anchor_mode(self) -> None:
        if self._busy():
            return
        if self._anchor_waiting:
            self._cancel_anchor_mode()
            return
        self._anchor_waiting = True
        self.hooks.state.anchor_armed = True
        self._sync_controls()
        self._status("Click the emulator window. Esc cancels. That click is not passed to the game.", "warn")

    def _cancel_anchor_mode(self) -> None:
        self._anchor_waiting = False
        self.hooks.state.anchor_armed = False
        self._sync_controls()
        self._status("Anchor cancelled.", "info")

    def _apply_anchor(self, hwnd: int) -> None:
        self._anchor_waiting = False
        self._sync_controls()
        error = self.anchor_target.capture(hwnd)
        if error:
            self._status(error, "error")
            return
        _status, _hwnd, _rect, title = self.anchor_target.snapshot()
        self._status(f"Anchored to {title}.", "ok")

    def _clear_anchor(self) -> None:
        if self._busy():
            return
        self._cancel_anchor_mode()
        self.anchor_target.clear()
        self.overlay.set_visible(False)
        self._status("Anchor cleared.", "info")

    def _edited_points(self) -> list[ClickPoint]:
        if self.recorder.active:
            return self.recorder.points
        if self.current is not None:
            return self.current.points
        return []

    def _place_markers(self, rect) -> None:
        if self.player.is_active:
            self.overlay.set_markers([], False)
            return
        points = self._edited_points()
        coords = [normalized_to_screen(rect, point.nx, point.ny) for point in points]
        self.overlay.set_markers(coords, True)

    def _on_marker_moved(self, index: int, x: int, y: int) -> None:
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        points = self._edited_points()
        if status != "ok" or rect is None or index >= len(points):
            return
        nx, ny = screen_to_normalized(rect, x, y)
        points[index].nx = min(1.0, max(0.0, nx))
        points[index].ny = min(1.0, max(0.0, ny))
        self._set_coord_text(index)

    def _on_marker_released(self, index: int, x: int, y: int) -> None:
        self._on_marker_moved(index, x, y)
        if not self.recorder.active:
            self._persist_current()

    def _set_coord_text(self, index: int) -> None:
        points = self._edited_points()
        if index >= len(self._rows) or index >= len(points):
            return
        point = points[index]
        self._rows[index]["coord"].configure(text=f"{point.nx:.3f}, {point.ny:.3f}")

    def _persist_current(self) -> None:
        if self.current is None or self.recorder.active:
            return
        self.store.save(self.current)

    def _rebuild_preset_list(self) -> None:
        for child in self.preset_list.winfo_children():
            child.destroy()
        for preset in self.store.presets:
            selected = self.current is not None and preset.path == self.current.path
            button = ctk.CTkButton(
                self.preset_list,
                text=preset.name,
                anchor="w",
                fg_color="#1f6aa5" if selected else "transparent",
                command=lambda item=preset: self._select(item),
            )
            button.pack(fill="x", pady=2)

    def _select(self, preset: Preset) -> None:
        if self.recorder.active:
            return
        self._begin_load()
        try:
            self.current = preset
            self._rebuild_preset_list()
            self._apply_loop_controls(preset)
            notes = preset.notes.strip()
            self.notes_label.configure(text=notes if notes else "")
            self._rebuild_points()
        finally:
            self._end_load()
        self._sync_controls()

    def _select_path(self, path: str | None) -> None:
        if path is None:
            self.current = None
            self._rebuild_preset_list()
            self._rebuild_points()
            self._sync_controls()
            return
        for preset in self.store.presets:
            if preset.path == path:
                self._select(preset)
                return
        self.current = self.store.presets[0] if self.store.presets else None
        if self.current is not None:
            self._select(self.current)
        else:
            self._rebuild_preset_list()
            self._rebuild_points()
            self._sync_controls()

    def _apply_loop_controls(self, preset: Preset) -> None:
        forever = preset.loop and preset.loop_count is None
        if forever:
            self.forever_switch.select()
            self.loop_entry.configure(state="disabled")
        else:
            self.forever_switch.deselect()
            self.loop_entry.configure(state="normal")
            count = preset.loop_count if preset.loop else 1
            if not count:
                count = 1
            self.loop_entry.delete(0, "end")
            self.loop_entry.insert(0, str(count))

    def _save_loop_from_ui(self) -> None:
        if self._loading() or self.current is None or self._busy():
            return
        forever = self._switch_on(self.forever_switch)
        if forever:
            self.current.loop = True
            self.current.loop_count = None
            self.loop_entry.configure(state="disabled")
        else:
            self.loop_entry.configure(state="normal")
            try:
                count = int(self.loop_entry.get().strip())
            except ValueError:
                self._status("Loop count must be a whole number.", "error")
                return
            if count < 1:
                self._status("Loop count must be at least 1.", "error")
                return
            self.current.loop = True
            self.current.loop_count = count
        self._persist_current()

    def _rebuild_points(self) -> None:
        self._begin_load()
        try:
            for child in self.points_list.winfo_children():
                child.destroy()
            self._rows = []
            points = self._edited_points()
            if not points:
                ctk.CTkLabel(
                    self.points_list,
                    text="Create a preset, then press Space on each spot.",
                    text_color="#9AA4B2",
                ).pack(anchor="w", pady=6)
                return
            editable = "disabled" if self.player.is_active else "normal"
            for index, point in enumerate(points):
                row = ctk.CTkFrame(self.points_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                number = ctk.CTkLabel(row, text=str(index + 1), width=28, anchor="w")
                number.pack(side="left", padx=2)
                coord = ctk.CTkLabel(row, text=f"{point.nx:.3f}, {point.ny:.3f}", width=110, anchor="w")
                coord.pack(side="left", padx=2)
                delay = ctk.CTkEntry(row, width=64)
                delay.insert(0, str(point.delay_ms))
                delay.configure(state=editable)
                delay.pack(side="left", padx=2)
                hold = ctk.CTkEntry(row, width=64)
                hold.insert(0, str(point.hold_ms))
                hold.configure(state=editable)
                hold.pack(side="left", padx=2)
                label = ctk.CTkEntry(row, width=140)
                label.insert(0, point.label)
                label.configure(state=editable)
                label.pack(side="left", padx=2)
                delay.bind("<Return>", lambda _event, i=index: self._commit_row(i))
                delay.bind("<FocusOut>", lambda _event, i=index: self._commit_row(i))
                hold.bind("<Return>", lambda _event, i=index: self._commit_row(i))
                hold.bind("<FocusOut>", lambda _event, i=index: self._commit_row(i))
                label.bind("<Return>", lambda _event, i=index: self._commit_row(i))
                label.bind("<FocusOut>", lambda _event, i=index: self._commit_row(i))
                self._rows.append({"number": number, "coord": coord, "delay": delay, "hold": hold, "label": label, "frame": row})
        finally:
            self._end_load()
        self._highlight_row(self._active_index)
        self._update_banner()

    def _highlight_row(self, index: int | None) -> None:
        for row_index, row in enumerate(self._rows):
            color = "#1f6aa5" if index is not None and row_index == index else "transparent"
            row["frame"].configure(fg_color=color)

    def _commit_row(self, index: int) -> None:
        if self._loading() or self.player.is_active:
            return
        points = self._edited_points()
        if index >= len(points) or index >= len(self._rows):
            return
        row = self._rows[index]
        try:
            delay = int(row["delay"].get().strip())
            hold = int(row["hold"].get().strip())
        except ValueError:
            self._status("Delay and hold must be whole milliseconds.", "error")
            return
        if delay < 0 or hold < 1:
            self._status("Delay must be 0 or more, and hold must be at least 1 ms.", "error")
            return
        point = points[index]
        label = row["label"].get()
        changed = point.delay_ms != delay or point.hold_ms != hold or point.label != label
        point.delay_ms = delay
        point.hold_ms = hold
        point.label = label
        if changed and not self.recorder.active:
            self._persist_current()

    def _modal(self, title: str, width: int, height: int) -> ctk.CTkToplevel:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.after(250, lambda: dialog.attributes("-topmost", False))
        return dialog

    def _ask_name(self, title: str, initial: str) -> str | None:
        result: dict[str, str | None] = {"value": None}
        dialog = self._modal(title, 380, 160)
        ctk.CTkLabel(dialog, text="Name").pack(anchor="w", padx=16, pady=(16, 6))
        entry = ctk.CTkEntry(dialog, width=340)
        entry.pack(padx=16)
        entry.insert(0, initial)
        entry.select_range(0, "end")

        def ok(_event=None) -> None:
            text = entry.get().strip()
            if not text:
                return
            result["value"] = text
            dialog.destroy()

        def cancel(_event=None) -> None:
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Cancel", width=90, command=cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Save", width=90, command=ok).pack(side="right")
        entry.bind("<Return>", ok)
        dialog.bind("<Escape>", cancel)
        entry.focus()
        self.wait_window(dialog)
        return result["value"]

    def _ask_new_preset(self) -> tuple[str, str] | None:
        result: dict[str, tuple[str, str] | None] = {"value": None}
        dialog = self._modal("Create preset", 440, 240)
        ctk.CTkLabel(dialog, text="Name").pack(anchor="w", padx=16, pady=(16, 6))
        entry = ctk.CTkEntry(dialog, width=400)
        entry.pack(padx=16)
        ctk.CTkLabel(dialog, text="Timing").pack(anchor="w", padx=16, pady=(12, 6))
        mode_var = ctk.StringVar(value="Instantaneous")
        ctk.CTkSegmentedButton(
            dialog,
            values=["Instantaneous", "One second", "Realtime"],
            variable=mode_var,
        ).pack(padx=16, anchor="w")

        def ok(_event=None) -> None:
            name = entry.get().strip()
            if not name:
                return
            result["value"] = (name, MODE_FROM_LABEL[mode_var.get()])
            dialog.destroy()

        def cancel(_event=None) -> None:
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Cancel", width=100, command=cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Start recording", width=140, command=ok).pack(side="right")
        entry.bind("<Return>", ok)
        dialog.bind("<Escape>", cancel)
        entry.focus()
        self.wait_window(dialog)
        return result["value"]

    def _confirm(self, title: str, text: str) -> bool:
        result = {"ok": False}
        dialog = self._modal(title, 380, 150)
        ctk.CTkLabel(dialog, text=text, wraplength=340, justify="left").pack(anchor="w", padx=16, pady=(18, 8))

        def yes() -> None:
            result["ok"] = True
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(buttons, text="Cancel", width=90, command=dialog.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Delete", width=90, command=yes).pack(side="right")
        self.wait_window(dialog)
        return result["ok"]

    def _create_preset(self) -> None:
        if self._busy():
            return
        if self.anchor_target.snapshot()[0] != "ok":
            self._status("Anchor a window before recording.", "error")
            return
        chosen = self._ask_new_preset()
        if chosen is None:
            return
        name, mode = chosen
        self.recorder.start(name, mode)
        self.hooks.state.recording = True
        self._rebuild_points()
        self._sync_controls()
        self._status("Recording. Put the cursor on a spot and press Space. Esc saves.", "warn")

    def _record_rect(self):
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            return None
        return rect

    def _finish_recording(self) -> None:
        self.hooks.state.recording = False
        points = self.recorder.finish()
        self._sync_controls()
        if not points:
            self._rebuild_points()
            self._status("Recording cancelled. No points were added.", "info")
            return
        preset = Preset(name=self.recorder.name, timing_mode=self.recorder.mode, points=points, loop=True, loop_count=None)
        self.store.save(preset)
        saved_path = preset.path
        self.store.load_all()
        self._select_path(saved_path)
        self._status(f"Saved {preset.name} with {len(points)} points.", "ok")

    def _rename_preset(self) -> None:
        if self.current is None or self._busy():
            return
        name = self._ask_name("Rename preset", self.current.name)
        if not name:
            return
        self.current.name = name
        self.store.save(self.current)
        saved = self.current.path
        self.store.load_all()
        self._select_path(saved)
        self._status(f"Renamed to {name}.", "ok")

    def _duplicate_preset(self) -> None:
        if self.current is None or self._busy():
            return
        copy = Preset(
            name=f"{self.current.name} copy",
            timing_mode=self.current.timing_mode,
            points=[
                ClickPoint(point.nx, point.ny, point.delay_ms, point.hold_ms, point.button, point.label)
                for point in self.current.points
            ],
            loop=self.current.loop,
            loop_count=self.current.loop_count,
            notes=self.current.notes,
        )
        self.store.save(copy)
        saved = copy.path
        self.store.load_all()
        self._select_path(saved)
        self._status(f"Duplicated as {copy.name}.", "ok")

    def _delete_preset(self) -> None:
        if self.current is None or self._busy():
            return
        if not self._confirm("Delete preset", f"Delete {self.current.name}?"):
            return
        name = self.current.name
        self.store.delete(self.current)
        self.current = None
        self.store.load_all()
        if self.store.presets:
            self._select(self.store.presets[0])
        else:
            self._rebuild_preset_list()
            self.notes_label.configure(text="")
            self._rebuild_points()
            self._sync_controls()
        self._status(f"Deleted {name}.", "info")

    def _reload_presets(self) -> None:
        if self.recorder.active:
            self._status("Finish recording before reloading.", "error")
            return
        path = self.current.path if self.current is not None else None
        errors = self.store.load_all()
        self._select_path(path)
        if errors:
            self._status("Skipped preset files: " + "; ".join(errors), "error")
        else:
            self._status(f"Loaded {len(self.store.presets)} presets.", "ok")

    def _import_preset(self) -> None:
        if self.recorder.active:
            return
        chosen = filedialog.askopenfilename(
            title="Import preset",
            filetypes=[("JSON presets", "*.json"), ("All files", "*.*")],
        )
        if not chosen:
            return
        try:
            preset = load_preset(Path(chosen))
        except PresetError as exc:
            self._status(str(exc), "error")
            return
        preset.path = None
        self.store.save(preset)
        saved = preset.path
        self.store.load_all()
        self._select_path(saved)
        self._status(f"Imported {preset.name}.", "ok")

    def _export_preset(self) -> None:
        if self.current is None or self._busy():
            return
        chosen = filedialog.asksaveasfilename(
            title="Export preset",
            defaultextension=".json",
            initialfile=f"{slug(self.current.name)}.json",
            filetypes=[("JSON presets", "*.json")],
        )
        if not chosen:
            return
        Path(chosen).write_text(json.dumps(preset_to_dict(self.current), indent=2) + "\n", encoding="utf-8")
        self._status(f"Exported {self.current.name}.", "ok")

    def _start_playback(self) -> None:
        if self.recorder.active or self.player.is_active:
            return
        if self.current is None or not self.current.points:
            self._status("Select a preset with at least one point.", "error")
            return
        for index in range(len(self.current.points)):
            self._commit_row(index)
        status, hwnd, _rect, _title = self.anchor_target.snapshot()
        if status == "minimized":
            self._status("The anchored window is minimized.", "error")
            return
        if status != "ok":
            self._status("Anchor a window before playback.", "error")
            return
        self.hooks.state.playback = True
        self._sync_controls()
        self.player.start(
            self.current.points,
            loop=self.current.loop,
            loop_count=self.current.loop_count,
            method=self.settings.click_method,
            focus=self.settings.focus_before_run,
            restore_cursor=self.settings.restore_cursor,
            countdown=self.settings.countdown_seconds,
            hwnd=hwnd,
            snapshot=self.anchor_target.snapshot,
        )

    def _stop_playback(self) -> None:
        if self.player.is_active:
            self.player.stop()
            self._status("Stopping.", "warn")

    def _toggle_pause(self) -> None:
        if self.player.is_active:
            self.player.toggle_pause()

    def _open_logger(self) -> None:
        if self._logger is None or not self._logger.win.winfo_exists():
            self._logger = ClickLogger(self)
        self._logger.lift_window()

    def _drain_hooks(self) -> None:
        try:
            for event in self.hooks.drain():
                kind = event[0]
                if kind == "anchor_click":
                    self._apply_anchor(int(event[3]))
                elif kind == "space_down" and self.recorder.active:
                    self.recorder.space_down(int(event[1]), int(event[2]))
                elif kind == "space_up" and self.recorder.active:
                    point = self.recorder.space_up(self._record_rect)
                    if self.recorder.last_error:
                        self._status(self.recorder.last_error, "error")
                    if point is not None:
                        self._rebuild_points()
                        self._status(f"Point {len(self.recorder.points)} added.", "warn")
                elif kind == "escape":
                    if self._anchor_waiting or self.hooks.state.anchor_armed:
                        self._cancel_anchor_mode()
                    elif self.recorder.active:
                        self._finish_recording()
                    elif self.player.is_active:
                        self._stop_playback()
                elif kind == "f6":
                    if self.player.is_active:
                        self._stop_playback()
                    elif not self.recorder.active:
                        self._start_playback()
                elif kind == "f7" and self.player.is_active:
                    self._toggle_pause()
        except Exception as exc:
            self._status(f"Hotkey handler failed: {exc}", "error")
        if self._alive:
            self.after(30, self._drain_hooks)

    def _drain_player(self) -> None:
        try:
            while True:
                try:
                    event = self.player.events.get_nowait()
                except Exception:
                    break
                kind = event[0]
                if kind == "status":
                    self._status(event[1], event[2])
                elif kind == "point":
                    index, loop_index, total = event[1], event[2], event[3]
                    self._active_index = index
                    self._highlight_row(index)
                    self._status(f"Loop {loop_index}, point {index + 1} of {total}.", "run")
                elif kind == "paused":
                    self.pause_button.configure(text="Resume" if event[1] else "Pause")
                    if event[1]:
                        self._status("Paused.", "warn")
                    else:
                        self._status("Resumed.", "run")
                elif kind == "stopped":
                    self.hooks.state.playback = False
                    self._active_index = None
                    self.pause_button.configure(text="Pause")
                    self._highlight_row(None)
                    self._sync_controls()
                    level = "ok" if event[1] == "Finished." else "warn"
                    self._status(event[1], level)
        except Exception as exc:
            self._status(f"Playback update failed: {exc}", "error")
        if self._alive:
            self.after(50, self._drain_player)

    def _on_close(self) -> None:
        self._alive = False
        self.hooks.state.anchor_armed = False
        self.hooks.state.recording = False
        self.hooks.state.playback = False
        try:
            self.auto_runtime.stop()
        except Exception:
            pass
        self.player.stop_and_wait()
        self.hooks.stop()
        try:
            self.overlay.destroy()
        except Exception:
            pass
        self.destroy()


    def _automation_anchor_rect(self):
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            return None
        return rect

    def _automation_play_preset(self, name: str) -> None:
        preset = next((item for item in self.store.presets if item.name == name), None)
        if preset is None:
            raise RuntimeError(f"preset not found: {name}")
        status, hwnd, rect, _title = self.anchor_target.snapshot()
        if status != "ok" or rect is None or not hwnd:
            raise RuntimeError("anchor missing for play_preset")
        play_points_sync(
            preset.points,
            rect,
            method=self.settings.click_method,
            hwnd=hwnd,
            focus=self.settings.focus_before_run,
            restore_cursor=self.settings.restore_cursor,
        )

    def _reload_automations(self) -> None:
        errors = self.auto_store.load_all()
        if self.auto_panel is not None:
            self.auto_panel.refresh_list()
            for message in errors:
                self.auto_panel.append_console(f"load error: {message}", "error")
            if not errors:
                self.auto_panel.append_console("Automations reloaded.", "ok")
        self.auto_runtime.reload_schedule()
        if errors:
            self._status("Skipped automation files: " + "; ".join(errors), "error")
        else:
            self._status("Automations reloaded.", "ok")

    def _start_automations(self) -> None:
        self.auto_runtime.start()
        self._status("Automations started.", "run")

    def _stop_automations(self) -> None:
        self.auto_runtime.stop()
        self._status("Automations stopped.", "warn")

    def _drain_automations(self) -> None:
        try:
            while True:
                try:
                    event = self.auto_runtime.events_out.get_nowait()
                except Exception:
                    break
                kind = event.get("kind")
                if kind == "console" and self.auto_panel is not None:
                    self.auto_panel.append_console(event.get("message", ""), event.get("level", "info"))
                elif kind == "queue" and self.auto_panel is not None:
                    self.auto_panel.set_queue(event.get("items") or [])
        except Exception as exc:
            self._status(f"Automations update failed: {exc}", "error")
        if self._alive:
            self.after(80, self._drain_automations)



def main() -> None:
    win32_api.set_dpi_aware()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
