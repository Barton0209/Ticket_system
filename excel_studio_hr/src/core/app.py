"""
Application - главный класс приложения

Инициализация, запуск GUI, обработка жизненного цикла.
"""

import sys
import logging
from typing import Optional

from .paths import AppPaths
from .config import Config


class Application:
    """Главный класс приложения."""
    
    def __init__(self):
        """Инициализация приложения."""
        # Инициализация путей (per-user, без прав админа)
        self.paths = AppPaths()
        
        # Инициализация конфигурации
        self.config = Config(self.paths)
        
        # Настройка логгирования
        self._setup_logging()
        
        # GUI приложение (создаётся при запуске)
        self._app_gui = None
        
        # Главное окно
        self._main_window = None
        
        # Логгер
        self.logger = logging.getLogger('ExcelStudioHR')
    
    def _setup_logging(self):
        """Настройка логгирования (М14, М40)."""
        log_file = self.paths.log_file
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
        except (IOError, OSError):
            # Если не удалось создать файл - логируем в stderr
            file_handler = logging.StreamHandler()
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.WARNING)
        
        # Console handler (только warnings+)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.WARNING)
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def run(self) -> int:
        """Запуск приложения.
        
        Returns:
            Код возврата (0 - успех).
        """
        self.logger.info(f'Запуск Excel Studio HR v3.2.1')
        self.logger.info(f'Пути: {self.paths}')
        self.logger.info(f'Конфигурация: schema_version={self.config.schema_version}')
        
        try:
            # Импорт PySide6 (ленивая загрузка)
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import Qt
            
            # Настройки High DPI
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
            
            # Создаём QApplication
            self._app_gui = QApplication(sys.argv)
            self._app_gui.setApplicationName('Excel Studio HR')
            self._app_gui.setOrganizationName('VelesStroyMontazh')
            self._app_gui.setApplicationVersion('3.2.1')
            
            # Создаём главное окно
            from ..ui.main_window import MainWindow
            self._main_window = MainWindow(self)
            self._main_window.show()
            
            # Запуск цикла событий
            return self._app_gui.exec()
            
        except ImportError as e:
            # PySide6 не установлен
            self.logger.critical(f'PySide6 не найден: {e}')
            print(f'Ошибка: PySide6 не установлен.\n'
                  f'Установите: pip install PySide6>=6.6.0')
            return 1
            
        except Exception as e:
            # Критическая ошибка запуска (М40 - телеметрия)
            self.logger.critical(f'Критическая ошибка запуска: {e}', exc_info=True)
            
            # Пишем в краш-лог (М40)
            try:
                crash_log = self.paths.crash_log_file
                with open(crash_log, 'w', encoding='utf-8') as f:
                    f.write(f'Crash at startup:\n{e}\n')
            except:
                pass
            
            print(f'Критическая ошибка: {e}')
            return 1
    
    def quit(self):
        """Завершение приложения."""
        self.logger.info('Завершение работы')
        
        if self._main_window:
            self._main_window.close()
        
        if self._app_gui:
            self._app_gui.quit()
    
    @property
    def main_window(self) -> Optional['MainWindow']:
        """Главное окно приложения."""
        return self._main_window
