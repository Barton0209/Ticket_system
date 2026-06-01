# ui/ctk_theme.py
"""CustomTkinter: тема и фабрики виджетов для desktop UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from ui_theme import COLORS, FONT_HEADING, FONT_SMALL, FONT_TITLE, FONT_UI, set_theme_mode

CTK_VARIANTS = {
    "primary": ("accent_blue", "#1e40af"),
    "accent": ("accent", "#be185d"),
    "success": ("success", "#15803d"),
    "info": ("info", "#0369a1"),
    "warning": ("warning", "#b45309"),
    "danger": ("danger", "#b91c1c"),
    "muted": ("#4b5563", "#374151"),
}


def init_ctk(dark: bool | None = None) -> None:
    if dark is None:
        from user_prefs import is_dark_theme

        dark = is_dark_theme()
    set_theme_mode(dark)
    ctk.set_appearance_mode("dark" if dark else "light")
    ctk.set_default_color_theme("dark-blue" if dark else "blue")


def apply_ctk_appearance(dark: bool) -> None:
    """Смена светлой/тёмной темы без перезапуска."""
    set_theme_mode(dark)
    ctk.set_appearance_mode("dark" if dark else "light")


def configure_ctk_root(root: ctk.CTk) -> None:
    root.configure(fg_color=COLORS["bg_panel"])
    try:
        root.option_add("*Font", FONT_UI)
    except Exception:
        pass


def setup_ctk_dialog(window: ctk.CTkToplevel, title: str, width: int = 1100, height: int = 720) -> None:
    window.title(title)
    window.geometry(f"{width}x{height}")
    window.minsize(int(width * 0.75), int(height * 0.65))
    window.configure(fg_color=COLORS["bg_panel"])


def embed_tk_frame(ctk_parent, bg: str | None = None) -> tk.Frame:
    """Контейнер tk/ttk/tksheet внутри CustomTkinter."""
    frame = tk.Frame(ctk_parent, bg=bg or COLORS["bg_panel"])
    frame.pack(fill="both", expand=True)
    return frame


def create_toolbar_button(parent, text, command, variant="primary", state="normal", **kwargs):
    key, hover = CTK_VARIANTS.get(variant, CTK_VARIANTS["primary"])
    fg = COLORS.get(key, key) if isinstance(key, str) and key in COLORS else key
    btn = ctk.CTkButton(
        parent,
        text=text,
        command=command,
        font=FONT_UI,
        height=34,
        fg_color=fg,
        hover_color=hover,
        corner_radius=8,
        state="normal" if state == "normal" else "disabled",
        **kwargs,
    )
    return btn


def set_button_state(btn, enabled: bool) -> None:
    state = "normal" if enabled else "disabled"
    if isinstance(btn, ctk.CTkButton):
        btn.configure(state=state)
    else:
        btn.config(state=state)


def apply_ttk_panel_style() -> None:
    """ttk внутри вкладок — в тон CustomTkinter."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=FONT_UI, background=COLORS["bg_panel"])
    style.configure("TFrame", background=COLORS["bg_panel"])
    style.configure("TLabel", background=COLORS["bg_panel"], foreground=COLORS["text"])
    style.configure("TLabelframe", background=COLORS["bg_panel"], foreground=COLORS["text"])
    style.configure("TLabelframe.Label", font=FONT_HEADING, foreground=COLORS["text"])
    style.configure(
        "Treeview",
        rowheight=26,
        font=FONT_UI,
        background=COLORS["white"],
        fieldbackground=COLORS["white"],
        foreground=COLORS["text"],
    )
    style.configure(
        "Treeview.Heading",
        font=FONT_HEADING,
        background=COLORS["bg_dark"],
        foreground=COLORS["white"],
        relief="flat",
    )
    style.configure("TButton", padding=(10, 5))
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["border"], background=COLORS["accent_blue"])
