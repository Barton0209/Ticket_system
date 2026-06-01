# settings_tab.py
"""Вкладка «Настройки» (только Admin)."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui_theme import style_tk_button, FONT_HEADING, FONT_UI
from database import (
    load_employees_base,
    export_employees_to_excel,
    employees_available,
    get_employees_count,
    get_employees_cache_meta,
)
from users_manager import load_users_from_excel, export_users_to_excel, load_users_cache
from template_manager import install_template, is_template_installed, TEMPLATE_FILE


class SettingsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Настройки системы", font=FONT_HEADING).pack(anchor="w", padx=20, pady=(20, 10))

        sections = [
            (
                "База сотрудников (лист «ВСЕ ОП»)",
                [
                    ("Загрузить / обновить базу", self._load_employees, "primary"),
                    ("Выгрузить базу", self._export_employees, "success"),
                    ("Добавить сотрудника вручную", self._add_employee, "info"),
                ],
            ),
            (
                "Пользователи (лист «Users+pass»)",
                [
                    ("Загрузить пользователей", self._load_users, "primary"),
                    ("Выгрузить пользователей", self._export_users, "success"),
                ],
            ),
            (
                "Шаблон заявки",
                [
                    ("Загрузить шаблон", self._load_template, "primary"),
                ],
            ),
        ]

        for title, buttons in sections:
            frame = ttk.LabelFrame(self, text=title, padding=12)
            frame.pack(fill="x", padx=20, pady=8)
            row = ttk.Frame(frame)
            row.pack(fill="x")
            for text, cmd, variant in buttons:
                btn = tk.Button(row, text=text, command=cmd)
                style_tk_button(btn, variant)
                btn.pack(side="left", padx=4, pady=4)

        self.status = tk.Label(self, text="", font=FONT_UI, justify="left", wraplength=700)
        self.status.pack(anchor="w", padx=20, pady=20)
        self.refresh_status()

    def refresh_status(self):
        db_count = get_employees_count() if employees_available() else 0
        meta = get_employees_cache_meta()
        tpl = "загружен" if is_template_installed() else "не загружен"
        load_users_cache()
        cache_line = "общий кэш: data/employees_cache.pkl (доступен всем пользователям)"
        if meta.get("updated_at"):
            cache_line += f"\n  обновлено: {meta['updated_at']}"
        if meta.get("source"):
            cache_line += f", файл: {meta['source']}"
        self.status.config(
            text=f"Сотрудников в базе: {db_count}\n"
            f"{cache_line}\n"
            f"Шаблон: {tpl} ({TEMPLATE_FILE.name if is_template_installed() else '—'})\n"
            f"Пользователи: data/Users+pass.xlsx\n"
            f"Tesseract: C:\\Tesseract-OCR\\tesseract.exe"
        )

    def _load_employees(self):
        path = filedialog.askopenfilename(
            title="База сотрудников",
            filetypes=[("Excel", "*.xlsx *.xls")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        ok, msg, _ = load_employees_base(path, loaded_by="Admin")
        if ok:
            messagebox.showinfo("База", msg, parent=self.winfo_toplevel())
            self.app.on_database_updated()
        else:
            messagebox.showerror("База", msg, parent=self.winfo_toplevel())
        self.refresh_status()

    def _export_employees(self):
        if not employees_available():
            messagebox.showwarning("База", "База пуста", parent=self.winfo_toplevel())
            return
        path = filedialog.asksaveasfilename(
            title="Выгрузить базу",
            defaultextension=".xlsx",
            initialfile="База_сотрудников.xlsx",
            filetypes=[("Excel", "*.xlsx")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        ok, msg = export_employees_to_excel(path)
        if ok:
            messagebox.showinfo("База", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("База", msg, parent=self.winfo_toplevel())

    def _add_employee(self):
        from employee_editor import EmployeeEditorDialog
        EmployeeEditorDialog(self.winfo_toplevel(), on_saved=self._on_employee_saved)

    def _on_employee_saved(self):
        self.app.on_database_updated()
        self.refresh_status()

    def _load_users(self):
        path = filedialog.askopenfilename(
            title="Пользователи",
            filetypes=[("Excel", "*.xlsx *.xls")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        ok, msg, _ = load_users_from_excel(path)
        if ok:
            messagebox.showinfo("Пользователи", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Пользователи", msg, parent=self.winfo_toplevel())
        self.refresh_status()

    def _export_users(self):
        path = filedialog.asksaveasfilename(
            title="Выгрузить пользователей",
            defaultextension=".xlsx",
            initialfile="Users+pass.xlsx",
            filetypes=[("Excel", "*.xlsx")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        ok, msg = export_users_to_excel(path)
        if ok:
            messagebox.showinfo("Пользователи", msg, parent=self.winfo_toplevel())
        else:
            messagebox.showerror("Пользователи", msg, parent=self.winfo_toplevel())

    def _load_template(self):
        path = filedialog.askopenfilename(
            title="Шаблон заявки",
            filetypes=[("Excel", "*.xlsx")],
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        ok, msg = install_template(path)
        if ok:
            messagebox.showinfo("Шаблон", msg, parent=self.winfo_toplevel())
            self.app.on_template_updated()
        else:
            messagebox.showerror("Шаблон", msg, parent=self.winfo_toplevel())
        self.refresh_status()
