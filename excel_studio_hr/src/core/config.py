"""
Config - конфигурация и настройки приложения

Настройки хранятся в settings.json (Приложение Б ТЗ).
Все настройки - per-user, без прав администратора.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import AppPaths


# Схема настроек по умолчанию (Приложение Б ТЗ v3.2.1)
DEFAULT_SETTINGS: Dict[str, Any] = {
    "schema_version": 3,
    "language": "ru",
    
    # ИИ-ассистент (М21)
    "ai_provider": "heuristic",  # heuristic | groq | gemini | local
    "ai_send_data_mode": "digest_only",  # none | digest_only | full
    
    # API ключи (шифруются DPAPI при сохранении)
    "groq_key_dpapi": "",
    "groq_model": "llama-3.3-70b-versatile",
    "gemini_key_dpapi": "",
    "gemini_model": "gemini-1.5-flash",
    "local_model": "Qwen/Qwen2.5-0.5B-Instruct",
    
    # Автосохранение (М14)
    "autosave": True,
    "autosave_min": 5,
    "autosave_keep": 10,
    
    # VBA исполнение (М18)
    "use_com_fallback": True,
    
    # Просмотр (М2)
    "page_size": 2000,
    
    # Безопасность (М36)
    "idle_lock_min": 10,
    "user_login_enabled": True,
    
    # Квитанции (М32)
    "receipts_mode": "draft",  # draft | send
    
    # Тема интерфейса
    "theme": "light",  # light | dark
    
    # Хранилище (М28)
    "warehouse_months": 36,
    
    # Журналы и бэкапы (М14, М40)
    "log_rotate_days": 30,
    "backup_rotate_days": 30,
    
    # Обновления (М39)
    "update_check": False,
    "update_source": "",
    "update_check_days": 7,
    
    # Буфер и ПДн (М34, М20)
    "buffer_pdn_mask_default": {
        "Оператор": True,
        "Аналитик": False,
        "Администратор": False
    },
    
    # Headless job (М29, FR-3920)
    "headless_duplicate_mode": "skip",  # skip | run
    
    # Лицензионный реестр (Приложение В)
    "_license_registered": False,
}


class Config:
    """Конфигурация приложения."""
    
    def __init__(self, paths: AppPaths):
        """Инициализация конфигурации.
        
        Args:
            paths: AppPaths для доступа к файлам настроек.
        """
        self.paths = paths
        self._settings: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Загрузка настроек из файла."""
        settings_file = self.paths.settings_file
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                
                # Объединяем с дефолтными (новые поля добавляются)
                self._settings = {**DEFAULT_SETTINGS, **loaded}
                
                # Проверяем версию схемы и выполняем миграции при необходимости
                self._migrate_settings()
                
            except (json.JSONDecodeError, IOError) as e:
                # При ошибке загрузки используем дефолтные настройки
                self._settings = DEFAULT_SETTINGS.copy()
                self._save()
        else:
            # Файл не существует - создаём с настройками по умолчанию
            self._settings = DEFAULT_SETTINGS.copy()
            self._save()
    
    def _migrate_settings(self):
        """Миграция схемы настроек между версиями."""
        current_version = self._settings.get('schema_version', 1)
        
        # Пример миграции: v1 → v2 → v3
        if current_version < 2:
            # Добавляем новые поля v2
            self._settings.setdefault('headless_duplicate_mode', 'skip')
            self._settings['schema_version'] = 2
        
        if current_version < 3:
            # Добавляем новые поля v3
            self._settings.setdefault('user_login_enabled', True)
            self._settings.setdefault('_license_registered', False)
            self._settings['schema_version'] = 3
        
        # Сохраняем после миграции
        if self._settings.get('schema_version', 1) != current_version:
            self._save()
    
    def _save(self):
        """Сохранение настроек в файл."""
        settings_file = self.paths.settings_file
        
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            # Логгируем ошибку, но не падаем - настройки не критичны
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения настройки.
        
        Args:
            key: Ключ настройки.
            default: Значение по умолчанию (если None - берётся из DEFAULT_SETTINGS).
        
        Returns:
            Значение настройки.
        """
        if default is None:
            return self._settings.get(key, DEFAULT_SETTINGS.get(key))
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Установка значения настройки.
        
        Args:
            key: Ключ настройки.
            value: Новое значение.
        """
        self._settings[key] = value
        self._save()
    
    def get_all(self) -> Dict[str, Any]:
        """Получение всех настроек.
        
        Returns:
            Словарь всех настроек.
        """
        return self._settings.copy()
    
    def update(self, updates: Dict[str, Any]):
        """Обновление нескольких настроек.
        
        Args:
            updates: Словарь обновлений.
        """
        self._settings.update(updates)
        self._save()
    
    def reset_to_defaults(self):
        """Сброс настроек к значениям по умолчанию."""
        self._settings = DEFAULT_SETTINGS.copy()
        self._save()
    
    @property
    def schema_version(self) -> int:
        """Версия схемы настроек."""
        return self._settings.get('schema_version', 1)
