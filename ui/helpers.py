"""Вспомогательные функции UI."""


def _normalize_tab_num(value) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ("nan", "none"):
        return ""
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s
