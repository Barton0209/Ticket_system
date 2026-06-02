# employees_store.py
"""SQLite-хранилище базы сотрудников (общее для всех пользователей)."""

from __future__ import annotations

import json
import pickle
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import DATA_DIR, EMPLOYEES_CACHE_FILE, EMPLOYEES_DB_FILE, EMPLOYEES_META_FILE

EMPLOYEE_FIELDS = [
    "fio",
    "tab_num",
    "position",
    "employment_status",
    "department",
    "citizenship",
    "birth_date",
    "doc_series",
    "doc_num",
    "doc_date",
    "doc_issuer",
    "address",
    "phone",
    "doc_expiry",
    "department_category",
    "fio_hash",
]

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio TEXT NOT NULL DEFAULT '',
    tab_num TEXT DEFAULT '',
    position TEXT DEFAULT '',
    employment_status TEXT DEFAULT '',
    department TEXT DEFAULT '',
    citizenship TEXT DEFAULT '',
    birth_date TEXT DEFAULT '',
    doc_series TEXT DEFAULT '',
    doc_num TEXT DEFAULT '',
    doc_date TEXT DEFAULT '',
    doc_issuer TEXT DEFAULT '',
    address TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    doc_expiry TEXT DEFAULT '',
    department_category TEXT DEFAULT '',
    fio_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_employees_fio_hash ON employees(fio_hash);
CREATE INDEX IF NOT EXISTS idx_employees_fio ON employees(fio);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_tab ON employees(tab_num);
"""


def db_path() -> Path:
    return EMPLOYEES_DB_FILE


def is_ready() -> bool:
    p = db_path()
    return p.exists() and p.stat().st_size > 0


@contextmanager
def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_CREATE_SQL)


def count_all() -> int:
    if not is_ready():
        return 0
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM employees").fetchone()
        return int(row[0]) if row else 0


def replace_from_dataframe(df: pd.DataFrame, source: str = "", loaded_by: str = "") -> int:
    """Полная перезапись базы (после загрузки Admin из Excel)."""
    init_db()
    cols = [c for c in EMPLOYEE_FIELDS if c in df.columns]
    if "fio_hash" not in cols:
        raise ValueError("DataFrame must contain fio_hash")

    rows = []
    for _, r in df.iterrows():
        rows.append(tuple(str(r.get(c, "") or "") for c in cols))

    placeholders = ",".join("?" * len(cols))
    col_list = ",".join(cols)

    with _connect() as conn:
        conn.execute("DELETE FROM employees")
        conn.executemany(
            f"INSERT INTO employees ({col_list}) VALUES ({placeholders})",
            rows,
        )

    meta = {
        "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "count": len(rows),
        "source": source,
        "loaded_by": loaded_by,
        "storage": "sqlite",
    }
    try:
        with open(EMPLOYEES_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return len(rows)


def migrate_from_pickle() -> Tuple[bool, str, int]:
    """Один раз импортировать employees_cache.pkl → SQLite."""
    if not EMPLOYEES_CACHE_FILE.exists():
        return False, "pickle не найден", 0
    try:
        # Проверка целостности pickle файла
        file_size = EMPLOYEES_CACHE_FILE.stat().st_size
        if file_size == 0:
            return False, "pickle пуст (нулевой размер)", 0
        if file_size > 500 * 1024 * 1024:  # 500 MB лимит
            return False, "pickle слишком большой (>500MB)", 0
        
        with open(EMPLOYEES_CACHE_FILE, "rb") as f:
            df = pickle.load(f)
        if df is None or df.empty:
            return False, "pickle пуст", 0
        if "doc_series" not in df.columns:
            return False, "устаревший pickle (нет серии)", 0
        n = replace_from_dataframe(df, source="employees_cache.pkl", loaded_by="migrate")
        return True, f"Импортировано в SQLite: {n}", n
    except Exception as e:
        return False, str(e), 0


def _row_to_dict(row: sqlite3.Row) -> Dict:
    return {k: row[k] for k in row.keys() if k != "id"}


def find_by_fio_hash(fio_hash: str) -> List[Dict]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM employees WHERE fio_hash = ?",
            (fio_hash,),
        )
        return [_row_to_dict(r) for r in cur.fetchall()]


def search(
    search: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 2000,
    offset: int = 0,
) -> List[Dict]:
    sql = "SELECT * FROM employees WHERE 1=1"
    params: list = []
    if department:
        sql += " AND department LIKE ?"
        params.append(f"%{department}%")
    if search and str(search).strip():
        q = f"%{str(search).strip().lower()}%"
        sql += " AND (LOWER(fio) LIKE ? OR LOWER(tab_num) LIKE ?)"
        params.extend([q, q])
    sql += " ORDER BY fio LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [_row_to_dict(r) for r in cur.fetchall()]


def count_filtered(
    search: Optional[str] = None,
    department: Optional[str] = None,
) -> int:
    sql = "SELECT COUNT(*) FROM employees WHERE 1=1"
    params: list = []
    if department:
        sql += " AND department LIKE ?"
        params.append(f"%{department}%")
    if search and str(search).strip():
        q = f"%{str(search).strip().lower()}%"
        sql += " AND (LOWER(fio) LIKE ? OR LOWER(tab_num) LIKE ?)"
        params.extend([q, q])
    with _connect() as conn:
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0


def search_partial_fio(
    parts: List[str],
    department: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Частичный поиск по словам ФИО (как в find_employee_by_fio)."""
    if not parts:
        return []
    sql = "SELECT * FROM employees WHERE 1=1"
    params: list = []
    if department:
        sql += " AND department LIKE ?"
        params.append(f"%{department}%")
    for part in parts:
        sql += " AND LOWER(fio) LIKE ?"
        params.append(f"%{part.lower()}%")
    sql += " ORDER BY fio LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        cur = conn.execute(sql, params)
        return [_row_to_dict(r) for r in cur.fetchall()]


def load_all_dataframe() -> pd.DataFrame:
    """Полная выгрузка (экспорт Admin)."""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM employees ORDER BY fio")
        rows = [_row_to_dict(r) for r in cur.fetchall()]
    if not rows:
        return pd.DataFrame(columns=EMPLOYEE_FIELDS)
    return pd.DataFrame(rows)


def list_departments() -> List[str]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT DISTINCT department FROM employees "
            "WHERE department IS NOT NULL AND TRIM(department) != '' "
            "ORDER BY department"
        )
        return [str(r[0]) for r in cur.fetchall()]


def load_dataframe_chunk(
    search: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> pd.DataFrame:
    records = search(search, department, limit=limit, offset=offset)
    if not records:
        return pd.DataFrame(columns=EMPLOYEE_FIELDS)
    return pd.DataFrame(records)
