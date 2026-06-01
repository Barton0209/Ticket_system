"""Общие константы маршрутов (обновляются при смене шаблона)."""

from routes import build_reverse_map, load_routes

ROUTES = load_routes()
REVERSE_ROUTES = build_reverse_map(ROUTES)
