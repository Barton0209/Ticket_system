# config.py
"""
============================================================================
КОНФИГУРАЦИЯ СИСТЕМЫ
============================================================================
"""

import json
import os
from pathlib import Path

APP_VERSION = "7.2"
APP_TITLE = f"Система заявок на билеты v{APP_VERSION}"

# HTTP API (этап 2 — Electron)
API_HOST = os.environ.get("TICKET_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TICKET_API_PORT", "8765"))

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

USERS = {
    "ОП А-НПС-4А": "qwer11",
    "ОП Астрахань": "qwer12",
    "ОП Большой Камень": "qwer13",
    "ОП Винный город": "qwer14",
    "ОП Гыдан": "qwer15",
    "ОП Дивноморское": "qwer16",
    "ОП Диксон": "qwer17",
    "ОП Карелия": "qwer18",
    "ОП Кингисепп": "qwer19",
    "ОП Криница": "qwer20",
    "ОП КС-7 Сивакинская": "qwer21",
    "ОП Кутузовский": "qwer22",
    "ОП Москва-Сити": "qwer23",
    "ОП Мурманск": "qwer24",
    "ОП Новый Уренгой": "qwer25",
    "ОП Норильск": "qwer26",
    "ОП ОП АМУР": "qwer27",
    "ОП ОП Кингисепп 2. ЕвроХим": "qwer28",
    "ОП РП Новороссийск": "qwer29",
    "ОП Сахалин": "qwer30",
    "ОП СВОБОДНЫЙ": "qwer31",
    "ОП Сочи": "qwer32",
    "ОП Сочи 2": "qwer33",
    "ОП Тарко-Сале": "qwer34",
    "ОП Усть-Луга": "qwer35",
}

ADMIN_CREDENTIALS = {
    "username": "Admin",
    "password": "Deto4ka111D"
}

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
