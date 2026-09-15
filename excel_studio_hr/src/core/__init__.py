"""
Excel Studio HR - Ядро приложения

Модули ядра:
- app: главный класс приложения
- config: конфигурация и настройки
- paths: управление путями (per-user, без прав админа)
"""

from .app import Application
from .config import Config
from .paths import AppPaths

__all__ = ['Application', 'Config', 'AppPaths']
