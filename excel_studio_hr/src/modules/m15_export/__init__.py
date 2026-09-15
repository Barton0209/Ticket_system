"""
Модуль М15: Экспорт данных

Действия:
- Экспорт в Excel/CSV/JSON
- Версионирование файлов
- Пересчёт формул (опция)
- BI-формат
- Сетевой диск
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import logging

logger = logging.getLogger('ExcelStudioHR.modules.m15_export')


def export_to_excel(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    output_path: Path = None,
    sheet_name: str = 'Sheet1',
    styles: Optional[List[List[Dict]]] = None,
    column_widths: Optional[List[float]] = None,
    row_heights: Optional[List[float]] = None,
    merges: Optional[List[str]] = None
) -> bool:
    """Экспорт в Excel (.xlsx).
    
    Args:
        data: Данные (матрица значений).
        headers: Заголовки (добавляются первой строкой).
        output_path: Путь к файлу.
        sheet_name: Имя листа.
        styles: Стили ячеек.
        column_widths: Ширины столбцов.
        row_heights: Высоты строк.
        merges: Диапазоны объединений.
        
    Returns:
        True если экспорт успешен.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Fill, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name[:31]  # Ограничение Excel
        
        # Добавляем заголовки если есть
        all_data = []
        if headers:
            all_data.append(headers)
        all_data.extend(data)
        
        # Записываем значения
        for row_idx, row in enumerate(all_data, start=1):
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                
                # Применяем стили если загружены
                if styles:
                    style_row_idx = row_idx - 1 if headers else row_idx - 1
                    if style_row_idx < len(styles):
                        style_col_idx = col_idx - 1
                        if style_col_idx < len(styles[style_row_idx]):
                            cell_style = styles[style_row_idx][style_col_idx]
                            _apply_style(cell, cell_style)
        
        # Ширины столбцов
        if column_widths:
            for col_idx, width in enumerate(column_widths, start=1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = width
        
        # Высоты строк
        if row_heights:
            for row_idx, height in enumerate(row_heights, start=1):
                ws.row_dimensions[row_idx].height = height
        
        # Объединения
        if merges:
            for merge_range in merges:
                ws.merge_cells(merge_range)
        
        # Сохраняем
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(str(output_path))
            logger.info(f'Экспорт в Excel: {output_path} ({len(all_data)} строк)')
            wb.close()
            return True
        
        wb.close()
        return True
        
    except Exception as e:
        logger.error(f'Ошибка экспорта в Excel: {e}', exc_info=True)
        return False


def _apply_style(cell, style: Dict):
    """Применение стиля к ячейке."""
    if not style:
        return
    
    # Шрифт
    if 'font' in style and style['font']:
        font = style['font']
        cell.font = Font(
            name=font.get('name', 'Calibri'),
            size=font.get('size', 11),
            bold=font.get('bold', False),
            italic=font.get('italic', False),
            color=font.get('color', '000000')
        )
    
    # Заливка
    if 'fill' in style and style['fill']:
        fill = style['fill']
        fg_color = fill.get('fgColor')
        if fg_color:
            cell.fill = PatternFill(start_color=fg_color.lstrip('#'), end_color=fg_color.lstrip('#'), fill_type='solid')
    
    # Выравнивание
    if 'alignment' in style and style['alignment']:
        align = style['alignment']
        cell.alignment = Alignment(
            horizontal=align.get('horizontal', 'general'),
            vertical=align.get('vertical', 'bottom')
        )
    
    # Числовой формат
    if 'number_format' in style and style['number_format']:
        cell.number_format = style['number_format']


def export_to_csv(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    output_path: Path = None,
    delimiter: str = ',',
    encoding: str = 'utf-8-sig'
) -> bool:
    """Экспорт в CSV.
    
    Args:
        data: Данные.
        headers: Заголовки.
        output_path: Путь к файлу.
        delimiter: Разделитель.
        encoding: Кодировка.
        
    Returns:
        True если экспорт успешен.
    """
    try:
        import csv
        
        if not output_path:
            return False
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding=encoding) as f:
            writer = csv.writer(f, delimiter=delimiter)
            
            if headers:
                writer.writerow(headers)
            
            for row in data:
                writer.writerow(row)
        
        logger.info(f'Экспорт в CSV: {output_path} ({len(data)} строк)')
        return True
        
    except Exception as e:
        logger.error(f'Ошибка экспорта в CSV: {e}', exc_info=True)
        return False


