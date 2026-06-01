"""Мастер заполнения заявки из базы сотрудников."""

import tkinter as tk
from tkinter import messagebox, ttk

from database import (
    employees_available,
    find_employee_by_fio,
    get_department_list,
    get_employee_status,
    get_employees_records,
    hash_fio,
)
from pdf_viewer import PDFViewer
from route_logic import apply_reason1_rules, get_reason_list, suggest_reason2
from routes import build_reverse_map, filter_route_suggestions, load_routes
from template_manager import get_column_dropdowns
from ui.catalog import EmployeeCatalogDialog
from ui.helpers import _normalize_tab_num
from ui_theme import COLORS, FONT_SMALL, bind_clipboard_shortcuts


class FillFromBaseWizard:
    WIZARD_FONT = ("Segoe UI", 9)
    WIZARD_FONT_BOLD = ("Segoe UI", 9, "bold")

    def __init__(
        self,
        parent,
        pdf_results,
        pdf_files,
        department,
        on_complete,
        routes=None,
        pdf_viewer=None,
    ):
        self.parent = parent
        self.pdf_results = pdf_results
        self.pdf_files = pdf_files
        self.department = department
        self.on_complete = on_complete
        self.pdf_viewer = None
        self.routes = routes or load_routes()
        self.reverse_routes = build_reverse_map(self.routes)
        lists = get_column_dropdowns()
        if lists.get("Маршрут"):
            self.routes = sorted(set(self.routes) | set(lists["Маршрут"]))
            self.reverse_routes = build_reverse_map(self.routes)
        self.reasons = get_reason_list(lists.get("Обоснование"))
        self.current_index = 0
        self.filled_results = []
        self.history = []
        self._emp_map: dict = {}
        self.current_employee = None
        self._dept_filter = None if department == "Admin" else department

        self.window = tk.Toplevel(parent)
        self.window.title("Заполнение из базы")
        self.window.transient(parent)
        # Без grab_set — иначе в главной таблице заявки не работают Ctrl+C / Ctrl+V
        w, h = 980, 620
        self.window.geometry(f"{w}x{h}+24+48")
        self.window.minsize(780, 480)

        self.create_ui()
        self.process_next()

    def create_ui(self):
        # Верхняя панель навигации
        nav_frame = tk.Frame(self.window, bg='#1a1a2e', height=50)
        nav_frame.pack(fill='x')

        self.nav_label = tk.Label(
            nav_frame, text="", font=self.WIZARD_FONT_BOLD, bg="#1a1a2e", fg="white"
        )
        self.nav_label.pack(side="left", padx=12)

        tk.Button(
            nav_frame, text="◀ Назад", command=self.navigate_prev,
            bg="#6c757d", fg="white", font=self.WIZARD_FONT,
        ).pack(side="right", padx=4, pady=6)

        tk.Button(
            nav_frame, text="Следующий ▶", command=self.navigate_next,
            bg="#17a2b8", fg="white", font=self.WIZARD_FONT,
        ).pack(side="right", padx=4)

        tk.Button(
            nav_frame, text="Пропустить", command=self.skip_current,
            bg="#ffc107", fg="black", font=self.WIZARD_FONT,
        ).pack(side="right", padx=4)

        body = ttk.PanedWindow(self.window, orient="horizontal")
        body.pack(fill="both", expand=True, padx=4, pady=2)

        pdf_col = ttk.Frame(body)
        body.add(pdf_col, weight=2)
        pdf_lf = ttk.LabelFrame(pdf_col, text="Просмотр PDF", padding=2)
        pdf_lf.pack(fill="both", expand=True)
        self.pdf_viewer = PDFViewer(pdf_lf)

        form_col = ttk.Frame(body)
        body.add(form_col, weight=3)

        right_frame = ttk.LabelFrame(form_col, text="Данные заявки", padding=6)
        right_frame.pack(fill="both", expand=True)

        # Список файлов
        files_frame = tk.LabelFrame(right_frame, text="Заявки (страницы PDF)", padx=4, pady=3)
        files_frame.pack(fill='x', pady=3)

        self.files_listbox = tk.Listbox(files_frame, height=4, font=self.WIZARD_FONT)
        self.files_listbox.pack(fill='x')
        self.files_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        self._refresh_files_listbox()

        # Поля редактирования
        edit_frame = tk.LabelFrame(right_frame, text="Редактирование полей", padx=4, pady=4)
        edit_frame.pack(fill='x', pady=4)

        # ФИО с автопоиском
        tk.Label(edit_frame, text="ФИО:", font=self.WIZARD_FONT_BOLD).grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.fio_entry = tk.Entry(edit_frame, font=self.WIZARD_FONT, width=32)
        self.fio_entry.grid(row=0, column=1, sticky='ew', padx=4, pady=2)
        self.fio_entry.bind('<KeyRelease>', self.on_fio_change)  # Автопоиск при вводе
        self.fio_entry.bind('<FocusOut>', self.on_fio_change)   # Автопоиск при выходе из поля

        # Маршрут 1 (выпадающий список + ручной ввод)
        tk.Label(edit_frame, text="Маршрут 1:", font=self.WIZARD_FONT).grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.route1_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=self.routes
        )
        self.route1_combo.grid(row=1, column=1, sticky='ew', padx=4, pady=2)
        self.route1_combo.set('')
        self.route1_combo.bind('<<ComboboxSelected>>', self.on_route1_select)
        self._bind_route_autocomplete(self.route1_combo)

        # Дата вылета 1 (туда)
        tk.Label(edit_frame, text="Дата вылета 1:", font=self.WIZARD_FONT).grid(
            row=2, column=0, sticky="w", pady=2
        )
        self.date1_entry = tk.Entry(edit_frame, font=self.WIZARD_FONT, width=32)
        self.date1_entry.grid(row=2, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Транспорт 1:", font=self.WIZARD_FONT).grid(
            row=3, column=0, sticky="w", pady=2
        )
        self.transport1_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=("АВИА", "ЖД")
        )
        self.transport1_combo.grid(row=3, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Примечание 1:", font=self.WIZARD_FONT).grid(
            row=4, column=0, sticky="w", pady=2
        )
        self.note1_entry = tk.Entry(edit_frame, font=self.WIZARD_FONT, width=32)
        self.note1_entry.grid(row=4, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Маршрут 2 (обратно):", font=self.WIZARD_FONT).grid(
            row=5, column=0, sticky="w", pady=2
        )
        self.route2_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=self.routes
        )
        self.route2_combo.grid(row=5, column=1, sticky='ew', padx=4, pady=2)
        self.route2_combo.set('')
        self._bind_route_autocomplete(self.route2_combo)

        tk.Label(edit_frame, text="Дата вылета 2:", font=self.WIZARD_FONT).grid(
            row=6, column=0, sticky="w", pady=2
        )
        self.date2_entry = tk.Entry(edit_frame, font=self.WIZARD_FONT, width=32)
        self.date2_entry.grid(row=6, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Транспорт 2:", font=self.WIZARD_FONT).grid(
            row=7, column=0, sticky="w", pady=2
        )
        self.transport2_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=("АВИА", "ЖД", "")
        )
        self.transport2_combo.grid(row=7, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Примечание 2:", font=self.WIZARD_FONT).grid(
            row=8, column=0, sticky="w", pady=2
        )
        self.note2_entry = tk.Entry(edit_frame, font=self.WIZARD_FONT, width=32)
        self.note2_entry.grid(row=8, column=1, sticky='ew', padx=4, pady=2)

        tk.Label(edit_frame, text="Обоснование:", font=self.WIZARD_FONT_BOLD).grid(
            row=9, column=0, sticky="w", pady=2
        )
        self.reason1_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=self.reasons
        )
        self.reason1_combo.grid(row=9, column=1, sticky='ew', padx=4, pady=2)
        self.reason1_combo.bind("<<ComboboxSelected>>", self.on_reason1_change)
        self.reason1_combo.bind("<FocusOut>", self.on_reason1_change)

        tk.Label(edit_frame, text="Обоснование 2:", font=self.WIZARD_FONT).grid(
            row=10, column=0, sticky="w", pady=2
        )
        self.reason2_combo = ttk.Combobox(
            edit_frame, font=self.WIZARD_FONT, width=30, values=self.reasons
        )
        self.reason2_combo.grid(row=10, column=1, sticky='ew', padx=4, pady=2)

        edit_frame.columnconfigure(1, weight=1)

        self.emp_info_label = tk.Label(
            edit_frame,
            text="Сотрудник не найден",
            font=self.WIZARD_FONT,
            fg="red",
            wraplength=280,
        )
        self.emp_info_label.grid(row=11, column=0, columnspan=2, sticky='w', pady=3)

        # Кнопки сохранения
        btn_edit_frame = tk.Frame(right_frame)
        btn_edit_frame.pack(fill='x', pady=3)

        tk.Button(
            btn_edit_frame, text="Сохранить изменения", command=self.save_edits,
            bg='#ffc107', fg='black', font=self.WIZARD_FONT,
        ).pack(fill='x', pady=1)

        tk.Button(
            btn_edit_frame, text="Сохранить и добавить всех в заявку", command=self.save_and_add,
            bg='#28a745', fg='white', font=self.WIZARD_FONT,
        ).pack(fill='x', pady=1)

        search_row1 = tk.Frame(right_frame)
        search_row1.pack(fill="x", pady=2)
        tk.Label(search_row1, text="Поиск в базе:", font=self.WIZARD_FONT).pack(side="left")
        self.search_entry = tk.Entry(search_row1, font=self.WIZARD_FONT, width=22)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.search_employees())
        tk.Button(search_row1, text="Найти", command=self.search_employees).pack(side="left", padx=2)

        search_row2 = tk.Frame(right_frame)
        search_row2.pack(fill="x", pady=2)
        tk.Label(search_row2, text="ОП:", font=self.WIZARD_FONT).pack(side="left")
        self.search_dept_combo = ttk.Combobox(
            search_row2, font=self.WIZARD_FONT, width=28, state="readonly"
        )
        self.search_dept_combo.pack(side="left", padx=5)
        self.search_status_label = tk.Label(
            search_row2, text="", font=FONT_SMALL, fg=COLORS["text_muted"]
        )
        self.search_status_label.pack(side="left", padx=8)

        self.btn_add_to_form = tk.Button(
            search_row1, text="Добавить в анкету",
            command=self.add_selected_to_form,
            bg='#17a2b8', fg='white', font=self.WIZARD_FONT, padx=6,
        )
        self.btn_add_to_form.pack(side='left', padx=5)
        self.btn_add_to_form.config(state='disabled')  # По умолчанию неактивна

        # Таблица сотрудников
        table_frame = tk.Frame(right_frame)
        table_frame.pack(fill='both', expand=True, pady=10)

        tk.Label(
            table_frame,
            text="Двойной клик по строке — выбрать сотрудника из базы (зелёная подсветка)",
            font=FONT_SMALL,
            fg=COLORS["text_muted"],
        ).pack(anchor="w")

        columns = ('ФИО', 'Отдел', 'Статус', 'Таб. №')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')

        for col in columns:
            self.tree.heading(col, text=col)
            width = 90 if col == 'Статус' else 120
            self.tree.column(col, width=width)

        self.tree.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)

        # Кнопки действий
        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Выбрать сотрудника", command=self.select_employee,
            bg='#28a745', fg='white', font=self.WIZARD_FONT, padx=12,
        ).pack(fill='x', pady=1)

        tk.Button(
            btn_frame, text="Открыть каталог", command=self.open_catalog,
            bg='#17a2b8', fg='white', font=self.WIZARD_FONT, padx=10,
        ).pack(fill='x', pady=1)

        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.tag_configure("picked", background="#d4edda", foreground="#155724")
        self._picked_tree_iid = None

        self._setup_wizard_clipboard()
        self._reload_wizard_departments()

    def _reload_wizard_departments(self):
        depts = ["Все"]
        if employees_available():
            for d in get_department_list():
                d = str(d).strip()
                if d and d not in depts:
                    depts.append(d)
        self.search_dept_combo["values"] = depts
        if self._dept_filter and self._dept_filter in depts:
            self.search_dept_combo.set(self._dept_filter)
        elif self._dept_filter:
            extra = list(depts) + [self._dept_filter]
            self.search_dept_combo["values"] = extra
            self.search_dept_combo.set(self._dept_filter)
        else:
            self.search_dept_combo.set("Все")

    def _active_search_department(self):
        val = self.search_dept_combo.get().strip()
        if val in ("", "Все"):
            return None
        return val

    def _setup_wizard_clipboard(self):
        """Копирование/вставка в полях мастера и в таблице поиска."""
        widgets = [
            self.fio_entry,
            self.date1_entry,
            self.date2_entry,
            self.note1_entry,
            self.note2_entry,
            self.search_entry,
            self.route1_combo,
            self.route2_combo,
            self.transport1_combo,
            self.transport2_combo,
            self.reason1_combo,
            self.reason2_combo,
        ]
        bind_clipboard_shortcuts(widgets)

        def copy_tree_fio(_event=None):
            sel = self.tree.selection()
            if not sel:
                return "break"
            emp = self._emp_map.get(sel[0])
            if not emp:
                return "break"
            self.window.clipboard_clear()
            self.window.clipboard_append(emp.get("fio", ""))
            return "break"

        self.tree.bind("<Control-c>", copy_tree_fio, add="+")
        self.tree.bind("<Control-C>", copy_tree_fio, add="+")

    def _bind_route_autocomplete(self, combo: ttk.Combobox):
        """Подсказки маршрутов из справочника при вводе."""

        def refresh(_event=None):
            if _event is not None and _event.keysym in (
                "Up", "Down", "Return", "Tab", "Escape", "Shift_L", "Shift_R",
            ):
                return
            combo["values"] = filter_route_suggestions(combo.get(), self.routes)

        combo.bind("<KeyRelease>", refresh)
        combo.bind("<FocusIn>", refresh)

    def on_tree_select(self, event):
        """Активируем кнопку 'Добавить в анкету' при выборе сотрудника в таблице"""
        selection = self.tree.selection()
        if selection:
            self.btn_add_to_form.config(state='normal')
        else:
            self.btn_add_to_form.config(state='disabled')

    def _assign_employee_from_pick(self, emp: dict):
        """Привязать сотрудника из базы к текущей заявке (без сброса автопоиском)."""
        self.current_employee = emp
        self.fio_entry.delete(0, "end")
        self.fio_entry.insert(0, emp.get("fio", ""))
        self.fio_entry.configure(bg="#d4edda")
        self.emp_info_label.config(
            text=(
                f"✓ Из базы: {emp.get('fio', '')} | {get_employee_status(emp)}"
                f" | {emp.get('department', '')}"
            ),
            fg="#155724",
            bg="#d4edda",
        )
        self._highlight_picked_employee(emp)
        self.sync_form_to_result()

    def _highlight_picked_employee(self, emp: dict):
        """Зелёная подсветка выбранного сотрудника в таблице поиска."""
        target_hash = hash_fio(emp.get("fio", ""))
        if self._picked_tree_iid and self.tree.exists(self._picked_tree_iid):
            self.tree.item(self._picked_tree_iid, tags=())
        self._picked_tree_iid = None
        for iid, row_emp in self._emp_map.items():
            if hash_fio(row_emp.get("fio", "")) == target_hash:
                self.tree.selection_set(iid)
                self.tree.focus(iid)
                self.tree.see(iid)
                self.tree.item(iid, tags=("picked",))
                self._picked_tree_iid = iid
                break

    def add_selected_to_form(self):
        """Добавить выбранного в таблице сотрудника в поле ФИО"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите сотрудника в таблице")
            return

        selected_emp = self._emp_map.get(selection[0])

        if selected_emp:
            self._assign_employee_from_pick(selected_emp)
        else:
            messagebox.showerror("Ошибка", "Не удалось найти сотрудника")

    def on_reason1_change(self, event=None):
        reason1 = self.reason1_combo.get()
        route2 = self.route2_combo.get()
        reason2 = self.reason2_combo.get()
        date2 = self.date2_entry.get()
        route2, reason2, date2 = apply_reason1_rules(reason1, route2, reason2, date2)
        if reason1 in ("Увольнение", "Перевод в др. ОП"):
            self.route2_combo.set("")
            self.date2_entry.delete(0, "end")
            self.reason2_combo.set("")
        else:
            if not reason2:
                self.reason2_combo.set(suggest_reason2(reason1))
            if route2:
                self.route2_combo.set(route2)

    def on_route1_select(self, event=None):
        """Автоматически заполняем обратный маршрут при выборе Маршрута 1"""
        route1 = self.route1_combo.get()
        if route1 in self.reverse_routes:
            self.route2_combo.set(self.reverse_routes[route1])
        elif " - " in route1:
            parts = route1.split(" - ", 1)
            if len(parts) == 2:
                reverse = f"{parts[1].strip()} - {parts[0].strip()}"
                if reverse in self.routes:
                    self.route2_combo.set(reverse)
                else:
                    self.route2_combo.set(reverse)

    def on_fio_change(self, event=None):
        """Автоматический поиск сотрудника при изменении ФИО"""
        fio = self.fio_entry.get().strip()
        held = self.current_employee

        if len(fio) < 3:  # Минимум 3 символа для поиска
            if held and hash_fio(fio) == hash_fio(held.get("fio", "")):
                self.emp_info_label.config(
                    text=f"✓ Из базы: {held.get('fio', '')} | {get_employee_status(held)}",
                    fg="green",
                )
            else:
                self.emp_info_label.config(text="Введите минимум 3 символа", fg="orange", bg=self.window.cget("bg"))
                self.fio_entry.configure(bg="white")
                if not held:
                    self.current_employee = None
            return

        if held and hash_fio(fio) == hash_fio(held.get("fio", "")):
            self.emp_info_label.config(
                text=(
                    f"✓ Из базы: {held.get('fio', '')} | {get_employee_status(held)}"
                    f" | {held.get('department', '')}"
                ),
                fg="green",
            )
            self.sync_form_to_result()
            return

        emp, status = find_employee_by_fio(fio, self._dept_filter)

        if status == "found":
            self.current_employee = emp
            self.emp_info_label.config(
                text=f"✓ Найден: {emp.get('fio', '')} | {get_employee_status(emp)} | {emp.get('department', '')}",
                fg="green",
            )
            self.search_employees(fio)
            self.sync_form_to_result()
        elif status == "multiple":
            emps = emp if isinstance(emp, list) else []
            if held and any(
                hash_fio(e.get("fio", "")) == hash_fio(held.get("fio", "")) for e in emps
            ):
                self.current_employee = held
                self.emp_info_label.config(
                    text=f"✓ Из базы: {held.get('fio', '')} | {get_employee_status(held)}",
                    fg="green",
                )
                self.sync_form_to_result()
            else:
                self.current_employee = None
                self.emp_info_label.config(
                    text=(
                        f"Найдено несколько: {len(emps)} сотрудников. "
                        "Выберите из таблицы и нажмите «Добавить в анкету»"
                    ),
                    fg="orange",
                )
                self.show_multiple_employees(emps)
        else:
            self.current_employee = None
            self.fio_entry.configure(bg="white")
            self.emp_info_label.config(
                text="Сотрудник не найден. Двойной клик по строке в таблице — выбрать из базы",
                fg="red",
                bg=self.window.cget("bg"),
            )
            if not self.search_entry.get().strip():
                self.tree.delete(*self.tree.get_children())
                self._emp_map = {}

    def show_multiple_employees(self, employees):
        """Отображение нескольких найденных сотрудников"""
        if isinstance(employees, list):
            self._show_employees_in_tree(employees)
        else:
            self._show_employees_in_tree([employees])

    def _refresh_files_listbox(self):
        self.files_listbox.delete(0, tk.END)
        for i, result in enumerate(self.pdf_results):
            fn = result.get("source_file", "")
            pg = result.get("page", i + 1)
            fio = (result.get("fio", "") or "—")[:26]
            r1 = (result.get("route1") or result.get("route", ""))[:20]
            self.files_listbox.insert("end", f"{i + 1}. {fn} стр.{pg} · {fio} · {r1}")

    def _select_listbox_index(self, index: int):
        if 0 <= index < self.files_listbox.size():
            self.files_listbox.selection_clear(0, tk.END)
            self.files_listbox.selection_set(index)
            self.files_listbox.see(index)

    def _show_pdf_for_file(self, filename: str, page: int = 1):
        if not self.pdf_viewer or filename not in self.pdf_files:
            return
        self.pdf_viewer.load_pdf(self.pdf_files[filename], page=page)

    def sync_form_to_result(self):
        """Записать поля формы в текущий элемент pdf_results."""
        if self.current_index >= len(self.pdf_results):
            return
        r = self.pdf_results[self.current_index]
        r["fio"] = self.fio_entry.get().strip()
        r["route1"] = self.route1_combo.get().strip()
        r["route"] = r["route1"]
        r["route2"] = self.route2_combo.get().strip()
        r["date1"] = self.date1_entry.get().strip()
        r["date"] = r["date1"]
        r["date2"] = self.date2_entry.get().strip()
        r["transport1"] = self.transport1_combo.get().strip() or "АВИА"
        r["transport2"] = self.transport2_combo.get().strip()
        r["note1"] = self.note1_entry.get().strip()
        r["note2"] = self.note2_entry.get().strip()
        r["reason1"] = self.reason1_combo.get().strip()
        r["reason"] = r["reason1"]
        r["reason2"] = self.reason2_combo.get().strip()
        if self.current_employee:
            r["employee"] = self.current_employee

    def on_file_select(self, event):
        """Переключение заявки по списку — с сохранением предыдущей."""
        selection = self.files_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx == self.current_index:
            return
        self.sync_form_to_result()
        self.current_index = idx
        self._load_current()

    def load_result_to_form(self, result):
        """Загрузить данные результата в форму редактирования."""
        fn = result.get("source_file", "")
        pg = result.get("page", 1)
        self.nav_label.config(text=f"{fn} · стр. {pg}")

        self.fio_entry.delete(0, "end")
        self.fio_entry.insert(0, result.get("fio", ""))

        self.route1_combo.set(result.get("route1") or result.get("route", ""))
        self.date1_entry.delete(0, "end")
        self.date1_entry.insert(0, result.get("date1") or result.get("date", ""))

        self.route2_combo.set(result.get("route2", ""))
        self.date2_entry.delete(0, "end")
        self.date2_entry.insert(0, result.get("date2", ""))

        self.transport1_combo.set(result.get("transport1") or "АВИА")
        self.transport2_combo.set(result.get("transport2", ""))
        self.note1_entry.delete(0, "end")
        self.note1_entry.insert(0, result.get("note1", ""))
        self.note2_entry.delete(0, "end")
        self.note2_entry.insert(0, result.get("note2", ""))

        reason = result.get("reason1") or result.get("reason", "")
        self.reason1_combo.set(reason)
        self.reason2_combo.set(result.get("reason2", ""))
        self.on_reason1_change()

        emp = result.get("employee")
        if emp:
            self.current_employee = emp
            self.emp_info_label.config(
                text=(
                    f"✓ Из базы: {emp.get('fio', '')} | {get_employee_status(emp)}"
                    f" | {emp.get('department', '')}"
                ),
                fg="green",
            )
        else:
            self.current_employee = None
            self.on_fio_change()

    def _load_current(self):
        if self.current_index >= len(self.pdf_results):
            self.finish()
            return

        total = len(self.pdf_results)
        self.nav_label.config(
            text=f"Заявка {self.current_index + 1} из {total}  |  в заявку: {len(self.filled_results)}"
        )
        result = self.pdf_results[self.current_index]
        self._select_listbox_index(self.current_index)

        filename = result.get("source_file", "")
        page = int(result.get("page", 1) or 1)
        self._show_pdf_for_file(filename, page=page)
        self.load_result_to_form(result)

    def navigate_prev(self):
        self.sync_form_to_result()
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current()
        else:
            messagebox.showinfo("Навигация", "Это первая заявка", parent=self.window)

    def navigate_next(self):
        self.sync_form_to_result()
        if self.current_index < len(self.pdf_results) - 1:
            self.current_index += 1
            self._load_current()
        else:
            messagebox.showinfo(
                "Навигация",
                "Это последняя заявка. Нажмите «Сохранить и добавить всех в заявку».",
                parent=self.window,
            )

    def process_next(self):
        """Совместимость: загрузка текущей заявки при открытии мастера."""
        self._load_current()

    def save_edits(self):
        self.sync_form_to_result()
        self._refresh_files_listbox()
        self._select_listbox_index(self.current_index)
        messagebox.showinfo("Сохранено", "Изменения сохранены в текущей заявке", parent=self.window)

    def save_and_add(self):
        """Сохранить все заявки из очереди PDF и передать в таблицу."""
        self.sync_form_to_result()
        self.filled_results = []
        for result in self.pdf_results:
            item = result.copy()
            employee = item.get("employee")
            if not employee and (item.get("fio") or "").strip():
                emp, status = find_employee_by_fio(
                    item.get("fio", "").strip(),
                    self._dept_filter,
                )
                if status == "found":
                    employee = emp
                    item["employee"] = emp
            if employee:
                item["status"] = "selected"
            elif item.get("fio") or item.get("route1") or item.get("route"):
                item["employee"] = None
                item["status"] = "manual"
            else:
                item["employee"] = None
                item["status"] = "skipped"
            self.filled_results.append(item)
        self.finish()

    def _show_employees_in_tree(self, employees: list):
        self.tree.delete(*self.tree.get_children())
        self._emp_map = {}
        self._picked_tree_iid = None
        for idx, emp in enumerate(employees, 1):
            iid = f"w_{idx}"
            self._emp_map[iid] = emp
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    emp.get("fio", ""),
                    emp.get("department", ""),
                    get_employee_status(emp),
                    emp.get("tab_num", ""),
                ),
            )

    def search_employees(self, query=None):
        if query is None:
            query = self.search_entry.get().strip()
        if not query or len(query) < 2:
            self.tree.delete(*self.tree.get_children())
            self._emp_map = {}
            self.search_status_label.config(text="Минимум 2 символа для поиска")
            return
        if not employees_available():
            self.search_status_label.config(text="База не загружена", fg="red")
            messagebox.showwarning(
                "База",
                "База сотрудников не загружена.\nAdmin: Настройки → Загрузить базу.",
                parent=self.window,
            )
            return
        dept = self._active_search_department()
        records = get_employees_records(query, dept, limit=100)
        self._show_employees_in_tree(records)
        self.search_status_label.config(
            text=f"Найдено: {len(records)}" + (f" (ОП: {dept})" if dept else " (все ОП)"),
            fg=COLORS["text_muted"],
        )

    def on_tree_double_click(self, event):
        """Двойной клик по строке в таблице базы — заполнить анкету и подсветить зелёным."""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            sel = self.tree.selection()
            item_id = sel[0] if sel else ""
        if not item_id:
            return
        emp = self._emp_map.get(item_id)
        if emp:
            self._assign_employee_from_pick(emp)

    def select_employee(self):
        """Выбрать сотрудника из таблицы и добавить в анкету"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите сотрудника из списка")
            return

        selected_emp = self._emp_map.get(selection[0])
        if selected_emp:
            self._assign_employee_from_pick(selected_emp)
        else:
            messagebox.showerror("Ошибка", "Не удалось найти сотрудника в базе")

    def open_catalog(self):
        def on_select(employees):
            if employees:
                self._assign_employee_from_pick(employees[0])

        dept_filter = None if self.department == "Admin" else self.department
        EmployeeCatalogDialog(
            self.window,
            on_select,
            department_filter=dept_filter,
        )

    def skip_current(self):
        self.sync_form_to_result()
        result = self.pdf_results[self.current_index].copy()
        result["employee"] = None
        result["status"] = "skipped"
        self.filled_results.append(result)
        self.history.append(self.current_index)

        if self.current_index < len(self.pdf_results) - 1:
            self.current_index += 1
            self._load_current()
        else:
            self.finish()

    def finish(self):
        self.on_complete(self.filled_results)
        self.window.destroy()
