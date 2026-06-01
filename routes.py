# routes.py
"""Справочник маршрутов (редактируется в data/routes.json)."""

import json
from pathlib import Path
from typing import Dict, List

from config import DATA_DIR

ROUTES_FILE = DATA_DIR / "routes.json"

DEFAULT_ROUTES = [
    "Абакан - Алеппо", "Абакан - Алматы", "Абакан - Астана", "Абакан - Ашхабад",
    "Абакан - Белград", "Абакан - Бишкек", "Абакан - Дамаск", "Абакан - Дели",
    "Абакан - Душанбе", "Абакан - Ереван", "Абакан - Загреб", "Абакан - Минск",
    "Абакан - Мумбаи", "Абакан - Подгорица", "Абакан - Самарканд", "Абакан - Сараево",
    "Абакан - Сплит", "Абакан - Ташкент", "Абакан - Тиват", "Абакан - Шымкент",
    "Алеппо - Абакан", "Алеппо - Анадырь", "Алеппо - Анапа", "Алеппо - Архангельск",
    "Алеппо - Астрахань", "Алеппо - Барнаул", "Алеппо - Белгород", "Алеппо - Благовещенск",
    "Алеппо - Братск", "Алеппо - Брянск", "Алеппо - Владивосток", "Алеппо - Владикавказ",
    "Алеппо - Волгоград", "Алеппо - Вологда", "Алеппо - Воронеж", "Алеппо - Горно-Алтайск",
    "Алеппо - Грозный", "Алеппо - Екатеринбург", "Алеппо - Жуковский", "Алеппо - Иваново",
    "Алеппо - Ижевск", "Алеппо - Иркутск", "Алеппо - Йошкар-Ола", "Алеппо - Казань",
    "Алеппо - Калининград", "Алеппо - Калуга", "Алеппо - Кемерово", "Алеппо - Киров",
    "Алеппо - Кострома", "Алеппо - Краснодар", "Алеппо - Красноярск", "Алеппо - Курган",
    "Алеппо - Курск", "Алеппо - Кызыл", "Алеппо - Липецк", "Алеппо - Магадан",
    "Алеппо - Магас", "Алеппо - Магнитогорск", "Алеппо - Махачкала", "Алеппо - Минеральные Воды",
    "Алеппо - Москва", "Алеппо - Мурманск", "Алеппо - Нальчик", "Алеппо - Нарьян-Мар",
    "Алеппо - Нижневартовск", "Алеппо - Нижнекамск", "Алеппо - Нижний Новгород",
    "Алеппо - Новокузнецк", "Алеппо - Новосибирск", "Алеппо - Норильск", "Алеппо - Омск",
    "Алеппо - Оренбург", "Алеппо - Орск", "Алеппо - Пенза", "Алеппо - Пермь",
    "Алеппо - Петрозаводск", "Алеппо - Петропавловск-Камчатский", "Алеппо - Псков",
    "Алеппо - Ростов-на-Дону", "Алеппо - Сабетта", "Алеппо - Салехард", "Алеппо - Самара",
    "Алеппо - Санкт-Петербург", "Алеппо - Саранск", "Алеппо - Саратов", "Алеппо - Симферополь",
    "Алеппо - Сочи", "Алеппо - Ставрополь", "Алеппо - Сургут", "Алеппо - Сыктывкар",
    "Алеппо - Тамбов", "Алеппо - Тобольск", "Алеппо - Томск", "Алеппо - Тюмень",
    "Алеппо - Улан-Удэ", "Алеппо - Ульяновск", "Алеппо - Уфа", "Алеппо - Хабаровск",
    "Алеппо - Ханты-Мансийск", "Алеппо - Чебоксары", "Алеппо - Челябинск", "Алеппо - Череповец",
    "Алеппо - Чита", "Алеппо - Элиста", "Алеппо - Южно-Сахалинск", "Алеппо - Якутск",
    "Алеппо - Ярославль",
    "Москва - Санкт-Петербург", "Санкт-Петербург - Москва",
    "Москва - Сочи", "Сочи - Москва",
    "Кингисепп - Москва", "Москва - Кингисепп",
]


def load_routes() -> List[str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ROUTES_FILE.exists():
        try:
            payload = json.loads(ROUTES_FILE.read_text(encoding="utf-8"))
            routes = payload.get("routes") if isinstance(payload, dict) else payload
            if isinstance(routes, list) and routes:
                cleaned = sorted({str(r).strip() for r in routes if str(r).strip()})
                return cleaned
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    save_routes(DEFAULT_ROUTES)
    return list(DEFAULT_ROUTES)


def save_routes(routes: List[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = sorted({str(r).strip() for r in routes if str(r).strip()})
    ROUTES_FILE.write_text(
        json.dumps({"routes": cleaned}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_route(route: str) -> List[str]:
    routes = load_routes()
    route = route.strip()
    if route and route not in routes:
        routes.append(route)
        save_routes(routes)
    return routes


def filter_route_suggestions(query: str, routes: List[str], limit: int = 30) -> List[str]:
    """Подсказки маршрутов при вводе (подстрока, приоритет — с начала)."""
    q = (query or "").strip().lower()
    if not q:
        return list(routes)[:limit]
    scored = []
    for route in routes:
        rl = route.lower()
        if q not in rl:
            continue
        scored.append((0 if rl.startswith(q) else 1, rl.find(q), route))
    scored.sort(key=lambda x: (x[0], x[1], x[2]))
    return [r[2] for r in scored[:limit]]


def build_reverse_map(routes: List[str]) -> Dict[str, str]:
    reverse: Dict[str, str] = {}
    route_set = set(routes)
    for route in routes:
        if " - " not in route:
            continue
        city_from, city_to = [p.strip() for p in route.split(" - ", 1)]
        rev = f"{city_to} - {city_from}"
        reverse[route] = rev if rev in route_set else rev
    return reverse
