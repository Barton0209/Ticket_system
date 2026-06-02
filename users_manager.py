# users_manager.py
"""Пользователи из Excel (лист Users+pass) и кэш.

Обновлённая логика безопасности:
- Все пароли в оперативной памяти и кэше хранятся в bcrypt-хеше.
- Открытые пароли из config.USERS мигрируются при инициализации в _USERS (хешируются).
- Аутентификация проверяет только хешированные пароли через verify_password.
- Admin пароль обязан задаваться через переменную окружения (config.ADMIN_CREDENTIALS).
"""

import pickle
import shutil
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import DATA_DIR, USERS, ADMIN_CREDENTIALS, USERS_CACHE_FILE, USERS_PASS_FILE
from app_logger import log
from password_utils import hash_password, verify_password, is_hashed

USERS_SHEET = "Users+pass"
PROFILE_COL_INDICES = (3, 4, 5, 6)


@dataclass
class AppUser:
    login: str
    password: str
    department: str
    fio: str = ""
    email: str = ""
    position: str = ""
    dept_category: str = ""

    @property
    def allowed_departments(self) -> List[str]:
        if not self.department:
            return []
        parts = [p.strip() for p in str(self.department).replace(";", ",").split(",")]
        return [p for p in parts if p]


_USERS: Dict[str, AppUser] = {}


def _safe(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _cell_by_index(row, col_names: List[str], index: int) -> str:
    if index < len(col_names):
        return _safe(row.get(col_names[index]))
    return ""


def load_users_from_excel(file_path: str, copy_to_data_dir: bool = True) -> Tuple[bool, str, int]:
    global _USERS
    try:
        xl = pd.ExcelFile(file_path)
        sheet = USERS_SHEET if USERS_SHEET in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(file_path, sheet_name=sheet)
        col_names = [str(c).strip() for c in df.columns]

        col_login = _find_col(df, ["логин", "login"]) or (col_names[0] if col_names else None)
        col_pass = _find_col(df, ["пароль", "password"]) or (col_names[1] if len(col_names) > 1 else None)
        col_dept = _find_col(df, ["значение_подразделение", "подразделение", "department"]) or (col_names[2] if len(col_names) > 2 else None)

        if not col_login or not col_pass:
            return False, "Нужны колонки A–B: Логин и Пароль", 0

        users: Dict[str, AppUser] = {}
        for _, row in df.iterrows():
            login = _safe(row.get(col_login))
            password = _safe(row.get(col_pass))
            if not login or not password:
                continue
            fio = _cell_by_index(row, col_names, PROFILE_COL_INDICES[0])
            email = _cell_by_index(row, col_names, PROFILE_COL_INDICES[1])
            position = _cell_by_index(row, col_names, PROFILE_COL_INDICES[2])
            dept_category = _cell_by_index(row, col_names, PROFILE_COL_INDICES[3])

            # Храним в хеше
            pwd_stored = password if is_hashed(password) else hash_password(password)
            users[login] = AppUser(
                login=login,
                password=pwd_stored,
                department=_safe(row.get(col_dept)) if col_dept else "",
                fio=fio,
                email=email,
                position=position,
                dept_category=dept_category,
            )

        _USERS = users
        _save_cache()
        if copy_to_data_dir:
            try:
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, USERS_PASS_FILE)
            except OSError as e:
                log.warning("Не удалось сохранить копию Users+pass: %s", e)
        log.info("Загружено пользователей: %s", len(users))
        return True, f"Загружено пользователей: {len(users)} (лист {sheet})", len(users)
    except Exception as e:
        log.error("Ошибка загрузки пользователей: %s", e)
        return False, str(e), 0


def _find_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    for col in df.columns:
        c = str(col).lower().replace(" ", "").replace("_", "")
        for name in names:
            n = name.lower().replace(" ", "").replace("_", "")
            if n in c or c in n:
                return col
    return None


