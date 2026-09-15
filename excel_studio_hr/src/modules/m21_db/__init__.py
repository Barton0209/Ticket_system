"""
М21: Работа с базами данных (SQLite, PostgreSQL)
Чтение/запись в БД, выполнение запросов, экспорт результатов.
"""
from typing import List, Dict, Any, Optional, Tuple
import sqlite3
import os

class DBModule:
    """Работа с локальными базами данных SQLite."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self) -> bool:
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except Exception:
            return False
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        if not self.conn:
            return []
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        if not self.conn:
            return 0
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount
    
    def create_table(self, table_name: str, columns: Dict[str, str]) -> bool:
        cols = ', '.join([f"{name} {dtype}" for name, dtype in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols})"
        return self.execute_update(query) >= 0
    
    def insert_row(self, table_name: str, data: Dict[str, Any]) -> bool:
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['?' for _ in values])
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        return self.execute_update(query, tuple(values)) > 0
    
    def export_to_df(self, query: str) -> List[Dict[str, Any]]:
        return self.execute_query(query)
    
    def import_from_df(self, table_name: str, rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> int:
        if not rows:
            return 0
        if columns is None:
            columns = list(rows[0].keys())
        count = 0
        for row in rows:
            data = {col: row.get(col) for col in columns}
            if self.insert_row(table_name, data):
                count += 1
        return count
