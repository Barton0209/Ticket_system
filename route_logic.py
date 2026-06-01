# route_logic.py
"""Правила маршрутов, обоснований и пересадок через Москву."""

from typing import Dict, List, Optional, Tuple

from config import REASONS

REASON_BLOCK_ROUTE2 = frozenset({"Увольнение", "Перевод в др. ОП"})
MOSCOW_HUB = "Москва"
SPB_MARKERS = (
    "санкт-петербург",
    "санкт петербург",
    "петербург",
    "спб",
    "saint-petersburg",
)


def suggest_reason2(reason1: str) -> str:
    if reason1 == "Командировка":
        return "Командировка"
    if reason1 == "Межвахтовый отдых":
        return "Возвращение из отпуска"
    return ""


def apply_reason1_rules(reason1: str, route2: str, reason2: str, date2: str) -> Tuple[str, str, str]:
    """Если маршрут 2 не нужен — очищаем поля; иначе подставляем обоснование 2."""
    if reason1 in REASON_BLOCK_ROUTE2:
        return "", "", ""
    if not reason2:
        reason2 = suggest_reason2(reason1)
    return route2, reason2, date2


def _normalize_route_text(route: str) -> str:
    return " ".join(str(route or "").lower().replace("ё", "е").split())


def route_contains_spb(route: str) -> bool:
    text = _normalize_route_text(route)
    return any(marker in text for marker in SPB_MARKERS)


def needs_moscow_transfer(route: str) -> bool:
    if not route or " - " not in route:
        return False
    return route_contains_spb(route)


def split_route_via_moscow(route: str) -> List[str]:
    """Город1 - Город2 (со СПб) -> [Город1 - Москва, Москва - Город2]."""
    if not route or " - " not in route:
        return [route] if route else []
    city_from, city_to = [p.strip() for p in route.split(" - ", 1)]
    if not needs_moscow_transfer(route):
        return [route]
    return [f"{city_from} - {MOSCOW_HUB}", f"{MOSCOW_HUB} - {city_to}"]


def expand_route_segments(route: str, date: str, reason: str) -> List[Dict]:
    """Развернуть маршрут в одну или две строки заявки."""
    if not route and not date:
        return []
    routes = split_route_via_moscow(route) if route else [""]
    note = ""
    if len(routes) > 1:
        note = "сложный маршрут (пересадка через Москва)"
    segments = []
    for idx, seg_route in enumerate(routes):
        seg_note = note if idx == 0 else ""
        segments.append({
            "route": seg_route,
            "date": date,
            "reason": reason,
            "note": seg_note,
        })
    return segments


def expand_wizard_result(result: Dict) -> List[Dict]:
    """
    Из результата мастера PDF — список сегментов {route, date, reason, note}.
  Учитывает маршрут 1/2 и обоснование 1/2.
    """
    reason1 = result.get("reason1") or result.get("reason", "")
    route1 = result.get("route1") or result.get("route", "")
    date1 = result.get("date1") or result.get("date", "")
    route2 = result.get("route2", "")
    date2 = result.get("date2", "")
    reason2 = result.get("reason2", "")

    route2, reason2, date2 = apply_reason1_rules(reason1, route2, reason2, date2)

    all_segments: List[Dict] = []
    for route, date, reason in (
        (route1, date1, reason1),
        (route2, date2, reason2),
    ):
        all_segments.extend(expand_route_segments(route, date, reason))
    return all_segments


def get_reason_list(template_reasons: Optional[List[str]] = None) -> List[str]:
    if template_reasons:
        return template_reasons
    return list(REASONS)
