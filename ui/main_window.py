"""Главное окно приложения."""

import os
import subprocess
import sys

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from app_logger import log
from application_builder import build_rows_from_wizard_result, dataframe_from_rows
from auth import AuthManager, LoginWindow
from config import (
    APP_TITLE,
    APP_VERSION,
    BASE_GRID_PAGE_SIZE,
    REASONS,
    TESSERACT_CMD,
)
from database import (
    add_employees_from_application,
    count_filtered_employees,
    employees_available,
    export_employees_to_excel,
    find_employee_by_fio,
    get_employees_cache_meta,
    get_employees_count,
    get_employees_display_dataframe,
    hash_fio,
    load_employees_base,
    load_employees_cache,
    normalize_fio,
    save_employees_from_display_dataframe,
)
from draft_storage import clear_draft, load_draft, save_draft
from excel_handler import (
    ALL_COLUMNS,
    create_application_row,
    create_empty_row,
    employee_to_application_row,
    format_date_ddmmyyyy,
    merge_employee_into_application_row,
    save_as_excel,
)
from excel_sheet import ExcelSheetGrid
from fio_list_dialog import FioListDialog
from route_logic import apply_reason1_rules, suggest_reason2
from routes import build_reverse_map, load_routes
from settings_tab import SettingsTab
from template_manager import (
    build_export_filename,
    export_application,
    get_column_dropdowns,
    is_template_installed,
)
from ui import constants as route_constants
from ui.catalog import EmployeeCatalogDialog
from ui.helpers import _normalize_tab_num
from ui.onboarding import FirstRunDialog
from ui.toast import ToastManager
from ui.wizard import FillFromBaseWizard
from user_prefs import (
    draft_autosave_minutes,
    is_dark_theme,
    is_first_run,
    set_theme,
)
from ui.ctk_theme import (
    apply_ctk_appearance,
    apply_ttk_panel_style,
    configure_ctk_root,
    create_toolbar_button,
    embed_tk_frame,
    init_ctk,
    set_button_state,
)
from ui_theme import COLORS, FONT_HEADING, FONT_SMALL, FONT_TITLE, FONT_UI, style_tk_button
from users_manager import format_user_header, load_users_cache

if os.path.isfile(TESSERACT_CMD):
    os.environ["TESSERACT_CMD"] = TESSERACT_CMD
    tesseract_dir = os.path.dirname(TESSERACT_CMD)
    if tesseract_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = tesseract_dir + os.pathsep + os.environ.get("PATH", "")

ROUTES = route_constants.ROUTES
REVERSE_ROUTES = route_constants.REVERSE_ROUTES


