"""
Модуль М2: Просмотр и редактирование

Действия:
- Постраничный просмотр (2000 строк на страницу, FR-0201)
- Undo/redo через дифф-журнал (FR-1402)
- Поиск и фильтры
- Буфер обмена
- Инспектор ячейки
- Редактирование значений
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
from datetime import datetime

logger = logging.getLogger('ExcelStudioHR.modules.m02_view')


@dataclass
class CellEdit:
    """Запись об изменении ячейки для undo/redo."""
    row: int
    col: int
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PageConfig:
    """Конфигурация страницы просмотра."""
    page_size: int = 2000  # FR-0201
    current_page: int = 0
    show_grid: bool = True
    show_headers: bool = True


class SheetViewer:
    """Просмотрщик листа с постраничной навигацией."""
    
    def __init__(self, sheet_model):
        """Инициализация просмотрщика.
        
        Args:
            sheet_model: Модель листа из М1.
        """
        self.sheet_model = sheet_model
        self.config = PageConfig()
        self.edit_history: List[CellEdit] = []
        self.redo_stack: List[CellEdit] = []
        
        # Кэш отфильтрованных строк
        self.filtered_rows: Optional[List[int]] = None
        
        # Текущий поиск
        self.search_results: List[Tuple[int, int]] = []
        self.search_current_idx: int = -1
    
    @property
    def total_pages(self) -> int:
        """Общее количество страниц."""
        if not self.sheet_model or self.sheet_model.row_count == 0:
            return 0
        return (self.sheet_model.row_count - 1) // self.config.page_size + 1
    
    @property
    def current_page(self) -> int:
        """Текущая страница."""
        return self.config.current_page
    
    def get_page_data(self, page_num: Optional[int] = None) -> List[List[Any]]:
        """Получить данные для указанной страницы.
        
        Args:
            page_num: Номер страницы (по умолчанию - текущая).
            
        Returns:
            Матрица значений для страницы.
        """
        if page_num is None:
            page_num = self.config.current_page
        
        if not self.sheet_model or self.sheet_model.row_count == 0:
            return []
        
        start_row = page_num * self.config.page_size
        end_row = min(start_row + self.config.page_size, self.sheet_model.row_count)
        
        # Применяем фильтр если есть
        if self.filtered_rows is not None:
            # Фильтрация на уровне индексов
            visible_rows = [r for r in self.filtered_rows 
                          if start_row <= r < end_row]
            return [self.sheet_model.data[r] for r in visible_rows]
        
        return self.sheet_model.data[start_row:end_row]
    
    def get_page_styles(self, page_num: Optional[int] = None) -> List[List[Dict]]:
        """Получить стили для указанной страницы.
        
        Args:
            page_num: Номер страницы (по умолчанию - текущая).
            
        Returns:
            Матрица стилей для страницы.
        """
        if page_num is None:
            page_num = self.config.current_page
        
        if not self.sheet_model or not self.sheet_model.styles:
            return []
        
        start_row = page_num * self.config.page_size
        end_row = min(start_row + self.config.page_size, len(self.sheet_model.styles))
        
        return self.sheet_model.styles[start_row:end_row]
    
    def navigate_to_page(self, page_num: int) -> bool:
        """Перейти к указанной странице.
        
        Args:
            page_num: Номер страницы.
            
        Returns:
            True если переход успешен.
        """
        if page_num < 0 or page_num >= self.total_pages:
            return False
        
        self.config.current_page = page_num
        logger.debug(f'Переход к странице {page_num}/{self.total_pages}')
        return True
    
    def next_page(self) -> bool:
        """Перейти к следующей странице."""
        return self.navigate_to_page(self.config.current_page + 1)
    
    def prev_page(self) -> bool:
        """Перейти к предыдущей странице."""
        return self.navigate_to_page(self.config.current_page - 1)
    
    def first_page(self) -> bool:
        """Перейти к первой странице."""
        return self.navigate_to_page(0)
    
    def last_page(self) -> bool:
        """Перейти к последней странице."""
        return self.navigate_to_page(self.total_pages - 1)
    
    def edit_cell(self, row: int, col: int, new_value: Any) -> bool:
        """Редактировать ячейку с записью в историю undo.
        
        Args:
            row: Индекс строки (абсолютный, не страницы).
            col: Индекс столбца.
            new_value: Новое значение.
            
        Returns:
            True если редактирование успешно.
        """
        if not self.sheet_model or row >= self.sheet_model.row_count:
            return False
        
        # Получаем старое значение
        while len(self.sheet_model.data) <= row:
            self.sheet_model.data.append([])
        while len(self.sheet_model.data[row]) <= col:
            self.sheet_model.data[row].append(None)
        
        old_value = self.sheet_model.data[row][col]
        
        # Создаём запись истории
        edit = CellEdit(row=row, col=col, old_value=old_value, new_value=new_value)
        self.edit_history.append(edit)
        self.redo_stack.clear()  # Очищаем redo при новом изменении
        
        # Применяем изменение
        self.sheet_model.data[row][col] = new_value
        
        logger.debug(f'Ячейка [{row},{col}] изменена: {old_value!r} → {new_value!r}')
        return True
    
    def undo(self) -> Optional[CellEdit]:
        """Отменить последнее изменение.
        
        Returns:
            Отменённая запись изменения или None.
        """
        if not self.edit_history:
            return None
        
        edit = self.edit_history.pop()
        
        # Восстанавливаем старое значение
        if edit.row < len(self.sheet_model.data) and edit.col < len(self.sheet_model.data[edit.row]):
            current_value = self.sheet_model.data[edit.row][edit.col]
            self.sheet_model.data[edit.row][edit.col] = edit.old_value
            
            # Добавляем в redo стек
            redo_edit = CellEdit(
                row=edit.row, col=edit.col,
                old_value=current_value, new_value=edit.old_value
            )
            self.redo_stack.append(redo_edit)
            
            logger.debug(f'Undo: [{edit.row},{edit.col}] ← {edit.old_value!r}')
        
        return edit
    
    def redo(self) -> Optional[CellEdit]:
        """Повторить отменённое изменение.
        
        Returns:
            Повторённая запись изменения или None.
        """
        if not self.redo_stack:
            return None
        
        edit = self.redo_stack.pop()
        
        # Применяем новое значение
        if edit.row < len(self.sheet_model.data) and edit.col < len(self.sheet_model.data[edit.row]):
            self.sheet_model.data[edit.row][edit.col] = edit.new_value
            
            # Возвращаем в undo историю
            undo_edit = CellEdit(
                row=edit.row, col=edit.col,
                old_value=edit.old_value, new_value=edit.new_value
            )
            self.edit_history.append(undo_edit)
            
            logger.debug(f'Redo: [{edit.row},{edit.col}] → {edit.new_value!r}')
        
        return edit
    
    def search(self, text: str, case_sensitive: bool = False) -> List[Tuple[int, int]]:
        """Поиск текста в листе.
        
        Args:
            text: Искомый текст.
            case_sensitive: Учитывать регистр.
            
        Returns:
            Список координат найденных ячеек.
        """
        self.search_results = []
        
        if not text or not self.sheet_model:
            return self.search_results
        
        for row_idx, row in enumerate(self.sheet_model.data):
            for col_idx, cell_value in enumerate(row):
                if cell_value is None:
                    continue
                
                cell_str = str(cell_value)
                if case_sensitive:
                    if text in cell_str:
                        self.search_results.append((row_idx, col_idx))
                else:
                    if text.lower() in cell_str.lower():
                        self.search_results.append((row_idx, col_idx))
        
        self.search_current_idx = -1
        logger.debug(f'Поиск "{text}": найдено {len(self.search_results)} совпадений')
        return self.search_results
    
    def find_next(self) -> Optional[Tuple[int, int]]:
        """Найти следующее совпадение поиска.
        
        Returns:
            Координаты ячейки или None.
        """
        if not self.search_results:
            return None
        
        self.search_current_idx = (self.search_current_idx + 1) % len(self.search_results)
        return self.search_results[self.search_current_idx]
    
    def find_previous(self) -> Optional[Tuple[int, int]]:
        """Найти предыдущее совпадение поиска.
        
        Returns:
            Координаты ячейки или None.
        """
        if not self.search_results:
            return None
        
        self.search_current_idx = (self.search_current_idx - 1) % len(self.search_results)
        return self.search_results[self.search_current_idx]
    
    def apply_filter(self, column: int, condition: callable) -> None:
        """Применить фильтр к столбцу.
        
        Args:
            column: Индекс столбца.
            condition: Функция-условие (возвращает True для видимых строк).
        """
        if not self.sheet_model:
            return
        
        self.filtered_rows = []
        for row_idx, row in enumerate(self.sheet_model.data):
            if column < len(row):
                if condition(row[column]):
                    self.filtered_rows.append(row_idx)
        
        logger.debug(f'Фильтр столбца {column}: {len(self.filtered_rows)} видимых строк')
    
    def clear_filter(self) -> None:
        """Очистить фильтр."""
        self.filtered_rows = None
        logger.debug('Фильтр очищен')
    
    def get_cell_inspector(self, row: int, col: int) -> Dict[str, Any]:
        """Получить полную информацию о ячейке для инспектора.
        
        Args:
            row: Индекс строки.
            col: Индекс столбца.
            
        Returns:
            Словарь с информацией о ячейке.
        """
        info = {
            'coordinates': f'R{row+1}C{col+1}',
            'value': None,
            'type': 'None',
            'style': None,
        }
        
        if self.sheet_model and row < len(self.sheet_model.data):
            row_data = self.sheet_model.data[row]
            if col < len(row_data):
                value = row_data[col]
                info['value'] = value
                info['type'] = type(value).__name__
                
                # Стиль если загружен
                if self.sheet_model.styles and row < len(self.sheet_model.styles):
                    style_row = self.sheet_model.styles[row]
                    if col < len(style_row):
                        info['style'] = style_row[col]
        
        return info
    
    def copy_to_clipboard(self, selection: List[Tuple[int, int]]) -> str:
        """Копировать выделенные ячейки в буфер (текстовый формат).
        
        Args:
            selection: Список координат выделенных ячеек.
            
        Returns:
            Текст для буфера обмена.
        """
        if not selection or not self.sheet_model:
            return ''
        
        # Группируем по строкам
        rows_dict: Dict[int, Dict[int, Any]] = {}
        for row, col in selection:
            if row not in rows_dict:
                rows_dict[row] = {}
            if row < len(self.sheet_model.data) and col < len(self.sheet_model.data[row]):
                rows_dict[row][col] = self.sheet_model.data[row][col]
        
        # Формируем TSV
        lines = []
        for row_idx in sorted(rows_dict.keys()):
            cols = rows_dict[row_idx]
            if not cols:
                continue
            min_col = min(cols.keys())
            max_col = max(cols.keys())
            line_parts = []
            for c in range(min_col, max_col + 1):
                val = cols.get(c, '')
                line_parts.append(str(val) if val is not None else '')
            lines.append('\t'.join(line_parts))
        
        return '\n'.join(lines)
    
    def can_undo(self) -> bool:
        """Проверить возможность отмены."""
        return len(self.edit_history) > 0
    
    def can_redo(self) -> bool:
        """Проверить возможность повтора."""
        return len(self.redo_stack) > 0


class FileViewer:
    """Просмотрщик файла Excel (набор листов)."""
    
    def __init__(self, file_model):
        """Инициализация просмотрщика файла.
        
        Args:
            file_model: Модель файла из М1.
        """
        self.file_model = file_model
        self.sheet_viewers: Dict[str, SheetViewer] = {}
        self.current_sheet: Optional[str] = None
        
        # Создаём просмотрщики для всех листов
        if file_model and file_model.sheets:
            for sheet_name in file_model.sheets:
                self.sheet_viewers[sheet_name] = SheetViewer(file_model.sheets[sheet_name])
            self.current_sheet = list(file_model.sheets.keys())[0]
    
    def get_current_viewer(self) -> Optional[SheetViewer]:
        """Получить текущий просмотрщик листа."""
        if self.current_sheet and self.current_sheet in self.sheet_viewers:
            return self.sheet_viewers[self.current_sheet]
        return None
    
    def switch_sheet(self, sheet_name: str) -> bool:
        """Переключиться на указанный лист.
        
        Args:
            sheet_name: Имя листа.
            
        Returns:
            True если переключение успешно.
        """
        if sheet_name in self.sheet_viewers:
            self.current_sheet = sheet_name
            logger.debug(f'Переключен на лист: {sheet_name}')
            return True
        return False
    
    def get_sheet_list(self) -> List[str]:
        """Получить список листов."""
        return list(self.sheet_viewers.keys())


__all__ = ['CellEdit', 'PageConfig', 'SheetViewer']
