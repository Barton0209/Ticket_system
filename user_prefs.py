# user_prefs.py
"""Настройки пользователя (тема, подсказки, автосохранение)."""

from __future__ import annotations

import json
from typing import Any, Dict

from config import DATA_DIR

PREFS_FILE = DATA_DIR / "user_prefs.json"

_DEFAULTS = {
    "theme": "light",
    "first_run_done": False,
    "draft_autosave_minutes": 5,
}


def load_prefs() -> Dict[str, Any]:
    if not PREFS_FILE.exists():
        return dict(_DEFAULTS)
    try:
        with open(PREFS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        out = dict(_DEFAULTS)
        if isinstance(data, dict):
            out.update(data)
        return out
    except (OSError, json.JSONDecodeError, TypeError):
        return dict(_DEFAULTS)


def save_prefs(prefs: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(_DEFAULTS)
    merged.update(prefs)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def is_dark_theme() -> bool:
    return str(load_prefs().get("theme", "light")).lower() == "dark"


def set_theme(theme: str) -> None:
    prefs = load_prefs()
    prefs["theme"] = "dark" if str(theme).lower() == "dark" else "light"
    save_prefs(prefs)


def mark_first_run_done() -> None:
    prefs = load_prefs()
    prefs["first_run_done"] = True
    save_prefs(prefs)


def is_first_run() -> bool:
    return not bool(load_prefs().get("first_run_done"))


def draft_autosave_minutes() -> int:
    try:
        return max(1, int(load_prefs().get("draft_autosave_minutes", 5)))
    except (TypeError, ValueError):
        return 5
