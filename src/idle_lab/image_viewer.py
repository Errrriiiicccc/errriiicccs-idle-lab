"""Simple screenshot / image viewer toplevel."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk


class ImageViewer(ctk.CTkToplevel):
    """Browse one or more image paths with Prev / Next."""

    def __init__(
        self,
        master,
        paths: list[Path],
        *,
        titles: list[str] | None = None,
        start_index: int = 0,
        title: str = "Screenshot viewer",
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("780x640")
        self.minsize(480, 360)
        self.paths = [Path(p) for p in paths if Path(p).exists()]
        self.titles = titles or [p.name for p in self.paths]
        while len(self.titles) < len(self.paths):
            self.titles.append(self.paths[len(self.titles)].name)
        self.index = max(0, min(start_index, max(0, len(self.paths) - 1)))
        self._photo: ImageTk.PhotoImage | None = None
        self._build()
        self.after(30, self._show)
        try:
            self.focus_force()
            self.lift()
        except Exception:
            pass

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 4))
        self.prev_btn = ctk.CTkButton(toolbar, text="◀ Prev", width=90, command=self._prev)
        self.prev_btn.pack(side="left")
        self.next_btn = ctk.CTkButton(toolbar, text="Next ▶", width=90, command=self._next)
        self.next_btn.pack(side="right")
        self.caption = ctk.CTkLabel(toolbar, text="", anchor="center")
        self.caption.pack(side="left", fill="x", expand=True, padx=8)

        self.canvas_host = ctk.CTkFrame(self)
        self.canvas_host.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.image_label = ctk.CTkLabel(self.canvas_host, text="No image", anchor="center")
        self.image_label.pack(fill="both", expand=True, padx=8, pady=8)

        self.bind("<Left>", lambda _e: self._prev())
        self.bind("<Right>", lambda _e: self._next())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _prev(self) -> None:
        if not self.paths:
            return
        self.index = (self.index - 1) % len(self.paths)
        self._show()

    def _next(self) -> None:
        if not self.paths:
            return
        self.index = (self.index + 1) % len(self.paths)
        self._show()

    def _show(self) -> None:
        if not self.paths:
            self.caption.configure(text="No screenshots to show")
            self.image_label.configure(image=None, text="No image files found.")
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")
            return
        path = self.paths[self.index]
        label = self.titles[self.index] if self.index < len(self.titles) else path.name
        self.caption.configure(text=f"{self.index + 1}/{len(self.paths)}  ·  {label}")
        multi = len(self.paths) > 1
        self.prev_btn.configure(state="normal" if multi else "disabled")
        self.next_btn.configure(state="normal" if multi else "disabled")
        try:
            image = Image.open(path)
            image.load()
        except OSError as exc:
            self.image_label.configure(image=None, text=f"Could not open:\n{path}\n{exc}")
            self._photo = None
            return
        host_w = max(self.canvas_host.winfo_width() - 24, 320)
        host_h = max(self.canvas_host.winfo_height() - 24, 240)
        fitted = image.copy()
        fitted.thumbnail((host_w, host_h), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(fitted)
        self.image_label.configure(image=self._photo, text="")


def open_image_viewer(
    master,
    paths: list[Path],
    *,
    titles: list[str] | None = None,
    start_index: int = 0,
    title: str = "Screenshot viewer",
) -> ImageViewer | None:
    existing = [Path(p) for p in paths if Path(p).exists()]
    if not existing:
        return None
    return ImageViewer(master, existing, titles=titles, start_index=start_index, title=title)
