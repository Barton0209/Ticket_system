"""
М7: Формулы и вычисления
FR-0701: Поддержка Excel-подобных формул
FR-0702: Вычисления по столбцам
FR-0703: Агрегатные функции
FR-0704: Условные вычисления
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
import re
import math
from datetime import datetime


@dataclass
class FormulaError:
    """Ошибка формулы"""
    row_index: int
    column: str
    formula: str
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'row_index': self.row_index,
            'column': self.column,
            'formula': self.formula,
            'message': self.message
        }


class FormulaEngine:
    """Движок формул"""
    
    def __init__(self):
        self.functions: Dict[str, Callable] = self._register_functions()
    
    def _register_functions(self) -> Dict[str, Callable]:
        """Регистрация встроенных функций"""
        return {
            # Математические
            'SUM': lambda *args: sum(args),
            'AVG': lambda *args: sum(args) / len(args) if args else 0,
            'MIN': lambda *args: min(args) if args else None,
            'MAX': lambda *args: max(args) if args else None,
            'ROUND': lambda x, n=0: round(x, int(n)),
            'ABS': abs,
            'SQRT': math.sqrt,
            'POWER': pow,
            'MOD': lambda x, y: x % y,
            
            # Логические
            'IF': lambda cond, true_val, false_val=None: true_val if cond else false_val,
            'AND': lambda *args: all(args),
            'OR': lambda *args: any(args),
            'NOT': lambda x: not x,
            'ISNULL': pd.isna,
            'ISBLANK': lambda x: x is None or x == '',
            
            # Текстовые
            'CONCAT': lambda *args: ''.join(str(a) for a in args),
            'UPPER': str.upper,
            'LOWER': str.lower,
            'LEN': len,
            'LEFT': lambda s, n: str(s)[:int(n)],
            'RIGHT': lambda s, n: str(s)[-int(n):],
            'MID': lambda s, start, length: str(s)[int(start):int(start)+int(length)],
            'TRIM': lambda s: str(s).strip(),
            'REPLACE': lambda s, old, new: str(s).replace(old, new),
            
            # Поиск
            'FIND': lambda sub, s: str(s).find(sub),
            'CONTAINS': lambda sub, s: sub in str(s),
            
            # Дата/время
            'TODAY': lambda: datetime.now().date(),
            'NOW': datetime.now,
            'YEAR': lambda d: d.year if hasattr(d, 'year') else pd.to_datetime(d).year,
            'MONTH': lambda d: d.month if hasattr(d, 'month') else pd.to_datetime(d).month,
            'DAY': lambda d: d.day if hasattr(d, 'day') else pd.to_datetime(d).day,
            
            # Приведение типов
            'TOINT': lambda x: int(x) if x is not None else None,
            'TOFLOAT': lambda x: float(x) if x is not None else None,
            'TOSTRING': str,
            'TONUMBER': lambda x: float(x) if x is not None else None,
        }
    
    def evaluate(self, formula: str, context: Dict[str, Any]) -> Any:
        """
        Вычисление формулы в контексте
        
        Args:
            formula: строка формулы
            context: словарь переменных (столбцы, значения)
            
        Returns:
            Результат вычисления
        """
        if not formula or not isinstance(formula, str):
            return formula
        
        formula = formula.strip()
        
        # Если начинается с =, убираем
        if formula.startswith('='):
            formula = formula[1:]
        
        # Простое значение или ссылка на столбец
        if formula in context:
            return context[formula]
        
        # Число
        try:
            if '.' in formula:
                return float(formula)
            return int(formula)
        except ValueError:
            pass
        
        # Строка в кавычках
        if (formula.startswith('"') and formula.endswith('"')) or \
           (formula.startswith("'") and formula.endswith("'")):
            return formula[1:-1]
        
        # Функция
        return self._evaluate_expression(formula, context)
    
    def _evaluate_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Вычисление выражения"""
        expr = expr.strip()
        
        # Поиск функции: FUNC(arg1, arg2, ...)
        func_match = re.match(r'(\w+)\s*\((.*)\)', expr, re.IGNORECASE)
        if func_match:
            func_name = func_match.group(1).upper()
            args_str = func_match.group(2)
            
            if func_name not in self.functions:
                raise ValueError(f"Неизвестная функция: {func_name}")
            
            func = self.functions[func_name]
            args = self._parse_args(args_str, context)
            
            try:
                return func(*args)
            except Exception as e:
                raise ValueError(f"Ошибка функции {func_name}: {str(e)}")
        
        # Бинарные операции
        for op in ['+', '-', '*', '/', '>', '<', '>=', '<=', '==', '!=']:
            # Находим оператор не внутри скобок
            level = 0
            for i, char in enumerate(expr):
                if char == '(':
                    level += 1
                elif char == ')':
                    level -= 1
                elif level == 0 and char == op[0]:
                    if len(op) > 1 and i + 1 < len(expr) and expr[i:i+2] == op:
                        left = expr[:i].strip()
                        right = expr[i+len(op):].strip()
                        left_val = self._evaluate_expression(left, context)
                        right_val = self._evaluate_expression(right, context)
                        
                        if op == '+':
                            return left_val + right_val
                        elif op == '-':
                            return left_val - right_val
                        elif op == '*':
                            return left_val * right_val
                        elif op == '/':
                            return left_val / right_val if right_val != 0 else None
                        elif op == '>':
                            return left_val > right_val
                        elif op == '<':
                            return left_val < right_val
                        elif op == '>=':
                            return left_val >= right_val
                        elif op == '<=':
                            return left_val <= right_val
                        elif op == '==':
                            return left_val == right_val
                        elif op == '!=':
                            return left_val != right_val
                    elif len(op) == 1:
                        left = expr[:i].strip()
                        right = expr[i+1:].strip()
                        left_val = self._evaluate_expression(left, context)
                        right_val = self._evaluate_expression(right, context)
                        
                        if op == '+':
                            return left_val + right_val
                        elif op == '-':
                            return left_val - right_val
                        elif op == '*':
                            return left_val * right_val
                        elif op == '/':
                            return left_val / right_val if right_val != 0 else None
                        elif op == '>':
                            return left_val > right_val
                        elif op == '<':
                            return left_val < right_val
        
        # Ссылка на контекст
        if expr in context:
            return context[expr]
        
        # Попытка числового преобразования
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            return expr
    
    def _parse_args(self, args_str: str, context: Dict[str, Any]) -> List[Any]:
        """Разбор аргументов функции"""
        args = []
        current_arg = ""
        paren_level = 0
        
        for char in args_str:
            if char == '(':
                paren_level += 1
                current_arg += char
            elif char == ')':
                paren_level -= 1
                current_arg += char
            elif char == ',' and paren_level == 0:
                if current_arg.strip():
                    args.append(self._evaluate_expression(current_arg.strip(), context))
                current_arg = ""
            else:
                current_arg += char
        
        if current_arg.strip():
            args.append(self._evaluate_expression(current_arg.strip(), context))
        
        return args


