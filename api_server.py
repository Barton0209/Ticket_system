# api_server.py
"""
HTTP API для Electron / внешних клиентов (этап 2).
Запуск: python api_server.py
       или run_api.bat
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from fastapi import Depends, FastAPI, HTTPException, Header
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as e:
    raise SystemExit(
        "Установите API-зависимости: pip install -r requirements-api.txt"
    ) from e

from config import API_HOST, API_PORT, APP_VERSION
from database import (
    employees_available,
    find_employee_by_fio,
    get_employees_cache_meta,
    get_employees_count,
    load_employees_cache,
)
import employees_store
from routes import load_routes

API_KEY = os.environ.get("TICKET_API_KEY", "")

# Предупреждение при отсутствии API ключа
if not API_KEY:
    import warnings
    warnings.warn(
        "⚠️ TICKET_API_KEY не установлен! API доступно всем без ограничений. "
        "Установите переменную окружения TICKET_API_KEY для безопасности.",
        UserWarning,
        stacklevel=2
    )

app = FastAPI(
    title="Ticket System API",
    version=APP_VERSION,
    description="REST-слой над SQLite и Python-логикой для Electron UI",
)

# CORS: ограничено localhost для безопасности
# Для production добавьте реальные домены Electron приложения
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",  # Vite dev server
    "http://localhost:5173",
    "app://localhost",  # Electron protocol
    "http://127.0.0.1:8765",  # API itself
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Api-Key"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=600,
)

# Rate limiting для защиты от brute-force
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    limiter = None
    app.state.limiter = None


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class SearchBody(BaseModel):
    q: Optional[str] = None
    department: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)


class PdfProcessBody(BaseModel):
    path: str


class BatchLookupBody(BaseModel):
    fios: List[str] = Field(default_factory=list)
    department: Optional[str] = None


class LoginBody(BaseModel):
    login: str
    password: str


class LoadDbBody(BaseModel):
    path: str
    loaded_by: str = "Admin"


class PdfFolderBody(BaseModel):
    folder_path: str


class ExportApplicationBody(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    output_path: str
    department: str = ""


class EmployeesToRowsBody(BaseModel):
    employees: List[Dict[str, Any]] = Field(default_factory=list)
    start_index: int = Field(default=1, ge=1)
    department: str = ""


class WizardToRowsBody(BaseModel):
    results: List[Dict[str, Any]] = Field(default_factory=list)
    start_index: int = Field(default=1, ge=1)
    department: str = ""


class MergeRowBody(BaseModel):
    existing: Dict[str, Any] = Field(default_factory=dict)
    employee: Dict[str, Any] = Field(default_factory=dict)
    row_num: Optional[int] = None


class AddFromAppBody(BaseModel):
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    department: Optional[str] = None


@app.on_event("startup")
def _startup():
    load_employees_cache(force=False)


@app.get("/")
def root():
    """Корень: подсказка — у эндпоинтов есть пути ниже `/`."""
    return {
        "service": "Ticket System API",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "openapi": "/openapi.json",
        "hint": "Браузер на / даёт только эту заготовку; откройте /docs или /health.",
        "auth": "При TICKET_API_KEY заголовок: X-Api-Key",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "employees_ready": employees_available(),
        "employees_count": get_employees_count(),
    }


@app.get("/meta/employees", dependencies=[Depends(_require_api_key)])
def meta_employees():
    meta = get_employees_cache_meta()
    return {
        "count": get_employees_count(),
        "ready": employees_available(),
        "meta": meta,
    }


def _search_department(department: Optional[str]) -> Optional[str]:
    from database import _normalize_department_filter

    return _normalize_department_filter(department)


@app.post("/employees/search", dependencies=[Depends(_require_api_key)])
def employees_search(body: SearchBody):
    if not employees_store.is_ready():
        load_employees_cache(force=True)
    if not employees_available():
        raise HTTPException(status_code=503, detail="Employee database not loaded")

    dept = _search_department(body.department)
    total = employees_store.count_filtered(body.q, dept)
    rows = employees_store.search(
        body.q,
        dept,
        limit=body.limit,
        offset=body.offset,
    )
    return {"total": total, "items": rows, "limit": body.limit, "offset": body.offset}


@app.post("/employees/base-grid", dependencies=[Depends(_require_api_key)])
def employees_base_grid(body: SearchBody):
    """Таблица базы в формате Excel (34 колонки), как вкладка «База» в Tkinter."""
    from database import count_filtered_employees, get_employees_display_dataframe

    if not employees_store.is_ready():
        load_employees_cache(force=True)
    if not employees_available():
        raise HTTPException(status_code=503, detail="Employee database not loaded")

    dept = _search_department(body.department)
    total = count_filtered_employees(body.q, dept)
    df = get_employees_display_dataframe(
        search=body.q,
        department=dept,
        limit=body.limit,
        offset=body.offset,
    )
    if df is None or df.empty:
        items: List[Dict[str, Any]] = []
    else:
        items = df.to_dict(orient="records")
    return {"total": total, "items": items, "limit": body.limit, "offset": body.offset}


@app.get("/employees/{fio_hash}", dependencies=[Depends(_require_api_key)])
def employee_by_hash(fio_hash: str):
    if not employees_store.is_ready():
        raise HTTPException(status_code=503, detail="Database not ready")
    rows = employees_store.find_by_fio_hash(fio_hash)
    if not rows:
        raise HTTPException(status_code=404, detail="Not found")
    return {"items": rows}


@app.get("/departments", dependencies=[Depends(_require_api_key)])
def departments_list():
    if not employees_store.is_ready():
        load_employees_cache(force=True)
    if not employees_available():
        return {"items": []}
    return {"items": employees_store.list_departments()}


@app.get("/employees/lookup/fio", dependencies=[Depends(_require_api_key)])
def employee_lookup_fio(fio: str, department: Optional[str] = None):
    emp, status = find_employee_by_fio(fio, department)
    if status == "multiple":
        candidates = emp if isinstance(emp, list) else []
        return {"status": status, "employee": None, "candidates": candidates}
    return {
        "status": status,
        "employee": emp if status == "found" else None,
        "candidates": [],
    }


@app.post("/employees/lookup/batch", dependencies=[Depends(_require_api_key)])
def employees_lookup_batch(body: BatchLookupBody):
    if not employees_available():
        raise HTTPException(status_code=503, detail="Employee database not loaded")
    items = []
    for fio in body.fios:
        fio = (fio or "").strip()
        if not fio:
            continue
        emp, status = find_employee_by_fio(fio, body.department)
        entry: Dict[str, Any] = {"query": fio, "status": status}
        if status == "found":
            entry["employee"] = emp
            entry["candidates"] = []
        elif status == "multiple":
            entry["employee"] = None
            entry["candidates"] = emp if isinstance(emp, list) else []
        else:
            entry["employee"] = None
            entry["candidates"] = []
        items.append(entry)
    found = sum(1 for x in items if x["status"] == "found")
    return {"total": len(items), "found": found, "items": items}


@app.post("/pdf/process", dependencies=[Depends(_require_api_key)])
def pdf_process(body: PdfProcessBody):
    path = body.path.strip()
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="File not found")
    try:
        from pdf_processor import process_ticket_application_pdf

        results = process_ticket_application_pdf(path)
        return {"ok": True, "count": len(results), "items": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/routes", dependencies=[Depends(_require_api_key)])
def routes_list():
    return {"routes": load_routes()}


@app.get("/auth/logins")
def auth_logins():
    from users_manager import get_all_logins, load_users_cache

    load_users_cache()
    return {"logins": ["Admin"] + get_all_logins()}


@app.post("/auth/login")
@limiter.limit("5/minute") if limiter else lambda x: x
def auth_login(body: LoginBody, request: Any = None):
    from users_manager import authenticate, load_users_cache

    load_users_cache()
    user, is_admin, dept = authenticate(body.login.strip(), body.password)
    if not is_admin and user is None:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    profile: Dict[str, str] = {}
    if user:
        profile = {
            "fio": user.fio or "",
            "email": user.email or "",
            "position": user.position or "",
            "dept_category": user.dept_category or "",
        }
    return {
        "ok": True,
        "login": body.login.strip(),
        "is_admin": is_admin,
        "department": dept or body.login.strip(),
        "profile": profile,
    }


@app.post("/database/add-from-application", dependencies=[Depends(_require_api_key)])
def database_add_from_application(body: AddFromAppBody):
    import pandas as pd
    from database import add_employees_from_application

    if not body.rows:
        raise HTTPException(status_code=400, detail="Нет данных заявки")
    df = pd.DataFrame(body.rows)
    added, skipped = add_employees_from_application(df, body.department)
    return {"added": added, "skipped": skipped}


@app.post("/database/reload-cache", dependencies=[Depends(_require_api_key)])
def database_reload_cache():
    ok, msg, n = load_employees_cache(force=True)
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    return {"ok": True, "message": msg, "count": n}


@app.post("/database/load", dependencies=[Depends(_require_api_key)])
def database_load(body: LoadDbBody):
    from database import load_employees_base

    path = body.path.strip()
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="Файл не найден")
    ok, msg, n = load_employees_base(path, loaded_by=body.loaded_by or "Admin")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "count": n}


@app.post("/application/rows-from-employees", dependencies=[Depends(_require_api_key)])
def application_rows_from_employees(body: EmployeesToRowsBody):
    from excel_handler import employee_to_application_row

    rows = [
        employee_to_application_row(emp, body.start_index + i)
        for i, emp in enumerate(body.employees)
    ]
    return {"rows": rows}


@app.post("/application/rows-from-wizard", dependencies=[Depends(_require_api_key)])
def application_rows_from_wizard(body: WizardToRowsBody):
    from application_builder import build_rows_from_wizard_result

    all_rows: List[Dict[str, Any]] = []
    idx = body.start_index
    for res in body.results:
        built = build_rows_from_wizard_result(res, body.department, idx)
        all_rows.extend(built)
        idx += len(built)
    return {"rows": all_rows}


@app.post("/application/merge-row", dependencies=[Depends(_require_api_key)])
def application_merge_row(body: MergeRowBody):
    from excel_handler import merge_employee_into_application_row

    rn = body.row_num
    if rn is None:
        try:
            rn = int(body.existing.get("№", 1))
        except (TypeError, ValueError):
            rn = 1
    row = merge_employee_into_application_row(body.existing, body.employee, rn)
    return {"row": row}


@app.post("/application/export", dependencies=[Depends(_require_api_key)])
def application_export(body: ExportApplicationBody):
    from config import ALL_COLUMNS
    from template_manager import export_application

    path = body.output_path.strip()
    if not path:
        raise HTTPException(status_code=400, detail="Путь не указан")
    if not body.rows:
        raise HTTPException(status_code=400, detail="Нет данных")
    import pandas as pd

    df = pd.DataFrame(body.rows)
    for c in ALL_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[ALL_COLUMNS]
    ok, msg = export_application(df, path)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "path": path}


@app.post("/pdf/process-folder", dependencies=[Depends(_require_api_key)])
def pdf_process_folder(body: PdfFolderBody):
    folder = body.folder_path.strip()
    if not folder or not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail="Папка не найдена")
    try:
        from pdf_processor import process_pdf_folder

        results = process_pdf_folder(folder, progress_callback=None)
        return {"ok": True, "count": len(results), "items": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def main():
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
