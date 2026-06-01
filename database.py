# database.py
"""
============================================================================
РАБОТА С БАЗОЙ ДАННЫХ
============================================================================
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
import hashlib
import re
import json
import os
import pickle
from datetime import datetime, timedelta

from config import EMPLOYEES_CACHE_FILE, EMPLOYEES_META_FILE, DATA_DIR, ALL_COLUMNS

import employees_store

EMPLOYEES_DB: Optional[pd.DataFrame] = None
_USE_SQLITE: bool = False


def safe_str(value, default="") -> str:
    if value is None or pd.isna(value):
        return default
    result = str(value).strip()
    if result in ("nan", "None", ""):
        return default
    return result


def format_passport_field(value) -> str:
    """Серия/номер из Excel: числа без хвоста .0, пробелы в серии (60 19) сохраняем."""
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return safe_str(value)
    text = safe_str(value)
    if text.endswith(".0") and text[:-2].replace(" ", "").isdigit():
        return text[:-2]
    return text


def _infer_doc_series_column(df: pd.DataFrame, mapping: Dict[str, str]) -> Optional[str]:
    """
    Найти колонку «Серия», если заголовок нестандартный или сдвинут (например, после AI).
    Обычно серия стоит сразу перед «Номер» или после «Вид документа».
    """
    cols = list(df.columns)
    mapped = set(mapping.keys())

    doc_num_col = next((c for c, dst in mapping.items() if dst == "doc_num"), None)
    if doc_num_col and doc_num_col in cols:
        idx = cols.index(doc_num_col)
        if idx > 0:
            prev = cols[idx - 1]
            if prev not in mapped:
                pl = str(prev).lower()
                blocked_prev = ("табель", "дата", "рожден", "фио", "граждан", "организа", "подраздел", "отдел")
                if not any(b in pl for b in blocked_prev):
                    if "вид" in pl and "документ" in pl:
                        pass
                    else:
                        return prev

    vid_col = find_column(
        df,
        ["Вид документа", "Вид док.", "Вид документа РФ"],
        exclude=list(mapped),
    )
    if vid_col and vid_col in cols:
        idx = cols.index(vid_col)
        if idx + 1 < len(cols):
            nxt = cols[idx + 1]
            if nxt not in mapped and nxt != doc_num_col:
                return nxt

    if len(cols) > 13:
        c13 = cols[13]
        if c13 not in mapped:
            h = str(c13).lower()
            blocked = ("табель", "маршрут", "обоснован", "фио", "граждан", "рожден", "организа")
            if not any(b in h for b in blocked):
                if h.strip() in ("серия", "series", "сер.", "сер") or "сери" in h:
                    return c13
                if len(cols) > ALL_COLUMNS.index("Серия"):
                    expected = ALL_COLUMNS[ALL_COLUMNS.index("Серия")].lower()
                    if _normalize_header(c13) == _normalize_header(expected):
                        return c13
                if doc_num_col and cols.index(doc_num_col) == 14:
                    return c13

    for col in cols:
        if col in mapped:
            continue
        cl = str(col).strip().lower()
        if cl in ("серия", "series", "сер.", "сер", "серия паспорта", "серия документа"):
            return col
        if "сери" in cl and "номер" not in cl and "дата" not in cl and "табель" not in cl:
            return col

    return None


def _fill_missing_doc_series_from_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Если серия пустая, а в номере записано «60 19 832138» — разделить."""
    if "doc_series" not in df.columns or "doc_num" not in df.columns:
        return df
    pattern = re.compile(r"^([\d\s]{2,10}?)\s+(\d{5,})$")
    for i in df.index:
        if safe_str(df.at[i, "doc_series"]):
            continue
        raw = safe_str(df.at[i, "doc_num"]).replace("-", " ").strip()
        m = pattern.match(raw)
        if m:
            series = re.sub(r"\s+", " ", m.group(1)).strip()
            df.at[i, "doc_series"] = series
            df.at[i, "doc_num"] = m.group(2).strip()
    return df


def normalize_fio(fio: str) -> str:
    if not fio:
        return ""
    return ' '.join(re.sub(r'[.,;]', '', str(fio)).split())


def hash_fio(fio: str) -> str:
    return hashlib.md5(normalize_fio(fio).lower().encode()).hexdigest()


