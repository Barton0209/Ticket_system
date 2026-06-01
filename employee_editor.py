# employee_editor.py
"""Добавление / редактирование сотрудника в базе."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional

from database import add_or_update_employee


class EmployeeEditorDialog:
    FIELDS = [
        ("Ф.И.О.", "fio"),
        ("Подразделение", "department"),
        ("Отдел", "department_category"),
        ("Табельный номер", "tab_num"),
        ("Гражданство", "citizenship"),
        ("Дата рождения", "birth_date"),
        ("Серия", "doc_series"),
        ("Номер", "doc_num"),
        ("Дата выдачи", "doc_date"),
        ("Дата окончания", "doc_expiry"),
        ("Кем выдан", "doc_issuer"),
        ("Адрес", "address"),
        ("Телефон", "phone"),
        ("Должность", "position"),
    ]

    def __init__(self, parent, employee: Optional[Dict] = None, on_saved: Optional[Callable] = None):
        self.employee = employee or {}
        self.on_saved = on_saved
        self.entries = {}

        self.win = tk.Toplevel(parent)
        self.win.title("Сотрудник")
        self.win.geometry("520x520")
        self.win.transient(parent)
        self.win.grab_set()

        form = ttk.Frame(self.win, padding=12)
        form.pack(fill="both", expand=True)
        for i, (label, key) in enumerate(self.FIELDS):
            ttk.Label(form, text=label + ":").grid(row=i, column=0, sticky="w", pady=3)
            e = ttk.Entry(form, width=40)
            e.grid(row=i, column=1, sticky="ew", pady=3, padx=5)
            e.insert(0, self.employee.get(key, ""))
            self.entries[key] = e
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(self.win, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="Сохранить", command=self._save).pack(side="left", padx=5)
        ttk.Button(btns, text="Отмена", command=self.win.destroy).pack(side="left")

    def _save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        if not data.get("fio"):
            messagebox.showwarning("Ошибка", "Укажите Ф.И.О.", parent=self.win)
            return
        ok, msg = add_or_update_employee(data)
        if ok:
            if self.on_saved:
                self.on_saved()
            messagebox.showinfo("Успех", msg, parent=self.win)
            self.win.destroy()
        else:
            messagebox.showerror("Ошибка", msg, parent=self.win)
