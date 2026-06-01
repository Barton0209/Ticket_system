# excel_sheet.py
"""Таблица в стиле Excel на базе tksheet."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

import pandas as pd
from openpyxl.utils import get_column_letter

from config import ALL_COLUMNS
from ui_theme import COLORS, FONT_SMALL

try:
    from tksheet import Sheet

    TKSHEET_AVAILABLE = True
except ImportError:
    TKSHEET_AVAILABLE = False
    Sheet = None


class ExcelSheetGrid(ttk.Frame):
    """Редактируемая таблица: клик по ячейке, Enter, стрелки, Ctrl+C/V."""

    def __init__(
        self,
        parent,
        columns: Optional[List[str]] = None,
        on_change: Optional[Callable] = None,
        dropdowns: Optional[Dict[str, List[str]]] = None,
        on_cell_edited: Optional[Callable[[int, str, str], None]] = None,
        show_row_numbers: bool = True,
    ):
        super().__init__(parent)
        self.columns = list(columns or ALL_COLUMNS)
        self.on_change = on_change
        self.on_cell_edited = on_cell_edited
        self.dropdowns = dropdowns or {}
        self.df = pd.DataFrame(columns=self.columns)
        self._sheet = None
        self._loading = False
        self._build_ui(show_row_numbers)

    def _build_ui(self, show_row_numbers: bool):
        if not TKSHEET_AVAILABLE:
            ttk.Label(
                self,
                text="Установите tksheet: pip install tksheet",
                foreground="red",
            ).pack(padx=20, pady=20)
            return

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 4))

        ttk.Button(bar, text="+ Строка", command=self.add_row).pack(side="left", padx=2)
        ttk.Button(bar, text="− Строка", command=self.delete_rows).pack(side="left", padx=2)
        ttk.Button(bar, text="Копировать", command=self.copy_selection).pack(side="left", padx=2)
        ttk.Button(bar, text="Вставить", command=self.paste_clipboard).pack(side="left", padx=2)

        self.hint = ttk.Label(
            bar,
            text="Как в Excel: выделение, Enter — правка, Ctrl+C / Ctrl+V, Delete",
            font=FONT_SMALL,
            foreground=COLORS["text_muted"],
        )
        self.hint.pack(side="left", padx=12)

        self._sheet = Sheet(
            self,
            show_row_index=show_row_numbers,
            show_header=True,
            headers=self.columns,
            font=("Segoe UI", 10, "normal"),
            header_font=("Segoe UI", 10, "bold"),
        )
        self._sheet.pack(fill="both", expand=True)

        self._sheet.enable_bindings(
            (
                "single_select",
                "drag_select",
                "column_select",
                "row_select",
                "column_width_resize",
                "double_click_column_resize",
                "arrowkeys",
                "right_click_popup_menu",
                "rc_select",
                "copy",
                "cut",
                "paste",
                "delete",
                "undo",
                "edit_cell",
            )
        )
        self._sheet.extra_bindings([("end_edit_cell", self._end_edit_cell)])
        self._bind_sheet_clipboard()
        self._bind_excel_hotkeys()

    def _bind_excel_hotkeys(self):
        """F2 — правка ячейки; Ctrl+Home/End — к первой/последней строке."""
        if not self._sheet:
            return

        def edit_cell(_event=None):
            try:
                sel = self._sheet.get_currently_selected()
                if sel:
                    self._sheet.open_cell()
            except Exception:
                pass
            return "break"

        def goto_first(_event=None):
            try:
                if self._sheet.total_rows():
                    self._sheet.see(row=0, column=0)
                    self._sheet.select_cell(0, 0)
            except Exception:
                pass
            return "break"

        def goto_last(_event=None):
            try:
                n = self._sheet.total_rows()
                if n > 0:
                    self._sheet.see(row=n - 1, column=0)
                    self._sheet.select_cell(n - 1, 0)
            except Exception:
                pass
            return "break"

        for w in (self, self._sheet):
            w.bind("<F2>", edit_cell, add="+")
            w.bind("<Control-Home>", goto_first, add="+")
            w.bind("<Control-End>", goto_last, add="+")

    def _bind_sheet_clipboard(self):
        """Явные Ctrl+C/V — на случай если tksheet не перехватил клавиши."""
        if not self._sheet:
            return
        for w in (self, self._sheet):
            for seq in (
                "<Control-c>", "<Control-C>", "<Control-Key-c>",
                "<Control-Insert>",
            ):
                w.bind(seq, lambda e: self.copy_selection() or "break", add="+")
            for seq in (
                "<Control-v>", "<Control-V>", "<Control-Key-v>",
                "<Shift-Insert>",
            ):
                w.bind(
                    seq,
                    lambda e: self.paste_clipboard() or "break",
                    add="+",
                )

    def refresh_dropdowns(self, dropdowns: Dict[str, List[str]]):
        self.dropdowns = dropdowns or {}
        self._apply_dropdowns()

    def _column_dropdown_key(self, col_idx: int) -> str:
        """tksheet: int = номер строки, буква столбца (A, B, …) = столбец."""
        return get_column_letter(col_idx + 1)

    def _apply_dropdowns(self):
        if not self._sheet:
            return
        for col_idx, col_name in enumerate(self.columns):
            values = self.dropdowns.get(col_name)
            if not values:
                continue
            try:
                self._sheet.dropdown(
                    self._column_dropdown_key(col_idx),
                    values=values,
                    validate_input=True,
                    state="normal",
                    edit_data=False,
                )
            except Exception:
                pass

    def _end_edit_cell(self, event):
        if not self._sheet:
            return
        row = event.row if hasattr(event, "row") else event[0]
        col = event.column if hasattr(event, "column") else event[1]
        value = event.value if hasattr(event, "value") else event[2]
        if col < 0 or col >= len(self.columns):
            return
        col_name = self.columns[col]
        if self.on_cell_edited:
            self.on_cell_edited(row, col_name, str(value))
        self._sync_df_from_sheet()
        self._notify()

    def _sync_df_from_sheet(self):
        if not self._sheet:
            return
        data = self._sheet.get_sheet_data()
        rows = []
        for row in data:
            if not any(str(c).strip() for c in row):
                continue
            item = {}
            for i, col in enumerate(self.columns):
                item[col] = row[i] if i < len(row) else ""
            rows.append(item)
        self.df = pd.DataFrame(rows, columns=self.columns) if rows else pd.DataFrame(columns=self.columns)
        if not self.df.empty:
            self.df["№"] = range(1, len(self.df) + 1)

    def load_dataframe(self, df: Optional[pd.DataFrame], apply_dropdowns: Optional[bool] = None):
        if not self._sheet:
            self.df = df.copy() if df is not None else pd.DataFrame(columns=self.columns)
            return
        self._loading = True
        try:
            if df is None or df.empty:
                self.df = pd.DataFrame(columns=self.columns)
                self._sheet.set_sheet_data([[]])
            else:
                self.df = df.copy()
                for c in self.columns:
                    if c not in self.df.columns:
                        self.df[c] = ""
                self.df = self.df[self.columns]
                data = self.df.fillna("").astype(str).values.tolist()
                self._sheet.set_sheet_data(data)
            if apply_dropdowns is None:
                apply_dropdowns = self.df is not None and len(self.df) <= 300
            if apply_dropdowns:
                self._apply_dropdowns()
        finally:
            self._loading = False
        self._notify()

    def get_dataframe(self) -> pd.DataFrame:
        if self._sheet:
            self._sync_df_from_sheet()
        if self.df is None or self.df.empty:
            return pd.DataFrame(columns=self.columns)
        self.df["№"] = range(1, len(self.df) + 1)
        return self.df.copy()

    def add_row(self):
        if not self._sheet:
            return
        empty = [""] * len(self.columns)
        if "Дата заказа" in self.columns:
            from datetime import datetime
            idx = self.columns.index("Дата заказа")
            empty[idx] = datetime.now().strftime("%d.%m.%Y")
        for field, val in (("Операция", "Заказ"), ("АВИА/ЖД", "АВИА"), ("Оплата", "Монтаж")):
            if field in self.columns:
                empty[self.columns.index(field)] = val
        self._sheet.insert_row(empty)
        self._sync_df_from_sheet()
        self._notify()

    def delete_rows(self):
        if not self._sheet:
            return
        rows = sorted(self._sheet.get_selected_rows(), reverse=True)
        if not rows:
            return
        for r in rows:
            self._sheet.delete_row(r)
        self._sync_df_from_sheet()
        self._notify()

    def copy_selection(self):
        if self._sheet:
            self._sheet.ctrl_c()

    def paste_clipboard(self):
        if self._sheet:
            self._sheet.ctrl_v()
            self._sync_df_from_sheet()
            self._notify()

    def append_rows(self, rows: List[dict]):
        if not rows:
            return
        new_df = pd.DataFrame(rows, columns=self.columns)
        current = self.get_dataframe()
        if current.empty:
            combined = new_df
        else:
            combined = pd.concat([current, new_df], ignore_index=True)
        combined["№"] = range(1, len(combined) + 1)
        self.load_dataframe(combined)

    def _notify(self):
        if self._loading or not self.on_change:
            return
        self.on_change()

    @property
    def tree(self):
        """Совместимость со старым кодом (double-click на таблице заявки)."""
        return self