def normalize_employment_status(value) -> str:
    """Статус из столбца AI: «Работает» или «Уволен»."""
    text = safe_str(value)
    if not text:
        return ""
    low = text.lower()
    if "увол" in low:
        return "Уволен"
    if "работ" in low:
        return "Работает"
    return text


def get_employee_status(emp: Dict) -> str:
    if not emp:
        return ""
    raw = emp.get("employment_status") or emp.get("AI") or emp.get("ai") or ""
    return normalize_employment_status(raw)


def _normalize_header(name: str) -> str:
    return str(name or "").strip().lower().replace(".", "").replace(" ", "").replace("_", "")


def find_column(
    df: pd.DataFrame,
    possible_names: List[str],
    exclude: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Поиск колонки по заголовку.
    Короткие имена («Номер», «Серия») — только точное совпадение,
    чтобы не путать с «Табельный номер».
    """
    exclude_set = set(exclude or [])
    ordered = sorted(possible_names, key=lambda n: -len(str(n)))

    for col in df.columns:
        if col in exclude_set:
            continue
        col_clean = _normalize_header(col)
        if not col_clean:
            continue
        for name in ordered:
            name_clean = _normalize_header(name)
            if not name_clean:
                continue
            if col_clean == name_clean:
                return col

    for col in df.columns:
        if col in exclude_set:
            continue
        col_clean = _normalize_header(col)
        col_lower = str(col).strip().lower()
        for name in ordered:
            name_clean = _normalize_header(name)
            if len(name_clean) <= 6:
                continue
            if name_clean in col_clean:
                if name_clean == "номер" and "табель" in col_lower:
                    continue
                if name_clean == "серия" and "табель" in col_lower:
                    continue
                return col
    return None


def _build_employee_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Сопоставление колонок листа «ВСЕ ОП» с полями базы.
    Сначала по имени (find_column), затем по индексу как в шаблоне заявки.
    """
    col_map = {
        "fio": ["ФИО", "Ф.И.О.", "FIO", "фио", "ФИО сотрудника"],
        "tab_num": ["Табельный номер", "Таб№", "Таб.№", "Табельный", "tab_num"],
        "position": ["Должность", "Position", "должность", "Должность сотрудника"],
        "department": ["Подразделение", "Department", "подразделение"],
        "department_category": [
            "Отдел",
            "Отдел (СМУ, УМиТ, ОТиЗ)",
            "Отдел (СМУ, УМиТ, ОТ и З)",
            "department_category",
            "Категория",
        ],
        "citizenship": ["Страна гражданства", "Гражданство", "Citizenship", "гражданство"],
        "birth_date": ["Дата рождения", "BirthDate", "дата рождения", "Д.рождения"],
        "doc_series": [
            "Серия",
            "Series",
            "серия",
            "Серия паспорта",
            "Серия документа",
            "Серия удостоверения",
            "Удостоверение.Серия",
            "Паспорт.Серия",
            "Паспорт серия",
        ],
        "doc_num": [
            "Номер паспорта",
            "Номер документа",
            "Удостоверение.Номер",
            "Паспорт.Номер",
            "Номер",
            "Number",
        ],
        "doc_date": ["Дата выдачи", "DocDate", "дата выдачи", "Удостоверение.Дата выдачи"],
        "doc_expiry": [
            "Дата окончания",
            "Срок действия",
            "Дата окончания срока",
            "doc_expiry",
        ],
        "doc_issuer": ["Кем выдан", "Issuer", "кем выдан", "Удостоверение.Кем выдан"],
        "address": [
            "Место постоянного проживания",
            "Адрес",
            "Address",
            "прописка",
            "Физическое лицо.Адрес по прописке",
            "Адрес регистрации",
        ],
        "phone": [
            "Телефон",
            "Phone",
            "Мобильный",
            "телефон",
            "Физическое лицо.Личный мобильный телефон",
        ],
    }

    mapping: Dict[str, str] = {}
    used_targets: set = set()

    for field, candidates in col_map.items():
        col = find_column(df, candidates, exclude=list(mapping.keys()))
        if col and col not in mapping and field not in used_targets:
            mapping[col] = field
            used_targets.add(field)

    # Столбец AI — статус (точное имя)
    for col in df.columns:
        if str(col).strip().upper() == "AI" and col not in mapping:
            mapping[col] = "employment_status"
            used_targets.add("employment_status")
            break
    if "employment_status" not in used_targets:
        status_col = find_column(df, ["Статус", "Status", "статус", "Статус сотрудника"])
        if status_col and status_col not in mapping:
            mapping[status_col] = "employment_status"

    # Дополнительно: заголовок содержит «серия», но не «номер»/«дата»
    if "doc_series" not in used_targets:
        for col in df.columns:
            if col in mapping:
                continue
            cl = str(col).lower()
            if "сери" in cl and "номер" not in cl and "дата" not in cl:
                mapping[col] = "doc_series"
                used_targets.add("doc_series")
                break

    # Позиционный fallback — только если заголовок похож на ожидаемое поле
    cols = list(df.columns)
    index_fallback = {
        7: ("fio", ("фио", "fio")),
        9: ("tab_num", ("табель", "таб№", "таб")),
        10: ("citizenship", ("граждан", "citizen")),
        11: ("birth_date", ("рожден", "birth")),
        13: ("doc_series", ("сери",)),
        14: ("doc_num", ("номер", "number", "паспорт")),
        15: ("doc_date", ("выдач",)),
        16: ("doc_expiry", ("окончан", "срок")),
        17: ("doc_issuer", ("выдан", "issuer")),
        18: ("address", ("адрес", "прожив", "address")),
        32: ("phone", ("телефон", "phone", "мобил")),
    }
    for idx, (field, hints) in index_fallback.items():
        if field in used_targets or idx >= len(cols):
            continue
        col_name = cols[idx]
        if col_name in mapping:
            continue
        cl = str(col_name).lower()
        if field == "doc_num" and "табель" in cl:
            continue
        if field == "tab_num" and cl.strip() in ("номер", "number") and "табель" not in cl:
            continue
        if field == "doc_series" and "doc_num" in used_targets:
            num_col = next((c for c, f in mapping.items() if f == "doc_num"), None)
            if num_col and num_col in cols and cols.index(num_col) == idx + 1:
                mapping[col_name] = field
                used_targets.add(field)
                continue
        if any(h in cl for h in hints):
            mapping[col_name] = field
            used_targets.add(field)

    if "doc_series" not in used_targets:
        series_col = _infer_doc_series_column(df, mapping)
        if series_col and series_col not in mapping:
            mapping[series_col] = "doc_series"

    return mapping


def load_employees_base(file_path: str, loaded_by: str = "Admin") -> Tuple[bool, str, int]:
    global EMPLOYEES_DB

    try:
        if not os.path.exists(file_path):
            return False, f"Файл не найден: {file_path}", 0

        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names

        df = None
        used_sheet = None

        for sheet in ["ВСЕ ОП", "Sheet1", "Employees", "Сотрудники"]:
            if sheet in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                used_sheet = sheet
                break

        if df is None:
            df = pd.read_excel(file_path, sheet_name=0)
            used_sheet = sheet_names[0]

        df.columns = df.columns.str.strip()

        column_mapping = _build_employee_column_mapping(df)
        if "fio" not in column_mapping.values():
            available = ", ".join(df.columns.astype(str).tolist()[:12])
            return False, f"Колонка ФИО не найдена. Доступные: {available}", 0

        df = df.rename(columns=column_mapping)
        if "doc_series" not in df.columns:
            df["doc_series"] = ""

        # === ИСПРАВЛЕНО: добавлен department_category в список ===
        needed_cols = [
            'fio', 'tab_num', 'position', 'employment_status', 'department', 'citizenship',
            'birth_date', 'doc_series', 'doc_num', 'doc_date',
            'doc_issuer', 'address', 'phone', 'doc_expiry', 'department_category',
        ]
        available_cols = [c for c in needed_cols if c in df.columns]
        df = df[available_cols]

        df['fio'] = df['fio'].apply(safe_str)
        df = df[df['fio'].notna() & (df['fio'] != '') & (df['fio'] != 'nan') & (df['fio'] != 'None')]
        df['fio_hash'] = df['fio'].apply(hash_fio)

        for col in df.columns:
            if col not in ["fio", "fio_hash"]:
                if col in ("doc_series", "doc_num"):
                    df[col] = df[col].apply(format_passport_field)
                elif col == "employment_status":
                    df[col] = df[col].apply(normalize_employment_status)
                else:
                    df[col] = df[col].apply(lambda x: safe_str(x, ""))

        df = _fill_missing_doc_series_from_cells(df)

        df = df.reset_index(drop=True)
        EMPLOYEES_DB = df
        n_loaded = len(df)
        save_employees_cache(
            source=os.path.basename(file_path),
            loaded_by=loaded_by,
        )

        series_src = next(
            (src for src, dst in column_mapping.items() if dst == "doc_series"),
            None,
        )
        series_note = ""
        if series_src:
            filled = (df["doc_series"].astype(str).str.strip() != "").sum()
            series_note = f", серия: {filled} заполнено (кол. «{series_src}»)"
        else:
            series_note = (
                ", серия: колонка не найдена — проверьте заголовок «Серия» "
                f"(колонки файла: {', '.join(list(column_mapping.keys())[:8])}…)"
            )

        return (
            True,
            f"Загружено {n_loaded} сотрудников (лист: {used_sheet}){series_note}",
            n_loaded,
        )

    except Exception as e:
        return False, f"Ошибка загрузки: {str(e)}", 0


def _write_employees_meta(source: str = "", loaded_by: str = "") -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        meta = {
            "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "count": len(EMPLOYEES_DB) if EMPLOYEES_DB is not None else 0,
            "source": source,
            "loaded_by": loaded_by,
        }
        with open(EMPLOYEES_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get_employees_cache_meta() -> Dict:
    if not EMPLOYEES_META_FILE.exists():
        return {}
    try:
        with open(EMPLOYEES_META_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_employees_cache(source: str = "", loaded_by: str = "") -> bool:
    """Сохранить базу: SQLite (основное) + pickle (резерв)."""
    global EMPLOYEES_DB, _USE_SQLITE
    df = EMPLOYEES_DB
    if df is None or df.empty:
        if employees_store.is_ready():
            return True
        return False
    try:
        employees_store.replace_from_dataframe(df, source=source, loaded_by=loaded_by)
        _USE_SQLITE = True
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(EMPLOYEES_CACHE_FILE, "wb") as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        _write_employees_meta(source=source, loaded_by=loaded_by)
        EMPLOYEES_DB = None
        return True
    except OSError:
        return False


def load_employees_cache(force: bool = False) -> Tuple[bool, str, int]:
    """Загрузить общую базу: SQLite (приоритет) или pickle + миграция."""
    global EMPLOYEES_DB, _USE_SQLITE
    if employees_store.is_ready():
        _USE_SQLITE = True
        EMPLOYEES_DB = None
        n = employees_store.count_all()
        meta = get_employees_cache_meta()
        extra = _meta_suffix(meta)
        return True, f"Общая база (SQLite): {n} сотрудников{extra}", n

    if EMPLOYEES_CACHE_FILE.exists():
        ok, msg, n = employees_store.migrate_from_pickle()
        if ok:
            _USE_SQLITE = True
            EMPLOYEES_DB = None
            meta = get_employees_cache_meta()
            return True, f"{msg}{_meta_suffix(meta)}", n
        if "устаревший" in msg:
            return False, msg + " Admin: перезагрузите базу из Excel.", 0

    if not force and EMPLOYEES_DB is not None and not EMPLOYEES_DB.empty:
        return True, f"База в памяти: {len(EMPLOYEES_DB)} сотрудников", len(EMPLOYEES_DB)

    if not EMPLOYEES_CACHE_FILE.exists():
        EMPLOYEES_DB = None
        _USE_SQLITE = False
        return False, "Общая база не найдена. Admin: Настройки → Загрузить базу.", 0
    try:
        with open(EMPLOYEES_CACHE_FILE, "rb") as f:
            EMPLOYEES_DB = pickle.load(f)
        if EMPLOYEES_DB is None or EMPLOYEES_DB.empty:
            EMPLOYEES_DB = None
            return False, "Кэш базы пуст", 0
        if "doc_series" not in EMPLOYEES_DB.columns:
            EMPLOYEES_DB = None
            return (
                False,
                "Кэш устарел (нет серии паспорта). Admin: перезагрузите базу из Excel.",
                0,
            )
        employees_store.replace_from_dataframe(
            EMPLOYEES_DB, source="employees_cache.pkl", loaded_by="migrate"
        )
        _USE_SQLITE = True
        n = len(EMPLOYEES_DB)
        EMPLOYEES_DB = None
        meta = get_employees_cache_meta()
        return True, f"Общая база: {n} сотрудников (миграция в SQLite){_meta_suffix(meta)}", n
    except (OSError, pickle.PickleError, Exception) as e:
        EMPLOYEES_DB = None
        _USE_SQLITE = False
        return False, f"Ошибка чтения кэша: {e}", 0


def _meta_suffix(meta: Dict) -> str:
    if not meta.get("updated_at"):
        return ""
    s = f" (обновлено {meta['updated_at']}"
    if meta.get("loaded_by"):
        s += f", {meta['loaded_by']}"
    return s + ")"


def _has_in_memory_db() -> bool:
    return EMPLOYEES_DB is not None and not EMPLOYEES_DB.empty


def employees_available() -> bool:
    return _has_in_memory_db() or employees_store.is_ready()


def get_employees_count() -> int:
    if _has_in_memory_db():
        return len(EMPLOYEES_DB)
    if employees_store.is_ready():
        return employees_store.count_all()
    return 0


def get_department_list() -> List[str]:
    if _has_in_memory_db() and "department" in EMPLOYEES_DB.columns:
        return sorted(
            EMPLOYEES_DB["department"].dropna().astype(str).unique().tolist()
        )
    if employees_store.is_ready():
        return employees_store.list_departments()
    if EMPLOYEES_DB is not None and "department" in EMPLOYEES_DB.columns:
        return sorted(
            EMPLOYEES_DB["department"].dropna().astype(str).unique().tolist()
        )
    return []


def get_employees_db() -> Optional[pd.DataFrame]:
    """Полный DataFrame в памяти (если есть); при SQLite-only — None (используйте search API)."""
    if EMPLOYEES_DB is not None:
        return EMPLOYEES_DB
    if employees_store.is_ready():
        return None
    return None


def get_employees_db_for_export() -> Optional[pd.DataFrame]:
    if EMPLOYEES_DB is not None and not EMPLOYEES_DB.empty:
        return EMPLOYEES_DB
    if employees_store.is_ready():
        return employees_store.load_all_dataframe()
    return None


def _normalize_department_filter(department_filter: str = None) -> Optional[str]:
    if not department_filter or str(department_filter).strip().lower() == "admin":
        return None
    return department_filter


def find_employee_by_fio(fio: str, department_filter: str = None) -> Tuple[Optional[Dict], str]:
    if not employees_available():
        return None, "not_found"

    department_filter = _normalize_department_filter(department_filter)
    fio_hash = hash_fio(fio)

    if _has_in_memory_db():
        pass
    elif employees_store.is_ready():
        matches = employees_store.find_by_fio_hash(fio_hash)
        if len(matches) == 1:
            emp = matches[0]
            if department_filter and department_filter not in emp.get("department", ""):
                return None, "not_found"
            return emp, "found"
        if len(matches) > 1:
            if department_filter:
                filtered = [
                    m for m in matches
                    if department_filter.lower() in str(m.get("department", "")).lower()
                ]
                if len(filtered) == 1:
                    return filtered[0], "found"
                if len(filtered) > 1:
                    return filtered, "multiple"
            return matches, "multiple"
        parts = normalize_fio(fio).lower().split()
        if len(parts) >= 2:
            partial = employees_store.search_partial_fio(
                parts, department_filter, limit=50
            )
            if len(partial) == 1:
                return partial[0], "found"
            if len(partial) > 1:
                return partial, "multiple"
        return None, "not_found"

    global EMPLOYEES_DB
    matches = EMPLOYEES_DB[EMPLOYEES_DB["fio_hash"] == fio_hash]

    if len(matches) == 1:
        emp = matches.iloc[0].to_dict()
        if department_filter and department_filter not in emp.get("department", ""):
            return None, "not_found"
        return emp, "found"

    if len(matches) > 1:
        if department_filter:
            filtered = matches[matches["department"].str.contains(department_filter, na=False, case=False)]
            if len(filtered) == 1:
                return filtered.iloc[0].to_dict(), "found"
            if len(filtered) > 1:
                return filtered.to_dict("records"), "multiple"
        return matches.to_dict("records"), "multiple"

    parts = normalize_fio(fio).lower().split()
    if len(parts) >= 2:
        mask = pd.Series([False] * len(EMPLOYEES_DB), index=EMPLOYEES_DB.index)
        for part in parts:
            mask |= EMPLOYEES_DB["fio"].str.lower().str.contains(part, na=False)
        matches = EMPLOYEES_DB[mask]
        if department_filter:
            dept_matches = matches[matches["department"].str.contains(department_filter, na=False, case=False)]
            if len(dept_matches) >= 1:
                matches = dept_matches
        if len(matches) == 1:
            return matches.iloc[0].to_dict(), "found"
        if len(matches) > 1:
            return matches.to_dict("records"), "multiple"

    return None, "not_found"


def get_all_employees() -> List[Dict]:
    global EMPLOYEES_DB

    if EMPLOYEES_DB is None:
        return []

    return EMPLOYEES_DB.to_dict('records')


def get_employees_records(
    search: str = None,
    department: str = None,
    limit: int = 2000,
) -> List[Dict]:
    """Список сотрудников для каталога (с фильтром, без загрузки всей базы в память)."""
    df = filter_employees_db(search, department)
    if df is None or df.empty:
        return []
    if limit is not None and limit > 0 and len(df) > limit:
        df = df.head(limit)
    return df.to_dict("records")


def employee_dict_to_display_row(emp: Dict, row_num: int) -> Dict:
    from config import ALL_COLUMNS
    from excel_handler import transliterate_name, get_classification, get_document_type, format_date_ddmmyyyy

    fio = emp.get("fio", "")
    citizenship = emp.get("citizenship", "")
    row = {c: "" for c in ALL_COLUMNS}
    row["№"] = row_num
    row["Подразделение"] = emp.get("department", "")
    row["Отдел"] = emp.get("department_category", "")
    row["Классификация"] = get_classification(emp.get("position", ""))
    row["Ф.И.О."] = fio
    row["Ф.И.О лат"] = transliterate_name(fio, citizenship)
    row["Табельный номер"] = emp.get("tab_num", "")
    row["Гражданство"] = citizenship
    row["Дата рождения"] = format_date_ddmmyyyy(emp.get("birth_date", ""))
    row["Вид документа"] = get_document_type(citizenship, emp.get("doc_series", ""))
    row["Серия"] = format_passport_field(emp.get("doc_series", ""))
    row["Номер"] = format_passport_field(emp.get("doc_num", ""))
    row["Дата выдачи"] = format_date_ddmmyyyy(emp.get("doc_date", ""))
    row["Дата окончания"] = format_date_ddmmyyyy(emp.get("doc_expiry", ""))
    row["Кем выдан"] = emp.get("doc_issuer", "")
    row["Адрес"] = emp.get("address", "")
    row["Телефон"] = emp.get("phone", "")
    return row


def filter_employees_db(
    search: str = None,
    department: str = None,
    limit: int = 50000,
    offset: int = 0,
) -> pd.DataFrame:
    """Отфильтрованный срез базы (без преобразования в 34 колонки заявки)."""
    department = _normalize_department_filter(department)
    if not _has_in_memory_db() and employees_store.is_ready():
        records = employees_store.search(
            search, department, limit=limit, offset=offset
        )
        return pd.DataFrame(records) if records else pd.DataFrame()
    global EMPLOYEES_DB
    if EMPLOYEES_DB is None or EMPLOYEES_DB.empty:
        return pd.DataFrame()
    df = EMPLOYEES_DB
    if department:
        df = df[df["department"].astype(str).str.contains(department, na=False, case=False)]
    if search and str(search).strip():
        q = str(search).strip().lower()
        fio = df["fio"].astype(str).str.lower()
        tab = df["tab_num"].astype(str).str.lower()
        df = df[fio.str.contains(q, na=False) | tab.str.contains(q, na=False)]
    return df.iloc[offset : offset + limit]


def count_filtered_employees(search: str = None, department: str = None) -> int:
    department = _normalize_department_filter(department)
    if not _has_in_memory_db() and employees_store.is_ready():
        return employees_store.count_filtered(search, department)
    filtered = filter_employees_db(search, department, limit=999999)
    return 0 if filtered is None or filtered.empty else len(filtered)


def get_employees_display_dataframe(
    search: str = None,
    department: str = None,
    limit: int = None,
    offset: int = 0,
) -> pd.DataFrame:
    """База сотрудников в формате колонок Excel (лист ВСЕ ОП).

    limit=-1 — все отфильтрованные строки (экспорт).
    limit=500 (по умолчанию) — порция для экрана.
    """
    from config import ALL_COLUMNS, BASE_GRID_PAGE_SIZE

    if limit is None:
        limit = BASE_GRID_PAGE_SIZE

    if limit is not None and limit < 0:
        chunk_limit = 999999
    elif limit is None:
        chunk_limit = BASE_GRID_PAGE_SIZE
    else:
        chunk_limit = limit

    filtered = filter_employees_db(
        search, department, limit=chunk_limit, offset=offset
    )
    if filtered is None or filtered.empty:
        return pd.DataFrame(columns=ALL_COLUMNS)

    rows = []
    for i, (_, emp) in enumerate(filtered.iterrows()):
        emp_d = emp.to_dict() if hasattr(emp, "to_dict") else dict(emp)
        rows.append(employee_dict_to_display_row(emp_d, offset + i + 1))
    return pd.DataFrame(rows, columns=ALL_COLUMNS)


def _display_row_to_employee_record(row) -> Dict:
    fio = safe_str(row.get("Ф.И.О.", ""))
    return {
        "fio": fio,
        "fio_hash": hash_fio(fio),
        "tab_num": safe_str(row.get("Табельный номер", "")),
        "position": "",
        "department": safe_str(row.get("Подразделение", "")),
        "department_category": safe_str(row.get("Отдел", "")),
        "citizenship": safe_str(row.get("Гражданство", "")),
        "birth_date": safe_str(row.get("Дата рождения", "")),
        "doc_series": safe_str(row.get("Серия", "")),
        "doc_num": safe_str(row.get("Номер", "")),
        "doc_date": safe_str(row.get("Дата выдачи", "")),
        "doc_expiry": safe_str(row.get("Дата окончания", "")),
        "doc_issuer": safe_str(row.get("Кем выдан", "")),
        "address": safe_str(row.get("Адрес", "")),
        "phone": safe_str(row.get("Телефон", "")),
    }


def save_employees_from_display_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Обновить в кэше только изменённые строки (не затирать всю базу)."""
    global EMPLOYEES_DB
    if df is None or df.empty:
        return False, "Нет данных"
    if EMPLOYEES_DB is None:
        EMPLOYEES_DB = pd.DataFrame()

    updated = 0
    added = 0
    for _, row in df.iterrows():
        fio = safe_str(row.get("Ф.И.О.", ""))
        if not fio:
            continue
        record = _display_row_to_employee_record(row)
        h = record["fio_hash"]
        idx = EMPLOYEES_DB.index[EMPLOYEES_DB["fio_hash"] == h].tolist() if "fio_hash" in EMPLOYEES_DB.columns else []
        if idx:
            for key, val in record.items():
                EMPLOYEES_DB.at[idx[0], key] = val
            updated += 1
        else:
            EMPLOYEES_DB = pd.concat([EMPLOYEES_DB, pd.DataFrame([record])], ignore_index=True)
            added += 1

    if updated + added == 0:
        return False, "Нет строк с ФИО"
    save_employees_cache()
    total = len(EMPLOYEES_DB)
    return True, f"Обновлено: {updated}, добавлено: {added}. Всего в базе: {total}"


def export_employees_to_excel(file_path: str) -> Tuple[bool, str]:
    """Выгрузка базы в формате листа «ВСЕ ОП»."""
    global EMPLOYEES_DB
    if not employees_available():
        return False, "База пуста"
    try:
        from config import ALL_COLUMNS
        from excel_handler import transliterate_name, get_classification, get_document_type, format_date_ddmmyyyy

        df = get_employees_display_dataframe(limit=-1)
        df.to_excel(file_path, sheet_name="ВСЕ ОП", index=False)
        rows = len(df)
        return True, f"Выгружено {rows} сотрудников"
    except Exception as e:
        return False, str(e)


def add_or_update_employee(data: Dict) -> Tuple[bool, str]:
    """Добавить или обновить сотрудника в базе до следующей загрузки Excel."""
    global EMPLOYEES_DB
    if employees_store.is_ready() and (EMPLOYEES_DB is None or EMPLOYEES_DB.empty):
        EMPLOYEES_DB = employees_store.load_all_dataframe()
    if EMPLOYEES_DB is None:
        EMPLOYEES_DB = pd.DataFrame(columns=[
            "fio", "tab_num", "position", "employment_status", "department", "citizenship",
            "birth_date", "doc_series", "doc_num", "doc_date",
            "doc_issuer", "address", "phone", "doc_expiry", "department_category", "fio_hash",
        ])

    fio = safe_str(data.get("fio"))
    if not fio:
        return False, "ФИО обязательно"

    tab_num = safe_str(data.get("tab_num"))
    fio_hash = hash_fio(fio)
    record = {
        "fio": fio,
        "fio_hash": fio_hash,
        "tab_num": tab_num,
        "position": safe_str(data.get("position")),
        "employment_status": normalize_employment_status(data.get("employment_status")),
        "department": safe_str(data.get("department")),
        "department_category": safe_str(data.get("department_category")),
        "citizenship": safe_str(data.get("citizenship")),
        "birth_date": safe_str(data.get("birth_date")),
        "doc_series": safe_str(data.get("doc_series")),
        "doc_num": safe_str(data.get("doc_num")),
        "doc_date": safe_str(data.get("doc_date")),
        "doc_expiry": safe_str(data.get("doc_expiry")),
        "doc_issuer": safe_str(data.get("doc_issuer")),
        "address": safe_str(data.get("address")),
        "phone": safe_str(data.get("phone")),
    }

    if tab_num and "tab_num" in EMPLOYEES_DB.columns:
        mask = EMPLOYEES_DB["tab_num"] == tab_num
        if mask.any():
            for col, val in record.items():
                EMPLOYEES_DB.loc[mask, col] = val
            save_employees_cache()
            return True, "Сотрудник обновлён"

    if "fio_hash" in EMPLOYEES_DB.columns:
        mask = EMPLOYEES_DB["fio_hash"] == fio_hash
        if mask.any():
            for col, val in record.items():
                EMPLOYEES_DB.loc[mask, col] = val
            save_employees_cache()
            return True, "Сотрудник обновлён"

    EMPLOYEES_DB = pd.concat([EMPLOYEES_DB, pd.DataFrame([record])], ignore_index=True)
    save_employees_cache()
    return True, "Сотрудник добавлен в базу"


def add_employees_from_application(df: pd.DataFrame, allowed_department: str = None) -> Tuple[int, int]:
    """Добавить в базу сотрудников из заявки, которых ещё нет."""
    if df is None or df.empty:
        return 0, 0
    added = 0
    skipped = 0
    for _, row in df.iterrows():
        fio = safe_str(row.get("Ф.И.О.", ""))
        if not fio:
            skipped += 1
            continue
        emp, status = find_employee_by_fio(fio, allowed_department)
        if status == "found":
            skipped += 1
            continue
        data = {
            "fio": fio,
            "tab_num": safe_str(row.get("Табельный номер", "")),
            "department": safe_str(row.get("Подразделение", "")),
            "department_category": safe_str(row.get("Отдел", "")),
            "citizenship": safe_str(row.get("Гражданство", "")),
            "birth_date": safe_str(row.get("Дата рождения", "")),
            "doc_series": safe_str(row.get("Серия", "")),
            "doc_num": safe_str(row.get("Номер", "")),
            "doc_date": safe_str(row.get("Дата выдачи", "")),
            "doc_expiry": safe_str(row.get("Дата окончания", "")),
            "doc_issuer": safe_str(row.get("Кем выдан", "")),
            "address": safe_str(row.get("Адрес", "")),
            "phone": safe_str(row.get("Телефон", "")),
            "position": "",
        }
        ok, _ = add_or_update_employee(data)
        if ok:
            added += 1
        else:
            skipped += 1
    return added, skipped


def find_employee_by_tab_num(tab_num: str) -> Optional[Dict]:
    """Поиск сотрудника по табельному номеру для проверки дубликатов"""
    global EMPLOYEES_DB

    if EMPLOYEES_DB is None or not tab_num:
        return None

    matches = EMPLOYEES_DB[EMPLOYEES_DB['tab_num'] == tab_num]
    if len(matches) > 0:
        return matches.iloc[0].to_dict()
    return None
