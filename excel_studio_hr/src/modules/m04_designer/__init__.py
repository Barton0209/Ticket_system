"""
Модуль М4: Конструктор цепочек операций

Действия:
- 65+ операций с op_id (неизменяемый код, §V.0)
- Построение цепочек обработки (сценариев)
- Избранное, условия шагов
- Сохранение/загрузка сценариев в JSON
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger('ExcelStudioHR.modules.m04_designer')


# ============================================================================
# ОПЕРАЦИИ (op_id - неизменяемые коды, §V.0)
# ============================================================================

@dataclass
class OperationParam:
    """Параметр операции."""
    name: str
    param_type: str  # 'int', 'str', 'float', 'bool', 'column', 'list'
    default: Any = None
    required: bool = False
    description: str = ''


@dataclass
class Operation:
    """Операция над моделью листа."""
    op_id: str  # Неизменяемый код (например, 'OP_DELETE_ROWS')
    name: str  # Отображаемое имя
    description: str = ''
    category: str = 'Общее'  # Категория для группировки
    params: List[OperationParam] = field(default_factory=list)
    icon: str = '⚙️'
    
    # Функция выполнения (устанавливается при регистрации)
    handler: Optional[Callable] = None


# Реестр всех операций
OPERATIONS_REGISTRY: Dict[str, Operation] = {}


def register_operation(op: Operation):
    """Регистрация операции в реестре."""
    if op.op_id in OPERATIONS_REGISTRY:
        logger.warning(f'Операция {op.op_id} уже зарегистрирована')
        return
    OPERATIONS_REGISTRY[op.op_id] = op
    logger.debug(f'Зарегистрирована операция: {op.op_id} - {op.name}')


def get_operation(op_id: str) -> Optional[Operation]:
    """Получить операцию по ID."""
    return OPERATIONS_REGISTRY.get(op_id)


def get_all_operations() -> List[Operation]:
    """Получить все зарегистрированные операции."""
    return list(OPERATIONS_REGISTRY.values())


def get_operations_by_category(category: str) -> List[Operation]:
    """Получить операции категории."""
    return [op for op in OPERATIONS_REGISTRY.values() if op.category == category]


# ============================================================================
# БАЗОВЫЕ ОПЕРАЦИИ (реализация handlers)
# ============================================================================

def _op_delete_rows_handler(sheet_model, params: Dict) -> Dict:
    """Удаление строк (FR-0401)."""
    row_indices = params.get('rows', [])
    deleted_count = 0
    
    # Сортируем в обратном порядке для безопасного удаления
    for idx in sorted(row_indices, reverse=True):
        if 0 <= idx < len(sheet_model.data):
            sheet_model.data.pop(idx)
            if sheet_model.styles and idx < len(sheet_model.styles):
                sheet_model.styles.pop(idx)
            deleted_count += 1
    
    return {'deleted_rows': deleted_count}


def _op_delete_columns_handler(sheet_model, params: Dict) -> Dict:
    """Удаление столбцов."""
    col_indices = params.get('columns', [])
    deleted_count = 0
    
    for col_idx in sorted(col_indices, reverse=True):
        for row in sheet_model.data:
            if col_idx < len(row):
                row.pop(col_idx)
                deleted_count += 1
        
        if sheet_model.styles:
            for style_row in sheet_model.styles:
                if col_idx < len(style_row):
                    style_row.pop(col_idx)
    
    return {'deleted_columns': deleted_count}


def _op_trim_handler(sheet_model, params: Dict) -> Dict:
    """Обрезка пробелов (FR-0402)."""
    trimmed_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        for col_idx, cell in enumerate(row):
            if isinstance(cell, str):
                original = cell
                trimmed = cell.strip()
                if original != trimmed:
                    sheet_model.data[row_idx][col_idx] = trimmed
                    trimmed_count += 1
    
    return {'trimmed_cells': trimmed_count}


def _op_uppercase_handler(sheet_model, params: Dict) -> Dict:
    """Верхний регистр."""
    column = params.get('column', 0)
    changed_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        if column < len(row):
            cell = row[column]
            if isinstance(cell, str):
                original = cell
                upper = cell.upper()
                if original != upper:
                    sheet_model.data[row_idx][column] = upper
                    changed_count += 1
    
    return {'changed_cells': changed_count}


def _op_lowercase_handler(sheet_model, params: Dict) -> Dict:
    """Нижний регистр."""
    column = params.get('column', 0)
    changed_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        if column < len(row):
            cell = row[column]
            if isinstance(cell, str):
                original = cell
                lower = cell.lower()
                if original != lower:
                    sheet_model.data[row_idx][column] = lower
                    changed_count += 1
    
    return {'changed_cells': changed_count}


def _op_capitalize_handler(sheet_model, params: Dict) -> Dict:
    """Заглавная первая буква (ФИО)."""
    column = params.get('column', 0)
    changed_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        if column < len(row):
            cell = row[column]
            if isinstance(cell, str):
                original = cell
                capitalized = cell.title()
                if original != capitalized:
                    sheet_model.data[row_idx][column] = capitalized
                    changed_count += 1
    
    return {'changed_cells': changed_count}


def _op_remove_duplicates_handler(sheet_model, params: Dict) -> Dict:
    """Удаление дубликатов (FR-0403)."""
    columns = params.get('columns', [0])  # По умолчанию по первому столбцу
    seen = set()
    removed_count = 0
    rows_to_remove = []
    
    for row_idx, row in enumerate(sheet_model.data):
        # Ключ для сравнения
        key_parts = []
        for col in columns:
            if col < len(row):
                key_parts.append(str(row[col]) if row[col] is not None else '')
        key = '|'.join(key_parts)
        
        if key in seen:
            rows_to_remove.append(row_idx)
            removed_count += 1
        else:
            seen.add(key)
    
    # Удаляем дубликаты в обратном порядке
    for idx in sorted(rows_to_remove, reverse=True):
        sheet_model.data.pop(idx)
        if sheet_model.styles and idx < len(sheet_model.styles):
            sheet_model.styles.pop(idx)
    
    return {'removed_duplicates': removed_count}


def _op_fill_down_handler(sheet_model, params: Dict) -> Dict:
    """Протяжка значения вниз (FR-0404)."""
    column = params.get('column', 0)
    filled_count = 0
    last_value = None
    
    for row_idx, row in enumerate(sheet_model.data):
        if column < len(row):
            cell = row[column]
            if cell is not None and cell != '':
                last_value = cell
            elif last_value is not None:
                sheet_model.data[row_idx][column] = last_value
                filled_count += 1
    
    return {'filled_cells': filled_count}


def _op_split_column_handler(sheet_model, params: Dict) -> Dict:
    """Разделение столбца по разделителю."""
    column = params.get('column', 0)
    delimiter = params.get('delimiter', ' ')
    max_splits = params.get('max_splits', -1)
    
    insert_col_idx = column + 1
    split_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        if column < len(row):
            cell = row[column]
            if isinstance(cell, str):
                parts = cell.split(delimiter, max_splits if max_splits > 0 else None)
                if len(parts) > 1:
                    row[column] = parts[0]
                    # Вставляем остальные части в новые столбцы
                    for i, part in enumerate(parts[1:], start=insert_col_idx):
                        while len(row) <= i:
                            row.append(None)
                        row[i] = part
                    split_count += 1
    
    return {'split_cells': split_count}


def _op_concat_columns_handler(sheet_model, params: Dict) -> Dict:
    """Объединение столбцов."""
    columns = params.get('columns', [0, 1])
    delimiter = params.get('delimiter', ' ')
    target_column = params.get('target', 0)
    
    concat_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        parts = []
        for col in columns:
            if col < len(row) and row[col] is not None:
                parts.append(str(row[col]))
        
        if parts:
            result = delimiter.join(parts)
            while len(row) <= target_column:
                row.append(None)
            if row[target_column] != result:
                row[target_column] = result
                concat_count += 1
    
    return {'concatenated_rows': concat_count}


def _op_replace_handler(sheet_model, params: Dict) -> Dict:
    """Замена текста/значений."""
    find_value = params.get('find', '')
    replace_value = params.get('replace', '')
    column = params.get('column', None)  # None = все столбцы
    use_regex = params.get('regex', False)
    
    replaced_count = 0
    
    for row_idx, row in enumerate(sheet_model.data):
        for col_idx, cell in enumerate(row):
            if column is not None and col_idx != column:
                continue
            
            if isinstance(cell, str):
                if use_regex:
                    import re
                    new_cell = re.sub(find_value, replace_value, cell)
                else:
                    new_cell = cell.replace(find_value, replace_value)
                
                if new_cell != cell:
                    sheet_model.data[row_idx][col_idx] = new_cell
                    replaced_count += 1
    
    return {'replaced_cells': replaced_count}


def _op_insert_rows_handler(sheet_model, params: Dict) -> Dict:
    """Вставка пустых строк."""
    position = params.get('position', 0)
    count = params.get('count', 1)
    
    for _ in range(count):
        sheet_model.data.insert(position, [None] * sheet_model.col_count)
        if sheet_model.styles:
            sheet_model.styles.insert(position, [{}] * sheet_model.col_count)
    
    return {'inserted_rows': count}


def _op_insert_columns_handler(sheet_model, params: Dict) -> Dict:
    """Вставка пустых столбцов."""
    position = params.get('position', 0)
    count = params.get('count', 1)
    
    for row in sheet_model.data:
        for _ in range(count):
            row.insert(position, None)
    
    if sheet_model.styles:
        for style_row in sheet_model.styles:
            for _ in range(count):
                style_row.insert(position, {})
    
    return {'inserted_columns': count}


def _op_sort_handler(sheet_model, params: Dict) -> Dict:
    """Сортировка по столбцу."""
    column = params.get('column', 0)
    ascending = params.get('ascending', True)
    
    # Создаём индексацию с данными
    indexed_data = list(enumerate(sheet_model.data))
    
    def sort_key(item):
        idx, row = item
        if column < len(row):
            val = row[column]
            # Пустые значения всегда в конце
            if val is None or val == '':
                return (1, '')
            return (0, val if isinstance(val, (int, float, str)) else str(val))
        return (1, '')
    
    indexed_data.sort(key=sort_key, reverse=not ascending)
    
    # Применяем сортировку
    sheet_model.data = [row for _, row in indexed_data]
    if sheet_model.styles:
        # Стили переставляем аналогично
        old_styles = sheet_model.styles
        sheet_model.styles = [old_styles[idx] for idx, _ in indexed_data if idx < len(old_styles)]
    
    return {'sorted': True}


def _op_filter_keep_handler(sheet_model, params: Dict) -> Dict:
    """Фильтрация: оставить строки где значение соответствует."""
    column = params.get('column', 0)
    value = params.get('value', '')
    operator = params.get('operator', 'equals')  # equals, contains, starts_with, ends_with, gt, lt
    
    rows_to_keep = []
    
    for row_idx, row in enumerate(sheet_model.data):
        if column >= len(row):
            continue
        
        cell = row[column]
        cell_str = str(cell) if cell is not None else ''
        
        match = False
        if operator == 'equals':
            match = cell_str == value
        elif operator == 'contains':
            match = value in cell_str
        elif operator == 'starts_with':
            match = cell_str.startswith(value)
        elif operator == 'ends_with':
            match = cell_str.endswith(value)
        elif operator == 'gt':
            try:
                match = float(cell) > float(value)
            except (ValueError, TypeError):
                match = False
        elif operator == 'lt':
            try:
                match = float(cell) < float(value)
            except (ValueError, TypeError):
                match = False
        
        if match:
            rows_to_keep.append(row_idx)
    
    # Оставляем только совпавшие строки
    new_data = [sheet_model.data[i] for i in rows_to_keep]
    sheet_model.data = new_data
    
    if sheet_model.styles:
        sheet_model.styles = [sheet_model.styles[i] for i in rows_to_keep if i < len(sheet_model.styles)]
    
    return {'kept_rows': len(rows_to_keep), 'removed_rows': len(sheet_model.data) - len(rows_to_keep)}


# ============================================================================
# РЕГИСТРАЦИЯ БАЗОВЫХ ОПЕРАЦИЙ
# ============================================================================

def register_builtin_operations():
    """Регистрация встроенных операций."""
    
    # Удаление
    register_operation(Operation(
        op_id='OP_DELETE_ROWS',
        name='Удалить строки',
        description='Удалить указанные строки',
        category='🗑️ Удаление',
        params=[
            OperationParam('rows', 'list', default=[], required=True, description='Индексы строк')
        ],
        icon='🗑️',
        handler=_op_delete_rows_handler
    ))
    
    register_operation(Operation(
        op_id='OP_DELETE_COLUMNS',
        name='Удалить столбцы',
        description='Удалить указанные столбцы',
        category='🗑️ Удаление',
        params=[
            OperationParam('columns', 'list', default=[], required=True)
        ],
        icon='🗑️',
        handler=_op_delete_columns_handler
    ))
    
    # Преобразование текста
    register_operation(Operation(
        op_id='OP_TRIM',
        name='Обрезать пробелы',
        description='Удалить ведущие и замыкающие пробелы',
        category='✏️ Текст',
        params=[],
        icon='✂️',
        handler=_op_trim_handler
    ))
    
    register_operation(Operation(
        op_id='OP_UPPERCASE',
        name='Верхний регистр',
        description='Преобразовать текст в верхний регистр',
        category='✏️ Текст',
        params=[
            OperationParam('column', 'int', default=0, required=True)
        ],
        icon='🔠',
        handler=_op_uppercase_handler
    ))
    
    register_operation(Operation(
        op_id='OP_LOWERCASE',
        name='Нижний регистр',
        description='Преобразовать текст в нижний регистр',
        category='✏️ Текст',
        params=[
            OperationParam('column', 'int', default=0, required=True)
        ],
        icon='🔡',
        handler=_op_lowercase_handler
    ))
    
    register_operation(Operation(
        op_id='OP_CAPITALIZE',
        name='Заглавные буквы',
        description='Первая буква заглавная (для ФИО)',
        category='✏️ Текст',
        params=[
            OperationParam('column', 'int', default=0, required=True)
        ],
        icon='🔤',
        handler=_op_capitalize_handler
    ))
    
    # Дубликаты
    register_operation(Operation(
        op_id='OP_REMOVE_DUPLICATES',
        name='Удалить дубликаты',
        description='Удалить повторяющиеся строки',
        category='🧹 Очистка',
        params=[
            OperationParam('columns', 'list', default=[0], required=True)
        ],
        icon='🔄',
        handler=_op_remove_duplicates_handler
    ))
    
    # Заполнение
    register_operation(Operation(
        op_id='OP_FILL_DOWN',
        name='Протяжка вниз',
        description='Заполнить пустые ячейки последним значением',
        category='📥 Заполнение',
        params=[
            OperationParam('column', 'int', default=0, required=True)
        ],
        icon='⬇️',
        handler=_op_fill_down_handler
    ))
    
    # Столбцы
    register_operation(Operation(
        op_id='OP_SPLIT_COLUMN',
        name='Разделить столбец',
        description='Разделить столбец по разделителю',
        category='✂️ Разделение',
        params=[
            OperationParam('column', 'int', default=0, required=True),
            OperationParam('delimiter', 'str', default=' ', required=False),
            OperationParam('max_splits', 'int', default=-1, required=False)
        ],
        icon='✂️',
        handler=_op_split_column_handler
    ))
    
    register_operation(Operation(
        op_id='OP_CONCAT_COLUMNS',
        name='Объединить столбцы',
        description='Объединить несколько столбцов',
        category='🔗 Объединение',
        params=[
            OperationParam('columns', 'list', default=[0, 1], required=True),
            OperationParam('delimiter', 'str', default=' ', required=False),
            OperationParam('target', 'int', default=0, required=True)
        ],
        icon='🔗',
        handler=_op_concat_columns_handler
    ))
    
    # Замена
    register_operation(Operation(
        op_id='OP_REPLACE',
        name='Заменить текст',
        description='Найти и заменить текст',
        category='✏️ Текст',
        params=[
            OperationParam('find', 'str', default='', required=True),
            OperationParam('replace', 'str', default='', required=True),
            OperationParam('column', 'int', default=None, required=False),
            OperationParam('regex', 'bool', default=False, required=False)
        ],
        icon='🔄',
        handler=_op_replace_handler
    ))
    
    # Вставка
    register_operation(Operation(
        op_id='OP_INSERT_ROWS',
        name='Вставить строки',
        description='Вставить пустые строки',
        category='➕ Вставка',
        params=[
            OperationParam('position', 'int', default=0, required=True),
            OperationParam('count', 'int', default=1, required=True)
        ],
        icon='➕',
        handler=_op_insert_rows_handler
    ))
    
    register_operation(Operation(
        op_id='OP_INSERT_COLUMNS',
        name='Вставить столбцы',
        description='Вставить пустые столбцы',
        category='➕ Вставка',
        params=[
            OperationParam('position', 'int', default=0, required=True),
            OperationParam('count', 'int', default=1, required=True)
        ],
        icon='➕',
        handler=_op_insert_columns_handler
    ))
    
    # Сортировка
    register_operation(Operation(
        op_id='OP_SORT',
        name='Сортировать',
        description='Сортировать по столбцу',
        category='📊 Сортировка',
        params=[
            OperationParam('column', 'int', default=0, required=True),
            OperationParam('ascending', 'bool', default=True, required=False)
        ],
        icon='🔼',
        handler=_op_sort_handler
    ))
    
    # Фильтрация
    register_operation(Operation(
        op_id='OP_FILTER_KEEP',
        name='Фильтр: оставить',
        description='Оставить строки соответствующие условию',
        category='🔍 Фильтр',
        params=[
            OperationParam('column', 'int', default=0, required=True),
            OperationParam('value', 'str', default='', required=True),
            OperationParam('operator', 'str', default='equals', required=False)
        ],
        icon='🎯',
        handler=_op_filter_keep_handler
    ))


# ============================================================================
# ЦЕПОЧКА (СЦЕНАРИЙ)
# ============================================================================

@dataclass
class ChainStep:
    """Шаг цепочки."""
    op_id: str  # Код операции
    version: str = '1.0'  # Версия операции
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True  # Флаг включения шага
    condition: Optional[Dict] = None  # Условие выполнения (опционально)
    name: str = ''  # Пользовательское имя шага


@dataclass
class OperationChain:
    """Цепочка операций (сценарий)."""
    name: str
    description: str = ''
    steps: List[ChainStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    author: str = ''
    tags: List[str] = field(default_factory=list)
    is_favorite: bool = False
    
    def add_step(self, step: ChainStep):
        """Добавить шаг в цепочку."""
        self.steps.append(step)
        self.updated_at = datetime.now()
    
    def remove_step(self, index: int) -> bool:
        """Удалить шаг из цепочки."""
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
            self.updated_at = datetime.now()
            return True
        return False
    
    def move_step(self, index: int, direction: int) -> bool:
        """Переместить шаг вверх/вниз."""
        new_index = index + direction
        if 0 <= index < len(self.steps) and 0 <= new_index < len(self.steps):
            self.steps[index], self.steps[new_index] = self.steps[new_index], self.steps[index]
            self.updated_at = datetime.now()
            return True
        return False
    
    def execute(self, sheet_model) -> Dict:
        """Выполнить цепочку на модели листа.
        
        Args:
            sheet_model: Модель листа из М1.
            
        Returns:
            Отчёт о выполнении.
        """
        results = {
            'chain_name': self.name,
            'steps_executed': 0,
            'steps_skipped': 0,
            'step_results': [],
            'errors': []
        }
        
        for step_idx, step in enumerate(self.steps):
            if not step.enabled:
                results['steps_skipped'] += 1
                results['step_results'].append({
                    'step': step_idx,
                    'op_id': step.op_id,
                    'status': 'skipped',
                    'reason': 'disabled'
                })
                continue
            
            # Получаем операцию
            op = get_operation(step.op_id)
            if not op:
                error_msg = f'Операция {step.op_id} не найдена'
                results['errors'].append(error_msg)
                results['step_results'].append({
                    'step': step_idx,
                    'op_id': step.op_id,
                    'status': 'error',
                    'error': error_msg
                })
                logger.error(error_msg)
                continue
            
            # Проверяем условие если есть
            if step.condition:
                # TODO: Реализация условий (FR-04xx)
                pass
            
            # Выполняем операцию
            try:
                if op.handler:
                    step_result = op.handler(sheet_model, step.params)
                    results['steps_executed'] += 1
                    results['step_results'].append({
                        'step': step_idx,
                        'op_id': step.op_id,
                        'status': 'success',
                        'result': step_result
                    })
                    logger.debug(f'Шаг {step_idx} выполнен: {step.op_id}')
                else:
                    raise ValueError(f'У операции {step.op_id} нет handler')
                    
            except Exception as e:
                error_msg = f'Ошибка шага {step_idx} ({step.op_id}): {e}'
                results['errors'].append(error_msg)
                results['step_results'].append({
                    'step': step_idx,
                    'op_id': step.op_id,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(error_msg, exc_info=True)
        
        return results
    
    def to_dict(self) -> Dict:
        """Сериализация в словарь."""
        return {
            'name': self.name,
            'description': self.description,
            'steps': [asdict(step) for step in self.steps],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author,
            'tags': self.tags,
            'is_favorite': self.is_favorite
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OperationChain':
        """Десериализация из словаря."""
        chain = cls(
            name=data.get('name', 'Без названия'),
            description=data.get('description', ''),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now(),
            author=data.get('author', ''),
            tags=data.get('tags', []),
            is_favorite=data.get('is_favorite', False)
        )
        
        for step_data in data.get('steps', []):
            step = ChainStep(**step_data)
            chain.steps.append(step)
        
        return chain
    
    def save_to_file(self, path: Path):
        """Сохранить цепочку в JSON файл."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f'Цепочка сохранена: {path}')
    
    @classmethod
    def load_from_file(cls, path: Path) -> 'OperationChain':
        """Загрузить цепочку из JSON файла."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


# ============================================================================
# МЕНЕДЖЕР ЦЕПОЧЕК
# ============================================================================

class ChainManager:
    """Менеджер цепочек операций."""
    
    def __init__(self, chains_dir: Optional[Path] = None):
        """Инициализация менеджера.
        
        Args:
            chains_dir: Каталог для хранения цепочек.
        """
        self.chains: List[OperationChain] = []
        self.chains_dir = chains_dir
        
        # Регистрируем встроенные операции
        register_builtin_operations()
    
    def add_chain(self, chain: OperationChain):
        """Добавить цепочку."""
        self.chains.append(chain)
        logger.debug(f'Добавлена цепочка: {chain.name}')
    
    def remove_chain(self, name: str) -> bool:
        """Удалить цепочку по имени."""
        for i, chain in enumerate(self.chains):
            if chain.name == name:
                self.chains.pop(i)
                logger.debug(f'Удалена цепочка: {name}')
                return True
        return False
    
    def get_chain(self, name: str) -> Optional[OperationChain]:
        """Получить цепочку по имени."""
        for chain in self.chains:
            if chain.name == name:
                return chain
        return None
    
    def get_favorite_chains(self) -> List[OperationChain]:
        """Получить избранные цепочки."""
        return [c for c in self.chains if c.is_favorite]
    
    def save_all(self):
        """Сохранить все цепочки."""
        if not self.chains_dir:
            logger.warning('Каталог цепочек не указан')
            return
        
        self.chains_dir.mkdir(parents=True, exist_ok=True)
        
        for chain in self.chains:
            filename = f"{chain.name.replace(' ', '_')}.json"
            path = self.chains_dir / filename
            chain.save_to_file(path)
    
    def load_all(self):
        """Загрузить все цепочки из каталога."""
        if not self.chains_dir or not self.chains_dir.exists():
            return
        
        for path in self.chains_dir.glob('*.json'):
            try:
                chain = OperationChain.load_from_file(path)
                self.chains.append(chain)
                logger.debug(f'Загружена цепочка: {chain.name}')
            except Exception as e:
                logger.error(f'Ошибка загрузки цепочки {path}: {e}')


# Инициализация при импорте
register_builtin_operations()

__all__ = ['OperationParam', 'Operation', 'ChainStep', 'register_operation', 'get_operation']