def export_to_json(
    data: List[List[Any]],
    headers: Optional[List[str]] = None,
    output_path: Path = None,
    orient: str = 'records'  # 'records' или 'list'
) -> bool:
    """Экспорт в JSON.
    
    Args:
        data: Данные.
        headers: Заголовки (для records).
        output_path: Путь к файлу.
        orient: Ориентация ('records' = [{header: value}], 'list' = {header: [values]}).
        
    Returns:
        True если экспорт успешен.
    """
    try:
        if not output_path:
            return False
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if orient == 'records' and headers:
            # Список словарей
            result = []
            for row in data:
                record = {}
                for i, h in enumerate(headers):
                    record[h] = row[i] if i < len(row) else None
                result.append(record)
        elif orient == 'list':
            # Словарь списков
            result = {}
            if headers:
                for i, h in enumerate(headers):
                    result[h] = [row[i] if i < len(row) else None for row in data]
            else:
                result['data'] = data
        else:
            # Просто матрица
            result = data
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f'Экспорт в JSON: {output_path}')
        return True
        
    except Exception as e:
        logger.error(f'Ошибка экспорта в JSON: {e}', exc_info=True)
        return False


def export_with_version(
    data: List[List[Any]],
    base_path: Path,
    headers: Optional[List[str]] = None,
    version_prefix: str = 'v',
    max_versions: int = 10
) -> Optional[Path]:
    """Экспорт с версионированием файла.
    
    Args:
        data: Данные.
        base_path: Базовый путь (без расширения).
        headers: Заголовки.
        version_prefix: Префикс версии.
        max_versions: Максимальное количество версий.
        
    Returns:
        Путь к созданному файлу или None.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    versioned_path = base_path.parent / f'{base_path.stem}_{version_prefix}{timestamp}{base_path.suffix}'
    
    # Определяем формат по расширению
    ext = base_path.suffix.lower()
    
    success = False
    if ext == '.xlsx':
        success = export_to_excel(data, headers, versioned_path)
    elif ext == '.csv':
        success = export_to_csv(data, headers, versioned_path)
    elif ext == '.json':
        success = export_to_json(data, headers, versioned_path)
    
    if success:
        # Ротация старых версий
        _rotate_versions(base_path.parent, base_path.stem, max_versions)
        return versioned_path
    
    return None


def _rotate_versions(directory: Path, stem: str, max_versions: int):
    """Ротация версий файла."""
    versions = list(directory.glob(f'{stem}_v*.xlsx')) + \
               list(directory.glob(f'{stem}_v*.csv')) + \
               list(directory.glob(f'{stem}_v*.json'))
    
    # Сортируем по времени изменения (новые первые)
    versions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Удаляем старые
    for old_version in versions[max_versions:]:
        try:
            old_version.unlink()
            logger.debug(f'Удалена старая версия: {old_version}')
        except Exception as e:
            logger.warning(f'Не удалось удалить {old_version}: {e}')


def export_to_bi_format(
    data: List[List[Any]],
    headers: List[str],
    output_path: Path
) -> bool:
    """Экспорт в BI-формат (JSON для PowerBI/Tableau).
    
    Args:
        data: Данные.
        headers: Заголовки.
        output_path: Путь к файлу.
        
    Returns:
        True если экспорт успешен.
    """
    try:
        # Формат: список записей с метаданными
        result = {
            'metadata': {
                'columns': [{'name': h, 'type': 'string'} for h in headers],
                'row_count': len(data),
                'exported_at': datetime.now().isoformat()
            },
            'data': []
        }
        
        for row in data:
            record = {}
            for i, h in enumerate(headers):
                value = row[i] if i < len(row) else None
                # Определяем тип
                if isinstance(value, (int, float)):
                    result['metadata']['columns'][i]['type'] = 'number'
                elif isinstance(value, datetime):
                    result['metadata']['columns'][i]['type'] = 'datetime'
                record[h] = value
            result['data'].append(record)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f'Экспорт в BI-формат: {output_path}')
        return True
        
    except Exception as e:
        logger.error(f'Ошибка экспорта в BI-формат: {e}', exc_info=True)
        return False


def export_to_network_drive(
    data: List[List[Any]],
    network_path: str,
    headers: Optional[List[str]] = None,
    format: str = 'xlsx'
) -> bool:
    """Экспорт на сетевой диск.
    
    Args:
        data: Данные.
        network_path: UNC путь (\\\\server\\share\\file.xlsx).
        headers: Заголовки.
        format: Формат файла.
        
    Returns:
        True если экспорт успешен.
    """
    try:
        path = Path(network_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'xlsx':
            return export_to_excel(data, headers, path)
        elif format == 'csv':
            return export_to_csv(data, headers, path)
        elif format == 'json':
            return export_to_json(data, headers, path)
        
        logger.error(f'Неподдерживаемый формат: {format}')
        return False
        
    except Exception as e:
        logger.error(f'Ошибка экспорта на сетевой диск: {e}', exc_info=True)
        return False


__all__ = [
    'export_to_excel', 'export_to_csv', 'export_to_json',
    'export_with_version', 'export_to_bi_format', 'export_to_network_drive'
]
