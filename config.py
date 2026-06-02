# config.py
"""
============================================================================
КОНФИГУРАЦИЯ СИСТЕМЫ
============================================================================
"""

import json
import os
import shutil
import sys
from pathlib import Path

APP_VERSION = "7.2"
APP_TITLE = f"Система заявок на билеты v{APP_VERSION}"

# HTTP API (этап 2 — Electron)
API_HOST = os.environ.get("TICKET_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TICKET_API_PORT", "8765"))

# Параметры окружения
ENV = os.environ.get("TICKET_ENV", "development").lower()

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

# Tesseract — кроссплатформенный поиск команды
def _find_tesseract_cmd() -> str:
    import shutil

    # 1) переменная окружения
    env = os.environ.get("TESSERACT_CMD")
    if env:
        return env

    # 2) PATH
    if shutil.which("tesseract"):
        return shutil.which("tesseract")

    # 3) типичные пути
    if sys.platform == "win32":
        typical = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    elif sys.platform == "darwin":
        typical = "/usr/local/bin/tesseract"
    else:
        typical = "/usr/bin/tesseract"

    if os.path.isfile(typical):
        return typical

    return ""

TESSERACT_CMD = _find_tesseract_cmd()

# USERS: по умолчанию пустой словарь — пароли НЕ хранятся в репо.
# Для локальной разработки можно установить переменную окружения TICKET_DEFAULT_USERS
# формат JSON: '{"login1":"pass1","login2":"pass2"}'
USERS = {}
_default_users_json = os.environ.get("TICKET_DEFAULT_USERS", "")
if _default_users_json:
    try:
        USERS.update(json.loads(_default_users_json))
    except Exception:
        # Игнорируем ошибки парсинга; лучше заполнить users.local.json
        pass

# Администратор: пароль должен быть задан через переменную окружения TICKET_ADMIN_PASSWORD
# НЕ храните пароль администратора в репозитории. Для production — используйте секреты.
ADMIN_CREDENTIALS = {
    "username": "Admin",
    "password": os.environ.get("TICKET_ADMIN_PASSWORD", "")
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
    # local users override defaults
    USERS.update(_local_users)
if _local_admin:
    ADMIN_CREDENTIALS.update(_local_admin)

# Если в USERS есть незахешированные пароли — их лучше мигрировать при старте
# migration происходит в users_manager._build_users_from_config
