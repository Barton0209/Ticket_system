# ui/toast.py
"""Неблокирующие уведомления (toast) вместо messagebox для статусных сообщений."""

from __future__ import annotations

import tkinter as tk
from typing import Literal

from ui_theme import COLORS, FONT_SMALL

ToastLevel = Literal["info", "success", "warning", "error"]

_LEVEL_STYLES = {
    "info": ("#dbeafe", "#1e40af"),
    "success": ("#d1fae5", "#065f46"),
    "warning": ("#fef3c7", "#92400e"),
    "error": ("#fee2e2", "#991b1b"),
}


class ToastManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._toasts: list[tk.Toplevel] = []

    def show(
        self,
        message: str,
        level: ToastLevel = "info",
        duration_ms: int = 3500,
    ) -> None:
        if not message:
            return

        bg, fg = _LEVEL_STYLES.get(level, _LEVEL_STYLES["info"])
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        try:
            toast.attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        frame = tk.Frame(toast, bg=bg, highlightbackground=COLORS["border"], highlightthickness=1)
        frame.pack(fill="both", expand=True)
        lbl = tk.Label(
            frame,
            text=message,
            font=FONT_SMALL,
            bg=bg,
            fg=fg,
            wraplength=420,
            justify="left",
            padx=14,
            pady=10,
        )
        lbl.pack()

        self._toasts.append(toast)
        self._position_toasts()

        def dismiss():
            try:
                if toast in self._toasts:
                    self._toasts.remove(toast)
                toast.destroy()
            except tk.TclError:
                pass
            self._position_toasts()

        toast.after(duration_ms, dismiss)

    def _position_toasts(self) -> None:
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + self.root.winfo_width() - 440
        y = self.root.winfo_rooty() + self.root.winfo_height() - 24
        for toast in reversed(self._toasts):
            try:
                toast.update_idletasks()
                h = toast.winfo_reqheight()
                y -= h + 8
                toast.geometry(f"+{max(x, 8)}+{max(y, 8)}")
            except tk.TclError:
                pass
