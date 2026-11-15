"""Fold a Feel Lab Look into CustomTkinter theme + existing widget trees."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look


def _pair(color: str) -> list[str]:
    """CTk theme values are [light, dark] — we pin both to the look color."""

    return [color, color]


def apply_ctk_theme(look: Look) -> None:
    """Retarget CTk defaults so new lab widgets inherit the shell look."""

    try:
        ctk.set_appearance_mode("dark" if look.style in {"type", "rail"} else "system")
    except Exception:
        pass
    theme = ctk.ThemeManager.theme
    try:
        theme["CTk"]["fg_color"] = _pair(look.bg)
        theme["CTkToplevel"]["fg_color"] = _pair(look.bg)
        theme["CTkFrame"]["fg_color"] = _pair(look.panel)
        theme["CTkFrame"]["top_fg_color"] = _pair(look.board)
        theme["CTkFrame"]["border_color"] = _pair(look.desc_border)
        theme["CTkFrame"]["border_width"] = 1 if look.style == "type" else 0
        theme["CTkButton"]["fg_color"] = _pair(look.live_bg)
        theme["CTkButton"]["hover_color"] = _pair(look.live_hover)
        theme["CTkButton"]["text_color"] = _pair(look.live_text)
        theme["CTkButton"]["border_color"] = _pair(look.live_border)
        theme["CTkButton"]["border_width"] = 1 if look.style == "type" else 0
        theme["CTkButton"]["text_color_disabled"] = _pair(look.dorm_text)
        theme["CTkLabel"]["text_color"] = _pair(look.line)
        theme["CTkEntry"]["fg_color"] = _pair(look.board)
        theme["CTkEntry"]["border_color"] = _pair(look.desc_border)
        theme["CTkEntry"]["text_color"] = _pair(look.line)
        theme["CTkEntry"]["placeholder_text_color"] = _pair(look.muted)
        theme["CTkTextbox"]["fg_color"] = _pair(look.board)
        theme["CTkTextbox"]["border_color"] = _pair(look.desc_border)
        theme["CTkTextbox"]["text_color"] = _pair(look.line)
        theme["CTkTextbox"]["scrollbar_button_color"] = _pair(look.dorm_bg)
        theme["CTkTextbox"]["scrollbar_button_hover_color"] = _pair(look.live_hover)
        theme["CTkOptionMenu"]["fg_color"] = _pair(look.live_bg)
        theme["CTkOptionMenu"]["button_color"] = _pair(look.live_hover)
        theme["CTkOptionMenu"]["button_hover_color"] = _pair(look.live_border)
        theme["CTkOptionMenu"]["text_color"] = _pair(look.live_text)
        theme["CTkComboBox"]["fg_color"] = _pair(look.board)
        theme["CTkComboBox"]["border_color"] = _pair(look.desc_border)
        theme["CTkComboBox"]["button_color"] = _pair(look.dorm_bg)
        theme["CTkComboBox"]["button_hover_color"] = _pair(look.live_hover)
        theme["CTkComboBox"]["text_color"] = _pair(look.line)
        theme["CTkScrollableFrame"]["label_fg_color"] = _pair(look.panel)
        theme["CTkScrollbar"]["button_color"] = _pair(look.dorm_bg)
        theme["CTkScrollbar"]["button_hover_color"] = _pair(look.live_hover)
        theme["CTkProgressBar"]["fg_color"] = _pair(look.board)
        theme["CTkProgressBar"]["progress_color"] = _pair(look.live_border)
        theme["CTkSlider"]["fg_color"] = _pair(look.board)
        theme["CTkSlider"]["progress_color"] = _pair(look.live_border)
        theme["CTkSlider"]["button_color"] = _pair(look.live_bg)
        theme["CTkSlider"]["button_hover_color"] = _pair(look.live_hover)
        theme["CTkSwitch"]["fg_color"] = _pair(look.dorm_bg)
        theme["CTkSwitch"]["progress_color"] = _pair(look.live_border)
        theme["CTkSwitch"]["button_color"] = _pair(look.live_text)
        theme["CTkSwitch"]["button_hover_color"] = _pair(look.line)
        theme["CTkCheckBox"]["fg_color"] = _pair(look.live_bg)
        theme["CTkCheckBox"]["hover_color"] = _pair(look.live_hover)
        theme["CTkCheckBox"]["border_color"] = _pair(look.desc_border)
        theme["CTkCheckBox"]["text_color"] = _pair(look.line)
        theme["CTkRadioButton"]["fg_color"] = _pair(look.live_bg)
        theme["CTkRadioButton"]["hover_color"] = _pair(look.live_hover)
        theme["CTkRadioButton"]["border_color"] = _pair(look.desc_border)
        theme["CTkRadioButton"]["text_color"] = _pair(look.line)
        theme["CTkSegmentedButton"]["fg_color"] = _pair(look.board)
        theme["CTkSegmentedButton"]["selected_color"] = _pair(look.live_bg)
        theme["CTkSegmentedButton"]["selected_hover_color"] = _pair(look.live_hover)
        theme["CTkSegmentedButton"]["unselected_color"] = _pair(look.dorm_bg)
        theme["CTkSegmentedButton"]["unselected_hover_color"] = _pair(look.live_hover)
        theme["CTkSegmentedButton"]["text_color"] = _pair(look.live_text)
        theme["DropdownMenu"]["fg_color"] = _pair(look.panel)
        theme["DropdownMenu"]["hover_color"] = _pair(look.live_hover)
        theme["DropdownMenu"]["text_color"] = _pair(look.line)
    except Exception:
        pass


def primary_button_kwargs(look: Look) -> dict[str, Any]:
    return {
        "fg_color": look.live_bg,
        "hover_color": look.live_hover,
        "text_color": look.live_text,
        "border_width": 1 if look.style == "type" else 0,
        "border_color": look.live_border,
    }


def dormant_button_kwargs(look: Look) -> dict[str, Any]:
    return {
        "fg_color": look.dorm_bg,
        "hover_color": look.live_hover,
        "text_color": look.caption,
        "border_width": 1 if look.style == "type" else 0,
        "border_color": look.desc_border,
    }


def panel_kwargs(look: Look) -> dict[str, Any]:
    return {
        "fg_color": look.panel,
        "border_width": 1 if look.style == "type" else 0,
        "border_color": look.desc_border,
    }


def _norm(color: Any) -> str:
    if isinstance(color, (list, tuple)) and color:
        color = color[-1]
    return str(color or "").strip().lower()


def _is_transparent(color: Any) -> bool:
    c = _norm(color)
    return c in {"", "transparent", "none"}


def _is_default_blue(color: Any) -> bool:
    c = _norm(color)
    return c in {
        "#1f6aa5",
        "#3b8ed0",
        "#36719f",
        "#144870",
        "#27577d",
        "#203a4f",
    }


def _is_stock_grey(color: Any) -> bool:
    c = _norm(color)
    if c.startswith("gray") or c.startswith("grey"):
        return True
    return c in {
        "#141a22",
        "#1b2330",
        "#121820",
        "#1d1e1e",
        "#343638",
        "#2a3140",
        "#2a2a2a",
        "#212121",
        "#1a1a1a",
        "#2b2b2b",
        "#333333",
        "#3a3a3a",
        "#1f2a3a",
        "#3a4558",
        "#3a5a78",
    }


def _is_ok_green(color: Any) -> bool:
    c = _norm(color)
    return c in {"#2f6f5e", "#2f6b4a", "#3a7a5c", "#1e3a4a", "#2a5568"}


def paint_widget_tree(root: Any, look: Look, *, depth: int = 0) -> None:
    """Repaint an existing subtree to match ``look`` (best-effort)."""

    if root is None or depth > 40:
        return
    name = type(root).__name__
    try:
        if name in {"CTkFrame", "CTkScrollableFrame"}:
            fg = root.cget("fg_color") if hasattr(root, "cget") else None
            if not _is_transparent(fg):
                target = look.board if "Scrollable" in name else look.panel
                if _is_stock_grey(fg) or _is_default_blue(fg) or depth == 0:
                    kwargs = {"fg_color": target}
                    if look.style == "type" and name == "CTkFrame":
                        try:
                            # Keep thin type borders on solid panels.
                            if int(root.cget("border_width") or 0) >= 0 and not _is_transparent(
                                root.cget("border_color")
                            ):
                                kwargs["border_color"] = look.desc_border
                        except Exception:
                            pass
                    root.configure(**kwargs)
        elif name == "CTkLabel":
            tc = root.cget("text_color") if hasattr(root, "cget") else None
            if _is_stock_grey(tc) or _norm(tc) in {"#dce4ee", "#e8eef6", "#9aa4b2", "#7e8796"}:
                # Muted greys → muted; bright → line
                root.configure(
                    text_color=look.muted
                    if _norm(tc) in {"#9aa4b2", "#7e8796"} or "gray" in _norm(tc)
                    else look.line
                )
        elif name == "CTkButton":
            fg = root.cget("fg_color") if hasattr(root, "cget") else None
            if _is_transparent(fg):
                root.configure(text_color=look.dorm_text, hover_color=look.live_hover)
            elif _is_ok_green(fg):
                root.configure(
                    fg_color=look.live_border,
                    hover_color=look.live_hover,
                    text_color=look.live_text,
                )
            elif _is_default_blue(fg) or _is_stock_grey(fg):
                # Prefer dormant for dark greys, live for blues / primary actions.
                if _is_default_blue(fg):
                    root.configure(**primary_button_kwargs(look))
                else:
                    root.configure(**dormant_button_kwargs(look))
        elif name in {"CTkEntry", "CTkTextbox"}:
            root.configure(
                fg_color=look.board,
                border_color=look.desc_border,
                text_color=look.line,
            )
        elif name == "CTkOptionMenu":
            root.configure(
                fg_color=look.live_bg,
                button_color=look.live_hover,
                button_hover_color=look.live_border,
                text_color=look.live_text,
            )
        elif name == "CTkComboBox":
            root.configure(
                fg_color=look.board,
                border_color=look.desc_border,
                button_color=look.dorm_bg,
                button_hover_color=look.live_hover,
                text_color=look.line,
            )
        elif name in {"CTkCheckBox", "CTkRadioButton"}:
            root.configure(
                fg_color=look.live_bg,
                hover_color=look.live_hover,
                border_color=look.desc_border,
                text_color=look.line,
            )
        elif name == "CTkSwitch":
            root.configure(
                fg_color=look.dorm_bg,
                progress_color=look.live_border,
                button_color=look.live_text,
                button_hover_color=look.line,
                text_color=look.line,
            )
        elif name == "CTkProgressBar":
            root.configure(fg_color=look.board, progress_color=look.live_border)
        elif name == "CTkSlider":
            root.configure(
                fg_color=look.board,
                progress_color=look.live_border,
                button_color=look.live_bg,
                button_hover_color=look.live_hover,
            )
        elif name == "CTkSegmentedButton":
            root.configure(
                fg_color=look.board,
                selected_color=look.live_bg,
                selected_hover_color=look.live_hover,
                unselected_color=look.dorm_bg,
                unselected_hover_color=look.live_hover,
                text_color=look.live_text,
            )
    except Exception:
        pass
    try:
        children = root.winfo_children()
    except Exception:
        return
    for child in children:
        paint_widget_tree(child, look, depth=depth + 1)


def paint_lab_surfaces(app: Any, look: Look) -> None:
    """Theme defaults + repaint desk panes and known host panels."""

    apply_ctk_theme(look)
    desk = getattr(app, "tabs", None)
    if desk is not None:
        try:
            desk.configure(fg_color=look.bg)
        except Exception:
            pass
        panes = getattr(desk, "_panes", None) or {}
        for pane in panes.values():
            paint_widget_tree(pane, look)
    for attr in (
        "atom_lab_pane",
        "_molecule_composer_pane",
        "auto_panel",
        "screen_map_panel",
        "ai_batch_panel",
        "_action_pane",
        "_condensed_panel",
        "_workspace",
    ):
        widget = getattr(app, attr, None)
        if widget is not None:
            paint_widget_tree(widget, look)