class MainApp:
    def __init__(self):
        init_ctk(is_dark_theme())
        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.geometry("1800x1000")
        configure_ctk_root(self.root)
        apply_ttk_panel_style()
        self.toast = ToastManager(self.root)
        self._settings_tab_name = None
        self._autosave_job = None
        try:
            self.root.state('zoomed')
        except tk.TclError:
            self.root.attributes("-zoomed", True)

        self.auth = AuthManager()
        self.current_department = None
        self.is_admin = False
        self.pdf_results = []
        self.pdf_files = {}
        self.applications_df = None
        self.selected_employees_history = []
        self.existing_tab_nums = set()
        self._base_tab_loaded = False
        self.base_search_var = tk.StringVar()
        self.base_page_offset = 0

        self._create_menu()
        self.create_ui()
        self.show_login()
        log.info("Приложение запущено v%s", APP_VERSION)

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Сохранить черновик", command=self.save_draft_file)
        file_menu.add_command(label="Загрузить черновик", command=self.load_draft_file)
        file_menu.add_command(
            label="Обновить общую базу сотрудников",
            command=self.reload_shared_database,
        )
        file_menu.add_command(label="Сменить пользователя", command=self.switch_user)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.logout)
        menubar.add_cascade(label="Файл", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        self._dark_theme_var = tk.BooleanVar(value=is_dark_theme())
        view_menu.add_checkbutton(
            label="Тёмная тема",
            variable=self._dark_theme_var,
            command=self._toggle_theme_pref,
        )
        view_menu.add_command(label="Показать подсказки", command=self._show_onboarding)
        menubar.add_cascade(label="Вид", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Проверка системы", command=self.run_self_check)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)
        self.root.config(menu=menubar)

    def show_about(self):
        from config import BASE_DIR, DATA_DIR, EMPLOYEES_CACHE_FILE
        from routes import ROUTES_FILE
        from pdf_processor import TESSERACT_AVAILABLE, CV2_AVAILABLE

        ocr = "да" if TESSERACT_AVAILABLE and CV2_AVAILABLE else "нет (только текстовые PDF)"
        messagebox.showinfo(
            APP_TITLE,
            f"Версия: {APP_VERSION}\n\n"
            f"Папка программы:\n{BASE_DIR}\n\n"
            f"Данные: {DATA_DIR}\n"
            f"База сотрудников: {EMPLOYEES_CACHE_FILE.name}\n"
            f"Маршруты: {ROUTES_FILE.name}\n"
            f"OCR: {ocr}\n\n"
            "1. Admin загружает Excel-базу\n"
            "2. Обработка PDF или каталог сотрудников\n"
            "3. Экспорт заявки в Excel",
            parent=self.root,
        )

    def _toggle_theme_pref(self):
        dark = bool(self._dark_theme_var.get())
        set_theme("dark" if dark else "light")
        apply_ctk_appearance(dark)
        apply_ttk_panel_style()
        self.toast.show(
            "Тема переключена.",
            "info",
            3000,
        )

    def _show_onboarding(self):
        FirstRunDialog(self.root)

    def _maybe_show_onboarding(self):
        if is_first_run():
            self.root.after(400, lambda: FirstRunDialog(self.root))

    def _cancel_autosave(self):
        if self._autosave_job is not None:
            try:
                self.root.after_cancel(self._autosave_job)
            except tk.TclError:
                pass
            self._autosave_job = None

    def _start_autosave(self):
        self._cancel_autosave()
        interval_ms = draft_autosave_minutes() * 60 * 1000

        def tick():
            self._autosave_draft_silent()
            self._autosave_job = self.root.after(interval_ms, tick)

        self._autosave_job = self.root.after(interval_ms, tick)

    def _autosave_draft_silent(self):
        df = self.application_grid.get_dataframe() if hasattr(self, "application_grid") else None
        if df is None or df.empty or not self.current_department:
            return
        ok, msg = save_draft(df, self.current_department, self.existing_tab_nums)
        if ok:
            self.toast.show(msg, "success", 2500)

    def run_self_check(self):
        from config import BASE_DIR

        py = sys.executable
        script = str(BASE_DIR / "check_app.py")
        try:
            result = subprocess.run(
                [py, script],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
                timeout=60,
            )
            text = (result.stdout or "") + (result.stderr or "")
            if result.returncode == 0:
                messagebox.showinfo("Проверка", text or "Все проверки пройдены.", parent=self.root)
            else:
                messagebox.showerror("Проверка", text or "Есть ошибки.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Проверка", str(e), parent=self.root)

    def save_draft_file(self):
        if self.applications_df is None or self.applications_df.empty:
            messagebox.showwarning("Черновик", "Нет данных заявки", parent=self.root)
            return
        ok, msg = save_draft(self.applications_df, self.current_department, self.existing_tab_nums)
        if ok:
            self.toast.show(msg, "success")
            self.status_label.config(text=msg)
        else:
            self.toast.show(msg, "warning")

    def load_draft_file(self):
        if self.applications_df is not None and not self.applications_df.empty:
            if not messagebox.askyesno("Черновик", "Заменить текущую заявку?", parent=self.root):
                return
        ok, msg, df, tab_nums = load_draft(self.current_department)
        if not ok:
            messagebox.showwarning("Черновик", msg, parent=self.root)
            return
        self.applications_df = df
        self.existing_tab_nums = set(tab_nums)
        self.display_table()
        set_button_state(self.btn_export, True)
        set_button_state(self.btn_clear, True)
        self.status_label.config(text=msg)
        messagebox.showinfo("Черновик", msg, parent=self.root)

    def _style_toolbar_button(self, parent, text, command, variant="primary", state="normal"):
        btn = create_toolbar_button(parent, text, command, variant, state=state)
        btn.pack(side="left", padx=4, pady=8)
        return btn

    def create_ui(self):
        top_frame = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"], corner_radius=0, height=64)
        top_frame.pack(fill="x")
        top_frame.pack_propagate(False)

        ctk.CTkLabel(
            top_frame,
            text="Система заявок на билеты",
            font=FONT_TITLE,
            text_color=COLORS["white"],
        ).pack(side="left", padx=20, pady=14)

        user_box = ctk.CTkFrame(top_frame, fg_color="transparent")
        user_box.pack(side="right", padx=16, pady=6)

        self.user_dept_label = ctk.CTkLabel(
            user_box,
            text="Не авторизован",
            font=FONT_HEADING,
            text_color=COLORS["white"],
            anchor="e",
            justify="right",
        )
        self.user_dept_label.pack(anchor="e")

        self.user_profile_label = ctk.CTkLabel(
            user_box,
            text="",
            font=FONT_SMALL,
            text_color="#a8b2c1",
            anchor="e",
            justify="right",
            wraplength=420,
        )
        self.user_profile_label.pack(anchor="e")

        toolbar = ctk.CTkFrame(self.root, fg_color=COLORS["bg_toolbar"], corner_radius=0, height=56)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self.btn_catalog = self._style_toolbar_button(
            toolbar, "Каталог", self.open_catalog, "info", state='disabled'
        )
        self.btn_select_file = self._style_toolbar_button(
            toolbar, "PDF файл", self.select_single_file, "primary"
        )
        self.btn_select_folder = self._style_toolbar_button(
            toolbar, "Папка PDF", self.select_folder, "primary"
        )
        self.btn_from_list = self._style_toolbar_button(
            toolbar, "Из списка", self.open_fio_list, "info", state="disabled"
        )
        self.btn_fill = self._style_toolbar_button(
            toolbar, "Заполнить из базы", self.fill_from_database, "primary", state='disabled'
        )
        self.btn_add_to_db = self._style_toolbar_button(
            toolbar, "Добавить в базу", self.add_missing_to_database, "info", state='disabled'
        )
        self.btn_export = self._style_toolbar_button(
            toolbar, "Экспорт Excel", self.export_to_excel, "accent", state='disabled'
        )
        self.btn_clear = self._style_toolbar_button(
            toolbar, "Очистить", self.clear_all, "danger", state='disabled'
        )

        self._style_toolbar_button(toolbar, "Сменить пользователя", self.switch_user, "muted").pack(
            side="right", padx=4, pady=8
        )
        logout_btn = create_toolbar_button(toolbar, "Выход", self.logout, "muted")
        logout_btn.pack(side="right", padx=10, pady=8)

        self.tabview = ctk.CTkTabview(self.root, fg_color=COLORS["bg_panel"])
        self.tabview.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        self.work_tab = self.tabview.add("Заявка")
        self.base_tab = self.tabview.add("База")
        try:
            self.tabview._segmented_button.configure(command=lambda _v: self._on_notebook_tab_changed())
        except AttributeError:
            pass

        self.settings_tab = None
        self._settings_tab_name = None
        self._build_base_tab()

        work_host = embed_tk_frame(self.work_tab)
        left_frame = ttk.Frame(work_host)
        left_frame.pack(fill="both", expand=True)
        self.pdf_viewer = None

        pdf_list_frame = ttk.LabelFrame(left_frame, text="Обработанные PDF", padding=5)
        pdf_list_frame.pack(fill='x', padx=5, pady=5)

        scrollbar = ttk.Scrollbar(pdf_list_frame)
        self.pdf_listbox = tk.Listbox(pdf_list_frame, height=3, font=('Arial', 10),
                                      yscrollcommand=scrollbar.set)
        self.pdf_listbox.pack(side='left', fill='x', expand=True)
        scrollbar.config(command=self.pdf_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.pdf_listbox.bind('<<ListboxSelect>>', self.on_pdf_select)

        grid_frame = ttk.LabelFrame(left_frame, text="Заявка — таблица Excel", padding=5)
        grid_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.application_grid = ExcelSheetGrid(
            grid_frame,
            columns=ALL_COLUMNS,
            on_change=self._on_grid_changed,
            dropdowns=get_column_dropdowns(),
            on_cell_edited=self._on_application_cell_edited,
        )
        self.application_grid.pack(fill='both', expand=True)
        self.table = self.application_grid
        if self.application_grid._sheet:
            self.application_grid._sheet.bind("<Double-Button-1>", self.on_table_double_click)

        self.status_label = ctk.CTkLabel(
            self.root,
            text="Готов к работе",
            anchor="w",
            font=FONT_UI,
            fg_color=COLORS["white"],
            text_color=COLORS["text"],
            corner_radius=0,
            height=36,
        )
        self.status_label.pack(side="bottom", fill="x")

        self.progress_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="", font=FONT_UI)
        self.progress_label.pack(side="left", padx=10)
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=320)
        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.set(0)

    def open_fio_list(self):
        if not self._ensure_employees_db():
            return
        FioListDialog(
            self.root,
            self.current_department,
            self.is_admin,
            on_create_application=self._apply_employees_to_application,
        )

    def _application_rows_with_fio(self, df: pd.DataFrame, fio: str) -> list:
        """Индексы строк заявки с тем же ФИО (как в OCR), без учёта регистра."""
        key = normalize_fio(fio)
        if not key or df is None or df.empty:
            return []
        rows = []
        for i in range(len(df)):
            cell = str(df.at[i, "Ф.И.О."]).strip()
            if cell and normalize_fio(cell) == key:
                rows.append(i)
        return rows

    def _open_catalog_for_row(self, row: int, fio: str):
        """Каталог с поиском по ФИО; при выборе — только поля из базы, OCR-поля сохраняются."""

        df = self.application_grid.get_dataframe()
        matching_rows = self._application_rows_with_fio(df, fio)
        if row not in matching_rows and 0 <= row < len(df):
            matching_rows = sorted(set(matching_rows + [row]))

        def on_pick(employees, apply_all_fio=False, bind_row=0, source_fio=""):
            if not employees:
                return 0
            emp = employees[0]
            df_local = self.application_grid.get_dataframe()
            if df_local is None or df_local.empty:
                return 0

            if apply_all_fio and source_fio:
                rows_to_update = self._application_rows_with_fio(df_local, source_fio)
            else:
                rows_to_update = [bind_row]

            if not rows_to_update:
                return 0

            updated = 0
            for r in rows_to_update:
                if r < 0 or r >= len(df_local):
                    continue
                existing = {col: df_local.at[r, col] for col in df_local.columns}
                merged = merge_employee_into_application_row(existing, emp, r + 1)
                for col, val in merged.items():
                    if col in df_local.columns:
                        df_local.at[r, col] = val
                updated += 1

            self.application_grid.load_dataframe(df_local)
            self.applications_df = df_local.copy()
            tab = _normalize_tab_num(emp.get("tab_num"))
            if tab:
                self.existing_tab_nums.add(tab)
            self._on_grid_changed()
            return updated

        dept_filter = None if self.is_admin else self.current_department
        EmployeeCatalogDialog(
            self.root,
            on_pick,
            added_tab_nums=self.existing_tab_nums,
            department_filter=dept_filter,
            initial_search=fio,
            bind_row_index=row,
            match_fio=fio,
            duplicate_row_count=len(matching_rows),
        )

    def on_table_double_click(self, event):
        df = self.application_grid.get_dataframe()
        if df.empty or not self.application_grid._sheet:
            return
        sel = self.application_grid._sheet.get_currently_selected()
        row = sel[0] if isinstance(sel, (list, tuple)) and sel else None
        if row is None or row < 0 or row >= len(df):
            return
        fio = str(df.at[row, "Ф.И.О."]).strip()
        if not fio:
            return

        note = str(df.at[row, "Примечание"])
        is_not_found = "НЕ НАЙДЕН" in note.upper()
        dept_filter = None if self.is_admin else self.current_department
        emp, status = find_employee_by_fio(fio, dept_filter)

        if status == "found" and not is_not_found:
            EmployeeDetailDialog(self.root, emp)
            return

        self._open_catalog_for_row(row, fio)

    def _clear_application_grid(self):
        """Чистая пустая заявка (без строк)."""
        empty = pd.DataFrame(columns=ALL_COLUMNS)
        self.application_grid.load_dataframe(empty)
        self.applications_df = empty.copy()
        self._on_grid_changed()

    def _apply_employees_to_application(self, employees: list) -> int:
        """Добавить сотрудников в заявку (сначала в пустые строки)."""
        if not employees:
            return 0

        df = self.application_grid.get_dataframe()
        if df is None or df.empty:
            df = pd.DataFrame(columns=ALL_COLUMNS)

        empty_slots = []
        for i in range(len(df)):
            if not str(df.at[i, "Ф.И.О."]).strip():
                empty_slots.append(i)

        updates = {}
        added_count = 0
        next_new_idx = len(df) + 1
        new_rows = []

        for emp in employees:
            tab_num = _normalize_tab_num(emp.get("tab_num"))
            if tab_num and tab_num in self.existing_tab_nums:
                continue

            empty_pdf_data = {
                "source_file": "Каталог",
                "direction": "туда",
                "fio": emp.get("fio", ""),
                "route": "",
                "date": "",
                "reason": "",
                "phone": emp.get("phone", ""),
            }

            if empty_slots:
                row_i = empty_slots.pop(0)
                row_num = row_i + 1
                filled = create_application_row(
                    row_num, self.current_department, empty_pdf_data, emp
                )
                updates[row_i] = filled
            else:
                filled = create_application_row(
                    next_new_idx, self.current_department, empty_pdf_data, emp
                )
                new_rows.append(filled)
                next_new_idx += 1

            if tab_num:
                self.existing_tab_nums.add(tab_num)
            added_count += 1

        if updates:
            for row_i, filled in updates.items():
                for col, val in filled.items():
                    if col in df.columns:
                        df.at[row_i, col] = val

        if new_rows:
            new_df = pd.DataFrame(new_rows, columns=ALL_COLUMNS)
            df = pd.concat([df, new_df], ignore_index=True)

        if updates or new_rows:
            df["№"] = range(1, len(df) + 1)
            self.application_grid.load_dataframe(df)
            self.applications_df = df.copy()

        if added_count:
            self._on_grid_changed()
            self.status_label.config(text=f"В заявке: {len(self.applications_df)} строк")

        return added_count

    def open_catalog(self):
        if not self._ensure_employees_db():
            return

        def on_select(employees):
            return self._apply_employees_to_application(employees)

        dept_filter = None if self.is_admin else self.current_department
        EmployeeCatalogDialog(
            self.root,
            on_select,
            added_tab_nums=self.existing_tab_nums,
            department_filter=dept_filter,
        )

    def clear_all(self):
        if messagebox.askyesno("Подтверждение", "Очистить все заявки?", parent=self.root):
            self.applications_df = None
            self.pdf_results = []
            self.pdf_files = {}
            self.existing_tab_nums.clear()
            clear_draft()
            self.pdf_listbox.delete(0, 'end')
            if self.pdf_viewer:
                self.pdf_viewer.close()
            self._clear_application_grid()
            self._sync_fill_button()
            self.status_label.config(text="Заявка очищена")

    def show_login(self):
        login = LoginWindow(self.root, self.auth)
        self.root.wait_window(login.window)

        if self.auth.current_user:
            self.current_department = self.auth.current_user
            self.is_admin = self.auth.is_admin
            self.selected_employees_history = []
            load_users_cache()
            self.status_label.config(text="Загрузка общей базы…")
            self.root.update_idletasks()
            self._setup_settings_tab()
            ok_db, msg_db, _ = load_employees_cache(force=True)
            self.update_ui()
            self.status_label.config(text=msg_db if ok_db else f"{self.current_department} | {msg_db}")
            self._clear_application_grid()
            self._start_autosave()
            self._maybe_show_onboarding()
            if ok_db:
                self.toast.show(msg_db, "info", 4000)
        else:
            self.root.quit()

    def reload_shared_database(self):
        """Перечитать общий кэш с диска (доступно всем после загрузки Admin)."""
        ok, message, _ = load_employees_cache(force=True)
        if ok:
            self.on_database_updated()
            self.toast.show(message, "success")
        else:
            self.toast.show(message, "warning")

    def _ensure_employees_db(self) -> bool:
        if employees_available():
            return True
        ok, message, _ = load_employees_cache(force=True)
        if ok:
            self.status_label.config(text=message)
            return True
        messagebox.showwarning(
            "База не загружена",
            f"{message}\n\nОбщая база загружается Admin в «Настройки» → «Загрузить базу».",
        )
        return False

    def _setup_settings_tab(self):
        if self.is_admin:
            if self.settings_tab is None:
                self._settings_tab_name = "Настройки"
                settings_ctk = self.tabview.add(self._settings_tab_name)
                settings_host = embed_tk_frame(settings_ctk)
                self.settings_tab = SettingsTab(settings_host, self)
        elif self.settings_tab is not None and self._settings_tab_name:
            try:
                self.tabview.delete(self._settings_tab_name)
            except (ValueError, tk.TclError):
                pass
            self.settings_tab = None
            self._settings_tab_name = None

    def _build_base_tab(self):
        base_host = embed_tk_frame(self.base_tab)
        bar = ttk.Frame(base_host)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Label(bar, text="Поиск (ФИО / таб. №):").pack(side="left", padx=(0, 4))
        search_entry = ttk.Entry(bar, textvariable=self.base_search_var, width=28)
        search_entry.pack(side="left", padx=2)
        search_entry.bind("<Return>", lambda e: self.refresh_base_tab())
        ttk.Button(bar, text="Найти", command=self._base_search_reset).pack(side="left", padx=4)
        ttk.Button(bar, text="◀ Назад", command=self._base_page_prev).pack(side="left", padx=2)
        ttk.Button(bar, text="Далее ▶", command=self._base_page_next).pack(side="left", padx=2)
        ttk.Button(bar, text="Сохранить правки", command=self.save_base_tab).pack(side="left", padx=4)
        self.base_status_label = ttk.Label(
            bar,
            text=f"Показывается до {BASE_GRID_PAGE_SIZE} строк. Введите ФИО для поиска.",
            font=FONT_SMALL,
        )
        self.base_status_label.pack(side="left", padx=12)

        base_frame = ttk.Frame(base_host)
        base_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.base_grid = ExcelSheetGrid(
            base_frame,
            columns=ALL_COLUMNS,
            dropdowns=get_column_dropdowns(),
        )
        self.base_grid.pack(fill="both", expand=True)

    def _base_department_filter(self):
        return None if self.is_admin else self.current_department

    def _base_search_reset(self):
        self.base_page_offset = 0
        self.refresh_base_tab()

    def _base_page_prev(self):
        if self.base_page_offset >= BASE_GRID_PAGE_SIZE:
            self.base_page_offset -= BASE_GRID_PAGE_SIZE
        self.refresh_base_tab()

    def _base_page_next(self):
        self.base_page_offset += BASE_GRID_PAGE_SIZE
        self.refresh_base_tab()

    def refresh_base_tab(self):
        if not employees_available():
            messagebox.showwarning("База", "Сначала загрузите базу (Настройки → Admin).", parent=self.root)
            return
        search = self.base_search_var.get().strip() or None
        dept = self._base_department_filter()
        total = count_filtered_employees(search, dept)
        if total == 0:
            self.base_grid.load_dataframe(None)
            self.base_status_label.config(text="Ничего не найдено. Уточните поиск.")
            self.base_page_offset = 0
            return
        if self.base_page_offset >= total:
            self.base_page_offset = max(0, total - BASE_GRID_PAGE_SIZE)
        self.status_label.config(text="Загрузка таблицы…")
        self.root.update_idletasks()
        df = get_employees_display_dataframe(
            search=search,
            department=dept,
            limit=BASE_GRID_PAGE_SIZE,
            offset=self.base_page_offset,
        )
        self.base_grid.load_dataframe(df)
        shown = len(df)
        page_from = self.base_page_offset + 1
        page_to = self.base_page_offset + shown
        hint = f"Строки {page_from}–{page_to} из {total}"
        self.base_status_label.config(text=hint)
        self.status_label.config(text=f"База: {get_employees_count()} сотрудников (SQLite)")

    def _on_notebook_tab_changed(self, _event=None):
        try:
            tab = self.tabview.get()
        except (AttributeError, tk.TclError):
            return
        if tab != "База" or not employees_available():
            return
        if not self._base_tab_loaded:
            self._base_tab_loaded = True
            self.refresh_base_tab()

    def save_base_tab(self):
        if not self.is_admin:
            messagebox.showwarning("База", "Сохранение базы доступно только Admin.", parent=self.root)
            return
        df = self.base_grid.get_dataframe()
        ok, msg = save_employees_from_display_dataframe(df)
        if ok:
            messagebox.showinfo("База", msg, parent=self.root)
            self.on_database_updated()
        else:
            messagebox.showerror("База", msg, parent=self.root)

    def _on_application_cell_edited(self, row: int, col_name: str, value: str):
        if col_name != "Ф.И.О." or not value.strip():
            return
        dept_filter = None if self.is_admin else self.current_department
        emp, status = find_employee_by_fio(value.strip(), dept_filter)
        if status != "found":
            return
        df = self.application_grid.get_dataframe()
        if row >= len(df):
            return
        existing = {col: df.at[row, col] for col in df.columns}
        if str(existing.get("Маршрут", "")).strip():
            filled = merge_employee_into_application_row(existing, emp, row + 1)
        else:
            filled = employee_to_application_row(emp, row + 1)
        for col, val in filled.items():
            if col in df.columns:
                df.at[row, col] = val
        self.application_grid.load_dataframe(df)

    def switch_user(self):
        if not self.auth.current_user:
            self.show_login()
            return
        if not messagebox.askyesno(
            "Сменить пользователя",
            "Текущая заявка будет сброшена. Войти под другим логином?",
            parent=self.root,
        ):
            return
        self._clear_session(keep_window=True)
        self.show_login()

    def _clear_session(self, keep_window: bool = False):
        self._cancel_autosave()
        self.auth.logout()
        self.current_department = None
        self.is_admin = False
        self.pdf_results = []
        self.pdf_files = {}
        self.applications_df = None
        self.selected_employees_history = []
        self.existing_tab_nums.clear()
        self._clear_application_grid()
        self.base_grid.load_dataframe(None)
        self._base_tab_loaded = False
        self.base_search_var.set("")
        self.pdf_listbox.delete(0, 'end')
        if self.pdf_viewer:
            self.pdf_viewer.close()
        self._sync_fill_button()
        set_button_state(self.btn_export, False)
        set_button_state(self.btn_catalog, False)
        set_button_state(self.btn_from_list, False)
        set_button_state(self.btn_clear, False)
        set_button_state(self.btn_add_to_db, False)
        if self.settings_tab is not None and self._settings_tab_name:
            try:
                self.tabview.delete(self._settings_tab_name)
            except (ValueError, tk.TclError):
                pass
            self.settings_tab = None
            self._settings_tab_name = None
        self.user_dept_label.config(text="Не авторизован")
        self.user_profile_label.config(text="")
        if not keep_window:
            pass

    def on_database_updated(self):
        load_employees_cache(force=True)
        if self._base_tab_loaded:
            self.refresh_base_tab()
        self.application_grid.refresh_dropdowns(get_column_dropdowns())
        if hasattr(self, "base_grid"):
            self.base_grid.refresh_dropdowns(get_column_dropdowns())
        self.update_ui()

    def on_template_updated(self):
        dd = get_column_dropdowns()
        self.application_grid.refresh_dropdowns(dd)
        self.base_grid.refresh_dropdowns(dd)
        lists = get_column_dropdowns()
        if lists.get("Маршрут"):
            route_constants.ROUTES = sorted(set(load_routes()) | set(lists["Маршрут"]))
            route_constants.REVERSE_ROUTES = build_reverse_map(route_constants.ROUTES)

    def _sync_fill_button(self):
        """Активна, если есть необработанные или повторно открываемые результаты PDF."""
        if self.pdf_results:
            set_button_state(self.btn_fill, True)
        else:
            set_button_state(self.btn_fill, False)

    def _on_grid_changed(self):
        self.applications_df = self.application_grid.get_dataframe()
        has_data = self.applications_df is not None and not self.applications_df.empty
        set_button_state(self.btn_export, has_data)
        set_button_state(self.btn_clear, has_data)
        set_button_state(self.btn_add_to_db, has_data)

    def _refresh_user_header(self):
        dept_line, profile = format_user_header(
            self.auth.app_user,
            self.current_department or "",
            self.is_admin,
        )
        self.user_dept_label.config(text=dept_line)
        self.user_profile_label.config(text=profile)

    def update_ui(self):
        if self.current_department:
            self._refresh_user_header()
            meta = get_employees_cache_meta()
            status_parts = []
            if employees_available():
                status_parts.append(f"Общая база: {get_employees_count()} чел.")
            if meta.get("updated_at"):
                status_parts.append(f"обновлено {meta['updated_at']}")
            if is_template_installed():
                status_parts.append("шаблон ✓")
            if status_parts:
                self.status_label.config(text=" | ".join(status_parts))
            ok_db = employees_available()
            set_button_state(self.btn_catalog, ok_db)
            set_button_state(self.btn_from_list, ok_db)
            self._setup_settings_tab()

    def add_missing_to_database(self):
        df = self.application_grid.get_dataframe()
        if df is None or df.empty:
            messagebox.showwarning("База", "Нет данных заявки", parent=self.root)
            return
        dept = None if self.is_admin else self.current_department
        added, skipped = add_employees_from_application(df, dept)
        messagebox.showinfo(
            "База",
            f"Добавлено в базу: {added}\nУже были / пропущено: {skipped}",
            parent=self.root,
        )
        self.on_database_updated()

    def select_single_file(self):
        if not self._ensure_employees_db():
            return

        file_path = filedialog.askopenfilename(
            title="Выберите PDF файл",
            filetypes=[("PDF", "*.pdf")]
        )

        if file_path:
            self.process_single_pdf(file_path)

    def select_folder(self):
        if not self._ensure_employees_db():
            return

        folder = filedialog.askdirectory(title="Выберите папку с PDF")

        if folder:
            self.process_pdfs(folder)

    def process_single_pdf(self, file_path: str):
        filename = os.path.basename(file_path)
        self.pdf_files[filename] = file_path

        self.progress_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        self.progress_bar.set(0.1)
        self.progress_label.configure(text="Обработка PDF (фон)…")
        self.root.update_idletasks()

        from pdf_worker import run_single_pdf_async

        def on_done(ok, msg, results, err):
            def finish():
                self.progress_frame.pack_forget()
                if not ok:
                    messagebox.showerror("Ошибка", msg, parent=self.root)
                    return
                self.pdf_results.extend(results)
                self.update_pdf_list()
                self._sync_fill_button()
                if results:
                    self.fill_from_database()
                else:
                    messagebox.showwarning(
                        "Внимание",
                        "Не удалось извлечь данные из PDF.",
                        parent=self.root,
                    )
                self.status_label.config(text=f"PDF: {len(self.pdf_results)} заявок")

            self.root.after(0, finish)

        run_single_pdf_async(file_path, on_done=on_done)

    def process_pdfs(self, folder_path: str):
        from pathlib import Path
        from pdf_worker import run_pdf_folder_async

        for pdf_file in Path(folder_path).glob("*.pdf"):
            filename = os.path.basename(str(pdf_file))
            self.pdf_files[filename] = str(pdf_file)

        self.progress_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        self.progress_label.configure(text="Обработка PDF (фон)…")
        self.root.update_idletasks()

        def on_progress(current, total, message):
            def tick():
                denom = max(total, 1)
                self.progress_bar.set(current / denom)
                self.progress_label.configure(text=message)

            self.root.after(0, tick)

        def on_done(ok, msg, results, err):
            def finish():
                self.progress_frame.pack_forget()
                if not ok:
                    messagebox.showerror("Ошибка", msg, parent=self.root)
                    return
                self.pdf_results.extend(results)
                self.update_pdf_list()
                self._sync_fill_button()
                if results:
                    self.fill_from_database()
                else:
                    messagebox.showwarning("Внимание", "Не удалось извлечь данные из PDF.", parent=self.root)
                self.status_label.config(text=f"PDF: {len(self.pdf_results)} заявок")

            self.root.after(0, finish)

        run_pdf_folder_async(folder_path, on_progress=on_progress, on_done=on_done)

    def update_pdf_list(self):
        self.pdf_listbox.delete(0, 'end')
        seen_files = set()
        for result in self.pdf_results:
            filename = result.get('source_file', '')
            if filename not in seen_files:
                seen_files.add(filename)
                self.pdf_listbox.insert('end', f"{filename}")

    def on_pdf_select(self, event):
        pass

    def fill_from_database(self):
        if not self.pdf_results:
            messagebox.showwarning("Внимание", "Сначала обработайте PDF!")
            return
        if not self._ensure_employees_db():
            return

        def on_complete(filled_results):
            self.add_to_dataframe(filled_results)
            # PDF не удаляем — можно снова открыть мастер при необходимости
            self._sync_fill_button()
            self.status_label.config(
                text=f"Мастер завершён. PDF в очереди: {len(self.pdf_results)}. "
                "Очистите заявку или обработайте новые файлы."
            )
            log.info("Мастер PDF завершён, добавлено записей: %s", len(filled_results))

        FillFromBaseWizard(
            self.root,
            self.pdf_results,
            self.pdf_files,
            self.current_department,
            on_complete,
            routes=route_constants.ROUTES,
        )

    def add_to_dataframe(self, results):
        if not results:
            return

        if self.applications_df is not None and not self.applications_df.empty:
            start_idx = len(self.applications_df) + 1
        else:
            start_idx = 1

        all_rows = []
        added_count = 0
        skipped_count = 0

        for result in results:
            if result.get("employee"):
                tab_num = result["employee"].get("tab_num", "")
                if tab_num and tab_num in self.existing_tab_nums:
                    skipped_count += 1
                    continue
                if tab_num:
                    self.existing_tab_nums.add(tab_num)

            rows = build_rows_from_wizard_result(result, self.current_department, start_idx + added_count)
            if not rows and result.get("status") == "skipped":
                skipped_count += 1
                continue
            all_rows.extend(rows)
            added_count += len(rows)

        if all_rows:
            self.application_grid.append_rows(all_rows)
            self.applications_df = self.application_grid.get_dataframe()
            msg = f"Добавлено строк: {len(all_rows)}"
            if skipped_count > 0:
                msg += f"\nПропущено: {skipped_count}"
            messagebox.showinfo("Готово", msg, parent=self.root)

    def display_table(self):
        self.application_grid.load_dataframe(self.applications_df)
        self._on_grid_changed()

    def export_to_excel(self):
        self.applications_df = self.application_grid.get_dataframe()
        if self.applications_df is None or self.applications_df.empty:
            messagebox.showwarning("Внимание", "Нет данных!", parent=self.root)
            return

        default_name = build_export_filename(self.applications_df, self.current_department or "ОП")

        file_path = filedialog.asksaveasfilename(
            title="Сохранить как",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel", "*.xlsx")],
            parent=self.root,
        )

        if file_path:
            ok, msg = export_application(self.applications_df, file_path)
            if ok:
                messagebox.showinfo("Успех", msg, parent=self.root)
            else:
                messagebox.showerror("Ошибка", msg, parent=self.root)

    def logout(self):
        if messagebox.askyesno("Выход", "Вы уверены?", parent=self.root):
            self._clear_session(keep_window=True)
            self.show_login()

    def run(self):
        self.root.mainloop()
