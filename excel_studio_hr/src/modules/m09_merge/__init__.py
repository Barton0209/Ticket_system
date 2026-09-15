"""
Модуль М9: Слияние и сведение данных

Действия:
- Стек файлов с выравниванием по заголовкам
- JOIN (left, inner, full)
- Агрегация (SUM, COUNT, AVG, MIN, MAX)
- Дедупликация свода
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
from collections import defaultdict

logger = logging.getLogger('ExcelStudioHR.modules.m09_merge')


@dataclass
class MergeResult:
    """Результат слияния."""
    data: List[List[Any]]
    headers: List[str]
    source_count: int
    total_rows: int
    duplicates_removed: int = 0
    warnings: List[str] = field(default_factory=list)


def merge_stack(files_data: List[Tuple[str, List[List[Any]], List[str]]]) -> MergeResult:
    """Слияние файлов в стек (вертикальное объединение).
    
    Args:
        files_data: Список кортежей (имя_файла, данные, заголовки).
        
    Returns:
        Результат слияния.
    """
    if not files_data:
        return MergeResult(data=[], headers=[], source_count=0, total_rows=0)
    
    # Используем заголовки первого файла как эталон
    _, _, reference_headers = files_data[0]
    all_data: List[List[Any]] = []
    warnings = []
    
    for file_name, data, headers in files_data:
        if not data:
            continue
        
        # Создаём маппинг столбцов: индекс в источнике → индекс в результате
        col_mapping = {}
        for i, h in enumerate(headers):
            if h in reference_headers:
                col_mapping[i] = reference_headers.index(h)
            else:
                warnings.append(f'Файл {file_name}: столбец "{h}" не найден в эталоне')
        
        # Добавляем строки
        for row in data[1:]:  # Пропускаем заголовок
            new_row = [None] * len(reference_headers)
            for src_idx, dst_idx in col_mapping.items():
                if src_idx < len(row):
                    new_row[dst_idx] = row[src_idx]
            all_data.append(new_row)
    
    # Добавляем заголовок в начало
    all_data.insert(0, reference_headers)
    
    return MergeResult(
        data=all_data,
        headers=reference_headers,
        source_count=len(files_data),
        total_rows=len(all_data) - 1,
        warnings=warnings
    )


def merge_join(
    left_data: List[List[Any]],
    right_data: List[List[Any]],
    left_key_col: int,
    right_key_col: int,
    join_type: str = 'left'
) -> MergeResult:
    """JOIN двух наборов данных.
    
    Args:
        left_data: Левая таблица (с заголовком).
        right_data: Правая таблица (с заголовком).
        left_key_col: Индекс ключевого столбца слева.
        right_key_col: Индекс ключевого столбца справа.
        join_type: Тип соединения ('left', 'inner', 'full').
        
    Returns:
        Результат соединения.
    """
    if not left_data or not right_data:
        return MergeResult(data=[], headers=[], source_count=2, total_rows=0)
    
    left_headers = left_data[0]
    right_headers = right_data[0]
    
    # Результирующие заголовки: левые + правые (кроме ключа)
    result_headers = list(left_headers)
    right_non_key_cols = []
    for i, h in enumerate(right_headers):
        if i != right_key_col:
            result_headers.append(h)
            right_non_key_cols.append(i)
    
    # Индексируем правую таблицу по ключу
    right_index: Dict[Any, List[Any]] = {}
    for row in right_data[1:]:
        if right_key_col < len(row):
            key = row[right_key_col]
            if key is not None and key != '':
                if key not in right_index:
                    right_index[key] = []
                right_index[key].append(row)
    
    result_data = [result_headers]
    
    # Обрабатываем левую таблицу
    for left_row in left_data[1:]:
        if left_key_col >= len(left_row):
            continue
        
        key = left_row[left_key_col]
        matching_right = right_index.get(key, [])
        
        if matching_right:
            # Есть совпадения
            for right_row in matching_right:
                new_row = list(left_row)
                for right_col_idx in right_non_key_cols:
                    val = right_row[right_col_idx] if right_col_idx < len(right_row) else None
                    new_row.append(val)
                result_data.append(new_row)
        elif join_type in ('left', 'full'):
            # Нет совпадений, но оставляем левую строку
            new_row = list(left_row) + [None] * len(right_non_key_cols)
            result_data.append(new_row)
    
    # Если full join, добавляем unmatched правые строки
    if join_type == 'full':
        matched_keys = set()
        for left_row in left_data[1:]:
            if left_key_col < len(left_row):
                matched_keys.add(left_row[left_key_col])
        
        for right_row in right_data[1:]:
            if right_key_col < len(right_row):
                key = right_row[right_key_col]
                if key not in matched_keys and key is not None and key != '':
                    new_row = [None] * len(left_headers)
                    for right_col_idx in right_non_key_cols:
                        val = right_row[right_col_idx] if right_col_idx < len(right_row) else None
                        new_row.append(val)
                    result_data.append(new_row)
    
    return MergeResult(
        data=result_data,
        headers=result_headers,
        source_count=2,
        total_rows=len(result_data) - 1
    )


def aggregate(
    data: List[List[Any]],
    group_by_cols: List[int],
    aggregations: Dict[int, str]
) -> MergeResult:
    """Агрегация данных.
    
    Args:
        data: Данные с заголовком.
        group_by_cols: Столбцы для группировки.
        aggregations: Маппинг {индекс_столбца: функция} где функция в ('sum', 'count', 'avg', 'min', 'max').
        
    Returns:
        Агрегированные данные.
    """
    if not data:
        return MergeResult(data=[], headers=[], source_count=0, total_rows=0)
    
    headers = data[0]
    groups: Dict[tuple, Dict[int, List[Any]]] = defaultdict(lambda: defaultdict(list))
    
    # Группируем
    for row in data[1:]:
        # Ключ группировки
        group_key = tuple(row[i] if i < len(row) else None for i in group_by_cols)
        
        # Собираем значения для агрегации
        for col_idx in aggregations.keys():
            if col_idx < len(row):
                groups[group_key][col_idx].append(row[col_idx])
    
    # Вычисляем агрегаты
    result_headers = [headers[i] if i < len(headers) else f'Col{i}' for i in group_by_cols]
    for col_idx, func in aggregations.items():
        result_headers.append(f'{func.upper()}({headers[col_idx] if col_idx < len(headers) else col_idx})')
    
    result_data = [result_headers]
    
    for group_key, cols_data in groups.items():
        result_row = list(group_key)
        
        for col_idx in aggregations.keys():
            values = cols_data[col_idx]
            func = aggregations[col_idx]
            
            # Числовые значения
            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v) if v is not None and v != '' else 0)
                except (ValueError, TypeError):
                    pass
            
            if func == 'sum':
                result_row.append(sum(numeric_values))
            elif func == 'count':
                result_row.append(len(values))
            elif func == 'avg':
                result_row.append(sum(numeric_values) / len(numeric_values) if numeric_values else 0)
            elif func == 'min':
                result_row.append(min(numeric_values) if numeric_values else None)
            elif func == 'max':
                result_row.append(max(numeric_values) if numeric_values else None)
        
        result_data.append(result_row)
    
    return MergeResult(
        data=result_data,
        headers=result_headers,
        source_count=1,
        total_rows=len(result_data) - 1
    )


def remove_duplicates(
    data: List[List[Any]],
    key_columns: Optional[List[int]] = None
) -> MergeResult:
    """Удаление дубликатов из свода.
    
    Args:
        data: Данные с заголовком.
        key_columns: Столбцы для определения уникальности (None = все столбцы).
        
    Returns:
        Данные без дубликатов.
    """
    if not data:
        return MergeResult(data=[], headers=[], source_count=0, total_rows=0)
    
    headers = data[0]
    seen = set()
    unique_rows = [headers]
    duplicates_count = 0
    
    for row in data[1:]:
        # Ключ для проверки
        if key_columns is None:
            key = tuple(str(cell) if cell is not None else '' for cell in row)
        else:
            key = tuple(str(row[i]) if i < len(row) and row[i] is not None else '' for i in key_columns)
        
        if key in seen:
            duplicates_count += 1
        else:
            seen.add(key)
            unique_rows.append(list(row))
    
    return MergeResult(
        data=unique_rows,
        headers=headers,
        source_count=1,
        total_rows=len(unique_rows) - 1,
        duplicates_removed=duplicates_count
    )


def align_columns(
    files_data: List[Tuple[str, List[List[Any]], List[str]]],
    reference_headers: Optional[List[str]] = None
) -> MergeResult:
    """Выравнивание столбцов по эталону.
    
    Args:
        files_data: Список кортежей (имя, данные, заголовки).
        reference_headers: Эталонные заголовки (если None, берётся первый файл).
        
    Returns:
        Данные с выровненными столбцами.
    """
    if not files_data:
        return MergeResult(data=[], headers=[], source_count=0, total_rows=0)
    
    if reference_headers is None:
        reference_headers = files_data[0][2]
    
    all_data = [reference_headers]
    warnings = []
    
    for file_name, data, headers in files_data:
        if not data:
            continue
        
        # Маппинг столбцов
        col_mapping = {}
        for i, h in enumerate(headers):
            if h in reference_headers:
                col_mapping[i] = reference_headers.index(h)
            else:
                warnings.append(f'{file_name}: столбец "{h}" отсутствует в эталоне')
        
        # Выравниваем каждую строку
        for row in data[1:]:
            aligned_row = [None] * len(reference_headers)
            for src_idx, dst_idx in col_mapping.items():
                if src_idx < len(row):
                    aligned_row[dst_idx] = row[src_idx]
            all_data.append(aligned_row)
    
    return MergeResult(
        data=all_data,
        headers=reference_headers,
        source_count=len(files_data),
        total_rows=len(all_data) - 1,
        warnings=warnings
    )


__all__ = [
    'merge_stack', 'merge_join', 'aggregate', 'remove_duplicates',
    'align_columns', 'MergeResult'
]
