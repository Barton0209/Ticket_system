"""
М8: Сводные таблицы
FR-0801: Создание сводных таблиц
FR-0802: Группировка данных
FR-0803: Агрегация по различным функциям
FR-0804: Фильтрация сводных данных
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class PivotField:
    """Поле сводной таблицы"""
    name: str
    role: str  # rows, columns, values, filters
    aggregation: Optional[str] = None  # SUM, COUNT, AVG, etc.
    group_by: Optional[str] = None  # day, month, year, custom
    sort_order: Optional[str] = None  # asc, desc
    filter_values: Optional[List[Any]] = None


@dataclass
class PivotConfig:
    """Конфигурация сводной таблицы"""
    rows: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    filters: Dict[str, List[Any]] = field(default_factory=dict)
    aggregations: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rows': self.rows,
            'columns': self.columns,
            'values': self.values,
            'filters': self.filters,
            'aggregations': self.aggregations
        }


class PivotModule:
    """Модуль сводных таблиц"""
    
    def __init__(self):
        self.aggregation_functions = {
            'SUM': 'sum',
            'COUNT': 'count',
            'AVG': 'mean',
            'MIN': 'min',
            'MAX': 'max',
            'FIRST': 'first',
            'LAST': 'last',
            'STD': 'std',
            'VAR': 'var',
            'MEDIAN': 'median'
        }
    
    def create_pivot(self, df: pd.DataFrame, config: PivotConfig) -> pd.DataFrame:
        """
        Создание сводной таблицы
        
        Args:
            df: исходный DataFrame
            config: конфигурация сводной
            
        Returns:
            DataFrame с сводной таблицей
        """
        # Применение фильтров
        filtered_df = self._apply_filters(df, config.filters)
        
        if not config.values:
            # Если нет значений, просто группируем
            if config.rows and config.columns:
                result = filtered_df.groupby(config.rows + config.columns).size().unstack(fill_value=0)
            elif config.rows:
                result = filtered_df.groupby(config.rows).size().to_frame('count')
            else:
                return filtered_df
        else:
            # Подготовка агрегаций
            agg_dict = {}
            for val_col in config.values:
                agg_func = config.aggregations.get(val_col, 'SUM')
                agg_dict[val_col] = self.aggregation_functions.get(agg_func.upper(), 'sum')
            
            # Создание сводной
            if config.rows and config.columns:
                result = pd.pivot_table(
                    filtered_df,
                    index=config.rows,
                    columns=config.columns,
                    values=config.values,
                    aggfunc=[self.aggregation_functions.get(agg_dict.get(col, 'sum'), 'sum') 
                            for col in config.values],
                    fill_value=0
                )
            elif config.rows:
                result = filtered_df.groupby(config.rows)[config.values].agg(agg_dict)
            elif config.columns:
                result = filtered_df.groupby(config.columns)[config.values].agg(agg_dict).T
            else:
                result = filtered_df[config.values].agg(agg_dict).to_frame().T
        
        # Сортировка
        if config.rows:
            sort_col = config.rows[0]
            if sort_col in result.index.names:
                ascending = True
                # Проверка настройки сортировки
                result = result.sort_index(ascending=ascending)
        
        return result
    
    def _apply_filters(self, df: pd.DataFrame, 
                      filters: Dict[str, List[Any]]) -> pd.DataFrame:
        """Применение фильтров к данным"""
        result = df.copy()
        
        for column, values in filters.items():
            if column in result.columns:
                result = result[result[column].isin(values)]
        
        return result
    
    def group_by_date(self, df: pd.DataFrame, column: str, 
                     level: str = 'month') -> pd.DataFrame:
        """
        Группировка по дате
        
        Args:
            df: DataFrame
            column: столбец с датой
            level: уровень группировки (day, week, month, quarter, year)
            
        Returns:
            DataFrame с группировкой
        """
        result = df.copy()
        
        if column not in result.columns:
            raise ValueError(f"Столбец {column} не найден")
        
        # Преобразование в datetime
        result[column] = pd.to_datetime(result[column])
        
        # Группировка по уровню
        if level == 'year':
            result['_group'] = result[column].dt.year
        elif level == 'quarter':
            result['_group'] = result[column].dt.to_period('Q')
        elif level == 'month':
            result['_group'] = result[column].dt.to_period('M')
        elif level == 'week':
            result['_group'] = result[column].dt.to_period('W')
        elif level == 'day':
            result['_group'] = result[column].dt.date
        else:
            result['_group'] = result[column]
        
        return result
    
    def add_calculated_field(self, pivot_df: pd.DataFrame, name: str,
                            expression: str) -> pd.DataFrame:
        """
        Добавление вычисляемого поля в сводную
        
        Args:
            pivot_df: сводная таблица
            name: имя нового поля
            expression: выражение для вычисления
            
        Returns:
            DataFrame с новым полем
        """
        result = pivot_df.copy()
        
        # Простая поддержка выражений
        try:
            result[name] = eval(expression, {}, result.to_dict())
        except Exception as e:
            print(f"Ошибка вычисления поля {name}: {e}")
            result[name] = None
        
        return result
    
    def drill_down(self, df: pd.DataFrame, config: PivotConfig,
                  row_key: Any) -> pd.DataFrame:
        """
        Детализация (drill-down) сводной таблицы
        
        Args:
            df: исходные данные
            config: конфигурация сводной
            row_key: ключ строки для детализации
            
        Returns:
            DataFrame с детальными данными
        """
        filtered_df = self._apply_filters(df, config.filters)
        
        # Фильтрация по ключу строки
        if config.rows:
            if len(config.rows) == 1:
                filtered_df = filtered_df[filtered_df[config.rows[0]] == row_key]
            else:
                for i, col in enumerate(config.rows):
                    if isinstance(row_key, (list, tuple)) and i < len(row_key):
                        filtered_df = filtered_df[filtered_df[col] == row_key[i]]
        
        # Убираем служебные столбцы
        cols_to_drop = [c for c in filtered_df.columns if c.startswith('_')]
        filtered_df = filtered_df.drop(columns=cols_to_drop, errors='ignore')
        
        return filtered_df
    
    def get_pivot_summary(self, pivot_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Получение сводной информации о сводной таблице
        
        Returns:
            dict со статистикой
        """
        return {
            'total_rows': len(pivot_df),
            'total_columns': len(pivot_df.columns),
            'row_headers': list(pivot_df.index.names) if pivot_df.index.names else None,
            'column_headers': list(pivot_df.columns.names) if hasattr(pivot_df.columns, 'names') else None,
            'has_multiindex_rows': isinstance(pivot_df.index, pd.MultiIndex),
            'has_multiindex_cols': isinstance(pivot_df.columns, pd.MultiIndex),
            'null_count': int(pivot_df.isnull().sum().sum()),
            'total_sum': float(pivot_df.select_dtypes(include='number').sum().sum()) if any(pivot_df.dtypes.apply(pd.api.types.is_numeric_dtype)) else None
        }


__all__ = ['PivotField', 'PivotConfig', 'PivotModule']