class FormulaModule:
    """Модуль работы с формулами"""
    
    def __init__(self):
        self.engine = FormulaEngine()
    
    def apply_formula_to_column(self, df: pd.DataFrame, target_column: str,
                                formula: str, source_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Применение формулы к столбцу
        
        Args:
            df: исходный DataFrame
            target_column: целевой столбец
            formula: формула для вычисления
            source_columns: столбцы, используемые в формуле
            
        Returns:
            DataFrame с новым столбцом
        """
        result_df = df.copy()
        
        if source_columns is None:
            # Автоматическое определение столбцов из формулы
            source_columns = list(set(re.findall(r'\b([A-Za-z_]\w*)\b', formula)))
            source_columns = [c for c in source_columns if c in df.columns and c.upper() not in self.engine.functions]
        
        errors = []
        values = []
        
        for idx, row in df.iterrows():
            context = {col: row[col] for col in source_columns if col in df.columns}
            
            try:
                value = self.engine.evaluate(formula, context)
                values.append(value)
            except Exception as e:
                values.append(None)
                errors.append(FormulaError(
                    row_index=int(idx),
                    column=target_column,
                    formula=formula,
                    message=str(e)
                ))
        
        result_df[target_column] = values
        
        if errors:
            print(f"Предупреждение: {len(errors)} ошибок при вычислении формулы")
        
        return result_df
    
    def calculate_aggregate(self, df: pd.DataFrame, column: str, 
                           operation: str) -> Any:
        """
        Вычисление агрегатной функции
        
        Args:
            df: DataFrame
            column: столбец для агрегации
            operation: операция (SUM, AVG, MIN, MAX, COUNT, etc.)
            
        Returns:
            Результат агрегации
        """
        if column not in df.columns:
            raise ValueError(f"Столбец {column} не найден")
        
        series = df[column].dropna()
        
        operations = {
            'SUM': series.sum,
            'AVG': series.mean,
            'MIN': series.min,
            'MAX': series.max,
            'COUNT': series.count,
            'MEDIAN': series.median,
            'STD': series.std,
            'VAR': series.var,
            'FIRST': lambda: series.iloc[0] if len(series) > 0 else None,
            'LAST': lambda: series.iloc[-1] if len(series) > 0 else None,
        }
        
        if operation.upper() not in operations:
            raise ValueError(f"Неизвестная операция: {operation}")
        
        return operations[operation.upper()]()
    
    def conditional_calculate(self, df: pd.DataFrame, target_column: str,
                             condition: str, true_formula: str,
                             false_formula: Optional[str] = None) -> pd.DataFrame:
        """
        Условное вычисление
        
        Args:
            df: DataFrame
            target_column: целевой столбец
            condition: условие (формула, возвращающая bool)
            true_formula: формула если истина
            false_formula: формула если ложь
            
        Returns:
            DataFrame с вычисленным столбцом
        """
        result_df = df.copy()
        values = []
        
        for idx, row in df.iterrows():
            context = {col: row[col] for col in df.columns}
            
            try:
                cond_result = self.engine.evaluate(condition, context)
                
                if cond_result:
                    value = self.engine.evaluate(true_formula, context)
                elif false_formula:
                    value = self.engine.evaluate(false_formula, context)
                else:
                    value = None
                
                values.append(value)
            except Exception as e:
                values.append(None)
        
        result_df[target_column] = values
        return result_df
    
    def get_available_functions(self) -> List[str]:
        """Список доступных функций"""
        return list(self.engine.functions.keys())
    
    def validate_formula(self, formula: str) -> tuple[bool, Optional[str]]:
        """
        Валидация формулы
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Пробуем вычислить с пустым контекстом
            self.engine.evaluate(formula, {})
            return True, None
        except Exception as e:
            return False, str(e)

