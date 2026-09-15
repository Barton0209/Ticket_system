"""
AppPaths - управление путями приложения

Профиль развёртывания: без прав администратора (v3.2.1)
Все пути - только в профиле пользователя:
- %LOCALAPPDATA%\Programs\ExcelStudioHR\ - установка
- %LOCALAPPDATA%\ExcelStudioHR\ - данные
- HKCU - реестр (ассоциации, автозапуск)
"""

import os
import sys
from pathlib import Path
from typing import Optional


class AppPaths:
    """Управление путями приложения (per-user, без прав админа)."""
    
    # Имя приложения для путей
    APP_NAME = "ExcelStudioHR"
    
    def __init__(self):
        """Инициализация путей."""
        # Определяем базовые директории профиля пользователя
        if sys.platform == 'win32':
            # Windows: используем переменные окружения
            self.local_app_data = Path(os.environ.get('LOCALAPPDATA', ''))
            self.app_data = Path(os.environ.get('APPDATA', ''))
            self.user_profile = Path(os.environ.get('USERPROFILE', ''))
        else:
            # Linux/macOS: эмуляция для отладки
            home = Path.home()
            self.local_app_data = home / '.local' / 'share'
            self.app_data = home / '.config'
            self.user_profile = home
        
        # Базовые пути приложения
        self._install_dir: Optional[Path] = None
        self._data_dir: Optional[Path] = None
        
        # Вычисляем пути
        self._init_paths()
    
    def _init_paths(self):
        """Инициализация путей приложения."""
        # Каталог установки (где лежит exe/main.py)
        if getattr(sys, 'frozen', False):
            # Запуск из EXE (PyInstaller)
            self._install_dir = Path(sys.executable).parent
        else:
            # Запуск из исходников
            self._install_dir = Path(__file__).parent.parent.parent
        
        # Каталог данных (%LOCALAPPDATA%\ExcelStudioHR\)
        self._data_dir = self.local_app_data / self.APP_NAME
        
        # Создаём структуру данных при первом запуске
        self._ensure_data_dirs()
    
    def _ensure_data_dirs(self):
        """Создание структуры каталогов данных."""
        dirs = [
            self.data_dir,
            self.state_dir,
            self.warehouse_dir,
            self.backups_dir,
            self.logs_dir,
            self.updates_dir,
            self.rollback_dir,
            self.migrations_dir,
            self.sandbox_dir,
            self.legal_dir,
            self.plugins_dir,
        ]
        
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    @property
    def install_dir(self) -> Path:
        """Каталог установки приложения."""
        return self._install_dir
    
    @property
    def data_dir(self) -> Path:
        """Каталог данных приложения (%LOCALAPPDATA%\ExcelStudioHR\)."""
        return self._data_dir
    
    @property
    def state_dir(self) -> Path:
        """Состояние job и маркеры выполнения."""
        return self.data_dir / 'state'
    
    @property
    def warehouse_dir(self) -> Path:
        """SQLite хранилище истории."""
        return self.data_dir / 'warehouse'
    
    @property
    def backups_dir(self) -> Path:
        """Автосохранения."""
        return self.data_dir / 'backups'
    
    @property
    def logs_dir(self) -> Path:
        """Журналы."""
        return self.data_dir / 'logs'
    
    @property
    def updates_dir(self) -> Path:
        """Каталог обновлений."""
        return self.data_dir / 'updates'
    
    @property
    def rollback_dir(self) -> Path:
        """Точки отката обновлений."""
        return self.updates_dir / 'rollback'
    
    @property
    def migrations_dir(self) -> Path:
        """Миграции схемы данных."""
        return self.data_dir / 'migrations'
    
    @property
    def sandbox_dir(self) -> Path:
        """Песочница тестового контура (М41)."""
        return self.data_dir / 'sandbox'
    
    @property
    def legal_dir(self) -> Path:
        """Документы оснований ПДн."""
        return self.data_dir / 'legal'
    
    @property
    def plugins_dir(self) -> Path:
        """Сторонние плагины."""
        return self.data_dir / 'plugins'
    
    @property
    def settings_file(self) -> Path:
        """Файл настроек settings.json."""
        return self.data_dir / 'settings.json'
    
    @property
    def users_file(self) -> Path:
        """Файл пользователей users.json."""
        return self.data_dir / 'users.json'
    
    @property
    def references_file(self) -> Path:
        """Файл справочников references.json."""
        return self.data_dir / 'references.json'
    
    @property
    def warehouse_db(self) -> Path:
        """База данных хранилища warehouse.db."""
        return self.warehouse_dir / 'warehouse.db'
    
    @property
    def log_file(self) -> Path:
        """Основной файл журнала."""
        return self.logs_dir / 'app.log'
    
    @property
    def crash_log_file(self) -> Path:
        """Файл краш-логов (М40)."""
        return self.logs_dir / 'crash.log'
    
    def get_job_state_file(self, job_name: str, date_str: str) -> Path:
        """Файл состояния job (маркер выполнения)."""
        return self.state_dir / f'{job_name}_{date_str}.done'
    
    def get_ipc_pipe_name(self) -> str:
        """Имя IPC канала (per-user namespace)."""
        # Per-user named pipe для IPC моста CLI ↔ GUI (FR-2909)
        if sys.platform == 'win32':
            import getpass
            sid = getpass.getuser()
            return f'\\\\.\\pipe\\{self.APP_NAME}-{sid}'
        else:
            return f'/tmp/{self.APP_NAME}-ipc.sock'
    
    def __repr__(self) -> str:
        return (f'AppPaths(install={self.install_dir}, data={self.data_dir})')
