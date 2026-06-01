# fio_list_dialog.py
"""Пакетный поиск ФИО из вставленного списка и формирование заявки."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional, Tuple

from database import find_employee_by_fio, employees_available, get_department_list, normalize_fio
from ui_theme import COLORS, FONT_SMALL, FONT_UI, bind_clipboard_shortcuts, setup_dialog_window


class DuplicatePickDialog:
    """Выбор одного сотрудника из нескольких совпадений в базе."""

    def __init__(
        self,
        parent,
        query_fio: str,
        candidates: List[dict],
        on_selected: Callable[[dict], None],
    ):
        self.on_selected = on_selected
        self.win = tk.Toplevel(parent)
        self.win.transient(parent)
        self.win.grab_set()
        setup_dialog_window(
            self.win,
            f"Выбор сотрудника — {query_fio[:40]}",
            720,
            420,
        )

        ttk.Label(
            self.win,
            text=f"Найдено записей: {len(candidates)}. Выберите нужную (двойной клик или кнопка):",
            font=FONT_UI,
            wraplength=660,
        ).pack(anchor="w", padx=12, pady=(12, 6))

        frame = ttk.Frame(self.win, padding=(12, 0))
        frame.pack(fill="both", expand=True)

        cols = ("fio", "department", "tab", "position")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        self.tree.heading("fio", text="ФИО")
        self.tree.heading("department", text="Подразделение")
        self.tree.heading("tab", text="Таб. №")
        self.tree.heading("position", text="Должность")
        self.tree.column("fio", width=240)
        self.tree.column("department", width=200)
        self.tree.column("tab", width=90)
        self.tree.column("position", width=120)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        self._candidates: List[dict] = []
        for emp in candidates:
            iid = self.tree.insert(
                "",
                "end",
                values=(
                    emp.get("fio", ""),
                    emp.get("department", ""),
                    emp.get("tab_num", ""),
                    emp.get("position", ""),
                ),
            )
            self._candidates.append((iid, emp))

        self.tree.bind("<Double-1>", self._on_double_click)

        btn_row = ttk.Frame(self.win, padding=12)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Выбрать", command=self._pick_selected).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Отмена", command=self.win.destroy).pack(side="right", padx=4)

    def _emp_by_iid(self, iid: str) -> Optional[dict]:
        for tree_iid, emp in self._candidates:
            if tree_iid == iid:
                return emp
        return None

    def _pick_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Выбор", "Выделите строку в списке.", parent=self.win)
            return
        emp = self._emp_by_iid(sel[0])
        if emp:
            self.on_selected(emp)
            self.win.destroy()

    def _on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        emp = self._emp_by_iid(iid)
        if emp:
            self.on_selected(emp)
            self.win.destroy()


class FioListDialog:
    """Вставка списка ФИО → поиск в базе по выбранному ОП → заявка."""

    def __init__(
        self,
        parent,
        current_department: str,
        is_admin: bool,
        on_create_application: Callable[[List[dict]], int],
    ):
        self.parent = parent
        self.current_department = current_department or ""
        self.is_admin = is_admin
        self.on_create_application = on_create_application
        self._rows: List[dict] = []
        self._tree_row_index: dict = {}

        self.win = tk.Toplevel(parent)
        self.win.transient(parent)
        setup_dialog_window(self.win, "Из списка — поиск в базе", 720, 640)

        self._build_ui()
        self._reload_departments()

    def _build_ui(self):
        top = ttk.Frame(self.win, padding=10)
        top.pack(fill="both", expand=True)

        ttk.Label(
            top,
            text="Вставьте ФИО (по одному в строке или столбец из Excel — Ctrl+V):",
            font=FONT_UI,
        ).pack(anchor="w")

        text_frame = ttk.Frame(top)
        text_frame.pack(fill="both", expand=True, pady=6)

        self.text = tk.Text(text_frame, height=12, font=FONT_UI, wrap="none")
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(text_frame, command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)
        bind_clipboard_shortcuts(self.text)

        filter_row = ttk.Frame(top)
        filter_row.pack(fill="x", pady=4)

        ttk.Label(filter_row, text="ОП (подразделение):").pack(side="left")
        self.dept_var = tk.StringVar()
        self.dept_combo = ttk.Combobox(
            filter_row,
            textvariable=self.dept_var,
            width=36,
            state="readonly",
        )
        self.dept_combo.pack(side="left", padx=8)

        ttk.Button(filter_row, text="Поиск", command=self._search).pack(side="left", padx=4)

        self.status_label = ttk.Label(top, text="", font=FONT_SMALL, foreground=COLORS["text_muted"])
        self.status_label.pack(anchor="w", pady=2)

        cols = ("fio", "status", "department", "tab")
        tree_frame = ttk.Frame(top)
        tree_frame.pack(fill="both", expand=True, pady=4)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        self.tree.heading("fio", text="ФИО (запрос)")
        self.tree.heading("status", text="Результат")
        self.tree.heading("department", text="Подразделение")
        self.tree.heading("tab", text="Таб. №")
        self.tree.column("fio", width=260)
        self.tree.column("status", width=140)
        self.tree.column("department", width=180)
        self.tree.column("tab", width=80)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.tag_configure("ok", background="#d4edda")
        self.tree.tag_configure("bad", background="#f8d7da")
        self.tree.tag_configure("warn", background="#fff3cd")
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        btn_row = ttk.Frame(top)
        btn_row.pack(fill="x", pady=8)

        self.btn_create = ttk.Button(
            btn_row,
            text="Составить заявку по найденным",
            command=self._create_application,
            state="disabled",
        )
        self.btn_create.pack(side="left", padx=4)

        ttk.Button(btn_row, text="Закрыть", command=self.win.destroy).pack(side="right", padx=4)

    def _reload_departments(self):
        depts = ["Все"]
        if employees_available():
            for d in get_department_list():
                d = d.strip()
                if d and d not in depts:
                    depts.append(d)
        self.dept_combo["values"] = depts
        if self.is_admin:
            self.dept_var.set("Все")
        elif self.current_department and self.current_department in depts:
            self.dept_var.set(self.current_department)
        elif self.current_department:
            self.dept_combo["values"] = depts + [self.current_department]
            self.dept_var.set(self.current_department)
        else:
            self.dept_var.set("Все")

    def _department_filter(self) -> Optional[str]:
        val = self.dept_var.get().strip()
        if val in ("", "Все", "Admin"):
            return None
        return val

    def _parse_fios(self) -> List[str]:
        raw = self.text.get("1.0", "end").strip()
        if not raw:
            return []
        fios: List[str] = []
        seen = set()
        for line in raw.replace("\r", "").split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.replace(";", "\t").split("\t") if p.strip()]
            if len(parts) > 1:
                for p in parts:
                    key = normalize_fio(p)
                    if key and key not in seen:
                        seen.add(key)
                        fios.append(p)
            else:
                key = normalize_fio(line)
                if key and key not in seen:
                    seen.add(key)
                    fios.append(line)
        return fios

    def _search(self):
        fios = self._parse_fios()
        if not fios:
            messagebox.showwarning("Поиск", "Вставьте хотя бы одно ФИО.", parent=self.win)
            return
        if not employees_available():
            messagebox.showwarning(
                "База",
                "База сотрудников не загружена.\nAdmin: Настройки → Загрузить базу.",
                parent=self.win,
            )
            return

        dept = self._department_filter()
        self._rows = []
        self._tree_row_index = {}
        self.tree.delete(*self.tree.get_children())

        for fio in fios:
            emp, status = find_employee_by_fio(fio, dept)
            row = {"query": fio, "status": status, "emp": emp}
            idx = len(self._rows)
            self._rows.append(row)
            iid = self.tree.insert(
                "",
                "end",
                values=self._row_display_values(row),
                tags=(self._row_tag(row),),
            )
            self._tree_row_index[iid] = idx

        self._update_create_button_state()

    def _row_tag(self, row: dict) -> str:
        if row.get("status") == "found":
            return "ok"
        if row.get("status") == "multiple":
            return "warn"
        return "bad"

    def _row_display_values(self, row: dict) -> Tuple[str, str, str, str]:
        fio = row.get("query", "")
        if row.get("status") == "found":
            emp = row.get("emp") or {}
            return (fio, "Найден", emp.get("department", ""), emp.get("tab_num", ""))
        if row.get("status") == "multiple":
            return (fio, "Несколько в базе (двойной клик)", "", "")
        return (fio, "Не найден", "", "")

    def _refresh_tree_row(self, tree_iid: str):
        idx = self._tree_row_index.get(tree_iid)
        if idx is None:
            return
        row = self._rows[idx]
        self.tree.item(
            tree_iid,
            values=self._row_display_values(row),
            tags=(self._row_tag(row),),
        )

    def _update_create_button_state(self):
        total = len(self._rows)
        found_count = sum(1 for r in self._rows if r.get("status") == "found" and r.get("emp"))
        multiple_count = sum(1 for r in self._rows if r.get("status") == "multiple")
        missing_count = total - found_count - multiple_count

        if found_count > 0:
            self.btn_create.config(state="normal")
            if found_count == total:
                self.status_label.config(
                    text=f"Все найдены: {found_count} из {total}. Можно составить заявку.",
                    foreground=COLORS.get("success", "#28a745"),
                )
            else:
                parts = [f"К заявке: {found_count} из {total}"]
                if multiple_count:
                    parts.append(f"уточните дубли: {multiple_count} (двойной клик)")
                if missing_count:
                    parts.append(f"не найдено: {missing_count}")
                self.status_label.config(
                    text=". ".join(parts) + ".",
                    foreground=COLORS.get("warning", "#856404"),
                )
        else:
            self.btn_create.config(state="disabled")
            self.status_label.config(
                text=(
                    f"Найдено: 0 из {total}. "
                    f"Неоднозначно: {multiple_count}, не найдено: {missing_count}."
                ),
                foreground=COLORS.get("danger", "#dc3545"),
            )

    def _on_tree_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        idx = self._tree_row_index.get(iid)
        if idx is None:
            return
        row = self._rows[idx]
        if row.get("status") != "multiple":
            return
        candidates = row.get("emp")
        if not isinstance(candidates, list) or not candidates:
            messagebox.showwarning(
                "Выбор",
                "Нет вариантов для выбора. Повторите поиск.",
                parent=self.win,
            )
            return

        def on_picked(emp: dict):
            row["status"] = "found"
            row["emp"] = emp
            self._refresh_tree_row(iid)
            self._update_create_button_state()

        DuplicatePickDialog(self.win, row.get("query", ""), candidates, on_picked)

    def _create_application(self):
        employees = [r["emp"] for r in self._rows if r.get("status") == "found" and r.get("emp")]
        if not employees:
            messagebox.showwarning("Заявка", "Нет сотрудников для добавления.", parent=self.win)
            return
        total = len(self._rows)
        unresolved = total - len(employees)
        msg = f"Добавить в заявку {len(employees)} сотрудников?"
        if unresolved > 0:
            msg += f"\n\n(Пропущено не найденных/неуточнённых: {unresolved})"
        if not messagebox.askyesno("Заявка", msg, parent=self.win):
            return
        added = self.on_create_application(employees)
        if added > 0:
            messagebox.showinfo("Готово", f"В заявку добавлено: {added} чел.", parent=self.win)
            self.win.destroy()
        else:
            messagebox.showwarning(
                "Заявка",
                "Никто не добавлен (возможно, уже есть в заявке).",
                parent=self.win,
            )
