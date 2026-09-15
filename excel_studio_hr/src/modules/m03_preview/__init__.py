"""
М3: Предварительный просмотр данных
FR-0301: Быстрый просмотр первых N строк
FR-0302: Статистика по столбцам (типы, пустые, уникальные)
FR-0303: Гистограммы распределения
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class ColumnStats:
    """Статистика по столбцу"""
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None


@dataclass
class PreviewData:
    """Данные предпросмотра"""
    rows: List[Dict[str, Any]]
    total_rows: int
    columns: List[str]
    column_stats: List[ColumnStats]
    sample_size: int = 100


class PreviewModule:
    """Модуль предварительного просмотра"""
    
    def __init__(self):
        self.max_preview_rows = 100
    
    def get_preview(self, df: pd.DataFrame, n_rows: int = 100) -> PreviewData:
        """
        Получить превью данных
        
        Args:
            df: DataFrame с данными
            n_rows: количество строк для превью
            
        Returns:
            PreviewData с первыми строками и статистикой
        """
        # Ограничиваем количество строк
        preview_df = df.head(n_rows)
        
        # Получаем статистику по столбцам
        stats = []
        for col in df.columns:
            col_stats = self._analyze_column(df[col])
            stats.append(col_stats)
        
        # Преобразуем в список словарей
        rows = preview_df.to_dict(orient='records')
        
        return PreviewData(
            rows=rows,
            total_rows=len(df),
            columns=list(df.columns),
            column_stats=stats,
            sample_size=min(n_rows, len(df))
        )
    
    def _analyze_column(self, series: pd.Series) -> ColumnStats:
        """Анализ одного столбца"""
        is_numeric = pd.api.types.is_numeric_dtype(series)
        
        stats = ColumnStats(
            name=series.name,
            dtype=str(series.dtype),
            non_null_count=int(series.notna().sum()),
            null_count=int(series.isna().sum()),
            unique_count=int(series.nunique())
        )
        
        if is_numeric:
            stats.min_val = float(series.min()) if not series.empty else None
            stats.max_val = float(series.max()) if not series.empty else None
            stats.mean_val = float(series.mean()) if not series.empty else None
            stats.std_val = float(series.std()) if not series.empty and len(series) > 1 else None
        
        return stats
    
    def get_distribution(self, df: pd.DataFrame, column: str, bins: int = 10) -> Dict[str, Any]:
        """
        Получить распределение значений столбца
        
        Args:
            df: DataFrame
            column: имя столбца
            bins: количество бинов для гистограммы
            
        Returns:
            dict с данными для гистограммы
        """
        if column not in df.columns:
            raise ValueError(f"Столбец {column} не найден")
        
        series = df[column].dropna()
        
        if pd.api.types.is_numeric_dtype(series):
            # Числовое распределение
            counts, bin_edges = np.histogram(series, bins=bins)
            return {
                'type': 'numeric',
                'bins': bin_edges.tolist(),
                'counts': counts.tolist(),
                'min': float(series.min()),
                'max': float(series.max())
            }
        else:
            # Категориальное распределение
            value_counts = series.value_counts().head(20)
            return {
                'type': 'categorical',
                'values': value_counts.index.tolist(),
                'counts': value_counts.values.tolist()
            }
