# application_builder.py
"""Сборка строк заявки из мастера PDF и каталога."""

from typing import Dict, List

import pandas as pd

from config import ALL_COLUMNS
from excel_handler import create_application_row, create_empty_row
from route_logic import expand_wizard_result


def build_rows_from_wizard_result(
    result: Dict,
    department: str,
    start_idx: int,
) -> List[Dict]:
    employee = result.get("employee")
    segments = expand_wizard_result(result)
    if not segments:
        segments = [{
            "route": result.get("route1") or result.get("route", ""),
            "date": result.get("date1") or result.get("date", ""),
            "reason": result.get("reason1") or result.get("reason", ""),
            "note": "",
        }]

    rows: List[Dict] = []
    idx = start_idx
    for seg in segments:
        pdf_data = {
            "source_file": result.get("source_file", ""),
            "fio": result.get("fio", ""),
            "route": seg.get("route", ""),
            "date": seg.get("date", ""),
            "reason": seg.get("reason", ""),
            "phone": result.get("phone", ""),
        }
        if employee:
            row = create_application_row(idx, department, pdf_data, employee)
        else:
            row = create_empty_row(idx, department, pdf_data)
            row["Примечание"] = "НЕ НАЙДЕН В БАЗЕ (ручной ввод)"
        note = seg.get("note", "")
        if note:
            existing = str(row.get("Примечание", "")).strip()
            row["Примечание"] = f"{existing} {note}".strip() if existing else note
        rows.append(row)
        idx += 1
    return rows


def dataframe_from_rows(rows: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=ALL_COLUMNS)
