"""Control panel for anchoring a window and playing presets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tkinter import filedialog, messagebox
import threading

import customtkinter as ctk

from idle_lab.anchor import Anchor
from idle_lab.automations.guide_overlay import GuideOverlay
from idle_lab.automations.mouse_sync import play_points_sync
from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.automations.validate import (
    dry_run_collection,
    dry_run_event,
    format_report,
    validate_store,
)
from idle_lab.ai_batch.schema import AiBatch, BatchRequest, RequestResult, now_iso
from idle_lab.ai_batch.store import AiBatchError, AiBatchStore
from idle_lab.ai_batch.runner import AiBatchRunner, AiBatchRunnerError
from idle_lab.ai_batch.ui import AiBatchPanel
from idle_lab.automations.ui import AutomationsPanel
from idle_lab.automations.walkthrough import Walkthrough
from idle_lab.automations.schema import Collection
from idle_lab.click_logger import ClickLogger
from idle_lab.comment_ui import make_comment_button, open_comment_dialog
from idle_lab.comments import (
    CommentStore,
    collection_comment_path,
    event_comment_path,
    mission_comment_path,
    mission_request_comment_path,
    preset_comment_path,
    screen_map_batch_comment_path,
    screen_map_shot_comment_path,
)
from idle_lab.flight_deck.keys import DEFAULT_EXPAND_VK, vk_label
from idle_lab.flight_deck.keymap import KeymapError, default_keymap_path, load_keymap
from idle_lab.flight_deck.shell import (
    EscAction,
    ShellPhase,
    active_unanchored_prompt,
    close_confirm_prompt,
    inactive_prompt,
    resolve_escape,
)
from idle_lab.flight_deck.window import FlightDeckWindow
from idle_lab.shell.deck_mode import (
    DeckMode,
    mode_abandons_menu,
    mode_display_name,
    mode_legend,
    mode_prompt,
)
from idle_lab.shell.atom_create import (
    AtomCreatePhase,
    AtomDraft,
    atom_create_legend,
    build_atom_create_keymap,
    draft_step_from_token,
    save_atom_draft,
)
from idle_lab.shell.console import SharedConsole
from idle_lab.shell.floating import FloatingLabWindow
from idle_lab.shell.idle_lab_window import build_tab_host
from idle_lab.shell.resume import resume_prompt
from idle_lab.shell.settings_panel import (
    BOOT_FLIGHT_DECK,
    BOOT_IDLE_LAB,
    build_settings_body,
    normalize_boot_surface,
)
from idle_lab.shell.surfaces import SurfaceKind, can_show_idle_lab, ensure_exclusive
from idle_lab.shell.tabs import normalize_last_tab
from idle_lab.taxonomy import (
    TaxonomyError,
    default_taxonomy_path,
    load_taxonomy,
    resolve_taxonomy,
)
from idle_lab.hotkeys import InputHooks
from idle_lab.humanize import HUMANIZE_LEVELS, HumanizeProfile, normalize_level
from idle_lab.image_viewer import open_image_viewer
from idle_lab.lab_mode import SuperviseGate, humanize_level_tooltip, normalize_lab_mode
from idle_lab.lab_watch import dir_fingerprint
from idle_lab.launch_flags import restart_command
from idle_lab.models import ClickPoint, Preset, normalized_to_screen, screen_to_normalized
from idle_lab.live_control import LiveControlController, LiveControlError
from idle_lab.live_control.overlay import LiveControlOverlay
from idle_lab.single_instance import release as release_single_instance
from idle_lab.single_instance import start_wake_watcher, try_acquire as try_acquire_single_instance
from idle_lab.tray import TrayController
from idle_lab.observation import ObservationController, ObservationError
from idle_lab.observation.session import auto_observation_title
from idle_lab.overlay import Overlay
from idle_lab.player import Player
from idle_lab.presets import PresetError, PresetStore, load_preset, preset_to_dict, project_root, slug
from idle_lab.prompt_packet import export_prompt_packet
from idle_lab.recorder import Recorder
from idle_lab.screen_map.batch import ScreenMapController, ScreenMapError, add_shot, create_batch
from idle_lab.screen_map.catalog import BatchSummary, list_batches as list_screen_map_batches
from idle_lab.screen_map.manifest import load_manifest, save_manifest
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
    def __init__(self, *, auto_anchor: bool = False) -> None:
        super().__init__()
        self._auto_anchor_on_boot = bool(auto_anchor)
        self.title("Errriiiccc's Idle Lab")
        self.geometry("1100x920")
        self.minsize(900, 700)
        root = project_root()
        self.store = PresetStore(root / "presets")
        self.settings_path = root / "settings.json"
        self.settings, settings_error = load_settings(self.settings_path)
        self.auto_store = AutomationStore(root / "automations")
        auto_errors = self.auto_store.load_all()
        (root / "automations" / "templates").mkdir(parents=True, exist_ok=True)
        self.supervise_gate = SuperviseGate(
            ask=self._supervised_ask,
            enabled=normalize_lab_mode(self.settings.lab_mode) == "supervised",
        )
        self.auto_runtime = AutomationRuntime(
            store=self.auto_store,
            runs_dir=root / "runs",
            get_anchor_rect=self._automation_anchor_rect,
            get_anchor_hwnd=self._automation_anchor_hwnd,
            get_humanize=self._humanize_profile,
            restore_cursor=bool(self.settings.restore_cursor),
            play_preset=self._automation_play_preset,
            supervise_gate=self.supervise_gate,
            trace_level=self.settings.trace_level,
            templates_dir=root / "automations" / "templates",
        )
        self.auto_panel: AutomationsPanel | None = None
        self.screen_map_panel: ScreenMapPanel | None = None
        self.ai_batch_panel: AiBatchPanel | None = None
        self.screen_map = ScreenMapController()
        self.observation = ObservationController()
        self._observation_ui_refresh_at = 0.0
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
        self.comment_store = CommentStore(root / "lab-comments.json")
        self.comment_store.load()
        self._current_tab = normalize_last_tab(self.settings.last_tab)
        self._resume_handle = False
        self._deck_mode = DeckMode.MENU
        self._atom_create_phase = AtomCreatePhase.IDLE
        self._atom_draft = AtomDraft()
        self._shared_console = SharedConsole()
        self._floating_lab: FloatingLabWindow | None = None
        self._settings_window = None
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
        self._last_refresh_at: float | None = None
        self._watch_paths = [
            root / "presets",
            root / "automations",
            root / "ai-batches",
            root / "screen-maps",
            root / "lab-comments.json",
        ]
        self._disk_fingerprint = dir_fingerprint(self._watch_paths)
        self._begin_load()
        self._build()
        self._end_load()
        self.update_idletasks()
        self.overlay = Overlay(self, self._on_marker_moved, self._on_marker_released)
        self.live_control_overlay = LiveControlOverlay(self)
        self._live_control_owns_observation = False
        self.live_control = LiveControlController(
            overlay=self.live_control_overlay,
            project_root=root,
            get_anchor=self._live_control_anchor,
            get_humanize=self._humanize_profile,
            run_event_once=self._live_control_run_event_once,
            on_evidence=self._live_control_evidence,
            post_event=self.hooks.events.put,
            on_legend_change=self._live_control_legend_changed,
            on_pause_change=self._live_control_pause_changed,
            on_toggle_token=self._live_control_toggle_token_changed,
            console_enabled=bool(self.settings.lco_console_enabled),
            console_verbosity=str(self.settings.lco_console_verbosity or "results"),
            cancel_event=self.hooks.state.live_control_cancel,
            log=self._live_control_log,
            restore_cursor=bool(self.settings.restore_cursor),
            async_actions=True,
        )
        self._lco_console_window = None
        self._lco_console_dirty = False
        self.live_control.console.on_change = self._lco_console_session_changed
        from idle_lab.live_control.molecule_lco import MoleculeLcoBridge

        self._molecule_lco = MoleculeLcoBridge(
            self,
            automations_root=root / "automations",
            on_run_molecule=self._lco_run_molecule,
            log=self._live_control_log,
        )
        self.live_control.attach_molecule_bridge(self._molecule_lco)
        self.auto_runtime.attach_shared_lco(self.live_control)
        self._molecule_lab_close_confirm = False
        self.flight_deck = FlightDeckWindow(
            self,
            on_close=self._flight_deck_user_close,
            on_activate_toggle=self._flight_deck_toggle_activate,
            on_geometry=self._flight_deck_store_geometry,
        )
        self._taxonomy = None
        self._flight_deck_keymap = None
        self._molecule_composer = None
        self._shell_phase = ShellPhase.INACTIVE
        self._boot_candidate_hwnd: int | None = None
        self._boot_offer_title: str | None = None
        self._lab_visible = False
        self._tray: TrayController | None = None
        self._lab_saved_geometry: str | None = None
        self._sync_flight_deck_expand_vk()
        errors = self.store.load_all()
        # Phase 0: clicker UI is not mounted — keep preset selection in memory only.
        self.current = self.store.presets[0] if self.store.presets else None
        self._reload_taxonomy()
        self._sync_lco_console_deck_labels()
        self._sync_settings_deck_labels()
        self._refresh_screen_map_catalog()
        # Lab X → exclusive Flight Deck (deactivated). Quit is Esc peel on the deck.
        self.protocol("WM_DELETE_WINDOW", self._withdraw_idle_lab_to_deck)
        try:
            self.hooks.start()
        except OSError as exc:
            self._status(f"Hotkeys unavailable: {exc}", "error")
        self.bind("<F5>", lambda _e: self._refresh_lab())
        self.after(120, self._poll_anchor)
        self.after(30, self._drain_hooks)
        self.after(50, self._drain_player)
        self.after(80, self._drain_automations)
        self.after(100, self._drain_ai_batch_runner)
        self.after(1500, self._poll_disk_watch)
        self.after(500, self._poll_activity)
        tray_error = self._start_tray()
        start_wake_watcher(self._schedule_ui, self._on_single_instance_wake)
        if settings_error:
            self._status(settings_error, "warn")
        elif errors:
            self._status("Skipped preset files: " + "; ".join(errors), "error")
        elif auto_errors:
            self._status("Skipped automation files: " + "; ".join(auto_errors), "error")
        elif ai_errors:
            self._status("Skipped AI batch files: " + "; ".join(ai_errors), "error")
        elif tray_error:
            self._status(tray_error, "warn")
        else:
            self._status(
                "Idle Lab · Info. Activate Deck for hotkeys. Info outline is live; Labs still stub.",
                "info",
            )
        boot = normalize_boot_surface(self.settings.boot_surface)
        self._lab_visible = boot == BOOT_IDLE_LAB
        # Park Idle Lab before first paint when Deck is the boot surface.
        if boot == BOOT_FLIGHT_DECK:
            self._hide_lab(quiet=True)
        self.after(0, self._start_boot)

    def _build(self) -> None:
        self.status_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=980)
        self.status_label.pack(side="bottom", fill="x", padx=12, pady=(4, 10))

        self._build_chrome()

        # Target tab strip. Info is nested docs; Labs stay stubs until later phases.
        self.auto_panel = None
        self.atom_lab_pane = None
        self._molecule_lab_root = None
        self.screen_map_panel = None
        self.ai_batch_panel = None
        self.body = None
        self.preset_list = None
        self.tabs, self._current_tab = build_tab_host(
            self,
            on_tab_changed=self._on_tab_changed,
            last_tab=self.settings.last_tab,
            on_open_tab=self._goto_lab_tab,
            on_start_live_overlay=self._start_live_overlay_from_lab,
            on_open_atom_create=self._open_atom_create_from_lab,
            on_open_composer=self._open_molecule_composer,
            host_automations=self._host_molecule_automations,
            host_atom_pane=self._host_molecule_atom_pane,
            on_goto_molecule_tab=self._goto_molecule_subtab,
            on_register_molecule_lab_root=self._register_molecule_lab_root,
            host_observation_user=self._host_observation_user,
            host_observation_ai=self._host_observation_ai,
        )
        self.settings.last_tab = self._current_tab

    def _build_chrome(self) -> None:
        """Thin global chrome: brand, compact Anchor, Refresh/Restart/Stop all, activity."""

        chrome = ctk.CTkFrame(self, corner_radius=12)
        chrome.pack(fill="x", padx=8, pady=(8, 4))

        left = ctk.CTkFrame(chrome, fg_color="transparent")
        left.pack(side="left", fill="y", padx=(12, 8), pady=8)
        ctk.CTkLabel(
            left,
            text="Errriiiccc's Idle Lab",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w")

        self.header_actions = ctk.CTkFrame(chrome, fg_color="transparent")
        self.header_actions.pack(side="right", padx=(8, 12), pady=8)
        self.settings_button = ctk.CTkButton(
            self.header_actions,
            text="Settings",
            width=88,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._open_settings_from_lab,
        )
        self.settings_button.pack(side="right", padx=(6, 0))
        self.stop_all_button = ctk.CTkButton(
            self.header_actions,
            text="Deactivate",
            width=100,
            fg_color="#5A3030",
            hover_color="#7A4040",
            command=self._deactivate_from_idle_lab,
        )
        self.stop_all_button.pack(side="right", padx=(6, 0))
        self.restart_button = ctk.CTkButton(
            self.header_actions,
            text="Restart",
            width=88,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._restart_lab,
        )
        self.restart_button.pack(side="right", padx=(6, 0))
        self.refresh_button = ctk.CTkButton(
            self.header_actions,
            text="Refresh",
            width=88,
            command=self._refresh_lab,
        )
        self.refresh_button.pack(side="right", padx=(6, 0))
        self.mode_menu = ctk.CTkOptionMenu(
            self.header_actions,
            values=["Auto", "Supervised"],
            width=110,
            command=self._on_lab_mode,
        )
        self.mode_menu.set("Supervised" if normalize_lab_mode(self.settings.lab_mode) == "supervised" else "Auto")
        self.mode_menu.pack(side="right", padx=(6, 0))

        mid = ctk.CTkFrame(chrome, fg_color="transparent")
        mid.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=6)

        anchor_row = ctk.CTkFrame(mid, fg_color="transparent")
        anchor_row.pack(anchor="w")
        self.anchor_button = ctk.CTkButton(
            anchor_row,
            text="Anchor",
            width=88,
            height=28,
            command=self._toggle_anchor_mode,
        )
        self.anchor_button.pack(side="left")
        self.clear_button = ctk.CTkButton(
            anchor_row,
            text="×",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#3A2030",
            text_color="#E25C5C",
            command=self._clear_anchor,
        )
        self.clear_button.pack(side="left", padx=(2, 0))
        self.anchor_dot = ctk.CTkLabel(anchor_row, text="●", text_color="#5A6474", width=16)
        self.anchor_dot.pack(side="left", padx=(6, 0))
        deck_col = ctk.CTkFrame(anchor_row, fg_color="transparent")
        deck_col.pack(side="left", padx=(10, 0))
        self.flight_deck_button = ctk.CTkButton(
            deck_col,
            text="Open Flight Deck",
            width=140,
            height=28,
            fg_color="#1E3A4A",
            hover_color="#2A5568",
            command=self._open_flight_deck_from_lab,
        )
        self.flight_deck_button.pack(anchor="w")
        self.flight_deck_button_hint = ctk.CTkLabel(
            deck_col,
            text="(closes Idle Lab)",
            anchor="w",
            text_color="#7E8796",
            font=ctk.CTkFont(size=11),
        )
        self.flight_deck_button_hint.pack(anchor="w")
        # Activate-key remap lives in Settings (A8).

        self.anchor_label = ctk.CTkLabel(
            mid,
            text="No window",
            anchor="w",
            justify="left",
            text_color="#7E8796",
            font=ctk.CTkFont(size=11),
        )
        self.anchor_label.pack(anchor="w", pady=(2, 0))

        pulse = ctk.CTkFrame(mid, fg_color="transparent")
        pulse.pack(anchor="w", pady=(4, 0))
        self.mode_chip = ctk.CTkLabel(
            pulse,
            text="Mode: Auto",
            anchor="w",
            text_color="#A8B4C4",
            font=ctk.CTkFont(size=11),
        )
        self.mode_chip.pack(side="left")
        self.activity_label = ctk.CTkLabel(
            pulse,
            text="Activity: Idle",
            anchor="w",
            text_color="#8EE0C2",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.activity_label.pack(side="left", padx=(10, 0))
        self.files_badge = ctk.CTkLabel(
            pulse,
            text="",
            anchor="w",
            text_color="#E7C36A",
            font=ctk.CTkFont(size=11),
        )
        self.files_badge.pack(side="left", padx=(10, 0))

    def _build_clicker_body(self) -> None:
        header = ctk.CTkFrame(self.body, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(header, text="Bench", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Presets are reusable verbs — fractions of the anchored window for Missions and Loops.",
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
        self.humanize_menu.set(_HUMANIZE_LABELS.get(normalize_level(self.settings.humanize_level), "Off"))
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
            text="F6 starts/stops Bench playback. F7 pauses. F8 = Stop all (Loops, Missions, Bench, Observe). Esc also stops the active run. F6–F8 are captured while this app is open.",
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
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        anchored = status in ("ok", "minimized", "closed")
        if getattr(self, "anchor_button", None) is not None:
            self.anchor_button.configure(text="Cancel" if waiting else "Anchor")
            self.anchor_button.configure(state="disabled" if busy else "normal")
            if waiting:
                self.anchor_button.configure(fg_color="#C9A227", hover_color="#E0B93A", text_color="#161616")
            elif anchored:
                self.anchor_button.configure(
                    fg_color="#2F6B4A",
                    hover_color="#3A855C",
                    text_color="#E8FFF2",
                )
            else:
                self.anchor_button.configure(
                    fg_color=["#3B8ED0", "#1F6AA5"],
                    hover_color=["#36719F", "#144870"],
                    text_color="#DCE4EE",
                )
        clear_ok = anchored and not busy and not waiting
        if getattr(self, "clear_button", None) is not None:
            self.clear_button.configure(
                state="normal" if clear_ok else "disabled",
                text_color="#E25C5C" if clear_ok else "#5A6474",
            )
        if self._clicker_ui_ready() and getattr(self, "create_button", None) is not None:
            self.create_button.configure(state="disabled" if busy else "normal")
            can_edit = self.current is not None and not busy
            for button in (self.rename_button, self.duplicate_button, self.delete_button, self.export_button):
                button.configure(state="normal" if can_edit else "disabled")
            self.start_button.configure(state="disabled" if busy or self.current is None else "normal")
            self.stop_button.configure(state="normal" if self.player.is_active else "disabled")
            self.pause_button.configure(state="normal" if self.player.is_active else "disabled")
        self._update_banner()
        self._update_activity()
        self._update_flight_deck_lab_button()

    def _update_banner(self) -> None:
        if getattr(self, "banner", None) is None:
            return
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
        self._status(humanize_level_tooltip(self.settings.humanize_level), "info")

    def _on_lab_mode(self, value: str) -> None:
        if self._loading():
            return
        mode = "supervised" if str(value).strip().lower().startswith("supervised") else "auto"
        self.settings.lab_mode = mode
        self.supervise_gate.enabled = mode == "supervised"
        self._save_settings()
        self._update_activity()
        self._status(
            "Supervised: confirm each click/preset." if mode == "supervised" else "Auto: run without confirms.",
            "info",
        )

    def _supervised_ask(self, description: str) -> bool:
        """Worker-thread safe confirm via UI thread + Event."""

        result = {"ok": False}
        done = threading.Event()

        def ask() -> None:
            try:
                result["ok"] = bool(
                    messagebox.askokcancel(
                        "Supervised",
                        f"{description}\n\nConfirm to actuate. Cancel skips this action.",
                        parent=self,
                    )
                )
            finally:
                done.set()

        try:
            self.after(0, ask)
        except Exception:
            return False
        while not done.wait(0.05):
            if self.auto_runtime._stop.is_set() or self.ai_batch_runner._stop.is_set():
                return False
        return bool(result["ok"])

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
            if getattr(self, "flight_deck", None) is not None:
                self._maybe_auto_show_flight_deck(status, rect)
        except Exception as exc:
            self._status(f"Anchor poll failed: {exc}", "error")
        if self._alive:
            self.after(100, self._poll_anchor)

    def _render_anchor(self, status: str, rect, title: str) -> None:
        if status == "ok" and rect is not None:
            short = (title or "Window").strip()
            if len(short) > 36:
                short = short[:33] + "…"
            text = f"{short} · {rect.width}×{rect.height}"
            dot = "#8EE0C2"
        elif status == "minimized":
            text = f"{title} minimized"
            dot = "#E7C36A"
        elif status == "closed":
            text = "Window closed"
            dot = "#F09595"
        else:
            text = "No window"
            dot = "#5A6474"
        self.anchor_label.configure(text=text)
        self.anchor_dot.configure(text_color=dot)
        clear_ok = status in ("ok", "minimized", "closed") and not self._busy() and not self._anchor_waiting
        self.clear_button.configure(
            state="normal" if clear_ok else "disabled",
            text_color="#E25C5C" if clear_ok else "#5A6474",
        )

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
        status, _hwnd, rect, title = self.anchor_target.snapshot()
        self.settings.last_anchor_title = (title or "").strip() or None
        try:
            self._save_settings()
        except Exception:
            pass
        self._status(f"Anchored to {title}.", "ok")
        self._leave_boot_into_deck(status=status, rect=rect)

    def _clear_anchor(self) -> None:
        if self._busy():
            return
        self._cancel_anchor_mode()
        self.anchor_target.clear()
        self.settings.last_anchor_title = None
        try:
            self._save_settings()
        except Exception:
            pass
        self.overlay.set_visible(False)
        if self._shell_phase is ShellPhase.ACTIVE:
            self._activate_flight_deck()
        else:
            self._enter_inactive()
        self._status("Anchor cleared.", "info")

    # --- Flight deck (in-flight HUD) ---

    def _reload_taxonomy(self) -> None:
        """Load Lab Loops taxonomy + separate flight-deck accordion catalog."""

        path = default_taxonomy_path(project_root())
        try:
            raw = load_taxonomy(path)
            resolved = resolve_taxonomy(
                raw,
                event_ids=self.auto_store.events.keys(),
                collection_ids=self.auto_store.collections.keys(),
                preset_names={preset.name for preset in self.store.presets},
            )
            self._taxonomy = resolved
            if self.auto_panel is not None:
                self.auto_panel.set_taxonomy(resolved)
        except TaxonomyError as exc:
            self._taxonomy = None
            if self.auto_panel is not None:
                self.auto_panel.set_taxonomy(None)
            self._status(f"Taxonomy: {exc}", "warn")

        deck_path = default_keymap_path(project_root())
        try:
            self._flight_deck_keymap = load_keymap(deck_path)
            if self._deck_mode is DeckMode.ATOM_CREATE:
                self._install_atom_create_keymap()
            else:
                self.flight_deck.set_keymap(self._flight_deck_keymap)
                self._sync_lco_console_deck_labels()
                self._sync_settings_deck_labels()
        except (KeymapError, OSError) as exc:
            self._flight_deck_keymap = None
            if self._deck_mode is not DeckMode.ATOM_CREATE:
                self.flight_deck.set_keymap(None)
            self._status(f"Flight deck catalog: {exc}", "warn")

    def _flight_deck_expand_vk_for_anchor(self) -> int:
        status, _hwnd, _rect, title = self.anchor_target.snapshot()
        if status in ("ok", "minimized", "closed") and title:
            mapped = (self.settings.flight_deck_expand_by_anchor or {}).get(title)
            if mapped:
                return int(mapped)
        return int(self.settings.flight_deck_expand_vk or DEFAULT_EXPAND_VK)

    def _sync_flight_deck_expand_vk(self) -> None:
        vk = self._flight_deck_expand_vk_for_anchor()
        self.hooks.state.flight_deck_expand_vk = vk
        self.flight_deck.set_expand_vk(vk)
        if getattr(self, "remap_expand_button", None) is not None:
            self.remap_expand_button.configure(text=f"Activate [{vk_label(vk)}]")

    def _flight_deck_store_geometry(self, geometry: str) -> None:
        from idle_lab.flight_deck.window import sanitize_geometry

        cleaned = sanitize_geometry(geometry)
        if not cleaned:
            return
        self.settings.flight_deck_geometry = cleaned
        try:
            self._save_settings()
        except Exception:
            pass

    def _flight_deck_is_visible(self) -> bool:
        try:
            return bool(self.flight_deck.winfo_viewable())
        except Exception:
            return False

    def _show_flight_deck(self, *, allow_unanchored: bool = True) -> None:
        status, _hwnd, rect, _title = self.anchor_target.snapshot()
        anchored = status in ("ok", "minimized")
        if not anchored and not allow_unanchored and self._shell_phase is ShellPhase.INACTIVE:
            # Inactive chrome is always allowed; activate handles anchoring next.
            pass
        self.settings.flight_deck_user_hidden = False
        self._save_settings()
        self._sync_flight_deck_expand_vk()
        self.flight_deck.show_deck(
            beside=rect if status == "ok" else None,
            geometry=self.settings.flight_deck_geometry,
        )
        self.hooks.state.flight_deck_open = True
        self.hooks.state.flight_deck_expand_armed = True
        self._sync_flight_deck_run_state()
        self._update_flight_deck_lab_button()
        self._sync_shell_hook_flags()

    def _hide_flight_deck(self, *, user_hidden: bool) -> None:
        """Withdraw the deck window (Lab stays up). Not the same as deactivate."""

        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._cancel_close_confirm()
        self.flight_deck.collapse_menu()
        self.flight_deck.hide_deck()
        self._shell_phase = ShellPhase.INACTIVE
        self.hooks.state.flight_deck_open = False
        self.hooks.state.flight_deck_active = False
        self.hooks.state.flight_deck_expanded = False
        if user_hidden:
            self.settings.flight_deck_user_hidden = True
            self._save_settings()
        self._update_flight_deck_lab_button()
        self._sync_shell_hook_flags()

    def _flight_deck_user_close(self) -> None:
        """Close button → confirm. Hidden while inactive."""

        if self._shell_phase is ShellPhase.INACTIVE:
            return
        if self.live_control.active:
            self._exit_live_control(reason="operator")
            return
        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._cancel_close_confirm()
            return
        self._enter_close_confirm()

    def _sync_shell_hook_flags(self) -> None:
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        anchored = status in ("ok", "minimized")
        active = self._shell_phase is ShellPhase.ACTIVE
        deck_visible = self._flight_deck_is_visible()
        self.hooks.state.quit_confirm = self._shell_phase is ShellPhase.CLOSE_CONFIRM
        lab_open = self._molecule_lab_is_open()
        self.hooks.state.molecule_lab_active = bool(lab_open)
        self.hooks.state.molecule_lab_close_confirm = bool(
            lab_open and getattr(self, "_molecule_lab_close_confirm", False)
        )
        self.hooks.state.lab_visible = bool(self._lab_visible)
        self.hooks.state.resume_handle = bool(self._resume_handle) and (not self._lab_visible)
        self.hooks.state.deck_mode_active = bool(
            mode_abandons_menu(self._deck_mode) and (not self._lab_visible)
        )
        self.hooks.state.atom_create_active = bool(
            self._deck_mode is DeckMode.ATOM_CREATE and (not self._lab_visible)
        )
        # Keep Activate armed even when the deck window is withdrawn after Close.
        # While Idle Lab is the surface, Activate VK is silent (buttons only).
        self.hooks.state.flight_deck_open = bool(deck_visible) and (not self._lab_visible)
        self.hooks.state.flight_deck_expand_armed = not bool(self._lab_visible)
        self.hooks.state.flight_deck_active = bool(active and deck_visible and not self._lab_visible)
        self.hooks.state.flight_deck_anchored = bool(
            anchored and active and deck_visible and not self._lab_visible
        )
        self.hooks.state.flight_deck_expanded = bool(
            active
            and anchored
            and deck_visible
            and (not self._lab_visible)
            and self.flight_deck.expanded
        )

    def _is_lab_visible(self) -> bool:
        return bool(self._lab_visible)

    def _is_anchored(self) -> bool:
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        return status in ("ok", "minimized")

    def _refresh_boot_candidate(self) -> None:
        self._boot_candidate_hwnd = None
        self._boot_offer_title = None
        last = (self.settings.last_anchor_title or "").strip() or None
        if not last:
            return
        hwnd = win32_api.find_window_by_title(last, our_pid=self.hooks.state.our_pid)
        self._boot_offer_title = last
        if hwnd:
            self._boot_candidate_hwnd = int(hwnd)

    def _active_unanchored_prompt_text(self) -> str:
        self._refresh_boot_candidate()
        last = self._boot_offer_title
        return active_unanchored_prompt(
            last_title=last,
            candidate_found=bool(self._boot_candidate_hwnd),
            lab_visible=self._is_lab_visible(),
        )

    def _start_boot(self) -> None:
        """Boot from Settings preference: Idle Lab (factory) or Flight Deck."""

        tab = normalize_last_tab(self.settings.last_tab)
        try:
            self.tabs.set(tab)
        except Exception:
            tab = "Info"
            self.tabs.set(tab)
        self._current_tab = tab
        self.settings.last_tab = tab
        self._clear_resume_handle()
        self._exit_deck_mode(quiet=True)
        self.update_idletasks()
        boot = normalize_boot_surface(self.settings.boot_surface)
        if boot == BOOT_FLIGHT_DECK:
            self._switch_to_flight_deck_surface(activate=False)
            if self._auto_anchor_on_boot:
                self._try_auto_anchor_on_boot()
                return
            self._status("Flight Deck (boot preference). Activate to listen.", "info")
            return
        self._show_idle_lab_surface(quiet=True)
        if self._auto_anchor_on_boot:
            self._try_auto_anchor_on_boot()
            return
        self._shell_phase = ShellPhase.INACTIVE
        self._sync_shell_hook_flags()
        self._status(f"Idle Lab · {tab}. Activate Deck for hotkeys.", "info")

    def _try_auto_anchor_on_boot(self) -> None:
        """Restart path: rebind last title; honor boot surface exclusivity."""

        boot = normalize_boot_surface(self.settings.boot_surface)
        self._refresh_boot_candidate()
        hwnd = self._boot_candidate_hwnd
        if hwnd:
            self._apply_anchor(int(hwnd))
            if boot == BOOT_FLIGHT_DECK:
                self._switch_to_flight_deck_surface(activate=False)
                self._status("Flight Deck (boot preference). Activate to listen.", "info")
                return
            self._show_idle_lab_surface(quiet=True)
            return
        if self._boot_offer_title:
            # Last title remembered but window gone — Deck surface for re-anchor prompt.
            self._switch_to_flight_deck_surface(activate=True)
            return
        if boot == BOOT_FLIGHT_DECK:
            self._switch_to_flight_deck_surface(activate=False)
            return
        self._shell_phase = ShellPhase.INACTIVE
        self._sync_shell_hook_flags()

    def _enter_inactive(self, *, resume: bool = False) -> None:
        self._shell_phase = ShellPhase.INACTIVE
        key = vk_label(self._flight_deck_expand_vk_for_anchor())
        if resume:
            self._set_resume_handle(True)
            prompt = resume_prompt(activate_key=key)
        else:
            self._clear_resume_handle()
            prompt = inactive_prompt(activate_key=key)
        self.flight_deck.set_shell_phase(
            ShellPhase.INACTIVE,
            prompt=prompt,
            lab_visible=self._is_lab_visible(),
            anchored=self._is_anchored(),
        )
        self._show_flight_deck(allow_unanchored=True)
        self._sync_shell_hook_flags()
        self._status(prompt, "info")

    def _activate_flight_deck(self) -> None:
        self._clear_resume_handle()
        self._ensure_deck_only_surface()
        self._shell_phase = ShellPhase.ACTIVE
        anchored = self._is_anchored()
        if anchored:
            status, _hwnd, rect, _title = self.anchor_target.snapshot()
            self.flight_deck.set_shell_phase(
                ShellPhase.ACTIVE,
                prompt="",
                lab_visible=False,
                anchored=True,
            )
            self.flight_deck.set_expanded(True)
            self._show_flight_deck()
            self._status("Flight deck active.", "ok")
            _ = status, rect
        else:
            prompt = self._active_unanchored_prompt_text()
            self.flight_deck.set_shell_phase(
                ShellPhase.ACTIVE,
                prompt=prompt,
                lab_visible=False,
                anchored=False,
            )
            self._show_flight_deck(allow_unanchored=True)
            self._status(prompt, "info")
        self.flight_deck.focus_deck()
        try:
            hwnd = win32_api.widget_hwnd(self.flight_deck)
            if hwnd:
                win32_api.focus_window(hwnd)
        except Exception:
            pass
        self._sync_shell_hook_flags()
        self._update_flight_deck_lab_button()

    def _deactivate_flight_deck(self) -> None:
        """Deactivate = pause/stop runners; deck stays up with resume handle."""

        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._cancel_close_confirm()
            return
        # Live Overlay Lab: ` pauses in place — handled by toggle, not here.
        self.hooks.state.live_control_cancel.set()
        self.hooks.state.live_control_active = False
        self.hooks.state.live_control_paused = False
        self.hooks.state.live_control_toggle_token = None
        self._exit_deck_mode(quiet=True)
        self._stop_all()
        try:
            self.flight_deck.set_live_control_active(False)
        except Exception:
            pass
        self.flight_deck.collapse_menu()
        self._ensure_deck_only_surface()
        self._enter_inactive(resume=True)

    def _pause_or_resume_live_overlay(self) -> None:
        """Activate key while Live Overlay Lab is armed: pause ↔ resume (stay in LOL)."""

        if not self.live_control.active:
            return
        self.live_control.toggle_pause()
        self._sync_shell_hook_flags()
        try:
            self.flight_deck.set_live_control_paused(bool(self.live_control.paused))
        except Exception:
            pass

    def _flight_deck_toggle_activate(self) -> None:
        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            return
        # Live Overlay Lab: ` = pause / resume — never kick back to inactive FD.
        if self.live_control.active or (
            self.hooks.state.live_control_active and self._deck_mode is DeckMode.LOL
        ):
            if self.live_control.active:
                self._pause_or_resume_live_overlay()
            return
        if self._shell_phase is ShellPhase.INACTIVE:
            self._activate_flight_deck()
            return
        self._deactivate_flight_deck()

    def _set_resume_handle(self, active: bool) -> None:
        self._resume_handle = bool(active)
        self.hooks.state.resume_handle = bool(active)

    def _clear_resume_handle(self) -> None:
        self._set_resume_handle(False)

    def _anything_running(self) -> bool:
        return bool(
            self.hooks.state.stoppable
            or self.hooks.state.recording
            or self.hooks.state.playback
            or self.hooks.state.observation_active
            or self.hooks.state.walkthrough_active
            or self.hooks.state.live_control_active
            or self.live_control.active
            or self.auto_runtime.is_running
            or self.auto_runtime.collection_running
            or self.ai_batch_runner.is_running
            or self.player.is_active
            or self.recorder.active
        )

    def _ensure_deck_only_surface(self) -> None:
        """Hard rule: never show Idle Lab with Flight Deck; running → Deck only."""

        surface = ensure_exclusive(
            want=SurfaceKind.FLIGHT_DECK,
            anything_running=self._anything_running(),
        )
        _ = surface
        # Always park Idle Lab when Deck owns the surface (flag can lag first paint).
        self._hide_lab(quiet=True)

    def _show_idle_lab_surface(self, *, quiet: bool = False) -> None:
        """Exclusive Idle Lab: hide Deck, show Lab (refused while anything is running)."""

        if not can_show_idle_lab(anything_running=self._anything_running()):
            self._status("Something is running — Flight Deck only until Deactivate.", "warn")
            self._ensure_deck_only_surface()
            return
        self._clear_resume_handle()
        self._hide_flight_deck(user_hidden=False)
        self._shell_phase = ShellPhase.INACTIVE
        self._show_lab_window(quiet=quiet)
        self._sync_shell_hook_flags()
        self._update_flight_deck_lab_button()

    def _switch_to_flight_deck_surface(self, *, activate: bool = False) -> None:
        """Idle Lab chrome → Deck. Deck starts deactivated unless activate=True."""

        self._ensure_deck_only_surface()
        if activate:
            self._activate_flight_deck()
            return
        self._enter_inactive(resume=False)
        self._update_flight_deck_lab_button()

    def _leave_boot_into_deck(self, *, status: str, rect) -> None:
        """After a successful anchor while active: show hotkey deck."""

        self._shell_phase = ShellPhase.ACTIVE
        self.flight_deck.set_shell_phase(
            ShellPhase.ACTIVE,
            prompt="",
            lab_visible=self._is_lab_visible(),
            anchored=True,
        )
        self.flight_deck.set_expanded(True)
        self._show_flight_deck()
        self._sync_shell_hook_flags()
        self._status("Anchored — flight deck hotkeys ready.", "ok")
        _ = status, rect

    def _schedule_ui(self, fn) -> None:
        """Marshal tray / background callbacks onto the Tk UI thread."""

        try:
            self.after(0, fn)
        except Exception:
            pass

    def _start_tray(self) -> str | None:
        self._tray = TrayController(
            schedule=self._schedule_ui,
            on_open_lab=self._show_lab,
            on_show_deck=self._tray_show_flight_deck,
            on_quit=self._on_close,
            on_error=lambda msg: self._status(msg, "warn"),
        )
        return self._tray.start()

    def _on_single_instance_wake(self) -> None:
        """Another launch attempted — surface Lab + deck instead of a second process."""

        self._show_lab()
        try:
            self._tray_show_flight_deck()
        except Exception:
            pass
        self._status("Already running — brought Idle Lab to the front.", "info")

    def _tray_show_flight_deck(self) -> None:
        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._show_flight_deck(allow_unanchored=True)
            return
        if self._shell_phase is ShellPhase.INACTIVE:
            self._activate_flight_deck()
            return
        self._show_flight_deck(allow_unanchored=True)
        self.flight_deck.focus_deck()

    def _hide_lab(self, *, quiet: bool = False) -> None:
        """Hide Lab UI but keep HWND mapped so the flight-deck Toplevel can show.

        On Windows, ``withdraw`` / ``iconify`` on the root also hide child Toplevels
        (the flight deck). Alpha-0 + park off-screen keeps a taskbar button.
        """

        try:
            if self._lab_saved_geometry is None:
                geo = str(self.geometry() or "").strip()
                if geo and "x" in geo:
                    self._lab_saved_geometry = geo
            screen = win32_api.virtual_screen()
            self.geometry(f"1100x920+{screen.right + 120}+{screen.bottom + 120}")
            self.attributes("-alpha", 0.0)
            self.state("normal")
            self.deiconify()
            self.update_idletasks()
        except Exception:
            pass
        self._lab_visible = False
        self.flight_deck.set_lab_visible(False)
        if self._shell_phase is ShellPhase.ACTIVE and not self._is_anchored():
            prompt = self._active_unanchored_prompt_text()
            self.flight_deck.set_shell_phase(
                ShellPhase.ACTIVE,
                prompt=prompt,
                lab_visible=False,
                anchored=False,
            )
        self._sync_shell_hook_flags()
        if not quiet:
            self._status(
                "Idle Lab closed — Flight Deck only. I→1 opens Idle Lab again.",
                "info",
            )

    def _show_lab(self) -> None:
        """Tray / Esc resume / I → exclusive Idle Lab surface."""

        self._show_idle_lab_surface(quiet=False)

    def _show_lab_window(self, *, quiet: bool = False) -> None:
        """Map Idle Lab HWND (alpha/geometry). Caller enforces exclusivity."""

        try:
            self.flight_deck._orphan_from_owner()
        except Exception:
            pass
        try:
            self.attributes("-alpha", 1.0)
            if self._lab_saved_geometry:
                self.geometry(self._lab_saved_geometry)
            else:
                screen = win32_api.virtual_screen()
                self.geometry(f"1100x920+{screen.left + 80}+{screen.top + 60}")
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()
            self.update_idletasks()
        except Exception:
            pass
        try:
            hwnd = win32_api.widget_hwnd(self)
            if hwnd:
                win32_api.focus_window(hwnd)
        except Exception:
            pass
        self._lab_visible = True
        self.flight_deck.set_lab_visible(True)
        self._sync_shell_hook_flags()
        if not quiet:
            self._status(f"Idle Lab · {self._current_tab}.", "ok")

    def _enter_close_confirm(self) -> None:
        self._shell_phase = ShellPhase.CLOSE_CONFIRM
        prompt = close_confirm_prompt(lab_visible=self._is_lab_visible())
        self.flight_deck.set_shell_phase(
            ShellPhase.CLOSE_CONFIRM,
            prompt=prompt,
            lab_visible=self._is_lab_visible(),
            anchored=self._is_anchored(),
        )
        self._show_flight_deck(allow_unanchored=True)
        self.flight_deck.focus_deck()
        try:
            hwnd = win32_api.widget_hwnd(self.flight_deck)
            if hwnd:
                win32_api.focus_window(hwnd)
        except Exception:
            pass
        self._sync_shell_hook_flags()
        self._status(prompt, "warn")

    def _cancel_close_confirm(self) -> None:
        if self._shell_phase is not ShellPhase.CLOSE_CONFIRM:
            return
        # Stay active — close cancelled, not deactivated.
        self._activate_flight_deck()
        self._status("Close cancelled.", "info")

    def _confirm_close_flight_deck(self) -> None:
        """Enter on close-confirm: quit app if Lab hidden; else withdraw deck only."""

        if self._shell_phase is not ShellPhase.CLOSE_CONFIRM:
            return
        if self._is_lab_visible():
            self._hide_flight_deck(user_hidden=True)
            self._status("Flight deck closed. Activate deck from Lab or tray to reopen.", "info")
            return
        self._on_close()

    def _handle_shell_enter(self) -> None:
        if self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._confirm_close_flight_deck()
            return
        if self._shell_phase is not ShellPhase.ACTIVE or self._is_anchored():
            return
        self._refresh_boot_candidate()
        hwnd = self._boot_candidate_hwnd
        if not hwnd:
            self._status("No live window to re-anchor. Press A to set a new anchor.", "warn")
            return
        self._apply_anchor(int(hwnd))

    def _handle_shell_a(self) -> None:
        if self._shell_phase is not ShellPhase.ACTIVE or self._is_anchored():
            return
        self._toggle_anchor_mode()

    def _handle_shell_i(self) -> None:
        """Legacy bare-I path — prefer accordion I→1 (open_idle_lab)."""

        if self._is_lab_visible():
            return
        self._show_idle_lab_surface()

    def _handle_shell_r(self) -> None:
        # Inactive Deck owns only Activate — never swallow R there.
        if self._shell_phase is not ShellPhase.ACTIVE:
            return
        self._restart_lab()

    def _lab_runners_active(self) -> bool:
        return bool(
            self.auto_runtime.is_running
            or self.auto_runtime.collection_running
            or self.ai_batch_runner.is_running
            or (self.walkthrough is not None and self.walkthrough.active)
            or self.observation.active
            or self.screen_map.active
            or self.player.is_active
        )

    def _molecule_lab_runners_active(self) -> bool:
        return bool(
            self.auto_runtime.is_running
            or self.auto_runtime.collection_running
            or (self.walkthrough is not None and self.walkthrough.active)
            or self.player.is_active
        )

    def _observation_runners_active(self) -> bool:
        return bool(
            self.observation.active
            or self.screen_map.active
            or self.ai_batch_runner.is_running
        )

    def _stop_lab_runners(self) -> None:
        """Esc while a Lab is open: stop the run, keep the Lab."""

        stopped: list[str] = []
        if self.player.is_active:
            self.player.stop()
            stopped.append("playback")
        if self.ai_batch_runner.is_running:
            self.ai_batch_runner.stop()
            stopped.append("AI mission")
            if self.ai_batch_panel is not None:
                try:
                    self.ai_batch_panel.set_run_message("Runner: stop requested…", level="warn")
                except Exception:
                    pass
        if self.auto_runtime.is_running or self.auto_runtime.collection_running:
            self.auto_runtime.stop()
            stopped.append("molecules")
        if self.walkthrough is not None and self.walkthrough.active:
            self._stop_collection_walkthrough()
            stopped.append("walkthrough")
        if self.observation.active or self.screen_map.active:
            try:
                self._stop_observation(reason="escape", prompt_rename=False)
                stopped.append("observation")
            except Exception:
                pass
        self._update_activity()
        self._sync_shell_hook_flags()
        if stopped:
            self._status("Stopped: " + ", ".join(stopped) + " — Lab stays open.", "warn")
        else:
            self._status("Nothing running.", "info")

    def _handle_shell_escape(self) -> None:
        rebinding = bool(
            getattr(self.live_control, "molecule_bridge", None) is not None
            and getattr(self.live_control.molecule_bridge, "rebinding", False)
        )
        action = resolve_escape(
            phase=self._shell_phase,
            live_control_active=bool(self.live_control.active),
            live_control_rebinding=rebinding,
            molecule_lab_active=self._molecule_lab_is_open(),
            molecule_lab_running=self._molecule_lab_runners_active(),
            observation_running=self._observation_runners_active(),
            remap_active=bool(self.hooks.state.flight_deck_remap),
            deck_active=self._shell_phase is ShellPhase.ACTIVE,
            deck_expanded=bool(self.flight_deck.expanded),
            open_menu=bool(self.flight_deck.open_menu_key),
            resume_handle=bool(self._resume_handle),
            deck_mode_active=mode_abandons_menu(self._deck_mode),
        )
        if action is EscAction.CANCEL_LCO_REBIND:
            self.live_control.cancel_molecule_rebind()
        elif action is EscAction.EXIT_LIVE_CONTROL:
            self._exit_live_control(reason="escape")
            if self._deck_mode is DeckMode.LOL:
                self._exit_deck_mode(quiet=True)
            self._status("Live Overlay Lab closed — Flight Deck.", "info")
        elif action is EscAction.STOP_LAB_RUNNERS:
            self._stop_lab_runners()
        elif action is EscAction.CLOSE_MOLECULE_LAB:
            self._confirm_close_molecule_lab()
            if self._deck_mode is DeckMode.MOLECULE_LAB:
                self._exit_deck_mode(quiet=True)
        elif action is EscAction.EXIT_DECK_MODE:
            self._exit_deck_mode()
        elif action is EscAction.CANCEL_REMAP:
            self.hooks.state.flight_deck_remap = False
            self._status("Activate remap cancelled.", "info")
        elif action is EscAction.CANCEL_CLOSE:
            self._cancel_close_confirm()
        elif action is EscAction.CLOSE_SECTION:
            self.flight_deck.go_back()
            self._sync_shell_hook_flags()
        elif action is EscAction.COLLAPSE_MENU:
            self.flight_deck.go_back()
            self._sync_shell_hook_flags()
        elif action is EscAction.ENTER_CLOSE_CONFIRM:
            self._enter_close_confirm()
        elif action is EscAction.OPEN_IDLE_LAB:
            self._show_idle_lab_surface()

    def _withdraw_idle_lab_to_deck(self) -> None:
        """Window X / hide — exclusive Deck (deactivated), not both surfaces."""

        self._switch_to_flight_deck_surface(activate=False)

    def _goto_lab_tab(self, tab_name: str) -> None:
        """Info checklist link → switch Idle Lab tab."""

        name = normalize_last_tab(tab_name)
        try:
            self.tabs.set(name)
        except Exception:
            self._status(f"Could not open tab “{tab_name}”.", "warn")
            return
        self._current_tab = name
        self.settings.last_tab = name
        self._save_settings()
        if not self._is_lab_visible():
            self._show_idle_lab_surface()
        self._status(f"Opened {name}.", "ok")

    def _start_live_overlay_from_lab(self) -> None:
        """Live Overlay Lab tab → Deck + live enter (Anchor required)."""

        self._ensure_deck_only_surface()
        if self._shell_phase is ShellPhase.INACTIVE:
            self._activate_flight_deck()
        self._enter_deck_mode(DeckMode.LOL)
        try:
            self._enter_live_control()
        except Exception as exc:
            self._status(f"Live Overlay Lab: {exc}", "error")

    def _open_atom_create_from_lab(self) -> None:
        self._ensure_deck_only_surface()
        if self._shell_phase is ShellPhase.INACTIVE:
            self._activate_flight_deck()
        self._atom_create_phase = AtomCreatePhase.CREATE
        self._atom_draft = AtomDraft()
        self._enter_deck_mode(DeckMode.ATOM_CREATE)
        self._status(
            "Atom Create — accordion like Deck menu; Esc asks for id then saves (no silent save).",
            "info",
        )

    def _install_atom_create_keymap(self) -> None:
        keymap = build_atom_create_keymap(step_count=len(self._atom_draft.steps))
        self.flight_deck.set_deck_lab_mode(False)
        self.flight_deck.set_keymap(keymap)
        try:
            self.flight_deck.set_expanded(True)
        except Exception:
            pass
        self._status(
            f"Atom Create · {len(self._atom_draft.steps)} step(s) · Esc = save/exit · {atom_create_legend(phase=self._atom_create_phase)}",
            "info",
        )

    def _restore_menu_keymap(self) -> None:
        keymap = getattr(self, "_flight_deck_keymap", None)
        if keymap is None:
            return
        try:
            self.flight_deck.set_keymap(keymap)
        except Exception:
            pass
        self._sync_lco_console_deck_labels()
        self._sync_settings_deck_labels()

    def _refresh_atom_create_chrome(self) -> None:
        if self._deck_mode is not DeckMode.ATOM_CREATE:
            return
        self._install_atom_create_keymap()

    def _atom_add_lco_step(self, action: str) -> None:
        try:
            self._atom_draft.add_lco(action)
        except ValueError as exc:
            self._status(str(exc), "error")
            return
        self._atom_create_phase = AtomCreatePhase.CREATE
        self._refresh_atom_create_chrome()
        self._status(
            f"Added lco:{action} ({len(self._atom_draft.steps)} step(s)).",
            "ok",
        )

    def _atom_add_click_step(self) -> None:
        self._atom_draft.add_click()
        self._atom_create_phase = AtomCreatePhase.CREATE
        self._refresh_atom_create_chrome()
        self._status(
            f"Added click center ({len(self._atom_draft.steps)} step(s)).",
            "ok",
        )

    def _handle_atom_create_key(self, token: str) -> None:
        """Legacy flat-key path — accordion dispatch is preferred."""

        key = str(token or "").strip().upper()
        if not key:
            return
        step = draft_step_from_token(key)
        if step is None:
            self._status(f"Atom Create: {key} not a step key.", "info")
            return
        kind, payload = step
        if kind == "lco":
            self._atom_add_lco_step(payload)
        else:
            self._atom_add_click_step()

    def _try_save_atom_draft(self) -> bool:
        """Prompt for event id and persist. Returns True if saved or nothing to save."""

        draft = self._atom_draft
        if not draft.steps:
            return True
        name = self._ask_name("Save atom — event id", draft.event_id or "atom_new")
        if not name:
            self._status(
                "Atom not saved — needs persist path (event id). Draft discarded.",
                "warn",
            )
            return False
        draft.event_id = name
        draft.title = name.replace("_", " ")
        try:
            path = save_atom_draft(project_root() / "automations" / "events", draft)
        except ValueError as exc:
            self._status(f"Atom save blocked: {exc}", "warn")
            return False
        except OSError as exc:
            self._status(f"Atom save failed: {exc}", "error")
            return False
        draft.clear()
        self._reload_automations()
        self._status(f"Atom saved: {path.name}", "ok")
        self._shared_console.append(f"Atom Create saved {path.name}", "ok")
        return True

    def _host_molecule_automations(self, parent) -> None:
        if self.auto_panel is not None:
            try:
                self.auto_panel.pack_forget()
            except Exception:
                pass
        self.auto_panel = AutomationsPanel(
            parent,
            store=self.auto_store,
            on_reload=self._reload_automations,
            on_start=self._start_automations_selection,
            on_start_all_enabled=None,
            on_stop=self._stop_automations,
            on_walkthrough=self._start_collection_walkthrough,
            on_walkthrough_stop=self._stop_collection_walkthrough,
            on_run_collection=self._start_molecule,
            on_validate=self._validate_automations,
            on_dry_run=self._dry_run_selection,
            on_comment_event=self._comment_event,
            on_comment_collection=self._comment_collection,
            comments=self.comment_store,
            scroll=self.scroll_memory,
        )
        self.auto_panel.pack(fill="both", expand=True)
        # Shared console → docked ML console (one stream with LOL logs).
        try:
            self._shared_console.unsubscribe(self._fanout_shared_console_to_panel)
        except Exception:
            pass
        self._shared_console.subscribe(self._fanout_shared_console_to_panel)
        try:
            self._reload_taxonomy()
        except Exception:
            pass

    def _fanout_shared_console_to_panel(self, line) -> None:
        if self.auto_panel is None:
            return
        try:
            self.auto_panel.append_console(line.message, line.level)
        except Exception:
            pass

    def _register_molecule_lab_root(self, root) -> None:
        self._molecule_lab_root = root

    def _host_molecule_atom_pane(self, parent) -> None:
        from idle_lab.shell.tabs.molecule_lab import AtomLabPane, find_ml_root

        found = find_ml_root(parent)
        if found is not None:
            self._molecule_lab_root = found
        if self.atom_lab_pane is not None:
            try:
                self.atom_lab_pane.destroy()
            except Exception:
                pass
        self.atom_lab_pane = AtomLabPane(
            parent,
            get_library_rows=self._atom_library_rows,
            get_coverage_rows=self._lol_coverage_rows,
            on_refresh=self._reload_automations,
            on_seed_missing=self._seed_lol_wrappers,
            on_run_atom=self._run_atom_once_by_id,
            on_create_stub=self._create_lol_stub_atom,
        )
        self.atom_lab_pane.pack(fill="both", expand=True)

    def _goto_molecule_subtab(self) -> None:
        from idle_lab.shell.tabs.molecule_lab import select_ml_subtab

        if not self._is_lab_visible():
            self._show_idle_lab_surface()
        try:
            self.tabs.set("Molecule Lab")
        except Exception:
            pass
        self._current_tab = "Molecule Lab"
        self.settings.last_tab = "Molecule Lab"
        self._save_settings()
        target = self._molecule_lab_root or self.atom_lab_pane
        ok = bool(target is not None and select_ml_subtab(target, "Molecule"))
        if ok:
            self._status("Molecule Lab → Molecule (compose / run).", "ok")
        else:
            self._status("Molecule Lab → Molecule jump failed (sub-tab not found).", "warn")

    def _atom_library_rows(self):
        from idle_lab.automations.lol_coverage import classify_library

        return classify_library(self.auto_store)

    def _lol_coverage_rows(self):
        from idle_lab.automations.lol_coverage import build_coverage_rows

        return build_coverage_rows(self.auto_store)

    def _seed_lol_wrappers(self) -> None:
        from idle_lab.automations.lol_coverage import seed_missing_wrappers

        events_dir = project_root() / "automations" / "events"
        written = seed_missing_wrappers(self.auto_store, events_dir)
        self._reload_automations()
        if written:
            names = ", ".join(p.stem for p in written)
            self._status(f"Seeded LOL wrappers: {names}", "ok")
            self._shared_console.append(f"Seeded LOL wrappers: {names}", "ok")
        else:
            self._status("LOL coverage already complete — nothing to seed.", "info")
        if self.atom_lab_pane is not None:
            try:
                self.atom_lab_pane.refresh()
            except Exception:
                pass

    def _create_lol_stub_atom(self, actuation: str) -> None:
        from idle_lab.automations.lol_coverage import write_stub_atom

        path = write_stub_atom(project_root() / "automations" / "events", actuation)
        self._reload_automations()
        self._status(f"Created stub atom {path.name}", "ok")
        self._shared_console.append(f"Created stub atom {path.name}", "ok")
        if self.atom_lab_pane is not None:
            try:
                self.atom_lab_pane.refresh()
            except Exception:
                pass

    def _run_atom_once_by_id(self, event_id: str) -> None:
        event = self.auto_store.events.get(event_id)
        if event is None:
            self._status(f"Atom not found: {event_id}", "error")
            return
        self._start_automations_selection(event, None)

    def _host_observation_user(self, parent) -> None:
        self.screen_map_panel = ScreenMapPanel(
            parent,
            on_start_batch=self._start_observation,
            on_end_batch=lambda: self._stop_observation(reason="operator", prompt_rename=False),
            on_mark=None,
            on_open_folder=self._open_screen_map_folder,
            on_refresh_catalog=self._refresh_screen_map_catalog,
            on_view_shot=self._view_screen_map_shot,
            on_view_batch=self._view_screen_map_batch,
            on_comment_batch=self._comment_screen_map_batch,
            on_comment_shot=self._comment_screen_map_shot,
            comments=self.comment_store,
            scroll=self.scroll_memory,
        )
        self.screen_map_panel.pack(fill="both", expand=True)
        self._refresh_screen_map_catalog()

    def _host_observation_ai(self, parent) -> None:
        self.ai_batch_panel = AiBatchPanel(
            parent,
            store=self.ai_batch_store,
            scroll=self.scroll_memory,
            screen_maps_root=self.screen_maps_root,
            on_reload=self._reload_ai_batches,
            on_new_batch=self._new_ai_batch,
            on_open_folder=self._open_ai_batch_folder,
            on_view_screenshots=self._view_ai_batch_screenshots,
            on_link_screen_map=self._link_ai_batch_screen_map,
            on_mark_request=self._mark_ai_request,
            on_add_feedback=None,
            on_open_screen_map_batch=self._goto_screen_map_batch,
            on_snapshot_event=self._snapshot_event_into_ai_batch,
            on_start_run=self._start_ai_batch_run,
            on_stop_run=self._stop_ai_batch_run,
            on_export_packet=self._export_prompt_packet,
            on_comment_batch=self._comment_mission,
            on_comment_request=self._comment_mission_request,
            comments=self.comment_store,
        )
        self.ai_batch_panel.pack(fill="both", expand=True)
        try:
            self.ai_batch_panel.refresh_list()
        except Exception:
            pass

    def _deactivate_from_idle_lab(self) -> None:
        """Chrome Deactivate ≡ Deck Deactivate (one stop model)."""

        self._exit_deck_mode(quiet=True)
        self._ensure_deck_only_surface()
        self._stop_all()
        self._enter_inactive(resume=True)
        self._update_flight_deck_lab_button()

    def _open_settings_from_lab(self) -> None:
        """Idle Lab Settings → same boot-preference panel as Deck S."""

        self._ensure_deck_only_surface()
        if self._shell_phase is ShellPhase.INACTIVE:
            self._activate_flight_deck()
        self._enter_deck_mode(DeckMode.SETTINGS)

    def _enter_deck_mode(self, mode: DeckMode) -> None:
        """Abandon menu letters; open floating Lab skeleton when needed."""

        if mode is DeckMode.MENU:
            self._exit_deck_mode()
            return
        self._ensure_deck_only_surface()
        if self._shell_phase is not ShellPhase.ACTIVE:
            self._activate_flight_deck()
        self._close_floating_lab()
        self._deck_mode = mode
        key = vk_label(self._flight_deck_expand_vk_for_anchor())
        prompt = mode_prompt(mode, activate_key=key)
        legend = mode_legend(mode)
        self.hooks.state.deck_mode_active = True

        if mode is DeckMode.ATOM_CREATE:
            # Keep real FD accordion chrome with a create keymap (Esc still peels).
            if not self._atom_draft.steps:
                self._atom_draft = AtomDraft()
            self._atom_create_phase = AtomCreatePhase.CREATE
            self._install_atom_create_keymap()
            self.hooks.state.atom_create_active = True
            self._sync_shell_hook_flags()
            self._status(f"Deck mode: {mode_display_name(mode)}.", "info")
            return

        self.flight_deck.collapse_menu()
        self.flight_deck.set_deck_lab_mode(True, prompt=prompt, legend=legend)
        self._sync_shell_hook_flags()

        if mode is DeckMode.MOLECULE_LAB:
            # Floating composer opened by caller / Deck M dispatch.
            pass
        elif mode is DeckMode.OBSERVATION_LAB:
            self._open_floating_lab(
                title="Idle Lab · Observation Lab",
                heading="Observation Lab",
                blurb="Review/capture lives in Idle Lab → Observation Lab. This float is a lightweight entry stub.",
            )
        elif mode is DeckMode.LOL:
            # Live enter is the product surface — no extra float.
            pass
        elif mode is DeckMode.SETTINGS:
            self._open_settings_float()
        self._status(f"Deck mode: {mode_display_name(mode)}.", "info")

    def _exit_deck_mode(self, *, quiet: bool = False) -> None:
        leaving = self._deck_mode
        if leaving is DeckMode.ATOM_CREATE:
            self._try_save_atom_draft()
        self._close_floating_lab()
        self._deck_mode = DeckMode.MENU
        self._atom_create_phase = AtomCreatePhase.IDLE
        try:
            self.flight_deck.set_deck_lab_mode(False)
        except Exception:
            pass
        self.hooks.state.deck_mode_active = False
        self.hooks.state.atom_create_active = False
        self._restore_menu_keymap()
        if self._shell_phase is ShellPhase.ACTIVE and self._is_anchored() and not self._is_lab_visible():
            try:
                self.flight_deck.set_expanded(True)
            except Exception:
                pass
        self._sync_shell_hook_flags()
        if not quiet:
            self._status("Deck menu.", "info")

    def _close_floating_lab(self) -> None:
        win = self._floating_lab
        self._floating_lab = None
        settings = self._settings_window
        self._settings_window = None
        for target in (win, settings):
            if target is None:
                continue
            try:
                target.destroy()
            except Exception:
                pass

    def _open_floating_lab(self, *, title: str, heading: str, blurb: str) -> None:
        self._close_floating_lab()

        def on_close() -> None:
            self._exit_deck_mode()

        self._floating_lab = FloatingLabWindow(
            self,
            title=title,
            heading=heading,
            blurb=blurb,
            on_close=on_close,
        )
        self._floating_lab.focus_float()

    def _open_settings_float(self) -> None:
        self._close_floating_lab()
        win = ctk.CTkToplevel(self)
        win.title("Idle Lab · Settings")
        win.geometry("480x320")
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", self._exit_deck_mode)

        def on_boot(value: str) -> None:
            self.settings.boot_surface = normalize_boot_surface(value)
            self._save_settings()
            self._status(
                f"Boot surface → {BOOT_IDLE_LAB if self.settings.boot_surface == BOOT_IDLE_LAB else 'flight_deck'}.",
                "ok",
            )

        build_settings_body(
            win,
            boot_surface=self.settings.boot_surface,
            expand_vk=int(self.settings.flight_deck_expand_vk or DEFAULT_EXPAND_VK),
            on_boot_change=on_boot,
            on_begin_remap=self._begin_flight_deck_remap,
        )
        self._settings_window = win
        try:
            win.lift()
            win.focus_force()
        except Exception:
            pass

    def _open_flight_deck_from_lab(self) -> None:
        """Idle Lab chrome → exclusive Flight Deck (closes Idle Lab)."""

        self._switch_to_flight_deck_surface(activate=False)
        self._status("Flight Deck open — Idle Lab closed.", "ok")

    def _toggle_flight_deck_from_lab(self) -> None:
        # Compatibility alias — chrome button is exclusive Open Flight Deck.
        self._open_flight_deck_from_lab()

    def _update_flight_deck_lab_button(self) -> None:
        if getattr(self, "flight_deck_button", None) is None:
            return
        self.flight_deck_button.configure(text="Open Flight Deck")
        if getattr(self, "flight_deck_button_hint", None) is not None:
            try:
                self.flight_deck_button_hint.configure(text="(closes Idle Lab)")
            except Exception:
                pass

    def _begin_flight_deck_remap(self) -> None:
        status, _hwnd, _rect, _title = self.anchor_target.snapshot()
        if status not in ("ok", "minimized", "closed"):
            self._status("Anchor a window first so the expand key can be saved per anchor.", "warn")
        self.hooks.state.flight_deck_remap = True
        self._status("Press the new Activate key (Esc cancels). Saved for this anchor when set.", "warn")

    def _apply_flight_deck_remap(self, vk: int) -> None:
        vk = int(vk)
        if vk in (0x1B,):  # Esc handled elsewhere
            return
        status, _hwnd, _rect, title = self.anchor_target.snapshot()
        self.settings.flight_deck_expand_vk = vk
        if status in ("ok", "minimized", "closed") and title:
            by_anchor = dict(self.settings.flight_deck_expand_by_anchor or {})
            by_anchor[title] = vk
            self.settings.flight_deck_expand_by_anchor = by_anchor
            self._status(f"Expand key → {vk_label(vk)} for anchor “{title}”.", "ok")
        else:
            self._status(f"Expand key → {vk_label(vk)} (global default).", "ok")
        self._save_settings()
        self._sync_flight_deck_expand_vk()
        self._sync_settings_deck_labels()

    def _dispatch_flight_deck_action(self, action: dict) -> None:
        kind = str(action.get("type") or "")
        path = str(action.get("_path") or action.get("_label") or kind)
        try:
            if kind == "open_lol":
                self._ensure_deck_only_surface()
                self._enter_deck_mode(DeckMode.LOL)
                try:
                    self._enter_live_control()
                except Exception as exc:
                    self._status(f"Live Overlay Lab: {exc}", "warn")
            elif kind == "open_molecule_lab":
                self._enter_deck_mode(DeckMode.MOLECULE_LAB)
                self._open_molecule_composer()
            elif kind == "open_atom_lab":
                self._open_atom_create_from_lab()
            elif kind == "open_observation_lab":
                self._enter_deck_mode(DeckMode.OBSERVATION_LAB)
                # Floating Observation Lab skeleton already opens; panel is Idle Lab-native.
            elif kind == "open_idle_lab":
                self._exit_deck_mode(quiet=True)
                self._show_idle_lab_surface()
                self._status("Idle Lab open — Flight Deck closed.", "ok")
            elif kind == "open_settings":
                self._enter_deck_mode(DeckMode.SETTINGS)
            elif kind == "remap_activate_key":
                self._begin_flight_deck_remap()
            elif kind == "cycle_boot_surface":
                self._cycle_boot_surface()
            elif kind == "atom_add_lco":
                self._atom_add_lco_step(str(action.get("action") or ""))
            elif kind == "atom_add_click":
                self._atom_add_click_step()
            elif kind == "atom_edit_enter":
                self._atom_create_phase = AtomCreatePhase.EDIT
                self._status("Atom Edit — reorder/select not wired yet.", "warn")
            elif kind == "play_preset":
                self._ensure_deck_only_surface()
                self._flight_deck_play_preset(str(action["preset"]), path=path)
            elif kind == "start_event":
                self._ensure_deck_only_surface()
                self._flight_deck_start_event(str(action["event"]), path=path)
            elif kind == "start_collection":
                self._ensure_deck_only_surface()
                self._flight_deck_start_collection(str(action["collection"]), path=path)
            elif kind == "start_enabled_loops":
                self._status("Start all enabled — cut from Flight Deck.", "warn")
            elif kind in {"observation_start", "observe_start"}:
                self._ensure_deck_only_surface()
                title = str(action.get("title") or "").strip() or None
                self._start_observation(title=title)
            elif kind in {"observation_mark", "observe_shot"}:
                self._status("Mark — cut from Flight Deck.", "warn")
            elif kind in {"observation_end", "observe_end"}:
                self._stop_observation(reason="operator", prompt_rename=False)
            elif kind == "live_control_enter":
                self._ensure_deck_only_surface()
                self._enter_live_control()
            elif kind == "live_control_enter_troubleshoot":
                self._ensure_deck_only_surface()
                self._enter_live_control_troubleshoot()
            elif kind == "live_control_exit":
                self._exit_live_control(reason="operator")
            elif kind == "live_control_toggle":
                if self.live_control.active:
                    self._exit_live_control(reason="toggle")
                else:
                    self._ensure_deck_only_surface()
                    self._enter_live_control()
            elif kind == "live_control_console_toggle":
                self._toggle_lco_console_setting()
            elif kind == "live_control_console_verbosity":
                self._cycle_lco_console_verbosity()
            elif kind == "molecule_composer_open":
                self._enter_deck_mode(DeckMode.MOLECULE_LAB)
                self._open_molecule_composer()
            else:
                self._status(f"Flight deck: unknown action type “{kind}”.", "error")
        except Exception as exc:
            self._status(f"Flight deck failed ({path}): {exc}", "error")

    def _live_control_anchor(self) -> tuple[str | None, int | None, object]:
        status, hwnd, rect, title = self.anchor_target.snapshot()
        if status != "ok":
            return None, None, None
        return title, hwnd, rect

    def _live_control_log(self, message: str, level: str = "info") -> None:
        self._status(message, level if level in STATUS_COLOR else "info")
        try:
            self._shared_console.append(message, level)
        except Exception:
            pass
        # Molecule Lab panel receives lines via SharedConsole subscription (no double-append).

    def _live_control_legend_changed(self, show_descriptors: bool) -> None:
        if getattr(self, "flight_deck", None) is None:
            return
        self.flight_deck.set_live_control_legend(bool(show_descriptors))

    def _live_control_toggle_token_changed(self, token: str | None) -> None:
        self.hooks.state.live_control_toggle_token = token

    def _live_control_pause_changed(self, paused: bool) -> None:
        self.hooks.state.live_control_paused = bool(paused)
        if getattr(self, "flight_deck", None) is None:
            return
        self.flight_deck.set_live_control_paused(bool(paused))

    def _lco_console_session_changed(self) -> None:
        """ConsoleSession may notify from OCR worker threads — never touch Tk here."""

        self._lco_console_dirty = True

    def _refresh_lco_console_window(self) -> None:
        self._lco_console_dirty = False
        window = getattr(self, "_lco_console_window", None)
        if window is None:
            return
        try:
            if window.winfo_exists():
                window.schedule_refresh()
        except Exception:
            self._lco_console_window = None

    def _sync_lco_console_deck_labels(self) -> None:
        """Keep L→2 / L→3 labels honest about ON/OFF and verbosity."""

        if self._deck_mode is DeckMode.ATOM_CREATE:
            return
        keymap = getattr(self, "_flight_deck_keymap", None)
        if keymap is None:
            return
        from idle_lab.flight_deck.keys import normalize_menu_key

        enabled = bool(self.settings.lco_console_enabled)
        verbosity = str(self.settings.lco_console_verbosity or "results")
        for root in keymap.roots:
            if normalize_menu_key(root.key) != "L":
                continue
            for child in root.children:
                key = normalize_menu_key(child.key)
                if key == "2":
                    state = "ON" if enabled else "OFF"
                    child.label = f"Toggle Console ({state})"
                elif key == "3":
                    child.label = f"Console Verbosity ({verbosity})"
            break
        if getattr(self, "flight_deck", None) is not None:
            try:
                self.flight_deck.set_keymap(keymap)
            except Exception:
                pass

    def _sync_settings_deck_labels(self) -> None:
        """Keep S→2 / S→3 labels current for Activate key + boot surface."""

        if self._deck_mode is DeckMode.ATOM_CREATE:
            return
        keymap = getattr(self, "_flight_deck_keymap", None)
        if keymap is None:
            return
        from idle_lab.flight_deck.keys import normalize_menu_key

        boot = normalize_boot_surface(self.settings.boot_surface)
        boot_label = "Idle Lab" if boot == BOOT_IDLE_LAB else "Flight Deck"
        key_label = vk_label(int(self.settings.flight_deck_expand_vk or DEFAULT_EXPAND_VK))
        for root in keymap.roots:
            if normalize_menu_key(root.key) != "S":
                continue
            for child in root.children:
                key = normalize_menu_key(child.key)
                if key == "2":
                    child.label = f"Set Deactivate Key ({key_label})"
                elif key == "3":
                    child.label = f"Boot Preferences ({boot_label})"
            break
        if getattr(self, "flight_deck", None) is not None:
            try:
                self.flight_deck.set_keymap(keymap)
            except Exception:
                pass

    def _cycle_boot_surface(self) -> None:
        current = normalize_boot_surface(self.settings.boot_surface)
        nxt = BOOT_FLIGHT_DECK if current == BOOT_IDLE_LAB else BOOT_IDLE_LAB
        self.settings.boot_surface = nxt
        self._save_settings()
        self._sync_settings_deck_labels()
        label = "Idle Lab" if nxt == BOOT_IDLE_LAB else "Flight Deck"
        self._status(f"Boot Preferences → {label} (applies on Restart).", "ok")

    def _persist_lco_console_settings(self) -> None:
        self.settings.lco_console_enabled = bool(self.live_control.console.enabled)
        self.settings.lco_console_verbosity = str(self.live_control.console.verbosity or "results")
        self._save_settings()
        self._sync_lco_console_deck_labels()

    def _open_lco_console_window(self) -> None:
        """Show the console window. Only call while LCO is active (or becoming active)."""

        if not self.settings.lco_console_enabled:
            return
        existing = getattr(self, "_lco_console_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.refresh()
                    return
            except Exception:
                self._lco_console_window = None

        from idle_lab.live_control.console_window import LcoConsoleWindow

        def _on_close() -> None:
            # Closing the window turns the preference off for subsequent LCO enters.
            self._set_lco_console_enabled(False, reason="window-close")

        def _on_geometry(value: str) -> None:
            self.settings.lco_console_geometry = value
            self._save_settings()

        self._lco_console_window = LcoConsoleWindow(
            self,
            console=self.live_control.console,
            on_close=_on_close,
            on_geometry=_on_geometry,
            geometry=self.settings.lco_console_geometry,
        )

    def _close_lco_console_window(self) -> None:
        window = getattr(self, "_lco_console_window", None)
        self._lco_console_window = None
        if window is None:
            return
        try:
            if window.winfo_exists():
                window.destroy_window()
        except Exception:
            pass

    def _set_lco_console_enabled(self, enabled: bool, *, reason: str = "toggle") -> None:
        from idle_lab.live_control.console import normalize_verbosity

        want = bool(enabled)
        verbosity = normalize_verbosity(self.settings.lco_console_verbosity)
        # Preference flip only — the window opens when LCO enters, not from the deck alone.
        if want:
            self.live_control.console.configure(enabled=True, verbosity=verbosity)
            if self.live_control.active:
                self.live_control.console.set_enabled(True)
                self._open_lco_console_window()
        else:
            if self.live_control.console.enabled:
                self.live_control.console.set_enabled(False)
            else:
                self.live_control.console.configure(enabled=False, verbosity=verbosity)
            self._close_lco_console_window()
        self._persist_lco_console_settings()
        state = "ON" if want else "OFF"
        msg = f"Toggle LCO Console ({state})"
        if want:
            where = " · opens with LCO" if not self.live_control.active else ""
            msg = f"{msg} · Console Verbosity ({verbosity}){where}"
        self._status(msg, "ok" if want else "warn")

    def _toggle_lco_console_setting(self) -> None:
        """Flight-deck U→3: flip persisted console preference (window follows LCO sessions)."""

        self._set_lco_console_enabled(not bool(self.settings.lco_console_enabled), reason="toggle")

    def _cycle_lco_console_verbosity(self) -> None:
        """Flight-deck U→4: cycle events → results → process."""

        if not self.settings.lco_console_enabled:
            self._status("Toggle Console (OFF) — enable with L→2 before changing verbosity.", "warn")
            return
        level = self.live_control.console.cycle_verbosity()
        self._persist_lco_console_settings()
        self._refresh_lco_console_window()
        self._status(f"Toggle LCO Console (ON) · Console Verbosity ({level})", "ok")

    def _live_control_run_event_once(self, event_id: str) -> None:
        if self.auto_runtime.is_running or self.auto_runtime.collection_running:
            raise LiveControlError("Stop Loops before Stat collect from Live Control.")
        if self.player.is_active or self.ai_batch_runner.is_running:
            raise LiveControlError("Stop Bench/Mission before Stat collect from Live Control.")
        self.auto_runtime.run_event_once(event_id)

    def _live_control_evidence(
        self,
        *,
        action: str,
        phase: str,
        detail: str = "",
        meta: dict | None = None,
        capture: bool = True,
    ) -> None:
        if not self.observation.active:
            return
        status, _hwnd, rect, title = self.anchor_target.snapshot()
        try:
            self.observation.note_live_control(
                action=action,
                phase=phase,
                detail=detail,
                meta=meta or {},
                anchor_title=title if status == "ok" else None,
                anchor_rect=rect if status == "ok" else None,
                capture=capture and status == "ok",
            )
        except ObservationError as exc:
            self._status(f"Live Control evidence: {exc}", "warn")

    def _arm_live_control_hooks(self) -> None:
        """Stop accordion listening immediately — before enter() does capture/OCR work."""

        self.hooks.state.live_control_active = True
        self.hooks.state.live_control_paused = False
        self.hooks.state.live_control_cancel.clear()
        try:
            self.flight_deck.collapse_menu()
        except Exception:
            pass
        self._sync_shell_hook_flags()

    def _enter_live_control(self) -> None:
        if self.observation.active or self.screen_map.active:
            self._status("Stop Observation / Screen Map before Live Control Overlay.", "warn")
            return
        if self.recorder.active or self.player.is_active:
            self._status("Stop Bench recording/playback before Live Control Overlay.", "warn")
            return
        if self.walkthrough is not None and self.walkthrough.active:
            self._status("Stop Walkthrough before Live Control Overlay.", "warn")
            return
        if self.live_control.active:
            self._status("Live Control Overlay already on.", "info")
            return
        # Gate U/digit accordion now so repeated 1s don't pile up while enter boots.
        self._arm_live_control_hooks()
        try:
            self.live_control.enter(evidence=False)
            self.overlay.set_markers([], False)
            self._live_control_owns_observation = False
            self.flight_deck.set_live_control_active(True)
            self._sync_shell_hook_flags()
            if self.settings.lco_console_enabled:
                self._open_lco_console_window()
        except LiveControlError as exc:
            self.hooks.state.live_control_active = False
            self.hooks.state.live_control_paused = False
            self.flight_deck.set_live_control_active(False)
            self._sync_shell_hook_flags()
            self._status(str(exc), "error")

    def _enter_live_control_troubleshoot(self) -> None:
        """Live Control + Observation: playbook hotkeys with framed evidence for each action."""

        if self.live_control.active or self.hooks.state.live_control_active:
            self._status("Exit Live Control first, then U → 2 for Troubleshoot.", "warn")
            return
        if self.observation.active or self.screen_map.active:
            self._status("Stop Observation / Screen Map before Troubleshoot Live Control.", "warn")
            return
        if self.recorder.active or self.player.is_active:
            self._status("Stop Bench recording/playback before Troubleshoot Live Control.", "warn")
            return
        if self.walkthrough is not None and self.walkthrough.active:
            self._status("Stop Walkthrough before Troubleshoot Live Control.", "warn")
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self._start_observation(title=f"live-control-troubleshoot-{stamp}")
        if not self.observation.active:
            return
        self._arm_live_control_hooks()
        try:
            self.live_control.enter(evidence=True)
            self.overlay.set_markers([], False)
            self._live_control_owns_observation = True
            self.flight_deck.set_live_control_active(True)
            self._sync_shell_hook_flags()
            if self.settings.lco_console_enabled:
                self._open_lco_console_window()
            self._status(
                f"Live Control Troubleshoot ON · evidence → {self.observation.folder.name if self.observation.folder else '?'}",
                "run",
            )
        except LiveControlError as exc:
            self._live_control_owns_observation = False
            self.hooks.state.live_control_active = False
            self.hooks.state.live_control_paused = False
            self.flight_deck.set_live_control_active(False)
            self._close_lco_console_window()
            self._sync_shell_hook_flags()
            self._stop_observation(reason="live-control-enter-failed", prompt_rename=False)
            self._status(str(exc), "error")

    def _exit_live_control(self, *, reason: str = "operator") -> None:
        if not self.live_control.active:
            return
        self.live_control.interrupt()
        self.live_control.exit(reason=reason)
        self.hooks.state.live_control_active = False
        self.hooks.state.live_control_paused = False
        self.hooks.state.live_control_toggle_token = None
        self.flight_deck.set_live_control_active(False)
        self._sync_shell_hook_flags()
        self._close_lco_console_window()
        if self._live_control_owns_observation:
            self._live_control_owns_observation = False
            if self.observation.active or self.screen_map.active:
                self._stop_observation(reason="live-control-exit", prompt_rename=False)

    def _flight_deck_play_preset(self, name: str, *, path: str) -> None:
        if self.recorder.active or self.player.is_active:
            self._status("Stop Bench recording/playback first.", "warn")
            return
        if self.auto_runtime.is_running or self.auto_runtime.collection_running:
            self._status("Stop Loops before a one-shot preset (single mouse runway).", "warn")
            return
        if self.ai_batch_runner.is_running:
            self._status("Stop the Mission before a one-shot preset.", "warn")
            return
        preset = next((item for item in self.store.presets if item.name == name), None)
        if preset is None:
            self._status(f"Preset not found: {name}", "error")
            return
        if not preset.points:
            self._status(f"Preset has no points: {name}", "error")
            return
        status, hwnd, _rect, _title = self.anchor_target.snapshot()
        if status != "ok" or not hwnd:
            self._status("Anchor a window before playing a preset.", "error")
            return
        self.hooks.state.playback = True
        self._sync_controls()
        self.player.start(
            preset.points,
            loop=False,
            loop_count=1,
            method=self.settings.click_method,
            focus=self.settings.focus_before_run,
            restore_cursor=self.settings.restore_cursor,
            countdown=self.settings.countdown_seconds,
            hwnd=hwnd,
            snapshot=self.anchor_target.snapshot,
            humanize=self._humanize_profile(),
        )
        self._status(f"Flight deck · {path}", "run")

    def _flight_deck_start_event(self, event_id: str, *, path: str) -> None:
        event = self.auto_store.events.get(event_id)
        if event is None:
            self._status(f"Atom not found: {event_id}", "error")
            return
        self._start_automations_selection(event, None)
        if self.auto_runtime.collection_running or self.auto_runtime.is_running:
            self._status(f"Flight deck · {path}", "run")

    def _flight_deck_start_collection(self, collection_id: str, *, path: str) -> None:
        collection = self.auto_store.collections.get(collection_id)
        if collection is None:
            self._status(f"Molecule not found: {collection_id}", "error")
            return
        self._start_molecule(collection)
        if self.auto_runtime.collection_running or self.auto_runtime.is_running:
            self._status(f"Flight deck · {path}", "run")

    def _molecule_lab_is_open(self) -> bool:
        win = getattr(self, "_molecule_composer", None)
        if win is None:
            return False
        try:
            return bool(win.winfo_exists())
        except Exception:
            return False

    def _set_molecule_lab_deck_mode(self, *, active: bool, close_confirm: bool = False) -> None:
        self._molecule_lab_close_confirm = bool(active and close_confirm)
        try:
            self.flight_deck.set_molecule_lab_active(active, close_confirm=close_confirm)
        except Exception:
            pass
        self._sync_shell_hook_flags()

    def _confirm_close_molecule_lab(self) -> None:
        """Immediate close — no Esc confirm peel."""

        win = getattr(self, "_molecule_composer", None)
        self._molecule_composer = None
        self._set_molecule_lab_deck_mode(active=False)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        self._status("Molecule Lab closed.", "info")

    def _lco_run_molecule(self, collection_id: str) -> None:
        collection = self.auto_store.collections.get(collection_id)
        if collection is None:
            # Lab may have enabled a draft that isn't loaded yet — soft reload once.
            try:
                self._reload_automations()
            except Exception:
                pass
            collection = self.auto_store.collections.get(collection_id)
        if collection is None:
            self._status(f"LCO molecule not found: {collection_id}", "error")
            return
        if self.live_control.active:
            # Free the shared LCO runway so atom steps aren't "busy" behind a spam hold.
            try:
                self.live_control.interrupt()
                self.hooks.state.live_control_cancel.clear()
            except Exception:
                pass
        self._status(f"LCO molecule [{collection.title}] starting…", "run")
        self._start_molecule(collection, lco_pack=True)

    def _open_molecule_composer(self) -> None:
        """Flight deck → Molecules → Molecule Lab: browse/edit/compose molecules."""

        existing = getattr(self, "_molecule_composer", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    self._set_molecule_lab_deck_mode(active=True)
                    # Deck chrome rebuild can steal focus — refocus Lab after.
                    try:
                        existing._orphan_and_focus()
                    except Exception:
                        existing.lift()
                        existing.focus_force()
                    self._status("Molecule Lab already open.", "info")
                    return
            except Exception:
                self._molecule_composer = None

        from idle_lab.composer.window import MoleculeLabWindow

        def _on_exported(collection_id: str) -> None:
            self._reload_automations()
            if self.live_control.active:
                self.live_control.refresh_molecule_marks()
            self._status(f"Molecule Lab saved “{collection_id}”.", "ok")

        def _on_lco_toggle() -> None:
            if self.live_control.active:
                self.live_control.refresh_molecule_marks()

        def _on_close() -> None:
            self._molecule_composer = None
            self._set_molecule_lab_deck_mode(active=False)

        self._molecule_composer = MoleculeLabWindow(
            self,
            automations_root=project_root() / "automations",
            project_root_path=project_root(),
            on_exported=_on_exported,
            on_status=lambda msg, level="info": self._status(msg, level),
            on_lco_changed=_on_lco_toggle,
            on_close=_on_close,
        )
        self._set_molecule_lab_deck_mode(active=True)
        # Render happens after construct; steal focus again so entries can type.
        try:
            self._molecule_composer._orphan_and_focus()
            self.after(80, self._molecule_composer._orphan_and_focus)
            self.after(200, self._molecule_composer._orphan_and_focus)
        except Exception:
            pass
        self._status(
            "Molecule Lab open — type freely; deck hotkeys paused (Esc still closes).",
            "ok",
        )

    def _start_observation(self, title: str | None = None) -> None:
        if self.observation.active or self.screen_map.active:
            self._status("An observation is already active — Mark or Stop.", "warn")
            return
        if self.recorder.active or self.player.is_active:
            self._status("Finish Bench recording/playback before Observe.", "warn")
            return
        if self.auto_runtime.is_running or self.auto_runtime.collection_running:
            self._status("Stop Loops before starting an observation.", "warn")
            return
        if self.ai_batch_runner.is_running:
            self._status("Stop the Mission before starting an observation.", "warn")
            return
        status, _hwnd, rect, window_title = self.anchor_target.snapshot()
        if status != "ok" or rect is None:
            self._status("Anchor a window before Observe.", "error")
            return
        human = (title or "").strip() or auto_observation_title()
        try:
            batch = self.observation.start(
                self.screen_maps_root,
                title=human,
                anchor_title=window_title,
                anchor_rect=rect,
            )
            self.screen_map.start(batch)
        except (ObservationError, ScreenMapError, OSError) as exc:
            if self.observation.active:
                try:
                    self.observation.stop(reason="error")
                except Exception:
                    pass
            self._status(str(exc), "error")
            return
        self.hooks.state.observation_active = True
        self.hooks.state.screenshot_mode = False
        self.hooks.state.title_dialog_open = False
        self.hooks.state.screenshot_busy = False
        self._screen_map_busy = False
        self._refresh_screen_map_panel()
        self._refresh_screen_map_catalog()
        self._update_activity()
        self._status(f"Observation ON · {batch.folder.name} — play normally; Esc stops.", "run")

    def _mark_observation(self) -> None:
        if not self.observation.active:
            self._status("Start an observation first (O→1).", "warn")
            return
        status, _hwnd, rect, window_title = self.anchor_target.snapshot()
        try:
            self.observation.mark(anchor_title=window_title, anchor_rect=rect if status == "ok" else None)
        except ObservationError as exc:
            self._status(str(exc), "error")
            return
        self._status("Observation mark queued.", "ok")

    def _stop_observation(self, *, reason: str = "operator", prompt_rename: bool = False) -> None:
        if not self.observation.active and not self.screen_map.active:
            self._status("No observation is active.", "warn")
            return
        if self._live_control_owns_observation:
            self._live_control_owns_observation = False
            if self.live_control.active:
                self.live_control.evidence = False
        summary = None
        if self.observation.active:
            summary = self.observation.stop(reason=reason)
        if self.screen_map.active:
            self.screen_map.end()
        self.hooks.state.observation_active = False
        self.hooks.state.screenshot_mode = False
        self._refresh_screen_map_panel()
        self._refresh_screen_map_catalog()
        self._update_activity()
        if summary is None:
            self._status("Observation stopped.", "warn")
            return
        self._status(
            f"Observation finished: {summary.shot_count} shot(s), {summary.event_count} events · {summary.folder.name}",
            "ok",
        )
        if prompt_rename and reason == "operator":
            self._maybe_rename_observation(summary.folder, summary.title)

    def _maybe_rename_observation(self, folder, current_title: str) -> None:
        rename = messagebox.askyesno(
            "Rename observation?",
            f"Rename this observation?\n\nCurrent title:\n“{current_title}”\n\nYes = rename, No = keep.",
            parent=self,
        )
        if not rename:
            return
        new_title = self._ask_name("Rename observation", current_title)
        if not new_title:
            return
        try:
            # Controller still holds last folder path after stop.
            self.observation.folder = folder
            renamed = self.observation.rename(new_title)
        except ObservationError as exc:
            self._status(str(exc), "error")
            return
        except OSError as exc:
            self._status(f"Could not rename observation: {exc}", "error")
            return
        self._refresh_screen_map_catalog()
        if self.screen_map_panel is not None:
            self.screen_map_panel.focus_batch(renamed.name)
        self._status(f"Observation renamed: {renamed.name}", "ok")

    def _observation_anchor(self):
        status, _hwnd, rect, window_title = self.anchor_target.snapshot()
        if status != "ok":
            return window_title, None
        return window_title, rect

    def _drain_observation_ui(self) -> None:
        saw_shot = False
        for event in self.observation.drain_ui():
            kind = event[0]
            if kind == "error":
                self._status(str(event[1]), "error")
            elif kind == "shot":
                saw_shot = True
            elif kind == "ended":
                self._refresh_screen_map_panel()
                self._refresh_screen_map_catalog()
        if saw_shot:
            now = time.perf_counter()
            # Spam-safe: panel refresh at most ~3 Hz while recording.
            if now - self._observation_ui_refresh_at >= 0.35:
                self._observation_ui_refresh_at = now
                self._refresh_screen_map_panel()

    def _sync_flight_deck_run_state(self) -> None:
        running = bool(
            self.player.is_active
            or self.auto_runtime.is_running
            or self.auto_runtime.collection_running
            or self.ai_batch_runner.is_running
        )
        paused = bool(self.player.is_active and self.player.paused)
        # Prefer the same wording as the Activity chip, trimmed for the deck.
        status = self._activity_text().replace("Activity: ", "")
        if paused:
            status = f"Paused · {status}"
        elif running:
            status = f"Running · {status}"
        self.flight_deck.set_run_state(running=running, paused=paused, status=status)
        self.hooks.state.flight_deck_expanded = bool(self.flight_deck.expanded)
        self.hooks.state.flight_deck_open = self._flight_deck_is_visible()

    def _maybe_auto_show_flight_deck(self, status: str, rect) -> None:
        # Activate model: deck stays visible; poller only syncs flags + onscreen.
        self.hooks.state.flight_deck_expand_armed = True
        if self._shell_phase is ShellPhase.ACTIVE:
            anchored = status in ("ok", "minimized")
            self.flight_deck.set_anchored(anchored)
            if anchored and not self.flight_deck.expanded:
                self.flight_deck.set_expanded(True)
            elif not anchored and self._shell_phase is ShellPhase.ACTIVE:
                prompt = self._active_unanchored_prompt_text()
                self.flight_deck.set_shell_phase(
                    ShellPhase.ACTIVE,
                    prompt=prompt,
                    lab_visible=self._is_lab_visible(),
                    anchored=False,
                )
        self._sync_shell_hook_flags()
        if self._flight_deck_is_visible():
            self.flight_deck.ensure_onscreen()
        _ = rect

    def _edited_points(self) -> list[ClickPoint]:
        if self.recorder.active:
            return self.recorder.points
        if self.current is not None:
            return self.current.points
        return []

    def _place_markers(self, rect) -> None:
        # Bench point markers are the old autoclicker circles — hide during playback
        # and while Live Control owns the anchor surface.
        if self.player.is_active or self.live_control.active:
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

    def _clicker_ui_ready(self) -> bool:
        return self.preset_list is not None and getattr(self, "points_list", None) is not None

    def _rebuild_preset_list(self) -> None:
        if not self._clicker_ui_ready():
            return

        def rebuild() -> None:
            for child in self.preset_list.winfo_children():
                child.destroy()
            for preset in self.store.presets:
                selected = self.current is not None and preset.path == self.current.path
                row = ctk.CTkFrame(self.preset_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                button = ctk.CTkButton(
                    row,
                    text=preset.name,
                    anchor="w",
                    fg_color="#1f6aa5" if selected else "transparent",
                    command=lambda item=preset: self._select(item),
                )
                button.pack(side="left", fill="x", expand=True)
                stem = Path(preset.path).stem if preset.path else slug(preset.name)
                path = preset_comment_path(stem)
                make_comment_button(
                    row,
                    has_notes=self.comment_store.has(path),
                    command=lambda p=path, n=preset.name: self._open_object_comment(
                        f"Comment · preset · {n}", p
                    ),
                ).pack(side="right", padx=(4, 0))

        self.scroll_memory.around_rebuild("clicker.presets", rebuild)

    def _on_tab_changed(self) -> None:
        previous = self._current_tab
        self.scroll_memory.remember_prefix(self._tab_scroll_prefix(previous))
        self._current_tab = self.tabs.get()
        self.settings.last_tab = normalize_last_tab(self._current_tab)
        self._save_settings()
        prefix = self._tab_scroll_prefix(self._current_tab)
        self.after(80, lambda p=prefix: self.scroll_memory.restore_prefix(p))

    def _tab_scroll_prefix(self, tab_name: str) -> str:
        return {
            "Info": "info.",
            "Live Overlay Lab": "live_overlay_lab.",
            "Molecule Lab": "molecule_lab.",
            "Observation Lab": "observation_lab.",
            "LOL": "live_overlay_lab.",
            # Legacy mega-tab names
            "Bench": "clicker.",
            "Observe": "screen_map.",
            "Missions": "ai.",
            "Loops": "automations.",
            "Clicker": "clicker.",
            "Automations": "automations.",
            "Screen Map": "screen_map.",
            "AI Batches": "ai.",
        }.get(tab_name, tab_name.lower().replace(" ", "_") + ".")

    def _select(self, preset: Preset) -> None:
        if self.recorder.active:
            return
        self.current = preset
        if not self._clicker_ui_ready():
            return
        self._begin_load()
        try:
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
        if not self._clicker_ui_ready() or getattr(self, "forever_switch", None) is None:
            return
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
        if not self._clicker_ui_ready():
            return
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
                    # Legacy Space capture — observations use mouse tracking instead.
                    if not self.observation.active:
                        self._screen_map_space()
                elif kind == "observation_move":
                    if self.observation.active:
                        title, rect = self._observation_anchor()
                        self.observation.handle_move(int(event[1]), int(event[2]), anchor_title=title, anchor_rect=rect)
                elif kind == "observation_down":
                    if self.observation.active:
                        title, rect = self._observation_anchor()
                        self.observation.handle_button(
                            down=True,
                            button=str(event[1]),
                            x=int(event[2]),
                            y=int(event[3]),
                            anchor_title=title,
                            anchor_rect=rect,
                        )
                elif kind == "observation_up":
                    if self.observation.active:
                        title, rect = self._observation_anchor()
                        self.observation.handle_button(
                            down=False,
                            button=str(event[1]),
                            x=int(event[2]),
                            y=int(event[3]),
                            anchor_title=title,
                            anchor_rect=rect,
                        )
                elif kind == "observation_wheel":
                    if self.observation.active:
                        title, rect = self._observation_anchor()
                        self.observation.handle_wheel(
                            x=int(event[1]),
                            y=int(event[2]),
                            dy=int(event[3]),
                            anchor_title=title,
                            anchor_rect=rect,
                        )
                elif kind == "walkthrough_space":
                    self._walkthrough_space()
                elif kind == "walkthrough_key":
                    self._walkthrough_key(str(event[1]))
                elif kind == "escape":
                    if (
                        self._shell_phase in {ShellPhase.ACTIVE, ShellPhase.CLOSE_CONFIRM}
                        or self.live_control.active
                        or self.hooks.state.flight_deck_remap
                    ):
                        self._handle_shell_escape()
                    elif self._anchor_waiting or self.hooks.state.anchor_armed:
                        self._cancel_anchor_mode()
                    elif self.walkthrough is not None and self.walkthrough.active:
                        self._stop_collection_walkthrough()
                    elif self.recorder.active:
                        self._finish_recording()
                    elif self.observation.active:
                        self._stop_observation(reason="operator", prompt_rename=False)
                    elif (
                        self.player.is_active
                        or self.auto_runtime.is_running
                        or self.auto_runtime.collection_running
                        or self.ai_batch_runner.is_running
                    ):
                        # Same authority as the chrome button / F8 when a run owns the mouse.
                        self._stop_all()
                    elif self.screen_map.active and not self._screen_map_busy:
                        self._end_screen_map_batch()
                elif kind == "shell_enter":
                    self._handle_shell_enter()
                elif kind == "shell_a":
                    self._handle_shell_a()
                elif kind == "shell_i":
                    self._handle_shell_i()
                elif kind == "shell_r":
                    self._handle_shell_r()
                elif kind == "flight_deck_activate":
                    self._flight_deck_toggle_activate()
                elif kind == "live_control_key":
                    if self.live_control.active:
                        phase = str(event[2]) if len(event) > 2 else "down"
                        self.live_control.handle_key(str(event[1]), phase=phase)
                elif kind == "live_control_repeat":
                    if self.live_control.active:
                        self.live_control.continue_repeat(str(event[1]))
                elif kind == "live_control_dequeue":
                    if self.live_control.active:
                        self.live_control.drain_queue()
                elif kind == "live_control_done":
                    if self.live_control.active:
                        done_action = str(event[1]) if len(event) > 1 else ""
                        done_repeat = event[2] if len(event) > 2 else None
                        done_errors = event[3] if len(event) > 3 else ()
                        self.live_control.finish_action(
                            done_action,
                            repeat=str(done_repeat) if done_repeat is not None else None,
                            errors=tuple(done_errors) if done_errors else (),
                        )
                elif kind == "live_control_repaint":
                    if self.live_control.active:
                        self.live_control.repaint_now(str(event[1]) if len(event) > 1 else "")
                elif kind == "live_control_pause_toggle":
                    if self.live_control.active:
                        self.live_control.toggle_pause()
                elif kind == "live_control_scroll":
                    if self.live_control.active:
                        mode = str(event[2]) if len(event) > 2 else "step"
                        retries = int(event[3]) if len(event) > 3 else 0
                        self.live_control.run_scroll(str(event[1]), mode=mode, _retries=retries)
                elif kind == "flight_deck_menu_key":
                    if self._shell_phase is ShellPhase.ACTIVE and self._is_anchored():
                        action = self.flight_deck.navigate(str(event[1]))
                        self._sync_shell_hook_flags()
                        if action is not None:
                            self._dispatch_flight_deck_action(action)
                elif kind == "atom_create_key":
                    if self._deck_mode is DeckMode.ATOM_CREATE:
                        self._handle_atom_create_key(str(event[1]))
                elif kind == "flight_deck_remap_key":
                    self._apply_flight_deck_remap(int(event[1]))
                elif kind == "f6":
                    if self.walkthrough is not None and self.walkthrough.active:
                        pass
                    elif self.player.is_active:
                        self._stop_playback()
                    elif not self.recorder.active and not self.screen_map.active and not self.observation.active:
                        self._start_playback()
                elif kind == "f7" and self.player.is_active:
                    self._toggle_pause()
                elif kind == "f8":
                    self._stop_all()
        except Exception as exc:
            self._status(f"Hotkey handler failed: {exc}", "error")
        try:
            self._drain_observation_ui()
        except Exception as exc:
            self._status(f"Observation UI update failed: {exc}", "error")
        if self._lco_console_dirty:
            try:
                self._refresh_lco_console_window()
            except Exception as exc:
                self._status(f"LCO console UI update failed: {exc}", "error")
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
        self.hooks.state.observation_active = False
        self.hooks.state.title_dialog_open = False
        self.hooks.state.screenshot_busy = False
        self.hooks.state.walkthrough_active = False
        self.hooks.state.flight_deck_open = False
        self.hooks.state.flight_deck_expanded = False
        self.hooks.state.flight_deck_remap = False
        self.hooks.state.flight_deck_expand_armed = False
        self.hooks.state.flight_deck_active = False
        self.hooks.state.quit_confirm = False
        self.hooks.state.lab_visible = False
        try:
            if self._tray is not None:
                self._tray.stop()
                self._tray = None
        except Exception:
            pass
        try:
            release_single_instance()
        except Exception:
            pass
        try:
            if self.observation.active:
                self.observation.stop(reason="app_close")
        except Exception:
            pass
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
            if getattr(self, "flight_deck", None) is not None:
                self.flight_deck.destroy()
        except Exception:
            pass
        try:
            if self.guide_overlay is not None:
                self.guide_overlay.destroy()
        except Exception:
            pass
        try:
            if getattr(self, "live_control", None) is not None and self.live_control.active:
                self.live_control.exit(reason="quit")
            if getattr(self, "live_control_overlay", None) is not None:
                self.live_control_overlay.destroy()
        except Exception:
            pass
        self.destroy()

    def _start_collection_walkthrough(self, collection: Collection) -> None:
        if self.recorder.active or self.player.is_active or self.screen_map.active or self.observation.active:
            self._status("Stop recording/playback/observation before Walkthrough.", "warn")
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
        if self.observation.active and self.observation.batch is not None:
            session = self.observation.batch
        if session is None:
            self.screen_map_panel.set_idle()
        else:
            self.screen_map_panel.set_active(
                session.folder,
                session.titles,
                ready=self.observation.active or not self._screen_map_busy,
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
        """Observe tab entry — Observations replaced Space-titled batches."""

        self._start_observation()

    def _end_screen_map_batch(self) -> None:
        if self.observation.active:
            self._stop_observation(reason="operator", prompt_rename=False)
            return
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
            self._status("Observation OFF.", "warn")
            return
        self._status(
            f"Batch finished: {session.shot_count} shot(s) in {session.folder}",
            "ok",
        )

    def _open_screen_map_folder(self) -> None:
        if self.observation.active and self.observation.folder is not None:
            folder = self.observation.folder
        elif self.screen_map.session is not None:
            folder = self.screen_map.session.folder
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
        self.tabs.set("Observe")
        self._on_tab_changed()
        self._status(f"Opened Observe batch: {slug}", "info")

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
        # Re-load so steps from disk are current.
        self.ai_batch_store.load_all()
        live = self.ai_batch_store.batches.get(batch.slug)
        if live is None:
            self._status("Batch missing on disk — Reload.", "error")
            return
        if not live.is_offline():
            status, _hwnd, _rect, _title = self.anchor_target.snapshot()
            if status != "ok":
                self._status("Anchor a window before starting an AI batch run.", "error")
                return
        try:
            self.ai_batch_runner.start(live)
        except AiBatchRunnerError as exc:
            self._status(str(exc), "error")
            if self.ai_batch_panel is not None:
                self.ai_batch_panel.set_run_message(str(exc), level="error")
            return
        if self.ai_batch_panel is not None:
            mode = "offline" if live.is_offline() else "anchored"
            self.ai_batch_panel.set_running(True, f"Runner: starting {live.name} ({mode})…")
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
                        self.ai_batch_panel.set_running(
                            False,
                            "Runner: idle — Refresh if needed, then Open linked Observe / tell chat it ran.",
                        )
                    self._refresh_screen_map_catalog()
                    report = event.get("report") or {}
                    sm = report.get("screen_map_batch")
                    if sm:
                        self._status(
                            f"Mission finished. Observe: screen-maps/{sm}/ (+ run_report.json). "
                            "Use Open linked Observe.",
                            "ok",
                        )
                    self._update_activity()
        except Exception as exc:
            self._status(f"AI batch runner update failed: {exc}", "error")
        if self._alive:
            self.after(100, self._drain_ai_batch_runner)

    def _reload_ai_batches(self) -> None:
        errors = self.ai_batch_store.load_all()
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        seeded = getattr(self.ai_batch_store, "last_seeded", []) or []
        if errors:
            self._status("Skipped AI batch files: " + "; ".join(errors), "error")
        elif seeded:
            self._status(
                f"AI batches reloaded ({len(self.ai_batch_store.batches)}). "
                f"Seeded: {', '.join(seeded)}.",
                "ok",
            )
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
        self._reload_taxonomy()
        if self.auto_panel is not None:
            for message in errors:
                self.auto_panel.append_console(f"load error: {message}", "error")
            if not errors:
                self.auto_panel.append_console("Automations + taxonomy reloaded.", "ok")
        self.auto_runtime.reload_schedule()
        if self.atom_lab_pane is not None:
            try:
                self.atom_lab_pane.refresh()
            except Exception:
                pass
        if errors:
            self._status("Skipped automation files: " + "; ".join(errors), "error")
        else:
            self._status("Automations reloaded.", "ok")

    def _start_automations_selection(self, event, collection) -> None:
        """Start selected atom (once) or molecule (once | interval pool)."""

        from idle_lab.automations.schema import Collection as CollType
        from idle_lab.automations.schema import Event as EventType

        if collection is not None and isinstance(collection, CollType):
            self._start_molecule(collection)
            return
        if event is None or not isinstance(event, EventType):
            self._status("Select an Atom or Molecule in Loops, then Start selected.", "warn")
            if self.auto_panel is not None:
                self.auto_panel.append_console(
                    "Nothing selected. Click an atom (or molecule) in Available, then Start selected. "
                    "Or use Start all enabled for every JSON-enabled atom interval.",
                    "warn",
                )
            return
        if self.auto_runtime.collection_running:
            self._status("Stop the running atom/molecule job first.", "error")
            return
        if self.auto_runtime.is_running:
            self._status("Loops already running — Stop (or F8) first.", "warn")
            return
        if self.anchor_target.rect is None:
            self._status("Anchor a window before starting Loops.", "error")
            return
        try:
            self.auto_runtime.trace.configure(
                level=self.settings.trace_level, run_number=self.auto_store.runtime.run_number
            )
            self.auto_runtime.run_event_once(event.id)
            self._status(f"Atom once: {event.title}", "run")
            if self.auto_panel is not None:
                self.auto_panel.append_console(
                    f"Atom once started: {event.id} (no interval wait; F8 = Stop all)",
                    "ok",
                )
        except Exception as exc:
            self._status(f"Start failed: {exc}", "error")

    def _start_molecule(self, collection, *, lco_pack: bool = False) -> None:
        """Molecule Start: run=once → serial pack; run=interval → child atoms on scheduler."""

        from idle_lab.automations.schema import collection_interval_event_ids

        if self.anchor_target.rect is None:
            self._status("Anchor a window before starting Loops.", "error")
            return
        mode = (collection.run or "interval").strip().lower()
        if mode == "once":
            self._run_collection_pack(collection, lco_pack=lco_pack)
            return
        # interval pool
        if self.auto_runtime.collection_running:
            self._status("Stop the running atom/molecule job first.", "error")
            return
        if self.auto_runtime.is_running:
            self._status("Loops already running — Stop (or F8) first.", "warn")
            return
        event_ids = collection_interval_event_ids(
            collection, self.auto_store.events, self.auto_store.collections
        )
        if not event_ids:
            self._status(f"Molecule {collection.id} has no atom children to schedule.", "warn")
            return
        try:
            self.auto_runtime.trace.configure(
                level=self.settings.trace_level, run_number=self.auto_store.runtime.run_number
            )
            self.auto_runtime.start(event_ids=event_ids)
            self._status(f"Molecule interval: {collection.title} ({len(event_ids)} atom(s))", "run")
            if self.auto_panel is not None:
                self.auto_panel.append_console(
                    f"Molecule interval pool: {collection.id} → {', '.join(event_ids)} (F8 = Stop all)",
                    "ok",
                )
        except Exception as exc:
            self._status(f"Molecule start failed: {exc}", "error")
            if self.auto_panel is not None:
                self.auto_panel.append_console(str(exc), "error")

    def _start_automations_all_enabled(self) -> None:
        """CUT — Start-all-enabled removed from product UX."""

        self._status("Start all enabled is cut — start an explicit atom or molecule pack.", "warn")

    def _stop_automations(self) -> None:
        self.auto_runtime.stop()
        self._status("Automations stopped. (F8 also Stop all)", "warn")

    def _run_collection_pack(self, collection: Collection, *, lco_pack: bool = False) -> None:
        """Serial once-molecule (run_collection). Interval molecules use _start_molecule."""

        if self.auto_runtime.is_running:
            self._status("Stop interval Loops first (single mouse runway).", "error")
            return
        if self.anchor_target.rect is None:
            self._status("Anchor a window before running a molecule.", "error")
            return
        try:
            self.auto_runtime.trace.configure(
                level=self.settings.trace_level, run_number=self.auto_store.runtime.run_number
            )
            self.auto_runtime.start_collection(collection.id, lco_pack=bool(lco_pack))
            self._status(f"Molecule once: {collection.title}", "run")
            if self.auto_panel is not None:
                self.auto_panel.append_console(
                    f"Molecule once started: {collection.id} (Stop / Stop all to abort)",
                    "ok",
                )
        except Exception as exc:
            self._status(f"Molecule start failed: {exc}", "error")
            if self.auto_panel is not None:
                self.auto_panel.append_console(str(exc), "error")

    def _validate_automations(self) -> None:
        preset_names = {preset.name for preset in self.store.presets}
        report = validate_store(self.auto_store, preset_names=preset_names)
        text = format_report(report)
        if self.auto_panel is not None:
            for line in text.splitlines():
                self.auto_panel.append_console(line, "ok" if report.ok else "error")
        self._status("Validate ok." if report.ok else f"Validate found {len(report.issues)} issue(s).", "ok" if report.ok else "warn")

    def _dry_run_selection(self, event: object | None, collection: Collection | None) -> None:
        lines: list[str] = []
        if collection is not None:
            lines = dry_run_collection(collection, self.auto_store, variables=dict(self.auto_runtime.state.variables))
        elif event is not None:
            lines = dry_run_event(event, self.auto_store, variables=dict(self.auto_runtime.state.variables))  # type: ignore[arg-type]
        else:
            self._status("Select an event or collection for Dry-run.", "warn")
            return
        if self.auto_panel is not None:
            self.auto_panel.append_console("── dry-run ──", "info")
            for line in lines:
                self.auto_panel.append_console(line, "info")
        self._status(f"Dry-run printed ({len(lines)} lines).", "ok")

    def _export_prompt_packet(self) -> None:
        root = project_root()
        packets = root / "prompt-packets"
        packets.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = packets / f"packet-{stamp}"
        goal = (
            "Describe the automation you want in plain language. "
            "Replace this GOAL.md after export if needed."
        )
        vision_dir = None
        batches = list_screen_map_batches(self.screen_maps_root)
        if batches:
            # newest first typically
            vision_dir = self.screen_maps_root / batches[0].slug
        try:
            export_prompt_packet(
                dest,
                goal=goal,
                vision_batch_dir=vision_dir,
                project_root=root,
            )
            self._status(f"Prompt packet exported: {dest}", "ok")
            try:
                os.startfile(str(dest))  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception as exc:
            self._status(f"Packet export failed: {exc}", "error")

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

    # --- Lab lifecycle: Refresh / Restart / Stop all / Activity / Comments ---

    def _refresh_lab(self) -> None:
        """Reload all file-backed stores without killing the process."""

        if self.recorder.active:
            self._status("Finish recording before Refresh.", "error")
            return
        messages: list[str] = []
        preset_path = self.current.path if self.current is not None else None
        preset_errors = self.store.load_all()
        self._select_path(preset_path)
        if preset_errors:
            messages.append("presets: " + "; ".join(preset_errors))

        auto_errors = self.auto_store.load_all()
        self.auto_runtime.reload_schedule()
        if auto_errors:
            messages.append("automations: " + "; ".join(auto_errors))

        ai_errors = self.ai_batch_store.load_all()
        if self.ai_batch_panel is not None:
            self.ai_batch_panel.refresh_list()
        if ai_errors:
            messages.append("missions: " + "; ".join(ai_errors))

        comment_errors = self.comment_store.load()
        if comment_errors:
            messages.append("comments: " + "; ".join(comment_errors))

        self._refresh_screen_map_catalog()
        self._rebuild_preset_list()
        self._reload_taxonomy()
        if self.auto_panel is not None:
            for message in auto_errors:
                self.auto_panel.append_console(f"load error: {message}", "error")
            if not auto_errors:
                self.auto_panel.append_console("Lab refreshed (automations + taxonomy).", "ok")
        self._sync_flight_deck_expand_vk()
        self._last_refresh_at = time.time()
        self._disk_fingerprint = dir_fingerprint(self._watch_paths)
        self._update_files_badge()
        stamp = time.strftime("%H:%M:%S")
        if messages:
            self._status(f"Lab refreshed at {stamp} with skips — " + " | ".join(messages), "warn")
        else:
            self._status(
                f"Lab refreshed at {stamp} "
                f"({len(self.store.presets)} presets, "
                f"{len(self.ai_batch_store.batches)} missions, "
                f"{len(self.auto_store.events)} events).",
                "ok",
            )

    def _stop_all(self) -> None:
        """Halt every owner of the mouse / capture without quitting."""

        stopped: list[str] = []
        if self.player.is_active:
            self.player.stop()
            stopped.append("Bench playback")
        if self.ai_batch_runner.is_running:
            self.ai_batch_runner.stop()
            stopped.append("Mission")
            if self.ai_batch_panel is not None:
                self.ai_batch_panel.set_run_message("Runner: stop requested…", level="warn")
        if self.auto_runtime.is_running or self.auto_runtime.collection_running:
            self.auto_runtime.stop()
            stopped.append("Loops")
        if self.observation.active:
            try:
                self._stop_observation(reason="stop_all", prompt_rename=False)
                stopped.append("Observation")
            except Exception:
                pass
        elif self.screen_map.active:
            try:
                self._end_screen_map_batch()
                stopped.append("Observe capture")
            except Exception:
                pass
        if self.walkthrough is not None and self.walkthrough.active:
            self._stop_collection_walkthrough()
            stopped.append("Walkthrough")
        if self.live_control.active:
            self._exit_live_control(reason="stop_all")
            stopped.append("Live Control Overlay")
        self._update_activity()
        if stopped:
            self._status("Stopped: " + ", ".join(stopped) + ".", "warn")
        else:
            self._status("Nothing running — already Idle.", "info")

    def _restart_lab(self) -> None:
        """Stop runners, save settings, relaunch process, exit (code changes).

        Successor gets ``--auto-anchor`` so R / Restart rebinds the last window
        without the Enter confirm step.
        """

        self._stop_all()
        try:
            self._save_settings()
        except Exception:
            pass
        # Release before spawn so the successor can take the single-instance lock.
        try:
            release_single_instance()
        except Exception:
            pass
        root = project_root()
        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        try:
            subprocess.Popen(
                restart_command(sys.executable, auto_anchor=True),
                cwd=str(root),
                close_fds=True,
                creationflags=creationflags,
            )
        except OSError as exc:
            self._status(f"Restart failed: {exc}", "error")
            return
        self._on_close()

    def _activity_text(self) -> str:
        if self.anchor_target.rect is None and (
            self.ai_batch_runner.is_running
            or self.auto_runtime.is_running
            or self.auto_runtime.collection_running
            or self.player.is_active
        ):
            return "Activity: Unanchored · actuation requested"
        if self.ai_batch_runner.is_running:
            slug_name = self.ai_batch_runner.active_slug or "?"
            return f"Activity: Mission · {slug_name}"
        if self.auto_runtime.collection_running:
            snap = self.auto_runtime.operator_snapshot()
            detail = snap.get("detail") or "collection"
            return f"Activity: Loops · {detail}"
        if self.auto_runtime.is_running:
            snap = self.auto_runtime.operator_snapshot()
            deferred = snap.get("deferred_summary") or ""
            blocking = snap.get("blocking_id")
            if deferred and blocking:
                return f"Activity: Loops · {blocking} · deferred: {deferred}"
            if blocking:
                return f"Activity: Loops · {blocking}"
            return "Activity: Loops"
        if self.observation.active:
            shots = self.observation.shot_count
            return f"Activity: Observe · recording ({shots} shots)"
        if self.screen_map.active:
            return "Activity: Observe · capturing"
        if self.player.is_active:
            return "Activity: Bench · playback"
        if self.recorder.active:
            return "Activity: Bench · recording"
        if self.walkthrough is not None and self.walkthrough.active:
            return "Activity: Walkthrough"
        return "Activity: Idle"

    def _sync_mode_chip(self) -> None:
        if getattr(self, "mode_chip", None) is None:
            return
        mode = normalize_lab_mode(self.settings.lab_mode)
        label = "Supervised" if mode == "supervised" else "Auto"
        self.mode_chip.configure(text=f"Mode: {label}")

    def _update_activity(self) -> None:
        if getattr(self, "mode_chip", None) is not None:
            mode = normalize_lab_mode(self.settings.lab_mode)
            self.mode_chip.configure(text=f"Mode: {'Supervised' if mode == 'supervised' else 'Auto'}")
        # Let Esc halt Loops/Missions the same way F8 does when something is running.
        try:
            self.hooks.state.stoppable = bool(
                self.auto_runtime.is_running
                or self.auto_runtime.collection_running
                or self.ai_batch_runner.is_running
                or self.player.is_active
                or self.recorder.active
                or self.observation.active
                or self.screen_map.active
                or (self.walkthrough is not None and self.walkthrough.active)
            )
        except Exception:
            pass
        if getattr(self, "activity_label", None) is None:
            return
        self.activity_label.configure(text=self._activity_text())
        if getattr(self, "flight_deck", None) is not None:
            try:
                self._sync_flight_deck_run_state()
            except Exception:
                pass

    def _update_files_badge(self) -> None:
        if getattr(self, "files_badge", None) is None:
            return
        current = dir_fingerprint(self._watch_paths)
        if self._disk_fingerprint and current > self._disk_fingerprint + 0.01:
            self.files_badge.configure(text="Files changed — Refresh")
            if getattr(self, "refresh_button", None) is not None:
                self.refresh_button.configure(fg_color="#C9A227", hover_color="#E0B93A", text_color="#161616")
        else:
            age = ""
            if self._last_refresh_at is not None:
                secs = int(time.time() - self._last_refresh_at)
                age = f" · refreshed {secs}s ago" if secs < 120 else " · refreshed"
            self.files_badge.configure(text=age.lstrip(" ·") if age else "")
            if getattr(self, "refresh_button", None) is not None:
                self.refresh_button.configure(
                    fg_color=["#3B8ED0", "#1F6AA5"],
                    hover_color=["#36719F", "#144870"],
                    text_color="#DCE4EE",
                )

    def _poll_disk_watch(self) -> None:
        try:
            self._update_files_badge()
        except Exception:
            pass
        if self._alive:
            self.after(2000, self._poll_disk_watch)

    def _poll_activity(self) -> None:
        try:
            self._update_activity()
        except Exception:
            pass
        if self._alive:
            self.after(400, self._poll_activity)

    def _open_object_comment(self, title: str, object_path: str) -> None:
        initial = self.comment_store.get(object_path)

        def save(text: str) -> None:
            self.comment_store.set(object_path, text)
            self._disk_fingerprint = dir_fingerprint(self._watch_paths)
            self._rebuild_preset_list()
            if self.screen_map_panel is not None:
                self.screen_map_panel.refresh_comments()
            if self.ai_batch_panel is not None:
                self.ai_batch_panel.refresh_list()
            if self.auto_panel is not None:
                self.auto_panel.refresh_list()
            self._status(f"Saved comment on {object_path}", "ok")

        open_comment_dialog(
            self,
            title=title,
            object_path=object_path,
            initial=initial,
            on_save=save,
        )

    def _comment_mission(self, batch: AiBatch) -> None:
        self._open_object_comment(
            f"Comment · mission · {batch.name}",
            mission_comment_path(batch.slug),
        )

    def _comment_mission_request(self, batch: AiBatch, req: BatchRequest) -> None:
        self._open_object_comment(
            f"Comment · request · {req.label}",
            mission_request_comment_path(batch.slug, req.id),
        )

    def _comment_event(self, event_id: str, label: str) -> None:
        self._open_object_comment(f"Comment · event · {label}", event_comment_path(event_id))

    def _comment_collection(self, collection_id: str, label: str) -> None:
        self._open_object_comment(
            f"Comment · collection · {label}",
            collection_comment_path(collection_id),
        )

    def _comment_screen_map_batch(self, batch: BatchSummary) -> None:
        path = screen_map_batch_comment_path(batch.slug)

        def save(text: str) -> None:
            self.comment_store.set(path, text)
            try:
                manifest = load_manifest(batch.folder)
                manifest.notes = text.strip() or None
                save_manifest(batch.folder, manifest)
            except Exception as exc:
                self._status(f"Comment saved; manifest sync failed: {exc}", "warn")
                return
            self._refresh_screen_map_catalog()
            self._status(f"Saved batch comment: {batch.slug}", "ok")

        open_comment_dialog(
            self,
            title=f"Comment · batch · {batch.title}",
            object_path=path,
            initial=self.comment_store.get(path) or (batch.manifest.notes or ""),
            on_save=save,
        )

    def _comment_screen_map_shot(self, batch: BatchSummary, shot_index: int) -> None:
        if shot_index < 0 or shot_index >= len(batch.manifest.shots):
            return
        shot = batch.manifest.shots[shot_index]
        path = screen_map_shot_comment_path(batch.slug, shot.filename)

        def save(text: str) -> None:
            self.comment_store.set(path, text)
            try:
                manifest = load_manifest(batch.folder)
                if shot_index < len(manifest.shots):
                    manifest.shots[shot_index].notes = text.strip() or None
                    save_manifest(batch.folder, manifest)
            except Exception as exc:
                self._status(f"Comment saved; shot notes sync failed: {exc}", "warn")
                return
            self._refresh_screen_map_catalog()
            self._status(f"Saved shot comment: {shot.filename}", "ok")

        open_comment_dialog(
            self,
            title=f"Comment · shot · {shot.title}",
            object_path=path,
            initial=self.comment_store.get(path) or (shot.notes or ""),
            on_save=save,
        )


def main(*, auto_anchor: bool = False) -> None:
    if sys.platform == "win32" and not try_acquire_single_instance():
        # Existing process was signaled to come forward.
        return
    win32_api.set_dpi_aware()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App(auto_anchor=auto_anchor)
    try:
        app.mainloop()
    finally:
        try:
            release_single_instance()
        except Exception:
            pass
