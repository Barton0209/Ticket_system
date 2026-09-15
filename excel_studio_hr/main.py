"""
Excel Studio HR v3.2.1
Автоматизированная станция обработки кадровой отчётности
Профиль развёртывания: без прав администратора

Точка входа приложения.
"""

import sys
import os

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.app import Application


def main():
    """Запуск приложения."""
    app = Application()
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
