"""Control panel for anchoring a window and playing presets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from idle_lab.anchor import Anchor
from idle_lab.automations.guide_overlay import GuideOverlay
from idle_lab.automations.mouse_sync import play_points_sync
from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.ai_batch.schema import AiBatch, BatchRequest, RequestResult, now_iso
from idle_lab.ai_batch.store import AiBatchError, AiBatchStore
from idle_lab.ai_batch.runner import AiBatchRunner, AiBatchRunnerError
from idle_lab.ai_batch.ui import AiBatchPanel
from idle_lab.automations.ui import AutomationsPanel
from idle_lab.automations.walkthrough import Walkthrough
from idle_lab.automations.schema import Collection
from idle_lab.click_logger import ClickLogger
from idle_lab.hotkeys import InputHooks
from idle_lab.humanize import HUMANIZE_LEVELS, HumanizeProfile, normalize_level
from idle_lab.image_viewer import open_image_viewer
from idle_lab.models import ClickPoint, Preset, normalized_to_screen, screen_to_normalized
from idle_lab.overlay import Overlay
from idle_lab.player import Player
from idle_lab.presets import PresetError, PresetStore, load_preset, preset_to_dict, project_root, slug
from idle_lab.recorder import Recorder
from idle_lab.screen_map.batch import ScreenMapController, ScreenMapError, add_shot, create_batch
from idle_lab.screen_map.catalog import BatchSummary, list_batches as list_screen_map_batches
from idle_lab.screen_map.ui import ScreenMapPanel
from idle_lab.scroll_memory import ScrollMemory
from idle_lab.settings_store import load_settings, save_settings
from idle_lab import win32_api

_HUMANIZE_LABELS = {
    "off": "Off",
    "light": "Light",
    "medium": "Medium",
    "heavy": "Heavy",
}
_HUMANIZE_FROM_LABEL = {label: key for key, label in _HUMANIZE_LABELS.items()}

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
            get_anchor_hwnd=self._automation_anchor_hwnd,
            get_humanize=self._humanize_profile,
            restore_cursor=bool(self.settings.restore_cursor),
            play_preset=self._automation_play_preset,
        )
        self.auto_panel: AutomationsPanel | None = None
        self.screen_map_panel: ScreenMapPanel | None = None
        self.ai_batch_panel: AiBatchPanel | None = None
        self.screen_map = ScreenMapController()
        self.screen_maps_root = root / "screen-maps"
        self.ai_batches_root = root / "ai-batches"
        self.ai_batch_store = AiBatchStore(self.ai_batches_root)
        ai_errors = self.ai_batch_store.load_all()
        self.ai_batch_runner = AiBatchRunner(
            store=self.ai_batch_store,
            screen_maps_root=self.screen_maps_root,
            get_anchor=self._ai_batch_anchor_snapshot,
            play_preset=self._automation_play_preset,
            restore_cursor=bool(self.settings.restore_cursor),
            get_humanize=self._humanize_profile,
        )
        self.scroll_memory = ScrollMemory()
        self._current_tab = "Clicker"
        self.walkthrough: Walkthrough | None = None
        self.guide_overlay: GuideOverlay | None = None
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
        self._screen_map_title_dialog = None
        self._screen_map_busy = False
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
        self._refresh_screen_map_catalog()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.hooks.start()
        except OSError as exc:
            self._status(f"Hotkeys unavailable: {exc}", "error")
        self.after(120, self._poll_anchor)
        self.after(30, self._drain_hooks)
        self.after(50, self._drain_player)
        self.after(80, self._drain_automations)
        self.after(100, self._drain_ai_batch_runner)
        if settings_error:
            self._status(settings_error, "warn")
        elif errors:
            self._status("Skipped preset files: " + "; ".join(errors), "error")
        elif auto_errors:
            self._status("Skipped automation files: " + "; ".join(auto_errors), "error")
        elif ai_errors:
            self._status("Skipped AI batch files: " + "; ".join(ai_errors), "error")
        else:
            self._status("Set anchor, then click the emulator window.", "info")

    def _build(self) -> None:
        self.status_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=980)
        self.status_label.pack(side="bottom", fill="x", padx=12, pady=(4, 10))

        self._build_chrome()

        self.tabs = ctk.CTkTabview(self, command=self._on_tab_changed)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=(4, 0))
        clicker = self.tabs.add("Clicker")
        automations = self.tabs.add("Automations")
        screen_map = self.tabs.add("Screen Map")
        ai_batches = self.tabs.add("AI Batches")

        self.body = ctk.CTkScrollableFrame(clicker, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=4, pady=(4, 0))
        self.scroll_memory.register("clicker.body", self.body)
        self._build_clicker_body()
        self.scroll_memory.register("clicker.presets", self.preset_list)

        self.auto_panel = AutomationsPanel(
            automations,
            store=self.auto_store,
            on_reload=self._reload_automations,
            on_start=self._start_automations,
            on_stop=self._stop_automations,
            on_walkthrough=self._start_collection_walkthrough,
            on_walkthrough_stop=self._stop_collection_walkthrough,
            scroll=self.scroll_memory,
        )
        self.auto_panel.pack(fill="both", expand=True)

        self.screen_map_panel = ScreenMapPanel(
            screen_map,
            on_start_batch=self._start_screen_map_batch,
            on_end_batch=self._end_screen_map_batch,
            on_open_folder=self._open_screen_map_folder,
            on_refresh_catalog=self._refresh_screen_map_catalog,
            on_view_shot=self._view_screen_map_shot,
            on_view_batch=self._view_screen_map_batch,
            scroll=self.scroll_memory,
        )
        self.screen_map_panel.pack(fill="both", expand=True)

        self.ai_batch_panel = AiBatchPanel(
            ai_batches,
            store=self.ai_batch_store,
            scroll=self.scroll_memory,
            screen_maps_root=self.screen_maps_root,
            on_reload=self._reload_ai_batches,
            on_new_batch=self._new_ai_batch,
            on_open_folder=self._open_ai_batch_folder,
            on_view_screenshots=self._view_ai_batch_screenshots,
            on_link_screen_map=self._link_ai_batch_screen_map,
            on_mark_request=self._mark_ai_request,
            on_add_feedback=self._add_ai_feedback,
            on_open_screen_map_batch=self._goto_screen_map_batch,
            on_snapshot_event=self._snapshot_event_into_ai_batch,
            on_start_run=self._start_ai_batch_run,
            on_stop_run=self._stop_ai_batch_run,
        )
        self.ai_batch_panel.pack(fill="both", expand=True)
        self._current_tab = self.tabs.get()

    def _build_chrome(self) -> None:
        """Global top bar: brand, shared anchor, reserved action tray (Settings later)."""

        chrome = ctk.CTkFrame(self, corner_radius=12)
        chrome.pack(fill="x", padx=8, pady=(8, 4))

        left = ctk.CTkFrame(chrome, fg_color="transparent")
        left.pack(side="left", fill="y", padx=(14, 10), pady=10)
        ctk.CTkLabel(
            left,
            text="Errriiiccc's Idle Lab",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Shared window anchor for every tab",
            text_color="#9AA4B2",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        # Right-side action tray first so anchor can expand into remaining space.
        self.header_actions = ctk.CTkFrame(chrome, fg_color="transparent")
        self.header_actions.pack(side="right", padx=(8, 12), pady=10)
        self.settings_button = ctk.CTkButton(
            self.header_actions,
            text="Settings",
            width=96,
            state="disabled",
            fg_color="#2A3140",
            text_color="#7E8796",
            hover=False,
        )
        self.settings_button.pack(side="right")

        anchor_cluster = ctk.CTkFrame(chrome, fg_color="#1A2030", corner_radius=10)
        anchor_cluster.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

        anchor_top = ctk.CTkFrame(anchor_cluster, fg_color="transparent")
        anchor_top.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            anchor_top,
            text="ANCHOR",
            text_color="#8EE0C2",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left")
        self.anchor_dot = ctk.CTkLabel(anchor_top, text="●", text_color="#5A6474", width=18)
        self.anchor_dot.pack(side="left", padx=(8, 0))

        self.anchor_label = ctk.CTkLabel(
            anchor_cluster,
            text="No window anchored",
            anchor="w",
            justify="left",
            text_color="#C5D0DC",
        )
        self.anchor_label.pack(fill="x", padx=10, pady=(0, 4))

        anchor_buttons = ctk.CTkFrame(anchor_cluster, fg_color="transparent")
        anchor_buttons.pack(fill="x", padx=10, pady=(0, 8))
        self.anchor_button = ctk.CTkButton(
            anchor_buttons,
            text="Set anchor",
            width=118,
            command=self._toggle_anchor_mode,
        )
        self.anchor_button.pack(side="left", padx=(0, 6))
        self.clear_button = ctk.CTkButton(
            anchor_buttons,
            text="Clear",
            width=78,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._clear_anchor,
        )
        self.clear_button.pack(side="left")

    def _build_clicker_body(self) -> None:
        header = ctk.CTkFrame(self.body, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(header, text="Clicker", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Presets are fractions of the anchored window, so they follow moves and resizes.",
            text_color="#9AA4B2",
            wraplength=520,
            justify="left",
        ).pack(anchor="w")

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
        ctk.CTkLabel(options, text="Humanize").pack(side="left", padx=(8, 4))
        self.humanize_menu = ctk.CTkOptionMenu(
            options,
            values=[_HUMANIZE_LABELS[level] for level in HUMANIZE_LEVELS],
            command=self._on_humanize,
            width=100,
        )
        self.humanize_menu.set(_HUMANIZE_LABELS.get(normalize_level(self.settings.humanize_level), "Medium"))
        self.humanize_menu.pack(side="left", padx=(0, 8))
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
        waiting = self._anchor_waiting
        self.anchor_button.configure(text="Cancel anchor" if waiting else "Set anchor")
        self.anchor_button.configure(state="disabled" if busy else "normal")
        if waiting:
            self.anchor_button.configure(fg_color="#C9A227", hover_color="#E0B93A", text_color="#161616")
        else:
            self.anchor_button.configure(fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"], text_color="#DCE4EE")
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

    def _humanize_profile(self) -> HumanizeProfile:
        return HumanizeProfile.from_level(self.settings.humanize_level)

    def _on_method(self, value: str) -> None:
        if self._loading():
            return
        self.settings.click_method = "background" if value == "Background" else "foreground"
        self._save_settings()

    def _on_humanize(self, value: str) -> None:
        if self._loading():
            return
        self.settings.humanize_level = _HUMANIZE_FROM_LABEL.get(value, normalize_level(value))
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
            if self.guide_overlay is not None and self.walkthrough is not None and self.walkthrough.active:
                self.guide_overlay.set_anchor(rect if status == "ok" else None)
        except Exception as exc:
            self._status(f"Anchor poll failed: {exc}", "error")
        if self._alive:
            self.after(100, self._poll_anchor)

    def _render_anchor(self, status: str, rect, title: str) -> None:
        if status == "ok" and rect is not None:
            text = f"{title}   {rect.width} x {rect.height}"
            dot = "#8EE0C2"
        elif status == "minimized":
            text = f"{title} is minimized"
            dot = "#E7C36A"
        elif status == "closed":
            text = "Anchored window closed"
            dot = "#F09595"
        else:
            text = "No window anchored"
            dot = "#5A6474"
        self.anchor_label.configure(text=text)
        self.anchor_dot.configure(text_color=dot)

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
        def rebuild() -> None:
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

        self.scroll_memory.around_rebuild("clicker.presets", rebuild)

    def _on_tab_changed(self) -> None:
        previous = self._current_tab
        self.scroll_memory.remember_prefix(self._tab_scroll_prefix(previous))
        self._current_tab = self.tabs.get()
        prefix = self._tab_scroll_prefix(self._current_tab)
        self.after(80, lambda p=prefix: self.scroll_memory.restore_prefix(p))

    def _tab_scroll_prefix(self, tab_name: str) -> str:
        return {
            "Clicker": "clicker.",
            "Automations": "automations.",
            "Screen Map": "screen_map.",
            "AI Batches": "ai.",
        }.get(tab_name, tab_name.lower().replace(" ", "_") + ".")

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

    def _modal(self, title: str, width: int, height: int, *, keep_topmost: bool = False) -> ctk.CTkToplevel:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.attributes("-topmost", True)
        if not keep_topmost:
            dialog.after(250, lambda: dialog.attributes("-topmost", False) if dialog.winfo_exists() else None)
        return dialog

    def _arm_dialog_focus(self, dialog: ctk.CTkToplevel, entry: ctk.CTkEntry) -> None:
        """Steal focus from BlueStacks / other apps into the dialog entry."""

        def focus_once() -> None:
            if not dialog.winfo_exists():
                return
            try:
                dialog.lift()
                dialog.attributes("-topmost", True)
                dialog.focus_force()
                hwnd = win32_api.widget_hwnd(dialog)
                win32_api.focus_window(hwnd)
                entry.focus_force()
                entry.icursor("end")
            except Exception:
                try:
                    entry.focus_force()
                except Exception:
                    pass

        dialog.after(1, focus_once)
        dialog.after(50, focus_once)
        dialog.after(150, focus_once)
        dialog.after(300, focus_once)

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
        self._arm_dialog_focus(dialog, entry)
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
            humanize=self._humanize_profile(),
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
                elif kind == "screen_map_space":
                    self._screen_map_space()
                elif kind == "walkthrough_space":
                    self._walkthrough_space()
                elif kind == "walkthrough_key":
                    self._walkthrough_key(str(event[1]))
                elif kind == "escape":
                    if self._anchor_waiting or self.hooks.state.anchor_armed:
                        self._cancel_anchor_mode()
                    elif self.walkthrough is not None and self.walkthrough.active:
                        self._stop_collection_walkthrough()
                    elif self.recorder.active:
                        self._finish_recording()
                    elif self.player.is_active:
                        self._stop_playback()
                    elif self.screen_map.active and not self._screen_map_busy:
                        self._end_screen_map_batch()
                elif kind == "f6":
                    if self.walkthrough is not None and self.walkthrough.active:
                        pass
                    elif self.player.is_active:
                        self._stop_playback()
                    elif not self.recorder.active and not self.screen_map.active:
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
        self.hooks.state.screenshot_mode = False
        self.hooks.state.title_dialog_open = False
        self.hooks.state.screenshot_busy = False
        self.hooks.state.walkthrough_active = False
        try:
            self._stop_collection_walkthrough()
        except Exception:
            pass
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
        try:
            if self.guide_overlay is not None:
                self.guide_overlay.destroy()
        except Exception:
            pass
        self.destroy()

    def _start_collection_walkthrough(self, collection: Collection) -> None:
        if self.recorder.active or self.player.is_active or self.screen_map.active:
            self._status("Stop recording/playback/screen-map before Walkthrough.", "warn")
            return
        if self.guide_overlay is None:
            self.guide_overlay = GuideOverlay(self)
        self.walkthrough = Walkthrough(self.auto_store, collection)
        step = self.walkthrough.start()
        self.hooks.state.walkthrough_active = True
        if self.auto_panel is not None:
            self.auto_panel.set_walkthrough_active(True)
            self.auto_panel.append_console(
                f"Walkthrough started: {collection.title}. Space = next, A/B/C = branches, Esc = exit.",
                "ok",
            )
        self._show_walkthrough_step(step)
        self._status(f"Walkthrough: {collection.title}", "run")

    def _stop_collection_walkthrough(self) -> None:
        self.hooks.state.walkthrough_active = False
        if self.walkthrough is not None:
            self.walkthrough.stop()
        self.walkthrough = None
        if self.guide_overlay is not None:
            self.guide_overlay.hide()
        if self.auto_panel is not None:
            self.auto_panel.set_walkthrough_active(False)
            self.auto_panel.append_console("Walkthrough ended.", "warn")
        self._status("Walkthrough ended.", "info")

    def _show_walkthrough_step(self, step) -> None:
        if self.walkthrough is None or self.guide_overlay is None or step is None:
            return
        card = self.walkthrough.to_card()
        if card is None:
            return
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        anchor = rect if status == "ok" else None
        self.guide_overlay.show(card, anchor)
        if self.auto_panel is not None:
            self.auto_panel.append_console(f"Tour: {step.title}", "info")

    def _walkthrough_space(self) -> None:
        if self.walkthrough is None or not self.walkthrough.active:
            return
        step = self.walkthrough.advance_space()
        if step is None:
            self._stop_collection_walkthrough()
            return
        self._show_walkthrough_step(step)
        if step.kind == "done":
            self._status("Walkthrough complete — Space or Esc to close.", "ok")

    def _walkthrough_key(self, letter: str) -> None:
        if self.walkthrough is None or not self.walkthrough.active:
            return
        step = self.walkthrough.choose(letter)
        if step is None:
            return
        self._show_walkthrough_step(step)

    def _refresh_screen_map_panel(self) -> None:
        if self.screen_map_panel is None:
            return
        session = self.screen_map.session
        if session is None:
            self.screen_map_panel.set_idle()
        else:
            self.screen_map_panel.set_active(
                session.folder,
                session.titles,
                ready=not self._screen_map_busy,
            )

    def _set_screen_map_busy(self, busy: bool, message: str | None = None) -> None:
        self._screen_map_busy = busy
        self.hooks.state.screenshot_busy = busy
        if self.screen_map_panel is not None:
            self.screen_map_panel.set_busy(message if busy else None)
            session = self.screen_map.session
            if session is not None:
                self.screen_map_panel.set_active(session.folder, session.titles, ready=not busy)
        self.update_idletasks()
        try:
            self.update()
        except Exception:
            pass

    def _start_screen_map_batch(self) -> None:
        if self.screen_map.active:
            self._status("A Screen Map batch is already running.", "warn")
            return
        if self.recorder.active or self.player.is_active:
            self._status("Finish recording/playback before starting a Screen Map batch.", "warn")
            return
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            self._status("Anchor a window before starting a Screen Map batch.", "error")
            return
        title = self._ask_name("Screen Map batch", "tower-screens")
        if not title:
            return
        try:
            self.screen_maps_root.mkdir(parents=True, exist_ok=True)
            session = create_batch(self.screen_maps_root, title)
            self.screen_map.start(session)
        except ScreenMapError as exc:
            self._status(str(exc), "error")
            return
        except OSError as exc:
            self._status(f"Could not create batch folder: {exc}", "error")
            return
        self.hooks.state.screenshot_mode = True
        self.hooks.state.title_dialog_open = False
        self.hooks.state.screenshot_busy = False
        self._screen_map_busy = False
        self._refresh_screen_map_panel()
        self._refresh_screen_map_catalog()
        self._status(f"Screenshot mode ON. Space captures, then title. Batch: {session.folder}", "run")

    def _end_screen_map_batch(self) -> None:
        if self._screen_map_title_dialog is not None:
            try:
                if self._screen_map_title_dialog.winfo_exists():
                    self._screen_map_title_dialog.destroy()
            except Exception:
                pass
            self._screen_map_title_dialog = None
        self.hooks.state.title_dialog_open = False
        self._set_screen_map_busy(False)
        session = self.screen_map.end()
        self.hooks.state.screenshot_mode = False
        self._refresh_screen_map_panel()
        self._refresh_screen_map_catalog()
        if session is None:
            self._status("Screenshot mode OFF.", "warn")
            return
        self._status(
            f"Batch finished: {session.shot_count} shot(s) in {session.folder}",
            "ok",
        )

    def _open_screen_map_folder(self) -> None:
        session = self.screen_map.session
        if session is not None:
            folder = session.folder
        elif self.screen_map_panel is not None and self.screen_map_panel.selected_batch is not None:
            folder = self.screen_map_panel.selected_batch.folder
        else:
            folder = self.screen_maps_root
        if not folder.exists():
            self._status("No batch folder to open yet.", "warn")
            return
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except OSError as exc:
            self._status(f"Could not open folder: {exc}", "error")

    def _refresh_screen_map_catalog(self) -> None:
        if self.screen_map_panel is None:
            return
        batches = list_screen_map_batches(self.screen_maps_root)
        focus = None
        if self.screen_map.session is not None:
            focus = self.screen_map.session.folder.name
        self.screen_map_panel.set_catalog(batches, focus_slug=focus)

    def _view_screen_map_shot(self, batch: BatchSummary, index: int) -> None:
        paths = [batch.shot_path(shot) for shot in batch.manifest.shots]
        titles = [shot.title for shot in batch.manifest.shots]
        viewer = open_image_viewer(
            self,
            paths,
            titles=titles,
            start_index=index,
            title=f"Screen Map — {batch.title}",
        )
        if viewer is None:
            self._status("No screenshot files found for that shot.", "warn")

    def _view_screen_map_batch(self, batch: BatchSummary) -> None:
        self._view_screen_map_shot(batch, 0)

    def _goto_screen_map_batch(self, slug: str) -> None:
        self._refresh_screen_map_catalog()
        if self.screen_map_panel is not None:
            self.screen_map_panel.focus_batch(slug)
        self.tabs.set("Screen Map")
        self._on_tab_changed()
        self._status(f"Opened Screen Map batch: {slug}", "info")

    def _screen_map_space(self) -> None:
        if not self.screen_map.active or self.screen_map.dialog_open or self._screen_map_busy:
            return
        if self.recorder.active or self.player.is_active:
            self._status("Cannot capture while recording or playing back.", "warn")
            return

        # Capture first so the PNG matches the frame when Space was pressed.
        self._set_screen_map_busy(True, "Capturing…")
        status, _hwnd, rect, window_title = self.anchor_target.snapshot()
        if status == "missing":
            self._set_screen_map_busy(False)
            self._status("No window anchored — capture refused.", "error")
            return
        if status == "closed":
            self._set_screen_map_busy(False)
            self._status("Anchored window is gone — capture refused.", "error")
            return
        if status == "minimized":
            self._set_screen_map_busy(False)
            self._status("Anchored window is minimized — capture refused.", "error")
            return
        if status != "ok" or rect is None:
            self._set_screen_map_busy(False)
            self._status(f"Anchor not ready ({status}) — capture refused.", "error")
            return
        try:
            image = grab_anchor(rect)
        except CaptureError as exc:
            self._set_screen_map_busy(False)
            self._status(f"Capture failed: {exc}", "error")
            return

        anchor_meta = {
            "window_title": window_title,
            "width": rect.width,
            "height": rect.height,
            "left": rect.left,
            "top": rect.top,
        }

        try:
            self.screen_map.begin_title_dialog()
        except ScreenMapError as exc:
            self._set_screen_map_busy(False)
            self._status(str(exc), "error")
            return

        # Title dialog needs keyboard input — clear busy so Space types normally.
        self._set_screen_map_busy(False)
        self.hooks.state.title_dialog_open = True
        title = self._ask_screen_map_title()
        self.hooks.state.title_dialog_open = False
        if not self.screen_map.active:
            return
        if title is None:
            self.screen_map.cancel_title_dialog()
            self._status("Shot cancelled (bitmap discarded).", "warn")
            self._refresh_screen_map_panel()
            return
        try:
            self.screen_map.finish_title_dialog()
        except ScreenMapError:
            self.screen_map.cancel_title_dialog()
            self._refresh_screen_map_panel()
            return

        session = self.screen_map.session
        if session is None:
            self._status("Batch session missing.", "error")
            return

        self._set_screen_map_busy(True, "Saving…")
        try:
            shot = add_shot(session, title=title, image=image, anchor=anchor_meta)
        except ScreenMapError as exc:
            self._set_screen_map_busy(False)
            self._status(str(exc), "error")
            return
        except OSError as exc:
            self._set_screen_map_busy(False)
            self._status(f"Could not save shot: {exc}", "error")
            return
        self._set_screen_map_busy(False)
        self._refresh_screen_map_panel()
        self._refresh_screen_map_catalog()
        self._status(f"Saved {shot.filename} — ready for Space.", "ok")

    def _ai_batch_anchor_snapshot(self):
        return self.anchor_target.snapshot()

    def _start_ai_batch_run(self, batch: AiBatch) -> None:
        if self.recorder.active or self.player.is_active or self.screen_map.active:
            self._status("Stop recording/playback/Screen Map before running an AI batch.", "warn")
            return
        if self.ai_batch_runner.is_running:
            self._status("An AI batch is already running.", "warn")
            return
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            self._status("Anchor a window before starting an AI batch run.", "error")
            return
        # Re-load so steps from disk are current.
        self.ai_batch_store.load_all()
        live = self.ai_batch_store.batches.get(batch.slug)
        if live is None:
            self._status("Batch missing on disk — Reload.", "error")
            return
        try:
            self.ai_batch_runner.start(live)
        except AiBatchRunnerError as exc:
            self._status(str(exc), "error")
            if self.ai_batch_panel is not None:
                self.ai_batch_panel.set_run_message(str(exc), level="error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.set_running(True, f"Runner: starting {live.name}…")
        self._status(f"AI batch running: {live.name}", "run")

    def _stop_ai_batch_run(self) -> None:
        self.ai_batch_runner.stop()
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.set_run_message("Runner: stop requested…", level="warn")
        self._status("Stopping AI batch…", "warn")

    def _drain_ai_batch_runner(self) -> None:
        try:
            while True:
                try:
                    event = self.ai_batch_runner.events_out.get_nowait()
                except Exception:
                    break
                kind = event.get("kind")
                if kind == "status":
                    message = event.get("message") or ""
                    level = event.get("level") or "info"
                    self._status(message, level if level in STATUS_COLOR else "info")
                    if self.ai_batch_panel is not None:
                        self.ai_batch_panel.set_run_message(message, level=level)
                elif kind == "refresh":
                    self.ai_batch_store.load_all()
                    if self.ai_batch_panel is not None:
                        self.ai_batch_panel.refresh_list()
                    self._refresh_screen_map_catalog()
                elif kind == "finished":
                    if self.ai_batch_panel is not None:
                        self.ai_batch_panel.set_running(False, "Runner: idle — tell the AI chat this batch ran.")
                    self._refresh_screen_map_catalog()
                    report = event.get("report") or {}
                    sm = report.get("screen_map_batch")
                    if sm:
                        self._status(f"AI batch finished. Screen Map: screen-maps/{sm}/ (+ run_report.json)", "ok")
        except Exception as exc:
            self._status(f"AI batch runner update failed: {exc}", "error")
        if self._alive:
            self.after(100, self._drain_ai_batch_runner)

    def _reload_ai_batches(self) -> None:
        errors = self.ai_batch_store.load_all()
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        if errors:
            self._status("Skipped AI batch files: " + "; ".join(errors), "error")
        else:
            self._status(f"AI batches reloaded ({len(self.ai_batch_store.batches)}).", "ok")

    def _new_ai_batch(self) -> None:
        name = self._ask_name("New AI information batch", "info-pass")
        if not name:
            return
        goal = self._ask_text("Batch goal (optional)", "What should this batch gather?") or ""
        try:
            batch = self.ai_batch_store.create(
                name,
                goal=goal,
                created_by="human",
                requests=[
                    {
                        "id": "req-1",
                        "kind": "screen_map_batch",
                        "label": "Link a Screen Map batch",
                        "detail": "Capture or attach screenshots via Screen Map, then link them here.",
                    },
                    {
                        "id": "req-2",
                        "kind": "note",
                        "label": "Notes / gaps",
                        "detail": "Record anything the AI still needs after this pass.",
                    },
                ],
            )
        except AiBatchError as exc:
            self._status(str(exc), "error")
            return
        except OSError as exc:
            self._status(f"Could not create AI batch: {exc}", "error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        self._status(f"Created AI batch: {batch.slug}", "ok")

    def _ask_text(self, title: str, prompt: str) -> str | None:
        result: dict[str, str | None] = {"value": None}
        dialog = self._modal(title, 420, 200)
        ctk.CTkLabel(dialog, text=prompt, wraplength=380, justify="left").pack(anchor="w", padx=16, pady=(16, 6))
        entry = ctk.CTkEntry(dialog, width=380)
        entry.pack(padx=16)

        def ok(_event=None) -> None:
            result["value"] = entry.get().strip()
            dialog.destroy()

        def cancel(_event=None) -> None:
            result["value"] = None
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Skip", width=90, command=cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="OK", width=90, command=ok).pack(side="right")
        entry.bind("<Return>", ok)
        dialog.bind("<Escape>", cancel)
        dialog.after(1, lambda: self._arm_dialog_focus(dialog, entry))
        self.wait_window(dialog)
        return result["value"]

    def _open_ai_batch_folder(self, batch: AiBatch) -> None:
        folder = self.ai_batch_store.folder_for(batch.slug) or (self.ai_batches_root / batch.slug)
        if not folder.exists():
            self._status("Batch folder missing.", "warn")
            return
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except OSError as exc:
            self._status(f"Could not open folder: {exc}", "error")

    def _view_ai_batch_screenshots(self, batch: AiBatch) -> None:
        paths: list[Path] = []
        titles: list[str] = []
        folder = self.ai_batch_store.folder_for(batch.slug)
        for req in batch.requests:
            if req.result is None:
                continue
            if req.result.path:
                candidate = Path(req.result.path)
                if not candidate.is_absolute() and folder is not None:
                    candidate = folder / candidate
                if candidate.exists():
                    paths.append(candidate)
                    titles.append(req.label)
                    continue
            if req.result.screen_map_batch:
                batch_folder = self.screen_maps_root / req.result.screen_map_batch
                shot_name = req.result.screen_map_shot
                if shot_name:
                    candidate = batch_folder / shot_name
                    if candidate.exists():
                        paths.append(candidate)
                        titles.append(req.label)
                elif batch_folder.exists():
                    for png in sorted(batch_folder.glob("*.png")):
                        paths.append(png)
                        titles.append(f"{req.label}: {png.stem}")
        for slug in batch.linked_screen_map_batches:
            batch_folder = self.screen_maps_root / slug
            if not batch_folder.exists():
                continue
            for png in sorted(batch_folder.glob("*.png")):
                if png not in paths:
                    paths.append(png)
                    titles.append(f"{slug}: {png.stem}")
        viewer = open_image_viewer(self, paths, titles=titles, title=f"AI batch — {batch.name}")
        if viewer is None:
            self._status("No screenshots linked to this batch yet.", "warn")

    def _link_ai_batch_screen_map(self, batch: AiBatch) -> None:
        catalogs = list_screen_map_batches(self.screen_maps_root)
        if not catalogs:
            self._status("No Screen Map batches on disk to link.", "warn")
            return
        choice = self._ask_choice(
            "Link Screen Map batch",
            "Pick a Screen Map batch to attach:",
            [f"{item.slug}  ({item.shot_count} shots)" for item in catalogs],
        )
        if choice is None:
            return
        slug = catalogs[choice].slug
        try:
            self.ai_batch_store.link_screen_map(batch, slug)
            # Also mark first pending screen_map request done if present.
            pending = next(
                (
                    req
                    for req in batch.requests
                    if req.status == "pending" and req.kind in ("screen_map_batch", "screenshot", "screen_map_shot")
                ),
                None,
            )
            if pending is not None:
                self.ai_batch_store.mark_request(
                    batch,
                    pending.id,
                    status="done",
                    result=RequestResult(
                        summary=f"Linked Screen Map batch {slug}",
                        screen_map_batch=slug,
                        captured_at=now_iso(),
                    ),
                )
        except AiBatchError as exc:
            self._status(str(exc), "error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        self._status(f"Linked Screen Map '{slug}' to AI batch '{batch.name}'.", "ok")

    def _ask_choice(self, title: str, prompt: str, options: list[str]) -> int | None:
        if not options:
            return None
        result: dict[str, int | None] = {"value": None}
        dialog = self._modal(title, 460, min(120 + 36 * len(options), 420))
        ctk.CTkLabel(dialog, text=prompt, wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(16, 8))
        box = ctk.CTkScrollableFrame(dialog, height=min(36 * len(options), 260))
        box.pack(fill="both", expand=True, padx=16)

        def pick(index: int) -> None:
            result["value"] = index
            dialog.destroy()

        for index, label in enumerate(options):
            ctk.CTkButton(box, text=label, anchor="w", command=lambda i=index: pick(i)).pack(fill="x", pady=2)

        def cancel(_event=None) -> None:
            result["value"] = None
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(buttons, text="Cancel", width=90, command=cancel).pack(side="right")
        dialog.bind("<Escape>", cancel)
        self.wait_window(dialog)
        return result["value"]

    def _mark_ai_request(self, batch: AiBatch, request: BatchRequest, status: str) -> None:
        result = request.result
        if status == "done" and result is None:
            result = RequestResult(summary="Marked done in Idle Lab UI", captured_at=now_iso())
        try:
            self.ai_batch_store.mark_request(batch, request.id, status=status, result=result)
        except AiBatchError as exc:
            self._status(str(exc), "error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        self._status(f"Request '{request.label}' → {status} ({batch.name}).", "ok")

    def _add_ai_feedback(self, batch: AiBatch) -> None:
        text = self._ask_text("Feedback for AI", "What did this batch miss / what should the next pass grab?")
        if text is None:
            return
        try:
            self.ai_batch_store.add_feedback(batch, text, author="human")
        except AiBatchError as exc:
            self._status(str(exc), "error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        self._status("Feedback saved on batch.", "ok")

    def _snapshot_event_into_ai_batch(self, batch: AiBatch, request: BatchRequest) -> None:
        events = sorted(self.auto_store.events.values(), key=lambda event: event.title.lower())
        if not events:
            self._status("No automation events loaded.", "warn")
            return
        choice = self._ask_choice(
            "Snapshot event",
            "Which event should be recorded into this request?",
            [f"{event.title} ({event.id})" for event in events],
        )
        if choice is None:
            return
        event = events[choice]
        try:
            payload = self.ai_batch_store.snapshot_event(self.auto_store.events, event.id)
            folder = self.ai_batch_store.folder_for(batch.slug)
            rel = f"captures/{event.id}.json"
            if folder is not None:
                capture_dir = folder / "captures"
                capture_dir.mkdir(parents=True, exist_ok=True)
                (capture_dir / f"{event.id}.json").write_text(
                    json.dumps(payload, indent=2) + "\n",
                    encoding="utf-8",
                )
            self.ai_batch_store.mark_request(
                batch,
                request.id,
                status="done",
                result=RequestResult(
                    summary=f"Event snapshot: {event.title}",
                    path=rel,
                    event_id=event.id,
                    captured_at=now_iso(),
                    payload=payload,
                ),
            )
        except (AiBatchError, OSError) as exc:
            self._status(str(exc), "error")
            return
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        self._status(f"Captured event '{event.title}' into AI batch.", "ok")

    def _ask_screen_map_title(self) -> str | None:
        """Title dialog after a capture. Esc cancels; Space types normally."""

        result: dict[str, str | None] = {"value": None}
        dialog = self._modal("Screenshot title", 420, 170, keep_topmost=True)
        self._screen_map_title_dialog = dialog
        ctk.CTkLabel(dialog, text="Shot captured — name this screen").pack(anchor="w", padx=16, pady=(16, 6))
        entry = ctk.CTkEntry(dialog, width=380)
        entry.pack(padx=16)

        def ok(_event=None) -> None:
            text = entry.get().strip()
            if not text:
                return
            result["value"] = text
            dialog.destroy()

        def cancel(_event=None) -> None:
            result["value"] = None
            dialog.destroy()

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Cancel", width=90, command=cancel).pack(side="right", padx=(8, 0))
        ctk.CTkButton(buttons, text="Save", width=100, command=ok).pack(side="right")
        entry.bind("<Return>", ok)
        dialog.bind("<Escape>", cancel)
        dialog.after(1, lambda: self._arm_dialog_focus(dialog, entry))
        self._arm_dialog_focus(dialog, entry)
        self.wait_window(dialog)
        self._screen_map_title_dialog = None
        return result["value"]


    def _automation_anchor_rect(self):
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            return None
        return rect

    def _automation_anchor_hwnd(self):
        status, hwnd, rect, _title = self.anchor_target.snapshot()
        if status != "ok":
            return None, None
        return hwnd, rect

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
            humanize=self._humanize_profile(),
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
