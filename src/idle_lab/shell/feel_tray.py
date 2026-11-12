"""Info specimen tray — poke the operator feel palette (shape-first draft)."""

from __future__ import annotations

import customtkinter as ctk

_FG = "#1A2030"
_HOVER = "#2A3140"
_ACCENT = "#1E3A4A"
_ACCENT_HOVER = "#2A5568"
_MUTED = "#9AA4B2"
_BODY = "#C5CDD8"
_LINE = "#E8EEF7"


def build_feel_tray(parent) -> ctk.CTkFrame:
    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="x", padx=8, pady=(0, 12))

    ctk.CTkLabel(
        root,
        text="How it talks",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=0, pady=(4, 2))
    ctk.CTkLabel(
        root,
        text="Poke the specimens. Captions appear from doing — not from reading.",
        text_color=_MUTED,
        wraplength=720,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(0, 8))

    line_host = ctk.CTkFrame(root, fg_color=_FG, corner_radius=8)
    line_host.pack(fill="x", pady=(0, 10))
    deck_line = ctk.CTkLabel(
        line_host,
        text="Deck line · idle",
        text_color=_LINE,
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    )
    deck_line.pack(fill="x", padx=12, pady=10)

    describe_host = ctk.CTkFrame(root, fg_color="transparent")
    describe_lbl = ctk.CTkLabel(
        describe_host,
        text="",
        text_color="#D4B483",
        wraplength=700,
        justify="left",
        anchor="w",
    )
    describe_lbl.pack(fill="x", padx=4)

    state: dict = {
        "focus": "accordion",
        "describe_on": False,
        "mode": "Single",
        "interval_ms": 100,
        "stack": ["Create"],
        "queue_n": 0,
        "typing": False,
    }

    descriptions = {
        "accordion": "Accordion — letter opens leaves; X collapses; digit picks one action.",
        "toggle": "Toggle leaf — press flips a two-state value. No dialog.",
        "typein": "Type-in leaf — press, type a value, Enter commits, Esc cancels.",
        "hold_d": "Hold D — description only while held. Nothing sticky.",
        "peel": "Esc peel — one layer out. Outer peel saves / exits.",
        "queue": "Queue + glyph — script line and on-board mark stay in sync.",
        "float": "Lab float — lightweight window from Deck energy; Esc returns.",
        "voices": "Two voices — same action as Lab button (mouse) or hotkey leaf (Deck).",
    }

    def set_line(text: str) -> None:
        deck_line.configure(text=text)

    def set_focus(key: str) -> None:
        state["focus"] = key
        if state["describe_on"]:
            describe_lbl.configure(text=descriptions.get(key, ""))

    def show_describe(on: bool) -> None:
        state["describe_on"] = on
        if on:
            describe_host.pack(fill="x", pady=(0, 8), before=grid)
            describe_lbl.configure(text=descriptions.get(state["focus"], ""))
        else:
            describe_host.pack_forget()
            describe_lbl.configure(text="")

    grid = ctk.CTkFrame(root, fg_color="transparent")
    grid.pack(fill="x")
    for col in range(2):
        grid.grid_columnconfigure(col, weight=1, uniform="feel")

    # --- Accordion ---
    acc = _specimen(grid, "Accordion", 0, 0)
    leaves_host = ctk.CTkFrame(acc, fg_color="transparent")
    leaf_btns: list[ctk.CTkButton] = []

    def collapse() -> None:
        set_focus("accordion")
        for b in leaf_btns:
            b.pack_forget()
        leaves_host.pack_forget()
        set_line("Deck line · menu collapsed")

    def expand_b() -> None:
        set_focus("accordion")
        leaves_host.pack(fill="x", pady=(6, 0))
        for b in leaf_btns:
            b.pack(side="left", padx=(0, 6))
        set_line("B · Basic Gesture — pick 1–4")

    def pick_leaf(n: int, name: str) -> None:
        set_focus("accordion")
        set_line(f"B→{n} · {name}")

    row = ctk.CTkFrame(acc, fg_color="transparent")
    row.pack(fill="x")
    ctk.CTkButton(
        row, text="B", width=40, height=32, fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=expand_b
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        row, text="P", width=40, height=32, fg_color=_FG, hover_color=_HOVER, command=lambda: (set_focus("accordion"), set_line("P · Playbook rewrite"))
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        row, text="E", width=40, height=32, fg_color=_FG, hover_color=_HOVER, command=lambda: (set_focus("accordion"), set_line("E · Edit mode"))
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        row, text="X", width=40, height=32, fg_color=_FG, hover_color=_HOVER, command=collapse
    ).pack(side="left")

    for n, name in ((1, "Click"), (2, "Drag"), (3, "Key"), (4, "OCR")):
        leaf_btns.append(
            ctk.CTkButton(
                leaves_host,
                text=f"{n} {name}",
                width=72,
                height=28,
                fg_color=_FG,
                hover_color=_HOVER,
                command=lambda n=n, name=name: pick_leaf(n, name),
            )
        )

    # --- Toggle ---
    tog = _specimen(grid, "Toggle leaf", 0, 1)
    mode_btn = ctk.CTkButton(tog, text="Mode: Single", width=160, height=32, fg_color=_ACCENT, hover_color=_ACCENT_HOVER)

    def flip_mode() -> None:
        set_focus("toggle")
        state["mode"] = "Spam" if state["mode"] == "Single" else "Single"
        mode_btn.configure(text=f"Mode: {state['mode']}")
        set_line(f"Mode: {state['mode']}")

    mode_btn.configure(command=flip_mode)
    mode_btn.pack(anchor="w")

    # --- Type-in ---
    typ = _specimen(grid, "Type-in leaf", 1, 0)
    type_row = ctk.CTkFrame(typ, fg_color="transparent")
    type_row.pack(fill="x")
    type_btn = ctk.CTkButton(type_row, text="Interval: 100ms", width=160, height=32, fg_color=_ACCENT, hover_color=_ACCENT_HOVER)
    type_entry = ctk.CTkEntry(type_row, width=100, height=32, placeholder_text="ms")

    def show_type_btn() -> None:
        type_entry.pack_forget()
        type_btn.pack(side="left")
        state["typing"] = False

    def commit_type(_event=None) -> None:
        raw = type_entry.get().strip()
        try:
            val = max(10, int(raw))
        except ValueError:
            set_line("Type-in · need a number (Esc cancels)")
            return
        state["interval_ms"] = val
        type_btn.configure(text=f"Interval: {val}ms")
        show_type_btn()
        set_line(f"Interval: {val}ms")

    def cancel_type(_event=None) -> None:
        show_type_btn()
        set_line(f"Interval: {state['interval_ms']}ms · cancelled")

    def begin_type() -> None:
        set_focus("typein")
        state["typing"] = True
        type_btn.pack_forget()
        type_entry.delete(0, "end")
        type_entry.insert(0, str(state["interval_ms"]))
        type_entry.pack(side="left")
        type_entry.focus_set()
        type_entry.select_range(0, "end")
        set_line("Type-in · enter ms · Enter commits · Esc cancels")

    type_btn.configure(command=begin_type)
    type_btn.pack(side="left")
    type_entry.bind("<Return>", commit_type)
    type_entry.bind("<Escape>", cancel_type)

    # --- Hold D ---
    hold = _specimen(grid, "Hold D", 1, 1)
    hold_btn = ctk.CTkButton(
        hold,
        text="Hold D",
        width=120,
        height=32,
        fg_color=_FG,
        hover_color=_HOVER,
        command=lambda: None,
    )
    hold_btn.pack(anchor="w")

    def d_press(_event=None) -> None:
        set_focus("hold_d")
        show_describe(True)
        set_line("Hold D · describing…")

    def d_release(_event=None) -> None:
        show_describe(False)
        set_line("Deck line · idle")

    hold_btn.bind("<ButtonPress-1>", d_press)
    hold_btn.bind("<ButtonRelease-1>", d_release)
    hold_btn.bind("<Leave>", lambda _e: show_describe(False) if state["describe_on"] else None)

    # --- Esc peel ---
    peel = _specimen(grid, "Esc peel", 2, 0)
    stack_lbl = ctk.CTkLabel(peel, text="Stack: Create", text_color=_BODY, anchor="w")
    stack_lbl.pack(anchor="w", pady=(0, 6))

    def refresh_stack() -> None:
        stack_lbl.configure(text="Stack: " + " › ".join(state["stack"]))

    def push_layer(name: str) -> None:
        set_focus("peel")
        if name not in state["stack"]:
            state["stack"].append(name)
        refresh_stack()
        set_line(f"Entered {name}")

    def do_peel() -> None:
        set_focus("peel")
        if len(state["stack"]) > 1:
            left = state["stack"].pop()
            refresh_stack()
            set_line(f"Esc · peeled {left}")
        else:
            set_line("Esc · outer peel · saved / exit")
            state["stack"] = ["Create"]
            refresh_stack()

    peel_row = ctk.CTkFrame(peel, fg_color="transparent")
    peel_row.pack(fill="x")
    ctk.CTkButton(
        peel_row, text="+ Edit", width=70, height=28, fg_color=_FG, hover_color=_HOVER, command=lambda: push_layer("Edit")
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        peel_row, text="+ Spam", width=70, height=28, fg_color=_FG, hover_color=_HOVER, command=lambda: push_layer("Spam")
    ).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        peel_row, text="Esc", width=56, height=28, fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=do_peel
    ).pack(side="left")

    # --- Queue + glyph ---
    queue = _specimen(grid, "Queue + glyph", 2, 1)
    board = ctk.CTkFrame(queue, fg_color="#12161F", corner_radius=6, height=72)
    board.pack(fill="x", pady=(0, 6))
    board.pack_propagate(False)
    glyph_lbl = ctk.CTkLabel(board, text="·", font=ctk.CTkFont(size=22, weight="bold"), text_color="#F0A060")
    glyph_lbl.place(relx=0.5, rely=0.5, anchor="center")
    queue_lbl = ctk.CTkLabel(queue, text="Queue · empty", text_color=_MUTED, anchor="w")
    queue_lbl.pack(anchor="w", pady=(0, 4))

    def add_step() -> None:
        set_focus("queue")
        state["queue_n"] += 1
        n = state["queue_n"]
        queue_lbl.configure(text=f"Queue · {n}: click", text_color=_BODY)
        glyph_lbl.configure(text=str(n))
        set_line(f"Queue · {n}: click")

    ctk.CTkButton(
        queue, text="Add step", width=100, height=28, fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=add_step
    ).pack(anchor="w")

    # --- Lab float ---
    flo = _specimen(grid, "Lab float", 3, 0)
    float_win: dict = {"ref": None}

    def close_float() -> None:
        win = float_win.get("ref")
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
            float_win["ref"] = None
        set_line("Lab float · closed · back to tray")

    def open_float() -> None:
        set_focus("float")
        if float_win.get("ref") is not None:
            try:
                float_win["ref"].lift()
                set_line("Lab float · already open")
                return
            except Exception:
                float_win["ref"] = None
        win = ctk.CTkToplevel(parent.winfo_toplevel())
        win.title("Lab float (specimen)")
        win.geometry("280x140")
        win.attributes("-topmost", True)
        float_win["ref"] = win
        ctk.CTkLabel(win, text="Stub Lab float", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=12, pady=(16, 6))
        ctk.CTkLabel(win, text="Esc or button returns.", text_color=_MUTED).pack(padx=12)
        ctk.CTkButton(win, text="Esc / Close", width=120, command=close_float).pack(pady=16)
        win.bind("<Escape>", lambda _e: close_float())
        win.protocol("WM_DELETE_WINDOW", close_float)
        set_line("Lab float · open")

    ctk.CTkButton(
        flo, text="Open float", width=120, height=32, fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=open_float
    ).pack(anchor="w")

    # --- Two voices ---
    voices = _specimen(grid, "Two voices", 3, 1)
    ctk.CTkLabel(voices, text="Same action, two channels", text_color=_MUTED, anchor="w").pack(anchor="w", pady=(0, 6))
    vrow = ctk.CTkFrame(voices, fg_color="transparent")
    vrow.pack(fill="x")

    def voice(kind: str) -> None:
        set_focus("voices")
        set_line(f"Start Molecule Lab · via {kind}")

    ctk.CTkButton(
        vrow, text="Lab button", width=110, height=32, fg_color=_ACCENT, hover_color=_ACCENT_HOVER, command=lambda: voice("Lab button")
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        vrow, text="M→1 leaf", width=110, height=32, fg_color=_FG, hover_color=_HOVER, command=lambda: voice("hotkey leaf")
    ).pack(side="left")

    show_describe(False)
    return root


def _specimen(grid: ctk.CTkFrame, title: str, row: int, col: int) -> ctk.CTkFrame:
    card = ctk.CTkFrame(grid, corner_radius=8, fg_color="#151A24")
    card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
    ctk.CTkLabel(
        card,
        text=title,
        font=ctk.CTkFont(size=13, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=10, pady=(8, 6))
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    return body
