"""
М10: Разделение файлов
FR-1001: Разделение по столбцу
FR-1002: Разделение по количеству строк
FR-1003: Фильтрация перед разделением
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import os


class SplitModule:
    """Модуль разделения файлов"""
    
    def split_by_column(self, df: pd.DataFrame, column: str,
                       output_dir: str, prefix: str = "split_",
                       file_format: str = "xlsx") -> List[str]:
        """
        Разделение DataFrame по значениям столбца
        
        Args:
            df: исходный DataFrame
            column: столбец для разделения
            output_dir: директория для выходных файлов
            prefix: префикс имен файлов
            file_format: формат файлов (xlsx, csv)
            
        Returns:
            Список созданных файлов
        """
        if column not in df.columns:
            raise ValueError(f"Столбец {column} не найден")
        
        os.makedirs(output_dir, exist_ok=True)
        created_files = []
        
        # Группировка по столбцу
        grouped = df.groupby(column, dropna=False)
        
        for value, group in grouped:
            # Безопасное имя файла
            safe_value = str(value).replace('/', '_').replace('\\', '_').replace(':', '_')
            filename = f"{prefix}{safe_value}.{file_format}"
            filepath = os.path.join(output_dir, filename)
            
            if file_format == 'csv':
                group.to_csv(filepath, index=False, encoding='utf-8-sig')
            else:
                group.to_excel(filepath, index=False)
            
            created_files.append(filepath)
        
        return created_files
    
    def split_by_rows(self, df: pd.DataFrame, rows_per_file: int,
                     output_dir: str, prefix: str = "part_",
                     file_format: str = "xlsx") -> List[str]:
        """
        Разделение DataFrame на файлы с указанным количеством строк
        
        Args:
            df: исходный DataFrame
            rows_per_file: количество строк в файле
            output_dir: директория для выходных файлов
            prefix: префикс имен файлов
            file_format: формат файлов
            
        Returns:
            Список созданных файлов
        """
        os.makedirs(output_dir, exist_ok=True)
        created_files = []
        
        total_rows = len(df)
        num_files = (total_rows + rows_per_file - 1) // rows_per_file
        
        for i in range(num_files):
            start_idx = i * rows_per_file
            end_idx = min((i + 1) * rows_per_file, total_rows)
            
            chunk = df.iloc[start_idx:end_idx]
            filename = f"{prefix}{i+1:03d}.{file_format}"
            filepath = os.path.join(output_dir, filename)
            
            if file_format == 'csv':
                chunk.to_csv(filepath, index=False, encoding='utf-8-sig')
            else:
                chunk.to_excel(filepath, index=False)
            
            created_files.append(filepath)
        
        return created_files
    
    def split_by_filter(self, df: pd.DataFrame, 
                       filters: List[Dict[str, Any]],
                       output_dir: str,
                       prefix: str = "filtered_",
                       file_format: str = "xlsx") -> List[str]:
        """
        Разделение по фильтрам
        
        Args:
            df: исходный DataFrame
            filters: список фильтров [{column, operator, value}]
            output_dir: директория для выходных файлов
            prefix: префикс имен файлов
            file_format: формат файлов
            
        Returns:
            Список созданных файлов
        """
        os.makedirs(output_dir, exist_ok=True)
        created_files = []
        
        for i, filter_config in enumerate(filters):
            column = filter_config.get('column')
            operator = filter_config.get('operator', '==')
            value = filter_config.get('value')
            
            if column not in df.columns:
                continue
            
            # Применение фильтра
            if operator == '==':
                filtered = df[df[column] == value]
            elif operator == '!=':
                filtered = df[df[column] != value]
            elif operator == '>':
                filtered = df[df[column] > value]
            elif operator == '<':
                filtered = df[df[column] < value]
            elif operator == '>=':
                filtered = df[df[column] >= value]
            elif operator == '<=':
                filtered = df[df[column] <= value]
            elif operator == 'in':
                filtered = df[df[column].isin(value)]
            elif operator == 'contains':
                filtered = df[df[column].astype(str).str.contains(str(value), na=False)]
            else:
                continue
            
            if len(filtered) > 0:
                filename = f"{prefix}{filter_config.get('name', i)}.{file_format}"
                filepath = os.path.join(output_dir, filename)
                
                if file_format == 'csv':
                    filtered.to_csv(filepath, index=False, encoding='utf-8-sig')
                else:
                    filtered.to_excel(filepath, index=False)
                
                created_files.append(filepath)
        
        return created_files
    
    def get_split_preview(self, df: pd.DataFrame, column: str,
                         max_groups: int = 10) -> Dict[str, Any]:
        """
        Предварительный просмотр результатов разделения
        
        Returns:
            dict со статистикой групп
        """
        if column not in df.columns:
            raise ValueError(f"Столбец {column} не найден")
        
        grouped = df.groupby(column, dropna=False)
        groups_info = []
        
        for value, group in list(grouped)[:max_groups]:
            groups_info.append({
                'value': value,
                'row_count': len(group),
                'percentage': round(len(group) / len(df) * 100, 2)
            })
        
        return {
            'total_groups': len(grouped),
            'showing': len(groups_info),
            'groups': groups_info,
            'total_rows': len(df)
        }


__all__ = ['SplitModule']
