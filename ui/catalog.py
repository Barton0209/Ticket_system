"""Каталог сотрудников и карточка."""

import tkinter as tk
from tkinter import messagebox, ttk

from database import (
    count_filtered_employees,
    get_department_list,
    get_employee_status,
    get_employees_records,
)
from ui.helpers import _normalize_tab_num
from ui_theme import (
    COLORS,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    FONT_UI,
    create_toolbar_button,
    setup_dialog_window,
)


class EmployeeCatalogDialog:
    CATALOG_PAGE_SIZE = 2000

    def __init__(
        self,
        parent,
        on_select_callback,
        added_tab_nums=None,
        department_filter=None,
        initial_search=None,
        bind_row_index=None,
        match_fio=None,
        duplicate_row_count=0,
    ):
        self.selected_employees = []
        self.on_select = on_select_callback
        self.selected_items = set()
        self.added_tab_nums = set(added_tab_nums or [])
        self.department_filter = department_filter
        self.initial_search = (initial_search or "").strip()
        self.bind_row_index = bind_row_index
        self.match_fio = (match_fio or self.initial_search or "").strip()
        self.duplicate_row_count = max(0, int(duplicate_row_count or 0))
        self._item_id_to_emp: dict = {}
        self.filtered_employees: list = []
        self._total_matching = 0
        self.apply_all_fio_var = tk.BooleanVar(
            value=self.duplicate_row_count > 1,
        )

        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.grab_set()
        title = "Подбор сотрудника по ФИО" if self.initial_search else "Каталог сотрудников"
        setup_dialog_window(self.window, title, 1000, 680)

        self.window.update_idletasks()
        x = parent.winfo_rootx() + 40
        y = parent.winfo_rooty() + 30
        self.window.geometry(f"+{x}+{y}")

        self._build_footer()
        self._build_table_area()
        self._build_header()

        self._reload_departments()
        if self.initial_search:
            self.search_entry.insert(0, self.initial_search)
        self.filter_list()

        self.window.bind("<Return>", lambda e: self.add_selected())
        self.window.bind("<Escape>", lambda e: self.done())
        self.search_entry.focus_set()

    def _build_header(self):
        header = tk.Frame(self.window, bg=COLORS["bg_dark"], height=56)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Каталог сотрудников",
            font=FONT_TITLE,
            bg=COLORS["bg_dark"],
            fg=COLORS["white"],
        ).pack(side="left", padx=20, pady=12)

        self.total_label = tk.Label(
            header,
            text="",
            font=FONT_UI,
            bg=COLORS["bg_dark"],
            fg="#a8b2c1",
        )
        self.total_label.pack(side="right", padx=20)

        filter_card = tk.Frame(self.window, bg=COLORS["white"], padx=16, pady=12)
        filter_card.pack(side="top", fill="x", padx=12, pady=(10, 6))

        tk.Label(filter_card, text="Поиск", font=FONT_SMALL, fg=COLORS["text_muted"], bg=COLORS["white"]).grid(
            row=0, column=0, sticky="w"
        )
        self.search_entry = tk.Entry(filter_card, font=FONT_UI, relief="flat", bg="#eef2f7")
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12), ipady=6)
        self.search_entry.bind("<KeyRelease>", self.filter_list)

        tk.Label(filter_card, text="Подразделение", font=FONT_SMALL, fg=COLORS["text_muted"], bg=COLORS["white"]).grid(
            row=0, column=1, sticky="w"
        )
        self.dept_filter = ttk.Combobox(filter_card, values=["Все"], width=28, state="readonly")
        self.dept_filter.grid(row=1, column=1, sticky="ew")
        self.dept_filter.set("Все")
        self.dept_filter.bind("<<ComboboxSelected>>", self.filter_list)

        filter_card.columnconfigure(0, weight=3)
        filter_card.columnconfigure(1, weight=1)

        tk.Label(
            self.window,
            text="Двойной клик или выделение строки + «ДОБАВИТЬ В ЗАЯВКУ»  •  галочка — несколько сразу",
            font=FONT_SMALL,
            fg=COLORS["text_muted"],
            bg=COLORS["bg_panel"],
        ).pack(side="top", fill="x", padx=16, pady=(0, 4))

    def _build_table_area(self):
        table_outer = ttk.LabelFrame(self.window, text="Список", padding=6)
        table_outer.pack(side="top", fill="both", expand=True, padx=12, pady=4)

        table_frame = tk.Frame(table_outer, bg=COLORS["white"])
        table_frame.pack(fill="both", expand=True)

        columns = ("#", "Выбрать", "ФИО", "Подразделение", "Статус", "Таб. №", "Гражданство")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("#", width=45, anchor="center", stretch=False)
        self.tree.column("Выбрать", width=72, anchor="center", stretch=False)
        self.tree.column("ФИО", width=220, stretch=True)
        self.tree.column("Подразделение", width=140, stretch=True)
        self.tree.column("Статус", width=100, stretch=True)
        self.tree.column("Таб. №", width=80, stretch=False)
        self.tree.column("Гражданство", width=100, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double_click)

    def _build_footer(self):
        """Нижняя панель всегда видна — основные действия здесь."""
        footer_h = 96 if self.bind_row_index is not None else 72
        footer = tk.Frame(self.window, bg="#e8edf3", height=footer_h)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        inner = tk.Frame(footer, bg="#e8edf3")
        inner.pack(fill="both", expand=True, padx=16, pady=10)

        left = tk.Frame(inner, bg="#e8edf3")
        left.pack(side="left", fill="y")

        self.count_label = tk.Label(
            left,
            text="Отмечено: 0",
            font=FONT_HEADING,
            bg="#e8edf3",
            fg=COLORS["text"],
        )
        self.count_label.pack(anchor="w")

        self.status_hint = tk.Label(
            left,
            text="В заявке отмечены ✓",
            font=FONT_SMALL,
            bg="#e8edf3",
            fg=COLORS["text_muted"],
        )
        self.status_hint.pack(anchor="w")

        if self.bind_row_index is not None:
            if self.duplicate_row_count > 1:
                chk_text = (
                    f"Заполнить данные из базы во всех строках с ФИО «{self.match_fio}» "
                    f"({self.duplicate_row_count} в заявке)"
                )
            else:
                chk_text = "Заполнить только выбранную строку заявки"
                self.apply_all_fio_var.set(False)
            self.apply_all_chk = tk.Checkbutton(
                left,
                text=chk_text,
                variable=self.apply_all_fio_var,
                font=FONT_SMALL,
                bg="#e8edf3",
                fg=COLORS["text"],
                activebackground="#e8edf3",
                wraplength=520,
                justify="left",
            )
            self.apply_all_chk.pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(inner, bg="#e8edf3")
        actions.pack(side="right")

        create_toolbar_button(actions, "Закрыть", self.done, "muted").pack(side="right", padx=4)
        create_toolbar_button(actions, "Выделенного →", self.add_current_row, "info").pack(side="right", padx=4)
        create_toolbar_button(
            actions,
            "ДОБАВИТЬ В ЗАЯВКУ",
            self.add_selected,
            "success",
            large=True,
        ).pack(side="right", padx=8)

    def _reload_departments(self):
        depts = {"Все"}
        if employees_available():
            for d in get_department_list():
                d = d.strip()
                if d:
                    depts.add(d)
        self.dept_filter["values"] = sorted(depts)
        if self.department_filter and self.department_filter in depts:
            self.dept_filter.set(self.department_filter)
        elif self.department_filter:
            self.dept_filter.set("Все")

    def load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self._item_id_to_emp = {}

        shown = len(self.filtered_employees)
        total = self._total_matching
        if total > shown:
            tail = f"  |  Показано: {shown} (лимит {self.CATALOG_PAGE_SIZE}, уточните поиск)"
        else:
            tail = f"  |  Показано: {shown}"
        self.total_label.config(text=f"Найдено: {total}{tail}")

        for idx, emp in enumerate(self.filtered_employees, 1):
            item_id = f"row_{idx}"
            self._item_id_to_emp[item_id] = emp
            tab_num = str(emp.get("tab_num", "") or "").strip()

            if tab_num and tab_num in self.added_tab_nums:
                checked = "✓"
            elif item_id in self.selected_items:
                checked = "☑"
            else:
                checked = "☐"

            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    idx,
                    checked,
                    emp.get("fio", ""),
                    emp.get("department", ""),
                    get_employee_status(emp),
                    tab_num,
                    emp.get("citizenship", ""),
                ),
            )

    def on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        if column != '#2':
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        values = self.tree.item(item_id, 'values')
        tab_num = values[5] if len(values) > 5 else ""

        if tab_num and tab_num in self.added_tab_nums:
            messagebox.showinfo("Информация", "Этот сотрудник уже добавлен в заявку")
            return

        if item_id in self.selected_items:
            self.selected_items.remove(item_id)
            new_check = '☐'
        else:
            self.selected_items.add(item_id)
            new_check = '☑'

        current_values = list(values)
        current_values[1] = new_check
        self.tree.item(item_id, values=tuple(current_values))
        self.count_label.config(text=f"Отмечено: {len(self.selected_items)}")

    def _emp_by_item_id(self, item_id: str):
        return self._item_id_to_emp.get(item_id)

    def _add_employees_to_application(self, employees: list, show_message: bool = True) -> int:
        if not employees:
            if show_message:
                messagebox.showwarning(
                    "Каталог",
                    "Выберите сотрудников (галочка в колонке «Выбрать») или дважды щёлкните по строке.",
                    parent=self.window,
                )
            return 0

        added = []
        for emp in employees:
            tab_num = _normalize_tab_num(emp.get("tab_num"))
            if tab_num and tab_num in self.added_tab_nums:
                continue
            added.append(emp)

        if not added:
            if show_message:
                messagebox.showinfo(
                    "Каталог",
                    "Выбранные сотрудники уже есть в заявке.",
                    parent=self.window,
                )
            return 0

        self.selected_employees.extend(added)
        added_count = self._call_on_select(added)
        if added_count <= 0:
            if show_message:
                messagebox.showwarning(
                    "Каталог",
                    "Не удалось добавить в заявку. Проверьте таблицу «Заявка».",
                    parent=self.window,
                )
            return 0

        for emp in added:
            tab_num = _normalize_tab_num(emp.get("tab_num"))
            if tab_num:
                self.added_tab_nums.add(tab_num)

        self.selected_items.clear()
        self.count_label.config(text="Отмечено: 0")
        self.load_employees()

        if show_message:
            if self.bind_row_index is not None:
                messagebox.showinfo(
                    "Готово",
                    f"Обновлено строк в заявке: {added_count}",
                    parent=self.window,
                )
                self.window.destroy()
            else:
                messagebox.showinfo(
                    "Каталог",
                    f"В заявку добавлено: {added_count} чел.\nМожно выбрать ещё.",
                    parent=self.window,
                )
        return added_count

    def _call_on_select(self, employees: list) -> int:
        if self.bind_row_index is not None:
            return self.on_select(
                employees,
                apply_all_fio=self.apply_all_fio_var.get(),
                bind_row=self.bind_row_index,
                source_fio=self.match_fio,
            )
        return self.on_select(employees)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            sel = self.tree.selection()
            item_id = sel[0] if sel else ""
        if not item_id:
            return
        emp = self._emp_by_item_id(item_id)
        if not emp:
            return
        tab_num = _normalize_tab_num(emp.get("tab_num"))
        if tab_num and tab_num in self.added_tab_nums:
            messagebox.showinfo(
                "Каталог",
                f"{emp.get('fio', '')} уже в заявке.",
                parent=self.window,
            )
            return
        self._add_employees_to_application([emp], show_message=True)

    def add_current_row(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Каталог", "Выделите строку в таблице.", parent=self.window)
            return
        emp = self._emp_by_item_id(selection[0])
        if emp:
            self._add_employees_to_application([emp])

    def filter_list(self, event=None):
        search_text = self.search_entry.get().strip()
        dept_filter = self.dept_filter.get()
        dept = None if dept_filter == "Все" else dept_filter
        if not dept and self.department_filter:
            dept = self.department_filter

        self._total_matching = count_filtered_employees(
            search_text or None,
            dept,
        )
        self.filtered_employees = get_employees_records(
            search_text or None,
            dept,
            limit=self.CATALOG_PAGE_SIZE,
        )
        self.selected_items.clear()
        self.count_label.config(text="Отмечено: 0")
        self.load_employees()

    def add_selected(self):
        selected = []
        seen_tabs = set()

        for item_id in self.selected_items:
            emp = self._emp_by_item_id(item_id)
            if emp:
                selected.append(emp)

        if not selected:
            for item_id in self.tree.selection():
                emp = self._emp_by_item_id(item_id)
                if emp:
                    tab = str(emp.get("tab_num", "") or "").strip()
                    if tab and tab in seen_tabs:
                        continue
                    if tab:
                        seen_tabs.add(tab)
                    selected.append(emp)

        self._add_employees_to_application(selected)

    def done(self):
        self.window.destroy()

    def cancel(self):
        self.window.destroy()


class EmployeeDetailDialog:
    def __init__(self, parent, employee, on_save_callback=None):
        self.employee = employee
        self.on_save = on_save_callback

        self.window = tk.Toplevel(parent)
        self.window.title(f"Сотрудник: {employee.get('fio', '')}")
        self.window.geometry("600x500")
        self.window.transient(parent)
        self.window.grab_set()

        info_frame = tk.LabelFrame(self.window, text="Данные сотрудника", padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=10)

        fields = [
            ('ФИО', 'fio'),
            ('Подразделение', 'department'),
            ('Должность', 'position'),
            ('Табельный номер', 'tab_num'),
            ('Гражданство', 'citizenship'),
            ('Дата рождения', 'birth_date'),
            ('Серия паспорта', 'doc_series'),
            ('Номер паспорта', 'doc_num'),
            ('Дата выдачи', 'doc_date'),
            ('Дата окончания', 'doc_expiry'),
            ('Адрес', 'address'),
            ('Телефон', 'phone'),
        ]

        self.entries = {}
        for label, key in fields:
            row = tk.Frame(info_frame)
            row.pack(fill='x', pady=2)

            tk.Label(row, text=f"{label}:", width=15, anchor='w').pack(side='left')

            entry = tk.Entry(row, font=('Arial', 10))
            entry.pack(side='left', fill='x', expand=True)
            entry.insert(0, employee.get(key, ''))
            entry.config(state='readonly')

            self.entries[key] = entry

        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=20)

        self.edit_btn = tk.Button(btn_frame, text="Редактировать", command=self.enable_edit,
                                 bg='#ffc107', fg='black', font=('Arial', 11), padx=20)
        self.edit_btn.pack(side='left', padx=5)

        tk.Button(btn_frame, text="Выбрать", command=self.select_employee,
                 bg='#28a745', fg='white', font=('Arial', 11), padx=20).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Закрыть", command=self.window.destroy,
                 bg='#6c757d', fg='white', font=('Arial', 11), padx=20).pack(side='left', padx=5)

    def enable_edit(self):
        for entry in self.entries.values():
            entry.config(state='normal')
        self.edit_btn.config(text="Сохранить", command=self.save_changes, bg='#28a745', fg='white')

    def save_changes(self):
        for key, entry in self.entries.items():
            self.employee[key] = entry.get()

        if self.on_save:
            self.on_save(self.employee)

        messagebox.showinfo("Успех", "Изменения сохранены")
        self.window.destroy()

    def select_employee(self):
        self.window.destroy()
        return self.employee
