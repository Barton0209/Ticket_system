# ui_theme.py
"""Единая тема оформления для tkinter/ttk."""

import tkinter as tk
from tkinter import ttk

COLORS_LIGHT = {
    "bg_dark": "#1a1a2e",
    "bg_toolbar": "#16213e",
    "bg_panel": "#f4f6fb",
    "accent": "#e94560",
    "accent_blue": "#0f3460",
    "success": "#28a745",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "danger": "#dc3545",
    "text": "#1f2937",
    "text_muted": "#6b7280",
    "border": "#d1d5db",
    "white": "#ffffff",
}

COLORS_DARK = {
    "bg_dark": "#0d0d18",
    "bg_toolbar": "#151528",
    "bg_panel": "#1e1e2e",
    "accent": "#f472b6",
    "accent_blue": "#3b82f6",
    "success": "#34d399",
    "warning": "#fbbf24",
    "info": "#38bdf8",
    "danger": "#f87171",
    "text": "#e5e7eb",
    "text_muted": "#9ca3af",
    "border": "#374151",
    "white": "#2a2a3d",
}

COLORS = dict(COLORS_LIGHT)


def set_theme_mode(dark: bool) -> None:
    """Переключить палитру (полное обновление виджетов — после перезапуска)."""
    global COLORS
    COLORS = dict(COLORS_DARK if dark else COLORS_LIGHT)

FONT_UI = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)


def apply_theme(root, dark: bool | None = None) -> ttk.Style:
    if dark is not None:
        set_theme_mode(dark)
    style = ttk.Style(root)
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
    style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", COLORS["text"])])
    style.configure("TButton", padding=(12, 6))
    style.configure("TCombobox", padding=4)
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["border"], background=COLORS["accent"])
    style.configure("Vertical.TScrollbar", background=COLORS["border"])
    return style


def style_tk_button(btn, variant="primary"):
    palettes = {
        "primary": (COLORS["accent_blue"], COLORS["white"]),
        "accent": (COLORS["accent"], COLORS["white"]),
        "success": (COLORS["success"], COLORS["white"]),
        "info": (COLORS["info"], COLORS["white"]),
        "warning": (COLORS["warning"], COLORS["text"]),
        "danger": (COLORS["danger"], COLORS["white"]),
        "muted": ("#4b5563", COLORS["white"]),
    }
    bg, fg = palettes.get(variant, palettes["primary"])
    btn.configure(
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        cursor="hand2",
        font=FONT_UI,
        padx=14,
        pady=8,
        bd=0,
        highlightthickness=0,
    )


def bind_clipboard_shortcuts(widget, include_select_all: bool = True):
    """Ctrl+C / Ctrl+V / Ctrl+X / Ctrl+A для Entry, Combobox и окна."""

    def _widget(event=None):
        if event is not None and event.widget:
            return event.widget
        return widget

    def copy(event=None):
        w = _widget(event)
        try:
            if hasattr(w, "selection_present") and w.selection_present():
                text = w.get(w.index("sel.first"), w.index("sel.last"))
                w.clipboard_clear()
                w.clipboard_append(text)
        except tk.TclError:
            pass
        return "break"

    def paste(event=None):
        w = _widget(event)
        try:
            text = w.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            if hasattr(w, "selection_present") and w.selection_present():
                w.delete("sel.first", "sel.last")
            w.insert("insert", text)
        except tk.TclError:
            pass
        return "break"

    def cut(event=None):
        copy(event)
        w = _widget(event)
        try:
            if hasattr(w, "selection_present") and w.selection_present():
                w.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def select_all(event=None):
        w = _widget(event)
        try:
            w.select_range(0, "end")
            w.icursor("end")
        except tk.TclError:
            pass
        return "break"

    targets = widget if isinstance(widget, (list, tuple, set)) else [widget]
    for w in targets:
        for seq in ("<Control-c>", "<Control-C>", "<Control-Key-c>", "<Control-Key-C>"):
            w.bind(seq, copy, add="+")
        for seq in ("<Control-v>", "<Control-V>", "<Control-Key-v>", "<Control-Key-V>"):
            w.bind(seq, paste, add="+")
        for seq in ("<Control-x>", "<Control-X>", "<Control-Key-x>", "<Control-Key-X>"):
            w.bind(seq, cut, add="+")
        if include_select_all:
            for seq in ("<Control-a>", "<Control-A>", "<Control-Key-a>", "<Control-Key-A>"):
                w.bind(seq, select_all, add="+")


def bind_window_clipboard(window, on_copy_extra=None):
    """Глобальные Ctrl+C/V в окне (если фокус не в поле с собственными биндами)."""
    bind_clipboard_shortcuts(window, include_select_all=False)

    def copy(event=None):
        w = window.focus_get()
        if w and hasattr(w, "selection_present"):
            try:
                if w.selection_present():
                    return None
            except tk.TclError:
                pass
        if on_copy_extra:
            on_copy_extra()
        return None

    window.bind("<Control-c>", copy, add="+")
    window.bind("<Control-C>", copy, add="+")


def configure_root(root):
    root.configure(bg=COLORS["bg_panel"])
    try:
        root.option_add("*Font", FONT_UI)
        root.option_add("*TCombobox*Listbox.font", FONT_UI)
    except Exception:
        pass


def setup_dialog_window(window, title: str, width: int = 1100, height: int = 720):
    window.title(title)
    window.geometry(f"{width}x{height}")
    window.minsize(int(width * 0.75), int(height * 0.65))
    window.configure(bg=COLORS["bg_panel"])
    apply_theme(window)


def create_toolbar_button(parent, text, command, variant="primary", large=False):
    btn = tk.Button(parent, text=text, command=command)
    if large:
        btn.configure(font=FONT_HEADING, padx=22, pady=12)
    style_tk_button(btn, variant)
    return btn
