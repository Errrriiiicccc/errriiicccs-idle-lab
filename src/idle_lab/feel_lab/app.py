"""Feel Lab — colour schemes + structure experiments (layered focus)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

import customtkinter as ctk
import tkinter as tk
import tkinter.font as tkfont

from idle_lab.feel_lab.stages import HOME_TABS, stage_by_id
from idle_lab.feel_lab.store import get_main_look_id, load_picks, save_pick, set_main_look
from idle_lab.feel_lab.themes import (
    FAMILIES,
    Family,
    Look,
    family_by_id,
    family_for_look,
    ordered_looks,
    resolve_look_id,
    theme_by_id,
)

Mode = Literal["live", "return", "dorm"]
StructureMode = Literal["folder_tree", "top_down", "left_right", "collapse"]


def _depth_plate(look: Look, depth: int, *, live: bool) -> tuple[str, str, str, str]:
    """Return (bg, border, key_fg, text_fg) — deeper folders lift toward live ink plates."""
    # Anchored to Type-Bracket ink room; still works on other schemes via look fields.
    steps = (
        (look.return_bg, look.return_border, look.esc_pop, look.return_text),
        (look.panel, look.desc_border, look.line, look.muted),
        (look.live_bg, look.live_border, look.live_key, look.live_text),
        (look.live_hover, look.live_border, look.live_key, look.live_text),
    )
    idx = min(depth, len(steps) - 1)
    if live:
        idx = min(max(idx, 2), len(steps) - 1)
        return steps[idx][0], look.live_border, look.live_key, look.live_text
    return steps[idx]


def main() -> int:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("green")
    FeelLabApp().mainloop()
    return 0


def _format_key(look: Look, key: str) -> str:
    k = key.upper() if look.uppercase else key
    if look.key_format == "bare":
        return k
    if look.key_format == "dot":
        return f"{k} ·"
    if look.key_format == "paren":
        return f"({k})"
    return f"[{k}]"


def _label_text(look: Look, label: str, *, is_new: bool = False) -> str:
    text = label.upper() if look.uppercase else label
    return f"· {text}" if is_new else text


@dataclass
class FocusAction:
    key: str
    label: str
    run: Callable[[], None]
    describe: str = ""
    is_new: bool = False


@dataclass
class FocusLayer:
    id: str
    title: str
    actions: list[FocusAction] = field(default_factory=list)
    hint: str = ""
    current: str = ""  # collapsed return summary (e.g. "Thread › Bracket")


@dataclass
class TreeItem:
    """Accordion folder / leaf — siblings stay visible; open branch expands underneath."""

    id: str
    key: str
    title: str
    describe: str = ""
    children: tuple["TreeItem", ...] = ()
    activate: Callable[[], None] | None = None  # leaf action
    is_new: bool = False


class KeyBtn(tk.Frame):
    def __init__(self, master) -> None:
        super().__init__(master, highlightthickness=0, bd=0)
        self.pack_propagate(False)
        self._key = ""
        self._label = ""
        self._command: Callable[[], None] | None = None
        self._describe = ""
        self._on_focus_desc: Callable[[str], None] | None = None
        self._mode: Mode = "dorm"
        self._is_new = False
        self._look: Look | None = None
        self._always_click = False

        self._rail = tk.Frame(self, bd=0, highlightthickness=0)
        self._body = tk.Frame(self, bd=0, highlightthickness=0)
        self._body.pack(side="left", fill="both", expand=True)
        self._key_lbl = tk.Label(self._body, anchor="w")
        self._lab_lbl = tk.Label(self._body, anchor="w")

        for w in (self, self._body, self._key_lbl, self._lab_lbl, self._rail):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

    def bind_action(self, action: FocusAction, on_focus_desc: Callable[[str], None] | None) -> None:
        self._key = action.key
        self._label = action.label
        self._command = action.run
        self._describe = action.describe
        self._is_new = action.is_new
        self._on_focus_desc = on_focus_desc

    def set_mode(self, mode: Mode, look: Look) -> None:
        self._mode = mode
        self._look = look
        style = look.style

        pad = look.pad_x
        size = look.font_size
        live_size = size + 1
        live_family = "Segoe UI Semibold"
        quiet_family = "Segoe UI"

        if mode == "live":
            bg, border = look.live_bg, look.live_border
            key_font = (live_family, live_size)
            lab_font = (live_family, live_size) if not look.bold_key_only else (quiet_family, size)
            if look.bold_key_only:
                key_font = (live_family, live_size)
            key_text = _format_key(look, self._key)
            lab_text = _label_text(look, self._label, is_new=self._is_new)
            self._key_lbl.configure(text=key_text, fg=look.live_key, font=key_font)
            self._lab_lbl.configure(text=lab_text, fg=look.live_text, font=lab_font)
        elif mode == "return":
            bg, border = look.return_bg, look.return_border
            quiet = (quiet_family, size)
            key_text, lab_text = "", _label_text(look, self._label)
            self._key_lbl.configure(text=key_text, fg=look.return_text, font=quiet)
            self._lab_lbl.configure(text=lab_text, fg=look.return_text, font=quiet)
        else:
            bg, border = look.dorm_bg, look.dorm_bg
            quiet = (quiet_family, max(10, size - 1))
            key_text, lab_text = "", _label_text(look, self._label)
            self._key_lbl.configure(text="", fg=look.dorm_text, font=quiet)
            self._lab_lbl.configure(text=lab_text, fg=look.dorm_text, font=quiet)

        self._key_lbl.pack_forget()
        self._lab_lbl.pack_forget()
        self._key_lbl.pack(side="left", padx=(pad, 4), pady=4)
        self._lab_lbl.pack(side="left", fill="x", expand=True, padx=(0, pad), pady=4)

        # Live always needs a readable plate edge (especially Type/ink).
        live_edge = max(1, look.border_width) if mode == "live" else look.border_width

        if style == "rim" and mode in {"live", "return"}:
            thick = live_edge if mode == "live" else (look.border_width if look.show_group_border else 0)
            self.configure(bg=bg, highlightthickness=max(thick, 1 if mode == "live" else 0), highlightbackground=border, highlightcolor=border)
            self._rail.pack_forget()
        elif style == "rail" and mode == "live":
            self.configure(bg=bg, highlightthickness=max(1, look.border_width if look.show_group_border else 1), highlightbackground=border, highlightcolor=border)
            self._rail.configure(bg=border, width=look.rail_width)
            if not self._rail.winfo_ismapped():
                self._rail.pack(side="left", fill="y", before=self._body)
        elif style == "rail" and mode == "return":
            self.configure(bg=bg, highlightthickness=0)
            self._rail.pack_forget()
        elif style == "lift" and mode in {"live", "return"}:
            # Lift has no outline — pop via stronger plate + hairline so it isn't floating text.
            thick = 1 if mode == "live" else 0
            self.configure(bg=bg, highlightthickness=thick, highlightbackground=border, highlightcolor=border)
            self._rail.pack_forget()
        elif style == "type":
            pure = look.live_bg if mode == "live" else (look.return_bg if mode == "return" else look.dorm_bg)
            thick = 1 if mode == "live" else (1 if mode == "return" else 0)
            edge = border if mode == "live" else look.return_border
            self.configure(
                bg=pure,
                highlightthickness=thick,
                highlightbackground=edge,
                highlightcolor=edge,
            )
            self._rail.pack_forget()
            bg = pure
            if mode == "live":
                self._key_lbl.configure(fg=look.live_key)
                self._lab_lbl.configure(fg=look.live_text)
            elif mode == "return":
                self._lab_lbl.configure(fg=look.return_text)
        else:
            thick = 1 if mode == "live" else 0
            self.configure(bg=bg, highlightthickness=thick, highlightbackground=border, highlightcolor=border)
            self._rail.pack_forget()

        self._body.configure(bg=bg)
        self._key_lbl.configure(bg=bg)
        self._lab_lbl.configure(bg=bg)

        # Dynamic width — never clip "[1] Bracket · main"
        key_font_use = self._key_lbl.cget("font")
        lab_font_use = self._lab_lbl.cget("font")
        kf = tkfont.Font(font=key_font_use)
        lf = tkfont.Font(font=lab_font_use)
        text_w = kf.measure(self._key_lbl.cget("text")) + lf.measure(self._lab_lbl.cget("text"))
        rail_w = look.rail_width if (style == "rail" and mode == "live") else 0
        edge_pad = 8
        width = max(look.btn_width, text_w + pad * 2 + 8 + rail_w + edge_pad)
        self.configure(width=width, height=look.btn_height)

    def _click(self, _e=None) -> None:
        if self._command and (self._mode == "live" or self._always_click):
            if self._describe and self._on_focus_desc:
                self._on_focus_desc(self._describe)
            self._command()

    def _enter(self, _e=None) -> None:
        if self._mode != "live" or not self._look:
            return
        h = self._look.live_hover
        self.configure(bg=h)
        self._body.configure(bg=h)
        self._key_lbl.configure(bg=h)
        self._lab_lbl.configure(bg=h)
        if self._describe and self._on_focus_desc:
            self._on_focus_desc(self._describe)

    def _leave(self, _e=None) -> None:
        if self._mode == "live" and self._look:
            self.set_mode("live", self._look)


class EscSummary(tk.Frame):
    """Collapsed return: Esc → Title + current: … (no button ghosts)."""

    def __init__(self, master) -> None:
        super().__init__(master, bd=0, highlightthickness=0)
        self._rail = tk.Frame(self, bd=0, width=3)
        self._rail.pack(side="left", fill="y")
        self._body = tk.Frame(self, bd=0)
        self._body.pack(side="left", fill="both", expand=True)
        self._esc = tk.Label(self._body, anchor="w", font=("Segoe UI Semibold", 12))
        self._esc.pack(fill="x", padx=10, pady=(8, 0))
        self._cur = tk.Label(self._body, anchor="w", font=("Segoe UI", 10))
        self._cur.pack(fill="x", padx=10, pady=(0, 8))

    def show(self, title: str, current: str, look: Look) -> None:
        self.configure(bg=look.return_bg, highlightthickness=1, highlightbackground=look.return_border, highlightcolor=look.return_border)
        self._rail.configure(bg=look.esc_pop)
        self._body.configure(bg=look.return_bg)
        self._esc.configure(bg=look.return_bg, fg=look.esc_pop, text=f"Esc  →  {title}")
        self._cur.configure(
            bg=look.return_bg,
            fg=look.return_text,
            text=f"current: {current}" if current else "current: —",
        )


class FolderBranch(tk.Frame):
    """One folder row + optional children host (explorer expand-underneath)."""

    def __init__(self, master) -> None:
        super().__init__(master, bd=0, highlightthickness=0)
        self._on_header: Callable[[], None] | None = None
        self._header = tk.Frame(self, bd=0, highlightthickness=0, cursor="hand2")
        self._header.pack(fill="x")
        self._chev = tk.Label(self._header, width=2, anchor="w")
        self._chev.pack(side="left", padx=(8, 0), pady=6)
        self._title = tk.Label(self._header, anchor="w", font=("Segoe UI Semibold", 11))
        self._title.pack(side="left", fill="x", expand=True, pady=6)
        self._meta = tk.Label(self._header, anchor="e", font=("Segoe UI", 9))
        self._meta.pack(side="right", padx=10, pady=6)
        self._kids = tk.Frame(self, bd=0)
        self._btns: list[KeyBtn] = []
        for w in (self._header, self._chev, self._title, self._meta):
            w.bind("<Button-1>", self._click)

    def _click(self, _e=None) -> None:
        if self._on_header:
            self._on_header()

    def show(
        self,
        *,
        title: str,
        depth: int,
        look: Look,
        expanded: bool,
        live: bool,
        current: str,
        actions: list[FocusAction] | None,
        on_focus_desc: Callable[[str], None],
        on_header: Callable[[], None] | None,
        keymap: dict[str, Callable[[], None]],
    ) -> None:
        self._on_header = on_header
        bg, border, key_fg, text_fg = _depth_plate(look, depth, live=live)
        indent = 14 + depth * 18
        self.configure(bg=look.bg)
        self._header.configure(
            bg=bg,
            highlightthickness=1 if live else 1,
            highlightbackground=border,
            highlightcolor=border,
        )
        chev = "▼" if expanded else "▸"
        self._chev.configure(bg=bg, fg=key_fg if live else look.esc_pop, text=chev, font=("Segoe UI Semibold", 11))
        self._title.configure(bg=bg, fg=text_fg if live else look.esc_pop, text=title)
        meta = ""
        if live:
            meta = "open"
        elif current:
            meta = f"current: {current}"
        else:
            meta = "Esc → here"
        self._meta.configure(bg=bg, fg=look.muted if not live else look.caption, text=meta)

        self._kids.pack_forget()
        for btn in self._btns:
            btn.pack_forget()

        if not (live and actions):
            return

        self._kids.configure(bg=look.bg)
        self._kids.pack(fill="x", padx=(indent, 4), pady=(4, 6))
        while len(self._btns) < len(actions):
            self._btns.append(KeyBtn(self._kids))
        child_bg, child_border, _, _ = _depth_plate(look, depth + 1, live=True)
        for i, action in enumerate(actions):
            btn = self._btns[i]
            btn.bind_action(action, on_focus_desc)
            btn.set_mode("live", look)
            # Depth tint the live child plates a step brighter than the folder header
            btn.configure(bg=child_bg, highlightthickness=1, highlightbackground=child_border, highlightcolor=child_border)
            btn._body.configure(bg=child_bg)  # noqa: SLF001
            btn._key_lbl.configure(bg=child_bg)  # noqa: SLF001
            btn._lab_lbl.configure(bg=child_bg)  # noqa: SLF001
            if btn._rail.winfo_ismapped():  # noqa: SLF001
                btn._rail.configure(bg=child_border)  # noqa: SLF001
            btn.pack(anchor="w", pady=2, padx=(0, 4))
            keymap[action.key.lower()] = action.run
            keymap[action.key.upper()] = action.run
        for j in range(len(actions), len(self._btns)):
            self._btns[j].pack_forget()


class LayerStrip(tk.Frame):
    def __init__(self, master, on_focus_desc: Callable[[str], None]) -> None:
        super().__init__(master, bd=0, highlightthickness=0)
        self._on_focus_desc = on_focus_desc
        self._outer = tk.Frame(self, bd=0)
        self._outer.pack(fill="both", expand=True)
        self._rail = tk.Frame(self._outer, bd=0)
        self._inner = tk.Frame(self._outer, bd=0)
        self._inner.pack(side="left", fill="both", expand=True)
        self._header = tk.Label(self._inner, anchor="w")
        self._header.pack(fill="x")
        self._hint = tk.Label(self._inner, anchor="w", justify="left", wraplength=720)
        self._grid = tk.Frame(self._inner, bd=0)
        self._grid.pack(fill="x")
        self._btns: list[KeyBtn] = []

    def show_layer(self, layer: FocusLayer, mode: Mode, look: Look) -> None:
        style = look.style
        if mode == "live":
            bg, fg, border = look.board, look.live_key, look.live_border
            # Type: band uses page board which is nearly black — lift live band slightly
            if style == "type":
                bg = look.panel
            head = f"LIVE · {layer.title}"
            head_fg = fg
            rail_color = border
        elif mode == "return":
            bg, border = look.return_bg, look.return_border
            head = f"Esc  →  {layer.title}"
            head_fg = look.esc_pop
            rail_color = look.esc_pop
        else:
            bg, border = look.dorm_bg, look.dorm_bg
            head = layer.title
            head_fg = look.dorm_text
            rail_color = look.dorm_bg

        if look.uppercase and mode == "live":
            head = head.upper()

        pad = look.group_pad
        gap = 2 if look.tight_gap else 4

        if style == "rim" and mode == "live":
            thick = max(1, look.border_width if look.show_group_border else 1)
            self.configure(bg=bg, highlightthickness=thick, highlightbackground=border, highlightcolor=border)
            self._rail.pack_forget()
        elif style == "rail" and mode == "live":
            thick = max(1, look.border_width if look.show_group_border else 1)
            self.configure(bg=bg, highlightthickness=thick, highlightbackground=border, highlightcolor=border)
            self._rail.configure(bg=rail_color, width=max(look.rail_width, 3))
            if not self._rail.winfo_ismapped():
                self._rail.pack(side="left", fill="y", before=self._inner)
        elif style == "rail" and mode == "return":
            self.configure(bg=bg, highlightthickness=0)
            self._rail.configure(bg=look.esc_pop, width=2)
            if not self._rail.winfo_ismapped():
                self._rail.pack(side="left", fill="y", before=self._inner)
        elif style == "lift" and mode in {"live", "return"}:
            self.configure(bg=bg, highlightthickness=1 if mode == "live" else 0, highlightbackground=border, highlightcolor=border)
            self._rail.pack_forget()
        elif style == "type":
            pure = bg
            thick = 1 if mode in {"live", "return"} else 0
            edge = border if mode == "live" else look.return_border
            self.configure(bg=pure, highlightthickness=thick, highlightbackground=edge, highlightcolor=edge)
            self._rail.pack_forget()
        elif mode == "return":
            self.configure(bg=bg, highlightthickness=1, highlightbackground=look.return_border, highlightcolor=look.return_border)
            self._rail.pack_forget()
        else:
            self.configure(bg=bg, highlightthickness=0)
            self._rail.pack_forget()

        self._outer.configure(bg=bg)
        self._inner.configure(bg=bg)
        self._header.configure(
            bg=bg,
            fg=head_fg,
            text=head,
            font=("Segoe UI", look.header_size + (1 if mode == "return" else 0), "bold" if mode in {"live", "return"} else "normal"),
            padx=pad,
            pady=max(6, pad // 2),
        )
        hint_fg = look.caption if mode == "live" else (look.return_text if mode == "return" else look.dorm_text)
        self._hint.configure(bg=bg, fg=hint_fg, padx=pad)
        self._grid.configure(bg=bg)
        self._grid.pack_forget()
        self._grid.pack(fill="x", padx=pad, pady=(0, pad))

        if layer.hint and mode == "live":
            self._hint.configure(text=layer.hint)
            if not self._hint.winfo_ismapped():
                self._hint.pack(fill="x", before=self._grid)
        elif layer.current and mode == "return":
            self._hint.configure(text=f"current: {layer.current}")
            if not self._hint.winfo_ismapped():
                self._hint.pack(fill="x", before=self._grid)
        else:
            self._hint.pack_forget()

        # Return/dorm in full mode still show buttons; collapse mode uses EscSummary instead.
        show_btns = mode == "live" or mode == "return"
        per_row = 6
        n = len(layer.actions) if show_btns else 0
        while len(self._btns) < max(n, 1):
            self._btns.append(KeyBtn(self._grid))

        for i, btn in enumerate(self._btns):
            btn.grid_forget()
            if i >= n:
                continue
            btn.bind_action(layer.actions[i], self._on_focus_desc if mode == "live" else None)
            btn.set_mode(mode, look)
            btn.grid(row=i // per_row, column=i % per_row, padx=gap, pady=gap, sticky="w")


class FeelLabApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Feel Lab")
        self.geometry("1180x740")
        self.minsize(960, 600)

        self._picks = load_picks().get("picks", {})
        start_raw = get_main_look_id()
        if not start_raw:
            saved = self._picks.get("change_theme") if isinstance(self._picks, dict) else None
            if isinstance(saved, dict) and saved.get("variant"):
                start_raw = str(saved["variant"])
        self._look = theme_by_id(resolve_look_id(str(start_raw) if start_raw else None))

        self._stack: list[FocusLayer] = []
        self._keymap: dict[str, Callable[[], None]] = {}
        self._strips: list[LayerStrip] = []
        self._esc_chips: list[EscSummary] = []
        self._folders: list[FolderBranch] = []
        self._nav_busy = False
        self._area = "describe_feel"  # home selection
        self._structure: StructureMode = self._load_structure()
        self._tree_roots: list[TreeItem] = []
        self._tree_path: list[str] = []  # expanded folder ids; siblings at each level stay visible
        self._top_tab_btns: list[KeyBtn] = []
        self._home_btns: list[KeyBtn] = []

        self._build_shell()
        # Land on Colour Scheme accordion — sibling families stay; expand under selection
        self._open_theme()
        self.bind("<KeyPress>", self._on_key)
        self.after(10, self.focus_force)

    def _load_structure(self) -> StructureMode:
        raw = self._picks.get("change_structure") if isinstance(self._picks, dict) else None
        if isinstance(raw, dict):
            v = str(raw.get("variant") or "")
            if v in {"folder_tree", "top_down", "left_right", "collapse"}:
                return v  # type: ignore[return-value]
        return "folder_tree"

    def _build_shell(self) -> None:
        look = self._look
        self.configure(fg_color=look.bg)

        # Do not name this `_root` — that shadows Tk's `_root()` and crashes CTk.configure.
        self._shell = tk.Frame(self, bg=look.bg)
        self._shell.pack(fill="both", expand=True)

        # Left home rail (file-explorer)
        self._home_rail = tk.Frame(self._shell, bg=look.panel, width=200)
        self._home_rail.pack(side="left", fill="y")
        self._home_rail.pack_propagate(False)
        self._home_title = tk.Label(
            self._home_rail, text="Home", bg=look.panel, fg=look.line, font=("Segoe UI Semibold", 14), anchor="w"
        )
        self._home_title.pack(fill="x", padx=12, pady=(14, 8))
        self._home_list = tk.Frame(self._home_rail, bg=look.panel)
        self._home_list.pack(fill="both", expand=True, padx=8, pady=4)

        # Right workspace
        self._work = tk.Frame(self._shell, bg=look.bg)
        self._work.pack(side="left", fill="both", expand=True)

        self._chrome = tk.Frame(self._work, bg=look.panel, height=48)
        self._chrome.pack(fill="x")
        self._chrome.pack_propagate(False)
        self._title = tk.Label(self._chrome, text="Feel Lab", bg=look.panel, fg=look.line, font=("Segoe UI", 15), anchor="w")
        self._title.pack(side="left", padx=14, pady=10)
        self._path = tk.Label(self._chrome, text="", bg=look.panel, fg=look.muted, font=("Segoe UI", 10), anchor="e")
        self._path.pack(side="right", padx=14)

        # Top tabs — siblings of current nest
        self._tabs_bar = tk.Frame(self._work, bg=look.bg)
        self._tabs_bar.pack(fill="x", padx=10, pady=(8, 0))
        self._tabs_label = tk.Label(self._tabs_bar, text="Area", bg=look.bg, fg=look.muted, font=("Segoe UI", 9), anchor="w")
        self._tabs_label.pack(fill="x", padx=4)
        self._tabs_row = tk.Frame(self._tabs_bar, bg=look.bg)
        self._tabs_row.pack(fill="x", pady=(2, 0))

        self._status_bar = tk.Frame(self._work, bg=look.board, height=32)
        self._status_bar.pack(fill="x", padx=10, pady=(8, 0))
        self._status_bar.pack_propagate(False)
        self._status = tk.Label(self._status_bar, text="", bg=look.board, fg=look.line, font=("Segoe UI", 10), anchor="w")
        self._status.pack(fill="x", padx=12, pady=6)

        self._body = tk.Frame(self._work, bg=look.bg)
        self._body.pack(fill="both", expand=True, padx=10, pady=8)
        self._stack_host = tk.Frame(self._body, bg=look.bg)
        self._stack_host.pack(fill="both", expand=True)
        # Accordion tree host (rebuilt each render in folder_tree mode)
        self._tree_host = tk.Frame(self._stack_host, bg=look.bg)
        self._tree_host.pack(fill="both", expand=True)

        self._describe_box = tk.Frame(
            self._work,
            bg=look.bg,
            highlightthickness=1,
            highlightbackground=look.desc_border,
            highlightcolor=look.desc_border,
        )
        self._describe_box.pack(fill="x", padx=10, pady=(0, 10))
        self._describe = tk.Label(
            self._describe_box,
            text="",
            bg=look.bg,
            fg=look.caption,
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            padx=14,
            pady=12,
            wraplength=860,
        )
        self._describe.pack(fill="x")
        self._paint_chrome()

    def _paint_chrome(self) -> None:
        look = self._look
        self.configure(fg_color=look.bg)
        for w, bg in (
            (self._shell, look.bg),
            (self._home_rail, look.panel),
            (self._home_list, look.panel),
            (self._work, look.bg),
            (self._chrome, look.panel),
            (self._tabs_bar, look.bg),
            (self._tabs_row, look.bg),
            (self._status_bar, look.board),
            (self._body, look.bg),
            (self._stack_host, look.bg),
            (self._tree_host, look.bg),
            (self._describe_box, look.bg),
            (self._describe, look.bg),
        ):
            w.configure(bg=bg)
        self._describe_box.configure(
            highlightbackground=look.desc_border,
            highlightcolor=look.desc_border,
            highlightthickness=1,
        )
        self._home_title.configure(bg=look.panel, fg=look.line)
        self._tabs_label.configure(bg=look.bg, fg=look.muted)
        self._title.configure(bg=look.panel, fg=look.line)
        self._path.configure(bg=look.panel, fg=look.muted)
        self._status.configure(bg=look.board, fg=look.line)
        self._describe.configure(bg=look.bg, fg=look.caption)

    def _home_layer(self) -> FocusLayer:
        return FocusLayer(
            id="home",
            title="Home",
            hint="Left rail = areas. Top tabs = siblings once you're inside.",
            actions=[
                FocusAction(
                    key="D",
                    label="Describe the Feel",
                    run=self._open_describe,
                    describe="Dense screen mockups under the current colour scheme.",
                ),
                FocusAction(
                    key="C",
                    label="Change Colour Scheme",
                    run=self._open_theme,
                    describe="Family rooms → looks. Type → Bracket is the colour favorite so far.",
                ),
                FocusAction(
                    key="S",
                    label="Change Structure",
                    run=self._open_structure,
                    describe="Experiment: top-down, left→right, or collapsed Esc summaries.",
                ),
            ],
            current=self._area_title(),
        )

    def _area_title(self) -> str:
        stage = stage_by_id(self._area)
        return stage.title if stage else self._area

    # --- describe / screens --------------------------------------------------

    def _open_describe(self) -> None:
        self._area = "describe_feel"
        self._stack = [self._home_layer(), self._screen_picker()]
        if self._structure == "folder_tree":
            self._tree_roots = self._describe_tree()
            self._tree_path = []
        else:
            self._tree_roots = []
            self._tree_path = []
        self._set_status("LIVE · Screen showcases")
        self._set_describe(
            "Sub-tabs are screens. Expand one to taste density underneath — neighbours stay in the list."
        )
        self._render()

    def _describe_tree(self) -> list[TreeItem]:
        screens = (
            ("1", "Flight Deck", "deck"),
            ("2", "Atom Create", "create"),
            ("3", "Molecule Lab", "molecule"),
            ("4", "Idle Lab chrome", "idle"),
            ("5", "Live Overlay", "overlay"),
            ("6", "Observation", "observe"),
            ("7", "Settings", "settings"),
        )
        roots: list[TreeItem] = []
        for key, label, sid in screens:
            layer = {
                "deck": self._screen_deck,
                "create": self._screen_create,
                "molecule": self._screen_molecule,
                "idle": self._screen_idle,
                "overlay": self._screen_overlay,
                "observe": self._screen_observe,
                "settings": self._screen_settings,
            }[sid]()
            kids = tuple(
                TreeItem(
                    id=f"{sid}:{a.key}",
                    key=a.key,
                    title=a.label,
                    describe=a.describe,
                    activate=a.run,
                )
                for a in layer.actions
            )
            roots.append(TreeItem(id=sid, key=key, title=label, describe=f"Open {label} density.", children=kids))
        return roots

    def _screen_picker(self) -> FocusLayer:
        screens = (
            ("1", "Flight Deck", "deck", "Top accordion + expanded leaves — hotkey density."),
            ("2", "Atom Create", "create", "Basic Gesture / Playbook / Edit + gesture leaves."),
            ("3", "Molecule Lab", "molecule", "Atom library + compose + trial — many rows."),
            ("4", "Idle Lab chrome", "idle", "Tabs + transport + status — mouse home."),
            ("5", "Live Overlay", "overlay", "Map tools + marks + describe — hands on glass."),
            ("6", "Observation", "observe", "Capture / review / mission panes."),
            ("7", "Settings", "settings", "Boot, keys, humanize, honesty toggles."),
        )
        return FocusLayer(
            id="showcase:picker",
            title="Screen showcases",
            hint="Each number opens a busy mock under the current colour scheme.",
            current="",
            actions=[
                FocusAction(
                    key=key,
                    label=label,
                    run=lambda sid=sid, lab=label: self._open_screen(sid, lab),
                    describe=desc,
                )
                for key, label, sid, desc in screens
            ],
        )

    def _open_screen(self, screen_id: str, title: str) -> None:
        builders = {
            "deck": self._screen_deck,
            "create": self._screen_create,
            "molecule": self._screen_molecule,
            "idle": self._screen_idle,
            "overlay": self._screen_overlay,
            "observe": self._screen_observe,
            "settings": self._screen_settings,
        }
        builder = builders.get(screen_id)
        if not builder:
            return
        self._stack = [self._home_layer(), self._screen_picker(), builder()]
        self._stack[1].current = title
        self._set_status(f"LIVE · {title}")
        self._set_describe(f"{title} mock — judge density under {self._look.title}. Esc peels.")
        self._render()

    def _leaf_actions(self, items: list[tuple[str, str, str]]) -> list[FocusAction]:
        return [
            FocusAction(
                key=key,
                label=label,
                run=lambda lab=label, d=desc: self._act(lab, d),
                describe=desc,
            )
            for key, label, desc in items
        ]

    def _screen_deck(self) -> FocusLayer:
        return FocusLayer(
            id="screen:deck",
            title="Flight Deck",
            hint="Dense Deck leaves for tasting.",
            actions=self._leaf_actions(
                [
                    ("L", "Labs", "Labs accordion root."),
                    ("M", "Molecules", "Molecules accordion root."),
                    ("O", "Observe", "Observation float."),
                    ("I", "Idle Lab", "Open Idle Lab (closes Deck)."),
                    ("S", "Settings", "Settings accordion."),
                    ("X", "Collapse", "Collapse open accordion."),
                    ("1", "Start Live", "L→1 Start Live Overlay."),
                    ("2", "Toggle Console", "L→2 console."),
                    ("3", "Verbosity", "L→3 console verbosity."),
                    ("4", "Molecule Lab", "M→1 float."),
                    ("5", "Atom Lab", "M→2 library."),
                    ("6", "Create Atom", "M→3 create."),
                ]
            ),
        )

    def _screen_create(self) -> FocusLayer:
        return FocusLayer(
            id="screen:create",
            title="Atom Create",
            hint="Create surface density.",
            actions=self._leaf_actions(
                [
                    ("B", "Basic Gesture", "Expand gesture types."),
                    ("P", "Playbook", "Rewrite from note."),
                    ("E", "Edit", "Edit current atom."),
                    ("1", "Click", "Click gesture."),
                    ("2", "Drag", "Drag gesture."),
                    ("3", "Key", "Key gesture."),
                    ("4", "OCR", "OCR crop."),
                    ("5", "Mode Single", "Toggle Single."),
                    ("6", "Mode Spam", "Toggle Spam."),
                ]
            ),
        )

    def _screen_molecule(self) -> FocusLayer:
        return FocusLayer(
            id="screen:molecule",
            title="Molecule Lab",
            hint="Library + compose density.",
            actions=self._leaf_actions(
                [
                    ("A", "Atom pane", "Switch Atom."),
                    ("M", "Molecule pane", "Switch Molecule."),
                    ("T", "Trial pane", "Switch Trial."),
                    ("1", "tab_attack", "Atom: open Attack."),
                    ("2", "buy_damage", "Atom: buy Damage."),
                    ("C", "Compose", "Add child to molecule."),
                    ("V", "Validate", "Dry-run pack."),
                    ("R", "Run trial", "Start trial once."),
                ]
            ),
        )

    def _screen_idle(self) -> FocusLayer:
        return FocusLayer(
            id="screen:idle",
            title="Idle Lab chrome",
            hint="Mouse home density.",
            actions=self._leaf_actions(
                [
                    ("1", "Info", "Info tab."),
                    ("2", "Live Overlay Lab", "LOL tab."),
                    ("3", "Molecule Lab", "ML tab."),
                    ("4", "Observation Lab", "OL tab."),
                    ("A", "Anchor", "Anchor target window."),
                    ("R", "Refresh", "Reload data files."),
                    ("E", "Restart", "Reload code."),
                    ("F", "Open Flight Deck", "Close Lab → Deck."),
                ]
            ),
        )

    def _screen_overlay(self) -> FocusLayer:
        return FocusLayer(
            id="screen:overlay",
            title="Live Overlay",
            hint="Hands on glass.",
            actions=self._leaf_actions(
                [
                    ("1", "Select map", "tower_main_gameplay."),
                    ("2", "Start live", "Enter live overlay."),
                    ("3", "Add mark", "Place object mark."),
                    ("D", "Hold describe", "Describe overlay keys."),
                    ("X", "Esc exit", "Leave live (not Deactivate)."),
                ]
            ),
        )

    def _screen_observe(self) -> FocusLayer:
        return FocusLayer(
            id="screen:observe",
            title="Observation Lab",
            hint="Capture / mission density.",
            actions=self._leaf_actions(
                [
                    ("U", "User pane", "User capture/review."),
                    ("A", "AI pane", "AI mission."),
                    ("1", "Start capture", "Begin batch."),
                    ("2", "Stop capture", "End batch."),
                    ("3", "Today", "Date group."),
                ]
            ),
        )

    def _screen_settings(self) -> FocusLayer:
        return FocusLayer(
            id="screen:settings",
            title="Settings",
            hint="Prefs as leaves.",
            actions=self._leaf_actions(
                [
                    ("1", "Boot Idle Lab", "Prefer Lab on Restart."),
                    ("2", "Boot Flight Deck", "Prefer Deck on Restart."),
                    ("3", "Activate key", "Remap `."),
                    ("5", "Humanize Off", "Default."),
                ]
            ),
        )

    def _act(self, name: str, detail: str) -> None:
        self._set_status(f"Did · {name}")
        self._set_describe(detail)

    # --- colour scheme -------------------------------------------------------

    def _open_theme(self) -> None:
        self._area = "change_theme"
        stage = stage_by_id("change_theme")
        assert stage is not None
        fam = family_for_look(self._look.id)
        self._tree_roots = self._colour_tree()
        # Open on current family so siblings Thread/Rim/… stay visible around it
        self._tree_path = [fam.id] if fam else ["type"]
        self._stack = [
            self._home_layer(),
            FocusLayer(
                id="stage:change_theme",
                title="Change Colour Scheme",
                hint="Sub-tabs stay in the list. Expand one — looks nest under it; neighbours remain above/below.",
                current=fam.title if fam else "Type",
            ),
        ]
        self._set_status(f"Colour · {(fam.title if fam else 'Type')} open")
        self._set_describe(
            "1–4 pick a family — siblings stay above/below. "
            "Looks nest underneath (A S D F …). Enter pins main. Esc collapses."
        )
        self._render()

    def _colour_tree(self) -> list[TreeItem]:
        main_id = get_main_look_id()
        look_keys = "asdfgh"
        roots: list[TreeItem] = []
        for family in FAMILIES:
            kids: list[TreeItem] = []
            for i, look in enumerate(ordered_looks(family, main_id)):
                tag = " · main" if look.id == main_id else ""
                kids.append(
                    TreeItem(
                        id=look.id,
                        key=look_keys[i] if i < len(look_keys) else str(i + 1),
                        title=f"{look.title}{tag}",
                        describe=look.blurb
                        + (
                            "  Enter pins main (#1)."
                            if look.id == self._look.id
                            else "  Press to preview · Enter pins main."
                        ),
                        activate=lambda lid=look.id: self._apply_look(lid),
                        is_new=(look.id == main_id),
                    )
                )
            roots.append(
                TreeItem(
                    id=family.id,
                    key=family.key,
                    title=family.title,
                    describe=family.blurb,
                    children=tuple(kids),
                )
            )
        return roots

    def _apply_look(self, look_id: str) -> None:
        self._look = theme_by_id(look_id)
        save_pick("change_theme", look_id)
        self._picks = load_picks().get("picks", {})
        fam = family_for_look(look_id)
        if fam is not None:
            self._tree_path = [fam.id]
        self._tree_roots = self._colour_tree()
        self._paint_chrome()
        self._set_status(f"Look · {self._look.title}")
        self._set_describe(
            f"Previewing {self._look.title}. {self._look.blurb}  "
            f"Press Enter to set as main (#1). Neighbour families stay in the list."
        )
        self._render()

    def _pin_main_look(self) -> None:
        if self._area != "change_theme" or not self._tree_path:
            return
        look_id = self._look.id
        set_main_look(look_id)
        self._picks = load_picks().get("picks", {})
        self._tree_roots = self._colour_tree()
        self._set_status(f"Main · {self._look.title} → #1")
        self._set_describe(f"{self._look.title} is now main (#1). It leads its family list.")
        self._render()

    # --- structure experiments -----------------------------------------------

    def _open_structure(self) -> None:
        self._area = "change_structure"
        stage = stage_by_id("change_structure")
        assert stage is not None
        self._stack = [
            self._home_layer(),
            FocusLayer(
                id="stage:change_structure",
                title="Change Structure",
                hint=stage.question,
                current=self._structure.replace("_", " "),
            ),
        ]
        if self._structure == "folder_tree":
            self._tree_roots = self._structure_tree()
            self._tree_path = ["projects"]  # open one branch so siblings Labs/Archive stay visible
            self._set_status("Structure · folder tree")
            self._set_describe(
                "Accordion folders: expand one, children appear under it; "
                "siblings stay above/below. Esc collapses one level."
            )
        else:
            self._tree_roots = []
            self._tree_path = []
            self._stack = [self._home_layer(), self._structure_picker()]
            self._set_status("LIVE · Change Structure")
            self._set_describe(stage.question)
        self._render()

    def _structure_tree(self) -> list[TreeItem]:
        """Sample nest + layout switcher as a quiet first folder."""
        stage = stage_by_id("change_structure")
        layout_kids: list[TreeItem] = []
        if stage:
            for v in stage.variants:
                layout_kids.append(
                    TreeItem(
                        id=v.id,
                        key=v.key,
                        title=v.title + (" · on" if v.id == self._structure else ""),
                        describe=v.blurb,
                        activate=lambda vid=v.id: self._pick_structure(vid),
                        is_new=(v.id == self._structure),
                    )
                )

        def leaf(title: str) -> TreeItem:
            return TreeItem(
                id=f"leaf:{title}",
                key="1",
                title=title,
                describe=f"Leaf · {title}",
                activate=lambda t=title: self._act(t, f"Leaf · {t} (end of nest)."),
            )

        return [
            TreeItem(
                id="layouts",
                key="0",
                title="Layouts",
                describe="Contrast structure experiments.",
                children=tuple(layout_kids),
            ),
            TreeItem(
                id="projects",
                key="1",
                title="Projects",
                describe="Projects folder.",
                children=(
                    TreeItem(
                        id="idle",
                        key="1",
                        title="Idle Lab",
                        describe="Idle Lab folder.",
                        children=(leaf("src"), TreeItem(id="docs", key="2", title="docs", describe="docs", activate=lambda: self._act("docs", "Leaf · docs"))),
                    ),
                    TreeItem(
                        id="feel",
                        key="2",
                        title="Feel Lab",
                        describe="Feel Lab folder.",
                        children=(
                            TreeItem(id="themes", key="1", title="themes", describe="themes", activate=lambda: self._act("themes", "Leaf · themes")),
                            TreeItem(id="structure", key="2", title="structure", describe="structure", activate=lambda: self._act("structure", "Leaf · structure")),
                        ),
                    ),
                    TreeItem(
                        id="notes",
                        key="3",
                        title="Notes",
                        describe="Notes folder.",
                        children=(TreeItem(id="scratch", key="1", title="scratch", describe="scratch", activate=lambda: self._act("scratch", "Leaf · scratch")),),
                    ),
                ),
            ),
            TreeItem(
                id="labs",
                key="2",
                title="Labs",
                describe="Labs folder.",
                children=(
                    TreeItem(id="mol", key="1", title="Molecule", describe="Molecule", children=(TreeItem(id="atoms", key="1", title="atoms", describe="atoms", activate=lambda: self._act("atoms", "Leaf · atoms")),)),
                    TreeItem(id="obs", key="2", title="Observation", describe="Observation", children=(TreeItem(id="batches", key="1", title="batches", describe="batches", activate=lambda: self._act("batches", "Leaf · batches")),)),
                ),
            ),
            TreeItem(
                id="archive",
                key="3",
                title="Archive",
                describe="Archive folder.",
                children=(
                    TreeItem(
                        id="cut",
                        key="1",
                        title="2026-11 cut",
                        describe="Cut demos.",
                        children=(TreeItem(id="demos", key="1", title="demos", describe="demos", activate=lambda: self._act("demos", "Leaf · demos")),),
                    ),
                ),
            ),
        ]

    def _structure_picker(self) -> FocusLayer:
        stage = stage_by_id("change_structure")
        assert stage is not None
        actions = []
        for v in stage.variants:
            actions.append(
                FocusAction(
                    key=v.key,
                    label=v.title + (" · on" if v.id == self._structure else ""),
                    run=lambda vid=v.id: self._pick_structure(vid),
                    describe=v.blurb,
                    is_new=(v.id == self._structure),
                )
            )
        return FocusLayer(
            id="stage:change_structure",
            title="Change Structure",
            hint="1 Folder tree (main) · 2 Top-down · 3 Left→right · 4 Collapse.",
            actions=actions,
            current=self._structure.replace("_", " "),
        )

    def _pick_structure(self, mode_id: str) -> None:
        if mode_id not in {"folder_tree", "top_down", "left_right", "collapse"}:
            return
        self._structure = mode_id  # type: ignore[assignment]
        save_pick("change_structure", mode_id)
        self._picks = load_picks().get("picks", {})
        self._open_structure()

    # --- keys / peel ---------------------------------------------------------

    def _on_key(self, event) -> None:
        if self._nav_busy:
            return
        key = (event.keysym or "").lower()
        char = event.char or ""
        if key == "escape":
            self._peel()
            return
        if key in {"return", "kp_enter"}:
            if self._area == "change_theme" and self._structure == "folder_tree":
                self._nav_busy = True
                try:
                    self._pin_main_look()
                finally:
                    self.after(1, self._clear_busy)
            return
        token = char.lower() if char and char.isprintable() else key
        # Home rail keys always available
        home = self._home_layer()
        for action in home.actions:
            if action.key.lower() == token.lower():
                self._nav_busy = True
                try:
                    if action.describe:
                        self._set_describe(action.describe)
                    action.run()
                finally:
                    self.after(1, self._clear_busy)
                return
        fn = self._keymap.get(token) or self._keymap.get(token.upper())
        if not fn:
            return
        self._nav_busy = True
        try:
            fn()
        finally:
            self.after(1, self._clear_busy)

    def _clear_busy(self) -> None:
        self._nav_busy = False

    def _peel(self) -> None:
        if self._structure == "folder_tree" and self._tree_path:
            self._tree_path = self._tree_path[:-1]
            self._set_status("Esc · collapsed one folder")
            self._set_describe(
                "Collapsed. Sibling sub-tabs stay in the list — expand another, or Esc again."
                if self._tree_path
                else "All folders collapsed. 1–4 (or listed keys) expand a sub-tab."
            )
            self._render()
            return
        if len(self._stack) <= 1:
            self._set_status("Home · already here")
            self._set_describe("Pick an area from the left rail: D · C · S.")
            self._render()
            return
        self._stack.pop()
        live = self._stack[-1]
        self._set_status(f"Esc · LIVE · {live.title}")
        self._set_describe(live.hint or f"Back on {live.title}.")
        self._render()

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _set_describe(self, text: str) -> None:
        self._describe.configure(text=text)

    # --- render --------------------------------------------------------------

    def _render(self) -> None:
        look = self._look
        self._path.configure(text=" › ".join(L.title for L in self._stack))
        self._keymap = {}
        self._paint_chrome()
        self._render_home_rail()
        self._render_top_tabs()
        self._render_stack()

    def _render_home_rail(self) -> None:
        look = self._look
        home = self._home_layer()
        while len(self._home_btns) < len(home.actions):
            self._home_btns.append(KeyBtn(self._home_list))
        for i, btn in enumerate(self._home_btns):
            btn.pack_forget()
            if i >= len(home.actions):
                continue
            action = home.actions[i]
            btn.bind_action(action, self._set_describe)
            selected = (
                (self._area == "describe_feel" and action.key == "D")
                or (self._area == "change_theme" and action.key == "C")
                or (self._area == "change_structure" and action.key == "S")
            )
            btn._always_click = True  # noqa: SLF001 — explorer rail always clickable
            btn.set_mode("live" if selected else "return", look)
            if not selected:
                # Quiet plate but keep keys visible for muscle memory
                btn._key_lbl.configure(text=_format_key(look, action.key), fg=look.return_text)  # noqa: SLF001
            btn.pack(fill="x", pady=3)

    def _render_top_tabs(self) -> None:
        look = self._look
        for btn in self._top_tab_btns:
            btn.pack_forget()

        # Folder tree owns nesting — top sibling tabs fight the expand-underneath feel.
        if self._structure == "folder_tree":
            self._tabs_label.configure(text="Folder tree · expand underneath (top tabs off)")
            return

        tabs: list[FocusAction] = []
        if self._area == "change_theme":
            for family in FAMILIES:
                tabs.append(
                    FocusAction(
                        key=family.key,
                        label=family.title,
                        run=lambda fid=family.id: self._open_family(fid),
                        describe=family.blurb,
                    )
                )
            self._tabs_label.configure(text="Colour families")
        elif self._area == "change_structure":
            stage = stage_by_id("change_structure")
            if stage:
                for v in stage.variants:
                    tabs.append(
                        FocusAction(
                            key=v.key,
                            label=v.title,
                            run=lambda vid=v.id: self._pick_structure(vid),
                            describe=v.blurb,
                        )
                    )
            self._tabs_label.configure(text="Structure experiments")
        elif self._area == "describe_feel":
            # Screen showcase siblings as tabs when deeper
            picker = self._screen_picker()
            tabs = list(picker.actions)
            self._tabs_label.configure(text="Screen showcases")
        else:
            self._tabs_label.configure(text="Area")

        while len(self._top_tab_btns) < len(tabs):
            self._top_tab_btns.append(KeyBtn(self._tabs_row))

        # Which tab is selected?
        selected_keys: set[str] = set()
        if self._area == "change_theme" and len(self._stack) >= 3 and self._stack[-1].id.startswith("looks:"):
            selected_keys.add(self._stack[-1].id.split(":", 1)[1])
            # map family id → key via FAMILIES
            fam = family_by_id(self._stack[-1].id.split(":", 1)[1])
            if fam:
                selected_keys = {fam.key}
        elif self._area == "change_theme" and len(self._stack) >= 2:
            # on family list — none deep-selected
            selected_keys = set()
        elif self._area == "change_structure":
            stage = stage_by_id("change_structure")
            if stage:
                for v in stage.variants:
                    if v.id == self._structure:
                        selected_keys.add(v.key)

        for i, action in enumerate(tabs):
            btn = self._top_tab_btns[i]
            btn.bind_action(action, self._set_describe)
            is_sel = action.key in selected_keys
            btn.set_mode("live" if is_sel or not selected_keys else "live", look)
            if selected_keys and not is_sel:
                # quiet tab
                btn.set_mode("live", look)
                btn.configure(highlightthickness=0)
                for w in (btn, btn._body, btn._key_lbl, btn._lab_lbl):  # noqa: SLF001
                    w.configure(bg=look.return_bg)
                btn._key_lbl.configure(fg=look.return_text)  # noqa: SLF001
                btn._lab_lbl.configure(fg=look.return_text)  # noqa: SLF001
            btn.pack(side="left", padx=3, pady=2)
            # Top tabs always keymap when visible (siblings)
            self._keymap[action.key.lower()] = action.run
            self._keymap[action.key.upper()] = action.run

        for j in range(len(tabs), len(self._top_tab_btns)):
            self._top_tab_btns[j].pack_forget()

    def _render_stack(self) -> None:
        look = self._look
        body_layers = self._stack[1:]  # home lives in left rail

        # Clear previous packs
        for strip in self._strips:
            strip.pack_forget()
        for chip in self._esc_chips:
            chip.pack_forget()
        for folder in self._folders:
            folder.pack_forget()

        if not body_layers:
            return

        if self._structure == "folder_tree":
            self._tree_host.pack(fill="both", expand=True)
            self._render_accordion(look)
            return

        self._tree_host.pack_forget()
        use_collapse = self._structure == "collapse"
        use_lr = self._structure == "left_right"

        # Ensure widgets
        while len(self._strips) < len(body_layers):
            self._strips.append(LayerStrip(self._stack_host, self._set_describe))
        while len(self._esc_chips) < len(body_layers):
            self._esc_chips.append(EscSummary(self._stack_host))

        live_index = len(body_layers) - 1

        for i, layer in enumerate(body_layers):
            is_live = i == live_index
            is_return = i == live_index - 1
            if is_live:
                mode: Mode = "live"
            elif is_return:
                mode = "return"
            else:
                mode = "dorm"

            if use_collapse and not is_live:
                chip = self._esc_chips[i]
                current = layer.current or (self._look.title if layer.id.startswith("stage:change_theme") else "")
                if layer.id.startswith("looks:"):
                    current = self._look.title
                chip.show(layer.title, current, look)
                if use_lr:
                    chip.pack(side="left", fill="y", padx=4, pady=4)
                else:
                    chip.pack(fill="x", pady=4)
                continue

            if mode == "dorm" and not use_collapse:
                chip = self._esc_chips[i]
                chip.show(layer.title, layer.current, look)
                if use_lr:
                    chip.pack(side="left", fill="y", padx=4, pady=4)
                else:
                    chip.pack(fill="x", pady=4)
                continue

            strip = self._strips[i]
            strip.show_layer(layer, mode, look)
            if use_lr:
                strip.pack(side="left", fill="both", expand=is_live, padx=4, pady=4)
            else:
                strip.pack(fill="x", pady=6)

            if mode == "live":
                for action in layer.actions:
                    self._keymap[action.key.lower()] = action.run
                    self._keymap[action.key.upper()] = action.run

    def _render_accordion(self, look: Look) -> None:
        """All siblings stay in the list; the open path expands children underneath."""
        for child in self._tree_host.winfo_children():
            child.destroy()
        self._folders.clear()
        if not self._tree_roots:
            return
        # Keys bind to the deepest open level's children (or roots if nothing open)
        active = self._active_tree_items()
        active_ids = {item.id for item in active}
        self._pack_accordion_level(
            self._tree_host,
            self._tree_roots,
            path_prefix=[],
            depth=0,
            look=look,
            active_ids=active_ids,
        )

    def _active_tree_items(self) -> list[TreeItem]:
        items = self._tree_roots
        if not self._tree_path:
            return list(items)
        node: TreeItem | None = None
        for nid in self._tree_path:
            node = next((x for x in items if x.id == nid), None)
            if node is None:
                return list(self._tree_roots)
            items = list(node.children)
        return items if items else list(self._tree_roots)

    def _pack_accordion_level(
        self,
        parent: tk.Frame,
        items: list[TreeItem] | tuple[TreeItem, ...],
        *,
        path_prefix: list[str],
        depth: int,
        look: Look,
        active_ids: set[str],
    ) -> None:
        open_id = self._tree_path[len(path_prefix)] if len(self._tree_path) > len(path_prefix) else None
        for item in items:
            expanded = open_id == item.id
            is_leaf = not item.children
            selected_leaf = is_leaf and self._area == "change_theme" and item.id == self._look.id
            live = expanded or selected_leaf

            def make_header(it: TreeItem = item, prefix: list[str] = list(path_prefix)) -> Callable[[], None]:
                def _go() -> None:
                    self._tree_activate(it, prefix)
                return _go

            key_prefix = _format_key(look, item.key)
            title = f"{key_prefix}  {item.title}"
            current = self._look.title if expanded and self._area == "change_theme" and item.children else ""

            row = FolderBranch(parent)
            self._folders.append(row)
            row.show(
                title=title,
                depth=depth,
                look=look,
                expanded=expanded,
                live=live,
                current=current,
                actions=None,
                on_focus_desc=self._set_describe,
                on_header=make_header(),
                keymap={},
            )

            # Neighbour siblings (same level, not open): visible but quieter — depth context
            if not expanded and not selected_leaf and open_id is not None:
                bg, border, _, _ = _depth_plate(look, depth, live=False)
                row._header.configure(bg=bg, highlightbackground=border, highlightcolor=border)  # noqa: SLF001
                row._chev.configure(bg=bg, fg=look.muted, text="▸")  # noqa: SLF001
                row._title.configure(bg=bg, fg=look.muted, text=title)  # noqa: SLF001
                row._meta.configure(bg=bg, fg=look.dorm_text, text="")  # noqa: SLF001
            elif expanded:
                row._meta.configure(text="open")  # noqa: SLF001
            elif selected_leaf:
                row._chev.configure(text="●")  # noqa: SLF001
                row._meta.configure(text="selected")  # noqa: SLF001
            elif item.id in active_ids and is_leaf:
                # Active look choices under an open family — readable, not abandoned
                bg, border, key_fg, text_fg = _depth_plate(look, depth, live=True)
                row._header.configure(bg=bg, highlightbackground=border, highlightcolor=border)  # noqa: SLF001
                row._chev.configure(bg=bg, fg=key_fg, text="·")  # noqa: SLF001
                row._title.configure(bg=bg, fg=text_fg, text=title)  # noqa: SLF001
                row._meta.configure(bg=bg, fg=look.caption, text="")  # noqa: SLF001

            row.pack(fill="x", padx=(depth * 16, 4), pady=2)

            if item.id in active_ids:
                self._keymap[item.key.lower()] = make_header()
                self._keymap[item.key.upper()] = make_header()

            # Colour families (and other root folders): digits always switch which sibling is open
            if depth == 0 and item.children:
                self._keymap[item.key.lower()] = make_header()
                self._keymap[item.key.upper()] = make_header()

            if expanded and item.children:
                nest = tk.Frame(parent, bg=look.bg)
                nest.pack(fill="x", padx=(depth * 16 + 10, 4), pady=(0, 4))
                self._pack_accordion_level(
                    nest,
                    item.children,
                    path_prefix=path_prefix + [item.id],
                    depth=depth + 1,
                    look=look,
                    active_ids=active_ids,
                )

    def _tree_activate(self, item: TreeItem, path_prefix: list[str]) -> None:
        if item.describe:
            self._set_describe(item.describe)
        if item.children:
            self._tree_path = path_prefix + [item.id]
            self._set_status(f"Open · {item.title}")
            self._set_describe(
                f"{item.title} expanded — children underneath. "
                f"Siblings stay in the list above/below. {item.describe}"
            )
            self._render()
            return
        if item.activate:
            item.activate()
            return
        self._act(item.title, item.describe or item.title)
