# users_manager.py
"""Пользователи из Excel (лист Users+pass) и кэш."""

import pickle
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import DATA_DIR, USERS, ADMIN_CREDENTIALS, USERS_CACHE_FILE, USERS_PASS_FILE
from app_logger import log
from password_utils import hash_password, verify_password, is_hashed

USERS_SHEET = "Users+pass"
# Столбцы D:G в Users+pass.xlsx (индексы 3–6): ФИО, Email, Должность, Отдел
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
        col_dept = _find_col(df, ["значение_подразделение", "подразделение", "department"])
        if not col_dept and len(col_names) > 2:
            col_dept = col_names[2]

        if not col_login or not col_pass:
            return False, "Нужны колонки A–B: Логин и Пароль", 0

        users: Dict[str, AppUser] = {}
        for _, row in df.iterrows():
            login = _safe(row.get(col_login))
            password = _safe(row.get(col_pass))
            if not login or not password:
                continue
            fio = _cell_by_index(row, col_names, 3)
            email = _cell_by_index(row, col_names, 4)
            position = _cell_by_index(row, col_names, 5)
            dept_category = _cell_by_index(row, col_names, 6)
            if not fio:
                col_fio = _find_col(df, ["фио", "fio"])
                fio = _safe(row.get(col_fio)) if col_fio else ""
            if not email:
                col_email = _find_col(df, ["email", "e-mail"])
                email = _safe(row.get(col_email)) if col_email else ""
            if not position:
                col_pos = _find_col(df, ["должность", "position"])
                position = _safe(row.get(col_pos)) if col_pos else ""
            if not dept_category:
                col_cat = _find_col(df, ["отдел", "department_category"])
                dept_category = _safe(row.get(col_cat)) if col_cat else ""

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
        c = col.lower().replace(" ", "").replace("_", "")
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
    if not USERS_CACHE_FILE.exists() and USERS_PASS_FILE.exists():
        ok, msg, n = load_users_from_excel(str(USERS_PASS_FILE), copy_to_data_dir=False)
        if ok:
            return ok, msg, n
    if not USERS_CACHE_FILE.exists():
        _build_users_from_config()
        return True, f"Пользователи из config: {len(_USERS)}", len(_USERS)
    try:
        with open(USERS_CACHE_FILE, "rb") as f:
            _USERS = pickle.load(f)
        if not _USERS:
            _build_users_from_config()
        return True, f"Пользователей: {len(_USERS)}", len(_USERS)
    except Exception as e:
        _build_users_from_config()
        return False, str(e), len(_USERS)


def format_user_header(app_user: Optional["AppUser"], department: str, is_admin: bool) -> Tuple[str, str]:
    """
    Заголовок справа вверху: (строка ОП/логин, блок D:G — ФИО, email, должность, отдел).
    """
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
    global _USERS
    _USERS = {}
    for dept, pwd in USERS.items():
        _USERS[dept] = AppUser(
            login=dept,
            password=hash_password(pwd) if pwd and not is_hashed(pwd) else pwd,
            department=dept,
        )


def get_all_logins() -> List[str]:
    if not _USERS:
        load_users_cache()
    return sorted(_USERS.keys())


def get_user(login: str) -> Optional[AppUser]:
    if not _USERS:
        load_users_cache()
    return _USERS.get(login)


def authenticate(login: str, password: str) -> Tuple[Optional[AppUser], bool, str]:
    """Возвращает (user, is_admin, department_label)."""
    admin_pwd = ADMIN_CREDENTIALS.get("password", "")
    if login == "Admin":
        if verify_password(password, admin_pwd) or (
            not is_hashed(admin_pwd) and password == admin_pwd
        ):
            return None, True, "Admin"
        return None, False, ""
    user = get_user(login)
    if user and verify_password(password, user.password):
        dept_label = user.allowed_departments[0] if len(user.allowed_departments) == 1 else user.department
        return user, False, dept_label or login
    if login in USERS and verify_password(password, USERS[login]):
        return AppUser(
            login=login,
            password=hash_password(password) if not is_hashed(USERS[login]) else USERS[login],
            department=login,
        ), False, login
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
