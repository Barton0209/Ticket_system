"""
М18: Аудит и логирование
FR-1801: Журнал действий пользователя
FR-1802: Отслеживание изменений
"""

from typing import Dict, List, Any
from datetime import datetime
import json
import os


class AuditModule:
    """Модуль аудита"""
    
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def log_action(self, user: str, action: str, details: Dict[str, Any]) -> None:
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'action': action,
            'details': details
        }
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.log_dir, f'audit_{date_str}.jsonl')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def get_logs(self, date: str = None, user: str = None,
                action: str = None) -> List[Dict]:
        logs = []
        
        if date:
            log_file = os.path.join(self.log_dir, f'audit_{date}.jsonl')
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line)
                        if (not user or entry.get('user') == user) and \
                           (not action or entry.get('action') == action):
                            logs.append(entry)
        
        return logs


__all__ = ['AuditModule']
