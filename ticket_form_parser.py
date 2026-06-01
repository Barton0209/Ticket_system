# ticket_form_parser.py
"""
Разбор стандартной бумажной «Заявки на приобретение билетов» (скан PDF).

Поля:
  - Ф.И.О. заявителя
  - Пункт отправления / назначения (2 строки: туда и обратно)
  - Дата вылета (2 строки)
  - Вид транспорта (2 строки)
  - Примечание (2 строки)
  - Обоснование (кадровый блок)
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from config import REASONS
from excel_handler import format_date_ddmmyyyy

# OCR-подмены
_OCR_FIXES = (
    (r"\bABHA\b", "АВИА"),
    (r"\bABia\b", "АВИА"),
    (r"\bЖД\b", "ЖД"),
    (r"Савкт-Петербург", "Санкт-Петербург"),
    (r"Савкт-Петербуг", "Санкт-Петербург"),
    (r"Санкт-Петербуг", "Санкт-Петербург"),
    (r"Шымкент", "Шымкент"),
    (r"Фергана", "Фергана"),
    (r"Бншкек", "Бишкек"),
    (r"К-\s*820", "ЖД"),
)

_REASON_KEYWORDS = [
    ("междувахтовый отдых", "Межвахтовый отдых"),
    ("междувахтовый садысх", "Межвахтовый отдых"),
    ("междувахтовый", "Межвахтовый отдых"),
    ("межвахта", "Межвахта"),
    ("командировка", "Командировка"),
    ("трудоустройство", "Устройство на работу"),
    ("трудоустрой", "Устройство на работу"),
    ("увольнение", "Увольнение"),
    ("больнич", "Больничный"),
    ("перевод", "Перевод в др. ОП"),
    ("ежегодный отпуск", "Ежегодный отпуск"),
    ("отпуск", "Ежегодный отпуск"),
    ("разъездной", "Разъездной характер работы"),
    ("возвращение из отпуска", "Возвращение из отпуска"),
]

_DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
_DATE_COMPACT_RE = re.compile(r"\b(\d{2})(\d{2})(\d{4})\b")


def _parse_date_token(token: str) -> str:
    token = token.strip()
    m = _DATE_RE.search(token)
    if m:
        return _norm_date(m)
    m8 = _DATE_COMPACT_RE.fullmatch(token)
    if m8:
        d, mo, y = m8.groups()
        return f"{d}.{mo}.{y}"
    return ""
_FIO_DATE_RE = re.compile(
    r"([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,4})\s+(\d{1,2}[./]\d{1,2}[./]\d{2,4})"
)
_ROUTE_ROW_RE = re.compile(
    r"^([А-ЯЁA-Za-z][А-ЯЁA-Za-z\-\s]{1,40}?)\s+"
    r"([А-ЯЁA-Za-z][А-ЯЁA-Za-z\-\s]{1,40}?)\s+"
    r"(\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{8})\s+"
    r"([А-ЯЁA-Za-z]{2,6})\s*"
    r"(.*)$",
    re.MULTILINE,
)


def _normalize_text(text: str) -> str:
    t = text.replace("\r", "\n")
    for pat, repl in _OCR_FIXES:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    return t


def _norm_date(m: re.Match) -> str:
    d, mo, y = m.groups()
    if len(y) == 2:
        y = "20" + y
    return f"{int(d):02d}.{int(mo):02d}.{y}"


def _clean_city(name: str) -> str:
    s = re.sub(r"[,;|\[\]°]+", "", name).strip()
    s = re.sub(r"\s+", " ", s)
    return s.title() if s.isupper() or "-" in s else s.strip()


def _clean_transport(val: str) -> str:
    v = re.sub(r"\s+", "", val.strip().upper())
    if "АВИ" in v or v in ("ABHA", "AVIA"):
        return "АВИА"
    if "ЖД" in v or "820" in v or v.startswith("К-"):
        return "ЖД"
    return val.strip() or "АВИА"


def extract_fio_from_form(text: str) -> str:
    text_n = _normalize_text(text)
    lines = [ln.strip() for ln in text_n.split("\n") if ln.strip()]

    exclude = (
        "заявка", "монтаж", "велесстрой", "согласие", "руководитель",
        "специалист", "кадров", "телефон", "подпись", "заполнению",
    )

    candidates: List[str] = []

    for line in lines:
        ll = line.lower()
        if any(x in ll for x in exclude):
            continue
        if "пункт отправления" in ll or "маршрут" in ll and "перемещ" in ll:
            continue

        m = _FIO_DATE_RE.search(line)
        if m:
            fio = re.sub(r"\s+", " ", m.group(1)).strip()
            parts = fio.split()
            if len(parts) >= 2 and len(parts) <= 5:
                candidates.append(fio)

        m2 = re.search(
            r"([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,4})\s+\d{2}[./]\d{2}[./]\d{4}",
            line,
        )
        if m2:
            candidates.append(m2.group(1).strip())

        if "подмостей" in ll or "лесов" in ll:
            m3 = re.search(
                r"([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,4})",
                line,
            )
            if m3:
                candidates.append(m3.group(1).strip())

    for c in candidates:
        if len(c.split()) >= 3:
            return c
    return candidates[0] if candidates else ""


def _parse_route_rows(text: str) -> List[Dict[str, str]]:
    """Строки таблицы маршрута после заголовка."""
    rows: List[Dict[str, str]] = []
    text_n = _normalize_text(text)
    lines = [ln.strip() for ln in text_n.split("\n")]

    start = 0
    for i, line in enumerate(lines):
        ll = line.lower()
        if "пункт отправления" in ll and "назначения" in ll:
            start = i + 1
            break
        if "пункт отправления" in ll:
            start = i + 1

    for line in lines[start : start + 6]:
        line = re.sub(r"[\[\]|]+", " ", line)
        line = line.replace("—", " ").replace("–", "-")
        line = re.sub(r"\s+", " ", line).strip()
        if not line or len(line) < 8:
            continue
        ll = line.lower()
        if any(
            x in ll
            for x in (
                "согласие",
                "заявителя",
                "руководитель",
                "кадров",
                "сокращен",
                "заполнению",
                "примечание",
                "транспорт",
                "назначения",
                "отправления",
            )
        ):
            if "пункт" not in ll:
                continue

        m = _ROUTE_ROW_RE.match(line)
        if not m:
            # «Город1 Город2 21.04.2026 АВИА —»
            parts = line.split()
            dates = [
                i
                for i, p in enumerate(parts)
                if _DATE_RE.fullmatch(p) or _DATE_COMPACT_RE.fullmatch(p)
            ]
            if len(dates) >= 1 and len(parts) >= dates[0] + 2:
                di = dates[0]
                from_c = _clean_city(" ".join(parts[: max(1, di - 1)]))
                if di >= 2:
                    to_c = _clean_city(parts[di - 1])
                else:
                    to_c = ""
                date_s = _parse_date_token(parts[di])
                transport_raw = parts[di + 1] if di + 1 < len(parts) else ""
                note_start = di + 2
                if note_start < len(parts) and re.match(r"^\d{2,4}$", parts[note_start]):
                    transport_raw = f"{transport_raw} {parts[note_start]}"
                    note_start = di + 3
                transport = _clean_transport(transport_raw)
                note = " ".join(parts[note_start:]) if note_start < len(parts) else ""
                if from_c and to_c and date_s:
                    rows.append(
                        {
                            "from": from_c,
                            "to": to_c,
                            "date": date_s,
                            "transport": transport,
                            "note": note.strip("—- "),
                        }
                    )
            continue

        from_c = _clean_city(m.group(1))
        to_c = _clean_city(m.group(2))
        date_s = _parse_date_token(m.group(3))
        transport = _clean_transport(m.group(4))
        note = m.group(5).strip("—- []")
        if from_c and to_c and date_s:
            rows.append(
                {
                    "from": from_c,
                    "to": to_c,
                    "date": date_s,
                    "transport": transport,
                    "note": note,
                }
            )

    return rows[:2]


def extract_reason_from_form(text: str) -> str:
    text_l = _normalize_text(text).lower()

    hr_start = text_l.find("кадровый документ")
    if hr_start < 0:
        hr_start = text_l.find("основание для приобретения")
    hr_block = text_l[hr_start : hr_start + 400] if hr_start >= 0 else text_l

    for kw, canonical in _REASON_KEYWORDS:
        if kw in hr_block:
            if canonical in REASONS:
                return canonical
            return canonical

    for kw, canonical in _REASON_KEYWORDS:
        if kw in text_l:
            if canonical in REASONS:
                return canonical
            return canonical
    return ""


def _rows_to_routes(rows: List[Dict[str, str]]) -> Tuple[str, str, str, str]:
    r1 = rows[0] if rows else {}
    r2 = rows[1] if len(rows) > 1 else {}
    route1 = f"{r1.get('from', '')} - {r1.get('to', '')}".strip(" -") if r1 else ""
    route2 = f"{r2.get('from', '')} - {r2.get('to', '')}".strip(" -") if r2 else ""
    return route1, route2, r1.get("date", ""), r2.get("date", "")


def parse_ticket_application_text(text: str, source_file: str = "", page: int = 1) -> Optional[Dict]:
    if not text or len(text.strip()) < 30:
        return None

    if "заявка" not in text.lower() and "приобретение билет" not in text.lower():
        if not extract_fio_from_form(text) and not _parse_route_rows(text):
            return None

    fio = extract_fio_from_form(text)
    rows = _parse_route_rows(text)
    reason = extract_reason_from_form(text)
    route1, route2, date1, date2 = _rows_to_routes(rows)

    if not fio and not route1:
        return None

    r1 = rows[0] if rows else {}
    r2 = rows[1] if len(rows) > 1 else {}

    item = {
        "source_file": source_file,
        "page": page,
        "fio": fio,
        "departure_from": [r1.get("from", ""), r2.get("from", "")],
        "destination_to": [r1.get("to", ""), r2.get("to", "")],
        "flight_date": [r1.get("date", ""), r2.get("date", "")],
        "transport": [r1.get("transport", "АВИА"), r2.get("transport", "")],
        "note": [r1.get("note", ""), r2.get("note", "")],
        "reason": reason,
        "reason1": reason,
        "reason2": reason if route2 else "",
        "phone": "",
        "route": route1,
        "route1": route1,
        "route2": route2,
        "date": date1,
        "date1": date1,
        "date2": date2,
        "direction": "туда",
        "transport1": r1.get("transport", "АВИА"),
        "transport2": r2.get("transport", ""),
        "note1": r1.get("note", ""),
        "note2": r2.get("note", ""),
    }
    return item


def parse_ticket_application_text_to_legacy_list(data: Dict) -> List[Dict]:
    """Совместимость: 1–2 записи (туда / обратно)."""
    if not data:
        return []
    out = [
        {
            "source_file": data.get("source_file", ""),
            "page": data.get("page", 1),
            "direction": "туда",
            "fio": data.get("fio", ""),
            "route": data.get("route1", ""),
            "route1": data.get("route1", ""),
            "date": data.get("date1", ""),
            "date1": data.get("date1", ""),
            "reason": data.get("reason1", ""),
            "reason1": data.get("reason1", ""),
            "transport": data.get("transport1", "АВИА"),
            "note": data.get("note1", ""),
            "phone": data.get("phone", ""),
        }
    ]
    if data.get("route2") and data.get("date2"):
        out.append(
            {
                "source_file": data.get("source_file", ""),
                "page": data.get("page", 1),
                "direction": "обратно",
                "fio": data.get("fio", ""),
                "route": data.get("route2", ""),
                "route2": data.get("route2", ""),
                "date": data.get("date2", ""),
                "date2": data.get("date2", ""),
                "reason": data.get("reason2", "") or data.get("reason1", ""),
                "reason2": data.get("reason2", ""),
                "transport": data.get("transport2", "АВИА"),
                "note": data.get("note2", ""),
                "phone": data.get("phone", ""),
            }
        )
    return out
