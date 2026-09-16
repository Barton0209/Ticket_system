"""
М6: Валидация данных
FR-0601: Проверка типов данных
FR-0602: Проверка диапазонов значений
FR-0603: Проверка уникальности
FR-0604: Проверка по регулярным выражениям
FR-0605: Отчёт об ошибках валидации
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import pandas as pd


class ValidationType(Enum):
    """Типы валидации"""
    REQUIRED = "required"
    DATA_TYPE = "data_type"
    RANGE = "range"
    REGEX = "regex"
    UNIQUE = "unique"
    IN_LIST = "in_list"
    CUSTOM = "custom"


class DataType(Enum):
    """Типы данных для валидации"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"


@dataclass
class ValidationError:
    """Ошибка валидации"""
    row_index: int
    column: str
    value: Any
    error_type: ValidationType
    message: str
    expected: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'row_index': self.row_index,
            'column': self.column,
            'value': str(self.value) if self.value is not None else None,
            'error_type': self.error_type.value,
            'message': self.message,
            'expected': self.expected
        }


@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'total_rows': self.total_rows,
            'valid_rows': self.valid_rows,
            'invalid_rows': self.invalid_rows,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'checked_at': self.checked_at
        }


@dataclass
class ValidationRule:
    """Правило валидации"""
    column: str
    validation_type: ValidationType
    required: bool = False
    data_type: Optional[DataType] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_func: Optional[Callable[[Any], bool]] = None
    error_message: Optional[str] = None
    warning: bool = False
    
    def validate(self, value: Any, row_index: int) -> Optional[ValidationError]:
        """Проверка значения по правилу"""
        # Пропуск пустых значений (если не required)
        if pd.isna(value) or value == '':
            if self.required:
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.REQUIRED,
                    message=self.error_message or f"Значение в столбце '{self.column}' обязательно",
                    expected="непустое значение"
                )
            return None
        
        # Проверка типа данных
        if self.validation_type == ValidationType.DATA_TYPE and self.data_type:
            if not self._check_data_type(value, self.data_type):
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.DATA_TYPE,
                    message=self.error_message or f"Неверный тип данных в столбце '{self.column}'",
                    expected=self.data_type.value
                )
        
        # Проверка диапазона
        if self.validation_type == ValidationType.RANGE:
            if self.min_value is not None and value < self.min_value:
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.RANGE,
                    message=self.error_message or f"Значение меньше минимального ({self.min_value})",
                    expected=f">= {self.min_value}"
                )
            if self.max_value is not None and value > self.max_value:
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.RANGE,
                    message=self.error_message or f"Значение больше максимального ({self.max_value})",
                    expected=f"<= {self.max_value}"
                )
        
        # Проверка по регулярному выражению
        if self.validation_type == ValidationType.REGEX and self.pattern:
            if not isinstance(value, str) or not re.match(self.pattern, str(value)):
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.REGEX,
                    message=self.error_message or f"Значение не соответствует шаблону '{self.pattern}'",
                    expected=self.pattern
                )
        
        # Проверка уникальности (обрабатывается отдельно)
        if self.validation_type == ValidationType.UNIQUE:
            pass  # Обрабатывается на уровне всего столбца
        
        # Проверка списка допустимых значений
        if self.validation_type == ValidationType.IN_LIST and self.allowed_values:
            if value not in self.allowed_values:
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.IN_LIST,
                    message=self.error_message or f"Значение不在 списке допустимых",
                    expected=str(self.allowed_values)
                )
        
        # Пользовательская функция
        if self.validation_type == ValidationType.CUSTOM and self.custom_func:
            try:
                if not self.custom_func(value):
                    return ValidationError(
                        row_index=row_index,
                        column=self.column,
                        value=value,
                        error_type=ValidationType.CUSTOM,
                        message=self.error_message or "Пользовательская проверка не пройдена"
                    )
            except Exception as e:
                return ValidationError(
                    row_index=row_index,
                    column=self.column,
                    value=value,
                    error_type=ValidationType.CUSTOM,
                    message=f"Ошибка пользовательской проверки: {str(e)}"
                )
        
        return None
    
    def _check_data_type(self, value: Any, data_type: DataType) -> bool:
        """Проверка типа данных"""
        try:
            if data_type == DataType.STRING:
                return isinstance(value, str)
            elif data_type == DataType.INTEGER:
                return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
            elif data_type == DataType.FLOAT:
                return isinstance(value, (int, float))
            elif data_type == DataType.BOOLEAN:
                return isinstance(value, bool) or str(value).lower() in ('true', 'false', '1', '0')
            elif data_type == DataType.DATE:
                if isinstance(value, str):
                    pd.to_datetime(value, format='%Y-%m-%d')
                return True
            elif data_type == DataType.DATETIME:
                if isinstance(value, str):
                    pd.to_datetime(value)
                return True
            elif data_type == DataType.EMAIL:
                return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(value)))
            elif data_type == DataType.PHONE:
                return bool(re.match(r'^[\+]?[\d\s\-\(\)]{7,20}$', str(value)))
        except:
            return False
        return True


