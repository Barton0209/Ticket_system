# draft_storage.py
"""Сохранение черновика заявки между сессиями."""

import pickle
from typing import Optional, Tuple

import pandas as pd

from config import DATA_DIR

DRAFT_FILE = DATA_DIR / "draft_application.pkl"


def save_draft(df: pd.DataFrame, department: str, tab_nums: set) -> Tuple[bool, str]:
    if df is None or df.empty:
        return False, "Нет данных для сохранения"
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "department": department,
            "dataframe": df,
            "tab_nums": list(tab_nums),
        }
        with open(DRAFT_FILE, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True, "Черновик сохранён"
    except OSError as e:
        return False, f"Ошибка сохранения: {e}"


def load_draft(expected_department: str = None) -> Tuple[bool, str, Optional[pd.DataFrame], set]:
    if not DRAFT_FILE.exists():
        return False, "Черновик не найден", None, set()
    try:
        with open(DRAFT_FILE, "rb") as f:
            payload = pickle.load(f)
        dept = payload.get("department", "")
        if expected_department and dept and dept != expected_department:
            return False, f"Черновик от другого подразделения ({dept})", None, set()
        df = payload.get("dataframe")
        tab_nums = set(payload.get("tab_nums") or [])
        if df is None or df.empty:
            return False, "Черновик пуст", None, set()
        return True, f"Загружено строк: {len(df)}", df, tab_nums
    except (OSError, pickle.PickleError, Exception) as e:
        return False, f"Ошибка чтения черновика: {e}", None, set()


def clear_draft() -> None:
    if DRAFT_FILE.exists():
        try:
            DRAFT_FILE.unlink()
        except OSError:
            pass
