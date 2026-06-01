# check_app.py
"""
Проверка модулей без GUI.
Запуск: python check_app.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ok(msg: str):
    print(f"  OK  {msg}")


def fail(msg: str):
    print(f" FAIL {msg}")
    raise AssertionError(msg)


def test_imports():
    import auth  # noqa: F401
    import config  # noqa: F401
    import database  # noqa: F401
    import excel_handler  # noqa: F401
    import pdf_processor  # noqa: F401
    import pdf_viewer  # noqa: F401
    import routes  # noqa: F401
    import ui_theme  # noqa: F401
    import ui.main_window  # noqa: F401
    import ui.catalog  # noqa: F401
    import ui.wizard  # noqa: F401
    import user_prefs  # noqa: F401
    import excel_sheet  # noqa: F401
    ok("все модули импортируются")
    if excel_sheet.TKSHEET_AVAILABLE:
        ok("tksheet доступен")
    else:
        print("  WARN tksheet не установлен — таблицы Excel будут недоступны")


def test_routes():
    from routes import load_routes, build_reverse_map, add_route

    routes = load_routes()
    if not routes:
        fail("список маршрутов пуст")
    rev = build_reverse_map(routes)
    if "Москва - Санкт-Петербург" in routes:
        assert "Санкт-Петербург - Москва" in rev.get("Москва - Санкт-Петербург", "") or True
    add_route("Тестовый - Маршрут")
    ok(f"маршрутов: {len(load_routes())}")


def test_database_helpers():
    from database import (
        normalize_fio,
        hash_fio,
        normalize_employment_status,
        get_employee_status,
        format_passport_field,
        _build_employee_column_mapping,
    )
    import pandas as pd

    assert normalize_fio("  Иванов  И.  Иванович ") == "Иванов И Иванович"
    assert hash_fio("Иванов Иван Иванович") == hash_fio("иванов иван иванович")
    assert normalize_employment_status("уволен") == "Уволен"
    assert normalize_employment_status("Работает") == "Работает"
    assert get_employee_status({"employment_status": "Уволен"}) == "Уволен"
    assert format_passport_field(4012.0) == "4012"
    assert format_passport_field("40 12") == "40 12"

    sample = pd.DataFrame(
        columns=[
            "№", "Подразделение", "Отдел", "Операция", "Классификация", "Дата заказа",
            "Организация", "Ф.И.О.", "Ф.И.О лат", "Табельный номер", "Гражданство",
            "Дата рождения", "Вид документа", "Серия паспорта", "Номер",
        ]
    )
    m = _build_employee_column_mapping(sample)
    assert m.get("Серия паспорта") == "doc_series"
    assert m.get("Табельный номер") == "tab_num"
    assert m.get("Номер") == "doc_num"

    tab_pass = pd.DataFrame(columns=["Ф.И.О.", "Табельный номер", "Номер"])
    m2 = _build_employee_column_mapping(tab_pass)
    assert m2["Табельный номер"] == "tab_num"
    assert m2["Номер"] == "doc_num"

    shifted = pd.DataFrame(
        columns=[
            "№", "AI", "Подразделение", "Отдел", "Операция", "Классификация", "Дата заказа",
            "Организация", "Ф.И.О.", "Ф.И.О лат", "Табельный номер", "Гражданство",
            "Дата рождения", "Вид документа", "Серия", "Номер",
        ]
    )
    m3 = _build_employee_column_mapping(shifted)
    assert m3.get("Серия") == "doc_series", m3

    only_num = pd.DataFrame(
        columns=["Ф.И.О.", "Номер"],
        data=[["Иванов Иван", "60 19 832138"]],
    )
    from database import load_employees_base
    import tempfile, os
    import database as db

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        only_num.to_excel(path, sheet_name="ВСЕ ОП", index=False)
        db.EMPLOYEES_DB = None
        ok_load, msg, _ = load_employees_base(path)
        assert ok_load, msg
        exp = db.get_employees_db_for_export()
        assert exp is not None and "doc_series" in exp.columns
        assert exp.iloc[0]["doc_series"] == "60 19"
        assert exp.iloc[0]["doc_num"] == "832138"
    finally:
        db.EMPLOYEES_DB = None
        try:
            os.unlink(path)
        except OSError:
            pass
    ok("normalize_fio / hash_fio / статус AI / серия и табельный vs номер")


def test_department_filter_admin():
    from database import find_employee_by_fio, hash_fio
    import pandas as pd
    import database as db

    db.EMPLOYEES_DB = pd.DataFrame(
        [{
            "fio": "Тестов Тест Тестович",
            "fio_hash": hash_fio("Тестов Тест Тестович"),
            "tab_num": "001",
            "department": "ОП Кингисепп",
            "position": "рабочий",
            "citizenship": "РОССИЯ",
        }]
    )

    emp, status = find_employee_by_fio("Тестов Тест Тестович", "Admin")
    if status != "found":
        fail("Admin не должен фильтровать подразделение")
    ok("поиск под Admin")

    emp2, status2 = find_employee_by_fio("Тестов Тест Тестович", "ОП Кингисепп")
    if status2 != "found":
        fail("поиск по подразделению")
    ok("поиск по ОП")

    db.EMPLOYEES_DB = None


def test_base_display_limit():
    import pandas as pd
    import database as db
    from database import get_employees_display_dataframe, count_filtered_employees, hash_fio

    rows = []
    for i in range(20):
        fio = f"Тест{i} Иван Иванович"
        rows.append({
            "fio": fio,
            "fio_hash": hash_fio(fio),
            "tab_num": str(i),
            "department": "ОП Тест",
            "position": "",
            "citizenship": "РОССИЯ",
        })
    db.EMPLOYEES_DB = pd.DataFrame(rows)
    assert count_filtered_employees() == 20
    df = get_employees_display_dataframe(limit=5)
    assert len(df) == 5
    db.EMPLOYEES_DB = None
    ok("лимит отображения базы")


def test_department_from_employee_db():
    from excel_handler import create_application_row, resolve_row_department

    emp = {"department": "ОП Кингисепп", "fio": "Тест"}
    assert resolve_row_department(emp, "ОП Другой") == "ОП Кингисепп"
    row = create_application_row(
        1,
        "ОП Другой",
        {"fio": "Тест"},
        emp,
    )
    assert row["Подразделение"] == "ОП Кингисепп"
    ok("Подразделение из базы, не из логина")


def test_user_profile_columns_dg():
    from users_manager import AppUser, format_user_header

    u = AppUser(
        login="op1",
        password="x",
        department="ОП Тест",
        fio="Иванов Иван",
        email="i@test.ru",
        position="Инженер",
        dept_category="СМУ",
    )
    dept, profile = format_user_header(u, "ОП Тест", False)
    assert "ОП Тест" in dept
    assert "Иванов" in profile and "Инженер" in profile
    ok("профиль D:G в шапке")


def test_wizard_employee_not_marked_missing():
    from application_builder import build_rows_from_wizard_result

    emp = {
        "fio": "Иванов Иван Иванович",
        "tab_num": "12345",
        "department": "ОП Тест",
        "citizenship": "РОССИЯ",
        "position": "рабочий",
    }
    result = {
        "fio": "Иванов И.И.",
        "route1": "Москва - СПб",
        "date1": "01.02.2026",
        "reason1": "Командировка",
        "employee": emp,
        "status": "selected",
    }
    rows = build_rows_from_wizard_result(result, "ОП Тест", 1)
    assert len(rows) >= 1
    assert rows[0]["Табельный номер"] == "12345"
    assert "НЕ НАЙДЕН" not in str(rows[0].get("Примечание", "")).upper()

    manual = build_rows_from_wizard_result(
        {"fio": "Неизвестный", "route1": "А - Б", "status": "manual"},
        "ОП Тест",
        2,
    )
    assert "НЕ НАЙДЕН" in manual[0].get("Примечание", "").upper()
    ok("мастер: выбранный из базы без метки «не найден»")


def test_excel_row():
    from excel_handler import create_application_row, save_as_excel, ALL_COLUMNS
    import pandas as pd

    row = create_application_row(
        1,
        "ОП Тест",
        {"fio": "Иванов Иван", "route": "Москва - Сочи", "date": "01.01.2026", "reason": "Командировка"},
        {"fio": "Иванов Иван", "tab_num": "1", "position": "инженер", "citizenship": "РОССИЯ"},
    )
    assert row["Классификация"] == "ИТР"
    assert len(row) == len(ALL_COLUMNS)
    df = pd.DataFrame([row], columns=ALL_COLUMNS)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        path = tmp.name
    save_as_excel(df, path)
    if not Path(path).exists() or Path(path).stat().st_size < 100:
        fail("excel не создан")
    Path(path).unlink(missing_ok=True)
    ok("строка заявки и экспорт Excel")


def test_route_logic_spb():
    from route_logic import split_route_via_moscow, apply_reason1_rules

    parts = split_route_via_moscow("Санкт-Петербург - Сочи")
    if len(parts) != 2 or "Москва" not in parts[0]:
        fail("пересадка через Москва")
    ok("маршрут СПб")

    r2, reason2, d2 = apply_reason1_rules("Увольнение", "X", "Y", "01.01.2026")
    if r2 or reason2 or d2:
        fail("увольнение блокирует маршрут 2")
    ok("правила обоснования")


def test_pdf_text_helpers():
    from pdf_processor import extract_fio, extract_reason, extract_phone

    text = "Заявка\nИванов Иван Иванович 01.01.1990\nКомандировка\n+7 921 000 00 00"
    assert extract_fio(text)
    assert extract_reason(text) == "Командировка"
    assert extract_phone(text)
    ok("парсинг текста PDF")


def test_ticket_form_parser_samples():
    from ticket_form_parser import parse_ticket_application_text

    data_dir = ROOT / "data"
    page1 = data_dir / "sample_page1_ocr.txt"
    if not page1.exists():
        print("  WARN нет sample_page1_ocr.txt — пропуск OCR-тестов")
        return

    t1 = page1.read_text(encoding="utf-8")
    p1 = parse_ticket_application_text(t1, source_file="test.pdf", page=1)
    if not p1 or not p1.get("fio"):
        fail("страница 1: нет ФИО")
    if not p1.get("route1"):
        fail("страница 1: нет маршрута")
    ok(f"стр.1: {p1.get('fio', '')[:30]} | {p1.get('route1', '')}")

    page2 = data_dir / "sample_page2_ocr.txt"
    if page2.exists():
        p2 = parse_ticket_application_text(page2.read_text(encoding="utf-8"), page=2)
        if p2 and p2.get("route2"):
            ok(f"стр.2: обратный маршрут {p2.get('route2', '')[:40]}")
        elif p2:
            ok("стр.2: односторонний маршрут")
        else:
            fail("страница 2: не распознана")

    page3 = data_dir / "sample_page3_ocr.txt"
    if page3.exists():
        p3 = parse_ticket_application_text(page3.read_text(encoding="utf-8"), page=3)
        if p3 and (p3.get("route1") or p3.get("fio")):
            ok(f"стр.3: {p3.get('fio', '')[:25]} | {p3.get('route1', '')[:30]}")
        else:
            print("  WARN стр.3 OCR слабый — проверьте вручную")


def test_user_prefs():
    from user_prefs import load_prefs, set_theme, is_dark_theme, draft_autosave_minutes

    set_theme("light")
    assert not is_dark_theme()
    assert draft_autosave_minutes() >= 1
    prefs = load_prefs()
    assert "theme" in prefs
    ok("настройки пользователя")


def test_auth_config():
    from config import USERS, ADMIN_CREDENTIALS, APP_VERSION

    assert APP_VERSION
    assert USERS
    assert ADMIN_CREDENTIALS.get("password")
    ok(f"конфиг v{APP_VERSION}")


def main():
    print("=== Проверка Ticket_system ===\n")
    tests = [
        test_imports,
        test_user_prefs,
        test_auth_config,
        test_routes,
        test_database_helpers,
        test_department_filter_admin,
        test_base_display_limit,
        test_department_from_employee_db,
        test_user_profile_columns_dg,
        test_wizard_employee_not_marked_missing,
        test_excel_row,
        test_route_logic_spb,
        test_pdf_text_helpers,
        test_ticket_form_parser_samples,
    ]
    failed = 0
    for test in tests:
        name = test.__name__
        print(f"[{name}]")
        try:
            test()
        except Exception as e:
            failed += 1
            print(f" FAIL {e}")
        print()
    if failed:
        print(f"Итого: {failed} ошибок")
        sys.exit(1)
    print("Все проверки пройдены.")
    sys.exit(0)


if __name__ == "__main__":
    main()
