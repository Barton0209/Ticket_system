# ui/onboarding.py
"""Подсказки при первом запуске."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui_theme import COLORS, FONT_HEADING, FONT_UI, setup_dialog_window
from user_prefs import mark_first_run_done


_TIPS = [
    ("PDF → заявка", "Загрузите PDF с заявками, затем «Заполнить из базы» — мастер подставит сотрудников."),
    ("Общая база", "Admin загружает Excel в «Настройки». Остальные: «Файл → Обновить общую базу»."),
    ("Из списка", "Вставьте список ФИО — система найдёт всех в базе и соберёт заявку."),
    ("Черновик", "Черновик сохраняется автоматически каждые несколько минут и вручную из меню «Файл»."),
    ("Горячие клавиши", "В таблице заявки: Ctrl+C/V, Delete, стрелки, F2 — как в Excel."),
]


class FirstRunDialog:
    def __init__(self, parent: tk.Tk):
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.grab_set()
        setup_dialog_window(self.window, "Добро пожаловать", 520, 420)

        tk.Label(
            self.window,
            text="Краткая инструкция",
            font=FONT_HEADING,
            bg=COLORS["white"],
            fg=COLORS["text"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        body = ttk.Frame(self.window, padding=12)
        body.pack(fill="both", expand=True)

        for title, text in _TIPS:
            row = ttk.Frame(body)
            row.pack(fill="x", pady=6)
            ttk.Label(row, text=title, font=FONT_HEADING).pack(anchor="w")
            ttk.Label(row, text=text, wraplength=460).pack(anchor="w", padx=(8, 0))

        btn_row = ttk.Frame(self.window)
        btn_row.pack(fill="x", padx=12, pady=12)
        ttk.Button(btn_row, text="Понятно, больше не показывать", command=self._close).pack(
            side="right"
        )

        self.window.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self):
        mark_first_run_done()
        self.window.destroy()
