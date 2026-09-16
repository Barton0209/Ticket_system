"""
М13: Сравнение файлов
FR-1301: Поиск различий между файлами
FR-1302: Визуализация изменений
"""

from typing import Dict, List, Any, Tuple
import pandas as pd


class CompareModule:
    """Модуль сравнения файлов"""
    
    def compare_dataframes(self, df1: pd.DataFrame, df2: pd.DataFrame,
                          key_columns: List[str] = None) -> Dict[str, Any]:
        """Сравнение двух DataFrame"""
        result = {
            'identical': True,
            'rows_only_in_first': 0,
            'rows_only_in_second': 0,
            'modified_rows': 0,
            'differences': []
        }
        
        if key_columns:
            df1_indexed = df1.set_index(key_columns)
            df2_indexed = df2.set_index(key_columns)
            
            only_in_first = df1_indexed.index.difference(df2_indexed.index)
            only_in_second = df2_indexed.index.difference(df1_indexed.index)
            common = df1_indexed.index.intersection(df2_indexed.index)
            
            result['rows_only_in_first'] = len(only_in_first)
            result['rows_only_in_second'] = len(only_in_second)
            
            # Поиск изменённых строк
            for idx in common:
                row1 = df1_indexed.loc[idx]
                row2 = df2_indexed.loc[idx]
                
                if not row1.equals(row2):
                    result['identical'] = False
                    result['modified_rows'] += 1
                    
                    # Поиск различий по столбцам
                    for col in df1.columns:
                        if col not in key_columns:
                            val1 = row1[col]
                            val2 = row2[col]
                            if val1 != val2 or (pd.isna(val1) != pd.isna(val2)):
                                result['differences'].append({
                                    'key': idx,
                                    'column': col,
                                    'old_value': val1,
                                    'new_value': val2
                                })
        else:
            # Простое сравнение без ключей
            result['identical'] = df1.equals(df2)
            if not result['identical']:
                result['differences'].append({'message': 'Файлы не идентичны'})
        
        return result
    
    def find_duplicates(self, df: pd.DataFrame, 
                       columns: List[str] = None) -> pd.DataFrame:
        """Поиск дубликатов"""
        if columns:
            return df[df.duplicated(subset=columns, keep=False)]
        return df[df.duplicated(keep=False)]


__all__ = ['CompareModule']