def _save_cache() -> bool:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(USERS_CACHE_FILE, "wb") as f:
            pickle.dump(_USERS, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True
    except OSError:
        return False


def load_users_cache() -> Tuple[bool, str, int]:
    global _USERS
    # Если есть Excel с паролями — загрузить и мигрировать
    if not USERS_CACHE_FILE.exists() and USERS_PASS_FILE.exists():
        ok, msg, n = load_users_from_excel(str(USERS_PASS_FILE), copy_to_data_dir=False)
        if ok:
            return ok, msg, n
    if not USERS_CACHE_FILE.exists():
        _build_users_from_config()
        return True, f"Пользователи из config: {len(_USERS)}", len(_USERS)
    try:
        # Проверка целостности pickle файла пользователей
        file_size = USERS_CACHE_FILE.stat().st_size
        if file_size == 0:
            _build_users_from_config()
            return True, "Кэш пользователей пуст, загружено из config", len(_USERS)
        if file_size > 10 * 1024 * 1024:  # 10 MB лимит для пользователей
            _build_users_from_config()
            return False, "Кэш пользователей слишком большой, загружено из config", len(_USERS)
        
        with open(USERS_CACHE_FILE, "rb") as f:
            _USERS = pickle.load(f)
        if not _USERS:
            _build_users_from_config()
        return True, f"Пользователей: {len(_USERS)}", len(_USERS)
    except Exception as e:
        _build_users_from_config()
        return False, str(e), len(_USERS)


def format_user_header(app_user: Optional["AppUser"], department: str, is_admin: bool) -> Tuple[str, str]:
    if is_admin:
        return "Admin", "Полный доступ · общая база сотрудников"
    if not app_user:
        return department or "—", ""

    dept_line = department or app_user.login
    parts = []
    if app_user.fio:
        parts.append(app_user.fio)
    if app_user.position:
        parts.append(app_user.position)
    if app_user.email:
        parts.append(app_user.email)
    if app_user.dept_category:
        parts.append(app_user.dept_category)
    profile = " · ".join(parts) if parts else app_user.department
    return dept_line, profile


def _build_users_from_config() -> None:
    """Создать _USERS на основе config.USERS, хешируя незахешированные пароли."""
    global _USERS
    _USERS = {}
    for dept, pwd in USERS.items():
        if not pwd:
            continue
        stored = pwd if is_hashed(pwd) else hash_password(pwd)
        _USERS[dept] = AppUser(
            login=dept,
            password=stored,
            department=dept,
        )

    # Также обработать ADMIN_CREDENTIALS: если пароль задан и не захеширован — хешировать в памяти
    admin_pwd = ADMIN_CREDENTIALS.get("password", "")
    if admin_pwd:
        if not is_hashed(admin_pwd):
            log.warning("ADMIN_CREDENTIALS password supplied in ENV is not hashed — hashing in memory. Rotate secrets for production.")
            ADMIN_CREDENTIALS["password"] = hash_password(admin_pwd)


def get_all_logins() -> List[str]:
    if not _USERS:
        load_users_cache()
    return sorted(_USERS.keys())


def get_user(login: str) -> Optional[AppUser]:
    if not _USERS:
        load_users_cache()
    return _USERS.get(login)


def authenticate(login: str, password: str) -> Tuple[Optional[AppUser], bool, str]:
    """Возвращает (user, is_admin, department_label).

    Администратор аутентифицируется только если ADMIN_CREDENTIALS.password задан и совпадает после bcrypt.
    Обычные пользователи проверяются только по _USERS (кэш). Открытые пароли в config.USERS
    заранее мигрируются при старте в _USERS (хешируются).
    """
    # Admin
    if login == "Admin":
        admin_pwd = ADMIN_CREDENTIALS.get("password", "")
        if not admin_pwd:
            return None, False, ""
        if verify_password(password, admin_pwd):
            return None, True, "Admin"
        return None, False, ""

    # Пользователь из кэша
    user = get_user(login)
    if user and verify_password(password, user.password):
        dept_label = user.allowed_departments[0] if len(user.allowed_departments) == 1 else user.department
        return user, False, dept_label or login

    # Никаких fallback-равенств по plain-text — отказ
    return None, False, ""


def export_users_to_excel(file_path: str) -> Tuple[bool, str]:
    if not _USERS:
        return False, "Нет пользователей"
    rows = []
    for u in _USERS.values():
        rows.append({
            "Логин": u.login,
            "Пароль": u.password,
            "Значение_Подразделение": u.department,
            "ФИО": u.fio,
            "Email": u.email,
            "Должность": u.position,
            "Отдел": u.dept_category,
        })
    pd.DataFrame(rows).to_excel(file_path, sheet_name=USERS_SHEET, index=False)
    return True, f"Сохранено: {file_path}"
