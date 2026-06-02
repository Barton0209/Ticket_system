# config.py
"""
============================================================================
КОНФИГУРАЦИЯ СИСТЕМЫ (безопасная версия с поддержкой переменных окружения)
============================================================================
"""

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv не установлен, используем только os.environ

APP_VERSION = "7.2"
APP_TITLE = f"Система заявок на билеты v{APP_VERSION}"

# === HTTP API (этап 2 — Electron) ===
API_HOST = os.environ.get("TICKET_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TICKET_API_PORT", "8765"))

# === БЕЗОПАСНОСТЬ: API KEY ===
# ОБЯЗАТЕЛЕН для боевого сервера!
_API_KEY = os.environ.get("TICKET_API_KEY", "").strip()
if not _API_KEY:
    import warnings
    warnings.warn(
        "\n⚠️  КРИТИЧНО: TICKET_API_KEY не установлен!\n"
        "API будет доступен без аутентификации.\n"
        "Установите: export TICKET_API_KEY='your-secret-key'\n"
    )
API_KEY = _API_KEY

# Вкладка «База»: не грузить все строки в таблицу (большие базы зависают)
BASE_GRID_PAGE_SIZE = 500

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EMPLOYEES_CACHE_FILE = DATA_DIR / "employees_cache.pkl"
EMPLOYEES_DB_FILE = DATA_DIR / "employees.db"
EMPLOYEES_META_FILE = DATA_DIR / "employees_meta.json"
USERS_CACHE_FILE = DATA_DIR / "users_cache.pkl"
USERS_PASS_FILE = DATA_DIR / "Users+pass.xlsx"
USERS_LOCAL_FILE = BASE_DIR / "users.local.json"

TESSERACT_CMD = os.environ.get(
    "TESSERACT_CMD",
    r"C:\Tesseract-OCR\tesseract.exe",
)

# === УЧЁТНЫЕ ДАННЫЕ (безопасное управление) ===
USERS = {
    # Пароли больше не должны быть здесь!
    # Вместо этого используйте users.local.json (в .gitignore) или переменные окружения
}

# === АДМИН УЧЁТНЫЕ ДАННЫЕ (безопасно) ===
# НИКОГДА не коммитьте реальные пароли в исходный код!
_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
ADMIN_CREDENTIALS = {
    "username": "Admin",
    "password": _ADMIN_PASSWORD or "changeme",  # По умолчанию заплатка
}

if not _ADMIN_PASSWORD:
    import warnings
    warnings.warn(
        "\n⚠️  WARNING: ADMIN_PASSWORD не установлен в переменных окружения.\n"
        "Используется пароль по умолчанию (НЕБЕЗОПАСНО!).\n"
        "Установите: export ADMIN_PASSWORD='your-secure-password'\n"
    )

DEFAULT_CONSTANTS = {
    "Операция": "Заказ",
    "АВИА/ЖД": "АВИА",
    "Оплата": "Монтаж",
    "Вид документа РФ": "Паспорт гражданина России",
    "Вид документа иностранный": "Паспорт иностранного гражданина",
    "Вид на жительство": "Вид на жительство",
}

COUNTRY_SCHEMA_MAP = {
    "РОССИЯ": "gost_52535",
    "БЕЛАРУСЬ": "gost_52535",
    "КАЗАХСТАН": "gost_52535",
    "КИРГИЗИЯ": "gost_52535",
    "УЗБЕКИСТАН": "gost_779",
    "ТУРКМЕНИЯ": "gost_779",
    "ТАДЖИКИСТАН": "gost_779",
    "СЕРБИЯ": "gost_779",
}

PASSPORT_VALIDITY = {
    "РОССИЯ": {"months": None, "note": "", "action": "empty"},
    "РФ": {"months": None, "note": "", "action": "empty"},
    "БЕЛАРУСЬ": {"months": None, "note": "проверить паспорт", "action": "check"},
    "КИРГИЗИЯ": {"months": 120, "note": "120 мес.", "no_minus": True},
    "СЕРБИЯ": {"months": 120, "note": "120 мес.", "no_minus": True},
    "КАЗАХСТАН": {"months": 120, "note": "120 мес."},
    "УЗБЕКИСТАН": {"months": 120, "note": "120 мес."},
    "ТАДЖИКИСТАН": {"months": 120, "note": "120 мес."},
    "ИНДИЯ": {"months": 120, "note": "120 мес."},
    "ТУРКМЕНИСТАН": {"months": 120, "note": "120 мес."},
    "КИТАЙ": {"months": 120, "note": "120 мес."},
}

ALL_COLUMNS = [
    "№", "Подразделение", "Отдел", "Операция", "Классификация", "Дата заказа",
    "Организация", "Ф.И.О.", "Ф.И.О лат", "Табельный номер", "Гражданство",
    "Дата рождения", "Вид документа", "Серия", "Номер", "Дата выдачи",
    "Дата окончания", "Кем выдан", "Адрес", "Маршрут", "Обоснование",
    "ПС", "АВИА/ЖД", "Дата вылета", "Примечание", "Ответственный",
    "Дата выписки", "Билет", "Сумма", "Оплата", "Причина возврата",
    "Последний перелет", "Телефон", "Трансфер"
]

ITR_KEYWORDS = ["инженер", "мастер", "начальник", "менеджер", "руководитель",
                "специалист", "техник", "геодезист", "сметчик"]

REASONS = [
    "Увольнение",
    "Межвахтовый отдых",
    "Возвращение из отпуска",
    "Устройство на работу",
    "Перевод в др. ОП",
    "Командировка",
    "Разъездной характер работы",
    "Ежегодный отпуск",
    "Больничный",
    "Межвахта",
]


def _load_local_users():
    """Опциональные учётные данные из users.local.json (не коммитить в git)."""
    if not USERS_LOCAL_FILE.exists():
        return None, None
    try:
        with open(USERS_LOCAL_FILE, encoding="utf-8") as f:
            data = json.load(f)
        users = data.get("users")
        admin = data.get("admin")
        return users, admin
    except (OSError, json.JSONDecodeError, TypeError):
        return None, None


_local_users, _local_admin = _load_local_users()
if _local_users:
    USERS.update(_local_users)
if _local_admin:
    ADMIN_CREDENTIALS.update(_local_admin)