class ValidationModule:
    """Модуль валидации данных"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
    
    def add_rule(self, rule: ValidationRule) -> 'ValidationModule':
        """Добавление правила валидации"""
        self.rules.append(rule)
        return self
    
    def clear_rules(self) -> 'ValidationModule':
        """Очистка всех правил"""
        self.rules = []
        return self
    
    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Валидация DataFrame
        
        Args:
            df: DataFrame для валидации
            
        Returns:
            ValidationResult с ошибками и статистикой
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        
        # Проверка уникальности на уровне столбца
        unique_rules = [r for r in self.rules if r.validation_type == ValidationType.UNIQUE]
        for rule in unique_rules:
            if rule.column in df.columns:
                duplicates = df[df.duplicated(subset=[rule.column], keep=False)]
                for idx in duplicates.index:
                    error = ValidationError(
                        row_index=int(idx),
                        column=rule.column,
                        value=df.at[idx, rule.column],
                        error_type=ValidationType.UNIQUE,
                        message=f"Дублирующееся значение в столбце '{rule.column}'",
                        expected="уникальное значение"
                    )
                    if rule.warning:
                        warnings.append(error)
                    else:
                        errors.append(error)
        
        # Проверка построчно
        invalid_row_indices = set()
        
        for rule in self.rules:
            if rule.validation_type == ValidationType.UNIQUE:
                continue  # Уже обработано
            
            if rule.column not in df.columns:
                continue  # Столбец отсутствует, пропускаем
            
            for idx, value in df[rule.column].items():
                error = rule.validate(value, int(idx))
                if error:
                    if rule.warning:
                        warnings.append(error)
                    else:
                        errors.append(error)
                        invalid_row_indices.add(idx)
        
        valid_count = len(df) - len(invalid_row_indices)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            total_rows=len(df),
            valid_rows=valid_count,
            invalid_rows=len(invalid_row_indices),
            errors=errors,
            warnings=warnings
        )
    
    def validate_column(self, df: pd.DataFrame, column: str, 
                       rules: List[ValidationRule]) -> ValidationResult:
        """Валидация отдельного столбца"""
        temp_module = ValidationModule()
        for rule in rules:
            temp_module.add_rule(rule)
        return temp_module.validate(df[[column]])
    
    @staticmethod
    def create_required_rule(column: str, error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила обязательности"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.REQUIRED,
            required=True,
            error_message=error_message
        )
    
    @staticmethod
    def create_range_rule(column: str, min_val: Any = None, max_val: Any = None,
                         error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила диапазона"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.RANGE,
            min_value=min_val,
            max_value=max_val,
            error_message=error_message
        )
    
    @staticmethod
    def create_regex_rule(column: str, pattern: str,
                         error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила regex"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.REGEX,
            pattern=pattern,
            error_message=error_message
        )
    
    @staticmethod
    def create_unique_rule(column: str, warning: bool = False,
                          error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила уникальности"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.UNIQUE,
            warning=warning,
            error_message=error_message
        )
    
    @staticmethod
    def create_in_list_rule(column: str, allowed_values: List[Any],
                           error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила списка значений"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.IN_LIST,
            allowed_values=allowed_values,
            error_message=error_message
        )
    
    @staticmethod
    def create_email_rule(column: str, required: bool = False,
                         error_message: Optional[str] = None) -> ValidationRule:
        """Создание правила email"""
        return ValidationRule(
            column=column,
            validation_type=ValidationType.DATA_TYPE,
            data_type=DataType.EMAIL,
            required=required,
            error_message=error_message
        )
    
    def get_error_summary(self, result: ValidationResult) -> Dict[str, int]:
        """Сводка ошибок по столбцам"""
        summary: Dict[str, int] = {}
        for error in result.errors:
            summary[error.column] = summary.get(error.column, 0) + 1
        return summary
    
    def filter_invalid_rows(self, df: pd.DataFrame, 
                           result: ValidationResult) -> pd.DataFrame:
        """Фильтрация невалидных строк"""
        if result.is_valid:
            return df.copy()
        
        invalid_indices = set(e.row_index for e in result.errors)
        return df.drop(index=invalid_indices)

__all__ = ['ValidationType', 'DataType', 'ValidationError']
