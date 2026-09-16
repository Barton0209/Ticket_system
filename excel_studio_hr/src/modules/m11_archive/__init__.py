"""
М11: Архивирование
FR-1101: Сжатие файлов
FR-1102: Распаковка архивов
FR-1103: Поддержка ZIP форматов
"""

import os
import zipfile
import tarfile
from typing import List, Optional
from datetime import datetime


class ArchiveModule:
    """Модуль архивирования"""
    
    def create_zip(self, files: List[str], output_path: str,
                   compression: int = zipfile.ZIP_DEFLATED,
                   password: Optional[str] = None) -> str:
        """Создание ZIP архива"""
        with zipfile.ZipFile(output_path, 'w', compression=compression) as zipf:
            for file in files:
                if os.path.exists(file):
                    arcname = os.path.basename(file)
                    zipf.write(file, arcname)
        return output_path
    
    def extract_zip(self, archive_path: str, output_dir: str,
                   password: Optional[str] = None) -> List[str]:
        """Распаковка ZIP архива"""
        extracted = []
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            zipf.extractall(output_dir, pwd=password.encode() if password else None)
            extracted = [os.path.join(output_dir, name) for name in zipf.namelist()]
        return extracted
    
    def list_archive(self, archive_path: str) -> List[dict]:
        """Список файлов в архиве"""
        files = []
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            for info in zipf.infolist():
                files.append({
                    'filename': info.filename,
                    'size': info.file_size,
                    'compressed_size': info.compress_size,
                    'date': datetime(*info.date_time).isoformat(),
                    'compression_ratio': round(info.file_size / info.compress_size, 2) if info.compress_size > 0 else 0
                })
        return files


__all__ = ['ArchiveModule']
