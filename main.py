# main.py
"""
Система обработки заявок на билеты — автономное desktop-приложение.
Точка входа; UI в пакете ui/.
"""

from ui.main_window import MainApp

if __name__ == "__main__":
    MainApp().run()
