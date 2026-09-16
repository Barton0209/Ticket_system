"""
М16: Импорт данных
FR-1601: Импорт из различных источников
FR-1602: Конвертация форматов
"""

from typing import Dict, Any, Optional
import pandas as pd
import json
from pathlib import Path


class ImportModule:
    """Модуль импорта данных"""
    
    def from_json(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Импорт из JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    
    def from_xml(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Импорт из XML"""
        return pd.read_xml(filepath, **kwargs)
    
    def from_sqlite(self, db_path: str, table: str, **kwargs) -> pd.DataFrame:
        """Импорт из SQLite"""
        import sqlite3
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_table(table, conn, **kwargs)
        conn.close()
        return df
    
    def from_clipboard(self, **kwargs) -> pd.DataFrame:
        """Импорт из буфера обмена"""
        return pd.read_clipboard(**kwargs)
    
    def from_dict(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Импорт из словаря"""
        return pd.DataFrame.from_dict(data)


__all__ = ['ImportModule']
